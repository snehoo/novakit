// functions/api/_files.js
// Paid .skill files live in R2 and are served only through /api/download,
// with a signed link tied to an order. The bucket itself is private: the old
// public https://assets.novakit.tech/skill/... URLs were listed in a public
// script, so anyone could download every paid file.
//
// A link is  /api/download/<display-name>?t=<payload>.<hmac>
//   payload = base64url(JSON {o: order ref | "free", k: R2 key, e: expiry})
// The HMAC key is derived from METRICS_SECRET, like _internal.js, so no new
// secret is needed. Every download re-checks the order is still 'paid', so a
// refund also ends access.

import { safeEqual } from './_internal.js';

const BASE = 'https://novakit.tech/api/download/';
const TTL_DAYS = 365;

function b64url(s) {
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function unb64url(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  return atob(s + '='.repeat((4 - s.length % 4) % 4));
}
async function hmacHex(secret, msg) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(msg));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}
async function signingKey(env) {
  if (!env.METRICS_SECRET) throw new Error('METRICS_SECRET not set');
  return hmacHex(env.METRICS_SECRET, 'download-v1');
}

// "skill/nk-business-plan-278041.skill" -> "business-plan.skill"
export function displayName(key) {
  return key.split('/').pop().replace(/^nk-/, '').replace(/-[a-f0-9]{4,}(\.skill)$/, '$1');
}

export async function signedUrl(env, orderRef, key, ttlDays = TTL_DAYS) {
  const payload = b64url(JSON.stringify({
    o: String(orderRef), k: key, e: Math.floor(Date.now() / 1000) + ttlDays * 86400,
  }));
  const sig = await hmacHex(await signingKey(env), payload);
  return `${BASE}${encodeURIComponent(displayName(key))}?t=${payload}.${sig}`;
}

// {o, k, e} or null.
export async function readToken(env, token) {
  const [payload, sig] = String(token || '').split('.');
  if (!payload || !sig) return null;
  let expected;
  try { expected = await hmacHex(await signingKey(env), payload); } catch { return null; }
  if (!safeEqual(sig, expected)) return null;
  try {
    const d = JSON.parse(unb64url(payload));
    if (!d.o || !d.k || !d.e || d.e < Date.now() / 1000) return null;
    return d;
  } catch { return null; }
}

// R2 keys for a sku, or for every skill in a bundle. `client` is a pg client.
export async function keysForSku(env, client, sku) {
  const isBundle = sku.endsWith('-bundle') || sku === 'all-access';
  let slugs = [sku];
  if (isBundle) {
    const { rows } = await client.query(
      `SELECT slug FROM skills WHERE bundle_key = $1 AND category != 'Bundle'`, [sku]);
    slugs = rows.map(r => r.slug);
  }
  const keys = [];
  for (const s of slugs) {
    const listed = await env.R2_BUCKET.list({ prefix: `skill/nk-${s}-` });
    for (const obj of listed.objects) keys.push(obj.key);
  }
  if (!keys.length && !isBundle) keys.push(`skill/nk-${sku}.skill`);
  return keys;
}

export async function signedUrlsForOrder(env, client, orderRef, sku) {
  const keys = await keysForSku(env, client, sku);
  return Promise.all(keys.map(k => signedUrl(env, orderRef, k)));
}
