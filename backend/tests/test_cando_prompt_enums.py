from types import SimpleNamespace

from scripts.canDo_creation_new import (
    AIComprehensionTutorCard,
    validate_or_repair,
    _literal_choices,
    build_comprehension_exercises_prompt,
    build_interaction_activities_prompt,
    build_production_exercises_prompt,
    ComprehensionExerciseItem,
    InteractionActivityItem,
    ProductionExerciseItem,
)


def _plan_stub() -> SimpleNamespace:
    """
    Create a minimal plan stub with the fields the prompt builders expect.
    """
    return SimpleNamespace(
        communicative_function_en="Ordering food at a café",
        communicative_function_ja="カフェで注文する",
        level="A1",
        evaluation=SimpleNamespace(success_criteria=["Polite, clear order"]),
        grammar_functions=[SimpleNamespace(id="g1")],
        scenarios=[SimpleNamespace(name="Coffee shop")],
    )


def test_comprehension_prompt_uses_literal_types() -> None:
    """
    Ensure comprehension prompt lists only the schema Literal exercise types.
    """
    plan = _plan_stub()
    _, user_prompt = build_comprehension_exercises_prompt("en", plan)
    expected_types = _literal_choices(ComprehensionExerciseItem, "exercise_type")

    for exercise_type in expected_types:
        assert exercise_type in user_prompt


def test_production_prompt_uses_literal_types() -> None:
    """
    Ensure production prompt lists only the schema Literal exercise types and avoids outdated names.
    """
    plan = _plan_stub()
    _, user_prompt = build_production_exercises_prompt("en", plan)
    expected_types = _literal_choices(ProductionExerciseItem, "exercise_type")

    for exercise_type in expected_types:
        assert exercise_type in user_prompt

    assert "sentence_transformation" not in user_prompt
    assert "writing_prompt" not in user_prompt


def test_interaction_prompt_uses_literal_types() -> None:
    """
    Ensure interaction prompt lists only the schema Literal activity types and avoids outdated names.
    """
    plan = _plan_stub()
    _, user_prompt = build_interaction_activities_prompt("en", plan)
    expected_types = _literal_choices(InteractionActivityItem, "activity_type")

    for activity_type in expected_types:
        assert activity_type in user_prompt

    assert "conversation_scenarios" not in user_prompt
    assert "collaborative_tasks" not in user_prompt
    assert "real_world_simulations" not in user_prompt


def test_ai_comprehension_tutor_question_must_be_jptext() -> None:
    """
    AIComprehensionTutorCard prompt should ensure LLM generates JPText for question field.
    Test verifies that correct JPText structure is generated (not testing auto-fix).
    """

    def fake_llm(_sys: str, _usr: str) -> str:
        # LLM should generate correct JPText structure based on improved prompt
        return (
            '{"type":"AIComprehensionTutorCard","title":{"en":"t","ja":"t"},'
            '"stages":[{"stage_id":"s1","goal_en":"g",'
            '"question":{"std":"質問","furigana":"しつもん","romaji":"shitsumon","translation":{"en":"question"}},'
            '"expected_answer_keywords":["k"],"hints":[{"en":"h","ja":"h"}],"ai_feedback":{"rubric":"r"}}]}'
        )

    card = validate_or_repair(
        fake_llm, AIComprehensionTutorCard, "sys", "usr", max_repair=0
    )
    q = card.stages[0].question
    assert q.std == "質問"
    assert q.furigana == "しつもん"
    assert q.romaji == "shitsumon"
    assert q.translation.get("en") == "question"


def test_comprehension_prompt_contains_jptext_exemplar() -> None:
    """
    ComprehensionExercisesCard prompt must include JPText exemplar and required keys.
    """
    plan = _plan_stub()
    _, user_prompt = build_comprehension_exercises_prompt("en", plan)
    
    # Verify JPText exemplar structure is present
    assert '"std":' in user_prompt
    assert '"furigana":' in user_prompt
    assert '"romaji":' in user_prompt
    assert '"translation":' in user_prompt
    
    # Verify required fields are mentioned
    assert '"id":' in user_prompt or "id" in user_prompt.lower()
    assert '"instructions":' in user_prompt or "instructions" in user_prompt.lower()
    assert '"question":' in user_prompt
    
    # Verify item count is reduced to 6-8
    assert "6-8" in user_prompt or "6 to 8" in user_prompt.lower()
    assert "8-12" not in user_prompt
    
    # Verify exercise_type is mentioned
    assert "exercise_type" in user_prompt


def test_production_prompt_contains_jptext_exemplar() -> None:
    """
    ProductionExercisesCard prompt must include JPText exemplar and required keys.
    """
    plan = _plan_stub()
    _, user_prompt = build_production_exercises_prompt("en", plan)
    
    # Verify JPText exemplar structure is present
    assert '"std":' in user_prompt
    assert '"furigana":' in user_prompt
    assert '"romaji":' in user_prompt
    assert '"translation":' in user_prompt
    
    # Verify required fields are mentioned
    assert '"id":' in user_prompt or "id" in user_prompt.lower()
    assert '"instructions":' in user_prompt or "instructions" in user_prompt.lower()
    assert '"prompt":' in user_prompt
    
    # Verify item count is reduced to 6-8
    assert "6-8" in user_prompt or "6 to 8" in user_prompt.lower()
    assert "10-15" not in user_prompt
    
    # Verify exercise_type is mentioned
    assert "exercise_type" in user_prompt
