"""Step 1: file selection + output path (plan §5.1 step 1)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.state import AppState
from app.ui.widgets import Card
from core import parser


class UploadScreen(QWidget):
    next_requested = Signal()

    def __init__(self, state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = state
        self.setAcceptDrops(True)
        self._build()

    # -- UI ---------------------------------------------------------------- #
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel("1단계 · 계약서 선택")
        title.setObjectName("StepTitle")
        root.addWidget(title)

        # File card
        file_card = Card("계약서 파일 (PDF / DOCX)")
        self._file_label = QLabel("선택된 파일이 없습니다. 파일을 끌어다 놓거나 선택하세요.")
        self._file_label.setWordWrap(True)
        pick = QPushButton("파일 선택…")
        pick.clicked.connect(self._pick_file)
        row = QHBoxLayout()
        row.addWidget(self._file_label, 1)
        row.addWidget(pick)
        rw = QWidget()
        rw.setLayout(row)
        file_card.add(rw)
        self._preview = QLabel("")
        self._preview.setWordWrap(True)
        self._preview.setStyleSheet("color:#555; background:#f6f6f6; padding:8px; border-radius:4px;")
        self._preview.setVisible(False)
        file_card.add(self._preview)
        root.addWidget(file_card)

        # Output card
        out_card = Card("리포트 저장 위치")
        self._out_label = QLabel("저장 폴더가 선택되지 않았습니다.")
        self._out_label.setWordWrap(True)
        out_btn = QPushButton("폴더 선택…")
        out_btn.clicked.connect(self._pick_output)
        save_as = QPushButton("파일명까지 지정…")
        save_as.clicked.connect(self._pick_output_file)
        orow = QHBoxLayout()
        orow.addWidget(self._out_label, 1)
        orow.addWidget(out_btn)
        orow.addWidget(save_as)
        ow = QWidget()
        ow.setLayout(orow)
        out_card.add(ow)
        root.addWidget(out_card)

        root.addStretch(1)

        nav = QHBoxLayout()
        nav.addStretch(1)
        self._next = QPushButton("다음 →")
        self._next.setObjectName("Primary")
        self._next.setEnabled(False)
        self._next.clicked.connect(self._go_next)
        nav.addWidget(self._next)
        nw = QWidget()
        nw.setLayout(nav)
        root.addWidget(nw)

    # -- Drag & drop ------------------------------------------------------- #
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self._load_file(path)
                break

    # -- Actions ----------------------------------------------------------- #
    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "계약서 선택", "", "계약서 (*.pdf *.docx)"
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        suffix = Path(path).suffix.lower()
        if suffix not in parser.SUPPORTED_SUFFIXES:
            QMessageBox.warning(self, "지원하지 않는 형식", "PDF 또는 DOCX 파일만 지원합니다.")
            return
        try:
            parsed = parser.parse(path)
        except parser.ParserError as exc:
            QMessageBox.critical(self, "파싱 실패", str(exc))
            return
        self._state.input_file_path = path
        self._state.parsed = parsed
        self._file_label.setText(path)
        meta = (
            f"페이지 {parsed.page_count} · 문단 {parsed.paragraph_count} · "
            f"{parsed.char_count:,}자\n\n{parsed.preview()}"
        )
        self._preview.setText(meta)
        self._preview.setVisible(True)
        # Default output folder = the contract's folder, if none chosen yet.
        if not self._state.output_path:
            self._state.output_path = str(Path(path).parent)
            self._out_label.setText(self._state.output_path)
        self._refresh_next()

    def _pick_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "리포트 저장 폴더 선택")
        if folder:
            self._state.output_path = folder
            self._out_label.setText(folder)
            self._refresh_next()

    def _pick_output_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "리포트 저장 파일명", "contract_analysis.docx", "Word 문서 (*.docx)"
        )
        if path:
            self._state.output_path = path
            self._out_label.setText(path)
            self._refresh_next()

    def _refresh_next(self) -> None:
        self._next.setEnabled(bool(self._state.input_file_path and self._state.output_path))

    def _go_next(self) -> None:
        if not (self._state.input_file_path and self._state.output_path):
            return
        self.next_requested.emit()

    def refresh(self) -> None:
        """Re-sync labels when navigating back to this screen."""
        if self._state.input_file_path:
            self._file_label.setText(self._state.input_file_path)
        if self._state.output_path:
            self._out_label.setText(self._state.output_path)
        self._refresh_next()
