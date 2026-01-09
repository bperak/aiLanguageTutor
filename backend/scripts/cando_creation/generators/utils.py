# Generator utilities
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Literal, Optional, Protocol, Tuple, Type, TypeVar, Union, get_args

from pydantic import BaseModel, ValidationError

def model_schema(model: Type[BaseModel]) -> str:
    """JSON Schema string for a Pydantic model."""
    return json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2)


def extract_first_json_block(text: str) -> str:
    """
    If a model returns extra prose, extract the first valid JSON object by brace matching.
    Falls back to original text if parsing fails.
    """
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text


T = TypeVar("T", bound=BaseModel)


def validate_or_repair(
    llm_call: Callable[[str, str], str],
    target_model: Type[T],
    system_prompt: str,
    user_prompt: str,
    max_repair: int = 2,
    fallback_data: Optional[Dict[str, Any]] = None,
) -> T:
    """
    Call LLM, extract JSON, validate against Pydantic model, repair if needed.
    
    Core logic only - no model-specific hacks, no debug logging bloat.
    If LLM generates bad JSON, fix the prompts instead of patching here.
    
    Args:
        llm_call: Function to call the LLM
        target_model: Pydantic model type to validate against
        system_prompt: System prompt for LLM
        user_prompt: User prompt for LLM
        max_repair: Maximum number of repair attempts
        fallback_data: Optional fallback data dict to use if all repairs fail
        
    Returns:
        Validated model instance
        
    Raises:
        ValidationError: If validation fails and no fallback provided
    """
    try:
        raw = llm_call(system_prompt, user_prompt)
    except Exception as e:
        # If LLM call fails and we have fallback, use it
        if fallback_data:
            try:
                return target_model.model_validate(fallback_data)
            except ValidationError:
                pass
        raise
    
    raw = extract_first_json_block(raw)

    for attempt in range(max_repair + 1):
        try:
            return target_model.model_validate_json(raw)
        except ValidationError as e:
            if attempt >= max_repair:
                # Last attempt failed - try fallback if available
                if fallback_data:
                    try:
                        return target_model.model_validate(fallback_data)
                    except ValidationError:
                        pass
                raise
            
            # Ask LLM to repair using schema and errors
            schema_str = model_schema(target_model)
            repair_user = (
                "You returned JSON that failed validation.\n"
                "SCHEMA:\n" + schema_str + "\n\n"
                "JSON_WITH_ERRORS:\n" + raw + "\n\n"
                "ERRORS:\n"
                + json.dumps(e.errors(), ensure_ascii=False, indent=2)
                + "\n\n"
                "Return a corrected JSON that fully validates. Output STRICT JSON only."
            )
            try:
                raw = llm_call(system_prompt, repair_user)
                raw = extract_first_json_block(raw)
            except Exception:
                # If repair call fails, try fallback
                if fallback_data:
                    try:
                        return target_model.model_validate(fallback_data)
                    except ValidationError:
                        pass
                raise

    # Should never reach
    return target_model.model_validate_json(raw)


class LLMFn(Protocol):
    def __call__(self, system: str, user: str) -> str: ...


def _literal_choices(model: Type[BaseModel], field_name: str) -> List[str]:
    """
    Extract Literal choices for a field to keep prompts in sync with schemas.
    """
    field = model.model_fields[field_name]
    literal_type = field.annotation
    return [choice for choice in get_args(literal_type) if isinstance(choice, str)]

