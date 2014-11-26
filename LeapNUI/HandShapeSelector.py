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
import bgl
import blf
import mathutils

from bpy.props import * # for properties

import os
from bpy_extras import image_utils

import time # for real-time animation

import re

from LeapNUI.LeapReceiver import LeapReceiver
from LeapNUI.LeapReceiver import PointableSelector

from MakeHumanTools.BoneSet import MH_HAND_BONES_L
from MakeHumanTools.BoneSet import MH_HAND_BONES_R


LHAND_ACTIVATION_CHAR = 'D'
RHAND_ACTIVATION_CHAR = 'A'

LHAND_POSE_LIBRARY_NAME = "handshape_lib_L"
RHAND_POSE_LIBRARY_NAME = "handshape_lib_R"

# Delay between TIMER events when entering the modal command mode. In seconds.
UPDATE_DELAY = 0.04

SELECTION_MIN_Y = 50
SELECTION_MAX_Y = 120

MAX_DISPLAY_ELEMENTS = 10


def getSelectedArmature(context):
    """Returns the selected armature. Or None"""
    
    arm = None
    
    objs = context.selected_objects
    if(len(objs) != 1):
        return None
    
    arm = objs[0]
    if(arm.type != "ARMATURE"):
        return None
    
    return arm


class HandShapeSelector(bpy.types.Operator):
    """This operator activates a interactive selection of a hand shape to impose to the character.
    It is a modal operator relying on LeapMotion data to control the selection."""
    
    bl_idname = "object.leap_hand_shape_selector"
    bl_label = "Select Hand Shape"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
    bl_options = {'REGISTER', 'UNDO'}
    
    use_right_hand = BoolProperty(name="use_right_hand", description="Whether to operate on the right hand, or the left one", default=True)
    
    leap_receiver = None

    pointable_selector = None


    # The list of items to select
    selectable_items = []
    

    # Set to True in modal() if a finger is visible and within the vertical range
    finger_visible = False
    
    # A normalized float factor of the y position of the finger, in range [0,1). Set in modal().
    selection_factor = -1
    
    # The number of the first item to select in the selectino window
    # range [0, len(selectable_items) - MAX_DISPLAY_ELEMENTS - 1]
    selection_window_first_item = 0

    # The selection number for the highlighted item, in range [0,len(selectable_items)-1]
    selection_num = -1
    
    # Store rotations to later be able to restore original values.
    r_hand_initial_rotations = None
    l_hand_initial_rotations = None

    # We want to draw the information only in the area/space/region where the function has been activated.
    # So, in this variable we will store the reference to the space (bpy.context.area.spaces.active) that was active when the user activated the controls.
    execution_active_space = None

    
    def __init__(self):
        self.leap_receiver = LeapReceiver.getSingleton()
        pass
    
    def __del__(self):
        self.removeHandlers()
        if(self.leap_receiver != None):
            LeapReceiver.releaseSingleton()
            self.leap_receiver = None
        # The sock attribute might not have been defined if the command was never run
        #if(hasattr(self, 'leap_receiver')):
        #    self.stop_leap_receiver()
        pass

    
    def addHandlers(self, context):
        #
        # TIMER
        self._timer = context.window_manager.event_timer_add(UPDATE_DELAY, context.window)

        #
        # DRAW
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context,), 'WINDOW', 'POST_PIXEL')
        if(bpy.context.area):
            bpy.context.area.tag_redraw()



    _timer = None
    _draw_handle = None


    def removeHandlers(self):
        print("Removing handlers...")
        
        #
        # TIMER
        if(self._timer != None):
            self._timer = bpy.context.window_manager.event_timer_remove(self._timer)
            self._timer = None

        #
        # DRAW
        if(self._draw_handle != None):
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
            if(bpy.context.area):
                bpy.context.area.tag_redraw()

    
    def invoke(self, context, event):
        # Maybe here we check on which hand we have to apply the pose
        return self.execute(context)
    

    def execute(self, context):
        
        self.selected_armature = getSelectedArmature(context)
        if(self.selected_armature==None):
            self.report({'ERROR'}, "No selected armature")
            return {"CANCELLED"}
        
        if(self.use_right_hand):
            self.POSE_LIBRARY_NAME = RHAND_POSE_LIBRARY_NAME
            self.HAND_BONE_NAMES = MH_HAND_BONES_R
        else:
            self.POSE_LIBRARY_NAME = LHAND_POSE_LIBRARY_NAME
            self.HAND_BONE_NAMES = MH_HAND_BONES_L
        
        if(not self.POSE_LIBRARY_NAME in bpy.data.actions):
            self.report({'ERROR'}, "No action library named '" + self.POSE_LIBRARY_NAME + "' found")
            return {"CANCELLED"}

        if(self.use_right_hand):
            self.r_hand_initial_rotations = retrieveBoneRotations(self.selected_armature, MH_HAND_BONES_R)
        else:
            self.l_hand_initial_rotations = retrieveBoneRotations(self.selected_armature, MH_HAND_BONES_L)

        # Store the reference to the space where this command was activated. So that we render only there.
        self.execution_active_space = context.area.spaces.active
        
        # Retrieve entries from the pose library
        action = bpy.data.actions[self.POSE_LIBRARY_NAME]
        # See http://www.blender.org/documentation/blender_python_api_2_69_3/bpy.types.TimelineMarker.html?highlight=timelinemarker#bpy.types.TimelineMarker
        self.selectable_items = []
        for marker in action.pose_markers:
            print("Found marker " + str(marker.name) + " at frame " + str(marker.frame))
            self.selectable_items.append(marker.name)
            
        #self.leap_receiver = LeapReceiver.getSingleton()
        self.pointable_selector = PointableSelector()

        context.window_manager.modal_handler_add(self)
        self.addHandlers(context)


        return {"RUNNING_MODAL"}
    

    last_modal_time = None

    def modal(self, context, event):
        #FINISHED, CANCELLED, RUNNING_MODAL
        #print("HandShapeSelector running modal")
        
        now = time.time()
        if(self.last_modal_time == None):
            self.last_modal_time = now - UPDATE_DELAY
        dt = now - self.last_modal_time
        self.last_modal_time = now
        
        if event.type == 'ESC':
            # Restore hand rotations
            if(self.use_right_hand):
                applyBoneRotations(self.selected_armature, self.r_hand_initial_rotations, try_record=False)
            else:
                applyBoneRotations(self.selected_armature, self.l_hand_initial_rotations, try_record=False)
            return self.cancel(context)
        
        if (event.type == RHAND_ACTIVATION_CHAR or event.type == LHAND_ACTIVATION_CHAR) and event.value == "PRESS":
            n = self.selection_num
            self.removeHandlers()
            self.stop_leap_receiver()
            if(n<0 or n>len(self.selectable_items)):
                self.report({'INFO'}, "No pose selected")
                return {"CANCELLED"}
            else:
                applyPose(armature=self.selected_armature, pose_library_name=self.POSE_LIBRARY_NAME, hand_bone_names=self.HAND_BONE_NAMES, pose_number=n, try_record=True)
                return {"FINISHED"}
        
        dict = self.leap_receiver.getLeapDict()
        if(dict == None):
            print("No dictionary yet...")
            return {"RUNNING_MODAL"}

            
        #print(str(dict))
        p = self.pointable_selector.select(dict)
        #print("Current pointable = " + str(p))
        
        # If the pointable is valid. Calculate the selected value according to its height
        if(p==None):
            self.finger_visible = False
        else:
            self.finger_visible = True

            n_items = len(self.selectable_items)
            
            y = p['tipPosition'][1]
            
            normalized_y = (y - SELECTION_MIN_Y) / (SELECTION_MAX_Y - SELECTION_MIN_Y)
            #self.selection_factor = normalized_y


            #
            # Check for circling gesture to shift the selection window
            p_id = p['id']
            gestures = dict["gestures"]
            found_gesture = None
            for gesture in gestures:
                if(gesture["type"] != "circle"):
                    continue
                if(p_id in gesture["pointableIds"]):
                    found_gesture = gesture
                    break

            if(found_gesture != None):
                USE_RADIUS = False
                if(USE_RADIUS):
                    min_radius = 5
                    max_radius = 50
                    min_speed = 0.5
                    max_speed = 6
                    radius = found_gesture['radius']
                    radius = min(max_radius, max(min_radius, radius))
                    
                    radius_k = (radius - min_radius) / (max_radius-min_radius)
                    radius_k = 1-radius_k
                    #print(" "+str(k))
                    rot_speed = min_speed + (max_speed - min_speed) * radius_k
                    delta_scroll = rot_speed * dt
                else:   #use tangent speed
                    vx,vy,vz = p['tipVelocity']
                    velocity = mathutils.Vector((vx,vy,vz))
                    linear_velocity = velocity.length
                    delta_scroll = 0.02 * linear_velocity * dt

                    
                normal = gesture["normal"]
                if(normal[2] < 0):
                    clockwise = True
                    self.selection_window_first_item += delta_scroll
                else:
                    clockwise = False
                    self.selection_window_first_item -= delta_scroll
                    
                    
                #print("Circling. Clockwise="+str(clockwise))
                if(self.selection_window_first_item<0):
                    self.selection_window_first_item = 0
                max_window_start = max(0, n_items - MAX_DISPLAY_ELEMENTS)
                if(self.selection_window_first_item>max_window_start):
                    self.selection_window_first_item = max_window_start
                #print("self.selection_window_first_item set at " + str(self.selection_window_first_item))
            else:
                # if not circle was detected, normally update the selection factor
                self.selection_factor = normalized_y
                pass
            
            
            #
            # If the finger is above or below the selection y range, scroll it.
            SCROLL_MAX_SPEED = 12
            SCROLL_ZONE_SIZE = 0.3 # in normalized space, for how much the finger will trigger the scroll up/down
            scroll_factor = 0.0
            if(normalized_y > 1.0 and normalized_y < (1.0 + SCROLL_ZONE_SIZE)):
                scroll_factor = (normalized_y - 1.0) / SCROLL_ZONE_SIZE
            elif(normalized_y < 0.0 and normalized_y > (0.0 - SCROLL_ZONE_SIZE)):
                scroll_factor = (normalized_y) / SCROLL_ZONE_SIZE

            if(scroll_factor != 0.0):
                delta_scroll = - scroll_factor * SCROLL_MAX_SPEED * dt
                #print("Scrolling f "+str(scroll_factor) + " -> " + str(delta_scroll))
                self.selection_window_first_item += delta_scroll
            
                if(self.selection_window_first_item<0):
                    self.selection_window_first_item = 0
                max_window_start = max(0, n_items - MAX_DISPLAY_ELEMENTS)
                if(self.selection_window_first_item>max_window_start):
                    self.selection_window_first_item = max_window_start

            
            #
            # Finally, if the finger is in the selection y range, calculate the selection number and apply the current pose
            if(self.selection_factor >= 0 and self.selection_factor < 1):

                first_id = int(self.selection_window_first_item)
                n_items_left = n_items - first_id
                n_items_left = min(n_items_left, MAX_DISPLAY_ELEMENTS)
                last_id = first_id + n_items_left

                self.selection_num = (int)((last_id-first_id) * (1-self.selection_factor))
                self.selection_num += first_id
                #print("Selected_item = " + str(self.selection_num))
                applyPose(armature=self.selected_armature, pose_library_name=self.POSE_LIBRARY_NAME, hand_bone_names=self.HAND_BONE_NAMES, pose_number=self.selection_num, try_record=False)



        # Force interactive redraw
        if(bpy.context.area):
            bpy.context.area.tag_redraw()
        
        return {"RUNNING_MODAL"}
    

    def cancel(self, context):
        self.stop_leap_receiver()
        self.removeHandlers()        
        return {'CANCELLED'}


    def stop_leap_receiver(self):
        if(self.leap_receiver != None):
            print("Releasing LeapReceiver singleton...")
            LeapReceiver.releaseSingleton()
            #self.leap_receiver.terminate()
            #self.leap_receiver.join()
            #del(self.leap_receiver)
            self.leap_receiver = None
    

    FONT_MAX_SIZE = 24
    FONT_RGBA = (0.8, 0.8, 0.8, 0.9)
    SELECTED_FONT_RGBA = (0.8, 0.1, 0.2, 0.9)
    ICON_SIZE = 64
    BACKGROUND_COLOR = (0.15,0.1,0.1,0.9)

    def draw_callback_px(self, context):
        if(self.execution_active_space != None):
            if(not (self.execution_active_space.as_pointer() == context.area.spaces.active.as_pointer()) ):
                #print("Skipping...")
                return

        #self.draw_callback_px_moving_text(context)
        self.draw_callback_px_moving_arrow(context)


    def draw_callback_px_moving_text(self, context):
        n_items = len(self.selectable_items)
        
        #
        # Draw pointing finger
        bgl.glPushClientAttrib(bgl.GL_CURRENT_BIT|bgl.GL_ENABLE_BIT)
        
        pos_y = (context.region.height / 2) - (self.ICON_SIZE / 2)
        
        # transparence
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        if(not self.finger_visible):
            pos_x = (context.region.width / 2) + self.ICON_SIZE
            bgl.glRasterPos2f(pos_x, pos_y)
            bgl.glDrawPixels(self.ICON_SIZE, self.ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, icon_pointing_finger_missing)
        else:
            pos_x = (context.region.width / 2)
            bgl.glRasterPos2f(pos_x, pos_y)
            bgl.glDrawPixels(self.ICON_SIZE, self.ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, icon_pointing_finger)

        bgl.glPopClientAttrib()
        
        self.draw_bg(context)
        
        #
        # Draw entries
        draw_height = context.region.height * 0.8
        n_items = len(self.selectable_items)
        font_size = draw_height / n_items
        font_size = min(font_size, self.FONT_MAX_SIZE)
        text_height = n_items * font_size

        text_lower_y = (context.region.height / 2)
        text_higher_y = text_lower_y + text_height

        #
        bgl.glPushAttrib(bgl.GL_CLIENT_ALL_ATTRIB_BITS)

        blf.size(0, font_size, 72)
        #print(self.selection_factor)
        pos_x = 0
        
        REVERSE = False
        if(REVERSE):
            pos_y = text_lower_y - text_height + self.selection_factor * (text_height) + (self.ICON_SIZE / 4)
        else:
            pos_y = text_lower_y + (1-self.selection_factor) * (text_higher_y - text_lower_y) - (self.ICON_SIZE / 4)


        for item_id in range(0,n_items):
            item = self.selectable_items[item_id]
            
            item_w,item_h = blf.dimensions(0, item)
            pos_x = (context.region.width / 2) - item_w
            
            blf.position(0, pos_x, pos_y, 0)
            
            if(item_id == self.selection_num):
                bgl.glColor4f(*self.SELECTED_FONT_RGBA)
            else:
                bgl.glColor4f(*self.FONT_RGBA)

            blf.draw(0, item)
            if(REVERSE):
                pos_y += font_size
            else:
                pos_y -= font_size
                

            
        bgl.glPopAttrib()
       
        pass


    def draw_callback_px_moving_arrow(self, context):
        #print("drawing")
        
        n_items = len(self.selectable_items)
        n_items_to_display = min(MAX_DISPLAY_ELEMENTS, len(self.selectable_items))
        text_area_height = n_items_to_display * self.FONT_MAX_SIZE
        font_size = self.FONT_MAX_SIZE
        #print("Font_size = " + str(font_size))
        #
        

        text_top_y = (context.region.height * 0.9)
        text_bottom_y = text_top_y - text_area_height

        
        #bgl.glPushClientAttrib(bgl.GL_CURRENT_BIT|bgl.GL_ENABLE_BIT)
        bgl.glPushAttrib(bgl.GL_CLIENT_ALL_ATTRIB_BITS)

        blf.size(0, font_size, 72)


        #
        # Draw background
        max_text_width = 0
        for item in self.selectable_items:
            item_w,item_h = blf.dimensions(0, item)
            if(item_w > max_text_width):
                max_text_width = item_w

        self.draw_bg(context=context, width=max_text_width*1.5)


        #
        # Draw entries
        pos_x = 0
        pos_y = text_top_y - font_size        
        pos_y += self.selection_window_first_item * self.FONT_MAX_SIZE
                
        for item_id in range(0,len(self.selectable_items)):
            item = self.selectable_items[item_id]
            
            item_w,item_h = blf.dimensions(0, item)
            pos_x = (context.region.width / 2) - item_w
            
            blf.position(0, pos_x, pos_y, 0)
            
            if(item_id == self.selection_num):
                bgl.glColor4f(*self.SELECTED_FONT_RGBA)
            else:
                bgl.glColor4f(*self.FONT_RGBA)

            blf.draw(0, item)            
            pos_y -= font_size

        #blf.position(0, 0, 0, 0)
        #blf.draw(0, "Test00")            
            
        bgl.glPopAttrib()
        #bgl.glPopClientAttrib()
                
        #
        # Draw pointing finger
        bgl.glPushClientAttrib(bgl.GL_CURRENT_BIT|bgl.GL_ENABLE_BIT)
        
        # transparence
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        
        if(not self.finger_visible):
            pos_x = (context.region.width / 2) + self.ICON_SIZE
            pos_y = text_top_y - self.ICON_SIZE
            bgl.glRasterPos2f(pos_x, pos_y)
            bgl.glDrawPixels(self.ICON_SIZE, self.ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, icon_pointing_finger_missing)
        else:
            pos_x = (context.region.width / 2)
            pos_y = text_bottom_y + self.selection_factor * text_area_height - (self.ICON_SIZE/2)
            bgl.glRasterPos2f(pos_x, pos_y)
            bgl.glDrawPixels(self.ICON_SIZE, self.ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, icon_pointing_finger)

        bgl.glPopClientAttrib()

        pass

    
    pass



    def draw_bg(self, context, width):
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        bgl.glBegin(bgl.GL_QUADS)
        
        top_y = context.region.height * 0.9
        bottom_y = top_y - (min(MAX_DISPLAY_ELEMENTS,len(self.selectable_items)) * self.FONT_MAX_SIZE)
        #bottom_y -= self.FONT_MAX_SIZE / 3  # move down a bit more to cover descending fonts
        right_x = context.region.width / 2
        left_x = right_x - width
        #right_x = context.region.width / 2
                
        bgl.glVertex2f(left_x,bottom_y)
        bgl.glColor4f(*self.BACKGROUND_COLOR)
        bgl.glVertex2f(right_x, bottom_y)
        bgl.glVertex2f(right_x, top_y)
        bgl.glVertex2f(left_x, top_y)
        
        bgl.glEnd()



def applyPose(armature, pose_library_name, hand_bone_names, pose_number, try_record):
    #print("Applying pose " + str(n))
    #bpy.ops.poselib.apply_pose(n)
    pose_name = bpy.data.actions[pose_library_name].pose_markers[pose_number].name
    #print("Applying pose " + str(pose_number) + " " +pose_name)
    poses_data = getPoseLibraryData(pose_library_name, hand_bone_names)
    bones_data = poses_data[pose_name]
    applyBoneRotations(armature, bones_data, try_record)



def applyBoneRotations(armature, rotations, try_record):
    """Takes as input the reference to the armature, and a dictionary with keys=bone_names, and values a 4-element list woth the quaternion values [w x y z]."""

    bones = armature.pose.bones
    for bone_name in rotations:
        #print("Applying " + bone_name)
        # e.g. bpy.data.objects['Human1-mhxrig-expr-advspine'].pose.bones['Finger-2-1_L'].rotation_quaternion = 1,0,0,0
        bones[bone_name].rotation_quaternion = rotations[bone_name]

        #print("Checking rec for "+bone_name)
        # RECORD (eventually)
        if(try_record and bpy.context.scene.tool_settings.use_keyframe_insert_auto):
            print("Recording keyframe for "+bone_name)
            frame = bpy.context.scene.frame_current
            bones[bone_name].keyframe_insert(data_path="rotation_quaternion", frame=frame)



def retrieveBoneRotations(armature, bone_names):
    """Takes as input the reference to the armature and the list of names of the bones to retrieve.
    Returns a dictionary with keys=bone_names, and values a 4-element list with the quaternion values [w x y z]."""

    out = {}
    
    bones = armature.pose.bones
    for bone in bones:
        bone_name = bone.name
        #print("Applying " + bone_name)
        # e.g. bpy.data.objects['Human1-mhxrig-expr-advspine'].pose.bones['Finger-2-1_L'].rotation_quaternion = 1,0,0,0
        w,x,y,z = bone.rotation_quaternion
        out[bone_name] = [w,x,y,z]
    
    return out




def getPoseLibraryData(pose_library_name, bones):
    """Returns a dictionary. Keys are the pose names. Values are the pose data.
    Each value will be dictionary with bone names as keys, and the a list of the 4 rotation elements as value: "bone_name" -> [w x y z]
    Only the bones specified in the bones parameter will be considered.
    For bones specified in the list but missing in the action data, rotation will be defaulted to identity [1 0 0 0].
    """
    
    # Prepare the output dictionary.
    # key=action_name, data=dict of rotations
    out = {}
    
    library_action = bpy.data.actions[pose_library_name]
    
    # Everything at identity by default
    for marker in library_action.pose_markers:
        pose_name = marker.name
        frame_number = marker.frame
        #print("--> " + pose_name + " @ " + str(frame_number))
        #prepare the dict of rotations.
        # key = bone_name, data=quaternion_elements
        dict_of_rotations = {}
        for bone in bones:
            dict_of_rotations[bone] = [ 1, 0, 0, 0 ]
            
        # Insert the bone->rotation dictionary into the main output dict
        out[pose_name] = dict_of_rotations

    # e.g. pose.bones["Head"].rotation_quaternion
    pattern = re.compile('pose\.bones\[\"(.+)\"\]\.rotation_quaternion') #  "pose\.bones\[\"(+*)\"\]\..+")

        
    # Now really parse the data
    for fcurve in library_action.fcurves:
        res = pattern.match(fcurve.data_path)
        if(res == None):
            continue

        bone_name = res.group(1)
        if(bone_name in bones):
            for kf in fcurve.keyframe_points:
            #kf = fcurve.keyframe_points[frame_number]
                t,val = kf.co
                #print("t="+str(t))
                # In a library, poses are indexed form 0, but keyframes start form 1
                pose_number = int(t) -1
                
                assert pose_number < len(library_action.pose_markers)
                marker = library_action.pose_markers[pose_number]
                pose_name = marker.name
                assert(pose_name in out)
                dict_of_rotations = out[pose_name]
                
                #print("Inserting for pose "+pose_name+"\tbone "+bone_name+"\trot_element " + str(fcurve.array_index))
                # the data_index will be between 0 and 3, indicating the quaternion component wxyz
                dict_of_rotations[bone_name][fcurve.array_index] = val
    
        
    return out




def loadImageEventually(image_file):
    """Load the image from the 'images' directory relative to the scene.
        If the image is already loaded just return it.
    """

    # list the names of already loaded images
    loaded_images_files = [img.name for img in bpy.data.images]
    
    scene_dir = os.path.dirname(bpy.data.filepath)
    
    if(not image_file in loaded_images_files):
        print("Loading image from '" + image_file + "'")
        image = image_utils.load_image(imagepath=image_file, dirname=scene_dir+"/images/")
    else:
        print("Image '" + image_file + "' already loaded. Skipping...")
        image = bpy.data.images[image_file]
    return image



# I've got here the possible values for the 'name' parameter for the KeyMap
# https://svn.blender.org/svnroot/bf-extensions/contrib/py/scripts/addons/presets/keyconfig/blender_2012_experimental.py
#EDIT_MODES = ['Object Mode', 'Pose']
EDIT_MODES = ['Pose']

# store keymaps here to access after registration
hand_selection_keymap_items = []

icon_pointing_finger = None
icon_pointing_finger_missing = None


def register():
    global icon_pointing_finger
    global icon_pointing_finger_missing


    bpy.utils.register_class(HandShapeSelector)
    
    #
    # LOAD ICONS
    image = loadImageEventually(image_file="1-finger-point-left-icon-red.png")
    icon_pointing_finger = bgl.Buffer(bgl.GL_FLOAT, len(image.pixels), image.pixels)
    image = loadImageEventually(image_file="1-finger-point-left-icon-red-missing.png")
    icon_pointing_finger_missing = bgl.Buffer(bgl.GL_FLOAT, len(image.pixels), image.pixels)

    
    
    # handle the keymap
    wm = bpy.context.window_manager
    
    km = wm.keyconfigs.addon.keymaps.new(name='Pose', space_type='EMPTY')
    kmi = km.keymap_items.new(HandShapeSelector.bl_idname, RHAND_ACTIVATION_CHAR, 'PRESS', ctrl=True, shift=False)
    kmi.properties.use_right_hand = True
    hand_selection_keymap_items.append((km, kmi))

    kmi = km.keymap_items.new(HandShapeSelector.bl_idname, LHAND_ACTIVATION_CHAR, 'PRESS', ctrl=True, shift=False)
    kmi.properties.use_right_hand = False
    #kmi.properties.isRotating = True
    #kmi.properties.translationUseFinger = True
    hand_selection_keymap_items.append((km, kmi))
 
    pass

def unregister():
    global icon_pointing_finger
    global icon_pointing_finger_missing

    # handle the keymap
    for km, kmi in hand_selection_keymap_items:
        km.hand_selection_keymap_items.remove(kmi)
    hand_selection_keymap_items.clear()

    print("ok")

    icon_pointing_finger = None
    icon_pointing_finger_missing = None

    bpy.utils.unregister_class(HandShapeSelector)
    pass

if __name__ == "__main__":
    register()
