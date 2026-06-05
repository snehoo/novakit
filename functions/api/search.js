// functions/api/search.js
// GET /api/search?q=cold+email&session=abc123
// Searches skills by name, category, bundle_key.
// Logs query + result count to search_queries table.

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
    return new Response(JSON.stringify({ results: [], query: q, count: 0 }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  const client = await getClient(env);
  try {
    const { rows } = await client.query(`
      SELECT slug, name, category, price_cents, bundle_key
      FROM skills
      WHERE category != 'Bundle'
        AND (
          LOWER(name)       ILIKE $1
          OR LOWER(category) ILIKE $1
          OR LOWER(bundle_key) ILIKE $1
        )
      ORDER BY
        CASE WHEN LOWER(name) ILIKE $1 THEN 0 ELSE 1 END,
        price_cents DESC
      LIMIT 20
    `, [`%${q}%`]);

    const resultCount = rows.length;

    // Log — upsert on query text (unique index)
    await client.query(`
      INSERT INTO search_queries (query, result_count, session_id, searched_at)
      VALUES ($1, $2, $3, NOW())
      ON CONFLICT (query) DO UPDATE
        SET result_count = EXCLUDED.result_count,
            searched_at  = NOW()
    `, [q, resultCount, session]);

    return new Response(JSON.stringify({
      results: rows,
      query: q,
      count: resultCount,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...CORS }
    });

  } catch (err) {
    console.error('[search]', err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  } finally {
    await client.end();
  }
}
