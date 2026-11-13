"""Approved mud-03 appearance on the existing field and landscape shaders.

No changes to the field sampling, WPO, holes, collision, water tables or traction.
Both ground surfaces use the same sampling block so an untouched patch matches.

Living mud LM5b (docs/LIVING_MUD_PLAN.md LM5b, docs/MUD_VARIANTS.md): the mud is one layer. M_GT_Mud wears its patch's
variant slice (MudVariant, AGTMudPatch sets it) of the four bog texture arrays (TA_MS_Bog{Color,Normal,Rough,Height},
Art/Unreal/import_mud_variants.py) everywhere in the patch, ruts included: a rut differs only by its shape, the fresh sheen
(FreshWet), the weather's wetness and the rut water. The arrays are sampled tri-planar; the top face at two tilings that share
no repeat (BogTileCm 300 square, BogTile2Cm 430 turned BogTile2Deg 37), height-blended by a world noise (BogMixCm); the far
gloss fade (FarGlossFade, a static switch, on) lifts the roughness toward FarGlossRough 0.65 from 6 to 12 m from the camera.
The landscape keeps the clay outside the mud; round each patch's box (MPC_TrackPaint Patch0..3) it takes the same variant
slice (PatchVariant0..3) over ApronCm, so the patch's edge does not show. The clods (M_GT_Clod) take the slice through their
patch's instance (MudVariant). The clay bakes (TEXTURES) stay for the landscape outside the aprons.

MudRunner MRP (docs/MUDRUNNER_LESSONS_PLAN.md MRP, docs/MUD_VARIANTS.md "Physically based mud"): the owner's "far too glossy, we
need pbr and occlusion mapping for detail. ensure it is optimised".
- The arrays are Color + Normal + ORH (TA_MS_BogORH: R horizon AO, G the roughness remapped into the PBR bands, B the height;
  Art/bake_mud_orh.py, Art/Unreal/import_mud_variants.py): three samples per projection, not four.
- gt.Mud.PBR (MPC_TrackPaint MudPBR, UGTTrackPaintSubsystem): 1 the physically based values - the ORH's roughness (dry lump tops
  0.89-0.95, the slurry 0.46-0.61), wet (the weather, the fresh sheen) toward the saturated surface's MudWetRoughLo..Hi (0.45-0.65),
  never under 0.4; the AO on the Ambient Occlusion output and a cavity tint of at most MudCavityTint (0.15); the far gloss fade
  only behind FarGlossFade (a static switch, now off). 0 the look before MRP (the bake's own roughness: the remap inverted).
- Parallax occlusion on M_GT_Mud (POM_HLSL, gt.Mud.POM 0/1/2 and gt.Mud.POMShadow, MPC MudPOM / MudPOMShadow): marched over the
  ORH height in a frame from the field's normal, MudPomDepthCm 3, SampleGrad with the un-slid derivatives and a linear refine; the
  hit's slide moves every lookup on both tilings and the walls; faded out MudPomNearM 6 to MudPomFarM 14 m behind a dynamic branch;
  8 steps (POM 1) or 8-16 by the view angle (POM 2); none under the rut water (MudWaterTableCm, AGTMudPatch); a 4-step sun
  self-shadow within MudPomShadowM 4 m (ground relief GR1c: scaled down on the field's slopes over MudPomShadowSlopeLo 15 deg, to
  MudPomShadowSlopeMin 0.3 at MudPomShadowSlopeHi 30 deg - the dark streaks on the old tracks' walls came from it).
- M_GT_MudWater (MR3's wrapper): water's F0 0.02 (Specular 0.25), settled 0.15 with a faint ripple normal, churned 0.5, the froth
  0.6 without its glint, no grazing-angle gloss or Fresnel opacity; gt.Mud.PBR 0 the MR3b water.
MudRunner MR4 (docs/MUDRUNNER_LESSONS_PLAN.md MR4): M_GT_Mud reads the patch's softness S from MudLayer's G (SOFT_HLSL): soft spots
blend toward the Deep slice, wetter, with a ragged edge from the base slice's parallax height; gt.Mud.SoftSpots 0 uploads G as 0.
"""
import ast
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
TEXTURES={'ClayC':'T_MS_ClayColor','ClayN':'T_MS_ClayNormal','WorkC':'T_MS_WorkedColor','WorkN':'T_MS_WorkedNormal'}
# LM1, the living field (docs/LIVING_MUD_PLAN.md): the clay drags with the field's offset (UV only, the vertices and
# SlideScale unchanged) and mud that just moved looks wet (MudTread B is the field's Fresh). Proposed starting points.
# LM5b: FreshWet 0.6 -> 0.3, the slight sheen the owner asked for on the ruts ("only a little wetter"), drying as Fresh fades.
# MW1 item 2c: FreshWet 0.3 -> 0.12 (the fresh sheen). Item 2a asked SlideUV 1.0 -> 0.35 unless the debug showed the slide is not
# the swirl source: it did not (the owner's frame and a fresh Deep bank, SlideUV 0 against the same frame: 1.05 and 0.54 of 255 mean,
# the capture floor 0.49-0.63; gt.Mud.POM 0: 9.9 and 9.6), so SlideUV stays 1.0 (docs/MUD_WATER_SURFACE_PLAN.md MW1 Done note).
LM1_SCALARS={'SlideUV':1.0,'FreshWet':0.12}
# Mud and water MW1 (docs/MUD_WATER_SURFACE_PLAN.md item 2, the owner's "mud and water are reading way too smooth"): M_GT_Mud's
# crisp deformation detail (item 2b: the variant slice's normal and ORH AO at DeformTileMul x the tiling, turned DeformTurnDeg, in
# the field-normal frame, never sliding; its strength DeformStrength x the max of the moved-mud mask - the tracks or the Fresh
# history - and smoothstep(DeformSlopeLo, DeformSlopeHi, the field's slope); gt.Mud.DeformDetail, MPC_TrackPaint MudDeformDetail)
# and the broken highlights (item 2d: on wet mud outside the rut water the roughness +- RoughNoiseAmp of two value-noise octaves
# at RoughNoiseCm1 and RoughNoiseCm2, and the wet floor WetRoughFloor; proposed numbers, the owner names them).
# MRD1 item 2: DeformStrength 0.8 -> 1.0.
MW1_MUD_SCALARS={'DeformTileMul':2.6,'DeformTurnDeg':29.0,'DeformStrength':1.0,'DeformSlopeLo':12.0,'DeformSlopeHi':25.0,
                 'RoughNoiseAmp':0.08,'RoughNoiseCm1':8.0,'RoughNoiseCm2':25.0,'WetRoughFloor':0.62,
                 # MW1b (the main session's look at MW1: the walls still smeared, the mud glaring white toward a low sun, Deep's
                 # craters): no parallax on deformed mud (PomFlatLo..Hi deg of the field's slope and the moved-mud mask take its
                 # depth to 0); the mud matte - dry MudDryRoughLo..Hi 0.8-0.95, wet MudWetBandLo..Hi 0.62-0.8, the floor
                 # WetRoughFloor 0.62 (was 0.5) - and specular occlusion from the baked AO (MudSpecOcclusion: Specular 0.5 x AO^2);
                 # Deep's slice softened: its normal x DeepNormalScale, its AO's strength x DeepAOScale, its parallax x DeepPomScale.
                 'PomFlatLo':10.0,'PomFlatHi':22.0,'MudDryRoughLo':0.8,'MudDryRoughHi':0.95,'MudWetBandLo':0.62,'MudWetBandHi':0.8,
                 'MudSpecOcclusion':1.0,'DeepNormalScale':0.5,'DeepAOScale':0.5,'DeepPomScale':0.5}
# MW1: the switches' MPC_TrackPaint scalars (UGTMudWaterSubsystem writes them from gt.Mud.DeformDetail / gt.Mud.WaterMotion).
MW1_MPC={'MudDeformDetail':1.0,'MudWaterMotion':1.0}
# Mud roads MRD1 item 2 (docs/MUD_ROADS_PLAN.md, the owner's five references): M_GT_Mud's wet/dry term - twelve taps of the field
# round the pixel find the nearest standing water within WetNearCm 60 and the local relief; near water (and, at 0.6, in troughs
# deeper than 2..TroughWetCm 12 cm or 1-6 cm under the taps' mean) the colour x WetDarken 0.72 and the roughness WetRoughLo..Hi
# 0.5-0.6 by the ORH band; on crowns (0.5..CrownCm 6 cm over the taps' mean) x DryLighten 1.08 and DryRoughLo..Hi 0.85-0.95;
# between, MW1b's bands (WetDryOn 0: MW1b exactly). The deep walls (the taps' relief over WallAODeepCm 10 +- 2 cm, on slopes over
# DeformSlopeLo..Hi) take the deformation detail's AO at WallAOBoost 1.5 x. The old tread on a mud road's freshest tracks
# (AGTMudPatch::PreChurnBraided: TreadTex G over 1.5) a lug tilt of OldTreadTiltDeg 12 x its strength (0.3-0.8 cm of a 9 cm
# period's 2.5 cm flank), x MPC_TrackPaint MudOldTread (gt.Mud.OldTread). Proposed numbers; the owner names them.
MRD1_MUD_SCALARS={'WetDryOn':1.0,'WetNearCm':60.0,'TroughWetCm':12.0,'CrownCm':6.0,'WetDarken':0.72,'WetRoughLo':0.5,'WetRoughHi':0.6,
                  'DryLighten':1.08,'DryRoughLo':0.85,'DryRoughHi':0.95,'WallAODeepCm':15.0,'WallAOBoost':1.0,'OldTreadTiltDeg':12.0,
                  'OldTreadPeriodCm':9.0,
                  # MRD1b item 4: the wall AO boost x1.5 -> x1.0, and only past 15 cm (MRD1: 10). Item 3, the silt surface: the bake's tiling
                  # / SiltTileMul and, on the running surface, its lump normal, AO and parallax depth x SiltStrength (AGTMudPatch sets both
                  # from the profile: a mud road's 2 and 0.4; 1 and 1 here, the bog as before).
                  'SiltTileMul':1.0,'SiltStrength':1.0}
MRD1_MPC={'MudOldTread':1.0}
DEST='/Game/GrandTour/ArtTests/MudStyle'
# LM5b: the bog arrays (slice = EGTMudVariant: Standard, Firm, Deep, Stony), their sampler types, the shared wrap sampler.
VARIANTS=['Standard','Firm','Deep','Stony']
# MRP: BogR and BogH became the packed ORH array (R AO, G roughness in the PBR bands, B height; linear BC7).
BOG_ARRAYS={'BogC':'TA_MS_BogColor','BogN':'TA_MS_BogNormal','BogORH':'TA_MS_BogORH'}
BOG_SAMPLERS={'BogC':'SAMPLERTYPE_COLOR','BogN':'SAMPLERTYPE_NORMAL','BogORH':'SAMPLERTYPE_LINEAR_COLOR'}
# MRP follow-up 3: back to the one ORH pack (follow-up 2's split, BogOR + BogHt, cost a sampler and 11 MB for no gain); ORH's B is
# now a soft-rimmed parallax height (Art/bake_mud_orh.py) - the bakes' near-vertical lump rims were what the parallax stretched
# into flank terraces, not the compression (BC7, BC4 and G8 drew the same bands).
BOG_RETIRED=['BogR','BogH','BogOR','BogHt']   # older inputs, removed from the surface nodes (and their LiveMud_ parameters) on a rerun
# The tilings, the mix noise, the height blend's width (of the 0-1 height) and the far gloss fade (A2's candidate, MUD_WET_STUDY).
BOG_SCALARS={'BogTileCm':300.0,'BogTile2Cm':430.0,'BogTile2Deg':37.0,'BogMixCm':260.0,'BogBlendSharp':0.2,
             'FarGlossNearCm':600.0,'FarGlossFarCm':1200.0,'FarGlossRough':0.65}
# MRP: the physically based values, the AO and the parallax (proposed starting points; the owner names them). MudWaterTableCm is
# AGTMudPatch's (the rut water's table, -10000 when none is drawn).
# MRP follow-up: MudPomGrazingMinSteps (the steps' floor at a grazing angle), MudPomRefine (binary halvings), MudPomSteepCap (0 = off).
MRP_SCALARS={'MudPomDepthCm':3.0,'MudPomNearM':6.0,'MudPomFarM':14.0,'MudPomMinSteps':8.0,'MudPomMaxSteps':16.0,'MudPomShadowM':4.0,
             'MudPomGrazingMinSteps':12.0,'MudPomRefine':5.0,'MudPomSteepCap':0.0,
             'MudPomShadowSlopeLo':15.0,'MudPomShadowSlopeHi':30.0,'MudPomShadowSlopeMin':0.3,
             'MudPomShadowStrength':0.45,'MudAOStrength':1.0,'MudCavityTint':0.15,'MudWetRoughLo':0.45,'MudWetRoughHi':0.65,'MudWaterTableCm':-10000.0}
# MRP: the console switches' MPC_TrackPaint scalars (UGTTrackPaintSubsystem writes them from gt.Mud.PBR / POM / POMShadow).
MRP_MPC={'MudPBR':1.0,'MudPOM':2.0,'MudPOMShadow':1.0}
APRON_CM=300.0   # the landscape's apron round a patch's box (L_MudDrive's clay feather, setup_live_mud_drive.py before LM5b)
MPC_PATH='/Game/GrandTour/Terrain/MPC_TrackPaint'
WEATHER_MPC='/Game/GrandTour/Materials/MPC_Weather'   # MW1: the rut water reads its WindDirection

def sampling():
    code='float3 weights=pow(abs(gn),6.0); weights/=max(dot(weights,1.0),0.0001);\nfloat3 clayColor=0; float3 clayDetail=0;\n'
    for axis,coords,weight,normal in [('z','xy','z','float3(d.x,d.y,0)'),('y','xz','y','float3(d.x,0,d.y)'),('x','yz','x','float3(0,d.x,d.y)')]:
        code+='''{
float2 f=frac(PaintPos.COORDS/1200.0);
float2 mirrored=1-abs(f*2-1);float2 uvPaint=float2(mirrored.x,1-mirrored.y);
float3 a=Texture2DSample(ClayC,ClayCSampler,uvPaint).rgb;
float3 b=Texture2DSample(WorkC,WorkCSampler,uvPaint).rgb;
float2 na=UnpackNormalMap(Texture2DSample(ClayN,ClayNSampler,uvPaint)).xy;
float2 nb=UnpackNormalMap(Texture2DSample(WorkN,WorkNSampler,uvPaint)).xy;
float2 d=lerp(na,nb,worked)*float2(f.x<0.5?1:-1,f.y<0.5?1:-1);
clayColor+=weights.WEIGHT*lerp(a,b,worked);
clayDetail+=weights.WEIGHT*NORMAL;
}
'''.replace('COORDS',coords).replace('WEIGHT',weight).replace('NORMAL',normal)
    return code

# ---- LM5b: the bog block -------------------------------------------------------------------------------------------
# Inputs: gn (float3, the surface normal), PaintPos (float3, cm), bogSlice (float, the variant), the BOG_SCALARS. The setup half
# (uvs, their screen derivatives, the mix noise) runs outside any branch so the landscape can skip the samples away from its
# aprons; the samples take explicit gradients. The bakes are true 3 m tiles (no mirror): the uvs are left unwrapped for the
# wrap sampler (a frac would put a mip seam on every tile edge). The normal's axes follow the clay's (float2(u, -v) with the
# tilt added as world (x, y)); the turned tiling's tilt is turned back by the same angle.
BOG_SETUP='''// LM5b: the bog's uvs - the top face at two tilings (A square, B turned), the walls at A's scale.
float bogCos=cos(radians(BogTile2Deg));float bogSin=sin(radians(BogTile2Deg));
float2 bogUA=float2(PaintPos.x,-PaintPos.y)/max(BogTileCm,1.0);
float2 bogTurn=float2(bogCos*PaintPos.x+bogSin*PaintPos.y,-bogSin*PaintPos.x+bogCos*PaintPos.y);
float2 bogUB=float2(bogTurn.x,-bogTurn.y)/max(BogTile2Cm,1.0);
float2 bogUY=float2(PaintPos.x,-PaintPos.z)/max(BogTileCm,1.0);
float2 bogUX=float2(PaintPos.y,-PaintPos.z)/max(BogTileCm,1.0);
float2 bogAx=ddx(bogUA);float2 bogAy=ddy(bogUA);float2 bogBx=ddx(bogUB);float2 bogBy=ddy(bogUB);
float2 bogYx=ddx(bogUY);float2 bogYy=ddy(bogUY);float2 bogXx=ddx(bogUX);float2 bogXy=ddy(bogUX);
float3 bogW=pow(abs(gn),6.0);bogW/=max(dot(bogW,1.0),0.0001);
// The mix between the two tilings: two octaves of world value noise over BogMixCm, sharpened.
float bogMix=0;
{
float2 bmc=PaintPos.xy/max(BogMixCm,1.0);
float2 bmi=floor(bmc);float2 bmf=frac(bmc);bmf=bmf*bmf*(3.0-2.0*bmf);
float b00=frac(sin(dot(bmi,float2(127.1,311.7)))*43758.5453);float b10=frac(sin(dot(bmi+float2(1,0),float2(127.1,311.7)))*43758.5453);
float b01=frac(sin(dot(bmi+float2(0,1),float2(127.1,311.7)))*43758.5453);float b11=frac(sin(dot(bmi+float2(1,1),float2(127.1,311.7)))*43758.5453);
bogMix=0.65*lerp(lerp(b00,b10,bmf.x),lerp(b01,b11,bmf.x),bmf.y);
float2 bmc2=bmc*2.31+float2(17.3,-9.1);
float2 bmj=floor(bmc2);float2 bmg=frac(bmc2);bmg=bmg*bmg*(3.0-2.0*bmg);
float c00=frac(sin(dot(bmj,float2(269.5,183.3)))*43758.5453);float c10=frac(sin(dot(bmj+float2(1,0),float2(269.5,183.3)))*43758.5453);
float c01=frac(sin(dot(bmj+float2(0,1),float2(269.5,183.3)))*43758.5453);float c11=frac(sin(dot(bmj+float2(1,1),float2(269.5,183.3)))*43758.5453);
bogMix+=0.35*lerp(lerp(c00,c10,bmg.x),lerp(c01,c11,bmg.x),bmg.y);
bogMix=smoothstep(0.3,0.7,bogMix);
}
// MRP: the parallax's slide (world cm, POM_HLSL sets it on M_GT_Mud) and its self-shadow; 0 on the landscape's apron.
float3 pomOff=float3(0.0,0.0,0.0);float pomShade=0.0;
'''
BOG_SAMPLE='''{
// MRP: the parallax's slide in each projection's uv (A square, B turned, the walls at A's scale); zero on the landscape.
float2 bogOffA=float2(pomOff.x,-pomOff.y)/max(BogTileCm,1.0);
float2 bogOffB=float2(bogCos*pomOff.x+bogSin*pomOff.y,bogSin*pomOff.x-bogCos*pomOff.y)/max(BogTile2Cm,1.0);
float2 bogOffY=float2(pomOff.x,-pomOff.z)/max(BogTileCm,1.0);
float2 bogOffX=float2(pomOff.y,-pomOff.z)/max(BogTileCm,1.0);
// LM5b: the top face, A and B height-blended (the higher bake wins, the mix noise tilting it), so no average washes out.
// MRP: the height, the roughness and the AO from the one ORH sample per tiling (B, G, R); the derivatives are the un-slid uv's.
float3 bsA=float3(bogUA+bogOffA,bogSlice);float3 bsB=float3(bogUB+bogOffB,bogSlice);
float4 boA=BogORH.SampleGrad(BogORHSampler,bsA,bogAx,bogAy);float4 boB=BogORH.SampleGrad(BogORHSampler,bsB,bogBx,bogBy);
float bt=saturate(((boB.b+bogMix)-(boA.b+1.0-bogMix))/max(BogBlendSharp,0.001)+0.5);
float3 bcZ=lerp(BogC.SampleGrad(BogCSampler,bsA,bogAx,bogAy).rgb,BogC.SampleGrad(BogCSampler,bsB,bogBx,bogBy).rgb,bt);
float2 bnA=UnpackNormalMap(BogN.SampleGrad(BogNSampler,bsA,bogAx,bogAy)).xy;
float2 bnB0=UnpackNormalMap(BogN.SampleGrad(BogNSampler,bsB,bogBx,bogBy)).xy;
float2 bnB=float2(bogCos*bnB0.x-bogSin*bnB0.y,bogSin*bnB0.x+bogCos*bnB0.y);
float2 bnZ=lerp(bnA,bnB,bt);
float2 boZ=lerp(boA.rg,boB.rg,bt);
// The walls: one tiling each.
float3 bsY=float3(bogUY+bogOffY,bogSlice);float3 bsX=float3(bogUX+bogOffX,bogSlice);
float3 bcY=BogC.SampleGrad(BogCSampler,bsY,bogYx,bogYy).rgb;float2 bnY=UnpackNormalMap(BogN.SampleGrad(BogNSampler,bsY,bogYx,bogYy)).xy;float2 boY=BogORH.SampleGrad(BogORHSampler,bsY,bogYx,bogYy).rg;
float3 bcX=BogC.SampleGrad(BogCSampler,bsX,bogXx,bogXy).rgb;float2 bnX=UnpackNormalMap(BogN.SampleGrad(BogNSampler,bsX,bogXx,bogXy)).xy;float2 boX=BogORH.SampleGrad(BogORHSampler,bsX,bogXx,bogXy).rg;
bogColor=bogW.z*bcZ+bogW.y*bcY+bogW.x*bcX;
bogDetail=bogW.z*float3(bnZ.x,bnZ.y,0)+bogW.y*float3(bnY.x,0,bnY.y)+bogW.x*float3(0,bnX.x,bnX.y);
float2 bogOR=bogW.z*boZ+bogW.y*boY+bogW.x*boX;
bogAO=bogOR.x;bogRough=bogOR.y;
}
'''
# MRP item 3 (M_GT_Mud only): parallax occlusion over the ORH height (B, 1 the top), after BOG_SETUP and before BOG_SAMPLE, in a
# frame from the field's normal n (the bicubic surface's, so it is right on the rut walls, where the flat grid's tangent space is
# not): the ray descends along -n and slides in n's tangent plane over MudPomDepthCm. The height is read in n's dominant projection
# - the top face blended from its two tilings exactly as BOG_SAMPLE blends them (a tiling the mix noise leaves out is not read), a
# wall at tiling A - with SampleGrad from the un-slid uv's derivatives, so no mip seam where the slide jumps. Optimised: faded out
# from MudPomNearM to MudPomFarM (the depth and the steps with it) behind a dynamic branch, so nothing is marched past it; none under
# the rut water (MudWaterTableCm, the patch's table in the field's frame, faded over its rim). The hit's slide (pomOff, world cm)
# moves every lookup in BOG_SAMPLE. The self-shadow (gt.Mud.POMShadow): 4 steps from the hit toward the sun (SunDir) within
# MudPomShadowM, faded over its last quarter; pomShade darkens the colour by MudPomShadowStrength. Ground relief GR1c: x a slope
# factor, 1 up to MudPomShadowSlopeLo (15 deg of the field's own normal n), falling linearly to MudPomShadowSlopeMin (0.3) at
# MudPomShadowSlopeHi (30 deg) and held there (the old tracks' walls drew dark streaks from it).
# MRP follow-up (the main session's look at Mud_PBR_Close: horizontal step bands on the larger lumps' flanks):
# - the step search reads the height one mip up (SampleGrad with doubled derivatives: a slightly blurred height, so a thin crest
#   between two steps is not jumped), the refine and the shadow read it as before (full resolution, the shadow one mip up too);
# - after the search, MudPomRefine (5) binary-search halvings of the last step's bracket at full resolution, then a secant
#   between the bracket's ends (one linear refine before), so the hit no longer snaps to the step layers;
# - steps: gt.Mud.POM 1 MudPomMinSteps (8); 2 MudPomMaxSteps (16) at a grazing angle to MudPomMinSteps looking straight down, with a
#   floor of MudPomGrazingMinSteps (12) at the grazing end (8 looking down) that the distance fade cannot take it under;
# - MudPomSteepCap (0, off): where the relief's own slope (full-resolution differences over 5 mm, times the depth) runs from 0.75
#   to 2.5 (cm per cm), the depth shrinks by up to MudPomSteepCap (four more samples where it runs). The fallback for the bands
#   that remained on the steepest flanks after the three fixes above; tried at 0.6 (Mud_PBR_Close_Steep with and without it, and
#   with gt.Mud.POMShadow 0): the bands stayed in all three, so it is off. They look like the packed height's own steps (BC7
#   keeps at most 16 levels of a 4 x 4 block's range: a lump's flank spans the whole range in a block), not the march's.
POM_HLSL='''struct GTMudPom
{
    int Axis; float3 UA; float3 UB; float2 Ax; float2 Ay; float2 Bx; float2 By; float Mix; float Sharp; float Cs; float Sn; float TileA; float TileB; bool UseA; bool UseB;
    float H(Texture2DArray T, SamplerState S, float3 o, float g)
    {
        if (Axis == 2)
        {
            float hA = 0.0;
            float hB = 0.0;
            if (UseA) { hA = T.SampleGrad(S, UA + float3(float2(o.x, -o.y) / TileA, 0.0), Ax * g, Ay * g).b; }
            if (UseB) { hB = T.SampleGrad(S, UB + float3(float2(Cs * o.x + Sn * o.y, Sn * o.x - Cs * o.y) / TileB, 0.0), Bx * g, By * g).b; }
            return lerp(hA, hB, saturate(((hB + Mix) - (hA + 1.0 - Mix)) / Sharp + 0.5));
        }
        float2 q = Axis == 1 ? float2(o.x, -o.z) : float2(o.y, -o.z);
        return T.SampleGrad(S, UA + float3(q / TileA, 0.0), Ax * g, Ay * g).b;
    }
};
{
    float pmDist = length(mudEye - CamPos);
    float pmFade = 1.0 - smoothstep(MudPomNearM * 100.0, max(MudPomFarM, MudPomNearM + 0.01) * 100.0, pmDist);
    float pmWater = MudWaterTableCm - s.r * 100.0;   // cm of rut water over this pixel (under 0: dry)
    pmFade *= 1.0 - smoothstep(-1.0, 0.25, pmWater);
    [branch] if (MudPOM > 0.5 && pmFade > 0.001)
    {
        GTMudPom Pm;
        Pm.Axis = (bogW.z >= bogW.y && bogW.z >= bogW.x) ? 2 : (bogW.y >= bogW.x ? 1 : 0);
        Pm.UA = float3(Pm.Axis == 2 ? bogUA : (Pm.Axis == 1 ? bogUY : bogUX), bogSlice);
        Pm.Ax = Pm.Axis == 2 ? bogAx : (Pm.Axis == 1 ? bogYx : bogXx);
        Pm.Ay = Pm.Axis == 2 ? bogAy : (Pm.Axis == 1 ? bogYy : bogXy);
        Pm.UB = float3(bogUB, bogSlice); Pm.Bx = bogBx; Pm.By = bogBy;
        Pm.Mix = bogMix; Pm.Sharp = max(BogBlendSharp, 0.001); Pm.Cs = bogCos; Pm.Sn = bogSin;
        Pm.TileA = max(BogTileCm, 1.0); Pm.TileB = max(BogTile2Cm, 1.0);
        Pm.UseA = Pm.Axis != 2 || bogMix < 0.999;
        Pm.UseB = Pm.Axis == 2 && bogMix > 0.001;
        float3 pmV = normalize(mudEye - CamPos);                 // from the eye into the surface
        float pmVn = min(dot(pmV, n), -0.2);                     // its descent along -n per unit (grazing rays clamped)
        float3 pmVt = pmV - n * dot(pmV, n);                     // its slide in n's tangent plane
        float pmDepth = max(MudPomDepthCm, 0.0) * pmFade;
        float pmSurf = 1.0 - Pm.H(BogORH, BogORHSampler, float3(0.0, 0.0, 0.0), 2.0);
        // The fallback for steep flanks (MudPomSteepCap, 0 = off): the height's change across this pixel against the uv's, a slope.
        if (MudPomSteepCap > 0.0)
        {
            float pmH0 = Pm.H(BogORH, BogORHSampler, float3(0.0, 0.0, 0.0), 1.0);
            float3 pmG = float3(Pm.H(BogORH, BogORHSampler, float3(0.5, 0.0, 0.0), 1.0), Pm.H(BogORH, BogORHSampler, float3(0.0, 0.5, 0.0), 1.0),
                                Pm.H(BogORH, BogORHSampler, float3(0.0, 0.0, 0.5), 1.0)) - pmH0;
            float pmSlope = length(pmG) * max(MudPomDepthCm, 0.0) / 0.5;   // the relief's slope over 5 mm, cm per cm
            pmDepth *= 1.0 - saturate(MudPomSteepCap) * smoothstep(0.75, 2.5, pmSlope);
        }
        float3 pmSlide = pmVt / (-pmVn) * pmDepth;               // the slide over the whole depth, world cm
        float pmT = saturate((-pmVn - 0.2) / 0.8);              // 0 grazing, 1 straight down
        float pmSteps = MudPomMinSteps;
        if (MudPOM > 1.5)
        {
            float pmFloor = lerp(MudPomGrazingMinSteps, MudPomMinSteps, pmT);
            pmSteps = lerp(pmFloor, lerp(MudPomMaxSteps, MudPomMinSteps, pmT), pmFade);
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
            pmSurf = 1.0 - Pm.H(BogORH, BogORHSampler, pmSlide * pmD, 2.0);
        }
        // The refine at full resolution: the bracket's ends, MudPomRefine halvings, then a secant between the last two ends.
        float pmLo = pmPrevD;
        float pmHi = pmD;
        float pmFLo = (1.0 - Pm.H(BogORH, BogORHSampler, pmSlide * pmLo, 1.0)) - pmLo;   // over 0: the ray still above the surface
        float pmFHi = (1.0 - Pm.H(BogORH, BogORHSampler, pmSlide * pmHi, 1.0)) - pmHi;
        int pmR = (int)clamp(MudPomRefine, 0.0, 6.0);
        [loop] for (int pmB = 0; pmB < 6; ++pmB)
        {
            if (pmB >= pmR) break;
            float pmMid = 0.5 * (pmLo + pmHi);
            float pmFMid = (1.0 - Pm.H(BogORH, BogORHSampler, pmSlide * pmMid, 1.0)) - pmMid;
            if (pmFMid > 0.0) { pmLo = pmMid; pmFLo = pmFMid; } else { pmHi = pmMid; pmFHi = pmFMid; }
        }
        float pmHit = lerp(pmLo, pmHi, saturate(pmFLo / max(pmFLo - pmFHi, 1e-5)));
        pomOff = pmSlide * pmHit;
        float pmSh = MudPOMShadow > 0.5 ? 1.0 - smoothstep(0.75 * MudPomShadowM * 100.0, max(MudPomShadowM, 0.01) * 100.0, pmDist) : 0.0;
        float3 pmL = normalize(SunDir);
        float pmLn = dot(pmL, n);
        [branch] if (pmSh > 0.001 && pmLn > 0.05 && pmHit > 0.02)
        {
            float3 pmLs = (pmL - n * pmLn) / pmLn * pmDepth;    // the slide toward the sun per whole depth climbed
            float pmOcc = 0.0;
            [unroll] for (int pmJ = 0; pmJ < 4; ++pmJ)
            {
                float pmRay = pmHit * (1.0 - (pmJ + 1) / 5.0);  // the ray's depth after climbing toward the sun
                float pmTop = 1.0 - Pm.H(BogORH, BogORHSampler, pomOff + pmLs * (pmHit - pmRay), 2.0);
                pmOcc = max(pmOcc, saturate((pmRay - pmTop) * 6.0));
            }
            // GR1c: less on the field's slopes (n's own tilt): 1 to MudPomShadowSlopeLo, MudPomShadowSlopeMin from MudPomShadowSlopeHi.
            float pmTilt = degrees(acos(saturate(n.z)));
            float pmSlopeK = lerp(1.0, saturate(MudPomShadowSlopeMin), saturate((pmTilt - MudPomShadowSlopeLo) / max(MudPomShadowSlopeHi - MudPomShadowSlopeLo, 0.01)));
            pomShade = pmOcc * pmSh * pmSlopeK;
        }
    }
}
'''
# The far gloss fade: the roughness rises toward FarGlossRough (only where it is below it) between FarGlossNearCm and
# FarGlossFarCm from the camera, so the sky's reflection in glossy slurry does not band across far ruts (A2's finding).
# MRP: the callers apply it - always with gt.Mud.PBR 0 (the look before MRP, when FarGlossFade was on), and with PBR only behind
# the FarGlossFade static switch (now off: at the PBR values the slurry is never under 0.45).
FAR_FADE='float bogFar=smoothstep(FarGlossNearCm,FarGlossFarCm,length(WorldPos-CamPos));\n'

# ---- MudRunner MR4 (docs/MUDRUNNER_LESSONS_PLAN.md MR4 execution block item 3), M_GT_Mud only: readable soft spots --------------
# S is the patch's static softness, MudLayer's G (AGTMudPatch: PF_R8G8, R the bog layer as before; G 0 off a bog's patch and with
# gt.Mud.SoftSpots 0, so w is 0 and the look is MRP's). The weight w = smoothstep(0.55, 0.68, S - 0.25 (h - 0.5)) with h the base
# slice's parallax height (ORH B, the top face's two tilings blended as the colour is): the lump tops stay the base mud and the
# hollows between them fill with the soft stuff first. Off Deep, inside a dynamic branch on w > 0.01, the Deep slice's colour,
# normal and ORH at the same parallax-slid uvs (the bog block again on slice 2, no second march): colour, normal and AO lerp by w,
# the roughness to max(0.45, Deep's). Off Deep the colour x lerp(1, 0.85, w) (MR4 follow-up: Deep keeps its colour, inside its soil
# band); every variant's roughness pulled toward 0.45 by 0.5 w. The same S feeds the traction (AGTMudPatch::SoftScalesAt): what you
# see is what you feel.
BOG_SAMPLE_MUD=BOG_SAMPLE.replace('bogAO=bogOR.x;bogRough=bogOR.y;\n}','bogAO=bogOR.x;bogRough=bogOR.y;\nbogH=lerp(boA.b,boB.b,bt);   // MR4: the base slice\'s parallax height\n}')
assert BOG_SAMPLE_MUD!=BOG_SAMPLE
SOFT_SAMPLE=BOG_SAMPLE
for _old,_new in [('bogSlice','2.0'),('bogColor=bogW.z','softColor=bogW.z'),('bogDetail=bogW.z','softDetail=bogW.z'),('bogAO=bogOR.x;bogRough=bogOR.y;','softAO=bogOR.x;softRough=bogOR.y;')]:
    assert _old in SOFT_SAMPLE,_old
    SOFT_SAMPLE=SOFT_SAMPLE.replace(_old,_new)
SOFT_HLSL='''// MR4: readable soft spots (S = MudLayer G; the hollows between the lumps fill first).
float softS=Texture2DSampleLevel(LayerTex,LayerTexSampler,uv,0).g;
float softW=smoothstep(0.55,0.68,softS-0.25*(bogH-0.5));
[branch]if(softW>0.01&&abs(bogSlice-2.0)>0.5)
{
// Not Deep: the Deep slice at the same parallax-slid uvs (no second march).
float3 softColor=0;float3 softDetail=0;float softRough=0.88;float softAO=1.0;
'''+SOFT_SAMPLE+'''bogColor=lerp(bogColor,softColor,softW);
bogDetail=lerp(bogDetail,softDetail,softW);
bogAO=lerp(bogAO,softAO,softW);
bogRough=lerp(bogRough,max(0.45,softRough),softW);
}
// Wetter: off Deep a little darker (MR4 follow-up: Deep keeps its colour, its soil band), every variant's roughness toward 0.45.
if(abs(bogSlice-2.0)>0.5){bogColor*=lerp(1.0,0.85,softW);}
bogRough=lerp(bogRough,0.45,0.5*softW);
'''

# ---- Mud and water MW1b item 1 (M_GT_Mud only): no parallax on deformed mud ---------------------------------------------------
# The moved-mud mask (the tracks, A, or the Fresh history, MudTread B) and the field's slope, before the parallax: its fade (so its
# depth, its steps and the branch that skips it) x mwPomK = (1 - moved) x (1 - smoothstep(PomFlatLo 10, PomFlatHi 22 deg, slope)),
# x DeepPomScale on the Deep slice (item 3). Walls, lips and fresh cells are not marched; the deformation detail carries them.
MW1B_MASK_HLSL='''// MW1b item 1: where the parallax runs - flat, unmoved mud only.
float mwSlopeDeg=degrees(acos(saturate(n.z)));
float mwMoved=max(tracks,saturate(Texture2DSampleLevel(TreadTex,TreadTexSampler,uv,0).b));
float mwPomK=(1.0-mwMoved)*(1.0-smoothstep(PomFlatLo,PomFlatHi,mwSlopeDeg))*(abs(bogSlice-2.0)<0.5?saturate(DeepPomScale):1.0);
'''
# ---- Mud roads MRD1 item 2 (M_GT_Mud only): the wet/dry term's and the deep walls' taps -----------------------------------------
MRD1_TAPS_HLSL='''// MRD1 item 2: twelve bilinear taps of the field round the pixel (six at 0.4, six at 0.85 x WetNearCm, the second ring turned
// 30 deg): mrdNear, the nearest standing water (under MudWaterTableCm) as about 1 - its distance / WetNearCm; the taps' mean, lowest
// and highest surface (cm) for the local relief (crowns, troughs, a deep track's wall).
float mrdH=s.r*100.0;
float mrdNear=smoothstep(-0.5,0.5,MudWaterTableCm-mrdH);
float mrdLo=mrdH;float mrdHi=mrdH;float mrdSum=0.0;
[unroll]for(int mrk=0;mrk<12;++mrk)
{
float mrf=mrk<6?0.4:0.85;
float mra=radians(60.0*(mrk%6)+(mrk<6?0.0:30.0));
float mrt=Texture2DSampleLevel(Tex,TexSampler,uv+float2(cos(mra),sin(mra))*mrf*WetNearCm/max(PatchSize.xy,1.0),0).r*100.0;
mrdNear=max(mrdNear,smoothstep(-0.5,0.5,MudWaterTableCm-mrt)*(1.0-mrf));
mrdLo=min(mrdLo,mrt);mrdHi=max(mrdHi,mrt);mrdSum+=mrt;
}
float mrdRel=mrdH-mrdSum/12.0;
float mrdWet=max(mrdNear,0.6*max(smoothstep(2.0,max(TroughWetCm,2.5),-mrdH),smoothstep(1.0,6.0,-mrdRel)))*saturate(WetDryOn);
float mrdDry=smoothstep(0.5,max(CrownCm,1.0),mrdRel)*(1.0-mrdWet)*saturate(WetDryOn);
float mrdDeep=smoothstep(WallAODeepCm-2.0,WallAODeepCm+2.0,mrdHi-mrdLo)*smoothstep(DeformSlopeLo,DeformSlopeHi,mwSlopeDeg);
'''
# MRD1 item 1's old tread (M_GT_Mud only): stage F's lug on the cells AGTMudPatch::PreChurnBraided marked (TreadTex G = 2 + the phase,
# R = the heading + its strength in eighths), point-sampled, the phase carried across the cell along the heading; x MudOldTread.
MRD1_TREAD_HLSL='''// MRD1 item 1: the partial old tread (gt.Mud.OldTread, MPC MudOldTread).
float3 mrdTread=float3(0.0,0.0,0.0);
{
float2 mrCellUv=(floor(uv*PatchTexels.xy)+0.5)/max(PatchTexels.xy,1.0);
float2 mrT=Texture2DSampleLevel(TreadTex,TreadTexSampler,mrCellUv,0).rg;
[branch]if(mrT.g>1.5&&OldTreadOn>0.5)
{
float mrStr=saturate(floor(mrT.r)/8.0);
float mrAng=frac(mrT.r)*6.28318531;
float2 mrDir=float2(cos(mrAng),sin(mrAng));
float2 mrCentre=PatchMin.xy+mrCellUv*PatchSize.xy;
float mrP=frac(mrT.g+dot(WorldPos.xy-mrCentre,mrDir)/max(OldTreadPeriodCm,1.0));
float mrS=frac(mrP+0.5)-0.5;
float mrTt=saturate((abs(mrS)*2.0-0.45)/0.55);
float mrSlope=-4.0*mrTt*(1.0-mrTt)*(mrS>=0.0?1.0:-1.0);
mrdTread=float3(-mrDir*(tan(radians(OldTreadTiltDeg))*mrSlope*mrStr),0.0);
}
}
'''
POM_MUD_HLSL=POM_HLSL.replace('    pmFade *= 1.0 - smoothstep(-1.0, 0.25, pmWater);','    pmFade *= (1.0 - smoothstep(-1.0, 0.25, pmWater)) * mwPomK * mrdSilt;   // MW1b: none on deformed mud; MRD1b: x the silt')
# ---- Mud roads MRD1b item 3 (M_GT_Mud only): the silt surface on a mud road (SiltTileMul, SiltStrength; 1 and 1 on a bog) ------
MRD1B_TILE_HLSL='''// MRD1b item 3: the bake tiles SiltTileMul x finer on a mud road (the deformation detail keeps its own scale, bogTileBase).
float bogTileBase=BogTileCm;
BogTileCm/=max(SiltTileMul,0.25);BogTile2Cm/=max(SiltTileMul,0.25);
'''
MRD1B_SILT_HLSL='''// MRD1b item 3: the running surface (off the crowns and lips - 1-4 cm over the taps' mean - and the walls over DeformSlopeLo..Hi)
// takes the bake's lump normal, AO and parallax depth x SiltStrength; the ridges, lips and walls keep full strength.
float mrdSilt=lerp(1.0,saturate(SiltStrength),(1.0-smoothstep(1.0,4.0,mrdRel))*(1.0-smoothstep(DeformSlopeLo,DeformSlopeHi,mwSlopeDeg)));
'''
MRD1B_SILT_APPLY_HLSL='''bogDetail*=mrdSilt;bogAO=lerp(1.0,bogAO,mrdSilt);   // MRD1b item 3: the silt
'''
assert POM_MUD_HLSL!=POM_HLSL

# ---- Mud and water MW1 item 2b (M_GT_Mud only): the crisp deformation detail ---------------------------------------------
# Moved mud and steep banks get a second, finer read of the variant slice that never slides with the field: its normal and its
# ORH AO at DeformTileMul x the tiling (BogTileCm / 2.6, about 1.15 m) turned DeformTurnDeg (29 deg, sharing no repeat with the
# base's two tilings), from the un-slid surface point (mudEye) - tri-planar by the field normal's weights (bogW), the top face and
# the two wall projections each turned the same way - and laid on as a perturbation in the field normal's tangent plane (so it
# holds on the walls). Its strength mwK = DeformDetailOn (gt.Mud.DeformDetail) x DeformStrength (0.8) x max(the moved-mud mask -
# the tracks, A, or the Fresh history, MudTread B - and smoothstep(DeformSlopeLo 12, DeformSlopeHi 25 deg) of the field's slope).
# Its uvs' derivatives are taken outside the branch (SampleGrad inside it). The AO multiplies bogAO by lerp(1, its AO, mwK).
MW1_DETAIL_HLSL='''// MW1 item 2b: the crisp, non-sliding deformation detail (gt.Mud.DeformDetail).
// MW1b item 3: Deep's slice softened - its normal x DeepNormalScale, its AO's strength x DeepAOScale.
if(abs(bogSlice-2.0)<0.5){bogDetail*=DeepNormalScale;bogAO=lerp(1.0,bogAO,saturate(DeepAOScale));}
float mwK=saturate(DeformDetailOn)*saturate(DeformStrength)*max(mwMoved,smoothstep(DeformSlopeLo,DeformSlopeHi,mwSlopeDeg));
float mwTile=max(bogTileBase,1.0)/max(DeformTileMul,0.1);   // MRD1b: the detail's own scale, not the silt's
float mwC=cos(radians(DeformTurnDeg));float mwS=sin(radians(DeformTurnDeg));
float2 mwQZ=float2(mwC*mudEye.x+mwS*mudEye.y,-mwS*mudEye.x+mwC*mudEye.y);
float2 mwQY=float2(mwC*mudEye.x+mwS*mudEye.z,-mwS*mudEye.x+mwC*mudEye.z);
float2 mwQX=float2(mwC*mudEye.y+mwS*mudEye.z,-mwS*mudEye.y+mwC*mudEye.z);
float2 mwUZ=float2(mwQZ.x,-mwQZ.y)/mwTile;float2 mwUY=float2(mwQY.x,-mwQY.y)/mwTile;float2 mwUX=float2(mwQX.x,-mwQX.y)/mwTile;
float2 mwZx=ddx(mwUZ);float2 mwZy=ddy(mwUZ);float2 mwYx=ddx(mwUY);float2 mwYy=ddy(mwUY);float2 mwXx=ddx(mwUX);float2 mwXy=ddy(mwUX);
float3 mwDetail=float3(0.0,0.0,0.0);
[branch]if(mwK>0.001)
{
float3 mwD=float3(0.0,0.0,0.0);float mwAO=0.0;float mwWsum=0.0;
{
float2 mwd2=UnpackNormalMap(BogN.SampleGrad(BogNSampler,float3(mwUZ,bogSlice),mwZx,mwZy)).xy;
float mwa1=BogORH.SampleGrad(BogORHSampler,float3(mwUZ,bogSlice),mwZx,mwZy).r;
mwD+=bogW.z*float3(mwC*mwd2.x-mwS*mwd2.y,mwS*mwd2.x+mwC*mwd2.y,0.0);mwAO+=bogW.z*mwa1;mwWsum+=bogW.z;
}
[branch]if(bogW.y>0.02)
{
float2 mwd2=UnpackNormalMap(BogN.SampleGrad(BogNSampler,float3(mwUY,bogSlice),mwYx,mwYy)).xy;
float mwa1=BogORH.SampleGrad(BogORHSampler,float3(mwUY,bogSlice),mwYx,mwYy).r;
mwD+=bogW.y*float3(mwC*mwd2.x-mwS*mwd2.y,0.0,mwS*mwd2.x+mwC*mwd2.y);mwAO+=bogW.y*mwa1;mwWsum+=bogW.y;
}
[branch]if(bogW.x>0.02)
{
float2 mwd2=UnpackNormalMap(BogN.SampleGrad(BogNSampler,float3(mwUX,bogSlice),mwXx,mwXy)).xy;
float mwa1=BogORH.SampleGrad(BogORHSampler,float3(mwUX,bogSlice),mwXx,mwXy).r;
mwD+=bogW.x*float3(0.0,mwC*mwd2.x-mwS*mwd2.y,mwS*mwd2.x+mwC*mwd2.y);mwAO+=bogW.x*mwa1;mwWsum+=bogW.x;
}
mwAO/=max(mwWsum,0.0001);
mwD-=n*dot(mwD,n);   // in the field normal's tangent plane: it holds on the walls
mwDetail=mwK*mwD;
bogAO*=lerp(1.0,saturate(1.0-lerp(1.0,WallAOBoost,mrdDeep)*(1.0-mwAO)),mwK);   // MRD1: the deep walls' AO x WallAOBoost
}
'''

def _find(expressions,cls,**props):
    for e in expressions:
        if isinstance(e,cls) and all(str(e.get_editor_property(k))==str(v) for k,v in props.items()):return e
    return None

def ensure_patch_variants():
    # LM5b: MPC_TrackPaint's PatchVariant0..3 (UGTMudSubsystem writes each patch's MudVariant beside its Patch<slot> box).
    # MRP: and MudPBR / MudPOM / MudPOMShadow (UGTTrackPaintSubsystem writes them from gt.Mud.PBR / POM / POMShadow).
    # MW1: and MudDeformDetail / MudWaterMotion (UGTMudWaterSubsystem writes them from gt.Mud.DeformDetail / WaterMotion).
    mpc=eal.load_asset(MPC_PATH);assert mpc,'no '+MPC_PATH+' (run setup_m6_mud.bat)'
    scalars=list(mpc.get_editor_property('scalar_parameters'));names=[str(p.get_editor_property('parameter_name')) for p in scalars];added=[]
    for name,value in [('PatchVariant%d'%i,0.0) for i in range(4)]+list(MRP_MPC.items())+list(MW1_MPC.items())+list(MRD1_MPC.items()):   # MRD1: MudOldTread
        if name in names:continue
        p=u.CollectionScalarParameter();p.set_editor_property('parameter_name',name);p.set_editor_property('default_value',value);scalars.append(p);added.append(name)
    if added:
        mpc.set_editor_property('scalar_parameters',scalars);eal.save_loaded_asset(mpc)
    return {'collection':MPC_PATH,'added':added,'scalars':[str(p.get_editor_property('parameter_name')) for p in mpc.get_editor_property('scalar_parameters')]}

def _inputs(node,names):
    inputs=list(node.get_editor_property('inputs'));have=[str(i.get_editor_property('input_name')) for i in inputs]
    for name in names:
        if name not in have:
            slot=u.CustomInput();slot.set_editor_property('input_name',name);inputs.append(slot)
    node.set_editor_property('inputs',inputs)

def _drop_inputs(node,names):
    # MRP: a retired input leaves the custom node (an unconnected input would not compile); the others keep their links.
    inputs=list(node.get_editor_property('inputs'));kept=[i for i in inputs if str(i.get_editor_property('input_name')) not in names]
    if len(kept)!=len(inputs):node.set_editor_property('inputs',kept)
    return [str(i.get_editor_property('input_name')) for i in inputs if str(i.get_editor_property('input_name')) in names]

def _outputs(node,pairs):
    outs=list(node.get_editor_property('additional_outputs'));have=[str(o.get_editor_property('output_name')) for o in outs]
    for name,kind in pairs:
        if name not in have:
            o=u.CustomOutput();o.set_editor_property('output_name',name);o.set_editor_property('output_type',kind);outs.append(o)
    node.set_editor_property('additional_outputs',outs)

def bog_array(name):
    path=DEST+'/'+BOG_ARRAYS[name];tex=eal.load_asset(path)
    assert tex,'no %s: run & Art/import_mud_variants.ps1 first (LM5b; MRP: python Art/bake_mud_orh.py before it for the ORH array)'%path
    return tex

def mpc_node(mat,expressions,param,desc,x,y):
    # MRP: an MPC_TrackPaint scalar (found by desc on a rerun, never doubled).
    node=_find(expressions,u.MaterialExpressionCollectionParameter,desc=desc)
    if node is None:
        node=mel.create_material_expression(mat,u.MaterialExpressionCollectionParameter,x,y);expressions.append(node);node.set_editor_property('desc',desc)
    node.set_editor_property('collection',eal.load_asset(MPC_PATH));node.set_editor_property('parameter_name',param)
    return node

def wire_bog(mat,surface,landscape):
    # LM5b: the arrays, the scalars, the camera, the far-fade switch onto the surface node (found or made on a rerun, never doubled).
    # MRP: the ORH array in place of the rough and height arrays (their inputs and parameters removed), the PBR switch, and on
    # M_GT_Mud the parallax's scalars and switches, the rut water's table and the sun.
    expressions=list(mel.get_material_expressions(mat))
    retired=_drop_inputs(surface,BOG_RETIRED)
    for e in list(expressions):
        if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name')) in ['LiveMud_'+n for n in BOG_RETIRED]:
            retired.append(str(e.get_editor_property('parameter_name')));mel.delete_material_expression(mat,e);expressions.remove(e)
    mrp=['MudCavityTint'] if landscape else list(MRP_SCALARS)
    names=list(BOG_ARRAYS)+list(BOG_SCALARS)+['CamPos','FarFade','MudPBR']+mrp+(['P0','P1','P2','P3','PV0','PV1','PV2','PV3','ApronCm'] if landscape else ['MudVariant','MudPOM','MudPOMShadow','SunDir'])
    _inputs(surface,names);y=[5200]
    def place():
        y[0]+=110;return y[0]
    for name in BOG_ARRAYS:
        param='LiveMud_'+name
        node=_find(expressions,u.MaterialExpressionTextureObjectParameter,parameter_name=param)
        if node is None:node=mel.create_material_expression(mat,u.MaterialExpressionTextureObjectParameter,-1500,place());expressions.append(node)
        node.set_editor_property('parameter_name',param);node.set_editor_property('texture',bog_array(name))
        node.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,BOG_SAMPLERS[name]))
        node.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        assert mel.connect_material_expressions(node,'',surface,name),name
    scalars=dict(BOG_SCALARS);scalars.update({'MudApronCm':APRON_CM} if landscape else {'MudVariant':0.0})
    scalars.update({k:MRP_SCALARS[k] for k in mrp})
    for name,value in scalars.items():
        node=_find(expressions,u.MaterialExpressionScalarParameter,parameter_name=name)
        if node is None:node=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-1500,place());expressions.append(node)
        node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value)
        assert mel.connect_material_expressions(node,'',surface,'ApronCm' if name=='MudApronCm' else name),name
    cam=_find(expressions,u.MaterialExpressionCameraPositionWS)
    if cam is None:cam=mel.create_material_expression(mat,u.MaterialExpressionCameraPositionWS,-1500,place());expressions.append(cam)
    assert mel.connect_material_expressions(cam,'',surface,'CamPos'),'CamPos'
    switch=_find(expressions,u.MaterialExpressionStaticSwitchParameter,parameter_name='FarGlossFade')
    if switch is None:
        switch=mel.create_material_expression(mat,u.MaterialExpressionStaticSwitchParameter,-1300,place());expressions.append(switch)
        switch.set_editor_property('parameter_name','FarGlossFade')
        for value,pins in [(1.0,('True','A')),(0.0,('False','B'))]:
            c=mel.create_material_expression(mat,u.MaterialExpressionConstant,-1500,place());c.set_editor_property('r',value)
            assert any(mel.connect_material_expressions(c,'',switch,pin) for pin in pins),'the FarGlossFade switch has no %s pin'%(pins,)
    # MRP: off - at the PBR values the far fade is not needed (gt.Mud.PBR 0 applies it whatever the switch says, as before MRP).
    switch.set_editor_property('default_value',False)
    assert mel.connect_material_expressions(switch,'',surface,'FarFade'),'FarFade'
    for pin,desc in [('MudPBR','LiveMud:pbr')]+([] if landscape else [('MudPOM','LiveMud:pom'),('MudPOMShadow','LiveMud:pomshadow')]):
        assert mel.connect_material_expressions(mpc_node(mat,expressions,pin,desc,-1500,place()),'',surface,pin),pin
    if not landscape:
        sun=_find(expressions,u.MaterialExpressionSkyAtmosphereLightDirection)
        if sun is None:
            sun=mel.create_material_expression(mat,u.MaterialExpressionSkyAtmosphereLightDirection,-1500,place());expressions.append(sun)
        sun.set_editor_property('light_index',0)
        assert mel.connect_material_expressions(sun,'',surface,'SunDir'),'SunDir'
    if landscape:
        mpc=eal.load_asset(MPC_PATH)
        for i in range(4):
            for pin,param,desc in [('P%d'%i,'Patch%d'%i,'Landscape:patch%d'%i),('PV%d'%i,'PatchVariant%d'%i,'LiveMud:variant%d'%i)]:
                node=_find(expressions,u.MaterialExpressionCollectionParameter,desc=desc)
                if node is None:
                    node=mel.create_material_expression(mat,u.MaterialExpressionCollectionParameter,-1500,place());expressions.append(node);node.set_editor_property('desc',desc)
                    node.set_editor_property('collection',mpc);node.set_editor_property('parameter_name',param)
                assert mel.connect_material_expressions(node,'',surface,pin),pin
    return {'arrays':{k:DEST+'/'+v for k,v in BOG_ARRAYS.items()},'scalars':scalars,'retired':retired,
            'far_gloss_fade':'static switch FarGlossFade, off (MRP); gt.Mud.PBR 0 applies the fade as before','switches':'MPC_TrackPaint MudPBR'+('' if landscape else ', MudPOM, MudPOMShadow')}

def wire_ao(mat,surface):
    # MRP item 2: the surface's Occl output (1 - AO; 0, no occlusion, where the code leaves it - M_GT_Snow's copy of this graph)
    # through a OneMinus onto the Ambient Occlusion pin.
    expressions=list(mel.get_material_expressions(mat))
    one=next((e for e in expressions if isinstance(e,u.MaterialExpressionOneMinus) and str(e.get_editor_property('desc'))=='LiveMud:ao'),None)
    if one is None:
        one=mel.create_material_expression(mat,u.MaterialExpressionOneMinus,-250,600);one.set_editor_property('desc','LiveMud:ao')
    assert mel.connect_material_expressions(surface,'Occl',one,''),'Occl -> OneMinus'
    assert mel.connect_material_property(one,'',u.MaterialProperty.MP_AMBIENT_OCCLUSION),'AO pin'
    return 'Occl -> OneMinus -> Ambient Occlusion'

def attach(mat,landscape=False):
    expressions=list(mel.get_material_expressions(mat))
    desc='Landscape:mudtex' if landscape else 'Mud surface (PS)'
    surface=next(e for e in expressions if isinstance(e,u.MaterialExpressionCustom) and (str(e.get_editor_property('desc'))==desc or str(e.get_editor_property('description'))==desc))
    inputs=list(surface.get_editor_property('inputs'));names=[str(i.get_editor_property('input_name')) for i in inputs]
    for name in TEXTURES:
        if name not in names:
            slot=u.CustomInput();slot.set_editor_property('input_name',name);inputs.append(slot)
    surface.set_editor_property('inputs',inputs)
    for name,asset in TEXTURES.items():
        param='LiveMud_'+name
        node=next((e for e in expressions if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))==param),None)
        if node is None:node=mel.create_material_expression(mat,u.MaterialExpressionTextureObjectParameter)
        node.set_editor_property('parameter_name',param);node.set_editor_property('texture',eal.load_asset(DEST+'/'+asset))
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if name.endswith('N') else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        assert mel.connect_material_expressions(node,'',surface,name)
    if not landscape:
        # LM1: the two scalars, and the tread texture the legacy block wired as TreadTex (the live code never sampled it).
        inputs=list(surface.get_editor_property('inputs'));names=[str(i.get_editor_property('input_name')) for i in inputs]
        for name in list(LM1_SCALARS)+['TreadTex']:
            if name not in names:
                slot=u.CustomInput();slot.set_editor_property('input_name',name);inputs.append(slot)
        surface.set_editor_property('inputs',inputs)
        for name,value in LM1_SCALARS.items():
            node=next((e for e in expressions if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))==name),None)
            if node is None:node=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-1100,4200+100*len(name))
            node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value)
            assert mel.connect_material_expressions(node,'',surface,name)
        tread=next((e for e in expressions if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='MudTread'),None)
        assert tread is not None,'M_GT_Mud has no MudTread parameter (run the legacy setup_m6_mud first)'
        assert mel.connect_material_expressions(tread,'',surface,'TreadTex')
        # MW1 item 2: the deformation detail's and the broken highlights' scalars, and gt.Mud.DeformDetail (MPC MudDeformDetail).
        _inputs(surface,list(MW1_MUD_SCALARS)+['DeformDetailOn']+list(MRD1_MUD_SCALARS)+['OldTreadOn'])   # MRD1: its scalars and gt.Mud.OldTread
        for k,(name,value) in enumerate(list(MW1_MUD_SCALARS.items())+list(MRD1_MUD_SCALARS.items())):
            node=_find(expressions,u.MaterialExpressionScalarParameter,parameter_name=name)
            if node is None:node=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-1700,7400+110*k);expressions.append(node)
            node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value)
            assert mel.connect_material_expressions(node,'',surface,name),name
        assert mel.connect_material_expressions(mpc_node(mat,expressions,'MudDeformDetail','LiveMud:deformdetail',-1700,7300),'',surface,'DeformDetailOn'),'DeformDetailOn'
        assert mel.connect_material_expressions(mpc_node(mat,expressions,'MudOldTread','LiveMud:oldtread',-1700,7200),'',surface,'OldTreadOn'),'OldTreadOn'   # MRD1
        _outputs(surface,[('Occl',u.CustomMaterialOutputType.CMOT_FLOAT1),('Spec',u.CustomMaterialOutputType.CMOT_FLOAT1)])   # MRP: 1 - AO; MW1b: the specular
    bog=wire_bog(mat,surface,landscape)
    if landscape:
        # LM5b: the clay outside the mud as before (bit for bit where the apron is 0); round each live patch's box the patch's
        # variant slice, fading to the clay over ApronCm. Apron/ApronColor/ApronNormal/ApronRough feed a strip landscape's own
        # apron (live_landscape). Away from every apron the bog samples are skipped (a branch; their gradients come from outside it).
        # MRP: the ORH's roughness (PBR) or, with gt.Mud.PBR 0, the bake's own (the remap inverted) and the far fade as before; with
        # PBR a cavity tint by the ORH's AO (no AO pin here: the apron feathers into the clay).
        _outputs(surface,[('Apron',u.CustomMaterialOutputType.CMOT_FLOAT1),('ApronColor',u.CustomMaterialOutputType.CMOT_FLOAT3),
                          ('ApronNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('ApronRough',u.CustomMaterialOutputType.CMOT_FLOAT1)])
        code='float3 gn=normalize(VertexNormal.xyz);float worked=0;float3 PaintPos=WorldPos;\n'+sampling()+'''
// LM5b: the apron - the nearest live patch box (MPC_TrackPaint Patch0..3; all zero outside play) and its variant (PatchVariant0..3).
float4 bogBoxes[4]={P0,P1,P2,P3};float bogSlots[4]={PV0,PV1,PV2,PV3};
float bogEdge=1.0e9;float bogSlice=0;
[unroll]for(int bk=0;bk<4;++bk){float4 bb=bogBoxes[bk];if(bb.z>bb.x&&bb.w>bb.y){float2 bq=abs(WorldPos.xy-0.5*(bb.xy+bb.zw))-0.5*(bb.zw-bb.xy);float be=max(bq.x,bq.y);if(be<bogEdge){bogEdge=be;bogSlice=bogSlots[bk];}}}
float apron=1.0-smoothstep(0.0,max(ApronCm,1.0),bogEdge);
'''+BOG_SETUP+'''float3 bogColor=0;float3 bogDetail=0;float bogRough=0.88;float bogAO=1.0;
[branch]if(apron>0.0)
'''+BOG_SAMPLE+FAR_FADE+'''if(MudPBR>0.5){bogRough=max(lerp(bogRough,max(bogRough,FarGlossRough),bogFar*FarFade),0.4);bogColor*=1.0-saturate(MudCavityTint)*(1.0-bogAO);}
else{bogRough=0.14+(bogRough-0.45)*1.54;bogRough=lerp(bogRough,max(bogRough,FarGlossRough),bogFar);}
BogAlbedo=lerp(clayColor*0.85,bogColor,apron);
Normal=normalize(gn+lerp(clayDetail,bogDetail,apron));
float mudRough=lerp(0.88,bogRough,apron);
MudRoughOut=float3(mudRough,mudRough,mudRough);BogRoughOut=MudRoughOut;
Apron=apron;ApronColor=bogColor;ApronNormal=normalize(gn+bogDetail);ApronRough=bogRough;
return lerp(clayColor,bogColor,apron);
'''
    else:
        tree=ast.parse((ROOT/'Art/Unreal/setup_m6_mud.py').read_text())
        prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SURFACE_A' for t in n.targets))
        code=prefix+'''// Existing bicubic height/derivatives above remain unchanged.
// LM5b: worked (the tyres' compressed ground) now only says where the weather's wetness darkens and glosses more.
float worked=tracks*smoothstep(0.0,0.035,-s.r)*lerp(0.8,0.25,saturate(length(slope)));
float3 PaintPos=WorldPos+float3(0,0,s.r*100.0);
// MRP: the displaced surface point the eye sees (before the slide below), for the parallax's ray.
float3 mudEye=PaintPos;
// LM1: the mud is dragged with the field - sampled back along the field's offset (GB, m), so where mud moved its texture
// moved with it. The vertices do not move (SlideScale stays 0).
PaintPos.xy-=s.gb*100.0*SlideUV;
// LM5b: one layer - the patch's variant slice everywhere, ruts, ridges and banks alike (no worked bake, no matte crests, no
// darker Bog row: the owner's "the ruts should be the same color and texture as the rest").
float bogSlice=MudVariant;
float3 bogColor=0;float3 bogDetail=0;float bogRough=0.88;float bogAO=1.0;float bogH=0.5;
'''+MRD1B_TILE_HLSL+BOG_SETUP+MW1B_MASK_HLSL+MRD1_TAPS_HLSL+MRD1B_SILT_HLSL+POM_MUD_HLSL+BOG_SAMPLE_MUD+SOFT_HLSL+MRD1B_SILT_APPLY_HLSL+MW1_DETAIL_HLSL+MRD1_TREAD_HLSL+'''float3 col=bogColor;
// LM1: mud that has just moved looks wet and fresh, then dulls (MudTread B, the field's Fresh 0..1), on top of the
// weather's wetness. Untouched ground has Fresh 0 and does not change. LM5b: FreshWet slight.
float fresh=saturate(saturate(Texture2DSampleLevel(TreadTex,TreadTexSampler,uv,0).b)*FreshWet);
'''+FAR_FADE+'''float rough=bogRough;float occl=0.0;float spec=0.5;
if(MudPBR>0.5)
{
// MRP item 1: physically based. bogRough is the ORH's remapped roughness (the lump tops 0.89-0.95, the slurry 0.46-0.61); wetR is
// the same surface saturated, MudWetRoughLo..Hi (0.45-0.65). The weather's wetness darkens 0.65-0.82x (as before) and takes the
// roughness toward wetR (fully on the tyres' worked ground, half elsewhere); the fresh sheen darkens 0.85x and takes it to wetR -
// never glossier than wet mud, never under 0.4. The AO (ORH R, MudAOStrength) goes to the Ambient Occlusion output and tints the
// cavities by at most MudCavityTint. The far gloss fade only behind FarGlossFade.
// MW1b item 2: matte toward a low sun - the ORH's band (0.45 slurry .. 0.95 lump tops) remapped dry to MudDryRoughLo..Hi (0.8-0.95)
// and wet to MudWetBandLo..Hi (0.62-0.8), for every variant (MudWetRoughLo/Hi are no longer read).
float mwBand=saturate((bogRough-0.45)/0.5);
float dryR=lerp(MudDryRoughLo,MudDryRoughHi,mwBand);
float wetR=lerp(MudWetBandLo,MudWetBandHi,mwBand);
col*=1.0-wet*(0.18+0.17*worked);
rough=lerp(dryR,wetR,saturate(wet*(0.5+0.5*worked)));
col*=lerp(1.0,0.85,fresh);
rough=lerp(rough,wetR,fresh);
// MW1 item 2d: broken highlights on wet mud outside the rut water - the roughness +- RoughNoiseAmp of two value-noise octaves
// (RoughNoiseCm1, RoughNoiseCm2) on the un-slid surface, by the wet share mwWet; the wet floor WetRoughFloor (from 0.4, reached
// at a wet share of 0.5). mwUnder: the rut water's cover (MudWaterTableCm over the mud).
{
float mwWet=1.0-(1.0-saturate(wet*(0.5+0.5*worked)))*(1.0-fresh);
float mwUnder=smoothstep(-1.0,0.25,MudWaterTableCm-s.r*100.0);
float mwN=0.0;
[unroll]for(int mwo=0;mwo<2;++mwo)
{
float2 mwq=mudEye.xy/max(mwo==0?RoughNoiseCm1:RoughNoiseCm2,0.5)+(mwo==0?float2(3.1,7.7):float2(-11.3,5.9));
float2 mwi=floor(mwq);float2 mwf=mwq-mwi;mwf=mwf*mwf*(3.0-2.0*mwf);
float4 mwh;
[unroll]for(int mwc=0;mwc<4;++mwc){float2 mwip=mwi+float2(mwc%2,mwc/2);float3 mwp=frac(mwip.xyx*0.1031);mwp+=dot(mwp,mwp.yzx+33.33);mwh[mwc]=frac((mwp.x+mwp.y)*mwp.z);}
mwN+=(mwo==0?0.6:0.4)*lerp(lerp(mwh.x,mwh.y,mwf.x),lerp(mwh.z,mwh.w,mwf.x),mwf.y);
}
rough+=RoughNoiseAmp*(2.0*mwN-1.0)*mwWet*(1.0-mwUnder);
rough=max(rough,WetRoughFloor);   // MW1b: the floor 0.62 wet or dry
}
// MRD1 item 2: wet near the water and in the troughs (darker, a soft sheen), drying on the crowns (lighter, matte); MW1b's bands between.
col*=lerp(1.0,WetDarken,mrdWet)*lerp(1.0,DryLighten,mrdDry);
rough=lerp(rough,lerp(WetRoughLo,WetRoughHi,mwBand),mrdWet);
rough=lerp(rough,lerp(DryRoughLo,DryRoughHi,mwBand),mrdDry);
rough=lerp(rough,max(rough,FarGlossRough),bogFar*FarFade);
rough=max(rough,0.4);
float ao=lerp(1.0,bogAO,saturate(MudAOStrength));
col*=1.0-saturate(MudCavityTint)*(1.0-ao);
occl=1.0-ao;
// MW1b item 2: specular occlusion from the baked AO (the cavities keep no sky highlight): Specular 0.5 x lerp(1, AO^2, MudSpecOcclusion).
spec=0.5*lerp(1.0,ao*ao,saturate(MudSpecOcclusion));
}
else
{
// gt.Mud.PBR 0: the look before MRP - the bake's own roughness (the ORH's remap inverted), glossier wet and fresh, the far fade.
float oldR=0.14+(bogRough-0.45)*1.54;
col*=1.0-wet*(0.18+0.17*worked);
rough=lerp(oldR,min(oldR,0.48),wet*worked);
col*=lerp(1.0,0.85,fresh);
rough=lerp(rough,min(rough,0.5),fresh);
rough=lerp(rough,max(rough,FarGlossRough),bogFar);
}
// MRP item 3: the parallax's self-shadow toward the sun (0 without it).
col*=1.0-saturate(MudPomShadowStrength)*pomShade;
Normal=normalize(n+bogDetail+mwDetail+mrdTread);Rough=rough;Mask=1.0;Emissive=0;Occl=occl;Spec=spec;
if(Diagnostic>0.5){Emissive=0.3*float3(saturate(0.5+s.r*100.0/80.0),saturate((WorldPos.z-DiagZ0)/max(DiagZRange,1.0)),tracks);col=0;Rough=1;Occl=0;}
return col;
'''
    surface.set_editor_property('code',code)
    ao=None if landscape else wire_ao(mat,surface)
    if not landscape:assert mel.connect_material_property(surface,'Spec',u.MaterialProperty.MP_SPECULAR),'MW1b: Spec -> Specular'
    errors=mel.recompile_material(mat);assert not errors,str(errors);eal.save_loaded_asset(mat)
    return {'material':mat.get_path_name(),'surface':desc,'approved_textures':list(TEXTURES.values()),'bog':bog,'fresh_wet':None if landscape else LM1_SCALARS['FreshWet'],
            'ambient_occlusion':ao,'pom':None if landscape else 'POM_HLSL (gt.Mud.POM, gt.Mud.POMShadow)',
            'soft_spots':None if landscape else 'MR4 SOFT_HLSL: MudLayer G, toward the Deep slice (gt.Mud.SoftSpots)','compile_errors':list(errors)}

# ---- LM5b: a strip landscape's own apron (L_MudDrive's M_LiveLandscape, L_MudVariants' M_VariantsLandscape) ----------
# A copy of M_GT_Landscape (made once) whose groundtex is the approved art road (gravel bakes, two tyre lanes) and whose
# apron round each live patch takes the patch's variant slice: the box and the feather from the mud block's Apron output
# (MPC_TrackPaint's boxes, so it follows any route), the colour, normal and roughness from its ApronColor/Normal/Rough. Until
# LM5b the apron was the clay inside two boxes measured on L_MudDrive (setup_live_mud_drive.py's q0/q1).
GROUND_HLSL='''float2 f=frac(WorldPos.xy/1200.0);float2 uv=1-abs(f*2-1);uv.y=1-uv.y;
float lane=max(exp(-pow((WorldPos.y-79.0)/34.0,2.0)),exp(-pow((WorldPos.y+79.0)/34.0,2.0)));
DirtAlbedo=lerp(Texture2DSample(RoadC,RoadCSampler,uv).rgb,Texture2DSample(LaneC,LaneCSampler,uv).rgb,lane);
GrassRoughOut=float3(.9,.9,.9);DirtRoughOut=GrassRoughOut;
float n=0.5+0.5*sin(WorldPos.x*.006)*sin(WorldPos.y*.007);
// LM5b: the apron is the live patches' own boxes (the mud block's Apron: 1 inside a box, feathered to 0 over ApronCm outside
// it) in the patch's variant slice (ApronC), so the patch's edge does not show. Outside play there are no boxes and no apron.
float blend=saturate(ApronW);
ClayBlend=blend;
DirtAlbedo=lerp(DirtAlbedo,ApronC,blend);
return lerp(lerp(float3(.095,.08,.052),float3(.19,.145,.083),n),ApronC,blend);
'''

def live_landscape(path):
    def setprops(obj,**values):
        for key,value in values.items():obj.set_editor_property(key,value)
        return obj
    landscape=eal.load_asset(path)
    if landscape is None:landscape=eal.duplicate_asset('/Game/GrandTour/Materials/M_GT_Landscape',path)
    facts=attach(landscape,True)
    for e in list(mel.get_material_expressions(landscape)):
        if isinstance(e,u.MaterialExpressionLandscapeGrassOutput):mel.delete_material_expression(landscape,e)
    ground=next(e for e in mel.get_material_expressions(landscape) if isinstance(e,u.MaterialExpressionCustom) and str(e.get_editor_property('desc'))=='Landscape:groundtex')
    _inputs(ground,['RoadC','LaneC','EdgeClay','ApronW','ApronC'])
    _outputs(ground,[('ClayBlend',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for key,asset in [('RoadC','T_GR_LooseColor'),('LaneC','T_GR_CompactColor'),('EdgeClay','T_MS_ClayColor')]:
        tex=next((e for e in mel.get_material_expressions(landscape) if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='Live_'+key),None)
        if tex is None:tex=mel.create_material_expression(landscape,u.MaterialExpressionTextureObjectParameter)
        folder='MudStyle' if key=='EdgeClay' else 'GravelRoad'
        setprops(tex,parameter_name='Live_'+key,texture=eal.load_asset('/Game/GrandTour/ArtTests/'+folder+'/'+asset));mel.connect_material_expressions(tex,'',ground,key)
    mudtex=next(e for e in mel.get_material_expressions(landscape) if isinstance(e,u.MaterialExpressionCustom) and str(e.get_editor_property('desc'))=='Landscape:mudtex')
    assert mel.connect_material_expressions(mudtex,'Apron',ground,'ApronW'),'ApronW'
    assert mel.connect_material_expressions(mudtex,'ApronColor',ground,'ApronC'),'ApronC'
    ground.set_editor_property('code',GROUND_HLSL)
    # The apron shares the patch's normals and roughness as well as its colour. The previous layer blend stays outside the
    # apron; the wrappers are found by desc on a rerun, so nothing nests.
    for label,prop,code,kind,pins in [
        ('LiveApronNormal',u.MaterialProperty.MP_NORMAL,'return normalize(lerp(Old,Clay,Blend));',u.CustomMaterialOutputType.CMOT_FLOAT3,[('ApronNormal','Clay')]),
        ('LiveApronRoughness',u.MaterialProperty.MP_ROUGHNESS,'return lerp(Old,Rough,Blend);',u.CustomMaterialOutputType.CMOT_FLOAT1,[('ApronRough','Rough')])]:
        node=next((e for e in mel.get_material_expressions(landscape) if isinstance(e,u.MaterialExpressionCustom) and str(e.get_editor_property('desc'))==label),None)
        if node is None:
            old=mel.get_material_property_input_node(landscape,prop);old_out=str(mel.get_material_property_input_node_output_name(landscape,prop))
            node=mel.create_material_expression(landscape,u.MaterialExpressionCustom);setprops(node,desc=label,output_type=kind)
            _inputs(node,['Old','Blend']);assert mel.connect_material_expressions(old,old_out,node,'Old')
        elif prop==u.MaterialProperty.MP_ROUGHNESS:
            # MudRunner MR1 (2026-10-08, found by a T3D export of M_VariantsLandscape): the wrapper was made reading the weather
            # call's FIRST output (BaseColor) as Old, so the strips' roughness outside the aprons was the colour's red channel
            # (about 0.1-0.3: a mirror sheen). Old is the weather call's Roughness output.
            names=[str(n) for n in mel.get_material_expression_input_names(node)];srcs=list(mel.get_inputs_for_material_expression(landscape,node))
            src=dict(zip(names,srcs)).get('Old')
            fn=src.get_editor_property('material_function') if isinstance(src,u.MaterialExpressionMaterialFunctionCall) else None
            if fn is not None and fn.get_name()=='MF_Weather':assert mel.connect_material_expressions(src,'Roughness',node,'Old'),'LiveApronRoughness Old'
        _inputs(node,[p for _o,p in pins]);node.set_editor_property('code',code)
        for out,pin in pins:assert mel.connect_material_expressions(mudtex,out,node,pin),label
        assert mel.connect_material_expressions(ground,'ClayBlend',node,'Blend');assert mel.connect_material_property(node,'',prop)
    errors=mel.recompile_material(landscape);assert not errors,str(errors);eal.save_loaded_asset(landscape)
    return {'material':landscape.get_path_name(),'apron':'the live patches\' boxes (MPC_TrackPaint), the variant slice, %.0f cm feather'%APRON_CM,'mudtex':facts,'compile_errors':list(errors),
            'mud_cover':mud_cover_on(landscape)}

# MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1, Art/Unreal/mud_cover.py): the carried mud (MF_MudCover) on a ground material, after
# the apron's wrappers so a rebuild keeps it; skipped until & Art/setup_mud_carry.ps1 has made MF_MudCover.
def mud_cover_on(mat,tangent=False):
    import mud_cover
    return mud_cover.wire_mud_cover(mat,tangent)

# LM2b (docs/LIVING_MUD_PLAN.md): the clods' material. The approved clay colour and normal bakes, tri-planar in world
# space at a 1.5 m scale (the ground's mirrored tiling at 6 m; chunks need smaller detail), roughness 0.85 dry to 0.45
# wet from MPC_Weather's Wetness, darker wet, a +-6 % tint per instance from PerInstanceRandom. World-space normals.
# LM2c: ten meshes; the tint +-12 % in value; a static freshness per instance from PerInstanceCustomData 0 (AGTMudPatch:
# a throw's clod 1, a bank clod 0.3), darker by FreshDarken and glossier toward FreshRough at 1 (proposed numbers).
# LM5b: the bog arrays' colour and normal in place of the clay, the slice from MudVariant (0 Standard; AGTMudPatch gives a
# variant patch's clods an instance with its own), one bake tile per ClodScaleCm (the bakes are true tiles: no mirror).
# Texture2DArraySample (Common.ush), not .Sample: a ray-tracing hit shader has no implicit derivatives (the first build failed
# on 'Opcode Sample not valid in shader model lib_6_6(closesthit)'); the helper takes mip 0 there.
CLOD_MATERIAL='/Game/GrandTour/Materials/M_GT_Clod'
CLOD_MESHES=['/Game/GrandTour/Mud/Clods/SM_GT_Clod_%d'%i for i in range(10)]
CLOD_SCALARS={'ClodScaleCm':150.0,'RoughDry':0.85,'RoughWet':0.45,'WetDarken':0.25,'TintRange':0.12,'FreshDarken':0.2,'FreshRough':0.5}
CLOD_HLSL='''float3 gn=normalize(VertexNormal);
float3 w=pow(abs(gn),4.0); w/=max(dot(w,1.0),0.0001);
float3 col=0; float3 det=0;
'''
for _axis,_coords,_weight,_normal in [('z','xy','z','float3(d.x,d.y,0)'),('y','xz','y','float3(d.x,0,d.y)'),('x','yz','x','float3(0,d.x,d.y)')]:
    CLOD_HLSL+='''{
float2 q=WorldPos.COORDS/max(ScaleCm,1.0);
float3 uvs=float3(q.x,-q.y,Slice);
float2 d=UnpackNormalMap(Texture2DArraySample(ClodN,ClodNSampler,uvs)).xy;
col+=w.WEIGHT*Texture2DArraySample(ClodC,ClodCSampler,uvs).rgb;
det+=w.WEIGHT*NORMAL;
}
'''.replace('COORDS',_coords).replace('WEIGHT',_weight).replace('NORMAL',_normal)
CLOD_HLSL+='''float wet=saturate(Wetness);
float fr=saturate(Fresh);
col*=(1.0+TintRange*(Rand*2.0-1.0))*(1.0-WetDarken*wet)*(1.0-FreshDarken*fr);
Rough=lerp(RoughDry,RoughWet,wet);
Rough=lerp(Rough,min(Rough,FreshRough),fr);
Nrm=normalize(gn+det);
return col;
'''

# MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5 execution block item 1): the mud chunks' material on M_GT_Clod's path - the same
# graph and numbers, the variant slice through MudVariant (AGTMudPatch's instance on a variant patch), freshness fixed at 0 (dry
# crust), the tint per chunk from its custom primitive data 0 (ChunkRand: a plain static mesh component has no per-instance random
# or custom data). For the chunks' own static mesh components (no instancing usage).
CHUNK_MATERIAL='/Game/GrandTour/Materials/M_GT_MudChunk'
CHUNK_MESHES=['/Game/GrandTour/Mud/Chunks/SM_GT_MudChunk_%d'%i for i in range(6)]

# Wheel spray P2 (docs/WHEEL_SPRAY_PLAN.md P2 item 4): the thrown mud blobs' clumps on the same path (spray=True) - freshness fixed at 1
# (wet), the variant slice from PerInstanceCustomData 0 (UGTSprayComponent: the slice of the patch the blob left), the scalars
# overridden by `scalars` (ClodScaleCm 25: a 2-6 cm clump shows the bake). Roughness: min(lerp(0.85, 0.45, wet), FreshRough 0.5).
SPRAY_CLUMP_MATERIAL='/Game/GrandTour/Materials/M_GT_SprayClump'
SPRAY_CLUMP_MESHES=['/Game/GrandTour/FX/Clumps/SM_GT_SprayClump_%d'%i for i in range(8)]

def build_clod_material(path=CLOD_MATERIAL,meshes=CLOD_MESHES,chunk=False,spray=False,scalars=None):
    assets=u.AssetToolsHelpers.get_asset_tools()
    mat=eal.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset(path.rsplit('/',1)[1],'/Game/GrandTour/Materials',u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property('tangent_space_normal',False)
    if not chunk:mel.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    custom=mel.create_material_expression(mat,u.MaterialExpressionCustom,-300,0)
    custom.set_editor_property('desc','Mud chunk surface (MR5, on the clod path)' if chunk else 'Spray clump surface (wheel spray P2, on the clod path)' if spray else 'Clod surface (LM2b, LM2c, LM5b)')
    values=dict(CLOD_SCALARS,**(scalars or {}))
    custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    names=['ClodC','ClodN','WorldPos','VertexNormal','Wetness','Rand','Fresh','Slice','ScaleCm','RoughDry','RoughWet','WetDarken','TintRange','FreshDarken','FreshRough']
    slots=[]
    for name in names:
        slot=u.CustomInput();slot.set_editor_property('input_name',name);slots.append(slot)
    custom.set_editor_property('inputs',slots)
    outputs=[]
    for name,kind in [('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1),('Nrm',u.CustomMaterialOutputType.CMOT_FLOAT3)]:
        o=u.CustomOutput();o.set_editor_property('output_name',name);o.set_editor_property('output_type',kind);outputs.append(o)
    custom.set_editor_property('additional_outputs',outputs)
    custom.set_editor_property('code',CLOD_HLSL)
    y=-600
    for name,array in [('ClodC','BogC'),('ClodN','BogN')]:
        node=mel.create_material_expression(mat,u.MaterialExpressionTextureObjectParameter,-900,y);y+=150
        node.set_editor_property('parameter_name',name);node.set_editor_property('texture',bog_array(array))
        node.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,BOG_SAMPLERS[array]))
        node.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        assert mel.connect_material_expressions(node,'',custom,name)
    wpos=mel.create_material_expression(mat,u.MaterialExpressionWorldPosition,-900,y);y+=150
    wpos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    assert mel.connect_material_expressions(wpos,'',custom,'WorldPos')
    vn=mel.create_material_expression(mat,u.MaterialExpressionVertexNormalWS,-900,y);y+=150
    assert mel.connect_material_expressions(vn,'',custom,'VertexNormal')
    wet=mel.create_material_expression(mat,u.MaterialExpressionCollectionParameter,-900,y);y+=150
    wet.set_editor_property('collection',eal.load_asset('/Game/GrandTour/Materials/MPC_Weather'));wet.set_editor_property('parameter_name','Wetness')
    assert mel.connect_material_expressions(wet,'',custom,'Wetness')
    if chunk:
        # MR5: the tint from the chunk's custom primitive data 0 (AGTMudPatch sets a random per chunk), the freshness 0.
        rand=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-900,y);y+=150
        rand.set_editor_property('parameter_name','ChunkRand');rand.set_editor_property('default_value',0.5)
        rand.set_editor_property('use_custom_primitive_data',True);rand.set_editor_property('primitive_data_index',0)
        fresh=mel.create_material_expression(mat,u.MaterialExpressionConstant,-900,y);y+=150
        fresh.set_editor_property('r',0.0)
    elif spray:
        # Wheel spray P2: wet (freshness 1); the slice comes from PerInstanceCustomData 0 below.
        rand=mel.create_material_expression(mat,u.MaterialExpressionPerInstanceRandom,-900,y);y+=150
        fresh=mel.create_material_expression(mat,u.MaterialExpressionConstant,-900,y);y+=150
        fresh.set_editor_property('r',1.0)
    else:
        rand=mel.create_material_expression(mat,u.MaterialExpressionPerInstanceRandom,-900,y);y+=150
        # LM2c: the freshness, PerInstanceCustomData 0 (a bank clod's 0.3 where no instance data is given).
        fresh=mel.create_material_expression(mat,u.MaterialExpressionPerInstanceCustomData,-900,y);y+=150
        fresh.set_editor_property('data_index',0);fresh.set_editor_property('const_default_value',0.3)
    assert mel.connect_material_expressions(rand,'',custom,'Rand')
    assert mel.connect_material_expressions(fresh,'',custom,'Fresh')
    # LM5b: the variant slice (AGTMudPatch's clod instance sets it; 0 Standard).
    if spray:
        # Wheel spray P2: the slice per blob, PerInstanceCustomData 0 (0 Standard where none is given).
        slice_=mel.create_material_expression(mat,u.MaterialExpressionPerInstanceCustomData,-900,y);y+=100
        slice_.set_editor_property('data_index',0);slice_.set_editor_property('const_default_value',0.0)
    else:
        slice_=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-900,y);y+=100
        slice_.set_editor_property('parameter_name','MudVariant');slice_.set_editor_property('default_value',0.0)
    assert mel.connect_material_expressions(slice_,'',custom,'Slice')
    for name,value in values.items():
        node=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-900,y);y+=100
        node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value)
        assert mel.connect_material_expressions(node,'',custom,'ScaleCm' if name=='ClodScaleCm' else name)
    assert mel.connect_material_property(custom,'',u.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(custom,'Rough',u.MaterialProperty.MP_ROUGHNESS)
    assert mel.connect_material_property(custom,'Nrm',u.MaterialProperty.MP_NORMAL)
    errors=mel.recompile_material(mat);assert not errors,str(errors);eal.save_loaded_asset(mat)
    assigned=[]
    for mesh_path in meshes:
        if eal.does_asset_exist(mesh_path):
            mesh=eal.load_asset(mesh_path);mesh.set_material(0,mat);eal.save_loaded_asset(mesh);assigned.append(mesh_path)
    return {'material':mat.get_path_name(),'scalars':values,'slice':'PerInstanceCustomData 0 (0 Standard)' if spray else 'MudVariant (0 Standard)','arrays':[DEST+'/'+BOG_ARRAYS['BogC'],DEST+'/'+BOG_ARRAYS['BogN']],'meshes':assigned,'compile_errors':list(errors),
            'fresh':'0 (MR5: dry crust)' if chunk else '1 (wet)' if spray else 'PerInstanceCustomData 0 (default 0.3)','rand':'ChunkRand (custom primitive data 0)' if chunk else 'PerInstanceRandom'}

# MudRunner MR3 (docs/MUDRUNNER_LESSONS_PLAN.md MR3 item 1, docs/MUD_VARIANTS.md "Muddy rut water"): churned rut water on
# M_GT_MudWater, a wrapper custom node after setup_m6_water's 'Mud water (PS)' on the colour, opacity and roughness (found or made
# on a rerun, never doubled; setup_m6_water rebuilds the material from scratch and this setup puts it back). AGTMudPatch gives the
# water's instance MudTread (A the field's Turbidity, B its Fresh) and MuddyWater (gt.Mud.MuddyWater).
# MR3b (the main session's look at Rut_Muddy / Rut_Settled: the froth read as spilt paint, settled and churned as the same flat
# brown): settled water (turbidity 0) is water - darker than the old tint, glossy, see-through at the rim, more of it at a grazing
# angle - and churned water (1) an opaque lighter mid-brown, rougher, lerped by turbidity; the froth is procedural bubbles (two
# jittered cellular layers, 1.6 and 0.72 cm cells, soft round, lighter at the centre with a glint) gathered in clumps by a 25 cm
# value noise, thinning toward the clumps' edges; past FrothNearCm the bubbles average into a soft tone. No splat atlas, no drips.
# MuddyWater 0 is still the water before MR3 exactly. Proposed starting points.
MUDDY_SCALARS={'MuddyWater':1.0,
               'SettledDarken':0.8,'SettledOpacity':0.6,'SettledRimOpacity':0.3,'SettledDeepCm':8.0,'SettledFresnel':0.45,
               'SettledRough':0.07,'SettledGlossRough':0.03,
               'TurbidLighten':2.3,'TurbidMottle':0.45,'TurbidMip':5.0,'TurbidTileCm':300.0,'TurbidOpacity':0.95,
               'TurbidRimOpacity':0.75,'TurbidOpaqueCm':3.0,'TurbidRough':0.35,
               'FrothTurbidLo':0.5,'FrothTurbidHi':0.85,'FrothAmount':1.0,'FrothClusterCm':25.0,'FrothClumpLo':0.35,'FrothClumpHi':0.75,
               'FrothBubbleCm':1.6,'FrothNearCm':400.0,'FrothFarCm':900.0,'FrothFarCover':0.55,'FrothGlint':0.35,'FrothRough':0.3,
               # MudRunner MRP item 1 (gt.Mud.PBR 1): water's F0 0.02 (UE Specular 0.25); settled 0.15 with a faint ripple normal (two
               # value-noise octaves, RippleCm and 0.43 x it, slopes up to about RippleSlope, drifting RippleSpeedCm a second); churned
               # 0.5; the froth (bubbles on water: foam) 0.6. The MR3b numbers above stay for gt.Mud.PBR 0.
               'WaterSpecular':0.25,'SettledRoughPBR':0.15,'TurbidRoughPBR':0.5,'FrothRoughPBR':0.6,
               'RippleCm':6.0,'RippleSlope':0.05,'RippleSpeedCm':0.6}
MUDDY_VECTORS={'FrothColor':(0.28,0.23,0.15),'BodyWarm':(1.08,0.95,0.78)}   # MRD1b: BodyWarm, the body's push toward orange-brown   # TurbidMean comes from the splat manifest (the Standard bog's mean)
MUDDY_RETIRED=['FrothTileCm','FrothLighten','MuddySplatter']   # MR3's splatter froth, removed from the graph on a rerun
MUDDY_DESC='Muddy water (MR3)'
# Mud and water MW1 item 3 (docs/MUD_WATER_SURFACE_PLAN.md, the owner's "the water is too static"), behind gt.Mud.WaterMotion
# (MPC_TrackPaint MudWaterMotion; with gt.Mud.PBR 1; 0 is the water before MW1 exactly):
# - the wind ruffle: two value-noise octaves (RuffleCm1 25, RuffleCm2 11 cm; slopes RuffleSlope1 0.12, RuffleSlope2 0.08), their
#   crests across the wind (stretched x1.8 along them), drifting RuffleSpeed1Cm 10 and RuffleSpeed2Cm 16 cm/s along MPC_Weather's
#   WindDirection (a fixed direction when it is unset) turned by a slow wander (+-0.37 rad over minutes); x a gust mask (cat's paws:
#   a GustCm 2.5 m noise drifting GustSpeedCm 60 cm/s with the wind, GustLo 0.3 to GustHi 1.6) and x EdgeCalm 0.4 where the water
#   is under EdgeCalmCm 2 cm deep; on top of the MRP ripple;
# - the settled roughness SettledRoughMW 0.2, up to RuffleRoughMW 0.3 in the gusts (churned and froth as before, F0 0.02);
# - the drift: the turbidity's mottle, the froth and a sparse fleck layer move DriftLoCm 3 to DriftHiCm 6 cm/s down the field's
#   slope (its height over +-DriftGradCm 60 cm, wider than a rut, so the walls cancel; the patch's long axis where it is flat),
#   as two phases DriftPeriodS 6 s apart cross-faded (the flow-map way: nothing smears however long it runs);
# - the flecks: straw bits and bubbles, dark or light specks of FleckRadLoCm 0.1-FleckRadHiCm 0.3 cm radius (2-6 mm), one chance
#   per FleckCm 3 cm cell, FleckDensLo 0.03 to FleckDensHi 0.2 of the cells by turbidity, faded out FleckNearCm 2.5 to FleckFarCm
#   6 m and below a pixel. Proposed numbers; the owner names them.
MW1_WATER_SCALARS={'RuffleCm1':25.0,'RuffleCm2':11.0,'RuffleSlope1':0.12,'RuffleSlope2':0.08,'RuffleSpeed1Cm':10.0,'RuffleSpeed2Cm':16.0,
                   'GustCm':250.0,'GustSpeedCm':60.0,'GustLo':0.3,'GustHi':1.6,'EdgeCalmCm':2.0,'EdgeCalm':0.4,
                   # MRD1 item 2: SettledRoughMW / RuffleRoughMW 0.2-0.3 -> 0.06-0.1 (Ref4: the sky reflects clearly).
                   'SettledRoughMW':0.06,'RuffleRoughMW':0.1,'DriftLoCm':3.0,'DriftHiCm':6.0,'DriftPeriodS':6.0,'DriftGradCm':60.0,
                   'FleckCm':3.0,'FleckDensLo':0.03,'FleckDensHi':0.2,'FleckRadLoCm':0.1,'FleckRadHiCm':0.3,'FleckNearCm':250.0,'FleckFarCm':600.0,
                   # MW1b items 4-5 (the main session: fingerprint-like swirl marks in the churned pool; its motion gate failed): the
                   # swirls were (a) the per-pixel drift - its direction from the field's slope varied across the pool, so the moving
                   # offsets warped the froth's bubbles and the mottle into arcs - and (b) the ruffle's crests stretched x1.8 across
                   # the wind, drawn as long diagonal bands on the churned water. Now the drift is one direction per patch (its long
                   # axis, the mean of DriftLoCm..HiCm: a pure translation, nothing bends; DriftGradCm is no longer read) and the
                   # ruffle isotropic; churned water ripples too, ChurnRippleSlope 0.15 (x turbidity, the finer octave weighted).
                   'ChurnRippleSlope':0.15}
# Mud roads MRD1b item 1 (the main session's look at MRD1: pale translucent oval lenses): an opaque turbid body (OpaqueBody, with
# gt.Mud.PBR) - the patch's variant mud tint (its bog slice's mean, the lowest mip, x0.8 off Deep: the spray's MudTintFor),
# saturated toward orange-brown (BodySaturation, x BodyWarm), at BodyOpacityLo..Hi 0.85-0.95 from BodyEdgeCm 1 cm deep (over
# BodyDeepCm), fading to 0 over the outer BodyEdgeCm, so the edge melts into wet mud with no rim; the sky's reflection on top is the
# PBR specular (F0 0.02) at the settled roughness 0.06-0.1 and MW1's ruffle. AGTMudPatch sets MudVariant on the water's instance.
# Proposed numbers; the owner names them. (MRD1's ShallowTurbidCm / ShallowTurbid are gone.)
MRD1B_WATER_SCALARS={'OpaqueBody':1.0,'MudVariant':0.0,'BodySaturation':1.6,'BodyBright':1.0,'BodyOpacityLo':0.85,'BodyOpacityHi':0.95,
                     'BodyEdgeCm':1.0,'BodyDeepCm':6.0}
MUDDY_HLSL='''// MudRunner MR3 / MR3b: rut water. Col/Op/Rgh are the rut water as it was; MuddyWater 0 with gt.Mud.PBR 0 returns them untouched
// (the water before MR3, exactly). Else settled (turbidity 0) water: Col x SettledDarken (the warm deep tint, darker), SettledOpacity
// in depth (SettledRimOpacity at the rim, so the floor shows there); churned (1): the Standard bog slice top-down TurbidMip mips down,
// toward its mean by TurbidMottle, x TurbidLighten, TurbidOpacity past TurbidOpaqueCm; lerped by turbidity (MudTread A). Froth where
// the cell is fresh (MudTread B) and turbid: procedural bubbles in clumps (see live_mud_style.py MR3b).
// MRP (gt.Mud.PBR 1, the PBR input): water's F0 0.02 (Spec, WaterSpecular 0.25), settled roughness SettledRoughPBR 0.15 with a faint
// ripple normal (Nrm, tangent space), churned TurbidRoughPBR 0.5, the froth FrothRoughPBR 0.6 - and no grazing-angle tricks: no
// SettledFresnel opacity, no fall to SettledGlossRough, no froth glint. gt.Mud.PBR 0: the MR3b water (Spec 0.5, the default; Nrm up).
// The ripple: the analytic gradient of two value-noise octaves (sin-free hash), the second turned and finer, both drifting.
// MW1 (gt.Mud.WaterMotion, Motion; with PBR): the wind ruffle with its gusts and calm edges, settled roughness 0.2-0.3, the mottle,
// froth and flecks drifting down the field's slope (live_mud_style.py MW1_WATER_SCALARS). Motion 0: the MRP water exactly.
struct GTRipple
{
    float Hash(float2 c)
    {
        float3 p3 = frac(float3(c.xyx) * 0.1031);
        p3 += dot(p3, p3.yzx + 33.33);
        return frac((p3.x + p3.y) * p3.z);
    }
    float2 Grad(float2 q)
    {
        float2 i = floor(q);
        float2 f = q - i;
        float2 w = f * f * (3.0 - 2.0 * f);
        float2 dw = 6.0 * f * (1.0 - f);
        float ha = Hash(i);
        float hb = Hash(i + float2(1.0, 0.0));
        float hc = Hash(i + float2(0.0, 1.0));
        float hd = Hash(i + float2(1.0, 1.0));
        float k = ha - hb - hc + hd;
        return dw * float2((hb - ha) + k * w.y, (hc - ha) + k * w.x);
    }
    float Value(float2 q)
    {
        float2 i = floor(q);
        float2 f = q - i;
        f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(Hash(i), Hash(i + float2(1.0, 0.0)), f.x), lerp(Hash(i + float2(0.0, 1.0)), Hash(i + float2(1.0, 1.0)), f.x), f.y);
    }
};
// MR3b's froth at a point p (MW1: a function of p, so the drift can move it; at the pixel's own p it is MR3b's exactly).
// Returns (the bubbles' cover, the centre shade, the glint, the clumps' density).
struct GTFroth
{
    float Fr; float Amount; float ClusterCm; float ClumpLo; float ClumpHi; float BubbleCm; float NearW;
    float4 Eval(float2 p)
    {
        // The clumps: a value noise at FrothClusterCm and a turned octave at 0.43 x it (sin-free hash).
        float cl = 0.0; float amp = 0.62; float2 q = p / max(ClusterCm, 1.0);
        [unroll] for (int o = 0; o < 2; ++o)
        {
            float2 i0 = floor(q); float2 f = frac(q); f = f * f * (3.0 - 2.0 * f);
            float4 hc = 0;
            [unroll] for (int c = 0; c < 4; ++c)
            {
                float2 ip = i0 + float2(c % 2, c / 2);
                float3 p3 = frac(ip.xyx * 0.1031); p3 += dot(p3, p3.yzx + 33.33);
                hc[c] = frac((p3.x + p3.y) * p3.z);
            }
            cl += amp * lerp(lerp(hc.x, hc.y, f.x), lerp(hc.z, hc.w, f.x), f.y);
            q = float2(0.8 * q.x - 0.6 * q.y, 0.6 * q.x + 0.8 * q.y) * 2.31 + 17.3; amp = 0.38;
        }
        float dens = saturate(Fr * Amount * smoothstep(ClumpLo, ClumpHi, cl));
        float foam = 0.0, centre = 0.0, glint = 0.0;
        if (dens > 0.001 && NearW > 0.001)
        {
            // Two jittered cellular layers (1 and 0.45 x FrothBubbleCm, the second turned): each cell's bubble a soft disc at a
            // random point, of a random size (smaller toward a clump's edge), shown when its own random number is under the density.
            [unroll] for (int s = 0; s < 2; ++s)
            {
                float cellCm = max(BubbleCm, 0.1) * (s == 0 ? 1.0 : 0.45);
                float2 pp = s == 0 ? p : float2(0.8 * p.x - 0.6 * p.y, 0.6 * p.x + 0.8 * p.y) + 37.0;
                float2 gq = pp / cellCm; float2 gi = floor(gq); float2 gf = frac(gq);
                [unroll] for (int k = 0; k < 9; ++k)
                {
                    float2 off = float2(k % 3 - 1, k / 3 - 1);
                    float3 h3 = frac(float3((gi + off).xyx) * float3(0.1031, 0.1030, 0.0973) + 0.37 * s);
                    h3 += dot(h3, h3.yzx + 33.33);
                    h3 = frac((h3.xxy + h3.yzz) * h3.zyx);
                    float2 ctr = off + 0.15 + 0.7 * h3.xy;
                    float rad = lerp(0.22, 0.5, h3.z) * lerp(0.65, 1.0, dens);
                    float show = step(frac(h3.z * 7.13 + h3.x * 3.1), dens * (s == 0 ? 1.0 : 0.8));
                    float dist = length(gf - ctr);
                    float b = (1.0 - smoothstep(rad * 0.45, rad, dist)) * show;
                    if (b > foam)
                    {
                        foam = b;
                        centre = saturate(1.0 - dist / max(rad, 0.001));
                        glint = (1.0 - smoothstep(0.0, rad * 0.3, length(gf - ctr - float2(-0.3, 0.3) * rad))) * show;
                    }
                }
            }
        }
        return float4(foam, centre, glint, dens);
    }
};
float mwPix = length(fwidth(WorldPos.xy));   // MW1: cm a pixel (the flecks fade under it)
Opacity = Op; Rough = Rgh; Nrm = float3(0.0, 0.0, 1.0); Spec = 0.5;
// MRD1c: the masked water's dither - interleaved gradient noise on the pixel, turned each of 8 frames (TSR blends it).
float mrdDither = frac(52.9829189 * frac(dot(Parameters.SvPosition.xy + 5.588238 * float(View.StateFrameIndexMod8), float2(0.06711056, 0.00583715))));
Mask = Op > mrdDither ? 1.0 : 0.0;
bool pbr = PBR > 0.5;
if (MuddyWater <= 0.0 && !pbr) { return Col; }
bool mw = pbr && Motion > 0.5;
float2 uv = saturate((WorldPos.xy - PatchMin.xy) / max(PatchSize.xy, 1.0));
float4 tr = Texture2DSampleLevel(Tread, TreadSampler, uv, 0);
float turb = saturate(tr.a) * saturate(MuddyWater);
float mudCm = Texture2DSampleLevel(Field, FieldSampler, uv, 0).r * 100.0;
float d = TableCm - mudCm;
float edge = saturate(d / max(EdgeFadeCm, 0.05));
float3 nrm = normalize(VertexNormal.xyz);
float3 vw = normalize(CameraVec.xyz);
float fres = pow(1.0 - saturate(abs(dot(nrm, vw))), 5.0);
float3 col = Col * SettledDarken;
float a = edge * saturate(lerp(SettledRimOpacity, SettledOpacity, saturate(d / max(SettledDeepCm, 0.1))) + (pbr ? 0.0 : SettledFresnel * fres));
float r = pbr ? SettledRoughPBR : lerp(SettledRough, SettledGlossRough, fres);
// MW1 item 3c / MW1b item 4: the drift - one direction per patch (its long axis; a per-pixel direction from the field's slope
// warped the froth and the mottle into arcs), the mean of DriftLoCm..HiCm, two phases cross-faded (a pure translation).
float2 off0 = float2(0.0, 0.0);
float2 off1 = float2(0.0, 0.0);
float fw0 = 1.0;
if (mw)
{
    float2 axis = PatchSize.x >= PatchSize.y ? float2(1.0, 0.0) : float2(0.0, 1.0);
    float2 flow = axis * 0.5 * (DriftLoCm + DriftHiCm);
    float per = max(DriftPeriodS, 0.5);
    float ph0 = frac(Time / per);
    float ph1 = frac(Time / per + 0.5);
    off0 = flow * ph0 * per;
    off1 = flow * ph1 * per + float2(37.0, 19.0);   // the second phase also shifted, so the two never coincide
    fw0 = 1.0 - abs(2.0 * ph0 - 1.0);
}
if (pbr)
{
    GTRipple Rp;
    float rc = max(RippleCm, 0.5);
    float2 rq = (WorldPos.xy + Time * RippleSpeedCm * float2(0.8, 0.6)) / rc;
    float2 rq2 = float2(0.6 * rq.x - 0.8 * rq.y, 0.8 * rq.x + 0.6 * rq.y) / 0.43 + 11.0 - Time * RippleSpeedCm * float2(0.3, -0.7) / rc;
    float2 g = (Rp.Grad(rq) + 0.6 * Rp.Grad(rq2)) / 1.6;
    float2 slope = RippleSlope * g;
    if (mw)
    {
        // MW1 item 3a/b: the wind ruffle, its gusts and the calm edges; the settled roughness 0.2 to 0.3 in the gusts.
        float2 wd = WindDir.xy;
        wd = dot(wd, wd) > 1e-4 ? normalize(wd) : float2(0.8, 0.6);
        float wa = 0.25 * sin(Time * 0.05 + 1.3) + 0.12 * sin(Time * 0.13 + 0.4);
        wd = float2(cos(wa) * wd.x - sin(wa) * wd.y, sin(wa) * wd.x + cos(wa) * wd.y);
        float2 wp = float2(-wd.y, wd.x);
        float2 gq = (WorldPos.xy - wd * GustSpeedCm * Time) / max(GustCm, 1.0);
        float gn = 0.65 * Rp.Value(gq) + 0.35 * Rp.Value(float2(0.8 * gq.x - 0.6 * gq.y, 0.6 * gq.x + 0.8 * gq.y) * 2.3 + 5.1);
        float gust = lerp(GustLo, GustHi, smoothstep(0.25, 0.75, gn));
        float calm = lerp(EdgeCalm, 1.0, smoothstep(0.0, max(EdgeCalmCm, 0.01), d));
        float k = gust * calm;
        float2 p1 = WorldPos.xy - wd * RuffleSpeed1Cm * Time;
        float2 p2 = WorldPos.xy - wd * RuffleSpeed2Cm * Time + 23.0;
        // MW1b item 4: isotropic (the crests stretched x1.8 across the wind drew long diagonal bands on the churned water).
        float2 h1 = Rp.Grad(p1 / max(RuffleCm1, 0.5));
        float2 h2 = Rp.Grad(p2 / max(RuffleCm2, 0.5) + 7.0);
        slope += k * (RuffleSlope1 * h1 + RuffleSlope2 * h2);
        // MW1b item 5: churned water ripples too, ChurnRippleSlope x turbidity, the finer octave weighted (it moves most in 0.5 s).
        slope += turb * ChurnRippleSlope * (0.35 * h1 + 0.65 * h2);
        r = lerp(SettledRoughMW, RuffleRoughMW, saturate(k - 0.6));
    }
    Nrm = normalize(float3(-slope, 1.0));
    Spec = WaterSpecular;
}
// MRD1b item 1: the opaque turbid body (live_mud_style.py MRD1B_WATER_SCALARS); the reflection is the specular above.
if (pbr && OpaqueBody > 0.5)
{
    float3 mt = BogC.SampleLevel(BogCSampler, float3(0.5, 0.5, MudVariant), 11.0).rgb * (abs(MudVariant - 2.0) < 0.5 ? 1.0 : 0.8);
    float ml = dot(mt, float3(0.2126, 0.7152, 0.0722));
    col = max(lerp(ml.xxx, mt, BodySaturation), 0.0) * BodyWarm.rgb * BodyBright;
    a = smoothstep(0.0, max(BodyEdgeCm, 0.05), d) * lerp(BodyOpacityLo, BodyOpacityHi, saturate((d - BodyEdgeCm) / max(BodyDeepCm, 0.1)));
}
if (turb > 0.001)
{
    float3 bog = BogC.SampleLevel(BogCSampler, float3((WorldPos.xy - off0) / max(TurbidTileCm, 1.0), 0.0), TurbidMip).rgb;
    if (mw)
    {
        float3 bog1 = BogC.SampleLevel(BogCSampler, float3((WorldPos.xy - off1) / max(TurbidTileCm, 1.0), 0.0), TurbidMip).rgb;
        bog = lerp(bog1, bog, fw0);
    }
    float3 brown = lerp(TurbidMean.rgb, bog, TurbidMottle) * TurbidLighten;
    float aT = edge * lerp(TurbidRimOpacity, TurbidOpacity, saturate(d / max(TurbidOpaqueCm, 0.1)));
    col = lerp(col, brown, turb);
    a = lerp(a, max(a, aT), turb);
    r = lerp(r, pbr ? TurbidRoughPBR : TurbidRough, turb);
    float fr = saturate(tr.b) * smoothstep(FrothTurbidLo, FrothTurbidHi, turb);
    if (fr > 0.001)
    {
        GTFroth Fz;
        Fz.Fr = fr; Fz.Amount = FrothAmount; Fz.ClusterCm = FrothClusterCm; Fz.ClumpLo = FrothClumpLo; Fz.ClumpHi = FrothClumpHi;
        Fz.BubbleCm = FrothBubbleCm; Fz.NearW = 1.0 - smoothstep(FrothNearCm, FrothFarCm, length(WorldPos - CamPos));
        float4 e = Fz.Eval(WorldPos.xy - off0);
        // Far away the bubbles average into a soft tone (no shimmer).
        float froth = lerp(e.w * FrothFarCover, e.x, Fz.NearW);
        float centre = e.y;
        float glint = e.z;
        if (mw)
        {
            float4 e1 = Fz.Eval(WorldPos.xy - off1);
            froth = lerp(lerp(e1.w * FrothFarCover, e1.x, Fz.NearW), froth, fw0);
            centre = lerp(e1.y, centre, fw0);
            glint = lerp(e1.z, glint, fw0);
        }
        float3 fc = FrothColor.rgb * (0.88 + 0.24 * centre * Fz.NearW) + (pbr ? 0.0 : FrothGlint * glint * Fz.NearW);
        col = lerp(col, fc, froth);
        a = lerp(a, max(a, edge), froth);
        r = lerp(r, pbr ? FrothRoughPBR : FrothRough, froth);
    }
}
if (mw)
{
    // MW1 item 3c: the flecks (straw bits, bubbles), one chance a FleckCm cell, drifting with the rest; under a pixel they fade.
    float fade = (1.0 - smoothstep(FleckNearCm, FleckFarCm, length(WorldPos - CamPos))) * edge;
    if (fade > 0.001)
    {
        float dens = lerp(FleckDensLo, FleckDensHi, turb);
        float cell = max(FleckCm, 0.5);
        float aa = max(mwPix / cell, 1e-4);
        float sp = 0.0;
        float3 fsum = float3(0.0, 0.0, 0.0);
        [unroll] for (int ph = 0; ph < 2; ++ph)
        {
            float2 fq = (WorldPos.xy - (ph == 0 ? off0 : off1)) / cell;
            float2 ci = floor(fq);
            float2 cf = fq - ci;
            float3 h3 = frac(float3(ci.xyx) * float3(0.1031, 0.1030, 0.0973) + 0.71);
            h3 += dot(h3, h3.yzx + 33.33);
            h3 = frac((h3.xxy + h3.yzz) * h3.zyx);
            float rad = lerp(FleckRadLoCm, FleckRadHiCm, frac(h3.z * 17.3)) / cell;
            float b = (1.0 - smoothstep(rad - aa, rad + aa, length(cf - (0.15 + 0.7 * h3.xy)))) * step(h3.z, dens) * saturate(rad / aa);
            float w = ph == 0 ? fw0 : 1.0 - fw0;
            sp += w * b;
            fsum += w * b * (frac(h3.x * 7.7) < 0.55 ? float3(0.022, 0.018, 0.013) : float3(0.30, 0.26, 0.18));
        }
        float k = saturate(sp) * fade;
        col = lerp(col, fsum / max(sp, 1e-4), k);
        a = lerp(a, max(a, 0.9 * edge), k);
        r = lerp(r, 0.5, k);
    }
}
Opacity = a; Rough = r; Mask = a > mrdDither ? 1.0 : 0.0;
return col;
'''

def muddy_water(mat):
    import mud_cover
    nodes=list(mel.get_material_expressions(mat))
    def custom_by(desc):
        return next((e for e in nodes if isinstance(e,u.MaterialExpressionCustom) and str(e.get_editor_property('description'))==desc),None)
    base=custom_by('Mud water (PS)');assert base is not None,'M_GT_MudWater has no Mud water (PS) node (run Art/setup_m6_water.bat)'
    wrap=custom_by(MUDDY_DESC)
    if wrap is None:
        wrap=mel.create_material_expression(mat,u.MaterialExpressionCustom,-250,200);wrap.set_editor_property('description',MUDDY_DESC)
    wrap.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    mud_cover.custom_slots(wrap,['Col','Op','Rgh','WorldPos','PatchMin','PatchSize','Field','Tread','TableCm','EdgeFadeCm','CameraVec','VertexNormal','CamPos',
                                 'BogC','TurbidMean','PBR','Time','Motion','WindDir']+list(MUDDY_VECTORS)+list(MUDDY_SCALARS)+list(MW1_WATER_SCALARS)+list(MRD1B_WATER_SCALARS),
                           [('Opacity',u.CustomMaterialOutputType.CMOT_FLOAT1),('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1),
                            ('Nrm',u.CustomMaterialOutputType.CMOT_FLOAT3),('Spec',u.CustomMaterialOutputType.CMOT_FLOAT1),
                            ('Mask',u.CustomMaterialOutputType.CMOT_FLOAT1)])   # MRD1c: the dithered opacity mask
    wrap.set_editor_property('code',MUDDY_HLSL)
    con=mud_cover.connect
    con(base,'',wrap,'Col');con(base,'Opacity',wrap,'Op');con(base,'Rough',wrap,'Rgh')
    # MR3b: MR3's splatter froth parameters leave the graph.
    retired=[]
    for e in list(nodes):
        if isinstance(e,(u.MaterialExpressionScalarParameter,u.MaterialExpressionTextureObjectParameter)) and str(e.get_editor_property('parameter_name')) in MUDDY_RETIRED:
            retired.append(str(e.get_editor_property('parameter_name')));mel.delete_material_expression(mat,e);nodes.remove(e)
    # The base's own inputs, by their parameters and classes (setup_m6_water's), so the wrapper reads the same field, table, rim and view.
    found={}
    for pin,cls,name in [('WorldPos',u.MaterialExpressionWorldPosition,None),('PatchMin',u.MaterialExpressionVectorParameter,'PatchMin'),
                         ('PatchSize',u.MaterialExpressionVectorParameter,'PatchSize'),('Field',u.MaterialExpressionTextureObjectParameter,'MudField'),
                         ('TableCm',u.MaterialExpressionScalarParameter,'WaterTableCm'),('EdgeFadeCm',u.MaterialExpressionScalarParameter,'EdgeFadeCm'),
                         ('CameraVec',u.MaterialExpressionCameraVectorWS,None),('VertexNormal',u.MaterialExpressionVertexNormalWS,None)]:
        node=_find(nodes,cls,parameter_name=name) if name else _find(nodes,cls)
        assert node is not None,'M_GT_MudWater has no %s'%(name or pin)
        con(node,'',wrap,pin);found[pin]=node.get_name()
    y=[1700]
    def place():
        y[0]+=110;return y[0]
    cam=_find(nodes,u.MaterialExpressionCameraPositionWS)
    if cam is None:cam=mel.create_material_expression(mat,u.MaterialExpressionCameraPositionWS,-700,place());nodes.append(cam)
    con(cam,'',wrap,'CamPos')
    # MRP: gt.Mud.PBR (MPC_TrackPaint MudPBR) and the time for the ripple's drift.
    con(mpc_node(mat,nodes,'MudPBR','LiveMud:pbr',-700,place()),'',wrap,'PBR')
    clock=_find(nodes,u.MaterialExpressionTime)
    if clock is None:clock=mel.create_material_expression(mat,u.MaterialExpressionTime,-700,place());nodes.append(clock)
    con(clock,'',wrap,'Time')
    # MW1: gt.Mud.WaterMotion (MPC_TrackPaint MudWaterMotion) and the wind's heading (MPC_Weather WindDirection; this material's
    # second collection, the limit is two).
    con(mpc_node(mat,nodes,'MudWaterMotion','LiveMud:watermotion',-700,place()),'',wrap,'Motion')
    wind=_find(nodes,u.MaterialExpressionCollectionParameter,desc='LiveMud:winddir')
    if wind is None:
        wind=mel.create_material_expression(mat,u.MaterialExpressionCollectionParameter,-700,place());nodes.append(wind);wind.set_editor_property('desc','LiveMud:winddir')
    wind.set_editor_property('collection',eal.load_asset(WEATHER_MPC));wind.set_editor_property('parameter_name','WindDirection')
    con(wind,'',wrap,'WindDir')
    rt=eal.load_asset('/Game/GrandTour/Terrain/RT_TrackPaint');assert rt,'no RT_TrackPaint (the tread parameter needs a linear default)'
    for pin,param,tex,sampler,shared in [('Tread','MudTread',rt,'SAMPLERTYPE_LINEAR_COLOR',False),('BogC','LiveMud_BogC',bog_array('BogC'),'SAMPLERTYPE_COLOR',True)]:
        node=_find(nodes,u.MaterialExpressionTextureObjectParameter,parameter_name=param)
        if node is None:node=mel.create_material_expression(mat,u.MaterialExpressionTextureObjectParameter,-700,place());nodes.append(node)
        node.set_editor_property('parameter_name',param);node.set_editor_property('texture',tex)
        node.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,sampler))
        if shared:node.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        con(node,'',wrap,pin)
    mean=mud_cover.dry_mud_colour()
    for name,value in [('TurbidMean',tuple(mean))]+list(MUDDY_VECTORS.items()):
        node=_find(nodes,u.MaterialExpressionVectorParameter,parameter_name=name)
        if node is None:node=mel.create_material_expression(mat,u.MaterialExpressionVectorParameter,-700,place());nodes.append(node)
        node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',u.LinearColor(value[0],value[1],value[2],1.0))
        con(node,'',wrap,name)
    for name,value in list(MUDDY_SCALARS.items())+list(MW1_WATER_SCALARS.items())+list(MRD1B_WATER_SCALARS.items()):   # MRD1b: the body
        node=_find(nodes,u.MaterialExpressionScalarParameter,parameter_name=name)
        if node is None:node=mel.create_material_expression(mat,u.MaterialExpressionScalarParameter,-700,place());nodes.append(node)
        node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value)
        con(node,'',wrap,name)
    for out,prop in [('',u.MaterialProperty.MP_BASE_COLOR),('Opacity',u.MaterialProperty.MP_OPACITY),('Rough',u.MaterialProperty.MP_ROUGHNESS),
                     ('Nrm',u.MaterialProperty.MP_NORMAL),('Spec',u.MaterialProperty.MP_SPECULAR)]:
        assert mel.connect_material_property(wrap,out,prop),'connect %r -> %s'%(out,prop)
    # Mud roads MRD1c item 1: the rut water MASKED (opaque), so it takes the mud's Lumen and screen-space reflections (the
    # translucent body read matte and darker than the wet mud); its opacity (the body's 0.85-0.95, faded over the outer 1 cm) goes
    # through a temporal dither (the wrapper's Mask: interleaved gradient noise on the pixel, turned each of 8 frames for TSR to
    # blend) into the opacity mask, so the edge melts in with no rim. Base colour, F0 0.02 (Spec), roughness 0.06-0.1 and the
    # ruffle's normal as before. Lost with it: the see-through rim of settled water (MR3b) and blended froth.
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    assert mel.connect_material_property(wrap,'Mask',u.MaterialProperty.MP_OPACITY_MASK),'MRD1c: Mask -> Opacity Mask'
    # MR3b item 2: LM5b's far gloss fade is the mud's and the landscape's (wire_bog), never this material's: say so from the graph.
    far=[str(e.get_editor_property('parameter_name')) for e in nodes if isinstance(e,(u.MaterialExpressionScalarParameter,u.MaterialExpressionStaticSwitchParameter))
         and str(e.get_editor_property('parameter_name')) in ('FarGlossFade','FarGlossNearCm','FarGlossFarCm','FarGlossRough')]
    errors=[str(e) for e in mel.recompile_material(mat)];eal.save_loaded_asset(mat)
    assert not errors,'M_GT_MudWater (MR3): %s'%errors
    return {'material':mat.get_path_name(),'muddy_water':MUDDY_DESC,'turbid_mean':mean,'vectors':MUDDY_VECTORS,'scalars':MUDDY_SCALARS,'inputs_from':found,
            'retired':retired,'far_gloss_fade_params_on_water':far,'blend_mode':str(mat.get_editor_property('blend_mode')),'pbr':'gt.Mud.PBR (MudPBR): Specular, ripple Normal (tangent %s), settled/churned/froth roughness'%mat.get_editor_property('tangent_space_normal'),
            'compile_errors':errors}

def apply_existing():
    # LM5b: MPC_TrackPaint's PatchVariant0..3 first, so the landscape's apron can read them when it compiles.
    facts=[ensure_patch_variants()]
    for name,landscape in [('M_GT_Mud',False),('M_GT_Landscape',True)]:
        path='/Game/GrandTour/Materials/'+name;backup=DEST+'/BeforeLive_'+name
        if not eal.does_asset_exist(backup):assert eal.duplicate_asset(path,backup)
        facts.append(attach(eal.load_asset(path),landscape))
        if landscape:facts.append(mud_cover_on(eal.load_asset(path)))   # MR1
    # The older near-black puddle tint reads as a cutout against the approved warm clay.
    # These are shading-only defaults; depth, water level and simulation remain unchanged.
    name='M_GT_MudWater';path='/Game/GrandTour/Materials/'+name;backup=DEST+'/BeforeLive_'+name
    if not eal.does_asset_exist(backup):assert eal.duplicate_asset(path,backup)
    water=eal.load_asset(path)
    # MRD1: the rut-water wrapper first (MudRunner MR3, MW1, MRD1), so a saved wrapper that does not compile (an input it reads gone)
    # is rebuilt before the defaults' recompile below asserts on it.
    muddy=muddy_water(water)
    scalar_values={'DeepOpacity':.78,'WaterRoughness':.12,'GlossRoughness':.08}
    found=set()
    for e in mel.get_material_expressions(water):
        if isinstance(e,u.MaterialExpressionScalarParameter):
            key=str(e.get_editor_property('parameter_name'))
            if key in scalar_values:e.set_editor_property('default_value',scalar_values[key]);found.add(key)
        elif isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='DeepColor':
            e.set_editor_property('default_value',u.LinearColor(.060,.041,.025,1));found.add('DeepColor')
    assert found==set(scalar_values)|{'DeepColor'},str(found)
    errors=mel.recompile_material(water);assert not errors,str(errors);eal.save_loaded_asset(water)
    facts.append({'material':water.get_path_name(),'deep_color':[.060,.041,.025],'scalars':scalar_values,'compile_errors':list(errors)})
    facts.append(muddy)   # MudRunner MR3: churned rut pools
    # LM2b: the clods' material, owned by the live setup (and put on the clod meshes when they are imported).
    facts.append(build_clod_material())
    # MudRunner MR5: the mud chunks' material on the same path.
    facts.append(build_clod_material(CHUNK_MATERIAL,CHUNK_MESHES,chunk=True))
    return facts
