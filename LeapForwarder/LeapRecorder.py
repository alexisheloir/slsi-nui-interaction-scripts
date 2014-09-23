#The Sign Language Synthesis and Interaction Research Tools
#    Copyright (C) 2014  Fabrizio Nunnari, Alexis Heloir, DFKI
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


# This script establish a websocket connect with the Leap Motion daemon and forwards all received information through UDP packets.
# This script has been developed because repeadtely creating and closing websocket connection was crashing the leapd process (at least in version 8.0)
# With this script only 1 long-lasting connection is established and all received frames are forwarded, and eventually lost, as UDP packets.
# Tested with python 2.7.2 on Mac.
# Requires the websocket-client library: https://pypi.python.org/pypi/websocket-client/

import socket
import json
import struct
import time

import websocket
import threading

import sys


BINDING_ADDR = ''   # Empty string means: bind to all network interfaces
RECEIVER_PORT = 5678


class LeapReceiver: #(threading.Thread):
    """This thread will be listening to the incoming updated Leap data.
    Remember that Blender is not thread safe: we cannot invoke bpy methods in a separate thread.
    This thread will only collect the Leap Data and store the decoded python dictionary in a local variable.
    """

    # When set to true, the thread receiving cycle will exit.
    terminationRequested = False
    
    # Set to true when the thread exists
    terminated = False

    # when not None, the information is saved to a log file
    current_log_file = None

    # The websocket used to gather data from the Leap application.
    sock = None


    def __init__(self):
        self.use_version_2 = False

    def useVersion2(self, v):
        self.use_version_2 = v
    
    
    def getLeapDict(self):
        return self.leapDict

    def _closeSocks(self):
        if(self.sock != None):
            #self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            self.sock = None

    def terminate(self):
        self.terminationRequested = True
        # Interrupt socket waiting
        self._closeSocks()
        
    def hasTerminated(self):
        return self.terminated

    def startRecording(self):
        self.stopRecording()

        filename = "Leap-LOG-" + time.ctime() + ".log"
        print("Opening new log file "+filename)
        try:
            self.current_log_file = open(filename,'w')
        except OSError as ex:
            msg = "Cannot open logfile '"+filename+"': "+str(ex)
            print(msg)
            self.current_log_file = None



    def stopRecording(self):
        if(self.current_log_file!=None):
            self.current_log_file.flush()
            self.current_log_file.close()
            self.current_log_file = None

    
    def run(self):
        print("LeapReceiver thread starting")

        try:
            # Open socket
            # The socket listening to incoming data.
            addr = "ws://localhost:6437/"
            if(self.use_version_2):
                addr += "v6.json"

            print("Creating web socket to '"+addr+"' ...")
            self.sock = websocket.create_connection(addr)
            print("Created.")

            # Enable gesture detection
            #{enableGestures: true}
            request = json.dumps({ "enableGestures": "true"})
            self.sock.send(request)


            if(self.use_version_2):
                # ws.send(JSON.stringify({focused: true})); // claim focus
                request = json.dumps({ "focused": "true"})
                self.sock.send(request)


            counter = 1
            max_length = 0
        
            while(not self.terminationRequested):

                # gather Leap data
                #print("Receiving")
                msg = self.sock.recv()
                #print(msg.__class__)
                #print("Received : " + str(msg))
                

                if(self.current_log_file != None):
                    self.current_log_file.write(msg+"\n")


                if(counter % 100 == 0):
                    print("Alive\trecorded "+str(counter))
                counter += 1

                pass

        except OSError as msg:
            print("LeapReceiver OSError Exception: "+ str(msg))
        except websocket.WebSocketConnectionClosedException as msg:
            print("LeapReceiver Connection Closed Exception: "+ str(msg))
        
        self.stopRecording()

        # Close socket
        self._closeSocks()
        print("LeapReceiver thread terminated")
        
        self.terminated = True





class CommandReceiver(threading.Thread):
    # The UDP socket used to receive commands
    udp_sock = None

    # When set to true, the thread receiving cycle will exit.
    terminationRequested = False
    
    # Set to true when the thread exists
    terminated = False


    def _closeSocks(self):
        print("Closing socket")
        if(self.udp_sock != None):
            self.udp_sock.close()
            self.udp_sock = None


    def run(self):
        print("LeapReceiver thread starting")

        print("Creating UDP socket...")
        # The socket listening to incoming data. Its status will be always synchronized with the singleton attribute:
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #     #self.sock.setblocking(False)
        #     self.sock.settimeout(0.1)
        #     self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1500)    # No buffer. We take the latest, if present, or nothing.
        print("Binding...")
        self.udp_sock.bind((BINDING_ADDR, RECEIVER_PORT))
        print("Bound.")

        while(not self.terminationRequested):

            try:
                msg = self.udp_sock.recv(1500)
                print("Received '"+msg+"'")


            except OSError as msg:
                print("LeapReceiver OSError Exception: "+ str(msg))

        # Close socket
        self._closeSocks()
        print("LeapReceiver thread terminated")
        
        self.terminated = True


    def terminate(self):
        self.terminationRequested = True
        # Interrupt socket waiting
        self._closeSocks()
        
    def hasTerminated(self):
        return self.terminated



#
# Instructions
print("You can use the following options:")
print("  v2 - enables protocol for Leap version 2 (v6.json)")
print("  rec - start already recording a log file")

#
# Parse Arguments
use_v2 = False
start_recording = False

for arg in sys.argv[1:]:
    if arg == "v2":
        use_v2 = True
    elif arg == "rec":
        start_recording = True



receiver = CommandReceiver()
receiver.start()


forwarder = LeapReceiver()

#
# Apply arguments
forwarder.useVersion2(use_v2)

if(start_recording):
    forwarder.startRecording()


#forwarder.start()
try:
    print("Running Leap reception...")
    forwarder.run()
#print("Thread Started.")
except KeyboardInterrupt:
    print("Got termination request...")
    forwarder.terminate()
    print("Waiting for process to finish")
    #while(not forwarder.hasTerminated()):
    #    pass


print("Stopping command receiver")
receiver.terminate()
print("Waiting for receiver to finish")
while(not receiver.hasTerminated()):
    pass


print("done.")

