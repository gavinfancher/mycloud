# Deploy the console (Cloudflare Pages + GitHub)

The SPA in `frontend/` is deployed as **static assets on a Cloudflare Worker**
(Git-connected: build → `wrangler deploy`). You do not need a separate Worker script.

Production URL: `https://app.myhomecloud.dev`  
API URL (separate stack): `https://api.myhomecloud.dev`

## One-time: connect GitHub → Workers & Pages

In [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages** → **Create** → connect Git:

| Setting | Value |
|---|---|
| Repository | `gavinfancher/homecloud` |
| **Production branch** | `main` |
| **Root directory** | `frontend` |
| **Build command** | `npm run build` |
| **Deploy command** | `npx wrangler deploy` |
| **Version command** | `npx wrangler versions upload` *(default — leave as-is)* |
| **Node.js version** | `22` |

The deploy command **cannot be removed** on Workers Git projects — that's expected.
`frontend/wrangler.toml` tells `wrangler deploy` to upload `./dist` as static assets.

Enable **automatic deployments** on push to `main`.

### Environment variables (Pages → Settings → Environment variables)

Set these for **Production** (and Preview if you want Clerk on preview deploys):

| Variable | Value | Notes |
|---|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | `pk_live_…` or `pk_test_…` | From Clerk Dashboard or `clerk env pull` |
| `VITE_API_BASE` | `https://api.myhomecloud.dev` | Also in `frontend/.env.production` (checked in) |

**Do not** set `VITE_DEV_BYPASS_AUTH` in Production. It is only for local `vite dev` and is ignored in prod builds anyway (`import.meta.env.DEV` is false).

### Custom domain

Pages → **Custom domains** → add `app.myhomecloud.dev` (likely already attached if the site is live).

## Backend alignment (control node `.env`)

When Clerk is enabled on the controller, set:

```bash
CLERK_JWKS_URL=https://<slug>.clerk.accounts.dev/.well-known/jwks.json
CLERK_ISSUER=https://<slug>.clerk.accounts.dev
CLERK_AUTHORIZED_PARTIES=https://app.myhomecloud.dev
CLERK_PUBLISHABLE_KEY=pk_…
FRONTEND_ORIGIN=https://app.myhomecloud.dev
CONSOLE_URL=https://app.myhomecloud.dev
API_PUBLIC_HOST=api.myhomecloud.dev
OWNER_USERNAME=gavin
```

Redeploy the stack on the control node after changing `.env`:

```bash
make deploy-stack   # or: docker compose up -d --build
```

## Troubleshooting

### Cloudflare Git builds never start on push

The **Workers Git** webhook often stalls. Use **GitHub Actions** instead (`.github/workflows/deploy-frontend.yml`).

Required GitHub secrets (repo or **production** environment):

| Secret | Value |
|--------|--------|
| `CLOUDFLARE_API_TOKEN` | API token with **Workers Scripts → Edit** (not DNS-only) |
| `CLOUDFLARE_ACCOUNT_ID` | `2750df8a500fb8335c195bad8cccc14a` |
| `VITE_CLERK_PUBLISHABLE_KEY` | Your Clerk `pk_test_…` or `pk_live_…` |

Create the token: Cloudflare Dashboard → **My Profile → API Tokens → Create Token** → template **Edit Cloudflare Workers** (or custom: Account / Workers Scripts / Edit).

After secrets are set, push any `frontend/` change or run **Actions → Deploy frontend → Run workflow**.

Optional: disable **automatic Git builds** on the Worker (Settings → Build) to avoid duplicate deploys.

### Pushes to `main` don't trigger a new deployment

Cloudflare **Workers Git** builds are separate from GitHub Actions CI. Check **Workers & Pages → homecloud → Deployments**:

- If the latest build is older than your last `git push`, the GitHub ↔ Cloudflare webhook may have stalled (common after repo settings changes).
- **Quick fix:** Deployments → **Retry deployment** on the latest commit, or **Create deployment** → branch `main`.
- **Reliable fix:** use the repo workflow `.github/workflows/deploy-frontend.yml` (runs on `frontend/**` pushes). Set GitHub **production** environment secrets:
  - `CLOUDFLARE_API_TOKEN` — Workers deploy permission
  - `CLOUDFLARE_ACCOUNT_ID` — from Cloudflare dashboard URL or `wrangler whoami`
  - `VITE_CLERK_PUBLISHABLE_KEY` — same value as Cloudflare build env

You can disable automatic Git builds in Cloudflare once GitHub Actions deploy is working (avoids duplicate deploys).

**Manual deploy from your laptop** (same as Workers Git uses):

```bash
cd frontend
export VITE_CLERK_PUBLISHABLE_KEY=pk_test_…   # or source from clerk env pull
npm run build
npx wrangler deploy
```

### Build succeeds, deploy fails with "Missing entry-point"

Your project uses **Workers Git deploy** (`npx wrangler deploy`). Ensure
`frontend/wrangler.toml` includes:

```toml
[assets]
directory = "./dist"
not_found_handling = "single-page-application"
```

Commit, push to `main`, and retry. Do **not** try to delete the deploy command —
Workers Git projects require it.

### Build fails: missing Clerk key

Add `VITE_CLERK_PUBLISHABLE_KEY` under Pages → **Environment variables** (Production), then retry.

## Verify a deploy

After pushing to `main`:

1. Cloudflare Pages → **Deployments** — build should succeed.
2. Open `https://app.myhomecloud.dev` — sign-in screen (Clerk), not the dev bypass badge.
3. Browser devtools → Network — API calls go to `https://api.myhomecloud.dev/api/…`.

## Local dev (unchanged)

```bash
make dev-api    # controller on :8080
make dev-web    # Vite on :5173/5174, proxies /api to controller
```

`frontend/.env.local`: `VITE_DEV_BYPASS_AUTH=true` skips Clerk locally.

## Manual deploy (optional)

If you need a one-off upload without Git:

```bash
make deploy-frontend   # requires wrangler login or CLOUDFLARE_API_TOKEN
```

Git-connected Pages is the preferred path for production.
