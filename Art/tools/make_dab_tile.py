"""make_dab_tile.py - the painted-dab normal tile T_GT_DabTile_N for M_GT_Painterly (Look stage L6, docs/LOOK_PLAN.md L6,
docs/VEHICLE_BUILD_SYSTEM.md section 57). Run by bash Art/make_dab_tile.sh (Blender 5.1, background, --factory-startup).

The tile is tooling, not a model: a flat 2 x 2 m plane (one quad, its UV 0..1 over the whole texture) goes through the
GT Paint pipeline exactly as the owner's props do - Apply Style, then Bake with the preset Art/Blender/gt_paint_preset.json
untouched, so the dabs are the owner's OW Painterly Normal Baker's at the preset's numbers (dab 55 cm, aspect 2, normal
jitter 8, coverage 2, the detail pass, seed 7). Only the _N is kept: it is copied to Art/Textures/Painted/T_GT_DabTile_N.png.
Nothing in Art/Blender is changed; the bake's own files land in the folder given as the first argument (a scratch folder).

Then the seam, the brief's measure of whether the bake tiles: the mean absolute difference between the texels either side
of the wrapped edge (column 0 against the last column, row 0 against the last row), against the mean absolute difference
between neighbouring texels inside. A tile that wraps cleanly reads a ratio near 1; the dabs a plane's edge cuts read
higher. Lines start GTDABTILE.
"""
import os
import shutil
import sys
import time

import bpy
import bmesh
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
BLENDER_DIR = os.path.join(ART, "Blender")
PRESET = os.path.join(BLENDER_DIR, "gt_paint_preset.json")
DEST_DIR = os.path.join(ART, "Textures", "Painted")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
WORK = os.path.abspath(ARGS[0]) if ARGS else os.path.join(os.environ.get("TEMP", "."), "gt_dab_tile")
ASSET = "DabTile"
SIZE_M = 2.0


def say(msg):
    print("GTDABTILE " + msg)
    sys.stdout.flush()


def make_plane():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    me = bpy.data.meshes.new(ASSET)
    bm = bmesh.new()
    h = SIZE_M * 0.5
    verts = [bm.verts.new(co) for co in ((-h, -h, 0.0), (h, -h, 0.0), (h, h, 0.0), (-h, h, 0.0))]
    face = bm.faces.new(verts)
    uv = bm.loops.layers.uv.new("UVMap")
    for loop, co in zip(face.loops, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))):
        loop[uv].uv = co
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(ASSET, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def seam(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[:, :, :3]
    inside_x = float(np.mean(np.abs(px[:, 1:] - px[:, :-1])))
    inside_y = float(np.mean(np.abs(px[1:, :] - px[:-1, :])))
    seam_x = float(np.mean(np.abs(px[:, 0] - px[:, -1])))
    seam_y = float(np.mean(np.abs(px[0, :] - px[-1, :])))
    flat = float(np.mean(np.all(np.abs(px - np.array([0.5, 0.5, 1.0], dtype=np.float32)) < 0.02, axis=2)))
    return w, h, inside_x, inside_y, seam_x, seam_y, flat


def main():
    sys.path.insert(0, BLENDER_DIR)
    import gt_paint
    gt_paint.register()
    from gt_paint import core
    preset, where = core.load_preset(PRESET)
    say("blender %s, preset %s, normal %s" % (bpy.app.version_string, where,
        ", ".join("%s %s" % (k, v) for k, v in preset.get("normal", {}).items() if not k.startswith("_"))))
    os.makedirs(WORK, exist_ok=True)
    ob = make_plane()
    s = bpy.context.scene.gt_paint
    s.asset_name = ASSET
    s.export_dir = WORK
    s.preset_path = PRESET
    s.bake_size = 'PRESET'
    for o in bpy.data.objects:   # the plane is the only object left
        if o is not None and o is not ob:
            o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    t0 = time.perf_counter()
    bpy.ops.gt_paint.apply_style()
    bpy.ops.gt_paint.bake()
    t1 = time.perf_counter()
    src = os.path.join(WORK, ASSET, "T_GT_%s_N.png" % ASSET)
    if not os.path.isfile(src):
        say("FAIL no _N was baked (%s); is the OW Painterly Normal Baker installed?" % src)
        raise SystemExit(1)
    os.makedirs(DEST_DIR, exist_ok=True)
    dst = os.path.join(DEST_DIR, "T_GT_%s_N.png" % ASSET)
    shutil.copyfile(src, dst)
    say("plane %.1f x %.1f m baked in %.0f s -> %s (%d bytes)" % (SIZE_M, SIZE_M, t1 - t0, dst, os.path.getsize(dst)))
    w, h, ix, iy, sx, sy, flat = seam(dst)
    say("seam %d x %d: across the wrapped vertical edge %.4f against %.4f between neighbours inside (ratio %.2f); "
        "across the wrapped horizontal edge %.4f against %.4f (ratio %.2f); flat texels %.1f %%"
        % (w, h, sx, ix, sx / max(ix, 1e-6), sy, iy, sy / max(iy, 1e-6), flat * 100.0))


main()
