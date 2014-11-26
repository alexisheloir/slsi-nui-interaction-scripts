#
# This script imports the poses that were created for a previous version of the avatar, created from MakeHuman 1.0alpha8, to the new version imported using the MHX2 importer v0.24.
# It contains a map between the old bone names to the new ones.
# Some of the bones are not present in the new skeleton version.
# The rotations are "inverted" on import to get a better resemblance of the pose.
# All poses will need to be corrected manually, anyway.

# Usage: copy into a text buffer and execute.


# Set this variable to R or L, according to which library wou wwant to import
H = 'L'

# The name of the file to load. The file is a json dump of the poses of a library
IN_FILE = 'pose_library_'+H+'.json'

# The anme of the library that will be created and populated
LIB_NAME = 'test_lib_L'



BONES_REMAP = {
	'Finger-1-1_'+H+'' : 'thumb.01.'+H+'',
	'Finger-1-2_'+H+'' : 'thumb.02.'+H+'',
	'Finger-1-3_'+H+'' : 'thumb.03.'+H+'',
	'Finger-2-1_'+H+'' : 'f_index.01.'+H+'',
	'Finger-2-2_'+H+'' : 'f_index.02.'+H+'',
	'Finger-2-3_'+H+'' : 'f_index.03.'+H+'',
	'Finger-3-1_'+H+'' : 'f_middle.01.'+H+'',
	'Finger-3-2_'+H+'' : 'f_middle.02.'+H+'',
	'Finger-3-3_'+H+'' : 'f_middle.03.'+H+'',
	'Finger-4-1_'+H+'' : 'f_ring.01.'+H+'',
	'Finger-4-2_'+H+'' : 'f_ring.02.'+H+'',
	'Finger-4-3_'+H+'' : 'f_ring.03.'+H+'',
	'Finger-5-1_'+H+'' : 'f_pinky.01.'+H+'',
	'Finger-5-2_'+H+'' : 'f_pinky.02.'+H+'',
	'Finger-5-3_'+H+'' : 'f_pinky.03.'+H+'',
	'Palm-1_'+H+'' : None,
	'Palm-2_'+H+'' : 'palm_index.'+H+'',
	'Palm-3_'+H+'' : 'palm_middle.'+H+'',
	'Palm-4_'+H+'' : 'palm_ring.'+H+'',
	'Palm-5_'+H+'' : 'palm_pinky.'+H+'',
	'Wrist-1_'+H+'' : None,
	'Wrist-2_'+H+'' : None
}

import json


shapes_file = open(IN_FILE, "r")
shapes = json.load(shapes_file)
shapes_file.close()

#print(str(shapes))

import bpy
import mathutils

#
#
# Dump the poses into a new library

if(LIB_NAME in bpy.data.actions):
    bpy.data.actions.remove(bpy.data.actions[LIB_NAME])

new_action_lib = bpy.data.actions.new(LIB_NAME)

# Maps the name of a new bone to the list of the 4 fcurves created for it.
# key is the name of the bone, value is a 4-list of the fcurves for the w,x,y,z values
target_bone_to_fcurve_map = {}


# Prepare the fcurves for this action
# For each bone in the target map
# We prepare 4 fcurves, one for each component of the rotation quaternion
for target_bone_name in BONES_REMAP.values():
    if(target_bone_name==None):
        continue
    
    # Create a group for each bone (easier visualization in the GUI)
    group_name = target_bone_name
    new_action_lib.groups.new(group_name)
    
    dpath = 'pose.bones["'+target_bone_name+'"].rotation_quaternion'
    curves = []
    for i in range(0,4):
        fc = new_action_lib.fcurves.new(dpath, index = i, action_group=group_name)
        curves.append(fc)
    # insert the fcurves reference in the map
    target_bone_to_fcurve_map[target_bone_name] = curves


IDENTITY_QUAT = mathutils.Quaternion((1,0,0,0))

# For each action we loaded from the json file
for action_number, action_name in enumerate(sorted(shapes.keys())):
    
    frame_num = action_number + 1
    
    print("Processing action '"+action_name+"'")
    action_data = shapes[action_name]
    #print("ndata="+str(len(action_data)))

    # Create an entry in the pose markers
    timelinemarker = new_action_lib.pose_markers.new(action_name)
    timelinemarker.frame = frame_num
    #print("Created tpose marker at frame "+str(timelinemarker.frame))


    # For each bone
    for bone_name in action_data:

        # Get the rotation data
        rot = action_data[bone_name]
        rot = mathutils.Quaternion(rot)
        
        # Test 
        rot.invert()

        # Find the new bone name
        #print("For bone "+bone_name)
        if(BONES_REMAP[bone_name] == None):
            if(not rot == IDENTITY_QUAT):
                print("No mapping for bone "+bone_name+" with non-identity rotation "+str(rot))
            continue

        new_bone_name = BONES_REMAP[bone_name]

        #print("Converted "+bone_name+" --> "+new_bone_name+"\tRotation "+str(rot))
        
        # Add the data to the library
        curves = target_bone_to_fcurve_map[new_bone_name]
        for i in range(0,4):
            curves[i].keyframe_points.insert(frame=frame_num, value=rot[i])
        

