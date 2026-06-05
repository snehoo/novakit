// functions/api/admin-feedback.js
// GET /api/admin-feedback?range=30d
// Header: x-metrics-secret: {METRICS_SECRET}
//
// Returns:
// {
//   summary: { total, avg_rating, worked_yes_pct, last_7d },
//   bySkill: [{ skill_slug, skill_name, count, avg_rating }, ...],
//   recent:  [{ created_at, skill_name, rating, worked, comment, source }, ...]
// }

import { getClient } from '../_db.js';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, x-metrics-secret',
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { 'Content-Type': 'application/json', ...CORS }
  });
}

const RANGE_DAYS = { '7d': 7, '30d': 30, '90d': 90, 'all': 3650 };

export async function onRequestGet({ request, env }) {
  // auth — same secret as /api/metrics
  const supplied = request.headers.get('x-metrics-secret');
  if (!env.METRICS_SECRET || supplied !== env.METRICS_SECRET) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const url = new URL(request.url);
  const range = url.searchParams.get('range') || '30d';
  const days = RANGE_DAYS[range] || 30;

  const client = await getClient(env);
  try {
    // Summary
    const { rows: sumRows } = await client.query(`
      SELECT
        COUNT(*)::int                                            AS total,
        ROUND(AVG(rating)::numeric, 2)::float                    AS avg_rating,
        ROUND(100.0 * SUM(CASE WHEN worked THEN 1 ELSE 0 END)::numeric
              / NULLIF(SUM(CASE WHEN worked IS NOT NULL THEN 1 ELSE 0 END),0), 1)::float AS worked_yes_pct,
        SUM(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 ELSE 0 END)::int AS last_7d
      FROM feedback
      WHERE created_at >= NOW() - ($1 || ' days')::interval
    `, [days]);

    // By skill
    const { rows: bySkill } = await client.query(`
      SELECT f.skill_slug,
             s.name AS skill_name,
             COUNT(*)::int                          AS count,
             ROUND(AVG(f.rating)::numeric, 2)::float AS avg_rating,
             SUM(CASE WHEN f.worked THEN 1 ELSE 0 END)::int AS worked_yes
      FROM feedback f
      JOIN skills s ON s.slug = f.skill_slug
      WHERE f.created_at >= NOW() - ($1 || ' days')::interval
      GROUP BY f.skill_slug, s.name
      ORDER BY count DESC, avg_rating DESC
    `, [days]);

    // Recent entries (cap 100)
    const { rows: recent } = await client.query(`
      SELECT f.created_at, f.skill_slug, s.name AS skill_name,
             f.rating, f.worked, f.comment, f.source
      FROM feedback f
      JOIN skills s ON s.slug = f.skill_slug
      WHERE f.created_at >= NOW() - ($1 || ' days')::interval
      ORDER BY f.created_at DESC
      LIMIT 100
    `, [days]);

    return json({
      summary: sumRows[0] || { total: 0, avg_rating: null, worked_yes_pct: null, last_7d: 0 },
      bySkill,
      recent,
    });
  } catch (err) {
    console.error('[admin-feedback]', err);
    return json({ error: err.message }, 500);
  } finally {
    await client.end();
  }
}
