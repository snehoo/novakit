#!/usr/bin/env python3
"""
novakit_sitemap_gen.py — Sitemap Generator
===========================================
Scans the site folder structure and generates a complete sitemap.xml.

Includes:
  - Core pages (index, blog index)
  - /legal/ folder
  - /skills/ individual skill pages
  - /skills/bundles/ bundle pages
  - /blog/ all HTML posts

Excludes:
  - /modified/    (working output folder)
  - /blog1/       (old/staging folder)
  - index.html files inside subfolders (not canonical URLs)
  - Any file starting with _ or .

Usage
-----
  python3 novakit_sitemap_gen.py --root /path/to/NovaKitwebsite
  python3 novakit_sitemap_gen.py --root .

Output
------
  sitemap.xml written to the site root
"""

import argparse
from pathlib import Path
from datetime import date

BASE_URL   = "https://novakit.tech"
TODAY      = date.today().isoformat()

# Folders to skip entirely
EXCLUDED_FOLDERS = {"modified", "blog1", "node_modules", ".git", "assets"}

# Priority and changefreq rules per section
RULES = {
    "core":    {"changefreq": "weekly",   "priority": "1.0"},
    "blog":    {"changefreq": "weekly",   "priority": "0.7"},
    "skill":   {"changefreq": "monthly",  "priority": "0.8"},
    "bundle":  {"changefreq": "monthly",  "priority": "0.8"},
    "legal":   {"changefreq": "monthly",  "priority": "0.4"},
}

def url_entry(loc, rule):
    return (
        f'  <url>'
        f'<loc>{loc}</loc>'
        f'<lastmod>{TODAY}</lastmod>'
        f'<changefreq>{rule["changefreq"]}</changefreq>'
        f'<priority>{rule["priority"]}</priority>'
        f'</url>'
    )

def scan_folder(folder, base_path, exclude_index=True):
    """Return sorted list of .html files in a folder."""
    if not folder.exists():
        return []
    files = sorted(folder.glob("*.html"))
    result = []
    for f in files:
        if f.name.startswith(("_", ".")):
            continue
        if exclude_index and f.stem.lower() in ("index", "index 2"):
            continue
        result.append(f)
    return result


def main():
    parser = argparse.ArgumentParser(description="Novakit Sitemap Generator")
    parser.add_argument("--root", required=True, help="Path to site root folder")
    args = parser.parse_args()

    root = Path(args.root)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
             '']

    # ── Core pages ────────────────────────────────────────────────────────────
    lines.append("  <!-- Core pages -->")
    lines.append(url_entry(f"{BASE_URL}/", RULES["core"]))
    lines.append(url_entry(f"{BASE_URL}/blog/", {**RULES["blog"], "priority": "0.8"}))
    lines.append('')

    # ── Legal folder ─────────────────────────────────────────────────────────
    legal_dir = root / "legal"
    legal_files = scan_folder(legal_dir, root)
    if legal_files:
        lines.append("  <!-- Legal -->")
        for f in legal_files:
            loc = f"{BASE_URL}/legal/{f.name}"
            lines.append(url_entry(loc, RULES["legal"]))
        lines.append('')

    # ── Individual skill pages ────────────────────────────────────────────────
    skills_dir  = root / "skills"
    skill_files = scan_folder(skills_dir, root)
    if skill_files:
        lines.append("  <!-- Individual Skills -->")
        for f in skill_files:
            loc = f"{BASE_URL}/skills/{f.name}"
            lines.append(url_entry(loc, RULES["skill"]))
        lines.append('')

    # ── Bundle pages ──────────────────────────────────────────────────────────
    bundles_dir  = root / "skills" / "bundles"
    bundle_files = scan_folder(bundles_dir, root)
    if bundle_files:
        lines.append("  <!-- Bundles -->")
        for f in bundle_files:
            loc = f"{BASE_URL}/skills/bundles/{f.name}"
            lines.append(url_entry(loc, RULES["bundle"]))
        lines.append('')

    # ── Blog posts ────────────────────────────────────────────────────────────
    blog_dir   = root / "blog"
    blog_files = scan_folder(blog_dir, root)
    if blog_files:
        lines.append("  <!-- Blog posts -->")
        for f in blog_files:
            loc = f"{BASE_URL}/blog/{f.name}"
            lines.append(url_entry(loc, RULES["blog"]))
        lines.append('')

    lines.append("</urlset>")

    sitemap = "\n".join(lines)
    out_path = root / "sitemap.xml"
    out_path.write_text(sitemap, encoding="utf-8")

    # Summary
    skill_count  = len(skill_files)
    bundle_count = len(bundle_files)
    blog_count   = len(blog_files)
    legal_count  = len(legal_files)
    total        = 2 + legal_count + skill_count + bundle_count + blog_count

    print(f"\n✅  sitemap.xml written → {out_path}")
    print(f"\n   Core pages  : 2")
    print(f"   Legal       : {legal_count}")
    print(f"   Skills      : {skill_count}")
    print(f"   Bundles     : {bundle_count}")
    print(f"   Blog posts  : {blog_count}")
    print(f"   ─────────────────")
    print(f"   Total URLs  : {total}\n")

    if not legal_files:
        print("   ⚠  /legal/ folder not found or empty")
    if not skill_files:
        print("   ⚠  /skills/ folder not found or empty")
    if not blog_files:
        print("   ⚠  /blog/ folder not found or empty")


if __name__ == "__main__":
    main()
