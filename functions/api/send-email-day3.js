// functions/api/send-email-day3.js
// Day 3 post-purchase email — before/after cross-sell.
// Shows a concrete output comparison and surfaces one complementary skill.
// Called by email-sequence-cron.js
// Body: { to, skillName, skillSlug, orderId }
// Env: RESEND_API_KEY

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

// Cross-sell: given the skill they bought, which skill is the natural next one?
const CROSS_SELL = {
  'linkedin-post-engine':       { slug: 'email-newsletter-engine',  name: 'Email Newsletter Engine',  price: '$9',  pitch: 'Turn the same ideas into a newsletter your subscribers actually read.' },
  'email-newsletter-engine':    { slug: 'linkedin-post-engine',     name: 'LinkedIn Post Engine',     price: '$9',  pitch: 'Repurpose your best newsletter sections into LinkedIn posts that get seen.' },
  'cold-outreach-email':        { slug: 'sales-page',               name: 'Sales Page Copy',          price: '$9',  pitch: 'When they click through from your cold email, they need a page that closes.' },
  'sales-page':                 { slug: 'cold-outreach-email',      name: 'Cold Outreach Email',      price: '$9',  pitch: 'Drive traffic to that page with cold emails that actually get replies.' },
  'pitch-deck-narrative':       { slug: 'investor-update-email',    name: 'Investor Update Email',    price: '$9',  pitch: 'Keep investors warm between rounds with updates that show momentum.' },
  'investor-update-email':      { slug: 'pitch-deck-narrative',     name: 'Pitch Deck Narrative',     price: '$9',  pitch: 'When you need to raise, this turns your traction into a compelling story.' },
  'seo-blog-post-brief':        { slug: 'content-calendar',         name: 'Content Calendar',         price: '$8',  pitch: 'Plan 30 days of briefs in one session so you never stare at a blank brief again.' },
  'content-calendar':           { slug: 'seo-blog-post-brief',      name: 'SEO Blog Post Brief',      price: '$9',  pitch: 'Turn every calendar slot into a brief that ranks.' },
  'resume-cv-builder':          { slug: 'cover-letter-writer',      name: 'Cover Letter Writer',      price: '$5',  pitch: 'Your CV gets you past the filter. Your cover letter gets you the interview.' },
  'cover-letter-writer':        { slug: 'resume-cv-builder',        name: 'Resume / CV Builder',      price: '$5',  pitch: 'Strong cover letter, weak CV — they still won\'t call. Fix both.' },
  'real-estate-listing-copy':   { slug: 'real-estate-photo-prompt', name: 'Real Estate Photo Prompt', price: '$5',  pitch: 'Great copy can\'t fix bad photos. Run both and close faster.' },
  'lesson-plan-builder':        { slug: 'exam-paper-generator',     name: 'Exam Paper Generator',     price: '$9',  pitch: 'Lesson plan built. Now generate a matching assessment in minutes.' },
  'brand-voice-guide':          { slug: 'brand-ad-copy',            name: 'Brand Ad Copy',            price: '$9',  pitch: 'Voice defined. Now write ads that actually sound like your brand.' },
  'brand-ad-copy':              { slug: 'brand-voice-guide',        name: 'Brand Voice Guide',        price: '$15', pitch: 'Ad copy without a voice guide drifts. Lock in the voice first.' },
  'podcast-episode-script':     { slug: 'podcast-show-notes',       name: 'Podcast Show Notes',       price: '$5',  pitch: 'Script done. Now generate SEO show notes and timestamps in minutes.' },
  'podcast-show-notes':         { slug: 'podcast-episode-script',   name: 'Podcast Episode Script',   price: '$9',  pitch: 'Great notes, no structure? Script your episodes so every minute earns its keep.' },
};

const DEFAULT_CROSS_SELL = { slug: 'content-calendar', name: 'Content Calendar', price: '$8', pitch: 'Plan 30 days of AI-assisted content in one session.' };

export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch {
    return new Response('Bad JSON', { status: 400, headers: CORS });
  }

  const { to, skillName, skillSlug, orderId } = body;
  if (!to || !skillName) {
    return new Response(JSON.stringify({ error: 'Missing required fields' }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  if (!env.RESEND_API_KEY) {
    return new Response(JSON.stringify({ error: 'Email service not configured' }), {
      status: 503, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  const cross = CROSS_SELL[skillSlug] || DEFAULT_CROSS_SELL;
  const html = buildDay3Html({ skillName, skillSlug, cross, orderId });

  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${env.RESEND_API_KEY}` },
    body: JSON.stringify({
      from: 'NovaKit <support@novakit.tech>',
      to,
      subject: `One thing that makes ${skillName} work even better`,
      html,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    console.error('[send-email-day3] Resend error:', err);
    return new Response(JSON.stringify({ error: 'Email send failed' }), {
      status: 502, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
  });
}

function buildDay3Html({ skillName, skillSlug, cross, orderId }) {
  return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f7f6f2;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f6f2;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.08);">

        <tr><td style="background:#0d0d0b;padding:24px 40px;">
          <img src="https://novakit.tech/assets/nkwhite.jpg" alt="NovaKit" height="28" style="display:block;border:0;">
        </td></tr>

        <tr><td style="padding:40px;">
          <p style="margin:0 0 8px;font-size:12px;color:#8a8980;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Day 3</p>
          <h1 style="margin:0 0 20px;font-size:24px;font-weight:800;color:#111110;letter-spacing:-0.02em;">What separates a good ${skillName} run from a great one</h1>

          <p style="margin:0 0 24px;font-size:15px;color:#545249;line-height:1.6;">
            The skill does the research. But what you put <em>into</em> the context block changes the output more than anything else.
          </p>

          <!-- Before / After -->
          <table cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 28px;">
            <tr>
              <td width="48%" valign="top" style="padding:18px;background:#fef2f2;border-radius:10px;border:1px solid #fecaca;">
                <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:#dc2626;text-transform:uppercase;letter-spacing:0.08em;">Weak input</p>
                <p style="margin:0;font-size:13px;color:#545249;line-height:1.55;font-family:monospace;">"Write something about my business"</p>
              </td>
              <td width="4%" style="text-align:center;font-size:18px;color:#8a8980;">→</td>
              <td width="48%" valign="top" style="padding:18px;background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0;">
                <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:#16a34a;text-transform:uppercase;letter-spacing:0.08em;">Strong input</p>
                <p style="margin:0;font-size:13px;color:#545249;line-height:1.55;font-family:monospace;">"B2B SaaS, target: mid-market ops managers, goal: book a demo call, tone: direct not salesy"</p>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 28px;font-size:15px;color:#545249;line-height:1.6;">
            The more specific you are about your audience, your goal, and what you <em>don't</em> want — the more the live research the skill pulls gets used correctly.
          </p>

          <!-- Cross-sell -->
          <div style="background:#f7f6f2;border-radius:12px;padding:24px 28px;margin:0 0 28px;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#8a8980;text-transform:uppercase;letter-spacing:0.08em;">One skill that pairs well with ${skillName}</p>
            <p style="margin:0 0 4px;font-size:17px;font-weight:800;color:#111110;">${cross.name} — ${cross.price}</p>
            <p style="margin:0 0 16px;font-size:14px;color:#545249;line-height:1.55;">${cross.pitch}</p>
            <a href="https://novakit.tech/skills/${cross.slug}.html?utm_source=email&utm_medium=sequence&utm_campaign=day3_crosssell" style="display:inline-block;padding:11px 20px;background:#DE7356;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px;">See ${cross.name} →</a>
          </div>

          <p style="margin:0;font-size:13px;color:#8a8980;line-height:1.6;">
            Reply if you have questions — or write to <a href="mailto:support@novakit.tech" style="color:#DE7356;">support@novakit.tech</a>.<br>
            <span style="font-family:monospace;font-size:11px;">Order: ${orderId}</span>
          </p>
        </td></tr>

        <tr><td style="padding:20px 40px;border-top:1px solid #eeecea;">
          <p style="margin:0;font-size:12px;color:#9a9890;text-align:center;">© 2026 NovaKit · <a href="https://novakit.tech" style="color:#9a9890;">novakit.tech</a></p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;
}
