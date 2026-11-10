"""Redaction: typed placeholders for secrets and personal data (C7)."""

from __future__ import annotations

import pytest
from accel_core.redaction import Redactor

CASES = [
    ("private_key", "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIB\n-----END RSA PRIVATE KEY-----"),
    ("jwt", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9P"),
    ("aws_access_key", "AKIAIOSFODNN7EXAMPLE"),
    ("github_token", "ghp_" + "a1B2" * 9),
    ("slack_token", "xoxb-1234567890-abcdefghij"),
    ("api_key", "sk-proj-abcdefghijklmnopqrstuvwx"),
    ("email", "jane.doe@example.com"),
    ("phone", "+1 415-555-0123"),
    ("phone", "(415) 555-0123"),
    ("phone", "+91 98765 43210"),
    ("phone", "+919876543210"),
    ("employee_id", "EMP-004211"),
]


@pytest.mark.parametrize(("kind", "value"), CASES)
def test_each_kind_is_replaced_with_a_typed_placeholder(kind: str, value: str) -> None:
    text, counts = Redactor().redact(f"before {value} after")
    assert text == f"before [REDACTED_{kind.upper()}_1] after"
    assert counts == {kind: 1}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("password=hunter2-secret", "password=[REDACTED_SECRET_1]"),
        ('"client_secret": "abcdef123456"', '"client_secret": "[REDACTED_SECRET_1]"'),
        ("API_KEY: 0123456789abcdef", "API_KEY: [REDACTED_SECRET_1]"),
        (
            "Authorization: Bearer abc.def-ghi_jkl.mnop",
            "Authorization: Bearer [REDACTED_BEARER_TOKEN_1]",
        ),
        (
            "postgres://app:s3cr3t-pw@db:5432/x",
            "postgres://app:[REDACTED_URL_CREDENTIALS_1]@db:5432/x",
        ),
        ('DB_PASSWORD = "hunter2-fixture-only"', 'DB_PASSWORD = "[REDACTED_SECRET_1]"'),
        ("SESSION_SECRET=abcdef123456", "SESSION_SECRET=[REDACTED_SECRET_1]"),
        ("GITHUB_API_KEY: 'zz9-plural-z-alpha'", "GITHUB_API_KEY: '[REDACTED_SECRET_1]'"),
    ],
)
def test_assignments_keep_their_context(text: str, expected: str) -> None:
    assert Redactor().redact(text)[0] == expected


def test_the_same_value_gets_the_same_placeholder_within_a_session() -> None:
    text, counts = Redactor().redact("a@x.io wrote to b@x.io, then a@x.io replied")
    assert text == (
        "[REDACTED_EMAIL_1] wrote to [REDACTED_EMAIL_2], then [REDACTED_EMAIL_1] replied"
    )
    assert counts == {"email": 3}


@pytest.mark.parametrize(
    "text",
    [
        "Released 2026-11-10 at 09:30, version 1.2.3",
        "commit 9f3c2e1a7b4d and sha256 3f1c9a7e5b2d4f6081a3c5e7f9b1d3e5",
        "def validate_token(token: str) -> bool: return True",
        "Listen on 0.0.0.0:8080 with 4 workers",
        "token = None",
        "access_token = body.access_token",
        "request.state.user_token = claims_from_header",
        "MAX_TOKENS = 4096",
    ],
)
def test_ordinary_code_and_text_is_left_alone(text: str) -> None:
    assert Redactor().redact(text) == (text, {})


def test_json_values_are_redacted_but_structural_keys_are_not() -> None:
    session = Redactor().session()
    message = {
        "role": "tool",
        "tool_call_id": "call_jane@example.com",
        "content": [{"type": "text", "text": "mail jane@example.com"}],
        "extra": ("call +1 415-555-0123", 7, None),
    }
    assert session.value(message) == {
        "role": "tool",
        "tool_call_id": "call_jane@example.com",
        "content": [{"type": "text", "text": "mail [REDACTED_EMAIL_1]"}],
        "extra": ["call [REDACTED_PHONE_1]", 7, None],
    }
    assert dict(session.counts) == {"email": 1, "phone": 1}


def test_with_literal_redacts_an_exact_secret_first() -> None:
    redactor = Redactor().with_literal("azure_openai_key", "plainkeywithnoshape")
    assert redactor.redact("key is plainkeywithnoshape") == (
        "key is [REDACTED_AZURE_OPENAI_KEY_1]",
        {"azure_openai_key": 1},
    )
