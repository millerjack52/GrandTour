"""setup_m1_body.py - vehicle and glass master materials with the dent function, headless.

Run with Art\\setup_m1_body.bat (close the editor first). Creates under /Game/GrandTour/Materials:
- RT_ImpactsDefault (in Terrain): a 32 x 2 float render target used only as the default texture
  of the ImpactTex parameter; at runtime UGTBodyComponent swaps in a transient float texture with
  the car's impact list (row 0 = local position xyz + radius, row 1 = local direction xyz + depth).
- MF_Dents: one custom HLSL node that loops the impact list and returns the world-space vertex
  offset (DentOffsetWS) and the bent tangent-space normal (DentNormalTS). Vertices move inward,
  against the record's outward direction, by depth x (1 - (d/r)^2)^2, scaled by how much the surface faces the impact,
  so a frontal hit dents the grille and not the roof. The normal tilts toward the dent centre by
  the analytic slope of that falloff. Dents cross panel seams because every panel reads the same
  texture in the same car space (panels are attached at the car origin).
- M_GT_Vehicle: BaseColor, Roughness, Metallic parameters; a Grime node (Dirt, DirtColour,
  DirtBottomZ, DirtHeight: dirt is heaviest at the sills and fades up the body in car space)
  whose result goes through MF_Weather (Wetness and Snow parameters as the local terms, the
  dirt mask as porosity so wet dirt darkens); MF_Dents into Normal and World Position Offset
  behind ImpactCount and DentStrength. Clear-coat shading model (ARCHITECTURE 6d: paint under a
  coat, so dirt and water can layer): ClearCoat x (1 - dirt mask) and ClearCoatRoughness go to the
  CustomData pins through UGTVehicleSetupLibrary.connect_material_custom_data (hidden from Python).
  Look L1 follow-up 3 (2026-09-24, VEHICLE_BUILD_SYSTEM 55): a painted path behind UsePaint (default 0) for the
  owner's GT Paint panel bakes - PaintAlbedo, PaintMask (R wear, G grime, B roughness) and PaintNormal, wired the way
  setup_look_l1.py wires M_GT_Painted (WearLighten, GrimeDarken 0; the normal behind M_GT_Painted's own NormalStrength,
  read from setup_look_l1.py). Each of the Grime node's BaseColor and Roughness inputs and the Normal pin is
  lerp(today's value, the painted value, UsePaint), so UsePaint 0 is today's material pixel for pixel; with UsePaint 1
  the dirt, MF_Weather wetness, the dents (their normal blended over the paint's) and the clear coat apply on top.
  UGTBodyComponent sets the textures and UsePaint 1 on a panel whose bake setup_look_l1.py imported.
- M_GT_Glass: translucent two-sided; BaseColor, Opacity, Roughness, a Crack parameter that
  whitens and thickens the glass (a crack pattern comes with the in-seat damage feedback item)
  and a Dirt parameter (mud throw-up) that browns and thickens it.
MudRunner MR2 (2026-10-08, docs/MUDRUNNER_LESSONS_PLAN.md MR2, VEHICLE_BUILD_SYSTEM 80): a muddy vehicle behind the CarMud
scalar (UGTBodyComponent sets it from gt.Mud.CarMud; 0 is the Grime node's flat DirtColour gradient pixel for pixel).
- M_GT_Vehicle's Grime node: the Standard bog slice (TA_MS_Bog{Color,Normal,Rough,Height}, MudSlice 0) tri-planar in car space
  at MudTileCm (100); a mud line at MudLineCm above the wheel bottoms (MudBaseZ, car space) broken by the bog's lumps and the
  car-space splatter (T_MudSplat_Splatter, a metre a tile, image down = car down), so its edge is splattered; the coat
  (MudCoat) from CoatEnds / CoatArches / CoatSides blended smoothly in car space round the wheels (WheelGeom: the axles' X, the
  hub height, the radius), so no panel seam shows; above the line thrown droplets thinning over AboveCm; below the last
  waterline (WashCm) clean by WashAmount; MudWet from wet (darker, glossy WetRough) to dried (lighter, matte DryRough). The bog's
  normal (car space, through a Local -> Tangent transform) by the coat. Both paths (UsePaint 0 and 1) go through it; the clear
  coat thins under it and MF_Weather takes it as porosity as before.
- M_GT_Tyre (new, skeletal mesh): the wheels' M_Wheel slot (it drew the engine's WorldGridMaterial): rubber and a rim by the
  radius from the hub (WheelGeom, RimShare), caked by TyreCoat (FL, FR, RL, RR) treads first, then the sidewall inward, the rim
  last, in the wheel's own rest-pose space (PreSkinnedPosition / Normal) so the mud turns with the wheel; MudWet wet/dry.
- M_GT_Glass: Dirt as mud splats (three layers of the splatter appearing as it rises), not a film.
MudRunner MR2b (2026-10-08, docs/MUDRUNNER_LESSONS_PLAN.md MR2b, VEHICLE_BUILD_SYSTEM 82): splatter with structure.
- The mud line is a curve along the body (s = x - y: car X on each side, across the ends, continuous at the corners), never a
  top-down sample (MR2's 7 m bog-height sample was constant up a side: tongues with vertical sides): the coat line x
  (1 - LineDropShare 0.35), two value-noise octaves along s (LineLongCm 80 / LineLongAmpCm 12, LineShortCm 25 / LineShortAmpCm 4),
  ArchRiseCm 15 over each arch smooth-stepped down over ArchRampCm 40 along car X: its slope at most 3 x 12 / 80 + 3 x 4 / 25 +
  1.5 x 15 / 40 = 1.49. Its edge broken at two scales: a fine value noise (EdgeNoiseCm 9 and a third of it, turned off the
  axes, EdgeNoiseAmpCm 3) and the splatter's droplets (EdgeSplatCm 8). The coat's thinning toward the line follows that line,
  its mottle a 40 cm noise on the side.
- The droplets above it show by a density: per arch a fan (an annular sector from the arch centre in the side plane, FanLowDeg
  -20 to FanHighDeg 105 from straight back, back = away from the wheel's last throw, FanDir; its density (1 - t)^FanFalloff 1.5
  over FanReachCm 120 from the arch's edge; radius and angle broken by a FanNoiseCm 25 noise) x the wheel's FanCoat, plus FanBase
  0.1 x the coat elsewhere (thinning over AboveCm above the line). T_MudSplat_Splatter's G is each droplet's rank (the bake,
  build_mud_splats.py), so the density shows that share of whole droplets: dense fans, sparse elsewhere, never evenly spread.
MudRunner MRP (2026-10-08, docs/MUDRUNNER_LESSONS_PLAN.md MRP items 1-2): physically based car mud behind MPC_TrackPaint's
MudPBR (gt.Mud.PBR; 0 is the look before MRP). The Grime node, M_GT_Tyre and M_GT_Glass read the Standard slice's ORH array
(TA_MS_BogORH: R AO, G roughness in the PBR bands, B height) in place of its rough and height maps; car mud is wet WetRoughPBR 0.5
(within 0.45-0.55) to dry DryRough 0.9 (within 0.85-0.95), the bake's roughness swinging it by at most +-0.025; the clear coat is
0 under full mud (ClearCoat x (1 - DirtMask), as MR2); the cavities tinted by the ORH's AO (CavityTint 0.15) and the AO on the
body's and the tyre's Ambient Occlusion pins; after MF_Weather a floor keeps mud at 0.45 or more (the weather's wet path would
take porous mud to 0.15); the glass's mud splats take the mud's roughness (they drew the pane's 0.05).
Requires MF_Weather (run Art/setup_m1_weather.bat first); MR2 also the bog arrays (Art/import_mud_variants.ps1) and the splatter
(Art/setup_mud_carry.ps1). After this script, Art/setup_m1_masters.bat (the glass's MF_Weather call).
Safe to re-run: the function is rebuilt, the masters are rebuilt from scratch.
"""
import unreal

TERRAIN = "/Game/GrandTour/Terrain"
MAT = "/Game/GrandTour/Materials"
MAX_IMPACTS = 32
# Look L1 follow-up 3: the painted path's default textures, sampled only while UsePaint is 0 (so never seen). Engine
# content, loaded with load_object: the commandlet's asset registry does not list them (EditorAssetLibrary.load_asset
# fails on FlatNormal, 2026-09-24). Each must carry the compression its sampler type demands.
PAINT_DEFAULTS = (("PaintAlbedo", "/Engine/EngineResources/DefaultTexture", "TC_DEFAULT"),
                  ("PaintMask", "/Engine/EngineMaterials/DefaultDiffuse_TC_Masks", "TC_MASKS"),
                  ("PaintNormal", "/Engine/EngineMaterials/FlatNormal", "TC_NORMALMAP"))

# MR2: the bog arrays (LM5b; slice 0 Standard) and the car-space splatter (MR1's bake).
BOG = "/Game/GrandTour/ArtTests/MudStyle"
# MRP: the ORH array (R AO, G roughness in the PBR bands, B height) in place of the rough and height arrays.
BOG_ARRAYS = (("BogC", "TA_MS_BogColor", "SAMPLERTYPE_COLOR"), ("BogN", "TA_MS_BogNormal", "SAMPLERTYPE_NORMAL"),
              ("BogORH", "TA_MS_BogORH", "SAMPLERTYPE_LINEAR_COLOR"))
MPC_TRACK = TERRAIN + "/MPC_TrackPaint"   # MRP: MudPBR (gt.Mud.PBR)
SPLATTER = "/Game/GrandTour/Mud/Splats/T_MudSplat_Splatter"
# Proposed (the owner names them after looking): MR1's ground numbers for wet and dried mud. The bog's colour, roughness and
# normal are read MudBlurMips mips down (3: the bake's lumps soften into mottled patches): sharp, at 100 cm and at 180 cm, the
# Standard bake's lumps read as a mosaic of round pebbles glued on the tailgate (Car_Muddy_Rear, the first two runs,
# 2026-10-08), the rejection list's pebble mosaic; its height stays sharp for the line's edge.
# The coat thins toward the line (the paint shows through in clusters), thick at the sills.
# MR2b (proposed, the owner names them after looking): the line a curve along the body with a rise over each arch and a jagged
# edge (Line*, Arch*, Edge*); the droplets above it by the wheels' fans (Fan*) and a sparse baseline (FanBase).
MUD_SCALARS = (("CarMud", 1.0), ("MudBaseZ", 0.0), ("MudLineCm", 0.0), ("WashCm", 0.0), ("WashAmount", 0.0), ("MudWet", 0.0),
               ("MudSlice", 0.0), ("MudTileCm", 100.0), ("SplatterTileCm", 100.0), ("AboveCm", 80.0), ("MudNormalStrength", 0.3),
               ("MudBlurMips", 3.0),
               ("DryLighten", 1.45), ("WetDarken", 0.78), ("WetRough", 0.3), ("DryRough", 0.9), ("WetRoughPBR", 0.5), ("CavityTint", 0.15),
               ("LineDropShare", 0.35), ("ArchRiseCm", 15.0), ("ArchRampCm", 40.0), ("LineLongCm", 80.0), ("LineLongAmpCm", 12.0),
               ("LineShortCm", 25.0), ("LineShortAmpCm", 4.0), ("EdgeNoiseCm", 9.0), ("EdgeNoiseAmpCm", 3.0), ("EdgeSplatCm", 8.0),
               ("FanReachCm", 120.0), ("FanLowDeg", -20.0), ("FanHighDeg", 105.0), ("FanFalloff", 1.5), ("FanNoiseCm", 25.0),
               ("FanNoiseAmpCm", 15.0), ("FanBase", 0.1))
MUD_VECTORS = (("CoatEnds", (0.0, 0.0, 0.0, 0.0)), ("CoatArches", (0.0, 0.0, 0.0, 0.0)), ("CoatSides", (0.0, 0.0, 0.0, 0.0)),
               ("WheelGeom", (140.0, -146.0, 38.0, 38.0)), ("FanCoat", (0.0, 0.0, 0.0, 0.0)), ("FanDir", (1.0, 1.0, 1.0, 1.0)))

# The Grime node. CarMud 0 is the pre-MR2 node exactly (the first block). MR2: the coat across the body from the region values,
# the bog tri-planar, the splattered line, the droplets above it, the washed band, wet and dry.
GRIME_HLSL = """DirtMask = 0.0;
MudNrm = float3(0.0, 0.0, 1.0);
NrmMask = 0.0;
MudAO = 1.0;
if (CarMud < 0.5)
{
    float m0 = Dirt * pow(saturate(1.0 - (LocalPos.z - DirtBottomZ) / max(DirtHeight, 1.0)), 1.5);
    DirtMask = m0;
    return float4(lerp(BaseColor.rgb, DirtColour.rgb, m0), lerp(Roughness, 0.9, m0));
}
float3 p = LocalPos;
float3 gn = normalize(LocalNormal);
MudNrm = gn;
// MR2b: a value noise (-1..1, smooth-step interpolated) on a sin-free hash.
struct GTMudNoise
{
    float Hash(float2 c)
    {
        float3 p3 = frac(float3(c.xyx) * 0.1031);
        p3 += dot(p3, p3.yzx + 33.33);
        return frac((p3.x + p3.y) * p3.z);
    }
    float Value(float2 q)
    {
        float2 i = floor(q);
        float2 f = q - i;
        f = f * f * (3.0 - 2.0 * f);
        float a = Hash(i);
        float b = Hash(i + float2(1.0, 0.0));
        float c = Hash(i + float2(0.0, 1.0));
        float d = Hash(i + float2(1.0, 1.0));
        return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y) * 2.0 - 1.0;
    }
};
GTMudNoise Nz;
float axF = WheelGeom.x;
float axR = WheelGeom.y;
float cz = WheelGeom.z;
float rad = max(WheelGeom.w, 1.0);
float h = p.z - MudBaseZ;
// MudCoat across the body: the regions blended smoothly in car space (sides, then the ends past the axles, the arches round
// the wheels, the roof), so no panel seam shows.
float sideC = p.y < 0.0 ? CoatSides.x : CoatSides.y;
float archF = p.y < 0.0 ? CoatArches.x : CoatArches.y;
float archR = p.y < 0.0 ? CoatArches.z : CoatArches.w;
float wF = saturate(2.6 - 1.2 * length(float2(p.x - axF, p.z - cz)) / rad);
float wR = saturate(2.6 - 1.2 * length(float2(p.x - axR, p.z - cz)) / rad);
float coat = sideC;
coat = lerp(coat, CoatEnds.x, saturate((p.x - (axF + rad)) / 60.0));
coat = lerp(coat, CoatEnds.y, saturate(((axR - rad) - p.x) / 60.0));
coat = lerp(coat, archF, wF);
coat = lerp(coat, archR, wR);
coat = lerp(coat, CoatEnds.z, saturate((h - 150.0) / 25.0));
if (coat < 0.002)
{
    return float4(BaseColor.rgb, Roughness);
}
float3 w = pow(abs(gn), 4.0);
w /= max(dot(w, 1.0), 0.0001);
float inv = 1.0 / max(MudTileCm, 1.0);
float3 sX = float3(float2(p.y, -p.z) * inv, MudSlice);
float3 sY = float3(float2(p.x, -p.z) * inv, MudSlice);
float3 sZ = float3(float2(p.x, p.y) * inv, MudSlice);
float bl = MudBlurMips;
float3 bc = w.x * Texture2DArraySampleBias(BogC, BogCSampler, sX, bl).rgb + w.y * Texture2DArraySampleBias(BogC, BogCSampler, sY, bl).rgb + w.z * Texture2DArraySampleBias(BogC, BogCSampler, sZ, bl).rgb;
// MRP: the ORH array - B the height (sharp, for the line's edge), R and G (AO, roughness) blurred as the colour.
float bh = w.x * Texture2DArraySample(BogORH, BogORHSampler, sX).b + w.y * Texture2DArraySample(BogORH, BogORHSampler, sY).b + w.z * Texture2DArraySample(BogORH, BogORHSampler, sZ).b;
float2 bo = w.x * Texture2DArraySampleBias(BogORH, BogORHSampler, sX, bl).rg + w.y * Texture2DArraySampleBias(BogORH, BogORHSampler, sY, bl).rg + w.z * Texture2DArraySampleBias(BogORH, BogORHSampler, sZ, bl).rg;
float2 nX = UnpackNormalMap(Texture2DArraySampleBias(BogN, BogNSampler, sX, bl)).xy;
float2 nY = UnpackNormalMap(Texture2DArraySampleBias(BogN, BogNSampler, sY, bl)).xy;
float2 nZ = UnpackNormalMap(Texture2DArraySampleBias(BogN, BogNSampler, sZ, bl)).xy;
float3 det = w.x * float3(0.0, nX.x, -nX.y) + w.y * float3(nY.x, 0.0, -nY.y) + w.z * float3(nZ.x, nZ.y, 0.0);
float si = 1.0 / max(SplatterTileCm, 1.0);
float2 gX = Texture2DSample(Splatter, SplatterSampler, float2(p.y, -p.z) * si).rg;
float2 gY = Texture2DSample(Splatter, SplatterSampler, float2(p.x, -p.z) * si).rg;
float2 gZ = Texture2DSample(Splatter, SplatterSampler, float2(p.x, p.y) * si).rg;
float spl = w.x * gX.x + w.y * gY.x + w.z * gZ.x;
// MR2b: each droplet's rank (the bake's G, weighted by the projections' coverage so a droplet keeps its own): a share D of whole
// droplets has a rank under D.
float rank = (w.x * gX.x * gX.y + w.y * gY.x * gY.y + w.z * gZ.x * gZ.y) / max(spl, 0.001);
// MR2b: the mud line, a curve along the body. s runs round it (x - y: car X on each side, across the ends, continuous at the
// corners), so each side has one line; MR2's 7 m top-down sample of the bog's height was constant up a side: rounded tongues
// with vertical sides. Two octaves along s (smooth-step value noise: each octave's slope at most 3 x its amplitude / its length)
// and a rise over each arch (full within the wheel's radius of its axle, smooth-stepped down over ArchRampCm): 0.45 + 0.48 +
// 0.56 = 1.49 at most with the proposed numbers, so no vertical walls.
float s = p.x - p.y;
float n1 = Nz.Value(float2(s / max(LineLongCm, 1.0), 7.0));
float n2 = Nz.Value(float2(s / max(LineShortCm, 1.0), 23.0));
float aF = 1.0 - smoothstep(rad, rad + max(ArchRampCm, 1.0), abs(p.x - axF));
float aR = 1.0 - smoothstep(rad, rad + max(ArchRampCm, 1.0), abs(p.x - axR));
float lineZ = MudLineCm * (1.0 - LineDropShare) + ArchRiseCm * max(aF, aR) + LineLongAmpCm * n1 + LineShortAmpCm * n2;
// Its edge broken at two scales: a fine value noise (EdgeNoiseCm and a third of it, turned off the axes) and the splatter's own
// droplets, so it is jagged, never rounded tongues.
float2 q = float2(0.8 * s + 0.6 * h, -0.6 * s + 0.8 * h) / max(EdgeNoiseCm, 1.0);
float en = Nz.Value(q) + 0.5 * Nz.Value(float2(0.6 * q.x - 0.8 * q.y, 0.8 * q.x + 0.6 * q.y) * 2.7 + 17.0);
float edge = lineZ + EdgeNoiseAmpCm * en + (spl - 0.17) * EdgeSplatCm;
float below = saturate((edge - h) / 2.0);
// Thick at the sills, thinning toward the line (the line's own shape), unevenly (a 40 cm mottle on the side and the bog's
// lumps), so near the line the paint shows through in clusters.
float rise = saturate(h / max(edge, 1.0));
float mo = Nz.Value(float2(s, h) / 40.0 + 5.0) * 0.5 + 0.5;
float thick = coat * (1.2 - 0.6 * rise) * (0.85 + 0.3 * mo) + 0.3 * (bh - 0.5) + 0.15 * spl;
float solid = below * smoothstep(0.45, 0.55, thick);
// MR2b: the wheel fans. Per arch an annular sector in the side plane from the arch centre, opening up and back (back: away from
// the wheel's last throw, FanDir +1 behind the arch), FanLowDeg..FanHighDeg from straight back, its density falling from the arch's
// edge over FanReachCm, its radius and angle broken by noise, x the wheel's FanCoat; plus FanBase x the coat elsewhere, thinning
// over AboveCm above the line. The splatter's droplets show by that density (their rank under it): dense in the fans, sparse
// elsewhere.
float fcF = p.y < 0.0 ? FanCoat.x : FanCoat.y;
float fcR = p.y < 0.0 ? FanCoat.z : FanCoat.w;
float fdF = p.y < 0.0 ? FanDir.x : FanDir.y;
float fdR = p.y < 0.0 ? FanDir.z : FanDir.w;
float2 fq = float2(s, h) / max(FanNoiseCm, 1.0);
float fnR = Nz.Value(fq);
float fnA = Nz.Value(fq + 41.0);
float lo = radians(FanLowDeg);
float hi = radians(FanHighDeg);
float fan = 0.0;
for (int k = 0; k < 2; k++)
{
    float ax = k == 0 ? axF : axR;
    float fd = k == 0 ? fdF : fdR;
    float2 d = float2((ax - p.x) * (fd < 0.0 ? -1.0 : 1.0), p.z - cz);
    float r = length(d) + FanNoiseAmpCm * fnR;
    float a = atan2(d.y, d.x) + 0.35 * fnA;
    float sector = smoothstep(lo - 0.25, lo + 0.25, a) * (1.0 - smoothstep(hi - 0.25, hi + 0.25, a));
    float t = saturate((r - rad) / max(FanReachCm, 1.0));
    fan += (k == 0 ? fcF : fcR) * sector * pow(1.0 - t, max(FanFalloff, 0.1));
}
float up = saturate(1.0 - (h - edge) / max(AboveCm, 1.0));
float dens = saturate(fan + FanBase * coat * up);
float keep = saturate((dens - rank) / 0.04 + 0.5);
float drops = (1.0 - solid) * smoothstep(0.45, 0.6, spl) * keep;
float m = max(solid, drops);
// The last wash: clean below its waterline, the line ragged too.
float wl = WashCm + (spl - 0.17) * 6.0 + (bh - 0.5) * 6.0 + n1 * 4.0;
m *= 1.0 - saturate(WashAmount) * saturate((wl - h) / 3.0);
float wet = saturate(MudWet);
float3 mud = lerp(bc * DryLighten + 0.01, bc * WetDarken, wet);
float mr;
if (PBR > 0.5)
{
    // MRP: wet WetRoughPBR (0.5) to dry DryRough (0.9), the bake's roughness swinging it a little, held in the bands: wet 0.45-0.55,
    // dry 0.85-0.95. The cavities tinted by the AO (CavityTint), the AO onto the material's pin (MudAO).
    mr = clamp(lerp(DryRough, WetRoughPBR, wet) + (bo.y - 0.7) * 0.1, lerp(0.85, 0.45, wet), lerp(0.95, 0.55, wet));
    mud *= 1.0 - saturate(CavityTint) * (1.0 - bo.x);
    MudAO = lerp(1.0, bo.x, m);
}
else
{
    float br = 0.14 + (bo.y - 0.45) * 1.54;   // the bake's own roughness (the ORH's remap inverted): MR2 exactly
    mr = saturate(lerp(DryRough, WetRough, wet) + (br - 0.5) * 0.2);
}
DirtMask = m;
NrmMask = m;
MudNrm = normalize(gn + det * MudNormalStrength);
return float4(lerp(BaseColor.rgb, mud, m), lerp(Roughness, mr, m));
"""
GRIME_INPUTS = ("BaseColor", "Roughness", "DirtColour", "Dirt", "LocalPos", "DirtBottomZ", "DirtHeight", "LocalNormal", "CoatEnds",
                "CoatArches", "CoatSides", "WheelGeom", "FanCoat", "FanDir", "BogC", "BogN", "BogORH", "Splatter", "PBR") + tuple(n for n, _v in MUD_SCALARS)
# MRP: after MF_Weather, mud's roughness held at 0.45 or more (PBR): the weather's wet path takes porous surfaces toward 0.15.
FLOOR_HLSL = "return PBR > 0.5 ? lerp(R, max(R, 0.45), saturate(Mask)) : R;\n"

# M_GT_Tyre: rubber and rim by the radius from the hub, the mud in the wheel's own rest-pose space (it turns with the wheel).
TYRE_SCALARS = (("CarMud", 1.0), ("MudWet", 0.0), ("MudSlice", 0.0), ("TyreTileCm", 50.0), ("RimShare", 0.62),
                ("DryLighten", 1.45), ("WetDarken", 0.78), ("WetRough", 0.3), ("DryRough", 0.9), ("WetRoughPBR", 0.5), ("CavityTint", 0.15))
TYRE_VECTORS = (("TyreCoat", (0.0, 0.0, 0.0, 0.0)), ("WheelGeom", (140.0, -146.0, 38.0, 38.0)),
                ("RubberColour", (0.022, 0.021, 0.02, 1.0)), ("RimColour", (0.3, 0.3, 0.31, 1.0)))
TYRE_HLSL = """float3 p = Pos;
float3 n = normalize(Nrm);
float axF = WheelGeom.x;
float axR = WheelGeom.y;
float rad = max(WheelGeom.w, 1.0);
bool front = p.x > 0.5 * (axF + axR);
float coat = front ? (p.y < 0.0 ? TyreCoat.x : TyreCoat.y) : (p.y < 0.0 ? TyreCoat.z : TyreCoat.w);
coat = CarMud > 0.5 ? saturate(coat) : 0.0;
float r = length(float2(p.x - (front ? axF : axR), p.z - WheelGeom.z)) / rad;
float rim = 1.0 - smoothstep(RimShare - 0.03, RimShare + 0.03, r);
float3 base = lerp(RubberColour.rgb, RimColour.rgb, rim);
Rough = lerp(0.85, 0.45, rim);
Metal = 0.6 * rim;
MudMask = 0.0;
MudAO = 1.0;
if (coat < 0.002)
{
    return base;
}
float3 w = pow(abs(n), 4.0);
w /= max(dot(w, 1.0), 0.0001);
float inv = 1.0 / max(TyreTileCm, 1.0);
float3 sX = float3(float2(p.y, -p.z) * inv, MudSlice);
float3 sY = float3(float2(p.x, -p.z) * inv, MudSlice);
float3 sZ = float3(float2(p.x, p.y) * inv, MudSlice);
float3 bc = w.x * Texture2DArraySampleBias(BogC, BogCSampler, sX, 2.0).rgb + w.y * Texture2DArraySampleBias(BogC, BogCSampler, sY, 2.0).rgb + w.z * Texture2DArraySampleBias(BogC, BogCSampler, sZ, 2.0).rgb;
float bh = w.x * Texture2DArraySample(BogORH, BogORHSampler, sX).b + w.y * Texture2DArraySample(BogORH, BogORHSampler, sY).b + w.z * Texture2DArraySample(BogORH, BogORHSampler, sZ).b;
float spl = w.x * Texture2DSample(Splatter, SplatterSampler, float2(p.y, -p.z) * 0.02).r + w.y * Texture2DSample(Splatter, SplatterSampler, float2(p.x, -p.z) * 0.02).r + w.z * Texture2DSample(Splatter, SplatterSampler, float2(p.x, p.y) * 0.02).r;
// Treads first (the tread face takes mud at the least coat), then the sidewall from the tread inward as the coat grows, the rim last.
float tread = (1.0 - smoothstep(0.5, 0.8, abs(n.y))) * smoothstep(0.85, 0.93, r);
float need = lerp(saturate(1.0 - r) * 1.5 + 0.1, 0.0, tread);
float m = smoothstep(-0.05, 0.05, coat * 1.1 - need + (bh - 0.5) * 0.35 + (spl - 0.17) * 0.25);
float wet = saturate(MudWet);
float3 mud = lerp(bc * DryLighten + 0.01, bc * WetDarken, wet);
MudMask = m;
if (PBR > 0.5)
{
    // MRP: the tyres' mud as the body's: wet WetRoughPBR 0.5 to dry DryRough 0.9, the cavities by the AO (two mips down, as the colour).
    float ao = w.x * Texture2DArraySampleBias(BogORH, BogORHSampler, sX, 2.0).r + w.y * Texture2DArraySampleBias(BogORH, BogORHSampler, sY, 2.0).r + w.z * Texture2DArraySampleBias(BogORH, BogORHSampler, sZ, 2.0).r;
    Rough = lerp(Rough, clamp(lerp(DryRough, WetRoughPBR, wet), 0.45, 0.95), m);
    mud *= 1.0 - saturate(CavityTint) * (1.0 - ao);
    MudAO = lerp(1.0, ao, m);
}
else
{
    Rough = lerp(Rough, saturate(lerp(DryRough, WetRough, wet)), m);
}
Metal = lerp(Metal, 0.0, m);
return lerp(base, mud, m);
"""
TYRE_INPUTS = ("Pos", "Nrm", "TyreCoat", "WheelGeom", "RubberColour", "RimColour", "BogC", "BogORH", "Splatter", "PBR") + tuple(n for n, _v in TYRE_SCALARS)

# M_GT_Glass: CarMud 0 the old film; MR2 the Dirt as splats (three layers of the splatter appearing as it rises), the pane's own
# local space (the greybox cube, -50..50) scaled to cm by GlassSizeX / Y, a metre a tile.
GLASS_HLSL = """Rough = BaseRough;
if (CarMud < 0.5)
{
    Opacity = BaseOpacity + Dirt * 0.4;
    return lerp(Tint.rgb, float3(0.22, 0.17, 0.11), Dirt * 0.6);
}
float2 uv = LocalPos.xy * float2(SizeX, SizeY) / 10000.0;
float s1 = Texture2DSample(Splatter, SplatterSampler, uv).r * step(0.02, Dirt);
float s2 = Texture2DSample(Splatter, SplatterSampler, uv * 1.37 + 0.31).r * step(0.35, Dirt);
float s3 = Texture2DSample(Splatter, SplatterSampler, uv * 0.73 + 0.57).r * step(0.7, Dirt);
float m = smoothstep(0.4, 0.6, max(s1, max(s2, s3)));
float3 mud = lerp(float3(0.102, 0.058, 0.027), float3(0.055, 0.031, 0.015), saturate(MudWet));
Opacity = lerp(BaseOpacity, 0.97, m);
// MRP: a mud splat on the glass is mud (wet 0.5 to dry 0.9), not the pane's gloss; gt.Mud.PBR 0 as before.
if (PBR > 0.5)
{
    Rough = lerp(BaseRough, lerp(0.9, 0.5, saturate(MudWet)), m);
}
return lerp(Tint.rgb, mud, m);
"""

# Custom node inputs: LocalPos, LocalNormal (car space), Tex (32 x 2 float), Count, Strength.
# Main output: local-space vertex offset. Additional output Normal: bent local-space normal.
HLSL = """float3 offset = float3(0.0, 0.0, 0.0);
float3 tilt = float3(0.0, 0.0, 0.0);
float3 N = normalize(LocalNormal);
int count = min((int)Count, %(max)d);
for (int i = 0; i < %(max)d; ++i)
{
    if (i >= count) break;
    float u = (i + 0.5) / %(max)d.0;
    float4 a = Texture2DSampleLevel(Tex, TexSampler, float2(u, 0.25), 0);
    float4 b = Texture2DSampleLevel(Tex, TexSampler, float2(u, 0.75), 0);
    float3 rv = LocalPos - a.xyz;
    float r = max(a.w, 1.0);
    float d = length(rv);
    if (d < r)
    {
        float s = d / r;
        float w = 1.0 - s * s;
        w = w * w;
        float eff = b.w * saturate(dot(b.xyz, N)) * Strength;   // b.xyz points outward, toward what hit us
        offset -= b.xyz * eff * w;
        float3 rt = rv - dot(rv, N) * N;
        float rl = length(rt);
        if (rl > 0.001)
        {
            tilt += rt / rl * (eff * 4.0 * s * (1.0 - s * s) / r);
        }
    }
}
Normal = normalize(N - tilt);
return offset;
""" % {"max": MAX_IMPACTS}

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log("SETUP_M1_BODY " + msg)


def get_or_create(name, path, cls, factory):
    full = path + "/" + name
    asset = eal.load_asset(full) if eal.does_asset_exist(full) else None
    if asset is None:
        asset = tools.create_asset(name, path, cls, factory)
        if asset is None:
            raise SystemExit("could not create " + full)
        log("created " + full)
    return asset


def clear_function(mf):
    """delete_all_material_expressions_in_function skips every other node (delete while iterating); finish the job."""
    mel.delete_all_material_expressions_in_function(mf)
    for e in list(mel.get_material_function_expressions(mf)):
        mel.delete_material_expression_in_function(mf, e)
    left = mel.get_num_material_expressions_in_function(mf)
    if left:
        raise SystemExit("%d expressions survived clearing %s" % (left, mf.get_name()))


def fresh_material(name):
    full = MAT + "/" + name
    if eal.does_asset_exist(full):
        m = eal.load_asset(full)
        mel.delete_all_material_expressions(m)
        log("rebuilding " + full)
    else:
        m = tools.create_asset(name, MAT, unreal.Material, unreal.MaterialFactoryNew())
        if m is None:
            raise SystemExit("could not create " + full)
        log("created " + full)
    return m


def connect(src, out_name, dst, in_name):
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    for alt in names:
        if alt != in_name and mel.connect_material_expressions(src, out_name, dst, alt):
            log("connected %s -> %s.%r (asked for %r)" % (src.get_name(), dst.get_name(), alt, in_name))
            return
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


def compile_or_die(material):
    errors = [str(e) for e in mel.recompile_material(material)]
    eal.save_loaded_asset(material)
    if errors:
        for error in errors:
            unreal.log_error("SETUP_M1_BODY compile error in %s: %s" % (material.get_name(), error))
        raise SystemExit(material.get_name() + " failed to compile")


def scalar(material, name, value, x, y):
    e = mel.create_material_expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", value)
    return e


def vector(material, name, colour, x, y):
    e = mel.create_material_expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", unreal.LinearColor(*colour))
    return e


def node(material, cls, x, y):
    return mel.create_material_expression(material, cls, x, y)


def texture_param(material, name, texture, sampler, x, y):
    e = node(material, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("texture", texture)
    e.set_editor_property("sampler_type", sampler)
    return e


def channels(material, src, out_name, keep, x, y):
    e = node(material, unreal.MaterialExpressionComponentMask, x, y)
    for c in "rgba":
        e.set_editor_property(c, c in keep)
    connect(src, out_name, e, "")
    return e


def load_paint_defaults():
    """{parameter: texture} for PAINT_DEFAULTS, checked before anything is rebuilt."""
    found = {}
    for param, path, compression in PAINT_DEFAULTS:
        tex = unreal.load_object(None, path + "." + path.rsplit("/", 1)[1])
        if tex is None:
            raise SystemExit("missing " + path + " (the default of " + param + ")")
        got = tex.get_editor_property("compression_settings").name
        if got != compression:
            raise SystemExit("%s is %s, %s needs %s" % (path, got, param, compression))
        found[param] = tex
    return found


def painted_normal_strength():
    """M_GT_Painted's NormalStrength, read from setup_look_l1.py so the car's panels and the props share one number."""
    import os
    import re
    path = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Art", "Unreal", "setup_look_l1.py")
    with open(path, encoding="utf-8") as f:
        m = re.search(r"^NORMAL_STRENGTH\s*=\s*([0-9.]+)", f.read(), re.M)
    if not m:
        raise SystemExit("no NORMAL_STRENGTH line in " + path)
    return float(m.group(1))


def load_mud_textures():
    """MR2: {pin: (texture, sampler)} for the bog arrays and the splatter, checked before anything is rebuilt."""
    found = {}
    for pin, name, sampler in BOG_ARRAYS:
        tex = eal.load_asset(BOG + "/" + name) if eal.does_asset_exist(BOG + "/" + name) else None
        if tex is None:
            raise SystemExit("missing %s/%s (Art/import_mud_variants.ps1)" % (BOG, name))
        found[pin] = (tex, getattr(unreal.MaterialSamplerType, sampler))
    tex = eal.load_asset(SPLATTER) if eal.does_asset_exist(SPLATTER) else None
    if tex is None:
        raise SystemExit("missing " + SPLATTER + " (Art/setup_mud_carry.ps1)")
    found["Splatter"] = (tex, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    return found


def texture_object(material, name, texture, sampler, x, y):
    e = node(material, unreal.MaterialExpressionTextureObjectParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("texture", texture)
    e.set_editor_property("sampler_type", sampler)
    e.set_editor_property("sampler_source", unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    return e


def mpc_scalar(material, name, x, y):
    """MRP: an MPC_TrackPaint scalar (MudPBR, written by UGTTrackPaintSubsystem from gt.Mud.PBR)."""
    e = node(material, unreal.MaterialExpressionCollectionParameter, x, y)
    mpc = eal.load_asset(MPC_TRACK) if eal.does_asset_exist(MPC_TRACK) else None
    if mpc is None:
        raise SystemExit("missing " + MPC_TRACK + " (Art/setup_m1_trackpaint.bat)")
    e.set_editor_property("collection", mpc)
    e.set_editor_property("parameter_name", name)
    return e


def vector4(material, name, value, x, y):
    """MR2: a vector parameter as a float4 (its default output is RGB only): RGB appended with A."""
    param = vector(material, name, value, x, y)
    joined = node(material, unreal.MaterialExpressionAppendVector, x + 200, y)
    connect(param, "", joined, "A")
    connect(param, "A", joined, "B")
    return joined


def custom_node(material, desc, code, inputs, outputs, kind, x, y):
    e = node(material, unreal.MaterialExpressionCustom, x, y)
    e.set_editor_property("description", desc)
    e.set_editor_property("output_type", kind)
    slots = []
    for name in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        slots.append(ci)
    e.set_editor_property("inputs", slots)
    outs = []
    for name, out_kind in outputs:
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", name)
        co.set_editor_property("output_type", out_kind)
        outs.append(co)
    e.set_editor_property("additional_outputs", outs)
    e.set_editor_property("code", code)
    return e


paint_defaults = load_paint_defaults()
paint_strength = painted_normal_strength()
mud_textures = load_mud_textures()
log("painted path defaults: %s; NormalStrength %.2f (setup_look_l1.py's)"
    % (", ".join("%s=%s" % (p, t.get_name()) for p, t in paint_defaults.items()), paint_strength))


# ---- default impact texture (a float render target: SRGB off, so the LinearColor sampler compiles)
rt = get_or_create("RT_ImpactsDefault", TERRAIN, unreal.TextureRenderTarget2D, unreal.TextureRenderTargetFactoryNew())
rt.set_editor_property("render_target_format", unreal.TextureRenderTargetFormat.RTF_RGBA32F)
rt.set_editor_property("size_x", MAX_IMPACTS)
rt.set_editor_property("size_y", 2)
rt.set_editor_property("clear_color", unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
rt.set_editor_property("srgb", False)
eal.save_loaded_asset(rt)

# ---- MF_Dents ---------------------------------------------------------------------------------
mf_full = MAT + "/MF_Dents"
if eal.does_asset_exist(mf_full):
    mf = eal.load_asset(mf_full)
    clear_function(mf)
    log("rebuilding " + mf_full)
else:
    mf = tools.create_asset("MF_Dents", MAT, unreal.MaterialFunction, unreal.MaterialFunctionFactoryNew())
    if mf is None:
        raise SystemExit("could not create " + mf_full)
    log("created " + mf_full)
mf.set_editor_property("description", "Procedural dents from the car's impact texture: DentOffsetWS (WPO), DentNormalTS (Normal).")


def fx(cls, x, y):
    return mel.create_material_expression_in_function(mf, cls, x, y)


wpos = fx(unreal.MaterialExpressionWorldPosition, -1100, -100)
to_local = fx(unreal.MaterialExpressionTransformPosition, -900, -100)
to_local.set_editor_property("transform_source_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
to_local.set_editor_property("transform_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
vnormal = fx(unreal.MaterialExpressionVertexNormalWS, -1100, 50)
normal_local = fx(unreal.MaterialExpressionTransform, -900, 50)
normal_local.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
normal_local.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
tex = fx(unreal.MaterialExpressionTextureObjectParameter, -900, 200)
tex.set_editor_property("parameter_name", "ImpactTex")
tex.set_editor_property("texture", rt)
tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
count = fx(unreal.MaterialExpressionScalarParameter, -900, 350)
count.set_editor_property("parameter_name", "ImpactCount")
count.set_editor_property("default_value", 0.0)
strength = fx(unreal.MaterialExpressionScalarParameter, -900, 450)
strength.set_editor_property("parameter_name", "DentStrength")
strength.set_editor_property("default_value", 1.0)

custom = fx(unreal.MaterialExpressionCustom, -550, 100)
custom.set_editor_property("description", "Dents")
custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
inputs = []
for name in ("LocalPos", "LocalNormal", "Tex", "Count", "Strength"):
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", name)
    inputs.append(ci)
custom.set_editor_property("inputs", inputs)
normal_out = unreal.CustomOutput()
normal_out.set_editor_property("output_name", "Normal")
normal_out.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
custom.set_editor_property("additional_outputs", [normal_out])
custom.set_editor_property("code", HLSL)

offset_ws = fx(unreal.MaterialExpressionTransform, -250, 50)
offset_ws.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
offset_ws.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
normal_ts = fx(unreal.MaterialExpressionTransform, -250, 200)
normal_ts.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
normal_ts.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
out_offset = fx(unreal.MaterialExpressionFunctionOutput, 0, 50)
out_offset.set_editor_property("output_name", "DentOffsetWS")
out_offset.set_editor_property("sort_priority", 0)
out_normal = fx(unreal.MaterialExpressionFunctionOutput, 0, 200)
out_normal.set_editor_property("output_name", "DentNormalTS")
out_normal.set_editor_property("sort_priority", 1)

connect(wpos, "", to_local, "")
connect(vnormal, "", normal_local, "")
connect(to_local, "", custom, "LocalPos")
connect(normal_local, "", custom, "LocalNormal")
connect(tex, "", custom, "Tex")
connect(count, "", custom, "Count")
connect(strength, "", custom, "Strength")
connect(custom, "", offset_ws, "")
connect(custom, "Normal", normal_ts, "")
connect(offset_ws, "", out_offset, "")
connect(normal_ts, "", out_normal, "")
mel.update_material_function(mf)
eal.save_loaded_asset(mf)
log("function MF_Dents: %d expressions" % mel.get_num_material_expressions_in_function(mf))

# ---- M_GT_Vehicle -----------------------------------------------------------------------------
veh = fresh_material("M_GT_Vehicle")
base = vector(veh, "BaseColor", (0.55, 0.47, 0.30, 1.0), -600, -200)
rough = scalar(veh, "Roughness", 0.4, -600, 0)
metal = scalar(veh, "Metallic", 0.0, -600, 120)
dents = mel.create_material_expression(veh, unreal.MaterialExpressionMaterialFunctionCall, -600, 300)
if not dents.set_material_function(mf):
    raise SystemExit("could not set MF_Dents on the function call")
# Grime: dirt from the body state, heaviest at the sills, then MF_Weather for wet and snow.
weather_full = MAT + "/MF_Weather"
if not eal.does_asset_exist(weather_full):
    raise SystemExit("missing " + weather_full + " (run Art/setup_m1_weather.bat first)")
weather = eal.load_asset(weather_full)
wpos_v = mel.create_material_expression(veh, unreal.MaterialExpressionWorldPosition, -1100, 500)
local_v = mel.create_material_expression(veh, unreal.MaterialExpressionTransformPosition, -950, 500)
local_v.set_editor_property("transform_source_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
local_v.set_editor_property("transform_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
vnormal_v = mel.create_material_expression(veh, unreal.MaterialExpressionVertexNormalWS, -1100, 640)
normal_v = mel.create_material_expression(veh, unreal.MaterialExpressionTransform, -950, 640)
normal_v.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
normal_v.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
dirt_colour = vector(veh, "DirtColour", (0.22, 0.17, 0.11, 1.0), -800, 600)
dirt = scalar(veh, "Dirt", 0.0, -800, 720)
dirt_bottom = scalar(veh, "DirtBottomZ", 35.0, -800, 820)
dirt_height = scalar(veh, "DirtHeight", 90.0, -800, 920)
grime = custom_node(veh, "Grime (MR2: the muddy vehicle behind CarMud)", GRIME_HLSL, GRIME_INPUTS,
                    (("DirtMask", unreal.CustomMaterialOutputType.CMOT_FLOAT1), ("MudNrm", unreal.CustomMaterialOutputType.CMOT_FLOAT3),
                     ("NrmMask", unreal.CustomMaterialOutputType.CMOT_FLOAT1), ("MudAO", unreal.CustomMaterialOutputType.CMOT_FLOAT1)),
                    unreal.CustomMaterialOutputType.CMOT_FLOAT4, -500, 550)
connect(mpc_scalar(veh, "MudPBR", -800, 400), "", grime, "PBR")   # MRP: gt.Mud.PBR
mud_y = 1000
for pname, value in MUD_SCALARS:
    connect(scalar(veh, pname, value, -800, mud_y), "", grime, pname)
    mud_y += 90
for pname, value in MUD_VECTORS:
    connect(vector4(veh, pname, value, -1000, mud_y), "", grime, pname)
    mud_y += 110
for pin, (texture, sampler) in mud_textures.items():
    connect(texture_object(veh, "Mud" + pin, texture, sampler, -800, mud_y), "", grime, pin)
    mud_y += 150
grime_rgb = mel.create_material_expression(veh, unreal.MaterialExpressionComponentMask, -300, 500)
grime_rgb.set_editor_property("r", True)
grime_rgb.set_editor_property("g", True)
grime_rgb.set_editor_property("b", True)
grime_rgb.set_editor_property("a", False)
grime_a = mel.create_material_expression(veh, unreal.MaterialExpressionComponentMask, -300, 600)
grime_a.set_editor_property("r", False)
grime_a.set_editor_property("g", False)
grime_a.set_editor_property("b", False)
grime_a.set_editor_property("a", True)
wetness = scalar(veh, "Wetness", 0.0, -300, 720)
snow = scalar(veh, "Snow", 0.0, -300, 820)
wcall = mel.create_material_expression(veh, unreal.MaterialExpressionMaterialFunctionCall, -100, 600)
if not wcall.set_material_function(weather):
    raise SystemExit("could not set MF_Weather on the function call")
# Look L1 follow-up 3: the painted path. M_GT_Painted's colour (setup_look_l1.build_master): lerp(PaintAlbedo, white,
# PaintMask.R x WearLighten) x (1 - PaintMask.G x GrimeDarken), roughness PaintMask.B; each chosen over today's input by
# lerp(today, painted, UsePaint), so UsePaint 0 hands the Grime node exactly today's BaseColor and Roughness.
use_paint = scalar(veh, "UsePaint", 0.0, -1300, -650)
p_albedo = texture_param(veh, "PaintAlbedo", paint_defaults["PaintAlbedo"], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -1900, -900)
p_mask = texture_param(veh, "PaintMask", paint_defaults["PaintMask"], unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, -1900, -550)
wear_lighten = scalar(veh, "WearLighten", 0.0, -1600, -450)
grime_darken = scalar(veh, "GrimeDarken", 0.0, -1600, -350)
p_white = node(veh, unreal.MaterialExpressionConstant3Vector, -1500, -800)
p_white.set_editor_property("constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
p_wear = node(veh, unreal.MaterialExpressionMultiply, -1400, -500)
connect(p_mask, "R", p_wear, "A")
connect(wear_lighten, "", p_wear, "B")
p_lit = node(veh, unreal.MaterialExpressionLinearInterpolate, -1250, -850)
connect(p_albedo, "RGB", p_lit, "A")
connect(p_white, "", p_lit, "B")
connect(p_wear, "", p_lit, "Alpha")
p_grime = node(veh, unreal.MaterialExpressionMultiply, -1400, -400)
connect(p_mask, "G", p_grime, "A")
connect(grime_darken, "", p_grime, "B")
p_keep = node(veh, unreal.MaterialExpressionOneMinus, -1250, -400)
connect(p_grime, "", p_keep, "")
p_colour = node(veh, unreal.MaterialExpressionMultiply, -1100, -700)
connect(p_lit, "", p_colour, "A")
connect(p_keep, "", p_colour, "B")
base_in = node(veh, unreal.MaterialExpressionLinearInterpolate, -850, -300)
connect(base, "", base_in, "A")
connect(p_colour, "", base_in, "B")
connect(use_paint, "", base_in, "Alpha")
rough_in = node(veh, unreal.MaterialExpressionLinearInterpolate, -850, -50)
connect(rough, "", rough_in, "A")
connect(p_mask, "B", rough_in, "B")
connect(use_paint, "", rough_in, "Alpha")
connect(base_in, "", grime, "BaseColor")
connect(rough_in, "", grime, "Roughness")
connect(dirt_colour, "", grime, "DirtColour")
connect(dirt, "", grime, "Dirt")
connect(wpos_v, "", local_v, "")
connect(local_v, "", grime, "LocalPos")
connect(vnormal_v, "", normal_v, "")
connect(normal_v, "", grime, "LocalNormal")
connect(dirt_bottom, "", grime, "DirtBottomZ")
connect(dirt_height, "", grime, "DirtHeight")
connect(grime, "", grime_rgb, "")
connect(grime, "", grime_a, "")
connect(grime_rgb, "", wcall, "BaseColor")
connect(grime_a, "", wcall, "Roughness")
connect(grime, "DirtMask", wcall, "Porosity")
connect(wetness, "", wcall, "LocalWetness")
connect(snow, "", wcall, "LocalSnow")
if not mel.connect_material_property(wcall, "BaseColor", unreal.MaterialProperty.MP_BASE_COLOR):
    raise SystemExit("could not connect the weathered BaseColor")
# MRP: mud's roughness floor after the weather (PBR), and the mud's AO on the Ambient Occlusion pin (1 without mud or PBR).
vfloor = custom_node(veh, "Mud roughness floor (MRP)", FLOOR_HLSL, ("R", "Mask", "PBR"), (), unreal.CustomMaterialOutputType.CMOT_FLOAT1, 100, 700)
connect(wcall, "Roughness", vfloor, "R")
connect(grime, "DirtMask", vfloor, "Mask")
connect(mpc_scalar(veh, "MudPBR", -100, 820), "", vfloor, "PBR")
if not mel.connect_material_property(vfloor, "", unreal.MaterialProperty.MP_ROUGHNESS):
    raise SystemExit("could not connect the weathered Roughness")
if not mel.connect_material_property(grime, "MudAO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION):
    raise SystemExit("could not connect the mud's AO")
mel.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
# Clear coat: the paint's coat, thinned where dirt covers it. The pins are hidden from Python.
veh.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLEAR_COAT)
coat = scalar(veh, "ClearCoat", 0.8, -300, 950)
coat_rough = scalar(veh, "ClearCoatRoughness", 0.1, -300, 1050)
clean = mel.create_material_expression(veh, unreal.MaterialExpressionOneMinus, -100, 900)
connect(grime, "DirtMask", clean, "")
coat_mul = mel.create_material_expression(veh, unreal.MaterialExpressionMultiply, 50, 950)
connect(coat, "", coat_mul, "A")
connect(clean, "", coat_mul, "B")
lib = unreal.GTVehicleSetupLibrary
if not lib.connect_material_custom_data(coat_mul, "", 0):
    raise SystemExit("could not connect ClearCoat")
if not lib.connect_material_custom_data(coat_rough, "", 1):
    raise SystemExit("could not connect ClearCoatRoughness")
# Look L1 follow-up 3: the painted-dab normal, M_GT_Painted's normalize(lerp((0,0,1), PaintNormal, NormalStrength)),
# with the dents' normal blended over it (whiteout: normalize(dent.xy + paint.xy, dent.z x paint.z)); the Normal pin
# takes lerp(DentNormalTS, that blend, UsePaint), so UsePaint 0 is today's DentNormalTS. With the flat default (no _N)
# the blend is the dent normal itself.
p_normal = texture_param(veh, "PaintNormal", paint_defaults["PaintNormal"], unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, -1900, 1300)
p_strength = scalar(veh, "NormalStrength", paint_strength, -1600, 1500)
p_flat = node(veh, unreal.MaterialExpressionConstant3Vector, -1600, 1200)
p_flat.set_editor_property("constant", unreal.LinearColor(0.0, 0.0, 1.0, 1.0))
p_towards = node(veh, unreal.MaterialExpressionLinearInterpolate, -1400, 1300)
connect(p_flat, "", p_towards, "A")
connect(p_normal, "RGB", p_towards, "B")
connect(p_strength, "", p_towards, "Alpha")
p_unit = node(veh, unreal.MaterialExpressionNormalize, -1250, 1300)
connect(p_towards, "", p_unit, "VectorInput")
dent_xy = channels(veh, dents, "DentNormalTS", "rg", -1100, 1150)
dent_z = channels(veh, dents, "DentNormalTS", "b", -1100, 1250)
paint_xy = channels(veh, p_unit, "", "rg", -1100, 1350)
paint_z = channels(veh, p_unit, "", "b", -1100, 1450)
n_xy = node(veh, unreal.MaterialExpressionAdd, -950, 1200)
connect(dent_xy, "", n_xy, "A")
connect(paint_xy, "", n_xy, "B")
n_z = node(veh, unreal.MaterialExpressionMultiply, -950, 1400)
connect(dent_z, "", n_z, "A")
connect(paint_z, "", n_z, "B")
n_joined = node(veh, unreal.MaterialExpressionAppendVector, -800, 1300)
connect(n_xy, "", n_joined, "A")
connect(n_z, "", n_joined, "B")
n_blend = node(veh, unreal.MaterialExpressionNormalize, -650, 1300)
connect(n_joined, "", n_blend, "VectorInput")
normal_in = node(veh, unreal.MaterialExpressionLinearInterpolate, -450, 1200)
connect(dents, "DentNormalTS", normal_in, "A")
connect(n_blend, "", normal_in, "B")
connect(use_paint, "", normal_in, "Alpha")
# MR2: the mud's own normal (the bog's, car space) over the panel's where the coat lies (NrmMask 0 with CarMud 0).
mud_ts = node(veh, unreal.MaterialExpressionTransform, -300, 1350)
mud_ts.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
mud_ts.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
connect(grime, "MudNrm", mud_ts, "")
normal_mud = node(veh, unreal.MaterialExpressionLinearInterpolate, -150, 1250)
connect(normal_in, "", normal_mud, "A")
connect(mud_ts, "", normal_mud, "B")
connect(grime, "NrmMask", normal_mud, "Alpha")
normal_out = node(veh, unreal.MaterialExpressionNormalize, 0, 1250)
connect(normal_mud, "", normal_out, "VectorInput")
if not mel.connect_material_property(normal_out, "", unreal.MaterialProperty.MP_NORMAL):
    raise SystemExit("could not connect the Normal pin (DentNormalTS / painted blend / mud)")
if not mel.connect_material_property(dents, "DentOffsetWS", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET):
    raise SystemExit("could not connect DentOffsetWS")
compile_or_die(veh)
log("M_GT_Vehicle compiled (painted path behind UsePaint 0: PaintAlbedo, PaintMask, PaintNormal, WearLighten 0, "
    "GrimeDarken 0, NormalStrength %.2f)" % paint_strength)
log("M_GT_Vehicle MR2 mud: CarMud 1, %s; %s; %s" % (", ".join("%s %g" % kv for kv in MUD_SCALARS[1:]), ", ".join(k for k, _v in MUD_VECTORS),
                                                     ", ".join(t.get_name() for t, _s in mud_textures.values())))

# ---- M_GT_Tyre (MR2) --------------------------------------------------------------------------------------------------
tyre = fresh_material("M_GT_Tyre")
mel.set_base_material_usage(tyre, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
tyre_custom = custom_node(tyre, "Tyre: rubber, rim, caked mud (MR2)", TYRE_HLSL, TYRE_INPUTS,
                          (("Rough", unreal.CustomMaterialOutputType.CMOT_FLOAT1), ("Metal", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
                           ("MudMask", unreal.CustomMaterialOutputType.CMOT_FLOAT1), ("MudAO", unreal.CustomMaterialOutputType.CMOT_FLOAT1)),
                          unreal.CustomMaterialOutputType.CMOT_FLOAT3, -400, 0)
connect(mpc_scalar(tyre, "MudPBR", -900, -500), "", tyre_custom, "PBR")   # MRP: gt.Mud.PBR
# The rest pose is a vertex-shader value: each goes to the pixel shader through a vertex interpolator.
for expr_cls, pin, iy in ((unreal.MaterialExpressionPreSkinnedPosition, "Pos", -400), (unreal.MaterialExpressionPreSkinnedNormal, "Nrm", -300)):
    interp = node(tyre, unreal.MaterialExpressionVertexInterpolator, -700, iy)
    connect(node(tyre, expr_cls, -900, iy), "", interp, "")
    connect(interp, "", tyre_custom, pin)
ty = -200
for pname, value in TYRE_SCALARS:
    connect(scalar(tyre, pname, value, -900, ty), "", tyre_custom, pname)
    ty += 90
for pname, value in TYRE_VECTORS:
    connect(vector4(tyre, pname, value, -1100, ty), "", tyre_custom, pname)
    ty += 110
for pin in ("BogC", "BogORH", "Splatter"):
    texture, sampler = mud_textures[pin]
    connect(texture_object(tyre, "Mud" + pin, texture, sampler, -900, ty), "", tyre_custom, pin)
    ty += 150
twet = scalar(tyre, "Wetness", 0.0, -100, 300)
tsnow = scalar(tyre, "Snow", 0.0, -100, 400)
tcall = node(tyre, unreal.MaterialExpressionMaterialFunctionCall, 100, 0)
if not tcall.set_material_function(weather):
    raise SystemExit("could not set MF_Weather on M_GT_Tyre")
tporo = scalar(tyre, "Porosity", 0.3, -100, 200)
connect(tyre_custom, "", tcall, "BaseColor")
connect(tyre_custom, "Rough", tcall, "Roughness")
connect(tporo, "", tcall, "Porosity")
connect(twet, "", tcall, "LocalWetness")
connect(tsnow, "", tcall, "LocalSnow")
if not mel.connect_material_property(tcall, "BaseColor", unreal.MaterialProperty.MP_BASE_COLOR):
    raise SystemExit("could not connect the tyre's BaseColor")
tfloor = custom_node(tyre, "Mud roughness floor (MRP)", FLOOR_HLSL, ("R", "Mask", "PBR"), (), unreal.CustomMaterialOutputType.CMOT_FLOAT1, 300, 100)
connect(tcall, "Roughness", tfloor, "R")
connect(tyre_custom, "MudMask", tfloor, "Mask")
connect(mpc_scalar(tyre, "MudPBR", 100, 300), "", tfloor, "PBR")
if not mel.connect_material_property(tfloor, "", unreal.MaterialProperty.MP_ROUGHNESS):
    raise SystemExit("could not connect the tyre's Roughness")
if not mel.connect_material_property(tyre_custom, "MudAO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION):
    raise SystemExit("could not connect the tyre's AO")
if not mel.connect_material_property(tyre_custom, "Metal", unreal.MaterialProperty.MP_METALLIC):
    raise SystemExit("could not connect the tyre's Metallic")
compile_or_die(tyre)
log("M_GT_Tyre compiled (skeletal mesh usage; TyreCoat FL FR RL RR, WheelGeom, RimShare 0.62, the bog slice and the splatter)")

# ---- M_GT_Glass -------------------------------------------------------------------------------
glass = fresh_material("M_GT_Glass")
glass.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
glass.set_editor_property("two_sided", True)
gbase = vector(glass, "BaseColor", (0.55, 0.65, 0.70, 1.0), -700, -200)
white = mel.create_material_expression(glass, unreal.MaterialExpressionConstant3Vector, -700, -50)
white.set_editor_property("constant", unreal.LinearColor(0.85, 0.85, 0.85, 1.0))
crack = scalar(glass, "Crack", 0.0, -900, 100)
tint = mel.create_material_expression(glass, unreal.MaterialExpressionLinearInterpolate, -450, -150)
connect(gbase, "", tint, "A")
connect(white, "", tint, "B")
connect(crack, "", tint, "Alpha")
gopacity = scalar(glass, "Opacity", 0.3, -700, 250)
crack_opacity = mel.create_material_expression(glass, unreal.MaterialExpressionMultiply, -700, 350)
half = mel.create_material_expression(glass, unreal.MaterialExpressionConstant, -900, 400)
half.set_editor_property("r", 0.5)
connect(crack, "", crack_opacity, "A")
connect(half, "", crack_opacity, "B")
opacity_sum = mel.create_material_expression(glass, unreal.MaterialExpressionAdd, -450, 250)
connect(gopacity, "", opacity_sum, "A")
connect(crack_opacity, "", opacity_sum, "B")
grough = scalar(glass, "Roughness", 0.05, -700, 50)
# Dirt (mud throw-up): CarMud 0 browns and thickens the glass as before; MR2 lays it as splats (from throw hits only).
gdirt = scalar(glass, "Dirt", 0.0, -900, 550)
gsplat = custom_node(glass, "Glass dirt (MR2: splats)", GLASS_HLSL, ("Tint", "BaseOpacity", "Dirt", "CarMud", "MudWet", "LocalPos", "SizeX", "SizeY", "Splatter",
                                                                     "BaseRough", "PBR"),
                     (("Opacity", unreal.CustomMaterialOutputType.CMOT_FLOAT1), ("Rough", unreal.CustomMaterialOutputType.CMOT_FLOAT1)),
                     unreal.CustomMaterialOutputType.CMOT_FLOAT3, -250, 0)
connect(grough, "", gsplat, "BaseRough")
connect(mpc_scalar(glass, "MudPBR", -900, 1250), "", gsplat, "PBR")   # MRP: gt.Mud.PBR
connect(tint, "", gsplat, "Tint")
connect(opacity_sum, "", gsplat, "BaseOpacity")
connect(gdirt, "", gsplat, "Dirt")
connect(scalar(glass, "CarMud", 1.0, -900, 650), "", gsplat, "CarMud")
connect(scalar(glass, "MudWet", 0.0, -900, 750), "", gsplat, "MudWet")
connect(scalar(glass, "GlassSizeX", 58.0, -900, 850), "", gsplat, "SizeX")
connect(scalar(glass, "GlassSizeY", 150.0, -900, 950), "", gsplat, "SizeY")
gpos = node(glass, unreal.MaterialExpressionWorldPosition, -1200, 1050)
glocal = node(glass, unreal.MaterialExpressionTransformPosition, -1050, 1050)
glocal.set_editor_property("transform_source_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
glocal.set_editor_property("transform_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
connect(gpos, "", glocal, "")
connect(glocal, "", gsplat, "LocalPos")
splatter_tex, splatter_sampler = mud_textures["Splatter"]
connect(texture_object(glass, "MudSplatter", splatter_tex, splatter_sampler, -900, 1150), "", gsplat, "Splatter")
mel.connect_material_property(gsplat, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(gsplat, "Opacity", unreal.MaterialProperty.MP_OPACITY)
mel.connect_material_property(gsplat, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)   # MRP: the splats' roughness (BaseRough elsewhere)
# The spray component draws dust and snow puffs as instanced spheres with this material.
mel.set_base_material_usage(glass, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
compile_or_die(glass)
log("M_GT_Glass compiled")
log("DONE")
