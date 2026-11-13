"""
Run inside Blender: Scripting workspace > Text > Open this file > Run Script (Alt+P).

Creates Image Empties from the crops made by split_blueprint.py. Each is sized
so 1 pixel = the same real-world distance, and positioned so the ground lines
and car centrelines coincide. Car nose points to -Y.
    Numpad 1 front, Ctrl+Numpad 1 rear, Numpad 3 left side, Ctrl+Numpad 3 right side, Numpad 7 top.

Set JSON_PATH to the blender_sizes.json written by split_blueprint.py.
Empties go in a collection named after the car; re-running replaces them.
"""
import json
import math
from pathlib import Path

import bpy

JSON_PATH = r"C:\Users\mille\OneDrive\Desktop\Reference Images\31450-mid_views\blender_sizes.json"

data = json.loads(Path(JSON_PATH).read_text())
coll_name = f"Blueprint_{data['name']}"

coll = bpy.data.collections.get(coll_name)
if coll is None:
    coll = bpy.data.collections.new(coll_name)
    bpy.context.scene.collection.children.link(coll)
for obj in list(coll.objects):                           # re-run friendly
    bpy.data.objects.remove(obj)

for name, info in data["views"].items():
    img = bpy.data.images.load(info["file"], check_existing=True)
    empty = bpy.data.objects.new(f"BP_{data['name']}_{name}", None)
    empty.empty_display_type = "IMAGE"
    empty.data = img
    empty.empty_display_size = info["size_m"]
    empty.empty_image_offset = (-0.5, -0.5)              # centre image on the empty
    empty.rotation_euler = [math.radians(a) for a in info["rotation_deg"]]
    empty.location = info["location"]
    empty.show_empty_image_perspective = False           # only show in ortho views
    empty.empty_image_depth = "BACK"                     # draw behind your mesh
    empty.use_empty_image_alpha = True
    empty.color[3] = 0.7
    empty.hide_select = True                             # don't grab it by accident
    coll.objects.link(empty)
    print(f"{name}: Size {info['size_m']} m at {info['location']}")
