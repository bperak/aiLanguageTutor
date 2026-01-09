"""
JSON extraction and parsing helpers for AI-generated content.

Provides robust JSON extraction with bracket balancing to handle
AI models that add extra text before or after JSON.
"""

from __future__ import annotations

import json
from typing import Any, Dict


def extract_balanced_json(content: str) -> str:
    """
    Extract JSON with proper bracket balancing.
    
    Handles common AI model issues:
    - Extra text before JSON (explanations, markdown)
    - Extra text after JSON (comments, notes)
    - Code fence wrappers (```json ... ```)
    - Language identifiers
    
    Args:
        content: Raw AI response string
        
    Returns:
        Extracted JSON string with balanced brackets
        
    Raises:
        ValueError: If no JSON found or brackets are unbalanced
    """
    content = content.strip()
    
    # Remove code fences
    if "```" in content:
        parts = content.split("```")
        for part in parts:
            part = part.strip()
            # Remove language identifiers
            for lang in ["json", "JSON", "javascript", "js"]:
                if part.startswith(lang):
                    part = part[len(lang):].strip()
            if part.startswith("{") or part.startswith("["):
                content = part
                break
    
    # Find start
    start_obj = content.find("{")
    start_arr = content.find("[")
    
    if start_obj == -1 and start_arr == -1:
        raise ValueError("No JSON found in response")
    
    # Determine which comes first
    if start_obj != -1 and (start_arr == -1 or start_obj < start_arr):
        start_char, end_char = "{", "}"
        start = start_obj
    else:
        start_char, end_char = "[", "]"
        start = start_arr
    
    # Count brackets to find balanced end
    count = 0
    in_string = False
    escape_next = False
    
    for i in range(start, len(content)):
        char = content[i]
        
        # Handle escape sequences
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        
        # Track string boundaries
        if char == '"':
            in_string = not in_string
            continue
        
        # Count brackets only outside strings
        if not in_string:
            if char == start_char:
                count += 1
            elif char == end_char:
                count -= 1
                if count == 0:
                    # Found the balanced closing bracket
                    return content[start:i+1]
    
    raise ValueError("Unbalanced brackets in JSON")


def parse_json_object(content: str) -> Dict[str, Any]:
    """
    Parse a JSON object from an AI response string.

    This is a convenience wrapper around `extract_balanced_json` that additionally
    parses the extracted JSON into a Python dict and validates that the root is an object.

    Args:
        content (str): Raw AI response string that should contain a JSON object.

    Returns:
        Dict[str, Any]: Parsed JSON object as a dict.

    Raises:
        ValueError: If the JSON cannot be extracted/parsed or the root is not an object.
    """
    extracted = extract_balanced_json(content)
    try:
        parsed = json.loads(extracted)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object at the root")

    return parsed

