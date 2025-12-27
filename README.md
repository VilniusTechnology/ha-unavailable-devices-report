# Unavailable Devices Report for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)


[![Validate HACS](https://github.com/lukas-mikelionis/unavailable-devices-report/actions/workflows/validate.yaml/badge.svg)](https://github.com/lukas-mikelionis/unavailable-devices-report/actions/workflows/validate.yaml)

A custom component that provides a sensor reporting all unavailable or unknown entities in Home Assistant, grouped by device.

## Features
- **Device-Centric**: Groups stray entities by their parent device.
- **Configurable**: Exclude specific entities or devices via configuration.
- **Markdown Report**: Provides a clean Markdown summary suitable for dashboards.

## Installation

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

## Configuration & Exclusions

You can configure the integration and manage exclusions directly through the Home Assistant UI:

1. Go to **Settings > Devices & Services**.
2. Find the **Unavailable Devices Report** card.
3. Click **Options**.
4. You will see two fields:
    - **Excluded Devices**: Select entire devices to ignore.
    - **Excluded Entities**: Select specific entities to ignore.

Alternatively, you can still use `configuration.yaml` (legacy support):

```yaml
sensor:
  - platform: unavailable_devices_report
    exclude:
      - device_tracker.my_phone
      - "MQTT Device Name"
```

## Uninstall

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

## Lovelace Configuration

A new sensor `sensor.unavailable_devices_report` will be created. 

### Available Attributes

| Attribute | Description |
|-----------|-------------|
| `count` | Number of unavailable devices and standalone entities. |
| `report_summary` | Full Markdown report of all unavailable items with duration. |
| `devices_report` | Markdown report of only unavailable **devices**. |
| `entities_report` | Markdown report of only standalone **entities**. |
| `excluded_devices` | List of names of devices currently excluded. |
| `excluded_entities` | List of IDs of entities currently excluded. |

---

### Dashboard Card Examples

#### 1. Standard Report (Unlimited Size)
Because Home Assistant has a database limit, large reports are split into pages. Use this template to stitch them together:

```yaml
type: markdown
content: >
  {{ state_attr('sensor.unavailable_devices_report', 'report_page_1') }}
  {{ state_attr('sensor.unavailable_devices_report', 'report_page_2') or '' }}
  {{ state_attr('sensor.unavailable_devices_report', 'report_page_3') or '' }}
  {{ state_attr('sensor.unavailable_devices_report', 'report_page_4') or '' }}
title: Unavailable Devices
```

#### 2. Devices Only
```yaml
type: markdown
content: >
  {{ state_attr('sensor.unavailable_devices_report', 'devices_page_1') }}
  {{ state_attr('sensor.unavailable_devices_report', 'devices_page_2') or '' }}
  {{ state_attr('sensor.unavailable_devices_report', 'devices_page_3') or '' }}
title: Hardware Issues
```

#### 3. Standalone Entities Only
```yaml
type: markdown
content: >
  {{ state_attr('sensor.unavailable_devices_report', 'entities_page_1') }}
  {{ state_attr('sensor.unavailable_devices_report', 'entities_page_2') or '' }}
  {{ state_attr('sensor.unavailable_devices_report', 'entities_page_3') or '' }}
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
  content: >
    {{ state_attr('sensor.unavailable_devices_report', 'report_page_1') }}
    {{ state_attr('sensor.unavailable_devices_report', 'report_page_2') or '' }}
  title: ⚠️ Service Alert
```

## Automations

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
By default, the sensor updates every 30 seconds. To force an update immediately (e.g., via an automation or button), use the `homeassistant.update_entity` service:

```yaml
service: homeassistant.update_entity
target:
  entity_id: sensor.unavailable_devices_report
```

## Debugging
If you need to troubleshoot why devices are not showing up or are showing up incorrectly, you can enable debug logging for this component.

Add the following to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.unavailable_devices_report: debug
```

After restarting Home Assistant, check the logs in **Settings -> System -> Logs** to see detailed information about which entities are being detected and how they are being grouped.

## Support

If you find this integration useful and would like to support its development, you can buy me a coffee!

[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/vilnius.technology)
