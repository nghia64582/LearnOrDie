#define IN1 14  // D5
#define IN2 12  // D6

void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  digitalWrite(IN2, LOW);  // chọn hướng quay (IN1 PWM)
}

void loop() {
  // Tăng tốc từ 0 -> 1023
  for (int speed = 0; speed <= 1023; speed += 100) {
    analogWrite(IN1, speed);

    // ---- LOG SPEED ----
    float duty = speed / 1023.0 * 100.0;
    Serial.print("PWM: ");
    Serial.print(speed);
    Serial.print(" / 1023  |  Duty cycle: ");
    Serial.print(duty, 1);
    Serial.println("%");

    delay(500); // chậm cho bạn đo điện áp
  }

  delay(1000);

  // Giảm tốc từ 1023 -> 0
  for (int speed = 1023; speed >= 0; speed -= 100) {
    analogWrite(IN1, speed);

    // ---- LOG SPEED ----
    float duty = speed / 1023.0 * 100.0;
    Serial.print("PWM: ");
    Serial.print(speed);
    Serial.print(" / 1023  |  Duty cycle: ");
    Serial.print(duty, 1);
    Serial.println("%");

    delay(500);
  }

  delay(1000);
}
