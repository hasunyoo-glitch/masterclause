"""Privacy: pre-analysis anonymization and zero-retention helpers (plan §8).

Anonymization is reversible: identifiers are replaced with stable placeholders
before the text is sent to Claude, and ``restore`` swaps the original values
back into any text Claude returns (e.g. verbatim clause quotes). This keeps the
final report faithful while never transmitting raw PII.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Identifier patterns. Order matters: more specific first.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    # Korean resident registration number (RRN): 6 digits - 7 digits.
    ("KRRN", re.compile(r"\b\d{6}-\d{7}\b")),
    # US Social Security Number.
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # Phone numbers (KR / US-ish): keep loose but bounded to avoid eating dates.
    ("PHONE", re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)\d{3,4}[-.\s]?\d{4}\b")),
]


@dataclass
class Anonymizer:
    """Reversible masking of identifiers and (optionally) named parties."""

    _forward: dict[str, str] = field(default_factory=dict)   # original → placeholder
    _reverse: dict[str, str] = field(default_factory=dict)   # placeholder → original
    _counters: dict[str, int] = field(default_factory=dict)

    def register_party_names(self, names: list[str]) -> None:
        """Mask explicit party names (e.g. extracted from the overview)."""
        for name in sorted({n.strip() for n in names if n and len(n.strip()) >= 2}, key=len, reverse=True):
            self._placeholder_for(name, "PARTY")

    def anonymize(self, text: str, *, mask_parties: bool = True) -> str:
        if mask_parties:
            for original, placeholder in sorted(
                self._forward.items(), key=lambda kv: len(kv[0]), reverse=True
            ):
                if self._reverse.get(placeholder, "").strip() and original in text:
                    text = text.replace(original, placeholder)
        for label, pattern in _PATTERNS:
            text = pattern.sub(lambda m: self._placeholder_for(m.group(0), label), text)
        return text

    def restore(self, text: str) -> str:
        """Replace placeholders back with their original values."""
        if not text:
            return text
        for placeholder, original in sorted(
            self._reverse.items(), key=lambda kv: len(kv[0]), reverse=True
        ):
            text = text.replace(placeholder, original)
        return text

    # -- internals --------------------------------------------------------- #
    def _placeholder_for(self, original: str, label: str) -> str:
        if original in self._forward:
            return self._forward[original]
        self._counters[label] = self._counters.get(label, 0) + 1
        placeholder = f"[{label}_{self._counters[label]}]"
        self._forward[original] = placeholder
        self._reverse[placeholder] = original
        return placeholder

    @property
    def mapping(self) -> dict[str, str]:
        """placeholder → original (for audit / restore)."""
        return dict(self._reverse)


def should_persist_history(zero_retention: bool) -> bool:
    """Zero-retention mode keeps everything in memory; nothing hits the DB."""
    return not zero_retention
