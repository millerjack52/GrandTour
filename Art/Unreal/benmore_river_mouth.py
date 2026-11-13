"""Replace the coarse backdrop only where the baked river enters the lake."""
import unreal as u,json,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreRivers';DEST='/Game/GrandTour/Demo/BenmoreRoads/Rivers'
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def apply_mouth(world):
    from benmore_river_material import build,lake_junction
    act=u.get_editor_subsystem(u.EditorActorSubsystem);eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
    assets=u.AssetToolsHelpers.get_asset_tools();sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    data=json.loads((OUT/'mouth-assets.json').read_text());assert data['bake_sha256']==hashlib.sha256((OUT/'river_bake.npz').read_bytes()).hexdigest()
    task=props(u.AssetImportTask(),filename=str(OUT/'T_Benmore_RiverMouth.png'),destination_path=DEST,destination_name='T_Benmore_RiverMouth',automated=True,replace_existing=True,save=True)
    assets.import_asset_tasks([task]);tex=u.load_asset(DEST+'/T_Benmore_RiverMouth');assert tex
    props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True);assert eal.save_loaded_asset(tex)
    banks=u.load_asset(DEST+'/T_Benmore_RiverBanks');water=build(u.load_asset(DEST+'/T_Benmore_RiverFlow'),banks);lake=lake_junction(banks)
    for a in act.get_all_level_actors():
        label=a.get_actor_label()
        if label=='Benmore_River_MouthBed':act.destroy_actor(a)
        elif label.startswith('Benmore_River_Surface_'):a.static_mesh_component.set_material(0,water)
        elif label=='Benmore_Vista_Lake':a.static_mesh_component.set_material(0,lake)
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    name=data['name'];task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
    mesh.set_material(0,u.load_asset(DEST+'/M_Benmore_RiverBank'));props(mesh.get_editor_property('body_setup'),collision_trace_flag=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;sm.set_nanite_settings(mesh,ns,True);assert eal.save_loaded_asset(mesh)
    a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*(v*100 for v in data['origin_m'])));a.set_actor_label('Benmore_River_MouthBed');a.static_mesh_component.set_static_mesh(mesh);a.static_mesh_component.set_collision_profile_name('BlockAll')
    props(a.static_mesh_component,cast_shadow=True,affect_distance_field_lighting=False,receives_decals=False)
    # The backdrop has no gameplay collision. Its river-local copy masks only
    # the precise DEM apron, avoiding a coarse triangle covering shallow water.
    name=DEST+'/M_Benmore_RiverBackdrop'
    m=u.load_asset(name) if eal.does_asset_exist(name) else eal.duplicate_asset('/Game/GrandTour/Demo/BenmoreRoads/Painterly/M_Painterly_Hills',name)
    for n in mel.get_material_expressions(m):
        if str(n.get_editor_property('desc'))=='RiverMouthCutout':mel.delete_material_expression(m,n)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    node=props(mel.create_material_expression(m,u.MaterialExpressionCustom),desc='RiverMouthCutout',inputs=[props(u.CustomInput(),input_name=n) for n in ['P','Mouth']],output_type=u.CustomMaterialOutputType.CMOT_FLOAT1,code='''
float2 uv=(P.xy*.01-float2(-1570,-20)+.5)/float2(1331,686);
float inside=step(0,uv.x)*step(0,uv.y)*step(uv.x,1)*step(uv.y,1);
return 1-step(.99,Texture2DSample(Mouth,MouthSampler,uv).r)*inside;
''')
    p=props(mel.create_material_expression(m,u.MaterialExpressionWorldPosition),desc='RiverMouthCutout')
    t=props(mel.create_material_expression(m,u.MaterialExpressionTextureObject),texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,desc='RiverMouthCutout')
    assert mel.connect_material_expressions(p,'',node,'P');assert mel.connect_material_expressions(t,'',node,'Mouth');mel.connect_material_property(node,'',u.MaterialProperty.MP_OPACITY_MASK)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    for a in act.get_all_level_actors():
        if a.get_actor_label().startswith('Benmore_Backdrop_'):a.static_mesh_component.set_material(0,m)
    return data

def check_mouth(world):
    act=u.get_editor_subsystem(u.EditorActorSubsystem);actors=act.get_all_level_actors()
    a=next(a for a in actors if a.get_actor_label()=='Benmore_River_MouthBed');mesh=a.static_mesh_component.get_editor_property('static_mesh');desc=mesh.get_static_mesh_description(0)
    data=json.loads((OUT/'mouth-assets.json').read_text());raw=json.loads((OUT/(data['name']+'.json')).read_text())['vertices'];coords=[];gaps=[]
    ignore=[v for v in actors if v!=a]
    for i in range(0,desc.get_vertex_count(),max(1,desc.get_vertex_count()//32)):
        p=desc.get_vertex_position(u.VertexID(i));coords.append(min(max(abs(p.x-v[0]*100),abs(p.y-v[1]*100),abs(p.z-v[2]*100)) for v in raw))
        pos=p+a.get_actor_location();hit=u.SystemLibrary.line_trace_single(world,pos+u.Vector(0,0,200),pos-u.Vector(0,0,200),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit is not None
        gaps.append(abs([v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z-pos.z)/100)
    assert max(coords)<.05 and max(gaps)<.01,(max(coords),max(gaps))
    report=dict(ok=True,triangles=data['triangles'],coordinate_max_error_cm=max(coords),collision_samples=len(gaps),max_collision_error_m=max(gaps),flow_changed=False)
    (OUT/'mouth-validation.json').write_text(json.dumps(report,indent=2));return report
