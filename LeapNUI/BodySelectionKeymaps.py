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
import bgl
import blf

import os
from bpy_extras import image_utils

from .LeapModalController import LeapModal

from MakeHumanTools.BoneSet import *



NO_CHAR = ' '
FACE_CHAR = 'Q'
HEAD_CHAR = 'W'
EYES_CHAR = 'E'
RHAND_CHAR = 'A'
TORSO_CHAR = 'S'
LHAND_CHAR = 'D'
RFOOT_CHAR = 'Y'
PELVIS_CHAR = 'X'
LFOOT_CHAR = 'C'


class MyDrawer:
    
    FONT_SIZE = 24
    FONT_RGBA = (0.8, 0.1, 0.2, 0.7)

    
    def __init__(self):

        
        # Keys to overlap to the icons
        self.shortcut_keys = [
            NO_CHAR, HEAD_CHAR, EYES_CHAR,
            RHAND_CHAR, TORSO_CHAR, LHAND_CHAR,
            RFOOT_CHAR, PELVIS_CHAR, LFOOT_CHAR
        ]
        

        # cache the names of already loaded images
        self.loaded_images_files = [img.name for img in bpy.data.images]

        
        # Used for loading relative to the .blend file
        self.scene_dir = os.path.dirname(bpy.data.filepath)
        
        # Images for a 3x3 grid
        image_filenames = [
                           [ "empty-icon.png", "head-icon.png", "eye-icon.png" ],
                           [ "rhand-icon.png", "torso-icon.png", "lhand-icon.png" ],
                           [ "rfoot-icon.png", "belly-icon.png", "lfoot-icon.png" ]
                           ]

        # @see http://blenderartists.org/forum/archive/index.php/t-239773.html

        # Use these lines for loading from the blendfile
        #image = bpy.data.images["hand-icon.png"]
        # @see http://blenderscripting.blogspot.de/2012/08/adjusting-image-pixels-internally-in.html
        
        #bpy_extras.image_utils.load_image(imagepath, dirname='', place_holder=False, recursive=False, ncase_cmp=True, convert_callback=None, verbose=False, relpath=None)
        #image = image_utils.load_image(imagepath="images/lfoot-icon.png", dirname=scene_dir)

        images = []
        for names_line in image_filenames:
            images_line = []
            for image_file in names_line:
                image = self.loadImageEventually(image_file=image_file)
                #if(not image_file in loaded_images_files):
                    #print("Loading icon from '" + image_file + "'")
                    #image = image_utils.load_image(imagepath=image_file, dirname=scene_dir+"/images/")
                #else:
                    #print("Icon '" + image_file + "' already loaded. Skipping...")
                    #image = bpy.data.images[image_file]
            
                images_line.append(image)
                    
            images.append(images_line)
        

        # Convert them into GL Buffers
        self.buffers = []
        for images_line in images:
            buffers_line = []
            for image in images_line:
                print("Converting image '" + image.name + "'")
                floats = image.pixels
                buf = bgl.Buffer(bgl.GL_FLOAT, len(floats), floats)
                buffers_line.append(buf)
            self.buffers.append(buffers_line)

                
        #
        # Load mask icon
        image = self.loadImageEventually(image_file="highlight-icon.png")
        self.highlight_buf = bgl.Buffer(bgl.GL_FLOAT, len(image.pixels), image.pixels)
    
        #
        # Load finger indication images
        image = self.loadImageEventually(image_file="1-finger-icon-red.png")
        self.one_finger_buf = bgl.Buffer(bgl.GL_FLOAT, len(image.pixels), image.pixels)
                
        image = self.loadImageEventually(image_file="5-spreadfingers-icon-red.png")
        self.five_fingers_buf = bgl.Buffer(bgl.GL_FLOAT, len(image.pixels), image.pixels)
    
        image = self.loadImageEventually(image_file="translate-arrows-icon.png")
        self.translate_arrows_buf = bgl.Buffer(bgl.GL_FLOAT, len(image.pixels), image.pixels)
    
        image = self.loadImageEventually(image_file="turnaround-arrows-icon.png")
        self.rotate_arrows_buf = bgl.Buffer(bgl.GL_FLOAT, len(image.pixels), image.pixels)

        pass
    

    def loadImageEventually(self, image_file):
        """Load the image from the 'images' directory relative to the scene.
            If the image is already loaded just return it.
        """
        
        if(not image_file in self.loaded_images_files):
            print("Loading image from '" + image_file + "'")
            image = image_utils.load_image(imagepath=image_file, dirname=self.scene_dir+"/images/")
        else:
            print("Image '" + image_file + "' already loaded. Skipping...")
            image = bpy.data.images[image_file]
        return image


    def drawIcons(self):
        global s_registration_active_space

        #print("Callback drawIcons")

        context = bpy.context

        #print("Drawing Icons in active space "+str(context.area.spaces.active.as_pointer()))
        if(s_registration_active_space != None):
            if(not (s_registration_active_space.as_pointer() == context.area.spaces.active.as_pointer()) ):
                #print("Skipping...")
                return
        
        #print("Drawing icons on context " + str(context) + "\tarea is " + str(context.area) + "(" + context.area.type +")")
        
        #glDrawPixels(width, height, format, type, pixels)
        #Write a block of pixels to the frame buffer
        #
        #height (width,) – Specify the dimensions of the pixel rectangle to be written into the frame buffer.
        #format (Enumerated constant) – Specifies the format of the pixel data.
        #type (Enumerated constant) – Specifies the data type for pixels.
        #pixels (bgl.Buffer object) – Specifies a pointer to the pixel data.
        
        bgl.glPushClientAttrib(bgl.GL_CURRENT_BIT|bgl.GL_ENABLE_BIT)

        
        # transparence
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
    
        ICON_SIZE = 64
        GRID_SIZE = 3
        BORDER_SIZE = 5
        
        blf.size(0, self.FONT_SIZE, 72)
        #bgl.glColor4f(*self.FONT_RGBA)
        blf.blur(0, 1)
        
        #bgl.glScalef(0.5,0.5,0.5)

        # Cycle to draw all the cells
        cell_num = 0
        pos_y = context.region.height - ICON_SIZE - BORDER_SIZE
        for buffers_line in self.buffers:
            #pos_x = (context.region.width - (ICON_SIZE * GRID_SIZE) - (BORDER_SIZE * (GRID_SIZE-1)) ) / 2
            pos_x = context.region.width - ((ICON_SIZE + BORDER_SIZE) * GRID_SIZE)
            
            for buf in buffers_line:
                #print("Drawing icon for pos "+ str(cell_num))
                bgl.glRasterPos2f(pos_x, pos_y)
                bgl.glDrawPixels(ICON_SIZE, ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, buf)

                # Print the char
                blf.position(0, pos_x, pos_y, 0)
                #bgl.glPushClientAttrib(bgl.GL_CLIENT_ALL_ATTRIB_BITS) #CURRENT_BIT|bgl.GL_ENABLE_BIT)
                bgl.glPushAttrib(bgl.GL_CLIENT_ALL_ATTRIB_BITS)
                blf.size(0, self.FONT_SIZE, 72)
                #blf.blur(0, 10)
                #blf.shadow(0, 3, 0.5, 0.5, 0.5, 0.2)
                #blf.shadow_offset(0, int(self.FONT_SIZE/10), int(self.FONT_SIZE/10))
                bgl.glColor4f(*self.FONT_RGBA)
                blf.draw(0, self.shortcut_keys[cell_num])
                bgl.glPopAttrib()
                #bgl.glPopClientAttrib()
            
                pos_x += ICON_SIZE + BORDER_SIZE
                cell_num += 1
            
            pos_y -= ICON_SIZE + BORDER_SIZE

    
        bgl.glPopClientAttrib()

        pass

            
    # This is invoked as callback by the LeapModal during its draw operation.
    def draw(self, leap_modal, context):
        self.draw_highlight(leap_modal, context)
    

    def draw_highlight(self, leap_modal, context):
        #print("Callback draw")

        if(s_registration_active_space != None):
            if(not (s_registration_active_space.as_pointer() == context.area.spaces.active.as_pointer()) ):
                #print("Skipping...")
                return

        
        #glDrawPixels(width, height, format, type, pixels)
        #Write a block of pixels to the frame buffer
        #
        #height (width,) – Specify the dimensions of the pixel rectangle to be written into the frame buffer.
        #format (Enumerated constant) – Specifies the format of the pixel data.
        #type (Enumerated constant) – Specifies the data type for pixels.
        #pixels (bgl.Buffer object) – Specifies a pointer to the pixel data.
        
        # transparence
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        
        ICON_SIZE = 64
        GRID_SIZE = 3
        BORDER_SIZE = 5
        
        # The number of the cell to highlight has been passed (as string) in the userData from the Keymaps
        if(leap_modal.userData == ""):  # in case we didn't call this, just jump out
            #print("No Userdata, skipping")
            return
        
        highlight_cell_num = int(leap_modal.userData)
                
        
        # Cycle to draw all the cells
        cell_num = 0
        pos_y = context.region.height - ICON_SIZE - BORDER_SIZE
        for buffers_line in self.buffers:
            #pos_x = (context.region.width - (ICON_SIZE * GRID_SIZE) - (BORDER_SIZE * (GRID_SIZE-1)) ) / 2
            pos_x = context.region.width - ((ICON_SIZE + BORDER_SIZE) * GRID_SIZE)
            
            for buf in buffers_line:
                #print("Drawing icon for pos "+ str(cell_num))
                bgl.glRasterPos2f(pos_x, pos_y)
                #bgl.glDrawPixels(ICON_SIZE, ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, buf)
                
                # eventually, draw the highlight contour for the selected operation
                if(cell_num == highlight_cell_num):
                    bgl.glDrawPixels(ICON_SIZE, ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, self.highlight_buf)
                
                cell_num += 1
                pos_x += ICON_SIZE + BORDER_SIZE
            
            pos_y -= ICON_SIZE + BORDER_SIZE

        #
        # Draw the usage hint icons
        #pos_x = (context.region.width - ICON_SIZE ) / 2
        pos_x = context.region.width - ((ICON_SIZE + BORDER_SIZE) * (GRID_SIZE-1)) #- (ICON_SIZE/2)
        pos_y = context.region.height - (ICON_SIZE + BORDER_SIZE) * (GRID_SIZE+2) #- (BORDER_SIZE*2)
        bgl.glRasterPos2f(pos_x, pos_y)
        
        if(leap_modal.translationUseFinger or leap_modal.rotationUseFinger or leap_modal.isElbowSwivelRotating):
            bgl.glDrawPixels(ICON_SIZE, ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, self.one_finger_buf)
        else:
            bgl.glDrawPixels(ICON_SIZE, ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, self.five_fingers_buf)
    
        if(leap_modal.isTranslating):
            bgl.glDrawPixels(ICON_SIZE, ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, self.translate_arrows_buf)

        if(leap_modal.isRotating or leap_modal.isElbowSwivelRotating):
            bgl.glDrawPixels(ICON_SIZE, ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, self.rotate_arrows_buf)

        pass





class MyModalListener:

    def controllersUpdated(self, leap_modal, context):
        if(leap_modal.isTranslating):
            # retrieve the object that is translated
            obj = leap_modal.obj_translator.target_object
            # if it is one of our "sensible" posebones, limit its range of motion
            # if(obj.name == "Shoulders"):
            #     loc = obj.location
            #     if(loc.x > 1.5): loc.x = 1.5
            #     if(loc.x < -1.5): loc.x = -1.5
            #     if(loc.y > 1.5): loc.y = 1.5
            #     if(loc.y < -1.5): loc.y = -1.5
            #     if(loc.z > 0.5): loc.z = 0.5
            #     if(loc.z < -0.5): loc.z = -0.5
            # if(obj.name == "Root"):
            #     loc = obj.location
            #     if(loc.x > 1.5): loc.x = 1.5
            #     if(loc.x < -1.5): loc.x = -1.5
            #     if(loc.y > 1.5): loc.y = 1.5
            #     if(loc.y < -1.5): loc.y = -1.5
            #     if(loc.z > 0.5): loc.z = 0.5
            #     if(loc.z < -0.5): loc.z = -0.5
                
        pass





s_my_drawer = MyDrawer()
s_my_modal_listener = MyModalListener()

s_draw_handler = None

# We want to draw the information only in the area/space/region where the function has been activated.
# So, in this variable we will store the reference to the space (bpy.context.area.spaces.active) that was active when the user activated the controls.
s_registration_active_space = None

print("in BodySelectionKeymap main __init__")
#print("s_draw_handle is " + str(s_draw_handle))

# store keymap items here to delete them on unregistration
body_selection_keymap_items = []


# I've got here the possible values for the 'name' parameter for the KeyMap
# https://svn.blender.org/svnroot/bf-extensions/contrib/py/scripts/addons/presets/keyconfig/blender_2012_experimental.py
#EDIT_MODES = ['Object Mode', 'Pose']
EDIT_MODES = ['Pose']


def register():
    # Bloody Hell!!! I HATE Python!!!
    # http://stackoverflow.com/questions/10851906/python-3-unboundlocalerror-local-variable-referenced-before-assignment
    global s_draw_handler
    global s_registration_active_space
    
    print("Registering keymaps for body selection...", end="")
    
    s_registration_active_space = bpy.context.area.spaces.active
    print("--> Body control activated in space "+str(s_registration_active_space.as_pointer()))

    
    #print("s_my_drawer is " + str(s_my_drawer) + str(s_my_modal_listener))
    #print("s_draw_handle is " + str(s_draw_handler))

    LeapModal.drawCallbacks.append(s_my_drawer)
    LeapModal.modalCallbacks.append(s_my_modal_listener)
    
    #ctx = bpy.context
    #s_draw_handle = bpy.types.SpaceView3D.draw_handler_add(s_my_drawer.drawIcons, (s_my_drawer,), 'WINDOW', 'POST_PIXEL')
    #print("s_draw_handle is " + str(s_draw_handler))
    s_draw_handler = bpy.types.SpaceView3D.draw_handler_add(s_my_drawer.drawIcons, (), 'WINDOW', 'POST_PIXEL')
    #print("s_draw_handle is " + str(s_draw_handler))


    # handle the keymap
    wm = bpy.context.window_manager
    
    for edit_mode in EDIT_MODES:
        km = wm.keyconfigs.addon.keymaps.new(name=edit_mode, space_type='EMPTY')
        #km = wm.keyconfigs.addon.keymaps.new(name=edit_mode, space_type='VIEW_3D')
        
        # FACE
        # Nothing for now. Later, we will activate FaceShift
        
        # HEAD
        kmi = km.keymap_items.new(LeapModal.bl_idname, HEAD_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isRotating = True
        #kmi.properties.translationUseFinger = True
        kmi.properties.targetPoseBoneName = MH_CONTROLLER_NECK
        kmi.properties.userData = "1" # icon position to highlight
        body_selection_keymap_items.append(kmi)
        
        # EYES
        kmi = km.keymap_items.new(LeapModal.bl_idname, EYES_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isTranslating = True
        kmi.properties.translationUseFinger = True
        kmi.properties.targetPoseBoneName = MH_CONTROLLER_GAZE
        kmi.properties.userData = "2" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        # RIGHT HAND
        kmi = km.keymap_items.new(LeapModal.bl_idname, RHAND_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isTranslating = True
        kmi.properties.isRotating = True
        kmi.properties.translationUseFinger = False
        kmi.properties.targetPoseBoneName = MH_HAND_CONTROLLER_R
        kmi.properties.userData = "3" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        # RIGHT ELBOW
        kmi = km.keymap_items.new(LeapModal.bl_idname, RHAND_CHAR, 'PRESS', ctrl=False, shift=True)
        #kmi.properties.isTranslating = True
        #kmi.properties.isRotating = False
        #kmi.properties.translationUseFinger = True
        kmi.properties.isElbowSwivelRotating = True
        kmi.properties.targetPoseBoneName = MH_ELBOW_CONTROLLER_R
        kmi.properties.userData = "3" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        
        # LEFT HAND
        kmi = km.keymap_items.new(LeapModal.bl_idname, LHAND_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isTranslating = True
        kmi.properties.isRotating = True
        kmi.properties.translationUseFinger = False
        kmi.properties.targetPoseBoneName = MH_HAND_CONTROLLER_L
        kmi.properties.userData = "5" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        # LEFT ELBOW
        kmi = km.keymap_items.new(LeapModal.bl_idname, LHAND_CHAR, 'PRESS', ctrl=False, shift=True)
        #kmi.properties.isTranslating = True
        #kmi.properties.isRotating = False
        #kmi.properties.translationUseFinger = True
        kmi.properties.isElbowSwivelRotating = True
        kmi.properties.targetPoseBoneName = MH_ELBOW_CONTROLLER_L
        kmi.properties.userData = "5" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        # TORSO
        kmi = km.keymap_items.new(LeapModal.bl_idname, TORSO_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isTranslating = True
        kmi.properties.isRotating = True
        kmi.properties.translationUseFinger = False
        #kmi.properties.targetPoseBoneName = "Spine3"   # this was for FK spine
        kmi.properties.targetPoseBoneName = MH_UPCHEST_CONTROLLER
        kmi.properties.userData = "4" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        # BELLY
        kmi = km.keymap_items.new(LeapModal.bl_idname, PELVIS_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isTranslating = True
        kmi.properties.isRotating = True
        kmi.properties.translationUseFinger = False
        kmi.properties.targetPoseBoneName = MH_ROOT_CONTROLLER
        kmi.properties.userData = "7" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        # RIGHT FOOT
        kmi = km.keymap_items.new(LeapModal.bl_idname, RFOOT_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isTranslating = True
        kmi.properties.isRotating = True
        kmi.properties.translationUseFinger = False
        kmi.properties.targetPoseBoneName = MH_LEG_CONTROLLER_R
        kmi.properties.userData = "6" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        # RIGHT KNEE
        kmi = km.keymap_items.new(LeapModal.bl_idname, RFOOT_CHAR, 'PRESS', ctrl=False, shift=True)
        kmi.properties.isTranslating = True
        kmi.properties.isRotating = False
        kmi.properties.translationUseFinger = True
        kmi.properties.targetPoseBoneName = MH_KNEE_CONTROLLER_R
        kmi.properties.userData = "6" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        # LEFT FOOT
        kmi = km.keymap_items.new(LeapModal.bl_idname, LFOOT_CHAR, 'PRESS', ctrl=False, shift=False)
        kmi.properties.isTranslating = True
        kmi.properties.isRotating = True
        kmi.properties.translationUseFinger = False
        kmi.properties.targetPoseBoneName = MH_LEG_CONTROLLER_L
        kmi.properties.userData = "8" # icon position to highlight
        body_selection_keymap_items.append(kmi)

        # LEFT KNEE
        kmi = km.keymap_items.new(LeapModal.bl_idname, LFOOT_CHAR, 'PRESS', ctrl=False, shift=True)
        kmi.properties.isTranslating = True
        kmi.properties.isRotating = False
        kmi.properties.translationUseFinger = True
        kmi.properties.targetPoseBoneName = MH_KNEE_CONTROLLER_L
        kmi.properties.userData = "8" # icon position to highlight
        body_selection_keymap_items.append(kmi)
    
    print("ok")


def unregister():
    global s_draw_handler


    print("Removing drawer listener " + str(s_my_drawer))
    if(s_my_drawer in LeapModal.drawCallbacks):
        LeapModal.drawCallbacks.remove(s_my_drawer)
    print("Removing modal listener " + str(s_my_modal_listener))
    if(s_my_modal_listener in LeapModal.modalCallbacks):
        LeapModal.modalCallbacks.remove(s_my_modal_listener)

    print("Removing draw handle " + str(s_draw_handler))
    if(s_draw_handler != None):
        bpy.types.SpaceView3D.draw_handler_remove(s_draw_handler, 'WINDOW')
        s_draw_handler = None


    print("Unregistering keymaps for body selection...", end="")
    # handle the keymap
    wm = bpy.context.window_manager
    for edit_mode in EDIT_MODES:
        km = wm.keyconfigs.addon.keymaps[edit_mode]
        for kmi in body_selection_keymap_items:
            if(kmi in km.keymap_items.values()):
                print("\t\tRemove from Addon/Pose Item '" + kmi.name +"'\t'" + kmi.idname + "'")
                km.keymap_items.remove(kmi)

    body_selection_keymap_items.clear()

    print("ok")


