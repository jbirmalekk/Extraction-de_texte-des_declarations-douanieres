# Frontend EMP SmartOCR

Application React/Vite pour l'authentification, l'import OCR, la validation de champs extraits et le reporting (dashboard/historique).

## Prerequis

- Node.js 18+
- Backend FastAPI disponible (par defaut `http://localhost:8000`)

## Installation

```bash
npm install
```

## Configuration

Creer un fichier `.env` (ou `.env.local`) a la racine de `front_EMP/`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Lancement

```bash
npm run dev
```

Application: `http://localhost:5173`

## Build production

```bash
npm run build
npm run preview
```

## Flux fonctionnels

1. **Auth**
   - Login/Register/Forgot/Reset password
   - Contexte session: `src/store/AuthContext.jsx`
2. **OCR**
   - Import document: `src/pages/ImportPage.jsx`
   - Extraction backend: `src/services/ocrService.js` -> `POST /api/ocr`
3. **Validation**
   - Resultats OCR: `src/pages/OcrResultPage.jsx`
   - Validation finale: `src/pages/ValidationPage.jsx` -> `PUT /api/ocr/{id}/valider`
4. **Reporting**
   - User dashboard/history: `/api/dashboard/me`, `/api/dashboard/me/history`
   - Admin dashboard/history: `/api/dashboard/admin`, `/api/dashboard/history`

## Routes principales

- `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`
- `/dashboard`, `/history`, `/profile`
- `/import`, `/ocr-result`, `/validation`, `/documents/:documentId`
- `/admin/dashboard`, `/admin/users`

## Services API

- `src/services/api.js` : client Axios + bearer token
- `src/services/authService.js` : endpoints `/auth/*`
- `src/services/ocrService.js` : endpoints `/api/*`
- `src/services/userService.js` : endpoints admin/profil utilisateur
