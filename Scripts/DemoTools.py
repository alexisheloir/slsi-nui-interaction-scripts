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


# Management panel and functions for a comprehensive fast recording demo.

# v01 - Integrated all scripts
# v02 - developed Demo control panel, Trimming operator, fixed FaceShift recording issue.
# v03 - Fixed simplification maxkf selection. Forced object to Pose Mode for proper FCurves selection.
# v04 - Fixed object selection/hiding sequence
# v05 - Fixed elbow recording
# v06 - Added FreePlay mode. Working on left/right selection buttons
# v07 - Adjusted horizontal offset for Leap hand direct control. Mirrored FaceShift controls.
# v08 - Re-exported and tested with Blender 2.69
# v08b - reworked objects selection for LeapModalCOntroller. Now using the active instead of the selected.

import bpy

import re

import mathutils


#ARMATURE_NAME = "Human1-mhxrig-expr-advspine"


def getFirstArmature(context):
    """Returns the selected armature. Or None"""
    
    for obj in bpy.data.objects:
        if(obj.type == "ARMATURE"):
            return obj
    
    return None



class DemoCaptureView(bpy.types.Operator):
    """Show demo capture view"""
    
    bl_idname = "scene.signrecdemo_demoviewcapture"
    bl_label = "Capture View"
    
    
    def execute(self, context):
        # auto key: off
        context.scene.tool_settings.use_keyframe_insert_auto = False
        
        bpy.context.window.screen = bpy.data.screens['Capture View']
        return {'FINISHED'}


#
#
#

class DemoEditView(bpy.types.Operator):
    """Show demo capture view"""
    
    bl_idname = "scene.signrecdemo_demoviewedit"
    bl_label = "Edit View"
    
    
    def execute(self, context):
        
        # cursor at sign beginning
        context.scene.frame_current = context.scene.frame_preview_start
        
        # auto key: on
        context.scene.tool_settings.use_keyframe_insert_auto = True
        
        bpy.context.window.screen = bpy.data.screens['Edit View']
        return {'FINISHED'}


#
#
#

class FreePlay(bpy.types.Operator):
    """Activate peripherals to control the character. But no recording is activated"""
    
    bl_idname = "scene.signrecdemo_freeplay"
    bl_label = "Activate character control"
    
    
    def execute(self, context):
        
        # auto key: on
        context.scene.tool_settings.use_keyframe_insert_auto = False
        
        #
        # Run operators
        bpy.ops.object.leap_modal(isHandsDirectlyControlled=True, handsMirrorMode=True, isFingersDirectlyControlled=True, isElbowsDirectlyControlled=True)
        # do not instantiate another timer if another modal command already did.
        # TODO - bpy.ops.object.faceshift_modal(instantiateTimer=False)
        
        bpy.ops.scene.signrecdemo_demoviewcapture()
        
        return {'FINISHED'}

#
#
#



class Reset(bpy.types.Operator):
    """Reset the scene to record a new sign."""
    
    bl_idname = "scene.signrecdemo_reset"
    bl_label = "Demo Reset"
    
    
    def execute(self, context):
        
        # select armature
        for obj in bpy.data.objects:
            obj.select = False
        #arm = bpy.data.objects[ARMATURE_NAME]
        arm = getFirstArmature(context)
        arm.hide = False
        arm.select = True
        bpy.context.scene.objects.active = arm
        #bpy.context.scene.objects.active = bpy.data.objects['Human1-mhxrig-expr']
        
        print("ACTIVE=" + str(bpy.context.scene.objects.active))
        print("ACTIVE TYPE=" + str(bpy.context.scene.objects.active.type))
        print("SELECTED=" + str(bpy.context.selected_objects))
        
        # Force Pose Mode
        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        
        # force alt-time
        context.scene.use_preview_range=True
        
        # clear time range
        context.scene.frame_preview_start = 0
        context.scene.frame_preview_end = 750
        
        # cursor at 0
        context.scene.frame_current = 0
        
        
        # delete all curves
        #bpy.data.objects[ARMATURE_NAME].animation_data_clear()
        arm.animation_data_clear()
        
        # Reset expression and pose
        bpy.ops.object.mh_reset_arms()
        bpy.ops.object.mh_reset_facial_rig()
        bpy.ops.object.mh_reset_body()
        bpy.ops.object.mh_reset_hands(left_hand=True, right_hand=True)
        
        #arm.hide = True
        
        bpy.ops.scene.signrecdemo_demoviewcapture()
        
        return {'FINISHED'}

#
#
#

class StartRecording(bpy.types.Operator):
    """Reset the scene to record a new sign."""
    
    bl_idname = "scene.signrecdemo_startrec"
    bl_label = "Start Recording a new sign"
    
    
    def execute(self, context):
        
        # auto key: on
        context.scene.tool_settings.use_keyframe_insert_auto = True
        
        #
        # Run operators
        bpy.ops.object.leap_modal(isHandsDirectlyControlled=True, handsMirrorMode=True, isFingersDirectlyControlled=True, isElbowsDirectlyControlled=True)
        # do not instantiate another timer if another modal command already did.
        # TODO - bpy.ops.object.faceshift_modal(instantiateTimer=False)
        # run the ESC catcher to stop the animation play
        bpy.ops.scene.signrecdemo_playpauser()
        
        #
        # start play
        bpy.ops.screen.animation_play(reverse=False, sync=True)
        
        return {'FINISHED'}


#
#
#

class StopRecording(bpy.types.Operator):
    """Reset the scene to record a new sign."""
    
    bl_idname = "scene.signrecdemo_stoprec"
    bl_label = "Stop Recording"
    
    
    def execute(self, context):
        
        bpy.ops.screen.animation_cancel()
        
        return {'FINISHED'}

#
#
#

class PlayPauser(bpy.types.Operator):
    """Small support modal operator to stop the timeline play when a key is pressed."""
    
    bl_idname = "scene.signrecdemo_playpauser"
    bl_label = "Pause the animation play"
    
    
    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        #print("Really RUNNING?")
        if event.type == 'ESC':
            print("ESC PRESSED! Cancel play!!!")
            bpy.ops.screen.animation_cancel()
            #return {'FINISHED'}
            return {'CANCELLED'}
        else:
            return {'PASS_THROUGH'}

#
#
#

class Trim(bpy.types.Operator):
    """Trim the animation curves of the character by deleting the keyframes out of the specified time range."""
    
    bl_idname = "scene.signrecdemo_trim"
    bl_label = "Trim animation"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    def execute(self, context):
        
        # Select all the curves to trim
        bpy.ops.object.mh_select_all_fcurves()
        
        # Trim it!
        bpy.ops.graph.trim_fcurves()
        
        return {'FINISHED'}

#
#
#

class Simplify(bpy.types.Operator):
    """Simplify the animation curves of the character."""
    
    bl_idname = "scene.signrecdemo_simplify"
    bl_label = "Simplify animation"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    def execute(self, context):
        
        # Select all the curves to trim
        bpy.ops.object.mh_select_all_fcurves()
        
        # Calculate how many frames there are, and simplify to 1/10th
        
        n_frames = context.scene.frame_preview_end - context.scene.frame_preview_start + 1
        #reduces_frames = int(n_frames / 5)
        reduces_frames = context.scene.signrecdemo_simplification_max_keyframes
        print("Selected " + str(n_frames) + " keyframes. Reducing to " + str(reduces_frames))
        
        #bpy.ops.screen.animation_cancel()
        bpy.ops.graph.simplify_multiple_curves_kf(maxkf=reduces_frames)
        
        return {'FINISHED'}


#
#
#

class PlayStopRecordedSign(bpy.types.Operator):
    """Play/Stop sign playback."""
    
    bl_idname = "scene.signrecdemo_play_stop"
    bl_label = "Playback (or pause) a recorded sign"
    
    
    def execute(self, context):
        
        # auto key: on
        context.scene.tool_settings.use_keyframe_insert_auto = True
        
        # cursor at sign beginning
        context.scene.frame_current = context.scene.frame_preview_start
        
        #
        # start play
        bpy.ops.screen.animation_play(reverse=False, sync=True)
        
        return {'FINISHED'}


#
#
#

class SelectRightHand(bpy.types.Operator):
    """Small support modal operator to select the interpreter right hand."""
    
    bl_idname = "scene.signrecdemo_selectrighthand"
    bl_label = "Select the right hand"
    
    
    def execute(self, context):
        
        arm = getFirstArmature(context)
        bone = arm.pose.bones["Wrist_R"]
        #context.active_pose_bone = bone
        # @see http://aligorith.blogspot.de/2011/02/scripting-25-faq-setting-active-bone.html
        arm.bones.active = bone.bone
        
        return {'FINISHED'}

#
#
#

class SelectLeftHand(bpy.types.Operator):
    """Small support modal operator to select the interpreter left hand."""
    
    bl_idname = "scene.signrecdemo_selectlefthand"
    bl_label = "Select the left hand"
    
    
    def execute(self, context):
        
        arm = getFirstArmature(context)
        bone = arm.pose.bones["Wrist_L"]
        #context.active_pose_bone = bone
        # @see http://aligorith.blogspot.de/2011/02/scripting-25-faq-setting-active-bone.html
        arm.bones.active = bone.bone
        
        return {'FINISHED'}

#
#
#


def get_last_keyed_frame(object, last_frame):
    """Scan the animation curves of this object.
        returns the frame number of the most recent key, up to last_frame.
        Returns -1 of no frames are found before (or including) the last_frame."""
    
    out = -1
    
    for fcurve in object.animation_data.action.fcurves: # It is valid because has been already
        print("Scanning " + str(fcurve.data_path) + "/ " + str(fcurve.array_index))
        keyframes = fcurve.keyframe_points
        i = 0
        for kf in keyframes:
            frame = kf.co[0]
            if(frame > last_frame):
                continue
            assert (frame <=last_frame)
            if(frame > out):
                print("FOUND most recent frame " + str(frame))
                out = frame
    
    return out




class StoreHold(bpy.types.Operator):
    """Store into buffer the configuration of all controllers (used in the demo)."""
    
    bl_idname = "scene.signrecdemo_store_hold"
    bl_label = "Store HOLD"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    def execute(self, context):
        
        target_frame = bpy.context.scene.frame_current
        
        # Select all bones keyable
        bpy.ops.object.mh_select_all_pose_bones()
        
        # Copy pose into buffer
        bpy.ops.pose.copy()
        
        return {'FINISHED'}



class InsertHold(bpy.types.Operator):
    """Duplicate the last keyframed position at current frame selection."""
    
    bl_idname = "scene.signrecdemo_insert_hold"
    bl_label = "Insert HOLD"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    def execute(self, context):
        
        #target_frame = bpy.context.scene.frame_current
        
        # Check the last keyframe (scan anim curves of selected object to find most recent past keyframe
        #arm = getFirstArmature(context)
        #last_keyed_frame = get_last_keyed_frame(object = arm, last_frame = target_frame)
        
        # Select all bones keyable
        bpy.ops.object.mh_select_all_pose_bones()
        
        # Move time cursor back at last valid keyframe
        #bpy.context.scene.frame_current = last_keyed_frame
        
        # Copy pose into buffer
        #bpy.ops.pose.copy()
        
        # Move cursor back at invocation time
        #bpy.context.scene.frame_current = target_frame
        
        # Paste pose
        bpy.ops.pose.paste()
        
        # Insert Keyframe for Makehuman
        bpy.ops.object.mh_insert_keyframe()
        
        return {'FINISHED'}

#
#
#


class SignRecordingDemoPanel(bpy.types.Panel):
    bl_label = "Sign Recording Demo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
    
    
    def draw(self, context):
        self.layout.operator("scene.signrecdemo_reset", text="Reset")
        self.layout.separator()
        r = self.layout.row()
        r.label(text="CAPTURE")
        r.operator("scene.signrecdemo_demoviewcapture", text=" ", icon='RIGHTARROW')
        self.layout.operator("scene.signrecdemo_freeplay", text="Free Play")
        self.layout.operator("scene.signrecdemo_startrec", text="START Rec")
        #self.layout.operator("scene.signrecdemo_stoprec", text="STOP rec")
        
        self.layout.separator()
        self.layout.operator("scene.signrecdemo_trim", text="Trim")
        self.layout.prop(data=context.scene, property="signrecdemo_simplification_max_keyframes")
        self.layout.operator("scene.signrecdemo_simplify", text="Simplify")
        #self.layout.operator("object.mh_reset_facial_rig", text='Reset Facial Expression')
        
        self.layout.separator()
        
        self.layout.operator("scene.signrecdemo_play_stop", text="PLAY / STOP")
        
        self.layout.separator()
        
        r = self.layout.row()
        r.label(text="EDIT")
        r.operator("scene.signrecdemo_demoviewedit", text=" ", icon='RIGHTARROW')
        
        self.layout.operator("object.mh_delete_keyframe", text="DELETE Keyframe")
        self.layout.operator("scene.signrecdemo_store_hold", text="Store HOLD")
        self.layout.operator("scene.signrecdemo_insert_hold", text="Insert HOLD")
        
        #        self.layout.separator()
        #        self.layout.label(text="EDIT")
        #        r = self.layout.row()
        #        r.label(text="Arm:")
        #        r.operator("scene.signrecdemo_selectrighthand", text="Right")
        #        r.operator("scene.signrecdemo_selectlefthand", text="Left")
        pass




def register():
    print("Registering SignRecordingDemo operators...", end="")
    
    bpy.types.Scene.signrecdemo_simplification_max_keyframes = bpy.props.IntProperty(name="Max Keyframes", default = 5, min=3, description="The maximum number of kexframes after simplification")
    
    bpy.utils.register_class(DemoCaptureView)
    bpy.utils.register_class(DemoEditView)
    bpy.utils.register_class(FreePlay)
    bpy.utils.register_class(Reset)
    bpy.utils.register_class(StartRecording)
    bpy.utils.register_class(StopRecording)
    bpy.utils.register_class(PlayPauser)
    bpy.utils.register_class(Trim)
    bpy.utils.register_class(Simplify)
    bpy.utils.register_class(PlayStopRecordedSign)
    bpy.utils.register_class(StoreHold)
    bpy.utils.register_class(InsertHold)
    #bpy.utils.register_class(EditPose)
    #bpy.utils.register_class(Store)
    bpy.utils.register_class(SignRecordingDemoPanel)
    bpy.utils.register_class(SelectRightHand)
    bpy.utils.register_class(SelectLeftHand)
    print("ok")

def unregister():
    print("Unregistering SignRecordingDemo operators...", end="")
    bpy.utils.unregister_class(DemoCaptureView)
    bpy.utils.unregister_class(DemoEditView)
    bpy.utils.unregister_class(FreePlay)
    bpy.utils.unregister_class(Reset)
    bpy.utils.unregister_class(StartRecording)
    bpy.utils.unregister_class(StopRecording)
    bpy.utils.unregister_class(PlayPauser)
    bpy.utils.unregister_class(Trim)
    bpy.utils.unregister_class(Simplify)
    bpy.utils.unregister_class(PlayStopRecordedSign)
    bpy.utils.unregister_class(StoreHold)
    bpy.utils.unregister_class(InsertHold)
    #bpy.utils.unregister_class(EditPose)
    #bpy.utils.unregister_class(Store)
    bpy.utils.unregister_class(SignRecordingDemoPanel)
    bpy.utils.unregister_class(SelectRightHand)
    bpy.utils.unregister_class(SelectLeftHand)
    
    print("ok")




if __name__ == "__main__":
    register()
