"""Install or verify the bounded forest-access study in the LiDAR editor world."""
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import sys
import traceback
import unreal as u

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(Path(u.Paths.project_dir()).resolve()/'Art/Unreal')]
import bend_layout as design
from lidar_grounding import GroundSampler

ROOT=Path(u.Paths.project_dir()).resolve()
BASE='/Game/GrandTour/ArtTests/LidarStudy'
MAP=BASE+'/L_LidarStudy'
FOLDER=BASE+'/ForestAccessBend'
OWNER='LidarStudy_ForestAccessBend_v1'
MAPFILE=ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
OUT=ROOT/'Saved/ForestAccessBend'
OUT.mkdir(parents=True,exist_ok=True)
A=u.get_editor_subsystem(u.EditorActorSubsystem)
L=u.get_editor_subsystem(u.LevelEditorSubsystem)
E=u.EditorAssetLibrary
M=u.MaterialEditingLibrary
SPACE=u.SplineCoordinateSpace.WORLD
V=u.Vector
MODE=os.environ.get('GT_BEND_STAGE','build')

def dump(name,value):
    p=OUT/(name+'.json')
    temp=p.with_suffix('.tmp')
    temp.write_text(json.dumps(value,indent=2),encoding='utf-8')
    temp.replace(p)

def actors():
    return list(A.get_all_level_actors())

def road_samples(road):
    spline=road.control_points
    length=spline.get_spline_length()/100.
    ds=list(range(0,math.ceil(length),2))+[length]
    return design.Road([tuple(spline.get_location_at_distance_along_spline(d*100,SPACE).to_tuple()) for d in ds],ds)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda:stream.read(4*1024*1024),b''):
            h.update(part)
    return h.hexdigest()

def save_backup():
    backup=OUT/'BeforeForestAccess.umap'
    current=digest(MAPFILE)
    if backup.exists():
        if digest(backup)!=current:
            raise RuntimeError('A different pre-pass backup exists. Use a fresh project copy.')
    else:
        tmp=backup.with_suffix('.partial')
        shutil.copyfile(MAPFILE,tmp)
        if digest(tmp)!=current:raise RuntimeError('Map backup did not match source.')
        tmp.replace(backup)
    return current

def local_components(rows, road):
    pts=[road.at(st) for st in range(design.START-2,design.END+3,2)]
    xs,ys,_=zip(*pts)
    box=u.Box()
    box.set_editor_property('min',V(min(xs)-1700,min(ys)-1700,-1000000))
    box.set_editor_property('max',V(max(xs)+1700,max(ys)+1700,1000000))
    box.set_editor_property('is_valid',True)
    trunks=[]; plants=[]; rocks=[]; rock_sources=[]
    for a in rows:
        label=a.get_actor_label()
        if label not in ['LidarStudy_FloraWorld_'+s for s in ('Canopy','Midstory','Understory','FernCover','Rocks')]:continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=c.static_mesh
            if not mesh or not c.visible or c.hidden_in_game:continue
            name=mesh.get_name()
            if label.endswith('_Rocks'):
                rock_sources.append(c)
            for i in c.get_instances_overlapping_box(box,True):
                tf=c.get_instance_transform(i,True)
                p=tf.translation
                if label.endswith(('_Canopy','_Midstory')):
                    trunks.append((p.x,p.y))
                    continue
                dist,st,off=road.nearest(p.x,p.y)
                if not(design.START<=st<=design.END and 2.30<=dist<=12.):continue
                if c.get_collision_enabled()!=u.CollisionEnabled.NO_COLLISION:continue
                entry=(c,int(i),tf,st,off)
                if label.endswith('_Rocks'):
                    if 'Large_Rock' in name:rocks.append(entry)
                elif label.endswith('_FernCover') or '_Grass_' in name or '_Ferns_' in name:
                    plants.append(entry)
    return trunks,plants,rocks,rock_sources

def survey():
    rows=actors()
    road=road_samples(next(a for a in rows if isinstance(a,u.GTProceduralRoad) and 'Logging mud track' in a.get_actor_label()))
    x,y,_=road.at(49)
    box=u.Box()
    box.set_editor_property('min',V(x-3200,y-3200,-100000))
    box.set_editor_property('max',V(x+3200,y+3200,100000))
    box.set_editor_property('is_valid',True)
    found=[]
    for a in rows:
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if not c.static_mesh or not c.visible or c.hidden_in_game:continue
            ids=c.get_instances_overlapping_box(box,True)
            if ids:found.append([a.get_actor_label(),c.static_mesh.get_name(),len(ids),str(c.get_collision_enabled()),
                                 [m.get_name() if m else '' for m in c.get_materials()]])
    dump('survey',found)

def make_decal():
    tex_path=FOLDER+'/T_ForestAccessFloor'
    if not E.does_asset_exist(tex_path):
        task=u.AssetImportTask()
        for k,v in dict(filename=str(OUT/'T_ForestAccessFloor.tga'),destination_path=FOLDER,
                        automated=True,save=True,replace_existing=False).items():
            task.set_editor_property(k,v)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(tex_path)
    assert tex,tex_path
    mat=u.load_asset(FOLDER+'/M_ForestAccessFloor')
    if mat:return mat
    mat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_ForestAccessFloor',FOLDER,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    texnode=M.create_material_expression(mat,u.MaterialExpressionTextureSample,-340,0)
    texnode.set_editor_property('texture',tex)
    # Pigment alone leaves the existing near normals, roughness and ruts intact.
    assert M.connect_material_property(texnode,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    assert M.connect_material_property(texnode,'A',u.MaterialProperty.MP_OPACITY)
    errors=M.recompile_material(mat)
    assert not errors,str(errors)
    assert E.save_loaded_asset(mat,False)
    return mat

def new_actor(cls,label,p,rot=None):
    a=A.spawn_actor_from_class(cls,p,rot or u.Rotator())
    assert a,label
    a.set_actor_label(label)
    a.tags=[*a.tags,u.Name(OWNER)]
    a.set_folder_path('LiDAR/Forest access bend')
    return a

def forest_layers(owner,road,terrain,roads,trunks,hero,dry):
    """Seat loose forest-floor geometry and layered fern colonies outside the wheel line."""
    kit='/Game/GrandTour/Environment/NativePlants/v01/'
    rng=random.Random(5782)
    placements={}
    def place(name,x,y,width,flatten=1.,burial=0.,living=False,yaw=None):
        mesh=u.load_asset(kit+'SM_NZ_'+name)
        if not mesh:raise RuntimeError('Missing native forest mesh '+name)
        radius=width*.5
        if not dry(x,y) or min(r.nearest(x,y)[0] for r in roads)<design.CLEAR+radius:return
        if living and any(math.hypot(x-tx,y-ty)<32 for tx,ty in trunks):return
        box=mesh.get_bounding_box()
        scale=100*width/max(box.max.x-box.min.x,box.max.y-box.min.y)
        heading=yaw if yaw is not None else rng.uniform(-180,180)
        tf=u.Transform(location=V(x,y,0),rotation=u.Rotator(yaw=heading),scale=V(scale,scale,scale*flatten))
        fitted=terrain.seat(mesh,tf,living)
        fitted.translation+=V(0,0,-burial)
        placements.setdefault(name,[]).append(fitted)
    # Broad, uneven fern beds on both sides, with two gaps on the inside.
    # Carry patches from the shoulder into the woods. Scale in metres by the
    # actual mesh bounds, so other versions of the native kit retain their size on site.
    for j,(st,off) in enumerate((*design.COLONIES,(43,10.7),(53,13.6))):
        side=math.copysign(1,off)
        for k,(along,across,width) in enumerate(((-1.3,-.55,1.45),(.05,.4,2.0),(.8,1.7,1.35),
                (-1.7,3.3,1.65),(1.2,4.6,1.8),(.2,6.0,1.45))):
            x,y,_=road.at(st+along+rng.uniform(-.4,.4),off+side*(across+rng.uniform(-.32,.32)))
            if math.hypot(x-hero.x,y-hero.y)<145:continue
            place('Kiokio_B' if k in (1,3) else 'CrownFern_B',x,y,width,living=True)
        if j in (1,3,5,6):
            x,y,_=road.at(st+1.6,off+side*(5.4+j*.18))
            place('TreeFern_Young',x,y,2.8+j*.09,living=True)
    # Trace root forms outward from a subset of actual stems and let them
    # disappear beneath moss or litter. Keep each root under a metre high.
    used=[]
    for tx,ty in sorted(set(trunks)):
        distance,st,_=road.nearest(tx,ty)
        if not (design.START+1<st<design.END-1 and 5.8<distance<15):continue
        if any(math.hypot(tx-x,ty-y)<400 for x,y in used):continue
        used.append((tx,ty))
        theta=rng.uniform(-math.pi,math.pi)
        x,y=tx+65*math.cos(theta),ty+65*math.sin(theta)
        place('RootTangle_A',x,y,1.9,.57,-2,yaw=math.degrees(theta))
        place('MossHummock_A',tx+29*math.cos(theta),ty+29*math.sin(theta),1.35,.48,-1)
    # Two small plants and a bedding of moss overlap the buried shoulder of the rock.
    for st,off,width in ((55.7,-7.9,1.2),(58.5,-7.7,1.4)):
        x,y,_=road.at(st,off)
        place('MossHummock_A',x,y,width,.50,-1)
        place('CrownFern_B',x+23,y-22,width*.84,living=True)
    summary={}
    bush=u.load_asset(BASE+'/MI_NZ_Foliage_Bush')
    for name,transforms in placements.items():
        mesh=u.load_asset(kit+'SM_NZ_'+name)
        c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,transforms,'ForestAccessHabitat','NoCollision',False)
        c.set_cull_distances(5000,8000)
        c.set_editor_property('visible_in_ray_tracing',False)
        c.set_editor_property('affect_distance_field_lighting',False)
        for i,slot in enumerate(mesh.static_materials):
            if bush and slot.material_interface and slot.material_interface.get_name()=='M_NZ_Foliage':
                c.set_material(i,bush)
        assert c.get_instance_count()==len(transforms)
        summary[name]=len(transforms)
    return summary

def painted_tree(owner,road,terrain,trunks,rows,dry):
    """Use the map's painted midstory and test branch-scale normals on one tree."""
    source=next(a for a in rows if a.get_actor_label()=='LidarStudy_FloraWorld_Midstory')
    choices=[c for c in source.get_components_by_class(u.InstancedStaticMeshComponent)
             if c.static_mesh and c.visible and not c.hidden_in_game]
    component=next(c for c in choices if c.static_mesh.get_name().endswith('_1'))
    mesh=component.static_mesh
    for station,offset in [(st,off) for off in (10.2,11.8,12.2,9.2,13.6) for st in (57,58,55,60,53)]:
        x,y,yaw=road.at(station,offset)
        if dry(x,y) and all(math.hypot(x-px,y-py)>120 for px,py in trunks):break
    else:raise RuntimeError('No dry, open space for the interior crown')
    height=460
    scale=height/(2*mesh.get_bounds().box_extent.z)
    transform=u.Transform(location=V(x,y,terrain.height(x,y)-4),rotation=u.Rotator(yaw=yaw+35),
                          scale=V(scale*1.09,scale*.93,scale))
    pilot=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,[transform],'ForestAccessPaintedTree','NoCollision',True)
    pilot.set_cull_distances(7500,11000)
    changes={}
    for i,base in enumerate(component.get_materials()):
        if not base:continue
        mat=base
        if 'Leaf' in base.get_name():
            mat=u.AssetToolsHelpers.get_asset_tools().create_asset('MI_ForestAccessLeaf',FOLDER,u.MaterialInstanceConstant,
                    u.MaterialInstanceConstantFactoryNew()) if not E.does_asset_exist(FOLDER+'/MI_ForestAccessLeaf') else u.load_asset(FOLDER+'/MI_ForestAccessLeaf')
            M.set_material_instance_parent(mat,base)
            params={str(p) for p in M.get_scalar_parameter_names(base)}
            for key,value in [('CrownVolume',.29),('MapCrownVolume',.33),('CrownCard',.86),('CrownOcclusion',.56)]:
                if key in params:
                    changes[key]=[M.get_material_instance_scalar_parameter_value(base,key),value]
                    M.set_material_instance_scalar_parameter_value(mat,key,value)
            assert changes,'Original LiDAR leaf inputs missing'
            M.update_material_instance(mat)
            assert E.save_loaded_asset(mat,False)
        pilot.set_material(i,mat)
    return dict(source=mesh.get_name(),position=list(transform.translation.to_tuple()),parameters=changes)

def floor_dressing(road,terrain,roads,trunks,dry):
    mat=make_decal()
    leaf=u.load_asset('/Game/GrandTour/Environment/NativePlants/v01/SM_NZ_LeafLitter_A')
    assert leaf
    root=new_actor(u.Actor,OWNER,V(0,0,0))
    if root.root_component:root.root_component.set_mobility(u.ComponentMobility.STATIC)
    layers=[];leaves=[]
    for j,(st,off,length,width) in enumerate(design.PATCHES):
        x,y,yaw=road.at(st,off)
        if not dry(x,y):continue
        ang=math.radians(yaw);tx,ty=math.cos(ang),math.sin(ang)
        # Along/across extents enclose the full rotated projector.
        for a in (-length,0,length):
            for b in (-width,0,width):
                xx=x+100*(a*tx-b*ty);yy=y+100*(a*ty+b*tx)
                if min(r.nearest(xx,yy)[0] for r in roads)<design.CLEAR:
                    raise ValueError('Ground projector enters the drive corridor')
        z=terrain.height(x,y)
        gx=(terrain.height(x+55,y)-terrain.height(x-55,y))/110
        gy=(terrain.height(x,y+55)-terrain.height(x,y-55))/110
        # Local X projects into the bank. Local Z follows the road tangent.
        rot=u.MathLibrary.make_rot_from_xz(V(gx,gy,-1),V(tx,ty,gx*tx+gy*ty))
        a=new_actor(u.DecalActor,OWNER+'_Floor_'+str(j),V(x,y,z),rot)
        dc=a.get_editor_property('decal')
        dc.set_editor_property('decal_size',V(28,width*100,length*100))
        dc.set_decal_material(mat)
        layers.append(a.get_actor_label())
        rng=random.Random(2701+j)
        for k in range(3):
            xx,yy,_=road.at(st+rng.uniform(-length*.6,length*.6),off+rng.uniform(-width*.48,width*.48))
            if not dry(xx,yy):continue
            if any(math.hypot(xx-xt,yy-yt)<70 for xt,yt in trunks):continue
            sc=rng.uniform(.65,1.)
            t=u.Transform(location=V(xx,yy,0),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=V(sc,sc,sc))
            fitted=terrain.seat(leaf,t,False)
            # Low mesh dressing needs its underside on the ground; the rock seating helper buries it 4 cm.
            fitted.translation+=V(0,0,4.5)
            leaves.append(fitted)
    if leaves:
        c=u.GTVegetationSubsystem.add_tagged_instances(root,leaf,leaves,'ForestAccessLitter','NoCollision',False)
        assert c and c.get_instance_count()==len(leaves)
        c.set_cull_distances(1800,3500)
    return root,layers,len(leaves)

def regroup(road,terrain,plants,trunks,hero,roads,dry):
    changes=[]
    local_roads=[r for r in roads if r is not road]
    for c,i,old,st,off in sorted(plants,key=lambda r:(r[0].get_name(),r[1])):
        kind='fern' if 'Fern' in c.static_mesh.get_name() else 'grass'
        seed=i+int.from_bytes(hashlib.sha256(c.get_name().encode()).digest()[:4],'little')
        for attempt in range(8):
            target,side=design.plant_target(st,off,seed+attempt*1009,kind)
            x,y,_=road.at(target,side)
            if not dry(x,y):continue
            if min([road.nearest(x,y)[0]]+[r.nearest(x,y)[0] for r in local_roads])<design.CLEAR:continue
            if math.hypot(x-hero[0],y-hero[1])<185 or any(math.hypot(x-xt,y-yt)<65 for xt,yt in trunks):continue
            copy_tf=u.Transform(location=V(x,y,0),rotation=old.rotation.rotator(),scale=old.scale3d)
            t=terrain.seat(c.static_mesh,copy_tf,True)
            changes.append((c,i,old,t))
            break
    return changes

def facing_the_track(report):
    """Choose a dry, visible rock shoulder and place the original painted fern in three beds."""
    rows=actors()
    root=next(a for a in rows if a.get_actor_label()==OWNER)
    if any('ForestAccessPaintedFerns' in map(str,c.component_tags)
           for c in root.get_components_by_class(u.InstancedStaticMeshComponent)):
        return report
    road_rows=[(a,road_samples(a)) for a in rows if isinstance(a,u.GTProceduralRoad)]
    road=next(s for a,s in road_rows if 'Logging mud track' in a.get_actor_label())
    terrain=GroundSampler(next(a for a in rows if isinstance(a,u.GTProceduralGround)))
    water=next(a for a in rows if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
    trunks,*_=local_components(rows,road)
    def clear(x,y,radius):
        return (not water.covers(u.Vector2D(x,y)) and min(r.nearest(x,y)[0] for _,r in road_rows)>=design.CLEAR+radius
                and all(math.hypot(x-tx,y-ty)>radius*100+30 for tx,ty in trunks))
    def visible(x,y,st,height):
        vx,vy,_=road.at(st)
        start=terrain.height(vx,vy)+165
        end=terrain.height(x,y)+height
        for j in range(1,12):
            t=j/12
            if terrain.height(vx+t*(x-vx),vy+t*(y-vy))>start+t*(end-start)-18:return False
        return True
    sites=[]
    for s in (48,50,52,54,46):
        for off in (5.35,6.0,6.8,7.5):
            x,y,yaw=road.at(s,off)
            if not clear(x,y,1.90):continue
            grade=math.hypot(terrain.height(x+80,y)-terrain.height(x-80,y),terrain.height(x,y+80)-terrain.height(x,y-80))/160.
            views=sum(visible(x,y,camera,90) for camera in (35,40,44))
            if views>=2:sites.append((grade+.12*(3-views)+.04*abs(s-50)+.05*(off-5.35),s,off,x,y,yaw))
    if not sites:raise ValueError("No visible dry rock site")
    _,stone_st,stone_off,x,y,yaw=min(sites)
    stone=next(a for a in rows if a.get_actor_label()==OWNER+'_Outcrop')
    mesh=stone.static_mesh_component.static_mesh
    box=mesh.get_bounding_box()
    sc=335/max(box.max.x-box.min.x,box.max.y-box.min.y)
    sz=178/(box.max.z-box.min.z)
    # Place the stone by the base of the actual mesh, with a level exposed face.
    # The far side naturally beds into the rising shoulder.
    t=u.Transform(location=V(x,y,terrain.height(x,y)-box.min.z*sz-36),
        rotation=u.Rotator(yaw=yaw-22),scale=V(sc,sc*.86,sz))
    stone.modify()
    stone.set_actor_transform(t,False,True)
    fern=u.load_asset('/Game/GrandTour/ArtTests/FloraTrail/Meshes/SM_Exact_fern')
    pigment=u.load_asset('/Game/GrandTour/ArtTests/FloraTrail/FernSurface/M_FernSurface')
    assert fern and pigment
    box=fern.get_bounding_box()
    spread=max(box.max.x-box.min.x,box.max.y-box.min.y)
    rng=random.Random(18031)
    placements=[]
    # Each colony has one broad leading frond and smaller plants climbing the bank.
    # The inner edge and the intervals between colonies stay open.
    for st,off in ((37,4.9),(stone_st,stone_off),(59,5.65),(61,9.8)):
        for ds,da,width in ((-2.2,-.15,1.62),(-1.15,.35,2.20),(-.35,1.25,1.85),
                            (1.30,.63,1.72),(1.85,1.65,2.05),(.4,2.55,1.48)):
            px,py,angle=road.at(st+ds,off+da)
            if not clear(px,py,width*.48) or math.hypot(px-x,py-y)<160:continue
            f=width*100/spread
            tf=u.Transform(location=V(px,py,terrain.height(px,py)-box.min.z*f-3),
                 rotation=u.Rotator(yaw=angle+rng.uniform(-180,180)),scale=V(f,f,f))
            placements.append(tf)
    if len(placements)<8:raise ValueError("Too few clear sites for the painted fern beds")
    comp=u.GTVegetationSubsystem.add_tagged_instances(root,fern,placements,'ForestAccessPaintedFerns','NoCollision',False)
    for i in range(comp.get_num_materials()):comp.set_material(i,pigment)
    comp.set_cull_distances(3200,5400)
    comp.set_editor_property('visible_in_ray_tracing',False)
    comp.set_editor_property('affect_distance_field_lighting',False)
    report.update(revision=2,hero=list(t.translation.to_tuple()),stone_station=stone_st,stone_offset=stone_off,
        painted_ferns=len(placements))
    return report

def recompose(report):
    rows=actors()
    road_rows=[(a,road_samples(a)) for a in rows if isinstance(a,u.GTProceduralRoad)]
    road=next(r for a,r in road_rows if 'Logging mud track' in a.get_actor_label())
    author=next(a for a in rows if isinstance(a,u.GTProceduralGround))
    ground=GroundSampler(author)
    water=next(a for a in rows if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
    from forest_floor import build
    art=build(road,ground,[r for _,r in road_rows],water,FOLDER,new_actor,OWNER,report['hero'])
    rock=next(a for a in rows if a.get_actor_label()==OWNER+'_Outcrop')
    from bend_rock import painted_rock
    stone=painted_rock(FOLDER)
    rock.modify();rock.static_mesh_component.modify()
    for slot in range(rock.static_mesh_component.get_num_materials()):rock.static_mesh_component.set_material(slot,stone)
    if report.get('revision',1)>=3:
        art['replaced']=report['woodland']['replaced']
        report.update(revision=4,woodland=art)
        return report
    x,y,_=road.at(49)
    box=u.Box()
    box.set_editor_property('min',V(x-3900,y-3900,-100000))
    box.set_editor_property('max',V(x+3900,y+3900,100000))
    box.set_editor_property('is_valid',True)
    removed={}
    for a in rows:
        label=a.get_actor_label()
        native=label.startswith(('LidarStudy_RS3_','LidarStudy_RS5_'))
        if not native and label!='LidarStudy_FloraWorld_Understory':continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if not c.static_mesh or not c.visible or c.hidden_in_game or c.get_collision_enabled()!=u.CollisionEnabled.NO_COLLISION:continue
            name=c.static_mesh.get_name()
            round_shrub='Coprosma' in name or 'Blooming_Shrubbery' in name
            spikes=any(k in name for k in ('VergeTussock','Rush_','Harakeke','Kiokio','CrownFern'))
            if not round_shrub and not (native and spikes):continue
            ids=[]
            for i in c.get_instances_overlapping_box(box,True):
                p=c.get_instance_transform(i,True).translation
                distance,st,offset=road.nearest(p.x,p.y)
                if not (27<=st<=69 and 3.25<distance<(19 if offset>0 else 13)):continue
                if water.covers(u.Vector2D(p.x,p.y)):continue
                # Keep a few shrubs on the far shoulder. Thin the repeated spikes
                # most heavily where the new folded fronds are closest to the driver.
                keep=(i*17+int(st*7))%10
                if not round_shrub and keep < (2 if distance<11 else 4):continue
                if round_shrub and distance>13 and keep<3:continue
                ids.append(i)
            if ids:
                a.modify();c.modify()
                assert c.remove_instances(sorted(ids,reverse=True))
                removed[name]=removed.get(name,0)+len(ids)
    art['replaced']=removed
    report.update(revision=4,woodland=art)
    return report

def middle_storey(report):
    """Frame the approach with two irregular groups of the calibrated F002 pine."""
    rows=actors()
    road_rows=[(a,road_samples(a)) for a in rows if isinstance(a,u.GTProceduralRoad)]
    road=next(r for a,r in road_rows if 'Logging mud track' in a.get_actor_label())
    terrain=GroundSampler(next(a for a in rows if isinstance(a,u.GTProceduralGround)))
    river=next(a for a in rows if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
    owner=next(a for a in rows if a.get_actor_label()==OWNER)
    if owner.root_component:owner.root_component.set_mobility(u.ComponentMobility.STATIC)
    trunks,*_=local_components(rows,road)
    kit='/Game/GrandTour/ArtTests/FloraTrail/'
    mesh=u.load_asset(kit+'PineTrial/Assets/SM_Exact_pine_f002')
    bark=u.load_asset(kit+'Woodland/v3/Materials/M_Woodland_bark_bd6a5687')
    needles=u.load_asset(kit+'Woodland/CrownForm/v3/M_Crown_b74ce8ab')
    assert mesh and bark and needles
    bounds=mesh.get_bounding_box()
    mesh_height=bounds.max.z-bounds.min.z
    mesh_width=max(bounds.max.x-bounds.min.x,bounds.max.y-bounds.min.y)
    # An uneven edge opens towards the boulder, then closes against the back of the bend.
    seeds=((34,-6.1,365),(37,-7.9,225),(40,-10.0,510),(45,-5.8,425),(47,-8.8,240),
           (49,8.8,370),(53,7.0,590),(55,10.8,315),(60,5.9,395),(62,9.3,545),(64,12.7,225))
    rng=random.Random(3104)
    placements=[]; sites=[]
    for station,offset,height in seeds:
        sz=height/mesh_height
        sc=sz*rng.uniform(.78,.90)
        radius=.5*mesh_width*sc
        for ds,extra in ((0,0),(1.2,.7),(-1.5,1.0),(0,2),(2,2),(-2,2),(0,3.8)):
            x,y,yaw=road.at(station+ds,offset+math.copysign(extra,offset))
            if river.covers(u.Vector2D(x,y)):continue
            if min(r.nearest(x,y)[0] for _,r in road_rows)<design.CLEAR+radius/100:continue
            if math.hypot(x-report['hero'][0],y-report['hero'][1])<radius+175:continue
            if any(math.hypot(x-a,y-b)<95 for a,b in trunks):continue
            if any(math.hypot(x-a,y-b)<135 for a,b in sites):continue
            sites.append((x,y))
            placements.append(u.Transform(location=V(x,y,terrain.height(x,y)-bounds.min.z*sz-5),
                rotation=u.Rotator(yaw=yaw+rng.uniform(-150,150)),scale=V(sc,sc,sz)))
            break
    assert len(placements)>=6,'The bend lacks enough dry, open sites for the pine groves'
    comp=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,placements,'ForestAccessPines','NoCollision',True)
    comp.set_material(0,bark);comp.set_material(1,needles)
    comp.set_evaluate_world_position_offset(False)
    comp.set_cull_distances(8500,12500)
    comp.set_editor_property('visible_in_ray_tracing',False)
    report.update(revision=5,pines=len(placements))
    return report

def meadow_crown(report):
    owner=next(a for a in actors() if a.get_actor_label()==OWNER)
    tree,=[c for c in owner.get_components_by_class(u.InstancedStaticMeshComponent)
           if 'ForestAccessPaintedTree' in map(str,c.component_tags)]
    slot=next(i for i,m in enumerate(tree.get_materials()) if m and m.get_name() in
              ('MI_ForestAccessLeaf','MI_BendCanopyVolume'))
    source=FOLDER+'/MI_ForestAccessLeaf'
    target=FOLDER+'/MI_BendCanopyVolume'
    mat=u.load_asset(target) if E.does_asset_exist(target) else E.duplicate_asset(source,target)
    parameters={'CrownVolume':.75,'MapCrownVolume':.70,'CrownCard':.49,'CrownOcclusion':.48}
    available={str(k) for k in M.get_scalar_parameter_names(mat)}
    assert parameters.keys()<=available,(parameters.keys()-available)
    for key,value in parameters.items():M.set_material_instance_scalar_parameter_value(mat,key,value)
    M.update_material_instance(mat)
    assert E.save_loaded_asset(mat,False)
    owner.modify();tree.modify();tree.set_material(slot,mat)
    report.update(revision=6,meadow_crown=parameters)
    return report

def other_tree_digest(rows, pilot):
    owners = ('LidarStudy_FloraWorld_Canopy', 'LidarStudy_FloraWorld_Midstory', OWNER)
    signature = hashlib.sha256()
    count = 0
    for a in sorted((a for a in rows if a.get_actor_label() in owners), key=lambda a: a.get_actor_label()):
        for c in sorted(a.get_components_by_class(u.InstancedStaticMeshComponent), key=lambda c: c.get_name()):
            if c == pilot or not c.static_mesh:
                continue
            if a.get_actor_label() == OWNER and 'ForestAccessPines' not in map(str, c.component_tags):
                continue
            count += c.get_instance_count()
            signature.update(str((a.get_actor_label(),c.get_name(),c.static_mesh.get_path_name(),
                [m.get_path_name() if m else '' for m in c.get_materials()],c.visible,c.cast_shadow)).encode())
            for i in range(c.get_instance_count()):
                t = c.get_instance_transform(i, True)
                values = t.translation.to_tuple() + t.rotation.to_tuple() + t.scale3d.to_tuple()
                signature.update((','.join(format(v,'.4f') for v in values)+'\n').encode())
    assert count > 13030
    return dict(instances=count,sha256=signature.hexdigest())

def grouped_broadleaf():
    import bend_crown as crown
    verify()
    report = json.loads((OUT/'build.json').read_text())
    rows = actors()
    tree = crown.target(rows)
    setup = json.loads((OUT/'broadleaf-prepared.json').read_text())
    assert setup['ok'] and setup['version'] == crown.VERSION
    mesh = u.load_asset(crown.VARIANT)
    assert mesh and E.get_metadata_tag(mesh, 'ForestAccessTufts') == crown.VERSION
    before = other_tree_digest(rows, tree)
    if report.get('revision') == 7:
        assert before == report['broadleaf']['other_trees']
        assert tree.static_mesh == mesh and tree.get_material(2) == u.load_asset(setup['far'])
        report['broadleaf'].update(setup)
        verify_placement(rows,report)
        dump('placement',report)
        dump('build',report)
        return
    assert report['revision'] == 6 and tree.static_mesh == u.load_asset(crown.ORIGINAL)
    assert tree.get_material(2) == u.load_asset(setup['old_far'])
    old_hash = digest(MAPFILE)
    backup = OUT/('BeforeBroadleaf-'+old_hash+'.umap')
    if not backup.exists():
        shutil.copyfile(MAPFILE, backup)
    assert digest(backup) == old_hash
    mats = list(tree.get_materials())
    tree.get_owner().modify()
    tree.modify()
    assert tree.set_static_mesh(mesh)
    for i, material in enumerate(mats[:2]):
        tree.set_material(i, material)
    tree.set_material(2, u.load_asset(setup['far']))
    report.update(revision=7, broadleaf=dict(**setup, other_trees=before, before_map_sha256=old_hash,
        near_materials=[m.get_path_name() for m in mats[:2]]))
    verify_placement(rows, report)
    dump('placement',report)
    assert L.save_current_level(), 'Could not save the isolated broadleaf placement'
    dump('build',report)

def install():
    rows=actors()
    road_pairs=[(a,road_samples(a)) for a in rows if isinstance(a,u.GTProceduralRoad)]
    road,=[s for a,s in road_pairs if 'Logging mud track' in a.get_actor_label()]
    roads=[s for _,s in road_pairs]
    author,=[a for a in rows if isinstance(a,u.GTProceduralGround)]
    terrain=GroundSampler(author)
    river=next(a for a in rows if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
    def dry(x,y):
        xy=u.Vector2D(x,y)
        return not river.covers(xy) or terrain.height(x,y)>river.surface_cm_at(xy)+8
    trunks,plants,rocks,sources=local_components(rows,road)
    if not plants or not sources:raise ValueError('Expected live forest dressing near the access bend.')
    # Reuse a visual rock instance when possible. Keep nearby physical obstacles as authored.
    options=sorted(rocks,key=lambda r:abs(r[3]-design.HERO[0])+abs(r[4]-design.HERO[1]))
    source=options[0][0] if options else next(c for c in sources if 'Large_Rock' in c.static_mesh.get_name())
    mesh=source.static_mesh;b=mesh.get_bounding_box()
    width=320.;sc=width/max(b.max.x-b.min.x,b.max.y-b.min.y)
    for ds,offset in [(d,o) for o in (design.HERO[1],-6.3,-6.,-8.2,7.5) for d in (0,-2,2,-4,4)]:
        hx,hy,yaw=road.at(design.HERO[0]+ds,offset)
        if (dry(hx,hy) and all(math.hypot(hx-tx,hy-ty)>240 for tx,ty in trunks) and
                min(r.nearest(hx,hy)[0] for r in roads)>design.CLEAR+2.5):break
    else:raise ValueError('No clear footprint for the outcrop.')
    rz=u.Rotator(yaw=yaw+20.,roll=7.)
    hero_tf=terrain.seat(mesh,u.Transform(location=V(hx,hy,0),rotation=rz,scale=V(sc,sc*.83,sc*.93)),False)
    hero_tf.translation-=V(0,0,(b.max.z-b.min.z)*sc*.13)
    moves=regroup(road,terrain,plants,trunks,(hx,hy),roads,dry)
    if not moves:raise ValueError('No local plant moves survived clearance checks.')
    backup_hash=save_backup()
    root,floor_labels,litter=floor_dressing(road,terrain,roads,trunks,dry)
    habitat=forest_layers(root,road,terrain,roads,trunks,hero_tf.translation,dry)
    crown=painted_tree(root,road,terrain,trunks,rows,dry)
    # Do not move an instance in from the opposite verge or outside its visible group.
    reuse=bool(options and options[0][4]<0 and abs(options[0][3]-design.HERO[0])<12)
    a=new_actor(u.StaticMeshActor,OWNER+'_Outcrop',hero_tf.translation)
    c=a.static_mesh_component
    c.set_static_mesh(mesh)
    c.set_collision_profile_name('NoCollision')
    a.set_actor_transform(hero_tf,False,True)
    if reuse:
        source.get_owner().modify()
        source.modify()
        assert source.remove_instance(options[0][1])
    components=set();samples=[]
    last_by_component={c:n for n,(c,i,old,new) in enumerate(moves)}
    for number,(c,i,old,new) in enumerate(moves):
        if c not in components:
            c.get_owner().modify();c.modify();components.add(c)
        if not c.update_instance_transform(i,new,True,number==last_by_component[c],True):
            raise ValueError('Could not move '+c.get_name())
        samples.append([c.get_owner().get_actor_label(),c.get_name(),i,list(new.translation.to_tuple())])
    ax,ay,heading=road.at(design.START-5)
    report=dict(stage='built',approach=[round(ax,1),round(ay,1),round(terrain.height(ax,ay)+150,1)],yaw=round(heading,2),source_sha256=backup_hash,ground_digest=str(author.output_digest),
                plants_moved=len(moves),reused_outcrop=reuse,rock_mesh=mesh.get_name(),
                floors=floor_labels,litter=litter,habitat=habitat,crown=crown,moved=samples,hero=list(hero_tf.translation.to_tuple()))
    report=meadow_crown(middle_storey(recompose(facing_the_track(report))))
    dump('placement',report)
    assert L.save_current_level(),'Level save failed'
    return report

def verify_placement(rows,r):
    named={a.get_actor_label():a for a in rows}
    assert OWNER in named and all(n in named for n in r['floors'])
    rock=named[OWNER+'_Outcrop']
    meadow=r.get('revision',1)>=6
    rock_mat='M_BendMossLedges' if meadow else ('M_ForestAccessBeddedStone' if r.get('revision',1)>=4 else 'M_ForestAccessStone')
    assert rock.static_mesh_component.get_material(0).get_name()==rock_mat
    assert math.dist(rock.get_actor_location().to_tuple(),r['hero'])<.2
    habitat={c.static_mesh.get_name().removeprefix('SM_NZ_'):c.get_instance_count()
             for c in named[OWNER].get_components_by_class(u.InstancedStaticMeshComponent)
             if 'ForestAccessHabitat' in map(str,c.component_tags)}
    assert habitat==r['habitat'],(habitat,r['habitat'])
    tree,=[c for c in named[OWNER].get_components_by_class(u.InstancedStaticMeshComponent)
           if 'ForestAccessPaintedTree' in map(str,c.component_tags)]
    leaf_name='MI_BendCanopyVolume' if meadow else 'MI_ForestAccessLeaf'
    leaf=next(m for m in tree.get_materials() if m and m.get_name()==leaf_name)
    assert tree.get_instance_count()==1
    if meadow:
        for k,v in r['meadow_crown'].items():assert abs(M.get_material_instance_scalar_parameter_value(leaf,k)-v)<.001
        assert r['woodland']['grass_fans']>0
    if 'broadleaf' in r:
        br=r['broadleaf']
        assert tree.static_mesh.get_path_name().split('.')[0]==br['mesh']
        assert [m.get_path_name() for m in list(tree.get_materials())[:2]]==br['near_materials']
        assert tree.get_material(2).get_path_name().split('.')[0]==br['far']
        assert other_tree_digest(rows,tree)==br['other_trees']
        assert math.dist(tree.get_instance_transform(0,True).translation.to_tuple(),r['crown']['position'])<.02
        assert [tree.static_mesh.get_num_triangles(i) for i in range(4)]==br['lod_triangles']
        if MODE=='verify':
            assert E.get_metadata_tag(tree.static_mesh,'ForestAccessTufts')==br['version']
    if r.get('revision',1)>=2:
        ferns,=[c for c in named[OWNER].get_components_by_class(u.InstancedStaticMeshComponent)
                if 'ForestAccessPaintedFerns' in map(str,c.component_tags)]
        assert ferns.get_instance_count()==r['painted_ferns'] and ferns.get_material(0).get_name()=='M_FernSurface'
    if r.get('revision',1)>=3:
        for label,(path,count) in r['woodland']['meshes'].items():
            component=named[label].static_mesh_component
            assert component.static_mesh.get_path_name().split('.')[0]==path and count>0
            assert component.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION
            ground_mat='M_BendPeatAndMoss' if r.get('revision',1)>=4 else 'M_BendMossPeat'
            expected=ground_mat if label.endswith('_ShoulderRelief') else 'M_BendBrushFoliage'
            if meadow:expected='M_BendMossColonies' if label.endswith('_ShoulderRelief') else 'M_BendMeadowBlades'
            assert component.get_material(0).get_name()==expected
    if MODE=='verify' and r.get('revision',1)>=4:
        version='3' if meadow else '2'
        assert E.get_metadata_tag(rock.static_mesh_component.get_material(0),'BendRockSurface')==version
        ground=u.load_asset(FOLDER+('/M_BendMossColonies' if meadow else '/M_BendPeatAndMoss'))
        assert E.get_metadata_tag(ground,'BendMossSurface')==('4' if meadow else version)
        assert E.does_asset_exist(FOLDER+('/T_BendMossShoots' if meadow else '/T_BendMossLitterFields'))
    if r.get('revision',1)>=5:
        if MODE=='verify':
            blades=u.load_asset(FOLDER+('/M_BendMeadowBlades' if meadow else '/M_BendBrushFoliage'))
            assert E.get_metadata_tag(blades,'BendFoliageSurface')==('3' if meadow else '2')
        grove,=[c for c in named[OWNER].get_components_by_class(u.InstancedStaticMeshComponent)
                if 'ForestAccessPines' in map(str,c.component_tags)]
        assert grove.get_instance_count()==r['pines'] and not grove.evaluate_world_position_offset
        assert grove.get_material(1).get_name()=='M_Crown_b74ce8ab'
        track=road_samples(next(a for a in rows if isinstance(a,u.GTProceduralRoad) and 'Logging mud track' in a.get_actor_label()))
        for index in range(grove.get_instance_count()):
            p=grove.get_instance_transform(index,True).translation
            distance,station,_=track.nearest(p.x,p.y)
            assert 27<=station<=69 and design.CLEAR<distance<19,(station,distance)
    assert all(named[n].get_editor_property('decal').get_decal_material() for n in r['floors'])
    cache={}
    for owner,comp,i,pos in r['moved']:
        key=(owner,comp)
        if key not in cache:
            cache[key]=next(c for c in named[owner].get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name()==comp)
        v=cache[key].get_instance_transform(i,True).translation
        assert math.dist(v.to_tuple(),pos)<.15,(owner,comp,i)
    assert str(next(a for a in rows if isinstance(a,u.GTProceduralGround)).output_digest)==r['ground_digest']
    if 'river_reveal' in r:
        import river_reveal
        river_reveal.verify(reveal_context(),rows,r['river_reveal'])
        assert other_tree_digest(rows,None)==r['river_reveal']['tree_digest']
        assert tree.static_mesh.get_name()==r['crown']['source']
        assert math.dist(tree.get_instance_transform(0,True).translation.to_tuple(),r['crown']['position'])<.02

def reveal_context():
    from types import SimpleNamespace
    return SimpleNamespace(actors=actors,road_samples=road_samples,FOLDER=FOLDER,OWNER=OWNER,
                           E=E,new_actor=new_actor)

def install_river_reveal():
    import river_reveal
    verify()
    r=json.loads((OUT/'build.json').read_text())
    if 'river_reveal' not in r:
        assert r['revision']==6,'The river study starts with the approved original broadleaf'
        old_hash=digest(MAPFILE)
        candidates=list(OUT.glob('*-'+old_hash+'.umap'))
        backup=candidates[0] if candidates else OUT/('BeforeRiverReveal-'+old_hash+'.umap')
        if not backup.exists():
            shutil.copyfile(MAPFILE,backup)
        assert digest(backup)==old_hash
        dump('before-river-reveal',r)
        tree_digest=other_tree_digest(actors(),None)
        changes=river_reveal.install(reveal_context(),r)
        changes.update(before_sha256=old_hash,backup=str(backup),tree_digest=tree_digest)
        r.update(revision=8,river_reveal=changes)
    if r['river_reveal'].get('edges_version')==2:
        return
    r['river_reveal'].update(river_reveal.install(reveal_context(),r,refit=True))
    r['revision']=9
    verify_placement(actors(),r)
    dump('placement',r)
    assert L.save_current_level(),'River study save failed'
    dump('build',r)
def verify():
    rows=actors()
    manifest=OUT/'build.json'
    pending=OUT/'placement.json'
    r=json.loads((manifest if manifest.exists() else pending).read_text())
    if pending.exists() and manifest.exists():
        staged=json.loads(pending.read_text())
        if staged.get('revision',1)>r.get('revision',1):
            # The editor can exit between its map save and its final receipt.
            try:verify_placement(rows,staged)
            except (AssertionError,KeyError,StopIteration):pass
            else:r=staged
    verify_placement(rows,r)
    if not manifest.exists() or json.loads(manifest.read_text())!=r:dump('build',r)
    receipt=dict(ok=True,revision=r.get('revision',1),plants_moved=r['plants_moved'],
                 ground_digest=r['ground_digest'],project=str(ROOT),map_sha256=digest(MAPFILE))
    if r.get('revision',1)>=6:
        moss=u.load_asset(FOLDER+'/M_BendMossColonies')
        receipt.update(moss_version=E.get_metadata_tag(moss,'BendMossSurface'),
                       moss_sha256=digest(MAPFILE.parent/'ForestAccessBend/M_BendMossColonies.uasset'),
                       grass_fans=r['woodland']['grass_fans'])
    dump('verified',receipt)

try:
    assert L.load_level(MAP),MAP
    if MODE=='survey':survey()
    elif MODE=='verify':verify()
    elif MODE=='broadleaf':grouped_broadleaf()
    elif MODE=='river-reveal':install_river_reveal()
    elif MODE=='build':
        if any(a.get_actor_label()==OWNER for a in actors()):
            verify()
            report=json.loads((OUT/'build.json').read_text())
            if report.get('revision',1)<6:
                old_revision=report.get('revision',1)
                if old_revision<2:report=facing_the_track(report)
                report=recompose(report)
                if old_revision<5:report=middle_storey(report)
                report=meadow_crown(report)
                dump('placement',report)
                assert L.save_current_level(),'Level save failed'
                dump('build',report)
            else:
                from forest_floor import material
                material(FOLDER,False)
        else:dump('build',install())
    else:raise ValueError(MODE)
    dump(MODE+'-session',dict(receipt=os.environ.get('GT_BEND_RECEIPT'),ok=True))
except Exception:
    dump('error',dict(stage=MODE,error=traceback.format_exc()))
    raise
