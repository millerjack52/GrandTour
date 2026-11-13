"""Compose the finished Flora Drive route from the purchased Flora Paint meshes."""
import unreal as u,math,random
from flora_drive_ground import floor_z,pond_delta
from make_mud_road import centre

def dress_scene(models,buckets,far_buckets,treepoints,place,spawn):
    rng=random.Random(2026111301);report={}
    trees=[n for n in models if 'Tree' in n]
    shrubs=[n for n in models if 'Shrubbery' in n]
    grass=[n for n in models if '_Grass_' in n and not any(s in n for s in ['Dry','Blooming'])]
    dry=[n for n in models if 'Dry_Grass' in n]
    flowers=[n for n in models if 'Flower_B' in n]
    small=[n for n in models if 'Small_Plants' in n]
    ferns=[n for n in models if 'Ferns' in n]
    reeds=[n for n in models if 'Miscanthus' in n]
    rocks=[n for n in models if '_Rock_' in n]
    litter=[n for n in models if 'Fallen_Leaves' in n]
    twigs=[n for n in models if 'Twig' in n]
    start=sum(map(len,buckets.values()))
    # Keep the route legible; use short grasses at its margins, taller groups behind.
    for k in range(150):
        x=rng.uniform(-2850,2850);y=centre(x)+rng.choice([-1,1])*rng.uniform(350,950)
        if abs(y)>2850 or pond_delta(x,y)<-2:continue
        family=rng.choice([grass,grass,small,dry])
        for j in range(rng.randint(15,25)):
            xx=x+rng.gauss(0,95);yy=y+rng.gauss(0,85)
            if abs(yy-centre(xx))<310 or pond_delta(xx,yy)<-2:continue
            place(rng.choice(family),xx,yy,rng.uniform(22,55))
        if k%8==0:
            for j in range(7):place(rng.choice(flowers),x+rng.gauss(0,50),y+rng.gauss(0,50),rng.uniform(20,38))
    report['verge_instances']=sum(map(len,buckets.values()))-start
    # Saplings and understory bridge the tall bare trunks and the ground layer.
    saplings=0;understory=0
    for k in range(115):
        angle=rng.uniform(0,math.tau);radius=rng.uniform(1300,5700);x=math.cos(angle)*radius;y=math.sin(angle)*radius
        if abs(y-centre(x))<850 or pond_delta(x,y)<-1:continue
        if k%3==0 and not any(math.hypot(x-a,y-b)<320 for a,b in treepoints):
            if place(rng.choice(trees),x,y,rng.uniform(550,1050)):
                saplings+=1;treepoints.append((x,y))
        for j in range(rng.randint(3,5)):
            xx=x+rng.gauss(0,130);yy=y+rng.gauss(0,130)
            if abs(yy-centre(xx))<650 or pond_delta(xx,yy)<-2:continue
            if place(rng.choice(shrubs),xx,yy,rng.uniform(90,175)):understory+=1
        for j in range(10):
            xx=x+rng.gauss(0,200);yy=y+rng.gauss(0,180)
            if abs(yy-centre(xx))>520:place(rng.choice(grass),xx,yy,rng.uniform(35,85))
        if k%9==0:place(rng.choice(ferns),x-100,y+100,rng.uniform(60,90))
    report.update(saplings=saplings,understory_shrubs=understory)
    # Close the bare apron with an interlocking middle layer on the raised banks.
    edge_shrubs=0;edge_trees=0
    for k in range(250):
        angle=rng.uniform(0,math.tau);radius=rng.uniform(3700,7300)
        x=math.cos(angle)*radius;y=math.sin(angle)*radius
        if max(abs(x),abs(y))<3100:continue
        for j in range(rng.randint(3,5)):
            xx=x+rng.gauss(0,180);yy=y+rng.gauss(0,180)
            if place(rng.choice(shrubs),xx,yy,rng.uniform(150,265)):edge_shrubs+=1
        if k%4==0 and not any(math.hypot(x-a,y-b)<280 for a,b in treepoints):
            if place(rng.choice(trees),x,y,rng.uniform(650,1200)):treepoints.append((x,y));edge_trees+=1
        for j in range(5):place(rng.choice(grass),x+rng.gauss(0,220),y+rng.gauss(0,220),rng.uniform(45,90))
    report.update(edge_shrubs=edge_shrubs,edge_trees=edge_trees)
    # Three uneven distant stands, using only the existing lowest tree LOD.
    distant=0
    for radius,count in [(6400,48),(8700,60),(11200,72)]:
        for i in range(count):
            angle=math.tau*(i+rng.uniform(-.35,.35))/count;r=radius+rng.uniform(-430,430)
            x=r*math.cos(angle);y=r*math.sin(angle);name=rng.choice(trees)
            if place(name,x,y,rng.uniform(1200,2200)):
                far_buckets.setdefault(name,[]).append(buckets[name].pop());distant+=1
    report['distant_trees_lowest_lod']=distant
    # Asymmetric reed / grass groups define the pond; keep the near shore open.
    shore=0
    for k in range(64):
        angle=math.tau*k/64
        if math.sin(angle)<-.3 and k%4:continue
        x=900+math.cos(angle)*rng.uniform(700,820);y=1050+math.sin(angle)*rng.uniform(500,590)
        for j in range(rng.randint(3,6)):
            xx=x+rng.gauss(0,40);yy=y+rng.gauss(0,40)
            if pond_delta(xx,yy)<-3 or abs(yy-centre(xx))<340:continue
            family=reeds if k%3 else grass
            if place(rng.choice(family),xx,yy,rng.uniform(55,100)):shore+=1
    report['shore_instances']=shore
    # A few larger outcrops mark bends; small rocks elsewhere remain supporting detail.
    hero=0
    for x,y in [(-2200,centre(-2200)-850),(1600,1800),(2350,centre(2350)-900)]:
        for j in range(5):
            xx=x+rng.uniform(-170,170);yy=y+rng.uniform(-150,150);name=rng.choice(rocks);height=rng.uniform(75,180)
            b=models[name].get_bounds();height=min(height,320*b.box_extent.z/max(b.box_extent.x,b.box_extent.y,1))
            if not place(name,xx,yy,height):continue
            b=models[name].get_bounds();scale=height/(b.box_extent.z*2)
            # Slightly bury the foot, and add a conservative solid core for driving.
            t=buckets[name][-1];p=t.translation;t.translation=u.Vector(p.x,p.y,p.z-height*.2)
            a=spawn(u.StaticMeshActor,'RockCore_'+str(hero),(xx,yy,floor_z(xx,yy)+height*.25))
            a.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));a.set_actor_scale3d(u.Vector(max(.4,b.box_extent.x*scale*.012),max(.4,b.box_extent.y*scale*.012),height*.009))
            a.set_actor_hidden_in_game(True);a.static_mesh_component.set_cast_shadow(False);a.static_mesh_component.set_collision_profile_name('BlockAll');hero+=1
    report['landmark_rocks']=hero
    # Flat debris is sized by footprint and follows the actual bank normal.
    def debris(name,x,y,width):
        if pond_delta(x,y)<-2:return
        b=models[name].get_bounds();scale=width/max(b.box_extent.x*2,b.box_extent.y*2,1.)
        dx=(floor_z(x+20,y)-floor_z(x-20,y))/40;dy=(floor_z(x,y+20)-floor_z(x,y-20))/40
        angle=rng.uniform(0,math.tau)
        rot=u.MathLibrary.make_rot_from_zx(u.Vector(-dx,-dy,1),u.Vector(math.cos(angle),math.sin(angle),0))
        z=floor_z(x,y)+3-(b.origin.z-b.box_extent.z)*scale
        buckets.setdefault(name,[]).append(u.Transform(location=u.Vector(x,y,z),rotation=rot,scale=u.Vector(scale,scale,scale)))
    for k in range(190):
        x=rng.uniform(-2800,2800);y=centre(x)+rng.choice([-1,1])*rng.uniform(400,2400)
        if abs(y)>2850:continue
        debris(rng.choice(litter),x,y,rng.uniform(65,140))
        if k%4==0:debris(rng.choice(twigs),x+35,y-30,rng.uniform(70,140))
    report['ground_debris_instances']=sum(len(t) for n,t in buckets.items() if 'Fallen_Leaves' in n or 'Twig' in n)
    return report
