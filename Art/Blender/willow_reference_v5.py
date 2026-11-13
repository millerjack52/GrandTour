"""Weeping willow rebuilt from the owner's three 2026-10-06 references.

Low fork, rounded arching scaffold, long attached whips, fine green leaves.
Separate model study; does not alter the level's v2 assets.
"""
import bpy
import bmesh
import math
import random
from mathutils import Vector
from willow_bark import apply_bark


def curve(points, steps=4):
    p=[Vector(x) for x in points]; out=[]
    for i in range(len(p)-1):
        a,b,c,d=p[max(0,i-1)],p[i],p[i+1],p[min(len(p)-1,i+2)]
        for j in range(steps):
            t=j/steps
            out.append(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out+[p[-1]]


class Mesh:
    def __init__(self): self.v=[]; self.f=[]; self.mi=[]
    def face(self,f,mi=0): self.f.append(tuple(f)); self.mi.append(mi)
    def tube(self,points,radii,sides=6):
        start=len(self.v); p=[Vector(q) for q in points]
        for i,q in enumerate(p):
            tangent=(p[min(i+1,len(p)-1)]-p[max(0,i-1)]).normalized()
            axis=Vector((0,1,0)) if abs(tangent.y)<.95 else Vector((1,0,0))
            u=tangent.cross(axis).normalized(); v=tangent.cross(u)
            radius=radii[i] if len(radii)==len(p) else radii[0]*(1-i/(len(p)-1))+radii[-1]*i/(len(p)-1)
            for j in range(sides):
                angle=math.tau*j/sides
                self.v.append(tuple(q+radius*(1+.04*math.sin(j*2.3+i*.15))*(u*math.cos(angle)+v*math.sin(angle))))
        self.face(reversed(range(start,start+sides)))
        for i in range(len(p)-1):
            for j in range(sides):
                a=start+i*sides+j; b=start+i*sides+(j+1)%sides
                self.face((a,b,b+sides,a+sides))
        self.face(range(start+(len(p)-1)*sides,start+len(p)*sides))
    def branch(self,points,radii,sides=8):
        p=curve(points); rr=[]
        for i in range(len(radii)-1):
            rr.extend(radii[i]*(1-j/4)+radii[i+1]*j/4 for j in range(4))
        rr.append(radii[-1]); self.tube(p,rr,sides); return p,rr
    def leaf(self,base,direction,length,width,mi,rng):
        d=Vector(direction).normalized(); side=d.cross(Vector((.17,.28,1))).normalized(); normal=side.cross(d)
        roll=rng.uniform(-1,1); side=side*math.cos(roll)+normal*math.sin(roll)
        mid=base+d*length*.40; start=len(self.v)
        self.v.extend([tuple(base),tuple(mid-side*width),tuple(base+d*length+Vector((0,0,-.015))),tuple(mid+side*width)])
        self.face((start,start+1,start+2),mi); self.face((start,start+2,start+3),mi)
    def object(self,name,factory,mats):
        ob=factory(name,self.v,self.f,mats[0],smooth=False)
        for mat in mats[1:]: ob.data.materials.append(mat)
        for p,mi in zip(ob.data.polygons,self.mi): p.material_index=mi
        return ob


PRESETS={
    'reference':dict(seed=6100627,height=1,width=1,wood=1,lean=0,wind=0,reach=1,whips=(13,17),sprigs=5,coverage=1,omit=(),tint=(1,1,1)),
    'young':dict(seed=6100631,height=.68,width=.57,wood=.51,lean=-.045,wind=0,reach=.70,whips=(9,13),sprigs=4,coverage=.94,omit=(5,6),tint=(1.05,1.08,.98)),
    'broad':dict(seed=6100637,height=1.05,width=1.28,wood=1.22,lean=.035,wind=0,reach=1.10,whips=(15,19),sprigs=6,coverage=1,omit=(),tint=(.95,1,.95)),
    'windswept':dict(seed=6100643,height=.88,width=.95,wood=.90,lean=.27,wind=.24,reach=.90,whips=(11,15),sprigs=4,coverage=.92,omit=(5,),tint=(.88,.93,.92)),
    'weathered':dict(seed=6100651,height=.94,width=1.10,wood=1.10,lean=-.11,wind=.04,reach=.86,whips=(6,10),sprigs=3,coverage=.65,omit=(2,6),tint=(1.08,.92,.85)),
}


def build(mesh_factory,material_factory,preset='reference'):
    cfg=PRESETS[preset]
    rng=random.Random(cfg['seed'])
    bark=material_factory('M_WillowReference_Bark',(.09,.065,.04))
    shootmat=material_factory('M_WillowReference_Shoots',(.075,.08,.028))
    leafmats=[material_factory('M_WillowReference_Leaf'+str(i),tuple(c[k]*cfg['tint'][k] for k in range(3))) for i,c in enumerate([
        (.13,.215,.028),(.21,.29,.047),(.075,.15,.017),(.27,.34,.06),(.115,.19,.032)])]
    for mat in [shootmat]+leafmats:
        p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        p.inputs['Roughness'].default_value=.9; p.inputs['Specular IOR Level'].default_value=.12
    wood=Mesh(); fine=Mesh(); axes=[]
    def shaped(p):
        x,y,z=p
        turn=(.07*math.sin(z*.7) if preset!='reference' else 0)
        return (cfg['width']*(x*math.cos(turn)-y*math.sin(turn))+cfg['lean']*max(0,z)**1.25,
                cfg['width']*(x*math.sin(turn)+y*math.cos(turn)),z*cfg['height'])
    def structural_branch(points,radii,sides):
        return wood.branch([shaped(p) for p in points],[r*cfg['wood'] for r in radii],sides)
    trunk=[(0,0,-.1),(.04,-.02,.45),(.15,.03,1.0),(.29,.06,1.55),(.32,.08,2.15)]
    axes.append(structural_branch(trunk,[.43,.34,.29,.24,.15],12))
    for j in range(6):
        a=j*2.399; reach=rng.uniform(.55,.85)
        axes.append(structural_branch([(.03,0,.38),(.27*math.cos(a),.27*math.sin(a),.13),(reach*math.cos(a),reach*math.sin(a),-.11)],[.16,.12,.012],8))
    leaders=[
        ([(.15,.03,1),(-.05,.05,2.25),(-.4,.25,4.15),(-.2,.4,5.9),(.45,.35,7.0),(.95,.3,7.05)],[.26,.22,.15,.095,.035,.005]),
        ([(.06,0,.65),(-.65,-.15,1.7),(-1.55,-.3,3.5),(-2.65,-.4,5.35),(-3.5,-.5,5.35)],[.28,.23,.16,.07,.005]),
        ([(.18,.03,1.15),(.85,.12,2.3),(1.65,.25,3.8),(2.6,.35,5.4),(3.5,.6,5.25)],[.24,.20,.14,.065,.005]),
        ([(.1,.08,1.0),(-.3,.75,2.5),(-.7,1.6,4.3),(-1.05,2.3,5.9),(-1.65,3.0,5.75)],[.23,.19,.13,.055,.005]),
        ([(.23,0,1.4),(.55,-.65,2.8),(.65,-1.6,4.2),(1.2,-2.65,5.0),(1.7,-3,4.75)],[.19,.15,.095,.04,.004]),
        ([(-.32,.23,3.6),(-1,-.3,4.8),(-1.6,-.9,6.1),(-2.2,-1.5,6.2)],[.13,.095,.045,.004]),
        ([(.1,.4,3.0),(.85,1.3,4.6),(1.45,2.2,6.2),(2.1,2.8,6.0)],[.15,.11,.048,.004]),
    ]
    secondary=[]
    for li,(controls,radii) in enumerate(leaders):
        if li in cfg['omit']:
            if preset=='weathered' and li==2:
                axes.append(structural_branch(controls[:3],[radii[0],radii[1],.11],9))
            continue
        p,rr=structural_branch(controls,radii,9); axes.append((p,rr))
        # Alternating rising arches spread a rounded three-dimensional crown.
        for j in range(int(len(p)*.42),len(p)-1,2):
            root=p[j]; tangent=(p[j+1]-p[j-1]).normalized()
            heading=math.atan2(tangent.y,tangent.x)+(1 if j%4 else -1)*rng.uniform(.65,1.4)
            reach=rng.uniform(.8,1.65)*(1-.20*j/len(p))*cfg['reach']
            along=Vector((math.cos(heading),math.sin(heading),0))
            high=root+along*reach*.53+Vector((0,0,rng.uniform(.45,.90)))
            tip=root+along*reach+Vector((0,0,rng.uniform(.0,.40)))
            path=curve([root,high,tip],3)
            fine.tube(path,[rng.uniform(.025,.039),.0025],5)
            secondary.append((path,heading,li))
        secondary.append((p[-6:],math.atan2(p[-1].y-p[-6].y,p[-1].x-p[-6].x),li))

    core=wood.object('SM_RF_Willow_Reference' if preset=='reference' else 'SM_Willow_'+preset.title(),mesh_factory,[bark])
    bpy.ops.object.select_all(action='DESELECT'); core.select_set(True); bpy.context.view_layer.objects.active=core
    mod=core.modifiers.new('Joined low forks','REMESH'); mod.mode='VOXEL'; mod.voxel_size=.038*min(1,cfg['wood'])
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=core.modifiers.new('Continuous wood','SMOOTH'); mod.factor=.65; mod.iterations=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=core.modifiers.new('Scaffold budget','DECIMATE'); mod.ratio=.30
    bpy.ops.object.modifier_apply(modifier=mod.name)
    apply_bark(core,axes)
    # Dark weathered wood, as in the supplied lake and model photographs.
    mat=core.data.materials[0]; nt=mat.node_tree
    p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'); source=p.inputs['Base Color'].links[0].from_socket
    tint=nt.nodes.new('ShaderNodeMixRGB'); tint.name='Weathered darker willow'; tint.blend_type='MULTIPLY'; tint.inputs[0].default_value=1; tint.inputs[2].default_value=(.48,.46,.42,1)
    nt.links.new(source,tint.inputs[1]); nt.links.new(tint.outputs[0],p.inputs['Base Color'])

    whips=0; leaf_count=0
    def whip(root,heading,drop,colour):
        nonlocal whips,leaf_count
        along=Vector((math.cos(heading),math.sin(heading),0)); cross=Vector((-along.y,along.x,0))
        reach=rng.uniform(.22,.60); bend=rng.uniform(-.17,.17); phase=rng.uniform(0,math.tau)
        points=[]
        for j in range(13):
            t=j/12
            points.append(root+along*(reach*(1-math.exp(-5*t)))+cross*(bend*math.sin(t*math.pi)+.035*math.sin(t*9+phase)*t)+Vector((cfg['wind']*drop*t**1.35,0,.07*math.sin(t*math.pi)-drop*(.22*t+.78*t*t))))
        fine.tube(points,[rng.uniform(.005,.009),.0004],3); whips+=1
        n=max(14,int(drop/.115))
        for j in range(1,n+1):
            t=(j-rng.uniform(.05,.55))/n; segment=min(11,int(t*12)); q=points[segment].lerp(points[segment+1],t*12-segment)
            # Alternate fine leaves along the stem, with occasional opposite leaves.
            for side in ([1,-1] if rng.random()<.85 else [1 if j%2 else -1]):
                if cfg['coverage']<1 and rng.random()>cfg['coverage']: continue
                a=heading+side*rng.uniform(.7,1.65)
                length=rng.uniform(.105,.185)*(1-.17*t)
                fine.leaf(q,(math.cos(a)*.5,math.sin(a)*.5,-rng.uniform(.45,.95)),length,length*rng.uniform(.085,.13),colour if rng.random()<.8 else rng.randint(1,5),rng)
                leaf_count+=1
    for path,heading,li in secondary:
        mass_colour=[2,1,2,3,1,4,1][li]
        for k in range(rng.randint(*cfg['whips'])):
            u=rng.uniform(.13,1); index=min(len(path)-2,int(u*(len(path)-1)))
            root=path[index].lerp(path[index+1],u*(len(path)-1)-index)
            radial=math.hypot(root.x,root.y)
            floor=(rng.uniform(.5,1.55) if radial>2*cfg['width'] else rng.uniform(1.1,2.5))*cfg['height']
            # Some shorter strands keep gaps between the larger hanging curtains.
            if k%5==0: floor+=rng.uniform(.8,1.6)
            drop=max(.9,root.z-floor)
            whip(root,heading+rng.uniform(-1.05,1.05),drop,mass_colour)
        # Short leafy branchlets round the crown above the long hanging curtains.
        for k in range(cfg['sprigs']):
            u=.15+k*(.17 if preset=='reference' else .70/max(1,cfg['sprigs']-1)); index=min(len(path)-2,int(u*(len(path)-1)))
            root=path[index].lerp(path[index+1],u*(len(path)-1)-index)
            angle=heading+(-1 if k%2 else 1)*rng.uniform(.65,1.65)
            along=Vector((math.cos(angle),math.sin(angle),0))
            peak=root+along*rng.uniform(.25,.40)+Vector((0,0,rng.uniform(.25,.50)))
            tip=root+along*rng.uniform(.55,.80)+Vector((0,0,rng.uniform(-.1,.2)))
            sprig=curve([root,peak,tip],3); fine.tube(sprig,[.012,.001],4)
            for j in range(1,17):
                t=j/17; ii=min(len(sprig)-2,int(t*(len(sprig)-1)))
                q=sprig[ii].lerp(sprig[ii+1],t*(len(sprig)-1)-ii)
                turn=angle+(1 if j%2 else -1)*rng.uniform(.65,1.6)
                length=rng.uniform(.12,.19)
                fine.leaf(q,(math.cos(turn)*.65,math.sin(turn)*.65,rng.uniform(-.5,.3)),length,length*.11,mass_colour,rng); leaf_count+=1
            whip(peak,angle+rng.uniform(-.7,.7),rng.uniform(.65,1.35),mass_colour)

    foliage=fine.object('Willow_reference_shoots_and_leaves',mesh_factory,[shootmat]+leafmats)
    bpy.ops.object.select_all(action='DESELECT'); core.select_set(True); foliage.select_set(True); bpy.context.view_layer.objects.active=core
    bpy.ops.object.join()
    bm=bmesh.new(); bm.from_mesh(core.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_area()<1e-10],context='FACES')
    bm.to_mesh(core.data); bm.free(); core.data.update()
    core['reference_set']='Art/References/Trees/UserWillows'
    core['willow_preset']=preset
    core['pendant_shoot_count']=whips; core['leaf_count']=leaf_count
    # Fresh lower-trunk hulls; the previous model's collision is not reused.
    hulls=[]
    for i in range(3):
        h=Mesh(); h.tube([shaped(trunk[i]),shaped(trunk[i+1])],[[.41,.34,.29][i]*cfg['wood'],[.34,.29,.24][i]*cfg['wood']],8)
        ob=h.object('UCX_'+core.name+'_'+str(i).zfill(2),mesh_factory,[bark]); ob.hide_render=True; ob.hide_set(True); hulls.append(ob)
    return [core],{core.name:hulls}
