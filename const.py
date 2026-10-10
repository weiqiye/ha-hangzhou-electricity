"""常量定义：杭州（浙江省）居民峰谷电价政策。"""

from __future__ import annotations

DOMAIN = "hangzhou_electricity"

# 峰谷时段定义（24小时制）
# 浙江省居民峰谷电价：高峰 8:00-22:00，低谷 22:00-次日8:00
DEFAULT_PEAK_START = 8
DEFAULT_PEAK_END = 22
DEFAULT_VALLEY_START = 22
DEFAULT_VALLEY_END = 8

# 费率标识
TARIFF_PEAK = "peak"
TARIFF_VALLEY = "valley"

TARIFF_NAMES = {
    TARIFF_PEAK: "峰",
    TARIFF_VALLEY: "谷",
}

# 阶梯电价（年用电量，单位：千瓦时）
# 第一档：年用电 2760 千瓦时及以下
# 第二档：年用电 2761 - 4800 千瓦时
# 第三档：年用电 4801 千瓦时及以上
TIER_1_LIMIT = 2760
TIER_2_LIMIT = 4800

TIER_1 = "tier1"
TIER_2 = "tier2"
TIER_3 = "tier3"
TIER_AUTO = "auto"

TIER_OPTIONS = {
    TIER_1: "第一档（年用电 ≤ 2760 kWh）",
    TIER_2: "第二档（年用电 2761-4800 kWh）",
    TIER_3: "第三档（年用电 > 4800 kWh）",
    TIER_AUTO: "自动（按年累计用电量判断）",
}

# 默认电价表（元/千瓦时）
# 数据来源：浙江省发展改革委居民阶梯电价政策
DEFAULT_PRICES = {
    TIER_1: {
        TARIFF_PEAK: 0.568,
        TARIFF_VALLEY: 0.288,
    },
    TIER_2: {
        TARIFF_PEAK: 0.618,
        TARIFF_VALLEY: 0.338,
    },
    TIER_3: {
        TARIFF_PEAK: 0.868,
        TARIFF_VALLEY: 0.588,
    },
}

# 配置项键名
CONF_PEAK_START = "peak_start"
CONF_PEAK_END = "peak_end"
CONF_TIER = "tier"
CONF_TIER1_PEAK = "tier1_peak_price"
CONF_TIER1_VALLEY = "tier1_valley_price"
CONF_TIER2_PEAK = "tier2_peak_price"
CONF_TIER2_VALLEY = "tier2_valley_price"
CONF_TIER3_PEAK = "tier3_peak_price"
CONF_TIER3_VALLEY = "tier3_valley_price"
CONF_ENERGY_SENSOR = "energy_sensor"
CONF_AUTO_RESET = "auto_reset"
CONF_INITIAL_YEARLY_ENERGY = "initial_yearly_energy"
CONF_DEBUG_LOG = "debug_log"

# 默认值
DEFAULT_TIER = TIER_1
DEFAULT_ENERGY_SENSOR = ""
DEFAULT_AUTO_RESET = True
DEFAULT_INITIAL_YEARLY_ENERGY = 0.0
DEFAULT_DEBUG_LOG = False

# 货币单位
CURRENCY_CNY = "CNY"
PRICE_UNIT = f"{CURRENCY_CNY}/kWh"
ENERGY_UNIT = "kWh"
