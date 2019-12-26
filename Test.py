from ThreadDeviceDriverWrapper import ThreadDeviceDriverWrapper

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
wrapper.gesture_listener(my_listener_callback)