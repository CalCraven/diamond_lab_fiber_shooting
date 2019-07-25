#define SERIAL_TIMEOUT 10 // serial communication timeout in ms

char command[2];

void parameter_update() {
  if (Serial.available() > 0) {
    // First 2 bytes are command + option, rest of string is a value
    Serial.readBytes(command, 2);
    unsigned long val = Serial.parseInt();
    while(Serial.available())
      Serial.read();
    
    switch (command[0]) {
      case 'f':  // set TOP (frequency)
        setTOP(val);
        break;
      
      case 'd':  // set CM (duty cycle)
        setCM(val);
        break;
        
      case 's':  // millisecond pulse
        open_shutter(command[1] - 48, val);
        break;
        
      case 'S':  // microsecond pulse
        open_shutter_micro(command[1] - 48, val);
        break;
        
      case 't':  // toggle shutter
        toggle_shutter(command[1] - 48);
        break;
    }
  }
}

