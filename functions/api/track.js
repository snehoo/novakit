// functions/api/track.js
// POST /api/track
//
// Called from your frontend JS for three event types:
//   { type: 'pageview', skillSlug: 'video-script-engine', sessionId: '...', referrer: '...' }
//   { type: 'download', skillSlug: 'video-script-engine', orderId: '...', buyerHash: '...' }
//   { type: 'search',   query: 'instagram caption', resultCount: 0, sessionId: '...' }

import { getClient, classifySource } from '../_db.js';

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
  try {
    body = await request.json();
  } catch {
    return new Response('Bad JSON', { status: 400, headers: CORS });
  }

  const client = await getClient(env);
  try {
    switch (body.type) {

      case 'pageview': {
        const source = classifySource(body.referrer ?? '');
        await client.query(
          `INSERT INTO page_views (skill_slug, session_id, referrer, source)
           VALUES ($1, $2, $3, $4)`,
          [body.skillSlug ?? null, body.sessionId, body.referrer ?? null, source]
        );
        break;
      }

      case 'download': {
        // Count how many times this buyer has downloaded this skill before
        const { rows } = await client.query(
          `SELECT COUNT(*) AS n FROM downloads
           WHERE skill_slug = $1 AND buyer_hash = $2`,
          [body.skillSlug, body.buyerHash]
        );
        const downloadNo = parseInt(rows[0].n, 10) + 1;

        await client.query(
          `INSERT INTO downloads (order_id, skill_slug, buyer_hash, download_no)
           VALUES ($1, $2, $3, $4)`,
          [body.orderId ?? null, body.skillSlug, body.buyerHash, downloadNo]
        );
        break;
      }

      case 'search': {
        const normalised = (body.query ?? '').toLowerCase().trim().slice(0, 200);
        if (!normalised) break;
        await client.query(
          `INSERT INTO search_queries (query, result_count, session_id)
           VALUES ($1, $2, $3)`,
          [normalised, body.resultCount ?? 0, body.sessionId ?? null]
        );
        break;
      }

      case 'lead': {
        // Free skill signup — stored as a page_view with skill_slug='__free_lead__'
        // so it's queryable without a schema change
        const source = classifySource(body.referrer ?? '');
        await client.query(
          `INSERT INTO page_views (skill_slug, session_id, referrer, source)
           VALUES ('__free_lead__', $1, $2, $3)`,
          [body.sessionId, body.referrer ?? null, source]
        );
        break;
      }

      default:
        return new Response('Unknown type', { status: 400, headers: CORS });
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...CORS },
    });
  } catch (err) {
    console.error('[track]', err);
    return new Response('Internal error', { status: 500, headers: CORS });
  } finally {
    await client.end();
  }
}
