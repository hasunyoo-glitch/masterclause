# One-shot setup: ensure Python 3.11+, create .venv, install dependencies.
# Invoked by install.bat (double-click). Safe to re-run.
# NOTE: messages are kept ASCII/English on purpose - non-ASCII text in batch/
# PowerShell launch scripts is fragile across Windows code pages. The detailed
# Korean guide lives in README.md.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== MasterClause - Music Contract Analyzer : Setup ===" -ForegroundColor Cyan

$PyDownloadPage = "https://www.python.org/downloads/"
$PyInstallerUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"

function Test-PyOK([string]$exe) {
    try {
        & $exe -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Find-Python {
    $cands = New-Object System.Collections.Generic.List[string]
    foreach ($v in @('3.12','3.11','3.13','3')) {
        try {
            $p = & py "-$v" -c "import sys;print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $p) { $cands.Add($p.Trim()) }
        } catch {}
    }
    try {
        $p = & python -c "import sys;print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $p) { $cands.Add($p.Trim()) }
    } catch {}
    $base = "$env:LOCALAPPDATA\Programs\Python"
    if (Test-Path $base) {
        Get-ChildItem $base -Directory -Filter "Python3*" -ErrorAction SilentlyContinue | ForEach-Object {
            $exe = Join-Path $_.FullName "python.exe"
            if (Test-Path $exe) { $cands.Add($exe) }
        }
    }
    foreach ($c in $cands) { if (Test-PyOK $c) { return $c } }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host "Python 3.11+ not found. Installing Python 3.12..." -ForegroundColor Yellow
    $installed = $false
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        try {
            winget install --id Python.Python.3.12 --scope user --silent `
                --accept-source-agreements --accept-package-agreements --disable-interactivity
            if ($LASTEXITCODE -eq 0) { $installed = $true }
        } catch {}
    }
    if (-not $installed) {
        $tmp = Join-Path $env:TEMP "python-3.12.10-amd64.exe"
        Write-Host "Downloading: $PyInstallerUrl"
        Invoke-WebRequest -Uri $PyInstallerUrl -OutFile $tmp
        Write-Host "Installing (user scope)..."
        Start-Process -FilePath $tmp -ArgumentList "/quiet","InstallAllUsers=0","PrependPath=1","Include_launcher=1" -Wait
    }
    $py = Find-Python
    if (-not $py) {
        Write-Error "Could not verify a Python install. Please install it manually, then re-run: $PyDownloadPage"
        exit 1
    }
}

Write-Host "Using Python: $py" -ForegroundColor Green

if (-not (Test-Path "$Root\.venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment (.venv)..."
    & $py -m venv .venv
}
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "Upgrading pip..."
& $venvPy -m pip install --upgrade pip

Write-Host "Installing dependencies (requirements.txt)..."
& $venvPy -m pip install -r requirements.txt

Write-Host ""
Write-Host "=== Done. ===" -ForegroundColor Cyan
Write-Host "Now double-click run.bat to launch the app." -ForegroundColor Cyan
