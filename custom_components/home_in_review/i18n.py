"""Report texts and number formatting. Add a language by adding a block to TEXTS (missing keys fall back to English)."""
from __future__ import annotations

TEXTS: dict[str, dict[str, object]] = {
    "en": {
        "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                   "October", "November", "December"],
        "months_short": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "title": "Home in Review",
        "cover_sub": "how the house did",
        "used": "used at home",
        "net_cost": "energy cost",
        "from_sun": "from the sun",
        "outside": "average outside",
        "water": "water",
        "gas": "gas",
        # sections
        "s_energy": "Electricity", "s_cost": "Costs", "s_solar": "Solar", "s_battery": "Batteries",
        "s_devices": "Where it went", "s_rhythm": "Daily rhythm", "s_weather": "Weather", "s_indoor": "Indoors",
        "s_water": "Water", "s_gas": "Gas", "s_about": "About this report",
        # comparisons
        "avg": "avg.", "average": "Average", "same": "about the same as usual", "more": "more", "less": "less",
        "than_avg": "than average", "last_year": "last year", "no_data": "no data",
        "per_month": "per month", "trend_use": "Use per month", "trend_cost": "Costs per month",
        "trend_solar": "Solar per month", "trend_temp": "Temperature per month", "trend_water": "Water per month",
        "trend_gas": "Gas per month",
        # energy
        "h_energy_more": "The house used <em>{pct} more</em> electricity than {ref}.",
        "h_energy_less": "The house used <em>{pct} less</em> electricity than {ref}.",
        "h_energy_same": "Electricity use was <em>in line</em> with {ref2}.",
        "ref_ly": "{month} last year", "ref_avg": "average", "ref2_ly": "{month} last year", "ref2_avg": "the average",
        "h_energy_first": "The house used <em>{v}</em> of electricity.",
        "imported": "From the grid", "exported": "Returned to the grid", "solar": "Solar",
        "self_sufficiency": "Self-sufficiency", "base_load": "Base load", "peak": "Busiest hour",
        "per_day": "per day", "kwh_per_day": "kWh per day", "load": "Used",
        # costs
        "h_cost_more": "Energy cost <em>{v} more</em> than {ref}.",
        "h_cost_less": "Energy cost <em>{v} less</em> than {ref}.",
        "h_cost_same": "Energy costs were <em>in line</em> with {ref2}.",
        "h_cost_first": "Energy cost <em>{v}</em> this month.",
        "h_cost_earned": "The house <em>earned</em> money on energy this month.",
        "paid": "Paid", "received": "Received", "import_cost": "Electricity bought", "compensation": "Electricity sold",
        "fixed": "Fixed costs", "water_cost": "Water", "gas_cost": "Gas", "total": "Total", "credit": "Credit",
        "avg_price": "Average price paid", "cost_note": "Estimate from the energy dashboard's cost statistics (hourly). Your actual bill can differ.",
        "cost_note_fixed": "Fixed costs as configured.",
        # solar
        "h_solar": "<em>{share}</em> of the solar power was used at home.",
        "self_used": "Used at home", "sun_hours": "Sunshine", "vs_normal": "normal", "self_used_short": "self-used",
        # battery
        "h_battery": "The batteries stored <em>{v}</em> and gave back {back}.",
        "charged": "Charged", "discharged": "Discharged", "efficiency": "Round-trip efficiency", "cycles": "cycles",
        # devices
        "h_devices": "<em>{name}</em> was the biggest user, with {share} of the total.",
        "untracked": "Not measured separately", "others": "Other ({n})", "device": "Device", "value": "Value",
        "share": "Share", "dev_note": "Value = the device's hourly use times the grid price in that hour. Devices without readings this month are left out: {names}.",
        "partial": "readings incomplete",
        # rhythm
        "h_rhythm": "The house was busiest around <em>{hour}</em>.",
        "rhythm_note": "Average power per hour of the day, everything included.",
        "base_note": "Base load is the lowest level the house rarely drops below (5th percentile of hourly use).",
        # weather
        "h_weather_warm": "A <em>warmer</em> {month} than normal: {delta} above the long-term average.",
        "h_weather_cold": "A <em>colder</em> {month} than normal: {delta} below the long-term average.",
        "h_weather_normal": "A <em>normal</em> {month}, close to the long-term average.",
        "h_weather_plain": "It was <em>{v}</em> on average outside.",
        "avg_temp": "Average", "coldest": "Lowest", "warmest": "Highest", "frost_days": "Frost days",
        "summer_days": "Summer days (25°+)", "degree_days": "Heating degree days", "rain": "Precipitation",
        "weather_note": "Weather from Open-Meteo (ERA5 reanalysis) for your area; normal = 1991–2020.",
        "weather_note_sensor": "Temperature from your outdoor sensor; rain, sunshine and normals from Open-Meteo (1991–2020).",
        "band": "outside, low to high", "mean_line": "outside, average", "normal_line": "normal",
        # indoor
        "h_indoor": "Inside it was <em>{v}</em> on average; {warm} was the warmest room.",
        "room": "Room", "temp": "Temperature", "humidity": "Humidity", "co2": "CO₂", "humid_hours": "hours >70%",
        "co2_high": "time >1000 ppm",
        "indoor_note": "Median per area of all temperature, humidity and CO₂ sensors with long-term statistics. Excluded areas can be changed in the integration options.",
        # water/gas
        "h_water": "The household used <em>{v}</em> of water, {pd} per day.",
        "h_gas": "The house used <em>{v}</em> of gas.",
        # about
        "about_sources": "Sources", "src_energy": "Energy dashboard of Home Assistant",
        "src_weather": "Open-Meteo weather archive", "src_sensors": "{n} climate sensors in {a} areas",
        "glitches": "Skipped implausible meter jumps: {list}.",
        "partial_month": "Grid readings start on {d}; this month is incomplete.",
        "excl_auto": "Left out of the indoor climate because their name says outdoors: {list}. Change this in the integration options.",
        "excl_set": "Left out of the indoor climate (set in the options): {list}.",
        "drop_not_room_sensor": "Temperatures not counted because the room has a dedicated climate sensor (temperature and humidity): {list}.",
        "drop_co2_module": "Not counted: the temperature of CO₂ modules without humidity, which measure their own chip: {list}.",
        "drop_implausible": "Not counted because the values don't fit a room (e.g. water or freezer temperatures): {list}.",
        "drop_coverage": "Not counted because of too few readings this month: {list}.",
        "drop_no_area": "{n} climate sensors have no area and were not counted.",
        "generated": "Generated {d}", "prev": "Previous", "next": "Next",
        "made_with": "Home in Review is open source and was built with the help of AI (Claude).",
        "theme": "Theme", "themes": {"auto": "auto", "light": "light", "dark": "dark", "night": "night", "mono": "mono"},
        "index_title": "All reports", "index_empty": "No reports yet. The first one is generated after the first full month, or start a backfill from the integration.",
    },
    "nl": {
        "months": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
                   "oktober", "november", "december"],
        "months_short": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
        "cover_sub": "de stand van het huis",
        "used": "stroom in huis", "net_cost": "energiekosten", "from_sun": "van de zon", "outside": "gemiddeld buiten",
        "water": "water", "gas": "gas",
        "s_energy": "Stroom", "s_cost": "Kosten", "s_solar": "Zon", "s_battery": "Batterijen",
        "s_devices": "Waar ging het heen", "s_rhythm": "Dagritme", "s_weather": "Weer", "s_indoor": "Binnen",
        "s_water": "Water", "s_gas": "Gas", "s_about": "Over dit rapport",
        "avg": "gem.", "average": "Gemiddeld", "same": "ongeveer zoals altijd", "more": "meer", "less": "minder",
        "than_avg": "dan gemiddeld", "last_year": "vorig jaar", "no_data": "geen data",
        "per_month": "per maand", "trend_use": "Verbruik per maand", "trend_cost": "Kosten per maand",
        "trend_solar": "Zon per maand", "trend_temp": "Temperatuur per maand", "trend_water": "Water per maand",
        "trend_gas": "Gas per maand",
        "h_energy_more": "Het huis gebruikte <em>{pct} meer</em> stroom dan {ref}.",
        "h_energy_less": "Het huis gebruikte <em>{pct} minder</em> stroom dan {ref}.",
        "h_energy_same": "Het stroomverbruik was <em>vergelijkbaar</em> met {ref2}.",
        "ref_ly": "{month} vorig jaar", "ref_avg": "gemiddeld", "ref2_ly": "{month} vorig jaar", "ref2_avg": "het gemiddelde",
        "h_energy_first": "Het huis gebruikte <em>{v}</em> stroom.",
        "imported": "Uit het net", "exported": "Teruggeleverd", "solar": "Zon",
        "self_sufficiency": "Zelfvoorzienend", "base_load": "Sluipverbruik", "peak": "Drukste uur",
        "per_day": "per dag", "kwh_per_day": "kWh per dag", "load": "Verbruikt",
        "h_cost_more": "Energie kostte <em>{v} meer</em> dan {ref}.",
        "h_cost_less": "Energie kostte <em>{v} minder</em> dan {ref}.",
        "h_cost_same": "De energiekosten waren <em>vergelijkbaar</em> met {ref2}.",
        "h_cost_first": "Energie kostte deze maand <em>{v}</em>.",
        "h_cost_earned": "Het huis <em>verdiende</em> deze maand geld met energie.",
        "paid": "Betaald", "received": "Terug", "import_cost": "Stroom ingekocht", "compensation": "Stroom verkocht",
        "fixed": "Vaste kosten", "water_cost": "Water", "gas_cost": "Gas", "total": "Totaal", "credit": "Tegoed",
        "avg_price": "Gemiddeld betaalde prijs",
        "cost_note": "Schatting uit de kostenstatistieken van het energiedashboard (per uur). Je echte rekening kan afwijken.",
        "cost_note_fixed": "Vaste kosten zoals ingesteld.",
        "h_solar": "<em>{share}</em> van de zonnestroom werd in huis gebruikt.",
        "self_used": "Zelf gebruikt", "sun_hours": "Zonneschijn", "vs_normal": "normaal", "self_used_short": "zelf gebruikt",
        "h_battery": "De batterijen sloegen <em>{v}</em> op en gaven {back} terug.",
        "charged": "Geladen", "discharged": "Ontladen", "efficiency": "Rendement", "cycles": "cycli",
        "h_devices": "<em>{name}</em> gebruikte het meest: {share} van het totaal.",
        "untracked": "Niet apart gemeten", "others": "Overige ({n})", "device": "Apparaat", "value": "Waarde",
        "share": "Aandeel", "dev_note": "Waarde = verbruik per uur maal de netprijs van dat uur. Apparaten zonder meting deze maand zijn weggelaten: {names}.",
        "partial": "meting onvolledig",
        "h_rhythm": "Het huis was het drukst rond <em>{hour}</em>.",
        "rhythm_note": "Gemiddeld vermogen per uur van de dag, alles inbegrepen.",
        "base_note": "Sluipverbruik is het niveau waar het huis zelden onder komt (5e percentiel van het uurverbruik).",
        "h_weather_warm": "Een <em>warmere</em> {month} dan normaal: {delta} boven het langjarig gemiddelde.",
        "h_weather_cold": "Een <em>koudere</em> {month} dan normaal: {delta} onder het langjarig gemiddelde.",
        "h_weather_normal": "Een <em>normale</em> {month}, dicht bij het langjarig gemiddelde.",
        "h_weather_plain": "Het was buiten gemiddeld <em>{v}</em>.",
        "avg_temp": "Gemiddeld", "coldest": "Laagste", "warmest": "Hoogste", "frost_days": "Vorstdagen",
        "summer_days": "Zomerse dagen (25°+)", "degree_days": "Graaddagen", "rain": "Neerslag",
        "weather_note": "Weer van Open-Meteo (ERA5-heranalyse) voor jouw omgeving; normaal = 1991–2020.",
        "weather_note_sensor": "Temperatuur van je buitensensor; neerslag, zon en normalen van Open-Meteo (1991–2020).",
        "band": "buiten, laag tot hoog", "mean_line": "buiten, gemiddeld", "normal_line": "normaal",
        "h_indoor": "Binnen was het gemiddeld <em>{v}</em>; {warm} was de warmste ruimte.",
        "room": "Ruimte", "temp": "Temperatuur", "humidity": "Luchtvochtigheid", "co2": "CO₂", "humid_hours": "uur >70%",
        "co2_high": "tijd >1000 ppm",
        "indoor_note": "Mediaan per ruimte van alle temperatuur-, vocht- en CO₂-sensoren met langetermijnstatistieken. Uitgesloten ruimtes pas je aan in de opties van de integratie.",
        "h_water": "Het huishouden gebruikte <em>{v}</em> water, {pd} per dag.",
        "h_gas": "Het huis gebruikte <em>{v}</em> gas.",
        "about_sources": "Bronnen", "src_energy": "Energiedashboard van Home Assistant",
        "src_weather": "Weerarchief van Open-Meteo", "src_sensors": "{n} klimaatsensoren in {a} ruimtes",
        "glitches": "Onmogelijke meterstanden overgeslagen: {list}.",
        "partial_month": "Netmetingen beginnen op {d}; deze maand is onvolledig.",
        "excl_auto": "Niet meegeteld voor het binnenklimaat omdat de naam op buiten wijst: {list}. Aan te passen in de opties van de integratie.",
        "excl_set": "Niet meegeteld voor het binnenklimaat (ingesteld in de opties): {list}.",
        "drop_not_room_sensor": "Temperaturen niet meegeteld omdat de ruimte een echte klimaatsensor heeft (temperatuur en vocht): {list}.",
        "drop_co2_module": "Niet meegeteld: de temperatuur van CO₂-modules zonder vochtmeting, die hun eigen chip meten: {list}.",
        "drop_implausible": "Niet meegeteld omdat de waarden niet bij een kamer passen (bijv. water- of vriezertemperaturen): {list}.",
        "drop_coverage": "Niet meegeteld wegens te weinig metingen deze maand: {list}.",
        "drop_no_area": "{n} klimaatsensoren hebben geen ruimte en zijn niet meegeteld.",
        "generated": "Gemaakt op {d}", "prev": "Vorige", "next": "Volgende",
        "made_with": "Home in Review is open source en gebouwd met hulp van AI (Claude).",
        "theme": "Thema", "themes": {"auto": "auto", "light": "licht", "dark": "donker", "night": "nacht", "mono": "zwart-wit"},
        "index_title": "Alle rapporten", "index_empty": "Nog geen rapporten. Het eerste verschijnt na de eerste volle maand, of start een backfill via de integratie.",
    },
}

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CHF": "CHF", "SEK": "kr", "NOK": "kr", "DKK": "kr",
                    "AUD": "A$", "CAD": "C$", "NZD": "NZ$", "PLN": "zł", "CZK": "Kč", "INR": "₹"}


class Lang:
    def __init__(self, lang: str, currency: str = "EUR") -> None:
        base = (lang or "en").split("-")[0].lower()
        self.code = base if base in TEXTS else "en"
        self.t = {**TEXTS["en"], **TEXTS[self.code]}
        # Decimal comma for most of continental Europe.
        self.comma = base in ("nl", "de", "fr", "es", "it", "pt", "da", "sv", "nb", "fi", "pl", "cs", "ru", "tr")
        self.currency = currency
        self.sym = CURRENCY_SYMBOLS.get(currency, currency)

    def __call__(self, key: str, **kw) -> str:
        s = self.t.get(key, key)
        return s.format(**kw) if kw else s  # type: ignore[union-attr]

    def month(self, m: int) -> str:
        return self.t["months"][m - 1]  # type: ignore[index]

    def month_short(self, m: int) -> str:
        return self.t["months_short"][m - 1]  # type: ignore[index]

    def num(self, x, d: int = 0) -> str:
        if x is None:
            return "–"
        s = f"{x:,.{d}f}"
        if self.comma:
            s = s.replace(",", " ").replace(".", ",").replace(" ", ".")
        if s.startswith("-"):
            s = "−" + s[1:]
        return "0" if s in ("−0", "−0,0", "−0.0") and d == 0 else s

    def money(self, x, d: int = 0) -> str:
        if x is None:
            return "–"
        n = self.num(abs(x), d)
        sign = "−" if x < 0 and round(abs(x), d) else ""
        if self.code == "en" or self.sym in ("$", "£", "A$", "C$", "NZ$", "₹", "¥"):
            return f"{sign}{self.sym}{n}" if len(self.sym) <= 3 and not self.sym.isalpha() else f"{sign}{n} {self.sym}"
        return f"{sign}{self.sym} {n}"

    def pct(self, x, d: int = 0) -> str:
        return "–" if x is None else f"{self.num(x * 100, d)}%"
