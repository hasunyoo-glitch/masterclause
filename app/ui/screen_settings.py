"""Settings: API key (GUI input / test / store / replace / delete) + defaults (plan §5.1 step 0)."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config
from app import state as state_mod
from app.state import AppState
from app.ui.widgets import Card
from core import api_key
from core.models import Jurisdiction, OutputLanguage, Perspective


class _KeyTestWorker(QThread):
    """Runs the network validation off the UI thread."""

    done = Signal(bool, str)

    def __init__(self, key: str):
        super().__init__()
        self._key = key

    def run(self) -> None:
        ok, msg = api_key.validate_key(self._key)
        self.done.emit(ok, msg)


class SettingsScreen(QWidget):
    key_saved = Signal()
    closed = Signal()

    def __init__(self, state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = state
        self._worker: _KeyTestWorker | None = None
        self._pending_save = False
        self._build()
        self.refresh()

    # -- UI ---------------------------------------------------------------- #
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel("설정")
        title.setObjectName("StepTitle")
        root.addWidget(title)

        # --- API key ---
        key_card = Card("Anthropic API 키")
        self._status = QLabel("")
        self._status.setStyleSheet("color:#444;")
        key_card.add(self._status)

        krow = QHBoxLayout()
        self._key_edit = QLineEdit()
        self._key_edit.setEchoMode(QLineEdit.Password)
        self._key_edit.setPlaceholderText("sk-ant-...")
        self._key_edit.textChanged.connect(self._on_key_text_changed)
        self._toggle = QPushButton("보기")
        self._toggle.setCheckable(True)
        self._toggle.toggled.connect(self._on_toggle_visibility)
        paste = QPushButton("붙여넣기")
        paste.clicked.connect(self._on_paste)
        krow.addWidget(self._key_edit, 1)
        krow.addWidget(self._toggle)
        krow.addWidget(paste)
        kw = QWidget()
        kw.setLayout(krow)
        key_card.add(kw)

        brow = QHBoxLayout()
        self._test_btn = QPushButton("연결 테스트")
        self._test_btn.clicked.connect(self._on_test)
        self._save_btn = QPushButton("저장")
        self._save_btn.setObjectName("Primary")
        self._save_btn.clicked.connect(self._on_save)
        self._delete_btn = QPushButton("키 삭제")
        self._delete_btn.clicked.connect(self._on_delete)
        brow.addWidget(self._test_btn)
        brow.addWidget(self._save_btn)
        brow.addStretch(1)
        brow.addWidget(self._delete_btn)
        bw = QWidget()
        bw.setLayout(brow)
        key_card.add(bw)

        self._test_result = QLabel("")
        self._test_result.setWordWrap(True)
        key_card.add(self._test_result)
        root.addWidget(key_card)

        # --- Default options ---
        def_card = Card("기본 옵션")
        self._def_perspective = self._combo(
            [(Perspective.LAWYER.value, "엔터테인먼트 변호사"),
             (Perspective.ARTIST.value, "아티스트"),
             (Perspective.LABEL.value, "음반사")],
            self._state.perspective,
        )
        self._def_language = self._combo(
            [(OutputLanguage.KO.value, "한글"), (OutputLanguage.EN.value, "English")],
            self._state.output_language,
        )
        self._def_jurisdiction = self._combo(
            [(Jurisdiction.KR.value, "대한민국"), (Jurisdiction.US.value, "미국")],
            self._state.jurisdiction,
        )
        self._def_model = self._combo(
            [(config.MODEL_PRIMARY, f"{config.MODEL_PRIMARY} (정밀)"),
             (config.MODEL_LIGHT, f"{config.MODEL_LIGHT} (경량/저비용)")],
            self._state.model or config.MODEL_PRIMARY,
        )
        def_card.add(self._labeled("기본 입장", self._def_perspective))
        def_card.add(self._labeled("기본 출력 언어", self._def_language))
        def_card.add(self._labeled("기본 관할", self._def_jurisdiction))
        def_card.add(self._labeled("분석 모델", self._def_model))
        save_def = QPushButton("기본 옵션 저장")
        save_def.clicked.connect(self._on_save_defaults)
        def_card.add(save_def)
        root.addWidget(def_card)

        root.addStretch(1)

        nav = QHBoxLayout()
        nav.addStretch(1)
        close = QPushButton("닫기")
        close.clicked.connect(self.closed.emit)
        nav.addWidget(close)
        nw = QWidget()
        nw.setLayout(nav)
        root.addWidget(nw)

    @staticmethod
    def _combo(items: list[tuple[str, str]], current: str) -> QComboBox:
        combo = QComboBox()
        for value, label in items:
            combo.addItem(label, value)
        idx = max(0, combo.findData(current))
        combo.setCurrentIndex(idx)
        return combo

    @staticmethod
    def _labeled(label: str, widget: QWidget) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(120)
        lay.addWidget(lbl)
        lay.addWidget(widget, 1)
        return w

    # -- Status / refresh -------------------------------------------------- #
    def refresh(self) -> None:
        key = api_key.load_key()
        if key:
            self._status.setText(f"상태: 설정됨  ·  {api_key.masked(key)}")
        else:
            self._status.setText("상태: 키가 설정되지 않았습니다. 분석 전에 키를 입력하세요.")
        self._test_result.setText("")

    # -- Key field --------------------------------------------------------- #
    def _on_toggle_visibility(self, shown: bool) -> None:
        self._key_edit.setEchoMode(QLineEdit.Normal if shown else QLineEdit.Password)
        self._toggle.setText("숨김" if shown else "보기")

    def _on_paste(self) -> None:
        text = QApplication.clipboard().text().strip()
        if text:
            self._key_edit.setText(text)

    def _on_key_text_changed(self) -> None:
        self._test_result.setText("")

    # -- Test / save / delete --------------------------------------------- #
    def _current_key(self) -> str:
        return self._key_edit.text().strip()

    def _on_test(self) -> None:
        key = self._current_key()
        if not key:
            self._test_result.setText("키를 입력하세요.")
            return
        self._pending_save = False
        self._run_validation(key)

    def _on_save(self) -> None:
        key = self._current_key()
        if not key:
            self._test_result.setText("키를 입력하세요.")
            return
        # Validate, then save on success.
        self._pending_save = True
        self._run_validation(key)

    def _run_validation(self, key: str) -> None:
        self._set_busy(True)
        self._test_result.setText("검증 중…")
        self._worker = _KeyTestWorker(key)
        self._worker.done.connect(self._on_validation_done)
        self._worker.start()

    def _on_validation_done(self, ok: bool, msg: str) -> None:
        self._set_busy(False)
        self._test_result.setText(msg)
        self._test_result.setStyleSheet("color:#1b7a36;" if ok else "color:#b00020;")
        if ok and self._pending_save:
            try:
                api_key.save_key(self._current_key())
                self._key_edit.clear()
                self.refresh()
                self._test_result.setText("저장 완료: 키가 안전하게 보관되었습니다.")
                self.key_saved.emit()
            except api_key.ApiKeyError as exc:
                self._test_result.setText(str(exc))
        self._pending_save = False

    def _set_busy(self, busy: bool) -> None:
        for btn in (self._test_btn, self._save_btn, self._delete_btn):
            btn.setEnabled(not busy)

    def _on_delete(self) -> None:
        confirm = QMessageBox.question(
            self, "키 삭제", "저장된 API 키를 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            api_key.delete_key()
            self.refresh()
            self._test_result.setText("키가 삭제되었습니다.")

    # -- Defaults ---------------------------------------------------------- #
    def _on_save_defaults(self) -> None:
        self._state.perspective = self._def_perspective.currentData()
        self._state.output_language = self._def_language.currentData()
        self._state.jurisdiction = self._def_jurisdiction.currentData()
        self._state.model = self._def_model.currentData()
        settings = state_mod.load_settings()
        settings.update(
            {
                "perspective": self._state.perspective,
                "output_language": self._state.output_language,
                "jurisdiction": self._state.jurisdiction,
                "model": self._state.model,
            }
        )
        state_mod.save_settings(settings)
        QMessageBox.information(self, "저장됨", "기본 옵션이 저장되었습니다.")
