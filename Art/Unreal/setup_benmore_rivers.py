"""Install the baked reach without rebuilding roads or changing terrain height."""
import unreal as u,sys,time,json,traceback,array,math,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreRivers';DEST='/Game/GrandTour/Demo/BenmoreRoads/Rivers';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_material import build,terrain_material,lake_junction,bank_material
from benmore_environment_scene import terrain_trace
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);eal=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
data=json.loads((OUT/'assets.json').read_text());bake=json.loads((OUT/'bake-report.json').read_text());assert bake['ok']
grid=array.array('f');grid.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes())
phase='load';last=time.monotonic();started=last;report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def height(x,y):
    fx=(x+1250)/2500*2016;fy=(y+1250)/2500*2016;i=int(fx);j=int(fy);a=fx-i;b=fy-j;k=j*2017+i
    q,r,s,t=grid[k],grid[k+1],grid[k+2017],grid[k+2018]
    return q+(r-q)*a+(t-r)*b if a>=b else q+(t-s)*a+(s-q)*b
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle)
    if error:u.SystemLibrary.quit_editor()
    else:
        p=ROOT/'Art/Unreal/check_benmore_rivers.py';exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
def texture(name):
    task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True)
    assert eal.save_loaded_asset(t);return t
def tick(dt):
    global phase,last,bank_art_report
    try:
        if time.monotonic()-started>600:raise RuntimeError('River setup timeout')
        if phase=='load':
            phase='building';assert les.load_level(LEVEL);eal.make_directory(DEST)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeRivers'
            if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
            assert hashlib.sha256((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes()).hexdigest()==bake['height_sha256']
            # Actual collision surface must agree with the input to the solve.
            ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)];errors=[]
            for x,y,z,surface in data['support_samples_m'][::3]:errors.append(abs(terrain_trace(world,ignore,x,y)-z))
            assert errors and max(errors)<.045,('River/terrain mismatch',max(errors))
            report['terrain_support']={'samples':len(errors),'max_error_m':max(errors)}
            flow=texture('T_Benmore_RiverFlow');banks=texture('T_Benmore_RiverBanks');veg=texture('T_Benmore_VegetationMask')
            water=build(flow,banks);terrain=terrain_material(banks,veg);lake=lake_junction(banks);bankmat=bank_material(banks)
            u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
            for a in act.get_all_level_actors():
                if a.get_actor_label().startswith('Benmore_River_'):act.destroy_actor(a)
            for part in data['parts']+data['bank_parts']:
                is_bank='RiverBank' in part['name'];mat=bankmat if is_bank else water
                name=part['name'];task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
                opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
                props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
                task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh;mesh.set_material(0,mat)
                if is_bank:props(mesh.get_editor_property('body_setup'),collision_trace_flag=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;sm.set_nanite_settings(mesh,ns,True);assert eal.save_loaded_asset(mesh)
                a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(('Benmore_River_Bank_' if is_bank else 'Benmore_River_Surface_')+name[-2:]);a.set_actor_location(u.Vector(*(v*100 for v in part['origin_m'])),False,True)
                c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_material(0,mat);c.set_collision_profile_name('BlockAll' if is_bank else 'NoCollision');a.set_actor_enable_collision(is_bank)
                props(c,cast_shadow=is_bank,affect_distance_field_lighting=False,receives_decals=False)
            # Read bank mask CPU data from the numeric export (not texture readback).
            raw=array.array('f');raw.frombytes((OUT/'bank_distance.f32').read_bytes());nx=1331;ny=686
            fill=array.array('f');fill.frombytes((OUT/'bank_surface.f32').read_bytes())
            def shore(x,y):
                i=round(x+1570);j=round(y+20)
                return raw[j*nx+i] if 0<=i<nx and 0<=j<ny else 100.
            def bank_ground(x,y):
                fx=x+1570;fy=y+20;i=int(fx);j=int(fy);a=fx-i;b=fy-j;k=j*nx+i
                q,r,s,t=fill[k],fill[k+1],fill[k+nx],fill[k+nx+1]
                surface=q+(r-q)*a+(t-r)*b if a>=b else q+(t-s)*a+(s-q)*b
                return max(height(x,y),surface)
            removed={}
            for a in act.get_all_level_actors():
                if isinstance(a,u.LandscapeProxy):a.set_editor_property('landscape_material',terrain);continue
                # Only authored foliage groups are river-cleared; no roads,
                # rocks, fences, vehicle components or unrelated asset edits.
                label=a.get_actor_label()
                if label=='Benmore_Vista_Lake':a.static_mesh_component.set_material(0,lake)
                if not any(s in label for s in ['Scrub','scrub','tussock','Willow','willow']):continue
                count=0
                for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                    ids=[]
                    for i in range(c.get_instance_count()):
                        tr=c.get_instance_transform(i,True);p=tr.translation
                        if shore(p.x/100,p.y/100)<7.0:ids.append(i)
                    for i in reversed(ids):assert c.remove_instance(i)
                    count+=len(ids)
                if count:removed[label]=count
            report['river_local_foliage_removed']=removed
            stone_group=act.spawn_actor_from_class(u.Actor,u.Vector());stone_group.set_actor_label('Benmore_River_GravelBars');support_gaps=[]
            for kind in range(1,5):
                mesh=u.load_asset('/Game/GrandTour/ArtTests/GravelRoad/SM_GR_Stone'+str(kind));bounds=mesh.get_bounds();desc=mesh.get_static_mesh_description(0)
                points=[desc.get_vertex_position(u.VertexID(i)) for i in range(desc.get_vertex_count())];cut=bounds.origin.z-bounds.box_extent.z+bounds.box_extent.z*.65
                base=[p for p in points if p.z<=cut];assert base
                transforms=[]
                for row in data['stones']:
                    if row['kind']!=kind:continue
                    scale=row['size_m']*100/max(bounds.box_extent.x,bounds.box_extent.y)/2;angle=math.radians(row['yaw']);cs=math.cos(angle);sn=math.sin(angle)
                    constraints=[]
                    for p in base:
                        x=row['x']+(p.x*cs-p.y*sn)*scale/100;y=row['y']+(p.x*sn+p.y*cs)*scale/100
                        constraints.append(bank_ground(x,y)-p.z*scale/100)
                    z=min(constraints)-.045;support_gaps.append(max(z-v for v in constraints))
                    transforms.append(u.Transform(u.Vector(row['x']*100,row['y']*100,z*100),u.Rotator(yaw=row['yaw']),u.Vector(scale,scale,scale)))
                c=u.GTVegetationSubsystem.add_tagged_instances(stone_group,mesh,transforms,'BenmoreRiver','NoCollision',False)
                c.set_material(0,u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/M_Benmore_VergeStone'));c.set_cull_distances(14000,26000)
                props(c,affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False)
            assert max(support_gaps)<0
            report.update(surface_meshes=len(data['parts']),bank_meshes=len(data['bank_parts']),surface_triangles=data['triangles'],bank_stones=len(data['stones']),max_stone_basal_gap_m=max(support_gaps),terrain_height_changed=False,runtime_solver=False,vehicle_water_interaction=False,backup=backup)
            # Saved camera bookmarks make the new reach easy to locate.
            for row in data['cameras']:
                a=act.spawn_actor_from_class(u.CameraActor,u.Vector(*(v*100 for v in row['position_m'])));a.set_actor_label('Benmore_River_Camera_'+row['name']);a.set_actor_rotation(u.Rotator(pitch=row['pitch'],yaw=row['yaw']),False);a.camera_component.set_field_of_view(70)
            u.SystemLibrary.execute_console_command(world,'grass.FlushCache');phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>30:
            if (OUT/'bank-art-placements.json').exists():
                phase='art_install'
                from benmore_river_bank_art import apply_art
                bank_art_report=apply_art(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world());phase='art_warm';last=time.monotonic()
            else:
                phase='saving';assert les.save_current_level();finish()
        elif phase=='art_warm' and time.monotonic()-last>12:
            phase='art_check'
            from benmore_river_bank_art import check_support
            check_support(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),bank_art_report)
            phase='saving';assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL);finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
