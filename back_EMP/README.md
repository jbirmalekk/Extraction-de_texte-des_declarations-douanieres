# Backend OCR Extraction API

API FastAPI pour l'extraction automatique de données depuis des documents (PDF, scannés).

## 🚀 Démarrage rapide

### 1. Activer l'environnement virtuel

```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Installer les dépendances (si pas déjà fait)

```powershell
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement

Vérifiez que le fichier `.env` contient bien :
- DB_SERVER, DB_NAME (SQL Server)
- SECRET_KEY (généré avec `python -c "import secrets; print(secrets.token_hex(32))"`)
- TESSERACT_PATH, POPPLER_PATH

### 4. Lancer l'API

```powershell
uvicorn app.main:app --reload
```

L'API sera accessible sur : `http://localhost:8000`

Documentation interactive : `http://localhost:8000/docs`

## 📋 Endpoints d'authentification

### 1. Sign-up (Créer un compte)

**POST** `/auth/signup`

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "monMotDePasse123"
}
```

**Réponse** (201 Created) :
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "is_active": true,
  "created_at": "2026-02-15T10:30:00"
}
```

### 2. Login (Obtenir un token)

**POST** `/auth/login`

Form data :
- `username`: alice
- `password`: monMotDePasse123

**Réponse** (200 OK) :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Get user info (endpoint protégé)

**GET** `/auth/me`

Headers :
- `Authorization: Bearer <votre_token>`

**Réponse** (200 OK) :
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "is_active": true
}
```

### 4. Logout (Révoquer le token)

**POST** `/auth/logout`

Headers :
- `Authorization: Bearer <votre_token>`

**Réponse** (200 OK) :
```json
{
  "message": "Successfully logged out"
}
```

## 🧪 Tester avec curl

### Sign-up
```powershell
curl -X POST "http://localhost:8000/auth/signup" `
  -H "Content-Type: application/json" `
  -d '{"username":"alice","email":"alice@test.com","password":"secret123"}'
```

### Login
```powershell
curl -X POST "http://localhost:8000/auth/login" `
  -F "username=alice" `
  -F "password=secret123"
```

### Get user info (remplacer TOKEN)
```powershell
curl -X GET "http://localhost:8000/auth/me" `
  -H "Authorization: Bearer TOKEN"
```

### Logout
```powershell
curl -X POST "http://localhost:8000/auth/logout" `
  -H "Authorization: Bearer TOKEN"
```

## 🧪 Tester avec Python

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Sign-up
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "username": "alice",
    "email": "alice@test.com",
    "password": "secret123"
})
print("Signup:", response.json())

# 2. Login
response = requests.post(f"{BASE_URL}/auth/login", data={
    "username": "alice",
    "password": "secret123"
})
token_data = response.json()
token = token_data["access_token"]
print("Token:", token)

# 3. Get user info
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print("User info:", response.json())

# 4. Logout
response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
print("Logout:", response.json())
```

## 📁 Structure du projet

```
back_EMP/
├── app/
│   ├── __init__.py
│   ├── main.py              # Point d'entrée FastAPI
│   ├── config.py            # Configuration (.env)
│   ├── database.py          # Connexion SQL Server
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py          # Modèle User (SQLAlchemy)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py          # Schémas Pydantic
│   ├── routers/
│   │   ├── __init__.py
│   │   └── auth.py          # Endpoints auth
│   └── utils/
│       ├── __init__.py
│       └── security.py      # JWT + hashing
├── .env                     # Variables d'environnement
├── requirements.txt
└── README.md
```

## 🔐 Sécurité

- **Mots de passe** : hashés avec bcrypt
- **Tokens JWT** : signés avec HS256, expiration configurable
- **Logout** : blacklist en mémoire (à remplacer par Redis en prod)
- **CORS** : configuré pour le frontend

## 🛠️ Prochaines étapes

1. Ajouter endpoints pour upload/traitement de documents PDF
2. Intégrer OCR (Tesseract + pdf2image)
3. Ajouter extraction de données structurées
4. Implémenter stockage persistant pour tokens révoqués (Redis)
5. Ajouter tests unitaires (pytest)
