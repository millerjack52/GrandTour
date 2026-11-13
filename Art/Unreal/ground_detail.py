"""Ground relief GR2 phase B (docs/GROUND_RELIEF_PLAN.md GR2): the soil detail and the ground scatter on the test strips only
(L_MudVariants, L_GravelDeform, L_MudDrive). The strips' setup scripts call apply_strip() last; import_ground_detail.py imports the
assets and builds M_GT_GroundScatter.

The landscape (item 2). Each strip has its own copy of M_GT_Landscape (M_VariantsLandscape, M_LiveLandscape, M_GravelLandscape;
The Hide's M_GT_Landscape is not touched), so each copy takes the GroundDetail static switch (off, its default: the copy compiles
as before) and its strip folder an MI_GT_Landscape_Strips with the switch on, which the strip's landscape wears.
- Where: M_VariantsLandscape / M_LiveLandscape - the Scrub row (its colour, roughness and normal inputs of the three layer blends;
  the row's apron blend, groundtex's ClayBlend, keeps the mud's colour); M_GravelLandscape - its gravel surface's grass verge
  (smoothstep 3.75-5.9 m off the line, gravel_dg1_material.FINISH), on the material's outputs.
- Slices: slice 0 ScrubSoil; slice 1 SoilUnderGrass where the grass is dense: T_GD_Grass_<strip>, a 50 cm map of the strip's grass
  instances' root footprints (tussocks 0.55 m x their scale, the fine undergrass 0.40 m), blurred over 1 m, smoothstep 0.2-0.5 of
  the cover.
- Palette kept: colour = layer x (detail luminance / the slice's mean) at 70 %, the bake's own colour at the layer's luminance at 30 %
  (GDHueShare); the 13 m tint (damp 0.82/0.80/0.82 - dry 1.12/1.07/0.96 over noise 0.38-0.62) divided by its midpoint so the mean
  palette stays. Roughness the bake's (ORH G, 0.6-0.95); the normal the bake's (DirectX, uv (x, -y) / 2 m, as the gravel's).
- Anti-tile (the A2 manifest): sample B at a 2.7 m tile turned 37 deg and offset (0.37, 0.61), its normal turned back; blended by a 7 m
  gradient-noise fBm (3 octaves) through smoothstep 0.45-0.55.
- Parallax: the gravel's POM (gravel_dg1_material.POM: adaptive 8-16 steps, 3 bisections, a 4-step sun self-shadow within 4 m) over
  ORH B at 1.5 cm, full to 15 m and gone by 25 m; the whole detail fades into the old look over 25-40 m.
- Switch: gt.Ground.Detail (MPC_TrackPaint GroundDetail): 0 the look before GR2.
The scatter (item 3): AGTGroundScatter (Source/GrandTour/Terrain/GTGroundScatter.h), placed by apply_strip at setup; M_GT_GroundScatter.
"""
import json
import math
import struct
import zlib
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
DEST = '/Game/GrandTour/ArtTests/GroundDetail'
MPC_PATH = '/Game/GrandTour/Terrain/MPC_TrackPaint'
MANIFEST = ROOT / 'Art/Export/GroundDetailGR2/manifest.json'
eal = u.EditorAssetLibrary
mel = u.MaterialEditingLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
TAG = 'GroundDetail:'
SWITCH = 'GroundDetail'
CF1, CF3 = u.CustomMaterialOutputType.CMOT_FLOAT1, u.CustomMaterialOutputType.CMOT_FLOAT3

# The scatter families' instances of M_GT_GroundScatter (vertex colour x the strip's palette; A2's render tints).
SCATTER_MI = {'Clods': 'MI_GD_Clod', 'Pebbles': 'MI_GD_Pebble', 'Twigs': 'MI_GD_Twig', 'Litter': 'MI_GD_Litter', 'TussockBases': 'MI_GD_TussockBase'}
SCATTER_LOOK = {   # SoilShare 1: the ground's own colour path (palette x ScrubSoil luminance); 0: the tint x the palette's local swing
    'Clods': dict(SoilShare=1.0, UseVertexColour=1.0, Rough=0.93, Tint=(1.2, 1.14, 1.06)),
    'TussockBases': dict(SoilShare=1.0, UseVertexColour=1.0, Rough=0.92, Tint=(0.86, 0.8, 0.7)),
    'Pebbles': dict(SoilShare=0.0, UseVertexColour=0.0, Rough=0.72, Tint=(0.16, 0.145, 0.12)),
    'Litter': dict(SoilShare=0.0, UseVertexColour=1.0, Rough=0.8, Tint=(0.32, 0.25, 0.13)),
    'Twigs': dict(SoilShare=0.0, UseVertexColour=0.0, Rough=0.85, Tint=(0.1, 0.08, 0.06)),
}
# The grass map: each instance's root footprint across, m, at scale 1 (the tussock style study's lobes +-0.13 m and roots 0.04-0.25 m
# out; the fine undergrass 0.01-0.16 m).
TUSSOCK_ROOT_M = 0.55
FINE_ROOT_M = 0.40
GRASS_CELL_CM = 50.0
GRASS_BLUR_CM = 100.0
GRASS_COVER = (0.2, 0.5)

SCALARS = dict(GDTileCm=200.0, GDTileBCm=270.0, GDRotBDeg=37.0, GDMaskM=7.0, GDTintM=13.0, GDHueShare=0.3, GDMeanLum0=0.101, GDMeanLum1=0.0622,
               GDUnderGrassTone=1.0, GDNormalStrength=1.0, GDPomDepthCm=1.5, GDPomNearM=15.0, GDPomFarM=25.0, GDPomMinSteps=8.0,
               GDPomMaxSteps=16.0, GDPomRefine=3.0, GDPomShadowM=4.0, GDPomShadowStrength=0.5, GDFadeNearM=25.0, GDFadeFarM=40.0)
VECTORS = dict(GDOffsetB=(0.37, 0.61, 0.0), GDMaskEdges=(0.45, 0.55, 0.0), GDTintEdges=(0.38, 0.62, 0.0),
               GDTintDamp=(0.82 / 0.97, 0.80 / 0.935, 0.82 / 0.89), GDTintDry=(1.12 / 0.97, 1.07 / 0.935, 0.96 / 0.89), GDGrassOrigin=(0.0, 0.0, 0.0), GDGrassScale=(0.0, 0.0, 0.0))

GD_HLSL = r'''// Ground relief GR2 phase B (Art/Unreal/ground_detail.py): the strips' soil detail over the row's own colour, roughness and normal.
struct GTGDNoise
{
    float Pad;
    float Hash(float2 c) { float3 p3 = frac(float3(c.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return frac((p3.x + p3.y) * p3.z); }
    float2 Grad(float2 c) { float a = 6.2831853 * Hash(c); return float2(cos(a), sin(a)); }
    float Perlin(float2 p)
    {
        float2 i = floor(p); float2 f = p - i;
        float2 w = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
        float a = dot(Grad(i), f);
        float b = dot(Grad(i + float2(1.0, 0.0)), f - float2(1.0, 0.0));
        float c = dot(Grad(i + float2(0.0, 1.0)), f - float2(0.0, 1.0));
        float d = dot(Grad(i + float2(1.0, 1.0)), f - float2(1.0, 1.0));
        return lerp(lerp(a, b, w.x), lerp(c, d, w.x), w.y);
    }
    float Fbm(float2 p, int octaves)
    {
        float sum = 0.0; float amp = 1.0; float norm = 0.0;
        [unroll] for (int k = 0; k < 4; ++k)
        {
            if (k >= octaves) break;
            sum += amp * Perlin(p); norm += amp; amp *= 0.5; p = p * 2.0 + float2(5.31, 1.73);
        }
        return 0.5 + 0.5 * sum / norm;
    }
};
struct GTGDPom
{
    float2 UA; float2 UB; float2 DxA; float2 DyA; float2 DxB; float2 DyB; float2x2 R; float S; float Tile; float M; float G;
    float H(Texture2DArray O, SamplerState Sm, float3 o, float g)
    {
        float2 oa = float2(o.x, -o.y) / Tile;
        float2 ob = mul(R, oa * S);
        float h0 = 0.0; float h1 = 0.0;
        [branch] if (G < 0.999)
        {
            float a = M < 0.999 ? O.SampleGrad(Sm, float3(UA + oa, 0.0), DxA * g, DyA * g).b : 0.0;
            float b = M > 0.001 ? O.SampleGrad(Sm, float3(UB + ob, 0.0), DxB * g, DyB * g).b : 0.0;
            h0 = lerp(a, b, M);
        }
        [branch] if (G > 0.001)
        {
            float a = M < 0.999 ? O.SampleGrad(Sm, float3(UA + oa, 1.0), DxA * g, DyA * g).b : 0.0;
            float b = M > 0.001 ? O.SampleGrad(Sm, float3(UB + ob, 1.0), DxB * g, DyB * g).b : 0.0;
            h1 = lerp(a, b, M);
        }
        return lerp(h0, h1, G);
    }
};
float3 gdN0 = normalize(N);
GDRough = float3(Rough.x, Rough.x, Rough.x);
GDRough1 = Rough.x;
GDNormal = gdN0;
GDAO = AOIn;
float2 gdXY = WorldPos.xy;
float2 gdUA = float2(gdXY.x, -gdXY.y) / max(GDTileCm, 1.0);
float2 gdDxA = ddx(gdUA);
float2 gdDyA = ddy(gdUA);
float gdDist = length(WorldPos - CamPos);
float gdW = saturate(ScrubW) * (1.0 - saturate(ApronBlend)) * (GroundDetail > 0.5 ? 1.0 : 0.0)
          * (1.0 - smoothstep(GDFadeNearM * 100.0, max(GDFadeFarM, GDFadeNearM + 0.01) * 100.0, gdDist));
[branch] if (gdW <= 0.001) { return Base; }
GTGDNoise gdNz;
gdNz.Pad = 0.0;
float gdS = GDTileCm / max(GDTileBCm, 1.0);
float gdC = cos(radians(GDRotBDeg));
float gdSn = sin(radians(GDRotBDeg));
float2x2 gdR = float2x2(gdC, -gdSn, gdSn, gdC);
float2 gdUB = mul(gdR, gdUA * gdS) + GDOffsetB.xy;
float2 gdDxB = mul(gdR, gdDxA * gdS);
float2 gdDyB = mul(gdR, gdDyA * gdS);
// The anti-tile mask (7 m) and the macro tint (13 m), gradient-noise fBm about 0.5.
float gdM = smoothstep(GDMaskEdges.x, GDMaskEdges.y, gdNz.Fbm(gdXY / (GDMaskM * 100.0) + float2(13.7, 71.3), 3));
float gdT = saturate((gdNz.Fbm(gdXY / (GDTintM * 100.0) + float2(41.1, 7.9), 4) - GDTintEdges.x) / max(GDTintEdges.y - GDTintEdges.x, 0.001));
// The grass ground (slice 1) from the strip's grass map.
float2 gdGuv = (gdXY - GDGrassOrigin.xy) * GDGrassScale.xy;
float gdG = all(gdGuv > 0.0) && all(gdGuv < 1.0) ? saturate(GrassMap.SampleLevel(GrassMapSampler, gdGuv, 0.0).r) : 0.0;
// Parallax (the gravel's POM), full to GDPomNearM, gone by GDPomFarM.
float3 pomOff = float3(0.0, 0.0, 0.0);
float pomShade = 0.0;
float3 gdNv = normalize(VN);
float pmFade = 1.0 - smoothstep(GDPomNearM * 100.0, max(GDPomFarM, GDPomNearM + 0.01) * 100.0, gdDist);
[branch] if (pmFade > 0.001 && GDPomDepthCm > 0.0)
{
    GTGDPom Pm;
    Pm.UA = gdUA; Pm.UB = gdUB; Pm.DxA = gdDxA; Pm.DyA = gdDyA; Pm.DxB = gdDxB; Pm.DyB = gdDyB; Pm.R = gdR; Pm.S = gdS;
    Pm.Tile = max(GDTileCm, 1.0); Pm.M = gdM; Pm.G = gdG;
    float3 pmV = normalize(WorldPos - CamPos);
    float pmVn = min(dot(pmV, gdNv), -0.2);
    float3 pmVt = pmV - gdNv * dot(pmV, gdNv);
    float pmDepth = GDPomDepthCm * pmFade;
    float pmSurf = 1.0 - Pm.H(GO, GOSampler, float3(0.0, 0.0, 0.0), 2.0);
    float3 pmSlide = pmVt / (-pmVn) * pmDepth;
    float pmT = saturate((-pmVn - 0.2) / 0.8);
    float pmSteps = lerp(lerp(GDPomMaxSteps, GDPomMinSteps, pmT), GDPomMinSteps, 1.0 - pmFade);
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
    int pmR = (int)clamp(GDPomRefine, 0.0, 6.0);
    [loop] for (int pmB = 0; pmB < 6; ++pmB)
    {
        if (pmB >= pmR) break;
        float pmMid = 0.5 * (pmLo + pmHi);
        float pmFMid = (1.0 - Pm.H(GO, GOSampler, pmSlide * pmMid, 1.0)) - pmMid;
        if (pmFMid > 0.0) { pmLo = pmMid; pmFLo = pmFMid; } else { pmHi = pmMid; pmFHi = pmFMid; }
    }
    float pmHit = lerp(pmLo, pmHi, saturate(pmFLo / max(pmFLo - pmFHi, 1e-5)));
    pomOff = pmSlide * pmHit;
    float pmSh = 1.0 - smoothstep(0.75 * GDPomShadowM * 100.0, max(GDPomShadowM, 0.01) * 100.0, gdDist);
    float3 pmL = normalize(SunDir);
    float pmLn = dot(pmL, gdNv);
    [branch] if (pmSh > 0.001 && pmLn > 0.05 && pmHit > 0.02)
    {
        float3 pmLs = (pmL - gdNv * pmLn) / pmLn * pmDepth;
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
// The detail at the slid uv: up to four samples (A/B by the mask, slice 0/1 by the grass), each skipped at no weight.
float2 gdOA = float2(pomOff.x, -pomOff.y) / max(GDTileCm, 1.0);
float2 gdOB = mul(gdR, gdOA * gdS);
float3 gdCol = float3(0.0, 0.0, 0.0);
float2 gdP = float2(0.0, 0.0);
float3 gdOrh = float3(0.0, 0.0, 0.0);
[unroll] for (int gdK = 0; gdK < 4; ++gdK)
{
    float gdSl = (float)(gdK / 2);
    bool gdIsB = (gdK % 2) == 1;
    float gdWk = (gdIsB ? gdM : 1.0 - gdM) * (gdK / 2 == 1 ? gdG : 1.0 - gdG);
    [branch] if (gdWk > 0.001)
    {
        float3 gdUv = float3(gdIsB ? gdUB + gdOB : gdUA + gdOA, gdSl);
        float2 gdDx = gdIsB ? gdDxB : gdDxA;
        float2 gdDy = gdIsB ? gdDyB : gdDyA;
        gdCol += gdWk * GC.SampleGrad(GCSampler, gdUv, gdDx, gdDy).rgb;
        gdOrh += gdWk * GO.SampleGrad(GOSampler, gdUv, gdDx, gdDy).rgb;
        float2 gdNd = UnpackNormalMap(GN.SampleGrad(GNSampler, gdUv, gdDx, gdDy)).xy;
        // In the tile's own uv, then world: A's (x, -y) as the gravel's; B's turned back by its rotation and scaled by its tile.
        float2 gdNa = gdIsB ? gdS * mul(gdNd, gdR) : gdNd;
        gdP += gdWk * float2(gdNa.x, -gdNa.y);
    }
}
// The palette kept: the layer x the detail's luminance over the slice's mean; the bake's own hue at GDHueShare; the macro tint.
float3 gdLw = float3(0.2126, 0.7152, 0.0722);
float gdMean = max(lerp(GDMeanLum0, GDMeanLum1, gdG), 1e-4);
float gdLumD = dot(gdCol, gdLw);
float gdLumL = dot(Base, gdLw);
float3 gdOut = lerp(Base * (gdLumD / gdMean), gdCol * (gdLumL / gdMean), saturate(GDHueShare));
gdOut *= lerp(GDTintDamp, GDTintDry, gdT) * lerp(1.0, GDUnderGrassTone, gdG);
gdOut *= 1.0 - saturate(GDPomShadowStrength) * pomShade;
float gdRough = lerp(Rough.x, gdOrh.g, gdW);
GDRough = float3(gdRough, gdRough, gdRough);
GDRough1 = gdRough;
GDNormal = normalize(lerp(gdN0, normalize(gdN0 + float3(gdP, 0.0) * GDNormalStrength), gdW));
GDAO = lerp(AOIn, gdOrh.r, gdW);
return lerp(Base, gdOut, gdW);
'''

VERGE_HLSL = '''// GR2: the gravel strip's grass verge (gravel_dg1_material.FINISH's gGrass): the soil detail's ground.
return smoothstep(375.0, 590.0, abs(WorldPos.y));
'''


def props(obj, **kw):
    for k, v in kw.items():
        obj.set_editor_property(k, v)
    return obj


def family_of(name):
    for fam, key in (('Clods', 'Clod'), ('Pebbles', 'Pebble'), ('Twigs', 'Twig'), ('Litter', 'Litter'), ('TussockBases', 'TussockBase')):
        if name.startswith('SM_GD_' + key):
            return fam
    raise ValueError(name)


def ensure_mpc():
    mpc = eal.load_asset(MPC_PATH)
    assert mpc, 'no ' + MPC_PATH
    scalars = list(mpc.get_editor_property('scalar_parameters'))
    have = [str(s.get_editor_property('parameter_name')) for s in scalars]
    added = []
    if SWITCH not in have:
        scalars.append(props(u.CollectionScalarParameter(), parameter_name=SWITCH, default_value=1.0))
        mpc.set_editor_property('scalar_parameters', scalars)
        eal.save_loaded_asset(mpc)
        added.append(SWITCH)
    return dict(mpc=MPC_PATH, added=added, scalars=len(scalars))


# ---------------------------------------------------------------- the scatter material
SCATTER_HLSL = r'''// Ground relief GR2 phase B (Art/Unreal/ground_detail.py): the ground scatter in the strip's own palette.
// The strips' scrub palette at this spot (live_mud_style.GROUND_HLSL's n), its mean, and its local swing.
float n = 0.5 + 0.5 * sin(WorldPos.x * 0.006) * sin(WorldPos.y * 0.007);
float3 pal = lerp(float3(0.095, 0.08, 0.052), float3(0.19, 0.145, 0.083), n);
float3 palMean = float3(0.1425, 0.1125, 0.0675);
float3 wn = normalize(VertexNormal);
// The ScrubSoil bake world-aligned (box, 2 m): its colour's luminance and its normal as a 1.5 cm bump.
float3 bw = pow(abs(wn), 4.0); bw /= max(dot(bw, float3(1.0, 1.0, 1.0)), 1e-4);
float2 uvZ = float2(WorldPos.x, -WorldPos.y) / 200.0;
float2 uvY = float2(WorldPos.x, -WorldPos.z) / 200.0;
float2 uvX = float2(WorldPos.y, -WorldPos.z) / 200.0;
float3 soil = float3(0.0, 0.0, 0.0);
float3 bump = float3(0.0, 0.0, 0.0);
[branch] if (bw.z > 0.01)
{
    soil += bw.z * GC.SampleGrad(GCSampler, float3(uvZ, 0.0), ddx(uvZ), ddy(uvZ)).rgb;
    float2 d = UnpackNormalMap(GN.SampleGrad(GNSampler, float3(uvZ, 0.0), ddx(uvZ), ddy(uvZ))).xy;
    bump += bw.z * float3(d.x, -d.y, 0.0) * sign(wn.z);
}
[branch] if (bw.y > 0.01)
{
    soil += bw.y * GC.SampleGrad(GCSampler, float3(uvY, 0.0), ddx(uvY), ddy(uvY)).rgb;
    float2 d = UnpackNormalMap(GN.SampleGrad(GNSampler, float3(uvY, 0.0), ddx(uvY), ddy(uvY))).xy;
    bump += bw.y * float3(d.x, 0.0, -d.y) * sign(wn.y);
}
[branch] if (bw.x > 0.01)
{
    soil += bw.x * GC.SampleGrad(GCSampler, float3(uvX, 0.0), ddx(uvX), ddy(uvX)).rgb;
    float2 d = UnpackNormalMap(GN.SampleGrad(GNSampler, float3(uvX, 0.0), ddx(uvX), ddy(uvX))).xy;
    bump += bw.x * float3(0.0, d.x, -d.y) * sign(wn.x);
}
float lum = dot(soil, float3(0.2126, 0.7152, 0.0722)) / 0.101;   // (SampleGrad, not Sample: the ray-tracing hit shaders refuse implicit derivatives)
float3 soilCol = pal * lum * Tint.rgb;
float3 ownCol = Tint.rgb * (pal / palMean);
float3 c = lerp(ownCol, soilCol, saturate(SoilShare)) * lerp(float3(1.0, 1.0, 1.0), VertexColour.rgb, saturate(UseVertexColour));
c *= 1.0 + 0.12 * (Rnd - 0.5);
float w = saturate(Wetness);
OutRough = lerp(Rough, 0.45, w);
OutNormal = normalize(wn + bump * BumpStrength);
float ign = frac(52.9829189 * frac(dot(Pixel.xy, float2(0.06711056, 0.00583715))));
Opacity = saturate(Fade) > ign ? 1.0 : 0.0;   // PerInstanceFadeAmount: 1 shown, 0 culled (the HISM's cull distances)
return c * lerp(1.0, 0.75, w);
'''


def build_scatter_material():
    """M_GT_GroundScatter (masked for the dithered cull fade, world-space normal, instanced) and its five family instances."""
    path = DEST + '/M_GT_GroundScatter'
    m = eal.load_asset(path) or assets.create_asset('M_GT_GroundScatter', DEST, u.Material, u.MaterialFactoryNew())
    for e in list(mel.get_material_expressions(m)):
        mel.delete_material_expression(m, e)
    props(m, blend_mode=u.BlendMode.BLEND_MASKED, dithered_lod_transition=True, used_with_instanced_static_meshes=True, tangent_space_normal=False)
    y = [0]

    def expr(cls, **kw):
        y[0] += 120
        return props(mel.create_material_expression(m, cls, -900, y[0]), **kw)
    c = expr(u.MaterialExpressionCustom, code=SCATTER_HLSL, output_type=CF3, description='Ground scatter (GR2)')
    names = ['WorldPos', 'VertexNormal', 'VertexColour', 'Rnd', 'Fade', 'Pixel', 'Wetness', 'GC', 'GN', 'Tint', 'SoilShare', 'UseVertexColour', 'Rough', 'BumpStrength']
    c.set_editor_property('inputs', [props(u.CustomInput(), input_name=k) for k in names])
    c.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name=k, output_type=t) for k, t in
                                                 [('OutRough', CF1), ('OutNormal', CF3), ('Opacity', CF1)]])
    def wire(a, pin, out=''):
        assert mel.connect_material_expressions(a, out, c, pin), pin
    wire(expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS), 'WorldPos')
    wire(expr(u.MaterialExpressionVertexNormalWS), 'VertexNormal')
    wire(expr(u.MaterialExpressionVertexColor), 'VertexColour')
    wire(expr(u.MaterialExpressionPerInstanceRandom), 'Rnd')
    wire(expr(u.MaterialExpressionPerInstanceFadeAmount), 'Fade')
    wire(expr(u.MaterialExpressionScreenPosition), 'Pixel', 'PixelPosition')
    wire(expr(u.MaterialExpressionCollectionParameter, collection=eal.load_asset('/Game/GrandTour/Materials/MPC_Weather'), parameter_name='Wetness'), 'Wetness')
    for pin, asset, sampler in [('GC', 'TA_GD_Color', 'SAMPLERTYPE_COLOR'), ('GN', 'TA_GD_Normal', 'SAMPLERTYPE_NORMAL')]:
        wire(expr(u.MaterialExpressionTextureObject, texture=eal.load_asset(DEST + '/' + asset), sampler_type=getattr(u.MaterialSamplerType, sampler)), pin)
    wire(expr(u.MaterialExpressionVectorParameter, parameter_name='Tint', default_value=u.LinearColor(1.0, 1.0, 1.0, 1.0)), 'Tint')
    for name, value in [('SoilShare', 1.0), ('UseVertexColour', 1.0), ('Rough', 0.9), ('BumpStrength', 1.0)]:
        wire(expr(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value), name)
    for out, prop in [('', u.MaterialProperty.MP_BASE_COLOR), ('OutRough', u.MaterialProperty.MP_ROUGHNESS), ('OutNormal', u.MaterialProperty.MP_NORMAL),
                      ('Opacity', u.MaterialProperty.MP_OPACITY_MASK)]:
        assert mel.connect_material_property(c, out, prop), str(prop)
    errors = mel.recompile_material(m)
    assert not errors, str(errors)
    eal.save_loaded_asset(m)
    made = {}
    for fam, mi_name in SCATTER_MI.items():
        mi = eal.load_asset(DEST + '/' + mi_name) or assets.create_asset(mi_name, DEST, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, m)
        look = SCATTER_LOOK[fam]
        for k in ('SoilShare', 'UseVertexColour', 'Rough'):
            mel.set_material_instance_scalar_parameter_value(mi, k, look[k])
        mel.set_material_instance_vector_parameter_value(mi, 'Tint', u.LinearColor(*look['Tint'], 1.0))
        if fam == 'Litter':   # flat mats of bent blades: both faces
            over = mi.get_editor_property('base_property_overrides')
            over.set_editor_property('override_two_sided', True)
            over.set_editor_property('two_sided', True)
            mi.set_editor_property('base_property_overrides', over)
        mel.update_material_instance(mi)
        eal.save_loaded_asset(mi)
        made[fam] = dict(mi=mi_name, **{k: v for k, v in look.items()})
    return dict(material=path, instances=made, colour='vertex colour x the strip palette (soil families: x ScrubSoil luminance, box 2 m)',
                bump='TA_GD_Normal slice 0 box-projected at 2 m (the 1.5 cm bake)', fade='PerInstanceFadeAmount, dithered, masked', wet='x0.75, rough to 0.45')


# ---------------------------------------------------------------- the landscape
def _custom_slots(node, names):
    node.set_editor_property('inputs', [props(u.CustomInput(), input_name=k) for k in names])


def apply_landscape(path, kind, grass_tex=None, bounds=(0.0, 0.0, 0.0, 0.0)):
    """The GroundDetail switch and nodes on a strip's landscape copy (kind 'live': M_VariantsLandscape / M_LiveLandscape's Scrub row;
    'gravel': M_GravelLandscape's outputs). Repeatable: the old GroundDetail: nodes go and the original wiring comes back first.
    The strip's grass map and its bounds are the parameters' defaults here (each strip has its own copy; the MI only flips the switch)."""
    m = eal.load_asset(path)
    assert m, 'no ' + path
    exprs = list(mel.get_material_expressions(m))
    for e in exprs:
        try:
            if str(e.get_editor_property('desc')).startswith(TAG):
                mel.delete_material_expression(m, e)
        except Exception:
            pass
    exprs = list(mel.get_material_expressions(m))

    def find(cls, pred):
        hits = [e for e in exprs if isinstance(e, cls) and pred(e)]
        assert len(hits) == 1, '%s: %d %s' % (path, len(hits), cls.__name__)
        return hits[0]
    desc = lambda e: str(e.get_editor_property('desc'))
    row = [0]

    def expr(cls, **kw):
        row[0] += 110
        return props(mel.create_material_expression(m, cls, -2600, 2400 + row[0]), desc=TAG + str(row[0]), **kw)

    def con(a, out, b, pin):
        assert mel.connect_material_expressions(a, out, b, pin), '%s %s -> %s' % (path, out, pin)
    gd = expr(u.MaterialExpressionCustom, code=GD_HLSL, output_type=CF3, description='Ground detail (GR2)')
    names = ['Base', 'Rough', 'N', 'AOIn', 'ScrubW', 'ApronBlend', 'WorldPos', 'VN', 'CamPos', 'SunDir', 'GroundDetail', 'GC', 'GN', 'GO', 'GrassMap'] \
        + list(SCALARS) + list(VECTORS)
    _custom_slots(gd, names)
    gd.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name=k, output_type=t) for k, t in
                                                  [('GDRough', CF3), ('GDRough1', CF1), ('GDNormal', CF3), ('GDAO', CF1)]])
    con(expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS), '', gd, 'WorldPos')
    con(expr(u.MaterialExpressionVertexNormalWS), '', gd, 'VN')
    con(expr(u.MaterialExpressionCameraPositionWS), '', gd, 'CamPos')
    con(expr(u.MaterialExpressionSkyAtmosphereLightDirection, light_index=0), '', gd, 'SunDir')
    con(expr(u.MaterialExpressionCollectionParameter, collection=eal.load_asset(MPC_PATH), parameter_name=SWITCH), '', gd, 'GroundDetail')
    for pin, asset, sampler in [('GC', 'TA_GD_Color', 'SAMPLERTYPE_COLOR'), ('GN', 'TA_GD_Normal', 'SAMPLERTYPE_NORMAL'), ('GO', 'TA_GD_ORH', 'SAMPLERTYPE_LINEAR_COLOR')]:
        tex = eal.load_asset(DEST + '/' + asset)
        assert tex, 'no %s/%s (run Art/ground_detail_gr2.ps1 -Step import)' % (DEST, asset)
        con(expr(u.MaterialExpressionTextureObject, texture=tex, sampler_type=getattr(u.MaterialSamplerType, sampler)), '', gd, pin)
    con(expr(u.MaterialExpressionTextureObjectParameter, parameter_name='GDGrassMap', texture=grass_tex or eal.load_asset('/Engine/EngineResources/Black'),
             sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE if grass_tex else u.MaterialSamplerType.SAMPLERTYPE_COLOR), '', gd, 'GrassMap')
    defaults = dict(VECTORS, GDGrassOrigin=(bounds[0], bounds[1], 0.0), GDGrassScale=(bounds[2], bounds[3], 0.0))
    for name, value in SCALARS.items():
        con(expr(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value), '', gd, name)
    for name, value in defaults.items():
        v = list(value) + [0.0] * (4 - len(value))
        con(expr(u.MaterialExpressionVectorParameter, parameter_name=name, default_value=u.LinearColor(*v)), '', gd, name)

    def switch(on_src, on_out, off_src, off_out):
        s = expr(u.MaterialExpressionStaticSwitchParameter, parameter_name=SWITCH, default_value=False)
        con(on_src, on_out, s, 'True')
        con(off_src, off_out, s, 'False')
        return s
    if kind == 'live':
        ground = find(u.MaterialExpressionCustom, lambda e: desc(e) == 'Landscape:groundtex')
        vnormal = find(u.MaterialExpressionVertexNormalWS, lambda e: desc(e) == 'Landscape:vertexnormal')
        blends = {n: find(u.MaterialExpressionLandscapeLayerBlend, lambda e, n=n: desc(e) == 'Landscape:' + n) for n in ('colour', 'roughness', 'normal')}
        con(ground, '', gd, 'Base')
        con(ground, 'GrassRoughOut', gd, 'Rough')
        con(vnormal, '', gd, 'N')
        con(ground, 'ClayBlend', gd, 'ApronBlend')
        one = expr(u.MaterialExpressionConstant, r=1.0)
        con(one, '', gd, 'AOIn')
        con(one, '', gd, 'ScrubW')
        for blend, (on_out, off_src, off_out) in [('colour', ('', ground, '')), ('roughness', ('GDRough', ground, 'GrassRoughOut')),
                                                  ('normal', ('GDNormal', vnormal, ''))]:
            node = blends[blend]
            pins = [str(p) for p in mel.get_material_expression_input_names(node)]
            pin = next(p for p in pins if p.lower().split()[-1:] == ['scrub'])
            con(switch(gd, on_out, off_src, off_out), '', node, pin)
        where = 'the Scrub row of the colour, roughness and normal layer blends (apron excluded by groundtex ClayBlend)'
    else:
        surf = find(u.MaterialExpressionCustom, lambda e: desc(e).startswith('Gravel:') and
                    [str(o.get_editor_property('output_name')) for o in e.get_editor_property('additional_outputs')] == ['Normal', 'Rough', 'AO'])
        layer = find(u.MaterialExpressionLandscapeLayerBlend, lambda e: desc(e).startswith('Gravel:'))
        verge = expr(u.MaterialExpressionCustom, code=VERGE_HLSL, output_type=CF1, description='GR2 verge')
        _custom_slots(verge, ['WorldPos'])
        con(expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS), '', verge, 'WorldPos')
        con(layer, '', gd, 'Base')
        con(surf, 'Rough', gd, 'Rough')
        con(surf, 'Normal', gd, 'N')
        con(surf, 'AO', gd, 'AOIn')
        con(verge, '', gd, 'ScrubW')
        con(expr(u.MaterialExpressionConstant, r=0.0), '', gd, 'ApronBlend')
        for prop, on_out, off_src, off_out in [(u.MaterialProperty.MP_BASE_COLOR, '', layer, ''), (u.MaterialProperty.MP_NORMAL, 'GDNormal', surf, 'Normal'),
                                               (u.MaterialProperty.MP_ROUGHNESS, 'GDRough1', surf, 'Rough'), (u.MaterialProperty.MP_AMBIENT_OCCLUSION, 'GDAO', surf, 'AO')]:
            assert mel.connect_material_property(switch(gd, on_out, off_src, off_out), '', prop), str(prop)
        where = "the gravel surface's grass verge (3.75-5.9 m off the line), on the base colour, normal, roughness and AO outputs"
    errors = mel.recompile_material(m)
    assert not errors, '%s: %s' % (path, errors)
    eal.save_loaded_asset(m)
    return dict(material=path, kind=kind, where=where, switch=SWITCH + ' (static, off in the parent)')


def strip_landscape(path):
    """The GroundDetail: nodes off a strip's landscape copy (its outputs or Scrub pins left unwired): L_GravelDeform's setup calls it
    first, as the gravel builders delete and remake the 'Gravel:' nodes the switches read and recompile in between."""
    m = eal.load_asset(path)
    if m is None:
        return 0
    gone = 0
    for e in list(mel.get_material_expressions(m)):
        try:
            if str(e.get_editor_property('desc')).startswith(TAG):
                mel.delete_material_expression(m, e)
                gone += 1
        except Exception:
            pass
    return gone


def make_mi(folder, parent_path):
    path = folder + '/MI_GT_Landscape_Strips'
    mi = eal.load_asset(path) or assets.create_asset('MI_GT_Landscape_Strips', folder, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, eal.load_asset(parent_path))
    mel.update_material_instance(mi)
    mel.set_material_instance_static_switch_parameter_value(mi, SWITCH, True)
    mel.update_material_instance(mi)
    assert mel.get_material_instance_static_switch_parameter_value(mi, SWITCH), 'the GroundDetail static switch did not take on ' + path
    # The switch-on path compiles here (the parent's recompile only builds the off path): its static counts must come back.
    st = mel.get_statistics(mi)
    assert st.num_pixel_shader_instructions > 0, 'MI_GT_Landscape_Strips (GroundDetail on) did not compile: ' + path
    eal.save_loaded_asset(mi)
    return mi


# ---------------------------------------------------------------- the grass map
def _png_gray(path, rows):
    h, w = len(rows), len(rows[0])
    raw = b''.join(b'\x00' + bytes(r) for r in rows)

    def chunk(k, payload):
        return struct.pack('>I', len(payload)) + k + payload + struct.pack('>I', zlib.crc32(k + payload) & 0xFFFFFFFF)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def _box_blur(grid, w, h, r):
    out = [[0.0] * w for _ in range(h)]
    for y in range(h):
        row, acc, n = grid[y], 0.0, 0
        pre = [0.0]
        for v in row:
            pre.append(pre[-1] + v)
        for x in range(w):
            a, b = max(0, x - r), min(w, x + r + 1)
            out[y][x] = (pre[b] - pre[a]) / (b - a)
    res = [[0.0] * w for _ in range(h)]
    for x in range(w):
        pre = [0.0]
        for y in range(h):
            pre.append(pre[-1] + out[y][x])
        for y in range(h):
            a, b = max(0, y - r), min(h, y + r + 1)
            res[y][x] = (pre[b] - pre[a]) / (b - a)
    return res


def grass_map(tag, spec, grass):
    """T_GD_Grass_<tag>: where the grass is dense (slice 1). grass: [(x_cm, y_cm, root_footprint_cm)]. Returns (texture, bounds, facts)."""
    side = (spec.components_per_side * spec.subsections_per_component * spec.quads_per_subsection) * spec.quad_size_cm
    x0, y0 = spec.origin_x_cm, spec.origin_y_cm
    n = int(math.ceil(side / GRASS_CELL_CM))
    cover = [[0.0] * n for _ in range(n)]
    for x, y, foot in grass:
        cx, cy = int((x - x0) // GRASS_CELL_CM), int((y - y0) // GRASS_CELL_CM)
        if 0 <= cx < n and 0 <= cy < n:
            cover[cy][cx] += math.pi * (0.5 * foot) ** 2 / (GRASS_CELL_CM * GRASS_CELL_CM)
    r = max(1, int(round(GRASS_BLUR_CM / GRASS_CELL_CM)))
    cover = _box_blur(_box_blur(cover, n, n, r), n, n, r)
    lo, hi = GRASS_COVER
    rows, dense = [], 0
    for y in range(n):
        row = []
        for x in range(n):
            t = min(1.0, max(0.0, (cover[y][x] - lo) / (hi - lo)))
            g = t * t * (3 - 2 * t)
            dense += g > 0.5
            row.append(int(round(255 * g)))
        rows.append(row)
    png = ROOT / ('Art/Export/GroundDetailGR2/T_GD_Grass_%s.png' % tag)
    _png_gray(png, rows)
    task = u.AssetImportTask()
    props(task, filename=str(png), destination_path=DEST, destination_name='T_GD_Grass_' + tag, automated=True, replace_existing=True, save=False)
    assets.import_asset_tasks([task])
    tex = eal.load_asset(DEST + '/T_GD_Grass_' + tag)
    assert tex, 'no grass map'
    props(tex, srgb=False, compression_settings=u.TextureCompressionSettings.TC_GRAYSCALE, lod_group=u.TextureGroup.TEXTUREGROUP_WORLD,
          address_x=u.TextureAddress.TA_CLAMP, address_y=u.TextureAddress.TA_CLAMP)
    eal.save_loaded_asset(tex)
    bounds = (x0, y0, 1.0 / (n * GRASS_CELL_CM), 1.0 / (n * GRASS_CELL_CM))
    return tex, bounds, dict(texture=tex.get_path_name(), png=str(png.relative_to(ROOT)).replace('\\', '/'), cells=n, cell_cm=GRASS_CELL_CM,
                             instances=len(grass), dense_share=round(dense / float(n * n), 4), blur_cm=GRASS_BLUR_CM, cover_smoothstep=list(GRASS_COVER))


# ---------------------------------------------------------------- the scatter
def scatter_meshes():
    rows = json.loads(MANIFEST.read_text())['scatter']
    out = []
    for row in rows:
        mesh = eal.load_asset(DEST + '/' + row['name'])
        assert mesh, 'no %s/%s (run Art/ground_detail_gr2.ps1 -Step import)' % (DEST, row['name'])
        size = row.get('across_cm', row.get('size_cm'))
        out.append(props(u.GTGroundScatterMesh(), mesh=mesh, family=family_of(row['name']), size_cm=float(size),
                         sink_share=0.0 if 'z_range_m' in row else 0.3))
    return out


def apply_strip(tag, folder, material_path, kind, spec_asset, grass, tussocks, feet):
    """The strip's whole GR2: the switch on its landscape copy, its grass map and MI_GT_Landscape_Strips on the landscape, and the
    scatter actor. grass: [(x_cm, y_cm, root_cm)] every grass instance; tussocks: the tussock transforms (kinds 0-2), feet their
    root footprints (cm). Call with the strip level loaded, after its grass is placed; the caller saves the level."""
    act = u.get_editor_subsystem(u.EditorActorSubsystem)
    out = dict(ensure_mpc=ensure_mpc())
    tex, bounds, out['grass_map'] = grass_map(tag, spec_asset.spec, grass)
    out['landscape'] = apply_landscape(material_path, kind, tex, bounds)
    mi = make_mi(folder, material_path)
    landscapes = [a for a in act.get_all_level_actors() if isinstance(a, u.LandscapeProxy)]
    for land in landscapes:
        land.set_editor_property('landscape_material', mi)
    out['mi'] = dict(path=mi.get_path_name(), landscapes=len(landscapes), grass_bounds=list(bounds))
    for a in act.get_all_level_actors():
        if isinstance(a, u.GTGroundScatter):
            act.destroy_actor(a)
    scatter = act.spawn_actor_from_class(u.GTGroundScatter, u.Vector(0, 0, 0), u.Rotator())
    scatter.set_actor_label('GD_GroundScatter')
    result = json.loads(scatter.build(spec_asset, scatter_meshes(), tussocks, feet))
    assert result.get('ok'), result
    out['scatter'] = result
    out['switches'] = 'gt.Ground.Detail 0/1, gt.Ground.Scatter 0/1, gt.Ground.ScatterDensity 0-1'
    return out


def grass_rows(transforms, kind):
    """(x_cm, y_cm, root_cm) for a grass placement of the tussock style's kind (0-2 tussocks, 3 the fine undergrass)."""
    root = (TUSSOCK_ROOT_M if kind < 3 else FINE_ROOT_M) * 100.0
    rows = []
    for t in transforms:
        s = t.scale3d
        rows.append((t.translation.x, t.translation.y, root * math.sqrt(abs(s.x * s.y))))
    return rows
