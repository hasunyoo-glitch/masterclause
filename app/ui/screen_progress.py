"""Step 3: analysis progress + cancel (plan §5.1 step 3)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProgressScreen(QWidget):
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel("3단계 · 분석 진행")
        title.setObjectName("StepTitle")
        root.addWidget(title)

        root.addStretch(1)

        self._stage = QLabel("준비 중…")
        self._stage.setAlignment(Qt.AlignCenter)
        self._stage.setStyleSheet("font-size:15px;")
        root.addWidget(self._stage)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        root.addWidget(self._bar)

        steps = QLabel("파싱 → (익명화) → AI 분석 → 관할 매핑 → 벤치마크 → 리포트 생성")
        steps.setAlignment(Qt.AlignCenter)
        steps.setStyleSheet("color:#888;")
        root.addWidget(steps)

        root.addStretch(2)

        nav = QHBoxLayout()
        nav.addStretch(1)
        self._cancel = QPushButton("취소")
        self._cancel.clicked.connect(self._on_cancel)
        nav.addWidget(self._cancel)
        nw = QWidget()
        nw.setLayout(nav)
        root.addWidget(nw)

    def reset(self) -> None:
        self._bar.setValue(0)
        self._stage.setText("준비 중…")
        self._cancel.setEnabled(True)

    def update_progress(self, label: str, percent: int) -> None:
        self._stage.setText(label)
        self._bar.setValue(percent)

    def _on_cancel(self) -> None:
        self._cancel.setEnabled(False)
        self._stage.setText("취소하는 중…")
        self.cancel_requested.emit()
