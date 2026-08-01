# Launch React Terminal Dark UI (npm ensure + lake API + Vite).
# Usage (from repo root): .\scripts\dev_ui.ps1 [--port 5173] [--api-port 8765] [--skip-install] [--no-api]
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Missing $Python — create a venv and run: .\.venv\Scripts\python.exe -m pip install -e `".[dev]`""
}
& $Python -m decifra ui @args
exit $LASTEXITCODE
