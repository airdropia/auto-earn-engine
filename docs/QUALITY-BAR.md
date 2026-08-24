# QUALITY BAR - Product Standard Checklist

Every product must pass this bar BEFORE it reaches the storefront.
Enforced automatically by `pipeline/quality_gate.py` in CI; the generator
also pre-filters candidates so weak output never enters the catalog.

## Hard gates (CI fails if violated)

1. **Well-formed SVG** - parses as valid XML, single `<svg>` root,
   xmlns present.
2. **Closed geometry for cut files** - every `<path>` in mandala bundles
   ends with `Z` (closed contour). Cricut/laser tools require closed
   paths; open strokes waste material and break offsets.
3. **Complexity floor** - minimum element counts per type:
   - Mandala bundle: >= 120 elements total across the set
   - Pattern board: >= 6 distinct pattern defs
   - Quote card set: >= 4 cards, each with kicker + body + rule elements
   - Planner sheet: full grid present (>= 40 grid lines)
4. **Contrast floor** - primary ink vs background luminance delta >= 0.35
   (checked by construction: generators pick the darkest palette members).
5. **Font safety** - only universal font stacks (Georgia/Times serif,
   Arial/Helvetica sans). No exotic font dependencies.
6. **Package completeness** - every bundle folder contains the asset files
   PLUS `ABOUT.txt` and `LICENSE.txt`. A ZIP without paperwork is an
   incomplete product.

## Soft standards (generator design goals)

- Rotational-symmetry composition for mandalas (true kaleidoscopic layering,
  not random rings)
- Colorways drawn from curated palettes only; never raw defaults
- Generous margins and print-safe zones on printable sheets (A4/Letter)
- Consistent naming: `{type}-{hash}-{n}.svg` everywhere

## Volume policy

Speed stays: the cron still runs twice daily. The generator produces
multiple candidates per slot and ships only gate-passers, so published
volume holds while junk is filtered at source.
