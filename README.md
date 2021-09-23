## Qudi branch used for fiber shooting experiment ##

### Installation ###

Additional packages have to be installed, which are absent in standard Qudi environment. Arduino hardware module needs `pyserial`, and camera module needs `py-opencv`.

The installation procedure is the following:

- Start `Anaconda Prompt` as Administrator
- execute the following:
```bash
conda activate qudi
conda install py-opencv
conda install pyserial
```
- If needed, install drivers for Arduino Uno (controls the shutter). In Windows Device Manager, adjust the speed of the Arduino COM port to 115200 bps
- Set the proper COM port number in `arduino_uno_hardware.py`
- Adjust the resource name for the USB power meter in `Thorlabs_TLPM_hardware.py`
- Make sure Thorlab's driver for power meter (usually, `c:\Program Files\IVI Foundation\VISA\Win64\Bin\TLPM_64.dll`) is in system PATH
