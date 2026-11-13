"""Import approved mud study into both existing style maps, with backups."""
import unreal as u,json,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudStyleUE';DEST='/Game/GrandTour/ArtTests/MudStyle'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools();report={'ok':False,'maps':[],'meshes':[]}
def import_asset(name,extension,mesh=False):
    task=u.AssetImportTask();task.filename=str(OUT/(name+extension));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
    if mesh:
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False;opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options=opt
    assets.import_asset_tasks([task]);result=eal.load_asset(DEST+'/'+name);assert result,name;return result
def simple(name,color=None,rough=.9,spec=.15):
    m=eal.load_asset(DEST+'/'+name) or assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(m)
    if color is None:n=mel.create_material_expression(m,u.MaterialExpressionVertexColor)
    else:
        n=mel.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*color,1))
    assert mel.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,rough),(u.MaterialProperty.MP_SPECULAR,spec)]:
        n=mel.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',value);mel.connect_material_property(n,'',prop)
    mel.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True);mel.recompile_material(m);eal.save_loaded_asset(m);return m
try:
    data=json.loads((OUT/'manifest.json').read_text());textures={}
    for name in data['textures']:
        tex=import_asset(name,'.png');normal=name.endswith('Normal');tex.set_editor_property('srgb',not normal)
        if normal:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',False)
        tex.set_editor_property('max_texture_size',2048);eal.save_loaded_asset(tex);textures[name]=tex
    # Rebuild from the approved gravel graph on reruns rather than appending duplicate nodes.
    from gravel_road_material import build as gravel_build
    mat=eal.load_asset(DEST+'/M_MS_Ground') or assets.create_asset('M_MS_Ground',DEST,u.Material,u.MaterialFactoryNew())
    gravel_build(mat,{name:eal.load_asset('/Game/GrandTour/ArtTests/GravelRoad/'+name) for name in ['T_GR_LooseColor','T_GR_LooseNormal','T_GR_CompactColor','T_GR_CompactNormal']})
    from mud_style_material import build
    build(mat,textures);detail=simple('M_MS_Clods');water=simple('M_MS_ShallowWater',(.042,.055,.058),.22,.255)
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);meshes={}
    for row in data['terrain']+data['models']:
        name=row['name'];mesh=import_asset(name,'.fbx',True);ground='replaces' in row;mesh.set_material(0,mat if ground else water if row['pool'] else detail)
        ns=mesh.get_editor_property('nanite_settings');ns.enabled=ground;sm.set_nanite_settings(mesh,ns,True)
        if ground:mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_loaded_asset(mesh);meshes[name]=mesh;report['meshes'].append(dict(name=name,triangles=row['triangles'],nanite=ground))
    assert 2599<meshes['SM_MS_DryRoad'].get_bounds().box_extent.x*2<2601,'Units wrong'
    for row in data['placements']:
        if row['mesh'] not in meshes:meshes[row['mesh']]=eal.load_asset('/Game/GrandTour/ArtTests/GravelRoad/'+row['mesh']);assert meshes[row['mesh']]
    replace={row['replaces']:meshes[row['name']] for row in data['terrain']};les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
    for name in ['L_TussockStyle','L_TussockStyle_Overview']:
        path='/Game/GrandTour/ArtTests/TussockStyle/'+name;assert les.load_level(path);backup=DEST+'/Before_'+name
        if not eal.does_asset_exist(backup):assert eal.duplicate_asset(path,backup)
        swapped=0
        for actor in act.get_all_level_actors():
            if actor.get_actor_label() in ['GR_ApprovedGravel','MS_ApprovedMud']:act.destroy_actor(actor);continue
            for c in actor.get_components_by_class(u.StaticMeshComponent):
                mesh=c.get_editor_property('static_mesh')
                if not mesh:continue
                n=mesh.get_name()
                if n in replace or n in [r['name'] for r in data['terrain']]:c.set_static_mesh(replace.get(n,meshes.get(n)));c.set_material(0,mat);swapped+=1
        assert swapped==8,swapped
        group=act.spawn_actor_from_class(u.Actor,u.Vector(0,0,0));group.set_actor_label('MS_ApprovedMud');group.root_component.set_mobility(u.ComponentMobility.STATIC);count=0
        for name in sorted(set(p['mesh'] for p in data['placements'])):
            transforms=[]
            for p in data['placements']:
                if p['mesh']!=name:continue
                x,y,z=p['location_m'];rx,ry,rz=p['rotation_deg'];sx,sy,sz=p['scale'];transforms.append(u.Transform(u.Vector(x*100,-y*100,z*100),u.Rotator(roll=rx,pitch=-ry,yaw=-rz),u.Vector(sx,sy,sz)))
            c=u.GTVegetationSubsystem.add_tagged_instances(group,meshes[name],transforms,'ApprovedMud','NoCollision',not name.startswith('SM_MS_Pool'))
            c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('receives_decals',False);c.set_cull_distances(0,0);count+=c.get_instance_count()
        assert count==len(data['placements'])
        # Close-up at the approved Blender camera position, converted to Unreal axes.
        camera=next((a for a in act.get_all_level_actors() if a.get_actor_label()=='MS_SurfaceDetail'),None)
        if camera is None:camera=act.spawn_actor_from_class(u.CameraActor,u.Vector(1100,230,340))
        camera.set_actor_label('MS_SurfaceDetail');camera.set_actor_location(u.Vector(1100,230,340),False,False)
        camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(1400,-40,72)),False);camera.camera_component.set_field_of_view(41.1)
        assert les.save_current_level();report['maps'].append(dict(path=path,backup=backup,terrain=swapped,instances=count))
    report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
finally:(OUT/'import-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
