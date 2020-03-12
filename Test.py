from ThreadDeviceDriverWrapper import ThreadDeviceDriverWrapper
from time import sleep
import keyboard
import threading

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

is_calibrated = wrapper.is_calibrated()
print("Calibrated?", is_calibrated)

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

# Recording gestures workflow:
# 1. Calibrate
# 2. Make sure we are calibrated
# 3. Create file for the recordings to go in
# 4. Start thread that listens for gestures
# 5. Listen to user input, on space bar start recording, on next space bar, end recording
calibrationFile = "C:\\Users\\Aaron\\source\\repos\\python-api-device-driver\\testCalibrationFiles\\recordingsCalReal.txt"
filename = "C:\\Users\\Aaron\\source\\repos\\python-api-device-driver\\gestureRecordings\\recordingsPan.txt"

is_calibrated = False
if not is_calibrated:
    print("About to start calibration")

    # step 1
    wrapper.start_calibration(10, calibrationFile)

    sleep(12)

    # step 2
    if not wrapper.is_calibrated():
        print("Not calibrated after calibrating")
        exit(1)
    is_calibrated = True

print("We are calibrated, setting up recording file")

# step 3
with open(filename, "w+") as newfile:
    newfile.write("Gesture Recordings \n")


# step 4
#x = threading.Thread(target=wrapper.gesture_listener, args=(my_listener_callback))
#x.start()

print("About to loop for recording")
print("Press space to start, then space to end")
print("This program will tell you when it has been recognized as started and when it has been recognized as ending")

# step 5
while True:
    keyboard.wait('space')
    wrapper.start_gesture_recording()
    print("Gesture recording started")
    keyboard.wait('space')
    wrapper.end_gesture_recording(filename)
    print("Gesture recordin  g ended")


