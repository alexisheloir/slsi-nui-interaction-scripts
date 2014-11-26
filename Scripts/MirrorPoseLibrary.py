# This script will copy the poses of one hand, stored in a pose library, to another library, mirrored for the opposite hand.
# It is useful if you need to correct or add some new poses. Just add them to one hand, and run this script to generate the mirror library.

# Usage: first load the SLSI scripts (some operators to select the hand bones are needed), then copy the script in a text buffer and execute.

import bpy

# The name of the original pose library
IN_LIB_NAME = "handshape_lib_L"
# The name of the target library. It must elready exist. It will be emptied of the marker names before the copy is performed. Warning: keyframes alredy existing in this library will not be deleted. Do it manually before executing.
OUT_LIB_NAME = "handshape_lib_R"


in_lib = bpy.data.actions[IN_LIB_NAME]
out_lib = bpy.data.actions[OUT_LIB_NAME]

# delete old pose markers
for old_pose in out_lib.pose_markers:
    print("Removing old pose "+old_pose.name)
    out_lib.pose_markers.remove(old_pose)

# for each pose in the IN library
for pose in in_lib.pose_markers:
    print("Copying pose '"+pose.name+"' at frame "+str(pose.frame))

    # select IN library
    bpy.context.object.animation_data.action = in_lib

    # position cursor
    bpy.context.scene.frame_current = pose.frame

    # Unselect all and select the left hand bones
    bpy.ops.pose.select_all(action='DESELECT')
    bpy.ops.object.mh_select_hand_bones(right_hand=False, left_hand=True)
    
    # copy the pose
    bpy.ops.pose.copy()
    
    # select the OUT library
    bpy.context.object.animation_data.action = out_lib
    
    # Unselect all and select the left hand bones
    bpy.ops.pose.select_all(action='DESELECT')
    bpy.ops.object.mh_select_hand_bones(right_hand=True, left_hand=False)

    # copy flipped pose
    bpy.ops.pose.paste(flipped=True)

    # insert roation info
    bpy.ops.anim.keyframe_insert(type='Rotation')
    
    # copy pose name
    new_pose = out_lib.pose_markers.new(pose.name)
    new_pose.frame = pose.frame
    
