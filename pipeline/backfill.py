#!/usr/bin/env python3
"""One-shot backfill: rebuild every historical catalog batch with the v2
quality generators.

Possible because generation is deterministic per UTC date - same seeds,
same slugs and ids, upgraded content and packaging. Catalog entries are
replaced in place; nothing is duplicated.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from generate_products import (  # noqa: F401  (module-level constants reused)
    BUILDERS,
    CATALOG_DIR,
    CATALOG_PATH,
    PRODUCTS_DIR,
    ROOT,
    build_product,
)

TYPES = ("mandala", "patterns", "quotes", "planner")


def main() -> None:
    catalog: list[dict] = []
    if not CATALOG_PATH.exists():
        print("no catalog found")
        return
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    dates = sorted({item["created"] for item in catalog})
    print(f"backfilling {len(dates)} date(s): {dates}")

    by_id = {item["id"]: item for item in catalog}
    rebuilt = 0
    for date in dates:
        rng = random.Random(f"auto-earn-engine:{date}")
        batch_dir = PRODUCTS_DIR / date
        batch_dir.mkdir(parents=True, exist_ok=True)
        for product_type in TYPES:
            item = build_product(product_type, rng, batch_dir, date)
            if item["id"] in by_id:
                by_id[item["id"]] = item
                rebuilt += 1

    CATALOG_PATH.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"rebuilt={rebuilt} catalog_total={len(catalog)}")


if __name__ == "__main__":
    main()
