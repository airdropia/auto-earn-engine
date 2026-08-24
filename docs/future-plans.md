# FUTURE PLANS - Auto-Earning Network

This document records how the Auto-Earn Engine was built, exactly which
tools and paths made it live, how monetization was attached, and where the
network goes next.

---

## PART 1 - THE GOAL

Original mission (as given):

> Build an operational auto-earning system with:
> - $0 cost
> - zero recurring user input
> - no paid services
> - minimum local PC usage

Everything below happened inside those constraints. Nothing paid, nothing
manual, no local machine load.

---

## PART 2 - RESEARCH AND ANALYSIS

### Constraint elimination

Every popular "auto earning" idea was tested against the constraints and
rejected on evidence:

| Rejected path | Why it failed the test |
| --- | --- |
| Crypto mining on CI runners | Violates GitHub ToS - account ban risk |
| Bandwidth-sharing apps | Needs local PC running constantly |
| Search/rewards bots | Platform ToS violations |
| Paid AI content APIs | Costs money |
| Trading bots | Needs capital, real financial risk |

### What survived

Procedurally generated digital assets (SVG vector art) published on free
hosting, monetized through free-to-join platforms:

- Proven market: Cricut/laser craft niche buys SVG bundles continuously
- GitHub public repos: unlimited Actions minutes, free Pages hosting
- Python stdlib-only pipeline: zero dependency installs, fast jobs
- Deterministic generation keyed by UTC date: unique daily batches that
  stay reproducible

### Live fee verification

Platform fees were verified against official pricing pages using the
Jina Search API (free key):

- Gumroad: 10% + 50c per direct sale, 30% via Discover, $0 monthly
- Payhip: Free Forever plan, $0/month, unlimited products
- Ko-fi: free to join, 0% fee on tips
- Patreon: multi-currency payouts documented for non-US creators

Sources are cited in `docs/RESEARCH.md`.

---

## PART 3 - TOOLS AND METHODS USED

| Tool | Role |
| --- | --- |
| GitHub Actions cron (`production.yml`) | Runs the factory twice daily, unattended |
| GitHub Pages (`deploy-pages`) | Free global hosting for the storefront |
| Python 3 stdlib only | Product generation, site build, PNG writer, zipping - no pip installs anywhere |
| Git + GitHub REST API | All pushes done via API (Contents API first commit, then blob/tree updates) - local git credentials never needed |
| `gh` CLI | Repo creation, workflow dispatch, run watching, deployment verification |
| Jina Search API (`s.jina.ai`, free key) | Live verification of platform fees and payout rules |
| Node.js runtime fetch | Network diagnostics when Windows TLS (schannel) blocked curl inside the sandbox |
| Ko-fi / Patreon / Trust Wallet | Payout rails - all free to join |

Notable engineering decisions:

1. Idempotent generation - re-running the same date never duplicates
   catalog entries (dedupe by product id).
2. `[skip ci]` on bot commits - prevents infinite workflow loops.
3. Two-job workflow (produce -> deploy) so artifact upload always ships
   the committed state.
4. Config-driven monetization - every revenue slot reads `config.json`,
   so swapping platforms means editing one JSON field, not code.

---

## PART 4 - HOW IT WENT LIVE

```
schedule (2x daily UTC cron)
    |
    v
generate_products.py     deterministic per-date seed -> mandala bundles,
                         seamless patterns, quote cards, habit trackers
    |
    v
build_site.py            zips each bundle -> renders dark storefront,
                         OG image, monetization box from config.json
    |
    v
git commit               full audit trail of every asset ever generated
    |
    v
GitHub Pages deploy      https://airdropia.github.io/auto-earn-engine/
```

Second workflow (`metrics.yml`) snapshots catalog size and repository
traffic weekly into `metrics/metrics.json`.

One-time manual steps that were required (all browser-based):

1. Enable GitHub Pages once (GITHUB_TOKEN cannot self-enable it):
   `POST /repos/{owner}/{repo}/pages {"build_type":"workflow"}`
2. Operator accounts: Payoneer (payout wallet, CNIC-based), Patreon
   creator page linked to Payoneer, Trust Wallet for USDT (BEP20) tips

---

## PART 5 - MONETIZATION INTEGRATION

All revenue slots live in one file - `config.json`:

```json
{
  "patreon_url": "https://www.patreon.com/cw/VectorForgeDaily",
  "crypto_address": "0x...",
  "crypto_network": "USDT (BEP20)"
}
```

- `build_site.py` renders the "Support this machine" box automatically
  whenever a slot is non-empty; empty slots render as dormant placeholders
- The crypto box shows the address with a Copy button plus a wrong-network
  warning (send only the labeled asset)
- Slots already coded and waiting for future use: `kofi_url`,
  `github_sponsors_url`, `affiliate_html`

Pakistan-specific payout reality that shaped this design:

- PayPal and Stripe are unavailable in PK, ruling out Ko-fi/Gumroad direct
  payouts
- Working combo: Patreon -> Payoneer (CNIC signup) -> local bank
- Crypto tips work wallet-to-wallet without any platform, converted to
  PKR later at the operator's own risk (grey-zone awareness documented)

---

## PART 6 - CURRENT STATUS SNAPSHOT

- Storefront live, 8+ products and growing ~4/day
- Scheduled runs green without any human involvement
- Catalog compounds: hundreds of indexed pages within months
- Revenue expected to start near zero - growth lever is time + catalog
  depth, not luck

---

## PART 7 - EXPANSION BLUEPRINT (same skeleton, new repos)

Every new property reuses the same recipe - roughly one evening of work:

1. Create repo from this one as template (or copy `pipeline/` +
   `.github/workflows/`)
2. Swap the generator module for the new property's output type
3. Point `config.json` at the SAME Patreon + crypto values - one identity,
   many properties
4. Push -> CI goes green -> Pages live
5. Cross-link footers between all properties (network ring - each site
   advertises the others)

A future "hub" page can list the whole network in one place.

Rules that keep the network safe:

- Never automate platform signups or spam external sites
- Keep everything original-generated (same license stance as here)
- One repo per property - blast-radius isolation if anything breaks

---

## PART 8 - FIVE NEXT IDEAS (attention + micro-problem solvers)

### 1. MicroTools Hub - "No signup. No tracking. Works offline."

A single-page browser toolbox: invoice generator, QR generator, strong
password maker, word counter, text case converter. Pure client-side JS -
nothing leaves the visitor's device, which is itself the marketing line.

- Why it attracts: evergreen search demand for these tools is enormous
- Build: static HTML/JS, zero backend, Actions only deploys
- Effort: medium (once), then frozen forever

### 2. Prayer Times PK + Islamic Tools

Accurate prayer times for Pakistani cities computed astronomically
offline (standard solar formulas - no API, no cost), plus Hijri date
converter and Qibla direction. Optional Urdu interface.

- Why it attracts: daily-use audience with extreme loyalty and sharing
  habits; massively underserved by clean ad-light pages
- Build: math-heavy but well-documented algorithms, fully static
- Effort: medium-high once; zero after

### 3. Wallpaper of the Day

Reuses the existing generative engine - new daily wallpaper batch with a
gallery, preview sizes for phone/desktop, free download.

- Why it attracts: visual content gets shared; every share is a backlink
- Build: mostly done already - new renderer module + gallery layout
- Effort: low - closest to launch

### 4. Name & Idea Arcade

Generators for startup names, gamertags, band names, pet names, story
character names. Combinatorial word-blending with quality filters.

- Why it attracts: fun, instantly usable, endlessly shareable; people
  bookmark and return
- Build: word lists + blend logic, purely static
- Effort: low-medium

### 5. Free Services Watchdog

Actions pings a curated list of popular free services hourly, publishes
uptime history as SVG charts: "is X down right now?"

- Why it attracts: everyone hits "is it down or is it me?" moments;
  honest independent status pages earn trust links
- Build: curl checks in Actions -> JSON -> static chart render
- Effort: medium

### Priority order

Wallpaper of the Day (lowest effort, engine exists) -> MicroTools Hub ->
Prayer Times PK -> Name Arcade -> Watchdog.

Each launches with the same Patreon + USDT tip box, feeds the same
identity, and cross-links the whole ring - presence spreads from one site
to a network.
