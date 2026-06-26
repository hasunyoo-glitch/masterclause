"""Negotiation playbook ordering (plan §5 Phase 5).

The model produces the negotiation items; this module deterministically orders
them so the report and result screen lead with the most important points:
walk-away issues first, then by priority (MUST_FIX → SHOULD_FIX → NICE_TO_FIX).
"""
from __future__ import annotations

from core.models import NegotiationItem, Priority

_PRIORITY_RANK = {
    Priority.MUST_FIX.value: 0,
    Priority.SHOULD_FIX.value: 1,
    Priority.NICE_TO_FIX.value: 2,
}


def _priority_value(item: NegotiationItem) -> str:
    p = item.priority
    return p.value if isinstance(p, Priority) else p


def order(items: list[NegotiationItem]) -> list[NegotiationItem]:
    """Return items sorted by (walk_away first, then priority)."""
    return sorted(
        items,
        key=lambda it: (0 if it.walk_away else 1, _PRIORITY_RANK.get(_priority_value(it), 99)),
    )


def walk_away_items(items: list[NegotiationItem]) -> list[NegotiationItem]:
    return [it for it in items if it.walk_away]
