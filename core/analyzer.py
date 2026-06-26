"""Claude analysis engine (plan §6).

In-process pipeline:
  parse (caller) → privacy → type detect → main structured analysis →
  concern advice (optional) → assemble AnalysisResult.

The main analysis uses a strict JSON-schema output contract derived from
``ContractAnalysis`` and is streamed (large structured result). On schema
rejection it falls back to a plain JSON-instruction pass; on validation failure
it retries once with a corrective message (plan: "Pydantic 검증/재시도").
"""
from __future__ import annotations

import json
from typing import Callable, Optional

from pydantic import BaseModel, ValidationError

import config
from core import api_key, benchmarks, jurisdiction, playbook, prompts
from core.models import (
    AnalysisOptions,
    AnalysisResult,
    ConcernAdvice,
    ContractAnalysis,
    ContractType,
)
from core.parser import ParsedDocument
from core.privacy import Anonymizer

# progress(stage_key, fraction). stage_key is a stable key the UI localizes:
# "prepare" | "detect_type" | "analyze" | "concern" | "done" (plus worker keys).
ProgressFn = Callable[[str, float], None]
CancelFn = Callable[[], bool]


class AnalyzerError(Exception):
    pass


class AnalysisCancelled(Exception):
    pass


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def analyze(
    parsed: ParsedDocument,
    options: AnalysisOptions,
    *,
    progress: Optional[ProgressFn] = None,
    should_cancel: Optional[CancelFn] = None,
) -> AnalysisResult:
    progress = progress or (lambda label, frac: None)
    should_cancel = should_cancel or (lambda: False)

    def _check_cancel() -> None:
        if should_cancel():
            raise AnalysisCancelled()

    err = options.validate_rules()
    if err:
        raise AnalyzerError(err)

    client = _client(options)
    model = options.model or config.MODEL_PRIMARY

    progress("prepare", 0.05)
    _check_cancel()

    # 1. Privacy: optional reversible anonymization before transmission.
    anonymizer: Optional[Anonymizer] = None
    contract_text = parsed.text
    if options.anonymize_before_analysis:
        anonymizer = Anonymizer()
        contract_text = anonymizer.anonymize(contract_text)

    # 2. Contract-type detection → type-specific benchmark context.
    progress("detect_type", 0.15)
    _check_cancel()
    contract_type = _detect_contract_type(client, model, contract_text)

    # 3. Build system context (framing + jurisdiction + benchmarks).
    jur_ctx = jurisdiction.build_prompt_context(options)
    bench_ctx = benchmarks.build_prompt_context(contract_type)
    system_blocks = _system_blocks(options, jur_ctx, bench_ctx)

    # 4. Main structured analysis.
    progress("analyze", 0.25)
    _check_cancel()
    analysis = _run_main_analysis(
        client, model, system_blocks, contract_text, progress, _check_cancel
    )

    # Order the playbook deterministically (MUST_FIX / walk-away first).
    analysis.negotiation_playbook = playbook.order(analysis.negotiation_playbook)

    # Restore real identifiers into anything Claude quoted back.
    if anonymizer is not None:
        analysis = _restore(anonymizer, analysis, ContractAnalysis)

    result = AnalysisResult(options=options, analysis=analysis)

    # 5. Optional user-concern advice (grounded in the finished analysis).
    if options.user_concern and options.user_concern.strip():
        progress("concern", 0.9)
        _check_cancel()
        advice = _run_concern_advice(client, model, options, analysis)
        if advice is not None and anonymizer is not None:
            advice = _restore(anonymizer, advice, ConcernAdvice)
        result.concern_advice = advice

    progress("done", 1.0)
    return result


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
def _client(options: AnalysisOptions):
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise AnalyzerError("anthropic 패키지가 설치되지 않았습니다.") from exc
    key = api_key.load_key()
    if not key:
        raise AnalyzerError("API 키가 설정되지 않았습니다. 설정 화면에서 키를 입력하세요.")
    return anthropic.Anthropic(api_key=key)


def _anthropic_errors():
    import anthropic

    return anthropic


# --------------------------------------------------------------------------- #
# System prompt blocks (with prompt caching on the stable framing block)
# --------------------------------------------------------------------------- #
def _system_blocks(options: AnalysisOptions, jur_ctx: str, bench_ctx: str) -> list[dict]:
    framing = prompts.build_framing_block(options)
    context = prompts.build_context_block(jur_ctx, bench_ctx)
    return [
        {"type": "text", "text": framing, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": context},
    ]


# --------------------------------------------------------------------------- #
# Contract-type detection (cheap pre-pass; tolerant of failure)
# --------------------------------------------------------------------------- #
class _TypeDetection(BaseModel):
    contract_type: ContractType


def _detect_contract_type(client, model: str, contract_text: str) -> ContractType:
    try:
        resp = client.messages.parse(
            model=model,
            max_tokens=512,
            messages=[
                {"role": "user", "content": prompts.build_type_detection_prompt(contract_text)}
            ],
            output_format=_TypeDetection,
        )
        parsed = resp.parsed_output
        if parsed is not None:
            return parsed.contract_type
    except Exception:
        pass
    return ContractType.UNKNOWN


# --------------------------------------------------------------------------- #
# Main analysis: structured → fallback → corrective retry
# --------------------------------------------------------------------------- #
def _run_main_analysis(
    client,
    model: str,
    system_blocks: list[dict],
    contract_text: str,
    progress: ProgressFn,
    check_cancel: Callable[[], None],
) -> ContractAnalysis:
    schema = _strict_schema(ContractAnalysis)
    user_prompt = prompts.build_analysis_user_prompt(contract_text)
    messages = [{"role": "user", "content": user_prompt}]

    # Attempt A: strict structured output.
    try:
        text = _stream_text(
            client, model, system_blocks, messages,
            max_tokens=config.ANALYSIS_MAX_TOKENS,
            output_format=schema,
            progress=progress,
        )
        return _validate(ContractAnalysis, text)
    except _BadSchemaRequest:
        pass  # fall through to plain JSON mode
    except (ValidationError, json.JSONDecodeError) as exc:
        check_cancel()
        return _corrective_retry(
            client, model, system_blocks, messages, schema, ContractAnalysis, str(exc)
        )

    # Attempt B: plain JSON instruction (no output_config.format).
    plain_messages = [
        {
            "role": "user",
            "content": user_prompt
            + "\n\n반드시 아래 JSON 스키마에 정확히 맞는 단일 JSON 객체만 출력하라. "
            "코드펜스나 설명 없이 JSON 만.\n\n"
            + json.dumps(schema, ensure_ascii=False),
        }
    ]
    text = _stream_text(
        client, model, system_blocks, plain_messages,
        max_tokens=config.ANALYSIS_MAX_TOKENS,
        output_format=None,
        progress=progress,
    )
    return _validate(ContractAnalysis, text)


def _corrective_retry(
    client, model, system_blocks, messages, schema, schema_model, error_text
):
    corrective = list(messages) + [
        {
            "role": "user",
            "content": (
                "직전 출력이 스키마 검증에 실패했다. 오류: "
                f"{error_text[:500]}. 동일 내용을 스키마에 정확히 맞는 JSON 으로 다시 출력하라."
            ),
        }
    ]
    text = _stream_text(
        client, model, system_blocks, corrective,
        max_tokens=config.ANALYSIS_MAX_TOKENS,
        output_format=schema,
        progress=None,
    )
    return _validate(schema_model, text)


# --------------------------------------------------------------------------- #
# Concern advice
# --------------------------------------------------------------------------- #
def _run_concern_advice(
    client, model: str, options: AnalysisOptions, analysis: ContractAnalysis
) -> Optional[ConcernAdvice]:
    schema = _strict_schema(ConcernAdvice)
    analysis_json = analysis.model_dump_json()
    system = [
        {
            "type": "text",
            "text": prompts.build_concern_system_prompt(options),
            "cache_control": {"type": "ephemeral"},
        }
    ]
    messages = [
        {
            "role": "user",
            "content": prompts.build_concern_user_prompt(options.user_concern or "", analysis_json),
        }
    ]
    try:
        text = _stream_text(
            client, model, system, messages,
            max_tokens=config.CONCERN_MAX_TOKENS,
            output_format=schema,
            progress=None,
        )
        return _validate(ConcernAdvice, text)
    except _BadSchemaRequest:
        plain = [
            {
                "role": "user",
                "content": messages[0]["content"]
                + "\n\n스키마에 맞는 단일 JSON 객체만 출력하라.\n\n"
                + json.dumps(schema, ensure_ascii=False),
            }
        ]
        text = _stream_text(
            client, model, system, plain,
            max_tokens=config.CONCERN_MAX_TOKENS,
            output_format=None,
            progress=None,
        )
        return _validate(ConcernAdvice, text)
    except (ValidationError, json.JSONDecodeError):
        return None  # advice is best-effort; never block the main result


# --------------------------------------------------------------------------- #
# Streaming helper
# --------------------------------------------------------------------------- #
class _BadSchemaRequest(Exception):
    """The API rejected the structured-output schema; caller should fall back."""


def _stream_text(
    client,
    model: str,
    system_blocks: list[dict],
    messages: list[dict],
    *,
    max_tokens: int,
    output_format: Optional[dict],
    progress: Optional[ProgressFn],
) -> str:
    anthropic = _anthropic_errors()
    output_config: dict = {"effort": config.ANALYSIS_EFFORT}
    if output_format is not None:
        output_config["format"] = {"type": "json_schema", "schema": output_format}

    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config=output_config,
        system=system_blocks,
        messages=messages,
    )
    try:
        with client.messages.stream(**kwargs) as stream:
            if progress is not None:
                _drain_with_progress(stream, progress)
            final = stream.get_final_message()
    except anthropic.BadRequestError as exc:
        # Most often a schema the strict validator won't accept.
        if output_format is not None:
            raise _BadSchemaRequest(str(exc)) from exc
        raise AnalyzerError(f"요청 오류: {getattr(exc, 'message', exc)}") from exc
    except anthropic.AuthenticationError as exc:
        raise AnalyzerError("API 키 인증에 실패했습니다. 설정에서 키를 확인하세요.") from exc
    except anthropic.RateLimitError as exc:
        raise AnalyzerError("사용량 제한에 걸렸습니다. 잠시 후 다시 시도하세요.") from exc
    except anthropic.APIConnectionError as exc:
        raise AnalyzerError("네트워크 오류로 분석에 실패했습니다.") from exc

    if final.stop_reason == "refusal":
        raise AnalyzerError("모델이 이 요청을 거부했습니다(안전상의 이유).")
    return _first_text(final)


def _drain_with_progress(stream, progress: ProgressFn) -> None:
    """Advance the progress bar from 0.25→0.8 as analysis tokens stream in."""
    frac = 0.25
    for event in stream:
        etype = getattr(event, "type", "")
        if etype == "content_block_delta" and frac < 0.8:
            frac = min(0.8, frac + 0.01)
            progress("analyze", frac)


def _first_text(message) -> str:
    for block in message.content:
        if getattr(block, "type", "") == "text":
            return block.text
    raise AnalyzerError("모델 응답에서 텍스트를 찾지 못했습니다.")


# --------------------------------------------------------------------------- #
# Schema / validation helpers
# --------------------------------------------------------------------------- #
def _strict_schema(model_cls: type[BaseModel]) -> dict:
    schema = model_cls.model_json_schema()
    _harden(schema)
    return schema


def _harden(node) -> None:
    """Force additionalProperties:false on every object node (strict mode)."""
    if isinstance(node, dict):
        if node.get("type") == "object" and "additionalProperties" not in node:
            node["additionalProperties"] = False
        for value in node.values():
            _harden(value)
    elif isinstance(node, list):
        for item in node:
            _harden(item)


def _validate(model_cls: type[BaseModel], text: str):
    payload = _extract_json(text)
    return model_cls.model_validate(payload)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        # Strip a ```json … ``` fence if the model added one.
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _restore(anonymizer: Anonymizer, obj: BaseModel, model_cls: type[BaseModel]):
    restored = anonymizer.restore(obj.model_dump_json())
    return model_cls.model_validate_json(restored)
