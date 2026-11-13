"""Benmore-specific bindings of the recovered programs; shared source assets stay intact."""
import re
from pathlib import Path
import unreal as u
from benmore_river_life_materials import Graph,props
from siberian_wave_materials import SAMPLING,lookup
import siberian_surface_repairs as repairs
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreNative'
BASE='/Game/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
def copy(source,name):
 path=BASE+'/'+name
 if assets.does_asset_exist(path):assets.delete_asset(path)
 m=assets.duplicate_asset(source,path);assert m;return m
def texture(site,name):
 task=props(u.AssetImportTask(),filename=str(OUT/(site+'_'+name+'.png')),destination_path=BASE,destination_name='T_'+site+'_'+name,automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=assets.load_asset(BASE+'/T_'+site+'_'+name);assert t
 props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
 assert assets.save_loaded_asset(t);return t
def save(m):
 assert not mel.recompile_material(m),m.get_path_name()
 assert assets.save_loaded_asset(m)
 return m
def water(kind):
 m=copy('/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterSurface/M_GC_Domain'+kind,'M_NativeDomain'+kind)
 g=Graph(m,'BenmoreNativeWaves')
 pixel=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
 wpo=mel.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 for n in [wpo,pixel]:
  c=str(n.get_editor_property('code'))
  c,count=re.subn(r'struct CurrentWaves \{.*?\};CurrentWaves waves;',SAMPLING if n==pixel else '',c,flags=re.S);assert count==1
  if n==wpo:
   c,count=re.subn(r'\[branch\]if\(Ready>\.5 && geometryFade>\.001\)\{.*?\n\}', '// Recovered optics are normal-only here; retain the accepted physical/wake height once.',c,count=1,flags=re.S);assert count==1
  else:
   c,count=re.subn(r'\[branch\]if\(Ready>\.5 && nearFade>\.001\)\{.*?\n\}', '''
MRWaveSampling recovered;
[branch]if(Ready>.5){
 float viewUp=max(abs(Camera.z-P.z)/max(length(Camera-P),1),.01);
 float nativeLod=max(0,log2(max(dist/(64*viewUp),.0001)));
 float4 optical=recovered.optical(Ambient,AmbientSampler,WaveDirections,WaveDirectionsSampler,WaveSpeeds,WaveSpeedsSampler,q,velocity,Clock,nativeLod);
 float3 flowNormal=recovered.normal(optical.xy,velocity,dist);
 float2 fine=(Texture2DSample(Ambient,AmbientSampler,P.xy*.005).rg-.50195998)*.2;
 // UE bridge: combine native optical tilt with the domain's physical slope below.
 detail=(flowNormal.xy+fine)/max(flowNormal.z,.05)*shore;
 bubble=0; // Native precombine alpha is not the old synthetic foam/transmittance.
 rippleShade=0;
}
''',c,count=1,flags=re.S);assert count==1
   for key,name in [('WaveDirections','direction'),('WaveSpeeds','speed')]:
    n.set_editor_property('inputs',list(n.get_editor_property('inputs'))+[props(u.CustomInput(),input_name=key)])
    g.wire(g.node(u.MaterialExpressionTextureObject,texture=lookup(name),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),n,key)
  assert 'waves.evaluate' not in c
  n.set_editor_property('code',c)
 return save(m)
def coverage(g,site,texture,dither=True):
 p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
 t=g.node(u.MaterialExpressionTextureObject,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 ox,oy=site['origin'];size=site['size']
 c=g.custom(['P','Cover'],f'float2 uv=(P.xy-float2({ox},{oy}))/{size};return all(uv>0)&&all(uv<1)?Texture2DSampleLevel(Cover,CoverSampler,saturate(uv),0).r:0;',u.CustomMaterialOutputType.CMOT_FLOAT1)
 g.wire(p,c,'P');g.wire(t,c,'Cover')
 if not dither:return c
 d=g.node(u.MaterialExpressionMaterialFunctionCall)
 assert d.set_material_function(assets.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
 pin=next(n for n in mel.get_material_expression_input_names(d) if 'alpha' in n.lower())
 g.wire(c,d,pin)
 return d
def soil(site,textures,track=False):
 name='M_Tread' if track else 'M_Soil'
 m=copy('/Game/GrandTour/ArtTests/SiberianShowcase/NW/'+name,site['name']+'_'+name)
 for e in mel.get_material_expressions(m):
  if isinstance(e,u.MaterialExpressionTextureObjectParameter):
   key=str(e.get_editor_property('parameter_name'))
   if key in ['GTLS_Paint','GTLS_Rest']:e.set_editor_property('texture',textures[key.split('_')[1].lower()])
  elif isinstance(e,u.MaterialExpressionTextureObject):
   t=e.get_editor_property('texture')
   if t and t.get_name() in ['T_style','T_macro']:e.set_editor_property('texture',textures[t.get_name()[2:]])
  if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_PaintWindow':e.set_editor_property('default_value',u.LinearColor(*site['origin'],site['size'],0))
  if isinstance(e,u.MaterialExpressionCustom):
   c=str(e.get_editor_property('code')).replace('800./65535.','8192./65535.')
   # Regional coverage must stay at its authored XY, including its feather.
   c=c.replace('noise.rbg*22*presence','float3(0,0,noise.g*22*presence)').replace('n.rbg*22*pr','float3(0,0,n.g*22*pr)')
   e.set_editor_property('code',c)
 g=Graph(m,'BenmoreRegionalCoverage');cover=coverage(g,site,textures['cover'])
 # The showcase replaces the tonemapper; Benmore uses physical daylight exposure.
 # Keep recovered display-referred ambient colour visible under that exposure.
 native=mel.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
 nativeout=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
 exposed=g.custom(['Native'],'return Native*View.OneOverPreExposure;')
 g.wire(native,exposed,'Native',nativeout);g.output(exposed,u.MaterialProperty.MP_EMISSIVE_COLOR)
 if track:
  old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY)
  oldout=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY)
  node=g.node(u.MaterialExpressionMultiply);g.wire(old,node,'A',oldout);g.wire(cover,node,'B');g.output(node,u.MaterialProperty.MP_OPACITY)
 else:
  props(m,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.5)
  g.output(cover,u.MaterialProperty.MP_OPACITY_MASK)
 return save(m)
def terrain(sites,textures):
 m=copy('/Game/GrandTour/Demo/BenmoreRoads/Gaea/ShoreRefinement/M_GC_Terrain','M_BenmoreNativeTerrain')
 g=Graph(m,'BenmoreRegionalCoverage');nodes=[coverage(g,s,textures[s['name']]['cover']) for s in sites]
 active=g.node(u.MaterialExpressionScalarParameter,parameter_name='MR_BenmoreActive',default_value=0)
 mask=g.custom(['A','B','C','Active'],'return 1-max(A,max(B,C))*Active;',u.CustomMaterialOutputType.CMOT_FLOAT1)
 for key,node in zip(['A','B','C','Active'],nodes+[active]):g.wire(node,mask,key)
 # The original opacity mask punches rectangular holes for the retired crossing
 # overlays. Only the regional coverage now owns the landscape cutout.
 props(m,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.5)
 g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
 # The new ford grass owns the regional cover. Suppress landscape-generated
 # tufts there and inside mud instead of leaving roots floating over new ruts.
 cov=[coverage(g,s,textures[s['name']]['cover'],False) for s in sites]
 density=g.custom(['A','B','C'],'return 1-max(A,max(B,C));',u.CustomMaterialOutputType.CMOT_FLOAT1)
 for key,node in zip(['A','B','C'],cov):g.wire(node,density,key)
 for output in list(mel.get_material_expressions(m)):
  if not isinstance(output,u.MaterialExpressionLandscapeGrassOutput):continue
  pins=mel.get_material_expression_input_names(output);sources=mel.get_inputs_for_material_expression(m,output)
  assert len(pins)==len(sources)
  for pin,source in zip(pins,sources):
   if not source:continue
   out=mel.get_input_node_output_name_for_material_expression(output,source)
   mix=g.node(u.MaterialExpressionMultiply);g.wire(source,mix,'A',out);g.wire(density,mix,'B');g.wire(mix,output,pin)
 return save(m)
