"""Benmore triage (docs/BENMORE_HANDOFF_FOR_GPT.md section 6.1; the owner after driving B2c: "Yes, all off"): Claude's B1/B2 additions
out of L_Benmore_GaeaReview, the code left in git.
- Every AGTDeformZone (B2's 39 gravel zones, 31 mud-road zones, 6 bogs; folder GT_DeformZones) and anything else in that folder.
- M_GC_Terrain through benmore_gt_ground.attach_surfaces: B1's ground detail and scatter grass entries, B2's coverage hole, apron and far
  mud out, Morphology/T_RL_Vegetation back, the gravel parallax switch back on MPC_Benmore_GravelPOM.Enabled; the landscape physical
  material output (the surface types) kept.
Benmore_VehicleSurfaceEffects and the water are not touched. The map is saved only if its file is unchanged since this run loaded it.
Run by Art/benmore_b2.ps1 -Step triage (a -RenderOffScreen editor) -> Art/Export/BenmoreTriage/triage.json. No timing, no tests."""
import json
import sys
import time
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
import benmore_gt_ground as g   # noqa: E402

OUT = ROOT / 'Art/Export/BenmoreTriage'
LEVEL = g.LEVEL
UMAP = ROOT / 'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'
FOLDER = 'GT_DeformZones'
PROPS = ['MP_BASE_COLOR', 'MP_NORMAL', 'MP_ROUGHNESS', 'MP_AMBIENT_OCCLUSION', 'MP_OPACITY_MASK', 'MP_SPECULAR', 'MP_METALLIC', 'MP_EMISSIVE_COLOR']
eal, mel = g.eal, g.mel
report = dict(ok=False, level=LEVEL, timings_collected=False, tests_run=False)


def material(m):
    s = mel.get_statistics(m)
    nodes = list(mel.get_material_expressions(m))
    roots = {}
    for name in PROPS:
        prop = getattr(u.MaterialProperty, name)
        n = mel.get_material_property_input_node(m, prop)
        roots[name] = [n.get_name(), mel.get_material_property_input_node_output_name(m, prop) or ''] if n else [None, '']
    gout = next(e for e in nodes if isinstance(e, u.MaterialExpressionLandscapeGrassOutput))
    tex = set()
    for e in nodes:
        if isinstance(e, (u.MaterialExpressionTextureSample, u.MaterialExpressionTextureObject, u.MaterialExpressionTextureObjectParameter)):
            t = e.get_editor_property('texture')
            if t:
                tex.add(t.get_path_name().split('.')[0])
    return dict(pixel=s.num_pixel_shader_instructions, vertex=s.num_vertex_shader_instructions, samplers=s.num_samplers,
                pixel_texture_samples=s.num_pixel_texture_samples, nodes=len(nodes), roots=roots,
                collections=sorted({'%s.%s' % (e.get_editor_property('collection').get_path_name().split('.')[0], e.get_editor_property('parameter_name'))
                                    for e in nodes if isinstance(e, u.MaterialExpressionCollectionParameter) and e.get_editor_property('collection')}),
                grass=[[str(e.get_editor_property('name')), e.get_editor_property('grass_type').get_name() if e.get_editor_property('grass_type') else None]
                       for e in gout.get_editor_property('grass_types')],
                physical_material_outputs=sum(1 for e in nodes if isinstance(e, u.MaterialExpressionLandscapePhysicalMaterialOutput)),
                claude_nodes=sum(1 for e in nodes if g.desc(e).startswith(('GTGround:', 'GTDeform:'))),
                textures=sorted(t for t in tex if '/DeformZones/' in t or '/GroundDetail/' in t or t.endswith('/T_RL_Vegetation')))


def classes(actors):
    out = {}
    for a in actors:
        k = a.get_class().get_name()
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    world = u.EditorLoadingAndSavingUtils.load_map(LEVEL)
    assert world
    loaded = UMAP.stat().st_mtime
    report['umap_mtime_at_load'] = loaded
    act = u.get_editor_subsystem(u.EditorActorSubsystem)
    actors = list(act.get_all_level_actors())
    report['actor_classes_before'] = classes(actors)
    # 1. The deform zones and anything else B2 put in their folder.
    removed = dict(gravel=0, mud_road=0, bog=0, other_in_folder=[])
    for a in actors:
        if isinstance(a, u.GTDeformZone):
            kind = 'bog' if a.get_editor_property('shape') == u.GTDeformZoneShape.BLOB else ('gravel' if a.get_editor_property('tiled') else 'mud_road')
            removed[kind] += 1
            assert act.destroy_actor(a)
        elif str(a.get_folder_path()).startswith(FOLDER):
            removed['other_in_folder'].append('%s (%s)' % (a.get_actor_label(), a.get_class().get_name()))
            assert act.destroy_actor(a)
    report['removed'] = removed
    left = list(act.get_all_level_actors())
    report['mud_patches_left'] = [a.get_actor_label() for a in left if isinstance(a, u.GTMudPatch)]
    report['zones_left'] = sum(1 for a in left if isinstance(a, u.GTDeformZone))
    report['surface_effects_actors'] = [a.get_actor_label() for a in left if a.get_class().get_name().startswith('GTVehicleSurfaceEffects')]
    # 2-4. The review material: B1's detail and scatter, B2's hole, apron, far mud and vegetation copy out; the surface types kept.
    land = next(a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Landscape))
    m = eal.load_asset(g.TERRAIN_MATERIAL)
    assert land.get_editor_property('landscape_material') == m, 'the review landscape wears another material'
    report['material_before'] = material(m)
    report['attach'] = g.attach_surfaces(m)
    report['material_after'] = material(m)
    after = report['material_after']
    assert after['claude_nodes'] == 3 and after['physical_material_outputs'] == 1, after
    assert not any(n in ('GTSoilScatter', 'GTGrassLitter') for n, _ in after['grass']), after['grass']
    assert after['textures'] == ['/Game/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/T_RL_Vegetation'], after['textures']
    u.SystemLibrary.execute_console_command(world, 'landscape.RebuildPhysicalMaterial')
    u.SystemLibrary.execute_console_command(world, 'grass.FlushCache')
    # The landscape re-renders its physical material on editor ticks once the material's shaders compile (same weights as before).
    t = time.monotonic()
    while time.monotonic() - t < 180.0:
        yield
    report['physical_material_wait_s'] = 180
    now = UMAP.stat().st_mtime
    report['umap_mtime_before_save'] = now
    if now != loaded:
        raise RuntimeError('L_Benmore_GaeaReview changed on disk since this run loaded it: not saved')
    assert u.EditorLoadingAndSavingUtils.save_map(world, LEVEL)
    report['saved'] = True
    report['actor_classes_after'] = classes(act.get_all_level_actors())


def finish(error=None):
    report['ok'] = error is None
    if error:
        report['error'] = error
        u.log_error(error)
    (OUT / 'triage.json').write_text(json.dumps(report, indent=1, default=str))
    u.unregister_slate_post_tick_callback(handle)
    u.SystemLibrary.quit_editor()


u.EditorPythonScripting.set_keep_python_script_alive(True)
gen = run()
busy = False


def tick(dt):
    global busy
    if busy:
        return
    busy = True
    try:
        next(gen)
    except StopIteration:
        finish()
    except Exception:  # noqa: BLE001
        finish(traceback.format_exc())
    finally:
        busy = False


handle = u.register_slate_post_tick_callback(tick)
