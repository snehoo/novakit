// functions/api/razorpay-webhook.js
// POST /api/razorpay-webhook
//
// Point this URL in your Razorpay dashboard:
//   Dashboard → Settings → Webhooks → Add new webhook
//   URL: https://novakit.io/api/razorpay-webhook
//   Events to subscribe: payment.captured, payment.failed, refund.created
//
// Razorpay signs every webhook with HMAC-SHA256.
// We MUST verify this before touching the database.

import { getClient, sha256 } from '../_db.js';

import { RZP_SHORT_TO_SKU } from './_plinks.js';

async function verifyRazorpaySignature(rawBody, signature, secret) {
  if (!secret || !/^[0-9a-f]{64}$/i.test(signature)) return false;
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['verify']
  );
  const sigBytes = hexToBytes(signature);
  return crypto.subtle.verify('HMAC', key, sigBytes, new TextEncoder().encode(rawBody));
}

function hexToBytes(hex) {
  const arr = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    arr[i / 2] = parseInt(hex.slice(i, i + 2), 16);
  }
  return arr;
}

export async function onRequestGet() {
  return new Response('OK', { status: 200 });
}

export async function onRequestPost({ request, env }) {
  const rawBody = await request.text();
  const signature = request.headers.get('x-razorpay-signature') ?? '';

  // 1. Verify signature — reject anything that doesn't match
  const valid = await verifyRazorpaySignature(
    rawBody,
    signature,
    env.RAZORPAY_WEBHOOK_SECRET
  );
  if (!valid) {
    console.warn('[webhook] Invalid signature');
    return new Response('Unauthorized', { status: 401 });
  }

  let event;
  try {
    event = JSON.parse(rawBody);
  } catch {
    return new Response('Bad JSON', { status: 400 });
  }

  const client = await getClient(env);
  try {
    const { event: eventName, payload } = event;

    if (eventName === 'payment.captured') {
      const payment = payload.payment.entity;

      const notes      = payment.notes ?? {};

      // Buyer email: Razorpay always captures it on payment links — use it directly
      const buyerEmail = payment.email || notes.buyer_email || null;
      const buyerHash  = buyerEmail ? await sha256(buyerEmail) : null;
      // Webhook comes from Razorpay's servers — no buyer IP available.
      // verify-payment sets the real country via CF-IPCountry when the buyer lands on the page.
      const country    = null;

      // Skill slug: look up from payment link's short URL, then fall back to notes
      let skillSlug = notes.skill_slug ?? null;
      if (!skillSlug) {
        const plinkShortUrl = payload.payment_link?.entity?.short_url ?? '';
        const shortCode = plinkShortUrl.split('/').pop();
        skillSlug = RZP_SHORT_TO_SKU[shortCode] ?? null;
      }

      // Look up bundle_key from skills table
      let bundleKey = null;
      if (skillSlug) {
        const { rows: skillRows } = await client.query(
          `SELECT bundle_key FROM skills WHERE slug = $1`, [skillSlug]
        );
        bundleKey = skillRows[0]?.bundle_key ?? null;
      }

      // Use payment_id as order_id for payment links (they have no order_id)
      const orderId = payment.order_id || payment.payment_link_id || payment.id;

      // Check if already recorded (avoid double-write from webhook + verify-payment)
      const { rows: existing } = await client.query(
        `SELECT id FROM orders WHERE razorpay_payment_id = $1`,
        [payment.id]
      );
      if (existing.length > 0) {
        // Already recorded by verify-payment — just ensure buyer_email is filled
        if (buyerEmail) {
          await client.query(
            `UPDATE orders SET buyer_email = $1, skill_slug = COALESCE(skill_slug, $2)
             WHERE razorpay_payment_id = $3 AND (buyer_email IS NULL OR buyer_email = '')`,
            [buyerEmail, skillSlug, payment.id]
          );
        }
      } else {
        // New order — write it fully
        if (buyerHash) {
          await client.query(
            `INSERT INTO buyers (buyer_hash, country, order_count, total_cents)
             VALUES ($1, $2, 1, $3)
             ON CONFLICT (buyer_hash) DO UPDATE
               SET order_count = buyers.order_count + 1,
                   total_cents = buyers.total_cents + $3`,
            [buyerHash, country, payment.amount]
          );
        }

        await client.query(
          `INSERT INTO orders
             (razorpay_order_id, razorpay_payment_id, buyer_hash, buyer_email,
              skill_slug, bundle_key, amount_cents, currency, status, country, paid_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'paid',$9,NOW())
           ON CONFLICT (razorpay_order_id) DO UPDATE
             SET razorpay_payment_id = EXCLUDED.razorpay_payment_id,
                 buyer_email = EXCLUDED.buyer_email,
                 skill_slug  = COALESCE(orders.skill_slug, EXCLUDED.skill_slug),
                 bundle_key  = COALESCE(orders.bundle_key, EXCLUDED.bundle_key),
                 status = 'paid', paid_at = NOW()`,
          [orderId, payment.id, buyerHash, buyerEmail, skillSlug, bundleKey,
           payment.amount, payment.currency, country]
        );

        // Add buyer to Brevo list 7 (NovaKit-Buyers)
        if (buyerEmail && env.BREVO_API_KEY) {
          fetch('https://api.brevo.com/v3/contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'api-key': env.BREVO_API_KEY },
            body: JSON.stringify({
              email: buyerEmail,
              listIds: [7],
              updateEnabled: true,
              attributes: { SOURCE: 'novakit_purchase', SKU: skillSlug || 'unknown' },
            }),
          }).catch(err => console.warn('[brevo] buyer sync failed:', err.message));
        }

        // Send delivery email to buyer
        if (buyerEmail && env.RESEND_API_KEY && skillSlug) {
          // Get file URLs from R2
          let fileUrls = [];
          try {
            const isBundle = skillSlug.endsWith('-bundle') || skillSlug === 'all-access';
            if (isBundle) {
              const { rows: bundleSkills } = await client.query(
                `SELECT slug FROM skills WHERE bundle_key = $1 AND category != 'Bundle'`,
                [skillSlug]
              );
              for (const s of bundleSkills) {
                const listed = await env.R2_BUCKET.list({ prefix: `skill/nk-${s.slug}-` });
                for (const obj of listed.objects) fileUrls.push(`https://assets.novakit.tech/${obj.key}`);
              }
            } else {
              const listed = await env.R2_BUCKET.list({ prefix: `skill/nk-${skillSlug}-` });
              for (const obj of listed.objects) fileUrls.push(`https://assets.novakit.tech/${obj.key}`);
            }
            if (!fileUrls.length) fileUrls = [`https://assets.novakit.tech/skill/nk-${skillSlug}.skill`];
          } catch (e) {
            console.warn('[webhook] R2 list error:', e.message);
            fileUrls = [`https://assets.novakit.tech/skill/nk-${skillSlug}.skill`];
          }

          const { rows: skillNameRows } = await client.query(
            `SELECT name FROM skills WHERE slug = $1`, [skillSlug]
          );
          const skillName = skillNameRows[0]?.name || skillSlug;
          const fileLinksHtml = fileUrls.map(u =>
            `<li><a href="${u}" style="color:#DE7356;">${u.split('/').pop()}</a></li>`
          ).join('');

          fetch('https://api.resend.com/emails', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${env.RESEND_API_KEY}` },
            body: JSON.stringify({
              from: 'NovaKit <support@novakit.tech>',
              to: buyerEmail,
              subject: `Your NovaKit skill — ${skillName}`,
              html: `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f7f6f2;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f6f2;padding:40px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.08);">
      <tr><td style="background:#0d0d0b;padding:24px 40px;">
        <img src="https://novakit.tech/assets/nkwhite.jpg" alt="NovaKit" height="28" style="display:block;border:0;">
      </td></tr>
      <tr><td style="padding:40px;">
        <p style="margin:0 0 8px;font-size:12px;color:#8a8980;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Your purchase</p>
        <h1 style="margin:0 0 16px;font-size:26px;font-weight:800;color:#111110;letter-spacing:-0.02em;">${skillName}</h1>
        <p style="margin:0 0 28px;font-size:15px;color:#545249;line-height:1.6;">Thanks for your purchase! Download your skill file below and upload it once to Claude — you can use it any time after that.</p>
        <ul style="margin:0 0 32px;padding:0;list-style:none;">${fileLinksHtml}</ul>
        <div style="background:#f7f6f2;border-radius:12px;padding:28px;margin:0 0 24px;">
          <p style="margin:0 0 12px;font-size:12px;font-weight:700;color:#111110;text-transform:uppercase;letter-spacing:0.08em;">Install in 3 steps</p>
          <p style="margin:0 0 8px;font-size:14px;color:#545249;">1. Open Claude → Customize → Skills → + → Upload a skill</p>
          <p style="margin:0 0 8px;font-size:14px;color:#545249;">2. Drop in the .skill file you downloaded</p>
          <p style="margin:0;font-size:14px;color:#545249;">3. Type / in any Claude chat and select the skill</p>
        </div>
        <p style="margin:0;font-size:13px;color:#8a8980;">Questions? Reply to this email or contact <a href="mailto:support@novakit.tech" style="color:#DE7356;">support@novakit.tech</a>. 7-day refund, no questions asked.</p>
      </td></tr>
      <tr><td style="padding:20px 40px;border-top:1px solid #eeecea;">
        <p style="margin:0;font-size:12px;color:#9a9890;text-align:center;">© 2026 NovaKit · <a href="https://novakit.tech" style="color:#9a9890;">novakit.tech</a></p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>`,
            }),
          }).catch(err => console.warn('[deliver-email] webhook failed:', err.message));
        }

        // Notify seller
        if (env.RESEND_API_KEY) {
          const amountDisplay = '$' + (payment.amount / 100).toFixed(2);
          fetch('https://api.resend.com/emails', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${env.RESEND_API_KEY}` },
            body: JSON.stringify({
              from: 'NovaKit <support@novakit.tech>',
              to: ['support@novakit.tech'],
              subject: `💰 New sale — ${skillSlug || 'unknown'} (${amountDisplay})`,
              html: `<p>New NovaKit sale via webhook!</p>
                     <ul>
                       <li><strong>Skill:</strong> ${skillSlug || 'unknown'}</li>
                       <li><strong>Amount:</strong> ${amountDisplay}</li>
                       <li><strong>Buyer:</strong> ${buyerEmail || 'unknown'}</li>
                       <li><strong>Payment ID:</strong> ${payment.id}</li>
                       <li><strong>Time:</strong> ${new Date().toISOString()}</li>
                     </ul>`,
            }),
          }).catch(err => console.warn('[notify-seller] failed:', err.message));
        }
      }
    }

    if (eventName === 'payment.failed') {
      const payment = payload.payment.entity;
      await client.query(
        `INSERT INTO orders (razorpay_order_id, amount_cents, currency, status)
         VALUES ($1, $2, $3, 'failed')
         ON CONFLICT (razorpay_order_id) DO UPDATE SET status = 'failed'`,
        [payment.order_id, payment.amount, payment.currency]
      );
    }

    if (eventName === 'refund.created') {
      const refund = payload.refund.entity;
      await client.query(
        `UPDATE orders SET status = 'refunded'
         WHERE razorpay_payment_id = $1`,
        [refund.payment_id]
      );
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('[webhook]', err);
    return new Response('Internal error', { status: 500 });
  } finally {
    await client.end();
  }
}
