"""Import the approved willow family and dress Benmore with trees and rocks."""
import unreal as u,json,time,traceback,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreScenery'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_rock_materials import configure as dry_rock
DEST='/Game/GrandTour/Demo/BenmoreRoads/Scenery';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem);sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
phase='load';started=time.monotonic();last=started;report={'ok':False,'trees':[],'rocks':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def expr(m,cls,**kw):return props(mel.create_material_expression(m,cls),**kw)
def wire(a,b,name,out=''):assert mel.connect_material_expressions(a,out,b,name)
def material(name):
    m=u.load_asset(DEST+'/'+name) if eal.does_asset_exist(DEST+'/'+name) else assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m);return m
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if time.monotonic()-started>900:raise RuntimeError('Scenery setup timeout')
        if phase=='load':
            phase='building';eal.make_directory(DEST)
            assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();assert world.get_path_name().startswith(LEVEL+'.')
            backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeScenery'
            if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
            task=props(u.AssetImportTask(),filename=str(ROOT/'Art/Textures/WillowBark/willow_bark_painted_v1.png'),destination_path=DEST,destination_name='T_Benmore_WillowBark',automated=True,replace_existing=True,save=True)
            assets.import_asset_tasks([task]);tex=u.load_asset(DEST+'/T_Benmore_WillowBark');assert tex
            bark=material('M_Benmore_WillowBark');vc=expr(bark,u.MaterialExpressionVertexColor);samples=[]
            for channel in [0,1]:
                uv=expr(bark,u.MaterialExpressionTextureCoordinate,coordinate_index=channel,u_tiling=1.,v_tiling=.5)
                t=expr(bark,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(uv,t,'UVs');samples.append(t)
            blend=expr(bark,u.MaterialExpressionLinearInterpolate);wire(samples[0],blend,'A','RGB');wire(samples[1],blend,'B','RGB');wire(vc,blend,'Alpha','R')
            tint=expr(bark,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.48,.46,.42,1));mult=expr(bark,u.MaterialExpressionMultiply);wire(blend,mult,'A');wire(tint,mult,'B');mel.connect_material_property(mult,'',u.MaterialProperty.MP_BASE_COLOR)
            for prop,val in [(u.MaterialProperty.MP_ROUGHNESS,.92),(u.MaterialProperty.MP_SPECULAR,.18)]:
                c=expr(bark,u.MaterialExpressionConstant,r=val);mel.connect_material_property(c,'',prop)
            assert not mel.recompile_material(bark);eal.save_loaded_asset(bark)
            u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
            data=json.loads((OUT/'willow-manifest.json').read_text());meshes={}
            for row in data['meshes']:
                task=props(u.AssetImportTask(),filename=str(OUT/(row['name']+'.fbx')),destination_path=DEST,destination_name=row['name'],automated=True,replace_existing=True,save=True)
                opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
                props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,one_convex_hull_per_ucx=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
                task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+row['name']);assert mesh
                for spec in row['materials']:
                    if spec['bark']:m=bark
                    else:
                        m=material('M_Benmore_'+row['variant']+'_'+str(spec['slot']));leaf=spec['slot']>=2
                        props(m,two_sided=leaf,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE if leaf else u.MaterialShadingModel.MSM_DEFAULT_LIT)
                        col=expr(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*spec['color'],1));mel.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
                        if leaf:mel.connect_material_property(col,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
                        for prop,val in [(u.MaterialProperty.MP_ROUGHNESS,.9),(u.MaterialProperty.MP_SPECULAR,.12)]:
                            c=expr(m,u.MaterialExpressionConstant,r=val);mel.connect_material_property(c,'',prop)
                        assert not mel.recompile_material(m);eal.save_loaded_asset(m)
                    mesh.set_material(spec['slot'],m)
                options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False
                options.reduction_settings=[props(u.StaticMeshReductionSettings(),percent_triangles=p,screen_size=s) for p,s in [(1,1),(.5,.18),(.22,.065),(.08,.02)]]
                assert sm.set_lods(mesh,options)==4
                ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;sm.set_nanite_settings(mesh,ns,True)
                hulls=len(mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('convex_elems'));assert hulls==3,(row['name'],hulls)
                eal.save_loaded_asset(mesh);meshes[row['variant']]=mesh
                bounds=mesh.get_bounds();dims=[bounds.box_extent.x*2/100,bounds.box_extent.y*2/100,bounds.box_extent.z*2/100]
                assert abs(dims[2]-row['dimensions_m'][2])<.1,(dims,row['dimensions_m'])
                report['trees'].append({'mesh':mesh.get_path_name(),'lods':sm.get_lod_count(mesh),'trunk_hulls':hulls,'dimensions_m':dims})
            rockmeshes={}
            for kind in [1,2,3]:
                source='/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/Rocks/Rocks_Moss/SM_Rock_'+str(kind).zfill(2)+'_Summer'
                path=DEST+'/SM_Benmore_Rock'+str(kind)
                rock=u.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset(source,path);assert rock
                body=rock.get_editor_property('body_setup');props(body,collision_trace_flag=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE);eal.save_loaded_asset(rock);rockmeshes[kind]=rock;dry_rock(rock,kind)
                report['rocks'].append({'mesh':path,'source':source})
            for a in act.get_all_level_actors():
                if a.get_actor_label().startswith('Benmore_Scenery_'):act.destroy_actor(a)
            placements=json.loads((OUT/'placements.json').read_text());counts={'trees':0,'rocks':0}
            for category in ['trees','rocks']:
                for i,row in enumerate(placements[category]):
                    mesh=meshes[row['variant']] if category=='trees' else rockmeshes[row['kind']]
                    x,y,z=row['xyz'];scale=row['scale'];bounds=mesh.get_bounds()
                    radius=max(bounds.box_extent.x,bounds.box_extent.y)/100*scale
                    assert row['road_clearance_m']>radius+3,('Road clearance',category,i,radius)
                    if category=='rocks':z-=(bounds.origin.z-bounds.box_extent.z)/100*scale+.15*scale
                    a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x*100,y*100,z*100),u.Rotator(yaw=row['yaw']));a.set_actor_label('Benmore_Scenery_'+category+'_'+str(i).zfill(3))
                    a.set_actor_scale3d(u.Vector(scale,scale,scale));c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_collision_profile_name('BlockAll')
                    props(c,cast_shadow=True,receives_decals=False);counts[category]+=1
            report['placed']=counts;report['road_clearance_validated']=True
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>30:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
