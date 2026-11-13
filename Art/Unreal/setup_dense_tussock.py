"""Task-owned editor: authored LOD vs Nanite voxel vs PreserveArea, equal placement."""
import unreal as u, json, traceback, sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve(); OUT=ROOT/'Art/Export/DenseTussock'
DEST='/Game/GrandTour/ArtTests/DenseTussock'
eal=u.EditorAssetLibrary; mel=u.MaterialEditingLibrary
assets=u.AssetToolsHelpers.get_asset_tools()
report={'ok':False,'levels':[],'meshes':[]}
try:
    data=json.loads((OUT/'manifest.json').read_text())
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    assert sm,'Requires full editor, not PythonScript commandlet'
    les=u.get_editor_subsystem(u.LevelEditorSubsystem); act=u.get_editor_subsystem(u.EditorActorSubsystem)
    mat=eal.load_asset(DEST+'/M_DT_Foliage') or assets.create_asset('M_DT_Foliage',DEST,u.Material,u.MaterialFactoryNew())
    sys.path.insert(0,str(ROOT/'Art/Unreal'))
    from dense_tussock_material import configure
    configure(mat)
    def import_mesh(row,destination_name=None):
        name=destination_name or row['name']
        task=u.AssetImportTask(); task.filename=str(OUT/(row['name']+'.fbx')); task.destination_path=DEST; task.destination_name=name
        task.automated=True; task.replace_existing=True; task.save=True
        opt=u.FbxImportUI(); opt.import_mesh=True; opt.import_as_skeletal=False; opt.import_materials=False; opt.import_textures=False; opt.import_animations=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.static_mesh_import_data.combine_meshes=True; opt.static_mesh_import_data.auto_generate_collision=False
        opt.static_mesh_import_data.generate_lightmap_u_vs=False; opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options=opt; assets.import_asset_tasks([task])
        mesh=eal.load_asset(DEST+'/'+name); assert mesh
        mesh.set_material(0,mat)
        ns=mesh.get_editor_property('nanite_settings'); ns.enabled=False; sm.set_nanite_settings(mesh,ns,True)
        eal.save_loaded_asset(mesh); return mesh
    source={(row['kind'],row['lod']):import_mesh(row) for row in data['models']}
    modes={}
    for mode in ['LOD','Voxel','Preserve']:
        modes[mode]={}
        for kind in range(4):
            name='SM_DT_'+str(kind)+'_'+mode; path=DEST+'/'+name
            base_row=next(r for r in data['models'] if r['kind']==kind and r['lod']==0)
            mesh=import_mesh(base_row,name)
            assert mesh
            if mode=='LOD':
                options=u.StaticMeshReductionOptions(); options.auto_compute_lod_screen_size=False
                rows=[]
                for screen in [1,.08,.025]:
                    settings=u.StaticMeshReductionSettings(); settings.percent_triangles=1.; settings.screen_size=screen; rows.append(settings)
                options.reduction_settings=rows
                assert sm.set_lods(mesh,options)==3
                for lod in [1,2]:
                    row=next(r for r in data['models'] if r['kind']==kind and r['lod']==lod)
                    assert sm.import_lod(mesh,lod,str(OUT/(row['name']+'.fbx')))==lod
                assert sm.get_lod_count(mesh)==3
                assert sm.set_lod_screen_sizes(mesh,[1,.08,.025])
            ns=mesh.get_editor_property('nanite_settings'); ns.enabled=mode!='LOD'
            if mode!='LOD':
                ns.shape_preservation=u.NaniteShapePreservation.VOXELIZE if mode=='Voxel' else u.NaniteShapePreservation.PRESERVE_AREA
            sm.set_nanite_settings(mesh,ns,True); eal.save_loaded_asset(mesh)
            modes[mode][kind]=mesh
            report['meshes'].append(dict(mode=mode,kind=kind,path=path,lods=sm.get_lod_count(mesh),nanite=bool(mesh.get_editor_property('nanite_settings').enabled),shape=str(mesh.get_editor_property('nanite_settings').shape_preservation),screens=list(sm.get_lod_screen_sizes(mesh))))
    for mode in modes:
        assert les.load_level('/Game/GrandTour/ArtTests/RoadFordStyle/L_RoadFordStyle')
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/Engine.GameModeBase'))
        for actor in act.get_all_level_actors():
            for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
                mesh=c.get_editor_property('static_mesh')
                if mesh and ('GrassCarpet' in mesh.get_name() or 'Tussock' in mesh.get_name()): c.destroy_component(actor)
        group=act.spawn_actor_from_class(u.Actor,u.Vector(0,0,0)); group.set_actor_label('DT_DenseTussock')
        for kind,mesh in modes[mode].items():
            transforms=[]
            for p in data['placements']:
                if p['kind']!=kind: continue
                x,y,z=p['location_m']; rx,ry,rz=p['rotation_deg']; scale=p['scale']
                transforms.append(u.Transform(u.Vector(x*100,-y*100,z*100),u.Rotator(roll=rx,pitch=-ry,yaw=-rz),u.Vector(scale,scale,scale)))
            c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'DenseTussock','NoCollision',False)
            c.set_cull_distances(0,0)
            c.set_editor_property('affect_distance_field_lighting',False); c.set_editor_property('visible_in_ray_tracing',False); c.set_editor_property('receives_decals',False)
            assert c.get_instance_count()==len(transforms)
        for view,xyz,rot in [('Driver',(700,-32,215),u.Rotator(pitch=-2,yaw=-2)),('Overview',(900,2400,1200),u.Rotator(pitch=-11,yaw=-28))]:
            for actor in act.get_all_level_actors():
                if isinstance(actor,u.PlayerStart): actor.set_actor_location(u.Vector(*xyz),False,False); actor.set_actor_rotation(rot,False)
            camera=act.spawn_actor_from_class(u.CameraActor,u.Vector(*xyz),rot); camera.set_actor_label('DT_'+view); camera.camera_component.set_field_of_view(65)
            level=DEST+'/L_DT_'+mode+'_'+view
            assert u.EditorLoadingAndSavingUtils.save_map(world,level)
            report['levels'].append(dict(path=level,mode=mode,view=view,instances=len(data['placements'])))
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc(); u.log_error(report['error'])
finally:
    (OUT/'unreal-setup-report.json').write_text(json.dumps(report,indent=2))
    u.log('DENSE_SETUP_RESULT '+json.dumps(report)); u.SystemLibrary.quit_editor()
