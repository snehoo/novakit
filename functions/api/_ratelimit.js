// functions/api/_ratelimit.js
// Per-IP limits for the public form endpoints. Postgres-backed (Hyperdrive),
// one upsert per request, keyed on a hash of the IP -- raw IPs are not kept.
//
// Fails OPEN: if the table is missing (migration not run) or the DB errors,
// the request proceeds. This guards against abuse (email bombing through
// free-skill, list stuffing through subscribe); it is not an auth check, and
// taking the forms down with the database would be the worse failure.

import { sha256 } from '../_db.js';

// Requests allowed per window, per IP, per endpoint.
export const LIMITS = {
  'free-skill': { max: 5,   windowMin: 60 },  // each call sends an email
  'subscribe':  { max: 5,   windowMin: 60 },
  'feedback':   { max: 10,  windowMin: 60 },
  'track':      { max: 120, windowMin: 1 },   // page events; generous
};

export async function overLimit(client, request, endpoint) {
  const rule = LIMITS[endpoint];
  if (!rule) return false;
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  try {
    const key = endpoint + ':' + (await sha256(ip)).slice(0, 32);
    const { rows } = await client.query(
      `WITH up AS (
         INSERT INTO rate_limits (key, bucket, n)
         VALUES ($1, date_trunc('minute', now()), 1)
         ON CONFLICT (key, bucket) DO UPDATE SET n = rate_limits.n + 1
         RETURNING 1)
       SELECT coalesce(sum(n), 0)::int + 1 AS total FROM rate_limits
        WHERE key = $1 AND bucket > now() - make_interval(mins => $2)`,
      [key, rule.windowMin]);
    if (Math.random() < 0.01) {
      client.query(`DELETE FROM rate_limits WHERE bucket < now() - interval '1 day'`)
        .catch(() => {});
    }
    return (rows[0]?.total || 0) > rule.max;
  } catch (err) {
    console.warn('[ratelimit] skipped:', err.message);
    return false;
  }
}

export function tooMany(headers = {}) {
  return new Response(JSON.stringify({ error: 'Too many requests — try again later.' }), {
    status: 429, headers: { 'Content-Type': 'application/json', 'Retry-After': '600', ...headers },
  });
}

// For endpoints that do not otherwise open a DB connection.
export async function limited(env, request, endpoint) {
  let client;
  try {
    const { getClient } = await import('../_db.js');
    client = await getClient(env);
    return await overLimit(client, request, endpoint);
  } catch (err) {
    console.warn('[ratelimit] skipped:', err.message);
    return false;
  } finally {
    if (client) client.end().catch(() => {});
  }
}
