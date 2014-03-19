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


bl_info = {
    "name": "Make Human Tools",
    "description": "Collection of panels and clases to help management of MakeHuman characters.",
    "author": "Fabrizio Nunnari",
    "version": (1, 0),
    "blender": (2, 69, 0),
    "location": "View3D > Toolbar",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "System"}


from . import MHTools


def register():

    print("Registering Make Human Tools...", end="")
    #bpy.utils.register_class(LeapModal)
    MHTools.register()

    print("ok")


def unregister():

    print("Unregistering Make Human Tools...", end="")
    MHTools.unregister()
    #bpy.utils.unregister_class(LeapModal)

    print("ok")


if __name__ == "__main__":
    register()
