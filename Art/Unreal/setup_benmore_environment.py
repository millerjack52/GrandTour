"""Import physical verge relief, re-seat dressing, and preserve the drive map."""
import unreal as u,json,time,traceback,array,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreEnvironment';DEST='/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface'
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive';les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem);eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_environment_scene import setup_background,ground_large_rocks,ground_aggregate
from benmore_reference_surface import build
data=json.loads((OUT/'height-report.json').read_text());old=array.array('f');old.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes());new=array.array('f');new.frombytes((OUT/'height_local_south_up.f32').read_bytes())
phase='load';last=time.monotonic();report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def height(grid,x,y):
    f=(x+1250)/2500*2016;g=(y+1250)/2500*2016
    if not (0<=f<2016 and 0<=g<2016):return 0
    i=int(f);j=int(g);a=f-i;b=g-j;k=j*2017+i
    return (grid[k]*(1-a)+grid[k+1]*a)*(1-b)+(grid[k+2017]*(1-a)+grid[k+2018]*a)*b
def change(p):return (height(new,p.x/100,p.y/100)-height(old,p.x/100,p.y/100))*100
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,land,rt,transfer
    now=time.monotonic()
    try:
        if phase=='load':
            phase='building';assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeEnvironment'
            if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
            m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            if not eal.does_asset_exist(DEST+'/M_Benmore_BeforeEnvironment'):eal.duplicate_asset(m.get_path_name(),DEST+'/M_Benmore_BeforeEnvironment')
            report['surface']=build(m);assert not mel.recompile_material(m);eal.save_loaded_asset(m)
            report['backdrop']=setup_background(world)
            land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape))
            task=props(u.AssetImportTask(),filename=str(OUT/'T_Benmore_RoadReliefRG.png'),destination_path=DEST,destination_name='T_Benmore_RoadReliefRG',automated=True,replace_existing=True,save=True)
            assets=u.AssetToolsHelpers.get_asset_tools();assets.import_asset_tasks([task]);tex=u.load_asset(DEST+'/T_Benmore_RoadReliefRG');assert tex
            props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_NEAREST,never_stream=True);eal.save_loaded_asset(tex)
            transfer=u.load_asset(DEST+'/M_Benmore_RoadReliefTransfer') if eal.does_asset_exist(DEST+'/M_Benmore_RoadReliefTransfer') else assets.create_asset('M_Benmore_RoadReliefTransfer',DEST,u.Material,u.MaterialFactoryNew())
            mel.delete_all_material_expressions(transfer);transfer.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
            node=props(mel.create_material_expression(transfer,u.MaterialExpressionTextureSample),texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            mel.connect_material_property(node,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR);assert not mel.recompile_material(transfer);eal.save_loaded_asset(transfer)
            rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8);phase='warm';last=time.monotonic()
        elif phase=='warm' and now-last>25:
            phase='drawing';u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);phase='import';last=now
        elif phase=='import' and now-last>8:
            phase='importing';u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer)
            for a in data['anchors']:
                c=u.RenderingLibrary.read_render_target_pixel(world,rt,*a['pixel']);z=(((int(c.r)<<8)|int(c.g))-32768)/64;assert abs(z-a['z_m'])<.001,(a,z,str(c))
            assert land.landscape_import_heightmap_from_render_target(rt,True,0);phase='settle';last=now
        elif phase=='settle' and now-last>20:
            phase='projecting';moved=0;actors_moved=0
            for a in act.get_all_level_actors():
                if not a.get_actor_label().startswith('Benmore_'):continue
                for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                    if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
                    for i in range(c.get_instance_count()):
                        t=c.get_instance_transform(i,True);p=t.translation;dz=change(p)
                        if abs(dz)>.01:
                            t.translation=u.Vector(p.x,p.y,p.z+dz);assert c.update_instance_transform(i,t,True,False,True);moved+=1
                    c.mark_render_state_dirty() if hasattr(c,'mark_render_state_dirty') else None
                    # Final update marks the instance buffer for upload.
                    if c.get_instance_count():
                        i=c.get_instance_count()-1;c.update_instance_transform(i,c.get_instance_transform(i,True),True,True,True)
                if a.get_actor_label().startswith('Benmore_Scenery_'):
                    p=a.get_actor_location();dz=change(p)
                    if abs(dz)>.01:a.set_actor_location(u.Vector(p.x,p.y,p.z+dz),False,False);actors_moved+=1
            report.update(instances_reseated=moved,scenery_reseated=actors_moved,height=data)
            report['rocks']=ground_large_rocks(world)
            report['aggregate']=ground_aggregate(world)
            assert land.landscape_export_heightmap_to_render_target(rt,True,True);phase='verify';last=now
        elif phase=='verify' and now-last>8:
            phase='verifying';assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            errors=[]
            for a in data['anchors']:
                c=u.RenderingLibrary.read_render_target_pixel(world,rt,*a['pixel']);z=(((int(c.r)<<8)|int(c.g))-32768)/64;errors.append(abs(z-a['z_m']))
            assert max(errors)<.001;report['height_import_max_error_m']=max(errors)
            assert les.save_current_level()
            # Commit the canonical authoring grid only after the edited map saves.
            (ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').write_bytes((OUT/'height_local_south_up.f32').read_bytes())
            finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
