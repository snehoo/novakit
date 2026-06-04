#!/usr/bin/env python3
"""
add_gtag.py
Injects Google Analytics tag immediately after <head> in every HTML file.
Modifies files IN PLACE.

Usage:
  python3 add_gtag.py --test index.html   # test single file
  python3 add_gtag.py                      # full run
"""

import argparse
from pathlib import Path

GTAG = """<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-E9HFQ33F0Y"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-E9HFQ33F0Y');
</script>"""

SKIP_DIRS  = {'node_modules', '.git', 'modified', 'checkout_old', 'delivery-old'}
SKIP_FILES = {'novakit-admin.html'}

def patch_file(path):
    html = path.read_text(encoding='utf-8')

    if 'G-E9HFQ33F0Y' in html:
        return 'SKIP — already has gtag'

    lower = html.lower()
    idx = lower.find('<head>')
    if idx == -1:
        idx = lower.find('<head ')
        if idx == -1:
            return 'SKIP — no <head> tag found'
        insert_at = lower.find('>', idx) + 1
    else:
        insert_at = idx + len('<head>')

    html = html[:insert_at] + '\n' + GTAG + '\n' + html[insert_at:]
    path.write_text(html, encoding='utf-8')
    return 'OK'

def find_html_files(root):
    files = []
    for path in Path(root).rglob('*.html'):
        if set(path.parts) & SKIP_DIRS:
            continue
        if path.name in SKIP_FILES:
            continue
        files.append(path)
    return sorted(files)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--test', metavar='FILE')
    args = parser.parse_args()

    if args.test:
        src = Path(args.root) / args.test
        if not src.exists():
            print(f'File not found: {src}')
            return
        status = patch_file(src)
        print(f"{'✓' if status == 'OK' else '–'} {args.test} → {status}")
        return

    files = find_html_files(args.root)
    ok = skip = 0
    for path in files:
        status = patch_file(path)
        icon = '✓' if status == 'OK' else '–'
        print(f"{icon} {path} → {status}")
        if status == 'OK': ok += 1
        else: skip += 1

    print(f"\n{'─'*50}")
    print(f"Done — {ok} patched, {skip} skipped")

if __name__ == '__main__':
    main()
