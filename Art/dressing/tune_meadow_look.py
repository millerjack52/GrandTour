"""LIVE meadow/forest look+perf knobs (source project, user 2026-07-28: frames struggle in
oak forest + meadow; flower/bush density and grass height must be tunable).

Ported to GrandTour (docs/LandscapeMigrationManifest.md 9.B.5) from the source project's
Scripts/ClaudeTuneMeadowLook.py. KNOBS values are byte-identical to the source.

RUN HEADLESS (editor closed):  Art/dressing/tune_meadow_look.bat
RUN IN-EDITOR:                 py "C:/GrandTour/Art/dressing/tune_meadow_look.py"

Edit KNOBS below, rerun, look. Values are ABSOLUTE (safe to rerun - no
compounding). LGT edits show up in the grass immediately (script flushes
the grass cache); the PCG knobs (bushes, oak tiers) save the graphs and
fire Generate on the meadow/forest/road biome actors of the open map
(none open, e.g. headless: Generate is skipped and the step still passes).

OWNERSHIP: this is the LIVE tuning layer. The durable baselines live in
Art/dressing/ported/ClaudeHookupMeadowPack.py (LGTs) and
Source/GrandTourEditor/Private/Dressing/OWCreateBiomePCGCommandlet.cpp (PCG
samplers) - when knob values feel right, report them and they get baked
back as the shipped defaults (snapshot doctrine). A hookup rerun or
commandlet regen (Art/dressing/create_biome_pcg.bat) stomps live tuning
back to those baselines: rerun this script after it.

Report: tune_meadow_look_report.json next to this script (per-step ok).
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


# ---------------------------------------------------------------------------
KNOBS = dict(
    # LGT_OWMeadowGrass (per-10m2 densities; variety order is fixed by the
    # hookup script: carpet Grass_01_02, dark accent Grass_03_02, fronds
    # CoverPlant_04)
    grass_density=450.0,
    grass_accent_density=40.0,      # applied to BOTH accent varieties
    grass_height=1.0,               # Z-only multiplier (1.0 = uniform demo look)
    grass_cull=(6000, 8000),        # start/end cm

    # LGT_OWMeadowFlowers (order fixed: Flower_07/08/03/05/06 + grass fill)
    flower_densities=(120.0, 70.0, 40.0, 30.0, 20.0, 25.0),
    flower_cull=(4500, 6000),

    # PCG_OWMeadow birch-bush scatters (points per m2). MF2: three streams,
    # rank-matched by saved density (lush > standard > dry) - keep the
    # three values distinct or the rank match misassigns.
    bush_points_per_m2=0.0004,
    lush_bush_points_per_m2=0.0006,
    dry_bush_points_per_m2=0.00008,

    # RV3 GroundCoverRVT dab scatter (standard + lush meadows; one value
    # drives both samplers). Dabs only read right with RVT live (RV0-2).
    dab_points_per_m2=0.0003,

    # MF2 meadow types (variety order fixed by ClaudeHookupMeadowPack.py).
    # Lush: Grass_01 carpet / Grass_03 accents / CoverPlant_04 / birch-leaf shrubs.
    lush_grass_densities=(600.0, 90.0, 70.0, 12.0),
    lush_grass_cull=(6000, 8000),
    lush_flower_densities=(240.0, 140.0, 80.0, 60.0, 40.0, 50.0),
    lush_flower_cull=(4500, 6000),
    # Dry: small Grass_01_03 / Grass_02 / lone Flower_06.
    dry_grass_densities=(250.0, 60.0, 8.0),
    dry_grass_cull=(5000, 6500),

    # MF3 per-type forest floors (order fixed by the hookup script).
    # RV+1: row 0 of each is the meadow-style CARPET variety - the
    # forest-coverage lever. DG round 2026-07-30: user-approved denser
    # table (~1.65x, mushrooms untouched), culls trimmed to 3500/4500 as
    # VRAM compensation. Escalation on stat gpu regress / VRAM banner:
    # halve the carpet DELTA (toward 250/150/200/250), then culls to
    # 3000/4000.
    floor_deciduous_densities=(420.0, 150.0, 45.0, 30.0, 4.0),
    floor_fir_densities=(240.0, 70.0, 30.0, 3.0),
    floor_oak_densities=(330.0, 100.0, 55.0, 6.0),
    # Shared mixed-forest floor LGT_OWForestFloor (knob added DG round -
    # previously only tunable via a hookup rerun).
    forest_floor_densities=(420.0, 160.0, 120.0, 55.0, 55.0),
    floor_cull=(3500, 4500),

    # RC-A alpine grass (order fixed by the hookup script: small
    # Grass_01_03 / Grass_02_02 / CoverPlant_02). Snow has no grass.
    alpine_grass_densities=(120.0, 30.0, 8.0),
    alpine_cull=(5000, 6500),

    # PCG_OWForest oak tiers: multiplier on the authored tier bases
    # (0.02 heavy / 0.01 dense / 0.0035 sparse). 0.35 = shipped default.
    oak_density_scale=0.35,

    # MF0 wind A/B switch: bEvaluateWorldPositionOffset on every oak spawner
    # mesh entry. False = statue-still trees (wind + player-push + float all
    # live in WPO). True = shipped default.
    oak_wind=True,

    # RL2 v3 typed road dressing (PCG_OWRoad; road TYPE = which BP the
    # road was dragged from: BP_OWRoad=mud, BP_OWRoad_Dusty, _Gravel).
    # SPLINE-ANCHORED spacings: one point per N cm of road PER SIDE
    # (smaller = denser). Baselines live in OWCreateBiomePCGCommandlet.cpp
    # RoadRecipes - keep in sync. The spline samplers are rank-matched by
    # saved increment per mesh token (bush doctrine): values within each
    # dict MUST stay distinct and keep their relative ordering or the
    # match misassigns.
    road_stone_spacing_cm=dict(gravel=350.0, mud=700.0, dusty=1000.0),
    road_tuft_spacing_cm=dict(dusty=80.0, mud=250.0),
    road_dab_spacing_cm=dict(mud_verge=500.0, mud_onroad=1200.0,
                             dusty_onroad=2500.0),
    # On-road slightly-sunk rock cards (user 2026-07-30 v2: pack rocks
    # read as boulders; GroundCoverRVT_Rock_01..04 instead). TOKEN
    # DOCTRINE: 01/03 are shared with the mud verge dabs (01/03/05), so
    # streams are matched by palette-UNIQUE tokens - this stream by
    # Rock_04, verge dabs by Rock_05, planks by _Plank.
    road_onroad_rock_spacing_cm=dict(gravel=400.0, mud=900.0, dusty=1800.0),
)
# ---------------------------------------------------------------------------

ASSET_DIR = "/Game/OWGame/Dev/DressingLab"
OAK_TIER_BASES = (0.02, 0.01, 0.0035)
REPORT_PATH = Path(__file__).with_name("tune_meadow_look_report.json")

result = {"ok": True, "steps": {}}


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
            unreal.log_error(f"MEADOWTUNE {name}: {exc!r}")
            return None

    return decorate


def _save(asset, label):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"save failed for {label}")


def _set_density(gv, value):
    pp = gv.get_editor_property("grass_density")
    pp.set_editor_property("default", float(value))
    gv.set_editor_property("grass_density", pp)


def _set_cull(gv, cull):
    for prop, val in (("start_cull_distance", int(cull[0])),
                      ("end_cull_distance", int(cull[1]))):
        pp = gv.get_editor_property(prop)
        pp.set_editor_property("default", val)
        gv.set_editor_property(prop, pp)


def _set_height(gv, height):
    """height==1.0 -> UNIFORM (demo behavior); else LOCK_XY with Z = the
    variety's own XY interval scaled by the knob (footprint unchanged)."""
    if abs(height - 1.0) < 1e-3:
        gv.set_editor_property("scaling", unreal.GrassScaling.UNIFORM)
        return
    xy = gv.get_editor_property("scale_x")
    z = gv.get_editor_property("scale_z")
    z.set_editor_property("min", float(xy.get_editor_property("min")) * height)
    z.set_editor_property("max", float(xy.get_editor_property("max")) * height)
    gv.set_editor_property("scale_z", z)
    gv.set_editor_property("scaling", unreal.GrassScaling.LOCK_XY)


@step("meadow_grass_lgt")
def meadow_grass_lgt():
    lgt = unreal.load_asset(f"{ASSET_DIR}/LGT_OWMeadowGrass")
    varieties = list(lgt.get_editor_property("grass_varieties"))
    if len(varieties) != 3:
        raise RuntimeError(f"expected 3 varieties (carpet+2 accents), got "
                           f"{len(varieties)} - rerun ClaudeHookupMeadowPack first")
    out = []
    for i, gv in enumerate(varieties):
        _set_density(gv, KNOBS["grass_density"] if i == 0
                     else KNOBS["grass_accent_density"])
        _set_cull(gv, KNOBS["grass_cull"])
        _set_height(gv, float(KNOBS["grass_height"]))
        mesh = gv.get_editor_property("grass_mesh")
        out.append(f"{mesh.get_name()}: d={KNOBS['grass_density'] if i == 0 else KNOBS['grass_accent_density']}"
                   f" h={KNOBS['grass_height']} cull={KNOBS['grass_cull']}")
    lgt.set_editor_property("grass_varieties", varieties)
    lgt.modify()
    _save(lgt, "LGT_OWMeadowGrass")
    return out


@step("meadow_flowers_lgt")
def meadow_flowers_lgt():
    lgt = unreal.load_asset(f"{ASSET_DIR}/LGT_OWMeadowFlowers")
    varieties = list(lgt.get_editor_property("grass_varieties"))
    wanted = KNOBS["flower_densities"]
    if len(varieties) != len(wanted):
        raise RuntimeError(f"expected {len(wanted)} flower varieties, got "
                           f"{len(varieties)} - rerun ClaudeHookupMeadowPack first")
    out = []
    for gv, dens in zip(varieties, wanted):
        _set_density(gv, dens)
        _set_cull(gv, KNOBS["flower_cull"])
        out.append(f"{gv.get_editor_property('grass_mesh').get_name()}: d={dens}")
    lgt.set_editor_property("grass_varieties", varieties)
    lgt.modify()
    _save(lgt, "LGT_OWMeadowFlowers")
    return out


def _tune_lgt(lgt_name, densities, cull):
    """Generic per-LGT density/cull tuner for the MF2/MF3 LGTs. Soft-skips
    (loudly) when the LGT does not exist yet - the hookup script creates
    them in the next editor-closed cycle."""
    path = f"{ASSET_DIR}/{lgt_name}"
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        return f"SKIPPED - {lgt_name} missing (run ClaudeHookupMeadowPack.py cycle first)"
    lgt = unreal.load_asset(path)
    varieties = list(lgt.get_editor_property("grass_varieties"))
    if len(varieties) != len(densities):
        raise RuntimeError(f"{lgt_name}: expected {len(densities)} varieties, "
                           f"got {len(varieties)} - rerun ClaudeHookupMeadowPack first")
    out = []
    for gv, dens in zip(varieties, densities):
        _set_density(gv, dens)
        _set_cull(gv, cull)
        out.append(f"{gv.get_editor_property('grass_mesh').get_name()}: d={dens}")
    lgt.set_editor_property("grass_varieties", varieties)
    lgt.modify()
    _save(lgt, lgt_name)
    return out


@step("lush_grass_lgt")
def lush_grass_lgt():
    return _tune_lgt("LGT_OWMeadowLushGrass",
                     KNOBS["lush_grass_densities"], KNOBS["lush_grass_cull"])


@step("lush_flowers_lgt")
def lush_flowers_lgt():
    return _tune_lgt("LGT_OWMeadowLushFlowers",
                     KNOBS["lush_flower_densities"], KNOBS["lush_flower_cull"])


@step("dry_grass_lgt")
def dry_grass_lgt():
    return _tune_lgt("LGT_OWMeadowDryGrass",
                     KNOBS["dry_grass_densities"], KNOBS["dry_grass_cull"])


@step("floor_deciduous_lgt")
def floor_deciduous_lgt():
    return _tune_lgt("LGT_OWFloorDeciduous",
                     KNOBS["floor_deciduous_densities"], KNOBS["floor_cull"])


@step("floor_fir_lgt")
def floor_fir_lgt():
    return _tune_lgt("LGT_OWFloorFir",
                     KNOBS["floor_fir_densities"], KNOBS["floor_cull"])


@step("floor_oak_lgt")
def floor_oak_lgt():
    return _tune_lgt("LGT_OWFloorOak",
                     KNOBS["floor_oak_densities"], KNOBS["floor_cull"])


@step("forest_floor_lgt")
def forest_floor_lgt():
    return _tune_lgt("LGT_OWForestFloor",
                     KNOBS["forest_floor_densities"], KNOBS["floor_cull"])


@step("alpine_grass_lgt")
def alpine_grass_lgt():
    return _tune_lgt("LGT_OWAlpineGrass",
                     KNOBS["alpine_grass_densities"], KNOBS["alpine_cull"])


def _directed_adjacency(graph):
    """(source_prop autodetect via a source-only node, then downstream map)"""
    edges = graph.get_all_edges()
    # Landscape getter only has outputs; whichever edge side it appears on
    # is the SOURCE side of every edge.
    source_prop = None
    for edge in edges:
        for prop, other in (("input_pin", "output_pin"), ("output_pin", "input_pin")):
            pin = edge.get_editor_property(prop)
            node = pin.get_editor_property("node") if pin else None
            s = node.get_editor_property("settings_interface") if node else None
            if isinstance(s, unreal.PCGGetLandscapeSettings):
                source_prop = prop
                break
        if source_prop:
            break
    if source_prop is None:
        raise RuntimeError("could not orient edges (no landscape getter found)")
    dest_prop = "output_pin" if source_prop == "input_pin" else "input_pin"
    downstream = {}
    for edge in edges:
        src = edge.get_editor_property(source_prop).get_editor_property("node")
        dst = edge.get_editor_property(dest_prop).get_editor_property("node")
        if src and dst:
            downstream.setdefault(src.get_name(), []).append(dst)
    return downstream


def _spawner_meshes_below(node, downstream):
    """BFS downstream; return concatenated mesh names of reached spawners."""
    names = []
    seen = set()
    queue = [node]
    while queue:
        n = queue.pop(0)
        if n.get_name() in seen:
            continue
        seen.add(n.get_name())
        s = n.get_editor_property("settings_interface")
        if isinstance(s, unreal.PCGStaticMeshSpawnerSettings):
            params = s.get_editor_property("mesh_selector_parameters")
            for e in params.get_editor_property("mesh_entries"):
                mesh = e.get_editor_property("descriptor").get_editor_property("static_mesh")
                if mesh:
                    names.append(mesh.get_name())
            continue
        queue.extend(downstream.get(n.get_name(), []))
    return names


def _samplers_feeding(graph, mesh_token):
    """[(node, settings, current points/m2)] for samplers whose downstream
    spawner palette contains mesh_token."""
    downstream = _directed_adjacency(graph)
    nodes = {}
    for edge in graph.get_all_edges():
        for prop in ("input_pin", "output_pin"):
            pin = edge.get_editor_property(prop)
            node = pin.get_editor_property("node") if pin else None
            if node:
                nodes[node.get_name()] = node
    hits = []
    for node in nodes.values():
        s = node.get_editor_property("settings_interface")
        if not isinstance(s, unreal.PCGSurfaceSamplerSettings):
            continue
        if any(mesh_token in m for m in _spawner_meshes_below(node, downstream)):
            hits.append((node, s, float(s.get_editor_property("points_per_squared_meter"))))
    return hits


@step("meadow_bush_density")
def meadow_bush_density():
    """MF2: 1 sampler = pre-MF2 graph (standard only); 3 samplers = typed
    graph, rank-matched by saved density (lush > standard > dry)."""
    graph = unreal.load_asset(f"{ASSET_DIR}/PCG_OWMeadow")
    hits = _samplers_feeding(graph, "BirchBush")
    if len(hits) == 1:
        _node, s, old = hits[0]
        s.set_editor_property("points_per_squared_meter", float(KNOBS["bush_points_per_m2"]))
        s.modify()
        _save(graph, "PCG_OWMeadow")
        return f"bush sampler {old} -> {KNOBS['bush_points_per_m2']} (pre-MF2 graph)"
    if len(hits) != 3:
        raise RuntimeError(f"expected 1 or 3 bush samplers, found {len(hits)}")
    hits.sort(key=lambda h: -h[2])  # saved density rank: lush > standard > dry
    wanted = (float(KNOBS["lush_bush_points_per_m2"]),
              float(KNOBS["bush_points_per_m2"]),
              float(KNOBS["dry_bush_points_per_m2"]))
    out = []
    for (_node, s, old), new in zip(hits, wanted):
        s.set_editor_property("points_per_squared_meter", new)
        s.modify()
        out.append(f"{old} -> {new}")
    _save(graph, "PCG_OWMeadow")
    return out


@step("dab_density")
def dab_density():
    """RV3: both meadow dab samplers get the same knob. Soft-skips before
    the dab streams exist (pre-RV3 graph)."""
    graph = unreal.load_asset(f"{ASSET_DIR}/PCG_OWMeadow")
    hits = _samplers_feeding(graph, "GroundCoverRVT")
    if not hits:
        return "SKIPPED - no dab samplers yet (run the RV3 cycle first)"
    if len(hits) != 2:
        raise RuntimeError(f"expected 2 dab samplers, found {len(hits)}")
    out = []
    for _node, s, old in hits:
        s.set_editor_property("points_per_squared_meter", float(KNOBS["dab_points_per_m2"]))
        s.modify()
        out.append(f"{old} -> {KNOBS['dab_points_per_m2']}")
    _save(graph, "PCG_OWMeadow")
    return out


def _spline_samplers_feeding(graph, mesh_token):
    """[(node, settings, saved DistanceIncrement)] for SPLINE samplers
    whose downstream spawner palette contains mesh_token (road graph)."""
    downstream = _directed_adjacency(graph)
    nodes = {}
    for edge in graph.get_all_edges():
        for prop in ("input_pin", "output_pin"):
            pin = edge.get_editor_property(prop)
            node = pin.get_editor_property("node") if pin else None
            if node:
                nodes[node.get_name()] = node
    hits = []
    for node in nodes.values():
        s = node.get_editor_property("settings_interface")
        if not isinstance(s, unreal.PCGSplineSamplerSettings):
            continue
        if any(mesh_token in m for m in _spawner_meshes_below(node, downstream)):
            params = s.get_editor_property("sampler_params")
            hits.append((node, s, float(params.get_editor_property("distance_increment"))))
    return hits


@step("road_dressing_spacing")
def road_dressing_spacing():
    """RL2 v3 + on-road rocks: eleven spline samplers across the three
    type recipes, matched by mesh token + saved-increment rank ASC
    (per-token baselines are distinct by design - see the KNOBS
    comment). Soft-skips pre-RL2 graphs. Read-back verified (struct
    copies write back silently)."""
    path = f"{ASSET_DIR}/PCG_OWRoad"
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        return "SKIPPED - PCG_OWRoad missing (run the RL2 commandlet cycle first)"
    graph = unreal.load_asset(path)
    # Tokens must be palette-UNIQUE, not just mesh-family-unique: the
    # on-road rock cards (01/02/03/04) share meshes with the mud verge
    # dabs (01/03/05), so each stream is matched by a member the others
    # lack (Rock_04 / Rock_05 / _Plank).
    wanted = (
        ("Rock_02_Summer", KNOBS["road_stone_spacing_cm"],
         ("gravel", "mud", "dusty")),
        ("Grass_01_Summer_03", KNOBS["road_tuft_spacing_cm"],
         ("dusty", "mud")),
        ("GroundCoverRVT_Plank", KNOBS["road_dab_spacing_cm"],
         ("mud_onroad", "dusty_onroad")),
        ("GroundCoverRVT_Rock_05", KNOBS["road_dab_spacing_cm"],
         ("mud_verge",)),
        ("GroundCoverRVT_Rock_04", KNOBS["road_onroad_rock_spacing_cm"],
         ("gravel", "mud", "dusty")),
    )
    out = []
    for token, knob, rank in wanted:
        hits = _spline_samplers_feeding(graph, token)
        if len(hits) != len(rank):
            raise RuntimeError(f"expected {len(rank)} spline samplers feeding "
                               f"'{token}', found {len(hits)}")
        hits.sort(key=lambda h: h[2])  # ASC: smaller spacing = denser stream
        for (_node, s, old), key in zip(hits, rank):
            params = s.get_editor_property("sampler_params")
            params.set_editor_property("distance_increment", float(knob[key]))
            s.set_editor_property("sampler_params", params)
            got = float(s.get_editor_property("sampler_params")
                        .get_editor_property("distance_increment"))
            if abs(got - float(knob[key])) > 1e-3:
                raise RuntimeError(f"{token}/{key}: read-back {got} != {knob[key]}")
            s.modify()
            out.append(f"{token}/{key}: {old} -> {knob[key]}")
    _save(graph, "PCG_OWRoad")
    return out


@step("oak_tier_density")
def oak_tier_density():
    graph = unreal.load_asset(f"{ASSET_DIR}/PCG_OWForest")
    hits = _samplers_feeding(graph, "OakTree")
    if len(hits) != len(OAK_TIER_BASES):
        raise RuntimeError(f"expected {len(OAK_TIER_BASES)} oak tier samplers, "
                           f"found {len(hits)}")
    # Densest saved sampler = heaviest tier; assign bases by rank.
    hits.sort(key=lambda h: -h[2])
    out = []
    for (_node, s, old), base in zip(hits, OAK_TIER_BASES):
        new = base * float(KNOBS["oak_density_scale"])
        s.set_editor_property("points_per_squared_meter", new)
        s.modify()
        out.append(f"{old} -> {new}")
    _save(graph, "PCG_OWForest")
    return out


def _spawners_with(graph, mesh_token):
    """[(node, spawner settings)] whose mesh entries contain mesh_token."""
    nodes = {}
    for edge in graph.get_all_edges():
        for prop in ("input_pin", "output_pin"):
            pin = edge.get_editor_property(prop)
            node = pin.get_editor_property("node") if pin else None
            if node:
                nodes[node.get_name()] = node
    hits = []
    for node in nodes.values():
        s = node.get_editor_property("settings_interface")
        if not isinstance(s, unreal.PCGStaticMeshSpawnerSettings):
            continue
        params = s.get_editor_property("mesh_selector_parameters")
        for e in params.get_editor_property("mesh_entries"):
            mesh = e.get_editor_property("descriptor").get_editor_property("static_mesh")
            if mesh and mesh_token in mesh.get_name():
                hits.append((node, s))
                break
    return hits


@step("oak_wind")
def oak_wind():
    """Patch bEvaluateWorldPositionOffset on every oak spawner mesh entry.
    Struct arrays come back as copies: mutate, set the array back, then
    READ BACK to verify - failed sets are silent."""
    want = bool(KNOBS["oak_wind"])
    graph = unreal.load_asset(f"{ASSET_DIR}/PCG_OWForest")
    spawners = _spawners_with(graph, "OakTree")
    if not spawners:
        raise RuntimeError("no oak spawners found in PCG_OWForest")
    patched = 0
    for _node, s in spawners:
        params = s.get_editor_property("mesh_selector_parameters")
        entries = list(params.get_editor_property("mesh_entries"))
        for e in entries:
            d = e.get_editor_property("descriptor")
            d.set_editor_property("evaluate_world_position_offset", want)
            e.set_editor_property("descriptor", d)
            patched += 1
        params.set_editor_property("mesh_entries", entries)
        s.modify()
        # Read-back verify against the settings object we just wrote.
        for e in params.get_editor_property("mesh_entries"):
            got = bool(e.get_editor_property("descriptor")
                       .get_editor_property("evaluate_world_position_offset"))
            if got != want:
                raise RuntimeError(
                    f"read-back mismatch on {e.get_editor_property('descriptor').get_editor_property('static_mesh')}: "
                    f"wanted {want}, got {got}")
    _save(graph, "PCG_OWForest")
    return f"evaluate_world_position_offset={want} on {patched} mesh entries " \
           f"across {len(spawners)} oak spawners (read-back verified)"


# Graphs this script edits; a PCG actor whose component runs one of them is a biome actor.
TUNED_GRAPHS = ("PCG_OWMeadow", "PCG_OWForest", "PCG_OWRoad")
# Actor labels the source's lab map used for the same actors (kept so the lab labels still match).
BIOME_LABELS = ("DRESSLAB_PCG_Meadow", "DRESSLAB_PCG_Forest", "DRESSLAB_PCG_Road")


@step("refresh")
def refresh():
    """Flush the grass cache, then fire Generate on the biome actors of the
    editor world. No world, or a world with no biome actors (headless: no map
    is loaded), is a clean no-op."""
    unreal.SystemLibrary.execute_console_command(None, "grass.FlushCache")
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    except Exception:
        world = None
    if world is None:
        return "grass cache flushed; no editor world - Generate skipped"
    fired = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        comp = a.get_component_by_class(unreal.PCGComponent)
        if not comp:
            continue
        graph = comp.get_graph()
        if a.get_actor_label() in BIOME_LABELS or (graph and graph.get_name() in TUNED_GRAPHS):
            comp.generate(True)
            fired.append(a.get_actor_label())
    if not fired:
        return f"grass cache flushed; no biome actors in {world.get_name()} - Generate skipped"
    return f"grass cache flushed; Generate fired on {fired}"


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT_PATH}")
unreal.log(f"MEADOWTUNE applied ok={result['ok']} report={REPORT_PATH} - generation is async, give it a few seconds")
