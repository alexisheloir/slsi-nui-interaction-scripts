
from . import BlenderLogger

import bpy


def register():
    print("Registering BlenderLogger...", end="")
    BlenderLogger.register()

    print("ok")


def unregister():
    print("Unregistering BlenderLogger...", end="")
    BlenderLogger.unregister()

    print("ok")


if __name__ == "__main__":
    register()
    