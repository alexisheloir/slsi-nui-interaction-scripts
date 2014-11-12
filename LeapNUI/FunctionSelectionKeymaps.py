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

from .LeapModalController import LeapModal



TRANSLATION_SHORTCUT_CHAR = 'G'
ROTATION_SHORTCUT_CHAR = 'R'
TR_AND_ROT_SHORTCUT_CHAR = 'T'
FINGER_ROTATION_SHORTCUT_CHAR = 'F'
HANDS_DIRECT_CONTROL_CHAR = 'H'


# I've got here the 'name' parameter possible values for the KeyMap
# https://svn.blender.org/svnroot/bf-extensions/contrib/py/scripts/addons/presets/keyconfig/blender_2012_experimental.py
EDIT_MODES = ['Object Mode', 'Pose']


# store keymap items here to delete them on unregistration
function_selection_keymap_items = []


def register():
    print("Registering keymaps for function selection...", end="")
    
    
    # handle the keymap
    wm = bpy.context.window_manager
    
    for edit_mode in EDIT_MODES:
        km = wm.keyconfigs.addon.keymaps.new(name=edit_mode, space_type='EMPTY')
        
        # G - Translation
        kmi = km.keymap_items.new(LeapModal.bl_idname, TRANSLATION_SHORTCUT_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isTranslating = True
        kmi.properties.translationUseFinger = True
        function_selection_keymap_items.append(kmi)
        
        # R - Rotation
        kmi = km.keymap_items.new(LeapModal.bl_idname, ROTATION_SHORTCUT_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isRotating = True
        #kmi.properties.rotationUseFinger = True
        function_selection_keymap_items.append(kmi)
        
        # T - Translation and Rotation
        kmi = km.keymap_items.new(LeapModal.bl_idname, TR_AND_ROT_SHORTCUT_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isTranslating = True
        kmi.properties.isRotating = True
        function_selection_keymap_items.append(kmi)
        
        # F - Elbow swivel rotation
        kmi = km.keymap_items.new(LeapModal.bl_idname, FINGER_ROTATION_SHORTCUT_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isElbowSwivelRotating = True
        function_selection_keymap_items.append(kmi)
        
        # H - Hands direct control (first person)
        kmi = km.keymap_items.new(LeapModal.bl_idname, HANDS_DIRECT_CONTROL_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isHandsDirectlyControlled = True
        function_selection_keymap_items.append(kmi)
        
        # H - Hands direct control (mirror mode)
        kmi = km.keymap_items.new(LeapModal.bl_idname, HANDS_DIRECT_CONTROL_CHAR, 'PRESS', ctrl=False, shift=True)
        kmi.properties.isHandsDirectlyControlled = True
        kmi.properties.handsMirrorMode = True
        function_selection_keymap_items.append(kmi)
        
    print("ok")


def unregister():
    print("Unregistering keymaps for function selection...", end="")
    
    # handle the keymap
    wm = bpy.context.window_manager
    for edit_mode in EDIT_MODES:
        km = wm.keyconfigs.addon.keymaps[edit_mode]
        for kmi in function_selection_keymap_items:
            if(kmi in km.keymap_items.values()):
                print("\t\tRemove from Addon/Pose Item '" + kmi.name +"'\t'" + kmi.idname + "'")
                km.keymap_items.remove(kmi)
    
    function_selection_keymap_items.clear()

    print("ok")


