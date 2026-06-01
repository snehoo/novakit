#!/usr/bin/env python3
"""
novakit_blog_audit.py — Missing Blog Scanner
=============================================
Scans your /blog folder and flags which skills don't have
a corresponding blog file.

Usage
-----
  python3 novakit_blog_audit.py --blogs ./blog

Output
------
  Prints a report to terminal
  Writes missing-blogs.txt with the list of unmatched skills
"""

import argparse
from pathlib import Path

# ── All 63 skill slugs ────────────────────────────────────────────────────────

ALL_SKILLS = [
    # Founder
    "pitch-deck-narrative", "cold-outreach-email", "sales-page",
    "business-plan", "investor-update-email", "job-description-writer",
    "executive-bio", "one-pager-investor-brief",
    # Creator
    "brand-voice-guide", "linkedin-post-engine", "social-content-engine",
    "twitter-x-thread-engine", "seo-blog-post-brief", "email-newsletter-engine",
    "content-calendar",
    # Marketing
    "ugc-ad-creator", "brand-ad-copy", "pr-press-release",
    "ecommerce-product-listing", "product-photography-prompt",
    # Legal/Biz
    "financial-model-prompt", "grant-proposal-writing", "nda-contract-draft",
    "terms-of-service-privacy-policy", "visa-application-cover-letter",
    # Video/Pod
    "short-form-ai-video", "video-script", "ai-animation-film-prompt",
    "product-ad-film-prompt", "dialogue-character-film-prompt",
    "podcast-episode-script", "webinar-online-event-script",
    "youtube-thumbnail-prompt", "podcast-show-notes",
    # Student
    "university-application-sop", "resume-cv-builder", "cover-letter-writer",
    "research-paper-outline", "conference-abstract",
    # Realtor
    "real-estate-listing-copy", "real-estate-photo-prompt",
    "hotel-airbnb-listing-copy",
    # Educator
    "course-curriculum-builder", "lesson-plan-builder", "exam-paper-generator",
    # Wedding
    "wedding-vows-writer", "wedding-invitation-prompt",
    "event-speech-writer", "menu-description-copy",
    # Creative
    "screenplay-script", "children-book-prompt", "short-story-prompt",
    "poetry-verse-prompt", "book-cover-prompt",
    "festival-holiday-greeting-prompt",
    # Standalone
    "prd-writer", "architecture-diagram-prompt", "logo-brand-identity",
    "performance-review-writer", "social-media-carousel-prompt",
    "health-wellness-plan", "travel-itinerary-planner",
    "recipe-development-prompt", "home-renovation-brief", "eulogy-writer",
]

# Known filename → skill mappings from novakit_linker.py
# Lets the audit recognise blogs whose filenames don't contain the slug
KNOWN_OVERRIDES = {
    "The-Holiday-Greeting-Written-for-Everyone-and-Why-It-Lands-with-No-One": "festival-holiday-greeting-prompt",
    "The-Screenplay-AI-Gets-Wrong-and-What-a-Trained-Script-Skill-Fixes":     "screenplay-script",
    "The-Short-Story-AI-Gets-Right-When-It-Knows-Your-Genre":                 "short-story-prompt",
    "Why-AI-Poetry-Reads-Like-a-Greeting-Card-and-How-to-Fix-It":             "poetry-verse-prompt",
    "Why-your-second-childrens-book-doesnt-sound-like-your-first":            "children-book-prompt",
    "childrens-book-prompt":                                                   "children-book-prompt",
    "the-book-cover-brief-your-designer-actually-needs":                       "book-cover-prompt",
    "why-your-book-cover-looks-wrong":                                         "book-cover-prompt",
    "The-LinkedIn-Post-That-Actually-Gets-Read-and-Why-Format-Is-Everything": "linkedin-post-engine",
    "Your-Brand-Voice-Is-the-One-Thing-AI-cant-fake":                         "brand-voice-guide",
    "Your-Social-Posts-Arent-Underperforming-Your-Brief-Is.":                 "social-content-engine",
    "seo-brief-for-freelancers":                                               "seo-blog-post-brief",
    "email-newsletter-subject-lines":                                          "email-newsletter-engine",
    "why-cold-emails-get-deleted":                                             "cold-outreach-email",
    "financial-model-why-spreadsheets-arent-the-problem":                     "financial-model-prompt",
    "visa-cover-letter-questions-answered":                                    "visa-application-cover-letter",
    "how-to-write-ai-film-prompts-that-actually-work":                        "ai-animation-film-prompt",
    "the-ai-film-prompt-that-gives-sora-a-character-not-just-a-scene":        "dialogue-character-film-prompt",
    "podcast-scripted-vs-outlined-vs-improvised":                             "podcast-episode-script",
    "the-podcast-script-that-sounds-like-you-wrote-it-not-like-youre-reading-it": "podcast-episode-script",
    "how-to-write-real-estate-listing":                                        "real-estate-listing-copy",
    "airbnb-listing-copy-you-vs-ai-vs-calibrated-skill":                      "hotel-airbnb-listing-copy",
    "the-airbnb-listing-that-gets-booked-before-anyone-asks-about-parking":   "hotel-airbnb-listing-copy",
    "how-to-write-wedding-vows-with-ai-that-actually-sound-like-you":         "wedding-vows-writer",
    "the-vows-that-sound-like-you-wrote-them-because-you-did":                "wedding-vows-writer",
    "the-wedding-speech-that-sounds-like-you-not-like-a-template":            "event-speech-writer",
    "wedding-invitation-your-invitation-sets-the-tone":                       "wedding-invitation-prompt",
    "why-menu-copy-fails-to-sell-food":                                       "menu-description-copy",
    "online-course-curriculum-completion":                                     "course-curriculum-builder",
    "why-ai-lesson-plans-fail-the-learning-objective-test":                   "lesson-plan-builder",
    "why-your-research-paper-structure-fails-peer-review":                    "research-paper-outline",
    # Excluded non-skill pages
    "index":   None,
    "index 2": None,
}

BUNDLE_MAP = {
    "pitch-deck-narrative": "Founder",       "cold-outreach-email": "Founder",
    "sales-page": "Founder",                 "business-plan": "Founder",
    "investor-update-email": "Founder",      "job-description-writer": "Founder",
    "executive-bio": "Founder",              "one-pager-investor-brief": "Founder",
    "brand-voice-guide": "Creator",          "linkedin-post-engine": "Creator",
    "social-content-engine": "Creator",      "twitter-x-thread-engine": "Creator",
    "seo-blog-post-brief": "Creator",        "email-newsletter-engine": "Creator",
    "content-calendar": "Creator",           "ugc-ad-creator": "Marketing",
    "brand-ad-copy": "Marketing",            "pr-press-release": "Marketing",
    "ecommerce-product-listing": "Marketing","product-photography-prompt": "Marketing",
    "financial-model-prompt": "Legal/Biz",   "grant-proposal-writing": "Legal/Biz",
    "nda-contract-draft": "Legal/Biz",       "terms-of-service-privacy-policy": "Legal/Biz",
    "visa-application-cover-letter": "Legal/Biz",
    "short-form-ai-video": "Video/Pod",      "video-script": "Video/Pod",
    "ai-animation-film-prompt": "Video/Pod", "product-ad-film-prompt": "Video/Pod",
    "dialogue-character-film-prompt": "Video/Pod",
    "podcast-episode-script": "Video/Pod",   "webinar-online-event-script": "Video/Pod",
    "youtube-thumbnail-prompt": "Video/Pod", "podcast-show-notes": "Video/Pod",
    "university-application-sop": "Student", "resume-cv-builder": "Student",
    "cover-letter-writer": "Student",        "research-paper-outline": "Student",
    "conference-abstract": "Student",        "real-estate-listing-copy": "Realtor",
    "real-estate-photo-prompt": "Realtor",   "hotel-airbnb-listing-copy": "Realtor",
    "course-curriculum-builder": "Educator", "lesson-plan-builder": "Educator",
    "exam-paper-generator": "Educator",      "wedding-vows-writer": "Wedding",
    "wedding-invitation-prompt": "Wedding",  "event-speech-writer": "Wedding",
    "menu-description-copy": "Wedding",      "screenplay-script": "Creative",
    "children-book-prompt": "Creative",      "short-story-prompt": "Creative",
    "poetry-verse-prompt": "Creative",       "book-cover-prompt": "Creative",
    "festival-holiday-greeting-prompt": "Creative",
}


def resolve_skill(stem):
    """Return skill slug for a blog filename stem, or None if excluded/unknown."""
    if stem in KNOWN_OVERRIDES:
        return KNOWN_OVERRIDES[stem]
    if stem in ALL_SKILLS:
        return stem
    candidates = [s for s in ALL_SKILLS if s in stem or stem in s]
    if candidates:
        return max(candidates, key=len)
    return "UNKNOWN"


def main():
    parser = argparse.ArgumentParser(description="Novakit Missing Blog Audit")
    parser.add_argument("--blogs", required=True, help="Path to blog folder")
    args = parser.parse_args()

    blogs_dir = Path(args.blogs)
    blog_files = sorted(blogs_dir.glob("*.html"))

    # Build a set of covered skill slugs
    covered  = set()
    unknown  = []

    for f in blog_files:
        slug = resolve_skill(f.stem)
        if slug is None:
            continue          # explicitly excluded (index.html etc.)
        if slug == "UNKNOWN":
            unknown.append(f.name)
        else:
            covered.add(slug)

    missing = [s for s in ALL_SKILLS if s not in covered]

    # ── Group missing by bundle ──────────────────────────────────────────────
    by_bundle = {}
    for slug in missing:
        bundle = BUNDLE_MAP.get(slug, "Standalone")
        by_bundle.setdefault(bundle, []).append(slug)

    # ── Print report ─────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  NOVAKIT BLOG AUDIT")
    print("═" * 60)
    print(f"  Blog files found   : {len(blog_files)}")
    print(f"  Skills covered     : {len(covered)} / {len(ALL_SKILLS)}")
    print(f"  Skills missing     : {len(missing)}")
    print(f"  Unrecognised files : {len(unknown)}")
    print("═" * 60)

    if missing:
        print("\n📋  MISSING BLOGS — by bundle\n")
        bundle_order = ["Founder","Creator","Marketing","Legal/Biz",
                        "Video/Pod","Student","Realtor","Educator",
                        "Wedding","Creative","Standalone"]
        for bundle in bundle_order:
            slugs = by_bundle.get(bundle, [])
            if not slugs:
                continue
            print(f"  [{bundle}]")
            for slug in slugs:
                print(f"    ✗  {slug}")
            print()
    else:
        print("\n  ✅  All 63 skills have a blog — nothing missing.\n")

    if unknown:
        print("❓  UNRECOGNISED FILES (not matched to any skill)\n")
        for f in unknown:
            print(f"    ?  {f}")
        print()

    if covered:
        print("✅  COVERED SKILLS\n")
        for slug in sorted(covered):
            bundle = BUNDLE_MAP.get(slug, "Standalone")
            print(f"    ✓  {slug:<45} [{bundle}]")
        print()

    # ── Write missing list to file ───────────────────────────────────────────
    out_path = Path("missing-blogs.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("MISSING BLOGS\n")
        f.write("=" * 60 + "\n")
        if missing:
            for slug in missing:
                bundle = BUNDLE_MAP.get(slug, "Standalone")
                f.write(f"{slug:<48} [{bundle}]\n")
        else:
            f.write("All 63 skills covered.\n")
        if unknown:
            f.write("\nUNRECOGNISED FILES\n")
            f.write("=" * 60 + "\n")
            for name in unknown:
                f.write(f"{name}\n")

    print(f"Report saved → {out_path}\n")


if __name__ == "__main__":
    main()
