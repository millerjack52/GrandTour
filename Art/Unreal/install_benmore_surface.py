"""Install or verify finer render surfaces; assert river/terrain/physics preservation."""
import unreal as u
import sys,json,time,traceback,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as s
from benmore_water_surface import precombine,surface,DEST,MIDDLE
OUT=ROOT/'Art/Export/BenmoreGaea/WaterSurface_20261011'
VERIFY='-GTSurfaceVerify' in u.SystemLibrary.get_command_line()
report={'ok':False,'mode':'verify' if VERIFY else 'install','images':[],'performance_measured':False}
busy=False;rt=None;world=None;finishing_at=None
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():
    sheet=s.refs()['Benmore_RS_WaterDomain'];domain=sheet.get_editor_property('water_domain')
    return dict(instances=s.signature(),profiles=s.profiles(),queries=json.loads(json.dumps(s.queries())),
        domain=digest((ROOT/'Content'/domain.get_path_name().split('.')[0].removeprefix('/Game/')).with_suffix('.uasset')),
        drive=digest(ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap'),
        runtime={k:sheet.get_editor_property(k) for k in ['field_cell_cm','max_sim_cells','wind_ripple_cm','rain_drop_cm','dry_cut_cm']})
def load():
    global world,rt
    if rt:u.RenderingLibrary.release_render_target2d(rt)
    rt=None;world=None
    assert s.les.load_level('/Engine/Maps/Entry');assert s.les.load_level(s.LEVEL)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    rt=u.RenderingLibrary.create_render_target2d(world,1,1,u.TextureRenderTargetFormat.RTF_RGBA8)
def capture(label,count=1):
    refs=s.refs();sheet=refs['Benmore_RS_WaterDomain'];cam=refs['Benmore_RL_Camera_Ford'];p=s.crossings[0]['center_m']
    pos=u.Vector((p[0]+2)*100,(p[1]-1)*100,(s.height(s.after,p[0]+2,p[1]-1)+1.0)*100)
    target=u.Vector((p[0]-2)*100,(p[1]+3)*100,p[2]*100)
    cam.set_actor_location(pos,False,False);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False);cam.camera_component.set_field_of_view(65)
    sheet.preview_water_at(u.Vector2D(p[0]*100,p[1]*100),0,True)
    mats=[sheet.get_component_by_class(u.ProceduralMeshComponent).get_material(0)]+[a.static_mesh_component.get_material(0) for a in sheet.get_editor_property('domain_surfaces')]
    spray=refs['Benmore_RiffleSpray'].static_mesh_component.create_dynamic_material_instance(0)
    for i in range(count):
        clock=12+i*.125;sheet.preview_ambient_waves(clock)
        for m in mats:m.set_scalar_parameter_value('WaterTimeOverride',clock)
        spray.set_scalar_parameter_value('WaterTimeOverride',clock)
        if i==0:
            yield 25
            for _ in range(30):yield 0
        for _ in range(5):yield 0
        path=OUT/('%s_%02d.png'%(label,i));stamp=time.time()
        u.AutomationLibrary.take_high_res_screenshot(960,600,str(path),cam)
        while not path.exists() or path.stat().st_mtime<stamp:
            if time.time()-stamp>90:raise RuntimeError('Screenshot timeout')
            yield .1
        report['images'].append(str(path))
    if label=='After':
        for m in mats:m.set_scalar_parameter_value('FoamVisibility',0)
        for _ in range(8):yield 0
        path=OUT/'ShapeWithoutFoam.png';stamp=time.time();u.AutomationLibrary.take_high_res_screenshot(960,600,str(path),cam)
        while not path.exists() or path.stat().st_mtime<stamp:yield .1
        for m in mats:m.set_scalar_parameter_value('FoamVisibility',1)

def run():
    load();before=snapshot();report['before']=before
    if not VERIFY:
        backup='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeWaterSurface'
        if not s.eal.does_asset_exist(backup):assert s.eal.duplicate_asset(s.LEVEL,backup)
        report['backup']=backup
        if not (OUT/'Before_00.png').exists():yield from capture('Before')
        load();assert snapshot()==before
        pre=precombine();river=surface('River');surface('Lake');yield 2
        data=json.loads((OUT/'mesh-report.json').read_text());assert data['ok']
        u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
        report['meshes']=[]
        for row in data['surfaces']:
            comp=s.refs()[row['label']].static_mesh_component;old=comp.static_mesh.get_bounds()
            task=u.AssetImportTask();task.filename=str(OUT/(row['name']+'.fbx'));task.destination_path=DEST;task.destination_name=row['name'];task.automated=True;task.replace_existing=True;task.save=True
            opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
            task.options=opt
            # A material tuning rerun reuses the already installed render mesh.
            if comp.static_mesh.get_path_name()!=DEST+'/'+row['name']+'.'+row['name']:
                u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            mesh=u.load_asset(DEST+'/'+row['name']);assert mesh;new=mesh.get_bounds()
            errors=[abs(a-b) for a,b in zip(old.origin.to_tuple()+old.box_extent.to_tuple(),new.origin.to_tuple()+new.box_extent.to_tuple())]
            assert max(errors)<1,(row['label'],errors)
            mesh.set_material(0,river);assert s.eal.save_loaded_asset(mesh)
            comp.set_static_mesh(mesh);comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            report['meshes'].append(dict(**row,max_bounds_error_cm=max(errors)))
        sheet=s.refs()['Benmore_RS_WaterDomain'];sheet.set_editor_property('ambient_wave_material',pre);sheet.set_editor_property('surface_material_path',river.get_path_name())
        s.DEST=DEST;s.clean_saved_water();assert snapshot()==before
        assert u.EditorLoadingAndSavingUtils.save_map(world,s.LEVEL)
        load();s.verify_saved_water();assert snapshot()==before
        yield from capture('After',12)
        load()
    s.DEST=DEST;s.verify_saved_water()
    if VERIFY:
        yield from capture('Verified',12)
        load();s.verify_saved_water()
    report['after']=snapshot();assert report['after']==before
    for kind in ['River','Lake']:
        m=u.load_asset(DEST+'/M_GC_Domain'+kind)
        assert not u.MaterialEditingLibrary.recompile_material(m)
        assert m.get_editor_property('refraction_method')==u.RefractionMode.RM_2D_OFFSET
    report['cars']=[a.get_actor_label() for a in s.act.get_all_level_actors() if isinstance(a,u.GTCarPawn)]
    s.les.editor_request_begin_play();yield 8
    game=u.EditorLevelLibrary.get_game_world();assert game
    pc=u.GameplayStatics.get_player_controller(game,0);u.SystemLibrary.execute_console_command(game,'ShowFlag.Rendering 0',pc)
    sheet=next(a for a in u.GameplayStatics.get_all_actors_of_class(game,u.GTWaterSheet) if a.get_editor_property('water_domain'))
    mats=[sheet.get_component_by_class(u.ProceduralMeshComponent).get_material(0)]+[a.static_mesh_component.get_material(0) for a in sheet.get_editor_property('domain_surfaces')]
    a=[m.get_scalar_parameter_value('AmbientClock') for m in mats];start=u.GameplayStatics.get_time_seconds(game)
    while u.GameplayStatics.get_time_seconds(game)-start<1:yield .03
    b=[m.get_scalar_parameter_value('AmbientClock') for m in mats];assert all(y>x for x,y in zip(a,b));assert all(m.get_scalar_parameter_value('FoamVisibility')==1 for m in mats)
    report['clocks']=[a,b];report['middle_waves']=MIDDLE
    mats=[];sheet=None;game=None;pc=None;m=None
    u.EditorLevelLibrary.editor_end_play();yield 2;report['ok']=True

def tick(dt):
    global busy,next_at,gen,rt,world,finishing_at
    if busy:return
    if finishing_at is not None:
        if time.monotonic()>=finishing_at:
            u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        return
    busy=True
    try:
        if world and rt:u.RenderingLibrary.read_render_target_pixel(world,rt,0,0)
        if time.monotonic()-started>1500:raise RuntimeError('Surface installation timeout')
        if time.monotonic()<next_at:return
        next_at=time.monotonic()+next(gen)
    except (StopIteration,Exception) as e:
        if not isinstance(e,StopIteration):report['ok']=False;report['error']=traceback.format_exc();u.log_error(report['error'])
        (OUT/(report['mode']+'-report.json')).write_text(json.dumps(report,indent=2))
        if rt:u.RenderingLibrary.release_render_target2d(rt)
        rt=None;world=None;gen=None
        # Drain the heavy scene/render resources before shutting down D3D.
        # Immediate quit after the last offscreen capture could fault at exit.
        s.les.load_level('/Engine/Maps/Entry')
        finishing_at=time.monotonic()+3
    finally:busy=False
if __name__=='__main__':
    started=time.monotonic();next_at=started;gen=run();handle=u.register_slate_post_tick_callback(tick)
