"""Compose a driving sightline with native shrubs, low banks and baked forest-floor beds."""
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import unreal as u
from bend_layout import CLEAR, Road
from forest_floor import clamp, mix
from lidar_grounding import GroundSampler
from preview_erosion_bank_meshes import build_tile

V = u.Vector
TAG = 'ForestAccessRiverReveal'


def install(ctx, report, refit=False):
    rows = ctx.actors()
    road = Road(json.loads((Path(__file__).parent/'drive-route.json').read_text()))
    terrain = GroundSampler(next(a for a in rows if isinstance(a, u.GTProceduralGround)))
    water = next(a for a in rows if isinstance(a, u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
    rng = random.Random(24038)
    # A local segment index makes footprint clearance cheap enough to test every vertex.
    network = defaultdict(list)
    for a in rows:
        if not isinstance(a, u.GTProceduralRoad):
            continue
        pts = ctx.road_samples(a).points
        for p,q in zip(pts,pts[1:]):
            ax,ay = p[:2]
            dx,dy = q[0]-ax,q[1]-ay
            length2 = dx*dx+dy*dy
            if length2 < .01:
                continue
            for i in range(math.floor((min(ax,q[0])-900)/1000), math.floor((max(ax,q[0])+900)/1000)+1):
                for j in range(math.floor((min(ay,q[1])-900)/1000), math.floor((max(ay,q[1])+900)/1000)+1):
                    network[i,j].append((ax,ay,dx,dy,length2))

    def clear(x,y,radius=0):
        for ax,ay,dx,dy,length2 in network.get((math.floor(x/1000),math.floor(y/1000)),()):
            t = clamp(((x-ax)*dx+(y-ay)*dy)/length2)
            if (x-ax-t*dx)**2+(y-ay-t*dy)**2 < (100*CLEAR+radius)**2:
                return False
        return True

    def wet(x,y):
        xy = u.Vector2D(x,y)
        return water.covers(xy) and terrain.height(x,y) < water.surface_cm_at(xy)+5

    # Locate the *opposite* waterline along a fan of view rays from the last dry bend.
    # Stands to either side of the centre leave the middle slope visible through the gap.
    ex,ey,yaw = road.at(61)
    heading = math.radians(yaw)
    banks = []
    for angle in (-72,-52,-33,-16,0,18,36,54,75):
        a = heading+math.radians(angle)
        dx,dy = math.cos(a),math.sin(a)
        wet_length = 0
        for distance in range(100,12501,100):
            x,y = ex+distance*dx,ey+distance*dy
            if wet(x,y):
                wet_length += 1
            elif wet_length >= 5:
                # Retreat onto dry land, keeping a wet toe below the visible rock bands.
                bx,by = x+dx*250,y+dy*250
                if clear(bx,by,170) and not wet(bx,by) and all(math.hypot(bx-p[0],by-p[1])>560 for p in banks):
                    banks.append((bx,by,a))
                break
            else:
                wet_length = 0
    if len(banks)<2:
        raise ValueError('Could not locate two separated stretches of far bank: '+str(banks))

    # Alternate tall, enclosed shoulders with low verges. At the turn the low
    # side opens towards the river while the closer stand passes beside the car.
    beds = []
    for s,d,length,width in [(8,-6.8,5.3,2.4),(12,7.4,7.2,2.6),
            (21,-6.5,7.8,2.7),(28,7.7,6.5,3),(35,-7.4,7.5,3.2),
            (42,8.2,8.5,3.3),(49,-6.8,7.6,2.9),(54,7.7,8.0,2.8),
            (61,7.3,6.1,2.7),(64,-7.5,5.8,2.6)]:
        x,y,h = road.at(s,d)
        beds.append((x,y,math.radians(h)+.13*math.copysign(1,d),length,width))
    for x,y,a in banks:
        beds.append((x,y,a+math.pi/2,6.8,3.5))
    shoulder_count=10
    if refit:
        for s,d,length,width in [(18,4.55,6.0,1.35),(24,-4.65,5.7,1.40),(39,-4.8,6.0,1.6),
                (46,4.6,6.8,1.40),(53,-4.7,5.1,1.4),(59,4.45,5.3,1.15)]:
            x,y,h=road.at(s,d)
            beds.append((x,y,math.radians(h),length,width))

    x0,y0,_ = road.at(47)
    z0 = terrain.height(x0,y0)
    def part():
        return dict(origin=(x0/100,y0/100,z0/100),v=[],c=[],uv=[],t=[])
    floor,plants = part(),part()
    def point(p,x,y,z,c,uv):
        p['v'].append(((x-x0)/100,(y-y0)/100,(z-z0)/100))
        p['c'].append(c)
        p['uv'].append(uv)
        return len(p['v'])-1
    def face(p,a,b,c):
        q,r,s = [p['v'][v] for v in (a,b,c)]
        cross = (r[0]-q[0])*(s[1]-q[1])-(r[1]-q[1])*(s[0]-q[0])
        p['t'].append((a,c,b) if cross>0 else (a,b,c))

    def sample(b,t,v,phase):
        x,y,a,length,width = b
        # Curved asymmetric cross sections; cut both ends below the underlying relief.
        width_factor = max(.03,1-t*t)**.54
        across = width*(v*width_factor+.21*math.sin(3*t+phase)) * 100
        along = t*length*100
        xx=x+along*math.cos(a)-across*math.sin(a)
        yy=y+along*math.sin(a)+across*math.cos(a)
        interior=max(0.,1-v*v)*width_factor
        height=(33+14*math.sin(3.1*t+phase)+11*math.sin(5*v-2*t))*interior-9
        return xx,yy,terrain.height(xx,yy)+height,interior

    fans = flecks = 0
    for j,b in enumerate(beds):
        phase=rng.uniform(-math.pi,math.pi)
        opposite = shoulder_count <= j < shoulder_count+len(banks)
        grid={}
        for i in range(25):
            for k in range(11):
                t,v=i/12-1,k/5-1
                x,y,z,m=sample(b,t,v,phase)
                if refit and opposite:
                    continue
                if not clear(x,y,50) or wet(x,y):
                    continue
                pigment=clamp(.20+.52*m+.26*math.sin(t*3-v*1.5+phase))
                grid[i,k]=point(floor,x,y,z,(.2,pigment,.12),(x/148,y/148))
        for i,k in grid:
            for keys in [((i,k),(i+1,k),(i,k+1)),((i+1,k),(i+1,k+1),(i,k+1))]:
                if all(key in grid for key in keys):
                    face(floor,*[grid[key] for key in keys])
        # The same broad sweep selects olive or straw across neighbouring fans.
        # Fold the blades and litter into lit and shaded planes with real parallax.
        for n in range(116):
            t,v=rng.uniform(-.95,.95),rng.uniform(-.88,.88)
            x,y,z,m=sample(b,t,v,phase)
            if not clear(x,y,85) or wet(x,y):
                continue
            z=max(terrain.height(x,y)+1,z)
            if refit and opposite:
                z=terrain.height(x,y)+1
            sweep=.5+.5*math.sin(2.8*t-1.4*v+phase)
            if n<76 and m>.27 and sweep>.23:
                fans+=1
                tip=mix((.074,.122,.042),(.23,.217,.078),sweep*.87)
                root=mix((.025,.049,.022),(.080,.076,.032),sweep*.77)
                direction=b[2]+.7*math.sin(3*t+phase)
                for blade in range(rng.randint(7,12)):
                    ang=direction+rng.uniform(-1.9,1.9)
                    dx,dy=math.cos(ang),math.sin(ang)
                    h=rng.uniform(28,69)*(1.05-.3*sweep)
                    reach=h*rng.uniform(.48,1.25)
                    w=rng.uniform(2.5,5.5)
                    bx,by=x+rng.uniform(-9,9),y+rng.uniform(-9,9)
                    def leaf(f,s,zoff,col):
                        return point(plants,bx+dx*reach*f-dy*w*s,by+dy*reach*f+dx*w*s,
                                     z-3+h*zoff,col,(2.5,f))
                    ids=[leaf(0,-.4,0,root),leaf(0,.4,0,root),
                         leaf(.30,-1,.60,mix(root,tip,.60)),leaf(.30,0,.68,mix(root,tip,.75)),
                         leaf(.30,1,.57,mix(root,tip,.51)),leaf(1,0,1,tip)]
                    for tri in [(0,2,3),(0,3,1),(1,3,4),(2,5,3),(3,5,4)]:
                        face(plants,*[ids[i] for i in tri])
            else:
                for _ in range(3):
                    bx=x+rng.uniform(-23,23);by=y+rng.uniform(-23,23)
                    if wet(bx,by) or not clear(bx,by,17):
                        continue
                    bz=terrain.height(bx,by)+max(2,z-terrain.height(x,y))+1
                    ang=b[2]+rng.uniform(-2.2,2.2)
                    dx,dy=math.cos(ang),math.sin(ang)
                    length=rng.uniform(7,16);width=length*rng.uniform(.28,.49)
                    col=mix((.073,.047,.028),(.235,.152,.064),rng.uniform(.08,.90))
                    ids=[point(plants,bx+dx*length*s-dy*width*v,by+dy*length*s+dx*width*v,
                           bz+h,tuple(k*val for k in col),(2.6,0)) for s,v,h,val in
                           [(-1,0,0,.68),(0,-1,1,.85),(0,0,3,1),(0,1,0,.76),(1,0,2,.9)]]
                    for tri in [(0,1,2),(0,2,3),(1,4,2),(2,4,3)]:
                        face(plants,*[ids[i] for i in tri])
                    flecks+=1

    meshes={}
    for name,p,mat_name in [('RiverFloor',floor,'M_BendMossColonies'),('RiverBlades',plants,'M_BendMeadowBlades')]:
        sig=hashlib.sha256(json.dumps(p,separators=(',',':')).encode()).hexdigest()[:12]
        path=ctx.FOLDER+'/SM_'+name+'_'+sig
        mat=u.load_asset(ctx.FOLDER+'/'+mat_name)
        if ctx.E.does_asset_exist(path):
            mesh,pos=u.load_asset(path),V(x0,y0,z0)
        else:
            mesh,pos=build_tile([p],path,mat)
            assert ctx.E.save_loaded_asset(mesh,False)
        label=ctx.OWNER+'_'+name
        actor=next((a for a in rows if a.get_actor_label()==label),None) if refit else None
        actor=actor or ctx.new_actor(u.StaticMeshActor,label,pos)
        actor.modify()
        c=actor.static_mesh_component
        c.modify()
        c.set_static_mesh(mesh)
        c.set_material(0,mat)
        c.set_collision_profile_name('NoCollision')
        c.set_editor_property('cast_shadow',False)
        c.set_editor_property('receives_decals',False)
        c.set_editor_property('visible_in_ray_tracing',False)
        c.set_editor_property('ld_max_draw_distance',12500)
        meshes[label]=[path,len(p['t'])]

    if refit:
        # Turn the far lip into occasional exposed stones. The lower bank is
        # the continuous LiDAR surface; a second earth skin made a sharp dark line.
        owner=next(a for a in rows if a.get_actor_label()==ctx.OWNER)
        rock,=[c for c in owner.get_components_by_class(u.InstancedStaticMeshComponent) if TAG in map(str,c.component_tags)]
        rock.modify()
        if owner.root_component:
            owner.root_component.set_mobility(u.ComponentMobility.STATIC)
            if not rock.get_attach_parent():
                rock.attach_to_component(owner.root_component,'',u.AttachmentRule.KEEP_WORLD,
                                         u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,False)
        discard=[]
        for i in range(rock.get_instance_count()):
            tf=rock.get_instance_transform(i,True)
            p=tf.translation
            if not any(math.hypot(p.x-x,p.y-y)<850 for x,y,a in banks):
                continue
            if i%3!=1:
                discard.append(i)
                continue
            tf.scale3d=V(tf.scale3d.x*.76,tf.scale3d.y*.65,tf.scale3d.z*.65)
            tf=terrain.seat(rock.static_mesh,tf)
            tf.translation-=V(0,0,13)
            assert rock.update_instance_transform(i,tf,True,True,True)
        if discard:
            assert rock.remove_instances(sorted(discard,reverse=True))
        # Reuse the accepted bend's fern material and source shapes. The bank
        # side of the bend gets one near, shoulder-high silhouette; the interior
        # drops into low grass. Far-bank groups leave a wide central notch.
        source=next(c for c in owner.get_components_by_class(u.InstancedStaticMeshComponent)
                    if c.static_mesh and c.static_mesh.get_name()=='SM_NZ_TreeFern_Young')
        fern=source.static_mesh
        box=fern.get_bounding_box()
        wide=max(box.max.x-box.min.x,box.max.y-box.min.y)
        high=box.max.z-box.min.z
        arrangements=[]
        for s,d,w,h in [(18,7.6,3.1,2.2),(21,8.7,3.7,2.7),(32,-7.7,3.4,2.6),
                (36,-6.6,3.7,3.15),(38.5,-8.8,4.1,3.5),(41,-5.8,3.3,2.75),
                (44,-6.8,4.0,3.35),(46,-9.3,3.6,2.85),(49,-7.6,3.2,2.4),
                (51,8.8,3.3,2.75),(54,8.0,3.6,2.5),(56,10.8,3.2,2.7)]:
            x,y,hdir=road.at(s,d)
            arrangements.append((x,y,math.radians(hdir),w,h))
        for j,(x,y,a) in enumerate(banks):
            if j not in (0,1,len(banks)-1):
                continue
            for shift,w,h in [(-1.6,3.4,2.75),(.55,4.1,3.15),(2.8,3.0,2.2)]:
                arrangements.append((x+180*math.cos(a)-shift*100*math.sin(a),
                     y+180*math.sin(a)+shift*100*math.cos(a),a,w,h))
        ferns=[]
        for i,(x,y,a,w,h) in enumerate(arrangements):
            if wet(x,y) or not clear(x,y,50*w):
                continue
            tf=u.Transform(location=V(x,y,terrain.height(x,y)-box.min.z*h*100/high-4),
                 rotation=u.Rotator(yaw=math.degrees(a)+i*73),scale=V(w*100/wide,w*92/wide,h*100/high))
            ferns.append(tf)
        assert len(ferns)>=10
        c=u.GTVegetationSubsystem.add_tagged_instances(owner,fern,ferns,TAG+'FernStands','NoCollision',True)
        for i,mat in enumerate(source.get_materials()):
            c.set_material(i,mat)
        c.set_cull_distances(8000,13500)
        c.set_evaluate_world_position_offset(False)
        c.set_editor_property('visible_in_ray_tracing',False)
        return dict(meshes=meshes,stands=len(beds),stones=rock.get_instance_count(),fans=fans,
                    fallen_leaves=flecks,fern_stands=len(ferns),edges_version=2)

    # Recompose existing shrub and grass instances. Their material overrides, LODs,
    # collision, source IDs and total counts remain intact.
    excluded={(a,c,i) for a,c,i,_ in report['moved']}
    changed=[]
    totals=Counter()
    box=u.Box()
    xy=[(b[0],b[1]) for b in beds]
    box.set_editor_property('min',V(min(x for x,y in xy)-1400,min(y for x,y in xy)-1400,-100000))
    box.set_editor_property('max',V(max(x for x,y in xy)+1400,max(y for x,y in xy)+1400,100000))
    box.set_editor_property('is_valid',True)
    for a in sorted(rows,key=lambda a:a.get_actor_label()):
        label=a.get_actor_label()
        if not (label.startswith('LidarStudy_RS3_') or label in (
                'LidarStudy_FloraWorld_Understory','LidarStudy_FloraWorld_FernCover')):
            continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if not c.visible or c.hidden_in_game or not c.static_mesh or c.get_collision_enabled()!=u.CollisionEnabled.NO_COLLISION:
                continue
            ids=sorted(c.get_instances_overlapping_box(box,True))
            mesh=c.static_mesh
            bounds=mesh.get_bounding_box()
            shrub=any(word in mesh.get_name() for word in ('Coprosma','Shrubbery'))
            for i in ids:
                if (label,c.get_name(),i) in excluded:
                    continue
                old=c.get_instance_transform(i,True)
                p=old.translation
                near=[b for b in beds if math.hypot(p.x-b[0],p.y-b[1])<1250]
                if not near or (rng.random()>.82 and not shrub):
                    continue
                if shrub:
                    # Concentrate shrubs at the approach, outside of the apex and
                    # the two margins of the far view; route centre and exit stay low.
                    allowed=[b for j,b in enumerate(beds) if j in (0,1,2,4,5,7,10,len(beds)-1)]
                    near=[b for b in allowed if math.hypot(p.x-b[0],p.y-b[1])<2300]
                if not near:
                    continue
                b=min(near,key=lambda q:math.hypot(q[0]-p.x,q[1]-p.y)+rng.uniform(0,370))
                t,v=rng.uniform(-.87,.87),rng.uniform(-.76,.76)
                x,y,_,_=sample(b,t,v,0)
                factor=(rng.uniform(1.15,1.42) if shrub else rng.uniform(.82,1.07))
                sc=old.scale3d*factor
                radius=max(bounds.max.x-bounds.min.x,bounds.max.y-bounds.min.y)*max(sc.x,sc.y)*.54
                if not clear(x,y,radius) or wet(x,y) or math.hypot(x-report['hero'][0],y-report['hero'][1])<180:
                    continue
                tf=terrain.seat(mesh,u.Transform(location=V(x,y,0),rotation=old.rotation.rotator(),scale=sc),True)
                if totals[(label,c.get_name())]==0:
                    a.modify();c.modify()
                assert c.update_instance_transform(i,tf,True,True,True)
                totals[(label,c.get_name())]+=1
                changed.append((label,c.get_name(),i,list(tf.translation.to_tuple())))

    # Use the approved landmark geometry and its own normals. Flatten and bed
    # each run of strata into the terrain; retain the original landmark itself.
    landmark=next(a for a in rows if a.get_actor_label()==ctx.OWNER+'_Outcrop')
    source=landmark.static_mesh_component
    mesh=source.static_mesh
    bounds=mesh.get_bounding_box()
    size=bounds.max-bounds.min
    stones=[]
    groups=[(p[0],p[1],p[2],p[3]) for i,p in enumerate(beds) if i in (1,4,6,9) or i>=10]
    for x,y,a,length in groups:
        for i in range(3):
            along=(i-1)*length*35+rng.uniform(-35,35)
            cross=rng.uniform(-55,55)
            xx=x+math.cos(a)*along-math.sin(a)*cross
            yy=y+math.sin(a)*along+math.cos(a)*cross
            span=rng.uniform(245,415) if i!=1 else rng.uniform(385,550)
            if not clear(xx,yy,span*.55) or wet(xx,yy) or math.hypot(xx-report['hero'][0],yy-report['hero'][1])<260:
                continue
            sc=V(span/size.x,span*rng.uniform(.44,.70)/size.y,span*rng.uniform(.22,.32)/size.z)
            tf=terrain.seat(mesh,u.Transform(location=V(xx,yy,0),
                rotation=u.Rotator(yaw=math.degrees(a)+rng.uniform(-22,22)),scale=sc))
            tf.translation-=V(0,0,span*.075)
            stones.append(tf)
    assert len(stones)>=5 and len(changed)>=50,(len(stones),len(changed))
    owner=next(a for a in rows if a.get_actor_label()==ctx.OWNER)
    owner.modify()
    if owner.root_component:
        owner.root_component.set_mobility(u.ComponentMobility.STATIC)
    c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,stones,TAG,'NoCollision',True)
    for slot,m in enumerate(source.get_materials()):
        c.set_material(slot,m)
    c.set_cull_distances(9000,14500)
    c.set_evaluate_world_position_offset(False)
    c.set_editor_property('visible_in_ray_tracing',False)
    return dict(meshes=meshes,banks=banks,stands=len(beds),stones=len(stones),fans=fans,
                fallen_leaves=flecks,moved=changed,water_on_centreline=[s for s in range(2,80)
                if wet(*road.at(s)[:2])])


def verify(ctx,rows,r):
    named={a.get_actor_label():a for a in rows}
    for label,(path,triangles) in r['meshes'].items():
        c=named[label].static_mesh_component
        assert c.static_mesh.get_path_name().split('.')[0]==path and triangles>0
        assert c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION
    c,=[c for c in named[ctx.OWNER].get_components_by_class(u.InstancedStaticMeshComponent)
        if TAG in map(str,c.component_tags)]
    assert c.get_instance_count()==r['stones'] and c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION
    if 'fern_stands' in r:
        groups=[c for c in named[ctx.OWNER].get_components_by_class(u.InstancedStaticMeshComponent)
                if TAG+'FernStands' in map(str,c.component_tags)]
        assert len(groups)==1 and groups[0].get_instance_count()==r['fern_stands']
    cache={}
    for label,name,i,pos in r['moved']:
        key=(label,name)
        if key not in cache:
            cache[key]=next(c for c in named[label].get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name()==name)
        assert math.dist(cache[key].get_instance_transform(i,True).translation.to_tuple(),pos)<.15,key
