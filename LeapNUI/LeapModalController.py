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
from LeapNUI.LeapReceiver import LeapReceiver
from LeapNUI.LeapReceiver import PointableSelector
from LeapNUI.LeapReceiver import HandSelector
from LeapNUI.LeapReceiver import CircleGestureSelector

from MakeHumanTools.BoneSet import *


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
    
    # Pointable ocation at previous call of update/
    pointable_last_location = None
    
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

    # Float number used to scale the translation delta vector. Can be used to increase precision (<1.0) or increase reactivity (>1.0)
    delta_scale = 1.0
    
    def useFinger(self, b):
        self.use_finger = b
        print("USE_FINGER for TR " + str(b))
    
    def setMirror(self, b):
        self.mirror_y = b
    
    def setLongitudinalMode(self, b):
        self.longitudinal_mode = b

    def setScale(self, s):
        self.delta_scale = s
    
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
        self.pointable_last_location = None
    
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
        #delta = [ pos[i] - self.pointable_start_location[i] for i in range(0,3)]
        delta = [ pos[i] - self.pointable_last_location[i] for i in range(0,3)]
        
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

        # scale for precision/reactivity
        delta = delta * self.delta_scale
        
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
        
        #new_loc = [ self.target_start_location[i] + (delta[i]) for i in range(0,3)]
        new_loc = [ self.target_object.location[i] + (delta[i]) for i in range(0,3)]
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

        if(self.pointable_last_location == None):
            self.pointable_last_location = pos

        new_loc = self.handPosToTargetSpace(pos)

        self.pointable_last_location = pos

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

        #print("setTarget\nobject_matrix="+str(self.target_object.matrix) + "\n"
        #"object_matrix_basis="+str(self.target_object.matrix_basis) + "\n"
        #"posebone_matrix = " + str(self.posebone_matrix) + "\n")
    
    
    def setViewMatrix(self, mat):
        self.view_matrix = mat
        #print("set view_matrix = " + str(self.view_matrix))
    
    
    def useFinger(self, b):
        self.use_finger = b


    def setLongitudinalMode(self, b):
        self.longitudinal_mode = b


    def reset(self):
        # Sorry, I have to force the reotation mode to Quaternion.
        self.target_object.rotation_mode = 'QUATERNION'
        self.target_start_rotation = mathutils.Quaternion(self.target_object.rotation_quaternion)
        #print("target_start_rotation="+str(self.target_start_rotation))
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

            #print(rot_mat)

            rot = rot_mat.to_quaternion()

            #print(rot)
            
            if(self.palm_start_rotation == None):
                self.palm_start_rotation = mathutils.Quaternion(rot)
            
            
            # Rotation with respect to the original palm rotation
            delta_rot = rot * self.palm_start_rotation.inverted()

            #print("delta_rot="+str(delta_rot))
        
        # rotate the delta vector according to the view matrix
        cam_rot = self.view_matrix.to_quaternion()
        #print("cam_rot="+str(cam_rot))

        delta_rot = cam_rot.inverted() * delta_rot * cam_rot
        #print("after cam_rot, delta_rot="+str(delta_rot))
    
        # If it is a PoseBone, must cancel the skeletal rotation
        if(self.posebone_matrix != None):
            delta_rot = self.posebone_matrix.inverted().to_quaternion() * delta_rot * self.posebone_matrix.to_quaternion()
        #print("after posebone_matrix, delta_rot="+str(delta_rot))
    
    
        # New rotation
        new_rot = delta_rot * self.target_start_rotation
        #print("new_rot="+str(new_rot))

        # Deal with the Double Coverage problem.
        # See http://mollyrocket.com/837, but his solution is uncorrect. Inverting the w is not enough, we need the negation of the quaterion.
        dot_prod = new_rot.dot(self.target_start_rotation)
        #print("dot_prod="+str(dot_prod))
        if(dot_prod<0):
            new_rot.negate()
    
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
            H = ".R"
        elif(self.target_hand == Hand.LEFT):
            H = ".L"
        else:
            assert False
    
        #print("SWIVEL "+H)
        
        
        SHOULDER_BONE = MH_SHOULDER_BONE_base + H
        ELBOW_BONE = MH_ELBOW_BONE_base + H
        WRIST_BONE = MH_WRIST_BONE_base + H
        self.ELBOW_CONTROL = MH_ELBOW_CONTROLLER_base + H
        
        
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
        pointable_id = gesture["pointableIds"][0]   # we take only one ID for circle gestures.
        pointables = [p for p in leap_dict["pointables"] if p["id"] == pointable_id]
        assert(len(pointables) > 0)
        tipVelocity = pointables[0]["tipVelocity"]
        tipVelocity = mathutils.Vector(tipVelocity).length
        angle = tipVelocity * UPDATE_DELAY * 0.005
        #print(tipVelocity, angle)
        
        normal = mathutils.Vector(gesture["normal"])
        #print("normal="+str(normal))
        if(normal.z < 0):   # cloclwise rotation
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

# The Leap coord system is like OpenGL: x-right, y-up, z-towards-observer
# Blender uses: x-right, y-away-form-observer, z-up
blender_to_leap_rotmat = mathutils.Matrix.Rotation(0, 3, 'X')
blender_to_leap_rotmat[0] = [-1,0,0]
blender_to_leap_rotmat[1] = [0,0,1]
blender_to_leap_rotmat[2] = [0,1,0]

blender_to_leap_mirror_rotmat = mathutils.Matrix.Rotation(0, 3, 'X')
blender_to_leap_mirror_rotmat[0] = [-1,0,0]
blender_to_leap_mirror_rotmat[1] = [0,0,-1]
blender_to_leap_mirror_rotmat[2] = [0,-1,0]


leap_to_blender_posmat = blender_to_leap_rotmat

# This matrix aligns a transformation in the Leap space to the Blender one.
leap_to_blender_mirror_posmat = mathutils.Matrix.Rotation(0, 3, 'X')
leap_to_blender_mirror_posmat[0] = [1,0,0]
leap_to_blender_mirror_posmat[1] = [0,0,1]
leap_to_blender_mirror_posmat[2] = [0,1,0]


# Offsets to apply to hands
# Calculated cosidering a sitting position with Leap centered more or less at the height of the belly button
# hands (palm pos) in "rest" position are just below the breasts
# Offsets calculated summing the corresponding hands controller offset + the Leap motion real-world hand position offset
# Wrist_R
#Matrix(((-0.1417485922574997, -0.9848122000694275, 0.10025876015424728, -6.943360328674316),
#        (0.9848121404647827, -0.15055248141288757, -0.08647795021533966, 0.8884090185165405),
#        (0.10025879740715027, 0.08647797256708145, 0.991195559501648, 15.048200607299805),
#        (0.0, 0.0, 0.0, 1.0)))

#
# .matrix contains the transformation in global axes.
# Controller hand.ik.L, in default position:
# mglobal = Matrix(((0.39478737115859985, 0.25884515047073364, -0.8815567493438721, 4.882474899291992),
#         (0.6339536309242249, -0.7712342143058777, 0.05745130777359009, -2.0682997703552246),
#         (-0.6650155186653137, -0.5815471410751343, -0.4685693085193634, 10.817537307739258),
#         (0.0, 0.0, 0.0, 1.0)))
# In "frontal" position (identity for the Leap)
# Matrix(((0.9926701784133911, 0.014985796064138412, -0.1199234127998352, 4.882474899291992),
#         (0.018050719052553177, -0.9995366334915161, 0.024511512368917465, -2.0682997703552246),
#         (-0.11950039863586426, -0.02649667114019394, -0.992480456829071, 10.817537307739258),
#         (0.0, 0.0, 0.0, 1.0)))
# or
# Quaternion((0.01277670543640852, -0.9980840682983398, -0.008275993168354034, 0.059971097856760025))

#
# .matrix_basis contains the transformation in local axes, as the values are inputted in the numerical properties panel.
# Controller hand.ik.L, in default position: Identity
# In "frontal" position (identity for the Leap)
# Matrix(((0.482806533575058, -0.6101229786872864, 0.6282100081443787, 0.0),
#         (0.31252166628837585, 0.7901647686958313, 0.5272284150123596, 0.0),
#         (-0.8180636167526245, -0.058220114558935165, 0.5721733570098877, 0.0),
#         (0.0, 0.0, 0.0, 1.0)))
# or
# Quaternion((0.8433778882026672, -0.173542782664299, 0.4287146031856537, 0.2734968066215515))


# matrix_channel (???):
# Matrix(((1.0, 2.9802322387695312e-08, 2.9802322387695312e-08, 0.0),
#         (5.587935447692871e-08, 1.0, -5.4016709327697754e-08, 4.76837158203125e-07),
#         (2.9802322387695312e-08, 2.2910535335540771e-07, 1.000000238418579, -9.5367431640625e-07),
#         (0.0, 0.0, 0.0, 1.0)))

#
# Controller hand.ik.R, in default position:
# from .matrix (GLOBAL_ALIGNMENT_R):
# Quaternion((0.012777568772435188, -0.998083770275116, 0.00827696267515421, -0.05997561663389206))
# from .matrix_basis (ALIGNMENT_L):
# Quaternion((0.843379557132721, -0.1735418289899826, -0.4287116825580597, -0.2734967768192291))

#local transformation can be extracted with:
# mbase.inverted() * .matrix
# for translation:
# (mbase.inverted() * .matrix).to_translation()
# for rotation:
#(mbase.inverted() * .matrix).to_quaternion()



# Absolute position of the hand in front of the body
# Vector((0.049218177795410156, -2.463426351547241, 11.399259567260742))  # from bpy.data.objects['Manuel'].pose.bones['hand.ik.L'].matrix.translation
# mathutils.Vector((0.049, -4, 11)) # Rounded and adjusted by trials
# Absolute position of the hand in default position
# Vector((4.882474899291992, -2.0682997703552246, 10.817537307739258))
# The additional 0.45 on the x axis is due to the distance between the wrist and the hand center
CONTROLLER_POS_OFFSET_L = mathutils.Vector((0.45, -4, 11)) - mathutils.Vector((4.882474899291992, -2.0682997703552246, 10.817537307739258))
CONTROLLER_POS_OFFSET_R = mathutils.Vector((-CONTROLLER_POS_OFFSET_L[0], CONTROLLER_POS_OFFSET_L[1], CONTROLLER_POS_OFFSET_L[2] ))  # symmetric to yz plane


# We consider that, when the hand is open, the palm center is in fact calculated very close to the middle finger base.
# A vector going form the controller center of rotation to the center of the palm
# first vector: left-hand palm center (more precisely, base of bone f_middle.01.L)
# second vector: left-hand wrist center (center of rotation of controller hand.ik.L )
WRIST_TO_HAND_OFFSET_L = mathutils.Vector((5.2734,-2.923,10.2127)) - mathutils.Vector((4.8825,-2.0683, 10.8175))
WRIST_TO_HAND_OFFSET_R = mathutils.Vector((-WRIST_TO_HAND_OFFSET_L[0], WRIST_TO_HAND_OFFSET_L[1], WRIST_TO_HAND_OFFSET_L[2])) # simmetric with respect to x-axis



class MakeHumanHandsDirectController:
    
    LEAP_BASE_HEIGHT = 1.20

    # Quaternion to align the left hand of the character to a frontal position.
    GLOBAL_ALIGNMENT_L = mathutils.Quaternion((0.01277670543640852, -0.9980840682983398, -0.008275993168354034, 0.059971097856760025))
    GLOBAL_ALIGNMENT_R = mathutils.Quaternion((0.012777568772435188, -0.998083770275116, 0.00827696267515421, -0.05997561663389206))
    
    isMirrored = False
    
    target_armature = None
    
    r_wrist_initial_rot = None
    r_wrist_initial_loc = None
    l_wrist_initial_rot = None
    l_wrist_initial_loc = None
    
    # The parent matrix transformation of each Hand controller
    PARENT_R = None
    PARENT_L = None


    def setTargetArmature(self, a):
        self.target_armature = a
    
    def setMirrored(self, b):
        self.isMirrored = b
    
    def reset(self):
        
        r_wrist = self.target_armature.pose.bones[MH_HAND_CONTROLLER_R]
        self.PARENT_R = r_wrist.matrix * r_wrist.matrix_basis.inverted()
        
        l_wrist = self.target_armature.pose.bones[MH_HAND_CONTROLLER_L]
        self.PARENT_L = l_wrist.matrix * l_wrist.matrix_basis.inverted()
        
        # Save data for restoration (We need a copy, not only a reference)
        self.r_wrist_initial_rot = mathutils.Quaternion(r_wrist.rotation_quaternion)
        self.r_wrist_initial_loc = mathutils.Vector(r_wrist.location)
        self.l_wrist_initial_rot = mathutils.Quaternion(l_wrist.rotation_quaternion)
        self.l_wrist_initial_loc = mathutils.Vector(l_wrist.location)
        
        pass
    
    def restore(self):
        self.target_armature.pose.bones[MH_HAND_CONTROLLER_R].rotation_quaternion = self.r_wrist_initial_rot
        self.target_armature.pose.bones[MH_HAND_CONTROLLER_R].location = self.r_wrist_initial_loc
        self.target_armature.pose.bones[MH_HAND_CONTROLLER_L].rotation_quaternion = self.l_wrist_initial_rot
        self.target_armature.pose.bones[MH_HAND_CONTROLLER_L].location = self.l_wrist_initial_loc
        pass
    
    def update(self, leap_dict):
        
        if(not 'hands' in leap_dict):
            return None


        rhand = None
        lhand = None

        hands = leap_dict["hands"]

        # Take the indices of right and left hands
        for h in hands:
            if(h["type"] == "right"):
                rhand = h
            elif(h["type"] == "left"):
                lhand = h


        if(self.isMirrored):
            hand_refs = [rhand, lhand]
        else:
            hand_refs = [lhand, rhand]


        for hand, GLOBAL_ALIGNMENT, PARENT, hand_controller_name, CONTROLLER_POS_OFFSET, WRIST_TO_HAND_OFFSET in zip(
                                                                                                        hand_refs,
                                                                                                        [self.GLOBAL_ALIGNMENT_L, self.GLOBAL_ALIGNMENT_R],
                                                                                                        [self.PARENT_L, self.PARENT_R],
                                                                                                        [MH_HAND_CONTROLLER_L, MH_HAND_CONTROLLER_R],
                                                                                                        [CONTROLLER_POS_OFFSET_L, CONTROLLER_POS_OFFSET_R],
                                                                                                        [WRIST_TO_HAND_OFFSET_L, WRIST_TO_HAND_OFFSET_R]) :
            
            
            if(hand == None):
                continue 

            hand_controller = self.target_armature.pose.bones[hand_controller_name]

            
            #
            # ROTATION
            #

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
            
            
            # Convert the rotations in Blender orientation axes
            if(self.isMirrored):
                rot = (blender_to_leap_mirror_rotmat.inverted() * rot_mat * blender_to_leap_mirror_rotmat).to_quaternion()
            else:
                rot = (blender_to_leap_rotmat.inverted() * rot_mat * blender_to_leap_rotmat).to_quaternion()

            # Compose with the global alignment to bring the character hand in frontal position.
            rot = rot * GLOBAL_ALIGNMENT

            # Convert to local system
            rot = PARENT.inverted().to_quaternion() * rot

            hand_controller.rotation_quaternion = rot

            
            #
            # POSITION
            #

            pos = mathutils.Vector(hand["palmPosition"])

            # Scale from millimeters to decimeters in MakeHuman space
            pos *= 0.01

            # Rotate axes from OpenGL to Blender
            if(self.isMirrored):
                pos = leap_to_blender_mirror_posmat * pos
            else:
                pos = leap_to_blender_posmat * pos
            
            #print("Absolute space: " + str(pos))
            # Align the hand palm center to the hand controller center
            pos = pos - WRIST_TO_HAND_OFFSET

            # Add the default offset to position the hand in front of the character
            pos += CONTROLLER_POS_OFFSET
            #print("controller offset=", str(hand_id), str(CONTROLLER_POS_OFFSET))

            # Convert to local coordinates
            pos = PARENT.inverted().to_quaternion() * pos
            #print("Local space: " + str(pos))

            hand_controller.location = pos

            # RECORD (eventually)
            if(bpy.context.scene.tool_settings.use_keyframe_insert_auto):
                frame = bpy.context.scene.frame_current
                hand_controller.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                hand_controller.keyframe_insert(data_path="location", frame=frame)
            

        pass # end update

#
#
#

# This class takes the information about finger extension in the Leap Dictionary and maps it to the Finger controllers fo the MakeHuman character
class MakeHumanFingersDirectController:

    isMirrored = False
    
    target_armature = None

    # Each of these vectors will contain 5 elements. Each element is the rotation quaternion of the controller at the controller reset.
    # The order is from thumb to pinkie.
    r_controllers_initial_values = []
    l_controllers_initial_values = []


    def setTargetArmature(self, a):
        self.target_armature = a
    
    def setMirrored(self, b):
        self.isMirrored = b
    
    def reset(self):
        
        self.r_controllers_initial_values.clear()
        for cname in MH_HAND_CONTROLLERS_R:
            c = self.target_armature.pose.bones[cname]
            self.r_controllers_initial_values.append(mathutils.Quaternion(c.rotation_quaternion))

        for cname in MH_HAND_CONTROLLERS_L:
            c = self.target_armature.pose.bones[cname]
            self.l_controllers_initial_values.append(mathutils.Quaternion(c.rotation_quaternion))

    
    def restore(self):

        for cnum, cname in enumerate(MH_HAND_CONTROLLERS_R):
            q = self.r_controllers_initial_values[cnum]
            self.target_armature.pose.bones[cname].rotation_quaternion = q

        for cnum, cname in enumerate(MH_HAND_CONTROLLERS_L):
            q = self.l_controllers_initial_values[cnum]
            self.target_armature.pose.bones[cname].rotation_quaternion = q

    
    def update(self, leap_dict):
        
        if(not 'hands' in leap_dict):
            return None
    

        # Infer which hand is left and which is right
        hands = leap_dict["hands"]

        rhand_id = None
        lhand_id = None

        # Take the indices of right and left hands
        for h in hands:
            if(h["type"] == "right"):
                rhand_id = h["id"]
            elif(h["type"] == "left"):
                lhand_id = h["id"]

        # If we work in mirror mode, let's swap them
        if(self.isMirrored):
            rhand_id, lhand_id = lhand_id, rhand_id


        # type()
        # The integer code representing the finger name.
        # 0 = TYPE_THUMB
        # 1 = TYPE_INDEX
        # 2 = TYPE_MIDDLE
        # 3 = TYPE_RING
        # 4 = TYPE_PINKY

        # Gather reference to fingers
        for p in leap_dict["pointables"]:
            finger_type = p["type"]
            #print("pointable "+str(finger_type)+" of hand "+str(p["handId"]))

            handId = p["handId"]
            if(handId==rhand_id):
                target_hand_id = rhand_id
                # names of the finger controllers, ordered as indexes by the leap SDK "type" attribute, from thumb to pink.
                controller_names = MH_HAND_CONTROLLERS_R
            elif(handId == lhand_id):
                target_hand_id = lhand_id
                controller_names = MH_HAND_CONTROLLERS_L
            else:
                # If the hand is neither the left nor the right one (maybe for slightly visible fingers or pointables), then skip everything.
                continue

            finger_length = p["length"]
            if(finger_length == 0):
                continue

            #
            # calculate an extension factor as ratio between the finger length and the position of the tip.

            # btipPosition – position of the extreme end of the distal phalanx as an array of 3 floating point numbers.
            # mcpPosition - The physical position of the metacarpophalangeal joint, or knuckle, of the finger. This position is the joint between the metacarpal and proximal phalanx bones.
            finger_tip_pos = mathutils.Vector(p["btipPosition"])
            finger_base_pos = mathutils.Vector(p["mcpPosition"])
            distance = (finger_tip_pos - finger_base_pos).length
            extension_ratio = distance / finger_length

            #
            # The provided length of a finger doesn't take into account the whole size until the knuckle.
            # For each finger, the proportion between the finger length and the full size (tip to knuckle) distance is 1.41 (2.00 for the thumb)
            # So I divide the ration for this value to normalize the extension_ratio between 0 and 1.
            FINGER_LENGTH_TO_DISTANCE_RATIO = 1.41
            THUMB_LENGTH_TO_DISTANCE_RATIO = 2.00
            if(finger_type == 0):
                controller_ratio = extension_ratio / THUMB_LENGTH_TO_DISTANCE_RATIO
            else:
                controller_ratio = extension_ratio / FINGER_LENGTH_TO_DISTANCE_RATIO


            #if(p["type"] == 1):
            #print(finger_length, finger_base_pos, finger_tip_pos, distance,  extension_ratio, controller_ratio)

            # clamp
            controller_ratio = sorted((0.0, controller_ratio, 1.0))[1]

            # The resulting ratio will be effectively between 0.6 and 1.
            # I operate the controllers by placing a rotation around the X axis, of a XYZ euler rotatino order, to be ca. 70 degs when the cntroller value is at 0.6.
            # ratio=1 -> rot = 0
            # ratio=0.6 -> rot = 70
            # 70/(1.0-0.6) -> -175
            # 90/(1.0-0.6) -> -225
            # eq: angle = 175 - 175 * ratio
            #finger_angle = 175 - 175 * controller_ratio
            finger_angle = 225 - 225 * controller_ratio
            finger_q = mathutils.Quaternion( (1.0, 0.0, 0.0), radians(finger_angle) )

            # Apply this ratio to the finger controllers.
            controller = self.target_armature.pose.bones[ controller_names[finger_type] ]
            controller.rotation_quaternion = finger_q

            # RECORD (eventually)
            if(bpy.context.scene.tool_settings.use_keyframe_insert_auto):
                frame = bpy.context.scene.frame_current
                controller.keyframe_insert(data_path="rotation_quaternion", frame=frame)



#
#
#

class MakeHumanElbowsDirectController:

    isMirrored = False
    
    target_armature = None

    def setTargetArmature(self, a):
        self.target_armature = a
    
    def setMirrored(self, b):
        self.isMirrored = b


    def reset(self):

        self.elbow_r = self.target_armature.pose.bones[MH_ELBOW_CONTROLLER_R]
        self.elbow_l = self.target_armature.pose.bones[MH_ELBOW_CONTROLLER_R]

        self.hand_r = self.target_armature.pose.bones[MH_HAND_CONTROLLER_R]
        self.hand_l = self.target_armature.pose.bones[MH_HAND_CONTROLLER_L]

        self.elbow_r = self.target_armature.pose.bones[MH_ELBOW_CONTROLLER_R]
        self.elbow_l = self.target_armature.pose.bones[MH_ELBOW_CONTROLLER_L]

        self.forearm_bone_r = self.target_armature.pose.bones[MH_FOREARM_BONE_base+".R"]
        self.forearm_bone_l = self.target_armature.pose.bones[MH_FOREARM_BONE_base+".L"]
        
        
        self.r_elbow_initial_pos = mathutils.Vector(self.elbow_r.location)
        self.l_elbow_initial_pos = mathutils.Vector(self.elbow_l.location)

    
    def restore(self):

        self.elbow_r.location = self.r_elbow_initial_pos
        self.elbow_l.location = self.l_elbow_initial_pos

    
    def update(self, leap_dict):
        
        if(not 'hands' in leap_dict):
            return None
    
        # Infer which hand is left and which is right
        hands = leap_dict["hands"]

        rhand_id = None
        rhand = None
        lhand_id = None
        lhand = None

        # Take the indices of right and left hands
        for h in hands:
            if(h["type"] == "right"):
                rhand = h
                rhand_id = h["id"]
            elif(h["type"] == "left"):
                lhand = h
                lhand_id = h["id"]

        # If we work in mirror mode, let's swap them
        if(self.isMirrored):
            rhand_id, lhand_id = lhand_id, rhand_id
            rhand, lhand = lhand, rhand


        for hand, hand_controller, elbow_controller, forearm_bone in zip([rhand, lhand],
                                            [self.hand_r, self.hand_l],
                                            [self.elbow_r, self.elbow_l],
                                            [self.forearm_bone_r, self.forearm_bone_l]):

            if(hand == None):
                continue

            # Get the vector from the wrist to the elbow, in Leap space.
            elbow_pos = mathutils.Vector(hand["elbow"])
            wrist_pos = mathutils.Vector(hand["wrist"])
            wrist_to_elbow_vect = elbow_pos - wrist_pos
            wrist_to_elbow_vect.normalize()   # get only the unitary direction

            # Transform the offset in Blender space
            if(self.isMirrored):
                wrist_to_elbow_vect = leap_to_blender_mirror_posmat * wrist_to_elbow_vect
            else:
                wrist_to_elbow_vect = leap_to_blender_posmat * wrist_to_elbow_vect

            wrist_to_elbow_vect *= forearm_bone.length    # remodulate on forearm length

            # absolute position for the elbow
            elbow_pos = hand_controller.matrix.to_translation() + wrist_to_elbow_vect

            # Set the absolute matrix
            elbow_controller.matrix = mathutils.Matrix.Translation(elbow_pos)

            # RECORD (eventually)
            if(bpy.context.scene.tool_settings.use_keyframe_insert_auto):
                frame = bpy.context.scene.frame_current                
                elbow_controller.keyframe_insert(data_path="location", frame=frame)



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
    isTranslationMirrored = BoolProperty(name="translate_mirror", description="Whether the translation is mirrored on the y-axis")
    isRotating = BoolProperty(name="rotate", description="Finger movement will rotate the object")
    isElbowSwivelRotating = BoolProperty(name="elbow_swivel_rotate", description="Finger Circle gesture rotates the elbow swivel angle")
    isHandsDirectlyControlled = BoolProperty(name="hands_direct_control", description="Hands position is directly controlled by hands detected in Leap")
    handsMirrorMode = BoolProperty(name="hands_mirror_mode", description="Hands direct control is applied with the 'mirror' metaphor")
    isFingersDirectlyControlled = BoolProperty(name="fingers_direct_control", description="Fingers extension and orientation is directly controlled by hands detected in Leap")
    isElbowsDirectlyControlled = BoolProperty(name="elbows_direct_control", description="Elbows position is directly controlled by hands and forearms detected in Leap")
    
    targetObjectName = StringProperty(name="target_object_name", description="The name of the object to manipulate. If None, the active object will be used", default="")
    targetPoseBoneName = StringProperty(name="target_posebone_name", description="The name of the posebone to manipulate. If None, the active posebone will be used", default="")
    
    
    # by default we use palm
    translationUseFinger = BoolProperty(name="translate_use_finger", default=False, description="Finger movement will used to translate the object")
    # by default we use palm
    rotationUseFinger = BoolProperty(name="rotation_use_finger", default=False, description="Finger movement will be used to rotate the object")

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
    fingers_direct_controller = MakeHumanFingersDirectController()
    elbows_direct_controller = MakeHumanElbowsDirectController()
    
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
        # print("Area " + str(area.type))
        # for r in area.regions:
        #     print("  region " + str(r.type))
        
        space = bpy.context.area.spaces.active
        #print("Executed in space "+str(space.as_pointer()))
        #print("Active Space " + space.type)
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
            target_object = self.getActiveArmatureBone(self.targetPoseBoneName)
            if(target_object == None):
                self.report({'ERROR'}, "Can't find bone named '"+self.targetPoseBoneName+"' in selected armature.")
                return {'CANCELLED'}

        elif(self.targetObjectName != ""):
            if(not self.targetObjectName in context.data.objects):
                self.report({'ERROR'}, "Can't find object named '"+self.targetObjectName+"'.")
                return {'CANCELLED'}
            target_object = context.data.objects[self.targetObjectName]
        elif(bpy.context.mode == 'POSE'):
            target_object = bpy.context.active_pose_bone
        else:
            target_object = bpy.context.active_object

        assert (target_object != None)
        
        
        # if(target_object == None):
        #     self.report({'ERROR'}, "No target object")
        #     return {'CANCELLED'}
        
        
        target_object_name = target_object.name
        print("Running Leap receiver on target '" + str(target_object_name) + "'")
        
        
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
            if(target_object_name == MH_ELBOW_CONTROLLER_L or target_object_name == MH_HAND_CONTROLLER_L):
                hand = Hand.LEFT
            elif(target_object_name == MH_ELBOW_CONTROLLER_R or target_object_name == MH_HAND_CONTROLLER_R):
                hand = Hand.RIGHT
            else:
                self.report({'ERROR'}, "You have to select a MakeHuman Elbow or Wrist IK handle to enable swivel rotation")
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


        if(self.isFingersDirectlyControlled):
            if(arm == None):
                self.report({'ERROR'}, "No armature selected")
                return {'CANCELLED'}

            self.fingers_direct_controller.setTargetArmature(arm)
            self.fingers_direct_controller.setMirrored(self.handsMirrorMode)
            self.fingers_direct_controller.reset()

        if(self.isElbowsDirectlyControlled):
            if(arm == None):
                self.report({'ERROR'}, "No armature selected")
                return {'CANCELLED'}

            self.elbows_direct_controller.setTargetArmature(arm)
            self.elbows_direct_controller.setMirrored(self.handsMirrorMode)
            self.elbows_direct_controller.reset()
        
        self.report({'INFO'}, "Leap control starting")
        
        context.window_manager.modal_handler_add(self)
        self.addHandlers(context)

        #
        # Inform listeners        
        for l in LeapModal.modalCallbacks:
            if( hasattr(l, 'started')):
                res = l.started(self, context)

        
        print("Acquiring LeapReceiver...")
        self.leap_receiver = LeapReceiver.getSingleton()
        
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
            if(self.isFingersDirectlyControlled):
                self.fingers_direct_controller.restore()
            if(self.isElbowsDirectlyControlled):
                self.elbows_direct_controller.restore()

            for l in LeapModal.modalCallbacks:
                if( hasattr(l, 'cancelled')):
                    res = l.cancelled(self, context)

            return self.cancel(context)
        
        # If an invocation key is selected again, we stop the operator
#        if(event.type == TRANSLATION_SHORTCUT_CHAR
#           or event.type == ROTATION_SHORTCUT_CHAR
#           or event.type == TR_AND_ROT_SHORTCUT_CHAR
#           or event.type == FINGER_ROTATION_SHORTCUT_CHAR
#           or event.type == HANDS_DIRECT_CONTROL_CHAR):
        if(event.value == 'PRESS'):
            self.report({'INFO'}, "Leap control finished")
            for l in LeapModal.modalCallbacks:
                if( hasattr(l, 'finished')):
                    l.finished(self, context)

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
                for l in LeapModal.modalCallbacks:
                    if( hasattr(l, 'finished')):
                        l.finished(self, context)
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

                if(self.isFingersDirectlyControlled):
                    self.fingers_direct_controller.update(leap_info)

                if(self.isElbowsDirectlyControlled):
                    self.elbows_direct_controller.update(leap_info)

            #
            # Update modal listeners
            #print("Updating " + str(len(LeapModal.modalCallbacks)) + " callbacks")
            for l in LeapModal.modalCallbacks:
                res = l.controllersUpdated(self, context)
                if(res != None):
                    self.report({'INFO'}, "Leap control finished by listener")
                    for l in LeapModal.modalCallbacks:
                        if( hasattr(l, 'finished')):
                            l.finished(self, context)


                    self.stop_leap_receiver()
                    self.removeHandlers()
                    return res
    
    
        return {'RUNNING_MODAL'}
    
    #
    #
    # Listeners management

    # Insert the argument in the list of global Listeners.
    # The provided object must declare the following methods:
    # - def controllersUpdated(self, controller, context):
    #   invoked just afetr the controllers have been update. First argument will be the controller running the modal method, the second the context of execution.
    def addModalListener(l):
        LeapModal.modalCallbacks.append(l)

    def removeModalListener(l):
        LeapModal.modalCallbacks.remove(l)


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
    
    def getActiveArmatureBone(self, bone_name):
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
            print("Releasing LeapReceiver ...")
            self.leap_receiver.releaseSingleton()
            self.leap_receiver = None
    

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
