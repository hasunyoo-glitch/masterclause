"""Pure-logic checks: privacy round-trip, playbook ordering, data loading, schema."""
from core import benchmarks, jurisdiction, playbook
from core.analyzer import _extract_json, _strict_schema
from core.models import (
    AnalysisOptions,
    ConcernAdvice,
    ContractAnalysis,
    ContractType,
    NegotiationItem,
    Priority,
)
from core.privacy import Anonymizer


def _options(**kw) -> AnalysisOptions:
    base = dict(input_file_path="c.docx", output_path=".", perspective="lawyer",
                output_language="ko", jurisdiction="KR")
    base.update(kw)
    return AnalysisOptions(**base)


# --- privacy ---------------------------------------------------------------- #
def test_anonymizer_roundtrip():
    anon = Anonymizer()
    text = "Contact jane@example.com or 010-1234-5678."
    masked = anon.anonymize(text)
    assert "jane@example.com" not in masked
    assert "010-1234-5678" not in masked
    assert anon.restore(masked) == text


def test_anonymizer_party_names():
    anon = Anonymizer()
    anon.register_party_names(["Big Label Inc"])
    masked = anon.anonymize("Big Label Inc shall own the masters.")
    assert "Big Label Inc" not in masked
    assert "Big Label Inc" in anon.restore(masked)


# --- playbook --------------------------------------------------------------- #
def _item(priority: Priority, walk: bool) -> NegotiationItem:
    return NegotiationItem(priority=priority, clause_id="", issue="i", strategy="s",
                           proposed_revision="r", walk_away=walk)


def test_playbook_orders_walk_away_then_priority():
    items = [
        _item(Priority.NICE_TO_FIX, False),
        _item(Priority.MUST_FIX, False),
        _item(Priority.SHOULD_FIX, True),
    ]
    ordered = playbook.order(items)
    assert ordered[0].walk_away is True             # walk-away first
    assert ordered[1].priority in (Priority.MUST_FIX, Priority.MUST_FIX.value)
    assert len(playbook.walk_away_items(items)) == 1


# --- jurisdiction data ------------------------------------------------------ #
def test_jurisdiction_kr_context():
    ctx = jurisdiction.build_prompt_context(_options(jurisdiction="KR"))
    assert "대한민국" in ctx
    assert "저작권법" in ctx


def test_jurisdiction_us_ca_context():
    ctx = jurisdiction.build_prompt_context(_options(jurisdiction="US", us_state="CA"))
    assert "California" in ctx or "캘리포니아" in ctx
    assert "2855" in ctx  # seven-year rule citation present


def test_jurisdiction_us_other_falls_back():
    data = jurisdiction.get_data(_options(jurisdiction="US", us_state="OTHER"))
    assert data.key == "US_OTHER"


# --- benchmarks ------------------------------------------------------------- #
def test_benchmark_recording_loaded():
    ctx = benchmarks.build_prompt_context(ContractType.RECORDING_AGREEMENT)
    assert "Recording" in ctx
    assert "FAVORABLE" in ctx


def test_benchmark_unknown_uses_default():
    data = benchmarks.get_standards(ContractType.UNKNOWN)
    assert data["standards"]


# --- schema / json extraction ---------------------------------------------- #
def test_strict_schema_hardened():
    schema = _strict_schema(ContractAnalysis)
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["AIClause"]["additionalProperties"] is False
    _strict_schema(ConcernAdvice)  # builds without error


def test_extract_json_strips_fence():
    payload = _extract_json('```json\n{"a": 1}\n```')
    assert payload == {"a": 1}


def test_extract_json_finds_object():
    payload = _extract_json('noise {"a": 2} trailing')
    assert payload == {"a": 2}
