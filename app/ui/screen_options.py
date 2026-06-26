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
from app.state import AppState
from app.ui.widgets import Card
from core.models import Jurisdiction, OutputLanguage, Perspective, USState

_PERSPECTIVES = [
    (Perspective.LAWYER.value, "엔터테인먼트 변호사", "의뢰인 자문 관점에서 집행가능성·법적 근거를 정밀하게 평가합니다."),
    (Perspective.ARTIST.value, "아티스트", "당신의 권리·수익·통제권 보호 관점에서 위험을 평가합니다."),
    (Perspective.LABEL.value, "음반사 / 레이블", "레이블의 리스크 노출·방어가능성·표준 대비 합리성을 평가합니다."),
]

_US_STATES = [
    (USState.CA.value, "California (CA)"),
    (USState.NY.value, "New York (NY)"),
    (USState.TN.value, "Tennessee (TN)"),
    (USState.DC.value, "Washington D.C. (DC)"),
    (USState.OTHER.value, "그 외 (직접 입력)"),
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

        title = QLabel("2단계 · 분석 옵션 확정")
        title.setObjectName("StepTitle")
        root.addWidget(title)

        # --- Perspective ---
        p_card = Card("입장 (Perspective)")
        self._p_group = QButtonGroup(self)
        for value, label, desc in _PERSPECTIVES:
            rb = QRadioButton(label)
            rb.setProperty("value", value)
            if value == self._state.perspective:
                rb.setChecked(True)
            self._p_group.addButton(rb)
            p_card.add(rb)
            d = QLabel(desc)
            d.setStyleSheet("color:#666; margin-left:22px; margin-bottom:4px;")
            d.setWordWrap(True)
            p_card.add(d)
        root.addWidget(p_card)

        # --- Language ---
        l_card = Card("출력 언어 (Output Language)")
        lrow = QHBoxLayout()
        self._l_group = QButtonGroup(self)
        for value, label in [(OutputLanguage.KO.value, "한글"), (OutputLanguage.EN.value, "English")]:
            rb = QRadioButton(label)
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
        j_card = Card("관할 (Jurisdiction)")
        jrow = QHBoxLayout()
        self._j_group = QButtonGroup(self)
        for value, label in [(Jurisdiction.KR.value, "대한민국"), (Jurisdiction.US.value, "미국")]:
            rb = QRadioButton(label)
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
        srow.addWidget(QLabel("주(State):"))
        self._state_combo = QComboBox()
        for value, label in _US_STATES:
            self._state_combo.addItem(label, value)
        self._state_combo.currentIndexChanged.connect(self._on_state_changed)
        srow.addWidget(self._state_combo, 1)
        self._state_other = QLineEdit()
        self._state_other.setPlaceholderText("주 이름 직접 입력")
        self._state_other.setVisible(False)
        srow.addWidget(self._state_other, 1)
        sw = QWidget()
        sw.setLayout(srow)
        j_card.add(sw)
        root.addWidget(j_card)

        # --- Privacy ---
        pr_card = Card("프라이버시 (선택)")
        self._anon = QCheckBox("전송 전 익명화 (이름·식별정보 마스킹)")
        self._anon.setChecked(self._state.anonymize_before_analysis)
        self._zero = QCheckBox("zero-retention (이력 DB에 저장하지 않음)")
        self._zero.setChecked(self._state.zero_retention)
        pr_card.add(self._anon)
        pr_card.add(self._zero)
        root.addWidget(pr_card)

        # --- Concern ---
        c_card = Card("가장 큰 우려 (선택)")
        hint = QLabel("이 계약에서 가장 걱정되는 점을 적어주세요. 비워두면 일반 분석만 수행합니다.")
        hint.setStyleSheet("color:#666;")
        hint.setWordWrap(True)
        c_card.add(hint)
        self._concern = QPlainTextEdit()
        self._concern.setPlaceholderText("예) 제 목소리가 AI 학습에 무기한 사용되는 것이 걱정됩니다.")
        self._concern.setFixedHeight(80)
        self._concern.textChanged.connect(self._on_concern_changed)
        c_card.add(self._concern)
        self._counter = QLabel(f"0/{config.USER_CONCERN_MAX_LEN}")
        self._counter.setAlignment(Qt.AlignRight)
        self._counter.setStyleSheet("color:#888;")
        c_card.add(self._counter)
        root.addWidget(c_card)

        # --- Output format ---
        f_card = Card("출력 형식")
        frow = QHBoxLayout()
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItem("DOCX (기본)", "docx")
        self._fmt_combo.addItem("PDF (Word 필요)", "pdf")
        self._fmt_combo.addItem("DOCX + PDF", "both")
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
        back = QPushButton("← 뒤로")
        back.clicked.connect(self.back_requested.emit)
        nav.addWidget(back)
        nav.addStretch(1)
        self._warn = QLabel("")
        self._warn.setStyleSheet("color:#b00020;")
        nav.addWidget(self._warn)
        self._start = QPushButton("분석 시작")
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
                msg = "주 이름을 입력하세요."
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
