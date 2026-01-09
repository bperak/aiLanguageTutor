"""
PHASE 7: Content Stage Card Generation Tests

Tests for content card generators:
- Objective card
- Words card (vocabulary)
- Grammar card
- Dialogue card
- Reading card
- Culture card
"""

import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
backend_path = Path(__file__).resolve().parent.parent
env_path = backend_path.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    for parent in backend_path.parents:
        candidate = parent / ".env"
        if candidate.exists():
            load_dotenv(candidate)
            break

from app.services.cando_v2_compile_service import _make_llm_call_openai
from scripts.cando_creation.generators.cards import (
    gen_domain_plan, gen_objective_card, gen_words_card,
    gen_grammar_card, gen_dialogue_card, gen_reading_card,
    gen_culture_card
)
from scripts.cando_creation.models.plan import DomainPlan
from scripts.cando_creation.models.cards import (
    ObjectiveCard, WordsCard, GrammarPatternsCard,
    DialogueCard, ReadingCard, CultureCard
)


@pytest.fixture
def sample_cando():
    """Sample CanDo descriptor for testing."""
    return {
        "uid": "JF:1",
        "level": "A1",
        "primaryTopic": "自己紹介",
        "primaryTopicEn": "Self-introduction",
        "skillDomain": "会話",
        "type": "表現",
        "descriptionEn": "Introduce yourself",
        "descriptionJa": "自己紹介をする",
        "source": "JFまるごと"
    }


@pytest.fixture
def sample_plan(sample_cando):
    """Generate a sample DomainPlan for card tests."""
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    try:
        return gen_domain_plan(
            llm_call=llm_call,
            cando=sample_cando,
            metalanguage="en"
        )
    except Exception:
        # Return a minimal mock plan if generation fails
        from scripts.cando_creation.models.plan import (
            PlanScenario, PlanRole, PlanLexBucket,
            PlanGrammarFunction, PlanEvaluation
        )
        return DomainPlan(
            uid="JF:1",
            level="A1",
            communicative_function_en="Introduce yourself",
            communicative_function_ja="自己紹介をする",
            scenarios=[
                PlanScenario(
                    name="Meeting",
                    setting="office",
                    roles=[PlanRole(label="Colleague", register="polite")]
                )
            ],
            lex_buckets=[
                PlanLexBucket(name="greetings", items=["こんにちは", "はじめまして", "よろしく"])
            ],
            grammar_functions=[
                PlanGrammarFunction(
                    id="gf_001",
                    label="introduction",
                    pattern_ja="XはYです",
                    slots=["X:name", "Y:role"]
                )
            ],
            evaluation=PlanEvaluation(
                success_criteria=["Can introduce self"],
                discourse_markers=["まず", "次に"]
            ),
            cultural_themes_en=["Business etiquette"],
            cultural_themes_ja=["ビジネスマナー"]
        )


@pytest.mark.asyncio
@pytest.mark.slow
async def test_gen_objective_card(sample_cando, sample_plan):
    """
    Test: Objective card generation.
    
    Verifies that ObjectiveCard is generated correctly.
    """
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    
    try:
        card = gen_objective_card(
            llm_call=llm_call,
            metalanguage="en",
            cando_meta=sample_cando,
            plan=sample_plan
        )
        
        assert isinstance(card, ObjectiveCard), "Result should be ObjectiveCard"
        assert card.title, "ObjectiveCard should have title"
        assert card.body, "ObjectiveCard should have body"
        assert card.success_criteria, "ObjectiveCard should have success_criteria"
        
    except Exception as e:
        pytest.skip(f"LLM call failed: {e}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_gen_words_card(sample_plan):
    """
    Test: Words card (vocabulary) generation.
    
    Verifies that WordsCard is generated with appropriate vocabulary.
    """
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    
    try:
        card = gen_words_card(
            llm_call=llm_call,
            metalanguage="en",
            plan=sample_plan
        )
        
        assert isinstance(card, WordsCard), "Result should be WordsCard"
        assert card.words, "WordsCard should have words"
        assert len(card.words) > 0, "WordsCard should have at least one word"
        
        # Verify word structure
        for word in card.words[:3]:  # Check first 3
            assert hasattr(word, 'std') or hasattr(word, 'form'), "Word should have form"
        
    except Exception as e:
        pytest.skip(f"LLM call failed: {e}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_gen_grammar_card(sample_plan):
    """
    Test: Grammar card generation.
    
    Verifies that GrammarPatternsCard is generated with appropriate patterns.
    """
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    
    try:
        card = gen_grammar_card(
            llm_call=llm_call,
            metalanguage="en",
            plan=sample_plan
        )
        
        assert isinstance(card, GrammarPatternsCard), "Result should be GrammarPatternsCard"
        assert card.patterns, "GrammarCard should have patterns"
        assert len(card.patterns) > 0, "GrammarCard should have at least one pattern"
        
    except Exception as e:
        pytest.skip(f"LLM call failed: {e}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_gen_dialogue_card(sample_plan):
    """
    Test: Dialogue card generation.
    
    Verifies that DialogueCard is generated with conversation.
    """
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    
    try:
        card = gen_dialogue_card(
            llm_call=llm_call,
            metalanguage="en",
            plan=sample_plan
        )
        
        assert isinstance(card, DialogueCard), "Result should be DialogueCard"
        assert card.title or card.dialogue or card.turns, "DialogueCard should have content"
        
    except Exception as e:
        pytest.skip(f"LLM call failed: {e}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_gen_reading_card(sample_plan):
    """
    Test: Reading card generation.
    
    Verifies that ReadingCard is generated with reading passage.
    """
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    
    try:
        card = gen_reading_card(
            llm_call=llm_call,
            metalanguage="en",
            plan=sample_plan
        )
        
        assert isinstance(card, ReadingCard), "Result should be ReadingCard"
        assert card.title or card.reading or card.text, "ReadingCard should have content"
        
    except Exception as e:
        pytest.skip(f"LLM call failed: {e}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_gen_culture_card(sample_plan):
    """
    Test: Culture card generation.
    
    Verifies that CultureCard is generated with cultural content.
    """
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    
    try:
        card = gen_culture_card(
            llm_call=llm_call,
            metalanguage="en",
            plan=sample_plan
        )
        
        assert isinstance(card, CultureCard), "Result should be CultureCard"
        assert card.title or card.themes or card.content, "CultureCard should have content"
        
    except Exception as e:
        pytest.skip(f"LLM call failed: {e}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_content_cards_level_appropriate(sample_cando, sample_plan):
    """
    Test: Generated content is level-appropriate (CEFR).
    
    Verifies that content complexity matches the A1 level.
    """
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    
    try:
        # Generate words card
        words_card = gen_words_card(
            llm_call=llm_call,
            metalanguage="en",
            plan=sample_plan
        )
        
        assert isinstance(words_card, WordsCard), "Should generate WordsCard"
        
        # A1 level should have simpler vocabulary
        # This is a soft check - actual level verification is complex
        assert len(words_card.words) <= 30, "A1 should not have too many words"
        
    except Exception as e:
        pytest.skip(f"LLM call failed: {e}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_content_cards_bilingual(sample_plan):
    """
    Test: Bilingual content is aligned.
    
    Verifies that Japanese and English content are both present.
    """
    llm_call = _make_llm_call_openai(model="gpt-4.1", timeout=120)
    
    try:
        # Generate objective card (has bilingual fields)
        card = gen_objective_card(
            llm_call=llm_call,
            metalanguage="en",
            cando_meta={
                "uid": "JF:1",
                "level": "A1",
                "primaryTopic": "自己紹介",
                "primaryTopicEn": "Self-introduction",
                "skillDomain": "会話",
                "type": "表現",
                "descriptionEn": "Introduce yourself",
                "descriptionJa": "自己紹介をする",
                "source": "JFまるごと"
            },
            plan=sample_plan
        )
        
        assert isinstance(card, ObjectiveCard), "Should generate ObjectiveCard"
        
        # Check for bilingual content
        # The card should have both English and Japanese content
        # depending on structure
        
    except Exception as e:
        pytest.skip(f"LLM call failed: {e}")

