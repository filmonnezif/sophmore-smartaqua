#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <time.h>

// Wi-Fi Credentials
const char* ssid = "F306";
const char* password = "dubai@123";

// NTP Configuration
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 14400;
const int   daylightOffset_sec = 0;

// Sensor Pins
#define DHTPIN 4
#define DHTTYPE DHT22
#define ULTRASONIC_TRIG_PIN 5
#define ULTRASONIC_ECHO_PIN 18
#define TDS_PIN 34
#define DO_PIN 35
#define LIGHT_SENSOR_PIN 32
#define PH_SENSOR_PIN 33

DHT dht(DHTPIN, DHTTYPE);

void connectToWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to Wi-Fi");
}

String getCurrentTime() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "2025-03-07T00:00:00"; // Fallback time
  }
  char timeString[25];
  strftime(timeString, sizeof(timeString), "%Y-%m-%dT%H:%M:%S", &timeinfo);
  return String(timeString);
}

float analogToVoltage(int analogValue) {
  return analogValue * (3.3 / 4095.0); // Convert ADC reading to voltage for ESP32
}

void readDHTSensor(float &temperature, float &humidity) {
  delay(2000); // Required delay for DHT sensor stability
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Failed to read from DHT sensor!");
    temperature = humidity = -1; // Error values
  }
}

float readWaterLevel() {
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  long duration = pulseIn(ULTRASONIC_ECHO_PIN, HIGH, 30000); // Timeout to prevent hanging
  if (duration == 0) {
    Serial.println("Ultrasonic sensor timeout");
    return -1;
  }
  return duration * 0.034 / 2;
}

void sendData() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin("http://192.168.1.150:8000/api/sensors/manual");
    http.addHeader("Content-Type", "application/json");

    float temperature, humidity, water_level, tds_level, dissolved_oxygen, light_level, ph_level;
    readDHTSensor(temperature, humidity);
    water_level = readWaterLevel();
    tds_level = analogToVoltage(analogRead(TDS_PIN));
    dissolved_oxygen = analogToVoltage(analogRead(DO_PIN));
    light_level = analogToVoltage(analogRead(LIGHT_SENSOR_PIN));
    ph_level = analogToVoltage(analogRead(PH_SENSOR_PIN));

    StaticJsonDocument<256> jsonDoc;
    jsonDoc["timestamp"] = getCurrentTime();
    jsonDoc["temperature"] = temperature;
    jsonDoc["humidity"] = humidity;
    jsonDoc["water_level"] = water_level;
    jsonDoc["tds_level"] = tds_level;
    jsonDoc["dissolved_oxygen"] = dissolved_oxygen;
    jsonDoc["light_level"] = light_level;
    jsonDoc["ph_level"] = ph_level;

    String jsonString;
    serializeJson(jsonDoc, jsonString);
    int httpResponseCode = http.POST(jsonString);
    if (httpResponseCode > 0) {
      Serial.println("✅ Data sent successfully!");
    } else {
      Serial.print("❌ Error sending data: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("❌ No WiFi connection. Skipping data transmission.");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  dht.begin();
  connectToWiFi();
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
}

void loop() {
  sendData();
  delay(5000);
}
