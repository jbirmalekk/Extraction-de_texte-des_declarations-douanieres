# Serveur S2 — migration ERP (port 8002)
$env:PYTHONUNBUFFERED = "1"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
