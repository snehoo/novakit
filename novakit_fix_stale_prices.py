#!/usr/bin/env python3
"""
novakit_fix_stale_prices.py — Fix Real Stale Prices in Blog Files
==================================================================
Applies targeted fixes ONLY to the 5 confirmed real price errors.
Everything else in the scan report is a false positive (revenue
figures, ARR, market sizes, hook examples, property values).

Real issues confirmed:
  1. airbnb-listing-copy-you-vs-ai-vs-calibrated-skill.html
       Hotel / Airbnb Listing Copy mentioned near $9 — should be $7

  2. the-sales-page-that-sounds-like-it-was-written-about-your-product.html
       Sales Page mentioned near $15 — should be $9

  3. university-application-sop-why-ai-sops-fail.html
       Student Bundle mentioned near $15 — should be $29

  4. travel-itinerary-planner.html
       rc-meta shows "$9 – $49" — $49 is retired, range is now $5 – $19

  5. why-ai-travel-itineraries-feel-generic.html
       Same rc-meta issue as above

False positives (DO NOT touch):
  business-plan.html              — £150k round, $3 is fragment of larger figure
  financial-model*.html           — ARR/MRR/revenue example figures ($240k, $720k etc.)
  job-description-writer.html     — $2.4M ARR in a job description example
  nda-contract-draft.html         — "$800 in legal fees" — contextual, not a price
  pitch-deck-narrative*.html      — $1.8M raised, $22B market, $190K MRR — example data
  pr-press-release*.html          — $3.5M seed round, $47B industry — press release examples
  real-estate-photo-prompt.html   — $280,000 house, $2.8M waterfront — property values
  short-form-ai-video-script.html — "$4,000" hook example in script
  terms-of-service*.html          — $500 liability cap — legal context example
  webinar-online-event-script.html— $2M/$10M ARR in webinar script example
  why-short-form-ai-video*.html   — "$4,000" hook example in table
  youtube-thumbnail-prompt*.html  — $50 in thumbnail hook example

Usage
-----
  # Dry run (default — shows changes, writes nothing)
  python3 novakit_fix_stale_prices.py --blogs ./blog

  # Live run
  python3 novakit_fix_stale_prices.py --blogs ./blog --run
"""

import re
import argparse
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# FIXES — each entry: (filename, search_pattern, replacement, description)
# Patterns are regex so we can be surgical — only match the price in context.
# ─────────────────────────────────────────────────────────────────────────────

FIXES = [

    # ── Fix 1: Airbnb listing — price shown as $9, correct price is $7 ───────
    {
        "file":   "airbnb-listing-copy-you-vs-ai-vs-calibrated-skill.html",
        "find":   re.compile(
            r'(Hotel\s*/\s*Airbnb Listing Copy[^$]*?)\$9(?!\d)',
            re.IGNORECASE | re.DOTALL
        ),
        "replace": r'\g<1>$7',
        "note":   "Hotel / Airbnb Listing Copy $9 → $7",
        "max_replacements": 3,
    },

    # ── Fix 2: Sales page blog — price shown as $15, correct price is $9 ─────
    {
        "file":   "the-sales-page-that-sounds-like-it-was-written-about-your-product.html",
        "find":   re.compile(
            r'(Sales\s*Page[^$\n]{0,80}?)\$15(?!\d)',
            re.IGNORECASE | re.DOTALL
        ),
        "replace": r'\g<1>$9',
        "note":   "Sales Page $15 → $9",
        "max_replacements": 3,
    },

    # ── Fix 3: Student bundle — shown as $15, correct price is $29 ───────────
    {
        "file":   "university-application-sop-why-ai-sops-fail.html",
        "find":   re.compile(
            r'(Student\s*Bundle[^$\n]{0,80}?)\$15(?!\d)',
            re.IGNORECASE | re.DOTALL
        ),
        "replace": r'\g<1>$29',
        "note":   "Student Bundle $15 → $29",
        "max_replacements": 3,
    },

    # ── Fix 4 & 5: rc-meta price range — $9–$49 is stale on both travel blogs
    # Correct individual skill range is $5–$19. Also update skill count 62→63.
    {
        "file":   "travel-itinerary-planner.html",
        "find":   re.compile(r'62\s*skills\s*·\s*\$9\s*[–-]\s*\$49', re.IGNORECASE),
        "replace": "63 skills · $5 – $19",
        "note":   "rc-meta: 62 skills · $9–$49 → 63 skills · $5–$19",
        "max_replacements": 5,
    },
    {
        "file":   "why-ai-travel-itineraries-feel-generic.html",
        "find":   re.compile(r'62\s*skills\s*·\s*\$9\s*[–-]\s*\$49', re.IGNORECASE),
        "replace": "63 skills · $5 – $19",
        "note":   "rc-meta: 62 skills · $9–$49 → 63 skills · $5–$19",
        "max_replacements": 5,
    },
]


def apply_fix(content, fix):
    """Apply a single fix, up to max_replacements times. Returns (new_content, count)."""
    count = 0
    max_r = fix.get("max_replacements", 1)
    new_content = content
    for _ in range(max_r):
        result = fix["find"].sub(fix["replace"], new_content, count=1)
        if result == new_content:
            break
        new_content = result
        count += 1
    return new_content, count


def main():
    parser = argparse.ArgumentParser(description="Fix confirmed stale prices in blog files")
    parser.add_argument("--blogs", required=True, help="Path to blog HTML folder")
    parser.add_argument("--run",   action="store_true", help="Write changes (default is dry run)")
    args = parser.parse_args()

    blogs_dir = Path(args.blogs)
    dry_run   = not args.run

    print(f"\n{'⚠  DRY RUN — pass --run to apply changes' if dry_run else '✅  LIVE RUN'}\n")
    print(f"{'FILE':<65} {'FIX':<45} MATCHES")
    print("─" * 120)

    total_fixes = 0

    for fix in FIXES:
        blog_path = blogs_dir / fix["file"]

        if not blog_path.exists():
            print(f"  {'[NOT FOUND] ' + fix['file']:<65} {fix['note']:<45} —")
            continue

        content     = blog_path.read_text(encoding="utf-8", errors="replace")
        new_content, count = apply_fix(content, fix)

        if count == 0:
            print(f"  {fix['file']:<65} {fix['note']:<45} no match found")
            continue

        print(f"  {fix['file']:<65} {fix['note']:<45} {count} replacement(s)")
        total_fixes += count

        if not dry_run and new_content != content:
            blog_path.write_text(new_content, encoding="utf-8")

    print("─" * 120)
    print(f"Total replacements: {total_fixes}")
    if dry_run:
        print("Run with --run to apply.\n")
    else:
        print("Files updated in place.\n")


if __name__ == "__main__":
    main()
