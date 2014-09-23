
from . import HeadCameraControl

import bpy


def register():
    print("Registering HeadCameraControl...", end="")
    HeadCameraControl.register()

    print("ok")


def unregister():
    print("Unregistering HeadCameraControl...", end="")
    HeadCameraControl.unregister()

    print("ok")


if __name__ == "__main__":
    register()
    