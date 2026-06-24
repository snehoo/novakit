#!/usr/bin/env python3
"""
Bulk-adds AI-citability elements (definition sentence, "how it works" numbered
list, dateModified, mini-FAQ + FAQPage schema, last-updated footer line) to
every individual skill page in skills/*.html.

Idempotent: skips any file that already contains the CITABILITY_MARKER.
Run: python3 add_citability.py [--dry-run] [files...]
"""
import re
import sys
import glob

CITABILITY_MARKER = "<!-- citability-v1 -->"
LAST_UPDATED = "June 24, 2026"
LAST_UPDATED_ISO = "2026-06-24"


def extract(pattern, text, group=1, flags=0):
    m = re.search(pattern, text, flags)
    return m.group(group) if m else None


def build_definition(skill_name, meta_desc):
    """Turn the existing meta description into a one-sentence 'X is a...' definition."""
    if not meta_desc:
        return None
    m = re.match(r"^(?:A\s+)?Claude AI skill that (.+?)\.\s", meta_desc + " ")
    if m:
        rest = m.group(1)
        return f'{skill_name} is a Claude AI skill that {rest}.'
    first_sentence = meta_desc.split(". ")[0].rstrip(".")
    return f"{skill_name} is a Claude AI skill. {first_sentence}."


def process_file(path, dry_run=False):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if CITABILITY_MARKER in content:
        return "skip (already processed)"

    # --- extract skill name + price from the Product JSON-LD ---
    product_name = extract(r'"@type":\s*"Product".*?"name":\s*"([^"]+)"', content, flags=re.DOTALL)
    if not product_name:
        return "skip (no Product name found)"
    skill_name = re.sub(r"\s*Claude Skill$", "", product_name)

    price = extract(r'"price":\s*"([^"]+)"', content)
    price_display = None
    if price:
        price_display = f"${int(float(price))}" if float(price) == int(float(price)) else f"${price}"

    meta_desc = extract(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', content) \
        or extract(r'<meta[^>]*content="([^"]+)"[^>]*name="description"', content)

    definition = build_definition(skill_name, meta_desc)

    changed = False

    # 1) marker, right after <head>
    if "<head>" in content:
        content = content.replace("<head>", f"<head>\n{CITABILITY_MARKER}", 1)
        changed = True

    # 2) definition paragraph, right after .sh-sub
    if definition:
        def_html = f'<p class="sh-def" style="font-size:16px;color:var(--muted);line-height:1.7;margin-bottom:20px;">{definition}</p>'
        new_content, n = re.subn(
            r'(<p class="sh-sub">.*?</p>)',
            lambda m: m.group(1) + "\n" + def_html,
            content, count=1, flags=re.DOTALL,
        )
        if n:
            content = new_content
            changed = True

    # 3) "How it works" numbered section, right before .wug-section
    howitworks = f'''<!-- ══ HOW IT WORKS ══ -->
<section class="wug-section" style="padding-bottom:0;">
<div class="inner">
<div class="section-eyebrow">How it works</div>
<h2 class="section-title">How does <em>{skill_name}</em> work?</h2>
<ol style="font-size:17px;color:var(--muted);line-height:1.9;margin-top:20px;padding-left:22px;max-width:680px;">
<li>Tell Claude what you need — the skill asks 2-3 narrowing questions specific to the task.</li>
<li>The skill runs live research and structures the output before writing a single word.</li>
<li>An anti-slop quality gate checks the draft, then delivers a ready-to-use result{f" for {price_display}" if price_display else ""}.</li>
</ol>
</div>
</section>
'''
    new_content, n = content.replace('<section class="wug-section">', howitworks + '<section class="wug-section">', 1), content.count('<section class="wug-section">')
    if '<section class="wug-section">' in content:
        content = content.replace('<section class="wug-section">', howitworks + '<section class="wug-section">', 1)
        changed = True

    # 4) dateModified in the Product JSON-LD
    new_content, n = re.subn(
        r'("@type":\s*"Product",)',
        r'\1\n  "dateModified": "' + LAST_UPDATED_ISO + '",',
        content, count=1,
    )
    if n:
        content = new_content
        changed = True

    # 5) mini FAQ + FAQPage schema, right before <footer>
    faq_html = f'''<!-- ══ FAQ ══ -->
<section class="for-section" style="padding-top:0;">
<div class="inner">
<div class="section-eyebrow">Quick answers</div>
<h3 style="font-size:17px;font-weight:700;color:var(--text);margin-bottom:16px;">Do I need a paid Claude account for {skill_name}?</h3>
<p style="font-size:16px;color:var(--muted);line-height:1.7;margin-bottom:24px;">No. The free Claude plan is enough to get started and see the skill working. A Pro plan unlocks longer outputs.</p>
<h3 style="font-size:17px;font-weight:700;color:var(--text);margin-bottom:16px;">How do I install the {skill_name} skill?</h3>
<p style="font-size:16px;color:var(--muted);line-height:1.7;">Download the .skill file, open Claude, go to Customize → Skills → Upload a skill, and drop the file in. It appears in your slash-command list immediately.</p>
</div>
</section>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {{
      "@type": "Question",
      "name": "Do I need a paid Claude account for {skill_name}?",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "No. The free Claude plan is enough to get started and see the skill working. A Pro plan unlocks longer outputs."
      }}
    }},
    {{
      "@type": "Question",
      "name": "How do I install the {skill_name} skill?",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "Download the .skill file, open Claude, go to Customize → Skills → Upload a skill, and drop the file in. It appears in your slash-command list immediately."
      }}
    }}
  ]
}}
</script>
'''
    if "<footer>" in content:
        content = content.replace("<footer>", faq_html + "<footer>", 1)
        changed = True

    # 6) visible "Last updated" line in the footer
    new_content, n = re.subn(
        r'(7-day refund policy</span>)(</div>)',
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
    files = args if args else sorted(glob.glob("skills/*.html"))

    for path in files:
        result = process_file(path, dry_run=dry_run)
        print(f"{path}: {result}")


if __name__ == "__main__":
    main()
