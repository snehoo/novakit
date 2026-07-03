# NovaKit Brag Video – Hyperframes Composition Brief

**Format:** 9:16 vertical (390 × 844 px viewport)  
**Duration:** 18.08 seconds @ 30fps  
**Music:** "Les Prisonnières – Epic Electronic" by Bensound, 126 BPM, cinematic/trailer-style. Free license — attribution "Music: bensound.com" required in share copy. File: `assets/music/les-prisonnieres.mp3`, cue data in `assets/music/cues/les-prisonnieres.music-cues.json`.
**Creative angle:** Epic trailer-grade score under a deliberately dumb-simple, kid-explainer script. The mismatch is the joke — don't write "epic" copy to match the music.
**Cut points (snapped to the 126 BPM beat grid):** 2.01s, 3.90s, 8.16s, 11.94s, 13.83s, 18.08s.

---

## Scene-by-Scene Composition

### Scene 1: Hook (0:00–0:02.01)
**Duration:** 2.01 seconds

**Layout:**
- Split-screen vertical layout
- **LEFT:** Stale LinkedIn post card (gray, faded, text: "Streamline your workflow...")
- **RIGHT:** NovaKit skill card (bright, dark theme, coral accent #DE7356, glowing research badge)

**Text:**
- Center overlay, bold sans-serif (white): "Your AI forgot what happened yesterday."
- Appear at 0:05, hold until 0:20 (cross-dissolve out)

**Animation:**
- LEFT side: Fade to 30% opacity over 1s, then drift down slightly
- RIGHT side: Zoom in 5% with a pulse glow on the research badge
- Hard cut transition at 0:02

**SFX Sync:**
- 0:00 — Music starts (cinematic swell)
- 2.01s — Bass hit lands exactly on the beat-grid cut

**Music Cues:** Hard cut at 2.01s aligned to real beat-grid value from `les-prisonnieres.music-cues.json`

---

### Scene 2: Reveal – Grid (0:02.01–0:03.90)
**Duration:** 1.89 seconds

**Layout:**
- Full-bleed skill cards grid (from NovaKit homepage)
- Show 12–20 skill cards visible, emoji icons prominent
- Cards slide/scale in rapidly

**Text:**
- Center top overlay: "Meet NovaKit: 63 Claude Skills"
- Appear at 0:24, hold until 0:40 (subtitle below)
- Subtitle: "...that research live trends first"

**Animation:**
- Fast pan/zoom through grid (like a scrolling reveal)
- Each visible card scales up ~10% as it enters frame, then settles
- Emoji icons rotate 360° over 0.5s (stagger by 50ms between cards)
- Hard cut-in at 2.01s, cut-out at 3.90s

**SFX Sync:**
- Card flip or whoosh sounds (one per visible card cluster, ~4 sounds total)
- Align first whoosh to beat-grid value 2.48s

**Music Cues:** Synth arpeggio entrance, beats at 2.48, 2.96, 3.44 within this scene

---

### Scene 3: The Magic – Research First (0:03.90–0:08.16)
**Duration:** 4.26 seconds

**Layout:**
- Skill detail page (e.g., "Cold Outreach Email") in 9:16 vertical frame
- Top: Skill name, emoji, description
- Middle: Research badge (green, glowing, text: "Live research on every run")
- Bottom: Split output preview (LEFT = grayed/stale, RIGHT = bright/fresh)

**Text:**
- Overlay: "Every skill researches live trends."
- Appear at 0:42, hold 0.5s
- Then: "*Then* it writes." (appear at 1:00, hold 0.5s)

**Animation:**
- 0:04–0:06: Research badge pulses (brightness +20% every 0.5s)
- 0:06–0:08: Split transition — LEFT side desaturates and fades, RIGHT side brightens and scales up 5%
- Smooth fade/zoom transitions between sub-scenes

**SFX Sync:**
- 3.90s — Soft data/ping sound (research start)
- ~7.21s — "Unlock" or satisfying ding (output reveal, on beat-grid value)

**Music Cues:** Full epic-electronic momentum through this scene — driving percussion/layered synths, hard cut out at 8.16s (beat-grid match)

---

### Scene 4: Bundle Play (0:08.16–0:11.94)
**Duration:** 3.78 seconds

**Layout:**
- Founder Bundle card dominates frame ($39 price, 6 skills)
- Cards for the 6 component skills cascade/stack below it
- Price comparison sidebar: "$54 individually → $39 bundle"

**Text:**
- Overlay: "Or grab a bundle. 6 skills, one price."
- Appear at 1:00, hold through 1:36

**Animation:**
- 0:08–0:09: Founder Bundle card enters from top (slide down + fade in)
- 0:09–0:11: 6 component skill cards stack vertically below it (stagger by 0.15s each, slight rotate)
- 0:11–0:12: Price comparison badge fades in, "$54" → "$39" with a strikethrough animation
- Playful bounce easing on stacking

**SFX Sync:**
- Each card stack: coin/chip drop sound (light, satisfying)
- 6 sounds total, staggered across the scene's beat grid (8.65, 9.03, 9.57, 10.04, 10.52, 10.99)

**Music Cues:** Stays at full intensity, hard cut out at 11.94s (beat-grid match)

---

### Scene 5: Pricing Tier (0:11.94–0:13.83)
**Duration:** 1.89 seconds

**Layout:**
- Fast montage: 4–5 price tiers flash across screen
- $5 tag → $15–$19 tag → $29–$45 tag → $69 tag
- Bold, large typography (48px+ font)

**Text:**
- Overlay: "From $5 to $69. Pick your power level."
- Appear at 1:36, hold through 2:00

**Animation:**
- Hard cuts between each price tier (no transitions, just cuts)
- Each price tag scales up 20% on entry, then settles
- Brief 0.3s hold per tier

**SFX Sync:**
- Retro game "level up" chimes (one per price tier)
- 4 chimes, each on a beat-grid value within 11.94–13.83s (11.94, 12.41, 12.88, 13.35)

**Music Cues:** Still driving, begins to taper toward outro, hard cut out at 13.83s (beat-grid match)

---

### Scene 6: Punchline & CTA (0:13.83–0:18.08)
**Duration:** 4.25 seconds

**Layout:**
- NovaKit homepage hero section (condensed)
- Checkout button prominent (coral #DE7356 background, white text)
- Success state (delivery page preview with download links + green checkmark)

**Text:**
- Line 1 (13.83–15.71s): "Never write stale again."
- Line 2 (15.71–18.08s): "novakit.tech" (large, centered, white)

**Animation:**
- 13.83–14.77s: Checkout button pulses/glows (emphasis)
- 14.77–15.71s: User avatar appears in top-right corner with a glow halo
- 15.71–18.08s: Quick cut to success/delivery page (green checkmark bounces in, files visible)
- Fade out to black at 18.08s with "novakit.tech" text persisting briefly longer

**SFX Sync:**
- 13.83s — Click/button press sound (beat-grid match)
- ~16.18s — Success/ding sound (uplifting, near beat-grid value)
- 18.08s — Final beat resolve / cut (music stays mid-energy — we cut out before the track's own outro since we only use the first ~18s of a 249s track)

**Music Cues:** Final hard cut at 18.08s (beat-grid match); no fade-down needed since the source track hasn't reached its own resolution yet

---

## Video Composition Rules

1. **Viewport:** 390 × 844 px (9:16, no letterboxing)
2. **Typography:** Use sans-serif (Geist preferred), white text on dark backgrounds for contrast
3. **Colors:**
   - Primary: #DE7356 (coral)
   - Secondary: #0d0d0b (dark bg), #1a1a17 (surface)
   - Accent: #34d399 (green, for "research" badge)
   - Text: #f0efe8 (light gray)
4. **Transitions:** Hard cuts, fades, zoom/pan (no bouncy ease effects; keep it professional-chaotic)
5. **Text Hold:** 
   - Short phrases: 0.8–1.2s
   - Full sentences: 1.2–1.8s
   - Never faster than 0.6s or text becomes unreadable
6. **Sound Effects:** Light, non-intrusive; punchy but not overwhelming
7. **Music:** "Les Prisonnières – Epic Electronic" (Bensound, 126 BPM). Volume 0.3–0.4, never above 0.5, SFX layered above it (0.55–0.85). `<audio>` track-index 10 for music, SFX ascending from 11.

---

## Assets Required

- NovaKit homepage screenshot (or vector): skill cards grid
- NovaKit skill detail page: "Cold Outreach Email" or similar
- Founder Bundle card image
- 6 component skill card images
- Pricing tier cards ($5, $15–$19, $29–$45, $69)
- Success/delivery page state (with download links, green checkmark)
- Generic stale LinkedIn post image (can be mock)
- Research badge graphic (green, glowing)

---

## Delivery Expectations

- Output: MP4 video (h.264, 1080 kbps target bitrate, 30fps)
- Aspect ratio: 9:16 (390 × 844 px)
- File path: `brag-output-2026-06-23-122344/brag.mp4`
- Sidecar: Share copy text file

---

## Notes

- This is a high-energy, "sleep cut" style brag video targeting TikTok/YouTube Shorts audiences.
- Explain to a 5-year-old level: "Your robot forgot the news, NovaKit reads it first."
- Every cut should feel snappy but readable. No flashing text.
- The video should feel premium (dark theme, coral pop) but fun (fast pacing, emojis, game-like sounds).
- Music is epic/cinematic on purpose against the kid-simple script — the contrast is the joke. Don't rewrite the copy to sound "epic."
- Bensound attribution ("Music: bensound.com") must appear in share-copy.txt / video description — free-tier license requirement.
