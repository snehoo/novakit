// functions/api/subscribe.js
// POST /api/subscribe
// Body: { email, source, utmSource, utmMedium, utmCampaign }
// Adds contact to Brevo list 8 (NovaKit-Leads).
// Env: BREVO_API_KEY

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

  const { email, source = 'homepage', utmSource = '', utmMedium = '', utmCampaign = '' } = body;

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
    return new Response(JSON.stringify({ error: 'Valid email required' }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  if (!env.BREVO_API_KEY) {
    return new Response(JSON.stringify({ error: 'Email service not configured' }), {
      status: 503, headers: { 'Content-Type': 'application/json', ...CORS }
    });
  }

  try {
    const res = await fetch('https://api.brevo.com/v3/contacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'api-key': env.BREVO_API_KEY },
      body: JSON.stringify({
        email: email.trim(),
        listIds: [8],
        updateEnabled: true,
        attributes: {
          SOURCE:       'novakit_' + source,
          UTM_SOURCE:   utmSource,
          UTM_MEDIUM:   utmMedium,
          UTM_CAMPAIGN: utmCampaign,
        },
      }),
    });

    // 201 = created, 204 = already exists and updated — both are success
    if (!res.ok && res.status !== 204) {
      const err = await res.text();
      console.error('[subscribe] Brevo error:', err);
      return new Response(JSON.stringify({ error: 'Subscribe failed' }), {
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
