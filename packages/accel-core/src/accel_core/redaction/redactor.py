"""Pattern-based redaction with typed placeholders such as `[REDACTED_EMAIL_1]`."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

# Message keys whose values are structure, not content, and are never redacted.
_STRUCTURAL_KEYS = frozenset({"role", "type", "id", "tool_call_id", "name"})


@dataclass(frozen=True)
class RedactionRule:
    """One kind of sensitive value.

    If `pattern` has a group named `value`, only that group is replaced, so the
    surrounding context (such as `password=`) stays readable.
    """

    kind: str
    pattern: re.Pattern[str]


def _rule(kind: str, pattern: str, flags: int = 0) -> RedactionRule:
    return RedactionRule(kind, re.compile(pattern, flags))


# Order matters: multi-line and specific token formats run before generic patterns.
DEFAULT_RULES: tuple[RedactionRule, ...] = (
    _rule(
        "private_key",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
    ),
    _rule("jwt", r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    _rule("aws_access_key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    _rule("github_token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})"),
    _rule("slack_token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    _rule("api_key", r"\bsk-[A-Za-z0-9_-]{20,}"),
    _rule("bearer_token", r"\bbearer\s+(?P<value>[A-Za-z0-9._~+/-]{16,}=*)", re.IGNORECASE),
    _rule("url_credentials", r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:(?P<value>[^\s@/]+)@", re.I),
    _rule(
        "secret",
        r"\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)"
        r"\w*[\"']?\s*[:=]\s*[\"']?(?P<value>[^\s\"',;]{6,})",
        re.IGNORECASE,
    ),
    # UPPER_SNAKE constants and env vars that end in a secret word, such as DB_PASSWORD.
    # Case-sensitive, so ordinary code like `access_token = body.access_token` is kept.
    _rule(
        "secret",
        r"\b[A-Z0-9]+(?:_[A-Z0-9]+)*_(?:PASSWORD|PASSWD|PWD|SECRET|TOKEN|API_?KEY|ACCESS_KEY)\b"
        r"[\"']?\s*[:=]\s*[\"']?(?P<value>[^\s\"',;]{6,})",
    ),
    _rule("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    _rule(
        "phone",
        r"(?<![\w+])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)\s?|\d{2,4}[\s.-])\d{3,4}[\s.-]\d{3,4}(?!\w)"
        r"|\+\d{1,3}[\s-]?\d{3,5}[\s-]?\d{4,6}\b",
    ),
    _rule("employee_id", r"\bEMP[-_]?\d{4,8}\b", re.IGNORECASE),
)


@dataclass
class RedactionSession:
    """Redacts values for one model call, giving each distinct value one placeholder."""

    rules: Sequence[RedactionRule]
    counts: Counter[str] = field(default_factory=Counter[str])
    _seen: dict[tuple[str, str], str] = field(default_factory=dict[tuple[str, str], str])
    _next: Counter[str] = field(default_factory=Counter[str])

    def _placeholder(self, kind: str, value: str) -> str:
        key = (kind, value)
        if key not in self._seen:
            self._next[kind] += 1
            self._seen[key] = f"[REDACTED_{kind.upper()}_{self._next[kind]}]"
        self.counts[kind] += 1
        return self._seen[key]

    def text(self, text: str) -> str:
        """Return `text` with every sensitive value replaced."""
        for rule in self.rules:
            text = rule.pattern.sub(lambda match, r=rule: self._replace(r, match), text)
        return text

    def _replace(self, rule: RedactionRule, match: re.Match[str]) -> str:
        whole = match.group(0)
        if "value" not in rule.pattern.groupindex or match.group("value") is None:
            return self._placeholder(rule.kind, whole)
        start = match.start("value") - match.start()
        end = match.end("value") - match.start()
        return whole[:start] + self._placeholder(rule.kind, match.group("value")) + whole[end:]

    def value(self, value: Any) -> Any:
        """Redact every string inside a JSON-like value, leaving structural keys alone."""
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, Mapping):
            mapping = cast("Mapping[str, Any]", value)
            return {
                key: item if key in _STRUCTURAL_KEYS else self.value(item)
                for key, item in mapping.items()
            }
        if isinstance(value, list | tuple):
            return [self.value(item) for item in cast("Iterable[Any]", value)]
        return value


@dataclass(frozen=True)
class Redactor:
    """Holds the rules. Call `session()` once per model call."""

    rules: tuple[RedactionRule, ...] = DEFAULT_RULES

    def with_literal(self, kind: str, secret: str) -> Redactor:
        """Return a redactor that also replaces one exact secret, such as the API key."""
        rule = RedactionRule(kind, re.compile(re.escape(secret)))
        return Redactor(rules=(rule, *self.rules))

    def session(self) -> RedactionSession:
        """Start a redaction session for one call."""
        return RedactionSession(rules=self.rules)

    def redact(self, text: str) -> tuple[str, dict[str, int]]:
        """Redact one string; return the text and a count per kind."""
        session = self.session()
        return session.text(text), dict(session.counts)
