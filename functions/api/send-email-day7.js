// functions/api/send-email-day7.js
// Called by email-sequence-cron.js for Day 7 emails.
// POST /api/send-email-day7
// Body: { to, skillName, skillSlug, bundleKey, orderId }

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

// ── Bundle upsell per skill slug ─────────────────────────────────────────────
const BUNDLE_UPSELL = {
  'pitch-deck-narrative':             { name: 'Founder Bundle',   slug: 'founder',   price: '$39', count: 6,  saving: '39%' },
  'cold-outreach-email':              { name: 'Founder Bundle',   slug: 'founder',   price: '$39', count: 6,  saving: '39%' },
  'sales-page':                       { name: 'Founder Bundle',   slug: 'founder',   price: '$39', count: 6,  saving: '39%' },
  'investor-update-email':            { name: 'Founder Bundle',   slug: 'founder',   price: '$39', count: 6,  saving: '39%' },
  'job-description-writer':           { name: 'Founder Bundle',   slug: 'founder',   price: '$39', count: 6,  saving: '39%' },
  'business-plan':                    { name: 'Founder Bundle',   slug: 'founder',   price: '$39', count: 6,  saving: '39%' },
  'prd-writer':                       { name: 'Founder Bundle',   slug: 'founder',   price: '$39', count: 6,  saving: '39%' },
  'architecture-diagram-prompt':      { name: 'Founder Bundle',   slug: 'founder',   price: '$39', count: 6,  saving: '39%' },
  'performance-review-writer':        { name: 'Founder Bundle',   slug: 'founder',   price: '$39', count: 6,  saving: '39%' },
  'linkedin-post-engine':             { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'seo-blog-post-brief':              { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'email-newsletter-engine':          { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'social-content-engine':            { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'twitter-x-thread-engine':          { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'brand-voice-guide':                { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'content-calendar':                 { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'logo-brand-identity':              { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'social-media-carousel-prompt':     { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'brand-ad-copy':                    { name: 'Marketing Bundle', slug: 'marketing', price: '$45', count: 5,  saving: '31%' },
  'ugc-ad-creator':                   { name: 'Marketing Bundle', slug: 'marketing', price: '$45', count: 5,  saving: '31%' },
  'pr-press-release':                 { name: 'Marketing Bundle', slug: 'marketing', price: '$45', count: 5,  saving: '31%' },
  'ecommerce-product-listing':        { name: 'Marketing Bundle', slug: 'marketing', price: '$45', count: 5,  saving: '31%' },
  'product-photography-prompt':       { name: 'Marketing Bundle', slug: 'marketing', price: '$45', count: 5,  saving: '31%' },
  'nda-contract-draft':               { name: 'Legal/Biz Bundle', slug: 'legal-biz', price: '$45', count: 5,  saving: '35%' },
  'tos-privacy-policy':               { name: 'Legal/Biz Bundle', slug: 'legal-biz', price: '$45', count: 5,  saving: '35%' },
  'financial-model-prompt':           { name: 'Legal/Biz Bundle', slug: 'legal-biz', price: '$45', count: 5,  saving: '35%' },
  'visa-cover-letter':                { name: 'Legal/Biz Bundle', slug: 'legal-biz', price: '$45', count: 5,  saving: '35%' },
  'grant-and-proposal-writing':       { name: 'Legal/Biz Bundle', slug: 'legal-biz', price: '$45', count: 5,  saving: '35%' },
  'video-script-engine':              { name: 'Video/Pod Bundle', slug: 'video-pod', price: '$69', count: 9,  saving: '39%' },
  'podcast-episode-script':           { name: 'Video/Pod Bundle', slug: 'video-pod', price: '$69', count: 9,  saving: '39%' },
  'short-form-ai-video':              { name: 'Video/Pod Bundle', slug: 'video-pod', price: '$69', count: 9,  saving: '39%' },
  'podcast-show-notes':               { name: 'Video/Pod Bundle', slug: 'video-pod', price: '$69', count: 9,  saving: '39%' },
  'webinar-online-event-script':      { name: 'Video/Pod Bundle', slug: 'video-pod', price: '$69', count: 9,  saving: '39%' },
  'ai-animation-film-prompt':         { name: 'Video/Pod Bundle', slug: 'video-pod', price: '$69', count: 9,  saving: '39%' },
  'product-ad-film-prompt':           { name: 'Video/Pod Bundle', slug: 'video-pod', price: '$69', count: 9,  saving: '39%' },
  'dialogue-character-film-prompt':   { name: 'Video/Pod Bundle', slug: 'video-pod', price: '$69', count: 9,  saving: '39%' },
  'youtube-thumbnail-prompt':         { name: 'Video/Pod Bundle', slug: 'video-pod', price: '$69', count: 9,  saving: '39%' },
  'resume-cv-builder':                { name: 'Student Bundle',   slug: 'student',   price: '$29', count: 5,  saving: '38%' },
  'cover-letter-writer':              { name: 'Student Bundle',   slug: 'student',   price: '$29', count: 5,  saving: '38%' },
  'university-sop':                   { name: 'Student Bundle',   slug: 'student',   price: '$29', count: 5,  saving: '38%' },
  'research-paper-outline':           { name: 'Student Bundle',   slug: 'student',   price: '$29', count: 5,  saving: '38%' },
  'conference-abstract':              { name: 'Student Bundle',   slug: 'student',   price: '$29', count: 5,  saving: '38%' },
  'real-estate-listing-copy':         { name: 'Realtor Bundle',   slug: 'realtor',   price: '$29', count: 5,  saving: '33%' },
  'real-estate-photo-prompt':         { name: 'Realtor Bundle',   slug: 'realtor',   price: '$29', count: 5,  saving: '33%' },
  'hotel-airbnb-listing-copy':        { name: 'Realtor Bundle',   slug: 'realtor',   price: '$29', count: 5,  saving: '33%' },
  'home-renovation-brief':            { name: 'Realtor Bundle',   slug: 'realtor',   price: '$29', count: 5,  saving: '33%' },
  'travel-itinerary-planner':         { name: 'Realtor Bundle',   slug: 'realtor',   price: '$29', count: 5,  saving: '33%' },
  'lesson-plan-builder':              { name: 'Educator Bundle',  slug: 'educator',  price: '$29', count: 4,  saving: '38%' },
  'exam-paper-generator':             { name: 'Educator Bundle',  slug: 'educator',  price: '$29', count: 4,  saving: '38%' },
  'course-curriculum-builder':        { name: 'Educator Bundle',  slug: 'educator',  price: '$29', count: 4,  saving: '38%' },
  'wedding-vows-writer':              { name: 'Wedding Bundle',   slug: 'wedding',   price: '$15', count: 4,  saving: '25%' },
  'wedding-invitation-prompt':        { name: 'Wedding Bundle',   slug: 'wedding',   price: '$15', count: 4,  saving: '25%' },
  'event-speech-writer':              { name: 'Wedding Bundle',   slug: 'wedding',   price: '$15', count: 4,  saving: '25%' },
  'menu-description-copy':            { name: 'Wedding Bundle',   slug: 'wedding',   price: '$15', count: 4,  saving: '25%' },
  'short-story-prompt':               { name: 'Creative Bundle',  slug: 'creative',  price: '$19', count: 6,  saving: '41%' },
  'screenplay-script':                { name: 'Creative Bundle',  slug: 'creative',  price: '$19', count: 6,  saving: '41%' },
  'book-cover-prompt':                { name: 'Creative Bundle',  slug: 'creative',  price: '$19', count: 6,  saving: '41%' },
  'poetry-verse-prompt':              { name: 'Creative Bundle',  slug: 'creative',  price: '$19', count: 6,  saving: '41%' },
  'childrens-book-prompt':            { name: 'Creative Bundle',  slug: 'creative',  price: '$19', count: 6,  saving: '41%' },
  'festival-holiday-greeting-prompt': { name: 'Creative Bundle',  slug: 'creative',  price: '$19', count: 6,  saving: '41%' },
  'eulogy-writer':                    { name: 'Creative Bundle',  slug: 'creative',  price: '$19', count: 6,  saving: '41%' },
  'health-wellness-plan':             { name: 'Creator Bundle',   slug: 'creator',   price: '$45', count: 7,  saving: '34%' },
  'recipe-development-prompt':        { name: 'Wedding Bundle',   slug: 'wedding',   price: '$15', count: 4,  saving: '25%' },
};

function buildDay7Html({ skillName, skillSlug, bundle, orderId }) {
  const bundleHtml = bundle ? `
          <!-- Bundle upsell -->
          <div style="background:#f7f6f2;border-radius:12px;padding:24px 28px;margin:0 0 28px;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#8a8980;text-transform:uppercase;letter-spacing:0.08em;">If it worked for you</p>
            <p style="margin:0 0 16px;font-size:15px;color:#111110;font-weight:700;line-height:1.4;">The ${bundle.name} has ${bundle.count} skills built for this kind of work — ${bundle.price}, save ${bundle.saving}.</p>
            <p style="margin:0 0 16px;font-size:14px;color:#545249;line-height:1.6;">Cheaper than buying them one by one, and they all work the same way as the one you have.</p>
            <a href="https://novakit.tech/skills/bundles/${bundle.slug}-bundle.html" style="display:inline-block;padding:12px 20px;background:#DE7356;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px;">See the ${bundle.name} — ${bundle.price}</a>
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
          <p style="margin:0 0 8px;font-size:12px;color:#8a8980;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">One week in</p>
          <h1 style="margin:0 0 20px;font-size:26px;font-weight:800;color:#111110;letter-spacing:-0.02em;">Did ${skillName} save you time?</h1>

          <p style="margin:0 0 28px;font-size:15px;color:#545249;line-height:1.6;">
            It has been a week — did it do what you needed? Reply and let us know. We read every response.
          </p>

          ${bundleHtml}

          <!-- Refund reminder -->
          <div style="border:1px solid #eeecea;border-radius:10px;padding:18px 22px;margin:0 0 28px;">
            <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#111110;">🛡️ Last day of your refund window</p>
            <p style="margin:0;font-size:13px;color:#545249;line-height:1.6;">
              If it was not what you expected, today is the last day of your 7-day refund period. Just reply to this email and we will sort it — no questions asked.
            </p>
          </div>

          <!-- Sign off -->
          <p style="margin:0 0 28px;font-size:15px;color:#545249;line-height:1.6;">
            Thanks for trying NovaKit.
          </p>

          <!-- Support note -->
          <p style="margin:0;font-size:13px;color:#8a8980;line-height:1.7;">
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

  const { to, skillName, skillSlug, orderId } = body;
  if (!to || !skillName || !skillSlug) {
    return new Response('Missing required fields', { status: 400, headers: CORS });
  }

  const bundle = BUNDLE_UPSELL[skillSlug] || null;
  const emailHtml = buildDay7Html({ skillName, skillSlug, bundle, orderId });

  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'NovaKit <support@novakit.tech>',
        to: [to],
        subject: `Did ${skillName} save you time?`,
        html: emailHtml,
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error('[send-email-day7] Resend error:', err);
      return new Response(JSON.stringify({ error: 'Email send failed', detail: err }), {
        status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
      });
    }

    const data = await res.json();
    return new Response(JSON.stringify({ ok: true, emailId: data.id }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
    });

  } catch (err) {
    console.error('[send-email-day7]', err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }
}
