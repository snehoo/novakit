// functions/api/email-sequence-cron.js
// CHANGES vs previous version:
//   - SELECT also pulls orders.id (UUID) — needed for feedback token
//   - Passes `orderUuid` to send-email-day2 + send-email-day7

import { getClient } from '../_db.js';

export async function scheduled(event, env, ctx) {
  ctx.waitUntil(runSequence(env));
}

export async function onRequestGet({ env }) {
  try {
    const result = await runSequence(env);
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function runSequence(env) {
  const client = await getClient(env);
  const log = { day2: [], day7: [], errors: [] };

  try {
    const baseUrl = 'https://novakit.tech';

    // ── Day 2 ───────────────────────────────────────────────────────────────
    const { rows: day2Orders } = await client.query(`
      SELECT id, buyer_email, skill_slug, razorpay_payment_id
      FROM orders
      WHERE status = 'paid'
        AND sequence_step = 0
        AND buyer_email IS NOT NULL
        AND buyer_email != ''
        AND paid_at <= NOW() - INTERVAL '47 hours'
        AND paid_at >= NOW() - INTERVAL '72 hours'
    `);

    for (const order of day2Orders) {
      try {
        const { rows: skillRows } = await client.query(
          `SELECT name FROM skills WHERE slug = $1`, [order.skill_slug]
        );
        const skillName = skillRows[0]?.name || order.skill_slug;

        const res = await fetch(`${baseUrl}/api/send-email-day2`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: order.buyer_email,
            skillName,
            skillSlug: order.skill_slug,
            orderId: order.razorpay_payment_id,
            orderUuid: order.id,                 // ← NEW
          }),
        });

        if (res.ok) {
          await client.query(`UPDATE orders SET sequence_step = 1 WHERE id = $1`, [order.id]);
          log.day2.push({ id: order.id, email: order.buyer_email, skill: order.skill_slug, status: 'sent' });
        } else {
          log.errors.push({ id: order.id, step: 'day2', error: await res.text() });
        }
      } catch (err) {
        log.errors.push({ id: order.id, step: 'day2', error: err.message });
      }
    }

    // ── Day 7 ───────────────────────────────────────────────────────────────
    const { rows: day7Orders } = await client.query(`
      SELECT id, buyer_email, skill_slug, bundle_key, razorpay_payment_id
      FROM orders
      WHERE status = 'paid'
        AND sequence_step = 1
        AND buyer_email IS NOT NULL
        AND buyer_email != ''
        AND paid_at <= NOW() - INTERVAL '167 hours'
        AND paid_at >= NOW() - INTERVAL '192 hours'
    `);

    for (const order of day7Orders) {
      try {
        const { rows: skillRows } = await client.query(
          `SELECT name FROM skills WHERE slug = $1`, [order.skill_slug]
        );
        const skillName = skillRows[0]?.name || order.skill_slug;

        const res = await fetch(`${baseUrl}/api/send-email-day7`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: order.buyer_email,
            skillName,
            skillSlug: order.skill_slug,
            bundleKey: order.bundle_key,
            orderId: order.razorpay_payment_id,
            orderUuid: order.id,                 // ← NEW
          }),
        });

        if (res.ok) {
          await client.query(`UPDATE orders SET sequence_step = 2 WHERE id = $1`, [order.id]);
          log.day7.push({ id: order.id, email: order.buyer_email, skill: order.skill_slug, status: 'sent' });
        } else {
          log.errors.push({ id: order.id, step: 'day7', error: await res.text() });
        }
      } catch (err) {
        log.errors.push({ id: order.id, step: 'day7', error: err.message });
      }
    }

  } finally {
    await client.end();
  }

  console.log('[email-sequence-cron]', JSON.stringify(log));
  return log;
}
