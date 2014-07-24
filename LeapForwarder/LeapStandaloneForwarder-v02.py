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

import websocket
import threading

import sys


#BINDING_ADDR = ''   # Empty string means: bind to all network interfaces
TARGET_ADDR = '127.0.0.1'   # Empty string means: bind to all network interfaces
SERVER_PORT = 6437


class LeapReceiver: #(threading.Thread):
    """This thread will be listening to the incoming updated Leap data.
    Remember that Blender is not thread safe: we cannot invoke bpy methods in a separate thread.
    This thread will only collect the Leap Data and store the decoded python dictionary in a local variable.
    """

    # When set to true, the thread receiving cycle will exit.
    terminationRequested = False
    
    # Set to true when the thread exists
    terminated = False

    # The websocket used to gather data from the Leap application.
    sock = None

    # The UDP socket used to forward messages received from the websocket
    udp_sock = None


    def __init__(self):
        self.use_version_2 = False

    def useVersion2(self, v):
        self.use_version_2 = v
    
    
    def getLeapDict(self):
        return self.leapDict

    def _closeSocks(self):
        if(self.sock != None):
            self.sock.close()
            self.sock = None

        if(self.udp_sock != None):
            self.udp_sock.close()
            self.udp_sock = None


    def terminate(self):
        self.terminationRequested = True
        # Interrupt socket waiting
        self._closeSock()
        
    def hasTerminated(self):
        return self.terminated

    
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

            print("Creating UDP socket...")
            # The socket listening to incoming data. Its status will be always synchronized with the singleton attribute:
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #     #self.sock.setblocking(False)
        #     self.sock.settimeout(0.1)
        #     self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1500)    # No buffer. We take the latest, if present, or nothing.
            #print("Binding...")
            #self.sock.bind((BINDING_ADDR, LISTENING_PORT))
            #print("Bound.")

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
                
                # Just to test
                #leapDict = json.loads(msg)
                #print(leapDict)

                raw_msg = msg.encode("utf-8")

                size = len(raw_msg)
                if(size > max_length):
                    max_length = size
                    print("New max_size="+str(max_length))
                #print(raw_msg.__class__)
                if(size > 10000):
                    print("Message too long ("+str(size)+"). Skipping...")
                else:
                    self.udp_sock.sendto(raw_msg, (TARGET_ADDR, SERVER_PORT))

                if(counter % 100 == 0):
                    print("Alive\tsent "+str(counter)+"\tmax_size="+str(max_length))
                counter += 1

                pass

        except OSError as msg:
            print("LeapReceiver OSError Exception: "+ str(msg))
        except websocket.WebSocketConnectionClosedException as msg:
            print("LeapReceiver Connection Closed Exception: "+ str(msg))
        
        # Close socket
        self._closeSocks()
        print("LeapReceiver thread terminated")
        
        self.terminated = True


#
# Instructions
print("You can use the following options:")
print("  v2 - enables protocol for Leap version 2 (v6.json)")

#
# Parse Arguments
use_v2 = False

for arg in sys.argv[1:]:
    if arg == "v2":
        use_v2 = True


forwarder = LeapReceiver()

#
# Apply arguments
forwarder.useVersion2(use_v2)

#forwarder.start()
forwarder.run()
print("Thread Started.")
