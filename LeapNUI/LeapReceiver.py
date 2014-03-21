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
import mathutils

import threading
import json
import math
import time


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

#
#
#


class HandMotionAnalyzer:

    @staticmethod
    def countFingers(hand_id, leap_dict):
        count = 0
        for p in leap_dict["pointables"]:
            if(p["tool"] == False
                and p["handId"] == hand_id):
                count +=1
        
        return count

    
    #BUFFER_MAX_SIZE = 20
    BUFFER_MAX_AGE_SECS = 2
    
    HAND_MAX_SPEED = 1000
    
    
    max_speed=0
    
    def __init__(self):
        # Will contain a list of the last N valid positions of an hand
        # Each element will be a tuple <time, position>
        # Newer elements will be put in front.
        self.positions_buffer = []
        
        # Initialize all variables
        self.reset()

    def reset(self):
        self.buffer_lookback = 0
        self.hand_removed = False        
        self.is_hand_stable = False
        del self.positions_buffer[:]


    def handRemoved(self):
        return self.hand_removed
    

    def isHandStable(self, time, threshold):    
        #
        # Look back in the buffer to see if the hand is "stable".
        # It means that the varianve of the position is smaller than a given fraction of its average
        stability_slots = self.slotsWithinTime(time)
        x,y,z, dx,dy,dz = self.getPosAvgAndDeviation(0,stability_slots)
        avg = mathutils.Vector((x,y,z))
        dev = mathutils.Vector((dx,dy,dz))
        #print("stability_slots="+str(stability_slots)+"\tavg="+str(avg)+"\tdev="+str(dev)+"\tdevlen="+str(dev.length))
        if(dev.length<threshold):
            return True
        else:
            return False
     

    def update(self, hand):
        t = time.time()
        
        #
        # Store hand positions
        p = hand["palmPosition"]
        #print(str(p.__class__))
        
        self.positions_buffer.insert( 0, (t,p) )
        
        # Delete old data
        while(len(self.positions_buffer) > 0):
            # time of the last element
            insert_time = self.positions_buffer[len(self.positions_buffer)-1][0]
            age = t - insert_time
            if(age > self.BUFFER_MAX_AGE_SECS):
                self.positions_buffer.pop()
                #print("rage "+str(age), end="")
            else:
                break
                
        #
        # Calc average speed
        self.buffer_lookback += 1
        self.buffer_lookback = min(self.buffer_lookback, len(self.positions_buffer))
        
        sx,sy,sz = self.getAverageSpeedSlots(self.buffer_lookback-1)
        speed_vect = mathutils.Vector((sx,sy,sz))
        self.hand_speed = speed_vect.length
        
        if(self.hand_speed>self.max_speed):
            self.max_speed = self.hand_speed
            print("New max speed found="+str(self.max_speed))


        #lt_x, lt_y, lt_z = self.getLatestSpeed()
        lt_x, lt_y, lt_z = self.getAverageSpeedSlots(min(3,self.buffer_lookback-1))
        latest_speed = mathutils.Vector((lt_x,lt_y,lt_z))
        if(latest_speed.length>self.HAND_MAX_SPEED):
            self.hand_removed = True
        else:
            self.hand_removed = False
        
        # liner
        #lookback_time = 0.02 + self.BUFFER_MAX_AGE_SECS + (speed * (-self.BUFFER_MAX_AGE_SECS / self.HAND_MAX_SPEED))
        # logaritmic        
        lookback_time = self.BUFFER_MAX_AGE_SECS + self.BUFFER_MAX_AGE_SECS * (-math.log(self.hand_speed+1) / math.log(self.HAND_MAX_SPEED))
        # clamp to a minimum with sense
        lookback_time = max(lookback_time, 0.02)    
        lookback_slots = self.slotsWithinTime(lookback_time)
        
        # choose the minimum among the counter and the required lookback
        self.buffer_lookback = min(lookback_slots, self.buffer_lookback)

        #print("handspeed="+str(self.hand_speed)+"\tBufsize="+str(len(self.positions_buffer))+"\tLookbak Slots="+str(lookback_slots)+"\tbuffer_lookback="+str(self.buffer_lookback))
        

       

    def slotsWithinTime(self, time_range):
        n = 0
        latest_t = None
        for t,p in self.positions_buffer: # array indices in reverse order
            if(latest_t == None): latest_t = t
            elapsed_t = latest_t - t
            if(elapsed_t > time_range):
                break
            n += 1
        
        return n

    
    def handAge(self):
        """Returns a float, secs, of how long the hand has been active in the buffer.
        Technically the difference between the first and the last time slots."""
        
        age = 0
        if(len(self.positions_buffer)>=2):
            oldest = self.positions_buffer[len(self.positions_buffer)-1]
            latest = self.positions_buffer[0]
            age = latest[0] - oldest[0]
        
        return age


    def handFastMovement(self, min_speed, lookback_time):
        lookback_slots = self.slotsWithinTime(lookback_time)
        lt_x, lt_y, lt_z = self.getAverageSpeedSlots(lookback_slots)
        latest_speed = mathutils.Vector((lt_x,lt_y,lt_z))
        if(latest_speed.length > min_speed):
            return True
        else:
            return False


    def getPositionAverage(self):
        """Returns a tuple x,y,z with the average position over the whole buffer."""
        n = 0
        avg_x = 0
        avg_y = 0
        avg_z = 0
        for t,p in self.positions_buffer:
            n += 1
            avg_x = avg_x + ( (p[0] - avg_x) / n )
            avg_y = avg_y + ( (p[1] - avg_y) / n )
            avg_z = avg_z + ( (p[2] - avg_z) / n )

        #print("avg="+str(avg_x) + "\t" + str(avg_y) + "\t" + str(avg_z))
        return avg_x, avg_y, avg_z


    def getPositionAverageInRange(self, t1, t2):
        """Returns a tuple x,y,z with the average position over the specified time range, with t1<t2."""
        n = 0
        avg_x = 0
        avg_y = 0
        avg_z = 0
        latest_t = None
        for t,p in self.positions_buffer: # array indices in reverse order
            n += 1
            if(latest_t == None): latest_t = t
            elapsed_t = latest_t - t
            if(elapsed_t<t1):
                continue
            if(elapsed_t>t2):
                break
            #print("Addng " + str(t)+" : " + str(p))
           
            avg_x = avg_x + ( (p[0] - avg_x) / n )
            avg_y = avg_y + ( (p[1] - avg_y) / n )
            avg_z = avg_z + ( (p[2] - avg_z) / n )

        #print("avg="+str(avg_x) + "\t" + str(avg_y) + "\t" + str(avg_z))
        return avg_x, avg_y, avg_z


    def getPositionAverageInSlotsRange(self, i1, i2):
        """Returns a tuple x,y,z with the average position over the specified time range, with i1<i2."""
        n = 0
        avg_x = 0
        avg_y = 0
        avg_z = 0
        latest_t = None
        for i in range(i1, i2): # array indices in reverse order
            n += 1
            t,p = self.positions_buffer[i]
            if(latest_t == None): latest_t = t
            elapsed_t = latest_t - t
            #print("Addng " + str(t)+" : " + str(p))
           
            avg_x = avg_x + ( (p[0] - avg_x) / n )
            avg_y = avg_y + ( (p[1] - avg_y) / n )
            avg_z = avg_z + ( (p[2] - avg_z) / n )

        #print("avg="+str(avg_x) + "\t" + str(avg_y) + "\t" + str(avg_z))
        return avg_x, avg_y, avg_z

    def getPosAvgAndDeviation(self, i1, i2):
        """Compute the average and eviation of the speed in the specified range.
        Returns the 6-tuple avg_x, avg_y, avg_z, dev_x, dev_y, dev_z."""
        #The standard deviation of a random variable, statistical population, data set, or probability distribution is the square root of its variance
        #http://www.stat.wisc.edu/~larget/math496/mean-var.html
        # m_k = m_{k-1} + (x_k - m_{k-1}) / k
        # s_k = s_{k-1} + (x_k - m_{k-1}) * (x_k - m_k)

        n = 0
        avg_x = 0
        avg_y = 0
        avg_z = 0
        dev_x = 0
        dev_y = 0
        dev_z = 0
        
        latest_t = None
        for i in range(i1, i2): # array indices in reverse order
            n += 1
            t,p = self.positions_buffer[i]
            if(latest_t == None): latest_t = t
            elapsed_t = latest_t - t
            #print("Addng " + str(t)+" : " + str(p))
           
            navg_x = avg_x + ( (p[0] - avg_x) / n )
            navg_y = avg_y + ( (p[1] - avg_y) / n )
            navg_z = avg_z + ( (p[2] - avg_z) / n )

            dev_x = dev_x + (p[0] - avg_x) * (p[0] - navg_x)
            dev_y = dev_y + (p[1] - avg_y) * (p[1] - navg_y)
            dev_z = dev_z + (p[2] - avg_z) * (p[2] - navg_z)

            avg_x = navg_x
            avg_y = navg_y
            avg_z = navg_z
    
        dev_x = math.sqrt(dev_x)
        dev_y = math.sqrt(dev_y)
        dev_z = math.sqrt(dev_z)
    
        #print("avg="+str(avg_x) + "\t" + str(avg_y) + "\t" + str(avg_z))
        return avg_x, avg_y, avg_z, dev_x, dev_y, dev_z



    def getAverageSpeed(self, time_window_secs):
        """Returns the average speed of the last samples, looking back for at maximum the provided amount if seconds.
        Returns a 3-tuple with the three components sx,sy,sz."""
        
        #
        # Calc the sped of the last limited time slot
        n = 0
        avg_sx = 0
        avg_sy = 0
        avg_sz = 0
        latest_t = None
        for i in range(0, len(self.positions_buffer)-1): # array indices in reverse order
            t1,p1 = self.positions_buffer[i] # more recent
            t2,p2 = self.positions_buffer[i+1] # previous one
            if(latest_t == None): latest_t = t1
            elapsed_t = latest_t - t2
            if(elapsed_t>time_window_secs):
                break;
            dt = t1-t2
            n += 1
            sx = (p1[0] - p2[0]) / dt
            sy = (p1[1] - p2[1]) / dt
            sz = (p1[2] - p2[2]) / dt
            
            avg_sx = avg_sx + ( (sx - avg_sx) / n )
            avg_sy = avg_sy + ( (sy - avg_sy) / n )
            avg_sz = avg_sz + ( (sz - avg_sz) / n )

        #print("avg_speed="+str(avg_sx) + "\t" + str(avg_sy) + "\t" + str(avg_sz)+"\ton "+str(n)+" samples")
        return avg_sx, avg_sy, avg_sz


    def getAverageSpeedSlots(self, slots):
        """Returns the average speed of the last samples, looking back for at maximum the provided amount if seconds.
        Returns a 3-tuple with the three components sx,sy,sz."""

        slots = min(slots, len(self.positions_buffer) -1)

        if(slots < 2):
            return 0.0,0.0,0.0
        
        #
        # Calc the sped of the last limited time slot
        n = 0
        avg_sx = 0
        avg_sy = 0
        avg_sz = 0
        for i in range(0, slots): # array indices in reverse order
            t1,p1 = self.positions_buffer[i] # more recent
            t2,p2 = self.positions_buffer[i+1] # previous one
            dt = t1-t2
            n += 1
            sx = (p1[0] - p2[0]) / dt
            sy = (p1[1] - p2[1]) / dt
            sz = (p1[2] - p2[2]) / dt
            
            avg_sx = avg_sx + ( (sx - avg_sx) / n )
            avg_sy = avg_sy + ( (sy - avg_sy) / n )
            avg_sz = avg_sz + ( (sz - avg_sz) / n )

        #print("avg_speed="+str(avg_sx) + "\t" + str(avg_sy) + "\t" + str(avg_sz)+"\ton "+str(n)+" samples")
        return avg_sx, avg_sy, avg_sz



    def getLatestSpeed(self):
        """Returns the speed easuring the last two samples.
        Returns a 3-tuple with the three components sx,sy,sz."""
        
        N = len(self.positions_buffer)
        
        if(N<2):
            return (0.0,0.0,0.0)
        #
        # Calc the speed of the last limited time slot
        t1,p1 = self.positions_buffer[0] # more recent
        t2,p2 = self.positions_buffer[1] # previous one
        dt = t1-t2
        sx = (p1[0] - p2[0]) / dt
        sy = (p1[1] - p2[1]) / dt
        sz = (p1[2] - p2[2]) / dt
            
        #print("avg_speed="+str(avg_sx) + "\t" + str(avg_sy) + "\t" + str(avg_sz)+"\ton "+str(n)+" samples")
        return sx, sy, sz



    def getSpeedModulatedPositionAverage(self):
        """Returns the average position of the hand considering only a recent temporal window.
        The window time size depends on the speed of the last movement.
        """
            
        return self.getPositionAverageInSlotsRange(0, self.buffer_lookback)

    def getStablePosition(self):
        print("Computing stable position for buffer range "+ str(self.buffer_lookback) + " - " + str(len(self.positions_buffer)))
        return self.getPositionAverageInSlotsRange(self.buffer_lookback, len(self.positions_buffer))


    # Tmovement ----------> Tchange ----------> T0
    def suddenChange(self, change_lookback, movement_lookback):
        if(len(self.positions_buffer) < 2):
            return False
        
        start_slot = self.slotsWithinTime(movement_lookback)
        change_slot = self.slotsWithinTime(change_lookback)
        
        now_pos = mathutils.Vector(self.positions_buffer[0][1])
        start_pos = mathutils.Vector(self.positions_buffer[start_slot-1][1])
        change_pos = mathutils.Vector(self.positions_buffer[change_slot-1][1])
        
        movement_vect = change_pos - start_pos
        change_vect = now_pos - change_pos
        
        prod = movement_vect.dot(change_vect)
        
        return prod < 0

    # Tmovement ----------> Tchange ----------> T0
    def changeOfDirection(self, change_lookback, movement_lookback, min_back_speed):
        change_lookback_slots = self.slotsWithinTime(change_lookback)
        movement_lookback_slots = self.slotsWithinTime(movement_lookback)
        speed = mathutils.Vector(self.getAverageSpeedSlots(change_lookback_slots))
        sudden_change = self.suddenChange(change_lookback=change_lookback, movement_lookback=movement_lookback)

        #print("speed="+str(speed.length)+"\tchange="+str(sudden_change))
        
        return (speed.length > min_back_speed) and sudden_change

