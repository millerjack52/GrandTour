"""setup_m6_mud.py - the mud mesh material and its parameter collection (docs/MUD_DEFORMATION_PLAN.md, stage B).

Run with Art\\setup_m6_mud.bat (close the editor first; setup_m3_weather for MPC_Weather and setup_m1_trackpaint for
MPC_TrackPaint and RT_TrackPaint before it, setup_m6_hide after it: the landscape material reads the boxes). The whole
order since stage G is setup_m6_textures (only when the texture set changes), setup_m6_water, setup_m6_mud,
setup_m6_hide.
- MPC_TrackPaint (Terrain/) gains Patch0..Patch3 (a mud patch's world box, x0 y0 x1 y1 in cm; all zero = none) and
  PatchCount, written by UGTMudSubsystem at BeginPlay; a material may reference two collections and M_GT_Landscape
  already has weather and track paint, so the boxes ride with the paint (setup_m1_trackpaint keeps them on a rerun).
  M_GT_Landscape pushes its Mud and Bog layers back in depth inside these boxes (setup_m6_hide.py) so the mud mesh
  wins the depth test where a rut dips below the landscape.
- M_GT_Mud: masked, two-sided, world-space normal. The vertex shader samples the patch's field texture (MudField: R
  height m, GB slide offset m, A tracks) at the vertex's world XY inside PatchMin / PatchSize (x y cm; PatchTexels x y
  the texture's size: a vector parameter's main pin is RGB) and offsets Z by the height and XY by the offset, in cm.
  The pixel shader derives the normal from the height by central
  differences over a texel on top of the ground's vertex normal, takes the colour and roughness from the baked layer
  (GroundColor / BogColor, GroundRoughness / BogRoughness: the landscape's Mud and Bog rows), darkens and lowers the
  roughness toward WetRoughness by MPC_Weather's Wetness and in the rut floors (water collects). Since stage D the mask
  is 1 everywhere: the mesh is the ground over the whole box and the landscape has a hole under it (setup_m6_hide.py);
  until then it clipped where the field was untouched and the edge of that region was a seam. MudDiagnostic 1 draws everything as an
  emissive ramp scaled to 0.3 (the linear part of the tonemapper): R the mud height (0.5 flat, 0 at -40 cm, 1 at
  +40 cm), G the ground's Z from DiagZ0 over DiagZRange, B the tracks; the hide shots read it by pixel
  (Art/tools/sample_mud_diag.ps1). Rebuilt from scratch every run.
- Stage E2 (2026-09-15, MUD_ONE_SURFACE_PLAN section 3): the surface wears the CC0 "muddy_tracks" maps
  (setup_m6_textures.bat imports them; run it before this). TRIPLANAR_HLSL samples MudDiffuse / MudNormal / MudRough
  three times each, by the derived normal, at MudTileCm 150 cm, and the albedo is tinted by the layer row's colour
  divided by TextureMeanColor (the diffuse map's mean in linear space), so the tone stays the landscape's. The detail
  normal's XY adds to the field's normal (MudNormalScale), flattened by TrackFlatten inside the tracks; the roughness
  map swings the row's roughness by MudRoughVary; the wetness and rut-depth darkening and gloss still sit over it.
  M_GT_Landscape (setup_m6_hide.py) carries the same block with the same numbers on its Mud and Bog rows, so the two
  surfaces match at the mud patch's box border. Keep the two copies of TRIPLANAR_HLSL in step.
- Stage F (2026-09-16, MUD_ONE_SURFACE_PLAN section 3): the tyre's tread in the rut floors. AGTMudPatch keeps a second
  texture, MudTread (R the stamping wheel's heading in turns, G the lug phase in turns of LugPeriodCm at the cell's
  centre), uploaded with the same dirty rects as MudField. The surface shader point-samples it (snapping the uv to the
  texel centre: a wrapping angle cannot be filtered), carries the phase across the cell along that heading, and turns a
  smoothstep ridge of LugWidth into a normal tilt of LugTiltDeg about the axis across the heading, only inside a rut
  (LugDepthMin, LugTracksMin) and fading with the field's cross-slope (LugWallFade, a smoothstep from half of it, and
  note that a 25 cm rut is only two cells wide so its floor already reads 1.0-1.4) so the walls stay smooth. Nothing of
  the tread is in the height field: a 9 cm period cannot live on a 12.5 cm cell.
- Stage H (2026-09-16, MUD_ONE_SURFACE_PLAN section 3), the user's "less spiky, more random". H1: the field is sampled
  bicubic (Catmull-Rom, 16 taps) in WPO_HLSL and in SURFACE_HLSL, where the slope is the interpolant's own derivative
  over those same taps instead of a central difference, so a 12.5 cm grid draws a smooth surface with no crease at a
  cell edge. H2: TRIPLANAR_HLSL carries two octaves of world-space value noise (MudNoiseFineCm, MudNoiseCoarseCm) that
  warp the tri-planar uv (MudNoiseWarp) and swing the tint (MudNoiseTint) and the roughness (MudNoiseRough). The
  field's own randomness (the ridge clumps, the floor, the ragged tracks edge) is in FGTMudField, not here.
- Stage I (2026-09-16, MUD_ONE_SURFACE_PLAN section 3), the user's "still very sharp and uniform, needs to be more
  mudlike". I3 is this file's half: the tri-planar weights go to pow(abs(n), MudTriSharp 6) so a steep wall takes its
  own projection instead of the floor's streaked down it; inside the tracks the roughness falls toward WetRoughness by
  TrackWetLook 0.25 even in the dry, the tint darkens by TrackSlurryDarken 0.12 and the fine noise doubles (a worked
  slurry floor); and CrestRoughUp 0.1 takes the gloss off every cell standing above the ground. I1 and I2, the shape
  itself (the plateau bank, the waves along the rut, the slump and the clods), are in FGTMudField / AGTMudPatch.
- Stage J (2026-09-16, MUD_ONE_SURFACE_PLAN section 3), the user's "mud is too shiny, and there are these lines that
  appear after mud has been deformed". J1: the sourced roughness map reads wet, so the shared block now remaps its
  sample into MudRoughMin 0.70 - MudRoughMax 0.90 and that band *is* the mud's roughness (the rows' own 0.55 / 0.45
  and MudRoughVary's swing no longer reach it; both are kept as parameters, unused in the roughness path, so the row
  swing can come back with one line). TrackWetLook 0.25 -> 0, so a worked floor keeps its darker tint and its doubled
  noise but takes no wet gloss in the dry; the wetness path itself (MPC_Weather's Wetness toward WetRoughness) is
  untouched, and M_GT_Landscape's Mud and Bog rows take the same band through the same block. J2: LugTiltDeg 25 -> 0,
  so stage F's tread lays no normal tilt by default - the field still carries the heading and the phase and the
  texture still uploads, so it can come back subtler and broken later; nothing else of the tread changed.
Safe to re-run.
"""
import unreal

MAT = "/Game/GrandTour/Materials"
TERRAIN = "/Game/GrandTour/Terrain"
MPC_NAME = "MPC_TrackPaint"
MATERIAL = "M_GT_Mud"
TEX_PATH = "/Game/GrandTour/Textures/Mud"        # setup_m6_textures.bat imports the CC0 set here; run it first
# Stage E2's numbers. M_GT_Landscape (setup_m6_hide.py) MUST use the same three maps, the same tile and the same mean
# colour: the two surfaces meet at the mud patch's box border and any difference draws that border.
MUD_TILE_CM = 150.0                               # the texture's world size: 1.5 m per tile
TEXTURE_MEAN = (0.080993, 0.029794, 0.011753)     # the diffuse map's mean colour in linear space (setup_m6_textures.log)
MUD_NORMAL_SCALE = 1.0                            # how much of the detail normal's XY is added to the surface normal
MUD_ROUGH_VARY = 0.35                             # stage E2's swing of the row's roughness; unused since stage J's remap (kept as a parameter)
# Stage J1's numbers (2026-09-16), in TRIPLANAR_HLSL and so in both materials: the sourced roughness map reads wet
# (the user: "mud is too shiny"), so its sample is remapped into this band and the band is the mud's roughness - the
# map's own variation is kept, the gloss is not. setup_m6_hide.py carries the same two: keep them in step.
MUD_ROUGH_MIN = 0.70                              # the roughness the map's darkest (glossiest) pixel reads as
MUD_ROUGH_MAX = 0.90                              # and its brightest: dry mud is matte
TRACK_FLATTEN = 0.6                               # the detail normal flattens by this inside the tracks (smeared mud)
# Stage H2's numbers (2026-09-16), in TRIPLANAR_HLSL and so in both materials: two octaves of world-space value noise
# that warp the tri-planar uv (so the 150 cm tile does not read as a tile), swing the tint and swing the roughness.
# setup_m6_hide.py carries the same five, and the block is the same text: keep them in step.
MUD_NOISE_FINE_CM = 60.0                          # the fine octave's wavelength
MUD_NOISE_COARSE_CM = 250.0                       # the coarse octave's
MUD_NOISE_TINT = 0.08                             # the albedo varies by this much either way
MUD_NOISE_ROUGH = 0.1                             # the roughness varies by this much either way
MUD_NOISE_WARP = 0.15                             # the uv offset per octave, in tiles
# Stage I3's numbers (2026-09-16, MUD_ONE_SURFACE_PLAN section 3), the walls and the floor. MUD_TRI_SHARP is inside
# TRIPLANAR_HLSL and so lives in both materials: setup_m6_hide.py carries the same value.
MUD_TRI_SHARP = 6.0                               # the tri-planar weights' exponent, 4 until stage I: a steep wall takes its side projection instead of streaking the floor's
TRACK_WET_LOOK = 0.0                              # 0.25 until stage J (the user: too shiny): a worked floor takes no wet gloss in the dry now, only its darker tint and its doubled noise
TRACK_SLURRY_DARKEN = 0.12                        # and the tint goes this much darker there, on top of TrackDarken
CREST_ROUGH_UP = 0.1                              # roughness up by this on any cell standing above the ground: no gloss on a crest
# Stage F's numbers (docs/MUD_ONE_SURFACE_PLAN.md section 3): the tyre's lug pattern in the rut floors. The field carries
# a heading and a phase per cell (AGTMudPatch::TreadTexture) and this material turns them into a normal tilt; nothing of
# the tread is in the height field (a 9 cm period cannot live on a 12.5 cm cell). AGTMudPatch pushes its own LugPeriodCm
# onto the instance, so the field and the material always agree; this is the master's default.
LUG_PERIOD_CM = 9.0                               # cm of rolled distance per lug: about 11 a metre under a 25 cm tyre
LUG_WIDTH = 0.45                                  # the share of the period the lug's plateau takes, the rest is its flank
# Stage J2 (2026-09-16): 0, not the 25 of stage F. The user on foot: "there are these lines that appear after mud has
# been deformed, which doesn't look good at all" - the lugs read as regular stripes across the rut floor and up its
# walls. At 0 the tilt is nothing (tan(0) = 0) and the rest of the tread system stays exactly where it is: the field
# keeps writing the heading and the phase, the patch keeps uploading MudTread, and one number brings it back.
LUG_TILT_DEG = 0.0                                # how far the flank tilts the surface normal, about the axis across the heading
# The field's cross-slope (cm/cm) at which the lugs are gone, with a smoothstep from half of it: rut walls stay smooth.
# 3.0 and not the 0.6 of the first cut. A 25 cm tyre's rut is two 12.5 cm cells wide, so the central difference the
# surface normal is built from already reads 1.0-1.4 across the rut's own floor and 2.8 on its wall: at 0.6 the fade
# erased the lugs everywhere (the first hide_19 read 4 brightness peaks against the 23.4 lugs the field held).
LUG_WALL_FADE = 3.0
LUG_DEPTH_MIN = 0.05                              # the rut depth (0..1 of 30 cm) the lugs start at
LUG_TRACKS_MIN = 0.5                              # the tracks factor the lugs start at
# name in the material, asset, sampler type (matched to the asset's sRGB: a mismatch is a compile error)
MUD_MAPS = (
    ("MudDiffuse", "T_GT_Mud_Diffuse", "SAMPLERTYPE_COLOR"),
    ("MudNormal", "T_GT_Mud_Normal", "SAMPLERTYPE_NORMAL"),
    ("MudRough", "T_GT_Mud_Rough", "SAMPLERTYPE_LINEAR_COLOR"),
)

# Inputs: WorldPos (excluding offsets), PatchMin, PatchSize, PatchTexels, Tex. Height and offset are metres in the texture.
# Stage H1 (2026-09-16): the field is read bicubic (Catmull-Rom, 16 taps) and not by the hardware's bilinear, so the
# 12.5 cm grid displaces a smooth surface instead of linear ramps with a crease at every cell. No new vertices: the mesh
# already carries one per cell, and this is a smoother value at each of them.
WPO_HLSL = """float2 uv = (WorldPos.xy - PatchMin.xy) / PatchSize.xy;
float2 texels = max(PatchTexels.xy, 1.0);
float2 tc = uv * texels - 0.5;
float2 f = frac(tc);
float2 cbase = (floor(tc) + 0.5) / texels;
float4 wx = float4(f.x * (-0.5 + f.x * (1.0 - 0.5 * f.x)), 1.0 + f.x * f.x * (-2.5 + 1.5 * f.x),
                   f.x * (0.5 + f.x * (2.0 - 1.5 * f.x)), f.x * f.x * (-0.5 + 0.5 * f.x));
float4 wy = float4(f.y * (-0.5 + f.y * (1.0 - 0.5 * f.y)), 1.0 + f.y * f.y * (-2.5 + 1.5 * f.y),
                   f.y * (0.5 + f.y * (2.0 - 1.5 * f.y)), f.y * f.y * (-0.5 + 0.5 * f.y));
float4 s = float4(0.0, 0.0, 0.0, 0.0);
[unroll]
for (int j = 0; j < 4; ++j)
{
    [unroll]
    for (int i = 0; i < 4; ++i)
    {
        s += wx[i] * wy[j] * Texture2DSampleLevel(Tex, TexSampler, cbase + float2(i - 1, j - 1) / texels, 0);
    }
}
return float3(s.g * SlideScale, s.b * SlideScale, s.r) * 100.0;
"""

# Stage E2's tri-planar mud detail. This block is repeated word for word in setup_m6_hide.py (the landscape's
# "Landscape:mudtex" node) with gn the landscape's vertex normal instead of the mud's derived one: both materials must
# sample the same maps at the same world scale with the same tint, or the patch box's border shows. Keep them in step.
# Needs, in scope: WorldPos (cm), gn (the unit surface normal), TileCm, DiffTex/NormTex/RoughTex and their samplers,
# and (stage J1) RoughMin / RoughMax.
# Leaves: tex (the albedo), texRough (the roughness itself since stage J1, in RoughMin..RoughMax), dn (the detail
# normal in world space, unnormalised).
# Texture2DSample (not SampleLevel) outside every branch, so the hardware takes the gradients from the world-space UVs.
TRIPLANAR_HLSL = """float2 nfp = WorldPos.xy / max(NoiseFineCm, 1.0);
float2 nfi = floor(nfp);
float2 nff = nfp - nfi;
nff = nff * nff * (3.0 - 2.0 * nff);
float4 nfh = frac(sin(float4(dot(nfi, float2(127.1, 311.7)), dot(nfi + float2(1.0, 0.0), float2(127.1, 311.7)),
                             dot(nfi + float2(0.0, 1.0), float2(127.1, 311.7)), dot(nfi + float2(1.0, 1.0), float2(127.1, 311.7)))) * 43758.5453);
float nFine = lerp(lerp(nfh.x, nfh.y, nff.x), lerp(nfh.z, nfh.w, nff.x), nff.y) * 2.0 - 1.0;
float2 ncp = WorldPos.xy / max(NoiseCoarseCm, 1.0);
float2 nci = floor(ncp);
float2 ncf = ncp - nci;
ncf = ncf * ncf * (3.0 - 2.0 * ncf);
float4 nch = frac(sin(float4(dot(nci, float2(269.5, 183.3)), dot(nci + float2(1.0, 0.0), float2(269.5, 183.3)),
                             dot(nci + float2(0.0, 1.0), float2(269.5, 183.3)), dot(nci + float2(1.0, 1.0), float2(269.5, 183.3)))) * 27183.1717);
float nCoarse = lerp(lerp(nch.x, nch.y, ncf.x), lerp(nch.z, nch.w, ncf.x), ncf.y) * 2.0 - 1.0;
float nMud = 0.6 * nFine + 0.4 * nCoarse;
float2 warp = float2(nFine, nCoarse) * NoiseWarp;
float3 bl = pow(abs(gn), max(TriSharp, 1.0));
bl /= max(bl.x + bl.y + bl.z, 1e-4);
float tile = max(TileCm, 1.0);
float2 tuz = WorldPos.xy / tile + warp;
float2 tuy = WorldPos.xz / tile + warp;
float2 tux = WorldPos.yz / tile + warp;
float3 tex = bl.z * Texture2DSample(DiffTex, DiffTexSampler, tuz).rgb
           + bl.y * Texture2DSample(DiffTex, DiffTexSampler, tuy).rgb
           + bl.x * Texture2DSample(DiffTex, DiffTexSampler, tux).rgb;
tex *= 1.0 + NoiseTint * nMud;
float texRough = bl.z * Texture2DSample(RoughTex, RoughTexSampler, tuz).r
               + bl.y * Texture2DSample(RoughTex, RoughTexSampler, tuy).r
               + bl.x * Texture2DSample(RoughTex, RoughTexSampler, tux).r;
// Stage J1: the sourced roughness map reads wet, so its range is remapped into RoughMin..RoughMax and texRough is the
// roughness itself from here on - the layer rows' own roughness and MudRoughVary's swing no longer reach the mud.
texRough = clamp(lerp(RoughMin, RoughMax, saturate(texRough)), 0.02, 1.0);
float2 pz = Texture2DSample(NormTex, NormTexSampler, tuz).rg * 2.0 - 1.0;
float2 py = Texture2DSample(NormTex, NormTexSampler, tuy).rg * 2.0 - 1.0;
float2 px = Texture2DSample(NormTex, NormTexSampler, tux).rg * 2.0 - 1.0;
float3 tz = float3(pz, sqrt(saturate(1.0 - dot(pz, pz))));
float3 ty = float3(py, sqrt(saturate(1.0 - dot(py, py))));
float3 tx = float3(px, sqrt(saturate(1.0 - dot(px, px))));
float3 dn = bl.z * float3(tz.x, tz.y, tz.z * sign(gn.z))
          + bl.y * float3(ty.x, ty.z * sign(gn.y), ty.y)
          + bl.x * float3(tx.z * sign(gn.x), tx.x, tx.y);
"""

# Inputs: WorldPos (excluding offsets), PatchMin, PatchSize, PatchTexels, Tex, LayerTex, VertexNormal, Wetness, Diagnostic,
# DiagZ0, DiagZRange, GroundColor, BogColor, GroundRough, BogRough, TrackDarken, WetRough and (stage E2) DiffTex, NormTex,
# RoughTex, TileCm, MeanColor, RoughVary, NormalScale, TrackFlatten.
# Outputs: BaseColor (main), Normal, Rough, Emissive, Mask.
SURFACE_A = """float2 uv = (WorldPos.xy - PatchMin.xy) / PatchSize.xy;
float texelCm = PatchSize.x / PatchTexels.x;
// Stage H1: the same bicubic (Catmull-Rom, 16 taps) read as the vertex shader's, and the slope is the interpolant's
// own derivative over those same 16 taps - which is what a finite difference of bicubic samples converges to, at a
// fifth of the taps (a central difference of bicubic samples would need four more sets of 16). The surface and its
// normal are then smooth across a cell edge instead of creasing at every one.
float2 texels = max(PatchTexels.xy, 1.0);
float2 tc = uv * texels - 0.5;
float2 f = frac(tc);
float2 cbase = (floor(tc) + 0.5) / texels;
float4 wx = float4(f.x * (-0.5 + f.x * (1.0 - 0.5 * f.x)), 1.0 + f.x * f.x * (-2.5 + 1.5 * f.x),
                   f.x * (0.5 + f.x * (2.0 - 1.5 * f.x)), f.x * f.x * (-0.5 + 0.5 * f.x));
float4 wy = float4(f.y * (-0.5 + f.y * (1.0 - 0.5 * f.y)), 1.0 + f.y * f.y * (-2.5 + 1.5 * f.y),
                   f.y * (0.5 + f.y * (2.0 - 1.5 * f.y)), f.y * f.y * (-0.5 + 0.5 * f.y));
float4 dwx = float4(-0.5 + f.x * (2.0 - 1.5 * f.x), f.x * (-5.0 + 4.5 * f.x), 0.5 + f.x * (4.0 - 4.5 * f.x), f.x * (-1.0 + 1.5 * f.x));
float4 dwy = float4(-0.5 + f.y * (2.0 - 1.5 * f.y), f.y * (-5.0 + 4.5 * f.y), 0.5 + f.y * (4.0 - 4.5 * f.y), f.y * (-1.0 + 1.5 * f.y));
float4 s = float4(0.0, 0.0, 0.0, 0.0);
float dhx = 0.0;
float dhy = 0.0;
[unroll]
for (int j = 0; j < 4; ++j)
{
    [unroll]
    for (int i = 0; i < 4; ++i)
    {
        float4 t4 = Texture2DSampleLevel(Tex, TexSampler, cbase + float2(i - 1, j - 1) / texels, 0);
        s += wx[i] * wy[j] * t4;
        dhx += dwx[i] * wy[j] * t4.r;
        dhy += wx[i] * dwy[j] * t4.r;
    }
}
float2 slope = float2(dhx, dhy) * 100.0 / texelCm;
float3 vn = normalize(VertexNormal.xyz);
float nz = max(vn.z, 0.2);
float3 n = normalize(float3(vn.xy / nz - slope, 1.0));
float tracks = saturate(s.a);
float depth = saturate(-s.r * 100.0 / 30.0);
float wet = saturate(Wetness);
// The ground this mesh stands in for is the landscape's Mud or Bog layer under the texel (the patch bakes which into
// LayerTex, blended across the quads as the landscape blends its weightmap), churned a little darker where the tyres
// have been; water darkens the floors and glosses the mud only when it rains (until 2026-09-15 a dry rut was as glossy
// as a wet one, a pale sheet over black sky-lit walls).
float bog = saturate(Texture2DSampleLevel(LayerTex, LayerTexSampler, uv, 0).r);
float3 gn = n;
"""

SURFACE_B = """// Stage E2: the sourced mud maps over the whole surface, tinted so that the texture's own mean colour reads as the
// layer row's colour (MeanColor is the diffuse map's mean in linear space, measured by setup_m6_textures.bat), so the
// tone stays the landscape's while the detail comes from the photograph. The detail normal adds to the field's normal
// in XY; inside the tracks it flattens by TrackFlatten (churned mud is smeared) and the colour darkens by TrackDarken.
float3 row = lerp(GroundColor.rgb, BogColor.rgb, bog);
float3 col = saturate(tex * (row / max(MeanColor.rgb, 1e-4))) * lerp(1.0, TrackDarken, tracks);
col *= 1.0 - (0.35 + 0.25 * depth) * wet;
// Stage J1: texRough is the map remapped into RoughMin..RoughMax by the shared block and it is the roughness itself.
// Until then it swung the layer row's own roughness (GroundRough 0.55 / BogRough 0.45) by RoughVary either way, and
// both the rows and the map read wet: the user's "mud is too shiny". Those three are still parameters and still wired,
// so one line brings the row swing back; nothing reads them now.
float rough = clamp(texRough + NoiseRough * nMud, 0.02, 1.0);   // stage H2's noise, the same the tint took (the landscape's mud rows do this too)
// Stage I3, the slurry floor: mud a tyre has worked is wet-looking whatever the weather, so inside the tracks the
// roughness falls toward WetRough by TrackWetLook - 0 since stage J (the user: too shiny), so the line is a no-op
// until someone raises it again - the tint goes TrackSlurry darker on top of TrackDarken, and the
// fine octave of the world noise doubles there (nFine is TRIPLANAR_HLSL's own local), so the floor reads churned
// rather than clean. Then the crests: any cell standing above the ground loses CrestRough of its gloss, last of all,
// so a sunlit bank is matte even in the wet - it was the crest highlights that read as knife edges.
rough = lerp(rough, WetRough, saturate(TrackWetLook * tracks));
col *= lerp(1.0, 1.0 - saturate(TrackSlurry), tracks);
col *= 1.0 + NoiseTint * nFine * tracks;
rough = clamp(rough + NoiseRough * nFine * tracks, 0.02, 1.0);
rough = lerp(rough, WetRough, saturate(wet * (0.6 + 0.4 * tracks + 0.5 * depth)));
rough = clamp(rough + CrestRough * saturate(s.r * 100.0), 0.02, 1.0);
float3 nOut = normalize(float3(n.xy + dn.xy * NormalScale * lerp(1.0, 1.0 - TrackFlatten, tracks), n.z));
// Stage F, the tread. TreadTex carries, per field cell, the heading of the wheel that stamped it (R, turns) and the lug
// phase at that cell's centre (G, turns of LugPeriod). Point-sampled: a wrapping angle and a wrapping phase cannot be
// filtered, so the uv is snapped to the texel centre and the phase is carried across the cell along that heading -
// exactly the way FGTMudField::StampWheel wrote it, so the cells of one stamp join with no step. The lug is a plateau
// LugWidth of the period wide with a smoothstep flank; the flank's analytic slope (-1..1) tilts the normal about the
// axis across the heading by LugTiltDeg. It shows only in a rut the tyre has been down (LugDepthMin, LugTracksMin) and
// fades out where the field's cross-slope is steep, so the rut walls stay smooth. Never in the height field.
float2 cellUv = (floor(uv * PatchTexels.xy) + 0.5) / max(PatchTexels.xy, 1.0);
float2 tread = Texture2DSampleLevel(TreadTex, TreadTexSampler, cellUv, 0).rg;
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
float lugAmount = saturate((depth - LugDepthMin) / 0.15) * saturate((tracks - LugTracksMin) / 0.2) * lugWall;
nOut = normalize(float3(nOut.xy - lugDir * (tan(radians(LugTiltDeg)) * lugSlope * lugAmount * nOut.z), nOut.z));
float3 emissive = float3(0.0, 0.0, 0.0);
// Mud plan stage D, one surface: the mesh is the ground over the whole patch box, so no pixel is clipped and there is no
// boundary between touched and untouched mud. The landscape has a hole the size of the box (MUD_HOLE_HLSL in
// setup_m6_hide.py) and the mesh's outermost vertex ring sits EdgeLipCm over it. Until 2026-09-15 this clipped where the
// field was untouched (tracks > 0.02 || |height| > 5 mm) and that boundary was the seam the user saw. No draw-cost
// change: the triangles were drawn either way, only their pixels discarded.
float mask = 1.0;
if (Diagnostic > 0.5)
{
    // Scaled to 0.3 so the ramp stays on the linear part of the tonemapper's curve (0.5 would sit in its shoulder).
    emissive = 0.3 * float3(saturate(0.5 + s.r * 100.0 / 80.0), saturate((WorldPos.z - DiagZ0) / max(DiagZRange, 1.0)), tracks);
    col = float3(0.0, 0.0, 0.0);
    rough = 1.0;
    mask = 1.0;
}
Normal = nOut;
Rough = rough;
Emissive = emissive;
Mask = mask;
return col;
"""

SURFACE_HLSL = SURFACE_A + TRIPLANAR_HLSL + SURFACE_B

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def log(msg):
    unreal.log("SETUP_M6_MUD " + msg)


def connect(src, out_name, dst, in_name):
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


def upsert(params, cls, name, value):
    for p in params:
        if str(p.get_editor_property("parameter_name")) == name:
            p.set_editor_property("default_value", value)
            return params
    p = cls()
    p.set_editor_property("parameter_name", name)
    p.set_editor_property("default_value", value)
    params.append(p)
    return params


def custom(m, desc, inputs, code, x, y, outputs=()):
    node = mel.create_material_expression(m, unreal.MaterialExpressionCustom, x, y)
    node.set_editor_property("description", desc)
    node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    ins = []
    for name in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        ins.append(ci)
    node.set_editor_property("inputs", ins)
    outs = []
    for name, kind in outputs:
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", name)
        co.set_editor_property("output_type", kind)
        outs.append(co)
    node.set_editor_property("additional_outputs", outs)
    node.set_editor_property("code", code)
    return node


def scalar(m, name, value, x, y):
    e = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", value)
    return e


def vector(m, name, colour, x, y):
    e = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", unreal.LinearColor(*colour))
    return e


# ---- the patch boxes in MPC_TrackPaint --------------------------------------------------------
if eal.does_asset_exist(MAT + "/MPC_Mud"):   # the first cut had its own collection: one too many for the landscape
    eal.delete_asset(MAT + "/MPC_Mud")
    log("removed the stale MPC_Mud")
mpc_full = TERRAIN + "/" + MPC_NAME
if not eal.does_asset_exist(mpc_full):
    raise SystemExit("missing " + mpc_full + " (run Art/setup_m1_trackpaint.bat first)")
mpc = eal.load_asset(mpc_full)
vectors = list(mpc.get_editor_property("vector_parameters"))
for index in range(4):
    vectors = upsert(vectors, unreal.CollectionVectorParameter, "Patch%d" % index, unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
scalars = list(mpc.get_editor_property("scalar_parameters"))
scalars = upsert(scalars, unreal.CollectionScalarParameter, "PatchCount", 0.0)
mpc.set_editor_property("vector_parameters", vectors)
mpc.set_editor_property("scalar_parameters", scalars)
eal.save_loaded_asset(mpc)
log("collection %s: vectors %s scalars %s" % (MPC_NAME, [str(n) for n in mpc.get_vector_parameter_names()], [str(n) for n in mpc.get_scalar_parameter_names()]))

# ---- M_GT_Mud ---------------------------------------------------------------------------------
weather_full = MAT + "/MPC_Weather"
if not eal.does_asset_exist(weather_full):
    raise SystemExit("missing " + weather_full + " (run Art/setup_m3_weather.bat first)")
weather = eal.load_asset(weather_full)
rt_full = TERRAIN + "/RT_TrackPaint"
if not eal.does_asset_exist(rt_full):
    raise SystemExit("missing " + rt_full + " (run Art/setup_m1_trackpaint.bat first); the texture parameter needs a linear default")
rt = eal.load_asset(rt_full)

mat_full = MAT + "/" + MATERIAL
if eal.does_asset_exist(mat_full):
    eal.delete_asset(mat_full)
m = tools.create_asset(MATERIAL, MAT, unreal.Material, unreal.MaterialFactoryNew())
if m is None:
    raise SystemExit("could not create " + mat_full)
m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
m.set_editor_property("two_sided", False)   # one-sided since section 30: the landscape has a hole under the mesh, so nothing looks at its back
m.set_editor_property("tangent_space_normal", False)
m.set_editor_property("opacity_mask_clip_value", 0.5)

wpos = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -1100, -300)
wpos.set_editor_property("world_position_shader_offset", unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
patch_min = vector(m, "PatchMin", (0.0, 0.0, 0.0, 0.0), -1100, -150)
patch_size = vector(m, "PatchSize", (100.0, 100.0, 0.0, 0.0), -1100, 0)
patch_texels = vector(m, "PatchTexels", (8.0, 8.0, 0.0, 0.0), -1100, 75)
tex = mel.create_material_expression(m, unreal.MaterialExpressionTextureObjectParameter, -1100, 150)
tex.set_editor_property("parameter_name", "MudField")
tex.set_editor_property("texture", rt)
tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
vnormal = mel.create_material_expression(m, unreal.MaterialExpressionVertexNormalWS, -1100, 300)
wetness = mel.create_material_expression(m, unreal.MaterialExpressionCollectionParameter, -1100, 400)
wetness.set_editor_property("collection", weather)
wetness.set_editor_property("parameter_name", "Wetness")
diag = scalar(m, "MudDiagnostic", 0.0, -1100, 500)
diag_z0 = scalar(m, "DiagZ0", 0.0, -1100, 600)
diag_range = scalar(m, "DiagZRange", 100.0, -1100, 700)
ground_colour = vector(m, "GroundColor", (0.28, 0.20, 0.12, 1.0), -1100, 800)   # the landscape's Mud row (setup_m6_hide LAYERS)
bog_colour = vector(m, "BogColor", (0.18, 0.13, 0.08, 1.0), -1100, 950)         # its Bog row
ground_rough = scalar(m, "GroundRoughness", 0.55, -1100, 1100)
bog_rough = scalar(m, "BogRoughness", 0.45, -1100, 1200)
track_darken = scalar(m, "TrackDarken", 0.85, -1100, 1250)                       # churned mud against the ground it sits in
wet_rough = scalar(m, "WetRoughness", 0.12, -1100, 1300)
layer_tex = mel.create_material_expression(m, unreal.MaterialExpressionTextureObjectParameter, -1100, 225)
layer_tex.set_editor_property("parameter_name", "MudLayer")
layer_tex.set_editor_property("texture", rt)
layer_tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)

# ---- stage E2: the sourced mud maps, sampled tri-planar -----------------------------------------
maps = {}
for offset, (param_name, asset_name, sampler) in enumerate(MUD_MAPS):
    asset_full = TEX_PATH + "/" + asset_name
    if not eal.does_asset_exist(asset_full):
        raise SystemExit("missing " + asset_full + " (run Art/setup_m6_textures.bat first: it imports the CC0 mud set)")
    node = mel.create_material_expression(m, unreal.MaterialExpressionTextureObjectParameter, -1100, 1500 + 150 * offset)
    node.set_editor_property("parameter_name", param_name)
    node.set_editor_property("texture", eal.load_asset(asset_full))
    node.set_editor_property("sampler_type", getattr(unreal.MaterialSamplerType, sampler))
    maps[param_name] = node
    log("%s <- %s (%s)" % (param_name, asset_full, sampler))
tile = scalar(m, "MudTileCm", MUD_TILE_CM, -1100, 1950)
mean_colour = vector(m, "TextureMeanColor", TEXTURE_MEAN + (1.0,), -1100, 2050)
rough_vary = scalar(m, "MudRoughVary", MUD_ROUGH_VARY, -1100, 2200)   # stage E2's swing; nothing reads it since stage J1's remap
rough_min = scalar(m, "MudRoughMin", MUD_ROUGH_MIN, -1100, 2150)      # stage J1: the band the roughness map is remapped into
rough_max = scalar(m, "MudRoughMax", MUD_ROUGH_MAX, -1100, 2175)
normal_scale = scalar(m, "MudNormalScale", MUD_NORMAL_SCALE, -1100, 2300)
track_flatten = scalar(m, "TrackFlatten", TRACK_FLATTEN, -1100, 2400)

# ---- stage F: the tread in the rut floors ------------------------------------------------------
tread_tex = mel.create_material_expression(m, unreal.MaterialExpressionTextureObjectParameter, -1100, 2500)
tread_tex.set_editor_property("parameter_name", "MudTread")
tread_tex.set_editor_property("texture", rt)   # a linear default until AGTMudPatch binds its own
tread_tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
lug_period = scalar(m, "LugPeriodCm", LUG_PERIOD_CM, -1100, 2600)
lug_width = scalar(m, "LugWidth", LUG_WIDTH, -1100, 2700)
lug_tilt = scalar(m, "LugTiltDeg", LUG_TILT_DEG, -1100, 2800)
lug_wall = scalar(m, "LugWallFade", LUG_WALL_FADE, -1100, 2900)
lug_depth_min = scalar(m, "LugDepthMin", LUG_DEPTH_MIN, -1100, 3000)
lug_tracks_min = scalar(m, "LugTracksMin", LUG_TRACKS_MIN, -1100, 3100)

# ---- stage H2: the world-space noise over the mud maps ----------------------------------------
noise_fine = scalar(m, "MudNoiseFineCm", MUD_NOISE_FINE_CM, -1100, 3200)
noise_coarse = scalar(m, "MudNoiseCoarseCm", MUD_NOISE_COARSE_CM, -1100, 3300)
noise_tint = scalar(m, "MudNoiseTint", MUD_NOISE_TINT, -1100, 3400)
noise_rough = scalar(m, "MudNoiseRough", MUD_NOISE_ROUGH, -1100, 3500)
noise_warp = scalar(m, "MudNoiseWarp", MUD_NOISE_WARP, -1100, 3600)

# ---- stage I3: sharper tri-planar weights, a slurry floor, matte crests -----------------------
tri_sharp = scalar(m, "MudTriSharp", MUD_TRI_SHARP, -1100, 3700)
track_wet_look = scalar(m, "TrackWetLook", TRACK_WET_LOOK, -1100, 3800)
track_slurry = scalar(m, "TrackSlurryDarken", TRACK_SLURRY_DARKEN, -1100, 3900)
crest_rough = scalar(m, "CrestRoughUp", CREST_ROUGH_UP, -1100, 4000)

# The slide-away offset no longer moves the vertices (0): two stamps pushing a strip of cells from both sides (the rears'
# ruts beside the fronts', a second pass) crossed them over and folded the sheet, a lip with the rut floor visible under
# it (section 30). The field keeps the offset for the texture pass (a UV shift, as the reference uses it); the shots set 1
# to picture the fold. A sheet moved only up and down cannot fold.
slide_scale = scalar(m, "SlideScale", 0.0, -1100, 1400)
displace = custom(m, "Mud displace (VS)", ("WorldPos", "PatchMin", "PatchSize", "PatchTexels", "Tex", "SlideScale"), WPO_HLSL, -600, -300)
surface = custom(m, "Mud surface (PS)",
                 ("WorldPos", "PatchMin", "PatchSize", "PatchTexels", "Tex", "LayerTex", "VertexNormal", "Wetness", "Diagnostic", "DiagZ0", "DiagZRange",
                  "GroundColor", "BogColor", "GroundRough", "BogRough", "TrackDarken", "WetRough",
                  "DiffTex", "NormTex", "RoughTex", "TileCm", "MeanColor", "RoughVary", "RoughMin", "RoughMax", "NormalScale", "TrackFlatten",
                  "TreadTex", "LugPeriod", "LugWidth", "LugTiltDeg", "LugWallFade", "LugDepthMin", "LugTracksMin",
                  "NoiseFineCm", "NoiseCoarseCm", "NoiseTint", "NoiseRough", "NoiseWarp",
                  "TriSharp", "TrackWetLook", "TrackSlurry", "CrestRough"),
                 SURFACE_HLSL, -600, 200,
                 outputs=(("Normal", unreal.CustomMaterialOutputType.CMOT_FLOAT3), ("Rough", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
                          ("Emissive", unreal.CustomMaterialOutputType.CMOT_FLOAT3), ("Mask", unreal.CustomMaterialOutputType.CMOT_FLOAT1)))

for node, name in ((wpos, "WorldPos"), (patch_min, "PatchMin"), (patch_size, "PatchSize"), (patch_texels, "PatchTexels"), (tex, "Tex"), (slide_scale, "SlideScale")):
    connect(node, "", displace, name)
for node, name in ((wpos, "WorldPos"), (patch_min, "PatchMin"), (patch_size, "PatchSize"), (patch_texels, "PatchTexels"), (tex, "Tex"), (layer_tex, "LayerTex"), (vnormal, "VertexNormal"),
                   (wetness, "Wetness"), (diag, "Diagnostic"), (diag_z0, "DiagZ0"), (diag_range, "DiagZRange"),
                   (ground_colour, "GroundColor"), (bog_colour, "BogColor"), (ground_rough, "GroundRough"), (bog_rough, "BogRough"), (track_darken, "TrackDarken"), (wet_rough, "WetRough"),
                   (maps["MudDiffuse"], "DiffTex"), (maps["MudNormal"], "NormTex"), (maps["MudRough"], "RoughTex"),
                   (tile, "TileCm"), (mean_colour, "MeanColor"), (rough_vary, "RoughVary"), (rough_min, "RoughMin"), (rough_max, "RoughMax"),
                   (normal_scale, "NormalScale"), (track_flatten, "TrackFlatten"),
                   (tread_tex, "TreadTex"), (lug_period, "LugPeriod"), (lug_width, "LugWidth"), (lug_tilt, "LugTiltDeg"),
                   (lug_wall, "LugWallFade"), (lug_depth_min, "LugDepthMin"), (lug_tracks_min, "LugTracksMin"),
                   (noise_fine, "NoiseFineCm"), (noise_coarse, "NoiseCoarseCm"), (noise_tint, "NoiseTint"),
                   (noise_rough, "NoiseRough"), (noise_warp, "NoiseWarp"),
                   (tri_sharp, "TriSharp"), (track_wet_look, "TrackWetLook"), (track_slurry, "TrackSlurry"), (crest_rough, "CrestRough")):
    connect(node, "", surface, name)

for node, out_name, prop in ((surface, "", unreal.MaterialProperty.MP_BASE_COLOR), (surface, "Normal", unreal.MaterialProperty.MP_NORMAL),
                             (surface, "Rough", unreal.MaterialProperty.MP_ROUGHNESS), (surface, "Emissive", unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                             (surface, "Mask", unreal.MaterialProperty.MP_OPACITY_MASK), (displace, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)):
    if not mel.connect_material_property(node, out_name, prop):
        raise SystemExit("could not connect %s.%r to %s" % (node.get_name(), out_name, prop))

errors = [str(e) for e in mel.recompile_material(m)]
eal.save_loaded_asset(m)
if errors:
    for error in errors:
        unreal.log_error("SETUP_M6_MUD " + error)
    raise SystemExit(MATERIAL + " has compile errors")
log("%s: masked, one-sided, world-space normal, %d expressions; displaced by MudField inside PatchMin/PatchSize, MudDiagnostic ramp" % (MATERIAL, mel.get_num_material_expressions(m)))
log("mud texture: tri-planar %s / %s / %s at MudTileCm %.0f cm, tinted by lerp(GroundColor, BogColor, bog) / TextureMeanColor %.6f %.6f %.6f, "
    "detail normal added at MudNormalScale %.2f (flattened by TrackFlatten %.2f in the tracks), the roughness map remapped "
    "into MudRoughMin %.2f - MudRoughMax %.2f (stage J1; MudRoughVary %.2f no longer reads); M_GT_Landscape must match "
    "(setup_m6_hide.py)"
    % (MUD_MAPS[0][1], MUD_MAPS[1][1], MUD_MAPS[2][1], MUD_TILE_CM, TEXTURE_MEAN[0], TEXTURE_MEAN[1], TEXTURE_MEAN[2],
       MUD_NORMAL_SCALE, TRACK_FLATTEN, MUD_ROUGH_MIN, MUD_ROUGH_MAX, MUD_ROUGH_VARY))
log("mud tread (stage F): MudTread point-sampled per field cell (R heading turns, G lug phase), LugPeriodCm %.1f, LugWidth %.2f, "
    "LugTiltDeg %.1f, LugWallFade %.2f, LugDepthMin %.2f, LugTracksMin %.2f; a normal tilt only, nothing in the height field "
    "(AGTMudPatch pushes its own LugPeriodCm onto the instance)"
    % (LUG_PERIOD_CM, LUG_WIDTH, LUG_TILT_DEG, LUG_WALL_FADE, LUG_DEPTH_MIN, LUG_TRACKS_MIN))
log("stage H1: the field is read bicubic (Catmull-Rom, 16 taps) in the vertex shader and in the surface shader, whose slope "
    "is the interpolant's own derivative over the same taps (no finite difference); the field's own shape numbers are stage H's "
    "in FGTMudField / AGTMudPatch, not here")
log("stage H2 noise: two octaves of world-space value noise at MudNoiseFineCm %.0f and MudNoiseCoarseCm %.0f cm, the uv warped "
    "by MudNoiseWarp %.2f tiles per octave, the tint swung by MudNoiseTint %.2f and the roughness by MudNoiseRough %.2f; "
    "M_GT_Landscape must match (setup_m6_hide.py)"
    % (MUD_NOISE_FINE_CM, MUD_NOISE_COARSE_CM, MUD_NOISE_WARP, MUD_NOISE_TINT, MUD_NOISE_ROUGH))
log("stage I3: the tri-planar weights sharpened to pow(abs(n), %.0f) so a steep rut wall takes its side projection (4 until "
    "stage I, which streaked the floor's projection down the walls); the slurry floor inside the tracks - roughness toward "
    "WetRoughness by TrackWetLook %.2f even when dry, the tint %.0f %% darker (TrackSlurryDarken), the fine noise doubled; "
    "CrestRoughUp %.2f on any cell above the ground (no gloss on a crest); M_GT_Landscape carries the same MudTriSharp"
    % (MUD_TRI_SHARP, TRACK_WET_LOOK, 100.0 * TRACK_SLURRY_DARKEN, CREST_ROUGH_UP))
log("stage J1 (the shine): the roughness map is remapped into MudRoughMin %.2f - MudRoughMax %.2f in the shared block and "
    "that band is the mud's roughness (the rows' GroundRoughness %.2f / BogRoughness %.2f and MudRoughVary %.2f are still "
    "parameters and no longer reach it); TrackWetLook %.2f (0.25 until stage J), so a worked floor takes no wet gloss in the "
    "dry; the wetness path (Wetness toward WetRoughness %.2f) and CrestRoughUp are untouched; M_GT_Landscape's Mud and Bog "
    "rows take the same band (setup_m6_hide.py)"
    % (MUD_ROUGH_MIN, MUD_ROUGH_MAX, 0.55, 0.45, MUD_ROUGH_VARY, TRACK_WET_LOOK, 0.12))
log("stage J2 (the lines): LugTiltDeg %.1f (25.0 until stage J) - stage F's tread lays no normal tilt by default; the field "
    "still writes the heading and the phase, AGTMudPatch still uploads MudTread, and the other five lug numbers are unchanged"
    % LUG_TILT_DEG)
log("done")
