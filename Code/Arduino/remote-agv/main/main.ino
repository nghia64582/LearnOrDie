
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Wi-Fi
const char* WIFI_SSID = "ML";
const char* WIFI_PASSWORD = "12345679";

// MQTT broker thử nghiệm
const char* MQTT_HOST = "test.mosquitto.org";
const int MQTT_PORT = 1883;

const char* MQTT_TOPIC = "car/esp32_01/cmd";

// L298N
#define IN1 25
#define IN2 26
#define IN3 27
#define IN4 14
#define ENA 33
#define ENB 32

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

int leftSpeed = 0;
int rightSpeed = 0;

unsigned long lastCommandTime = 0;
const unsigned long COMMAND_TIMEOUT = 5000;

void setMotor(int left, int right) {
  left = constrain(left, -255, 255);
  right = constrain(right, -255, 255);

  digitalWrite(IN1, left > 0 ? HIGH : LOW);
  digitalWrite(IN2, left < 0 ? HIGH : LOW);

  digitalWrite(IN3, right > 0 ? HIGH : LOW);
  digitalWrite(IN4, right < 0 ? HIGH : LOW);

  analogWrite(ENA, abs(left));
  analogWrite(ENB, abs(right));

  leftSpeed = left;
  rightSpeed = right;
}

void stopMotor() {
  setMotor(0, 0);
}

void mqttCallback(char* topic, byte* payload,
                  unsigned int length) {
  StaticJsonDocument<128> doc;

  DeserializationError error =
      deserializeJson(doc, payload, length);

  if (error) {
    Serial.println("Invalid JSON");
    return;
  }

  if (!doc["left"].is<int>() ||
      !doc["right"].is<int>()) {
    Serial.println("Missing left/right");
    return;
  }

  int left = doc["left"].as<int>();
  int right = doc["right"].as<int>();

  left = constrain(left, -255, 255);
  right = constrain(right, -255, 255);

  setMotor(left, right);
  lastCommandTime = millis();

  Serial.printf("Motor left=%d right=%d\n", left, right);
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.println(WiFi.localIP());
}

void connectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("Connecting MQTT...");

    String clientId = "ESP32-Car-";
    clientId += String((uint32_t)ESP.getEfuseMac(), HEX);

    if (mqtt.connect(clientId.c_str())) {
      Serial.println("connected");
      mqtt.subscribe(MQTT_TOPIC);
      Serial.println("Subscribed to command topic");
    } else {
      Serial.printf("failed, state=%d\n", mqtt.state());
      stopMotor();
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);

  stopMotor();

  connectWiFi();

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(256);
  mqtt.setKeepAlive(15);
  mqtt.setSocketTimeout(3);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    stopMotor();
    WiFi.reconnect();
    delay(100);
    return;
  }

  if (!mqtt.connected()) {
    stopMotor();
    connectMQTT();
  }

  mqtt.loop();

  if (millis() - lastCommandTime > COMMAND_TIMEOUT) {
    stopMotor();
  }
}