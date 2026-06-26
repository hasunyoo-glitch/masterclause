"""Application entry point.

Run with:  python -m app.main
"""
from __future__ import annotations

import os
import sys

# Force UTF-8 on Windows consoles (plan §8).
os.environ.setdefault("PYTHONUTF8", "1")

from PySide6.QtWidgets import QApplication  # noqa: E402

import config  # noqa: E402

STYLESHEET = """
QWidget { font-family: 'Segoe UI', 'Malgun Gothic', '-apple-system', 'Apple SD Gothic Neo', 'Noto Sans CJK KR', sans-serif; font-size: 13px; color: #1f2328; }
QMainWindow, QStackedWidget { background: #ffffff; }
#Header { background: #1f2328; }
#AppTitle { color: #ffffff; font-size: 15px; font-weight: 600; }
#Header QPushButton { color: #ffffff; background: transparent; border: 1px solid #555; border-radius: 4px; padding: 4px 12px; }
#Header QPushButton:hover { background: #333; }
#StepTitle { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
#Card { background: #ffffff; border: 1px solid #e3e6ea; border-radius: 8px; }
#CardTitle { font-weight: 700; font-size: 14px; color: #1f2328; }
QPushButton { background: #f1f3f5; border: 1px solid #ccd0d5; border-radius: 6px; padding: 7px 14px; }
QPushButton:hover { background: #e7eaee; }
QPushButton:disabled { color: #aab; background: #f6f7f8; }
QPushButton#Primary { background: #1f6feb; color: #ffffff; border: 1px solid #1a5fd0; font-weight: 600; }
QPushButton#Primary:hover { background: #1a5fd0; }
QPushButton#Primary:disabled { background: #9db8e8; border-color: #9db8e8; }
QLineEdit, QComboBox, QPlainTextEdit { border: 1px solid #ccd0d5; border-radius: 6px; padding: 6px 8px; background: #fff; }
QProgressBar { border: 1px solid #ccd0d5; border-radius: 6px; height: 22px; text-align: center; }
QProgressBar::chunk { background: #1f6feb; border-radius: 5px; }
QRadioButton, QCheckBox { padding: 3px 0; }
QScrollArea { border: none; }
"""


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setStyleSheet(STYLESHEET)

    # Import here so a missing core dep surfaces as a dialog, not an import crash.
    from app.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
