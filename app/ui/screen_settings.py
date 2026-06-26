"""Settings: API key (input / test / store / delete), defaults, UI language (plan §5.1 step 0)."""
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
from app import i18n
from app import state as state_mod
from app.i18n import tr
from app.state import AppState
from core import api_key
from core.models import Jurisdiction, OutputLanguage, Perspective


class _KeyTestWorker(QThread):
    """Runs the network validation off the UI thread."""

    done = Signal(bool, str)

    def __init__(self, key: str):
        super().__init__()
        self._key = key

    def run(self) -> None:
        ok, msg_key = api_key.validate_key(self._key)
        self.done.emit(ok, msg_key)


class SettingsScreen(QWidget):
    key_saved = Signal()
    closed = Signal()
    ui_language_changed = Signal(str)

    def __init__(self, state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = state
        self._worker: _KeyTestWorker | None = None
        self._pending_save = False
        self._ready = False
        self._build()
        self.refresh()
        self._ready = True

    # -- UI ---------------------------------------------------------------- #
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel(tr("settings.title"))
        title.setObjectName("StepTitle")
        root.addWidget(title)

        # --- API key ---
        from app.ui.widgets import Card  # local import avoids a cycle at module load

        key_card = Card(tr("settings.key_card"))
        self._status = QLabel("")
        self._status.setStyleSheet("color:#444;")
        key_card.add(self._status)

        krow = QHBoxLayout()
        self._key_edit = QLineEdit()
        self._key_edit.setEchoMode(QLineEdit.Password)
        self._key_edit.setPlaceholderText("sk-ant-...")
        self._key_edit.textChanged.connect(self._on_key_text_changed)
        self._toggle = QPushButton(tr("settings.show"))
        self._toggle.setCheckable(True)
        self._toggle.toggled.connect(self._on_toggle_visibility)
        paste = QPushButton(tr("settings.paste"))
        paste.clicked.connect(self._on_paste)
        krow.addWidget(self._key_edit, 1)
        krow.addWidget(self._toggle)
        krow.addWidget(paste)
        kw = QWidget()
        kw.setLayout(krow)
        key_card.add(kw)

        brow = QHBoxLayout()
        self._test_btn = QPushButton(tr("settings.test"))
        self._test_btn.clicked.connect(self._on_test)
        self._save_btn = QPushButton(tr("settings.save"))
        self._save_btn.setObjectName("Primary")
        self._save_btn.clicked.connect(self._on_save)
        self._delete_btn = QPushButton(tr("settings.delete"))
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

        # --- Default options + UI language ---
        def_card = Card(tr("settings.defaults"))
        self._ui_lang = self._combo(
            [("ko", tr("options.lang.ko")), ("en", tr("options.lang.en"))],
            i18n.get_language(),
        )
        self._ui_lang.currentIndexChanged.connect(self._on_ui_lang_changed)
        self._def_perspective = self._combo(
            [(Perspective.LAWYER.value, tr("options.persp.lawyer")),
             (Perspective.ARTIST.value, tr("options.persp.artist")),
             (Perspective.LABEL.value, tr("options.persp.label"))],
            self._state.perspective,
        )
        self._def_language = self._combo(
            [(OutputLanguage.KO.value, tr("options.lang.ko")),
             (OutputLanguage.EN.value, tr("options.lang.en"))],
            self._state.output_language,
        )
        self._def_jurisdiction = self._combo(
            [(Jurisdiction.KR.value, tr("options.jur.kr")),
             (Jurisdiction.US.value, tr("options.jur.us"))],
            self._state.jurisdiction,
        )
        self._def_model = self._combo(
            [(config.MODEL_PRIMARY, tr("settings.model_primary", m=config.MODEL_PRIMARY)),
             (config.MODEL_LIGHT, tr("settings.model_light", m=config.MODEL_LIGHT))],
            self._state.model or config.MODEL_PRIMARY,
        )
        def_card.add(self._labeled(tr("settings.ui_lang"), self._ui_lang))
        def_card.add(self._labeled(tr("settings.def_persp"), self._def_perspective))
        def_card.add(self._labeled(tr("settings.def_lang"), self._def_language))
        def_card.add(self._labeled(tr("settings.def_jur"), self._def_jurisdiction))
        def_card.add(self._labeled(tr("settings.def_model"), self._def_model))
        save_def = QPushButton(tr("settings.save_defaults"))
        save_def.clicked.connect(self._on_save_defaults)
        def_card.add(save_def)
        root.addWidget(def_card)

        root.addStretch(1)

        nav = QHBoxLayout()
        nav.addStretch(1)
        close = QPushButton(tr("common.close"))
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
            self._status.setText(tr("settings.status_set", masked=api_key.masked(key)))
        else:
            self._status.setText(tr("settings.status_unset"))
        self._test_result.setText("")

    # -- UI language ------------------------------------------------------- #
    def _on_ui_lang_changed(self) -> None:
        if not self._ready:
            return
        lang = self._ui_lang.currentData()
        if lang and lang != i18n.get_language():
            self.ui_language_changed.emit(lang)

    # -- Key field --------------------------------------------------------- #
    def _on_toggle_visibility(self, shown: bool) -> None:
        self._key_edit.setEchoMode(QLineEdit.Normal if shown else QLineEdit.Password)
        self._toggle.setText(tr("settings.hide") if shown else tr("settings.show"))

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
        if not self._current_key():
            self._test_result.setText(tr("settings.enter_key"))
            return
        self._pending_save = False
        self._run_validation(self._current_key())

    def _on_save(self) -> None:
        if not self._current_key():
            self._test_result.setText(tr("settings.enter_key"))
            return
        self._pending_save = True
        self._run_validation(self._current_key())

    def _run_validation(self, key: str) -> None:
        self._set_busy(True)
        self._test_result.setText(tr("settings.validating"))
        self._worker = _KeyTestWorker(key)
        self._worker.done.connect(self._on_validation_done)
        self._worker.start()

    def _on_validation_done(self, ok: bool, msg_key: str) -> None:
        self._set_busy(False)
        self._test_result.setText(_translate_apikey(msg_key))
        self._test_result.setStyleSheet("color:#1b7a36;" if ok else "color:#b00020;")
        if ok and self._pending_save:
            try:
                api_key.save_key(self._current_key())
                self._key_edit.clear()
                self.refresh()
                self._test_result.setText(tr("settings.saved"))
                self.key_saved.emit()
            except api_key.ApiKeyError as exc:
                self._test_result.setText(str(exc))
        self._pending_save = False

    def _set_busy(self, busy: bool) -> None:
        for btn in (self._test_btn, self._save_btn, self._delete_btn):
            btn.setEnabled(not busy)

    def _on_delete(self) -> None:
        confirm = QMessageBox.question(
            self, tr("settings.delete_q_title"), tr("settings.delete_q_body"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            api_key.delete_key()
            self.refresh()
            self._test_result.setText(tr("settings.deleted"))

    # -- Defaults ---------------------------------------------------------- #
    def _on_save_defaults(self) -> None:
        self._state.perspective = self._def_perspective.currentData()
        self._state.output_language = self._def_language.currentData()
        self._state.jurisdiction = self._def_jurisdiction.currentData()
        self._state.model = self._def_model.currentData()
        settings = state_mod.load_settings()
        settings.update(
            {
                "ui_language": i18n.get_language(),
                "perspective": self._state.perspective,
                "output_language": self._state.output_language,
                "jurisdiction": self._state.jurisdiction,
                "model": self._state.model,
            }
        )
        state_mod.save_settings(settings)
        QMessageBox.information(
            self, tr("settings.saved_defaults_title"), tr("settings.saved_defaults_body")
        )


def _translate_apikey(msg_key: str) -> str:
    """Localize an api_key validation key, including the 'apikey.fail|detail' form."""
    if msg_key.startswith("apikey.fail|"):
        return tr("apikey.fail", detail=msg_key.split("|", 1)[1])
    return tr(msg_key)
