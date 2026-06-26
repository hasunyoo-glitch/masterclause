"""Shared application state and persisted user settings (plan §5.2).

Holds the selected file, parsed preview, output path and option choices, then
serializes them into ``AnalysisOptions`` when the user starts the analysis.
Defaults persist to ``%APPDATA%/ai-contract-analyzer/config.json`` (never the key).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

import config
from core.models import (
    AnalysisOptions,
    AnalysisResult,
    Jurisdiction,
    OutputLanguage,
    Perspective,
    USState,
)
from core.parser import ParsedDocument


# --------------------------------------------------------------------------- #
# Settings persistence (defaults only — no API key)
# --------------------------------------------------------------------------- #
def load_settings() -> dict:
    data = dict(config.DEFAULTS)
    try:
        if config.CONFIG_PATH.exists():
            with config.CONFIG_PATH.open(encoding="utf-8") as fh:
                data.update(json.load(fh))
    except Exception:
        pass
    return data


def save_settings(settings: dict) -> None:
    try:
        clean = {k: v for k, v in settings.items() if k != "api_key"}
        with config.CONFIG_PATH.open("w", encoding="utf-8") as fh:
            json.dump(clean, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Live app state
# --------------------------------------------------------------------------- #
@dataclass
class AppState:
    # Step 1
    input_file_path: Optional[str] = None
    parsed: Optional[ParsedDocument] = None
    output_path: Optional[str] = None

    # Step 2 — option choices (stored as enums/strings)
    perspective: str = field(default_factory=lambda: config.DEFAULTS["perspective"])
    output_language: str = field(default_factory=lambda: config.DEFAULTS["output_language"])
    jurisdiction: str = field(default_factory=lambda: config.DEFAULTS["jurisdiction"])
    us_state: Optional[str] = None
    us_state_other: Optional[str] = None
    output_format: str = field(default_factory=lambda: config.DEFAULTS["output_format"])
    user_concern: Optional[str] = None
    anonymize_before_analysis: bool = False
    zero_retention: bool = False
    model: Optional[str] = None

    # Result
    result: Optional[AnalysisResult] = None
    written_paths: list[str] = field(default_factory=list)

    def apply_defaults(self, settings: dict) -> None:
        self.perspective = settings.get("perspective", self.perspective)
        self.output_language = settings.get("output_language", self.output_language)
        self.jurisdiction = settings.get("jurisdiction", self.jurisdiction)
        self.us_state = settings.get("us_state", self.us_state)
        self.output_format = settings.get("output_format", self.output_format)
        self.anonymize_before_analysis = settings.get(
            "anonymize_before_analysis", self.anonymize_before_analysis
        )
        self.zero_retention = settings.get("zero_retention", self.zero_retention)
        self.model = settings.get("model", self.model)

    def to_options(self) -> AnalysisOptions:
        return AnalysisOptions(
            input_file_path=self.input_file_path or "",
            output_path=self.output_path or "",
            perspective=Perspective(self.perspective),
            output_language=OutputLanguage(self.output_language),
            jurisdiction=Jurisdiction(self.jurisdiction),
            us_state=USState(self.us_state) if self.us_state else None,
            us_state_other=self.us_state_other,
            output_format=self.output_format,  # type: ignore[arg-type]
            user_concern=(self.user_concern or None),
            anonymize_before_analysis=self.anonymize_before_analysis,
            zero_retention=self.zero_retention,
            model=self.model or config.MODEL_PRIMARY,
        )
