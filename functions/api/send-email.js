// functions/api/send-email.js
// POST /api/send-email
// Body: { to, skillName, skillSlug, fileUrls, isBundle, bundleKey, orderId }
//
// Sends the delivery email via Resend.
// Set RESEND_API_KEY in Cloudflare Pages env variables.

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

  const { to, skillName, skillSlug, fileUrls, isBundle, orderId } = body;
  if (!to || !skillName || !fileUrls?.length) {
    return new Response('Missing required fields', { status: 400, headers: CORS });
  }

  // Build file links HTML
  const fileLinksHtml = fileUrls.map(url => {
    const filename = url.split('/').pop();
    const displayName = filename
      .replace('nk-', '')
      .replace(/(-[a-f0-9]+\.skill)$/, '.skill');
    return `<a href="${url}" style="display:inline-block;margin:8px 0;padding:12px 20px;background:#DE7356;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px;">⬇ Download ${displayName}</a>`;
  }).join('\n');

  const emailHtml = `<!DOCTYPE html>
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
          <p style="margin:0 0 8px;font-size:12px;color:#8a8980;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Your skill is ready</p>
          <h1 style="margin:0 0 20px;font-size:26px;font-weight:800;color:#111110;letter-spacing:-0.02em;">${skillName}</h1>

          <p style="margin:0 0 28px;font-size:15px;color:#545249;line-height:1.6;">
            Your purchase was successful. Download your skill file below and follow the 3-step install to get started.
          </p>

          <!-- Download buttons -->
          <div style="margin:0 0 36px;">
            ${fileLinksHtml}
          </div>

          <!-- How to install -->
          <div style="background:#f7f6f2;border-radius:12px;padding:28px;margin:0 0 32px;">
            <p style="margin:0 0 20px;font-size:12px;font-weight:700;color:#111110;text-transform:uppercase;letter-spacing:0.08em;">How to install — 3 steps</p>

            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td style="padding:14px 0;border-bottom:1px solid #eeecea;vertical-align:top;">
                  <table cellpadding="0" cellspacing="0"><tr>
                    <td width="28" height="28" style="width:28px;height:28px;min-width:28px;background:#DE7356;border-radius:14px;text-align:center;vertical-align:middle;font-size:12px;font-weight:700;color:#fff;padding:0;line-height:28px;">1</td>
                    <td style="padding-left:14px;vertical-align:top;">
                      <div style="font-size:14px;font-weight:700;color:#111110;margin-bottom:4px;">Open Claude → Customize → Skills → <span style="color:#DE7356;">+</span></div>
                      <div style="font-size:13px;color:#545249;line-height:1.5;">In Claude's sidebar click <span style="background:#eeecea;padding:2px 6px;border-radius:4px;font-size:12px;font-family:monospace;">Customize</span>, then <span style="background:#eeecea;padding:2px 6px;border-radius:4px;font-size:12px;font-family:monospace;">Skills</span>, then the <span style="background:#eeecea;padding:2px 6px;border-radius:4px;font-size:12px;font-family:monospace;">+</span> button and choose <span style="background:#eeecea;padding:2px 6px;border-radius:4px;font-size:12px;font-family:monospace;">Upload a skill</span>.</div>
                    </td>
                  </tr></table>
                </td>
              </tr>
              <tr>
                <td style="padding:14px 0;border-bottom:1px solid #eeecea;vertical-align:top;">
                  <table cellpadding="0" cellspacing="0"><tr>
                    <td width="28" height="28" style="width:28px;height:28px;min-width:28px;background:#DE7356;border-radius:14px;text-align:center;vertical-align:middle;font-size:12px;font-weight:700;color:#fff;padding:0;line-height:28px;">2</td>
                    <td style="padding-left:14px;vertical-align:top;">
                      <div style="font-size:14px;font-weight:700;color:#111110;margin-bottom:4px;">Drop in your .skill file</div>
                      <div style="font-size:13px;color:#545249;line-height:1.5;">Drag the downloaded <span style="background:#eeecea;padding:2px 6px;border-radius:4px;font-size:12px;font-family:monospace;">.skill</span> file into the upload area. Wait a moment for validation — you'll see it appear in your skills list.</div>
                    </td>
                  </tr></table>
                </td>
              </tr>
              <tr>
                <td style="padding:14px 0 0;vertical-align:top;">
                  <table cellpadding="0" cellspacing="0"><tr>
                    <td width="28" height="28" style="width:28px;height:28px;min-width:28px;background:#DE7356;border-radius:14px;text-align:center;vertical-align:middle;font-size:12px;font-weight:700;color:#fff;padding:0;line-height:28px;">3</td>
                    <td style="padding-left:14px;vertical-align:top;">
                      <div style="font-size:14px;font-weight:700;color:#111110;margin-bottom:4px;">Type / in any chat to use it</div>
                      <div style="font-size:13px;color:#545249;line-height:1.5;">Start any new chat, type <span style="background:#eeecea;padding:2px 6px;border-radius:4px;font-size:12px;font-family:monospace;">/</span> and select your skill from the menu. Done.</div>
                    </td>
                  </tr></table>
                </td>
              </tr>
            </table>
          </div>

          <!-- Support note -->
          <p style="margin:0;font-size:13px;color:#8a8980;line-height:1.7;">
            Questions or need a refund? Just reply to this email — we're at <a href="mailto:support@novakit.tech" style="color:#DE7356;">support@novakit.tech</a>.<br>
            We have a <strong style="color:#111110;">7-day refund policy</strong> — no questions asked.<br>
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
        subject: `Your skill is ready — ${skillName}`,
        html: emailHtml,
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error('[send-email] Resend error:', err);
      return new Response(JSON.stringify({ error: 'Email send failed', detail: err }), {
        status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
      });
    }

    const data = await res.json();
    return new Response(JSON.stringify({ ok: true, emailId: data.id }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
    });

  } catch (err) {
    console.error('[send-email]', err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }
}
