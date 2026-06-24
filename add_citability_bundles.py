#!/usr/bin/env python3
"""
Bulk-adds AI-citability elements (definition sentence, a crawlable comparison
table of included skills, dateModified, last-updated footer line) to every
bundle page in skills/bundles/*.html.

Idempotent: skips any file that already contains the CITABILITY_MARKER.
Run: python3 add_citability_bundles.py [--dry-run] [files...]
"""
import re
import sys
import glob

CITABILITY_MARKER = "<!-- citability-v1 -->"
LAST_UPDATED = "June 24, 2026"
LAST_UPDATED_ISO = "2026-06-24"


def process_file(path, dry_run=False):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if CITABILITY_MARKER in content:
        return "skip (already processed)"

    # --- extract bundle name / skill count / bundle price from the hero pill/eyebrow ---
    # Two known class-naming variants across bundle pages: hero-pill/hero-dot, or bh-eyebrow/bh-dot.
    m = re.search(r'<div class="(?:hero-dot|bh-dot)"></div>([^·<]+)·\s*(\d+)\s*Claude Skills?\s*·\s*\$(\d+)\s*</div>', content)
    if not m:
        return "skip (could not parse hero pill/eyebrow)"
    bundle_name = m.group(1).strip()
    skill_count = m.group(2).strip()
    bundle_price = m.group(3).strip()

    individual_price = re.search(r'<div class="(?:stat-num|bh-stat-num)">\$(\d+)</div><div class="(?:stat-label|bh-stat-label)">Individual price</div>', content)
    individual_price = individual_price.group(1) if individual_price else None

    savings = re.search(r'<div class="(?:stat-num|bh-stat-num)">(\d+)%</div><div class="(?:stat-label|bh-stat-label)">You save</div>', content)
    savings = savings.group(1) if savings else None

    audience = re.search(r'Claude AI skills for ([^:]+):', content)
    audience = audience.group(1).strip() if audience else "this audience"

    definition = f"The {bundle_name} is a NovaKit bundle of {skill_count} Claude AI skills for {audience}"
    if bundle_price and individual_price:
        definition += f", ${bundle_price} instead of ${individual_price} bought separately"
        if savings:
            definition += f" — a {savings}% saving"
    definition += "."

    # --- extract skill name/price pairs for the comparison table ---
    # Two known class-naming variants: skill-name/skill-price, or sr-name/sr-price.
    pairs = re.findall(r'<div class="(?:skill-name|sr-name)">([^<]+)</div>\s*<div class="(?:skill-price|sr-price)">([^<]+)</div>', content)

    changed = False

    # 1) marker, right after <head>
    if "<head>" in content:
        content = content.replace("<head>", f"<head>\n{CITABILITY_MARKER}", 1)
        changed = True

    # 2) definition paragraph, right after .hero-sub / .bh-sub
    def_html = f'<p class="bundle-def" style="font-size:16px;color:var(--muted);line-height:1.7;margin-bottom:20px;">{definition}</p>'
    new_content, n = re.subn(
        r'(<p class="(?:hero-sub|bh-sub)">.*?</p>)',
        lambda mm: mm.group(1) + "\n" + def_html,
        content, count=1, flags=re.DOTALL,
    )
    if n:
        content = new_content
        changed = True

    # 3) comparison table, right after .skills-intro
    if pairs:
        rows = "\n".join(
            f'<tr style="border-bottom:1px solid var(--border);"><td style="padding:10px 12px 10px 0;color:var(--text);font-weight:600;">{name}</td><td style="padding:10px 0;color:var(--muted);">{price}</td></tr>'
            for name, price in pairs
        )
        table_html = f'''<table style="width:100%;max-width:640px;margin:28px 0 8px;border-collapse:collapse;font-size:15px;">
<thead><tr style="border-bottom:1px solid var(--border-s);"><th style="text-align:left;padding:10px 12px 10px 0;color:var(--muted);font-weight:600;">Skill</th><th style="text-align:left;padding:10px 0;color:var(--muted);font-weight:600;">Individual price</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
'''
        new_content, n = re.subn(
            r'(<div class="skills-intro">.*?</div>)',
            lambda mm: mm.group(1) + "\n" + table_html,
            content, count=1, flags=re.DOTALL,
        )
        if n:
            content = new_content
            changed = True

    # 4) dateModified in the Product JSON-LD (single-line minified JSON in bundle pages)
    new_content, n = re.subn(
        r'("@type":"Product",)',
        r'\1"dateModified":"' + LAST_UPDATED_ISO + '",',
        content, count=1,
    )
    if n:
        content = new_content
        changed = True

    # 5) visible "Last updated" line in the footer
    new_content, n = re.subn(
        r'(7-day refund(?: policy)?</span>)(</div>)',
        r'\1 · <span>Last updated ' + LAST_UPDATED + r'</span>\2',
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
    files = args if args else sorted(glob.glob("skills/bundles/*.html"))

    for path in files:
        result = process_file(path, dry_run=dry_run)
        print(f"{path}: {result}")


if __name__ == "__main__":
    main()
