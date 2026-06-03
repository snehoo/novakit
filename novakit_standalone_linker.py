#!/usr/bin/env python3
"""
novakit_standalone_linker.py — Targeted Interlinking for Standalone Skills
===========================================================================
Runs the full keyword-injection + fallback linking logic ONLY for the 11
standalone skills that have no bundle and were missed in the main run.

Skills covered:
  prd-writer, dialogue-character-film-prompt, architecture-diagram-prompt,
  logo-brand-identity, performance-review-writer, social-media-carousel-prompt,
  health-wellness-plan, travel-itinerary-planner, recipe-development-prompt,
  home-renovation-brief, eulogy-writer

Usage
-----
  # Dry run (default)
  python3 novakit_standalone_linker.py --blogs ./blog --skills ./skills

  # Live run
  python3 novakit_standalone_linker.py --blogs ./blog --skills ./skills --output ./modified --run

Requirements: pip install beautifulsoup4
"""

import re
import csv
import argparse
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = "https://novakit.tech"

def skill_url(slug): return f"{BASE_URL}/skills/{slug}.html"
def blog_url(slug):  return f"{BASE_URL}/blog/{slug}.html"


# ─────────────────────────────────────────────────────────────────────────────
# THE 11 STANDALONE SKILLS
# slug → (display_name, [trigger_keywords], next_slug_in_chain)
# ─────────────────────────────────────────────────────────────────────────────

STANDALONES = {
    "prd-writer": {
        "name":     "PRD Writer",
        "keywords": ["PRD","product requirements","product spec","requirements document",
                     "feature spec","product brief","technical spec","product documentation",
                     "product requirements document","spec writing"],
        "next":     "pitch-deck-narrative",
        "anchor":   "a PRD that engineering can build from without a follow-up meeting",
        "layer3":   ("the complete guide to writing PRDs with AI",
                     "a spec engineers can act on versus one that needs a follow-up meeting"),
    },
    "dialogue-character-film-prompt": {
        "name":     "Dialogue & Character Film Prompt",
        "keywords": ["character dialogue","film dialogue","scene prompt","character voice",
                     "dialogue writing","film scene","character brief","Sora character",
                     "scene writing","character script"],
        "next":     "podcast-episode-script",
        "anchor":   "character dialogue prompts that hold a consistent voice",
        "layer3":   ("the complete guide to character dialogue prompts",
                     "dialogue that holds voice versus generic back-and-forth"),
    },
    "architecture-diagram-prompt": {
        "name":     "Architecture Diagram Prompt",
        "keywords": ["architecture diagram","system diagram","tech diagram","system architecture",
                     "infrastructure diagram","diagram prompt","system design diagram",
                     "technical diagram","service diagram","architecture map"],
        "next":     "prd-writer",
        "anchor":   "architecture diagrams that communicate decisions clearly",
        "layer3":   ("the complete guide to architecture diagram prompts",
                     "diagrams that communicate decisions versus ones that just describe components"),
    },
    "logo-brand-identity": {
        "name":     "Logo & Brand Identity",
        "keywords": ["logo design","brand identity","visual identity","brand design",
                     "logo brief","identity design","brand guidelines","logo concept",
                     "visual brand","branding brief"],
        "next":     "brand-voice-guide",
        "anchor":   "a brand identity brief that gives a designer real direction",
        "layer3":   ("the complete guide to brand identity briefs",
                     "a brief that gives a designer real direction versus a mood board"),
    },
    "performance-review-writer": {
        "name":     "Performance Review Writer",
        "keywords": ["performance review","annual review","employee review","review writing",
                     "performance assessment","staff review","360 review","appraisal writing",
                     "performance appraisal","review cycle"],
        "next":     "resume-cv-builder",
        "anchor":   "a performance review that is honest and actually useful",
        "layer3":   ("the complete guide to performance review writing",
                     "a review that is useful versus one that is diplomatic and vague"),
    },
    "social-media-carousel-prompt": {
        "name":     "Social Media Carousel Prompt",
        "keywords": ["carousel post","social carousel","swipe post","multi-slide post",
                     "carousel design","slide content","Instagram carousel","carousel brief",
                     "swipe carousel","slide deck social"],
        "next":     "social-content-engine",
        "anchor":   "carousel prompts designed for swipe-through completion",
        "layer3":   ("the complete guide to social media carousel prompts",
                     "a carousel built for swipe-through versus one built for looks"),
    },
    "health-wellness-plan": {
        "name":     "Health & Wellness Plan",
        "keywords": ["wellness plan","health plan","fitness plan","wellness routine",
                     "health routine","wellbeing plan","lifestyle plan","wellness brief",
                     "health goal","wellness programme"],
        "next":     "brand-voice-guide",
        "anchor":   "a wellness plan built around actual habits, not aspirations",
        "layer3":   ("the complete guide to AI wellness planning",
                     "a plan built around real habits versus one built around ideals"),
    },
    "travel-itinerary-planner": {
        "name":     "Travel Itinerary Planner",
        "keywords": ["travel itinerary","trip plan","travel plan","vacation itinerary",
                     "travel schedule","trip itinerary","travel route","itinerary writing",
                     "travel brief","trip planning"],
        "next":     "hotel-airbnb-listing-copy",
        "anchor":   "an itinerary that accounts for how travel actually goes",
        "layer3":   ("the complete guide to AI travel itineraries",
                     "a plan that accounts for how travel actually goes versus a wishlist"),
    },
    "recipe-development-prompt": {
        "name":     "Recipe Development Prompt",
        "keywords": ["recipe development","recipe writing","dish development","recipe copy",
                     "culinary brief","recipe prompt","food recipe","recipe brief",
                     "dish brief","recipe creation"],
        "next":     "menu-description-copy",
        "anchor":   "recipe copy that makes the dish sound worth making",
        "layer3":   ("the complete guide to recipe development prompts",
                     "copy that makes a dish sound worth making versus one that just lists steps"),
    },
    "home-renovation-brief": {
        "name":     "Home Renovation Brief",
        "keywords": ["renovation brief","renovation plan","home improvement","renovation project",
                     "interior brief","home renovation","building brief","refurbishment brief",
                     "contractor brief","renovation scope"],
        "next":     "real-estate-listing-copy",
        "anchor":   "a renovation brief that a contractor can actually quote from",
        "layer3":   ("the complete guide to home renovation briefs",
                     "a brief a contractor can quote from versus a vague wishlist"),
    },
    "eulogy-writer": {
        "name":     "Eulogy Writer",
        "keywords": ["eulogy","funeral speech","memorial speech","tribute speech",
                     "funeral tribute","memorial tribute","remembrance speech",
                     "memorial words","farewell speech","tribute writing"],
        "next":     "event-speech-writer",
        "anchor":   "a eulogy that honours the person, not the occasion",
        "layer3":   ("the complete guide to eulogy writing",
                     "a eulogy that honours the person versus one that honours the occasion"),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# BLOG FILENAME → SKILL SLUG for standalone blogs
# Add entries here if your blog filenames don't contain the skill slug.
# ─────────────────────────────────────────────────────────────────────────────

STANDALONE_OVERRIDES = {
    "what-a-generic-ai-eulogy-sounds-like":              "eulogy-writer",
    "why-ai-dialogue-sounds-flat":                       "dialogue-character-film-prompt",
    "why-ai-travel-itineraries-feel-generic":            "travel-itinerary-planner",
    "why-your-architecture-diagram-confuses-everyone":   "architecture-diagram-prompt",
    "why-your-carousel-slides-get-scrolled-past":        "social-media-carousel-prompt",
}

# Skill page filename overrides — slug → actual file stem
SKILL_FILE_OVERRIDES = {
    # slug used in linker scripts → actual skill page filename stem (products.js key)
    "short-form-ai-video":           "ai-video-prompt",
    "grant-proposal-writing":        "grant-and-proposal-writing",
    "logo-brand-identity":           "logo-brand-identity-prompt",
    "sales-page":                    "sales-landing-page-copy",
    "terms-of-service-privacy-policy":"tos-privacy-policy",
    "university-application-sop":    "university-sop",
    "visa-application-cover-letter": "visa-cover-letter",
    "video-script":                  "video-script-engine",
    "children-book-prompt":          "childrens-book-prompt",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

SKIP_TAGS = {"a", "title", "script", "style", "head", "h1"}

def url_present(soup, url):
    return bool(soup.find("a", href=url))

def find_content(soup):
    for sel in ["article","main",".blog-content",".post-content",
                ".entry-content",".content",".blog-body","#content"]:
        el = soup.select_one(sel)
        if el:
            return el
    return soup.body or soup

def find_last_para(container):
    paras = [p for p in container.find_all("p") if len(p.get_text(strip=True)) > 60]
    return paras[-1] if paras else None

def has_skip_ancestor(node):
    for p in node.parents:
        if getattr(p, "name", None) in SKIP_TAGS:
            return True
    return False

def inject_link(container, keywords, url):
    """Wrap first keyword match in <a href=url>. Returns (True, matched_text) or (False, None)."""
    for kw in keywords:
        pat = re.compile(r'(?<!\w)' + re.escape(kw) + r'(?!\w)', re.IGNORECASE)
        for node in container.find_all(string=True):
            if not isinstance(node, NavigableString) or has_skip_ancestor(node):
                continue
            m = pat.search(str(node))
            if m:
                before, matched, after = str(node)[:m.start()], str(node)[m.start():m.end()], str(node)[m.end():]
                a_tag = BeautifulSoup(f'<a href="{url}">{matched}</a>', "html.parser").find("a")
                parent = node.parent
                idx = list(parent.children).index(node)
                node.extract()
                nodes = ([NavigableString(before)] if before else []) + [a_tag] + ([NavigableString(after)] if after else [])
                for i, n in enumerate(nodes):
                    if i == 0: parent.insert(idx, n)
                    else: nodes[i-1].insert_after(n)
                return True, matched
    return False, None

def find_not_what_box(soup):
    INLINE = {"span","p","h1","h2","h3","h4","h5","h6","strong","em","b","i","label","small"}

    def walk_up(tag):
        el = tag.parent
        while el and el.name in INLINE:
            el = el.parent
        return el

    # Exact phrase in short elements
    for tag in soup.find_all(["h1","h2","h3","h4","h5","h6","p","span","div","label","small"]):
        text = tag.get_text(separator=" ", strip=True).lower()
        for phrase in ["not what this is for","not what it's for","this is not for",
                       "what this isn't","not for","not designed for","doesn't cover","limitations"]:
            if phrase in text and len(text) < 120:
                c = walk_up(tag)
                if c: return c

    # Negative keyword scan
    for tag in soup.find_all(True):
        if tag.name in ["html","body"]: continue
        text = tag.get_text(separator=" ", strip=True).lower()
        if any(k in text for k in ["not what","not for","won't","doesn't","cannot","limitation"]) and len(text) < 300:
            c = walk_up(tag)
            if c and c.name not in ["html","body"]: return c

    # Negative-dominant list
    for ul in soup.find_all(["ul","ol"]):
        items = ul.find_all("li")
        if sum(1 for li in items if li.get_text(strip=True).lower()[:6] in ["not ", "no ", "won't", "doesn't", "cannot", "–     ", "—     "][:6]) >= 2:
            return ul.parent or ul

    # Last section before buy CTA
    last_good = None
    for el in soup.find_all(["section","div","aside"]):
        links = el.find_all("a", href=True)
        if any(any(k in (a.get("href","") + a.get_text()).lower()
               for k in ["checkout","buy","purchase","get this","/cart","/buy"]) for a in links):
            break
        if len(el.get_text(strip=True)) > 30:
            last_good = el
    return last_good

def match_blog(stem, slug):
    """Return True if this blog file matches the given skill slug."""
    if stem in STANDALONE_OVERRIDES:
        return STANDALONE_OVERRIDES[stem] == slug
    if stem == slug or slug in stem:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Novakit Standalone Skills Linker")
    parser.add_argument("--blogs",  required=True)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--output", default="./modified")
    parser.add_argument("--run",    action="store_true")
    args = parser.parse_args()

    blogs_dir  = Path(args.blogs)
    skills_dir = Path(args.skills)
    output_dir = Path(args.output)
    dry_run    = not args.run

    print(f"\n{'⚠  DRY RUN' if dry_run else f'✅  LIVE RUN → {output_dir}'}\n")
    print(f"Targeting {len(STANDALONES)} standalone skills\n")
    print(f"{'FILE':<52} {'SKILL':<36} ACTIONS")
    print("─" * 120)

    blog_files  = sorted(blogs_dir.glob("*.html"))
    skill_files = {f.stem: f for f in skills_dir.glob("*.html")}
    log_rows, skipped = [], []

    for slug, meta in STANDALONES.items():
        keywords  = meta["keywords"]
        next_slug = meta["next"]
        anchor    = meta["anchor"]
        l3_anchor, l3_diff = meta["layer3"]

        # Find matching blog file
        matching = [f for f in blog_files if match_blog(f.stem, slug)]

        if not matching:
            skipped.append(f"[BLOG] No blog file found for: {slug}")
            print(f"  {'— no file —':<52} {slug:<36} SKIPPED — no blog found")
            continue

        for blog_path in matching:
            source    = blog_path.read_text(encoding="utf-8", errors="replace")
            soup      = BeautifulSoup(source, "html.parser")
            container = find_content(soup)
            actions   = []

            # Layer 1 — blog → skill page
            s_url = skill_url(slug)
            if not url_present(soup, s_url):
                ok, matched = inject_link(container, keywords, s_url)
                if ok:
                    actions.append(f"L1 injected '{matched}'")
                else:
                    # fallback para for L1
                    lp = find_last_para(container)
                    if lp:
                        fb = BeautifulSoup(
                            f'<p>If you\'re doing this manually, <a href="{s_url}">{anchor}</a> is the faster path.</p>',
                            "html.parser"
                        )
                        lp.insert_after(fb)
                        actions.append("L1 fallback para")
                    else:
                        skipped.append(f"[BLOG] {blog_path.name} — no para for L1 fallback")
            else:
                actions.append("L1 present")

            # Layer 2 — blog → next blog in chain
            n_url = blog_url(next_slug)
            if not url_present(soup, n_url):
                next_kws = [next_slug.replace("-", " "), next_slug.replace("-", " ").title()]
                ok, matched = inject_link(container, next_kws, n_url)
                if ok:
                    actions.append(f"L2 injected '{matched}'")
                else:
                    next_anchor = next_slug.replace("-", " ")
                    lp = find_last_para(container)
                    if lp:
                        fb = BeautifulSoup(
                            f'<p>The next piece most people tackle from here is '
                            f'<a href="{n_url}">{next_anchor}</a>.</p>',
                            "html.parser"
                        )
                        lp.insert_after(fb)
                        actions.append("L2 fallback para")
            else:
                actions.append("L2 present")

            changed = bool(actions)
            print(f"  {blog_path.name:<52} {slug:<36} {' | '.join(actions)}")

            if changed and not dry_run:
                out_dir  = output_dir / "blog"
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / blog_path.name).write_text(str(soup), encoding="utf-8")

            log_rows.append({"file": blog_path.name, "skill": slug, "actions": " | ".join(actions)})

            # Layer 3 — skill page → blog
            sp = skill_files.get(SKILL_FILE_OVERRIDES.get(slug, slug))
            if not sp:
                skipped.append(f"[SKILL] {slug}.html not in skills folder")
                continue

            sk_src  = sp.read_text(encoding="utf-8", errors="replace")
            sk_soup = BeautifulSoup(sk_src, "html.parser")
            b_url   = blog_url(blog_path.stem)

            if not url_present(sk_soup, b_url):
                box = find_not_what_box(sk_soup)
                if box:
                    sentence = (f'<p><a href="{b_url}">{l3_anchor.capitalize()}</a> '
                                f'covers what makes {l3_diff}.</p>')
                    box.insert_after(BeautifulSoup(sentence, "html.parser"))
                    sk_action = "L3 added"
                    if not dry_run:
                        out_dir = output_dir / "skills"
                        out_dir.mkdir(parents=True, exist_ok=True)
                        (out_dir / sp.name).write_text(str(sk_soup), encoding="utf-8")
                else:
                    sk_action = "L3 — insertion point not found"
                    skipped.append(f"[SKILL] {sp.name} — not-what box not found")
            else:
                sk_action = "L3 present"

            print(f"  {'  └─ ' + sp.name:<52} {slug:<36} {sk_action}")

    print("\n" + "─" * 120)
    print(f"Done. Skipped: {len(skipped)}")

    if not dry_run and log_rows:
        with open("standalone-link-log.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["file","skill","actions"])
            w.writeheader(); w.writerows(log_rows)
        print("Log → standalone-link-log.csv")

    if skipped:
        with open("standalone-skipped.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(skipped))
        print("Skipped → standalone-skipped.txt")
        for s in skipped: print(f"  {s}")
    print()

if __name__ == "__main__":
    main()
