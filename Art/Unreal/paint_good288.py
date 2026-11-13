"""Apply baked GT Paint normals to the existing validated Ferrari rig."""
import unreal as u,json,traceback
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-painterly-v01')
DEST='/Game/GrandTour/Vehicles/Ferrari288Good'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
def prop(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def save(o):assert E.save_loaded_asset(o,False)
report={'ok':False}
try:
 data=json.loads((OUT/'painterly-report.json').read_text());assert data['ok']
 task=prop(u.AssetImportTask(),filename=str(OUT/'T_GT_Ferrari288_N.png'),destination_path=DEST+'/Textures',automated=True,replace_existing=True,save=False)
 A.import_asset_tasks([task]);tex=E.load_asset(DEST+'/Textures/T_GT_Ferrari288_N');assert tex
 prop(tex,compression_settings=u.TextureCompressionSettings.TC_NORMALMAP,srgb=False,flip_green_channel=False);save(tex)
 name='M_F288_Painterly';path=DEST+'/Materials/'+name
 mat=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(mat);M.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
 def node(cls,x,y,**kw):return prop(M.create_material_expression(mat,cls,x,y),**kw)
 albedo=E.load_asset(DEST+'/Textures/T_F288_Source');assert albedo
 color=node(u.MaterialExpressionTextureSample,-600,-300,texture=albedo,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
 assert M.connect_material_property(color,'RGB',u.MaterialProperty.MP_BASE_COLOR)
 normal=node(u.MaterialExpressionTextureSample,-600,0,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 flat=node(u.MaterialExpressionConstant3Vector,-600,250,constant=u.LinearColor(0,0,1,1))
 strength=node(u.MaterialExpressionScalarParameter,-600,420,parameter_name='BrushNormalStrength',default_value=.5)
 blend=node(u.MaterialExpressionLinearInterpolate,-260,100)
 assert M.connect_material_expressions(flat,'',blend,'A');assert M.connect_material_expressions(normal,'RGB',blend,'B');assert M.connect_material_expressions(strength,'',blend,'Alpha')
 norm=node(u.MaterialExpressionNormalize,-60,100);assert M.connect_material_expressions(blend,'',norm,'VectorInput');assert M.connect_material_property(norm,'',u.MaterialProperty.MP_NORMAL)
 for y,val,pin in [(400,.78,u.MaterialProperty.MP_ROUGHNESS),(520,.05,u.MaterialProperty.MP_METALLIC)]:
  c=node(u.MaterialExpressionConstant,-200,y,r=val);assert M.connect_material_property(c,'',pin)
 M.recompile_material(mat);save(mat)
 sk=E.load_asset(DEST+'/SK_Ferrari288');slots=list(sk.get_editor_property('materials'));before=[s.material_interface.get_path_name() for s in slots]
 for slot in slots:
  if str(slot.get_editor_property('imported_material_slot_name'))=='F288_Source':slot.material_interface=mat
 sk.set_editor_property('materials',slots);save(sk)
 assert u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(sk)==3
 report.update(ok=True,material=path,texture=tex.get_path_name(),normal_strength=.5,roughness=.78,directx_no_green_flip=True,previous_materials=before,materials=[s.material_interface.get_path_name() for s in slots],geometry_reimported=False)
except Exception:report['error']=traceback.format_exc();raise
finally:(OUT/'unreal-painterly-report.json').write_text(json.dumps(report,indent=2))
# Use the existing capture-only PIE harness against all three LODs.
p=Path('C:/GrandTour/Art/Unreal/test_good288.py')
s=p.read_text().replace("s=s.replace('graphic-adventure-unreal-v01','ferrari288-good-game-v01')","s=s.replace('graphic-adventure-unreal-v01','ferrari288-painterly-v01')")
exec(compile(s,str(p),'exec'))
