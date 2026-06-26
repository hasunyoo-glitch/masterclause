# PyInstaller spec — onedir build (recommended for stability; plan §9).
# Build from the project root:
#     pip install pyinstaller
#     pyinstaller build/main.spec --noconfirm
# Output: dist/MasterClause/

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden = []
# keyring backends are discovered dynamically — pull them in explicitly.
hidden += collect_submodules("keyring.backends")
hidden += collect_submodules("anthropic")

a = Analysis(
    ["..\\run.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("..\\data", "data"),     # bundled jurisdiction + benchmark JSON
        ("..\\config.py", "."),   # config module at root for frozen path logic
    ],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MasterClause",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # GUI app — no console window
    disable_windowed_traceback=False,
    icon=None,               # add an .ico path here when available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="MasterClause",
)
