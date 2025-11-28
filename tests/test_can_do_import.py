import io
from pathlib import Path

from resources.can_do_import import parse_can_do_tsv, CanDoRow


def _make_tsv(tmp_path: Path) -> Path:
    content = "\t".join([
        "No.",
        "種別",
        "種類",
        "レベル",
        "活動",
        "カテゴリー",
        "第1トピック",
        "JF Can-do (日本語)",
        "JF Can-do (English)",
    ]) + "\n"
    content += "\t".join([
        "1",
        "JF",
        "活動",
        "B2",
        "産出",
        "自由時間と娯楽",
        "連続テレビドラマ",
        "日本語の説明",
        "English description",
    ]) + "\n"

    p = tmp_path / "mini_can_do.tsv"
    p.write_text(content, encoding="utf-8")
    return p


def test_parse_can_do_tsv(tmp_path: Path):
    tsv = _make_tsv(tmp_path)
    rows = parse_can_do_tsv(tsv)
    assert len(rows) == 1
    row: CanDoRow = rows[0]
    assert row.entryNumber == 1
    assert row.source == "JF"
    assert row.type == "活動"
    assert row.level == "B2"
    assert row.skillDomain == "産出"
    assert row.category == "自由時間と娯楽"
    assert row.primaryTopic.startswith("連続テレビ")
    assert row.descriptionJa == "日本語の説明"
    assert row.descriptionEn == "English description"
    as_dict = row.to_dict()
    assert as_dict["uid"] == "JF:1"
    assert as_dict["entryNumber"] == 1
    assert as_dict["descriptionEn"].startswith("English")


