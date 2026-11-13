"""Install the overlook vegetation bands and terrain-fitted schist formations."""
import unreal as u,sys,time,json,traceback,array,math,shutil,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreComposition'
DEST='/Game/GrandTour/Demo/BenmoreRoads/Composition';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_environment_scene import terrain_trace
from benmore_painterly_surface import NOISE
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
data=json.loads((OUT/'placements.json').read_text());formations=json.loads((OUT/'outcrops.json').read_text())
grid=array.array('f');grid.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes())
phase='load';last=time.monotonic();report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)

def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o

def clone(path,name):return u.load_asset(DEST+'/'+name) if eal.does_asset_exist(DEST+'/'+name) else eal.duplicate_asset(path,DEST+'/'+name)
def wire(a,b,pin,out=''):assert mel.connect_material_expressions(a,out,b,pin)
def height(x,y):
    fx=(x+1250)/2500*2016;fy=(y+1250)/2500*2016;i=int(fx);j=int(fy);a=fx-i;b=fy-j;k=j*2017+i
    q,r,s,t=grid[k],grid[k+1],grid[k+2017],grid[k+2018]
    return q+(r-q)*a+(t-r)*b if a>=b else q+(t-s)*a+(s-q)*b

def material(name,foliage=False,color=None):
    m=u.load_asset(DEST+'/'+name) if eal.does_asset_exist(DEST+'/'+name) else assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m)
    props(m,two_sided=foliage,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE if foliage else u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for usage in [u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,u.MaterialUsage.MATUSAGE_NANITE]:mel.set_base_material_usage(m,usage,True)
    if foliage:
        node=props(mel.create_material_expression(m,u.MaterialExpressionConstant3Vector),constant=u.LinearColor(*color,1))
        mel.connect_material_property(node,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
    else:
        code=NOISE+'''
float dist=length(Camera-P)*.01;
float vein=f.n(float2((q.x*.72+q.y*.28)/2.8,(P.z*.01+q.x*.10+q.y*.065)/.22));
float fade=1-smoothstep(100,500,dist);
float tone=saturate(.40+VC.r*.40+(field-.5)*.22);
float3 rock=lerp(float3(.145,.164,.176),float3(.285,.272,.238),tone);
rock*=1+(smoothstep(.30,.72,vein)-.5)*.20*fade;
float3 soil=float3(.255,.206,.132)*lerp(.95,1.05,field);
return lerp(soil,rock,smoothstep(.05,.43,VC.g));
'''
        node=props(mel.create_material_expression(m,u.MaterialExpressionCustom),inputs=[props(u.CustomInput(),input_name=n) for n in ['P','Camera','VC']],code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
        for cls,pin in [(u.MaterialExpressionWorldPosition,'P'),(u.MaterialExpressionCameraPositionWS,'Camera'),(u.MaterialExpressionVertexColor,'VC')]:wire(mel.create_material_expression(m,cls),node,pin)
    mel.connect_material_property(node,'',u.MaterialProperty.MP_BASE_COLOR)
    for p,v in [(u.MaterialProperty.MP_ROUGHNESS,.95),(u.MaterialProperty.MP_SPECULAR,.10)]:
        mel.connect_material_property(props(mel.create_material_expression(m,u.MaterialExpressionConstant),r=v),'',p)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def fail():
    report['error']=traceback.format_exc();u.log_error(report['error']);(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='building';assert les.load_level(LEVEL);eal.make_directory(DEST)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeComposition'
            if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
            for name in ['High_Overlook','Hillside_Vista']:
                dst=OUT/('Before_'+name+'.png')
                if not dst.exists():shutil.copy2(ROOT/'Art/Export/BenmoreVistaStudy'/(name+'.png'),dst)
            assert hashlib.sha256((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes()).hexdigest()==data['height_sha256']==formations['height_sha256']
            ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)]
            errors=[];gaps=[]
            for part in formations['parts']:
                for x,y,z in part['support_samples_m']:
                    ground=terrain_trace(world,ignore,x,y);errors.append(abs(ground-height(x,y)));gaps.append(z-ground)
            assert max(errors)<.045 and max(gaps)<-.07,(max(errors),max(gaps))
            report['support_check']={'samples':len(gaps),'max_height_error_m':max(errors),'max_basal_gap_m':max(gaps)}
            task=props(u.AssetImportTask(),filename=str(OUT/'T_Benmore_CompositionZones.png'),destination_path=DEST,destination_name='T_Benmore_CompositionZones',automated=True,replace_existing=True,save=True)
            assets.import_asset_tasks([task]);tex=u.load_asset(DEST+'/T_Benmore_CompositionZones')
            props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True);assert eal.save_loaded_asset(tex)
            terrain=clone('/Game/GrandTour/Demo/BenmoreRoads/VistaStudy/M_VistaStudy_Terrain','M_Composition_Terrain');changed=0
            for n in mel.get_material_expressions(terrain):
                if isinstance(n,u.MaterialExpressionTextureObject):
                    t=n.get_editor_property('texture')
                    if t and t.get_name() in ['T_Benmore_GeographicZones','T_Benmore_CompositionZones']:n.set_editor_property('texture',tex);changed+=1
            assert changed==1;assert not mel.recompile_material(terrain);assert eal.save_loaded_asset(terrain)
            rock=material('M_Composition_Schist')
            leafcolors=[(.067,.092,.039),(.092,.116,.051),(.131,.143,.068),(.077,.101,.046)]
            leaves=[material('M_Composition_Sage'+str(i),True,c) for i,c in enumerate(leafcolors)]
            shrubs=[]
            for suffix in ['Open','Dense']:
                mesh=clone('/Game/GrandTour/Demo/BenmoreRoads/Character/SM_Benmore_Scrub_'+suffix,'SM_Composition_Scrub_'+suffix)
                for i in range(3,7):mesh.set_material(i,leaves[i-3])
                options=props(u.StaticMeshReductionOptions(),auto_compute_lod_screen_size=False,reduction_settings=[props(u.StaticMeshReductionSettings(),percent_triangles=p,screen_size=s) for p,s in [(1,1),(.60,.12),(.32,.035)]])
                assert sm.set_lods(mesh,options)==3;assert eal.save_loaded_asset(mesh);shrubs.append(mesh)
            u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0');rockmeshes=[]
            for part in formations['parts']:
                name=part['name'];task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
                opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
                props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
                task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
                mesh.set_material(0,rock);ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;sm.set_nanite_settings(mesh,ns,True)
                props(mesh.get_editor_property('body_setup'),collision_trace_flag=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                raw=json.loads((OUT/(name+'.json')).read_text())['vertices'];desc=mesh.get_static_mesh_description(0);coordinate_errors=[]
                for i in range(0,desc.get_vertex_count(),max(1,desc.get_vertex_count()//20)):
                    p=desc.get_vertex_position(u.VertexID(i))
                    coordinate_errors.append(min(max(abs(p.x-v[0]*100),abs(p.y-v[1]*100),abs(p.z-v[2]*100)) for v in raw))
                assert max(coordinate_errors)<.05,(name,max(coordinate_errors))
                assert eal.save_loaded_asset(mesh);rockmeshes.append(mesh)
            for a in act.get_all_level_actors():
                if a.get_actor_label().startswith('Benmore_Composition_'):act.destroy_actor(a)
                elif isinstance(a,u.LandscapeProxy):a.set_editor_property('landscape_material',terrain)
            for part,mesh in zip(formations['parts'],rockmeshes):
                a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label('Benmore_Composition_'+part['name'].replace('SM_Benmore_',''))
                a.set_actor_location(u.Vector(*(v*100 for v in part['origin_m'])),False,True);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(1,1,1))
                c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_collision_profile_name('BlockAll');props(c,cast_shadow=True,receives_decals=False)
            tussocks=[u.load_asset('/Game/GrandTour/ArtTests/TussockStyle/SM_TS_'+suffix) for suffix in ['Straw','Rust']];assert all(tussocks)
            grassmat=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Painterly/M_Painterly_Tussock')
            counts={}
            for category,meshes,cast,cull in [('shrubs',shrubs,True,(140000,210000)),('tussocks',tussocks,False,(52000,85000))]:
                count=0
                for ci in range(len(data['stems'])):
                    group=act.spawn_actor_from_class(u.Actor,u.Vector());group.set_actor_label('Benmore_Composition_'+category+'_'+str(ci).zfill(2));group.set_actor_location(u.Vector(),False,True)
                    for kind,mesh in enumerate(meshes):
                        b=mesh.get_bounds();transforms=[]
                        for row in data[category]:
                            if row['kind']!=kind or row['cluster']!=ci:continue
                            x,y=row['x'],row['y'];scale=row['height_m']/(b.box_extent.z*2/100)
                            z=height(x,y)*100-(b.origin.z-b.box_extent.z)*scale-12
                            transforms.append(u.Transform(u.Vector(x*100,y*100,z),u.Rotator(yaw=row['yaw']),u.Vector(scale,scale,scale)))
                        if not transforms:continue
                        c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'BenmoreComposition','NoCollision',cast);c.set_cull_distances(*cull)
                        props(c,affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False)
                        if category=='tussocks':c.set_material(0,grassmat)
                        count+=len(transforms)
                counts[category]=count
            assert counts=={'shrubs':len(data['shrubs']),'tussocks':len(data['tussocks'])}
            report.update(counts=counts,formations=len(rockmeshes),vegetation_bands=len(data['stems']),height_sha256=data['height_sha256'],height_changed=False,
                          min_rock_road_edge_clearance_m=formations['min_road_edge_clearance_m'],min_shrub_road_edge_clearance_m=data['min_shrub_road_edge_clearance_m'],original_assets_modified=False)
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>35:
            phase='saved';assert les.save_current_level();report['ok']=True;(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
            u.unregister_slate_post_tick_callback(handle)
            p=ROOT/'Art/Unreal/check_benmore_composition.py';exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
    except Exception:phase='error';fail()
handle=u.register_slate_post_tick_callback(tick)
