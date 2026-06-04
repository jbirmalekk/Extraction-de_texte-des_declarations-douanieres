# Lance l'API facture (port 8001) avec le venv local
$Root = $PSScriptRoot
Set-Location $Root

if (-not (Test-Path "$Root\.venv\Scripts\Activate.ps1")) {
    Write-Host "Creation du venv..."
    python -m venv .venv
    & "$Root\.venv\Scripts\pip.exe" install -r requirements.txt
}

& "$Root\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8001
