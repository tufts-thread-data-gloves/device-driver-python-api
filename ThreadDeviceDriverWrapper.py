from enum import Enum
import socket
from struct import *
import uuid
from Constants import *
from collections import namedtuple
import win32pipe, win32file, pywintypes
import time


class ThreadDeviceDriverWrapper:

    ##################
    # Public Methods #
    ##################
    def __init__(self):
        # constructor
        self.listening_pipe = ""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        if self.socket_connected:
            expected_length = 2  # 1 byte for 0/1, 1 byte for newline char
            data = ""
            while not len(data) == expected_length:
                data += self.socket.recv(expected_length - len(data))
            if data[0] == 1:
                return True
            else:
                return False
        else:
            raise CouldNotConnectException

    # start_calibration(delay_time, file_path) takes an integer parameter which tells the device driver how long to
    # wait for the user to perform the calibration motion. It also takes in the string parameter file_path which is
    # used to store the calibration information. This call is blocking for delay_time seconds. Raises
    # CouldNotConnectException on Socket error.
    def start_calibration(self, delay_time, file_path):
        self.__build_and_send_endpoint_request(DriverRequestCode.CALIBRATION_REQUEST.value, "")
        time.sleep(delay_time)
        self.__build_and_send_endpoint_request(DriverRequestCode.END_CALIBRATION_REQUEST.value, "")
        # read calibration results and save into file
        newline_read = False
        data = ""
        while not newline_read:
            data += self.socket.recv(BUFFER_SIZE)
            index = data.find(b'\n')
            if not index == -1:
                newline_read = True

        with open(file_path, 'w+') as calibration_file:
            calibration_file.write(data)
            calibration_file.write('\n')

    # set_calibration_with_file(file_path) calibrates the device driver with the results in the file. Raises exception
    # bad_file if the file is not in the correct format.
    def set_calibration_with_file(self, file_path):
        self.__build_and_send_endpoint_request(DriverRequestCode.USE_SAVED_CALIBRATION_DATA_REQUEST.value, file_path)

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
                    callback(gesture_code, vector[0], vector[1], vector[2])
                except ValueError:
                    print("Not a valid gesture code")

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
        message = ""
        if payload == "":
            # no payload
            format_string += 'c'
            message = pack(format_string, request_code, b'\n')
        else:
            format_string += str(len(payload)) + 'c'
            message = pack(format_string, request_code, payload, b'\n')
        # send message
        try:
            if not self.socket.send(message) == len(message):
                raise IOError
        except IOError or socket.error:
            raise CouldNotConnectException


class GestureCode(Enum):
    ZOOM_IN = 1
    ZOOM_OUT = 2
    ROTATE = 3
    PAN = 4


class DriverRequestCode(Enum):
    BATTERY_LIFE_REQUEST = 3
    CALIBRATION_REQUEST = 4
    END_CALIBRATION_REQUEST = 5
    USE_SAVED_CALIBRATION_DATA_REQUEST = 6
    ASK_IF_CALIBRATED_REQUEST = 7


class ConnectCode(Enum):
    HELLO = 1
    BYE = 2


class CouldNotConnectException(Exception):
    # used for failure to connect to driver
    pass


class BadFileException(Exception):
    # used for bad calibration file
    pass
