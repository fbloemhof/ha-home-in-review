"""Constants for Home in Review."""

DOMAIN = "home_in_review"
NAME = "Home in Review"
SCHEMA_VERSION = 1

# Options
CONF_NOTIFY = "notify_services"
CONF_ADMIN_ONLY = "admin_only"
CONF_THEME = "default_theme"
CONF_REPORT_DAY = "report_day"
CONF_REPORT_TIME = "report_time"
CONF_EXCLUDED_AREAS = "excluded_areas"
CONF_OUTDOOR_SENSOR = "outdoor_sensor"
CONF_FIXED_DAILY = "fixed_costs_daily"
CONF_FIXED_MONTHLY = "fixed_costs_monthly"
CONF_MAX_HOURLY_KWH = "max_hourly_kwh"
CONF_BACKFILL_MONTHS = "backfill_months"
CONF_USE_OPEN_METEO = "use_open_meteo"
CONF_RAIN_SENSOR = "rain_sensor"
CONF_EVCC_URL = "evcc_url"
CONF_YEAR_START = "year_start_month"
CONF_GAS_BASE = "gas_base_per_day"
CONF_HP_DEVICES = "heat_pump_devices"
CONF_HP_HEAT = "heat_pump_heat_sensor"
CONF_CAR_ODOMETERS = "car_odometers"
CONF_CAR_CHARGERS = "car_chargers"
CONF_TM_URL = "teslamate_grafana_url"
CONF_TM_TOKEN = "teslamate_grafana_token"
CONF_TM_HOME = "teslamate_home_geofence"
CONF_AI_TASK = "ai_task_entity"
CONF_AI_INSTRUCTIONS = "ai_instructions"
CONF_TILES = "custom_tiles"

DEFAULT_REPORT_DAY = 1
DEFAULT_REPORT_TIME = "07:00:00"
DEFAULT_MAX_HOURLY_KWH = 25.0  # about a 3 x 35 A connection; 3 x 25 A is ~17 kWh
DEFAULT_BACKFILL_MONTHS = 12

# Storage: one JSON document per month in <config>/home_in_review/
STORAGE_DIR = "home_in_review"

URL_BASE = "/api/home_in_review"
PANEL_URL = "home-in-review"
STATIC_URL = "/home_in_review_static"

# Words that mark an area or floor as outdoors. A word matches a whole word in the name, or the end of a compound
# word ("Achtertuin", "Backyard", "Vorgarten"), but not its start ("Tuinkamer" is a room). Garages and storage
# rooms are deliberately not listed: whether they count as indoors differs per home (set it in the options).
OUTDOOR_AREA_HINTS = (
    "garden", "tuin", "outside", "outdoor", "outdoors", "buiten", "balcony", "balkon", "terrace", "terras",
    "patio", "yard", "shed", "schuur", "carport", "driveway", "oprit", "porch", "veranda",
    "garten", "jardin", "jardín", "giardino", "außen", "aussen", "exterieur", "extérieur",
)
