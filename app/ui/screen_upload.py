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

from app.i18n import tr
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

        title = QLabel(tr("upload.title"))
        title.setObjectName("StepTitle")
        root.addWidget(title)

        # File card
        file_card = Card(tr("upload.file_card"))
        self._file_label = QLabel(tr("upload.no_file"))
        self._file_label.setWordWrap(True)
        pick = QPushButton(tr("upload.pick_file"))
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
        out_card = Card(tr("upload.out_card"))
        self._out_label = QLabel(tr("upload.no_out"))
        self._out_label.setWordWrap(True)
        out_btn = QPushButton(tr("upload.pick_folder"))
        out_btn.clicked.connect(self._pick_output)
        save_as = QPushButton(tr("upload.pick_filename"))
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
        self._next = QPushButton(tr("common.next"))
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
            self, tr("upload.dlg_select"), "", tr("upload.filter_contract")
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        suffix = Path(path).suffix.lower()
        if suffix not in parser.SUPPORTED_SUFFIXES:
            QMessageBox.warning(self, tr("upload.unsupported_title"),
                                tr("upload.unsupported_body"))
            return
        try:
            parsed = parser.parse(path)
        except parser.ParserError as exc:
            QMessageBox.critical(self, tr("upload.parse_fail"), str(exc))
            return
        self._state.input_file_path = path
        self._state.parsed = parsed
        self._file_label.setText(path)
        meta = tr("upload.meta", pages=parsed.page_count,
                  paras=parsed.paragraph_count, chars=parsed.char_count)
        meta = f"{meta}\n\n{parsed.preview()}"
        self._preview.setText(meta)
        self._preview.setVisible(True)
        # Default output folder = the contract's folder, if none chosen yet.
        if not self._state.output_path:
            self._state.output_path = str(Path(path).parent)
            self._out_label.setText(self._state.output_path)
        self._refresh_next()

    def _pick_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("upload.dlg_folder"))
        if folder:
            self._state.output_path = folder
            self._out_label.setText(folder)
            self._refresh_next()

    def _pick_output_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("upload.dlg_filename"), "contract_analysis.docx", tr("upload.filter_word")
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
