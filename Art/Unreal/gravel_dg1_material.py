"""Deformable gravel DG1 item 2 (docs/DEFORMABLE_GRAVEL_PLAN.md DG1): M_GT_Gravel on the gravel field, M_GravelLandscape on the
same arrays, M_GT_GravelStone for the loose stones, and MPC_TrackPaint's GravelPOM / GravelDebug.

M_GT_Gravel (/Game/GrandTour/ArtTests/DeformableGravel, the profile's SurfaceMaterialPath) keeps M_GravelField's field displacement
(setup_m6_mud.py WPO_HLSL) and bicubic field normal (SURFACE_A's prefix) and paints the DG1 bakes (TA_GV_{Color,Normal,ORH}, slice 0
Loose, 1 Packed, a 2 m world tile; uv (x, -y) / 2 m as the bake lies, its DirectX green toward -y):
- the track blend: p = smoothstep(0.35, 0.7, T - 0.3 (hL - mean(hL))), T the study's worked mask (tracks x smoothstep(0.05, 1.5, cut
  cm)), hL the Loose slice's parallax height (ORH B), mean(hL) the bake's (Art/Export/GravelDG1/manifest.json track_blend.mean_hL);
  Packed's Color, Normal and ORH lerp in by p;
- the windrow: over 0-2 cm of positive field height, Loose's AO contrast x1.15 and the parallax depth x1.2;
- parallax occlusion: M_GT_Mud's POM (live_mud_style.py POM_HLSL: the field-normal frame, 6-14 m fade, adaptive 8-16 steps with a
  grazing floor of 12, 5 binary halvings and a secant, the 4-step sun self-shadow within 4 m) on one tiling; the height marched is the
  surface the pixel shows, lerp(Loose B x 0.8 cm, Packed B x 0.5 cm, p) in Loose's depth units (Packed's sample only where the track
  mask can reach p > 0), behind gt.Gravel.POM 0/1/2 (MPC_TrackPaint GravelPOM);
- PBR: roughness from ORH G (dry 0.55-0.9), the weather's wetness darkens the base colour to x0.75 and takes the roughness to 0.4 (never
  under), default specular (F0 0.04); the AO to the Ambient Occlusion output and a cavity tint of at most 0.15 (as the mud's);
- the study's grass verge blend and its x0.82 albedo calibration are kept;
- the pale edge line: the study's RepeatedPass line is drawn by the field normal (gt.Gravel.Debug 1, the flat normal, removes it; 2,
  no slide, and 3, no detail normal, do not; a B-spline slope in place of Catmull-Rom's drew it the same): the sun-lit wall of an
  even rut under a low sun, compressed by the grazing view into a thin pale line (no specular, fully rough: the same; the lighting
  normal flat: gone). The wall's lighting slope now varies along the rut (a two-octave 45 cm value noise, x 0.25-1.25) and stone
  by stone (x 0.8-1.2 by hL), and its tilt is soft-capped (slope / (1 + |slope| / 0.14), about 8 deg at most).
GravelDebug (MPC, 0 normally) is the pale-edge-line diagnosis: 1 draws the flat vertex normal instead of the field's, 2 drops the
texture's slide with the field (the study's q = P - Shift), 3 drops the baked detail normal.
M_GravelLandscape: the study's landscape copy, its Gravel: nodes rebuilt on the same arrays and uv (slice 0, no POM, no field).
M_GT_GravelStone (DG1b): the ground's own stone palette - per instance a stone face of the Loose bake through the ground's x0.82 colour
path with a small tint; roughness 0.75-0.85 per instance to 0.4 wet, darker wet, dithered out by the cull fade (25-35 m).
"""
import ast
import json
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
DEST = '/Game/GrandTour/ArtTests/DeformableGravel'
MPC_PATH = '/Game/GrandTour/Terrain/MPC_TrackPaint'
mel = u.MaterialEditingLibrary
eal = u.EditorAssetLibrary
ARRAYS = {'GC': ('TA_GV_Color', 'SAMPLERTYPE_COLOR'), 'GN': ('TA_GV_Normal', 'SAMPLERTYPE_NORMAL'), 'GO': ('TA_GV_ORH', 'SAMPLERTYPE_LINEAR_COLOR')}
MANIFEST = json.loads((ROOT / 'Art/Export/GravelDG1/manifest.json').read_text())
SCALARS = {
    'GravelTileCm': 200.0, 'GravelMeanHL': float(MANIFEST['track_blend']['mean_hL']), 'GravelSlideUV': 1.0,
    'GravelPomDepthCm': float(MANIFEST['parallax_depth_cm']['Loose']), 'GravelPackedDepthCm': float(MANIFEST['parallax_depth_cm']['Packed']),
    'GravelPomNearM': 6.0, 'GravelPomFarM': 14.0, 'GravelPomMinSteps': 8.0, 'GravelPomMaxSteps': 16.0, 'GravelPomGrazingMinSteps': 12.0,
    'GravelPomRefine': 5.0, 'GravelPomShadowM': 4.0, 'GravelPomShadowStrength': 0.45,
    'GravelWindrowAO': 1.15, 'GravelWindrowHeight': 1.2, 'GravelNormalStrength': 1.0, 'GravelAOStrength': 1.0, 'GravelCavityTint': 0.15,
    'GravelAlbedoScale': 0.82, 'GravelWetDarken': 0.75, 'GravelWetRough': 0.4,
    'GravelWallBreakLo': 0.25, 'GravelWallBreakHi': 1.25, 'GravelWallNoiseCm': 45.0, 'GravelWallTiltCap': 0.14,
}
LANDSCAPE_SCALARS = ['GravelTileCm', 'GravelNormalStrength', 'GravelAOStrength', 'GravelCavityTint', 'GravelAlbedoScale', 'GravelWetDarken', 'GravelWetRough']
MPC_SCALARS = {'GravelPOM': 2.0, 'GravelDebug': 0.0}


def props(o, **kw):
    for k, v in kw.items():
        o.set_editor_property(k, v)
    return o


def study_hlsl():
    tree = ast.parse((ROOT / 'Art/Unreal/setup_m6_mud.py').read_text())
    c = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
         if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ('WPO_HLSL', 'SURFACE_A')}
    return c['WPO_HLSL'], c['SURFACE_A'].split('// The ground this mesh')[0]


POM = '''struct GTGravelPom
{
    float2 UV; float2 Dx; float2 Dy; float Tile; float T; float MeanHL; float Ratio; bool Packed;
    float H(Texture2DArray O, SamplerState S, float3 o, float g)
    {
        float2 q = UV + float2(o.x, -o.y) / Tile;
        float hl = O.SampleGrad(S, float3(q, 0.0), Dx * g, Dy * g).b;
        if (!Packed) { return hl; }
        float hp = O.SampleGrad(S, float3(q, 1.0), Dx * g, Dy * g).b;
        return lerp(hl, hp * Ratio, smoothstep(0.35, 0.7, T - 0.3 * (hl - MeanHL)));
    }
};
{
    float pmDist = length(gEye - CamPos);
    float pmFade = 1.0 - smoothstep(GravelPomNearM * 100.0, max(GravelPomFarM, GravelPomNearM + 0.01) * 100.0, pmDist);
    [branch] if (GravelPOM > 0.5 && pmFade > 0.001)
    {
        GTGravelPom Pm;
        Pm.UV = gUV; Pm.Dx = gDx; Pm.Dy = gDy; Pm.Tile = gTile; Pm.T = gT; Pm.MeanHL = GravelMeanHL;
        Pm.Ratio = GravelPackedDepthCm / max(GravelPomDepthCm, 0.01);
        Pm.Packed = gT > 0.13;   // below it p is 0 whatever hL (0.35 - 0.3 x (1 - mean))
        float3 pmV = normalize(gEye - CamPos);
        float pmVn = min(dot(pmV, n), -0.2);
        float3 pmVt = pmV - n * dot(pmV, n);
        float pmDepth = max(GravelPomDepthCm, 0.0) * pmFade * lerp(1.0, GravelWindrowHeight, gWindrow);
        float pmSurf = 1.0 - Pm.H(GO, GOSampler, float3(0.0, 0.0, 0.0), 2.0);
        float3 pmSlide = pmVt / (-pmVn) * pmDepth;
        float pmT = saturate((-pmVn - 0.2) / 0.8);
        float pmSteps = GravelPomMinSteps;
        if (GravelPOM > 1.5)
        {
            float pmFloor = lerp(GravelPomGrazingMinSteps, GravelPomMinSteps, pmT);
            pmSteps = lerp(pmFloor, lerp(GravelPomMaxSteps, GravelPomMinSteps, pmT), pmFade);
        }
        int pmN = (int)clamp(round(pmSteps), 4.0, 16.0);
        float pmStep = 1.0 / (float)pmN;
        float pmD = 0.0;
        float pmPrevD = 0.0;
        [loop] for (int pmK = 0; pmK < 16; ++pmK)
        {
            if (pmK >= pmN || pmD >= pmSurf) break;
            pmPrevD = pmD;
            pmD += pmStep;
            pmSurf = 1.0 - Pm.H(GO, GOSampler, pmSlide * pmD, 2.0);
        }
        float pmLo = pmPrevD;
        float pmHi = pmD;
        float pmFLo = (1.0 - Pm.H(GO, GOSampler, pmSlide * pmLo, 1.0)) - pmLo;
        float pmFHi = (1.0 - Pm.H(GO, GOSampler, pmSlide * pmHi, 1.0)) - pmHi;
        int pmR = (int)clamp(GravelPomRefine, 0.0, 6.0);
        [loop] for (int pmB = 0; pmB < 6; ++pmB)
        {
            if (pmB >= pmR) break;
            float pmMid = 0.5 * (pmLo + pmHi);
            float pmFMid = (1.0 - Pm.H(GO, GOSampler, pmSlide * pmMid, 1.0)) - pmMid;
            if (pmFMid > 0.0) { pmLo = pmMid; pmFLo = pmFMid; } else { pmHi = pmMid; pmFHi = pmFMid; }
        }
        float pmHit = lerp(pmLo, pmHi, saturate(pmFLo / max(pmFLo - pmFHi, 1e-5)));
        pomOff = pmSlide * pmHit;
        float pmSh = 1.0 - smoothstep(0.75 * GravelPomShadowM * 100.0, max(GravelPomShadowM, 0.01) * 100.0, pmDist);
        float3 pmL = normalize(SunDir);
        float pmLn = dot(pmL, n);
        [branch] if (pmSh > 0.001 && pmLn > 0.05 && pmHit > 0.02)
        {
            float3 pmLs = (pmL - n * pmLn) / pmLn * pmDepth;
            float pmOcc = 0.0;
            [unroll] for (int pmJ = 0; pmJ < 4; ++pmJ)
            {
                float pmRay = pmHit * (1.0 - (pmJ + 1) / 5.0);
                float pmTop = 1.0 - Pm.H(GO, GOSampler, pomOff + pmLs * (pmHit - pmRay), 2.0);
                pmOcc = max(pmOcc, saturate((pmRay - pmTop) * 6.0));
            }
            pomShade = pmOcc * pmSh;
        }
    }
}
'''

SAMPLE = '''// The two slices at the parallax-slid uv (the derivatives the un-slid uv's); Packed only where p reaches over 0.
float2 sUV = gUV + float2(pomOff.x, -pomOff.y) / gTile;
float4 oL = GO.SampleGrad(GOSampler, float3(sUV, 0.0), gDx, gDy);
float gP = smoothstep(0.35, 0.7, gT - 0.3 * (oL.b - GravelMeanHL));
float3 col = GC.SampleGrad(GCSampler, float3(sUV, 0.0), gDx, gDy).rgb;
float2 nd = UnpackNormalMap(GN.SampleGrad(GNSampler, float3(sUV, 0.0), gDx, gDy)).xy;
float ao = 1.0 - (1.0 - oL.r) * lerp(1.0, GravelWindrowAO, gWindrow);   // the windrow: denser stones, deeper gaps
float rough = oL.g;
[branch] if (gP > 0.001)
{
    float4 oP = GO.SampleGrad(GOSampler, float3(sUV, 1.0), gDx, gDy);
    col = lerp(col, GC.SampleGrad(GCSampler, float3(sUV, 1.0), gDx, gDy).rgb, gP);
    nd = lerp(nd, UnpackNormalMap(GN.SampleGrad(GNSampler, float3(sUV, 1.0), gDx, gDy)).xy, gP);
    ao = lerp(ao, oP.r, gP);
    rough = lerp(rough, oP.g, gP);
}
'''

FINISH = '''// The study's calibration and its grass verge (the strip's road runs along y = 0).
col *= GravelAlbedoScale;
float gGrass = smoothstep(375.0, 590.0, abs(WorldPos.y));
float gVar = 0.5 + 0.5 * sin(WorldPos.x * 0.006) * sin(WorldPos.y * 0.008);
col = lerp(col, lerp(float3(0.10, 0.081, 0.046), float3(0.18, 0.147, 0.077), gVar), gGrass);
// PBR: the weather's wetness darkens to x GravelWetDarken and takes the roughness to GravelWetRough (never under); the AO.
float gWet = saturate(Wetness);
col *= lerp(1.0, GravelWetDarken, gWet);
rough = max(lerp(rough, GravelWetRough, gWet), GravelWetRough);
ao = lerp(1.0, ao, saturate(GravelAOStrength));
col *= 1.0 - saturate(GravelCavityTint) * (1.0 - ao);
'''


def build_field():
    wpo, prefix = study_hlsl()
    path = DEST + '/M_GT_Gravel'
    m = eal.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_GT_Gravel', DEST, u.Material, u.MaterialFactoryNew())
    for e in list(mel.get_material_expressions(m)):
        mel.delete_material_expression(m, e)
    props(m, tangent_space_normal=False)
    row = [0]

    def expr(cls, x=-2200, **kw):
        row[0] += 120
        return props(mel.create_material_expression(m, cls, x, row[0]), **kw)

    def wire(a, b, name, out=''):
        assert mel.connect_material_expressions(a, out, b, name), name

    def custom(code, inputs, kind=u.CustomMaterialOutputType.CMOT_FLOAT3, outputs=()):
        n = expr(u.MaterialExpressionCustom, x=-600, code=code, output_type=kind)
        n.set_editor_property('inputs', [props(u.CustomInput(), input_name=k) for k in inputs])
        n.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name=k, output_type=t) for k, t in outputs])
        return n
    p = expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    vn = expr(u.MaterialExpressionVertexNormalWS)
    wet = expr(u.MaterialExpressionCollectionParameter, collection=u.load_asset('/Game/GrandTour/Materials/MPC_Weather'), parameter_name='Wetness')
    mpc = u.load_asset(MPC_PATH)
    pom = expr(u.MaterialExpressionCollectionParameter, collection=mpc, parameter_name='GravelPOM')
    dbg = expr(u.MaterialExpressionCollectionParameter, collection=mpc, parameter_name='GravelDebug')
    cam = expr(u.MaterialExpressionCameraPositionWS)
    sun = expr(u.MaterialExpressionSkyAtmosphereLightDirection, light_index=0)
    zero = expr(u.MaterialExpressionConstant, r=0.0)
    field = expr(u.MaterialExpressionTextureObjectParameter, parameter_name='MudField', texture=u.load_asset('/Game/GrandTour/Terrain/RT_TrackPaint'),
                 sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    params = {name: expr(u.MaterialExpressionVectorParameter, parameter_name=name, default_value=u.LinearColor(*val, 1))
              for name, val in [('PatchMin', (0, 0, 0)), ('PatchSize', (100, 100, 0)), ('PatchTexels', (8, 8, 0))]}
    displace = custom(wpo, ['WorldPos', 'PatchMin', 'PatchSize', 'PatchTexels', 'Tex', 'SlideScale'])
    for name, node in params.items():
        wire(node, displace, name)
    wire(p, displace, 'WorldPos')
    wire(field, displace, 'Tex')
    wire(zero, displace, 'SlideScale')
    assert mel.connect_material_property(displace, '', u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    code = prefix + '''// ==== Deformable gravel DG1: M_GT_Gravel (Art/Unreal/gravel_dg1_material.py) ====
if (GravelDebug > 0.5 && GravelDebug < 1.5) { n = normalize(VertexNormal.xyz); }   // the diagnosis: no field slope
float gCut = max(0.0, -s.r * 100.0);
float gT = saturate(tracks) * smoothstep(0.05, 1.5, gCut);   // the study's worked mask: the track blend's T
float gWindrow = saturate(s.r * 100.0 / 2.0);                 // 0-2 cm of displaced windrow
float3 gEye = WorldPos + float3(0.0, 0.0, s.r * 100.0);       // the displaced point the eye sees
float gSlide = (GravelDebug > 1.5 && GravelDebug < 2.5) ? 0.0 : GravelSlideUV;
float2 gq = WorldPos.xy - s.gb * 100.0 * gSlide;            // the study's q: the texture slides with the field
float gTile = max(GravelTileCm, 1.0);
float2 gUV = float2(gq.x, -gq.y) / gTile;
float2 gDx = ddx(gUV);
float2 gDy = ddy(gUV);
float3 pomOff = float3(0.0, 0.0, 0.0);
float pomShade = 0.0;
''' + POM + SAMPLE + FINISH + '''col *= 1.0 - saturate(GravelPomShadowStrength) * pomShade;
float3 gDetail = (GravelDebug > 2.5) ? float3(0.0, 0.0, 0.0) : float3(nd.x, -nd.y, 0.0) * GravelNormalStrength;   // DirectX green: -y
// The pale edge line (the study's RepeatedPass; gt.Gravel.Debug 1-3): the field normal's sun-lit rut wall. The cut is even all
// along a rut, so its sun-facing wall (about 25 cm, ~15 deg) lights as one strip that a grazing view compresses into a thin pale
// line (the shadowed wall into the dark stripe). The wall's slope now varies along the rut - a two-octave value noise of
// GravelWallNoiseCm, x GravelWallBreakLo..Hi - and stone by stone (x 0.8-1.2 by hL), so it catches the light in broken, uneven
// stretches. Flat ground (no field slope) is untouched.
float3 gN = n;
if (GravelDebug < 0.5 || GravelDebug > 1.5)
{
    float2 gwc = WorldPos.xy / max(GravelWallNoiseCm, 1.0);
    float2 gwi = floor(gwc); float2 gwf = frac(gwc); gwf = gwf * gwf * (3.0 - 2.0 * gwf);
    float gw00 = frac(sin(dot(gwi, float2(127.1, 311.7))) * 43758.5453); float gw10 = frac(sin(dot(gwi + float2(1, 0), float2(127.1, 311.7))) * 43758.5453);
    float gw01 = frac(sin(dot(gwi + float2(0, 1), float2(127.1, 311.7))) * 43758.5453); float gw11 = frac(sin(dot(gwi + float2(1, 1), float2(127.1, 311.7))) * 43758.5453);
    float gwn = 0.65 * lerp(lerp(gw00, gw10, gwf.x), lerp(gw01, gw11, gwf.x), gwf.y);
    float2 gwc2 = gwc * 2.31 + float2(17.3, -9.1);
    float2 gwj = floor(gwc2); float2 gwg = frac(gwc2); gwg = gwg * gwg * (3.0 - 2.0 * gwg);
    float gv00 = frac(sin(dot(gwj, float2(269.5, 183.3))) * 43758.5453); float gv10 = frac(sin(dot(gwj + float2(1, 0), float2(269.5, 183.3))) * 43758.5453);
    float gv01 = frac(sin(dot(gwj + float2(0, 1), float2(269.5, 183.3))) * 43758.5453); float gv11 = frac(sin(dot(gwj + float2(1, 1), float2(269.5, 183.3))) * 43758.5453);
    gwn += 0.35 * lerp(lerp(gv00, gv10, gwg.x), lerp(gv01, gv11, gwg.x), gwg.y);
    float gWallK = lerp(GravelWallBreakLo, GravelWallBreakHi, saturate(gwn)) * lerp(0.8, 1.2, oL.b);
    // And the macro tilt is soft-capped (GravelWallTiltCap, the tangent): under a low sun a few degrees of tilt toward it is a big
    // change of light, so the walls' light and shadow stay a shading of the gravel, not a stripe; the relief is drawn by the
    // parallax, the track blend, the stones and the AO.
    float2 gS = slope * gWallK;
    gS /= 1.0 + length(gS) / max(GravelWallTiltCap, 0.001);
    gN = normalize(float3(vn.xy / nz - gS, 1.0));
}
if (GravelDebug > 3.5 && GravelDebug < 4.5) { gN = normalize(VertexNormal.xyz); }   // the diagnosis: the lighting's normal flat, the parallax's frame the field's
Spec = (GravelDebug > 4.5 && GravelDebug < 5.5) ? 0.0 : 0.5;   // default specular (F0 0.04); the diagnosis 5: none
if (GravelDebug > 5.5) { rough = 1.0; }                        // the diagnosis 6: fully rough
Normal = normalize(gN + gDetail);
Rough = rough;
Occl = 1.0 - ao;
return col;
'''
    scalars = {k: expr(u.MaterialExpressionScalarParameter, parameter_name=k, default_value=v) for k, v in SCALARS.items()}
    names = ['WorldPos', 'PatchMin', 'PatchSize', 'PatchTexels', 'Tex', 'VertexNormal', 'Wetness', 'CamPos', 'SunDir', 'GravelPOM', 'GravelDebug'] + list(ARRAYS) + list(SCALARS)
    surf = custom(code, names, outputs=[('Normal', u.CustomMaterialOutputType.CMOT_FLOAT3), ('Rough', u.CustomMaterialOutputType.CMOT_FLOAT1),
                                        ('Occl', u.CustomMaterialOutputType.CMOT_FLOAT1), ('Spec', u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for name, node in params.items():
        wire(node, surf, name)
    for node, pin in [(p, 'WorldPos'), (field, 'Tex'), (vn, 'VertexNormal'), (wet, 'Wetness'), (cam, 'CamPos'), (sun, 'SunDir'), (pom, 'GravelPOM'), (dbg, 'GravelDebug')]:
        wire(node, surf, pin)
    for pin, (asset, sampler) in ARRAYS.items():
        tex = u.load_asset(DEST + '/' + asset)
        assert tex, 'no %s (Art/import_gravel_dg1.ps1)' % asset
        node = expr(u.MaterialExpressionTextureObjectParameter, parameter_name='Gravel_' + pin, texture=tex, sampler_type=getattr(u.MaterialSamplerType, sampler),
                    sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        wire(node, surf, pin)
    for name, node in scalars.items():
        wire(node, surf, name)
    one = expr(u.MaterialExpressionOneMinus, x=-250)
    wire(surf, one, '', 'Occl')
    for node, out, prop in [(surf, '', u.MaterialProperty.MP_BASE_COLOR), (surf, 'Normal', u.MaterialProperty.MP_NORMAL),
                            (surf, 'Rough', u.MaterialProperty.MP_ROUGHNESS), (one, '', u.MaterialProperty.MP_AMBIENT_OCCLUSION),
                            (surf, 'Spec', u.MaterialProperty.MP_SPECULAR)]:
        assert mel.connect_material_property(node, out, prop), str(prop)
    errors = mel.recompile_material(m)
    assert not errors, str(errors)
    eal.save_loaded_asset(m)
    return dict(material=path, arrays={k: DEST + '/' + v[0] for k, v in ARRAYS.items()}, scalars=SCALARS, mpc=list(MPC_SCALARS),
                expressions=len(mel.get_material_expressions(m)))


def build_landscape():
    path = DEST + '/M_GravelLandscape'
    m = eal.load_asset(path)
    assert m, 'no ' + path + ' (the study setup duplicates it from M_GT_Landscape)'
    for e in list(mel.get_material_expressions(m)):
        if str(e.get_editor_property('desc')).startswith('Gravel:') or isinstance(e, u.MaterialExpressionLandscapeGrassOutput):
            mel.delete_material_expression(m, e)
    props(m, tangent_space_normal=False)
    row = [0]

    def expr(cls, **kw):
        row[0] += 140
        return props(mel.create_material_expression(m, cls, -2200, row[0]), desc='Gravel:' + str(row[0]), **kw)

    def wire(a, b, name, out=''):
        assert mel.connect_material_expressions(a, out, b, name), name
    p = expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    vn = expr(u.MaterialExpressionVertexNormalWS)
    wet = expr(u.MaterialExpressionCollectionParameter, collection=u.load_asset('/Game/GrandTour/Materials/MPC_Weather'), parameter_name='Wetness')
    code = '''// Deformable gravel DG1 (Art/Unreal/gravel_dg1_material.py): the patch's Loose slice on the same 2 m world tile, no field, no POM.
float2 WorldPosXY = WorldPos.xy;
float2 gUV = float2(WorldPosXY.x, -WorldPosXY.y) / max(GravelTileCm, 1.0);
float2 gDx = ddx(gUV);
float2 gDy = ddy(gUV);
float4 oL = GO.SampleGrad(GOSampler, float3(gUV, 0.0), gDx, gDy);
float3 col = GC.SampleGrad(GCSampler, float3(gUV, 0.0), gDx, gDy).rgb;
float2 nd = UnpackNormalMap(GN.SampleGrad(GNSampler, float3(gUV, 0.0), gDx, gDy)).xy;
float ao = oL.r;
float rough = oL.g;
''' + FINISH + '''Normal = normalize(normalize(VertexNormal.xyz) + float3(nd.x, -nd.y, 0.0) * GravelNormalStrength);
Rough = rough;
AO = ao;
return col;
'''
    surf = expr(u.MaterialExpressionCustom, code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    names = ['WorldPos', 'VertexNormal', 'Wetness'] + list(ARRAYS) + LANDSCAPE_SCALARS
    surf.set_editor_property('inputs', [props(u.CustomInput(), input_name=k) for k in names])
    surf.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name=k, output_type=t) for k, t in
                                                    [('Normal', u.CustomMaterialOutputType.CMOT_FLOAT3), ('Rough', u.CustomMaterialOutputType.CMOT_FLOAT1),
                                                     ('AO', u.CustomMaterialOutputType.CMOT_FLOAT1)]])
    for node, pin in [(p, 'WorldPos'), (vn, 'VertexNormal'), (wet, 'Wetness')]:
        wire(node, surf, pin)
    for pin, (asset, sampler) in ARRAYS.items():
        node = expr(u.MaterialExpressionTextureObject, texture=u.load_asset(DEST + '/' + asset), sampler_type=getattr(u.MaterialSamplerType, sampler))
        wire(node, surf, pin)
    for name in LANDSCAPE_SCALARS:
        wire(expr(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=SCALARS[name]), surf, name)
    # Keep all six physical landscape layers referenced (the study's), with the same appearance.
    layer = expr(u.MaterialExpressionLandscapeLayerBlend)
    layers = ['Tarmac', 'Dirt', 'Mud', 'Snow', 'Scrub', 'Bog']
    layer.set_editor_property('layers', [props(u.LayerBlendInput(), layer_name=name, blend_type=u.LandscapeLayerBlendType.LB_WEIGHT_BLEND) for name in layers])
    for name in layers:
        wire(surf, layer, 'Layer ' + name)
    for node, out, prop in [(layer, '', u.MaterialProperty.MP_BASE_COLOR), (surf, 'Normal', u.MaterialProperty.MP_NORMAL),
                            (surf, 'Rough', u.MaterialProperty.MP_ROUGHNESS), (surf, 'AO', u.MaterialProperty.MP_AMBIENT_OCCLUSION)]:
        assert mel.connect_material_property(node, out, prop), str(prop)
    errors = mel.recompile_material(m)
    assert not errors, str(errors)
    eal.save_loaded_asset(m)
    return dict(material=path, arrays='slice 0 (Loose), uv (x, -y) / 2 m, no POM', scalars=LANDSCAPE_SCALARS)


def build_stone():
    """M_GT_GravelStone (DG1b): the loose stones in the ground's own stone palette. Each instance (PerInstanceRandom) picks a point
    of the Loose bake that lies on a stone face (ORH B over StoneFaceHeight; up to eight hashed tries, the last kept) and takes the
    bake's colour there one mip up (an ~8 mm average of the face), through the ground's colour path (x GravelAlbedoScale 0.82) with a
    small per-instance tint (x StoneTintLo..Hi); roughness StoneRoughLo..Hi per instance (0.75-0.85), wet x0.75 and to 0.4. The
    meshes' vertex colours (the study's palette, which import near-black) are no longer read. The cull fade is dithered."""
    path = DEST + '/M_GT_GravelStone'
    m = eal.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_GT_GravelStone', DEST, u.Material, u.MaterialFactoryNew())
    for e in list(mel.get_material_expressions(m)):
        mel.delete_material_expression(m, e)
    # DG1b: the instanced-static-mesh usage (without it the HISMs drew the engine's default material: DG1's near-black specks).
    props(m, blend_mode=u.BlendMode.BLEND_MASKED, dithered_lod_transition=True, used_with_instanced_static_meshes=True)
    y = [0]

    def expr(cls, **kw):
        y[0] += 120
        return props(mel.create_material_expression(m, cls, -900, y[0]), **kw)
    rnd = expr(u.MaterialExpressionPerInstanceRandom)
    wet = expr(u.MaterialExpressionCollectionParameter, collection=u.load_asset('/Game/GrandTour/Materials/MPC_Weather'), parameter_name='Wetness')
    fade = expr(u.MaterialExpressionPerInstanceFadeAmount)
    screen = expr(u.MaterialExpressionScreenPosition)
    code = '''// Deformable gravel DG1b: a stone face of the ground's own Loose bake per instance, the ground's colour path, PBR, the dithered fade.
float r = Rnd;
float2 q = float2(0.5, 0.5);
[loop] for (int k = 0; k < 8; ++k)
{
    q = frac(sin(float2(r * 127.1 + k * 311.7, r * 269.5 + k * 183.3)) * 43758.5453);
    if (GO.SampleLevel(GOSampler, float3(q, 0.0), 0.0).b > StoneFaceHeight) { break; }
}
float3 c = GC.SampleLevel(GCSampler, float3(q, 0.0), 3.0).rgb * AlbedoScale * lerp(StoneTintLo, StoneTintHi, frac(r * 7.31 + 0.13));
float w = saturate(Wetness);
Rough = lerp(lerp(StoneRoughLo, StoneRoughHi, frac(r * 3.17 + 0.41)), 0.4, w);
float ign = frac(52.9829189 * frac(dot(Pixel.xy, float2(0.06711056, 0.00583715))));
Opacity = saturate(Fade) > ign ? 1.0 : 0.0;   // PerInstanceFadeAmount: 1 shown, 0 faded out (the cull 25-35 m)
return c * lerp(1.0, 0.75, w);
'''
    c = expr(u.MaterialExpressionCustom, code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    names = ['Rnd', 'Wetness', 'Fade', 'Pixel', 'GC', 'GO', 'AlbedoScale', 'StoneFaceHeight', 'StoneTintLo', 'StoneTintHi', 'StoneRoughLo', 'StoneRoughHi']
    c.set_editor_property('inputs', [props(u.CustomInput(), input_name=k) for k in names])
    c.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name=k, output_type=u.CustomMaterialOutputType.CMOT_FLOAT1) for k in ['Rough', 'Opacity']])
    for node, pin in [(rnd, 'Rnd'), (wet, 'Wetness'), (fade, 'Fade')]:
        assert mel.connect_material_expressions(node, '', c, pin), pin
    assert mel.connect_material_expressions(screen, 'PixelPosition', c, 'Pixel'), 'Pixel'
    for pin in ('GC', 'GO'):
        asset, sampler = ARRAYS[pin]
        node = expr(u.MaterialExpressionTextureObject, texture=u.load_asset(DEST + '/' + asset), sampler_type=getattr(u.MaterialSamplerType, sampler))
        assert mel.connect_material_expressions(node, '', c, pin), pin
    for name, value in [('AlbedoScale', SCALARS['GravelAlbedoScale']), ('StoneFaceHeight', 0.45), ('StoneTintLo', 0.92), ('StoneTintHi', 1.06),
                        ('StoneRoughLo', 0.75), ('StoneRoughHi', 0.85)]:
        node = expr(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)
        assert mel.connect_material_expressions(node, '', c, name), name
    for node, out, prop in [(c, '', u.MaterialProperty.MP_BASE_COLOR), (c, 'Rough', u.MaterialProperty.MP_ROUGHNESS), (c, 'Opacity', u.MaterialProperty.MP_OPACITY_MASK)]:
        assert mel.connect_material_property(node, out, prop), str(prop)
    errors = mel.recompile_material(m)
    assert not errors, str(errors)
    eal.save_loaded_asset(m)
    return dict(material=path, colour='a Loose-bake stone face per instance (ORH B > 0.45, mip 3) x 0.82 x 0.92-1.06',
                rough='0.75-0.85 per instance, to 0.4 wet', fade='PerInstanceFadeAmount, interleaved-gradient dither, masked')


def ensure_mpc():
    mpc = eal.load_asset(MPC_PATH)
    assert mpc, 'no ' + MPC_PATH
    scalars = list(mpc.get_editor_property('scalar_parameters'))
    have = [str(s.get_editor_property('parameter_name')) for s in scalars]
    added = []
    for name, value in MPC_SCALARS.items():
        if name not in have:
            s = u.CollectionScalarParameter()
            s.set_editor_property('parameter_name', name)
            s.set_editor_property('default_value', value)
            scalars.append(s)
            added.append(name)
    if added:
        mpc.set_editor_property('scalar_parameters', scalars)
        eal.save_loaded_asset(mpc)
    return dict(mpc=MPC_PATH, added=added, scalars=len(scalars))


def build_all():
    out = dict(mpc=ensure_mpc())
    out['field'] = build_field()
    out['landscape'] = build_landscape()
    out['stone'] = build_stone()
    return out
