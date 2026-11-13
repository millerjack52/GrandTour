"""Build only DustLab-owned assets and an opt-in test map. No shared saves."""
import json
import traceback
import time
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/DustLab'
OUT.mkdir(parents=True, exist_ok=True)
BASE = '/Game/GrandTour/ArtTests/DustLab'
RUN = BASE + '/Build_' + datetime.now().strftime('%Y%m%d_%H%M%S')
LEVEL = BASE + '/L_DustLab'
eal = u.EditorAssetLibrary
mel = u.MaterialEditingLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
report = {'ok': False, 'level': LEVEL, 'asset_folder': RUN}
u.EditorPythonScripting.set_keep_python_script_alive(True)

class MapCopyCreated(Exception):
    pass


def save(asset):
    assert asset.get_path_name().startswith(BASE + '/'), asset.get_path_name()
    assert eal.save_loaded_asset(asset)


def build_material():
    atlas = eal.duplicate_asset('/Game/GrandTour/FX/Textures/T_GT_SprayDust', RUN + '/T_DustAtlas')
    assert atlas, 'Existing painterly dust atlas missing'
    save(atlas)
    mat = assets.create_asset('M_DustLab', RUN, u.Material, u.MaterialFactoryNew())
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('used_with_niagara_sprites', True)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    def node(cls, x=0, y=0):
        return mel.create_material_expression(mat, cls, x, y)
    def link(a, out, b, inp):
        assert mel.connect_material_expressions(a, out, b, inp), (a, b, inp)
    def constant(value):
        n = node(u.MaterialExpressionConstant)
        n.set_editor_property('r', value)
        return n
    tex = node(u.MaterialExpressionTextureObjectParameter, -900, -200)
    tex.set_editor_property('parameter_name', 'Atlas')
    tex.set_editor_property('texture', atlas)
    tex.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE)
    uv = node(u.MaterialExpressionTextureCoordinate, -900, 0)
    age = node(u.MaterialExpressionParticleRelativeTime, -900, 100)
    color = node(u.MaterialExpressionParticleColor, -900, 300)
    mask = node(u.MaterialExpressionCustom, -400, 0)
    inputs = []
    for name in ('Atlas', 'UV', 'Age', 'Alpha'):
        item = u.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
    mask.set_editor_property('inputs', inputs)
    mask.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    mask.set_editor_property('code', '''
float age=saturate(Age), f=age*15.0, i=floor(f), j=min(i+1.0,15.0);
// Inset half a texel within each atlas cell to avoid neighbour-frame bleeding.
float2 q=lerp(0.002,0.998,saturate(UV));
float a=Texture2DSample(Atlas,AtlasSampler,(q+float2(fmod(i,4.0),floor(i/4.0)))/4.0).r;
float b=Texture2DSample(Atlas,AtlasSampler,(q+float2(fmod(j,4.0),floor(j/4.0)))/4.0).r;
float fade=smoothstep(0.0,0.10,age)*(1.0-smoothstep(0.55,1.0,age));
return saturate(lerp(a,b,frac(f))*Alpha*0.65*fade);
''')
    for n, output, name in ((tex, '', 'Atlas'), (uv, '', 'UV'), (age, '', 'Age'), (color, 'A', 'Alpha')):
        link(n, output, mask, name)
    fade = node(u.MaterialExpressionDepthFade, -100, 0)
    fade.set_editor_property('fade_distance_default', 55.0)
    link(mask, '', fade, 'Opacity')
    assert mel.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    # Private lighting values: no dependency on the shared spray MPC.
    for prop, scale in ((u.MaterialProperty.MP_BASE_COLOR, 0.7), (u.MaterialProperty.MP_EMISSIVE_COLOR, 1.05)):
        mul = node(u.MaterialExpressionMultiply)
        link(color, 'RGB', mul, 'A')
        link(constant(scale), '', mul, 'B')
        assert mel.connect_material_property(mul, '', prop)
    assert mel.connect_material_property(constant(1.), '', u.MaterialProperty.MP_ROUGHNESS)
    errors = mel.recompile_material(mat)
    assert not errors, str(errors)
    save(mat)
    return mat


try:
    material = build_material()
    log = u.GTDustLabSetupLibrary.build_dust(RUN, 'NS_DustLab', material)
    report['niagara_log'] = log.splitlines()
    assert 'BUILD OK' in log and 'FAIL' not in log, log
    system = eal.load_asset(RUN + '/NS_DustLab')
    assert system
    save(system)
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    # World assets must use Save As, not EditorAssetLibrary.duplicate_asset:
    # duplicating a loaded UWorld leaves a standalone world rooted during map GC.
    if not eal.does_asset_exist(LEVEL):
        assert levels.load_level('/Game/GrandTour/ArtTests/DeformableGravel/L_GravelDeform')
        copied_world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        assert u.EditorLoadingAndSavingUtils.save_map(copied_world, LEVEL)
        del copied_world
        # SaveMap writes a copy but leaves the source world open. Never edit or
        # save_current_level in that world. Finish this run; rerun to install.
        report.update(ok=True, map_created=True, install_pending=True)
        raise MapCopyCreated()
    else:
        assert levels.load_level(LEVEL)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    current_world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert current_world.get_path_name().startswith(LEVEL + '.'), current_world.get_path_name()
    del current_world
    for actor in actors.get_all_level_actors():
        if isinstance(actor, u.GTDustLab):
            actors.destroy_actor(actor)
    lab = actors.spawn_actor_from_class(u.GTDustLab, u.Vector(0, 0, 0))
    lab.set_actor_label('DustLab_OptIn')
    lab.set_editor_property('dust_system', system)
    lab.set_editor_property('intensity', 2.4)
    assert levels.save_current_level()
    report.update(ok=True, system=system.get_path_name(), material=material.get_path_name(),
                  shared_assets_saved=False, note='Prototype only; Benmore and shared spray unchanged.')
except MapCopyCreated:
    pass
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'setup-report.json').write_text(json.dumps(report, indent=2))
    # Allow the saved world's scene/render resources to finish initialization
    # before shutdown; quitting on the startup Python frame can fault on teardown.
    quit_at = time.monotonic() + 3.
    quit_stage = 0
    def quit_tick(dt):
        global quit_at, quit_stage
        if time.monotonic() >= quit_at:
            if quit_stage == 0 and not report.get('install_pending'):
                # Tear the landscape world down while the renderer is still alive.
                # No Python actor wrappers may retain the old world across LoadLevel.
                globals().pop('actor', None)
                globals().pop('lab', None)
                u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
                quit_stage = 1
                quit_at = time.monotonic() + 2.
                return
            u.unregister_slate_post_tick_callback(quit_handle)
            u.SystemLibrary.quit_editor()
    quit_handle = u.register_slate_post_tick_callback(quit_tick)
