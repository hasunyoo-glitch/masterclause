"""Prompt construction for the analyzer (plan §6.1–6.5).

Encodes the three levers that make this version distinctive:
  * perspective (lawyer / artist / label) — whose interest defines "risk"
  * output language (ko / en) — generated text language; verbatim clauses kept
  * jurisdiction (+ US state) — applicable-law context, injected by the caller

The system prompt is split into a stable framing block (cacheable) and the
volatile per-document context blocks.
"""
from __future__ import annotations

from core.models import (
    AnalysisOptions,
    OutputLanguage,
    Perspective,
)

_DISCLAIMER_REQUIRED = (
    "모든 분석은 일반 정보 제공이며 법률 자문이 아니다. disclaimer 필드에 "
    "선택된 출력 언어로 '법률 자문 아님' 고지를 반드시 포함하라."
)

PERSPECTIVE_FRAMING = {
    Perspective.LAWYER.value: (
        "당신은 의뢰인을 자문하는 엔터테인먼트 전문 변호사다. 중립적이고 정밀한 법률 분석 "
        "톤을 유지하되, 집행가능성(enforceability)과 법적 근거(legal_basis)를 특히 엄밀하게 "
        "평가하라. 위험은 '의뢰인(계약 당사자 중 약자 또는 자문 대상)' 관점에서 산정한다."
    ),
    Perspective.ARTIST.value: (
        "당신은 아티스트 본인의 권리를 보호하는 입장에서 분석한다. 평이하고 이해하기 쉬운 "
        "언어를 사용하되 정확성을 잃지 마라. 위험은 '아티스트'에게 불리한 정도로 평가하며, "
        "아티스트의 권리·수익·통제권을 지키는 방향으로 협상 전략을 제시하라."
    ),
    Perspective.LABEL.value: (
        "당신은 음반사/레이블의 입장에서 분석한다. 레이블의 리스크 노출, 조항의 방어가능성, "
        "산업 표준 대비 합리성 중심으로 평가하라. 위험은 '레이블'에게 불리한 정도(분쟁 노출, "
        "집행 불가 위험, 평판 리스크 등)로 산정한다."
    ),
}

LANGUAGE_INSTRUCTION = {
    OutputLanguage.KO.value: (
        "생성하는 모든 텍스트(요약, 분석, 영향, 수정안, 노트, 고지)는 자연스러운 실무 한국어로 "
        "작성하라."
    ),
    OutputLanguage.EN.value: (
        "Write all generated text (summaries, analysis, impact, revisions, notes, disclaimer) in "
        "clear professional legal-memo English. Use concise citation form where helpful."
    ),
}


def _enum_value(v) -> str:
    return v.value if hasattr(v, "value") else v


def build_framing_block(options: AnalysisOptions) -> str:
    """Stable, cacheable portion of the system prompt (perspective + language + rules)."""
    perspective = _enum_value(options.perspective)
    language = _enum_value(options.output_language)
    return "\n\n".join(
        [
            "당신은 음악 산업 계약서의 AI 관련 조항을 분석하는 전문 분석 엔진이다.",
            f"[입장] {PERSPECTIVE_FRAMING.get(perspective, PERSPECTIVE_FRAMING[Perspective.LAWYER.value])}",
            f"[출력 언어] {LANGUAGE_INSTRUCTION.get(language, LANGUAGE_INSTRUCTION[OutputLanguage.KO.value])}",
            (
                "[원문 보존] ai_clauses 의 verbatim_text 는 반드시 계약서 원문 그대로 "
                "(원본 언어, 번역 금지) 인용하라. 요약·분석은 선택한 출력 언어로 작성한다."
            ),
            (
                "[탐지 대상] 다음 AIIssueType 을 우선 탐지하라: training_data_usage, ai_ownership, "
                "voice_cloning, synthetic_covers, future_technology, perpetual_license, "
                "class_action_waiver, identity_disclosure, ai_clause_absence(관련 보호 조항의 부재). "
                "각 조항에는 안정적인 id(C1, C2, …)를 부여하라."
            ),
            (
                "[입장 반영] 동일 조항도 입장에 따라 RED/YELLOW/GREEN 이 달라질 수 있다. flag, "
                "impact_on_you, negotiation_playbook, recommendation, risk_score 는 모두 선택 입장의 "
                "이익을 기준으로 산정하라."
            ),
            _DISCLAIMER_REQUIRED,
        ]
    )


def build_context_block(jurisdiction_context: str, benchmark_context: str) -> str:
    """Volatile per-document context (jurisdiction + benchmarks)."""
    return "\n\n".join([jurisdiction_context.strip(), benchmark_context.strip()])


def build_analysis_user_prompt(contract_text: str) -> str:
    return (
        "다음은 분석 대상 음악 계약서의 전체 텍스트다. 위 지침과 관할/벤치마크 컨텍스트에 따라 "
        "구조화된 분석 결과를 생성하라. 스키마에 정의된 모든 필드를 채우되, 해당 항목이 없으면 "
        "빈 문자열/빈 배열을 사용하라.\n\n"
        "===== 계약서 시작 =====\n"
        f"{contract_text}\n"
        "===== 계약서 끝 ====="
    )


# --------------------------------------------------------------------------- #
# Contract-type detection (cheap pre-pass)
# --------------------------------------------------------------------------- #
def build_type_detection_prompt(contract_text: str) -> str:
    head = contract_text[:6000]
    return (
        "다음 계약서의 유형을 ContractType 중 하나로 분류하라. 본문 일부만 제공될 수 있다.\n\n"
        f"{head}"
    )


# --------------------------------------------------------------------------- #
# Concern advice (plan §6.5)
# --------------------------------------------------------------------------- #
def build_concern_system_prompt(options: AnalysisOptions) -> str:
    framing = build_framing_block(options)
    return framing + "\n\n" + (
        "[우려 맞춤 조언 규칙] 이미 산출된 분석(ai_clauses/benchmarks/jurisdiction_notes/"
        "negotiation_playbook)에만 근거하여 사용자의 우려에 답하라. 새로운 사실을 지어내지 마라. "
        "관련 조항이 없으면 그 사실을 명시하고 일반론 또는 누락 위험(ai_clause_absence) 관점에서 "
        "보완 조언하라. concern_text 에는 사용자의 우려 원문을 그대로 보존하라."
    )


def build_concern_user_prompt(user_concern: str, analysis_json: str) -> str:
    return (
        "사용자의 우려:\n"
        f"\"\"\"{user_concern}\"\"\"\n\n"
        "아래는 방금 완료된 본 분석 결과(JSON)다. 이 근거만 사용하여 우려에 직접 답하는 "
        "ConcernAdvice 를 생성하라.\n\n"
        "===== 분석 결과 시작 =====\n"
        f"{analysis_json}\n"
        "===== 분석 결과 끝 ====="
    )
