"""End-to-end report generation from a synthetic result (KO + EN)."""
from pathlib import Path

from core import report_writer
from core.models import (
    AIClause,
    AIIssueType,
    AnalysisOptions,
    AnalysisResult,
    BenchmarkAssessment,
    BenchmarkItem,
    ConcernAdvice,
    ContractAnalysis,
    ContractOverview,
    ContractType,
    Enforceability,
    JurisdictionNote,
    NegotiationItem,
    Priority,
    Recommendation,
    RiskLevel,
    RiskScore,
)


def _result(output_dir: str, language: str) -> tuple[AnalysisResult, AnalysisOptions]:
    ov = ContractOverview(contract_type=ContractType.RECORDING_AGREEMENT, parties=["아티스트", "레이블"],
                          effective_date="2026-01-01", term="3년", territory="전세계",
                          governing_law="California", venue="LA")
    rs = RiskScore(overall=72, copyright=80, revenue=65, control=70, legal_remedy=60, summary="높은 위험.")
    clause = AIClause(id="C1", issue_type=AIIssueType.VOICE_CLONING, title="AI 음성 복제",
                      verbatim_text="Label may use the voice for AI training in perpetuity.",
                      location="7.2", summary="무기한 AI 음성 권리.", flag=RiskLevel.RED,
                      enforceability=Enforceability.CONTESTED, impact_on_you="영구 학습 위험.",
                      proposed_revision="동의·기간 제한.", legal_basis="CA AB 2602")
    bench = BenchmarkItem(topic="AI 권리", contract_value="무기한", industry_standard="프로젝트 한정",
                          assessment=BenchmarkAssessment.UNFAVORABLE, comment="비표준.")
    note = JurisdictionNote(topic="디지털 레플리카", applicable_law="CA AB 2602",
                            analysis="특정성 없으면 집행 불가.", conflict=True)
    nego = NegotiationItem(priority=Priority.MUST_FIX, clause_id="C1", issue="무기한 권리 삭제",
                           strategy="sunset 요구.", proposed_revision="...", walk_away=True)
    analysis = ContractAnalysis(overview=ov, risk_score=rs, ai_clauses=[clause], benchmarks=[bench],
                                jurisdiction_notes=[note], negotiation_playbook=[nego],
                                recommendation=Recommendation.NEGOTIATE, disclaimer="법률 자문 아님.")
    advice = ConcernAdvice(concern_text="목소리 걱정.", direct_answer="C1 조항이 핵심.",
                           relevant_clause_ids=["C1"], risk_assessment=RiskLevel.RED,
                           recommended_actions=["sunset 협상."])
    opts = AnalysisOptions(input_file_path="contract.docx", output_path=output_dir,
                           perspective="artist", output_language=language, jurisdiction="US",
                           us_state="CA", user_concern="목소리 걱정.")
    return AnalysisResult(options=opts, analysis=analysis, concern_advice=advice), opts


def test_report_writes_docx_ko(tmp_path):
    result, opts = _result(str(tmp_path), "ko")
    written = report_writer.write_report(result, opts)
    assert written
    p = Path(written[0])
    assert p.exists() and p.suffix == ".docx"
    assert p.stat().st_size > 5000


def test_report_writes_docx_en(tmp_path):
    result, opts = _result(str(tmp_path), "en")
    written = report_writer.write_report(result, opts)
    assert Path(written[0]).exists()


def test_report_respects_explicit_filename(tmp_path):
    result, opts = _result(str(tmp_path), "ko")
    opts.output_path = str(tmp_path / "myreport.docx")
    written = report_writer.write_report(result, opts)
    assert Path(written[0]).name == "myreport.docx"
