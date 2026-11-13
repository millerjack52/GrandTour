"""Wheel spray P2 (docs/WHEEL_SPRAY_PLAN.md P2 items 1, 2 and 4): the painterly spray's assets, headless.

Run with & Art/setup_wheel_spray.ps1 (a full editor, -RenderOffScreen, so the sprite materials and the Niagara GPU scripts compile
for real). From Art/Export/WheelSpray (Art/Blender/build_spray_assets.py):
- the three atlases as /Game/GrandTour/FX/Textures/T_GT_SprayMud, T_GT_SprayGrit (RGBA, linear, BC7) and T_GT_SprayDust (grey,
  linear);
- the eight P1b clumps as /Game/GrandTour/FX/Clumps/SM_GT_SprayClump_0..7 (no collision, Nanite off, the FBX's normals);
- the sprite materials /Game/GrandTour/FX/M_GT_SprayMud (masked at 0.33, lit, roughness 0.5, the frame from Particle Random, a
  normal from R), M_GT_SprayGrit (masked, lit, the particle colour x the facet shade R x 0.9-1.1 by the chip's G) and
  M_GT_SprayDust (translucent, lit per pixel, base colour DustTint x DustLit 0.7 and an emissive floor DustTint x DustFloor 1.4
  from MPC_GT_Spray (Benmore B1c: display-referred under daylight exposures, x DustFloorDisplay; DUST_FLOOR_HLSL), the flipbook by Particle Relative Time with the frames blended, at most 0.5 opaque, a 60 cm
  depth fade so the big puffs never cut a line into the ground);
- M_GT_SprayClump on the clods' builder (live_mud_style.build_clod_material, spray=True: wet, the slice from per-instance custom
  data 0, ClodScaleCm 25), put on the clumps;
- /Game/GrandTour/FX/NS_GT_WheelSpray from UGTNiagaraSetupLibrary::BuildWheelSpray (every input write guarded).
Writes Art/Export/WheelSpray/setup-report.json.
"""
import sys, json, traceback
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
SRC = ROOT / 'Art/Export/WheelSpray'
FX = '/Game/GrandTour/FX'
TEX = FX + '/Textures'
CLUMPS = FX + '/Clumps'
eal = u.EditorAssetLibrary
mel = u.MaterialEditingLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
report = {'ok': False}


def import_file(path, dest, name, options=None):
    task = u.AssetImportTask()
    task.filename = str(path)
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options:
        task.options = options
    assets.import_asset_tasks([task])
    asset = eal.load_asset(dest + '/' + name)
    assert asset, name
    return asset


def textures():
    out = {}
    for name, comp in (('T_GT_SprayMud', u.TextureCompressionSettings.TC_BC7), ('T_GT_SprayGrit', u.TextureCompressionSettings.TC_BC7),
                       ('T_GT_SprayDust', u.TextureCompressionSettings.TC_GRAYSCALE)):
        tex = import_file(SRC / (name + '.png'), TEX, name)
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('compression_settings', comp)
        tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_EFFECTS)
        eal.save_loaded_asset(tex)
        out[name] = tex
    report['textures'] = {k: dict(asset=v.get_path_name(), size=[v.blueprint_get_size_x(), v.blueprint_get_size_y()], srgb=False,
                                  compression=str(v.get_editor_property('compression_settings'))) for k, v in out.items()}
    return out


def clumps():
    data = json.loads((SRC / 'manifest.json').read_text())['clumps']['rows']
    rows = []
    for row in data:
        opt = u.FbxImportUI()
        opt.import_mesh = True
        opt.import_as_skeletal = False
        opt.import_materials = False
        opt.import_textures = False
        opt.import_animations = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        opt.static_mesh_import_data.combine_meshes = True
        opt.static_mesh_import_data.auto_generate_collision = False
        opt.static_mesh_import_data.generate_lightmap_u_vs = False
        opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        mesh = import_file(SRC / (row['name'] + '.fbx'), CLUMPS, row['name'], opt)
        b = mesh.get_bounding_box()
        rows.append(dict(asset=mesh.get_path_name(), family=row['family'], triangles=row['triangles'],
                         size_cm=[round(b.max.x - b.min.x, 2), round(b.max.y - b.min.y, 2), round(b.max.z - b.min.z, 2)]))
    report['clumps'] = rows


def custom_node(mat, x, y, desc, inputs, code, out_type, extra=()):
    node = mel.create_material_expression(mat, u.MaterialExpressionCustom, x, y)
    node.set_editor_property('desc', desc)
    node.set_editor_property('output_type', out_type)
    slots = []
    for name in inputs:
        s = u.CustomInput()
        s.set_editor_property('input_name', name)
        slots.append(s)
    node.set_editor_property('inputs', slots)
    outs = []
    for name, kind in extra:
        o = u.CustomOutput()
        o.set_editor_property('output_name', name)
        o.set_editor_property('output_type', kind)
        outs.append(o)
    node.set_editor_property('additional_outputs', outs)
    node.set_editor_property('code', code)
    return node


def tex_object(mat, tex, x, y, name='Atlas'):
    t = mel.create_material_expression(mat, u.MaterialExpressionTextureObjectParameter, x, y)
    t.set_editor_property('parameter_name', name)
    t.set_editor_property('texture', tex)
    t.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE if 'Dust' in tex.get_name() else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    return t


def new_material(name, blend):
    path = FX + '/' + name
    mat = eal.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset(name, FX, u.Material, u.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', blend)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('used_with_niagara_sprites', True)
    return mat


# The frame from a random 0..1 (16 frames, 4 x 4, row 0 at the top) and the sprite's own uv.
FRAME = '''float f=floor(saturate(Rand)*15.999);
float2 cell=float2(fmod(f,4.0),floor(f*0.25));
float2 uv=(saturate(UV)+cell)*0.25;
float4 t=Texture2DSample(Atlas,AtlasSampler,uv);
'''

MUD_HLSL = FRAME + '''const float d=1.0/1024.0;
float hx=Texture2DSample(Atlas,AtlasSampler,uv+float2(d,0)).r-Texture2DSample(Atlas,AtlasSampler,uv-float2(d,0)).r;
float hy=Texture2DSample(Atlas,AtlasSampler,uv+float2(0,d)).r-Texture2DSample(Atlas,AtlasSampler,uv-float2(0,d)).r;
Nrm=normalize(float3(-hx*Strength,hy*Strength,1.0));
return t.a;
'''

GRIT_HLSL = FRAME + '''Col=Tint*lerp(0.55,1.1,t.r)*(0.9+0.2*t.g);
return t.a;
'''

# The flipbook over the particle's life, frames blended; at most MaxOpacity.
DUST_HLSL = '''float a=saturate(Age)*15.0;
float f0=floor(a);float f1=min(f0+1.0,15.0);float k=a-f0;
float2 c0=float2(fmod(f0,4.0),floor(f0*0.25));float2 c1=float2(fmod(f1,4.0),floor(f1*0.25));
float2 s=saturate(UV);
float v0=Texture2DSample(Atlas,AtlasSampler,(s+c0)*0.25).r;
float v1=Texture2DSample(Atlas,AtlasSampler,(s+c1)*0.25).r;
return lerp(v0,v1,k)*MaxOpacity;
'''


# P2c: the dust's lighting numbers (chosen by check_wheel_spray.py's same-frame sweep and Art/sample_spray_pbr.py's dust gate).
# Benmore B1c: DustFloorDisplay, the floor's display scale where the scene is exposed for real daylight (DUST_FLOOR_HLSL).
DUST_LIGHT = {'DustLit': 0.7, 'DustFloor': 1.4, 'DustFloorDisplay': 2.5}
# Benmore B1c: the emissive floor was absolute (DustTint x DustFloor, cd/m2), so at Benmore's fixed EV100 13.6 (a 60,000 lux sun) it
# came out about 1/15,000 of the strips' (EV100 0.25 or under): dust in the car's shadow showed only the weak sky fill, as soot. Past
# EV100 about 4 (1/exposure over 16) the floor fades to a display-referred one, F x DustFloorDisplay x 1/exposure, so it reads the same
# at any daylight exposure; at the strips' exposures (1/exposure under 3) w is 0 and the floor is exactly P2c's.
DUST_FLOOR_HLSL = '''float inv=Inv.x;
float w=saturate((log2(max(inv,1e-6))-4.0)*0.25);
return F*lerp(1.0,K*inv,w);'''


def spray_mpc():
    """MPC_GT_Spray, made once: its parameters are kept (a material's collection node holds a parameter's id), only their defaults set."""
    path = FX + '/MPC_GT_Spray'
    mpc = eal.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset('MPC_GT_Spray', FX, u.MaterialParameterCollection,
                                                                                      u.MaterialParameterCollectionFactoryNew())
    scalars = list(mpc.get_editor_property('scalar_parameters'))
    names = [str(p.get_editor_property('parameter_name')) for p in scalars]
    for name, value in DUST_LIGHT.items():
        if name in names:
            scalars[names.index(name)].set_editor_property('default_value', value)
        else:
            p = u.CollectionScalarParameter()
            p.set_editor_property('parameter_name', name)
            p.set_editor_property('default_value', value)
            scalars.append(p)
    mpc.set_editor_property('scalar_parameters', scalars)
    eal.save_loaded_asset(mpc)
    report['dust_light'] = dict(collection=mpc.get_path_name(), **DUST_LIGHT)
    return mpc


def sprite_materials(tex):
    F1, F3 = u.CustomMaterialOutputType.CMOT_FLOAT1, u.CustomMaterialOutputType.CMOT_FLOAT3
    out = {}
    # Mud: masked, lit, the frame from Particle Random, a normal from the soft height, the colour the particle's (MudTint).
    mat = new_material('M_GT_SprayMud', u.BlendMode.BLEND_MASKED)
    mat.set_editor_property('opacity_mask_clip_value', 0.33)
    node = custom_node(mat, -300, 0, 'Spray mud droplet (wheel spray P2)', ['Atlas', 'UV', 'Rand', 'Strength'], MUD_HLSL, F1, [('Nrm', F3)])
    assert mel.connect_material_expressions(tex_object(mat, tex['T_GT_SprayMud'], -900, -200), '', node, 'Atlas')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionTextureCoordinate, -900, 0), '', node, 'UV')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionParticleRandom, -900, 100), '', node, 'Rand')
    k = mel.create_material_expression(mat, u.MaterialExpressionConstant, -900, 200)
    k.set_editor_property('r', 6.0)
    assert mel.connect_material_expressions(k, '', node, 'Strength')
    pc = mel.create_material_expression(mat, u.MaterialExpressionParticleColor, -300, -250)
    rough = mel.create_material_expression(mat, u.MaterialExpressionConstant, -300, 250)
    rough.set_editor_property('r', 0.5)
    assert mel.connect_material_property(pc, '', u.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(rough, '', u.MaterialProperty.MP_ROUGHNESS)
    assert mel.connect_material_property(node, '', u.MaterialProperty.MP_OPACITY_MASK)
    assert mel.connect_material_property(node, 'Nrm', u.MaterialProperty.MP_NORMAL)
    out['M_GT_SprayMud'] = mat
    # Grit: masked, lit, the particle colour (between GritTintA and GritTintB) x the facet shade x the chip's own +-10 %.
    mat = new_material('M_GT_SprayGrit', u.BlendMode.BLEND_MASKED)
    mat.set_editor_property('opacity_mask_clip_value', 0.33)
    node = custom_node(mat, -300, 0, 'Spray gravel grit (wheel spray P2)', ['Atlas', 'UV', 'Rand', 'Tint'], GRIT_HLSL, F1, [('Col', F3)])
    assert mel.connect_material_expressions(tex_object(mat, tex['T_GT_SprayGrit'], -900, -200), '', node, 'Atlas')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionTextureCoordinate, -900, 0), '', node, 'UV')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionParticleRandom, -900, 100), '', node, 'Rand')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionParticleColor, -900, 200), '', node, 'Tint')
    rough = mel.create_material_expression(mat, u.MaterialExpressionConstant, -300, 250)
    rough.set_editor_property('r', 0.75)
    assert mel.connect_material_property(node, 'Col', u.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(rough, '', u.MaterialProperty.MP_ROUGHNESS)
    assert mel.connect_material_property(node, '', u.MaterialProperty.MP_OPACITY_MASK)
    out['M_GT_SprayGrit'] = mat
    # Dust: translucent, lit, the flipbook over the life, at most 0.5 (P2b), a 60 cm depth fade.
    mat = new_material('M_GT_SprayDust', u.BlendMode.BLEND_TRANSLUCENT)
    # P2b: lit per pixel like a surface (the default volumetric non-directional lighting read the puffs darker than the sunlit
    # gravel they rose from).
    mat.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    node = custom_node(mat, -300, 0, 'Spray gravel dust (wheel spray P2)', ['Atlas', 'UV', 'Age', 'MaxOpacity'], DUST_HLSL, F1)
    assert mel.connect_material_expressions(tex_object(mat, tex['T_GT_SprayDust'], -900, -200), '', node, 'Atlas')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionTextureCoordinate, -900, 0), '', node, 'UV')
    assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionParticleRelativeTime, -900, 100), '', node, 'Age')
    k = mel.create_material_expression(mat, u.MaterialExpressionConstant, -900, 200)
    k.set_editor_property('r', 0.5)   # P2b (P2: 0.35)
    assert mel.connect_material_expressions(k, '', node, 'MaxOpacity')
    fade = mel.create_material_expression(mat, u.MaterialExpressionDepthFade, -100, 100)
    fade.set_editor_property('fade_distance_default', 60.0)
    assert mel.connect_material_expressions(node, '', fade, 'Opacity')
    # P2c: the dust's light from MPC_GT_Spray - base colour DustTint x DustLit (the sun's and the sky's share), emissive DustTint x
    # DustFloor (a sky floor, blended by the opacity like the lit colour), so dust in the car's shadow is not black.
    pc = mel.create_material_expression(mat, u.MaterialExpressionParticleColor, -500, -250)
    collection = spray_mpc()
    for prop, param, y in ((u.MaterialProperty.MP_BASE_COLOR, 'DustLit', -250), (u.MaterialProperty.MP_EMISSIVE_COLOR, 'DustFloor', -450)):
        k = mel.create_material_expression(mat, u.MaterialExpressionCollectionParameter, -500, y - 100)
        k.set_editor_property('collection', collection)
        k.set_editor_property('parameter_name', param)
        m = mel.create_material_expression(mat, u.MaterialExpressionMultiply, -200, y)
        assert mel.connect_material_expressions(pc, '', m, 'A')
        assert mel.connect_material_expressions(k, '', m, 'B')
        if prop == u.MaterialProperty.MP_EMISSIVE_COLOR:
            # Benmore B1c: the floor display-referred under daylight exposures (DUST_FLOOR_HLSL).
            floor = custom_node(mat, 0, y, 'Spray dust floor (Benmore B1c)', ['F', 'Inv', 'K'], DUST_FLOOR_HLSL, F3)
            assert mel.connect_material_expressions(m, '', floor, 'F')
            assert mel.connect_material_expressions(mel.create_material_expression(mat, u.MaterialExpressionEyeAdaptationInverse, -200, y + 100), '', floor, 'Inv')
            kd = mel.create_material_expression(mat, u.MaterialExpressionCollectionParameter, -500, y + 150)
            kd.set_editor_property('collection', collection)
            kd.set_editor_property('parameter_name', 'DustFloorDisplay')
            assert mel.connect_material_expressions(kd, '', floor, 'K')
            m = floor
        assert mel.connect_material_property(m, '', prop)
    rough = mel.create_material_expression(mat, u.MaterialExpressionConstant, -300, 250)
    rough.set_editor_property('r', 1.0)
    assert mel.connect_material_property(rough, '', u.MaterialProperty.MP_ROUGHNESS)
    assert mel.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    out['M_GT_SprayDust'] = mat
    errors = {}
    for name, m in out.items():
        e = mel.recompile_material(m)
        errors[name] = list(e)
        eal.save_loaded_asset(m)
    report['sprite_materials'] = dict(paths={k: v.get_path_name() for k, v in out.items()}, compile_errors=errors)
    assert not any(errors.values()), errors
    return out


WATER_SPRAY = '/Game/GrandTour/Materials/M_GT_WaterSpray'
MUDDY_TAG = 'P2d muddy rut splash'


def muddy_splash():
    """P2d (the owner approved): M_GT_WaterSpray reads the muddy rut splash from the Water ISM's per-instance custom data, which
    UGTSprayComponent::PushWaterMud writes after the Water kind's own 0 (opacity) and 1 (family): 2 the mud colour's weight, 3-5 its
    colour, 6 the rut water's turbidity. Base colour = lerp(BaseColor, the mud colour, 2); the coverage's Alpha = lerp(Opacity, 0.85,
    6). Zeros outside a Mud patch leave the clean splash exactly as before; the roughness is the material's 0.7 (at least 0.45).
    Added onto the material its own setup (Art/Unreal/benmore_water_interaction.py, not touched here) builds; idempotent, and lost if
    that setup rebuilds the material: run this again."""
    if not eal.does_asset_exist(WATER_SPRAY):
        return dict(skipped='no ' + WATER_SPRAY)
    m = eal.load_asset(WATER_SPRAY)
    exprs = list(mel.get_material_expressions(m))
    if any(str(e.get_editor_property('desc')) == MUDDY_TAG for e in exprs):
        return dict(material=m.get_path_name(), already=True)
    colour = mel.get_material_property_input_node(m, u.MaterialProperty.MP_BASE_COLOR)
    custom = next(e for e in exprs if isinstance(e, u.MaterialExpressionCustom) and 'SprayMask' in str(e.get_editor_property('code')))
    alpha = next(e for e in exprs if isinstance(e, u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name')) == 'Opacity')

    def data(i, x, y):
        n = mel.create_material_expression(m, u.MaterialExpressionPerInstanceCustomData, x, y)
        n.set_editor_property('data_index', i)
        n.set_editor_property('const_default_value', 0.0)
        n.set_editor_property('desc', MUDDY_TAG)
        return n
    weight, r, g, b, turb = data(2, -1400, 600), data(3, -1400, 700), data(4, -1400, 800), data(5, -1400, 900), data(6, -1400, 1000)
    rg = mel.create_material_expression(m, u.MaterialExpressionAppendVector, -1200, 750)
    assert mel.connect_material_expressions(r, '', rg, 'A') and mel.connect_material_expressions(g, '', rg, 'B')
    rgb = mel.create_material_expression(m, u.MaterialExpressionAppendVector, -1050, 800)
    assert mel.connect_material_expressions(rg, '', rgb, 'A') and mel.connect_material_expressions(b, '', rgb, 'B')
    tint = mel.create_material_expression(m, u.MaterialExpressionLinearInterpolate, -900, 600)
    tint.set_editor_property('desc', MUDDY_TAG)
    assert mel.connect_material_expressions(colour, '', tint, 'A') and mel.connect_material_expressions(rgb, '', tint, 'B')
    assert mel.connect_material_expressions(weight, '', tint, 'Alpha')
    assert mel.connect_material_property(tint, '', u.MaterialProperty.MP_BASE_COLOR)
    murk = mel.create_material_expression(m, u.MaterialExpressionLinearInterpolate, -900, 1000)
    murk.set_editor_property('desc', MUDDY_TAG)
    murk.set_editor_property('const_b', 0.85)
    assert mel.connect_material_expressions(alpha, '', murk, 'A') and mel.connect_material_expressions(turb, '', murk, 'Alpha')
    assert mel.connect_material_expressions(murk, '', custom, 'Alpha')
    errors = mel.recompile_material(m)
    assert not errors, str(errors)
    eal.save_loaded_asset(m)
    return dict(material=m.get_path_name(), added='base colour lerp by custom data 2 (3-5 the mud colour); Alpha lerp to 0.85 by 6',
                compile_errors=list(errors))


try:
    tex = textures()
    clumps()
    import live_mud_style as lms
    report['clump_material'] = lms.build_clod_material(lms.SPRAY_CLUMP_MATERIAL, lms.SPRAY_CLUMP_MESHES, spray=True, scalars={'ClodScaleCm': 25.0})
    report['muddy_splash'] = muddy_splash()
    mats = sprite_materials(tex)
    # Art/setup_wheel_spray.ps1 removes the old file before the editor starts: a system built over an existing package (an
    # in-session delete leaves the file) crashed every later load (2026-10-10).
    assert not eal.does_asset_exist(FX + '/NS_GT_WheelSpray'), 'NS_GT_WheelSpray still exists: run Art/setup_wheel_spray.ps1'
    log = u.GTNiagaraSetupLibrary.build_wheel_spray(FX, 'NS_GT_WheelSpray', mats['M_GT_SprayMud'], mats['M_GT_SprayGrit'], mats['M_GT_SprayDust'])
    report['niagara_log'] = log.splitlines()
    system = eal.load_asset(FX + '/NS_GT_WheelSpray')
    report['niagara_saved'] = bool(system) and eal.save_loaded_asset(system)
    report['ok'] = 'BUILD OK' in log and report['niagara_saved']
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (SRC / 'setup-report.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
