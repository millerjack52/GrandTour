"""test_gt_paint.py - the GT Paint addon's headless test (docs/LOOK_PLAN.md L1, VEHICLE_BUILD_SYSTEM 55).

Run with `bash Art/blender_test.sh`: it copies Art/rangerover.blend to a temp folder and opens THE COPY in Blender
5.1 in the background with this script; nothing is ever saved, and the script refuses to run on the owner's file.
Three assets go through the panel's own operators (Apply Style, Bake, Export) exactly as a click would:
- TestCube: a 1 m cube, sharp edges, wearing an owner-style flat material (ochre), so its ID colour is the material's.
- TestBox: a 1.2 x 0.8 x 0.8 m box with a Bevel modifier (5 cm, 3 segments), no material: the palette by name.
- TestCar: every part of the blockout copy that export_rangerover.py would export (outside Reference/Jig, 4+ faces),
  joined into one bake, pivot at the Roof's origin (the vehicle origin).
Per asset it prints the bake time, the files and their sizes, the albedo's distinct tones (8-bit colours holding over
0.5 % of the baked texels) against the ceiling (the preset's tones x the asset's base colours), the mean albedo (sRGB
0-255) and the mask channels' means (0-1), all over the texels the bake covered (the albedo's alpha). Then (section 55's
follow-up), over the surface (texels rasterised from the bake mesh's UV triangles, the margin left out): the wear
share (mask R > 0.5), split by the asset's lower and upper half, the
stroke share (texels whose colour is not the most common colour of their base colour's family: the bake mesh's UV
triangles are rasterised per material, so a family is every texel painted from one ID colour; wear and grime texels
count too, so the share outside wear and the share lighter than that colour outside wear are printed beside it),
the largest 4-connected wear patch in texels (cut at UV seams), and for a multi-part asset the same per part. A
second argument after the export folder names another preset (scratch runs). It FAILS on a missing or empty file or
an operator error; the tone count is reported against its ceiling, not gated.
Follow-up 2 (2026-09-24): Bake's third output T_GT_<Asset>_N (painted-dab normals from the owner's OW Painterly
Normal Baker, imported from its folder: this run is --factory-startup) - its size, the 8-bit mean, the RMS tilt of the
decoded normals from straight up and the dab coverage (share tilted > 2 degrees) over the surface; the preview (every
GT material of the asset carries the _N on the bake's UV); Show Bake swapping the viewport and back.
Follow-up 4 (2026-09-25): Bake unwraps a single source with no UV (the source gets GT_UV) - TestNoUV, a copy of
TestCube with its UV removed, baked twice (one map of non-zero area, more than one tone, the second Bake keeps the map),
and Unwrap for Paint on a second copy and TestCube (nouv_case). TestCube and TestBox have no UV when made, so their own
Bake now unwraps them too.
The outputs land in Art/Export/<Asset>/, where Art/Unreal/setup_look_l1.py imports them.
"""
import math
import os
import sys
import time
import traceback
from collections import deque

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.dirname(HERE)
ART = os.path.dirname(BLENDER_DIR)
SOURCE_BLEND = os.path.join(ART, "rangerover.blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
EXPORT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(ART, "Export")
PRESET = os.path.abspath(ARGS[1]) if len(ARGS) > 1 else os.path.join(BLENDER_DIR, "gt_paint_preset.json")   # a 2nd argument: another preset
REF_COLLECTIONS = {"Reference", "Jig"}
MIN_FACES = 4
TONE_SHARE = 0.005

failures = []


def say(msg):
    print("GTPAINT_TEST " + msg)
    sys.stdout.flush()


def fail(msg):
    failures.append(msg)
    say("FAIL " + msg)


def guard():
    here = os.path.normcase(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else ""
    if not here:
        raise SystemExit("GTPAINT_TEST open a COPY of Art/rangerover.blend (bash Art/blender_test.sh does)")
    if here == os.path.normcase(os.path.abspath(SOURCE_BLEND)):
        raise SystemExit("GTPAINT_TEST refusing to run on the owner's blockout itself; bash Art/blender_test.sh copies it")
    say("blender %s, file %s (a copy; never saved), export to %s" % (bpy.app.version_string, bpy.data.filepath, EXPORT))


def modifier_type(owner, wanted):
    ids = [i.identifier for i in bpy.types.Modifier.bl_rna.properties["type"].enum_items]
    if wanted not in ids:
        raise SystemExit("modifier type %s not in %s" % (wanted, ids))
    return wanted


def make_box(name, size, location, bevel=None, colour_hex=None):
    """A box with its origin at the middle of its base, so Unreal places it on the ground."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], (v.co.z + 0.5) * size[2]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = location
    if bevel:
        mod = ob.modifiers.new("Bevel", modifier_type(ob, "BEVEL"))
        mod.width = bevel
        mod.segments = 3
    if colour_hex:
        from gt_paint import core
        mat = bpy.data.materials.new(name + "_OwnerPaint")
        tree = mat.node_tree
        bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if tree else None
        if bsdf is None:
            raise SystemExit("a new material has no Principled BSDF on this Blender; the cube's owner colour cannot be set")
        core.sock(bsdf.inputs, "Base Color").default_value = core.hex_linear(colour_hex)
        me.materials.append(mat)
    return ob


def car_parts():
    parts = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or {c.name for c in ob.users_collection} & REF_COLLECTIONS:
            continue
        if len(ob.data.polygons) < MIN_FACES:
            say("car: skipped %s (%d faces, as export_rangerover.py does)" % (ob.name, len(ob.data.polygons)))
            continue
        if ob.name.startswith("Test"):
            continue
        parts.append(ob)
    return parts


def select(obs, active):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


def image_array(path, raw=False):
    """The image's pixels, h x w x 4. raw: read as Non-Color (the _N is a 16-bit PNG: Blender loads it into a float
    buffer, which an sRGB colour space would linearise; measured: the 8-bit mean read 55 55 255 that way)."""
    img = bpy.data.images.load(path, check_existing=False)
    if raw:
        from gt_paint import core
        core.set_enum(img.colorspace_settings, "name", "Non-Color")
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4), w, h


def texel_families(asset, w, h):
    """Rasterises the bake mesh's UV triangles (texel centres) into a family index per texel (the ID colour of the
    triangle's material, -1 = no triangle) and the world Z per texel. Returns (family, z, family colours, z range)."""
    from gt_paint import core
    ob = bpy.data.objects.get(asset + core.BAKE_SUFFIX)
    if ob is None or len(ob.data.uv_layers) == 0:
        return None
    me = ob.data
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    loops = np.empty(nt * 3, np.int32)
    verts = np.empty(nt * 3, np.int32)
    mat_idx = np.empty(nt, np.int32)
    me.loop_triangles.foreach_get("loops", loops)
    me.loop_triangles.foreach_get("vertices", verts)
    me.loop_triangles.foreach_get("material_index", mat_idx)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers[0].data.foreach_get("uv", uv)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    uv = uv.reshape(-1, 2)[loops].reshape(nt, 3, 2) * np.array([w, h], np.float32)
    zs = co.reshape(-1, 3)[verts, 2].reshape(nt, 3)
    colours, fam_of_slot = [], []
    for slot in ob.material_slots:
        m = slot.material
        key = tuple(round(float(c), 4) for c in list(m[core.ID_PROP])[:3]) if core.is_gt(m) else None
        if key not in colours:
            colours.append(key)
        fam_of_slot.append(colours.index(key))
    fam = np.full((h, w), -1, np.int32)
    slot = np.full((h, w), -1, np.int32)
    area = 0.0
    zimg = np.zeros((h, w), np.float32)
    for t in range(nt):
        (ax, ay), (bx, by), (cx, cy) = uv[t]
        x0, x1 = max(int(math.floor(min(ax, bx, cx))), 0), min(int(math.ceil(max(ax, bx, cx))), w - 1)
        y0, y1 = max(int(math.floor(min(ay, by, cy))), 0), min(int(math.ceil(max(ay, by, cy))), h - 1)
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if x1 < x0 or y1 < y0 or abs(den) < 1e-12:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        l0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        l1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        l2 = 1.0 - l0 - l1
        inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        area += 0.5 * abs(den)
        if not inside.any():
            continue
        yi, xi = (Y[inside] - 0.5).astype(np.int32), (X[inside] - 0.5).astype(np.int32)
        fam[yi, xi] = fam_of_slot[mat_idx[t]] if mat_idx[t] < len(fam_of_slot) else -1
        slot[yi, xi] = mat_idx[t]
        zimg[yi, xi] = l0[inside] * zs[t, 0] + l1[inside] * zs[t, 1] + l2[inside] * zs[t, 2]
    return fam, zimg, colours, (float(zs.min()), float(zs.max())), area, slot, [s_.material for s_ in ob.material_slots]


def largest_patch(mask):
    """The largest 4-connected run of True texels (breadth-first; texel space, so a patch is cut at UV seams)."""
    h, w = mask.shape
    todo = mask.copy()
    best = 0
    for start in np.flatnonzero(todo.ravel()):
        if not todo.flat[start]:
            continue
        todo.flat[start] = False
        queue = deque([start])
        size = 0
        while queue:
            i = queue.popleft()
            size += 1
            y, x = divmod(i, w)
            for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1), (i - w, y > 0), (i + w, y < h - 1)):
                if ok and todo.flat[j]:
                    todo.flat[j] = False
                    queue.append(j)
        best = max(best, size)
    return best


def texel_stats(asset, d, m, w, h, covered):
    n = int(covered.sum())
    wear_all = (m[..., 0] > 0.5) & covered
    fams = texel_families(asset, w, h)
    if fams is None:
        fail("%s: no bake mesh to rasterise for the stroke share" % asset)
        return None
    fam, zimg, colours, (zlo, zhi), area, slot, slot_mats = fams
    rgb = np.round(d[..., :3] * 255.0).astype(np.int64)
    keys = (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]
    lum = rgb.sum(axis=-1)
    painted = covered & (fam >= 0)
    wear = wear_all & painted
    t0 = time.perf_counter()
    patch = largest_patch(wear)
    t_patch = time.perf_counter() - t0
    lower = painted & (zimg < 0.5 * (zlo + zhi))
    upper = painted & ~lower
    off_all = off_dry = total = dry = light_dry = 0
    parts = []
    for f, colour in enumerate(colours):
        sel = painted & (fam == f)
        cnt = int(sel.sum())
        if cnt == 0:
            continue
        uniq, counts = np.unique(keys[sel], return_counts=True)
        modal = int(uniq[np.argmax(counts)])
        off = sel & (keys != modal)
        drysel = sel & ~wear
        off_all += int(off.sum())
        off_dry += int((off & ~wear).sum())
        light_dry += int((off & ~wear & (lum > (modal >> 16) + ((modal >> 8) & 255) + (modal & 255))).sum())
        total += cnt
        dry += int(drysel.sum())
        parts.append("#%06X %d texels, modal #%06X, off %.1f %%, wear %.1f %%" % (
            (int(round(core_srgb(colour[0]))) << 16) | (int(round(core_srgb(colour[1]))) << 8) | int(round(core_srgb(colour[2])))
            if colour else 0, cnt, modal, 100.0 * off.sum() / cnt, 100.0 * (sel & wear).sum() / cnt))
    np_ = int(painted.sum())
    say("%s: surface = %d texels rasterised from the UV triangles (their UV area %.0f texels; %d uncovered) of %d covered (the rest is the %s px margin)" % (asset, np_, area, int(((fam >= 0) & ~covered).sum()), n, "grown"))
    say("%s: wear share %.4f of the surface (R > 0.5; lower half %.4f, upper half %.4f of their texels; %.4f with the margin); stroke share %.4f (off the family's modal colour), %.4f outside wear, %.4f lighter outside wear; largest wear patch %d texels (%.2f s)"
        % (asset, wear.sum() / float(max(np_, 1)), (lower & wear).sum() / float(max(lower.sum(), 1)),
           (upper & wear).sum() / float(max(upper.sum(), 1)), wear_all.sum() / float(n), off_all / float(max(total, 1)),
           off_dry / float(max(dry, 1)), light_dry / float(max(dry, 1)), patch, t_patch))
    say("%s: families %s" % (asset, "; ".join(parts)))
    if len(slot_mats) > 1:   # per part (one GT material each): wear share / stroke share against the family's modal colour
        modal_of = {}
        for f in range(len(colours)):
            sel = painted & (fam == f)
            if sel.any():
                uniq, counts = np.unique(keys[sel], return_counts=True)
                modal_of[f] = int(uniq[np.argmax(counts)])
        rows = []
        for i, mat in enumerate(slot_mats):
            sel = painted & (slot == i)
            cnt = int(sel.sum())
            f = int(fam[sel][0]) if cnt else -1
            if cnt == 0 or f not in modal_of:
                continue
            mlum = (modal_of[f] >> 16) + ((modal_of[f] >> 8) & 255) + (modal_of[f] & 255)
            rows.append("%s %d: wear %.3f, strokes %.3f, lighter %.3f" % ((mat.name[3:] if mat and mat.name.startswith("GT_") else str(mat and mat.name)),
                                                          cnt, (sel & wear).sum() / float(cnt), (sel & ~wear & (keys != modal_of[f])).sum() / float(cnt),
                                                          (sel & ~wear & (lum > mlum)).sum() / float(cnt)))
        say("%s: per part (texels: wear share, off-modal share outside wear, lighter than modal outside wear) %s" % (asset, "; ".join(rows)))
    return fam >= 0


def normal_stats(asset, path, surface):
    """The painted normal (follow-up 2): over the surface texels (the bake mesh's UV triangles rasterised), the 8-bit
    mean, the RMS tilt in degrees of the decoded normals from straight up (0 0 1), and the dab coverage = the share
    tilted more than 2 degrees. The file is DirectX (green down); a tilt does not depend on the green's sign."""
    n, w, h = image_array(path, raw=True)
    if surface is None or surface.shape != (h, w):
        fail("%s: the _N is %d x %d, the surface mask %s" % (asset, w, h, None if surface is None else surface.shape))
        return
    rgb = n[..., :3][surface].astype(np.float64) * 255.0     # 16-bit in the file: kept unrounded
    vec = rgb / 255.0 * 2.0 - 1.0
    length = np.linalg.norm(vec, axis=1)
    z = np.clip(vec[:, 2] / np.maximum(length, 1e-6), -1.0, 1.0)
    tilt = np.degrees(np.arccos(z))
    mean = rgb.mean(axis=0)
    say("%s: normal %d x %d, %d-bit, over %d surface texels: mean (8-bit scale) %.1f %.1f %.1f; RMS tilt %.2f deg (mean %.2f, 95 %% %.2f, "
        "max %.1f); dab coverage %.4f tilted > 2 deg (%.4f > 5 deg, %.4f > 10 deg); decoded length %.3f"
        % (asset, w, h, png_depth(path), int(surface.sum()), mean[0], mean[1], mean[2], float(np.sqrt((tilt ** 2).mean())),
           float(tilt.mean()), float(np.percentile(tilt, 95)), float(tilt.max()), float((tilt > 2.0).mean()),
           float((tilt > 5.0).mean()), float((tilt > 10.0).mean()), float(length.mean())))
    if not (tilt > 2.0).any():
        fail("%s: the _N has no texel tilted over 2 degrees (no dabs)" % asset)


def png_depth(path):
    with open(path, "rb") as handle:
        head = handle.read(26)
    return head[24] if head[1:4] == b"PNG" else -1


def preview_check(asset, objects, path):
    """Bake plugs the _N into the asset's GT materials (the preview): every one must carry it on the bake's UV."""
    from gt_paint import core
    bake_ob = bpy.data.objects.get(asset + core.BAKE_SUFFIX)
    uv = str(bake_ob.get("gt_uv", "")) if bake_ob is not None else ""
    mats = []
    for ob in objects:
        for s_ in ob.material_slots:
            if core.is_gt(s_.material) and s_.material not in mats:
                mats.append(s_.material)
    good = 0
    for m in mats:
        node = core.normal_node_of(m)
        img = next((n.image for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.name.startswith(core.NORMAL_TAG)), None)
        if node is not None and img is not None and node.uv_map == uv and \
                os.path.normcase(bpy.path.abspath(img.filepath)) == os.path.normcase(path):
            good += 1
    carry = sum(1 for ob in objects if uv in ob.data.uv_layers)
    say("%s: preview: %d of %d GT material(s) carry the _N on UV %s; %d of %d source object(s) carry that UV "
        "(the rest show it through Show Bake)" % (asset, good, len(mats), uv, carry, len(objects)))
    if good != len(mats):
        fail("%s: the _N preview is on %d of %d materials" % (asset, good, len(mats)))


def core_srgb(c):
    c = max(0.0, min(1.0, float(c)))
    return 255.0 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1.0 / 2.4) - 0.055)


def run_asset(asset, objects, active, preset):
    from gt_paint import core
    folder = os.path.join(EXPORT, asset)
    names = {"D": "T_GT_%s_D.png" % asset, "M": "T_GT_%s_M.png" % asset, "N": "T_GT_%s_N.png" % asset,
             "FBX": "SM_%s.fbx" % asset}
    for f in names.values():
        p = os.path.join(folder, f)
        if os.path.isfile(p):
            os.remove(p)   # this test's own output: a stale file must not pass for a new one
    s = bpy.context.scene.gt_paint
    s.asset_name = asset
    s.export_dir = EXPORT
    s.preset_path = PRESET
    s.bake_size = 'PRESET'
    select(objects, active)
    t0 = time.perf_counter()
    bpy.ops.gt_paint.apply_style()
    t1 = time.perf_counter()
    bpy.ops.gt_paint.bake()
    t2 = time.perf_counter()
    select(objects, active)
    bpy.ops.gt_paint.export()
    t3 = time.perf_counter()

    sizes = []
    for key in ("D", "M", "N", "FBX"):
        p = os.path.join(folder, names[key])
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            fail("%s: missing or empty %s" % (asset, p))
            sizes.append("%s MISSING" % names[key])
        else:
            sizes.append("%s %.1f KB" % (names[key], os.path.getsize(p) / 1024.0))
    say("%s: apply %.2f s, bake %.2f s, export %.2f s; %d object(s); files: %s"
        % (asset, t1 - t0, t2 - t1, t3 - t2, len(objects), ", ".join(sizes)))
    if not os.path.isfile(os.path.join(folder, names["D"])) or not os.path.isfile(os.path.join(folder, names["M"])):
        return

    bases = set()
    sources = set()
    for ob in objects:
        for slot in ob.material_slots:
            m = slot.material
            if core.is_gt(m):
                bases.add(tuple(round(float(c), 4) for c in list(m[core.ID_PROP])[:3]))
                sources.add(str(m.get(core.SOURCE_PROP, "?")))
    d, w, h = image_array(os.path.join(folder, names["D"]))
    m, _, _ = image_array(os.path.join(folder, names["M"]))
    covered = d[..., 3] > 0.5
    n = int(covered.sum())
    if n == 0:
        fail("%s: the albedo covers no texel" % asset)
        return
    rgb = np.round(d[..., :3][covered] * 255.0).astype(np.int64)
    keys = (rgb[:, 0] << 16) | (rgb[:, 1] << 8) | rgb[:, 2]
    uniq, counts = np.unique(keys, return_counts=True)
    tones = int((counts > TONE_SHARE * n).sum())
    ceiling = int(preset["tones"]) * max(1, len(bases))
    top = sorted(zip(counts.tolist(), uniq.tolist()), reverse=True)[:tones]
    top_txt = " ".join("#%06X:%.1f%%" % (k, 100.0 * c / n) for c, k in top)
    mean = rgb.mean(axis=0)
    mm = m[..., :3][covered].mean(axis=0)
    say("%s: %d x %d, %.1f %% of texels baked; tones %d over %.1f %% (ceiling %d = %d tones x %d base colour(s), %s; "
        "%d distinct colours in all) -> %s" % (asset, w, h, 100.0 * n / (w * h), tones, 100 * TONE_SHARE, ceiling,
                                              int(preset["tones"]), len(bases), "/".join(sorted(sources)), len(uniq),
                                              "within" if tones <= ceiling else "OVER THE CEILING"))
    say("%s: tones by share %s" % (asset, top_txt))
    say("%s: mean albedo sRGB %.1f %.1f %.1f; mask means R wear %.3f, G grime %.3f, B roughness %.3f"
        % (asset, mean[0], mean[1], mean[2], mm[0], mm[1], mm[2]))
    surface = texel_stats(asset, d, m, w, h, covered)
    n_path = os.path.join(folder, names["N"])
    if os.path.isfile(n_path):
        normal_stats(asset, n_path, surface)
        preview_check(asset, objects, n_path)


def uv_copy(ob):
    uv = np.empty(len(ob.data.loops) * 2, np.float32)
    ob.data.uv_layers[0].data.foreach_get("uv", uv)
    return uv


def nouv_case(cube, preset):
    """Follow-up 4: a copy of TestCube with its UV map removed goes through the panel's Bake. The SOURCE must come out
    with exactly one UV map of non-zero area, the albedo must hold more than one tone (counted as run_asset counts),
    and a second Bake must keep that map (still one, same name, same UVs). Then Unwrap for Paint on a second UV-less
    copy and TestCube (which has a UV): the copy gets one map, TestCube's is left alone (Replace off). The bakes go to
    a temp folder beside the blend copy with a temp preset that differs from the test's only in normal_enable false:
    the _N is not what this case checks, and it costs about 170 s a bake (TestCube's above)."""
    import json
    from gt_paint import core
    work = os.path.dirname(bpy.data.filepath)
    out = os.path.join(work, "export_nouv")
    with open(PRESET, encoding="utf-8") as f:
        data = json.load(f)
    data["normal_enable"] = False
    temp_preset = os.path.join(work, "preset_no_normal.json")
    with open(temp_preset, "w", encoding="utf-8") as f:
        json.dump(data, f)
    asset = "TestNoUV"
    ob = cube.copy()
    ob.data = cube.data.copy()
    ob.name = asset
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (14.0, 0.0, 0.0)
    had = [u.name for u in ob.data.uv_layers]
    for name in had:
        ob.data.uv_layers.remove(ob.data.uv_layers[name])
    say("%s: a copy of TestCube (%d faces), its UV map(s) %s removed -> %d" % (asset, len(ob.data.polygons), had,
                                                                              len(ob.data.uv_layers)))
    s = bpy.context.scene.gt_paint
    s.asset_name = asset
    s.export_dir = out
    s.preset_path = temp_preset
    s.bake_size = 'PRESET'
    d_path = os.path.join(out, asset, "T_GT_%s_D.png" % asset)
    if os.path.isfile(d_path):
        os.remove(d_path)
    select([ob], ob)
    say("%s: panel line before Bake: %s" % (asset, core.uv_plan([ob])))
    result = bpy.ops.gt_paint.bake()
    uvs = ob.data.uv_layers
    area = core.uv_area(ob.data) if len(uvs) else 0.0
    say("%s: Bake %s; the source now has %d UV map(s) %s, UV area %.4f" % (asset, sorted(result), len(uvs),
                                                                          [u.name for u in uvs], area))
    if result != {'FINISHED'} or len(uvs) != 1 or area <= 0.0:
        fail("%s: the source did not come out of Bake with one UV map of non-zero area" % asset)
        return
    if not os.path.isfile(d_path):
        fail("%s: no %s" % (asset, d_path))
        return
    d, w, h = image_array(d_path)
    covered = d[..., 3] > 0.5
    n = int(covered.sum())
    rgb = np.round(d[..., :3][covered] * 255.0).astype(np.int64)
    keys = (rgb[:, 0] << 16) | (rgb[:, 1] << 8) | rgb[:, 2]
    uniq, counts = np.unique(keys, return_counts=True)
    tones = int((counts > TONE_SHARE * n).sum())
    top = sorted(zip(counts.tolist(), uniq.tolist()), reverse=True)[:max(tones, 1)]
    mean = rgb.mean(axis=0) if n else np.zeros(3)
    say("%s: albedo %.1f %% of texels baked; tones %d over %.1f %% (%s), %d distinct colours in all; mean sRGB %.1f %.1f "
        "%.1f" % (asset, 100.0 * n / (w * h), tones, 100 * TONE_SHARE,
                  " ".join("#%06X:%.1f%%" % (k, 100.0 * c / max(n, 1)) for c, k in top), len(uniq),
                  mean[0], mean[1], mean[2]))
    if tones < 2:
        fail("%s: the albedo is one flat colour (%d tone over %.1f %%)" % (asset, tones, 100 * TONE_SHARE))
    name, first = uvs[0].name, uv_copy(ob)
    select([ob], ob)
    say("%s: panel line before the second Bake: %s" % (asset, core.uv_plan([ob])))
    result = bpy.ops.gt_paint.bake()
    uvs = ob.data.uv_layers
    same = len(uvs) == 1 and uvs[0].name == name and np.array_equal(first, uv_copy(ob))
    bake_ob = bpy.data.objects.get(asset + core.BAKE_SUFFIX)
    say("%s: second Bake %s; %d UV map(s) %s, UVs %s; the bake copy's UV %s" % (
        asset, sorted(result), len(uvs), [u.name for u in uvs], "unchanged" if same else "CHANGED",
        bake_ob.get("gt_uv") if bake_ob is not None else None))
    if result != {'FINISHED'} or not same:
        fail("%s: a second Bake did not keep the UV map the first one made" % asset)
    # Unwrap for Paint: the operator on a UV-less copy and on TestCube (a UV already, Replace off).
    ob2 = cube.copy()
    ob2.data = cube.data.copy()
    ob2.name = asset + "2"
    bpy.context.scene.collection.objects.link(ob2)
    ob2.location = (17.0, 0.0, 0.0)
    for u in [u.name for u in ob2.data.uv_layers]:
        ob2.data.uv_layers.remove(ob2.data.uv_layers[u])
    cube_names, cube_uv = [u.name for u in cube.data.uv_layers], uv_copy(cube)
    s.unwrap_replace = False
    select([ob2, cube], ob2)
    result = bpy.ops.gt_paint.unwrap()
    got = [u.name for u in ob2.data.uv_layers]
    area2 = core.uv_area(ob2.data) if got else 0.0
    kept = [u.name for u in cube.data.uv_layers] == cube_names and np.array_equal(cube_uv, uv_copy(cube))
    say("unwrap for paint %s: %s %s UV area %.4f (= the Bake's %.4f: %s); TestCube %s %s" % (
        sorted(result), ob2.name, got, area2, area, abs(area2 - area) < 1e-6, cube_names, "left alone" if kept else "CHANGED"))
    if result != {'FINISHED'} or len(got) != 1 or area2 <= 0.0 or not kept:
        fail("Unwrap for Paint: the UV-less copy did not get one map, or TestCube's UV changed")


def main():
    guard()
    sys.path.insert(0, BLENDER_DIR)
    import gt_paint
    gt_paint.register()
    from gt_paint import core
    preset, where = core.load_preset(PRESET)
    say("preset %s: tones %s, strokes %.2f of the surface over %.2f m (stretch %.1f), wear %.3f m x %.2f (pointiness "
        "%.2f, tint %.2f), scuffs %.2f over %.2f m, grime %.2f over %.2f m, "
        "highlight %.2f, roughness %.2f/%.2f/%.2f, bake %d px at %d sample(s)"
        % (where, preset["tones"], preset["grain_strength"], preset["grain_scale_m"], preset["grain_stretch"],
           preset["wear_width_m"], preset["wear_lighten"], preset["wear_pointiness"], preset["wear_tint"],
           preset["scuff_cover"], preset["scuff_scale_m"], preset["grime_strength"], preset["grime_distance_m"],
           preset["highlight"], preset["roughness"], preset["roughness_wear"], preset["roughness_grime"],
           preset["bake_size"], preset["bake_samples"]))
    say("preset normal: enable %s, baker path %r, %s" % (preset.get("normal_enable"), preset.get("normal_baker_path", ""),
        ", ".join("%s %s" % (k, v) for k, v in preset.get("normal", {}).items() if not k.startswith("_"))))
    car = car_parts()
    roof = next((o for o in car if o.name == "Roof"), car[0] if car else None)
    cube = make_box("TestCube", (1.0, 1.0, 1.0), (8.0, 0.0, 0.0), colour_hex="#E3B04B")
    box = make_box("TestBox", (1.2, 0.8, 0.8), (11.0, 0.0, 0.0), bevel=0.05)
    jobs = [("TestCube", [cube], cube), ("TestBox", [box], box)]
    if car:
        jobs.append(("TestCar", car, roof))
    else:
        fail("no car parts in the copy")
    for asset, objects, active in jobs:
        try:
            run_asset(asset, objects, active, preset)
        except Exception as error:
            traceback.print_exc()
            fail("%s: %s" % (asset, str(error).strip().splitlines()[-1] if str(error).strip() else type(error).__name__))
    # Apply Style again on the cube: a refresh must keep the material (no GT_*.001) and its ID colour.
    before = [(s.material.name, tuple(round(float(c), 4) for c in list(s.material[core.ID_PROP])[:3])) for s in cube.material_slots]
    bpy.context.scene.gt_paint.asset_name = "TestCube"   # the refresh reads the cube's own _N
    select([cube], cube)
    bpy.ops.gt_paint.apply_style()
    after = [(s.material.name, tuple(round(float(c), 4) for c in list(s.material[core.ID_PROP])[:3])) for s in cube.material_slots]
    say("refresh: TestCube %s -> %s (%s)" % (before, after, "kept" if before == after else "CHANGED"))
    if before != after:
        fail("a second Apply Style changed TestCube's material or ID colour")
    kept_n = all(core.normal_node_of(s_.material) is not None and any(
        n.type == "TEX_IMAGE" and n.name.startswith(core.NORMAL_TAG) and n.image is not None
        and n.image.filepath.endswith("T_GT_TestCube_N.png") for n in s_.material.node_tree.nodes)
        for s_ in cube.material_slots)
    say("refresh: TestCube's _N preview %s after Apply Style" % ("kept" if kept_n else "LOST"))
    if not kept_n:
        fail("Apply Style dropped TestCube's _N preview")
    if car:
        # Show Bake: the bake copy in, the sources out, and back.
        bpy.context.scene.gt_paint.asset_name = "TestCar"
        bake_ob = bpy.data.objects.get("TestCar" + core.BAKE_SUFFIX)
        select(car, roof)
        bpy.ops.gt_paint.show_bake()
        swapped = bake_ob is not None and not bake_ob.hide_get() and all(o.hide_get() for o in car)
        bpy.ops.gt_paint.show_bake()
        back = bake_ob is not None and bake_ob.hide_get() and not any(o.hide_get() for o in car)
        say("show bake: swapped %s, back %s" % (swapped, back))
        if not (swapped and back):
            fail("Show Bake did not swap the bake copy and the sources and back")
    try:
        nouv_case(cube, preset)
    except Exception as error:
        traceback.print_exc()
        fail("TestNoUV: %s" % (str(error).strip().splitlines()[-1] if str(error).strip() else type(error).__name__))
    if failures:
        say("RESULT FAIL %d: %s" % (len(failures), "; ".join(failures)))
        sys.stdout.flush()
        sys.exit(1)
    say("RESULT PASS %d assets baked and exported into %s" % (len(jobs), EXPORT))


main()
