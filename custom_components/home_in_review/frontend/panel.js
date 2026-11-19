// Home in Review sidebar panel.
// Reports are served by /api/home_in_review/report/<month> to logged-in users only. The panel asks Home Assistant for
// a short-lived signed URL (auth/sign_path) and shows the report in an iframe. Links inside a report post a message
// to this panel, which updates the address (/home-in-review/2026-10) and loads the next signed URL.
class HomeInReviewPanel extends HTMLElement {
  set hass(h) { const first = !this._hass; this._hass = h; if (first) this._init(); }
  set route(r) { this._route = r; if (this._frame) this._fromRoute(); }
  set narrow(n) { this._narrow = n; if (this._menu) this._menu.hidden = !n; }
  set panel(p) { this._panel = p; }

  _init() {
    this.style.cssText = "display:block;height:100%;position:relative;background:var(--primary-background-color)";
    this.innerHTML = `
      <iframe title="Home in Review" style="border:0;width:100%;height:100vh;display:block"></iframe>
      <button aria-label="Menu" style="position:fixed;left:12px;bottom:max(12px,env(safe-area-inset-bottom));z-index:3;
        width:40px;height:40px;border-radius:50%;border:1px solid rgba(127,127,127,.35);background:rgba(20,24,32,.75);color:#eee;
        font-size:18px;cursor:pointer" hidden>☰</button>`;
    this._frame = this.querySelector("iframe");
    this._menu = this.querySelector("button");
    this._menu.hidden = !this._narrow;
    this._menu.addEventListener("click", () =>
      this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
    window.addEventListener("message", (e) => {
      if (!this._frame || e.source !== this._frame.contentWindow) return;
      const target = e.data && e.data.homeInReview;
      if (typeof target === "string" && /^(index|(year-)?\d{4}-\d{2})$/.test(target)) {
        history.pushState(null, "", `/${this._base()}/${target === "index" ? "" : target}`);
        this._show(target);
      }
    });
    requestAnimationFrame(() => this._fromRoute());
  }

  _base() { return (this._route && this._route.prefix || "/home-in-review").replace(/^\//, ""); }

  _fromRoute() {
    const p = ((this._route && this._route.path) || "").replace(/^\//, "").replace(/\/$/, "");
    this._show(/^(year-)?\d{4}-\d{2}$/.test(p) ? p : "index");
  }

  async _show(target) {
    if (target === this._current) return;
    this._current = target;
    try {
      const r = await this._hass.callWS({ type: "auth/sign_path", path: `/api/home_in_review/report/${target}`, expires: 3600 });
      this._frame.src = r.path;
    } catch (err) {
      this._frame.srcdoc = `<p style="font:16px system-ui;padding:24px">Could not load the report: ${String((err && err.message) || err)}</p>`;
    }
  }
}
customElements.define("home-in-review-panel", HomeInReviewPanel);
