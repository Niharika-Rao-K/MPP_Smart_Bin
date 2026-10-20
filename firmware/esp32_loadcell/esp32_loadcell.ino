
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <math.h>
#include "HX711.h"
#include "secrets.h"

// ============================================================
// 1. HX711 CONNECTIONS
// ============================================================
// DT/DOUT -> GPIO 4
// SCK/CLK -> GPIO 5
// VCC     -> 3.3V (check module specifications)
// GND     -> GND

const int LOADCELL_DOUT_PIN = 4;
const int LOADCELL_SCK_PIN  = 5;

HX711 scale;
float calibration_factor = 224.3;

// ============================================================
// 2. WI-FI SETTINGS
// ============================================================

//In secrets

// ============================================================
// 3. BACKEND SETTINGS
// ============================================================

const char* API_BASE_URL =
  "https://mpp-smart-bin.onrender.com";

const char* BIN_ID = "BIN001";
const char* SENSOR_ID = "loadcell-01";

// ============================================================
// 4. MEASUREMENT SETTINGS
// ============================================================

const unsigned long WIFI_TIMEOUT_MS = 30000UL;
const unsigned long POLL_INTERVAL_MS = 3000UL;
const unsigned long MEASUREMENT_DURATION_MS = 30000UL;
const unsigned long READING_INTERVAL_MS = 300UL;

const unsigned long HTTP_TIMEOUT_MS = 15000UL;

double totalWeight = 0.0;
unsigned long validReadingCount = 0;

// ============================================================
// 5. WI-FI CONNECTION
// ============================================================

bool connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  Serial.println("Connecting to Wi-Fi...");

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - start < WIFI_TIMEOUT_MS) {
    delay(250);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("Wi-Fi connected.");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.println("Wi-Fi connection failed.");
  return false;
}

// ============================================================
// 6. READ A STRING FIELD FROM A SIMPLE JSON RESPONSE
// ============================================================
// Used for backend responses containing status and request_id.
// These fields contain simple strings, such as UUIDs.

String getJsonString(String json, const char* key) {
  String searchKey = "\"" + String(key) + "\"";

  int keyPosition = json.indexOf(searchKey);
  if (keyPosition < 0) {
    return "";
  }

  int colonPosition = json.indexOf(':', keyPosition);
  if (colonPosition < 0) {
    return "";
  }

  int valueStart = colonPosition + 1;

  while (valueStart < (int)json.length() &&
         (json[valueStart] == ' ' ||
          json[valueStart] == '\n' ||
          json[valueStart] == '\r' ||
          json[valueStart] == '\t')) {
    valueStart++;
  }

  if (valueStart >= (int)json.length() ||
      json[valueStart] != '"') {
    return "";
  }

  valueStart++;

  int valueEnd = json.indexOf('"', valueStart);
  if (valueEnd < 0) {
    return "";
  }

  return json.substring(valueStart, valueEnd);
}

// ============================================================
// 7. HTTP GET HELPER
// ============================================================

bool httpGetJson(const String& url, String& response) {
  WiFiClientSecure client;

  // Testing configuration. See security note below.
  client.setInsecure();

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println("Could not initialize HTTP GET.");
    return false;
  }

  http.addHeader("Accept", "application/json");

  int code = http.GET();

  if (code > 0) {
    response = http.getString();

    Serial.print("GET HTTP status: ");
    Serial.println(code);

    http.end();
    client.stop();

    return code >= 200 && code < 300;
  }

  Serial.print("GET failed: ");
  Serial.println(http.errorToString(code));

  http.end();
  client.stop();

  return false;
}

// ============================================================
// 8. CHECK FOR A DASHBOARD MEASUREMENT REQUEST
// ============================================================

bool getMeasurementRequest(String& requestId) {
  String url = String(API_BASE_URL) +
      "/api/sensor/requests/next?bin_id=" + BIN_ID;

  String response;

  if (!httpGetJson(url, response)) {
    Serial.println("Could not check for a request.");
    return false;
  }

  String status = getJsonString(response, "status");

  if (status != "claimed") {
    // Normal when no dashboard request is waiting.
    return false;
  }

  requestId = getJsonString(response, "request_id");

  if (requestId.length() == 0) {
    Serial.println("ERROR: Response has no request ID.");
    return false;
  }

  Serial.println();
  Serial.println("====================================");
  Serial.println("MEASUREMENT REQUEST CLAIMED");
  Serial.print("Request ID: ");
  Serial.println(requestId);
  Serial.println("====================================");

  return true;
}

// ============================================================
// 9. TAKE ONE REQUESTED MEASUREMENT
// ============================================================

bool measureAverageWeight(float& averageWeight) {
  totalWeight = 0.0;
  validReadingCount = 0;

  Serial.println();
  Serial.println("Starting 30-second measurement.");
  Serial.println("Keep the item still on the platform.");

  unsigned long measurementStart = millis();
  unsigned long lastStatus = 0;

  while (millis() - measurementStart <
         MEASUREMENT_DURATION_MS) {

    if (scale.is_ready()) {
      float weight = scale.get_units(10);

      if (isfinite(weight)) {
        totalWeight += weight;
        validReadingCount++;

        Serial.print("Elapsed: ");
        Serial.print(
          (millis() - measurementStart) / 1000.0,
          1
        );
        Serial.print(" s | Weight: ");
        Serial.print(weight, 2);
        Serial.println(" g");
      } else {
        Serial.println("Invalid reading skipped.");
      }
    } else if (millis() - lastStatus >= 2000UL) {
      lastStatus = millis();
      Serial.println("HX711 temporarily not ready.");
    }

    delay(READING_INTERVAL_MS);
  }

  if (validReadingCount == 0) {
    Serial.println("ERROR: No valid readings collected.");
    return false;
  }

  averageWeight =
      (float)(totalWeight / validReadingCount);

  if (!isfinite(averageWeight) || averageWeight <= 0.0) {
    Serial.println("ERROR: Average weight is not positive.");
    Serial.print("Calculated weight: ");
    Serial.println(averageWeight, 2);
    return false;
  }

  Serial.println("------------------------------------");
  Serial.print("Valid readings: ");
  Serial.println(validReadingCount);
  Serial.print("Average weight: ");
  Serial.print(averageWeight, 2);
  Serial.println(" g");
  Serial.println("------------------------------------");

  return true;
}

// ============================================================
// 10. SUBMIT WEIGHT FOR THE EXACT REQUEST
// ============================================================

bool submitMeasurement(
    const String& requestId,
    float averageWeight) {

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Cannot submit: Wi-Fi disconnected.");
    return false;
  }

  String url = String(API_BASE_URL) +
      "/api/sensor/requests/" +
      requestId +
      "/reading";

  String payload = "{";
  payload += "\"bin_id\":\"" + String(BIN_ID) + "\",";
  payload += "\"sensor_id\":\"" + String(SENSOR_ID) + "\",";
  payload += "\"weight_g\":" + String(averageWeight, 2);
  payload += "}";

  WiFiClientSecure client;

  // Testing configuration. See security note below.
  client.setInsecure();

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println("Could not initialize weight submission.");
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Accept", "application/json");

  Serial.println("Submitting weight for request:");
  Serial.println(requestId);
  Serial.print("Weight: ");
  Serial.print(averageWeight, 2);
  Serial.println(" g");

  // One POST attempt per measurement request.
  int code = http.POST(payload);

  bool success = false;

  if (code > 0) {
    String response = http.getString();

    Serial.print("POST HTTP status: ");
    Serial.println(code);
    Serial.print("Backend response: ");
    Serial.println(response);

    if (code >= 200 && code < 300) {
      String status = getJsonString(response, "status");

      if (status == "completed") {
        Serial.println("SUCCESS: Weight recorded.");
        success = true;
      } else {
        Serial.println(
          "WARNING: HTTP succeeded but completion "
          "was not confirmed."
        );
      }
    } else {
      Serial.println("ERROR: Backend rejected the reading.");
    }
  } else {
    Serial.print("POST failed: ");
    Serial.println(http.errorToString(code));
    Serial.println("No automatic POST retry will occur.");
  }

  http.end();
  client.stop();

  return success;
}

// ============================================================
// 11. PROCESS ONE REQUEST
// ============================================================

void processMeasurementRequest(const String& requestId) {
  float averageWeight = 0.0;

  if (!measureAverageWeight(averageWeight)) {
    Serial.println(
      "Measurement failed. Request may expire; "
      "start a new deposit attempt."
    );
    return;
  }

  if (submitMeasurement(requestId, averageWeight)) {
    Serial.println("Measurement request completed.");
  } else {
    Serial.println(
      "Submission was not confirmed. Check backend "
      "status before attempting another deposit."
    );
  }

  Serial.println("Returning to request polling.");
}

// ============================================================
// 12. SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("====================================");
  Serial.println("     RECYCLE2EARN SMART BIN");
  Serial.println("  REQUEST-BASED WEIGHT MEASUREMENT");
  Serial.println("====================================");

  // Initialize HX711.
  Serial.println("Initializing HX711...");

  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);

  unsigned long hx711Start = millis();

  while (!scale.is_ready() &&
         millis() - hx711Start < 5000UL) {
    delay(100);
  }

  if (!scale.is_ready()) {
    Serial.println("ERROR: HX711 is not responding.");
    Serial.println("Check DT, SCK, VCC and GND.");

    while (true) {
      delay(1000);
    }
  }

  scale.set_scale(calibration_factor);

  Serial.println("HX711 initialized.");

  // IMPORTANT: The platform must be empty during startup tare.
  Serial.println();
  Serial.println("Ensure the weighing platform is EMPTY.");
  Serial.println("Taring in 2 seconds...");
  delay(2000);

  scale.tare(20);

  Serial.println("Tare complete.");

  // Connect to Wi-Fi.
  connectToWiFi();

  Serial.println();
  Serial.println("Ready for dashboard requests.");
  Serial.println("No request means no measurement.");
}

// ============================================================
// 13. LOOP — WAIT FOR REQUESTS
// ============================================================

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi disconnected; reconnecting...");

    if (!connectToWiFi()) {
      delay(POLL_INTERVAL_MS);
      return;
    }
  }

  String requestId;

  if (getMeasurementRequest(requestId)) {
    // The backend has claimed the request for this ESP32.
    processMeasurementRequest(requestId);
  } else {
    Serial.println("No measurement request. Waiting...");
  }

  delay(POLL_INTERVAL_MS);
}
