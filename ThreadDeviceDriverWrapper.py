from enum import Enum
import socket
from struct import *
import uuid
from Constants import *
from collections import namedtuple
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

    # connect establishes connection with device driver
    def connect(self):
        driver_address = ('localhost', DRIVER_PORT)
        try:
            self.socket.connect(driver_address)
            self.socket_connected = True
        except socket.error:
            raise CouldNotConnectException

        # now establish connection
        try:
            # form connect message
            connect_message = self.__build_connect_message(ConnectCode.HELLO)  # 17 bytes
            if not self.socket.send(connect_message) == LENGTH_OF_CONNECT_MESSAGE:
                raise IOError
        except IOError:
            raise CouldNotConnectException

        # get named pipe value from device driver for listening to gestural information
        try:
            newline_read = False
            data = ""
            format_string = 'c'
            while not newline_read:
                data += self.socket.recv(BUFFER_SIZE)
                index = data.find(b'\n')
                if not index == -1:
                    newline_read = True
                    format_string += str(index - 1) + 's'

            # unpack message
            driver_response = namedtuple('DriverResponse', 'success_code file_path')
            driver_response._make(unpack(format_string, data))
            if driver_response.success_code == 1:
                self.listening_pipe = driver_response.file_path
            else:
                raise CouldNotConnectException
        except socket.error:
            raise CouldNotConnectException

    # calibration_set returns True if calibration has been done/set, False otherwise. Raises CouldNotConnectException
    # on socket failure.
    def calibration_set(self):
        self.__build_and_send_endpoint_request(DriverRequestCode.ASK_IF_CALIBRATED_REQUEST, "")

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
        self.__build_and_send_endpoint_request(DriverRequestCode.CALIBRATION_REQUEST, "")
        time.sleep(delay_time)
        self.__build_and_send_endpoint_request(DriverRequestCode.END_CALIBRATION_REQUEST, "")
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
        self.__build_and_send_endpoint_request(DriverRequestCode.USE_SAVED_CALIBRATION_DATA_REQUEST, file_path)

    # gesture_listener(callback) takes a callback function of the form callback(enum gesture_id, double x, double y,
    # double z) where x, y, z form the movement vector of the hand
    def gesture_listener(self, callback):
        with open(self.listening_pipe) as fifo:
            for line in fifo:
                # line is of format [ gesture code | comma separated strength vector ]
                gesture_values = line.split()  # split on spaces
                gesture_code = GestureCode(gesture_values[0])
                vector = gesture_values.split(',')
                callback(gesture_code, vector[0], vector[1], vector[2])

    def __del__(self):
        self.socket.close()

    ###################
    # Private Methods #
    ###################
    # __build_connect_message(message, id) packs a byte array connect message in the form [ message | id ] where message
    # is a ConnectCode enum value, and id is a 4 byte string identifier for this current program
    # Connect message is 17 bytes
    def __build_connect_message(self, message):
        return pack('c16s', message, self.id.bytes)

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
            message = pack(format_string, request_code, '\n')
        else:
            format_string += str(len(payload)) + 'c'
            message = pack(format_string, request_code, payload, '\n')
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
    BATTERY_LIFE_REQUEST = 1
    CALIBRATION_REQUEST = 2
    END_CALIBRATION_REQUEST = 3
    USE_SAVED_CALIBRATION_DATA_REQUEST = 4
    ASK_IF_CALIBRATED_REQUEST = 5


class ConnectCode(Enum):
    HELLO = 0
    BYE = 1


class CouldNotConnectException(Exception):
    # used for failure to connect to driver
    pass


class BadFileException(Exception):
    # used for bad calibration file
    pass
