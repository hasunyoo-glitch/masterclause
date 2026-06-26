"""Domain-model rules: option validation, jurisdiction labels, derived counts."""
import pytest

from core.models import (
    AIClause,
    AIIssueType,
    AnalysisOptions,
    AnalysisResult,
    BenchmarkAssessment,
    ContractAnalysis,
    ContractOverview,
    ContractType,
    Enforceability,
    NegotiationItem,
    Priority,
    Recommendation,
    RiskLevel,
    RiskScore,
)


def _options(**kw) -> AnalysisOptions:
    base = dict(
        input_file_path="c.docx",
        output_path=".",
        perspective="artist",
        output_language="ko",
        jurisdiction="KR",
    )
    base.update(kw)
    return AnalysisOptions(**base)


def test_us_requires_state():
    opts = _options(jurisdiction="US", us_state=None)
    assert opts.validate_rules() is not None


def test_us_with_state_ok():
    opts = _options(jurisdiction="US", us_state="CA")
    assert opts.validate_rules() is None
    assert opts.jurisdiction_label() == "US-CA"


def test_kr_ignores_state():
    opts = _options(jurisdiction="KR", us_state=None)
    assert opts.validate_rules() is None
    assert opts.jurisdiction_label() == "KR"


def test_us_other_label_uses_free_text():
    opts = _options(jurisdiction="US", us_state="OTHER", us_state_other="Texas")
    assert opts.jurisdiction_label() == "US-Texas"


def test_concern_length_limit():
    with pytest.raises(Exception):
        _options(user_concern="x" * 301)


def _clause(flag: RiskLevel) -> AIClause:
    return AIClause(
        id="C1", issue_type=AIIssueType.VOICE_CLONING, title="t", verbatim_text="v",
        location="", summary="s", flag=flag, enforceability=Enforceability.CONTESTED,
        impact_on_you="i", proposed_revision="r", legal_basis="b",
    )


def _analysis(clauses, nego) -> ContractAnalysis:
    return ContractAnalysis(
        overview=ContractOverview(contract_type=ContractType.UNKNOWN, parties=[], effective_date="",
                                  term="", territory="", governing_law="", venue=""),
        risk_score=RiskScore(overall=10, copyright=10, revenue=10, control=10, legal_remedy=10, summary=""),
        ai_clauses=clauses, benchmarks=[], jurisdiction_notes=[], negotiation_playbook=nego,
        recommendation=Recommendation.NEGOTIATE, disclaimer="x",
    )


def test_derived_counts():
    nego = [NegotiationItem(priority=Priority.MUST_FIX, clause_id="C1", issue="i",
                            strategy="s", proposed_revision="r", walk_away=True)]
    analysis = _analysis([_clause(RiskLevel.RED), _clause(RiskLevel.GREEN)], nego)
    result = AnalysisResult(options=_options(), analysis=analysis)
    assert result.red_clause_count == 1
    assert result.walk_away_count == 1
    # Flat pass-through properties work.
    assert result.recommendation == Recommendation.NEGOTIATE
    assert len(result.ai_clauses) == 2
