# SETUP - One-Time Activation (5 minutes, browser only)

The system is operational from the first successful CI run: it generates
products and publishes a live storefront with zero configuration. The steps
below only connect the money. Every step can be done in a web browser - no
local machine work is needed.

## 0. Nothing required on day one

No secrets are needed for generation or publishing. The pipeline uses only:
- GitHub Actions free minutes (public repositories: unlimited)
- GitHub Pages free hosting

## 1. Connect a payout destination (pick any, all free)

### Option A - Ko-fi (fastest, 0% platform fee on tips)
1. Create account at https://ko-fi.com
2. Copy your page URL, e.g. `https://ko-fi.com/yourname`
3. Edit `config.json` in this repo (GitHub web UI: pencil icon)
4. Set `"kofi_url": "https://ko-fi.com/yourname"`
5. Commit. Next storefront build shows the support box automatically.

### Option B - GitHub Sponsors
1. Join at https://github.com/sponsors (requires payout setup with Stripe)
2. Put your profile URL in `config.json` -> `"github_sponsors_url"`

### Option D - Patreon + Payoneer (recommended for Pakistan)
PayPal and Stripe are not available in Pakistan, so Ko-fi/Gumroad direct
payouts fail there. The working free combo is:

1. **Payoneer** (free account, acts like the payout wallet):
   sign up at https://www.payoneer.com - requires CNIC and a phone number.
2. **Patreon** (free creator page): sign up at https://www.patreon.com,
   create a creator page for your design studio.
3. In Patreon: Settings -> Payouts -> connect Payoneer.
4. Copy your Patreon page URL into `config.json` -> `"patreon_url"`.
   The storefront support box activates automatically on next build.

Verify current Patreon payout country support on
https://support.patreon.com before relying on it.

### Option C - Paid product listings (Gumroad / Payhip)
1. Create a free Gumroad or Payhip account
2. Optional automation token: repo Settings -> Secrets and variables ->
   Actions -> New repository secret -> name `GUMROAD_ACCESS_TOKEN`
3. Add your store URL to `config.json` -> `"affiliate_html"` (any HTML,
   e.g. a styled link/button) and it renders on every storefront page.

## 2. Verify the pipeline

- Actions tab -> `production` workflow -> run history should show green runs
- Latest run -> deploy job -> URL is your live storefront
- `metrics/metrics.json` updates every Monday via the `metrics` workflow

## 3. Optional secrets (none required today)

| Secret | Purpose |
| --- | --- |
| `GUMROAD_ACCESS_TOKEN` | Future auto-listing of products to Gumroad |
| `DEVTO_API_KEY` | Future auto-publishing of articles that link back to the storefront |

Missing a secret does not block anything; features activate when present.
