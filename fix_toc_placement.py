#!/usr/bin/env python3
"""
One-off fix: the "In this guide" box inserted by add_citability_blog.py landed
right BEFORE <article class="post-body"> instead of inside it, so it rendered
full-bleed (no max-width/padding) instead of matching the post column width.
Moves it inside, as the first child of the article.
"""
import re
import glob

PATTERN = re.compile(
    r'(<div style="background:var\(--surface\);border:1px solid var\(--border\);border-radius:14px;padding:24px 28px;margin-bottom:8px;">.*?</div>)\s*(<article class="post-body">)',
    re.DOTALL,
)

fixed = 0
for path in sorted(glob.glob("blog/*.html")):
    content = open(path, encoding="utf-8").read()
    new_content, n = PATTERN.subn(lambda m: m.group(2) + m.group(1), content, count=1)
    if n:
        open(path, "w", encoding="utf-8").write(new_content)
        fixed += 1
        print(f"{path}: fixed")
    else:
        if '<!-- citability-v1 -->' in content and 'In this guide' in content:
            print(f"{path}: marker present but pattern did not match (check manually)")

print(f"\ntotal fixed: {fixed}")
