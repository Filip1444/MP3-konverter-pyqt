$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    py -3 -m venv (Join-Path $projectRoot "venv")
}

& $python -m pip install -r (Join-Path $projectRoot "requirements.txt") -r (Join-Path $PSScriptRoot "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name Mp3Konverter --collect-all imageio_ffmpeg --paths (Join-Path $projectRoot "src") --distpath (Join-Path $projectRoot "dist") --workpath (Join-Path $projectRoot "build") --specpath $PSScriptRoot (Join-Path $projectRoot "src\app.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }