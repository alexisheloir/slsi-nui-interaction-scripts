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


#
#
#

import bpy
import bgl
import blf
import mathutils

import math
import time

from LeapNUI.LeapReceiver import LeapReceiver
from LeapNUI.LeapReceiver import HandSelector
from LeapNUI.LeapModalController import LeapModal



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
        
        
        
#
#
#



class LeapDictListener:
    
    def __init__(self):
    
        self.hand_selector = HandSelector()

        self.hand_motion_analyzer = HandMotionAnalyzer()
    
        self.tracking_start = -1
        
        #self.first_time_in_3dview = -1
    
        self.last_3dview = None

        self.last_hand_id = None
        
        self.last_dict_received = None
    
        # end __init__
        
    def getHandId(self):
        """Returns the ID of the last hand detected as valid for motion.
        Or None if no hand is detected."""
        
        return self.last_hand_id
    
    def resetHandId(self):
        self.last_hand_id = None
    
    def getLeapDict(self):
        return self.last_dict_received
    
     
    
    def newDictReceived(self, leap_dict):
    
        self.last_dict_received = leap_dict
    

        leap_logic = bpy.context.window_manager.leap_info.leap_logic
        
    
        leap_logic.hand_changed = False
    
        hand = self.hand_selector.select(leap_dict)
        if(hand != None):
            #print("HHH ID "+str(hand["id"]))
            if(hand["id"] != self.last_hand_id):
                leap_logic.hand_changed = True
                self.hand_motion_analyzer.reset()
    
            self.hand_motion_analyzer.update(hand)
    
        #
        # Memories for next cycle
        if(hand != None):
            self.last_hand_id = hand["id"]
        else:
            self.last_hand_id = None
            

        #print("gmode="+str(leap_logic.GRAB_MODE)+"\t"+str(leap_logic.EDIT_ON_THRESHOLD_SECS))
    
        #
        # Handle tracking condition    
        if(leap_logic.isTracking() == True):
            #print("t")
            # Deactivatino logic is in the LeapManipulator Operator
            pass
                   
        if(leap_logic.isTracking() == False):
            if(hand != None):
                #active_time = hand["timeVisible"]
                #print(str(hand["id"]) + ": " + str(active_time))
                
                distant_from_last_drop = True
                if(leap_logic.last_drop_pos!=None):
                    curr_pos = mathutils.Vector(hand["palmPosition"])
                    dist = (curr_pos - leap_logic.last_drop_pos).length
                
                    distant_from_last_drop = dist > leap_logic.DROP_OFF_RADIUS_THRESHOLD_MM
                    #print("DISTANT ENOUGH? " + str(dist) + "\t" + str(distant_from_last_drop))
        
                n_fingers = HandMotionAnalyzer.countFingers(hand_id=hand["id"], leap_dict=leap_dict)


            
                # Activate tracking!!!
                #print("hand age="+str(self.hand_motion_analyzer.handAge()))
                if( (leap_logic.GRAB_MODE == leap_logic.GRAB_MODE_TIMED
                    and self.hand_motion_analyzer.handAge()>leap_logic.EDIT_ON_THRESHOLD_SECS
                    and self.hand_motion_analyzer.isHandStable(leap_logic.EDIT_ON_THRESHOLD_SECS, leap_logic.EDIT_STABILITY_THRESHOLD)
                    and distant_from_last_drop==True
                    )
                    or
                    (
                    leap_logic.GRAB_MODE == leap_logic.GRAB_MODE_FINGER
                    and n_fingers <= leap_logic.EDIT_ON_MAX_FINGERS
                    )
                    ):
                    print(str(self.hand_motion_analyzer.handAge()) + " ... ")
                    leap_logic.setTracking(True)
                    print("Tracking ACTIVATED")
                    
                    self.tracking_start = time.time()
    
                    # run translator
                    # TODO
                    #bpy.operator.
                    #bpy.ops.view3d.leap_manipulator()
                    # @see http://www.blender.org/documentation/blender_python_api_2_68_release/bpy.ops.html
                    #bpy.ops.transform.leap_manipulator('INVOKE_DEFAULT')
                    bpy.ops.object.leap_modal(isRotating=True, isTranslating=True)
                    
            else:
                #assert (self.tracking == False and hand==None)
                
                # We reset the location of the last stable position
                if( (leap_logic.GRAB_MODE == leap_logic.GRAB_MODE_TIMED) ):
                    if(leap_logic.last_drop_pos != None):
                        print("Clearing last drop position")
                        leap_logic.last_drop_pos = None
                pass
        
        
        pass # end newDictReceived
    

#
#
#

class LeapInteractionLogic:
    
    EDIT_ON_THRESHOLD_SECS = 0.5 #0.1
    EDIT_OFF_THRESHOLD_SECS = 1.0 #0.5
    EDIT_STABILITY_THRESHOLD = 10 #20
    EDIT_ON_MAX_FINGERS = 2

    DROP_OFF_RADIUS_THRESHOLD_MM = 50
    
    FAST_MOVEMENT_SPEED = 1000
    FAST_MOVEMENT_LOOKBACK_SECS = 0.1

    CARRIAGE_RETURN_TOTAL_LOOKBACK_SECS = 0.4
    CARRIAGE_RETURN_CHANGE_LOOKBACK_SECS = 0.2
    CARRIAGE_RETURN_MIN_BACKSPEED = 100


    GRAB_MODE_FINGER = 0
    GRAB_MODE_TIMED = 1

    GRAB_MODE = GRAB_MODE_TIMED
    #GRAB_MODE = GRAB_MODE_FINGER
    

    def __init__(self):
        self.tracking = False
        
        self.last_drop_pos = None
        
        self.hand_changed = False
        
    
    def isTracking(self):
        return self.tracking
    
    def setTracking(self,b):
        self.tracking = b

    def clearLastDrop():
        self.last_drop_pos = None


#
#
#

class LeapInfo:
    """Support class to collect global shared data: the receiver thread, and the listener taking care of new incoming leap dictionaries.
    """
        
    def __init__(self):
        self.leap_receiver = None
        self.leap_listener = None
        self.leap_logic = None
        
        self.dict_last_id = -1
        
    def start(self):
        self.leap_receiver = LeapReceiver.getSingleton()
        self.leap_listener = LeapDictListener()
        self.leap_logic = LeapInteractionLogic()

    def update(self):
        
        # Local copy (Should be protected, but is atomic enough)
        leap_dict = self.leap_receiver.leapDict
        
        #print("update called on "+str(self))
        #print(leap_dict)
        if(leap_dict == None):
            print("No Leap data yet...")
            return

        if(not "id" in leap_dict):
            print("No id in dict (must be version frame...)")
            return

        new_id = leap_dict["id"]
        # Check if the dictionary has been updated
        if(new_id > self.dict_last_id):
            #print("Old dict, skipping...")
            self.dict_last_id = new_id

            self.leap_listener.newDictReceived(leap_dict)

        
    def stop(self):
        if(self.leap_receiver != None):
            self.leap_receiver.releaseSingleton()
            self.leap_receiver = None



#
#
#

class KeyboardlessControlOn(bpy.types.Operator):
    bl_idname = "wm.leap_nui_keyboardless_control_on"
    bl_label = "Keyboardless Daemon On"
    bl_description = "Activate the modal operator enabling Keyboardless interaction"

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        if (context.window_manager.leap_nui_keyboardless_active == False):
            bpy.ops.wm.leap_nui_keyboardless_control_switch()

        return {'FINISHED'}


#
#
#

class KeyboardlessControlOff(bpy.types.Operator):
    bl_idname = "wm.leap_nui_keyboardless_control_off"
    bl_label = "Keyboardless Daemon Off"
    bl_description = "Deactivate the modal operator enabling Keyboardless interaction"
    
    def invoke(self, context, event):
        return self.execute(context)
    
    def execute(self, context):
        if (context.window_manager.leap_nui_keyboardless_active == True):
            bpy.ops.wm.leap_nui_keyboardless_control_switch()
        
        return {'FINISHED'}


#
#
#


class KeyboardlessControlSwitch(bpy.types.Operator):
    bl_idname = "wm.leap_nui_keyboardless_control_switch"
    bl_label = "Leap Daemon Switch"
    bl_description = "De/Activate reception of Leap Motion data into Blender"
    
    ACTIVATION_KEY = 'K'    # characters in upcase, please.

    _draw_handle = None

    _time_handle = None
    

    @staticmethod
    def handle_add(self, context):
        KeyboardlessControlSwitch._draw_handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL')
        KeyboardlessControlSwitch._time_handle = context.window_manager.event_timer_add(0.025, context.window)
        if(bpy.context.area):
            bpy.context.area.tag_redraw()

    @staticmethod
    def handle_remove(context):
        if KeyboardlessControlSwitch._draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(KeyboardlessControlSwitch._draw_handle, 'WINDOW')
        KeyboardlessControlSwitch._draw_handle = None
        if(bpy.context.area):
            bpy.context.area.tag_redraw()


    _leap_modal_listener = None


    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        print(str(self.__class__)+ " invoked on area type " + context.area.type)

        if (context.window_manager.leap_nui_keyboardless_active == False):
            #
            # ACTIVATION CALL
            #
            print("KeyboardlessControlSwitch activating...")

            KeyboardlessControlSwitch.handle_add(self, context)            
            context.window_manager.leap_info.start()
            
            context.window_manager.modal_handler_add(self)
            
            KeyboardlessControlSwitch._leap_modal_listener = KeyboardLessLogicModalListener()
            LeapModal.modalCallbacks.append(KeyboardlessControlSwitch._leap_modal_listener)
            
            KeyboardlessControlSwitch._terminate = False

            context.window_manager.leap_nui_keyboardless_active = True
            return {'RUNNING_MODAL'}

        else:
            print("KeyboardlessControlSwitch asking termination...")
            # The command was already running. Flag to finish it at next modal call
            context.window_manager.leap_nui_keyboardless_active = False
            # and finish this instance
            return {'FINISHED'}
        
        
    def modal(self, context, event):
        
#        print(event.type
#            +"\t"+str(context.window_manager.leap_info.isActive())
#            +"\t"+str(LeapDaemonSwitch._terminate))
        if(not event.type == 'TIMER'):
            return {'PASS_THROUGH'}

        
        if(context.window_manager.leap_nui_keyboardless_active == False):
            print("LeapDaemonSwitch stopping...")

            LeapModal.modalCallbacks.remove(KeyboardlessControlSwitch._leap_modal_listener)
            KeyboardlessControlSwitch._leap_modal_listener = None

            context.window_manager.leap_info.stop()

            KeyboardlessControlSwitch.handle_remove(context)
                        
            return {'FINISHED'}
            
        else:
            context.window_manager.leap_info.update()
            return {'PASS_THROUGH'}
        
        return {'PASS_THROUGH'}


    def cancel(self, context):
        if context.window_manager.leap_nui_keyboardless_active:
            KeyboardlessControlSwitch.handle_remove(context)
            context.window_manager.leap_info.stop()
            KeyboardlessControlSwitch._terminate = False
        return {'CANCELLED'}

#
#
#

class KeyboardLessLogicModalListener:
    
    tracking_start = None

    
    def controllersUpdated(self, leap_modal, context):
        li = context.window_manager.leap_info
        #assert(li!=None) # otherwise the command wouldn't have started
        leap_logic = context.window_manager.leap_info.leap_logic

        assert (leap_logic.isTracking() == True)
    
        now = time.time()
        if(self.tracking_start == None):
            self.tracking_start = now

        tracking_time = now - self.tracking_start

        leap_dict = li.leap_listener.getLeapDict()
        hand_id = li.leap_listener.getHandId()
        hand = li.leap_listener.hand_selector.getHandFromId(hand_id, leap_dict)

        
        #if(hand == None or hand_changed):
        if(hand_id == None or leap_logic.hand_changed):
            # Hand out of sight
            # or hand changed: DEACTIVATE TRACKING
            leap_logic.setTracking(False)
            li.leap_listener.resetHandId()
            leap_logic.last_drop_pos = None
            reason = "Unknown"
            if(hand_id == None): reason = "lost"
            elif(leap_logic.hand_changed) : reason = "changed"
            print("Tracking DEACTIVATED (hand " + reason + ")")
            return {'FINISHED'}

        else:
            # Tracking on and hand in sight: MOVE OBJECT
            #leap_modal.object_translator.update(li.leap_listener.getLeapDict())
            
            #leap_modal.object_rotator.update(li.leap_listener.getLeapDict())
            
            #
            # if "HAND REMOVED"
            if(leap_logic.GRAB_MODE == leap_logic.GRAB_MODE_TIMED
                and li.leap_listener.hand_motion_analyzer.handFastMovement(leap_logic.FAST_MOVEMENT_SPEED, leap_logic.FAST_MOVEMENT_LOOKBACK_SECS)
                ):
                # put the object in previous stable position
                x,y,z = li.leap_listener.hand_motion_analyzer.getStablePosition()

                leap_modal.obj_translator.setTargetPositionHandSpace(x,y,z)
                # switch tracking to deactiveted
                leap_logic.setTracking(False)
                li.leap_listener.resetHandId()
                leap_logic.last_drop_pos = None
                print("Tracking DEACTIVATED (Hand fast movement)")
                return {'FINISHED'}

        
            #
            # handle "CARRAGE RETURN"
            if(leap_logic.GRAB_MODE == leap_logic.GRAB_MODE_TIMED
                and li.leap_listener.hand_motion_analyzer.changeOfDirection(
                    leap_logic.CARRIAGE_RETURN_CHANGE_LOOKBACK_SECS,
                    leap_logic.CARRIAGE_RETURN_TOTAL_LOOKBACK_SECS,
                    leap_logic.CARRIAGE_RETURN_MIN_BACKSPEED)
                ):
                leap_logic.setTracking(False)
                li.leap_listener.resetHandId()
                leap_logic.last_drop_pos = None
                print("Tracking DEACTIVATED (Change of direction)")
                return {'FINISHED'}


            #
            # if "HAND IS STABLE"
            if(leap_logic.GRAB_MODE == leap_logic.GRAB_MODE_TIMED
                and li.leap_listener.hand_motion_analyzer.isHandStable(leap_logic.EDIT_OFF_THRESHOLD_SECS, leap_logic.EDIT_STABILITY_THRESHOLD)
                and tracking_time>leap_logic.EDIT_OFF_THRESHOLD_SECS
                ):
                leap_logic.setTracking(False)
                li.leap_listener.resetHandId()
                leap_logic.last_drop_pos = mathutils.Vector(hand["palmPosition"])
                li.leap_listener.hand_motion_analyzer.reset()
                print("Tracking DEACTIVATED (Hand stable)")
                return {'FINISHED'}

                
            #
            # if "FINGERS CLOSED"
            n_fingers = li.leap_listener.hand_motion_analyzer.countFingers(hand_id=hand_id, leap_dict=leap_dict)
            if(leap_logic.GRAB_MODE == leap_logic.GRAB_MODE_FINGER
                and n_fingers > leap_logic.EDIT_ON_MAX_FINGERS
                ):
                leap_logic.setTracking(False)
                li.leap_listener.resetHandId()
                leap_logic.last_drop_pos = mathutils.Vector(hand["palmPosition"])
                #op.hand_motion_analyzer.reset()
                print("Tracking DEACTIVATED (Fingers opened)")
                return {'FINISHED'}
                
        
        pass # end (op.tracking==True && hand!=None)

        return None


#
#
#

def draw_callback_px(self, context):
    wm = context.window_manager
    r=0.8
    g=0.1
    b=0.2
    

    if(context.window_manager.leap_nui_keyboardless_active):
        #print("Draw Callback True")
        # draw text in the 3D View
        bgl.glPushClientAttrib(bgl.GL_CURRENT_BIT|bgl.GL_ENABLE_BIT)
        
        blf.size(0, 12, 72)
        blf.position(0, 10, 10, 0)
        bgl.glColor4f(r, g, b, 0.7)
        blf.blur(0, 1)
        # shadow?
        blf.enable(0, blf.SHADOW)
        blf.shadow_offset(0, 1, -1)
        blf.shadow(0, 5, 0.0, 0.0, 0.0, 0.8)
    
        blf.draw(0, "Leap Active!")
        
        bgl.glPopClientAttrib()
    else:
        #print("Draw Callback False")
        pass

    if(wm.leap_info.leap_logic.isTracking()):
        bgl.glPushClientAttrib(bgl.GL_CURRENT_BIT|bgl.GL_ENABLE_BIT)

        # transparence
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        
        msg = "GRABBING!"
        font_size = 48
     
        blf.size(0, font_size, 72)
        bgl.glColor4f(r, g, b, 0.7)
        blf.blur(0, 1)
        # shadow?
        blf.enable(0, blf.SHADOW)
        blf.shadow_offset(0, 1, -1)
        blf.shadow(0, 5, 0.0, 0.0, 0.0, 0.8)

        item_w,item_h = blf.dimensions(0, msg)
        pos_x = (context.region.width - item_w) / 2
        pos_y = 0
        
        blf.position(0, pos_x, pos_y, 0)    
        blf.draw(0, msg)
        
        bgl.glPopClientAttrib()

#
#
#


# store keymaps here to access after registration
addon_keymaps = []


def register():
    # Init global properties

    # Runstate initially always set to False
    # note: it is not stored in the Scene, but in window manager:
    bpy.types.WindowManager.leap_info = LeapInfo()
    
    
    # Register classes    
    bpy.utils.register_class(KeyboardlessControlSwitch)
    bpy.utils.register_class(KeyboardlessControlOn)
    bpy.utils.register_class(KeyboardlessControlOff)

    # Init key shortcuts control
    
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Window', space_type='EMPTY', region_type='WINDOW')
        kmi = km.keymap_items.new(KeyboardlessControlSwitch.bl_idname, KeyboardlessControlSwitch.ACTIVATION_KEY, 'PRESS', shift=True, alt=True)
        addon_keymaps.append((km, kmi))

    print("Registered")


def unregister():
    
    # in case its enabled
    #GlobalTimedCallbackOperator.handle_remove(bpy.context)

    bpy.utils.unregister_class(KeyboardlessControlOff)
    bpy.utils.unregister_class(KeyboardlessControlOn)
    bpy.utils.unregister_class(KeyboardlessControlSwitch)

    

    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    # removal of properties when script is disabled
    del bpy.context.window_manager.leap_info
    # wm = bpy.context.window_manager
    # props = "leap_info"
    # for p in props:
    #     if p in wm:
    #         del wm[p]

    print("Unregistered")


if __name__ == "__main__":
    register()

