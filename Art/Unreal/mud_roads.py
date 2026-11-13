"""Mud roads MRD1 (docs/MUD_ROADS_PLAN.md): the strips' MudRoad section profile and the debris branches' import, shared by
setup_mud_variants.py (its Standard section becomes a MudRoad) and setup_live_mud_drive.py (a 60 m MudRoad section).

road_deform(): a bog section's Deform as ground_relief.bog_deform() (Mode ByKind, the variant's feel, PreChurnScale 1) with
  PreChurnStyle Braided (AGTMudPatch::PreChurnBraided: 6-14 braided old tracks, power-law depths, torn walls, puddles in the low runs,
  churn zones with clod fields, partial old tread), MudRoadSprayScale 2 (item 4: the number only - Benmore B1b's spray code reads it)
  and RoadDebrisPerM2 0.05
  (item 3: 0.03-0.08 a m^2, clustered); MRD1b item 3's silt surface, RoadSiltTileMul 2 and RoadSiltStrength 0.4.
ROAD_WATER_TABLE_CM: the MudRoad sections' water table (-10 cm; the bog's -25 lies under the road's tracks).
import_branches(): Art/Export/MudRoads/SM_MRD_Branch0-1.fbx (Art/Blender/build_road_branches.py) into
  /Game/GrandTour/ArtTests/MudRoads, wearing GR2's MI_GD_Twig (read, not edited), no collision, no Nanite. Repeatable.
"""
import json
from pathlib import Path

import unreal as u

import ground_relief

ROOT = Path(u.Paths.project_dir()).resolve()
SRC = ROOT / 'Art/Export/MudRoads'
DEST = '/Game/GrandTour/ArtTests/MudRoads'
TWIG_MATERIAL = '/Game/GrandTour/ArtTests/GroundDetail/MI_GD_Twig'
SPRAY_SCALE = 2.0
DEBRIS_PER_M2 = 0.05
# MRD1b item 3, the silt surface: the bog bake 2x finer, its lump normal, AO and parallax x0.4 on the running surface.
SILT_TILE_MUL = 2.0
SILT_STRENGTH = 0.4
# The MudRoad section's water table (FGTRouteSection::WaterTableCm), cm. The bog's -25 cm sits under almost every old track of a
# road (the braided tracks settle to a median of about 4 cm and a 90th percentile of about 12 cm): the first capture found 0.0 % of
# the road under it with one basin cut (GR2's 30 deg basin walls cannot reach -25 cm inside a track), so item 1's puddles stand at
# -10 cm on a road - the deepest runs settle under it and are cut 1-5 cm below it. A decision for the main session to confirm.
ROAD_WATER_TABLE_CM = -10.0
eal = u.EditorAssetLibrary


def road_deform():
    """A MudRoad section's Deform (see the module's note)."""
    d = ground_relief.bog_deform()
    d.set_editor_property('pre_churn_style', u.GTPreChurnStyle.BRAIDED)
    d.set_editor_property('mud_road_spray_scale', SPRAY_SCALE)
    d.set_editor_property('road_debris_per_m2', DEBRIS_PER_M2)
    d.set_editor_property('road_silt_tile_mul', SILT_TILE_MUL)   # MRD1b item 3
    d.set_editor_property('road_silt_strength', SILT_STRENGTH)
    return d


def import_branches():
    manifest = json.loads((SRC / 'manifest.json').read_text())
    assets = u.AssetToolsHelpers.get_asset_tools()
    sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    material = eal.load_asset(TWIG_MATERIAL)
    rows = []
    for row in manifest['branches']:
        name = row['name']
        task = u.AssetImportTask()
        task.filename = str(ROOT / row['fbx'])
        task.destination_path = DEST
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        opt = u.FbxImportUI()
        opt.import_mesh = True
        opt.import_as_skeletal = False
        opt.import_materials = False
        opt.import_textures = False
        opt.import_animations = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        data = opt.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options = opt
        assets.import_asset_tasks([task])
        mesh = eal.load_asset(DEST + '/' + name)
        assert mesh, 'the import made no ' + name
        if material:
            mesh.set_material(0, material)
        ns = mesh.get_editor_property('nanite_settings')
        ns.enabled = False
        sm.set_nanite_settings(mesh, ns, True)
        try:
            sm.remove_collisions(mesh)
        except Exception:   # noqa: BLE001
            pass
        eal.save_loaded_asset(mesh)
        box = mesh.get_bounding_box()
        rows.append(dict(name=name, asset=mesh.get_path_name(), triangles=row['triangles'], length_cm=row['length_cm'],
                         size_cm=[round(box.max.x - box.min.x, 1), round(box.max.y - box.min.y, 1), round(box.max.z - box.min.z, 1)],
                         material=material.get_path_name() if material else None))
    return rows
