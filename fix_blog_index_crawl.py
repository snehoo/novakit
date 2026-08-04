#!/usr/bin/env python3
"""
fix_blog_index_crawl.py — Fix blog/index.html for AI crawler visibility.

The blog index renders posts via JavaScript from a POSTS array.
AI crawlers that don't execute JS see an empty <div id="posts-list">.

Fix:
  1. Parse the POSTS array from the existing JS in blog/index.html
  2. Pre-populate <div id="posts-list"> with static HTML (same structure
     the JS renders) — crawlers see all posts; JS replaces it on load
  3. Inject a <noscript> <ul> of all post links above the list as an
     additional fallback for strict no-JS crawlers

Run: python3 fix_blog_index_crawl.py [--dry-run]
"""

import re
import shutil
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

BLOG_INDEX = Path(__file__).parent / "blog" / "index.html"
DRY_RUN = "--dry-run" in sys.argv

BUNDLE_LABELS = {
    "founder": "Founder", "creator": "Creator", "marketing": "Marketing",
    "legal": "Legal/Biz", "video": "Video/Pod", "student": "Student",
    "realtor": "Realtor", "educator": "Educator", "wedding": "Wedding",
    "creative": "Creative",
}


# ── Parse POSTS array from JS ─────────────────────────────────────────────────

def extract_posts(source: str) -> list:
    """
    Pull each { file:'...', title:'...', desc:'...', skill:'...', bundle:'...', date:'...' }
    object out of the POSTS JS array.
    Uses regex on each object block — no JS eval required.
    """
    # Grab everything between `const POSTS = [` and the closing `];`
    match = re.search(r"const POSTS\s*=\s*\[(.*?)\];\s*\n", source, re.DOTALL)
    if not match:
        raise ValueError("Could not find POSTS array in blog/index.html")

    block = match.group(1)

    # Extract individual { ... } objects
    posts = []
    for obj_match in re.finditer(r"\{([^}]+)\}", block, re.DOTALL):
        obj_text = obj_match.group(1)

        def get_field(name: str) -> str:
            # Match both single and double quoted values, handle escaped quotes
            m = re.search(
                rf"""{name}\s*:\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")""",
                obj_text,
            )
            if not m:
                return ""
            val = m.group(1) if m.group(1) is not None else m.group(2)
            # Unescape JS escape sequences
            return val.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")

        post = {
            "file": get_field("file"),
            "title": get_field("title"),
            "desc": get_field("desc"),
            "skill": get_field("skill"),
            "bundle": get_field("bundle"),
            "date": get_field("date"),
        }
        if post["file"] and post["title"]:
            posts.append(post)

    return posts


# ── Generate static HTML matching the JS template ────────────────────────────

def render_post_item(p: dict) -> str:
    bundle_label = BUNDLE_LABELS.get(p["bundle"], p["bundle"].title())
    return (
        f'<a href="{p["file"]}" class="post-item">'
        f'<div class="pi-date">{p["date"]}</div>'
        f'<div class="pi-body">'
        f'<div class="pi-title">{p["title"]}</div>'
        f'<div class="pi-desc">{p["desc"]}</div>'
        f'<div class="pi-pills">'
        f'<span class="pill pill-skill">{p["skill"]}</span>'
        f'<span class="pill pill-bundle">{bundle_label}</span>'
        f'</div>'
        f'</div>'
        f'<div class="pi-arrow">→</div>'
        f'</a>'
    )


def render_noscript_list(posts: list) -> str:
    items = "\n".join(
        f'  <li><a href="{p["file"]}">{p["title"]}</a> — {p["date"]}</li>'
        for p in posts
    )
    return (
        f'<noscript>\n'
        f'<style>.posts-wrap{{display:none}}</style>\n'
        f'<div style="max-width:1200px;margin:0 auto;padding:0 40px 80px;">\n'
        f'<p style="font-size:14px;color:#888;margin-bottom:16px;">'
        f'{len(posts)} posts — enable JavaScript for search &amp; filtering</p>\n'
        f'<ul style="list-style:none;padding:0;">\n'
        f'{items}\n'
        f'</ul>\n'
        f'</div>\n'
        f'</noscript>\n'
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not BLOG_INDEX.exists():
        print(f"ERROR: {BLOG_INDEX} not found")
        sys.exit(1)

    source = BLOG_INDEX.read_text(encoding="utf-8")
    posts = extract_posts(source)
    print(f"Found {len(posts)} posts in POSTS array")

    soup = BeautifulSoup(source, "html.parser")

    # ── 1. Pre-populate #posts-list with static HTML ──────────────────────────
    posts_list_div = soup.find("div", id="posts-list")
    if not posts_list_div:
        print("ERROR: <div id='posts-list'> not found")
        sys.exit(1)

    static_html = "\n".join(render_post_item(p) for p in posts)
    posts_list_div.clear()
    posts_list_div.append(BeautifulSoup(static_html, "html.parser"))

    # ── 2. Inject <noscript> fallback before .posts-wrap ─────────────────────
    posts_wrap = soup.find("div", class_="posts-wrap")
    if posts_wrap and not soup.find("noscript"):
        noscript_html = render_noscript_list(posts)
        noscript_tag = BeautifulSoup(noscript_html, "html.parser")
        posts_wrap.insert_before(noscript_tag)

    # ── 3. Update post-count span so crawlers see the count too ──────────────
    count_span = soup.find("span", id="post-count")
    if count_span:
        n = len(posts)
        count_span.string = f"{n} posts"

    result = str(soup)

    if DRY_RUN:
        print("[DRY RUN] Would write the following changes to blog/index.html:")
        print(f"  - Pre-populated #posts-list with {len(posts)} static post items")
        print(f"  - Injected <noscript> fallback list with {len(posts)} links")
        print(f"  - Set post-count to '{len(posts)} posts'")
        return

    shutil.copy2(BLOG_INDEX, BLOG_INDEX.with_suffix(".html.bak"))
    BLOG_INDEX.write_text(result, encoding="utf-8")
    print(f"✓ blog/index.html updated")
    print(f"  - {len(posts)} posts pre-rendered as static HTML in #posts-list")
    print(f"  - <noscript> fallback list injected")
    print(f"  - Backup saved as blog/index.html.bak")


if __name__ == "__main__":
    main()
