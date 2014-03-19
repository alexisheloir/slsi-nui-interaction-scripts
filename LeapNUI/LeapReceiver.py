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


import bpy

import threading
import json
import math

# Extras
import websocket
import socket
import struct   # to pack/unpack data from udp messages




# If set to true listen for forwarded UDP packets.
# Otherwise directly connect to the leapd through websockets.
# But I experienced leapd crashes when quickly opening and closing connections to it in SDK v8.0.
USE_UDP_SOCKET = True

# Address to receive packets from the Leap UDP forwarder
BINDING_ADDR = ''   # Empty string means: bind to all network interfaces
LISTENING_PORT = 6437


#
#
#

class LeapReceiver(threading.Thread):
    """This thread will be listening to the incoming updated Leap data.
    Remember that Blender is not thread safe: we cannot invoke bpy methods in a separate thread.
    This thread will only collect the Leap Data and store the decoded python dictionary in a local variable.
    Usage:
        leap_receiver = LeapReceiver()
        leap_receiver.start()
        ...
        while(i_need):
            if(leap_receiver.newDict):
                do_stuff_with(leap_receiver.getLeapDict())
                leap_receiver.markDictAsRead()
        ...
        leap_receiver.terminate()
                

    Alternatively, the class can be used with manual updates:
        leap_receiver = LeapReceiver()
        ...
        leap_receiver.connect()
        ...
        while(i_need):
            leap_receiver.update()
            do_stuff_with(leap_receiver.getLeapDict())
        ...
        leap_receiver.disconnect()
    """

    #
    # METHODS FOR STATIC USE
    #    
    
    #Counts the use of the singleton
    s_useCounter = 0
    
    # Reference to the singleton
    s_singleton = None
    
    # Maybe for the future:
    # from sys import getrefcount as grc
    # and then get the ref count with
    # grc(cls.s_singleton)
    
    @classmethod
    def getSingleton(cls):
        if(cls.s_useCounter == 0):
            assert(cls.s_singleton == None)
            cls.s_singleton = LeapReceiver()
            cls.s_singleton.start()
        cls.s_useCounter += 1
        
        return cls.s_singleton
    
    @classmethod
    def releaseSingleton(cls):
        if(cls.s_useCounter == 0):
            return
        
        cls.s_useCounter -= 1
        
        if(cls.s_useCounter == 0):
            cls.s_singleton.terminate()
            cls.s_singleton = None


    @classmethod
    def print_leap_msg_info(message):
        info = json.loads(message)
        #hands = message['hands']
        
        if(not 'hands' in info):
            return
    
        hands = info['hands']
        
        print("#hands=" + str(len(hands)))
        for hand in hands:
            id = hand['id']
            print("id="+ str(id))
        if(len(hands) > 0) :
            hand0 = hands[0]
            x,y,z = hand0['palmPosition']
            print("pos= " + str(x) + "\t" + str(y) + "\t" + str(z))
        pass
    
                        
    #
    #
    #
    
    

    # When set to true, the thread receiving cycle will exit.
    terminationRequested = False
    
    # Set to true when the thread exists
    terminated = False

    # The websocket used to gather data from the Leap application.
    sock = None
    
    # Will hold the decoded python dictionary. Updated at each leap message reception
    leapDict = None

    # Will be set to true everytime a new dictionary is received
    # Readers can set it to False to avoid reading duplicates
    newDict = False
    
    # list of listeners. Listeners must provide a function newDictReceived(dictionary) that will be called each time a new dictionary is received.
    listeners = []

    def addListener(self, l):
        self.listeners.append(l)
    
    def removeAllListeners(self):
        del self.listeners[:]
    

    def getLeapDict(self):
        return self.leapDict

    def _closeSock(self):
        if(self.sock != None):
            self.sock.close()
            self.sock = None


    def terminate(self):
        self.terminationRequested = True
        # Interrupt socket waiting
        self._closeSock()
        
    def hasTerminated(self):
        return self.terminated
    
    def hasNewDict(self):
        return self.newDict
    
    def markDictAsRead(self):
        self.newDict = False

    def connect(self):
        # Open socket
        print("Creating web socket...")

        # The socket listening to incoming data.
        if(USE_UDP_SOCKET):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((BINDING_ADDR, LISTENING_PORT))
        else:
            self.sock = websocket.create_connection("ws://localhost:6437/")

        print("Created.")

        if(not USE_UDP_SOCKET):
            # Enable gesture detection
            request = json.dumps({ "enableGestures": "true"})
            self.sock.send(request)
    
    def disconnect(self):
        # Close socket
        self._closeSock()
        print("LeapReceiver thread terminated")
        
        self.terminated = True
        

    def update(self):
        # gather Leap data
        #print("Receiving")

        if(USE_UDP_SOCKET):
            raw_msg = self.sock.recv(10000)
            msg = raw_msg.decode("utf-8")
        else:
            msg = self.sock.recv()
        
        self.leapDict = json.loads(msg)
        self.newDict = True
        for l in self.listeners:
            l.newDictReceived(self.leapDict)

        pass

        
    
    def run(self):
        print("LeapReceiver thread starting")


        try:
            self.connect()
            
            while(not self.terminationRequested):
                self.update()

        except OSError as msg:
            print("LeapReceiver OSError Exception: "+ str(msg))
        except websocket.WebSocketConnectionClosedException as msg:
            print("LeapReceiver Connection Closed Exception: "+ str(msg))
        
        self.disconnect()




#
#
#

class HandSelector:
    """Hand detection is sometime unstable, so IDs are lost and reassigned even when the hand
        id actually still in the Leap working space. Also, hand order is sometime shuffled.
        This class encapsulate some policies to try to stick on the same hand.
        """

    @staticmethod
    def getHandFromId(id, leap_dict):
        if(not 'hands' in leap_dict):
            return None
        
        hands = leap_dict["hands"]
        
        for hand in hands:
            if( hand["id"] == id):
                return hand
        
        return None


    last_hand_id = None
    
    def select(self, leap_dict):
        """Return the most appropriate hand according to previous selection.
            Returns None if no hands where found."""
        
        
        if(not 'hands' in leap_dict):
            print("NO HANDS")
            return None
        
        hands = leap_dict["hands"]
        
        if (len(hands) < 1):
            return None
        
        hand = None
        
        # if there were no hand since last reset, take the first available
        if(self.last_hand_id == None):
            hand = hands[0]
            self.last_hand_id = int(hand["id"])
            #print("FIRST HAND FOUND ID="+str(self.last_hand_id))
            #print(str(hands))
        else:   #there was a finger in previous message. Try to use the same.
            for h in hands:
                id = int(h["id"])
                if(id == self.last_hand_id):
                    hand = h
                    #print("PREVIOUS POINTABLE RETRIEVED ID=" + str(id))
                    break ;
            # If the previous hand is not anymore recognized, take again the first one
            # TODO -- instead of taking the first available, store the coordinates of the previous hand and choose the closest one!
            if(hand == None):
                hand = hands[0]
                self.last_hand_id = int(hand["id"])
                #print("NEW HAND SELECTED ID="+str(self.last_hand_id))
                #print(str(hands))
        
        
        assert (hand != None)
        
        return hand


#
#
#

class PointableSelector:
    """Same philosophy of HandSelector."""
    
    last_pointable_id = None
    
    def select(self, leap_dict):
        """Return the most appropriate finger according to previous selection.
            Returns None if no pointables where found."""
        
        
        if(not 'pointables' in leap_dict):
            print("NO POINTABLES")
            return None
        
        all_pointables = leap_dict["pointables"]
        
        
        # Remove pointables with no hand associated. They ceate some false positive detections.
        pointables = [p for p in all_pointables if p["handId"] != -1]
        
        if (len(pointables) < 1):
            return None
        
        pointable = None
        
        # if there were no pointables since last reset, take the first available
        if(self.last_pointable_id == None):
            pointable = pointables[0]
            self.last_pointable_id = int(pointable["id"])
            #print("FIRST POINTABLE FOUND ID="+str(self.last_pointable_id))
            #print(str(pointables))
        else:   #there was a finger in previous message. Try to use the same.
            for p in pointables:
                id = int(p["id"])
                if(id == self.last_pointable_id):
                    pointable = p
                    #print("PREVIOUS POINTABLE RETRIEVED ID=" + str(id))
                    break ;
            # If the previous pointable is not anymore recognized, take again the first one
            if(pointable == None):
                pointable = pointables[0]
                self.last_pointable_id = int(pointable["id"])
                #print("NEW POINTABLE SELECTED ID="+str(self.last_pointable_id))
                #print(str(pointables))
        
        assert (pointable != None)
        
        return pointable


#
#
#

class CircleGestureSelector:
    """Used to retrieve information about pointable circle events.
        Same philosophy of HandSelector."""
    
    last_gesture_id = None
    
    def select(self, leap_dict):
        """Returns the most recent circle gesture according to previous selection.
            Returns None, None if no hands where found."""
        
        if(not 'gestures' in leap_dict):
            #print("NO GESTURES")
            return None
        
        all_gestures = leap_dict["gestures"]
        
        # Remove gestures not of type circle.
        gestures = [g for g in all_gestures if g["type"] == "circle"]
        #print(str(gestures))
        
        if (len(gestures) < 1):
            return None
        
        gesture = None
        
        # if there were no hand since last reset, take the first available
        if(self.last_gesture_id == None):
            gesture = gestures[0]
            self.last_gesture_id = int(gesture["id"])
            print("FIRST GESTURE FOUND ID="+str(self.last_gesture_id))
            print(str(gestures))
        else:   #there was a finger in previous message. Try to use the same.
            for g in gestures:
                id = int(g["id"])
                if(id == self.last_gesture_id):
                    gesture = g
                    #print("PREVIOUS POINTABLE RETRIEVED ID=" + str(id))
                    break ;
            # If the previous hand is not anymore recognized, take again the first one
            if(gesture == None):
                gesture = gestures[0]
                self.last_gesture_id = int(gesture["id"])
                print("NEW GESTURE SELECTED ID="+str(self.last_gesture_id))
                print("state=" + gesture["state"])
                print(str(gestures))
        
        assert (gesture != None)
        
        return gesture
