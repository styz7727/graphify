"""Strip secrets from any text before logging or displaying."""
from __future__ import annotations

import re

_PATTERNS = [
    # API keys & tokens
    (re.compile(r"(sk-[A-Za-z0-9]{20,})", re.I),              "[REDACTED_KEY]"),
    (re.compile(r"(Bearer\s+\S{10,})", re.I),                  "[REDACTED_BEARER]"),
    (re.compile(r"(token[=:\s]+['\"]?)([A-Za-z0-9_\-\.]{16,})", re.I), r"\1[REDACTED]"),
    (re.compile(r"(password[=:\s]+['\"]?)(\S+)", re.I),        r"\1[REDACTED]"),
    (re.compile(r"(api[_-]?key[=:\s]+['\"]?)(\S+)", re.I),    r"\1[REDACTED]"),
    (re.compile(r"(secret[=:\s]+['\"]?)(\S+)", re.I),          r"\1[REDACTED]"),
    # AWS
    (re.compile(r"AKIA[0-9A-Z]{16}", re.I),                    "[REDACTED_AWS_KEY]"),
    # Private key blocks
    (re.compile(r"-----BEGIN [A-Z ]+ KEY-----.*?-----END [A-Z ]+ KEY-----", re.S), "[REDACTED_PEM]"),
]


def clean(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
