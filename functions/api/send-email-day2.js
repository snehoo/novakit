// functions/api/send-email-day2.js
// Called by the cron worker (email-sequence-cron.js) for Day 2 emails.
// POST /api/send-email-day2
// Body: { to, skillName, skillSlug, orderId, orderUuid }
//
// CHANGES vs previous version:
//   - Accepts `orderUuid` in body
//   - Generates feedback token via HMAC(FEEDBACK_SECRET, orderUuid)
//   - Adds a soft feedback CTA block between the cross-sell and support note

const CORS = {
  'Access-Control-Allow-Origin':               `*`,
  'Access-Control-Allow-Methods':              `POST, OPTIONS`,
  'Access-Control-Allow-Headers':              `Content-Type`,
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

// ── Feedback token ───────────────────────────────────────────────────────────
async function makeFeedbackToken(secret, orderUuid) {
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(orderUuid));
  return Array.from(new Uint8Array(sig))
    .slice(0, 16)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

// ── One tip per skill ────────────────────────────────────────────────────────
const SKILL_TIPS = {
  'pitch-deck-narrative':                      `Paste your actual one-line company description and target investor type in the context block before running — the output shifts from generic to fundable.`,
  'cold-outreach-email':                       `Add 2–3 sentences about what makes your offer genuinely different before you run it. Generic input = generic email. Specific input = reply-worthy email.`,
  'sales-page':                                `Drop in a real customer objection you hear often — the skill will weave in the counter-argument naturally instead of leaving it unaddressed.`,
  'brand-ad-copy':                             `Run it once for awareness copy and once for conversion copy with the same brief — the output shifts significantly and gives you two angles to test.`,
  'resume-cv-builder':                         `Include the actual job description text in your context, not just the job title. The skill tailors language to the specific role, not the generic category.`,
  'linkedin-post-engine':                      `Specify your goal (grow followers / drive DMs / build authority) explicitly — without it the skill defaults to generic thought leadership.`,
  'seo-blog-post-brief':                       `Paste the top 3 URLs already ranking for your keyword. The skill uses them to identify the gaps your post should fill.`,
  'email-newsletter-engine':                   `Tell it your subscriber's #1 pain point upfront. The best newsletters are painkillers, not showcases.`,
  'social-content-engine':                     `Give it a content theme for the week, not just a topic. "AI tools for solopreneurs" beats "AI" every time.`,
  'twitter-x-thread-engine':                   `Specify the hook style you want — contrarian, story, or data-led. The opening line is 80% of the thread's performance.`,
  'content-calendar':                          `Include your publishing frequency and the platforms you're active on — the calendar adapts cadence and format to what's actually sustainable for you.`,
  'pr-press-release':                          `Add the journalist angle explicitly — what's the story for someone who has never heard of you? That's the lede.`,
  'brand-voice-guide':                         `Feed it 3 examples of copy you love and 3 you hate. The contrast is what sharpens the voice definition.`,
  'prd-writer':                                `Include your user persona and their biggest frustration with existing tools. The PRD becomes a product argument, not just a spec.`,
  'architecture-diagram-prompt':               `Specify your stack explicitly — cloud provider, services, scale expectations. Vague input produces vague diagrams.`,
  'grant-and-proposal-writing':                `Include the funder's stated priorities verbatim. Mirror their language back — reviewers score what matches their criteria.`,
  'course-curriculum-builder':                 `Define your student's starting point and their desired outcome in one sentence each. The curriculum arc becomes obvious from there.`,
  'university-sop':                            `Name the specific research group or professor you want to work with and why. Generic SOPs don't get reads — specific ones do.`,
  'video-script-engine':                       `Specify the retention hook style upfront — open loop, bold claim, or curiosity gap. The first 8 seconds determine if it gets watched.`,
  'ai-animation-film-prompt':                  `Lock your character description first and keep it identical across every scene prompt. Character drift is the #1 reason AI animation looks incoherent.`,
  'product-ad-film-prompt':                    `Add your one conversion goal (click / sign-up / purchase) explicitly. The script structure changes based on what action you're driving.`,
  'dialogue-character-film-prompt':            `Define each character's speech pattern before running — formal vs casual, verbose vs clipped. Consistent voice is what makes dialogue feel written, not generated.`,
  'nda-contract-draft':                        `Specify the jurisdiction and whether it's mutual or one-way before running. These two variables change the clause structure significantly.`,
  'tos-privacy-policy':                        `List every third-party tool you use that touches user data (Stripe, analytics, email). The privacy policy must name them — leaving them out creates legal exposure.`,
  'financial-model-prompt':                    `Define your key growth assumption first — the model is only as good as the number you're most uncertain about.`,
  'visa-cover-letter':                         `Include the exact visa category code and subclass. Immigration officers are pattern-matching against criteria — match the language precisely.`,
  'cover-letter-writer':                       `Tell it the one thing you most want the hiring manager to remember after reading it. Lead with that.`,
  'investor-update-email':                     `Be specific about what you're stuck on — investors who can help, will. Vague updates get filed and forgotten.`,
  'job-description-writer':                    `Include what's hard about the role honestly. The best candidates self-select in because of honesty, not despite it.`,
  'performance-review-writer':                 `Include the employee's own goals from their last review. It shows you were listening.`,
  'business-plan':                             `Define your unfair advantage in one sentence before running. If you can't, the plan will expose that gap clearly.`,
  'real-estate-listing-copy':                  `Add the neighbourhood lifestyle details beyond the property itself — what's walkable, what's changing, what's the vibe. Buyers buy the life, not just the building.`,
  'real-estate-photo-prompt':                  `Specify time of day and light direction for each room. Flat light is why most real estate photos look the same.`,
  'hotel-airbnb-listing-copy':                 `List what guests always comment on in your reviews. The skill leads with proof, not promises.`,
  'ecommerce-product-listing':                 `Include the customer complaint you see most about competitor products. The listing addresses it head-on and converts better.`,
  'product-photography-prompt':                `Specify the platform the images are for — Amazon, Instagram, and website hero images need completely different framing and negative space.`,
  'logo-brand-identity':                       `Include 3 brands whose aesthetic you admire and 1 whose you actively dislike. The contrast is more useful than references alone.`,
  'podcast-episode-script':                    `Specify whether this is a solo or interview episode. The pacing, structure, and listener experience are different problems.`,
  'webinar-online-event-script':               `Define the one thing attendees should do immediately after — the script is built backwards from that action.`,
  'podcast-show-notes':                        `Include the episode's single most quotable moment. Show notes that surface a strong quote get shared more.`,
  'short-form-ai-video':                       `Define the scroll-stop hook in one sentence before running. Everything else in the video earns its place by delivering on that promise.`,
  'youtube-thumbnail-prompt':                  `Specify the emotion you want viewers to feel in the first glance — curiosity, urgency, or FOMO. The visual is built to trigger that state.`,
  'screenplay-script':                         `Define your protagonist's want (external goal) and need (internal arc) as two separate things. The tension between them is the story.`,
  'short-story-prompt':                        `Give it the ending you want to land emotionally, then let it build backwards. Stories that know where they're going feel purposeful.`,
  'book-cover-prompt':                         `Include 5 comparable titles in your genre. The prompt uses them to calibrate genre signals — what makes covers look like they belong on the shelf.`,
  'poetry-verse-prompt':                       `Specify the form constraint if you have one (sonnet, free verse, syllable count). Constraint produces better poetry, not worse.`,
  'childrens-book-prompt':                     `Define the age range precisely — writing for 3-year-olds vs 7-year-olds is a completely different vocabulary and concept complexity.`,
  'festival-holiday-greeting-prompt':          `Add your brand's specific tone constraint — warm but not saccharine, celebratory but not generic. Generic greetings get scrolled past.`,
  'social-media-carousel-prompt':              `Define the single takeaway of slide 1 — if it doesn't earn a swipe, the rest doesn't matter.`,
  'health-wellness-plan':                      `Be specific about constraints — schedule, equipment, injuries. Tailored plans get followed. Generic ones get abandoned.`,
  'travel-itinerary-planner':                  `Include travel pace preference (packed vs slow) and one non-negotiable experience. The itinerary builds around what actually matters to you.`,
  'recipe-development-prompt':                 `Specify dietary constraints and skill level explicitly. A Michelin-star technique for a weeknight cook is a recipe for abandonment.`,
  'home-renovation-brief':                     `Include your must-haves vs nice-to-haves as two separate lists. Contractors quote against must-haves — don't let them blur the line.`,
  'lesson-plan-builder':                       `Include prior knowledge assumptions for your students. The plan scaffolds from where they actually are, not where the curriculum assumes.`,
  'exam-paper-generator':                      `Specify the cognitive levels you want to test — recall, application, analysis. Good papers mix all three, not just recall.`,
  'research-paper-outline':                    `State your central argument in one sentence before running. If you can't, the outline will make that clear — which is the most useful thing it can do.`,
  'conference-abstract':                       `Name the conference and its audience explicitly. A methods-focused abstract for a practitioner conference will be rejected regardless of quality.`,
  'menu-description-copy':                     `Include the story behind 1–2 signature dishes. Provenance sells at any price point.`,
  'wedding-vows-writer':                       `Write down 3 specific memories — not qualities, memories. Vows built on real moments land differently than ones built on adjectives.`,
  'wedding-invitation-prompt':                 `Define the visual mood in 3 words before running. Specific aesthetic direction produces a specific prompt, not a generic one.`,
  'event-speech-writer':                       `Include one genuine story about the person being celebrated. Speeches without a real story feel like press releases.`,
  'eulogy-writer':                             `Write down the one thing you most want people to remember about them. The eulogy is built to leave that with the room.`,
  'ugc-ad-creator':                            `Specify the scroll-stop problem your product solves in plain English. The UGC hook is built around that moment of recognition.`,
};

// ── Cross-sell pairings (skill slug → related skill) ────────────────────────
const CROSS_SELL = {
  'pitch-deck-narrative':           { name: 'Investor Update Email',          slug: 'investor-update-email',          price: '$9'  },
  'cold-outreach-email':            { name: 'LinkedIn Post Engine',           slug: 'linkedin-post-engine',           price: '$9'  },
  'sales-page':                     { name: 'Cold Outreach Email',            slug: 'cold-outreach-email',            price: '$9'  },
  'brand-ad-copy':                  { name: 'UGC Ad Creator',                 slug: 'ugc-ad-creator',                 price: '$19' },
  'resume-cv-builder':              { name: 'Cover Letter Writer',            slug: 'cover-letter-writer',            price: '$9'  },
  'linkedin-post-engine':           { name: 'Twitter/X Thread Engine',        slug: 'twitter-x-thread-engine',        price: '$9'  },
  'seo-blog-post-brief':            { name: 'Content Calendar',               slug: 'content-calendar',               price: '$9'  },
  'email-newsletter-engine':        { name: 'Social Content Engine',          slug: 'social-content-engine',          price: '$9'  },
  'social-content-engine':          { name: 'Email Newsletter Engine',        slug: 'email-newsletter-engine',        price: '$9'  },
  'twitter-x-thread-engine':        { name: 'LinkedIn Post Engine',           slug: 'linkedin-post-engine',           price: '$9'  },
  'content-calendar':               { name: 'Social Content Engine',          slug: 'social-content-engine',          price: '$9'  },
  'pr-press-release':               { name: 'Brand & Ad Copy',                slug: 'brand-ad-copy',                  price: '$19' },
  'brand-voice-guide':              { name: 'Brand & Ad Copy',                slug: 'brand-ad-copy',                  price: '$19' },
  'prd-writer':                     { name: 'Architecture Diagram',           slug: 'architecture-diagram-prompt',    price: '$15' },
  'architecture-diagram-prompt':    { name: 'PRD Writer',                     slug: 'prd-writer',                     price: '$15' },
  'grant-and-proposal-writing':     { name: 'Research Paper Outline',         slug: 'research-paper-outline',         price: '$9'  },
  'course-curriculum-builder':      { name: 'Lesson Plan Builder',            slug: 'lesson-plan-builder',            price: '$9'  },
  'university-sop':                 { name: 'Research Paper Outline',         slug: 'research-paper-outline',         price: '$9'  },
  'video-script-engine':            { name: 'Podcast Episode Script',         slug: 'podcast-episode-script',         price: '$9'  },
  'ai-animation-film-prompt':       { name: 'Product Ad Film Prompt',         slug: 'product-ad-film-prompt',         price: '$15' },
  'product-ad-film-prompt':         { name: 'AI Animation Film Prompt',       slug: 'ai-animation-film-prompt',       price: '$15' },
  'dialogue-character-film-prompt': { name: 'Screenplay / Script',            slug: 'screenplay-script',              price: '$9'  },
  'nda-contract-draft':             { name: 'Terms of Service & Privacy Policy', slug: 'terms-of-service-privacy-policy', price: '$15' },
  'tos-privacy-policy':             { name: 'NDA / Contract Draft',           slug: 'nda-contract-draft',             price: '$15' },
  'financial-model-prompt':         { name: 'Pitch Deck Narrative',           slug: 'pitch-deck-narrative',           price: '$19' },
  'visa-cover-letter':              { name: 'University Application SOP',     slug: 'university-application-sop',     price: '$15' },
  'cover-letter-writer':            { name: 'Resume & CV Builder',            slug: 'resume-cv-builder',              price: '$9'  },
  'investor-update-email':          { name: 'Pitch Deck Narrative',           slug: 'pitch-deck-narrative',           price: '$19' },
  'job-description-writer':         { name: 'Performance Review Writer',      slug: 'performance-review-writer',      price: '$9'  },
  'performance-review-writer':      { name: 'Job Description Writer',         slug: 'job-description-writer',         price: '$9'  },
  'business-plan':                  { name: 'Financial Model Prompt',         slug: 'financial-model-prompt',         price: '$15' },
  'real-estate-listing-copy':       { name: 'Real Estate Photo Prompt',       slug: 'real-estate-photo-prompt',       price: '$9'  },
  'real-estate-photo-prompt':       { name: 'Real Estate Listing Copy',       slug: 'real-estate-listing-copy',       price: '$9'  },
  'hotel-airbnb-listing-copy':      { name: 'Product Photography Prompt',     slug: 'product-photography-prompt',     price: '$9'  },
  'ecommerce-product-listing':      { name: 'Product Photography Prompt',     slug: 'product-photography-prompt',     price: '$9'  },
  'product-photography-prompt':     { name: 'E-Commerce Product Listing',     slug: 'ecommerce-product-listing',      price: '$9'  },
  'logo-brand-identity':            { name: 'Brand Voice Guide',              slug: 'brand-voice-guide',              price: '$15' },
  'podcast-episode-script':         { name: 'Podcast Show Notes',             slug: 'podcast-show-notes',             price: '$9'  },
  'webinar-online-event-script':    { name: 'Video Script Engine',            slug: 'video-script-engine',            price: '$15' },
  'podcast-show-notes':             { name: 'Podcast Episode Script',         slug: 'podcast-episode-script',         price: '$9'  },
  'short-form-ai-video':            { name: 'UGC Ad Creator',                 slug: 'ugc-ad-creator',                 price: '$19' },
  'youtube-thumbnail-prompt':       { name: 'Short-Form AI Video',            slug: 'short-form-ai-video',            price: '$19' },
  'screenplay-script':              { name: 'Short Story Prompt',             slug: 'short-story-prompt',             price: '$9'  },
  'short-story-prompt':             { name: 'Screenplay / Script',            slug: 'screenplay-script',              price: '$9'  },
  'book-cover-prompt':              { name: "Children's Book Prompt",         slug: 'childrens-book-prompt',          price: '$9'  },
  'poetry-verse-prompt':            { name: 'Short Story Prompt',             slug: 'short-story-prompt',             price: '$9'  },
  'childrens-book-prompt':          { name: 'Book Cover Prompt',              slug: 'book-cover-prompt',              price: '$9'  },
  'festival-holiday-greeting-prompt': { name: 'Social Media Carousel',       slug: 'social-media-carousel-prompt',   price: '$9'  },
  'social-media-carousel-prompt':   { name: 'Social Content Engine',          slug: 'social-content-engine',          price: '$9'  },
  'health-wellness-plan':           { name: 'Meal / Recipe Development',      slug: 'recipe-development-prompt',      price: '$9'  },
  'travel-itinerary-planner':       { name: 'Hotel/Airbnb Listing Copy',      slug: 'hotel-airbnb-listing-copy',      price: '$9'  },
  'recipe-development-prompt':      { name: 'Menu Description Copy',          slug: 'menu-description-copy',          price: '$9'  },
  'home-renovation-brief':          { name: 'Real Estate Listing Copy',       slug: 'real-estate-listing-copy',       price: '$9'  },
  'lesson-plan-builder':            { name: 'Exam Paper Generator',           slug: 'exam-paper-generator',           price: '$9'  },
  'exam-paper-generator':           { name: 'Lesson Plan Builder',            slug: 'lesson-plan-builder',            price: '$9'  },
  'research-paper-outline':         { name: 'Conference Abstract',            slug: 'conference-abstract',            price: '$9'  },
  'conference-abstract':            { name: 'Research Paper Outline',         slug: 'research-paper-outline',         price: '$9'  },
  'menu-description-copy':          { name: 'Recipe Development',             slug: 'recipe-development-prompt',      price: '$9'  },
  'wedding-vows-writer':            { name: 'Event Speech Writer',            slug: 'event-speech-writer',            price: '$9'  },
  'wedding-invitation-prompt':      { name: 'Wedding Vows Writer',            slug: 'wedding-vows-writer',            price: '$9'  },
  'event-speech-writer':            { name: 'Wedding Vows Writer',            slug: 'wedding-vows-writer',            price: '$9'  },
  'eulogy-writer':                  { name: 'Event Speech Writer',            slug: 'event-speech-writer',            price: '$9'  },
  'ugc-ad-creator':                 { name: 'Social Content Engine',          slug: 'social-content-engine',          price: '$9'  },
};

// ── Bundle upsell per skill slug ─────────────────────────────────────────────
const BUNDLE_UPSELL = {
  'pitch-deck-narrative':             { name: 'Founder Bundle',    slug: 'founder',    price: '$39', count: 6 },
  'cold-outreach-email':              { name: 'Founder Bundle',    slug: 'founder',    price: '$39', count: 6 },
  'sales-page':                       { name: 'Founder Bundle',    slug: 'founder',    price: '$39', count: 6 },
  'brand-ad-copy':                    { name: 'Marketing Bundle',  slug: 'marketing',  price: '$45', count: 5 },
  'ugc-ad-creator':                   { name: 'Marketing Bundle',  slug: 'marketing',  price: '$45', count: 5 },
  'resume-cv-builder':                { name: 'Student Bundle',    slug: 'student',    price: '$29', count: 5 },
  'cover-letter-writer':              { name: 'Student Bundle',    slug: 'student',    price: '$29', count: 5 },
  'university-sop':                   { name: 'Student Bundle',    slug: 'student',    price: '$29', count: 5 },
  'research-paper-outline':           { name: 'Student Bundle',    slug: 'student',    price: '$29', count: 5 },
  'conference-abstract':              { name: 'Student Bundle',    slug: 'student',    price: '$29', count: 5 },
  'linkedin-post-engine':             { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'seo-blog-post-brief':              { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'email-newsletter-engine':          { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'social-content-engine':            { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'twitter-x-thread-engine':          { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'brand-voice-guide':                { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'content-calendar':                 { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'financial-model-prompt':           { name: 'Legal/Biz Bundle',  slug: 'legal-biz',  price: '$45', count: 5 },
  'visa-cover-letter':                { name: 'Legal/Biz Bundle',  slug: 'legal-biz',  price: '$45', count: 5 },
  'grant-and-proposal-writing':       { name: 'Legal/Biz Bundle',  slug: 'legal-biz',  price: '$45', count: 5 },
  'video-script-engine':              { name: 'Video/Pod Bundle',  slug: 'video-pod',  price: '$69', count: 9 },
  'podcast-episode-script':           { name: 'Video/Pod Bundle',  slug: 'video-pod',  price: '$69', count: 9 },
  'short-form-ai-video':              { name: 'Video/Pod Bundle',  slug: 'video-pod',  price: '$69', count: 9 },
  'podcast-show-notes':               { name: 'Video/Pod Bundle',  slug: 'video-pod',  price: '$69', count: 9 },
  'webinar-online-event-script':      { name: 'Video/Pod Bundle',  slug: 'video-pod',  price: '$69', count: 9 },
  'ai-animation-film-prompt':         { name: 'Video/Pod Bundle',  slug: 'video-pod',  price: '$69', count: 9 },
  'product-ad-film-prompt':           { name: 'Video/Pod Bundle',  slug: 'video-pod',  price: '$69', count: 9 },
  'dialogue-character-film-prompt':   { name: 'Video/Pod Bundle',  slug: 'video-pod',  price: '$69', count: 9 },
  'youtube-thumbnail-prompt':         { name: 'Video/Pod Bundle',  slug: 'video-pod',  price: '$69', count: 9 },
  'real-estate-listing-copy':         { name: 'Realtor Bundle',    slug: 'realtor',    price: '$29', count: 5 },
  'real-estate-photo-prompt':         { name: 'Realtor Bundle',    slug: 'realtor',    price: '$29', count: 5 },
  'hotel-airbnb-listing-copy':        { name: 'Realtor Bundle',    slug: 'realtor',    price: '$29', count: 5 },
  'product-photography-prompt':       { name: 'Realtor Bundle',    slug: 'realtor',    price: '$29', count: 5 },
  'lesson-plan-builder':              { name: 'Educator Bundle',   slug: 'educator',   price: '$29', count: 4 },
  'exam-paper-generator':             { name: 'Educator Bundle',   slug: 'educator',   price: '$29', count: 4 },
  'course-curriculum-builder':        { name: 'Educator Bundle',   slug: 'educator',   price: '$29', count: 4 },
  'wedding-vows-writer':              { name: 'Wedding Bundle',    slug: 'wedding',    price: '$15', count: 4 },
  'wedding-invitation-prompt':        { name: 'Wedding Bundle',    slug: 'wedding',    price: '$15', count: 4 },
  'event-speech-writer':              { name: 'Wedding Bundle',    slug: 'wedding',    price: '$15', count: 4 },
  'menu-description-copy':            { name: 'Wedding Bundle',    slug: 'wedding',    price: '$15', count: 4 },
  'short-story-prompt':               { name: 'Creative Bundle',   slug: 'creative',   price: '$19', count: 6 },
  'screenplay-script':                { name: 'Creative Bundle',   slug: 'creative',   price: '$19', count: 6 },
  'book-cover-prompt':                { name: 'Creative Bundle',   slug: 'creative',   price: '$19', count: 6 },
  'poetry-verse-prompt':              { name: 'Creative Bundle',   slug: 'creative',   price: '$19', count: 6 },
  'childrens-book-prompt':            { name: 'Creative Bundle',   slug: 'creative',   price: '$19', count: 6 },
  'festival-holiday-greeting-prompt': { name: 'Creative Bundle',   slug: 'creative',   price: '$19', count: 6 },
  'pr-press-release':                 { name: 'Marketing Bundle',  slug: 'marketing',  price: '$45', count: 5 },
  'ecommerce-product-listing':        { name: 'Marketing Bundle',  slug: 'marketing',  price: '$45', count: 5 },
  'investor-update-email':            { name: 'Founder Bundle',    slug: 'founder',    price: '$39', count: 6 },
  'job-description-writer':           { name: 'Founder Bundle',    slug: 'founder',    price: '$39', count: 6 },
  'business-plan':                    { name: 'Founder Bundle',    slug: 'founder',    price: '$39', count: 6 },
  'prd-writer':                       { name: 'Founder Bundle',    slug: 'founder',    price: '$39', count: 6 },
  'architecture-diagram-prompt':      { name: 'Founder Bundle',    slug: 'founder',    price: '$39', count: 6 },
  'logo-brand-identity':              { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'social-media-carousel-prompt':     { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'performance-review-writer':        { name: 'Founder Bundle',    slug: 'founder',    price: '$39', count: 6 },
  'health-wellness-plan':             { name: 'Creator Bundle',    slug: 'creator',    price: '$45', count: 7 },
  'travel-itinerary-planner':         { name: 'Realtor Bundle',    slug: 'realtor',    price: '$29', count: 5 },
  'recipe-development-prompt':        { name: 'Wedding Bundle',    slug: 'wedding',    price: '$15', count: 4 },
  'home-renovation-brief':            { name: 'Realtor Bundle',    slug: 'realtor',    price: '$29', count: 5 },
  'eulogy-writer':                    { name: 'Creative Bundle',   slug: 'creative',   price: '$19', count: 6 },
};

function buildDay2Html({ skillName, skillSlug, tip, crossSell, orderId, feedbackUrl }) {
  const crossSellHtml = crossSell ? `
    <tr><td style="padding-top:28px;">
      <p style="margin:0 0 12px;font-size:14px;color:#545249;line-height:1.6;">
        If you do a lot of this kind of work, <a href="https://novakit.tech/skills/${crossSell.slug}.html" style="color:#DE7356;font-weight:600;">${crossSell.name}</a> (${crossSell.price}) pairs well with this one — worth knowing it exists.
      </p>
    </td></tr>` : '';

  const feedbackHtml = feedbackUrl ? `
            <!-- Feedback CTA -->
            <div style="background:#fff7f3;border:1px solid #f3d8cb;border-radius:10px;padding:18px 22px;margin:28px 0 0;">
              <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#DE7356;text-transform:uppercase;letter-spacing:0.08em;">How is it going?</p>
              <p style="margin:0 0 14px;font-size:14px;color:#545249;line-height:1.6;">You have had it 48 hours — early reactions help us improve. One star rating, takes 30 seconds.</p>
              <a href="${feedbackUrl}" style="display:inline-block;padding:11px 20px;background:#DE7356;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px;">Rate it →</a>
            </div>` : '';

  return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f7f6f2;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f6f2;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background:#0d0d0b;padding:24px 40px;text-align:left;">
          <img src="https://novakit.tech/assets/nkwhite.jpg" alt="NovaKit" height="28" style="display:block;border:0;outline:none;text-decoration:none;">
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:40px;">
          <p style="margin:0 0 8px;font-size:12px;color:#8a8980;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">One thing most people miss</p>
          <h1 style="margin:0 0 20px;font-size:26px;font-weight:800;color:#111110;letter-spacing:-0.02em;">${skillName}</h1>

          <table cellpadding="0" cellspacing="0" width="100%">
            <tr><td>
              <p style="margin:0 0 20px;font-size:15px;color:#545249;line-height:1.6;">
                Most people install the skill and use it as-is. That works. But here's what makes the output noticeably better:
              </p>

              <!-- Tip block -->
              <div style="background:#f7f6f2;border-left:3px solid #DE7356;border-radius:0 8px 8px 0;padding:16px 20px;margin:0 0 24px;">
                <p style="margin:0;font-size:14px;color:#111110;line-height:1.7;">${tip}</p>
              </div>

              <p style="margin:0 0 20px;font-size:15px;color:#545249;line-height:1.6;">
                Try it on your next prompt — the difference is immediate.
              </p>
            </td></tr>

            ${crossSellHtml}

          </table>

          ${feedbackHtml}

          <!-- Support note -->
          <p style="margin:28px 0 0;font-size:13px;color:#8a8980;line-height:1.7;">
            Questions? Reply to this email or write to <a href="mailto:support@novakit.tech" style="color:#DE7356;">support@novakit.tech</a>.<br>
            Order ID: <span style="font-family:monospace;font-size:12px;">${orderId}</span>
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f7f6f2;padding:20px 40px;text-align:center;border-top:1px solid #eeecea;">
          <p style="margin:0;font-size:12px;color:#8a8980;">
            © 2026 NovaKit &nbsp;·&nbsp; <a href="https://novakit.tech/legal/refund.html" style="color:#8a8980;">Refund Policy</a> &nbsp;·&nbsp; <a href="https://novakit.tech/legal/privacy.html" style="color:#8a8980;">Privacy</a> &nbsp;·&nbsp; <a href="https://novakit.tech/legal/terms.html" style="color:#8a8980;">Terms</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;
}

export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch {
    return new Response('Bad JSON', { status: 400, headers: CORS });
  }

  const { to, skillName, skillSlug, orderId, orderUuid } = body;
  if (!to || !skillName || !skillSlug) {
    return new Response('Missing required fields', { status: 400, headers: CORS });
  }

  // Build feedback URL — gracefully skipped if env var not set yet
  let feedbackUrl = null;
  if (orderUuid && env.FEEDBACK_SECRET) {
    const tok = await makeFeedbackToken(env.FEEDBACK_SECRET, orderUuid);
    feedbackUrl = `https://novakit.tech/feedback.html?o=${orderUuid}&t=${tok}&s=day2`;
  }

  const tip       = SKILL_TIPS[skillSlug]  || 'Give the skill specific, detailed context before running — the output quality scales directly with input quality.';
  const crossSell = CROSS_SELL[skillSlug]  || null;

  const emailHtml = buildDay2Html({ skillName, skillSlug, tip, crossSell, orderId, feedbackUrl });

  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.RESEND_API_KEY}`,
        'Content-Type':  `application/json`,
      },
      body: JSON.stringify({
        from: 'NovaKit <support@novakit.tech>',
        to:   [to],
        subject: `One thing most people miss with ${skillName}`,
        html: emailHtml,
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error('[send-email-day2] Resend error:', err);
      return new Response(JSON.stringify({ error: 'Email send failed', detail: err }), {
        status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
      });
    }

    const data = await res.json();
    return new Response(JSON.stringify({ ok: true, emailId: data.id }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
    });

  } catch (err) {
    console.error('[send-email-day2]', err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }
}
