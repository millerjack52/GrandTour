"""export_rangerover.py - Unreal-ready FBX from the hand-modelled Range Rover blockout.

Headless only; it never saves the .blend. Double-click Art\\export_rangerover.bat, or run:
    "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" -b Art\\rangerover.blend
        --python Art\\Blender\\export_rangerover.py -- Art\\Export

Blender file conventions (docs/VEHICLE_BUILD_SYSTEM.md s10): metres, ground z = 0, front -Y,
left +X. Export space: centimetres, front +X (EXPORT_YAW_DEG), Z up, same origin. Unreal's FBX
import keeps X and Z and negates Y, so the car faces +X in Unreal and its left side is -Y.

Outputs in <out>/:
    SK_RangeRover.fbx        skeletal mesh: Root + Wheel_FL/FR/RL/RR bones, every part skinned
                             rigidly to one bone (body -> Root, each wheel -> its bone)
    Static/SM_RR_<Part>.fbx  one static mesh per Blender object, mirrored pairs split into
                             _L/_R, origin = vehicle origin; SM_RR_Wheel has its origin at the hub
    manifest.json            hubs, wheel radius/width, wheelbase, bones, parts, warnings

Rules: mesh objects outside the Reference/Jig collections are exported; objects with fewer than
MIN_FACES faces are skipped (stray quads, empty meshes); an object whose name starts with
"wheel" is a wheel and gets its corner from its position. Materials are placeholder slots
chosen by name (M_Wheel, M_Interior, M_Trim, M_Body) so Unreal creates the slots.
"""
import bpy
import bmesh
import json
import math
import os
import re
import sys
from mathutils import Matrix, Vector

EXPORT_YAW_DEG = 90.0        # -Y front (Blender) -> +X front (Unreal)
CM = 100.0                   # metres -> centimetres; the FBX is written in cm with unit scale 1
MIN_FACES = 4
MERGE_DIST = 0.001           # metres
REF_COLLECTIONS = {"Reference", "Jig"}
WHEEL_PREFIX = "wheel"
PAIR_GAP = 0.02              # a part is a mirrored pair if no vertex is within this of x = 0
SK_NAME = "SK_RangeRover"
SM_PREFIX = "SM_RR_"
BONE_ROOT = "Root"
BONE_WHEEL = {"FL": "Wheel_FL", "FR": "Wheel_FR", "RL": "Wheel_RL", "RR": "Wheel_RR"}
MATERIAL_RULES = [("interior", "M_Interior"), ("pillar", "M_Trim"), ("bumper", "M_Trim"),
                  ("", "M_Body")]          # wheels (name starts with WHEEL_PREFIX) get M_Wheel
FBX_COMMON = dict(axis_forward='-Z', axis_up='Y', global_scale=1.0, apply_unit_scale=True,
                  apply_scale_options='FBX_SCALE_NONE', bake_space_transform=False,
                  use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=False,
                  add_leaf_bones=False, use_armature_deform_only=True, bake_anim=False,
                  path_mode='AUTO', embed_textures=False, use_custom_props=False,
                  use_selection=True)

LOG = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def out_dir():
    if "--" in sys.argv:
        rest = sys.argv[sys.argv.index("--") + 1:]
        if rest:
            return os.path.abspath(rest[0])
    return os.path.join(os.path.dirname(bpy.data.filepath), "Export")


def clean_name(n):
    n = re.sub(r"\.\d{3}$", "", n)
    n = re.sub(r"[^A-Za-z0-9]+", "", n)
    return (n[:1].upper() + n[1:]) if n else "Part"


def material_for(name):
    low = name.lower()
    if low.startswith(WHEEL_PREFIX):
        return "M_Wheel"
    for key, mat in MATERIAL_RULES:
        if key in low:
            return mat
    return "M_Body"


def get_material(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    return m


def deselect_all():
    for o in bpy.data.objects:
        o.select_set(False)


def set_mode(ob, mode):
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.mode_set(mode=mode)
    except RuntimeError:
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
            bpy.ops.object.mode_set(mode=mode)


def r1(v):
    return [round(float(x), 1) for x in v]


def r3(v):
    return [round(float(x), 3) for x in v]


def main():
    if not bpy.app.background:
        raise SystemExit("Run this headless via Art/export_rangerover.bat. It builds throwaway "
                         "export copies and must not run inside your working session.")
    sc = bpy.context.scene
    # The export copy works in centimetres. With scale_length 0.01 the FBX exporter's unit
    # factor is 1.0, so the cm data goes into the file untouched (Unreal reads it as cm).
    # Leaving the scene at metres made the exporter scale everything by 100 again.
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 0.01
    sc.unit_settings.length_unit = 'CENTIMETERS'
    out = out_dir()
    os.makedirs(os.path.join(out, "Static"), exist_ok=True)
    warnings = []
    dg = bpy.context.evaluated_depsgraph_get()
    yaw = Matrix.Rotation(math.radians(EXPORT_YAW_DEG), 4, 'Z')
    to_export = Matrix.Scale(CM, 4) @ yaw      # metres/-Y front -> cm/+X front

    # ---- 1. pick sources -------------------------------------------------------------------
    sources = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        if {c.name for c in ob.users_collection} & REF_COLLECTIONS:
            continue
        if len(ob.data.polygons) < MIN_FACES:
            warnings.append(f"skipped {ob.name}: only {len(ob.data.polygons)} faces")
            continue
        if re.search(r"\.\d{3}$", ob.name):
            warnings.append(f"{ob.name}: numbered name, rename it in the .blend")
        try:
            if ob.hide_get():
                warnings.append(f"{ob.name}: hidden in viewport but exported anyway")
        except Exception:
            pass
        sources.append(ob)
    if not sources:
        raise SystemExit("no mesh objects to export")

    # ---- 2. baked copies in export space ---------------------------------------------------
    exp_col = bpy.data.collections.new("EXPORT")
    sc.collection.children.link(exp_col)
    parts = []
    used_names = {}
    for ob in sources:
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        me.transform(ob.matrix_world)                    # metres, Blender space
        bm = bmesh.new()
        bm.from_mesh(me)
        n_before = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DIST)
        merged = n_before - len(bm.verts)
        internal = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        bm.to_mesh(me)
        bm.free()
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        zs = [v.co.z for v in me.vertices]
        bmin = Vector((min(xs), min(ys), min(zs)))
        bmax = Vector((max(xs), max(ys), max(zs)))
        is_wheel = ob.name.lower().startswith(WHEEL_PREFIX)
        paired = (not is_wheel) and min(abs(x) for x in xs) > PAIR_GAP and min(xs) < 0 < max(xs)
        me.transform(to_export)                          # cm, +X front, left +Y
        new = bpy.data.objects.new("EXP_" + ob.name, me)
        exp_col.objects.link(new)
        mat = get_material(material_for(ob.name))
        me.materials.append(mat)
        for p in me.polygons:
            p.material_index = 0
        name = clean_name(ob.name)
        if name in used_names:
            used_names[name] += 1
            name = f"{name}{used_names[name]}"
            warnings.append(f"{ob.name}: exported as {name} because another object cleans to "
                            f"the same name; give it its own name in the .blend")
        else:
            used_names[name] = 1
        parts.append(dict(src=ob.name, name=name, ob=new, me=me, is_wheel=is_wheel,
                          paired=paired, centre_m=(bmin + bmax) / 2, bmin_m=bmin, bmax_m=bmax,
                          material=mat.name, faces=len(me.polygons),
                          tris=sum(len(p.vertices) - 2 for p in me.polygons)))
        if merged:
            warnings.append(f"{ob.name}: merged {merged} doubled verts (within 1 mm) for export; "
                            f"do Merge by Distance in the .blend too")
        if internal:
            warnings.append(f"{ob.name}: {internal} edges shared by 3+ faces (internal faces)")

    # ---- 3. wheels: corners, hubs ----------------------------------------------------------
    wheels = [p for p in parts if p["is_wheel"]]
    body = [p for p in parts if not p["is_wheel"]]
    if len(wheels) != 4:
        warnings.append(f"expected 4 objects whose names start with 'wheel', found {len(wheels)}")
    for p in wheels:
        c = p["centre_m"]
        p["corner"] = ("F" if c.y < 0 else "R") + ("L" if c.x > 0 else "R")
        p["bone"] = BONE_WHEEL[p["corner"]]
        size = p["bmax_m"] - p["bmin_m"]
        p["radius_m"] = size.z / 2
        p["width_m"] = size.x
    corners = [p["corner"] for p in wheels]
    if len(set(corners)) != len(corners):
        warnings.append(f"wheel corners are ambiguous: {corners}")
    fronts = [p["centre_m"].y for p in wheels if p["corner"][0] == "F"]
    rears = [p["centre_m"].y for p in wheels if p["corner"][0] == "R"]
    wheelbase = track = axle_mid_y = None
    if fronts and rears:
        wheelbase = sum(rears) / len(rears) - sum(fronts) / len(fronts)
        axle_mid_y = (sum(rears) / len(rears) + sum(fronts) / len(fronts)) / 2
        track = 2 * sum(abs(p["centre_m"].x) for p in wheels) / len(wheels)
        if abs(axle_mid_y) > 0.01:
            where = "behind" if axle_mid_y < 0 else "ahead of"
            warnings.append(f"vehicle origin is {abs(axle_mid_y) * 100:.1f} cm {where} the axle "
                            f"midpoint; docs convention is origin at the axle midpoint. Move the "
                            f"model in the .blend if you want them to coincide (the FBX follows "
                            f"the file).")
    ground = min(p["bmin_m"].z for p in parts)
    if abs(ground) > 0.01:
        warnings.append(f"lowest point is at z = {ground:.3f} m, expected 0 (ground)")

    # ---- 4. static meshes (independent copies, no rig) --------------------------------------
    static_files = []

    def export_static(name, me):
        o = bpy.data.objects.new(name, me)
        exp_col.objects.link(o)
        deselect_all()
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        path = os.path.join(out, "Static", name + ".fbx")
        bpy.ops.export_scene.fbx(filepath=path, object_types={'MESH'}, **FBX_COMMON)
        static_files.append(os.path.relpath(path, out).replace("\\", "/"))

    for p in body:
        if p["paired"]:
            for side, sign in (("L", 1), ("R", -1)):      # export space: left = +Y
                me2 = p["me"].copy()
                bm = bmesh.new()
                bm.from_mesh(me2)
                kill = [v for v in bm.verts if v.co.y * sign < 0]
                bmesh.ops.delete(bm, geom=kill, context='VERTS')
                bm.to_mesh(me2)
                bm.free()
                export_static(f"{SM_PREFIX}{p['name']}_{side}", me2)
        else:
            export_static(f"{SM_PREFIX}{p['name']}", p["me"].copy())
    if wheels:
        w = sorted(wheels, key=lambda p: p["corner"])[0]
        me2 = w["me"].copy()
        me2.transform(Matrix.Translation(-(to_export @ w["centre_m"])))
        export_static(f"{SM_PREFIX}Wheel", me2)

    # ---- 5. rig + skeletal mesh ------------------------------------------------------------
    # Unreal (legacy FBX and Interchange) drops Blender's armature null only when it is named
    # "Armature", sits at the scene root and has a single child (the root bone). So: that name,
    # and the meshes are NOT parented to it; the Armature modifier alone carries the skinning.
    arm = bpy.data.armatures.new(SK_NAME + "_Rig")
    arm_ob = bpy.data.objects.new("Armature", arm)
    exp_col.objects.link(arm_ob)
    deselect_all()
    arm_ob.select_set(True)
    set_mode(arm_ob, 'EDIT')
    # Bones point along export +Y (the car's left) with zero roll: that is the orientation that
    # imports into Unreal as an identity bone rotation (measured: +Z gave roll 90, -Y gave yaw
    # 180). Chaos Vehicles use the root body's frame as the vehicle frame, so the root bone must
    # be identity or the centre of mass override and the forward axis come out wrong.
    root = arm.edit_bones.new(BONE_ROOT)
    root.head = (0.0, 0.0, 0.0)
    root.tail = (0.0, 30.0, 0.0)
    bone_pos = {BONE_ROOT: Vector((0.0, 0.0, 0.0))}
    for p in wheels:
        c = to_export @ p["centre_m"]
        b = arm.edit_bones.new(p["bone"])
        b.head = c
        b.tail = c + Vector((0.0, 15.0, 0.0))
        b.parent = root
        b.use_connect = False
        bone_pos[p["bone"]] = c
    set_mode(arm_ob, 'OBJECT')
    for p in parts:
        ob = p["ob"]
        bone = p.get("bone", BONE_ROOT)
        vg = ob.vertex_groups.new(name=bone)
        vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')
        mod = ob.modifiers.new("Armature", 'ARMATURE')
        mod.object = arm_ob
        p["bone"] = bone
    deselect_all()
    arm_ob.select_set(True)
    for p in parts:
        p["ob"].select_set(True)
    bpy.context.view_layer.objects.active = arm_ob
    sk_path = os.path.join(out, SK_NAME + ".fbx")
    bpy.ops.export_scene.fbx(filepath=sk_path, object_types={'ARMATURE', 'MESH'}, **FBX_COMMON)

    # ---- 6. manifest + report --------------------------------------------------------------
    def unreal(v):                      # export space -> Unreal: negate Y
        return [round(float(v.x), 1), round(-float(v.y), 1), round(float(v.z), 1)]

    all_min = Vector([min(p["bmin_m"][i] for p in parts) for i in range(3)])
    all_max = Vector([max(p["bmax_m"][i] for p in parts) for i in range(3)])
    manifest = {
        "source_blend": bpy.data.filepath,
        "blender": bpy.app.version_string,
        "export_yaw_deg": EXPORT_YAW_DEG,
        "units": "FBX in centimetres, unit scale 1; Blender file in metres",
        "axes": "export space: +X front, +Y left, +Z up; Unreal: +X front, -Y left, +Z up",
        "skeletal_mesh": os.path.basename(sk_path),
        "bones": {name: {"export_cm": r1(pos), "unreal_cm": unreal(pos),
                         "parent": None if name == BONE_ROOT else BONE_ROOT}
                  for name, pos in bone_pos.items()},
        "wheelbase_cm": None if wheelbase is None else round(wheelbase * CM, 1),
        "track_cm": None if track is None else round(track * CM, 1),
        "axle_midpoint_offset_cm": None if axle_mid_y is None else round(axle_mid_y * CM, 1),
        "wheel_radius_cm": (round(sum(p["radius_m"] for p in wheels) / len(wheels) * CM, 1)
                            if wheels else None),
        "wheel_width_cm": (round(sum(p["width_m"] for p in wheels) / len(wheels) * CM, 1)
                           if wheels else None),
        "overall_size_cm": r1((all_max - all_min) * CM),
        "parts": [{"source": p["src"], "name": p["name"], "bone": p["bone"], "material": p["material"],
                   "faces": p["faces"], "tris": p["tris"], "paired": p["paired"],
                   "centre_blender_m": r3(p["centre_m"])} for p in parts],
        "static_meshes": static_files,
        "warnings": warnings,
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)

    say(f"exported {sk_path}  ({len(parts)} parts, {sum(p['tris'] for p in parts)} tris)")
    say(f"exported {len(static_files)} static meshes to {os.path.join(out, 'Static')}")
    for name, pos in bone_pos.items():
        say(f"  bone {name:9} unreal cm {unreal(pos)}")
    if wheelbase is not None:
        say(f"  wheelbase {wheelbase * CM:.1f} cm, track {track * CM:.1f} cm, wheel radius "
            f"{manifest['wheel_radius_cm']} cm, width {manifest['wheel_width_cm']} cm")
    say(f"  overall size cm {manifest['overall_size_cm']}")
    if warnings:
        say("WARNINGS:")
        for w in warnings:
            say("  - " + w)
    say("EXPORT_OK")


main()
