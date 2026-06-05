// functions/api/search.js
// GET /api/search?q=cold+email&session=abc123
// Logs search queries to search_queries table.
// Actual filtering happens client-side — this is analytics only.

import { getClient } from '../_db.js';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const q = (url.searchParams.get('q') || '').trim().toLowerCase();
  const session = url.searchParams.get('session') || null;

  if (!q || q.length < 2) {
    return new Response(JSON.stringify({ ok: true }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  const client = await getClient(env);
  try {
    // Simple insert — no conflict handling since query has no unique constraint
    await client.query(`
      INSERT INTO search_queries (query, result_count, session_id, searched_at)
      VALUES ($1, 0, $2, NOW())
    `, [q, session]);

    return new Response(JSON.stringify({ ok: true }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
    });

  } catch (err) {
    console.error('[search]', err);
    // Never surface a logging failure to the user
    return new Response(JSON.stringify({ ok: true }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  } finally {
    await client.end();
  }
}
