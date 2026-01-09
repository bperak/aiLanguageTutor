from __future__ import annotations

import re
from typing import Optional


def prettify_romaji_template(text: Optional[str]) -> str:
    """
    Prettify grammar-template romaji strings for better readability.
    
    Handles textbook-style patterns like:
    - `N(kotoba)gadekimasu(ka) Nhadekimasen` -> `N (kotoba) ga dekimasu (ka) N ha dekimasen`
    - `~wa~desu` -> `~wa ~desu`
    
    This function:
    - Adds spaces around parentheses
    - Splits common particle/verb boundaries (ga, wa, ha, de, ni, wo, etc.)
    - Normalizes multiple spaces
    - Preserves tilde (~) placeholders
    
    Args:
        text: Raw romaji template string from textbook data
        
    Returns:
        Formatted romaji string with proper spacing
    """
    if not isinstance(text, str) or not text:
        return ""
    
    result = text.strip()

    # 1) Parentheses spacing: "N(kotoba)ga" -> "N (kotoba) ga"
    result = re.sub(r"(\S)\(", r"\1 (", result)
    result = re.sub(r"\)(\S)", r") \1", result)

    # 2) Tilde placeholders: "~wa~desu" -> "~wa ~desu"
    result = re.sub(r"(~[a-z0-9]+)(~)", r"\1 \2", result, flags=re.IGNORECASE)

    # 3) Textbook placeholders: add a space after N/V/A (+ optional digits) when glued to particles.
    # Examples:
    # - "Nhadekimasen" -> "N ha dekimasen"
    # - "N1waN2desu"   -> "N1 wa N2 desu"
    result = re.sub(
        r"\b([NVA]\d*)(ga|wa|ha|ni|wo|o|ka|mo|no)(?=[A-Za-z~(])",
        r"\1 \2 ",
        result,
        flags=re.IGNORECASE,
    )

    # 4) If a particle is glued after a closing paren, split it: "(kotoba)ga" -> "(kotoba) ga"
    result = re.sub(
        r"\)(ga|wa|ha|ni|wo|o|ka|mo|no)\b",
        r") \1",
        result,
        flags=re.IGNORECASE,
    )

    # 5) If a particle is glued to the following token, add a space: "gaDekimasu" -> "ga Dekimasu"
    # Additionally, split common particles when they appear between letters:
    # - "watashiwagakusei" -> "watashi wa gakusei"
    # Keep this list intentionally small to avoid breaking normal words like "kotoba".
    result = re.sub(r"([a-z])wa([a-z])", r"\1 wa \2", result, flags=re.IGNORECASE)
    result = re.sub(r"([a-z])ga([a-z])", r"\1 ga \2", result, flags=re.IGNORECASE)
    result = re.sub(r"([a-z])ha([a-z])", r"\1 ha \2", result, flags=re.IGNORECASE)

    # Split additional common particles when they appear between letters.
    # Use conservative rules to avoid breaking ordinary words like "nihongo".
    result = re.sub(r"([a-z])ni([a-z])", r"\1 ni \2", result, flags=re.IGNORECASE)
    result = re.sub(r"([a-z])mo([a-z])", r"\1 mo \2", result, flags=re.IGNORECASE)
    # "de" particle, but avoid splitting:
    # - the verb stem in "dekimasu/dekimasen"
    # - "desu/deshita" (copula)
    result = re.sub(r"([a-z])de(?!ki)(?!s)([a-z])", r"\1 de \2", result, flags=re.IGNORECASE)

    # Question marker "ka" at end of a token: "desuka" -> "desu ka"
    result = re.sub(r"([a-z])ka\b", r"\1 ka", result, flags=re.IGNORECASE)

    # 6) Ensure space before common polite endings when glued: "dekimasu" / "dekimasen" / "desu" / "masu" / "masen"
    # - Keep "dekimasu/dekimasen" intact (do NOT split into "deki masu").
    result = re.sub(r"([a-z])(dekimasu|dekimasen)\b", r"\1 \2", result, flags=re.IGNORECASE)

    # - Then split the shorter endings when glued, but avoid matching inside "dekimasu/dekimasen".
    result = re.sub(r"([a-z])(?<!deki)masu\b", r"\1 masu", result, flags=re.IGNORECASE)
    result = re.sub(r"([a-z])(?<!deki)masen\b", r"\1 masen", result, flags=re.IGNORECASE)
    result = re.sub(r"([a-z])desu\b", r"\1 desu", result, flags=re.IGNORECASE)
    result = re.sub(r"([a-z])deshita\b", r"\1 deshita", result, flags=re.IGNORECASE)
    result = re.sub(r"([a-z])mashita\b", r"\1 mashita", result, flags=re.IGNORECASE)

    # Normalize multiple spaces to single space
    result = re.sub(r"\s+", " ", result)

    return result.strip()


def to_romaji_hepburn(text: Optional[str]) -> str:
    """
    Lightweight Hepburn-like transliteration for kana. Handles:
    - Basic digraphs (きゃ etc.)
    - Sokuon (っ) doubling next consonant
    - Chōon (ー) lengthening previous vowel
    - Katakana equivalents

    Note: This is a pragmatic helper for UI; not a full morphological transliterator.
    """
    if not isinstance(text, str) or not text:
        return ""
    # Mapping tables (subset sufficient for lesson UI)
    digraphs = {
        "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo",
        "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
        "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho",
        "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
        "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
        "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
        "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
        "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
        "じゃ": "ja",  "じゅ": "ju",  "じょ": "jo",
        "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
        "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
        "キャ": "kya", "キュ": "kyu", "キョ": "kyo",
        "シャ": "sha", "シュ": "shu", "ショ": "sho",
        "チャ": "cha", "チュ": "chu", "チョ": "cho",
        "ニャ": "nya", "ニュ": "nyu", "ニョ": "nyo",
        "ヒャ": "hya", "ヒュ": "hyu", "ヒョ": "hyo",
        "ミャ": "mya", "ミュ": "myu", "ミョ": "myo",
        "リャ": "rya", "リュ": "ryu", "リョ": "ryo",
        "ギャ": "gya", "ギュ": "gyu", "ギョ": "gyo",
        "ジャ": "ja",  "ジュ": "ju",  "ジョ": "jo",
        "ビャ": "bya", "ビュ": "byu", "ビョ": "byo",
        "ピャ": "pya", "ピュ": "pyu", "ピョ": "pyo",
    }
    base = {
        "あ":"a","い":"i","う":"u","え":"e","お":"o",
        "か":"ka","き":"ki","く":"ku","け":"ke","こ":"ko",
        "さ":"sa","し":"shi","す":"su","せ":"se","そ":"so",
        "た":"ta","ち":"chi","つ":"tsu","て":"te","と":"to",
        "な":"na","に":"ni","ぬ":"nu","ね":"ne","の":"no",
        "は":"ha","ひ":"hi","ふ":"fu","へ":"he","ほ":"ho",
        "ま":"ma","み":"mi","む":"mu","め":"me","も":"mo",
        "や":"ya","ゆ":"yu","よ":"yo",
        "ら":"ra","り":"ri","る":"ru","れ":"re","ろ":"ro",
        "わ":"wa","を":"o","ん":"n",
        "が":"ga","ぎ":"gi","ぐ":"gu","げ":"ge","ご":"go",
        "ざ":"za","じ":"ji","ず":"zu","ぜ":"ze","ぞ":"zo",
        "だ":"da","ぢ":"ji","づ":"zu","で":"de","ど":"do",
        "ば":"ba","び":"bi","ぶ":"bu","べ":"be","ぼ":"bo",
        "ぱ":"pa","ぴ":"pi","ぷ":"pu","ぺ":"pe","ぽ":"po",
        "ぁ":"a","ぃ":"i","ぅ":"u","ぇ":"e","ぉ":"o",
        "ア":"a","イ":"i","ウ":"u","エ":"e","オ":"o",
        "カ":"ka","キ":"ki","ク":"ku","ケ":"ke","コ":"ko",
        "サ":"sa","シ":"shi","ス":"su","セ":"se","ソ":"so",
        "タ":"ta","チ":"chi","ツ":"tsu","テ":"te","ト":"to",
        "ナ":"na","ニ":"ni","ヌ":"nu","ネ":"ne","ノ":"no",
        "ハ":"ha","ヒ":"hi","フ":"fu","ヘ":"he","ホ":"ho",
        "マ":"ma","ミ":"mi","ム":"mu","メ":"me","モ":"mo",
        "ヤ":"ya","ユ":"yu","ヨ":"yo",
        "ラ":"ra","リ":"ri","ル":"ru","レ":"re","ロ":"ro",
        "ワ":"wa","ヲ":"o","ン":"n",
        "ガ":"ga","ギ":"gi","グ":"gu","ゲ":"ge","ゴ":"go",
        "ザ":"za","ジ":"ji","ズ":"zu","ゼ":"ze","ゾ":"zo",
        "ダ":"da","ヂ":"ji","ヅ":"zu","デ":"de","ド":"do",
        "バ":"ba","ビ":"bi","ブ":"bu","ベ":"be","ボ":"bo",
        "パ":"pa","ピ":"pi","プ":"pu","ペ":"pe","ポ":"po",
        "ァ":"a","ィ":"i","ゥ":"u","ェ":"e","ォ":"o",
        "ー":"-",
    }
    out: list[str] = []
    i = 0
    prev_last = ""
    while i < len(text):
        ch = text[i]
        pair = text[i:i+2]
        if pair in digraphs:
            rom = digraphs[pair]
            out.append(rom)
            prev_last = rom[-1]
            i += 2
            continue
        if ch in ("っ", "ッ"):
            if i + 1 < len(text):
                nxt_pair = text[i+1:i+3]
                if nxt_pair in digraphs:
                    out.append(digraphs[nxt_pair][0])
                else:
                    nxt = base.get(text[i+1], "")
                    if nxt:
                        out.append(nxt[0])
            i += 1
            continue
        if ch == "ー":
            if out and prev_last in "aeiou":
                out.append(prev_last)
            i += 1
            continue
        rom = base.get(ch)
        if rom:
            out.append(rom)
            prev_last = rom[-1]
        else:
            out.append(ch)
            prev_last = ch[-1] if ch else ""
        i += 1
    return "".join(out).replace("-", "")


