void setup() {
  // Initialize the serial communication
  Serial.begin(9600);
  // Initialize the LED pin as an output
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  // Blink the LED
  digitalWrite(LED_BUILTIN, HIGH); // Turn the LED on (HIGH is the voltage level)
  delay(1000);                     // Wait for a second
  digitalWrite(LED_BUILTIN, LOW);  // Turn the LED off by making the voltage LOW
  delay(1000);                     // Wait for a second
}