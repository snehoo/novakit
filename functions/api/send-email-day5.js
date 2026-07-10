// functions/api/send-email-day5.js
// Day 5 post-purchase email — All Access pitch.
// Called by email-sequence-cron.js
// Body: { to, skillName, orderId }
// Env: RESEND_API_KEY

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch {
    return new Response('Bad JSON', { status: 400, headers: CORS });
  }

  const { to, skillName, orderId } = body;
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

  const html = buildDay5Html({ skillName, orderId });

  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${env.RESEND_API_KEY}` },
    body: JSON.stringify({
      from: 'NovaKit <support@novakit.tech>',
      to,
      subject: `You've used 1 skill. Here's what 60+ looks like.`,
      html,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    console.error('[send-email-day5] Resend error:', err);
    return new Response(JSON.stringify({ error: 'Email send failed' }), {
      status: 502, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
  });
}

function buildDay5Html({ skillName, orderId }) {
  const categories = [
    { label: 'Business & Founder',  skills: 'Pitch Deck, Cold Outreach, Sales Page, Investor Update, Business Plan, PRD Writer' },
    { label: 'Content & Social',    skills: 'LinkedIn Post Engine, Email Newsletter, SEO Blog Brief, Content Calendar, Twitter/X Thread, Brand Voice Guide' },
    { label: 'Marketing',           skills: 'Brand Ad Copy, PR Press Release, eCommerce Listing, UGC Ad Creator, Sales Landing Page' },
    { label: 'Video & Podcast',     skills: 'Video Script, Podcast Episode, Short-Form AI Video, Show Notes, Webinar Script, Film Prompts' },
    { label: 'Creative Writing',    skills: 'Short Story, Screenplay, Poetry, Children\'s Book, Eulogy Writer, Holiday Greeting' },
    { label: 'Real Estate',         skills: 'Listing Copy, Photo Prompt, Airbnb Copy, Home Renovation Brief' },
    { label: 'Education',           skills: 'Lesson Plan, Exam Paper, Course Curriculum' },
    { label: 'Career & Legal',      skills: 'Resume, Cover Letter, NDA Draft, Grant Proposal, Visa Cover Letter' },
  ];

  const catRows = categories.map(c => `
    <tr>
      <td style="padding:10px 0;border-bottom:1px solid #eeecea;vertical-align:top;width:40%;">
        <span style="font-size:13px;font-weight:700;color:#111110;">${c.label}</span>
      </td>
      <td style="padding:10px 0 10px 16px;border-bottom:1px solid #eeecea;vertical-align:top;">
        <span style="font-size:13px;color:#545249;line-height:1.5;">${c.skills}</span>
      </td>
    </tr>`).join('');

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
          <p style="margin:0 0 8px;font-size:12px;color:#8a8980;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Day 5</p>
          <h1 style="margin:0 0 20px;font-size:24px;font-weight:800;color:#111110;letter-spacing:-0.02em;">You've been running ${skillName}. Here's what else is in the kit.</h1>

          <p style="margin:0 0 24px;font-size:15px;color:#545249;line-height:1.6;">
            NovaKit has 60+ skills across 8 categories. Every one runs live research before it writes. Here's the full map — in case something else on this list is sitting on your to-do list.
          </p>

          <!-- Skills table -->
          <table cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 28px;">
            ${catRows}
          </table>

          <!-- All Access CTA -->
          <div style="background:#0d0d0b;border-radius:14px;padding:28px;margin:0 0 28px;text-align:center;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#DE7356;text-transform:uppercase;letter-spacing:0.1em;">All Access</p>
            <p style="margin:0 0 8px;font-size:26px;font-weight:800;color:#ffffff;letter-spacing:-0.02em;">Every skill. One price.</p>
            <p style="margin:0 0 20px;font-size:15px;color:#8a8980;line-height:1.5;">60+ skills, all categories, all future additions — $69 once, no subscription.</p>
            <a href="https://novakit.tech/checkout?sku=all-access&utm_source=email&utm_medium=sequence&utm_campaign=day5_allaccess" style="display:inline-block;padding:14px 32px;background:#DE7356;color:#ffffff;text-decoration:none;border-radius:10px;font-weight:700;font-size:16px;">Get All Access — $69 →</a>
            <p style="margin:16px 0 0;font-size:12px;color:#545249;">7-day refund if it's not what you expected.</p>
          </div>

          <p style="margin:0 0 8px;font-size:14px;color:#545249;line-height:1.6;">
            Not ready for All Access? Individual skills from $5, bundles by category from $15. Browse at <a href="https://novakit.tech?utm_source=email&utm_medium=sequence&utm_campaign=day5_browse" style="color:#DE7356;">novakit.tech</a>.
          </p>

          <p style="margin:0;font-size:13px;color:#8a8980;line-height:1.6;">
            Questions? Reply or write to <a href="mailto:support@novakit.tech" style="color:#DE7356;">support@novakit.tech</a>.<br>
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
