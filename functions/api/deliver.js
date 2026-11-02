// functions/api/deliver.js
// POST /api/deliver   Body: { razorpayOrderId, buyerEmail }
//
// Re-issues signed download links for a paid order, e.g. for a past buyer
// whose old public link stopped working when the bucket went private. The
// buyer's email must match the one on the order -- an order with no email on
// record is refused rather than handed to whoever knows its id.
//
// Returns { skillName, fileUrls, isBundle }.

import { getClient, sha256 } from '../_db.js';
import { signedUrlsForOrder } from './_files.js';
import { limited, tooMany } from './_ratelimit.js';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
const json = (o, status = 200) => new Response(JSON.stringify(o), {
  status, headers: { 'Content-Type': 'application/json', ...CORS },
});

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

export async function onRequestPost({ request, env }) {
  if (await limited(env, request, 'feedback')) return tooMany(CORS);
  let body;
  try { body = await request.json(); } catch { return json({ error: 'Bad JSON' }, 400); }
  const { razorpayOrderId, buyerEmail } = body || {};
  if (!razorpayOrderId || !buyerEmail) return json({ error: 'Missing order id or email' }, 400);

  const client = await getClient(env);
  try {
    const { rows } = await client.query(
      `SELECT o.skill_slug, o.buyer_hash, o.razorpay_payment_id, s.name AS skill_name
         FROM orders o JOIN skills s ON s.slug = o.skill_slug
        WHERE (o.razorpay_order_id = $1 OR o.razorpay_payment_id = $1)
          AND o.status = 'paid' LIMIT 1`, [razorpayOrderId]);
    const order = rows[0];
    if (!order || !order.buyer_hash || order.buyer_hash !== await sha256(buyerEmail)) {
      // One answer for "no such order" and "wrong email": either would let
      // someone probe which order ids exist.
      return json({ error: 'No paid order matches that id and email.' }, 404);
    }
    const ref = order.razorpay_payment_id || razorpayOrderId;
    const fileUrls = await signedUrlsForOrder(env, client, ref, order.skill_slug);
    return json({
      skillName: order.skill_name,
      fileUrls,
      isBundle: order.skill_slug.endsWith('-bundle') || order.skill_slug === 'all-access',
    });
  } catch (err) {
    console.error('[deliver]', err);
    return json({ error: 'Could not prepare your downloads — please try again.' }, 500);
  } finally {
    await client.end();
  }
}
