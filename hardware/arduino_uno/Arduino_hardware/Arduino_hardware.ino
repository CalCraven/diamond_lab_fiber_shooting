#include <TimerOne.h>

// ---------------------------- Variables -----------------------------

char oldSREG;                 // To hold Status Register while ints disabled
int TOP = 3199;               // 5 kHz PWM frequency
int TOP_min = 799;            // 20 kHz (lower resolution)
int TOP_max = 3199;           // 5 kHz (higher resolution)
int CM = 0;                   // duty cycle = (CM + 1) / (TOP + 1)
float duty_max = .6;          // hard limit on max duty cycle
#define SHUTTERS 2
int pinPWM = 9;               // Arduino pin for laser control. Connected to ATmega Counter 1, output A (OC1A).
int pin_shutter[SHUTTERS] = {12, 11};  // Arduino pins for the shutters (Flip mirror and HDD shutter, respectively).
boolean shutter_toggling[SHUTTERS] = {true, false};  // true: toggling, false: high/low state
unsigned long shutter_starttime[SHUTTERS];  // Time at which shutter opens (in microseconds since Arduino start time)
unsigned long shutter_length[SHUTTERS];     // Duration for shutter open state (in microseconds)
boolean shutter_on[SHUTTERS] = {false, false};

// ------------------ Basics function of the arduino ------------------

void setup()
{
  initialize();
  setTOP(TOP);
  setCM(CM);
}

void loop()
{
  parameter_update(); // Communication function from Arduino_communication.ino
  for (int s = 0; s < SHUTTERS; s++)
    check_shutter(s); 
}

// -------------------------- Laser control------------------------------

// PWM : Pulse Width Modulation
// TOP : Maximum value of the counter before it starts again from BOTTOM
// ICR : Input Capture Register
// OCR : Output Compare Register
// TCCR : Timer Counter Control Register
// CM : Compare Match
// ISR : Interrupt Service Routine

// Description :
// A TTL signal is sent from the Arduino to control emission of the CO2 laser. Laser emits, when
// the TTL level is high.
// This program modify the duty cycle of the pulses and pulses frequency sent from the Arduino.
// In order to do that, we use a Fast PWM mode on Timer/Counter1, which is the only counter
// that allows 16-bit PWM resolution.
// The counter runs from BOTTOM (0) to TOP at the clock frequency, after which it restarts from BOTTOM.
// The PWM frequency is therefore PWM_freq = F_CPU / (TOP + 1)

// Setting PWM frequency and duty cycle:
// Refer to ATmega328P Datasheet, chapter 15.9. We use Waveform Generation Mode number 14 (WGM13:0 = 14).
// In this mode, the counter increments until it matches the TOP value stored in ICR1 register.
// The OC1A register (the TTL output, which is routed to the output pin) is set HIGH at BOTTOM (0)
// and cleared when the counter reaches the value stored in OCR1A.
// The value in OCR1A therefore defines the duty cycle:
// TTL output (OC1A) will be high during (CM + 1) clock cycles, while the PWM period is (TOP + 1) clock cycles.
// Duty cycle will be PWM_duty = (CM + 1) / (TOP + 1)
// TOP is stored in the ICR1 register.
// CM is stored in the OCR1A register.

// Communication from Python to Arduino:
// See arduino_hardware.py file and Arduino_communication.ino files
// First 2 bytes are command + option, rest of string is a value.

void initialize() {
  // Set OC1A to output mode. Alternatively set bit DDB1 to on as follows: DDRB |= _BV(PORTB1);
  pinMode(pinPWM, OUTPUT);           // Arduino pin 9 (= ATmega pin 15, PB1): PWM output
  for (int s = 0; s < SHUTTERS; s++)
    pinMode(pin_shutter[s], OUTPUT); // pin 11 : HDD shutter, pin 12 : flip mirror
  // Set Fast PWM mode on Timer/Counter1, non-inverting output.
  // Refer to ATmega328P Datacheet, chapter 15.11, register TCCR1.
  TCCR1A = _BV(WGM11);               // Fast PWM with ICR1 as TOP
  TCCR1B = _BV(WGM12) | _BV(WGM13);  // Fast PWM with ICR1 as TOP
  TCCR1A |= _BV(COM1A1);             // Set non-inverting Fast PWM mode
  TCCR1B |= _BV(CS10);               // No prescaling, i.e., use Arduino Uno's 16 MHz clock (F_CPU)
  Serial.begin(115200);              // Connect to the serial port
}

// Raw set TOP
void setTOP_raw(int top) {
  oldSREG = SREG;
  cli();            // Disable interrupts for 16 bit register access
  ICR1 = top;
  SREG = oldSREG;   // Restore interrupt settings
}

// Raw set CM
void setCM_raw(int cm) {
  oldSREG = SREG;
  cli();            // Disable interrupts for 16 bit register access
  OCR1A = cm;
  SREG = oldSREG;   // Restore interrupt setting
}

// Constrained set TOP. We also need to change CM to keep the duty cycle unchanged.
void setTOP(int top) {
  top = constrain(top, TOP_min, TOP_max);
  float duty_cycle = float(CM + 1)/(TOP + 1)
  int CM_new = (top + 1) * duty_cycle - 1;
  TOP = top;
  setCM(0);        // make sure duty cycle is changed as well
  setTOP_raw(top);
  setCM(CM_new);
}

// Constrained set CM
void setCM(int cm) {
  cm = constrain(cm, 0, int(duty_max * TOP));
  CM = cm;
  setCM_raw(cm);
}

// -------------------------- Shutters control------------------------------

// Pins 11 and 12 control shutters

// This function makes sure the shutter is open for the required duration of time.
void check_shutter(int s) {
  if (shutter_on[s]) {
    if (micros() - shutter_starttime[s] >= shutter_length[s]) {
      if (shutter_toggling[s]) { // For toggling shutter, send a TTL pulse of 10 ms
        digitalWrite(pin_shutter[s], HIGH);
        delay(10);
        digitalWrite(pin_shutter[s], LOW);
      }
      else {  // For non-toggling shutter, set the voltage to LOW
        digitalWrite(pin_shutter[s], LOW);
      }
      shutter_on[s] = false;
    }
  }
}

void open_shutter(int s, long pulselen) {
  open_shutter_micro(s, pulselen * 1000);
}

void open_shutter_micro(int s, long pulselen) {
  if (!shutter_on[s]) {
    shutter_starttime[s] = micros();
    shutter_length[s] = pulselen;
    if (shutter_toggling[s]) { // For toggling shutter, send a TTL pulse of 10 ms
      digitalWrite(pin_shutter[s], HIGH);
      delay(10);
      digitalWrite(pin_shutter[s], LOW);
    }
    else {  // For non-toggling shutter, set the voltage to HIGH
      digitalWrite(pin_shutter[s], HIGH);
    }
    shutter_on[s] = true;
  }
}

void toggle_shutter(int s) {
  if (shutter_toggling[s]) {  // For toggling shutter, send a TTL pulse
    digitalWrite(pin_shutter[s], HIGH);
    delay(10);
    digitalWrite(pin_shutter[s], LOW);
  }
  else {  // For non-toggling shutter, reverse the output voltage
    digitalWrite(pin_shutter[s], !digitalRead(pin_shutter[s]));
  }
}
