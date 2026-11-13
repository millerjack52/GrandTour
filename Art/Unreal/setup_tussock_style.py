"""Bring approved Blender study 07 into a separate complete ford style map."""
import unreal as u, json, traceback, sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve(); OUT=ROOT/'Art/Export/TussockStyle'
DEST='/Game/GrandTour/ArtTests/TussockStyle'
eal=u.EditorAssetLibrary; mel=u.MaterialEditingLibrary; assets=u.AssetToolsHelpers.get_asset_tools()
report={'ok':False,'meshes':[],'levels':[]}
try:
    data=json.loads((OUT/'manifest.json').read_text())
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem); assert sm
    les=u.get_editor_subsystem(u.LevelEditorSubsystem); act=u.get_editor_subsystem(u.EditorActorSubsystem)
    mat=eal.load_asset(DEST+'/M_TS_Grass') or assets.create_asset('M_TS_Grass',DEST,u.Material,u.MaterialFactoryNew())
    sys.path.insert(0,str(ROOT/'Art/Unreal'))
    from dense_tussock_material import configure
    configure(mat)
    meshes={}
    for kind in range(4):
        row=next(r for r in data['models'] if r['kind']==kind and r['lod']==0)
        name=row['name'].replace('_LOD0',''); path=DEST+'/'+name
        task=u.AssetImportTask(); task.filename=str(OUT/(row['name']+'.fbx')); task.destination_path=DEST; task.destination_name=name
        task.automated=True; task.replace_existing=True; task.save=True
        opt=u.FbxImportUI(); opt.import_mesh=True; opt.import_as_skeletal=False; opt.import_materials=False; opt.import_textures=False; opt.import_animations=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.static_mesh_import_data.combine_meshes=True; opt.static_mesh_import_data.auto_generate_collision=False
        opt.static_mesh_import_data.generate_lightmap_u_vs=False; opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options=opt; assets.import_asset_tasks([task])
        mesh=eal.load_asset(path); assert mesh; mesh.set_material(0,mat)
        options=u.StaticMeshReductionOptions(); options.auto_compute_lod_screen_size=False; rows=[]
        for screen in [1,.08,.025]:
            settings=u.StaticMeshReductionSettings(); settings.percent_triangles=1.; settings.screen_size=screen; rows.append(settings)
        options.reduction_settings=rows; assert sm.set_lods(mesh,options)==3
        for lod in [1,2]:
            row=next(r for r in data['models'] if r['kind']==kind and r['lod']==lod)
            assert sm.import_lod(mesh,lod,str(OUT/(row['name']+'.fbx')))==lod
        assert sm.get_lod_count(mesh)==3
        assert sm.set_lod_screen_sizes(mesh,[1,.08,.025])
        ns=mesh.get_editor_property('nanite_settings'); ns.enabled=False; sm.set_nanite_settings(mesh,ns,True)
        eal.save_loaded_asset(mesh); meshes[kind]=mesh
        report['meshes'].append(dict(path=path,lods=sm.get_lod_count(mesh),screens=list(sm.get_lod_screen_sizes(mesh)),material=mesh.get_material(0).get_path_name()))
    assert les.load_level('/Game/GrandTour/ArtTests/DenseTussock/L_DT_LOD_Driver')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    for actor in act.get_all_level_actors():
        if actor.get_actor_label()=='DT_DenseTussock':act.destroy_actor(actor)
    group=act.spawn_actor_from_class(u.Actor,u.Vector(0,0,0)); group.set_actor_label('TS_ApprovedTussock')
    for kind,mesh in meshes.items():
        transforms=[]
        for p in data['placements']:
            if p['kind']!=kind:continue
            x,y,z=p['location_m']; rx,ry,rz=p['rotation_deg']; scale=p['scale']
            transforms.append(u.Transform(u.Vector(x*100,-y*100,z*100),u.Rotator(roll=rx,pitch=-ry,yaw=-rz),u.Vector(scale,scale,scale)))
        c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'TussockStyle','NoCollision',False)
        c.set_cull_distances(0,0); c.set_editor_property('affect_distance_field_lighting',False)
        c.set_editor_property('visible_in_ray_tracing',False); c.set_editor_property('receives_decals',False)
        assert c.get_instance_count()==len(transforms)
    for actor in act.get_all_level_actors():
        if isinstance(actor,u.CameraActor) and actor.get_actor_label()=='DT_Driver':actor.set_actor_label('TS_Driver')
    camera=act.spawn_actor_from_class(u.CameraActor,u.Vector(900,2400,1200),u.Rotator(pitch=-11,yaw=-28))
    camera.set_actor_label('TS_Overview'); camera.camera_component.set_field_of_view(65)
    from tussock_style_lighting import configure as configure_lighting
    configure_lighting(world)
    for name,pos,rot in [('L_TussockStyle',(700,-32,215),u.Rotator(pitch=-2,yaw=-2)),('L_TussockStyle_Overview',(900,2400,1200),u.Rotator(pitch=-11,yaw=-28))]:
        for actor in act.get_all_level_actors():
            if isinstance(actor,u.PlayerStart):actor.set_actor_location(u.Vector(*pos),False,False); actor.set_actor_rotation(rot,False)
        assert u.EditorLoadingAndSavingUtils.save_map(world,DEST+'/'+name)
        report['levels'].append(DEST+'/'+name)
    report['instances']=len(data['placements']); report['ok']=True
except Exception:
    report['error']=traceback.format_exc(); u.log_error(report['error'])
finally:
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
    u.log('TUSSOCK_STYLE_SETUP_RESULT '+json.dumps(report)); u.SystemLibrary.quit_editor()
