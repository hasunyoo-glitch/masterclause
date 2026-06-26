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

from app.i18n import tr, tr_stage


class ProgressScreen(QWidget):
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel(tr("progress.title"))
        title.setObjectName("StepTitle")
        root.addWidget(title)

        root.addStretch(1)

        self._stage = QLabel(tr("stage.ready"))
        self._stage.setAlignment(Qt.AlignCenter)
        self._stage.setStyleSheet("font-size:15px;")
        root.addWidget(self._stage)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        root.addWidget(self._bar)

        steps = QLabel(tr("progress.steps"))
        steps.setAlignment(Qt.AlignCenter)
        steps.setStyleSheet("color:#888;")
        root.addWidget(steps)

        root.addStretch(2)

        nav = QHBoxLayout()
        nav.addStretch(1)
        self._cancel = QPushButton(tr("common.cancel"))
        self._cancel.clicked.connect(self._on_cancel)
        nav.addWidget(self._cancel)
        nw = QWidget()
        nw.setLayout(nav)
        root.addWidget(nw)

    def reset(self) -> None:
        self._bar.setValue(0)
        self._stage.setText(tr("stage.ready"))
        self._cancel.setEnabled(True)

    def update_progress(self, stage_key: str, percent: int) -> None:
        self._stage.setText(tr_stage(stage_key))
        self._bar.setValue(percent)

    def _on_cancel(self) -> None:
        self._cancel.setEnabled(False)
        self._stage.setText(tr("progress.cancelling"))
        self.cancel_requested.emit()
