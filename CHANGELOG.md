# Changelog

## 0.5.2

**Fixed**
- Gas with the boiler's status (OpenTherm): the measured split now also applies to the month in which the status
  sensors were set up, as soon as they cover at least 7 days; the measured proportion is applied to the whole
  month and the report says since when it was measured. Before, only months covered completely were measured, so
  nothing changed until the month after.
- Gas: when gas clearly follows the weather but the month alone can't show the hot-water part (the best-fit line
  meets the axis below zero), the report no longer says "too little variation in the weather". It now uses the gas
  per day of earlier months without heating as hot water and cooking, or explains what is missing. Existing
  reports are updated automatically.

## 0.5.1

**Fixed**
- Gas: a home that only heats water with gas could get part of its gas labelled as heating (e.g. 30%). The split
  from the weather is now only made when gas clearly follows the degree days and the extra use per degree day is
  large enough to be space heating; otherwise the report says heating and hot water can't be told apart this month.
  Existing reports are corrected automatically after the update.

**New**
- Option **Gas used for**: *Heating and hot water* (default) or *Only hot water and cooking*, for homes heated
  otherwise (e.g. with a heat pump). All gas then counts as hot water and cooking.

## 0.5.0

**New**
- Batteries: what they were worth in money (each hour, discharged energy at that hour's price minus what charging
  cost), cycles from the state of charge, days full, and the highest charge and discharge power. Per battery in a
  table when there are several. No new settings: the power and state-of-charge sensors from the energy dashboard
  are used (#4).
- Gas: split into hot water and heating from the boiler's own status (#2). Choose its hot-water and/or heating
  status (a binary sensor such as OpenTherm's, or a thermostat) in the options; two sensors of the integration add
  up the hours, and from the first full month after that, gas is split per hour from what the boiler was doing
  instead of being estimated from the weather. The split is now also shown without weather data when it is
  measured.
- Peak power: the solar peak (solar slide) and the highest grid import and export (rhythm slide), from the power
  sensors in the energy dashboard.
- Reports are re-made once after the update to add these figures.
- Theme "Home Assistant": the report looks like part of Home Assistant. It takes the colours, font and card style
  (corners, border, shadow) of your active theme, and the colours of the energy dashboard for grid, solar, battery
  and return. It is laid out like Home Assistant's own dashboards (such as Energy): Home Assistant's Roboto font, a
  header bar, and each topic as a card in columns, instead of full-screen slides.
  It follows light/dark mode while open. Outside Home Assistant it uses neutral colours.
- The panel's script is now cached by its content, so a browser picks up a new version without a hard refresh.

**Docs**
- New page [Your own figures](docs/own-figures.md): the calculations, appliance runs, and a helper sensor for
  on/off things.

**Changed**
- The theme choice at the bottom of a report is now a small menu. Its first item, "default", shows the theme
  set in the options and forgets the viewer's own choice, so a later change of that option applies again.

**Fixed**
- When TeslaMate or evcc is unreachable while a report is re-made, the report keeps the car figures it had instead
  of losing them, and the month is tried again on the next start.
- Electricity: the stacked daily bars now have rounded ends like the other charts (only the outer end; the
  seams between grid, solar and battery stay straight).
- Units with digits in them (kWh/100 km, m³) are now printed small like the other units.
- Hours are abbreviated per language ("u" in Dutch instead of "h"): sun hours and hour tiles.

## 0.4.0

**New**
- Reports update themselves: each report remembers the version and the settings it was made with. After an update
  or a change of settings, outdated months are re-made in the background (newest first). AI summaries are only
  written again when the figures behind them changed. No more manual backfill with overwrite.
- Electricity: each day's use stacked by source (grid, solar used directly, battery), with what was returned to
  the grid below; solar and battery also as figures.
- Costs: water is on the bill ("energy + water"); a negative fixed amount (e.g. a daily tax credit) is shown as a
  credit. Fixed costs per day may now be negative. The year review uses the same total.
- Heat pump: cost (electricity per hour × that hour's price), cost per degree day, and with a heat sensor the COP
  as the main figure with an efficiency headline compared with last year or the average.
- Car (odometer + charger, evcc or TeslaMate): headline compares the distance, cost per 100 km as the main
  figure, charging cost at home, average charging price, saving from smart charging (against the month's plain
  average price), use per 100 km, all with comparisons.
- Typography and colours: Fraunces and Inter ship with the integration (nothing loaded from elsewhere); the night
  theme uses a navy and amber palette. New option **Default theme**.
- Degree days: options for the heating threshold (default 18 °C / 65 °F) and Dutch weighted degree days
  (Nov–Feb ×1.1, Mar/Oct ×1.0, Apr–Sep ×0.8), so gas per degree day can be compared with other services. The weather
  slide states which definition is used, and for which place the weather is (the rounded Home Assistant location,
  or the name of your outdoor sensor).
- README screenshots in the new design.
- Click a bar in any month chart (the 13-month trends and the year review) to open that month.
- The navigation on the right shows each slide's icon instead of a dot (the current one highlighted, the name on
  hover); the heat pump and own figures got icons of their own.
- Switching month (month menu, ‹ ›, the [ and ] keys or a chart bar) keeps you at the same topic instead of
  jumping back to the top.

**Fixed**
- The night and black-and-white themes were overridden by the dark theme on devices set to dark mode.

## 0.3.3

**Changed**
- The first backfill now covers all of last year plus this year so far (e.g. 22 months in November), so both year
  reviews start complete instead of two half years. The `backfill` action uses the same default when you leave
  out `months`.
- A past year with missing months reads "2 of 12 months" instead of "… so far"; only the running year says "so far".

## 0.3.2

**New**
- Gas: use per degree day, and the split between heating and hot water/cooking (degree-day regression: daily gas ≈
  base + k × degree days). Set the base per day in the options, or let it be estimated per month. A scatter chart
  shows every day against the degree days with the fitted line. The AI summary mentions it too.
- Demo screenshots now include gas and the own-figures cards.

**Fixed**
- Water and gas cost were labelled with the name of the meter instead of "Cost" and had no comparison.

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

**Fixed**
- After an update the browser could log "home-in-review-panel has already been used" (panel loaded twice).

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
