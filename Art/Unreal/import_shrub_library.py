"""Import the standalone shrub kit; does not load or modify a gameplay map."""
import unreal as u, json, traceback, sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/ShrubLibrary/v01'
DEST='/Game/GrandTour/Environment/Shrubs/v01'
eal=u.EditorAssetLibrary; assets=u.AssetToolsHelpers.get_asset_tools()
report={'ok':False,'destination':DEST,'meshes':[]}
try:
    data=json.loads((OUT/'manifest.json').read_text())
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    assert sm, 'Run through the full editor with -ExecutePythonScript; commandlets do not provide StaticMeshEditorSubsystem.'
    eal.make_directory(DEST)
    mat=eal.load_asset(DEST+'/M_SH_Foliage') or assets.create_asset('M_SH_Foliage',DEST,u.Material,u.MaterialFactoryNew())
    sys.path.insert(0,str(ROOT/'Art/Unreal'))
    from dense_tussock_material import configure
    configure(mat)
    for row in [r for r in data['models'] if r['lod']==0]:
        name=row['asset']; path=DEST+'/'+name
        task=u.AssetImportTask(); task.filename=str(OUT/(row['name']+'.fbx')); task.destination_path=DEST; task.destination_name=name
        task.automated=True; task.replace_existing=True; task.save=True
        opt=u.FbxImportUI(); opt.import_mesh=True; opt.import_as_skeletal=False; opt.import_materials=False; opt.import_textures=False; opt.import_animations=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.static_mesh_import_data.combine_meshes=True; opt.static_mesh_import_data.auto_generate_collision=False
        opt.static_mesh_import_data.generate_lightmap_u_vs=False; opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options=opt; assets.import_asset_tasks([task])
        mesh=eal.load_asset(path); assert mesh; mesh.set_material(0,mat)
        options=u.StaticMeshReductionOptions(); options.auto_compute_lod_screen_size=False; settings=[]
        for screen in [1,.18,.065]:
            setting=u.StaticMeshReductionSettings(); setting.percent_triangles=1.; setting.screen_size=screen; settings.append(setting)
        options.reduction_settings=settings; assert sm.set_lods(mesh,options)==3
        for lod in [1,2]:
            assert sm.import_lod(mesh,lod,str(OUT/(name+'_LOD'+str(lod)+'.fbx')))==lod
        assert sm.get_lod_count(mesh)==3; assert sm.set_lod_screen_sizes(mesh,[1,.18,.065])
        ns=mesh.get_editor_property('nanite_settings'); ns.enabled=False; sm.set_nanite_settings(mesh,ns,True)
        sm.remove_collisions(mesh)
        size=mesh.get_bounds().box_extent*2
        expected=row['size_m']; actual=[size.x/100,size.y/100,size.z/100]
        assert all(abs(a-b)<.025 for a,b in zip(sorted(actual),sorted(expected))), (name,actual,expected)
        assert mesh.get_num_sections(0)==1
        eal.save_loaded_asset(mesh)
        report['meshes'].append(dict(path=path,lods=sm.get_lod_count(mesh),size_m=actual,material=mesh.get_material(0).get_path_name(),collision='none',screens=list(sm.get_lod_screen_sizes(mesh))))
    report['ok']=len(report['meshes'])==12
except Exception:
    report['error']=traceback.format_exc(); u.log_error(report['error'])
finally:
    (OUT/'unreal-import-report.json').write_text(json.dumps(report,indent=2))
    u.log('SHRUB_IMPORT_RESULT '+json.dumps(report))
    u.SystemLibrary.quit_editor()
