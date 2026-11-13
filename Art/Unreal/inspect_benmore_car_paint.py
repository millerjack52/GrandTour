import unreal as u,json,time,traceback
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-benmore-paint');OUT.mkdir(exist_ok=True)
u.EditorPythonScripting.set_keep_python_script_alive(True)
les=u.get_editor_subsystem(u.LevelEditorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
les.load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
start=time.monotonic();phase=0;result={};materials={}
def inspect(m):
 if not m:return None
 p=m.get_path_name()
 if p in materials:return p
 row={'class':m.get_class().get_name()};materials[p]=row
 if isinstance(m,u.MaterialInstance):
  parent=m.get_editor_property('parent');row['parent']=inspect(parent)
  for typ in ['scalar','vector','texture']:
   fn=getattr(M,'get_'+typ+'_parameter_names');get=getattr(M,'get_material_instance_'+typ+'_parameter_value')
   if isinstance(m,u.MaterialInstanceDynamic):
    get=getattr(m,'k2_get_'+typ+'_parameter_value');row[typ]={str(n):str(get(n)) for n in fn(m)}
   else:row[typ]={str(n):str(get(m,n)) for n in fn(m)}
 return p
def tick(dt):
 global phase,start
 try:
  if phase==0 and time.monotonic()-start>4:
   les.editor_request_begin_play();phase=1;start=time.monotonic()
  elif phase==1 and time.monotonic()-start>20:
   world=u.EditorLevelLibrary.get_game_world();car=u.GameplayStatics.get_player_pawn(world,0);result['pawn']=car.get_class().get_path_name();result['components']=[]
   for c in car.get_components_by_class(u.MeshComponent):
    row={'name':c.get_name(),'class':c.get_class().get_name(),'materials':[inspect(c.get_material(i)) for i in range(c.get_num_materials())]}
    result['components'].append(row)
   result['materials']=materials
   (OUT/'reference-materials.json').write_text(json.dumps(result,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
 except Exception:
  (OUT/'inspect-error.txt').write_text(traceback.format_exc());result['materials']=materials;(OUT/'reference-partial.json').write_text(json.dumps(result,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
