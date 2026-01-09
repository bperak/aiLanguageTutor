import pytest

from app.utils.json_helpers import parse_json_object


def test_coerce_to_json_obj_parses_plain_json_string_expected_use() -> None:
    raw = (
        '{"learning_goals": ["a", "b"], "previous_knowledge": {}, '
        '"learning_experiences": {}, "usage_context": {}}'
    )
    obj = parse_json_object(raw)
    assert obj["learning_goals"] == ["a", "b"]


def test_coerce_to_json_obj_parses_markdown_fenced_json_edge_case() -> None:
    raw = """```json
{
  "learning_goals": ["travel"],
  "previous_knowledge": {},
  "learning_experiences": {},
  "usage_context": {}
}
```"""
    obj = parse_json_object(raw)
    assert obj["learning_goals"] == ["travel"]


def test_coerce_to_json_obj_raises_on_non_json_failure_case() -> None:
    with pytest.raises(ValueError):
        parse_json_object("not json at all")


