"""配置流程：杭州峰谷电价集成。"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_RESET,
    CONF_ENERGY_SENSOR,
    CONF_INITIAL_YEARLY_ENERGY,
    CONF_PEAK_END,
    CONF_PEAK_START,
    CONF_TIER,
    CONF_TIER1_PEAK,
    CONF_TIER1_VALLEY,
    CONF_TIER2_PEAK,
    CONF_TIER2_VALLEY,
    CONF_TIER3_PEAK,
    CONF_TIER3_VALLEY,
    DEFAULT_AUTO_RESET,
    DEFAULT_ENERGY_SENSOR,
    DEFAULT_INITIAL_YEARLY_ENERGY,
    DEFAULT_PEAK_END,
    DEFAULT_PEAK_START,
    DEFAULT_PRICES,
    DEFAULT_TIER,
    DOMAIN,
    TARIFF_PEAK,
    TARIFF_VALLEY,
    TIER_1,
    TIER_2,
    TIER_3,
    TIER_AUTO,
    TIER_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


class HangzhouElectricityConfigFlow(ConfigFlow, domain=DOMAIN):
    """处理杭州峰谷电价的配置流程。"""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """获取选项流程。"""
        return HangzhouElectricityOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """处理用户初始配置。"""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            # 校验峰时段
            peak_start = user_input[CONF_PEAK_START]
            peak_end = user_input[CONF_PEAK_END]
            if peak_start == peak_end:
                errors[CONF_PEAK_START] = "peak_hours_invalid"
            else:
                return self.async_create_entry(
                    title="杭州峰谷电价",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PEAK_START, default=DEFAULT_PEAK_START
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=23,
                            mode=selector.NumberSelectorMode.SLIDER,
                        )
                    ),
                    vol.Required(
                        CONF_PEAK_END, default=DEFAULT_PEAK_END
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=24,
                            mode=selector.NumberSelectorMode.SLIDER,
                        )
                    ),
                    vol.Required(CONF_TIER, default=DEFAULT_TIER): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=k, label=v)
                                for k, v in TIER_OPTIONS.items()
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_INITIAL_YEARLY_ENERGY, default=DEFAULT_INITIAL_YEARLY_ENERGY
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            step=0.1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )


class HangzhouElectricityOptionsFlow(OptionsFlow):
    """处理选项配置。"""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """初始化选项流程。"""
        self._config_entry = config_entry

    @property
    def config_entry(self) -> ConfigEntry:
        """返回配置项。"""
        return self._config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """管理选项。"""
        errors: dict[str, str] = {}

        if user_input is not None:
            peak_start = user_input[CONF_PEAK_START]
            peak_end = user_input[CONF_PEAK_END]
            if peak_start == peak_end:
                errors[CONF_PEAK_START] = "peak_hours_invalid"
            else:
                return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.data
        options = self.config_entry.options

        peak_start = options.get(CONF_PEAK_START, data.get(CONF_PEAK_START, DEFAULT_PEAK_START))
        peak_end = options.get(CONF_PEAK_END, data.get(CONF_PEAK_END, DEFAULT_PEAK_END))
        tier = options.get(CONF_TIER, data.get(CONF_TIER, DEFAULT_TIER))

        tier1_peak = options.get(CONF_TIER1_PEAK, DEFAULT_PRICES[TIER_1][TARIFF_PEAK])
        tier1_valley = options.get(CONF_TIER1_VALLEY, DEFAULT_PRICES[TIER_1][TARIFF_VALLEY])
        tier2_peak = options.get(CONF_TIER2_PEAK, DEFAULT_PRICES[TIER_2][TARIFF_PEAK])
        tier2_valley = options.get(CONF_TIER2_VALLEY, DEFAULT_PRICES[TIER_2][TARIFF_VALLEY])
        tier3_peak = options.get(CONF_TIER3_PEAK, DEFAULT_PRICES[TIER_3][TARIFF_PEAK])
        tier3_valley = options.get(CONF_TIER3_VALLEY, DEFAULT_PRICES[TIER_3][TARIFF_VALLEY])

        energy_sensor = options.get(CONF_ENERGY_SENSOR, data.get(CONF_ENERGY_SENSOR, DEFAULT_ENERGY_SENSOR))
        auto_reset = options.get(CONF_AUTO_RESET, data.get(CONF_AUTO_RESET, DEFAULT_AUTO_RESET))
        initial_yearly_energy = options.get(
            CONF_INITIAL_YEARLY_ENERGY,
            data.get(CONF_INITIAL_YEARLY_ENERGY, DEFAULT_INITIAL_YEARLY_ENERGY),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PEAK_START, default=peak_start): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=23, mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Required(CONF_PEAK_END, default=peak_end): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=24, mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Required(CONF_TIER, default=tier): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=k, label=v)
                                for k, v in TIER_OPTIONS.items()
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_TIER1_PEAK, default=tier1_peak): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, step=0.001, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(CONF_TIER1_VALLEY, default=tier1_valley): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, step=0.001, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(CONF_TIER2_PEAK, default=tier2_peak): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, step=0.001, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(CONF_TIER2_VALLEY, default=tier2_valley): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, step=0.001, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(CONF_TIER3_PEAK, default=tier3_peak): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, step=0.001, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(CONF_TIER3_VALLEY, default=tier3_valley): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, step=0.001, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Optional(CONF_ENERGY_SENSOR, default=energy_sensor): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="energy",
                        )
                    ),
                    vol.Required(CONF_AUTO_RESET, default=auto_reset): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_INITIAL_YEARLY_ENERGY, default=initial_yearly_energy
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            step=0.1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )
