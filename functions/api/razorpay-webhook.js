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

async function verifyRazorpaySignature(rawBody, signature, secret) {
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
      const order   = payload.order?.entity;

      // Extract metadata Razorpay passes through from your order creation call
      // You need to set these when creating the order on your frontend:
      //   notes: { skill_slug: 'video-script-engine', bundle_key: null, buyer_email: 'user@example.com' }
      const notes      = payment.notes ?? {};
      const skillSlug  = notes.skill_slug  ?? null;
      const bundleKey  = notes.bundle_key  ?? null;
      const buyerEmail = notes.buyer_email ?? null;
      const buyerHash  = buyerEmail ? await sha256(buyerEmail) : null;
      const country    = payment.international ? 'international' : 'IN';

      // Upsert buyer record
      if (buyerHash) {
        await client.query(
          `INSERT INTO buyers (buyer_hash, country)
           VALUES ($1, $2)
           ON CONFLICT (buyer_hash) DO UPDATE
             SET order_count = buyers.order_count + 1,
                 total_cents = buyers.total_cents + $3`,
          [buyerHash, country, payment.amount]
        );
      }

      // Insert order
      await client.query(
        `INSERT INTO orders
           (razorpay_order_id, razorpay_payment_id, buyer_hash,
            skill_slug, bundle_key, amount_cents, currency, status, country, paid_at)
         VALUES ($1,$2,$3,$4,$5,$6,$7,'paid',$8,NOW())
         ON CONFLICT (razorpay_order_id) DO UPDATE
           SET razorpay_payment_id = EXCLUDED.razorpay_payment_id,
               status = 'paid',
               paid_at = NOW()`,
        [
          payment.order_id,
          payment.id,
          buyerHash,
          skillSlug,
          bundleKey,
          payment.amount,
          payment.currency,
          country,
        ]
      );
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
