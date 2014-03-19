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


# v01 - First test. Receiving and printing data with message reception in modal() function. But very sloooow.
# v02 - Implemented object position editing. Definitely too slow.
# v03 - Converted reception to a separate thread. Tested Leap application crash and disconnection possibilities. Now run smoothly :-) Pretty stable in closing sockets properly.
# v04 - Implemented translation with palm. Ready to get view matrices to align translation with point of view.
# v05 - Found View_3D view_transform matrix to invert and align movement to screen.
# v06 - implemented average finger for translation
# v07 - Implemented a conservative single finger selection
# v08 - Cleaned up code. Pointer selection logic out of translator. Ready to proceed with rotation.
# v09 - Yeah. Both translation and rotation are implemented. To improve the activation system now.
# v10 - Yo. Implemented dynamic translation adjustment according to the camera distance.
# v11 - Faster activation mode. G,R,T key for Grab, Rotation and both together immediate activation.
# v12 - Added also both translation and rotation by hand palm
# v13 - implemented rotation by finger gesture.... but is crap.
# v14 - Improved translation sensibility: now is relative to the camera and object current position. So sensibility adjust during movement. Also Removed MESH constraint for object selection.
# v15 - Included explicit handling of MakeHuman hands (in IK mode)
# v16 - Fixed control of PoseBones.
# v17 - First swivel movement to finger circles works.
# v18 - Cleaned up lot of code. Finger or palm use is now selectable as property, hence usable is keymapping. Merged Hand and Finger rotators in one class. Swivel rotation implemented for both arms.
# v19 - Fixed Swivel angle restore()
# v20 - working on "from above shoulders" direct hand control
# v21 - Direct two hands control ok.
# v22 - Implemented restore for Direct hands control. Inserted a filter to avoid capturing the head-as-hand.
# v23 - Added macro boolean to use assistive Leap UDP forwarder instead of direct websocket connection. With SDK v0.8 repeadetly connecting and disconnecting form the Leap makes the leapd daemon process crash.
# v24 - Applied proper offset to compensate Leap measurement of palm center and MakeHuman positioning of wrist (10 cm distance ca.)
# v25 - Implemented direct mirrored rotation of hands. Optionally available a mirroring also of the translation.
# v26 - Added MakeHuman Tools to perform several tasks. Added transparent-red target objects for tests.
# v27-v32 - Some fixes + implemented routines for usr study
# v33 - Fixed Target box shape.
# v34 - Fixed angle comparison. Angles are "similar" also near 6.28 rads!
# v35 - Merged MH Tools scripts with Experiment tools. Finished setup of scenes 1 to 7
# v36-v37 - Brick cone increased size. Fine tuned thresholds for experiments. Elbow slower. Tuned cameras position. Used for 1st experiment.
# v38 - Added ColorTargets script to color objects without using a direct invocation form the LeapModal Operator. So now we can log keys and color objects also using plain mouse+keyboard control.
# v39 - Removed ColorTarget coloring form main LeapModalController. So it becomes independent from the specific experiments.
# v40 - Cleanup of much unused code
# v41 - reinserted two hands capturing mode, extended for both first person and mirrored modes
# v42 - Added GPLv3 header and Blender plugin infos.
# 1.0 - First public release

bl_info = {
    "name": "Leap Modal Controller",
    "author": "Fabrizio Nunnari",
    "version": (1,0),
    "blender": (2, 66, 0),
    "location": "Search > Leap Modal Control",
    "description": "Uses the Leap Motion to edit objects position in space",
    "warning": "",
    "wiki_url": "http://",
    "tracker_url": "https://",
    "category": "Animation"}

"""
    This script enables using the Leap Motion device to edit objects location and orientation in space.
    It also allows quickly editing Hands and Elbow position in MakeHuman characters.
    """

# From this module
from .LeapReceiver import LeapReceiver
from .LeapReceiver import PointableSelector
from .LeapReceiver import HandSelector
from .LeapReceiver import CircleGestureSelector


# Blender specific
import bpy
from bpy.props import * # for properties
import mathutils
# for overlay rendering
import bgl
import blf


# Python standard
import threading
import json
from math import radians    # to convert degrees to radians
from math import pi
from math import sqrt
#import time
import re


# Delay between TIMER events when entering the modal command mode. In seconds.
UPDATE_DELAY = 0.04


# Simple enumeration for hand-specific operations
class Hand:
    RIGHT = 1
    LEFT = 2

#
#
#

# This is (ideally) the distance, in millimiters, that a user has to span in real space to have an object in 3D span the width of the screen
LEAP_HORIZ_SPAN_MM = 400

#
#
#
# This is the transofrmation matrix that might be applied when using the Lep in "Longitudinal mode"
long_leap_to_blender_rotmat = mathutils.Matrix.Rotation(0, 3, 'X')
long_leap_to_blender_rotmat[0] = [0,0,-1]
long_leap_to_blender_rotmat[1] = [0,1,0]
long_leap_to_blender_rotmat[2] = [1,0,0]

rot_long_leap_to_blender_rotmat = long_leap_to_blender_rotmat.to_quaternion()

#
#
#

class ObjectTranslator:
    
    # The object that will be translated by the Leap
    target_object = None
    
    #The location taken as base to offset the object with the Leap
    target_start_location = None
    
    # Pointable location at the start of the operation
    pointable_start_location = None
    
    
    # If True, a pointable position will be used to translate the object, otherwise the hand palm center
    use_finger = False
    
    # to move objects with a pointable tip
    pointable_selector = PointableSelector()
    
    # to move objects with the hand palm center
    hand_selector = HandSelector()
    
    # if True, the y component of delta movement will be reverted,
    # so that moving the hand towards the screen will cause the object to move closer to the camera.
    mirror_y = False
    
    # The Pose Bone transformation matrix relative to the armature root
    posebone_matrix = None

    # If true, we assume you are using the Leap longitudinally
    longitudinal_mode = False
    
    def useFinger(self, b):
        self.use_finger = b
        print("USE_FINGER for TR " + str(b))
    
    def setMirror(self, b):
        self.mirror_y = b
    
    def setLongitudinalMode(self, b):
        self.longitudinal_mode = b
    
    def setTarget(self, obj):
        self.target_object = obj
        # Special treatment for PoseBones
        if(self.target_object.__class__ == bpy.types.PoseBone):
            self.posebone_matrix = self.target_object.matrix * self.target_object.matrix_basis.inverted()
            print("Saved matrix for PoseBone " + str(self.target_object.__class__))
        else:
            print("Resetting matrix for PoseBone")
            self.posebone_matrix = None
    
    def setViewMatrix(self, mat):
        self.view_matrix = mat
    
    def reset(self):
        self.target_start_location = mathutils.Vector(self.target_object.location)
        self.pointable_start_location = None
    
    def restore(self):
        self.target_object.location = self.target_start_location
    
    def setTargetPositionHandSpace(self, x, y, z):
        pos = mathutils.Vector((x, y, z))
        new_loc = self.handPosToTargetSpace(pos)
        if(self.target_object != None):
            self.target_object.location = new_loc
    
    def handPosToTargetSpace(self, pos):
        if(self.pointable_start_location == None):
            self.pointable_start_location = pos
        
        # difference in pointable position
        delta = [ pos[i] - self.pointable_start_location[i] for i in range(0,3)]
        
        # Here we want to scale the delta according to the distance of the object from the camera.
        # We don't consider the field of view (yet)
        cam_pos = self.view_matrix.inverted().to_translation()
        #distance = (cam_pos - self.target_start_location).length
        distance = (cam_pos - self.target_object.location).length
        #print("cam_pos " + str(cam_pos) + "\tdist=" + str(distance))
        s = distance / LEAP_HORIZ_SPAN_MM
        
        # Scale the delta
        delta = [ delta[i] * s for i in range(0,3)]
        
        # Convert to vector
        delta = mathutils.Vector(delta)
        
        # Eventually, adapt for logitudinal usage
        if(self.longitudinal_mode):
            delta = long_leap_to_blender_rotmat * delta
        
        # rotate the delta vector according to the view matrix
        delta = self.view_matrix.to_quaternion().inverted() * delta
        
        #print("palm delta=" + str(delta))
        
        if(self.mirror_y):
            delta.y = - delta.y
        
        # If it is a PoseBone, must invert the parent matrix
        if(self.posebone_matrix != None):
            delta = self.posebone_matrix.inverted().to_quaternion() * delta
        
        new_loc = [ self.target_start_location[i] + (delta[i]) for i in range(0,3)]
        #print("start_loc" + str(self.target_start_location))
        #print("new_loc=" + str(new_loc))
        
        return new_loc
    
    
    def update(self, leap_dict):
        """Takes as input the python dict with the leap infomation"""
        
        
        if(self.use_finger):
            pointable = self.pointable_selector.select(leap_dict)
            if(pointable == None):
                return
            
            pos = mathutils.Vector(pointable["tipPosition"])
        else:
            hand = self.hand_selector.select(leap_dict)
            if(hand == None):
                return
            
            pos = mathutils.Vector(hand["palmPosition"])


        new_loc = self.handPosToTargetSpace(pos)


        #print("obj=" + str(obj))
        if(self.target_object != None):
            self.target_object.location = new_loc
    
        #
        # RECORD (eventually)
        if(bpy.context.scene.tool_settings.use_keyframe_insert_auto):
            frame = bpy.context.scene.frame_current
            self.target_object.keyframe_insert(data_path="location", frame=frame)


        pass # end update

#
#
#

class ObjectRotator:
    
    # The object that will be translated by the Leap
    target_object = None
    
    #The rotation taken as base to offset the object with the Leap
    target_start_rotation = None    # as quaternion
    
    # Pointable start direction and Pointable selector
    pointable_start_direction = None
    pointable_selector = PointableSelector()
    
    # Palm start rotation and hand selector
    palm_start_rotation = None
    hand_selector = HandSelector()
    
    # Determines during update() whether to use a pointable or the hand palm
    use_finger = False
    
    # If the target is a bone, we need to invert some matrix data during update.
    posebone_matrix = None
    
    # If true, we assume you are using the Leap longitudinally
    longitudinal_mode = False
    
    
    def setTarget(self, obj):
        self.target_object = obj
        # Special treatment for PoseBones
        if(self.target_object.__class__ == bpy.types.PoseBone):
            self.posebone_matrix = self.target_object.matrix * self.target_object.matrix_basis.inverted()
        else:
            self.posebone_matrix = None
    
    
    def setViewMatrix(self, mat):
        self.view_matrix = mat
    
    
    def useFinger(self, b):
        self.use_finger = b


    def setLongitudinalMode(self, b):
        self.longitudinal_mode = b


    def reset(self):
        # Sorry, I have to force the reotation mode to Quaternion.
        self.target_object.rotation_mode = 'QUATERNION'
        self.target_start_rotation = mathutils.Quaternion(self.target_object.rotation_quaternion)
        self.palm_start_rotation = None
    
    def restore(self):
        self.target_object.rotation_quaternion = self.target_start_rotation
    
    def update(self, leap_dict):
        
        if(self.use_finger):
            pointable = self.pointable_selector.select(leap_dict)
            if(pointable == None):
                return
            
            dir = mathutils.Vector(pointable["direction"])
            
            if(self.pointable_start_direction == None):
                self.pointable_start_direction = mathutils.Vector(dir)
            
            # Rotation with respect to the original pointable direction
            delta_rot = self.pointable_start_direction.rotation_difference(dir)
        
        else:   # Use hand palm
            
            hand = self.hand_selector.select(leap_dict)
            if(hand == None):
                return
            
            h_x = mathutils.Vector(hand["direction"])
            h_y = mathutils.Vector(hand["palmNormal"])
            h_z = h_x.cross(h_y)
            
            # Build the rotation matrix using the data of the 3 orthogonal vectors (hand direction, palm normal, and their outgoing cross product)
            rot_mat = mathutils.Matrix.Rotation(0, 3, 'X')
            rot_mat[0][0], rot_mat[1][0], rot_mat[2][0] = h_x[0], h_x[1], h_x[2]
            rot_mat[0][1], rot_mat[1][1], rot_mat[2][1] = h_y[0], h_y[1], h_y[2]
            rot_mat[0][2], rot_mat[1][2], rot_mat[2][2] = h_z[0], h_z[1], h_z[2]


            # Eventually, adapt for logitudinal usage
            if(self.longitudinal_mode):
                rot_mat = long_leap_to_blender_rotmat * rot_mat


            rot = rot_mat.to_quaternion()
            
            if(self.palm_start_rotation == None):
                self.palm_start_rotation = mathutils.Quaternion(rot)
            
            
            # Rotation with respect to the original palm rotation
            delta_rot = rot * self.palm_start_rotation.inverted()
        
        # rotate the delta vector according to the view matrix
        cam_rot = self.view_matrix.to_quaternion()
        delta_rot = cam_rot.inverted() * delta_rot * cam_rot
    
        # If it is a PoseBone, must cancel the skeletal rotation
        if(self.posebone_matrix != None):
            delta_rot = self.posebone_matrix.inverted().to_quaternion() * delta_rot * self.posebone_matrix.to_quaternion()
    
    
        # New rotation
        new_rot = delta_rot * self.target_start_rotation
    
        #Finally put it in there
        if(self.target_object != None):
            self.target_object.rotation_quaternion = new_rot
    
        #
        # RECORD (eventually)
        if(bpy.context.scene.tool_settings.use_keyframe_insert_auto):
            frame = bpy.context.scene.frame_current
            self.target_object.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    

        pass # end update


#
#
#


SWIVEL_ROTATION_SPEED = 0.2   # radians per second

class FingerCircleElbowSwivelRotator:
    """WARNING: This works only on MakeHuman characters.
        Will enable users to rotate the human elbow with circle gestures.
        Beware, it is initialized with the ID on the hand arm to rotate. The name
        of the bones to take from the armature are stored statically in this class.
        """
    
    
    # The MakeHuman armature that will be analyses to adjust the elbow
    target_object = None
    
    # The hand identifier (Instance of class Hand defined above)
    target_hand = None
    
    # to detect circles
    gesture_selector = CircleGestureSelector()
    
    # Position of the shoulder in space. Updated at reset.
    shoulder_location = None
    
    # Position of the wrist in space. Updated at reset.
    wrist_location = None
    
    # Location of the elbow at last computation. Initialized at reset.
    elbow_last_location = None
    
    # Initial location of the elbow control
    elbow_control_initial_location = None
    
    def setTarget(self, obj):
        self.target_object = obj
    
    def setTargetHand(self, hand):
        self.target_hand = hand
    
    
    def reset(self):
        if(self.target_object == None):
            return
    
        # Prepare a suffix for the bone names
        H = None
        if(self.target_hand == Hand.RIGHT):
            H = "R"
        elif(self.target_hand == Hand.LEFT):
            H = "L"
        else:
            assert False
    
        #print("SWIVEL "+H)
        
        
        SHOULDER_BONE = "UpArmVec_" + H #"DfmUpArm1_L"
        ELBOW_BONE = "LoArmVec_" + H # "DfmLoArm1_L"
        WRIST_BONE = "Palm-1_" + H
        self.ELBOW_CONTROL = "ElbowPT_" + H
        
        
        print("STORING ELBOW CONTROLLER")
        self.elbow_control_initial_location = mathutils.Matrix(self.target_object.pose.bones[self.ELBOW_CONTROL].matrix)
        
        
        # Retrieve the key points of the arm
        self.shoulder_location = self.target_object.pose.bones[SHOULDER_BONE].matrix.to_translation()
        self.wrist_location = self.target_object.pose.bones[WRIST_BONE].matrix.to_translation()
        self.elbow_last_location = self.target_object.pose.bones[ELBOW_BONE].matrix.to_translation()
        
        # According to the elbow position, calculate the position of the elbow controller
        # Its the position of the elbow, for the moment
        self.target_object.pose.bones[self.ELBOW_CONTROL].matrix.translation = self.elbow_last_location
    
    
    def restore(self):
        print("RESTORING ELBOW CONTROL")
        self.target_object.pose.bones[self.ELBOW_CONTROL].matrix[:] = self.elbow_control_initial_location[:]
    
    
    last_duration = None
    
    def update(self, leap_dict):
        if(self.target_object == None):
            return
        
        
        gesture = self.gesture_selector.select(leap_dict)
        if(gesture == None):
            #print("NO GES")
            return
        
        duration = int(gesture["duration"])
        
        if(self.last_duration == None):
            self.last_duration = duration
    
        # That's a duplicate msg. Skip
        if(duration == self.last_duration):
            return
    
        self.last_duration = duration
        
        
        # Calculate the vector between the shoulder and the wrist
        rotation_axis = self.wrist_location - self.shoulder_location
        angle = SWIVEL_ROTATION_SPEED * UPDATE_DELAY
        
        normal = mathutils.Vector(gesture["normal"])
        #print("normal="+str(normal))
        if(normal.z > 0):   # cloclwise rotation
            angle = -angle
    
        #
        # Must rotate the elbow location around  the shoulder-wrist axis
        #
        # 1) center the axis on the origin
        # 2) rotate around the computed axis/angle
        # 3) re-translate back in position
        M = mathutils.Matrix.Translation(self.shoulder_location)\
            * mathutils.Matrix.Rotation(angle, 4, rotation_axis)\
            * mathutils.Matrix.Translation(self.shoulder_location).inverted()

        self.elbow_last_location = M * self.elbow_last_location
        self.target_object.pose.bones[self.ELBOW_CONTROL].matrix.translation = self.elbow_last_location

        #
        # Eventually, insert the keyframes
        if(bpy.context.scene.tool_settings.use_keyframe_insert_auto):
            self.target_object.pose.bones[self.ELBOW_CONTROL].keyframe_insert(data_path='location', frame=bpy.context.scene.frame_current)


        pass # end update




#
#
#


leap_to_blender_rotmat = mathutils.Matrix.Rotation(0, 3, 'X')
leap_to_blender_rotmat[0] = [1,0,0]
leap_to_blender_rotmat[1] = [0,0,-1]
leap_to_blender_rotmat[2] = [0,1,0]


leap_to_blender_mirror_rotmat = mathutils.Matrix.Rotation(0, 3, 'X')
leap_to_blender_mirror_rotmat[0] = [1,0,0]
leap_to_blender_mirror_rotmat[1] = [0,0,1]
leap_to_blender_mirror_rotmat[2] = [0,-1,0]


# Offsets to apply to hands
# Calculated cosidering a sitting position with Leap centered more or less at the height of the belly button
# hands (palm pos) in "rest" position are just below the breasts
# Offsets calculated summing the corresponding hands controller offset + the Leap motion real-world hand position offset
# Wrist_R
#Matrix(((-0.1417485922574997, -0.9848122000694275, 0.10025876015424728, -6.943360328674316),
#        (0.9848121404647827, -0.15055248141288757, -0.08647795021533966, 0.8884090185165405),
#        (0.10025879740715027, 0.08647797256708145, 0.991195559501648, 15.048200607299805),
#        (0.0, 0.0, 0.0, 1.0)))

#L_CONTROLLER_POS_OFFSET = mathutils.Vector((4.8884, -6.94336, -2))
#R_CONTROLLER_POS_OFFSET = mathutils.Vector((-4.8884, -6.94336, -2))

#L_CONTROLLER_POS_OFFSET = mathutils.Vector((4.8884, -6.3, -2))
#R_CONTROLLER_POS_OFFSET = mathutils.Vector((-4.8884, -6.3, -2))
L_CONTROLLER_POS_OFFSET = mathutils.Vector((4.0, -6.1, -2))
R_CONTROLLER_POS_OFFSET = mathutils.Vector((-4.0, -6.1, -2))


# We consider that, when the hand is open, the palm center is in fact calculated very close to the middle finger base.
#>>> bpy.context.selected_pose_bones[0].name
#'DfmHand_L'
# >>> bpy.context.selected_pose_bones[0].length
# 1.1286101501538919
#WRIST_TO_HAND_OFFSET = mathutils.Vector((0,1.1236,0))
WRIST_TO_HAND_OFFSET = mathutils.Vector((0,1.0,0))


class MakeHumanHandsDirectController:
    
    WRIST_BONE_L = "Wrist_L"
    WRIST_BONE_R = "Wrist_R"
    
    LEAP_BASE_HEIGHT = 1.20
    
    isMirrored = False
    
    target_armature = None
    
    r_wrist_initial_rot = None
    r_wrist_initial_loc = None
    l_wrist_initial_rot = None
    l_wrist_initial_loc = None
    
    l_wrist_local_mat = None
    r_wrist_local_mat = None
    
    l_hand_id = None
    r_hand_id = None
    
    def setTargetArmature(self, a):
        self.target_armature = a
    
    def setMirrored(self, b):
        self.isMirrored = b
    
    def reset(self):
        
        r_wrist = self.target_armature.pose.bones[self.WRIST_BONE_R]
        self.r_wrist_local_mat = r_wrist.matrix * r_wrist.matrix_basis.inverted()
        
        l_wrist = self.target_armature.pose.bones[self.WRIST_BONE_L]
        self.l_wrist_local_mat = l_wrist.matrix * l_wrist.matrix_basis.inverted()
        
        self.r_wrist_initial_rot = r_wrist.rotation_quaternion
        self.r_wrist_initial_loc = r_wrist.location
        self.l_wrist_initial_rot = l_wrist.rotation_quaternion
        self.l_wrist_initial_loc = l_wrist.location
        
        self.l_hand_id = None
        self.r_hand_id = None
        pass
    
    def restore(self):
        self.target_armature.pose.bones[self.WRIST_BONE_R].rotation_quaternion = self.r_wrist_initial_rot
        self.target_armature.pose.bones[self.WRIST_BONE_R].location = self.r_wrist_initial_loc
        self.target_armature.pose.bones[self.WRIST_BONE_L].rotation_quaternion = self.l_wrist_initial_rot
        self.target_armature.pose.bones[self.WRIST_BONE_L].location = self.l_wrist_initial_loc
        pass
    
    def update(self, leap_dict):
        
        if(not 'hands' in leap_dict):
            return None
        
        # Infer which hand is left and which is right
        hands = leap_dict["hands"]
        n_hands = len(hands)
        if(n_hands > 2):
            #print("Too may hands: " + str(n_hands))
            
            # Re-sort according to the y value of the palmPosition
            hands.sort(key=lambda h: mathutils.Vector(h["palmPosition"]).length )
            n_hands_to_keep = min(n_hands,2)
            hands[:] = hands[0:n_hands_to_keep-1]
        
        n_hands = len(hands)
        
        assert n_hands <= 2
        
        # Check that the previously detected IDs are still valid
        if(self.l_hand_id != None):
            found = False
            for h in hands:
                if(self.l_hand_id == h["id"]):
                    found = True
                    break
            if(not found):
                self.l_hand_id = None
        
        if(self.r_hand_id != None):
            found = False
            for h in hands:
                if(self.r_hand_id == h["id"]):
                    found = True
                    break
            if(not found):
                self.r_hand_id = None
        
        #print("--> LEFT ID=" + str(self.l_hand_id) + "\tRIGHT ID=" + str(self.r_hand_id))
        
        
        # First guess. If there are two hands, use the position to infer left and right
        if(n_hands == 2):
            hand0_id = hands[0]["id"]
            hand1_id = hands[1]["id"]
            
            # If no hands were previously identified
            if(self.l_hand_id == None and self.r_hand_id == None):
                hand0_pos = mathutils.Vector(hands[0]["palmPosition"])
                hand1_pos = mathutils.Vector(hands[1]["palmPosition"])
                
                if(hand0_pos.x > hand1_pos.x):
                    self.r_hand_id = hand0_id
                    self.l_hand_id = hand1_id
                else:
                    self.r_hand_id = hand1_id
                    self.l_hand_id = hand0_id
            
            elif(self.l_hand_id == None and self.r_hand_id != None):
                # We already checked that if a hand id is not None, then its still in the list of hands
                # So the hand with None id takes the free index
                if(self.r_hand_id == hand0_id):
                    self.l_hand_id = hand1_id
                else:
                    self.l_hand_id = hand0_id
            elif(self.l_hand_id != None and self.r_hand_id == None):
                if(self.l_hand_id == hand0_id):
                    self.r_hand_id = hand1_id
                else:
                    self.r_hand_id = hand0_id

        #print("LEFT ID=" + str(self.l_hand_id) + "\tRIGHT ID=" + str(self.r_hand_id))
        
        
        #
        # Find the array indices for the hands array corresponding to the desired hands IDs.
        l_hand_index = None
        r_hand_index = None
        
        for i,h in enumerate(hands):
            if(self.l_hand_id == h["id"]):
                l_hand_index = i
            if(self.r_hand_id == h["id"]):
                r_hand_index = i

        # for each hand: if we found the id we also have the array index.
        assert( (self.l_hand_id == None and l_hand_index == None) or (self.l_hand_id != None and l_hand_index != None) )
        assert( (self.r_hand_id == None and r_hand_index == None) or (self.r_hand_id != None and r_hand_index != None) )

        #print("LEFT INDEX=" + str(l_hand_index) + "\tRIGHT INDEX=" + str(r_hand_index))

        if(self.isMirrored):
            hand_ids = [self.r_hand_id, self.l_hand_id]
            hand_indices = [r_hand_index, l_hand_index]
        else:
            hand_ids = [self.l_hand_id, self.r_hand_id]
            hand_indices = [l_hand_index, r_hand_index]

        for hand_id, hand_index, align_angle, wrist_local_mat, WRIST_BONE, CONTROLLER_POS_OFFSET in zip(
                                                                                                        hand_ids,
                                                                                                        hand_indices,
                                                                                                        [-90,90],
                                                                                                        [self.l_wrist_local_mat, self.r_wrist_local_mat],
                                                                                                        [self.WRIST_BONE_L, self.WRIST_BONE_R],
                                                                                                        [L_CONTROLLER_POS_OFFSET, R_CONTROLLER_POS_OFFSET]) :
            
            
            if(hand_id != None):
                hand = hands[hand_index]
                
                # When the hand is straight over the Leap, the resulting quaternion must be Identity.
                # This calc is made in Leap/OpenGL axes space.
                h_z = - mathutils.Vector(hand["direction"])
                h_y = - mathutils.Vector(hand["palmNormal"])
                h_x = h_y.cross(h_z)
                
                # Build the rotation matrix of the hand using the data of the 3 orthogonal vectors (hand direction, palm normal, and their outgoing cross product)
                rot_mat = mathutils.Matrix.Rotation(0, 3, 'X')
                rot_mat[0][0], rot_mat[1][0], rot_mat[2][0] = h_x[0], h_x[1], h_x[2]
                rot_mat[0][1], rot_mat[1][1], rot_mat[2][1] = h_y[0], h_y[1], h_y[2]
                rot_mat[0][2], rot_mat[1][2], rot_mat[2][2] = h_z[0], h_z[1], h_z[2]
                
                
                # Align right hand to screen by rotating of +/- 90 degrees along the Y axis. Use -90 for left hand, 90 for the right one.
                if(self.isMirrored):
                    align_angle = -align_angle
                rot_mat = mathutils.Matrix.Rotation(radians(align_angle), 3, 'Y') * rot_mat
            
                # Convert the rotations in Blender orientation axes
                if(self.isMirrored):
                    rot = (leap_to_blender_mirror_rotmat * rot_mat * leap_to_blender_mirror_rotmat.inverted()).to_quaternion()
                else:
                    rot = (leap_to_blender_rotmat * rot_mat * leap_to_blender_rotmat.inverted()).to_quaternion()

                self.target_armature.pose.bones[WRIST_BONE].rotation_quaternion = rot
                
                pos = mathutils.Vector(hand["palmPosition"])
                # Scale from millimeters to decimeters in MakeHuman space
                pos *= 0.01
                #print("Leap Space: " + str(pos))
                # Rotate axes from OpenGL to Blender
                pos = leap_to_blender_rotmat * pos
                
                if(self.isMirrored):
                    pos.x = -pos.x

                #print("Blender space: " + str(pos))
                # Align the hand position offset to the local hand controller axes
                pos = wrist_local_mat.to_quaternion() * pos
                #print("Wrist space: " + str(pos))

                pos -= wrist_local_mat.to_quaternion() * WRIST_TO_HAND_OFFSET

                # Add the default offset t position the hand in front of the character
                pos += CONTROLLER_POS_OFFSET

                self.target_armature.pose.bones[WRIST_BONE].location = pos

        # RECORD (eventually)
        if(bpy.context.scene.tool_settings.use_keyframe_insert_auto):
            frame = bpy.context.scene.frame_current
            # for the wrists
            for bone_name in [self.WRIST_BONE_L, self.WRIST_BONE_R]:
                #print("Inserting key at frame "+str(frame))
                self.target_armature.pose.bones[bone_name].keyframe_insert(data_path="rotation_quaternion", frame=frame)
                self.target_armature.pose.bones[bone_name].keyframe_insert(data_path="location", frame=frame)
            
            # take care of elbow controllers
            for bone_name in ['ElbowPT_L', 'ElbowPT_R']:
                self.target_armature.pose.bones[bone_name].keyframe_insert(data_path="location", frame=frame)


        pass # end update




#
# OPERATOR: LEAP MODAL
#
class LeapModal(bpy.types.Operator):
    """This is the Blender operator to start the Leap Motion timed modal listening as long as ESC isn't pressed."""
    
    bl_idname = "object.leap_modal"
    bl_label = "Leap Motion Start Net Listener"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
    bl_options = {'REGISTER', 'UNDO'}

    
    isTranslating = BoolProperty(name="translate", description="Palm/Finger movement will translate the object")
    translationUseFinger = BoolProperty(name="translate_use_finger", description="Translation point is taken from a finger instead of hand palm")
    isTranslationMirrored = BoolProperty(name="translate_mirror", description="Whether the translation is mirrored on the y-axis")
    isRotating = BoolProperty(name="rotate", description="Finger movement will rotate the object")
    isElbowSwivelRotating = BoolProperty(name="elbow_swivel_rotate", description="Finger Circle gesture rotates the elbow swivel angle")
    isHandsDirectlyControlled = BoolProperty(name="hands_direct_control", description="Hands position is directly controlled by hands detected in Leap")
    handsMirrorMode = BoolProperty(name="hands_mirror_mode", description="Hands direct control is applied with the 'mirror' metaphor")
    
    targetObjectName = StringProperty(name="target_object_name", description="The name of the object to manipulate. If None, the active object will be used", default="")
    targetPoseBoneName = StringProperty(name="target_posebone_name", description="The name of the posebone to manipulate. If None, the active posebone will be used", default="")
    
    
    # by default we use palm
    translationUseFinger = BoolProperty(name="translate", default=False, description="Finger movement will used to translate the object")
    # by default we use palm
    rotationUseFinger = BoolProperty(name="translate", default=False, description="Finger movement will be used to rotate the object")

    # if True, an overlay will print interaction information during modal functioning.
    drawOverlay = BoolProperty(name="draw_overlay", description="Whether to draw (or not) in overlay the current editing operation")
    
    # Custom string-encoded custom user information. Useful to be set via Keymaps and returned to callbacks.
    userData = StringProperty(name="user_data", default="", description="Custom user data set via Keymaps")
    
    
    # Static attribute. List of callbacks to call when drawing the overlay.
    drawCallbacks = []
    
    # Static attribute. List of callbacks to call when modal is invoked.
    # Elements must be instances of some class declaring the following method signature:
    #     def controllersUpdated(self, leap_modal, context): ...
    modalCallbacks = []
    
    
    
    leap_receiver = None    # The network receiving thread
    
    # Controllers / Updaters
    obj_translator = ObjectTranslator()
    obj_rotator = ObjectRotator()
    elbow_swivel_rotator = FingerCircleElbowSwivelRotator()
    hands_direct_controller = MakeHumanHandsDirectController()
    
    timer = None
    
    
    def __init__(self):
        self._timer = None
        self._draw_handle = None
        pass

    
    def __del__(self):
        # The sock attribute might not have been defined if the command was never run
        if(hasattr(self, 'leap_receiver')):
            self.stop_leap_receiver()
        
        #self.removeHandlers()
        

    def addHandlers(self, context):
        #
        # TIMER
        self._timer = context.window_manager.event_timer_add(UPDATE_DELAY, context.window)

        #
        # DRAW
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context,), 'WINDOW', 'POST_PIXEL')
        if(bpy.context.area):
            bpy.context.area.tag_redraw()



    def removeHandlers(self):
        print("Removing handlers...")
        
        #
        # TIMER
        if(self._timer != None):
            bpy.context.window_manager.event_timer_remove(self._timer)
            self._timer = None

        #
        # DRAW
        if(self._draw_handle != None):
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
            if(bpy.context.area):
                bpy.context.area.tag_redraw()





    #
    # EXECUTE
    #
    # Return enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’}
    def execute(self, context):
        
        area=bpy.context.area
        print("Area " + str(area.type))
        for r in area.regions:
            print("  region " + str(r.type))
        
        space = bpy.context.area.spaces.active
        print("Active Space " + space.type)
        if(space.type == 'VIEW_3D'):
            region3d = space.region_3d
        #            print("view_perspective=" + region3d.view_perspective)
        #            print("is_perspective=" + str(region3d.is_perspective))
        #            print("view_rotation=" + str(region3d.view_rotation))
        #            print("view_matrix=" + str(region3d.view_matrix))
        #            print("perspective_matrix=" + str(region3d.perspective_matrix))
        #            print("view_distance=" + str(region3d.view_distance))
        #            print("view_location=" + str(region3d.view_location))
        

        #
        # Object selection
        #target_object = self.getSelectedObject()
        if(self.targetPoseBoneName != ""):
            target_object = self.getSelectedArmatureBone(self.targetPoseBoneName)
        elif(self.targetObjectName != ""):
            target_object = context.data.objects[self.targetObjectName]
        elif(bpy.context.mode == 'POSE'):
            target_object = bpy.context.active_pose_bone
        else:
            target_object = bpy.context.active_object

        assert (target_object != None)
        
        
        if(target_object == None):
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}
        
        
        assert (target_object != None)
        
        #self.target_object_name = objs[0].name
        target_object_name = target_object.name
        print("Running Leap receiver on object '" + str(target_object_name) + "'")
        
        
        #
        # Initialize the object manipulators
        if(self.isTranslating):
            self.obj_translator.setTarget(target_object)
            self.obj_translator.setViewMatrix(region3d.view_matrix)
            self.obj_translator.useFinger(self.translationUseFinger)
            self.obj_translator.setMirror(self.isTranslationMirrored)
            self.obj_translator.setLongitudinalMode(bpy.context.window_manager.leap_nui_longitudinal_mode)
            self.obj_translator.reset()
        
        
        if(self.isRotating):
            self.obj_rotator.setTarget(target_object)
            self.obj_rotator.setViewMatrix(region3d.view_matrix)
            self.obj_rotator.useFinger(self.rotationUseFinger)
            self.obj_rotator.setLongitudinalMode(bpy.context.window_manager.leap_nui_longitudinal_mode)
            self.obj_rotator.reset()
        
        
        arm = LeapModal.getSelectedArmature()

    
        if(self.isElbowSwivelRotating):
            
            hand = None
            if(target_object_name == "ElbowPT_L"):
                hand = Hand.LEFT
            elif(target_object_name == "ElbowPT_R"):
                hand = Hand.RIGHT
            else:
                self.report({'ERROR'}, "You have to select a MakeHuman Elbow IK handle to enable swivel rotation")
                return {'CANCELLED'}
            
            
            assert (hand != None)
            
            self.elbow_swivel_rotator.setTarget(arm)
            self.elbow_swivel_rotator.setTargetHand(hand)
            self.elbow_swivel_rotator.reset()
        
        if(self.isHandsDirectlyControlled):
            if(arm == None):
                self.report({'ERROR'}, "No armature selected")
                return {'CANCELLED'}
            
            self.hands_direct_controller.setTargetArmature(arm)
            self.hands_direct_controller.setMirrored(self.handsMirrorMode)
            self.hands_direct_controller.reset()
        
        self.report({'INFO'}, "Leap control starting")
        
        context.window_manager.modal_handler_add(self)
        self.addHandlers(context)
        
        
        print("Launching LeapReceiver thread...")
        #self.leap_receiver = LeapReceiver()
        #self.leap_receiver.start()
        self.leap_receiver = LeapReceiver.getSingleton()
        print("Launched LeapReceiver thread.")
        
        #self.report({'WARNING'}, "Leap started!") # anyway, won't be displayed before exiting the modal command.
        
        return {'RUNNING_MODAL'}


    #
    # MODAL
    #
    def modal(self, context, event):
        if event.type == 'ESC':
            # restore ranslation and/or rotation to initial values.
            if(self.isTranslating):
                self.obj_translator.restore()
            if(self.isRotating):
                self.obj_rotator.restore()
            if(self.isElbowSwivelRotating):
                self.elbow_swivel_rotator.restore()
            if(self.isHandsDirectlyControlled):
                self.hands_direct_controller.restore()

            return self.cancel(context)
        
        # If an invocation key is selected again, we stop the operator
#        if(event.type == TRANSLATION_SHORTCUT_CHAR
#           or event.type == ROTATION_SHORTCUT_CHAR
#           or event.type == TR_AND_ROT_SHORTCUT_CHAR
#           or event.type == FINGER_ROTATION_SHORTCUT_CHAR
#           or event.type == HANDS_DIRECT_CONTROL_CHAR):
        if(event.value == 'PRESS'):
            self.report({'INFO'}, "Leap control finished")
            self.stop_leap_receiver()
            self.removeHandlers()
            return {'FINISHED'}
        
        
        if event.type == 'TIMER':
            #print("TIMER for instance " + str(id(self)))
            
            # If the receiving thread has for some reason terminated
            # (for example for network error, or Leap disconnection)
            # Then we also exit.
            if(self.leap_receiver.hasTerminated()):
                # The socket has been already closed by the (dead) thread
                self.report({'ERROR'}, "Connection to Leap error!")
                return self.cancel(context)
            
            
            #
            # Update all active controllers
            leap_info = self.leap_receiver.getLeapDict()
            if(leap_info != None):
                if(self.isTranslating):
                    self.obj_translator.update(leap_info)
                
                if(self.isRotating):
                    self.obj_rotator.update(leap_info)
                
                if(self.isElbowSwivelRotating):
                    self.elbow_swivel_rotator.update(leap_info)
                
                if(self.isHandsDirectlyControlled):
                    self.hands_direct_controller.update(leap_info)

            #
            # Update modal listeners
            #print("Updating " + str(len(LeapModal.modalCallbacks)) + " callbacks")
            for l in LeapModal.modalCallbacks:
                res = l.controllersUpdated(self, context)
                if(res != None):
                    self.report({'INFO'}, "Leap control finished by listener")
                    self.stop_leap_receiver()
                    self.removeHandlers()
                    return res
    
    
        return {'RUNNING_MODAL'}
    
    #
    #
    #
    def getSelectedObject():
        
        out = None
        
        if(bpy.context.mode == 'POSE'):
            out = bpy.context.active_pose_bone
        else:
            out = bpy.context.active_object
        
        return out

    
    def getSelectedArmature():
        """Returns the specified bone from the selected armature. Or None"""
        # first search for a selected armature
        arm = None
        obj = bpy.context.active_object
        if(obj.type=="ARMATURE"):
            arm = obj
        return arm
    
    def getSelectedPoseBone():
        return bpy.context.active_pose_bone
    
    def getSelectedArmatureBone(self, bone_name):
        """Returns the specified bone from the selected armature. Or None"""
        # first search for a selected armature
        arm = None
        obj = bpy.context.active_object
        if(obj.type=="ARMATURE"):
            arm = obj
        
        if(arm==None):
            self.report({'WARNING'}, "No Armatures selected")
            return None
        
        if(not bone_name in arm.pose.bones):
            self.report({'WARNING'}, "No bone '" + bone_name + "' in armature '"+arm.name+"'")
            return None
        
        return arm.pose.bones[bone_name]
    
    
    #
    #
    #


    def stop_leap_receiver(self):
        if(self.leap_receiver != None):
            print("Terminating LeapReceiver thread...")
            #self.leap_receiver.terminate()
            #self.leap_receiver.join()
            #del(self.leap_receiver)
            self.leap_receiver.releaseSingleton()
            self.leap_receiver = None
            print("LeapReceiver thread joined.")
    

    def cancel(self, context):
        
        self.stop_leap_receiver()
        
        self.removeHandlers()
        
        self.report({'WARNING'}, "Leap exit")
        return {'CANCELLED'}

    #
    #
    #

    FONT_SIZE = 24
    FONT_RGBA = (0.8, 0.1, 0.2, 0.7)

    def draw_callback_px(self, context):

        #
        # DRAW OVERLAY
        #
        if(self.drawOverlay):
            #print("draw...")
            wm = context.window_manager
        
            msgs = []
            if(self.isTranslating):
                msg = "Translating"
                if(self.translationUseFinger):
                    msg += " (with finger)"
                msgs.append(msg)

            if(self.isRotating):
                msgs.append("Rotating")
            if(self.isElbowSwivelRotating):
                msgs.append("Rotate Elbow (with finger)")
            if(self.isHandsDirectlyControlled):
                msgs.append("Control both hands")


            if(len(msgs) > 0):
            
                # message = string.join(msgs, ", ") # was good for python 2
                message = ", ".join(msgs)
                lines = ["Leap Active:", message]
                max_width = 0
                for l in lines:
                    w,h = blf.dimensions(0, l)
                    if(w>max_width):
                        max_width = w

                #print("Draw Callback True")
                # draw text in the 3D View
                bgl.glPushClientAttrib(bgl.GL_CURRENT_BIT|bgl.GL_ENABLE_BIT)
            
                pos_x = (context.region.width / 2) - (max_width / 2)
                pos_y = context.region.height - (self.FONT_SIZE * 2) # context.region.height - (self.FONT_SIZE * 3) - 100
            
                blf.size(0, self.FONT_SIZE, 72)
                bgl.glColor4f(*self.FONT_RGBA)
                blf.blur(0, 1)
                # shadow?
                #blf.enable(0, blf.SHADOW)
                #blf.shadow_offset(0, 1, -1)
                #blf.shadow(0, 5, 0.0, 0.0, 0.0, 0.8)

                for l in lines:
                    blf.position(0, pos_x, pos_y, 0)
                    blf.draw(0, l)
                    pos_y -= self.FONT_SIZE
            
            
                bgl.glPopClientAttrib()

        #
        # INVOKE GLOBAL CALLBACKS
        #
        for cb in LeapModal.drawCallbacks:
            cb.draw(self, context)

        pass

#
#
#
