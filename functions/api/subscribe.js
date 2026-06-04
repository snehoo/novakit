// functions/api/subscribe.js
// POST /api/subscribe
// Body: { email, source }
// Proxies subscription to Beehiiv — avoids CORS and keeps API key server-side.

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
  try { body = await request.json(); } catch {
    return new Response('Bad JSON', { status: 400, headers: CORS });
  }

  const { email, source } = body;
  if (!email || !email.includes('@')) {
    return new Response(JSON.stringify({ error: 'Invalid email' }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  try {
    const res = await fetch(`https://api.beehiiv.com/v2/publications/${env.BEEHIIV_PUB_ID}/subscriptions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${env.BEEHIIV_API_KEY}`,
      },
      body: JSON.stringify({
        email,
        reactivate_existing: false,
        send_welcome_email: false,
        utm_source: source || 'blog_subscribe',
        utm_medium: 'organic',
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error('[subscribe] Beehiiv error:', err);
      return new Response(JSON.stringify({ error: 'Subscribe failed', detail: err }), {
        status: 502, headers: { 'Content-Type': 'application/json', ...CORS }
      });
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...CORS }
    });

  } catch (err) {
    console.error('[subscribe]', err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }
}
