# Recovered vs rebuilt

## Recovered (original code, byte-exact)

The full frontend source under `frontend/src/` and `frontend/public/` was
recovered on 2026-10-29 from the published app's webpack source maps at
`https://aipromovids.preview.emergentagent.com/static/js/bundle.js.map`.
Webpack `sourcesContent` contains the exact original files, so these are the
author's real sources, not re-typed approximations:

- 30 source files: pages (Landing, Login, Dashboard, Admin, Payment,
  ResetPassword, AuthCallback), site components, UI primitives, contexts,
  `lib/api.js`, `lib/utils.js`, `App.js`, `index.js`, `public/index.html`.

One legitimate, read-only recovery route; no bypass of any Emergent control.
The backend is not reachable this way - it never leaves Emergent's workspace,
and Emergent's full-export routes are gated to paid plans server-side.

`frontend/src/index.css` is the compiled stylesheet extracted from the same
source map (the original Tailwind input file is not recoverable). It is plain
CSS and needs no Tailwind build step; re-creating Tailwind config is optional
future work.

## Rebuilt (written from scratch, 2026-10-29)

Everything else:

- `backend/` - FastAPI + SQLite implementing the exact endpoints the recovered
  frontend calls, derived from `src/lib/api.js`, `ScriptPreview.jsx`, and the
  pages/contexts: cookie auth with refresh rotation
  (`register/login/logout/me/refresh/forgot-password/reset-password`),
  uploads + file serving, mock checkout + payment status + my orders, teaser
  lifecycle with a free-quota, SSE script preview, and the admin overview/orders
  desk.
- Frontend build config: `package.json` (dependency set derived from the
  recovered imports), `craco.config.js` (`@` alias), `jsconfig.json`,
  `.env.example` files.

## Honest limits of the rebuild

- **Payments run in mock mode.** `/api/payments/checkout` creates the order,
  marks it paid without charging anyone, and redirects to the success page,
  mirroring the original Stripe round-trip. No Stripe code is included; set
  `PAYMENT_PROVIDER=stripe` + `STRIPE_API_KEY` and add a real integration.
- **Teaser avatar videos fail loudly.** The original used an external AI video
  provider. With none configured, teasers move from `processing` to `failed`
  with an explicit explanation. No fake video output is produced.
- **Script preview is a template, not AI.** The endpoint streams the same
  HOOK / SCRIPT / CTA format the frontend parses, generated from a fixed
  template. No AI model is called.
- **Google sign-in is off until the owner registers a Google OAuth client.**
  The original went through Emergent's hosted auth (`auth.emergentagent.com`),
  which is not reusable. This build implements the standard Google OAuth2
  authorization-code flow (`/api/auth/google/login` + `/callback`), active only
  when `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are set; otherwise the
  button bounces back with a clear notice. Email/password auth works fully.
- **Password reset emails send only when SMTP is configured** (`SMTP_HOST` and
  friends); without SMTP the reset link is logged, never emailed.
- **Paid-video production is manual, as the original intended.** The original
  promised "You approve the script before we render" and its app tracked only
  payment status (the dashboard hardcoded "In production"); production was
  operator work outside the app. This build makes the promised approval loop
  real: verified payment -> in production -> admin sends script -> customer
  approves or requests changes -> admin marks delivered. No automated video
  production is claimed; nothing renders without an approved script.

## Verified

- `python -m pytest tests -q` - 8 passed (auth lifecycle incl. refresh/logout,
  upload + file serving, mock checkout + status + my orders, teaser lifecycle +
  free limit, SSE script preview, admin overview/orders + 403 for non-admins,
  password reset flow, Google sign-in 501).
- `npm run build` (CRACO) - production build compiles clean.
- Live smoke test: uvicorn serving `/api`, register, `/auth/me`, mock checkout.
