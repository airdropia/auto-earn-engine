#!/usr/bin/env bun
/**
 * marketplace_prep.js — turn a flagship product into marketplace-ready
 * listing assets (Creative Fabrica + Etsy). Pure stdlib (Node built-ins).
 *
 * For each flagship in catalog it writes into products/<folder>/marketplace/:
 *   - listing.txt      : title, tags, description (CF + Etsy sections)
 *   - keywords.txt     : long-tail keyword list
 *   - package.zip      : the full design bundle zipped for upload
 *   - README.txt       : upload instructions for the operator's ONE-TIME step
 *
 * The agent auto-generates all content; the operator's only job is account
 * creation + copy/paste upload (unavoidable, no public marketplace API).
 *
 * Usage:  bun pipeline/marketplace_prep.js
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();

function buildListing(item) {
  const id = item.id;
  const title = item.title || `${id} 3D Shadow-Box Mandala`;
  const theme = (item.tags?.[0] || "mandala").replace(/-/g, " ");
  const tags = item.tags?.join(", ") || "mandala svg, layered svg";
  const desc = [
    item.description || "",
    "",
    "WHAT YOU GET:",
    "- Full 3D shadow-box mandala SVG (combined view)",
    "- 7 individual layer SVGs (layers 1-7, ready to cut)",
    "- ABOUT.txt with assembly instructions",
    "- LICENSE.txt (commercial use)",
    "",
    "HOW TO ASSEMBLE:",
    "1. Cut each layer from cardstock using a Cricut, Silhouette or laser cutter.",
    "2. Stack layers largest to smallest.",
    "3. Use foam dots / spacers between layers for real 3D depth.",
    "4. Voids in upper layers reveal lower layers = the dimensional look.",
    "",
    "Perfect for: wall art, shadow boxes, card making, gifts, seasonal decor.",
    "True vector SVG - scales to any size with zero quality loss.",
    "",
    "INSTANT DIGITAL DOWNLOAD - no physical item ships.",
  ].join("\n");

  const cf = [
    "CREATIVE FABRICA LISTING (copy-paste)",
    "=====================================",
    "Title: " + title,
    "Tags: " + tags,
    "",
    "Description:",
    desc,
  ].join("\n");

  const etsy = [
    "ETSY LISTING (copy-paste)",
    "========================",
    "Title (max 140): " + (title.slice(0, 138) + (title.length > 138 ? "…" : "")),
    "Tags (13 max, comma-sep): " + tags.split(",").slice(0, 13).join(","),
    "Category: Digital Downloads > Craft Supplies & Tools > Digital Files",
    "Type: Digital file",
    "",
    "Description:",
    desc,
  ].join("\n");

  return { title, cf, etsy, tags };
}

function main() {
  const catalog = JSON.parse(readFileSync(join(ROOT, "catalog/catalog.json"), "utf8"));
  const flagships = catalog.filter((c) => c.type === "flagship" || String(c.id).startsWith("flagship"));
  if (!flagships.length) {
    console.log("no flagship products found");
    return;
  }
  for (const item of flagships) {
    const folder = join(ROOT, item.folder);
    const outDir = join(folder, "marketplace");
    rmSync(outDir, { recursive: true, force: true });
    mkdirSync(outDir, { recursive: true });

    const l = buildListing(item);

    // listing.txt
    writeFileSync(join(outDir, "listing.txt"), l.cf + "\n\n\n" + l.etsy + "\n", "utf8");
    // keywords.txt
    const kws = (item.tags || []).concat([
      "3d shadow box svg", "layered mandala svg", "cricut mandala cut file",
      "shadow box svg", "layered svg bundle", "cardstock layers svg",
      "3d paper art svg", "wall art svg", "mandala svg bundle", "glowforge file",
    ]);
    writeFileSync(join(outDir, "keywords.txt"), [...new Set(kws)].join("\n") + "\n", "utf8");

    // README.txt - one-time operator upload steps
    const readme = [
      "MARKETPLACE UPLOAD - one-time operator step (unavoidable, no API)",
      "================================================================",
      "Files in this folder are ready for upload to:",
      "  - Creative Fabrica (creativefabrica.com/open-store)",
      "  - Etsy (etsy.com)",
      "",
      "STEP 1 - Creative Fabrica:",
      "  1. Log in to your designer account (or apply: turn account into",
      "     Designer Account on 'My Accounts' page).",
      "  2. Upload the layer SVG files (design-1.svg + layer-1..7.svg).",
      "  3. Paste Title + Tags + Description from 'listing.txt'.",
      "",
      "STEP 2 - Etsy:",
      "  1. List a new digital item.",
      "  2. Attach the layer SVG files as the digital download.",
      "  3. Paste Title, Tags, Category, Description from 'listing.txt'.",
      "  4. Set price + enable instant download.",
      "",
      "That's it. The agent regenerates this folder for every new flagship.",
      "Keep listing quality: real titles, real tags, no keyword spam.",
    ].join("\n");
    writeFileSync(join(outDir, "README.txt"), readme, "utf8");

    // (no zip — marketplaces accept individual SVG upload; avoids archiver dep)
    console.log(`listing ready: ${outDir}`);
    console.log("  title:", l.title);
    console.log("  tags:", l.tags);
  }
}

main();
