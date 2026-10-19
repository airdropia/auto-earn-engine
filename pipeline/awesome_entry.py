#!/usr/bin/env python3
"""Place a curated-list entry where a maintainer will actually accept it.

The first version of the discovery workflow appended the entry to the end of
the target's README. That is wrong in three separate ways, and each one is
enough for a maintainer to close the PR:

  - many curated lists keep their content in per-topic files (awesome-svg
    uses topics/*.md) and the root README is only a table of contents, so an
    appended line never appears in the list at all;
  - the end of a README is usually the License section, so the line reads as
    spam pasted below the footer;
  - the list is usually sorted, and the right section is usually obvious.

So: find the file that actually holds the entries, find the section whose
subject matches, match the list's own bullet style and separator, and insert
alphabetically inside that section.

Usage:
  awesome_entry.py <repo-dir> <entry-line> [name]

<entry-line> is the fully rendered markdown line. <name> is the sort key
(defaults to the bracketed label in the entry).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Section names that fit a tool which generates layered SVG cut files.
SECTION_HINTS = [
    "software", "tools", "tool", "svg", "graphics", "image", "design",
    "graphics & design", "maker", "maker tools", "craft", "crafts",
    "diy", "3d", "3d printing", "generative", "art", "creative",
    "illustrations", "vector", "cad", "editors",
]

# Chinese section names for the same idea.
SECTION_HINTS_ZH = [
    "软件", "工具", "建模", "cad", "3d 建模", "绘图", "素材", "设计",
]


def is_bullet(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^(\*\s+|-(\s{1,3}))\S", s))


def sort_key(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^(\*\s+|-(\s{1,3}))", "", s)
    s = s.lstrip("[")
    return s.lower()


def strip_label(line: str) -> str:
    m = re.match(r"^\s*(?:\*\s+|-(\s{1,3}))\[([^\]]+)\]", line)
    return m.group(2) if m else ""


def find_entry_files(repo: Path) -> list[Path]:
    """Files that plausibly hold list entries.

    A README whose body is only a table of contents pointing at topics/*.md
    means the entries live in those files instead.
    """
    readme = None
    for cand in ("README.md", "Readme.md", "readme.md", "README.MD"):
        p = repo / cand
        if p.exists():
            readme = p
            break
    if readme is None:
        return []

    text = readme.read_text(encoding="utf-8", errors="replace")
    bullets = [l for l in text.splitlines() if is_bullet(l)]
    topic_links = re.findall(r"\]\((?:\./)?topics/([A-Za-z0-9\-_]+\.md)\)", text)

    files = [readme]
    if topic_links:
        topics_dir = readme.parent / "topics"
        for name in topic_links:
            tp = topics_dir / name
            if tp.exists():
                files.append(tp)
    # A README with no entries at all and no topic links is not the right file.
    if not bullets and not topic_links:
        files = []
    return files


def score_file(path: Path) -> int:
    """How likely this file is to be the right home for the entry."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return -1
    score = 0
    for hint in SECTION_HINTS + SECTION_HINTS_ZH:
        if f"## {hint}" in text or f"### {hint}" in text:
            score += 3
    if re.search(r"^#+\s*(svg|software|tools)", text, re.M):
        score += 2
    if "svg" in path.name.lower():
        score += 2
    if "softwar" in path.name.lower() or "tool" in path.name.lower():
        score += 2
    bullets = sum(1 for l in text.splitlines() if is_bullet(l))
    score += min(bullets // 8, 4)
    return score


def detect_style(text: str) -> tuple[str, int, str]:
    """Return (bullet, pad, separator) as the list itself uses them."""
    for line in text.splitlines():
        if not is_bullet(line):
            continue
        m = re.match(r"^(\*|-)(\s+)(\[.*)", line)
        if not m:
            continue
        bullet = m.group(1)
        pad = len(m.group(2))
        sep = " - "
        after = line[m.end(0):] if False else line
        sm = re.search(r"\]\s*([-–—:]\s)", line)
        if sm:
            sep = sm.group(1)
        return bullet, pad, sep
    return "*", 1, " - "


def collect_sections(lines: list[str]) -> list[tuple[int, int, int, str]]:
    """Headings with their bullet block: (heading index, block start, block end, heading)."""
    out = []
    for i, line in enumerate(lines):
        if not line.strip().startswith("#"):
            continue
        start = i + 1
        while start < len(lines) and lines[start].strip().startswith(">"):
            start += 1
        while start < len(lines) and lines[start].strip() == "":
            start += 1
        end = start
        while end < len(lines) and is_bullet(lines[end]):
            end += 1
        out.append((i, start, end, line.strip()))
    return out


def insert_into(path: Path, entry: str, name: str) -> tuple[int, str]:
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    sections = collect_sections(lines)

    # Rank the headings that actually hold a bullet list. A heading whose
    # block is empty is followed by prose, and inserting there put the entry
    # in the middle of a paragraph - which is how a PR looks like spam.
    ranked = []
    for (h, s, e, title) in sections:
        if e == s:
            continue
        low = title.lower()
        score = 0
        for hint in SECTION_HINTS + SECTION_HINTS_ZH:
            if hint in low:
                score += len(hint)
        ranked.append((score, e - s, h, s, e))
    ranked.sort(key=lambda t: (-t[0], -t[1]))

    if ranked:
        _score, _n, _h, start, end = ranked[0]
        where = "section, alphabetical"
    else:
        # No heading with bullets anywhere: use the file's last bullet block.
        start, end = 0, len(lines)
        last = -1
        for i, l in enumerate(lines):
            if is_bullet(l):
                last = i
        if last < 0:
            lines.append("")
            lines.append(entry)
            path.write_text("\n".join(lines), encoding="utf-8")
            return len(lines), "appended (no bullets in file)"
        start, end = 0, last + 1
        where = "file bullets, appended"

    target = name.lower()
    for i in range(start, end):
        if sort_key(lines[i]) > target:
            lines.insert(i, entry)
            path.write_text("\n".join(lines), encoding="utf-8")
            return i + 1, where

    lines.insert(end, entry)
    path.write_text("\n".join(lines), encoding="utf-8")
    return end + 1, where + ", appended"


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    repo = Path(sys.argv[1])
    entry = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else strip_label(entry) or "VectorForge Daily"

    files = find_entry_files(repo)
    if not files:
        print("no entry-bearing file found")
        return 1

    ranked = sorted(files, key=lambda p: score_file(p), reverse=True)
    target = ranked[0]
    text = target.read_text(encoding="utf-8", errors="replace")

    # Re-render the entry in the list's own style if it differs.
    bullet, pad, sep = detect_style(text)
    rendered = entry
    m = re.match(r"^(\*|-)(\s*)(\[.*)$", entry, re.S)
    if m:
        rendered = f"{bullet}{' ' * pad}{m.group(3)}"
        # normalise the separator between the label and the description
        rendered = re.sub(r"(\])\s*[-–—:]\s*", lambda mm: mm.group(1) + sep, rendered, count=1)

    # Remove any previous copy of this entry first.
    if name in text:
        kept = [l for l in text.split("\n") if name not in l]
        target.write_text("\n".join(kept), encoding="utf-8")
        text = "\n".join(kept)

    line_no, where = insert_into(target, rendered, name)
    print(f"entry placed in {target.name} at line {line_no} ({where})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
