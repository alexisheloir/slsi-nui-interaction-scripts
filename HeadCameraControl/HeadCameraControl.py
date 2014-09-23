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
# This script ...
#
# Press alt+fhift+p to activate. Same to end.
#

# Modal listening method taken from Screencast Key Status Tool
# http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/3D_interaction/Screencast_Key_Status_Tool

import bpy
import bgl
import blf
import mathutils

from bpy.props import * # for properties

import time

import struct
import socket



# properties used by the script
def init_properties():
    # Runstate initially always set to False
    # note: it is not stored in the Scene, but in window manager:
    bpy.types.WindowManager.head_camera = bpy.props.BoolProperty(default=False)


# removal of properties when script is disabled
def clear_properties():
    if(bpy.context.window_manager.head_camera):
        del(bpy.context.window_manager.head_camera)



def draw_callback_px(self, context):
    bgl.glPushAttrib(bgl.GL_CLIENT_ALL_ATTRIB_BITS)

    FONT_RGBA = (0.8, 0.1, 0.1, 0.5)
    bgl.glColor4f(*FONT_RGBA)

    font_size = 11
    DPI = 72

    blf.size(0, font_size, DPI)
    msg = "Head Camera on..."
    
    msg_w,msg_h = blf.dimensions(0, msg)

    pos_x = context.region.width - msg_w
    pos_y = font_size / 2
    blf.position(0, pos_x, pos_y, 0)
    #blf.position(0, 10, 10, 0)

    blf.draw(0, msg)

    bgl.glPopAttrib()

    pass
    
    

class HeadCameraOn(bpy.types.Operator):
    bl_idname = "view3d.head_camera_on"
    bl_label = "Turns Head-driven camera control on (if not already)"
    bl_description = "The current camera position is controlled by remote head movement."
    
    # Whether to use the camera or not. If not, the region 3d viewport is used instead. This is false by default.
    rotationAngle = FloatProperty(name="Rotation Angle", default = 45, min=0.0, step=100, description="How much the camera or the view will rotate around the pivot according to the head movement")
    useCamera = BoolProperty(name="Manipulare the camera instead of the viewport", description="If true, the camera will be moved, instead of the viewport", default=False)
    cameraOffset = FloatProperty(name="Camera Offset", description="How much the camera should pan according to the head movement" , default=2.0)
    cameraPivotDistance = FloatProperty(name="Camera Pivot Distance", description="The distance f the imaginary point around which the camera will rotate", default=20.0)



    def invoke(self, context, event):
        return self.execute(context)
        
    def execute(self, context):
        print("Invoked HeadCameraOn")

        if context.window_manager.head_camera is False:
            bpy.ops.view3d.head_camera_switch(useCamera = self.useCamera, cameraOffset = self.cameraOffset, cameraPivotDistance=self.cameraPivotDistance, rotationAngle=self.rotationAngle)

        return {'FINISHED'}


class HeadCameraOff(bpy.types.Operator):
    bl_idname = "view3d.head_camera_off"
    bl_label = "Turns Head-driven camera control off (if not already)"
    bl_description = "Stop The current camera position is controlled by remote head movement."

    def invoke(self, context, event):
        return self.execute(context)
        
    def execute(self, context):
        print("Invoked HeadCameraOff")

        if context.window_manager.head_camera is True:
            bpy.ops.view3d.head_camera_switch()

        return {'FINISHED'}
        



class SwitchHeadCameraStatus(bpy.types.Operator):
    bl_idname = "view3d.head_camera_switch"
    bl_label = "Switch Camera"
    bl_description = "The current camera position is controlled by remote head movement."
    
    #logActiveObjectTransform = BoolProperty(name="Log loc/rot/scale of the active object", description="If true, the log will include a sampling of the current active object location x y z, rotation_quaternion w x y z and scale x y z.", default=False)

    # Whether to use the camera or not. If not, the region 3d viewport is used instead. This is false by default.
    rotationAngle = FloatProperty(name="Rotation Angle", default = 45, min=0.0, step=100, description="How much the camera or the view will rotate around the pivot according to the head movement")
    useCamera = BoolProperty(name="Manipulare the camera instead of the viewport", description="If true, the camera will be moved, instead of the viewport", default=False)
    cameraOffset = FloatProperty(name="Camera Offset", description="How much the camera should pan according to the head movement" , default=2.0)
    cameraPivotDistance = FloatProperty(name="Camera Pivot Distance", description="The distance f the imaginary point around which the camera will rotate", default=20.0)

    # Reference to a bpy.data.texts entry, where log is eventually written
    text_buffer = None

    _handle = None
    _timer = None
    
    
    
    def adjustCameraPosition(self, x, y, area):
        # I want to shift/pan the position of the camera according to the face position factors.
        x *= self.cameraOffset
        y *= self.cameraOffset

        dx = mathutils.Vector((x, 0.0, 0.0))
        dy = mathutils.Vector((0.0, y, 0.0))

        dx = self.initial_rotation * dx
        dy = self.initial_rotation * dy

        self.camera.location = self.initial_location + dx + dy


        # Update lenses
        #cam = bpy.data.cameras[self.camera.name]
        #cam.lens = self.initial_lens * area
    
        pass


    def adjustCameraPosition2(self, x, y, area):
        # I want to shift/pan the position of the camera according to the face position factors.

        AMP = self.rotationAngle
        x_angle = x * AMP
        y_angle = - y * AMP

        dist = self.cameraPivotDistance

        # bring camera back to center of view
        d_neg = mathutils.Matrix.Translation(mathutils.Vector((0, 0, -dist)))
        # rotate it around two axes
        x_rot = mathutils.Matrix.Rotation(x_angle, 4, 'Y')
        y_rot = mathutils.Matrix.Rotation(y_angle, 4, 'X')
        # and bring it back to position
        d_pos = mathutils.Matrix.Translation(mathutils.Vector((0, 0, dist)))
    
        Mx = d_neg * x_rot * y_rot * d_pos
    
        # Compose the view_matrix with the actual deltas
        self.camera.matrix_basis = self.initial_matrix * Mx


        # Update lenses
        #cam = bpy.data.cameras[self.camera.name]
        #cam.lens = self.initial_lens * area
    
        pass
    
    
    def adjustViewportPosition(self, x, y, area):
        # I want to shift/pan the position of the camera according to the face position factors.
        
    
        # Modulate pan quantity according to view distance.    
        # We can shift the view up to 10% of the view distance
        AMP = self.space.region_3d.view_distance * 0.1
        # Apply to offsets, and invert axes.
        x *= - AMP
        y *= - AMP
        
        # orient the pan vector according to original viewpot orientation
        pan_vector = mathutils.Vector((x,y,0.0))
        pan_vector = self.initial_rotation * pan_vector
    
        # Compose the view_matrix with the actual deltas
        self.space.region_3d.view_matrix = self.initial_matrix * mathutils.Matrix.Translation(pan_vector)
        
        #self.space.lens = self.initial_lens * area
    
        pass
    
    def adjustViewportPosition2(self, x, y, area):
        # I want to rotate the position of the view around the pivot according to the face position factors.
        
        
        AMP = self.rotationAngle
        x_angle = - x * AMP
        y_angle = y * AMP

        dist = self.space.region_3d.view_distance

        # bring camera back to center of view
        d_neg = mathutils.Matrix.Translation(mathutils.Vector((0, 0, -dist)))
        # rotate it around two axes
        x_rot = mathutils.Matrix.Rotation(x_angle, 4, 'Y')
        y_rot = mathutils.Matrix.Rotation(y_angle, 4, 'X')
        # and bring it back to position
        d_pos = mathutils.Matrix.Translation(mathutils.Vector((0, 0, dist)))
    
        Mx = d_neg * x_rot * y_rot * d_pos
    
        # Compose the view_matrix with the actual deltas
        #self.space.region_3d.view_matrix = self.initial_matrix * Mx
        self.space.region_3d.view_matrix = Mx * self.initial_matrix
        
        #self.space.lens = self.initial_lens * area
    
        pass
    



    

    @staticmethod
    def handle_add(self, context):
        SwitchHeadCameraStatus._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL')
        SwitchHeadCameraStatus._timer = context.window_manager.event_timer_add(0.04, context.window)

    @staticmethod
    def handle_remove(context):
        if SwitchHeadCameraStatus._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(SwitchHeadCameraStatus._handle, 'WINDOW')
            SwitchHeadCameraStatus._handle = None

        if SwitchHeadCameraStatus._timer is not None:
            context.window_manager.event_timer_remove(SwitchHeadCameraStatus._timer)
            SwitchHeadCameraStatus._timer = None

        

    def invoke(self, context, event):
        return self.execute(context)
        
    def execute(self, context):
        print("Invoked SwitchHeadCameraStatus")

        if context.window_manager.head_camera is False:
            # operator is called for the first time, start everything
            print("HeadCamera first call")
            
            if(self.useCamera):
                # Take camera info
                # I want a reference to a Camera instance, not an Object instance.
                self.camera = bpy.context.scene.camera
                self.initial_location = mathutils.Vector(self.camera.location)
                self.initial_rotation = mathutils.Quaternion(self.camera.rotation_quaternion)
                self.initial_matrix = mathutils.Matrix(self.camera.matrix_basis)
                cam = bpy.data.cameras[self.camera.name]
                self.initial_lens = cam.lens
                print("Stored location="+str(self.initial_location)+", rotation="+str(self.initial_rotation)+", lens="+str(self.initial_lens))

            else:   # Store data for the viewport
    

                # Save View Matrix info
                space = bpy.context.area.spaces.active
                print("Active Space " + space.type)
                if(space.type != 'VIEW_3D'):
                    self.report({'ERROR'}, "Active space is not a VIEW_3D")
                    return {'CANCELLED'}
    
                self.space = space
                
                self.initial_matrix = mathutils.Matrix(self.space.region_3d.view_matrix)
                self.initial_rotation = self.space.region_3d.view_rotation
                self.initial_lens = self.space.lens
                
                print("Stored matrix="+str(self.initial_matrix)+", initial_rotation="+str(self.initial_rotation)+", lens="+str(self.initial_lens))
    
    

            # Init OSC receiver
            #ip_dump = 'localhost'
            ip_dump = '127.0.0.1'
            host_dump = 12005
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket.setblocking(0)
                self.socket.settimeout(0.01)
                #self.sock.setsockopt(level, optname, value)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 50)    # No buffer. We take the latest, if present, or nothing.
                self.socket.bind((ip_dump, host_dump))
            except OSError as err:
                print("Exception creating socket: "+str(err))
                if(self.socket != None):
                    self.socket.close()
                    self.socket = None
                return {'CANCELLED'}

            

            # Synch stuff
            context.window_manager.head_camera = True
            SwitchHeadCameraStatus.handle_add(self, context)
            context.window_manager.modal_handler_add(self)

    
            # Force redraw to print informative message                        
            if context.area:
                context.area.tag_redraw()

            return {'RUNNING_MODAL'}

        else:
            # operator is called again, stop displaying
            print("HeadCamera stop")
            context.window_manager.head_camera = False
            return {'CANCELLED'}


    def modal(self, context, event):
        #if context.area:
        #    context.area.tag_redraw()

        if not context.window_manager.head_camera:
            # stop script
            SwitchHeadCameraStatus.handle_remove(context)
            if context.area:
                context.area.tag_redraw()
                
            # shutdown Network
            self.socket.close()
            self.socket = None

            # Restore camera/viewport positions
            if(self.useCamera):
                self.camera.location = self.initial_location
                self.camera.rotation_quaternion = self.initial_rotation
                cam = bpy.data.cameras[self.camera.name]
                cam.lens = self.initial_lens
            else:
                self.space.region_3d.view_matrix = self.initial_matrix
                self.space.region_3d.view_rotation = self.initial_rotation
                self.space.lens = self.initial_lens
            
            # Reset vlaues
            self.camera = None      
            self.space = None
            self.initial_matrix = None
            self.initial_location = None
            self.initial_rotation = None
            self.initial_lens = None

            return {'FINISHED'}

        if event.type == 'MOUSEMOVE':
            return {'PASS_THROUGH'}
            

        if event.type == 'TIMER':
            try:
                raw_msg = self.socket.recv(1024)
                x,y,area = struct.unpack_from('fff', raw_msg, 0)
                #print("Received from UDP "+str(x)+"\t"+str(y)+"\t"+str(area))
                
                if(self.useCamera):
                    self.adjustCameraPosition2(x, y, area)
                else:
                    self.adjustViewportPosition2(x, y, area)
                
            except socket.timeout as to_msg:
                #print("We know it: " + str(to_msg))
                pass    # We know. Can happen very often            

            return {'PASS_THROUGH'}

        if event.type == 'TIMER_REPORT':
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}


    def cancel(self, context):
        if context.window_manager.head_camera:
            SwitchHeadCameraStatus.handle_remove(context)
            #context.window_manager.screencast_keys_keys = False
        return {'CANCELLED'}

    def __init__(self):
        self.socket = None

    def __del__(self):
        # The sock attribute might not have been defined if the command was never run
        print("Deleting SwitchHeadCameraStatus instance"+str(self))
        if(hasattr(self, 'socket')):
            print("Socket was defined")
            if(self.socket != None):
                print("Closing surviving socket")
                self.socket.close()
                self.socket = None





# store keymaps here to access after registration
addon_keymaps = []


def register():
    print("Registering HeadCamera classes")
    init_properties()
    
    bpy.utils.register_class(SwitchHeadCameraStatus)
    bpy.utils.register_class(HeadCameraOn)
    bpy.utils.register_class(HeadCameraOff)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')

        kmi = km.keymap_items.new('view3d.head_camera_switch', 'P', 'PRESS', shift=True, alt=True)
        kmi.properties.useCamera = False
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new('view3d.head_camera_switch', 'O', 'PRESS', shift=True, alt=True)
        kmi.properties.useCamera = True
        addon_keymaps.append((km, kmi))


def unregister():
    print("Unregistering HeadCamera classes")

    # in case its enabled
    SwitchHeadCameraStatus.handle_remove(bpy.context)

    bpy.utils.unregister_class(SwitchHeadCameraStatus)
    bpy.utils.unregister_class(HeadCameraOn)
    bpy.utils.unregister_class(HeadCameraOff)

    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    clear_properties()


if __name__ == "__main__":
    register()
