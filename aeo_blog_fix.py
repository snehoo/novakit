#!/usr/bin/env python3
"""
aeo_blog_fix.py — Apply AEO schema fixes to all NovaKit blog pages.

Fixes applied per page (all invisible to readers — no approval gate per SOP §9):
  1. Article author: Organization → Person with @id and sameAs
  2. Article schema: add @id derived from canonical URL
  3. Article publisher: replace inline Organization with @id reference
  4. dateModified: update to today's date (2026-07-06)
  5. FAQPage schema: inject from .faq-list HTML if present;
                     fall back to H2-section extraction;
                     fall back to generated pairs from headline/description

Usage:
  python3 aeo_blog_fix.py                    # process all blog/*.html
  python3 aeo_blog_fix.py --dry-run          # preview changes, write nothing
  python3 aeo_blog_fix.py --skip-faq         # fixes 1-4 only
  python3 aeo_blog_fix.py --file blog/x.html # single file
  python3 aeo_blog_fix.py --backup           # write .bak before overwriting
"""

import json
import sys
import re
import shutil
from datetime import date
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

BLOG_DIR = Path(__file__).parent / "blog"
TODAY = "2026-07-06"

NOVAKIT_AUTHOR = {
    "@type": "Person",
    "@id": "https://novakit.tech/#author-novakit-team",
    "name": "NovaKit Team",
    "url": "https://novakit.tech/about",
    "sameAs": ["https://www.linkedin.com/company/novakit"]
}

NOVAKIT_PUBLISHER_REF = {"@id": "https://novakit.tech/#organization"}

# Generic fallback Q&As used when no FAQ content can be extracted
GENERIC_FAQ_PAIRS = [
    {
        "q": "Do I need a Claude subscription to use NovaKit skills?",
        "a": "Yes. NovaKit skills run inside Claude, so you need an active Claude account (free or paid). The skill is a one-time purchase from NovaKit — there are no recurring fees beyond your existing Claude plan."
    },
    {
        "q": "Can I edit the output the skill produces?",
        "a": "Yes. Every output is plain text you own and can edit freely. Most users make small tweaks — adjusting tone, swapping specific details, or updating calls-to-action — before publishing or sending."
    },
    {
        "q": "How specific do my inputs need to be to get a good result?",
        "a": "The more specific your input, the more precise the output. The skill asks targeted questions to gather context — answering these in detail produces noticeably better results than generic one-line prompts."
    },
    {
        "q": "What happens after I purchase a NovaKit skill?",
        "a": "You receive the skill file immediately. Install it in Claude via the Projects feature, then use it any time from within your Claude workspace. One purchase, unlimited uses."
    }
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_schemas(soup):
    """Return list of (parsed_dict, script_tag) for all JSON-LD blocks."""
    results = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            results.append((json.loads(tag.string), tag))
        except (json.JSONDecodeError, TypeError):
            pass
    return results


def has_type(obj, type_name):
    t = obj.get("@type", "")
    return type_name in (t if isinstance(t, list) else [t])


def get_canonical_slug(soup):
    """Extract slug from canonical tag e.g. https://novakit.tech/blog/my-post → my-post"""
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        return link["href"].rstrip("/").split("/")[-1]
    return None


def serialize(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


# ── Fix 1+2+3+4: Article schema patches ───────────────────────────────────────

def patch_article_schema(soup, schemas, slug, log):
    article_data, article_tag = None, None
    for data, tag in schemas:
        if has_type(data, "Article") or has_type(data, "BlogPosting"):
            article_data, article_tag = data, tag
            break

    if article_data is None:
        log.append("  SKIP: no Article/BlogPosting schema found")
        return False

    changed = False

    # Fix 1 — author: Organization → Person
    author = article_data.get("author", {})
    if isinstance(author, dict) and author.get("@type") == "Organization":
        article_data["author"] = NOVAKIT_AUTHOR
        log.append("  FIX author: Organization → Person")
        changed = True

    # Fix 2 — add @id to Article
    if "@id" not in article_data and slug:
        article_data["@id"] = f"https://novakit.tech/blog/{slug}/#article"
        log.append(f"  FIX @id: added /#article")
        changed = True

    # Fix 3 — publisher: replace inline Organization with @id reference
    publisher = article_data.get("publisher", {})
    if isinstance(publisher, dict) and publisher.get("@type") == "Organization":
        article_data["publisher"] = NOVAKIT_PUBLISHER_REF
        log.append("  FIX publisher: inline org → @id ref")
        changed = True

    # Fix 4 — dateModified → today
    if article_data.get("dateModified") != TODAY:
        article_data["dateModified"] = TODAY
        log.append(f"  FIX dateModified → {TODAY}")
        changed = True

    if changed:
        article_tag.string = "\n" + serialize(article_data) + "\n"

    return changed


# ── Fix 5: FAQPage schema ─────────────────────────────────────────────────────

def extract_faq_from_html(soup):
    """
    Attempt to extract Q&A pairs from the page's .faq-list > .faq-item structure.
    Returns list of {"q": str, "a": str} or [].
    """
    faq_list = soup.find(class_="faq-list")
    if not faq_list:
        return []

    pairs = []
    for item in faq_list.find_all(class_="faq-item"):
        q_el = item.find(class_="faq-q")
        a_el = item.find(class_="faq-a")
        if q_el and a_el:
            q = q_el.get_text(strip=True)
            a = a_el.get_text(strip=True)
            if q and a:
                pairs.append({"q": q, "a": a})

    return pairs


def extract_faq_from_h2_sections(soup):
    """
    Fall back: scan H2 headings with question phrasing + their first paragraph.
    Returns up to 4 pairs.
    """
    question_words = ("what", "how", "why", "who", "when", "is ", "can ", "does ", "do ", "are ")
    pairs = []
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True).lower()
        if any(text.startswith(w) for w in question_words) or text.endswith("?"):
            q = h2.get_text(strip=True).rstrip("?") + "?"
            # First paragraph sibling
            para = h2.find_next_sibling("p")
            if para:
                a = para.get_text(strip=True)
                if len(a) > 30:
                    pairs.append({"q": q, "a": a[:500]})
        if len(pairs) >= 4:
            break

    return pairs


def build_faqpage_schema(pairs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": p["q"],
                "acceptedAnswer": {"@type": "Answer", "text": p["a"]}
            }
            for p in pairs
        ]
    }


def inject_faq_schema(soup, schemas, log):
    # Skip if FAQPage already present
    for data, _ in schemas:
        if has_type(data, "FAQPage"):
            log.append("  SKIP FAQ: FAQPage schema already present")
            return False

    # Try extraction sources in priority order
    pairs = extract_faq_from_html(soup)
    source = ".faq-list"

    if len(pairs) < 2:
        pairs = extract_faq_from_h2_sections(soup)
        source = "H2 sections"

    if len(pairs) < 2:
        pairs = GENERIC_FAQ_PAIRS[:4]
        source = "generic fallback"

    # Ensure minimum 4 pairs by padding with generics
    if len(pairs) < 4:
        existing_qs = {p["q"] for p in pairs}
        for g in GENERIC_FAQ_PAIRS:
            if g["q"] not in existing_qs:
                pairs.append(g)
            if len(pairs) >= 4:
                break

    faq_schema = build_faqpage_schema(pairs[:8])

    new_script = soup.new_tag("script", type="application/ld+json")
    new_script.string = "\n" + serialize(faq_schema) + "\n"

    # Insert after BreadcrumbList script, else append to head
    inserted = False
    for data, tag in schemas:
        if has_type(data, "BreadcrumbList"):
            tag.insert_after(new_script)
            inserted = True
            break

    if not inserted and soup.head:
        soup.head.append(new_script)

    log.append(f"  FIX FAQPage: injected {len(pairs[:8])} Q&As from {source}")
    return True


# ── Per-file processor ────────────────────────────────────────────────────────

def process_file(path: Path, dry_run=False, skip_faq=False, backup=False):
    log = [f"\n{path.name}"]
    content = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    schemas = get_schemas(soup)
    slug = get_canonical_slug(soup)

    changed = False
    changed |= patch_article_schema(soup, schemas, slug, log)

    if not skip_faq:
        # Reload schemas after article patch (tag references may have updated)
        schemas = get_schemas(soup)
        changed |= inject_faq_schema(soup, schemas, log)

    if not changed:
        log.append("  OK: no changes needed")
        print("\n".join(log))
        return

    if dry_run:
        log.append("  DRY RUN: changes previewed, file not written")
        print("\n".join(log))
        return

    if backup:
        shutil.copy2(path, path.with_suffix(".html.bak"))

    path.write_text(str(soup), encoding="utf-8")
    log.append(f"  WRITTEN")
    print("\n".join(log))


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    skip_faq = "--skip-faq" in args
    backup = "--backup" in args

    single_file = None
    if "--file" in args:
        idx = args.index("--file")
        single_file = Path(args[idx + 1])

    if single_file:
        files = [single_file]
    else:
        files = sorted(BLOG_DIR.glob("*.html"))

    print(f"AEO Blog Fix — {'DRY RUN ' if dry_run else ''}{len(files)} file(s)")

    total = fixed = 0
    for f in files:
        total += 1
        try:
            process_file(f, dry_run=dry_run, skip_faq=skip_faq, backup=backup)
        except Exception as e:
            print(f"\n  ERROR {f.name}: {e}")

    print(f"\nDone. {total} files processed.")


if __name__ == "__main__":
    main()
