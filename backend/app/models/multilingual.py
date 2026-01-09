"""
Pydantic models for two-stage lesson generation with multilingual support.

Stage 1 models: Simple content structure (plain Japanese text)
Stage 2 models: Multilingual structure (kanji, romaji, furigana, translation)
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import List, Optional, Union, Literal
import re


# ========== STAGE 1 MODELS (Simple Content) ==========

_META_PHRASE_BLOCKLIST = [
    # English meta
    r"\bIntroduce the lesson\b",
    r"\bIntroduce the topic\b",
    r"\bTeach key vocabulary\b",
    r"\bstudentTask\b",
    r"\bteacherNotes\b",
    r"\bExplain the grammar\b",
    r"\bPractice the dialogue\b",
    # Occasional shortened forms
    r"\bIntroduce\b",
    r"\bTeach\b",
    r"\bExplain\b",
]


def _contains_japanese(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return bool(re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", text))


class ContentLessonStep(BaseModel):
    """Learner-facing lesson plan step (Japanese only, no teacher meta)."""
    title: str = Field(
        ..., min_length=3,
        description=(
            "短い見出し（3文字以上）。レッスンの流れを示すタイトル。"
        ),
        examples=["導入", "語彙ウォームアップ", "文法ミニレッスン", "会話タスクへ橋渡し"],
    )
    contentJP: str = Field(
        ..., min_length=120,
        description=(
            "学習者に直接語りかける日本語本文（120文字以上）。教師向けメタ語句は禁止"
            "（例: Introduce/Teach/studentTask/teacherNotes/Explain など）。"
        ),
        examples=[
            "今日の目標は、よく知っている人の性格を具体的な出来事と一緒に紹介できるようになることです。まずは短い例で…"
        ],
    )
    goalsJP: Optional[str] = Field(
        default=None, min_length=20,
        description="任意：到達目標の日本語要約（20文字以上）。",
        examples=["友人に、身近な人の性格と印象的なエピソードを自然に伝えられる。"],
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("contentJP")
    @classmethod
    def _validate_contentjp(cls, v: str) -> str:
        if not _contains_japanese(v or ""):
            raise ValueError("contentJP_must_contain_japanese")
        for pat in _META_PHRASE_BLOCKLIST:
            if re.search(pat, v, flags=re.IGNORECASE):
                raise ValueError("contentJP_meta_forbidden")
        return v


class SimpleReading(BaseModel):
    """Reading section with plain Japanese text."""
    title: str = Field(..., min_length=2)
    text: str = Field(..., min_length=250)
    # Optional Q&A support
    # Each item: { q: str, a: str }
    questions: Optional[List[dict]] = None
    
    model_config = ConfigDict(extra="ignore")


class SimpleDialogueTurn(BaseModel):
    """Single dialogue turn with plain text."""
    speaker: str = Field(..., min_length=1)
    text: str = Field(..., min_length=2)
    
    model_config = ConfigDict(extra="ignore")


class SimpleGrammarPoint(BaseModel):
    """Grammar point with plain example sentences."""
    pattern: str = Field(..., min_length=2)
    explanation: str = Field(..., min_length=5)
    examples: List[str] = Field(..., min_length=2)
    
    model_config = ConfigDict(extra="ignore")


class SimplePracticeExercise(BaseModel):
    """Practice exercise with basic structure."""
    type: str
    instruction: str = Field(..., min_length=5)
    content: str = Field(..., min_length=3)
    
    model_config = ConfigDict(extra="ignore")


class SimpleCultureNote(BaseModel):
    """Cultural note about the topic."""
    title: str = Field(..., min_length=3)
    content: str = Field(..., min_length=20)
    oneSentenceEN: Optional[str] = None
    
    model_config = ConfigDict(extra="ignore")


class Stage1ClozeItem(BaseModel):
    prompt: str
    choices: List[str] = Field(..., min_length=3, max_length=5)
    answer: str
    explanation: Optional[str] = None


class Stage1PracticeCloze(BaseModel):
    type: Literal["cloze"] = "cloze"
    instruction: str = Field(..., min_length=5)
    items: List[Stage1ClozeItem] = Field(..., min_length=3)


class Stage1MatchingPair(BaseModel):
    jp: str
    en: str
    id: str


class Stage1PracticeMatching(BaseModel):
    type: Literal["matching"] = "matching"
    instruction: str = Field(..., min_length=5)
    pairs: List[Stage1MatchingPair] = Field(..., min_length=4)
    correctMapping: Optional[List[List[str]]] = None


class Stage1DialogueGapItem(BaseModel):
    prompt: str
    given: List[str] = Field(default_factory=list)
    answers: List[str] = Field(default_factory=list)


class Stage1PracticeDialogueGap(BaseModel):
    type: Literal["dialogueGap"] = "dialogueGap"
    instruction: str = Field(..., min_length=5)
    items: List[Stage1DialogueGapItem] = Field(..., min_length=2)


class Stage1Content(BaseModel):
    """Complete Stage 1 lesson content with simple structure."""
    objective: Optional[str] = None
    topic: Optional[str] = None
    level: Optional[str] = None
    lessonPlan: List[ContentLessonStep] = Field(
        ..., min_length=4, max_length=4,
        description=(
            "レッスンプラン（厳密に4つの段階）。各段階は学習者向けの日本語本文で、"
            "教師向けメタ指示は禁止。導入はCandoの説明を短く含める。"
        ),
    )
    reading: SimpleReading
    dialogue: List[SimpleDialogueTurn] = Field(..., min_length=6)
    grammar: List[SimpleGrammarPoint] = Field(..., min_length=3, max_length=3)
    # Allow richer practice cards while remaining backward compatible
    practice: List[Union[
        Stage1PracticeCloze,
        Stage1PracticeMatching,
        Stage1PracticeDialogueGap,
        SimplePracticeExercise
    ]] = Field(..., min_length=3)
    culture: List[SimpleCultureNote] = Field(..., min_length=2)
    
    model_config = ConfigDict(strict=True, extra="forbid")

    @field_validator("lessonPlan")
    @classmethod
    def _enforce_lesson_plan_len(cls, v: List[ContentLessonStep]) -> List[ContentLessonStep]:
        if len(v) != 4:
            raise ValueError("lessonPlan must contain exactly 4 steps")
        return v

    @field_validator("dialogue")
    @classmethod
    def _enforce_dialogue_len(cls, v: List[SimpleDialogueTurn]) -> List[SimpleDialogueTurn]:
        if not (6 <= len(v) <= 8):
            raise ValueError("dialogue must contain 6 to 8 turns")
        return v

    @field_validator("grammar")
    @classmethod
    def _enforce_grammar_len(cls, v: List[SimpleGrammarPoint]) -> List[SimpleGrammarPoint]:
        if len(v) != 3:
            raise ValueError("grammar must contain exactly 3 points")
        return v

    @field_validator("practice")
    @classmethod
    def _enforce_practice_cards(cls, v: List[object]) -> List[object]:
        if len(v) != 3:
            raise ValueError("practice must contain exactly 3 cards: cloze, matching, dialogueGap")
        return v

    @field_validator("culture")
    @classmethod
    def _enforce_culture_len(cls, v: List[SimpleCultureNote]) -> List[SimpleCultureNote]:
        if not (2 <= len(v) <= 3):
            raise ValueError("culture must contain 2 to 3 notes")
        return v


# ========== STAGE 2 MODELS (Multilingual Structure) ==========

class FuriganaSegment(BaseModel):
    """Single furigana segment."""
    text: str
    ruby: Optional[str] = None
    
    model_config = ConfigDict(extra="ignore")


class JapaneseText(BaseModel):
    """Multilingual Japanese text structure."""
    kanji: str = Field(..., min_length=1)
    romaji: str = Field(..., min_length=1)
    furigana: List[FuriganaSegment] = Field(..., min_length=1)
    translation: str = Field(..., min_length=1)
    
    model_config = ConfigDict(extra="ignore")

    @field_validator("romaji")
    @classmethod
    def _normalize_romaji(cls, v: str) -> str:
        # Collapse multiple spaces, trim, and lowercase for consistency
        return " ".join((v or "").split()).lower()

    @model_validator(mode="after")
    def _validate_furigana_coverage(self):  # type: ignore[override]
        kanji_text = (self.kanji or "").replace(" ", "")
        joined = "".join(seg.text for seg in (self.furigana or []))
        if joined.replace(" ", "") != kanji_text:
            raise ValueError("furigana coverage must exactly cover kanji text")
        # Ensure ruby provided for segments with any Kanji
        for seg in self.furigana or []:
            if any('\u4e00' <= ch <= '\u9fff' for ch in seg.text):
                if not seg.ruby:
                    raise ValueError("ruby is required for furigana segments containing kanji")
        return self


class ComprehensionQA(BaseModel):
    q: str
    a: str
    evidenceSpan: Optional[str] = None


class ReadingSection(BaseModel):
    """Reading section with multilingual structure."""
    title: JapaneseText
    content: JapaneseText
    comprehension: List[ComprehensionQA] = Field(default_factory=list, min_length=1)
    
    model_config = ConfigDict(extra="ignore")


class DialogueTurn(BaseModel):
    """Single dialogue turn with multilingual structure."""
    speaker: str
    japanese: JapaneseText
    notes: Optional[str] = None
    
    model_config = ConfigDict(extra="ignore")


class DialogueCard(BaseModel):
    """Dialogue card with contextual setting and optional multi-speaker cast.

    This model is used for Stage 2 (multilingual) dialogue content and is
    designed to be backward compatible with existing dialogue rendering. The
    `setting` provides a narrative paragraph that frames the conversation
    (place, people, motives), and `characters` enables 2+ named speakers.
    """
    title: Optional[Union[str, JapaneseText]] = None
    setting: Optional[str] = Field(default=None, description="Contextual opening paragraph for the dialogue scene")
    characters: Optional[List[str]] = Field(default=None, description="List of character names participating in the dialogue")
    dialogue_turns: List[DialogueTurn] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class GrammarPoint(BaseModel):
    """Grammar point with multilingual examples."""
    pattern: str
    explanation: str
    examples: List[JapaneseText] = Field(..., min_length=2)
    
    model_config = ConfigDict(extra="ignore")


# ========== BATCH VALIDATION MODELS ==========

class Stage2DialogueTurnList(BaseModel):
    """Batch validation for multiple dialogue turns."""
    turns: List[DialogueTurn] = Field(..., min_length=1)
    
    model_config = ConfigDict(extra="ignore")


class GrammarPointList(BaseModel):
    """Batch validation for multiple grammar points."""
    points: List[GrammarPoint] = Field(..., min_length=1)
    
    model_config = ConfigDict(extra="ignore")


class CultureNoteML(BaseModel):
    """Stage 2 multilingual culture note."""
    title: str
    body: JapaneseText
    
    model_config = ConfigDict(extra="ignore")


class CultureNoteList(BaseModel):
    """Batch validation for multiple culture notes."""
    notes: List[CultureNoteML] = Field(..., min_length=1)
    
    model_config = ConfigDict(extra="ignore")


# ========== OPTIONAL VOCABULARY MODEL ==========

_POS_WHITELIST = {
    "noun",
    "verb",
    "adjective",
    "adverb",
    "particle",
    "pronoun",
    "conjunction",
    "interjection",
    "counter",
    "expression",
}


def _is_kana(s: str) -> bool:
    return all(("\u3040" <= ch <= "\u30ff") or ch.isspace() for ch in (s or ""))


class VocabularyEntry(BaseModel):
    """Validated vocabulary entry for extracted entities.

    Ensures kana/kanji coherence and POS whitelist.
    """

    surface: str = Field(..., min_length=1)
    reading: str = Field(..., min_length=1)
    pos: str = Field(..., min_length=2)
    translation: Optional[str] = None

    model_config = ConfigDict(extra="ignore")

    @field_validator("pos")
    @classmethod
    def _normalize_pos(cls, v: str) -> str:
        p = (v or "").strip().lower()
        if p and p not in _POS_WHITELIST:
            # Map common abbreviations
            mapping = {
                "adj": "adjective",
                "adv": "adverb",
                "n": "noun",
                "v": "verb",
                "prt": "particle",
                # Japanese POS labels → English
                "名詞": "noun",
                "動詞": "verb",
                "形容詞": "adjective",
                "副詞": "adverb",
                "助詞": "particle",
                "代名詞": "pronoun",
                "接続詞": "conjunction",
                "感動詞": "interjection",
                "助数詞": "counter",
                "表現": "expression",
            }
            p = mapping.get(p, p)
        if p not in _POS_WHITELIST:
            raise ValueError("pos not in whitelist")
        return p

    @model_validator(mode="after")
    def _validate_reading(self):  # type: ignore[override]
        # Reading must be kana (hiragana/katakana)
        if not _is_kana(self.reading):
            raise ValueError("reading must be kana (hiragana/katakana)")
        return self


# ========== FIXED PHRASE / CONVERSATIONAL MOTIF MODELS ==========

class FixedPhrase(BaseModel):
    """Fixed phrase or conversational motif for a specific situation.
    
    These are idiomatic expressions, common phrases, or formulaic language
    patterns that are essential for natural conversation in a given context.
    """
    phrase: JapaneseText = Field(..., description="The fixed phrase in multilingual format")
    usage_note: Optional[str] = Field(
        default=None,
        description="Optional note about when/how to use this phrase (e.g., 'formal', 'casual', 'when greeting')"
    )
    register: Optional[str] = Field(
        default=None,
        description="Formality level: 'formal', 'casual', 'polite', 'humble', etc."
    )
    
    model_config = ConfigDict(extra="ignore")


class FixedPhraseList(BaseModel):
    """Batch validation for multiple fixed phrases."""
    phrases: List[FixedPhrase] = Field(..., min_length=1)
    
    model_config = ConfigDict(extra="ignore")