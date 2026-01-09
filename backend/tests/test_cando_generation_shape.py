"""
Lightweight shape regression tests for CanDo generation scaffolding.

These tests use the validate_or_repair pipeline with deterministic fake LLM
responses to ensure the newest prompt/repair rules keep key JPText and enum
fields well-formed. They run fast and can be invoked to check regressions in
prompt design or repair logic without calling real models.
"""

from types import SimpleNamespace

from scripts.canDo_creation_new import (
    AIComprehensionTutorCard,
    InteractionActivitiesCard,
    ProductionExercisesCard,
    validate_or_repair,
)


def _plan_stub() -> SimpleNamespace:
    return SimpleNamespace(
        communicative_function_en="Ordering food at a café",
        communicative_function_ja="カフェで注文する",
        level="A1",
        evaluation=SimpleNamespace(success_criteria=["Polite, clear order"]),
        grammar_functions=[SimpleNamespace(id="g1")],
        scenarios=[SimpleNamespace(name="Coffee shop")],
    )


def test_ai_comprehension_tutor_question_autofix() -> None:
    """String question should be auto-wrapped into JPText."""

    def fake_llm(_sys: str, _usr: str) -> str:
        return (
            '{"type":"AIComprehensionTutorCard","title":{"en":"t","ja":"t"},'
            '"stages":[{"stage_id":"s1","goal_en":"g","question":"質問",'
            '"expected_answer_keywords":["k"],"hints":[{"en":"h","ja":"h"}],"ai_feedback":{"rubric":"r"}}]}'
        )

    card = validate_or_repair(
        fake_llm, AIComprehensionTutorCard, "sys", "usr", max_repair=0
    )
    q = card.stages[0].question
    assert q.std == "質問"
    assert q.translation.get("en") == "質問"
    assert q.furigana
    assert q.romaji


def test_production_exercises_enum_and_jptext_guardrail() -> None:
    """Production exercises should keep exercise_type literal and JPText payloads."""

    def fake_llm(_sys: str, _usr: str) -> str:
        return (
            '{"type":"ProductionExercisesCard","title":{"en":"t","ja":"t"},'
            '"items":[{"exercise_type":"sentence_construction","id":"ex1",'
            '"instructions":{"en":"Write","ja":"書く"},'
            '"prompt":{"std":"カフェで注文してください","furigana":"カフェで注文してください","romaji":"kafe de chuumon shite kudasai",'
            '"translation":{"en":"Order at the cafe"}}}]}'
        )

    card = validate_or_repair(
        fake_llm, ProductionExercisesCard, "sys", "usr", max_repair=0
    )
    item = card.items[0]
    assert item.exercise_type == "sentence_construction"
    assert item.prompt.translation["en"]


def test_interaction_activities_enum_guardrail() -> None:
    """Interaction activities keep enum and bilingual instructions."""

    def fake_llm(_sys: str, _usr: str) -> str:
        return (
            '{"type":"InteractionActivitiesCard","title":{"en":"t","ja":"t"},'
            '"items":[{"activity_type":"role_play","id":"a1","title":{"en":"Cafe","ja":"カフェ"},'
            '"instructions":{"en":"Practice ordering","ja":"注文を練習"},'
            '"roles":["Customer","Staff"],"goals":["Order politely"]}]}'
        )

    card = validate_or_repair(
        fake_llm, InteractionActivitiesCard, "sys", "usr", max_repair=0
    )
    item = card.items[0]
    assert item.activity_type == "role_play"
    assert item.instructions["ja"]
