"""Transfer approved gravel 04 into both existing tussock review maps."""
import unreal as u,json,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/GravelRoadUE';DEST='/Game/GrandTour/ArtTests/GravelRoad'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
report={'ok':False,'maps':[],'meshes':[]}
def import_asset(name,extension,mesh=False):
    task=u.AssetImportTask();task.filename=str(OUT/(name+extension));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
    if mesh:
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False;opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options=opt
    assets.import_asset_tasks([task]);result=eal.load_asset(DEST+'/'+name);assert result,name;return result
try:
    data=json.loads((OUT/'manifest.json').read_text());textures={}
    for name in data['textures']:
        tex=import_asset(name,'.png');normal=name.endswith('Normal');tex.set_editor_property('srgb',not normal)
        if normal:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',False)
        tex.set_editor_property('max_texture_size',2048);eal.save_loaded_asset(tex);textures[name]=tex
    mat=eal.load_asset(DEST+'/M_GR_Road') or assets.create_asset('M_GR_Road',DEST,u.Material,u.MaterialFactoryNew())
    from gravel_road_material import build
    build(mat,textures)
    pebble=eal.load_asset(DEST+'/M_GR_Stone') or assets.create_asset('M_GR_Stone',DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(pebble);c=mel.create_material_expression(pebble,u.MaterialExpressionVertexColor);assert mel.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.9),(u.MaterialProperty.MP_SPECULAR,.15)]:
        n=mel.create_material_expression(pebble,u.MaterialExpressionConstant);n.set_editor_property('r',value);mel.connect_material_property(n,'',prop)
    mel.set_base_material_usage(pebble,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True);mel.recompile_material(pebble);eal.save_loaded_asset(pebble)
    meshes={};sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for row in data['terrain']+data['models']:
        name=row['name'];mesh=import_asset(name,'.fbx',True);ground='replaces' in row;mesh.set_material(0,mat if ground else pebble)
        ns=mesh.get_editor_property('nanite_settings');ns.enabled=ground;sm.set_nanite_settings(mesh,ns,True)
        if ground:mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_loaded_asset(mesh);meshes[name]=mesh
        report['meshes'].append(dict(name=name,source_triangles=row['triangles'],nanite=ground))
    bounds=meshes['SM_GR_DryRoad'].get_bounds();assert 2599<bounds.box_extent.x*2<2601,'Road units incorrect'
    replace={row['replaces']:meshes[row['name']] for row in data['terrain']}
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
    for name in ['L_TussockStyle','L_TussockStyle_Overview']:
        path='/Game/GrandTour/ArtTests/TussockStyle/'+name;assert les.load_level(path)
        backup='/Game/GrandTour/ArtTests/GravelRoad/Before_'+name
        if not eal.does_asset_exist(backup):assert eal.duplicate_asset(path,backup)
        swapped=0;hidden=0
        for a in act.get_all_level_actors():
            if a.get_actor_label()=='GR_ApprovedGravel':act.destroy_actor(a);continue
            for c in a.get_components_by_class(u.StaticMeshComponent):
                mesh=c.get_editor_property('static_mesh')
                if not mesh:continue
                old_name=mesh.get_name()
                if old_name in replace:c.set_static_mesh(replace[old_name]);c.set_material(0,mat);swapped+=1
                elif old_name.startswith('SM_GR_') and old_name in meshes and not isinstance(c,u.InstancedStaticMeshComponent):c.set_static_mesh(meshes[old_name]);c.set_material(0,mat);swapped+=1
                elif old_name.startswith('SM_RF_RoadStone'):
                    c.set_visibility(False,True);c.set_hidden_in_game(True,True);c.set_cast_shadow(False);hidden+=1
        assert swapped==8,swapped
        group=act.spawn_actor_from_class(u.Actor,u.Vector(0,0,0));group.set_actor_label('GR_ApprovedGravel');count=0
        for row in data['models']:
            transforms=[]
            for p in data['placements']:
                if p['mesh']!=row['name']:continue
                x,y,z=p['location_m'];rx,ry,rz=p['rotation_deg'];sx,sy,sz=p['scale']
                transforms.append(u.Transform(u.Vector(x*100,-y*100,z*100),u.Rotator(roll=rx,pitch=-ry,yaw=-rz),u.Vector(sx,sy,sz)))
            c=u.GTVegetationSubsystem.add_tagged_instances(group,meshes[row['name']],transforms,'ApprovedGravel','NoCollision',True)
            c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('receives_decals',False);c.set_cull_distances(0,0)
            count+=c.get_instance_count()
        assert count==len(data['placements']);assert les.save_current_level()
        report['maps'].append(dict(path=path,replaced_terrain=swapped,hidden_old_stone_components=hidden,instances=count,backup=backup))
    report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (OUT/'import-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
