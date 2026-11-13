"""Repair the transferred wave bindings, shore sampling and tree root placement."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/install_lidar_place.py').read_text().split('def run():')[0],'<lidar-place-helpers>','exec'))
report=dict(ok=False,driving_tested=False)
# LP3e: warmer, less blue pasture numbers (LP3d was near tint (.48,.88,.42), distance diffuse (.60,.95,.55), cover tint (.70,1,.55)); spacing 35 cm and BladeScale .8 on the grass actor (the 30 cm floor and the two
# properties are GTMixedGroundDetails C++); STRAW is the rank-band colour multiplier on the near cards' diffuse, driven by per-instance custom data 3 (style G .3 to .8, GTMixedGroundStreaming.cpp).
GRASS_NEAR_TINT=(.52,.82,.36);GRASS_DIFFUSE=(.62,.88,.46);COVER_TINT=(.85,1.0,.70)
assert tuple(COVER_TINT)==tuple(GP2C_COVER_TINT),('GP2c solved the pasture tint against another cover tint than Polish applies',COVER_TINT,GP2C_COVER_TINT)   # the GP2c tint accounts for this downstream multiplier (Install)
GRASS_SPACING_CM=CARD_SPACING_CM;BLADE_SCALE=.8;RANK_BAND_SCALE=1.4;STRAW=(1.25,1.05,.55)   # GP2: 45 cm is the card fallback's spacing (gt.Grass.Clumps 0); the clump lattice is ClumpSpacingCm 40 (GP2d, the C++ floor)
# GP2 clump materials: clones of the card material M_LidarGrass whose colour node takes the mesh vertex colour (linear, dark base to yellow-green tip) instead of the diffuse texture, times GrassBaseTint; the opacity mask
# loses the texture alpha (the clump is real geometry). Wind, contact decoding, per-instance fade, subsurface and the LP3eStraw wrapper (reads 0 for clumps) are the card material's own nodes.
CLUMP_TAG='GP2Clump';CLUMP_TINT=(.88,.96,.60);RANK_TINT=(1.,1.,1.)   # GS1 keeps these: the GS1Style macro colour pair is expressed relative to the tint (pair / tint), so the colour that reaches the shading is vertex colour x pair
CLUMP_COLOUR_CODE='// GP2 clump colour: Diffuse is the mesh vertex colour (linear albedo as authored), Tint is GrassBaseTint.'+chr(10)+'return max(Diffuse*Tint,0);'
# GP4b (docs/LIDAR_PLACE_PLAN.md GP4): the clump materials fade with a dither instead of the clip value (GP4Dither: PerInstanceFadeAmount, which the pasture cull distances 30 to 38 m drive, against an interleaved-gradient noise, so the
# patches thin out over the 8 m band; the card material multiplied the fade into the opacity mask, which for solid geometry makes every instance vanish at once where the fade crosses the clip value), and M_LidarClump takes its wind weight from
# the mesh vertex alpha (GP4Wind: the recovered grass program's offset, wind and contact bend, times the vertex alpha (Parameters.VertexColor.a in the custom node), 0 at the blade base and 1 at the tip, passed through unchanged for a removed instance so a removed patch still sinks whole).
# The program has no weight input (it computes step(5 cm, Local.z) inside), so the weight is applied to its output. NativeGrassWindScale (the program's own amplitude: +-2.5 cm x scale at full weight) goes to CLUMP_WIND_SCALE because only the upper blade moves now.
DITHER_TAG='GP4Dither';WIND_TAG='GP4Wind';CLUMP_WIND_SCALE=2.0   # GS1: still 2.0; the recovered program's own sway is switched off by GS1 (its WindScale input is wired to 0) and the parameter scales GS1Wind's sway instead (2.25 cm x scale at the tip)
DITHER_CODE='// GP4 distance fade: Fade is PerInstanceFadeAmount (1 at the cull start, 0 at the cull end), Pixel the screen pixel; interleaved-gradient dither, masked.'+chr(10)+'float ign=frac(52.9829189*frac(dot(Pixel.xy,float2(0.06711056,0.00583715))));return saturate(Fade)>ign?1.0:0.0;'
WIND_CODE='// GP4 wind weight: Base is the recovered grass program offset (wind and contact bend), Removed the instance flag (per-instance custom data 2); the weight is the mesh vertex alpha (0 at the blade base, 1 at the tip), read from the vertex parameters because the VertexColor node only exposes RGB by name.'+chr(10)+'return Removed>.5 ? Base : Base*saturate(Parameters.VertexColor.a);'
STRAW_TAG='LP3eStraw'
STRAW_CODE='// LP3e rank-band straw: Straw is per-instance custom data 3 (0 to 1). The diffuse (gamma) is multiplied by lerp(1,(1.25,1.05,.55),Straw) before the colour is linearised, so the linear albedo scales by its 2.2 power.'+chr(10)+'return Base*pow(lerp(float3(1,1,1),float3(%s),saturate(Straw)),2.2);'%','.join(str(v) for v in STRAW)
# GS1 (docs/LIDAR_PLACE_PLAN.md GS1, owner 2026-10-19 "Go for a Breath of the Wild style grass"): the clump materials are re-lit in a stylised way by two wrapper custom nodes added by Polish. GS1Style sits BEFORE the straw wrapper (colour node -> GS1Style -> LP3eStraw -> BaseColor,
# so LP3eStraw is still the node that feeds BaseColor) and also feeds Normal (vertex normal blended 70% toward world up), SubsurfaceColor (tip colour x .6) and EmissiveColor (flower heads); roughness .55 and specular .35 are constants on a Two-Sided Foliage shading model.
# GS1Wind sits BEFORE GP4Wind (recovered program -> GS1Wind -> GP4Wind -> world position offset): the program's own sway is switched off (its WindScale input is wired to a constant 0, so it keeps only the contact bend and the removed-instance sink), GS1Wind adds the travelling sway and
# gusts, and GP4Wind still multiplies the lot by the vertex alpha and passes removed instances through. Both rebuild their own nodes on every run (the nodes are tagged GS1Style / GS1Wind), so the result is the same on a re-run.
GS1_TAG='GS1Style';GS1_WIND_TAG='GS1Wind';GS1_ROUGH=.70;GS1_SPEC=.10   # the brief says .55 / .35; with the flat normal that gave a cream sun glare on every field seen toward the sun (Paddock_gate far field 170,165,119 against 103,113,38 before), see the report
GS1_MACRO=dict(clump=((.72,.95,.60),(1.0,.95,.62)),rank=((.90,.96,.78),(1.0,.96,.68)))   # cooler green / warmer yellow-green multipliers on the vertex colour (divided by the material's GrassBaseTint in code, which already multiplies the colour node); the rank band (straw) takes a mild pair, its colour is the straw multiplier
GS1_NOISE='struct GS1N{float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);} float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+float2(1,1)),f.x),f.y);}};GS1N gn;'
GS1_CODE=GS1_NOISE+'''
// GS1 stylised grass. Base = linear albedo (vertex colour x GrassBaseTint: the authored dark base to bright tip gradient; the straw wrapper multiplies the result afterwards), VN vertex normal (world), Eye camera vector (towards the camera), Sun direction TOWARDS the sun (AtmosphericLightVector),
// P world position, Camera camera position, Rand PerInstanceRandom (0 to 1 per patch). Outputs: BaseColor (return), Normal (flattened), Sub (translucency), Emissive (flower heads).
float3 vc=Parameters.VertexColor.rgb;float a=saturate(Parameters.VertexColor.a);
float3 fn=normalize(lerp(normalize(VN),float3(0,0,1),.7));
// flower heads (white or pale purple vertex colour): green is not the dominant channel, or low saturation and high value, or R>.6 and B>.4
float mx=max(vc.r,max(vc.g,vc.b)),mn=min(vc.r,min(vc.g,vc.b));
float lowSat=(mx>.5&&(mx-mn)<.15*mx)?1.0:0.0;float purple=(vc.r>.6&&vc.b>.4)?1.0:0.0;
float flower=saturate(max(1-smoothstep(0,.03,vc.g-max(vc.r,vc.b)),max(lowSat,purple)));
// macro colour: a 6 m world noise (plus a 24 m octave) pushed by the per-patch random, as a multiply between the cooler green and the warmer yellow-green
float nz=.7*gn.n(P.xy/600.)+.3*gn.n(P.xy/2400.+31.);
float k=smoothstep(0.,1.,saturate(.5+(nz-.5)*3.2*lerp(.6,1.,Rand)+(Rand-.5)*.3));
float3 macro=lerp(float3(<COOL>),float3(<WARM>),k);
// gradient and tip: authored gradient reshaped by pow(alpha,.7), +15% in the top quarter (alpha>.75), plus a sun-facing highlight on the tips
float g=pow(a,.7);float3 col=Base*macro*lerp(.7,1.,g);
float tipM=smoothstep(.75,.9,a);col*=1+.15*tipM;
float hl=pow(saturate(dot(fn,normalize(Sun))),4);col+=tipM*hl*.25*float3(.85,1,.4);
// rim: pale yellow-green where a blade is seen edge-on (the vertex normal only 30% flattened: with the 70% flat normal the term was a view-angle ramp that paled the whole mid field), stronger toward the tips and gone beyond the fade so the ground can match
float dist=length(P.xy-Camera.xy)*.01;float3 rn=normalize(lerp(normalize(VN),float3(0,0,1),.3));float rim=pow(1-abs(dot(normalize(Eye),rn)),3)*.15;
col+=rim*lerp(.3,1.,a)*(1-smoothstep(12,30,dist))*float3(.62,.78,.34);
col=lerp(col,vc,flower);
Normal=fn;Sub=lerp(float3(.30,.40,.10)*macro*.2*lerp(.35,1.,g),vc*.2,flower);Emissive=flower*.10*(vc/max(mx,.01))*(1-smoothstep(10,25,dist));
return max(col,0);'''
GS1_WIND_CODE=GS1_NOISE+'''
// GS1 wind: Base is the recovered grass program (its own sway is off here: its WindScale input is 0, so it is the contact bend and the removed-instance sink only), Removed the instance flag, P the world position without shader offsets, Time seconds, Scale the
// NativeGrassWindScale parameter (2). Two travelling sine waves in world space (3.5 m at .8 m/s along 25 degrees, 11 m at 1.6 m/s along 45 degrees: 20 degrees apart) and a gust from a 25 m noise travelling at 2.5 m/s (amplitude x2 where the noise is above .6), along 35 degrees,
// with a vertical dip of .15 x the horizontal so a bent blade shortens. The vertex alpha weight is applied here once and once more by GP4Wind downstream, so the sway goes with alpha squared (0 at the blade base, 1 at the tip): 4.5 cm at the tip in calm, 9 cm in a gust.
float a=saturate(Parameters.VertexColor.a);float2 m=P.xy*.01;
float2 d1=float2(.9063,.4226),d2=float2(.7071,.7071),dw=float2(.8192,.5736);
float w1=sin(6.2831853*(dot(m,d1)-.8*Time)/3.5);float w2=sin(6.2831853*(dot(m,d2)-1.6*Time)/11.);
float gust=gn.n((m-dw*2.5*Time)/25.);float amp=1+smoothstep(.55,.65,gust);
float push=saturate(.55+.45*(.6*w1+.4*w2));float h=2.25*Scale*a*push*amp;
return Removed>.5 ? Base : Base+float3(dw*h,-.15*h);'''
def dither_fade(mat):
 """GP4b: the opacity mask becomes the GP4Dither node (PerInstanceFadeAmount against an interleaved-gradient noise). Idempotent; returns what it did."""
 cur=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_OPACITY_MASK);assert cur is not None
 if str(cur.get_editor_property('desc'))==DITHER_TAG:cur.set_editor_property('code',DITHER_CODE);return 'updated'
 g=Graph(mat,DITHER_TAG);n=g.custom(['Fade','Pixel'],DITHER_CODE,u.CustomMaterialOutputType.CMOT_FLOAT1)
 g.wire(g.node(u.MaterialExpressionPerInstanceFadeAmount),n,'Fade');g.wire(g.node(u.MaterialExpressionScreenPosition),n,'Pixel','PixelPosition');g.output(n,u.MaterialProperty.MP_OPACITY_MASK);return 'added'
def wind_alpha(mat):
 """GP4b: the world position offset becomes GP4Wind (the recovered program's output times the vertex alpha, removed instances passed through). Idempotent; returns what it did."""
 cur=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);assert cur is not None
 if str(cur.get_editor_property('desc'))==GS1_WIND_TAG:return 'first GS1 structure (GS1Wind in place of GP4Wind): gs1_wind rebuilds GP4Wind'   # the first GS1 run replaced GP4Wind with GS1Wind; gs1_wind migrates it
 if str(cur.get_editor_property('desc'))==WIND_TAG:cur.set_editor_property('code',WIND_CODE);return 'updated'
 oo=mel.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 g=Graph(mat,WIND_TAG);n=g.custom(['Base','Removed'],WIND_CODE)
 g.wire(cur,n,'Base',oo);g.wire(g.node(u.MaterialExpressionPerInstanceCustomData,data_index=2),n,'Removed');g.output(n,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);return 'added'
def clump_material(name,tint,wind=False,kind='clump'):
 """GP2: M_LidarClump / M_LidarRank = clone of M_LidarGrass (already tinted and straw-wrapped) with the vertex colour feeding the colour node and a constant 1 in place of the texture alpha. GP4b: the opacity mask is the GP4Dither node, and with wind=True the
 world position offset takes the vertex alpha as its weight (GP4Wind, amplitude NativeGrassWindScale = CLUMP_WIND_SCALE). Idempotent; returns what it did."""
 mat=clone(BASE+'/M_LidarGrass',name);ex=list(mel.get_material_expressions(mat))
 col=[e for e in ex if isinstance(e,u.MaterialExpressionCustom) and [str(i.get_editor_property('input_name')) for i in e.get_editor_property('inputs')]==['Diffuse','Tint']]
 # The recovered card material carries a second, orphaned copy of the colour node (its Tint input is unwired and nothing reads it); the live one has both inputs wired.
 live=[e for e in col if all(x is not None for x in mel.get_inputs_for_material_expression(mat,e))];assert len(live)==1,('colour node',name,len(col),len(live));col=live[0]
 mask=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_OPACITY_MASK);assert isinstance(mask,(u.MaterialExpressionMultiply,u.MaterialExpressionCustom)),('opacity mask node',name,mask)
 vc=[e for e in ex if isinstance(e,u.MaterialExpressionVertexColor) and str(e.get_editor_property('desc'))==CLUMP_TAG];row=dict(material=mat.get_path_name(),vertex_colour='kept' if vc else 'added')
 if not vc:
  assert isinstance(mask,u.MaterialExpressionMultiply),('opacity mask node',name,mask)
  g=Graph(mat,CLUMP_TAG);vcn=g.node(u.MaterialExpressionVertexColor);g.wire(vcn,col,'Diffuse');g.wire(g.scalar(1.),mask,'A')
 col.set_editor_property('code',CLUMP_COLOUR_CODE);tints=0
 for e in mel.get_material_expressions(mat):
  if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GrassBaseTint':e.set_editor_property('default_value',u.LinearColor(*tint,1));tints+=1
 assert tints>=1,('GrassBaseTint',name,tints);row.update(base_tint=list(tint),straw=straw_wrap(mat),dither=dither_fade(mat))
 if wind:
  row['wind_alpha']=wind_alpha(mat);scales=[e for e in mel.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='NativeGrassWindScale'];assert scales,('NativeGrassWindScale',name)
  row['wind_scale_before']=float(scales[0].get_editor_property('default_value'))
  for e in scales:e.set_editor_property('default_value',CLUMP_WIND_SCALE)
  row['wind_scale']=CLUMP_WIND_SCALE
 row['gs1']=gs1_style(mat,kind,tint)
 if wind:row['gs1_wind']=gs1_wind(mat)
 row['custom_nodes']=gs1_graph(mat)
 errs=mel.recompile_material(mat);assert not errs,('GS1 compile',name,list(errs));assert assets.save_loaded_asset(mat);return mat,row
def straw_wrap(mat):
 """Wraps the near grass material's BaseColor in the LP3eStraw custom node (inputs Base and Straw = PerInstanceCustomData 3), built fully wired before it is spliced in; the subsurface colour (a Multiply of the old colour node) is rewired to the wrapper. Idempotent; returns what it did."""
 cur=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR);assert cur is not None
 if str(cur.get_editor_property('desc'))==GS1_TAG:   # GS1: GS1Style wraps the straw wrapper; its Base input is the straw wrapper, whose code is refreshed
  names=[str(i.get_editor_property('input_name')) for i in cur.get_editor_property('inputs')];inner=list(mel.get_inputs_for_material_expression(mat,cur))[names.index('Base')];assert inner is not None and str(inner.get_editor_property('desc'))==STRAW_TAG,('GS1Style Base is not the straw wrapper',inner)
  inner.set_editor_property('code',STRAW_CODE);return dict(base_colour='updated (under GS1Style)',subsurface='GS1Style')
 if str(cur.get_editor_property('desc'))==STRAW_TAG:cur.set_editor_property('code',STRAW_CODE);return dict(base_colour='updated',subsurface='kept')
 oo=mel.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR);g=Graph(mat,STRAW_TAG);n=g.custom(['Base','Straw'],STRAW_CODE);idx=g.node(u.MaterialExpressionPerInstanceCustomData,data_index=3)
 g.wire(cur,n,'Base',oo);g.wire(idx,n,'Straw')
 sub=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_SUBSURFACE_COLOR);sub_note='no subsurface node'
 if sub is not None and isinstance(sub,u.MaterialExpressionMultiply):
  ins=list(mel.get_inputs_for_material_expression(mat,sub));pin=next((name for name,x in zip(['A','B'],ins) if x is not None and x.get_name()==cur.get_name()),None)
  if pin:g.wire(n,sub,pin);sub_note='rewired '+pin
  else:sub_note='subsurface multiply does not take the old colour node'
 elif sub is not None:sub_note='subsurface node is '+sub.get_class().get_name()
 g.output(n,u.MaterialProperty.MP_BASE_COLOR);return dict(base_colour='wrapped',subsurface=sub_note)
def gs1_style(mat,kind,tint):
 """GS1: the stylised lighting wrapper. One custom node (GS1_CODE) fed by the colour node (Base = vertex colour x GrassBaseTint), VertexNormalWS, CameraVectorWS, AtmosphericLightVector, WorldPosition (no shader offsets), CameraPositionWS and PerInstanceRandom, feeding
 the LP3eStraw wrapper's Base (so LP3eStraw still feeds BaseColor), Normal (output Normal), SubsurfaceColor (Sub) and EmissiveColor (Emissive); roughness and specular constants; the shading model is Two-Sided Foliage. The GS1Style nodes are rebuilt on every run, and the first GS1 structure
 (GS1Style feeding BaseColor with the straw wrapper under it) is migrated. Returns what it did."""
 P=u.MaterialProperty;tag=lambda e:str(e.get_editor_property('desc'))
 def src(e,name):return list(mel.get_inputs_for_material_expression(mat,e))[[str(i.get_editor_property('input_name')) for i in e.get_editor_property('inputs')].index(name)]
 cur=mel.get_material_property_input_node(mat,P.MP_BASE_COLOR);assert cur is not None
 straw=src(cur,'Base') if tag(cur)==GS1_TAG else cur;assert tag(straw)==STRAW_TAG,('GS1Style needs the LP3eStraw wrapper',tag(straw))
 first=src(straw,'Base');colour=src(first,'Base') if tag(first)==GS1_TAG else first;assert colour is not None
 old=[e for e in mel.get_material_expressions(mat) if tag(e)==GS1_TAG]   # taken before the new nodes exist; deleted only after everything is rewired (every set_editor_property or deletion that leaves a half-wired graph recompiles the material and logs a compile failure)
 row=dict(replaced_nodes=len(old),migrated_first_structure=tag(cur)==GS1_TAG,shading_model_before=str(mat.get_editor_property('shading_model')),two_sided_before=bool(mat.get_editor_property('two_sided')),tangent_space_normal_before=bool(mat.get_editor_property('tangent_space_normal')))
 if mat.get_editor_property('shading_model')!=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE:mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
 if not mat.get_editor_property('two_sided'):mat.set_editor_property('two_sided',True)
 if mat.get_editor_property('tangent_space_normal'):mat.set_editor_property('tangent_space_normal',False)
 cool,warm=[[round(a/t,5) for a,t in zip(pair,tint)] for pair in GS1_MACRO[kind]];code=GS1_CODE.replace('<COOL>',','.join(str(v) for v in cool)).replace('<WARM>',','.join(str(v) for v in warm))
 g=Graph(mat,GS1_TAG);n=g.custom(['Base','VN','Eye','Sun','P','Camera','Rand'],code,outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Sub',u.CustomMaterialOutputType.CMOT_FLOAT3),('Emissive',u.CustomMaterialOutputType.CMOT_FLOAT3)])
 sun_cls=getattr(u,'MaterialExpressionAtmosphericLightVector',None);assert sun_cls is not None,'unreal.MaterialExpressionAtmosphericLightVector is missing (the AtmosphereSunLightVector node)'
 g.wire(colour,n,'Base');g.wire(g.node(u.MaterialExpressionVertexNormalWS),n,'VN');g.wire(g.node(u.MaterialExpressionCameraVectorWS),n,'Eye');g.wire(g.node(sun_cls),n,'Sun')
 g.wire(g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),n,'P');g.wire(g.node(u.MaterialExpressionCameraPositionWS),n,'Camera');g.wire(g.node(u.MaterialExpressionPerInstanceRandom),n,'Rand')
 g.wire(n,straw,'Base');g.output(straw,P.MP_BASE_COLOR);g.output(n,P.MP_NORMAL,'Normal');g.output(n,P.MP_SUBSURFACE_COLOR,'Sub');g.output(n,P.MP_EMISSIVE_COLOR,'Emissive')
 g.output(g.scalar(GS1_ROUGH),P.MP_ROUGHNESS);g.output(g.scalar(GS1_SPEC),P.MP_SPECULAR)
 for e in old:mel.delete_material_expression(mat,e)
 row.update(nodes=[e.get_class().get_name() for e in mel.get_material_expressions(mat) if tag(e)==GS1_TAG],base_colour_node=tag(mel.get_material_property_input_node(mat,P.MP_BASE_COLOR)),macro_cool=list(GS1_MACRO[kind][0]),macro_warm=list(GS1_MACRO[kind][1]),macro_relative_to_tint=dict(cool=cool,warm=warm,tint=list(tint)),roughness=GS1_ROUGH,specular=GS1_SPEC,flat_normal_blend=.7,subsurface='tip colour (.30,.40,.10) x macro x .2 x lerp(.35,1,pow(alpha,.7)) (brief: x .6, which bleached backlit grass to cream)',tip_boost='+15% luminance for vertex alpha > .75',
  sun_highlight='pow(saturate(dot(flatN,SunDir)),4) x .25 on the tips',rim='pow(1-abs(dot(Eye,N30)),3) x .15 pale yellow-green x lerp(.3,1,alpha), N30 = vertex normal 30% toward up; fades out 12 to 30 m',flower_emissive=.10,shading_model_after=str(mat.get_editor_property('shading_model')),code_sha=hashlib.sha256(code.encode()).hexdigest()[:12])
 return row
def gs1_graph(mat):
 """GS1 diagnostic: every custom node with its tag and, per input, the class and tag of what feeds it (None = unwired), plus what feeds the properties that matter."""
 tag=lambda e:str(e.get_editor_property('desc'));P=u.MaterialProperty;out=[]
 for e in mel.get_material_expressions(mat):
  if isinstance(e,u.MaterialExpressionCustom):
   names=[str(i.get_editor_property('input_name')) for i in e.get_editor_property('inputs')];ins=list(mel.get_inputs_for_material_expression(mat,e))
   out.append(dict(tag=tag(e),name=e.get_name(),inputs={n:(None if x is None else x.get_class().get_name().replace('MaterialExpression','')+':'+tag(x)) for n,x in zip(names,ins)}))
 props=dict((n,(lambda x:None if x is None else x.get_class().get_name().replace('MaterialExpression','')+':'+tag(x)+':'+x.get_name())(mel.get_material_property_input_node(mat,p))) for n,p in [('BaseColor',P.MP_BASE_COLOR),('Normal',P.MP_NORMAL),('Subsurface',P.MP_SUBSURFACE_COLOR),('Emissive',P.MP_EMISSIVE_COLOR),('Roughness',P.MP_ROUGHNESS),('Specular',P.MP_SPECULAR),('Opacity mask',P.MP_OPACITY_MASK),('World position offset',P.MP_WORLD_POSITION_OFFSET)])
 return dict(custom=out,properties=props)
def gs1_wind(mat):
 """GS1: the sway. GS1Wind (GS1_WIND_CODE) goes between the recovered program and GP4Wind: its Base is the program, Removed the per-instance custom data 2 GP4Wind already reads, P the world position, Time the time and Scale the NativeGrassWindScale parameter the program had; the program's own
 WindScale input is rewired to a constant 0, so the program keeps the contact bend and the removed sink and loses its sway. Rebuilt on every run (same result); the first GS1 structure (GS1Wind in place of GP4Wind) is migrated back to GP4Wind. Returns what it did."""
 P=u.MaterialProperty;tag=lambda e:str(e.get_editor_property('desc'))
 def src(e,name):return list(mel.get_inputs_for_material_expression(mat,e))[[str(i.get_editor_property('input_name')) for i in e.get_editor_property('inputs')].index(name)]
 wpo=mel.get_material_property_input_node(mat,P.MP_WORLD_POSITION_OFFSET);assert wpo is not None;t=tag(wpo);assert t in (WIND_TAG,GS1_WIND_TAG),('world position offset is neither GP4Wind nor the first GS1Wind',t)
 removed=src(wpo,'Removed')
 if t==WIND_TAG:
  b=src(wpo,'Base')
  if tag(b)==GS1_WIND_TAG:prog=src(b,'Base');scale=src(b,'Scale');was='GS1Wind before GP4Wind (rebuilt)'
  else:prog=b;scale=src(prog,'WindScale');was='GP4Wind fed by the recovered program'
  gp=wpo
 else:prog=src(wpo,'Base');scale=src(prog,'WindScale');gp=None;was='first GS1 structure (GS1Wind in place of GP4Wind), migrated'
 assert prog is not None and removed is not None and scale is not None and isinstance(scale,u.MaterialExpressionScalarParameter) and str(scale.get_editor_property('parameter_name'))=='NativeGrassWindScale',('GS1Wind sources',was,prog,removed,scale)
 old=[e for e in mel.get_material_expressions(mat) if tag(e)==GS1_WIND_TAG]   # deleted only after the new nodes are wired, so the graph is never half-wired
 if gp is None:
  gw=Graph(mat,WIND_TAG);gp=gw.custom(['Base','Removed'],WIND_CODE);gw.wire(removed,gp,'Removed');gw.output(gp,P.MP_WORLD_POSITION_OFFSET)
 g=Graph(mat,GS1_WIND_TAG);n=g.custom(['Base','Removed','P','Time','Scale'],GS1_WIND_CODE)
 g.wire(prog,n,'Base');g.wire(removed,n,'Removed');g.wire(g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),n,'P');g.wire(g.node(u.MaterialExpressionTime),n,'Time');g.wire(scale,n,'Scale')
 g.wire(n,gp,'Base');g.wire(g.scalar(0.),prog,'WindScale')
 for e in old:mel.delete_material_expression(mat,e)
 return dict(was=was,rebuilt_nodes=len(old),chain='recovered program (WindScale input 0) -> GS1Wind -> GP4Wind -> world position offset',waves='3.5 m at .8 m/s along 25 deg, 11 m at 1.6 m/s along 45 deg; gust 25 m noise at 2.5 m/s, x2 above .6; lean along 35 deg',tip_offset_cm_at_scale_2=dict(calm=4.5,gust=9.0),vertical_dip=-.15,weight='vertex alpha squared (GS1Wind x alpha, GP4Wind x alpha)',
  base_program_kept=prog.get_class().get_name(),code_sha=hashlib.sha256(GS1_WIND_CODE.encode()).hexdigest()[:12])
COVER_TINT_CODE='float g=Texture2DSampleLevel(Style,StyleSampler,saturate((P.xy+185000)/370000),0).g;return Native*lerp(float3(1,1,1),float3(%s),g);'%','.join(str(v) for v in COVER_TINT)
def run():
 before=protected();backup=ROOT/'Saved/LidarStudyBackups'/('VisualRepair-'+str(time.time_ns()));shutil.copytree(ROOT/'Content/GrandTour/ArtTests/LidarStudy',backup);report['backup']=str(backup);prune_backups(backup.parent)
 assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();refs=actors.get_all_level_actors();sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'));grass=next(a for a in refs if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player);forest=next(a for a in refs if a.get_actor_label()=='LidarStudy_Forest')
 for a in list(sheet.get_editor_property('domain_surfaces')):actors.destroy_actor(a)
 patches=[];surfaces=[];watermats=[]
 for spec in data['water']:
  d,a,m=water_patch(spec,world);patches.append(d);surfaces.append(a);watermats.append(m);yield 1
 domain=sheet.get_editor_property('water_domain')
 base_domain=u.load_asset(BASE+'/DA_WaterDomain');base_names={d.get_path_name() for d in base_domain.road_patches}
 generated=[d for d in domain.road_patches if d.get_path_name() not in base_names]
 assert domain.set_child_domains(patches+generated)
 # Generated composites belong to the level; only standalone domains save as assets.
 if domain==base_domain:assets.save_loaded_asset(domain)
 report['preserved_generated_water_domains']=len(generated)
 wave=u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/Waves/M_NativeWavePrecombine');assert wave
 props(sheet,domain_surfaces=surfaces,surface_material_path=watermats[-1].get_path_name(),ambient_wave_material=wave,ambient_wave_resolution=512)
 # Bind recovered grass to greener temperate vegetation. Its wind, contact
 # decoding, opacity and deformation programs stay unchanged. LP3d: near cards take GrassBaseTint (.48,.88,.42) (their only tint; the recovered colour node is
 # pow(max(Diffuse*Tint,0),2.2)), the distance cover has no tint parameter and takes the Diffuse multiply (.60,.95,.55) in its colour node, rewritten by pattern so a re-run updates it.
 grass_report=dict(spacing_cm_before=float(grass.get_editor_property('grass_spacing_cm')));cover_report={}
 for prop,name in [('grass_material','M_LidarGrass'),('distant_grass_material','M_LidarGrassDistance')]:
  source=grass.get_editor_property(prop);mat=clone(source.get_path_name(),name);changed=0;row=dict(base_tint=None,diffuse_multiply=None)
  for e in mel.get_material_expressions(mat):
   if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GrassBaseTint':e.set_editor_property('default_value',u.LinearColor(*GRASS_NEAR_TINT,1));changed+=1;row['base_tint']=list(GRASS_NEAR_TINT)
   if isinstance(e,u.MaterialExpressionCustom):
    code=str(e.get_editor_property('code'));new=re.sub(r'Diffuse\*float3\([^)]*\)','Diffuse*float3(%s)'%','.join(str(v) for v in GRASS_DIFFUSE),code)
    if new==code:new=code.replace('pow(max(Diffuse,0),2.2)','pow(max(Diffuse*float3(%s),0),2.2)'%','.join(str(v) for v in GRASS_DIFFUSE))
    if code!=new:e.set_editor_property('code',new);changed+=1;row['diffuse_multiply']=list(GRASS_DIFFUSE)
    elif 'float3(%s)'%','.join(str(v) for v in GRASS_DIFFUSE) in code:row['diffuse_multiply']=list(GRASS_DIFFUSE)
  if prop=='grass_material':row['straw']=straw_wrap(mat);changed+=1
  assert changed or source==mat;assert not mel.recompile_material(mat);assets.save_loaded_asset(mat);grass.set_editor_property(prop,mat);cover_report[name]=row
 # GP2: the loop above leaves grass_material = M_LidarGrass; that is now the CARD material (card_grass_material, used when gt.Grass.Clumps is 0 and by the card mesh the component is placed with). grass_material becomes
 # M_LidarClump (what the clump mode streams on the pasture clumps), rank_material M_LidarRank (the rank band clumps). The clumps and spacings are set the same way Install sets them.
 card_mat=grass.grass_material;clump_mat,clump_row=clump_material('M_LidarClump',CLUMP_TINT,wind=True);rank_mat,rank_row=clump_material('M_LidarRank',RANK_TINT,kind='rank')
 grass.set_editor_property('card_grass_material',card_mat);grass.set_editor_property('grass_material',clump_mat);grass.set_editor_property('rank_material',rank_mat)
 report['gp2']=dict(materials=dict(M_LidarClump=clump_row,M_LidarRank=rank_row,M_LidarGrass_card=card_mat.get_path_name()),clumps=set_clump_props(grass))
 grass.grass.set_material(0,card_mat);grass.distant_grass.set_material(0,grass.distant_grass_material)
 # LP3e density: GrassSpacingCm (one jittered card per cell, kept with probability min(1, style G * 1.5), so 1.0 inside the paddocks) now clamps to 30 to 100 cm in C++ (LP3d: 45 floor); 35 cm is about 1.65x the cards of 45 cm.
 # BladeScale scales the near cards' XY and Z (distance cards keep their scale); RankBandScale stretches the rank-band cards (style G .3 to .8) in Z.
 grass.set_editor_property('grass_spacing_cm',GRASS_SPACING_CM);grass.set_editor_property('blade_scale',BLADE_SCALE);grass.set_editor_property('rank_band_scale',RANK_BAND_SCALE)
 grass_report.update(spacing_cm_after=float(grass.get_editor_property('grass_spacing_cm')),spacing_clamp_cm=[30,100],blade_scale=float(grass.get_editor_property('blade_scale')),rank_band_scale=float(grass.get_editor_property('rank_band_scale')),cover_probability='min(1, style G * 1.5)',materials=cover_report,straw_multiplier=list(STRAW))
 report['lp3d_grass']=grass_report
 # A map-specific tint applies only to the visual grass cover layer. Soil
 # geometry, normals, wetness and the recovered physical state are untouched.
 from benmore_river_life_materials import Graph
 # LP3e: the high-grass multiplier is (.85,1.0,.70) (LP3d .70,1.0,.55; before that .55,.85,.40) so it no longer dulls or blues the pasture; low style G (forest floor) still does almost nothing. An existing node is rewritten.
 for name in ['Terrain','Detail']:
  mat=u.load_asset(BASE+'/M_'+name);g=Graph(mat,'LidarCoverTint');old=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR);oo=mel.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR)
  existing=next((e for e in mel.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionCustom) and str(e.get_editor_property('desc'))=='LidarCoverTint'),None)
  if existing:existing.set_editor_property('code',COVER_TINT_CODE)
  else:
   p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS);t=g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(BASE+'/T_style'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
   n=g.custom(['Native','P','Style'],COVER_TINT_CODE);g.wire(old,n,'Native',oo);g.wire(p,n,'P');g.wire(t,n,'Style');g.output(n,u.MaterialProperty.MP_BASE_COLOR)
  assert not mel.recompile_material(mat);assets.save_loaded_asset(mat)
 report['lp3d_cover_tint']=dict(high_grass_multiplier=list(COVER_TINT),previous=[.70,1.0,.55],code=COVER_TINT_CODE)
 import lidar_canopy_assets
 meshes=yield from lidar_canopy_assets.build(world);trees=json.loads((OUT/'trees.json').read_text())
 # Re-seat every tree from the kit transforms (ground pivot, root flare sunk 6cm); the kit canopy meshes are only rebuilt when their cache is stale.
 for kind,mesh in enumerate(meshes):
  c=next(c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh==mesh)
  c.clear_instances();c.add_instances(lidar_canopy_assets.tree_transforms(mesh,trees,kind),False,True);yield 1
 # Apply the same native track surface pass directly to the final LiDAR materials.
 if (OUT/'TrackDetail/manifest.json').exists():
  import lidar_track_detail
  report['track_detail']=lidar_track_detail.install();yield 1
 if (OUT/'river-repair.json').exists():
  import lidar_river_detail
  report['river_detail']=lidar_river_detail.install();yield 1
 # Keep the logging pools connected to their live mud after an authoring rebuild.
 if (OUT/'rutwater.json').exists():
  import lidar_rut_water
  report['rut_water']=lidar_rut_water.install();yield 1
 if (OUT/'GrassGS3/manifest.json').exists():
  import lidar_grass_gs3
  report['gs3']=lidar_grass_gs3.install()
 if (OUT/'levelpolish.json').exists():
  import lidar_level_polish
  report['level_polish']=yield from lidar_level_polish.install()
 if (ROOT/'Art/Export/LidarStudy/Homestead/layout.json').exists():
  # Reseeding trees above must not restore trunks through the house or garage.
  import lidar_homestead
  report['homestead']=lidar_homestead.place()
 if (OUT/'reference-style.json').exists():
  import lidar_reference_style
  report['reference_style']=lidar_reference_style.apply()
 import canopy_depth
 if canopy_depth.enabled():report['canopy_depth']=canopy_depth.apply()
 assert les.save_current_level();assert protected()==before
 if 'rut_water' in report:
  # Only publish the basin digest after the level containing those basins saves.
  report['rut_water']['ok']=True
  (OUT/'rutwater.json').write_text(json.dumps(report['rut_water'],indent=2))
 report.update(ok=True,ambient_wave_material=wave.get_path_name(),shore_coordinates_rebound=True,tree_roots_seated=True,protected_unchanged=len(before));(OUT/'polish.json').write_text(json.dumps(report,indent=2))
 world=refs=sheet=grass=forest=a=d=m=domain=wave=source=b=c=mesh=meshes=surfaces=patches=watermats=mat=g=old=n=p=t=e=None
 # Generated water domains are outered to the level too, even when the sheet
 # reference is gone. Release them before unloading its world.
 generated=base_domain=card_mat=clump_mat=rank_mat=existing=None
 gc.collect();yield 2;les.load_level('/Engine/Maps/Entry');yield 8

steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global deadline,busy,steps
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1000
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();(OUT/'polish.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
