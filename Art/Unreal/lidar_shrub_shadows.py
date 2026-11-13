"""Audit and restore physical shadows on LiDAR shrubs and the authored bank plants."""
import unreal as u,json,hashlib,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_first_section as section
QA=ROOT/'Saved/LidarAuthoringQA/ShrubShadows';QA.mkdir(parents=True,exist_ok=True)
WOODY=('Coprosma','Gorse','Broom','Matagouri','Shrub')
def candidates():
 for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
  if not a.get_actor_label().startswith('LidarStudy'):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if not c.static_mesh:continue
   name=c.static_mesh.get_name()
   if any(k in name for k in WOODY) or (a.get_actor_label().startswith(section.PREFIX) and name.startswith('SM_RS7_') and 'BankSkin' not in name):yield a,c

def digest():
 rows=[]
 for a,c in candidates():
  for i in range(c.get_instance_count()):rows.append([a.get_actor_label(),c.get_name(),c.static_mesh.get_path_name(),section.tfkey(c.get_instance_transform(i,True))])
 return dict(count=len(rows),hash=hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest())

def audit():
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);rows=[];meshes={}
 for a,c in candidates():
  row=dict(actor=a.get_actor_label(),component=c.get_name(),mesh=c.static_mesh.get_path_name(),instances=c.get_instance_count(),materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())])
  for prop in ['cast_shadow','cast_dynamic_shadow','cast_contact_shadow','cast_shadow_as_two_sided','affect_distance_field_lighting','visible_in_ray_tracing']:
   try:row[prop]=c.get_editor_property(prop)
   except Exception:row[prop]='not_exposed'
  rows.append(row)
  if row['mesh'] not in meshes:
   meshes[row['mesh']]=[[sm.is_section_cast_shadow_enabled(c.static_mesh,lod,sec) for sec in range(c.static_mesh.get_num_sections(lod))] for lod in range(sm.get_lod_count(c.static_mesh))]
 report=dict(components=rows,mesh_section_cast_shadow=meshes,planting=digest(),local=section.snapshot(),outside=section.outside_snapshot())
 (QA/'audit.json').write_text(json.dumps(report,indent=2));print('SHRUB_SHADOW_AUDIT',len(rows),sum(r['instances'] for r in rows))
 return report

def apply():
 original=json.loads((QA/'audit.json').read_text());assert digest()==original['planting']
 changed=[]
 for a,c in candidates():
  a.modify();c.modify();c.set_cast_shadow(True)
  c.set_editor_property('cast_dynamic_shadow',True);c.set_editor_property('cast_shadow_as_two_sided',True)
  assert c.get_editor_property('cast_shadow') and c.get_editor_property('cast_dynamic_shadow') and c.get_editor_property('cast_shadow_as_two_sided')
  changed.append(dict(actor=a.get_actor_label(),component=c.get_name(),instances=c.get_instance_count()))
 assert digest()==original['planting'] and section.snapshot()==original['local'] and section.outside_snapshot()==original['outside']
 report=dict(ok=True,changed_components=changed,planting=digest(),local=section.snapshot(),outside=section.outside_snapshot(),validation=section.validate(),policy='Physical dynamic shadows and two-sided shadow casting on woody shrubs and the 152 authored bank plants. No transforms, materials, cull distances or collision settings changed.')
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
 (QA/'installed.json').write_text(json.dumps(report,indent=2));print('SHRUB_SHADOWS_INSTALLED',report['planting'])
