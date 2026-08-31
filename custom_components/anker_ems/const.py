from __future__ import annotations

DOMAIN = "anker_ems"
NAME = "Dummy OS EMS"
VERSION = "0.0.1-alpha.66"

CONF_SIMULATION_MODE = "simulation_mode"

# Central electrical connection / battery power safety limits.
CONF_ELECTRICAL_PROFILE = "electrical_profile"
CONF_MAX_CHARGE_POWER_W = "max_charge_power_w"
CONF_MAX_DISCHARGE_POWER_W = "max_discharge_power_w"

ELECTRICAL_PROFILE_DEDICATED = "dedicated_group"
ELECTRICAL_PROFILE_SHARED = "shared_group"

# Fail-safe defaults for upgraded entries that have not yet explicitly chosen
# their electrical installation profile in Options Flow.
DEFAULT_ELECTRICAL_PROFILE = ELECTRICAL_PROFILE_SHARED
DEFAULT_SHARED_MAX_POWER_W = 800
DEFAULT_DEDICATED_MAX_CHARGE_POWER_W = 3500
DEFAULT_DEDICATED_MAX_DISCHARGE_POWER_W = 3500
ABSOLUTE_MAX_CHARGE_POWER_W = 3500
ABSOLUTE_MAX_DISCHARGE_POWER_W = 3500
MIN_CONTROL_POWER_W = 100

CONF_SOC_ENTITY = "soc_entity"
CONF_DEVICE_STATUS_ENTITY = "device_status_entity"
CONF_CHARGE_POWER_ENTITY = "charge_power_entity"
CONF_DISCHARGE_POWER_ENTITY = "discharge_power_entity"
CONF_GRID_IMPORT_POWER_ENTITY = "grid_import_power_entity"
CONF_GRID_EXPORT_POWER_ENTITY = "grid_export_power_entity"
CONF_OPERATING_MODE_ENTITY = "operating_mode_entity"
CONF_ACTION_DIRECTION_ENTITY = "action_direction_entity"
CONF_POWER_SETPOINT_ENTITY = "power_setpoint_entity"


# Alpha40.3 supplier-independent market-price architecture.
CONF_MARKET_PRICE_ARCHITECTURE_ENABLED = "market_price_architecture_enabled"
CONF_MARKET_PRICE_ENTITY = "market_price_entity"
CONF_IMPORT_MARKUP_PER_KWH = "import_markup_per_kwh"
CONF_EXPORT_MARKUP_PER_KWH = "export_markup_per_kwh"
CONF_TARIFF_RESOLUTION = "tariff_resolution"

TARIFF_RESOLUTION_HOURLY = "hourly"
TARIFF_RESOLUTION_QUARTER_HOURLY = "quarter_hourly"
DEFAULT_TARIFF_RESOLUTION = TARIFF_RESOLUTION_HOURLY
DEFAULT_MARKET_PRICE_ENTITY = "sensor.stroomvoorspeller_data"
DEFAULT_IMPORT_MARKUP_PER_KWH = 0.1288
DEFAULT_EXPORT_MARKUP_PER_KWH = 0.1288

# Forecast / source entities.
CONF_KNOWN_PRICE_ENTITY = "known_price_entity"
CONF_FORECAST_PRICE_ENTITY = "forecast_price_entity"
CONF_HOME_FORECAST_ENTITY = "home_forecast_entity"
CONF_SOLAR_TODAY_ENTITY = "solar_today_entity"
CONF_SOLAR_TOMORROW_ENTITY = "solar_tomorrow_entity"
CONF_SOLAR_DAY3_ENTITY = "solar_day3_entity"

DEFAULT_KNOWN_PRICE_ENTITY = "sensor.stroomvoorspeller_data"
DEFAULT_FORECAST_PRICE_ENTITY = "sensor.forecast_prices_all_in_data"
DEFAULT_HOME_FORECAST_ENTITY = "sensor.forecast_home_consumption_data"
DEFAULT_SOLAR_TODAY_ENTITY = "sensor.solcast_pv_forecast_forecast_today"
DEFAULT_SOLAR_TOMORROW_ENTITY = "sensor.solcast_pv_forecast_forecast_tomorrow"
DEFAULT_SOLAR_DAY3_ENTITY = "sensor.solcast_pv_forecast_forecast_day_3"

# Source monitor entities.
CONF_MONITOR_ENERGYZERO_ENTITY = "monitor_energyzero_entity"
CONF_MONITOR_STROOMVOORSPELLER_ENTITY = "monitor_stroomvoorspeller_entity"
CONF_MONITOR_SOLCAST_API_ENTITY = "monitor_solcast_api_entity"

DEFAULT_MONITOR_ENERGYZERO_ENTITY = "sensor.energyzero_today_energy_usage"
DEFAULT_MONITOR_STROOMVOORSPELLER_ENTITY = "sensor.stroomvoorspeller_data"
DEFAULT_MONITOR_SOLCAST_API_ENTITY = "sensor.solcast_pv_forecast_api_used"

FORECAST_HORIZON_HOURS = 72
DEFAULT_BATTERY_CAPACITY_KWH = 7.2
CONF_SOFTWARE_RESERVE_PERCENT = "software_reserve_percent"
DEFAULT_SOFTWARE_RESERVE_PERCENT = 7.0
CONF_CHARGE_EFFICIENCY_PERCENT = "charge_efficiency_percent"
CONF_DISCHARGE_EFFICIENCY_PERCENT = "discharge_efficiency_percent"
CONF_MINIMUM_TRADE_MARGIN = "minimum_trade_margin"
DEFAULT_CHARGE_EFFICIENCY_PERCENT = 92.0
DEFAULT_DISCHARGE_EFFICIENCY_PERCENT = 92.0
DEFAULT_MINIMUM_TRADE_MARGIN = 0.10
MIN_ACTIONABLE_SAFETY_CHARGE_KWH = 0.10
PLAN_SLOT_COUNT = 3
