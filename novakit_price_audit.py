#!/usr/bin/env python3
"""
novakit_price_audit.py — Products.js Price & Slug Audit
=========================================================
Parses products.js and compares every skill and bundle against
the canonical pricing reference (novakit-pricing-ref-final.html).

Checks:
  1. Price mismatches (products.js vs canonical)
  2. Name casing issues in products.js
  3. Slug mismatches between products.js keys and linker script expectations
  4. Skills present in canonical ref but missing from products.js
  5. Skills in products.js not in canonical ref (orphans)

Usage
-----
  python3 novakit_price_audit.py --products ./products.js
  python3 novakit_price_audit.py --products ./products.js --fix   # writes products.js.fixed
"""

import re
import argparse
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CANONICAL REFERENCE — from novakit-pricing-ref-final.html
# This is the source of truth for prices and display names.
# Key: products.js slug  Value: (canonical_display_name, price)
# ─────────────────────────────────────────────────────────────────────────────

CANONICAL = {
    # $19 skills
    "ugc-ad-creator":                  ("UGC Ad Creator",                    19),
    "brand-ad-copy":                   ("Brand & Ad Copy",                   19),
    "pitch-deck-narrative":            ("Pitch Deck Narrative",               19),
    "financial-model-prompt":          ("Financial Model Prompt",             19),
    "ai-video-prompt":                 ("Short-Form AI Video",                19),  # slug ≠ display name intentionally
    # $15 skills
    "brand-voice-guide":               ("Brand Voice Guide",                  15),
    "prd-writer":                      ("PRD Writer",                         15),
    "architecture-diagram-prompt":     ("Architecture Diagram Prompt",        15),
    "grant-and-proposal-writing":      ("Grant & Proposal Writing",           15),
    "course-curriculum-builder":       ("Course & Curriculum Builder",        15),
    "university-sop":                  ("University Application SOP",         15),
    "video-script-engine":             ("Video Script Engine",                15),
    "ai-animation-film-prompt":        ("AI Animation Film Prompt",           15),
    "product-ad-film-prompt":          ("Product Ad Film Prompt",             15),
    "dialogue-character-film-prompt":  ("Dialogue / Character Film Prompt",   15),
    "nda-contract-draft":              ("NDA / Contract Draft",               15),
    "tos-privacy-policy":              ("Terms of Service & Privacy Policy",  15),
    # $9 skills
    "linkedin-post-engine":            ("LinkedIn Post Engine",                9),
    "social-content-engine":           ("Social Content Engine",               9),
    "twitter-x-thread-engine":         ("Twitter / X Thread Engine",           9),
    "seo-blog-post-brief":             ("SEO Blog Post Brief",                 9),
    "email-newsletter-engine":         ("Email Newsletter Engine",             9),
    "pr-press-release":                ("PR Press Release",                    9),
    "sales-landing-page-copy":         ("Sales Page",                          9),
    "business-plan":                   ("Business Plan",                       9),
    "resume-cv-builder":               ("Resume & CV Builder",                 9),
    "logo-brand-identity-prompt":      ("Logo & Brand Identity",               9),
    "podcast-episode-script":          ("Podcast Episode Script",              9),
    "webinar-online-event-script":     ("Webinar / Online Event Script",       9),
    "ecommerce-product-listing":       ("E-Commerce Product Listing",          9),
    "real-estate-listing-copy":        ("Real Estate Listing Copy",            9),
    "investor-update-email":           ("Investor Update Email",               9),
    "cold-outreach-email":             ("Cold Outreach Email",                 9),
    "cover-letter-writer":             ("Cover Letter Writer",                 9),
    "job-description-writer":          ("Job Description Writer",              9),
    "performance-review-writer":       ("Performance Review Writer",           9),
    "exam-paper-generator":            ("Exam Paper Generator",                9),
    "product-photography-prompt":      ("Product Photography Prompt",          9),
    "real-estate-photo-prompt":        ("Real Estate Photo Prompt",            9),
    # $8 skills
    "social-media-carousel-prompt":    ("Social Media Carousel Prompt",        8),
    "content-calendar":                ("Content Calendar",                    8),
    "lesson-plan-builder":             ("Lesson Plan Builder",                 8),
    "youtube-thumbnail-prompt":        ("YouTube Thumbnail Prompt",            8),
    "podcast-show-notes":              ("Podcast Show Notes",                  8),
    "health-wellness-plan":            ("Health & Wellness Plan",              8),
    # $7 skills
    "research-paper-outline":          ("Research Paper Outline",              7),
    "conference-abstract":             ("Conference Abstract",                 7),
    "hotel-airbnb-listing-copy":       ("Hotel / Airbnb Listing Copy",         7),
    # $6 skills
    "screenplay-script":               ("Screenplay / Script",                 6),
    "childrens-book-prompt":           ("Children's Book Prompt",              6),
    # $5 skills
    "short-story-prompt":              ("Short Story Prompt",                  5),
    "poetry-verse-prompt":             ("Poetry & Verse Prompt",               5),
    "book-cover-prompt":               ("Book Cover Prompt",                   5),
    "festival-holiday-greeting-prompt":("Festival & Holiday Greeting Prompt",  5),
    "menu-description-copy":           ("Menu Description Copy",               5),
    "wedding-invitation-prompt":       ("Wedding Invitation Prompt",           5),
    "wedding-vows-writer":             ("Wedding Vows Writer",                 5),
    "event-speech-writer":             ("Event Speech Writer",                 5),
    "eulogy-writer":                   ("Eulogy Writer",                       5),
    "visa-cover-letter":               ("Visa Application Cover Letter",       5),
    "travel-itinerary-planner":        ("Travel Itinerary Planner",            5),
    "recipe-development-prompt":       ("Recipe Development Prompt",           5),
    "home-renovation-brief":           ("Home Renovation Brief",               5),
    # Bundles
    "founder-bundle":                  ("Founder Bundle",                      39),
    "creator-bundle":                  ("Creator Bundle",                      45),
    "marketing-bundle":                ("Marketing Bundle",                    45),
    "legal-biz-bundle":                ("Legal & Biz Bundle",                  45),
    "video-pod-bundle":                ("Video & Podcast Bundle",              69),
    "student-bundle":                  ("Student Bundle",                      29),
    "realtor-bundle":                  ("Realtor Bundle",                      29),
    "educator-bundle":                 ("Educator Bundle",                     29),
    "wedding-bundle":                  ("Wedding Bundle",                      15),
    "creative-bundle":                 ("Creative Bundle",                     19),
}

# ─────────────────────────────────────────────────────────────────────────────
# LINKER SCRIPT SLUG MAP
# Maps the slug used in novakit_linker.py → products.js key
# Flags mismatches so linker scripts can be kept in sync
# ─────────────────────────────────────────────────────────────────────────────

LINKER_TO_PRODUCTS = {
    "short-form-ai-video":           "ai-video-prompt",
    "grant-proposal-writing":        "grant-and-proposal-writing",
    "logo-brand-identity":           "logo-brand-identity-prompt",
    "sales-page":                    "sales-landing-page-copy",
    "terms-of-service-privacy-policy":"tos-privacy-policy",
    "university-application-sop":    "university-sop",
    "visa-application-cover-letter": "visa-cover-letter",
    "video-script":                  "video-script-engine",
    "children-book-prompt":          "childrens-book-prompt",
    # All others: linker slug == products.js key
}

# Canonical name fixes for products.js (display name corrections)
NAME_FIXES = {
    "linkedin-post-engine":   ("Linkedin Post Engine",  "LinkedIn Post Engine"),
    "resume-cv-builder":      ("Resume Cv Builder",     "Resume & CV Builder"),
    "youtube-thumbnail-prompt":("Youtube Thumbnail Prompt","YouTube Thumbnail Prompt"),
    "health-wellness-plan":   ("Health Wellness Plan",  "Health & Wellness Plan"),
}


# ─────────────────────────────────────────────────────────────────────────────
# PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_products_js(content):
    """
    Extract all entries from products.js.
    Returns dict: key → {name, slug, price}
    """
    entries = {}
    # Match each top-level key block
    blocks = re.findall(
        r"'([^']+)':\s*\{([^}]+)\}",
        content, re.DOTALL
    )
    for key, body in blocks:
        name_m  = re.search(r'name:\s*["\']([^"\']+)["\']', body)
        slug_m  = re.search(r'slug:\s*["\']([^"\']+)["\']', body)
        price_m = re.search(r'price:\s*(\d+)', body)
        if name_m and price_m:
            entries[key] = {
                "name":  name_m.group(1),
                "slug":  slug_m.group(1) if slug_m else key,
                "price": int(price_m.group(1)),
            }
    return entries


def apply_fixes(content):
    """Apply name casing fixes to products.js content string."""
    for slug, (wrong, correct) in NAME_FIXES.items():
        content = content.replace(f'name: "{wrong}"', f'name: "{correct}"')
    return content


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Novakit Products.js Price & Slug Audit")
    parser.add_argument("--products", required=True, help="Path to products.js")
    parser.add_argument("--fix", action="store_true",
                        help="Write products.js.fixed with name casing corrections applied")
    args = parser.parse_args()

    content  = Path(args.products).read_text(encoding="utf-8")
    products = parse_products_js(content)

    price_errors  = []
    name_errors   = []
    slug_errors   = []
    missing       = []
    orphans       = []

    canonical_keys = set(CANONICAL.keys())
    products_keys  = set(products.keys())

    # ── 1. Price check ───────────────────────────────────────────────────────
    for key, (canon_name, canon_price) in CANONICAL.items():
        if key not in products:
            missing.append(key)
            continue
        actual_price = products[key]["price"]
        if actual_price != canon_price:
            price_errors.append((key, canon_price, actual_price))

    # ── 2. Name casing check ─────────────────────────────────────────────────
    for key, (wrong, correct) in NAME_FIXES.items():
        if key in products and products[key]["name"] == wrong:
            name_errors.append((key, wrong, correct))

    # ── 3. Slug consistency (key == entry slug) ───────────────────────────────
    for key, data in products.items():
        if key != data["slug"]:
            slug_errors.append((key, data["slug"]))

    # ── 4. Orphans (in products.js but not in canonical ref) ─────────────────
    for key in products_keys - canonical_keys:
        orphans.append(key)

    # ── Print report ──────────────────────────────────────────────────────────
    W = "⚠ "
    OK = "✓ "
    print("\n" + "═" * 70)
    print("  NOVAKIT PRODUCTS.JS AUDIT")
    print("═" * 70)
    print(f"  Skills/bundles in products.js : {len(products)}")
    print(f"  Skills/bundles in canonical   : {len(CANONICAL)}")
    print("═" * 70)

    # Price mismatches
    print(f"\n{'PRICE MISMATCHES':─<70}")
    if price_errors:
        for key, expected, actual in price_errors:
            print(f"  {W}{key:<45} expected ${expected}  got ${actual}")
    else:
        print(f"  {OK}All prices match canonical reference")

    # Name casing
    print(f"\n{'NAME CASING ISSUES':─<70}")
    if name_errors:
        for key, wrong, correct in name_errors:
            print(f"  {W}{key}")
            print(f"       current : \"{wrong}\"")
            print(f"       correct : \"{correct}\"")
    else:
        print(f"  {OK}All display names look correct")

    # Key ≠ slug inside entry
    print(f"\n{'SLUG CONSISTENCY (key ≠ internal slug)':─<70}")
    if slug_errors:
        for key, slug in slug_errors:
            print(f"  {W}key: '{key}'  →  slug: '{slug}'")
    else:
        print(f"  {OK}All keys match their internal slug field")

    # Linker script slug mismatches
    print(f"\n{'LINKER SCRIPT SLUG MAP (scripts → products.js)':─<70}")
    print(f"  These slugs in novakit_linker.py differ from products.js keys.")
    print(f"  Both the SKILL_FILE_OVERRIDES dict and any URL builders must use")
    print(f"  the products.js key as the skill page filename stem.\n")
    for linker_slug, products_key in sorted(LINKER_TO_PRODUCTS.items()):
        in_products = OK if products_key in products else W + "NOT IN PRODUCTS.JS"
        print(f"  {linker_slug:<45} →  {products_key}  {in_products}")

    # Missing from products.js
    print(f"\n{'MISSING FROM PRODUCTS.JS':─<70}")
    if missing:
        for key in sorted(missing):
            canon_name, canon_price = CANONICAL[key]
            print(f"  {W}{key:<45} ({canon_name}, ${canon_price})")
    else:
        print(f"  {OK}No canonical skills missing from products.js")

    # Orphans
    print(f"\n{'IN PRODUCTS.JS BUT NOT IN CANONICAL REF':─<70}")
    if orphans:
        for key in sorted(orphans):
            d = products[key]
            print(f"  {W}{key:<45} \"{d['name']}\"  ${d['price']}")
    else:
        print(f"  {OK}No orphan entries found")

    # Full price list for visual confirmation
    print(f"\n{'FULL PRICE LIST — products.js':─<70}")
    skills  = {k: v for k, v in products.items() if "bundle" not in k}
    bundles = {k: v for k, v in products.items() if "bundle" in k}

    by_price = {}
    for k, v in skills.items():
        by_price.setdefault(v["price"], []).append((k, v["name"]))
    for price in sorted(by_price.keys(), reverse=True):
        print(f"\n  ${price}")
        for slug, name in sorted(by_price[price]):
            canon_price = CANONICAL.get(slug, (None, None))[1]
            flag = "" if canon_price == price else f"  {W}PRICE MISMATCH (canonical: ${canon_price})"
            print(f"    {slug:<45} {name}{flag}")

    print(f"\n  Bundles")
    for slug, data in sorted(bundles.items()):
        canon_price = CANONICAL.get(slug, (None, None))[1]
        flag = "" if canon_price == data["price"] else f"  {W}MISMATCH (canonical: ${canon_price})"
        print(f"    {slug:<45} ${data['price']}{flag}")

    # Summary
    total_issues = len(price_errors) + len(name_errors) + len(slug_errors) + len(missing)
    print(f"\n{'═' * 70}")
    print(f"  Issues found: {total_issues}  "
          f"(prices: {len(price_errors)}, names: {len(name_errors)}, "
          f"slug consistency: {len(slug_errors)}, missing: {len(missing)})")
    print(f"{'═' * 70}\n")

    # ── Apply fixes if requested ───────────────────────────────────────────
    if args.fix:
        fixed = apply_fixes(content)
        out_path = Path(args.products).with_suffix(".js.fixed")
        out_path.write_text(fixed, encoding="utf-8")
        if name_errors:
            print(f"products.js updated in place → {out_path}")
            print("Changes made:")
            for key, wrong, correct in name_errors:
                print(f"  \"{wrong}\" → \"{correct}\"")
        else:
            print("No name fixes needed — products.js unchanged.")
        print()


if __name__ == "__main__":
    main()
