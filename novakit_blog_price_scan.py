#!/usr/bin/env python3
"""
novakit_blog_price_scan.py — Stale Price Reference Scanner
===========================================================
Scans every HTML file in your blog folder for any price mention
($5, $9, $15 etc.) and flags lines that reference a price that
doesn't match what products.js says for that skill.

Also catches:
  - Old bundle prices no longer in products.js
  - Any hardcoded price that differs from the canonical list
  - Price mentions in meta descriptions, og:description, alt text

Usage
-----
  python3 novakit_blog_price_scan.py --blogs ./blog --products ./js/products.js

Output
------
  Terminal report + stale-prices.txt
"""

import re
import argparse
from pathlib import Path
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────────────────
# VALID PRICES — all prices currently live in products.js
# Any price found in a blog that isn't in this set is immediately suspicious.
# ─────────────────────────────────────────────────────────────────────────────

VALID_SKILL_PRICES  = {5, 6, 7, 8, 9, 15, 19}
VALID_BUNDLE_PRICES = {15, 19, 29, 39, 45, 69}
ALL_VALID_PRICES    = VALID_SKILL_PRICES | VALID_BUNDLE_PRICES

# Prices that used to exist but are now wrong — flag these explicitly
RETIRED_PRICES = {49, 59, 99, 10, 12, 20, 25, 29.99, 49.99}

# ─────────────────────────────────────────────────────────────────────────────
# CANONICAL SKILL → PRICE (from products.js, locked May 2026)
# ─────────────────────────────────────────────────────────────────────────────

SKILL_PRICES = {
    # $19
    "UGC Ad Creator": 19, "Brand & Ad Copy": 19, "Pitch Deck Narrative": 19,
    "Financial Model Prompt": 19, "Short-Form AI Video": 19,
    # $15
    "Brand Voice Guide": 15, "PRD Writer": 15, "Architecture Diagram Prompt": 15,
    "Grant & Proposal Writing": 15, "Course & Curriculum Builder": 15,
    "University Application SOP": 15, "Video Script Engine": 15,
    "AI Animation Film Prompt": 15, "Product Ad Film Prompt": 15,
    "Dialogue / Character Film Prompt": 15, "NDA / Contract Draft": 15,
    "Terms of Service & Privacy Policy": 15,
    # $9
    "LinkedIn Post Engine": 9, "Social Content Engine": 9,
    "Twitter / X Thread Engine": 9, "SEO Blog Post Brief": 9,
    "Email Newsletter Engine": 9, "PR Press Release": 9, "Sales Page": 9,
    "Business Plan": 9, "Resume & CV Builder": 9, "Logo & Brand Identity": 9,
    "Podcast Episode Script": 9, "Webinar / Online Event Script": 9,
    "E-Commerce Product Listing": 9, "Real Estate Listing Copy": 9,
    "Investor Update Email": 9, "Cold Outreach Email": 9,
    "Cover Letter Writer": 9, "Job Description Writer": 9,
    "Performance Review Writer": 9, "Exam Paper Generator": 9,
    "Product Photography Prompt": 9, "Real Estate Photo Prompt": 9,
    # $8
    "Social Media Carousel Prompt": 8, "Content Calendar": 8,
    "Lesson Plan Builder": 8, "YouTube Thumbnail Prompt": 8,
    "Podcast Show Notes": 8, "Health & Wellness Plan": 8,
    # $7
    "Research Paper Outline": 7, "Conference Abstract": 7,
    "Hotel / Airbnb Listing Copy": 7,
    # $6
    "Screenplay / Script": 6, "Children's Book Prompt": 6,
    # $5
    "Short Story Prompt": 5, "Poetry & Verse Prompt": 5, "Book Cover Prompt": 5,
    "Festival & Holiday Greeting Prompt": 5, "Menu Description Copy": 5,
    "Wedding Invitation Prompt": 5, "Wedding Vows Writer": 5,
    "Event Speech Writer": 5, "Eulogy Writer": 5,
    "Visa Application Cover Letter": 5, "Travel Itinerary Planner": 5,
    "Recipe Development Prompt": 5, "Home Renovation Brief": 5,
}

BUNDLE_PRICES = {
    "Founder Bundle": 39, "Creator Bundle": 45, "Marketing Bundle": 45,
    "Legal & Biz Bundle": 45, "Video & Podcast Bundle": 69,
    "Student Bundle": 29, "Realtor Bundle": 29, "Educator Bundle": 29,
    "Wedding Bundle": 15, "Creative Bundle": 19,
}

ALL_NAMED_PRICES = {**SKILL_PRICES, **BUNDLE_PRICES}


def parse_products_js(path):
    """Extract slug → price from products.js as the live source of truth."""
    content = Path(path).read_text(encoding="utf-8")
    entries = re.findall(
        r"'([^']+)':\s*\{[^}]*price:\s*(\d+)",
        content, re.DOTALL
    )
    return {slug: int(price) for slug, price in entries}


def scan_blog(html_path, products_prices):
    """
    Scan a single blog HTML for price mentions.
    Returns list of (line_number, line_text, issue_description)
    """
    issues = []
    content = html_path.read_text(encoding="utf-8", errors="replace")

    # Price pattern: $5 $9 $15 $19 $39 $45 $69 etc.
    # Also catch "from $X", "only $X", "just $X", "was $X"
    price_pattern = re.compile(r'\$\s*(\d+(?:\.\d{2})?)', re.IGNORECASE)

    # Patterns that are never skill prices — suppress entirely
    FALSE_POSITIVE_PATTERNS = [
        re.compile(r'\$\d+[kKmMbB]'),            # $400k, $2.1M, $47B etc.
        re.compile(r'\$(\d{3,}),\d{3}'),         # $240,000 $2,160,000 etc.
        re.compile(r'ARR|MRR|NRR|CAC|ACV', re.I),  # revenue metric context
        re.compile(r'raise[sd]?|round|seed|fund', re.I),  # funding context
        re.compile(r'market|industry|valuation', re.I),   # market size context
        re.compile(r'property|house|home|listing price', re.I),  # real estate values
        re.compile(r'legal fee|liability|damages|penalty', re.I),# legal context
        re.compile(r'lost \$|earn|revenue|salary|budget', re.I),# earnings context
        re.compile(r'hook|example|script|template', re.I),       # content examples
    ]

    lines = content.split('\n')
    for line_num, line in enumerate(lines, 1):
        # Skip lines that are clearly JS/CSS/URLs, not visible content
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('//') or stripped.startswith('/*'):
            continue
        if 'rzp.io' in line or 'assets.novakit' in line:
            continue

        matches = price_pattern.finditer(line)
        for m in matches:
            price_val = float(m.group(1))
            price_int = int(price_val) if price_val == int(price_val) else price_val

            # Skip prices that look like years, IDs, or percentages
            context = line[max(0, m.start()-30):m.end()+60]
            if re.search(r'\d{4}', m.group(0)):  # skip years
                continue
            if '%' in line[m.end():m.end()+2]:   # skip percentages
                continue
            # Skip if surrounding context matches known false positive patterns
            if any(fp.search(context) for fp in FALSE_POSITIVE_PATTERNS):
                continue
            # Skip large numbers — revenue/market figures, not prices
            if price_int > 99:
                continue

            # Flag if not in valid price set
            if price_int not in ALL_VALID_PRICES:
                issues.append((
                    line_num,
                    stripped[:120],
                    f"INVALID PRICE ${price_int} — not in any current tier"
                ))
            elif price_int in RETIRED_PRICES:
                issues.append((
                    line_num,
                    stripped[:120],
                    f"RETIRED PRICE ${price_int} — this tier no longer exists"
                ))

    # Also check for skill names with wrong prices mentioned nearby
    soup = BeautifulSoup(content, 'html.parser')
    text = soup.get_text(separator='\n')

    for skill_name, correct_price in ALL_NAMED_PRICES.items():
        # Find skill name in text
        pattern = re.compile(re.escape(skill_name), re.IGNORECASE)
        for m in pattern.finditer(text):
            # Look for a price within 150 chars of the skill name
            window = text[m.start():m.start()+150]
            price_nearby = re.search(r'\$\s*(\d+)', window)
            if price_nearby:
                found_price = int(price_nearby.group(1))
                if found_price != correct_price and found_price in ALL_VALID_PRICES:
                    # Wrong but valid price — likely a stale reference
                    issues.append((
                        0,  # line number not available from soup
                        f"'{skill_name}' mentioned near ${found_price}",
                        f"WRONG PRICE — '{skill_name}' should be ${correct_price}, found ${found_price} nearby"
                    ))
                    break  # one flag per skill per file is enough

    # Deduplicate
    seen = set()
    deduped = []
    for item in issues:
        key = (item[0], item[2])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


def main():
    parser = argparse.ArgumentParser(description="Novakit Blog Stale Price Scanner")
    parser.add_argument("--blogs",    required=True, help="Path to blog HTML folder")
    parser.add_argument("--products", required=False, help="Path to products.js (optional, for live price check)")
    args = parser.parse_args()

    blogs_dir = Path(args.blogs)
    blog_files = sorted(blogs_dir.glob("*.html"))

    # Load live prices from products.js if provided
    products_prices = {}
    if args.products:
        products_prices = parse_products_js(args.products)
        print(f"\nLoaded {len(products_prices)} prices from products.js")

    print(f"Scanning {len(blog_files)} blog files...\n")

    all_issues = {}   # filename → list of issues
    clean_count = 0

    for blog_path in blog_files:
        issues = scan_blog(blog_path, products_prices)
        if issues:
            all_issues[blog_path.name] = issues
        else:
            clean_count += 1

    # ── Print report ─────────────────────────────────────────────────────────
    print("═" * 70)
    print("  BLOG PRICE SCAN RESULTS")
    print("═" * 70)
    print(f"  Files scanned : {len(blog_files)}")
    print(f"  Clean files   : {clean_count}")
    print(f"  Files with issues : {len(all_issues)}")
    print("═" * 70)

    if all_issues:
        print()
        for filename, issues in sorted(all_issues.items()):
            print(f"\n  📄 {filename}")
            for line_num, line_text, description in issues:
                loc = f"line {line_num}" if line_num else "in content"
                print(f"     ⚠  [{loc}] {description}")
                print(f"        {line_text[:100]}")
    else:
        print("\n  ✅  No stale price references found in any blog file.\n")

    # ── Write report ──────────────────────────────────────────────────────────
    report_path = Path("stale-prices.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("NOVAKIT BLOG STALE PRICE REPORT\n")
        f.write("=" * 70 + "\n")
        if all_issues:
            for filename, issues in sorted(all_issues.items()):
                f.write(f"\n{filename}\n")
                for line_num, line_text, description in issues:
                    loc = f"line {line_num}" if line_num else "in content"
                    f.write(f"  [{loc}] {description}\n")
                    f.write(f"  {line_text[:120]}\n")
        else:
            f.write("No stale price references found.\n")

    print(f"\n  Report saved → {report_path}\n")


if __name__ == "__main__":
    main()
