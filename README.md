# Unavailable Devices Report for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)


[![Validate HACS](https://github.com/VilniusTechnology/ha-unavailable-devices-report/actions/workflows/validate.yaml/badge.svg)](https://github.com/VilniusTechnology/ha-unavailable-devices-report/actions/workflows/validate.yaml)

<a href="https://buymeacoffee.com/vilnius.technology" target="_blank"><img src="https://img.shields.io/badge/donate-%E2%98%95buy_me_a_coffee-yellow.svg?style=for-the-badge" alt="Buy Me A Coffee"></a>

A custom component that provides a sensor reporting all unavailable or unknown entities in Home Assistant, grouped by device.

## ✨ Features
- **Device-Centric**: Groups stray entities by their parent device.
- **Configurable**: Exclude specific entities or devices via configuration.
- **Markdown Report**: Provides a clean Markdown summary suitable for dashboards.

## 🚀 Installation

### Step 1: Install Files
#### HACS (Recommended)
1. Add this repository to HACS Custom Repositories.
2. Search for "Unavailable Devices Report" and install.
3. Restart Home Assistant.

#### Manual
1. Copy `custom_components/unavailable_devices_report` to your `config/custom_components/` directory.
2. Restart Home Assistant.

### Step 2: Add Integration
1. Go to **Settings > Devices & Services**.
2. Click **Add Integration** and search for **Unavailable Devices Report**.
3. Follow the UI prompts to complete the setup.

## ⚙️ Configuration & Exclusions

You can configure the integration and manage exclusions directly through the Home Assistant UI:

1. Go to **Settings > Devices & Services**.
2. Find the **Unavailable Devices Report** card.
3. Click **Options**.
4. You can configure the following settings:
    - **Excluded Devices**: Select entire devices to ignore.
    - **Excluded Entities**: Select specific entities to ignore.
    - **Scan Interval**: How often the sensor updates (default: 30 seconds).
    - **Logging Level**: Set specific logging level for this component (e.g., DEBUG for troubleshooting).

### 🛡️ Strict Mode & Device Identification
To prevent false positives, this integration uses a **Strict Mode** logic for devices:
- A **Device** is considered unavailable ONLY if **ALL** of its entities are unavailable.
- If even one entity in a device is still active (e.g., a "sleep mode" sensor), the device is considered **active** and will not be reported, though individual unavailable entities might still be listed as "Standalone" if they don't map clearly.
- **Diagnostic** and **Configuration** entities are ignored by default and do not affect this logic.

Alternatively, you can still use `configuration.yaml` (legacy support):

```yaml
sensor:
  - platform: unavailable_devices_report
    exclude:
      - device_tracker.my_phone
      - "MQTT Device Name"
```

## 🗑️ Uninstall

### Step 1: Remove Integration
1. Go to **Settings > Devices & Services**.
2. Find the **Unavailable Devices Report** card.
3. Click the three dots menu and select **Delete**.

### Step 2: Remove Files
#### HACS
1. Navigate to HACS -> Integrations.
2. Locate "Unavailable Devices Report".
3. Click the three dots menu and select "Remove".
4. Restart Home Assistant.

#### Manual
1. Remove the `unavailable_devices_report` folder from your `custom_components` directory.
2. Remove the sensor configuration from `configuration.yaml` (if used).
3. Restart Home Assistant.

## 🖼️ Lovelace Configuration

A new sensor `sensor.unavailable_devices_report` will be created. 

### Available Attributes

| Attribute | Description |
|-----------|-------------|
| `count` | Number of unavailable devices and standalone entities. |
| `devices_report` | Markdown report of only unavailable **devices**. |
| `entities_report` | Markdown report of only standalone **entities**. |
| `excluded_devices` | List of names of devices currently excluded. |
| `excluded_entities` | List of IDs of entities currently excluded. |

---

### Dashboard Card Examples

> [!TIP]
> **Use the Manual Card**: When adding these cards to your dashboard, select **Manual** from the card picker and paste the YAML code below directly. This is the easiest method.

#### 1. Standard Report (Unlimited Size)
Because Home Assistant has a database limit, large reports are split into pages. Use this template to stitch them together:

```yaml
type: markdown
content: |
  {% for i in range(1, state_attr('sensor.unavailable_devices_report', 'devices_pages') | int(default=1) + 1) %}
  {{ state_attr('sensor.unavailable_devices_report', 'devices_page_' ~ i) or '' }}
  {% endfor %}
  {% for i in range(1, state_attr('sensor.unavailable_devices_report', 'entities_pages') | int(default=1) + 1) %}
  {{ state_attr('sensor.unavailable_devices_report', 'entities_page_' ~ i) or '' }}
  {% endfor %}
title: Unavailable Devices
```

#### 2. Devices Only
```yaml
type: markdown
content: |
  {% for i in range(1, state_attr('sensor.unavailable_devices_report', 'devices_pages') | int(default=1) + 1) %}
  {{ state_attr('sensor.unavailable_devices_report', 'devices_page_' ~ i) or '' }}
  {% endfor %}
title: Hardware Issues
```

#### 3. Standalone Entities Only
```yaml
type: markdown
content: |
  {% for i in range(1, state_attr('sensor.unavailable_devices_report', 'entities_pages') | int(default=1) + 1) %}
  {{ state_attr('sensor.unavailable_devices_report', 'entities_page_' ~ i) or '' }}
  {% endfor %}
title: Entity Issues
```

#### 4. Conditional Warning Card
Only shows up when something is actually broken.

```yaml
type: conditional
conditions:
  - entity: sensor.unavailable_devices_report
    state_not: "0"
card:
  type: markdown
  content: |
    {% for i in range(1, state_attr('sensor.unavailable_devices_report', 'devices_pages') | int(default=1) + 1) %}
    {{ state_attr('sensor.unavailable_devices_report', 'devices_page_' ~ i) or '' }}
    {% endfor %}
    {% for i in range(1, state_attr('sensor.unavailable_devices_report', 'entities_pages') | int(default=1) + 1) %}
    {{ state_attr('sensor.unavailable_devices_report', 'entities_page_' ~ i) or '' }}
    {% endfor %}
  title: ⚠️ Service Alert
```

#### 5. Report with Refresh Button
Combines the report with a manual refresh button using a vertical stack.

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      {% for i in range(1, state_attr('sensor.unavailable_devices_report', 'devices_pages') | int(default=1) + 1) %}
      {{ state_attr('sensor.unavailable_devices_report', 'devices_page_' ~ i) or '' }}
      {% endfor %}
    title: Unavailable Devices
  - type: markdown
    content: |
      {% for i in range(1, state_attr('sensor.unavailable_devices_report', 'entities_pages') | int(default=1) + 1) %}
      {{ state_attr('sensor.unavailable_devices_report', 'entities_page_' ~ i) or '' }}
      {% endfor %}
    title: Unavailable Entities
  - type: entities
    entities:
      - type: button
        name: Refresh Report
        icon: mdi:refresh
        action_name: Refresh
        tap_action:
          action: call-service
          service: homeassistant.update_entity
          target:
            entity_id: sensor.unavailable_devices_report
```

## 🤖 Automations

You can trigger automations when specific critical entities become unavailable using the `unavailable_entity_ids` attribute.

```yaml
automation:
  - alias: "Notify if Fridge is Unavailable"
    trigger:
      - platform: state
        entity_id: sensor.unavailable_devices_report
    condition:
      - condition: template
        value_template: >
          {{ 'sensor.kitchen_fridge_temperature' in state_attr('sensor.unavailable_devices_report', 'unavailable_entity_ids') }}
    action:
      - service: notify.mobile_app
        data:
          message: "⚠️ Critical: Fridge sensor is unavailable!"
```
*Note: The `unavailable_entity_ids` list is capped at 300 items to prevent database issues.*

### Manual Update (On Request)
The sensor updates periodically based on your **Scan Interval** setting. To force an update immediately (e.g., via an automation or button), use the `homeassistant.update_entity` service:

```yaml
service: homeassistant.update_entity
target:
  entity_id: sensor.unavailable_devices_report
```

## 🛠️ Services

### Remove Items (`unavailable_devices_report.remove_items`)
Permanently removes entities or devices from the Home Assistant registry. This is useful for automated cleanup of old or broken devices.

**Parameters:**
- `entity_id`: List of entity IDs to remove.
- `device_id`: List of device IDs to remove.

**Example Automation with Confirmation:**
This automation sends a notification to your phone and waits for you to click "Delete" before removing items.

```yaml
alias: Purge Unavailable Items
description: "Ask for confirmation before deleting unavailable items."
trigger:
  - platform: state
    entity_id: sensor.unavailable_devices_report
    attribute: count
    # Trigger when count changes, or run manually
    to: null
condition:
  - condition: numeric_state
    entity_id: sensor.unavailable_devices_report
    above: 0
action:
  # 1. Send actionable notification
  - service: notify.mobile_app_your_device  # CHANGE THIS to your notify service
    data:
      message: "Found {{ states('sensor.unavailable_devices_report') }} unavailable items. Purge them?"
      title: "Unavailable Devices Report"
      data:
        actions:
          - action: "PURGE_UNAVAILABLE_CONFIRM"
            title: "Delete Forever"
            destructive: true
  
  # 2. Wait for confirmation
  - wait_for_trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: "PURGE_UNAVAILABLE_CONFIRM"
    timeout: "00:01:00"
    continue_on_timeout: false
  
  # 3. Perform removal
  - service: unavailable_devices_report.remove_items
    data:
      entity_id: "{{ state_attr('sensor.unavailable_devices_report', 'unavailable_entity_ids') }}"
      device_id: "{{ state_attr('sensor.unavailable_devices_report', 'unavailable_device_ids') }}"
  
  - service: notify.mobile_app_your_device
    data:
      message: "Purge complete."
```
> [!WARNING]
> Registry removal is permanent! The above automation includes a safety check, but always double-check what is unavailable before confirming.

## 🐞 Debugging
If you need to troubleshoot why devices are not showing up or are showing up incorrectly, you can enable debug logging for this component directly in the UI:

1. Go to **Settings > Devices & Services**.
2. Find the **Unavailable Devices Report** card.
3. Click **Options**.
4. Change **Logging Level** to **DEBUG**.
5. Click **Submit**.

After changing the level, check the logs in **Settings > System > Logs** to see detailed information about which entities are being detected and how they are being grouped.

### Legacy Debugging (YAML)
Alternatively, you can still use `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.unavailable_devices_report: debug
```

After restarting Home Assistant, check the logs in **Settings -> System -> Logs** to see detailed information about which entities are being detected and how they are being grouped.

## ☕ Support

If you find this integration useful and want to support its development:

<a href="https://buymeacoffee.com/vilnius.technology" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

