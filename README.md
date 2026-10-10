# 杭州峰谷电价 (hangzhou_electricity)

![版本](https://img.shields.io/badge/版本-v1.1.4-blue)
![HA](https://img.shields.io/badge/Home_Assistant-2025.1%2B-41bdf5)
![License](https://img.shields.io/badge/License-MIT-green)

适用于 Home Assistant 的杭州（浙江省）居民峰谷电价集成插件，为能源模块提供分时电价和峰谷电量统计。

> **声明**：本项目为个人自用集成，非官方产品。电价数据基于浙江省居民阶梯电价政策整理，仅供参考，实际电价以供电公司公布为准。欢迎自行修改和分发，但不提供任何保证。

> **杭州居民电价政策**：峰时段 08:00-22:00（0.568 元/kWh），谷时段 22:00-08:00（0.288 元/kWh），年用电量超 2760 kWh 进入第二档，超 4800 kWh 进入第三档。

## 功能特性

- **当前电价传感器**：根据当前时间（峰/谷时段）和用电阶梯，实时输出当前电价（元/kWh），可直接用于能源模块的"当前价格实体"。
- **当前费率传感器**：输出当前处于"峰"还是"谷"时段，可用于驱动 `utility_meter` 拆分用电量。
- **当前阶梯传感器**：显示当前所处的用电阶梯（第一/二/三档）。
- **峰/谷电量统计**：若配置了用电量源传感器，自动统计峰时段和谷时段的累计用电量。
- **年度累计用电量**：统计本年度累计用电量，支持自动判断阶梯（可选），每年 1 月 1 日自动重置。

## 杭州居民峰谷电价政策

### 峰谷时段

| 时段 | 时间 |
|------|------|
| 峰 | 08:00 - 22:00 |
| 谷 | 22:00 - 次日 08:00 |

### 阶梯电价（年用电量，元/kWh）

| 阶梯 | 年用电量 | 峰电价 | 谷电价 |
|------|----------|--------|--------|
| 第一档 | ≤ 2760 kWh | 0.568 | 0.288 |
| 第二档 | 2761 - 4800 kWh | 0.618 | 0.338 |
| 第三档 | > 4800 kWh | 0.868 | 0.588 |

> 数据来源：浙江省发展改革委居民阶梯电价政策。实际电价以供电公司公布为准，可在集成选项中自定义修改。

## 安装

1. 将 `custom_components/hangzhou_electricity` 目录复制到 Home Assistant 的 `custom_components` 目录下。
2. 重启 Home Assistant。
3. 在 **设置 → 设备与服务 → 添加集成** 中搜索"杭州峰谷电价"。

## 配置

### 初始配置

- **峰时段开始/结束**：设置峰时段的起止小时（24 小时制），默认为 8:00 - 22:00。峰时段以外的时间自动为谷时段。
- **用电阶梯**：选择当前所处的阶梯，或选择"自动"根据年度累计用电量判断。

### 选项配置（添加集成后可修改）

- 各档峰/谷电价（可自定义覆盖默认值）
- **用电量源传感器**（可选）：选择一个 `device_class: energy` 的传感器作为总用电量输入，用于峰谷电量拆分统计。
- **每年自动重置**：是否在每年 1 月 1 日自动重置年度累计用电量。

## 在能源模块中使用

### 方式一：使用当前电价传感器（推荐）

1. 进入 **设置 → 仪表盘 → 能源**。
2. 在"电网"中添加你的电网连接，选择用电量统计传感器。
3. 在"使用以下实体的当前价格"中选择 `sensor.当前电价`（`sensor.hangzhou_electricity_current_price`）。
4. 保存。能源模块将根据各时段的实际电价计算用电成本。

### 方式二：使用 utility_meter 拆分峰谷电量

在 `configuration.yaml` 中添加：

```yaml
utility_meter:
  electricity_tariff:
    source: sensor.your_energy_sensor   # 替换为你的用电量传感器
    name: 分时电量
    tariffs:
      - peak
      - valley
```

然后创建自动化，根据 `sensor.当前费率` 的状态切换 utility_meter 的费率：

```yaml
automation:
  - alias: 切换电价费率
    trigger:
      - platform: state
        entity_id: sensor.当前费率
    action:
      - service: utility_meter.select_tariff
        target:
          entity_id: select.分时电量
        data:
          tariff: "{{ states('sensor.当前费率') }}"
```

之后在能源模块中分别添加峰、谷两个电量传感器，并配置各自的固定电价即可。

## 生成的实体

| 实体 ID | 说明 |
|---------|------|
| `sensor.hangzhou_electricity_current_price` | 当前电价（CNY/kWh），`device_class: monetary` |
| `sensor.hangzhou_electricity_current_tariff` | 当前费率（peak/valley） |
| `sensor.hangzhou_electricity_current_tier` | 当前阶梯（tier1/tier2/tier3） |
| `sensor.hangzhou_electricity_peak_energy` | 峰电量累计（kWh），仅在配置了源传感器时生成 |
| `sensor.hangzhou_electricity_valley_energy` | 谷电量累计（kWh），仅在配置了源传感器时生成 |
| `sensor.hangzhou_electricity_yearly_energy` | 本年度累计用电量（kWh），仅在配置了源传感器时生成 |

## 注意事项

- 本集成的电价数据基于浙江省居民阶梯电价政策，工商业用户电价不同，请自行在选项中调整。
- 峰谷电量统计依赖源用电量传感器的状态变化，数据通过 HA 的存储机制持久化，重启后不会丢失。
- 若选择"自动"阶梯判断，年度累计用电量将在每年 1 月 1 日自动重置（可在选项中关闭）。

## 版本更新日志

### v1.1.0 (2026-10-10)

- **新增**：阶梯选择"自动"模式时，支持输入"当前已用电量"作为年度累计初始值
- **新增**：品牌图标 `icon.png`（256x256）
- **新增**：`manifest.json` 添加 `icon` 字段（mdi:currency-cny 兜底）
- **新增**：HACS 支持（`hacs.json`）
- **修复**：`OptionsFlowWithConfigEntry` 废弃 API 导致配置向导 500 错误
- **修复**：`device_class=MONETARY` 与 `CNY/kWh` 单位不兼容导致实体不可用
- **修复**：`SensorDeviceClass.ENUM` 的 `translation_key` 与翻译键不匹配
- **修复**：`native_value` property 与 `async_schedule_update_ha_state` 时序冲突
- **修复**：`%02d` 格式化 float 类型导致 `ValueError`
- **修复**：`strings.json` / `translations/zh-Hans.json` 规范化（英文参考 + 中文翻译）
- **修复**：协调器监听器无清理逻辑，配置重载时内存泄漏

### v1.0.0 (2026-10-10)

- **初始版本**
- 杭州居民峰谷分时电价（峰 08:00-22:00，谷 22:00-08:00）
- 三档阶梯电价（2760/4800 kWh 阈值）
- 动态电价传感器，直接对接 HA 能源模块
- 峰谷电量拆分统计（需配置用电量源传感器）
- 阶梯自动判断（按年累计用电量）
- GUI 配置流程，支持自定义时段和电价
- 每年 1 月 1 日自动重置年度累计用电量
