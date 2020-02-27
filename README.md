## Qudi branch used for fiber shooting experiment ##

### Installation ###

Additional packages have to be installed, which are absent in standard Qudi environment. Arduino hardware module needs `pyserial`, and camera module needs `py-opencv`. Additionally, a package for Thorlabs powermeter has to be installed from `hardware\Powermeter_PM100A\ThorlabsPM100-1.1.2\`.

The installation procedure is the following:

- Start `Anaconda Prompt` as Administrator
- execute the following (substitute `...` with the correct path):
```bash
conda activate qudi
conda install py-opencv
conda install pyserial
cd ...\hardware\Powermeter_PM100A\ThorlabsPM100-1.1.2
python setup.py install
```
- Adjust the COM port number in `arduino_uno_hardware.py`
- Adjust the resource name for the USB port in `power_meter_PM100A_hardware.py`
