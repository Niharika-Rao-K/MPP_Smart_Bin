
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <math.h>
#include "HX711.h"
#include "secrets.h"
#include <ESP32Servo.h>

// ============================================================
// 1. HX711 CONNECTIONS
// ============================================================

const int LOADCELL_DOUT_PIN = 4;
const int LOADCELL_SCK_PIN = 5;

HX711 scale;
float calibration_factor = 220;

// ============================================================
// 2. SEGREGATION SERVOS
// ============================================================

const int PAN_SERVO_PIN = 18;
const int TILT_SERVO_PIN = 19;

Servo panServo;
Servo tiltServo;

// Physical layout viewed from the front:
// Metal = left, E-waste = center, Plastic = right.
//
// These are INITIAL angles. Calibrate with an empty tray.

const int PAN_LEFT_ANGLE = 60;       // Metal (M)
const int PAN_CENTER_ANGLE = 90;     // E-waste (E)
const int PAN_RIGHT_ANGLE = 120;     // Plastic (P)

const int TILT_HOME_ANGLE = 90;
const int TILT_RELEASE_ANGLE = 130;

const unsigned long SERVO_MOVE_DELAY_MS = 700UL;
const unsigned long RELEASE_HOLD_MS = 4000UL;

// ============================================================
// 3. BACKEND SETTINGS
// ============================================================

// Change this if your computer's LAN IP changes.
// The ESP32 and local backend must be on a reachable network.

const char* API_BASE_URL = "http://10.165.119.195:8000";

const char* BIN_ID = "BIN001";
const char* SENSOR_ID = "loadcell-01";

// ============================================================
// 4. TIMING SETTINGS
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
// 6. SIMPLE JSON STRING FIELD READER
// ============================================================

// Intended for simple JSON string fields such as status,
// request_id, command_id and route_signal.
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
// 7. HTTP GET HELPER
// ============================================================

bool httpGetJson(const String& url, String& response) {
  WiFiClient client;
  HTTPClient http;

  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println("Could not initialize HTTP GET.");
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
// 8. GET ONE SEGREGATION COMMAND
// ============================================================

// The backend must claim the command and return status="claimed"
// before the ESP32 is allowed to move either servo.
//
// The backend should return only pending commands. Commands
// already in processing must not be automatically replayed.

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
    Serial.println(
      "Segregation poll failed. No servo movement."
    );
    return false;
  }

  String status = getJsonString(response, "status");

  if (status != "claimed") {
    // "waiting" is normal when there is no pending command.
    return false;
  }

  commandId = getJsonString(response, "command_id");
  routeSignal = getJsonString(response, "route_signal");

  if (commandId.length() == 0 ||
      commandId == "null") {
    Serial.println(
      "ERROR: Claimed command has no valid command ID."
    );
    Serial.println(
      "Command may remain in processing; inspect backend."
    );
    return false;
  }

  if (routeSignal != "P" &&
      routeSignal != "M" &&
      routeSignal != "E") {
    Serial.println(
      "ERROR: Invalid route. Refusing servo movement."
    );
    Serial.print("Route signal: ");
    Serial.println(routeSignal);
    Serial.println(
      "Inspect this command before manually recovering it."
    );
    return false;
  }

  return true;
}

// ============================================================
// 9. ACKNOWLEDGE SEGREGATION COMPLETION
// ============================================================

// Call only after the complete servo movement sequence.

bool acknowledgeSegregationCommand(
    const String& commandId
) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(
      "Cannot acknowledge: Wi-Fi disconnected."
    );
    return false;
  }

  String url = String(API_BASE_URL) +
      "/api/sensor/segregation/" +
      commandId +
      "/complete";

  WiFiClient client;
  HTTPClient http;

  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println(
      "Could not initialize completion request."
    );
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
    Serial.println(
      "Segregation command acknowledged as completed."
    );
    return true;
  }

  Serial.println(
    "WARNING: Physical movement may have occurred, "
    "but completion was not confirmed."
  );
  Serial.println(
    "Inspect the item and command record before recovery."
  );
  Serial.println(response);

  return false;
}

// ============================================================
// 10. EXECUTE ONE CLAIMED SEGREGATION COMMAND
// ============================================================

// Route mapping:
// M = left compartment (metal)
// E = center compartment (e-waste)
// P = right compartment (plastic)
// R or any unknown signal = no movement
//
// This function is called only after a valid command has
// been claimed by getSegregationCommand().

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
    Serial.println(
      "Rejected route. Servos will not move."
    );
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

  // Step 1: Align pan with the selected compartment.
  panServo.write(panAngle);
  delay(SERVO_MOVE_DELAY_MS);

  // Step 2: Move tilt to release position.
  tiltServo.write(TILT_RELEASE_ANGLE);
  delay(RELEASE_HOLD_MS);

  // Step 3: Return tilt to home position.
  tiltServo.write(TILT_HOME_ANGLE);
  delay(SERVO_MOVE_DELAY_MS);

  // Step 4: Return pan to center.
  panServo.write(PAN_CENTER_ANGLE);
  delay(SERVO_MOVE_DELAY_MS);

  // Step 5: Acknowledge only after motion has finished.
  return acknowledgeSegregationCommand(commandId);
}

// ============================================================
// 11. POLL FOR SEGREGATION
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
// 12. CHECK FOR A DASHBOARD MEASUREMENT REQUEST
// ============================================================

bool getMeasurementRequest(String& requestId) {
  String url = String(API_BASE_URL) +
      "/api/sensor/requests/next?bin_id=" +
      String(BIN_ID);

  String response;

  if (!httpGetJson(url, response)) {
    Serial.println("Could not check for a request.");
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
// 13. TAKE ONE REQUESTED MEASUREMENT
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

  if (!isfinite(averageWeight) ||
      averageWeight <= 0.0) {
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
// 14. SUBMIT WEIGHT FOR THE EXACT REQUEST
// ============================================================

bool submitMeasurement(
    const String& requestId,
    float averageWeight
) {
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

  WiFiClient client;
  HTTPClient http;

  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println(
      "Could not initialize weight submission."
    );
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Accept", "application/json");

  Serial.println("Submitting weight for request:");
  Serial.println(requestId);
  Serial.print("Weight: ");
  Serial.print(averageWeight, 2);
  Serial.println(" g");

  // Preserve the existing single-POST behavior.
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
    Serial.println(
      "No automatic POST retry will occur."
    );
  }

  http.end();
  client.stop();

  return success;
}

// ============================================================
// 15. MARK THE SCALE REQUEST READY
// ============================================================

bool markRequestReady(const String& requestId) {
  String url = String(API_BASE_URL) +
      "/api/sensor/requests/" +
      requestId +
      "/ready";

  WiFiClient client;
  HTTPClient http;

  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(client, url)) {
    Serial.println(
      "Could not connect to backend to mark scale ready."
    );
    return false;
  }

  http.addHeader("Accept", "application/json");

  int code = http.POST("");
  String response = "";

  if (code > 0) {
    response = http.getString();
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
// 16. WAIT FOR DASHBOARD CONFIRMATION
// ============================================================

bool waitForMeasurementConfirmation(
    const String& requestId
) {
  Serial.println(
    "Scale is ready. Waiting for dashboard confirmation..."
  );

  const unsigned long started = millis();
  const unsigned long timeoutMs = 90000UL;

  while (millis() - started < timeoutMs) {
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println(
        "Wi-Fi disconnected. Reconnecting..."
      );

      connectToWiFi();
      delay(1000);
      continue;
    }

    String url = String(API_BASE_URL) +
        "/api/sensor/requests/" +
        requestId;

    String response;

    if (httpGetJson(url, response)) {
      String status = getJsonString(response, "status");

      if (status == "measuring") {
        Serial.println(
          "Dashboard confirmed. Starting measurement."
        );
        return true;
      }

      if (status == "expired" ||
          status == "completed") {
        Serial.print(
          "Request ended before weighing. Status: "
        );
        Serial.println(status);
        return false;
      }
    }

    delay(1500);
  }

  Serial.println(
    "Timed out waiting for dashboard confirmation."
  );
  return false;
}

// ============================================================
// 17. PROCESS ONE MEASUREMENT REQUEST
// ============================================================

void processMeasurementRequest(
    const String& requestId
) {
  Serial.println();
  Serial.println("========================================");
  Serial.println("New measurement request received.");
  Serial.println("Keep the platform EMPTY while taring.");
  Serial.println("========================================");

  // Step 1: Check HX711.
  if (!scale.is_ready()) {
    Serial.println("ERROR: HX711 is not ready.");
    return;
  }

  // Step 2: Tare the empty platform.
  Serial.println(
    "Taring scale. Keep platform empty..."
  );

  scale.tare(20);
  Serial.println("Tare complete.");

  // Step 3: Tell the backend the scale is ready.
  if (!markRequestReady(requestId)) {
    Serial.println(
      "ERROR: Could not mark request ready."
    );
    Serial.println(
      "Check backend logs and request status."
    );
    return;
  }

  Serial.println("Scale tared successfully.");
  Serial.println(
    "Place the waste item when the dashboard prompts you."
  );

  // Step 4: Wait for dashboard confirmation.
  if (!waitForMeasurementConfirmation(requestId)) {
    Serial.println(
      "Measurement cancelled or confirmation timed out."
    );
    Serial.println(
      "Returning to request polling."
    );
    return;
  }

  // Step 5: Preserve the existing 30-second average.
  float averageWeight = 0.0;

  if (!measureAverageWeight(averageWeight)) {
    Serial.println(
      "Measurement failed. Request may expire; "
      "start a new deposit attempt."
    );
    return;
  }

  // Step 6: Submit the measured weight.
  if (submitMeasurement(requestId, averageWeight)) {
    Serial.println(
      "Measurement request completed."
    );
  } else {
    Serial.println(
      "Submission was not confirmed. Check backend "
      "status before attempting another deposit."
    );
  }

  Serial.println(
    "Returning to request polling."
  );
}

// ============================================================
// 18. SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("====================================");
  Serial.println("     RECYCLE2EARN SMART BIN");
  Serial.println(" LOAD CELL + SERVO SEGREGATION");
  Serial.println("====================================");

  // Initialize HX711.
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
    Serial.println(
      "ERROR: HX711 is not responding."
    );
    Serial.println(
      "Check DT, SCK, VCC and GND."
    );

    while (true) {
      delay(1000);
    }
  }

  scale.set_scale(calibration_factor);
  Serial.println("HX711 initialized.");

  // IMPORTANT: platform must be empty during startup tare.
  Serial.println();
  Serial.println(
    "Ensure the weighing platform is EMPTY."
  );
  Serial.println("Taring in 2 seconds...");
  delay(2000);

  scale.tare(20);
  Serial.println("Tare complete.");

  // Initialize the servos.
  Serial.println(
    "Initializing segregation servos..."
  );

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
    Serial.println(
      "WARNING: One or both servo attachments failed."
    );
  }

  // Start at neutral/home positions.
  panServo.write(PAN_CENTER_ANGLE);
  tiltServo.write(TILT_HOME_ANGLE);

  delay(SERVO_MOVE_DELAY_MS);

  Serial.println(
    "Servo initialization commands sent."
  );

  // Connect to Wi-Fi.
  connectToWiFi();

  Serial.println();
  Serial.println(
    "Ready for dashboard requests."
  );
  Serial.println(
    "Segregation requires a claimed backend command."
  );
  Serial.println(
    "No command means no segregation movement."
  );
}

// ============================================================
// 19. MAIN LOOP
// ============================================================

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(
      "Wi-Fi disconnected; reconnecting..."
    );

    if (!connectToWiFi()) {
      delay(POLL_INTERVAL_MS);
      return;
    }
  }

  String requestId;

  // Preserve the existing measurement-request workflow.
  if (getMeasurementRequest(requestId)) {
    processMeasurementRequest(requestId);
  } else {
    Serial.println(
      "No measurement request."
    );
  }

  // Poll segregation after measurement processing.
  // The backend must return status="claimed" before
  // any physical release can occur.
  pollSegregationCommand();

  delay(POLL_INTERVAL_MS);
}
