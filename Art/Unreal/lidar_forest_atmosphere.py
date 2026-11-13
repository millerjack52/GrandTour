"""Map-owned atmosphere and far-crown tuning; never regenerates planting."""
import unreal as u,json,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
BASE='/Game/GrandTour/ArtTests/LidarStudy'
QA=ROOT/'Saved/LidarAuthoringQA/Atmosphere'
CONFIG=ROOT/'Art/Export/LidarStudy/Place/forest-atmosphere.json'
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)

def props(obj,values):
 for key,value in values.items():obj.set_editor_property(key,value)

def multiplier(settings,mesh):
 return settings.get('far_card_screen_multipliers',{}).get(mesh.get_name().rsplit('_',1)[-1],settings['far_card_screen_multiplier'])

def apply_global_fog():
 settings=json.loads(CONFIG.read_text())
 fogs=[a for a in actors.get_all_level_actors() if isinstance(a,u.ExponentialHeightFog)]
 assert len(fogs)==1
 fog=fogs[0];fog.set_actor_location(u.Vector(0,0,settings['height_cm']),False,True)
 props(fog.component,dict(fog_density=settings['density'],fog_height_falloff=settings['height_falloff'],start_distance=settings['start_cm'],fog_max_opacity=settings['max_opacity'],fog_inscattering_luminance=u.LinearColor(*settings['luminance'],1),enable_volumetric_fog=False))
 if settings.get('far_haze',{}).get('enabled'):
  import lidar_far_haze
  lidar_far_haze.apply(settings['far_haze'])
 import firewatch_distance_style as distance_style
 if distance_style.enabled():distance_style.apply_haze()
 return settings

def apply(save_map=True):
 import lidar_first_section as section
 settings=json.loads(CONFIG.read_text());survey=json.loads((QA/'survey.json').read_text())
 before=section.snapshot();outside=section.outside_snapshot()
 assert before==survey['snapshot'] and outside==survey['outside']
 apply_global_fog()
 pockets=[]
 for row in settings['pockets']:
  label='LidarAtmosphere_Mist_'+row['name']
  a=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None) or actors.spawn_actor_from_class(u.LocalFogVolume,u.Vector(*row['position']))
  a.set_actor_label(label);a.set_actor_location(u.Vector(*row['position']),False,True)
  a.set_actor_scale3d(u.Vector(*([row['radius_cm']/500]*3)))
  c=a.get_component_by_class(u.LocalFogVolumeComponent)
  props(c,dict(radial_fog_extinction=row['radial'],height_fog_extinction=row['height'],height_fog_falloff=5.,height_fog_offset=-.15,fog_phase_g=.15,fog_albedo=u.LinearColor(.24,.34,.36,1),fog_emissive=u.LinearColor(0,0,0,1),fog_start_distance=2600.))
  pockets.append(dict(label=label,position=row['position'],radius_cm=row['radius_cm']))
 lods=[]
 for row in survey['forest']:
  if '/CanopyKit/' not in row['mesh']:continue
  mesh=u.load_asset(row['mesh']);screens=list(row['screens']);screens[-1]*=multiplier(settings,mesh)
  assert sm.set_lod_screen_sizes(mesh,screens)
  assert u.EditorAssetLibrary.save_loaded_asset(mesh,False)
  lods.append(dict(mesh=mesh.get_path_name(),before=row['screens'],after=list(sm.get_lod_screen_sizes(mesh))))
 assert section.snapshot()==before and section.outside_snapshot()==outside
 if save_map:assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
 report=dict(ok=True,settings=settings,pockets=pockets,lods=lods,snapshot=before,outside=outside,backup=survey['backup'],sun_sky_exposure_unchanged=True)
 (QA/'install.json').write_text(json.dumps(report,indent=2))
 return report

def validate():
 import lidar_first_section as section
 settings=json.loads(CONFIG.read_text());survey=json.loads((QA/'survey.json').read_text())
 assert section.snapshot()==survey['snapshot'] and section.outside_snapshot()==survey['outside']
 refs=actors.get_all_level_actors();fog=next(a for a in refs if isinstance(a,u.ExponentialHeightFog))
 for key,value in [('fog_density',settings['density']),('start_distance',settings['start_cm']),('fog_max_opacity',settings['max_opacity'])]:
  assert abs(fog.component.get_editor_property(key)-value)<.0001,(key,value)
 assert abs(fog.get_actor_location().z-settings['height_cm'])<.001
 assert not fog.component.get_editor_property('enable_volumetric_fog')
 for row in settings['pockets']:
  a=next(a for a in refs if a.get_actor_label()=='LidarAtmosphere_Mist_'+row['name'])
  c=a.get_component_by_class(u.LocalFogVolumeComponent)
  assert abs(c.get_editor_property('radial_fog_extinction')-row['radial'])<.00001
  assert abs(a.get_actor_scale3d().x*500-row['radius_cm'])<.01
 forest=next(a for a in refs if a.get_actor_label()=='LidarStudy_Forest')
 components={c.get_name():c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent)}
 for row in survey['forest']:
  c=components[row['component']];assert c.get_instance_count()==row['count'] and c.static_mesh.get_path_name()==row['mesh']
  if '/CanopyKit/' not in row['mesh']:continue
  screens=list(sm.get_lod_screen_sizes(c.static_mesh))
  assert all(abs(a-b)<.000001 for a,b in zip(screens[:-1],row['screens'][:-1]))
  assert abs(screens[-1]-row['screens'][-1]*multiplier(settings,c.static_mesh))<.000001
  assert [sm.get_number_verts(c.static_mesh,i) for i in range(sm.get_lod_count(c.static_mesh))]==row['vertices']
 report=dict(ok=True,planting_unchanged=True,terrain_unchanged=True,tree_counts_unchanged=True,near_lods_unchanged=True,settings=settings)
 (QA/'validation.json').write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':apply()
