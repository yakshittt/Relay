# RELAY ESP32 Hardware Sentinel Setup Guide

## 1. Role in the RELAY Architecture

The ESP32 DevKit acts as an **independent, out-of-band physical network sentinel**. Positioned at the customer location (e.g., store counter, clinic reception), it:
- Connects directly to the local Jio Router Wi-Fi access point.
- Measures live Wi-Fi signal strength (RSSI in dBm) from the physical store floor.
- Measures device uptime and FreeRTOS heap memory health.
- Emits periodic authenticated heartbeats over HTTP/HTTPS.
- Enables the diagnosis engine to distinguish between total ISP/network outages versus isolated workstation or application errors (Decision Tree Case D).

---

## 2. Hardware Requirements

- **ESP32 Development Board**: Any standard ESP32-WROOM-32, NodeMCU-32S, or ESP32-DevKitC board.
- **Micro-USB Cable**: Connected to 5V USB power adapter or laptop USB port.
- **No External Sensors Required**: Avoids fictitious sensor data. Telemetry consists solely of actual physical Wi-Fi RSSI, uptime, and memory counters.

---

## 3. Firmware Configuration

Open `firmware/relay_esp32/relay_esp32.ino` (or `firmware/relay_esp32.ino`):

```cpp
// 1. Wi-Fi Access Point (Jio Home Router SSID & Password)
const char* WIFI_SSID     = "YOUR_JIO_ROUTER_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// 2. Security Mode Flag
#define USE_HTTPS false // Set to true for production TLS, false for local LAN development

// 3. Backend Endpoint
// Replace 192.168.29.100 with your laptop's local LAN IP address
const char* API_BASE_URL  = "http://192.168.29.100:8000";

// 4. Authentication Credentials (must match DEVICE_TOKEN in backend .env)
const char* DEVICE_TOKEN  = "relay-esp32-token-secret-2026";
const char* DEVICE_ID     = "esp32-jio-sentinel-01";
const char* SITE_ID       = "jio-lab";
```

### Production Security Considerations
- When `USE_HTTPS` is set to `true`, the firmware initializes `WiFiClientSecure` and validates the server certificate against `ROOT_CA_CERT`.
- For enterprise fleet deployments, each ESP32 should receive a unique device token rather than a shared credential.
- ESP32 hardware limitations: The basic ESP32 stores credentials in flash memory. In high-security production deployments, use ESP32-S3 / ESP32-C3 with Flash Encryption and Secure Boot enabled.

---

## 4. Compiling & Flashing

### Using Arduino CLI (Verified in this environment)
The firmware has been compiled and validated using `arduino-cli` with the `esp32:esp32:esp32` core and `ArduinoJson v7.4.2`:

```bash
# Verify compilation
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/relay_esp32

# Flash to connected ESP32 board (replace COM3 with your actual serial port)
arduino-cli upload -p COM3 --fqbn esp32:esp32:esp32 firmware/relay_esp32
```

### Using Arduino IDE
1. Open Arduino IDE.
2. In **Boards Manager**, ensure `esp32` by Espressif Systems is installed.
3. In **Library Manager**, install `ArduinoJson` (v7.x).
4. Open `firmware/relay_esp32/relay_esp32.ino`.
5. Select Board: **ESP32 Dev Module**.
6. Select your USB Serial Port (e.g., `COM3` on Windows).
7. Click **Upload**.
8. Open **Serial Monitor** at **115200 baud** to view real-time heartbeat logs.

---

## 5. Verification Status

| Component | Status | Details |
| :--- | :--- | :--- |
| **Code Syntax & Modern API** | **Verified** | Upgraded to ArduinoJson v7 and non-blocking state machine |
| **Toolchain Compilation** | **Verified** | Compiled with `arduino-cli` (Code size: 941,403 bytes, 71% flash, zero errors) |
| **Backend Ingestion** | **Verified** | Tested via automated test suite (`tests/test_incidents_and_devices.py`) |
| **Physical USB Flashing** | **Pending Physical Hardware** | Requires physical USB connection to dev board |
