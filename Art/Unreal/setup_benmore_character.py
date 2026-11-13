import unreal as u,sys,json,time,traceback,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreCharacter';sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import build
from benmore_bank_surface import backdrop_material
from benmore_character_sky import build as skybuild
from benmore_environment_scene import terrain_trace
DEST='/Game/GrandTour/Demo/BenmoreRoads/Character';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools();act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
data=json.loads((OUT/'placements.json').read_text());report={'ok':False};phase='load';last=time.monotonic();u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def material(name,color,leaf=False):
    path=DEST+'/'+name;m=u.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(m)
    props(m,two_sided=leaf,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE if leaf else u.MaterialShadingModel.MSM_DEFAULT_LIT)
    col=props(mel.create_material_expression(m,u.MaterialExpressionConstant3Vector),constant=u.LinearColor(*color,1));mel.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
    if leaf:mel.connect_material_property(col,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
    for prop,val in [(u.MaterialProperty.MP_ROUGHNESS,.91),(u.MaterialProperty.MP_SPECULAR,.15)]:mel.connect_material_property(props(mel.create_material_expression(m,u.MaterialExpressionConstant),r=val),'',prop)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);assert not mel.recompile_material(m);eal.save_loaded_asset(m);return m
def finish(err=None):
    global phase
    phase='done';report['ok']=err is None
    if err:report['error']=err;u.log_error(err)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='working';assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();eal.make_directory(DEST)
            backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeCharacter'
            if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
            mat=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            for m,name in [(mat,'M_BeforeCharacter_Ground'),(u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Environment/M_Benmore_Backdrop'),'M_BeforeCharacter_Backdrop')]:
                if not eal.does_asset_exist(DEST+'/'+name):eal.duplicate_asset(m.get_path_name(),DEST+'/'+name)
            report['surface']=build(mat);assert not mel.recompile_material(mat);eal.save_loaded_asset(mat);backdrop_material()
            for a in act.get_all_level_actors():
                if a.get_actor_label().startswith('Benmore_Character_'):act.destroy_actor(a)
            report['sky']=skybuild()
            ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)]
            wood=material('M_Benmore_SilveredTimber',(.205,.18,.135));wire=material('M_Benmore_FenceWire',(.13,.14,.14));leaves=[material('M_Benmore_ScrubLeaf'+str(i),color,True) for i,color in enumerate([(.075,.083,.045),(.105,.112,.063),(.14,.137,.072),(.087,.096,.057)])]
            shrubgroup=act.spawn_actor_from_class(u.Actor,u.Vector(0,0,0));shrubgroup.set_actor_label('Benmore_Character_ShelteredScrub');shrubgroup.set_actor_location(u.Vector(0,0,0),False,True)
            report['scrub']=[]
            for kind,suffix in enumerate(['Open','Dense']):
                path=DEST+'/SM_Benmore_Scrub_'+suffix;mesh=u.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset('/Game/GrandTour/ArtTests/RoadFordStyle/SM_RF_Scrub_'+suffix,path);assert mesh
                for i in range(3,7):mesh.set_material(i,leaves[i-3])
                options=props(u.StaticMeshReductionOptions(),auto_compute_lod_screen_size=False,reduction_settings=[props(u.StaticMeshReductionSettings(),percent_triangles=p,screen_size=s) for p,s in [(1,1),(.4,.2),(.12,.06)]])
                assert sm.set_lods(mesh,options)==3;eal.save_loaded_asset(mesh);bounds=mesh.get_bounds();transforms=[]
                for row in data['shrubs']:
                    if row['kind']!=kind:continue
                    scale=row['height_m']/(bounds.box_extent.z*2/100);ground=terrain_trace(world,ignore,row['x'],row['y']);z=ground*100-(bounds.origin.z-bounds.box_extent.z)*scale-8
                    transforms.append(u.Transform(u.Vector(row['x']*100,row['y']*100,z),u.Rotator(yaw=row['yaw']),u.Vector(scale,scale,scale)))
                c=u.GTVegetationSubsystem.add_tagged_instances(shrubgroup,mesh,transforms,'BenmoreShelteredScrub','NoCollision',True);c.set_cull_distances(38000,65000);props(c,affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False)
                report['scrub'].append({'mesh':path,'count':len(transforms),'lods':3,'bounds':str(bounds)})
            posts=[];wires=[];clearances=[]
            for fence in data['fences']:
                prev=None
                for p in fence['points']:
                    if p is None:prev=None;continue
                    x,y,_,lean=p;z=terrain_trace(world,ignore,x,y);posts.append(u.Transform(u.Vector(x*100,y*100,z*100+48),u.Rotator(pitch=lean),u.Vector(.095,.095,1.2)))
                    if prev:
                        for height in [.30,.59,.89]:
                            a=u.Vector(prev[0]*100,prev[1]*100,(prev[2]+height)*100);b=u.Vector(x*100,y*100,(z+height)*100);d=b-a
                            wires.append(u.Transform((a+b)*.5,u.MathLibrary.make_rot_from_z(d),u.Vector(.004,.004,d.length()/100)))
                    prev=(x,y,z)
            group=act.spawn_actor_from_class(u.Actor,u.Vector(0,0,0));group.set_actor_label('Benmore_Character_StockFences');group.set_actor_location(u.Vector(0,0,0),False,True)
            for mesh,transforms,mat,name in [(u.load_asset('/Engine/BasicShapes/Cube'),posts,wood,'FencePosts'),(u.load_asset('/Engine/BasicShapes/Cylinder'),wires,wire,'FenceWires')]:
                c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,name,'NoCollision',name=='FencePosts');c.set_material(0,mat);c.set_cull_distances(65000,95000);props(c,affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False)
            report.update(fence_posts=len(posts),wire_spans=len(wires),clusters=len(data['clusters']),min_shrub_road_clearance_m=data['min_shrub_road_clearance_m'],height_changed=False)
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>25:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
