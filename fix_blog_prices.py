"""
fix_blog_prices.py
Scans blog/ and blog1/ for incorrect skill prices and fixes them.
Run from NovaKitwebsite folder:
  python3 fix_blog_prices.py
"""

import re
import shutil
from pathlib import Path

DRY_RUN = True  # flip to False to apply

# Correct price for each skill slug
CORRECT_PRICES = {
    'ai-animation-film-prompt': 15,
    'ai-video-prompt': 19,
    'architecture-diagram-prompt': 8,
    'book-cover-prompt': 5,
    'brand-ad-copy': 19,
    'brand-voice-guide': 15,
    'business-plan': 9,
    'childrens-book-prompt': 6,
    'cold-outreach-email': 9,
    'conference-abstract': 7,
    'content-calendar': 8,
    'course-curriculum-builder': 15,
    'cover-letter-writer': 9,
    'dialogue-character-film-prompt': 15,
    'ecommerce-product-listing': 9,
    'email-newsletter-engine': 9,
    'event-speech-writer': 5,
    'exam-paper-generator': 9,
    'festival-holiday-greeting-prompt': 5,
    'financial-model-prompt': 19,
    'grant-and-proposal-writing': 15,
    'health-wellness-plan': 8,
    'home-renovation-brief': 7,
    'hotel-airbnb-listing-copy': 7,
    'investor-update-email': 9,
    'job-description-writer': 9,
    'lesson-plan-builder': 8,
    'linkedin-post-engine': 9,
    'logo-brand-identity-prompt': 9,
    'menu-description-copy': 5,
    'nda-contract-draft': 15,
    'performance-review-writer': 9,
    'pitch-deck-narrative': 19,
    'podcast-episode-script': 9,
    'podcast-show-notes': 8,
    'poetry-verse-prompt': 5,
    'pr-press-release': 9,
    'prd-writer': 9,
    'product-ad-film-prompt': 15,
    'product-photography-prompt': 9,
    'real-estate-listing-copy': 9,
    'real-estate-photo-prompt': 9,
    'recipe-development-prompt': 7,
    'research-paper-outline': 7,
    'resume-cv-builder': 9,
    'sales-landing-page-copy': 9,
    'screenplay-script': 6,
    'seo-blog-post-brief': 9,
    'short-form-ai-video': 19,      # old slug — keep for blog1/ files
    'short-story-prompt': 5,
    'social-content-engine': 9,
    'social-media-carousel-prompt': 8,
    'tos-privacy-policy': 15,
    'travel-itinerary-planner': 8,
    'twitter-x-thread-engine': 9,
    'ugc-ad-creator': 19,
    'university-sop': 15,
    'university-application-sop': 15,  # old slug — keep for blog1/ files
    'video-script-engine': 15,
    'visa-cover-letter': 5,
    'visa-application-cover-letter': 5, # old slug — keep for blog1/ files
    'webinar-online-event-script': 9,
    'wedding-invitation-prompt': 5,
    'wedding-vows-writer': 5,
    'youtube-thumbnail-prompt': 8,
}

# Blog slug → skill slug mapping for blogs with descriptive filenames
# (blog filename doesn't match skill slug directly)
BLOG_TO_SKILL = {
    # Descriptive blog filenames → skill slug
    'why-cold-emails-get-deleted': 'cold-outreach-email',
    'financial-model-why-spreadsheets-arent-the-problem': 'financial-model-prompt',
    'financial-model': 'financial-model-prompt',
    'airbnb-listing-copy-you-vs-ai-vs-calibrated-skill': 'hotel-airbnb-listing-copy',
    'the-airbnb-listing-that-gets-booked-before-anyone-asks-about-parking': 'hotel-airbnb-listing-copy',
    'how-to-write-real-estate-listing': 'real-estate-listing-copy',
    'how-to-write-wedding-vows-with-ai-that-actually-sound-like-you': 'wedding-vows-writer',
    'the-vows-that-sound-like-you-wrote-them-because-you-did': 'wedding-vows-writer',
    'the-wedding-speech-that-sounds-like-you-not-like-a-template': 'event-speech-writer',
    'the-event-speech-that-lands': 'event-speech-writer',
    'wedding-invitation-your-invitation-sets-the-tone': 'wedding-invitation-prompt',
    'wedding-invitation': 'wedding-invitation-prompt',
    'why-menu-copy-fails-to-sell-food': 'menu-description-copy',
    'menu-description-copy-ai': 'menu-description-copy',
    'online-course-curriculum-completion': 'course-curriculum-builder',
    'course-curriculum-builder-ai': 'course-curriculum-builder',
    'why-ai-lesson-plans-fail-the-learning-objective-test': 'lesson-plan-builder',
    'lesson-plan-builder-ai': 'lesson-plan-builder',
    'why-your-research-paper-structure-fails-peer-review': 'research-paper-outline',
    'research-paper-outline-ai': 'research-paper-outline',
    'what-a-generic-ai-eulogy-sounds-like': 'eulogy-writer',
    'why-ai-dialogue-sounds-flat': 'dialogue-character-film-prompt',
    'why-ai-travel-itineraries-feel-generic': 'travel-itinerary-planner',
    'why-your-architecture-diagram-confuses-everyone': 'architecture-diagram-prompt',
    'why-your-carousel-slides-get-scrolled-past': 'social-media-carousel-prompt',
    'what-investors-want-in-a-business-plan': 'business-plan',
    'sales-page-skill': 'sales-landing-page-copy',
    'the-sales-page-that-sounds-like-it-was-written-about-your-product': 'sales-landing-page-copy',
    'social-content-engine-skill': 'social-content-engine',
    'wedding-vows-writer-ai': 'wedding-vows-writer',
    'short-form-ai-video-script': 'ai-video-prompt',
    'why-short-form-ai-video-scripts-miss-the-algorithm': 'ai-video-prompt',
    'logo-brand-identity': 'logo-brand-identity-prompt',
    'logo-brand-identity-why-generic-ai-fails': 'logo-brand-identity-prompt',
    'how-to-write-ai-film-prompts-that-actually-work': 'ai-animation-film-prompt',
    'the-ai-film-prompt-that-gives-sora-a-character-not-just-a-scene': 'dialogue-character-film-prompt',
    'podcast-scripted-vs-outlined-vs-improvised': 'podcast-episode-script',
    'the-podcast-script-that-sounds-like-you-wrote-it-not-like-youre-reading-it': 'podcast-episode-script',
    'seo-brief-for-freelancers': 'seo-blog-post-brief',
    'email-newsletter-subject-lines': 'email-newsletter-engine',
    'the-book-cover-brief-your-designer-actually-needs': 'book-cover-prompt',
    'why-your-book-cover-looks-wrong': 'book-cover-prompt',
    'visa-cover-letter-questions-answered': 'visa-cover-letter',
    'the-holiday-greeting-written-for-everyone-and-why-it-lands-with-no-one': 'festival-holiday-greeting-prompt',
    'the-linkedin-post-that-actually-gets-read-and-why-format-is-everything': 'linkedin-post-engine',
    'the-screenplay-ai-gets-wrong-and-what-a-trained-script-skill-fixes': 'screenplay-script',
    'the-short-story-ai-gets-right-when-it-knows-your-genre': 'short-story-prompt',
    'why-ai-poetry-reads-like-a-greeting-card-and-how-to-fix-it': 'poetry-verse-prompt',
    'why-your-second-childrens-book-doesnt-sound-like-your-first': 'childrens-book-prompt',
    'your-brand-voice-is-the-one-thing-ai-cant-fake': 'brand-voice-guide',
    'your-social-posts-arent-underperforming-your-brief-is': 'social-content-engine',
    'grant-proposal-writing': 'grant-and-proposal-writing',
    'grant-proposal-writing-why-generic-fails': 'grant-and-proposal-writing',
    'grant-and-proposal-writing': 'grant-and-proposal-writing',
    'university-application-sop': 'university-sop',
    'university-application-sop-why-ai-sops-fail': 'university-sop',
    'visa-application-cover-letter': 'visa-cover-letter',
    'terms-of-service-privacy-policy': 'tos-privacy-policy',
    'terms-of-service-privacy-policy-what-copied-tos-misses': 'tos-privacy-policy',
}

VALID_PRICES = {5, 6, 7, 8, 9, 15, 19}

def resolve_skill(stem):
    """Get skill slug for a blog file stem."""
    if stem in BLOG_TO_SKILL:
        return BLOG_TO_SKILL[stem]
    if stem in CORRECT_PRICES:
        return stem
    return None


def find_and_fix_prices(filepath, skill_slug, correct_price, dry_run):
    """Find all price occurrences in a blog file and fix wrong ones."""
    content = filepath.read_text(encoding='utf-8')
    original = content
    changes = []

    # Price patterns to look for in blog HTML:
    # $9, $15 etc — in text, buttons, badges
    # We want to replace WRONG prices with CORRECT price
    # But only replace prices that look like the skill price (not unrelated numbers)
    # Pattern: dollar sign followed by a valid price tier number

    for wrong_price in VALID_PRICES - {correct_price}:
        # Match $X where X is a wrong price tier
        # Be specific: match as standalone price display, not part of larger numbers
        pattern = r'(\$)' + str(wrong_price) + r'(?!\d)'
        matches = list(re.finditer(pattern, content))
        if matches:
            # Check context — only fix price in skill-related contexts
            # (buy buttons, price badges, skill price mentions)
            price_contexts = [
                'btn', 'price', 'badge', 'cost', 'Get the skill', 'See the skill',
                'tier', 'buy', 'purchase', 'skill-price', 'data-price',
                str(correct_price)  # near correct price = likely a comparison
            ]
            for match in matches:
                start = max(0, match.start() - 200)
                end = min(len(content), match.end() + 200)
                context = content[start:end].lower()
                # Only fix if in a price-display context
                if any(ctx.lower() in context for ctx in price_contexts[:8]):
                    changes.append(f'  ${wrong_price} → ${correct_price} (pos {match.start()})')

            if changes:
                content = re.sub(pattern, f'${correct_price}', content)

    if content != original:
        if dry_run:
            return changes, None
        else:
            filepath.write_text(content, encoding='utf-8')
            return changes, True
    return [], None


# ── Main ─────────────────────────────────────────────────────────────────────

BLOG_DIRS = [
    Path('/Users/snehoomac/snehoo/AI/novakit/NovaKitwebsite/blog'),
    Path('/Users/snehoomac/snehoo/AI/novakit/NovaKitwebsite/blog1'),
]

print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}\n")

total_files = 0
total_changes = 0
mismatches = []

for blog_dir in BLOG_DIRS:
    if not blog_dir.exists():
        print(f"[SKIP] {blog_dir} not found")
        continue

    print(f"\n{'='*60}")
    print(f"Scanning {blog_dir.name}/")
    print(f"{'='*60}")

    for filepath in sorted(blog_dir.glob('*.html')):
        stem = filepath.stem
        skill = resolve_skill(stem)

        if skill is None:
            continue

        correct = CORRECT_PRICES.get(skill)
        if correct is None:
            print(f"  [NO PRICE] {filepath.name} → skill '{skill}' not in price map")
            continue

        # Quick check: does this file contain any wrong prices?
        content = filepath.read_text(encoding='utf-8')
        has_wrong = False
        for wrong in VALID_PRICES - {correct}:
            if f'${wrong}' in content:
                has_wrong = True
                break

        if not has_wrong:
            continue

        changes, written = find_and_fix_prices(filepath, skill, correct, DRY_RUN)
        if changes:
            total_files += 1
            total_changes += len(changes)
            status = '[DRY RUN]' if DRY_RUN else '[FIXED]'
            print(f"\n  {status} {filepath.name} (skill: {skill}, correct: ${correct})")
            for c in changes:
                print(c)
            mismatches.append((blog_dir.name, filepath.name, skill, correct))

print(f"\n{'='*60}")
print(f"Summary: {total_changes} price fixes across {total_files} files")
if DRY_RUN and total_changes > 0:
    print("Flip DRY_RUN = False and re-run to apply.")
elif not DRY_RUN:
    print("All done.")
