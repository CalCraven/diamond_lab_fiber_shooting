## Qudi branch used for fiber shooting experiment ##

### Installation ###

Additional packages have to be installed, which are absent in standard Qudi environment. Arduino hardware module needs `pyserial`, and camera module needs `py-opencv`.

The installation procedure is the following:

- Start `Anaconda Prompt` as Administrator
- execute the following (substitute `...` with the correct path):
```bash
conda activate qudi
conda install py-opencv
conda install pyserial
```
- Adjust the COM port number in `arduino_uno_hardware.py`
- Adjust the resource name for the USB port in `Thorlabs_TLPM_hardware.py`
