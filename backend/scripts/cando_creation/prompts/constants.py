# Prompt constants
STRICT_SYSTEM = (
    "You output a SINGLE JSON object that must validate the target Pydantic model. "
    "Return STRICT JSON only. No Markdown, no comments, no explanations. "
    "The response must be valid JSON that matches the provided schema exactly."
)

