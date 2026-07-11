// functions/api/metrics.js
// GET /api/metrics?range=30d
//
// Returns all dashboard metrics in one call.
// Protect this endpoint! Add a secret header check or Cloudflare Access rule
// so only you can read it.

import { getClient } from '../_db.js';

const RANGES = {
  '7d':  '7 days',
  '30d': '30 days',
  '90d': '90 days',
  'all': '100 years',  // effectively all-time
};

export async function onRequestGet({ request, env }) {
  // Simple secret header protection — set METRICS_SECRET in wrangler.jsonc vars
  const secret = request.headers.get('x-metrics-secret');
  if (env.METRICS_SECRET && secret !== env.METRICS_SECRET) {
    return new Response('Forbidden', { status: 403 });
  }

  const url   = new URL(request.url);
  const range = url.searchParams.get('range') ?? '30d';
  const interval = RANGES[range] ?? '30 days';

  const client = await getClient(env);
  try {
    const [
      kpi,
      revenueByDay,
      downloadsByDay,
      topSkills,
      revenueByType,
      categoryRevenue,
      recentActivity,
      recentOrders,
      topSearches,
      missedSearches,
      funnelData,
      buyerGeo,
      entrySkills,
    ] = await Promise.all([

      // KPIs
      client.query(`
        SELECT
          COALESCE(SUM(amount_cents),0)                          AS total_paise,
          COUNT(*)                                               AS total_orders,
          COUNT(DISTINCT buyer_hash)                             AS unique_buyers,
          (SELECT COUNT(*) FROM downloads
           WHERE downloaded_at > NOW() - $1::interval)          AS total_downloads
        FROM orders
        WHERE status = 'paid'
          AND created_at > NOW() - $1::interval
      `, [interval]),

      // Revenue per day (last N days)
      client.query(`
        SELECT
          DATE_TRUNC('day', paid_at) AS day,
          SUM(amount_cents)          AS paise
        FROM orders
        WHERE status = 'paid'
          AND paid_at > NOW() - $1::interval
        GROUP BY 1
        ORDER BY 1
      `, [interval]),

      // Downloads per day
      client.query(`
        SELECT
          DATE_TRUNC('day', downloaded_at) AS day,
          COUNT(*)                          AS count
        FROM downloads
        WHERE downloaded_at > NOW() - $1::interval
        GROUP BY 1
        ORDER BY 1
      `, [interval]),

      // Top 15 skills by revenue
      client.query(`
        SELECT
          o.skill_slug,
          s.name,
          s.category,
          SUM(o.amount_cents)                                  AS total_paise,
          COUNT(*)                                             AS order_count,
          (SELECT COUNT(*) FROM downloads d WHERE d.skill_slug = o.skill_slug) AS download_count
        FROM orders o
        JOIN skills s ON s.slug = o.skill_slug
        WHERE o.status = 'paid'
          AND o.created_at > NOW() - $1::interval
        GROUP BY o.skill_slug, s.name, s.category
        ORDER BY total_paise DESC
        LIMIT 15
      `, [interval]),

      // Individual vs bundle split
      client.query(`
        SELECT
          CASE WHEN bundle_key IS NULL THEN 'individual' ELSE 'bundle' END AS type,
          SUM(amount_cents) AS paise
        FROM orders
        WHERE status = 'paid'
          AND created_at > NOW() - $1::interval
        GROUP BY 1
      `, [interval]),

      // Revenue by category
      client.query(`
        SELECT
          s.category,
          SUM(o.amount_cents) AS paise
        FROM orders o
        JOIN skills s ON s.slug = o.skill_slug
        WHERE o.status = 'paid'
          AND o.created_at > NOW() - $1::interval
        GROUP BY s.category
        ORDER BY paise DESC
        LIMIT 8
      `, [interval]),

      // Recent activity (last 20 events)
      client.query(`
        (SELECT 'order' AS type, o.skill_slug, s.name AS skill_name,
                o.buyer_hash, o.amount_cents, o.created_at AS ts
         FROM orders o JOIN skills s ON s.slug = o.skill_slug
         WHERE o.status = 'paid' ORDER BY o.created_at DESC LIMIT 10)
        UNION ALL
        (SELECT 'download' AS type, d.skill_slug, s.name AS skill_name,
                d.buyer_hash, NULL, d.downloaded_at AS ts
         FROM downloads d JOIN skills s ON s.slug = d.skill_slug
         ORDER BY d.downloaded_at DESC LIMIT 10)
        ORDER BY ts DESC LIMIT 20
      `),

      // Recent orders (for Orders tab)
      client.query(`
        SELECT
          o.id,
          o.razorpay_order_id,
          o.razorpay_payment_id,
          o.buyer_email,
          o.skill_slug,
          o.bundle_key,
          o.amount_cents,
          o.status,
          COALESCE(o.paid_at, o.created_at) AS paid_at,
          o.created_at,
          s.name AS skill_name
        FROM orders o
        LEFT JOIN skills s ON s.slug = o.skill_slug
        WHERE o.status = 'paid'
        ORDER BY COALESCE(o.paid_at, o.created_at) DESC NULLS LAST
        LIMIT 50
      `),

      // Top search terms
      client.query(`
        SELECT
          query,
          COUNT(*)                      AS searches,
          SUM(CASE WHEN result_count = 0 THEN 1 ELSE 0 END) AS misses,
          AVG(result_count)             AS avg_results
        FROM search_queries
        WHERE searched_at > NOW() - $1::interval
        GROUP BY query
        ORDER BY searches DESC
        LIMIT 20
      `, [interval]),

      // Missed searches (result_count = 0)
      client.query(`
        SELECT query, COUNT(*) AS searches
        FROM search_queries
        WHERE result_count = 0
          AND searched_at > NOW() - $1::interval
        GROUP BY query
        ORDER BY searches DESC
        LIMIT 10
      `, [interval]),

      // Funnel (page views → orders in same period)
      client.query(`
        SELECT
          COUNT(DISTINCT session_id)                                              AS visitors,
          COUNT(DISTINCT CASE WHEN skill_slug IS NOT NULL
                              AND skill_slug != '__free_lead__'
                         THEN session_id END)                                     AS skill_page_views,
          COUNT(DISTINCT CASE WHEN skill_slug = '__free_lead__'
                         THEN session_id END)                                     AS free_leads
        FROM page_views
        WHERE viewed_at > NOW() - $1::interval
      `, [interval]),

      // Buyer geography
      client.query(`
        SELECT country, COUNT(*) AS buyers
        FROM buyers
        GROUP BY country
        ORDER BY buyers DESC
        LIMIT 10
      `),

      // Entry-point skills (first purchase per buyer)
      client.query(`
        SELECT
          o.skill_slug,
          s.name,
          COUNT(*) AS first_purchases
        FROM orders o
        JOIN skills s ON s.slug = o.skill_slug
        WHERE o.status = 'paid'
          AND o.created_at = (
            SELECT MIN(o2.created_at)
            FROM orders o2
            WHERE o2.buyer_hash = o.buyer_hash AND o2.status = 'paid'
          )
        GROUP BY o.skill_slug, s.name
        ORDER BY first_purchases DESC
        LIMIT 8
      `),
    ]);

    // Repeat buyer rate
    const repeatResult = await client.query(`
      SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeats
      FROM buyers
    `);
    const { total, repeats } = repeatResult.rows[0];
    const repeatRate = total > 0 ? Math.round((repeats / total) * 100) : 0;

    const data = {
      range,
      kpi: {
        totalCents:    parseInt(kpi.rows[0].total_paise, 10),
        totalPaise:    parseInt(kpi.rows[0].total_paise, 10),
        totalOrders:   parseInt(kpi.rows[0].total_orders, 10),
        uniqueBuyers:  parseInt(kpi.rows[0].unique_buyers, 10),
        totalDownloads:parseInt(kpi.rows[0].total_downloads, 10),
        repeatRate,
      },
      revenueByDay:    revenueByDay.rows,
      downloadsByDay:  downloadsByDay.rows,
      topSkills:       topSkills.rows,
      revenueByType:   revenueByType.rows,
      categoryRevenue: categoryRevenue.rows,
      recentActivity:  recentActivity.rows,
      recentOrders:    recentOrders.rows,
      topSearches:     topSearches.rows,
      missedSearches:  missedSearches.rows,
      funnel: {
        visitors:       parseInt(funnelData.rows[0].visitors, 10),
        skillPageViews: parseInt(funnelData.rows[0].skill_page_views, 10),
        freeLeads:      parseInt(funnelData.rows[0].free_leads, 10),
        orders:         parseInt(kpi.rows[0].total_orders, 10),
      },
      buyerGeo:    buyerGeo.rows,
      entrySkills: entrySkills.rows,
    };

    return new Response(JSON.stringify(data), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'private, max-age=300',  // cache 5 min
      },
    });
  } catch (err) {
    console.error('[metrics]', err);
    return new Response('Internal error', { status: 500 });
  } finally {
    await client.end();
  }
}
