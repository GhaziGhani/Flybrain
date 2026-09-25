// FlyBridge: the Arduino side of the fly-brain loop.
//
// This board only senses and acts. It never decides whether something is too close;
// it streams ultrasonic distances to the PC, where the fly connectome decides, and
// sets the LED to whatever the brain answers.
//
// Wiring (Arduino Uno / Nano):
//   HC-SR04 VCC -> 5V, GND -> GND, TRIG -> D9, ECHO -> D10
//   LED anode -> 220 ohm resistor -> D6 (PWM), LED cathode -> GND
//
// Protocol, 115200 baud, one message per line:
//   out: HELLO,FlyBridge,1          on boot and in reply to "?"
//   out: D,<millis>,<cm>            every SAMPLE_MS; -1.0 = no echo (nothing in range)
//   in:  C,<led 0|1>,<pwm 0-255>    the brain's decision; pwm = how strongly it wants to avoid
//
// Failsafe: with no command for FAILSAFE_MS the LED goes off and the onboard LED blinks,
// so a stopped or crashed brain never leaves an actuator running.

const uint8_t TRIG_PIN = 9;
const uint8_t ECHO_PIN = 10;
const uint8_t LED_PIN = 6;
const uint8_t STATUS_PIN = LED_BUILTIN;

const unsigned long SAMPLE_MS = 80;
const unsigned long FAILSAFE_MS = 600;
const unsigned long ECHO_TIMEOUT_US = 25000;
const uint8_t MIN_VISIBLE_PWM = 40;

unsigned long lastSample = 0;
unsigned long lastCommand = 0;
bool haveCommand = false;
char line[24];
uint8_t lineLength = 0;

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long echoUs = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  if (echoUs == 0) return -1.0;
  return echoUs / 58.0;
}

void applyCommand(int led, int pwm) {
  pwm = constrain(pwm, 0, 255);
  analogWrite(LED_PIN, led ? max(pwm, (int)MIN_VISIBLE_PWM) : 0);
  lastCommand = millis();
  haveCommand = true;
}

void handleLine(const char *text) {
  if (text[0] == '?') {
    Serial.println(F("HELLO,FlyBridge,1"));
    return;
  }
  if (text[0] == 'C' && text[1] == ',') {
    int led = 0, pwm = 0;
    if (sscanf(text + 2, "%d,%d", &led, &pwm) == 2) applyCommand(led, pwm);
  }
}

void readCommands() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n') {
      line[lineLength] = '\0';
      handleLine(line);
      lineLength = 0;
    } else if (c != '\r') {
      if (lineLength < sizeof(line) - 1) line[lineLength++] = c;
      else lineLength = 0;
    }
  }
}

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(STATUS_PIN, OUTPUT);
  analogWrite(LED_PIN, 0);
  Serial.begin(115200);
  Serial.println(F("HELLO,FlyBridge,1"));
}

void loop() {
  readCommands();

  unsigned long now = millis();
  if (now - lastSample >= SAMPLE_MS) {
    lastSample = now;
    float cm = readDistanceCm();
    Serial.print(F("D,"));
    Serial.print(now);
    Serial.print(',');
    Serial.println(cm, 1);
  }

  bool brainSilent = !haveCommand || (now - lastCommand > FAILSAFE_MS);
  if (brainSilent) {
    analogWrite(LED_PIN, 0);
    digitalWrite(STATUS_PIN, (now / 250) % 2);
  } else {
    digitalWrite(STATUS_PIN, LOW);
  }
}
