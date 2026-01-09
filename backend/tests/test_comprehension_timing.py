"""
Test to time comprehension exercises generation for a real lesson.
"""
import os
import sys
import time
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

# Load .env file
from dotenv import load_dotenv
env_path = backend_path.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try to find .env in parent directories
    for parent in backend_path.parents:
        candidate = parent / ".env"
        if candidate.exists():
            load_dotenv(candidate)
            break

from openai import OpenAI
from types import SimpleNamespace

from scripts.canDo_creation_new import (
    gen_comprehension_exercises_card,
    DomainPlan,
    PlanScenario,
    PlanRole,
    PlanLexBucket,
    PlanGrammarFunction,
    PlanEvaluation,
    ReadingCard,
    ReadingSection,
    ComprehensionQA,
    JPText,
)


def _make_llm_call_gpt41(model: str = "gpt-4.1", timeout: int = 120):
    """Create LLM call function using gpt-4.1."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    
    import httpx
    timeout_config = httpx.Timeout(timeout, connect=10.0)
    client = OpenAI(
        api_key=api_key,
        timeout=timeout_config,
        max_retries=2,
    )

    def llm_call(system: str, user: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
        )
        return (resp.choices[0].message.content or "").strip()

    return llm_call


def _create_test_plan() -> DomainPlan:
    """Create a minimal test plan."""
    return DomainPlan(
        uid="test_plan",
        level="A1",
        communicative_function_en="Ordering food at a café",
        communicative_function_ja="カフェで注文する",
        scenarios=[
            PlanScenario(
                name="Coffee shop",
                setting="café",
                roles=[PlanRole(label="Customer", register="polite")]
            )
        ],
        lex_buckets=[
            PlanLexBucket(name="food", items=["コーヒー", "サンドイッチ", "ケーキ"])
        ],
        grammar_functions=[
            PlanGrammarFunction(
                id="gf_001",
                label="ordering",
                pattern_ja="Xをください",
                slots=["X:item"],
                notes_en="Polite request pattern"
            )
        ],
        evaluation=PlanEvaluation(
            success_criteria=["Can order politely"],
            discourse_markers=["すみません", "お願いします"]
        ),
        cultural_themes_en=["Café etiquette"],
        cultural_themes_ja=["カフェのマナー"]
    )


def _create_test_reading() -> ReadingCard:
    """Create a minimal test reading card."""
    return ReadingCard(
        type="ReadingCard",
        title={"en": "At the Café", "ja": "カフェで"},
        reading=ReadingSection(
            title=JPText(
                std="カフェで",
                furigana="カフェで",
                romaji="kafe de",
                translation={"en": "At the Café"}
            ),
            content=JPText(
                std="カフェでコーヒーを注文しました。店員さんが「いらっしゃいませ」と言いました。私は「コーヒーをください」と答えました。",
                furigana="カフェでコーヒーをちゅうもんしました。てんいんさんが「いらっしゃいませ」といいました。わたしは「コーヒーをください」とこたえました。",
                romaji="kafe de koohii wo chuumon shimashita. tenin-san ga 'irasshaimase' to iimashita. watashi wa 'koohii wo kudasai' to kotaemashita.",
                translation={"en": "I ordered coffee at the café. The staff said 'Welcome'. I answered 'Please give me coffee'."}
            ),
            comprehension=[
                ComprehensionQA(
                    q=JPText(
                        std="どこで注文しましたか？",
                        furigana="どこでちゅうもんしましたか？",
                        romaji="doko de chuumon shimashita ka?",
                        translation={"en": "Where did you order?"}
                    ),
                    a=JPText(
                        std="カフェで",
                        furigana="カフェで",
                        romaji="kafe de",
                        translation={"en": "At the café"}
                    )
                )
            ]
        )
    )


def test_comprehension_timing():
    """Time comprehension exercises generation with gpt-4.1."""
    print("=" * 60)
    print("Testing Comprehension Exercises Generation Timing")
    print("=" * 60)
    print(f"Model: gpt-4.1")
    print()
    
    plan = _create_test_plan()
    reading = _create_test_reading()
    llm_call = _make_llm_call_gpt41(model="gpt-4.1")
    
    print("Starting comprehension exercises generation...")
    start_time = time.time()
    
    try:
        card = gen_comprehension_exercises_card(
            llm_call=llm_call,
            metalanguage="en",
            plan=plan,
            reading=reading,
            content_cards=None,
            max_repair=2,
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✓ Generation completed successfully!")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Number of exercises: {len(card.items)}")
        print(f"  Exercise types: {[item.exercise_type for item in card.items]}")
        
        return duration
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"\n✗ Generation failed after {duration:.2f} seconds")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    duration = test_comprehension_timing()
    print(f"\n{'=' * 60}")
    print(f"Total time: {duration:.2f} seconds")
    if duration < 60:
        print(f"✓ Under 60 seconds target!")
    else:
        print(f"✗ Exceeded 60 seconds target by {duration - 60:.2f} seconds")
    print(f"{'=' * 60}")

