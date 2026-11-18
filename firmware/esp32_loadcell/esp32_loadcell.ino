
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <math.h>
#include <time.h>

#include "HX711.h"
#include "secrets.h"
#include <ESP32Servo.h>
#include "root_ca.h"

// ============================================================
// 1. HX711 CONNECTIONS
// ============================================================

const int LOADCELL_DOUT_PIN = 4;
const int LOADCELL_SCK_PIN = 5;

HX711 scale;
float calibration_factor = 220.0f;

// ============================================================
// 2. SEGREGATION SERVOS
// ============================================================

const int PAN_SERVO_PIN = 18;
const int TILT_SERVO_PIN = 19;

Servo panServo;
Servo tiltServo;

const int PAN_LEFT_ANGLE = 60;       // Metal
const int PAN_CENTER_ANGLE = 90;     // E-waste
const int PAN_RIGHT_ANGLE = 120;     // Plastic

const int TILT_HOME_ANGLE = 90;
const int TILT_RELEASE_ANGLE = 130;

const unsigned long SERVO_MOVE_DELAY_MS = 700UL;
const unsigned long RELEASE_HOLD_MS = 4000UL;

// ============================================================
// 3. BACKEND SETTINGS
// ============================================================

// LOCAL TESTING:
const char* API_BASE_URL = "https://10.165.119.195:8000";

//const char* API_BASE_URL = "https://mpp-smart-bin.onrender.com";

const char* BIN_ID = "BIN001";
const char* SENSOR_ID = "loadcell-01";

// ============================================================
// 4. TIMING SETTINGS
// ============================================================

const unsigned long WIFI_TIMEOUT_MS = 30000UL;
const unsigned long POLL_INTERVAL_MS = 3000UL;

const unsigned long MEASUREMENT_DURATION_MS = 30000UL;
const unsigned long HTTP_TIMEOUT_MS = 15000UL;

// ============================================================
// 5. MECHANICAL IMPACT FINGERPRINTING
// MATCHED TO EXPERIMENTAL LOGGER
// ============================================================

const int BASELINE_SAMPLE_COUNT = 20;

const unsigned long BASELINE_TIMEOUT_MS = 15000UL;
const unsigned long PLACEMENT_TIMEOUT_MS = 60000UL;

const float MIN_TRIGGER_THRESHOLD_G = 0.5f;
const float BASELINE_NOISE_MULTIPLIER = 5.0f;

const unsigned long IMPACT_CAPTURE_DURATION_MS = 8000UL;
const int MAX_IMPACT_SAMPLES = 100;

const int SETTLING_CONSECUTIVE_SAMPLES = 3;

float baselineMean = 0.0f;
float baselineSD = 0.0f;
float placementThreshold = 0.5f;

struct ImpactFeatures {
  float peakWeightG;
  int settlingTimeMs;
  int sampleCount;
  float variationIndex;
};

float impactWeights[MAX_IMPACT_SAMPLES];
unsigned long impactTimestamps[MAX_IMPACT_SAMPLES];

// ============================================================
// 6. WI-FI CONNECTION
// ============================================================

bool connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  Serial.println("Connecting to Wi-Fi...");

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long started = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - started < WIFI_TIMEOUT_MS) {
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
// 7. TLS CLOCK SYNCHRONIZATION
// ============================================================

bool synchronizeClock() {
  Serial.println("Synchronizing clock for TLS verification...");

  configTime(
    0,
    0,
    "pool.ntp.org",
    "time.google.com"
  );

  struct tm timeInfo;

  if (!getLocalTime(&timeInfo, 15000)) {
    Serial.println("ERROR: Could not synchronize system time.");
    return false;
  }

  Serial.print("Synchronized time: ");
  Serial.println(&timeInfo, "%Y-%m-%d %H:%M:%S");

  return true;
}

// ============================================================
// ENSURE WI-FI AND TLS CLOCK ARE READY BEFORE HTTPS
// ============================================================

bool ensureTlsReady() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi disconnected. Reconnecting...");

    if (!connectToWiFi()) {
      Serial.println("HTTPS cancelled: Wi-Fi unavailable.");
      return false;
    }
  }

  // 1700000000 corresponds to November 2023.
  // A clock earlier than this is treated as unsynchronized.

  if (time(nullptr) < 1700000000) {
    Serial.println("TLS clock is not synchronized.");

    if (!synchronizeClock()) {
      Serial.println("HTTPS cancelled: TLS clock unavailable.");
      return false;
    }
  }

  return true;
}

// ============================================================
// 8. SIMPLE JSON STRING FIELD READER
// ============================================================

// Intended for simple string fields such as:
// status, request_id, command_id and route_signal.
//
// This is not a general-purpose JSON parser.

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
// 9. HTTP GET HELPER
// ALL HTTPS REQUESTS USE CA VERIFICATION
// ============================================================

bool httpGetJson(const String& url, String& response) {
  if (!ensureTlsReady()) {
    return false;
  }

  WiFiClientSecure client;
  client.setCACert(ROOT_CA_PEM);

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println("Could not initialize HTTPS GET.");
    return false;
  }

  http.addHeader("Accept", "application/json");

  int code = http.GET();
  bool success = false;

  if (code > 0) {
    response = http.getString();

    Serial.print("GET HTTP status: ");
    Serial.println(code);

    success = (code >= 200 && code < 300);
  } else {
    Serial.print("GET failed: ");
    Serial.println(http.errorToString(code));
  }

  http.end();
  client.stop();

  return success;
}

// ============================================================
// 10. GET ONE SEGREGATION COMMAND
// ============================================================

bool getSegregationCommand(
    String& commandId,
    String& routeSignal
) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  String url = String(API_BASE_URL) +
      "/api/sensor/segregation/next?bin_id=" +
      String(BIN_ID);

  String response;

  if (!httpGetJson(url, response)) {
    Serial.println("Segregation poll failed. No servo movement.");
    return false;
  }

  String status = getJsonString(response, "status");

  if (status != "claimed") {
    return false;
  }

  commandId = getJsonString(response, "command_id");
  routeSignal = getJsonString(response, "route_signal");

  if (commandId.length() == 0 ||
      commandId == "null") {
    Serial.println("ERROR: Claimed command has no valid ID.");
    return false;
  }

  if (routeSignal != "P" &&
      routeSignal != "M" &&
      routeSignal != "E") {
    Serial.println("ERROR: Invalid route. Refusing servo movement.");

    Serial.print("Route signal: ");
    Serial.println(routeSignal);

    return false;
  }

  return true;
}

// ============================================================
// 11. ACKNOWLEDGE SEGREGATION COMPLETION
// ============================================================

bool acknowledgeSegregationCommand(
    const String& commandId
) {
  if (!ensureTlsReady()) {
    Serial.println("Cannot acknowledge segregation command.");
    return false;
  }

  String url = String(API_BASE_URL) +
      "/api/sensor/segregation/" +
      commandId +
      "/complete";

  WiFiClientSecure client;
  client.setCACert(ROOT_CA_PEM);

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println("Could not initialize completion request.");
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Accept", "application/json");

  int code = http.POST("{\"status\":\"completed\"}");

  String response = "";

  if (code > 0) {
    response = http.getString();
  } else {
    Serial.print("Completion POST failed: ");
    Serial.println(http.errorToString(code));
  }

  http.end();
  client.stop();

  Serial.print("Segregation acknowledgement HTTP: ");
  Serial.println(code);

  if (code >= 200 &&
      code < 300 &&
      getJsonString(response, "status") == "completed") {
    Serial.println("Segregation command acknowledged.");
    return true;
  }

  Serial.println("WARNING: Completion was not confirmed.");
  Serial.println(response);

  return false;
}

// ============================================================
// 12. EXECUTE ONE CLAIMED SEGREGATION COMMAND
// ============================================================

bool executeSegregation(
    const String& commandId,
    const String& routeSignal
) {
  int panAngle;

  if (routeSignal == "M") {
    panAngle = PAN_LEFT_ANGLE;
  } else if (routeSignal == "E") {
    panAngle = PAN_CENTER_ANGLE;
  } else if (routeSignal == "P") {
    panAngle = PAN_RIGHT_ANGLE;
  } else {
    Serial.println("Rejected route. Servos will not move.");
    return false;
  }

  Serial.println();
  Serial.println("====================================");
  Serial.println("SEGREGATION COMMAND CLAIMED");

  Serial.print("Command ID: ");
  Serial.println(commandId);

  Serial.print("Route signal: ");
  Serial.println(routeSignal);

  Serial.print("Pan angle: ");
  Serial.println(panAngle);

  Serial.println("====================================");

  // Step 1: Align pan with selected compartment.
  panServo.write(panAngle);
  delay(SERVO_MOVE_DELAY_MS);

  // Step 2: Release item.
  tiltServo.write(TILT_RELEASE_ANGLE);
  delay(RELEASE_HOLD_MS);

  // Step 3: Return tilt to home.
  tiltServo.write(TILT_HOME_ANGLE);
  delay(SERVO_MOVE_DELAY_MS);

  // Step 4: Return pan to center.
  panServo.write(PAN_CENTER_ANGLE);
  delay(SERVO_MOVE_DELAY_MS);

  // Step 5: Acknowledge after movement is complete.
  return acknowledgeSegregationCommand(commandId);
}

// ============================================================
// 13. POLL FOR SEGREGATION
// ============================================================

void pollSegregationCommand() {
  String commandId;
  String routeSignal;

  if (!getSegregationCommand(commandId, routeSignal)) {
    return;
  }

  executeSegregation(commandId, routeSignal);
}

// ============================================================
// 14. CHECK FOR A DASHBOARD MEASUREMENT REQUEST
// ============================================================

bool getMeasurementRequest(String& requestId) {
  String url = String(API_BASE_URL) +
      "/api/sensor/requests/next?bin_id=" +
      String(BIN_ID);

  String response;

  if (!httpGetJson(url, response)) {
    Serial.println("Could not check for a measurement request.");
    return false;
  }

  String status = getJsonString(response, "status");

  if (status != "claimed") {
    return false;
  }

  requestId = getJsonString(response, "request_id");

  if (requestId.length() == 0 ||
      requestId == "null") {
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
// 15. COLLECT EMPTY-PLATFORM BASELINE
// MATCHED TO EXPERIMENTAL LOGGER
// ============================================================

bool collectBaseline() {
  Serial.println();
  Serial.println("COLLECTING EMPTY-PLATFORM BASELINE");
  Serial.println("Keep the platform completely empty.");

  double sum = 0.0;
  double sumSquared = 0.0;

  int collected = 0;

  unsigned long started = millis();

  while (collected < BASELINE_SAMPLE_COUNT) {

    if (millis() - started > BASELINE_TIMEOUT_MS) {
      Serial.println("ERROR: Baseline collection timed out.");
      return false;
    }

    if (scale.is_ready()) {
      float weight = scale.get_units(1);

      if (isfinite(weight)) {
        sum += weight;
        sumSquared += (double)weight * weight;

        collected++;

        Serial.print("Baseline ");
        Serial.print(collected);
        Serial.print("/");
        Serial.print(BASELINE_SAMPLE_COUNT);
        Serial.print(": ");

        Serial.println(weight, 4);
      }
    }

    delay(2);
  }

  baselineMean = (float)(sum / collected);

  double variance =
      (sumSquared / collected) -
      ((double)baselineMean * baselineMean);

  if (variance < 0.0) {
    variance = 0.0;
  }

  baselineSD = (float)sqrt(variance);

  placementThreshold =
      BASELINE_NOISE_MULTIPLIER * baselineSD;

  if (placementThreshold < MIN_TRIGGER_THRESHOLD_G) {
    placementThreshold = MIN_TRIGGER_THRESHOLD_G;
  }

  Serial.println("------------------------------------");
  Serial.println("BASELINE SUMMARY");

  Serial.print("Mean: ");
  Serial.println(baselineMean, 4);

  Serial.print("Standard deviation: ");
  Serial.println(baselineSD, 4);

  Serial.print("Placement threshold: ");
  Serial.println(placementThreshold, 4);

  Serial.println("------------------------------------");

  return true;
}

// ============================================================
// 16. WAIT FOR ACTUAL ITEM PLACEMENT
// MATCHED TO EXPERIMENTAL LOGGER
// ============================================================

bool waitForObjectPlacement() {
  Serial.println();
  Serial.println("WAITING FOR ACTUAL ITEM PLACEMENT");
  Serial.println("Place the item on the load-cell platform.");

  unsigned long started = millis();

  const float triggerLevel =
      baselineMean + placementThreshold;

  while (millis() - started < PLACEMENT_TIMEOUT_MS) {

    if (scale.is_ready()) {
      float weight = scale.get_units(1);

      if (isfinite(weight) && weight > triggerLevel) {

        Serial.println();
        Serial.println("====================================");
        Serial.println("ITEM PLACEMENT DETECTED");

        Serial.print("Detected weight: ");
        Serial.println(weight, 3);

        Serial.print("Trigger level: ");
        Serial.println(triggerLevel, 3);

        Serial.println("====================================");

        return true;
      }
    }

    delay(2);
  }

  Serial.println("ERROR: Placement timeout.");
  Serial.println("No item was detected within 60 seconds.");

  return false;
}

// ============================================================
// 17. CAPTURE IMPACT BURST
// 8 SECONDS, MAXIMUM 100 SAMPLES
// ============================================================

bool captureImpactBurst(ImpactFeatures& features) {
  Serial.println();
  Serial.println("MECHANICAL IMPACT CAPTURE STARTED");

  features.peakWeightG = 0.0f;
  features.settlingTimeMs = -1;
  features.sampleCount = 0;
  features.variationIndex = 0.0f;

  const unsigned long captureStart = millis();

  double total = 0.0;
  double totalSquared = 0.0;

  float peak = -INFINITY;
  float modelPeak = -INFINITY;

  while (millis() - captureStart <
         IMPACT_CAPTURE_DURATION_MS) {

    if (scale.is_ready()) {
      float weight = scale.get_units(1);

      unsigned long elapsed =
          millis() - captureStart;

      if (isfinite(weight) &&
          features.sampleCount < MAX_IMPACT_SAMPLES) {

        int index = features.sampleCount;

        impactWeights[index] = weight;
        impactTimestamps[index] = elapsed;

        total += weight;
        totalSquared += (double)weight * weight;

        if (weight > peak) {
          peak = weight;
        }

        if (elapsed <= 2500UL && weight > modelPeak) {
          modelPeak = weight;
        }

        features.sampleCount++;

        Serial.print(elapsed);
        Serial.print(",");
        Serial.print(weight, 3);
        Serial.println(",CAPTURE");
      }
    }

    delay(1);
  }

  if (features.sampleCount < 3) {
    Serial.println("ERROR: Too few impact samples.");
    return false;
  }

  double count = features.sampleCount;
  double mean = total / count;

  double variance =
      (totalSquared / count) - (mean * mean);

  if (variance < 0.0) {
    variance = 0.0;
  }

  double standardDeviation = sqrt(variance);

  double denominator = fabs(mean);

  if (denominator < 0.5) {
    denominator = 0.5;
  }

  if (!isfinite(modelPeak)) {
    Serial.println("ERROR: No valid samples in the first 2500 ms.");
    return false;
  }

  features.peakWeightG = modelPeak;

  features.variationIndex =
      (float)(standardDeviation / denominator);

  Serial.println("------------------------------------");
  Serial.println("IMPACT CAPTURE SUMMARY");

  Serial.print("Samples: ");
  Serial.println(features.sampleCount);

  Serial.print("Model peak (first 2500 ms): ");
  Serial.println(features.peakWeightG, 3);

  Serial.print("Full 8-second peak: ");
  Serial.println(peak, 3);

  Serial.print("Mean: ");
  Serial.println(mean, 3);

  Serial.print("Standard deviation: ");
  Serial.println(standardDeviation, 4);

  Serial.print("Variation index: ");
  Serial.println(features.variationIndex, 5);

  Serial.println("------------------------------------");

  return true;
}

// ============================================================
// 18. MEASURE FINAL STABLE WEIGHT
// 30 SECONDS, MATCHED TO EXPERIMENTAL LOGGER
// ============================================================

bool measureAverageWeight(float& averageWeight) {
  double total = 0.0;
  unsigned long count = 0;

  Serial.println();
  Serial.println("STARTING 30-SECOND STABLE MEASUREMENT");

  unsigned long started = millis();

  while (millis() - started < MEASUREMENT_DURATION_MS) {

    if (scale.is_ready()) {
      float weight = scale.get_units(1);

      if (isfinite(weight)) {
        total += weight;
        count++;

        Serial.print("Elapsed: ");
        Serial.print((millis() - started) / 1000.0, 1);
        Serial.print(" s | Weight: ");
        Serial.println(weight, 3);
      }
    }

    delay(2);
  }

  if (count == 0) {
    Serial.println("ERROR: No valid stable readings.");
    return false;
  }

  averageWeight = (float)(total / count);

  if (!isfinite(averageWeight) ||
      averageWeight <= 0.0f) {
    Serial.println("ERROR: Invalid final average.");
    return false;
  }

  Serial.println("------------------------------------");

  Serial.print("Stable sample count: ");
  Serial.println(count);

  Serial.print("Final average weight: ");
  Serial.println(averageWeight, 3);

  Serial.println("------------------------------------");

  return true;
}

// ============================================================
// 19. CALCULATE IMPACT SETTLING TIME
// ============================================================

void calculateImpactSettlingTime(
    ImpactFeatures& features,
    float finalAverageWeight
) {
  features.settlingTimeMs = -1;

  if (features.sampleCount <
      SETTLING_CONSECUTIVE_SAMPLES) {
    return;
  }

  // Tolerance = max(5% of final average, 0.5 g).

  float tolerance = fabs(finalAverageWeight) * 0.05f;

  if (tolerance < 0.5f) {
    tolerance = 0.5f;
  }

  // Find peak index.

  int peakIndex = 0;
  float peak = impactWeights[0];

  for (int i = 1; i < features.sampleCount; i++) {
    if (impactWeights[i] > peak) {
      peak = impactWeights[i];
      peakIndex = i;
    }
  }

  // Find the first set of three consecutive readings
  // within the acceptable band after the peak.

  int consecutive = 0;
  int firstStableIndex = -1;

  for (int i = peakIndex + 1;
       i < features.sampleCount;
       i++) {

    float difference =
        fabs(impactWeights[i] - finalAverageWeight);

    if (difference <= tolerance) {
      if (consecutive == 0) {
        firstStableIndex = i;
      }

      consecutive++;

      if (consecutive >= SETTLING_CONSECUTIVE_SAMPLES) {
        features.settlingTimeMs =
            (int)impactTimestamps[firstStableIndex];

        break;
      }
    } else {
      consecutive = 0;
      firstStableIndex = -1;
    }
  }

  Serial.print("Estimated settling time: ");

  if (features.settlingTimeMs >= 0) {
    Serial.print(features.settlingTimeMs);
    Serial.println(" ms");
  } else {
    Serial.println("Not reached during impact capture window.");
  }
}

// ============================================================
// 20. SUBMIT WEIGHT AND IMPACT FEATURES
// ============================================================

bool submitMeasurement(
    const String& requestId,
    float averageWeight,
    const ImpactFeatures& impact
) {
  if (!ensureTlsReady()) {
    Serial.println("Cannot submit: HTTPS is unavailable.");
    return false;
  }

  String url = String(API_BASE_URL) +
      "/api/sensor/requests/" +
      requestId +
      "/reading";

  String payload = "{";

  payload.reserve(6000);

  payload += "\"bin_id\":\"" + String(BIN_ID) + "\",";
  payload += "\"sensor_id\":\"" + String(SENSOR_ID) + "\",";
  payload += "\"weight_g\":" + String(averageWeight, 2) + ",";

  payload += "\"impact_peak_g\":" +
      String(impact.peakWeightG, 3) + ",";

  payload += "\"impact_settling_ms\":";

  if (impact.settlingTimeMs >= 0) {
    payload += String(impact.settlingTimeMs);
  } else {
    payload += "null";
  }

  payload += ",";

  payload += "\"impact_sample_count\":" +
      String(impact.sampleCount) + ",";

  payload += "\"impact_variation_index\":" +
    String(impact.variationIndex, 5) + ",";

// Empty-platform baseline used by the experimental logger.
payload += "\"baseline_mean_g\":" +
    String(baselineMean, 4) + ",";

// Send the original impact samples.
// The backend will independently extract the four features.
payload += "\"raw_samples\":[";

for (int i = 0; i < impact.sampleCount; i++) {

  if (i > 0) {
    payload += ",";
  }

  payload += "{";

  payload += "\"t_ms\":" +
      String((unsigned long)impactTimestamps[i]) + ",";

  payload += "\"weight_g\":" +
      String(impactWeights[i], 4);

  payload += "}";
}

payload += "]";

payload += "}";

  WiFiClientSecure client;
  client.setCACert(ROOT_CA_PEM);

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println("Could not initialize measurement submission.");
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Accept", "application/json");

  Serial.println();
  Serial.println("Submitting measurement and impact features.");

  Serial.print("Request ID: ");
  Serial.println(requestId);

  Serial.print("Stable average: ");
  Serial.print(averageWeight, 2);
  Serial.println(" g");

  Serial.print("Impact peak: ");
  Serial.print(impact.peakWeightG, 3);
  Serial.println(" g");

  Serial.print("Settling time: ");
  Serial.print(impact.settlingTimeMs);
  Serial.println(" ms");

  Serial.print("Sample count: ");
  Serial.println(impact.sampleCount);

  Serial.print("Variation index: ");
  Serial.println(impact.variationIndex, 5);

  Serial.println("JSON payload:");
  Serial.println(payload);

  // Preserve single-POST behaviour.
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
        Serial.println("SUCCESS: Measurement recorded.");
        success = true;
      } else {
        Serial.println("WARNING: Completion was not confirmed.");
      }
    } else {
      Serial.println("ERROR: Backend rejected measurement.");
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
// 21. MARK THE SCALE REQUEST READY
// ============================================================

bool markRequestReady(const String& requestId) {
  if (!ensureTlsReady()) {
    Serial.println("Cannot mark request ready.");
    return false;
  }

  String url = String(API_BASE_URL) +
      "/api/sensor/requests/" +
      requestId +
      "/ready";

  WiFiClientSecure client;
  client.setCACert(ROOT_CA_PEM);

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println("Could not initialize ready request.");
    return false;
  }

  http.addHeader("Accept", "application/json");

  int code = http.POST("");

  String response = "";

  if (code > 0) {
    response = http.getString();
  } else {
    Serial.print("Ready POST failed: ");
    Serial.println(http.errorToString(code));
  }

  http.end();
  client.stop();

  Serial.print("Ready response code: ");
  Serial.println(code);

  Serial.println(response);

  return code >= 200 &&
      code < 300 &&
      getJsonString(response, "status") == "ready";
}

// ============================================================
// 22. NOTIFY BACKEND THAT IMPACT WAS DETECTED
// ============================================================

bool markImpactDetected(const String& requestId) {
  if (!ensureTlsReady()) {
    Serial.println("Cannot notify backend of impact detection.");
    return false;
  }

  String url = String(API_BASE_URL) +
      "/api/sensor/requests/" +
      requestId +
      "/impact-detected";

  WiFiClientSecure client;
  client.setCACert(ROOT_CA_PEM);

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println("Could not initialize impact-detected request.");
    return false;
  }

  http.addHeader("Accept", "application/json");

  int code = http.POST("");

  String response = "";

  if (code > 0) {
    response = http.getString();
  } else {
    Serial.print("Impact-detected POST failed: ");
    Serial.println(http.errorToString(code));
  }

  http.end();
  client.stop();

  Serial.print("Impact-detected response code: ");
  Serial.println(code);

  Serial.println(response);

  if (code >= 200 &&
      code < 300 &&
      getJsonString(response, "status") == "measuring") {
    Serial.println("Backend confirmed measuring state.");
    return true;
  }

  Serial.println("ERROR: Backend did not confirm measuring state.");

  return false;
}

// ============================================================
// 23. WAIT FOR DASHBOARD CONFIRMATION
// ============================================================

bool waitForMeasurementConfirmation(
    const String& requestId
) {
  Serial.println("Scale is ready.");
  Serial.println("Waiting for dashboard confirmation...");

  const unsigned long started = millis();
  const unsigned long timeoutMs = 90000UL;

  while (millis() - started < timeoutMs) {

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("Wi-Fi disconnected. Reconnecting...");

      if (!connectToWiFi()) {
        delay(1000);
        continue;
      }
    }

    String url = String(API_BASE_URL) +
        "/api/sensor/requests/" +
        requestId;

    String response;

    if (httpGetJson(url, response)) {
      String status = getJsonString(response, "status");

      if (status == "armed") {
        Serial.println("Dashboard confirmation received.");
        Serial.println("Backend request is armed.");
        return true;
      }

      if (status == "expired" ||
          status == "completed") {
        Serial.print("Request ended. Status: ");
        Serial.println(status);
        return false;
      }
    }

    delay(1500);
  }

  Serial.println("Timed out waiting for dashboard confirmation.");

  return false;
}

// ============================================================
// 24. PROCESS ONE MEASUREMENT REQUEST
// ============================================================

void processMeasurementRequest(
    const String& requestId
) {
  Serial.println();
  Serial.println("========================================");
  Serial.println("NEW MEASUREMENT REQUEST");
  Serial.println("Keep platform EMPTY.");
  Serial.println("========================================");

  // Step 1: Check HX711.

  if (!scale.is_ready()) {
    Serial.println("ERROR: HX711 is not ready.");
    return;
  }

  // Step 2: Tare empty platform.

  Serial.println("Taring empty platform...");

  scale.tare(20);

  Serial.println("Tare complete.");

  // Step 3: Collect experimental baseline.

  if (!collectBaseline()) {
    Serial.println("Baseline collection failed.");
    return;
  }

  // Step 4: Tell backend scale is ready.

  if (!markRequestReady(requestId)) {
    Serial.println("ERROR: Could not mark request ready.");
    return;
  }

  Serial.println("Scale ready.");
  Serial.println("Waiting for dashboard confirmation.");

  // Step 5: Wait for dashboard confirmation.

  if (!waitForMeasurementConfirmation(requestId)) {
    Serial.println("Request cancelled or expired.");
    return;
  }

  // Step 6: Wait for actual physical placement.

  if (!waitForObjectPlacement()) {
    Serial.println("No item detected. Measurement cancelled.");
    return;
  }

  // Step 7: Capture impact IMMEDIATELY.
  //
  // Do not perform an HTTPS request between placement
  // detection and impact capture.

  ImpactFeatures impact;

  if (!captureImpactBurst(impact)) {
    Serial.println("Impact capture failed.");
    return;
  }

  // Step 8: Notify backend after impact data is captured.
  //
  // Backend transitions armed -> measuring here.

  if (!markImpactDetected(requestId)) {
    Serial.println("ERROR: Backend did not confirm measuring.");
    Serial.println("Captured impact data will not be submitted.");
    return;
  }

  // Step 9: Measure final stable weight.

  float averageWeight = 0.0f;

  if (!measureAverageWeight(averageWeight)) {
    Serial.println("Stable weight measurement failed.");
    return;
  }

  // Step 10: Calculate settling time.

  calculateImpactSettlingTime(
      impact,
      averageWeight
  );

  // Step 11: Submit weight and mechanical features.

  if (submitMeasurement(
        requestId,
        averageWeight,
        impact
      )) {

    Serial.println();
    Serial.println("MEASUREMENT COMPLETED SUCCESSFULLY.");

  } else {
    Serial.println("Submission not confirmed. Check backend status.");
  }

  Serial.println("Returning to request polling.");
}

// ============================================================
// 25. SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("====================================");
  Serial.println("     RECYCLE2EARN SMART BIN");
  Serial.println(" LOAD CELL + SERVO SEGREGATION");
  Serial.println("====================================");

  // ----------------------------------------------------------
  // Initialize HX711
  // ----------------------------------------------------------

  Serial.println("Initializing HX711...");

  scale.begin(
    LOADCELL_DOUT_PIN,
    LOADCELL_SCK_PIN
  );

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

  // ----------------------------------------------------------
  // Startup tare
  // ----------------------------------------------------------

  Serial.println();
  Serial.println("Ensure the weighing platform is EMPTY.");
  Serial.println("Taring in 2 seconds...");

  delay(2000);

  scale.tare(20);

  Serial.println("Tare complete.");

  // ----------------------------------------------------------
  // Initialize servos
  // ----------------------------------------------------------

  Serial.println("Initializing segregation servos...");

  panServo.setPeriodHertz(50);
  tiltServo.setPeriodHertz(50);

  panServo.attach(
    PAN_SERVO_PIN,
    500,
    2400
  );

  tiltServo.attach(
    TILT_SERVO_PIN,
    500,
    2400
  );

  if (!panServo.attached() ||
      !tiltServo.attached()) {
    Serial.println("WARNING: Servo attachment issue.");
  }

  panServo.write(PAN_CENTER_ANGLE);
  tiltServo.write(TILT_HOME_ANGLE);

  delay(SERVO_MOVE_DELAY_MS);

  Serial.println("Servo initialization commands sent.");

  // ----------------------------------------------------------
  // Connect to Wi-Fi and synchronize TLS clock
  // ----------------------------------------------------------

  if (connectToWiFi()) {
    if (!synchronizeClock()) {
      Serial.println("WARNING: TLS clock synchronization failed.");
      Serial.println("HTTPS requests will retry synchronization.");
    }
  }

  // ----------------------------------------------------------
  // Startup complete
  // ----------------------------------------------------------

  Serial.println();
  Serial.println("====================================");
  Serial.println("SMART BIN INITIALIZATION COMPLETE");
  Serial.println("====================================");

  Serial.println("Ready for dashboard requests.");

  Serial.println(
    "Segregation requires a claimed backend command."
  );

  Serial.println(
    "No command means no segregation movement."
  );
}

// ============================================================
// 26. MAIN LOOP
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

  // ----------------------------------------------------------
  // Measurement workflow
  // ----------------------------------------------------------

  if (getMeasurementRequest(requestId)) {
    processMeasurementRequest(requestId);
  } else {
    Serial.println("No measurement request.");
  }

  // ----------------------------------------------------------
  // Segregation workflow
  // ----------------------------------------------------------

  pollSegregationCommand();

  delay(POLL_INTERVAL_MS);
}
