#!/usr/bin/env python3
"""
Second-pass AI-citability fixes for skills/bundles/*.html, layered on top of
the v1 pass (add_citability_bundles.py). Adds, right after the skills section
and before the buy section:
  - a TL;DR box
  - a "What is the X Bundle?" section (question-format H2)
  - a "How do I use the X Bundle?" section with a real numbered <ol>
  - an explicit "X vs. buying skills individually" comparison section
  - datePublished + author/publisher fields on the existing Product JSON-LD

All generated copy is built from data already on the page (bundle name,
skill count/price/savings, audience, skill names + hooks) — nothing
fabricated.

Idempotent via a separate <!-- citability-v2 --> marker so it can run safely
on files already processed by the v1 script.
Run: python3 add_citability_bundles_v2.py [--dry-run] [files...]
"""
import re
import sys
import glob

MARKER = "<!-- citability-v2 -->"
DATE_PUBLISHED = "2026-01-20"


def process_file(path, dry_run=False):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER in content:
        return "skip (already processed)"

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

    names = re.findall(r'<div class="(?:skill-name|sr-name)">([^<]+)</div>', content)
    hooks = re.findall(r'<div class="(?:skill-hook|sr-hook)">([^<]+)</div>', content)
    first_hook = hooks[0].rstrip(".") + "." if hooks else ""

    if not names:
        return "skip (no skill names found)"

    if len(names) > 1:
        name_list = ", ".join(names[:-1]) + f", and {names[-1]}"
    else:
        name_list = names[0]

    changed = False

    if "<head>" in content:
        content = content.replace("<head>", f"<head>\n{MARKER}", 1)
        changed = True

    # datePublished + author/publisher on the existing Product JSON-LD
    new_content, n = re.subn(
        r'("@type":"Product",)',
        r'\1"datePublished":"' + DATE_PUBLISHED + '","author":{"@type":"Organization","name":"NovaKit","url":"https://novakit.tech"},"publisher":{"@type":"Organization","name":"NovaKit","url":"https://novakit.tech"},',
        content, count=1,
    )
    if n:
        content = new_content
        changed = True

    price_clause = ""
    if individual_price and savings:
        price_clause = f" The {skill_count} skills cost ${individual_price} bought separately — the bundle is ${bundle_price}, a {savings}% saving."

    tldr_items = [
        f"{bundle_name} bundles {skill_count} Claude AI skills for {audience}: {name_list}.",
        f"${bundle_price} instead of ${individual_price} bought individually — a {savings}% saving." if individual_price and savings else f"${bundle_price} for all {skill_count} skills.",
        "Works with a free Claude account; upload all the skill files once.",
        "Each skill still runs its own live research and quality check before writing — buying as a bundle doesn't change that.",
    ]
    tldr_html = (
        '<div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:24px 28px;margin-bottom:40px;">'
        '<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:var(--faint);margin-bottom:14px;">TL;DR</div>'
        '<ul style="margin:0;padding-left:20px;color:var(--muted);font-size:15px;line-height:1.8;">'
        + "".join(f"<li>{item}</li>" for item in tldr_items)
        + "</ul></div>"
    )

    what_is_html = (
        '<div style="margin-bottom:40px;">'
        f'<h2 style="font-family:\'Instrument Serif\',serif;font-size:clamp(28px,3.5vw,40px);line-height:1.15;letter-spacing:-0.02em;margin-bottom:16px;">What is the <em style="font-style:italic;color:var(--accent);">{bundle_name}</em>?</h2>'
        f'<p style="font-size:16px;color:var(--muted);line-height:1.75;">The {bundle_name} bundles {skill_count} Claude AI skills for {audience}: {name_list}.{(" " + first_hook) if first_hook else ""}{price_clause}</p>'
        "</div>"
    )

    steps = [
        f"Buy the {bundle_name} once — you get all {skill_count} skill files in a single download.",
        'Open Claude, go to Customize → Skills → Upload a skill, and add each file (one-time setup).',
        f"Pick whichever skill matches the task in front of you — {names[0]}" + (f" or {names[1]}" if len(names) > 1 else "") + ", for example.",
        "Each skill still runs its own live research and quality gate before writing, so the output is current every time, regardless of which skill in the bundle you use.",
    ]
    how_to_html = (
        '<div style="margin-bottom:40px;">'
        f'<h2 style="font-family:\'Instrument Serif\',serif;font-size:clamp(28px,3.5vw,40px);line-height:1.15;letter-spacing:-0.02em;margin-bottom:16px;">How do I use the <em style="font-style:italic;color:var(--accent);">{bundle_name}</em>?</h2>'
        '<ol style="font-size:16px;color:var(--muted);line-height:1.9;padding-left:22px;max-width:680px;">'
        + "".join(f"<li>{step}</li>" for step in steps)
        + "</ol></div>"
    )

    vs_html = ""
    if individual_price and savings:
        vs_html = (
            '<div style="margin-bottom:8px;">'
            f'<h2 style="font-family:\'Instrument Serif\',serif;font-size:clamp(28px,3.5vw,40px);line-height:1.15;letter-spacing:-0.02em;margin-bottom:16px;">{bundle_name} vs. <em style="font-style:italic;color:var(--accent);">buying skills individually</em></h2>'
            f'<p style="font-size:16px;color:var(--muted);line-height:1.75;">Buying {name_list} one at a time costs ${individual_price}. The {bundle_name} costs ${bundle_price} for all {skill_count} — a {savings}% saving — and every skill is available from day one instead of being added as the need comes up. See the skill-by-skill price breakdown above.</p>'
            "</div>"
        )

    section_html = (
        f'<section style="padding:0 40px 72px;background:var(--bg2);">'
        f'<div class="inner" style="max-width:1100px;margin:0 auto;padding-top:8px;">'
        f"{tldr_html}{what_is_html}{how_to_html}{vs_html}"
        "</div></section>"
    )

    new_content, n = re.subn(
        r'(<section class="buy(?:-section)?" id="buy">)',
        section_html + r"\1",
        content, count=1,
    )
    if n:
        content = new_content
        changed = True
    else:
        return "skip (could not find buy section to insert before)"

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
