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
import time
import socket
import math
from bpy.props import * # for properties


import copy

import struct

# This is Blender specific
import mathutils


LISTENING_PORT = 33433
#BINDING_ADDR = "127.0.0.1"     # Good for local work
BINDING_ADDR = ''   # Empty string means: bind to all network interfaces

BLOCK_ID_TRACKING_STATE = 33433     # According to faceshift docs

# Delay between modal timed updates when entered the modal command mode. In seconds.
UPDATE_DELAY = 0.04


# These are the names of the FaceShift control channels
# 48 channels
# blend_shape_names = [
#     "EyeBlink_L",
#     "EyeBlink_R",
#     "EyeSquint_L",
#     "EyeSquint_R",
#     "EyeDown_L",
#     "EyeDown_R",
#     "EyeIn_L",
#     "EyeIn_R",
#     "EyeOpen_L",
#     "EyeOpen_R",
#     "EyeOut_L",
#     "EyeOut_R",
#     "EyeUp_L",
#     "EyeUp_R",
#     "BrowsD_L",
#     "BrowsD_R",
#     "BrowsU_C",
#     "BrowsU_L",
#     "BrowsU_R",
#     "JawFwd",
#     "JawLeft",
#     "JawOpen",
#     "JawChew",
#     "JawRight",
#     "MouthLeft",
#     "MouthRight",
#     "MouthFrown_L",
#     "MouthFrown_R",
#     "MouthSmile_L",
#     "MouthSmile_R",
#     "MouthDimple_L",
#     "MouthDimple_R",
#     "LipsStretch_L",
#     "LipsStretch_R",
#     "LipsUpperClose",
#     "LipsLowerClose",
#     "LipsUpperUp",
#     "LipsLowerDown",
#     "LipsUpperOpen",
#     "LipsLowerOpen",
#     "LipsFunnel",
#     "LipsPucker",
#     "ChinLowerRaise",
#     "ChinUpperRaise",
#     "Sneer",
#     "Puff",
#     "CheekSquint_L",
#     "CheekSquint_R"]
    

# New names for v2014.1
# 51 channels
blend_shape_names = [
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

    #"JawChew",
    #"LipsUpperOpen",
    #"LipsLowerOpen",

# 20 Facial control rigs. Listed from top to bottom (arbitrary decision)
# Don't change the order.
mh_facial_controls_name = [
        "PBrows",   # 0
        "PBrow_R",
        "PBrow_L",
        "PUpLid_R",
        "PUpLid_L",
        "PLoLid_L",
        "PLoLid_R",
        
        "PNose",    # 7
        "PCheek_L",
        "PCheek_R",
        
        "PUpLipMid",    # 10
        "PUpLip_R",
        "PUpLip_L",
        "PMouth_R",     # 13
        "PMouth_L",     # 14
        "PLoLip_R",
        "PLoLip_L",
        "PLoLipMid",    # 17
        
        "PMouthMid",    # 18
        "PJaw"
    ]
    
#bpy.data.objects["Human1-mhxrig-expr"]["Mhsmouth_retraction"]
mh_mouth_retraction_eu = "Mhsmouth_retraction"

# This dictionay maps the full value (1.0) of a FaceShift control channel to a set of vectors to apply to the MakeHuman face control rig.
# The key if the FaceShift channel name.
# The data is a list of 20 vectors, each one to be applied as location of a MakeHuman facial control rig
# The order of application is defined in the 'mh_facial_controls_name' list.
fs_to_mh_control_rig_vectors = {
    "EyeBlink_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0) ]
    ,"EyeBlink_L": [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0) ]
    ,"EyeSquint_R": [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0) ]
    ,"EyeSquint_L":[ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0) ]
    ,"EyeDown_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.08), (0.0,0.0,0.20), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"EyeDown_L" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.08), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.20), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
#    "EyeIn_L",     # can't be done in MakeHuman rig
#    "EyeIn_R",     # can't be done in MakeHuman rig
    ,"EyeOpen_R" :[ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.20), (0.0,0.0,0.13), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)]
    ,"EyeOpen_L" :[ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.20), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.13), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)]
#    "EyeOut_L",    # can't be done in MakeHuman rig
#    "EyeOut_R",    # can't be done in MakeHuman rig
    ,"EyeUp_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,-0.055), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"EyeUp_L" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.055), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]

    ,"BrowsD_R" : #[ (0.0,0.0,0.13094329833984375), (0.0,0.0,0.0), (0.0,0.0,0.1571331024169922), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
            # [ (0.0,0.0,0.10), (0.0,0.0,0.0), (0.0,0.0,0.20), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
            [ (0.0,0.0,0.12), (0.0,0.0,0.0), (0.0,0.0,0.12), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    
    ,"BrowsD_L" : #[ (0.0,0.0,0.13094329833984375), (0.0,0.0,0.1571331024169922), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
            #[ (0.0,0.0,0.10), (0.0,0.0,0.20), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
            [ (0.0,0.0,0.12), (0.0,0.0,0.12), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"BrowsU_C": #[ (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0) ]
            [ (0.0,0.0,-0.18), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0) ]
    ,"BrowsU_R" :# [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)]
            [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.12), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)]
    ,"BrowsU_L" : #[ (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)]
            [ (0.0,0.0,0.0), (0.0,0.0,-0.12), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)]


#    "JawFwd",  # Can't be done in MakeHuman rig
#    "JawLeft", # handled with bones
    ,"JawOpen" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.12399999797344208), (0.0,0.0,0.12399999797344208), (0.05900000035762787,0.0,0.0), (-0.05900000035762787,0.0,0.0), (0.0,0.0,-0.16300000250339508), (0.0,0.0,-0.16300000250339508), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.25)  ]
    ,"JawChew" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.14000000059604645), (0.0,0.0,-0.14000000059604645), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.05000000074505806)  ]
#    "JawRight", # handled with bones
    ,"MouthRight" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.25,0.0,0.0), (0.109,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,-0.1775), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"MouthLeft" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (-0.109,0.0,-0.25), (-0.25,0.0,0.0), (0.0,0.0,-0.1775), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"MouthFrown_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.05,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"MouthFrown_L" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (-0.05,0.0,0.20), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"MouthSmile_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.10), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.085,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,-0.15), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"MouthSmile_L" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.10), (0.0,0.0,-0.25), (0.0,0.0,0.0), (-0.085,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,-0.15), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"MouthDimple_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.07), (0.0,0.0,0.0), (0.05,0.0,-0.2), (0.0,0.0,0.0), (0.0,0.0,-0.07), (0.0,0.0,-0.045), (0.0,0.0,0.0), (0.0,0.0,0.0) ]
    ,"MouthDimple_L" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.07), (0.0,0.0,0.0), (-0.05,0.0,-0.20), (0.0,0.0,0.0), (0.0,0.0,-0.07), (0.0,0.0,0.0), (0.0,0.0,-0.045), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"LipsStretch_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.15,0.0,-0.15), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"LipsStretch_L" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (-0.15,0.0,-0.15), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"LipsUpperClose" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (-0.25,0.0,0.05), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"LipsLowerClose": [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (-0.17,0.0,-0.03), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    ,"LipsUpperUp" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.10), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,-0.05), (0.0,0.0,-0.05), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"LipsLowerDown" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.05), (0.0,0.0,0.05), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]

    ,"LipsUpperOpen" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.15,0.0,-0.15), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"LipsLowerOpen" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.20,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]

    ,"LipsFunnel" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.16,0.0,-0.056), (0.0,0.0,0.12), (0.0,0.0,0.12), (0.20,0.0,0.065), (-0.20,0.0,0.065), (0.0,0.0,-0.10), (0.0,0.0,-0.10), (0.17,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"LipsPucker": [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.19,0.0,0.0027), (0.0,0.0,0.09), (0.0,0.0,0.09), (0.25,0.0,0.065), (-0.25,0.0,0.065), (0.0,0.0,-0.05), (0.0,0.0,-0.05), (0.25,0.0,0.25), (0.0,0.0,0.028), (0.0,0.0,0.0)  ]
    
    ,"ChinLowerRaise" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"ChinUpperRaise" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.18125343322753906), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]

    ,"Sneer" : [ (0.0,0.0,0.11), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.15), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"Puff" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.25,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.063,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.1,0.0,0.0), (-0.1,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.127,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"CheekSquint_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.11), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.11), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    ,"CheekSquint_L" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.11), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.11), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]

    # extra duplicated mappings for 2014.1 channels
    #No mapping for JawFwd
    #No mapping for LipsUpperUp_L
    ,"LipsUpperUp_L" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.10), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,-0.05), (0.0,0.0,-0.05), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    #No mapping for LipsUpperUp_R
    ,"LipsUpperUp_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.10), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.25), (0.0,0.0,-0.05), (0.0,0.0,-0.05), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    #No mapping for LipsLowerDown_L
    ,"LipsLowerDown_L" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.05), (0.0,0.0,0.05), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    #No mapping for LipsLowerDown_R
    ,"LipsLowerDown_R" : [ (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.05), (0.0,0.0,0.05), (0.0,0.0,0.25), (0.0,0.0,0.0), (0.0,0.0,0.0),  ]
    #No mapping for MouthPress_L
    #No mapping for MouthPress_R
    #No mapping for Sneer_L
    ,"Sneer_L" : [ (0.0,0.0,0.11), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.15), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
    #No mapping for Sneer_R
    ,"Sneer_R" : [ (0.0,0.0,0.11), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,-0.15), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0), (0.0,0.0,0.0)  ]
}
    





# This applies the FaceShift channel values to the Fce control rig using the manually calibrated mapping dictionay 'fs_to_mh_control_rig_vectors'
def FS2Rig_MappingDict(target_object, bs_names, bs_vals):

    # Prepare the accumulation vector: a list of 20 3D vectors
    n_of_displacements = len(mh_facial_controls_name)
    #print("this should be 20: " + str(n_of_displacements) )
    
    # The starting value is a 0-vector that will be summed with values from the mapping
    displacements = [ mathutils.Vector((0,0,0)) for i in range(n_of_displacements) ]
    #print("also this should be 20: " + str(len(displacements)) )
    
    jaw_rot_z = 0   # degrees
    
    #print("==================")
    
    # For each channel (bs_name), look-up the mapping vector in the dictionary and add to the accumulator.
    for bs_name, bs_val in zip(bs_names, bs_vals):
        
        # Quick skip if the faceshift blendshape is not having influence
        # No. If it is at 0, it means that we want to put the value of the blandshapes back to 0.
        #if(bs_val == 0):
        #    continue
        
        # Special case for Jaw bone rotation
        if(bs_name == "JawLeft"):
            jaw_rot_z += bs_val * 5    # 5 degrees is the max side jaw extension
            continue
        elif(bs_name == "JawRight"):
            jaw_rot_z += bs_val * (-5)    # 5 degrees is the max side jaw extension
            continue
        
        if( not bs_name in fs_to_mh_control_rig_vectors):
            #print("No mapping for " + bs_name)
            continue
        

        # Take the list of displacement triplets for this blend shape. Remember that the list is composed of 3-sized sequences, not vectors.
        bs_disps = fs_to_mh_control_rig_vectors[bs_name]
        #print("++This should be 20: " + str(len(bs_disps)))

        #print(" =========== For "+bs_name+" at "+str(bs_val))
        
        # Accumulate
        displacements_avg_counters = [ 0 for i in range(len(displacements)) ] # will keep the counter for the average calculator
        for tot_bs_disp, bs_disp, i in zip(displacements, bs_disps, range(len(displacements))):
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
    bones["Jaw"].rotation_mode = 'XYZ'
    bones["Jaw"].rotation_euler.z = math.radians(jaw_rot_z)


    LOG_BASE = 3.5

    # ... and copy the displacement vectors in them.
    for rig_name, i in zip(mh_facial_controls_name, range(n_of_displacements)):        
        #if(displacements[i].length > 0.25):
        #    print("Saturation for " + rig_name +": "+ str(displacements[i].length))
        
        #print(" FROM " + str(displacements[i]))

        if(displacements[i].x >= 0):
            displacements[i].x = math.log(1 + displacements[i].x, LOG_BASE)
        else:
            displacements[i].x = -math.log(1 - displacements[i].x, LOG_BASE)

        if(displacements[i].y >= 0):
            displacements[i].y = math.log(1 + displacements[i].y, LOG_BASE)
        else:
            displacements[i].y = -math.log(1 - displacements[i].y, LOG_BASE)

        if(displacements[i].z >= 0):
            displacements[i].z = math.log(1 + displacements[i].z, LOG_BASE)
        else:
            displacements[i].z = -math.log(1 - displacements[i].z, LOG_BASE)

        #print(" --> " + str(displacements[i]))


        # Set the value        
        #print("Setting " + rig_name + "("+str(i)+") to "+str(displacements[i]))
        bones[rig_name].location.xyz = displacements[i]
        
    # Hard-code: Compute the mean of PMouth_R.z and PMouth_L.z, and apply it to MHX Expression Unit "mouth_retraction"
    # "PMouth_R",     # 13
    # "PMouth_L",     # 14

    mouth_retr_avg = - (displacements[13].z + displacements[14].z) / 2.0
    mouth_retr_avg *= 1.8
    #print("Mouth retr at " + str(mouth_retr_avg))
    bpy.data.objects[target_object][mh_mouth_retraction_eu] = mouth_retr_avg
    
    #Quick hack to limit lip upraising
    # "PLoLipMid",    # 17
    if(displacements[17].z < -0.15):
        displacements[17].z = -0.15
        #print("PloLipMid limited!!!")


XZ_mirror_matrix = mathutils.Matrix.Rotation(0, 3, 'X')
XZ_mirror_matrix[0] = [1,0,0]
XZ_mirror_matrix[1] = [0,-1,0]
XZ_mirror_matrix[2] = [0,0,-1]


def HeadRot2Rig(target_object, head_rotation_quat):
    # Take reference to the rig bones...
    bones = bpy.data.objects[target_object].pose.bones
    
    #print("Mult by " + str(XZ_mirror_matrix))
    #print(str(XZ_mirror_matrix.to_quaternion()))

    # ... set Neck bone rotation
    #bones["Neck"].rotation_mode = 'QUATERNION'
    #bones["Neck"].rotation_quaternion = XZ_mirror_matrix.to_quaternion() * head_rotation_quat


    bones["Neck"].rotation_mode = 'QUATERNION'
    bones["Neck"].rotation_quaternion = (XZ_mirror_matrix * head_rotation_quat.to_matrix() * XZ_mirror_matrix.inverted()).to_quaternion()


def EyesRot2Skeleton(target_object, leye_theta, leye_phi, reye_theta, reye_phi):
    #print(str(leye_theta) + "\t" + str(leye_phi))

    # Take reference to the rig bones...
    bones = bpy.data.objects[target_object].pose.bones

    gaze_bone = bones["Gaze"]
    
    # This is the matrix of the Gaze at "stand position". Constant. Might be computed only once at initialization.
    gaze_stand_matrix = gaze_bone.matrix * gaze_bone.matrix_basis.inverted()
    #print(str(gaze_stand_matrix))
    
    GAZE_DISTANCE = 6 # The autonomoously decided distance of the Gaze controller from the eye
    #head_matrix = bones["Neck"].matrix
    #head_rotation = bones["Neck"].rotation_quaternion
    # Yes, Spine3. The rotation of the Neck bone (hence, the head) is stored in the rotation of its parent bone: Spine 3.
    head_absolute_rotation = bones["Spine3"].rotation_quaternion
    
    eye_rot_euler = mathutils.Euler((math.radians(leye_theta),0,math.radians(-leye_phi)), 'XYZ')
    
    #new_gaze_absolute_direction = head_matrix.to_quaternion() * eye_rot_euler.to_quaternion() * mathutils.Vector((0, -GAZE_DISTANCE, 0))
    new_gaze_absolute_direction = head_absolute_rotation * eye_rot_euler.to_quaternion() * mathutils.Vector((0, -GAZE_DISTANCE, 0))
    
    new_gaze_absolute_location = bones["Eye_L"].matrix.to_translation() + new_gaze_absolute_direction
    
    new_gaze_location = gaze_stand_matrix * new_gaze_absolute_location
    
    #print("Setting Gaze to " + str(new_gaze_location))
    
    bones["Gaze"].location = new_gaze_location
    



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
                

class FaceShiftReceiver :
    """This is the receiving Thread listening for FaceShift UDP messages on some port."""
    
    def decode_faceshift_datastream(target_object, data):
        """ Takes as input the bytes of a binary DataStream received via network.
        
         If it is a Tracking State block (ID 33433) then extract some data (info, blendshapes, markers, ...).
         Otherwise None is returned.
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
            # Handle HEAD ROTATION
            if(track_ok==1):                
                if(head_rotation_quat!=None):
                    HeadRot2Rig(target_object, head_rotation_quat)

            #
            # Handle BLEND SHAPES
            #print(str(track_ok) + " - " + str(len(blend_shape_values)))
            if(track_ok==1):
                FS2Rig_MappingDict(target_object, blend_shape_names, blend_shape_values)

            #
            # Handle BLEND SHAPES
            #print(str(track_ok) + " - " + str(len(blend_shape_values)))
            if(track_ok==1):
                EyesRot2Skeleton(target_object, leye_theta, leye_phi, reye_theta, reye_phi)



def insert_mh_keyframe(armature_name, frame):
    #print("Inserting frame at " + str(frame) )
    
    bones = bpy.data.objects[armature_name].pose.bones

    # Reset all controllers position
    for ctrl in mh_facial_controls_name:
        bones[ctrl].keyframe_insert(data_path='location', frame=frame)
        
    # Reset Jaw rotation
    bones["Jaw"].rotation_mode = 'XYZ'
    bones["Jaw"].keyframe_insert(data_path='rotation_euler', frame=frame)
    
    # Reset head rotation
    bones["Neck"].rotation_mode = 'QUATERNION'
    bones["Neck"].keyframe_insert(data_path='rotation_quaternion', frame=frame)

    # Reset Eyes rotation
    bones["Gaze"].keyframe_insert(data_path='location', frame=frame)
    
    # mouth retraction
    #bpy.data.objects["Human1-mhxrig-expr"].get("Mhsmouth_retraction")
    # bpy.data.objects["Human1-mhxrig-expr"].keyframe_insert(data_path='["Mhsmouth_retraction"]', frame=1)
    bpy.data.objects[armature_name].keyframe_insert(data_path='["Mhsmouth_retraction"]', frame=frame)


def delete_mh_keyframe(armature_name, frame):
    #print("Deleting keyframes for armature "+armature_name)

    bones = bpy.data.objects[armature_name].pose.bones

    # Reset all controllers position
    for ctrl in mh_facial_controls_name:
        bones[ctrl].keyframe_delete(data_path='location', frame=frame)
        
    # Reset Jaw rotation
    bones["Jaw"].rotation_mode = 'XYZ'
    bones["Jaw"].keyframe_delete(data_path='rotation_euler', frame=frame)
    
    # Reset head rotation
    bones["Neck"].rotation_mode = 'QUATERNION'
    bones["Neck"].keyframe_delete(data_path='rotation_quaternion', frame=frame)

    # Reset Eyes rotation
    bones["Gaze"].keyframe_delete(data_path='location', frame=frame)

    # mouth retraction
    bpy.data.objects[armature_name].keyframe_delete(data_path='["Mhsmouth_retraction"]', frame=frame)

    


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
        for ctrl in mh_facial_controls_name:
            bones[ctrl].location.xyz = 0,0,0
            
        # Reset Jaw rotation
        bones["Jaw"].rotation_mode = 'XYZ'
        bones["Jaw"].rotation_euler.z = 0.0
        
        # Reset head rotation
        bones["Neck"].rotation_mode = 'QUATERNION'
        bones["Neck"].rotation_quaternion = mathutils.Quaternion((1,0,0,0))

        # Reset Eyes rotation
        bones["Gaze"].location = 0,0,0

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

        print( "[ ", end="")
        for ctrl in mh_facial_controls_name:
            loc = bones[ctrl].location
            # Limit known approximation errors in control rig movememnts
            if(abs(loc.x) < 0.00001): loc.x = 0
            if(abs(loc.y) < 0.00001): loc.y = 0
            if(abs(loc.z) < 0.00001): loc.z = 0
            # Print out in python code format to facilitate copy/paste into code
            print( "(" + str(loc.x) + "," + str(loc.y) + "," + str(loc.z) + "), ", end="")

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
                FaceShiftReceiver.decode_faceshift_datastream(self.target_object, msg)

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
    