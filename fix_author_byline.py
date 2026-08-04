#!/usr/bin/env python3
"""
fix_author_byline.py — Update visible author byline on all blog posts.

Changes:
  author-av   : "NK"                  → "SP"
  author-name : "NovaKit"             → "Snehal Patel"
  author-role : "Claude Skill Research" → "Founder, NovaKit"

Invisible-layer change? No — this is visible to readers, approved by user.

Usage:
  python3 fix_author_byline.py [--dry-run]
"""

import shutil
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

BLOG_DIR = Path(__file__).parent / "blog"
DRY_RUN = "--dry-run" in sys.argv

REPLACEMENTS = {
    "author-av":   ("NK",                    "SP"),
    "author-name": ("NovaKit",               "Snehal Patel"),
    "author-role": ("Claude Skill Research", "Founder, NovaKit"),
}


def patch_file(path: Path) -> bool:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    changed = False

    for css_class, (old, new) in REPLACEMENTS.items():
        el = soup.find(class_=css_class)
        if not el:
            continue

        # author-name wraps an <a> tag — update the link text, keep href
        if css_class == "author-name":
            a = el.find("a")
            if a and a.get_text(strip=True) == old:
                a.string = new
                changed = True
        else:
            if el.get_text(strip=True) == old:
                el.string = new
                changed = True

    if changed and not DRY_RUN:
        bak = path.with_suffix(".html.bak")
        if not bak.exists():
            shutil.copy2(path, bak)
        path.write_text(str(soup), encoding="utf-8")

    return changed


def main():
    files = sorted(BLOG_DIR.glob("*.html"))
    patched = 0
    skipped = 0

    for path in files:
        if path.name == "index.html":
            continue
        changed = patch_file(path)
        if changed:
            patched += 1
            print(f"  {'[DRY] ' if DRY_RUN else ''}✓ {path.name}")
        else:
            skipped += 1

    print(f"\n{'DRY RUN — ' if DRY_RUN else ''}Done: {patched} updated, {skipped} already correct / no byline")


if __name__ == "__main__":
    main()
