import unreal as u
from pathlib import Path
import sys,json,traceback,shutil,time,hashlib
R=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(R/'Art/Unreal'))
from woodland_native_grass import build,build_distance_cover,BASE
report={'ok':False}
try:
 target=R/'Content/GrandTour/ArtTests/BenmoreWoodland';backup=R/'Saved/BenmoreWoodlandBackups'/('grass-'+str(time.time_ns()));shutil.copytree(target,backup);report['backup']=str(backup)
 protected=[*target.glob('M_Terrain.uasset'),*target.glob('M_Detail.uasset'),*target.glob('M_Tread.uasset'),*(R/'Content/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces').glob('M_NativeDomain*.uasset')]
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_Benmore_Woodland');m=build()
 details=[a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.GTMixedGroundDetails)];assert details
 distant=build_distance_cover()
 for a in details:
  a.set_editor_property('grass_material',m);a.grass.set_material(0,m)
  if a.generate_around_player:a.set_editor_property('distant_grass_material',distant)
 assert les.save_current_level();les.load_level('/Engine/Maps/Entry');assert les.load_level(BASE+'/L_Benmore_Woodland')
 a=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.GTMixedGroundDetails));assert a.grass_material==m
 assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 report.update(ok=True,material=m.get_path_name(),protected_hashes=hashes,source_variant='Plants GRASS 0x11fda5c',wind_metres=.04,alpha_clip=.35,lighting='UE foliage adapter',distance_material=distant.get_path_name(),distance_fade_metres=[95,120],near_overlap_metres=[18,26])
 les.load_level('/Engine/Maps/Entry')
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(R/'Art/Export/BenmoreWoodland/grassinstall.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
