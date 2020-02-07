from ThreadDeviceDriverWrapper import ThreadDeviceDriverWrapper
from time import sleep

def my_listener_callback(gesture_id, x, y, z):
    print("the gesture i received is " + str(gesture_id) + " with x,y,z of" + str(x) + "," + str(y) + "," + str(z))

wrapper = ThreadDeviceDriverWrapper()
print("Initialized")
try:
    wrapper.connect()
    print("connected")
except Exception as e:
    print(e)
    print("failed")

print("connected")
# now try to read from named pipe
#wrapper.gesture_listener(my_listener_callback)

print("Calibrated?", wrapper.is_calibrated())

glove_connected = False
while not glove_connected:
    sleep(2)
    glove_connected = wrapper.is_glove_connected()

print("Calibrated?", wrapper.is_calibrated())

#calibration_path = "C:\\Users\\Aaron\\source\\repos\\python-api-device-driver\\testCalibrationFiles"
#calibration_file_one = calibration_path + "\\testtwo.txt"

# This is calibration test with no file
"""
wrapper.start_calibration(10, calibration_file_one)
sleep(12)
print("File should have calibration stuff in it now")
"""

# Calibration test with file
"""
wrapper.set_calibration_with_file(calibration_file_one)
sleep(2)

# check that it is calibrated
print("Calibrated?", wrapper.is_calibrated())
"""

# now listen
wrapper.gesture_listener(my_listener_callback)