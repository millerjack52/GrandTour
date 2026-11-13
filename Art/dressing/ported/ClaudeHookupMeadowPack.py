"""AM1 of Docs/MeadowPackIntegrationPlan.md: repoint the three OW
LandscapeGrassTypes at ANGRY MESH Meadow Pack summer meshes.

HEADLESS (editor CLOSED; PowerShell):
  & 'C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe'
    C:\\GrandTour\\GrandTour.uproject -run=PythonScript
    "-Script=C:/GrandTour/Art/dressing/ported/ClaudeHookupMeadowPack.py"
    -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"

Rerunnable: each run REPLACES grass_varieties on the three LGTs with the
spec below. The paint pins in ClaudeSetupDressingLab.py GRASS_TYPES stay
as they are (its grass_types step no longer re-tunes existing LGTs, so a
lab-script rerun cannot stomp these values). Retired by this hookup: MW
donor varieties + SM_OWFlowerClump_* recolors (assets stay on disk).

Saves pass only_if_is_dirty=False (paid 2026-07-28: property swaps do not
reliably dirty packages; save_loaded_asset silently skips + reports ok).
The source's REAL gate was ClaudeVerifyMeadowPackHookup.py (not ported) in a
FRESH session - it read this run's report and compared disk state against it.
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


# ---------------------------------------------------------------------------
# FIRST FPS KNOB at the gate: per-LGT densities (instances per 10m2).
# DEMO-MATCH 2026-07-28 (user: "grass should look like it does in the demos"):
# values below mirror the pack's own LG_M01_Grass_Summer/LG_M01_Plants_Summer
# reference LGTs exactly (audit: ClaudeAuditPackGrassReferenceReport.json) -
# ONE mid-size grass mesh at 800 with 0.75-1.5 uniform scale jitter, flowers
# at 400/200 + a 50-density grass fill. ONE deliberate delta: the demo runs
# flowers with cast shadows ON; our grass/small-prop budget policy keeps
# every variety shadowless. Escalation if FPS tanks: halve densities, then
# trim culls back to 6000/8000.
# Layered per the user's diorama/summer-map references (audit:
# ClaudeAuditPackDemoMapsReport.json): bright Grass_01 carpet + big dark
# Grass_03 ferny accents (diorama places them at 1.65-2.0 scale) +
# CoverPlant_04 fronds; flowers = the summer map's five-species mix ratios.
# PERF CUT 2026-07-28 (user: meadow struggled at demo-spec 800/630 with
# 15km culls): densities roughly halved, culls back down. LIVE tuning of
# all of this without an editor close: ClaudeTuneMeadowLook.py (stage B) -
# keep its KNOBS defaults in sync with these baselines when baking.
MEADOW_GRASS_DENSITIES = (450.0, 40.0, 40.0)        # Grass_01 / Grass_03 / CoverPlant_04
FLOWER_DENSITIES = (120.0, 70.0, 40.0, 30.0, 20.0, 25.0)  # 07/08/03/05/06 + grass fill
FOREST_FLOOR_DENSITIES = (420.0, 160.0, 120.0, 55.0, 55.0)  # carpet Grass_01_02 + Grass_02 x2 + CoverPlant x2 (carpet added RV+1 round; DG round 2026-07-30 densities ~1.65x)

MEADOW_GRASS_CULL = (6000, 8000)    # start/end cm
FLOWER_CULL = (4500, 6000)
FOREST_FLOOR_CULL = (3500, 4500)    # under canopy, kept short (DG round trim: offsets the ~1.65x density rise to ~+35% instances net)

# MF2 meadow TYPES (Docs/MeadowForestLookPerfPlan.md): lush = the diorama/
# hero look (leaf-blob ground shrubs included), dry = short sparse scrubland.
# Live knobs mirror these in ClaudeTuneMeadowLook.py - keep in sync.
LUSH_GRASS_DENSITIES = (600.0, 90.0, 70.0, 12.0)    # Grass_01 / Grass_03 / CoverPlant_04 / BirchLeaves
LUSH_FLOWER_DENSITIES = (240.0, 140.0, 80.0, 60.0, 40.0, 50.0)  # double standard
DRY_GRASS_DENSITIES = (250.0, 60.0, 8.0)            # small Grass_01_03 / Grass_02 / lone flowers
LUSH_GRASS_CULL = (6000, 8000)
LUSH_FLOWER_CULL = (4500, 6000)
DRY_GRASS_CULL = (5000, 6500)

# MF3 per-type forest floors (shared LGT_OWForestFloor stays for mixed
# OW_Forest; the type layers get their own recipes, mushrooms rare).
# RV+1 forest-carpet round (user 2026-07-28, post-RVT: "similar grass
# coverage in forests"): each floor gains a meadow-style CARPET variety
# as row 0, slightly under-scaled (under-canopy read). DG round
# 2026-07-30 (user-approved denser-forest-grass table): carpet+grass rows
# up ~1.6-1.7x, cover plants smaller bumps, mushrooms untouched
# (accents); culls trimmed 3750/5000 -> 3500/4500 as VRAM compensation
# (density x cull-radius^2 nets ~+35% instances, not +65%). Other perf
# guards untouched: shadowless, MF3 patch-noise mask (~1/3 of floor
# carries grass). Escalation if a forest stat gpu glance regresses or
# the screen-only VRAM banner shows: halve the carpet DELTA (back toward
# 250/150/200), then culls to 3000/4000 - via ClaudeTuneMeadowLook.py
# knobs, not here.
FLOOR_DECIDUOUS_DENSITIES = (420.0, 150.0, 45.0, 30.0, 4.0)  # carpet Grass_01_02 / Grass_02_01 / CoverPlant_01 / _03 / brown mushroom
FLOOR_FIR_DENSITIES = (240.0, 70.0, 30.0, 3.0)               # small carpet Grass_01_03 / Grass_02_02 / CoverPlant_02 / red mushroom
FLOOR_OAK_DENSITIES = (330.0, 100.0, 55.0, 6.0)              # carpet Grass_01_02 / CoverPlant_04 / Grass_03_02 / brown mushroom
# RC-A alpine round (user 2026-07-30): sparse hardy high-altitude grass -
# small variants only, low density, open-ground culls. OW_Snow gets NO
# grass by design (clean snowfield; weight-blend kills siblings).
ALPINE_GRASS_DENSITIES = (120.0, 30.0, 8.0)  # small Grass_01_03 / Grass_02_02 / CoverPlant_02
ALPINE_GRASS_CULL = (5000, 6500)
# ---------------------------------------------------------------------------

PACK_MESHES = "/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes"
LGT_DIR = "/Game/OWGame/Dev/DressingLab"

REPORT_PATH = Path(__file__).with_name("ClaudeHookupMeadowPackReport.json")


def _mesh(sub: str, name: str) -> str:
    return f"{PACK_MESHES}/{sub}/{name}.{name}"


def _row(mesh, density, cull, scale_min, scale_max, use_grid, jitter):
    return {
        "mesh": mesh,
        "density": float(density),
        "start_cull": int(cull[0]),
        "end_cull": int(cull[1]),
        "scale_min": float(scale_min),
        "scale_max": float(scale_max),
        "use_grid": bool(use_grid),
        "placement_jitter": float(jitter),
        "cast_dynamic_shadow": False,
    }


def _spec():
    """(lgt asset path, [variety row dicts]) - rows mirror the pack demo
    LGTs field-for-field (grid/jitter/scale included) except shadows."""
    meadow = [
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_01_Summer_02"),
             MEADOW_GRASS_DENSITIES[0], MEADOW_GRASS_CULL, 0.75, 1.5, False, 1.0),
        # Dark feathery accent clumps - diorama hand-places these BIG.
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_03_Summer_02"),
             MEADOW_GRASS_DENSITIES[1], MEADOW_GRASS_CULL, 1.2, 2.0, False, 1.0),
        # Fern fronds - the summer map's most-painted cover plant.
        _row(_mesh("CoverPlants/CoverPlants_Summer", "SM_CoverPlant_04_Summer"),
             MEADOW_GRASS_DENSITIES[2], MEADOW_GRASS_CULL, 0.7, 1.3, False, 1.0),
    ]
    flowers = [
        _row(_mesh("Flowers", "SM_Flower_07_02"),
             FLOWER_DENSITIES[0], FLOWER_CULL, 0.75, 1.5, True, 1.0),
        _row(_mesh("Flowers", "SM_Flower_08_02"),
             FLOWER_DENSITIES[1], FLOWER_CULL, 0.75, 1.2, False, 0.0),
        _row(_mesh("Flowers", "SM_Flower_03_02"),
             FLOWER_DENSITIES[2], FLOWER_CULL, 0.75, 1.25, False, 1.0),
        _row(_mesh("Flowers", "SM_Flower_05_02"),
             FLOWER_DENSITIES[3], FLOWER_CULL, 0.75, 1.25, False, 1.0),
        _row(_mesh("Flowers", "SM_Flower_06_02"),
             FLOWER_DENSITIES[4], FLOWER_CULL, 0.75, 1.25, False, 1.0),
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_02_Summer_02"),
             FLOWER_DENSITIES[5], FLOWER_CULL, 1.0, 1.0, False, 1.0),
    ]
    floor_meshes = (
        _mesh("Grass/Grass_Summer", "SM_Grass_01_Summer_02"),
        _mesh("Grass/Grass_Summer", "SM_Grass_02_Summer_01"),
        _mesh("Grass/Grass_Summer", "SM_Grass_02_Summer_02"),
        _mesh("CoverPlants/CoverPlants_Summer", "SM_CoverPlant_01_Summer"),
        _mesh("CoverPlants/CoverPlants_Summer", "SM_CoverPlant_02_Summer"),
    )
    floor = [
        _row(path, FOREST_FLOOR_DENSITIES[i], FOREST_FLOOR_CULL,
             0.6 if i == 0 else 0.75, 1.1 if i == 0 else 1.2, False, 1.0)
        for i, path in enumerate(floor_meshes)
    ]
    # MF2: lush meadow - denser carpet, big dark accents, fern fronds, and
    # the diorama's leaf-blob ground shrubs (SM_Leaves_BirchTree_02).
    lush = [
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_01_Summer_02"),
             LUSH_GRASS_DENSITIES[0], LUSH_GRASS_CULL, 0.75, 1.5, False, 1.0),
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_03_Summer_02"),
             LUSH_GRASS_DENSITIES[1], LUSH_GRASS_CULL, 1.2, 2.0, False, 1.0),
        _row(_mesh("CoverPlants/CoverPlants_Summer", "SM_CoverPlant_04_Summer"),
             LUSH_GRASS_DENSITIES[2], LUSH_GRASS_CULL, 0.7, 1.3, False, 1.0),
        _row(_mesh("Leaves/Leaves_Summer", "SM_Leaves_BirchTree_02_Summer"),
             LUSH_GRASS_DENSITIES[3], LUSH_GRASS_CULL, 0.8, 1.3, False, 1.0),
    ]
    lush_flowers = [
        _row(_mesh("Flowers", "SM_Flower_07_02"),
             LUSH_FLOWER_DENSITIES[0], LUSH_FLOWER_CULL, 0.75, 1.5, True, 1.0),
        _row(_mesh("Flowers", "SM_Flower_08_02"),
             LUSH_FLOWER_DENSITIES[1], LUSH_FLOWER_CULL, 0.75, 1.2, False, 0.0),
        _row(_mesh("Flowers", "SM_Flower_03_02"),
             LUSH_FLOWER_DENSITIES[2], LUSH_FLOWER_CULL, 0.75, 1.25, False, 1.0),
        _row(_mesh("Flowers", "SM_Flower_05_02"),
             LUSH_FLOWER_DENSITIES[3], LUSH_FLOWER_CULL, 0.75, 1.25, False, 1.0),
        _row(_mesh("Flowers", "SM_Flower_06_02"),
             LUSH_FLOWER_DENSITIES[4], LUSH_FLOWER_CULL, 0.75, 1.25, False, 1.0),
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_02_Summer_02"),
             LUSH_FLOWER_DENSITIES[5], LUSH_FLOWER_CULL, 1.0, 1.0, False, 1.0),
    ]
    # MF2: dry meadow - the SMALL Grass_01 variant, short and sparse.
    dry = [
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_01_Summer_03"),
             DRY_GRASS_DENSITIES[0], DRY_GRASS_CULL, 0.7, 1.2, False, 1.0),
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_02_Summer_02"),
             DRY_GRASS_DENSITIES[1], DRY_GRASS_CULL, 0.75, 1.2, False, 1.0),
        _row(_mesh("Flowers", "SM_Flower_06_02"),
             DRY_GRASS_DENSITIES[2], DRY_GRASS_CULL, 0.75, 1.25, False, 1.0),
    ]
    # MF3 per-type floors.
    floor_deciduous = [
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_01_Summer_02"),
             FLOOR_DECIDUOUS_DENSITIES[0], FOREST_FLOOR_CULL, 0.6, 1.1, False, 1.0),
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_02_Summer_01"),
             FLOOR_DECIDUOUS_DENSITIES[1], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
        _row(_mesh("CoverPlants/CoverPlants_Summer", "SM_CoverPlant_01_Summer"),
             FLOOR_DECIDUOUS_DENSITIES[2], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
        _row(_mesh("CoverPlants/CoverPlants_Summer", "SM_CoverPlant_03_Summer"),
             FLOOR_DECIDUOUS_DENSITIES[3], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
        _row(_mesh("Mushrooms/Mushrooms_Summer", "SM_Mushroom_Brown_12_Summer"),
             FLOOR_DECIDUOUS_DENSITIES[4], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
    ]
    floor_fir = [
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_01_Summer_03"),
             FLOOR_FIR_DENSITIES[0], FOREST_FLOOR_CULL, 0.6, 1.0, False, 1.0),
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_02_Summer_02"),
             FLOOR_FIR_DENSITIES[1], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
        _row(_mesh("CoverPlants/CoverPlants_Summer", "SM_CoverPlant_02_Summer"),
             FLOOR_FIR_DENSITIES[2], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
        _row(_mesh("Mushrooms/Mushrooms_Summer", "SM_Mushroom_Red_12_Summer"),
             FLOOR_FIR_DENSITIES[3], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
    ]
    floor_oak = [
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_01_Summer_02"),
             FLOOR_OAK_DENSITIES[0], FOREST_FLOOR_CULL, 0.6, 1.1, False, 1.0),
        _row(_mesh("CoverPlants/CoverPlants_Summer", "SM_CoverPlant_04_Summer"),
             FLOOR_OAK_DENSITIES[1], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_03_Summer_02"),
             FLOOR_OAK_DENSITIES[2], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
        _row(_mesh("Mushrooms/Mushrooms_Summer", "SM_Mushroom_Brown_12_Summer"),
             FLOOR_OAK_DENSITIES[3], FOREST_FLOOR_CULL, 0.75, 1.2, False, 1.0),
    ]
    alpine = [
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_01_Summer_03"),
             ALPINE_GRASS_DENSITIES[0], ALPINE_GRASS_CULL, 0.5, 0.9, False, 1.0),
        _row(_mesh("Grass/Grass_Summer", "SM_Grass_02_Summer_02"),
             ALPINE_GRASS_DENSITIES[1], ALPINE_GRASS_CULL, 0.6, 1.0, False, 1.0),
        _row(_mesh("CoverPlants/CoverPlants_Summer", "SM_CoverPlant_02_Summer"),
             ALPINE_GRASS_DENSITIES[2], ALPINE_GRASS_CULL, 0.6, 1.0, False, 1.0),
    ]
    return [
        (f"{LGT_DIR}/LGT_OWMeadowGrass", meadow),
        (f"{LGT_DIR}/LGT_OWMeadowFlowers", flowers),
        (f"{LGT_DIR}/LGT_OWForestFloor", floor),
        (f"{LGT_DIR}/LGT_OWMeadowLushGrass", lush),
        (f"{LGT_DIR}/LGT_OWMeadowLushFlowers", lush_flowers),
        (f"{LGT_DIR}/LGT_OWMeadowDryGrass", dry),
        (f"{LGT_DIR}/LGT_OWFloorDeciduous", floor_deciduous),
        (f"{LGT_DIR}/LGT_OWFloorFir", floor_fir),
        (f"{LGT_DIR}/LGT_OWFloorOak", floor_oak),
        (f"{LGT_DIR}/LGT_OWAlpineGrass", alpine),
    ]


result = {"ok": True, "steps": {}, "expected": {}}


def step(name):
    def decorate(func):
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": value}
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            unreal.log_error(f"MEADOWPACK {name}: {exc!r}")
            return None

    return decorate


DONOR_GRASS_TYPE = "/Game/MWLandscapeAutoMaterial/Procedurals/LGT_MWAM_Grass"


def _repoint(lgt_path: str, entries):
    lgt = unreal.load_asset(lgt_path)
    if lgt is None:
        # MF2/MF3: this script now OWNS LGT authoring - get-or-create the
        # new type/floor LGTs from the proven donor (varieties are replaced
        # wholesale below, so the donor's contents never leak through).
        # Asset creation requires a headless session (editor closed).
        if unreal.EditorAssetLibrary.duplicate_asset(DONOR_GRASS_TYPE, lgt_path) is None:
            raise RuntimeError(f"LGT missing and donor duplicate failed: {lgt_path}")
        lgt = unreal.load_asset(lgt_path)
        if lgt is None:
            raise RuntimeError(f"LGT still unloadable after create: {lgt_path}")
    varieties = []
    written = []
    for row in entries:
        mesh = unreal.load_asset(row["mesh"])
        if mesh is None:
            raise RuntimeError(f"pack mesh failed to load: {row['mesh']}")
        gv = unreal.GrassVariety()
        gv.set_editor_property("grass_mesh", mesh)
        # Per-platform structs: set the 'default' field (house pattern from
        # ClaudeSetupDressingLab.py grass_types).
        for prop, val in (("grass_density", row["density"]),
                          ("start_cull_distance", row["start_cull"]),
                          ("end_cull_distance", row["end_cull"])):
            pp = gv.get_editor_property(prop)
            pp.set_editor_property("default", val)
            gv.set_editor_property(prop, pp)
        # Demo-look fields (scaling stays the UNIFORM default, so the X
        # interval is the whole scale jitter).
        scale = gv.get_editor_property("scale_x")
        scale.set_editor_property("min", row["scale_min"])
        scale.set_editor_property("max", row["scale_max"])
        gv.set_editor_property("scale_x", scale)
        gv.set_editor_property("use_grid", row["use_grid"])
        gv.set_editor_property("placement_jitter", row["placement_jitter"])
        # Grass/prop budget policy: grass never casts shadows (deliberate
        # delta from the pack demo, which shadows its flowers).
        gv.set_editor_property("cast_dynamic_shadow", row["cast_dynamic_shadow"])
        varieties.append(gv)
        written.append(dict(row))
    lgt.set_editor_property("grass_varieties", varieties)
    lgt.modify()
    if not unreal.EditorAssetLibrary.save_loaded_asset(lgt, only_if_is_dirty=False):
        raise RuntimeError(f"save failed for {lgt_path}")
    result["expected"][lgt_path] = written
    return written


for _lgt_path, _entries in _spec():
    _name = _lgt_path.rsplit("/", 1)[-1]
    step(_name)(lambda p=_lgt_path, e=_entries: _repoint(p, e))

REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT_PATH}")
unreal.log("MEADOWPACK hookup complete - now run "
           "ClaudeVerifyMeadowPackHookup.py in a FRESH session")
