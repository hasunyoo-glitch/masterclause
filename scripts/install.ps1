# One-shot setup: ensure Python 3.11+, create .venv, install dependencies.
# Invoked by install.bat (double-click). Safe to re-run.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== MasterClause - Music Contract Analyzer : 설치 / Setup ===" -ForegroundColor Cyan

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
    Write-Host "Python 3.11+ 가 없습니다. Python 3.12 를 설치합니다... / Installing Python 3.12..." -ForegroundColor Yellow
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
        Write-Host "다운로드 중 / Downloading: $PyInstallerUrl"
        Invoke-WebRequest -Uri $PyInstallerUrl -OutFile $tmp
        Write-Host "설치 중(사용자 범위) / Installing (user scope)..."
        Start-Process -FilePath $tmp -ArgumentList "/quiet","InstallAllUsers=0","PrependPath=1","Include_launcher=1" -Wait
    }
    $py = Find-Python
    if (-not $py) {
        Write-Error "Python 설치를 확인하지 못했습니다. 수동 설치 후 다시 실행하세요: $PyDownloadPage"
        exit 1
    }
}

Write-Host "사용 Python / Using Python: $py" -ForegroundColor Green

if (-not (Test-Path "$Root\.venv\Scripts\python.exe")) {
    Write-Host "가상환경 생성 / Creating virtual environment (.venv)..."
    & $py -m venv .venv
}
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "pip 업그레이드 / Upgrading pip..."
& $venvPy -m pip install --upgrade pip

Write-Host "의존성 설치 / Installing dependencies (requirements.txt)..."
& $venvPy -m pip install -r requirements.txt

Write-Host ""
Write-Host "=== 설치 완료! / Done. ===" -ForegroundColor Cyan
Write-Host "이제 run.bat 을 더블클릭해 실행하세요. / Now double-click run.bat to launch." -ForegroundColor Cyan
