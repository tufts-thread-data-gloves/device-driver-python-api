# Thread Data Gloves Device Driver Wrapper for Python
The library ThreadDeviceDriverWrapper is a python library that functions as an API for using the thread
data gloves.

# Usage
```python
def my_listener_callback(gesture_id, x, y, z):
    print("the gesture i received is " + str(gesture_id) + " with x,y,z of" + str(x) + "," + str(y) + "," + str(z))

wrapper = ThreadDeviceDriverWrapper()

try:
    wrapper.connect()
    print("connected")
except Exception as e:
    print(e)
    exit(1)

print("connected")
# now try to read from named pipe
wrapper.gesture_listener(my_listener_callback)
```
Once we are past wrapper.connect() we can also use the device driver wrapper to send requests to the device driver, as
highlighted below. This snippet demonstrates how to use the device driver wrapper to listen to gestures made with the
attached glove.

# API calls to talk with device driver
```python
wrapper.calibration_set() # returns true if the glove has been calibrated
wrapper.start_calibration(delay_time, file_path) # starts the calibration process - allows for the calibration to go 
                                                # for delay_time seconds, and stores the results in the string file_path
                                                # This returns before the calibration is stored, the waiting and storing
                                                # happens in the background.
wrapper.set_calibration_with_file(file_path) # sets the calibration with a saved file given by the string file_path
wrapper.is_glove_connected() # returns true if glove is connected to driver over bluetooth
```
