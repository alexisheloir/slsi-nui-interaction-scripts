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
from LeapNUI.LeapReceiver import HandMotionAnalyzer
from LeapNUI.LeapModalController import LeapModal



        
#
#
#

class LeapInteractionLogic:
    
    EDIT_ON_THRESHOLD_SECS = 0.5 #0.1
    EDIT_OFF_THRESHOLD_SECS = 1.0 #0.5
    EDIT_STABILITY_THRESHOLD = 10 #20
    EDIT_ON_MAX_FINGERS = 2

    DROP_OFF_RADIUS_THRESHOLD_MM = 1
    
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
    

        li = bpy.context.window_manager.leap_info
        leap_logic = li.leap_logic
        
    
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
                    #print(str(self.hand_motion_analyzer.handAge()) + " ... ")
                    leap_logic.setTracking(True)
                    print("Tracking ACTIVATED")
                    
                    self.tracking_start = time.time()
    
                    # Run LeapModal operator
                    # @see http://www.blender.org/documentation/blender_python_api_2_68_release/bpy.ops.html
                    li.leap_listener.hand_motion_analyzer.reset()
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
            self.tracking_start = None
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
                self.tracking_start = None
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
                self.tracking_start = None
                li.leap_listener.resetHandId()
                leap_logic.last_drop_pos = None
                print("Tracking DEACTIVATED (Change of direction)")
                return {'FINISHED'}


            #
            # if "HAND IS STABLE"
            #print("stable="+str((li.leap_listener.hand_motion_analyzer.isHandStable(leap_logic.EDIT_OFF_THRESHOLD_SECS, leap_logic.EDIT_STABILITY_THRESHOLD))) + "\ttracinktime="+str(tracking_time))
            if(leap_logic.GRAB_MODE == leap_logic.GRAB_MODE_TIMED
                and li.leap_listener.hand_motion_analyzer.isHandStable(leap_logic.EDIT_OFF_THRESHOLD_SECS, leap_logic.EDIT_STABILITY_THRESHOLD)
                and tracking_time>leap_logic.EDIT_OFF_THRESHOLD_SECS
                ):
                leap_logic.setTracking(False)
                self.tracking_start = None
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
                self.tracking_start = None
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

