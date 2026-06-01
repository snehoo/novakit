#!/usr/bin/env python3
"""
add_tracker.py
Adds <script src="/novakit-tracker.js" data-skill="SLUG" defer></script>
to every HTML file in /skills/ and /skills/bundles/.

- Derives the slug from the filename (strips .html)
- Skips files that already have the tracker
- Adds the tag just before </body>
- Also adds the tracker (without data-skill) to index.html
"""

import os
import re
from pathlib import Path

SITE_ROOT = Path("/Users/snehoomac/snehoo/AI/novakit/NovaKitwebsite")
SKILLS_DIR = SITE_ROOT / "skills"
BUNDLES_DIR = SKILLS_DIR / "bundles"
INDEX_FILE = SITE_ROOT / "index.html"

TRACKER_SRC = "/novakit-tracker.js"
MARKER = "novakit-tracker.js"  # used to detect if already added


def make_tag(slug=None):
    if slug:
        return f'<script src="{TRACKER_SRC}" data-skill="{slug}" defer></script>'
    return f'<script src="{TRACKER_SRC}" defer></script>'


def inject(filepath, slug=None):
    content = filepath.read_text(encoding="utf-8")

    if MARKER in content:
        print(f"  SKIP (already has tracker): {filepath.name}")
        return

    tag = make_tag(slug)
    if "</body>" in content:
        new_content = content.replace("</body>", f"  {tag}\n</body>", 1)
    else:
        # No </body> — append at end of file
        new_content = content + f"\n{tag}\n"

    filepath.write_text(new_content, encoding="utf-8")
    print(f"  OK: {filepath.name}  →  slug={slug or '(none)'}")


def process_dir(directory, is_bundle=False):
    html_files = sorted(directory.glob("*.html"))
    if not html_files:
        print(f"  No HTML files found in {directory}")
        return

    for f in html_files:
        slug = f.stem  # filename without .html
        inject(f, slug=slug)


print("=" * 55)
print("NovaKit tracker injector")
print("=" * 55)

# 1. index.html — no slug
print("\n[index.html]")
if INDEX_FILE.exists():
    inject(INDEX_FILE, slug=None)
else:
    print("  NOT FOUND — skipping")

# 2. /skills/*.html
print(f"\n[skills/]")
process_dir(SKILLS_DIR)

# 3. /skills/bundles/*.html
print(f"\n[skills/bundles/]")
process_dir(BUNDLES_DIR)

print("\nDone.")
