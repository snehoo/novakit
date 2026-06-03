// functions/api/verify-payment.js
// POST /api/verify-payment
// Body: { paymentId, sku, signature, paymentLinkId, paymentLinkStatus }
//
// 1. Verifies Razorpay signature
// 2. Fetches payment details from Razorpay API (gets buyer email)
// 3. Creates/upserts order in DB
// 4. Returns { skillName, fileUrls, email, orderId }

import { getClient, sha256 } from '../_db.js';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

function razorpayAuth(env) {
  return 'Basic ' + btoa(`${env.RAZORPAY_KEY_ID}:${env.RAZORPAY_KEY_SECRET}`);
}

async function verifySignature(env, paymentLinkId, paymentLinkRefId, paymentLinkStatus, paymentId, signature) {
  // Razorpay payment link signature: payment_link_id|payment_link_reference_id|payment_link_status|razorpay_payment_id
  const payload = `${paymentLinkId}|${paymentLinkRefId}|${paymentLinkStatus}|${paymentId}`;
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(env.RAZORPAY_KEY_SECRET),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payload));
  const computed = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
  return computed === signature;
}

export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch {
    return new Response('Bad JSON', { status: 400, headers: CORS });
  }

  const { paymentId, sku, signature, paymentLinkId, paymentLinkRefId, paymentLinkStatus } = body;

  if (!paymentId || !sku) {
    return new Response(JSON.stringify({ error: 'Missing paymentId or sku' }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  // 1. Verify signature (skip if no payment link params — direct API payment)
  if (signature && paymentLinkId) {
    const valid = await verifySignature(env, paymentLinkId, paymentLinkRefId || '', paymentLinkStatus || 'paid', paymentId, signature);
    if (!valid) {
      return new Response(JSON.stringify({ error: 'Invalid signature' }), {
        status: 403, headers: { 'Content-Type': 'application/json', ...CORS }
      });
    }
  }

  // 2. Fetch payment from Razorpay API
  let payment;
  try {
    const res = await fetch(`https://api.razorpay.com/v1/payments/${paymentId}`, {
      headers: { 'Authorization': razorpayAuth(env) }
    });
    if (!res.ok) throw new Error('Razorpay API error: ' + res.status);
    payment = await res.json();
  } catch (err) {
    return new Response(JSON.stringify({ error: 'Could not fetch payment: ' + err.message }), {
      status: 502, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  // Check payment is captured
  if (payment.status !== 'captured') {
    return new Response(JSON.stringify({ error: 'Payment not captured', status: payment.status }), {
      status: 402, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  const buyerEmail = payment.email || payment.notes?.buyer_email || '';
  const buyerHash  = buyerEmail ? await sha256(buyerEmail) : null;
  const amountCents = payment.amount; // Razorpay stores in paise/cents
  const isBundle = sku.endsWith('-bundle');

  const client = await getClient(env);
  try {
    // 3. Look up skill
    const { rows: skillRows } = await client.query(
      `SELECT slug, name, category, price_cents, bundle_key FROM skills WHERE slug = $1`,
      [sku]
    );

    if (!skillRows.length) {
      return new Response(JSON.stringify({ error: 'Skill not found: ' + sku }), {
        status: 404, headers: { 'Content-Type': 'application/json', ...CORS }
      });
    }

    const skill = skillRows[0];

    // 4. Upsert buyer
    if (buyerHash) {
      await client.query(
        `INSERT INTO buyers (buyer_hash)
         VALUES ($1)
         ON CONFLICT (buyer_hash) DO UPDATE
           SET order_count = buyers.order_count + 1,
               total_cents = buyers.total_cents + $2`,
        [buyerHash, amountCents]
      );
    }

    // 5. Upsert order (use payment ID as unique key since no order ID from payment links)
    await client.query(
      `INSERT INTO orders
         (razorpay_order_id, razorpay_payment_id, buyer_hash, buyer_email,
          skill_slug, bundle_key, amount_cents, currency, status, paid_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, 'USD', 'paid', NOW())
       ON CONFLICT (razorpay_order_id) DO UPDATE
         SET razorpay_payment_id = EXCLUDED.razorpay_payment_id,
             buyer_email = EXCLUDED.buyer_email,
             status = 'paid',
             paid_at = NOW()`,
      [
        paymentId,       // use payment ID as order ID for payment links
        paymentId,
        buyerHash,
        buyerEmail,
        sku,
        skill.bundle_key,
        amountCents,
      ]
    );

    // 6. Get order ID for download tracking
    const { rows: orderRows } = await client.query(
      `SELECT id FROM orders WHERE razorpay_payment_id = $1`,
      [paymentId]
    );
    const orderId = orderRows[0]?.id;

    // 7. Get file URLs for this skill/bundle
    let fileUrls = [];

    if (isBundle) {
      // Get all skills in this bundle
      const { rows: bundleSkills } = await client.query(
        `SELECT slug FROM skills WHERE bundle_key = $1 AND category != 'Bundle'`,
        [sku]
      );
      for (const s of bundleSkills) {
        const listed = await env.R2_BUCKET.list({ prefix: `skill/nk-${s.slug}-` });
        for (const obj of listed.objects) {
          fileUrls.push(`https://assets.novakit.tech/${obj.key}`);
        }
      }
    } else {
      const listed = await env.R2_BUCKET.list({ prefix: `skill/nk-${sku}-` });
      for (const obj of listed.objects) {
        fileUrls.push(`https://assets.novakit.tech/${obj.key}`);
      }
    }

    // Fallback: use fileUrl from products data pattern if R2 list returns nothing
    if (!fileUrls.length) {
      fileUrls = [`https://assets.novakit.tech/skill/nk-${sku}.skill`];
    }

    return new Response(JSON.stringify({
      ok: true,
      skillName: skill.name,
      skillSlug: sku,
      isBundle,
      bundleKey: skill.bundle_key,
      fileUrls,
      email: buyerEmail,
      orderId: orderId || paymentId,
      paymentId,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...CORS }
    });

  } catch (err) {
    console.error('[verify-payment]', err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  } finally {
    await client.end();
  }
}
