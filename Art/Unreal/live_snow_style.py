"""Living mud LM3a + LM3b + LM3c (docs/LIVING_MUD_PLAN.md LM3a, LM3b, LM3c): the snow materials on the live field.

M_GT_Snow is a copy of the live M_GT_Mud graph (Art/Unreal/live_mud_style.py's): the same displacement (WPO) and the same
field sampling (setup_m6_mud.py's SURFACE_A: the bicubic height, its slope, the normal, the tracks), the same masked root
and the same hole logic. LM3b replaces LM3a's flat surface with the God of War look, all procedural (no texture files):
- fresh snow (tracks 0): albedo SnowFreshAlbedo 0.85, a little blue where the surface turns from the sun (SnowShadeTint),
  a soft normal from world-space value noise at 2, 12 and 60 cm (SnowNoiseCm, SnowNoiseSlope), roughness 0.7 swung by
  the 12 cm octave, and the glint: 1 cm hashed world cells whose facet lines up with the sun's half-vector dip in
  roughness (GlintRough) with the normal turned to the half-vector. The sun's direction is the Sky Atmosphere Light
  Direction node (light 0): the view uniform's AtmosphereLightDirection[0], which the renderer fills from the atmosphere
  sun light (the strip's DirectionalLight is one by default) even without a SkyAtmosphere component;
- packed snow (tracks 1): albedo SnowPackedAlbedo 0.72 x SnowPackedTint (greyer-blue), roughness 0.45, the grain at
  SnowPackedNoise of its strength, and stage F's tread lugs at LugTiltDeg 30 from the field's tread data (mud keeps 0);
  LM3c: the lugs only where a tyre's tread is set (the tread texture's A, the field's lug strength 0.25-1, 0 in the
  missing patches: broken lugs, LugTiltDeg the peak), and where the belly scraped (A -1, no tread) faint scrape streaks
  along its heading: stretched world value noise ScrapeWidthCm (3) across by ScrapeLengthCm (55) long, the normal tilted
  by up to ScrapeSlope across the heading and the albedo swung by ScrapeAlbedo, faded where a pixel spans a streak;
- walls, by the field's slope (SnowWallSlopeMin..Max, cm/cm): SnowWallAlbedo 0.64 x SnowWallTint, a shade darker
  blue-grey, roughness 0.55;
- the soft, slightly blue shade: the project runs Substrate (r.Substrate=True, r.Substrate.ProjectGBufferFormat=0, the
  blendable GBuffer), so the surface goes into a Substrate Slab with Sub-Surface Type Wrap and a blue-heavy SSS MFP
  (from SnowSubsurfaceColor: MFP = -0.01 / ln(colour) cm, the Slab's default 0.01 cm thickness, which Substrate
  rescales to its 100 cm simple volume before the transmittance it exports as the subsurface colour). In the blendable GBuffer a
  Slab's Diffusion type (MFP without a profile) exports as Default Lit (SubstrateGetLegacyShadingModels), so Wrap, which
  exports as the legacy Subsurface shading model, is the one that shades. The SSS fades out over the patch's 3 m taper
  (SnowEdgeCm), so at the box's border the patch matches the landscape apron, which has none.
The fresh-snow block (NOISE_HLSL, FRESH_HLSL, GLINT_HLSL) is shared with the strip landscape's apron
(setup_live_snow_drive.py), so the two surfaces give the same response at the patch's edge.

M_GT_Clod_Snow is M_GT_Clod's snow copy (LM3a housekeeping item 5; LM3c item 4): the same instanced-mesh usage and the
per-instance random tint (TintRange +-5 %), albedo 0.82, roughness 0.7, no darkening by freshness or wetness (the
freshness custom data is no longer read), and LM3c: the same Substrate Slab as M_GT_Snow (Sub-Surface Type Wrap, the SSS
MFP from M_GT_Snow's SnowSubsurfaceColor, phase anisotropy 0.3, F0 0.02), so its shaded side takes the snow's soft blue
light instead of reading as a dark stone. AGTMudPatch puts it on a snow patch's clod HISMs only; the meshes keep M_GT_Clod.

LM4 (docs/LIVING_MUD_PLAN.md LM4 item 5), God of War snow:
- a granular surface on fresh and packed snow (NOISE_HLSL, shared with the apron): cellular (Voronoi) clumps on the displaced
  surface's XY at SnowClumpCm 1.5 and 6 cm, each a low dome about its hashed feature point with a crisp crease at the border to
  the next (SnowClumpSlope at the border, none SnowClumpEdge of a cell in), the gaps between clumps darkened by
  SnowClumpGapDark (the fine scale half of it); PCG-hashed per lattice cell, so nothing repeats at 2 m; faded where a pixel
  spans a clump, gone on walls and crust plates, SnowPackedClump of it in packed snow;
- walls and crust plates (the field's slope; the plate mask in the tread texture's B on snow) get a compressed, faceted
  response: the grain at SnowWallNoise 0.3 (LM3b's 0.6: flatter), 3D Voronoi facets SnowFacetCm 4 cm each tipping the
  normal by SnowFacetTilt toward a hashed direction and swinging the albedo by SnowFacetAlbedo (isotropic cells: no
  vertical streaks), the plates' tops at SnowPlateAlbedo 0.76 (a shade darker than fresh, lighter than a wall);
- the shade toward a neutral grey-blue: SnowShadeSaturation (the dial the owner names; 0.5 = half LM3b's saturation, 1 =
  LM3b's) takes SnowShadeTint, SnowPackedTint, SnowWallTint and SnowSubsurfaceColor toward their own luminance (Rec. 709);
  M_GT_Clod_Snow's MFP is taken from the same desaturated colour.

LM4b (docs/LIVING_MUD_PLAN.md LM4b items 4-7; the owner's "the snow is a bit blocky"): the crumbly detail moves into the
surface, as God of War's does, over a soft field shape:
- the snow-clump detail height map T_GT_SnowDetail (Art/tools/bake_snow_detail.py, imported by Art/Unreal/import_snow_detail.py:
  R crumbs 1-4 cm, G clods 6-15 cm, B the two together; linear, BC7, tileable over SnowDetailTileCm), world-space tri-planar on
  the field's normal at two tilings that do not share a repeat (SnowDetailTileCm.x and .y, 100 and 113 cm, the 60 cm grain
  octave choosing between them), its height gradient bending the normal by SnowDetailCm.x (crumbs) and .y (clods) cm of
  height a unit, its crevices darkening the albedo (DETAIL_HLSL, shared with the apron);
- the edge mask E = the largest of the field's slope (SnowEdgeSlope.x..y, cm/cm), the tracks' boundary (4 t (1 - t)) and the
  lip band (raised SnowEdgeLipCm over the snow top next to tracked cells, or holding a lump: the tread texture's B); fresh
  snow (E 0) takes the crumbs at SnowDetailFresh and a little cavity (SnowCavityFresh); edges, walls, the lip and the berm
  (E 1) both layers at full strength and SnowCavityEdge; the packed floor the crumbs at SnowDetailPacked (and the tread as
  LM3c left it). LM4's cellular grain is gone (SnowCellGrain 0; 1 brings it back) and so are its wall facets and the plates'
  albedo (the plates are soft domes now);
- the parallax experiment (SnowParallax, AGTMudPatch's gt.Snow.Parallax): parallax occlusion over B where E is over 0.2 and a
  pixel spans under SnowParallaxNearCm, marched in a frame from the field's normal (its depth along the normal, its slide in
  the normal's tangent plane, the height map read in the normal's dominant projection), SnowParallaxSteps steps over
  SnowParallaxCm of depth, a linear refine; the hit's slide moves every detail lookup. Faded in over E 0.2-0.4.
- the shade dial SnowShadeSaturation stays at LM4's 0.5; SnowEdgeDebug 1 draws E (red) for a diagnostic picture.
LM4d (docs/LIVING_MUD_PLAN.md LM4d item 4): E is at least BellyDetail (0.35) where the belly scraped, and the scrape streaks are
stronger (ScrapeSlope 0.3, ScrapeAlbedo 0.06; LM3c's 0.15 and 0.03).
"""
import ast,math
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
MUD='/Game/GrandTour/Materials/M_GT_Mud'
SNOW='/Game/GrandTour/Materials/M_GT_Snow'
CLOD_SNOW='/Game/GrandTour/Materials/M_GT_Clod_Snow'
# The fresh-snow response, shared by M_GT_Snow and the strip landscape's apron (proposed numbers; the owner names them).
FRESH_SCALARS={'SnowFreshAlbedo':0.85,'SnowFreshRough':0.7,'SnowRoughVary':0.06,'SnowAlbedoVary':0.025,
    'GlintCellCm':1.0,'GlintSpread':0.8,'GlintAngleDeg':5.0,'GlintRough':0.12,'GlintDensity':0.5,
    'SnowShadeSaturation':0.5,'SnowClumpEdge':0.22,'SnowClumpGapDark':0.07,
    # LM4b: LM4's cellular grain off (1 brings it back); the detail map on fresh snow (the crumbs at SnowDetailFresh and a
    # little cavity), shared with the apron so the border matches.
    'SnowCellGrain':0.0,'SnowDetailFresh':0.35,'SnowCavityFresh':0.05}
FRESH_VECTORS={'SnowShadeTint':(0.90,0.96,1.06),'SnowNoiseCm':(2.0,12.0,60.0),'SnowNoiseSlope':(0.10,0.12,0.10),
    'SnowClumpCm':(1.5,6.0,0.0),'SnowClumpSlope':(0.18,0.25,0.0),
    # LM4b: the detail map's two tilings (cm), and each layer's height (cm) at a channel value of 1 (crumbs, clods).
    'SnowDetailTileCm':(100.0,113.0,0.0),'SnowDetailCm':(0.8,2.0,0.0)}
DETAIL_TEXTURE='/Game/GrandTour/Textures/Snow/T_GT_SnowDetail'   # LM4b item 4 (Art/Unreal/import_snow_detail.py)
APRON_DETAIL=True   # LM4b: the landscape's apron reads the detail map too (its fresh-snow crumbs), so the border matches
# M_GT_Snow only: packed, walls, the subsurface and the border fade.
SNOW_SCALARS={'SnowPackedAlbedo':0.72,'SnowPackedRough':0.45,'SnowPackedNoise':0.3,
    'SnowWallAlbedo':0.64,'SnowWallRough':0.55,'SnowWallNoise':0.3,'SnowWallSlopeMin':0.8,'SnowWallSlopeMax':2.0,
    'SnowPackedClump':0.6,
    'SnowSSS':1.0,'SnowEdgeCm':300.0,
    # LM4b items 5-6: the edge mask (the lip band's height over the snow top, cm), the detail's gains by it, the parallax
    # experiment (0 off by default until the pictures and the cost say otherwise), and the edge mask's diagnostic view.
    'SnowEdgeLipCm':2.0,'SnowDetailPacked':0.2,'SnowCavityPacked':0.04,'SnowCavityEdge':0.3,
    'SnowParallax':0.0,'SnowParallaxCm':2.5,'SnowParallaxSteps':10.0,'SnowParallaxNearCm':1.2,'SnowEdgeDebug':0.0,
    # LM4d item 4 (the owner's "the middle is still very perfectly flat"): the belly's channel takes the edge mask's floor BellyDetail
    # (the crumbs and clods there at mid strength), and stronger scrape streaks (LM3c's ScrapeSlope 0.15, ScrapeAlbedo 0.03).
    'ScrapeLengthCm':55.0,'ScrapeWidthCm':3.0,'ScrapeSlope':0.3,'ScrapeAlbedo':0.06,'BellyDetail':0.35,
    # LM4e cut 6 (docs/LIVING_MUD_PLAN.md LM4e; AGTMudPatch's gt.Snow.FastMaterial): 1 the scrape streaks' noise (four hashes and a
    # quintic per pixel) only where they show (the belly scraped there and a pixel spans under a streak), 0 everywhere as before.
    # LM4f item 2 (docs/LIVING_MUD_PLAN.md LM4f): 2, the default, LM4e's 1 and the cheaper detail, glint and subsurface (FAST_DETAIL_HLSL,
    # SNOW_HLSL): each changes pixels, so the owner A/B's 2 against 1 (LM4e's) and 0 (the full material).
    'SnowFastPath':2.0}
SNOW_VECTORS={'SnowPackedTint':(0.95,1.0,1.08),'SnowWallTint':(0.93,1.0,1.10),'SnowSubsurfaceColor':(0.55,0.70,0.90),
    'SnowEdgeSlope':(0.35,1.2,0.0)}   # LM4b: the edge mask's slope ramp, cm/cm (19-50 deg)
# Into the Slab directly (not through the surface node).
SLAB_SCALARS={'SnowSSSWrap':0.3,'SnowF0':0.02}
LUG_TILT_DEG=30.0   # stage F's tread lugs in the packed floors (M_GT_Mud keeps 0 since stage J2)
# LM4e cut 5 (docs/LIVING_MUD_PLAN.md LM4e): M_GT_Snow opaque. The copied mud root is masked, but its mask has been 1 on every
# pixel since mud stage D (SNOW_HLSL sets Mask 1.0 too), so opaque draws the same pixels while the depth prepass and every
# shadow cascade take the position-only path instead of running the masked pixel shader. MI_GT_Snow_Masked overrides the blend
# mode back to masked, for the profile's A/B (Art/Unreal/profile_live_snow.py, Masked).
SNOW_OPAQUE=True
SNOW_MASKED_MI='/Game/GrandTour/Materials/MI_GT_Snow_Masked'
def desaturate(c,sat):
    # LM4: SnowShadeSaturation's rule (the shader's): toward the colour's own Rec. 709 luminance.
    l=0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
    return tuple(l+(x-l)*sat for x in c)

# The caller defines SnowPos (world cm, the displaced surface), SnowBaseN (world normal) and SnowNoiseGain; NOISE_HLSL
# leaves snNrm, snVary (the albedo's swing, about 1) and snRoughSwing.
NOISE_HLSL='''// LM3b, the snow's grain: world-space value noise (quintic, analytic gradient; PCG3D integer hashes, so it does not
// band far from the origin) at three octaves, SnowNoiseCm x/y/z (2, 12, 60 cm), each bending the normal by its
// SnowNoiseSlope (a slope, unitless) times SnowNoiseGain. The 12 cm octave swings the roughness, the 60 cm one the albedo.
float3 snGrad = float3(0.0, 0.0, 0.0);
float snVal[3];
[unroll] for (int snO = 0; snO < 3; ++snO)
{
    float snScale = max(snO == 0 ? SnowNoiseCm.x : (snO == 1 ? SnowNoiseCm.y : SnowNoiseCm.z), 0.1);
    float snAmp = snO == 0 ? SnowNoiseSlope.x : (snO == 1 ? SnowNoiseSlope.y : SnowNoiseSlope.z);
    float3 snX = SnowPos / snScale + float3(17.31, 5.17, 3.71) * (float)snO;
    float3 snI = floor(snX);
    float3 snF = snX - snI;
    float3 snU = snF * snF * snF * (snF * (snF * 6.0 - 15.0) + 10.0);
    float3 snDu = 30.0 * snF * snF * (snF * (snF - 2.0) + 1.0);
    float snC[8];
    [unroll] for (int snK = 0; snK < 8; ++snK)
    {
        uint3 snH = asuint(int3(snI) + int3(snK & 1, (snK >> 1) & 1, (snK >> 2) & 1)) * 1664525u + 1013904223u;
        snH.x += snH.y * snH.z; snH.y += snH.z * snH.x; snH.z += snH.x * snH.y;
        snH ^= snH >> 16u;
        snH.x += snH.y * snH.z; snH.y += snH.z * snH.x; snH.z += snH.x * snH.y;
        snC[snK] = (float)(snH.x >> 8u) * (1.0 / 16777215.0);
    }
    float snK1 = snC[1] - snC[0];
    float snK2 = snC[2] - snC[0];
    float snK3 = snC[4] - snC[0];
    float snK4 = snC[0] - snC[1] - snC[2] + snC[3];
    float snK5 = snC[0] - snC[2] - snC[4] + snC[6];
    float snK6 = snC[0] - snC[1] - snC[4] + snC[5];
    float snK7 = -snC[0] + snC[1] + snC[2] - snC[3] + snC[4] - snC[5] - snC[6] + snC[7];
    snVal[snO] = snC[0] + snK1 * snU.x + snK2 * snU.y + snK3 * snU.z + snK4 * snU.x * snU.y + snK5 * snU.y * snU.z
        + snK6 * snU.z * snU.x + snK7 * snU.x * snU.y * snU.z;
    float3 snD = snDu * float3(snK1 + snK4 * snU.y + snK6 * snU.z + snK7 * snU.y * snU.z,
                               snK2 + snK5 * snU.z + snK4 * snU.x + snK7 * snU.z * snU.x,
                               snK3 + snK6 * snU.x + snK5 * snU.y + snK7 * snU.x * snU.y);
    snGrad += snAmp * snD;
}
float3 snG = snGrad * SnowNoiseGain;
// LM4 item 5, the granular clumps: cellular (Voronoi) noise on the displaced surface's XY at SnowClumpCm.x (1-2 cm) and
// SnowClumpCm.y (4-8 cm), the feature points hashed per lattice cell (PCG3D: no repetition). Each clump is a low dome about
// its point (the slope half SnowClumpSlope at the cell's edge) with a crisp crease at the border to the next (the slope
// SnowClumpSlope at the border, none SnowClumpEdge of a cell in), and the gap darkened by SnowClumpGapDark (the fine scale
// half of it). Faded where a pixel spans a clump; the caller's SnowClumpGain (none on walls and plates).
float2 clGrad = float2(0.0, 0.0);
float clGap = 0.0;
[branch] if (SnowClumpGain > 0.001)   // LM4b: off unless SnowCellGrain brings LM4's grain back
{
[unroll] for (int clO = 0; clO < 2; ++clO)
{
    float clCell = max(clO == 0 ? SnowClumpCm.x : SnowClumpCm.y, 0.1);
    float clSlope = clO == 0 ? SnowClumpSlope.x : SnowClumpSlope.y;
    float clNear = 1.0 - smoothstep(0.3, 1.0, glPix / clCell);
    float2 clP = SnowPos.xy / clCell + float2(37.1, 19.3) * (float)clO;
    float2 clI = floor(clP);
    float2 clF = clP - clI;
    float clD1 = 1e9;
    float clD2 = 1e9;
    float2 clV1 = float2(0.0, 0.0);
    float2 clV2 = float2(0.0, 0.0);
    [unroll] for (int clK = 0; clK < 9; ++clK)
    {
        int2 clOff = int2(clK % 3 - 1, clK / 3 - 1);
        uint3 clH = asuint(int3(int2(clI) + clOff, 811 + clO)) * 1664525u + 1013904223u;
        clH.x += clH.y * clH.z; clH.y += clH.z * clH.x; clH.z += clH.x * clH.y;
        clH ^= clH >> 16u;
        clH.x += clH.y * clH.z; clH.y += clH.z * clH.x; clH.z += clH.x * clH.y;
        float2 clV = float2(clOff) + (float2)(clH.xy >> 8u) * (1.0 / 16777215.0) - clF;
        float clDd = dot(clV, clV);
        bool clNearer = clDd < clD1;
        bool clSecond = !clNearer && clDd < clD2;
        clD2 = clNearer ? clD1 : (clSecond ? clDd : clD2);
        clV2 = clNearer ? clV1 : (clSecond ? clV : clV2);
        clD1 = clNearer ? clDd : clD1;
        clV1 = clNearer ? clV : clV1;
    }
    float2 clN = normalize(clV1 - clV2 + float2(1e-6, 0.0));   // the way into the clump, square to its border
    float clE = max(-dot(0.5 * (clV1 + clV2), clN), 0.0);       // the distance to the border, cells
    float clIn = saturate(clE / max(SnowClumpEdge, 0.02));
    clGrad += clNear * clSlope * ((1.0 - clIn) * clN + 0.5 * clV1);
    clGap += clNear * (clO == 0 ? 0.5 : 1.0) * (1.0 - clIn);
}
}
snG += float3(clGrad, 0.0) * SnowClumpGain;
DETAIL_HOOK
float3 snNrm = normalize(SnowBaseN - (snG - SnowBaseN * dot(snG, SnowBaseN)));
float snVary = (1.0 + SnowAlbedoVary * (snVal[2] * 2.0 - 1.0)) * (1.0 - SnowClumpGapDark * saturate(clGap) * SnowClumpGain) * (1.0 - dtCav);
float snRoughSwing = SnowRoughVary * (snVal[1] * 2.0 - 1.0);
'''
# LM4b items 4-6: the caller defines DetCrumb, DetClod (the layers' normal gains), DetCavCrumb, DetCavClod (their cavity
# gains) and the texture SnowDetail; DETAIL_HLSL adds the detail's gradient to snG and leaves dtCav (the albedo's darkening).
# PARALLAX_HLSL (M_GT_Snow only) sets dtOffset, the parallax hit's slide, from the caller's edge, CamVec and SnowParallax*.
DETAIL_PRE='''// LM4b items 4-5, the snow-clump detail (T_GT_SnowDetail: R crumbs 1-4 cm, G clods 6-15 cm, B both; tileable over its
// tiling, linear): world-space tri-planar on the field's normal (the weights |n|^4) at two tilings that do not share a repeat
// (SnowDetailTileCm.x, .y), the 60 cm grain octave choosing between them (smoothly, so neither tiling's repeat shows).
float3 dtW = pow(abs(SnowBaseN), 4.0);
dtW /= max(dot(dtW, 1.0), 1e-4);
float dtMix = smoothstep(0.3, 0.7, snVal[2]);
float2 dtTile = max(SnowDetailTileCm.xy, 1.0);
float3 dtOffset = float3(0.0, 0.0, 0.0);
'''
PARALLAX_HLSL='''// LM4b item 6, the parallax experiment: parallax occlusion over B (1 the top) where E is over 0.2 and a pixel spans under
// SnowParallaxNearCm, in a frame from the field's normal: the ray descends along -n and slides in n's tangent plane; the map is
// read in n's dominant projection at the tiling the mix picks. SnowParallaxSteps layers over SnowParallaxCm, a linear refine
// between the last two; the hit's slide (faded in over E 0.2-0.4 and out with the distance) moves every detail lookup below.
{
    float3 pxAbs = abs(SnowBaseN);
    int pxAxis = pxAbs.x > pxAbs.y ? (pxAbs.x > pxAbs.z ? 0 : 2) : (pxAbs.y > pxAbs.z ? 1 : 2);
    bool pxSecond = dtMix >= 0.5;
    float pxS = pxSecond ? dtTile.y : dtTile.x;
    float2 pxUv0 = (pxAxis == 0 ? SnowPos.yz : (pxAxis == 1 ? SnowPos.xz : SnowPos.xy)) / pxS + (pxSecond ? float2(0.371, 0.613) : float2(0.0, 0.0)) + 0.29 * (float)pxAxis;
    float2 pxDx = ddx(pxUv0);
    float2 pxDy = ddy(pxUv0);
    float pxFade = saturate((edge - 0.2) / 0.2) * (1.0 - smoothstep(0.6 * SnowParallaxNearCm, SnowParallaxNearCm, glPix));
    [branch] if (SnowParallax > 0.5 && pxFade > 0.001)
    {
        float3 pxV = -normalize(CamVec);                        // from the eye into the surface
        float pxVn = min(dot(pxV, SnowBaseN), -0.25);           // its descent along -n per unit (grazing rays clamped)
        float3 pxVt = pxV - SnowBaseN * dot(pxV, SnowBaseN);    // its slide in the tangent plane
        float3 pxSlide = pxVt / (-pxVn) * max(SnowParallaxCm, 0.0);   // the slide over the whole depth, world cm
        float2 pxSlideUv = (pxAxis == 0 ? pxSlide.yz : (pxAxis == 1 ? pxSlide.xz : pxSlide.xy)) / pxS;
        int pxN = (int)clamp(SnowParallaxSteps, 4.0, 16.0);
        float pxStep = 1.0 / (float)pxN;
        float pxD = 0.0;
        float pxSurf = 1.0 - Texture2DSampleGrad(SnowDetail, SnowDetailSampler, pxUv0, pxDx, pxDy).b;
        float pxPrevD = 0.0;
        float pxPrevSurf = pxSurf;
        [loop] for (int pxK = 0; pxK < 16; ++pxK)
        {
            if (pxK >= pxN || pxD >= pxSurf) break;
            pxPrevD = pxD;
            pxPrevSurf = pxSurf;
            pxD += pxStep;
            pxSurf = 1.0 - Texture2DSampleGrad(SnowDetail, SnowDetailSampler, pxUv0 + pxSlideUv * pxD, pxDx, pxDy).b;
        }
        float pxA0 = pxPrevSurf - pxPrevD;
        float pxA1 = pxSurf - pxD;
        float pxHit = lerp(pxPrevD, pxD, saturate(pxA0 / max(pxA0 - pxA1, 1e-5)));
        dtOffset = pxSlide * (pxHit * pxFade);
    }
}
'''
DETAIL_MAIN='''float3 dtG = float3(0.0, 0.0, 0.0);
float dtCav = 0.0;
[unroll] for (int dtA = 0; dtA < 3; ++dtA)
{
    float dtWa = dtA == 0 ? dtW.x : (dtA == 1 ? dtW.y : dtW.z);
    float2 dtQ = dtA == 0 ? SnowPos.yz : (dtA == 1 ? SnowPos.xz : SnowPos.xy);
    float2 dtQo = dtA == 0 ? dtOffset.yz : (dtA == 1 ? dtOffset.xz : dtOffset.xy);
    [unroll] for (int dtT = 0; dtT < 2; ++dtT)
    {
        float dtWt = dtWa * (dtT == 0 ? 1.0 - dtMix : dtMix);
        float dtS = dtT == 0 ? dtTile.x : dtTile.y;
        float2 dtUvBase = dtQ / dtS + (dtT == 0 ? float2(0.0, 0.0) : float2(0.371, 0.613)) + 0.29 * (float)dtA;
        float2 dtDx = ddx(dtUvBase);   // the derivatives of the surface's own uv (the parallax slide is not differentiable)
        float2 dtDy = ddy(dtUvBase);
        float dtE = max(1.0 / 1024.0, 0.5 * max(length(dtDx), length(dtDy)));
        [branch] if (dtWt > 0.01)
        {
            float2 dtUv = dtUvBase + dtQo / dtS;
            float3 dtH0 = Texture2DSampleGrad(SnowDetail, SnowDetailSampler, dtUv, dtDx, dtDy).rgb;
            float3 dtHu = Texture2DSampleGrad(SnowDetail, SnowDetailSampler, dtUv + float2(dtE, 0.0), dtDx, dtDy).rgb;
            float3 dtHv = Texture2DSampleGrad(SnowDetail, SnowDetailSampler, dtUv + float2(0.0, dtE), dtDx, dtDy).rgb;
            float dtCm = dtE * dtS;
            float dtGu = (DetCrumb * SnowDetailCm.x * (dtHu.r - dtH0.r) + DetClod * SnowDetailCm.y * (dtHu.g - dtH0.g)) / dtCm;
            float dtGv = (DetCrumb * SnowDetailCm.x * (dtHv.r - dtH0.r) + DetClod * SnowDetailCm.y * (dtHv.g - dtH0.g)) / dtCm;
            dtG += dtWt * (dtA == 0 ? float3(0.0, dtGu, dtGv) : (dtA == 1 ? float3(dtGu, 0.0, dtGv) : float3(dtGu, dtGv, 0.0)));
            // The crevices: the lower half of each layer's heights darkens, by the caller's cavity gains.
            dtCav += dtWt * (DetCavCrumb * saturate(1.0 - dtH0.r / 0.5) + DetCavClod * saturate(1.0 - dtH0.g / 0.5));
        }
    }
}
snG += dtG;
dtCav = saturate(dtCav);
'''
# LM4f item 2 (M_GT_Snow only, SnowFastPath 2): after DETAIL_PRE, before the parallax and the detail's loop. Reads the caller's edge.
FAST_DETAIL_HLSL='''// LM4f item 2 (SnowFastPath 2, docs/LIVING_MUD_PLAN.md LM4f), the detail map's cheaper read: one top-down projection where the
// surface is under 30 deg (its normal within 30 deg of up; tri-planar only on the walls); none where the edge mask E is 0.05 or under
// (fading in over 0.05-0.10, so no line where it starts); one tiling (the first) where E is under 0.2, the second fading in over
// 0.2-0.3. The loop below skips every projection and tiling whose weight is 0.01 or under, so a skipped one costs nothing.
if (SnowFastPath > 1.5)
{
    if (SnowBaseN.z >= 0.8660254)
    {
        dtW = float3(0.0, 0.0, 1.0);
    }
    dtW *= saturate((edge - 0.05) / 0.05);
    dtMix *= saturate((edge - 0.2) / 0.1);
}
'''
def noise_hlsl(parallax,fast=False):
    # LM4b: the noise with the detail block in it (and the parallax before the detail on M_GT_Snow only).
    # LM4f: and M_GT_Snow's level-2 detail cut (fast) before both.
    return NOISE_HLSL.replace('DETAIL_HOOK',DETAIL_PRE+(FAST_DETAIL_HLSL if fast else '')+(PARALLAX_HLSL if parallax else '')+DETAIL_MAIN)
def noise_plain():
    # The apron without the detail map (APRON_DETAIL False): no detail, no cavity.
    return NOISE_HLSL.replace('DETAIL_HOOK','float dtCav = 0.0;\n')
# Leaves snL (toward the sun), snCol and snRough: fresh snow.
FRESH_HLSL='''// LM3b, fresh snow: SnowFreshAlbedo with a little blue where the surface turns from the sun (SnowShadeTint by
// 1 - 3 N.L; the sun is the Sky Atmosphere Light Direction 0, a fixed afternoon sun if the scene has none).
float3 snL = SunDir;
snL = dot(snL, snL) > 0.25 ? normalize(snL) : float3(-0.47, 0.76, 0.45);
float snShade = 1.0 - saturate(dot(snNrm, snL) * 3.0);
// LM4: the shade toward a neutral grey-blue, SnowShadeSaturation of the tint's own (0.5: half LM3b's).
float3 snLuma = float3(0.2126, 0.7152, 0.0722);
float3 snShadeTint = lerp(dot(SnowShadeTint, snLuma).xxx, SnowShadeTint, SnowShadeSaturation);
float3 snCol = SnowFreshAlbedo * lerp(float3(1.0, 1.0, 1.0), snShadeTint, snShade) * snVary;
float snRough = clamp(SnowFreshRough + snRoughSwing, 0.05, 1.0);
'''
# The caller defines glN, glRough, glPix (cm a pixel spans, from ddx/ddy outside any branch) and SnowGlintGain; GLINT_HLSL
# turns glN and dips glRough where a cell glints.
GLINT_HLSL='''// LM3b, the glint: GlintCellCm world cells (1 cm), each a facet (the surface normal tipped by a hashed random direction
// of GlintSpread), GlintDensity of them able to sparkle. Where a facet lines up with the half-vector of the sun and the
// eye within GlintAngleDeg, the normal turns to the half-vector and the roughness dips to GlintRough: the sun's
// highlight in that one cell. Only on surfaces facing the sun, and gone where a pixel spans more than three cells.
{
    float3 glV = normalize(CamVec);
    float3 glH = normalize(snL + glV);
    float glCell = max(GlintCellCm, 0.1);
    uint3 glHash = asuint(int3(floor(SnowPos / glCell))) * 1664525u + 1013904223u;
    glHash.x += glHash.y * glHash.z; glHash.y += glHash.z * glHash.x; glHash.z += glHash.x * glHash.y;
    glHash ^= glHash >> 16u;
    glHash.x += glHash.y * glHash.z; glHash.y += glHash.z * glHash.x; glHash.z += glHash.x * glHash.y;
    float3 glR = (float3)(glHash >> 8u) * (1.0 / 16777215.0);
    float glZ = glR.x * 2.0 - 1.0;
    float glPhi = glR.y * 6.28318531;
    float3 glRand = float3(sqrt(saturate(1.0 - glZ * glZ)) * float2(cos(glPhi), sin(glPhi)), glZ);
    float3 glFacet = normalize(glN + GlintSpread * glRand);
    float glCos = cos(radians(clamp(GlintAngleDeg, 0.1, 45.0)));
    float glAlign = smoothstep(glCos, lerp(glCos, 1.0, 0.35), dot(glFacet, glH));
    float glNear = 1.0 - smoothstep(glCell, 3.0 * glCell, glPix);
    float glOn = glR.z < GlintDensity ? 1.0 : 0.0;
    float glint = glOn * glAlign * glNear * saturate(dot(glN, snL) * 4.0) * saturate(SnowGlintGain);
    glN = normalize(lerp(glN, glH, glint));
    glRough = lerp(glRough, GlintRough, glint);
}
'''
SNOW_HLSL='''// LM3b (docs/LIVING_MUD_PLAN.md LM3b): the God of War look on snow. The bicubic field read, its slope, the normal n and the
// tracks above are the mud's, unchanged (and so are the WPO, the masked root and the hole). Everything below is procedural.
float3 SnowPos = WorldPos + float3(0.0, 0.0, s.r * 100.0);   // the displaced surface (as the clay's PaintPos): the grain sits on the cut
float3 SnowBaseN = n;
float packed = saturate(tracks);
float wall = smoothstep(SnowWallSlopeMin, max(SnowWallSlopeMax, SnowWallSlopeMin + 0.01), length(slope));
// Stage F's tread texture, point-sampled per field cell (read here since LM4: its B on snow is the lumps' mask,
// FGTMudField::PlateAlpha: LM4b's soft domes, LM4's plates before).
float2 cellUv = (floor(uv * PatchTexels.xy) + 0.5) / max(PatchTexels.xy, 1.0);
float4 tread = Texture2DSampleLevel(TreadTex, TreadTexSampler, cellUv, 0);
float lumps = saturate(tread.b);
// LM4b item 5, the edge mask E (0-1): the field's slope (SnowEdgeSlope.x..y, cm/cm), the tracks' boundary (the ragged band
// where the tracks are between 0 and 1: 4 t (1 - t)) and the lip band (raised SnowEdgeLipCm over the snow top next to tracked
// cells, or holding a lump: the lips' and the berm's soft domes).
float edgeSlope = smoothstep(SnowEdgeSlope.x, max(SnowEdgeSlope.y, SnowEdgeSlope.x + 0.01), length(slope));
float edgeTracks = saturate(4.0 * tracks * (1.0 - tracks));
float edgeLip = max(saturate(s.r * 100.0 / max(SnowEdgeLipCm, 0.1)) * saturate(4.0 * tracks), lumps);
float edge = saturate(max(edgeSlope, max(edgeTracks, edgeLip)));
// LM4d item 4: where the belly scraped (the tread texture's A at -1: its channel) the edge mask is at least BellyDetail, so the
// crumbs and the clods show there at mid strength instead of the packed floor's smooth crumbs.
edge = max(edge, BellyDetail * saturate(-tread.a));
float SnowNoiseGain = lerp(lerp(1.0, SnowPackedNoise, packed), SnowWallNoise, wall);
float SnowClumpGain = SnowCellGrain * lerp(1.0, SnowPackedClump, packed) * (1.0 - wall);   // LM4b: 0 (LM4's cellular grain gone)
float SnowGlintGain = (1.0 - packed) * (1.0 - wall);
float glPix = max(length(ddx(SnowPos)), length(ddy(SnowPos)));
// LM4b item 5, the detail's gains by E: fresh snow the crumbs at SnowDetailFresh and SnowCavityFresh, the packed floor the
// crumbs at SnowDetailPacked (smoother; the tread below), edges, walls, the lip and the berm both layers in full and SnowCavityEdge.
float DetCrumb = lerp(lerp(SnowDetailFresh, SnowDetailPacked, packed), 1.0, edge);
float DetClod = edge;
float DetCavCrumb = lerp(lerp(SnowCavityFresh, SnowCavityPacked, packed), SnowCavityEdge, edge);
float DetCavClod = SnowCavityEdge * edge;
'''+noise_hlsl(True,True)+FRESH_HLSL+'''// Packed snow (the tyres' floors, tracks 1): greyer-blue, smoother, glossier; the walls (the field's slope): a shade
// darker blue-grey compressed snow.
// LM4: the tints at SnowShadeSaturation of their own. LM4b: no plates' albedo (the plates are soft domes).
float3 snPackedTint = lerp(dot(SnowPackedTint, snLuma).xxx, SnowPackedTint, SnowShadeSaturation);
float3 snWallTint = lerp(dot(SnowWallTint, snLuma).xxx, SnowWallTint, SnowShadeSaturation);
float3 colPacked = SnowPackedAlbedo * snPackedTint * snVary;
float3 colWall = SnowWallAlbedo * snWallTint * snVary;
float3 col = lerp(lerp(snCol, colPacked, packed), colWall, wall);
float rough = lerp(lerp(snRough, SnowPackedRough + 0.5 * snRoughSwing, packed), SnowWallRough + 0.5 * snRoughSwing, wall);
float3 nOut = snNrm;
// Stage F, the tread (setup_m6_mud.py SURFACE_B, unchanged but for the normal it tilts): TreadTex carries per field cell
// the stamping wheel's heading (R, turns) and the lug phase at the cell's centre (G, turns of LugPeriod), point-sampled;
// the lug's smoothstep flank tilts the normal by LugTiltDeg (30 in snow) about the axis across the heading, only in a rut
// the tyre has been down and fading on the field's steep cross-slope.
// LM3c: A is the field's lug strength where a tyre's tread is set (0.25-1; 0 in the missing patches, and wherever no tyre
// has been: no lugs across the belly's channel) and -1 where the belly scraped (no tread; R is then the belly's heading).
float lugStrength = saturate(tread.a);
float scrape = saturate(-tread.a);
float lugAng = tread.r * 6.28318531;
float2 lugDir = float2(cos(lugAng), sin(lugAng));
float2 cellCentre = PatchMin.xy + cellUv * PatchSize.xy;
float lugP = frac(tread.g + dot(WorldPos.xy - cellCentre, lugDir) / max(LugPeriod, 1.0));
float lugW = clamp(LugWidth, 0.05, 0.9);
float lugF = max(1.0 - lugW, 0.05);
float lugS = frac(lugP + 0.5) - 0.5;
float lugT = saturate((abs(lugS) * 2.0 - lugW) / lugF);
float lugSlope = -4.0 * lugT * (1.0 - lugT) * (lugS >= 0.0 ? 1.0 : -1.0);
float2 lugCross = float2(-lugDir.y, lugDir.x);
float lugWall = 1.0 - smoothstep(max(LugWallFade, 0.05) * 0.5, max(LugWallFade, 0.05), abs(dot(slope, lugCross)));
float lugAmount = lugStrength * saturate((depth - LugDepthMin) / 0.15) * saturate((tracks - LugTracksMin) / 0.2) * lugWall;
nOut = normalize(float3(nOut.xy - lugDir * (tan(radians(LugTiltDeg)) * lugSlope * lugAmount * nOut.z), nOut.z));
// LM3c, the belly's scrape streaks: world value noise stretched along the belly's heading (R, the cell's heading), ScrapeLengthCm
// long and ScrapeWidthCm across (one lattice unit each way, so streaks 30-80 cm by 2-4 cm), quintic, PCG-hashed. Its slope
// across the heading tilts the normal by up to ScrapeSlope and its value swings the albedo by ScrapeAlbedo: faint grooves
// where the belly scraped, faded where a pixel spans a streak. The direction is the cell's heading binned to 5 degrees:
// neighbouring cells' headings differ by fractions of a degree as the car yaws, and 50 m from the world's origin that moves
// a 3 cm streak by tens of centimetres, so unbinned the streaks broke at every cell border (the first LM3c check's
// Snow_Floor_Close.png showed the 12.5 cm grid); binned, they run on unbroken until the heading turns past a bin.
// LM4e cut 6: where the streaks' amount is 0 (no scrape, a wall, or a pixel wider than a streak) they change nothing - the
// normal's renormalisation of a unit vector and the albedo times 1 - so with SnowFastPath the noise is not computed there.
float stNear = 1.0 - smoothstep(0.5, 1.5, glPix / max(ScrapeWidthCm, 0.1));
float stAmount = scrape * saturate(tracks) * (1.0 - wall) * stNear;
[branch] if (stAmount > 0.0 || SnowFastPath < 0.5)
{
    float stAng = round(tread.r * 72.0) * (6.28318531 / 72.0);
    float2 stDir = float2(cos(stAng), sin(stAng));
    float2 stAcross = float2(-stDir.y, stDir.x);
    float2 stP = float2(dot(SnowPos.xy, stDir) / max(ScrapeLengthCm, 1.0), dot(SnowPos.xy, stAcross) / max(ScrapeWidthCm, 0.1));
    float2 stI = floor(stP);
    float2 stF = stP - stI;
    float2 stU = stF * stF * stF * (stF * (stF * 6.0 - 15.0) + 10.0);
    float2 stDu = 30.0 * stF * stF * (stF * (stF - 2.0) + 1.0);
    float stC[4];
    [unroll] for (int stK = 0; stK < 4; ++stK)
    {
        uint3 stH = asuint(int3(int2(stI) + int2(stK & 1, stK >> 1), 977)) * 1664525u + 1013904223u;
        stH.x += stH.y * stH.z; stH.y += stH.z * stH.x; stH.z += stH.x * stH.y;
        stH ^= stH >> 16u;
        stH.x += stH.y * stH.z; stH.y += stH.z * stH.x; stH.z += stH.x * stH.y;
        stC[stK] = (float)(stH.x >> 8u) * (1.0 / 16777215.0);
    }
    float stK4 = stC[0] - stC[1] - stC[2] + stC[3];
    float stV = stC[0] + (stC[1] - stC[0]) * stU.x + (stC[2] - stC[0]) * stU.y + stK4 * stU.x * stU.y;
    float stD = stDu.y * ((stC[2] - stC[0]) + stK4 * stU.x) / 1.875;
    nOut = normalize(float3(nOut.xy - stAcross * (ScrapeSlope * clamp(stD, -1.0, 1.0) * stAmount * nOut.z), nOut.z));
    col *= 1.0 + ScrapeAlbedo * (stV * 2.0 - 1.0) * stAmount;
}
// LM4 item 5's faceted walls and plates are gone in LM4b (the detail map's crumbs and clods are the edges' response).
float3 glN = nOut;
float glRough = rough;
// LM4f item 2 (SnowFastPath 2): the glint fades out over 12-20 m (SnowCamDepth, the pixel's depth, cm) and is not computed where its
// gain is 0 (there, and on the packed floors and walls).
if (SnowFastPath > 1.5)
{
    SnowGlintGain *= 1.0 - smoothstep(1200.0, 2000.0, SnowCamDepth);
}
[branch] if (SnowFastPath < 1.5 || SnowGlintGain > 0.0)
'''+GLINT_HLSL+'''// The subsurface (the Slab's Wrap SSS): SnowSubsurfaceColor is the legacy subsurface colour the Slab exports. Substrate
// rescales the MFP by its 100 cm simple volume over the Slab's thickness (unwired: SUBSTRATE_LAYER_DEFAULT_THICKNESS_CM
// 0.01 cm) before taking the transmittance, so colour = exp(-0.01 / MFP) and MFP = -0.01 / ln(colour) cm (the first
// LM3b run took the 100 cm as the thickness, which made every MFP 10,000 times too long: a near-white subsurface colour
// at any amount, and a step at the box's border). Less in packed snow and on the walls, and nothing at the box's border
// (it fades in over the patch's taper, SnowEdgeCm), so the patch meets the landscape apron with the same response.
float2 snIn = min(WorldPos.xy - PatchMin.xy, PatchMin.xy + PatchSize.xy - WorldPos.xy);
float snEdge = smoothstep(0.0, max(SnowEdgeCm, 1.0), min(snIn.x, snIn.y));
float sssAmount = saturate(SnowSSS) * (1.0 - 0.5 * packed) * (1.0 - 0.5 * wall) * snEdge;
// LM4f item 2 (SnowFastPath 2): the subsurface fades to 0 over 20-35 m, so the far pixels carry no SSS (Substrate classifies them
// Simple, as LM3c measured with SnowSSS 0).
if (SnowFastPath > 1.5)
{
    sssAmount *= 1.0 - smoothstep(2000.0, 3500.0, SnowCamDepth);
}
float3 snSssTint = lerp(dot(SnowSubsurfaceColor, snLuma).xxx, SnowSubsurfaceColor, SnowShadeSaturation);   // LM4: the dial
float3 sssColour = clamp(snSssTint * sssAmount, 1e-4, 0.999);
SSSColor = sssAmount > 0.001 ? sssColour : float3(0.0, 0.0, 0.0);
SSSMfp = sssAmount > 0.001 ? -0.01 / log(sssColour) : float3(0.0, 0.0, 0.0);
Normal=glN;Rough=glRough;Mask=1.0;Emissive=0;
// LM4b: the edge mask's diagnostic view (E red over a dark grey, the parallax's reach yellow).
if(SnowEdgeDebug>0.5){Emissive=float3(0.04,0.04,0.05)+edge*float3(0.9,0.1,0.05)+(SnowParallax>0.5&&edge>0.2?float3(0.0,0.4,0.0):float3(0.0,0.0,0.0));col=0;Rough=1;SSSMfp=0;SSSColor=0;}
if(Diagnostic>0.5){Emissive=0.3*float3(saturate(0.5+s.r*100.0/80.0),saturate((WorldPos.z-DiagZ0)/max(DiagZRange,1.0)),tracks);col=0;Rough=1;SSSMfp=0;SSSColor=0;}
return col;
'''

def surface_prefix():
    tree=ast.parse((ROOT/'Art/Unreal/setup_m6_mud.py').read_text())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SURFACE_A' for t in n.targets))

def set_param(mat,expressions,cls,name,value,x,y):
    # The parameter node by name (the copied graph's, or a new one), its default set.
    node=next((e for e in expressions if isinstance(e,cls) and str(e.get_editor_property('parameter_name'))==name),None)
    if node is None:
        node=mel.create_material_expression(mat,cls,x,y);expressions.append(node)
    node.set_editor_property('parameter_name',name)
    if cls is u.MaterialExpressionVectorParameter:node.set_editor_property('default_value',u.LinearColor(value[0],value[1],value[2],1.0))
    else:node.set_editor_property('default_value',value)
    return node

def add_inputs(node,names):
    inputs=list(node.get_editor_property('inputs'));have=[str(i.get_editor_property('input_name')) for i in inputs]
    for name in names:
        if name not in have:
            slot=u.CustomInput();slot.set_editor_property('input_name',name);inputs.append(slot)
    node.set_editor_property('inputs',inputs)

def add_outputs(node,outs):
    outputs=list(node.get_editor_property('additional_outputs'));have=[str(o.get_editor_property('output_name')) for o in outputs]
    for name,kind in outs:
        if name not in have:
            o=u.CustomOutput();o.set_editor_property('output_name',name);o.set_editor_property('output_type',kind);outputs.append(o)
    node.set_editor_property('additional_outputs',outputs)

def view_nodes(mat,x,y):
    # The eye (CameraVectorWS, toward the camera) and the sun (Sky Atmosphere Light Direction 0, toward the light).
    cam=mel.create_material_expression(mat,u.MaterialExpressionCameraVectorWS,x,y)
    sun=mel.create_material_expression(mat,u.MaterialExpressionSkyAtmosphereLightDirection,x,y+100)
    sun.set_editor_property('light_index',0)
    return cam,sun

def wire_fresh_params(mat,expressions,node,x,y):
    k=0
    for name,value in FRESH_SCALARS.items():
        p=set_param(mat,expressions,u.MaterialExpressionScalarParameter,name,value,x,y+100*k);k+=1
        assert mel.connect_material_expressions(p,'',node,name),name
    for name,value in FRESH_VECTORS.items():
        p=set_param(mat,expressions,u.MaterialExpressionVectorParameter,name,value,x,y+100*k);k+=1
        assert mel.connect_material_expressions(p,'',node,name),name
    return k

def slab_pin(names,*keys):
    norm={n.lower().replace(' ','').replace('_','').replace('-',''):n for n in names}
    for key in keys:
        if key in norm:return norm[key]
    raise RuntimeError('the Substrate Slab has no pin %s (pins: %s)'%(keys,names))

def wrap_type():
    enum=getattr(u,'MaterialSubSurfaceType')
    if hasattr(enum,'MSS_WRAP'):return enum.MSS_WRAP
    return next(getattr(enum,k) for k in dir(enum) if 'WRAP' in k.upper() and 'TWO' not in k.upper())

def detail_node(mat,expressions,x,y):
    # LM4b item 4: the detail height map as a texture object (linear colour, the shared wrap sampler: no sampler slot of its own).
    tex=eal.load_asset(DETAIL_TEXTURE)
    assert tex,'no %s: run python Art/tools/bake_snow_detail.py, then & Art/import_snow_detail.ps1'%DETAIL_TEXTURE
    node=next((e for e in expressions if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='SnowDetail'),None)
    if node is None:
        node=mel.create_material_expression(mat,u.MaterialExpressionTextureObjectParameter,x,y);expressions.append(node)
    node.set_editor_property('parameter_name','SnowDetail')
    node.set_editor_property('texture',tex)
    node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    node.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    return node

def build_snow_material():
    # A fresh copy of the live mud graph every run, so the snow follows the mud's displacement and sampling as they are now.
    if eal.does_asset_exist(SNOW):assert eal.delete_asset(SNOW),'could not delete the old '+SNOW
    mat=eal.duplicate_asset(MUD,SNOW);assert mat,'could not copy '+MUD
    expressions=list(mel.get_material_expressions(mat))
    surface=next(e for e in expressions if isinstance(e,u.MaterialExpressionCustom) and (str(e.get_editor_property('desc'))=='Mud surface (PS)' or str(e.get_editor_property('description'))=='Mud surface (PS)'))
    names=list(FRESH_SCALARS)+list(FRESH_VECTORS)+list(SNOW_SCALARS)+list(SNOW_VECTORS)+['CamVec','SunDir','SnowDetail','SnowCamDepth']
    add_inputs(surface,names)
    add_outputs(surface,[('SSSMfp',u.CustomMaterialOutputType.CMOT_FLOAT3),('SSSColor',u.CustomMaterialOutputType.CMOT_FLOAT3)])
    k=wire_fresh_params(mat,expressions,surface,-1500,5200)
    for name,value in SNOW_SCALARS.items():
        p=set_param(mat,expressions,u.MaterialExpressionScalarParameter,name,value,-1500,5200+100*k);k+=1
        assert mel.connect_material_expressions(p,'',surface,name),name
    for name,value in SNOW_VECTORS.items():
        p=set_param(mat,expressions,u.MaterialExpressionVectorParameter,name,value,-1500,5200+100*k);k+=1
        assert mel.connect_material_expressions(p,'',surface,name),name
    cam,sun=view_nodes(mat,-1500,5200+100*k)
    assert mel.connect_material_expressions(cam,'',surface,'CamVec')
    assert mel.connect_material_expressions(sun,'',surface,'SunDir')
    detail=detail_node(mat,expressions,-1500,5400+100*k)
    assert mel.connect_material_expressions(detail,'',surface,'SnowDetail'),'SnowDetail'
    # LM4f item 2: the pixel's depth (cm) for SnowFastPath 2's glint and subsurface fades.
    depth=mel.create_material_expression(mat,u.MaterialExpressionPixelDepth,-1500,5500+100*k)
    assert mel.connect_material_expressions(depth,'',surface,'SnowCamDepth'),'SnowCamDepth'
    # Stage F's lugs at 30 degrees in snow: the copied graph's own LugTiltDeg parameter (AGTMudPatch does not push it).
    lug=next(e for e in expressions if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='LugTiltDeg')
    lug.set_editor_property('default_value',LUG_TILT_DEG)
    if SNOW_OPAQUE:mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)   # LM4e cut 5
    surface.set_editor_property('desc','Snow surface (PS, LM3b, LM3c, LM4, LM4b, LM4f)')
    surface.set_editor_property('code',surface_prefix()+SNOW_HLSL)
    # The shade: Substrate is on, so the surface goes into a Slab with Wrap SSS on the Front Material; the root keeps the
    # WPO and the opacity mask. If the Slab cannot be built, the legacy Subsurface shading model (the hidden conversion
    # gives the same Wrap slab) is the fallback, and the report says which.
    route={}
    try:
        slab=mel.create_material_expression(mat,u.MaterialExpressionSubstrateSlabBSDF,-150,700)
        pins=[str(n) for n in mel.get_material_expression_input_names(slab)]
        slab.set_editor_property('sub_surface_type',wrap_type())
        f0=set_param(mat,expressions,u.MaterialExpressionScalarParameter,'SnowF0',SLAB_SCALARS['SnowF0'],-500,900)
        wrap=set_param(mat,expressions,u.MaterialExpressionScalarParameter,'SnowSSSWrap',SLAB_SCALARS['SnowSSSWrap'],-500,1000)
        for out,keys in [('',('diffusealbedo',)),('Rough',('roughness',)),('Normal',('normal',)),('Emissive',('emissivecolor','emissive')),('SSSMfp',('sssmfp',))]:
            assert mel.connect_material_expressions(surface,out,slab,slab_pin(pins,*keys)),out
        assert mel.connect_material_expressions(f0,'',slab,slab_pin(pins,'f0'))
        assert mel.connect_material_expressions(wrap,'',slab,slab_pin(pins,'sssphaseanisotropy'))
        assert mel.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL),'could not connect the Slab to the Front Material'
        route=dict(route='Substrate Slab, Sub-Surface Type Wrap, SSS MFP from SnowSubsurfaceColor (Front Material)',slab_pins=pins,sub_surface_type=str(slab.get_editor_property('sub_surface_type')))
    except Exception as error:
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE)
        assert mel.connect_material_property(surface,'SSSColor',u.MaterialProperty.MP_SUBSURFACE_COLOR)
        opacity=set_param(mat,expressions,u.MaterialExpressionScalarParameter,'SnowSSSOpacity',1.0-SLAB_SCALARS['SnowSSSWrap'],-500,1100)
        assert mel.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
        route=dict(route='legacy Subsurface shading model (hidden Substrate conversion), the Slab failed',slab_error=str(error))
    errors=mel.recompile_material(mat);assert not errors,str(errors);eal.save_loaded_asset(mat)
    masked=masked_instance(mat)
    return {'material':mat.get_path_name(),'blend_mode':str(mat.get_editor_property('blend_mode')),'masked_instance':masked,'copied_from':MUD,'subsurface':route,'lug_tilt_deg':LUG_TILT_DEG,'detail_texture':DETAIL_TEXTURE,
        'fresh':dict(FRESH_SCALARS,**{k:list(v) for k,v in FRESH_VECTORS.items()}),'snow':dict(SNOW_SCALARS,**{k:list(v) for k,v in SNOW_VECTORS.items()}),'slab':SLAB_SCALARS,'compile_errors':list(errors or [])}

def masked_instance(parent):
    # LM4e cut 5: M_GT_Snow with its blend mode overridden back to masked (the copied root's), for the profile's A/B.
    if eal.does_asset_exist(SNOW_MASKED_MI):assert eal.delete_asset(SNOW_MASKED_MI),'could not delete the old '+SNOW_MASKED_MI
    folder,name=SNOW_MASKED_MI.rsplit('/',1)
    mi=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi,parent)
    over=mi.get_editor_property('base_property_overrides')
    over.set_editor_property('override_blend_mode',True);over.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    mi.set_editor_property('base_property_overrides',over)
    mel.update_material_instance(mi);eal.save_loaded_asset(mi)
    return dict(path=mi.get_path_name(),blend_mode=str(mi.get_editor_property('base_property_overrides').get_editor_property('blend_mode')))

def stats(path):
    # Representative shader instruction counts at GMaxRHIShaderPlatform (a synchronous compile): the cost beside the GPU timing.
    s=mel.get_statistics(eal.load_asset(path))
    return dict(material=path,pixel_instructions=s.num_pixel_shader_instructions,vertex_instructions=s.num_vertex_shader_instructions,
        samplers=s.num_samplers,pixel_texture_samples=s.num_pixel_texture_samples)

CLOD_SNOW_SCALARS={'ClodScaleCm':150.0,'SnowRough':0.7,'TintRange':0.05,'DetailScale':0.5}
CLOD_SNOW_COLOR=(0.82,0.82,0.82)   # LM3c item 4: albedo 0.82 (LM3a: 0.85 / 0.86 / 0.88)
# LM3c: the Slab's subsurface, M_GT_Snow's SnowSubsurfaceColor as an MFP (cm) by the same rule: MFP = -0.01 / ln(colour).
CLOD_SSS_COLOR=desaturate(SNOW_VECTORS['SnowSubsurfaceColor'],FRESH_SCALARS['SnowShadeSaturation'])   # LM4: at the shade dial
CLOD_SSS_MFP=tuple(-0.01/math.log(min(0.999,max(1e-4,c))) for c in CLOD_SSS_COLOR)
CLOD_SNOW_HLSL='''float3 gn=normalize(VertexNormal);
float3 w=pow(abs(gn),4.0); w/=max(dot(w,1.0),0.0001);
float3 det=0;
'''
for _coords,_weight,_normal in [('xy','z','float3(d.x,d.y,0)'),('xz','y','float3(d.x,0,d.y)'),('yz','x','float3(0,d.x,d.y)')]:
    CLOD_SNOW_HLSL+='''{
float2 f=frac(WorldPos.COORDS/(2.0*max(ScaleCm,1.0)));
float2 m=1-abs(f*2-1);float2 uv=float2(m.x,1-m.y);
float2 d=UnpackNormalMap(Texture2DSample(ClodN,ClodNSampler,uv)).xy*float2(f.x<0.5?1:-1,f.y<0.5?1:-1);
det+=w.WEIGHT*NORMAL;
}
'''.replace('COORDS',_coords).replace('WEIGHT',_weight).replace('NORMAL',_normal)
CLOD_SNOW_HLSL+='''// LM3c: white snow, the instance tint (TintRange), no darkening by freshness or wetness.
float3 col=SnowColor.rgb*(1.0+TintRange*(Rand*2.0-1.0));
Rough=SnowRough;
Nrm=normalize(gn+det*DetailScale);
return col;
'''

def build_snow_clod_material():
    assets=u.AssetToolsHelpers.get_asset_tools()
    folder,name=CLOD_SNOW.rsplit('/',1)
    mat=eal.load_asset(CLOD_SNOW) if eal.does_asset_exist(CLOD_SNOW) else assets.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property('tangent_space_normal',False)
    mel.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    custom=mel.create_material_expression(mat,u.MaterialExpressionCustom,-300,0)
    custom.set_editor_property('desc','Snow clod surface (LM3a)')
    custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    names=['ClodN','WorldPos','VertexNormal','Rand','ScaleCm','SnowColor','SnowRough','TintRange','DetailScale']
    slots=[]
    for n in names:
        slot=u.CustomInput();slot.set_editor_property('input_name',n);slots.append(slot)
    custom.set_editor_property('inputs',slots)
    outputs=[]
    for n,kind in [('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1),('Nrm',u.CustomMaterialOutputType.CMOT_FLOAT3)]:
        o=u.CustomOutput();o.set_editor_property('output_name',n);o.set_editor_property('output_type',kind);outputs.append(o)
    custom.set_editor_property('additional_outputs',outputs)
    custom.set_editor_property('code',CLOD_SNOW_HLSL)
    y=-600
    node=mel.create_material_expression(mat,u.MaterialExpressionTextureObjectParameter,-900,y);y+=150
    node.set_editor_property('parameter_name','ClodN');node.set_editor_property('texture',eal.load_asset('/Game/GrandTour/ArtTests/MudStyle/T_MS_ClayNormal'))
    node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    assert mel.connect_material_expressions(node,'',custom,'ClodN')
    wpos=mel.create_material_expression(mat,u.MaterialExpressionWorldPosition,-900,y);y+=150
    wpos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    assert mel.connect_material_expressions(wpos,'',custom,'WorldPos')
    vn=mel.create_material_expression(mat,u.MaterialExpressionVertexNormalWS,-900,y);y+=150
    assert mel.connect_material_expressions(vn,'',custom,'VertexNormal')
    rand=mel.create_material_expression(mat,u.MaterialExpressionPerInstanceRandom,-900,y);y+=150
    assert mel.connect_material_expressions(rand,'',custom,'Rand')
    colour=mel.create_material_expression(mat,u.MaterialExpressionVectorParameter,-900,y);y+=150
    colour.set_editor_property('parameter_name','SnowColor');colour.set_editor_property('default_value',u.LinearColor(CLOD_SNOW_COLOR[0],CLOD_SNOW_COLOR[1],CLOD_SNOW_COLOR[2],1))
    assert mel.connect_material_expressions(colour,'',custom,'SnowColor')
    for n,value in CLOD_SNOW_SCALARS.items():
        s=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-900,y);y+=100
        s.set_editor_property('parameter_name',n);s.set_editor_property('default_value',value)
        assert mel.connect_material_expressions(s,'',custom,'ScaleCm' if n=='ClodScaleCm' else n)
    # LM3c: M_GT_Snow's Substrate Slab (Wrap SSS, the snow's MFP, phase anisotropy and F0) on the Front Material, so the
    # clod's shaded side takes the snow's soft blue light; the legacy Default Lit inputs if the Slab cannot be built.
    route={}
    try:
        slab=mel.create_material_expression(mat,u.MaterialExpressionSubstrateSlabBSDF,0,0)
        pins=[str(n) for n in mel.get_material_expression_input_names(slab)]
        slab.set_editor_property('sub_surface_type',wrap_type())
        mfp=mel.create_material_expression(mat,u.MaterialExpressionVectorParameter,-300,300)
        mfp.set_editor_property('parameter_name','SnowSSSMfp');mfp.set_editor_property('default_value',u.LinearColor(CLOD_SSS_MFP[0],CLOD_SSS_MFP[1],CLOD_SSS_MFP[2],1))
        f0=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-300,450)
        f0.set_editor_property('parameter_name','SnowF0');f0.set_editor_property('default_value',SLAB_SCALARS['SnowF0'])
        wrap=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-300,550)
        wrap.set_editor_property('parameter_name','SnowSSSWrap');wrap.set_editor_property('default_value',SLAB_SCALARS['SnowSSSWrap'])
        for out,keys in [('',('diffusealbedo',)),('Rough',('roughness',)),('Nrm',('normal',))]:
            assert mel.connect_material_expressions(custom,out,slab,slab_pin(pins,*keys)),out
        assert mel.connect_material_expressions(mfp,'',slab,slab_pin(pins,'sssmfp'))
        assert mel.connect_material_expressions(f0,'',slab,slab_pin(pins,'f0'))
        assert mel.connect_material_expressions(wrap,'',slab,slab_pin(pins,'sssphaseanisotropy'))
        assert mel.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL),'could not connect the Slab to the Front Material'
        route=dict(route='Substrate Slab, Sub-Surface Type Wrap, SSS MFP %s cm (Front Material)'%(tuple(round(v,5) for v in CLOD_SSS_MFP),),slab_pins=pins,sub_surface_type=str(slab.get_editor_property('sub_surface_type')))
    except Exception as error:
        assert mel.connect_material_property(custom,'',u.MaterialProperty.MP_BASE_COLOR)
        assert mel.connect_material_property(custom,'Rough',u.MaterialProperty.MP_ROUGHNESS)
        assert mel.connect_material_property(custom,'Nrm',u.MaterialProperty.MP_NORMAL)
        route=dict(route='legacy Default Lit (the Slab failed)',slab_error=str(error))
    errors=mel.recompile_material(mat);assert not errors,str(errors);eal.save_loaded_asset(mat)
    return {'material':mat.get_path_name(),'color':CLOD_SNOW_COLOR,'scalars':CLOD_SNOW_SCALARS,'subsurface':route,'sss_mfp_cm':[round(v,5) for v in CLOD_SSS_MFP],'compile_errors':list(errors or [])}

# ---- the strip landscape's apron (setup_live_snow_drive.py): the same fresh-snow response, 3 m out from the patch box --
APRON_HLSL_HEAD='''// LM3b, the border: the landscape takes M_GT_Snow's fresh-snow response (the same NOISE/FRESH/GLINT code and numbers) at
// the snow patch box's border, fading to its own over ApronCm (3 m) outside it, and wherever its Snow layer lies. The box
// is the strip's measured patch box (ApronMin, ApronMax); the check compares it with the patch's own.
float2 apQ = abs(WorldPos.xy - (ApronMin.xy + ApronMax.xy) * 0.5) - (ApronMax.xy - ApronMin.xy) * 0.5;
float apOut = length(max(apQ, 0.0)) + min(max(apQ.x, apQ.y), 0.0);
float apron = 1.0 - smoothstep(0.0, max(ApronCm, 1.0), apOut);
Blend = saturate(max(apron, SnowLayer));
float3 SnowPos = WorldPos;
float3 SnowBaseN = normalize(VertexNormal);
float glPix = max(length(ddx(SnowPos)), length(ddy(SnowPos)));
float3 apCol = float3(0.85, 0.85, 0.85);
SnowN = SnowBaseN;
SnowRough = 0.7;
[branch] if (Blend > 0.001)
{
float SnowNoiseGain = 1.0;
float SnowClumpGain = SnowCellGrain;   // LM4b: 0 (LM4's cellular grain gone), as M_GT_Snow's fresh snow
float SnowGlintGain = 1.0;
// LM4b: M_GT_Snow's fresh-snow detail gains (E 0, not packed).
float DetCrumb = SnowDetailFresh;
float DetClod = 0.0;
float DetCavCrumb = SnowCavityFresh;
float DetCavClod = 0.0;
'''
APRON_HLSL_TAIL='''float3 glN = snNrm;
float glRough = snRough;
'''+GLINT_HLSL+'''apCol = snCol;
SnowN = glN;
SnowRough = glRough;
}
return apCol;
'''
APRON_HLSL=APRON_HLSL_HEAD+(noise_hlsl(False) if APRON_DETAIL else noise_plain())+FRESH_HLSL+APRON_HLSL_TAIL

def apply_snow():
    return [build_snow_material(),build_snow_clod_material()]
