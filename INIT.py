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
# Copy and paste this script into a text buffer of your Blender scene.
# Run it to initialize the whole system.
#


import bpy
import os
import sys


#
# Direct Script loading
FILES = [
	"SimplifyMultipleFCurves/SimplifyMultipleFCurves.py",
	"TrimFCurves/TrimFCurves.py",
    "FaceShift2Blender/FaceShiftControl.py",
    "Scripts/DemoTools.py",
    #"Script/ColorTargets.py",
    #"Script/ExperimentTools.py"
]

# Compose filename
scene_path = bpy.data.scenes.data.filepath
scene_dir, scene_file = os.path.split(scene_path)

    

#
# Module loading
if scene_dir not in sys.path:
    print("Appending '" + scene_dir + "' to system path")
    sys.path.append(scene_dir)
    sys.path.append(scene_dir+"/3rdParty")

#import websocket

import MakeHumanTools
MakeHumanTools.register()


import LeapNUI
LeapNUI.register()


import BlenderLogger
BlenderLogger.register()

import HeadCameraControl
HeadCameraControl.register()


for f in FILES:
    script_path = scene_dir + "/" + f
    print ("Executing '" + f + "'")
    bpy.ops.script.python_file_run(filepath=script_path)    

# Switch to Demo View
bpy.context.window.screen = bpy.data.screens['Capture View']
