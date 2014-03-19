SLSI NUI Interaction Scripts
============================

The Blender add-ons and scripts used at the Sign Language Synthesis and Interaction group and DFKI/MMCI (http://slsi.dfki.de)


CONTENT
=======

BlenderLogger/					A logging system recording Blender events into an internal buffer. Can also be installed alone.Downloads/						External packages.FaceShift2Blender/				Direct real-time control of MakeHuman faces through FaceShift software.gpl-3.0-header_template.txt		GPLv3 text for source code.gpl-3.0.txt						GPLv3 full text.images/							Collection of shared icons.INIT.py							Initialization script to paste into your Blender Scene.LeapForwarder/					Support utility for forward Leap Motion frames into UDP packets.LeapNUI/						Add-ons to Manipulate objects using Leap Motion.MakeHumanTools/					Add-ons to manipulate MakeHuman Characters.README.txt						This file.Scripts/						Other misc scripts.SimplifyMultipleFCurves/		Parallel simplification of multiple animation curves. Can also be installed alone.TrimFCurves/					Add-on to trim selected animation curves. Can also be installed alone.



INSTALLATION
============

Constraint: the Blender scene must be placed in the same directory of this README.txt file

1)
Save the scene into tha same directory containig also this README file).
Copy and paste the INIT.py script into a new text buffer of your Blender scene.
Run it to initialize the whole system.

Some of the add-ons can be also installed using the standard Blender add-ons installation mechanism.
Use the menu -> File -> User Preferences -> Addons (tab) -> Install from File...


2) (optional)
- Downloads/websocket.py
It is needed when the Leap Motion receiver is used to directly connect to the websocket, instead of using the LeapForwarder.
This is a flag in the source code of FaceShiftControl.py and LeapReceiver.py.

If needed, must be copied manually into the Blender-embedded python installation:
Select the Blender app and right click "Show Package Contents" 
-> Contents/MacOS/2.xx/python/lib/python3.3/




fnunnari
