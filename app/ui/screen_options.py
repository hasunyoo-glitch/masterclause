"""Step 2: perspective / language / jurisdiction (+state) / concern (plan §5.1 step 2)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

import config
from app.i18n import tr
from app.state import AppState
from app.ui.widgets import Card
from core.models import Jurisdiction, OutputLanguage, Perspective, USState

# (value, label_key, desc_key) — resolved through tr() at build time.
_PERSPECTIVES = [
    (Perspective.LAWYER.value, "options.persp.lawyer", "options.persp.lawyer_desc"),
    (Perspective.ARTIST.value, "options.persp.artist", "options.persp.artist_desc"),
    (Perspective.LABEL.value, "options.persp.label", "options.persp.label_desc"),
]

_US_STATES = [
    (USState.CA.value, "options.state.ca"),
    (USState.NY.value, "options.state.ny"),
    (USState.TN.value, "options.state.tn"),
    (USState.DC.value, "options.state.dc"),
    (USState.OTHER.value, "options.state.other"),
]


class OptionsScreen(QWidget):
    start_requested = Signal()
    back_requested = Signal()

    def __init__(self, state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = state
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel(tr("options.title"))
        title.setObjectName("StepTitle")
        root.addWidget(title)

        # --- Perspective ---
        p_card = Card(tr("options.perspective"))
        self._p_group = QButtonGroup(self)
        for value, label_key, desc_key in _PERSPECTIVES:
            rb = QRadioButton(tr(label_key))
            rb.setProperty("value", value)
            if value == self._state.perspective:
                rb.setChecked(True)
            self._p_group.addButton(rb)
            p_card.add(rb)
            d = QLabel(tr(desc_key))
            d.setStyleSheet("color:#666; margin-left:22px; margin-bottom:4px;")
            d.setWordWrap(True)
            p_card.add(d)
        root.addWidget(p_card)

        # --- Language ---
        l_card = Card(tr("options.language"))
        lrow = QHBoxLayout()
        self._l_group = QButtonGroup(self)
        for value, label_key in [(OutputLanguage.KO.value, "options.lang.ko"),
                                 (OutputLanguage.EN.value, "options.lang.en")]:
            rb = QRadioButton(tr(label_key))
            rb.setProperty("value", value)
            if value == self._state.output_language:
                rb.setChecked(True)
            self._l_group.addButton(rb)
            lrow.addWidget(rb)
        lrow.addStretch(1)
        lw = QWidget()
        lw.setLayout(lrow)
        l_card.add(lw)
        root.addWidget(l_card)

        # --- Jurisdiction + state ---
        j_card = Card(tr("options.jurisdiction"))
        jrow = QHBoxLayout()
        self._j_group = QButtonGroup(self)
        for value, label_key in [(Jurisdiction.KR.value, "options.jur.kr"),
                                 (Jurisdiction.US.value, "options.jur.us")]:
            rb = QRadioButton(tr(label_key))
            rb.setProperty("value", value)
            if value == self._state.jurisdiction:
                rb.setChecked(True)
            self._j_group.addButton(rb)
            rb.toggled.connect(self._on_jurisdiction_changed)
            jrow.addWidget(rb)
        jrow.addStretch(1)
        jw = QWidget()
        jw.setLayout(jrow)
        j_card.add(jw)

        srow = QHBoxLayout()
        srow.addWidget(QLabel(tr("options.state")))
        self._state_combo = QComboBox()
        for value, label_key in _US_STATES:
            self._state_combo.addItem(tr(label_key), value)
        self._state_combo.currentIndexChanged.connect(self._on_state_changed)
        srow.addWidget(self._state_combo, 1)
        self._state_other = QLineEdit()
        self._state_other.setPlaceholderText(tr("options.state_other_ph"))
        self._state_other.setVisible(False)
        srow.addWidget(self._state_other, 1)
        sw = QWidget()
        sw.setLayout(srow)
        j_card.add(sw)
        root.addWidget(j_card)

        # --- Privacy ---
        pr_card = Card(tr("options.privacy"))
        self._anon = QCheckBox(tr("options.anon"))
        self._anon.setChecked(self._state.anonymize_before_analysis)
        self._zero = QCheckBox(tr("options.zero"))
        self._zero.setChecked(self._state.zero_retention)
        pr_card.add(self._anon)
        pr_card.add(self._zero)
        root.addWidget(pr_card)

        # --- Concern ---
        c_card = Card(tr("options.concern"))
        hint = QLabel(tr("options.concern_hint"))
        hint.setStyleSheet("color:#666;")
        hint.setWordWrap(True)
        c_card.add(hint)
        self._concern = QPlainTextEdit()
        self._concern.setPlaceholderText(tr("options.concern_ph"))
        self._concern.setFixedHeight(80)
        self._concern.textChanged.connect(self._on_concern_changed)
        c_card.add(self._concern)
        self._counter = QLabel(f"0/{config.USER_CONCERN_MAX_LEN}")
        self._counter.setAlignment(Qt.AlignRight)
        self._counter.setStyleSheet("color:#888;")
        c_card.add(self._counter)
        root.addWidget(c_card)

        # --- Output format ---
        f_card = Card(tr("options.format"))
        frow = QHBoxLayout()
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItem(tr("options.fmt.docx"), "docx")
        self._fmt_combo.addItem(tr("options.fmt.pdf"), "pdf")
        self._fmt_combo.addItem(tr("options.fmt.both"), "both")
        idx = max(0, self._fmt_combo.findData(self._state.output_format))
        self._fmt_combo.setCurrentIndex(idx)
        frow.addWidget(self._fmt_combo)
        frow.addStretch(1)
        fw = QWidget()
        fw.setLayout(frow)
        f_card.add(fw)
        root.addWidget(f_card)

        root.addStretch(1)

        # --- Nav ---
        nav = QHBoxLayout()
        back = QPushButton(tr("common.back"))
        back.clicked.connect(self.back_requested.emit)
        nav.addWidget(back)
        nav.addStretch(1)
        self._warn = QLabel("")
        self._warn.setStyleSheet("color:#b00020;")
        nav.addWidget(self._warn)
        self._start = QPushButton(tr("options.start"))
        self._start.setObjectName("Primary")
        self._start.clicked.connect(self._on_start)
        nav.addWidget(self._start)
        nw = QWidget()
        nw.setLayout(nav)
        root.addWidget(nw)

        self._sync_state_visibility()
        self._validate()

    # -- Reactions --------------------------------------------------------- #
    def _on_jurisdiction_changed(self) -> None:
        self._sync_state_visibility()
        self._validate()

    def _on_state_changed(self) -> None:
        is_other = self._state_combo.currentData() == USState.OTHER.value
        self._state_other.setVisible(is_other and self._is_us())
        self._validate()

    def _sync_state_visibility(self) -> None:
        is_us = self._is_us()
        self._state_combo.setEnabled(is_us)
        self._state_other.setVisible(
            is_us and self._state_combo.currentData() == USState.OTHER.value
        )

    def _on_concern_changed(self) -> None:
        text = self._concern.toPlainText()
        if len(text) > config.USER_CONCERN_MAX_LEN:
            text = text[: config.USER_CONCERN_MAX_LEN]
            self._concern.blockSignals(True)
            self._concern.setPlainText(text)
            cursor = self._concern.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self._concern.setTextCursor(cursor)
            self._concern.blockSignals(False)
        self._counter.setText(f"{len(text)}/{config.USER_CONCERN_MAX_LEN}")

    # -- Helpers ----------------------------------------------------------- #
    def _is_us(self) -> bool:
        btn = self._j_group.checkedButton()
        return bool(btn and btn.property("value") == Jurisdiction.US.value)

    def _validate(self) -> bool:
        ok = True
        msg = ""
        if self._is_us():
            data = self._state_combo.currentData()
            if not data:
                ok = False
            elif data == USState.OTHER.value and not self._state_other.text().strip():
                ok = False
                msg = tr("options.need_state")
        self._warn.setText(msg)
        self._start.setEnabled(ok)
        return ok

    # -- Start ------------------------------------------------------------- #
    def _collect(self) -> None:
        self._state.perspective = self._p_group.checkedButton().property("value")
        self._state.output_language = self._l_group.checkedButton().property("value")
        self._state.jurisdiction = self._j_group.checkedButton().property("value")
        if self._is_us():
            self._state.us_state = self._state_combo.currentData()
            self._state.us_state_other = (
                self._state_other.text().strip()
                if self._state_combo.currentData() == USState.OTHER.value
                else None
            )
        else:
            self._state.us_state = None
            self._state.us_state_other = None
        self._state.anonymize_before_analysis = self._anon.isChecked()
        self._state.zero_retention = self._zero.isChecked()
        self._state.output_format = self._fmt_combo.currentData()
        concern = self._concern.toPlainText().strip()
        self._state.user_concern = concern or None

    def _on_start(self) -> None:
        if not self._validate():
            return
        self._collect()
        self.start_requested.emit()
