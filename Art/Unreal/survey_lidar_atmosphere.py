"""Read the saved LiDAR atmosphere and distance representations before tuning."""
import unreal as u, json, sys, shutil, time
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_first_section as section
QA=ROOT/'Saved/LidarAuthoringQA/Atmosphere';QA.mkdir(exist_ok=True)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
def read(obj,keys):
 out={}
 for k in keys:
  try:
   v=obj.get_editor_property(k)
   out[k]=v if isinstance(v,(str,float,int,bool)) else str(v)
  except Exception as e:out[k]=str(e)
 return out
rows=[];forest=[];cameras=[]
for a in actors.get_all_level_actors():
 row=dict(name=a.get_name(),label=a.get_actor_label(),type=a.get_class().get_name(),location=str(a.get_actor_location()))
 if isinstance(a,u.ExponentialHeightFog):
  row['properties']=read(a.component,['fog_density','fog_height_falloff','start_distance','fog_max_opacity','fog_inscattering_luminance','second_fog_data','volumetric_fog','volumetric_fog_distance','directional_inscattering_luminance','directional_inscattering_exponent']);rows.append(row)
 elif isinstance(a,u.SkyAtmosphere):
  row['properties']=read(a.get_component_by_class(u.SkyAtmosphereComponent),['aerial_perspective_view_distance_scale','aerial_perspective_start_depth','rayleigh_scattering_scale','mie_scattering_scale','height_fog_contribution']);rows.append(row)
 elif isinstance(a,u.SkyLight):
  row['properties']=read(a.light_component,['intensity','light_color','real_time_capture','lower_hemisphere_is_black']);rows.append(row)
 elif isinstance(a,u.DirectionalLight):
  row['rotation']=str(a.get_actor_rotation());row['properties']=read(a.light_component,['intensity','light_color','light_source_angle','atmosphere_sun_light']);rows.append(row)
 elif isinstance(a,u.CameraActor):
  row['rotation']=str(a.get_actor_rotation());row['fov']=a.camera_component.field_of_view;cameras.append(row)
 if a.get_actor_label()=='LidarStudy_Forest':
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   m=c.static_mesh
   if not m:continue
   r=dict(component=c.get_name(),mesh=m.get_path_name(),count=c.get_instance_count(),properties=read(c,['instance_lod_distance_scale','instance_start_cull_distance','instance_end_cull_distance','forced_lod_model']),materials=[str(c.get_material(i)) for i in range(c.get_num_materials())])
   r['screens']=list(sm.get_lod_screen_sizes(m));r['vertices']=[sm.get_number_verts(m,i) for i in range(sm.get_lod_count(m))];forest.append(r)
backup=ROOT/'Saved/LidarAuthoringBackups'/('Atmosphere-'+str(time.time_ns()));backup.mkdir()
content=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
shutil.copy2(content/'L_LidarStudy.umap',backup/'L_LidarStudy.umap')
shutil.copytree(content/'CanopyKit',backup/'CanopyKit')
report=dict(backup=str(backup),atmosphere=rows,forest=forest,cameras=cameras,snapshot=section.snapshot(),outside=section.outside_snapshot())
(QA/'survey.json').write_text(json.dumps(report,indent=2))
print('ATMOSPHERE_SURVEY_DONE')
