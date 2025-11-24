#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// ====== WiFi + MQTT config ======
const char* ssid = "ML";
const char* password = "12345679";
const char* mqtt_server = "broker.hivemq.com";

WiFiClient espClient;
PubSubClient client(espClient);

// ====== Stepper pins ======
int IN1 = D1;  
int IN2 = D2;
int IN3 = D3;
int IN4 = D4;

int stepIndex = 0;

// 28BYJ-48 step sequence
int seq[8][4] = {
  {1,0,0,0},
  {1,1,0,0},
  {0,1,0,0},
  {0,1,1,0},
  {0,0,1,0},
  {0,0,1,1},
  {0,0,0,1},
  {1,0,0,1}
};

// ====== Step one ======
void stepMotor(int dir) {
  stepIndex += dir;
  if (stepIndex > 7) stepIndex = 0;
  if (stepIndex < 0) stepIndex = 7;

  digitalWrite(IN1, seq[stepIndex][0]);
  digitalWrite(IN2, seq[stepIndex][1]);
  digitalWrite(IN3, seq[stepIndex][2]);
  digitalWrite(IN4, seq[stepIndex][3]);

  delay(3);   // tốc độ (ms)
}

// ====== MQTT callback ======
void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (int i = 0; i < length; i++) msg += (char)payload[i];

  int steps = msg.toInt();   // số bước
  int dir = (steps >= 0) ? 1 : -1;
  steps = abs(steps);

  for (int i = 0; i < steps; i++) {
    stepMotor(dir);
  }
}

// ====== Reconnect MQTT ======
void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP8266Stepper")) {
      client.subscribe("motor/step");
    } else {
      delay(2000);
    }
  }
}

// ====== Setup ======
void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);

  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

// ====== Loop ======
void loop() {
  if (!client.connected()) reconnect();
  client.loop();
}
