// functions/api/email-sequence-cron.js
//
// Step chain:
//   0 → [Day 2]  → 1
//   1 → [Day 3]  → 2   (time window 71–120 h; skips buyers already past that window)
//   2 → [Day 5]  → 3   (time window 119–144 h)
//   1|3 → [Day 7] → 4  (step IN (1,3): catches pre-existing buyers at step 1
//                        AND new buyers who completed Day 3/5 at step 3)
//   4 → [Day 14] → 5

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
  const log = { day2: [], day3: [], day5: [], day7: [], day14: [], errors: [] };

  try {
    const baseUrl = 'https://novakit.tech';

    // ── Day 2 (47–72 h) ─────────────────────────────────────────────────────
    const { rows: day2Orders } = await client.query(`
      SELECT id, buyer_email, skill_slug, razorpay_payment_id
      FROM orders
      WHERE status = 'paid'
        AND sequence_step = 0
        AND buyer_email IS NOT NULL AND buyer_email != ''
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
            to: order.buyer_email, skillName,
            skillSlug: order.skill_slug,
            orderId: order.razorpay_payment_id,
            orderUuid: order.id,
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

    // ── Day 3 (71–120 h) ────────────────────────────────────────────────────
    const { rows: day3Orders } = await client.query(`
      SELECT id, buyer_email, skill_slug, razorpay_payment_id
      FROM orders
      WHERE status = 'paid'
        AND sequence_step = 1
        AND buyer_email IS NOT NULL AND buyer_email != ''
        AND paid_at <= NOW() - INTERVAL '71 hours'
        AND paid_at >= NOW() - INTERVAL '120 hours'
    `);

    for (const order of day3Orders) {
      try {
        const { rows: skillRows } = await client.query(
          `SELECT name FROM skills WHERE slug = $1`, [order.skill_slug]
        );
        const skillName = skillRows[0]?.name || order.skill_slug;

        const res = await fetch(`${baseUrl}/api/send-email-day3`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: order.buyer_email, skillName,
            skillSlug: order.skill_slug,
            orderId: order.razorpay_payment_id,
          }),
        });

        if (res.ok) {
          await client.query(`UPDATE orders SET sequence_step = 2 WHERE id = $1`, [order.id]);
          log.day3.push({ id: order.id, email: order.buyer_email, skill: order.skill_slug, status: 'sent' });
        } else {
          log.errors.push({ id: order.id, step: 'day3', error: await res.text() });
        }
      } catch (err) {
        log.errors.push({ id: order.id, step: 'day3', error: err.message });
      }
    }

    // ── Day 5 (119–144 h) ───────────────────────────────────────────────────
    const { rows: day5Orders } = await client.query(`
      SELECT id, buyer_email, skill_slug, razorpay_payment_id
      FROM orders
      WHERE status = 'paid'
        AND sequence_step = 2
        AND buyer_email IS NOT NULL AND buyer_email != ''
        AND paid_at <= NOW() - INTERVAL '119 hours'
        AND paid_at >= NOW() - INTERVAL '144 hours'
    `);

    for (const order of day5Orders) {
      try {
        const { rows: skillRows } = await client.query(
          `SELECT name FROM skills WHERE slug = $1`, [order.skill_slug]
        );
        const skillName = skillRows[0]?.name || order.skill_slug;

        const res = await fetch(`${baseUrl}/api/send-email-day5`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: order.buyer_email, skillName,
            orderId: order.razorpay_payment_id,
          }),
        });

        if (res.ok) {
          await client.query(`UPDATE orders SET sequence_step = 3 WHERE id = $1`, [order.id]);
          log.day5.push({ id: order.id, email: order.buyer_email, skill: order.skill_slug, status: 'sent' });
        } else {
          log.errors.push({ id: order.id, step: 'day5', error: await res.text() });
        }
      } catch (err) {
        log.errors.push({ id: order.id, step: 'day5', error: err.message });
      }
    }

    // ── Day 7 (167–192 h) ───────────────────────────────────────────────────
    // step IN (1, 3): step 1 = pre-existing buyers who never got Day 3/5
    //                 step 3 = new buyers who completed the full Day 3→5 chain
    const { rows: day7Orders } = await client.query(`
      SELECT id, buyer_email, skill_slug, bundle_key, razorpay_payment_id
      FROM orders
      WHERE status = 'paid'
        AND sequence_step IN (1, 3)
        AND buyer_email IS NOT NULL AND buyer_email != ''
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
            to: order.buyer_email, skillName,
            skillSlug: order.skill_slug,
            bundleKey: order.bundle_key,
            orderId: order.razorpay_payment_id,
            orderUuid: order.id,
          }),
        });

        if (res.ok) {
          await client.query(`UPDATE orders SET sequence_step = 4 WHERE id = $1`, [order.id]);
          log.day7.push({ id: order.id, email: order.buyer_email, skill: order.skill_slug, status: 'sent' });
        } else {
          log.errors.push({ id: order.id, step: 'day7', error: await res.text() });
        }
      } catch (err) {
        log.errors.push({ id: order.id, step: 'day7', error: err.message });
      }
    }

    // Day 14 referral email — disabled until affiliate program is set up
    // Re-enable by uncommenting and wiring send-email-day14.js

  } finally {
    await client.end();
  }

  console.log('[email-sequence-cron]', JSON.stringify(log));
  return log;
}
