"""Scatter follows the authored road bed; interactive clods retain native behaviour."""
import unreal as u,json,random,math,array
from pathlib import Path
from make_mud_road import centre
O=Path('C:/GrandTour/Art/Export/FloraDrive')
def rest_sampler():
    values=array.array('f');values.frombytes((O/'road-rest-heights.f32').read_bytes());assert len(values)==512*512
    def sample(x,y):
        a=max(0,min(511,(x+3150)/6300*512-.5));b=max(0,min(511,(y+3150)/6300*512-.5))
        i=int(a);j=int(b);fx=a-i;fy=b-j
        return (values[j*512+i]*(1-fx)+values[j*512+min(511,i+1)]*fx)*(1-fy)+(values[min(511,j+1)*512+i]*(1-fx)+values[min(511,j+1)*512+min(511,i+1)]*fx)*fy
    return sample

def dress(models,buckets,spawn,actors):
    rng=random.Random(72331);height=rest_sampler()
    manifest=O/'road-clod-sources.json'
    old=[a for a in actors.get_all_level_actors() if isinstance(a,u.GTMudRunnerClod)]
    if not manifest.exists():
        sources={str(a.large):{'mesh':a.body.static_mesh.get_path_name(),'large':bool(a.large)} for a in old};assert sources
        manifest.write_text(json.dumps(list(sources.values()),indent=2))
    sources=json.loads(manifest.read_text())
    for a in old:actors.destroy_actor(a)
    rocks=[n for n in models if n.endswith(('_Rock_0_018','_Rock_0_013','_Rock_0_014','_Rock_0_015','_Rock_0_017'))]
    assert rocks
    def xy(x,d):return x,centre(x)+d*math.sqrt(1+(530/1050*math.cos((x+2200)/1050))**2)
    count=0
    for k in range(100):
        x=rng.uniform(-2160,2350);d=rng.choice([-1,1])*rng.uniform(175,310)
        for j in range(rng.randint(3,7)):
            xx,yy=xy(x+rng.gauss(0,60),d+rng.gauss(0,30));z=height(xx,yy)
            if z<-4:continue
            name=rng.choice(rocks);b=models[name].get_bounds();total=rng.uniform(9,22)
            scale=min(total/(2*b.box_extent.z),rng.uniform(20,48)/(2*max(b.box_extent.x,b.box_extent.y)))
            total=2*b.box_extent.z*scale
            z-=total*rng.uniform(.40,.65)+(b.origin.z-b.box_extent.z)*scale
            buckets.setdefault(name,[]).append(u.Transform(location=u.Vector(xx,yy,z),rotation=u.Rotator(pitch=rng.uniform(-10,10),yaw=rng.uniform(0,360),roll=rng.uniform(-10,10)),scale=u.Vector(scale,scale,scale)));count+=1
    # 64 physical clods instead of the inherited 275 arranged in long border rows.
    # Keep the wheel channels free of fixed suspension obstacles.
    for i in range(64):
        x=rng.uniform(-2100,2320);d=rng.choice([-1,1])*rng.uniform(165,290);x,y=xy(x,d)
        row=sources[i%len(sources)];mesh=u.load_asset(row['mesh']);assert mesh
        b=mesh.get_bounds();scale=min(rng.uniform(18,30)/(2*b.box_extent.z),48/(2*max(b.box_extent.x,b.box_extent.y)))
        total=2*b.box_extent.z*scale;z=height(x,y)-total*.65-(b.origin.z-b.box_extent.z)*scale
        a=spawn(u.GTMudRunnerClod,'EmbeddedClod_'+str(i),(x,y,z),u.Rotator(yaw=rng.uniform(0,360)));a.large=row['large'];a.body.set_static_mesh(mesh);a.set_actor_scale3d(u.Vector(scale,scale,scale))
    return {'removed_inherited_clods':len(old),'interactive_clods':64,'instanced_embedded_stones':count,'scatter_seed':72331,'roadbed_source':'same road-rest-heights.f32 used for numeric rest texture','traffic_lane_static_detail':False}
