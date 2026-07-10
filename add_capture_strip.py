#!/usr/bin/env python3
"""
Inject a free-skill email capture strip before <footer> in all blog/*.html
and skills/*.html pages. Idempotent — skips pages that already have it.
"""

import os, glob, re

MARKER = '<!-- nk-capture -->'

STRIP = '''\
<!-- nk-capture -->
<div id="nk-capture-strip" style="background:var(--surface,#fff);border-top:1px solid var(--line,#e4e1d8);border-bottom:1px solid var(--line,#e4e1d8);padding:32px 24px;text-align:center;">
  <p style="margin:0 0 6px;font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#DE7356;">Free skill</p>
  <p style="margin:0 0 4px;font-size:20px;font-weight:700;color:var(--ink,#21201c);line-height:1.3;">Try NovaKit before you spend a dollar.</p>
  <p style="margin:0 0 20px;font-size:14px;color:var(--muted,#6b6860);">Get the LinkedIn Post Engine free — runs live research before every post.</p>
  <div id="nkc-form" style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;max-width:440px;margin:0 auto 8px;">
    <input id="nkc-email" type="email" placeholder="your@email.com" style="flex:1;min-width:180px;padding:11px 14px;border:1.5px solid var(--line,#e4e1d8);border-radius:8px;font-size:14px;background:var(--bg,#f7f6f2);color:var(--ink,#21201c);outline:none;">
    <button onclick="nkcSubmit()" style="padding:11px 22px;background:#DE7356;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap;">Send it free →</button>
  </div>
  <p id="nkc-ok" style="display:none;margin:12px 0 0;font-size:15px;color:#4a7c59;font-weight:600;">✓ Check your inbox — it’s on its way.</p>
  <p style="margin:10px 0 0;font-size:12px;color:var(--muted,#6b6860);">No spam. Unsubscribe any time.</p>
</div>
<script>
function nkcSubmit(){
  var e=document.getElementById('nkc-email').value.trim();
  if(!e||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)){document.getElementById('nkc-email').focus();return;}
  var attr={};try{attr=JSON.parse(localStorage.getItem('nk_attr')||'{}');}catch(x){}
  document.getElementById('nkc-form').style.display='none';
  document.getElementById('nkc-ok').style.display='block';
  fetch('/api/free-skill',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({email:e,utmSource:attr.src||'',utmMedium:attr.med||'',utmCampaign:attr.cam||''})
  }).catch(function(){});
}
</script>
<!-- /nk-capture -->
'''

def inject(path):
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    if MARKER in html:
        return 'skipped'
    # Insert before first <footer
    idx = html.find('<footer')
    if idx == -1:
        return 'no-footer'
    new_html = html[:idx] + STRIP + '\n' + html[idx:]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_html)
    return 'injected'

base = os.path.dirname(os.path.abspath(__file__))
counts = {'injected': 0, 'skipped': 0, 'no-footer': 0}

for pattern in ['blog/*.html', 'skills/*.html']:
    for path in sorted(glob.glob(os.path.join(base, pattern))):
        result = inject(path)
        counts[result] += 1
        if result != 'injected':
            print(f'  {result}: {os.path.relpath(path, base)}')

print(f"\nDone — injected: {counts['injected']}, skipped: {counts['skipped']}, no-footer: {counts['no-footer']}")
