import pytest

from app.models.multilingual import JapaneseText, FuriganaSegment, VocabularyEntry
from app.core.japanese_utils import fallback_multilingual


class TestJapaneseTextValidation:
    def test_furigana_requires_ruby_on_kanji(self):
        with pytest.raises(ValueError):
            JapaneseText(
                kanji="日本語",
                romaji="nihongo",
                furigana=[
                    FuriganaSegment(text="日本", ruby=None),  # missing ruby for kanji
                    FuriganaSegment(text="語", ruby="ご"),
                ],
                translation="Japanese",
            )

    def test_furigana_coverage_must_match(self):
        with pytest.raises(ValueError):
            JapaneseText(
                kanji="日本語",
                romaji="nihongo",
                furigana=[
                    FuriganaSegment(text="日本", ruby="にほん"),
                    FuriganaSegment(text="語X", ruby="ご"),  # extra character
                ],
                translation="Japanese",
            )

    def test_valid_japanese_text(self):
        jt = JapaneseText(
            kanji="日本語",
            romaji="nihongo",
            furigana=[
                FuriganaSegment(text="日本", ruby="にほん"),
                FuriganaSegment(text="語", ruby="ご"),
            ],
            translation="Japanese",
        )
        assert jt.romaji == "nihongo"  # normalized lowercase


class TestFallbackMultilingual:
    def test_fallback_multilingual_produces_valid_japanese_text(self):
        data = fallback_multilingual("日本語です")
        # Should validate as JapaneseText
        jt = JapaneseText.model_validate(data)
        assert jt.kanji == "日本語です"
        assert isinstance(jt.furigana, list) and len(jt.furigana) > 0
        # Ensure translation placeholder is non-empty
        assert jt.translation


class TestVocabularyEntry:
    def test_vocab_reading_must_be_kana(self):
        with pytest.raises(ValueError):
            VocabularyEntry(surface="日本", reading="nihon", pos="noun")

        ok = VocabularyEntry(surface="日本", reading="にほん", pos="noun")
        assert ok.pos == "noun"

    def test_vocab_pos_whitelist_and_mapping(self):
        # Abbreviation mapping
        ve = VocabularyEntry(surface="速い", reading="はやい", pos="adj")
        assert ve.pos == "adjective"

        # Invalid POS
        with pytest.raises(ValueError):
            VocabularyEntry(surface="X", reading="えっくす", pos="foo")


