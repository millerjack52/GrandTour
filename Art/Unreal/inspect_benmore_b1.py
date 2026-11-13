"""Benmore integration B1 item 1 (docs/BENMORE_INTEGRATION_PLAN.md B1): a read-only inventory of L_Benmore_GaeaReview - the landscape's
layers and weights, its material (graph roots, collections, grass output, static shader counts), the grass types, the road and Gaea
mask textures, the terrain builders, the review cameras and the surface physical materials. Saves nothing.
Run in a -RenderOffScreen editor (shader counts need HLSL): Art/benmore_b1.ps1 -Step inspect. Writes Art/Export/BenmoreB1/inventory.json."""
import json
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/BenmoreB1'
OUT.mkdir(parents=True, exist_ok=True)
LEVEL = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
mel = u.MaterialEditingLibrary
eal = u.EditorAssetLibrary
report = dict(ok=False, level=LEVEL, read_only=True)


def safe(fn, default=None):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return default if default is not None else 'ERR %s' % str(e)[:160]


def pyval(v):
    if isinstance(v, (bool, int, float, str)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [pyval(x) for x in v]
    if isinstance(v, u.Object):
        return v.get_path_name()
    if isinstance(v, u.FloatInterval):
        return [v.min, v.max]
    if isinstance(v, (u.PerPlatformFloat, u.PerPlatformInt)):
        return safe(lambda: v.get_editor_property('default'), str(v))
    return str(v)


def struct_dump(s):
    out = {}
    for name in dir(s):
        if name.startswith('_') or name in ('cast', 'copy', 'static_struct', 'export_text', 'import_text', 'assign', 'to_tuple'):
            continue
        try:
            val = getattr(s, name)
        except Exception:  # noqa: BLE001
            continue
        if callable(val):
            continue
        out[name] = pyval(val)
    return out


def material_stats(m):
    s = mel.get_statistics(m)
    return dict(pixel=s.num_pixel_shader_instructions, vertex=s.num_vertex_shader_instructions, samplers=s.num_samplers,
                pixel_texture_samples=s.num_pixel_texture_samples, vertex_texture_samples=s.num_vertex_texture_samples,
                interpolator_scalars=s.num_interpolator_scalars)


def collections_of(m):
    found = set()
    for n in mel.get_material_expressions(m):
        if isinstance(n, u.MaterialExpressionCollectionParameter):
            c = n.get_editor_property('collection')
            found.add(c.get_path_name() if c else None)
    return sorted(x for x in found if x)


try:
    world = u.EditorLoadingAndSavingUtils.load_map(LEVEL)
    assert world
    actors = list(u.GameplayStatics.get_all_actors_of_class(world, u.Actor))
    # ---------------------------------------------------------------- the landscape
    lands = []
    for a in actors:
        if not isinstance(a, u.LandscapeProxy):
            continue
        row = dict(label=a.get_actor_label(), cls=a.get_class().get_name(), location=pyval(a.get_actor_location().to_tuple()),
                   scale=pyval(a.get_actor_scale3d().to_tuple()))
        for key in ('landscape_material', 'default_phys_material', 'collision_mip_level', 'simple_collision_mip_level', 'component_size_quads',
                    'subsection_size_quads', 'num_subsections', 'use_dynamic_material_instance', 'b_use_dynamic_material_instance'):
            row[key] = safe(lambda key=key: pyval(a.get_editor_property(key)))
        layers = {}
        for name, setting in safe(lambda: dict(a.get_editor_property('target_layers')), {}).items():
            info = setting.get_editor_property('layer_info_obj')
            layers[str(name)] = dict(info=pyval(info), phys=safe(lambda info=info: pyval(info.get_editor_property('phys_material'))) if info else None,
                                     no_weight_blend=safe(lambda info=info: info.get_editor_property('no_weight_blend')) if info else None)
        row['target_layers'] = layers
        comps = list(a.get_components_by_class(u.LandscapeComponent))
        row['components'] = len(comps)
        # Paint weights per layer on a 16 x 16 grid over the landscape (the editor API; 0 everywhere = an unpainted layer).
        weights = {}
        infos = {n: eal.load_asset(v['info'].split('.')[0]) for n, v in layers.items() if isinstance(v['info'], str)}
        quads = row['component_size_quads'] if isinstance(row['component_size_quads'], int) else 0
        span = quads * a.get_actor_scale3d().x
        origins = [(c, c.get_world_location()) for c in comps]
        for n, info in infos.items():
            vals = []
            for i in range(16):
                for j in range(16):
                    x = -124000 + 248000 * (i + 0.5) / 16
                    y = -124000 + 248000 * (j + 0.5) / 16
                    loc = u.Vector(x, y, 0)
                    w = None
                    for c, o in origins:
                        if 0 <= x - o.x < span and 0 <= y - o.y < span:
                            w = safe(lambda c=c, loc=loc, info=info: c.editor_get_paint_layer_weight_at_location(loc, info))
                            break
                    vals.append(w)
            nums = [v for v in vals if isinstance(v, (int, float))]
            weights[n] = dict(samples=len(vals), numeric=len(nums), mean=(sum(nums) / len(nums)) if nums else None,
                              nonzero=sum(1 for v in nums if v > 0.01), first_err=next((v for v in vals if isinstance(v, str)), None))
        row['layer_weights_16x16'] = weights
        lands.append(row)
    report['landscapes'] = lands
    # ---------------------------------------------------------------- the material
    land = next(a for a in actors if isinstance(a, u.Landscape))
    m = land.get_editor_property('landscape_material')
    mat = dict(path=m.get_path_name(), cls=m.get_class().get_name())
    base = m
    chain = []
    while isinstance(base, u.MaterialInstance):
        chain.append(base.get_path_name())
        base = base.get_editor_property('parent')
    mat['instance_chain'] = chain
    mat['base'] = base.get_path_name()
    for key in ('blend_mode', 'shading_model', 'tangent_space_normal', 'two_sided', 'used_with_instanced_static_meshes', 'opacity_mask_clip_value'):
        mat[key] = safe(lambda key=key: pyval(base.get_editor_property(key)))
    mat['collections'] = collections_of(base)
    mat['stats'] = safe(lambda: material_stats(base))
    mat['roots'] = {}
    for key in ('MP_BASE_COLOR', 'MP_NORMAL', 'MP_ROUGHNESS', 'MP_AMBIENT_OCCLUSION', 'MP_OPACITY_MASK', 'MP_SPECULAR', 'MP_METALLIC', 'MP_EMISSIVE_COLOR'):
        n = mel.get_material_property_input_node(base, getattr(u.MaterialProperty, key))
        out = safe(lambda key=key: mel.get_material_property_input_node_output_name(base, getattr(u.MaterialProperty, key)))
        mat['roots'][key] = [n.get_name() if n else None, pyval(out)]
    nodes = list(mel.get_material_expressions(base))
    mat['node_count'] = len(nodes)
    kinds = {}
    for n in nodes:
        k = n.get_class().get_name()
        kinds[k] = kinds.get(k, 0) + 1
    mat['node_kinds'] = kinds
    grass = []
    for n in nodes:
        if isinstance(n, u.MaterialExpressionLandscapeGrassOutput):
            ins = list(mel.get_inputs_for_material_expression(base, n))
            for idx, gi in enumerate(n.get_editor_property('grass_types')):
                name = str(gi.get_editor_property('name'))
                gt = gi.get_editor_property('grass_type')
                src = ins[idx] if idx < len(ins) else None
                outname = safe(lambda name=name: pyval(mel.get_input_node_output_name_for_material_expression(n, name)))
                row = dict(input=name, grass_type=pyval(gt), source=src.get_name() if src else None, source_out=outname,
                           source_tex=pyval(src.get_editor_property('texture')) if isinstance(src, u.MaterialExpressionTextureSample) else None)
                if gt:
                    row['scalability'] = safe(lambda gt=gt: pyval(gt.get_editor_property('enable_density_scaling')))
                    row['varieties'] = [struct_dump(v) for v in gt.get_editor_property('grass_varieties')]
                grass.append(row)
    mat['grass'] = grass
    mat['textures'] = sorted({pyval(n.get_editor_property('texture')) for n in nodes
                              if isinstance(n, (u.MaterialExpressionTextureSample, u.MaterialExpressionTextureObject)) and n.get_editor_property('texture')})
    report['material'] = mat
    # The strips' landscape copies: their collections (the two-per-material limit).
    report['strip_collections'] = {p: safe(lambda p=p: collections_of(eal.load_asset(p))) for p in
                                   ['/Game/GrandTour/ArtTests/MudVariants/M_VariantsLandscape', '/Game/GrandTour/ArtTests/LiveMudDrive/M_LiveLandscape',
                                    '/Game/GrandTour/ArtTests/DeformableGravel/M_GravelLandscape', '/Game/GrandTour/Materials/M_GT_Landscape']}
    # ---------------------------------------------------------------- actors
    by_class = {}
    for a in actors:
        k = a.get_class().get_name()
        by_class[k] = by_class.get(k, 0) + 1
    report['actor_classes'] = by_class
    report['cameras'] = [dict(label=a.get_actor_label(), loc=pyval(a.get_actor_location().to_tuple()), rot=pyval(a.get_actor_rotation().to_tuple()))
                         for a in actors if isinstance(a, u.CameraActor)]
    report['road_actors'] = []
    for a in actors:
        lab = a.get_actor_label()
        if any(k in lab.lower() for k in ('road', 'verge', 'gravel', 'route', 'spline')):
            ism = sum(c.get_instance_count() for c in a.get_components_by_class(u.InstancedStaticMeshComponent))
            splines = len(list(a.get_components_by_class(u.SplineComponent)))
            report['road_actors'].append(dict(label=lab, cls=a.get_class().get_name(), instances=ism, splines=splines))
    builders = []
    for a in actors:
        if a.get_class().get_name() == 'GTTerrainBuilder':
            spec_asset = safe(lambda a=a: a.get_editor_property('spec_asset'))
            row = dict(label=a.get_actor_label(), spec_asset=pyval(spec_asset))
            if isinstance(spec_asset, u.Object):
                spec = spec_asset.get_editor_property('spec')
                secs = list(spec.get_editor_property('sections'))
                row['sections'] = len(secs)
                row['section_rows'] = [safe(lambda s=s: {k: pyval(s.get_editor_property(k)) for k in ('name', 'kind', 'medium', 'start_cm', 'end_cm', 'surface')}) for s in secs[:12]]
            builders.append(row)
    report['terrain_builders'] = builders
    report['sky'] = [a.get_actor_label() for a in actors if a.get_class().get_name() in ('SkyAtmosphere', 'DirectionalLight', 'SkyLight', 'ExponentialHeightFog')]
    # ---------------------------------------------------------------- mask textures
    tex = []
    for folder in ['/Game/GrandTour/Demo/BenmoreRoads/Gaea', '/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface', '/Game/GrandTour/Demo/BenmoreRoads']:
        for p in eal.list_assets(folder, recursive=(folder.endswith('Gaea')), include_folder=False):
            if '/T_' not in p:
                continue
            t = eal.load_asset(p)
            if isinstance(t, u.Texture2D):
                tex.append(dict(path=p.split('.')[0], size=[t.blueprint_get_size_x(), t.blueprint_get_size_y()],
                                srgb=safe(lambda t=t: t.get_editor_property('srgb')), compression=safe(lambda t=t: str(t.get_editor_property('compression_settings')))))
    report['textures'] = tex
    # ---------------------------------------------------------------- surfaces
    surf = {}
    for p in ['/Game/GrandTour/Terrain/Surfaces/PM_Dirt', '/Game/GrandTour/Terrain/Surfaces/PM_Mud', '/Game/GrandTour/Terrain/Surfaces/PM_Bog',
              '/Game/GrandTour/Terrain/Surfaces/PM_Tarmac', '/Game/GrandTour/Demo/BenmoreRoads/Gaea/PM_Benmore_FirmGround']:
        pm = eal.load_asset(p)
        if not pm:
            surf[p] = None
            continue
        row = {k: safe(lambda k=k: pyval(pm.get_editor_property(k))) for k in
               ('friction', 'static_friction', 'restitution', 'surface_type', 'wet_friction_scale', 'wet_rolling_resistance_scale', 'wet_sinkage_scale',
                'rolling_resistance', 'sinkage_rate', 'max_sinkage', 'sinkage_drag_scale', 'plough_drag', 'sinkage_grip_loss', 'track_depth')}
        row['tag'] = safe(lambda: str(pm.get_editor_property('surface_tag')))
        surf[p] = row
    report['surfaces'] = surf
    report['mpcs'] = {}
    for p in ['/Game/GrandTour/Terrain/MPC_TrackPaint', '/Game/GrandTour/Materials/MPC_Weather', '/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/MPC_Benmore_GravelPOM']:
        c = eal.load_asset(p)
        report['mpcs'][p] = dict(scalars=[str(s.get_editor_property('parameter_name')) for s in c.get_editor_property('scalar_parameters')],
                                 vectors=[str(s.get_editor_property('parameter_name')) for s in c.get_editor_property('vector_parameters')]) if c else None
    report['ok'] = True
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'inventory.json').write_text(json.dumps(report, indent=1))
    u.SystemLibrary.quit_editor()
