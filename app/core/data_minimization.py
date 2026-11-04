import re
from typing import Any

_PATTERNS = (
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[E-MAIL REMOVIDO]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[DOCUMENTO REMOVIDO]"),
    (re.compile(r"\b(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-.\s]?\d{4}\b"), "[TELEFONE REMOVIDO]"),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,})\b", re.IGNORECASE), "[SEGREDO REMOVIDO]"),
)


def redact_sensitive_content(value: Any) -> Any:
    """Best-effort redaction before sending structured exercise data to an external LLM."""
    if isinstance(value, dict):
        return {key: redact_sensitive_content(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive_content(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_content(item) for item in value)
    if isinstance(value, str):
        redacted = value
        for pattern, replacement in _PATTERNS:
            redacted = pattern.sub(replacement, redacted)
        return redacted
    return value
