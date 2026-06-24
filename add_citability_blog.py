#!/usr/bin/env python3
"""
Bulk-adds AI-citability elements to blog posts in blog/*.html:
  - a definition sentence ("X is a Claude AI skill that...") derived from the
    existing .hero-card-text box
  - an "In this guide" jump-list built from the post's real H2 headings
    (turns the existing narrative headings into a crawlable, structured list
    and gives each section a real #anchor)

Skips non-post files (index pages, stray backups, and the one orphaned
unstyled test page that doesn't use the site template at all).

Idempotent: skips any file that already contains the CITABILITY_MARKER.
Run: python3 add_citability_blog.py [--dry-run] [files...]
"""
import re
import sys
import glob

CITABILITY_MARKER = "<!-- citability-v1 -->"

EXCLUDE = {
    "index.html", "index copy.html", "index-old.html", "index-old1.html",
    "youtube-thumbnail-prompt-blog-test.html",
}


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text)
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def process_file(path, dry_run=False):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if CITABILITY_MARKER in content:
        return "skip (already processed)"

    changed = False

    # 1) marker, right after <head>
    if "<head>" in content:
        content = content.replace("<head>", f"<head>\n{CITABILITY_MARKER}", 1)
        changed = True

    # 2) definition sentence, derived from .hero-card-text ("Skill Name — description")
    definition = None
    m = re.search(r'<div class="hero-card-text">([^<]+)</div>', content)
    if m:
        raw = m.group(1).strip()
        if " — " in raw:
            skill_name, desc = raw.split(" — ", 1)
            desc = desc.strip().rstrip(".")
            definition = f"{skill_name.strip()} is a Claude AI skill — {desc}."

    # 3) "In this guide" jump list, built from real post-body H2 headings
    body_match = re.search(r'(<article class="post-body">)(.*?)(</article>)', content, re.DOTALL)
    toc_html = ""
    if body_match:
        body_inner = body_match.group(2)
        headings = re.findall(r'<h2>(.*?)</h2>', body_inner, re.DOTALL)
        if len(headings) >= 2:
            seen = set()
            new_body_inner = body_inner
            items = []
            for h in headings:
                label = re.sub(r"<[^>]+>", "", h).strip()
                slug = slugify(label)
                base_slug = slug
                i = 2
                while slug in seen:
                    slug = f"{base_slug}-{i}"
                    i += 1
                seen.add(slug)
                items.append(f'<li><a href="#{slug}" style="color:var(--accent);text-decoration:underline;text-underline-offset:3px;">{label}</a></li>')
                # add id to the matching h2 (first untagged occurrence of this exact heading)
                new_body_inner = new_body_inner.replace(f"<h2>{h}</h2>", f'<h2 id="{slug}">{h}</h2>', 1)
            content = content[:body_match.start(2)] + new_body_inner + content[body_match.end(2):]
            # Definition sentence (if found) leads the box instead of sitting in its
            # own paragraph — it would otherwise just repeat .hero-card-text shown
            # immediately above on the page.
            def_line = f'<p style="font-size:15px;color:var(--text);line-height:1.6;margin-bottom:16px;">{definition}</p>' if definition else ""
            toc_html = (
                '<div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:24px 28px;margin-bottom:36px;">'
                '<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:var(--faint);margin-bottom:14px;">In this guide</div>'
                f'{def_line}'
                f'<ol style="margin:0;padding-left:20px;color:var(--muted);font-size:15px;line-height:1.9;">{"".join(items)}</ol>'
                "</div>"
            )
            changed = True

    if toc_html:
        # Insert *inside* <article class="post-body"> (not before it) so the box
        # inherits the article's max-width/padding instead of going full-bleed.
        new_content, n = re.subn(
            r'(<article class="post-body">)',
            r'\1' + toc_html,
            content, count=1,
        )
        if n:
            content = new_content
            changed = True

    if not changed:
        return "skip (no insertion points matched)"

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return "updated"


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    if args:
        files = args
    else:
        files = sorted(
            p for p in glob.glob("blog/*.html")
            if p.split("/", 1)[1] not in EXCLUDE
        )

    for path in files:
        result = process_file(path, dry_run=dry_run)
        print(f"{path}: {result}")


if __name__ == "__main__":
    main()
