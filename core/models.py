"""Domain models — the single source of truth (plan §4).

UI, core, history DB and the report writer all share these Pydantic models.
Two of them are *model-facing* (their JSON schema is sent to Claude as a strict
output contract): ``ContractAnalysis`` and ``ConcernAdvice``. Those keep every
field required and avoid validation constraints the structured-output API does
not support — Pydantic still validates client-side.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Classification enums (plan §4.1)
# --------------------------------------------------------------------------- #
class ContractType(str, Enum):
    RECORDING_AGREEMENT = "recording_agreement"
    SYNC_LICENSE = "sync_license"
    DISTRIBUTION_DEAL = "distribution_deal"
    PUBLISHING_AGREEMENT = "publishing_agreement"
    PRODUCER_AGREEMENT = "producer_agreement"
    CO_PUBLISHING = "co_publishing"
    MANAGEMENT_AGREEMENT = "management_agreement"
    PERFORMANCE_AGREEMENT = "performance_agreement"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class Priority(str, Enum):
    MUST_FIX = "MUST_FIX"
    SHOULD_FIX = "SHOULD_FIX"
    NICE_TO_FIX = "NICE_TO_FIX"


class Enforceability(str, Enum):
    LIKELY_ENFORCEABLE = "LIKELY_ENFORCEABLE"
    CONTESTED = "CONTESTED"
    LIKELY_UNENFORCEABLE = "LIKELY_UNENFORCEABLE"


class AIIssueType(str, Enum):
    TRAINING_DATA_USAGE = "training_data_usage"
    AI_OWNERSHIP = "ai_ownership"
    VOICE_CLONING = "voice_cloning"
    SYNTHETIC_COVERS = "synthetic_covers"
    FUTURE_TECHNOLOGY = "future_technology"
    PERPETUAL_LICENSE = "perpetual_license"
    CLASS_ACTION_WAIVER = "class_action_waiver"
    IDENTITY_DISCLOSURE = "identity_disclosure"
    AI_CLAUSE_ABSENCE = "ai_clause_absence"


class Recommendation(str, Enum):
    SIGN = "SIGN"
    NEGOTIATE = "NEGOTIATE"
    REJECT = "REJECT"


class BenchmarkAssessment(str, Enum):
    FAVORABLE = "FAVORABLE"
    NEUTRAL = "NEUTRAL"
    UNFAVORABLE = "UNFAVORABLE"


# --------------------------------------------------------------------------- #
# New option enums (plan §4.2 — the core of this version)
# --------------------------------------------------------------------------- #
class Perspective(str, Enum):
    LAWYER = "lawyer"   # entertainment lawyer advising a client
    ARTIST = "artist"   # the artist protecting their own rights
    LABEL = "label"     # the record label / company


class OutputLanguage(str, Enum):
    KO = "ko"
    EN = "en"


class Jurisdiction(str, Enum):
    KR = "KR"
    US = "US"
    # extensible: EU, UK, JP, UNKNOWN


class USState(str, Enum):
    CA = "CA"       # California
    NY = "NY"       # New York
    TN = "TN"       # Tennessee
    DC = "DC"       # Washington D.C. (federal district, treated as a venue)
    OTHER = "OTHER"  # anything else — free-typed name carried separately


# --------------------------------------------------------------------------- #
# Options decided in the GUI and passed to the worker (plan §4.2)
# --------------------------------------------------------------------------- #
class AnalysisOptions(BaseModel):
    """Confirmed when the user clicks "Start analysis"."""

    model_config = ConfigDict(use_enum_values=True)

    input_file_path: str
    output_path: str                       # directory or file path for the report

    perspective: Perspective
    output_language: OutputLanguage
    jurisdiction: Jurisdiction
    us_state: Optional[USState] = None     # required when jurisdiction == US
    us_state_other: Optional[str] = None   # free text when us_state == OTHER

    output_format: Literal["docx", "pdf", "both"] = "docx"

    # Free-form "what worries you most about this deal" (≤300 chars). Optional.
    user_concern: Optional[str] = Field(default=None, max_length=300)

    # Privacy
    anonymize_before_analysis: bool = False
    zero_retention: bool = False

    # Which Claude model to use (defaults set in config.py).
    model: Optional[str] = None

    def validate_rules(self) -> Optional[str]:
        """Return an error message if the option set is invalid, else None.

        Rule (plan §4.2): jurisdiction == US ⇒ us_state required.
        """
        jur = self.jurisdiction
        jur = jur.value if isinstance(jur, Jurisdiction) else jur
        if jur == Jurisdiction.US.value and not self.us_state:
            return "US 관할을 선택한 경우 주(state)를 지정해야 합니다."
        if self.user_concern and len(self.user_concern) > 300:
            return "우려 입력은 300자를 초과할 수 없습니다."
        return None

    def jurisdiction_label(self) -> str:
        """Human-readable jurisdiction, e.g. 'US-CA' or 'KR'."""
        jur = self.jurisdiction.value if isinstance(self.jurisdiction, Jurisdiction) else self.jurisdiction
        if jur != Jurisdiction.US.value:
            return jur
        state = self.us_state.value if isinstance(self.us_state, USState) else (self.us_state or "")
        if state == USState.OTHER.value and self.us_state_other:
            return f"US-{self.us_state_other}"
        return f"US-{state}" if state else "US"


# --------------------------------------------------------------------------- #
# Result sub-models (plan §4.3)
# --------------------------------------------------------------------------- #
class ContractOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_type: ContractType = Field(description="Detected contract type.")
    parties: list[str] = Field(description="Named contracting parties.")
    effective_date: str = Field(description="Effective date as written, or '' if absent.")
    term: str = Field(description="Term / duration of the agreement, or '' if absent.")
    territory: str = Field(description="Territorial scope, or '' if absent.")
    governing_law: str = Field(description="Governing law named in the contract, or '' if absent.")
    venue: str = Field(description="Dispute venue / forum, or '' if absent.")


class RiskScore(BaseModel):
    """Computed from the selected perspective (plan §4.3)."""

    model_config = ConfigDict(extra="forbid")

    overall: int = Field(description="Overall risk 0-100 (higher = worse for the chosen side).")
    copyright: int = Field(description="Copyright / ownership sub-score 0-100.")
    revenue: int = Field(description="Revenue / royalty sub-score 0-100.")
    control: int = Field(description="Creative & business control sub-score 0-100.")
    legal_remedy: int = Field(description="Legal remedy / dispute exposure sub-score 0-100.")
    summary: str = Field(description="One-paragraph rationale for the overall score.")


class AIClause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable id, e.g. 'C1', referenced by concern advice.")
    issue_type: AIIssueType
    title: str = Field(description="Short label for this clause / issue.")
    verbatim_text: str = Field(
        description="Exact clause text from the contract, original language, not translated."
    )
    location: str = Field(description="Where it appears, e.g. 'Section 7.2', or '' if absent.")
    summary: str = Field(description="Plain-language summary in the OUTPUT language.")
    flag: RiskLevel = Field(description="RED/YELLOW/GREEN from the chosen perspective.")
    enforceability: Enforceability
    impact_on_you: str = Field(
        description="One sentence: what this clause means for the chosen side."
    )
    proposed_revision: str = Field(description="Suggested redline / replacement language.")
    legal_basis: str = Field(description="Legal grounds for the assessment (statute / doctrine).")


class BenchmarkItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(description="What is benchmarked, e.g. 'Royalty rate', 'Term length'.")
    contract_value: str = Field(description="What this contract says.")
    industry_standard: str = Field(description="Typical market standard for this contract type.")
    assessment: BenchmarkAssessment = Field(description="From the chosen perspective.")
    comment: str = Field(description="Short explanation in the OUTPUT language.")


class JurisdictionNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(description="Legal issue, e.g. 'Right of publicity', '7-year rule'.")
    applicable_law: str = Field(description="Statute / regulation that applies in this jurisdiction.")
    analysis: str = Field(description="How the law bears on this contract, in the OUTPUT language.")
    conflict: bool = Field(
        description="True if the contract's governing law conflicts with the selected jurisdiction."
    )


class NegotiationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: Priority
    clause_id: str = Field(description="Related AIClause id, or '' if general.")
    issue: str = Field(description="What to negotiate.")
    strategy: str = Field(description="How to approach it from the chosen perspective.")
    proposed_revision: str = Field(description="Concrete language to propose.")
    walk_away: bool = Field(description="True if this is a deal-breaker / walk-away point.")


class ConcernAdvice(BaseModel):
    """Generated only when the user supplied ``user_concern`` (plan §4.3, §6.5).

    Model-facing: grounded strictly in the already-produced analysis.
    """

    model_config = ConfigDict(extra="forbid")

    concern_text: str = Field(description="The user's original concern, preserved verbatim.")
    direct_answer: str = Field(
        description="Direct answer to the concern, in the chosen language and perspective."
    )
    relevant_clause_ids: list[str] = Field(
        description="AIClause ids directly related to this concern (may be empty)."
    )
    risk_assessment: RiskLevel = Field(description="Risk for this concern: RED/YELLOW/GREEN.")
    recommended_actions: list[str] = Field(
        description="Concrete steps to address the concern (negotiation points, language)."
    )


# --------------------------------------------------------------------------- #
# Model-facing analysis container (its schema is the strict output contract)
# --------------------------------------------------------------------------- #
class ContractAnalysis(BaseModel):
    """Everything Claude produces for the main analysis pass.

    ``options`` and ``concern_advice`` are intentionally *not* here — they are
    attached by application code. Keep all fields required (no defaults) so the
    structured-output schema stays strict-compatible.
    """

    model_config = ConfigDict(extra="forbid")

    overview: ContractOverview
    risk_score: RiskScore
    ai_clauses: list[AIClause]
    benchmarks: list[BenchmarkItem]
    jurisdiction_notes: list[JurisdictionNote]
    negotiation_playbook: list[NegotiationItem]
    recommendation: Recommendation
    disclaimer: str = Field(
        description="A 'not legal advice' notice, in the OUTPUT language."
    )


# --------------------------------------------------------------------------- #
# Full result (assembled by application code; carries options for reproducibility)
# --------------------------------------------------------------------------- #
class AnalysisResult(BaseModel):
    options: AnalysisOptions
    analysis: ContractAnalysis
    concern_advice: Optional[ConcernAdvice] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Convenience pass-throughs so the report writer / UI can use flat access.
    @property
    def overview(self) -> ContractOverview:
        return self.analysis.overview

    @property
    def risk_score(self) -> RiskScore:
        return self.analysis.risk_score

    @property
    def ai_clauses(self) -> list[AIClause]:
        return self.analysis.ai_clauses

    @property
    def benchmarks(self) -> list[BenchmarkItem]:
        return self.analysis.benchmarks

    @property
    def jurisdiction_notes(self) -> list[JurisdictionNote]:
        return self.analysis.jurisdiction_notes

    @property
    def negotiation_playbook(self) -> list[NegotiationItem]:
        return self.analysis.negotiation_playbook

    @property
    def recommendation(self) -> Recommendation:
        return self.analysis.recommendation

    @property
    def disclaimer(self) -> str:
        return self.analysis.disclaimer

    @property
    def red_clause_count(self) -> int:
        return sum(1 for c in self.ai_clauses if _as_value(c.flag) == RiskLevel.RED.value)

    @property
    def walk_away_count(self) -> int:
        return sum(1 for n in self.negotiation_playbook if n.walk_away)


def _as_value(v: object) -> object:
    """Return ``.value`` for an Enum, else the value itself (use_enum_values safe)."""
    return v.value if isinstance(v, Enum) else v
