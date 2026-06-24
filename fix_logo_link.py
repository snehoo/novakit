#!/usr/bin/env python3
"""
Fixes the nav logo not linking back to the homepage on skill/bundle pages.

Two known-good patterns already exist on most pages:
  <a class="logo" href="../index.html"><img.../><img.../></a>
  <div class="logo"><a href="../index.html"><img.../><img.../></a></div>

This finds pages using the broken pattern:
  <div class="logo"><img.../><img.../></div>   (no <a> at all)
and wraps the two logo <img> tags in an <a href="...index.html">, using the
correct relative path depending on the file's depth (skills/ vs skills/bundles/).

Idempotent: does nothing if a homepage link is already present in the logo block.
Run: python3 fix_logo_link.py [--dry-run] [files...]
"""
import re
import sys
import glob

BROKEN_RE = re.compile(
    r'(<div class="logo">\s*)(<img[^>]*class="logo-img logo-dark"[^>]*/>\s*<img[^>]*class="logo-img logo-light"[^>]*/>)(\s*</div>)',
    re.DOTALL,
)


def process_file(path, dry_run=False):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "skills/bundles/" in path.replace("\\", "/"):
        home_href = "../../index.html"
    else:
        home_href = "../index.html"

    m = BROKEN_RE.search(content)
    if not m:
        return "skip (no unlinked logo block found)"

    if f'href="{home_href}"' in m.group(0):
        return "skip (already linked)"

    fixed = m.group(1) + f'<a href="{home_href}">' + m.group(2) + "</a>" + m.group(3)
    new_content = content[: m.start()] + fixed + content[m.end():]

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return "fixed"


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    files = args if args else sorted(glob.glob("skills/*.html") + glob.glob("skills/bundles/*.html"))

    for path in files:
        result = process_file(path, dry_run=dry_run)
        print(f"{path}: {result}")


if __name__ == "__main__":
    main()
