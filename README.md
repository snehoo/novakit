# NovaKit — novakit.tech

Claude Skills marketplace. Living skills that do live trend research before every output.

## Stack
- Pure HTML/CSS/JS — no framework, no build step
- Google Fonts (Instrument Serif, Geist, Geist Mono)
- All assets base64 inline — no external image dependencies

## Pages
- `index.html` — homepage/catalogue
- `skills/pitch-deck-narrative.html` — first skill detail page (template for all others)

## Design system
- Accent: #DE7356
- Dark bg: #0d0d0b, surface: #1a1a17
- Light bg: #f7f6f2, surface: #ffffff
- Fonts: Instrument Serif (headings/italic), Geist (body), Geist Mono (code/mono)
- Both pages support dark/light mode via data-theme="dark"|"light" on <html>

## Skill detail page template
`skills/pitch-deck-narrative.html` is the template for all future skill pages.
Sections: Hero → Before/After demo → What you get → Who it's for → 4 research checks → Proof → Buy
Nav links back to index.html#section anchors.

## Pricing
- Individual skills: $5 (Pitch Deck: $9)
- Starter bundle: $9 (LinkedIn + Cold Outreach + Social Engine)
- Category bundles: $19
- All Access: $79 (28 skills)
- 7-day money back guarantee on all purchases

## To add a new skill page
Copy `skills/pitch-deck-narrative.html`, update:
1. <title> and hero headline/sub
2. Before/After demo content (5 after-slides)
3. What you get cards (4 cards)
4. Who it's for list
5. 4 research checks
6. Proof pullquote
7. Buy section price + bundle name

