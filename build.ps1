$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    py -3 -m venv (Join-Path $PSScriptRoot "venv")
}

& $python -m pip install -r (Join-Path $PSScriptRoot "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name Mp3Konverter --collect-all imageio_ffmpeg (Join-Path $PSScriptRoot "app.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }