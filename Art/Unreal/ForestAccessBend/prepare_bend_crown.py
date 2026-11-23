"""Rebake the four existing far-card views from the locally regrouped tree."""
import json
import math
import struct
import sys
import traceback
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import bend_crown as crown
from benmore_river_life_materials import props

out = crown.ROOT / 'Saved/ForestAccessBend'
receipt = out / 'broadleaf-prepared.json'
source_family = crown.BASE + '/FloraWorld'
far_name = 'M_BendBroadleafFar'
assets = u.EditorAssetLibrary
actors = u.get_editor_subsystem(u.EditorActorSubsystem)


def import_atlas(name, data, original):
    tga = out / (name + '.tga')
    tga.write_bytes(struct.pack('<BBBHHBHHHHBB', 0,0,2,0,0,0,0,0,2048,512,32,40) + data)
    task = props(u.AssetImportTask(), filename=str(tga), destination_path=crown.FOLDER,
                 destination_name=name, automated=True, replace_existing=True, save=True)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = u.load_asset(crown.FOLDER + '/' + name)
    for setting in ('srgb', 'compression_settings', 'mip_gen_settings', 'filter', 'power_of_two_mode',
                    'address_x', 'address_y', 'do_scale_mips_for_alpha_coverage', 'alpha_coverage_thresholds'):
        texture.set_editor_property(setting, original.get_editor_property(setting))
    assert assets.save_loaded_asset(texture, False)
    return texture


def prepare():
    source = u.load_asset(crown.ORIGINAL)
    tree, islands = crown.make_geometry(source)
    source_mesh = u.load_asset('/Game/GrandTour/ArtTests/FloraPath/SM_Path_FP_Tree_D_003')
    bounds = source_mesh.get_bounds()
    size = max(bounds.box_extent.to_tuple()) * 2.12
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    tree_actor = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(0, 0, -100000))
    capture = actors.spawn_actor_from_class(u.SceneCapture2D, tree_actor.get_actor_location())
    component = tree_actor.static_mesh_component
    component.set_static_mesh(tree)
    component.set_forced_lod_model(1)
    for slot in (0, 1):
        mat = u.load_asset(source_family + '/BakeMaterials/' + source_mesh.get_material(slot).get_name())
        assert mat
        component.set_material(slot, mat)
    rt = u.RenderingLibrary.create_render_target2d(world, 512, 512, u.TextureRenderTargetFormat.RTF_RGBA16F)
    camera = props(capture.capture_component2d, texture_target=rt, capture_every_frame=False,
                   capture_on_movement=False, projection_type=u.CameraProjectionMode.ORTHOGRAPHIC,
                   ortho_width=size, primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
    camera.show_only_component(component)
    for _ in range(30):
        yield
    rgba = bytearray(2048*512*4)
    normals = bytearray(len(rgba))
    occupancy = []
    for view in range(4):
        angle = math.radians(60*view)
        direction = u.Vector(0,0,1) if view == 3 else u.Vector(math.cos(angle),math.sin(angle),0)
        centre = tree_actor.get_actor_location() + bounds.origin
        eye = centre + direction*size*2
        capture.set_actor_location_and_rotation(eye, u.MathLibrary.find_look_at_rotation(eye, centre), False, True)
        passes = []
        for mode in (u.SceneCaptureSource.SCS_BASE_COLOR, u.SceneCaptureSource.SCS_SCENE_COLOR_HDR, u.SceneCaptureSource.SCS_NORMAL):
            camera.set_editor_property('capture_source', mode)
            camera.capture_scene()
            for _ in range(3):
                yield
            passes.append(u.RenderingLibrary.read_render_target_raw_pixel_area(world, rt, 0, 0, 512, 512, False))
        assert all(len(p) == 512*512 for p in passes)
        covered = 0
        for i, (c, a, n) in enumerate(zip(*passes)):
            mask = round(255*max(0., min(1., 1-a.a)))
            covered += mask > 127
            offset = ((i//512)*2048 + view*512 + i%512)*4
            rgba[offset:offset+4] = bytes([round(255*max(0., min(1., v))**(1/2.2)) for v in (c.b,c.g,c.r)] + [mask])
            normals[offset:offset+4] = bytes([round(255*max(0., min(1., .5+.5*v))) for v in (n.b,n.g,n.r)] + [mask])
        assert 1000 < covered < 512*512*.8, (view, covered)
        occupancy.append(covered)
    actors.destroy_actor(capture)
    actors.destroy_actor(tree_actor)
    # The installed map uses a locally adapted far material. Retain its shading graph.
    template_path = next(str(d.package_name) for d in u.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(
        crown.BASE, True) if str(d.asset_name) == 'M_FirFar_1_7f3a4a16')
    dest = crown.FOLDER + '/' + far_name
    far = u.load_asset(dest) if assets.does_asset_exist(dest) else assets.duplicate_asset(template_path, dest)
    edits = {}
    for n in u.MaterialEditingLibrary.get_material_expressions(far):
        if not isinstance(n, u.MaterialExpressionTextureSample):
            continue
        old = n.get_editor_property('texture')
        if old is None:
            continue
        for stem, name, pixels in [('FirAtlas','T_BendBroadleafColour',rgba), ('FirNormal','T_BendBroadleafNormals',normals)]:
            if old.get_name() in ('T_'+stem+'_1',name):
                orig = u.load_asset(source_family+'/Canopy/T_'+stem+'_1')
                if name not in edits:
                    edits[name] = import_atlas(name, pixels, orig)
                n.set_editor_property('texture', edits[name])
    assert len(edits) == 2, edits
    assert not u.MaterialEditingLibrary.recompile_material(far)
    assert assets.save_loaded_asset(far, False)
    assets.set_metadata_tag(tree, 'ForestAccessTufts', crown.VERSION)
    assert assets.save_loaded_asset(tree, False)
    receipt.write_text(json.dumps(dict(ok=True, version=crown.VERSION, mesh=crown.VARIANT,
        far=dest, source=crown.ORIGINAL, old_far=template_path, leaf_islands=islands,
        lod_triangles=[tree.get_num_triangles(i) for i in range(4)], covered_texels=occupancy), indent=2))


steps = prepare()
def advance(_):
    if steps.gi_running:
        return
    try:
        next(steps)
    except StopIteration:
        u.unregister_slate_post_tick_callback(handle)
        u.SystemLibrary.quit_editor()
    except Exception:
        receipt.write_text(json.dumps(dict(ok=False, error=traceback.format_exc()), indent=2))
        u.unregister_slate_post_tick_callback(handle)
        u.SystemLibrary.quit_editor()
handle = u.register_slate_post_tick_callback(advance)
