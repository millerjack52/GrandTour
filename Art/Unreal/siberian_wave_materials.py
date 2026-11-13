"""Recovered native wave sampling, isolated to the showcase materials."""
import unreal as u
from pathlib import Path
from benmore_river_life_materials import Graph,props
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/SiberianShowcase/WaveResearch'
BASE='/Game/GrandTour/ArtTests/SiberianShowcase/Waves'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
SAMPLING=(Path(__file__).parent/'mudrunner_wave_sampling.hlsl').read_text()

def lookup(name):
 path=BASE+'/T_'+name
 if not assets.does_asset_exist(path):
  task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=BASE,destination_name='T_'+name,automated=True,save=True)
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
 t=assets.load_asset(path);assert t
 props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_NEAREST,never_stream=True)
 assets.save_loaded_asset(t);return t

def precombine():
 path=BASE+'/M_NativeWavePrecombine'
 m=assets.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_NativeWavePrecombine',BASE,u.Material,u.MaterialFactoryNew())
 for e in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,e)
 props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT)
 g=Graph(m,'RecoveredWaves')
 tex=assets.load_asset('/Game/GrandTour/ArtTests/MudLab/NativeReference/T_env_water_waves__d_a_uncmp');assert tex
 inputs={'WaveSource':g.node(u.MaterialExpressionTextureObject,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),'UV':g.node(u.MaterialExpressionTextureCoordinate),'Time':g.node(u.MaterialExpressionScalarParameter,parameter_name='WaveClock',default_value=0)}
 body=(ROOT/'Art/Export/MudLab/NativeReference/waves.hlsl').read_text()
 # RGB canvas retains normal XY and source height in B; avoid losing source alpha.
 body=body.replace('return oC0;','return float3(oC0.xy,oC0.w);')
 e=g.custom(list(inputs),body)
 for k,v in inputs.items():g.wire(v,e,k)
 g.output(e,u.MaterialProperty.MP_EMISSIVE_COLOR)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m);return m

def patch(m):
 g=Graph(m,'RecoveredWaveSampling')
 nodes={}
 for e in mel.get_material_expressions(m):
  if isinstance(e,u.MaterialExpressionCustom) and 'MRWaveSampling recovered;' in e.get_editor_property('code'):return
 for key,name in [('WaveDirections','direction'),('WaveSpeeds','speed')]:
  nodes[key]=g.node(u.MaterialExpressionTextureObject,texture=lookup(name),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 nodes['AmbientTex']=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='AmbientTex',texture=assets.load_asset('/Engine/EngineResources/Black'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 for key in ['AmbientClock','AmbientReady']:nodes[key]=g.node(u.MaterialExpressionScalarParameter,parameter_name=key,default_value=0)
 found=0
 for e in mel.get_material_expressions(m):
  if not isinstance(e,u.MaterialExpressionCustom):continue
  c=e.get_editor_property('code')
  if 'struct NativeWaves' not in c:continue
  river='AxisX.xy*wave.b' in c
  flow='(AxisX.xy*wave.b+AxisY.xy*wave.a)*.01' if river else 'wave.ba*.01'
  gradient='AxisX.xy*dx/(2*cell.x)+AxisY.xy*dy/(2*cell.y)' if river else 'float2(dx,dy)/(2*cell)'
  c=c[:c.index('struct NativeWaves')]+SAMPLING+'''
MRWaveSampling recovered;
float2 movingFlow=FLOW;
float distanceM=length(Camera-P)*.01;
// Source pixel LOD: log2(distance/(64*dot(baseNormal,view))).
float viewUp=max(abs(Camera.z-P.z)/max(length(Camera-P),1),.01);
float lod=max(0,log2(max(distanceM/(64*viewUp),.0001)));
float4 optical=recovered.optical(AmbientTex,AmbientTexSampler,WaveDirections,WaveDirectionsSampler,WaveSpeeds,WaveSpeedsSampler,P.xy*.01,movingFlow,AmbientClock,lod);
float3 flowNormal=recovered.normal(optical.xy,movingFlow,distanceM);
// Water_000 also samples world XZ*.5 and adds .2*(RG-.50196) to its
// reflection/refraction vector. SLW exposes one normal: this is the explicit
// UE optical bridge for fine still-water detail, not extra physical waves.
float2 fine=(Texture2DSample(AmbientTex,AmbientTexSampler,P.xy*.005).rg-.50195998)*.2;
float2 cell=max(FieldSize.xy/FieldTexels.xy,1),du=1/FieldTexels.xy;
float dx=Texture2DSampleLevel(Wave,WaveSampler,saturate(wu+float2(du.x,0)),0).r-Texture2DSampleLevel(Wave,WaveSampler,saturate(wu-float2(du.x,0)),0).r;
float dy=Texture2DSampleLevel(Wave,WaveSampler,saturate(wu+float2(0,du.y)),0).r-Texture2DSampleLevel(Wave,WaveSampler,saturate(wu-float2(0,du.y)),0).r;
float2 physical=GRADIENT;
if(AmbientReady<.5)return normalize(float3(-physical,1));
return normalize(float3((flowNormal.xy+fine)*AmbientReady-physical*flowNormal.z,flowNormal.z));
'''.replace('FLOW',flow).replace('GRADIENT',gradient)
  e.set_editor_property('code',c)
  ins=list(e.get_editor_property('inputs'));names=[str(i.get_editor_property('input_name')) for i in ins]
  for k in nodes:
   if k not in names:ins.append(props(u.CustomInput(),input_name=k))
  e.set_editor_property('inputs',ins)
  for k,v in nodes.items():g.wire(v,e,k)
  found+=1
 assert found==1,(m.get_path_name(),found)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)
