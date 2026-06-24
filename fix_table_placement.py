#!/usr/bin/env python3
"""
One-off fix: the comparison table inserted by add_citability_bundles.py landed
right after the eyebrow div instead of after the full .skills-intro block
(h2 + intro paragraph). This moves it to the correct spot, after the intro
paragraph and before the skill-list/skill-rows div.
"""
import re
import glob

TABLE_RE = re.compile(r'\n<table style="width:100%;max-width:640px.*?</table>\n', re.DOTALL)

for path in sorted(glob.glob("skills/bundles/*.html")):
    content = open(path, encoding="utf-8").read()
    m = TABLE_RE.search(content)
    if not m:
        print(f"{path}: no table found, skipping")
        continue
    table_block = m.group(0)
    content_without_table = content[:m.start()] + "\n" + content[m.end():]

    # Re-insert right after the closing </p> of the skills-intro paragraph,
    # i.e. right before the next "<div class=\"skill-list\">" / "<div class=\"skill-rows\">".
    new_content, n = re.subn(
        r'(</p>\s*</div>\s*\n\s*<div class="(?:skill-list|skill-rows)">)',
        lambda mm: "</p>\n    </div>\n" + table_block.strip() + "\n    <div class=\"" + ("skill-list" if "skill-list" in mm.group(1) else "skill-rows") + "\">",
        content_without_table, count=1,
    )
    if n == 0:
        print(f"{path}: could not find re-insertion point, skipping")
        continue
    open(path, "w", encoding="utf-8").write(new_content)
    print(f"{path}: fixed")
