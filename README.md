# Home in Review

A monthly report of your home, made from data Home Assistant already has. Once a month it puts together
**how much energy the house used and what it cost, where it went, how the weather compared to normal and how
warm, humid and fresh it was inside**. The result is a calm, scrollable presentation in the sidebar, one topic
per screen.

> **Status: early test version (0.1).** It works on the author's own installation and is now shared with a few
> testers. Expect rough edges. Please [open an issue](https://github.com/fbloemhof/ha-home-in-review/issues) with
> what you see.

## Built with AI

This integration was designed and written together with an AI coding assistant
([Claude Code](https://claude.com/claude-code) by Anthropic). A human (the maintainer) chose the features,
tested every version on a real Home Assistant installation and reviews every change. Commits written with AI
help are marked with a `Co-Authored-By: Claude` line. If something looks wrong, it may well be. Please report it.

## What you get

| Slide | Source | Shown when |
|---|---|---|
| Cover with key figures | everything below | always |
| Electricity: use per day, grid in/out, self-sufficiency, base load | energy dashboard | a grid source is set up |
| Costs: bought, sold, fixed costs, average price | the energy dashboard's cost statistics | prices are set in the energy dashboard |
| Solar: production, share used at home, sunshine vs. normal | energy dashboard, Open-Meteo | solar is set up |
| Batteries: charged, discharged, efficiency | energy dashboard | batteries are set up |
| Where it went: devices ranked, untracked rest, value at grid price | energy dashboard "individual devices" | devices are set up |
| Daily rhythm: average power per hour of day, busiest hour | energy dashboard | a grid source is set up |
| Weather: temperature, rain, sunshine, degree days vs. 1991–2020 | Open-Meteo (or your own outdoor sensor) | your home has a location |
| Indoors: temperature, humidity and CO₂ per area | your sensors | climate sensors are assigned to areas |
| Water and gas | energy dashboard | set up |

Every figure is compared with the same month last year (when available) or the average of the last twelve
months, with a small 13-month trend chart.

There is **nothing to configure** to get started: the integration reads your energy dashboard and finds your
indoor sensors through their areas.

## Installation

Home in Review is not in the default HACS / Marketplace list yet. Add it as a custom repository:

1. In Home Assistant open **HACS** (Marketplace) → ⋮ → **Custom repositories**.
2. Add `https://github.com/fbloemhof/ha-home-in-review` with type **Integration**.
3. Install **Home in Review** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → Home in Review**.

On setup it generates the last 12 months from your long-term statistics in the background, so you can browse a
year of reports right away. After that, a new report is made on the 1st of every month at 07:00.

Manual install: copy `custom_components/home_in_review` into your `config/custom_components` folder and restart.

## Options

**Settings → Devices & services → Home in Review → Configure**

- **Notify when a report is ready**: one or more notify services (e.g. your phone). The notification opens the report.
- **Day and time**: when last month's report is made (default: the 1st at 07:00).
- **Areas that are not indoors**: excluded from the indoor climate. Areas or floors with names like garden, garage, balcony or shed are suggested.
- **Outdoor temperature sensor**: use your own sensor instead of Open-Meteo for the temperature.
- **Fixed energy costs** per day and/or per month, including tax: added to the costs.
- **Largest plausible use per hour**: meter jumps above this are treated as glitches (default 50 kWh).

## Actions

- `home_in_review.generate`: (re)make the report for one month (`month: "2026-10"`, default: last month), optionally with notifications.
- `home_in_review.backfill`: make missing reports for earlier months (`overwrite: true` re-makes existing ones, e.g. after an update).

## How it works

- **Energy** comes from the hourly long-term statistics of the sensors in your energy dashboard. Costs come
  from the cost statistics Home Assistant keeps for the energy dashboard. So with a dynamic tariff, every hour
  is priced at that hour's price. Device "value" is the device's hourly use times the grid price of that hour.
- **Glitches**: a meter step larger than the configured maximum per hour is skipped and mentioned in the report.
  A meter that resets (for example per charging session) is handled.
- **Indoor climate**: all temperature, humidity and CO₂ sensors with long-term statistics that are assigned to
  an area, either directly or through their device. When an area has a device that measures both temperature and humidity, only
  those temperature readings count, so motion sensors, pipe probes and the chip temperature of CO₂ modules
  don't skew the room. Per area the median is used. Implausible values (e.g. water temperatures) are dropped.
- **Indoors vs. outdoors**: until you choose areas in the options, areas and floors whose name says outdoors
  (garden, balcony, terrace, shed, driveway and the like, also as the end of a compound word such as
  "Backyard") are left out. Garages and storage rooms are not, because that differs per home. The last slide of
  every report lists what was left out and why.
- **Costs** in the totals are electricity bought minus sold, plus gas and the fixed costs you entered. Water is
  shown on its own slide.
- **Weather** comes from [Open-Meteo](https://open-meteo.com) (ERA5 reanalysis, free, no account). Normals are the
  1991–2020 averages for your area, computed once and cached.
- Reports are stored as JSON in `config/home_in_review/` and rendered when you open them, so improvements to
  the layout also apply to older months.

## Privacy

- Reports are only served to logged-in Home Assistant users (`/api/home_in_review/...` requires authentication;
  the panel uses short-lived signed links).
- The only outside service is Open-Meteo. It receives your location **rounded to 0.1° (about 10 km)** and the
  dates. Nothing else leaves your home.
- The report pages load no external fonts, scripts or images.

## Requirements

- Home Assistant 2025.4 or newer, with the recorder (long-term statistics) and the energy dashboard set up.
- Data older than your recorder's long-term statistics cannot be reported.

## Roadmap

- Yearly review
- Heat pump: electricity per degree day and COP when production is measured
- Electric car via TeslaMate (optional)
- Optional AI-written summary through Home Assistant's AI Task (your own model)
- Custom slides from your own statistics
- More languages (currently English and Dutch)

## License

MIT
