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
    CONF_ELECTRICAL_PROFILE,
    CONF_MAX_CHARGE_POWER_W,
    CONF_MAX_DISCHARGE_POWER_W,
    ELECTRICAL_PROFILE_DEDICATED,
    ELECTRICAL_PROFILE_SHARED,
    DEFAULT_ELECTRICAL_PROFILE,
    DEFAULT_SHARED_MAX_POWER_W,
    DEFAULT_DEDICATED_MAX_CHARGE_POWER_W,
    DEFAULT_DEDICATED_MAX_DISCHARGE_POWER_W,
    ABSOLUTE_MAX_CHARGE_POWER_W,
    ABSOLUTE_MAX_DISCHARGE_POWER_W,
    CONF_SOC_ENTITY,
    CONF_DEVICE_STATUS_ENTITY,
    CONF_CHARGE_POWER_ENTITY,
    CONF_DISCHARGE_POWER_ENTITY,
    CONF_GRID_IMPORT_POWER_ENTITY,
    CONF_GRID_EXPORT_POWER_ENTITY,
    CONF_OPERATING_MODE_ENTITY,
    CONF_ACTION_DIRECTION_ENTITY,
    CONF_POWER_SETPOINT_ENTITY,
    CONF_MARKET_PRICE_ARCHITECTURE_ENABLED,
    CONF_MARKET_PRICE_ENTITY,
    CONF_IMPORT_MARKUP_PER_KWH,
    CONF_EXPORT_MARKUP_PER_KWH,
    CONF_TARIFF_RESOLUTION,
    TARIFF_RESOLUTION_HOURLY,
    TARIFF_RESOLUTION_QUARTER_HOURLY,
    DEFAULT_TARIFF_RESOLUTION,
    DEFAULT_MARKET_PRICE_ENTITY,
    DEFAULT_IMPORT_MARKUP_PER_KWH,
    DEFAULT_EXPORT_MARKUP_PER_KWH,
    CONF_KNOWN_PRICE_ENTITY,
    CONF_FORECAST_PRICE_ENTITY,
    CONF_HOME_FORECAST_ENTITY,
    CONF_SOLAR_TODAY_ENTITY,
    CONF_SOLAR_TOMORROW_ENTITY,
    CONF_SOLAR_DAY3_ENTITY,
    CONF_SOFTWARE_RESERVE_PERCENT,
    DEFAULT_SOFTWARE_RESERVE_PERCENT,
    CONF_CHARGE_EFFICIENCY_PERCENT,
    CONF_DISCHARGE_EFFICIENCY_PERCENT,
    CONF_MINIMUM_TRADE_MARGIN,
    DEFAULT_CHARGE_EFFICIENCY_PERCENT,
    DEFAULT_DISCHARGE_EFFICIENCY_PERCENT,
    DEFAULT_MINIMUM_TRADE_MARGIN,
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
    VERSION = 2

    def __init__(self) -> None:
        self._base_data: dict[str, Any] = {}
        self._electrical_profile = DEFAULT_ELECTRICAL_PROFILE

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._base_data = dict(user_input)
            return await self.async_step_electrical_setup()

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

    async def async_step_electrical_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._electrical_profile = str(user_input[CONF_ELECTRICAL_PROFILE])
            return await self.async_step_power_limits()

        schema = vol.Schema({
            vol.Required(CONF_ELECTRICAL_PROFILE, default=DEFAULT_ELECTRICAL_PROFILE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=ELECTRICAL_PROFILE_DEDICATED, label="Eigen groep"),
                        selector.SelectOptionDict(value=ELECTRICAL_PROFILE_SHARED, label="Geen eigen groep / gedeelde groep"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        })
        return self.async_show_form(step_id="electrical_setup", data_schema=schema)

    async def async_step_power_limits(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        profile = self._electrical_profile
        profile_cap = (
            DEFAULT_SHARED_MAX_POWER_W
            if profile == ELECTRICAL_PROFILE_SHARED
            else ABSOLUTE_MAX_CHARGE_POWER_W
        )
        charge_default = (
            DEFAULT_SHARED_MAX_POWER_W
            if profile == ELECTRICAL_PROFILE_SHARED
            else DEFAULT_DEDICATED_MAX_CHARGE_POWER_W
        )
        discharge_default = (
            DEFAULT_SHARED_MAX_POWER_W
            if profile == ELECTRICAL_PROFILE_SHARED
            else DEFAULT_DEDICATED_MAX_DISCHARGE_POWER_W
        )

        if user_input is not None:
            charge = int(user_input[CONF_MAX_CHARGE_POWER_W])
            discharge = int(user_input[CONF_MAX_DISCHARGE_POWER_W])
            if charge > profile_cap or discharge > profile_cap:
                errors["base"] = "power_above_profile_limit"
            else:
                await self.async_set_unique_id("dummy_os_ems_main")
                self._abort_if_unique_id_configured()
                data = {
                    **self._base_data,
                    CONF_ELECTRICAL_PROFILE: profile,
                    CONF_MAX_CHARGE_POWER_W: charge,
                    CONF_MAX_DISCHARGE_POWER_W: discharge,
                }
                return self.async_create_entry(title=NAME, data=data)

        schema = vol.Schema({
            vol.Required(CONF_MAX_CHARGE_POWER_W, default=charge_default): selector.NumberSelector(
                selector.NumberSelectorConfig(min=100, max=profile_cap, step=100, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="W")
            ),
            vol.Required(CONF_MAX_DISCHARGE_POWER_W, default=discharge_default): selector.NumberSelector(
                selector.NumberSelectorConfig(min=100, max=profile_cap, step=100, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="W")
            ),
        })
        return self.async_show_form(step_id="power_limits", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return AnkerEmsOptionsFlow()


class AnkerEmsOptionsFlow(config_entries.OptionsFlow):

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if user_input is not None:
            profile = str(user_input.get(CONF_ELECTRICAL_PROFILE, DEFAULT_ELECTRICAL_PROFILE))
            charge = int(user_input.get(CONF_MAX_CHARGE_POWER_W, DEFAULT_SHARED_MAX_POWER_W))
            discharge = int(user_input.get(CONF_MAX_DISCHARGE_POWER_W, DEFAULT_SHARED_MAX_POWER_W))
            profile_cap = DEFAULT_SHARED_MAX_POWER_W if profile == ELECTRICAL_PROFILE_SHARED else ABSOLUTE_MAX_CHARGE_POWER_W
            if charge > profile_cap or discharge > profile_cap:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._options_schema(user_input),
                    errors={"base": "power_above_profile_limit"},
                )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self._options_schema(self.config_entry.options))

    def _options_schema(self, values: dict[str, Any]) -> vol.Schema:
        options = self.config_entry.options
        profile = str(values.get(CONF_ELECTRICAL_PROFILE, options.get(CONF_ELECTRICAL_PROFILE, self.config_entry.data.get(CONF_ELECTRICAL_PROFILE, DEFAULT_ELECTRICAL_PROFILE))))
        default_charge = int(values.get(CONF_MAX_CHARGE_POWER_W, options.get(CONF_MAX_CHARGE_POWER_W, self.config_entry.data.get(CONF_MAX_CHARGE_POWER_W, DEFAULT_SHARED_MAX_POWER_W))))
        default_discharge = int(values.get(CONF_MAX_DISCHARGE_POWER_W, options.get(CONF_MAX_DISCHARGE_POWER_W, self.config_entry.data.get(CONF_MAX_DISCHARGE_POWER_W, DEFAULT_SHARED_MAX_POWER_W))))
        return vol.Schema(
            {
                vol.Optional(CONF_ELECTRICAL_PROFILE, default=profile): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=ELECTRICAL_PROFILE_DEDICATED, label="Eigen groep"),
                            selector.SelectOptionDict(value=ELECTRICAL_PROFILE_SHARED, label="Geen eigen groep / gedeelde groep"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_MAX_CHARGE_POWER_W, default=default_charge): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=100, max=ABSOLUTE_MAX_CHARGE_POWER_W, step=100, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="W")
                ),
                vol.Optional(CONF_MAX_DISCHARGE_POWER_W, default=default_discharge): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=100, max=ABSOLUTE_MAX_DISCHARGE_POWER_W, step=100, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="W")
                ),
                vol.Optional(
                    CONF_MARKET_PRICE_ARCHITECTURE_ENABLED,
    CONF_MARKET_PRICE_ENTITY,
    CONF_IMPORT_MARKUP_PER_KWH,
    CONF_EXPORT_MARKUP_PER_KWH,
    CONF_TARIFF_RESOLUTION,
    TARIFF_RESOLUTION_HOURLY,
    TARIFF_RESOLUTION_QUARTER_HOURLY,
    DEFAULT_TARIFF_RESOLUTION,
    DEFAULT_MARKET_PRICE_ENTITY,
    DEFAULT_IMPORT_MARKUP_PER_KWH,
    DEFAULT_EXPORT_MARKUP_PER_KWH,
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
                    CONF_CHARGE_EFFICIENCY_PERCENT,
                    default=options.get(
                        CONF_CHARGE_EFFICIENCY_PERCENT, DEFAULT_CHARGE_EFFICIENCY_PERCENT
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=50, max=100, step=1, mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%"
                    )
                ),
                vol.Optional(
                    CONF_DISCHARGE_EFFICIENCY_PERCENT,
                    default=options.get(
                        CONF_DISCHARGE_EFFICIENCY_PERCENT, DEFAULT_DISCHARGE_EFFICIENCY_PERCENT
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=50, max=100, step=1, mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%"
                    )
                ),
                vol.Optional(
                    CONF_MINIMUM_TRADE_MARGIN,
                    default=options.get(
                        CONF_MINIMUM_TRADE_MARGIN, DEFAULT_MINIMUM_TRADE_MARGIN
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=1, step=0.01, mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="€/kWh"
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

