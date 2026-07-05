#!/usr/bin/env python3
"""
update_social_seo_batch.py
──────────────────────────
Adds YouTube + Instagram social links and AI-citability meta tags
to all NovaKit skill pages (skills/*.html) and bundle pages
(skills/bundles/*.html).

What it changes in every file
──────────────────────────────
1. <head> — inserts social + AI-citability meta block (idempotent; skipped
   if already present, detected by the marker comment <!-- novakit-social-v1 -->)
2. sameAs — if an ld+json Organization block exists, populates sameAs with
   the two social URLs (skipped if already present)
3. <footer> — appends the social icon row (idempotent; skipped if already
   present, detected by class="footer-social")
4. dateModified in ld+json — bumped to today's date

Run from any directory:
    python3 /path/to/update_social_seo_batch.py

Dry-run (show what would change, write nothing):
    python3 update_social_seo_batch.py --dry-run

Target a single file for testing:
    python3 update_social_seo_batch.py --file skills/cold-outreach-email.html
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Tuple

# ── Configuration ─────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent.resolve()
SKILLS_GLOB  = str(SCRIPT_DIR / "skills" / "*.html")
BUNDLES_GLOB = str(SCRIPT_DIR / "skills" / "bundles" / "*.html")

YT_URL       = "https://www.youtube.com/@NovaKit-tech"
IG_URL       = "https://www.instagram.com/novakit.tech"
TODAY        = date.today().isoformat()

# Marker used to detect whether a file was already patched (idempotency key)
SOCIAL_MARKER = "<!-- novakit-social-v1 -->"

# ── Social + AI citability meta block ─────────────────────────────────────────

SOCIAL_META_BLOCK = f"""{SOCIAL_MARKER}
<!-- YouTube channel -->
<meta property="og:video:url" content="{YT_URL}">
<meta name="youtube:channel" content="{YT_URL}">
<!-- Instagram -->
<meta property="og:instagram" content="{IG_URL}">
<!-- AI Citability — helps LLMs cite & surface NovaKit correctly -->
<meta name="citation_author" content="NovaKit">
<meta name="citation_publication_date" content="{TODAY[:4]}">
<meta name="citation_online_date" content="{TODAY}">
<meta name="citation_journal_title" content="novakit.tech">
<meta name="citation_language" content="en">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<meta name="googlebot" content="index, follow">"""

# ── Social icon footer row ─────────────────────────────────────────────────────

FOOTER_SOCIAL_CSS = """.footer-social{display:flex;gap:14px;align-items:center;}
.footer-social a{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--muted);text-decoration:none;transition:color .2s;}
.footer-social a:hover{color:var(--text);}
.footer-social svg{width:16px;height:16px;flex-shrink:0;}"""

FOOTER_SOCIAL_HTML = f"""  <div class="footer-social">
    <a href="{YT_URL}" target="_blank" rel="noopener" aria-label="NovaKit on YouTube">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
      YouTube
    </a>
    <a href="{IG_URL}" target="_blank" rel="noopener" aria-label="NovaKit on Instagram">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
      Instagram
    </a>
  </div>"""

# ── Helpers ────────────────────────────────────────────────────────────────────

def patch_head_meta(html: str) -> Tuple[str, bool]:
    """Insert social+citability meta block before </head>. Idempotent."""
    if SOCIAL_MARKER in html:
        return html, False
    # Insert just before the closing </head>
    patched = html.replace("</head>", f"{SOCIAL_META_BLOCK}\n</head>", 1)
    return patched, patched != html


def patch_same_as(html: str) -> Tuple[str, bool]:
    """
    Find the Organization ld+json block and fill sameAs if it's empty ([]).
    Also handles already-empty sameAs with no spaces.
    """
    if YT_URL in html and IG_URL in html:
        # Already has both URLs somewhere — leave it
        return html, False

    pattern = r'("sameAs"\s*:\s*)\[\s*\]'
    replacement = (
        r'\1[\n'
        f'    "{YT_URL}",\n'
        f'    "{IG_URL}"\n'
        r'  ]'
    )
    patched, n = re.subn(pattern, replacement, html, count=1)
    return patched, n > 0


def patch_date_modified(html: str) -> Tuple[str, bool]:
    """Bump dateModified to today in all ld+json blocks."""
    # Matches "dateModified":"2026-xx-xx" or "dateModified": "2026-xx-xx"
    pattern = r'"dateModified"\s*:\s*"[0-9]{4}-[0-9]{2}-[0-9]{2}"'
    replacement = f'"dateModified": "{TODAY}"'
    patched, n = re.subn(pattern, replacement, html)
    return patched, n > 0


def patch_footer_css(html: str) -> Tuple[str, bool]:
    """Inject footer-social CSS into the last <style> block before </style>."""
    if "footer-social" in html:
        return html, False
    # Find the last </style> before <body (or just the last one in <head>)
    # Insert just before the final </style> in the <head>
    head_end = html.find("</head>")
    head_part = html[:head_end]
    last_style = head_part.rfind("</style>")
    if last_style == -1:
        return html, False
    patched = html[:last_style] + "\n" + FOOTER_SOCIAL_CSS + "\n" + html[last_style:]
    return patched, True


def patch_footer_html(html: str, depth: int = 1) -> Tuple[str, bool]:
    """
    Append the social icon row inside the existing <footer> block.
    depth=1 for skills/*.html  (links use ../index.html)
    depth=2 for bundles/*.html (links use ../../index.html)
    Idempotent — skipped if footer-social class already present.
    """
    if 'class="footer-social"' in html:
        return html, False
    # Find </footer> and insert before it
    idx = html.rfind("</footer>")
    if idx == -1:
        return html, False
    patched = html[:idx] + "\n" + FOOTER_SOCIAL_HTML + "\n" + html[idx:]
    return patched, True


def process_file(path: str, dry_run: bool, depth: int = 1) -> dict:
    """Apply all patches to one file. Returns a result dict."""
    result = {"file": path, "changes": [], "error": None}
    try:
        html = Path(path).read_text(encoding="utf-8")
        original = html

        html, changed = patch_head_meta(html)
        if changed: result["changes"].append("head-meta")

        html, changed = patch_same_as(html)
        if changed: result["changes"].append("sameAs")

        html, changed = patch_date_modified(html)
        if changed: result["changes"].append("dateModified")

        html, changed = patch_footer_css(html)
        if changed: result["changes"].append("footer-css")

        html, changed = patch_footer_html(html, depth=depth)
        if changed: result["changes"].append("footer-html")

        if html != original:
            if not dry_run:
                Path(path).write_text(html, encoding="utf-8")
            result["status"] = "DRY-RUN" if dry_run else "UPDATED"
        else:
            result["status"] = "SKIPPED (already up to date)"
    except Exception as e:
        result["error"] = str(e)
        result["status"] = "ERROR"
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch-update NovaKit skill + bundle pages with social links & SEO.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files.")
    parser.add_argument("--file", help="Process a single file instead of the full batch.")
    args = parser.parse_args()

    if args.file:
        targets = [(args.file, 1)]
    else:
        skill_files  = [(f, 1) for f in sorted(glob.glob(SKILLS_GLOB))]
        bundle_files = [(f, 2) for f in sorted(glob.glob(BUNDLES_GLOB))]
        targets = skill_files + bundle_files

    if not targets:
        print("No HTML files found. Run from the NovaKitwebsite directory or check paths.")
        sys.exit(1)

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Processing {len(targets)} files\n{'─'*60}")

    updated = skipped = errors = 0
    for path, depth in targets:
        r = process_file(path, dry_run=args.dry_run, depth=depth)
        label = os.path.relpath(r["file"], SCRIPT_DIR)
        if r.get("error"):
            print(f"  ERROR   {label}: {r['error']}")
            errors += 1
        elif r["status"].startswith("SKIPPED"):
            print(f"  --      {label}")
            skipped += 1
        else:
            changes = ", ".join(r["changes"]) if r["changes"] else "none"
            print(f"  {'~' if args.dry_run else '✓'}  {label}  [{changes}]")
            updated += 1

    print(f"\n{'─'*60}")
    print(f"{'Would update' if args.dry_run else 'Updated'}: {updated}  |  Already current: {skipped}  |  Errors: {errors}")
    if args.dry_run:
        print("Run without --dry-run to apply changes.")
    print()


if __name__ == "__main__":
    main()
