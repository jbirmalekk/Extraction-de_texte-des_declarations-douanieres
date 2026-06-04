# back_EMP_Fact — API factures (port 8001)

## Environnement Python

```powershell
cd back_EMP_Fact
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copier `.env.example` vers `.env` et aligner **`DB_*`** sur `back_EMP/.env` (même base `OCR_Extraction_DB`).

```env
DB_SERVER=LAPTOP-IPKVL4CG\SQLEXPRESS
DB_NAME=OCR_Extraction_DB
DB_DRIVER=ODBC Driver 18 for SQL Server
DB_TRUSTED_CONNECTION=yes
```

Installer le driver : `pip install pyodbc requests`

Tables créées au démarrage : `invoices`, `invoice_lines`, `invoice_upload_traces`  
Liaison 1–1 : `invoices.dum_document_id` → `documents.id`

### Nextcloud GED (comme la DUM)

Copier les variables `NEXTCLOUD_*` depuis `back_EMP/.env`. Les factures vont dans  
`EMP-SmartOCR/factures/{utilisateur}/{date}/`.

Headers upload (front) : `X-Uploaded-By-User-Id`, `X-Uploaded-By-Username`, `X-Client-PC-Name`

### API liaison / comparaison

- `POST /api/invoices/{id}/link-dum` — body `{ "dum_document_id": 42 }`
- `POST /api/invoices/{id}/compare-dum` — body optionnel ; si `dum_document_id` ou liaison existante, PFN lu depuis `documents`

## Lancer l’API

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8001
```

## OCR avancé (optionnel, comme la DUM)

Sans Paddle, les PDF scannés utilisent Tesseract seul en secours.

```powershell
pip install -r requirements-ocr.txt
```

Puis redémarrer uvicorn. Variables dans `.env` : `OCR_ENGINE_PRIMARY`, `TESSERACT_PATH`, etc.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```
