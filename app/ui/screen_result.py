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

from app.i18n import tr
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

        title = QLabel(tr("result.title"))
        title.setObjectName("StepTitle")
        root.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        root.addWidget(self._scroll, 1)

        nav = QHBoxLayout()
        self._open_folder = QPushButton(tr("result.open_folder"))
        self._open_folder.clicked.connect(self._on_open_folder)
        self._open_report = QPushButton(tr("result.open_report"))
        self._open_report.clicked.connect(self._on_open_report)
        nav.addWidget(self._open_folder)
        nav.addWidget(self._open_report)
        nav.addStretch(1)
        new_btn = QPushButton(tr("result.new"))
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
            lay.addWidget(QLabel(tr("result.empty")))
            self._scroll.setWidget(container)
            return

        # Saved-path notice
        if self._state.written_paths:
            paths = "\n".join(self._state.written_paths)
            note = Card(tr("result.saved_title"))
            lbl = QLabel(tr("result.saved_body", paths=paths))
            lbl.setWordWrap(True)
            note.add(lbl)
            lay.addWidget(note)

        # Score card
        lay.addWidget(ScoreCard(result))

        # Concern advice — prominent, near the top
        if result.concern_advice is not None:
            ca = result.concern_advice
            card = Card(tr("result.concern"))
            crow = QHBoxLayout()
            crow.addWidget(QLabel(tr("result.concern_risk")))
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
                rel = QLabel(tr("result.related", ids=", ".join(ca.relevant_clause_ids)))
                rel.setStyleSheet("color:#666;")
                card.add(rel)
            for action in ca.recommended_actions:
                a = QLabel(f"•  {action}")
                a.setWordWrap(True)
                card.add(a)
            lay.addWidget(card)

        # Clauses
        clause_card = Card(tr("result.clauses", n=len(result.ai_clauses)))
        if not result.ai_clauses:
            clause_card.add(QLabel(tr("result.no_clauses")))
        for clause in result.ai_clauses:
            clause_card.add(ClauseItem(clause))
        lay.addWidget(clause_card)

        # Playbook
        pb_card = Card(tr("result.playbook", n=len(result.negotiation_playbook)))
        if not result.negotiation_playbook:
            pb_card.add(QLabel(tr("result.no_items")))
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
        disc = Card(tr("result.disclaimer"))
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
