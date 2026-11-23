"""Replay the same recorded pickup trajectory with a locked driver-height camera."""
import bisect
import hashlib
import json
import os
from pathlib import Path

import unreal as u


def replay(world,pc,car,actors,road,ground,photo,out):
    source=Path(os.environ['GT_BEND_REPLAY'])
    original=json.loads(source.read_text())
    assert original['ok'] and original['station_end_m']>=72
    path=[]
    for row in original['path']:
        if not path or row[0]>path[-1][0]:
            path.append(row)
    stations=[r[0] for r in path]
    assert stations[0]<6 and stations[-1]>=72
    def position(s):
        i=max(1,min(bisect.bisect_left(stations,s),len(path)-1))
        a,b=path[i-1:i+1]
        t=(s-a[0])/(b[0]-a[0])
        return u.Vector(*[a[k]+(b[k]-a[k])*t for k in (1,2,3)])

    cam=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,
        u.Transform(location=position(6)),'RiverDriverReview')
    cam.camera_component.set_field_of_view(82)
    car.get_chaos_movement().set_handbrake_input(True)
    pc.set_view_target_with_blend(cam,0)
    # Move the streaming source with the camera. The original tyre dynamics are
    # already in the path; this comparison reviews scenery and the water opening.
    car.set_actor_hidden_in_game(True)
    views=[]
    snaps=[]
    def point_camera(eye,look):
        rotation=u.MathLibrary.find_look_at_rotation(eye,look)
        cam.set_actor_location_and_rotation(eye,rotation,False,True)
        return list(eye.to_tuple())+list(rotation.to_tuple())
    woodland_review=os.environ.get('GT_WOODLAND_FIELD_REVIEW')=='1'
    identify=os.environ.get('GT_WOODLAND_IDENTIFY')=='1'
    for i in range(0,0 if identify else 133,4 if woodland_review else 1):
        s=6+i*.5
        p=position(s)
        forward=position(s+1)-position(s-1)
        yaw=u.MathLibrary.find_look_at_rotation(p,p+forward)
        car.set_actor_location_and_rotation(p,u.Rotator(yaw=yaw.yaw),False,True)
        eye=p+u.Vector(0,0,155)
        look=position(s+4)+u.Vector(0,0,153)
        pose=point_camera(eye,look)
        for _ in range(3 if i else 24):
            yield
        yield from photo('motion-%03d'%i)
        views.append([s,*pose])
        snaps.append([i,s])
    def roadside(s,offset,h):
        x,y,_=road.at(s,offset)
        return u.Vector(x,y,ground(x,y)+h)
    for label,s,end,offset,height in [('early',19,34,0,130),('turn',41,58,-1,120),
                                      ('verge',53,61,5,55),('water',61,76,-1,115)]:
        eye,look=roadside(s,0,235),roadside(end,offset,height)
        car.set_actor_location(position(s),False,True)
        cam.camera_component.set_field_of_view(73)
        point_camera(eye,look)
        for _ in range(28):
            yield
        yield from photo(label)
    if woodland_review:
        root=Path(u.Paths.project_dir()).resolve()
        guide=json.loads((root/'Art/Export/LidarStudy/Place/prepare.json').read_text())['captures']['Bush_track']
        x,y=guide['pos_cm'];tx,ty=guide['target_cm']
        w=[('bush-entry',(x,y),(tx,ty),160,140),('bush-interior',(x,y),(x+820,y-420),165,70),
           ('bush-downhill',(tx,ty),(tx-(tx-x)*.6,ty-(ty-y)*.6),160,100)]
        for label,(x,y),(tx,ty),h,eh in w:
            p=u.Vector(x,y,ground(x,y)+h);look=u.Vector(tx,ty,ground(tx,ty)+eh)
            car.set_actor_location(p,False,True);point_camera(p,look)
            for _ in range(100):yield
            yield from photo(label);views.append([label,*p.to_tuple(),*look.to_tuple()])
            if label=='bush-interior':
                from woodland_isolation import inspect_floor
                inspect_floor(p,look,ground,root,out,world)
            if label=='bush-interior' and os.environ.get('GT_WOODLAND_IDENTIFY')=='1':
                from woodland_isolation import isolate
                yield from isolate(u.GameplayStatics.get_all_actors_of_class(world,u.Actor),photo,out,p)
    tree=next(c for a in actors for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
              if 'ForestAccessPaintedTree' in map(str,c.component_tags))
    note=dict(ok=True,view='Recorded driver-height replay',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              station_start_m=6,station_end_m=72,driven_tree=tree.static_mesh.get_path_name(),
              river_floor_present=any(c.static_mesh and c.static_mesh.get_name().startswith('SM_RiverFloor_')
                   for a in actors for c in a.get_components_by_class(u.StaticMeshComponent)))
    for name,obj in [('motion',snaps),('camera-poses',views),('drive',note)]:
        (out/(name+'.json')).write_text(json.dumps(obj))
