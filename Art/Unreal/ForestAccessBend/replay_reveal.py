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
    for i in range(133):
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
    tree=next(c for a in actors for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
              if 'ForestAccessPaintedTree' in map(str,c.component_tags))
    note=dict(ok=True,view='Recorded driver-height replay',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              station_start_m=6,station_end_m=72,driven_tree=tree.static_mesh.get_path_name(),
              river_floor_present=any(c.static_mesh and c.static_mesh.get_name().startswith('SM_RiverFloor_')
                   for a in actors for c in a.get_components_by_class(u.StaticMeshComponent)))
    for name,obj in [('motion',snaps),('camera-poses',views),('drive',note)]:
        (out/(name+'.json')).write_text(json.dumps(obj))
