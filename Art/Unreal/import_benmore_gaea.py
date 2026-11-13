"""Import the approved Gaea return into a separate review map and re-seat dressing."""
import unreal as u
import array,hashlib,json,math,sys,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea';DATA=OUT/'integration'
SOURCE='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea';LEVEL=DEST+'/L_Benmore_GaeaReview'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_gaea_materials as materials
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
meta=json.loads((OUT/'candidate/import-manifest.json').read_text());data=json.loads((DATA/'assets.json').read_text())
assert meta['ok'] and data['ok'] and meta['candidate_sha256']==data['height_sha256']
grid=array.array('f');grid.frombytes((OUT/'candidate/height_local_south_up.f32').read_bytes())
oldraw=array.array('H');oldraw.frombytes((OUT/'source/H_Current_Unreal_2017.r16').read_bytes())
old=array.array('f',((v-32768)/64 for v in oldraw))
shore=array.array('f');shore.frombytes((DATA/'shore_distance.f32').read_bytes())
N=2017;phase='load';last=time.monotonic();started=last;cache={};support=[]
report={'ok':False,'level':LEVEL,'source_level':SOURCE,'candidate_sha256':meta['candidate_sha256'],'stages':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)


def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o


def height(a,x,y):
    fx=max(0,min(2015.999999,(x+1250)/2500*2016));fy=max(0,min(2015.999999,(y+1250)/2500*2016))
    i=int(fx);j=int(fy);s=fx-i;t=fy-j;k=j*N+i;q,r,v,w=a[k],a[k+1],a[k+N],a[k+N+1]
    return q+(r-q)*s+(w-r)*t if s>=t else q+(w-v)*s+(v-q)*t


def delta(x,y):
    return height(grid,x,y)-height(old,x,y) if abs(x)<1250 and abs(y)<1250 else 0.


def texture(name,path,exact=False):
    task=props(u.AssetImportTask(),filename=str(path),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,
          address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,
          mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS if exact else u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP,
          filter=u.TextureFilter.TF_NEAREST if exact else u.TextureFilter.TF_BILINEAR,never_stream=True)
    assert eal.save_loaded_asset(t);return t


def basal(mesh):
    path=mesh.get_path_name()
    if path not in cache:
        desc=mesh.get_static_mesh_description(0);assert desc
        bounds=mesh.get_bounds();cut=bounds.origin.z-bounds.box_extent.z+bounds.box_extent.z*.55
        pts=[desc.get_vertex_position(u.VertexID(i)) for i in range(desc.get_vertex_count())]
        pts=[p for p in pts if p.z<=cut];assert pts
        # All original low vertices are used: sparse sampling can miss rock rims.
        cache[path]=pts
    return cache[path]


def seat(tr,mesh,sink_cm=5.,record=False):
    constraints=[];oldz=tr.translation.z
    for p in basal(mesh):
        v=u.MathLibrary.transform_location(tr,p)
        if abs(v.x)>124900 or abs(v.y)>124900:continue
        z=height(grid,v.x/100,v.y/100)*100
        constraints.append((z-(v.z-oldz),v.x,v.y,z))
    if not constraints:return tr
    limit,x,y,z=min(constraints,key=lambda r:r[0]);newz=limit-sink_cm
    tr.translation=u.Vector(tr.translation.x,tr.translation.y,newz)
    if record:support.append([x,y,z,newz-limit])
    return tr


def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    report['source_map_unchanged']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest()==data['source_map_sha256']
    (DATA/'unreal-import-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()


def placement_digest(actor):
    h=hashlib.sha256();count=0
    for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,True);h.update(array.array('d',[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()]).tobytes());count+=1
    return [count,h.hexdigest()]


def dressing():
    removed=[];moved={};cleared={};bankcounts={};static_moved=[]
    for a in list(act.get_all_level_actors()):
        label=a.get_actor_label()
        if label.startswith(('Benmore_River_Surface_','Benmore_River_Bank_','Benmore_River_Art_')) or label=='Benmore_River_GravelBars':
            removed.append(label);act.destroy_actor(a);continue
        if isinstance(a,u.LandscapeProxy):continue
        instances=0;deleted=0
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=c.get_editor_property('static_mesh')
            if not mesh:continue
            foliage=any(k in label.lower() for k in ['scrub','shrubs','tussock','trees','willow'])
            rock=any(k in mesh.get_name().lower() for k in ['stone','rock'])
            remove=[]
            for i in range(c.get_instance_count()):
                tr=c.get_instance_transform(i,True);p=tr.translation;x=p.x/100;y=p.y/100
                if foliage and abs(x)<1250 and abs(y)<1250 and height(shore,x,y)<2.2:remove.append(i);continue
                dz=delta(x,y)
                if abs(dz)<.02:continue
                if rock:tr=seat(tr,mesh,4.5,instances%75==0)
                else:
                    tr.translation=u.Vector(p.x,p.y,p.z+dz*100)
                    if instances%75==0:support.append([p.x,p.y,height(grid,x,y)*100,None])
                assert c.update_instance_transform(i,tr,True,True,True);instances+=1
            for i in reversed(remove):assert c.remove_instance(i)
            deleted+=len(remove)
        if instances:moved[label]=instances
        if deleted:cleared[label]=deleted
        if isinstance(a,u.StaticMeshActor) and label.startswith(('Benmore_Scenery_','Benmore_Composition_SchistExposure_')):
            mesh=a.static_mesh_component.get_editor_property('static_mesh');tr=a.get_actor_transform()
            b=mesh.get_bounds();points=[u.MathLibrary.transform_location(tr,b.origin+u.Vector(x*b.box_extent.x,y*b.box_extent.y,-b.box_extent.z)) for x,y in [(0,0),(-1,-1),(-1,1),(1,-1),(1,1)]]
            if max(abs(delta(p.x/100,p.y/100)) for p in points)<.02:continue
            oldz=tr.translation.z;tr=seat(tr,mesh,8.,True);a.set_actor_transform(tr,False,True)
            static_moved.append({'label':label,'z_change_m':(tr.translation.z-oldz)/100})
        if label=='Benmore_Vista_Lake':a.static_mesh_component.set_material(0,materials.lake(a.static_mesh_component.get_material(0)))
    placements=json.loads((DATA/'bank-placements.json').read_text())
    for label,components in placements.items():
        a=act.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label(label.replace('Benmore_River_','Benmore_Gaea_'))
        total=0
        for row in components:
            mesh=u.load_asset(row['mesh']);assert mesh;trs=[]
            for i,p in enumerate(row['transforms']):
                tr=u.Transform();tr.translation=u.Vector(p['x_m']*100,p['y_m']*100,0);tr.rotation=u.Quat(*p['quat_xyzw']);tr.scale3d=u.Vector(*p['scale'])
                trs.append(seat(tr,mesh,6.5,i%31==0))
            if not trs:continue
            solid=label.endswith(('rocks','trees'))
            c=u.GTVegetationSubsystem.add_tagged_instances(a,mesh,trs,'BenmoreGaea','BlockAll' if solid else 'NoCollision',solid)
            for i,m in enumerate(row['materials']):
                if m:c.set_material(i,u.load_asset(m))
            c.set_cull_distances(22000 if solid else 14000,42000 if solid else 26000)
            props(c,affect_distance_field_lighting=solid,receives_decals=False);total+=len(trs)
        bankcounts[label]=total
    assert bankcounts==data['bank_counts']
    report.update(retired_river_actors=removed,repositioned_instances=moved,channel_foliage_cleared=cleared,repositioned_static_actors=static_moved,bank_instance_counts=bankcounts)


def water_mesh():
    name='SM_Benmore_GaeaCreeks'
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    task=props(u.AssetImportTask(),filename=str(DATA/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;u.get_editor_subsystem(u.StaticMeshEditorSubsystem).set_nanite_settings(mesh,ns,True)
    mesh.set_material(0,watermat);assert eal.save_loaded_asset(mesh)
    a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label('Benmore_Gaea_CreekSurface');a.static_mesh_component.set_static_mesh(mesh);a.static_mesh_component.set_material(0,watermat)
    a.static_mesh_component.set_collision_profile_name('NoCollision');a.set_actor_enable_collision(False);props(a.static_mesh_component,cast_shadow=False,affect_distance_field_lighting=False,receives_decals=False)
    raw=json.loads((DATA/(name+'.json')).read_text())['vertices'];bounds=mesh.get_bounds()
    for axis in ['x','y','z']:
        k=['x','y','z'].index(axis);lo=min(v[k] for v in raw)*100;hi=max(v[k] for v in raw)*100
        assert abs(getattr(bounds.origin,axis)-(lo+hi)/2)<.1
        assert abs(getattr(bounds.box_extent,axis)-(hi-lo)/2)<.1
    report['water_mesh_coordinate_bounds_verified']=True


def tick(dt):
    global phase,last,world,land,rt,transfer,watermat,road_before
    now=time.monotonic()
    try:
        if now-started>1100:raise RuntimeError('Gaea review import timed out; source map retained')
        if phase=='load':
            phase='loading'
            sourcefile=ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap'
            assert hashlib.sha256(sourcefile.read_bytes()).hexdigest()==data['source_map_sha256'],'Source level changed since export; resnapshot before import'
            previous=DATA/'unreal-import-report.json'
            if previous.exists() and json.loads(previous.read_text()).get('ok'):
                raise RuntimeError('Completed review already exists; use the saved-map check rather than overwriting it')
            assert les.load_level(SOURCE);eal.make_directory(DEST)
            sourceworld=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            assert u.EditorLoadingAndSavingUtils.save_map(sourceworld,LEVEL)
            assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();assert world.get_path_name().startswith(LEVEL+'.')
            land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape));land.set_actor_label('Benmore_Gaea_Terrain_2500m')
            assert max(abs(a-b) for a,b in zip(land.get_actor_location().to_tuple(),meta['location_cm']))<.01
            road_before={label:placement_digest(next(a for a in act.get_all_level_actors() if a.get_actor_label()==label)) for label in ['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail']}
            tex=texture('T_Gaea_HeightRG',OUT/'candidate/T_Benmore_GaeaHeightRG.png',True)
            path=DEST+'/M_Gaea_HeightTransfer';transfer=u.load_asset(path) or assets.create_asset('M_Gaea_HeightTransfer',DEST,u.Material,u.MaterialFactoryNew())
            for n in list(mel.get_material_expressions(transfer)):mel.delete_material_expression(transfer,n)
            transfer.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
            n=props(mel.create_material_expression(transfer,u.MaterialExpressionTextureSample),texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            mel.connect_material_property(n,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR);assert not mel.recompile_material(transfer);assert eal.save_loaded_asset(transfer)
            flow=texture('T_Gaea_Flow',DATA/'T_Gaea_Flow.png');banks=texture('T_Gaea_Banks',DATA/'T_Gaea_Banks.png');veg=texture('T_Gaea_VegetationMask',DATA/'T_Gaea_VegetationMask.png')
            terrain=materials.ground(land.get_editor_property('landscape_material'),banks,veg);land.set_editor_property('landscape_material',terrain);watermat=materials.water(flow,banks)
            rt=u.RenderingLibrary.create_render_target2d(world,N,N,u.TextureRenderTargetFormat.RTF_RGBA8)
            report['stages'].append('Copied source and prepared isolated materials');phase='warm';last=now
        elif phase=='warm' and now-last>20:
            phase='drawing';u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);phase='import';last=now
        elif phase=='import' and now-last>12:
            phase='importing';u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer)
            for a in meta['anchors']:
                c=u.RenderingLibrary.read_render_target_pixel(world,rt,*a['pixel']);z=(((int(c.r)<<8)|int(c.g))-32768)/64
                assert abs(z-a['z_m'])<.0001,(a,z)
            assert land.landscape_import_heightmap_from_render_target(rt,True,0)
            report['stages'].append('Imported exact approved heightfield');phase='settle';last=now
        elif phase=='settle' and now-last>25:
            phase='exporting';assert land.landscape_export_heightmap_to_render_target(rt,True,True);phase='verify';last=now
        elif phase=='verify' and now-last>12:
            phase='verifying';assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            pixels=u.RenderingLibrary.read_render_target(world,rt,False);assert len(pixels)==N*N
            values=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
            digest=hashlib.sha256(values.tobytes()).hexdigest();assert digest==meta['candidate_sha256'],(digest,meta['candidate_sha256'])
            report['unreal_height_sha256']=digest;report['all_height_samples_exact']=True
            dressing();water_mesh()
            for camera in data['cameras']:
                a=act.spawn_actor_from_class(u.CameraActor,u.Vector(*(v*100 for v in camera['position_m'])));a.set_actor_label('Benmore_Gaea_Camera_'+camera['name'])
                a.set_actor_rotation(u.MathLibrary.find_look_at_rotation(a.get_actor_location(),u.Vector(*(v*100 for v in camera['target_m']))),False)
                a.camera_component.set_field_of_view(camera['fov']);a.camera_component.set_editor_property('constrain_aspect_ratio',False)
                if camera['name']=='Creek_Reach':u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(a.get_actor_location(),a.get_actor_rotation())
            road_after={label:placement_digest(next(a for a in act.get_all_level_actors() if a.get_actor_label()==label)) for label in road_before}
            assert road_after['Benmore_ReferenceRoadAggregate']==road_before['Benmore_ReferenceRoadAggregate']
            assert all(road_after[k][0]==road_before[k][0] for k in road_before)
            report['road_dressing_before']=road_before;report['road_dressing_after']=road_after
            report['stages'].append('Replaced river preview and grounded dressing')
            u.SystemLibrary.execute_console_command(world,'grass.FlushCache');phase='ground_check';last=time.monotonic()
        elif phase=='ground_check' and now-last>15:
            phase='checking';actors=act.get_all_level_actors();ignore=[a for a in actors if not isinstance(a,u.LandscapeProxy)];errors=[]
            for x,y,z,gap in support:
                hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,z+20000),u.Vector(x,y,z-20000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
                assert hit is not None,('Terrain support miss',x,y)
                actual=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z
                errors.append(abs(actual-z)/100)
            assert errors and max(errors)<.05,(len(errors),max(errors) if errors else 0)
            report['native_ground_checks']={'samples':len(errors),'max_error_m':max(errors),'largest_recorded_basal_gap_cm':max(v[3] for v in support if v[3] is not None)}
            (DATA/'support-samples.json').write_text(json.dumps(support))
            assert les.save_current_level();report['stages'].append('Saved review map with verified terrain collision')
            finish()
    except Exception:finish(traceback.format_exc())


handle=u.register_slate_post_tick_callback(tick)
