#!/usr/bin/env python3
"""
add_timesave.py
Adds a ⚡ time-save pill to every NovaKit skill and bundle HTML page.

Skill pages  : skills/<slug>.html       → inserts before <a href="#buy"...>
Bundle pages : skills/bundles/<slug>-bundle.html → inserts before <div class="bh-cta">

Usage:
  python3 add_timesave.py --test ai-animation-film-prompt   # single skill test
  python3 add_timesave.py --test-bundle creative-bundle     # single bundle test
  python3 add_timesave.py                                    # full run

Output goes to ./modified/ — originals untouched.
A log is written to timesave-log.csv.
"""

import os, re, csv, shutil, argparse
from pathlib import Path

# ── CSS to inject (once per file, before </style>) ──────────────────────────
TIMESAVE_CSS = (
    ".sh-time-save{display:inline-flex;align-items:center;gap:8px;"
    "background:var(--green-bg);color:var(--green-text);font-size:14px;"
    "font-weight:600;padding:10px 16px;border-radius:8px;margin-bottom:24px;}\n"
    ".bh-time-save{display:inline-flex;align-items:center;gap:8px;"
    "background:var(--green-bg);color:var(--green-text);font-size:14px;"
    "font-weight:600;padding:10px 16px;border-radius:8px;margin-bottom:20px;}\n"
)

# ── Filename overrides (slug → actual filename without .html) ───────────────
SKILL_FILENAME_OVERRIDES = {
    'grant-and-proposal-writing': 'grant-proposal-writing',
    'logo-brand-identity-prompt': 'logo-brand-identity',
    'sales-landing-page-copy':    'sales-page',
    'tos-privacy-policy':         'terms-of-service-privacy-policy',
    'university-sop':             'university-application-sop',
    'visa-cover-letter':          'visa-application-cover-letter',
    'ai-video-prompt':             'short-form-ai-video',
}

# ── Time-save copy per skill slug ────────────────────────────────────────────
SKILL_TIMESAVE = {
    # $19 skills — 5–8 hrs → under 10 mins
    'ai-video-prompt':               "⚡ Replaces 5–8 hours of scripting and tool calibration — runs in under 10 minutes.",
    'brand-ad-copy':                 "⚡ Replaces 5–8 hours of copy iteration across platforms — runs in under 10 minutes.",
    'financial-model-prompt':        "⚡ Replaces 6–8 hours of spreadsheet scoping — runs in under 10 minutes.",
    'pitch-deck-narrative':          "⚡ Replaces 6–10 hours of deck writing — runs in under 10 minutes.",
    'ugc-ad-creator':                "⚡ Replaces 5–8 hours of brief writing and storyboarding — runs in under 10 minutes.",

    # $15 skills — 3–6 hrs → under 5 mins
    'ai-animation-film-prompt':      "⚡ Replaces 4–6 hours of manual prompt iteration — runs in under 5 minutes.",
    'architecture-diagram-prompt':   "⚡ Replaces 3–5 hours of diagram drafting — runs in under 5 minutes.",
    'brand-voice-guide':             "⚡ Replaces 4–6 hours of brand workshops — runs in under 5 minutes.",
    'course-curriculum-builder':     "⚡ Replaces 4–6 hours of curriculum planning — runs in under 5 minutes.",
    'dialogue-character-film-prompt':"⚡ Replaces 3–5 hours of shot scripting — runs in under 5 minutes.",
    'grant-and-proposal-writing':    "⚡ Replaces 5–8 hours of grant writing — runs in under 5 minutes.",
    'nda-contract-draft':            "⚡ Replaces 3–5 hours of legal drafting — runs in under 5 minutes.",
    'prd-writer':                    "⚡ Replaces 4–6 hours of requirements writing — runs in under 5 minutes.",
    'product-ad-film-prompt':        "⚡ Replaces 3–5 hours of ad brief writing — runs in under 5 minutes.",
    'tos-privacy-policy':            "⚡ Replaces 4–6 hours of legal drafting — runs in under 5 minutes.",
    'university-sop':                "⚡ Replaces 4–6 hours of SOP drafting — runs in under 5 minutes.",
    'video-script-engine':           "⚡ Replaces 3–5 hours of script writing — runs in under 5 minutes.",

    # $9 and below — 45–90 mins → under 3 mins
    'book-cover-prompt':             "⚡ Replaces 60–90 minutes of design briefing — runs in under 3 minutes.",
    'business-plan':                 "⚡ Replaces 4–6 hours of business plan writing — runs in under 3 minutes.",
    'childrens-book-prompt':         "⚡ Replaces 60–90 minutes of story planning — runs in under 3 minutes.",
    'cold-outreach-email':           "⚡ Replaces 45–90 minutes of email drafting — runs in under 3 minutes.",
    'conference-abstract':           "⚡ Replaces 60–90 minutes of abstract writing — runs in under 3 minutes.",
    'content-calendar':              "⚡ Replaces 3–4 hours of calendar planning — runs in under 3 minutes.",
    'cover-letter-writer':           "⚡ Replaces 45–90 minutes of cover letter drafting — runs in under 3 minutes.",
    'ecommerce-product-listing':     "⚡ Replaces 60–90 minutes of listing writing — runs in under 3 minutes.",
    'email-newsletter-engine':       "⚡ Replaces 2–3 hours of newsletter writing — runs in under 3 minutes.",
    'eulogy-writer':                 "⚡ Replaces 2–4 hours of writing at a difficult time — runs in under 3 minutes.",
    'event-speech-writer':           "⚡ Replaces 2–3 hours of speech writing — runs in under 3 minutes.",
    'exam-paper-generator':          "⚡ Replaces 3–5 hours of paper setting — runs in under 3 minutes.",
    'festival-holiday-greeting-prompt': "⚡ Replaces 60–90 minutes of campaign briefing — runs in under 3 minutes.",
    'health-wellness-plan':          "⚡ Replaces 2–3 hours of plan writing — runs in under 3 minutes.",
    'home-renovation-brief':         "⚡ Replaces 2–3 hours of brief writing — runs in under 3 minutes.",
    'hotel-airbnb-listing-copy':     "⚡ Replaces 60–90 minutes of listing writing — runs in under 3 minutes.",
    'investor-update-email':         "⚡ Replaces 60–90 minutes of investor update writing — runs in under 3 minutes.",
    'job-description-writer':        "⚡ Replaces 60–90 minutes of JD writing — runs in under 3 minutes.",
    'lesson-plan-builder':           "⚡ Replaces 2–3 hours of lesson planning — runs in under 3 minutes.",
    'linkedin-post-engine':          "⚡ Replaces 45–90 minutes of post drafting — runs in under 3 minutes.",
    'logo-brand-identity-prompt':    "⚡ Replaces 2–3 hours of design briefing — runs in under 3 minutes.",
    'menu-description-copy':         "⚡ Replaces 60–90 minutes of menu writing — runs in under 3 minutes.",
    'performance-review-writer':     "⚡ Replaces 60–90 minutes of review writing — runs in under 3 minutes.",
    'podcast-episode-script':        "⚡ Replaces 2–3 hours of episode scripting — runs in under 3 minutes.",
    'podcast-show-notes':            "⚡ Replaces 45–60 minutes of show notes writing — runs in under 3 minutes.",
    'poetry-verse-prompt':           "⚡ Replaces 45–90 minutes of verse writing — runs in under 3 minutes.",
    'pr-press-release':              "⚡ Replaces 2–3 hours of press release writing — runs in under 3 minutes.",
    'product-photography-prompt':    "⚡ Replaces 60–90 minutes of photography briefing — runs in under 3 minutes.",
    'real-estate-listing-copy':      "⚡ Replaces 60–90 minutes of listing writing — runs in under 3 minutes.",
    'real-estate-photo-prompt':      "⚡ Replaces 60–90 minutes of photography briefing — runs in under 3 minutes.",
    'recipe-development-prompt':     "⚡ Replaces 60–90 minutes of recipe development — runs in under 3 minutes.",
    'research-paper-outline':        "⚡ Replaces 2–3 hours of outline planning — runs in under 3 minutes.",
    'resume-cv-builder':             "⚡ Replaces 2–3 hours of resume writing — runs in under 3 minutes.",
    'sales-landing-page-copy':       "⚡ Replaces 3–5 hours of copywriting — runs in under 3 minutes.",
    'screenplay-script':             "⚡ Replaces 3–5 hours of script formatting — runs in under 3 minutes.",
    'seo-blog-post-brief':           "⚡ Replaces 60–90 minutes of SEO research — runs in under 3 minutes.",
    'short-story-prompt':            "⚡ Replaces 60–90 minutes of story planning — runs in under 3 minutes.",
    'social-content-engine':         "⚡ Replaces 2–3 hours of weekly content planning — runs in under 3 minutes.",
    'social-media-carousel-prompt':  "⚡ Replaces 60–90 minutes of carousel planning — runs in under 3 minutes.",
    'travel-itinerary-planner':      "⚡ Replaces 2–3 hours of itinerary research — runs in under 3 minutes.",
    'twitter-x-thread-engine':       "⚡ Replaces 45–90 minutes of thread writing — runs in under 3 minutes.",
    'visa-cover-letter':             "⚡ Replaces 60–90 minutes of application writing — runs in under 3 minutes.",
    'webinar-online-event-script':   "⚡ Replaces 3–5 hours of webinar scripting — runs in under 3 minutes.",
    'wedding-invitation-prompt':     "⚡ Replaces 60–90 minutes of design briefing — runs in under 3 minutes.",
    'wedding-vows-writer':           "⚡ Replaces 2–3 hours of vow writing — runs in under 3 minutes.",
    'youtube-thumbnail-prompt':      "⚡ Replaces 45–60 minutes of thumbnail briefing — runs in under 3 minutes.",
}

# ── Bundle time-save copy ────────────────────────────────────────────────────
BUNDLE_TIMESAVE = {
    'creative-bundle':   "⚡ 6 skills. Replaces 15+ hours of creative writing work — each runs in under 3 minutes.",
    'creator-bundle':    "⚡ 7 skills. Replaces 12+ hours of weekly content work — each runs in under 3 minutes.",
    'educator-bundle':   "⚡ 4 skills. Replaces 15+ hours of curriculum and exam prep — each runs in under 5 minutes.",
    'founder-bundle':    "⚡ 6 skills. Replaces 20+ hours of founder writing work — each runs in under 10 minutes.",
    'legal-biz-bundle':  "⚡ 5 skills. Replaces 20+ hours of legal and financial drafting — each runs in under 5 minutes.",
    'marketing-bundle':  "⚡ 5 skills. Replaces 25+ hours of marketing work — each runs in under 10 minutes.",
    'realtor-bundle':    "⚡ 5 skills. Replaces 8+ hours of listing and photo work — each runs in under 3 minutes.",
    'student-bundle':    "⚡ 5 skills. Replaces 15+ hours of application writing — each runs in under 5 minutes.",
    'video-pod-bundle':  "⚡ 9 skills. Replaces 30+ hours of video and podcast production work — each runs in under 5 minutes.",
    'wedding-bundle':    "⚡ 4 skills. Replaces 10+ hours of wedding writing — each runs in under 3 minutes.",
}


def inject_css(html):
    """Inject CSS before closing </style> tag if not already present."""
    if ".sh-time-save{" in html or ".bh-time-save{" in html:
        return html, False  # already patched
    # Insert before first </style>
    html = html.replace('</style>', TIMESAVE_CSS + '</style>', 1)
    return html, True


def patch_skill_page(html, slug):
    """Insert time-save pill before the hero CTA button on a skill page."""
    copy = SKILL_TIMESAVE.get(slug)
    if not copy:
        return html, f"SKIP — no time-save copy for slug '{slug}'"

    pill = f'      <div class="sh-time-save">{copy}</div>\n'

    # Match the primary CTA button in the hero (href="#buy", btn-primary, btn-lg)
    pattern = r'( {6}<a href="#buy" class="btn btn-primary btn-lg">)'
    match = re.search(pattern, html)
    if not match:
        # Fallback: any btn-primary btn-lg buy link
        pattern = r'(<a href="#buy" class="btn btn-primary btn-lg">)'
        match = re.search(pattern, html)

    if not match:
        return html, "SKIP — could not find hero CTA anchor"

    # Only insert once (before the first match)
    insert_at = match.start()
    html = html[:insert_at] + pill + html[insert_at:]
    html, _ = inject_css(html)
    return html, "OK"


def patch_bundle_page(html, slug):
    """Insert time-save pill before the bh-cta div on a bundle page."""
    copy = BUNDLE_TIMESAVE.get(slug)
    if not copy:
        return html, f"SKIP — no time-save copy for bundle slug '{slug}'"

    pill = f'      <div class="bh-time-save">{copy}</div>\n'

    # Try bh-cta first (creative-bundle), then hero-cta (all other bundles)
    pattern = r'( {6}<div class="bh-cta">)'
    match = re.search(pattern, html)
    if not match:
        pattern = r'(<div class="bh-cta">)'
        match = re.search(pattern, html)
    if not match:
        pattern = r'( {6}<div class="hero-cta">)'
        match = re.search(pattern, html)
    if not match:
        pattern = r'(<div class="hero-cta">)'
        match = re.search(pattern, html)

    if not match:
        return html, "SKIP — could not find bh-cta or hero-cta div"

    insert_at = match.start()
    html = html[:insert_at] + pill + html[insert_at:]
    html, _ = inject_css(html)
    return html, "OK"


def process_file(src: Path, out_dir: Path, slug: str, is_bundle: bool) -> str:
    html = src.read_text(encoding='utf-8')

    # Skip if already patched
    if ".sh-time-save{" in html or ".bh-time-save{" in html:
        return "SKIP — already patched"

    if is_bundle:
        html, status = patch_bundle_page(html, slug)
    else:
        html, status = patch_skill_page(html, slug)

    if status == "OK":
        dest = out_dir / src.name
        dest.write_text(html, encoding='utf-8')

    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skills-dir', default='./skills',
                        help='Path to skills/ folder (contains .html skill pages)')
    parser.add_argument('--bundles-dir', default='./skills/bundles',
                        help='Path to skills/bundles/ folder')
    parser.add_argument('--out-dir', default='./modified',
                        help='Output directory (default: ./modified)')
    parser.add_argument('--test', metavar='SLUG',
                        help='Test a single skill slug only')
    parser.add_argument('--test-bundle', metavar='SLUG',
                        help='Test a single bundle slug only')
    args = parser.parse_args()

    skills_dir  = Path(args.skills_dir)
    bundles_dir = Path(args.bundles_dir)
    out_dir     = Path(args.out_dir)
    out_bundles = out_dir / 'bundles'
    out_dir.mkdir(exist_ok=True)
    out_bundles.mkdir(exist_ok=True)

    log = []

    if args.test:
        slug = args.test
        filename = SKILL_FILENAME_OVERRIDES.get(slug, slug)
        src = skills_dir / f'{filename}.html'
        if not src.exists():
            print(f"✗ File not found: {src}")
            return
        status = process_file(src, out_dir, slug, is_bundle=False)
        print(f"{'✓' if status == 'OK' else '✗'} {slug} → {status}")
        return

    if args.test_bundle:
        slug = args.test_bundle
        src = bundles_dir / f'{slug}.html'
        if not src.exists():
            print(f"✗ File not found: {src}")
            return
        status = process_file(src, out_bundles, slug, is_bundle=True)
        print(f"{'✓' if status == 'OK' else '✗'} {slug} → {status}")
        return

    # Full run — skills
    ok = skip = 0
    for slug in SKILL_TIMESAVE:
        filename = SKILL_FILENAME_OVERRIDES.get(slug, slug)
        src = skills_dir / f'{filename}.html'
        if not src.exists():
            status = "SKIP — file not found"
        else:
            status = process_file(src, out_dir, slug, is_bundle=False)
        icon = '✓' if status == 'OK' else '✗'
        print(f"{icon} {slug}: {status}")
        log.append({'file': f'{slug}.html', 'type': 'skill', 'status': status})
        if status == 'OK': ok += 1
        else: skip += 1

    # Full run — bundles
    for slug in BUNDLE_TIMESAVE:
        src = bundles_dir / f'{slug}.html'
        if not src.exists():
            status = "SKIP — file not found"
        else:
            status = process_file(src, out_bundles, slug, is_bundle=True)
        icon = '✓' if status == 'OK' else '✗'
        print(f"{icon} {slug}: {status}")
        log.append({'file': f'{slug}.html', 'type': 'bundle', 'status': status})
        if status == 'OK': ok += 1
        else: skip += 1

    # Write log
    log_path = out_dir / 'timesave-log.csv'
    with open(log_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'type', 'status'])
        writer.writeheader()
        writer.writerows(log)

    print(f"\n{'─'*50}")
    print(f"Done — {ok} patched, {skip} skipped")
    print(f"Log → {log_path}")
    print(f"Output → {out_dir}/")


if __name__ == '__main__':
    main()
