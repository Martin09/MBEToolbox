# -*- coding: utf-8 -*-
"""
Created on Wed Sep 28 10:49:07 2016

@author: Martin Friedl
"""

import serial
from time import sleep

class SbValve():
    def __init__(self,COM):
        try:
            # configure the serial connections
            self.ser = serial.Serial(
                port='//./COM{:d}'.format(COM),
                baudrate=9600,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.SEVENBITS,
                timeout=50
            )
            self.ser.isOpen()  # Open serial connection
            self.working = True
        except:
            self.ser = None
            self.working = False

    def __del__(self):
         #Correctly close COM port when object is deleted
        self.ser.close()

    def getPV(self):
        '''
        Returns the present value (PV) of the Sb valve from 0 (closed) to 300 (fully open)
        If it wasn't able to get the PV, returns None
        '''
        if not self.working:
            return None
        #Remove any remaining characters that could be in the input/output buffers
        self.ser.flushInput()
        self.ser.flushOutput()
        cmd_getPV = "\x040011PV\x05" #Standard format taken from "BiSynic-Manual.pdf"
        self.ser.write(cmd_getPV) #Send command
        sleep(0.1)
        response = self.readBuffer() #Read the response
        try: #Try to parse the reply
            PV = float(response.split('PV')[1].split('\x03')[0])
            PV = PV/300.0*100.0 #Convert to a percentage
        except: #If it fails return none
            PV = None
        return PV
    
    def doXOR(self, inputstring):
        """
        Computes the checksum required when setting the PV value of the eurotherm
        inputstring: the specific string on which to perform the bitwise XOR
        returns: checksum character
        """
        checksum = 0
        for i,c in enumerate(inputstring): #Perform the bitwise XOR
            checksum ^= ord(c)     
        return chr(checksum)
        
    def setPV(self, percentage):
        """
        Sets the PV of the eurotherm to the provided value
        value: % value that you want to set for the valve opening (0 to 100)
        returns: True if it was successful, False otherwise
        """
        if not self.working:
            return False
        #Remove any remaining characters that could be in the input/output buffers        
        self.ser.flushInput()
        self.ser.flushOutput()    
        if percentage > 100 or percentage < 0:
            return False        
        #TODO: Check if max is actually 300 or pi*100=314
        maxOpening = 300
        value = maxOpening * percentage / 100.0
        #Inject value into the command string
        cmd_setPV = "\x04\x30\x30\x31\x31\x02SL{:.1f}\x03".format(value)
        #Generate the checksum from last part of command string
        checksum  = self.doXOR(cmd_setPV.split('\x02')[1])
        #Add checksum to end of command
        cmd_setPV += str(checksum)
        
        self.ser.write(cmd_setPV) #Send command
        sleep(0.1)    
        response = self.readBuffer() #Get the response
        if len(response)>1: response = response[-1] #In case multiple characters are in buffer take last one
        if response == '\x06': return True #Successful write
        else: return False #Unsucessful write
        
    def readBuffer(self):
        """
        Reads all of the characters waiting in the serial communication buffer and returns them as a single string
        """
        if not self.working:
            return None
        out = ''
        #While there are characters in the buffer, read them
        while self.ser.inWaiting() > 0:
            out += self.ser.read(1)
        return out

#For testing:
if __name__ == '__main__':
    valve = SbValve(COM=3)
    print valve.getPV()