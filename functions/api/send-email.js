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
        <tr><td style="background:#0d0d0b;padding:32px 40px;text-align:center;">
          <img src="https://assets.novakit.tech/nkwhite.jpg" alt="NovaKit" height="28" style="display:block;margin:0 auto;">
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:40px;">
          <p style="margin:0 0 8px;font-size:13px;color:#8a8980;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Your skill is ready</p>
          <h1 style="margin:0 0 24px;font-size:26px;font-weight:800;color:#111110;letter-spacing:-0.02em;">${skillName}</h1>

          <p style="margin:0 0 24px;font-size:15px;color:#545249;line-height:1.6;">
            Your purchase was successful. Download your skill file below and add it to Claude to get started.
          </p>

          <!-- Download buttons -->
          <div style="margin:0 0 32px;">
            ${fileLinksHtml}
          </div>

          <!-- How to use -->
          <div style="background:#f7f6f2;border-radius:10px;padding:24px;margin:0 0 32px;">
            <p style="margin:0 0 12px;font-size:13px;font-weight:700;color:#111110;text-transform:uppercase;letter-spacing:0.06em;">How to use your skill</p>
            <ol style="margin:0;padding:0 0 0 18px;font-size:14px;color:#545249;line-height:1.8;">
              <li>Download the <code style="background:#eeecea;padding:2px 6px;border-radius:4px;font-size:13px;">.skill</code> file above</li>
              <li>Open <a href="https://claude.ai" style="color:#DE7356;">claude.ai</a> and start a new project</li>
              <li>Add the skill file to your project knowledge</li>
              <li>Type your request — the skill takes it from there</li>
            </ol>
          </div>

          <!-- Support note -->
          <p style="margin:0;font-size:13px;color:#8a8980;line-height:1.6;">
            Questions? Reply to this email or visit <a href="https://novakit.tech" style="color:#DE7356;">novakit.tech</a>.<br>
            Order ID: <code style="font-size:12px;">${orderId}</code>
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f7f6f2;padding:24px 40px;text-align:center;border-top:1px solid #eeecea;">
          <p style="margin:0;font-size:12px;color:#8a8980;">
            © 2026 NovaKit · <a href="https://novakit.tech/legal/privacy.html" style="color:#8a8980;">Privacy</a> · <a href="https://novakit.tech/legal/terms.html" style="color:#8a8980;">Terms</a>
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
        from: 'NovaKit <skills@novakit.tech>',
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
