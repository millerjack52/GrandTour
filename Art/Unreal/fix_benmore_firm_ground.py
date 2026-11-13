"""Stop unprofiled Benmore ground from continuously sinking tyres; preserve authored mud profiles."""
import unreal as u,json,traceback,shutil,hashlib
from pathlib import Path
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/BenmoreFleet/FerrariGroundContact'
MAP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/PM_Benmore_FirmGround'
report={'ok':False}
try:
    source=ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap';backup=OUT/'before-firm-ground.umap'
    if not backup.exists():shutil.copy2(source,backup)
    e=u.EditorAssetLibrary;les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(MAP)
    old=e.load_asset('/Game/GrandTour/Terrain/Surfaces/PM_Dirt')
    oldfile=ROOT/'Content/GrandTour/Terrain/Surfaces/PM_Dirt.uasset';oldhash=hashlib.sha256(oldfile.read_bytes()).hexdigest()
    pm=e.load_asset(DEST) if e.does_asset_exist(DEST) else e.duplicate_asset(old.get_path_name().split('.')[0],DEST)
    # A zero growth rate makes ordinary grass/dirt firm. Keep MaxSinkage and the other row values:
    # GTTractionComponent uses MaxSinkage>0 as eligibility for the explicit crossing profiles,
    # which replace both the rate and cap inside their bounds. Global PM_Dirt is untouched.
    pm.set_editor_property('sinkage_rate',0.);assert e.save_loaded_asset(pm,False)
    report['changed_landscapes']=[];report['profile_assets']={};report['firm_layers']=[]
    for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if isinstance(a,u.LandscapeProxy):
            prior=a.get_editor_property('default_phys_material');assert prior==old or prior==pm,prior
            a.modify();a.set_editor_property('default_phys_material',pm)
            layers=a.get_editor_property('target_layers');replacements={}
            for name,setting in layers.items():
                info=setting.get_editor_property('layer_info_obj')
                if info and info.get_editor_property('phys_material') in [old,pm]:
                    dest=DEST.rsplit('/',1)[0]+'/FirmGroundLayers/'+info.get_name()
                    local=e.load_asset(dest) if e.does_asset_exist(dest) else e.duplicate_asset(info.get_path_name().split('.')[0],dest)
                    local.set_editor_property('phys_material',pm);assert e.save_loaded_asset(local,False)
                    setting.set_editor_property('layer_info_obj',local);layers[name]=setting
                    replacements[info]=local
                    report['firm_layers'].append(str(name))
            # TargetLayers is a read-only property whose reflected map entries are mutable.
            assert all(a.get_editor_property('target_layers')[name].get_editor_property('layer_info_obj')==setting.get_editor_property('layer_info_obj') for name,setting in layers.items())
            # Run with the two process-local PackageRedirects from fix_benmore_firm_ground.ps1.
            # Those remap protected serialized weightmap references during load without editing shared layers.
            assert '+PackageRedirects=' in u.SystemLibrary.get_command_line()
            report['weightmap_references_remapped_on_load']=True
            # Rebuild serialized heightfield collision as well as the actor's default row.
            # Landscape's PostEditChange for collision_mip_level recreates its collision components.
            a.set_editor_property('collision_mip_level',a.get_editor_property('collision_mip_level'))
            report['changed_landscapes'].append(a.get_actor_label())
        if isinstance(a,u.GTTerrainBuilder):
            asset=a.get_editor_property('spec_asset')
            if asset:report['profile_assets'][a.get_actor_label()]=asset.get_path_name()
    assert len(report['changed_landscapes'])==1
    assert les.save_current_level();assert hashlib.sha256(oldfile.read_bytes()).hexdigest()==oldhash
    report.update(ok=True,surface=pm.get_path_name(),unprofiled_sinkage_rate=pm.get_editor_property('sinkage_rate'),profile_eligibility_cap_m=pm.get_editor_property('max_sinkage'),global_dirt_unchanged=True)
    p=OUT.parent/'placement-report.json';r=json.loads(p.read_text());r['saved_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();r['firm_ground_fix']='FerrariGroundContact/firm-ground-report.json';p.write_text(json.dumps(r,indent=2))
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'firm-ground-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
