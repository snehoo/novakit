#!/usr/bin/env python3
"""
Quick fix: AI-citability checkers often read plain <meta> tags rather than
JSON-LD, so the "Author identified" / "Publication date" / "Content
freshness" checks kept failing on bundle pages even after datePublished and
author were added to the Product JSON-LD (add_citability_bundles_v2.py).

Adds <meta name="author">, <meta property="article:published_time">, and
<meta property="article:modified_time"> to <head> on all skills/bundles/*.html.
No visible UI change — dates stay out of the page body per earlier decision.

Idempotent: skips files that already have a name="author" meta tag.
Run: python3 fix_bundle_meta_dates.py [--dry-run] [files...]
"""
import re
import sys
import glob

DATE_PUBLISHED = "2026-01-20"
DATE_MODIFIED = "2026-06-24"


def process_file(path, dry_run=False):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if 'name="author"' in content:
        return "skip (already has author meta)"

    m = re.search(r'(<meta property="og:type"[^>]*>)', content)
    if not m:
        return "skip (no og:type meta found)"

    insert = (
        '<meta name="author" content="NovaKit">'
        f'<meta property="article:published_time" content="{DATE_PUBLISHED}">'
        f'<meta property="article:modified_time" content="{DATE_MODIFIED}">'
    )
    new_content = content[: m.end()] + insert + content[m.end():]

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return "updated"


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    files = args if args else sorted(glob.glob("skills/bundles/*.html"))

    for path in files:
        result = process_file(path, dry_run=dry_run)
        print(f"{path}: {result}")


if __name__ == "__main__":
    main()
