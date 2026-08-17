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
)


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

            return self.async_create_entry(
                title=NAME,
                data=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SIMULATION_MODE,
                    default=True,
                ): selector.BooleanSelector(),

                vol.Required(
                    CONF_SOC_ENTITY
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                vol.Required(
                    CONF_DEVICE_STATUS_ENTITY
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                vol.Required(
                    CONF_CHARGE_POWER_ENTITY
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                vol.Required(
                    CONF_DISCHARGE_POWER_ENTITY
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                vol.Optional(
                    CONF_GRID_IMPORT_POWER_ENTITY
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                vol.Optional(
                    CONF_GRID_EXPORT_POWER_ENTITY
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                vol.Required(
                    CONF_OPERATING_MODE_ENTITY
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="select")
                ),

                vol.Required(
                    CONF_ACTION_DIRECTION_ENTITY
                ): selector.EntitySelector(),

                vol.Required(
                    CONF_POWER_SETPOINT_ENTITY
                ): selector.EntitySelector(),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
