import unreal as u,json,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
from forest_shaders import connected_nodes
try:
 rows=[]
 for k,kind in enumerate(['Mature','Pole','Edge']):
  mesh=u.load_asset(C.DEST+'/SM_CD_Canopy_'+str(k));actual=list(C.sm.get_lod_screen_sizes(mesh));expected=C.distance_screens(mesh,k)
  assert all(abs(a-b)<1e-6 for a,b in zip(actual,expected))
  mat=u.load_asset(C.DEST+'/'+kind+'/M_PD_TreeProxy');nodes=connected_nodes(mat)
  assert any(str(n.get_editor_property('desc'))=='CanopyEnvelopeLighting' for n in nodes)
  assert any(isinstance(n,u.MaterialExpressionCustom) and 'float enclosure=lerp(.24,1.85' in n.get_editor_property('code') for n in nodes)
  assert not u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR),'Temporary diagnostic emissive survived'
  assert u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
  textures=[]
  for name in ['T_PD_TreeColour','T_PD_TreeNormalDepth']:
   t=u.load_asset(C.DEST+'/'+kind+'/'+name);assert t.get_editor_property('never_stream');assert t.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_BC7
   textures.append(dict(name=name,resident=True,compression='BC7',mips=str(t.get_editor_property('mip_gen_settings'))))
  rows.append(dict(kind=kind,screens=actual,far_material_slot=C.sm.get_lod_material_slot(mesh,3,0),textures=textures))
 result=dict(ok=True,trees=rows,protected_packages=C.validate_protected())
 if json.loads((C.OUT/'recipe.json').read_text()).get('surface_shadows'):
  leaf=u.load_asset(C.DEST+'/M_CD_Foliage_SurfaceShadow')
  assert any(str(n.get_editor_property('desc'))=='CanopySurfaceShadow' for n in connected_nodes(leaf))
  mi=u.load_asset(C.DEST+'/MI_CD_Foliage_SurfaceShadow');assert mi.get_editor_property('parent')==leaf
  for k,kind in enumerate(['Mature','Pole','Edge']):
   assert u.load_asset(C.DEST+'/SM_CD_Canopy_'+str(k)).get_material(1)==mi
   mat=u.load_asset(C.DEST+'/'+kind+'/M_PD_TreeProxy')
   assert any(str(n.get_editor_property('desc'))=='CanopySurfaceShadow' for n in connected_nodes(mat))
  field=u.load_asset(C.DEST+'/T_CD_ShadowHeight');assert field.get_editor_property('never_stream')
  assert field.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP
  result['surface_shadows_verified']=True
except Exception:result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
(C.QA/'assets-verified.json').write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
