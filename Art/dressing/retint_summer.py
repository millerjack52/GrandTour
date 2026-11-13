"""Leg dressing LD8a step 2 (docs/LEG_DRESSING_PLAN.md LD8a): the summer retint of the GT graphs' leaf materials.

Headless (Art/dressing/retint_summer.bat [apply]); env GT_RETINT_MODE picks the mode (-Script= drops arguments):
  inventory (default, READ-ONLY): every material on every mesh that PCG_GT_* spawns (the descriptor's override, else the
      mesh slot's own) and on the pack meshes the Nanite copies came from, with its parent chain, every vector
      parameter's value and hue (degrees, from the linear RGB), the static switches, the texture parameters and, for the
      pack leaf master, the albedo texture's mean colour -> docs/landscape_migration/ld8_warm_materials.json.
  apply: for every warm LEAF material (children of M_OWFoliageMaster or the pack's M_Tree_Leaf) a summer copy in
      /Game/GrandTour/Dressing/Materials/ (duplicate_asset: the same parent, every parameter copied), only its leaf colour
      parameters set from PALETTE below; then Art/dressing/retint_summer_map.txt ("<mesh> <slot material> <summer copy>"
      lines), which OWCreateBiomePCGCommandlet -Variant=GT reads to point the GT spawner entries at the copies
      (OverrideMaterials). The OW MIs, the pack MIs and the OW graphs are never written.
      Report docs/landscape_migration/ld8_retint_summer.json.
After apply: Art/dressing/create_biome_pcg.bat GT, setup_dress_hide.bat, then the tick harness (LandscapeToolkit.md).

THE STYLE PASS: PALETTE, VALUE_STEP and TONES are the single place the summer leaf colours live. Change them here, rerun
this script with apply (it re-tints the existing copies, reading the sources through the map), then rebuild as above.
None of it is final art.

How a palette row reaches a material (LD8a's mapping; the style pass may change it here):
  M_OWFoliageMaster (the colours ARE the albedo: BaseColor = hue jitter(lerp(TopColor x top term, NoiseColor, noise)),
      SubsurfaceColor = hue jitter(SubsurfaceColor)): TopColor and SubsurfaceColor = the row; NoiseColor, the second
      colour, = the row's hue at +/- VALUE_STEP value (the sign of the source's NoiseColor against its TopColor);
      GradientColor1/2 (behind hasGradientColor, off in every OW MI) = the row at +/- VALUE_STEP. Tone copies
      (_ToneWarm/_ToneCool) get the OW tone transform (TONES) on top.
  M_Tree_Leaf (pack; albedo = Blend_Overlay(the desaturated albedo texture, Base Albedo Color), lerped by
      "Base Lerp Between Color and Texture", x "Base Albedo Brightness"): when that albedo is warm (LD8c: only the cover
      plants), Base Albedo Color is solved per channel so the texture's mean comes out at the row (overlay below 0.5:
      2 x texture x colour), clamped to 0-1, otherwise it keeps the vendor value; every other warm
      leaf colour that is switched on (Base SSS Color, Tint Color 1/2, Second Color, Gradient Color) takes the row's hue
      and keeps its own saturation and value.
  LD8c: pack-master MIs (the copies above and the Nanite pack copies' bark) sit on GrandTour copies of the vendor masters
      (/Game/GrandTour/Dressing/Materials/Masters/M_GT_Tree_Leaf, M_GT_Tree_Bark) with the Voxels, Nanite and ISM usage
      flags; the vendor masters lack Voxels, so under r.Nanite.AllowVoxels=1 the Nanite pack copies drew the default
      material in game.
"""
import colorsys
import json
import os
import struct
import time
import traceback

import unreal

# ---- the summer palette (linear RGB). Dials placed near the GT grass value (the L3 cards: 0.08 0.20 0.06). ----
PALETTE = {
    "Beech": (0.09, 0.21, 0.05),
    "Birch": (0.16, 0.28, 0.07),
    "Oak":   (0.07, 0.17, 0.04),
    "Fir":   (0.04, 0.11, 0.05),
    "Bush":  (0.10, 0.22, 0.06),   # the bushes (SM_OWBush_*, SM_BirchBush_*); the cover plants borrow it (no row of their own)
}
# A material's second / gradient colour: the same hue at +/- this share of the value.
VALUE_STEP = 0.25
# The OW per-tree tone copies (ClaudeAuthorFoliageVariants.py ToneWarm/ToneCool: target hue deg, hue blend, sat x,
# value x), applied on top of the summer colour so the per-tree variation survives.
TONES = {
    "ToneWarm": (40.0, 0.15, 1.05, 1.06),
    "ToneCool": (160.0, 0.12, 0.88, 0.96),
}
# What counts as warm: a hue under WARM_HUE_MAX or from WARM_HUE_MIN up, with saturation >= WARM_SAT_MIN.
WARM_HUE_MAX = 70.0
WARM_HUE_MIN = 300.0
WARM_SAT_MIN = 0.2
# The copies' names: MI_GT_Leaf_<row>[_<source tag, when a row has several sources>][_<tone>]_Summer.
SOURCE_TAGS = {
    "MI_OWFoliage_Beech": "OWBeech", "MI_OWFoliage_Birch": "OWBirch", "MI_OWFoliage_FirTree": "OWFir",
    "MI_BirchTree_Leaf_01_Summer": "PackBirch", "MI_CoverPlants_01_Summer": "CoverPlant",
    "MI_OakTree_Leaf_01_Summer": "", "MI_OakTree_IvyLeaf_01_Summer": "Ivy",
}

GT_GRAPHS = ["/Game/GrandTour/Dressing/PCG/PCG_GT_" + b for b in ("Forest", "Meadow", "Scree", "Alpine", "Brush")]
# The pack meshes the Nanite copies (SM_GTN_*) were made from: checked too (the plan: "the pack MIs").
PACK_DIR = "/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes"
PACK_SOURCES = ([PACK_DIR + "/Trees/Trees_Summer/SM_BirchBush_%02d_Summer" % i for i in range(1, 6)]
                + [PACK_DIR + "/CoverPlants/CoverPlants_Summer/SM_CoverPlant_%02d_Summer" % i for i in range(1, 5)])
SUMMER_DIR = "/Game/GrandTour/Dressing/Materials"
# LD8c: the pack masters lack usage flags the GT meshes need (the Nanite pack copies under r.Nanite.AllowVoxels=1 asked
# M_Tree_Leaf / M_Tree_Bark for MATUSAGE_Voxels and drew the default checker in game). GrandTour copies of those masters
# carry the flags; every GT MI on them is reparented to the copy, and the Nanite pack copies' other vendor MIs (the
# bark) get GT MIs on the copies too. The vendor masters and MIs are only read.
MASTERS_DIR = SUMMER_DIR + "/Masters"
VENDOR_MASTERS = {"M_Tree_Leaf": "/Game/ANGRY_MESH/StylizedPack_Common/Materials/Masters/M_Tree_Leaf",
                  "M_Tree_Bark": "/Game/ANGRY_MESH/StylizedPack_Common/Materials/Masters/M_Tree_Bark"}
MASTER_COPIES = {"M_Tree_Leaf": "M_GT_Tree_Leaf", "M_Tree_Bark": "M_GT_Tree_Bark"}
MASTER_USAGES = ["MATUSAGE_VOXELS", "MATUSAGE_NANITE", "MATUSAGE_INSTANCED_STATIC_MESHES"]
NANITE_COPY_DIR = "/Game/GrandTour/Dressing/Nanite/"
OW_MASTER = "M_OWFoliageMaster"
PACK_MASTER = "M_Tree_Leaf"
PACK_LEAF_MASTERS = (PACK_MASTER, "M_GT_Tree_Leaf")
OW_MAIN = ["TopColor", "SubsurfaceColor"]
OW_SECOND = "NoiseColor"
OW_GRADIENT = ["GradientColor1", "GradientColor2"]
# The pack master's leaf colours and the static switch each needs (None: always on).
PACK_COLOURS = {"Base Albedo Color": None, "Base SSS Color": None, "Tint Color 1": "Enable Tint Variation Color",
                "Tint Color 2": "Enable Tint Variation Color", "Second Color": "Enable Second Color",
                "Gradient Color": "Enable Gradient Color"}

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MODE = os.environ.get("GT_RETINT_MODE", "inventory").strip().lower() or "inventory"
INV_PATH = os.path.join(ROOT, "docs", "landscape_migration", "ld8_warm_materials.json")
APPLY_PATH = os.path.join(ROOT, "docs", "landscape_migration", "ld8_retint_summer.json")
MAP_PATH = os.path.join(ROOT, "Art", "dressing", "retint_summer_map.txt")
TEX_DIR = os.path.join(ROOT, "Saved", "Temp", "retint_summer_tex")

mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
result = {"ok": True, "mode": MODE, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": {}}
state = {}


def step(name):
    def deco(fn):
        rec = {"ok": False}
        result["steps"][name] = rec
        try:
            rec["result"] = fn()
            rec["ok"] = True
        except Exception:
            rec["error"] = traceback.format_exc()[-3000:]
            result["ok"] = False
        return fn
    return deco


def obj_path(o):
    return str(o.get_path_name()) if o else None


def pkg_path(p):
    return p.split(".")[0] if p else p


def hsv(c):
    h, s, v = colorsys.rgb_to_hsv(max(c[0], 0.0), max(c[1], 0.0), max(c[2], 0.0))
    return round(h * 360.0, 1), round(s, 3), round(v, 4)


def is_warm(c):
    h, s, _v = hsv(c)
    return s >= WARM_SAT_MIN and (h < WARM_HUE_MAX or h >= WARM_HUE_MIN)


def row_of(mesh_name):
    n = mesh_name.lower()
    if "bush" in n:
        return "Bush", "bush"
    if "coverplant" in n:
        return "Bush", "cover plant: no palette row of its own, mapped to the bushes"
    for key, row in (("oak", "Oak"), ("fir", "Fir"), ("beech", "Beech"), ("birch", "Birch")):
        if key in n:
            return row, key
    return None, "no species in the name"


def parent_chain(m):
    chain = []
    cur = m
    while cur is not None and isinstance(cur, unreal.MaterialInstance):
        cur = cur.get_editor_property("parent")
        chain.append(obj_path(cur))
    return chain


def vec_value(m, name):
    if isinstance(m, unreal.MaterialInstance):
        c = mel.get_material_instance_vector_parameter_value(m, name)
    else:
        c = mel.get_material_default_vector_parameter_value(m, name)
    return [round(float(c.r), 5), round(float(c.g), 5), round(float(c.b), 5), round(float(c.a), 5)]


def scalar_value(m, name):
    if isinstance(m, unreal.MaterialInstance):
        return float(mel.get_material_instance_scalar_parameter_value(m, name))
    return float(mel.get_material_default_scalar_parameter_value(m, name))


_tex_cache = {}


def texture_mean(tex_path):
    """The mean linear colour of a texture's opaque texels (alpha >= 0.5), from a TGA export (Saved/Temp)."""
    if tex_path in _tex_cache:
        return _tex_cache[tex_path]
    t = unreal.load_asset(pkg_path(tex_path))
    os.makedirs(TEX_DIR, exist_ok=True)
    fn = os.path.join(TEX_DIR, tex_path.split(".")[-1] + ".tga")
    task = unreal.AssetExportTask()
    task.set_editor_property("object", t)
    task.set_editor_property("filename", fn)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    if not unreal.Exporter.run_asset_export_task(task) or not os.path.isfile(fn):
        raise RuntimeError("texture export failed: " + tex_path)
    b = open(fn, "rb").read()
    itype, (w, h), bpp = b[2], struct.unpack("<HH", b[12:16]), b[16]
    px, n, data = bpp // 8, w * h, b[18 + b[0]:]
    if itype == 10:
        out, i = bytearray(), 0
        while len(out) < n * px:
            hdr = data[i]
            i += 1
            cnt = (hdr & 0x7F) + 1
            if hdr & 0x80:
                out += data[i:i + px] * cnt
                i += px
            else:
                out += data[i:i + px * cnt]
                i += px * cnt
        data = bytes(out)
    srgb = bool(t.get_editor_property("srgb"))
    lin = (lambda c: (c / 255.0) / 12.92 if c <= 10 else ((c / 255.0 + 0.055) / 1.055) ** 2.4) if srgb else (lambda c: c / 255.0)
    s, k = [0.0, 0.0, 0.0], 0
    for j in range(0, n, max(1, n // 200000)):
        q = data[j * px:(j + 1) * px]
        if px == 4 and q[3] < 128:
            continue
        s[0] += lin(q[2])
        s[1] += lin(q[1])
        s[2] += lin(q[0])
        k += 1
    mean = [x / max(k, 1) for x in s]
    _tex_cache[tex_path] = mean
    return mean


def pack_albedo_terms(d):
    """(texture mean after desaturation, lerp L, brightness b) of an M_Tree_Leaf MI's base albedo."""
    t = texture_mean(d["textures"]["Base Albedo"])
    desat = d["scalars"].get("Base Albedo Desaturation", 0.0)
    lum = 0.3 * t[0] + 0.59 * t[1] + 0.11 * t[2]
    td = [x + (lum - x) * desat for x in t]
    return td, d["scalars"].get("Base Lerp Between Color and Texture", 1.0), d["scalars"].get("Base Albedo Brightness", 1.0)


def overlay(base, blend):
    return 2.0 * base * blend if base < 0.5 else 1.0 - 2.0 * (1.0 - base) * (1.0 - blend)


def describe_material(m):
    d = {"path": obj_path(m), "class": m.get_class().get_name(), "parents": parent_chain(m), "vectors": {},
         "scalars": {}, "switches": {}, "textures": {}}
    for n in mel.get_vector_parameter_names(m) or []:
        n = str(n)
        v = vec_value(m, n)
        h, s, val = hsv(v)
        d["vectors"][n] = {"rgba": v, "hue": h, "sat": s, "val": val, "warm": is_warm(v)}
    for n in mel.get_static_switch_parameter_names(m) or []:
        n = str(n)
        try:
            d["switches"][n] = bool(mel.get_material_instance_static_switch_parameter_value(m, n) if isinstance(m, unreal.MaterialInstance)
                                    else mel.get_material_default_static_switch_parameter_value(m, n))
        except Exception as exc:
            d["switches"][n] = "?" + repr(exc)[:80]
    for n in mel.get_texture_parameter_names(m) or []:
        n = str(n)
        try:
            t = (mel.get_material_instance_texture_parameter_value(m, n) if isinstance(m, unreal.MaterialInstance)
                 else mel.get_material_default_texture_parameter_value(m, n))
            d["textures"][n] = obj_path(t)
        except Exception as exc:
            d["textures"][n] = "?" + repr(exc)[:80]
    master = (d["parents"][-1] or "").split(".")[-1] if d["parents"] else d["path"].split(".")[-1]
    d["master"] = master
    d["leaf"] = master in (OW_MASTER,) + PACK_LEAF_MASTERS
    if master == OW_MASTER:
        leaf = OW_MAIN + [OW_SECOND] + (OW_GRADIENT if d["switches"].get("hasGradientColor") is True else [])
        d["leaf_params"] = [p for p in leaf if p in d["vectors"]]
    elif master in PACK_LEAF_MASTERS:
        for n in ("Base Albedo Desaturation", "Base Lerp Between Color and Texture", "Base Albedo Brightness"):
            try:
                d["scalars"][n] = scalar_value(m, n)
            except Exception as exc:
                d["scalars"][n] = None
        d["scalars"] = {k: v for k, v in d["scalars"].items() if v is not None}
        d["leaf_params"] = [p for p, sw in PACK_COLOURS.items() if p in d["vectors"] and (sw is None or d["switches"].get(sw) is True)]
        td, lerp, bright = pack_albedo_terms(d)
        c = d["vectors"]["Base Albedo Color"]["rgba"]
        eff = [bright * ((1.0 - lerp) * c[i] + lerp * overlay(td[i], c[i])) for i in range(3)]
        h, s, val = hsv(eff)
        d["albedo_texture_mean"] = [round(x, 4) for x in td]
        d["effective_albedo"] = {"rgb": [round(x, 4) for x in eff], "hue": h, "sat": s, "val": val, "warm": is_warm(eff)}
    else:
        d["leaf_params"] = []
    d["warm_params"] = [p for p in d["leaf_params"] if d["vectors"][p]["warm"]
                        and not (p == "Base Albedo Color" and "effective_albedo" in d)]
    if d.get("effective_albedo", {}).get("warm"):
        d["warm_params"].insert(0, "Base Albedo Color (effective, with the texture)")
    d["warm"] = bool(d["warm_params"])
    d["any_warm_colour"] = any(v["warm"] for v in d["vectors"].values())
    return d


def spawner_entries():
    """[(graph, node name, mesh, [override per slot], tags)] from the GT graphs."""
    out = []
    for g in GT_GRAPHS:
        graph = unreal.load_asset(g)
        if graph is None:
            raise RuntimeError("missing graph " + g)
        for node in graph.get_editor_property("nodes") or []:
            s = node.get_editor_property("settings_interface")
            if not isinstance(s, unreal.PCGStaticMeshSpawnerSettings):
                continue
            params = s.get_editor_property("mesh_selector_parameters")
            for e in params.get_editor_property("mesh_entries"):
                desc = e.get_editor_property("descriptor")
                out.append((g.rsplit("/", 1)[1], node.get_name(), desc.get_editor_property("static_mesh"),
                            list(desc.get_editor_property("override_materials") or []),
                            [str(t) for t in desc.get_editor_property("component_tags") or []]))
    return out


def effective_slots(mesh, overrides):
    slots = []
    for i, sm in enumerate(mesh.get_editor_property("static_materials")):
        own = sm.get_editor_property("material_interface")
        ov = overrides[i] if i < len(overrides) else None
        slots.append({"slot": i, "slot_name": str(sm.get_editor_property("material_slot_name")),
                      "own": obj_path(own), "override": obj_path(ov), "material": ov if ov else own})
    return slots


def summer_sources():
    """{summer copy path: source material path} from an earlier apply's map (a rebuilt GT graph already wears them)."""
    back = {}
    if os.path.isfile(MAP_PATH):
        for line in open(MAP_PATH, encoding="utf-8"):
            parts = line.split()
            if len(parts) == 3 and not parts[0].startswith("#"):
                back[parts[2]] = parts[1]
    return back


@step("inventory")
def inventory():
    mats, uses = {}, []
    back = summer_sources()
    for graph, node, mesh, overrides, tags in spawner_entries():
        if mesh is None:
            uses.append({"graph": graph, "node": node, "mesh": None})
            continue
        row, why = row_of(mesh.get_name())
        for sl in effective_slots(mesh, overrides):
            m = sl.pop("material")
            p = obj_path(m)
            if p in back:
                # the entry already wears a summer copy: inventory (and re-tint from) its source
                sl["summer_now"] = p
                m = unreal.load_asset(pkg_path(back[p]))
                p = obj_path(m)
            if p and p not in mats:
                mats[p] = describe_material(m)
            uses.append({"graph": graph, "node": node, "mesh": obj_path(mesh), "tags": tags, "row": row, "row_why": why,
                         "slot": sl["slot"], "slot_name": sl["slot_name"], "own": sl["own"], "override": sl["override"],
                         "summer_now": sl.get("summer_now"), "material": p})
    pack = []
    for mp in PACK_SOURCES:
        mesh = unreal.load_asset(mp)
        if mesh is None:
            pack.append({"mesh": mp, "missing": True})
            continue
        for sl in effective_slots(mesh, []):
            m = sl.pop("material")
            p = obj_path(m)
            if p and p not in mats:
                mats[p] = describe_material(m)
            pack.append({"mesh": obj_path(mesh), "slot": sl["slot"], "slot_name": sl["slot_name"], "material": p})
    for p, d in mats.items():
        d["used_by_meshes"] = sorted({u["mesh"].rsplit("/", 1)[1] for u in uses if u.get("material") == p})
        d["rows"] = sorted({u["row"] or "none" for u in uses if u.get("material") == p})
    state["mats"], state["uses"] = mats, uses
    return {"materials": len(mats), "uses": len(uses),
            "warm_leaf": sorted(p.split(".")[-1] for p, d in mats.items() if d["leaf"] and d["warm"]),
            "warm_not_leaf": sorted(p.split(".")[-1] for p, d in mats.items() if not d["leaf"] and d["any_warm_colour"]),
            "pack_sources": pack}


# ---------------------------------------------------------------------------------------------------------------- apply

def lc(rgb, a=1.0):
    c = unreal.LinearColor()
    c.r, c.g, c.b, c.a = float(rgb[0]), float(rgb[1]), float(rgb[2]), float(a)
    return c


def scale_value(rgb, k):
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    return colorsys.hsv_to_rgb(h, s, v * k)


def with_hue(rgb, hue_of):
    _h, s, v = colorsys.rgb_to_hsv(*[max(x, 0.0) for x in rgb])
    h, _s, _v = colorsys.rgb_to_hsv(*hue_of)
    return colorsys.hsv_to_rgb(h, s, v)


def tone(rgb, tone_name):
    if not tone_name:
        return tuple(rgb)
    hue, blend, sat_mul, val_mul = TONES[tone_name]
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    d = ((hue / 360.0 - h + 0.5) % 1.0) - 0.5
    return colorsys.hsv_to_rgb((h + d * blend) % 1.0, min(1.0, s * sat_mul), v * val_mul)


def summer_values(d, row, tone_name):
    """{param: rgba} for the copy (the mapping in the module docstring)."""
    base = tone(PALETTE[row], tone_name)
    vec = d["vectors"]
    out = {}
    if d["master"] == OW_MASTER:
        for p in OW_MAIN:
            out[p] = list(base) + [vec[p]["rgba"][3]]
        up = vec[OW_SECOND]["val"] >= vec["TopColor"]["val"]
        out[OW_SECOND] = list(scale_value(base, 1.0 + (VALUE_STEP if up else -VALUE_STEP))) + [vec[OW_SECOND]["rgba"][3]]
        g1, g2 = OW_GRADIENT
        hi, lo = (g1, g2) if vec[g1]["val"] >= vec[g2]["val"] else (g2, g1)
        out[hi] = list(scale_value(base, 1.0 + VALUE_STEP)) + [vec[hi]["rgba"][3]]
        out[lo] = list(scale_value(base, 1.0 - VALUE_STEP)) + [vec[lo]["rgba"][3]]
    else:
        # LD8c: the albedo moves only when it is warm (the cover plants' orange texture); a green one (the birch bushes,
        # 126 deg; the oaks) keeps the vendor value - LD8a's solve for every pack leaf turned the birch bushes purple-grey.
        if d.get("effective_albedo", {}).get("warm"):
            td, lerp, bright = pack_albedo_terms(d)
            col = []
            for i in range(3):
                # base < 0.5 (every pack leaf texture mean is): overlay = 2 t c, so albedo = b c ((1 - L) + 2 L t)
                k = bright * ((1.0 - lerp) + 2.0 * lerp * td[i]) if td[i] < 0.5 else None
                col.append(min(1.0, max(0.0, base[i] / k)) if k else vec["Base Albedo Color"]["rgba"][i])
            out["Base Albedo Color"] = col + [vec["Base Albedo Color"]["rgba"][3]]
        else:
            out["Base Albedo Color"] = list(vec["Base Albedo Color"]["rgba"])
        for p in d["leaf_params"]:
            if p != "Base Albedo Color" and vec[p]["warm"]:
                out[p] = list(with_hue(vec[p]["rgba"][:3], base)) + [vec[p]["rgba"][3]]
    return out


def summer_name(row, src_name, tone_name, several):
    stem = src_name.split("_Tone")[0]
    tag = SOURCE_TAGS.get(stem, stem.replace("MI_", "")) if several else ""
    return "MI_GT_Leaf_%s%s%s_Summer" % (row, "_" + tag if tag else "", "_" + tone_name if tone_name else "")


def make_master_copies():
    """{vendor master name: GT copy path}: duplicate each vendor master once, then set its usage flags (every apply)."""
    if not eal.does_directory_exist(MASTERS_DIR):
        eal.make_directory(MASTERS_DIR)
    out = {}
    for name, src in VENDOR_MASTERS.items():
        dst = MASTERS_DIR + "/" + MASTER_COPIES[name]
        if not eal.does_asset_exist(dst) and eal.duplicate_asset(src, dst) is None:
            raise RuntimeError("duplicate_asset(%s, %s) failed" % (src, dst))
        m = unreal.load_asset(dst)
        for usage in MASTER_USAGES:
            mel.set_base_material_usage(m, getattr(unreal.MaterialUsage, usage), True)
        missing = [u for u in ("used_with_voxels", "used_with_nanite", "used_with_instanced_static_meshes")
                   if not m.get_editor_property(u)]
        if missing:
            raise RuntimeError("%s lacks %s after set_base_material_usage" % (dst, missing))
        mel.recompile_material(m)
        if not eal.save_asset(dst, only_if_is_dirty=False):
            raise RuntimeError("save failed: " + dst)
        out[name] = obj_path(m)
    return out


def reparent_to_gt(mi, d, gt_masters):
    """Put a GT MI on the GT copy of its source's master (when there is one); returns its parent's path."""
    src_parent = d["parents"][0] if d["parents"] else None
    master = (src_parent or "").split(".")[-1]
    if master in gt_masters:
        if obj_path(mi.get_editor_property("parent")) != gt_masters[master]:
            mel.set_material_instance_parent(mi, unreal.load_asset(pkg_path(gt_masters[master])))
        want = gt_masters[master]
    else:
        want = src_parent
    if obj_path(mi.get_editor_property("parent")) != want:
        raise RuntimeError("%s has parent %s, wanted %s" % (obj_path(mi), obj_path(mi.get_editor_property("parent")), want))
    return want


@step("apply")
def apply_step():
    if MODE != "apply":
        return "skipped (inventory mode)"
    mats, uses = state["mats"], state["uses"]
    warm = {p for p, d in mats.items() if d["leaf"] and d["warm"]}
    no_param = [p for p in warm if not mats[p]["leaf_params"]]
    if no_param:
        raise RuntimeError("warm leaf colour not driven by a parameter (texture only): %s" % no_param)
    pairs = sorted({(u["material"], u["row"]) for u in uses if u.get("material") in warm})
    unmapped = [p for p in pairs if p[1] is None]
    if unmapped:
        raise RuntimeError("warm leaf material on a mesh with no palette row: %s" % unmapped)
    stems_by_row = {}
    for src, row in pairs:
        stems_by_row.setdefault(row, set()).add(src.split(".")[-1].split("_Tone")[0])
    if not eal.does_directory_exist(SUMMER_DIR):
        eal.make_directory(SUMMER_DIR)
    gt_masters = make_master_copies()
    made, copy_of = {}, {}
    for src, row in pairs:
        d = mats[src]
        src_name = src.split(".")[-1]
        tone_name = next((t for t in TONES if src_name.endswith("_" + t)), None)
        name = summer_name(row, src_name, tone_name, len(stems_by_row[row]) > 1)
        dst = SUMMER_DIR + "/" + name
        if not eal.does_asset_exist(dst):
            if eal.duplicate_asset(pkg_path(src), dst) is None:
                raise RuntimeError("duplicate_asset(%s, %s) failed" % (src, dst))
        mi = unreal.load_asset(dst)
        if not isinstance(mi, unreal.MaterialInstanceConstant):
            raise RuntimeError("the copy %s is not a MaterialInstanceConstant" % dst)
        src_parent = reparent_to_gt(mi, d, gt_masters)
        values = summer_values(d, row, tone_name)
        for p, rgba in values.items():
            # the return value is not a success flag here (False on a pack MI whose value did change): read it back
            mel.set_material_instance_vector_parameter_value(mi, p, lc(rgba[:3], rgba[3]))
            got = vec_value(mi, p)
            if max(abs(got[i] - rgba[i]) for i in range(4)) > 1e-4:
                raise RuntimeError("set %s on %s failed: read back %s, wanted %s" % (p, dst, got, rgba))
        mel.update_material_instance(mi)
        if not eal.save_asset(dst, only_if_is_dirty=False):
            raise RuntimeError("save failed: " + dst)
        after = describe_material(mi)
        made[name] = {"path": obj_path(mi), "source": src, "row": row, "tone": tone_name, "parent": src_parent,
                      "set": {p: {"rgb": [round(x, 4) for x in v[:3]], "hue_sat_val": list(hsv(v[:3]))} for p, v in values.items()},
                      "before": {p: d["vectors"][p]["rgba"] for p in values},
                      "effective_albedo_after": after.get("effective_albedo"),
                      "other_vectors_equal": all(after["vectors"][k]["rgba"] == d["vectors"][k]["rgba"] for k in d["vectors"] if k not in values),
                      "scalars_equal": after["scalars"] == d["scalars"],
                      "switches_equal": after["switches"] == d["switches"],
                      "textures_equal": after["textures"] == d["textures"]}
        if not (made[name]["other_vectors_equal"] and made[name]["switches_equal"] and made[name]["textures_equal"]):
            raise RuntimeError("the copy %s differs from its source outside the leaf colours" % dst)
        copy_of[(src, row)] = obj_path(mi)
    # LD8c: the Nanite pack copies' remaining vendor MIs on a copied master (the birch bushes' bark) get GT MIs.
    usage = {}
    for u in uses:
        m = u.get("material")
        if not m or not (u.get("mesh") or "").startswith(NANITE_COPY_DIR) or (m, u.get("row")) in copy_of:
            continue
        d = mats[m]
        master = (d["parents"][-1] or "").split(".")[-1] if d["parents"] else ""
        if master not in MASTER_COPIES:
            continue
        dst = SUMMER_DIR + "/MI_GT_" + m.split(".")[-1][len("MI_"):]
        if not eal.does_asset_exist(dst) and eal.duplicate_asset(pkg_path(m), dst) is None:
            raise RuntimeError("duplicate_asset(%s, %s) failed" % (m, dst))
        mi = unreal.load_asset(dst)
        parent = reparent_to_gt(mi, d, gt_masters)
        mel.update_material_instance(mi)
        if not eal.save_asset(dst, only_if_is_dirty=False):
            raise RuntimeError("save failed: " + dst)
        after = describe_material(mi)
        same = all(after["vectors"][k]["rgba"] == d["vectors"][k]["rgba"] for k in d["vectors"]) \
            and after["switches"] == d["switches"] and after["textures"] == d["textures"]
        if not same:
            raise RuntimeError("the GT MI %s differs from its source" % dst)
        usage[dst.rsplit("/", 1)[1]] = {"path": obj_path(mi), "source": m, "parent": parent, "equal_to_source": same}
        copy_of[(m, u.get("row"))] = obj_path(mi)
    lines = set()
    for u in uses:
        key = (u.get("material"), u.get("row"))
        if key in copy_of:
            lines.add("%s %s %s" % (u["mesh"], u["material"], copy_of[key]))
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        f.write("# Written by Art/dressing/retint_summer.py apply (leg dressing LD8a); read by OWCreateBiomePCGCommandlet -Variant=GT.\n")
        f.write("# <GT spawner mesh> <slot material> <its summer copy>\n")
        for line in sorted(lines):
            f.write(line + "\n")
    return {"masters": gt_masters, "made": made, "copies": len(made), "usage_copies": usage, "map_lines": len(lines),
            "map_path": MAP_PATH}


result["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
out = dict(result)
if "mats" in state:
    out["materials"] = state["mats"]
    out["uses"] = state["uses"]
report = INV_PATH if MODE != "apply" else APPLY_PATH
with open(report, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, default=str)
unreal.log("RETINT_SUMMER mode=%s ok=%s report=%s" % (MODE, result["ok"], report))
