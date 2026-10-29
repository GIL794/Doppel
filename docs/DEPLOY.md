# Deploying DoppelAI at $0 (single origin)

Status: prepared and tested locally; NOT deployed. No accounts, keys, charges or
live provider calls have been made.

## Shape
One Docker image: FastAPI serves `/api/*` and the built React app (same origin, so
login cookies work with `SameSite=Lax; Secure`). State is external so a sleeping or
restarted free host loses nothing:
- `DATABASE_URL` - PostgreSQL (Supabase or Neon free). Unset = local SQLite (dev).
- `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` (+ optional `SUPABASE_BUCKET`, default
  `doppelai-files`, create it PRIVATE) - uploads and rendered videos. Unset = local disk.
  Files are served by redirect to a 1-hour signed URL. Free projects cap files at 50 MB.

## Production switches
- `APP_ENV=production`: cookies are `Secure`; the simulated checkout is closed
  (503 "Ordering is not open yet", `/api` reports `payments: "closed"`, the site
  shows "Early access / Ordering opens soon"). Ordering opens only when
  `PAYMENT_PROVIDER=stripe` + `STRIPE_API_KEY` + `STRIPE_WEBHOOK_SECRET` are set and
  the Stripe webhook points at `https://<host>/api/stripe/webhook`.
- Paid AI stays off until `ORDER_AUTOMATION=on` plus provider keys; see RECOVERY.md.

## Limits to know
- Render free: sleeps after 15 min without HTTP traffic (about 1 min cold start),
  750 instance-hours/month, "not for production" per Render docs. An in-flight
  render or script draft thread dies if the instance sleeps; recovery runs on the
  next boot (resume polling the same fal job) or via the admin "Re-check render".
- Supabase free: 500 MB database, project paused after 1 week of inactivity.
- The Docker image build is untested (no Docker in the build sandbox); the app, the
  frontend build and the single-origin serving were each tested separately.

## Tests
`cd backend && python -m pytest tests -q` (SQLite); the same suite against PostgreSQL
by setting `DATABASE_URL` to an empty database (tests/conftest.py resets rows).
