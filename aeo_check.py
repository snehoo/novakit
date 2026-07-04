#!/usr/bin/env python3
"""
aeo_check.py — Validate AEO fixes across all NovaKit skill and bundle pages.

Skill checks per file:
  product_has_id            Product schema has @id
  product_date_published    datePublished present in schema
  product_soft_app          @type includes SoftwareApplication
  seller_org_id             seller uses @id reference (not @type: Organization)
  howto_schema              HowTo schema block present
  faq_schema_4plus          FAQPage schema has ≥ 4 Q&As
  faq_visible_4plus         ≥ 4 FAQ <h3> questions visible in HTML
  star_rating               ★ rating display present in testimonial section
  footer_date               Footer contains published/updated date
  rating_schema_match       aggregateRating in schema matched by visible ★ block

Bundle checks per file:
  product_has_id, product_date_published, product_date_modified,
  product_soft_app, seller_org_id, breadcrumb_schema, howto_schema,
  faq_schema_3plus, faq_h2_sections, footer_date

Usage:
  python3 aeo_check.py            # skill pages, pretty table
  python3 aeo_check.py --bundles  # bundle pages
  python3 aeo_check.py --csv      # CSV output
  python3 aeo_check.py --fails    # only show files with at least one FAIL
"""

import csv
import json
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

SKILLS_DIR = Path(__file__).parent / "skills"
BUNDLES_DIR = Path(__file__).parent / "skills" / "bundles"
LLMS_TXT = Path(__file__).parent / "llms.txt"

CHECKS = [
    "product_has_id",
    "product_date_published",
    "product_soft_app",
    "seller_org_id",
    "howto_schema",
    "faq_schema_4plus",
    "faq_visible_4plus",
    "star_rating",
    "footer_date",
    "rating_schema_match",
]

BUNDLE_CHECKS = [
    "product_has_id",
    "product_date_published",
    "product_date_modified",
    "product_soft_app",
    "seller_org_id",
    "breadcrumb_schema",
    "howto_schema",
    "faq_schema_3plus",
    "faq_h2_sections",
    "footer_date",
]

STATUS = {"PASS": "✅", "FAIL": "❌", "SKIP": "—"}

# ── Helpers ────────────────────────────────────────────────────────────────

def parse_schemas(soup):
    out = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            out.append(json.loads(tag.string))
        except (json.JSONDecodeError, TypeError):
            pass
    return out


def has_type(data, type_name):
    t = data.get("@type", "")
    return type_name in (t if isinstance(t, list) else [t])


def get_product(schemas):
    for s in schemas:
        if has_type(s, "Product"):
            return s
    return None


def get_faq(schemas):
    for s in schemas:
        if has_type(s, "FAQPage"):
            return s
    return None


def get_howto(schemas):
    for s in schemas:
        if has_type(s, "HowTo"):
            return s
    return None

# ── Per-file check ─────────────────────────────────────────────────────────

def check_file(html_path):
    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    schemas = parse_schemas(soup)
    product = get_product(schemas)
    faq = get_faq(schemas)
    howto = get_howto(schemas)

    r = {c: "FAIL" for c in CHECKS}
    notes = []

    # product_has_id
    if product and "@id" in product:
        r["product_has_id"] = "PASS"

    # product_date_published
    if product and "datePublished" in product:
        r["product_date_published"] = "PASS"

    # product_soft_app
    if product:
        types = product.get("@type", "")
        if isinstance(types, list) and "SoftwareApplication" in types:
            r["product_soft_app"] = "PASS"

    # seller_org_id
    if product:
        seller = product.get("offers", {}).get("seller", {})
        if isinstance(seller, dict) and "@id" in seller and "@type" not in seller:
            r["seller_org_id"] = "PASS"

    # howto_schema
    if howto:
        r["howto_schema"] = "PASS"

    # faq_schema_4plus
    if faq:
        count = len(faq.get("mainEntity", []))
        if count >= 4:
            r["faq_schema_4plus"] = "PASS"
        else:
            notes.append(f"faq_schema has {count} Q&As")

    # faq_visible_4plus — find "Quick answers" section
    faq_section = None
    for section in soup.find_all("section"):
        eyebrow = section.find(class_="section-eyebrow")
        if eyebrow and "quick answers" in eyebrow.get_text(strip=True).lower():
            faq_section = section
            break

    if faq_section:
        h3_count = len(faq_section.find_all("h3"))
        if h3_count >= 4:
            r["faq_visible_4plus"] = "PASS"
        else:
            notes.append(f"faq_visible has {h3_count} H3s")
    else:
        notes.append("faq_section not found")

    # star_rating — ★ in pq-inner
    pq = soup.find(class_="pq-inner")
    if pq and "★" in pq.get_text():
        r["star_rating"] = "PASS"

    # footer_date
    footer_left = soup.find(class_="footer-left")
    if footer_left and "Published" in footer_left.get_text():
        r["footer_date"] = "PASS"

    # rating_schema_match
    if product and "aggregateRating" in product:
        if pq and "★" in (pq.get_text() if pq else ""):
            r["rating_schema_match"] = "PASS"
        else:
            notes.append("aggregateRating in schema but no ★ visible")
    else:
        r["rating_schema_match"] = "SKIP"  # no aggregateRating → not applicable

    return r, notes

# ── Bundle check ───────────────────────────────────────────────────────────

def check_bundle_file(html_path):
    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    schemas = parse_schemas(soup)
    product = get_product(schemas)
    faq = get_faq(schemas)
    howto = get_howto(schemas)

    r = {c: "FAIL" for c in BUNDLE_CHECKS}
    notes = []

    if product:
        if "@id" in product:
            r["product_has_id"] = "PASS"
        if "datePublished" in product:
            r["product_date_published"] = "PASS"
        if "dateModified" in product:
            r["product_date_modified"] = "PASS"
        types = product.get("@type", "")
        if isinstance(types, list) and "SoftwareApplication" in types:
            r["product_soft_app"] = "PASS"
        seller = product.get("offers", {}).get("seller", {})
        if isinstance(seller, dict) and "@id" in seller and "@type" not in seller:
            r["seller_org_id"] = "PASS"

    # breadcrumb
    for s in schemas:
        if has_type(s, "BreadcrumbList"):
            r["breadcrumb_schema"] = "PASS"
            break

    # howto
    if howto:
        r["howto_schema"] = "PASS"

    # faq schema (3+ for bundles)
    if faq:
        count = len(faq.get("mainEntity", []))
        if count >= 3:
            r["faq_schema_3plus"] = "PASS"
        else:
            notes.append(f"faq_schema has {count} Q&As")

    # faq H2 sections visible
    h2_questions = [
        h2 for h2 in soup.find_all("h2")
        if any(kw in h2.get_text(strip=True).lower()
               for kw in ("what is", "how do i", "how to", " vs", "versus"))
    ]
    if len(h2_questions) >= 2:
        r["faq_h2_sections"] = "PASS"
    else:
        notes.append(f"only {len(h2_questions)} H2 Q&A sections found")

    # footer date
    footer_left = soup.find(class_="footer-left")
    if footer_left and "Published" in footer_left.get_text():
        r["footer_date"] = "PASS"

    return r, notes


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    to_csv = "--csv" in sys.argv
    fails_only = "--fails" in sys.argv
    bundles = "--bundles" in sys.argv

    if bundles:
        files = sorted(BUNDLES_DIR.glob("*.html"))
        active_checks = BUNDLE_CHECKS
        check_fn = check_bundle_file
    else:
        files = sorted(SKILLS_DIR.glob("*.html"))
        active_checks = CHECKS
        check_fn = check_file

    rows = []
    for f in files:
        checks, notes = check_fn(f)
        pass_n = sum(1 for v in checks.values() if v == "PASS")
        total_n = sum(1 for v in checks.values() if v != "SKIP")
        fail_list = [c for c in active_checks if checks.get(c) == "FAIL"]
        rows.append({
            "file": f.name,
            "pass": pass_n,
            "total": total_n,
            "checks": checks,
            "fails": fail_list,
            "notes": "; ".join(notes),
        })

    llms_ok = LLMS_TXT.exists()

    if to_csv:
        fieldnames = ["file", "score"] + active_checks + ["notes"]
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "file": row["file"],
                "score": f"{row['pass']}/{row['total']}",
                **row["checks"],
                "notes": row["notes"],
            })
        return

    col = 36
    header = f"{'FILE':<{col}} {'SCORE':<8}" + "  ".join(f"{c[:14]:<14}" for c in active_checks)
    print("\n" + header)
    print("-" * len(header))

    shown = 0
    for row in rows:
        if fails_only and not row["fails"]:
            continue
        score_str = f"{row['pass']}/{row['total']}"
        icon = "✅" if not row["fails"] else ("⚠️ " if row["pass"] / max(row["total"], 1) >= 0.7 else "❌")
        cells = "  ".join(
            f"{STATUS.get(row['checks'].get(c, 'FAIL'), '?'):<14}" for c in active_checks
        )
        print(f"{row['file']:<{col}} {icon} {score_str:<6} {cells}")
        if row["notes"]:
            print(f"  {'':>{col}} {'':8} {row['notes']}")
        shown += 1

    all_pass = sum(1 for r in rows if not r["fails"])
    print(f"\n{'=' * 60}")
    print(f"Files checked : {len(rows)}")
    print(f"All checks pass: {all_pass}/{len(rows)}")
    print(f"llms.txt present: {'✅' if llms_ok else '❌'}")
    if fails_only and shown == 0:
        print("No failures found.")

if __name__ == "__main__":
    main()
