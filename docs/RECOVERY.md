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
- **Script preview defaults to a template, not AI.** A Gemini adapter is
  included (original build's recovered prompt) and activates with
  `SCRIPT_PROVIDER=gemini` + an owner key; otherwise the endpoint streams the
  same HOOK / SCRIPT / CTA format from a fixed template and the banner says
  "script previews templated".
- **Google sign-in is off until the owner registers a Google OAuth client.**
  The original went through Emergent's hosted auth (`auth.emergentagent.com`),
  which is not reusable. This build implements the standard Google OAuth2
  authorization-code flow (`/api/auth/google/login` + `/callback`), active only
  when `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are set; otherwise the
  button bounces back with a clear notice. Email/password auth works fully.
- **Password reset emails send only when SMTP is configured** (`SMTP_HOST` and
  friends); without SMTP the reset link is logged, never emailed. Reset links
  are always built from the server-configured `FRONTEND_ORIGIN`, never from
  client-supplied origins.

## Security model (independent-review fixes)

- Password registration never grants admin; `ADMIN_EMAILS` promotion applies
  only on the Google OAuth path (Google-verified email) or out-of-band.
- Google OAuth state is single-use, 10-minute, and bound to the initiating
  browser with an HttpOnly cookie; only Google-verified emails create/sign in.
  Linking an existing password account to a verified Google sign-in revokes
  every pre-verification credential (password, live sessions, outstanding
  reset tokens), so a squatter who registered the address first keeps nothing;
  the owner can set a fresh password afterwards via the reset flow, which now
  reaches the verified inbox.
- Guest orders attach to an account by email only after that email is verified
  (Google); password-registered accounts see only their own checkouts.
- Payment fulfillment is idempotent and fails closed: verified `paid` status,
  expected amount/currency, matching provider and session; expiry/failure
  events never downgrade a paid order; mock payments never send real email.
- Teasers accept only photos uploaded by the requesting account; payment and
  reset redirect targets come from server config only.
- **Paid-video production is manual by default, with optional automation.**
  The original promised "You approve the script before we render" and its app
  tracked only payment status (the dashboard hardcoded "In production");
  production was operator work outside the app. This build makes the promised
  approval loop real: verified payment -> in production -> script -> customer
  approves or requests changes -> delivered. Nothing renders without an
  approved script. With `ORDER_AUTOMATION=off` (the default) every step is
  done by the admin by hand; see below for the optional automated pipeline.

## Verified

- `python -m pytest tests -q` - 76 passed (56 original + 2 more demo-flag +
  18 automation: full pipeline, duplicate-submit/duplicate-finish guards,
  failed submit, lost-contact resume, provider-reported failure, restart
  recovery for submitted/mid-submit/mid-draft states, admin retry + reconcile,
  change-request redraft, off-by-default, verified default model ids): auth lifecycle incl. refresh/logout,
  uploads + file serving, checkout + payment status, teaser lifecycle, SSE
  script preview, admin desk, password reset, provider adapters (Stripe/Gemini/
  fal/SMTP/Google OAuth) with fake transports, payment fail-closed +
  idempotency + expiry guards, the order script-approval workflow, and
  regression tests for the independent-review attack paths (reset-origin
  poisoning, registration admin escalation, OAuth login CSRF, unverified-email
  order access, cross-user teaser photos, misconfigured-Stripe capability).
- `npx craco test` - 14 passed (capability mapping, payment copy).
- `npx craco build` - production build compiles clean.
- Playwright journeys (Chromium): responsive menu/order/script-review flows at
  mobile, tablet and desktop widths.


## Optional paid-order automation (OFF by default)

Requested direction (original build chat, 2026-10-29): AI integrations for the
business - Gemini for scripts (the owner picked "Gemini 3 Flash" there) and
fal.ai for video generation. The concrete pipeline below is the builder's
design, not a detailed owner spec: paid order -> Gemini drafts the script ->
customer approves the exact script (gate kept from the original promise) ->
fal.ai renders the avatar video -> stored, marked delivered, emailed.

It runs ONLY when `ORDER_AUTOMATION=on` AND the relevant keys are set
(`SCRIPT_PROVIDER=gemini` + `GEMINI_API_KEY` for drafts, `TEASER_PROVIDER=fal`
+ `FAL_KEY` for renders). Off by default; nothing is charged while off.

Provider facts verified against official docs on 2026-10-29:
- Gemini model code `gemini-3-flash-preview`:
  https://ai.google.dev/gemini-api/docs/models/gemini-3-flash-preview
- fal endpoint `veed/fabric-1.0/text` (inputs image_url + text + resolution,
  output video file; $0.08/second at 480p, $0.15/second at 720p):
  https://fal.ai/models/veed/fabric-1.0/text/llms.txt
Re-check both pages before enabling - model ids and prices change.

Money-safety design:
- Billable automation only touches orders with a VERIFIED real payment
  (provider='stripe' + paid, set only by the verified Stripe fulfillment
  path). A mock-paid order triggers zero Gemini/fal calls even with
  ORDER_AUTOMATION=on and keys set - the mock checkout does not even schedule
  the draft, both automation functions re-check the order's payment
  provenance, and the admin render retry refuses non-real-paid orders.
- The fal submit is the only billable render step. Each order submits at most once:
  an atomic claim (`video_job` none -> submitting) blocks duplicates, and the
  provider request id + model are persisted immediately after submit
  (`video_request_id`, `video_request_model`).
- A failed or ambiguous submit is NEVER retried automatically - a retry could
  be billed twice. The order falls back to the manual admin path with an
  error that says the billing state is unknown.
- Restart recovery: on boot, orders still `submitted` resume polling the SAME
  provider job (polling and downloading are free; no new charge). Orders that
  died mid-submit (no request id) are marked `failed` for manual review -
  never auto-resubmitted. Interrupted Gemini drafts (`drafting`) resume once;
  the draft never reached the customer and the approval gate still applies.
- Admin recovery is explicit and reviewed: `POST
  /api/admin/orders/{ref}/render/retry` (only for `failed` jobs, only after
  the operator checks the provider dashboard for billing) and `POST
  /api/admin/orders/{ref}/render/reconcile` (re-poll a `submitted` job now -
  free). The admin desk shows the video job state, the recorded error, and
  both actions; the retry button carries a billing warning.
- The finisher claims `submitted -> done` atomically, so duplicate resumes
  cannot store, deliver or email twice. If local storage fails after a render
  completes, the job rolls back to `submitted` so reconcile re-downloads the
  finished video (free) instead of resubmitting.

Dashboard: delivered orders show the video inline with a download link
(`video_file_id` was already returned by `/api/orders/mine`).

Known limits: background work runs in-process (daemon threads), not a durable
queue. Polling of a submitted render resumes ONLY when the server restarts or
an admin clicks "Re-check render" - there is no periodic background recheck,
so if the server is down (or stays up but the polling thread already died) the
finished video simply waits at the provider until one of those two happens;
nothing is lost and nothing is billed twice, but delivery stalls until then.
Render polling caps at 5 minutes per attempt; longer renders stay `submitted`
and resume on restart/reconcile. SMTP still required for the script-ready and
delivery emails.
