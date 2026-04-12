# Système d'Authentification avec Validation Email et Approbation Admin

## Vue d'ensemble

Ce système implémente un flux d'inscription en 3 étapes:
1. **Inscription** - L'utilisateur crée un compte
2. **Vérification d'email** - L'utilisateur confirme son adresse email
3. **Approbation admin** - L'administrateur approuve l'accès (avant d'accéder à l'application)

---

## 🔄 Flux Utilisateur

### 1️⃣ Inscription (Sign Up)
```
User → /auth/signup (POST)
  ↓
Compte créé avec:
  - is_email_verified = False
  - is_approved = False
  ↓
Email de validation envoyé (via Mailtrap)
  ↓
Réponse au client
```

**Données envoyées:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

### 2️⃣ Vérification d'Email
L'utilisateur reçoit un lien par email:
```
https://frontend.url/verify-email?token=JWT_TOKEN_VERIFICATION
```

**Endpoint backend:**
```
POST /auth/verify-email
{
  "token": "JWT_TOKEN_VERIFICATION"
}
```

**Après vérification:**
- Champs mis à jour: `is_email_verified = True`
- L'utilisateur ne peut toujours pas se connecter (en attente d'approbation)

### 3️⃣ Page d'Attente (Pending Users)
L'administrateur se rend sur `/admin/users`

**Onglet "En attente d'approbation"** affiche:
- Username
- Email
- Date inscription
- Boutons: **Approuver** | **Rejeter**

### 4️⃣ Approbation par Admin
```
Admin → Bouton "Approuver" → /auth/approve-user/{user_id}
  ↓
Utilisateur reçoit email: "Votre compte a été approuvé"
  ↓
is_approved = True
  ↓
Utilisateur peut maintenant se connecter
```

### 5️⃣ Rejet par Admin
```
Admin → Bouton "Rejeter" → /auth/reject-user/{user_id}
  ↓
Utilisateur reçoit email: "Votre inscription a été rejetée"
  ↓
Compte supprimé de la base de données
```

### 6️⃣ Connexion (Login)
```
User → /auth/login (POST)
  ↓
Vérifications:
  1. ✅ Email et mot de passe corrects
  2. ✅ Utilisateur actif (is_active = True)
  3. ✅ Email vérifié (is_email_verified = True)
  4. ✅ Compte approuvé (is_approved = True)
  ↓
Si OK: Token JWT retourné
Si KO: Erreur descriptive retournée
```

---

## 📊 Modèle de Données

### Nouveau modèle User
```python
class User(Base):
    __tablename__ = "users"
    
    id: int (clé primaire)
    username: str (unique)
    email: str (unique)
    hashed_password: str
    role: str (default: "user")
    is_active: bool (default: True)
    is_email_verified: bool (NEW - default: False)  ⭐
    is_approved: bool (NEW - default: False)         ⭐
    created_at: datetime
    updated_at: datetime
```

---

## 🔐 Tokens JWT

### Token d'Accès (Access Token)
- **Durée:** Configurable (par défaut 30 min)
- **Scope:** `None` (accès général)
- **Usage:** Authentification API

### Token de Vérification d'Email
- **Durée:** 24 heures
- **Scope:** `email_verification`
- **Usage:** `/auth/verify-email`

### Token de Reset Password (existant)
- **Durée:** 15 minutes
- **Scope:** `password_reset`
- **Usage:** `/auth/reset-password`

---

## 📧 Emails Envoyés

### 1. Email de Vérification (inscription)
```
Sujet: "Vérifiez votre adresse email"

Corps:
  Lien de vérification valide 24h
  https://frontend/verify-email?token=...
```

### 2. Email d'Approbation (admin approuve)
```
Sujet: "Votre compte a été approuvé"

Corps:
  "Vous pouvez maintenant vous connecter à l'application"
```

### 3. Email de Rejet (admin rejette)
```
Sujet: "Votre compte a été rejeté"

Corps:
  "Malheureusement, votre demande a été rejetée"
```

---

## 🛠️ Configuration Mailtrap

**J'ai utilisé la même configuration pour les nouveaux emails que pour le reset password.**

Dans `.env`:
```env
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=587
SMTP_USER=votre_username_mailtrap
SMTP_PASSWORD=votre_password_mailtrap
SMTP_FROM=noreply@example.com
SMTP_USE_TLS=true
```

---

## 📁 Fichiers Modifiés

### Backend (Python/FastAPI)

#### 1. **app/models/user.py**
- ✅ Ajout de `is_email_verified` (bool)
- ✅ Ajout de `is_approved` (bool)

#### 2. **app/schemas/user.py**
- ✅ Ajout de `is_email_verified` et `is_approved` dans `UserOut`
- ✅ Ajout de `UserOut`, `UserInDB` et signature
- ✅ Nouveaux schémas:
  - `EmailVerification` (token)
  - `SignupResponse`
  - `ApprovalResponse`

#### 3. **app/utils/security.py**
- ✅ `create_email_verification_token()` - Crée token de 24h
- ✅ `decode_email_verification_token()` - Décode et valide le scope

#### 4. **app/utils/email_service.py**
- ✅ `send_email_verification()` - Email de vérification
- ✅ `send_approval_notification()` - Email d'approbation/rejet
- ✅ (ancien) `send_reset_email()` - Inchangé

#### 5. **app/routers/auth.py**
- ✅ Modification de `create_user()` - Ajoute les flags
- ✅ Modification de `signup()` - Envoie email, crée compte non approuvé
- ✅ Modification de `login()` - Vérifie email_verified + approved
- ✅ **NEW** `verify_email()` - POST /auth/verify-email
- ✅ **NEW** `get_pending_users()` - GET /auth/pending-users
- ✅ **NEW** `approve_user()` - POST /auth/approve-user/{user_id}
- ✅ **NEW** `reject_user()` - POST /auth/reject-user/{user_id}

### Frontend (React/Vite)

#### 1. **src/services/userService.js**
- ✅ `verifyEmail(token)`
- ✅ `getPendingUsers()`
- ✅ `approveUser(userId)`
- ✅ `rejectUser(userId)`

#### 2. **src/pages/VerifyEmailPage.jsx** (NOUVEAU)
- ✅ Page de vérification d'email
- ✅ Extrait token depuis URL
- ✅ Affiche statut (loading, success, error)
- ✅ Redirection vers login après succès

#### 3. **src/pages/AdminUsersPage.jsx**
- ✅ Deux onglets: "En attente" | "Tous les utilisateurs"
- ✅ Onglet "En attente" avec boutons Approuver/Rejeter
- ✅ Affichage du statut d'approbation
- ✅ Visualisation de is_email_verified et is_approved

#### 4. **src/App.jsx**
- ✅ Ajout import `VerifyEmailPage`
- ✅ Ajout route `/verify-email`

---

## 🧪 Étapes de Test

### Test 1: Inscription
```bash
POST /auth/signup
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "TestPass123"
}

Résultat attendu:
✅ 201 Created
✅ Email de vérification envoyé (voir Mailtrap)
✅ is_email_verified = False
✅ is_approved = False
```

### Test 2: Vérification Email
```bash
# Récupérer le token depuis Mailtrap
POST /auth/verify-email
{
  "token": "JWT_FROM_EMAIL"
}

Résultat attendu:
✅ 200 OK
✅ is_email_verified = True (en BD)
✅ is_approved = False (toujours)
```

### Test 3: Login (avant approbation)
```bash
POST /auth/login
{
  "email": "test@example.com",
  "password": "TestPass123"
}

Résultat attendu:
❌ 400 Bad Request
❌ Message: "Account not approved yet..."
```

### Test 4: Admin approuve
```bash
# Admin appelle:
POST /auth/approve-user/1

Résultat attendu:
✅ 200 OK
✅ is_approved = True (en BD)
✅ Email d'approbation envoyé
```

### Test 5: Login (après approbation)
```bash
POST /auth/login
{
  "email": "test@example.com",
  "password": "TestPass123"
}

Résultat attendu:
✅ 200 OK
✅ access_token retourné
✅ Connexion réussie
```

### Test 6: Admin rejette
```bash
# Admin appelle:
POST /auth/reject-user/2

Résultat attendu:
✅ 200 OK
✅ Utilisateur supprimé de la BD
✅ Email de rejet envoyé
```

---

## 📋 Checklist d'Implémentation

### Backend
- [x] Modifier le modèle User
- [x] Ajouter schemas Pydantic
- [x] Ajouter fonctions security JWT
- [x] Ajouter fonctions email
- [x] Modifier endpoints auth
- [x] Ajouter endpoints validation/approbation

### Frontend
- [x] Ajouter fonctions API
- [x] Créer page VerifyEmailPage
- [x] Modifier AdminUsersPage
- [x] Ajouter route dans App.jsx

### Base de Données
- [ ] **À FAIRE:** Migration Alembic OU ALTER TABLE (voir section suivante)

---

## 🗄️ Migration Base de Données

**Vous devez ajouter les deux colonnes au modèle User. Deux approches:**

### Option 1: Utiliser Alembic (recommandé pour prod)
```bash
cd back_EMP
alembic revision --autogenerate -m "Add is_email_verified and is_approved to User"
alembic upgrade head
```

### Option 2: Script SQL direct (si pas Alembic)
```sql
-- SQL Server
ALTER TABLE users
ADD is_email_verified BIT DEFAULT 0 NOT NULL,
    is_approved BIT DEFAULT 0 NOT NULL;

-- Pour utilisateurs existants
UPDATE users SET is_email_verified = 1, is_approved = 1;
```

### Option 3: Via SQLAlchemy (dans main.py)
```python
# Lancer une seule fois au démarrage
from app.database import engine
from app.models.user import User
User.metadata.create_all(bind=engine)  # Crée les nouvelles colonnes
```

---

## 🔄 Résumé du Flux Complet

```
1. User → /auth/signup
   └─ Email sent ✉️
   └─ is_email_verified = False
   └─ is_approved = False

2. User reçoit email → Click link
   └─ ...verify-email?token=XXX
   └─ is_email_verified = True

3. User → /auth/login
   └─ ❌ "Account not approved"

4. Admin → /admin/users → "En attente"
   └─ Voit l'utilisateur
   └─ Clique "Approuver"

5. /auth/approve-user/{id}
   └─ is_approved = True
   └─ Email d'approbation envoyé ✉️

6. User → /auth/login
   └─ ✅ Token JWT
   └─ Accès à l'app
```

---

## 📞 Support & Dépannage

### Problème: Email pas reçu
- Vérifier Mailtrap inbox (sandbox.smtp.mailtrap.io)
- Vérifier logs backend pour erreurs SMTP
- Vérifier `.env` SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

### Problème: Token expiré
- Duration: 24h pour email_verification
- Créer nouveau token: Renvoyer signup ou nouveau lien

### Problème: Login refuse
- Afficher message d'erreur pour: email pas vérifié, pas approuvé, inactif
- Admin peut approuver dans /admin/users

---

## 🎯 Fonctionnalités Futures

- [ ] Réenvoi d'email de vérification
- [ ] Dashboard pour admin (statistiques)
- [ ] Logs d'approbation/rejet
- [ ] Rate limiting sur signup
- [ ] CAPTCHA sur inscription
- [ ] 2FA authentification

---

**Implémentation terminée** ✅
Date: 10 Avril 2026
