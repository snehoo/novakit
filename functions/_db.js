// functions/_db.js
// Shared helper — import this in every Pages Function that needs DB access.

import pg from 'pg';
const { Client } = pg;

/**
 * Returns a connected pg Client using Hyperdrive's connection string.
 * Always call client.end() in a finally block.
 *
 * @param {object} env - The Pages Function env object (has env.HYPERDRIVE)
 */
export async function getClient(env) {
  const client = new Client({
    connectionString: env.HYPERDRIVE.connectionString,
  });
  await client.connect();
  return client;
}

/**
 * Hash a string (email) to a hex SHA-256.
 * Used to anonymise buyer identity — we never store raw emails.
 */
export async function sha256(text) {
  const buf = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(text.toLowerCase().trim())
  );
  return Array.from(new Uint8Array(buf))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Classify a referrer URL into a traffic source bucket.
 */
export function classifySource(referrer) {
  if (!referrer) return 'direct';
  const r = referrer.toLowerCase();
  if (r.includes('google') || r.includes('bing') || r.includes('duckduckgo')) return 'organic';
  if (r.includes('twitter') || r.includes('x.com') || r.includes('instagram') ||
      r.includes('linkedin') || r.includes('facebook') || r.includes('youtube')) return 'social';
  if (r.includes('mail') || r.includes('substack') || r.includes('beehiiv')) return 'email';
  return 'referral';
}
