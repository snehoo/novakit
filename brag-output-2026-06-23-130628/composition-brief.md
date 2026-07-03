# Composition Brief — NovaKit "Never The Same Skill Twice"

- Format: 1080×1920 (9:16)
- Duration: 20.09s
- Music: "By My Side" (Joyful Party), Bensound, ~114.84 BPM — `composition/assets/music/by-my-side.mp3`
- Creative angle: power-user fatigue with stale/repetitive skill outputs, resolved by NovaKit's live-trend-research-per-run mechanic. Fast, hard cuts. No trend-chasing visual gimmicks in the edit — speed lives in the cutting, not the messaging.
- Cut points (beat-snapped): 0 → 2.19 → 4.30 → 7.98 → 11.66 → 15.91 → 20.09

## Scenes

### Scene 1 — Hook (0–2.19s)
Three near-identical output cards stack in rapid hard-cuts (beats 0.62 / 1.14 / 1.66). Headline: "You've run this skill 50 times."

### Scene 2 — Pain sharpened (2.19–4.30s)
The three cards collapse into one flattened, grayscale card — visual shorthand for sameness. Headline: "Same hook. Same structure. Same everything."

### Scene 3 — Reveal (4.30–7.98s)
NovaKit's actual "Live trend research" timeline step (green checkmark + sub-line, pulled from real site UI/copy) ticks in and pulses. Headline: "NovaKit skills research live — before every single run."

### Scene 4 — Highlight 1: Narrowing questions (7.98–11.66s)
Real site UI: "Tell me about your topic" / "1 of 3" selector, 4 options, each highlighting in turn on the beat. Headline: "3 questions. Zero generic output."

### Scene 5 — Highlight 2: Quality gate (11.66–15.91s)
A weak draft line strikes through and fades; a sharper rewritten line fades in to replace it. Headline: "A quality gate rewrites the weak draft before you ever see it."

### Scene 6 — Punchline + CTA (15.91–20.09s)
Split card: "Today" output vs. "6 months later" output, visibly different. Beat-locked to the strong cue at 17.98s. Cuts to NovaKit wordmark + CTA, beat-locked to the strong cue at 20.09s (close). Lines: "Same skill. Six months later. Different result." → "NovaKit. Skills from $5. novakit.tech"

## Rules Applied

1. Standalone root, no `<template>` wrapper. `data-composition-id="main"`, `data-width="1080"`, `data-height="1920"`, `data-duration="20.09"`, `data-start="0"`.
2. One GSAP timeline, built synchronously, registered at `window.__timelines["main"]`.
3. `<audio>` is a direct child of root, `data-track-index="10"`, volume 0.35 (music stays under dialogue/text emphasis, never above 0.5).
4. No `Math.random`/`Date.now`, no `repeat:-1`. Pulse effects use finite `repeat` + `yoyo`.
5. No animating `display`/`visibility` — opacity/transform/background-color/border-color only.
6. No `<br>` in copy — text wraps via `max-width`.
7. All transformed elements are block-level and explicitly sized.
8. Absolutely-positioned pulsing badges sized for their peak (scaled) frame, not resting frame.

## Notes

- Bensound attribution required in share copy: "Music: bensound.com".
- All UI mockups (trend-research badge, 3-question selector, quality-gate rewrite) are paraphrased from actual site copy/structure in [index.html](../index.html) — not invented screens.
