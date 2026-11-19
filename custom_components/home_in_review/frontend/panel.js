// Home in Review sidebar panel.
// Reports are served by /api/home_in_review/report/<name> to logged-in users only. The panel asks Home Assistant for
// a short-lived signed URL (auth/sign_path) and shows the report in an iframe. Links inside a report post a message
// to this panel, which updates the address (/home-in-review/2026-10) and loads the next signed URL. On narrow
// screens the report shows a menu button in its own top bar; it asks the panel to open the sidebar.
// For the report theme "Home Assistant" the panel passes the colours and font of the active HA theme to the report,
// again whenever the theme or dark mode changes.

// Report variable <- Home Assistant theme variables (first one that is set wins).
const HA_THEME_VARS = {
  "--bg": ["--primary-background-color"],
  "--paper": ["--ha-card-background", "--card-background-color"],
  "--ink": ["--primary-text-color"],
  "--ink2": ["--secondary-text-color"],
  "--mut": ["--secondary-text-color"],
  "--line": ["--divider-color"],
  "--hi": ["--accent-color", "--primary-color"],
  "--cost": ["--secondary-text-color"],
  "--s1": ["--energy-grid-consumption-color"],
  "--s3": ["--energy-grid-return-color"],
  "--s4": ["--energy-solar-color"],
  "--s5": ["--energy-battery-out-color"],
  "--card-solid": ["--card-background-color"],
  "--ha-radius": ["--ha-card-border-radius"],
  "--ha-border": ["--ha-card-border-color", "--divider-color"],
  "--ha-border-w": ["--ha-card-border-width"],
  "--ha-shadow": ["--ha-card-box-shadow"],
  "--sans": ["--ha-font-family-body", "--paper-font-body1_-_font-family"],
  "--serif": ["--ha-font-family-body", "--paper-font-body1_-_font-family"],
};
class HomeInReviewPanel extends HTMLElement {
  set hass(h) {
    const first = !this._hass;
    const themeChanged = !first && (h.themes !== this._hass.themes || h.selectedTheme !== this._hass.selectedTheme);
    this._hass = h;
    if (first) this._init();
    // Theme variables are applied by HA after the hass update; read them a frame later.
    else if (themeChanged) requestAnimationFrame(() => this._sendTheme());
  }
  set route(r) { this._route = r; if (this._frame) this._fromRoute(); }
  set narrow(n) {
    this._narrow = !!n;
    if (this._frame && this._frame.contentWindow) this._frame.contentWindow.postMessage({ hirNarrow: this._narrow }, location.origin);
  }
  set panel(p) { this._panel = p; }

  _init() {
    this.style.cssText = "display:block;height:100%;position:relative;background:var(--primary-background-color)";
    this.innerHTML = `<iframe title="Home in Review" style="border:0;width:100%;height:100vh;display:block"></iframe>`;
    this._frame = this.querySelector("iframe");
    this._frame.addEventListener("load", () => this._sendTheme());
    window.addEventListener("message", (e) => {
      // Only messages from our own report frame, served by this Home Assistant (same origin).
      if (!this._frame || e.source !== this._frame.contentWindow || e.origin !== location.origin) return;
      const target = e.data && e.data.homeInReview;
      if (target === "menu") {
        this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
      } else if (typeof target === "string" && /^(index|(year-)?\d{4}-\d{2})$/.test(target)) {
        // The report says which slide (topic) was in view, so the next report opens at the same topic.
        const slide = typeof e.data.slide === "string" && /^[a-z]+$/.test(e.data.slide) ? e.data.slide : "";
        history.pushState(null, "", `/${this._base()}/${target === "index" ? "" : target}`);
        this._show(target, slide);
      }
    });
    requestAnimationFrame(() => this._fromRoute());
  }

  _sendTheme() {
    const w = this._frame && this._frame.contentWindow;
    if (!w) return;
    const cs = getComputedStyle(this);
    const vars = {};
    for (const [to, from] of Object.entries(HA_THEME_VARS)) {
      const v = from.map((n) => cs.getPropertyValue(n).trim()).find(Boolean);
      if (v) vars[to] = to === "--sans" || to === "--serif" ? `${v}, system-ui, sans-serif` : v;
    }
    const dark = !!(this._hass && this._hass.themes && this._hass.themes.darkMode);
    w.postMessage({ hirHaVars: vars, hirHaDark: dark }, location.origin);
  }

  _base() { return (this._route && this._route.prefix || "/home-in-review").replace(/^\//, ""); }

  _fromRoute() {
    const p = ((this._route && this._route.path) || "").replace(/^\//, "").replace(/\/$/, "");
    this._show(/^(year-)?\d{4}-\d{2}$/.test(p) ? p : "index");
  }

  async _show(target, slide = "") {
    if (target === this._current) return;
    this._current = target;
    try {
      const r = await this._hass.callWS({ type: "auth/sign_path", path: `/api/home_in_review/report/${target}`, expires: 3600 });
      const hash = [this._narrow ? "menu" : "", slide ? `s=${slide}` : ""].filter(Boolean).join("&");
      this._frame.src = r.path + (hash ? `#${hash}` : "");
    } catch (err) {
      const p = document.createElement("p");
      p.style.cssText = "font:16px system-ui;padding:24px";
      p.textContent = `Could not load the report: ${String((err && err.message) || err)}`;
      this._frame.removeAttribute("src");
      this._frame.srcdoc = p.outerHTML;
    }
  }
}
// After an update the browser can load a new panel.js while the old element is still registered.
if (!customElements.get("home-in-review-panel")) customElements.define("home-in-review-panel", HomeInReviewPanel);
