"""Apply the reference-led hill surface and mid-distance scrub mosaic."""
import unreal as u,sys,json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreReferenceVistas';DEST='/Game/GrandTour/Demo/BenmoreRoads/ReferenceVistas';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import build
from benmore_bank_surface import backdrop_material
from benmore_environment_scene import terrain_trace
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem);eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
phase='load';last=time.monotonic();report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(err=None):
    global phase
    phase='done';report['ok']=err is None
    if err:report['error']=err;u.log_error(err)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='building';assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();eal.make_directory(DEST)
            backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeReferenceVistas'
            if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
            ground=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            for mat,name in [(ground,'M_BeforeReference_Ground'),(u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Environment/M_Benmore_Backdrop'),'M_BeforeReference_Backdrop')]:
                if not eal.does_asset_exist(DEST+'/'+name):assert eal.duplicate_asset(mat.get_path_name(),DEST+'/'+name)
            for name in ['T_Benmore_CoverStructure','T_Benmore_FineHillNormal']:
                t=u.AssetImportTask()
                for k,v in dict(filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True).items():t.set_editor_property(k,v)
                assets.import_asset_tasks([t]);tex=u.load_asset(DEST+'/'+name);assert tex
                for k,v in dict(srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True).items():tex.set_editor_property(k,v)
                eal.save_loaded_asset(tex)
            report['surface']=build(ground);assert not mel.recompile_material(ground);eal.save_loaded_asset(ground);backdrop_material()
            for a in act.get_all_level_actors():
                if a.get_actor_label()=='Benmore_Reference_ScrubMosaics':act.destroy_actor(a)
            group=act.spawn_actor_from_class(u.Actor,u.Vector());group.set_actor_label('Benmore_Reference_ScrubMosaics');group.set_actor_location(u.Vector(),False,True)
            data=json.loads((OUT/'placements.json').read_text());ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)]
            report['scrub']=[]
            for kind,suffix in enumerate(['Open','Dense']):
                mesh=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Character/SM_Benmore_Scrub_'+suffix);bounds=mesh.get_bounds();transforms=[]
                for row in data['shrubs']:
                    if row['kind']!=kind:continue
                    scale=row['height_m']/(bounds.box_extent.z*2/100);g=terrain_trace(world,ignore,row['x'],row['y']);z=g*100-(bounds.origin.z-bounds.box_extent.z)*scale-9
                    transforms.append(u.Transform(u.Vector(row['x']*100,row['y']*100,z),u.Rotator(yaw=row['yaw']),u.Vector(scale,scale,scale)))
                c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'BenmoreReferenceScrub','NoCollision',False);c.set_cull_distances(110000,175000)
                for k,v in dict(affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False).items():c.set_editor_property(k,v)
                report['scrub'].append({'mesh':mesh.get_path_name(),'count':len(transforms),'cull_m':[1100,1750]})
            report.update(clusters=len(data['clusters']),min_road_edge_clearance_m=data['min_road_edge_clearance_m'],height_changed=False,texture_size=data['texture_size'])
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>40:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
