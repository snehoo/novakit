#!/usr/bin/env python3
"""
aeo_apply.py — Apply AEO fixes to all NovaKit skill and bundle pages.

Changes per page (skips already-patched pages):
  1. Product schema: add @id, datePublished, dateModified, SoftwareApplication type, fix seller @id
  2. HowTo schema: inject for the "How it works" <ol>
  3. FAQPage schema + visible HTML: expand to 4+ Q&A pairs for skills;
     extract from H2 sections for bundles
  4. BreadcrumbList schema: inject for bundle pages (already present on skill pages)
  5. Star rating block: inject before testimonial if aggregateRating exists in schema
  6. Footer date: add "Published / Last updated" line to footer-left

Usage:
  python3 aeo_apply.py              # process all skill pages
  python3 aeo_apply.py --bundles    # process all bundle pages
  python3 aeo_apply.py --dry-run    # preview changes, write nothing
  python3 aeo_apply.py --file skills/bundles/creative-bundle.html  # single file
"""

import json
import sys
import shutil
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing beautifulsoup4...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

SKILLS_DIR = Path(__file__).parent / "skills"
BUNDLES_DIR = Path(__file__).parent / "skills" / "bundles"

# Already manually patched — skip
SKIP_FILES = {"cold-outreach-email.html"}

# 2 generic Q&As added when a page has fewer than 4 FAQ entries
GENERIC_FAQ_ADDITIONS = [
    {
        "q": "Can I edit or customise the output after I receive it?",
        "a": "Yes. The output is plain text you own and can edit freely. Most users tweak specific details or the call-to-action to fit their exact use case before sending or publishing."
    },
    {
        "q": "How specific do my inputs need to be to get a good result?",
        "a": "The more specific your input, the more precise the output. The skill asks targeted questions to gather context — answering these in detail produces noticeably better results than generic one-line inputs."
    }
]

# ── Helpers ────────────────────────────────────────────────────────────────

def fmt_month_year(date_str):
    """'2026-06-24' → 'June 2026'"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %Y")
    except ValueError:
        return date_str


def get_schemas(soup):
    """Return all parsed JSON-LD dicts plus their <script> elements."""
    results = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            results.append((json.loads(tag.string), tag))
        except (json.JSONDecodeError, TypeError):
            pass
    return results


def has_type(schema_dict, type_name):
    t = schema_dict.get("@type", "")
    return type_name in (t if isinstance(t, list) else [t])


def get_product(schemas):
    for data, tag in schemas:
        if has_type(data, "Product"):
            return data, tag
    return None, None

# ── Fix 1: Product schema ──────────────────────────────────────────────────

def patch_product_schema(soup, slug, schemas):
    product, tag = get_product(schemas)
    if product is None:
        return False

    changed = False

    # @id
    if "@id" not in product:
        product["@id"] = f"https://novakit.tech/skills/{slug}/#product"
        changed = True

    # SoftwareApplication type
    types = product.get("@type", "Product")
    if isinstance(types, str):
        types = [types]
    if "SoftwareApplication" not in types:
        product["@type"] = ["Product", "SoftwareApplication"]
        product["applicationCategory"] = "BusinessApplication"
        changed = True

    # datePublished
    if "datePublished" not in product:
        product["datePublished"] = "2026-05-01"
        changed = True

    # seller → org @id reference
    offers = product.get("offers", {})
    seller = offers.get("seller", {})
    if isinstance(seller, dict) and seller.get("@type") == "Organization" and "@id" not in seller:
        product["offers"]["seller"] = {"@id": "https://novakit.tech/#organization"}
        changed = True

    if changed:
        tag.string = json.dumps(product, separators=(",", ":"))

    return changed

# ── Fix 2: HowTo schema ────────────────────────────────────────────────────

def inject_howto_schema(soup, skill_name, schemas):
    # Skip if already present
    for data, _ in schemas:
        if has_type(data, "HowTo"):
            return False

    ol = soup.find("ol")
    if not ol:
        return False

    steps = []
    for i, li in enumerate(ol.find_all("li", recursive=False), 1):
        text = li.get_text(strip=True)
        # First clause before em-dash or period as the step name
        name = text.split("—")[0].split(".")[0].strip()[:80]
        steps.append({
            "@type": "HowToStep",
            "position": i,
            "name": name,
            "text": text
        })

    if not steps:
        return False

    howto = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": f"How to use the {skill_name}",
        "description": f"Generate professional results with the {skill_name} in three steps.",
        "step": steps
    }

    new_script = soup.new_tag("script", type="application/ld+json")
    new_script.string = "\n" + json.dumps(howto, indent=2) + "\n"

    # Insert after the BreadcrumbList script
    breadcrumb_tag = None
    for data, tag in schemas:
        if has_type(data, "BreadcrumbList"):
            breadcrumb_tag = tag
            break

    if breadcrumb_tag:
        breadcrumb_tag.insert_after(new_script)
    elif soup.head:
        soup.head.append(new_script)
    else:
        return False

    return True

# ── Fix 3: Expand FAQ ──────────────────────────────────────────────────────

def expand_faq(soup, skill_name, schemas):
    faq_data, faq_tag = None, None
    for data, tag in schemas:
        if has_type(data, "FAQPage"):
            faq_data, faq_tag = data, tag
            break

    if faq_data is None:
        return False

    existing_qs = {q["name"] for q in faq_data.get("mainEntity", [])}
    current_count = len(existing_qs)

    if current_count >= 4:
        return False

    to_add = [item for item in GENERIC_FAQ_ADDITIONS if item["q"] not in existing_qs]
    if not to_add:
        return False

    # Update schema
    for item in to_add:
        faq_data["mainEntity"].append({
            "@type": "Question",
            "name": item["q"],
            "acceptedAnswer": {"@type": "Answer", "text": item["a"]}
        })
    faq_tag.string = "\n" + json.dumps(faq_data, indent=2) + "\n"

    # Update visible FAQ HTML — find the "Quick answers" section
    faq_section = None
    for section in soup.find_all("section"):
        eyebrow = section.find(class_="section-eyebrow")
        if eyebrow and "quick answers" in eyebrow.get_text(strip=True).lower():
            faq_section = section
            break

    if faq_section:
        inner = faq_section.find(class_="inner") or faq_section
        all_ps = inner.find_all("p", recursive=False)
        # Use the div.inner's direct children to find the last <p>
        # Fall back to any p in the section
        if not all_ps:
            all_ps = inner.find_all("p")
        last_p = all_ps[-1] if all_ps else None

        for item in to_add:
            h3 = soup.new_tag("h3", style="font-size:17px;font-weight:700;color:var(--text);margin-bottom:16px;")
            h3.string = item["q"]
            p = soup.new_tag("p", style="font-size:16px;color:var(--muted);line-height:1.7;margin-bottom:24px;")
            p.string = item["a"]

            if last_p:
                last_p.insert_after(p)
                last_p.insert_after(h3)
                last_p = p
            else:
                inner.append(h3)
                inner.append(p)

    return True

# ── Fix 4: Star rating display ─────────────────────────────────────────────

def inject_star_rating(soup, schemas):
    product, _ = get_product(schemas)
    if product is None or "aggregateRating" not in product:
        return False

    pq_inner = soup.find(class_="pq-inner")
    if not pq_inner:
        return False

    if "★" in pq_inner.get_text():
        return False  # already present

    ar = product["aggregateRating"]
    rating = ar.get("ratingValue", "4.9")
    count = ar.get("reviewCount", "41")

    star_soup = BeautifulSoup(
        f'<div style="margin-bottom:20px;display:flex;flex-direction:column;align-items:center;gap:4px;">'
        f'<div style="font-size:22px;letter-spacing:2px;color:#f59e0b;">★★★★★</div>'
        f'<div style="font-size:13px;color:var(--muted);">{rating} · {count} verified ratings</div>'
        f'</div>',
        "html.parser"
    )
    pq_inner.insert(0, star_soup)
    return True

# ── Fix 5: Footer date ─────────────────────────────────────────────────────

def add_footer_date(soup, schemas):
    footer_left = soup.find(class_="footer-left")
    if not footer_left:
        return False

    if "Published" in footer_left.get_text():
        return False  # already present

    product, _ = get_product(schemas)
    date_pub = "2026-05-01"
    date_mod = "2026-06-24"
    if product:
        date_pub = product.get("datePublished", date_pub)
        date_mod = product.get("dateModified", date_mod)

    br = soup.new_tag("br")
    footer_left.append(br)
    span = soup.new_tag("span", style="font-size:12px;color:var(--faint);")
    span.string = f"Published {fmt_month_year(date_pub)} · Last updated {fmt_month_year(date_mod)}"
    footer_left.append(span)
    return True

# ── Bundle-specific helpers ────────────────────────────────────────────────

def extract_dates_from_meta(soup):
    """Pull published/modified dates from OG article meta tags."""
    pub = mod = None
    for tag in soup.find_all("meta"):
        prop = tag.get("property", "")
        if prop == "article:published_time":
            pub = tag.get("content", "")[:10]
        elif prop == "article:modified_time":
            mod = tag.get("content", "")[:10]
    return pub or "2026-05-01", mod or "2026-06-24"


def patch_bundle_product_schema(soup, slug, schemas, date_pub, date_mod):
    """Fix Product schema for bundle pages (also adds dateModified and seller)."""
    product, tag = get_product(schemas)
    if product is None:
        return False

    changed = False

    if "@id" not in product:
        product["@id"] = f"https://novakit.tech/skills/bundles/{slug}/#product"
        changed = True

    types = product.get("@type", "Product")
    if isinstance(types, str):
        types = [types]
    if "SoftwareApplication" not in types:
        product["@type"] = ["Product", "SoftwareApplication"]
        product["applicationCategory"] = "BusinessApplication"
        changed = True

    if "datePublished" not in product:
        product["datePublished"] = date_pub
        changed = True

    if "dateModified" not in product:
        product["dateModified"] = date_mod
        changed = True

    offers = product.get("offers", {})
    if "seller" not in offers:
        product["offers"]["seller"] = {"@id": "https://novakit.tech/#organization"}
        changed = True
    elif isinstance(offers.get("seller"), dict) and "@id" not in offers["seller"]:
        product["offers"]["seller"] = {"@id": "https://novakit.tech/#organization"}
        changed = True

    if changed:
        tag.string = json.dumps(product, separators=(",", ":"))

    return changed


def inject_breadcrumb_schema(soup, slug, bundle_name, schemas):
    """Inject BreadcrumbList schema for bundle pages."""
    for data, _ in schemas:
        if has_type(data, "BreadcrumbList"):
            return False  # already present

    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "NovaKit", "item": "https://novakit.tech"},
            {"@type": "ListItem", "position": 2, "name": "Skills", "item": "https://novakit.tech/#skills"},
            {"@type": "ListItem", "position": 3, "name": bundle_name,
             "item": f"https://novakit.tech/skills/bundles/{slug}"}
        ]
    }

    new_script = soup.new_tag("script", type="application/ld+json")
    new_script.string = "\n" + json.dumps(breadcrumb, indent=2) + "\n"

    # Insert after Product schema tag
    product, prod_tag = get_product(schemas)
    if prod_tag:
        prod_tag.insert_after(new_script)
    elif soup.head:
        soup.head.append(new_script)

    return True


def extract_faq_from_h2_sections(soup):
    """
    Extract Q&A pairs from bundle H2 content sections.
    Looks for H2s matching 'What is', 'How do I', 'vs' patterns.
    """
    pairs = []
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)
        # Strip italic/em markup from text
        if not any(kw in text.lower() for kw in ("what is", "how do i", "how to", " vs", "versus")):
            continue

        # Collect following sibling content until next heading
        answer_parts = []
        for sib in h2.next_siblings:
            if hasattr(sib, "name"):
                if sib.name in ("h1", "h2", "h3"):
                    break
                if sib.name == "p":
                    part = sib.get_text(strip=True)
                    if part:
                        answer_parts.append(part)
                elif sib.name == "ol":
                    items = [li.get_text(strip=True) for li in sib.find_all("li")]
                    answer_parts.append(" ".join(f"{i+1}. {t}" for i, t in enumerate(items)))

        if answer_parts:
            answer = " ".join(answer_parts)[:500]  # cap at 500 chars
            # Normalise question — ensure it ends with ?
            q = text.rstrip(".")
            if not q.endswith("?"):
                q += "?"
            pairs.append({"q": q, "a": answer})

    return pairs[:6]  # max 6


def inject_bundle_faq(soup, schemas, faq_items):
    """Inject FAQPage schema for bundle pages (schema only — H2s already visible)."""
    if not faq_items:
        return False

    for data, _ in schemas:
        if has_type(data, "FAQPage"):
            return False  # already present

    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]}
            }
            for item in faq_items
        ]
    }

    new_script = soup.new_tag("script", type="application/ld+json")
    new_script.string = "\n" + json.dumps(faq, indent=2) + "\n"

    footer = soup.find("footer")
    if footer:
        footer.insert_before(new_script)
    else:
        soup.body.append(new_script)

    return True


def add_bundle_footer_date(soup, date_pub, date_mod):
    """Add published/updated date to bundle footer-left."""
    footer_left = soup.find(class_="footer-left")
    if not footer_left:
        return False
    if "Published" in footer_left.get_text():
        return False

    br = soup.new_tag("br")
    footer_left.append(br)
    span = soup.new_tag("span", style="font-size:12px;color:var(--faint);")
    span.string = f"Published {fmt_month_year(date_pub)} · Last updated {fmt_month_year(date_mod)}"
    footer_left.append(span)
    return True


def process_bundle_file(html_path, dry_run=False):
    slug = html_path.stem
    print(f"\n{'[DRY RUN] ' if dry_run else ''}→ {html_path.name}")

    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    schemas = get_schemas(soup)

    product, _ = get_product(schemas)
    skill_name = (product or {}).get("name", slug.replace("-", " ").title())
    date_pub, date_mod = extract_dates_from_meta(soup)

    log = []

    if patch_bundle_product_schema(soup, slug, schemas, date_pub, date_mod):
        log.append("product_schema")
        schemas = get_schemas(soup)

    if inject_breadcrumb_schema(soup, slug, skill_name, schemas):
        log.append("breadcrumb_schema")
        schemas = get_schemas(soup)

    if inject_howto_schema(soup, skill_name, schemas):
        log.append("howto_schema")
        schemas = get_schemas(soup)

    faq_items = extract_faq_from_h2_sections(soup)
    if inject_bundle_faq(soup, schemas, faq_items):
        log.append(f"faq_schema({len(faq_items)})")
        schemas = get_schemas(soup)

    if add_bundle_footer_date(soup, date_pub, date_mod):
        log.append("footer_date")

    if log:
        print(f"  Applied: {', '.join(log)}")
        if not dry_run:
            bak = html_path.with_suffix(".html.bak")
            if not bak.exists():
                shutil.copy2(html_path, bak)
            html_path.write_text(str(soup), encoding="utf-8")
            print(f"  ✓ Saved  (backup: {bak.name})")
    else:
        print(f"  No changes needed.")

    return log


# ── Main processing ────────────────────────────────────────────────────────

def process_file(html_path, dry_run=False):
    slug = html_path.stem
    print(f"\n{'[DRY RUN] ' if dry_run else ''}→ {html_path.name}")

    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    schemas = get_schemas(soup)

    product, _ = get_product(schemas)
    skill_name = (product or {}).get("name", slug.replace("-", " ").title())

    log = []
    if patch_product_schema(soup, slug, schemas):
        log.append("product_schema")
        schemas = get_schemas(soup)  # re-parse after mutation

    if inject_howto_schema(soup, skill_name, schemas):
        log.append("howto_schema")
        schemas = get_schemas(soup)

    if expand_faq(soup, skill_name, schemas):
        log.append("faq_expanded")
        schemas = get_schemas(soup)

    if inject_star_rating(soup, schemas):
        log.append("star_rating")

    if add_footer_date(soup, schemas):
        log.append("footer_date")

    if log:
        print(f"  Applied: {', '.join(log)}")
        if not dry_run:
            bak = html_path.with_suffix(".html.bak")
            if not bak.exists():
                shutil.copy2(html_path, bak)
            html_path.write_text(str(soup), encoding="utf-8")
            print(f"  ✓ Saved  (backup: {bak.name})")
    else:
        print(f"  No changes needed.")

    return log


def main():
    dry_run = "--dry-run" in sys.argv
    bundles = "--bundles" in sys.argv
    specific = None
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 < len(sys.argv):
            specific = Path(sys.argv[idx + 1])

    if specific:
        files = [specific]
        is_bundle = "bundles" in str(specific)
    elif bundles:
        files = sorted(BUNDLES_DIR.glob("*.html"))
        is_bundle = True
    else:
        files = sorted(SKILLS_DIR.glob("*.html"))
        is_bundle = False

    mode = "bundles" if is_bundle else "skills"
    print(f"Mode: {mode}  |  Files: {len(files)}")

    summary = {}
    for f in files:
        if f.name in SKIP_FILES:
            print(f"Skipping {f.name} (already patched)")
            continue
        if is_bundle or "bundles" in str(f):
            summary[f.name] = process_bundle_file(f, dry_run=dry_run)
        else:
            summary[f.name] = process_file(f, dry_run=dry_run)

    print(f"\n{'=' * 55}")
    print(f"Processed : {len(summary)} files")
    changed = [k for k, v in summary.items() if v]
    print(f"Changed   : {len(changed)}")
    if dry_run:
        print("(dry-run — nothing written)")


if __name__ == "__main__":
    main()
