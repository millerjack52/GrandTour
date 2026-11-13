"""Owner's first saved logging route: trial dressing and measurable bog checks."""
import bisect
import math
import json
from pathlib import Path
import unreal as u

VERSION='LT3'
DRESSING_VERSION='LT3c'
DESIGN_ID='fce56694-1591-406d-8ac5-75b330a90436'
KIT='/Game/GrandTour/Environment/NativePlants/v01'


def specification():
    return json.loads((Path(u.Paths.project_dir())/'Art/Export/LidarStudy/Place/logging_trial.json').read_text(encoding='utf-8'))


def route(roads):
    return next((r['authoring'] for r in roads if r.get('authoring',{}).get('id')==DESIGN_ID),None)


def at(path, station, across=0.):
    pts=path['points_cm'];cum=[0.]
    for a,b in zip(pts,pts[1:]):cum.append(cum[-1]+math.dist(a,b)/100)
    k=max(1,min(len(pts)-1,bisect.bisect_right(cum,station)))
    a,b=pts[k-1],pts[k];t=max(0.,min(1.,(station-cum[k-1])/(cum[k]-cum[k-1])))
    yaw=math.atan2(b[1]-a[1],b[0]-a[0]);x=a[0]+t*(b[0]-a[0])-math.sin(yaw)*across*100;y=a[1]+t*(b[1]-a[1])+math.cos(yaw)*across*100
    return x,y,math.degrees(yaw)


def dress(path, ground, spawn):
    placed=[]
    # Large river stones beside the tyre corridor; small embedded stones in it.
    for i,(s,off,size) in enumerate([(82,-2.5,110),(88,2.7,90),(124,-2.6,100),(148,2.5,120),(153,-2.6,85),(84,.2,24),(150,-.2,20)]):
        x,y,yaw=at(path,s,off);mesh=u.load_asset(KIT+'/SM_NZ_Boulder_'+('A' if i%2==0 else 'B'));assert mesh
        box=mesh.get_bounding_box();scale=size/max(box.max.x-box.min.x,box.max.y-box.min.y)
        z=ground(x,y)-box.min.z*scale-(box.max.z-box.min.z)*scale*.25
        a=spawn(u.StaticMeshActor,'LoggingDetail_rock_'+str(i),(x,y,z));a.static_mesh_component.set_static_mesh(mesh)
        a.set_actor_scale3d(u.Vector(scale,scale,scale));a.set_actor_rotation(u.Rotator(yaw=yaw+i*37),False)
        a.static_mesh_component.set_collision_profile_name('BlockAll');a.static_mesh_component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
        placed.append(dict(kind='river_rock',station_m=s,across_m=off,size_cm=size,position_cm=[x,y,z]))
    # Small local bar on the point between crossings, using the native cobble kit.
    for i,(s,off) in enumerate([(111,-2.5),(114,-2.9),(117,-2.5)]):
        x,y,yaw=at(path,s,off);mesh=u.load_asset(KIT+'/SM_NZ_CobbleBar');assert mesh
        box=mesh.get_bounding_box();scale=260/max(box.max.x-box.min.x,box.max.y-box.min.y)
        z=ground(x,y)-box.min.z*scale+1
        a=spawn(u.StaticMeshActor,'LoggingDetail_gravel_bank_'+str(i),(x,y,z));a.static_mesh_component.set_static_mesh(mesh)
        a.set_actor_scale3d(u.Vector(scale,scale,scale));a.set_actor_rotation(u.Rotator(yaw=yaw+15*i),False)
        a.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        placed.append(dict(kind='small_gravel_cobble_bank',station_m=s,across_m=off,position_cm=[x,y,z]))
    for i,item in enumerate(specification()['obstacles']):
        log=item['kind']=='log'
        name=KIT+'/SM_NZ_Log_'+('A' if item['variant']==0 else 'B') if log else '/Game/GrandTour/Mud/Chunks/SM_GT_MudChunk_'+str(item['variant'])
        mesh=u.load_asset(name);assert mesh,name
        body=mesh.get_editor_property('body_setup')
        assert len(body.get_editor_property('agg_geom').get_editor_property('convex_elems'))>0,('Movable obstacle needs simple hulls',name)
        box=mesh.get_bounding_box();scale=item['size_cm']/max(box.max.x-box.min.x,box.max.y-box.min.y)
        x,y,yaw=at(path,item['station_m'],item['across_m']);yaw+=item['yaw_offset']
        # Rest the long hull above its highest support sample, rather than burying
        # one end in a slope. Gravity settles it when play begins.
        angle=math.radians(yaw);half=item['size_cm']*.42
        support=max(ground(x+math.cos(angle)*d,y+math.sin(angle)*d) for d in (-half,0,half))
        if not log:
            # Sample the entire rotated footprint. A single longitudinal line
            # can start a small convex hull inside a steep shoulder; CCD cannot
            # recover a body that already overlaps the ground at initialization.
            support=max(ground(x+math.cos(angle)*dx-math.sin(angle)*dy,
                               y+math.sin(angle)*dx+math.cos(angle)*dy)
                        for dx in (box.min.x*scale,0,box.max.x*scale)
                        for dy in (box.min.y*scale,0,box.max.y*scale))
        z=support-box.min.z*scale+(10 if not log else 2)
        a=spawn(u.StaticMeshActor,'LoggingDetail_movable_'+str(i),(x,y,z));c=a.static_mesh_component
        c.set_mobility(u.ComponentMobility.MOVABLE);c.set_static_mesh(mesh)
        a.set_actor_scale3d(u.Vector(scale,scale,scale));a.set_actor_rotation(u.Rotator(yaw=yaw),False)
        c.set_collision_profile_name('PhysicsActor');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
        c.set_use_ccd(True)
        c.set_mass_override_in_kg('',item['mass_kg'],True);c.set_linear_damping(.6);c.set_angular_damping(1.2)
        if not log:
            material=u.load_asset('/Game/GrandTour/Materials/M_GT_MudChunk');assert material
            c.set_material(0,material);c.set_custom_primitive_data_float(0,(i*.61803398875)%1)
        c.set_simulate_physics(True)
        a.tags=['LidarLoggingMovable','LoggingLog' if log else 'LoggingMudClump']
        placed.append(dict(item,actor=a.get_actor_label(),mesh=name,position_cm=[x,y,z],simple_hulls=len(body.get_editor_property('agg_geom').get_editor_property('convex_elems')),simulates_physics=True,continuous_collision_detection=True))
    return placed


def verify_pools(author, sheet, path, ground):
    base=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/DA_WaterDomain');root=sheet.get_editor_property('water_domain')
    children=list(root.road_patches);original=list(base.road_patches)
    assert len(original)==3 and children[:3]==original and len(children)==4,'River/pond children must survive pool composition'
    pool=children[-1];samples=list(pool.samples);origin=pool.origin_cm;step=pool.cell_cm;w=pool.size_x
    wet=[]
    for i in range(len(samples)//4):
        if samples[4*i+1]>.005:
            wet.append(dict(x=origin.x+(i%w+.5)*step,y=origin.y+(i//w+.5)*step,z=samples[4*i],depth_cm=samples[4*i+1]*100))
    assert wet and len(wet)==author.road_pool_wet_samples,'No standing water generated'
    errors=[abs(p['z']-ground(p['x'],p['y'])-p['depth_cm']) for p in wet[::max(1,len(wet)//100)]]
    assert max(errors)<.2,('Pool does not follow collision bed',max(errors))
    bogs=[]
    for c in path['conditions']:
        if c.get('water_fill_cm',0)<=0:continue
        x,y,_=at(path,(c['start_metres']+c['end_metres'])/2)
        local=[p for p in wet if math.hypot(p['x']-x,p['y']-y)<(c['end_metres']-c['start_metres'])*50+200]
        assert len(local)>=48,('Bog has too little standing water',c['name'],len(local))
        deepest=max(local,key=lambda p:p['depth_cm'])
        assert deepest['depth_cm']<=c['water_fill_cm']+.1,('Bog exceeds its fill cap',c['name'],deepest)
        bogs.append(dict(name=c['name'],area_m2=len(local)*(step/100)**2,max_depth_cm=deepest['depth_cm'],probe=deepest))
    return dict(version=VERSION,base_children=[d.get_path_name() for d in original],pool_cells=len(wet),water_bed_max_error_cm=max(errors),bogs=bogs)


def repair_legacy_polish(refs, sheet):
    """Recover pools dropped by pre-LT2 Polish, using the saved immutable base."""
    author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
    if author.road_pool_wet_samples<=0:return None
    root=sheet.get_editor_property('water_domain')
    if len(root.road_patches)>3:return None
    before=author.road_pool_wet_samples;digest=author.output_digest
    assert author.rebuild(),author.last_message
    assert len(sheet.get_editor_property('water_domain').road_patches)==4
    assert author.road_pool_wet_samples==before,('Non-deterministic pool rebuild',before,author.road_pool_wet_samples)
    assert author.output_digest==digest,'Road terrain/soil changed during pool restoration'
    return dict(rebuilt=True,wet_cells_before=before,wet_cells_after=author.road_pool_wet_samples,terrain_soil_digest_unchanged=True)
