"""Root launcher (used by `python run.py` and the PyInstaller build).

Keeps the project root on sys.path so `import config` and `from app...` resolve
both in development and inside the frozen bundle.
"""
import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
