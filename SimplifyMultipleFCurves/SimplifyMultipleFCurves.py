#     "Simplify Multiple F-Curves" is a Blender addon to simplify and align the keyframes of multiple F-Curves at once.
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
    "name": "Simplify Multiple F-Curves",
    "author": "Fabrizio Nunnari",
    "version": (1, 5),
    "blender": (2, 66, 0),
    "location": "Search > Simplify Curves",
    "description": "Simplifies Multiple FCurves",
    "warning": "",
    "wiki_url": "http://",
    "tracker_url": "https://",
    "category": "Animation"}

"""
This script simplifies and align keyframes of multiple F-Curves at once.
"""


import bpy
from bpy.props import * # for properties
import sys
import copy
import math
import mathutils        # for Vector

import time             # for performance timing


def print_curves_info(fcurves):
    """ Print out keyframes
    :param fcurves: An array of FCurve instances
    :return: None
    """
    
    def print_curve_keyframes(curve):
        for kf in curve.keyframe_points:
            # get time and value
            data = kf.co
            print(str(data[0]) + "\t" + str(data[1]) )
    
    for i, fcurve in enumerate(fcurves):
        data_path = fcurve.data_path        # the property affected by the curve (location, rotation, scale,...)
        array_index = fcurve.array_index    # the index for a given property. E.g., for location 0=x, 1=y, 2=z)
        rng = fcurve.range()
        n_mods = len(fcurve.modifiers)
        n_kf = len(fcurve.keyframe_points)
        n_sampled = len(fcurve.sampled_points)
        print(str(i) + "\t" + str(id(fcurve)) + "\t" + data_path + "[" + str(array_index)
            + "]\trange " + str(rng[0]) + "-" + str(rng[1])
            + "\t#modifiers " + str(n_mods) + "\t#KFs " + str(n_kf) + "\t#Sampled " + str(n_sampled))
        # print_curve_keyframes(fcurve)


class FCurveInfo:
    """This class will be used as key for the storage dictionary.
    It holds the values needed to retrieve curves from a fresh selection.
    """
    def __init__(self, data_path, array_index):
        self.data_path = data_path
        self.array_index = array_index
        # Crossed extreems for invalid info
        self.min_val = sys.maxsize
        self.max_val = -sys.maxsize
        
    def toString(self):
        return "FCurveInfo["+self.data_path+"["+str(self.array_index)+"],min="+str(self.min_val)+",max="+str(self.max_val)+"]"
        

class KFInfo:
    """This class is used to keep all the values needed to reconstruct a keyframe: coordinates, and eventually the coordinates of the tangent handles.
    """

    # It's not possible to overload the constructor in Python.
    # See: http://stackoverflow.com/questions/682504/what-is-a-clean-pythonic-way-to-have-multiple-constructors-in-python    
    
    @classmethod
    def fromCoords(cls, vector):
        out = cls()
        out.co = mathutils.Vector((vector[0], vector[1]))
        out.hasTangentsData = False
        return out
        
    @classmethod
    def fromKeyFrame(cls, kf):
        out = cls()
        out.co = mathutils.Vector((kf.co[0], kf.co[1]))
        out.hasTangentsData = True
        out.interpolation = kf.interpolation
        out.handle_left = mathutils.Vector((kf.handle_left[0], kf.handle_left[1]))
        out.handle_left_type = kf.handle_left_type
        out.handle_right = mathutils.Vector((kf.handle_right[0], kf.handle_right[1]))
        out.handle_right_type = kf.handle_right_type
        return out


def scanCurvesInfo(fcurves, sframe, eframe):
    """Stores the curves information within the specified time range (in frames on the timeline).
    Returns a pair:
        First, dictionary with key=(FCurveInfo)The source FCurve information, and data=(KFInfo[]) a list of KFInfo with curve data.
        Second, the number of keyframes stored for each curve (i.e., the size common to all the the vectors referenced by the dictionay values)
    """

    n_keyframes = 0

    # Prepare the output dictionary    
    out_dict = {}
    # Prepare a temporary association between a curve and its key in the output dictionary
    curve_to_key_map = {}

    for curve in fcurves:
        k = FCurveInfo(data_path=curve.data_path, array_index=curve.array_index)
        out_dict[k] = []
        curve_to_key_map[curve] = k

    # Prepare the array of indices that will, in parallel, scan through the keyframes of the curves.
    idxs = [-1 for i in range(len(fcurves))]
    # idxs = []
    for i, curve in enumerate(fcurves):
        kframes = curve.keyframe_points
        idx = 0
        while idx < len(kframes):
            time = kframes[idx].co[0]

            # if the time of the next keyframe is already within the required range, stop here.
            if(time < sframe):
                idxs[i] = idx
            else:
                break ;

            idx += 1    # next kframe
            
        # print("First start kf for curve " + str(i) + " = " + str(idxs[i]))
        # print("Curve Info: " + curve_info.toString())

    # Scan the curves in parallel, advancing to the next keyframe with lower timestamp among all curves.
    # When a new keyframe is found, the value is taken from all curves.
    # If a curve has not a keyframe for that time, its value is evaluated.
    done = False
    while not done:

        # Take the minimum of the next times among the curves
        next_min_time = sys.maxsize # let's say "infinite"
        for i, curve in enumerate(fcurves):
            # print_curves_info([curve])
            kframes = curve.keyframe_points
            idx = idxs[i]
            if idx < len(kframes) - 1:     # if there is still a "next keyframe"
                next_time = kframes[idx+1].co[0]    # take time of next keyframe
                # if the next time is the new minimum AND still inside the desired range.
                if next_time < next_min_time and next_time <= eframe:      # store the minimum of them
                    # print("  Next min time found in curve " + str(i) + " at idx " + str(idx+1) + ":" + str(next_time))
                    next_min_time = next_time

        # print("Next min time is " + str(next_min_time) )

        # If a valid next_min_time is found: advance indices and store the keyframe values.
        if next_min_time != sys.maxsize:
            #
            # Take note of the new KF count
            n_keyframes += 1

            #
            # Advance all the indices pointing to the next min time
            for i, curve in enumerate(fcurves):
                kframes = curve.keyframe_points
                idx = idxs[i]
                if idx < len(kframes) -1:
                    if kframes[idx+1].co[0] <= next_min_time:
                        # print("Advancing frame to " + str(idx+1) + " for curve " + str(i)) # + ": ", end="")
                        idxs[i] += 1                            # advance the kexframe

            #
            # Store value or interpolate
            for i, curve in enumerate(fcurves):
                kframes = curve.keyframe_points
                idx = idxs[i]
                curve_info = curve_to_key_map[curve]

                # What's the time of the current keyframe?
                time_at_index = None
                if idx>=0 and idx < len(kframes):
                    time_at_index = kframes[idx].co[0]

                # print("STORE crv " + str(i) + ", idx " + str(idx) + ", t " + str(time_at_index))

                if time_at_index == next_min_time:   # we are on time, store vertex info
                    new_kf_info = KFInfo.fromKeyFrame(kf=kframes[idx])
                    
                    # curve_data_key = curve_to_key_map[curve]
                    val = kframes[idx].co[1]
    
                    # UPDATE MIN/MAX
                    # print("->"+str(val))
                    if val > curve_info.max_val:
                        # print("bigger than "+str(curve_info.max_val))
                        curve_info.max_val = val            
                    if val < curve_info.min_val:
                        # print("smaller than "+str(curve_info.min_val))
                        curve_info.min_val = val
    
                else:                                   # otherwise we interpolate the value
                    val = curve.evaluate(next_min_time)
                    p = mathutils.Vector((next_min_time, val))
                    new_kf_info = KFInfo.fromCoords(vector=p)
            
                # print("Adding " + str(newKFInfo.co) + " hasTng=" + str(newKFInfo.hasTangentsData))
            
                # Finally, store the value
                out_dict[curve_info].append(new_kf_info)

        else:
            # In this case, all the indices reached the end of the curves, and none was able to record a new "min_time"
            done = True

    return out_dict, n_keyframes


#
#
#

def normalizeCurvesInfo(curves_data):
    """Normalize all the curves in parallel. Every curve keyframe value will range in [0,1].
    curves_info is expected to be a dictionary with key=(FCurveInfo)The source FCurve information, and data=(KFInfo[]) a list of KFInfo with curve data.
    Each curve will be normalized according to its min/max value.
    Outputs a dictionary with the same structure of the input one. The keys will be shared, the data vectors will be replaced by new instances."""

    out_dict = {}

    #
    # For each curve: first scan for min/max values, then replace the data with normalized ones.
    for curve_info in curves_data:
        kframesinfo = curves_data[curve_info]
        print("Normailizing "+curve_info.toString())
        #
        # Look for max absolute value in current data
        max_val = 0.0

        for kfinfo in kframesinfo:            
            val = kfinfo.co[1]
            # UPDATE MAX
            if abs(val) > max_val:
                max_val = val            

        print("Maxval="+str(max_val))

        #
        # Now normalize all values towards [0,1]
        new_frames = []        
        for kfinfo in kframesinfo:
            if max_val>0:
                new_val = kfinfo.co[1] / max_val
            else:
                new_val = kfinfo.co[1]

            p = mathutils.Vector((kfinfo.co[0], new_val))
            new_kf = KFInfo.fromCoords(p)
            new_frames.append(new_kf)

        out_dict[curve_info] = new_frames

    return out_dict

#
#
#
def altitude(point1, point2, pointn):
    """Given two points (1 and 2), calculate the distance of point N to the line passing through points 1-2."""
    edge1 = point2 - point1
    edge2 = pointn - point1
    if edge2.length == 0:
        alt = 0
        return alt
    if edge1.length == 0:
        alt = edge2.length
        return alt
    alpha = edge1.angle(edge2)
    alt = math.sin(alpha) * edge2.length
    return alt


def get_max_offset(curves_data):
    """Returns the maximum 'offset' within all the curves.
    The offset in a curve is the max distance between a keyframe value and the line connecting the extreme points.
    Such value is used as reference to apply the curve simplification.
    """
    max_offset = 0
    for frames_info in curves_data.values():
        if(len(frames_info) < 2):
            return 0
        
        p1 = frames_info[0].co
        p2 = frames_info[len(frames_info)-1].co
        
        for kfinfo in frames_info:
            offset = altitude(p1,p2,kfinfo.co)
            if(offset > max_offset):
                max_offset = offset
    
    return max_offset


def simplify_curves_R(curves_data, s_idx, e_idx, threshold_error, indices):
    """Applies a modified version of the Ramer–Douglas–Peucker algorithm to simplify multiple curves in parallel.
    See http://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm
    Take as input the curves_data as retrieved by the storeCurveInfo function.
    Append to the indices list the indices to keep for the reconstruction.
    """
    

    # Search, for each curve, at least 1 keyframe than is above the error
    bigErrorFound = False
    bigErrorValue = -1
    bigErrorCurve = None
    bigErrorIdx = None
    
    for curve in curves_data.keys():
        kframes = curves_data[curve]
        #print("For curve " + curve.data_path + str(curve.array_index))

        # For all the indices within the range
        for idx in range(s_idx+1, e_idx):
            #print("Considering index " + str(idx) + ": " + str(kframes[idx].co))
            error = altitude(point1=kframes[s_idx].co, point2=kframes[e_idx].co, pointn=kframes[idx].co)
            #print("Error="+str(error))
            if(error > threshold_error):
                bigErrorFound = True
                if(error > bigErrorValue):
                    #print("New big error found "+ str(error))
                    bigErrorValue = error
                    bigErrorCurve = curve
                    bigErrorIdx = idx
        


    # If a "bigError" is found:
    # - Insert the keyframe creating the error in the list of keyframes to keep
    # - Recurse left and right
    if(bigErrorFound):
        # Insert the retained keyframe in the list
        indices.append(bigErrorIdx)
        
        #error_time = bigErrorCurve.keyframe_points[bigErrorIdx].co[0]
        kframes = curves_data[bigErrorCurve]
        error_time = kframes[bigErrorIdx].co[0]
        #print("Biggest Error in curve " + bigErrorCurve.data_path + str(bigErrorCurve.array_index) + ": " + str(bigErrorValue) + " time="+str(error_time) + " (idx " + str(bigErrorIdx) + ")")

        #print("RECURSING")
        # left recursion
        simplify_curves_R(curves_data, s_idx, bigErrorIdx, threshold_error, indices)
        
        # right recursion
        simplify_curves_R(curves_data, bigErrorIdx, e_idx, threshold_error, indices)
        


def simplify_curves(curves_data, n_frames, error):
    """Applies a modified version of the Ramer–Douglas–Peucker algorithm to simplify multiple curves in parallel.
    See http://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm
    
    Returns the array of the indices to keep for the reconstruction.
    """


    #print(curves_data)
    #for c in curves_data.keys():
    #    print("#KFs " + str(len(curves_data[c])))

    # No curves? No party.
    if(len(curves_data) == 0):
        print("No curves selected")
        return

    
    print("From "+str(n_frames)+ " keyframes (incl. borders)")

    # Prepare the vector that will be filled with the indices to keep
    indices_to_keep = [0, n_frames-1]

    # Recurse to rerieve the indices of the keyframes to keep
    # By definition of the function, the first and the last will be kept for sure.
    simplify_curves_R(curves_data, 0, n_frames-1, threshold_error=error, indices=indices_to_keep)
    indices_to_keep.sort()
    
    print("Keeping " + str(len(indices_to_keep)) + " keyframes: " + str(indices_to_keep))
    
    return indices_to_keep



def apply_simplification(selected_curves, sframe, eframe, curves_data, indices_to_keep):
    """Applies the simplification result to the actual curves selection.
    First delets all the keyframes within the specified range, then re-build the keyframes according to the fcurves_data and the indices to keep.
    """

    def get_curve(curve_info):
        """Returns the curve with corresponding key info (data_path and array_index) from the selection.
        Returns None if the curve cannot be found.
        """

        out = None        
        for c in selected_curves:
            if(curve_info.data_path == c.data_path and curve_info.array_index == c.array_index):
                out = c
                break
        return out
    
    # Update the keyframes of the selected curves
    for curve_key in curves_data.keys():
        # retrieves the curve with corresponding key info from the selection      
        curve = get_curve(curve_key)
        
        #print("Retrieved from selection: " + str(curve))
        
        if(curve==None):
            print("No data were stored for curve: " + curve_key.data_path + str(curve_key.array_index))
            continue                            # <---- Warning!!! Skip cycle.
        
        #print("Before: ", end="")
        #print_curves_info([curve])
        
        kframes = curve.keyframe_points

        #
        # DELETE existing keyframes

        # move to the first valid kf
        idx = 0
        while(idx < len(kframes)):
            if(kframes[idx].co[0] >= sframe):
                break ;
            idx += 1
        # delete as long as the time is within the range
        while(idx < len(kframes)):
            time = kframes[idx].co[0]
            if(time > eframe):
                break
            #print("Deleting kframe " + str(idx))
            kframes.remove(kframes[idx])
            
        #
        # RE-ADDING FRAMES

        #print("ADDING FRAMES in: " + curve_key.data_path + str(curve_key.array_index))
        kfdata = curves_data[curve_key]

        # Single Step: tangent data ignored
        for i in indices_to_keep:
            #print("Adding coordinates for index " + str(i) + " " + str(kfdata[i].co))
            kfinfo = kfdata[i]
            newkf = kframes.insert(frame=kfinfo.co[0], value=kfinfo.co[1], options={'FAST'})

        # print("After: ", end="")
        # print_curves_info([curve])


#########################################################################
### Auxiliary methods, common to all Operators
#########################################################################

def get_range(curves):
    """Returns a pair, with min and max range among all curves.
    Returns None if no curves are selected.
    :param curves: """
    
    # Set extreme ranges
    min_val = sys.maxsize
    max_val = - sys.maxsize
    
    # Scan curves
    for c in curves:
        r = c.range()
        if r[0] < min_val: min_val = r[0]
        if r[1] > max_val: max_val = r[1]
        
    if min_val == sys.maxsize or max_val == -sys.maxsize:
        return None, None
    
    return min_val, max_val


def get_selected_fcurves(context):
    obj = context.active_object

    # Retrieve selected curves list
    selected_fcurves = []
    for fc in obj.animation_data.action.fcurves:  # It is valid because has been already polled
        if fc.select:
            selected_fcurves.append(fc)

    # retrieve range
    scene = bpy.context.scene
    if scene.use_preview_range:
        sframe = scene.frame_preview_start
        eframe = scene.frame_preview_end
    else:
        sframe, eframe = get_range(selected_fcurves)
        # if(sframe == None):
        #     operator.report({'ERROR'}, "No curves selected!")

    print("Selected " + str(len(selected_fcurves)) + " curves in range " + str(sframe) + "-" + str(eframe))

    return selected_fcurves, sframe, eframe


#####

#def store_fcurves_data(operator, selected_fcurves, sframe, eframe, context):
#    """Scan the context to find the updated list of selected curves, and retrieve the data needed for reconstruction.
#    The retrieved data will be put in the fcurves_data, fcurves_max_offset and fcurves_max_keyframes attributes of the operator.
#    """
#    
#    # Will be in fact invoked at first call, when new curves are selected and the operator is created.
#    if not operator.fcurves_data:            
#        print("==========================> Storing curves <============================")
#        print_curves_info(selected_fcurves)
#        operator.fcurves_data, operator.fcurves_max_keyframes = scanCurvesInfo(fcurves=selected_fcurves, sframe=sframe, eframe=eframe)
#        operator.fcurves_max_offset = get_max_offset(operator.fcurves_data)
#        print("Stored KFs=" + str(operator.fcurves_max_keyframes) + ", Max Error among curves=" + str(operator.fcurves_max_offset))
#        

#####

def check_fcurves_data(operator, fcurves_data):
    """Checks that there are at least 1 curve and 2 keyframes selected.
    If the selection is not satisfactory, an error pop-up is displayed.
    Returns if Ok, False otherwise.
    :param fcurves_data:
    :param operator: """
    
    if len(fcurves_data) < 1:
        operator.report({'ERROR'}, "No curves data!")
        return False
    
    first_curve_key = [ k for k in fcurves_data.keys()][0]
    first_curve_data = fcurves_data[first_curve_key]
    n_kf = len(first_curve_data)
    if n_kf < 2:
        operator.report({'ERROR'}, "At least 2 KF must be in selected range!")
        return False
    
    return True


#####

def poll_for_fcurves(context):
    """Used by operators as static method to check if the user selected an object and its F-Curves.
    """

    obj = context.active_object
    # Well, there should always be an active object...
    if obj:
        animdata = obj.animation_data
        if animdata:
            act = animdata.action
            if act:
                fcurves = act.fcurves                
                if fcurves:
                    n_selected_curves = sum([1 if c.select else 0 for c in fcurves])
                    # print("poll n curves")
                    # print(n_selected_curves)
                    if n_selected_curves>0:
                        return True

    return False


###########################################################################################
#### ANIMATION CURVES OPERATOR: DESELECT ALL ANIMATION FCURVES FOR THE ACTIVE OBJECT ##################
###########################################################################################
class GRAPH_OT_DeselectFCurves(bpy.types.Operator):
    """Deselects all the fcurves of the active object, including the curves of its pose bones,
     if the object is an armature."""

    bl_idname = "graph.deselect_fcurves"
    bl_label = "Deselect F-Curves of Active Object"
    bl_description = "Deselect all the F-Curves of the active object, including the curves of its pose bones, if the object is an armature."
    bl_options = {'REGISTER', 'UNDO'}
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj != None

    def execute(self, context):
        obj = bpy.context.active_object
        action = obj.animation_data.action

        for c in action.fcurves:
            c.select=False
            # print(str(c.select) + "\t" + str(c.data_path))

        return {'FINISHED'}


#########################################################################
#### ANIMATION CURVES OPERATOR: SIMPLIFY BY PERCENTAGE ##################
#########################################################################
class GRAPH_OT_SimplifyMultipleCurves(bpy.types.Operator):
    """Simplify multiple curves at once, aligning keyframes, specifying a percentage of simplification."""

    bl_idname = "graph.simplify_multiple_curves"
    bl_label = "Simplifiy Multiple F-Curves"
    bl_description = "Simplify all Selected FCurves aligning their keyframes"
    bl_options = {'REGISTER', 'UNDO'}
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        return poll_for_fcurves(context)

    def execute(self, context):
        print("EXECUTE "+str(hex(id(self)))+ ", context="+str(context))

        selected_fcurves, sframe, eframe = get_selected_fcurves(context)
        print("*"*20 + " SELECTION:")
        print_curves_info(selected_fcurves)
        print("*"*20)

        #
        # fill the fcurves_data and fcurves_max_offset fields
        print("==========================> Storing curves <============================")
        before = time.time()
        fcurves_data, fcurves_max_keyframes = scanCurvesInfo(fcurves=selected_fcurves, sframe=sframe, eframe=eframe)
        after = time.time() ; elapsed = after-before
        print("Storing time (secs): "+str(elapsed))
        print("Stored KFs=" + str(fcurves_max_keyframes))
        for curve_info in fcurves_data:
            print("Curve Info: " + curve_info.toString() + " - #kframes="+str(len(fcurves_data[curve_info])))
        print("========================================================================")

        #
        # Check data consistency
        if(not check_fcurves_data(self, fcurves_data)):
            return {'CANCELLED'}

        normalize = context.scene.simplify_fcurves_normalize
        if(normalize):
            print("==========================> NORMALIZATION <============================")
            before = time.time()
            normalized_fcurves_data = normalizeCurvesInfo(fcurves_data)
            after = time.time() ; elapsed = after-before
            print("Normalization time (secs): "+str(elapsed))
            print("========================================================================")

        # Variable to store the maximum offset among all curves
        # Needed to control the simplification as percentage
        before = time.time()
        if(normalize):
            fcurves_max_offset = get_max_offset(normalized_fcurves_data)
        else:
            fcurves_max_offset = get_max_offset(fcurves_data)
        after = time.time() ; elapsed = after-before
        print("Computation of max offset time (secs): "+str(elapsed))
        print("Max Error among curves=" + str(fcurves_max_offset))

        error_pct = context.scene.simplify_fcurves_error
        print("Simplification Error Pct = " + str(error_pct))
        err = fcurves_max_offset * error_pct / 100.0
        print("Simplifying with error: "+str(err))

        print("*"*20)
        before = time.time()
        if(normalize):
            kept_indices = simplify_curves(curves_data=normalized_fcurves_data, n_frames=fcurves_max_keyframes, error=err)
        else:
            kept_indices = simplify_curves(curves_data=fcurves_data, n_frames=fcurves_max_keyframes, error=err)
        after = time.time() ; elapsed = after-before
        print("Simplification time (secs): "+str(elapsed))
        print("*"*20)


        print("+"*20)
        # def apply_simplification(selected_curves, sframe, eframe, curves_data, indices_to_keep):
        before = time.time()        
        apply_simplification(selected_curves=selected_fcurves, sframe=sframe, eframe=eframe, curves_data=fcurves_data, indices_to_keep=kept_indices)
        after = time.time() ; elapsed = after-before
        print("Reconstruction time (secs): "+str(elapsed))
        print("+"*20)

        return {'FINISHED'}
    

#########################################################################
#### ANIMATION CURVES OPERATOR: SIMPLIFY BY MAX KF NUMBER ###############
#########################################################################
class GRAPH_OT_SimplifyMultipleCurvesKF(bpy.types.Operator):
    """Simplify multiple curves at once, aligning keyframes, specifying the max number of keyframes"""
    
    bl_idname = "graph.simplify_multiple_curves_kf"
    bl_label = "Simplifiy Multiple F-Curves by Max KF"
    bl_description = "Simplify all Selected FCurves aligning their keyframes by specifying a maximum number of keyframes"
    bl_options = {'REGISTER', 'UNDO'}
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        return poll_for_fcurves(context)

    def execute(self, context):
        print("EXECUTE")

        selected_fcurves, sframe, eframe = get_selected_fcurves(context)
        print("*"*20 + " SELECTION:")
        print_curves_info(selected_fcurves)
        print("*"*20)

        #
        # fill the fcurves_data and fcurves_max_offset fields
        print("==========================> Storing curves <============================")
        before = time.time()
        fcurves_data, fcurves_max_keyframes = scanCurvesInfo(fcurves=selected_fcurves, sframe=sframe, eframe=eframe)
        after = time.time() ; elapsed = after-before
        print("Storing time (secs): "+str(elapsed))
        print("Stored KFs=" + str(fcurves_max_keyframes))
        for curve_info in fcurves_data:
            print("Curve Info: " + curve_info.toString() + " - #kframes="+str(len(fcurves_data[curve_info])))
        print("========================================================================")

        #
        # Check data consistency
        if(not check_fcurves_data(self, fcurves_data)):
            return {'CANCELLED'}


        normalize = context.scene.simplify_fcurves_normalize
        if(normalize):
            print("==========================> NORMALIZATION <============================")
            before = time.time()
            normalized_fcurves_data = normalizeCurvesInfo(fcurves_data)
            after = time.time() ; elapsed = after-before
            print("Normalization time (secs): "+str(elapsed))
            print("========================================================================")


        # Variable to store the maximum offset among all curves
        # Needed to control the simplification as percentage
        before = time.time()
        if(normalize):
            fcurves_max_offset = get_max_offset(normalized_fcurves_data)
        else:
            fcurves_max_offset = get_max_offset(fcurves_data)
        after = time.time() ; elapsed = after-before
        print("Computation of max offset time (secs): "+str(elapsed))
        print("Max Error among curves=" + str(fcurves_max_offset))
            

        maxkf = context.scene.simplify_fcurves_max_keyframes
        print("Trying to simplify for max #KF " + str(maxkf))

        # The relative precision to use to keep on trying to optimize the search
        relativePrecision = 0.001

        # The refinement algorithm will stop if the difference in error value between two cycles is less then this value.
        precision = relativePrecision * fcurves_max_offset
        print("Precision " + str(precision))

        minErr = 0
        maxErr = fcurves_max_offset
        err = minErr

        # We will cycle trying to simplify curves using a crescent error.
        # an error to maxErr is the safest choice, because with only 2 KF you are surely satisfying the constraint.
        # an error of 0 is the safest choice to preserve all KF when the KF constraint is higher than the actual number of KFs
        # In other words. max error is safer, min error is desirable
        # We start attempting a search at error 0 (max Keyframes), but then move to max error if the 
        kept_indices = []
        done = False
        while(not done):
            print("Trying simplification with error " + str(err))

            if(normalize):
                kept_indices = simplify_curves(curves_data=normalized_fcurves_data, n_frames=fcurves_max_keyframes, error=err)
            else:
                kept_indices = simplify_curves(curves_data=fcurves_data, n_frames=fcurves_max_keyframes, error=err)
            n = len(kept_indices)

            print("--> " + str(n) + " KFs")
            if(n > maxkf): # we have to increase the error to have less keyframes
                minErr = err
            else:               # we can decrease the error to increment the keyframes
                maxErr = err

            new_err = minErr + ((maxErr - minErr) / 2.0)
            delta = abs(new_err - err)
            print("Min/Max " + str(minErr) + " / " + str(maxErr) + ", New_err " + str(new_err) + ", delta " + str(delta))
            err = new_err            
            
            if(delta <= precision):
                # if during the last computation we were exceeding the n of keyframes,
                # then set the error back in a safe zone
                if(n > maxkf):
                    err = maxErr
                    if(normalize):
                        kept_indices = simplify_curves(curves_data=normalized_fcurves_data, n_frames=fcurves_max_keyframes, error=err)
                    else:
                        kept_indices = simplify_curves(curves_data=fcurves_data, n_frames=fcurves_max_keyframes, error=err)
                done = True
                
        print("Final err " + str(err))

        # def apply_simplification(selected_curves, sframe, eframe, curves_data, indices_to_keep):
        apply_simplification(selected_curves=selected_fcurves, sframe=sframe, eframe=eframe,
                             curves_data=fcurves_data, indices_to_keep=kept_indices)

        return {'FINISHED'}


#################################################
#### ANIMATION CURVES PANEL ##################
#################################################
class GRAPH_OT_SimplifyMultipleCurvesPanel(bpy.types.Panel):
    bl_label = "Simplify Multiple F-Curves"
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = 'UI'
    # enum in ['WINDOW', 'HEADER', 'CHANNELS', 'TEMPORARY', 'UI', 'TOOLS', 'TOOL_PROPS', 'PREVIEW'], default 'WINDOW'

    def draw(self, context):
        self.layout.label("Simplify Multiple F-Curves:")
        self.layout.operator("graph.simplify_multiple_curves", text="by Error")
        self.layout.operator("graph.simplify_multiple_curves_kf", text='by Max keyframes')
        self.layout.separator()
        self.layout.label("Options:")
        self.layout.prop(context.scene, "simplify_fcurves_normalize")
        self.layout.prop(context.scene, "simplify_fcurves_error")
        self.layout.prop(context.scene, "simplify_fcurves_max_keyframes")
        self.layout.separator()
        self.layout.label("Tools:")
        self.layout.operator("graph.deselect_fcurves")  # , text='by Max keyframes')
        self.layout.separator()
        self.layout.label("Info:")
        obj = bpy.context.active_object
        n_selected_curves = "N/A"
        if obj.animation_data is not None:
            action = obj.animation_data.action
            if action is not None:
                n_selected_curves = sum([1 if c.select else 0 for c in action.fcurves])
        self.layout.label("# selected curves: "+str(n_selected_curves))


#################################################
# REGISTER ###################################
#################################################
def register():
    print("Registering Simplify Multiple F-Curves classes...")
    bpy.types.Scene.simplify_fcurves_error =\
        bpy.props.FloatProperty(name="Max Error (%)",
                                description="Error Percentage. With 0 the curve won't be simplified. With 100% the curve will be fully simplified (only border keyframes are retained).",
                                min=0.0,
                                max=100.0,
                                subtype="PERCENTAGE",
                                default=0, precision=2)
    bpy.types.Scene.simplify_fcurves_max_keyframes =\
        bpy.props.IntProperty(name="Max #KF", description="Max number of keyframes retained after simplification",
                              min=2, default = 2)
    bpy.types.Scene.simplify_fcurves_normalize =\
        bpy.props.BoolProperty(name="Normalize", default=True,
                               description="If True, the curves are normalized in the range 0-1 befaore performing the simplification. So that curves with bigger amplitudes do not _eat_ the small ones.")

    bpy.utils.register_class(GRAPH_OT_DeselectFCurves)
    bpy.utils.register_class(GRAPH_OT_SimplifyMultipleCurves)
    bpy.utils.register_class(GRAPH_OT_SimplifyMultipleCurvesKF)
    bpy.utils.register_class(GRAPH_OT_SimplifyMultipleCurvesPanel)


def unregister():
    print("Unregistering Simplify Multiple F-Curves classes...")
    bpy.utils.unregister_class(GRAPH_OT_SimplifyMultipleCurvesPanel)
    bpy.utils.unregister_class(GRAPH_OT_SimplifyMultipleCurvesKF)
    bpy.utils.unregister_class(GRAPH_OT_SimplifyMultipleCurves)
    bpy.utils.unregister_class(GRAPH_OT_DeselectFCurves)

    del bpy.context.scene.simplify_fcurves_error
    del bpy.context.scene.simplify_fcurves_max_keyframes
    del bpy.context.scene.simplify_fcurves_normalize


if __name__ == "__main__":
    register()
