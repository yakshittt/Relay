/*
 * RELAY ESP32 heartbeat starter.
 * Configure Wi-Fi, DEVICE_TOKEN and API_BASE_URL before flashing.
 * For a real installation, prefer TLS and provision unique per-device credentials.
 */
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* API_BASE_URL = "http://192.168.1.10:8000"; // laptop LAN IP; update for your network
const char* DEVICE_TOKEN = "replace-me-with-another-long-random-secret";
const char* DEVICE_ID = "esp32-lab-01";
const char* SITE_ID = "jio-lab";
const unsigned long INTERVAL_MS = 15000;
unsigned long lastSent = 0;

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 15000) delay(250);
}

void sendHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  String url = String(API_BASE_URL) + "/v1/devices/heartbeat";
  http.begin(url); // Prototype on trusted LAN only; switch to HTTPS for deployment.
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  StaticJsonDocument<256> doc;
  doc["device_id"] = DEVICE_ID;
  doc["site_id"] = SITE_ID;
  doc["wifi_rssi_dbm"] = WiFi.RSSI();
  doc["uptime_seconds"] = millis() / 1000;
  String body;
  serializeJson(doc, body);
  int code = http.POST(body);
  Serial.printf("heartbeat status=%d rssi=%d dBm\n", code, WiFi.RSSI());
  http.end();
}

void setup() {
  Serial.begin(115200);
  connectWiFi();
}

void loop() {
  connectWiFi();
  if (millis() - lastSent >= INTERVAL_MS) {
    lastSent = millis();
    sendHeartbeat();
  }
  delay(50);
}
