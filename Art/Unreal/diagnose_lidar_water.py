"""LP2 step 1: diagnose the L_LidarStudy water. Read-only for assets and the level.
Eye-level PIE captures: A as installed, B the original Benmore material, C the plain
sheet material, D a metallic car body and trees/sky; river/pond_sky15 the A poses with the
SkyLight at 1.5 (PIE only, restored to 8.0). Writes Place/waterdiag.json."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/install_lidar_place.py').read_text().split('def run():')[0],'<lidar-place-helpers>','exec'))
WATER=OUT/'water';WATER.mkdir(parents=True,exist_ok=True)
sites=json.loads((OUT/'installed-sites.json').read_text())
report=dict(ok=False,driving_tested=False,images=[],started=time.strftime('%Y-%m-%d %H:%M:%S'))
world=pc=car=camera=None;busy=False
ORIGINAL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces/M_NativeDomainRiver'
PLAIN='/Game/GrandTour/Materials/M_GT_Water'
BENMORE_ON=False
BENMORE_LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'

def save():(OUT/'waterdiag.json').write_text(json.dumps(report,indent=2,default=str))
def js(v):
    if isinstance(v,(bool,int,float,str)) or v is None:return v
    if isinstance(v,(list,tuple)):return [js(x) for x in v]
    if isinstance(v,u.LinearColor):return [round(v.r,4),round(v.g,4),round(v.b,4),round(v.a,4)]
    if isinstance(v,u.Object):return v.get_path_name()
    return str(v)
def safe(obj,names):
    out={}
    for n in names:
        try:out[n]=js(obj.get_editor_property(n))
        except Exception:pass
    return out
MAT_PROPS=['material_domain','blend_mode','shading_model','two_sided','is_thin_surface','opacity_mask_clip_value','translucency_lighting_mode','refraction_method','refraction_depth_bias',
 'screen_space_reflections','contact_shadows','output_translucent_velocity','allow_negative_emissive_color','tangent_space_normal','use_material_attributes',
 'used_with_static_lighting','used_with_instanced_static_meshes','used_with_nanite','used_with_water','used_with_spline_meshes','used_with_skeletal_mesh',
 'disable_depth_test','write_only_alpha','fully_rough','use_hq_forward_reflections','use_planar_forward_reflections','is_sky','compute_fog_per_pixel','translucency_pass','enable_responsive_aa']
OUTPUTS=['MP_BASE_COLOR','MP_EMISSIVE_COLOR','MP_OPACITY','MP_OPACITY_MASK','MP_METALLIC','MP_SPECULAR','MP_ROUGHNESS','MP_NORMAL','MP_REFRACTION','MP_WORLD_POSITION_OFFSET','MP_AMBIENT_OCCLUSION','MP_PIXEL_DEPTH_OFFSET','MP_ANISOTROPY','MP_TANGENT','MP_SUBSURFACE_COLOR','MP_CUSTOM_DATA0','MP_CUSTOM_DATA1','MP_FRONT_MATERIAL','MP_SHADING_MODEL']

def material_report(m,tag):
    r=dict(path=m.get_path_name(),cls=m.get_class().get_name(),props=safe(m,MAT_PROPS),outputs={},customs=[],params={})
    for name in OUTPUTS:
        prop=getattr(u.MaterialProperty,name,None)
        if prop is None:continue
        try:
            n=mel.get_material_property_input_node(m,prop)
            if n:r['outputs'][name]=dict(node=n.get_class().get_name(),desc=str(n.get_editor_property('desc')),output=str(mel.get_material_property_input_node_output_name(m,prop)))
        except Exception as e:r['outputs'][name]='err '+str(e)[:80]
    for i,e in enumerate(mel.get_material_expressions(m)):
        cls=e.get_class().get_name()
        if isinstance(e,u.MaterialExpressionCustom):
            code=str(e.get_editor_property('code'));f=WATER/f'code_{tag}_{i}.hlsl';f.write_text(code)
            r['customs'].append(dict(index=i,desc=str(e.get_editor_property('desc')),file=f.name,chars=len(code),inputs=[str(x.get_editor_property('input_name')) for x in e.get_editor_property('inputs')],
              outputs=[str(x.get_editor_property('output_name')) for x in e.get_editor_property('additional_outputs')],output_type=str(e.get_editor_property('output_type'))))
        elif isinstance(e,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSample)):
            t=e.get_editor_property('texture');r.setdefault('textures',[]).append(dict(index=i,cls=cls,texture=t.get_path_name() if t else None,param=str(e.get_editor_property('parameter_name')) if isinstance(e,u.MaterialExpressionTextureObjectParameter) else None))
        elif 'SingleLayerWater' in cls or 'Substrate' in cls or 'Refraction' in cls or 'DepthFade' in cls or 'SceneDepth' in cls or 'SceneColor' in cls:
            r.setdefault('special_nodes',[]).append(dict(index=i,cls=cls,desc=str(e.get_editor_property('desc'))))
    exprs=list(mel.get_material_expressions(m));idx={e.get_path_name():i for i,e in enumerate(exprs)}
    def describe(x):
        if x is None:return None
        d=dict(index=idx.get(x.get_path_name()),cls=x.get_class().get_name())
        for k in ['parameter_name','texture','r','constant','default_value']:
            try:d[k]=js(x.get_editor_property(k))
            except Exception:pass
        return d
    r['links']={}
    for i,e in enumerate(exprs):
        if isinstance(e,u.MaterialExpressionCustom) or 'SingleLayerWater' in e.get_class().get_name() or isinstance(e,u.MaterialExpressionTextureSample):
            try:
                ins=list(mel.get_inputs_for_material_expression(m,e))
                try:names=[str(n) for n in mel.get_material_expression_input_names(e)]
                except Exception:names=[str(x.get_editor_property('input_name')) for x in e.get_editor_property('inputs')] if isinstance(e,u.MaterialExpressionCustom) else [str(k) for k in range(len(ins))]
                row={}
                for k,x in enumerate(ins):
                    if x is None:continue
                    name=names[k] if k<len(names) else str(k);d=describe(x)
                    try:d['out']=str(mel.get_input_node_output_name_for_material_expression(e,name))
                    except Exception:pass
                    row[name]=d
                r['links'][str(i)]=row
            except Exception as ex:r['links'][str(i)]='err '+str(ex)[:120]
    for kind,names,get in [('scalar',mel.get_scalar_parameter_names,mel.get_material_default_scalar_parameter_value),('vector',mel.get_vector_parameter_names,mel.get_material_default_vector_parameter_value),('texture',mel.get_texture_parameter_names,mel.get_material_default_texture_parameter_value)]:
        try:r['params'][kind]={str(n):js(get(m,n)) for n in names(m)}
        except Exception as e:r['params'][kind]='err '+str(e)[:80]
    return r

def chain(m):
    out=[];k=0
    while m and k<6:
        item=dict(cls=m.get_class().get_name(),name=m.get_name(),path=m.get_path_name());out.append(item);k+=1
        if isinstance(m,u.MaterialInstance):m=m.get_editor_property('parent')
        else:break
    if not out or (out[-1]['cls']!='Material' and len(out)<6):out.append(dict(cls='None',name='<no parent>'))
    return out

def mid_report(m):
    r=dict(chain=chain(m))
    if isinstance(m,u.MaterialInstance):
        for k in ['AmbientReady','FieldActive','LocalSurface','AmbientClock','FieldLevelCm','WakeDetailReady','DetailEnabled']:
            try:r[k]=m.get_scalar_parameter_value(k)
            except Exception as e:r[k]='err '+str(e)[:60]
        for k in ['AmbientTex','FieldTex','DetailTex']:
            try:
                t=m.get_texture_parameter_value(k);r[k]=(t.get_class().get_name()+' '+t.get_name()) if t else None
            except Exception as e:r[k]='err '+str(e)[:60]
    return r

def lighting(w):
    out={}
    for cls in [getattr(u,n,None) for n in ['SkyLight','SkyAtmosphere','DirectionalLight','ExponentialHeightFog','PostProcessVolume','VolumetricCloud','SphereReflectionCapture','BoxReflectionCapture','PlanarReflection']]:
        if cls is None:continue
        rows=[]
        for a in u.GameplayStatics.get_all_actors_of_class(w,cls):
            row=dict(name=a.get_name(),label=a.get_actor_label() if hasattr(a,'get_actor_label') else '')
            if cls==u.SkyLight:row.update(safe(a.light_component,['real_time_capture','intensity','source_type','cubemap','lower_hemisphere_is_black','cast_shadows','affects_world','mobility','indirect_lighting_intensity','volumetric_scattering_intensity','sky_distance_threshold','capture_emissive_only']))
            if cls==u.DirectionalLight:row.update(safe(a.light_component,['intensity','light_color','atmosphere_sun_light','cast_shadows','mobility','indirect_lighting_intensity','use_temperature','temperature']));row['rotation']=js(a.get_actor_rotation().to_tuple())
            if cls==u.ExponentialHeightFog:row.update(safe(a.get_editor_property('component'),['fog_density','fog_height_falloff','enable_volumetric_fog','fog_inscattering_luminance','start_distance']))
            if cls==u.PostProcessVolume:
                row.update(safe(a,['enabled','unbound','priority','blend_weight']))
                s=a.get_editor_property('settings')
                row['settings']=safe(s,['override_reflection_method','reflection_method','override_dynamic_global_illumination_method','dynamic_global_illumination_method','override_lumen_reflection_quality','lumen_reflection_quality',
                  'override_screen_space_reflection_intensity','screen_space_reflection_intensity','override_screen_space_reflection_quality','screen_space_reflection_quality','override_lumen_front_layer_translucency_reflections','lumen_front_layer_translucency_reflections',
                  'override_lumen_ray_lighting_mode','lumen_ray_lighting_mode','override_lumen_max_reflection_bounces','lumen_max_reflection_bounces','override_auto_exposure_method','auto_exposure_method','override_auto_exposure_bias','auto_exposure_bias','override_auto_exposure_min_brightness','auto_exposure_min_brightness','override_auto_exposure_max_brightness','auto_exposure_max_brightness'])
                row['settings']={k:v for k,v in row['settings'].items() if not k.startswith('override_') or v}
            rows.append(row)
        out[cls.__name__]=rows
    return out

CVARS=['r.ReflectionMethod','r.Lumen.Reflections.Allow','r.SSR.Quality','r.DynamicGlobalIlluminationMethod','r.Lumen.TranslucencyReflections.FrontLayer.Allow','r.Lumen.TranslucencyReflections.FrontLayer.Enable',
 'r.Lumen.HardwareRayTracing','r.Lumen.Reflections.HardwareRayTracing','r.Lumen.Reflections.ScreenTraces','r.Water.SingleLayer','r.Water.SingleLayer.Reflection','r.Water.SingleLayer.RefractionDownsampleFactor','r.Water.SingleLayer.SSRTAA','r.Water.SingleLayer.LumenReflections',
 'r.Substrate','r.SkyLight.RealTimeReflectionCapture','r.ReflectionCaptureResolution','r.Lumen.Reflections.MaxRoughnessToTrace','r.Lumen.Reflections.SmoothBias','gt.Look.Post','gt.Look.Surface','gt.Water.Domain.Ambient','gt.Water.Domain.Detail']
def cvars():
    out={}
    for c in CVARS:
        try:out[c]=u.SystemLibrary.get_console_variable_float_value(c)
        except Exception as e:out[c]='err'
    return out

def settle(seconds):
    start=u.GameplayStatics.get_time_seconds(world);deadline=time.monotonic()+180
    while u.GameplayStatics.get_time_seconds(world)-start<seconds:
        assert time.monotonic()<deadline;yield .1

def ground_z(x,y):
    hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,60000),u.Vector(x,y,-20000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[car] if car else [],u.DrawDebugTrace.NONE,True)
    if hit is None:return None
    vs=[v for v in hit.to_tuple() if isinstance(v,u.Vector)]
    return vs[0].z if vs else None

def column(x,y):
    hits=u.SystemLibrary.line_trace_multi(world,u.Vector(x,y,60000),u.Vector(x,y,-20000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[],u.DrawDebugTrace.NONE,True)
    out=[]
    for h in hits or []:
        t=h.to_tuple();vs=[v for v in t if isinstance(v,u.Vector)];acts=[v for v in t if isinstance(v,u.Actor)]
        out.append(dict(z=round(vs[0].z,1) if vs else None,actor=(acts[0].get_actor_label() or acts[0].get_name()) if acts else None))
    return out

def capture(name,pos,target,fov=68,sky=None):
    global camera
    if camera:camera.destroy_actor()
    p=u.Vector(*pos);t=u.Vector(*target);camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'LiDARWater')
    camera.camera_component.set_field_of_view(fov);camera.camera_component.set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0);yield from settle(3)
    path=WATER/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
    if sky:
        # GTWeatherSubsystem re-applies its cached sky intensity (8.0) on every unpaused tick and does not
        # tick while paused, so the test intensity is set after the pause and left 2 s to settle.
        sky[0].set_intensity(sky[1]);yield 2;report['sky_intensity'][name]=sky[0].get_editor_property('intensity')
    u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
    until=time.monotonic()+45
    while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
    if sky:sky[0].set_intensity(8.0)
    u.GameplayStatics.set_game_paused(world,False);report['images'].append(str(path));report.setdefault('poses',{})[name]=dict(camera=list(pos),target=list(target));save()

def park(site_name):
    site=next(s for s in sites if s['name']==site_name);x,y=site['center'];z=site['center_height_cm']
    mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    car.set_actor_location_and_rotation(u.Vector(x,y,z+100),u.Rotator(yaw=site['yaw']),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
    yield from settle(8)

def surfaces_pie():
    out={}
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor):
        c=a.static_mesh_component;m=c.static_mesh if c else None
        if m and m.get_name() in ['SM_MappedPondWater','SM_AccessPondWater','SM_RiverWater']:out[m.get_name()[3:-5]]=c
    return out

def pond_pose(lift=0):
    x,y,z=next(p for p in data['water'] if p['name']=='AccessPond')['probe']
    return (x-900,y+600,z+160+lift),(x+600,y-400,z-20)
def river_pose(shift=400,lift=0):
    # Run 1: a bush crown and a rock face blocked the brief's pose; move 4 m to the camera's right.
    x,y,z=data['river_house_probe'];dx,dy=-1100,-1600;n=math.hypot(dx,dy);rx,ry=-dy/n,dx/n
    return (x+500+rx*shift,y+700+ry*shift,z+150+lift),(x-600+rx*shift,y-900+ry*shift,z-30)

def run():
    global world,pc,car
    assert les.load_level(LEVEL);refs=actors.get_all_level_actors();sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet))
    report['sheet']=safe(sheet,['ambient_wave_material','ambient_wave_resolution','surface_material_path','water_domain'])
    report['sheet']['domain_surfaces']=[a.get_actor_label() for a in sheet.get_editor_property('domain_surfaces')]
    try:report['sheet']['domain_materials']=js(sheet.get_editor_property('domain_materials'))
    except Exception as e:report['sheet']['domain_materials']='not exposed to Python ('+type(e).__name__+')'
    report['editor_surfaces']={}
    for a in sheet.get_editor_property('domain_surfaces'):
        c=a.static_mesh_component;report['editor_surfaces'][a.get_actor_label()]=dict(component_material=chain(c.get_material(0)),mesh_material=chain(c.static_mesh.get_material(0)),cast_shadow=c.cast_shadow,translucency_sort=c.get_editor_property('translucency_sort_priority'))
    report['materials']={}
    for name in ['AccessPond','River','MappedPond']:report['materials']['clone_'+name]=material_report(u.load_asset(BASE+f'/M_{name}Water'),'clone_'+name)
    report['materials']['original']=material_report(u.load_asset(ORIGINAL),'original')
    report['materials']['plain']=material_report(u.load_asset(PLAIN),'plain')
    report['editor_lighting']=lighting(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world());save()
    # Exactly what check_lidar_place.py does in the editor world before PIE.
    report['editor_preview']=[]
    for patch in data['water']:
        x,y,z=patch['probe'];xy=u.Vector2D(x,y);sheet.preview_water_at(xy,0,True);before=sheet.surface_cm_at(xy);added=sheet.add_impulse(xy,120,3);sheet.preview_water_at(xy,.2,False)
        report['editor_preview'].append(dict(name=patch['name'],surface_cm=before,added_m3=added))
    report['editor_surfaces_after_preview']={a.get_actor_label():chain(a.static_mesh_component.get_material(0)) for a in sheet.get_editor_property('domain_surfaces')};save()
    refs=sheet=a=c=None;gc.collect();yield 1
    les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
    deadline=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<deadline;yield .5
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert isinstance(car,u.GTCarPawn);pc.possess(car)
    car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement();move.set_brake_input(0);move.set_throttle_input(0);move.set_handbrake_input(True)
    for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
    report['cvars']=cvars();report['pie_lighting']=lighting(world);save()
    # A: as installed.
    yield from park('Pond bend')
    pos,tgt=pond_pose();g=ground_z(pos[0],pos[1]);report['pond_camera_ground_cm']=g
    lift=max(0,(g or -1e9)+160-pos[2]);report['pond_camera_lift_cm']=lift
    surf=surfaces_pie();report['pie_surfaces']={k:mid_report(c.get_material(0)) for k,c in surf.items()};save()
    pos,tgt=pond_pose(lift);yield from capture('pond_A',pos,tgt)
    yield from park('Riverside house')
    pos,tgt=river_pose();g=ground_z(pos[0],pos[1]);report['river_camera_ground_cm']=g;lift=max(0,(g or -1e9)+160-pos[2]);report['river_camera_lift_cm']=lift
    pos,tgt=river_pose(400,lift);yield from capture('river_A',pos,tgt)
    report['pie_surfaces_after_A']={k:mid_report(c.get_material(0)) for k,c in surfaces_pie().items()};save()
    # B/C: swap only the access pond component's material, then restore.
    yield from park('Pond bend')
    comp=surfaces_pie()['AccessPond'];installed=comp.get_material(0);lift=report['pond_camera_lift_cm']
    for tag,path in [('B',ORIGINAL),('C',PLAIN)]:
        comp.set_material(0,u.load_asset(path));yield from settle(2)
        pos,tgt=pond_pose(lift);yield from capture('pond_'+tag,pos,tgt)
        comp.set_material(0,installed);yield from settle(.5)
    report['restored_access_pond']=comp.get_material(0)==installed
    # D: metallic car body at eye level beside the pond bend, and trees+sky over the river.
    p=car.get_actor_location();yaw=math.radians(car.get_actor_rotation().yaw);fx,fy=math.cos(yaw),math.sin(yaw)
    pos=(p.x+fx*350-fy*450,p.y+fy*350+fx*450,p.z+90);yield from capture('pond_D',pos,(p.x,p.y,p.z+40))
    yield from park('Riverside house')
    pos,tgt=river_pose(400,report['river_camera_lift_cm']);tgt=(tgt[0],tgt[1],tgt[2]+700);yield from capture('river_D',pos,tgt)
    pond=next(p for p in data['water'] if p['name']=='AccessPond');x,y,z=pond['probe']
    yield from park('Pond bend');yield from capture('pond_check',(x-3300,y+2800,z+2000),(x,y,z))
    report['columns']={'pond_probe':column(x,y),'pond_camera':column(*pond_pose()[0][:2])}
    x,y,z=data['river_house_probe'];yield from park('Riverside house');yield from capture('river_check',(x+600,y+900,z+1100),(x,y-500,z))
    report['columns'].update(river_probe=column(x,y),river_camera=column(*river_pose()[0][:2]))
    # LP2b: the same eye-level pair with the SkyLight at 1.5 (this map 8.0, Benmore review 1.15), set in PIE only, never saved.
    skies=list(u.GameplayStatics.get_all_actors_of_class(world,u.SkyLight));assert len(skies)==1,len(skies);sky=skies[0].light_component
    report['sky_intensity']=dict(before=sky.get_editor_property('intensity'));save()
    yield from capture('river_sky15',*river_pose(400,report['river_camera_lift_cm']),sky=(sky,1.5))
    yield from park('Pond bend');yield from capture('pond_sky15',*pond_pose(report['pond_camera_lift_cm']),sky=(sky,1.5))
    yield from settle(.5);report['sky_intensity']['restored']=sky.get_editor_property('intensity');save();sky=skies=None
    report['pie_ok']=True;save()
    comp=installed=surf=move=None;gc.collect()
    yield from finish(False)
    # Read-only lighting/material reference from the Benmore review map (run 1 recorded it).
    try:
        assert BENMORE_ON
        t0=time.monotonic();assert les.load_level(BENMORE_LEVEL);yield 2
        w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();report['benmore_lighting']=lighting(w);report['benmore_load_s']=round(time.monotonic()-t0,1)
        users=[]
        for a in actors.get_all_level_actors():
            if isinstance(a,u.StaticMeshActor) and a.static_mesh_component:
                m=a.static_mesh_component.get_material(0)
                if m and 'DomainRiver' in m.get_path_name():users.append(dict(label=a.get_actor_label(),material=m.get_path_name(),cast_shadow=a.static_mesh_component.cast_shadow,sort=a.static_mesh_component.get_editor_property('translucency_sort_priority')))
        report['benmore_river_surfaces']=users[:8];w=a=m=None
    except AssertionError:
        if BENMORE_ON:report['benmore_error']=traceback.format_exc()[-600:]
    except Exception:report['benmore_error']=traceback.format_exc()[-600:]
    gc.collect();les.load_level('/Engine/Maps/Entry');yield 2
    report['ok']=True;save()

def finish(entry=True):
    global world,pc,car,camera
    if world:u.GameplayStatics.set_game_paused(world,False)
    u.EditorLevelLibrary.editor_end_play();yield 4
    world=pc=car=camera=None;gc.collect()
    if entry:les.load_level('/Engine/Maps/Entry');yield 2

steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
    global deadline,busy,steps,failed
    if busy:return
    busy=True
    try:
        assert time.monotonic()-began<1700,'WaterDiag timeout'
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
    except Exception:
        report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
        if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
