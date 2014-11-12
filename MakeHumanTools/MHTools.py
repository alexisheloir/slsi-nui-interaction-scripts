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
from bpy.props import * # for properties

import re

import mathutils

from .BoneSet import *


def getSelectedArmature(context):
    """Returns the selected armature, or None."""
    
    arm = None
    
    objs = context.selected_objects
    if(len(objs) != 1):
        return None
    
    arm = objs[0]
    if(arm.type != "ARMATURE"):
        return None
    
    return arm


def mh_poll(cls, context):
    """Unified poll for all MakeHuman related commands. Check that the selected armature is a valid MakeHuman structure."""
    
    arm = getSelectedArmature(context)
    
    if(arm == None):
        return False
    
    for c in MH_ALL_CONTROLLERS:
        if(not c in arm.pose.bones):
            return False

    return True

#
#
#

class MakeHumanResetArms(bpy.types.Operator):
    """Resets hand and elbows to default position."""
    
    bl_idname = "object.mh_reset_arms"
    bl_label = "MH Reset Arms"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return mh_poll(cls, context)
    
    #
    # EXECUTE
    #
    # Return enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’}
    def execute(self, context):
        
        arm = getSelectedArmature(context)
        if(arm == None):
            self.report({'ERROR'}, " Not armature selected")
            return {'CANCELLED'}
        
        for c in MH_ARM_CONTROLLERS:
            pb = arm.pose.bones[c]
            #print("Resetting " + str(pb))
            
            pb.location = 0,0,0
            pb.rotation_euler = 0,0,0
            pb.rotation_quaternion = 1,0,0,0
        
        # Rework on the Elbows. We don't really like the 0,0,0 position.
        #arm.pose.bones["ElbowPT_R"].location = 0.7,-2.5,4
        #arm.pose.bones["ElbowPT_L"].location = -0.7,-2.5,4
        
        
        
        return {'FINISHED'}


#
#
#


class MakeHumanResetFacialRig(bpy.types.Operator):
    """This is the Blender operator to reset the MakeHumn facial rig to default position."""
    
    bl_idname = "object.mh_reset_facial_rig"
    bl_label = "Reset MakeHuman Facial Rig"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        return mh_poll(cls, context)
    
    def execute(self, context):
        
        # Retrieve the currently selected armature
        armature = getSelectedArmature(context)
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}
        
        bones = bpy.data.objects[armature.name].pose.bones
        
        # Reset all controllers position
        for ctrl in MH_FACIAL_CONTROLLERS:
            bones[ctrl].location.xyz = 0,0,0
        
        # Reset Jaw rotation
        bones[MH_CONTROLLER_JAW].rotation_mode = 'XYZ'
        bones[MH_CONTROLLER_JAW].rotation_euler.z = 0.0
        
        # Reset head rotation
        bones[MH_CONTROLLER_NECK].rotation_mode = 'QUATERNION'
        bones[MH_CONTROLLER_NECK].rotation_quaternion = mathutils.Quaternion((1,0,0,0))
        
        # Reset Eyes rotation
        bones[MH_CONTROLLER_GAZE].location = 0,0,0
        
        # Reset mouth retraction Expression Unit
        bpy.data.objects[armature.name][MH_EU_MOUTH_RETRACTION] = 0.0
        
        
        return {'FINISHED'}

#
#
#


class MakeHumanResetBody(bpy.types.Operator):
    """This is the Blender operator to reset the MakeHumn body to default position."""
    
    bl_idname = "object.mh_reset_body"
    bl_label = "Reset MakeHuman Body"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        return mh_poll(cls, context)
    
    def execute(self, context):
        
        # Retrieve the currently selected armature
        armature = getSelectedArmature(context)
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}
        
        bones = bpy.data.objects[armature.name].pose.bones
        
        # Reset all controllers position
        for ctrl in MH_BODY_CONTROLLERS + MH_HEAD_CONTROLLERS:
            bones[ctrl].location.xyz = 0,0,0
            bones[ctrl].rotation_quaternion = mathutils.Quaternion((1,0,0,0))
        
        return {'FINISHED'}

#
#
#



class MakeHumanResetHands(bpy.types.Operator):
    """This is the Blender operator to reset the MakeHumn body to default position."""
    
    bl_idname = "object.mh_reset_hands"
    bl_label = "Reset MakeHuman Hand"
    bl_options = {'REGISTER', 'UNDO'}
    
    right_hand = BoolProperty(name="right_hand", description="Whether to reset the right hand", default=True)
    left_hand = BoolProperty(name="left_hand", description="Whether to reset the left hand", default=True)
    
    @classmethod
    def poll(cls, context):
        return mh_poll(cls, context)
    
    def execute(self, context):
        # Retrieve the currently selected armature
        armature = getSelectedArmature(context)
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}
        
        # e.g.:
        # bpy.data.objects['Human1-mhxrig-expr-advspine'].pose.bones['Finger-2-1_L'].rotation_quaternion = 1,0,0,0
        bones = bpy.data.objects[armature.name].pose.bones
        if(self.right_hand):
            for name in MH_HAND_BONES_R + MH_HAND_CONTROLLERS_R:
                b = bones[name]
                b.rotation_quaternion = 1,0,0,0
        
        if(self.left_hand):
            for name in MH_HAND_BONES_L + MH_HAND_CONTROLLERS_L:
                b = bones[name]
                b.rotation_quaternion = 1,0,0,0
        
        return {'FINISHED'}


#
#
#

class MakeHumanSelectHandBones(bpy.types.Operator):
    """This is the Blender operator to select the MakeHumn hand bones (useful to store keys)."""
    
    bl_idname = "object.mh_select_hand_bones"
    bl_label = "Select MakeHuman Hand Bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    right_hand = BoolProperty(name="right_hand", description="Whether to select the right hand", default=True)
    left_hand = BoolProperty(name="left_hand", description="Whether to select the left hand", default=True)
    
    @classmethod
    def poll(cls, context):
        return mh_poll(cls, context)
    
    def execute(self, context):
        # Retrieve the currently selected armature
        armature = getSelectedArmature(context)
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}
        
        # e.g.:
        # bpy.data.armatures['Human1-mhxrig-expr-advspine'].bones['Finger-2-1_L'].select = True
        bones = bpy.data.armatures[armature.name].bones
        if(self.right_hand):
            for name in MH_HAND_BONES_R:
                bones[name].select = True
        
        if(self.left_hand):
            for name in MH_HAND_BONES_L:
                bones[name].select = True
        
        return {'FINISHED'}


#
#
#



class MakeHumanSelectAllFCurves(bpy.types.Operator):
    """Select all the animation fcurves"""
    
    bl_idname = "object.mh_select_all_fcurves"
    bl_label = "Select all MakeHuman FCurves (used in the demo)"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        return mh_poll(cls, context)
    
    def execute(self, context):
        
        arm = getSelectedArmature(context)
        
        fcurves = arm.animation_data.action.fcurves
        
        pattern = re.compile('pose\.bones\[\"(.+)\"\]\..+') #  "pose\.bones\[\"(+*)\"\]\..+")
        
        for c in fcurves:
            print(c.data_path)
            
            if(c.data_path == '["'+MH_EU_MOUTH_RETRACTION+'"]'):
                c.select=True
                continue
            
            res = pattern.match(c.data_path)
            #print(res)
            #print(res.group(0))
            if(res == None):
                c.select=False
                continue
            
            bone_name = res.group(1)
            if(bone_name in MH_ALL_CONTROLLERS ):
                c.select = True
            else:
                c.select = False
        
        return {'FINISHED'}


#
#
#

class MakeHumanSelectAllPoseBones(bpy.types.Operator):
    """Select all the pose bones used by these MakeHuman tools."""
    
    bl_idname = "object.mh_select_all_pose_bones"
    bl_label = "Select all MakeHuman Pose Bones (used in the demo)"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        return mh_poll(cls, context)
    
    def execute(self, context):
        
        arm = getSelectedArmature(context)

        # selection example:
        #arm.pose.bones['Wrist_R'].bone.select = False

        # First, remove existing selections
        for bone in arm.pose.bones:
            bone.bone.select = False


        # Now select all by name
        for name in (MH_ALL_CONTROLLERS + MH_HAND_BONES):
            bone = arm.pose.bones[name]
            bone.bone.select = True

        return {'FINISHED'}


#
#
#

class MakeHumanInsertKeyframe(bpy.types.Operator):
    """Insert keyframe of the whole makehuman body from the current frame position"""
    
    bl_idname = "object.mh_insert_keyframe"
    bl_label = "Insert the keyframe of all rig controllers at current keyframe"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        return mh_poll(cls, context)
    
    def execute(self, context):
        
        # Retrieve the currently selected armature
        armature = getSelectedArmature(context)
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}
        
        bones = bpy.data.objects[armature.name].pose.bones
        
        frame = context.scene.frame_current
        
        
        #
        # reset ARMS
        for c in MH_ARM_CONTROLLERS:
            bones[c].keyframe_insert(data_path="location", frame=frame)
            bones[c].keyframe_insert(data_path="rotation_quaternion", frame=frame)
        
        
        #
        # reset FACE
        for ctrl in MH_FACIAL_CONTROLLERS:
            bones[ctrl].keyframe_insert(data_path='location', frame=frame)
        
        # Reset Jaw rotation
        bones[MH_CONTROLLER_JAW].keyframe_insert(data_path='rotation_euler', frame=frame)
        
        # Reset head rotation
        bones[MH_CONTROLLER_NECK].keyframe_insert(data_path='rotation_quaternion', frame=frame)
        
        # Reset Eyes rotation
        bones[MH_CONTROLLER_GAZE].keyframe_insert(data_path='location', frame=frame)
        
        # Reset mouth retraction Expression Unit
        bpy.data.objects[armature.name].keyframe_insert(data_path='["'+MH_EU_MOUTH_RETRACTION+'"]', frame=frame)
        
        
        #
        # reset BODY
        for ctrl in MH_BODY_CONTROLLERS:
            bones[ctrl].keyframe_insert(data_path='rotation_quaternion', frame=frame)
        
        #
        # reset HANDS
        for name in (MH_HAND_BONES):
            bones[name].keyframe_insert(data_path="rotation_quaternion", frame=frame)
        
        
        return {'FINISHED'}


#
#
#

class MakeHumanDeleteKeyframe(bpy.types.Operator):
    """Delete keyframe of the whole makehuman body from the current frame position"""
    #(armature_name, frame):
    #print("Deleting keyframes for armature "+armature_name)
    
    bl_idname = "object.mh_delete_keyframe"
    bl_label = "Delete the keyframe of all rig controllers at current keyframe"
    bl_options = {'REGISTER', 'UNDO'}

    
    @classmethod
    def poll(cls, context):
        return mh_poll(cls, context)
    
    def execute(self, context):
        
        # Retrieve the currently selected armature
        armature = getSelectedArmature(context)
        
        if(armature == None):
            self.report({'ERROR'}, "No armature found!")
            return {'CANCELLED'}
        
        bones = bpy.data.objects[armature.name].pose.bones
        
        frame = context.scene.frame_current
        
        
        #
        # reset ARMS
        for c in MH_ARM_CONTROLLERS:
            bones[c].keyframe_delete(data_path="location", frame=frame)
            bones[c].keyframe_delete(data_path="rotation_quaternion", frame=frame)


        #
        # reset FACE
        for ctrl in MH_FACIAL_CONTROLLERS:
            bones[ctrl].keyframe_delete(data_path='location', frame=frame)
        
        # Reset Jaw rotation
        bones[MH_CONTROLLER_JAW].keyframe_delete(data_path='rotation_euler', frame=frame)

        # Reset head rotation
        bones[MH_CONTROLLER_NECK].keyframe_delete(data_path='rotation_quaternion', frame=frame)
        
        # Reset Eyes rotation
        bones[MH_CONTROLLER_GAZE].keyframe_delete(data_path='location', frame=frame)
        
        # Reset mouth retraction Expression Unit
        bpy.data.objects[armature.name].keyframe_delete(data_path='["'+MH_EU_MOUTH_RETRACTION+'"]', frame=frame)


        #
        # reset BODY
        for ctrl in MH_BODY_CONTROLLERS:
            bones[ctrl].keyframe_delete(data_path='rotation_quaternion', frame=frame)

        #
        # reset HANDS
        for name in (MH_HAND_BONES):
            bones[name].keyframe_delete(data_path="rotation_quaternion", frame=frame)


        return {'FINISHED'}


#
#
#


class MHToolsPanel(bpy.types.Panel):
    bl_label = "Make Human Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
    
    
    def draw(self, context):
        self.layout.operator("object.mh_reset_arms", text="Reset Arms")
        self.layout.operator("object.mh_reset_facial_rig", text="Reset Facial Expression")
        self.layout.operator("object.mh_reset_body", text="Reset Body")
        
        r = self.layout.row()
        # see http://wiki.blender.org/index.php/Dev:2.5/Py/Scripts/Cookbook/Code_snippets/Interface
        p = r.operator("object.mh_reset_hands", text="Reset Left Hand")
        p.right_hand = False
        p.left_hand = True
        p = r.operator("object.mh_reset_hands", text="Reset Right Hand")
        p.right_hand = True
        p.left_hand = False
        
        self.layout.operator("object.mh_select_all_fcurves", text="Select All FCurves")

        self.layout.operator("object.mh_select_all_pose_bones", text="Select All Pose Bones")

        r = self.layout.row()
        p = r.operator("object.mh_select_hand_bones", text="Select Left Hand")
        p.right_hand = False
        p.left_hand = True
        p = r.operator("object.mh_select_hand_bones", text="Select Right Hand")
        p.right_hand = True
        p.left_hand = False



def register():
    print("Registering Leap operators...", end="")
    bpy.utils.register_class(MakeHumanResetArms)
    bpy.utils.register_class(MakeHumanResetFacialRig)
    bpy.utils.register_class(MakeHumanResetBody)
    bpy.utils.register_class(MakeHumanResetHands)
    bpy.utils.register_class(MakeHumanSelectHandBones)
    bpy.utils.register_class(MakeHumanSelectAllFCurves)
    bpy.utils.register_class(MakeHumanSelectAllPoseBones)
    bpy.utils.register_class(MakeHumanInsertKeyframe)
    bpy.utils.register_class(MakeHumanDeleteKeyframe)
    bpy.utils.register_class(MHToolsPanel)
    print("ok")

def unregister():
    print("Unregistering Leap operators...", end="")
    bpy.utils.unregister_class(MakeHumanResetArms)
    bpy.utils.unregister_class(MakeHumanResetFacialRig)
    bpy.utils.unregister_class(MakeHumanResetBody)
    bpy.utils.unregister_class(MakeHumanResetHands)
    bpy.utils.unregister_class(MakeHumanSelectHandBones)
    bpy.utils.unregister_class(MakeHumanSelectAllFCurves)
    bpy.utils.unregister_class(MakeHumanSelectAllPoseBones)
    bpy.utils.unregister_class(MakeHumanInsertKeyframe)
    bpy.utils.unregister_class(MakeHumanDeleteKeyframe)
    bpy.utils.unregister_class(MHToolsPanel)
    print("ok")




if __name__ == "__main__":
    register()
