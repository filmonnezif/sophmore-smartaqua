#include <WiFi.h>  // Use <ESP8266WiFi.h> if you're using ESP8266
#include <HTTPClient.h>  // Library for making HTTP requests
#include <ArduinoJson.h>  // For creating JSON data to send
#include <DHT.h>  // Library for DHT sensor
#include <time.h>  // For NTP time

const char* ssid = "****";
const char* password = "****";

const String serverUrl = "http://192.168.1.150:8000/api/sensors/manual";  // Adjust the server's address

// DHT Sensor setup
#define DHTPIN 4  // Digital pin connected to the DHT sensor
#define DHTTYPE DHT22  // DHT 22 (AM2302) - Change to DHT11 if you're using that sensor
DHT dht(DHTPIN, DHTTYPE);

// NTP Server settings
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0;      
const int daylightOffset_sec = 0;   // Change for Daylight Saving Time offset

// Function to connect to Wi-Fi
void connectToWiFi() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to Wi-Fi...");
  }
  
  Serial.println("Connected to Wi-Fi");
  
  // Configure and get time from NTP server
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  Serial.println("NTP time configured");
}

// Function to get the current time as ISO 8601 string
String getFormattedTime() {
  struct tm timeinfo;
  char timeStringBuff[30];
  
  if(!getLocalTime(&timeinfo)) {
    Serial.println("Failed to obtain time");
    return "2025-03-07T00:00:00"; // Fallback timestamp
  }
  
  // Format: YYYY-MM-DDThh:mm:ss
  strftime(timeStringBuff, sizeof(timeStringBuff), "%Y-%m-%dT%H:%M:%S", &timeinfo);
  return String(timeStringBuff);
}

// Function to read temperature and humidity from DHT sensor
void readDHTSensor(float &temperature, float &humidity) {
  // Reading temperature or humidity takes about 250 milliseconds
  humidity = dht.readHumidity();
  // Read temperature as Celsius (the default)
  temperature = dht.readTemperature();

  // Check if any reads failed and exit early (to try again)
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor!");
    temperature = 0.0;
    humidity = 0.0;
    return;
  }

  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.print(" °C, Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");
}

// Function to send data to FastAPI server
void sendData() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected. Reconnecting...");
    WiFi.begin(ssid, password);
    delay(5000);
    return;
  }

  float temperature, humidity;
  readDHTSensor(temperature, humidity);

  HTTPClient http;

  // Start HTTP connection to FastAPI server
  http.begin(serverUrl);

  // Set content-type header to application/json
  http.addHeader("Content-Type", "application/json");

  // Create JSON object to hold sensor data
  DynamicJsonDocument doc(1024);
  
  // Get current time from NTP
  doc["timestamp"] = getFormattedTime();
  
  // Use actual temperature and humidity values from the sensor
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  
  // Keep the other values fixed as in your original code
  doc["water_level"] = 69;
  doc["ph_level"] = 6.9;
  doc["tds_level"] = 69;
  doc["dissolved_oxygen"] = 69;

  // Serialize the JSON object into a string
  String jsonData;
  serializeJson(doc, jsonData);

  // Send POST request with JSON data
  int httpResponseCode = http.POST(jsonData);

  // Check response code
  if (httpResponseCode == 200) {
    Serial.println("✅ Data sent successfully!");
    Serial.println("Current timestamp: " + getFormattedTime());
  } else {
    Serial.printf("❌ Error sending data: %d\n", httpResponseCode);
  }

  // End HTTP connection
  http.end();
}

void setup() {
  Serial.begin(115200);
  dht.begin();      // Initialize DHT sensor
  connectToWiFi();  // Connect to Wi-Fi and setup NTP
}

void loop() {
  sendData();      // Read sensor data and send to FastAPI
  delay(5000);     // Wait 5 seconds before sending the next data
}
