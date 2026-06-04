"""
novakit_blog_fixes.py
=====================
Standalone patch file — apply these fixes to novakit_linker.py v3.

BUGS ADDRESSED
--------------
1. BLOG_SLUG_OVERRIDES missing 7 entries for renamed skill slugs
   → linker resolves wrong skill path for these 7 skills
2. Double-dot filename in sitemap + on disk
   → /blog/Your-Social-Posts-Arent-Underperforming-Your-Brief-Is..html
3. 8 mixed-case blog slugs — casing must match files on disk exactly
   → documented below for manual verification

HOW TO APPLY
------------
- Section A: drop-in replacement for your BLOG_SLUG_OVERRIDES dict
- Section B: run once to rename the double-dot file on disk
- Section C: checklist for mixed-case slugs (manual server verification)
- Section D: sitemap patch — corrected <loc> entries to copy into sitemap.xml
"""

# =============================================================================
# SECTION A — BLOG_SLUG_OVERRIDES (full replacement block)
# =============================================================================
# Replace your existing BLOG_SLUG_OVERRIDES dict in novakit_linker.py with this.
# Maps new skill slug (as it appears in /skills/*.html) → old blog filename prefix.
# The linker uses these when the blog filename doesn't match the skill slug directly.

BLOG_SLUG_OVERRIDES = {
    # ── 7 NEW entries: skill slugs renamed in the updated sitemap ──────────
    # New skill slug                 : blog files still use old naming pattern
    'grant-and-proposal-writing'    : 'grant-proposal-writing',
    'logo-brand-identity-prompt'    : 'logo-brand-identity',
    'sales-landing-page-copy'       : 'sales-page',
    'tos-privacy-policy'            : 'terms-of-service-privacy-policy',
    'university-sop'                : 'university-application-sop',
    'visa-cover-letter'             : 'visa-application-cover-letter',
    'ai-video-prompt'               : 'short-form-ai-video',

    # ── Existing overrides (keep these — add any you already had below) ────
    # Example pattern — replace with your actual existing entries:
    # 'financial-model-prompt'      : 'financial-model',
    # 'event-speech-writer'         : 'event-speech-writer',  # direct match, optional
}

# How the linker uses BLOG_SLUG_OVERRIDES (reference — do not change):
# When building the Layer 1 link from blog → skill page, the linker checks:
#   resolved_slug = BLOG_SLUG_OVERRIDES.get(skill_slug, skill_slug)
# Then scans blog files whose names start with resolved_slug.
# Without the 7 entries above, those 7 skills will either:
#   (a) link to the wrong /skills/ URL, or
#   (b) fall through to the fallback paragraph with an incorrect href


# =============================================================================
# SECTION B — RENAME double-dot file on disk (run once)
# =============================================================================
# The file:
#   /blog/Your-Social-Posts-Arent-Underperforming-Your-Brief-Is..html
# has a trailing dot before .html, making it an invalid URL.
# Rename it to remove the extra dot.

import os
import shutil

def fix_double_dot_file(blog_dir: str, dry_run: bool = True):
    """
    Renames the double-dot blog file to the correct single-dot version.

    Args:
        blog_dir: absolute path to your /blog/ folder on disk
                  e.g. '/Users/you/novakit/blog'
        dry_run:  True  → prints what would happen, touches nothing
                  False → actually renames the file
    """
    broken_name  = "Your-Social-Posts-Arent-Underperforming-Your-Brief-Is..html"
    fixed_name   = "Your-Social-Posts-Arent-Underperforming-Your-Brief-Is.html"

    broken_path  = os.path.join(blog_dir, broken_name)
    fixed_path   = os.path.join(blog_dir, fixed_name)

    if not os.path.exists(broken_path):
        print(f"[SKIP] Broken file not found at: {broken_path}")
        print(f"       Either already renamed, or blog_dir path is wrong.")
        return

    if os.path.exists(fixed_path):
        print(f"[SKIP] Target already exists: {fixed_path}")
        print(f"       Delete the duplicate before renaming.")
        return

    if dry_run:
        print(f"[DRY RUN] Would rename:")
        print(f"  FROM: {broken_path}")
        print(f"  TO:   {fixed_path}")
        print(f"  Re-run with dry_run=False to apply.")
    else:
        shutil.move(broken_path, fixed_path)
        print(f"[RENAMED] {broken_name}")
        print(f"       → {fixed_name}")


# =============================================================================
# SECTION C — Mixed-case blog slugs (manual server verification checklist)
# =============================================================================
# These 8 blog files use Title-Case or mixed-case in the sitemap.
# URLs are case-sensitive. If the actual .html files on disk use different
# casing, they will 404 when crawled.
#
# Action: SSH/FTP into your server and confirm each filename matches exactly.
# Recommended fix: rename all to lowercase and update sitemap.xml to match.

MIXED_CASE_BLOG_SLUGS = [
    # Sitemap entry (current)                                          Recommended rename
    ("The-Holiday-Greeting-Written-for-Everyone-and-Why-It-Lands-with-No-One.html",
     "the-holiday-greeting-written-for-everyone-and-why-it-lands-with-no-one.html"),

    ("The-LinkedIn-Post-That-Actually-Gets-Read-and-Why-Format-Is-Everything.html",
     "the-linkedin-post-that-actually-gets-read-and-why-format-is-everything.html"),

    ("The-Screenplay-AI-Gets-Wrong-and-What-a-Trained-Script-Skill-Fixes.html",
     "the-screenplay-ai-gets-wrong-and-what-a-trained-script-skill-fixes.html"),

    ("The-Short-Story-AI-Gets-Right-When-It-Knows-Your-Genre.html",
     "the-short-story-ai-gets-right-when-it-knows-your-genre.html"),

    ("Why-AI-Poetry-Reads-Like-a-Greeting-Card-and-How-to-Fix-It.html",
     "why-ai-poetry-reads-like-a-greeting-card-and-how-to-fix-it.html"),

    ("Why-your-second-childrens-book-doesnt-sound-like-your-first.html",
     "why-your-second-childrens-book-doesnt-sound-like-your-first.html"),

    ("Your-Brand-Voice-Is-the-One-Thing-AI-cant-fake.html",
     "your-brand-voice-is-the-one-thing-ai-cant-fake.html"),

    # This one also has the double-dot bug (fixed in Section B above)
    ("Your-Social-Posts-Arent-Underperforming-Your-Brief-Is..html",
     "your-social-posts-arent-underperforming-your-brief-is.html"),
]

def print_casing_checklist(blog_dir: str):
    """Checks which mixed-case files exist on disk and prints their status."""
    print("\n=== Mixed-case file check ===")
    for current, recommended in MIXED_CASE_BLOG_SLUGS:
        current_path     = os.path.join(blog_dir, current)
        recommended_path = os.path.join(blog_dir, recommended)
        current_exists     = os.path.exists(current_path)
        recommended_exists = os.path.exists(recommended_path)
        if recommended_exists:
            print(f"  [OK - already lowercase] {recommended}")
        elif current_exists:
            print(f"  [NEEDS RENAME] {current}")
            print(f"              → {recommended}")
        else:
            print(f"  [NOT FOUND on disk] {current}")
            print(f"  Check server — file may have different name entirely.")


def rename_mixed_case_files(blog_dir: str, dry_run: bool = True):
    """
    Renames mixed-case blog files to lowercase.

    Args:
        blog_dir: absolute path to your /blog/ folder
        dry_run:  True → preview only, False → apply renames
    """
    print(f"\n=== Renaming mixed-case files ({'DRY RUN' if dry_run else 'LIVE'}) ===")
    for current, recommended in MIXED_CASE_BLOG_SLUGS:
        if current == recommended:
            continue  # already lowercase, skip
        current_path     = os.path.join(blog_dir, current)
        recommended_path = os.path.join(blog_dir, recommended)

        if not os.path.exists(current_path):
            print(f"  [SKIP - not found] {current}")
            continue
        if os.path.exists(recommended_path):
            print(f"  [SKIP - target exists] {recommended}")
            continue
        if dry_run:
            print(f"  [DRY RUN] {current}\n           → {recommended}")
        else:
            shutil.move(current_path, recommended_path)
            print(f"  [RENAMED] {current}\n         → {recommended}")


# =============================================================================
# SECTION D — Sitemap patches (corrected <loc> entries)
# =============================================================================
# After renaming files, update these entries in sitemap.xml.

SITEMAP_FIXES = {
    # Double-dot fix
    "https://novakit.tech/blog/Your-Social-Posts-Arent-Underperforming-Your-Brief-Is..html":
    "https://novakit.tech/blog/your-social-posts-arent-underperforming-your-brief-is.html",

    # Mixed-case → lowercase
    "https://novakit.tech/blog/The-Holiday-Greeting-Written-for-Everyone-and-Why-It-Lands-with-No-One.html":
    "https://novakit.tech/blog/the-holiday-greeting-written-for-everyone-and-why-it-lands-with-no-one.html",

    "https://novakit.tech/blog/The-LinkedIn-Post-That-Actually-Gets-Read-and-Why-Format-Is-Everything.html":
    "https://novakit.tech/blog/the-linkedin-post-that-actually-gets-read-and-why-format-is-everything.html",

    "https://novakit.tech/blog/The-Screenplay-AI-Gets-Wrong-and-What-a-Trained-Script-Skill-Fixes.html":
    "https://novakit.tech/blog/the-screenplay-ai-gets-wrong-and-what-a-trained-script-skill-fixes.html",

    "https://novakit.tech/blog/The-Short-Story-AI-Gets-Right-When-It-Knows-Your-Genre.html":
    "https://novakit.tech/blog/the-short-story-ai-gets-right-when-it-knows-your-genre.html",

    "https://novakit.tech/blog/Why-AI-Poetry-Reads-Like-a-Greeting-Card-and-How-to-Fix-It.html":
    "https://novakit.tech/blog/why-ai-poetry-reads-like-a-greeting-card-and-how-to-fix-it.html",

    "https://novakit.tech/blog/Why-your-second-childrens-book-doesnt-sound-like-your-first.html":
    "https://novakit.tech/blog/why-your-second-childrens-book-doesnt-sound-like-your-first.html",

    "https://novakit.tech/blog/Your-Brand-Voice-Is-the-One-Thing-AI-cant-fake.html":
    "https://novakit.tech/blog/your-brand-voice-is-the-one-thing-ai-cant-fake.html",
}


def patch_sitemap(sitemap_path: str, dry_run: bool = True):
    """
    Applies all URL fixes to sitemap.xml in one pass.

    Args:
        sitemap_path: full path to your sitemap.xml
        dry_run: True → print diff only, False → write the file
    """
    with open(sitemap_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for old_url, new_url in SITEMAP_FIXES.items():
        if old_url in content:
            print(f"  [FIX] {old_url.split('/blog/')[-1]}\n      → {new_url.split('/blog/')[-1]}")
            content = content.replace(old_url, new_url)
        else:
            print(f"  [NOT FOUND] {old_url.split('/blog/')[-1]} — already fixed or different?")

    if content == original:
        print("\n  No changes needed — sitemap already clean.")
        return

    if dry_run:
        print(f"\n  [DRY RUN] {len(SITEMAP_FIXES)} fixes ready. Re-run with dry_run=False to write.")
    else:
        backup_path = sitemap_path + '.bak'
        shutil.copy(sitemap_path, backup_path)
        print(f"\n  [BACKUP] {backup_path}")
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [WRITTEN] {sitemap_path}")


# =============================================================================
# MAIN — run all fixes
# =============================================================================
# Set your actual paths and flip dry_run=False when ready.

if __name__ == '__main__':
    BLOG_DIR    = '/path/to/your/blog'        # ← change this
    SITEMAP     = '/path/to/your/sitemap.xml'  # ← change this
    DRY_RUN     = True                         # ← flip to False to apply

    print("=" * 60)
    print("novakit_blog_fixes.py")
    print("=" * 60)

    print("\n[1] Double-dot file rename")
    fix_double_dot_file(BLOG_DIR, dry_run=DRY_RUN)

    print("\n[2] Mixed-case file check")
    print_casing_checklist(BLOG_DIR)

    print("\n[3] Mixed-case file renames")
    rename_mixed_case_files(BLOG_DIR, dry_run=DRY_RUN)

    print("\n[4] Sitemap URL patches")
    patch_sitemap(SITEMAP, dry_run=DRY_RUN)

    print("\n[5] BLOG_SLUG_OVERRIDES — manual step")
    print("    Copy the BLOG_SLUG_OVERRIDES dict from Section A")
    print("    into novakit_linker.py, merging with any existing entries.")
    print("\nDone. Set DRY_RUN=False and re-run to apply all changes.")
