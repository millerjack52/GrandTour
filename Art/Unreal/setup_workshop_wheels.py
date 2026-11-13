"""Import only the isolated RR wheel library, material response and generated LODs."""
import unreal as u,json,shutil,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();SRC=ROOT/'Art/Export/WorkshopWheels-v01';DEST='/Game/GrandTour/UI/Workshop/Wheels'
OUT=ROOT/'Saved/WorkshopQA';OUT.mkdir(parents=True,exist_ok=True)
BACKUP=ROOT/'Saved/WorkshopBackups'/time.strftime('%Y%m%d-%H%M%S-wheel-assets')
A=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
report={'ok':False,'meshes':[]};manifest=json.loads((SRC/'manifest.json').read_text())
def backup(path):
    f=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    if f.exists():BACKUP.mkdir(parents=True,exist_ok=True);shutil.copy2(f,BACKUP/f.name)
def expr(mat,cls,**kw):
    o=M.create_material_expression(mat,cls)
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def wire(a,p,b,q):assert M.connect_material_expressions(a,p,b,q)
def material(name,color,metal,rough):
    path=DEST+'/M_'+name;backup(path)
    mat=A.load_asset(path) if A.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset('M_'+name,DEST,u.Material,u.MaterialFactoryNew())
    M.delete_all_material_expressions(mat)
    base=expr(mat,u.MaterialExpressionVectorParameter,parameter_name='BaseColour',default_value=u.LinearColor(*color,1))
    dirt=expr(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.105,.075,.038,1))
    coat=expr(mat,u.MaterialExpressionScalarParameter,parameter_name='Coat',default_value=0)
    lerp=expr(mat,u.MaterialExpressionLinearInterpolate);wire(base,'',lerp,'A');wire(dirt,'',lerp,'B');wire(coat,'',lerp,'Alpha')
    assert M.connect_material_property(lerp,'',u.MaterialProperty.MP_BASE_COLOR)
    met=expr(mat,u.MaterialExpressionConstant, r=metal);assert M.connect_material_property(met,'',u.MaterialProperty.MP_METALLIC)
    dry=expr(mat,u.MaterialExpressionConstant,r=rough);wetrough=expr(mat,u.MaterialExpressionConstant,r=max(.17,rough*.5));wet=expr(mat,u.MaterialExpressionScalarParameter,parameter_name='Wetness',default_value=0)
    rr=expr(mat,u.MaterialExpressionLinearInterpolate);wire(dry,'',rr,'A');wire(wetrough,'',rr,'B');wire(wet,'',rr,'Alpha');assert M.connect_material_property(rr,'',u.MaterialProperty.MP_ROUGHNESS)
    assert not M.recompile_material(mat);assert A.save_loaded_asset(mat);return mat
try:
    materials={
      'GT | limestone steel':material('RimLimestone',(.40,.38,.30),.65,.38),
      'GT | satin silver alloy':material('RimSilver',(.42,.45,.47),.8,.32),
      'GT | graphite steel':material('RimGraphite',(.055,.062,.066),.65,.42),
      'GT | dark hub':material('WheelHub',(.035,.043,.045),.35,.48),
      'GT | machined fasteners':material('WheelHardware',(.40,.43,.45),.8,.3),
      'GT | tyre charcoal':material('TyreRubber',(.018,.022,.025),0,.83),
      'GT | tread rubber':material('TyreTread',(.025,.030,.032),0,.87)}
    u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    for row in manifest['assets']:
        name=row['name'];backup(DEST+'/'+name)
        task=u.AssetImportTask();task.filename=str(SRC/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=False
        task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=A.load_asset(DEST+'/'+name);assert mesh,name
        slots=mesh.get_editor_property('static_materials');assert len(slots)==len(row['materials']),(name,len(slots))
        for i,key in enumerate(row['materials']):mesh.set_material(i,materials[key])
        opts=u.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=False
        settings=[]
        for fraction,screen in [(1.,1.),(.45,.35),(.16,.15),(.06,.06)]:
            s=u.StaticMeshReductionSettings();s.percent_triangles=fraction;s.screen_size=screen;settings.append(s)
        opts.reduction_settings=settings;assert SM.set_lods(mesh,opts)==4
        assert A.save_loaded_asset(mesh)
        bounds=mesh.get_bounds();extent=bounds.box_extent
        assert 20<extent.x<40 and 9<extent.y<13 and 20<extent.z<40,(name,str(extent))
        report['meshes'].append({'name':name,'extent_cm':[extent.x,extent.y,extent.z],'lods':SM.get_lod_count(mesh),'triangles':[mesh.get_num_triangles(lod) for lod in range(4)]})
    report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'wheelsetup.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
