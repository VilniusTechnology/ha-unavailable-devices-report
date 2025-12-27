# ❓ Troubleshooting Guide

## 📋 Common Issues

### 1. "Entity not found" error in Lovelace
**Symptoms:**  
- The card shows a yellow warning symbol with "Entity not found: sensor.unavailable_devices_report".
- You cannot find `sensor.unavailable_devices_report` in Developer Tools -> States.

**Possible Causes & Solutions:**
- **Restart Required:** You must restart Home Assistant after installing the integration (via HACS or manual copy) AND after adding the configuration to `configuration.yaml`.
- **Missing Configuration:** Ensure you have added the `sensor:` platform configuration to your `configuration.yaml`.
  ```yaml
  sensor:
    - platform: unavailable_devices_report
  ```
- **Configuration Check Failed:** If your configuration is invalid, Home Assistant might skip loading the sensor. Check **Developer Tools -> YAML -> Check Configuration**.

### 2. "No logs" for `custom_components.unavailable_devices_report`
**Symptoms:**  
- You enabled debug logging but see no entries when searching for `unavailable_devices_report`.

**Possible Causes & Solutions:**
- **Integration Not Loading:** See issue #1 above. If the integration isn't loaded, it won't produce logs.
- **Incorrect Logger Config:** Ensure your logger config is correct and you have restarted.
  ```yaml
  logger:
    default: warning
    logs:
      custom_components.unavailable_devices_report: debug
  ```
- **Updates Not Triggered:** The sensor updates every 30 seconds. Wait a minute after restart.

### 3. Sensor state is 0, but I have unavailable devices
**Symptoms:**  
- You know a device is offline, but the sensor reports 0.

**Possible Causes & Solutions:**
- **Device vs. Entity:** This report groups by *Device*. If an entity is unavailable but it doesn't belong to a Device (e.g., some helper entities or pure MQTT entities without device registry info), it might be treated differently depending on internal logic. (Note: The current logic *does* catch standalone entities, so check if they are `unavailable` or `unknown`. Some entities might have a different state like `off` which is not considered unavailable).
- **Exclusions:** Check if you have inadvertently excluded the entity or device in your configuration.

### 4. "Entity not found" when clicking the Force Update button
**Symptoms:**  
- Clicking "Force Update" gives a toaster error "Failed to call service homeassistant/update_entity. Entity not found."

**Solution:**
- This confirms the sensor is not loaded. See issue #1.

### 5. Duplicate Entities (`_2`) or "Ghost" Entities
**Symptoms:**
- You see `sensor.unavailable_devices_report_2`.
- You cannot delete `sensor.unavailable_devices_report` even though you removed the config.
- Developer Tools shows `restored: true` for the entity.

**Solution:**
1. **Identify the Ghost:** If an entity has `restored: true` in its attributes (Developer Tools > States), it means Home Assistant remembers it from a past session, but it's no longer being provided by an integration.
2. **Delete it:**
   - Go to **Settings > Devices & Services > Entities**.
   - Search for `unavailable_devices_report`.
   - Click the "Ghost" entity (the one without `_2` that is "Unavailable").
   - Click **Delete Selected**.
3. **Rename the New One:**
   - Click on `sensor.unavailable_devices_report_2`.
   - Change the **Entity ID** to `sensor.unavailable_devices_report`.
   - Restart (optional, but good practice).

## 🆘 Getting more help
If none of the above solves your issue, please open an issue on GitHub with:
1. Your `configuration.yaml` snippet for this sensor.
2. Debug logs (if available).
3. A screenshot of the unavailable entity in Developer Tools -> States.
