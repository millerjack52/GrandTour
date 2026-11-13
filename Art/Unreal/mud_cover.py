"""MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1 items 4-5): the carried mud's materials.

- The splat atlas (Art/Blender/build_mud_splats.py -> Art/Export/MudSplats) into /Game/GrandTour/Mud/Splats: T_MudSplat_Mask,
  T_MudSplat_Height, T_MudSplat_Splatter (linear, TC_Masks) and T_MudSplat_Normal (TC_NormalMap, DirectX).
- MPC_TrackPaint gains MudCover and GrassMud (UGTTrackPaintSubsystem writes them from gt.Mud.Carry / gt.Mud.Splats and
  gt.Mud.GrassMud; 1 until play writes them).
- MF_MudCover (/Game/GrandTour/Materials): where the track paint's G (coverage) is over 0, the ground goes toward the Standard
  bog slice (TA_MS_Bog* slice 0, one top-down tiling at MudCoverTileCm): coverage x (0.5 + the bog's height three mips down +
  0.3 x (its height - 0.5)), then a soft threshold (MudCoverEdgeLo..Hi), so the edge is ragged in metre-scale patches (MR2
  housekeeping 1: MR1's 0.25 + 1.5 x the sharp height drew the tracks as dotted specks); B (wetness) takes it from dried (lighter
  by MudDryLighten, matte MudDryRough) to wet (darker by MudWetDarken, glossy MudWetRough). Faces up only (VertexNormal z).
  The ruts' R is MF_TrackPaint's, untouched. Where the cover is 0 the inputs pass through unchanged. It sits in front of the
  MF_Weather call's BaseColor and Roughness (so rain wets the mud too, and every master still ends in MF_Weather) and on
  MP_NORMAL; TangentNormal (a static bool) picks the material's normal space.
- wire_mud_cover(material): puts it into a ground material (M_GT_Environment tangent, M_GT_Landscape and the strips' copies
  world), found by desc on a rerun and re-spliced if another setup rewired round it.
- M_GT_MudSplatDecal (/Game/GrandTour/Mud/Splats): the pooled splat decal (UGTMudSplatSubsystem): the atlas tile (Tile) over
  the decal, the Standard bog's colour at SizeCm, wet to dry over 90 s (exp), faded out over 600 s from SpawnTime.
- wire_grass_mud(material): the grass's base toward dried mud by G at the blade's world XY, the lower 18-30 cm of each clump
  (per instance; about 30-50 % of the 60 cm mean tussock) with a ragged line and a speckle above it, behind the static switch
  GrassMud (on) and MPC_TrackPaint's GrassMud. MR2 housekeeping 2: the instance's origin comes through a vertex interpolator
  (a pixel shader's ObjectPositionWS is the ISM component's origin, MaterialTemplate.ush), and the mud is the bog's mean colour
  (not x 1.6, the straw's own brown).
Run through Art/Unreal/setup_mud_carry.py (& Art/setup_mud_carry.ps1); live_mud_style.py calls wire_mud_cover on the
landscapes it rebuilds, so the strip setups keep it.
MudRunner MRP (docs/MUDRUNNER_LESSONS_PLAN.md MRP items 1-2): MF_MudCover and the splat decal read the Standard slice's ORH array
(TA_MS_BogORH: R AO, G roughness in the PBR bands, B height) in place of its rough and height maps; behind MPC_TrackPaint's MudPBR
(gt.Mud.PBR) dried mud is 0.85-0.95 rough and wet mud 0.45-0.65 (MR1's wet 0.30-0.32 was a gloss), the AO tints the cavities by
at most MudCavityTint 0.15 and leaves MF_MudCover as AmbientOcclusion (onto a ground material's Ambient Occlusion pin when it is
free); MudPBR 0 is the look before MRP. The decal has no AO pin (a translucent deferred decal), so only the cavity tint.
MRP follow-up (rain on carried mud): MF_MudCover's FloorMask output (its cover with gt.Mud.PBR, else 0) drives a floor node after
the ground material's MF_Weather call, `MudCover rain floor (MRP)`: roughness max(R, 0.45) by the cover x (1 - the weather's
Puddle), so the weather's wet path (toward 0.15 on porous ground) no longer glosses carried mud and landscape splats; standing
puddles and every other surface keep the weather's values. The splat decals on meshes draw after the base pass with their own
roughness (0.45 or more), so the weather never reaches them.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
mel = u.MaterialEditingLibrary
eal = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
SRC = ROOT / 'Art/Export/MudSplats'
SPLATS = '/Game/GrandTour/Mud/Splats'
MAT = '/Game/GrandTour/Materials'
TERRAIN = '/Game/GrandTour/Terrain'
MPC_PATH = TERRAIN + '/MPC_TrackPaint'
RT_PATH = TERRAIN + '/RT_TrackPaint'
MF_PATH = MAT + '/MF_MudCover'
WEATHER_NAME = 'MF_Weather'
DECAL_PATH = SPLATS + '/M_GT_MudSplatDecal'
BOG = '/Game/GrandTour/ArtTests/MudStyle'
BOG_ARRAYS = {'BogC': ('TA_MS_BogColor', 'SAMPLERTYPE_COLOR'), 'BogN': ('TA_MS_BogNormal', 'SAMPLERTYPE_NORMAL'),
              'BogORH': ('TA_MS_BogORH', 'SAMPLERTYPE_LINEAR_COLOR')}   # MRP: R AO, G roughness (PBR bands), B height
# MRP: the console switches' MPC_TrackPaint scalars (live_mud_style.MRP_MPC; UGTTrackPaintSubsystem writes them).
MRP_MPC = {'MudPBR': 1.0, 'MudPOM': 2.0, 'MudPOMShadow': 1.0}
SPLAT_TEXTURES = {'Mask': ('T_MudSplat_Mask', 'TC_MASKS', 'SAMPLERTYPE_MASKS'), 'Height': ('T_MudSplat_Height', 'TC_MASKS', 'SAMPLERTYPE_MASKS'),
                  'Normal': ('T_MudSplat_Normal', 'TC_NORMALMAP', 'SAMPLERTYPE_NORMAL'), 'Splatter': ('T_MudSplat_Splatter', 'TC_MASKS', 'SAMPLERTYPE_MASKS')}
# Proposed starting points (the owner names them after looking).
# EdgeLo/Hi 0.30/0.50 hid a 0.4 load's track (G about 0.3) but for the bog's highest lumps (2026-10-08): 0.15/0.35.
# MRP: MudWetRough (0.32 / 0.30) is gt.Mud.PBR 0's; with PBR wet mud is MudWetRoughLo..Hi by the ORH's roughness.
COVER_SCALARS = {'MudCoverTileCm': 300.0, 'MudCoverEdgeLo': 0.15, 'MudCoverEdgeHi': 0.35, 'MudDryLighten': 1.45,
                 'MudWetDarken': 0.78, 'MudWetRough': 0.32, 'MudDryRough': 0.88, 'MudWetRoughLo': 0.45, 'MudWetRoughHi': 0.65,
                 'MudCavityTint': 0.15}
DECAL_SCALARS = {'SpawnTime': 0.0, 'Tile': 0.0, 'SizeCm': 40.0, 'SplatTileCm': 300.0, 'SplatFadeS': 600.0, 'SplatDryS': 90.0,
                 'MudDryLighten': 1.45, 'MudWetDarken': 0.78, 'MudWetRough': 0.30, 'MudDryRough': 0.88, 'MudWetRoughLo': 0.45,
                 'MudWetRoughHi': 0.65, 'MudCavityTint': 0.15}
GRASS_SCALARS = {'GrassMudLineMinCm': 18.0, 'GrassMudLineMaxCm': 30.0}
GRASS_MATERIALS = ['/Game/GrandTour/ArtTests/TussockStyle/M_TS_Grass', MAT + '/M_GT_FoliageCard']
COVER_MATERIALS = [(MAT + '/M_GT_Environment', True), (MAT + '/M_GT_Landscape', False),
                   ('/Game/GrandTour/ArtTests/LiveMudDrive/M_LiveLandscape', False), ('/Game/GrandTour/ArtTests/MudVariants/M_VariantsLandscape', False)]
TAG_CALL = 'MudCover:call'
TAG_SPACE = 'MudCover:space'


def log(msg):
    u.log('MUD_COVER ' + msg)


def setprops(obj, **values):
    for key, value in values.items():
        obj.set_editor_property(key, value)
    return obj


def connect(src, out, dst, pin):
    if mel.connect_material_expressions(src, out, dst, pin):
        return
    raise RuntimeError('could not connect %s.%r -> %s.%r (inputs %s)' % (src.get_name(), out, dst.get_name(), pin,
                       [str(n) for n in mel.get_material_expression_input_names(dst)]))


def custom_slots(node, inputs, outputs=()):
    slots = []
    for name in inputs:
        s = u.CustomInput()
        s.set_editor_property('input_name', name)
        slots.append(s)
    node.set_editor_property('inputs', slots)
    outs = []
    for name, kind in outputs:
        o = u.CustomOutput()
        o.set_editor_property('output_name', name)
        o.set_editor_property('output_type', kind)
        outs.append(o)
    node.set_editor_property('additional_outputs', outs)


def manifest():
    path = SRC / 'manifest.json'
    return json.loads(path.read_text()) if path.exists() else {}


def dry_mud_colour():
    # MR2 housekeeping 2: the Standard bog's mean as it is (MR1 lightened it x 1.6, which is the straw tussocks' own brown in the
    # sun: the grass's mud was there and could not be seen); the grass block darkens it further toward wet (x 0.6 at B 1).
    mean = manifest().get('standard_bog_mean_linear') or [0.0705, 0.0401, 0.0186]
    return [round(min(1.0, c * 1.0), 4) for c in mean]


# ---------------------------------------------------------------- the atlas
def import_textures():
    tasks = []
    for _key, (name, _comp, _sampler) in SPLAT_TEXTURES.items():
        path = SRC / (name + '.png')
        assert path.exists(), 'no %s (bake Art/Blender/build_mud_splats.py first)' % path
        task = u.AssetImportTask()
        task.filename = str(path)
        task.destination_path = SPLATS
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        tasks.append(task)
    assets.import_asset_tasks(tasks)
    facts = []
    for _key, (name, comp, _sampler) in SPLAT_TEXTURES.items():
        tex = eal.load_asset(SPLATS + '/' + name)
        assert tex, 'the import made no ' + name
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('compression_settings', getattr(u.TextureCompressionSettings, comp))
        if comp == 'TC_NORMALMAP':
            tex.set_editor_property('flip_green_channel', False)
        tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WORLD)
        for axis in ('address_x', 'address_y'):
            tex.set_editor_property(axis, u.TextureAddress.TA_CLAMP if name != 'T_MudSplat_Splatter' else u.TextureAddress.TA_WRAP)
        eal.save_loaded_asset(tex)
        facts.append(dict(asset=SPLATS + '/' + name, compression=comp, size=[tex.blueprint_get_size_x(), tex.blueprint_get_size_y()]))
    return facts


def ensure_mpc():
    mpc = eal.load_asset(MPC_PATH)
    assert mpc, 'no ' + MPC_PATH
    scalars = list(mpc.get_editor_property('scalar_parameters'))
    names = [str(p.get_editor_property('parameter_name')) for p in scalars]
    added = []
    for name, value in [('MudCover', 1.0), ('GrassMud', 1.0)] + list(MRP_MPC.items()):
        if name in names:
            continue
        p = u.CollectionScalarParameter()
        p.set_editor_property('parameter_name', name)
        p.set_editor_property('default_value', value)
        scalars.append(p)
        added.append(name)
    if added:
        mpc.set_editor_property('scalar_parameters', scalars)
        eal.save_loaded_asset(mpc)
    return dict(collection=MPC_PATH, added=added, scalars=len(scalars))


# ---------------------------------------------------------------- MF_MudCover
COVER_HLSL = '''// MudRunner MR1: the carried mud over the ground (G coverage, B wetness of RT_TrackPaint).
// MRP: the Standard slice's ORH (R AO, G roughness in the PBR bands, B height) in place of its rough and height maps. With gt.Mud.PBR
// (PBR) dried mud takes max(the ORH's roughness, DryRough) within 0.85-0.95 and wet mud the saturated surface's WetRoughLo..Hi
// (0.45-0.65), never glossier; the AO tints the cavities by at most CavityTint and leaves through AO (the material's Ambient
// Occlusion where its pin was free). gt.Mud.PBR 0: the bake's own roughness (the remap inverted) as before MRP.
float3 col = OldColor; Rough = OldRough; Cover = 0.0; MudNormalWS = normalize(VertexNormal); AO = 1.0; FloorMask = 0.0;
float2 bu = float2(WorldPos.x, -WorldPos.y) / max(TileCm, 1.0);
float2 bx = ddx(bu); float2 by = ddy(bu);
[branch] if (CoverOn > 0.5)
{
    float2 uv = (WorldPos.xy - Origin.xy) / Origin.z + 0.5;
    float inside = (uv.x > 0.0 && uv.x < 1.0 && uv.y > 0.0 && uv.y < 1.0) ? 1.0 : 0.0;
    float4 t = Texture2DSampleLevel(Tex, TexSampler, uv, 0);
    float g = saturate(t.g) * inside * saturate(VertexNormal.z * 2.0 - 1.0);
    [branch] if (g > 0.002)
    {
        float3 bs = float3(bu, 0.0);
        float4 o = BogORH.SampleGrad(BogORHSampler, bs, bx, by);
        float h = o.b;
        // MR2 housekeeping 1: the edge is ragged by the bog's height three mips down (its lumps blurred into metre-scale patches)
        // with only a little of the lumps themselves; g x (0.25 + 1.5 h) let a track's moderate G through on the lumps alone,
        // which drew the carried tracks as dotted lines of small dark specks however continuous G was (Carry_Exit, 2026-10-08).
        float hb = BogORH.SampleGrad(BogORHSampler, bs, bx * 8.0, by * 8.0).b;
        float c = smoothstep(EdgeLo, EdgeHi, g * (0.5 + hb + 0.3 * (h - 0.5)));
        float3 bc = BogC.SampleGrad(BogCSampler, bs, bx, by).rgb;
        float2 bn = UnpackNormalMap(BogN.SampleGrad(BogNSampler, bs, bx, by)).xy;
        float wet = saturate(t.b);
        float3 mud = lerp(bc * DryLighten + 0.01, bc * WetDarken, wet);
        float mr;
        if (PBR > 0.5)
        {
            float wetR = lerp(WetRoughLo, WetRoughHi, saturate((o.g - 0.45) / 0.5));
            mr = lerp(clamp(max(o.g, DryRough), 0.85, 0.95), wetR, wet);
            mud *= 1.0 - saturate(CavityTint) * (1.0 - o.r);
            AO = lerp(1.0, o.r, c);
            FloorMask = c;   // MRP follow-up: the rain floor after MF_Weather (wire_mud_cover)
        }
        else
        {
            float br = 0.14 + (o.g - 0.45) * 1.54;
            mr = lerp(max(br, DryRough), min(br, WetRough), wet);
        }
        col = lerp(OldColor, mud, c);
        Rough = lerp(OldRough, mr, c);
        MudNormalWS = normalize(normalize(VertexNormal) + float3(bn.x, bn.y, 0.0));
        Cover = c;
    }
}
return col;
'''
NORMAL_HLSL = 'return Cover > 0.0 ? normalize(lerp(Old, Mud, Cover)) : Old;\n'
COVER_INPUTS = ['OldColor', 'OldRough', 'WorldPos', 'VertexNormal', 'Origin', 'CoverOn', 'Tex', 'BogC', 'BogN', 'BogORH',
                'TileCm', 'EdgeLo', 'EdgeHi', 'DryLighten', 'WetDarken', 'WetRough', 'DryRough', 'PBR', 'WetRoughLo', 'WetRoughHi', 'CavityTint']
COVER_PINS = {'MudCoverTileCm': 'TileCm', 'MudCoverEdgeLo': 'EdgeLo', 'MudCoverEdgeHi': 'EdgeHi', 'MudDryLighten': 'DryLighten',
              'MudWetDarken': 'WetDarken', 'MudWetRough': 'WetRough', 'MudDryRough': 'DryRough', 'MudWetRoughLo': 'WetRoughLo',
              'MudWetRoughHi': 'WetRoughHi', 'MudCavityTint': 'CavityTint'}
FUNCTION_INPUTS = [('BaseColor', 'FUNCTION_INPUT_VECTOR3', -400), ('Roughness', 'FUNCTION_INPUT_SCALAR', -250), ('Normal', 'FUNCTION_INPUT_VECTOR3', -100),
                   ('TangentNormal', 'FUNCTION_INPUT_STATIC_BOOL', 50)]
FUNCTION_OUTPUTS = ['BaseColor', 'Roughness', 'Normal', 'AmbientOcclusion', 'FloorMask']


def build_function():
    """MF_MudCover, made or rebuilt. MRP: a rerun keeps the function's inputs and outputs (the nodes, so every material's call keeps
    its pins and links) and rebuilds everything between them: MR1's rerun changed only the code, which cannot add the ORH array, the
    PBR switch or the AmbientOcclusion output."""
    mf = eal.load_asset(MF_PATH) if eal.does_asset_exist(MF_PATH) else None
    created = mf is None
    if created:
        mf = assets.create_asset('MF_MudCover', MAT, u.MaterialFunction, u.MaterialFunctionFactoryNew())
        assert mf, 'could not create ' + MF_PATH
    mf.set_editor_property('description', 'MudRunner MR1/MRP: the carried mud (RT_TrackPaint G/B) over the ground: the Standard bog slice (colour, normal, ORH), ragged by its height, wet to dry, physically based behind MudPBR.')

    def fx(cls, x, y):
        return mel.create_material_expression_in_function(mf, cls, x, y)
    nodes = list(mel.get_material_function_expressions(mf))
    ins = {str(e.get_editor_property('input_name')): e for e in nodes if isinstance(e, u.MaterialExpressionFunctionInput)}
    outs = {str(e.get_editor_property('output_name')): e for e in nodes if isinstance(e, u.MaterialExpressionFunctionOutput)}
    removed = 0
    for e in nodes:
        if not isinstance(e, (u.MaterialExpressionFunctionInput, u.MaterialExpressionFunctionOutput)):
            mel.delete_material_expression_in_function(mf, e)
            removed += 1
    for priority, (name, kind, y) in enumerate(FUNCTION_INPUTS):
        if name not in ins:
            node = fx(u.MaterialExpressionFunctionInput, -1600, y)
            setprops(node, input_name=name, input_type=getattr(u.FunctionInputType, kind), sort_priority=priority)
            if name == 'TangentNormal':
                try:
                    node.set_editor_property('use_preview_value_as_default', True)
                except Exception as e:   # the materials always connect it
                    log('TangentNormal preview default not set: %s' % e)
            ins[name] = node
    for priority, name in enumerate(FUNCTION_OUTPUTS):
        if name not in outs:
            node = fx(u.MaterialExpressionFunctionOutput, 200, -300 + 150 * priority)
            setprops(node, output_name=name, sort_priority=priority)
            outs[name] = node
    surface = fx(u.MaterialExpressionCustom, -900, -300)
    setprops(surface, description='MudCover surface', output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    custom_slots(surface, COVER_INPUTS, [('Rough', u.CustomMaterialOutputType.CMOT_FLOAT1), ('Cover', u.CustomMaterialOutputType.CMOT_FLOAT1),
                                         ('MudNormalWS', u.CustomMaterialOutputType.CMOT_FLOAT3), ('AO', u.CustomMaterialOutputType.CMOT_FLOAT1),
                                         ('FloorMask', u.CustomMaterialOutputType.CMOT_FLOAT1)])
    surface.set_editor_property('code', COVER_HLSL)
    connect(ins['BaseColor'], '', surface, 'OldColor')
    connect(ins['Roughness'], '', surface, 'OldRough')
    wpos = fx(u.MaterialExpressionWorldPosition, -1600, 200)
    wpos.set_editor_property('world_position_shader_offset', u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    connect(wpos, '', surface, 'WorldPos')
    vn = fx(u.MaterialExpressionVertexNormalWS, -1600, 300)
    connect(vn, '', surface, 'VertexNormal')
    mpc = eal.load_asset(MPC_PATH)
    for pin, param, y in (('Origin', 'TrackOrigin', 400), ('CoverOn', 'MudCover', 500), ('PBR', 'MudPBR', 550)):
        node = fx(u.MaterialExpressionCollectionParameter, -1600, y)
        setprops(node, collection=mpc, parameter_name=param)
        connect(node, '', surface, pin)
    rt = fx(u.MaterialExpressionTextureObjectParameter, -1600, 600)
    setprops(rt, parameter_name='MudCover_TrackRT', texture=eal.load_asset(RT_PATH),
             sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, sampler_source=u.SamplerSourceMode.SSM_CLAMP_WORLD_GROUP_SETTINGS)
    connect(rt, '', surface, 'Tex')
    y = 750
    for pin, (asset, sampler) in BOG_ARRAYS.items():
        tex = eal.load_asset(BOG + '/' + asset)
        assert tex, 'no %s/%s (run & Art/import_mud_variants.ps1; MRP: python Art/bake_mud_orh.py first)' % (BOG, asset)
        node = fx(u.MaterialExpressionTextureObjectParameter, -1600, y)
        y += 120
        setprops(node, parameter_name='MudCover_' + pin, texture=tex, sampler_type=getattr(u.MaterialSamplerType, sampler),
                 sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        connect(node, '', surface, pin)
    for param, value in COVER_SCALARS.items():
        node = fx(u.MaterialExpressionScalarParameter, -1600, y)
        y += 90
        setprops(node, parameter_name=param, default_value=value)
        connect(node, '', surface, COVER_PINS[param])
    # The mud's normal in the material's space: tangent (M_GT_Environment) through a world-to-tangent transform, else world.
    xform = fx(u.MaterialExpressionTransform, -500, 200)
    setprops(xform, transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
             transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    connect(surface, 'MudNormalWS', xform, '')
    switch = fx(u.MaterialExpressionStaticSwitch, -300, 200)
    for src, pins in ((xform, ('True', 'A')), (surface, ('False', 'B'))):
        out = '' if src is xform else 'MudNormalWS'
        assert any(mel.connect_material_expressions(src, out, switch, p) for p in pins), 'static switch pin %s' % (pins,)
    connect(ins['TangentNormal'], '', switch, 'Value')
    blend = fx(u.MaterialExpressionCustom, -100, 150)
    setprops(blend, description='MudCover normal', output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    custom_slots(blend, ['Old', 'Mud', 'Cover'])
    blend.set_editor_property('code', NORMAL_HLSL)
    connect(ins['Normal'], '', blend, 'Old')
    connect(switch, '', blend, 'Mud')
    connect(surface, 'Cover', blend, 'Cover')
    for name, src, out in (('BaseColor', surface, ''), ('Roughness', surface, 'Rough'), ('Normal', blend, ''), ('AmbientOcclusion', surface, 'AO'),
                           ('FloorMask', surface, 'FloorMask')):
        connect(src, out, outs[name], '')
    mel.update_material_function(mf)
    eal.save_loaded_asset(mf)
    return dict(function=MF_PATH, created=created, rebuilt_between_pins=removed, inputs=sorted(ins), outputs=sorted(outs),
                expressions=mel.get_num_material_expressions_in_function(mf))


# ---------------------------------------------------------------- wiring into a material
def _inputs(mat, node):
    names = [str(n) for n in mel.get_material_expression_input_names(node)]
    srcs = list(mel.get_inputs_for_material_expression(mat, node))
    return dict(zip(names, srcs))


def _out_name(consumer, src):
    r = mel.get_input_node_output_name_for_material_expression(consumer, src)
    if isinstance(r, tuple):
        r = r[-1]
    return '' if r is None or isinstance(r, bool) else str(r)


def _reaches(mat, start, target, seen=None):
    seen = seen if seen is not None else set()
    if start is None:
        return False
    if start == target:
        return True
    key = start.get_name()
    if key in seen:
        return False
    seen.add(key)
    return any(_reaches(mat, s, target, seen) for s in mel.get_inputs_for_material_expression(mat, start) if s is not None)


def _weather_call(mat):
    node = mel.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR)
    if isinstance(node, u.MaterialExpressionMaterialFunctionCall):
        fn = node.get_editor_property('material_function')
        if fn is not None and fn.get_name() == WEATHER_NAME:
            return node
    return None


class Slot:
    """Where a value flows: a pin of an expression, or a material property."""

    def __init__(self, mat, node=None, pin=None, prop=None):
        self.mat, self.node, self.pin, self.prop = mat, node, pin, prop

    def feeder(self):
        if self.prop is not None:
            src = mel.get_material_property_input_node(self.mat, self.prop)
            return src, (str(mel.get_material_property_input_node_output_name(self.mat, self.prop)) if src else '')
        src = _inputs(self.mat, self.node).get(self.pin)
        return src, (_out_name(self.node, src) if src is not None else '')

    def feed(self, src, out):
        if self.prop is not None:
            assert mel.connect_material_property(src, out, self.prop), 'connect %s -> %s' % (src.get_name(), self.prop)
        else:
            connect(src, out, self.node, self.pin)


def splice(mat, node, out, in_pin, slot):
    """node.out feeds slot, and whatever fed slot feeds node.in_pin; on a rerun nothing moves. If another setup rewired round
    node (slot fed by something else), node takes that as its input; if that something already reads node (it wrapped
    node), its pin is given node's old input first, so nothing loops."""
    src, src_out = slot.feeder()
    if src == node:
        return 'kept'
    if src is None:
        raise RuntimeError('%s: nothing feeds %s' % (mat.get_name(), slot.pin or slot.prop))
    if _reaches(mat, src, node):
        old, old_out = _inputs(mat, node).get(in_pin), None
        if old is not None:
            old_out = _out_name(node, old)
        for e in mel.get_material_expressions(mat):
            if e == node:
                continue
            for pin, s in _inputs(mat, e).items():
                if s == node and _out_name(e, node) == out and old is not None:
                    connect(old, old_out or '', e, pin)
    connect(src, src_out, node, in_pin)
    slot.feed(node, out)
    return 'spliced'


TAG_FLOOR = 'MudCover:rainfloor'
FLOOR_HLSL = 'return lerp(R, max(R, 0.45), saturate(Mask) * (1.0 - saturate(Puddle)));\n'


def rain_floor(mat, call, weather):
    """MRP follow-up: carried mud's roughness held at 0.45 or more after the weather (its wet path takes porous ground toward
    0.15): a custom node between the weather call's Roughness output and whatever read it (the Roughness pin, or the strips'
    LiveApronRoughness wrapper's Old), by MF_MudCover's FloorMask x (1 - the weather's Puddle). Found by desc on a rerun."""
    if weather is None:
        return 'no MF_Weather call'
    nodes = list(mel.get_material_expressions(mat))
    floor = next((e for e in nodes if isinstance(e, u.MaterialExpressionCustom) and str(e.get_editor_property('desc')) == TAG_FLOOR), None)
    if floor is None:
        floor = mel.create_material_expression(mat, u.MaterialExpressionCustom, 150, 900)
        setprops(floor, desc=TAG_FLOOR, description='MudCover rain floor (MRP)', output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
        custom_slots(floor, ['R', 'Mask', 'Puddle'])
    floor.set_editor_property('code', FLOOR_HLSL)
    # Everything that read the weather's Roughness reads the floor instead (the floor itself keeps it).
    moved = []
    for e in nodes:
        if e == floor:
            continue
        for pin, src in _inputs(mat, e).items():
            if src == weather and _out_name(e, weather) == 'Roughness':
                connect(floor, '', e, pin)
                moved.append('%s.%s' % (e.get_name(), pin))
    rough_src = mel.get_material_property_input_node(mat, u.MaterialProperty.MP_ROUGHNESS)
    if rough_src == weather and str(mel.get_material_property_input_node_output_name(mat, u.MaterialProperty.MP_ROUGHNESS)) == 'Roughness':
        assert mel.connect_material_property(floor, '', u.MaterialProperty.MP_ROUGHNESS), '%s: floor -> Roughness' % mat.get_name()
        moved.append('Roughness pin')
    connect(weather, 'Roughness', floor, 'R')
    if not mel.connect_material_expressions(call, 'FloorMask', floor, 'Mask'):
        call.set_material_function(eal.load_asset(MF_PATH))   # an older call: refresh its pins from the function, then again
        connect(call, 'FloorMask', floor, 'Mask')
    connect(weather, 'Puddle', floor, 'Puddle')
    return 'moved %s' % (', '.join(moved) if moved else 'nothing (kept)')


def wire_mud_cover(mat, tangent=False):
    """MF_MudCover into a ground material: before its MF_Weather call's BaseColor and Roughness (on the properties when it has
    no weather call), and on MP_NORMAL. Idempotent."""
    mf = eal.load_asset(MF_PATH)
    if mf is None:
        return dict(material=mat.get_path_name(), skipped='no MF_MudCover yet (run & Art/setup_mud_carry.ps1)')
    nodes = list(mel.get_material_expressions(mat))
    call = next((e for e in nodes if isinstance(e, u.MaterialExpressionMaterialFunctionCall) and str(e.get_editor_property('desc')) == TAG_CALL), None)
    if call is None:
        call = mel.create_material_expression(mat, u.MaterialExpressionMaterialFunctionCall, -250, 900)
        call.set_editor_property('desc', TAG_CALL)
        assert call.set_material_function(mf), 'set MF_MudCover'
    space = next((e for e in nodes if isinstance(e, u.MaterialExpressionStaticBool) and str(e.get_editor_property('desc')) == TAG_SPACE), None)
    if space is None:
        space = mel.create_material_expression(mat, u.MaterialExpressionStaticBool, -450, 1100)
        space.set_editor_property('desc', TAG_SPACE)
    space.set_editor_property('value', bool(tangent))
    connect(space, '', call, 'TangentNormal')
    weather = _weather_call(mat)
    if weather is not None:
        colour, rough = Slot(mat, weather, 'BaseColor'), Slot(mat, weather, 'Roughness')
    else:
        colour, rough = Slot(mat, prop=u.MaterialProperty.MP_BASE_COLOR), Slot(mat, prop=u.MaterialProperty.MP_ROUGHNESS)
    done = dict(material=mat.get_path_name(), weather=weather is not None, tangent=bool(tangent))
    done['BaseColor'] = splice(mat, call, 'BaseColor', 'BaseColor', colour)
    done['Roughness'] = splice(mat, call, 'Roughness', 'Roughness', rough)
    done['Normal'] = splice(mat, call, 'Normal', 'Normal', Slot(mat, prop=u.MaterialProperty.MP_NORMAL))
    # MRP: the cover's AO onto the Ambient Occlusion pin where nothing else feeds it (1 wherever there is no cover).
    ao_src = mel.get_material_property_input_node(mat, u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if ao_src is None or ao_src == call:
        if not mel.connect_material_property(call, 'AmbientOcclusion', u.MaterialProperty.MP_AMBIENT_OCCLUSION):
            call.set_material_function(mf)   # an older call: refresh its pins from the function, then again
            assert mel.connect_material_property(call, 'AmbientOcclusion', u.MaterialProperty.MP_AMBIENT_OCCLUSION), '%s: AO pin' % mat.get_name()
        done['AmbientOcclusion'] = 'kept' if ao_src == call else 'wired'
    else:
        done['AmbientOcclusion'] = 'left (%s feeds it)' % ao_src.get_name()
    done['RainFloor'] = rain_floor(mat, call, weather)
    errors = [str(e) for e in mel.recompile_material(mat)]
    eal.save_loaded_asset(mat)
    done['compile_errors'] = errors
    assert not errors, '%s: %s' % (mat.get_name(), errors)
    return done


# ---------------------------------------------------------------- the splat decal
DECAL_HLSL = '''// MudRunner MR1: a thrown blob's splat on a static mesh (UGTMudSplatSubsystem's pooled decal).
// MRP: with gt.Mud.PBR (PBR) dried 0.85-0.95 by the Standard slice's ORH roughness and wet the saturated surface's WetRoughLo..Hi
// (MR1's 0.30 was a gloss), the cavities tinted by the ORH's AO (CavityTint); PBR 0 as before.
float age = max(Time - SpawnTime, 0.0);
float fade = saturate(1.0 - age / max(FadeS, 1.0));
float wet = exp(-age / max(DryS, 1.0));
float t = clamp(floor(Tile + 0.5), 0.0, 15.0);
float2 tuv = (float2(fmod(t, 4.0), floor(t / 4.0)) + saturate(UV)) * 0.25;
float m = Texture2DSample(Mask, MaskSampler, tuv).r;
float h = Texture2DSample(Height, HeightSampler, tuv).r;
float3 n = UnpackNormalMap(Texture2DSample(NormalTex, NormalTexSampler, tuv)).xyz;
float3 bs = float3(UV * SizeCm / max(TileCm, 1.0), 0.0);
float3 bc = Texture2DArraySample(BogC, BogCSampler, bs).rgb;
Opacity = smoothstep(0.22, 0.5, m * (0.6 + 0.8 * h)) * fade;
Nrm = normalize(lerp(float3(0.0, 0.0, 1.0), n, 0.85));
float3 mud = lerp(bc * DryLighten + 0.01, bc * WetDarken, wet);
if (PBR > 0.5)
{
    float4 o = Texture2DArraySample(BogORH, BogORHSampler, bs);
    float wetR = lerp(WetRoughLo, WetRoughHi, saturate((o.g - 0.45) / 0.5));
    Rough = lerp(clamp(max(o.g, DryRough), 0.85, 0.95), wetR, wet);
    mud *= 1.0 - saturate(CavityTint) * (1.0 - o.r);
}
else
{
    Rough = lerp(DryRough, WetRough, wet);
}
return mud;
'''


def build_decal():
    mat = eal.load_asset(DECAL_PATH) if eal.does_asset_exist(DECAL_PATH) else assets.create_asset('M_GT_MudSplatDecal', SPLATS, u.Material, u.MaterialFactoryNew())
    assert mat, 'could not create ' + DECAL_PATH
    mel.delete_all_material_expressions(mat)
    # The blend first: a deferred decal must be translucent (Substrate's "Translucent - Grey Transmittance"), and setting the
    # domain on an opaque material logs a failed compile for the moment between the two.
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('material_domain', u.MaterialDomain.MD_DEFERRED_DECAL)
    custom = mel.create_material_expression(mat, u.MaterialExpressionCustom, -300, 0)
    setprops(custom, description='Mud splat decal (MR1)', output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    names = ['UV', 'Mask', 'Height', 'NormalTex', 'BogC', 'Tile', 'SpawnTime', 'Time', 'SizeCm', 'TileCm', 'FadeS', 'DryS',
             'DryLighten', 'WetDarken', 'WetRough', 'DryRough', 'BogORH', 'PBR', 'WetRoughLo', 'WetRoughHi', 'CavityTint']
    custom_slots(custom, names, [('Rough', u.CustomMaterialOutputType.CMOT_FLOAT1), ('Opacity', u.CustomMaterialOutputType.CMOT_FLOAT1),
                                 ('Nrm', u.CustomMaterialOutputType.CMOT_FLOAT3)])
    custom.set_editor_property('code', DECAL_HLSL)
    y = -700
    uv = mel.create_material_expression(mat, u.MaterialExpressionTextureCoordinate, -900, y)
    connect(uv, '', custom, 'UV')
    for pin, key in (('Mask', 'Mask'), ('Height', 'Height'), ('NormalTex', 'Normal')):
        name, _comp, sampler = SPLAT_TEXTURES[key]
        y += 130
        node = mel.create_material_expression(mat, u.MaterialExpressionTextureObjectParameter, -900, y)
        setprops(node, parameter_name='Splat' + key, texture=eal.load_asset(SPLATS + '/' + name), sampler_type=getattr(u.MaterialSamplerType, sampler))
        connect(node, '', custom, pin)
    y += 130
    bog = mel.create_material_expression(mat, u.MaterialExpressionTextureObjectParameter, -900, y)
    setprops(bog, parameter_name='SplatBogC', texture=eal.load_asset(BOG + '/' + BOG_ARRAYS['BogC'][0]), sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR,
             sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    connect(bog, '', custom, 'BogC')
    y += 130
    orh = mel.create_material_expression(mat, u.MaterialExpressionTextureObjectParameter, -900, y)
    setprops(orh, parameter_name='SplatBogORH', texture=eal.load_asset(BOG + '/' + BOG_ARRAYS['BogORH'][0]), sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,
             sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    connect(orh, '', custom, 'BogORH')
    y += 130
    pbr = mel.create_material_expression(mat, u.MaterialExpressionCollectionParameter, -900, y)
    setprops(pbr, collection=eal.load_asset(MPC_PATH), parameter_name='MudPBR')
    connect(pbr, '', custom, 'PBR')
    y += 130
    time_node = mel.create_material_expression(mat, u.MaterialExpressionTime, -900, y)
    connect(time_node, '', custom, 'Time')
    pins = {'SplatTileCm': 'TileCm', 'SplatFadeS': 'FadeS', 'SplatDryS': 'DryS', 'MudDryLighten': 'DryLighten', 'MudWetDarken': 'WetDarken',
            'MudWetRough': 'WetRough', 'MudDryRough': 'DryRough', 'MudWetRoughLo': 'WetRoughLo', 'MudWetRoughHi': 'WetRoughHi',
            'MudCavityTint': 'CavityTint'}
    for param, value in DECAL_SCALARS.items():
        y += 90
        node = mel.create_material_expression(mat, u.MaterialExpressionScalarParameter, -900, y)
        setprops(node, parameter_name=param, default_value=value)
        connect(node, '', custom, pins.get(param, param))
    assert mel.connect_material_property(custom, '', u.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(custom, 'Rough', u.MaterialProperty.MP_ROUGHNESS)
    assert mel.connect_material_property(custom, 'Opacity', u.MaterialProperty.MP_OPACITY)
    assert mel.connect_material_property(custom, 'Nrm', u.MaterialProperty.MP_NORMAL)
    errors = [str(e) for e in mel.recompile_material(mat)]
    eal.save_loaded_asset(mat)
    assert not errors, errors
    return dict(material=DECAL_PATH, domain=str(mat.get_editor_property('material_domain')), blend=str(mat.get_editor_property('blend_mode')),
                scalars=DECAL_SCALARS, compile_errors=errors)


# ---------------------------------------------------------------- muddy grass
GRASS_HLSL = '''// MudRunner MR1: grass over carried mud darkens toward dried mud at its base (G at the blade's XY).
float3 col = Base;
[branch] if (GrassOn > 0.5)
{
    float2 uv = (WorldPos.xy - Origin.xy) / Origin.z + 0.5;
    if (uv.x > 0.0 && uv.x < 1.0 && uv.y > 0.0 && uv.y < 1.0)
    {
        float4 t = Texture2DSampleLevel(Tex, TexSampler, uv, 0);
        float g = saturate(t.g);
        [branch] if (g > 0.01)
        {
            float hz = WorldPos.z - ObjPos.z;
            float2 cell = floor(WorldPos.xy / 4.0);
            float n = frac(sin(dot(cell, float2(127.1, 311.7))) * 43758.5453);
            float mudLine = lerp(LineMinCm, LineMaxCm, Rand) * (0.55 + 0.45 * g) + (n - 0.5) * 6.0;
            float band = 1.0 - smoothstep(mudLine - 4.0, mudLine + 1.5, hz);
            float3 sc = floor(WorldPos / 1.6);
            float s = frac(sin(dot(sc, float3(12.9898, 78.233, 37.719))) * 43758.5453);
            float speck = step(0.86, s) * (1.0 - smoothstep(mudLine, mudLine + 18.0, hz)) * step(mudLine - 2.0, hz);
            float m = saturate(max(band, speck)) * smoothstep(0.02, 0.3, g);
            col = lerp(col, MudDry * lerp(1.0, 0.6, saturate(t.b)), m);
        }
    }
}
return col;
'''
TAG_GRASS = 'GrassMud:surface'
TAG_GRASS_SWITCH = 'GrassMud'


def wire_grass_mud(mat):
    nodes = list(mel.get_material_expressions(mat))
    surface = next((e for e in nodes if isinstance(e, u.MaterialExpressionCustom) and str(e.get_editor_property('desc')) == TAG_GRASS), None)
    fresh = surface is None
    if fresh:
        surface = mel.create_material_expression(mat, u.MaterialExpressionCustom, -500, 700)
        setprops(surface, desc=TAG_GRASS, description='GrassMud (MR1)', output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
        custom_slots(surface, ['Base', 'WorldPos', 'ObjPos', 'Tex', 'Origin', 'GrassOn', 'Rand', 'MudDry', 'LineMinCm', 'LineMaxCm'])
        y = 800
        wpos = mel.create_material_expression(mat, u.MaterialExpressionWorldPosition, -900, y)
        wpos.set_editor_property('world_position_shader_offset', u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
        connect(wpos, '', surface, 'WorldPos')
        obj = mel.create_material_expression(mat, u.MaterialExpressionObjectPositionWS, -900, y + 100)
        connect(obj, '', surface, 'ObjPos')
        rt = mel.create_material_expression(mat, u.MaterialExpressionTextureObjectParameter, -900, y + 200)
        setprops(rt, parameter_name='GrassMud_TrackRT', texture=eal.load_asset(RT_PATH), sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,
                 sampler_source=u.SamplerSourceMode.SSM_CLAMP_WORLD_GROUP_SETTINGS)
        connect(rt, '', surface, 'Tex')
        mpc = eal.load_asset(MPC_PATH)
        for pin, param, dy in (('Origin', 'TrackOrigin', 300), ('GrassOn', 'GrassMud', 400)):
            node = mel.create_material_expression(mat, u.MaterialExpressionCollectionParameter, -900, y + dy)
            setprops(node, collection=mpc, parameter_name=param)
            connect(node, '', surface, pin)
        rand = mel.create_material_expression(mat, u.MaterialExpressionPerInstanceRandom, -900, y + 500)
        connect(rand, '', surface, 'Rand')
        dry = mel.create_material_expression(mat, u.MaterialExpressionVectorParameter, -900, y + 600)
        setprops(dry, parameter_name='GrassMudDryColor')
        connect(dry, '', surface, 'MudDry')
        for index, (param, value) in enumerate(GRASS_SCALARS.items()):
            node = mel.create_material_expression(mat, u.MaterialExpressionScalarParameter, -900, y + 700 + 90 * index)
            setprops(node, parameter_name=param, default_value=value)
            connect(node, '', surface, 'LineMinCm' if param.endswith('MinCm') else 'LineMaxCm')
    surface.set_editor_property('code', GRASS_HLSL)
    # MR2 housekeeping 2: the instance's origin reaches the pixel shader through a vertex interpolator. Read in the pixel shader,
    # ObjectPositionWS is the component's origin (MaterialTemplate.ush: the pixel parameters take the primitive's position, the
    # vertex parameters the instance's), so on the strips (component at the world origin, ground about 34 cm up) every blade
    # stood above its mud line.
    nodes = list(mel.get_material_expressions(mat))
    obj = next((e for e in nodes if isinstance(e, u.MaterialExpressionObjectPositionWS)), None)
    interp = next((e for e in nodes if isinstance(e, u.MaterialExpressionVertexInterpolator) and str(e.get_editor_property('desc')) == TAG_GRASS + ' origin'), None)
    if obj is not None and interp is None:
        interp = mel.create_material_expression(mat, u.MaterialExpressionVertexInterpolator, -700, 900)
        interp.set_editor_property('desc', TAG_GRASS + ' origin')
        connect(obj, '', interp, '')
        connect(interp, '', surface, 'ObjPos')
    colour = dry_mud_colour()
    for e in mel.get_material_expressions(mat):
        if isinstance(e, u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name')) == 'GrassMudDryColor':
            e.set_editor_property('default_value', u.LinearColor(colour[0], colour[1], colour[2], 1.0))
    switch = next((e for e in mel.get_material_expressions(mat) if isinstance(e, u.MaterialExpressionStaticSwitchParameter)
                   and str(e.get_editor_property('parameter_name')) == TAG_GRASS_SWITCH), None)
    if switch is None:
        switch = mel.create_material_expression(mat, u.MaterialExpressionStaticSwitchParameter, -250, 700)
        setprops(switch, parameter_name=TAG_GRASS_SWITCH, default_value=True)
        assert any(mel.connect_material_expressions(surface, '', switch, p) for p in ('True', 'A')), 'GrassMud switch True'
    # The base colour as it stood (vertex colour on M_TS_Grass, the weather call's BaseColor input on M_GT_FoliageCard).
    weather = _weather_call(mat)
    slot = Slot(mat, weather, 'BaseColor') if weather is not None else Slot(mat, prop=u.MaterialProperty.MP_BASE_COLOR)
    src, src_out = slot.feeder()
    how = 'kept'
    if src != switch:
        assert src is not None, '%s has nothing on its base colour' % mat.get_name()
        connect(src, src_out, surface, 'Base')
        assert any(mel.connect_material_expressions(src, src_out, switch, p) for p in ('False', 'B')), 'GrassMud switch False'
        slot.feed(switch, '')
        how = 'spliced'
    # Two-sided foliage's subsurface colour took the same vertex colour: the base's mud reaches it too.
    sub = mel.get_material_property_input_node(mat, u.MaterialProperty.MP_SUBSURFACE_COLOR)
    if sub is not None and sub != switch and weather is None and sub == mel.get_inputs_for_material_expression(mat, surface)[0]:
        assert mel.connect_material_property(switch, '', u.MaterialProperty.MP_SUBSURFACE_COLOR)
    errors = [str(e) for e in mel.recompile_material(mat)]
    eal.save_loaded_asset(mat)
    assert not errors, '%s: %s' % (mat.get_name(), errors)
    return dict(material=mat.get_path_name(), created=fresh, base=how, weather=weather is not None, dry_colour=colour,
                line_cm=[GRASS_SCALARS['GrassMudLineMinCm'], GRASS_SCALARS['GrassMudLineMaxCm']], compile_errors=errors)


def setup():
    """Everything, in order: the atlas, the collection, the function, the decal, the ground materials, the grass."""
    report = dict(textures=import_textures(), collection=ensure_mpc(), function=build_function(), decal=build_decal(), ground=[], grass=[])
    for path, tangent in COVER_MATERIALS:
        mat = eal.load_asset(path)
        report['ground'].append(wire_mud_cover(mat, tangent) if mat else dict(material=path, skipped='missing'))
    for path in GRASS_MATERIALS:
        mat = eal.load_asset(path)
        report['grass'].append(wire_grass_mud(mat) if mat else dict(material=path, skipped='missing'))
    return report
