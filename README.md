# Aipromovids (Doppel)

AI-generated spokesperson promo videos for small businesses: visitors try a free
templated script preview, registered users get free avatar "teaser" videos, and a
full promo video costs £350.

## What this repo is

The app was originally built on Emergent (app.emergent.sh). Emergent's free plan
does not export the full project, so this repo combines:

- **Recovered, original code** - the complete frontend source, recovered
  byte-exact from the published app's webpack source maps.
- **Rebuilt code** - the entire backend plus project config, written from
  scratch to match the API contract the recovered frontend expects.

See [docs/RECOVERY.md](docs/RECOVERY.md) for exactly what is recovered vs
rebuilt, how, and the honest limits (mock payments, no AI video provider).

## Layout

- `frontend/` - React 18 + Create React App (CRACO for the `@/` import alias). **Original recovered source**, except build config (`package.json`, `craco.config.js`, `jsconfig.json`, `.env.example`) and `src/index.css` (compiled stylesheet recovered from the source map).
- `backend/` - FastAPI + SQLite. **Rebuilt from scratch** against the frontend's API calls.

## Run locally

Backend:

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # set ADMIN_EMAILS to your email to get the admin desk
python server.py       # http://localhost:8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env
npm start              # http://localhost:3000
```

## Tests

```bash
cd backend && python -m pytest tests -q    # 8 tests covering the full API
cd frontend && npm run build               # production build compiles clean
```
