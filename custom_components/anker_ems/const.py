from __future__ import annotations

DOMAIN = "anker_ems"
NAME = "Dummy OS EMS"
VERSION = "0.0.1-alpha.4"

CONF_SIMULATION_MODE = "simulation_mode"

CONF_SOC_ENTITY = "soc_entity"
CONF_DEVICE_STATUS_ENTITY = "device_status_entity"
CONF_CHARGE_POWER_ENTITY = "charge_power_entity"
CONF_DISCHARGE_POWER_ENTITY = "discharge_power_entity"
CONF_GRID_IMPORT_POWER_ENTITY = "grid_import_power_entity"
CONF_GRID_EXPORT_POWER_ENTITY = "grid_export_power_entity"
CONF_OPERATING_MODE_ENTITY = "operating_mode_entity"
CONF_ACTION_DIRECTION_ENTITY = "action_direction_entity"
CONF_POWER_SETPOINT_ENTITY = "power_setpoint_entity"

PLATFORMS = ["sensor", "binary_sensor"]

DEFAULT_BATTERY_CAPACITY_KWH = 7.2
MIN_SOC_PERCENT = 5
MAX_SOC_PERCENT = 100

REQUIRED_SOURCE_KEYS = (
    CONF_SOC_ENTITY,
    CONF_DEVICE_STATUS_ENTITY,
    CONF_CHARGE_POWER_ENTITY,
    CONF_DISCHARGE_POWER_ENTITY,
    CONF_OPERATING_MODE_ENTITY,
    CONF_ACTION_DIRECTION_ENTITY,
    CONF_POWER_SETPOINT_ENTITY,
)
