# VectorForge Daily

Original layered SVG cut files for paper crafters and laser cutters — built by
an automated design pipeline, sold with USDT, no account required.

**Storefront (buy with USDT):** https://airdropia.github.io/auto-earn-engine/
**Crypto checkout:** https://airdropia.github.io/auto-earn-engine/checkout/

## What these files are

Each flagship is a 3D shadow-box mandala built from **7 physical layers**. Voids
in the upper layers reveal the layers beneath, which is what creates the depth
when the pieces are stacked. Every bundle ships:

- the combined SVG
- one SVG per layer, named in cut order
- a 6500px print-ready PNG render (vector-lossless, no quality loss)

Formats open in Cricut Design Space, Silhouette Studio, Inkscape, Illustrator
and most laser software. All shapes are real vector paths — nothing traced.

## Browse by type

| Collection | What it is |
|---|---|
| [Shadow Box SVG Files](https://airdropia.github.io/auto-earn-engine/c/shadow-box-svg/) | Layered designs built for physical depth |
| [Cricut Mandala SVG Templates](https://airdropia.github.io/auto-earn-engine/c/cricut-mandala-svg/) | Opens directly in Cricut Design Space |
| [Layered SVG Bundles](https://airdropia.github.io/auto-earn-engine/c/layered-svg-bundle/) | One file per layer plus a combined design |
| [Silhouette Cut Files](https://airdropia.github.io/auto-earn-engine/c/silhouette-cut-files/) | Grouped and named per layer for Silhouette Studio |
| [Mandala SVG Designs](https://airdropia.github.io/auto-earn-engine/c/mandala-svg/) | Original radial geometry as vector |
| [3D Layered Art Templates](https://airdropia.github.io/auto-earn-engine/c/3d-layered-art/) | Multi-sheet templates for depth |

## Licensing

Free for personal and commercial use — physical products, client work, printed
goods. Please do not resell or redistribute the raw digital files as-is.

## The generator (open source)

The design pipeline in `pipeline/` is the software behind this storefront, and
it is MIT-licensed (see `LICENSE`):

- `flagship_generator.py` — designs a new 7-layer shadow-box mandala per UTC
  day (idempotent: the slug derives from the date, existing days are skipped)
- `svgkit.py` — dependency-free SVG geometry helpers used by every design
- `quality_gate.py` — floor checks (layer counts, palette, path sanity)
- `build_site.py` — renders the static storefront, collections and checkout

Requirements: **Python 3.10+, standard library only — no pip installs.**

```bash
python3 pipeline/flagship_generator.py     # design today's flagship
python3 pipeline/quality_gate.py           # verify generated output
python3 pipeline/build_site.py             # render the static site
```

Everything above also runs unattended on scheduled GitHub Actions; see
`.github/workflows/`.

## How this is built

The storefront and every asset here are produced by a scheduled pipeline that
runs entirely in GitHub Actions. Design generation, rendering, packaging and
deployment are automated; no manual step sits between the generator and a live
listing. Payments are confirmed on-chain, so buying needs no account.

The repository ships both the MIT-licensed generator source and its generated
artifacts. See `LICENSE`: the code is MIT; design assets keep their own
commercial-use grant.
