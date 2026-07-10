// utm.js — NovaKit attribution capture
// Include in <head> of every page. Reads UTM params from the URL and
// persists them to localStorage (30-day TTL). Survives multi-page browsing
// before checkout. checkout.html mirrors these to sessionStorage so they
// survive the cross-domain Razorpay redirect back to delivery.html.
(function () {
  try {
    var p = new URLSearchParams(location.search);
    var src = p.get('utm_source');
    if (!src) return; // no UTMs on this URL — don't overwrite existing attribution

    var ref = document.referrer || '';
    // Don't clobber attribution when returning from a payment processor
    if (ref.includes('razorpay') || ref.includes('ccavenue') || ref.includes('stripe')) return;

    var attr = {
      src: src,
      med: p.get('utm_medium') || '',
      cam: p.get('utm_campaign') || '',
      cnt: p.get('utm_content') || '',
      ref: ref && !ref.includes(location.hostname) ? ref : '',
      ts: Date.now()
    };
    localStorage.setItem('nk_attr', JSON.stringify(attr));
  } catch (e) {}
})();
