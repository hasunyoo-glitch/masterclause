# Build & Packaging

## 1. Freeze the app with PyInstaller (onedir — recommended)

```powershell
.\.venv\Scripts\activate
pip install pyinstaller
pyinstaller build/main.spec --noconfirm
```

Output: `dist/MasterClause/MasterClause.exe`

Run it on a **clean Windows machine** to verify native deps (PyMuPDF, PySide6,
keyring backends, anthropic) are bundled. If a module is missing at runtime, add
it to `hiddenimports` in `build/main.spec`.

## 2. Build the installer with Inno Setup

Install Inno Setup (https://jrsoftware.org/isinfo.php), then:

```powershell
iscc build/installer.iss
```

Output: `build/Output/AIMusicContractAnalyzer-Setup.exe`

## 3. (Optional) Code signing

Sign `AIMusicContractAnalyzer.exe` and the installer with a code-signing
certificate to reduce SmartScreen warnings:

```powershell
signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com /td SHA256 `
  dist\MasterClause\MasterClause.exe
```

## macOS build (.app)

The app is cross-platform Python, so it also runs and packages on macOS. Build
a native `.app` from the same `run.py` (the Windows `main.spec` is Windows-only —
use a plain PyInstaller invocation on macOS):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pyinstaller
pyinstaller --windowed --name "MasterClause" \
  --add-data "data:data" --add-data "config.py:." run.py
```

Output: `dist/MasterClause.app`. (Sign/notarize with `codesign`/`notarytool`
for distribution.)

## Notes

- The bundled `data/` (jurisdiction + benchmark JSON) is included via the spec's
  `datas`. `config.py` resolves it from `sys._MEIPASS` when frozen.
- The API key is **not** bundled — it is entered in-app and stored in the Windows
  Credential Manager via `keyring`.
- User data (config.json, optional history DB) lives under
  `%APPDATA%/ai-contract-analyzer/`.
