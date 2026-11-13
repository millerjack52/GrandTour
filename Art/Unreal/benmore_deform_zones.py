"""Benmore integration B2 / B2c (docs/BENMORE_INTEGRATION_PLAN.md B2, its addendum and B2c): the deform zones' material side.

Shared (GrandTour, /Game/GrandTour/Terrain/DeformZones):
- T_GT_DeformCoverageNone: the coverage parameter's default (black, linear; Art/Export/BenmoreB2/T_GT_DeformCoverageNone.png).
- T_GT_MudZoneMask / T_GT_MudZoneColour (B2c): the far maps AGTDeformZone::BakeMudMaps writes (FAR_*): R the mud's opacity and G the
  apron round it at 50 cm; each mud zone's wet mud colour at 2 m.
- M_GC_Terrain_Zone (B2c): the review terrain material itself, copied after attach_deform, worn by the gravel zones' patches: the same
  layers, textures, tiling, world UVs, tints and parallax as the road it replaces, with the deformation on top - the field's displacement
  and slope, the DG1 track blend (Codex's loose share taken to the packed gravel where the field has tracks, x0.92 value, the parallax
  x0.5) and the windrows' shade; it draws on the patch's side of the coverage dither.
- M_GT_Mud_Zone (B2c): M_GT_Mud copied with MudTint (vector, white by default) on its base colour - a zone's Benmore palette - and
  drawn on the patch's side of the dither. The strips keep M_GT_Mud and M_GT_Gravel untouched.
- T_RL_Vegetation (B2b): Morphology/T_RL_Vegetation with the bogs' inner 70 % painted out (Art/benmore_b2_plan.py).

attach_deform(m) on the review terrain material (M_GC_Terrain; benmore_gt_ground.attach calls it, so install_benmore_shore's rebuild
keeps it, and it rebuilds M_GC_Terrain_Zone from the result). Repeatable: the GTDeform: nodes go and the original wiring comes back first.
- GTDeformCoverage / GTDeformWindow: what UGTMudSubsystem writes into the landscape's and the zone patches' dynamic instances.
- The opacity mask x Keep: the coverage's A is how much of a live patch draws (faded out over 40-60 m from the camera); a per-pixel
  dither (interleaved gradient noise, the frame's index) gives each pixel to the patch where it is under A and to the landscape where it
  is not, so the two never share a pixel and the feather of a mud zone blends by TAA (the material is Masked already, clip 0.5).
- Near the mud zones (the far maps): the apron (G) wet-darkens the ground (value x0.62, saturation x1.15), more on Codex's wheel paths so
  the tracks run on as wet dark ruts, with splatter in the zone's mud colour; inside a zone (R) the ground is the zone's wet mud colour x
  the bog bake's luminance detail - what a mud zone looks like beyond its live patch, crossfading into the patch.
- The vegetation sample swapped to the copy when it exists.
"""
import re
import sys
import ast
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
from benmore_reference_surface import TRACKS   # noqa: E402  Codex's road-relative wheel paths (track, loose, lateral, halfWidth)

ZONES = '/Game/GrandTour/Terrain/DeformZones'
TAG = 'GTDeform:'
TERRAIN = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/ShoreRefinement/M_GC_Terrain'
ROAD_ZONE = ZONES + '/M_GC_Terrain_Zone'
MUD_SRC = '/Game/GrandTour/Materials/M_GT_Mud'
MUD_ZONE = ZONES + '/M_GT_Mud_Zone'
COVER_NONE = ZONES + '/T_GT_DeformCoverageNone'
FAR_MASK = ZONES + '/T_GT_MudZoneMask'
FAR_COLOUR = ZONES + '/T_GT_MudZoneColour'
BOG_COLOUR = '/Game/GrandTour/ArtTests/MudStyle/TA_MS_BogColor'
VEG_COPY = ZONES + '/T_RL_Vegetation'
VEG_SRC = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/T_RL_Vegetation'
EXPORT = ROOT / 'Art/Export/BenmoreB2'
# The far maps' square (cm): every mud zone of the plan with 10 m to spare; 4096 texels of 50 cm, the colour 1024 of 2 m.
FAR_ORIGIN = (-130200.0, -125800.0)
FAR_SIZE = 204800.0
FAR_MASK_SIZE = 4096
FAR_COLOUR_SIZE = 1024
FAR_APRON_CM = 200.0
# The four bog variants' mean albedo (linear; the TA_MS_BogColor slices' means) and the Standard slice's luminance.
BOG_MEAN = dict(STANDARD=(0.0703, 0.0400, 0.0186), FIRM=(0.0872, 0.0584, 0.0335), DEEP=(0.0492, 0.0290, 0.0134), STONY=(0.0688, 0.0439, 0.0225))
eal = u.EditorAssetLibrary
mel = u.MaterialEditingLibrary
CF1, CF2, CF3 = u.CustomMaterialOutputType.CMOT_FLOAT1, u.CustomMaterialOutputType.CMOT_FLOAT2, u.CustomMaterialOutputType.CMOT_FLOAT3
FRAME = 'View.StateFrameIndexMod8'   # the dither's frame term (set to '0' if a pass will not compile it)

COVERAGE_HLSL = r'''// Benmore B2c (Art/Unreal/benmore_deform_zones.py): the deform zones' coverage (UGTMudSubsystem round the focus): A how much of a live
// patch draws (blurred two texels), B a mud zone's variant code. A complementary dither shares each pixel: the patch draws where the
// dither is under A (faded out over 40-60 m from the camera), the landscape where it is not. Win: centre x, y, size (cm; off at 2 or under).
float4 c = float4(0.0, 0.0, 0.0, 0.0);
float2 uv = (P.xy - Win.xy) / max(Win.z, 1.0) + 0.5;
if (Win.z > 2.0 && all(uv > 0.0) && all(uv < 1.0))
{
    c = Texture2DSampleLevel(Tex, TexSampler, uv, 0.0);
}
#if SHADOW_DEPTH_SHADER
float a = c.a;   // the shadow map takes whichever surface the patch's coverage says, at any distance (its view is not the camera)
#else
float a = c.a * (1.0 - smoothstep(4000.0, 6000.0, length(Cam - P)));
#endif
float n = frac(52.9829189 * frac(dot(Pix.xy + 5.588238 * (float)(<FRAME>), float2(0.06711056, 0.00583715))));
Draw = (a > 0.0 && n < a) ? 1.0 : 0.0;
return 1.0 - Draw;
'''

NOISE = r'''struct GTZoneNoise { float V(float2 v) { float2 i = floor(v), f = frac(v); f = f * f * (3.0 - 2.0 * f);
float4 h = frac(sin(float4(dot(i, float2(127.1, 311.7)), dot(i + float2(1, 0), float2(127.1, 311.7)), dot(i + float2(0, 1), float2(127.1, 311.7)), dot(i + 1, float2(127.1, 311.7)))) * 43758.5453);
return lerp(lerp(h.x, h.y, f.x), lerp(h.z, h.w, f.x), f.y); } };
GTZoneNoise zn;
'''

FAR_HLSL = r'''// Benmore B2c: near the mud zones (the far maps T_GT_MudZoneMask: R the mud, G the apron; T_GT_MudZoneColour: the zone's wet mud).
float2 fuv = (P.xy - float2(<OX>, <OY>)) / <SIZE>;
float4 fm = float4(0.0, 0.0, 0.0, 0.0);
[branch] if (all(fuv > 0.0) && all(fuv < 1.0))
{
#if RAYHITGROUPSHADER
    fm = Texture2DSampleLevel(Far, FarSampler, fuv, 0.0);   // no implicit derivatives in a hit shader
#else
    fm = Texture2DSample(Far, FarSampler, fuv);
#endif
}
WetK = 0.0;
[branch] if (fm.r + fm.g < 0.003)
{
    return Src;
}
#if RAYHITGROUPSHADER
float3 mc = Texture2DSampleLevel(FarC, FarCSampler, fuv, 0.0).rgb;
#else
float3 mc = Texture2DSample(FarC, FarCSampler, fuv).rgb;
#endif
''' + TRACKS + '\n' + NOISE + r'''float n1 = zn.V(P.xy / 45.0);
float n2 = zn.V(P.xy / 11.0);
float n3 = zn.V(P.xy / 170.0);
// The apron: the ground wet-darkened (value x0.62, saturation x1.15), noise-broken, more on the wheel paths (the tracks run on as wet dark
// ruts onto the gravel, then fade), with splatter in the zone's mud colour.
float onRoad = saturate(Mask.r * 1.5);
float wet = saturate(fm.g * (0.45 + 0.8 * n3) + fm.g * track * onRoad * 0.7);
float l = dot(Src, float3(0.2126, 0.7152, 0.0722));
float3 col = lerp(Src, lerp(l.xxx, Src, 1.15) * 0.62, wet);
float splat = smoothstep(0.66, 0.74, n2) * smoothstep(0.35, 0.65, n1) * fm.g;
col = lerp(col, mc, splat * 0.9);
// Inside a zone (beyond its live patch, and under the patch's feather): the zone's wet mud x the bog bake's luminance detail (3 m tile).
#if RAYHITGROUPSHADER
float3 bogc = BogC.SampleLevel(BogCSampler, float3(P.xy / 300.0, 0.0), 0.0).rgb;
#else
float3 bogc = BogC.Sample(BogCSampler, float3(P.xy / 300.0, 0.0)).rgb;
#endif
float det = dot(bogc, float3(0.2126, 0.7152, 0.0722)) / 0.0453;
col = lerp(col, mc * clamp(det, 0.45, 1.8), fm.r);
WetK = max(wet, fm.r);
return col;
'''

FAR_ROUGH_HLSL = '// Benmore B2c: wet mud and wet ground are glossier.\nreturn lerp(Src, 0.5, saturate(WetK) * 0.75);\n'


def _field_hlsl():
    """setup_m6_mud's bicubic field read and its slope (the mud and gravel materials' own), then the track blend's T (DG1's study rule:
    the tracks factor x the cut, 0.05-1.5 cm), the slope and the windrow (0-2 cm up)."""
    tree = ast.parse((ROOT / 'Art/Unreal/setup_m6_mud.py').read_text())
    c = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
         if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ('WPO_HLSL', 'SURFACE_A')}
    surface = c['SURFACE_A']
    read = surface[:surface.index('float3 vn = normalize(VertexNormal.xyz);')]
    assert 'float2 slope' in read
    field = '// Benmore B2c: the deform field under a gravel zone\'s patch (setup_m6_mud\'s bicubic read and slope).\n' + read + \
        'SlopeX = slope.x;\nSlopeY = slope.y;\nWindrow = saturate(s.r * 100.0 / 2.0);\nreturn saturate(s.a) * smoothstep(0.05, 1.5, max(0.0, -s.r * 100.0));\n'
    return c['WPO_HLSL'], field


def props(o, **kw):
    for k, v in kw.items():
        o.set_editor_property(k, v)
    return o


def desc(e):
    try:
        return str(e.get_editor_property('desc') or '')
    except Exception:  # noqa: BLE001
        return ''


def _import_png(src, dest_path, srgb, compression):
    folder, name = dest_path.rsplit('/', 1)
    task = props(u.AssetImportTask(), filename=str(src), destination_path=folder, destination_name=name, automated=True, replace_existing=True, save=False)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = eal.load_asset(dest_path)
    assert tex, 'import failed: ' + dest_path
    tex.set_editor_property('srgb', srgb)
    tex.set_editor_property('compression_settings', compression)
    eal.save_loaded_asset(tex)
    return tex


def ensure_coverage_default():
    tex = _import_png(EXPORT / 'T_GT_DeformCoverageNone.png', COVER_NONE, False, u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
    tex.set_editor_property('filter', u.TextureFilter.TF_NEAREST)
    tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    eal.save_loaded_asset(tex)
    return tex.get_path_name()


def ensure_vegetation_copy():
    """Morphology/T_RL_Vegetation with the bogs painted out, its settings copied from the original."""
    src = eal.load_asset(VEG_SRC)
    assert src, VEG_SRC
    tex = _import_png(EXPORT / 'T_RL_Vegetation_B2.png', VEG_COPY, src.get_editor_property('srgb'), src.get_editor_property('compression_settings'))
    for k in ('filter', 'lod_group', 'mip_gen_settings', 'address_x', 'address_y', 'never_stream'):
        try:
            tex.set_editor_property(k, src.get_editor_property(k))
        except Exception:  # noqa: BLE001
            pass
    eal.save_loaded_asset(tex)
    return tex.get_path_name()


def import_far_maps(mask_png, colour_png):
    """The baked far maps: the mask linear BC7 (two smooth channels), the colour sRGB."""
    m = _import_png(mask_png, FAR_MASK, False, u.TextureCompressionSettings.TC_BC7)
    c = _import_png(colour_png, FAR_COLOUR, True, u.TextureCompressionSettings.TC_DEFAULT)
    for t in (m, c):
        t.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
        t.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
        eal.save_loaded_asset(t)
    return dict(mask=m.get_path_name(), colour=c.get_path_name())


def _unwrap(m):
    """The GTDeform: wrappers out (each one's first input back to its root property), then every GTDeform: node deleted."""
    restored = []
    for e in list(mel.get_material_expressions(m)):
        d = desc(e)
        if not d.startswith(TAG + 'wrap:'):
            continue
        _, _, prop, out = d.split(':', 3)
        ins = mel.get_inputs_for_material_expression(m, e)
        if ins and ins[0]:
            assert mel.connect_material_property(ins[0], out, getattr(u.MaterialProperty, prop)), d
            restored.append(prop)
    for e in list(mel.get_material_expressions(m)):
        if desc(e).startswith(TAG):
            mel.delete_material_expression(m, e)
    return restored


class _Graph:
    def __init__(self, m, x=2600, y=-2600):
        self.m, self.x, self.y = m, x, y

    def expr(self, cls, **kw):
        self.y += 110
        return props(mel.create_material_expression(self.m, cls, self.x, self.y), desc=TAG + str(self.y), **kw)

    def con(self, a, out, b, pin):
        assert mel.connect_material_expressions(a, out, b, pin), '%s -> %s' % (out, pin)

    def custom(self, code, ins, kind, outs=(), title=''):
        n = self.expr(u.MaterialExpressionCustom, code=code, output_type=kind, description=title)
        n.set_editor_property('inputs', [props(u.CustomInput(), input_name=k) for k in ins])
        if outs:
            n.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name=k, output_type=t) for k, t in outs])
        return n

    def wrap(self, prop_name, node, pin_or_none, out=''):
        """node takes the property's current input on pin_or_none (its first input) and goes to the property."""
        prop = getattr(u.MaterialProperty, prop_name)
        src = mel.get_material_property_input_node(self.m, prop)
        assert src, 'no input on ' + prop_name
        src_out = mel.get_material_property_input_node_output_name(self.m, prop) or ''
        self.con(src, src_out, node, pin_or_none)
        node.set_editor_property('desc', '%swrap:%s:%s' % (TAG, prop_name, src_out))
        assert mel.connect_material_property(node, out, prop), prop_name
        return '%s.%s' % (src.get_name(), src_out or '(main)')


def _coverage_nodes(g, frame=None):
    cover = eal.load_asset(COVER_NONE)
    assert cover, 'run ensure_coverage_default first'
    p = g.expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    pix = g.expr(u.MaterialExpressionScreenPosition)
    cam = g.expr(u.MaterialExpressionCameraPositionWS)
    tex = g.expr(u.MaterialExpressionTextureObjectParameter, parameter_name='GTDeformCoverage', texture=cover,
                 sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, sampler_source=u.SamplerSourceMode.SSM_CLAMP_WORLD_GROUP_SETTINGS)
    win = g.expr(u.MaterialExpressionVectorParameter, parameter_name='GTDeformWindow', default_value=u.LinearColor(0.0, 0.0, 1.0, 0.0))
    cov = g.custom(COVERAGE_HLSL.replace('<FRAME>', frame or FRAME), ['P', 'Pix', 'Cam', 'Tex', 'Win'], CF1, [('Draw', CF1)], 'Benmore B2c deform coverage')
    cov.set_editor_property('desc', TAG + 'coverage')
    for a, out, pin in [(p, '', 'P'), (pix, 'PixelPosition', 'Pix'), (cam, '', 'Cam'), (tex, '', 'Tex'), (win, '', 'Win')]:
        g.con(a, out, cov, pin)
    return cov, p


def _sample_node(m, name):
    for e in mel.get_material_expressions(m):
        if isinstance(e, u.MaterialExpressionTextureSample) and e.get_editor_property('texture') and e.get_editor_property('texture').get_name() == name:
            return e
    return None


def _compile(m):
    errors = [str(x) for x in mel.recompile_material(m)]
    return errors


def attach_deform(m, report=None, build_zone_material=True):
    """The coverage dither, the apron and the far mud on the review terrain material; the vegetation copy; then M_GC_Terrain_Zone from the
    result. The caller recompiles m (attach() does; setup_benmore_b2 too)."""
    report = report if report is not None else {}
    report['unwrapped'] = _unwrap(m)
    g = _Graph(m)
    cov, p = _coverage_nodes(g)
    wrapped = {}
    op = g.expr(u.MaterialExpressionMultiply)
    g.con(cov, '', op, 'B')
    wrapped['MP_OPACITY_MASK'] = g.wrap('MP_OPACITY_MASK', op, 'A')
    mask_tex, colour_tex, bog = eal.load_asset(FAR_MASK), eal.load_asset(FAR_COLOUR), eal.load_asset(BOG_COLOUR)
    road, coords = _sample_node(m, 'T_Benmore_RoadMask'), _sample_node(m, 'T_Benmore_RoadCoordinates')
    if mask_tex and colour_tex and bog and road and coords:
        code = FAR_HLSL.replace('<OX>', '%.1f' % FAR_ORIGIN[0]).replace('<OY>', '%.1f' % FAR_ORIGIN[1]).replace('<SIZE>', '%.1f' % FAR_SIZE)
        far = g.custom(code, ['Src', 'P', 'Mask', 'Coords', 'Far', 'FarC', 'BogC'], CF3, [('WetK', CF1)], 'Benmore B2c mud zones near and far')
        for node, out, pin in [(p, '', 'P'), (road, 'RGB', 'Mask'), (coords, 'RGB', 'Coords')]:
            g.con(node, out, far, pin)
        for tex, pin, ss, st in [(mask_tex, 'Far', u.SamplerSourceMode.SSM_CLAMP_WORLD_GROUP_SETTINGS, u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
                                 (colour_tex, 'FarC', u.SamplerSourceMode.SSM_CLAMP_WORLD_GROUP_SETTINGS, u.MaterialSamplerType.SAMPLERTYPE_COLOR),
                                 (bog, 'BogC', u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS, u.MaterialSamplerType.SAMPLERTYPE_COLOR)]:
            node = g.expr(u.MaterialExpressionTextureObject, texture=tex, sampler_type=st)
            try:
                node.set_editor_property('sampler_source', ss)
            except Exception:  # noqa: BLE001
                pass
            g.con(node, '', far, pin)
        wrapped['MP_BASE_COLOR'] = g.wrap('MP_BASE_COLOR', far, 'Src')
        rough = g.custom(FAR_ROUGH_HLSL, ['Src', 'WetK'], CF1, (), 'Benmore B2c wet roughness')
        g.con(far, 'WetK', rough, 'WetK')
        wrapped['MP_ROUGHNESS'] = g.wrap('MP_ROUGHNESS', rough, 'Src')
    else:
        wrapped['far'] = 'not wired: %s' % dict(mask=bool(mask_tex), colour=bool(colour_tex), bog=bool(bog), road=bool(road), coords=bool(coords))
    report['wrapped'] = wrapped
    # The bogs' vegetation copy in place of Morphology/T_RL_Vegetation (the one vegetation sample: the grass and B1's weights).
    veg = eal.load_asset(VEG_COPY) if eal.does_asset_exist(VEG_COPY) else None
    swapped = []
    for e in mel.get_material_expressions(m):
        if isinstance(e, (u.MaterialExpressionTextureSample, u.MaterialExpressionTextureObject)):
            t = e.get_editor_property('texture')
            if t and t.get_name() == 'T_RL_Vegetation':
                want = veg if veg else eal.load_asset(VEG_SRC)
                if want and t.get_path_name() != want.get_path_name():
                    e.set_editor_property('texture', want)
                swapped.append(want.get_path_name() if want else None)
    report['vegetation'] = swapped
    if build_zone_material:
        try:
            report['road_zone_material'] = build_road_zone_material(m)
        except Exception as e:  # noqa: BLE001
            report['road_zone_material'] = 'failed: %s' % e
    return report


def _inject_track(m, g, track):
    """Codex's custom nodes in the copy: the loose share taken to the packed gravel where the field has tracks; the parallax x0.5 there."""
    done = []
    for e in mel.get_material_expressions(m):
        if not isinstance(e, u.MaterialExpressionCustom):
            continue
        code = e.get_editor_property('code')
        new = code
        mt = re.search(r'float loose=clamp\([^;]*;', new)
        if mt:
            new = new[:mt.end()] + '\nloose=lerp(loose,0.0,saturate(GTTrack));' + new[mt.end():]
        ms = re.search(r'float strength=[^;]*;', new)
        if ms:
            new = new[:ms.end()] + '\nstrength*=lerp(1.0,0.5,saturate(GTTrack));' + new[ms.end():]
        if new == code:
            continue
        e.set_editor_property('code', new)
        e.set_editor_property('inputs', list(e.get_editor_property('inputs')) + [props(u.CustomInput(), input_name='GTTrack')])
        g.con(track, '', e, 'GTTrack')
        done.append(dict(node=e.get_name(), loose=bool(mt), parallax=bool(ms)))
    return done


def build_road_zone_material(m=None):
    """M_GC_Terrain_Zone: the review terrain material (after attach_deform) copied for the gravel zones' patches, the deformation on top."""
    wpo_code, field_code = _field_hlsl()
    if eal.does_asset_exist(ROAD_ZONE):
        eal.delete_asset(ROAD_ZONE)
    z = eal.duplicate_asset(TERRAIN, ROAD_ZONE)
    assert z, ROAD_ZONE
    nodes = list(mel.get_material_expressions(z))
    op = next(e for e in nodes if desc(e).startswith(TAG + 'wrap:MP_OPACITY_MASK'))
    cov = next(e for e in nodes if desc(e) == TAG + 'coverage')
    g = _Graph(z, 3200, -2600)
    g.con(cov, 'Draw', op, 'B')   # the patch's side of the dither
    p = g.expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    pw = g.expr(u.MaterialExpressionWorldPosition)
    params = {name: g.expr(u.MaterialExpressionVectorParameter, parameter_name=name, default_value=u.LinearColor(*val, 1))
              for name, val in [('PatchMin', (0, 0, 0)), ('PatchSize', (100, 100, 0)), ('PatchTexels', (8, 8, 0))]}
    field_tex = g.expr(u.MaterialExpressionTextureObjectParameter, parameter_name='MudField', texture=u.load_asset('/Game/GrandTour/Terrain/RT_TrackPaint'),
                       sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    zero = g.expr(u.MaterialExpressionConstant, r=0.0)
    wpo = g.custom(wpo_code, ['WorldPos', 'PatchMin', 'PatchSize', 'PatchTexels', 'Tex', 'SlideScale'], CF3, (), 'Benmore B2c field displacement')
    field = g.custom(field_code, ['WorldPos', 'PatchMin', 'PatchSize', 'PatchTexels', 'Tex'], CF1, [('SlopeX', CF1), ('SlopeY', CF1), ('Windrow', CF1)],
                     'Benmore B2c field: track blend, slope, windrow')
    for node in (wpo, field):
        for name, pn in params.items():
            g.con(pn, '', node, name)
        g.con(field_tex, '', node, 'Tex')
    g.con(pw, '', wpo, 'WorldPos')
    g.con(zero, '', wpo, 'SlideScale')
    g.con(p, '', field, 'WorldPos')
    had_wpo = mel.get_material_property_input_node(z, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    assert not had_wpo, 'M_GC_Terrain has a world position offset: add, do not replace'
    assert mel.connect_material_property(wpo, '', u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    injected = _inject_track(z, g, field)
    col = g.custom('// Benmore B2c: the track blend\'s value (x0.92) and the windrows\' shade.\nreturn Src * lerp(1.0, 0.92, saturate(T)) * (1.0 - 0.12 * saturate(Windrow));\n',
                   ['Src', 'T', 'Windrow'], CF3, (), 'Benmore B2c ruts colour')
    g.con(field, '', col, 'T')
    g.con(field, 'Windrow', col, 'Windrow')
    base_from = g.wrap('MP_BASE_COLOR', col, 'Src')
    nrm = g.custom('// Benmore B2c: the field\'s slope on the tangent-space normal (tangents along world X), soft-capped so a rut wall is a shading.\n'
                   'float2 sl = float2(SlopeX, SlopeY);\nsl /= 1.0 + length(sl) / 0.3;\nreturn normalize(float3(Src.xy / max(Src.z, 0.2) - sl, 1.0));\n',
                   ['Src', 'SlopeX', 'SlopeY'], CF3, (), 'Benmore B2c ruts normal')
    g.con(field, 'SlopeX', nrm, 'SlopeX')
    g.con(field, 'SlopeY', nrm, 'SlopeY')
    normal_from = g.wrap('MP_NORMAL', nrm, 'Src')
    errors = _compile(z)
    if errors and any('StateFrameIndexMod8' in e for e in errors):
        raise RuntimeError('frame term: %s' % errors[:2])
    assert not errors, errors[:3]
    eal.save_loaded_asset(z)
    s = mel.get_statistics(z)
    return dict(material=z.get_path_name(), injected=injected, base_colour_from=base_from, normal_from=normal_from,
                pixel=s.num_pixel_shader_instructions, vertex=s.num_vertex_shader_instructions, samplers=s.num_samplers)


def build_mud_zone_material():
    """M_GT_Mud_Zone: M_GT_Mud copied, its base colour x MudTint, drawn on the patch's side of the dither."""
    if eal.does_asset_exist(MUD_ZONE):
        eal.delete_asset(MUD_ZONE)
    z = eal.duplicate_asset(MUD_SRC, MUD_ZONE)
    assert z, MUD_ZONE
    g = _Graph(z, -2400, 1200)
    tint = g.expr(u.MaterialExpressionVectorParameter, parameter_name='MudTint', default_value=u.LinearColor(1.0, 1.0, 1.0, 1.0))
    mul = g.expr(u.MaterialExpressionMultiply)
    g.con(tint, '', mul, 'B')
    base_from = g.wrap('MP_BASE_COLOR', mul, 'A')
    cov, _ = _coverage_nodes(g)
    op = g.expr(u.MaterialExpressionMultiply)
    g.con(cov, 'Draw', op, 'B')
    mask_from = g.wrap('MP_OPACITY_MASK', op, 'A')
    errors = _compile(z)
    assert not errors, errors[:3]
    eal.save_loaded_asset(z)
    s = mel.get_statistics(z)
    return dict(material=z.get_path_name(), base_colour_from=base_from, opacity_from=mask_from, blend_mode=str(z.get_editor_property('blend_mode')),
                pixel=s.num_pixel_shader_instructions, samplers=s.num_samplers)
