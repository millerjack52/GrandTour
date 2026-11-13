"""Mud and water MW1 (docs/MUD_WATER_SURFACE_PLAN.md items 1, 4 and 5): the owner's on-foot frame along a water-filled old track
(GR1c puddle) on L_MudVariants, its debug set, the moving-water frames, the rings drive, the footsteps and the close mud, with the
buffer dumps the gates read. Run by Art/check_mud_water.ps1 (fixed 1/60 s step); python Art/sample_mud_water.py reads the report.

GT_MW_TAG names the run: 'before' (the diagnosis, before any MW1 change: MW_Before_*) or 'after' (MW_* and the switch pairs).
GT_MW_CAMERAS names an earlier report whose puddle and cameras are reused exactly (the after run takes the before run's frames).
GT_MW_TAG 'mrd' (Mud roads MRD1, docs/MUD_ROADS_PLAN.md item 6; Art/Export/MudRoads/check-mrd.json, Art/sample_mud_roads.py reads it):
the MW owner frame and its moving-water frames on L_MudVariants' Standard section (now a MudRoad) for the glare and motion gates, the
six MRD pictures (MRD_Ref1-5 beside the owner's references, MRD_Top), every patch's DescribeMudRoad, the mud mask last; then
L_MudDrive's 60 m MudRoad (MRD_Top_MudDrive, MRD_Ref1_MudDrive, its DescribeMudRoad).
MRD1b: GT_MRD_CAMERAS names an earlier check-mrd.json whose MRD cameras (both stages) are reused exactly; GT_MRD_CHASE 0 skips the
chase (MRD_Ref5); MRD_Ref4's water cells go in the report (the puddle look gate); a camera that does not move when aimed is made
movable (L_MudDrive's two MRD1 pictures were one view).
The steps (no timing, no cost):
- the puddle: the Standard and Deep patches' cells under their water table (AGTMudPatch WaterTableCm + WaterLiftCm against the
  surface, UGTMudSubsystem::MudCellHeightsCm), the cell with the most water within 1.5 m along X and 25 cm across;
- the owner's frame: on foot, the eye 1.6 m over the mud 4.5 m behind the puddle, looking along the track (-X) over it, the sun
  turned 30 deg off the view and 22 deg up (about 37 deg ahead of the view: the grazing glare case);
- the debug set at that frame: SlideUV 0 and FreshWet 0 (every patch's mud instance), gt.Mud.POM 0, the rut water hidden, the
  buffers (BaseColor, Roughness, WorldNormal, MaterialAO; uncompressed EXR); after: gt.Mud.DeformDetail 0 and gt.Mud.WaterMotion 0;
- the water: a fixed camera 1.8 m over the puddle looking down along it, the water hidden (the mask), then three frames 30 game
  frames (0.5 s) apart with rendering on throughout; after: again with gt.Mud.WaterMotion 0;
- the rings: the car from 10 m back along the track at about 10 km/h (low range, diff lock), its wheels in the puddle's rut, side
  view with the sun behind the camera when its front axle is 1 m past the puddle's centre (rendering on for its last 3 m);
- the footsteps: the car parked away, the player out and walked through the puddle along the track (UGTMudWaterSubsystem's ring
  counts when it is built);
- the close mud: a deformed bank of the car's rut 2 m from the eye (the owner's sun), the water hidden (the mask), the buffer dumps
  dry and at test wetness 1, and the strip's gravel (the calibration, roughness 0.9 by construction).
Writes Art/Export/MudWater/check-<tag>.json."""
import unreal as u,json,time,math,os,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudWater';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from check_render import Gate
TAG=os.environ.get('GT_MW_TAG','after').strip() or 'after'
PRE={'before':'MW_Before_','mw1':'MW1_'}.get(TAG,'MW_')   # MW1b: 'mw1' is MW1's committed look, before MW1b
LEVEL='/Game/GrandTour/ArtTests/MudVariants/L_MudVariants';SPEC='/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants'
SECTIONS=[('Standard',7500.,10000.),('Deep',12000.,14500.)]
# Mud roads MRD1: the MudRoad (Standard) only, its own folder, then L_MudDrive's MudRoad (115-175 m) as a second stage.
MRD=TAG=='mrd';STAGE=1
MRD_LEVEL2='/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive';MRD_SPEC2='/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive';MRD_ROAD2=(11500.,17500.)
if MRD:
    OUT=ROOT/'Art/Export/MudRoads';OUT.mkdir(parents=True,exist_ok=True);SECTIONS=[('Standard',7500.,10000.)]
MRD_OLD=json.loads(Path(os.environ['GT_MRD_CAMERAS']).read_text()) if os.environ.get('GT_MRD_CAMERAS','').strip() else {}   # MRD1b
MRD_CHASE=os.environ.get('GT_MRD_CHASE','1').strip()!='0'
MRD_SHOTS=[s.strip() for s in os.environ.get('GT_MRD_SHOTS','').split(',') if s.strip()]   # MRD1c: only these MRD stills (all when empty)
CALIB=(6500.,260.)   # gravel between Firm and Standard, off the line (check_mud_variants MRP_CALIB: roughness 0.9 by construction)
VIEW=(1440,900);TARGETS='BaseColor,Roughness,WorldNormal,MaterialAO'
OWNER_SUN=dict(pitch=-22.,yaw=30.)      # the light travels toward yaw 30: the sun at azimuth 210, 22 deg up; the view looks at 180
SIDE_SUN=dict(pitch=-35.,yaw=90.)       # the light travels +Y: behind a camera on the -Y side looking +Y
GATE=Gate()
report={'ok':False,'tag':TAG,'level':LEVEL,'images':[],'cameras':{},'dumps':[],'steps':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
world=pc=camera=car=move=mud=weather=spec=None;patches=[];FRAME=0;BUSY=False;start=time.monotonic();phase='load';last=start
steps=[];cur=None;WET=0.;sun=None;mws=None;ring0=None

def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def ground(x,y):return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x,y)
def surf(x,y):return ground(x,y)+mud.mud_height_cm_at(u.Vector2D(x,y))
def V(a):return u.Vector(a[0],a[1],a[2])
def gtime():
    try:return u.GameplayStatics.get_time_seconds(world)
    except Exception:return 0.
def note(s):report['steps'].append('%.1f s (game %.2f): %s'%(time.monotonic()-start,gtime(),s));u.log('MW1CHECK '+s)
def save():(OUT/('check-%s.json'%TAG)).write_text(json.dumps(report,separators=(',',':')))   # compact: the water cells run to thousands
def finish(err=None):
    global phase
    phase='done'
    if err:report['error']=err;u.log_error('MW1CHECK '+err)
    try:report['check_run']=GATE.report()
    except Exception:report['check_run_error']=traceback.format_exc().splitlines()[-1]
    save()
    try:u.unregister_slate_post_tick_callback(handle)
    except Exception:pass
    try:u.EditorLevelLibrary.editor_end_play()
    except Exception:pass
    u.SystemLibrary.quit_editor()

# ---- the puddle ----------------------------------------------------------------------------------------------------------
def find_puddle(sections=SECTIONS,key='puddle_search'):
    best=None;rows=[]
    for name,x0,x1 in sections:
        mid=.5*(x0+x1)
        p=next((q for q in patches if q.bounds_min.x<=mid<=q.bounds_max.x),None)
        if p is None:rows.append(dict(section=name,patch=None));continue
        lo=u.Vector2D(p.bounds_min.x,p.bounds_min.y);hi=u.Vector2D(p.bounds_max.x,p.bounds_max.y)
        hs=list(mud.mud_cell_heights_cm(lo,hi));nx=mud.mud_cells_across(lo,hi)
        if not hs or nx<=0:rows.append(dict(section=name,patch=p.get_name(),cells=0));continue
        ny=len(hs)//nx;cx=(hi.x-lo.x)/nx;cy=(hi.y-lo.y)/ny
        table=p.water_table_cm+p.water_lift_cm
        d=[max(0.,table-h) for h in hs]
        wx=int(round(75./cx));wy=max(1,int(round(25./cy)))
        top=None
        for j in range(wy,ny-wy):
            for i in range(wx,nx-wx):
                if d[j*nx+i]<1.5:continue
                x=lo.x+(i+.5)*cx
                if x<x0+300. or x>x1-300.:continue   # inside the section, room for the eye and the car's run-up
                s=0.
                for jj in range(j-wy,j+wy+1):
                    base=jj*nx
                    for ii in range(i-wx,i+wx+1):s+=d[base+ii]
                if top is None or s>top[0]:top=(s,i,j)
        wet=sum(1 for v in d if v>=1.)
        row=dict(section=name,patch=p.get_name(),cells=len(d),cell_cm=[round(cx,2),round(cy,2)],table_cm=round(table,2),cells_1cm=wet,
                 deepest_cm=round(max(d),2))
        if top:
            s,i,j=top;row.update(score=round(s,1),x_cm=round(lo.x+(i+.5)*cx,1),y_cm=round(lo.y+(j+.5)*cy,1),depth_cm=round(d[j*nx+i],2))
            # Its extent along X at that row (cells over 1 cm), for the reports.
            a=i
            while a>0 and d[j*nx+a-1]>=1.:a-=1
            b=i
            while b<nx-1 and d[j*nx+b+1]>=1.:b+=1
            row['run_x_cm']=[round(lo.x+(a+.5)*cx,1),round(lo.x+(b+.5)*cx,1)]
            if best is None or s>best[0]:best=(s,row,p,table)
        rows.append(row)
    report[key]=rows
    assert best,'no puddle (cells 1.5 cm under the table) in Standard or Deep: %s'%rows
    s,row,p,table=best
    return dict(section=row['section'],x=row['x_cm'],y=row['y_cm'],depth_cm=row['depth_cm'],table_cm=table,run_x_cm=row['run_x_cm'],patch=p.get_name())

def cameras(P):
    x,y=P['x'],P['y'];wz=ground(x,y)+P['table_cm']
    ex=x+450.;ez=surf(ex,y)+160.
    cams=dict(owner=dict(eye=[ex,y,ez],look=[x-300.,y,wz],fov=75.),
              water=dict(eye=[x+200.,y,wz+180.],look=[x-40.,y,wz],fov=50.))
    return cams

# ---- the steps -----------------------------------------------------------------------------------------------------------
def aim(c):
    cpos=V(c['eye']);ct=V(c['look'])
    camera.set_actor_location(cpos,False,False)
    if (camera.get_actor_location()-cpos).length()>1.:
        # MRD1b item 5: a camera that does not move (static mobility) is made movable, once, and the fix reported.
        camera.root_component.set_mobility(u.ComponentMobility.MOVABLE);camera.set_actor_location(cpos,False,False)
        report.setdefault('camera_fixes',[]).append(dict(camera=camera.get_name(),moved=bool((camera.get_actor_location()-cpos).length()<=1.)))
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos,ct),False)
    camera.camera_component.set_field_of_view(c['fov']);pc.set_view_target_with_blend(camera,0.)
def set_sun(r):
    global sun
    for l in u.GameplayStatics.get_all_actors_of_class(world,u.DirectionalLight):
        c=l.get_component_by_class(u.DirectionalLightComponent)
        if c and c.get_editor_property('mobility')!=u.ComponentMobility.MOVABLE:c.set_mobility(u.ComponentMobility.MOVABLE)
        l.set_actor_rotation(u.Rotator(roll=0.,pitch=r['pitch'],yaw=r['yaw']),False)
        rr=l.get_actor_rotation();sun=[round(rr.pitch,2),round(rr.yaw,2)]
    report.setdefault('sun',[]).append(dict(asked=r,read=sun))
def mids():
    out=[]
    for p in patches:
        m=p.get_editor_property('mesh_material')
        if m:out.append(m)
    return out
SAVED={}
import live_mud_style as _lms
KNOWN={'SlideUV':_lms.LM1_SCALARS['SlideUV'],'FreshWet':_lms.LM1_SCALARS['FreshWet'],'MudDiagnostic':0.0}
def set_param(name,value):
    for m in mids():
        key=(m.get_name(),name)
        if key not in SAVED:SAVED[key]=KNOWN[name]   # MW1b: restored to the material's known default (neither the MID's read nor the editor default read gave it back)
        m.set_scalar_parameter_value(name,value)
def restore_param(name):
    for m in mids():
        key=(m.get_name(),name)
        if key in SAVED:m.set_scalar_parameter_value(name,SAVED.pop(key))
def water(visible):
    for p in patches:
        w=p.get_editor_property('water_mesh')
        if w:w.set_visibility(visible,False)
def subsystem():
    cls=getattr(u,'GTMudWaterSubsystem',None)
    return next((o for o in u.ObjectIterator(cls) if o.get_outer()==world),None) if cls else None

def water_cells(name,x0,x1,y0,y1):
    # The rut water's cells in a world box now (depth over 0.3 cm: the table and the weather's lift against the surface), as
    # [x, y, water z] for the sampler's projected water mask (a picture-difference mask caught the grass and the capture noise).
    out=[]
    for p in patches:
        if p.bounds_max.x<x0 or p.bounds_min.x>x1 or p.bounds_max.y<y0 or p.bounds_min.y>y1:continue
        lo=u.Vector2D(p.bounds_min.x,p.bounds_min.y);hi=u.Vector2D(p.bounds_max.x,p.bounds_max.y)
        hs=list(mud.mud_cell_heights_cm(lo,hi));nx=mud.mud_cells_across(lo,hi)
        if not hs or nx<=0:continue
        ny=len(hs)//nx;cx=(hi.x-lo.x)/nx;cy=(hi.y-lo.y)/ny;table=p.water_table_cm+p.water_lift_cm
        for j in range(ny):
            y=lo.y+(j+.5)*cy
            if y<y0 or y>y1:continue
            for i in range(nx):
                d=table-hs[j*nx+i]
                if d<=0.3:continue
                x=lo.x+(i+.5)*cx
                if x0<=x<=x1:out.append([round(x,1),round(y,1),round(ground(x,y)+table,1)])
        report.setdefault('water_cell_cm',round(cx,2))
    report.setdefault('water_cells',{})[name]=out
def wall_cells(name,x0,x1,y0,y1,deg=22.):
    # MW1b: the field's cells steeper than deg (central differences of the surface heights), [x, y, surface z], for the walls' mask.
    out=[];t=math.tan(math.radians(deg))
    for p in patches:
        if p.bounds_max.x<x0 or p.bounds_min.x>x1 or p.bounds_max.y<y0 or p.bounds_min.y>y1:continue
        lo=u.Vector2D(p.bounds_min.x,p.bounds_min.y);hi=u.Vector2D(p.bounds_max.x,p.bounds_max.y)
        hs=list(mud.mud_cell_heights_cm(lo,hi));nx=mud.mud_cells_across(lo,hi)
        if not hs or nx<=0:continue
        ny=len(hs)//nx;cx=(hi.x-lo.x)/nx;cy=(hi.y-lo.y)/ny
        for j in range(1,ny-1):
            y=lo.y+(j+.5)*cy
            if y<y0 or y>y1:continue
            for i in range(1,nx-1):
                x=lo.x+(i+.5)*cx
                if x<x0 or x>x1:continue
                gx=(hs[j*nx+i+1]-hs[j*nx+i-1])/(2*cx);gy=(hs[(j+1)*nx+i]-hs[(j-1)*nx+i])/(2*cy)
                if gx*gx+gy*gy>t*t:out.append([round(x,1),round(y,1),round(ground(x,y)+hs[j*nx+i],1)])
    report.setdefault('water_cells',{})[name]=out
def do(fn,label=None):steps.append(dict(kind='do',fn=fn,label=label))
def shot(name,cam,dump=False,warm=45):steps.append(dict(kind='shot',name=name,cam=cam,dump=dump,warm=warm))
def frames(n):steps.append(dict(kind='frames',n=n))
def motion(names,cam,gap=30):steps.append(dict(kind='motion',names=names,cam=cam,gap=gap))
def until(fn,cap_s,label):steps.append(dict(kind='until',fn=fn,cap=cap_s,label=label))

def image(name):
    p=OUT/(name+'.png');report['images'].append(str(p.as_posix()));return p
def issue(name,cam,dump):
    path=image(name)
    report['cameras'][name]=cam
    if dump:
        report['dumps'].append(dict(name=name,base=str((OUT/name).as_posix()),camera=dict(location=cam['eye'],target=cam['look'],fov=cam['fov']),wetness=WET))
    console('HighResShot %dx%d%s filename="%s"'%(VIEW[0],VIEW[1],' 0 0 0 0 0 1 1' if dump else '',path.as_posix()))
    GATE.expect(path)
    return path

WSAVED={}
def water_mids():
    out=[]
    for p in patches:
        w=p.get_editor_property('water_mesh')
        m=w.get_material(0) if w else None
        if m and isinstance(m,u.MaterialInstanceDynamic):out.append(m)
    return out
def wparam(name,value):
    for m in water_mids():
        key=(m.get_name(),name)
        if key not in WSAVED:WSAVED[key]=u.MaterialEditingLibrary.get_material_default_scalar_parameter_value(m.get_base_material(),name)
        m.set_scalar_parameter_value(name,value)
def wrestore():
    for m in water_mids():
        for (mn,name),v in list(WSAVED.items()):
            if mn==m.get_name():m.set_scalar_parameter_value(name,v)
    WSAVED.clear()
def plan_diag(P,cams):
    # MW1b item 4: what draws the swirl marks in the churned pool - the car churns the pool (the rings drive), then at the close
    # frame with the water shown, each of the water's layers off in turn, a reference right before each (the pool settles).
    until(lambda:gtime()>15.,60.,'settle')
    do(lambda:start_drive(P),'the drive');until(lambda:drive_tick(P),60.,'drive')
    do(lambda:diag_close(P),'pool layers')
def diag_close(P):
    x,y=P['x'],P['y'];ly=DRIVE.get('line_y',y);wy=ly+(79. if y>ly else -79.);out=1. if wy>ly else -1.;bx=x+300.
    eye=[bx+60.,wy+out*190.,surf(bx+60.,wy+out*190.)+110.];look=[bx-20.,wy,surf(bx-20.,wy)+5.]
    c=dict(eye=eye,look=look,fov=60.);report['close']=dict(wheel_y_cm=round(wy,1),camera=c)
    move.set_throttle_input(0.);car.set_actor_location(u.Vector(-1500.,0.,ground(-1500.,0.)+150.),False,True)
    set_sun(OWNER_SUN)
    for k,(label,params) in enumerate([('Mottle0',{'TurbidMottle':0.}),('Ruffle0',{'RuffleSlope1':0.,'RuffleSlope2':0.}),('Froth0',{'FrothAmount':0.}),
                                       ('Flecks0',{'FleckDensLo':0.,'FleckDensHi':0.}),('Drift0',{'DriftLoCm':0.,'DriftHiCm':0.}),('Ripple0',{'RippleSlope':0.})]):
        shot('MW1b_Pool_Ref%d'%k,c,warm=90 if k==0 else 30)
        do(lambda params=params:[wparam(n,v) for n,v in params.items()]);shot('MW1b_Pool_'+label,c,warm=30);do(wrestore)
    do(lambda:console('gt.Mud.WaterMotion 0'));shot('MW1b_Pool_Ref6',c,warm=30);shot('MW1b_Pool_Motion0',c,warm=30);do(lambda:console('gt.Mud.WaterMotion 1'))
    do(lambda:(report.update(ok=True),finish()),'finish')
# ---- Mud roads MRD1 (GT_MW_TAG mrd) --------------------------------------------------------------------------------------
def look_yaw(c):return math.degrees(math.atan2(c['look'][1]-c['eye'][1],c['look'][0]-c['eye'][0]))
def mrd_shot(name,c,sun=None,warm=90):
    # The sun behind the camera (25 deg off its view, 30 deg up) unless the reference has it otherwise.
    do(lambda c=c,sun=sun:set_sun(sun or dict(pitch=-30.,yaw=look_yaw(c)+25.)),name)
    shot(name,c,warm=warm)
def describe_roads(key):
    rows=[]
    for p in patches:
        try:rows.append(json.loads(p.describe_mud_road()))
        except Exception:rows.append(dict(error=traceback.format_exc().splitlines()[-1]))
    report[key]=[r for r in rows if r]
    return report[key]
def mrd_cams(P,x0,x1):
    road=next((r for r in report.get('mud_roads',[]) if r.get('churn_zones') is not None and x0-700.<=(r.get('churn_zones') or [[0.5*(x0+x1)]])[0][0]<=x1+700.),{})
    def at(x,y,h):return [x,y,surf(x,y)+h]
    def on(x,y):return [x,y,surf(x,y)]
    xc=0.5*(x0+x1);cams={}
    cams['MRD_Ref1']=dict(eye=at(x0+150.,90.,160.),look=on(x0+1900.,-30.),fov=70.)   # on foot, along the road over the tracks
    zs=road.get('churn_zones') or [[xc,0.,140.,300.]]
    zx,zy=zs[0][0],zs[0][1]
    cams['MRD_Ref2']=dict(eye=at(zx-420.,zy+170.,160.),look=on(zx+40.,zy),fov=65.)   # a churn zone and its clod field, on foot
    if P:cams['MRD_Ref3']=dict(eye=at(P['x']+260.,P['y']+20.,120.),look=[P['x']-260.,P['y'],ground(P['x'],P['y'])+P['table_cm']],fov=60.)   # down a deep rut with water
    cams['MRD_Ref4']=dict(eye=at(x1-100.,-70.,150.),look=on(x0+400.,40.),fov=70.)   # along the puddled tracks, the sky ahead in the puddles
    cams['MRD_Top']=dict(eye=at(xc-1300.,-1050.,2000.),look=on(xc,0.),fov=60.)   # 20 m up, 50 deg down: the braid
    return cams
CHASE={}
def start_chase(x0):
    x=x0-1200.;z=ground(x,0.)
    pc.possess(car);car.disable_input(pc)
    car.set_actor_location_and_rotation(u.Vector(x,0.,z+150.),u.Rotator(roll=0.,pitch=0.,yaw=0.),False,True)
    body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector())
    car.reset_driving_inputs();move.set_handbrake_input(False);move.set_brake_input(0.);move.set_target_gear(1,True)
    try:car.get_drivetrain().set_low_range(False);car.get_drivetrain().set_diff_lock(True)
    except Exception:pass
    # Ref5: a low sun ahead and to the left of the chase camera (the shadows come toward it; the spray against the light).
    set_sun(dict(pitch=-22.,yaw=145.))
    CHASE.clear();CHASE.update(t0=gtime(),shot=False,samples=[],x0=x0);GATE.start_dt()
def chase_cam():
    pos=car.get_actor_location();f=car.get_actor_forward_vector()
    return dict(eye=[pos.x-f.x*750.,pos.y-f.y*750.,pos.z+260.],look=[pos.x+f.x*500.,pos.y+f.y*500.,pos.z+30.],fov=60.)
def chase_tick():
    pos=car.get_actor_location();speed=car.get_velocity().length()/100.
    err=(math.degrees(math.atan2(0.-pos.y,650.))-car.get_actor_rotation().yaw+180)%360-180
    car.set_raw_steer(max(-.65,min(.65,err/24)))
    move.set_throttle_input(max(.35,min(1.,.65+(6.-speed)*.3)));move.set_brake_input(0.)
    c=chase_cam();aim(c)
    t=gtime()-CHASE['t0']
    if not CHASE['samples'] or t-CHASE['samples'][-1]['t_s']>=.25:
        CHASE['samples'].append(dict(t_s=round(t,2),x_cm=round(pos.x,1),y_cm=round(pos.y,1),kmh=round(speed*3.6,2)))
    if pos.x>CHASE['x0']+300.:GATE.ready(world,pc,warm=30)
    if not CHASE['shot'] and pos.x>=CHASE['x0']+1000. and GATE.ready(world,pc,warm=30):
        CHASE['shot']=True;CHASE['shot_kmh']=round(speed*3.6,2);issue('MRD_Ref5',c,False);return False
    if CHASE['shot'] and GATE.capturing():return False
    if CHASE['shot'] or t>45.:
        move.set_throttle_input(0.);move.set_brake_input(1.);move.set_handbrake_input(True)
        report['chase']=dict(samples=CHASE['samples'],shot_kmh=CHASE.get('shot_kmh'),reached_shot=CHASE['shot'],game_s=round(t,2),
                             fine_rates=fine_rates())
        return True
    return False
def fine_rates():
    try:return [round(car.get_spray().get_fine_rate(w,0),2) for w in range(4)]
    except Exception:return None
def park():
    move.set_throttle_input(0.);move.set_brake_input(1.)
    car.set_actor_location(u.Vector(-1500.,0.,ground(-1500.,0.)+150.),False,True)
def to_stage2():
    global STAGE,LEVEL,SPEC,phase,last
    save()
    try:u.EditorLevelLibrary.editor_end_play()
    except Exception:pass
    STAGE=2;LEVEL=MRD_LEVEL2;SPEC=MRD_SPEC2;phase='load';last=time.monotonic()
def plan_mrd(P,cams):
    # Stage 1 (L_MudVariants): the MW owner frame and its moving water (the gates), the MRD stills, the chase, the mud mask last.
    O=cams['owner'];W=cams['water']
    do(lambda:set_sun(OWNER_SUN),'owner sun')
    frames(30)
    until(lambda:gtime()>15.,60.,'settle')
    do(lambda:(water_cells('owner',P['x']-1500.,P['x']+450.,P['y']-400.,P['y']+400.),water_cells('water',P['x']-300.,P['x']+250.,P['y']-200.,P['y']+200.),
               wall_cells('owner_walls',P['x']-1500.,P['x']+450.,P['y']-400.,P['y']+400.)))
    shot('MW_After_OnFoot',O,warm=150)
    do(lambda:water(False));shot(PRE+'Water_NoWater',W);do(lambda:water(True))
    motion([PRE+'Water_t0',PRE+'Water_t05',PRE+'Water_t10'],W)
    describe_roads('mud_roads')
    mc=MRD_OLD.get('mrd_cameras') or mrd_cams(P,7500.,10000.);report['mrd_cameras']=mc   # MRD1b: MRD1's cameras when given
    for name in ['MRD_Ref1','MRD_Ref2','MRD_Ref3','MRD_Ref4','MRD_Top']:
        if name in mc and (not MRD_SHOTS or name in MRD_SHOTS):
            if name=='MRD_Ref4':
                # MRD1b item 1's gate: the water cells in MRD_Ref4's view (the sampler projects them).
                report['frames']['ref4']=mc[name];do(lambda:water_cells('ref4',7300.,10200.,-500.,500.))
            mrd_shot(name,mc[name])
    if MRD_CHASE:do(lambda:start_chase(7500.),'the chase');until(chase_tick,60.,'chase')
    do(park)
    do(lambda:set_sun(OWNER_SUN))
    do(lambda:set_param('MudDiagnostic',1.),'the mud mask');shot(PRE+'Dbg_MudMask',O,warm=60);do(lambda:restore_param('MudDiagnostic'))
    do(to_stage2,'L_MudDrive')
def plan_mrd2():
    # Stage 2 (L_MudDrive): its MudRoad's numbers and two stills.
    x0,x1=MRD_ROAD2
    until(lambda:gtime()>8.,30.,'settle 2')
    do(lambda:describe_roads('mud_roads2'))
    def at(x,y,h):return [x,y,surf(x,y)+h]
    def on(x,y):return [x,y,surf(x,y)]
    xc=0.5*(x0+x1)
    c1=dict(eye=at(x0+250.,90.,160.),look=on(x0+2000.,-30.),fov=70.)
    c2=dict(eye=at(xc-1300.,-1050.,2000.),look=on(xc,0.),fov=60.)
    old=MRD_OLD.get('mrd2_cameras') or {}   # MRD1b: MRD1's cameras when given
    c1=old.get('MRD_Ref1_MudDrive',c1);c2=old.get('MRD_Top_MudDrive',c2)
    report['mrd2_cameras']=dict(MRD_Ref1_MudDrive=c1,MRD_Top_MudDrive=c2)
    mrd_shot('MRD_Ref1_MudDrive',c1);mrd_shot('MRD_Top_MudDrive',c2)
    do(lambda:(report.update(ok=True),finish()),'finish')
def plan_steps(P,cams):
    if MRD:plan_mrd(P,cams);return
    O=cams['owner'];W=cams['water']
    do(lambda:set_sun(OWNER_SUN),'owner sun')
    frames(30)
    do(lambda:(water_cells('owner',P['x']-1500.,P['x']+450.,P['y']-400.,P['y']+400.),water_cells('water',P['x']-300.,P['x']+250.,P['y']-200.,P['y']+200.)))
    # MW1b: the owner set waits for game time 15 s (the first pictures of the earlier runs differed from the rest by 10.85/255:
    # the field still settling), then the walls (cells steeper than 22 deg) and the mud's own pixels (the Diagnostic shot).
    until(lambda:gtime()>15.,60.,'settle')
    do(lambda:(water_cells('owner',P['x']-1500.,P['x']+450.,P['y']-400.,P['y']+400.),wall_cells('owner_walls',P['x']-1500.,P['x']+450.,P['y']-400.,P['y']+400.)))
    shot({'before':'MW_Before_OnFoot','mw1':'MW1_OnFoot'}.get(TAG,'MW_After_OnFoot'),O,warm=150)
    shot(PRE+'Dbg_Repeat',O)   # the same frame again: the capture-to-capture floor for every difference below
    # The debug set at the same frame.
    dbg=PRE+'Dbg_'
    shot(dbg+'PomRef',O);do(lambda:console('gt.Mud.POM 0'),'POM 0');shot(dbg+'POM0',O);do(lambda:console('gt.Mud.POM 2'))
    if TAG!='before':
        do(lambda:console('gt.Mud.DeformDetail 0'),'DeformDetail 0');shot(dbg+'DeformDetail0',O);do(lambda:console('gt.Mud.DeformDetail 1'))
        do(lambda:console('gt.Mud.WaterMotion 0'),'WaterMotion 0');shot(dbg+'WaterMotion0',O);do(lambda:console('gt.Mud.WaterMotion 1'))
    do(lambda:water(False),'water hidden');shot(dbg+'NoWater',O);do(lambda:water(True))
    do(dump_on);shot(dbg+'Buffers',O,dump=True);do(dump_off)
    # The moving water.
    do(lambda:water(False));shot(PRE+'Water_NoWater',W);do(lambda:water(True))
    motion([PRE+'Water_t0',PRE+'Water_t05',PRE+'Water_t10'],W)
    if TAG!='before':
        do(lambda:console('gt.Mud.WaterMotion 0'));motion(['MW_Water_Motion0_t0','MW_Water_Motion0_t05'],W);do(lambda:console('gt.Mud.WaterMotion 1'))
    if TAG!='before':
        # The rings on settled water, the same water camera: three test rings 0.3 s apart at the puddle (UGTMudWaterSubsystem
        # EmitRingsForTest), the picture 0.7 s after the first; then gt.Mud.WaterRings 0 (every ring gone at once) the same frame.
        wz=W['look'][2]+0.6
        for k in range(3):
            do(lambda k=k:(subsystem().emit_rings_for_test(u.Vector(P['x']-20.+15.*k,P['y']+4.*k,wz),1) if subsystem() else None),'test ring %d'%k if k==0 else None)
            frames(18)
        frames(6);steps.append(dict(kind='shot',name='MW_Rings_Test',cam=W,dump=False,warm=1))
        do(lambda:console('gt.Mud.WaterRings 0'));shot('MW_Rings_Test_Off',W,warm=10);do(lambda:console('gt.Mud.WaterRings 1'))
    # The rings drive.
    # MW1b item 6: the rings frame on a Standard or Firm puddle at about 10 km/h (rings alive at the capture); then Deep's drive
    # (it churns the pool and the bank the close frames look at).
    R=find_puddle([('Firm',3000.,5500.),('Standard',7500.,10000.)],'rings_puddle_search');report['rings_puddle']=R
    do(lambda:start_drive(R,'rings',PRE+'Rings'),'the rings drive (%s)'%R['section'])
    until(lambda:drive_tick(R),60.,'rings drive')
    do(lambda:start_drive(P,'drive',PRE+'Rings_Deep'),'the Deep drive')
    until(lambda:drive_tick(P),60.,'drive')
    # The footsteps.
    do(lambda:start_walk(P),'the footsteps')
    until(lambda:walk_tick(P),20.,'walk')
    # The close mud.
    do(lambda:close_setup(P),'close mud')
    frames(20)
    steps.append(dict(kind='close'))

def dump_on():
    console('r.BufferVisualizationOverviewTargets %s'%TARGETS);console('r.SaveEXR.CompressionQuality 0');console('r.PostProcessingColorFormat 1')
def dump_off():console('r.PostProcessingColorFormat 0')

DRIVE={}
def start_drive(P,key='drive',name=None):
    x,y=P['x'],P['y']
    # The old rut pairs sit about +-79 cm round their line (the strips' tyre lanes): the car's centre one lane-half off the puddle.
    side=-1. if y>0 else 1.
    cy=y+side*79.
    z=ground(x+2000.,cy)
    pc.possess(car);car.disable_input(pc)
    car.set_actor_location_and_rotation(u.Vector(x+2000.,cy,z+150.),u.Rotator(roll=0.,pitch=0.,yaw=180.),False,True)
    body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector())
    car.reset_driving_inputs();move.set_handbrake_input(False);move.set_brake_input(0.);move.set_target_gear(1,True)
    try:car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
    except Exception:pass
    # The side camera on the puddle's side of the car, 6 m out, looking across at the puddle's rut; the sun behind it.
    wz=ground(x,y)+P['table_cm']
    cam=dict(eye=[x-50.,y-side*600.,wz+230.],look=[x-50.,y,wz+20.],fov=55.)
    set_sun(dict(pitch=SIDE_SUN['pitch'],yaw=90. if cam['eye'][1]<y else -90.))
    aim(cam)   # the side camera holds still through the drive (no cut at the shot)
    DRIVE.clear();DRIVE.update(line_y=cy,cam=cam,t0=gtime(),shot=False,samples=[],rings0=ring_counts(),key=key,name=name or PRE+'Rings',past=None);GATE.start_dt()
    report[key]=dict(line_y_cm=round(cy,1),start_x_cm=round(x+2000.,1),camera=cam,puddle=P)
def ring_counts():
    s=subsystem()
    if not s:return None
    try:return dict(wheels=s.get_rings_emitted(False),feet=s.get_rings_emitted(True),live=s.get_ring_live_particles())
    except Exception:return None
def drive_tick(P):
    pos=car.get_actor_location();speed=car.get_velocity().length()/100.
    err=(math.degrees(math.atan2(DRIVE['line_y']-pos.y,-650.))-car.get_actor_rotation().yaw+180)%360-180
    car.set_raw_steer(max(-.65,min(.65,err/24)))
    move.set_throttle_input(max(.15,min(1.,.42+(2.8-speed)*.25)));move.set_brake_input(.3 if speed>3.4 else 0.)
    front=pos.x-130.   # the front axle, about 1.3 m ahead of the car's origin (it drives -X)
    t=gtime()-DRIVE['t0']
    if not DRIVE['samples'] or t-DRIVE['samples'][-1]['t_s']>=.25:
        w=car.get_traction().wheels
        DRIVE['samples'].append(dict(t_s=round(t,2),x_cm=round(pos.x,1),y_cm=round(pos.y,1),kmh=round(speed*3.6,2),
                                     water_cm=[round(q.water_depth_m*100.,2) for q in w],rut=[bool(q.get_editor_property('bRutWater')) for q in w]))
    if front<P['x']+300.:GATE.ready(world,pc,warm=30)   # the scene on for the last 3 m (the rings render; CPU particles run anyway)
    # MW1b item 6: the shot once the front axle is 0.5 m past the puddle's centre and a ring is alive (or 2.5 m past, regardless).
    rc=ring_counts();alive=bool(rc and rc.get('live',0)>0)
    if not DRIVE['shot'] and front<=P['x']-50. and (alive or front<=P['x']-250.) and GATE.ready(world,pc,warm=30):
        DRIVE['shot']=True;DRIVE['shot_kmh']=round(speed*3.6,2);DRIVE['shot_counts']=rc
        issue(DRIVE['name'],DRIVE['cam'],False);DRIVE['shot_t']=t
        return False
    if DRIVE['shot'] and GATE.capturing():return False
    if DRIVE['shot'] or t>40.:
        move.set_throttle_input(0.);move.set_brake_input(1.);move.set_handbrake_input(True)
        s=subsystem();report[DRIVE['key']]['rings_describe']=s.describe_rings() if s and hasattr(s,'describe_rings') else None
        report[DRIVE['key']].update(samples=DRIVE['samples'],shot_kmh=DRIVE.get('shot_kmh'),counts_at_shot=DRIVE.get('shot_counts'),
                               counts_start=DRIVE['rings0'],counts_end=ring_counts(),game_s=round(t,2),reached_shot=DRIVE['shot'])
        return True
    return False

WALK={}
def start_walk(P):
    x,y=P['x'],P['y']
    move.set_throttle_input(0.);move.set_brake_input(0.);move.set_handbrake_input(True)
    try:
        ok=pc.exit_car()
    except Exception:ok=False
    ch=u.GameplayStatics.get_player_pawn(world,0)
    car.set_actor_location(u.Vector(-1500.,0.,ground(-1500.,0.)+150.),False,True)
    if not ok or ch is None or ch==car:
        report['walk']=dict(skipped='exit_car failed');WALK['skip']=True;return
    z=surf(x+300.,y)+100.
    ch.set_actor_location(u.Vector(x+300.,y,z),False,True);ch.set_actor_rotation(u.Rotator(roll=0.,pitch=0.,yaw=180.),False)
    WALK.update(ch=ch,t0=gtime(),counts0=ring_counts(),samples=[],shot=False,skip=False)
    side=1. if y<=0 else -1.
    WALK['cam']=dict(eye=[x-50.,y+side*450.,ground(x,y)+P['table_cm']+170.],look=[x-50.,y,ground(x,y)+P['table_cm']+30.],fov=55.)
    set_sun(dict(pitch=SIDE_SUN['pitch'],yaw=90. if WALK['cam']['eye'][1]<y else -90.));aim(WALK['cam'])
    report['walk']=dict(start_x_cm=round(x+300.,1),y_cm=round(y,1),camera=WALK['cam'])
def walk_tick(P):
    if WALK.get('skip'):return True
    ch=WALK['ch'];t=gtime()-WALK['t0']
    ch.add_movement_input(u.Vector(-1.,0.,0.),1.,False)
    pos=ch.get_actor_location()
    if not WALK['samples'] or t-WALK['samples'][-1]['t_s']>=.2:
        WALK['samples'].append(dict(t_s=round(t,2),x_cm=round(pos.x,1),speed_cms=round(ch.get_velocity().length(),1)))
    if pos.x<P['x']+60.:GATE.ready(world,pc,warm=20)
    if not WALK['shot'] and pos.x<=P['x']-60. and GATE.ready(world,pc,warm=20):
        WALK['shot']=True;issue(PRE+'Rings_Foot',WALK['cam'],False);WALK['counts_shot']=ring_counts();return False
    if WALK['shot'] and GATE.capturing():return False
    if WALK['shot'] or t>12. or pos.x<P['x']-300.:
        s=subsystem();report['walk']['rings_describe']=s.describe_rings() if s and hasattr(s,'describe_rings') else None
        report['walk'].update(samples=WALK['samples'],counts_start=WALK['counts0'],counts_at_shot=WALK.get('counts_shot'),counts_end=ring_counts(),game_s=round(t,2))
        ch.set_actor_location(u.Vector(-1500.,600.,ground(-1500.,600.)+120.),False,True)
        return True
    return False

def close_setup(P):
    global WET
    x,y=P['x'],P['y'];ly=DRIVE.get('line_y',y)
    # The car's rut on the puddle's side (its wheels ran at line_y +- 79): the bank 2 m from an eye beside it, 3 m behind the puddle.
    wy=ly+(79. if y>ly else -79.);out=1. if wy>ly else -1.
    bx=x+300.
    eye=[bx+60.,wy+out*190.,surf(bx+60.,wy+out*190.)+110.];look=[bx-20.,wy,surf(bx-20.,wy)+5.]
    report['close']=dict(wheel_y_cm=round(wy,1),camera=dict(eye=eye,look=look,fov=60.))
    set_sun(OWNER_SUN);WET=0.
    c=dict(eye=eye,look=look,fov=60.)
    do(lambda:water_cells('close',min(eye[0],look[0])-300.,max(eye[0],look[0])+300.,min(eye[1],look[1])-300.,max(eye[1],look[1])+300.))
    shot(PRE+'Mud_Close',c,warm=90);do(lambda:water(False));shot(PRE+'Mud_Close_NoWater',c)
    # The debug set again on the fresh rut's bank (moved mud, Fresh history), the water hidden (the churned pool settles from shot
    # to shot): the slide, the sheen, the parallax; a repeat for the floor.
    dbg=PRE+'Dbg_Close_'
    shot(dbg+'Repeat',c)
    do(lambda:console('gt.Mud.POM 0'));shot(dbg+'POM0',c);do(lambda:console('gt.Mud.POM 2'))
    if TAG!='before':
        do(lambda:console('gt.Mud.DeformDetail 0'));shot(dbg+'DeformDetail0',c);do(lambda:console('gt.Mud.DeformDetail 1'))
    shot(dbg+'Repeat2',c);do(lambda:water(True))
    if TAG!='before':
        # The moving water on the fresh rut's pool (deeper than the old track's puddle), WaterMotion 1 and 0.
        W2=dict(eye=[bx-40.,wy+out*170.,surf(bx-40.,wy)+170.],look=[bx-40.,wy,surf(bx-40.,wy)],fov=50.)
        report['frames']['water2']=W2
        do(lambda:water_cells('water2',bx-400.,bx+300.,wy-300.,wy+300.))
        motion(['MW_Water2_t0','MW_Water2_t05','MW_Water2_t10'],W2)
        do(lambda:console('gt.Mud.WaterMotion 0'));motion(['MW_Water2_Motion0_t0','MW_Water2_Motion0_t05'],W2);do(lambda:console('gt.Mud.WaterMotion 1'))
    do(dump_on)
    shot(PRE+'PBR_Close_Dry',c,dump=True)
    do(lambda:set_wet(1.),'test wetness 1');frames(120)
    do(lambda:water_cells('close_wet',min(eye[0],look[0])-300.,max(eye[0],look[0])+300.,min(eye[1],look[1])-300.,max(eye[1],look[1])+300.))
    shot(PRE+'PBR_Close_Wet',c,dump=True);shot(PRE+'Mud_Close_Wet',c)
    do(lambda:water(False));shot(PRE+'Mud_Close_Wet_NoWater',c);do(lambda:water(True))
    do(lambda:set_wet(0.))
    cx,cy=CALIB;cz=ground(cx,cy)
    shot(PRE+'PBR_Calib',dict(eye=[cx-150.,cy,cz+200.],look=[cx+30.,cy,cz],fov=50.),dump=True)
    do(dump_off)
    # MW1b: the owner frame's mud-instance toggles last - a parameter set on the patches' instances from Python did not come back on
    # its restore in the earlier runs (every picture after it stayed shifted), so nothing after these is measured.
    O=report['frames']['owner'];dbg=PRE+'Dbg_'
    do(lambda:set_sun(OWNER_SUN))
    shot(dbg+'EndRef',O,warm=90)   # the reference for the toggles below (the drive has changed the track since the base)
    do(lambda:set_param('SlideUV',0.),'SlideUV 0');shot(dbg+'SlideUV0',O);do(lambda:restore_param('SlideUV'))
    shot(dbg+'Repeat2',O)   # MW1b: after the slide's restore - against the base, whether the restore and the clock left the frame as it was
    do(lambda:set_param('FreshWet',0.),'FreshWet 0');shot(dbg+'FreshWet0',O);do(lambda:restore_param('FreshWet'))
    do(lambda:(set_param('SlideUV',0.),set_param('FreshWet',0.),console('gt.Mud.POM 0')),'all three off');shot(dbg+'AllOff',O)
    do(lambda:(restore_param('SlideUV'),restore_param('FreshWet'),console('gt.Mud.POM 2')))
    do(lambda:set_param('MudDiagnostic',1.),'the mud mask');shot(dbg+'MudMask',O);do(lambda:restore_param('MudDiagnostic'))
    do(lambda:(report.update(ok=True),finish()),'finish')
def set_wet(w):
    global WET
    WET=w;weather.set_wetness_for_test(w)

# ---- the tick ------------------------------------------------------------------------------------------------------------
def dump_written(name):
    return all((OUT/(name+'_'+t+'.exr')).exists() and (OUT/(name+'_'+t+'.exr')).stat().st_mtime>=cur.get('t_issued',0)-1. for t in TARGETS.split(','))
def run_step(now):
    global cur
    if cur is None:
        if not steps:finish();return
        cur=steps.pop(0);cur['t']=now;cur['f']=FRAME;cur['g']=gtime()
        if cur.get('label'):note(cur['label'])
    k=cur['kind']
    if k=='do':
        cur['fn']();cur=None
    elif k=='frames':
        if FRAME-cur['f']>=cur['n']:cur=None
    elif k=='shot':
        if 'issued' not in cur:
            aim(cur['cam'])
            if 'aimed' not in cur:cur['aimed']=FRAME   # the view settles (TSR history, Lumen) for warm frames after the camera moves
            if GATE.ready(world,pc,warm=cur['warm']) and FRAME-cur['aimed']>=cur['warm']:
                cur['issued']=FRAME;cur['t_issued']=time.time();issue(cur['name'],cur['cam'],cur['dump'])
        else:
            GATE.ready(world,pc)   # keep the scene on until the file lands
            if cur['dump']:
                if dump_written(cur['name']) or now-cur['t']>60.:cur=None
            elif not GATE.capturing():cur=None
    elif k=='motion':
        if 'f0' not in cur:
            aim(cur['cam'])
            if 'aimed' not in cur:cur['aimed']=FRAME
            if GATE.ready(world,pc,warm=60) and FRAME-cur['aimed']>=60:
                cur['f0']=FRAME;cur['i']=0;cur['frames']=[];cur['game']=[]
        if 'f0' in cur:
            GATE.ready(world,pc)
            i=cur['i']
            if i<len(cur['names']) and FRAME>=cur['f0']+i*cur['gap']:
                cur['frames'].append(FRAME);cur['game'].append(round(gtime(),4));issue(cur['names'][i],cur['cam'],False);cur['i']=i+1
            if cur['i']>=len(cur['names']) and not GATE.capturing():
                report.setdefault('motion',[]).append(dict(names=cur['names'],frames=cur['frames'],game_s=cur['game'],gap=cur['gap'],camera=cur['cam']));cur=None
    elif k=='until':
        if cur['fn']():cur=None
        elif gtime()-cur['g']>cur['cap']:note('%s hit its %.0f s game-time cap'%(cur['label'],cur['cap']));cur=None
    elif k=='close':
        cur=None   # close_setup queued the close steps after this marker

def tick(dt):
    global BUSY
    if BUSY:return
    BUSY=True
    try:body()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False
def body():
    global phase,last,world,pc,camera,car,move,mud,weather,spec,patches,FRAME
    now=time.monotonic();FRAME+=1
    if phase=='done':return
    if now-start>2400.:finish('the 40 min wall-clock cap');return
    GATE.tick(world)
    if phase=='steps':
        if weather is not None:weather.set_wetness_for_test(WET)
        rendering=cur is not None and cur['kind'] in ('shot','motion')
        GATE.idle(world,pc,keep=rendering)
        run_step(now);return
    if phase=='load':
        assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL);phase='loaded';last=now
    elif phase=='loaded' and now-last>5:
        lib=getattr(u,'GTPlayWindowLibrary',None)
        if not(lib and lib.request_play_in_new_window(VIEW[0],VIEW[1])):u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
        phase='warm';last=now
    elif phase=='warm' and now-last>20:
        world=u.EditorLevelLibrary.get_game_world()
        if world is None:
            if now-last>120:raise RuntimeError('PIE did not start')
            return
        pc=u.GameplayStatics.get_player_controller(world,0)
        cams=u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor);assert cams,'no CameraActor on '+LEVEL
        camera=cams[0];spec=u.load_asset(SPEC).spec
        mud=next(o for o in u.ObjectIterator(u.GTMudSubsystem) if o.get_outer()==world)
        weather=next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world)
        clear=weather.find_state('Clear')
        if clear:weather.set_state(clear,True)
        weather.set_wetness_for_test(0.)
        car=u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn)[0];move=car.get_chaos_movement()
        car.set_actor_location(u.Vector(-1500.,0.,ground(-1500.,0.)+150.),False,True)
        patches=list(u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch))
        if STAGE==2:   # MRD1: L_MudDrive's stage
            console('showhud');note('stage 2: %s'%LEVEL);plan_mrd2();phase='steps';last=now;return
        report['patches']=[dict(name=p.get_name(),variant=str(getattr(p,'mud_variant',None)),x=[p.bounds_min.x,p.bounds_max.x],y=[p.bounds_min.y,p.bounds_max.y],
                                table_cm=p.water_table_cm,lift_cm=p.water_lift_cm) for p in patches]
        fixed=os.environ.get('GT_MW_CAMERAS','').strip()
        if fixed:
            old=json.loads(Path(fixed).read_text());P=old['puddle'];cams_=old['frames']
        else:
            P=find_puddle();cams_=cameras(P)
        report['puddle']=P;report['frames']=cams_
        report['switches']={n:u.SystemLibrary.get_console_variable_int_value(n) for n in ('gt.Mud.POM','gt.Mud.PBR','gt.Mud.DeformDetail','gt.Mud.WaterMotion','gt.Mud.WaterRings')}
        report['has_subsystem']=subsystem() is not None
        console('showhud')   # the HUD off for the pictures
        note('puddle %s'%P)
        (plan_diag if TAG=='diag' else plan_steps)(P,cams_);phase='steps';last=now
handle=u.register_slate_post_tick_callback(tick)
