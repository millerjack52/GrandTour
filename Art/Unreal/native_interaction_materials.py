"""Particle shader arithmetic recovered from build 9640861; UE lighting is the host adapter."""
import unreal as u
from pathlib import Path
from benmore_river_life_materials import Graph,props
BASE='/Game/GrandTour/ArtTests/MudRoad/NativeInteractions'
DATA=Path(u.Paths.project_dir())/'Art/Export/MudRoad/NativeInteractions'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
def texture(name):
 t=props(u.AssetImportTask(),filename=str(DATA/(name+'.png')),destination_path=BASE,destination_name='T_'+name,automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=assets.load_asset(BASE+'/T_'+name);assert a
 props(a,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,never_stream=True)
 assets.save_loaded_asset(a);return a

def make():
 textures={p.stem:texture(p.stem) for p in DATA.glob('*.png') if not p.stem[0].isdigit()}
 rows=[('mud_small','upspray_small',.4,1.,.5,None,0),('mud_large','sheet_large',.2,4.,.12,None,0),
       ('water_small','upspray_fast',0,1,0,(0,.4,.6,.6),0),('water_medium','upspray_medium',.35,2,.2,(.1,.4,.7,.6),10),
       ('water_large','upspray_large',.35,2,.2,(.1,.4,.7,.6),10),('water_fluid','fluid',.4,1,.35,(0,.4,1,.6),40),
       ('mud_bits','fragments',2,.05,5,None,0),('water_drops','fragments',0,1,0,None,0),('water_bits','fragments',0,1,0,None,0)]
 result=[]
 for name,tex,mult,scale,speed,clip,soft in rows:
  m=assets.load_asset(BASE+'/M_'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_'+name,BASE,u.Material,u.MaterialFactoryNew())
  mel.delete_all_material_expressions(m)
  masked=name in ['mud_small','mud_large']
  props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT,two_sided=True,blend_mode=u.BlendMode.BLEND_MASKED if masked else u.BlendMode.BLEND_TRANSLUCENT,opacity_mask_clip_value=.5)
  g=Graph(m);uv=g.node(u.MaterialExpressionTextureCoordinate);age=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=1);col=g.node(u.MaterialExpressionVertexColor)
  diffuse=g.node(u.MaterialExpressionTextureObject,texture=textures[('sfx_particles_' if tex=='fragments' else 'sfx_substance_')+tex+'__d_a'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
  distort=g.node(u.MaterialExpressionTextureObject,texture=textures['sfx_substance_distort__n_d'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
  code=f'''// Particles PS_105/136: self distortion, alpha-kill / alpha-clip.
float2 d=Texture2DSample(Distort,DistortSampler,UV*{scale:.8f}+float2(0,Age.y*{speed:.8f})).rg-.50195998;
float2 q=UV+d*{mult:.8f};
float4 s=Texture2DSample(Sprite,SpriteSampler,q);
float alpha=s.a;
'''
  if clip:
   a,b,c,k=clip;code+=f'''float cut=Age.x<{k} ? lerp({a:.8f},{b:.8f},Age.x/{k}) : lerp({b:.8f},{c:.8f},saturate((Age.x-{k})/(1-{k})));
alpha=saturate((alpha-cut)/max(1-cut*.5,.01));
'''
  code+='Opacity=alpha*VertexAlpha;return pow(max(s.rgb,0),2.2)*Tint.rgb;'
  node=g.custom(['UV','Age','Tint','VertexAlpha','Sprite','Distort'],code,outputs=[('Opacity',u.CustomMaterialOutputType.CMOT_FLOAT1)])
  for key,n in [('UV',uv),('Age',age),('Tint',col),('Sprite',diffuse),('Distort',distort)]:g.wire(n,node,key)
  g.wire(col,node,'VertexAlpha','A')
  g.output(node,u.MaterialProperty.MP_EMISSIVE_COLOR)
  if soft:
   fade=g.node(u.MaterialExpressionDepthFade);pins=mel.get_material_expression_input_names(fade)
   opacity_pin=next(p for p in pins if 'opacity' in str(p).lower());distance_pin=next(p for p in pins if 'distance' in str(p).lower())
   g.wire(node,fade,opacity_pin,'Opacity');g.wire(g.scalar(soft),fade,distance_pin);g.output(fade,u.MaterialProperty.MP_OPACITY)
  else:g.output(node,u.MaterialProperty.MP_OPACITY_MASK if masked else u.MaterialProperty.MP_OPACITY,'Opacity')
  assert not mel.recompile_material(m);assets.save_loaded_asset(m);result.append(m)
 return textures,result

def shore_materials():
 # Rebuild only the mixed-tile wrapper, retaining source mud programs and all
 # authored terrain state. Overlay alpha/specular are actual source channels.
 import mixed_route_materials as mix
 old_inputs=mix.native.shared.inputs
 return mix.soil(assets.load_asset(mix.BASE+'/T_paint'),assets.load_asset(mix.BASE+'/T_rest'),assets.load_asset(mix.BASE+'/T_style'),assets.load_asset(mix.BASE+'/T_macro'))

def terrain_oracle():
 m=assets.load_asset(BASE+'/M_TerrainOverlayOracle') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_TerrainOverlayOracle',BASE,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m);props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT)
 g=Graph(m);uv=g.node(u.MaterialExpressionTextureCoordinate)
 e=g.custom(['UV'],(DATA/'terrain-overlay-oracle.hlsl').read_text());g.wire(uv,e,'UV');g.output(e,u.MaterialProperty.MP_EMISSIVE_COLOR)
 assert not mel.recompile_material(m);assets.save_loaded_asset(m)
