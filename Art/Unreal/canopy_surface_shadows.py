"""Per-surface canopy occlusion, shared by geometry and distance proxies."""
import unreal as u,json,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
from benmore_river_life_materials import Graph,props
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary

def import_field():
 task=props(u.AssetImportTask(),filename=str(C.OUT/'T_CD_ShadowHeight.png'),destination_path=C.DEST,destination_name='T_CD_ShadowHeight',automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(C.DEST+'/T_CD_ShadowHeight')
 # RG stores one 16-bit height. Lossy block compression would corrupt carries.
 props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True,max_texture_size=2048,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
 assert assets.save_loaded_asset(tex,False)

def wrap(m,surface=None,surface_output=''):
 from forest_shaders import connected_nodes
 nodes=connected_nodes(m);data=json.loads((C.OUT/'shadow-height.json').read_text())
 if any(str(n.get_editor_property('desc'))=='CanopySurfaceShadow' for n in nodes):
  # A rebake can change the packed height range without changing the graph.
  ranges=[n for n in nodes if isinstance(n,u.MaterialExpressionConstant3Vector) and (str(n.get_editor_property('desc'))=='CanopyShadowHeightRange' or (abs(n.constant.r+20)<.001 and abs(n.constant.b)<.001))]
  assert len(ranges)==1
  ranges[0].set_editor_property('desc','CanopyShadowHeightRange')
  ranges[0].set_editor_property('constant',u.LinearColor(data['height_min_m'],data['height_max_m']-data['height_min_m'],0,0))
  assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
  return
 g=Graph(m,'CanopySurfaceShadow')
 base=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
 baseout=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)
 ao=mel.get_material_property_input_node(m,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 aoout=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_AMBIENT_OCCLUSION) if ao else ''
 if not ao:ao=g.scalar(1)
 if surface is None:surface=g.node(u.MaterialExpressionWorldPosition)
 field=g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(C.DEST+'/T_CD_ShadowHeight'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 span=g.vector((data['height_min_m'],data['height_max_m']-data['height_min_m'],0))
 span.set_editor_property('desc','CanopyShadowHeightRange')
 node=g.custom(['C','OldAO','Surface','Camera','Field','HeightRange'],'''
float distance=length(Camera-Surface);
float fade=smoothstep(12000,36000,distance);
float2 uv=(Surface.xy+185000)/370000;
float2 packed=Texture2DSampleLevel(Field,FieldSampler,uv,0).rg;
float ceiling=HeightRange.x+HeightRange.y*dot(packed,float2(65280,255))/65535;
// Broad penumbra and bias accommodate the porous crown envelope.
float visibility=smoothstep(-2.0,2.0,Surface.z*.01+2.5-ceiling);
float3 light=lerp(float3(.20,.28,.36),float3(1.18,1.14,1.04),visibility);
AO=OldAO*lerp(1,lerp(.70,1,visibility),fade);
return C*lerp(float3(1,1,1),light,fade);
''',outputs=[('AO',u.CustomMaterialOutputType.CMOT_FLOAT1)])
 for a,key,out in [(base,'C',baseout),(ao,'OldAO',aoout),(surface,'Surface',surface_output),(g.node(u.MaterialExpressionCameraPositionWS),'Camera',''),(field,'Field',''),(span,'HeightRange','')]:g.wire(a,node,key,out)
 g.output(node,u.MaterialProperty.MP_BASE_COLOR);g.output(node,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO')
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)

def install():
 import_field()
 source=u.load_asset(C.BASE+'/MI_NZ_Foliage_Canopy');parent=source.get_editor_property('parent')
 assert isinstance(parent,u.Material),parent
 name=C.DEST+'/M_CD_Foliage_SurfaceShadow'
 m=u.load_asset(name) or assets.duplicate_asset(parent.get_path_name().split('.')[0],name)
 wrap(m)
 path=C.DEST+'/MI_CD_Foliage_SurfaceShadow'
 mi=u.load_asset(path) or assets.duplicate_asset(source.get_path_name().split('.')[0],path)
 mel.set_material_instance_parent(mi,m);assert assets.save_loaded_asset(mi,False)
 for k in range(3):
  mesh=u.load_asset(C.DEST+'/SM_CD_Canopy_'+str(k));mesh.set_material(1,mi);assert assets.save_loaded_asset(mesh,False)
 recipe=json.loads((C.OUT/'recipe.json').read_text());recipe['surface_shadows']=True;(C.OUT/'recipe.json').write_text(json.dumps(recipe,indent=2))
 return dict(ok=True,source=source.get_path_name(),parent=parent.get_path_name(),material=mi.get_path_name(),field=json.loads((C.OUT/'shadow-height.json').read_text()),protected_packages=C.validate_protected())

if __name__=='__main__':
 try:result=install()
 except Exception:result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
 (C.QA/'surface-shadow-materials.json').write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
