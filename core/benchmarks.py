"""Industry-standard benchmark data by contract type (plan §6.4, Phase 4).

Provides the prompt context the analyzer uses to judge clauses against market
norms (FAVORABLE/NEUTRAL/UNFAVORABLE from the chosen perspective) and the raw
standards for the report appendix.
"""
from __future__ import annotations

import json
from functools import lru_cache

import config
from core.models import ContractType

# Contract types that map to a publishing-style benchmark file.
_PUBLISHING_LIKE = {
    ContractType.PUBLISHING_AGREEMENT.value,
    ContractType.CO_PUBLISHING.value,
}


def _file_for(contract_type: str | ContractType | None) -> str:
    ct = contract_type.value if isinstance(contract_type, ContractType) else (contract_type or "")
    if ct in _PUBLISHING_LIKE:
        return "publishing_agreement"
    known = {
        ContractType.RECORDING_AGREEMENT.value: "recording_agreement",
        ContractType.DISTRIBUTION_DEAL.value: "distribution_deal",
        ContractType.MANAGEMENT_AGREEMENT.value: "management_agreement",
    }
    return known.get(ct, "_default")


@lru_cache(maxsize=None)
def _load(name: str) -> dict:
    path = config.BENCHMARK_DATA_DIR / f"{name}.json"
    if not path.exists():
        path = config.BENCHMARK_DATA_DIR / "_default.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def get_standards(contract_type: str | ContractType | None) -> dict:
    return _load(_file_for(contract_type))


def build_prompt_context(contract_type: str | ContractType | None) -> str:
    data = get_standards(contract_type)
    lines = [f"[산업 표준 벤치마크 — {data.get('label', '')}]"]
    for item in data.get("standards", []):
        lines.append(f"  - {item.get('topic')}: {item.get('standard')}")
    lines.append(
        "각 BenchmarkItem 은 선택된 입장 기준으로 FAVORABLE/NEUTRAL/UNFAVORABLE 를 판정하라."
    )
    return "\n".join(lines)
