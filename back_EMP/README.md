# Backend EMP SmartOCR

API FastAPI pour l'authentification, l'extraction OCR, la validation humaine et le reporting (dashboard/historique).

## Demarrage rapide

### 1) Activer l'environnement virtuel

```powershell
.\venv\Scripts\Activate.ps1
```

### 2) Installer les dependances

```powershell
pip install -r requirements.txt
```

### 3) Configurer les variables d'environnement

Le fichier `.env` doit contenir au minimum:

- `DB_SERVER`, `DB_NAME`, `DB_DRIVER`, `DB_TRUSTED_CONNECTION` (ou `DB_USER`/`DB_PASSWORD`)
- `SECRET_KEY` (obligatoire, >= 32 caracteres)
- `FRONTEND_URL`
- `TESSERACT_PATH` et `POPPLER_PATH` selon votre environnement

Exemple de generation d'une cle:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4) Lancer l'API

```powershell
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Configuration Nextcloud GED (optionnelle)

Variables backend:

- `NEXTCLOUD_ENABLED=true|false`
- `NEXTCLOUD_BASE_URL`
- `NEXTCLOUD_USERNAME`
- `NEXTCLOUD_PASSWORD`
- `NEXTCLOUD_UPLOAD_ROOT=EMP-SmartOCR`
- `NEXTCLOUD_TIMEOUT_SECONDS=20`
- `NEXTCLOUD_VERIFY_SSL=true|false`
- `NEXTCLOUD_REQUIRED=true|false`

Comportement:

- si `NEXTCLOUD_REQUIRED=false`: fallback SQL si upload GED en echec
- si `NEXTCLOUD_REQUIRED=true`: erreur HTTP 502 si GED indisponible

Le nom du poste client peut etre transmis avec le header `X-Client-PC-Name`.

## Endpoints principaux

### Sante

- `GET /health` : etat API + connectivite DB

### Authentification (`/auth`)

- `POST /auth/signup`
  - payload JSON: `username`, `email`, `password`
  - cree un compte non approuve et non verifie email
- `POST /auth/login`
  - payload JSON: `email`, `password`
  - retourne `access_token` si email verifie + compte approuve + actif
- `POST /auth/logout`
  - invalide le token courant (blacklist en memoire)
- `GET /auth/me`
  - retourne le profil de l'utilisateur connecte
- `POST /auth/verify-email`
  - confirme l'email via token
- `POST /auth/forgot-password`
  - declenche l'envoi email reset (reponse generique, sans divulgation de token)
- `POST /auth/reset-password`
  - applique un nouveau mot de passe avec token reset
- `PUT /auth/me`
  - mise a jour profil courant
- `PUT /auth/me/password`
  - changement de mot de passe courant

Administration (role admin):

- `GET /auth/users`
- `GET /auth/users/{user_id}`
- `PUT /auth/users/{user_id}`
- `DELETE /auth/users/{user_id}`
- `GET /auth/pending-users`
- `POST /auth/approve-user/{user_id}`
- `POST /auth/reject-user/{user_id}`

### OCR et documents (`/api`)

- `POST /api/ocr`
  - upload `multipart/form-data` (`file`)
  - query params: `fast_mode`, `use_deskew`
  - persiste `Document`, `OCRResult`, `ExtractedField`, `Taxe`, `Article`, `DocumentUploadTrace`
- `PUT /api/ocr/{document_id}/valider`
  - enregistre une session de validation et l'historique des corrections
- `GET /api/ocr/{document_id}/corrections/latest`
  - retourne la derniere correction par champ
- `GET /api/documents`
  - admin: tous les documents
  - user: uniquement ses documents
- `GET /api/documents/{document_id}`
  - detail document avec controle d'acces

### Dashboard (`/api/dashboard`)

- `GET /api/dashboard/me`
- `GET /api/dashboard/me/history`
- `GET /api/dashboard/admin` (admin)
- `GET /api/dashboard/history` (admin)

## Exemple rapide avec curl

### Signup

```powershell
curl -X POST "http://localhost:8000/auth/signup" `
  -H "Content-Type: application/json" `
  -d '{"username":"alice","email":"alice@test.com","password":"StrongP@ssw0rd"}'
```

### Login (JSON email/password)

```powershell
curl -X POST "http://localhost:8000/auth/login" `
  -H "Content-Type: application/json" `
  -d '{"email":"alice@test.com","password":"StrongP@ssw0rd"}'
```

### Upload OCR (remplacer TOKEN et chemin fichier)

```powershell
curl -X POST "http://localhost:8000/api/ocr?fast_mode=false&use_deskew=true" `
  -H "Authorization: Bearer TOKEN" `
  -H "X-Client-PC-Name: Poste-Import-01" `
  -F "file=@C:/tmp/document.pdf"
```

## Structure backend (vue simplifiee)

```text
back_EMP/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py
│   ├── database.py              # couche compatibilite d'import
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── ocr.py
│   │   └── dashboard.py
│   ├── services/
│   └── utils/
├── requirements.txt
└── README.md
```

## Notes securite

- Mots de passe hashes via bcrypt.
- JWT signes avec `SECRET_KEY` obligatoire.
- Blacklist logout en memoire (prevoyez Redis/DB en production).
- Ne jamais versionner de secrets dans Git (`.env`, mots de passe compose, tokens).
