"""
make_jf_cando_csv.py
====================
Create jf_cando_clean.csv from 202305_JF_Cando_Category_list.pdf

• Uses tabula-py (if Java is available) otherwise falls back to PyMuPDF.
• Produces a nine-column CSV with embedded line-breaks flattened and
  every cell quoted, so Excel/LibreOffice show a perfect table.

Columns:
No,種別,種類,レベル,言語活動,カテゴリー,第1トピック,
JF Can-do (日本語),JF Can-do (English)
"""
import argparse, csv, re, sys
from pathlib import Path

from networkx import add_path
import pandas as pd

# ---------------------------------------------------------------------
PDF_DEFAULT = "202305_JF_Cando_Category_list.pdf"
OUT_DEFAULT = "jf_cando_clean.csv"

COLUMN_ORDER = [
    "No", "種別", "種類", "レベル", "言語活動",
    "カテゴリー", "第1トピック",
    "JF Can-do (日本語)", "JF Can-do (English)"
]
# ---------------------------------------------------------------------


# ────────────────────────────────────────────────────────────────────
# 1) Preferred extraction: Tabula
# ────────────────────────────────────────────────────────────────────
def try_tabula(pdf_path: str) -> pd.DataFrame | None:
    """Return DataFrame via Tabula or None if Tabula unavailable/fails."""
    try:
        import tabula  # noqa: F401
    except ImportError:
        return None

    try:
        dfs = tabula.read_pdf(
            pdf_path,
            pages="all",
            lattice=True,                       # detect grid lines
            pandas_options={"dtype": str},
        )
    except Exception:
        return None

    if not dfs:
        return None

    df = pd.concat(dfs, ignore_index=True)
    df.columns = [c.strip() for c in df.columns]
    if len(df.columns) < 9:                     # table shape off?
        return None

    df = df.iloc[:, :9]                         # keep first nine cols
    df.columns = COLUMN_ORDER

    # forward-fill structural columns
    df["No"] = df["No"].ffill()
    for c in COLUMN_ORDER[1:7]:
        df[c] = df[c].replace("", pd.NA).ffill()

    df = df[df["No"].str.match(r"^\d+$")]       # drop header junk
    return df.reset_index(drop=True)


# ────────────────────────────────────────────────────────────────────
# 2) Fallback extraction: PyMuPDF (fitz)
# ────────────────────────────────────────────────────────────────────
def fallback_fitz(pdf_path: str) -> pd.DataFrame:
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    rows, cur = [], {k: "" for k in COLUMN_ORDER}
    jp, en, in_jp, in_en = [], [], False, False

    def flush():
        nonlocal cur, jp, en, in_jp, in_en
        if cur["No"]:
            cur["JF Can-do (日本語)"] = " ".join(jp).strip()
            cur["JF Can-do (English)"] = " ".join(en).strip()
            rows.append(cur)
        cur = {k: "" for k in COLUMN_ORDER}
        jp, en, in_jp, in_en = [], [], False, False

    for page in doc:
        for raw in page.get_text("text").splitlines():
            line = raw.strip()
            if not line:
                continue
            # New row?
            if re.fullmatch(r"\d{1,4}", line):
                flush()
                cur["No"] = line
                continue
            if line in {"JF", "まるごと"}:
                cur["種別"] = line; continue
            if line in {"活動", "やりとり", "受容", "産出", "媒介"}:
                cur["種類"] = line; cur["言語活動"] = line; continue
            if re.fullmatch(r"[AB][12]", line):
                cur["レベル"] = line; continue

            # Before JP sentence: fill カテゴリー / トピック
            if not in_jp and not in_en:
                if cur["カテゴリー"] == "":
                    cur["カテゴリー"] += line
                    if any(s in cur["カテゴリー"] for s in ("を語る", "を書く", "をする", "を読む")):
                        cur["カテゴリー"] = cur["カテゴリー"].strip()
                else:
                    cur["第1トピック"] += line
                continue

            # English start?
            if line.startswith("Can "):
                in_en, in_jp = True, False; en.append(line); continue

            if in_en:
                en.append(line)
            else:
                in_jp = True; jp.append(line)

    flush()
    return pd.DataFrame(rows)[COLUMN_ORDER]


# ────────────────────────────────────────────────────────────────────
# Tidy • flatten embedded newlines and double-spaces
# ────────────────────────────────────────────────────────────────────
def tidy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.fillna("")
    for col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(r"[\r\n]+", " ", regex=True)
            .str.replace(r"\s{2,}", " ", regex=True)
            .str.strip()
        )
    return df


# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────
def main(pdf_path: str, out_csv: str):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        sys.exit(f"PDF not found: {pdf_path}")

    print("Attempting PDF extraction with Tabula...")
    df = try_tabula(str(pdf_path))      # first attempt (Tabula)
    if df is None or df.empty:          # if Tabula failed or returned nothing
        print("Tabula failed. Falling back to PyMuPDF (fitz)...")
        df = fallback_fitz(str(pdf_path))
    else:
        print("Tabula extraction successful.")

    df = tidy(df)[COLUMN_ORDER]

    df.to_csv(
        out_csv,
        index=False,
        encoding="utf-8",
        quoting=csv.QUOTE_ALL,
        lineterminator="\r\n"
    )
    print(f"✅  {len(df):,} rows written → {out_csv}")


# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=PDF_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()
    main(args.pdf, args.out)
