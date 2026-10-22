// functions/api/_internal.js
// Shared guard for server-to-server calls between our own Pages Functions
// (webhook / verify-payment / cron -> send-email*). The token is derived from
// METRICS_SECRET, so no new secret is needed. Fails closed when it is unset.

async function hmacHex(secret, msg) {
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const s = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(msg));
  return Array.from(new Uint8Array(s)).map(b => b.toString(16).padStart(2, '0')).join('');
}

// Constant-time string compare (both inputs are hex of equal length when valid).
export function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

export async function internalToken(env) {
  if (!env.METRICS_SECRET) return null;
  return hmacHex(env.METRICS_SECRET, 'internal-email-v1');
}

export async function isInternal(request, env) {
  const t = await internalToken(env);
  if (!t) return false;
  return safeEqual(request.headers.get('x-internal-auth') || '', t);
}

export async function internalHeaders(env) {
  return { 'Content-Type': 'application/json', 'x-internal-auth': (await internalToken(env)) || '' };
}
