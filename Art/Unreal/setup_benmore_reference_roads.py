"""Apply the user's road/photo references to the current Benmore map."""
import unreal as u,json,time,traceback,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreReferenceRoads';sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import DEST
from benmore_ground_detail import build
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools();les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive';phase='load';started=time.monotonic();last=started;report={'ok':False}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if time.monotonic()-started>600:raise RuntimeError('Reference road setup timeout')
        if phase=='load':
            phase='building';assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();eal.make_directory(DEST)
            m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover');assert m
            if not eal.does_asset_exist(DEST+'/M_Benmore_BeforeReferenceRoads'):assert eal.duplicate_asset(m.get_path_name(),DEST+'/M_Benmore_BeforeReferenceRoads')
            sources=[('T_Benmore_FineGravel','gravel_floor_04_diff_2k.jpg'),('T_Benmore_LooseGravel','gravel_floor_02_diff_2k.jpg'),('T_Benmore_FineGravelN','gravel_floor_04_nor_dx_2k.jpg'),('T_Benmore_LooseGravelN','gravel_floor_02_nor_dx_2k.jpg'),('T_Benmore_RoadCoordinates',None)]
            for name,file in sources:
                path=ROOT/'Art/Textures/RoadBenchmark'/file if file else OUT/(name+'.png')
                task=props(u.AssetImportTask(),filename=str(path),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True);assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
                if name.endswith('N'):props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_NORMALMAP,flip_green_channel=False)
                elif file is None:props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_BILINEAR,never_stream=True)
                eal.save_loaded_asset(t)
            report.update(build(m));errors=mel.recompile_material(m);assert not errors,str(errors);assert eal.save_loaded_asset(m)
            for a in act.get_all_level_actors():
                if a.get_actor_label()=='Benmore_ReferenceRoadAggregate':act.destroy_actor(a)
            group=act.spawn_actor_from_class(u.Actor,u.Vector());group.set_actor_label('Benmore_ReferenceRoadAggregate')
            data=json.loads((OUT/'surface-data.json').read_text());count=0
            for kind in range(1,5):
                mesh=u.load_asset('/Game/GrandTour/ArtTests/GravelRoad/SM_GR_Stone'+str(kind));assert mesh
                transforms=[u.Transform(u.Vector(*[v*100 for v in r['xyz']]),u.Rotator(yaw=r['yaw']),u.Vector(r['scale'],r['scale']*.8,r['scale']*.5)) for r in data['stones'] if r['kind']==kind]
                c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'BenmoreRoadAggregate','NoCollision',False);c.set_cull_distances(4500,7000);props(c,affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False);count+=c.get_instance_count()
            report['small_gravel_instances']=count;assert count==len(data['stones'])
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>30:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
