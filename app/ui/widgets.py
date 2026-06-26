"""Reusable widgets: cards, risk badges, score card, collapsible clause item."""
from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.models import AIClause, RiskLevel


def _v(x) -> str:
    return x.value if isinstance(x, Enum) else (str(x) if x is not None else "")


# Risk colors used on screen only — the saved report stays monochrome.
RISK_COLORS = {
    RiskLevel.RED.value: "#b00020",
    RiskLevel.YELLOW.value: "#9a6700",
    RiskLevel.GREEN.value: "#1b7a36",
}
RISK_BG = {
    RiskLevel.RED.value: "#fdecef",
    RiskLevel.YELLOW.value: "#fff7e6",
    RiskLevel.GREEN.value: "#eaf6ee",
}


class Card(QFrame):
    """A bordered container with an optional title."""

    def __init__(self, title: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(8)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("CardTitle")
            self._layout.addWidget(lbl)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)


class RiskBadge(QLabel):
    def __init__(self, flag, parent: QWidget | None = None):
        super().__init__(parent)
        value = _v(flag) or RiskLevel.GREEN.value
        self.setText(value)
        self.setAlignment(Qt.AlignCenter)
        color = RISK_COLORS.get(value, "#333")
        bg = RISK_BG.get(value, "#eee")
        self.setStyleSheet(
            f"color:{color}; background:{bg}; border:1px solid {color};"
            "border-radius:4px; padding:1px 8px; font-weight:600;"
        )
        self.setFixedHeight(22)


class ScoreCard(Card):
    """Overall risk score + recommendation + sub-scores."""

    def __init__(self, result, parent: QWidget | None = None):
        super().__init__(title="종합 위험 점수", parent=parent)
        rs = result.risk_score
        row = QHBoxLayout()
        score = QLabel(f"{rs.overall}")
        score.setStyleSheet("font-size:40px; font-weight:700;")
        outof = QLabel("/ 100")
        outof.setStyleSheet("color:#666; font-size:16px;")
        rec = QLabel(_v(result.recommendation))
        rec.setStyleSheet("font-size:18px; font-weight:600; margin-left:18px;")
        row.addWidget(score)
        row.addWidget(outof, alignment=Qt.AlignBottom)
        row.addStretch(1)
        row.addWidget(QLabel("권고:"), alignment=Qt.AlignVCenter)
        row.addWidget(rec)
        wrap = QWidget()
        wrap.setLayout(row)
        self.add(wrap)

        sub = QLabel(
            f"저작권 {rs.copyright}   ·   수익 {rs.revenue}   ·   "
            f"통제 {rs.control}   ·   법적구제 {rs.legal_remedy}"
        )
        sub.setStyleSheet("color:#444;")
        self.add(sub)

        stats = QLabel(
            f"RED 조항: {result.red_clause_count}    walk-away 이슈: {result.walk_away_count}"
        )
        stats.setStyleSheet("color:#444; font-weight:600;")
        self.add(stats)

        summary = QLabel(rs.summary)
        summary.setWordWrap(True)
        summary.setStyleSheet("color:#333; margin-top:4px;")
        self.add(summary)


class ClauseItem(QFrame):
    """Collapsible clause card: header (id/title/flag) + expandable detail."""

    def __init__(self, clause: AIClause, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self._toggle = QToolButton()
        self._toggle.setArrowType(Qt.RightArrow)
        self._toggle.setStyleSheet("border:none;")
        self._toggle.clicked.connect(self._on_toggle)
        title = QLabel(f"[{clause.id}] {clause.title}")
        title.setStyleSheet("font-weight:600;")
        title.setWordWrap(True)
        header.addWidget(self._toggle)
        header.addWidget(title, 1)
        header.addWidget(RiskBadge(clause.flag))
        hw = QWidget()
        hw.setLayout(header)
        layout.addWidget(hw)

        self._detail = QWidget()
        dl = QVBoxLayout(self._detail)
        dl.setContentsMargins(28, 4, 4, 4)
        dl.setSpacing(6)
        dl.addWidget(self._field("쟁점 / 집행가능성",
                                 f"{_v(clause.issue_type)}  ·  {_v(clause.enforceability)}"))
        dl.addWidget(self._quote("원문", clause.verbatim_text))
        dl.addWidget(self._field("요약", clause.summary))
        dl.addWidget(self._field("당신에게 미치는 영향", clause.impact_on_you))
        dl.addWidget(self._field("제안 수정안", clause.proposed_revision))
        dl.addWidget(self._field("법적 근거", clause.legal_basis))
        self._detail.setVisible(False)
        layout.addWidget(self._detail)

    def _on_toggle(self) -> None:
        shown = not self._detail.isVisible()
        self._detail.setVisible(shown)
        self._toggle.setArrowType(Qt.DownArrow if shown else Qt.RightArrow)

    @staticmethod
    def _field(label: str, value: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        lab = QLabel(label)
        lab.setStyleSheet("color:#666; font-size:11px;")
        val = QLabel(value or "—")
        val.setWordWrap(True)
        lay.addWidget(lab)
        lay.addWidget(val)
        return w

    @staticmethod
    def _quote(label: str, value: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        lab = QLabel(label)
        lab.setStyleSheet("color:#666; font-size:11px;")
        val = QLabel(value or "—")
        val.setWordWrap(True)
        val.setStyleSheet(
            "font-style:italic; background:#f6f6f6; border-left:3px solid #ccc;"
            "padding:6px 8px;"
        )
        lay.addWidget(lab)
        lay.addWidget(val)
        return w
