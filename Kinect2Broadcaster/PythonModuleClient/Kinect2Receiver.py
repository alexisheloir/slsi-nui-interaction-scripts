    # Kinect2Receiver. A Python module inplementing the client side of the Kinect2Broadcaster protocol.
    # Copyright (C) 2014  Fabrizio Nunnari

    # This program is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
#
# Usage:
#
# Kinect2Receiver.startReception()
#
# Kinect2Receiver.discoverServer()
#
# time.sleep(100) # wait for answer
#
# while(i_want):
#
#     if(first_cacle or 10_minutes_passed):
#         Kinect2Receiver.askForData("“CLOSEST_TO_CENTER”")
#
#     joints_dict = Kinect2Receiver.getKinectData()
# 
# Kinect2Receiver.stopReception()
#

import OSC
import time, threading

import socket

local_osc_server = None
receiving_thread = None

# Buffer for the lat valid received data
# dictionary of joints. key=(int)joint_id, value=([ifffffffi])[joint_id, x,y,z, rot_w,rot_x,rot_x,rot_z, confidence]
joints_data={}
joints_data_timestamp=0

# Buffers the last pose received
pose=""
pose_timestamp=0



#BROADCAST_ADDRESS = "10.105.1.22"
#BROADCAST_ADDRESS = "10.105.15.255"
BROADCAST_ADDRESS = "255.255.255.255"

SERVER_PORT = 10750
LOCAL_PORT = 10751

# The server IP address string. None before any discovery
server_address = None

# Used to send osc data
osc_bcast_client = OSC.OSCClient()
osc_bcast_client.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
osc_bcast_client.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) 


#
# OSC reception handlers
#

def joint_position(addr, tags, joint_info, source):
    global joints_data, joints_data_timestamp
    # store in the dictionary, using the joint_id as key
    joints_data[joint_info[0]]=joint_info
    joints_data_timestamp = time.time()
    

def sever_answer(addr, tags, params, source):
    global server_address
    print("Kinect2Receiver: received answer from "+str(addr)+", src="+str(source))
    server_address = source[0]  # TODO - check, it might be the OSC level addr

def pose_received(addr, tags, params, source):
    global pose, pose_timestamp
    pose = params[0]
    #print("Got pose "+pose)
    pose_timestamp = time.time()

#
# Protocol send methods
#

# Send a message on the broadcast address to discover any server
def discoverServer():
    # From https://docs.python.org/3/library/socket.html
    #For IPv4 addresses, two special forms are accepted instead of a host address: the empty string represents INADDR_ANY, and the string '<broadcast>' represents INADDR_BROADCAST. This behavior is not compatible with IPv6, therefore, you may want to avoid these if you intend to support IPv6 with your Python programs.


    # info = socket.getaddrinfo(socket.gethostname(), 10751, socket.AF_INET, socket.SOCK_DGRAM, 0, 0)
    # for i in info:
    #     print(" - " + str(i))


    #def sendto(self, msg, address, timeout=None):
    msg = OSC.OSCMessage()
    msg.setAddress("/kinect2/where_are_you")

    print("Kinect2Receiver: broadcast "+str(msg)+" to "+BROADCAST_ADDRESS)
    osc_bcast_client.sendto(msg, (BROADCAST_ADDRESS, SERVER_PORT))


def askForClosestToCenterData():
    askForData("CLOSEST_TO_CENTER")

def askForFirstLeftFromCenterData():
    askForData("FIRST_LEFT_FROM_CENTER")

def askForFirstRightFromCenterData():
    askForData("FIRST_RIGHT_FROM_CENTER")


# User Position can be one of the following:
# “CLOSEST_TO_CENTER”: the subject whose center x coordinates is closest to x=0
# “FIRST_LEFT_FROM_CENTER”: the first subject whose center x coordinates are > 0 (left when looking at the Kinect)
# “FIRST_RIGHT_FROM_CENTER”: the first subject whose center x coordinates are < 0 (right when looking at the Kinect)
def askForData(user_position):
    if(server_address == None):
        print("Kinect2Receiver: askForData(): no Server discovered yet. Request not sent.")
        return

    msg = OSC.OSCMessage("/kinect2/send_me_info")
    msg.append(user_position, 's')

    osc_bcast_client.sendto(msg, (server_address, SERVER_PORT))

#
# Management
#
    
def startReception():
    global local_osc_server, receiving_thread

    if(local_osc_server != None):
        print("Local OSC listener still running. Force stopping.")
        stopReception()

    #receive_address='10.105.11.255', 10750  
    receive_address='', LOCAL_PORT  # ready to receive on every network interface
    local_osc_server = OSC.OSCServer(receive_address)
    local_osc_server.addDefaultHandlers()
    local_osc_server.addMsgHandler("/kinect2/joint", joint_position)
    local_osc_server.addMsgHandler("/kinect2/here_I_am", sever_answer)
    local_osc_server.addMsgHandler("/kinect2/pose", pose_received)

    receiving_thread = threading.Thread( target = local_osc_server.serve_forever )
    receiving_thread.start()
	
	
def stopReception():
    global local_osc_server, receiving_thread, server_address
    if(local_osc_server != None):
        local_osc_server.close()
        local_osc_server = None
    if(receiving_thread != None):
        receiving_thread.join()
        receiving_thread = None
    # Reset address of the remote server
    server_address = None


def getJointsData():
    return joints_data

def getJointsDataTimestamp():
    return joints_data_timestamp

def getPose():
    return pose

def getPoseTimestamp():
    return pose_timestamp

def isServerDiscovered():
    return (server_address != None)


# start the server and run it for 5 seconds
def test():
    #info = socket.getaddrinfo("<broadcast>", 10751, socket.AF_INET, socket.SOCK_DGRAM, 0, 0)
    #for i in info:
    #    print(" - " + str(i))

    print("Starting...")
    startReception()

    print("Discovering...")
    discoverServer()

    time.sleep(0.1) # wait for answer

    print("Asking...")
    askForData("CLOSEST_TO_CENTER")
    #askForFirstLeftFromCenterData()

    start_time = time.time()

    while((time.time()-start_time) < 60.0):

        print("Getting...")
        joints_dict = getKinectData()
        print("Received: "+str(joints_dict))

        time.sleep(0.7)

    print("Stopping...")
    stopReception()

    print("Done.")

