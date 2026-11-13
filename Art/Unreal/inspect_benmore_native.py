"""Read-only inventory of the saved Benmore level before native-surface integration."""
import unreal as u
import json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/BenmoreNative';OUT.mkdir(parents=True,exist_ok=True)
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
report={'ok':False,'actors':[]};materials={}
def value(v):
 if isinstance(v,u.Object):return v.get_path_name()
 if isinstance(v,(str,int,float,bool)) or v is None:return v
 if isinstance(v,(u.Vector,u.Vector2D)):return [getattr(v,k) for k in ('x','y','z') if hasattr(v,k)]
 try:return [value(x) for x in v]
 except TypeError:return str(v)
try:
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
 for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
  d={'label':a.get_actor_label(),'class':a.get_class().get_name(),'location':value(a.get_actor_location())}
  for key in ['landscape_material','enable_nanite','water_domain','domain_surfaces','ambient_wave_material','surface_material_path','field_cell_cm','max_sim_cells','base_level_cm','default_game_mode','paint_origin_cm','paint_size_cm','landscape','section','shape','blob_half_cm','line_cm','width_cm','start_cm','end_cm','label','patch_material_path','mud_regions']:
   try:d[key]=value(a.get_editor_property(key))
   except Exception:pass
  comps=[]
  for c in a.get_components_by_class(u.MeshComponent):
   cs={'name':c.get_name(),'materials':[]}
   if isinstance(c,u.InstancedStaticMeshComponent):cs['instances']=c.get_instance_count()
   for i in range(c.get_num_materials()):
    m=c.get_material(i)
    if m:materials[m.get_path_name()]=m;cs['materials'].append(m.get_path_name())
   comps.append(cs)
  if comps:d['components']=comps
  if 'landscape_material' in d:
   m=a.get_editor_property('landscape_material');materials[m.get_path_name()]=m
  report['actors'].append(d)
 for path,m in materials.items():
  if isinstance(m,u.Material):
   nodes=[]
   for n in u.MaterialEditingLibrary.get_material_expressions(m):
    if isinstance(n,u.MaterialExpressionCustom):nodes.append({'desc':str(n.get_editor_property('desc')),'code':str(n.get_editor_property('code')),'inputs':[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]})
   if nodes:(OUT/(m.get_name()+'.json')).write_text(json.dumps({'path':path,'custom':nodes},indent=2))
 report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'inventory.json').write_text(json.dumps(report,indent=2))
u.SystemLibrary.quit_editor()
