"""Jurisdiction mapping: (Jurisdiction, USState) → applicable law context (plan §6.3).

Loads the review-flagged datasets under ``data/jurisdiction`` and produces the
prompt context injected into the analyzer, plus the structured issue list for
the report. Governing-law ↔ jurisdiction conflict detection is left to the model
(it has the contract's governing_law in hand), but this module names the
selected jurisdiction so the model can compare.
"""
from __future__ import annotations

import json
from functools import lru_cache

import config
from core.models import AnalysisOptions, Jurisdiction, USState


class JurisdictionData:
    def __init__(self, raw: dict):
        self.key: str = raw.get("key", "")
        self.label: str = raw.get("label", self.key)
        self.review_status: str = raw.get("review_status", "")
        self.sources_as_of: str = raw.get("sources_as_of", "")
        self.issues: list[dict] = raw.get("issues", [])
        self.prompt_context: str = raw.get("prompt_context", "")


def _dataset_key(options: AnalysisOptions) -> str:
    jur = options.jurisdiction
    jur = jur.value if isinstance(jur, Jurisdiction) else jur
    if jur != Jurisdiction.US.value:
        return "KR"
    state = options.us_state
    state = state.value if isinstance(state, USState) else state
    if state in {USState.CA.value, USState.NY.value, USState.TN.value, USState.DC.value}:
        return f"US_{state}"
    return "US_OTHER"


@lru_cache(maxsize=None)
def _load(dataset_key: str) -> JurisdictionData:
    path = config.JURISDICTION_DATA_DIR / f"{dataset_key}.json"
    if not path.exists():
        # Safe fallback so analysis never hard-fails on a missing dataset.
        return JurisdictionData(
            {
                "key": dataset_key,
                "label": dataset_key,
                "review_status": "MISSING dataset — analysis used generic context.",
                "prompt_context": "관할별 데이터셋을 찾지 못해 일반 법리로 분석함.",
            }
        )
    with path.open(encoding="utf-8") as fh:
        return JurisdictionData(json.load(fh))


def get_data(options: AnalysisOptions) -> JurisdictionData:
    return _load(_dataset_key(options))


def build_prompt_context(options: AnalysisOptions) -> str:
    """Return the jurisdiction context string for the system prompt."""
    data = get_data(options)
    lines = [f"[관할 컨텍스트 — {data.label}]", data.prompt_context.strip()]
    if data.issues:
        lines.append("주요 쟁점/적용법:")
        for issue in data.issues:
            lines.append(f"  - {issue.get('topic')}: {issue.get('law')} — {issue.get('note')}")
    lines.append(
        "준거법 충돌 점검: 계약서가 정한 준거법이 위 선택 관할과 다르면 "
        "해당 JurisdictionNote.conflict 를 true 로 표시하고 그 의미를 설명하라."
    )
    return "\n".join(lines)
