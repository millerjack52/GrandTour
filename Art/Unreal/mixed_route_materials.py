"""Recovered source blending/grass arithmetic with explicit richer art direction."""
import unreal as u
from pathlib import Path
from benmore_river_life_materials import Graph,props
import mudrunner_stage4_materials as native
import mudrunner_terrain_overlay
BASE='/Game/GrandTour/ArtTests/MudRoad/MixedSurfaces'
DATA=Path(u.Paths.project_dir())/'Art/Export/MudRoad/MixedSurfaces'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
def fresh(name):
 m=assets.load_asset(BASE+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,BASE,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m);return m
def texture(name):
 task=props(u.AssetImportTask(),filename=str(DATA/(name+'.png')),destination_path=BASE,destination_name='T_'+name,automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=assets.load_asset(BASE+'/T_'+name);assert t
 props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True)
 assets.save_loaded_asset(t);return t
def soil(paint,rest,style,macro):
 old_inputs=native.shared.inputs;old_state=native.STATE;old_base=native.BASE
 def inputs(g,p,r):
  d=old_inputs(g,p,r)
  native_assets='/Game/GrandTour/ArtTests/MudRoad/NativeInteractions'
  dark_sand=assets.load_asset(native_assets+'/T_overlays_wet_sand_dark__d_a') or assets.load_asset(BASE+'/T_overlays_wet_sand__d_a')
  spec=assets.load_asset(native_assets+'/T_overlays_wet_sand__s_d') or assets.load_asset(BASE+'/T_overlays_wet_sand__s_d')
  for key,t in [('Style',style),('Macro',macro),('Sand',assets.load_asset(BASE+'/T_tiles_beach_dark__d_a')),('WetSand',dark_sand),('SandSpec',spec)]:
   d[key]=g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
  return d
 native.shared.inputs=inputs;native.BASE=BASE
 # Authoring mask supplies the material distinction. Original Mud Color PS stays
 # intact; only its base-map inputs and final art-directed colour are adapted.
 pre='''float2 styleUV=saturate((P.xy-PaintWindow.xy)/PaintWindow.z);
float4 style=Texture2DSampleLevel(Style,StyleSampler,styleUV,0);
float sandCover=style.r,grassCover=style.g;
mud*=saturate(1-sandCover-grassCover);
'''
 native.STATE=pre+old_state.replace('float vegetation=0;','float vegetation=grassCover;')
 try:m=native.soil(paint,rest);track=native.soil(paint,rest,True)
 finally:native.shared.inputs=old_inputs;native.STATE=old_state;native.BASE=old_base
 for mat in [m,track]:
  for e in mel.get_material_expressions(mat):
   if not isinstance(e,u.MaterialExpressionCustom):continue
   code=e.get_editor_property('code')
   # Source normal sees the relief; the host also needs the real landscape grade.
   marker='float3 mrNormal=nativeNormal.eval(hx,hy);'
   code=code.replace(marker,marker+'''
float2 me=float2(50/PaintWindow.z,0);
float2 mx0=Texture2DSampleLevel(Macro,MacroSampler,styleUV-me,0).rg;
float2 mx1=Texture2DSampleLevel(Macro,MacroSampler,styleUV+me,0).rg;
float2 my0=Texture2DSampleLevel(Macro,MacroSampler,styleUV-me.yx,0).rg;
float2 my1=Texture2DSampleLevel(Macro,MacroSampler,styleUV+me.yx,0).rg;
float2 macroSlope=float2(dot(mx1-mx0,float2(65280,255)),dot(my1-my0,float2(65280,255)))*(800./65535.)/100.;
mrNormal=normalize(float3(mrNormal.xy-macroSlope,mrNormal.z));
''')
   # Rich colours are a requested departure from source colour grading, not a
   # claim that the native material constants were different.
   if 'float4 c0=0' in code:
    # Sand suppresses mud geometry, but its worn pigment must be evaluated as
    # mud. Feeding zero mud coverage to the colour pass exposed green base grass.
    code=code.replace('v3=float4(grassTint,mud)', 'v3=float4(grassTint,max(mud,sandCover))')
    code=code.replace('v5=float4(presence,shade,flat,decalWeight)', 'v5=float4(max(presence,sandCover),shade,flat,decalWeight)')
    code=code.replace('float3 trackColour=oC0.rgb*.86*', 'float3 trackBase=lerp(oC0.rgb,lerp(Texture2DSample(Sand,SandSampler,materialXY*.0018).rgb,Texture2DSample(WetSand,WetSandSampler,materialXY/600.).rgb,.8),sandCover);\nfloat3 trackColour=trackBase*.86*')
    ret='return pow(max(oC0.rgb,0),2.2);'
    if ret in code:code=code.replace(ret,mudrunner_terrain_overlay.code()+'''
float3 turf=Texture2DSample(Grass,GrassSampler,materialXY*.0012).rgb*float3(.48,.68,.24);
float exposed=saturate(field.a*.75+max(0,-height)*.10);
turf=lerp(turf,oC0.rgb*float3(.8,.65,.43),exposed);
float light=.78+.22*saturate(mrNormal.z);
float3 rich=oC0.rgb*float3(.96,.84,.68);
rich=lerp(rich,sandy,sandCover);
rich=lerp(rich,turf*light,grassCover);
return pow(max(rich,0),2.2);
''')
   # Do not fade physical height off with camera distance on the host extension.
   code=code.replace('height*nearWeight-.1','height-.1').replace('h*fade-.1','h-.1')
   # The tyre ribbon must use the same zero mud-noise weight as the sand/sod
   # surface; retaining mud's 22cm offset produces floating tread fragments.
   code=code.replace('float pr=smoothstep(0,3,saturate(pp.r*DepthScale)*50)*max(pp.a,ff.a);','float pr=smoothstep(0,3,saturate(pp.r*DepthScale)*50)*max(pp.a,ff.a)*saturate(1-sandCover-grassCover);')
   e.set_editor_property('code',code)
  assert not mel.recompile_material(mat);assets.save_loaded_asset(mat)
 return m,track
def grass():
 m=fresh('M_NativeGrassRich');props(m,blend_mode=u.BlendMode.BLEND_MASKED,two_sided=True,opacity_mask_clip_value=.35)
 g=Graph(m);uv=g.node(u.MaterialExpressionTextureCoordinate)
 tex=g.node(u.MaterialExpressionTextureSample,texture=assets.load_asset(BASE+'/T_grass_grass_short__d_a'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);g.wire(uv,tex,'UVs')
 col=g.custom(['C'],'return pow(max(C.rgb*float3(.64,.95,.38),0),2.2);');g.wire(tex,col,'C');g.output(col,u.MaterialProperty.MP_BASE_COLOR)
 g.output(tex,u.MaterialProperty.MP_OPACITY_MASK,'A')
 g.output(g.scalar(.85),u.MaterialProperty.MP_ROUGHNESS)
 p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
 root=g.node(u.MaterialExpressionPerInstanceCustomData,data_index=0)
 bend=g.node(u.MaterialExpressionPerInstanceCustomData,data_index=1)
 removed=g.node(u.MaterialExpressionPerInstanceCustomData,data_index=2)
 wpo=g.custom(['P','Root','Bend','Removed'],'''
// Plants_009 GRASS deflector: root envelope, height gate, 2x XY and -.8Y.
// Host contact supplies persistent strength and a fixed bend direction.
float h=max(0,(P.z-Root)*.01);
float amount=saturate((h-.1)*2.5)*saturate(h)*Bend;
return Removed>.5 ? float3(0,0,-100000) : float3(.7,.3,-.8)*amount*100;
''');
 for k,v in [('P',p),('Root',root),('Bend',bend),('Removed',removed)]:g.wire(v,wpo,k)
 g.output(wpo,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);assert not mel.recompile_material(m);assets.save_loaded_asset(m);return m
def grade():
 original='/Game/GrandTour/ArtTests/MudRoad/NativeStage4/M_NativeDayGrade'
 m=assets.load_asset(BASE+'/M_RichDayGrade') or assets.duplicate_asset(original,BASE+'/M_RichDayGrade')
 for e in mel.get_material_expressions(m):
  if isinstance(e,u.MaterialExpressionCustom):
   code=e.get_editor_property('code').replace('*.0029','*.0008')
   old='return pow(max(lerp(a,b,frac(coord.b))*1.05,0),1.05);'
   code=code.replace(old,'''float3 sourceGrade=pow(max(lerp(a,b,frac(coord.b))*1.05,0),1.05);
float3 natural=pow(max(Encoded,0),1.07);
return lerp(natural,sourceGrade,.18);''')
   e.set_editor_property('code',code)
 assert not mel.recompile_material(m);assets.save_loaded_asset(m);return m

def river(source):
 # Reuse the recovered Water optics and 94-instruction Waves program. The
 # established open-channel solver supplies depth/current in its rotated grid.
 path=BASE+'/M_NativeRiver'
 m=assets.load_asset(path) or assets.duplicate_asset(source.get_path_name().split('.')[0],path)
 props(m,tangent_space_normal=False)
 g=Graph(m)
 extras={'AxisX':g.node(u.MaterialExpressionVectorParameter,parameter_name='FieldAxisX',default_value=u.LinearColor(0,-1,0,0)),
         'AxisY':g.node(u.MaterialExpressionVectorParameter,parameter_name='FieldAxisY',default_value=u.LinearColor(1,0,0,0)),
         'OpticalTime':g.node(u.MaterialExpressionTime)}
 for e in mel.get_material_expressions(m):
  if not isinstance(e,u.MaterialExpressionCustom):continue
  code=e.get_editor_property('code')
  code=code.replace('float2 wu=(P.xy-FieldMin.xy)/max(FieldSize.xy,1);','float2 rel=P.xy-FieldMin.xy; float2 wu=float2(dot(rel,AxisX.xy),dot(rel,AxisY.xy))/max(FieldSize.xy,1);')
  code=code.replace('float baseBed=Texture2DSampleLevel(BaseBed,BaseBedSampler,saturate(wu),0).r;','float baseBed=Level+wave.r-wave.g;')
  code=code.replace('float waterDepth=min(wave.g,max(0,Level+wave.r-baseBed-height));','float waterDepth=max(0,wave.g);')
  code=code.replace('float4 optical=Texture2DSampleLevel(MRWaves,MRWavesSampler,frac(q),0);','float4 optical=nativeWaves.eval(WaveSource,WaveSourceSampler,frac(q),OpticalTime);')
  code=code.replace('float2 movingFlow=lerp(wave.ba*.01,(nativeState.gb-.50195998)*2,NativeWaterReady);','float2 movingFlow=(AxisX.xy*wave.b+AxisY.xy*wave.a)*.01;')
  code=code.replace('-float2(dx,dy)/(2*cell);','-(AxisX.xy*dx/(2*cell.x)+AxisY.xy*dy/(2*cell.y));')
  e.set_editor_property('code',code)
  ins=list(e.get_editor_property('inputs'));names=[str(v.get_editor_property('input_name')) for v in ins]
  for name in extras:
   if name not in names:ins.append(props(u.CustomInput(),input_name=name))
  e.set_editor_property('inputs',ins)
  for name,node in extras.items():g.wire(node,e,name)
 assert not mel.recompile_material(m);assets.save_loaded_asset(m);return m

