"""Use Benmore's existing vehicle paint parent, with Ferrari-specific GT bakes."""
import unreal as u,json
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-benmore-paint')
DEST='/Game/GrandTour/Vehicles/Ferrari288Good';E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def prop(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def save(o):assert E.save_loaded_asset(o,False)
assert json.loads((OUT/'paint-report.json').read_text())['ok']
parent=E.load_asset('/Game/GrandTour/Materials/M_GT_Vehicle');assert parent
(OUT/'parent-parameters.json').write_text(json.dumps({typ:[str(x) for x in getattr(M,'get_'+typ+'_parameter_names')(parent)] for typ in ['scalar','vector','texture']},indent=2))
name='MI_F288_GT_Painted';path=DEST+'/Materials/'+name
mi=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
M.set_material_instance_parent(mi,parent)
M.update_material_instance(mi)
for suffix,param in [('D','PaintAlbedo'),('M','PaintMask'),('N','PaintNormal')]:
 task=prop(u.AssetImportTask(),filename=str(OUT/f'T_F288_GT_{suffix}.png'),destination_path=DEST+'/Textures',automated=True,replace_existing=True,save=False);A.import_asset_tasks([task])
 tex=E.load_asset(DEST+f'/Textures/T_F288_GT_{suffix}');assert tex
 prop(tex,srgb=suffix=='D',compression_settings={'D':u.TextureCompressionSettings.TC_DEFAULT,'M':u.TextureCompressionSettings.TC_MASKS,'N':u.TextureCompressionSettings.TC_NORMALMAP}[suffix])
 if suffix=='N':prop(tex,flip_green_channel=False)
 save(tex);M.set_material_instance_texture_parameter_value(mi,param,tex)
for name,value in [('UsePaint',1.),('ImpactCount',0.),('Dirt',0.),('Wetness',0.),('Snow',0.)]:
 M.set_material_instance_scalar_parameter_value(mi,name,value)
M.update_material_instance(mi);save(mi)
assert M.get_material_instance_scalar_parameter_value(mi,'UsePaint')==1.
for suffix,param in [('D','PaintAlbedo'),('M','PaintMask'),('N','PaintNormal')]:
 assert M.get_material_instance_texture_parameter_value(mi,param)==E.load_asset(DEST+f'/Textures/T_F288_GT_{suffix}'),param
sk=E.load_asset(DEST+'/SK_Ferrari288');slots=list(sk.get_editor_property('materials'));changed=0
for slot in slots:
 if str(slot.get_editor_property('imported_material_slot_name'))=='F288_Source':slot.material_interface=mi;changed+=1
assert changed==1;sk.set_editor_property('materials',slots);save(sk)
assert mi.get_editor_property('parent')==parent
report={'ok':True,'parent':parent.get_path_name(),'material':mi.get_path_name(),'textures':{str(n):str(M.get_material_instance_texture_parameter_value(mi,n)) for n in M.get_texture_parameter_names(mi)},'scalar_parameters':{str(n):M.get_material_instance_scalar_parameter_value(mi,n) for n in M.get_scalar_parameter_names(mi)},'geometry_reimported':False,'reference':'BenmoreGaea native GTCarPawn with 18 GT Body panels using M_GT_Vehicle and UsePaint=1; inspected runtime log InspectBenmoreCarPaint.log'}
(OUT/'unreal-paint-report.json').write_text(json.dumps(report,indent=2))
p=Path('C:/GrandTour/Art/Unreal/test_good288.py');s=p.read_text().replace("s=s.replace('graphic-adventure-unreal-v01','ferrari288-good-game-v01')","s=s.replace('graphic-adventure-unreal-v01','ferrari288-benmore-paint')");exec(compile(s,str(p),'exec'))
