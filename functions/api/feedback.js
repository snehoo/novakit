// functions/api/feedback.js
// GET  /api/feedback?o={orderId}&t={token}              → returns { skillName, alreadySubmitted }
// POST /api/feedback  Body: { orderId, token, rating, worked, comment, source }
//
// Token is stateless: HMAC-SHA256(FEEDBACK_SECRET, orderId) truncated to 32 hex chars.
// Required env: FEEDBACK_SECRET

import { getClient } from '../_db.js';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

// ── token helpers ────────────────────────────────────────────────────────────
async function makeToken(secret, orderId) {
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(orderId));
  return Array.from(new Uint8Array(sig))
    .slice(0, 16)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

async function verifyToken(secret, orderId, token) {
  if (!secret || !orderId || !token) return false;
  const expected = await makeToken(secret, orderId);
  // constant-time compare
  if (expected.length !== token.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= expected.charCodeAt(i) ^ token.charCodeAt(i);
  return diff === 0;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS },
  });
}

// ── GET — validate + pre-fill ───────────────────────────────────────────────
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const orderId = url.searchParams.get('o');
  const token   = url.searchParams.get('t');

  if (!(await verifyToken(env.FEEDBACK_SECRET, orderId, token))) {
    return json({ error: 'Invalid or expired link' }, 403);
  }

  const client = await getClient(env);
  try {
    const { rows } = await client.query(
      `SELECT o.id, o.skill_slug, s.name AS skill_name,
              EXISTS(SELECT 1 FROM feedback f WHERE f.order_id = o.id) AS already_submitted
       FROM orders o
       JOIN skills s ON s.slug = o.skill_slug
       WHERE o.id = $1 AND o.status = 'paid'
       LIMIT 1`,
      [orderId]
    );

    if (!rows.length) return json({ error: 'Order not found' }, 404);

    return json({
      ok: true,
      skillName: rows[0].skill_name,
      skillSlug: rows[0].skill_slug,
      alreadySubmitted: rows[0].already_submitted,
    });
  } catch (err) {
    console.error('[feedback GET]', err);
    return json({ error: err.message }, 500);
  } finally {
    await client.end();
  }
}

// ── POST — upsert feedback ──────────────────────────────────────────────────
export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch { return json({ error: 'Bad JSON' }, 400); }

  const { orderId, token, rating, worked, comment, source } = body;

  if (!(await verifyToken(env.FEEDBACK_SECRET, orderId, token))) {
    return json({ error: 'Invalid or expired link' }, 403);
  }

  const r = parseInt(rating, 10);
  if (!Number.isInteger(r) || r < 1 || r > 5) {
    return json({ error: 'Rating must be 1-5' }, 400);
  }

  const workedBool = (worked === true || worked === 'yes' || worked === 'true') ? true
                   : (worked === false || worked === 'no' || worked === 'false') ? false
                   : null;

  const cleanComment = (comment || '').toString().slice(0, 2000).trim() || null;
  const cleanSource  = ['day2', 'day7'].includes(source) ? source : null;

  const client = await getClient(env);
  try {
    // confirm order exists + paid + grab skill_slug + buyer_hash
    const { rows: orderRows } = await client.query(
      `SELECT id, skill_slug, buyer_hash FROM orders WHERE id = $1 AND status = 'paid' LIMIT 1`,
      [orderId]
    );
    if (!orderRows.length) return json({ error: 'Order not found' }, 404);
    const order = orderRows[0];

    await client.query(
      `INSERT INTO feedback (order_id, skill_slug, buyer_hash, rating, worked, comment, source)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       ON CONFLICT (order_id) DO UPDATE
         SET rating     = EXCLUDED.rating,
             worked     = EXCLUDED.worked,
             comment    = EXCLUDED.comment,
             source     = EXCLUDED.source,
             updated_at = NOW()`,
      [order.id, order.skill_slug, order.buyer_hash, r, workedBool, cleanComment, cleanSource]
    );

    return json({ ok: true });
  } catch (err) {
    console.error('[feedback POST]', err);
    return json({ error: err.message }, 500);
  } finally {
    await client.end();
  }
}
