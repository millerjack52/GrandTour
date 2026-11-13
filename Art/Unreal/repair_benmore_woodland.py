"""Repair saved materials and dust without reauthoring the user's level."""
import unreal as u
from pathlib import Path
import sys,json,traceback,shutil,time,hashlib
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_woodland_materials as mat
OUT=mat.OUT;BASE=mat.BASE;report=dict(ok=False)
try:
 target=ROOT/'Content/GrandTour/ArtTests/BenmoreWoodland'
 backup=ROOT/'Saved/BenmoreWoodlandBackups'/str(time.time_ns());shutil.copytree(target,backup);report['backup']=str(backup)
 paths=[ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap',ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain.uasset']
 paths+=list((ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces').glob('M_NativeDomain*.uasset'))
 hashes=lambda:{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 before=hashes();les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_Benmore_Woodland')
 for name in ['Terrain','Detail','Tread']:mat.matte_ground(u.load_asset(BASE+'/M_'+name))
 import benmore_mud_relief
 surfaces=[a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.GTLandscapeSurface)]
 assert len(surfaces)==1;benmore_mud_relief.install(surfaces[0])
 import benmore_woodland_detail
 report['soil_detail']=benmore_woodland_detail.install()
 import woodland_mud_clods
 report['native_clods']=woodland_mud_clods.install()
 if surfaces[0].grass_is_visual_cover:
  import woodland_sunlit_ground
  report['sunlit_ground']=woodland_sunlit_ground.install(u.load_asset(BASE+'/T_style_groundstudy'))
 effects=[a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.GTVehicleSurfaceEffects)]
 assert effects
 # Keep the dust coordinator's ownership: deleting its system would re-enable
 # legacy spray dust. Zero intensity stops every contact/wake/trail emitter.
 for a in effects:a.set_editor_property('dust_intensity',0.)
 assert les.save_current_level();assert les.load_level('/Engine/Maps/Entry');assert les.load_level(BASE+'/L_Benmore_Woodland')
 assert hashes()==before;report.update(ok=True,protected_hashes=before,dust_intensity=0,cosmetic_noise=True,ground_roughness='spatial daylight adapter' if 'sunlit_ground' in report else .78,ground_specular=.12,scanned_soil_override=False,physical_rest_detail_cm=12.5)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'repair.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
