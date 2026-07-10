// functions/api/free-skill.js
// POST /api/free-skill
// Body: { email, utmSource, utmMedium, utmCampaign }
//
// 1. Validates email
// 2. Adds contact to Brevo list 8 (NovaKit-Leads)
// 3. Fetches LinkedIn Post Engine file URL from R2
// 4. Sends delivery email via Resend
// Env: BREVO_API_KEY, RESEND_API_KEY, R2_BUCKET

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

const FREE_SKILL_SLUG = 'linkedin-post-engine';
const FREE_SKILL_NAME = 'LinkedIn Post Engine';

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch {
    return new Response('Bad JSON', { status: 400, headers: CORS });
  }

  const { email, utmSource = '', utmMedium = '', utmCampaign = '' } = body;

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
    return new Response(JSON.stringify({ error: 'Valid email required' }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  const cleanEmail = email.trim().toLowerCase();

  // 1. Add to Brevo list 8 (NovaKit-Leads) — fire-and-forget
  if (env.BREVO_API_KEY) {
    fetch('https://api.brevo.com/v3/contacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'api-key': env.BREVO_API_KEY },
      body: JSON.stringify({
        email: cleanEmail,
        listIds: [8],
        updateEnabled: true,
        attributes: {
          SOURCE:       'novakit_free_skill',
          UTM_SOURCE:   utmSource,
          UTM_MEDIUM:   utmMedium,
          UTM_CAMPAIGN: utmCampaign,
          SKU:          FREE_SKILL_SLUG,
        },
      }),
    }).catch(e => console.warn('[brevo] free-skill lead sync failed:', e.message));
  }

  // 2. Get skill file URL from R2
  let fileUrl = '';
  try {
    const listed = await env.R2_BUCKET.list({ prefix: `skill/nk-${FREE_SKILL_SLUG}` });
    if (listed.objects.length > 0) {
      fileUrl = `https://assets.novakit.tech/${listed.objects[0].key}`;
    }
  } catch (e) {
    console.warn('[free-skill] R2 list error:', e.message);
  }
  // Fallback if R2 list fails
  if (!fileUrl) fileUrl = `https://assets.novakit.tech/skill/nk-${FREE_SKILL_SLUG}.skill`;

  // 3. Send delivery email via Resend
  if (!env.RESEND_API_KEY) {
    return new Response(JSON.stringify({ error: 'Email service not configured' }), {
      status: 503, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  const emailHtml = buildEmail(cleanEmail, fileUrl);

  const resendRes = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${env.RESEND_API_KEY}`,
    },
    body: JSON.stringify({
      from: 'NovaKit <support@novakit.tech>',
      to: cleanEmail,
      subject: `Your free LinkedIn Post Engine skill`,
      html: emailHtml,
    }),
  });

  if (!resendRes.ok) {
    const err = await resendRes.text();
    console.error('[free-skill] Resend error:', err);
    return new Response(JSON.stringify({ error: 'Email delivery failed' }), {
      status: 502, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
  });
}

function buildEmail(email, fileUrl) {
  return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f7f6f2;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f6f2;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background:#0d0d0b;padding:24px 40px;">
          <img src="https://novakit.tech/assets/nkwhite.jpg" alt="NovaKit" height="28" style="display:block;border:0;">
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:40px;">
          <p style="margin:0 0 8px;font-size:12px;color:#8a8980;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Your free skill</p>
          <h1 style="margin:0 0 16px;font-size:26px;font-weight:800;color:#111110;letter-spacing:-0.02em;">LinkedIn Post Engine</h1>

          <p style="margin:0 0 28px;font-size:15px;color:#545249;line-height:1.6;">
            Here's your skill file. It runs live trend research before every post — so the hooks and angles it gives you are calibrated to what's actually landing this week, not last year.
          </p>

          <!-- Download button -->
          <div style="margin:0 0 36px;">
            <a href="${fileUrl}" style="display:inline-block;padding:14px 28px;background:#DE7356;color:#ffffff;text-decoration:none;border-radius:10px;font-weight:700;font-size:15px;">⬇ Download LinkedIn Post Engine.skill</a>
          </div>

          <!-- How to install -->
          <div style="background:#f7f6f2;border-radius:12px;padding:28px;margin:0 0 32px;">
            <p style="margin:0 0 20px;font-size:12px;font-weight:700;color:#111110;text-transform:uppercase;letter-spacing:0.08em;">Install in 3 steps</p>
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr><td style="padding:12px 0;border-bottom:1px solid #eeecea;vertical-align:top;">
                <table cellpadding="0" cellspacing="0"><tr>
                  <td width="28" style="width:28px;min-width:28px;"><div style="width:28px;height:28px;background:#DE7356;border-radius:14px;text-align:center;line-height:28px;font-size:12px;font-weight:700;color:#fff;">1</div></td>
                  <td style="padding-left:14px;font-size:14px;color:#111110;">Open Claude → <strong>Customize</strong> → <strong>Skills</strong> → <strong>+</strong> → <strong>Upload a skill</strong></td>
                </tr></table>
              </td></tr>
              <tr><td style="padding:12px 0;border-bottom:1px solid #eeecea;vertical-align:top;">
                <table cellpadding="0" cellspacing="0"><tr>
                  <td width="28" style="width:28px;min-width:28px;"><div style="width:28px;height:28px;background:#DE7356;border-radius:14px;text-align:center;line-height:28px;font-size:12px;font-weight:700;color:#fff;">2</div></td>
                  <td style="padding-left:14px;font-size:14px;color:#111110;">Drop in the <code style="background:#eeecea;padding:2px 6px;border-radius:4px;font-size:12px;">.skill</code> file you just downloaded</td>
                </tr></table>
              </td></tr>
              <tr><td style="padding:12px 0 0;vertical-align:top;">
                <table cellpadding="0" cellspacing="0"><tr>
                  <td width="28" style="width:28px;min-width:28px;"><div style="width:28px;height:28px;background:#DE7356;border-radius:14px;text-align:center;line-height:28px;font-size:12px;font-weight:700;color:#fff;">3</div></td>
                  <td style="padding-left:14px;font-size:14px;color:#111110;">Type <code style="background:#eeecea;padding:2px 6px;border-radius:4px;font-size:12px;">/</code> in any Claude chat and select the skill</td>
                </tr></table>
              </td></tr>
            </table>
          </div>

          <!-- Upsell nudge -->
          <div style="background:#fdf3f0;border:1px solid rgba(222,115,86,0.25);border-radius:12px;padding:24px;margin:0 0 32px;">
            <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#DE7356;text-transform:uppercase;letter-spacing:0.06em;">Want more?</p>
            <p style="margin:0 0 16px;font-size:15px;color:#111110;line-height:1.5;">The Creator Bundle includes 8 more skills — Content Calendar, Email Newsletter Engine, Social Content Engine, and others — for $29.</p>
            <a href="https://novakit.tech/checkout?sku=creator-bundle&utm_source=email&utm_medium=free_skill&utm_campaign=linkedin_post_engine" style="display:inline-block;padding:11px 22px;background:#111110;color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;">See the Creator Bundle →</a>
          </div>

          <p style="margin:0;font-size:13px;color:#8a8980;line-height:1.6;">
            Questions? Reply to this email or contact <a href="mailto:support@novakit.tech" style="color:#DE7356;">support@novakit.tech</a>.<br>
            7-day refund on any paid skill, no questions asked.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:20px 40px;border-top:1px solid #eeecea;">
          <p style="margin:0;font-size:12px;color:#9a9890;text-align:center;">
            © 2026 NovaKit · <a href="https://novakit.tech" style="color:#9a9890;">novakit.tech</a> ·
            You're receiving this because you requested a free skill.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;
}
