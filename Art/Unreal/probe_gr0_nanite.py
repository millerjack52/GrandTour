"""GR0 probe (docs/GROUND_RELIEF_PLAN.md GR0), uncommitted: can Nanite tessellation displace the landscape here?
On a copy of L_MudVariants (L_GR_Probe): Nanite on the landscape, a copy of its material with tessellation and a displacement
from the gravel Loose height (TA_GV_ORH B, 2 m tile, +-4 cm), on-foot pictures with and without, NaniteStats pictures (counts).
Writes Art/Export/GRProbe/probe-report.json and the pictures there. No timing."""
import unreal as u,json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/GRProbe';OUT.mkdir(parents=True,exist_ok=True)
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;les=u.get_editor_subsystem(u.LevelEditorSubsystem)
SRC_LEVEL='/Game/GrandTour/ArtTests/MudVariants/L_MudVariants';SRC_MAT='/Game/GrandTour/ArtTests/MudVariants/M_VariantsLandscape'
DEST='/Game/GrandTour/ArtTests/GRProbe';LEVEL=DEST+'/L_GR_Probe';MAT=DEST+'/M_GR_ProbeLandscape'
SPEC='/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants'
VIEW=(1440,900)
report={'ok':False,'steps':{},'images':[],'errors':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def step(name,fn):
    try:
        r=fn();report['steps'][name]={'ok':True,'result':r};return r
    except Exception:
        report['steps'][name]={'ok':False,'error':traceback.format_exc().splitlines()[-3:]};return None
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def copy_assets():
    out={}
    if not eal.does_asset_exist(MAT):
        out['material']=bool(eal.duplicate_asset(SRC_MAT,MAT));eal.save_asset(MAT)
    # The level: load the source and save it under the probe's name (duplicate_asset of a World leaves a standalone copy that
    # the next load_level cannot collect: the first run's fatal error).
    assert les.load_level(SRC_LEVEL)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    out['level']=bool(u.EditorLoadingAndSavingUtils.save_map(world,LEVEL))
    out['current']=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name()
    out['exists']=[eal.does_asset_exist(MAT),eal.does_asset_exist(LEVEL)];return out
def build_material():
    m=eal.load_asset(MAT);assert m,MAT
    for e in list(mel.get_material_expressions(m)):
        if str(e.get_editor_property('desc')).startswith('GR0:'):mel.delete_material_expression(m,e)
    def expr(cls,y,**kw):return props(mel.create_material_expression(m,cls,-2600,y),desc='GR0:%d'%y,**kw)
    p=expr(u.MaterialExpressionWorldPosition,0,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    go=expr(u.MaterialExpressionTextureObject,150,texture=u.load_asset('/Game/GrandTour/ArtTests/DeformableGravel/TA_GV_ORH'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    tile=expr(u.MaterialExpressionScalarParameter,300,parameter_name='GR0TileCm',default_value=200.)
    c=expr(u.MaterialExpressionCustom,450,code='float2 uv=float2(P.x,-P.y)/max(Tile,1.0);\nreturn GO.SampleLevel(GOSampler,float3(uv,0.0),0.0).b;',output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
    c.set_editor_property('inputs',[props(u.CustomInput(),input_name=k) for k in ['P','GO','Tile']])
    for n,pin in [(p,'P'),(go,'GO'),(tile,'Tile')]:assert mel.connect_material_expressions(n,'',c,pin),pin
    prop=getattr(u.MaterialProperty,'MP_DISPLACEMENT',None);report['mp_displacement_in_python']=prop is not None
    if prop is None:
        # MP_Displacement is UMETA(Hidden) (SceneTypes.h, value 32): the fifth run found no Python name for it; try the cast.
        try:prop=u.MaterialProperty.cast(32);report['mp_displacement_cast']=str(prop)
        except Exception as e:report['mp_displacement_cast']='failed: %s'%e
    m.set_editor_property('enable_tessellation',True)
    assert prop is not None,'MaterialProperty.MP_DISPLACEMENT is not exposed to Python'
    assert mel.connect_material_property(c,'',prop),'connect to Displacement failed'
    m.set_editor_property('enable_tessellation',True)
    ds=m.get_editor_property('displacement_scaling');ds.set_editor_property('magnitude',8.);ds.set_editor_property('center',.5);m.set_editor_property('displacement_scaling',ds)
    errors=mel.recompile_material(m);eal.save_loaded_asset(m)
    return dict(errors=[str(e) for e in errors] if errors else [],blend=str(m.get_editor_property('blend_mode')),tess=bool(m.get_editor_property('enable_tessellation')),
                magnitude=m.get_editor_property('displacement_scaling').magnitude,center=m.get_editor_property('displacement_scaling').center)
def landscape_actor(world):
    return next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Landscape))
def setup_level():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    # Live rebuild stays off (the default): with it on, set_editor_property's PostEditChange asked for a Nanite build while the
    # proxy was not registered with ULandscapeSubsystem (Assertion failed: Proxies.Contains(LandscapeProxy), the third and fourth
    # runs). ALandscapeProxy::PreSave builds the Nanite representation (LandscapeInfo->UpdateNanite) when the level is saved.
    ls=landscape_actor(world)
    ls.set_editor_property('landscape_material',eal.load_asset(MAT))
    ls.set_editor_property('enable_nanite',True)
    return dict(landscape=ls.get_name(),nanite=bool(ls.get_editor_property('enable_nanite')),material=ls.get_editor_property('landscape_material').get_path_name())
def nanite_facts():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();ls=landscape_actor(world);out={}
    comps=ls.get_components_by_class(u.LandscapeNaniteComponent) if hasattr(u,'LandscapeNaniteComponent') else []
    out['nanite_components']=len(comps);tris=[]
    for c in comps:
        sm=c.get_editor_property('static_mesh')
        if sm is None:tris.append(None);continue
        try:tris.append(sm.get_num_triangles(0))
        except Exception as e:tris.append('n/a: %s'%e)
    out['nanite_mesh_triangles']=tris
    out['landscape_components']=len(ls.get_components_by_class(u.LandscapeComponent))
    return out
phase='setup';last=time.monotonic();start=last;world=pc=camera=None;queue=[];pending=None;FRAME=0
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def ground(x,y):return u.GTVehicleSetupLibrary.sample_terrain_height_cm(u.load_asset(SPEC).spec,x,y)
def aim(cpos,ctarget,fov):
    camera.set_actor_location(cpos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos,ctarget),False);camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
def finish(err=None):
    global phase
    phase='done'
    if err:report['errors'].append(err)
    (OUT/'probe-report.json').write_text(json.dumps(report,indent=2))
    try:u.unregister_slate_post_tick_callback(handle)
    except Exception:pass
    try:u.EditorLevelLibrary.editor_end_play()
    except Exception:pass
    u.SystemLibrary.quit_editor()
BUSY=False
def tick(dt):
    global BUSY
    if BUSY:return   # load_level and save_map tick slate: the second run's re-entry overflowed the stack
    BUSY=True
    try:tick_body(dt)
    finally:BUSY=False
def tick_body(dt):
    global phase,last,world,pc,camera,pending,FRAME
    now=time.monotonic();FRAME+=1
    try:
        if now-start>1800:finish('probe timed out');return
        if pending and now>=pending[0] and FRAME>=pending[2]:
            console('HighResShot %dx%d filename="%s"'%(VIEW[0],VIEW[1],pending[1].as_posix()));pending=None;last=now;return
        if pending:return
        if phase=='setup':
            step('copy',copy_assets);step('material',build_material)
            w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            if 'L_GR_Probe' not in w.get_path_name():assert les.load_level(LEVEL)
            phase='registered';last=now
        elif phase=='registered' and now-last>10:
            # The landscape proxies register with ULandscapeSubsystem over the ticks after the load (the third run's assertion,
            # Proxies.Contains(LandscapeProxy), was a Nanite build asked for in the load's own tick).
            step('level',setup_level);phase='nanite_wait';last=now
        elif phase=='nanite_wait' and now-last>45:
            step('nanite_before_save',nanite_facts)
            step('save',lambda:bool(les.save_current_level()));step('nanite_after_save',nanite_facts);phase='play';last=now
        elif phase=='play' and now-last>5:
            lib=getattr(u,'GTPlayWindowLibrary',None)
            report['play']='new window' if (lib and lib.request_play_in_new_window(VIEW[0],VIEW[1])) else (u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play() or 'level viewport')
            phase='warm';last=now
        elif phase=='warm' and now-last>25:
            world=u.EditorLevelLibrary.get_game_world()
            if world is None:
                if now-last>90:finish('PIE did not start')
                return
            pc=u.GameplayStatics.get_player_controller(world,0);report['viewport']=list(pc.get_viewport_size())
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Live_Overview')
            for c in u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn):c.set_actor_location(u.Vector(500,-3000,ground(500,-3000)+150),False,True)
            patches=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch)
            report['patches']=[dict(section=p.section_index,min=[p.bounds_min.x,p.bounds_min.y],max=[p.bounds_max.x,p.bounds_max.y]) for p in patches]
            std=next((p for p in patches if p.bounds_min.x<8800<p.bounds_max.x),None)
            ey=std.bounds_max.y if std else 680.
            # On foot: 1.7 m eye at 11 m off the line looking across the Standard patch's +Y edge; the edge close-up from 0.6 m.
            foot=(u.Vector(9000,ey+430,ground(9000,ey+430)+170),u.Vector(8600,0,ground(8600,0)),70.)
            edge=(u.Vector(9000,ey+160,ground(9000,ey+160)+60),u.Vector(9000,ey-60,ground(9000,ey-60)),60.)
            report['edge_y_cm']=ey;report['cameras']={'foot':[[foot[0].x,foot[0].y,foot[0].z],[foot[1].x,foot[1].y,foot[1].z]],'edge':[[edge[0].x,edge[0].y,edge[0].z],[edge[1].x,edge[1].y,edge[1].z]]}
            for tag,cmds in [('Tess1',['landscape.RenderNanite 1','r.Nanite.Tessellation 1']),('Tess0',['landscape.RenderNanite 1','r.Nanite.Tessellation 0']),('NoNanite',['landscape.RenderNanite 0','r.Nanite.Tessellation 1'])]:
                queue.append(('cmd',cmds));queue.append(('shot','GR0_OnFoot_'+tag,foot));queue.append(('shot','GR0_Edge_'+tag,edge))
                if tag!='NoNanite':queue.append(('cmd',['r.ShaderPrint 1','NaniteStats Primary']));queue.append(('shot','GR0_Stats_'+tag,foot));queue.append(('cmd',['NaniteStats off']))
            queue.append(('cmd',['landscape.RenderNanite 1','r.Nanite.Tessellation 1','r.Nanite.Visualize Triangles']));queue.append(('shot','GR0_Triangles_Tess1',edge))
            queue.append(('cmd',['r.Nanite.Tessellation 0']));queue.append(('shot','GR0_Triangles_Tess0',edge));queue.append(('cmd',['r.Nanite.Visualize None','r.Nanite.Tessellation 1']))
            phase='shots';last=now
        elif phase=='shots' and now-last>2:
            if not queue:report['ok']=True;finish();return
            item=queue.pop(0)
            if item[0]=='cmd':
                for c in item[1]:console(c)
                report.setdefault('commands',[]).append(item[1]);last=now+2;return
            name,(cpos,ctarget,fov)=item[1],item[2];aim(cpos,ctarget,fov);path=OUT/(name+'.png');report['images'].append(str(path))
            pending=(now+2.5,path,FRAME+12)
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
