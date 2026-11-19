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
  --s1:#2a78d6;--s3:#1baf7a;--s4:#d99400;--s5:#8a6fd1;--hi:#d9602b;--cost:#6b6e76;
  --serif:"Fraunces","Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  --sans:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]):not([data-theme="night"]):not([data-theme="mono"]){
  color-scheme:dark;--bg:#0f1115;--paper:#171a21;--ink:#f0efec;--ink2:#c3c2b7;--mut:#8f8f8a;--line:#2a2e36;
  --s1:#4a90e2;--s3:#22a777;--s4:#d29a1c;--s5:#9b85e6;--hi:#e8743f;--cost:#9a9ca3}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0f1115;--paper:#171a21;--ink:#f0efec;--ink2:#c3c2b7;--mut:#8f8f8a;--line:#2a2e36;
  --s1:#4a90e2;--s3:#22a777;--s4:#d29a1c;--s5:#9b85e6;--hi:#e8743f;--cost:#9a9ca3}
:root[data-theme="night"]{color-scheme:dark;--bg:#0a1020;--paper:#111a2e;--ink:#eef2fa;--ink2:#b9c3d6;--mut:#7c88a0;--line:#1f2a42;
  --s1:#3f86e0;--s3:#1fa37a;--s4:#d9a62b;--s5:#8f7be0;--hi:#c4801c;--cost:#8a96ad}
:root[data-theme="mono"]{color-scheme:light;--bg:#f6f6f4;--paper:#fff;--ink:#0b0b0b;--ink2:#4a4a48;--mut:#85857f;--line:#e2e2df;
  --s1:#3d3d3b;--s3:#2f5bea;--s4:#9a9a96;--s5:#6e6e6a;--hi:#2f5bea;--cost:#a3a39e;--serif:var(--sans)}
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
.stat .v small{font-family:var(--sans);font-size:13px;font-weight:500;color:var(--ink2);margin-left:4px;letter-spacing:0;white-space:nowrap;display:inline-block}
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
.nav{position:fixed;right:12px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:4px;z-index:5;
  max-height:calc(100svh - 120px);padding:6px 4px;border-radius:14px;background:color-mix(in srgb,var(--bg) 70%,transparent)}
.nav a{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;position:relative;color:var(--mut);opacity:.75;
  transition:color .15s,opacity .15s,background .15s}
.nav a .ic{width:17px;height:17px}
.nav a:hover{opacity:1;color:var(--ink)}
.nav a.on{opacity:1;color:var(--hi);background:color-mix(in srgb,var(--hi) 14%,transparent)}
@media (max-height:640px){.nav a{width:22px;height:22px}.nav a .ic{width:14px;height:14px}.nav{gap:2px}}
.nav a:hover:after{content:attr(data-l);position:absolute;right:36px;top:50%;transform:translateY(-50%);white-space:nowrap;
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
.topbar a{white-space:nowrap}
.topbar .home .short{display:none}
.topbar .home .short .ic{width:15px;height:15px;vertical-align:-3px}
@media (max-width:480px){.topbar .home .full{display:none}.topbar .home .short{display:inline}}
.topbar .hmenu{font:600 15px var(--sans);line-height:1;color:var(--ink2);background:color-mix(in srgb,var(--paper) 85%,transparent);
  border:1px solid var(--line);border-radius:999px;padding:5px 11px;cursor:pointer}
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
.notes{display:grid;gap:8px}
.story{max-width:40em}
.story p{font-family:var(--serif);font-size:clamp(17px,1.45vw,20px);line-height:1.5;margin:0 0 .8em;color:var(--ink2)}
.story p:first-child{font-size:clamp(21px,2vw,27px);line-height:1.38;color:var(--ink)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:22px 32px}
.card{border-top:2px solid var(--ink);padding-top:12px;display:grid;gap:8px;align-content:start}
.card .cl{font-size:13px;color:var(--mut);letter-spacing:.02em}
.card .cv{font-family:var(--serif);font-size:clamp(30px,3.4vw,44px);font-weight:500;letter-spacing:-.02em;line-height:1.05}
.card .cv small{font-family:var(--sans);font-size:14px;font-weight:500;color:var(--ink2);margin-left:6px;letter-spacing:0}
.card .cmp{font-size:13px;margin:0;min-height:1.2em}
.card .trend{max-width:none}
.card .trend .cap{display:none}
svg.days{margin-top:2px}
ul.src{margin:0;padding-left:1.1em;color:var(--ink2);font-size:14.5px}
#tip{position:fixed;pointer-events:none;background:var(--paper);color:var(--ink);border:1px solid var(--line);border-radius:8px;
  padding:6px 10px;font-size:13px;box-shadow:0 6px 24px rgba(0,0,0,.12);opacity:0;transition:opacity .1s;z-index:9;max-width:280px}
.hit{fill:transparent}
.hit[data-go]{cursor:pointer}
.hit[data-go]:hover{fill:color-mix(in srgb,var(--ink) 7%,transparent)}
.idx{display:grid;gap:0;max-width:900px}
.idx a{display:grid;grid-template-columns:1fr auto auto;gap:24px;align-items:baseline;text-decoration:none;padding:14px 0;border-bottom:1px solid var(--line)}
.idx a b{font-family:var(--serif);font-size:clamp(22px,2.6vw,30px);font-weight:500}
.idx a span{color:var(--ink2);font-variant-numeric:tabular-nums}
.idx a:hover b{color:var(--hi)}
.idx .y{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);padding-top:26px}
"""

# Fonts ship with the integration (SIL Open Font License, see frontend/fonts): nothing is loaded from elsewhere.
FONT_BASE = "/home_in_review_static/fonts"
FONT_FACES = (
    ("Fraunces", "italic", "400 700", "fraunces-italic-latin-ext.woff2", "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF"),
    ("Fraunces", "italic", "400 700", "fraunces-italic-latin.woff2", "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
    ("Fraunces", "normal", "400 700", "fraunces-normal-latin-ext.woff2", "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF"),
    ("Fraunces", "normal", "400 700", "fraunces-normal-latin.woff2", "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
    ("Inter", "normal", "400 700", "inter-normal-latin-ext.woff2", "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF"),
    ("Inter", "normal", "400 700", "inter-normal-latin.woff2", "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
)
THEMES = ("auto", "light", "dark", "night", "mono")


def font_css() -> str:
    return "".join(f"@font-face{{font-family:'{f}';font-style:{st};font-weight:{w};font-display:swap;"
                   f"src:url('{FONT_BASE}/{n}') format('woff2');unicode-range:{r}}}" for f, st, w, n, r in FONT_FACES)


def theme_head(default: str = "auto") -> str:
    """Theme before first paint: ?theme= / #theme=, else the viewer's own choice, else the configured default."""
    default = default if default in THEMES else "auto"
    return ("<script>(()=>{const r=document.documentElement;let t=new URLSearchParams(location.search).get('theme');"
            "const h=/theme=([a-z]+)/.exec(location.hash);if(h)t=h[1];if(!t){try{t=localStorage.getItem('hir-theme')}catch(e){}}"
            f"if(!t)t='{default}';if(t&&t!=='auto')r.dataset.theme=t;}})()</script>")

JS = r"""
window.hirSlide=()=>{let b='',best=1e9;document.querySelectorAll('.slide').forEach(x=>{const d=Math.abs(x.getBoundingClientRect().top);if(d<best){best=d;b=x.id}});return b};
/* Go to another report. ``s`` is the slide to open there (the same topic), '' for the top. */
window.hirGo=(f,s)=>{if(s===undefined)s=f==='index'?'':hirSlide();
 if(window.parent!==window)parent.postMessage({homeInReview:f,slide:s},location.origin);else location.href='./'+f+'.html'+(s?'#s='+s:'')};
document.addEventListener('click',e=>{const a=e.target.closest&&e.target.closest('[data-go]');if(!a)return;e.preventDefault();
 const sl=a.closest('.slide');hirGo(a.dataset.go,a.closest('.mfoot')?'':(sl&&!sl.classList.contains('cover')?sl.id:undefined))});
/* Opened for a given topic: start at that slide. */
(()=>{const m=/(?:^|[#&])s=([a-z]+)/.exec(location.hash);if(!m)return;const el=document.getElementById(m[1]);
 if(el)window.scrollTo({top:el.offsetTop,behavior:'instant'})})();
(()=>{const b=document.querySelector('.hmenu');if(!b||window.parent===window)return;const set=v=>{b.hidden=!v};
 set(/(^|[#&])menu\b/.test(location.hash));addEventListener('message',e=>{if(e.source===parent&&e.origin===location.origin&&e.data&&'hirNarrow' in e.data)set(!!e.data.hirNarrow)});
 b.onclick=()=>parent.postMessage({homeInReview:'menu'},location.origin)})();
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
    "quote": '<path d="M6 7h4v4c0 3-1.3 5-4 6M14 7h4v4c0 3-1.3 5-4 6"/>',
    "car": '<path d="M3.5 16.5v-3.5l2-5a2 2 0 0 1 1.9-1.3h9.2a2 2 0 0 1 1.9 1.3l2 5v3.5"/><path d="M3.5 13h17"/><circle cx="7.5" cy="16.5" r="1.8"/><circle cx="16.5" cy="16.5" r="1.8"/>',
    "heatpump": '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="10" cy="12" r="4"/><path d="M10 8.5c1.5 1.2 1.5 2.3 0 3.5s-1.5 2.3 0 3.5"/><path d="M17 9v6"/>',
    "tiles": '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><path d="M16.5 13v7M13 16.5h7"/>',
    "cloud": '<path d="M7 18h10a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.2 9.2 4.5 4.5 0 0 0 7 18z"/>',
}


def topbar_left(L: Lang) -> str:
    """Left side of the top bar: the sidebar menu button (only shown inside the panel on narrow screens) and home."""
    return (f'<div class="mnav"><button class="hmenu" type="button" aria-label="{esc(L("menu"))}" hidden>☰</button>'
            f'<a href="#" data-go="index" class="home" aria-label="{esc(L("title"))}"><span class="full">{esc(L("title"))}</span>'
            f'<span class="short">{icon("house")}</span></a></div>')


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
        # Bars of other months with a report open that month; the current month (the accent bar) has no link.
        go = f' data-go="{ym}"' if v is not None and not last else ""
        out.append(f'<rect class="hit" x="{x:.1f}" y="0" width="{bw:.1f}" height="{H}"{go} data-tip="{esc(L.month_short(m))} {ym[:4]}: {esc(tipv)}"/>')
        lab = L.month_short(m)[0].upper() + (("’" + ym[2:4]) if (first or last) else "")
        out.append(f'<text x="{x + bw / 2:.1f}" y="{H - 3}" class="ax" text-anchor="middle"{" font-weight=\"600\"" if (first or last) else ""}>{lab}</text>')
    out.append("</svg></div>")
    return "".join(out)


def day_sources(x: dict) -> tuple[float, float, float]:
    """Where a day's electricity came from: grid, solar used directly, battery."""
    bat = x.get("bat_out", 0.0)
    solar_direct = max(0.0, x.get("load", 0.0) - x["import"] - bat) if x.get("solar") else 0.0
    return x["import"], solar_direct, bat


def bar_path(x: float, y: float, w: float, h: float, fill: str, rounded: str | None, r: float = 3) -> str:
    """A bar (segment) with only its outer end rounded: "top", "bottom" (bars below the axis) or None (a middle
    segment of a stack)."""
    if rounded is None:
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"/>'
    r = min(r, w / 2, h)
    if rounded == "top":
        d = (f"M{x:.1f},{y + h:.1f}V{y + r:.1f}Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f}H{x + w - r:.1f}"
             f"Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f}V{y + h:.1f}Z")
    else:
        d = (f"M{x:.1f},{y:.1f}V{y + h - r:.1f}Q{x:.1f},{y + h:.1f} {x + r:.1f},{y + h:.1f}H{x + w - r:.1f}"
             f"Q{x + w:.1f},{y + h:.1f} {x + w:.1f},{y + h - r:.1f}V{y:.1f}Z")
    return f'<path d="{d}" fill="{fill}"/>'


def daily_energy_chart(L: Lang, daily: list[dict], W=1000, H=340, every=7) -> str:
    """Per day: what the house used, stacked by source (grid, solar directly, battery); returned to the grid below."""
    if not daily:
        return ""
    pl, top, bot = 44, 14, 26
    ups = [sum(day_sources(x)) for x in daily]
    step = nice_step(max(max(ups), max(x["export"] for x in daily)), 3)
    up = step * max(1, math.ceil(max(ups) / step))
    dn = step * math.ceil(max(x["export"] for x in daily) / step)
    span = up + dn
    y0 = top + (H - top - bot) * up / span
    sc = (H - top - bot) / span
    bw = (W - pl) / len(daily)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(L("kwh_per_day"))}">']
    for v in (up, -dn) if dn else (up,):
        y = y0 - v * sc
        out.append(f'<line x1="{pl}" x2="{W}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/><text x="{pl - 8}" y="{y + 4:.1f}" class="ax" text-anchor="end">{L.num(abs(v))}</text>')
    out.append(f'<line x1="{pl}" x2="{W}" y1="{y0:.1f}" y2="{y0:.1f}" stroke="var(--ink2)" stroke-width="1"/>')
    for i, x in enumerate(daily):
        px = pl + i * bw
        w = max(bw - 3, 2)
        grid, solar, bat = day_sources(x)
        y = y0
        parts = [(v * sc, col) for v, col in ((grid, "var(--s1)"), (solar, "var(--s4)"), (bat, "var(--s5)")) if v * sc > 0.3]
        for n, (h, col) in enumerate(parts):
            # only the outer end of the stack is rounded, so the seams between sources stay straight
            out.append(bar_path(px + 1.5, y - h, w, h, col, rounded="top" if n == len(parts) - 1 else None))
            y -= h
        hd = x["export"] * sc
        if hd > 0.3:
            out.append(bar_path(px + 1.5, y0, w, hd, "var(--s3)", rounded="bottom"))
        d = dt.date.fromisoformat(x["d"])
        tip = f'{d.day} {L.month_short(d.month)} · {L("imported")} {L.num(grid, 1)}'
        if x.get("solar"):
            tip += f' · {L("solar_direct")} {L.num(solar, 1)}'
        if bat:
            tip += f' · {L("from_battery")} {L.num(bat, 1)}'
        tip += f' · {L("exported")} {L.num(x["export"], 1)} kWh'
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


def day_bars(L: Lang, period: dict, daily: list | None, fmt, W=420, H=64) -> str:
    """A small bar per day of the month (weekends slightly lighter)."""
    if not daily or not any(v for v in daily if v):
        return ""
    vals = [v or 0 for v in daily]
    hi = max(vals) or 1
    bw = W / len(vals)
    first = dt.date(period["year"], period["month"], 1)
    out = [f'<svg class="days" viewBox="0 0 {W} {H + 14}" role="img">']
    for i, v in enumerate(vals):
        day = first + dt.timedelta(days=i)
        h = max(v / hi * H, 1.2 if v else 0)
        op = ".55" if day.weekday() >= 5 else "1"
        if h:
            out.append(f'<rect x="{i * bw + bw * .15:.1f}" y="{H - h:.1f}" width="{bw * .7:.1f}" height="{h:.1f}" rx="2" fill="var(--s1)" opacity="{op}"/>')
        out.append(f'<rect class="hit" x="{i * bw:.1f}" y="0" width="{bw:.1f}" height="{H + 14}" data-tip="{day.day} {esc(L.month_short(day.month))}: {esc(fmt(daily[i]) if daily[i] is not None else L("no_data"))}"/>')
        if day.day in (1, 15) or i == len(vals) - 1:
            out.append(f'<text x="{i * bw + bw / 2:.1f}" y="{H + 12}" class="ax" text-anchor="middle">{day.day}</text>')
    out.append("</svg>")
    return "".join(out)


def gas_scatter(L: Lang, pts: list[tuple[float, float, str]], base: float | None, k: float | None, unit: str,
                tu: str, W=1000, H=210) -> str:
    """Gas per day against degree days, with the line base + k × degree days when the split is known."""
    if len(pts) < 5:
        return ""
    pl, top, bot = 54, 12, 30
    xmax = max(p[0] for p in pts) or 1
    ymax = max(p[1] for p in pts) or 1
    sx = nice_step(xmax, 4)
    xmax = sx * math.ceil(xmax / sx)
    sy = nice_step(ymax, 3)
    ymax = sy * math.ceil(ymax / sy)
    X = lambda v: pl + v / xmax * (W - pl - 10)  # noqa: E731
    Y = lambda v: top + (1 - v / ymax) * (H - top - bot)  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(L("gas_scatter"))}">']
    t = 0.0
    while t <= ymax + 1e-9:
        out.append(f'<line x1="{pl}" x2="{W}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/><text x="{pl - 8}" y="{Y(t) + 4:.1f}" class="ax" text-anchor="end">{L.num(t, 0 if float(sy).is_integer() else 1)}</text>')
        t += sy
    t = 0.0
    while t <= xmax + 1e-9:
        out.append(f'<text x="{X(t):.1f}" y="{H - 10}" class="ax" text-anchor="middle">{L.num(t, 0 if float(sx).is_integer() else 1)}</text>')
        t += sx
    if base is not None and k:
        # End the line where it leaves the chart, so its slope stays right.
        x_end = min(xmax, (ymax - base) / k) if base < ymax else 0.0
        out.append(f'<line x1="{X(0):.1f}" y1="{Y(base):.1f}" x2="{X(x_end):.1f}" y2="{Y(base + k * x_end):.1f}" stroke="var(--hi)" stroke-width="2" stroke-dasharray="6 5"/>')
        out.append(f'<line x1="{X(0):.1f}" y1="{Y(base):.1f}" x2="{X(xmax):.1f}" y2="{Y(base):.1f}" stroke="var(--s3)" stroke-width="1.5" stroke-dasharray="2 4"/>')
    for x, y, day in pts:
        dd = dt.date.fromisoformat(day)
        tip = f"{dd.day} {L.month_short(dd.month)}: {L.num(y, 2)} {unit} · {L.num(x, 1)} {L('degree_days').lower()}"
        out.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="5" fill="var(--s1)" opacity=".8" data-tip="{esc(tip)}"/>')
    out.append(f'<text x="{W}" y="{top + 2}" class="ax" text-anchor="end">↓ {esc(unit)} · {esc(L("degree_days"))} →</text></svg>')
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
    # the unit may contain digits (kWh/100 km, m³) but must not start with one
    if sep and num and unit and any(c.isdigit() for c in num) and not unit[0].isdigit():
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
            except (KeyError, TypeError, IndexError, StopIteration):
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
            except (KeyError, TypeError, IndexError, StopIteration):
                v = None
            if v is not None:
                mn = self.L.month(int(self.ym[5:]))
                return v, {"ref": self.L("ref_ly", month=mn), "ref2": self.L("ref2_ly", month=mn), "kind": "ly"}
        return self.ref_avg(fn), {"ref": self.L("ref_avg"), "ref2": self.L("ref2_avg"), "kind": "avg"}

    def delta(self, cur, fn, unit: str, nd: int = 1) -> tuple[str, str] | None:
        """Absolute difference with the reference (same month last year, else 12-month average), for seasonal
        figures like indoor temperature where a percentage means little. Returns (short text, tooltip)."""
        if cur is None:
            return None
        ref, refs = self.compare(fn)
        if ref is None:
            return None
        d = cur - ref
        label = self.L("last_year") if refs.get("kind") == "ly" else self.L("avg")
        tip = f"{label}: {self.L.num(ref, nd)}{unit}"
        if abs(d) < 0.5 * 10 ** -nd * 2:
            return "=", tip
        return f'{"▲" if d > 0 else "▼"} {self.L.num(abs(d), nd)}{unit}', tip

    def stat_vs(self, label: str, value: str, cur, fn, unit: str, nd: int = 1) -> str:
        """A stat whose comparison line uses the seasonal reference (see delta)."""
        c = ""
        ref, refs = self.compare(fn) if cur is not None else (None, {})
        if ref is not None:
            name = self.L("last_year") if refs.get("kind") == "ly" else self.L("avg")
            d = cur - ref
            arrow = "" if abs(d) < 10 ** -nd else f' · {"▲" if d > 0 else "▼"} {self.L.num(abs(d), nd)}{unit}'
            c = f'<div class="c">{esc(name)} {self.L.num(ref, nd)}{esc(unit)}{arrow}</div>'
        return f'<div class="stat"><div class="l">{esc(label)}</div><div class="v">{split_unit(value)}</div>{c}</div>'

    def series13(self, fn) -> list[tuple[str, float | None]]:
        out = []
        for i in range(12, -1, -1):
            m = prev_ym(self.ym, i)
            d = self.docs.get(m)
            try:
                out.append((m, fn(d) if d else None))
            except (KeyError, TypeError, IndexError, StopIteration):
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
        self.slides.append((sid, label, f'<section class="slide {cls}" id="{sid}">{mark}{body}<div class="pg">{n:02d}</div></section>', wm))

    def kicker(self, label: str, ic: str) -> str:
        return f'<div class="kicker">{icon(ic)}<b>{len(self.slides) + 1:02d}</b>{esc(label)}</div>'


def _get(fn):
    def inner(d):
        try:
            return fn(d)
        except (KeyError, TypeError, IndexError, StopIteration):
            return None
    return inner


# ============================================================================ month report
def render_month(ym: str, docs: dict[str, dict], lang: str = "en", home_name: str | None = None,
                 start_month: int = 1, theme: str = "auto") -> str:
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
        bill = e.get("bill_total", e["total_cost"])
        lbl = L("cost_with_water") if e.get("water_cost") is not None else L("net_cost")
        figs.append(f'<div>{icon("euro")}<b>{money(bill)}</b><span>{esc(lbl)}</span></div>')
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

    # ---------------------------------------------------------------- AI summary (optional)
    if d.get("story"):
        paras = "".join(f"<p>{esc(p.strip())}</p>" for p in d["story"]["text"].split("\n") if p.strip())
        P.add("story", L("s_story"), "quote", f'''{P.kicker(L("s_story"), "quote")}
<div class="story">{paras}</div><p class="note">{esc(L("story_note", model=d["story"].get("entity", "AI")))}</p>''')

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
        if e.get("solar"):
            stats.append(P.stat(L("solar"), kwh(e["solar"]), e["solar"], _get(lambda x: x["energy"]["solar"])))
        if e.get("battery_discharge"):
            stats.append(P.stat(L("from_battery"), kwh(e["battery_discharge"]), e["battery_discharge"],
                                _get(lambda x: x["energy"]["battery_discharge"])))
        if e.get("export"):
            stats.append(P.stat(L("exported"), kwh(e["export"]), e["export"], _get(lambda x: x["energy"]["export"])))
        if e.get("self_sufficiency") is not None:
            stats.append(P.stat(L("self_sufficiency"), L.pct(e["self_sufficiency"])))
        if e.get("base_load_w"):
            stats.append(P.stat(L("base_load"), f'{L.num(e["base_load_w"])} W', e["base_load_w"], _get(lambda x: x["energy"]["base_load_w"])))
        tr = trend(L, P.series13(_get(lambda x: x["energy"]["consumption"])), L("trend_use"), lambda v: kwh(v))
        legend = f'<span><i style="background:var(--s1)"></i>{esc(L("imported"))}</span>'
        if e.get("solar"):
            legend += f'<span><i style="background:var(--s4)"></i>{esc(L("solar_direct"))}</span>'
        if e.get("battery_discharge"):
            legend += f'<span><i style="background:var(--s5)"></i>{esc(L("from_battery"))}</span>'
        if e.get("export"):
            legend += f'<span><i style="background:var(--s3)"></i>{esc(L("exported"))}</span>'
        P.add("energy", L("s_energy"), "bolt", f'''{P.kicker(L("s_energy"), "bolt")}
<div class="head2"><h2>{head}</h2>{tr}</div>
<div><div class="wide">{daily_energy_chart(L, e["daily"], 1000, 260)}</div><div class="narrow">{daily_energy_chart(L, e["daily"], 420, 280, 14)}</div>
<div class="legend">{legend}<span style="color:var(--mut)">{esc(L("kwh_per_day"))}</span></div></div>
<div class="stats">{"".join(stats)}</div>''')

    # ---------------------------------------------------------------- costs
    if e.get("total_cost") is not None:
        # The household bill: energy (electricity, gas, fixed costs) plus water when it has a price.
        def billf(x):
            return x["energy"].get("bill_total", x["energy"]["total_cost"])
        tot = billf(d)
        bill_label = L("cost_with_water") if e.get("water_cost") is not None else L("net_cost")
        avg, refs = P.compare(billf)
        if tot < 0:
            head = L("h_cost_earned")
        elif avg is not None:
            diff = tot - avg
            head = (L("h_cost_same", **refs) if abs(diff) < max(5, abs(avg) * .05)
                    else L("h_cost_more" if diff > 0 else "h_cost_less", v=money(abs(diff)), **refs))
        else:
            head = L("h_cost_first", v=money(tot))
        paid = [(L("import_cost"), e["cost_import"], "var(--cost)")] if e.get("cost_import") is not None else []
        if e.get("gas_cost"):
            paid.append((L("gas_cost"), e["gas_cost"], "color-mix(in srgb,var(--s4) 70%,var(--bg))"))
        if e.get("fixed_costs") and e["fixed_costs"] > 0:
            paid.append((L("fixed"), e["fixed_costs"], "color-mix(in srgb,var(--cost) 55%,var(--bg))"))
        if e.get("water_cost"):
            paid.append((L("water_cost"), e["water_cost"], "color-mix(in srgb,var(--s1) 45%,var(--bg))"))
        back = [(L("compensation"), e["compensation"], "var(--s3)")] if e.get("compensation") else []
        if e.get("fixed_costs") and e["fixed_costs"] < 0:  # e.g. a fixed tax credit
            back.append((L("fixed_credit"), -e["fixed_costs"], "color-mix(in srgb,var(--s3) 55%,var(--bg))"))
        tp, tb = sum(v for _, v, _ in paid), sum(v for _, v, _ in back)
        mx = max(tp, tb, 0.01)

        def bar(title, items, total):
            segs = "".join(f'<i style="width:{max(v, 0) / mx * 100:.2f}%;background:{c}" data-tip="{esc(n)}: {esc(money(v))}"></i>' for n, v, c in items if v > 0)
            return f'<div class="bb"><div class="bh"><span>{esc(title)}</span><b>{money(total)}</b></div><div class="bt">{segs}</div></div>'

        lines = "".join(f'<div class="rl"><span><i style="background:{c}"></i>{esc(n)}</span><span>{money(v, 2)}</span></div>' for n, v, c in paid)
        lines += "".join(f'<div class="rl"><span><i style="background:{c}"></i>{esc(n)}</span><span>−{money(v, 2)}</span></div>' for n, v, c in back)
        bill = f'''<div class="bill">{bar(L("paid"), paid, tp)}{bar(L("received"), back, tb) if back else ""}
<div class="rec">{lines}<div class="rl tot"><span>{esc(L("total") if tot >= 0 else L("credit"))}</span><span>{money(abs(tot), 2)}</span></div></div></div>'''
        tr = trend(L, P.series13(_get(billf)), L("trend_cost"), lambda v: money(v))
        note = L("cost_note") + (" " + L("cost_note_fixed") if e.get("fixed_costs") else "")
        price = ""
        if e.get("avg_import_price") is not None:
            price = f'<div class="cmp">{esc(L("avg_price"))}: <b>{money(e["avg_import_price"], 3)}</b>/kWh</div>'
        P.add("cost", L("s_cost"), "receipt", f'''{P.kicker(L("s_cost"), "receipt")}
<div class="split"><div><h2>{head}</h2>
<div class="hero" style="margin-top:22px">{money(abs(tot))}<small>{esc(bill_label)}</small></div>{price}
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
                c = f'<div class="c">{esc(L("vs_normal"))} {L.num(wx["normal"]["sun_h"])} {esc(L("unit_hours"))}</div>'
            stats.append(f'<div class="stat"><div class="l">{esc(L("sun_hours"))}</div><div class="v">{L.num(wx["sun_h"])}<small>{esc(L("unit_hours"))}</small></div>{c}</div>')
        tr = trend(L, P.series13(_get(lambda x: x["energy"]["solar"])), L("trend_solar"), lambda v: kwh(v))
        P.add("solar", L("s_solar"), "sun", f'''{P.kicker(L("s_solar"), "sun")}
<div class="split"><div><h2>{head}</h2><div class="hero" style="margin-top:22px">{L.num(sol)}<small>kWh</small></div></div>
<div><div class="stats">{"".join(stats)}</div><div style="margin-top:28px">{tr}</div></div></div>''')

    # ---------------------------------------------------------------- batteries
    b = d.get("batteries")
    if b and b.get("charge", 0) > 1:
        one = len(b["units"]) == 1
        head = L("h_battery_one" if one else "h_battery", v=kwh(b["charge"]), back=kwh(b["discharge"]))
        rows = "".join(
            f'<tr><td>{esc(x["name"])}</td><td>{L.num(x["charge"], 1)}</td><td>{L.num(x["discharge"], 1)}</td><td>{L.pct(x["efficiency"])}</td></tr>'
            for x in b["units"])
        if len(b["units"]) > 1:
            rows += f'<tr><td><b>{esc(L("total"))}</b></td><td><b>{L.num(b["charge"], 1)}</b></td><td><b>{L.num(b["discharge"], 1)}</b></td><td><b>{L.pct(b["efficiency"])}</b></td></tr>'
        bt = L("s_battery_one" if one else "s_battery")
        P.add("battery", bt, "battery", f'''{P.kicker(bt, "battery")}
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
                a = P.ref_avg(lambda x, s=stat: next((i["kwh"] for i in x["devices"]["items"] if i["stat"] == s), None))
                if a:
                    tip = f' data-tip="{esc(L("avg"))} {esc(kwh(a))}"'
            lines.append(f'<div class="r"{tip}><div class="lb">{esc(name)}{badge}</div><div class="t"><div class="f{muted}" style="width:{k / mx * 100:.1f}%"></div></div>'
                         f'<div class="v">{L.num(k)}</div><div class="p">{L.pct(k / cons)}</div><div class="e">{money(val) if val is not None else ""}</div></div>')
        top = next((r for r in rows if r[4]), None)
        head = L("h_devices", name=esc(top[0]), share=L.pct(top[1] / cons)) if top else ""
        note = L("dev_note", names=", ".join(missing)) if missing else L("dev_note", names="–").split(". ")[0] + "."
        P.add("devices", L("s_devices"), "plug", f'''{P.kicker(L("s_devices"), "plug")}
<h2>{head}</h2><div class="rank">{"".join(lines)}</div><p class="note">{esc(note)}</p>''')

    # ---------------------------------------------------------------- heat pump (optional)
    hp = d.get("heat_pump")
    if hp and hp.get("electricity"):
        cop_fn = _get(lambda x: x["heat_pump"]["cop"])
        if hp.get("cop"):
            ref, refs = P.compare(cop_fn)
            if ref:
                p = (hp["cop"] - ref) / ref
                head = (L("h_hp_cop_same", **refs) if abs(p) < .05 else
                        L("h_hp_cop_better" if p > 0 else "h_hp_cop_worse", **refs))
            else:
                head = L("h_hp_cop", v=kwh(hp["electricity"]), cop=L.num(hp["cop"], 1))
            hero = f'{L.num(hp["cop"], 1)}<small>COP</small>'
            hero_note = f'<p class="note" style="margin-top:10px">{esc(L("hp_cop_explained", cop=L.num(hp["cop"], 1)))}</p>'
            if ref:
                hero_note = (f'<div class="cmp">{esc(L("last_year") if refs.get("kind") == "ly" else L("average"))} '
                             f'{L.num(ref, 1)}</div>') + hero_note
        else:
            head = L("h_hp", v=kwh(hp["electricity"]))
            hero, hero_note = f'{L.num(hp["electricity"])}<small>kWh</small>', ""
        stats = []
        if hp.get("heat"):
            stats.append(P.stat(L("hp_heat"), kwh(hp["heat"]), hp["heat"], _get(lambda x: x["heat_pump"]["heat"])))
        stats.append(P.stat(L("hp_elec"), kwh(hp["electricity"]), hp["electricity"], _get(lambda x: x["heat_pump"]["electricity"])))
        if hp.get("cost") is not None:
            stats.append(P.stat(L("cost_short"), money(hp["cost"]), hp["cost"], _get(lambda x: x["heat_pump"]["cost"]),
                                lambda v: money(v)))
        if hp.get("kwh_per_degree_day"):
            stats.append(P.stat(L("hp_per_dd"), f'{L.num(hp["kwh_per_degree_day"], 2)} kWh', hp["kwh_per_degree_day"],
                                _get(lambda x: x["heat_pump"]["kwh_per_degree_day"]), lambda v: L.num(v, 2)))
        if hp.get("cost_per_degree_day"):
            stats.append(P.stat(L("hp_cost_per_dd"), money(hp["cost_per_degree_day"], 2), hp["cost_per_degree_day"],
                                _get(lambda x: x["heat_pump"]["cost_per_degree_day"]), lambda v: money(v, 2)))
        if hp.get("share"):
            stats.append(P.stat(L("share"), L.pct(hp["share"])))
        tr = trend(L, P.series13(_get(lambda x: x["heat_pump"]["electricity"])), L("trend_hp"), lambda v: kwh(v))
        P.add("heatpump", L("s_heat_pump"), "heatpump", f'''{P.kicker(L("s_heat_pump"), "heatpump")}
<div class="split"><div><h2>{head}</h2><div class="hero" style="margin-top:22px">{hero}</div>{hero_note}</div>
<div><div class="stats">{"".join(stats)}</div><div style="margin-top:28px">{tr}</div></div></div>
<p class="note">{esc(L("hp_note", devices=", ".join(hp.get("devices", []))))}</p>''')

    # ---------------------------------------------------------------- car (optional: odometer + charger, evcc or TeslaMate)
    car = d.get("car")
    if car:
        mi = tu == "°F"
        f_km = 1.609344 if mi else 1.0
        dist = lambda v: f"{L.num(v / f_km)} {'mi' if mi else 'km'}"  # noqa: E731
        src = car.get("source")
        C = lambda k: _get(lambda x, k=k: x["car"][k])  # noqa: E731
        home_key = "home_used_kwh" if car.get("home_used_kwh") is not None else (
            "charged_home" if car.get("charged_home") is not None else "charged")
        cost_key = "home_cost" if car.get("home_cost") is not None else "cost"
        km = car.get("km") or 0
        if km:
            ref, refs = P.compare(C("km"))
            if ref:
                p = (km - ref) / ref
                head = (L("h_car_km_same", km=dist(km), **refs) if abs(p) < .05 else
                        L("h_car_km_more" if p > 0 else "h_car_km_less", km=dist(km), pct=L.pct(abs(p)), **refs))
            else:
                head = L("h_car_km", km=dist(km))
        else:
            head = L("h_car_charged", v=kwh(car.get(home_key) or 0))
        if car.get("cost_per_100km") is not None:
            hero = f'{money(car["cost_per_100km"] * f_km, 2)}<small>{esc(L("car_per_100_cost_mi" if mi else "car_per_100_cost"))}</small>'
            hero_note = f'<p class="note" style="margin-top:10px">{esc(L("car_cost_explained"))}</p>'
        else:
            hero = f'{L.num(km / f_km)}<small>{"mi" if mi else "km"}</small>' if km else f'{L.num(car.get(home_key) or 0)}<small>kWh</small>'
            hero_note = ""
        stats = []
        if car.get("drives"):
            stats.append(P.stat(L("car_drives"), L.num(car["drives"]), car["drives"], C("drives")))
        if car.get("sessions"):
            stats.append(P.stat(L("car_sessions"), L.num(car["sessions"]), car["sessions"], C("sessions")))
        if car.get(home_key):
            stats.append(P.stat(L("car_charged_home"), kwh(car[home_key]), car[home_key], C(home_key)))
        if car.get(cost_key) is not None:
            stats.append(P.stat(L("car_home_cost"), money(car[cost_key]), car[cost_key], C(cost_key), lambda v: money(v)))
        if car.get("avg_charge_price") is not None:
            stats.append(P.stat(L("car_avg_price"), f'{money(car["avg_charge_price"], 3)}', car["avg_charge_price"],
                                C("avg_charge_price"), lambda v: money(v, 3)))
        if car.get("smart_saving") is not None and abs(car["smart_saving"]) >= 0.5:
            stats.append(P.stat(L("car_smart_saving"), money(car["smart_saving"]), car["smart_saving"], C("smart_saving"),
                                lambda v: money(v)))
        if car.get("solar_share") is not None:
            stats.append(P.stat(L("solar"), L.pct(car["solar_share"])))
        use = None
        if car.get("wh_per_km"):
            use = car["wh_per_km"] / 10
        elif car.get("kwh_per_100km_home"):
            use = car["kwh_per_100km_home"]
        elif km > 10 and car.get("charged"):
            use = car["charged"] / km * 100
        if use:
            stats.append(P.stat(L("car_use"), f'{L.num(use * f_km, 1)} kWh/{"100\u00a0mi" if mi else "100\u00a0km"}'))
        tr = trend(L, P.series13(C("km")), L("trend_car"), dist) if km else trend(L, P.series13(C(home_key)), L("trend_charged"), lambda v: kwh(v))
        table = ""
        if len(car.get("cars", [])) > 1:
            rows = "".join(f'<tr><td>{esc(c["name"])}</td><td>{dist(c["km"]) if c.get("km") else "–"}</td>'
                           f'<td>{L.num(c["charged"]) if c.get("charged") is not None else "–"}</td></tr>' for c in car["cars"])
            table = (f'<div class="tbl"><table><thead><tr><th></th><th>{"mi" if mi else "km"}</th><th>{esc(L("car_charged"))} (kWh)</th>'
                     f'</tr></thead><tbody>{rows}</tbody></table></div>')
        note = {"teslamate": "car_note", "evcc": "car_note_evcc"}.get(src, "car_note_generic")
        P.add("car", L("s_car"), "car", f'''{P.kicker(L("s_car"), "car")}
<div class="split"><div><h2>{head}</h2><div class="hero" style="margin-top:22px">{hero}</div>{hero_note}</div>
<div><div class="stats">{"".join(stats)}</div><div style="margin-top:28px">{tr}</div></div></div>
{table}<p class="note">{esc(L(note))}</p>''')

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
                 (f'<div class="stat"><div class="l">{esc(L("rain"))}</div><div class="v">{L.num(wx["precip"], 0 if pu == "mm" else 1)}<small>{pu}</small></div>'
                  + (f'<div class="c">{esc(L("vs_normal"))} {L.num(wx["normal"]["precip"], 0 if pu == "mm" else 1)} {pu}</div>' if g(wx, "normal", "precip") is not None else "") + '</div>')
                 if wx.get("precip") is not None else "",
                 f'<div class="stat"><div class="l">{esc(L("frost_days"))}</div><div class="v">{wx["frost_days"]}</div></div>'
                 if wx["frost_days"] or m in (11, 12, 1, 2, 3) else
                 f'<div class="stat"><div class="l">{esc(L("summer_days"))}</div><div class="v">{wx["summer_days"]}</div></div>',
                 P.stat(L("degree_days"), L.num(wx["degree_days"]), wx["degree_days"], _get(lambda x: x["weather"]["degree_days"]))]
        legend = (f'<span><i style="background:var(--s1);opacity:.35"></i>{esc(L("band"))}</span><span><i style="background:var(--s1)"></i>{esc(L("mean_line"))}</span>'
                  + (f'<span><i style="background:var(--hi)"></i>{esc(L("normal_line"))}</span>' if n is not None else ""))
        src_w = wx.get("source", "open-meteo")
        note = L({"sensor": "weather_note_sensor", "sensor-only": "weather_note_sensor_only"}.get(src_w, "weather_note"))
        if wx.get("rain_source") == "sensor":
            note += " " + L("weather_note_rain")
        if wx.get("sensor_name"):
            note += " " + L("weather_where_sensor", name=wx["sensor_name"])
        if wx.get("location"):
            la, lo = wx["location"]["lat"], wx["location"]["lon"]
            where = f'{L.num(abs(la), 1)}° {"N" if la >= 0 else "S"}, {L.num(abs(lo), 1)}° {"E" if lo >= 0 else "W"}'
            if src_w == "open-meteo":
                note = L("weather_note_at", where=where)
            else:
                note += " " + L("weather_where_om", where=where)
        if wx.get("dd_base") is not None:
            nd = 0 if float(wx["dd_base"]).is_integer() else 1
            note += " " + L("dd_def_weighted" if wx.get("dd_weighted") else "dd_def", base=f'{L.num(wx["dd_base"], nd)} {tu}')
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
            t = "–"
            if "temp" in a:
                dl = P.delta(a["temp"], lambda x, aid=a["area_id"]: next(
                    (y["temp"] for y in x["indoor"]["areas"] if y["area_id"] == aid and "temp" in y), None), "°")
                dl_html = f'<span class="sm" data-tip="{esc(dl[1])}">{esc(dl[0])}</span>' if dl else ""
                t = f'{L.num(a["temp"], 1)}{tu}{dl_html}<span class="sm">{L.num(a["temp_min"], 0)}–{L.num(a["temp_max"], 0)}</span>'
            h = (f'{L.num(a["humidity"])}%' + (f'<span class="sm">{a["humid_hours"]} {esc(L("humid_hours"))}</span>' if a.get("humid_hours") else "")) if "humidity" in a else ""
            c = (f'{L.num(a["co2"])} ppm' + (f'<span class="sm">{L.pct(a["co2_over_1000"])} {esc(L("co2_high"))}</span>' if a.get("co2_over_1000") else "")) if "co2" in a else ""
            rows.append(f'<tr><td>{esc(a["name"])}</td><td>{t}</td>' + (f"<td>{h}</td>" if has_h else "") + (f"<td>{c}</td>" if has_c else "") + "</tr>")
        th = f'<th>{esc(L("room"))}</th><th>{esc(L("temp"))}</th>' + (f'<th>{esc(L("humidity"))}</th>' if has_h else "") + (f'<th>{esc(L("co2"))}</th>' if has_c else "")
        stats = [P.stat_vs(L("temp"), f'{L.num(ind["temp"], 1)} {tu}', ind["temp"], _get(lambda x: x["indoor"]["temp"]), tu)]
        if ind.get("humidity") is not None:
            stats.append(P.stat_vs(L("humidity"), f'{L.num(ind["humidity"])} %', ind["humidity"],
                                   _get(lambda x: x["indoor"]["humidity"]), "%", 0))
        if ind.get("co2") is not None:
            stats.append(P.stat_vs(L("co2"), f'{L.num(ind["co2"])} ppm', ind["co2"], _get(lambda x: x["indoor"]["co2"]), " ppm", 0))
        P.add("indoor", L("s_indoor"), "thermo", f'''{P.kicker(L("s_indoor"), "thermo")}
<h2>{head}</h2>
<div class="stats">{"".join(stats)}</div>
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
        stats = [P.stat(L(f"s_{kind}"), amount, x["amount"], _get(lambda z, k=kind: z[k]["amount"]), fmt=lambda v, u=unit: (L.num(v / 1000, 1) + " m³") if u == "L" else f"{L.num(v, 1)} {u}"),
                 P.stat(L("per_day"), pd)]
        if x.get("cost") is not None:
            stats.append(P.stat(L("cost_short"), money(x["cost"], 2), x["cost"], _get(lambda z, k=kind: z[k]["cost"]),
                                lambda v: money(v, 2)))
        extra = ""
        if kind == "gas" and x.get("per_degree_day"):
            gu = unit
            stats.append(P.stat(L("hp_per_dd"), f'{L.num(x["per_degree_day"], 2)} {gu}', x["per_degree_day"],
                                _get(lambda z: z["gas"]["per_degree_day"]), lambda v: L.num(v, 2)))
            if x.get("heating") is not None:
                stats.append(P.stat(L("gas_heating"), f'{L.num(x["heating"], 1)} {gu}', x["heating"],
                                    _get(lambda z: z["gas"]["heating"]), lambda v: L.num(v, 1)))
                stats.append(P.stat(L("gas_hot_water"), f'{L.num(x["hot_water"], 1)} {gu}'))
                share = x["heating"] / x["amount"] if x["amount"] else 0
                head = L("h_gas_split", v=amount, share=L.pct(share))
            wx_days = {w["d"]: w for w in (d.get("weather") or {}).get("daily", [])}
            base_t = 18.0 if tu == "°C" else 65.0
            pts = [(max(0.0, base_t - wx_days[g["d"]]["mean"]), g["v"], g["d"]) for g in x.get("daily", [])
                   if g["d"] in wx_days and wx_days[g["d"]].get("mean") is not None]
            note_key = {"option": "gas_note_option", "estimate": "gas_note_estimate", "no_heating": "gas_note_summer",
                        "unknown": "gas_note_unknown"}.get(x.get("base_source"), "gas_note_unknown")
            extra = (f'<div><div class="wide">{gas_scatter(L, pts, x.get("base_per_day"), x.get("heating_per_degree_day"), gu, tu)}</div>'
                     f'<div class="narrow">{gas_scatter(L, pts, x.get("base_per_day"), x.get("heating_per_degree_day"), gu, tu, 420, 220)}</div>'
                     f'<p class="note" style="margin-top:8px">{esc(L(note_key, base=f"{L.num(x.get('base_per_day') or 0, 2)} {gu}"))}</p></div>')
        tr = trend(L, P.series13(_get(lambda z, k=kind, u=unit: z[k]["amount"] / (1000 if u == "L" else 1))), L(f"trend_{kind}"),
                   lambda v: L.num(v, 1))
        P.add(kind, L(f"s_{kind}"), ic, f'''{P.kicker(L(f"s_{kind}"), ic)}
<div class="split"><div><h2>{head}</h2><div class="hero" style="margin-top:22px">{L.num(big, 1)}<small>{bigu}</small></div></div>
<div><div class="stats">{"".join(stats)}</div>{"" if extra else f'<div style="margin-top:28px">{tr}</div>'}</div></div>
{f'<div class="head2" style="align-items:start">{extra}{tr}</div>' if extra else ""}''')

    # ---------------------------------------------------------------- custom tiles (optional)
    tiles = [t for t in d.get("custom") or [] if t["value"] is not None]
    if tiles:
        cards, best = [], None
        for t in tiles:
            nd = t["decimals"]
            unit = {"days_above": L("unit_days"), "runs_above": L("unit_runs")}.get(t["type"], t["unit"])
            if t["type"] == "hours_above" or unit == "h":
                unit = L("unit_hours")
            fmt = lambda v, nd=nd, unit=unit: f"{L.num(v, nd)} {unit}".strip()  # noqa: E731
            fn = _get(lambda x, sid=t["statistic"], typ=t["type"], name=t["name"]: next(
                (c["value"] for c in x["custom"] if c["statistic"] == sid and c["type"] == typ and c["name"] == name), None))
            ref, refs = P.compare(fn)
            cmp_txt = ""
            if ref is not None:
                name = L("last_year") if refs.get("kind") == "ly" else L("avg")
                if ref and abs(t["value"] - ref) / abs(ref) >= .05:
                    p = (t["value"] - ref) / abs(ref)
                    cmp_txt = f'{esc(name)} {esc(fmt(ref))} · <b>{"▲" if p > 0 else "▼"} {L.num(abs(p) * 100)}%</b>'
                    if best is None or abs(p) > abs(best[1]):
                        best = (t["name"], p, refs)
                elif ref:
                    cmp_txt = f'{esc(name)} {esc(fmt(ref))} · {esc(L("same"))}'
                else:  # a reference of 0 (e.g. not measured yet) says nothing about this month
                    cmp_txt = f'{esc(name)} {esc(fmt(ref))}'
            strip = day_bars(L, d["period"], t.get("daily"), fmt)
            tr = trend(L, P.series13(fn), L("per_month_short"), fmt)
            cards.append(f'''<div class="card"><div class="cl">{esc(t["name"])}</div>
<div class="cv">{split_unit(fmt(t["value"]))}</div><div class="cmp">{cmp_txt}</div>{strip}{tr}</div>''')
        if best:
            head = L("h_custom_more" if best[1] > 0 else "h_custom_less", name=esc(best[0]),
                     pct=L.pct(abs(best[1])), **best[2])
        else:
            head = esc(L("h_custom"))
        P.add("custom", L("s_custom"), "tiles", f'''{P.kicker(L("s_custom"), "tiles")}
<h2>{head}</h2><div class="cards">{"".join(cards)}</div>''')

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
    srcs = d.get("indoor_sources")
    if srcs:
        if srcs["excluded_areas"]:
            notes.append(L("excl_auto" if srcs["excluded_auto"] else "excl_set", list=", ".join(srcs["excluded_areas"])))
        by_reason: dict[str, dict[str, int]] = {}
        for x in srcs["dropped"]:
            area = x.get("area") or "–"
            by_reason.setdefault(x["reason"], {}).setdefault(area, 0)
            by_reason[x["reason"]][area] += 1
        for reason in ("not_room_sensor", "co2_module", "implausible", "coverage"):
            if reason in by_reason:
                areas_n = ", ".join(f"{a} ({n})" if n > 1 else a for a, n in sorted(by_reason[reason].items()))
                notes.append(L(f"drop_{reason}", list=areas_n))
        if srcs.get("no_area"):
            notes.append(L("drop_no_area", n=srcs["no_area"]))
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
<div class="notes">{"".join(f'<p class="note">{esc(n)}</p>' for n in notes)}</div>
<p class="note">{esc(L("generated", d=f"{gen.day} {L.month(gen.month)} {gen.year}"))} · {esc(L("made_with"))}</p>
<div class="themes">{esc(L("theme"))}: {themes}</div>
<p style="font-size:15px"><a href="#" data-go="year-{year_key(ym, start_month)}">{esc(L("year_title"))} {esc(year_label(year_key(ym, start_month)))} →</a></p>
{foot}''')

    # ---------------------------------------------------------------- page
    nav = "".join(f'<a href="#{sid}" data-l="{esc(lab)}" aria-label="{esc(lab)}">{icon(ic)}</a>' for sid, lab, _, ic in P.slides)
    opts = "".join(f'<option value="{x}"{" selected" if x == ym else ""}>{esc(mlabel(x))}</option>' for x in reversed(months))
    top = (f'<div class="topbar">{topbar_left(L)}<div class="mnav">'
           + (f'<a href="#" class="prev" data-go="{prv}">‹</a>' if prv else "")
           + f'<select class="msel" aria-label="month">{opts}</select>'
           + (f'<a href="#" class="next" data-go="{nxt}">›</a>' if nxt else "") + "</div></div>")
    title = f"{L('title')} · {mname} {y}"
    return (f'<!doctype html><html lang="{L.code}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(title)}</title>{theme_head(theme)}<style>{font_css()}{CSS}</style></head><body data-ym="{ym}">'
            f'<div class="bar"></div>{top}<nav class="nav">{nav}</nav>{"".join(s for _, _, s, _ in P.slides)}<div id="tip"></div>'
            f'<script>{JS}</script></body></html>')


# ============================================================================ index
def render_index(docs: dict[str, dict], lang: str = "en", home_name: str | None = None, currency: str = "EUR",
                 start_month: int = 1, theme: str = "auto") -> str:
    L = Lang(lang, currency)
    rows, year = [], None
    keys = year_keys(docs, start_month)
    if keys:
        rows.append(f'<div class="y">{esc(L("year_title"))}</div>')
        for k in reversed(keys):
            ms = [m for m in year_months(k) if m in docs]
            use = sum((docs[m].get("energy") or {}).get("consumption") or 0 for m in ms)
            note = year_note(L, k, docs)
            rows.append(f'<a href="#" data-go="year-{k}"><b>{esc(year_label(k))}</b><span>{esc(note)}</span><span>{L.num(use)} kWh</span></a>')
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
            f'<title>{esc(L("title"))}</title>{theme_head(theme)}<style>{font_css()}{CSS} html{{scroll-snap-type:none}}</style></head><body>'
            f'<div class="topbar">{topbar_left(L)}</div>'
            f'<section class="slide" style="align-content:start"><div class="kicker">{icon("house")}{esc(L("title"))}{(" · " + sub) if sub else ""}</div>'
            f'<h2>{esc(L("index_title"))}</h2><div class="idx">{body}</div></section><div class="bar"></div><div id="tip"></div><script>{JS}</script></body></html>')


def months_json(docs: dict[str, dict]) -> str:
    return json.dumps(sorted(docs))


# ============================================================================ year review
def year_key(ym: str, start_month: int) -> str:
    """The first month (YYYY-MM) of the report year that contains ``ym``."""
    y, m = int(ym[:4]), int(ym[5:])
    return f"{y if m >= start_month else y - 1:04d}-{start_month:02d}"


def year_months(key: str) -> list[str]:
    y, m = int(key[:4]), int(key[5:])
    out = []
    for _ in range(12):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def year_status(key: str, docs: dict[str, dict]) -> str:
    """"complete", "running" (the year isn't over yet) or "incomplete" (over, but months are missing)."""
    months = year_months(key)
    have = sum(1 for m in months if m in docs)
    if have == 12:
        return "complete"
    return "running" if docs and months[-1] > max(docs) else "incomplete"


def year_note(L: Lang, key: str, docs: dict[str, dict]) -> str:
    st = year_status(key, docs)
    n = sum(1 for m in year_months(key) if m in docs)
    return "" if st == "complete" else L("year_partial" if st == "running" else "year_incomplete", n=n)


def year_label(key: str) -> str:
    y, m = int(key[:4]), int(key[5:])
    return str(y) if m == 1 else f"{y}/{(y + 1) % 100:02d}"


def year_keys(docs: dict[str, dict], start_month: int) -> list[str]:
    return sorted({year_key(ym, start_month) for ym in docs})


def month_bars(L: Lang, months: list[str], cur: list[float | None], prev: list[float | None], fmt, W=1000, H=260) -> str:
    """12 bars for this year (accent) with last year's values as outlines behind them."""
    vals = [v for v in cur + prev if v is not None]
    if not vals:
        return ""
    lo, hi = min(vals + [0]), max(vals + [0])
    step = nice_step(hi - lo or 1, 3)
    hi = step * math.ceil(hi / step) if hi > 0 else 0
    lo = step * math.floor(lo / step) if lo < 0 else 0
    pl, top, bot = 64, 14, 26
    sc = (H - top - bot) / ((hi - lo) or 1)
    y0 = top + hi * sc
    bw = (W - pl) / 12
    out = [f'<svg viewBox="0 0 {W} {H}" role="img">']
    t = lo
    while t <= hi + 1e-9:
        y = y0 - t * sc
        out.append(f'<line x1="{pl}" x2="{W}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/><text x="{pl - 8}" y="{y + 4:.1f}" class="ax" text-anchor="end">{esc(fmt(t))}</text>')
        t += step
    for i, ym in enumerate(months):
        x = pl + i * bw
        p, c = prev[i], cur[i]
        if p is not None:
            h = abs(p) * sc
            out.append(f'<rect x="{x + bw * .14:.1f}" y="{(y0 - h if p >= 0 else y0):.1f}" width="{bw * .72:.1f}" height="{max(h, 1):.1f}" rx="4" fill="none" stroke="var(--mut)" stroke-width="1.2" opacity=".7"/>')
        if c is not None:
            h = abs(c) * sc
            out.append(f'<rect x="{x + bw * .26:.1f}" y="{(y0 - h if c >= 0 else y0):.1f}" width="{bw * .48:.1f}" height="{max(h, 1):.1f}" rx="3" fill="var(--hi)"/>')
        tip = f'{L.month(int(ym[5:]))} {ym[:4]}: {fmt(c) if c is not None else L("no_data")}'
        if p is not None:
            tip += f' · {L("last_year")} {fmt(p)}'
        go = f' data-go="{ym}"' if c is not None else ""  # a bar of the year opens that month
        out.append(f'<rect class="hit" x="{x:.1f}" y="0" width="{bw:.1f}" height="{H}"{go} data-tip="{esc(tip)}"/>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{H - 6}" class="ax" text-anchor="middle">{esc(L.month_short(int(ym[5:])))}</text>')
    out.append(f'<line x1="{pl}" x2="{W}" y1="{y0:.1f}" y2="{y0:.1f}" stroke="var(--ink2)" stroke-width="1"/></svg>')
    return "".join(out)


def render_year(key: str, docs: dict[str, dict], lang: str = "en", home_name: str | None = None,
                start_month: int = 1, theme: str = "auto") -> str:
    months = year_months(key)
    prev_key = prev_ym(key, 12)
    prev_months = year_months(prev_key)
    have = [m for m in months if m in docs]
    if not have:
        raise KeyError(key)
    u = docs[have[-1]]["units"]
    L = Lang(lang, u.get("currency", "EUR"))
    P = Page(L, have[-1], docs)
    tu = u.get("temperature", "°C")
    label = year_label(key)
    complete = len(have) == 12

    def series(ms, fn):
        out = []
        for m in ms:
            try:
                out.append(fn(docs[m]) if m in docs else None)
            except (KeyError, TypeError, IndexError, StopIteration):
                out.append(None)
        return out

    def tot(ms, fn):
        v = [x for x in series(ms, fn) if x is not None]
        return sum(v) if v else None

    def prev_tot(fn):
        """Last year's total over the same months that this year has (fair comparison for a running year)."""
        idx = [i for i, m in enumerate(months) if m in docs]
        ps = series(prev_months, fn)
        if any(ps[i] is None for i in idx):
            return None
        return sum(ps[i] for i in idx)

    def cmp(cur, prv, fmt):
        if cur is None or not prv:
            return ""
        p = (cur - prv) / abs(prv)
        if abs(p) < .03:
            return f'<div class="cmp">{esc(L("last_year"))} {esc(fmt(prv))} · {esc(L("same"))}</div>'
        return f'<div class="cmp">{esc(L("last_year"))} {esc(fmt(prv))} · <b>{"▲" if p > 0 else "▼"} {L.num(abs(p) * 100)}%</b></div>'

    kwh = lambda v: f"{L.num(v)} kWh"  # noqa: E731
    E = lambda k: _get(lambda x: x["energy"][k])  # noqa: E731
    BILL = _get(lambda x: x["energy"].get("bill_total", x["energy"]["total_cost"]))  # energy plus water

    # ---------------------------------------------------------------- cover
    use, cost, sol = tot(months, E("consumption")), tot(months, BILL), tot(months, E("solar"))
    temps = [x for x in series(months, _get(lambda x: x["weather"]["temp"])) if x is not None]
    figs = []
    if use is not None:
        figs.append(f'<div>{icon("house")}<b>{kwh(use)}</b><span>{esc(L("used"))}</span></div>')
    if cost is not None:
        figs.append(f'<div>{icon("euro")}<b>{L.money(cost)}</b><span>{esc(L("net_cost"))}</span></div>')
    if sol:
        figs.append(f'<div>{icon("sun")}<b>{kwh(sol)}</b><span>{esc(L("from_sun"))}</span></div>')
    if temps:
        figs.append(f'<div>{icon("thermo")}<b>{L.num(sum(temps) / len(temps), 1)}{tu}</b><span>{esc(L("outside"))}</span></div>')
    sub = L("year_sub") if complete else year_note(L, key, docs)
    P.add("cover", L("year_title"), "house", f'''
<div class="top"><span>{esc(L("title"))} · {esc(L("year_title"))}</span><span>{esc(home_name or "")}</span></div>
<h1>{esc(label)}<span>{esc(sub)}</span></h1>
<div class="figs">{"".join(figs)}</div>''', "cover")

    def topic(sid, title, ic, fn, fmt, head_key, extra=""):
        cur, prv = series(months, fn), series(prev_months, fn)
        total_v = tot(months, fn)
        if total_v is None:
            return
        best = max(((m, v) for m, v in zip(months, cur, strict=False) if v is not None), key=lambda x: x[1])
        low = min(((m, v) for m, v in zip(months, cur, strict=False) if v is not None), key=lambda x: x[1])
        hl = L("year_highlow", hi=L.month(int(best[0][5:])), hv=fmt(best[1]), lo=L.month(int(low[0][5:])), lv=fmt(low[1]))
        if head_key == "y_cost" and total_v < 0:
            head_key = "y_cost_earned"
        P.add(sid, title, ic, f'''{P.kicker(title, ic)}
<div class="split"><div><h2>{L(head_key, v=esc(fmt(abs(total_v) if head_key == "y_cost_earned" else total_v)))}</h2>
<div class="hero" style="margin-top:22px;font-size:clamp(44px,7vw,96px)">{split_unit(fmt(total_v))}</div>{cmp(total_v, prev_tot(fn), fmt)}
<p class="note" style="margin-top:14px">{esc(hl)}</p></div>
<div><div class="wide">{month_bars(L, months, cur, prv, fmt, 640, 300)}</div><div class="narrow">{month_bars(L, months, cur, prv, fmt, 420, 260)}</div><div class="legend"><span><i style="background:var(--hi)"></i>{esc(label)}</span>
<span><i style="border:1.2px solid var(--mut);background:none"></i>{esc(L("last_year"))}</span></div>{extra}</div></div>''')

    topic("energy", L("s_energy"), "bolt", E("consumption"), kwh, "y_energy")
    if cost is not None:
        topic("cost", L("s_cost"), "receipt", BILL, lambda v: L.money(v), "y_cost")
    if sol:
        topic("solar", L("s_solar"), "sun", E("solar"), kwh, "y_solar")
    if any(m in docs and g(docs[m], "heat_pump", "electricity") for m in months):
        topic("heatpump", L("s_heat_pump"), "heatpump", _get(lambda x: x["heat_pump"]["electricity"]), kwh, "y_hp")
    if any(m in docs and docs[m].get("car") for m in months):
        topic("car", L("s_car"), "car", _get(lambda x: x["car"]["km"]), lambda v: f"{L.num(v)} km", "y_car")

    # ---------------------------------------------------------------- devices over the year
    agg: dict[str, dict] = {}
    for m in have:
        for x in (docs[m].get("devices") or {}).get("items", []):
            if x.get("parent"):
                continue
            a = agg.setdefault(x["stat"], {"name": x["name"], "kwh": 0.0, "value": 0.0})
            a["kwh"] += x["kwh"]
            a["value"] += x.get("value") or 0
    rows = sorted((a for a in agg.values() if a["kwh"] >= 0.5), key=lambda a: -a["kwh"])[:10]
    if rows and use:
        mx = rows[0]["kwh"]
        lines = [f'<div class="r h"><div>{esc(L("device"))}</div><div class="t" style="background:none"></div><div class="v">kWh</div><div class="p">{esc(L("share"))}</div><div class="e">{esc(L("value"))}</div></div>']
        for a in rows:
            lines.append(f'<div class="r"><div class="lb">{esc(a["name"])}</div><div class="t"><div class="f" style="width:{a["kwh"] / mx * 100:.1f}%"></div></div>'
                         f'<div class="v">{L.num(a["kwh"])}</div><div class="p">{L.pct(a["kwh"] / use)}</div><div class="e">{L.money(a["value"]) if a["value"] else ""}</div></div>')
        P.add("devices", L("s_devices"), "plug", f'''{P.kicker(L("s_devices"), "plug")}
<h2>{L("h_devices", name=esc(rows[0]["name"]), share=L.pct(rows[0]["kwh"] / use))}</h2><div class="rank">{"".join(lines)}</div>''')

    # ---------------------------------------------------------------- weather over the year
    wt = series(months, _get(lambda x: x["weather"]["temp"]))
    if any(v is not None for v in wt):
        normals = series(months, _get(lambda x: x["weather"]["normal"]["temp"]))
        avg_t = sum(v for v in wt if v is not None) / len([v for v in wt if v is not None])
        nt = [n for n, v in zip(normals, wt, strict=False) if n is not None and v is not None]
        delta = (sum(v for n, v in zip(normals, wt, strict=False) if n is not None and v is not None) / len(nt) - sum(nt) / len(nt)) if nt else None
        if delta is None:
            head = L("h_weather_plain", v=f"{L.num(avg_t, 1)}{tu}")
        else:
            thr = 0.3 if tu == "°C" else 0.5
            wkey = "y_weather_normal" if abs(delta) < thr else ("y_weather_warm" if delta > 0 else "y_weather_cold")
            head = L(wkey, delta=f"{L.num(abs(delta), 1)}{tu}")
        stats = [P.stat(L("avg_temp"), f"{L.num(avg_t, 1)} {tu}")]
        pr = tot(months, _get(lambda x: x["weather"]["precip"]))
        prn = tot([m for m in months if m in docs], _get(lambda x: x["weather"]["normal"]["precip"]))
        if pr is not None:
            stats.append(f'<div class="stat"><div class="l">{esc(L("rain"))}</div><div class="v">{L.num(pr)}<small>mm</small></div>'
                         + (f'<div class="c">{esc(L("vs_normal"))} {L.num(prn)} mm</div>' if prn else "") + "</div>")
        sun = tot(months, _get(lambda x: x["weather"]["sun_h"]))
        if sun:
            stats.append(P.stat(L("sun_hours"), f'{L.num(sun)} {L("unit_hours")}'))
        frost = tot(months, _get(lambda x: x["weather"]["frost_days"]))
        if frost is not None:
            stats.append(P.stat(L("frost_days"), L.num(frost)))
        dd = tot(months, _get(lambda x: x["weather"]["degree_days"]))
        if dd is not None:
            stats.append(P.stat(L("degree_days"), L.num(dd)))
        P.add("weather", L("s_weather"), "cloud", f'''{P.kicker(L("s_weather"), "cloud")}
<h2>{head}</h2><div>{month_bars(L, months, wt, normals, lambda v: f"{L.num(v, 1)}°")}
<div class="legend"><span><i style="background:var(--hi)"></i>{esc(label)}</span><span><i style="border:1.2px solid var(--mut);background:none"></i>{esc(L("normal_line"))}</span></div></div>
<div class="stats">{"".join(stats)}</div>''')

    # ---------------------------------------------------------------- indoor by season
    seasons = {"winter": (12, 1, 2), "summer": (6, 7, 8)}
    areas: dict[str, dict] = {}
    for m in have:
        mm = int(m[5:])
        for a in (docs[m].get("indoor") or {}).get("areas", []):
            x = areas.setdefault(a["name"], {"floor": a.get("floor"), "winter": [], "summer": [], "all": [], "hum": []})
            if "temp" in a:
                x["all"].append(a["temp"])
                for sname, sm in seasons.items():
                    if mm in sm:
                        x[sname].append(a["temp"])
            if "humidity" in a:
                x["hum"].append(a["humidity"])
    if areas:
        avg = lambda v: sum(v) / len(v) if v else None  # noqa: E731
        trs = "".join(
            f'<tr><td>{esc(n)}</td><td>{L.num(avg(x["all"]), 1) if x["all"] else "–"}</td><td>{L.num(avg(x["winter"]), 1) if x["winter"] else "–"}</td>'
            f'<td>{L.num(avg(x["summer"]), 1) if x["summer"] else "–"}</td><td>{(L.num(avg(x["hum"])) + "%") if x["hum"] else "–"}</td></tr>'
            for n, x in sorted(areas.items(), key=lambda kv: (kv[1]["floor"] or "", kv[0])) if x["all"] or x["hum"])
        P.add("indoor", L("s_indoor"), "thermo", f'''{P.kicker(L("s_indoor"), "thermo")}
<h2>{esc(L("y_indoor"))}</h2><div class="tbl"><table><thead><tr><th>{esc(L("room"))}</th><th>{esc(L("year_avg"))} ({tu})</th>
<th>{esc(L("winter"))}</th><th>{esc(L("summer"))}</th><th>{esc(L("humidity"))}</th></tr></thead><tbody>{trs}</tbody></table></div>''')

    # ---------------------------------------------------------------- water & gas
    for kind, ic in (("water", "drop"), ("gas", "flame")):
        unit = next((docs[m][kind]["unit"] for m in have if docs[m].get(kind)), None)
        if not unit:
            continue
        div = 1000 if unit == "L" else 1
        shown = "m³" if unit == "L" else unit
        topic(kind, L(f"s_{kind}"), ic, _get(lambda x, k=kind, dv=div: x[k]["amount"] / dv),
              lambda v, su=shown: f"{L.num(v, 1)} {su}", f"y_{kind}")

    # ---------------------------------------------------------------- about + page
    links = []
    ks = year_keys(docs, start_month)
    i = ks.index(key)
    if i > 0:
        links.append(f'<a href="#" data-go="year-{ks[i - 1]}"><span>{esc(L("prev"))}</span><b>{esc(year_label(ks[i - 1]))}</b></a>')
    if i < len(ks) - 1:
        links.append(f'<a href="#" class="nx" data-go="year-{ks[i + 1]}"><span>{esc(L("next"))}</span><b>{esc(year_label(ks[i + 1]))}</b></a>')
    mlinks = " · ".join(f'<a href="#" data-go="{m}">{esc(L.month_short(int(m[5:])))}</a>' for m in have)
    P.add("about", L("s_about"), "info", f'''{P.kicker(L("s_about"), "info")}
<p class="note">{esc(L("year_about", n=len(have)))}</p><p style="font-size:15px">{mlinks}</p>
<p class="note">{esc(L("made_with"))}</p><div class="mfoot">{"".join(links)}</div>''')
    nav = "".join(f'<a href="#{sid}" data-l="{esc(lab)}" aria-label="{esc(lab)}">{icon(ic)}</a>' for sid, lab, _, ic in P.slides)
    top = f'<div class="topbar">{topbar_left(L)}<div class="mnav"><a href="#" data-go="{have[-1]}">{esc(L.month(int(have[-1][5:])))} {have[-1][:4]}</a></div></div>'
    return (f'<!doctype html><html lang="{L.code}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(L("title"))} · {esc(label)}</title>{theme_head(theme)}<style>{font_css()}{CSS}</style></head><body>'
            f'<div class="bar"></div>{top}<nav class="nav">{nav}</nav>{"".join(s for _, _, s, _ in P.slides)}<div id="tip"></div>'
            f'<script>{JS}</script></body></html>')
