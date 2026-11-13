"""Fit scenery beneath the outlet; keep the native Landscape unchanged."""
import unreal as u,json,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/RiverLife';sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_river_life_materials as mats
act=u.get_editor_subsystem(u.EditorActorSubsystem);eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools();props=mats.props;DEST=mats.DEST
report={'ok':False}
try:
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();data=json.loads((OUT/'outlet-assets.json').read_text())
    task=props(u.AssetImportTask(),filename=str(OUT/'T_RL_Mouth.png'),destination_path=DEST,destination_name='T_RL_Mouth',automated=True,replace_existing=True,save=True);assets.import_asset_tasks([task]);tex=u.load_asset(DEST+'/T_RL_Mouth');props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True);assert eal.save_loaded_asset(tex)
    hills=[a for a in act.get_all_level_actors() if a.get_actor_label().startswith('Benmore_Hills_')];assert hills
    report['hills']=[a.get_actor_label() for a in hills]
    def shore_graph(m,code,tag):
        marked=next((n for n in mel.get_material_expressions(m) if str(n.get_editor_property('desc')).startswith(tag+'Original|')),None)
        original=marked or mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK)
        output=str(marked.get_editor_property('desc')).split('|',1)[1] if marked else mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY_MASK)
        if original:original.set_editor_property('desc',tag+'Original|'+output)
        for n in list(mel.get_material_expressions(m)):
            if str(n.get_editor_property('desc'))==tag:mel.delete_material_expression(m,n)
        g=mats.Graph(m,tag);p=g.node(u.MaterialExpressionWorldPosition);uv=g.custom(['P'],'return (P.xy*.01-float2(-1580,-330)+.625)/float2(331.25,1131.25);',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(p,uv,'P');sample=g.tex(tex,uv)
        node=g.custom(['Old','M','UV'],'float inside=step(0,UV.x)*step(UV.x,1)*step(0,UV.y)*step(UV.y,1);'+code,u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(original or g.scalar(1),node,'Old',output if original else '');g.wire(sample,node,'M','RGBA');g.wire(uv,node,'UV');g.output(node,u.MaterialProperty.MP_OPACITY_MASK);props(m,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.5);assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    source=hills[0].static_mesh_component.get_material(0);path=DEST+'/M_RL_Hills';m=u.load_asset(path) or eal.duplicate_asset(source.get_path_name().split('.')[0],path)
    shore_graph(m,'return Old*(1-step(.5,M.r)*inside);','RL_MouthCut')
    for a in hills:a.static_mesh_component.set_material(0,m)
    for a in list(act.get_all_level_actors()):
        if a.get_actor_label() in ['Benmore_River_MouthBed','Benmore_RL_MouthBed']:act.destroy_actor(a)
    ground=u.load_asset(DEST+'/M_RL_MouthBed') or eal.duplicate_asset(DEST+'/M_RL_Terrain',DEST+'/M_RL_MouthBed')
    for n in list(mel.get_material_expressions(ground)):
        if isinstance(n,u.MaterialExpressionLandscapeGrassOutput):mel.delete_material_expression(ground,n)
    g=mats.Graph(ground,'RL_MouthGround');g.output(g.scalar(1),u.MaterialProperty.MP_OPACITY_MASK);assert not mel.recompile_material(ground);assert eal.save_loaded_asset(ground)
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0');name='SM_RL_MouthBed';task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH);props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS);task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);mesh.set_material(0,ground);props(mesh.get_editor_property('body_setup'),collision_trace_flag=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE);assert eal.save_loaded_asset(mesh)
    a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label('Benmore_RL_MouthBed');a.static_mesh_component.set_static_mesh(mesh);a.static_mesh_component.set_material(0,ground);a.static_mesh_component.set_collision_profile_name('BlockAll');props(a.static_mesh_component,cast_shadow=True,affect_distance_field_lighting=False)
    lake=mats.lake(u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/M_Gaea_Lake'),u.load_asset(DEST+'/T_RL_WaterMask'));shore_graph(lake,'return lerp(Old,M.g*(1-M.b),step(.5,M.r)*inside);','RL_MouthLake')
    next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_Vista_Lake').static_mesh_component.set_material(0,lake)
    assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview');report.update(ok=True,terrain_unchanged=True,scenery_bed_vertices=data['vertices'])
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'outlet-report.json').write_text(json.dumps(report,indent=2))
# Return to the bounded inspection session without launching another editor.
script=ROOT/'Art/Unreal/polish_benmore_river_life.py';exec(compile(script.read_text(),str(script),'exec'),{'__file__':str(script)})
