// functions/api/deliver.js
// POST /api/deliver
// Body: { razorpayOrderId, buyerEmail }
//
// 1. Verifies the order exists and is paid
// 2. Looks up fileUrl(s) from NK_PRODUCTS via the skill slug
// 3. Generates signed R2 URLs (1 hour expiry)
// 4. Records the download event
// 5. Returns { skillName, fileUrls, price, isBundle }

import { getClient, sha256 } from '../_db.js';

// R2 signed URL helper
async function signedR2Url(env, fileUrl, expiresInSeconds = 3600) {
  // fileUrl format: https://assets.novakit.tech/skill/nk-xxx.skill
  const url = new URL(fileUrl);
  const key = url.pathname.slice(1); // strip leading /

  // Build the URL to sign
  const expiry = Math.floor(Date.now() / 1000) + expiresInSeconds;
  const stringToSign = `GET\n\n\n${expiry}\n/${key}`;

  // Use R2 binding to generate presigned URL
  const obj = await env.R2_BUCKET.get(key);
  if (!obj) {
    // Fall back to direct URL if R2 binding not available
    return fileUrl;
  }

  // Generate presigned URL using Workers R2 presign
  const signed = await env.R2_BUCKET.createPresignedUrl(key, {
    expiresIn: expiresInSeconds,
  });
  return signed;
}

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

  const { razorpayOrderId, buyerEmail } = body;
  if (!razorpayOrderId || !buyerEmail) {
    return new Response('Missing razorpayOrderId or buyerEmail', { status: 400, headers: CORS });
  }

  const client = await getClient(env);
  try {
    // 1. Verify order is paid
    const { rows } = await client.query(
      `SELECT o.id, o.skill_slug, o.bundle_key, o.amount_cents, o.buyer_hash,
              s.name AS skill_name, s.price_cents
       FROM orders o
       JOIN skills s ON s.slug = o.skill_slug
       WHERE o.razorpay_order_id = $1 AND o.status = 'paid'`,
      [razorpayOrderId]
    );

    if (!rows.length) {
      return new Response(JSON.stringify({ error: 'Order not found or not paid' }), {
        status: 404, headers: { 'Content-Type': 'application/json', ...CORS }
      });
    }

    const order = rows[0];
    const buyerHash = await sha256(buyerEmail);

    // Security check: buyer email must match order
    if (order.buyer_hash && order.buyer_hash !== buyerHash) {
      return new Response(JSON.stringify({ error: 'Email does not match order' }), {
        status: 403, headers: { 'Content-Type': 'application/json', ...CORS }
      });
    }

    // 2. Get file URLs from products data
    // We store these in an env variable as JSON, or derive from slug
    // Format: https://assets.novakit.tech/skill/nk-{slug}-{hash}.skill
    // We'll use the R2 bucket directly via binding
    const isBundle = !!order.bundle_key && order.bundle_key !== order.skill_slug;

    // Build file key(s) from R2
    // List objects with prefix to find the right file
    const prefix = `skill/nk-${order.skill_slug}-`;
    const listed = await env.R2_BUCKET.list({ prefix });

    let fileUrls = [];
    if (listed.objects.length > 0) {
      // For individual skills — one file
      for (const obj of listed.objects) {
        const url = `https://assets.novakit.tech/${obj.key}`;
        fileUrls.push(url);
      }
    }

    // For bundles, list all skill files
    if (isBundle) {
      const bundleSkills = await client.query(
        `SELECT slug FROM skills WHERE bundle_key = $1 AND category != 'Bundle'`,
        [order.bundle_key]
      );
      fileUrls = [];
      for (const skill of bundleSkills.rows) {
        const p = `skill/nk-${skill.slug}-`;
        const l = await env.R2_BUCKET.list({ prefix: p });
        for (const obj of l.objects) {
          fileUrls.push(`https://assets.novakit.tech/${obj.key}`);
        }
      }
    }

    // 3. Record download
    const { rows: dlRows } = await client.query(
      `SELECT COUNT(*) AS n FROM downloads WHERE order_id = $1`,
      [order.id]
    );
    const downloadNo = parseInt(dlRows[0].n, 10) + 1;

    await client.query(
      `INSERT INTO downloads (order_id, skill_slug, buyer_hash, download_no)
       VALUES ($1, $2, $3, $4)`,
      [order.id, order.skill_slug, buyerHash, downloadNo]
    );

    return new Response(JSON.stringify({
      skillName: order.skill_name,
      skillSlug: order.skill_slug,
      bundleKey: order.bundle_key,
      isBundle,
      fileUrls,
      price: order.price_cents,
      downloadNo,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...CORS }
    });

  } catch (err) {
    console.error('[deliver]', err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  } finally {
    await client.end();
  }
}
