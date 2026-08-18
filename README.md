# Structura — Web app

Version web de Mobile-app, servie entièrement par un serveur Python (FastAPI).
Le frontend (Expo Router / React Native Web / TypeScript) est compilé en site
statique une fois au build, puis FastAPI le sert avec l'API `/api` sur la même
origine. Aucun process Node n'est nécessaire en production — Yarn ne sert
qu'à builder.

## Structure

```
Web-app/
  frontend/   Expo Router + TypeScript (web only : ios/android/admob retirés)
  backend/    FastAPI + Motor/MongoDB + Str-lib (backend/strlib_repo)
```

## Build + run (local)

```bash
# 1. Build du site statique
cd frontend
yarn install
yarn build          # = expo export -p web -> génère frontend/dist/

# 2. Lancer le serveur Python (site + API sur le même port)
cd ../backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # (Linux/Mac: .venv/bin/pip)
.venv/Scripts/python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

Puis ouvrir http://localhost:8001 — le site et `/api/*` répondent sur le
même port.

## Notes

- `frontend/.env` : `EXPO_PUBLIC_BACKEND_URL` est vide → les appels API du
  frontend sont relatifs (`/api/...`), donc rien à changer entre local et
  prod tant que le site et l'API sont servis par le même serveur/domaine.
- `backend/.env` : `DB_NAME=structura_web`, séparée de la base utilisée par
  Mobile-app.
- Après tout changement dans `frontend/`, il faut relancer `yarn build`
  puis redémarrer le serveur Python pour que `server.py` détecte
  `frontend/dist/`.
- `backend/strlib_repo` est une copie de Str-lib (même mécanisme que dans
  Mobile-app) — à resynchroniser manuellement si Str-lib évolue.
- Paiement Premium via Stripe (`backend/stripe_service.py`) : renseigner
  `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`,
  `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL` dans `backend/.env` pour
  activer le checkout — sans ça l'appel renvoie une erreur 500 propre,
  le reste de l'app fonctionne normalement.
- Mobile-app n'est plus un dépôt Git suivi (dossier remplacé par un
  téléchargement ZIP `Mobile-app-main/`) : pour une prochaine synchro,
  comparer directement les fichiers plutôt que `git diff`.
