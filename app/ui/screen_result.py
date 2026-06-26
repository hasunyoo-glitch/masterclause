"""Step 4: result summary, concern advice, clauses, playbook, save actions (plan §5.1 step 4)."""
from __future__ import annotations

import os
import subprocess
import sys
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.state import AppState
from app.ui.widgets import Card, ClauseItem, RiskBadge, ScoreCard


def _v(x) -> str:
    return x.value if isinstance(x, Enum) else (str(x) if x is not None else "")


class ResultScreen(QWidget):
    new_analysis_requested = Signal()

    def __init__(self, state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = state
        self._content: QWidget | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(12)

        title = QLabel("4단계 · 분석 결과")
        title.setObjectName("StepTitle")
        root.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        root.addWidget(self._scroll, 1)

        nav = QHBoxLayout()
        self._open_folder = QPushButton("저장 폴더 열기")
        self._open_folder.clicked.connect(self._on_open_folder)
        self._open_report = QPushButton("리포트 열기")
        self._open_report.clicked.connect(self._on_open_report)
        nav.addWidget(self._open_folder)
        nav.addWidget(self._open_report)
        nav.addStretch(1)
        new_btn = QPushButton("새 분석")
        new_btn.setObjectName("Primary")
        new_btn.clicked.connect(self.new_analysis_requested.emit)
        nav.addWidget(new_btn)
        nw = QWidget()
        nw.setLayout(nav)
        root.addWidget(nw)

    # -- Populate ---------------------------------------------------------- #
    def populate(self) -> None:
        result = self._state.result
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(2, 2, 16, 2)
        lay.setSpacing(14)

        if result is None:
            lay.addWidget(QLabel("결과가 없습니다."))
            self._scroll.setWidget(container)
            return

        # Saved-path notice
        if self._state.written_paths:
            paths = "\n".join(self._state.written_paths)
            note = Card("저장 완료")
            lbl = QLabel(f"리포트가 다음 위치에 저장되었습니다:\n{paths}")
            lbl.setWordWrap(True)
            note.add(lbl)
            lay.addWidget(note)

        # Score card
        lay.addWidget(ScoreCard(result))

        # Concern advice — prominent, near the top
        if result.concern_advice is not None:
            ca = result.concern_advice
            card = Card("당신의 우려에 대한 조언")
            crow = QHBoxLayout()
            crow.addWidget(QLabel("우려 관점 위험도:"))
            crow.addWidget(RiskBadge(ca.risk_assessment))
            crow.addStretch(1)
            cw = QWidget()
            cw.setLayout(crow)
            card.add(cw)
            concern_q = QLabel(f"“{ca.concern_text}”")
            concern_q.setWordWrap(True)
            concern_q.setStyleSheet("font-style:italic; color:#555;")
            card.add(concern_q)
            ans = QLabel(ca.direct_answer)
            ans.setWordWrap(True)
            card.add(ans)
            if ca.relevant_clause_ids:
                rel = QLabel("관련 조항: " + ", ".join(ca.relevant_clause_ids))
                rel.setStyleSheet("color:#666;")
                card.add(rel)
            for action in ca.recommended_actions:
                a = QLabel(f"•  {action}")
                a.setWordWrap(True)
                card.add(a)
            lay.addWidget(card)

        # Clauses
        clause_card = Card(f"AI 관련 조항 ({len(result.ai_clauses)})")
        if not result.ai_clauses:
            clause_card.add(QLabel("탐지된 조항이 없습니다."))
        for clause in result.ai_clauses:
            clause_card.add(ClauseItem(clause))
        lay.addWidget(clause_card)

        # Playbook
        pb_card = Card(f"협상 플레이북 ({len(result.negotiation_playbook)})")
        if not result.negotiation_playbook:
            pb_card.add(QLabel("항목이 없습니다."))
        for item in result.negotiation_playbook:
            tag = "★ walk-away  " if item.walk_away else ""
            head = QLabel(f"{tag}[{_v(item.priority)}] {item.issue}")
            head.setStyleSheet("font-weight:600;")
            head.setWordWrap(True)
            pb_card.add(head)
            strat = QLabel(item.strategy)
            strat.setWordWrap(True)
            strat.setStyleSheet("color:#444; margin-bottom:6px;")
            pb_card.add(strat)
        lay.addWidget(pb_card)

        # Disclaimer
        disc = Card("면책 고지")
        d = QLabel(result.disclaimer)
        d.setWordWrap(True)
        d.setStyleSheet("color:#666;")
        disc.add(d)
        lay.addWidget(disc)

        lay.addStretch(1)
        self._scroll.setWidget(container)

    # -- Actions ----------------------------------------------------------- #
    def _first_report(self) -> str | None:
        return self._state.written_paths[0] if self._state.written_paths else None

    def _on_open_folder(self) -> None:
        report = self._first_report()
        folder = str(Path(report).parent) if report else (self._state.output_path or "")
        if folder and os.path.isdir(folder):
            self._open_path(folder)

    def _on_open_report(self) -> None:
        report = self._first_report()
        if report and os.path.exists(report):
            self._open_path(report)

    @staticmethod
    def _open_path(path: str) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception:
            pass
