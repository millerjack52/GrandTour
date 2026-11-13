"""Mud and water MW1 (docs/MUD_WATER_SURFACE_PLAN.md items 2 and 3): M_GT_Mud and M_GT_MudWater from Art/Unreal/live_mud_style.py,
MPC_TrackPaint's MudDeformDetail / MudWaterMotion, and the water rings - T_GT_WaterRings (Art/Blender/build_water_rings.py's
painted atlas), M_GT_WaterRing and NS_GT_WaterRings (UGTNiagaraSetupLibrary::BuildWaterRings, every input write guarded).

Only these: the landscape materials, the clods and the strips' levels are not touched (live_mud_style.apply_existing does those;
GR2 owns the strips' setups). Run with & Art/setup_mud_water.ps1 (a full editor, -RenderOffScreen: the materials and the Niagara
script compile for real). The static shader statistics of the three materials (instructions, samplers; not timing) before and
after. Writes Art/Export/MudWater/setup-report.json.

M_GT_WaterRing: translucent, lit per pixel (the sky and the sun on the rings, nothing glowing at night), Niagara sprites, two-sided.
The atlas cell from Particle Random (2 x 2); the shade R lerps RingDark .. RingLight (the trough, the crest); the opacity A x
RingOpacity 0.9 x the fade in over the first 6 % of the life and out as (1 - age)^1.2, x a 4 cm depth fade (no hard cut where a ring
meets a bank); roughness RingRough 0.25, specular 0.25 (water's F0 0.02). Proposed numbers; the owner names them.
"""
import sys, json, traceback
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
OUT = ROOT / 'Art/Export/MudWater'
FX = '/Game/GrandTour/FX'
TEX = FX + '/Textures'
eal = u.EditorAssetLibrary
mel = u.MaterialEditingLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
report = {'ok': False}
RING_SCALARS = {'RingOpacity': 0.9, 'RingRough': 0.25, 'RingDepthFadeCm': 4.0}
RING_VECTORS = {'RingDark': (0.018, 0.016, 0.013), 'RingLight': (0.30, 0.31, 0.32)}
RING_HLSL = '''// MW1: the ring atlas cell from the particle's random number (2 x 2, row 0 at the top), the shade and the coverage.
float f=floor(saturate(Rand)*3.999);
float2 cell=float2(fmod(f,2.0),floor(f*0.5));
float4 t=Texture2DSample(Atlas,AtlasSampler,(saturate(UV)+cell)*0.5);
float age=saturate(Age);
Col=lerp(Dark.rgb,Light.rgb,saturate(t.r));
return t.a*Opacity*smoothstep(0.0,0.06,age)*pow(1.0-age,1.2);
'''
MATERIALS = ['/Game/GrandTour/Materials/M_GT_Mud', '/Game/GrandTour/Materials/M_GT_MudWater', FX + '/M_GT_WaterRing']


def stats(tag):
    rows = []
    for path in MATERIALS:
        mat = eal.load_asset(path) if eal.does_asset_exist(path) else None
        if mat is None:
            rows.append(dict(material=path, missing=True))
            continue
        s = mel.get_statistics(mat)
        rows.append(dict(material=path, pixel_instructions=s.num_pixel_shader_instructions, vertex_instructions=s.num_vertex_shader_instructions,
                         samplers=s.num_samplers, pixel_texture_samples=s.num_pixel_texture_samples))
    report['shader_stats_' + tag] = rows


def ring_texture():
    task = u.AssetImportTask()
    task.filename = str(OUT / 'T_GT_WaterRings.png')
    task.destination_path = TEX
    task.destination_name = 'T_GT_WaterRings'
    task.automated = True
    task.replace_existing = True
    task.save = True
    assets.import_asset_tasks([task])
    tex = eal.load_asset(TEX + '/T_GT_WaterRings')
    assert tex, 'T_GT_WaterRings did not import (run Art/Blender/build_water_rings.py first)'
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_BC7)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_EFFECTS)
    eal.save_loaded_asset(tex)
    report['ring_texture'] = dict(asset=tex.get_path_name(), size=[tex.blueprint_get_size_x(), tex.blueprint_get_size_y()], srgb=False, compression='BC7')
    return tex


def ring_material(tex):
    name = 'M_GT_WaterRing'
    path = FX + '/' + name
    mat = eal.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset(name, FX, u.Material, u.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('used_with_niagara_sprites', True)
    node = mel.create_material_expression(mat, u.MaterialExpressionCustom, -300, 0)
    node.set_editor_property('desc', 'Water ring (MW1)')
    node.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    slots = []
    for n in ['Atlas', 'UV', 'Rand', 'Age', 'Dark', 'Light', 'Opacity']:
        c = u.CustomInput()
        c.set_editor_property('input_name', n)
        slots.append(c)
    node.set_editor_property('inputs', slots)
    o = u.CustomOutput()
    o.set_editor_property('output_name', 'Col')
    o.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    node.set_editor_property('additional_outputs', [o])
    node.set_editor_property('code', RING_HLSL)
    t = mel.create_material_expression(mat, u.MaterialExpressionTextureObjectParameter, -900, -200)
    t.set_editor_property('parameter_name', 'Atlas')
    t.set_editor_property('texture', tex)
    t.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    assert mel.connect_material_expressions(t, '', node, 'Atlas')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionTextureCoordinate, -900, 0), '', node, 'UV')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionParticleRandom, -900, 100), '', node, 'Rand')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionParticleRelativeTime, -900, 200), '', node, 'Age')
    y = 300
    for n, v in RING_VECTORS.items():
        e = mel.create_material_expression(mat, u.MaterialExpressionVectorParameter, -900, y)
        e.set_editor_property('parameter_name', n)
        e.set_editor_property('default_value', u.LinearColor(v[0], v[1], v[2], 1.0))
        assert mel.connect_material_expressions(e, '', node, 'Dark' if n == 'RingDark' else 'Light')
        y += 120
    op = mel.create_material_expression(mat, u.MaterialExpressionScalarParameter, -900, y)
    op.set_editor_property('parameter_name', 'RingOpacity')
    op.set_editor_property('default_value', RING_SCALARS['RingOpacity'])
    assert mel.connect_material_expressions(op, '', node, 'Opacity')
    fade = mel.create_material_expression(mat, u.MaterialExpressionDepthFade, -100, 100)
    fade.set_editor_property('fade_distance_default', RING_SCALARS['RingDepthFadeCm'])
    assert mel.connect_material_expressions(node, '', fade, 'Opacity')
    assert mel.connect_material_property(node, 'Col', u.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    rough = mel.create_material_expression(mat, u.MaterialExpressionScalarParameter, -300, 300)
    rough.set_editor_property('parameter_name', 'RingRough')
    rough.set_editor_property('default_value', RING_SCALARS['RingRough'])
    assert mel.connect_material_property(rough, '', u.MaterialProperty.MP_ROUGHNESS)
    spec = mel.create_material_expression(mat, u.MaterialExpressionConstant, -300, 400)
    spec.set_editor_property('r', 0.25)
    assert mel.connect_material_property(spec, '', u.MaterialProperty.MP_SPECULAR)
    errors = [str(e) for e in mel.recompile_material(mat)]
    eal.save_loaded_asset(mat)
    report['ring_material'] = dict(asset=mat.get_path_name(), scalars=RING_SCALARS, vectors=RING_VECTORS, compile_errors=errors)
    assert not errors, errors
    return mat


try:
    import live_mud_style as lms
    stats('before')
    report['mpc'] = lms.ensure_patch_variants()
    report['mud'] = lms.attach(eal.load_asset('/Game/GrandTour/Materials/M_GT_Mud'), False)
    report['water'] = lms.muddy_water(eal.load_asset('/Game/GrandTour/Materials/M_GT_MudWater'))
    report['mw1_mud_scalars'] = lms.MW1_MUD_SCALARS
    report['mw1_water_scalars'] = lms.MW1_WATER_SCALARS
    report['lm1_scalars'] = lms.LM1_SCALARS
    tex = ring_texture()
    mat = ring_material(tex)
    # NS_GT_WaterRings: built on a fresh package (the wrapper deletes the old file before the editor starts: a system built over
    # an existing package crashed every later load, WHEEL_SPRAY 2026-10-10).
    log = u.GTNiagaraSetupLibrary.build_water_rings(FX, 'NS_GT_WaterRings', mat)
    report['niagara_log'] = log.splitlines()
    system = eal.load_asset(FX + '/NS_GT_WaterRings')
    report['niagara_saved'] = bool(system) and eal.save_loaded_asset(system)
    stats('after')
    report['ok'] = 'BUILD OK' in log and report['niagara_saved']
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'setup-report.json').write_text(json.dumps(report, indent=2, default=str))
u.SystemLibrary.quit_editor()
