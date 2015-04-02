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

bl_info = {
    "name": "Leap Modal Control",
    "description": "Enables input from Leap Motion.",
    "author": "Fabrizio Nunnari",
    "version": (1, 0),
    "blender": (2, 69, 0),
    "location": "View3D > Toolbar",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "System"}


#from .LeapReceiver import LeapReceiver

from .LeapModalController import LeapModal

from . import FunctionSelectionKeymaps
from . import BodySelectionKeymaps
from . import HandShapeSelector
from . import KeyboardlessActivation
from . import Icons

import bpy


class LeapNUIControlPanel(bpy.types.Panel):
    bl_label = "Leap NUI Control Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
    
    
    def draw(self, context):
        self.layout.prop(data=bpy.context.window_manager, property="leap_nui_longitudinal_mode")
        self.layout.prop(data=bpy.context.window_manager, property="leap_nui_body_selection_active", toggle=True)
        self.layout.prop(data=bpy.context.window_manager, property="leap_nui_function_selection_active", toggle=True)
        if(bpy.context.window_manager.leap_nui_keyboardless_active):
            target = "OFF"
        else:
            target = "ON"
        self.layout.operator(operator="wm.leap_nui_keyboardless_control_switch", text="Turn "+target+" Keyboardless Control")
        self.layout.prop(data=bpy.context.window_manager, property="leap_keyboardless_grab_mode")
        self.layout.prop(data=bpy.context.window_manager, property="leap_keyboardless_grasp_operation")
        self.layout.prop(data=bpy.context.window_manager, property="leap_hand_shape_selector_finger_extension_filter")


def toggleBodySelectionKeymaps(self, context):
    if(bpy.context.window_manager.leap_nui_body_selection_active==True):
        BodySelectionKeymaps.register()
    else:
        BodySelectionKeymaps.unregister()
    return None

def toggleFunctionSelectionKeymaps(self, context):
    if(bpy.context.window_manager.leap_nui_function_selection_active==True):
        FunctionSelectionKeymaps.register()
    else:
        FunctionSelectionKeymaps.unregister()
    return None



def register():
    print("Registering LeapNUI classes...", end="")

    # Init properties to enable/disable different keymaps
    bpy.types.WindowManager.leap_nui_body_selection_active = bpy.props.BoolProperty(name="Body Selection", description="Switch the use of the direct body selection system", default=False, options={'SKIP_SAVE'}, update=toggleBodySelectionKeymaps)

    bpy.types.WindowManager.leap_nui_function_selection_active = bpy.props.BoolProperty(name="Function Selection", description="Switch the use of the shotcuts to manipulate objects using the LeapMotion", default=False, options={'SKIP_SAVE'}, update=toggleFunctionSelectionKeymaps)

    bpy.types.WindowManager.leap_nui_longitudinal_mode = bpy.props.BoolProperty(name="Longitudinal Leap", description="Check if you use the Leap is longitudinal mode, rotated 90 degrees, with the cable going away from the user", default=False, options={'SKIP_SAVE'})

    bpy.types.WindowManager.leap_nui_keyboardless_active = bpy.props.BoolProperty(name="Keyboardless Activation", description="Switch the use of the keyboardless mode to activate the LeapMotion", default=False, options={'SKIP_SAVE'})


    bpy.utils.register_class(LeapModal)

    #FunctionSelectionKeymaps.register()
    #BodySelectionKeymaps.register()
    KeyboardlessActivation.register()

    HandShapeSelector.register()

    bpy.utils.register_class(LeapNUIControlPanel)

    print("ok")


def unregister():
    print("Unregistering LeapNUI...", end="")

    bpy.utils.unregister_class(LeapNUIControlPanel)

    HandShapeSelector.unregister()

    KeyboardlessActivation.unregister()
    #FunctionSelectionKeymaps.unregister()
    #BodySelectionKeymaps.unregister()

    bpy.utils.unregister_class(LeapModal)
    
    del bpy.context.window_manager.leap_nui_keyboardless_active
    del bpy.context.window_manager.leap_nui_longitudinal_mode
    del bpy.context.window_manager.leap_nui_function_selection_active
    del bpy.context.window_manager.leap_nui_body_selection_active

    print("ok")


if __name__ == "__main__":
    register()
