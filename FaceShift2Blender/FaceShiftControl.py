#     "FaceShift 2 Blender" is a Blender addon to apply FaceShift stream data to a MakeHuman character face.
#     Copyright (C) <2014>  <Fabrizio Nunnari>
# 
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
# 
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.


bl_info = {
    "name": "FaceShift 2 Blender",
    "author": "Fabrizio Nunnari",
    "version": (1,1),
    "blender": (2, 66, 0),
    "location": "Search > Faceshoft 2 Blender",
    "description": "Apply FaceShift stream data to a MakeHuman face.",
    "warning": "",
    "wiki_url": "http://",
    "tracker_url": "https://",
    "category": "Animation"}

"""
This script allows to control a MakeHuman Blender character using the stream data from FaceShift.
User can use their own face to perform character face posing and animation.
"""


import bpy
from bpy.props import * # for properties

import time
import socket
import math
import struct

# This is Blender specific
import mathutils


from MakeHumanTools import BoneSet


LISTENING_PORT = 33433
#BINDING_ADDR = "127.0.0.1"     # Good for local work
BINDING_ADDR = ''   # Empty string means: bind to all network interfaces

BLOCK_ID_TRACKING_STATE = 33433     # According to faceshift docs

# Delay between modal timed updates when entered the modal command mode. In seconds.
UPDATE_DELAY = 0.04


    

# FaceShift Studio v2014.1, 51 channels
# This is the order the blendsheps are received from FaceShift.
BLEND_SHAPE_NAMES_FS2014_1 = [
    "EyeBlink_L",
    "EyeBlink_R",
    "EyeSquint_L",
    "EyeSquint_R",
    "EyeDown_L",
    "EyeDown_R",
    "EyeIn_L",
    "EyeIn_R",
    "EyeOpen_L",
    "EyeOpen_R",
    "EyeOut_L",
    "EyeOut_R",
    "EyeUp_L",
    "EyeUp_R",
    "BrowsD_L",
    "BrowsD_R",
    "BrowsU_C",
    "BrowsU_L",
    "BrowsU_R",
    "JawOpen",
    "LipsTogether",
    "JawLeft",
    "JawRight",
    "JawFwd",
    "LipsUpperUp_L",
    "LipsUpperUp_R",
    "LipsLowerDown_L",
    "LipsLowerDown_R",
    "LipsUpperClose",
    "LipsLowerClose",
    "MouthSmile_L",
    "MouthSmile_R",
    "MouthDimple_L",
    "MouthDimple_R",
    "LipsStretch_L",
    "LipsStretch_R",
    "MouthFrown_L",
    "MouthFrown_R",
    "MouthPress_L",
    "MouthPress_R",
    "LipsPucker",
    "LipsFunnel",
    "MouthLeft",
    "MouthRight",
    "ChinLowerRaise",
    "ChinUpperRaise",
    "Sneer_L",
    "Sneer_R",
    "Puff",
    "CheekSquint_L",
    "CheekSquint_R"]

# Customized version, to better accomodate the rig offered by MHX2 0.24. The number of channels is 51 - 8 + 3 = 46
# Differences with the default Rig profile are marked as comment
BLEND_SHAPE_NAMES_FS2014_1_CUSTOM = [
    "EyeBlink_L",
    "EyeBlink_R",
    "EyeSquint_L",
    "EyeSquint_R",
    "EyeDown_L",
    "EyeDown_R",
    #"EyeIn_L",         # -
    #"EyeIn_R",         # -
    "EyeOpen_L",
    "EyeOpen_R",
    #"EyeOut_L",        # -
    #"EyeOut_R",        # -
    "EyeUp_L",
    "EyeUp_R",
    "BrowsD_L",
    "BrowsD_R",
    "BrowsU_C",
    "BrowsU_L",
    "BrowsU_R",
    "BrowsSqueeze",     # +
    "JawOpen",
    "JawChew",          # +
    #"LipsTogether",    # -
    "JawLeft",
    "JawRight",
    #"JawFwd",          # -
    "LipsUpperUp_L",
    "LipsUpperUp_R",
    "LipsLowerDown_L",
    "LipsLowerDown_R",
    "LipsUpperClose",
    "LipsLowerClose",
    "MouthSmile_L",
    "MouthSmile_R",
    "MouthDimple_L",
    "MouthDimple_R",
    "LipsStretch_L",
    "LipsStretch_R",
    "MouthFrown_L",
    "MouthFrown_R",
    "MouthPress_L",
    "MouthPress_R",
    "LipsPucker",
    "LipsFunnel",
    "MouthLeft",
    "MouthRight",
    "ChinLowerRaise",
    "ChinUpperRaise",
    #"Sneer_L",      # -
    #"Sneer_R",      # -
    "Sneer",        # +
    "Puff",
    "CheekSquint_L",
    "CheekSquint_R"]



BLEND_SHAPE_NAMES = BLEND_SHAPE_NAMES_FS2014_1_CUSTOM




# 10 Faceshift control channels, to operate eyelids.
# They are mapped to the rotation of the eyelid controllers on the face.
# The key if the FaceShift channel name.
# The data is a list of 4 vectors, each one an XYZ euler angles triplet.
# The order of application is defined in the 'MakeHumanTools.BoneSet.MH_EYELID_CONTROLLERS' list.
FS_TO_MH_EYELIDS_ROTATION_FS2014_1 = {

    # Handled by the 
    "EyeBlink_R"    : [  (0.0,0.0,0.0),  (0.436,0.0,0.0),  (0.0,0.0,0.0),  (0.0,0.0,0.0),  ]
    ,"EyeBlink_L"   : [  (0.436,0.0,0.0),  (0.0,0.0,0.0),  (0.0,0.0,0.0),  (0.0,0.0,0.0),  ]
    ,"EyeSquint_R"  : [  (0.0,0.0,0.0),  (0.0,0.0,0.0),  (0.0,0.0,0.0),  (-0.156,0.0,0.0),  ]
    ,"EyeSquint_L"  : [  (0.0,0.0,0.0),  (0.0,0.0,0.0),  (-0.156,0.0,0.0),  (0.0,0.0,0.0),  ]
    ,"EyeDown_R"    : [  (0.0,0.0,0.0),  (0.188,0.0,0.0),  (0.0,0.0,0.0),  (0.409,0.0,0.0),  ]
    ,"EyeDown_L"    : [  (0.188,0.0,0.0),  (0.0,0.0,0.0),  (0.409,0.0,0.0),  (0.0,0.0,0.0),  ]
#    "EyeIn_L",     # can't be done in MakeHuman rig
#    "EyeIn_R",     # can't be done in MakeHuman rig
    ,"EyeOpen_R"    : [  (0.0,0.0,0.0),  (-0.516,0.0,0.0),  (0.0,0.0,0.0),  (0.147,0.0,0.0),  ]
    ,"EyeOpen_L"    : [  (-0.516,0.0,0.0),  (0.0,0.0,0.0),  (0.147,0.0,0.0),  (0.0,0.0,0.0),  ]
#    "EyeOut_L",    # can't be done in MakeHuman rig
#    "EyeOut_R",    # can't be done in MakeHuman rig
    ,"EyeUp_R"      : [  (0.0,0.0,0.0),  (-0.516,0.0,0.0),  (0.0,0.0,0.0),  (-0.049,0.0,0.0),  ]
    ,"EyeUp_L"      : [  (-0.516,0.0,0.0),  (0.0,0.0,0.0),  (-0.049,0.0,0.0),  (0.0,0.0,0.0),  ]
}



# This dictionay maps the full value (1.0) of a FaceShift control channel to a set of vectors to apply to the MakeHuman face control rig.
# They are 36 (46 total - 10 for the eyelids) FaceShift control channels.
# The key if the FaceShift channel name.
# The data is a list of 25 XYZ vectors. 
# The order of application is defined in the 'MakeHumanTools.BoneSet.MH_FACIAL_CONTROLLERS' list.
FS_TO_MH_FACECONTROLLERS_TRANSLATION_FS2014_1 = {

    "BrowsD_R"      : [ (0.0,0.0,0.1), (0.0,0.0,0.0), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.15), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"BrowsD_L"     : [ (0.0,0.0,0.1), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.15), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]

    #,"BrowsU_C"     : [ (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,-0.25), (0.0,0.0,0.05), (0.0,0.0,0.05), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"BrowsU_C"     : [ (0.000,0.000,0.000), (0.000,0.000,-0.150), (0.000,0.000,-0.150), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    #,"BrowsU_L"     : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"BrowsU_L"     : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.150), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    #,"BrowsU_R"     : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"BrowsU_R"     : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.150), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"BrowsSqueeze" : [ (0.000,0.000,0.150), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]

    ,"JawOpen"      : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.100,0.0,0.0), (-0.100,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.060), (0.0,0.0,0.060), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.100,0.0,0.0), (-0.100,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.25),  ]
#   ,"LipsTogether",    # Can't be done in MakeHuman rig
    ,"JawChew"      : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.180), (0.000,0.000,0.100), (0.000,0.000,0.100), (0.000,0.000,-0.077), (0.000,0.000,-0.220), (0.000,0.000,-0.220), (0.000,0.000,0.000), (0.000,0.000,0.060), (0.000,0.000,0.060), (0.050,0.000,0.000), (-0.050,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.035),  ]
#    "JawLeft", # handled with bones
#    "JawRight", # handled with bones
#    "JawFwd",  # Can't be done in MakeHuman rig

    ,"LipsUpperUp_L"    : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.025), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.06), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"LipsUpperUp_R"    : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.025), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.06), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"LipsLowerDown_L"  : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.006),  ]
    ,"LipsLowerDown_R"  : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.006),  ]
    ,"LipsUpperClose"   : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"LipsLowerClose"   : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.150), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]

    ,"MouthSmile_L"     : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (-0.150,0.000,-0.150), (0.000,0.000,0.000), (0.000,0.000,0.100), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.020), (0.000,0.000,-0.025), (0.000,0.000,0.000), (0.000,0.000,0.000), (-0.200,0.000,-0.060), (0.000,0.000,0.000), (-0.120,0.000,-0.250), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"MouthSmile_R"     : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.150,0.000,-0.150), (0.000,0.000,0.100), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.020), (0.000,0.000,0.000), (0.000,0.000,-0.025), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.200,0.000,-0.060), (0.000,0.000,0.000), (0.120,0.000,-0.250), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"MouthDimple_L"    : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (-0.100,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.050), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.050), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (-0.200,0.0,-0.025), (0.0,0.0,0.0), (-0.200,0.0,-0.150), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"MouthDimple_R"    : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.100,0.0,0.0), (0.0,0.0,0.050), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.050), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.200,0.0,-0.025), (0.0,0.0,0.0), (0.200,0.0,-0.150), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]

    ,"LipsStretch_L"    : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (-0.100,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (-0.150,0.000,0.000), (0.000,0.000,0.000), (-0.250,0.000,0.180), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"LipsStretch_R"    : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.100,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.150,0.000,0.000), (0.000,0.000,0.000), (0.250,0.000,0.180), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"MouthFrown_L"     : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.050), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (-0.150,0.000,0.000), (0.000,0.000,0.000), (-0.085,0.000,0.170), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"MouthFrown_R"     : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.050), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.150,0.000,0.000), (0.000,0.000,0.000), (0.085,0.000,0.170), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"MouthPress_L"     : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (-0.150,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.080), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.075), (0.000,0.000,0.000), (-0.050,0.000,-0.200), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"MouthPress_R"     : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.150,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.080), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.075), (0.000,0.000,0.000), (0.050,0.000,-0.200), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]

    ,"LipsPucker"       : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.250), (0.000,0.000,0.070), (0.000,0.000,0.070), (0.000,0.000,-0.220), (0.000,0.000,-0.050), (0.000,0.000,-0.050), (0.000,0.000,-0.180), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.170,0.000,0.000), (-0.170,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.005),  ]
    ,"LipsFunnel"       : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.200), (0.000,0.000,-0.100), (0.000,0.000,-0.100), (0.000,0.000,-0.020), (0.000,0.000,0.100), (0.000,0.000,0.100), (0.000,0.000,-0.250), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.200,0.000,0.000), (-0.200,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"MouthLeft"        : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.100), (0.000,0.000,0.000), (-0.100,0.000,-0.060), (0.000,0.000,0.000), (-0.180,0.000,-0.250), (-0.150,0.000,-0.080), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"MouthRight"       : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.100), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.100,0.000,-0.060), (0.150,0.000,-0.080), (0.180,0.000,-0.250), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"ChinLowerRaise"   : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.220), (0.000,0.000,-0.200), (0.000,0.000,-0.200), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.050), (0.000,0.000,-0.050), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"ChinUpperRaise"   : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.050), (0.000,0.000,-0.210), (0.000,0.000,-0.210), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.050), (0.000,0.000,-0.050), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"Sneer_L"          : [ (0.000,0.000,0.200), (0.000,0.000,0.050), (0.000,0.000,0.050), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.250), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"Sneer_R"          : [ (0.000,0.000,0.200), (0.000,0.000,0.050), (0.000,0.000,0.050), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.250), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"Puff"             : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (-0.250,0.000,0.000), (0.250,0.000,0.000), (0.000,0.000,-0.098), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.103), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.112,0.000,0.000), (-0.112,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"CheekSquint_L"    : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.050), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.250), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]
    ,"CheekSquint_R"    : [ (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.050), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,-0.250), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000), (0.000,0.000,0.000),  ]

}





FS_TO_MH_FACECONTROLLERS_TRANSLATION = FS_TO_MH_FACECONTROLLERS_TRANSLATION_FS2014_1



# This applies the FaceShift channel values to the Fce control rig using the manually calibrated mapping matrix
def Face2Rig(target_object, bs_names, bs_vals):

    # Prepare the accumulation vector: a list of 20 3D vectors
    n_of_displacements = len(BoneSet.MH_FACIAL_CONTROLLERS)
    #print("this should be 25: " + str(n_of_displacements) )
    
    # The starting value is a 0-vector that will be summed with values from the mapping
    displacements = [ mathutils.Vector((0,0,0)) for i in range(n_of_displacements) ]
    #print("also this should be 20: " + str(len(displacements)) )
    
    jaw_rot_z = 0   # degrees
    
    # For each channel (bs_name), look-up the mapping vector in the dictionary and add to the accumulator.
    for bs_name, bs_val in zip(bs_names, bs_vals):
        
        # Quick skip if the faceshift blendshape is not having influence
        # No. If it is at 0, it means that we want to put the value of the blandshapes back to 0.
        #if(bs_val == 0):
        #    continue

        #        
        # Special case for Jaw bone rotation
        if(bs_name == "JawLeft"):
            jaw_rot_z += bs_val * 8    # 5 degrees is the max side jaw extension
            continue
        elif(bs_name == "JawRight"):
            jaw_rot_z += bs_val * (-8)    # 5 degrees is the max side jaw extension
            continue
        
        if(not bs_name in FS_TO_MH_FACECONTROLLERS_TRANSLATION):
            #print("No mapping for " + bs_name)
            continue
        

        # Take the list of displacement triplets for this blend shape. Remember that the list is composed of 3-sized sequences, not vectors.
        bs_disps = FS_TO_MH_FACECONTROLLERS_TRANSLATION[bs_name]
        #print("++This should be 20: " + str(len(bs_disps)))

        #print(" =========== For "+bs_name+" at "+str(bs_val))
        
        # Accumulate
        #displacements_avg_counters = [ 0 for i in range(len(displacements)) ] # will keep the counter for the average calculator
        for tot_bs_disp, bs_disp in zip(displacements, bs_disps):
            #print("Adding " + str(bs_disp) + " to " + str(tot_bs_disp))

            # Modulate according to blend shape value 
            rig_displacement_vect = mathutils.Vector(bs_disp) * bs_val

            # Add to the total
            tot_bs_disp += rig_displacement_vect

            #print("For "+bs_name+" at "+str(bs_val))
            #print("   " + str(rig_displacement_vect) + " --> "  +str (tot_bs_disp) )

    #print("  ==> Total on disp[1] " + str(displacements[1]) )


    # Take reference to the rig bones...
    bones = bpy.data.objects[target_object].pose.bones

    # ... set Jaw bone rotation
    bones[BoneSet.MH_CONTROLLER_JAW].rotation_mode = 'XYZ'
    bones[BoneSet.MH_CONTROLLER_JAW].rotation_euler.z = math.radians(jaw_rot_z)


    LOG_BASE = 3.5

    # ... and copy the displacement vectors in them.
    for i, rig_name in enumerate(BoneSet.MH_FACIAL_CONTROLLERS):
        #if(displacements[i].length > 0.25):
        #    print("Saturation for " + rig_name +": "+ str(displacements[i].length))
        
        # Set the value        
        #print("Setting " + rig_name + "("+str(i)+") to "+str(displacements[i]))
        bones[rig_name].location.xyz = displacements[i]
        

#
#
#
def Eyelids2Rig(target_object, bs_names, bs_vals):
    # Prepare the accumulation vector: a list of 4 3D vectors (each is a XYZ rotation)
    n_of_controllers = len(BoneSet.MH_EYELID_CONTROLLERS)
    
    # The starting value is a 0-vector that will be summed with values from the mapping
    displacements = [ mathutils.Vector((0,0,0)) for i in range(n_of_controllers) ]

    # For each channel (bs_name), look-up the mapping vector in the dictionary and add to the accumulator.
    for bs_name, bs_val in zip(bs_names, bs_vals):

        if(not bs_name in FS_TO_MH_EYELIDS_ROTATION_FS2014_1):
            continue

        #print("Eyelids2Rig: computing rotation for blendshape "+bs_name+ "\t"+str(bs_val))

        # Take the list of displacement triplets for this blend shape. Remember that the list is composed of 3-sized sequences, not vectors.
        bs_disps = FS_TO_MH_EYELIDS_ROTATION_FS2014_1[bs_name]
        #print("++This should be 20: " + str(len(bs_disps)))

        #print(" =========== For "+bs_name+" at "+str(bs_val))
        
        # Accumulate
        for tot_bs_disp, bs_disp in zip(displacements, bs_disps):
            #print("Adding " + str(bs_disp) + " to " + str(tot_bs_disp))

            # Modulate according to blend shape value 
            rig_displacement_vect = mathutils.Vector(bs_disp) * bs_val

            # Add to the total
            tot_bs_disp += rig_displacement_vect

    # Take reference to the rig bones...
    bones = bpy.data.objects[target_object].pose.bones

    # ... and copy the displacement vectors in them.
    for i, rig_name in enumerate(BoneSet.MH_EYELID_CONTROLLERS):
        #print(rig_name+"\t"+str(displacements[i]))
        bones[rig_name].rotation_mode = 'XYZ'
        bones[rig_name].rotation_euler = displacements[i]


#
#
#
XZ_mirror_matrix = mathutils.Matrix.Rotation(0, 3, 'X')
XZ_mirror_matrix[0] = [1,0,0]
XZ_mirror_matrix[1] = [0,-1,0]
XZ_mirror_matrix[2] = [0,0,-1]


def HeadRot2Rig(target_object, head_rotation_quat):
    # Take reference to the rig bones...
    bones = bpy.data.objects[target_object].pose.bones
    
    bones[BoneSet.MH_CONTROLLER_NECK].rotation_mode = 'QUATERNION'
    bones[BoneSet.MH_CONTROLLER_NECK].rotation_quaternion = (XZ_mirror_matrix * head_rotation_quat.to_matrix() * XZ_mirror_matrix.inverted()).to_quaternion()


def EyesRot2Skeleton(target_object, leye_theta, leye_phi, reye_theta, reye_phi):
    #print(str(leye_theta) + "\t" + str(leye_phi))

    # Take reference to the rig bones...
    bones = bpy.data.objects[target_object].pose.bones

    gaze_bone = bones[BoneSet.MH_CONTROLLER_GAZE]
    
    # This is the matrix of the Gaze at "stand position". Constant. Might be computed only once at initialization.
    gaze_stand_matrix = gaze_bone.matrix * gaze_bone.matrix_basis.inverted()
    #print(str(gaze_stand_matrix))
    
    GAZE_DISTANCE = 6 # The distance of the Gaze controller from the eye
    # The rotation of the Neck bone (hence, the head) is stored in the rotation of its parent bone: DEF-chest-1.
    head_absolute_rotation = bones["DEF-chest-1"].rotation_quaternion
    
    eye_rot_euler = mathutils.Euler((math.radians(leye_theta),0,math.radians(-leye_phi)), 'XYZ')
    
    #new_gaze_absolute_direction = head_matrix.to_quaternion() * eye_rot_euler.to_quaternion() * mathutils.Vector((0, -GAZE_DISTANCE, 0))
    new_gaze_absolute_direction = head_absolute_rotation * eye_rot_euler.to_quaternion() * mathutils.Vector((0, -GAZE_DISTANCE, 0))
    
    #new_gaze_absolute_location = bones["Eye_L"].matrix.to_translation() + new_gaze_absolute_direction
    new_gaze_absolute_location = bones["DEF-eye.L"].matrix.to_translation() + new_gaze_absolute_direction
    
    new_gaze_location = gaze_stand_matrix * new_gaze_absolute_location
    
    #print("Setting Gaze to " + str(new_gaze_location))
    
    gaze_bone.location = new_gaze_location
    

#
#

# Support method to map the sull blend shape value of a FaceShift Studio back to the rig.
def fs_channel_to_rig(fs_channel_name):
    arm = get_selected_armature()
    if(arm==None):
        print("No armature selected")


    rig_values = FS_TO_MH_FACECONTROLLERS_TRANSLATION[fs_channel_name]
    
    assert len(rig_values) == len(BoneSet.MH_FACIAL_CONTROLLERS)
    
    bones = arm.pose.bones
    
    for rig_name, rig_value in zip(BoneSet.MH_FACIAL_CONTROLLERS, rig_values):
        bones[rig_name].location = rig_value # mathutils.Vector(rig_value)



# Retrieve the currently selected armature. Returns None if no appropriate MakeHuman compatible armature is found.
def get_selected_armature():
    objs = bpy.context.selected_objects
    if(len(objs) < 1):
        return None

    armature = None

    if(objs[0].type == 'ARMATURE'):
        armature = objs[0]
    elif(objs[0].type == 'MESH'):
        # maybe I could also use find_armature()
        if(objs[0].parent != None):
            if(objs[0].parent.type == 'ARMATURE'):
                armature = objs[0].parent

    return armature
                


#
# 
# Decodes the binary UDP packets incoming from FaceShift studio.
# Also, calls the subroutines to apply the values to the specific body parts.
def decode_faceshift_datastream(target_object, data):
    """Takes as input the bytes of a binary DataStream received via network.
    If it is a Tracking State block (ID 33433) then extract some data (info, blendshapes, markers, ...) and applies it to the MakeHuman skeleton.
    """

    # block_id = struct.unpack_from('H', data)
    # print("Received block id " + str(block_id)) ;

    offset = 0
    block_id, version, block_size = struct.unpack_from('HHI', data, offset)
 
    #print("ID, v, size = " + str(block_id) + "," + str(version) + "," + str(block_size) )

    offset += 8

    if(block_id == BLOCK_ID_TRACKING_STATE):
        n_blocks, = struct.unpack_from('H', data, offset)
        #print("n_blocks = " + str(n_blocks))
        offset += 2

        track_ok = 0                # Will be a byte: 1 if tracking ok, 0 otherwise.
        head_rotation_quat = None   # Will be filled with the rotation using mathutils.Quaternion
        blend_shape_values = []     # Will be a list of float in the range 0-1
        #eyes_values = None          # Will be a sequence of 4 angle values
        markers_position = []       # Will be a list of mathutils.Vector
    
        curr_block = 0
        while(curr_block < n_blocks):
            block_id, version, block_size = struct.unpack_from('HHI', data, offset)
            #print("ID, v, size = " + str(block_id) + "," + str(version) + "," + str(block_size) )
        
            # put the offset at the beginning of the block
            offset += 8
        
            if(block_id == 101):        # Frame Information blobk (timestamp and tracking status)
                ts, track_ok = struct.unpack_from('dB', data, offset)
                #print("timestamp, track_ok " + str(ts) + ", " + str(track_ok) )
                #offset += 9
            elif(block_id == 102):      # Pose block (head rotation and position)
                x,y,z,w = struct.unpack_from('ffff', data, offset)
                head_rotation_quat = mathutils.Quaternion((w,x,y,z))
            elif(block_id == 103):      # Blendshapes block (blendshape values)
                n_coefficients, = struct.unpack_from('I', data, offset)
                #print("Blend shapes count="+ str(n_coefficients) )
                i = 0
                #coeff_list = ""
                while(i < n_coefficients):
                    # Offset of the block, plus the 4 bytes for int n_coefficients, plus 4 bytes per float
                    val, = struct.unpack_from('f', data, offset + 4 + (i*4))
                    blend_shape_values.append(val)
                    #coeff_list += repr(val) + " "
                    i += 1
                #print("Values: " + coeff_list)
            elif(block_id == 104):     # Eyes block (eyes gaze)
                leye_theta, leye_phi, reye_theta, reye_phi = struct.unpack_from('ffff', data, offset)
            elif(block_id == 105):     # Markers block (absolute position of mark points)
                n_markers, = struct.unpack_from('H', data, offset)
                #print("n markers="+str(n_markers))
                i = 0
                while(i < n_markers):
                    # Offset of the block, plus the 2 bytes for int n_markers, plus 4 bytes for each x,y,z floats
                    x, y, z = struct.unpack_from('fff', data, offset + 2 + (i*4*3))
                    #print("m" + str(i) + " " + str(x) + "\t" + str(y) + "\t" + str(z))
                    markers_position.append(mathutils.Vector((x,y,z)))
                    i += 1
        
            curr_block += 1
            offset += block_size

        # end -- while on blocks. Track State scan complete

        #
        # Handle EYELIDS
        if(track_ok==1):
            Eyelids2Rig(target_object, BLEND_SHAPE_NAMES, blend_shape_values)


        #
        # Handle HEAD ROTATION
        if(track_ok==1):
            if(head_rotation_quat!=None):
                HeadRot2Rig(target_object, head_rotation_quat)
                pass

        #
        # Handle BLEND SHAPES
        #print(str(track_ok) + " - " + str(len(blend_shape_values)))
        if(track_ok==1):
            Face2Rig(target_object, BLEND_SHAPE_NAMES, blend_shape_values)
            pass

        #
        # Handle BLEND SHAPES
        #print(str(track_ok) + " - " + str(len(blend_shape_values)))
        if(track_ok==1):
            EyesRot2Skeleton(target_object, leye_theta, leye_phi, reye_theta, reye_phi)
            pass




def insert_mh_keyframe(armature_name, frame):
    #print("Inserting frame at " + str(frame) )
    
    bones = bpy.data.objects[armature_name].pose.bones

    # Face controllers location
    for ctrl in BoneSet.MH_FACIAL_CONTROLLERS:
        bones[ctrl].keyframe_insert(data_path='location', frame=frame)

    # Eyelids rotation
    for ctrl in BoneSet.MH_EYELID_CONTROLLERS:
        bones[ctrl].keyframe_insert(data_path='rotation_euler', frame=frame)
        
    # Jaw rotation
    bones[BoneSet.MH_CONTROLLER_JAW].rotation_mode = 'XYZ'
    bones[BoneSet.MH_CONTROLLER_JAW].keyframe_insert(data_path='rotation_euler', frame=frame)
    
    # Head rotation
    bones[BoneSet.MH_CONTROLLER_NECK].rotation_mode = 'QUATERNION'
    bones[BoneSet.MH_CONTROLLER_NECK].keyframe_insert(data_path='rotation_quaternion', frame=frame)

    # Eyes rotation
    bones[BoneSet.MH_CONTROLLER_GAZE].keyframe_insert(data_path='location', frame=frame)



def delete_mh_keyframe(armature_name, frame):
    #print("Deleting keyframes for armature "+armature_name)

    bones = bpy.data.objects[armature_name].pose.bones

    # Face controllers location
    for ctrl in BoneSet.MH_FACIAL_CONTROLLERS:
        bones[ctrl].keyframe_delete(data_path='location', frame=frame)

    # Eyelids rotation
    for ctrl in BoneSet.MH_EYELID_CONTROLLERS:
        bones[ctrl].keyframe_delete(data_path='rotation_euler', frame=frame)
        
    # Jaw rotation
    bones[BoneSet.MH_CONTROLLER_JAW].rotation_mode = 'XYZ'
    bones[BoneSet.MH_CONTROLLER_JAW].keyframe_delete(data_path='rotation_euler', frame=frame)
    
    # Head rotation
    bones[BoneSet.MH_CONTROLLER_NECK].rotation_mode = 'QUATERNION'
    bones[BoneSet.MH_CONTROLLER_NECK].keyframe_delete(data_path='rotation_quaternion', frame=frame)

    # Reset Eyes rotation
    bones[BoneSet.MH_CONTROLLER_GAZE].keyframe_delete(data_path='location', frame=frame)

    


class MakeHumanResetFacialRig(bpy.types.Operator):
    """This is the Blender operator to reset the MakeHumn facial rig to default position."""

    bl_idname = "object.makehuman_reset_facial_rig"
    bl_label = "Reset MakeHuman Facial Rig"

    def execute(self, context):
        
        # Retrieve the currently selected armature
        armature = get_selected_armature()
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}

        bones = bpy.data.objects[armature.name].pose.bones

        # Reset all controllers position
        for ctrl in BoneSet.MH_FACIAL_CONTROLLERS:
            bones[ctrl].location.xyz = 0,0,0

        # Reset Eyelids
        for ctrl in BoneSet.MH_EYELID_CONTROLLERS:
            bones[ctrl].rotation_mode = 'XYZ'
            bones[ctrl].rotation_euler.x = 0.0

            
        # Reset Jaw rotation
        bones[BoneSet.MH_CONTROLLER_JAW].rotation_mode = 'XYZ'
        bones[BoneSet.MH_CONTROLLER_JAW].rotation_euler.z = 0.0
        
        # Reset head rotation
        bones[BoneSet.MH_CONTROLLER_NECK].rotation_mode = 'QUATERNION'
        bones[BoneSet.MH_CONTROLLER_NECK].rotation_quaternion = mathutils.Quaternion((1,0,0,0))

        # Reset Eyes rotation
        bones[BoneSet.MH_CONTROLLER_GAZE].location = 0,0,0

        return {'FINISHED'}



class MakeHumanPrintFacialRig(bpy.types.Operator):
    """This is the Blender operator to print out the values of the facial control rig translation vectors.
    
    This is used during development to calibrate correspondences between FaceShift channel values and MakeHuman control rigs."""

    bl_idname = "object.makehuman_print_facial_rig"
    bl_label = "Print MakeHuman Facial Rig values"

    def execute(self, context):
        
        # Retrieve the currently selected armature
        armature = get_selected_armature()
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}

        bones = bpy.data.objects[armature.name].pose.bones

        formatter = "{:.3f}"

        #
        # Print out rotation for lids
        print( "[ ", end="")
        for ctrl in BoneSet.MH_EYELID_CONTROLLERS:
            rot = bones[ctrl].rotation_euler
            #print(" (" + str(rot.x) + "," + str(rot.y) + "," + str(rot.z) + "), ", end="")
            print(" (" + formatter.format(rot.x) + "," + formatter.format(rot.y) + "," + formatter.format(rot.z) + "), ", end="")

        print(" ]")

        #
        # Print out translation for other facial controllers
        print( "[ ", end="")
        for ctrl in BoneSet.MH_FACIAL_CONTROLLERS:
            loc = bones[ctrl].location
            # Limit known approximation errors in control rig movememnts
            if(abs(loc.x) < 0.00001): loc.x = 0
            if(abs(loc.y) < 0.00001): loc.y = 0
            if(abs(loc.z) < 0.00001): loc.z = 0
            # Print out in python code format to facilitate copy/paste into code
            print( "(" + formatter.format(loc.x) + "," + formatter.format(loc.y) + "," + formatter.format(loc.z) + "), ", end="")
        print(" ]")


        return {'FINISHED'}

#
# OPERATOR: INSERT KEYFRAME
#
class MakeHumanInsertKeyframe(bpy.types.Operator):
    """This is the Blender operator to insert a keyframe for all MakeHuman bones used to drive the facial expression."""

    bl_idname = "object.makehuman_insert_keyframe"
    bl_label = "Insert MakeHuman Facial Rig keyframe"

    def execute(self, context):
        
        # Retrieve the currently selected armature
        armature = get_selected_armature()
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}
        
        insert_mh_keyframe(armature.name, bpy.context.scene.frame_current)
        return {'FINISHED'}


#
# OPERATOR: DELETE KEYFRAME
#
class MakeHumanDeleteKeyframe(bpy.types.Operator):
    """This is the Blender operator to delete a keyframe for all MakeHuman bones used to drive the facial expression."""

    bl_idname = "object.makehuman_delete_keyframe"
    bl_label = "Delete MakeHuman Facial Rig keyframe"

    def execute(self, context):
        
        # Retrieve the currently selected armature
        armature = get_selected_armature()
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}
        
        delete_mh_keyframe(armature.name, bpy.context.scene.frame_current)
        return {'FINISHED'}







#
# OPERATOR: FACESHIFT MODAL
#
class FaceShiftModal(bpy.types.Operator):
    """This is the Blender operator to start the FaceShift timed modal listening as long as ESC isn't pressed."""
    
    bl_idname = "object.faceshift_modal"
    bl_label = "FaceShift Start Net Listener"
    
    _updating = False
    
    
    # The object whose armature is going to be piloted piloting    
    target_object = None

    instantiateTimer = BoolProperty(name="instantiate_timer", default=True, description="Whether this operator must create a timer for continuous updates.")


    def modal(self, context, event):
        if event.type == 'ESC':
            return self.cancel(context)

        if(self.sock == None):
            return {'CANCELLED'}
        
        if event.type == 'TIMER' and not self._updating:
            self._updating = True
            
            try:
                msg = self.sock.recv(4096)
                #print("Received : " + str(msg))
                decode_faceshift_datastream(self.target_object, msg)

                #
                # Handle RECORDING
                #
                
                # Recording logic:
                # if the section is None, the space is pausing and resuming the recording from the current frame
                # If a section is selected, resuming the recording restart from the beginning of the section, up to a maximum time.
                if(context.scene.tool_settings.use_keyframe_insert_auto):
                    
                    #print(str(self.update_count) + ":\t" + str(self.frame_record_start) + "\t--> " + str(frame))
                    insert_mh_keyframe(self.target_object, bpy.context.scene.frame_current)

            except socket.timeout as to_msg:
                #print("We know it: " + str(to_msg))
                pass    # We know. Can happen very often
            except OSError as msg:
                # Note that we can enter this section also because we explicitly closed
                # the socket to interrupt receiving messages (see the terminate method)
                print("FaceShift thread, recv Exception: "+ str(msg))
                
                if(self.sock != None):
                    self.sock.close()
                    self.sock = None
            
            self._updating = False
        
        return {'PASS_THROUGH'}
        #return {'RUNNING_MODAL'}


    def execute(self, context):
        
        # Retrieve the currently selected armature
        armature = get_selected_armature()
        
        if(armature == None):
            self.report({'INFO'}, "No armature found!")
            return {'CANCELLED'}
            
        self.target_object = armature.name
        print("Running FaceShift receiver on object '" + str(self.target_object) + "'")
        
        self.report({'INFO'}, "FaceShift starting")
        
        context.window_manager.modal_handler_add(self)
        
        if(self.instantiateTimer):
            self._timer = context.window_manager.event_timer_add(UPDATE_DELAY, context.window)

        # If recording is enabled, it will start from this frame
        #print("SECT="+context.scene.faceshift_record_section)
        #sect_num = section_number(context.scene.faceshift_record_section)
        #if(sect_num==0):    # if the None section
        #    self.frame_record_start = bpy.context.scene.frame_current
        #else:
        #    self.frame_record_start = sect_num * FRAMES_PER_SECTION
        
        
        # First try to create the socket and bind it
        try:
            print("Creating socket...")
            # The socket listening to incoming data. Its status will be always synchronized with the singleton attribute:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            #self.sock.setblocking(False)
            self.sock.settimeout(0.1)
            #self.sock.setsockopt(level, optname, value)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1500)    # No buffer. We take the latest, if present, or nothing.
            print("Binding...")
            self.sock.bind((BINDING_ADDR, LISTENING_PORT))
            print("Bound.")
            #self.report({'INFO'}, "FaceShift Modal listening...")
        except OSError as msg:
            print("FaceShift thread, binding Exception: "+ str(msg))
            self.report({'ERROR'}, "FaceShift thread, binding Exception: "+str(msg))

            if(self.sock != None):
                self.sock.close()
                self.sock = None
            
        return {'RUNNING_MODAL'}


    def cancel(self, context):
        if(self._timer != None):
            context.window_manager.event_timer_remove(self._timer)
        self.timer = None
        
        print("FaceShift modal command, closing socket...")
        if(self.sock != None):
            self.sock.close()
            self.sock = None

        print("closed.")
        
        self.report({'INFO'}, "FaceShift exit")
        return {'CANCELLED'}
    
    
    def __init__(self):
        self._timer = None

    
    def __del__(self):
        # The sock attribute might not have been defined if the command was never run
        if(hasattr(self, 'sock')):
            if(self.sock != None):
                self.sock.close()
                self.sock = None

        if(hasattr(self, '_timer')):
            if(self._timer != None):
                print("Removing surviving timer")
                bpy.context.window_manager.event_timer_remove(self._timer)
                self._timer = None




class FaceShiftPanel(bpy.types.Panel):
    bl_label = "FaceShift Control"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
    
    # global memory of whether we a re recording or not.
    #s_is_recording = bpy.props.BoolProperty(name="FaceShiftRecord")


    def draw(self, context):
        self.layout.operator("object.faceshift_modal", text='Start Net Listener')
        self.layout.separator()
        self.layout.operator("object.makehuman_reset_facial_rig", text='Reset Expression')
        self.layout.separator()
        self.layout.operator("object.makehuman_insert_keyframe", text='Insert Keyframe')
        self.layout.operator("object.makehuman_delete_keyframe", text='Delete Keyframe')
        self.layout.operator("object.makehuman_print_facial_rig", text='Print data to console')


def register():
    bpy.utils.register_class(MakeHumanResetFacialRig)
    bpy.utils.register_class(MakeHumanPrintFacialRig)
    bpy.utils.register_class(FaceShiftModal)
    bpy.utils.register_class(FaceShiftPanel)
    bpy.utils.register_class(MakeHumanInsertKeyframe)
    bpy.utils.register_class(MakeHumanDeleteKeyframe)
    
def unregister():
    bpy.utils.unregister_class(MakeHumanResetFacialRig)
    bpy.utils.unregister_class(MakeHumanPrintFacialRig)
    bpy.utils.unregister_class(FaceShiftModal)
    bpy.utils.unregister_class(FaceShiftPanel)
    bpy.utils.unregister_class(MakeHumanInsertKeyframe)
    bpy.utils.unregister_class(MakeHumanDeleteKeyframe)


if __name__ == "__main__":
    register()
    print("Registered FaceShift operators")
    