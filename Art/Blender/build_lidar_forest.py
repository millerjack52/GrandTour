"""FS1: irregular beech boughs for the actual LiDAR forest, not the kit lineup.

Blender --background --python this_file -- [--only Mature,Pole,Edge]
One deterministic branching design supplies all three LODs. Every bough survives
each LOD; fewer, broader folded leaf sprays retain its volume and silhouette.
The original NativePlants kit and its manifest are never overwritten.
"""
import bpy, sys, math, random, json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_plant_lib as L
import build_native_bush as B

OUT = Path(__file__).resolve().parents[1] / 'Export/LidarStudy/ForestFS1'
ARGS = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ONLY = ARGS[ARGS.index('--only')+1].split(',') if '--only' in ARGS else ['Mature','Pole','Edge']
SPECS = {
 'Mature': dict(height=22., base=9.0, radius=4.7, stem=.32, branches=9, seed=201026, budget=(24000,7000,1800)),
 'Pole': dict(height=12., base=6.2, radius=1.7, stem=.10, branches=6, seed=201027, budget=(6000,2000,600)),
 'Edge': dict(height=16., base=2.4, radius=4.4, stem=.28, branches=9, seed=201028, budget=(22000,6500,1800)),
}

def bough(g, centre, radii, seed, lod, pole=False):
    """Three-dimensional leaf groups, with no shared horizontal tier planes.

    A nested low-discrepancy distribution preserves all sides of the bough at
    distance. Geometry is opaque; the far atlas alone uses alpha masking.
    """
    rng=random.Random(seed)
    count = ((30,8,3) if pole else (84,27,9))[lod]
    size = ((.30,.45,.67) if pole else (.58,.88,1.23))[lod]
    golden=math.pi*(3-math.sqrt(5)); phase=rng.uniform(0,math.tau)
    for j in range(count):
        z=1-2*(j+.5)/count
        az=j*golden+phase; r=math.sqrt(max(0,1-z*z))
        n=Vector((r*math.cos(az),r*math.sin(az),z))
        # Bough lobes are irregular and porous, never closed geometric balls.
        ripple=1+.12*math.sin(az*3+seed)+.09*math.sin(az*5+z*4)
        p=centre+Vector((n.x*radii.x,n.y*radii.y,n.z*radii.z))*ripple*rng.uniform(.60,1.)
        normal=(n*.55+L.Z*.65+B.jit(rng,.22)).normalized()
        direction=L.rot(L.perp(normal),normal,rng.uniform(0,math.tau))
        shade=L.clamp(.46+.24*n.z+rng.uniform(-.18,.18))
        colour=L.scale_col(L.mix(B.LEAF_DARK,B.LEAF_LIGHT,shade),rng.uniform(.88,1.12))
        length=size*rng.uniform(.78,1.15)
        L.spray(g,p-direction*length*.4,direction,length,colour,normal,
                quads=3 if lod<2 else 2,fan=.68,width=.83,fold=.17)
    g.counts['clusters']+=1

def design(kind):
    s=SPECS[kind]; rng=random.Random(s['seed']); D=B.Design()
    h=s['height']; edge=kind=='Edge'; pole=kind=='Pole'; stem=s['stem']
    lean=Vector((1.25,.35,0)) if edge else Vector((.32,-.16,0))
    ctrl=[lean*(i/12)**1.4+Vector((.11*math.sin(i*.91),.08*math.sin(i*1.31),-.06+(h*.86+.06)*i/12)) for i in range(13)]
    ctrl[0]=Vector((0,0,-.06))
    D.tube(ctrl,[(0,stem*1.5),(.035,stem),(.45,stem*.70),(1,.025)],(44,18,8),(9,7,5),'bark')
    D.trunk=L.curve(ctrl,6); D.hull_z=min(7.,s['base']); D.hull_rfn=lambda t:stem*(1-.75*t)
    # Root buttresses at the player-height contact, part of the same mesh.
    for i in range(5):
        az=i*2.4; out=Vector((math.cos(az),math.sin(az),0))
        D.tube([out*stem*.2+L.Z*.65,out*stem*1.7+L.Z*.10,out*stem*2.6-L.Z*.06],[(0,stem*.42),(1,.025)],(3,2,1),(5,4,3),'bark')
    lobes=[]; phase=rng.uniform(0,math.tau)
    for i in range(s['branches']):
        f=(i+rng.uniform(.15,.85))/s['branches']
        z=s['base']+(h*.79-s['base'])*f
        root=B.trunk_at(D.trunk,z)[0]
        az=phase+i*2.39996+rng.uniform(-.35,.35)
        radial=Vector((math.cos(az),math.sin(az),0))
        reach=s['radius']*rng.uniform(.66,1.0)*(1-.40*f)
        if edge:reach*=1+.20*math.cos(az)
        lift=(h-z)*(rng.uniform(.16,.28) if edge else rng.uniform(.25,.44))
        end=root+radial*reach+L.Z*lift
        bend=root+radial*reach*.47+L.Z*lift*.38+B.jit(rng,.18)
        D.tube([root,bend,end],[(0,stem*(.40-.16*f)),(1,.018)],(7,4,2),(6,5,3),'bark')
        # Unequal side branches, not the repeated symmetric Y skeleton.
        for k,t in enumerate((.47,.76,1.0)):
            origin=L.along(L.curve([root,bend,end],4),t)[0]
            direction=L.rot(radial,L.Z,(-1 if k==0 else 1)*rng.uniform(.4,1.3))
            c=origin+direction*reach*rng.uniform(.12,.30)+L.Z*rng.uniform(.2,.9)
            D.tube([origin,origin.lerp(c,.55)+L.Z*.12,c],[(0,.03 if pole else .055),(1,.008)],(3,2,1),(4,3,3),'bark',keep=(1,1,0))
            rr=(.65 if pole else 1.38)*rng.uniform(.82,1.14)
            radii=Vector((rr*rng.uniform(.85,1.2),rr*rng.uniform(.8,1.15),rr*rng.uniform(.72,1.12)))
            lobes.append((c,radii,rng.randrange(1<<29)))
    # Upper crown has offset leaders and a broken skyline, with a connected core.
    for j in range(5 if not pole else 3):
        az=phase+j*2.4; rr=s['radius']*.28
        c=lean+Vector((math.cos(az)*rr,math.sin(az)*rr,h-1.4-j*.48))
        root=B.trunk_at(D.trunk,h*.76)[0]
        D.tube(B.aim(root,c,rng,lift=.12),[(0,stem*.22),(1,.012)],(5,3,2),(5,4,3),'bark')
        r=.65 if pole else 1.35;lobes.append((c,Vector((r,r*.9,r*1.12)),rng.randrange(1<<29)))
    for z in (s['base']*.48,s['base']*.78):
        B.dead_stub(D,D.trunk,rng,z,.4 if pole else .8,.025,group='bark')
    B.beech_paint(D,.38,.10,(.4,1),moss_top=6.)
    for c,r,seed in lobes:
        D.extra(lambda g,lod,c=c,r=r,seed=seed:bough(g,c,r,seed,lod,pole))
    return D,len(lobes)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    mats=L.plant_materials();rows=[]
    manifest=OUT/'manifest.json'
    if manifest.exists():rows=[r for r in json.loads(manifest.read_text())['models'] if r['variant'] not in ONLY]
    for kind in ONLY:
        D,n=design(kind);s=SPECS[kind];name='SM_FS1_Beech_'+kind
        g,_=B.emit(D,0,s['budget'][0]); scale=s['height']/max(v.z for v in g.v)
        # Scale emitted geometry uniformly about the planted pivot; extras are closures.
        for lod in range(3):
            g,_=B.emit(D,lod,s['budget'][lod]);g.v=[v*scale for v in g.v]
            ob,dropped=L.to_object(g,name+'_LOD'+str(lod),mats,[0,1])
            tris=len(ob.data.loop_triangles);assert tris<=s['budget'][lod],(kind,lod,tris)
            L.export(ob,out=OUT)
            rows.append(L.manifest_row(ob,name,'Beech',kind,lod,[0,1],s['seed'],g.counts,0,s['budget'][lod],dict(boughs=n,dropped_degenerate_faces=dropped)))
            ob.hide_set(True);ob.hide_render=True
            print('FS1',kind,lod,tris,'triangles',n,'boughs',flush=True)
    L.write_manifest(rows,out=OUT,extra=dict(stage='FS1',unreal_destination='/Game/GrandTour/ArtTests/LidarStudy/ForestShapes',lod_rule='Every branch lobe persists through all three LODs; radial folded leaf sprays, no flat tiers.'))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ForestShapes.blend'))
    print('FS1_BUILD_OK',flush=True)

if __name__=='__main__':main()
