from enum import Enum, IntEnum
import socket
from struct import *
import uuid
from Constants import *
import win32pipe, win32file, pywintypes
import time
import threading


class ThreadDeviceDriverWrapper:

    ##################
    # Public Methods #
    ##################
    def __init__(self):
        # constructor
        self.listening_pipe = ""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5) # sets timeout of 5 seconds
        self.id = uuid.uuid1()
        self.socket_connected = False
        print("Initialized pt 0.1")

    # connect establishes connection with device driver
    def connect(self):
        print("trying to connect")
        driver_address = ('localhost', DRIVER_PORT)
        try:
            self.socket.connect(driver_address)
            print("here")
            self.socket_connected = True
        except socket.error:
            print("Error connecting")
            raise CouldNotConnectException

        print("socket connect done")

        # now establish connection
        try:
            # form connect message
            connect_message = self.__build_connect_message(ConnectCode.HELLO.value)  # 18 bytes
            if not self.socket.send(connect_message) == LENGTH_OF_CONNECT_MESSAGE:
                raise IOError
        except IOError:
            print("Could not send hello message")
            raise CouldNotConnectException

        print("connect message sent")

        # get named pipe value from device driver for listening to gestural information
        try:
            newline_read = False
            data = b''
            format_string = 'c'
            while not newline_read:
                data += self.socket.recv(BUFFER_SIZE)
                index = data.find(b'\n')
                if not index == -1:
                    newline_read = True
                    format_string += str(index - 1) + 's'
            # check if we got error status code
            if data[0] == 1:
                raise CouldNotConnectException
            # get file path
            self.listening_pipe = (data[1:index]).decode('utf-8')
            print("listening pipe is " + self.listening_pipe)
        except socket.error:
            print("Error receiving data from socket")
            raise CouldNotConnectException

    # calibration_set returns True if calibration has been done/set, False otherwise. Raises CouldNotConnectException
    # on socket failure.
    def calibration_set(self):
        self.__build_and_send_endpoint_request(DriverRequestCode.ASK_IF_CALIBRATED_REQUEST.value, "")

        # read from socket to get value back from driver
        payload = self.__receive_endpoint_request()
        if "yes" in payload:
            return True
        return False

    # start_calibration(delay_time, file_path) takes an integer parameter which tells the device driver how long to
    # wait for the user to perform the calibration motion. It also takes in the string parameter file_path which is
    # used to store the calibration information. Raises CouldNotConnectException on Socket error.
    def start_calibration(self, delay_time, file_path):
        self.__build_and_send_endpoint_request(DriverRequestCode.CALIBRATION_REQUEST.value, "")
        # make sure it went through
        self.__receive_endpoint_request()

        # start background thread to handle the waiting and file save
        calibration_background_task = threading.Thread(target=self.__wait_and_save_calibration,
                                                       args=(delay_time, file_path))
        calibration_background_task.daemon = True
        calibration_background_task.start()

    # set_calibration_with_file(file_path) calibrates the device driver with the results in the file. Raises
    # BadFileException if the file is not in the correct format. Raises CouldNotConnectException on socket failure.
    def set_calibration_with_file(self, file_path):
        self.__build_and_send_endpoint_request(DriverRequestCode.USE_SAVED_CALIBRATION_DATA_REQUEST.value, file_path)
        try:
            payload = self.__receive_endpoint_request()
        except CouldNotConnectException:
            raise BadFileException
        print("SUCCESS returned on set calibration with file")

    # is_glove_connected() returns True if glove is connected to the driver, False otherwise.
    # Raises CouldNotConnectException on socket failure.
    def is_glove_connected(self):
        self.__build_and_send_endpoint_request(DriverRequestCode.IS_GLOVE_CONNECTED_REQUEST.value, "")
        payload = self.__receive_endpoint_request()
        if "yes" in payload:
            return True
        else:
            return False

    # is_calibrated() returns True if glove is calibrated, False otherwise. Raises CouldNotConnectException on
    # socket failure.
    def is_calibrated(self):
        self.__build_and_send_endpoint_request(DriverRequestCode.ASK_IF_CALIBRATED_REQUEST.value, "")
        try:
            payload = self.__receive_endpoint_request()
        except CouldNotConnectException:
            return False
        if "yes" in payload:
            return True
        else:
            return False

    # gesture_listener(callback) takes a callback function of the form callback(enum gesture_id, double x, double y,
    # double z) where x, y, z form the movement vector of the hand
    def gesture_listener(self, callback):
        handle = win32file.CreateFile(
            self.listening_pipe,
            win32file.GENERIC_READ,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        while True:
            resp = win32file.ReadFile(handle, 64 * 1024)
            if resp[0] == 0:
                byte_resp = resp[1]
                str_resp = byte_resp.decode('utf-16')
                gesture_values = str_resp.split()
                try:
                    gesture_code = GestureCode(int(gesture_values[0]))
                    vector = gesture_values[1].split(',')
                    values = [0, 0, 0]
                    for i in range(3):
                        elt = vector[i]
                        elt.split(':')
                        if elt[0] == 1:
                            values[i] = -1 * int(elt[1])
                        else:
                            values[i] = int(elt[1])

                    callback(gesture_code, values[0], values[1], values[2])
                except ValueError:
                    print("Not a valid gesture code")

    # TODO: see todos below
    def start_gesture_recording(self):
        self.__build_and_send_endpoint_request(DriverRequestCode.START_RECORDING.value, "")
        try:
            payload = self.__receive_endpoint_request()
        except CouldNotConnectException:
            return False
        print("SUCCESS STARTING")
        return True

    # TODO: see todos below
    def end_gesture_recording(self, file_path):
        self.__build_and_send_endpoint_request(DriverRequestCode.END_RECORDING.value, file_path)
        try:
            payload = self.__receive_endpoint_request()
        except CouldNotConnectException:
            return False
        print("SUCCESS ENDING")
        return True

    def __del__(self):
        self.socket.close()

    ###################
    # Private Methods #
    ###################
    # __build_connect_message(message) packs a byte array connect message in the form [ message | id ] where message
    # is a ConnectCode enum value, and id is a 16 byte string identifier for this current program
    # Connect message is 18 bytes
    def __build_connect_message(self, message):
        m = bytes([message])
        return pack('c16sc', m, bytes(str(self.id), 'utf-8'), b'\n')

    # __build_and_send_endpoint_request(request_code, payload) packs a byte array for an endpoint request message in the
    # form of [ request_code | payload ] where payload is a maximum 64 byte string. This byte array is the sent over the
    # existing socket to the device driver. Raises CouldNotConnectException on socket error.
    def __build_and_send_endpoint_request(self, request_code, payload):
        if not self.socket_connected:
            raise CouldNotConnectException

        format_string = 'c'
        if payload == "":
            format_string += 'c'
            message = pack(format_string, bytes(chr(request_code), encoding='utf-8'), b'\n')
        else:
            format_string += str(len(payload)) + 's' + 'c'
            message = pack(format_string, bytes(chr(request_code), encoding='utf-8'), bytes(payload, encoding='utf-8'),
                           b'\n')

        # send message
        print("Message is", message)
        try:
            if not self.socket.send(message) == len(message):
                raise IOError
        except IOError or socket.error:
            raise CouldNotConnectException

    # __receive_endpoint_request() listens to socket until we receive the end of a payload, and then the payload is
    # returned. Raises CouldNotConnectException on socket error.
    def __receive_endpoint_request(self):
        if not self.socket_connected:
            raise CouldNotConnectException

        # listen until we get '/n'
        try:
            newline_read = False
            data = b''
            while not newline_read:
                data += self.socket.recv(BUFFER_SIZE)
                index = data.find(b'\n')
                if not index == -1:
                    newline_read = True
        except socket.error or Exception:
            print("Error receiving data from socket")
            raise CouldNotConnectException

        # make sure success was returned, and then return the payload
        if data[0] == 1:
            raise CouldNotConnectException
        return (data[1:index]).decode('utf-8')

    # __wait_and_save_calibration waits for delay_time seconds and then requests the device driver to end the
    # calibration request. It then saves the calibration result to the file specified by the string file_path. Does
    # not raise any exception.
    def __wait_and_save_calibration(self, delay_time, file_path):
        time.sleep(delay_time)
        print("Done waiting, now going to retrieve info and try and save it")
        # create file to save with and then close it
        with open(file_path, 'w+') as newfile:
            pass

        # tell the driver to end calibration
        try:
            self.__build_and_send_endpoint_request(DriverRequestCode.END_CALIBRATION_REQUEST.value, "")
        except CouldNotConnectException:
            # catch all exceptions and create an empty file to show the calibration was not successful
            return

        # read result from end calibration request
        payload = " "
        try:
            # since response includes multiple new lines - we dont use receive_endpoint_request helper function
            if not self.socket_connected:
                raise CouldNotConnectException

            try:
                newlines_read = 0
                data = b''
                while not newlines_read >= 2:
                    data += self.socket.recv(BUFFER_SIZE)
                    newlines_read = data.count(b'\n')
            except socket.error:
                print("Error receiving data from socket")
                raise CouldNotConnectException

            # make sure success was returned, and then return the payload
            if data[0] == 1:
                raise CouldNotConnectException
            print("Data received from end calibration", data)
            payload = (data[1:]).decode('utf-8')
        except CouldNotConnectException or Exception:
            return

        # save into file
        with open(file_path, 'w+') as calibration_file:
            calibration_file.write(payload)
            calibration_file.write('\n')


class GestureCode(Enum):
    ZOOM_IN = 1
    ZOOM_OUT = 2
    ROTATE = 3
    PAN = 4


class DriverRequestCode(IntEnum):
    BATTERY_LIFE_REQUEST = 3
    CALIBRATION_REQUEST = 4
    END_CALIBRATION_REQUEST = 5
    USE_SAVED_CALIBRATION_DATA_REQUEST = 6
    ASK_IF_CALIBRATED_REQUEST = 7
    IS_GLOVE_CONNECTED_REQUEST = 8
    START_RECORDING = 9 #TODO: this is a temporary endpoint for recording gestures for the purpose of gesture recognition
    END_RECORDING = 11 #TODO: ^


class ConnectCode(Enum):
    HELLO = 1
    BYE = 2


class CouldNotConnectException(Exception):
    # used for failure to connect to driver
    pass


class BadFileException(Exception):
    # used for bad calibration file
    pass
