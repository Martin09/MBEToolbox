# -*- coding: utf-8 -*-
"""
Created on Wed Aug 10 08:31:57 2011

@author: rueffer
"""

import re, socket, threading
from time import sleep
from struct import unpack, pack
from string import atoi
from calendar import timegm
from datetime import datetime
from collections import OrderedDict
import numpy as np
from numpy import greater, bool8, uint8, uint32, float32, float64, ndarray, array, take, frombuffer, empty, hstack, \
    dtype
from  PyQt4 import QtGui, QtCore


class StayAliveThread(threading.Thread):
    def stop(self):
        self.__stop = True

    def run(self):
        self.__stop = False
        self.connection = self._Thread__kwargs["connection"]
        self.semaphore = self._Thread__kwargs["semaphore"]
        while not self.__stop:
            for i in xrange(150):
                sleep(0.1)
                if self.__stop:
                    #                    print "stop"
                    break
            if not self.__stop and not self.semaphore.locked():
                try:
                    if not self.connection.send_command("OK") == "OK":
                        raise RuntimeError("Unexpected answer from server during stayalive signal")
                except Exception, err:
                    print "Error: " + str(err)


class ServerConnection:
    def __init__(self, tcp, port, password, name="test", bufferSize=1024):
        self.tcp = tcp
        if isinstance(port, int):
            self.port = port
        elif isinstance(port, str):
            self.port = atoi(port)
        else:
            raise TypeError("integer or string required for port")
        self.password = password
        self.buffersize = bufferSize
        self.byteInterpreter = None
        self.Chamber = None
        self.name = name
        self.__stayAlive = None
        self.__semaphore = threading.Lock()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.connect((self.tcp, self.port))
        self.__connect()

    def __del__(self):
        # does not work in this implementation
        self.__stayAlive.stop()
        self.__socket.close()

    def close(self):
        self.__stayAlive.stop()
        self.__socket.close()

    def __connect(self):
        self.__send(self.password + "Client:" + self.name)
        self.__receiveConfig()
        self.Chamber = self.send_command("get this.chamber")
        self.__stayAlive = StayAliveThread(kwargs={"connection": self, "semaphore": self.__semaphore})
        self.__stayAlive.start()

    def __receiveConfig(self):
        answer = self.send_command("get this.config")
        self.ByteInterpreter = ByteInterpreter(answer)

    def __send(self, byte):
        lengthInfo = pack("!l", len(byte))
        self.__socket.send(lengthInfo + byte)

    #        print "sent "+str(len(byte)) + " bytes"

    def __receive(self, allowElse=True):
        a = self.__socket.recv(4)
        lengthInfo = unpack("!l", a)[0]
        #        print "received "+str(lengthInfo) + " bytes"
        if lengthInfo:
            answer = self.__socket.recv(lengthInfo)
            if answer == "OK":
                return answer
            elif answer == "WAIT":
                answer = self.__receive(False)
                return answer
            elif answer == "PWD":
                raise RuntimeError("Error 9201: Password rejected")
            elif allowElse:
                raise RuntimeError(answer)
            return answer
        else:
            return ""

    def send_command(self, cmd):
        self.__semaphore.acquire()
        self.__send(self.password + cmd)
        try:
            answer = self.__receive()
            self.__semaphore.release()
        except Exception, exep:
            self.__semaphore.release()
            raise RuntimeError(exep)

        return answer

    def getStatus(self):
        strData = self.send_command("get this.StatusInBytes")
        return self.ByteInterpreter.convert(strData)

    def getSections(self):
        return self.ByteInterpreter.byteConfig.sections

    def getValue(self, name):
        return self.getStatus()[name][0]


class helping:
    def __init__(self):
        self.greater = greater
        self.bool8 = bool8
        self.uint8 = uint8
        self.uint32 = uint32
        self.float32 = float32
        self.float64 = float64
        self.ndarray = ndarray
        self.array = array
        self.take = take
        self.frombuffer = frombuffer
        self.empty = empty
        self.hstack = hstack
        self.dtype = dtype


np = helping()


class ByteInterpreter:
    def __init__(self, astring):
        self.byteConfig = ByteConfig(astring, string=True)
        self.__timeoffset = timegm((1904, 1, 1, 0, 0, 0))

    def get_sections(self):
        return self.byteConfig.sections

    def iToBin(self, value, bit=32):
        l = []
        for i in xrange(bit):
            l.append(np.greater(value & 2 ** i, 0))
        return l

    def iToEnum(self, value, bit=2, no=16):
        l = []
        for i in xrange(no):
            l.append(value & (2 * bit) ** (i + 1))
        return l

    def iToStr(self, value, no=2):
        strings = ["Undefi", "Closed", "Open", "Undefi"]
        if not isinstance(value, np.ndarray):
            value = np.array([value])
        l = []
        for i in range(0, no * 2, 2):
            l.append(np.take(strings, (np.greater((value & 2 ** i), 0).astype(np.uint8) + \
                                       2 * np.greater((value & 2 ** (i + 1)), 0).astype(np.uint8))))
        return l

    def get_names(self):
        return self.data.dtype.names

    def get_data(self, row, column):
        name = self.data.dtype.names[column + 1]
        return (self.data[name][row])

    def get_time(self, row):
        timestamp = datetime.fromtimestamp(self.data["Time"][row])
        return "{0:0=2}:{1:0=2}:{2:0=2}.{3:0=3}".format(timestamp.hour, timestamp.minute, \
                                                        timestamp.second, timestamp.microsecond / 1000)

    #        return "".format(timestamp.hour)+":"+str(timestamp.minute)+":"+ \
    #                    str(timestamp.second)+":"+str(timestamp.microsecond/1000)


    def convert(self, strData):
        """ Read all data after current file position
        """
        rawData = np.frombuffer(strData, self.byteConfig.dtypefile)
        self.temp = rawData
        temp = np.empty(rawData.shape, dtype=self.byteConfig.dtype)

        for i in self.byteConfig.translate["Copy"]:
            if i == "Time":
                temp[i] = rawData[i] + self.__timeoffset
            else:
                temp[i] = rawData[i]
        for i in self.byteConfig.translate["Modify"]:
            if i == "GateValves":
                strings = self.iToStr(rawData[i], no=len(self.byteConfig.translate["Modify"][i]))
                for n, j in enumerate(self.byteConfig.translate["Modify"][i]):
                    temp[j] = strings[n]
            else:
                bools = self.iToBin(rawData[i], len(self.byteConfig.translate["Modify"][i]))
                for n, j in enumerate(self.byteConfig.translate["Modify"][i]):
                    temp[j] = bools[n]

        return temp


class LogFile:
    def __init__(self, path):
        self.byteConfig = ByteConfig(path, closeFile=False)
        self.file = self.byteConfig.file
        self.data = None
        self.__timeoffset = timegm((1904, 1, 1, 0, 0, 0))
        self.readNew()

    def get_sections(self):
        return self.byteConfig.sections

    def iToBin(self, value, bit=32):
        l = []
        for i in xrange(bit):
            l.append(np.greater(value & 2 ** i, 0))
        return l

    def iToEnum(self, value, bit=2, no=16):
        l = []
        for i in xrange(no):
            l.append(value & (2 * bit) ** (i + 1))
        return l

    def iToStr(self, value, no=2):
        strings = ["Undefi", "Closed", "Open", "Undefi"]
        if not isinstance(value, np.ndarray):
            value = np.array([value])
        l = []
        for i in range(0, no * 2, 2):
            l.append(np.take(strings, (np.greater((value & 2 ** i), 0).astype(np.uint8) + \
                                       2 * np.greater((value & 2 ** (i + 1)), 0).astype(np.uint8))))
        return l

    def get_data(self, row, column):
        name = self.data.dtype.names[column + 1]
        return (self.data[name][row])

    def get_time(self, row):
        timestamp = datetime.fromtimestamp(self.data["Time"][row])
        return "{0:0=2}:{1:0=2}:{2:0=2}.{3:0=3}".format(timestamp.hour, timestamp.minute, \
                                                        timestamp.second, timestamp.microsecond / 1000)

    #        return "".format(timestamp.hour)+":"+str(timestamp.minute)+":"+ \
    #                    str(timestamp.second)+":"+str(timestamp.microsecond/1000)


    def readNew(self):
        """ Read all data after current file position
        """
        strData = self.file.read()
        rawData = np.frombuffer(strData, self.byteConfig.dtypefile)
        self.temp = rawData
        temp = np.empty(rawData.shape, dtype=self.byteConfig.dtype)

        for i in self.byteConfig.translate["Copy"]:
            if i == "Time":
                temp[i] = rawData[i] + self.__timeoffset
            else:
                temp[i] = rawData[i]
        for i in self.byteConfig.translate["Modify"]:
            if i == "GateValves":
                strings = self.iToStr(rawData[i], no=len(self.byteConfig.translate["Modify"][i]))
                for n, j in enumerate(self.byteConfig.translate["Modify"][i]):
                    temp[j] = strings[n]
            else:
                bools = self.iToBin(rawData[i], len(self.byteConfig.translate["Modify"][i]))
                for n, j in enumerate(self.byteConfig.translate["Modify"][i]):
                    temp[j] = bools[n]

        if self.data == None:
            self.data = temp
        else:
            self.data = np.hstack([self.data, temp])
            # self.data = temp


class ByteConfig:
    def __init__(self, arg=None, closeFile=True, string=False):
        """

        :param arg: The filename of the log file that you want to open
        :param closeFile:
        :param string:
        """
        self.header = ""
        self.dtypefile = None
        self.dtype = None
        self.byteCount = 0
        self.file = None
        self.translate = dict()
        self.sections = OrderedDict()
        #        self.subsections = {}
        #        self.cells = []
        if arg == None:  # If not filename was provided
            None
        elif isinstance(arg, str) and not string:
            self.byteCount = 0
            f = open(arg, "rb")
            try:
                temp = f.read(4)
                length, = unpack("!l", temp)
                self.header = f.read(length)
                if closeFile:
                    f.close()
                else:
                    self.file = f
            except IOError:
                self.header = arg
                f.close()
            self.calc_dtype()  # this converts the string to the dtype, translate etc..
        elif string:
            self.header = arg
            self.calc_dtype()
        else:
            raise TypeError("only paths or strings accepted")

    def __findType(self, string):
        if string == "B32":
            return np.uint32
        elif string == "F32":
            return np.float32
        elif string == "F64":
            return np.float64

    def __calcByte(self, string):
        if string == "B32":
            return 4
        elif string == "F32":
            return 4
        elif string == "F64":
            return 8

    def calc_dtype(self):
        if self.header == "":
            raise ValueError("Please give a correct header")

        # print self.header

        headerlist = re.split(r"\r\n", self.header)
        if headerlist[-1] == "":
            headerlist = headerlist[0:-1]
        pattern1 = re.compile(r"([\d]*)x?([\d]*)x?([FB]\d\d)")
        pattern2 = re.compile(r"\((\w+)[\)\[]")
        pattern3 = re.compile(r"\((\w+)[\[\{]")
        pattern4 = re.compile(r"\[(.+)\]")
        pattern5 = re.compile(r"[:]")
        pattern6 = re.compile(r"\{(.+)\}")

        def findType(string):
            if string == "B32":
                return np.uint32
            elif string == "F32":
                return np.float32
            elif string == "F64":
                return np.float64

        def calcByte(string):
            if string == "B32":
                return 4
            elif string == "F32":
                return 4
            elif string == "F64":
                return 8

        l = []
        l2 = dict()
        self.translate = dict([("Copy", dict()), ("Modify", dict())])
        for head in headerlist:
            temp = re.match(pattern1, head).groups()
            if temp[0]:  # Multiple Elements
                n = atoi(temp[0])
                name = re.search(pattern3, head).group(1)
                elements = re.split(pattern5, re.search(pattern4, head).group(1))
                self.sections.update(OrderedDict({name: elements}))
                if len(elements) != n:
                    raise ValueError("Corrupted data")
                if temp[1]:
                    m = atoi(temp[1])
                    parameters = re.split(pattern5, re.search(pattern6, head).group(1))
                    if len(parameters) != m:
                        raise ValueError("Corrupted data")
                    # parameters = ["."+i  for i in parameters]
                    names = [("", "") for i in elements]
                    for p, parameter in enumerate(parameters):
                        for k, element in enumerate(elements):
                            if p == 0 and k == 0:
                                self.sections[name] = OrderedDict({element: [parameter]})
                            elif p == 0:
                                self.sections[name].update(OrderedDict({element: [parameter]}))
                            else:
                                self.sections[name][element].append(parameter)
                            self.byteCount += calcByte(temp[2])
                            l.append((element + "." + parameter, self.__findType(temp[2])))
                else:
                    m = 1
                    parameters = []
                    names = [(name + "(", ")") for i in elements]
                    for element in elements:
                        l.append((element, self.__findType(temp[2])))

                        # This is the old part
                        #                for k,element in enumerate(elements):
                        #                    print element
                        #                    for parameter in parameters:
                        #                        print parameter
                        #                        self.byteCount += calcByte(temp[2])
                        #                        l.append((names[k][0]+parameter[0]+element+parameter[1]+names[k][1],self.__findType(temp[2])))
            else:
                self.byteCount += self.__calcByte(temp[2])
                name = re.search(pattern2, head).group(1)
                if temp[2] == "B32":
                    if name == "GateValves":
                        elements = re.split(pattern5, re.search(pattern4, head).group(1))
                    else:
                        elements = re.split(pattern5, re.search(pattern4, head).group(1))
                    l2.update([(name, elements)])
                    self.sections.update({name: elements})
                l.append((name, self.__findType(temp[2])))

        index = 0
        for i in l2:
            self.translate["Modify"].update([(i, [])])
            for j in l2[i]:
                if j.upper() == "OFF":
                    j = j + str(index)
                    index += 1
                self.translate["Modify"][i].append(i + "." + j)

                #        print self.translate["Modify"]
                #        print l2
                #
        l3 = []
        index = 0
        for i in l:
            if i[0] in l2:
                if i[0] == "GateValves":
                    t = np.dtype("S6")
                else:
                    t = np.bool8
                for j in l2[i[0]]:
                    if j.upper() == "OFF":
                        j = j + str(index)
                        index += 1
                    l3.append((i[0] + "." + j, t))
            else:
                l3.append(i)
                self.translate["Copy"].update([i])
                #
                #        print l3
                #        print self.translate

        self.dtype = np.dtype(l3)
        self.dtypefile = np.dtype(l).newbyteorder(">")

# print self.dtypefile
