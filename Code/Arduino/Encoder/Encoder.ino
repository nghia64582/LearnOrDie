#define CLK 14   // D5
#define DT 12    // D6
#define SW 13    // D7

volatile int encoderValue = 0;
int lastClk = HIGH;

void IRAM_ATTR handleEncoder() {
  int clkState = digitalRead(CLK);
  if (clkState != lastClk) {
    if (digitalRead(DT) != clkState) {
      encoderValue++;
    } else {
      encoderValue--;
    }
  }
  lastClk = clkState;
}

void setup() {
  Serial.begin(115200);

  pinMode(CLK, INPUT_PULLUP);
  pinMode(DT, INPUT_PULLUP);
  pinMode(SW, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(CLK), handleEncoder, CHANGE);
}

void loop() {
  static int last = 0;

  // đọc nút nhấn
  if (digitalRead(SW) == LOW) {
    Serial.println("Button pressed!");
    delay(200); // debounce
  }

  // in giá trị
  if (encoderValue != last) {
    Serial.print("Encoder = ");
    Serial.println(encoderValue);
    last = encoderValue;
  }
}
