"""传感器平台：杭州峰谷电价。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import event as event_helper
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import StateType

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
    PRICE_UNIT,
    TARIFF_PEAK,
    TARIFF_VALLEY,
    TIER_1,
    TIER_1_LIMIT,
    TIER_2,
    TIER_2_LIMIT,
    TIER_3,
    TIER_AUTO,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_data"

# 电价更新间隔：每分钟检查一次是否需要切换费率
SCAN_INTERVAL = timedelta(minutes=1)

# 传感器描述
PRICE_SENSOR = SensorEntityDescription(
    key="current_price",
    name="当前电价",
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=PRICE_UNIT,
    icon="mdi:currency-cny",
)

TARIFF_SENSOR = SensorEntityDescription(
    key="current_tariff",
    name="当前费率",
    icon="mdi:clock-time-eight",
)

PEAK_ENERGY_SENSOR = SensorEntityDescription(
    key="peak_energy",
    name="峰电量",
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL_INCREASING,
    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    icon="mdi:lightning-bolt",
)

VALLEY_ENERGY_SENSOR = SensorEntityDescription(
    key="valley_energy",
    name="谷电量",
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL_INCREASING,
    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    icon="mdi:lightning-bolt-outline",
)

TIER_SENSOR = SensorEntityDescription(
    key="current_tier",
    name="当前阶梯",
    icon="mdi:stairs",
)

YEARLY_ENERGY_SENSOR = SensorEntityDescription(
    key="yearly_energy",
    name="本年度累计用电量",
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL_INCREASING,
    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    icon="mdi:calendar-account",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """根据配置项设置传感器。"""
    data = config_entry.data
    options = config_entry.options

    # 合并配置（options 优先于 data）
    merged = {**data, **options}

    peak_start = merged.get(CONF_PEAK_START, DEFAULT_PEAK_START)
    peak_end = merged.get(CONF_PEAK_END, DEFAULT_PEAK_END)
    tier = merged.get(CONF_TIER, DEFAULT_TIER)
    energy_sensor = merged.get(CONF_ENERGY_SENSOR, DEFAULT_ENERGY_SENSOR)
    auto_reset = merged.get(CONF_AUTO_RESET, DEFAULT_AUTO_RESET)
    initial_yearly_energy = float(
        merged.get(CONF_INITIAL_YEARLY_ENERGY, DEFAULT_INITIAL_YEARLY_ENERGY)
    )

    prices = {
        TIER_1: {
            TARIFF_PEAK: merged.get(CONF_TIER1_PEAK, DEFAULT_PRICES[TIER_1][TARIFF_PEAK]),
            TARIFF_VALLEY: merged.get(CONF_TIER1_VALLEY, DEFAULT_PRICES[TIER_1][TARIFF_VALLEY]),
        },
        TIER_2: {
            TARIFF_PEAK: merged.get(CONF_TIER2_PEAK, DEFAULT_PRICES[TIER_2][TARIFF_PEAK]),
            TARIFF_VALLEY: merged.get(CONF_TIER2_VALLEY, DEFAULT_PRICES[TIER_2][TARIFF_VALLEY]),
        },
        TIER_3: {
            TARIFF_PEAK: merged.get(CONF_TIER3_PEAK, DEFAULT_PRICES[TIER_3][TARIFF_PEAK]),
            TARIFF_VALLEY: merged.get(CONF_TIER3_VALLEY, DEFAULT_PRICES[TIER_3][TARIFF_VALLEY]),
        },
    }

    # 持久化存储
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored = await store.async_load() or {}

    # 若存储中无年度用电量记录，使用配置中的初始值
    if "yearly_energy" not in stored and initial_yearly_energy > 0:
        stored["yearly_energy"] = initial_yearly_energy
        await store.async_save(stored)

    coordinator = HangzhouElectricityCoordinator(
        hass, store, stored, peak_start, peak_end, tier, prices, energy_sensor, auto_reset
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    entities: list[SensorEntity] = [
        HangzhouElectricityPriceSensor(coordinator, PRICE_SENSOR),
        HangzhouElectricityTariffSensor(coordinator, TARIFF_SENSOR),
        HangzhouElectricityTierSensor(coordinator, TIER_SENSOR),
    ]

    if energy_sensor:
        entities.extend(
            [
                HangzhouElectricityEnergySensor(coordinator, PEAK_ENERGY_SENSOR, TARIFF_PEAK),
                HangzhouElectricityEnergySensor(coordinator, VALLEY_ENERGY_SENSOR, TARIFF_VALLEY),
                HangzhouElectricityYearlyEnergySensor(coordinator, YEARLY_ENERGY_SENSOR),
            ]
        )

    async_add_entities(entities)

    # 启动协调器
    await coordinator.async_start()

    # 卸载时清理
    @callback
    def _cleanup() -> None:
        coordinator.stop_listeners()

    config_entry.async_on_unload(_cleanup)


class HangzhouElectricityCoordinator:
    """协调器：管理电价计算和电量统计。"""

    def __init__(
        self,
        hass: HomeAssistant,
        store: Store,
        stored: dict[str, Any],
        peak_start: int,
        peak_end: int,
        tier: str,
        prices: dict[str, dict[str, float]],
        energy_sensor: str,
        auto_reset: bool,
    ) -> None:
        """初始化协调器。"""
        self.hass = hass
        self._store = store
        self._stored = stored
        self._peak_start = peak_start
        self._peak_end = peak_end
        self._tier = tier
        self._prices = prices
        self._energy_sensor = energy_sensor
        self._auto_reset = auto_reset

        # 峰谷电量累计
        self._peak_energy = float(stored.get("peak_energy", 0.0))
        self._valley_energy = float(stored.get("valley_energy", 0.0))
        self._yearly_energy = float(stored.get("yearly_energy", 0.0))
        self._last_source_value: float | None = None
        self._last_year = stored.get("last_year", datetime.now().year)

        self._listeners: list[Any] = []
        self._entities: list[SensorEntity] = []

    def register_entity(self, entity: SensorEntity) -> None:
        """注册实体以便更新。"""
        self._entities.append(entity)

    @callback
    def _update_entities(self) -> None:
        """更新所有注册的实体的值。"""
        for entity in self._entities:
            if isinstance(entity, HangzhouElectricityPriceSensor):
                entity._attr_native_value = round(self.get_current_price(), 4)
            elif isinstance(entity, HangzhouElectricityTariffSensor):
                entity._attr_native_value = self.get_current_tariff()
            elif isinstance(entity, HangzhouElectricityTierSensor):
                entity._attr_native_value = self.get_current_tier()
            elif isinstance(entity, HangzhouElectricityEnergySensor):
                if entity._tariff == TARIFF_PEAK:
                    entity._attr_native_value = round(self._peak_energy, 3)
                else:
                    entity._attr_native_value = round(self._valley_energy, 3)
            elif isinstance(entity, HangzhouElectricityYearlyEnergySensor):
                entity._attr_native_value = round(self._yearly_energy, 3)
            entity.async_write_ha_state()

    def get_current_tariff(self, now: datetime | None = None) -> str:
        """获取当前费率（峰/谷）。"""
        if now is None:
            now = datetime.now()
        hour = now.hour
        # 峰时段：peak_start 到 peak_end（例如 8:00-22:00）
        if self._peak_start < self._peak_end:
            return TARIFF_PEAK if self._peak_start <= hour < self._peak_end else TARIFF_VALLEY
        else:
            # 跨午夜的情况（一般不会用到）
            return TARIFF_PEAK if hour >= self._peak_start or hour < self._peak_end else TARIFF_VALLEY

    def get_current_tier(self) -> str:
        """获取当前阶梯。"""
        if self._tier != TIER_AUTO:
            return self._tier
        # 自动：根据本年度累计用电量判断
        if self._yearly_energy <= TIER_1_LIMIT:
            return TIER_1
        elif self._yearly_energy <= TIER_2_LIMIT:
            return TIER_2
        else:
            return TIER_3

    def get_current_price(self) -> float:
        """获取当前电价。"""
        tariff = self.get_current_tariff()
        tier = self.get_current_tier()
        return self._prices[tier][tariff]

    @property
    def peak_energy(self) -> float:
        """峰电量。"""
        return self._peak_energy

    @property
    def valley_energy(self) -> float:
        """谷电量。"""
        return self._valley_energy

    @property
    def yearly_energy(self) -> float:
        """本年度累计用电量。"""
        return self._yearly_energy

    async def async_start(self) -> None:
        """启动协调器：注册监听器。"""
        # 定时更新（每分钟检查费率切换）
        self._listeners.append(
            event_helper.async_track_time_interval(
                self.hass, self._async_time_update, SCAN_INTERVAL
            )
        )

        # 监听源用电量传感器
        if self._energy_sensor:
            self._listeners.append(
                self.hass.bus.async_listen(
                    "state_changed", self._async_source_changed
                )
            )

    @callback
    def stop_listeners(self) -> None:
        """清理监听器。"""
        for listener in self._listeners:
            listener()
        self._listeners.clear()

    async def _async_time_update(self, now: datetime) -> None:
        """定时更新：处理年度重置和费率切换。"""
        current_year = now.year
        if self._auto_reset and current_year != self._last_year:
            # 新年重置年度累计用电量
            self._yearly_energy = 0.0
            self._last_year = current_year
            await self._async_save()
        self._update_entities()

    async def _async_source_changed(self, event: Event) -> None:
        """源用电量传感器变化时更新峰谷电量。"""
        if event.data.get("entity_id") != self._energy_sensor:
            return

        new_state = event.data.get("new_state")
        if new_state is None:
            return

        try:
            new_value = float(new_state.state)
        except (TypeError, ValueError):
            return

        if self._last_source_value is None:
            # 首次记录，只记录不计算增量
            self._last_source_value = new_value
            return

        delta = new_value - self._last_source_value
        if delta < 0:
            # 源传感器重置（可能是电表归零或更换）
            _LOGGER.debug("源用电量传感器值下降，重置基准: %s -> %s", self._last_source_value, new_value)
            self._last_source_value = new_value
            return

        self._last_source_value = new_value

        tariff = self.get_current_tariff()
        if tariff == TARIFF_PEAK:
            self._peak_energy += delta
        else:
            self._valley_energy += delta

        self._yearly_energy += delta

        await self._async_save()
        self._update_entities()

    async def _async_save(self) -> None:
        """持久化数据。"""
        self._stored.update(
            {
                "peak_energy": self._peak_energy,
                "valley_energy": self._valley_energy,
                "yearly_energy": self._yearly_energy,
                "last_year": self._last_year,
            }
        )
        await self._store.async_save(self._stored)


class HangzhouElectricityPriceSensor(SensorEntity):
    """当前电价传感器。"""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HangzhouElectricityCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """初始化。"""
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_native_value = round(coordinator.get_current_price(), 4)

    async def async_added_to_hass(self) -> None:
        """添加到HA时注册。"""
        self.coordinator.register_entity(self)
        self._attr_native_value = round(self.coordinator.get_current_price(), 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """返回额外属性。"""
        tariff = self.coordinator.get_current_tariff()
        tier = self.coordinator.get_current_tier()
        return {
            "tariff": tariff,
            "tariff_name": "峰" if tariff == TARIFF_PEAK else "谷",
            "tier": tier,
            "tier_name": {
                TIER_1: "第一档",
                TIER_2: "第二档",
                TIER_3: "第三档",
            }.get(tier, "未知"),
            "peak_hours": f"{int(self.coordinator._peak_start):02d}:00-{int(self.coordinator._peak_end):02d}:00",
        }


class HangzhouElectricityTariffSensor(SensorEntity):
    """当前费率传感器（峰/谷）。"""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HangzhouElectricityCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """初始化。"""
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_native_value = "peak"

    async def async_added_to_hass(self) -> None:
        """添加到HA时注册。"""
        self.coordinator.register_entity(self)
        self._attr_native_value = self.coordinator.get_current_tariff()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """返回额外属性。"""
        tariff = self.coordinator.get_current_tariff()
        return {
            "tariff_name": "峰" if tariff == TARIFF_PEAK else "谷",
        }


class HangzhouElectricityTierSensor(SensorEntity):
    """当前阶梯传感器。"""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HangzhouElectricityCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """初始化。"""
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_native_value = TIER_1

    async def async_added_to_hass(self) -> None:
        """添加到HA时注册。"""
        self.coordinator.register_entity(self)
        self._attr_native_value = self.coordinator.get_current_tier()


class HangzhouElectricityEnergySensor(SensorEntity):
    """峰/谷电量累计传感器。"""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HangzhouElectricityCoordinator,
        description: SensorEntityDescription,
        tariff: str,
    ) -> None:
        """初始化。"""
        self.coordinator = coordinator
        self.entity_description = description
        self._tariff = tariff
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        if tariff == TARIFF_PEAK:
            self._attr_native_value = round(coordinator.peak_energy, 3)
        else:
            self._attr_native_value = round(coordinator.valley_energy, 3)

    async def async_added_to_hass(self) -> None:
        """添加到HA时注册。"""
        self.coordinator.register_entity(self)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """返回额外属性。"""
        return {
            "tariff": self._tariff,
            "tariff_name": "峰" if self._tariff == TARIFF_PEAK else "谷",
        }


class HangzhouElectricityYearlyEnergySensor(SensorEntity):
    """本年度累计用电量传感器（用于自动阶梯判断）。"""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HangzhouElectricityCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """初始化。"""
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_native_value = round(coordinator.yearly_energy, 3)

    async def async_added_to_hass(self) -> None:
        """添加到HA时注册。"""
        self.coordinator.register_entity(self)
