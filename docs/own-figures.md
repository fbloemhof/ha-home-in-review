# Your own figures

Besides energy, water, weather and the car, a report can show figures you choose yourself: how often the
dishwasher ran, how many hours the TV was on, on how many days the wood stove burned. They appear on the slide
**Your figures**, compared with the same month last year (or, without one, the average of the last 12 months),
with a small bar per day.

Add one in **Settings → Devices & services → Home in Review → Configure → Add your own figure**.

## What a figure can be built from

A figure is built from a **statistic**: the long-term statistics Home Assistant keeps for sensors with a
`state_class` (`measurement`, `total` or `total_increasing`). Most power, energy, temperature and similar
sensors have one already. If a sensor is not offered in the list, it has no statistics.

A few things to know:

- Statistics are kept **per hour**. Figures are counted from hourly values (an hour's average, lowest or highest
  value), not from every single state change.
- They start when the sensor (or its `state_class`) was added. A new helper sensor has no history, so earlier
  months stay empty for that figure.
- **On/off entities (`binary_sensor`, `input_boolean`, `switch`, …) have no statistics.** Make a small helper
  sensor that is 1 when on and 0 when off; see [the example below](#on-off-things-tv-wood-stove).

## The calculations

| Calculation | What it shows | Example |
|---|---|---|
| **Total (increase)** | how much a counter went up in the month | a water sub-meter, a kWh meter that is not in the energy dashboard |
| **Average** | the month's average | humidity in the bathroom, CO₂ in the bedroom |
| **Highest** / **Lowest** | the highest or lowest hourly value | the coldest night in the garden shed |
| **Hours above threshold** | the number of hours whose *average* was above the threshold | hours the desk was in use (power > 12 W) |
| **Days above threshold** | the number of days with at least one such hour | days the wood stove burned |
| **Runs** | how many times something started: blocks of hours above the threshold | dishwasher, washing machine, dryer programmes |

Because these work on hourly averages, "hours above" counts an hour when its *average* is above the threshold.
For a 0/1 sensor with threshold 0.5 that means: on for more than half of that hour. That is close enough for a
monthly figure, but don't expect it to match a stopwatch.

## Examples

### Appliances: dishwasher, washing machine, dryer

Use the **power** sensor of the appliance (W), from a smart plug or the appliance's own integration, with
**Runs**:

| Name | Statistic | Calculation | Threshold | Typical length of one run |
|---|---|---|---|---|
| Dishwasher | `sensor.dishwasher_power` | Runs | 10 | 3 |
| Washing machine | `sensor.washing_machine_power` | Runs | 10 | |
| Dryer | `sensor.dryer_power` | Runs | 10 | 3 |

- **Threshold**: just above the standby power. Look at the sensor's history: standby is often 0–5 W, a
  programme hundreds or thousands of watts. Some machines keep a few watts after the programme (an
  anti-crease drum turn, a display); raise the threshold above that.
- **Pauses**: a programme that soaks or cools down for a while still counts as one run, as long as the pause is
  2 hours or shorter.
- **Typical length of one run** (optional): when you run two programmes back to back, they form one long block.
  With a length of 3 hours, a 6-hour block counts as two runs. Leave it empty if your programmes vary a lot in
  length.

### On/off things: TV, wood stove

These have no statistics of their own, so first add a helper sensor, for example in a package
(`packages/home_in_review.yaml`, with `homeassistant: packages: !include_dir_named packages` in
`configuration.yaml`) or under `template:` in `configuration.yaml`:

```yaml
template:
  - sensor:
      - name: "TV living room on"
        unique_id: report_tv_living_room_on
        icon: mdi:television
        state_class: measurement
        state: "{{ 1 if is_state('media_player.living_room_tv', 'on') else 0 }}"

      - name: "Wood stove burning"
        unique_id: report_wood_stove_on
        icon: mdi:fireplace
        state_class: measurement
        state: "{{ 1 if is_state('input_boolean.wood_stove', 'on') else 0 }}"
```

`state_class: measurement` is what makes Home Assistant keep statistics. Then add the figures:

| Name | Statistic | Calculation | Threshold |
|---|---|---|---|
| TV on | `sensor.tv_living_room_on` | Hours above threshold | 0.5 |
| Wood stove | `sensor.wood_stove_burning` | Hours above threshold, or Days above threshold for heating days | 0.5 |

The same works for anything with an on/off state: a fan, a garage door, presence in a room.

### Desk, standing desk, workshop

- **Desk in use**: the power of the desk's plug with *Hours above threshold*, threshold just above the
  standby power of the screens (e.g. 12 W).
- **Standing at the desk**: the height sensor of a standing desk with *Hours above threshold*, threshold
  between sitting and standing height (e.g. 95 cm).

### Climate and other measurements

- **Average** humidity of the bathroom or CO₂ of the bedroom.
- **Lowest** temperature in a shed or greenhouse, **Highest** in the attic.
- **Hours above threshold** for "hours with CO₂ above 1200 ppm" or "hours the attic was above 28 °C".

## Changing or removing a figure

Remove a figure under **Configure → Remove your own figures** and add it again with other settings. After a
change, the reports are re-made in the background, so earlier months use the new settings too (as far as the
statistic has history).
