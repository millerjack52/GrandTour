"""Recovered ground programs, with explicit UE lighting/large-terrain adapters."""
import unreal as u
from pathlib import Path
from benmore_river_life_materials import props,Graph
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreWoodland'
BASE='/Game/GrandTour/ArtTests/BenmoreWoodland';assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
def copy(source,name):
 path=BASE+'/'+name
 if assets.does_asset_exist(path):assets.delete_asset(path)
 m=assets.duplicate_asset(source,path);assert m;return m
def texture(name,native=False):
 path=OUT/('NativeReference' if native else '')/(name+'.png')
 task=props(u.AssetImportTask(),filename=str(path),destination_path=BASE,destination_name='T_'+name,automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=assets.load_asset(BASE+'/T_'+name);assert t
 props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,never_stream=True)
 if not native:props(t,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
 assert assets.save_loaded_asset(t);return t
def save(m):
 assert not mel.recompile_material(m),m.get_path_name()
 assert assets.save_loaded_asset(m);return m
def soil(textures,kind):
 track=kind=='Tread';m=copy('/Game/GrandTour/ArtTests/SiberianShowcase/NW/'+('M_Tread' if track else 'M_Soil'),'M_'+kind)
 for e in mel.get_material_expressions(m):
  if isinstance(e,u.MaterialExpressionTextureObjectParameter):
   key=str(e.get_editor_property('parameter_name'))
   if key in ['GTLS_Paint','GTLS_Rest']:e.set_editor_property('texture',textures[key.split('_')[1].lower()])
  elif isinstance(e,u.MaterialExpressionTextureObject):
   t=e.get_editor_property('texture')
   if t and t.get_name() in ['T_style','T_macro']:e.set_editor_property('texture',textures[t.get_name()[2:]])
   if t and t.get_name()=='T_tiles_grass__d_a':e.set_editor_property('texture',textures['tiles_forest__d_a'])
  if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_PaintWindow':e.set_editor_property('default_value',u.LinearColor(-125000,-125000,250000,0))
  if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_DepthScale':e.set_editor_property('default_value',2.48)
  if isinstance(e,u.MaterialExpressionCustom):
   c=str(e.get_editor_property('code')).replace('800./65535.','32768./65535.')
   # Retain Mud_001's full XYZ displacement. Vertical-only noise produces
   # regular spikes; zeroing it removes the native clods entirely.
   c=c.replace('float3(.52,.62,.36)','float3(.95,1.02,.85)').replace('sandy*float3(.72,.60,.44)','sandy')
   # Native colour uses neutral light inputs; UE now supplies actual tree/vehicle
   # shadows and scene lighting, instead of baking overcast brightness into emissive.
   for key in ['AmbientPos','AmbientMid','AmbientNeg']:c=c.replace('float4('+key+',0)','float4(1,1,1,0)')
   e.set_editor_property('code',c)
 g=Graph(m,'BenmoreWoodlandBridge')
 pixel=mel.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
 po=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
 if not track:
  code=str(pixel.get_editor_property('code'));assert '// Host inputs:' in code
  prefix=code.split('// Host inputs:')[0]
  names=[str(i.get_editor_property('input_name')) for i in pixel.get_editor_property('inputs')]
  sources=mel.get_inputs_for_material_expression(m,pixel);assert len(sources)==len(names)
  normal=g.custom(names,prefix+'\nreturn mrNormal;')
  for pin,src in zip(names,sources):
   if src:g.wire(src,normal,pin,mel.get_input_node_output_name_for_material_expression(pixel,src))
  g.output(normal,u.MaterialProperty.MP_NORMAL)
  props(m,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,tangent_space_normal=False)
  g.output(g.scalar(0),u.MaterialProperty.MP_EMISSIVE_COLOR)
 else:
  # The existing translucent ribbon uses its accepted unlit colour path.
  exposed=g.custom(['Native'],'return Native*View.OneOverPreExposure;');g.wire(pixel,exposed,'Native',po);g.output(exposed,u.MaterialProperty.MP_EMISSIVE_COLOR)
 p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
 style=g.node(u.MaterialExpressionTextureObject,texture=textures['style'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 if not track:
  rock=g.node(u.MaterialExpressionTextureObject,texture=textures['tiles_rock_slope__d_a'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
  colour=g.custom(['Native','P','Style','Rock'],'''float4 s=Texture2DSampleLevel(Style,StyleSampler,saturate((P.xy+125000)/250000),0);
float3 r=pow(max(Texture2DSample(Rock,RockSampler,P.xy/550).rgb,0),2.2);
return saturate(lerp(Native,r,s.a));''')
  for k,v in [('Native',pixel),('P',p),('Style',style),('Rock',rock)]:g.wire(v,colour,k,po if k=='Native' else '')
  g.output(colour,u.MaterialProperty.MP_BASE_COLOR)
  rough=g.custom(['P','Style'],'float4 s=Texture2DSampleLevel(Style,StyleSampler,saturate((P.xy+125000)/250000),0);return lerp(.92,lerp(.85,.64,s.b),(1-s.g)*(1-s.a));',u.CustomMaterialOutputType.CMOT_FLOAT1)
  g.wire(p,rough,'P');g.wire(style,rough,'Style');g.output(rough,u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.08),u.MaterialProperty.MP_SPECULAR)
 window=g.node(u.MaterialExpressionVectorParameter,parameter_name='MR_VisualWindow',default_value=u.LinearColor(-76000,-43200,2400,600))
 cover=g.custom(['P','Window'],'float2 d=abs(P.xy-Window.xy);return 1-smoothstep(Window.z-Window.w,Window.z-50,max(d.x,d.y));',u.CustomMaterialOutputType.CMOT_FLOAT1)
 g.wire(p,cover,'P');g.wire(window,cover,'Window','RGBA')
 d=g.node(u.MaterialExpressionMaterialFunctionCall);assert d.set_material_function(assets.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
 g.wire(cover,d,next(n for n in mel.get_material_expression_input_names(d) if 'alpha' in n.lower()))
 if track:
  old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY);oo=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY)
  mul=g.node(u.MaterialExpressionMultiply);g.wire(old,mul,'A',oo);g.wire(cover,mul,'B');g.output(mul,u.MaterialProperty.MP_OPACITY)
 else:
  props(m,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.5)
  if kind=='Terrain':
   active=g.node(u.MaterialExpressionScalarParameter,parameter_name='MR_ActiveGrid',default_value=0)
   mask=g.custom(['D','Active'],'return 1-D*Active;',u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(d,mask,'D');g.wire(active,mask,'Active');g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
  else:g.output(d,u.MaterialProperty.MP_OPACITY_MASK)
 if kind in ['Detail','Tread']:
  old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);oo=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
  mul=g.node(u.MaterialExpressionMultiply);g.wire(old,mul,'A',oo);g.wire(cover,mul,'B');g.output(mul,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 return matte_ground(m)

def matte_ground(m):
 # Benmore lighting adapter only. Native height updates remain untouched.
 # Keep source geometry intact. Cached reflection is handled by UE lighting.
 for e in mel.get_material_expressions(m):
  if isinstance(e,u.MaterialExpressionCustom):
   code=str(e.get_editor_property('code'))
   # Terrain_003 c22 is the cached reflection colour. Do not bake that
   # view-dependent reflection into UE BaseColor (or the matching tread).
   code=code.replace('float4 c22=float4(1,1,1,0),c23=', 'float4 c22=0,c23=')
   e.set_editor_property('code',code)
 if m.get_name()!='M_Tread':
  g=Graph(m,'WoodlandMatteGround')
  for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,1.),(u.MaterialProperty.MP_SPECULAR,0.)]:
   old=mel.get_material_property_input_node(m,prop)
   if isinstance(old,u.MaterialExpressionConstant) and str(old.get_editor_property('desc'))=='WoodlandMatteGround':old.set_editor_property('r',value)
   else:g.output(g.scalar(value),prop)
 return save(m)

def grass():
 m=copy('/Game/GrandTour/ArtTests/SiberianShowcase/M_Grass','M_Grass')
 props(m,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,two_sided=True,tangent_space_normal=False)
 g=Graph(m,'WoodlandGrassLighting')
 colour=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
 output=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)
 sub=g.node(u.MaterialExpressionMultiply);g.wire(colour,sub,'A',output);g.wire(g.scalar(.04),sub,'B');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
 g.output(g.scalar(0),u.MaterialProperty.MP_SPECULAR)
 g.output(g.vector((0,0,1)),u.MaterialProperty.MP_NORMAL)
 old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK);oo=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY_MASK)
 fade=g.node(u.MaterialExpressionPerInstanceFadeAmount);mul=g.node(u.MaterialExpressionMultiply);g.wire(old,mul,'A',oo);g.wire(fade,mul,'B');g.output(mul,u.MaterialProperty.MP_OPACITY_MASK)
 return save(m)

def fir(source):
 m=copy(source.get_path_name().split('.')[0],'MI_'+source.get_name()+'_Forest')
 for key,rgb in [('TopColor',(.018,.045,.012)),('NoiseColor',(.028,.065,.018)),('SubsurfaceColor',(.015,.035,.008))]:
  mel.set_material_instance_vector_parameter_value(m,key,u.LinearColor(*rgb,1))
  actual=mel.get_material_instance_vector_parameter_value(m,key)
  assert max(abs(a-b) for a,b in zip((actual.r,actual.g,actual.b),rgb))<1e-5
 mel.update_material_instance(m);assert assets.save_loaded_asset(m);return m
