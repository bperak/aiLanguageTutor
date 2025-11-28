#!/usr/bin/env python3
"""
Generate watercolor-style illustrations for GrammarPattern nodes using Gemini
==============================================================================

This script:
- Reads GrammarPattern nodes from Neo4j
- Builds a metaphor-rich illustration prompt for each pattern
- Calls Gemini image model (models/gemini-2.5-flash-image-preview)
- Saves the image to images/grammar/
- Stores the prompt and saved image path on the GrammarPattern node

Usage (PowerShell examples):
  # Activate venv first
  # .\.venv\Scripts\Activate.ps1

  # Generate up to 20 new illustrations
  python resources/generate_grammar_illustrations.py --limit 20 --offset 0

  # Dry-run (build prompts only, do not call API or write to Neo4j/files)
  python resources/generate_grammar_illustrations.py --limit 5 --dry-run

Environment (.env managed by user):
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USERNAME=neo4j
  NEO4J_PASSWORD=...
  GEMINI_API_KEY=...
  ILLUSTRATION_BATCH_SIZE=20            (optional)
  ILLUSTRATION_CONCURRENCY=1            (optional)
  ILLUSTRATION_OUT_DIR=images/grammar   (optional)
"""

import argparse
import base64
import datetime as dt
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load env
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env")
except Exception:
    pass

from neo4j import GraphDatabase


MODEL_ID = "gemini-2.5-flash-image-preview"


class Settings:
    def __init__(self) -> None:
        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.batch_size = int(os.getenv('ILLUSTRATION_BATCH_SIZE', '20'))
        self.concurrency = int(os.getenv('ILLUSTRATION_CONCURRENCY', '1'))
        self.out_dir = os.getenv('ILLUSTRATION_OUT_DIR', 'images/grammar')

        if not self.neo4j_password:
            raise ValueError("NEO4J_PASSWORD is required")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required")


def create_gemini_client(api_key: str):
    """Lazy import google-genai client to keep tests light."""
    from google import genai  # type: ignore
    return genai.Client(api_key=api_key)


# ----------------------------- Utility helpers -----------------------------

def slugify(value: str) -> str:
    """Make a filesystem-friendly slug."""
    if value is None:
        return "item"
    safe = ''.join(ch if ch.isalnum() or ch in ['-', '_'] else '-' for ch in value)
    # Collapse repeats
    while '--' in safe:
        safe = safe.replace('--', '-')
    return safe.strip('-_').lower() or 'item'


def ensure_out_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    # also create runs dir for logs
    (p / "_runs").mkdir(parents=True, exist_ok=True)
    (p / "meta").mkdir(parents=True, exist_ok=True)
    return p


# ----------------------------- Theme selection -----------------------------

THEMES = {
    "Identity/Classification": "Identity/Classification",
    "Ability/Possibility": "Ability/Possibility",
    "Existence/Location": "Existence/Location",
    "Action/Movement": "Action/Movement",
    "Giving/Receiving": "Giving/Receiving",
    "Cause/Reason": "Cause/Reason",
    "Purpose/Intention": "Purpose/Intention",
    "Time/Sequence": "Time/Sequence",
    "Comparison/Degree": "Comparison/Degree",
    "Permission/Prohibition": "Permission/Prohibition",
    "Obligation/Necessity": "Obligation/Necessity",
    "Desire/Wish": "Desire/Wish",
    "Change/Transformation": "Change/Transformation",
    "Passive/Agent": "Passive/Agent",
    "Conditional": "Conditional",
    "Volition/Invitation": "Volition/Invitation",
}


def pick_theme(node: Dict[str, Optional[str]]) -> str:
    """Heuristic mapping from pattern/classification to a theme category."""
    classification = (node.get('classification') or '').strip()
    pattern = (node.get('pattern') or '').strip()

    # Simple heuristics
    if 'でき' in pattern or '可能' in classification:
        return THEMES["Ability/Possibility"]
    if 'あります' in pattern or 'います' in pattern or '存在' in classification:
        return THEMES["Existence/Location"]
    if '行き' in pattern or '来' in pattern or '動作' in classification or '移動' in classification:
        return THEMES["Action/Movement"]
    if 'あげ' in pattern or 'もら' in pattern or 'くれ' in pattern:
        return THEMES["Giving/Receiving"]
    if 'から' in pattern or 'ので' in pattern or '理由' in classification:
        return THEMES["Cause/Reason"]
    if 'ために' in pattern or '目的' in classification:
        return THEMES["Purpose/Intention"]
    if 'てから' in pattern or '時' in pattern or '順序' in classification:
        return THEMES["Time/Sequence"]
    if 'より' in pattern or '一番' in pattern or '比較' in classification:
        return THEMES["Comparison/Degree"]
    if 'てもいい' in pattern or 'てはいけない' in pattern or '許可' in classification or '禁止' in classification:
        return THEMES["Permission/Prohibition"]
    if 'なければ' in pattern or '必要' in classification:
        return THEMES["Obligation/Necessity"]
    if 'たい' in pattern or 'ほしい' in pattern or '希望' in classification:
        return THEMES["Desire/Wish"]
    if 'になります' in pattern or '変化' in classification:
        return THEMES["Change/Transformation"]
    if 'られ' in pattern or '受け身' in classification:
        return THEMES["Passive/Agent"]
    if 'たら' in pattern or 'ば' in pattern or 'と' in pattern or '条件' in classification:
        return THEMES["Conditional"]
    if 'ましょう' in pattern or 'ませんか' in pattern or '勧誘' in classification:
        return THEMES["Volition/Invitation"]
    # Default
    return THEMES["Identity/Classification"]


# ----------------------------- Prompt builder -----------------------------

CORE_INSTRUCTIONS = (
    "Create an illustration in a highly Japanese illustrative style, evoking gentle watercolor/ink wash aesthetics. "
    "Keep it clean, minimalist, calm, and culturally authentic. "
    "Use a warm, inviting palette with muted tones. Stylize characters to be friendly and simple (no complex details). "
    "Absolutely NO TEXT, letters, numbers, signs, labels, UI, or typographic elements anywhere in the image. "
    "The mood must remain approachable and educational throughout."
)


def build_illustration_prompt(node: Dict[str, Optional[str]]) -> str:
    pattern = node.get('pattern') or ''
    pattern_romaji = node.get('pattern_romaji') or ''
    example_sentence = node.get('example_sentence') or ''
    classification = node.get('classification') or ''
    jfs_category = node.get('jfs_category') or ''
    textbook = node.get('textbook') or ''

    theme = pick_theme(node)
    # Essence / descriptive context
    description = node.get('description') or node.get('what_is') or ''

    # Suggest specific visual elements based on theme
    characters = "A single stylized character"  # default
    action = "A simple interaction that clearly conveys the grammar’s function"
    symbolism = "A strong, central visual metaphor that explicitly maps to the grammar’s essence"
    setting = "A tranquil traditional Japanese room or serene garden"
    key_idea = "Communicate the grammar’s core meaning at a glance"

    if theme == THEMES["Identity/Classification"]:
        symbolism = "Two distinct objects joined by a soft red thread, clearly communicating identity/equation"
        action = "One item gently aligning with the other to convey equivalence"
    elif theme == THEMES["Ability/Possibility"]:
        symbolism = "An opening path bathed in soft light; a bud blossoming to clearly signify capability"
        action = "Character performing a simple skill with ease"
    elif theme == THEMES["Existence/Location"]:
        symbolism = "An object purposefully placed in a space; a clearly highlighted spot on a simple map"
        action = "Character noticing or placing an item"
    elif theme == THEMES["Action/Movement"]:
        symbolism = "Footsteps on a gentle path or a flowing river to unmistakably signify motion"
        action = "Character moving toward a destination"
    elif theme == THEMES["Giving/Receiving"]:
        symbolism = "Hands exchanging a small wrapped gift, clearly emphasizing giver→receiver direction"
        action = "A considerate exchange between two stylized figures"
    elif theme == THEMES["Cause/Reason"]:
        symbolism = "Visible cause→effect chain: soft domino sequence or a seed sprouting into a plant"
        action = "Clear before→after visual cue"
    elif theme == THEMES["Purpose/Intention"]:
        symbolism = "A path leading to a clear goal marker; blueprint simplicity implying intention"
        action = "Focused preparation toward a goal"
    elif theme == THEMES["Time/Sequence"]:
        symbolism = "Minimal clock/hourglass or small frames showing clear progression over time"
        action = "Order of events gently indicated"
    elif theme == THEMES["Comparison/Degree"]:
        symbolism = "Two objects of different sizes or a ladder with distinct steps, highlighting degree"
        action = "Highlight the relative difference without clutter"
    elif theme == THEMES["Permission/Prohibition"]:
        symbolism = "Open vs closed gate; warm green glow vs soft red stop to signal permission vs prohibition"
        action = "Welcoming gesture vs a gentle hand stop"
    elif theme == THEMES["Obligation/Necessity"]:
        symbolism = "A single bridge that must be crossed; a clear checklist implying necessity"
        action = "Character decisively walking the only path"
    elif theme == THEMES["Desire/Wish"]:
        symbolism = "A reaching hand toward a desired object; a small bloom representing a wish"
        action = "Character looking longingly at a simple object"
    elif theme == THEMES["Change/Transformation"]:
        symbolism = "Caterpillar→butterfly, seed→sprout, or cloud clearing to unambiguously depict change"
        action = "A calm reveal of before/after states"
    elif theme == THEMES["Passive/Agent"]:
        symbolism = "An object being acted upon by an external gentle force; a guiding hand"
        action = "External influence visible yet soft"
    elif theme == THEMES["Conditional"]:
        symbolism = "A branching path or a key unlocking a door to visualize if→then"
        action = "If→then progression subtly indicated"
    elif theme == THEMES["Volition/Invitation"]:
        symbolism = "Hands reaching to collaborate; a small group moving together to invite action"
        action = "Inviting gesture toward shared activity"

    avoid = (
        "No text of any kind (letters, numbers, signs, labels, UI). "
        "No harsh lines, no overly bright neon colors, no crowded scenes."
    )

    # Compose final prompt
    # Minimal structured guidance to reinforce constraints (not to be rendered as text)
    structured_guidance = {
        "essence": description or theme,
        "metaphor": symbolism,
        "no_text_in_image": True,
        "forbidden_text": "no letters, numbers, signs, labels, UI, or typographic marks",
        "allow_text_in_image": False
    }

    lines = [
        CORE_INSTRUCTIONS,
        "",
        f"For the grammar pattern: {pattern} {f'({pattern_romaji})' if pattern_romaji else ''}",
        "",
        f"Theme/Concept: {theme}",
        "",
        "Essence & Meaning (for the artist, do not add any text in the image):",
        f"- Essence: {description or 'Emphasize the core functional meaning of the pattern with a clear metaphor.'}",
        "",
        "Specific Visual Elements to Consider:",
        f"- Characters: {characters}",
        f"- Action/Interaction: {action}",
        f"- Symbolism/Metaphor: {symbolism}",
        f"- Setting: {setting}",
        f"- Key Idea to Convey: {key_idea} (make the metaphor the focal point)",
        "",
        f"Context cues (optional, do not reproduce as text): classification={classification}, jfs={jfs_category}, level={textbook}, example={example_sentence}",
        "",
        f"Avoid: {avoid}",
        "",
        "Structured guidance (do NOT render this as text; follow concept only):",
        json.dumps(structured_guidance, ensure_ascii=False)
    ]
    return "\n".join(lines).strip()


# ----------------------------- Neo4j access -----------------------------

def fetch_candidates(session, *, limit: int, offset: int, force: bool = False, only_id: Optional[str] = None) -> List[Dict[str, Optional[str]]]:
    if only_id:
        query = (
            "MATCH (g:GrammarPattern {id: $id})\n"
            "RETURN g.id as id, g.sequence_number as sequence_number, g.pattern as pattern, "
            "g.pattern_romaji as pattern_romaji, g.classification as classification, g.jfs_category as jfs_category, "
            "g.textbook as textbook, g.example_sentence as example_sentence, g.description as description, g.what_is as what_is, g.illustration_path as illustration_path"
        )
        params = {"id": only_id}
    else:
        where_clause = "" if force else "WHERE g.illustration_path IS NULL"
        query = (
            f"MATCH (g:GrammarPattern) {where_clause}\n"
            "RETURN g.id as id, g.sequence_number as sequence_number, g.pattern as pattern, "
            "g.pattern_romaji as pattern_romaji, g.classification as classification, g.jfs_category as jfs_category, "
            "g.textbook as textbook, g.example_sentence as example_sentence, g.description as description, g.what_is as what_is, g.illustration_path as illustration_path\n"
            "ORDER BY coalesce(g.sequence_number, 0) ASC, g.id ASC\n"
            "SKIP $offset LIMIT $limit"
        )
        params = {"offset": offset, "limit": limit}

    result = session.run(query, **params)
    return [dict(r) for r in result]


def update_node_with_illustration(session, *, node_id: str, prompt: str, rel_path: str) -> None:
    query = (
        "MATCH (g:GrammarPattern {id: $id})\n"
        "SET g.illustration_prompt = $prompt,\n"
        "    g.illustration_path = $path,\n"
        "    g.illustration_model = $model,\n"
        "    g.illustration_created_at = datetime()"
    )
    session.run(query, id=node_id, prompt=prompt, path=rel_path, model=MODEL_ID)


def metaphor_title_for_theme(theme: str) -> str:
    mapping = {
        THEMES["Identity/Classification"]: "Red thread of identity",
        THEMES["Ability/Possibility"]: "Opening path of ability",
        THEMES["Existence/Location"]: "Place in space",
        THEMES["Action/Movement"]: "Flow of motion",
        THEMES["Giving/Receiving"]: "Gesture of giving",
        THEMES["Cause/Reason"]: "Chain of cause and effect",
        THEMES["Purpose/Intention"]: "Path toward intention",
        THEMES["Time/Sequence"]: "Frames of time",
        THEMES["Comparison/Degree"]: "Steps of degree",
        THEMES["Permission/Prohibition"]: "Gate of permission",
        THEMES["Obligation/Necessity"]: "Bridge of necessity",
        THEMES["Desire/Wish"]: "Reaching for a wish",
        THEMES["Change/Transformation"]: "Becoming",
        THEMES["Passive/Agent"]: "Guided by another",
        THEMES["Conditional"]: "Branching if→then",
        THEMES["Volition/Invitation"]: "Invitation to act",
    }
    return mapping.get(theme, "Visual essence")


def _extract_json_block(text: str) -> Optional[str]:
    """Try to extract a JSON array/object substring from model text output."""
    if not text:
        return None
    text = text.strip()
    # Prefer fenced code blocks
    if "```" in text:
        parts = text.split("```")
        # pick the largest block that starts with { or [
        candidates = [p.strip() for p in parts if p.strip().startswith(('{', '['))]
        if candidates:
            return max(candidates, key=len)
    # Fallback: find first { or [ and last matching brace/bracket
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
    return None


def generate_usage_examples_for_pattern(client, pattern: str, pattern_romaji: str, theme: str, description: str) -> List[Dict[str, str]]:
    """Ask Gemini to produce 2 usage examples with jp, romaji, and en in strict JSON."""
    instruction = (
        "Generate exactly 2 usage examples for this Japanese grammar pattern as pure JSON array. "
        "Each item must have keys: jp (Japanese), romaji (romanization), en (English). "
        "Do not include any extra commentary or markdown."
    )
    prompt = (
        f"{instruction}\n\n"
        f"Pattern: {pattern} {f'({pattern_romaji})' if pattern_romaji else ''}\n"
        f"Essence: {description or theme}\n"
        "Constraints: natural, beginner-friendly sentences; ensure romaji matches jp; keep it short."
    )
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt])
        text = getattr(resp, 'text', None)
        if not text and hasattr(resp, 'candidates'):
            # Fallback: concatenate candidate texts
            texts = []
            for cand in resp.candidates:
                if hasattr(cand, 'content') and hasattr(cand.content, 'parts'):
                    for part in cand.content.parts:
                        if getattr(part, 'text', None):
                            texts.append(part.text)
            text = "\n".join(texts)
        json_str = _extract_json_block(text or "")
        if not json_str:
            return []
        data = json.loads(json_str)
        # Basic validation
        results: List[Dict[str, str]] = []
        if isinstance(data, list):
            for item in data[:2]:
                if isinstance(item, dict):
                    jp = str(item.get('jp', '')).strip()
                    romaji = str(item.get('romaji', '')).strip()
                    en = str(item.get('en', '')).strip()
                    if jp and romaji and en:
                        results.append({"jp": jp, "romaji": romaji, "en": en})
        return results
    except Exception:
        return []


# ----------------------------- Gemini generate -----------------------------

def _extract_image_bytes(result) -> Optional[bytes]:
    """Best-effort extraction of image bytes from google-genai response shapes."""
    # Known shapes vary across SDK revisions. Try common fields.
    if result is None:
        return None
    # 0) Preferred: generate_content returns candidates[].content.parts[].inline_data.data
    try:
        candidates = getattr(result, 'candidates', None)
        if candidates:
            for cand in candidates:
                content = getattr(cand, 'content', None)
                parts = getattr(content, 'parts', []) if content else []
                for part in parts:
                    inline_data = getattr(part, 'inline_data', None)
                    if inline_data is not None:
                        data = getattr(inline_data, 'data', None)
                        if isinstance(data, (bytes, bytearray)) and data:
                            return bytes(data)
                        if isinstance(data, str) and data:
                            # Some SDKs may surface base64 strings
                            try:
                                return base64.b64decode(data)
                            except Exception:
                                pass
    except Exception:
        pass
    # 1) client.images.generate returns result.images[0].image.bytes or .bytes
    try:
        images = getattr(result, 'images', None) or getattr(result, 'generated_images', None)
        if images:
            first = images[0]
            if hasattr(first, 'image') and hasattr(first.image, 'bytes') and first.image.bytes:
                return first.image.bytes
            if hasattr(first, 'bytes') and first.bytes:
                return first.bytes
            if hasattr(first, 'b64_data') and first.b64_data:
                return base64.b64decode(first.b64_data)
    except Exception:
        pass
    # 2) Some responses include a single image field
    try:
        image = getattr(result, 'image', None)
        if image and hasattr(image, 'bytes') and image.bytes:
            return image.bytes
    except Exception:
        pass
    # 3) JSON payload with base64
    try:
        if isinstance(result, dict):
            b64 = result.get('image_b64') or result.get('data')
            if b64:
                return base64.b64decode(b64)
    except Exception:
        pass
    return None


def generate_image_bytes(client, prompt: str) -> bytes:
    """Call Gemini to create an image and return raw bytes.

    Note: If you encounter an AttributeError, update the call to match your installed
    google-genai version. We prefer `client.models.generate_content` for this model.
    """
    # Preferred path per current SDK docs/snippet provided by user
    try:
        result = client.models.generate_content(model=MODEL_ID, contents=[prompt])
    except Exception as e:
        # As last resort, try old shapes
        try:
            result = client.images.generate(model=MODEL_ID, prompt=prompt)  # type: ignore[attr-defined]
        except Exception as inner:
            raise RuntimeError(f"Gemini image generation call failed: {e} / {inner}")

    img = _extract_image_bytes(result)
    if not img:
        raise RuntimeError("No image bytes returned from Gemini")
    return img


# ----------------------------- Main flow -----------------------------

def process_batch(driver, client, out_dir: Path, *, limit: int, offset: int, dry_run: bool, force: bool, only_id: Optional[str]) -> Tuple[int, int]:
    created = 0
    skipped = 0

    with driver.session() as session:
        nodes = fetch_candidates(session, limit=limit, offset=offset, force=force, only_id=only_id)
        if not nodes:
            logger.info("No GrammarPattern nodes to process.")
            return (0, 0)

        run_log_path = out_dir / "_runs" / f"run_{dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
        with run_log_path.open('a', encoding='utf-8') as runlog:
            for node in nodes:
                node_id = str(node.get('id') or '')
                seq = node.get('sequence_number')
                pattern = node.get('pattern') or ''
                prompt = build_illustration_prompt(node)

                # Filename
                if isinstance(seq, int):
                    prefix = f"{seq:03d}-"
                else:
                    prefix = ""
                name_core = slugify(pattern) if pattern else slugify(node_id)
                filename = f"{prefix}{name_core}.png"
                rel_path = str(Path("images") / "grammar" / filename)
                abs_path = out_dir / filename

                # Dry run: log and continue
                if dry_run:
                    runlog.write(json.dumps({
                        "id": node_id,
                        "action": "dry-run",
                        "filename": filename,
                        "prompt": prompt[:1800]
                    }, ensure_ascii=False) + "\n")
                    skipped += 1
                    continue

                try:
                    img_bytes = generate_image_bytes(client, prompt)
                    abs_path.write_bytes(img_bytes)
                    update_node_with_illustration(session, node_id=node_id, prompt=prompt, rel_path=rel_path)

                    # Build JSON sidecar metadata based on current node and theme
                    theme = pick_theme(node)
                    description = node.get('description') or node.get('what_is') or ''
                    examples = generate_usage_examples_for_pattern(
                        client,
                        pattern=pattern,
                        pattern_romaji=node.get('pattern_romaji') or '',
                        theme=theme,
                        description=description,
                    )
                    sidecar = {
                        "pattern_id": node_id,
                        "pattern": pattern,
                        "pattern_romaji": node.get('pattern_romaji') or '',
                        "grammar_essence": theme,
                        "metaphor_title": metaphor_title_for_theme(theme),
                        "no_text_in_image": True,
                        "image_path": rel_path.replace("\\", "/"),
                        "ai_model": MODEL_ID,
                        "usage_examples": examples,
                        "teaching_points": [],
                        "created_at": dt.datetime.utcnow().isoformat() + "Z"
                    }
                    sidecar_name = f"{prefix}{name_core}.json"
                    sidecar_rel = str(Path("images") / "grammar" / "meta" / sidecar_name)
                    sidecar_abs = out_dir / "meta" / sidecar_name
                    sidecar_abs.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding='utf-8')
                    # Store sidecar path on node
                    session.run(
                        "MATCH (g:GrammarPattern {id: $id}) SET g.illustration_meta_path = $meta, g.usage_examples = $examples",
                        id=node_id, meta=sidecar_rel, examples=examples
                    )

                    created += 1
                    runlog.write(json.dumps({
                        "id": node_id,
                        "action": "created",
                        "path": rel_path,
                        "meta": sidecar_rel,
                        "size": len(img_bytes)
                    }, ensure_ascii=False) + "\n")
                    logger.info(f"Saved image and updated node id={node_id} -> {rel_path}")
                except Exception as e:
                    runlog.write(json.dumps({
                        "id": node_id,
                        "action": "error",
                        "error": str(e)
                    }, ensure_ascii=False) + "\n")
                    logger.error(f"Failed to generate/store illustration for id={node_id}: {e}")
                    skipped += 1

    return (created, skipped)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate illustrations for GrammarPattern nodes using Gemini")
    p.add_argument("--limit", type=int, default=None, help="Max patterns to process (overrides env batch size)")
    p.add_argument("--offset", type=int, default=0, help="Offset for paging")
    p.add_argument("--force", action="store_true", help="Regenerate even if illustration_path exists")
    p.add_argument("--dry-run", action="store_true", help="Build prompts only; do not call API or write")
    p.add_argument("--out-dir", type=str, default=None, help="Output dir for images (default images/grammar)")
    p.add_argument("--id", type=str, default=None, help="Process a single GrammarPattern by id")
    return p.parse_args()


def main() -> None:
    settings = Settings()
    args = parse_args()

    limit = args.limit if args.limit is not None else settings.batch_size
    offset = args.offset
    force = args.force
    dry_run = args.dry_run
    out_dir = ensure_out_dir(args.out_dir or settings.out_dir)

    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    client = create_gemini_client(settings.gemini_api_key)

    try:
        created, skipped = process_batch(
            driver, client, out_dir,
            limit=limit, offset=offset, dry_run=dry_run, force=force, only_id=args.id
        )
        logger.info(f"Done. created={created}, skipped={skipped}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()


