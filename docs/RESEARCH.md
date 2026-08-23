# RESEARCH - Authentic Analysis

Date: 2026-02-14. Constraint set: $0 budget, zero recurring user input,
no paid services, minimal local PC usage. Note: live web verification was
unavailable in this session; fee figures below come from prior knowledge
and MUST be re-verified on the official pricing pages before being relied
on for business decisions (links included).

## Why digital products + GitHub infra

Hard constraints eliminate almost every "auto earning" idea:

| Rejected path | Reason |
| --- | --- |
| Crypto mining on Actions | Violates GitHub ToS, account ban risk |
| Bandwidth-sharing apps | Uses local PC constantly, pennies/month |
| Search/rewards bots | Platform ToS violations |
| Paid AI content APIs | Costs money |
| Trading bots | Needs capital, real financial risk |

What survives: **procedurally generated digital assets** (SVG vector art)
published on **free hosting**, monetized through **free-to-join platforms**.
Proven demand exists for SVG bundles (Cricut/craft/laser niche is a large,
persistent Etsy category), printables, and social media templates.

## Infrastructure cost: $0 confirmed

- GitHub Actions: public repositories get unlimited standard minutes;
  private repos only get 2,000 min/month free tier. => repo must be PUBLIC.
- GitHub Pages: free for public repositories.
- Job wall-clock limit (6h) and cron delay (typically up to ~15-30 min) are
  acceptable for twice-daily batches.
- Runtime deps of pipeline: Python stdlib only -> no install step, fast jobs.

## Revenue paths (in activation order)

1. **Tips (Ko-fi)** - 0% platform fee on tips per Ko-fi pricing page
   (verify: https://ko-fi.com/pricing). Activation: paste URL in config.
2. **GitHub Sponsors** - 0% platform fee, payment processor fees apply
   (verify: https://docs.github.com/en/sponsors). Payout via Stripe.
3. **Paid listings - Gumroad** - historically ~10% flat fee era changed;
   verify current fee at https://gumroad.com/pricing. Has an API usable
   with a token stored as repo secret. PWYW (pay-what-you-want) fits:
   keep files free here, let fans pay.
4. **Payhip** - free plan, ~5% transaction fee (verify:
   https://payhip.com/pricing). Good Gumroad alternative.
5. **Etsy** (later, manual-assisted) - $0.20 listing fee + ~6.5% transaction
   (verify). Highest buyer intent for SVG/printables but requires manual
   shop work; out of scope for full automation.

## Honest expectations

- Month 1 without promotion: near-zero traffic (GitHub Pages has weak SEO
  initially). This is normal and documented - not a system failure.
- The catalog compounds: ~8 new product listings/week become hundreds of
  indexed pages within months. Long-tail search traffic is the engine.
- Realistic first-dollar timeline after payout hookup: weeks, not days.
  Anyone promising instant automated income at $0 cost is selling hope.

## Growth levers (still $0)

- dev.to articles auto-published linking to storefront (needs one API key).
- Pinterest pins of quote cards (manual or future automation phase).
- Product count scaling: cron frequency is trivially adjustable in
  `production.yml`.
- Niche focus: mandala/Cricut keywords have stable commercial search volume.

## Risks / mitigations

| Risk | Mitigation |
| --- | --- |
| Public repo = anyone copies assets | Volume + velocity game; originals carry generation provenance in git history |
| Cron delays/skips (GitHub warns crons may be delayed) | workflow_dispatch manual trigger available; two daily slots |
| Platform fee changes | Multi-platform config, swap links in config.json only |
| GitHub disables Pages for inactivity | Weekly metrics commit keeps repo active |
