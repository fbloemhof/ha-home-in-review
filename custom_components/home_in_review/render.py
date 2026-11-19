"""Render report documents (see collector.py) as a self-contained HTML presentation.

One topic per full-screen slide; slides without data are left out. No external resources: system fonts,
inline SVG charts, inline CSS/JS. Rendering happens on request, so layout and translation updates also apply to
months that were collected earlier.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import math
from collections.abc import Callable
from typing import Any

from .i18n import Lang

esc = html.escape


def ym_of(doc: dict) -> str:
    return f'{doc["period"]["year"]:04d}-{doc["period"]["month"]:02d}'


def prev_ym(ym: str, n: int = 1) -> str:
    y, m = map(int, ym.split("-"))
    m -= n
    while m < 1:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def g(d: Any, *path, default=None):
    for p in path:
        if not isinstance(d, dict) or p not in d or d[p] is None:
            return default
        d = d[p]
    return d


# ============================================================================ styles & scripts
CSS = r"""
:root{
  color-scheme:light;
  --bg:#f3efe6;--paper:#faf8f2;--ink:#16181d;--ink2:#4a4d55;--mut:#7d8088;--line:#ddd7c9;
  --s1:#2a78d6;--s3:#1baf7a;--s4:#d99400;--hi:#d9602b;--cost:#6b6e76;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]):not([data-theme="paper"]){
  color-scheme:dark;--bg:#0f1115;--paper:#171a21;--ink:#f0efec;--ink2:#c3c2b7;--mut:#8f8f8a;--line:#2a2e36;
  --s1:#4a90e2;--s3:#22a777;--s4:#d29a1c;--hi:#e8743f;--cost:#9a9ca3}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0f1115;--paper:#171a21;--ink:#f0efec;--ink2:#c3c2b7;--mut:#8f8f8a;--line:#2a2e36;
  --s1:#4a90e2;--s3:#22a777;--s4:#d29a1c;--hi:#e8743f;--cost:#9a9ca3}
:root[data-theme="night"]{color-scheme:dark;--bg:#0a1020;--paper:#111a2e;--ink:#eef2fa;--ink2:#b9c3d6;--mut:#7f8ba3;--line:#1f2a42;
  --s1:#3f86e0;--s3:#1fa37a;--s4:#c9961c;--hi:#d68a2a;--cost:#8a96ad}
:root[data-theme="mono"]{color-scheme:light;--bg:#f6f6f4;--paper:#fff;--ink:#0b0b0b;--ink2:#4a4a48;--mut:#85857f;--line:#e2e2df;
  --s1:#3d3d3b;--s3:#2f5bea;--s4:#9a9a96;--hi:#2f5bea;--cost:#a3a39e;--serif:var(--sans)}
*{box-sizing:border-box}
html{scroll-snap-type:y mandatory;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
a{color:inherit}
.slide{min-height:100svh;scroll-snap-align:start;padding:max(64px,clamp(28px,6vw,88px)) clamp(18px,6vw,96px) clamp(44px,6vw,88px);
  display:grid;align-content:center;gap:clamp(18px,3vw,36px);border-bottom:1px solid var(--line);position:relative}
.kicker{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--mut);display:flex;gap:12px;align-items:center}
.kicker b{color:var(--hi);font-weight:600}
.kicker:after{content:"";height:1px;background:var(--line);flex:1;max-width:160px}
h1,h2{font-family:var(--serif);font-weight:500;letter-spacing:-.02em;margin:0;line-height:1.1}
h2{font-size:clamp(28px,4.4vw,56px);max-width:18em;text-wrap:balance}
h2 em{font-style:italic;color:var(--hi)}
:root[data-theme="mono"] h2 em{font-style:normal}
.hero{font-family:var(--serif);font-weight:600;font-size:clamp(56px,10vw,136px);line-height:.95;letter-spacing:-.03em}
.hero small{display:block;font-family:var(--sans);font-size:max(15px,.13em);font-weight:500;letter-spacing:.02em;margin-top:.5em;color:var(--ink2)}
.cmp{color:var(--ink2);font-size:15px;margin-top:8px}
.cmp b{color:var(--ink)}
.head2{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(0,1fr);gap:clamp(24px,5vw,72px);align-items:end}
.head2 .trend{justify-self:end;width:100%}
@media (max-width:860px){.head2{grid-template-columns:1fr}.head2 .trend{justify-self:start}}
.split{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:clamp(28px,6vw,96px);align-items:center}
@media (max-width:860px){.split{grid-template-columns:1fr}}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:20px 28px}
.stat{border-top:1px solid var(--line);padding-top:10px}
.stat .l{font-size:13px;color:var(--mut)}
.stat .v{font-family:var(--serif);font-size:28px;font-weight:500;letter-spacing:-.01em;line-height:1.15}
.stat .v small{font-family:var(--sans);font-size:13px;font-weight:500;color:var(--ink2);margin-left:4px;letter-spacing:0}
.stat .c{font-size:12.5px;color:var(--mut)}
.note{font-size:13px;color:var(--mut);max-width:48em;margin:0}
svg{display:block;width:100%;height:auto;overflow:visible}
.ax{fill:var(--mut);font:11px var(--sans)}
.vl{fill:var(--ink);font:600 12px var(--sans)}
.grid{stroke:var(--line);stroke-width:1}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--ink2);margin-top:10px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.trend{max-width:440px}
.trend .cap{font-size:12px;color:var(--mut);margin-bottom:4px}
.cover{align-content:space-between}
.cover .top{display:flex;justify-content:space-between;gap:16px;font-size:13px;color:var(--mut);letter-spacing:.08em;text-transform:uppercase}
.cover h1{font-size:clamp(68px,17vw,240px);font-weight:600;letter-spacing:-.045em;line-height:.88}
.cover h1 span{display:block;font-size:.2em;letter-spacing:0;font-weight:400;color:var(--ink2);margin-top:.4em;font-style:italic}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:18px 32px}
.figs div{border-top:2px solid var(--ink);padding-top:10px}
.figs b{display:block;font-family:var(--serif);font-size:clamp(26px,3.4vw,42px);font-weight:500;letter-spacing:-.02em}
.figs span{font-size:13px;color:var(--mut)}
@media (max-width:560px){.figs{grid-template-columns:1fr 1fr}}
.narrow{display:none}
@media (max-width:640px){.wide{display:none}.narrow{display:block}}
.rank{display:grid;gap:10px}
.rank .r{display:grid;grid-template-columns:minmax(110px,220px) 1fr 84px 54px 70px;gap:14px;align-items:center;font-size:14.5px}
.rank .h{font-size:12px;color:var(--mut);letter-spacing:.04em}
.rank .v,.rank .e,.rank .p{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.rank .e{color:var(--ink2)}.rank .p{color:var(--mut);font-size:13px}
.rank .t{height:10px;border-radius:5px;background:color-mix(in srgb,var(--line) 55%,transparent);overflow:hidden}
.rank .f{height:100%;border-radius:5px;background:var(--s1)}
.rank .f.muted{background:var(--mut);opacity:.5}
.rank .lb{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rank .lb small{color:var(--mut);margin-left:6px}
@media (max-width:560px){.rank .r{grid-template-columns:1fr 70px 44px 58px;gap:4px 10px}.rank .t{grid-column:1/-1;order:5}.rank .h .t{display:none}}
.tbl{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14.5px;font-variant-numeric:tabular-nums}
th{font-weight:500;font-size:12px;color:var(--mut);letter-spacing:.04em;text-align:right;padding:6px 10px;border-bottom:1px solid var(--line)}
td{padding:7px 10px;border-bottom:1px solid color-mix(in srgb,var(--line) 60%,transparent);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
tr.fl td{color:var(--mut);font-size:12px;letter-spacing:.12em;text-transform:uppercase;padding-top:16px}
td .sm{color:var(--mut);font-size:12.5px;margin-left:6px}
.bill{display:grid;gap:18px}
.bb .bh{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px}
.bb .bh span{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
.bb .bh b{font-family:var(--serif);font-size:26px;font-weight:500}
.bb .bt{display:flex;gap:2px;height:30px}
.bb .bt i{display:block;height:100%;border-radius:5px}
.rec{border-top:1px solid var(--line);padding-top:10px;display:grid;gap:4px;font-size:14.5px}
.rec .rl{display:flex;justify-content:space-between;gap:12px;font-variant-numeric:tabular-nums}
.rec .rl i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:8px;vertical-align:-1px}
.rec .tot{border-top:2px solid var(--ink);margin-top:6px;padding-top:8px;font-weight:600;font-size:16px}
.ic{width:1em;height:1em;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;flex:none}
.kicker .ic{width:17px;height:17px;color:var(--hi)}
.figs .ic{display:block;width:24px;height:24px;color:var(--hi);margin-bottom:10px}
.wm{position:absolute;right:clamp(20px,6vw,96px);top:clamp(56px,9vh,96px);width:clamp(100px,14vw,220px);height:auto;color:var(--ink);opacity:.07;stroke-width:.9;pointer-events:none}
.slide>*:not(.wm):not(.pg){position:relative;z-index:1}
@media (max-width:700px){.wm{width:90px;opacity:.05}}
.nav{position:fixed;right:18px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:10px;z-index:5}
.nav a{width:9px;height:9px;border-radius:50%;background:var(--line);display:block;position:relative}
.nav a.on{background:var(--hi);transform:scale(1.25)}
.nav a:hover:after{content:attr(data-l);position:absolute;right:18px;top:50%;transform:translateY(-50%);white-space:nowrap;
  font-size:12px;background:var(--paper);color:var(--ink);padding:3px 8px;border-radius:6px;border:1px solid var(--line)}
@media (max-width:700px){.nav{display:none}}
.bar{position:fixed;left:0;top:0;height:3px;background:var(--hi);width:0;z-index:6}
[hidden]{display:none!important}
.topbar{position:fixed;left:0;right:0;top:0;display:flex;justify-content:space-between;align-items:center;gap:10px;
  padding:max(10px,env(safe-area-inset-top)) 16px 10px;z-index:7;pointer-events:none}
.topbar>*{pointer-events:auto}
.topbar a,.topbar select{font:600 11.5px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);text-decoration:none;
  background:color-mix(in srgb,var(--paper) 85%,transparent);border:1px solid var(--line);border-radius:999px;padding:6px 12px;
  backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);cursor:pointer}
.topbar a:hover,.topbar select:hover{color:var(--hi);border-color:var(--hi)}
.topbar select{appearance:none;-webkit-appearance:none;text-align:center}
.mnav{display:flex;gap:6px;align-items:center}
.mfoot{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:760px}
.mfoot a{display:block;text-decoration:none;border-top:2px solid var(--ink);padding-top:10px}
.mfoot a span{display:block;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
.mfoot a b{font-family:var(--serif);font-size:clamp(24px,3vw,36px);font-weight:500;letter-spacing:-.02em}
.mfoot a:hover b{color:var(--hi)}
.mfoot .nx{text-align:right;grid-column:2}
.themes{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13px;color:var(--mut)}
.themes button{font:600 12px var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--ink2);background:var(--paper);
  border:1px solid var(--line);border-radius:999px;padding:7px 14px;cursor:pointer}
.themes button.on{border-color:var(--hi);color:var(--hi)}
.pg{position:absolute;right:clamp(20px,6vw,96px);bottom:22px;font-size:12px;color:var(--mut);letter-spacing:.1em}
ul.src{margin:0;padding-left:1.1em;color:var(--ink2);font-size:14.5px}
#tip{position:fixed;pointer-events:none;background:var(--paper);color:var(--ink);border:1px solid var(--line);border-radius:8px;
  padding:6px 10px;font-size:13px;box-shadow:0 6px 24px rgba(0,0,0,.12);opacity:0;transition:opacity .1s;z-index:9;max-width:280px}
.hit{fill:transparent}
.idx{display:grid;gap:0;max-width:900px}
.idx a{display:grid;grid-template-columns:1fr auto auto;gap:24px;align-items:baseline;text-decoration:none;padding:14px 0;border-bottom:1px solid var(--line)}
.idx a b{font-family:var(--serif);font-size:clamp(22px,2.6vw,30px);font-weight:500}
.idx a span{color:var(--ink2);font-variant-numeric:tabular-nums}
.idx a:hover b{color:var(--hi)}
.idx .y{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);padding-top:26px}
"""

# Navigation between reports: inside the panel the page is in an iframe and asks the panel to load another report.
THEME_HEAD = r"""<script>(()=>{const r=document.documentElement;let t=new URLSearchParams(location.search).get('theme');
const h=/theme=([a-z]+)/.exec(location.hash);if(h)t=h[1];if(!t){try{t=localStorage.getItem('hir-theme')}catch(e){}}
if(t&&t!=='auto')r.dataset.theme=t;})()</script>"""

JS = r"""
window.hirGo=f=>{if(window.parent!==window)parent.postMessage({homeInReview:f},'*');else location.href='./'+f+'.html'};
document.addEventListener('click',e=>{const a=e.target.closest&&e.target.closest('a[data-go]');if(!a)return;e.preventDefault();hirGo(a.dataset.go)});
window.hirTheme=t=>{const r=document.documentElement;delete r.dataset.theme;if(t!=='auto')r.dataset.theme=t;
 try{localStorage.setItem('hir-theme',t)}catch(e){};document.querySelectorAll('.themes button').forEach(b=>b.classList.toggle('on',b.dataset.t===t))};
(()=>{const t=document.documentElement.dataset.theme||'auto';document.querySelectorAll('.themes button').forEach(b=>b.classList.toggle('on',b.dataset.t===t))})();
(()=>{const sel=document.querySelector('.msel');if(sel)sel.onchange=()=>hirGo(sel.value);
addEventListener('keydown',e=>{if(e.target.tagName==='SELECT')return;const k={'[':'.prev',']':'.next'}[e.key];
 if(k){const a=document.querySelector('.topbar '+k);if(a&&!a.hidden)hirGo(a.dataset.go)}});})();
(()=>{const s=[...document.querySelectorAll('.slide')],dots=[...document.querySelectorAll('.nav a')],bar=document.querySelector('.bar');
const io=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){const i=s.indexOf(e.target);dots.forEach((d,j)=>d.classList.toggle('on',j===i));}})},{threshold:.5});
s.forEach(x=>io.observe(x));
addEventListener('scroll',()=>{const h=document.documentElement;bar.style.width=(h.scrollTop/Math.max(1,h.scrollHeight-h.clientHeight)*100)+'%'},{passive:true});
const cur=()=>{let b=0,best=1e9;s.forEach((x,i)=>{const d=Math.abs(x.getBoundingClientRect().top);if(d<best){best=d;b=i}});return b};
addEventListener('keydown',e=>{if(['ArrowRight','PageDown'].includes(e.key)){e.preventDefault();s[Math.min(cur()+1,s.length-1)].scrollIntoView()}
 if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();s[Math.max(cur()-1,0)].scrollIntoView()}});
const tip=document.getElementById('tip');
const show=(e,t)=>{tip.textContent=t;tip.style.opacity=1;const x=Math.min(e.clientX+14,innerWidth-tip.offsetWidth-8),y=Math.max(e.clientY-tip.offsetHeight-12,8);tip.style.left=x+'px';tip.style.top=y+'px'};
document.querySelectorAll('[data-tip]').forEach(el=>{el.addEventListener('mousemove',e=>show(e,el.dataset.tip));
 el.addEventListener('mouseleave',()=>tip.style.opacity=0);el.addEventListener('click',e=>show(e,el.dataset.tip))});
})();
"""

ICONS = {
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>',
    "bolt": '<path d="M13 2.5 4.5 13.5H11l-1 8 8.5-11H12z"/>',
    "plug": '<path d="M9 3v5M15 3v5"/><path d="M6 8h12v3a6 6 0 0 1-12 0z"/><path d="M12 17v4"/>',
    "receipt": '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    "euro": '<path d="M17.5 6.5a7 7 0 1 0 0 11"/><path d="M4 10h9M4 14h9"/>',
    "house": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-5.5h4V20"/>',
    "battery": '<rect x="2.5" y="7" width="17" height="10" rx="2"/><path d="M21.5 10.5v3"/><path d="M6.5 10v4M10 10v4M13.5 10v4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.6v.01"/>',
    "drop": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/><path d="M9 14.5a3 3 0 0 0 3 3"/>',
    "flame": '<path d="M12 3c.5 3 5 5.2 5 10a5 5 0 0 1-10 0c0-2.6 1.6-4 2.2-5.8.9 1 1.6 2 1.6 3.2 1.2-1.6 1.6-4.6 1.2-7.4z"/>',
    "thermo": '<path d="M10 4.5a2 2 0 0 1 4 0v9.8a4 4 0 1 1-4 0z"/><path d="M12 9v8.5"/>',
    "cloud": '<path d="M7 18h10a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.2 9.2 4.5 4.5 0 0 0 7 18z"/>',
}


def icon(name: str, cls: str = "ic") -> str:
    return f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true">{ICONS.get(name, ICONS["plug"])}</svg>'


# ============================================================================ charts
def nice_step(span: float, ticks: int = 3) -> float:
    """A round grid step (1, 2, 2.5 or 5 x 10^n) giving about ``ticks`` lines."""
    raw = max(span, 1e-9) / ticks
    mag = 10 ** math.floor(math.log10(raw))
    return next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)


def trend(L: Lang, series: list[tuple[str, float | None]], cap: str, fmt: Callable[[float], str]) -> str:
    """13 bars: same month last year (outlined) .. this month (accent)."""
    if sum(1 for _, v in series if v is not None) < 3:
        return ""
    W, H, pb, pt = 440, 100, 18, 18
    vals = [v for _, v in series if v is not None]
    hi, lo = max(vals + [0]), min(vals + [0])
    span = (hi - lo) or 1
    y0 = pt + (H - pb - pt) * hi / span
    n = len(series)
    bw = W / n
    ly = series[0][1] if n == 13 else None
    out = [f'<div class="trend"><div class="cap">{esc(cap)}' + (f' · {L("last_year")} {fmt(ly)}' if ly is not None else "")
           + f'</div><svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(cap)}">',
           f'<line x1="0" x2="{W}" y1="{y0:.1f}" y2="{y0:.1f}" class="grid"/>']
    for i, (ym, v) in enumerate(series):
        x = i * bw
        last, first = i == n - 1, (i == 0 and n == 13)
        m = int(ym[5:])
        if v is not None:
            h = max((H - pb - pt) * abs(v) / span, 1.5)
            y = y0 - h if v >= 0 else y0
            if last:
                out.append(f'<rect x="{x + bw * .18:.1f}" y="{y:.1f}" width="{bw * .64:.1f}" height="{h:.1f}" rx="3" fill="var(--hi)"/>')
            elif first:
                out.append(f'<rect x="{x + bw * .18 + .75:.1f}" y="{y + .75:.1f}" width="{bw * .64 - 1.5:.1f}" height="{max(h - 1.5, .5):.1f}" rx="3" fill="none" stroke="var(--hi)" stroke-width="1.5"/>')
            else:
                out.append(f'<rect x="{x + bw * .18:.1f}" y="{y:.1f}" width="{bw * .64:.1f}" height="{h:.1f}" rx="3" fill="var(--mut)" opacity=".4"/>')
            if last or first:
                ty = y - 5 if v >= 0 else y0 - 5
                out.append(f'<text x="{x + bw / 2:.1f}" y="{ty:.1f}" class="vl" text-anchor="middle">{fmt(v)}</text>')
        tipv = fmt(v) if v is not None else L("no_data")
        out.append(f'<rect class="hit" x="{x:.1f}" y="0" width="{bw:.1f}" height="{H}" data-tip="{esc(L.month_short(m))} {ym[:4]}: {esc(tipv)}"/>')
        lab = L.month_short(m)[0].upper() + (("’" + ym[2:4]) if (first or last) else "")
        out.append(f'<text x="{x + bw / 2:.1f}" y="{H - 3}" class="ax" text-anchor="middle"{" font-weight=\"600\"" if (first or last) else ""}>{lab}</text>')
    out.append("</svg></div>")
    return "".join(out)


def daily_energy_chart(L: Lang, daily: list[dict], W=1000, H=340, every=7) -> str:
    """Grid import up, export down, per day."""
    if not daily:
        return ""
    pl, top, bot = 44, 14, 26
    step = nice_step(max(max(x["import"] for x in daily), max(x["export"] for x in daily)), 2)
    up = step * max(1, math.ceil(max(x["import"] for x in daily) / step))
    dn = step * math.ceil(max(x["export"] for x in daily) / step)
    span = up + dn
    y0 = top + (H - top - bot) * up / span
    sc = (H - top - bot) / span
    bw = (W - pl) / len(daily)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(L("imported"))} / {esc(L("exported"))}">']
    for v in (up, -dn) if dn else (up,):
        y = y0 - v * sc
        out.append(f'<line x1="{pl}" x2="{W}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/><text x="{pl - 8}" y="{y + 4:.1f}" class="ax" text-anchor="end">{L.num(abs(v))}</text>')
    out.append(f'<line x1="{pl}" x2="{W}" y1="{y0:.1f}" y2="{y0:.1f}" stroke="var(--ink2)" stroke-width="1"/>')
    for i, x in enumerate(daily):
        px = pl + i * bw
        hu, hd = x["import"] * sc, x["export"] * sc
        w = max(bw - 3, 2)
        if hu > 0.3:
            out.append(f'<rect x="{px + 1.5:.1f}" y="{y0 - hu:.1f}" width="{w:.1f}" height="{hu:.1f}" rx="{min(4, w / 2):.1f}" fill="var(--s1)"/>')
        if hd > 0.3:
            out.append(f'<rect x="{px + 1.5:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{hd:.1f}" rx="{min(4, w / 2):.1f}" fill="var(--s3)"/>')
        d = dt.date.fromisoformat(x["d"])
        tip = f'{d.day} {L.month_short(d.month)} · {L("imported")} {L.num(x["import"], 1)} kWh · {L("exported")} {L.num(x["export"], 1)} kWh'
        if x.get("solar"):
            tip += f' · {L("solar")} {L.num(x["solar"], 1)} kWh'
        out.append(f'<rect class="hit" x="{px:.1f}" y="0" width="{bw:.1f}" height="{H}" data-tip="{esc(tip)}"/>')
        if (d.day - 1) % every == 0:
            out.append(f'<text x="{px + bw / 2:.1f}" y="{H - 6}" class="ax" text-anchor="middle">{d.day} {esc(L.month_short(d.month))}</text>')
    out.append("</svg>")
    return "".join(out)


def hour_profile(L: Lang, w: list[float | None], W=1000, H=240) -> str:
    vals = [v for v in w if v is not None]
    if not vals:
        return ""
    pl, top, bot = 58, 16, 24
    step = nice_step(max(vals))
    hi = max(step * math.ceil(max(vals) / step), 1)
    bw = (W - pl) / 24
    sc = (H - top - bot) / hi
    peak = max(range(24), key=lambda i: w[i] or 0)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(L("s_rhythm"))}">']
    t = step
    while t <= hi + 1e-9:
        y = H - bot - t * sc
        out.append(f'<line x1="{pl}" x2="{W}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/><text x="{pl - 8}" y="{y + 4:.1f}" class="ax" text-anchor="end">{L.num(t)} W</text>')
        t += step
    for i, v in enumerate(w):
        if v is None:
            continue
        h = v * sc
        x = pl + i * bw
        fill = "var(--hi)" if i == peak else "var(--s1)"
        out.append(f'<rect x="{x + 2:.1f}" y="{H - bot - h:.1f}" width="{bw - 4:.1f}" height="{h:.1f}" rx="3" fill="{fill}"/>')
        out.append(f'<rect class="hit" x="{x:.1f}" y="0" width="{bw:.1f}" height="{H}" data-tip="{i:02d}:00–{(i + 1) % 24:02d}:00 · {L.num(v)} W"/>')
        if i % 3 == 0:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{H - 6}" class="ax" text-anchor="middle">{i:02d}</text>')
    out.append("</svg>")
    return "".join(out)


def temp_chart(L: Lang, daily: list[dict], normal: float | None, unit: str, W=1000, H=260, every=7) -> str:
    pts = [x for x in daily if x.get("mean") is not None]
    if not pts:
        return ""
    vals = [v for x in pts for v in (x["min"], x["max"]) if v is not None] + ([normal] if normal is not None else [])
    step = 5 if unit == "°C" else 10
    lo, hi = step * int(min(vals) // step), step * (int(max(vals) // step) + 1)
    pl, top, bot = 44, 12, 26
    n = len(daily)
    bw = (W - pl) / n
    Y = lambda v: top + (hi - v) / (hi - lo) * (H - top - bot)  # noqa: E731
    X = lambda i: pl + i * bw + bw / 2  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(L("s_weather"))}">']
    for t in range(lo, hi + 1, step):
        out.append(f'<line x1="{pl}" x2="{W}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/><text x="{pl - 8}" y="{Y(t) + 4:.1f}" class="ax" text-anchor="end">{t}°</text>')
    up = [(X(i), Y(x["max"])) for i, x in enumerate(daily) if x.get("max") is not None]
    dn = [(X(i), Y(x["min"])) for i, x in enumerate(daily) if x.get("min") is not None][::-1]
    if up and dn:
        out.append('<path d="M' + " L".join(f"{a:.1f},{b:.1f}" for a, b in up + dn) + 'Z" fill="var(--s1)" opacity=".16"/>')
    if normal is not None:
        out.append(f'<line x1="{pl}" x2="{W}" y1="{Y(normal):.1f}" y2="{Y(normal):.1f}" stroke="var(--hi)" stroke-width="1.5" stroke-dasharray="5 5"/>')
    p = [(X(i), Y(x["mean"])) for i, x in enumerate(daily) if x.get("mean") is not None]
    out.append('<path d="M' + " L".join(f"{a:.1f},{b:.1f}" for a, b in p) + '" fill="none" stroke="var(--s1)" stroke-width="2" stroke-linejoin="round"/>')
    for i, x in enumerate(daily):
        d = dt.date.fromisoformat(x["d"])
        tip = f'{d.day} {L.month_short(d.month)} · {L.num(x.get("min"), 1)} – {L.num(x.get("max"), 1)}{unit} ({L("avg")} {L.num(x.get("mean"), 1)}{unit})'
        if x.get("precip"):
            tip += f' · {L.num(x["precip"], 1)} mm'
        out.append(f'<rect class="hit" x="{pl + i * bw:.1f}" y="0" width="{bw:.1f}" height="{H}" data-tip="{esc(tip)}"/>')
        if (d.day - 1) % every == 0:
            out.append(f'<text x="{X(i):.1f}" y="{H - 6}" class="ax" text-anchor="middle">{d.day} {esc(L.month_short(d.month))}</text>')
    out.append("</svg>")
    return "".join(out)


# ============================================================================ page building blocks
def split_unit(value: str) -> str:
    """'123 kWh' -> '123<small>kWh</small>'."""
    num, sep, unit = value.rpartition(" ")
    if sep and num and any(c.isdigit() for c in num) and not any(c.isdigit() for c in unit):
        return f"{esc(num)}<small>{esc(unit)}</small>"
    return esc(value)


class Page:
    def __init__(self, L: Lang, ym: str, docs: dict[str, dict]):
        self.L = L
        self.ym = ym
        self.doc = docs[ym]
        self.docs = docs
        self.slides: list[tuple[str, str, str]] = []
        # Reference = the previous 12 months that have data (not this month).
        self.ref = [docs[m] for m in (prev_ym(ym, i) for i in range(1, 13)) if m in docs]

    # --- comparisons
    def ref_avg(self, fn) -> float | None:
        vals = []
        for d in self.ref:
            try:
                v = fn(d)
            except (KeyError, TypeError, IndexError):
                v = None
            if v is not None:
                vals.append(v)
        return sum(vals) / len(vals) if len(vals) >= 2 else None

    def compare(self, fn) -> tuple[float | None, dict]:
        """Reference for headlines: the same month last year when complete, else the 12-month average."""
        ly = self.docs.get(prev_ym(self.ym, 12))
        if ly and not g(ly, "energy", "partial_from"):
            try:
                v = fn(ly)
            except (KeyError, TypeError, IndexError):
                v = None
            if v is not None:
                mn = self.L.month(int(self.ym[5:]))
                return v, {"ref": self.L("ref_ly", month=mn), "ref2": self.L("ref2_ly", month=mn)}
        return self.ref_avg(fn), {"ref": self.L("ref_avg"), "ref2": self.L("ref2_avg")}

    def series13(self, fn) -> list[tuple[str, float | None]]:
        out = []
        for i in range(12, -1, -1):
            m = prev_ym(self.ym, i)
            d = self.docs.get(m)
            try:
                out.append((m, fn(d) if d else None))
            except (KeyError, TypeError, IndexError):
                out.append((m, None))
        return out

    def stat(self, label: str, value: str, cur=None, fn=None, fmt=None) -> str:
        c = ""
        if fn is not None and cur is not None:
            a = self.ref_avg(fn)
            if a:
                p = (cur - a) / abs(a)
                f = fmt or (lambda v: self.L.num(v))
                c = f'<div class="c">{self.L("avg")} {esc(f(a))}' + ("" if abs(p) < .05 else f' · {"▲" if p > 0 else "▼"} {self.L.num(abs(p) * 100)}%') + "</div>"
        return f'<div class="stat"><div class="l">{esc(label)}</div><div class="v">{split_unit(value)}</div>{c}</div>'

    def add(self, sid: str, label: str, wm: str, body: str, cls: str = "") -> None:
        n = len(self.slides) + 1
        mark = icon(wm, "ic wm") if sid != "cover" else ""
        self.slides.append((sid, label, f'<section class="slide {cls}" id="{sid}">{mark}{body}<div class="pg">{n:02d}</div></section>'))

    def kicker(self, label: str, ic: str) -> str:
        return f'<div class="kicker">{icon(ic)}<b>{len(self.slides) + 1:02d}</b>{esc(label)}</div>'


def _get(fn):
    def inner(d):
        try:
            return fn(d)
        except (KeyError, TypeError, IndexError):
            return None
    return inner


# ============================================================================ month report
def render_month(ym: str, docs: dict[str, dict], lang: str = "en", home_name: str | None = None) -> str:
    d = docs[ym]
    u = d["units"]
    L = Lang(lang, u.get("currency", "EUR"))
    P = Page(L, ym, docs)
    y, m = d["period"]["year"], d["period"]["month"]
    mname = L.month(m)
    e = d.get("energy") or {}
    kwh = lambda v, n=0: f"{L.num(v, n)} kWh"  # noqa: E731
    money = L.money
    tu = u.get("temperature", "°C")

    # ---------------------------------------------------------------- cover
    figs = []
    if e:
        figs.append(f'<div>{icon("house")}<b>{kwh(e["consumption"])}</b><span>{esc(L("used"))}</span></div>')
    if e.get("total_cost") is not None:
        figs.append(f'<div>{icon("euro")}<b>{money(e["total_cost"])}</b><span>{esc(L("net_cost"))}</span></div>')
    if e.get("solar"):
        figs.append(f'<div>{icon("sun")}<b>{kwh(e["solar"])}</b><span>{esc(L("from_sun"))}</span></div>')
    if g(d, "weather", "temp") is not None:
        figs.append(f'<div>{icon("thermo")}<b>{L.num(d["weather"]["temp"], 1)}{tu}</b><span>{esc(L("outside"))}</span></div>')
    if d.get("water"):
        w = d["water"]
        amt = f'{L.num(w["amount"] / 1000, 1)} m³' if w["unit"] == "L" else f'{L.num(w["amount"])} {w["unit"]}'
        figs.append(f'<div>{icon("drop")}<b>{amt}</b><span>{esc(L("water"))}</span></div>')
    top_right = esc(home_name) if home_name else str(y)
    P.add("cover", L("title"), "house", f'''
<div class="top"><span>{esc(L("title"))}</span><span>{top_right}</span></div>
<h1>{esc(mname[:1].upper() + mname[1:])}<span>{esc(L("cover_sub"))} · {y}</span></h1>
<div class="figs">{"".join(figs)}</div>''', "cover")

    # ---------------------------------------------------------------- electricity
    if e:
        cons = e["consumption"]
        avg, refs = P.compare(lambda x: x["energy"]["consumption"])
        if avg:
            p = (cons - avg) / avg
            head = L("h_energy_same", **refs) if abs(p) < .05 else L("h_energy_more" if p > 0 else "h_energy_less", pct=L.pct(abs(p)), **refs)
        else:
            head = L("h_energy_first", v=kwh(cons))
        stats = [P.stat(L("load"), kwh(cons), cons, _get(lambda x: x["energy"]["consumption"])),
                 P.stat(L("imported"), kwh(e["import"]), e["import"], _get(lambda x: x["energy"]["import"]))]
        if e.get("export"):
            stats.append(P.stat(L("exported"), kwh(e["export"]), e["export"], _get(lambda x: x["energy"]["export"])))
        if e.get("self_sufficiency") is not None:
            stats.append(P.stat(L("self_sufficiency"), L.pct(e["self_sufficiency"])))
        if e.get("base_load_w"):
            stats.append(P.stat(L("base_load"), f'{L.num(e["base_load_w"])} W', e["base_load_w"], _get(lambda x: x["energy"]["base_load_w"])))
        tr = trend(L, P.series13(_get(lambda x: x["energy"]["consumption"])), L("trend_use"), lambda v: kwh(v))
        legend = f'<span><i style="background:var(--s1)"></i>{esc(L("imported"))}</span>'
        if e.get("export"):
            legend += f'<span><i style="background:var(--s3)"></i>{esc(L("exported"))}</span>'
        P.add("energy", L("s_energy"), "bolt", f'''{P.kicker(L("s_energy"), "bolt")}
<div class="head2"><h2>{head}</h2>{tr}</div>
<div><div class="wide">{daily_energy_chart(L, e["daily"], 1000, 260)}</div><div class="narrow">{daily_energy_chart(L, e["daily"], 420, 280, 14)}</div>
<div class="legend">{legend}<span style="color:var(--mut)">{esc(L("kwh_per_day"))}</span></div></div>
<div class="stats">{"".join(stats)}</div>''')

    # ---------------------------------------------------------------- costs
    if e.get("net_cost") is not None:
        tot = e["total_cost"]
        avg, refs = P.compare(lambda x: x["energy"]["total_cost"])
        if tot < 0:
            head = L("h_cost_earned")
        elif avg is not None:
            diff = tot - avg
            head = (L("h_cost_same", **refs) if abs(diff) < max(5, abs(avg) * .05)
                    else L("h_cost_more" if diff > 0 else "h_cost_less", v=money(abs(diff)), **refs))
        else:
            head = L("h_cost_first", v=money(tot))
        paid = [(L("import_cost"), e.get("cost_import") or 0, "var(--cost)")]
        if e.get("fixed_costs"):
            paid.append((L("fixed"), e["fixed_costs"], "color-mix(in srgb,var(--cost) 55%,var(--bg))"))
        back = [(L("compensation"), e["compensation"], "var(--s3)")] if e.get("compensation") else []
        tp, tb = sum(v for _, v, _ in paid), sum(v for _, v, _ in back)
        mx = max(tp, tb, 0.01)

        def bar(title, items, total):
            segs = "".join(f'<i style="width:{max(v, 0) / mx * 100:.2f}%;background:{c}" data-tip="{esc(n)}: {esc(money(v))}"></i>' for n, v, c in items if v > 0)
            return f'<div class="bb"><div class="bh"><span>{esc(title)}</span><b>{money(total)}</b></div><div class="bt">{segs}</div></div>'

        lines = "".join(f'<div class="rl"><span><i style="background:{c}"></i>{esc(n)}</span><span>{money(v, 2)}</span></div>' for n, v, c in paid)
        lines += "".join(f'<div class="rl"><span><i style="background:{c}"></i>{esc(n)}</span><span>−{money(v, 2)}</span></div>' for n, v, c in back)
        bill = f'''<div class="bill">{bar(L("paid"), paid, tp)}{bar(L("received"), back, tb) if back else ""}
<div class="rec">{lines}<div class="rl tot"><span>{esc(L("total") if tot >= 0 else L("credit"))}</span><span>{money(abs(tot), 2)}</span></div></div></div>'''
        tr = trend(L, P.series13(_get(lambda x: x["energy"]["total_cost"])), L("trend_cost"), lambda v: money(v))
        note = L("cost_note") + (" " + L("cost_note_fixed") if e.get("fixed_costs") else "")
        price = ""
        if e.get("avg_import_price") is not None:
            price = f'<div class="cmp">{esc(L("avg_price"))}: <b>{money(e["avg_import_price"], 3)}</b>/kWh</div>'
        P.add("cost", L("s_cost"), "receipt", f'''{P.kicker(L("s_cost"), "receipt")}
<div class="split"><div><h2>{head}</h2>
<div class="hero" style="margin-top:22px">{money(abs(tot))}<small>{esc(L("net_cost"))}</small></div>{price}
<div style="margin-top:28px">{tr}</div></div>
<div>{bill}<p class="note" style="margin-top:14px">{esc(note)}</p></div></div>''')

    # ---------------------------------------------------------------- solar
    if e.get("solar") and e["solar"] > 1:
        sol = e["solar"]
        self_used = max(0.0, sol - e.get("export", 0)) / sol
        head = L("h_solar", share=L.pct(self_used))
        stats = [P.stat(L("solar"), kwh(sol), sol, _get(lambda x: x["energy"]["solar"])),
                 P.stat(L("self_used"), L.pct(self_used))]
        wx = d.get("weather") or {}
        if wx.get("sun_h"):
            c = ""
            if g(wx, "normal", "sun_h"):
                c = f'<div class="c">{esc(L("vs_normal"))} {L.num(wx["normal"]["sun_h"])} h</div>'
            stats.append(f'<div class="stat"><div class="l">{esc(L("sun_hours"))}</div><div class="v">{L.num(wx["sun_h"])}<small>h</small></div>{c}</div>')
        tr = trend(L, P.series13(_get(lambda x: x["energy"]["solar"])), L("trend_solar"), lambda v: kwh(v))
        P.add("solar", L("s_solar"), "sun", f'''{P.kicker(L("s_solar"), "sun")}
<div class="split"><div><h2>{head}</h2><div class="hero" style="margin-top:22px">{L.num(sol)}<small>kWh</small></div></div>
<div><div class="stats">{"".join(stats)}</div><div style="margin-top:28px">{tr}</div></div></div>''')

    # ---------------------------------------------------------------- batteries
    b = d.get("batteries")
    if b and b.get("charge", 0) > 1:
        head = L("h_battery", v=kwh(b["charge"]), back=kwh(b["discharge"]))
        rows = "".join(
            f'<tr><td>{esc(x["name"])}</td><td>{L.num(x["charge"], 1)}</td><td>{L.num(x["discharge"], 1)}</td><td>{L.pct(x["efficiency"])}</td></tr>'
            for x in b["units"])
        if len(b["units"]) > 1:
            rows += f'<tr><td><b>{esc(L("total"))}</b></td><td><b>{L.num(b["charge"], 1)}</b></td><td><b>{L.num(b["discharge"], 1)}</b></td><td><b>{L.pct(b["efficiency"])}</b></td></tr>'
        P.add("battery", L("s_battery"), "battery", f'''{P.kicker(L("s_battery"), "battery")}
<h2>{head}</h2>
<div class="tbl"><table><thead><tr><th></th><th>{esc(L("charged"))} (kWh)</th><th>{esc(L("discharged"))} (kWh)</th><th>{esc(L("efficiency"))}</th></tr></thead>
<tbody>{rows}</tbody></table></div>''')

    # ---------------------------------------------------------------- devices
    dv = d.get("devices")
    if dv and e:
        items = [x for x in dv["items"] if not x["no_data"] and not x.get("parent")]
        missing = [x["name"] for x in dv["items"] if x["no_data"]]
        rows = [(x["name"], x["kwh"], x.get("value"), x.get("partial"), x["stat"]) for x in items]
        rows.append((L("untracked"), dv["untracked"], None, False, None))
        rows.sort(key=lambda r: -r[1])
        main, small = rows[:10], rows[10:]
        if small:
            main.append((L("others", n=len(small)), sum(r[1] for r in small), None, False, None))
        mx = max((r[1] for r in main), default=1) or 1
        cons = e["consumption"] or 1
        lines = [f'<div class="r h"><div>{esc(L("device"))}</div><div class="t" style="background:none"></div><div class="v">kWh</div><div class="p">{esc(L("share"))}</div><div class="e">{esc(L("value"))}</div></div>']
        for name, k, val, partial, stat in main:
            muted = " muted" if stat is None else ""
            badge = f'<small>{esc(L("partial"))}</small>' if partial else ""
            tip = ""
            if stat:
                a = P.ref_avg(lambda x, s=stat: next(i["kwh"] for i in x["devices"]["items"] if i["stat"] == s))
                if a:
                    tip = f' data-tip="{esc(L("avg"))} {esc(kwh(a))}"'
            lines.append(f'<div class="r"{tip}><div class="lb">{esc(name)}{badge}</div><div class="t"><div class="f{muted}" style="width:{k / mx * 100:.1f}%"></div></div>'
                         f'<div class="v">{L.num(k)}</div><div class="p">{L.pct(k / cons)}</div><div class="e">{money(val) if val is not None else ""}</div></div>')
        top = next((r for r in rows if r[4]), None)
        head = L("h_devices", name=esc(top[0]), share=L.pct(top[1] / cons)) if top else ""
        note = L("dev_note", names=", ".join(missing)) if missing else L("dev_note", names="–").split(". ")[0] + "."
        P.add("devices", L("s_devices"), "plug", f'''{P.kicker(L("s_devices"), "plug")}
<h2>{head}</h2><div class="rank">{"".join(lines)}</div><p class="note">{esc(note)}</p>''')

    # ---------------------------------------------------------------- daily rhythm
    if e.get("by_hour_w") and any(e["by_hour_w"]):
        w = e["by_hour_w"]
        peak = max(range(24), key=lambda i: w[i] or 0)
        stats = []
        if e.get("base_load_w"):
            stats.append(P.stat(L("base_load"), f'{L.num(e["base_load_w"])} W', e["base_load_w"], _get(lambda x: x["energy"]["base_load_w"])))
        if e.get("peak"):
            t = dt.datetime.fromisoformat(e["peak"]["at"])
            stats.append(f'<div class="stat"><div class="l">{esc(L("peak"))}</div><div class="v">{L.num(e["peak"]["kw"], 1)}<small>kW</small></div>'
                         f'<div class="c">{t.day} {esc(L.month_short(t.month))} {t:%H}:00</div></div>')
        P.add("rhythm", L("s_rhythm"), "clock", f'''{P.kicker(L("s_rhythm"), "clock")}
<h2>{L("h_rhythm", hour=f"{peak:02d}:00")}</h2>
<div><div class="wide">{hour_profile(L, w)}</div><div class="narrow">{hour_profile(L, w, 420, 240)}</div></div>
<div class="stats">{"".join(stats)}</div>
<p class="note">{esc(L("rhythm_note"))} {esc(L("base_note"))}</p>''')

    # ---------------------------------------------------------------- weather
    wx = d.get("weather")
    if wx and wx.get("temp") is not None:
        n = g(wx, "normal", "temp")
        if n is not None:
            delta = wx["temp"] - n
            thr = 0.5 if tu == "°C" else 0.9
            key = "h_weather_normal" if abs(delta) < thr else ("h_weather_warm" if delta > 0 else "h_weather_cold")
            head = L(key, month=esc(mname), delta=f"{L.num(abs(delta), 1)}{tu}")
        else:
            head = L("h_weather_plain", v=f"{L.num(wx['temp'], 1)}{tu}")
        pu = wx.get("precip_unit", "mm")
        stats = [f'<div class="stat"><div class="l">{esc(L("avg_temp"))}</div><div class="v">{L.num(wx["temp"], 1)}<small>{tu}</small></div>'
                 + (f'<div class="c">{esc(L("vs_normal"))} {L.num(n, 1)}{tu}</div>' if n is not None else "") + '</div>',
                 f'<div class="stat"><div class="l">{esc(L("coldest"))} / {esc(L("warmest"))}</div><div class="v">{L.num(wx["min"], 1)} / {L.num(wx["max"], 1)}<small>{tu}</small></div></div>',
                 f'<div class="stat"><div class="l">{esc(L("rain"))}</div><div class="v">{L.num(wx["precip"], 0 if pu == "mm" else 1)}<small>{pu}</small></div>'
                 + (f'<div class="c">{esc(L("vs_normal"))} {L.num(wx["normal"]["precip"], 0 if pu == "mm" else 1)} {pu}</div>' if g(wx, "normal", "precip") is not None else "") + '</div>',
                 f'<div class="stat"><div class="l">{esc(L("frost_days"))}</div><div class="v">{wx["frost_days"]}</div></div>'
                 if wx["frost_days"] or m in (11, 12, 1, 2, 3) else
                 f'<div class="stat"><div class="l">{esc(L("summer_days"))}</div><div class="v">{wx["summer_days"]}</div></div>',
                 P.stat(L("degree_days"), L.num(wx["degree_days"]), wx["degree_days"], _get(lambda x: x["weather"]["degree_days"]))]
        legend = (f'<span><i style="background:var(--s1);opacity:.35"></i>{esc(L("band"))}</span><span><i style="background:var(--s1)"></i>{esc(L("mean_line"))}</span>'
                  + (f'<span><i style="background:var(--hi)"></i>{esc(L("normal_line"))}</span>' if n is not None else ""))
        note = L("weather_note_sensor") if wx.get("source") == "sensor" else L("weather_note")
        P.add("weather", L("s_weather"), "cloud", f'''{P.kicker(L("s_weather"), "cloud")}
<h2>{head}</h2>
<div><div class="wide">{temp_chart(L, wx["daily"], n, tu)}</div><div class="narrow">{temp_chart(L, wx["daily"], n, tu, 420, 240, 14)}</div>
<div class="legend">{legend}</div></div>
<div class="stats">{"".join(stats)}</div><p class="note">{esc(note)}</p>''')

    # ---------------------------------------------------------------- indoor
    ind = d.get("indoor")
    if ind and ind.get("temp") is not None:
        head = L("h_indoor", v=f'{L.num(ind["temp"], 1)}{tu}', warm=esc(ind.get("warmest") or "–"))
        rows, floor = [], object()
        has_h = any("humidity" in a for a in ind["areas"])
        has_c = any("co2" in a for a in ind["areas"])
        floors = {a.get("floor") for a in ind["areas"]}
        for a in ind["areas"]:
            if len(floors) > 1 and a.get("floor") != floor:
                floor = a.get("floor")
                rows.append(f'<tr class="fl"><td colspan="4">{esc(floor or "–")}</td></tr>')
            t = f'{L.num(a["temp"], 1)}{tu}<span class="sm">{L.num(a["temp_min"], 0)}–{L.num(a["temp_max"], 0)}</span>' if "temp" in a else "–"
            h = (f'{L.num(a["humidity"])}%' + (f'<span class="sm">{a["humid_hours"]} {esc(L("humid_hours"))}</span>' if a.get("humid_hours") else "")) if "humidity" in a else ""
            c = (f'{L.num(a["co2"])} ppm' + (f'<span class="sm">{L.pct(a["co2_over_1000"])} {esc(L("co2_high"))}</span>' if a.get("co2_over_1000") else "")) if "co2" in a else ""
            rows.append(f'<tr><td>{esc(a["name"])}</td><td>{t}</td>' + (f"<td>{h}</td>" if has_h else "") + (f"<td>{c}</td>" if has_c else "") + "</tr>")
        th = f'<th>{esc(L("room"))}</th><th>{esc(L("temp"))}</th>' + (f'<th>{esc(L("humidity"))}</th>' if has_h else "") + (f'<th>{esc(L("co2"))}</th>' if has_c else "")
        P.add("indoor", L("s_indoor"), "thermo", f'''{P.kicker(L("s_indoor"), "thermo")}
<h2>{head}</h2>
<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<p class="note">{esc(L("indoor_note"))}</p>''')

    # ---------------------------------------------------------------- water & gas
    for kind, ic in (("water", "drop"), ("gas", "flame")):
        x = d.get(kind)
        if not x or x["amount"] <= 0:
            continue
        unit = x["unit"]
        if kind == "water" and unit == "L":
            big, bigu = x["amount"] / 1000, "m³"
            amount = f"{L.num(big, 1)} m³"
            pd = f'{L.num(x["per_day"])} L'
        else:
            big, bigu = x["amount"], unit
            amount = f"{L.num(big, 1)} {unit}"
            pd = f'{L.num(x["per_day"], 1)} {unit}'
        head = L("h_water", v=amount, pd=pd) if kind == "water" else L("h_gas", v=amount)
        stats = [P.stat(L(kind), amount, x["amount"], _get(lambda z, k=kind: z[k]["amount"]), fmt=lambda v, u=unit: (L.num(v / 1000, 1) + " m³") if u == "L" else f"{L.num(v, 1)} {u}"),
                 P.stat(L("per_day"), pd)]
        if x.get("cost") is not None:
            stats.append(P.stat(L(f"{kind}_cost"), money(x["cost"], 2)))
        tr = trend(L, P.series13(_get(lambda z, k=kind, u=unit: z[k]["amount"] / (1000 if u == "L" else 1))), L(f"trend_{kind}"),
                   lambda v: L.num(v, 1))
        P.add(kind, L(f"s_{kind}"), ic, f'''{P.kicker(L(f"s_{kind}"), ic)}
<div class="split"><div><h2>{head}</h2><div class="hero" style="margin-top:22px">{L.num(big, 1)}<small>{bigu}</small></div></div>
<div><div class="stats">{"".join(stats)}</div><div style="margin-top:28px">{tr}</div></div></div>''')

    # ---------------------------------------------------------------- about
    src = []
    if e:
        src.append(L("src_energy"))
    if wx:
        src.append(L("src_weather"))
    if ind:
        n_s = sum(a.get("temp_sensors", 0) + a.get("humidity_sensors", 0) + a.get("co2_sensors", 0) for a in ind["areas"])
        src.append(L("src_sensors", n=n_s, a=len(ind["areas"])))
    notes = []
    if e.get("glitch_hours"):
        notes.append(L("glitches", list=", ".join(f"{k} ({v}×)" for k, v in e["glitch_hours"].items())))
    if e.get("partial_from"):
        notes.append(L("partial_month", d=e["partial_from"]))
    months = sorted(docs)
    i = months.index(ym)
    prv = months[i - 1] if i > 0 else None
    nxt = months[i + 1] if i < len(months) - 1 else None

    def mlabel(x):
        return f"{L.month(int(x[5:]))} {x[:4]}"

    foot = '<div class="mfoot">'
    if prv:
        foot += f'<a href="#" data-go="{prv}"><span>{esc(L("prev"))}</span><b>{esc(mlabel(prv))}</b></a>'
    if nxt:
        foot += f'<a href="#" class="nx" data-go="{nxt}"><span>{esc(L("next"))}</span><b>{esc(mlabel(nxt))}</b></a>'
    foot += "</div>"
    tn = L.t["themes"]
    themes = "".join(f'<button data-t="{t}" onclick="hirTheme(\'{t}\')">{esc(tn[t])}</button>' for t in ("auto", "light", "dark", "night", "mono"))
    gen = dt.datetime.fromisoformat(d["generated"])
    P.add("about", L("s_about"), "info", f'''{P.kicker(L("s_about"), "info")}
<div><div class="l" style="font-size:13px;color:var(--mut)">{esc(L("about_sources"))}</div>
<ul class="src">{"".join(f"<li>{esc(s)}</li>" for s in src)}</ul></div>
{"".join(f'<p class="note">{esc(n)}</p>' for n in notes)}
<p class="note">{esc(L("generated", d=f"{gen.day} {L.month(gen.month)} {gen.year}"))} · {esc(L("made_with"))}</p>
<div class="themes">{esc(L("theme"))}: {themes}</div>
{foot}''')

    # ---------------------------------------------------------------- page
    nav = "".join(f'<a href="#{sid}" data-l="{esc(lab)}"></a>' for sid, lab, _ in P.slides)
    opts = "".join(f'<option value="{x}"{" selected" if x == ym else ""}>{esc(mlabel(x))}</option>' for x in reversed(months))
    top = (f'<div class="topbar"><a href="#" data-go="index">{esc(L("title"))}</a><div class="mnav">'
           + (f'<a href="#" class="prev" data-go="{prv}">‹</a>' if prv else "")
           + f'<select class="msel" aria-label="month">{opts}</select>'
           + (f'<a href="#" class="next" data-go="{nxt}">›</a>' if nxt else "") + "</div></div>")
    title = f"{L('title')} · {mname} {y}"
    return (f'<!doctype html><html lang="{L.code}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(title)}</title>{THEME_HEAD}<style>{CSS}</style></head><body data-ym="{ym}">'
            f'<div class="bar"></div>{top}<nav class="nav">{nav}</nav>{"".join(s for _, _, s in P.slides)}<div id="tip"></div>'
            f'<script>{JS}</script></body></html>')


# ============================================================================ index
def render_index(docs: dict[str, dict], lang: str = "en", home_name: str | None = None, currency: str = "EUR") -> str:
    L = Lang(lang, currency)
    rows, year = [], None
    for ym in sorted(docs, reverse=True):
        d = docs[ym]
        if ym[:4] != year:
            year = ym[:4]
            rows.append(f'<div class="y">{year}</div>')
        e = d.get("energy") or {}
        a = f'{L.num(e["consumption"])} kWh' if e.get("consumption") is not None else ""
        b = L.money(e["total_cost"]) if e.get("total_cost") is not None else ""
        rows.append(f'<a href="#" data-go="{ym}"><b>{esc(L.month(int(ym[5:])))}</b><span>{a}</span><span>{b}</span></a>')
    body = "".join(rows) if rows else f'<p class="note">{esc(L("index_empty"))}</p>'
    sub = esc(home_name) if home_name else ""
    return (f'<!doctype html><html lang="{L.code}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(L("title"))}</title>{THEME_HEAD}<style>{CSS} html{{scroll-snap-type:none}}</style></head><body>'
            f'<section class="slide" style="align-content:start"><div class="kicker">{icon("house")}{esc(L("title"))}{(" · " + sub) if sub else ""}</div>'
            f'<h2>{esc(L("index_title"))}</h2><div class="idx">{body}</div></section><div class="bar"></div><div id="tip"></div><script>{JS}</script></body></html>')


def months_json(docs: dict[str, dict]) -> str:
    return json.dumps(sorted(docs))
