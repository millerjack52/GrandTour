"""Apply terrain/crown-envelope lighting to distant forest materials only."""
import unreal as u,sys,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
import perceived_tree_proxy as proxy
import canopy_depth as C
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
def wrap(m):
 from forest_shaders import connected_nodes
 if any(str(n.get_editor_property('desc'))=='CanopyEnvelopeLighting' for n in connected_nodes(m)):return
 g=Graph(m,'CanopyEnvelopeLighting')
 old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
 oldnormal=mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
 oldao=mel.get_material_property_input_node(m,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 oldaoout=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 origin=proxy.position(g,g.vector((0,0,0)),u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE,u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
 tex=g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(C.DEST+'/T_CD_Lighting'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 node=g.custom(['C','N','OldAO','Origin','Camera','Field'],'''
float distance=length(Camera-Origin);float far=smoothstep(10000,26000,distance);
float2 uv=(Origin.xy+185000)/370000;
float4 f=Texture2DSampleLevel(Field,FieldSampler,uv,clamp(log2(max(1,distance/18000)),0,5));
float2 xy=f.rg*2-1;float3 macro=normalize(float3(xy,sqrt(max(.01,1-dot(xy,xy)))));
Normal=normalize(lerp(N,macro,far*.18));
// Preserve crown-scale light/shade separation after distant texture filtering.
// Use captured surface normals and the baked sun, never the viewing direction.
float3 sun=normalize(float3(-.1586355,.8996666,.4067366));
float top=smoothstep(.08,.82,normalize(N).z);
float facing=smoothstep(-.20,.45,dot(normalize(N),sun));
float lit=sqrt(saturate(top*facing));
float contrast=smoothstep(15000,40000,distance);
float visibility=smoothstep(.08,.95,f.b);
float3 crown=lerp(float3(.50,.58,.70),float3(2.15,2.00,1.70),lit*visibility);
AO=OldAO*lerp(1,f.a,far)*lerp(1,lerp(.72,1,lit),contrast);
float3 shadow=lerp(float3(.24,.31,.39),float3(1,1,1),visibility);
return C*lerp(float3(1,1,1),shadow,far)*lerp(float3(1,1,1),crown,contrast);
''',outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('AO',u.CustomMaterialOutputType.CMOT_FLOAT1)])
 for a,key,out in [(old,'C',''),(oldnormal,'N',''),(oldao,'OldAO',oldaoout),(origin,'Origin',''),(g.node(u.MaterialExpressionCameraPositionWS),'Camera',''),(tex,'Field','')]:g.wire(a,node,key,out)
 g.output(node,u.MaterialProperty.MP_BASE_COLOR);g.output(node,u.MaterialProperty.MP_NORMAL,'Normal');g.output(node,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO')
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 if json.loads((C.OUT/'recipe.json').read_text()).get('surface_shadows'):
  import canopy_surface_shadows
  captured=next(n for n in connected_nodes(m) if isinstance(n,u.MaterialExpressionCustom) and 'LocalSurface=Centre' in n.get_editor_property('code'))
  surface=proxy.position(g,captured,u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE,u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,'LocalSurface')
  canopy_surface_shadows.wrap(m,surface)
def install():
 task=props(u.AssetImportTask(),filename=str(C.OUT/'T_CD_Lighting.png'),destination_path=C.DEST,destination_name='T_CD_Lighting',automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(C.DEST+'/T_CD_Lighting');assert t
 props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_BC7,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,never_stream=True,max_texture_size=2048,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
 assert assets.save_loaded_asset(t,False)
 for kind in ['Mature','Pole','Edge']:
  proxy.OUT=C.OUT/kind;proxy.PD=C.DEST+'/'+kind
  m=proxy.material(json.loads((C.OUT/kind/'tree-bake.json').read_text()));wrap(m)
 # The old handover left most valley trees on geometry LOD2. Select the
 # elevation-aware representation by valley range, retaining geometry nearby.
 lods=[]
 for k in range(3):
  mesh=u.load_asset(C.DEST+'/SM_CD_Canopy_'+str(k));screens=C.distance_screens(mesh,k)
  assert C.sm.set_lod_screen_sizes(mesh,screens);assert assets.save_loaded_asset(mesh,False)
  lods.append(dict(kind=k,screens=screens))
 return dict(ok=True,field=json.loads((C.OUT/'lighting-field.json').read_text()),protected_packages=C.validate_protected(),lods=lods)
if __name__=='__main__':
 try:result=install()
 except Exception:result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
 (C.QA/'lighting-result.json').write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
