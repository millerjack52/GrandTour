"""Isolated first-pass Big Mountain level. Existing Benmore assets remain read-only."""
import unreal as u
import json,sys,time,traceback,hashlib,array,re,shutil,math,gc
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props,Graph
import lidar_firm_roads
OUT=ROOT/'Art/Export/LidarStudy/Place';BASE='/Game/GrandTour/ArtTests/LidarStudy';LEVEL=BASE+'/L_LidarStudy'
OLD='/Game/GrandTour/ArtTests/BenmoreWoodland'
KIT='/Game/GrandTour/Environment/NativePlants/v01'
def understory_class(name):
 # LP3 cull distances (cm, start/end) by plant class: crown fern, litter, hummocks and tussock 60/90 m; tree ferns, logs, stumps, kiokio 120/180 m; margin scrub and flax 150/220 m.
 n=name.replace('SM_NZ_','')
 if n.startswith(('TreeFern','Log_','Stump','Kiokio')):return 12000,18000
 if n.startswith(('Coprosma','Gorse','Broom','Harakeke')):return 15000,22000
 return 6000,9000
def hull_count(mesh):return len(mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('convex_elems'))
TEMPLATE='/Game/GrandTour/ArtTests/ProceduralGround'
# LP3c: forest-floor peat in the LiDAR ground materials and the kit tint instances. The Install fast path (skip when the inputs digest matches) also
# requires this version, so the first Install after a change here rebuilds the level and every later Install is quick again.
LP3C='lp3c-2'
PEAT_MARK='// LP3c forest-floor peat'
PEAT_OLD='return pow(max(rich,0),2.2);'
# Replaces the final line of the colour program shared by M_Terrain and M_Detail. style is the LiDAR atlas (R sand, G grass, B wet, A rock),
# rich the grass/sand/dirt blend in gamma space, grain the program's own value-noise helper and materialXY its world position.
# Peat colour and litter are LINEAR albedo, so the blend is applied after the pow(2.2). Detail octaves fade with camera distance so far peat is flat.
PEAT_NEW=PEAT_MARK+''' (style B wet over .55, not grass, not the river bed in A): dark peat with litter flecks, linear albedo
float peatRock=1-smoothstep(.6,.95,style.a);
float peatMask=saturate((style.b-.55)*3)*(1-style.g)*peatRock;
float peatD=length(Camera.xy-P.xy)*.01;
float peatF1=1-saturate((peatD-30)/90),peatF2=1-saturate((peatD-12)/38),peatF3=1-saturate((peatD-6)/14);
float peatN=.1*lerp(.5,grain.noise(materialXY/37.+7.),peatF1)+.5*lerp(.5,grain.noise(materialXY/11.+17.),peatF2)+.4*lerp(.5,grain.noise(materialXY/3.7+41.),peatF3);
float3 peatCol=float3(.045,.034,.024)*lerp(.6,1.4,saturate(peatN));
peatCol=lerp(peatCol,float3(.14,.10,.05),lerp(.025,smoothstep(.70,.76,peatN)*.5,peatF2));
return lerp(pow(max(rich,0),2.2),peatCol,peatMask);'''
def peat_patch(code):
 """Idempotent: adds the peat block to the colour program once; returns (code, changed)."""
 if PEAT_MARK in code or PEAT_OLD not in code:return code,False
 assert code.count(PEAT_OLD)==1,'colour program final line is not unique'
 return code.replace(PEAT_OLD,PEAT_NEW),True
# LP3d (docs/LIDAR_PLACE_PLAN.md): grazed pasture in the LiDAR ground materials (owner photo 09). The block REPLACES the final line of the colour program (the peat return, which is itself the program's last line),
# so it sits upstream of CL1Colour: clay wins wherever the clay atlas R is above 0, and the rock mix (style A) and the LidarCoverTint wrapper still follow. style is the LiDAR atlas, grain the program's own value-noise
# helper, materialXY the world position, Camera the camera position; all colours are LINEAR albedo, applied after the pow(2.2) (peat and clay are authored the same way).
# Weight: smoothstep(.3,.8,style G) so G over .8 is full pasture and G .3 to .8 blends back to the existing olive (rank grass at the bush edge and verge); sand (style R) and peat keep their own colour.
# Variation: two noise scales (2.5 m and 0.4 m, +-20% at the noise extremes, contrast-stretched so it reads) with the fine octave fading out beyond 40 m; about 8% of the pasture is lighter, mown-looking (.12,.26,.06). LP3e warmed both: pasture (.12,.21,.04), mown (.15,.25,.05) (photo 09 R/G about .77).
# GP2b (docs/LIDAR_PLACE_PLAN.md): the noise is now three independent octaves, 2.5 m (+-24%, unchanged), 0.4 m (+-35%, was +-20%, fades out between 10 and 40 m) and a new 0.12 m blade-speckle octave (+-15%, fades out between 4 and 12 m);
# pasture (.11,.20,.045), mown (.14,.24,.055) (was .12,.21,.04 / .15,.25,.05). The 15% desaturation stays.
LP3D='lp3d-3'   # GP2c: the colour program keeps only its pre-pasture ground colour (the GP2b noise octaves, pasture/mown colours and the 15% desaturation are gone); the tiled pasture is the GP2cPasture node (GP2C below)
# LP3e (docs/LIDAR_PLACE_PLAN.md): warmer pasture numbers (above) and a darker tint instance on the beech canopy foliage slots (SM_Canopy_0..2; the spar keeps its bark tint). The Install fast path also
# requires this version, so the first Install after a change here rebuilds the level (the ground clones persist, pasture_patch rewrites their block) and every later Install is quick again.
LP3E='lp3e-1'
CANOPY_TINT=(.55,.62,.50);CANOPY_KINDS=(0,1,2)
# GP2 (docs/LIDAR_PLACE_PLAN.md GP1-GP3): the streamed grass draws clump meshes (GTMixedGroundDetails clump mode, console variable gt.Grass.Clumps) instead of single cards. The ground pasture colour above
# is mixed 15% toward its luminance (the colour block's last lines), and the grass actor gets PastureClumpMesh, RankClumpMesh, ClumpSpacingCm and the card-fallback spacing (set_clump_props, shared with Polish,
# which builds M_LidarClump / M_LidarRank and assigns the materials). The Install fast path also requires this version, so the first Install after a change here rebuilds the level.
GP2='gp4b-1'   # GP4b: the pasture is the three SM_NZ_GrassPatch meshes on a 55 cm lattice (GP2d was PastureClump_L at 40 cm); the rank band keeps RankClump_A
# GP4b (docs/LIDAR_PLACE_PLAN.md GP4): dense grass. PastureClumpMesh / B / C = SM_NZ_GrassPatch_A / B / C (70 x 70 cm patches, vertex colour dark base to bright tip, vertex alpha 0 base to 1 tip), one ISM component each, picked per lattice
# cell by a hash; patches overlap at ClumpSpacingCm 55 for full coverage. Scale .8 to 1.25 (hash plus the 2.5 m value noise), random yaw. Streaming out to 40 m, cull 30 to 38 m (the grass materials fade by PerInstanceFadeAmount, which the
# cull distances drive), LOD1 at 10 m and LOD2 at 22 m (the patch meshes' LOD2 screen size is set so their LOD1 and LOD2 screen sizes give that ratio). gt.Grass.Clumps 0 still restores the cards (GrassSpacingCm CARD_SPACING_CM).
CLUMP_PASTURE=('SM_NZ_GrassPatch_A','SM_NZ_GrassPatch_B','SM_NZ_GrassPatch_C');CLUMP_RANK='SM_NZ_RankClump_A';CLUMP_SPACING_CM=55.;CARD_SPACING_CM=45.
CLUMP_SCALE=(.8,1.25);CLUMP_STREAM_RADIUS_CM=4000.;CLUMP_LOD_CM=(1000.,2200.);GRASS_CULL_CM=(3000.,3800.)
def set_patch_lod_screen_sizes(meshes):
 """GP4b: the GPU LOD selection has one distance scale per component (C++ derives it from the LOD1 screen size so LOD1 lands at CLUMP_LOD_CM[0]); LOD2 then lands at LOD1 x (screen1 / screen2), so each patch mesh's LOD2 screen size
 is set to screen1 x CLUMP_LOD_CM[0] / CLUMP_LOD_CM[1] (the asset is saved only when it changes). Returns the sizes before and after per mesh."""
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);out={}
 for m in meshes:
  cur=[float(v) for v in sm.get_lod_screen_sizes(m)];assert len(cur)>=3,('GP4b: patch mesh needs 3 LODs',m.get_name(),cur)
  want=cur[:2]+[round(cur[1]*CLUMP_LOD_CM[0]/CLUMP_LOD_CM[1],4)]+cur[3:]
  if abs(cur[2]-want[2])>1e-4:
   assert sm.set_lod_screen_sizes(m,want),m.get_name();assert assets.save_loaded_asset(m,False),m.get_name()   # only_if_is_dirty False: the screen-size edit does not dirty the package, and a plain save skipped it
  out[m.get_name()]=dict(before=cur,after=[float(v) for v in sm.get_lod_screen_sizes(m)])
 return out
def set_clump_props(grass):
 """Sets the pasture patch meshes, the rank mesh, the clump lattice spacing, scale, streaming radius, LOD and cull distances and the card-fallback spacing on the streamed grass actor; returns what it set."""
 pms=[u.load_asset(KIT+'/'+n) for n in CLUMP_PASTURE];rm=u.load_asset(KIT+'/'+CLUMP_RANK);assert rm and all(pms),('GP4b meshes missing',CLUMP_PASTURE,CLUMP_RANK,[bool(m) for m in pms])
 lod=set_patch_lod_screen_sizes(pms)
 props(grass,pasture_clump_mesh=pms[0],pasture_clump_mesh_b=pms[1],pasture_clump_mesh_c=pms[2],rank_clump_mesh=rm,clump_spacing_cm=CLUMP_SPACING_CM,clump_scale_min=CLUMP_SCALE[0],clump_scale_max=CLUMP_SCALE[1],clump_stream_radius_cm=CLUMP_STREAM_RADIUS_CM,
  clump_lod1_distance_cm=CLUMP_LOD_CM[0],clump_lod2_distance_cm=CLUMP_LOD_CM[1],grass_cull_start_cm=GRASS_CULL_CM[0],grass_cull_end_cm=GRASS_CULL_CM[1],grass_spacing_cm=CARD_SPACING_CM)
 g=lambda n:float(grass.get_editor_property(n))
 if (OUT/'GrassGS3/manifest.json').exists():
  import lidar_grass_gs3
  lidar_grass_gs3.configure(grass)
 return dict(pasture_clump_mesh=grass.pasture_clump_mesh.get_path_name(),pasture_clump_mesh_b=grass.pasture_clump_mesh_b.get_path_name(),pasture_clump_mesh_c=grass.pasture_clump_mesh_c.get_path_name(),rank_clump_mesh=rm.get_path_name(),clump_spacing_cm=g('clump_spacing_cm'),card_spacing_cm=g('grass_spacing_cm'),
  clump_scale=[g('clump_scale_min'),g('clump_scale_max')],clump_stream_radius_cm=g('clump_stream_radius_cm'),clump_lod_cm=[g('clump_lod1_distance_cm'),g('clump_lod2_distance_cm')],grass_cull_cm=[g('grass_cull_start_cm'),g('grass_cull_end_cm')],patch_lod_screen_sizes=lod)
# GP2c: the colour program no longer paints pasture. Its final line is back to the pre-pasture ground colour (the PASTURE_OLD line, which the LP3c peat block returns); the grazed pasture is the GP2cPasture node downstream (block GP2C below).
# The block keeps the LP3d marker so the idempotence checks and every older clone (which still carry the GP2b block ending in PASTURE_END_OLD) are rewritten to this form on the next Install.
PASTURE_MARK='// LP3d grazed pasture'
PASTURE_OLD='return lerp(pow(max(rich,0),2.2),peatCol,peatMask);'
PASTURE_NEW=PASTURE_MARK+' (GP2c: pasture is the GP2cPasture node downstream; this program returns the ground colour and the LP3c peat, linear albedo)'+chr(10)+PASTURE_OLD
PASTURE_END_OLD='return lerp(pasGround,pasCol,pasW);'
def pasture_patch(code):
 """Idempotent: replaces the colour program's final line with the GP2c block once; an existing block (GP2b ends in PASTURE_END_OLD, GP2c in PASTURE_OLD) is rewritten to the current form. Returns (code, changed)."""
 if PASTURE_MARK in code:
  i=code.index(PASTURE_MARK);hits=[(code.index(e,i),e) for e in (PASTURE_END_OLD,PASTURE_OLD) if e in code[i:]];assert hits,'LP3d pasture block has no recognised end'
  k,e=min(hits);new=code[:i]+PASTURE_NEW+code[k+len(e):];return new,new!=code
 if PASTURE_OLD not in code:return code,False
 assert code.count(PASTURE_OLD)==1,'colour program final line is not unique'
 return code.replace(PASTURE_OLD,PASTURE_NEW),True
# CL1 BEGIN clay in the LiDAR ground materials (owner photos 10/11/12). The weight comes from the LidarClay atlas (prepare clay.png: R clay, G orange cut face, B bush slurry), NOT style R:
# GTLandscapeSurface reads style R as sand (granular physics) and AGTProceduralGround::Rebuild zeroes it across road corridors. The clay look is two NEW custom nodes, built fully wired
# before they are spliced in (a named custom input left unconnected is a compile error, and every property set on an existing node recompiles the material): CL1Colour sits between the
# colour program and the rock mix (it takes the program's output, peat included) and CL1Rough wraps whatever feeds the Roughness property. The existing programs are not edited.
CL1='cl1-3'
CL1_INFO={};GP2C_INFO={}
# CL2: the clay atlas is imported into the surface's own CPU atlas (GTLandscapeSurface ClayCells, same origin and span as the style atlas) so the soil response reads it.
# The Install fast path also requires this version, so the first Install after a change here rebuilds the level and every later Install is quick again.
CL2='cl2-1'
# LP4 (docs/LIDAR_PLACE_PLAN.md): the farm hardware (fences, strainers, gates, cattle stop, culverts, poles, troughs, bales, signs) from prepare's Place/hardware.json as one ISM component per mesh on
# the actor LidarStudy_Farm, ground-snapped to the BUILT relief tiles. The fast path below also requires this version, so the first Install after a change rebuilds the level.
LP4='lp4-1'
FARM_FAR=('SM_NZ_PowerPole','SM_NZ_Strainer')   # 250/350 m cull; every other farm mesh 150/220 m
FARM_SPAN_CM={'SM_NZ_Fence_4m':400.,'SM_NZ_Gate_3m6':396.}   # post-axis to post-axis span of the two spanning meshes (their pivot is the first post, the span runs along +X)
CL1_STRUCT='''// CL1 clay wetness and noise helper (same hash and value noise as the colour program's grain); wet() is the style wet channel B with 5 m and 1.3 m patches so dry crust and wet clay alternate
struct GTClayWet {
 float hash(float2 p){uint2 q=uint2(int2(p));uint h=q.x*374761393u+q.y*668265263u;h=(h^(h>>13))*1274126177u;return float((h^(h>>16))&0x00ffffffu)/16777215.0;}
 float noise(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);}
 float wet(float2 xy,float b){return saturate(b+(noise(xy/540.+3.)-.5)*.55+(noise(xy/130.+29.)-.5)*.30);}
};GTClayWet clayw;
'''
CL1_COLOUR_WRAP=CL1_STRUCT+'''// CL1 clay colour (photos 10/11/12): LidarClay R clay weight, G orange cut face, B bush slurry; style B is the wet channel; Paint R*50 is the road depth in cm; linear albedo. Native is the colour program's output.
float2 uvC=saturate((P.xy+185000)/370000);
float4 style=Texture2DSampleLevel(Style,StyleSampler,uvC,0);
float4 clayA=Texture2DSampleLevel(LidarClay,LidarClaySampler,uvC,0);
float3 clayOut=Native;
[branch] if(clayA.r>.002){
float clayD=length(Camera.xy-P.xy)*.01;
float clayF=1-saturate((clayD-4)/10),clayM=1-saturate((clayD-60)/140);
float wetE=clayw.wet(P.xy,style.b);
float dryW=1-smoothstep(.45,.60,wetE);
float bushW=saturate(clayA.b),cutW=saturate(clayA.g);
float mott=lerp(1,lerp(.78,1.22,clayw.noise(P.xy/310.+11.))*lerp(.90,1.10,clayw.noise(P.xy/47.+5.)),clayM);
float3 clayCol=lerp(float3(.20,.14,.08),float3(.34,.27,.17),dryW)*mott;
float crA=clayw.noise(P.xy/15.+float2(23.,5.));
float crB=clayw.noise(float2(P.x*.8-P.y*.6,P.x*.6+P.y*.8)/9.5+float2(61.,17.));
float crack=max(1-smoothstep(0,.035,abs(crA-.5)),.7*(1-smoothstep(0,.03,abs(crB-.5))));
clayCol*=1-.35*lerp(.2,crack,clayF)*dryW;
float depthCm=Texture2DSampleLevel(Paint,PaintSampler,uvC,0).r*50.;
float churn=smoothstep(2.8,6.,depthCm)*.55;
clayCol=lerp(clayCol,clayCol*float3(.62,.58,.55),churn*(1-bushW));
clayCol=lerp(clayCol,float3(.085,.07,.055),smoothstep(.80,.93,wetE)*(1-bushW)*.85);
float3 slurry=float3(.18,.15,.12)*lerp(1,lerp(.80,1.18,clayw.noise(P.xy/42.+19.)),clayM);
slurry=lerp(slurry,float3(.10,.08,.06),saturate(smoothstep(5.,12.,depthCm)*.85));
clayCol=lerp(clayCol,slurry,bushW);
clayCol=lerp(clayCol,float3(.42,.22,.08)*lerp(.78,1.15,clayw.noise(P.xy/55.+9.)),cutW);
clayOut=lerp(Native,clayCol,saturate(clayA.r));
}
return clayOut;'''
CL1_ROUGH_WRAP=CL1_STRUCT+'''// CL1 clay gloss: dry crust .85, wet clay toward .25 where wet is over .6; Base is whatever fed the Roughness property
float2 uvC=saturate((P.xy+185000)/370000);
float4 style=Texture2DSampleLevel(Style,StyleSampler,uvC,0);
float clayCW=saturate(Texture2DSampleLevel(LidarClay,LidarClaySampler,uvC,0).r);
return lerp(Base,lerp(.85,.25,smoothstep(.58,.80,clayw.wet(P.xy,style.b))),clayCW);'''
def cl1_wrap(m,textures):
 """Idempotent. Splices CL1Colour between the colour program and the rock mix, and CL1Rough around the Roughness property; returns what it did."""
 ex=list(mel.get_material_expressions(m));custom=[e for e in ex if isinstance(e,u.MaterialExpressionCustom)];info={}
 def tagged(tag):return [e for e in custom if str(e.get_editor_property('desc'))==tag]
 col=tagged('CL1Colour')
 if col:col[0].set_editor_property('code',CL1_COLOUR_WRAP);info['colour']='updated'
 else:
  prog=[e for e in custom if PEAT_MARK in str(e.get_editor_property('code'))];rock=[e for e in custom if 'lerp(Native,r,s.a)' in str(e.get_editor_property('code'))]
  assert len(prog)==1 and len(rock)==1,('CL1: colour program / rock mix not found once each',len(prog),len(rock))
  assert any(x.get_name()==prog[0].get_name() for x in mel.get_inputs_for_material_expression(m,rock[0]) if x),'CL1: the rock mix does not take the colour program'
  g=Graph(m,'CL1Colour');w=g.custom(['Native','P','Camera','Style','Paint','LidarClay'],CL1_COLOUR_WRAP)
  g.wire(prog[0],w,'Native');g.wire(g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),w,'P');g.wire(g.node(u.MaterialExpressionCameraPositionWS),w,'Camera')
  for key,pin in [('style','Style'),('paint','Paint'),('clay','LidarClay')]:g.wire(g.node(u.MaterialExpressionTextureObject,texture=textures[key],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),w,pin)
  g.wire(w,rock[0],'Native');info['colour']='spliced'
 rough_nodes=tagged('CL1Rough')   # RD1: RD1Rough now wraps the Roughness property, so CL1Rough is found by its tag, not as the property's input
 if rough_nodes:rough_nodes[0].set_editor_property('code',CL1_ROUGH_WRAP);info['rough']='updated'
 else:
  rn=mel.get_material_property_input_node(m,u.MaterialProperty.MP_ROUGHNESS)
  ro=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_ROUGHNESS) if rn is not None else '';g=Graph(m,'CL1Rough');w=g.custom(['Base','P','Style','LidarClay'],CL1_ROUGH_WRAP,u.CustomMaterialOutputType.CMOT_FLOAT1)
  g.wire(rn if rn is not None else g.scalar(.9),w,'Base',ro);g.wire(g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),w,'P')
  for key,pin in [('style','Style'),('clay','LidarClay')]:g.wire(g.node(u.MaterialExpressionTextureObject,texture=textures[key],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),w,pin)
  g.output(w,u.MaterialProperty.MP_ROUGHNESS);info['rough']='wrapped '+(rn.get_class().get_name() if rn is not None else 'nothing')+' output "'+ro+'"'
 return info
# CL1 END
# GP2c BEGIN tiled pasture (docs/LIDAR_PLACE_PLAN.md GP2c; owner 2026-10-18 on the GP2b ground: "It still doesn't look that good", a blotchy carpet of low-frequency noise). The pasture colour is no longer built from noise octaves: it is the pack's
# T_Landscape_Grass_01_A tile sampled at 1.5 m world tiling, blended 35% with the same tile at 5.3 m (rotated 29 degrees so the repeat does not line up), times a 12 m brightness-only value-noise octave (+-8%, never hue) and one final tint,
# with T_Landscape_DryGrass_01_A lerped in at 25% inside the 8% mown patches and 60% in the rank band (style G .3 to .8, full below .62). The tints are MEASURED, not typed: gp2c_measure exports both tiles (TGA under Saved/, deleted again), averages them
# in linear light and solves the tint so the final albedo (after the downstream LidarCoverTint multiplier at style G) lands on the display targets below. Built as NEW wrapper nodes (an unconnected named custom input, or a changed input
# array on an existing node, fails to compile; read the CL1 notes): GP2cPasture sits between the colour program (ground and LP3c peat) and CL1Colour, so peat keeps priority through the (1-peatMask) weight and clay, the rock mix and the cover tint
# still follow it; GP2cNormal wraps whatever feeds the Normal property. The colour program itself keeps only its pre-pasture ground colour (PASTURE_NEW above): no noise octaves and no desaturation remain in the pasture path.
GP2C='gp2c-3'   # GP4b: pasture target (.537,.637,.272) (GP2d: (.546,.65,.28))
PACK_TEX='/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Landscape/'
GP2C_COVER_TINT=(.85,1.0,.70)    # = Polish COVER_TINT: the LidarCoverTint node downstream multiplies the base colour by lerp(1,tint,style G); Polish asserts they are equal
GP2C_STYLE_G=dict(grass=.95,dry=.55)   # style G where each tile lands: inside the paddocks (prepare: .95) and the middle of the rank band
GP2C_TARGET_DISPLAY=dict(grass=(.537,.637,.272),dry=(.66,.57,.33))   # final albedo after the cover tint, sRGB-encoded R,G,B. GP2d: grass was (.5336,.58,.2494) (R/G .92), which GP2c measured in the render at R/G 1.03, value .52 near (ochre); photo 09 is R/G .945, value .66, B/G .43, so the grass triple is the brief's (R/G .84, value .65) aiming the render there; straw (photo 09 band about .72,.65,.42)
# GP4b distance match (docs/LIDAR_PLACE_PLAN.md GP4): the pasture beyond the 30 to 38 m patch fade is this ground. The GP4b Check captures put the rendered patches just inside the fade within a few percent of the ground just beyond it; the residual step the row profiles of
# Paddock_chase and Paddock_middle show at the fade (ground lighter than the trend of the patch bands before it: R +1.6%, G +2.0%, B +3.0%) is taken out of the grass target, (.546,.65,.28) x (.984,.98,.97) = (.537,.637,.272).
# Matching the ground to the near (within 15 m) patch mean instead, (.490,.530,.110) in Paddock_chase, would have re-solved the target to (.410,.502,.134) and made the ground beyond the fade 18% darker than the patches in it.
GP2C_TILING_CM=dict(grass=150.,grass_far=530.,dry=150.,normal=150.)
GP2C_TILES={}
def srgb_to_lin(c):
 return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
def lin_to_srgb(x):
 x=max(0.,min(1.,x));return 12.92*x if x<=.0031308 else 1.055*x**(1/2.4)-.055
def tga_linear_mean(path):
 """Mean RGB of an uncompressed 24/32 bit TGA (the editor's TextureExporterTGA output), averaged in LINEAR light from the sRGB bytes; returns (r,g,b,width,height)."""
 import struct
 from collections import Counter
 b=open(path,'rb').read();idlen,cmap,itype=b[0],b[1],b[2];assert itype==2 and cmap==0,('TGA type',itype,cmap)
 w,h=struct.unpack('<HH',b[12:16]);bpp=b[16];assert bpp in (24,32),bpp;n=bpp//8;data=memoryview(b)[18+idlen:18+idlen+w*h*n];out=[]
 for ch in (2,1,0):   # TGA stores B,G,R(,A)
  hist=Counter(bytes(data[ch::n]));tot=sum(hist.values());out.append(sum(srgb_to_lin(k/255.)*v for k,v in hist.items())/tot)
 return out[0],out[1],out[2],w,h
def gp2c_measure():
 """Once per run: exports the two pack tiles, measures their linear mean colour and solves each tint = target linear albedo / (tile mean x downstream cover multiplier). Returns GP2C_TILES."""
 if GP2C_TILES:return GP2C_TILES
 folder=ROOT/'Saved/Gp2cTiles';folder.mkdir(parents=True,exist_ok=True)
 for key,name in (('grass','T_Landscape_Grass_01_A'),('dry','T_Landscape_DryGrass_01_A')):
  t=u.load_asset(PACK_TEX+name);assert t,('pack texture missing',name);path=folder/(name+'.tga')
  task=u.AssetExportTask();task.object=t;task.filename=str(path);task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.TextureExporterTGA();assert u.Exporter.run_asset_export_task(task),name
  r,g,b,w,h=tga_linear_mean(path);path.unlink();cover=[1+(c-1)*GP2C_STYLE_G[key] for c in GP2C_COVER_TINT];target=[srgb_to_lin(c) for c in GP2C_TARGET_DISPLAY[key]];tint=[round(tg/(m*cv),4) for tg,m,cv in zip(target,(r,g,b),cover)]
  read={}
  for pn in ('srgb','never_stream','compression_settings','mip_gen_settings','lod_group','filter','address_x','address_y'):
   try:read[pn]=str(t.get_editor_property(pn))
   except Exception as err:read[pn]='unreadable '+repr(err)[:60]
  disp=[lin_to_srgb(v) for v in (r,g,b)]
  GP2C_TILES[key]=dict(texture=PACK_TEX+name,size=[w,h],mean_linear=[round(v,5) for v in (r,g,b)],mean_display=[round(v,4) for v in disp],mean_display_r_over_g=round(disp[0]/disp[1],3),mean_display_value=round(max(disp),3),
   style_g_assumed=GP2C_STYLE_G[key],cover_multiplier=[round(c,4) for c in cover],target_display=list(GP2C_TARGET_DISPLAY[key]),target_linear=[round(v,5) for v in target],tint=tint,
   expected_final_display=[round(lin_to_srgb(m*tn*cv),4) for m,tn,cv in zip((r,g,b),tint,cover)],texture_settings=read)
 try:folder.rmdir()
 except OSError:pass
 return GP2C_TILES
GP2C_STRUCT='''struct GTPas {
 float hash(float2 p){uint2 q=uint2(int2(p));uint h=q.x*374761393u+q.y*668265263u;h=(h^(h>>13))*1274126177u;return float((h^(h>>16))&0x00ffffffu)/16777215.0;}
 float noise(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);}
};GTPas pas;
'''
GP2C_WEIGHT='''float peatRock=1-smoothstep(.6,.95,style.a);
float peatMask=saturate((style.b-.55)*3)*(1-style.g)*peatRock;
float pasW=smoothstep(.3,.8,style.g)*(1-saturate(style.r))*(1-peatMask);
'''
GP2C_COLOUR_CODE=GP2C_STRUCT+'''// GP2c tiled pasture, linear albedo. Native is the colour program (ground and LP3c peat), GrassA the pack Grass_01 tile at 1.5 m, GrassB the same tile at 5.3 m (rotated), Dry the DryGrass tile at 1.5 m, Style the LiDAR atlas.
float4 style=Texture2DSampleLevel(Style,StyleSampler,saturate((P.xy+185000)/370000),0);
'''+GP2C_WEIGHT+'''float macro=1+.08*clamp((pas.noise(P.xy/1200.+71.)-.5)*3.,-1,1);
float3 grass=lerp(GrassA,GrassB,.35)*macro*float3(@TINT@);
float3 straw=Dry*macro*float3(@DRYTINT@);
float mown=smoothstep(.74,.80,pas.noise(P.xy/800.+211.));
float rank=1-smoothstep(.62,.80,style.g);
float dryW=max(.25*mown,.60*rank);
return lerp(Native,lerp(grass,straw,dryW),pasW);'''
GP2C_NORMAL_CODE='''// GP2c pasture micro-normal. Base is whatever fed the Normal property, GrassN the pack Grass_01 normal at 1.5 m (unpacked tangent space, world axes), added at 50% strength within 20 m of the camera and fading to 0 by 40 m, on pasture only (the colour's weight) and off the clay.
float2 uvA=saturate((P.xy+185000)/370000);
float4 style=Texture2DSampleLevel(Style,StyleSampler,uvA,0);
'''+GP2C_WEIGHT+'''float clayW=saturate(Texture2DSampleLevel(LidarClay,LidarClaySampler,uvA,0).r);
float k=.5*(1-saturate((length(Camera-P)*.01-20)/20))*pasW*(1-clayW);
return normalize(float3(Base.xy+GrassN.xy*k,Base.z));'''
def gp2c_colour_code():
 t=gp2c_measure();return GP2C_COLOUR_CODE.replace('@TINT@',','.join('%.4f'%v for v in t['grass']['tint'])).replace('@DRYTINT@',','.join('%.4f'%v for v in t['dry']['tint']))
def gp2c_wrap(m,textures):
 """Idempotent. Splices GP2cPasture between the colour program and CL1Colour and GP2cNormal around the Normal property's input, each built fully wired first; an existing node only gets its code rewritten. Returns what it did."""
 ex=list(mel.get_material_expressions(m));custom=[e for e in ex if isinstance(e,u.MaterialExpressionCustom)];info={};code=gp2c_colour_code()
 def tagged(tag):return [e for e in custom if str(e.get_editor_property('desc'))==tag]
 def wpos(g):return g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
 def tobj(g,key):return g.node(u.MaterialExpressionTextureObject,texture=textures[key],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 def tsample(g,name,uv,normal=False):
  n=g.node(u.MaterialExpressionTextureSample,texture=u.load_asset(PACK_TEX+name),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR,sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS);g.wire(uv,n,'UVs');return n
 col=tagged('GP2cPasture')
 if col:col[0].set_editor_property('code',code);info['colour']='updated'
 else:
  prog=[e for e in custom if PEAT_MARK in str(e.get_editor_property('code'))];cl1=tagged('CL1Colour');assert len(prog)==1 and len(cl1)==1,('GP2c: colour program / CL1Colour not found once each',len(prog),len(cl1))
  assert any(x is not None and x.get_name()==prog[0].get_name() for x in mel.get_inputs_for_material_expression(m,cl1[0])),'GP2c: CL1Colour does not take the colour program'
  g=Graph(m,'GP2cPasture');gu=Graph(m,'GP2cUV');p=wpos(g);F2=u.CustomMaterialOutputType.CMOT_FLOAT2
  uv1=gu.custom(['P'],'return P.xy/%.1f;'%GP2C_TILING_CM['grass'],F2);gu.wire(p,uv1,'P')
  uv2=gu.custom(['P'],'float2 r=float2(P.x*.8746-P.y*.4848,P.x*.4848+P.y*.8746);return r/%.1f;'%GP2C_TILING_CM['grass_far'],F2);gu.wire(p,uv2,'P')   # 29 degrees
  ga=tsample(g,'T_Landscape_Grass_01_A',uv1);gb=tsample(g,'T_Landscape_Grass_01_A',uv2);dr=tsample(g,'T_Landscape_DryGrass_01_A',uv1)
  w=g.custom(['Native','P','Style','GrassA','GrassB','Dry'],code)
  g.wire(prog[0],w,'Native');g.wire(p,w,'P');g.wire(tobj(g,'style'),w,'Style');g.wire(ga,w,'GrassA','RGB');g.wire(gb,w,'GrassB','RGB');g.wire(dr,w,'Dry','RGB')
  g.wire(w,cl1[0],'Native');info['colour']='spliced between the colour program and CL1Colour'
 nn=tagged('GP2cNormal')
 if nn:nn[0].set_editor_property('code',GP2C_NORMAL_CODE);info['normal']='updated'
 else:
  rn=mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
  if rn is None:info['normal']='skipped: nothing feeds the Normal property'
  else:
   ro=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL);g=Graph(m,'GP2cNormal');gu=Graph(m,'GP2cUV');p=wpos(g)
   uv=gu.custom(['P'],'return P.xy/%.1f;'%GP2C_TILING_CM['normal'],u.CustomMaterialOutputType.CMOT_FLOAT2);gu.wire(p,uv,'P');gn=tsample(g,'T_Landscape_Grass_01_N',uv,True)
   w=g.custom(['Base','P','Camera','Style','LidarClay','GrassN'],GP2C_NORMAL_CODE);g.wire(rn,w,'Base',ro);g.wire(p,w,'P');g.wire(g.node(u.MaterialExpressionCameraPositionWS),w,'Camera');g.wire(tobj(g,'style'),w,'Style');g.wire(tobj(g,'clay'),w,'LidarClay');g.wire(gn,w,'GrassN','RGB')
   g.output(w,u.MaterialProperty.MP_NORMAL);info['normal']='wrapped '+rn.get_class().get_name()+' output "'+ro+'"'
 return info
# GP2c END
# RD1 BEGIN gravel roads (docs/LIDAR_PLACE_PLAN.md RD1; owner 2026-10-19: "they should be gravel roads"). Every road on the map is gravel: the road corridor of the colour is the project's painterly gravel tile (Art/Textures/GroundPainterly/T_Gravel_Painted_v1.png, imported as T_gravel,
# sRGB, tiling) at 1.0 m world tiling blended 30% with itself at 3.7 m (rotated 31 degrees), pulled toward grey river gravel (saturation x.35, tint measured below), the two wheel lines 25% darker and 15% less rough, and clay stays only where prepare's clay atlas R is (the cut band and the yard).
# The corridor and the wheel lines come from the road LATERAL DISTANCE that prepare writes into the clay atlas alpha (A = d / 6.4 m + .5, left positive, 1 = far): gravel at |d| < 2.0 m, none beyond 2.6 m, wheel lines at |d| = .82 m. The program has no explicit road weight of its own (style G, the grass cover, is all the corridor carries),
# and a 1.8 m atlas cannot hold two 25 cm wheel lines, but bilinear sampling of a linear distance field is exact between texels. Two NEW wrapper nodes (built fully wired first, idempotent, nothing else edited): RD1Gravel sits between CL1Colour and the rock mix, RD1Rough wraps what feeds the Roughness property (CL1Rough).
# Grass that the corridor carries (style G over about .12 to .6: verges, the centre strip) shows through as before.
RD1='rd1-5-fr1'   # FR1: firm road policy; older rd1-4 (RD1b): road soil depth raised so gravel ruts shallowly - Gravel track mud 4 -> 9, rut 2 -> 3, firmness .85 -> .80 (private base mud 4 -> 9); Firm gravel mud 2 -> 5, rut 1 -> 2, firmness .95 -> .90; rd1-2: the road relief tiles take M_Terrain (RELIEF_KIND) and the tread ribbons a gravel grey (RD1Tread); rd1-3: saturation .35 -> .20 and a cooler target (the first render read R/G 1.17, warm brown, not grey)
RD1_INFO={}
GRAVEL_SRC=ROOT/'Art/Textures/GroundPainterly/T_Gravel_Painted_v1.png';GRAVEL_PATH=BASE+'/T_gravel'
RD1_TILING_CM=dict(a=100.,b=370.);RD1_BLEND_B=.30;RD1_SAT=.20;RD1_FAR_DEG=31.
# Measured offline from the 1254 px tile (display mean .422/.356/.286, linear mean .1487/.1043/.0665, mean luminance .111); after the saturation pull to .20 the linear mean is lum + .2 x (mean - lum) = (.1185,.1097,.1021); RD1_TARGET_LINEAR is the albedo the road should average (display about .47/.47/.46; the first render at (.188,.178,.162) came out R/G 1.17 under the sun), the tint is target / mean.
RD1_TILE_MEAN_AFTER_SAT=(.1185,.1097,.1021);RD1_TARGET_LINEAR=(.19,.186,.182);RD1_TINT=tuple(round(t/m,3) for t,m in zip(RD1_TARGET_LINEAR,RD1_TILE_MEAN_AFTER_SAT))
RD1_WHEEL=dict(centre_m=.82,half_width_m=.20,darker=.25,rougher=.15,rough_gravel=.85)
RD1_STRUCT='''struct GTRd1 {
 float hash(float2 p){uint2 q=uint2(int2(p));uint h=q.x*374761393u+q.y*668265263u;h=(h^(h>>13))*1274126177u;return float((h^(h>>16))&0x00ffffffu)/16777215.0;}
 float noise(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);}
};GTRd1 rd1;
'''
RD1_COMMON='''float2 uvC=saturate((P.xy+185000)/370000);
float4 style=Texture2DSampleLevel(Style,StyleSampler,uvC,0);
float ad=abs((Texture2DSampleLevel(LidarClay,LidarClaySampler,uvC,0).a-.5)*6.4);
float gw=1-smoothstep(2.0,2.6,ad);
float grassMix=smoothstep(.12,.6,style.g);
float wl=1-smoothstep(@WHALF1@,@WHALF2@,abs(ad-@WCENTRE@));
wl*=lerp(.55,1,rd1.noise(P.xy/3.1+9.));
'''
RD1_COLOUR_CODE=RD1_STRUCT+'''// RD1 gravel road, linear albedo. Native is the CL1Colour output, Style the LiDAR atlas, LidarClay the clay atlas (A = road lateral distance, see install_lidar_place RD1), GravelA / GravelB the painterly gravel tile at 1.0 m and 3.7 m.
'''+RD1_COMMON+'''[branch] if(gw<.002)return Native;
float3 gr=lerp(GravelA,GravelB,@BLEND@);
float lum=dot(gr,float3(.2126,.7152,.0722));
gr=lerp(lum.xxx,gr,@SAT@)*float3(@TINT@);
gr*=1-@DARK@*wl;
return lerp(Native,gr,gw*(1-grassMix));'''
RD1_ROUGH_CODE=RD1_STRUCT+'''// RD1 gravel gloss: river gravel roughness @RG@, the wheel lines 15% lower; Base is whatever fed the Roughness property (CL1Rough).
'''+RD1_COMMON+'''return lerp(Base,@RG@*(1-@ROUGHER@*wl),gw*(1-grassMix));'''
def rd1_fill(code):
 w=RD1_WHEEL;return code.replace('@WHALF1@','%.3f'%max(w['half_width_m']-.10,.01)).replace('@WHALF2@','%.3f'%(w['half_width_m']+.10)).replace('@WCENTRE@','%.3f'%w['centre_m']).replace('@BLEND@','%.3f'%RD1_BLEND_B).replace('@SAT@','%.3f'%RD1_SAT).replace('@TINT@',','.join('%.3f'%v for v in RD1_TINT)).replace('@DARK@','%.3f'%w['darker']).replace('@ROUGHER@','%.3f'%w['rougher']).replace('@RG@','%.3f'%w['rough_gravel'])
def gravel_texture():
 """T_gravel: the project's painterly gravel tile, sRGB, tiling (wrap), streaming on, stretched to a 2048 square (the provenance's import settings). Idempotent; returns the texture."""
 if not assets.does_asset_exist(GRAVEL_PATH):
  t=props(u.AssetImportTask(),filename=str(GRAVEL_SRC),destination_path=BASE,destination_name='T_gravel',automated=True,replace_existing=True,save=True);at.import_asset_tasks([t])
 v=u.load_asset(GRAVEL_PATH);assert v,'T_gravel import failed'
 props(v,srgb=True,max_texture_size=2048,compression_no_alpha=True,never_stream=False,power_of_two_mode=u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP)
 assert assets.save_loaded_asset(v);return v
def rd1_wrap(m,textures):
 """Idempotent. Splices RD1Gravel between CL1Colour and the rock mix and RD1Rough around the Roughness property's input (CL1Rough); each is built fully wired first, an existing node only gets its code rewritten. Returns what it did."""
 ex=list(mel.get_material_expressions(m));custom=[e for e in ex if isinstance(e,u.MaterialExpressionCustom)];info={}
 def tagged(tag):return [e for e in custom if str(e.get_editor_property('desc'))==tag]
 def wpos(g):return g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
 def tobj(g,key):return g.node(u.MaterialExpressionTextureObject,texture=textures[key],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 gravel=u.load_asset(GRAVEL_PATH);assert gravel
 col=tagged('RD1Gravel')
 if col:col[0].set_editor_property('code',rd1_fill(RD1_COLOUR_CODE));info['colour']='updated'
 else:
  cl1=tagged('CL1Colour');rock=[e for e in custom if 'lerp(Native,r,s.a)' in str(e.get_editor_property('code'))];assert len(cl1)==1 and len(rock)==1,('RD1: CL1Colour / rock mix not found once each',len(cl1),len(rock))
  assert any(x is not None and x.get_name()==cl1[0].get_name() for x in mel.get_inputs_for_material_expression(m,rock[0])),'RD1: the rock mix does not take CL1Colour'
  g=Graph(m,'RD1Gravel');gu=Graph(m,'RD1UV');p=wpos(g);F2=u.CustomMaterialOutputType.CMOT_FLOAT2
  uv1=gu.custom(['P'],'return P.xy/%.1f;'%RD1_TILING_CM['a'],F2);gu.wire(p,uv1,'P')
  rad=math.radians(RD1_FAR_DEG);uv2=gu.custom(['P'],'float2 r=float2(P.x*%.4f-P.y*%.4f,P.x*%.4f+P.y*%.4f);return r/%.1f;'%(math.cos(rad),math.sin(rad),math.sin(rad),math.cos(rad),RD1_TILING_CM['b']),F2);gu.wire(p,uv2,'P')
  def tsample(uv):
   n=g.node(u.MaterialExpressionTextureSample,texture=gravel,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR,sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS);g.wire(uv,n,'UVs');return n
  ga=tsample(uv1);gb=tsample(uv2);w=g.custom(['Native','P','Style','LidarClay','GravelA','GravelB'],rd1_fill(RD1_COLOUR_CODE))
  g.wire(cl1[0],w,'Native');g.wire(p,w,'P');g.wire(tobj(g,'style'),w,'Style');g.wire(tobj(g,'clay'),w,'LidarClay');g.wire(ga,w,'GravelA','RGB');g.wire(gb,w,'GravelB','RGB')
  g.wire(w,rock[0],'Native');info['colour']='spliced between CL1Colour and the rock mix'
 rn_=tagged('RD1Rough')
 if rn_:rn_[0].set_editor_property('code',rd1_fill(RD1_ROUGH_CODE));info['rough']='updated'
 else:
  rn=mel.get_material_property_input_node(m,u.MaterialProperty.MP_ROUGHNESS);assert rn is not None and str(rn.get_editor_property('desc'))=='CL1Rough',('RD1: the Roughness property is not fed by CL1Rough',rn.get_class().get_name() if rn is not None else None)
  ro=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_ROUGHNESS);g=Graph(m,'RD1Rough');w=g.custom(['Base','P','Style','LidarClay'],rd1_fill(RD1_ROUGH_CODE),u.CustomMaterialOutputType.CMOT_FLOAT1)
  g.wire(rn,w,'Base',ro);g.wire(wpos(g),w,'P');g.wire(tobj(g,'style'),w,'Style');g.wire(tobj(g,'clay'),w,'LidarClay');g.output(w,u.MaterialProperty.MP_ROUGHNESS);info['rough']='wrapped CL1Rough output "'+ro+'"'
 return info
# RD1 DIAGNOSIS (2026-10-19, Check Drive step): the road relief tiles (AGTRoadReliefTile) were built with M_Detail, the VISUAL-GRID material. M_Detail's opacity mask is the dither of the player window (visible INSIDE MR_VisualWindow), the tile's own MID is never registered with the
# surface (AGTLandscapeSurface::BindTextures only feeds the visual grid's MID: GTLS_Ready 0, GTLS_Field 'Black') and M_Detail has no MR_ActiveGrid parameter, so inside the window the tile drew its undisplaced rest surface coplanar with the visual grid and covered every rut and tread ribbon
# (hiding the tiles in the same frame showed two clean tyre ruts behind the car). The tile code (BeginPlay sets MR_ActiveGrid 1, BindWindow sets MR_VisualWindow) is written for M_Terrain, whose mask is 1 - dither(window) x MR_ActiveGrid: the tile is cut away exactly where the grid draws. RELIEF_KIND is that fix.
RELIEF_KIND='Terrain'
RD1_TREAD_CODE='''// RD1 gravel tread: Base is the native tread ribbon (unlit, pre-exposed). On the road corridor (clay atlas A = lateral distance, |d| < 2.0 m full, 2.6 m none) the ribbon keeps its luminance but loses its dirt hue, so tyre prints on gravel are darker gravel, not orange clay.
float2 uvC=saturate((P.xy+185000)/370000);
float ad=abs((Texture2DSampleLevel(LidarClay,LidarClaySampler,uvC,0).a-.5)*6.4);
float gw=1-smoothstep(2.0,2.6,ad);
float l=dot(Base,float3(.2126,.7152,.0722));
return lerp(Base,l*float3(.82,.84,.90),gw*.92);'''
def rd1_tread_wrap(m,textures):
 """Idempotent. Wraps whatever feeds the Tread material's Emissive Color with RD1Tread (built fully wired first); an existing node only gets its code rewritten."""
 custom=[e for e in mel.get_material_expressions(m) if isinstance(e,u.MaterialExpressionCustom)];have=[e for e in custom if str(e.get_editor_property('desc'))=='RD1Tread']
 if have:have[0].set_editor_property('code',RD1_TREAD_CODE);return dict(tread='updated')
 rn=mel.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR);assert rn is not None,'RD1: the Tread material has no emissive input'
 ro=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_EMISSIVE_COLOR);g=Graph(m,'RD1Tread');w=g.custom(['Base','P','LidarClay'],RD1_TREAD_CODE)
 g.wire(rn,w,'Base',ro);g.wire(g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),w,'P');g.wire(g.node(u.MaterialExpressionTextureObject,texture=textures['clay'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),w,'LidarClay')
 g.output(w,u.MaterialProperty.MP_EMISSIVE_COLOR);return dict(tread='wrapped '+rn.get_class().get_name()+' output "'+ro+'"')
# RD1 END
FOLIAGE_TINT=('CrownFern','TwigLitter','LeafLitter','RootTangle','MossHummock','Log_','Stump','TreeFern','Kiokio')   # understory classes that wear MI_NZ_Foliage_Bush on their Foliage slot
SPAR_TINT=(.42,.40,.38);BUSH_TINT=(.62,.70,.60)
def kit_instance(name,parent_path,rgb):
 path=BASE+'/'+name;mi=u.load_asset(path) if assets.does_asset_exist(path) else at.create_asset(name,BASE,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());assert mi,name
 parent=u.load_asset(parent_path);assert parent and 'Tint' in [str(n) for n in mel.get_vector_parameter_names(parent)],('the kit material has no Tint parameter; run native_plants.ps1 -Mode Import first',parent_path)
 mel.set_material_instance_parent(mi,parent);mel.set_material_instance_vector_parameter_value(mi,'Tint',u.LinearColor(*rgb,1));assert assets.save_loaded_asset(mi);return mi
def tint_slots(component,mesh,source_path,instance):
 """Overrides every slot of the mesh whose material is source_path with the instance; returns the slot indices."""
 hit=[]
 for i,s in enumerate(mesh.get_editor_property('static_materials')):
  m=s.get_editor_property('material_interface')
  if m and m.get_path_name().split('.')[0]==source_path:component.set_material(i,instance);hit.append(i)
 return hit
def tint_far_card(k,rgb):
 """Shared, idempotent tint also recognises the node below LP6 crown shading."""
 import lidar_canopy_assets
 lidar_canopy_assets.tint_far_card(k,rgb)
data=json.loads((OUT/'prepare.json').read_text());report=dict(ok=False,driving_tested=False,stages=[])
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools();actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
busy=False
def protected():
 paths=[]
 for folder in ['BenmoreWoodland','BigMountain','ProceduralGround']:
  paths+=list((ROOT/'Content/GrandTour/ArtTests'/folder).rglob('*.uasset'))+list((ROOT/'Content/GrandTour/ArtTests'/folder).rglob('*.umap'))
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
def prune_backups(root,keep=2):
 # Each run copies the whole LidarStudy content folder (~1 GB); keep the newest two.
 # copytree copies the source folder's mtime, so order by the run stamp in the name.
 allowed=(ROOT/'Saved/LidarStudyBackups').resolve();assert root.resolve()==allowed
 copies=sorted((d for d in root.iterdir() if d.is_dir()),key=lambda d:(int(re.search(r'(\d{10,})$',d.name).group(1)) if re.search(r'(\d{10,})$',d.name) else int(d.stat().st_mtime*1e9)))
 for d in copies[:-keep]:
  assert d.resolve().parent==allowed and not d.is_symlink(),('Unsafe backup path',str(d))
  shutil.rmtree(d,ignore_errors=True)
def spawn(cls,label,pos=(0,0,0)):
 a=actors.spawn_actor_from_class(cls,u.Vector(*pos));a.set_actor_label('LidarStudy_'+label);return a
def tex(name):
 t=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=BASE,destination_name='T_'+name,automated=True,replace_existing=True,save=True)
 at.import_asset_tasks([t]);v=u.load_asset(BASE+'/T_'+name);assert v
 props(v,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_NEAREST if name=='HeightRG' else u.TextureFilter.TF_BILINEAR,never_stream=True,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
 assert assets.save_loaded_asset(v);return v
def clone(source,name):
 path=BASE+'/'+name
 if assets.does_asset_exist(path):return u.load_asset(path)
 a=assets.duplicate_asset(source,path);assert a;return a
def ground(kind,textures):
 m=clone(TEMPLATE+'/M_'+kind,'M_'+kind);peats=0;pastures=0
 for e in mel.get_material_expressions(m):
  if isinstance(e,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSample)):
   t=e.get_editor_property('texture')
   if t:
    key=t.get_name()[2:]
    if key in ['style','style_groundstudy']:key='style'
    if key in textures:e.set_editor_property('texture',textures[key])
  if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_PaintWindow':e.set_editor_property('default_value',u.LinearColor(-185000,-185000,370000,0))
  if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='WoodlandGroundReviewOnly':e.set_editor_property('default_value',0)
  if isinstance(e,u.MaterialExpressionCustom):
   code=str(e.get_editor_property('code')).replace('+250000','+185000').replace('/500000','/370000')
   if kind in ['Terrain','Detail']:
    code,changed=peat_patch(code);peats+=int(changed)+int(PEAT_MARK in code and not changed)
    code,pchanged=pasture_patch(code);pastures+=int(pchanged)+int(PASTURE_MARK in code and not pchanged)
   e.set_editor_property('code',code)
 if kind in ['Terrain','Detail']:
  assert peats==1,('LP3c peat block must be in exactly one colour program',kind,peats)
  assert pastures==1,('LP3d pasture block must be in exactly one colour program',kind,pastures)
  CL1_INFO[kind]=cl1_wrap(m,textures);GP2C_INFO[kind]=gp2c_wrap(m,textures);RD1_INFO[kind]=rd1_wrap(m,textures)
 if kind=='Tread':RD1_INFO[kind]=rd1_tread_wrap(m,textures)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m);return m

def water_patch(spec,world):
 name=spec['name'];flow=tex(name+'-flow');shore=tex(name+'-shore')
 m=clone('/Game/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces/M_NativeDomainRiver','M_'+name+'Water');changed=0
 for e in mel.get_material_expressions(m):
  if isinstance(e,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter)):
   t=e.get_editor_property('texture')
   if t and ('DomainFlow' in t.get_name() or t.get_name().endswith('-flow')):e.set_editor_property('texture',flow)
   if t and ('Shore' in t.get_name() or t.get_name().endswith('-shore')):e.set_editor_property('texture',shore)
  if isinstance(e,u.MaterialExpressionCustom):
   ox,oy=spec['origin_cm'];sx,sy=spec['span_cm'];uv=f'(P.xy-float2({ox},{oy}))/float2({sx},{sy})';code,n=re.subn(r'float2 buv\s*=.*?;',f'float2 buv={uv};',str(e.get_editor_property('code')))
   code=re.sub(r'float2 (shapeBankUV|bankUV)\s*=.*?;',lambda match:f'float2 {match.group(1)}={uv};',code)
   code=re.sub(r'\(P.xy\*\.01-float2\(-1480(?:\.0+)?,-300(?:\.0+)?\)\+\.(?:625|3125)\)/float2\(126[01]\.\d+,107[56]\.\d+\)',uv,code)
   assert '-1480' not in code and '1260.625' not in code,'Unmapped water coordinates';e.set_editor_property('code',code);changed+=n
 assert changed and not mel.recompile_material(m);assert assets.save_loaded_asset(m)
 domain=clone('/Game/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain','DA_'+name+'Water');assert domain.import_bake(str(OUT/(name+'-domain.bin')));assert domain.set_child_domains([]);assets.save_loaded_asset(domain)
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.OBJ 0')
 ui=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(ui.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False,generate_lightmap_u_vs=False)
 task=props(u.AssetImportTask(),filename=str(OUT/(name+'.obj')),destination_path=BASE,destination_name='SM_'+name+'Water',automated=True,replace_existing=True,save=True,options=ui);at.import_asset_tasks([task]);mesh=u.load_asset(BASE+'/SM_'+name+'Water');assert mesh
 mesh.set_material(0,m);u.get_editor_subsystem(u.StaticMeshEditorSubsystem).remove_collisions(mesh);assets.set_metadata_tag(mesh,'LP6CoverageKey','');assets.save_loaded_asset(mesh)
 first=mesh.get_static_mesh_description(0).get_vertex_position(u.VertexID(0));assert (first-u.Vector(*spec['first_vertex'])).length()<.1,(first,spec['first_vertex'])
 actor=spawn(u.StaticMeshActor,name+'Water');actor.static_mesh_component.set_static_mesh(mesh);actor.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);actor.static_mesh_component.set_cast_shadow(False)
 return domain,actor,m

def run():
 global report
 import sys
 sys.path.insert(0,str(ROOT/'Art/tools'))
 import lidar_authoring as LA
 inputs_digest=LA.inputs_digest(OUT)
 assert data.get('authoring',{}).get('design_digest')==LA.digest(LA.load()),'Saved designs differ from preparation: run Prepare first'
 assert hashlib.sha256((OUT/'authoring-height.r16').read_bytes()).hexdigest()==data['authoring']['derived_height_sha256'],'Derived terrain digest mismatch'
 assert hashlib.sha256((OUT.parent/'height.r16').read_bytes()).hexdigest()==data['authoring']['source_height_sha256'],'Source terrain changed since preparation'
 before=protected();report['protected_before']=before
 prior=OUT/'install.json'
 if prior.exists():
  saved=json.loads(prior.read_text())
  only_dressing_changed=False
  if saved.get('inputs_digest')!=inputs_digest and saved.get('logging_trial',{}).get('dressing_version'):
   # Reconstruct the exact previous manifest from the successful install's
   # recorded source fields. Every other input byte must still match its digest.
   old_manifest=json.loads((OUT/'logging_trial.json').read_text(encoding='utf-8'))
   fields=('kind','station_m','across_m','size_cm','yaw_offset','mass_kg','variant')
   old_manifest['obstacles']=[{k:item[k] for k in fields} for item in saved['logging_trial']['dressing'] if item.get('kind') in ('log','mud_clump')]
   newline='\r\n' if b'\r\n' in (OUT/'logging_trial.json').read_bytes() else '\n'
   old_bytes=(json.dumps(old_manifest,indent=2)+'\n').replace('\n',newline).encode('utf-8');old_hash=hashlib.sha256()
   for p in LA.input_files(OUT):
    old_hash.update(p.name.encode()+b'\0');old_hash.update(hashlib.sha256(old_bytes if p.name=='logging_trial.json' else p.read_bytes()).digest())
   only_dressing_changed=old_hash.hexdigest()==saved.get('inputs_digest')
  if saved.get('road_generation') and (saved.get('ok') or 'domain_surfaces' in saved.get('error','')) and (saved.get('inputs_digest')==inputs_digest or only_dressing_changed) and saved.get('lp3c',{}).get('version')==LP3C and saved.get('cl1',{}).get('version')==CL1 and saved.get('cl2',{}).get('version')==CL2 and saved.get('lp4',{}).get('version')==LP4 and saved.get('lp3d',{}).get('version')==LP3D and saved.get('lp3e',{}).get('version')==LP3E and saved.get('gp2',{}).get('version')==GP2 and saved.get('gp2c',{}).get('version')==GP2C and saved.get('rd1',{}).get('version')==RD1 and saved.get('firm_gravel',{}).get('version')==lidar_firm_roads.VERSION and saved.get('logging_trial',{}).get('version')=='LT3':
   assert les.load_level(LEVEL);refs=actors.get_all_level_actors();author=next(a for a in refs if isinstance(a,u.GTProceduralGround));sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
   assert author.output_digest==saved['road_generation']['digest'] and len(author.relief_tiles)==saved['road_generation']['tiles']
   surfaces=sheet.get_editor_property('domain_surfaces');assert len(surfaces)==3
   for a in surfaces:assert a and a.static_mesh_component.get_material(0)
   assert u.load_asset(sheet.get_editor_property('surface_material_path')) and before==saved['protected_before']
   import lidar_logging_trial as trial
   if only_dressing_changed or saved['logging_trial'].get('dressing_version')!=trial.DRESSING_VERSION:
    # A dressing-code change does not require regenerating verified terrain.
    # The complete inputs digest and saved road digest were checked above.
    backup=ROOT/'Saved/LidarStudyBackups'/('Dressing-'+str(time.time_ns()));backup.mkdir(parents=True)
    shutil.copy2(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup/'L_LidarStudy.umap')
    tiles=list(author.relief_tiles.values())
    def dressing_ground(x,y):
     xy=u.Vector2D(x,y)
     for t in tiles:
      o=t.get_actor_location()
      if o.x<=x<o.x+t.span_cm and o.y<=y<o.y+t.span_cm:return t.height_at(xy)
     return author.base_height_at(xy)
    path=trial.route(json.loads((OUT/'roads.json').read_text()));assert path
    trial.verify_pools(author,sheet,path,dressing_ground)
    for a in refs:
     if a.get_actor_label().startswith('LidarStudy_LoggingDetail_'):actors.destroy_actor(a)
    saved['logging_trial']['dressing']=trial.dress(path,dressing_ground,spawn)
    saved['logging_trial']['dressing_version']=trial.DRESSING_VERSION
    assert author.output_digest==saved['road_generation']['digest']
    assert author.road_pool_wet_samples==saved['logging_trial']['pool_cells']
    assert les.save_current_level()
    saved['logging_trial']['dressing_backup']=str(backup)
    saved['inputs_digest']=inputs_digest
    tiles=dressing_ground=path=None
   import lidar_gravel_dust
   saved['gravel_dust']=lidar_gravel_dust.configure()
   assert les.save_current_level()
   # GP4b: the patch meshes can be re-imported in place (which resets their LOD screen sizes), so the fast path re-applies the LOD2 screen size (saved only when it differs).
   saved['gp2'].setdefault('clumps',{})['patch_lod_screen_sizes']=set_patch_lod_screen_sizes([u.load_asset(KIT+'/'+n) for n in CLUMP_PASTURE])
   saved.pop('error',None);saved.update(ok=True,saved_and_reloaded=True,level=LEVEL,original_maps_unchanged=True);report=saved;prior.write_text(json.dumps(report,indent=2));refs=author=sheet=surfaces=a=None;gc.collect();yield 2;les.load_level('/Engine/Maps/Entry');yield 8;return
 backup=ROOT/'Saved/LidarStudyBackups'/('Place-'+str(time.time_ns()));shutil.copytree(ROOT/'Content/GrandTour/ArtTests/LidarStudy',backup);report['backup']=str(backup);prune_backups(backup.parent)
 assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();refs=actors.get_all_level_actors()
 land=next(a for a in refs if isinstance(a,u.Landscape));surface=next(a for a in refs if isinstance(a,u.GTLandscapeSurface));visual=next(a for a in refs if isinstance(a,u.GTMudRunnerVisual));sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'));grass=next(a for a in refs if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
 old_author=next(a for a in refs if isinstance(a,u.GTProceduralGround));relief=next(a.relief_texture for a in refs if isinstance(a,u.GTProceduralRoad) and a.relief_texture)
 assert old_author.clear_generated(),old_author.last_message
 assert u.GTLandscapeSurfaceSetupLibrary.import_lidar_authoring_heights(land,str(OUT/'authoring-height.r16')),'Derived height import/readback failed'
 report['authoring']=data['authoring']
 for a in list(actors.get_all_level_actors()):
  if a in [land,surface,visual,sheet,grass]:continue
  if isinstance(a,u.GTLidarAuthoringPath):actors.destroy_actor(a);continue
  if isinstance(a,(u.GTProceduralGround,u.GTProceduralRoad,u.GTProceduralGroundRegion,u.GTMudRoute,u.PlayerStart,u.CameraActor)) or a.get_actor_label() in ['LidarStudy_Forest','LidarStudy_Understory','LidarStudy_Farm'] or a.get_actor_label().startswith('LidarStudy_LoggingDetail_') or (a.get_actor_label().startswith('LidarStudy_') and a.get_actor_label().endswith('Water')):actors.destroy_actor(a)
 refs=old_author=None
 textures={n:tex(n) for n in ['paint','style','macro','rest','clay']};gravel_texture();mats={n:ground(n,textures) for n in ['Terrain','Detail','Tread']};land.set_editor_property('landscape_material',mats['Terrain'])
 for fn,key in [(u.GTLandscapeSurfaceSetupLibrary.import_paint,'paint'),(u.GTLandscapeSurfaceSetupLibrary.import_material_atlas,'style'),(u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights,'rest'),(u.GTLandscapeSurfaceSetupLibrary.import_clay_atlas,'clay')]:assert fn(surface,textures[key]),key
 assert int(re.search(r'clay_atlas=(\d+)',surface.get_surface_report()).group(1))==2048,'CL2: clay atlas not imported'
 props(visual,material=mats['Detail'],track_material=mats['Tread']);props(surface,grass_is_visual_cover=True,mud_regions=[])
 # Explicitly persist every water material; missing transient M_Water was an
 # undetected fault in the original first-pass map.
 patches=[];wateractors=[];watermats=[]
 for spec in data['water']:
  d,a,m=water_patch(spec,world);patches.append(d);wateractors.append(a);watermats.append(m);yield 1
 domain=clone('/Game/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain','DA_WaterDomain');assert domain.import_bake(str(OUT.parent/'water-domain.bin'));assert domain.set_child_domains(patches);assets.save_loaded_asset(domain)
 props(sheet,water_domain=domain,domain_surfaces=wateractors,surface_material_path=watermats[-1].get_path_name(),ambient_wave_material=u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/Waves/M_NativeWavePrecombine'),ambient_wave_resolution=512);sheet.get_component_by_class(u.ProceduralMeshComponent).clear_all_mesh_sections()
 report['water_patches']=[d.get_path_name() for d in patches]
 # LP3b: do the kit materials expose a tint / base-colour multiplier? Recorded so the colour decision rests on the assets, not the importer code.
 report['kit_material_params']={}
 for mn in ['M_NZ_Foliage','M_NZ_Bark']:
  try:mm=u.load_asset(KIT+'/'+mn);report['kit_material_params'][mn]=dict(expression_types=sorted({e.get_class().get_name() for e in mel.get_material_expressions(mm)}),scalar_parameters=[str(n) for n in mel.get_scalar_parameter_names(mm)],vector_parameters=[str(n) for n in mel.get_vector_parameter_names(mm)])
  except Exception as err:report['kit_material_params'][mn]=dict(error=repr(err))
 # LP3c: tint instances of the kit materials (the kit's own Tint parameter, Art/Unreal/import_native_plants.py add_tint) and the ground peat record.
 mi_foliage=kit_instance('MI_NZ_Foliage_Bush',KIT+'/M_NZ_Foliage',BUSH_TINT);mi_bark=kit_instance('MI_NZ_Bark_Spar',KIT+'/M_NZ_Bark',SPAR_TINT)
 mi_canopy=kit_instance('MI_NZ_Foliage_Canopy',KIT+'/M_NZ_Foliage',CANOPY_TINT);report['lp3e']=dict(version=LP3E,instance=mi_canopy.get_path_name(),parent=KIT+'/M_NZ_Foliage',tint=list(CANOPY_TINT),canopy_slots={},far_cards={},pasture='superseded by GP2c (the tiled pasture node GP2cPasture; see report gp2c)')
 report['lp3c']=dict(version=LP3C,ground_peat=['M_Terrain','M_Detail'],instances={mi_foliage.get_path_name():dict(parent=KIT+'/M_NZ_Foliage',tint=list(BUSH_TINT)),mi_bark.get_path_name():dict(parent=KIT+'/M_NZ_Bark',tint=list(SPAR_TINT))},canopy_slots={},understory_slots={},spar_far_card=BASE+'/CanopyKit/M_FirFar_3')
 report['cl1']=dict(version=CL1,atlas=BASE+'/T_clay',atlas_channels='R clay weight, G orange cut face, B bush slurry, A 1',style_r_written=False,ground_materials=['M_Terrain','M_Detail'],nodes=dict(CL1_INFO),conditions={})
 report['lp3d']=dict(version=LP3D,ground_pasture=['M_Terrain','M_Detail'],mark=PASTURE_MARK,note='GP2c: the program returns the pre-pasture ground colour only; pasture colours, noise octaves and the 15% desaturation were removed (pasture is the GP2cPasture node)',grass_weight='smoothstep(.3,.8,style G) in GP2cPasture',mown_fraction=.08)
 report['gp2c']=dict(version=GP2C,nodes=dict(GP2C_INFO),tiles=gp2c_measure(),tiling_cm=GP2C_TILING_CM,blend_far=.35,far_rotation_deg=29,macro=dict(wavelength_m=12,brightness=.08,hue=0),dry_mix=dict(mown=.25,rank=.60,rank_style_g='.3 to .8, full below .62'),pasture_weight='smoothstep(.3,.8,style G) x (1-style R) x (1-peat mask)',normal=dict(texture=PACK_TEX+'T_Landscape_Grass_01_N',tiling_cm=GP2C_TILING_CM['normal'],strength=.5,full_within_m=20,zero_beyond_m=40),cover_tint=list(GP2C_COVER_TINT))
 report['rd1']=dict(version=RD1,relief_material=BASE+'/M_'+RELIEF_KIND,texture=GRAVEL_PATH,source=str(GRAVEL_SRC.relative_to(ROOT)),source_sha256=hashlib.sha256(GRAVEL_SRC.read_bytes()).hexdigest(),tiling_cm=RD1_TILING_CM,blend_far=RD1_BLEND_B,far_rotation_deg=RD1_FAR_DEG,saturation=RD1_SAT,tile_mean_after_saturation_linear=RD1_TILE_MEAN_AFTER_SAT,target_linear=RD1_TARGET_LINEAR,tint=RD1_TINT,wheel=RD1_WHEEL,corridor_full_m=2.0,corridor_none_m=2.6,lateral_atlas='T_clay alpha = d / 6.4 m + .5',nodes=dict(RD1_INFO),conditions=report['cl1']['conditions'],note='conditions is the same dict as cl1.conditions: filled per road below');report['cl2']=dict(version=CL2,atlas=BASE+'/T_clay',surface_clay_atlas=int(re.search(r'clay_atlas=(\d+)',surface.get_surface_report()).group(1)),note='ClayCells hold the T_clay source colours; SampleSurface reads R as the clay weight')
 import lidar_canopy_assets
 meshes=yield from lidar_canopy_assets.build(world);report['canopy']=lidar_canopy_assets.report;tint_far_card(3,SPAR_TINT)
 trees=json.loads((OUT/'trees.json').read_text());forest=spawn(u.Actor,'Forest');trunks=[]
 for kind,mesh in enumerate(meshes):
  trunks+=lidar_canopy_assets.trunk_transforms(mesh,trees,kind)
  c=u.GTVegetationSubsystem.add_tagged_instances(forest,mesh,lidar_canopy_assets.tree_transforms(mesh,trees,kind),'LidarStudyForest','NoCollision',True);c.set_cull_distances(380000,450000);props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  if kind==3:report['lp3c']['canopy_slots'][mesh.get_name()]=dict(material=mi_bark.get_name(),bark_slots=tint_slots(c,mesh,KIT+'/M_NZ_Bark',mi_bark))
  if kind in CANOPY_KINDS:report['lp3e']['canopy_slots'][mesh.get_name()]=dict(material=mi_canopy.get_name(),foliage_slots=tint_slots(c,mesh,KIT+'/M_NZ_Foliage',mi_canopy));tint_far_card(kind,CANOPY_TINT);report['lp3e']['far_cards'][mesh.get_name()]=BASE+'/CanopyKit/M_FirFar_'+str(kind)
  yield 1
 c=u.GTVegetationSubsystem.add_tagged_instances(forest,u.load_asset('/Engine/BasicShapes/Cylinder'),trunks,'LidarStudyTrunks','BlockAll',False);c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
 owner=spawn(u.Actor,'Understory');entries=json.loads((OUT/'understory.json').read_text());by={};report['understory_components']={}
 for item in entries:by.setdefault(item['kind'],[]).append(item)
 for name,items in sorted(by.items()):
  mesh=u.load_asset(KIT+'/'+name);assert mesh,name;b=mesh.get_bounds();ts=[]
  for item in items:
   x,y,z=item['p'];sc=item['height_cm']/max(1,2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(x,y,z-(b.origin.z-b.box_extent.z)*sc-3),rotation=u.Rotator(yaw=item['yaw']),scale=u.Vector(sc,sc,sc)))
  start,end=understory_class(name);solid=name.replace('SM_NZ_','').startswith(('TreeFern','Log_','Stump')) and hull_count(mesh)>0
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'LidarStudyUnderstory','BlockAll' if solid else 'NoCollision',any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')));c.set_cull_distances(start,end);props(c,cast_shadow_as_two_sided=any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')),visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  if solid:c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
  if name.replace('SM_NZ_','').startswith(FOLIAGE_TINT):report['lp3c']['understory_slots'][name]=dict(material=mi_foliage.get_name(),foliage_slots=tint_slots(c,mesh,KIT+'/M_NZ_Foliage',mi_foliage))
  report['understory_components'][name]=dict(instances=len(ts),cull_cm=[start,end],collision='QUERY_AND_PHYSICS (hulls %d)'%hull_count(mesh) if solid else 'none');yield 1
 roads=json.loads((OUT/'roads.json').read_text());points=[p for r in roads for p in r['points']];xs=[p[0] for p in points];ys=[p[1] for p in points]
 xmin=max(-184500,min(xs)-1400);xmax=min(184500,max(xs)+1400);ymin=max(-184500,min(ys)-1400);ymax=min(184500,max(ys)+1400);cx=(xmin+xmax)/2;cy=(ymin+ymax)/2
 author=spawn(u.GTProceduralGround,'Registered roads',(cx,cy,0));props(author,landscape=land,surface=surface,allow_large_sparse_road_bounds=True,seed=161026,output_asset_root=BASE+'/',paint_texture=textures['paint'],style_texture=textures['style'],macro_texture=textures['macro'],relief_material=mats[RELIEF_KIND],road_water_material=u.load_asset(TEMPLATE+'/M_RoadPools'),relief_spacing_cm=50.,scatter_rules=[])
 author.generation_bounds.set_box_extent(u.Vector((xmax-xmin)/2,(ymax-ymin)/2,30000),False);assert author.capture_base(),author.last_message
 for k,item in enumerate(roads):
  private=item['name'] in ['Riverside access','Pond field spur'];road=spawn(u.GTProceduralRoad,item['name'],(cx,cy,0));props(road,author=author,relief_texture=relief,width_cm=380. if private else 550.,bed_depth_cm=3.,mud_depth_cm=9. if private else 2.,wetness=.25,centre_grass_cover=.15 if private else .02,verge_grass_cover=.9,maximum_cut_fill_cm=60. if private else 22.,detail_seed=161026+k,relief_strength=.20 if private else .08)
  draft=item.get('authoring')
  if draft:
   props(road,width_cm=draft['width_m']*100,bed_depth_cm=0.,mud_depth_cm=draft['mud_depth_cm'],wetness=draft['wetness'],centre_grass_cover=.1,maximum_cut_fill_cm=draft['max_cut_fill_m']*100,relief_strength=draft.get('relief_strength',0),relief_texture=u.load_asset('/Game/GrandTour/ArtTests/ProceduralGround/RoadProfiles/T_dirt_path'),relief_default_width_cm=600.,relief_diffuse_aspect=2.)
   road.tags=list(road.tags)+['LidarMudTrack','LidarDesign:'+draft['id']]
  road.control_points.clear_spline_points(False)
  for i,(x,y) in enumerate(item['points']):
   xy=u.Vector2D(x,y);base_z=author.base_height_at(xy);z=item['elevations_cm'][i] if draft else base_z
   road.control_points.add_spline_point(u.Vector(x,y,z),u.SplineCoordinateSpace.WORLD,False)
   if draft:road.control_points.set_scale_at_spline_point(i,u.Vector(1,item['widths_cm'][i]/road.width_cm,1),False)
  road.control_points.update_spline();conditions=[]
  # Legacy geometry is retained at the protected house-end junction. The firm
  # road policy below removes yielding depth and suppresses relief elsewhere.
  length=item['length_m'];rows=[]
  rows=[('Firm gravel',0.,length,5,2,.90,.25,.02,0,25.,2.)]   # public roads; RD1b: mud 2 -> 5, rut 1 -> 2, firmness .95 -> .90 so a pass leaves a shallow rut
  if private:
   # RD1 (owner 2026-10-19: "they should be gravel roads"): the private roads and the bush climbs are gravel along their whole length (CL1 had Clay track / Clay slurry by corridor class); the Damp hollow stays. Clay is only where prepare's clay atlas R is (the cut band and the yard).
   rows=[('Gravel track',0.,length,9,3,.80,.25,.15,.05,25.,2.),('Damp hollow',length*.48,length*.58,28,9,.32,.8,.18,.3,25.,2.)]
  if draft:rows=[('Mud track',0.,length,draft['mud_depth_cm'],draft['rut_depth_cm'],draft['firmness'],draft['wetness'],.1,0.,0.,0.)]
  for label,a,b,depth,rut,firm,wet,cover,churn,spread,breakup in rows:
   conditions.append(props(u.GTRoadCondition(),name=label,start_metres=a,end_metres=b,blend_metres=12.,mud_depth_cm=float(depth),rut_depth_cm=float(rut),firmness=float(firm),wetness=float(wet),grass_cover=float(cover),water_fill_cm=0.,track_spread_cm=float(spread),churn=float(churn),crossing_tracks=.05,breakup_cm=float(breakup)))
  if draft:
   for c in draft.get('conditions',[]):conditions.append(props(u.GTRoadCondition(),**c))
  road.conditions=conditions
  if not draft:
   assert item['name'] in lidar_firm_roads.NAMES,item['name']
   lidar_firm_roads.configure(road)
   rows=[('Compacted gravel FR1',0.,length,0,0,1.,.25,.15 if private else .02,0,0,0)]
  report['cl1']['conditions'][item['name']]=[dict(name=r[0],start_m=round(float(r[1]),1),end_m=round(float(r[2]),1),mud_depth_cm=r[3],rut_depth_cm=r[4],firmness=r[5],wetness=r[6],grass_cover=r[7],churn=r[8],track_spread_cm=r[9],breakup_cm=r[10],blend_m=12.) for r in rows]
 report['firm_gravel']=dict(version=lidar_firm_roads.VERSION,roads=list(lidar_firm_roads.NAMES),profile_smoothing_m=16.,yielding_depth_cm=0.)
 assert author.rebuild(),author.last_message;report['road_generation']=dict(digest=author.output_digest,tiles=len(author.relief_tiles),triangles=author.relief_triangles,wet_pool_samples=author.road_pool_wet_samples);yield 5
 for t in textures.values():assert assets.save_loaded_asset(t)
 sites=json.loads((OUT/'sites.json').read_text())
 for s in sites:
  xy=u.Vector2D(*s['center']);h=author.base_height_at(xy)
  for tile in author.relief_tiles.values():
   o=tile.get_actor_location()
   if o.x<=xy.x<o.x+tile.span_cm and o.y<=xy.y<o.y+tile.span_cm:h=tile.height_at(xy);break
  s['center_height_cm']=h
 # LP4 farm hardware. Ground = the built relief tile under the point (the road bench, shoulders and cut/fill), else the captured landscape base: exactly how the sites above are seated.
 tiles=[(t.get_actor_location(),t.span_cm,t) for t in author.relief_tiles.values() if t];cell=max([sp for _,sp,_ in tiles]+[1.]);tgrid={}
 for o,sp,t in tiles:
  for i in range(math.floor(o.x/cell),math.floor((o.x+sp)/cell)+1):
   for j in range(math.floor(o.y/cell),math.floor((o.y+sp)/cell)+1):tgrid.setdefault((i,j),[]).append((o.x,o.y,sp,t))
 def farm_ground(gx,gy):
  xy=u.Vector2D(gx,gy)
  for ox,oy,sp,t in tgrid.get((math.floor(gx/cell),math.floor(gy/cell)),()):
   if ox<=gx<ox+sp and oy<=gy<oy+sp:return t.height_at(xy)
  return author.base_height_at(xy)
 hw=json.loads((OUT/'hardware.json').read_text());farm=spawn(u.Actor,'Farm');farm_tf={};report['farm_components']={};far_slope=0.
 for it in hw:
  x,y,_=it['p'];z=farm_ground(x,y);yaw=it['yaw'];pitch=0.;sx=1.
  if 'len_cm' in it:   # fence module and gate: follow the ground between their two posts (pitch the module, stretch it to the chord)
   L=it['len_cm'];yr=math.radians(yaw);z2=farm_ground(x+L*math.cos(yr),y+L*math.sin(yr));dz=z2-z;pitch=max(-15.,min(15.,math.degrees(math.atan2(dz,L))));sx=math.hypot(L,dz)/FARM_SPAN_CM[it['mesh']];far_slope=max(far_slope,abs(pitch))
  farm_tf.setdefault(it['mesh'],[]).append(u.Transform(location=u.Vector(x,y,z),rotation=u.Rotator(roll=0.,pitch=pitch,yaw=yaw),scale=u.Vector(sx,1.,1.)))
 for name,tfs in sorted(farm_tf.items()):
  mesh=u.load_asset(KIT+'/'+name);assert mesh and hull_count(mesh)>0,('farm mesh missing or without hulls',name)
  start,end=(25000,35000) if name in FARM_FAR else (15000,22000)
  c=u.GTVegetationSubsystem.add_tagged_instances(farm,mesh,tfs,'LidarStudyFarm','BlockAll',True);c.set_cull_distances(start,end);props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=False);c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
  report['farm_components'][name]=dict(instances=len(tfs),cull_cm=[start,end],collision='QUERY_AND_PHYSICS (hulls %d)'%hull_count(mesh));yield 1
 report['lp4']=dict(version=LP4,actor='LidarStudy_Farm',items=len(hw),components=len(farm_tf),max_module_pitch_deg=far_slope,by_mesh={k:len(v) for k,v in sorted(farm_tf.items())})
 import lidar_logging_trial as trial
 logging_path=trial.route(roads)
 if logging_path:
  report['logging_trial']=trial.verify_pools(author,sheet,logging_path,farm_ground)
  report['logging_trial']['dressing']=trial.dress(logging_path,farm_ground,spawn)
  report['logging_trial']['dressing_version']=trial.DRESSING_VERSION
  trial_start=trial.at(logging_path,3.)
  trial_z=farm_ground(trial_start[0],trial_start[1])
  trial_recovery=[]
  for station in (192.,270.,530.,637.):
   x,y,yaw=trial.at(logging_path,station)
   trial_recovery.append(u.Transform(location=u.Vector(x,y,farm_ground(x,y)+100),rotation=u.Rotator(yaw=yaw)))
 tiles=tgrid=farm_ground=farm_tf=hw=None
 (OUT/'installed-sites.json').write_text(json.dumps(sites,indent=2));start=sites[0]
 for a in [surface,visual]:a.set_actor_location(u.Vector(*start['center'],0),False,True)
 grass.grass.clear_instances();grass.grass_b.clear_instances();grass.grass_c.clear_instances();grass.distant_grass.clear_instances();grass.rank_grass.clear_instances()
 report['gp2']=dict(version=GP2,pasture_desaturation=0.,desaturation_note='GP2 mixed the ground pasture 15% toward its luminance; removed by GP2c',clumps=set_clump_props(grass),note='Polish builds M_LidarClump / M_LidarRank and assigns grass_material / rank_material / card_grass_material')
 route=spawn(u.GTMudRoute,'Route');props(route,title='BALD HILL / Waimeamea access',checkpoint_labels='1 Access entrance   2 Pond bend   3 Riverside house   4 Field spur',recovery_points=[u.Transform(location=u.Vector(*s['center'],s['center_height_cm']+80),rotation=u.Rotator(yaw=s['yaw'])) for s in sites])
 if logging_path:
  start=dict(center=list(trial_start[:2]),center_height_cm=trial_z,yaw=trial_start[2])
  props(route,title='LOGGING TRACK / dirt - fords - mud - bogs',
        recovery_points=[u.Transform(location=u.Vector(*start['center'],trial_z+80),rotation=u.Rotator(yaw=start['yaw']))]+trial_recovery+list(route.get_editor_property('recovery_points')),
        checkpoint_labels='1 Track start   2 First hollow   3 Rutted saddle   4 Wet shelf   5 Deep gully   6 Access   7 Pond   8 House   9 Field spur')
 spawn(u.PlayerStart,'Start',(*start['center'],start['center_height_cm']+80)).set_actor_rotation(u.Rotator(yaw=start['yaw']),False)
 # Location marker, not a fictitious architectural reconstruction.
 house=spawn(u.TargetPoint,'Survey anchor - riverside house',(-52264.44549,-26256.74983,0));house.set_actor_hidden_in_game(True)
 import lidar_authoring_editor
 lidar_authoring_editor.load_designs()
 if (OUT/'levelpolish.json').exists():
  import lidar_level_polish
  report['level_polish']=yield from lidar_level_polish.install()
 if (ROOT/'Art/Export/LidarStudy/Homestead/layout.json').exists():
  import lidar_homestead
  report['homestead']=lidar_homestead.place()
 import lidar_gravel_dust
 report['gravel_dust']=lidar_gravel_dust.configure()
 if (OUT/'reference-style.json').exists():
  import lidar_reference_style
  report['reference_style']=lidar_reference_style.apply()
 import canopy_depth
 if canopy_depth.enabled():report['canopy_depth']=canopy_depth.apply()
 assert les.save_current_level();report.update(trees=len(trees),understory=len(entries),roads=len(roads),terrain_source_unchanged=True)
 # Release transient references before loading another world.
 world=land=surface=visual=sheet=grass=author=road=forest=owner=c=a=house=route=tile=None;wateractors=[];gc.collect();assert les.load_level('/Engine/Maps/Entry');yield 3
 assert les.load_level(LEVEL);loaded=actors.get_all_level_actors();sheet=next(a for a in loaded if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'));assert len(sheet.get_editor_property('domain_surfaces'))==3
 for a in sheet.get_editor_property('domain_surfaces'):assert a and a.static_mesh_component.get_material(0), 'Missing saved water material'
 assert u.load_asset(sheet.get_editor_property('surface_material_path'));assert protected()==before
 report.update(ok=True,saved_and_reloaded=True,level=LEVEL,original_maps_unchanged=True,inputs_digest=inputs_digest);(OUT/'install.json').write_text(json.dumps(report,indent=2));loaded=sheet=None;gc.collect();les.load_level('/Engine/Maps/Entry');yield 3

steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global deadline,busy
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1700,'Install timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);globals()['steps']=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();(OUT/'install.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
