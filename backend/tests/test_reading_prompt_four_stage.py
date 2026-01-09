from types import SimpleNamespace


def test_build_reading_prompt_mentions_four_stage_and_notes_en_sections():
    # Import locally to avoid test collection side-effects if module is heavy.
    from scripts.canDo_creation_new import build_reading_prompt

    # Minimal stubs – build_reading_prompt only reads a few attributes.
    plan = SimpleNamespace(lex_buckets=[], grammar_functions=[])
    dialog = SimpleNamespace(
        setting="test-setting",
        characters=["A", "B"],
        turns=[
            SimpleNamespace(speaker="A", ja=SimpleNamespace(std="こんにちは")),
            SimpleNamespace(speaker="B", ja=SimpleNamespace(std="こんにちは")),
        ],
    )
    cando = {
        "uid": "TEST:1",
        "level": "A1",
        "primaryTopic": "テスト",
        "primaryTopicEn": "Test",
        "skillDomain": "産出",
        "type": "活動",
        "descriptionEn": "desc",
        "descriptionJa": "説明",
    }

    _sys, user = build_reading_prompt("en", cando, plan, dialog)

    assert "STAGE 1" in user
    assert "STAGE 2" in user
    assert "STAGE 3" in user
    assert "STAGE 4" in user
    assert "notes_en" in user
    assert "PRODUCTION:" in user
    assert "INTERACTION:" in user


