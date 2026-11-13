"""Road-only native colour program and source clod materials. Original lab unchanged."""
from pathlib import Path
import unreal as u
from benmore_river_life_materials import Graph,props
import mud_proving_materials as shared
from mudrunner_lab_materials import STATE
ROOT=Path(u.Paths.project_dir());DATA=ROOT/'Art/Export/MudRoad/NativeStage4'
BASE='/Game/GrandTour/ArtTests/MudRoad/NativeStage4';LAB='/Game/GrandTour/ArtTests/MudLab/NativeReference'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary

def fresh(name):
 m=assets.load_asset(BASE+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,BASE,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m);return m

def texture(name):
 task=props(u.AssetImportTask(),filename=str(DATA/(name+'.png')),destination_path=BASE,destination_name='T_'+name,automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=assets.load_asset(BASE+'/T_'+name);assert t
 props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,never_stream=True)
 assets.save_loaded_asset(t);return t

def colour(s,scale):return [(x/255)**2.2*scale for x in s]

def soil(paint,rest,track=False):
 m=fresh('M_NativeTread' if track else 'M_RoadNativeSoil');props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT,tangent_space_normal=False,two_sided=True)
 if track:props(m,blend_mode=u.BlendMode.BLEND_TRANSLUCENT,translucency_pass=u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
 else:mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE)
 g=Graph(m,'MudRunnerStage4');d=shared.inputs(g,paint,rest)
 d['P'].set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
 d['Camera']=g.node(u.MaterialExpressionCameraPositionWS)
 d['VisualGrid']=g.node(u.MaterialExpressionScalarParameter,parameter_name='MR_VisualGrid',default_value=0)
 for key,name in [('Mud','tiles_mud__d_a'),('Flat','tiles_mud_flat__d_a'),('Dirt','tiles_dirt__d_a'),('Grass','tiles_grass__d_a'),('Noise','env_mud_noise__uncmp')]:
  d[key]=g.node(u.MaterialExpressionTextureObject,texture=assets.load_asset(LAB+'/T_'+name),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 d['Decals']=g.node(u.MaterialExpressionTextureObject,texture=texture('env_decals_diffuse__d_a'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 if track:
  d['TrackUV']=g.node(u.MaterialExpressionTextureCoordinate)
  d['TrackData']=g.node(u.MaterialExpressionVertexColor)
  d['TrackTangent']=g.node(u.MaterialExpressionVertexTangentWS)
  for key,name in [('TrackAlpha','tracks_offroad_alpha__s_d'),('TrackHeight','tracks_offroad_height__s_d'),('TrackSlip','env_track_slip_height__s_d')]:
   d[key]=g.node(u.MaterialExpressionTextureObject,texture=texture(name),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 for name,value in [('InterestCenter',(10000,10000,0,0)),('InterestForward',(1,0,4.7,0)),('InterestRight',(0,1,1.9,0)),('InterestHeight',(1,1,1,1))]:
  d[name]=g.node(u.MaterialExpressionVectorParameter,parameter_name='MR_'+name,default_value=u.LinearColor(*value))
 for name,v in [('AmbientPos',colour([200,210,216],1.8)),('AmbientMid',colour([200,210,216],1.5)),('AmbientNeg',colour([214,214,214],1.2)),('FogColor',colour([184,218,243],.32))]:d[name]=g.vector(v)
 # Geometry remains source VS arithmetic, with the original 32..40m height blend.
 def out(code,prop,kind=u.CustomMaterialOutputType.CMOT_FLOAT3):
  e=g.custom(list(d),shared.COMMON+STATE+code,kind)
  for k,v in d.items():g.wire(v,e,k)
  g.output(e,prop);return e
 offset='''
float3 noise=Texture2DSampleLevel(Noise,NoiseSampler,P.xy*.0024,0).rgb-.5;
// Shared host mesh includes the dry ground; native disappearing-tile edge is not applied here.
return (float3(0,0,height*nearWeight-.1)+noise.rbg*22*presence)*VisualGrid;
'''
 if track:
  # Ribbons are clipped to the visual grid triangles on the CPU. Interpolate
  # those same displaced grid vertices, not a fresh height sample between them.
  offset='''
float2 cell=floor(P.xy/12.5),f=P.xy/12.5-cell;
float4 weights=f.x+f.y<=1 ? float4(1-f.x-f.y,f.x,f.y,0) : float4(0,1-f.y,1-f.x,f.x+f.y-1);
float3 result=0;
[unroll] for(int k=0;k<4;k++) {
 float2 xy=(cell+float2(k%2,k/2))*12.5;
 float2 q=(xy-PaintWindow.xy)/PaintWindow.z;
 float4 pp=Texture2DSampleLevel(Paint,PaintSampler,saturate(q),0)*(all(q>=0)&&all(q<=1));
 float2 fu=(xy-Window.xy)/max(Window.z,1);
 float4 ff=Texture2DSampleLevel(Field,FieldSampler,saturate(fu),0)*Ready*(all(fu>=0)&&all(fu<=1));
 float pr=smoothstep(0,3,saturate(pp.r*DepthScale)*50)*max(pp.a,ff.a);
 float h=ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,xy,PaintWindow,Window,Ready);
 float fade=1-saturate((length(Camera.xy-xy)*.01-32)*.125);
 float3 n=Texture2DSampleLevel(Noise,NoiseSampler,xy*.0024,0).rgb-.5;
 result+=weights[k]*(float3(0,0,h*fade-.1)+n.rbg*22*pr);
}
return result*VisualGrid;
'''
 out(offset,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 header='''
// Host inputs: overcast daytime, neutral unused lightmap/shadow resources.
// Complete native PS arithmetic follows. Dynamic projector resources are a separate remaining seam.
float4 c0=0,c1=0,c2=float4(InterestForward.z*.5,0,0,0),c3=float4(1/max(InterestForward.z,.01),0,0,0);
float4 c4=0,c5=float4(InterestRight.z*.5,0,0,0),c6=float4(1/max(InterestRight.z,.01),0,0,0);
float4 c7=float4(1,0,0,0),c8=float4(0,1,0,0),c9=float4(0,0,1,0),c10=float4(0,0,0,1),c11=c7,c12=c8,c13=c9,c14=c10;
float4 c15=float4(AmbientPos,0),c16=float4(AmbientMid,0),c17=float4(AmbientNeg,0);
float4 c18=float4(InterestForward.xyz,0),c19=float4(InterestRight.xyz,0),c20=0,c21=float4(0,0,1./1024,1./1024),c22=0,c23=0;
float4 c24=float4(InterestCenter.xy,0,0),c25=InterestHeight.xxxx,c26=float4(0,2,0,0),c27=0,c28=float4(3,.03,0,0);
float3 noise=Texture2DSampleLevel(Noise,NoiseSampler,P.xy*.0024,0).rgb-.5;
float3 wp=P.xzy*.01+float3(0,height*.01,0)+noise*.22*presence;
// The native distance fog is applied once to the composed road scene in M_NativeDayGrade.
float fog=0;
float4 v0=float4(wp,1),v1=float4(mrNormal.xzy,0),v2=float4(puv,materialXY*.01);
float4 v3=float4(grassTint,mud),v4=float4(dirtTint,1),v5=float4(presence,shade,flat,decalWeight),v6=float4(FogColor,fog);
#define SAMPLE0(p) float4(1,1,1,1)
#define SAMPLE1(p) float4(0,0,0,0)
#define SAMPLE2(p) float4(1,1,1,1)
#define SAMPLE3(p) Texture2DSample(Decals,DecalsSampler,p)
#define SAMPLE4(p) Texture2DSample(Dirt,DirtSampler,p)
#define SAMPLE5(p) Texture2DSample(Grass,GrassSampler,p)
#define SAMPLE6(p) Texture2DSample(Mud,MudSampler,p)
#define SAMPLE7(p) Texture2DSample(Flat,FlatSampler,p)
'''
 body=(DATA/'mud-color-native.hlsl').read_text()
 end='\n'+'\n'.join('#undef SAMPLE'+str(i) for i in range(8))+'\nreturn pow(max(oC0.rgb,0),2.2);'
 if track:
  # Recovered WheelTrack_002 height mix and _000 pigment/alpha terms. The
  # projector and its screen-space POM are replaced by terrain-following ribbons.
  track_inputs='''
float2 tuv=float2(TrackUV.x*.5,TrackUV.y);
float ta=Texture2DSample(TrackAlpha,TrackAlphaSampler,tuv).r;
float th=Texture2DSample(TrackHeight,TrackHeightSampler,tuv).r;
float sh=Texture2DSample(TrackSlip,TrackSlipSampler,float2(tuv.x,TrackUV.y*.5)).r;
float strength=ta*TrackData.r*1.2;
float relief=1-lerp(1,lerp(th,sh,TrackData.g),strength);
float3 pigment=Texture2DSample(Decals,DecalsSampler,P.xy*.0048).rgb;
'''
  header=track_inputs+header
  end=end.replace('return pow(max(oC0.rgb,0),2.2);','''
// Native dry-ground factor and relief darkening; surface light/fog come from Mud Color.
float3 trackColour=oC0.rgb*.86*lerp(float3(1,1,1),pigment,(.15*wet+.5)*relief);
return pow(max(trackColour,0),2.2);''')
  out('''float ta=Texture2DSample(TrackAlpha,TrackAlphaSampler,float2(TrackUV.x*.5,TrackUV.y)).r;
return saturate(ta*ta*TrackData.r*1.2)*saturate((mrNormal.z-.4)*2.5);''',u.MaterialProperty.MP_OPACITY,u.CustomMaterialOutputType.CMOT_FLOAT1)
 out(header+body+end,u.MaterialProperty.MP_EMISSIVE_COLOR)
 assert not mel.recompile_material(m);assets.save_loaded_asset(m)
 return m

def make(paint,rest):
 m=soil(paint,rest);track=soil(paint,rest,True)
 lut=texture('native_day_lut');props(lut,filter=u.TextureFilter.TF_BILINEAR,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP);assets.save_loaded_asset(lut)
 grade=fresh('M_NativeDayGrade');props(grade,material_domain=u.MaterialDomain.MD_POST_PROCESS,blendable_location=u.BlendableLocation.BL_REPLACING_TONEMAPPER)
 gg=Graph(grade);scene=gg.node(u.MaterialExpressionSceneTexture,scene_texture_id=u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
 lt=gg.node(u.MaterialExpressionTextureObject,texture=lut,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 c=gg.custom(['Scene','LUT','P','Camera','FogColor'],'''float3 Encoded=pow(max(Scene.rgb*View.OneOverPreExposure,0),1./2.2);
// Mud_001 exponential fog, shared after water/vehicle composition. day__1 has no
// ScatterAngle; the loader at 0x14070fca3 defaults it to zero.
float distanceCm=length(Camera-P);
// The host sky is outside the 63-m fixture and has its own sky shading, as in
// the source's separate sky pass. Do not fog reconstructed far-plane pixels.
float fog=distanceCm<100000 ? saturate(exp((distanceCm*.01+8)*.0029)-1) : 0;
Encoded=lerp(Encoded,FogColor,fog);
'''+(DATA/'native-grade.hlsl').read_text())
 gg.wire(scene,c,'Scene','Color');gg.wire(lt,c,'LUT');gg.wire(gg.node(u.MaterialExpressionWorldPosition),c,'P');gg.wire(gg.node(u.MaterialExpressionCameraPositionWS),c,'Camera');gg.wire(gg.vector(colour([184,218,243],.32)),c,'FogColor');gg.output(c,u.MaterialProperty.MP_EMISSIVE_COLOR)
 assert not mel.recompile_material(grade);assets.save_loaded_asset(grade)
 grade_oracle=fresh('M_NativeGradeOracle');props(grade_oracle,shading_model=u.MaterialShadingModel.MSM_UNLIT)
 gg=Graph(grade_oracle);c=gg.custom(['UV','LUT'],(DATA/'native-grade-oracle.hlsl').read_text());gg.wire(gg.node(u.MaterialExpressionTextureCoordinate),c,'UV');gg.wire(gg.node(u.MaterialExpressionTextureObject,texture=lut,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),c,'LUT');gg.output(c,u.MaterialProperty.MP_EMISSIVE_COLOR)
 assert not mel.recompile_material(grade_oracle);assets.save_loaded_asset(grade_oracle)
 oracle=fresh('M_NativeColorOracle');props(oracle,shading_model=u.MaterialShadingModel.MSM_UNLIT)
 go=Graph(oracle);e=go.custom(['UV'],(DATA/'mud-color-oracle.hlsl').read_text());go.wire(go.node(u.MaterialExpressionTextureCoordinate),e,'UV');go.output(e,u.MaterialProperty.MP_EMISSIVE_COLOR)
 assert not mel.recompile_material(oracle);assets.save_loaded_asset(oracle)
 clod=fresh('M_NativeClod');gc=Graph(clod);t=texture('plants_chunks__d_a')
 uv=gc.node(u.MaterialExpressionTextureCoordinate);tex=gc.tex(t,uv)
 col=gc.custom(['C'],'return pow(max(C.rgb,0),2.2);');gc.wire(tex,col,'C','RGB');gc.output(col,u.MaterialProperty.MP_BASE_COLOR)
 gc.output(gc.scalar(.9),u.MaterialProperty.MP_ROUGHNESS);gc.output(gc.scalar(0),u.MaterialProperty.MP_SPECULAR)
 mel.set_material_usage(clod,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);assert not mel.recompile_material(clod);assets.save_loaded_asset(clod)
 return m,clod,track,grade
