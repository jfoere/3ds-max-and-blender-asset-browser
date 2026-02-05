bl_info = {
    "name": "Model Library",
    "author": "Your Name",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Model Library",
    "description": "Browse and add procedural models from a searchable library with preview thumbnails",
    "category": "Object",
}

from . import models
from . import operators
from . import ui


def register():
    operators.register()
    ui.register()


def unregister():
    ui.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()
