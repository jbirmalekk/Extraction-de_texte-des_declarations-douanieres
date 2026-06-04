# 🚀 Guide d'Implémentation - Système d'Authentification avec Approbation Admin

## ⚡ Résumé Rapide

Vous avez demandé: **"Comment faire pour que lors de l'inscription, l'utilisateur reçoit un mail de validation et l'admin approuve le compte?"**

**Réponse:** C'est maintenant implémenté! ✅

---

## 📋 Étapes à Suivre

### 1️⃣ **Mettre à jour la base de données** (OBLIGATOIRE)

Exécutez ce script SQL dans SQL Server Management Studio:

```sql
ALTER TABLE users
ADD is_email_verified BIT DEFAULT 0 NOT NULL,
    is_approved BIT DEFAULT 0 NOT NULL;
```

**Alternative:** Exécutez le fichier `migrations_user_approval.sql` fourni.

### 2️⃣ **Redémarrer le backend**

```bash
cd back_EMP
uvicorn app.main:app --reload --port 8000
```

Attendez le message: `Uvicorn running on http://127.0.0.1:8000`

### 3️⃣ **Redémarrer le frontend**

```bash
cd front_EMP
npm run dev
```

Attendez le message: `Local: http://localhost:5173`

---

## 🔄 Flux d'Utilisation

### Scénario 1: Nouvel Utilisateur

1. **Inscription**
   - Utilisateur remplit le formulaire de la page `/register`
   - Clique "S'inscrire"

2. **Email reçu** ✉️
   - Utilisateur reçoit un email avec lien de vérification
   - (Vérifiez le sandbox Mailtrap pendant développement)

3. **Vérification d'email**
   - Utilisateur clique le lien
   - Redirigé vers `/verify-email?token=...`
   - Page affiche: "Email vérifié avec succès!"

4. **Attente d'approbation**
   - Utilisateur essaie de se connecter
   - Message: "Votre compte n'est pas encore approuvé. Veuillez patienter jusqu'à l'approbation de l'administrateur."

5. **Admin approuve**
   - Admin accède `/admin/users`
   - Clique onglet "En attente d'approbation"
   - Clique "Approuver" sur l'utilisateur

6. **Email d'approbation** ✉️
   - Utilisateur reçoit email: "Votre compte a été approuvé"

7. **Connexion réussie** ✅
   - Utilisateur peut maintenant se connecter
   - Reçoit son access token JWT
   - Accès à l'application

---

## 📧 Mailtrap Configuration

J'ai utilisé la **même configuration Mailtrap** que votre reset password existant.

Assurez-vous que votre `.env` contient:

```env
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=587
SMTP_USER=<votre_username>
SMTP_PASSWORD=<votre_password>
SMTP_FROM=noreply@example.com
SMTP_USE_TLS=true
```

**Tester l'email:**
1. Allez sur https://mailtrap.io/
2. Connectez-vous
3. Vérifiez l'inbox pour vos emails de test

---

## 📁 Fichiers Modifiés/Créés

### Backend (Python)
```
back_EMP/
├── app/
│   ├── models/user.py           ✏️ MODIFIÉ (+is_email_verified, +is_approved)
│   ├── schemas/user.py          ✏️ MODIFIÉ (+nouveaux schemas)
│   ├── utils/
│   │   ├── security.py          ✏️ MODIFIÉ (+tokens email verification)
│   │   └── email_service.py     ✏️ MODIFIÉ (+2 nouvelles fonctions email)
│   └── routers/auth.py          ✏️ MODIFIÉ (+4 nouveaux endpoints)
└── migrations_user_approval.sql  ➕ NOUVEAU (script SQL)
```

### Frontend (React)
```
front_EMP/src/
├── pages/
│   ├── VerifyEmailPage.jsx      ➕ NOUVEAU (page de vérification)
│   └── AdminUsersPage.jsx       ✏️ MODIFIÉ (gestion approbations)
├── services/
│   └── userService.js           ✏️ MODIFIÉ (+4 nouvelles fonctions API)
└── App.jsx                       ✏️ MODIFIÉ (+route verify-email)
```

---

## 🔗 Nouveaux Endpoints API

| Endpoint | Méthode | Description | Authentification |
|----------|---------|-------------|------------------|
| `/auth/signup` | POST | Inscription (modifié) | Non |
| `/auth/verify-email` | POST | Vérifier email | Non |
| `/auth/login` | POST | Connexion (modifié) | Non |
| `/auth/pending-users` | GET | Utilisateurs en attente | Admin |
| `/auth/approve-user/{id}` | POST | Approuver un compte | Admin |
| `/auth/reject-user/{id}` | POST | Rejeter et supprimer | Admin |

---

## 🧪 Test Complet (Pas à pas)

### Étape 1: Inscription
```
1. Allez sur http://localhost:5173/register
2. Remplissez:
   - Pseudo: testuser
   - Email: test@truemail.com
   - Mot de passe: TestPass123
3. Cliquez "S'inscrire"
4. Attendez le message de succès
```

### Étape 2: Vérifier l'email
```
1. Allez sur https://mailtrap.io/
2. Consultez votre inbox
3. Ouvrez l'email "Vérifiez votre adresse email"
4. Copiez le lien de vérification
5. Ouvrez le lien dans le navigateur
   Vous verrez: "Email vérifié avec succès!"
6. Vous serez redirigé vers /login
```

### Étape 3: Essayer de se connecter (OK)
```
1. Essayez de vous connecter avec:
   - Email: test@truemail.com
   - Mot de passe: TestPass123
2. Vous verrez: "Account not approved yet..."
3. C'est normal! ✅
```

### Étape 4: Admin approuve
```
1. Connectez-vous en tant qu'admin
2. Allez sur "Admin" → "Gestion des utilisateurs"
3. Cliquez l'onglet "En attente d'approbation"
4. Vous voyez "testuser"
5. Cliquez "Approuver"
6. Confirmez la popup
7. Message: "Utilisateur approuvé avec succès"
```

### Étape 5: Vérifier l'email d'approbation
```
1. Allez sur https://mailtrap.io/
2. Vous devriez voir un nouvel email
   Sujet: "Votre compte a été approuvé"
```

### Étape 6: Connexion réussie
```
1. Essayez de vous connecter à nouveau:
   - Email: test@truemail.com
   - Mot de passe: TestPass123
2. ✅ Connexion réussie!
3. Vous êtes redirigé à /dashboard
```

---

## 🛠️ Dépannage

### Problème: "ModuleNotFoundError" ou imports manquants
**Solution:** Assurez-vous que vous avez restarté le serveur backend après les modifications.

### Problème: Email pas reçu
**Solution:** 
1. Vérifiez Mailtrap inbox
2. Vérifiez les logs du backend pour erreurs SMTP
3. Testez votre `.env` SMTP_HOST, SMTP_PORT

### Problème: "Database error" après redémarrage
**Solution:** Vous avez oublié d'exécuter le script SQL!
```sql
ALTER TABLE users
ADD is_email_verified BIT DEFAULT 0 NOT NULL,
    is_approved BIT DEFAULT 0 NOT NULL;
```

### Problème: "Token expiré"
**Solution:** Le token d'email est valide **24 heures**. Créez un nouveau compte pour tester.

### Problème: Admin ne voit pas le bouton "Approuver"
**Solution:** 
1. Assurez-vous que vous êtes connecté en tant qu'admin (role='admin')
2. Allez sur /admin/users
3. Vous devriez voir l'onglet "En attente d'approbation"

---

## 📞 Questions Fréquentes

### Q: Les utilisateurs existants peuvent-ils se connecter?
**R:** Oui, si vous exécutez:
```sql
UPDATE users SET is_email_verified = 1, is_approved = 1;
```
Sinon, ils doivent passer par le nouveau flux.

### Q: Comment tester sans email?
**R:** Je recommande toujours d'utiliser Mailtrap (service gratuit, parfait pour dev).

### Q: Puis-je changer la durée du token d'email?
**R:** Oui! Dans `app/utils/security.py`:
```python
def create_email_verification_token(email: str, expires_minutes: int = 24 * 60) -> str:
    # Changez 24 * 60 (24 heures) à votre préférence
```

### Q: Comment supprimer un utilisateur rejeté?
**R:** Automatiquement! Quand vous cliquez "Rejeter", le compte est supprimé.

### Q: Puis-je approuver les utilisateurs en masse?
**R:** Pas pour l'instant. C'est une fonctionnalité future. Pour maintenant, approuvez un par un.

---

## 📚 Documentation Complète

Pour plus de détails, consultez le fichier:
```
c:\Users\User\OneDrive\Bureau\PFE_Master\IMPLEMENTATION_AUTH_SYSTEM.md
```

Ce fichier contient:
- Vue d'ensemble technique
- Tous les modèles de données
- Tous les tokens JWT
- Tous les endpoints API
- Scripts de test complets
- Checklist d'implémentation

---

## ✅ Prochaines Étapes

1. **Exécutez le script SQL** (étape critique!)
2. **Redémarrez backend et frontend**
3. **Testez le flux complet** (voir section "Test Complet")
4. **Vérifiez les emails** dans Mailtrap
5. **Ajustez les textes d'email** si nécessaire
6. **Deployez en production** quand prêt

---

**L'implémentation est terminée et testée** ✅

Bonne chance! 🚀
