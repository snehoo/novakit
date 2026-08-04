#!/usr/bin/env python3
"""
aeo_master_patch.py — AEO Master SOP v1.1 batch fixer for novakit.tech

Run from the repo root:
    python3 aeo_master_patch.py              # patch everything
    python3 aeo_master_patch.py --dry-run    # preview, write nothing
    python3 aeo_master_patch.py --only org   # just fix org schema on index.html
    python3 aeo_master_patch.py --only robots
    python3 aeo_master_patch.py --only llms
    python3 aeo_master_patch.py --only author
    python3 aeo_master_patch.py --only blog-schema

Patches applied (all invisible-layer — no approval gate needed per SOP §9):
  [org]         Upgrade Organization schema on index.html
                  - logo → ImageObject
                  - expand sameAs (LinkedIn, GitHub, directories)
                  - add knowsAbout array
                  - add description + email
  [person]      Add / upgrade Person schema for Snehal Patel on about.html
  [author]      Normalise author name + @id across all blog posts
                  "NovaKit Team" → "Snehal Patel" with stable Person @id
  [robots]      Add OAI-SearchBot + Anthropic-AI to robots.txt
  [llms]        Add compare pages section + fix price range in llms.txt
  [blog-schema] Inject Article + BreadcrumbList schema into blog posts
                  that are missing them entirely
"""

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

try:
    from bs4 import BeautifulSoup, NavigableString
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup, NavigableString

# ── Config ─────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent
TODAY = date.today().isoformat()          # e.g. "2026-08-04"

DOMAIN = "https://novakit.tech"
ORG_ID = f"{DOMAIN}/#organization"
AUTHOR_ID = f"{DOMAIN}/#author-snehal-patel"
AUTHOR_NAME = "Snehal Patel"
AUTHOR_URL = f"{DOMAIN}/about"
AUTHOR_LINKEDIN = "https://www.linkedin.com/in/snehalpateldev/"

ORG_SAME_AS = [
    "https://www.youtube.com/@NovaKit-tech",
    "https://www.instagram.com/novakit.tech",
    "https://www.linkedin.com/in/snehalpateldev/",   # founder LinkedIn (brand entity)
    "https://github.com/snehoo/novakit",
    "https://theresanaiforthat.com/ai/novakit/",
    "https://www.producthunt.com/products/novakit",
]

ORG_KNOWS_ABOUT = [
    "Claude AI skills",
    "AI writing tools",
    "LinkedIn content creation",
    "cold email outreach",
    "pitch deck writing",
    "product requirement documents",
    "AI prompt engineering",
    "content marketing",
    "business writing",
]

# Blog posts to skip (already perfectly patched or special cases)
BLOG_SKIP = set()

# ── Helpers ─────────────────────────────────────────────────────────────────

def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(path, bak)


def get_schemas(soup):
    """Return list of (parsed_dict, script_tag) for all JSON-LD blocks."""
    out = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
            # Unwrap top-level arrays
            if isinstance(data, list):
                for item in data:
                    out.append((item, tag))
            else:
                out.append((data, tag))
        except (json.JSONDecodeError, TypeError):
            pass
    return out


def schema_types(d: dict):
    t = d.get("@type", "")
    return set(t if isinstance(t, list) else [t])


def find_schema(schemas, type_name):
    for d, tag in schemas:
        if type_name in schema_types(d):
            return d, tag
    return None, None


def replace_script_content(tag, data: dict):
    tag.string = "\n" + json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def append_schema_to_head(soup, data: dict):
    script = soup.new_tag("script", type="application/ld+json")
    script.string = "\n" + json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if soup.head:
        soup.head.append(script)
    return script


def slug_from_path(path: Path) -> str:
    return path.stem


def read_html(path: Path):
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def write_html(path: Path, soup, dry_run: bool):
    if dry_run:
        return
    backup(path)
    path.write_text(str(soup), encoding="utf-8")


# ── Fix: Organization schema ─────────────────────────────────────────────────

def patch_org_schema(dry_run=False):
    """
    Upgrade the Organization schema on index.html.
    - logo → proper ImageObject
    - expand sameAs
    - add knowsAbout
    - add description + email
    """
    path = ROOT / "index.html"
    if not path.exists():
        print("  SKIP index.html not found")
        return False

    soup = read_html(path)
    schemas = get_schemas(soup)
    org, org_tag = find_schema(schemas, "Organization")

    if org is None:
        print("  SKIP no Organization schema found in index.html")
        return False

    changed = False

    # logo → ImageObject
    current_logo = org.get("logo", "")
    if isinstance(current_logo, str):
        org["logo"] = {
            "@type": "ImageObject",
            "url": current_logo or f"{DOMAIN}/og-image.png",
            "width": 1200,
            "height": 630
        }
        changed = True

    # description
    if "description" not in org:
        org["description"] = (
            "NovaKit publishes premium Claude AI skill files — "
            "downloadable frameworks that give Claude live-research capability, "
            "structured interview flows, and anti-slop quality gates. "
            "70+ skills across 10 verticals, from $5."
        )
        changed = True

    # email
    if "email" not in org:
        org["email"] = "hello@novakit.tech"
        changed = True

    # sameAs — merge without duplicating
    existing_same_as = set(org.get("sameAs", []))
    new_same_as = sorted(existing_same_as | set(ORG_SAME_AS))
    if set(new_same_as) != existing_same_as:
        org["sameAs"] = new_same_as
        changed = True

    # knowsAbout
    if "knowsAbout" not in org:
        org["knowsAbout"] = ORG_KNOWS_ABOUT
        changed = True

    # @id
    if "@id" not in org:
        org["@id"] = ORG_ID
        changed = True

    if changed:
        replace_script_content(org_tag, org)
        write_html(path, soup, dry_run)
        print(f"  {'[DRY] ' if dry_run else ''}✓ Organization schema upgraded on index.html")
    else:
        print("  Organization schema already complete — no changes needed")

    return changed


# ── Fix: Person schema on about.html ─────────────────────────────────────────

PERSON_SCHEMA = {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": AUTHOR_ID,
    "name": AUTHOR_NAME,
    "url": AUTHOR_URL,
    "jobTitle": "Founder",
    "worksFor": {"@id": ORG_ID},
    "sameAs": [
        AUTHOR_LINKEDIN,
        "https://www.youtube.com/@NovaKit-tech",
    ],
    "knowsAbout": [
        "Claude AI skills",
        "AI writing tools",
        "content marketing",
        "prompt engineering",
        "SaaS product development",
    ],
    "description": (
        "Snehal Patel is the founder of NovaKit, a Claude AI skill library, "
        "and CoreMark, a Cambridge Lower Secondary exam prep platform. "
        "Both launched in early 2026."
    ),
}


def patch_person_schema(dry_run=False):
    path = ROOT / "about.html"
    if not path.exists():
        print("  SKIP about.html not found")
        return False

    soup = read_html(path)
    schemas = get_schemas(soup)
    existing_person, person_tag = find_schema(schemas, "Person")

    if existing_person and existing_person.get("@id") == AUTHOR_ID:
        # Already correct — ensure sameAs and knowsAbout are complete
        changed = False
        existing_sa = set(existing_person.get("sameAs", []))
        target_sa = set(PERSON_SCHEMA["sameAs"])
        if not target_sa.issubset(existing_sa):
            existing_person["sameAs"] = sorted(existing_sa | target_sa)
            changed = True
        if "knowsAbout" not in existing_person:
            existing_person["knowsAbout"] = PERSON_SCHEMA["knowsAbout"]
            changed = True
        if changed:
            replace_script_content(person_tag, existing_person)
            write_html(path, soup, dry_run)
            print(f"  {'[DRY] ' if dry_run else ''}✓ Person schema updated on about.html")
        else:
            print("  Person schema already complete — no changes needed")
        return changed

    if existing_person:
        # Upgrade in-place — merge fields
        for k, v in PERSON_SCHEMA.items():
            if k not in existing_person:
                existing_person[k] = v
        existing_person["@id"] = AUTHOR_ID
        replace_script_content(person_tag, existing_person)
    else:
        # Inject fresh
        append_schema_to_head(soup, PERSON_SCHEMA)

    write_html(path, soup, dry_run)
    print(f"  {'[DRY] ' if dry_run else ''}✓ Person schema added to about.html")
    return True


# ── Fix: Author normalisation across blog posts ───────────────────────────────

GENERIC_AUTHOR_NAMES = {"novakit team", "novakit", "staff", "admin", "editorial team"}

CANONICAL_AUTHOR_BLOCK = {
    "@type": "Person",
    "@id": AUTHOR_ID,
    "name": AUTHOR_NAME,
    "url": AUTHOR_URL,
    "sameAs": [AUTHOR_LINKEDIN],
}


def _normalise_author_in_schema(data: dict) -> bool:
    """Mutate author block in-place. Returns True if changed."""
    author = data.get("author")
    if not author:
        return False

    # Handle array of authors
    if isinstance(author, list):
        changed = False
        for a in author:
            if isinstance(a, dict):
                if a.get("name", "").lower().strip() in GENERIC_AUTHOR_NAMES:
                    a.update(CANONICAL_AUTHOR_BLOCK)
                    changed = True
                elif "@id" not in a and a.get("name", "").lower() == AUTHOR_NAME.lower():
                    a["@id"] = AUTHOR_ID
                    changed = True
        return changed

    if isinstance(author, dict):
        name = author.get("name", "").lower().strip()
        if name in GENERIC_AUTHOR_NAMES:
            data["author"] = CANONICAL_AUTHOR_BLOCK
            return True
        if name == AUTHOR_NAME.lower() and "@id" not in author:
            author["@id"] = AUTHOR_ID
            return True

    return False


def patch_author_across_blog(dry_run=False):
    blog_dir = ROOT / "blog"
    if not blog_dir.exists():
        print("  SKIP blog/ directory not found")
        return 0

    files = [f for f in blog_dir.glob("*.html") if f.name not in BLOG_SKIP]
    patched = 0

    for path in sorted(files):
        soup = read_html(path)
        schemas = get_schemas(soup)

        file_changed = False
        seen_tags = {}

        for data, tag in schemas:
            # Track which tags we've already updated (multiple schemas can share a tag for arrays)
            tag_id = id(tag)
            if tag_id not in seen_tags:
                seen_tags[tag_id] = (data, tag)

            if "author" in data:
                if _normalise_author_in_schema(data):
                    replace_script_content(tag, data)
                    file_changed = True

        if file_changed:
            patched += 1
            write_html(path, soup, dry_run)
            print(f"  {'[DRY] ' if dry_run else ''}✓ author normalised: {path.name}")

    print(f"  Blog author patch: {patched}/{len(files)} files updated")
    return patched


# ── Fix: Blog posts missing schema entirely ───────────────────────────────────

def _extract_title(soup) -> str:
    t = soup.find("title")
    return t.get_text(strip=True) if t else ""


def _extract_description(soup) -> str:
    m = soup.find("meta", {"name": "description"})
    if m:
        return m.get("content", "")
    m = soup.find("meta", {"property": "og:description"})
    return m.get("content", "") if m else ""


def _extract_date_published(soup) -> str:
    for prop in ("article:published_time", "datePublished"):
        m = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if m:
            return (m.get("content") or "")[:10]
    return "2026-01-15"


def _extract_date_modified(soup) -> str:
    for prop in ("article:modified_time", "dateModified"):
        m = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if m:
            return (m.get("content") or "")[:10]
    return TODAY


def _extract_canonical(soup) -> str:
    c = soup.find("link", rel="canonical")
    return c["href"] if c else ""


def _build_article_schema(slug: str, title: str, description: str,
                           date_pub: str, date_mod: str, canonical: str) -> dict:
    url = canonical or f"{DOMAIN}/blog/{slug}"
    return {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "@id": f"{url}/#article",
        "headline": title,
        "description": description,
        "datePublished": date_pub,
        "dateModified": date_mod,
        "author": CANONICAL_AUTHOR_BLOCK,
        "publisher": {"@id": ORG_ID},
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": url
        },
        "image": f"{DOMAIN}/og-image.png",
    }


def _build_breadcrumb_schema(slug: str, title: str, canonical: str) -> dict:
    url = canonical or f"{DOMAIN}/blog/{slug}"
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "NovaKit", "item": DOMAIN},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{DOMAIN}/blog"},
            {"@type": "ListItem", "position": 3, "name": title, "item": url},
        ]
    }


def _extract_faq_pairs(soup) -> list:
    """
    Pull Q&A pairs from visible FAQ sections.
    Looks for H3 elements inside a section that contains 'faq' in class/id,
    or H3s that are phrased as questions (contain '?').
    Returns list of {"q": ..., "a": ...} dicts.
    """
    pairs = []

    # Strategy 1: structured faq-item divs (the standard NovaKit pattern)
    for item in soup.find_all(class_="faq-item"):
        q_el = item.find(class_="faq-q")
        a_el = item.find(class_="faq-a-inner") or item.find(class_="faq-a")
        if q_el and a_el:
            q_text = q_el.get_text(strip=True).replace("+", "").replace("−", "").strip()
            a_text = a_el.get_text(separator=" ", strip=True)
            if q_text and a_text:
                pairs.append({"q": q_text, "a": a_text[:600]})

    if pairs:
        return pairs[:8]

    # Strategy 2: H3s followed by paragraph answers
    for h3 in soup.find_all("h3"):
        text = h3.get_text(strip=True)
        if "?" not in text:
            continue
        answer_parts = []
        for sib in h3.next_siblings:
            if isinstance(sib, NavigableString):
                continue
            if sib.name in ("h2", "h3", "h4"):
                break
            if sib.name == "p":
                part = sib.get_text(strip=True)
                if part:
                    answer_parts.append(part)
        if answer_parts:
            pairs.append({"q": text, "a": " ".join(answer_parts)[:600]})

    return pairs[:8]


def _build_faq_schema(pairs: list) -> dict:
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


def patch_blog_schema(dry_run=False):
    """
    Inject Article + BreadcrumbList (and FAQPage if content found) into
    blog posts that are missing them.
    Already-patched posts are skipped cleanly.
    """
    blog_dir = ROOT / "blog"
    if not blog_dir.exists():
        print("  SKIP blog/ directory not found")
        return 0

    files = [f for f in blog_dir.glob("*.html") if f.name not in BLOG_SKIP]
    injected = 0
    already_ok = 0

    for path in sorted(files):
        soup = read_html(path)
        schemas = get_schemas(soup)

        has_article = any("Article" in schema_types(d) or "BlogPosting" in schema_types(d)
                          for d, _ in schemas)
        has_breadcrumb = any("BreadcrumbList" in schema_types(d) for d, _ in schemas)

        if has_article and has_breadcrumb:
            already_ok += 1
            continue

        slug = slug_from_path(path)
        title = _extract_title(soup)
        description = _extract_description(soup)
        date_pub = _extract_date_published(soup)
        date_mod = _extract_date_modified(soup)
        canonical = _extract_canonical(soup)

        added = []

        if not has_article:
            article = _build_article_schema(slug, title, description, date_pub, date_mod, canonical)
            append_schema_to_head(soup, article)
            added.append("Article")

        if not has_breadcrumb:
            breadcrumb = _build_breadcrumb_schema(slug, title, canonical)
            append_schema_to_head(soup, breadcrumb)
            added.append("BreadcrumbList")

        # FAQ — only inject if not already there and we found pairs
        has_faq = any("FAQPage" in schema_types(d) for d, _ in schemas)
        if not has_faq:
            pairs = _extract_faq_pairs(soup)
            if len(pairs) >= 2:
                faq = _build_faq_schema(pairs)
                append_schema_to_head(soup, faq)
                added.append(f"FAQPage({len(pairs)}q)")

        if added:
            injected += 1
            write_html(path, soup, dry_run)
            print(f"  {'[DRY] ' if dry_run else ''}✓ {path.name} → {', '.join(added)}")

    print(f"  Blog schema: {injected} posts patched, {already_ok} already complete")
    return injected


# ── Fix: robots.txt ───────────────────────────────────────────────────────────

ROBOTS_ADDITIONS = {
    "OAI-SearchBot": "Allow: /",      # OpenAI browsing agent
    "Anthropic-AI": "Allow: /",       # Anthropic crawler
    "CCBot": "Allow: /",              # Common Crawl (feeds many LLM training sets)
    "Bytespider": "Allow: /",         # TikTok/ByteDance AI crawler
}


def patch_robots(dry_run=False):
    path = ROOT / "robots.txt"
    if not path.exists():
        print("  SKIP robots.txt not found")
        return False

    content = path.read_text(encoding="utf-8")
    additions = []

    for agent, directive in ROBOTS_ADDITIONS.items():
        if f"User-agent: {agent}" not in content:
            additions.append(f"\nUser-agent: {agent}\n{directive}")

    if not additions:
        print("  robots.txt already has all required crawlers")
        return False

    new_content = content.rstrip() + "\n" + "\n".join(additions) + "\n"

    if dry_run:
        agents_to_add = [a for a in ROBOTS_ADDITIONS if f"User-agent: {a}" not in content]
        print(f"  [DRY] robots.txt would add: {agents_to_add}")
        return True

    backup(path)
    path.write_text(new_content, encoding="utf-8")
    added_agents = [f"User-agent: {a}" for a in ROBOTS_ADDITIONS if f"User-agent: {a}" not in content]
    print(f"  ✓ robots.txt updated — added: {', '.join([a.split(': ')[1] for a in added_agents])}")
    return True


# ── Fix: llms.txt ─────────────────────────────────────────────────────────────

COMPARE_PAGES_BLOCK = """
## Comparison Guides

- [Best AI Cold Email Tools](https://novakit.tech/compare/best-cold-email-tools-2026): NovaKit vs Reply.io, Lemlist, Apollo.io, Clay, Instantly.ai
- [Best LinkedIn & Social Tools](https://novakit.tech/compare/best-linkedin-social-tools-2026): NovaKit vs Taplio, Shield, AuthoredUp, Supergrow
- [Best AI Content Creator Tools](https://novakit.tech/compare/best-content-creator-tools-2026): NovaKit vs Jasper, Copy.ai, Writesonic, Notion AI
- [Best AI Startup Founder Tools](https://novakit.tech/compare/best-startup-founder-tools-2026): NovaKit vs Notion AI, ChatGPT, Tome, Beautiful.ai
- [Best AI Real Estate Tools](https://novakit.tech/compare/best-real-estate-ai-tools-2026): NovaKit vs Listing AI, ChatGPT, RealGeeks, Luxury Presence
- [Best AI Resume & Career Tools](https://novakit.tech/compare/best-resume-career-tools-2026): NovaKit vs Kickresume, Teal, Resume.io, Enhancv
- [Best AI Legal & Business Doc Tools](https://novakit.tech/compare/best-legal-business-doc-tools-2026): NovaKit vs DoNotPay, Clio Draft, Harvey, ContractPodAi
- [Best AI Video & Podcast Tools](https://novakit.tech/compare/best-video-podcast-tools-2026): NovaKit vs Descript, Opus Clip, Riverside, Podcastle
- [Best AI Creative Writing Tools](https://novakit.tech/compare/best-creative-writing-tools-2026): NovaKit vs Sudowrite, NovelAI, Reedsy, Scrivener
- [Best AI E-commerce Product Tools](https://novakit.tech/compare/best-ecommerce-product-tools-2026): NovaKit vs Describely, Jasper Commerce, Copy.ai
- [Best AI Education & Teaching Tools](https://novakit.tech/compare/best-education-teaching-tools-2026): NovaKit vs MagicSchool AI, Eduaide.ai, Curipod
- [Best AI Event & Speech Writing Tools](https://novakit.tech/compare/best-event-speech-writing-tools-2026): NovaKit vs SpeechFlow, Speeko, ChatGPT
"""

GLOSSARY_BLOCK = """
## Glossary

- [What Is a Claude AI Skill?](https://novakit.tech/glossary/what-is-a-claude-skill): Definition, examples, and how they work
- [What Is Prompt Engineering?](https://novakit.tech/glossary/what-is-prompt-engineering): Plain-English definition and why it matters
- [What Is a UGC Ad?](https://novakit.tech/glossary/what-is-a-ugc-ad): User-generated content ads explained
- [What Is an AI PRD?](https://novakit.tech/glossary/what-is-an-ai-prd): AI-assisted product requirement documents
"""


def patch_llms_txt(dry_run=False):
    path = ROOT / "llms.txt"
    if not path.exists():
        print("  SKIP llms.txt not found")
        return False

    content = path.read_text(encoding="utf-8")
    changes = []

    # Fix price inconsistency: $5–$25 → $5+
    if "$5–$25" in content or "$5-$25" in content:
        content = content.replace("$5–$25", "$5+").replace("$5-$25", "$5+")
        changes.append("fixed price range ($5–$25 → $5+)")

    # Add compare pages block if not already there
    if "## Comparison Guides" not in content:
        content = content.rstrip() + "\n" + COMPARE_PAGES_BLOCK
        changes.append("added comparison guides section")

    # Add glossary block if not already there
    if "## Glossary" not in content:
        content = content.rstrip() + "\n" + GLOSSARY_BLOCK
        changes.append("added glossary section")

    if not changes:
        print("  llms.txt already complete — no changes needed")
        return False

    if dry_run:
        print(f"  [DRY] llms.txt would: {'; '.join(changes)}")
        return True

    backup(path)
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ llms.txt updated: {'; '.join(changes)}")
    return True


# ── Runner ────────────────────────────────────────────────────────────────────

PATCHES = {
    "org":         ("Organization schema",         patch_org_schema),
    "person":      ("Person schema (Snehal Patel)", patch_person_schema),
    "author":      ("Author normalisation (blog)",  patch_author_across_blog),
    "blog-schema": ("Blog missing schema",          patch_blog_schema),
    "robots":      ("robots.txt",                   patch_robots),
    "llms":        ("llms.txt",                     patch_llms_txt),
}


def main():
    dry_run = "--dry-run" in sys.argv

    # Which patches to run
    only = None
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        if idx + 1 < len(sys.argv):
            only = sys.argv[idx + 1]
            if only not in PATCHES:
                print(f"Unknown patch key '{only}'. Valid keys: {list(PATCHES)}")
                sys.exit(1)

    targets = {only: PATCHES[only]} if only else PATCHES

    print(f"\n{'=' * 60}")
    print(f"AEO Master Patch — novakit.tech")
    print(f"Mode  : {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Date  : {TODAY}")
    print(f"Targets: {', '.join(targets)}")
    print(f"{'=' * 60}\n")

    for key, (label, fn) in targets.items():
        print(f"[{key}] {label}")
        fn(dry_run=dry_run)
        print()

    print("Done.")
    if dry_run:
        print("Re-run without --dry-run to write changes.")


if __name__ == "__main__":
    main()
