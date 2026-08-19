from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    NAME,
    CONF_SIMULATION_MODE,
    CONF_SOC_ENTITY,
    CONF_DEVICE_STATUS_ENTITY,
    CONF_CHARGE_POWER_ENTITY,
    CONF_DISCHARGE_POWER_ENTITY,
    CONF_GRID_IMPORT_POWER_ENTITY,
    CONF_GRID_EXPORT_POWER_ENTITY,
    CONF_OPERATING_MODE_ENTITY,
    CONF_ACTION_DIRECTION_ENTITY,
    CONF_POWER_SETPOINT_ENTITY,
    CONF_KNOWN_PRICE_ENTITY,
    CONF_FORECAST_PRICE_ENTITY,
    CONF_HOME_FORECAST_ENTITY,
    CONF_SOLAR_TODAY_ENTITY,
    CONF_SOLAR_TOMORROW_ENTITY,
    CONF_SOLAR_DAY3_ENTITY,
    CONF_SOFTWARE_RESERVE_PERCENT,
    DEFAULT_SOFTWARE_RESERVE_PERCENT,
    DEFAULT_KNOWN_PRICE_ENTITY,
    DEFAULT_FORECAST_PRICE_ENTITY,
    DEFAULT_HOME_FORECAST_ENTITY,
    DEFAULT_SOLAR_TODAY_ENTITY,
    DEFAULT_SOLAR_TOMORROW_ENTITY,
    DEFAULT_SOLAR_DAY3_ENTITY,
    CONF_MONITOR_ENERGYZERO_ENTITY,
    CONF_MONITOR_STROOMVOORSPELLER_ENTITY,
    CONF_MONITOR_SOLCAST_API_ENTITY,
    DEFAULT_MONITOR_ENERGYZERO_ENTITY,
    DEFAULT_MONITOR_STROOMVOORSPELLER_ENTITY,
    DEFAULT_MONITOR_SOLCAST_API_ENTITY,
)


def _entity_selector(domain: str | None = None) -> selector.EntitySelector:
    config = selector.EntitySelectorConfig(domain=domain) if domain else selector.EntitySelectorConfig()
    return selector.EntitySelector(config)


class AnkerEmsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id("dummy_os_ems_main")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=NAME, data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SIMULATION_MODE, default=True): selector.BooleanSelector(),
                vol.Required(CONF_SOC_ENTITY): _entity_selector("sensor"),
                vol.Required(CONF_DEVICE_STATUS_ENTITY): _entity_selector("sensor"),
                vol.Required(CONF_CHARGE_POWER_ENTITY): _entity_selector("sensor"),
                vol.Required(CONF_DISCHARGE_POWER_ENTITY): _entity_selector("sensor"),
                vol.Optional(CONF_GRID_IMPORT_POWER_ENTITY): _entity_selector("sensor"),
                vol.Optional(CONF_GRID_EXPORT_POWER_ENTITY): _entity_selector("sensor"),
                vol.Required(CONF_OPERATING_MODE_ENTITY): _entity_selector("select"),
                vol.Required(CONF_ACTION_DIRECTION_ENTITY): _entity_selector(),
                vol.Required(CONF_POWER_SETPOINT_ENTITY): _entity_selector(),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return AnkerEmsOptionsFlow(config_entry)


class AnkerEmsOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_KNOWN_PRICE_ENTITY,
                    default=options.get(CONF_KNOWN_PRICE_ENTITY, DEFAULT_KNOWN_PRICE_ENTITY),
                ): _entity_selector("sensor"),
                vol.Optional(
                    CONF_FORECAST_PRICE_ENTITY,
                    default=options.get(CONF_FORECAST_PRICE_ENTITY, DEFAULT_FORECAST_PRICE_ENTITY),
                ): _entity_selector("sensor"),
                vol.Optional(
                    CONF_HOME_FORECAST_ENTITY,
                    default=options.get(CONF_HOME_FORECAST_ENTITY, DEFAULT_HOME_FORECAST_ENTITY),
                ): _entity_selector("sensor"),
                vol.Optional(
                    CONF_SOLAR_TODAY_ENTITY,
                    default=options.get(CONF_SOLAR_TODAY_ENTITY, DEFAULT_SOLAR_TODAY_ENTITY),
                ): _entity_selector("sensor"),
                vol.Optional(
                    CONF_SOLAR_TOMORROW_ENTITY,
                    default=options.get(CONF_SOLAR_TOMORROW_ENTITY, DEFAULT_SOLAR_TOMORROW_ENTITY),
                ): _entity_selector("sensor"),
                vol.Optional(
                    CONF_SOLAR_DAY3_ENTITY,
                    default=options.get(CONF_SOLAR_DAY3_ENTITY, DEFAULT_SOLAR_DAY3_ENTITY),
                ): _entity_selector("sensor"),
                vol.Optional(
                    CONF_SOFTWARE_RESERVE_PERCENT,
                    default=options.get(
                        CONF_SOFTWARE_RESERVE_PERCENT, DEFAULT_SOFTWARE_RESERVE_PERCENT
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=30, step=1, mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%"
                    )
                ),
                vol.Optional(
                    CONF_MONITOR_ENERGYZERO_ENTITY,
                    default=options.get(CONF_MONITOR_ENERGYZERO_ENTITY, DEFAULT_MONITOR_ENERGYZERO_ENTITY),
                ): _entity_selector("sensor"),
                vol.Optional(
                    CONF_MONITOR_STROOMVOORSPELLER_ENTITY,
                    default=options.get(CONF_MONITOR_STROOMVOORSPELLER_ENTITY, DEFAULT_MONITOR_STROOMVOORSPELLER_ENTITY),
                ): _entity_selector("sensor"),
                vol.Optional(
                    CONF_MONITOR_SOLCAST_API_ENTITY,
                    default=options.get(CONF_MONITOR_SOLCAST_API_ENTITY, DEFAULT_MONITOR_SOLCAST_API_ENTITY),
                ): _entity_selector("sensor"),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
