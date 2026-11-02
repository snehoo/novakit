// functions/api/download/[name].js
// GET /api/download/<display-name>?t=<signed token>   (see ../_files.js)
// Streams a .skill from the private R2 bucket after checking the signature,
// the expiry, and that the order is still paid. <display-name> is cosmetic:
// the file served is the one named inside the signed token.

import { getClient } from '../../_db.js';
import { readToken, displayName } from '../_files.js';

const deny = (status, msg) => new Response(msg, {
  status, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' },
});

export async function onRequestGet({ request, env }) {
  const t = new URL(request.url).searchParams.get('t');
  const tok = await readToken(env, t);
  if (!tok) return deny(403, 'This download link is invalid or has expired. Email support@novakit.tech and we will send a fresh one.');
  if (!tok.k.startsWith('skill/')) return deny(403, 'Not a downloadable file.');

  if (tok.o !== 'free') {
    const client = await getClient(env);
    try {
      const { rows } = await client.query(
        `SELECT 1 FROM orders
          WHERE (razorpay_payment_id = $1 OR razorpay_order_id = $1)
            AND status = 'paid' LIMIT 1`, [tok.o]);
      if (!rows.length) return deny(403, 'This order is not active. Email support@novakit.tech if you think this is wrong.');
    } finally {
      await client.end();
    }
  }

  const obj = await env.R2_BUCKET.get(tok.k);
  if (!obj) return deny(404, 'File not found. Email support@novakit.tech and we will sort it out.');
  return new Response(obj.body, {
    headers: {
      'Content-Type': 'application/octet-stream',
      'Content-Disposition': `attachment; filename="${displayName(tok.k).replace(/"/g, '')}"`,
      'Cache-Control': 'private, no-store',
    },
  });
}
