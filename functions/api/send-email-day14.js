// functions/api/send-email-day14.js
// Day 14 post-purchase email — referral/affiliate ask.
// Uses the order payment ID (first 8 chars) as a lightweight ref code.
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
  if (!to || !skillName || !orderId) {
    return new Response(JSON.stringify({ error: 'Missing required fields' }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  if (!env.RESEND_API_KEY) {
    return new Response(JSON.stringify({ error: 'Email service not configured' }), {
      status: 503, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  // Short ref code derived from order ID — easy to recognise in UTM reports
  const refCode = String(orderId).replace(/[^a-z0-9]/gi, '').slice(0, 8).toLowerCase();
  const refLink = `https://novakit.tech?ref=${refCode}&utm_source=referral&utm_medium=email&utm_campaign=day14_referral`;

  const html = buildDay14Html({ skillName, orderId, refCode, refLink });

  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${env.RESEND_API_KEY}` },
    body: JSON.stringify({
      from: 'NovaKit <support@novakit.tech>',
      to,
      subject: `Earn 40% on every NovaKit sale you refer`,
      html,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    console.error('[send-email-day14] Resend error:', err);
    return new Response(JSON.stringify({ error: 'Email send failed' }), {
      status: 502, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
  });
}

function buildDay14Html({ skillName, orderId, refCode, refLink }) {
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
          <p style="margin:0 0 8px;font-size:12px;color:#8a8980;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Day 14</p>
          <h1 style="margin:0 0 20px;font-size:24px;font-weight:800;color:#111110;letter-spacing:-0.02em;">If ${skillName} worked for you — earn 40% sharing it.</h1>

          <p style="margin:0 0 24px;font-size:15px;color:#545249;line-height:1.6;">
            Two weeks in. If the skill did what it was supposed to, there's probably someone in your life who'd get the same value from it — a colleague, a client, someone in a group you're in.
          </p>

          <p style="margin:0 0 24px;font-size:15px;color:#545249;line-height:1.6;">
            We pay <strong style="color:#111110;">40% commission</strong> on every sale you refer — skills, bundles, All Access. No cap. Paid manually for now (reply to confirm a sale, we'll sort payment) — we're keeping it simple while we build out the dashboard.
          </p>

          <!-- Ref link box -->
          <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:24px 28px;margin:0 0 28px;">
            <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#16a34a;text-transform:uppercase;letter-spacing:0.08em;">Your referral link</p>
            <p style="margin:0 0 16px;font-size:13px;color:#545249;line-height:1.5;">Share this link. When someone buys through it, reply to this email with "referral" and we'll confirm and pay you within 48 hours.</p>
            <div style="background:#ffffff;border:1px solid #bbf7d0;border-radius:8px;padding:12px 16px;margin:0 0 16px;word-break:break-all;">
              <span style="font-family:monospace;font-size:13px;color:#111110;">${refLink}</span>
            </div>
            <p style="margin:0;font-size:12px;color:#8a8980;">Your ref code: <strong style="font-family:monospace;">${refCode}</strong></p>
          </div>

          <!-- How it works -->
          <table cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 28px;">
            <tr><td colspan="2" style="padding:0 0 14px;">
              <p style="margin:0;font-size:13px;font-weight:700;color:#111110;text-transform:uppercase;letter-spacing:0.06em;">How it works</p>
            </td></tr>
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #eeecea;vertical-align:top;width:24px;">
                <div style="width:24px;height:24px;background:#DE7356;border-radius:12px;text-align:center;line-height:24px;font-size:11px;font-weight:700;color:#fff;">1</div>
              </td>
              <td style="padding:10px 0 10px 14px;border-bottom:1px solid #eeecea;font-size:14px;color:#545249;line-height:1.5;">Share your link in a post, a DM, a newsletter, wherever it fits naturally.</td>
            </tr>
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #eeecea;vertical-align:top;">
                <div style="width:24px;height:24px;background:#DE7356;border-radius:12px;text-align:center;line-height:24px;font-size:11px;font-weight:700;color:#fff;">2</div>
              </td>
              <td style="padding:10px 0 10px 14px;border-bottom:1px solid #eeecea;font-size:14px;color:#545249;line-height:1.5;">Someone buys through it. They get the skill. You get 40% of the sale price.</td>
            </tr>
            <tr>
              <td style="padding:10px 0;vertical-align:top;">
                <div style="width:24px;height:24px;background:#DE7356;border-radius:12px;text-align:center;line-height:24px;font-size:11px;font-weight:700;color:#fff;">3</div>
              </td>
              <td style="padding:10px 0 10px 14px;font-size:14px;color:#545249;line-height:1.5;">Reply to this email saying "referral" — we confirm and pay within 48 hours via PayPal or bank transfer.</td>
            </tr>
          </table>

          <p style="margin:0 0 8px;font-size:14px;color:#545249;line-height:1.6;">
            <strong style="color:#111110;">On a $69 All Access sale, you earn $27.60.</strong> On a $45 bundle, $18. On a single $9 skill, $3.60. Share once in the right place and it compounds.
          </p>

          <p style="margin:24px 0 0;font-size:13px;color:#8a8980;line-height:1.6;">
            Questions? Reply to this email — I read them all.<br>
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
