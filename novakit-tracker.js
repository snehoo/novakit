// novakit-tracker.js
// Drop this script on every page of the NovaKit site.
// It auto-fires a pageview on load, and exposes window.nk for manual events.
//
// Usage in HTML:
//   <script src="/novakit-tracker.js" data-skill="video-script-engine" defer></script>
//
// Manual calls:
//   nk.download('video-script-engine', orderId, buyerHash)
//   nk.search('instagram caption', 0)   // 0 results = miss

(function () {
  const ENDPOINT = '/api/track';

  // Stable session ID for this browser session (resets on tab close)
  function getSessionId() {
    let id = sessionStorage.getItem('nk_sid');
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem('nk_sid', id);
    }
    return id;
  }

  async function send(payload) {
    try {
      await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        // Use keepalive so the request completes even if user navigates away
        keepalive: true,
      });
    } catch {
      // Silent fail — never break the user experience for analytics
    }
  }

  // Auto-fire pageview on load
  const script   = document.currentScript;
  const skillSlug = script?.dataset?.skill ?? null;

  send({
    type:      'pageview',
    skillSlug,
    sessionId: getSessionId(),
    referrer:  document.referrer || null,
  });

  // Public API
  window.nk = {
    download(skillSlug, orderId, buyerHash) {
      send({ type: 'download', skillSlug, orderId, buyerHash });
    },
    search(query, resultCount) {
      send({ type: 'search', query, resultCount, sessionId: getSessionId() });
    },
  };
})();
