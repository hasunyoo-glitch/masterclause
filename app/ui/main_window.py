"""Main window: QStackedWidget navigation + worker lifecycle (plan §3, §5)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import config
from app import state as state_mod
from app.state import AppState
from app.ui.screen_options import OptionsScreen
from app.ui.screen_progress import ProgressScreen
from app.ui.screen_result import ResultScreen
from app.ui.screen_settings import SettingsScreen
from app.ui.screen_upload import UploadScreen
from app.worker import AnalysisWorker
from core import api_key

# Stack indices
S_UPLOAD = 0
S_OPTIONS = 1
S_PROGRESS = 2
S_RESULT = 3
S_SETTINGS = 4


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.resize(840, 720)
        self.setMinimumSize(420, 420)

        self._state = AppState()
        self._state.apply_defaults(state_mod.load_settings())
        self._worker: AnalysisWorker | None = None
        self._return_index = S_UPLOAD

        self._build()
        self._route_initial()

    # -- Layout ------------------------------------------------------------ #
    def _build(self) -> None:
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setObjectName("Header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 12, 20, 12)
        title = QLabel(config.APP_NAME)
        title.setObjectName("AppTitle")
        hl.addWidget(title)
        hl.addStretch(1)
        self._settings_btn = QPushButton("설정")
        self._settings_btn.clicked.connect(self._open_settings)
        hl.addWidget(self._settings_btn)
        outer.addWidget(header)

        # Stacked screens
        self._stack = QStackedWidget()
        self._upload = UploadScreen(self._state)
        self._options = OptionsScreen(self._state)
        self._progress = ProgressScreen()
        self._result = ResultScreen(self._state)
        self._settings = SettingsScreen(self._state)

        # Wrap the tall screens in scroll areas so every control stays reachable
        # when the window is not maximized. The result screen manages its own
        # scroll (with fixed action buttons), so it is added directly.
        self._stack.addWidget(self._scrollable(self._upload))    # 0
        self._stack.addWidget(self._scrollable(self._options))   # 1
        self._stack.addWidget(self._progress)                    # 2
        self._stack.addWidget(self._result)                      # 3
        self._stack.addWidget(self._scrollable(self._settings))  # 4
        outer.addWidget(self._stack, 1)

        self.setCentralWidget(central)

        # Wire signals (connect to the inner screens, not the scroll wrappers)
        self._upload.next_requested.connect(self._goto_options)
        self._options.back_requested.connect(self._goto_upload)
        self._options.start_requested.connect(self._start_analysis)
        self._progress.cancel_requested.connect(self._cancel_analysis)
        self._result.new_analysis_requested.connect(self._goto_upload_fresh)
        self._settings.closed.connect(self._close_settings)
        self._settings.key_saved.connect(self._on_key_saved)

    @staticmethod
    def _scrollable(widget: QWidget) -> QScrollArea:
        """Wrap a screen so it scrolls vertically when the window is small."""
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        area.setWidget(widget)
        return area

    # -- Initial routing --------------------------------------------------- #
    def _route_initial(self) -> None:
        if not api_key.has_key():
            self._return_index = S_UPLOAD
            self._stack.setCurrentIndex(S_SETTINGS)
            QMessageBox.information(
                self, "API 키 필요",
                "분석을 시작하려면 먼저 Anthropic API 키를 설정하세요.",
            )
        else:
            self._stack.setCurrentIndex(S_UPLOAD)

    # -- Navigation -------------------------------------------------------- #
    def _goto_upload(self) -> None:
        self._upload.refresh()
        self._stack.setCurrentIndex(S_UPLOAD)

    def _goto_upload_fresh(self) -> None:
        self._state.result = None
        self._state.written_paths = []
        self._upload.refresh()
        self._stack.setCurrentIndex(S_UPLOAD)

    def _goto_options(self) -> None:
        self._stack.setCurrentIndex(S_OPTIONS)

    def _open_settings(self) -> None:
        if self._stack.currentIndex() != S_SETTINGS:
            self._return_index = self._stack.currentIndex()
        self._settings.refresh()
        self._stack.setCurrentIndex(S_SETTINGS)

    def _close_settings(self) -> None:
        target = self._return_index if self._return_index != S_SETTINGS else S_UPLOAD
        self._stack.setCurrentIndex(target)

    def _on_key_saved(self) -> None:
        # If we were forced here at startup, move on to the upload screen.
        if self._return_index == S_UPLOAD:
            self._stack.setCurrentIndex(S_UPLOAD)

    # -- Analysis lifecycle ------------------------------------------------ #
    def _start_analysis(self) -> None:
        if not api_key.has_key():
            QMessageBox.warning(self, "API 키 필요", "분석 전에 API 키를 설정하세요.")
            self._open_settings()
            return
        try:
            options = self._state.to_options()
        except Exception as exc:  # malformed option set
            QMessageBox.critical(self, "옵션 오류", str(exc))
            return
        err = options.validate_rules()
        if err:
            QMessageBox.warning(self, "옵션 확인", err)
            return

        self._progress.reset()
        self._stack.setCurrentIndex(S_PROGRESS)

        self._worker = AnalysisWorker(options, parsed=self._state.parsed)
        self._worker.progress.connect(self._progress.update_progress)
        self._worker.finished_ok.connect(self._on_analysis_done)
        self._worker.failed.connect(self._on_analysis_failed)
        self._worker.cancelled.connect(self._on_analysis_cancelled)
        self._worker.start()

    def _cancel_analysis(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    def _on_analysis_done(self, result, written_paths) -> None:
        self._state.result = result
        self._state.written_paths = list(written_paths)
        self._result.populate()
        self._stack.setCurrentIndex(S_RESULT)
        self._cleanup_worker()

    def _on_analysis_failed(self, message: str) -> None:
        QMessageBox.critical(self, "분석 실패", message)
        self._stack.setCurrentIndex(S_OPTIONS)
        self._cleanup_worker()

    def _on_analysis_cancelled(self) -> None:
        self._stack.setCurrentIndex(S_OPTIONS)
        self._cleanup_worker()

    def _cleanup_worker(self) -> None:
        if self._worker is not None:
            self._worker.wait(50)
            self._worker = None

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        event.accept()
