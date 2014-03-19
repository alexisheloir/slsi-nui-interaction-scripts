#     "Trim F-Curves" is a Blender addon to trim F-Curves by deleting keyframes outside the time range selection.
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
    "name": "Trim F-Curves",
    "author": "Fabrizio Nunnari",
    "version": (1,0),
    "blender": (2, 66, 0),
    "location": "Search > Trim FCurves",
    "description": "Trim F-Curves by deleting keyframes outside the time range selection.",
    "warning": "",
    "wiki_url": "http://",
    "tracker_url": "https://",
    "category": "Animation"}

"""
Trim F-Curves is a Blender addon to trim F-Curves by deleting keyframes outside the time range selection.
"""

import bpy

#########################################################################
#### OPERATOR: TRIM FCURVES                            ##################
#########################################################################
class TrimFCurves(bpy.types.Operator):
    """Trim F-Curves by deleting keyframes outside the time range selection."""

    bl_idname = "graph.trim_fcurves"
    bl_label = "Trim F-Curves"
    bl_description = "Trim F-Curves by deleting keyframes outside the time range selection."
    bl_options = {'REGISTER', 'UNDO'}
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        #print("POLL")
        obj = context.active_object
        fcurves = False
        if obj:
            animdata = obj.animation_data
            if animdata:
                act = animdata.action
                if act:
                    fcurves = act.fcurves
        return (obj and fcurves)


    def execute(self, context):
        #
        # Take the selection
        obj = context.active_object
        selected_fcurves = []
        for fc in obj.animation_data.action.fcurves: # It is valid because has been already polled
            if (fc.select):
                selected_fcurves.append(fc)

        #print("SELECTED "+str(len(selected_fcurves)))

        #
        # Take the time range
        sframe = None
        eframe = None
    
        scene = context.scene
        if(scene.use_preview_range):
            sframe = scene.frame_preview_start
            eframe = scene.frame_preview_end
        else:
            sframe = scene.frame_start
            eframe = scene.frame_end
            
        #
        # Cycle to delete outside keyframes, for each curve
        for fcurve in selected_fcurves:
            i = 0
            keyframes = fcurve.keyframe_points
            # Run through the keyframes, and delete the ones outside the range.
            while(i < len(keyframes)):
                kf = keyframes[i]
                frame = kf.co[0]
                if(frame < sframe or frame > eframe):
                    # delete the keyframe and keep the index at this position
                    #print("Removing keyframe at position " + str(frame))
                    keyframes.remove(kf)
                else:
                    # else advance in the keyframes vector
                    i += 1

        return {'FINISHED'}
    
    
    def invoke(self, context, event):
        return self.execute(context)


#################################################
#### PANEL                     ##################
#################################################
class TrimFCurvesPanel(bpy.types.Panel):
    bl_label = "Trim F-Curves"
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = 'UI'
    #enum in ['WINDOW', 'HEADER', 'CHANNELS', 'TEMPORARY', 'UI', 'TOOLS', 'TOOL_PROPS', 'PREVIEW'], default 'WINDOW'

    def draw(self, context):
        self.layout.operator("graph.trim_fcurves", text="Trim")



#################################################
#### SYS                       ##################
#################################################

def register():
    print("Registering TrimFCurves classes...")
    bpy.utils.register_class(TrimFCurves)
    bpy.utils.register_class(TrimFCurvesPanel)
    print("done")
    
def unregister():
    print("Unregistering TrimFCurves classes...")
    bpy.utils.unregister_class(TrimFCurves)
    bpy.utils.unregister_class(TrimFCurvesPanel)
    print("done")

if __name__ == "__main__":
    register()
