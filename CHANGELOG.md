# Changelog

## 0.3.1

**Security and reliability** (after an independent code review)
- Addresses for TeslaMate's Grafana and evcc are checked in the options and again before every request: only
  http(s), no user name or password in the address, and a token to an address outside your network needs https.
  Requests that carry a token never follow redirects, so the token only reaches the host you entered.
- Errors from outside services are logged without addresses or response bodies; unexpected errors are logged as
  bugs instead of being swallowed.
- New option **Only administrators can view the reports** (off by default: everyone in the household with a Home
  Assistant login can open them, as before).
- Report pages are served with a strict Content-Security-Policy (nothing loaded from elsewhere, no outgoing
  requests, only framed by Home Assistant). Messages between the panel and the report are checked for their origin.
- Reports are written atomically (temporary file, then rename), so an interrupted write can't damage one.
- Stored options are validated before use; the AI instructions are limited to 1000 characters.
- The README now says that your energy-dashboard device names are part of what the AI summary receives.

**New**
- Indoors: temperature, humidity and CO₂ compared with the same month last year (or the 12-month average), and
  per room the difference in degrees.
- Your own figures: "runs" counted from a device's power (e.g. dishwasher, washing machine and dryer programmes,
  also for months before you had counters).
- The "Your figures" slide shows each figure as a card with the comparison, a bar per day and a 13-month trend;
  the headline names the figure that changed most.
- Removing own figures uses a checkbox list.

**Development**
- Tests inside a real (test) Home Assistant: config flow, setup and unload, report access with and without login,
  signed links, administrators only, address checks in the options, and escaping of names.
- CI: GitHub Actions pinned to commit SHAs, Dependabot, separate job for the Home Assistant tests.
- `__init__.py` split into `store.py`, `views.py`, `options.py` and `net.py`.

## 0.3.0

**New**
- Icon and logo (shown in Home Assistant 2026.3 and newer).
- Car: [evcc](https://evcc.io) as a source: charging sessions, energy, cost and solar share per vehicle (kilometres
  from the odometer sensors when evcc doesn't know them).
- Weather: a rain gauge of your own can replace the modelled rainfall.
- Your own figures: "days above a threshold", e.g. the days the wood stove burned.
- Spanish and Italian, for the report and the settings.
- Amounts follow the language's convention (`€ 12` in Dutch, `12 €` in German, French, Spanish and Italian).

**Changed**
- Settings are one form with collapsible sections; adding or removing a figure saves right away.
- On narrow screens the sidebar menu button sits in the report's own top bar instead of floating over the text.
- The AI summary gets verified, pre-computed statements to phrase (no own calculations, causes or judgements).
- One battery is described in the singular.

**Fixed**
- The "add your own figure" form was empty (a required statistic field has no initial value in the frontend).
- The settings menu had no labels.
- Unloading after startup logged "Unable to remove unknown job listener".
- Comparisons crashed when an earlier month lacked the same car, device or figure.

## 0.2.0

- Year review (configurable start month), heat pump (any brand, COP, kWh per degree day), car (odometer and
  charger, or TeslaMate), your own figures, optional AI summary through your AI Task entity, Open-Meteo can be
  switched off, German and French, options in a menu, screenshots from anonymised demo data.

## 0.1.0

- First version: monthly report from the energy dashboard (electricity, costs, solar, batteries, devices, daily
  rhythm, water, gas), Open-Meteo weather with 1991–2020 normals, indoor climate per area, sidebar panel,
  monthly schedule with notifications, backfill of earlier months.
