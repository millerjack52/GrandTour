"""Ground relief GR1 item 7 (docs/GROUND_RELIEF_PLAN.md): the relief pictures of the three test strips, the same cameras before
and after, the sun behind the camera (tussock_style_lighting's sun: pitch -27, yaw -58, so every camera looks along yaw -58).
Per strip Relief_Overview (25 m up, 40 deg down) and Relief_OnFoot (1.7 m eye, across the grass and hummocks to the track); on the
two bog strips Relief_Bog (a Standard section from 1.7 m, before driving: the pre-churn). Play In Editor, no driving, no timing.
GT_RELIEF_TAG names the set: Art/Export/<strip>/Relief_<view>.png for 'after' (the default), GR1_Before/ for 'before';
GT_RELIEF_STRIPS limits the run to some strips (GR1b retook MudVariants and LiveMudDrive). Writes Art/Export/GroundRelief/pictures-<tag>.json.
GR2 phase B item 5 (GT_RELIEF_GR2=1): per strip also Ground_Close (1.7 m eye, 30 deg down, at bare scrub between tussocks: the first
spot on a 4 x 2 m grid 10-18 m off the line with no tussock within 1.5 m of the aim and at least two within 4 m), Ground_Close_Detail0
(the same frame at gt.Ground.Detail 0 and gt.Ground.Scatter 0) and Ground_Far (1.7 m eye over 40-60 m of open scrub beyond the
tussock band, aimed at the ground 50 m on); every view along yaw -58 (the sun behind)."""
import unreal as u,json,time,math,os,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/GroundRelief';OUT.mkdir(parents=True,exist_ok=True)
TAG=os.environ.get('GT_RELIEF_TAG','after').strip() or 'after'
VIEW=(1440,900);YAW=-58.;FWD=(math.cos(math.radians(YAW)),math.sin(math.radians(YAW)))
# (folder, level, spec, overview target (m), on-foot eye (m), bog eye (m) or None)
STRIPS=[('MudVariants','/Game/GrandTour/ArtTests/MudVariants/L_MudVariants','/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants',(95.,0.),(80.,18.),(80.,4.)),
        ('DeformableGravel','/Game/GrandTour/ArtTests/DeformableGravel/L_GravelDeform','/Game/GrandTour/ArtTests/DeformableGravel/DA_GravelDeform',(70.,0.),(60.,18.),None),
        ('LiveMudDrive','/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive','/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive',(40.,0.),(30.,18.),(36.,4.))]
# GR1b: GT_RELIEF_STRIPS (comma-separated folder names) retakes only those strips, the same cameras.
ONLY=[x.strip() for x in os.environ.get('GT_RELIEF_STRIPS','').split(',') if x.strip()]
if ONLY:STRIPS=[s for s in STRIPS if s[0] in ONLY]
report={'ok':False,'tag':TAG,'strips':[],'images':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def ground(spec,x,y):return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x*100.,y*100.)
GR2=os.environ.get('GT_RELIEF_GR2','').strip()=='1'
def gr2_views(strip,world):
    """GR2 phase B item 5: Ground_Close (+ its Detail0 twin) and Ground_Far, placed from the level's own tussocks (meters)."""
    folder,level,spec_path,(tx,ty),(fx,fy),bog=strip;spec=u.load_asset(spec_path).spec
    tuss=[]
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if a.get_actor_label()!='TS_ApprovedTussock':continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=c.get_editor_property('static_mesh')
            if mesh is None or 'Fine' in mesh.get_name():continue
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True);tuss.append((t.translation.x/100.,t.translation.y/100.))
    side=spec.components_per_side*spec.subsections_per_component*spec.quads_per_subsection*spec.quad_size_cm/100.
    x0,y0=spec.origin_x_cm/100.,spec.origin_y_cm/100.
    def inside(x,y,m=2.):return x0+m<x<x0+side-m and y0+m<y<y0+side-m
    near=lambda x,y,r:sum(1 for (a,b) in tuss if (a-x)**2+(b-y)**2<r*r)
    reach=1.7/math.tan(math.radians(30.))
    aim=None
    for yy in [10.,-10.,12.,-12.,14.,-14.,16.,-16.,18.,-18.]:
        for xx in [tx+d for d in range(-40,44,4)]:
            ex,ey=xx-FWD[0]*reach,yy-FWD[1]*reach
            if inside(xx,yy) and inside(ex,ey) and near(xx,yy,1.5)==0 and near(xx,yy,4.)>=2 and near(ex,ey,0.6)==0:
                aim=(xx,yy);break
        if aim:break
    out=[]
    if aim:
        ax,ay=aim;ex,ey=ax-FWD[0]*reach,ay-FWD[1]*reach
        cam=((ex,ey,ground(spec,ex,ey)/100.+1.7),(ax,ay,ground(spec,ax,ay)/100.),65.)
        out.append(('Ground_Close',)+cam+([],))
        out.append(('Ground_Close_Detail0',)+cam+(['gt.Ground.Detail 0','gt.Ground.Scatter 0'],))
    # Far: from 24 m off the line on the side yaw -58 looks away to (the -y side), the aim 50 m on (shortened to stay on the landscape).
    ex,ey=tx,-24.
    for dist in (50.,45.,40.):
        ax,ay=ex+FWD[0]*dist,ey+FWD[1]*dist
        if inside(ax,ay,5.):break
    out.append(('Ground_Far',(ex,ey,ground(spec,ex,ey)/100.+1.7),(ax,ay,ground(spec,ax,ay)/100.),65.,[]))
    return out,dict(close_aim_m=aim,tussocks=len(tuss),far_aim_m=[round(ax,1),round(ay,1)])
def views(strip):
    folder,level,spec_path,(tx,ty),(fx,fy),bog=strip;spec=u.load_asset(spec_path).spec;out=[]
    back=25./math.tan(math.radians(40.))
    cx,cy=tx-FWD[0]*back,ty-FWD[1]*back
    out.append(('Relief_Overview',(cx,cy,ground(spec,cx,cy)/100.+25.),(tx,ty,ground(spec,tx,ty)/100.),60.))
    t=fy/-FWD[1];gx,gy=fx+FWD[0]*t,0.
    out.append(('Relief_OnFoot',(fx,fy,ground(spec,fx,fy)/100.+1.7),(gx,gy,ground(spec,gx,gy)/100.),65.))
    if bog:
        bx,by=bog;lx,ly=bx+FWD[0]*15.,by+FWD[1]*15.
        out.append(('Relief_Bog',(bx,by,None),(lx,ly,None),65.))   # Z from the mud surface in play (mud_height_cm_at)
    return out
idx=0;phase='load';last=time.monotonic();start=last;world=pc=camera=mud=None;queue=[];pending=None;FRAME=0;BUSY=False;cur=None
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def finish(err=None):
    global phase
    phase='done'
    if err:report['error']=err
    (OUT/('pictures-%s.json'%TAG)).write_text(json.dumps(report,indent=2))
    try:u.unregister_slate_post_tick_callback(handle)
    except Exception:pass
    try:u.EditorLevelLibrary.editor_end_play()
    except Exception:pass
    u.SystemLibrary.quit_editor()
def tick(dt):
    global BUSY
    if BUSY:return
    BUSY=True
    try:body()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False
def body():
    global idx,phase,last,world,pc,camera,mud,pending,FRAME,cur
    now=time.monotonic();FRAME+=1
    if now-start>3600:finish('timed out');return
    if pending and now>=pending[0] and FRAME>=pending[2]:
        console('HighResShot %dx%d filename="%s"'%(VIEW[0],VIEW[1],pending[1].as_posix()));pending=None;last=now;return
    if pending:return
    if phase=='load':
        if idx>=len(STRIPS):report['ok']=True;finish();return
        cur=STRIPS[idx];assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(cur[1]);phase='loaded';last=now
    elif phase=='loaded' and now-last>5:
        lib=getattr(u,'GTPlayWindowLibrary',None)
        if not(lib and lib.request_play_in_new_window(VIEW[0],VIEW[1])):u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
        phase='warm';last=now
    elif phase=='warm' and now-last>20:
        world=u.EditorLevelLibrary.get_game_world()
        if world is None:
            if now-last>90:raise RuntimeError('PIE did not start on '+cur[0])
            return
        pc=u.GameplayStatics.get_player_controller(world,0)
        camera=u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor)[0]
        mud=next((o for o in u.ObjectIterator(u.GTMudSubsystem) if o.get_outer()==world),None)
        weather=next((o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world),None)
        if weather:
            clear=weather.find_state('Clear')
            if clear:weather.set_state(clear,True)
            weather.set_wetness_for_test(0.)
        for car in u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn):   # parked out of every view, behind the start
            spec=u.load_asset(cur[2]).spec;car.set_actor_location(u.Vector(-1500,0,ground(spec,-15.,0.)+150.),False,True)
        folder=cur[0]+('/GR1_Before' if TAG=='before' else '');(ROOT/'Art/Export'/folder).mkdir(parents=True,exist_ok=True)
        row={'strip':cur[0],'level':cur[1],'cameras':{}}
        # GR1b: GT_RELIEF_CAMERAS names an earlier pictures-<tag>.json whose cameras are reused exactly (eye and target Z too).
        fixed=os.environ.get('GT_RELIEF_CAMERAS','').strip()
        known=next((r['cameras'] for r in json.loads(Path(fixed).read_text())['strips'] if r['strip']==cur[0]),{}) if fixed else {}
        extra=[]
        if GR2:
            extra,row['gr2']=gr2_views(cur,world)
        for name,eye,look,fov,*cmds in [v+([],) for v in views(cur)]+extra:
            cmds=cmds[0] if cmds else []
            if name in known:eye=tuple(known[name]['eye_m']);look=tuple(known[name]['look_m']);fov=known[name]['fov']
            ex,ey,ez=eye;lx,ly,lz=look
            if ez is None:   # the bog: 1.7 m over the mud surface, looking at the mud 15 m on
                spec=u.load_asset(cur[2]).spec
                ez=(ground(spec,ex,ey)+(mud.mud_height_cm_at(u.Vector2D(ex*100.,ey*100.)) if mud else 0.))/100.+1.7
                lz=(ground(spec,lx,ly)+(mud.mud_height_cm_at(u.Vector2D(lx*100.,ly*100.)) if mud else 0.))/100.
            row['cameras'][name]=dict(eye_m=[round(ex,2),round(ey,2),round(ez,2)],look_m=[round(lx,2),round(ly,2),round(lz,2)],fov=fov,console=cmds)
            queue.append((name,u.Vector(ex*100.,ey*100.,ez*100.),u.Vector(lx*100.,ly*100.,lz*100.),fov,ROOT/'Art/Export'/folder/(name+'.png'),cmds))
        report['strips'].append(row);phase='shots';last=now
    elif phase=='shots' and now-last>3:
        if not queue:
            u.EditorLevelLibrary.editor_end_play();idx+=1;phase='load';last=now+3;return
        name,cpos,ctarget,fov,path,cmds=queue.pop(0)
        # GR2: a view's switches for its own shot only (the default look back for the next).
        for c in ['gt.Ground.Detail 1','gt.Ground.Scatter 1']+list(cmds):console(c)
        camera.set_actor_location(cpos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos,ctarget),False)
        camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
        report['images'].append(str(path));pending=(now+3.,path,FRAME+15)
handle=u.register_slate_post_tick_callback(tick)
