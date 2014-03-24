import bpy
import bgl

import os
from bpy_extras import image_utils


ICON_SIZE = 64


# cache the names of already loaded images
loaded_images_files = [img.name for img in bpy.data.images]

        
# Used for loading relative to the .blend file
scene_dir = os.path.dirname(bpy.data.filepath)


# Images for a 3x3 grid
image_filenames = [
                   "empty-icon.png", "head-icon.png", "eye-icon.png",
                   "rhand-icon.png", "torso-icon.png", "lhand-icon.png",
                   "rfoot-icon.png", "belly-icon.png", "lfoot-icon.png",
                   "highlight-icon.png","1-finger-icon-red.png",
                   "5-spreadfingers-icon.png", "5-spreadfingers-icon-red.png", "5-spreadfingers-icon-green.png",
                   "translate-arrows-icon.png","turnaround-arrows-icon.png"
                   ]

def loadImageEventually(image_file):
    """Load the image from the 'images' directory relative to the scene.
        If the image is already loaded just return it.
    """
    
    if(not image_file in loaded_images_files):
        print("Loading image from '" + image_file + "'")
        image = image_utils.load_image(imagepath=image_file, dirname=scene_dir+"/images/")
    else:
        print("Image '" + image_file + "' already loaded. Skipping...")
        image = bpy.data.images[image_file]
    return image


def drawIcon(image_file, pos_x, pos_y):
    bgl.glPushClientAttrib(bgl.GL_CURRENT_BIT|bgl.GL_ENABLE_BIT)

    # transparence
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

    bgl.glRasterPos2f(pos_x, pos_y)

    buf = buffers[image_file]
    bgl.glDrawPixels(ICON_SIZE, ICON_SIZE, bgl.GL_RGBA, bgl.GL_FLOAT, buf)

    bgl.glPopClientAttrib()



print("Loading Icons...")

# A dictionary file -> image
images = {} 
for image_file in image_filenames:
    image = loadImageEventually(image_file=image_file)            
    images[image_file] = image
                    


# Convert them into GL Buffers (needed to draw the image)
print("Converting Icons...")

# A dictionary file -> GL Buffer
buffers = {}
for f, image in images.items():
    print("Converting image '" + image.name + "'")
    floats = image.pixels
    buf = bgl.Buffer(bgl.GL_FLOAT, len(floats), floats)
    buffers[f] = buf

print("Icons loaded.")

