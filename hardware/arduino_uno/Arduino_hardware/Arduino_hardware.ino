#include <TimerOne.h>

// ---------------------------- Variables -----------------------------

char oldSREG;                 // To hold Status Register while ints disabled
int TOP = 3199;               // 5 kHz PWM frequency
int TOP_min = 799;            // 20 kHz (lower resolution)
int TOP_max = 3199;           // 5 kHz (higher resolution)
int CM = 0;                   // duty cycle (CM + 1) / (TOP + 1)
float duty_max = .4;          // hard limit on max duty cycle
#define SHUTTERS 2
int pinPWM = 9;
int pin_shutter[SHUTTERS] = {12, 11};
boolean shutter_toggling[SHUTTERS] = {true, false};  // true: toggling, false: high/low state
unsigned long shutter_starttime[SHUTTERS];
unsigned long shutter_length[SHUTTERS];
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
  parameter_update();
  for (int s = 0; s < SHUTTERS; s++)
    check_shutter(s); 
}

// -------------------------- Laser control------------------------------

// PWM : Pulse Width Modulation
// TOP : Maximum value of the counter before it starts again from BOTTOM
// ICR : Input Capture Register
// OCR : Output Capture Register
// TCCR : Timer Counter Control Register
// CM : Compare Match
// ISR : Interrupt Service Routine

// Description :
// A sawtooth signal is sent from the arduino. The laser emit light pulses corresponding to the input signal.
// This program modify the duty cycle of the pulses of the sawtooth signal sent from the arduino.
// In order to do that, we use a PWM output.
// The PWM output is a sawtooth counting from BOTTOM (0) to TOP at the clock frequency.
// PWM frequency is therefore PWMfreq = F_CPU / (TOP + 1)

// Setting PWM frequency and duty cycle:
// The OC1A register (which is routed to the output pin) is set at BOTTOM (0) and cleared when the timer reaches CM.
// PWM high time will be PWMhigh = 1/F_CPU * (CM + 1)
// Duty cycle will be PWMduty = PWMhigh * PWMfreq = (CM + 1) / (TOP + 1)
// TOP is stored in the ICR1 register
// CM is stored in the OCR1A register

// Communication from Python to Arduino:
// See arduino_hardware.py file and Arduino_communication.ino files
// First 2 bytes are command + option, rest of string is a value.

void initialize() {
  // Set pins mode
  pinMode(pinPWM, OUTPUT);           // pin 9 : PWM output, alternatively use DDRB |= _BV(PORTB1);
  for (int s = 0; s < SHUTTERS; s++)
    pinMode(pin_shutter[s], OUTPUT); // pin 11 : HDD shutter, pin 12 : flip mirror
  // Set TCCR1 (ATmega328P docs 15.11)
  // Custom ISR Timer Routine
  TCCR1A = _BV(WGM11);               // Fast PWM with ICR1 as TOP
  TCCR1A |= _BV(COM1A1);             // set non-inverting PWM mode
  TCCR1B = _BV(WGM12) | _BV(WGM13);  // Fast PWM with ICR1 as TOP
  TCCR1B |= _BV(CS10);               // Use 16 MHz clock (F_CPU) with no prescaling
  Serial.begin(115200);              // Connect to the serial port
}

// Raw set TOP
void setTOP_raw(int top) {
  oldSREG = SREG;
  cli();            // Disable interrupts for 16 bit register access
  ICR1 = top;
  SREG = oldSREG;   // Restore interrupt setting
}

// Raw set CM
void setCM_raw(int cm) {
  oldSREG = SREG;
  cli();            // Disable interrupts for 16 bit register access
  OCR1A = cm;
  SREG = oldSREG;   // Restore interrupt setting
}

// Constrained set TOP
void setTOP(int top) {
  top = constrain(top, TOP_min, TOP_max);
  int CM_new = (top + 1) * float(CM + 1) / (TOP + 1) - 1;
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

// The pin 11 and 12 controls shutters

void check_shutter(int s) {
  if (shutter_on[s]) {
    if (micros() - shutter_starttime[s] >= shutter_length[s]) {
      if (shutter_toggling[s]) {
        digitalWrite(pin_shutter[s], HIGH);
        delay(10);
        digitalWrite(pin_shutter[s], LOW);
      }
      else {
        digitalWrite(pin_shutter[s], LOW);    // turn the LED off by making the voltage LOW
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
    if (shutter_toggling[s]) {
      digitalWrite(pin_shutter[s], HIGH);
      delay(10);
      digitalWrite(pin_shutter[s], LOW);
    }
    else {
      digitalWrite(pin_shutter[s], HIGH);   // turn the LED on (HIGH is the voltage level)
    }
    shutter_on[s] = true;
  }
}

void toggle_shutter(int s) {
  if (shutter_toggling[s]) {
    digitalWrite(pin_shutter[s], HIGH);
    delay(1);
    digitalWrite(pin_shutter[s], LOW);
  }
  else {
    digitalWrite(pin_shutter[s], !digitalRead(pin_shutter[s]));
  }
}
