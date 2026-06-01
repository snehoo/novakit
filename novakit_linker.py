#!/usr/bin/env python3
"""
novakit_linker.py — Novakit Blog Interlinking Automation v3
============================================================
For each skill, holds a list of ~10 trigger phrases likely to appear
naturally in blog text. Scans every blog for those phrases and wraps
the first unlinked match in an <a> tag.

  Layer 1  : blog → skill page         (/skills/[slug].html)
  Layer 2  : blog → next blog in chain (/blog/[slug].html)
  Layer 2b : blog → bundle upsell      (/skills/bundles/[slug]-bundle.html)
  Layer 3  : skill page → blog back-link (below "not what this is for" box)

Fallback: if no keyword match found for a layer, appends a closing
paragraph with the link — same behaviour as v2.

Usage
-----
  # Dry run (default)
  python3 novakit_linker.py --blogs ./blog --skills ./skills

  # Test single skill pair
  python3 novakit_linker.py --blogs ./blog --skills ./skills --output ./modified --run --test cold-outreach-email

  # Full run
  python3 novakit_linker.py --blogs ./blog --skills ./skills --output ./modified --run

Requirements: pip install beautifulsoup4
"""

import re
import csv
import argparse
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — URL BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = "https://novakit.tech"

def skill_url(slug):   return f"{BASE_URL}/skills/{slug}.html"
def blog_url(slug):    return f"{BASE_URL}/blog/{slug}.html"
def bundle_url(slug):  return f"{BASE_URL}/skills/bundles/{slug}-bundle.html"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — SKILL → BUNDLE MAP
# ─────────────────────────────────────────────────────────────────────────────

SKILL_BUNDLE = {
    "pitch-deck-narrative":             ("founder",   "Founder"),
    "cold-outreach-email":              ("founder",   "Founder"),
    "sales-page":                       ("founder",   "Founder"),
    "business-plan":                    ("founder",   "Founder"),
    "investor-update-email":            ("founder",   "Founder"),
    "job-description-writer":           ("founder",   "Founder"),
    "executive-bio":                    ("founder",   "Founder"),
    "one-pager-investor-brief":         ("founder",   "Founder"),
    "brand-voice-guide":                ("creator",   "Creator"),
    "linkedin-post-engine":             ("creator",   "Creator"),
    "social-content-engine":            ("creator",   "Creator"),
    "twitter-x-thread-engine":          ("creator",   "Creator"),
    "seo-blog-post-brief":              ("creator",   "Creator"),
    "email-newsletter-engine":          ("creator",   "Creator"),
    "content-calendar":                 ("creator",   "Creator"),
    "ugc-ad-creator":                   ("marketing", "Marketing"),
    "brand-ad-copy":                    ("marketing", "Marketing"),
    "pr-press-release":                 ("marketing", "Marketing"),
    "ecommerce-product-listing":        ("marketing", "Marketing"),
    "product-photography-prompt":       ("marketing", "Marketing"),
    "financial-model-prompt":           ("legal-biz", "Legal & Biz"),
    "grant-proposal-writing":           ("legal-biz", "Legal & Biz"),
    "nda-contract-draft":               ("legal-biz", "Legal & Biz"),
    "terms-of-service-privacy-policy":  ("legal-biz", "Legal & Biz"),
    "visa-application-cover-letter":    ("legal-biz", "Legal & Biz"),
    "short-form-ai-video":              ("video-pod", "Video & Pod"),
    "video-script":                     ("video-pod", "Video & Pod"),
    "ai-animation-film-prompt":         ("video-pod", "Video & Pod"),
    "product-ad-film-prompt":           ("video-pod", "Video & Pod"),
    "dialogue-character-film-prompt":   ("video-pod", "Video & Pod"),
    "podcast-episode-script":           ("video-pod", "Video & Pod"),
    "webinar-online-event-script":      ("video-pod", "Video & Pod"),
    "youtube-thumbnail-prompt":         ("video-pod", "Video & Pod"),
    "podcast-show-notes":               ("video-pod", "Video & Pod"),
    "university-application-sop":       ("student",   "Student"),
    "resume-cv-builder":                ("student",   "Student"),
    "cover-letter-writer":              ("student",   "Student"),
    "research-paper-outline":           ("student",   "Student"),
    "conference-abstract":              ("student",   "Student"),
    "real-estate-listing-copy":         ("realtor",   "Realtor"),
    "real-estate-photo-prompt":         ("realtor",   "Realtor"),
    "hotel-airbnb-listing-copy":        ("realtor",   "Realtor"),
    "course-curriculum-builder":        ("educator",  "Educator"),
    "lesson-plan-builder":              ("educator",  "Educator"),
    "exam-paper-generator":             ("educator",  "Educator"),
    "wedding-vows-writer":              ("wedding",   "Wedding"),
    "wedding-invitation-prompt":        ("wedding",   "Wedding"),
    "event-speech-writer":              ("wedding",   "Wedding"),
    "menu-description-copy":            ("wedding",   "Wedding"),
    "screenplay-script":                ("creative",  "Creative"),
    "children-book-prompt":             ("creative",  "Creative"),
    "short-story-prompt":               ("creative",  "Creative"),
    "poetry-verse-prompt":              ("creative",  "Creative"),
    "book-cover-prompt":                ("creative",  "Creative"),
    "festival-holiday-greeting-prompt": ("creative",  "Creative"),
    "prd-writer":                       (None, None),
    "architecture-diagram-prompt":      (None, None),
    "logo-brand-identity":              (None, None),
    "performance-review-writer":        (None, None),
    "social-media-carousel-prompt":     (None, None),
    "health-wellness-plan":             (None, None),
    "travel-itinerary-planner":         (None, None),
    "recipe-development-prompt":        (None, None),
    "home-renovation-brief":            (None, None),
    "eulogy-writer":                    (None, None),
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — DAISY CHAIN
# ─────────────────────────────────────────────────────────────────────────────

DAISY_CHAIN = {
    "business-plan": "pitch-deck-narrative",
    "pitch-deck-narrative": "investor-update-email",
    "investor-update-email": "cold-outreach-email",
    "cold-outreach-email": "sales-page",
    "sales-page": "job-description-writer",
    "job-description-writer": "financial-model-prompt",
    "brand-voice-guide": "linkedin-post-engine",
    "linkedin-post-engine": "social-content-engine",
    "social-content-engine": "content-calendar",
    "content-calendar": "email-newsletter-engine",
    "email-newsletter-engine": "twitter-x-thread-engine",
    "twitter-x-thread-engine": "seo-blog-post-brief",
    "seo-blog-post-brief": "pr-press-release",
    "brand-ad-copy": "ugc-ad-creator",
    "ugc-ad-creator": "sales-page",
    "pr-press-release": "linkedin-post-engine",
    "financial-model-prompt": "nda-contract-draft",
    "nda-contract-draft": "terms-of-service-privacy-policy",
    "terms-of-service-privacy-policy": "grant-proposal-writing",
    "grant-proposal-writing": "visa-application-cover-letter",
    "visa-application-cover-letter": "pitch-deck-narrative",
    "video-script": "short-form-ai-video",
    "short-form-ai-video": "product-ad-film-prompt",
    "product-ad-film-prompt": "ai-animation-film-prompt",
    "ai-animation-film-prompt": "dialogue-character-film-prompt",
    "dialogue-character-film-prompt": "podcast-episode-script",
    "podcast-episode-script": "podcast-show-notes",
    "podcast-show-notes": "social-content-engine",
    "webinar-online-event-script": "video-script",
    "youtube-thumbnail-prompt": "short-form-ai-video",
    "university-application-sop": "resume-cv-builder",
    "resume-cv-builder": "cover-letter-writer",
    "cover-letter-writer": "research-paper-outline",
    "research-paper-outline": "conference-abstract",
    "conference-abstract": "linkedin-post-engine",
    "real-estate-listing-copy": "real-estate-photo-prompt",
    "real-estate-photo-prompt": "hotel-airbnb-listing-copy",
    "hotel-airbnb-listing-copy": "ecommerce-product-listing",
    "ecommerce-product-listing": "product-photography-prompt",
    "product-photography-prompt": "brand-ad-copy",
    "course-curriculum-builder": "lesson-plan-builder",
    "lesson-plan-builder": "exam-paper-generator",
    "exam-paper-generator": "university-application-sop",
    "event-speech-writer": "wedding-vows-writer",
    "wedding-vows-writer": "wedding-invitation-prompt",
    "wedding-invitation-prompt": "menu-description-copy",
    "menu-description-copy": "eulogy-writer",
    "short-story-prompt": "screenplay-script",
    "screenplay-script": "book-cover-prompt",
    "book-cover-prompt": "poetry-verse-prompt",
    "poetry-verse-prompt": "children-book-prompt",
    "children-book-prompt": "festival-holiday-greeting-prompt",
    "prd-writer": "pitch-deck-narrative",
    "architecture-diagram-prompt": "prd-writer",
    "logo-brand-identity": "brand-voice-guide",
    "performance-review-writer": "resume-cv-builder",
    "social-media-carousel-prompt": "social-content-engine",
    "eulogy-writer": "event-speech-writer",
    "recipe-development-prompt": "menu-description-copy",
    "home-renovation-brief": "real-estate-listing-copy",
    "travel-itinerary-planner": "hotel-airbnb-listing-copy",
    "health-wellness-plan": "brand-voice-guide",
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — SKILL TRIGGER KEYWORDS
# ~10 phrases per skill, ordered by how likely they are to appear in blog text.
# The script tries them in order and stops at the first match.
# ─────────────────────────────────────────────────────────────────────────────

SKILL_KEYWORDS = {
    # Founder
    "pitch-deck-narrative":    ["pitch deck","investor pitch","deck narrative","pitch story","pitch slides","investor presentation","funding pitch","narrative arc","pitch structure","deck copy"],
    "cold-outreach-email":     ["cold email","cold outreach","outreach email","sales email","prospecting email","first touch","email sequence","B2B email","outbound email","cold sequence"],
    "sales-page":              ["sales page","landing page","conversion page","sales copy","page copy","offer page","sales letter","conversion copy","product page copy","page that converts"],
    "business-plan":           ["business plan","business model","go-to-market","executive summary","market analysis","business case","startup plan","revenue model","company overview","operational plan"],
    "investor-update-email":   ["investor update","monthly update","board update","investor email","portfolio update","update email","investor communication","stakeholder update","LP update","founder update"],
    "job-description-writer":  ["job description","job posting","job listing","role description","hiring post","job spec","talent acquisition","job advert","JD writing","hiring copy"],
    "executive-bio":           ["executive bio","founder bio","speaker bio","about page","professional bio","leadership bio","author bio","personal bio","bio writing","bio copy"],
    "one-pager-investor-brief":["one-pager","investor brief","pitch brief","company brief","deal summary","single page overview","one page summary","investor one-pager","brief document"],
    # Creator
    "brand-voice-guide":       ["brand voice","tone of voice","voice guide","brand tone","content voice","writing style","brand language","editorial voice","consistent voice","tone guidelines"],
    "linkedin-post-engine":    ["LinkedIn post","LinkedIn content","LinkedIn algorithm","LinkedIn reach","LinkedIn engagement","posting on LinkedIn","LinkedIn feed","LinkedIn audience","LinkedIn writing","LinkedIn format"],
    "social-content-engine":   ["social content","social media content","content strategy","social posts","content creation","social media strategy","organic content","content mix","social writing","content output"],
    "twitter-x-thread-engine": ["Twitter thread","X thread","tweet thread","threaded post","long-form tweet","thread writing","Twitter content","X content","thread structure","thread format"],
    "seo-blog-post-brief":     ["SEO blog","blog brief","content brief","SEO content","search-optimised","keyword targeting","blog post brief","search intent","SEO writing","content outline"],
    "email-newsletter-engine": ["email newsletter","newsletter copy","subscriber email","email list","newsletter writing","email marketing","weekly newsletter","newsletter open rate","newsletter subject","subscriber list"],
    "content-calendar":        ["content calendar","editorial calendar","publishing schedule","content planning","posting schedule","content schedule","monthly calendar","content pipeline","content plan","calendar template"],
    # Marketing
    "ugc-ad-creator":          ["UGC ad","user-generated content","UGC video","creator ad","UGC brief","ad creative brief","UGC campaign","organic-style ad","creator brief","UGC content"],
    "brand-ad-copy":           ["ad copy","advertising copy","brand copy","ad creative","campaign copy","display ad","paid ad copy","ad headline","ad text","ad writing"],
    "pr-press-release":        ["press release","media release","PR announcement","news release","media outreach","press coverage","editorial pitch","PR copy","press statement","journalist pitch"],
    "ecommerce-product-listing":["product listing","e-commerce listing","product description","listing copy","product page copy","Amazon listing","marketplace listing","product title","product copy","listing description"],
    "product-photography-prompt":["product photo","product photography","photo brief","product shot","photography prompt","product image brief","visual brief","product shoot","image brief","photo prompt"],
    # Legal/Biz
    "financial-model-prompt":  ["financial model","revenue forecast","financial projections","unit economics","financial assumptions","cash flow model","financial plan","P&L model","revenue model","financial spreadsheet"],
    "grant-proposal-writing":  ["grant proposal","grant writing","funding proposal","grant application","proposal writing","grant narrative","funding narrative","RFP response","grant bid","grant document"],
    "nda-contract-draft":      ["NDA","non-disclosure agreement","contract draft","confidentiality agreement","legal draft","contract template","agreement draft","legal agreement","contractor agreement","contract writing"],
    "terms-of-service-privacy-policy":["terms of service","privacy policy","terms and conditions","user agreement","data policy","cookie policy","legal terms","ToS","privacy notice","terms document"],
    "visa-application-cover-letter":["visa application","visa letter","immigration letter","visa cover letter","visa document","visa support letter","visa paperwork","travel visa","visa writing"],
    # Video/Pod
    "short-form-ai-video":     ["short-form video","vertical video","Reels script","TikTok script","short video","60-second video","short video prompt","AI video prompt","vertical format","short clip"],
    "video-script":            ["video script","script writing","script structure","YouTube script","video content","scripted video","talking head script","explainer script","script format","video writing"],
    "ai-animation-film-prompt":["AI animation","animation prompt","animated film","motion prompt","AI film","Sora prompt","generative animation","visual prompt","AI video","animation brief"],
    "product-ad-film-prompt":  ["product ad","ad film","commercial prompt","product film brief","ad film prompt","video ad brief","product video","product commercial","brand film","ad production brief"],
    "dialogue-character-film-prompt":["character dialogue","film dialogue","scene prompt","character voice","dialogue writing","film scene","character brief","Sora character","scene writing","character script"],
    "podcast-episode-script":  ["podcast script","podcast episode","episode script","podcast writing","show script","interview script","podcast structure","episode writing","podcast format","audio script"],
    "webinar-online-event-script":["webinar script","webinar writing","online event script","virtual event script","webinar structure","presentation script","webinar flow","webinar copy","live event script","virtual workshop script"],
    "youtube-thumbnail-prompt":["YouTube thumbnail","thumbnail brief","CTR thumbnail","thumbnail design","thumbnail prompt","click-through thumbnail","thumbnail psychology","thumbnail text","thumbnail layout","thumbnail copy"],
    "podcast-show-notes":      ["show notes","podcast notes","episode notes","podcast SEO","episode description","podcast summary","show description","episode summary","podcast description","audio SEO"],
    # Student
    "university-application-sop":["personal statement","university application","statement of purpose","college application","admissions essay","application essay","SOP writing","university statement","application statement","uni application"],
    "resume-cv-builder":       ["resume","CV","curriculum vitae","job application","resume writing","CV writing","ATS resume","resume format","work history","resume structure"],
    "cover-letter-writer":     ["cover letter","application letter","job letter","cover letter writing","letter of application","accompanying letter","job cover letter","hiring letter","application cover","cover letter format"],
    "research-paper-outline":  ["research paper","academic paper","paper outline","research outline","literature review","academic writing","paper structure","thesis structure","research structure","academic outline"],
    "conference-abstract":     ["conference abstract","abstract submission","academic abstract","paper abstract","conference paper","abstract writing","research abstract","academic submission","call for papers","abstract format"],
    # Realtor
    "real-estate-listing-copy":["property listing","real estate listing","listing copy","property description","home listing","MLS listing","listing write-up","property copy","home description","listing text"],
    "real-estate-photo-prompt":["property photo","real estate photo","listing photo","home photography","property shot","architectural photo","real estate photography","property image","home photo brief","listing image"],
    "hotel-airbnb-listing-copy":["Airbnb listing","short-term rental","vacation rental listing","rental copy","STR listing","Airbnb description","holiday rental","rental listing","short let listing","holiday let copy"],
    # Educator
    "course-curriculum-builder":["course curriculum","curriculum design","learning curriculum","course outline","educational curriculum","course structure","learning pathway","course framework","curriculum planning","course design"],
    "lesson-plan-builder":     ["lesson plan","teaching plan","class plan","lesson structure","lesson objective","learning plan","teaching resource","classroom plan","lesson writing","lesson template"],
    "exam-paper-generator":    ["exam paper","test paper","assessment questions","exam questions","quiz paper","test questions","exam format","assessment design","question paper","exam writing"],
    # Wedding
    "wedding-vows-writer":     ["wedding vows","vow writing","personal vows","ceremony vows","vow exchange","writing vows","personalised vows","vow words","wedding ceremony words","vow draft"],
    "wedding-invitation-prompt":["wedding invitation","invitation copy","invite wording","invitation text","wedding invite","RSVP card","invitation wording","invite copy","wedding stationery copy","invitation brief"],
    "event-speech-writer":     ["wedding speech","event speech","best man speech","toast writing","speech writing","ceremony speech","reception speech","speech draft","speech structure","speech copy"],
    "menu-description-copy":   ["menu copy","menu description","food description","dish description","menu writing","restaurant menu","menu item copy","food copy","menu language","tasting menu copy"],
    # Creative
    "screenplay-script":       ["screenplay","script writing","film script","script structure","screenwriting","script format","three-act structure","scene writing","feature script","spec script"],
    "children-book-prompt":    ["children's book","picture book","kids' book","children's story","picture book prompt","children's writing","story for children","illustrated story","early reader","kids story"],
    "short-story-prompt":      ["short story","fiction writing","story writing","short fiction","story prompt","narrative writing","flash fiction","story structure","prose fiction","short-form fiction"],
    "poetry-verse-prompt":     ["poetry","poem writing","verse writing","poetic form","poem structure","lyric poetry","free verse","rhyming verse","spoken word","prose poem"],
    "book-cover-prompt":       ["book cover","cover design","cover brief","book cover design","cover prompt","cover art brief","book design","front cover","cover typography","cover concept"],
    "festival-holiday-greeting-prompt":["holiday greeting","seasonal copy","festive message","holiday message","greeting card copy","seasonal greeting","Christmas copy","holiday card","seasonal content","festive copy"],
    # Standalone
    "eulogy-writer":           ["eulogy","funeral speech","memorial speech","tribute speech","funeral tribute","memorial tribute","remembrance speech","memorial words","farewell speech","tribute writing"],
    "prd-writer":              ["PRD","product requirements","product spec","requirements document","feature spec","product brief","technical spec","product documentation","product requirements document","spec writing"],
    "architecture-diagram-prompt":["architecture diagram","system diagram","tech diagram","system architecture","infrastructure diagram","diagram prompt","system design diagram","technical diagram","service diagram","architecture map"],
    "logo-brand-identity":     ["logo design","brand identity","visual identity","brand design","logo brief","identity design","brand guidelines","logo concept","visual brand","branding brief"],
    "performance-review-writer":["performance review","annual review","employee review","review writing","performance assessment","staff review","360 review","appraisal writing","performance appraisal","review cycle"],
    "social-media-carousel-prompt":["carousel post","social carousel","swipe post","multi-slide post","carousel design","slide content","Instagram carousel","carousel brief","swipe carousel","slide deck social"],
    "health-wellness-plan":    ["wellness plan","health plan","fitness plan","wellness routine","health routine","wellbeing plan","lifestyle plan","wellness brief","health goal","wellness programme"],
    "travel-itinerary-planner":["travel itinerary","trip plan","travel plan","vacation itinerary","travel schedule","trip itinerary","travel route","itinerary writing","travel brief","trip planning"],
    "recipe-development-prompt":["recipe development","recipe writing","dish development","recipe copy","culinary brief","recipe prompt","food recipe","recipe brief","dish brief","recipe creation"],
    "home-renovation-brief":   ["renovation brief","renovation plan","home improvement","renovation project","interior brief","home renovation","building brief","refurbishment brief","contractor brief","renovation scope"],
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — BUNDLE TRIGGER KEYWORDS
# ─────────────────────────────────────────────────────────────────────────────

BUNDLE_KEYWORDS = {
    "founder":   ["as a founder","early-stage startup","pre-seed","fundraising","pitch to investors","startup toolkit","founding team","startup workflow","early-stage founder","building a startup"],
    "creator":   ["content creator","building an audience","content workflow","growing on social","creator economy","personal brand","building your brand","content output","creator workflow","audience growth"],
    "marketing": ["marketing team","marketing workflow","campaign creation","brand marketing","marketing copy","growth marketing","marketing toolkit","paid and organic","marketing output","campaign workflow"],
    "legal-biz": ["legal documents","business legal","compliance","contracts and agreements","business documentation","legal workflow","business formation","document workflow","legal writing","business compliance"],
    "video-pod": ["video and podcast","content production","video production","podcast production","video workflow","production workflow","film and audio","video and audio","production output","content production workflow"],
    "student":   ["student workflow","academic journey","applying to university","job hunting","graduate applications","student toolkit","academic writing toolkit","student applications","academic output","graduate toolkit"],
    "realtor":   ["property market","real estate business","listing workflow","property sales","real estate agent","property marketing","estate agent toolkit","letting agent","property workflow","real estate workflow"],
    "educator":  ["teaching workflow","classroom content","educational materials","course creation","teaching toolkit","curriculum development","academic content","teaching output","educator workflow","classroom toolkit"],
    "wedding":   ["wedding planning","the big day","wedding industry","event planning","wedding workflow","wedding content","wedding supplier","wedding vendor","planning a wedding","wedding business"],
    "creative":  ["creative writing","storytelling","fiction writing","creative workflow","writing for creatives","narrative craft","creative toolkit","creative output","creative process","fiction workflow"],
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — BLOG FILENAME → SKILL SLUG OVERRIDES
# ─────────────────────────────────────────────────────────────────────────────

BLOG_SLUG_OVERRIDES = {
    # Creative
    "The-Holiday-Greeting-Written-for-Everyone-and-Why-It-Lands-with-No-One": "festival-holiday-greeting-prompt",
    "The-Screenplay-AI-Gets-Wrong-and-What-a-Trained-Script-Skill-Fixes":     "screenplay-script",
    "The-Short-Story-AI-Gets-Right-When-It-Knows-Your-Genre":                 "short-story-prompt",
    "Why-AI-Poetry-Reads-Like-a-Greeting-Card-and-How-to-Fix-It":             "poetry-verse-prompt",
    "Why-your-second-childrens-book-doesnt-sound-like-your-first":            "children-book-prompt",
    "childrens-book-prompt":                                                   "children-book-prompt",
    "the-book-cover-brief-your-designer-actually-needs":                       "book-cover-prompt",
    "why-your-book-cover-looks-wrong":                                         "book-cover-prompt",
    # Creator / Social
    "The-LinkedIn-Post-That-Actually-Gets-Read-and-Why-Format-Is-Everything": "linkedin-post-engine",
    "Your-Brand-Voice-Is-the-One-Thing-AI-cant-fake":                         "brand-voice-guide",
    "Your-Social-Posts-Arent-Underperforming-Your-Brief-Is.":                 "social-content-engine",
    "seo-brief-for-freelancers":                                               "seo-blog-post-brief",
    "email-newsletter-subject-lines":                                          "email-newsletter-engine",
    # Founder / Biz
    "why-cold-emails-get-deleted":                                             "cold-outreach-email",
    "financial-model-why-spreadsheets-arent-the-problem":                     "financial-model-prompt",
    "visa-cover-letter-questions-answered":                                    "visa-application-cover-letter",
    # Video / Podcast / Film
    "how-to-write-ai-film-prompts-that-actually-work":                        "ai-animation-film-prompt",
    "the-ai-film-prompt-that-gives-sora-a-character-not-just-a-scene":        "dialogue-character-film-prompt",
    "podcast-scripted-vs-outlined-vs-improvised":                             "podcast-episode-script",
    "the-podcast-script-that-sounds-like-you-wrote-it-not-like-youre-reading-it": "podcast-episode-script",
    # Real Estate / Listings
    "how-to-write-real-estate-listing":                                        "real-estate-listing-copy",
    "airbnb-listing-copy-you-vs-ai-vs-calibrated-skill":                      "hotel-airbnb-listing-copy",
    "the-airbnb-listing-that-gets-booked-before-anyone-asks-about-parking":   "hotel-airbnb-listing-copy",
    # Wedding
    "how-to-write-wedding-vows-with-ai-that-actually-sound-like-you":         "wedding-vows-writer",
    "the-vows-that-sound-like-you-wrote-them-because-you-did":                "wedding-vows-writer",
    "the-wedding-speech-that-sounds-like-you-not-like-a-template":            "event-speech-writer",
    "wedding-invitation-your-invitation-sets-the-tone":                       "wedding-invitation-prompt",
    "why-menu-copy-fails-to-sell-food":                                       "menu-description-copy",
    # Education
    "online-course-curriculum-completion":                                     "course-curriculum-builder",
    "why-ai-lesson-plans-fail-the-learning-objective-test":                   "lesson-plan-builder",
    "why-your-research-paper-structure-fails-peer-review":                    "research-paper-outline",
    # Excluded — not skill blogs
    "index":   None,
    "index 2": None,
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — FALLBACK ANCHOR TEXT (used when injecting a closing paragraph)
# ─────────────────────────────────────────────────────────────────────────────

SKILL_ANCHOR = {
    "pitch-deck-narrative":          "a pitch narrative investors actually follow",
    "cold-outreach-email":           "cold emails calibrated to role and context",
    "sales-page":                    "a sales page that closes without feeling pushy",
    "business-plan":                 "a structured business plan built around your model",
    "investor-update-email":         "investor updates that keep momentum between rounds",
    "job-description-writer":        "job descriptions that attract the right candidates",
    "executive-bio":                 "an executive bio that positions you accurately",
    "one-pager-investor-brief":      "a one-pager that survives a ten-second scan",
    "brand-voice-guide":             "a brand voice that stays consistent across every channel",
    "linkedin-post-engine":          "LinkedIn posts that earn reach without paid promotion",
    "social-content-engine":         "social content built around what your audience engages with",
    "twitter-x-thread-engine":       "threads that hold attention from first line to last",
    "seo-blog-post-brief":           "blog briefs structured around how search actually ranks content",
    "email-newsletter-engine":       "newsletters that get opened and read past the first line",
    "content-calendar":              "a content calendar mapped to real publishing cadence",
    "ugc-ad-creator":                "UGC ad prompts that produce footage that converts",
    "brand-ad-copy":                 "ad copy calibrated to audience and format",
    "pr-press-release":              "a press release editors will actually read",
    "ecommerce-product-listing":     "product listings optimised for search and conversion",
    "product-photography-prompt":    "product photo briefs that match how buyers actually see",
    "financial-model-prompt":        "a financial model built around your actual assumptions",
    "grant-proposal-writing":        "a grant proposal structured around what reviewers score",
    "nda-contract-draft":            "an NDA drafted around your specific terms",
    "terms-of-service-privacy-policy": "terms and privacy policy that reflect your actual data practices",
    "visa-application-cover-letter": "a visa cover letter that addresses every required point",
    "short-form-ai-video":           "short-form video prompts built for vertical formats",
    "video-script":                  "a video script structured around viewer retention",
    "ai-animation-film-prompt":      "AI animation prompts with scene-level control",
    "product-ad-film-prompt":        "product ad film prompts that brief a director properly",
    "dialogue-character-film-prompt":"character dialogue prompts that hold a consistent voice",
    "podcast-episode-script":        "a podcast episode script with natural conversation flow",
    "webinar-online-event-script":   "a webinar script that keeps a live audience engaged",
    "youtube-thumbnail-prompt":      "thumbnail briefs engineered around click psychology",
    "podcast-show-notes":            "show notes formatted for both listeners and search",
    "university-application-sop":    "a personal statement that reads specific, not generic",
    "resume-cv-builder":             "a CV structured around what recruiters actually scan for",
    "cover-letter-writer":           "a cover letter that earns the interview, not just the read",
    "research-paper-outline":        "a research paper outline built around your argument",
    "conference-abstract":           "an abstract that clears the review committee",
    "real-estate-listing-copy":      "listing copy that sells the lifestyle, not just the specs",
    "real-estate-photo-prompt":      "real estate photo briefs that make buyers feel the space",
    "hotel-airbnb-listing-copy":     "a listing that converts browsers into confirmed bookings",
    "course-curriculum-builder":     "a course curriculum structured around real learning outcomes",
    "lesson-plan-builder":           "lesson plans built around how students actually retain things",
    "exam-paper-generator":          "exam questions calibrated to the right level and format",
    "wedding-vows-writer":           "vows that sound like you wrote them, not an AI",
    "wedding-invitation-prompt":     "wedding invitation copy that sets the right tone immediately",
    "event-speech-writer":           "a speech that lands on the night, not just on paper",
    "menu-description-copy":         "menu copy that makes every dish sound worth ordering",
    "screenplay-script":             "a screenplay structure that holds across three acts",
    "children-book-prompt":          "a children's book with the rhythm young readers follow",
    "short-story-prompt":            "a short story structure built around the turn that matters",
    "poetry-verse-prompt":           "verse that lands in the ear, not just on the page",
    "book-cover-prompt":             "a book cover brief that works before the title is read",
    "festival-holiday-greeting-prompt": "seasonal copy that avoids sounding like a template",
    "eulogy-writer":                 "a eulogy that honours the person, not the occasion",
    "prd-writer":                    "a PRD that engineering can build from without a meeting",
    "architecture-diagram-prompt":   "architecture diagrams that communicate decisions clearly",
    "logo-brand-identity":           "a brand identity brief that gives a designer real direction",
    "performance-review-writer":     "a performance review that is honest and useful",
    "social-media-carousel-prompt":  "carousel prompts designed for swipe-through completion",
    "health-wellness-plan":          "a wellness plan built around actual habits",
    "travel-itinerary-planner":      "an itinerary that accounts for how travel actually goes",
    "recipe-development-prompt":     "recipe copy that makes the dish sound worth making",
    "home-renovation-brief":         "a renovation brief that a contractor can actually quote from",
}

LAYER3_ANCHOR = {
    "pitch-deck-narrative":          ("the complete guide to pitch deck narratives",    "a calibrated narrative different from a generic slide deck"),
    "cold-outreach-email":           ("the complete guide to cold outreach email",      "a role-calibrated email different from a generic blast"),
    "sales-page":                    ("the complete guide to sales page copy",          "a converting page different from a generic landing page"),
    "business-plan":                 ("the complete guide to AI-assisted business plans","a structured plan different from a generic template"),
    "investor-update-email":         ("the complete guide to investor update emails",   "a useful update different from a generic check-in"),
    "job-description-writer":        ("the complete guide to job description writing",  "a targeted JD different from a generic posting"),
    "executive-bio":                 ("the complete guide to executive bios",           "a positioned bio different from a generic summary"),
    "one-pager-investor-brief":      ("the complete guide to investor one-pagers",      "a scannable brief different from a generic overview"),
    "brand-voice-guide":             ("the complete guide to brand voice guides",       "a consistent voice different from generic tone guidelines"),
    "linkedin-post-engine":          ("the complete guide to LinkedIn post writing",    "a post that earns reach versus one that disappears"),
    "social-content-engine":         ("the complete guide to social content creation",  "content built for engagement versus content built for volume"),
    "twitter-x-thread-engine":       ("the complete guide to writing X threads",        "a thread that holds attention versus one that loses it at line two"),
    "seo-blog-post-brief":           ("the complete guide to SEO blog post briefs",     "a brief that ranks versus one that gets ignored by search"),
    "email-newsletter-engine":       ("the complete guide to email newsletter writing", "a newsletter that gets read versus one that gets unsubscribed"),
    "content-calendar":              ("the complete guide to content calendar planning","a calendar built around cadence versus one built around hope"),
    "ugc-ad-creator":                ("the complete guide to UGC ad prompts",           "a brief that produces usable footage versus one that misses"),
    "brand-ad-copy":                 ("the complete guide to brand and ad copy",        "copy built for conversion versus copy built for the brief"),
    "pr-press-release":              ("the complete guide to press release writing",    "a release editors read versus one they skip"),
    "ecommerce-product-listing":     ("the complete guide to e-commerce product listings","a listing that converts versus one that informs"),
    "product-photography-prompt":    ("the complete guide to product photography briefs","a brief that captures the right shot versus a vague direction"),
    "financial-model-prompt":        ("the complete guide to AI financial model prompts","a model built on assumptions versus one built on templates"),
    "grant-proposal-writing":        ("the complete guide to grant proposal writing",   "a proposal reviewers score highly versus one they pass over"),
    "nda-contract-draft":            ("the complete guide to NDA drafting with AI",     "a draft built around your terms versus a generic fill-in"),
    "terms-of-service-privacy-policy":("the complete guide to ToS and privacy policy writing","policy copy that reflects actual practices versus boilerplate"),
    "visa-application-cover-letter": ("the complete guide to visa application letters", "a letter that addresses every point versus one that misses criteria"),
    "short-form-ai-video":           ("the complete guide to short-form AI video prompts","a vertical video prompt versus a generic script"),
    "video-script":                  ("the complete guide to video script writing",     "a script built for retention versus one built for length"),
    "ai-animation-film-prompt":      ("the complete guide to AI animation prompts",     "a scene-level prompt versus a vague style direction"),
    "product-ad-film-prompt":        ("the complete guide to product ad film prompts",  "a director-ready brief versus a rough concept"),
    "dialogue-character-film-prompt":("the complete guide to character dialogue prompts","dialogue that holds voice versus generic back-and-forth"),
    "podcast-episode-script":        ("the complete guide to podcast episode scripting","a script with natural flow versus a rigid outline"),
    "webinar-online-event-script":   ("the complete guide to webinar scripting",        "a live-ready script versus one that loses the audience"),
    "youtube-thumbnail-prompt":      ("the complete guide to YouTube thumbnail briefs", "a CTR-engineered prompt different from a generic image brief"),
    "podcast-show-notes":            ("the complete guide to podcast show notes",       "notes that rank in search versus notes that just recap"),
    "university-application-sop":    ("the complete guide to university application statements","a personal statement that reads specific versus one that sounds generic"),
    "resume-cv-builder":             ("the complete guide to AI resume writing",        "a CV built for ATS and humans versus a standard template"),
    "cover-letter-writer":           ("the complete guide to cover letter writing",     "a letter that earns an interview versus one that fills the form"),
    "research-paper-outline":        ("the complete guide to research paper outlines",  "an argument-driven outline versus a section-by-section filler"),
    "conference-abstract":           ("the complete guide to conference abstract writing","an abstract that clears review versus one that gets declined"),
    "real-estate-listing-copy":      ("the complete guide to real estate listing copy", "copy that sells a lifestyle versus copy that lists features"),
    "real-estate-photo-prompt":      ("the complete guide to real estate photo briefs", "a brief that makes buyers feel the space versus a checklist"),
    "hotel-airbnb-listing-copy":     ("the complete guide to short-term rental listings","copy that converts a browser into a booking"),
    "course-curriculum-builder":     ("the complete guide to AI course curriculum design","a curriculum built on outcomes versus one built on topics"),
    "lesson-plan-builder":           ("the complete guide to lesson plan writing",      "a plan built for retention versus one built for coverage"),
    "exam-paper-generator":          ("the complete guide to AI exam paper generation", "questions calibrated to level versus questions that just fill a page"),
    "wedding-vows-writer":           ("the complete guide to writing wedding vows",     "vows that sound like you versus vows that sound borrowed"),
    "wedding-invitation-prompt":     ("the complete guide to wedding invitation copy",  "copy that sets tone immediately versus generic formal wording"),
    "event-speech-writer":           ("the complete guide to event speech writing",     "a speech that lands on the night versus one that reads well on paper"),
    "menu-description-copy":         ("the complete guide to menu copy writing",        "descriptions that make dishes sound worth ordering versus ones that just name them"),
    "screenplay-script":             ("the complete guide to AI screenplay structure",  "a three-act structure that holds versus a loose scene collection"),
    "children-book-prompt":          ("the complete guide to children's book prompts",  "a story with the rhythm young readers follow versus one they put down"),
    "short-story-prompt":            ("the complete guide to short story prompts",      "a story built around the right turn versus one that meanders"),
    "poetry-verse-prompt":           ("the complete guide to poetry and verse prompts", "verse that lands in the ear versus one that sits on the page"),
    "book-cover-prompt":             ("the complete guide to book cover briefs",        "a cover that works before the title is read versus a decorative one"),
    "festival-holiday-greeting-prompt":("the complete guide to seasonal greeting copy","copy that avoids sounding like a template versus copy that does"),
    "eulogy-writer":                 ("the complete guide to eulogy writing",           "a eulogy that honours the person versus one that honours the occasion"),
    "prd-writer":                    ("the complete guide to writing PRDs with AI",     "a spec engineers can build from versus one that needs a follow-up meeting"),
    "architecture-diagram-prompt":   ("the complete guide to architecture diagram prompts","diagrams that communicate decisions versus ones that just describe components"),
    "logo-brand-identity":           ("the complete guide to brand identity briefs",    "a brief that gives a designer real direction versus a mood board"),
    "performance-review-writer":     ("the complete guide to performance review writing","a review that is useful versus one that is diplomatic and vague"),
    "social-media-carousel-prompt":  ("the complete guide to social media carousel prompts","a carousel built for swipe-through versus one built for looks"),
    "health-wellness-plan":          ("the complete guide to AI wellness planning",     "a plan built around real habits versus one built around ideals"),
    "travel-itinerary-planner":      ("the complete guide to AI travel itineraries",    "a plan that accounts for how travel actually goes versus a wishlist"),
    "recipe-development-prompt":     ("the complete guide to recipe development prompts","copy that makes a dish sound worth making versus one that just lists steps"),
    "home-renovation-brief":         ("the complete guide to home renovation briefs",   "a brief a contractor can quote from versus a vague wishlist"),
}


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

SKIP_TAG_NAMES = {"a", "title", "script", "style", "head", "h1"}

def url_already_present(soup, url):
    return bool(soup.find("a", href=url))

def find_main_content(soup):
    for sel in ["article","main",".blog-content",".post-content",".entry-content",".content",".blog-body","#content"]:
        el = soup.select_one(sel)
        if el:
            return el
    return soup.body or soup

def find_last_paragraph(container):
    paras = container.find_all("p")
    meaningful = [p for p in paras if len(p.get_text(strip=True)) > 60]
    return meaningful[-1] if meaningful else None


def inject_keyword_link(container, keywords, target_url):
    """
    Scan all text nodes in container for the first matching keyword phrase.
    Wrap the matched text in <a href=target_url>.
    Returns (True, matched_keyword) or (False, None).
    Skips text nodes inside <a>, <h1>, <script>, <style>, <title>.
    Only wraps the very first match found across all keywords.
    """
    def has_skip_ancestor(tag):
        for parent in tag.parents:
            if getattr(parent, "name", None) in SKIP_TAG_NAMES:
                return True
        return False

    for keyword in keywords:
        pattern = re.compile(r'(?<!\w)' + re.escape(keyword) + r'(?!\w)', re.IGNORECASE)
        for text_node in container.find_all(string=True):
            if not isinstance(text_node, NavigableString):
                continue
            if has_skip_ancestor(text_node):
                continue
            text = str(text_node)
            m = pattern.search(text)
            if m:
                before = text[:m.start()]
                matched = text[m.start():m.end()]
                after  = text[m.end():]
                a_tag  = BeautifulSoup(f'<a href="{target_url}">{matched}</a>', "html.parser").find("a")
                # Replace text node with [before_text, <a>, after_text]
                parent = text_node.parent
                idx    = list(parent.children).index(text_node)
                text_node.extract()
                nodes = []
                if before:
                    nodes.append(NavigableString(before))
                nodes.append(a_tag)
                if after:
                    nodes.append(NavigableString(after))
                for i, node in enumerate(nodes):
                    if i == 0:
                        parent.insert(idx, node)
                    else:
                        nodes[i-1].insert_after(node)
                return True, matched
    return False, None


def build_fallback_paragraph(skill_slug, next_blog_slug, injected_skill, injected_bundle):
    """
    Build closing fallback <p> for any links that didn't get keyword-injected.
    Only includes sentences for links not already injected.
    """
    parts = []
    bundle_info = SKILL_BUNDLE.get(skill_slug, (None, None))
    bundle_slug_v, bundle_name = bundle_info

    if not injected_skill:
        anchor = SKILL_ANCHOR.get(skill_slug, f"the {skill_slug.replace('-',' ')} skill")
        parts.append(f'If you\'re doing this manually, <a href="{skill_url(skill_slug)}">{anchor}</a> is the faster path.')

    if next_blog_slug:
        next_anchor = SKILL_ANCHOR.get(next_blog_slug, f"the {next_blog_slug.replace('-',' ')} guide")
        parts.append(f'The next piece most people tackle from here is <a href="{blog_url(next_blog_slug)}">{next_anchor}</a>.')

    if not injected_bundle and bundle_slug_v:
        parts.append(f'If you\'re working across the full {bundle_name} workflow, the <a href="{bundle_url(bundle_slug_v)}">{bundle_name} bundle</a> covers everything in one place.')

    if parts:
        return f"<p>{' '.join(parts)}</p>"
    return ""


def find_not_what_box(soup):
    INLINE = {"span","p","h1","h2","h3","h4","h5","h6","strong","em","b","i","label","small"}

    def walk_up(tag):
        el = tag.parent
        while el and el.name in INLINE:
            el = el.parent
        return el

    # Strategy 1 — exact heading phrases
    exact = ["not what this is for","not what it's for","what this is not for","this is not for","what this isn't","not for","not designed for","won't help with","doesn't cover","does not cover","limitations"]
    for tag in soup.find_all(["h1","h2","h3","h4","h5","h6","p","span","div","label","small"]):
        text = tag.get_text(separator=" ", strip=True).lower()
        for phrase in exact:
            if phrase in text and len(text) < 120:
                c = walk_up(tag)
                if c:
                    return c

    # Strategy 2 — keyword scan in short elements
    kws = ["not what","not for","won't","doesn't","cannot","limitation","exclud"]
    for tag in soup.find_all(True):
        if tag.name in ["html","body"]:
            continue
        text = tag.get_text(separator=" ", strip=True).lower()
        if any(k in text for k in kws) and len(text) < 300:
            c = walk_up(tag)
            if c and c.name not in ["html","body"]:
                return c

    # Strategy 3 — negative-dominant list
    neg = ("not ","no ","won't","doesn't","cannot","–","—","×","x ")
    for ul in soup.find_all(["ul","ol"]):
        items = ul.find_all("li")
        if sum(1 for li in items if li.get_text(strip=True).lower()[:6] in [s[:6] for s in neg]) >= 2:
            return ul.parent or ul

    # Strategy 4 — last section before buy CTA
    buy_kws = ["checkout","buy","purchase","get this","add to cart","/cart","/buy"]
    last_good = None
    for el in soup.find_all(["section","div","aside"]):
        links = el.find_all("a", href=True)
        if any(any(k in (a.get("href","") + a.get_text()).lower() for k in buy_kws) for a in links):
            break
        if len(el.get_text(strip=True)) > 30:
            last_good = el
    return last_good


def build_layer3_sentence(skill_slug, blog_file_stem):
    anchor_text, differentiator = LAYER3_ANCHOR.get(
        skill_slug,
        (f"the complete guide to {skill_slug.replace('-',' ')}", "a calibrated output different from a generic one")
    )
    return f'<p><a href="{blog_url(blog_file_stem)}">{anchor_text.capitalize()}</a> covers what makes {differentiator}.</p>'


def match_blog_to_skill(blog_stem):
    if blog_stem in BLOG_SLUG_OVERRIDES:
        return BLOG_SLUG_OVERRIDES[blog_stem]
    all_slugs = list(SKILL_BUNDLE.keys())
    if blog_stem in all_slugs:
        return blog_stem
    candidates = [s for s in all_slugs if s in blog_stem or blog_stem in s]
    if candidates:
        return max(candidates, key=len)
    return None


def process_blog(html_path, skill_slug, log_rows, skipped):
    source = html_path.read_text(encoding="utf-8", errors="replace")
    soup   = BeautifulSoup(source, "html.parser")
    container = find_main_content(soup)

    s_url      = skill_url(skill_slug)
    next_slug  = DAISY_CHAIN.get(skill_slug)
    n_url      = blog_url(next_slug) if next_slug else None
    b_slug, b_name = SKILL_BUNDLE.get(skill_slug, (None, None))
    b_url      = bundle_url(b_slug) if b_slug else None

    injected_skill  = False
    injected_next   = False
    injected_bundle = False
    actions = []

    # ── Layer 1: inject skill keyword link ──────────────────────────────────
    if not url_already_present(soup, s_url):
        keywords = SKILL_KEYWORDS.get(skill_slug, [])
        ok, matched = inject_keyword_link(container, keywords, s_url)
        if ok:
            injected_skill = True
            actions.append(f"L1 injected on '{matched}'")
    else:
        injected_skill = True
        actions.append("L1 already present")

    # ── Layer 2: inject next-blog keyword link ───────────────────────────────
    if next_slug and not url_already_present(soup, n_url):
        keywords = SKILL_KEYWORDS.get(next_slug, [])
        ok, matched = inject_keyword_link(container, keywords, n_url)
        if ok:
            injected_next = True
            actions.append(f"L2 injected on '{matched}'")
    elif next_slug:
        injected_next = True
        actions.append("L2 already present")

    # ── Layer 2b: inject bundle keyword link ─────────────────────────────────
    if b_slug and not url_already_present(soup, b_url):
        keywords = BUNDLE_KEYWORDS.get(b_slug, [])
        ok, matched = inject_keyword_link(container, keywords, b_url)
        if ok:
            injected_bundle = True
            actions.append(f"L2b bundle injected on '{matched}'")
    elif b_slug:
        injected_bundle = True
        actions.append("L2b already present")

    # ── Fallback paragraph for anything not injected ─────────────────────────
    fallback_html = build_fallback_paragraph(
        skill_slug,
        next_slug if not injected_next else None,
        injected_skill,
        injected_bundle
    )
    if fallback_html:
        last_para = find_last_paragraph(container)
        if last_para:
            new_tag = BeautifulSoup(fallback_html, "html.parser")
            last_para.insert_after(new_tag)
            actions.append("fallback para appended")
        else:
            skipped.append(f"[BLOG] {html_path.name} — no paragraph for fallback insertion")

    changed = bool(actions)
    log_rows.append({
        "file": html_path.name, "type": "blog",
        "skill": skill_slug, "actions": " | ".join(actions)
    })
    return soup, changed


def process_skill_page(html_path, skill_slug, blog_file_stem, log_rows, skipped):
    source = html_path.read_text(encoding="utf-8", errors="replace")
    soup   = BeautifulSoup(source, "html.parser")
    b_url  = blog_url(blog_file_stem)

    if url_already_present(soup, b_url):
        log_rows.append({"file": html_path.name, "type": "skill-page", "skill": skill_slug, "actions": "L3 already present"})
        return soup, False

    container = find_not_what_box(soup)
    if not container:
        skipped.append(f"[SKILL] {html_path.name} — insertion point not found")
        return soup, False

    new_tag = BeautifulSoup(build_layer3_sentence(skill_slug, blog_file_stem), "html.parser")
    container.insert_after(new_tag)
    log_rows.append({"file": html_path.name, "type": "skill-page", "skill": skill_slug, "actions": "L3 back-link added"})
    return soup, True


def write_output(soup, original_path, output_root, subfolder):
    out_dir  = output_root / subfolder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / original_path.name
    out_path.write_text(str(soup), encoding="utf-8")
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Novakit Blog Interlinking v3")
    parser.add_argument("--blogs",  required=True)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--output", default="./modified")
    parser.add_argument("--run",    action="store_true")
    parser.add_argument("--test",   default=None, help="Test with one skill slug only")
    args = parser.parse_args()

    blogs_dir  = Path(args.blogs)
    skills_dir = Path(args.skills)
    output_dir = Path(args.output)
    dry_run    = not args.run

    print(f"\n{'⚠  DRY RUN — pass --run to write files' if dry_run else f'✅  LIVE RUN → {output_dir}'}\n")
    if args.test:
        print(f"🧪  TEST MODE — skill: {args.test}\n")

    blog_files  = sorted(blogs_dir.glob("*.html"))
    skill_files = {f.stem: f for f in skills_dir.glob("*.html")}
    log_rows, skipped = [], []

    print(f"{'FILE':<52} {'SKILL':<32} ACTIONS")
    print("─" * 120)

    for blog_path in blog_files:
        skill_slug = match_blog_to_skill(blog_path.stem)

        if skill_slug is None:
            if blog_path.stem in BLOG_SLUG_OVERRIDES and BLOG_SLUG_OVERRIDES[blog_path.stem] is None:
                print(f"  {blog_path.name:<52} {'—':<32} EXCLUDED")
            else:
                skipped.append(f"[BLOG] {blog_path.name} — no skill match")
                print(f"  {blog_path.name:<52} {'—':<32} SKIPPED")
            continue

        if args.test and skill_slug != args.test:
            continue

        mod_soup, changed = process_blog(blog_path, skill_slug, log_rows, skipped)
        action_str = next((r["actions"] for r in reversed(log_rows) if r["file"] == blog_path.name), "")
        print(f"  {blog_path.name:<52} {skill_slug:<32} {action_str}")

        if changed and not dry_run:
            write_output(mod_soup, blog_path, output_dir, "blog")

        # Skill page Layer 3
        skill_page = skill_files.get(skill_slug)
        if not skill_page:
            skipped.append(f"[SKILL] {skill_slug}.html not found")
            continue

        sk_soup, sk_changed = process_skill_page(skill_page, skill_slug, blog_path.stem, log_rows, skipped)
        sk_action = next((r["actions"] for r in reversed(log_rows) if r["file"] == skill_page.name), "")
        print(f"  {'  └─ ' + skill_page.name:<52} {skill_slug:<32} {sk_action}")

        if sk_changed and not dry_run:
            write_output(sk_soup, skill_page, output_dir, "skills")

    print("\n" + "─" * 120)
    print(f"Done. Skipped: {len(skipped)}")

    if not dry_run:
        with open("link-log.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["file","type","skill","actions"], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(log_rows)
        print("Log → link-log.csv")

    if skipped:
        with open("skipped.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(skipped))
        print("Skipped → skipped.txt")
        for s in skipped:
            print(f"  {s}")
    print()

if __name__ == "__main__":
    main()
