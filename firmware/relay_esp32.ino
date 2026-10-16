/*
 * RELAY ESP32 Hardware Sentinel Probe Firmware
 * Version: 1.2.0
 * Target: ESP32 DevKit v1 / NodeMCU-32S (Arduino Framework)
 *
 * MISSION:
 * Independent out-of-band network presence sentinel.
 * Measures local Wi-Fi RSSI, system uptime, and memory health.
 * Sends periodic authenticated heartbeats to the RELAY incident response backend.
 *
 * HARDWARE REQUIRED:
 * - ESP32 Development Board (ESP-WROOM-32 or equivalent)
 * - Micro-USB cable connected to laptop or USB power supply
 * - No additional external sensors required (avoids fictitious hardware data)
 *
 * LIBRARIES REQUIRED:
 * - WiFi (built-in ESP32 core)
 * - HTTPClient (built-in ESP32 core)
 * - WiFiClientSecure (built-in ESP32 core for HTTPS)
 * - ArduinoJson (v6 or v7, install via Arduino Library Manager)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

// ============================================================================
// CONFIGURATION (Adjust for your local lab environment)
// ============================================================================

// Wi-Fi Access Point Settings (Connects to Jio Router Wi-Fi)
const char* WIFI_SSID     = "YOUR_JIO_ROUTER_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Security Flag: Set to true for production TLS, false for local LAN prototype
#define USE_HTTPS false

#if USE_HTTPS
  // Production Endpoint
  const char* API_BASE_URL = "https://relay.yourdomain.com";
  // Root CA Certificate in PEM format for certificate validation
  const char* ROOT_CA_CERT = \
    "-----BEGIN CERTIFICATE-----\n" \
    "MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw\n" \
    "... (Paste your server root CA PEM here) ...\n" \
    "-----END CERTIFICATE-----\n";
#else
  // Development LAN Endpoint (HTTP only on trusted local network)
  // Replace with the IP address of the laptop running RELAY backend
  const char* API_BASE_URL = "http://192.168.29.100:8000";
#endif

// Device Authentication Credentials (matched with DEVICE_TOKEN in backend .env)
const char* DEVICE_TOKEN = "relay-esp32-token-secret-2026";
const char* DEVICE_ID    = "esp32-jio-sentinel-01";
const char* SITE_ID      = "jio-lab";
const char* FW_VERSION   = "1.2.0";

// Telemetry intervals
const unsigned long HEARTBEAT_INTERVAL_MS = 15000;  // 15 seconds
const unsigned long WIFI_TIMEOUT_MS        = 10000;  // 10s connection attempt

// ============================================================================
// STATE VARIABLES
// ============================================================================
unsigned long lastHeartbeatTime = 0;
unsigned long heartbeatCycle    = 0;
unsigned int consecutiveFailures = 0;

void printBanner() {
  Serial.println(F("\n=============================================="));
  Serial.println(F("   RELAY ESP32 Sentinel Probe v1.2.0          "));
  Serial.println(F("   Voice-Native Physical Incident Responder   "));
  Serial.println(F("=============================================="));
  Serial.printf("Device ID: %s | Site ID: %s\n", DEVICE_ID, SITE_ID);
#if USE_HTTPS
  Serial.println(F("Security Mode: HTTPS (TLS Certificate Verified)"));
#else
  Serial.println(F("Security Mode: [DEVELOPMENT WARNING] Plain HTTP on LAN"));
#endif
  Serial.println(F("----------------------------------------------"));
}

void ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.printf("[WIFI] Connecting to SSID: %s ...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttempt = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - startAttempt < WIFI_TIMEOUT_MS)) {
    delay(300);
    Serial.print(F("."));
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WIFI] Connected! Assigned IP: %s | RSSI: %d dBm\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
    consecutiveFailures = 0;
  } else {
    Serial.printf("[WIFI] Connection failed. Current status code: %d\n", WiFi.status());
  }
}

void sendHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("[HEARTBEAT] Skipped: Wi-Fi offline."));
    return;
  }

  heartbeatCycle++;
  unsigned long nowMs = millis();
  unsigned long uptimeSec = nowMs / 1000;
  int rssi = WiFi.RSSI();
  uint32_t freeHeap = ESP.getFreeHeap();

  Serial.printf("[HEARTBEAT #%lu] Sending telemetry: Uptime=%lus, RSSI=%d dBm, Heap=%u B\n",
                heartbeatCycle, uptimeSec, rssi, freeHeap);

  HTTPClient http;
  String endpoint = String(API_BASE_URL) + "/v1/devices/heartbeat";

#if USE_HTTPS
  WiFiClientSecure client;
  client.setCACert(ROOT_CA_CERT);
  http.begin(client, endpoint);
#else
  WiFiClient client;
  http.begin(client, endpoint);
#endif

  // Set timeout bounds to prevent blocking loop
  http.setTimeout(4000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);

  // Build JSON payload safely with ArduinoJson
  JsonDocument doc;
  doc["device_id"]        = DEVICE_ID;
  doc["site_id"]          = SITE_ID;
  doc["wifi_rssi_dbm"]    = rssi;
  doc["uptime_seconds"]   = uptimeSec;
  doc["firmware_version"] = FW_VERSION;
  doc["free_heap"]        = freeHeap;
  doc["cycle_count"]      = heartbeatCycle;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  int httpCode = http.POST(jsonPayload);

  if (httpCode > 0) {
    Serial.printf("[HEARTBEAT] Backend response: HTTP %d\n", httpCode);
    if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_CREATED) {
      consecutiveFailures = 0;
    } else {
      String response = http.getString();
      Serial.printf("[HEARTBEAT] Error response body: %s\n", response.c_str());
      consecutiveFailures++;
    }
  } else {
    Serial.printf("[HEARTBEAT] POST failed, error: %s\n", http.errorToString(httpCode).c_str());
    consecutiveFailures++;
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000); // Allow UART to stabilize
  printBanner();
  ensureWiFi();
}

void loop() {
  // Check Wi-Fi state non-blockingly
  ensureWiFi();

  unsigned long currentMillis = millis();

  // Dynamic backoff if consecutive network errors occur (up to 60s max)
  unsigned long interval = HEARTBEAT_INTERVAL_MS;
  if (consecutiveFailures > 3) {
    interval = min((unsigned long)60000, HEARTBEAT_INTERVAL_MS * (consecutiveFailures - 2));
  }

  if (currentMillis - lastHeartbeatTime >= interval) {
    lastHeartbeatTime = currentMillis;
    sendHeartbeat();
  }

  delay(100); // Friendly CPU yield for FreeRTOS
}
