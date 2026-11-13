"""Leg dressing LD8b (docs/LEG_DRESSING_PLAN.md): GrandTour copies of the 10 OW landscape grass types.

Headless (Art/dressing/gt_grass_copies.bat). For each /Game/OWGame/Dev/DressingLab/LGT_OW<Name> it makes (or refreshes)
/Game/GrandTour/Dressing/Grass/LGT_GT_<Name> with duplicate_asset (every variety and setting copied), then sets on every
variety: bCastDynamicShadow false, bCastContactShadow true, bAffectDistanceFieldLighting false (FGrassVariety, Python
cast_dynamic_shadow / cast_contact_shadow / affect_distance_field_lighting). M_GT_Landscape's grass output wears the
copies (Art/Unreal/setup_m6_hide.py GT_GRASS_PATH; rebuild it with Art/dressing/ld2_landscape_material.bat). The OW grass
types are only read. The copies are look dials for the style pass: VARIETY_FLAGS below is the one place.
Report docs/landscape_migration/ld8b_grass_copies.json.
"""
import json
import os
import time
import traceback

import unreal

OW_DIR = "/Game/OWGame/Dev/DressingLab"
GT_DIR = "/Game/GrandTour/Dressing/Grass"
NAMES = ["AlpineGrass", "FloorDeciduous", "FloorFir", "FloorOak", "ForestFloor", "MeadowDryGrass", "MeadowFlowers",
         "MeadowGrass", "MeadowLushFlowers", "MeadowLushGrass"]
VARIETY_FLAGS = {"cast_dynamic_shadow": False, "cast_contact_shadow": True, "affect_distance_field_lighting": False}
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPORT = os.path.join(ROOT, "docs", "landscape_migration", "ld8b_grass_copies.json")

eal = unreal.EditorAssetLibrary
result = {"ok": True, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "flags": VARIETY_FLAGS, "copies": {}}
try:
    if not eal.does_directory_exist(GT_DIR):
        eal.make_directory(GT_DIR)
    for n in NAMES:
        src, dst = "%s/LGT_OW%s" % (OW_DIR, n), "%s/LGT_GT_%s" % (GT_DIR, n)
        rec = {"source": src}
        if not eal.does_asset_exist(src):
            raise RuntimeError("missing " + src)
        if not eal.does_asset_exist(dst) and eal.duplicate_asset(src, dst) is None:
            raise RuntimeError("duplicate_asset failed: " + dst)
        lgt = unreal.load_asset(dst)
        varieties = list(lgt.get_editor_property("grass_varieties"))
        before = [{k: bool(v.get_editor_property(k)) for k in VARIETY_FLAGS} for v in varieties]
        for v in varieties:
            for k, val in VARIETY_FLAGS.items():
                v.set_editor_property(k, val)
        lgt.set_editor_property("grass_varieties", varieties)
        after = [{k: bool(v.get_editor_property(k)) for k in VARIETY_FLAGS} for v in lgt.get_editor_property("grass_varieties")]
        if any(a != VARIETY_FLAGS for a in after):
            raise RuntimeError("read-back differs on " + dst)
        if not eal.save_asset(dst, only_if_is_dirty=False):
            raise RuntimeError("save failed: " + dst)
        rec.update({"copy": dst, "varieties": len(varieties), "before": before, "after": after})
        result["copies"]["LGT_GT_" + n] = rec
except Exception:
    result["ok"] = False
    result["error"] = traceback.format_exc()[-2000:]
result["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=1)
unreal.log("GT_GRASS_COPIES ok=%s copies=%d report=%s" % (result["ok"], len(result["copies"]), REPORT))
