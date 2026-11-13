"""Mature willow crown study. v2 and its younger tree/scrub stay intact.

Actual opaque leaf geometry, authored structural limbs, deterministic branching.
The v2 lower trunk path is retained so its collision remains valid.
"""
import math
import random
import bpy
import bmesh
from mathutils import Vector
from riverbank_vegetation_v2 import build as build_previous
from willow_bark import apply_bark


def build(mesh_factory, material_factory):
    assets, collisions = build_previous(mesh_factory, material_factory)
    old = assets[0]
    old_mesh = old.data
    bpy.data.objects.remove(old, do_unlink=True)
    bpy.data.meshes.remove(old_mesh)
    rng = random.Random(61026)
    bark = material_factory('M_RF_WillowV3_Bark', (.115, .085, .055), vertex=True)
    palette = [(.40, .21, .018), (.55, .31, .032), (.25, .24, .035),
               (.135, .165, .022), (.42, .13, .015), (.64, .39, .048)]
    mats = [bark] + [material_factory('M_RF_WillowV3_Leaf'+str(i), c)
                     for i, c in enumerate(palette)]
    for mat in mats:
        principled=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        principled.inputs['Specular IOR Level'].default_value=.15
    verts, faces, indices = [], [], []
    wood_axes=[]

    def face(ids, material=0):
        faces.append(tuple(ids)); indices.append(material)

    def curve(controls, steps=3):
        p = [Vector(x) for x in controls]
        result = []
        for i in range(len(p)-1):
            a, b, c, d = p[max(0, i-1)], p[i], p[i+1], p[min(len(p)-1, i+2)]
            for j in range(steps):
                t = j/steps
                result.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
        return result+[p[-1]]

    def tube(points, radii, sides=7):
        start = len(verts)
        p = [Vector(v) for v in points]
        for i, q in enumerate(p):
            tangent = (p[min(i+1,len(p)-1)]-p[max(i-1,0)]).normalized()
            axis = Vector((0,1,0)) if abs(tangent.y)<.95 else Vector((1,0,0))
            u = tangent.cross(axis).normalized(); v = tangent.cross(u)
            radius = radii[0]*(1-i/(len(p)-1))+radii[-1]*i/(len(p)-1) if len(radii)==2 else radii[i]
            for j in range(sides):
                a = math.tau*j/sides
                k = 1+.045*math.sin(j*2.1+i*.2)
                verts.append(tuple(q+radius*k*(u*math.cos(a)+v*math.sin(a))))
        face(reversed(range(start,start+sides)))
        for i in range(len(p)-1):
            for j in range(sides):
                a=start+i*sides+j; b=start+i*sides+(j+1)%sides
                face((a,b,b+sides,a+sides))
        face(range(start+(len(p)-1)*sides,start+len(p)*sides))

    def branch(controls, radii, sides=8, steps=3):
        p = curve(controls, steps)
        rr=[]
        for i in range(len(radii)-1):
            rr += [radii[i]*(1-j/steps)+radii[i+1]*j/steps for j in range(steps)]
        tube(p, rr+[radii[-1]], sides)
        if radii[0]>=.085:
            wood_axes.append((p,rr+[radii[-1]]))
        return p

    trunk=[(0,0,-.13),(.12,.03,.45),(.02,0,1.05),(-.30,.02,1.75),(-.67,.05,2.45),(-.79,.10,3.15)]
    branch(trunk,[.63,.48,.39,.34,.29,.16],12)
    for j in range(7):
        a=j*2.399; length=rng.uniform(.68,1.18)
        branch([(.08,0,.55),(.36*math.cos(a),.36*math.sin(a),.16),
                (length*math.cos(a),length*math.sin(a),-.09)], [.22,.16,.015],7)
    leaders=[
        ([(-.45,.03,2.05),(-1.35,.02,3.0),(-2.5,-.12,3.9),(-3.22,-.1,5.2),(-3.4,.1,5.95)],[.33,.27,.18,.09,.014]),
        ([(-.76,.09,2.95),(.1,-.1,3.65),(1.42,.05,4.1),(2.7,.33,4.7),(3.45,.45,5.35)],[.29,.245,.16,.08,.012]),
        ([(-.78,.10,2.90),(-.5,.3,4.05),(-.99,.2,5.13),(-.70,.48,6.15),(-.22,.67,6.7)],[.29,.23,.155,.075,.012]),
        ([(-.6,.1,2.65),(-.15,1.10,3.75),(.72,1.72,4.64),(1.6,2.10,5.5)],[.24,.18,.10,.012]),
        ([(-.27,-.08,1.9),(.6,-.72,2.85),(1.8,-1.25,3.5),(2.9,-1.48,4.1)],[.25,.19,.095,.012]),
        ([(-.65,.05,2.8),(-1.25,1.25,3.65),(-2.1,2.05,4.4),(-2.55,2.4,5.45)],[.20,.15,.085,.012]),
        ([(.1,-.1,3.65),(.65,-.15,4.5),(1,-.3,5.7),(1.8,-.15,6.3)],[.15,.115,.06,.012]),
        ([(-1.35,.02,3),(-1.65,-.75,4.35),(-1.8,-1.0,5.6),(-2,-.7,6.35)],[.16,.12,.065,.012]),
    ]
    secondary=[]
    for li,(controls,radii) in enumerate(leaders):
        p=branch(controls,radii,9)
        for j in range(4,len(p)-1,2):
            # Alternating side branches; no paired fans or radial umbrellas.
            root=p[j]; tangent=(p[j+1]-p[j-1]).normalized()
            heading=math.atan2(tangent.y,tangent.x)+(1 if j%4 else -1)*rng.uniform(.65,1.65)
            horizontal=Vector((math.cos(heading),math.sin(heading),0))
            reach=rng.uniform(.8,1.55)*(1-.22*j/len(p))
            tip=root+horizontal*reach+Vector((0,0,rng.uniform(.4,.85)))
            elbow=root.lerp(tip,.55)+Vector((0,0,.20))
            base_radius=.055*(1-.3*j/len(p))
            secondary.append((root,elbow,tip,heading,li))
            branch([root,elbow,tip],[base_radius,.026,.003],6)
        secondary.append((p[-3],p[-2],p[-1],math.atan2(p[-1].y-p[-3].y,p[-1].x-p[-3].x),li))

    # Merge only the structural scaffold, leaving fine stems and leaves explicit.
    scaffold=mesh_factory('WillowV3Scaffold',verts,faces,bark,smooth=False)
    bpy.ops.object.select_all(action='DESELECT')
    scaffold.select_set(True); bpy.context.view_layer.objects.active=scaffold
    remesh=scaffold.modifiers.new('Joined structural forks','REMESH'); remesh.mode='VOXEL'; remesh.voxel_size=.043
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    soften=scaffold.modifiers.new('Flow through forks','SMOOTH'); soften.factor=.7; soften.iterations=4
    bpy.ops.object.modifier_apply(modifier=soften.name)
    decimate=scaffold.modifiers.new('Bark planes','DECIMATE'); decimate.ratio=.24
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    verts[:]=[tuple(v.co) for v in scaffold.data.vertices]
    faces[:]=[tuple(p.vertices) for p in scaffold.data.polygons]; indices[:]=[0]*len(faces)
    me=scaffold.data; bpy.data.objects.remove(scaffold,do_unlink=True); bpy.data.meshes.remove(me)
    for root,elbow,tip,heading,li in secondary:
        # Restore tapered tips finer than the remesh voxel size.
        branch([root,elbow,tip],[.037,.024,.0025],5)

    def leaf(base, direction, length, colour):
        d=Vector(direction).normalized()
        side=d.cross(Vector((.13,.23,1))).normalized()
        # Four triangles per folded lance leaf; a varied roll avoids edge-on rows.
        up=side.cross(d).normalized()
        roll=rng.uniform(-.85,.85)
        side=side*math.cos(roll)+up*math.sin(roll)
        mid=base+d*length*.43
        width=length*rng.uniform(.14,.20)
        start=len(verts)
        verts.extend([tuple(base),tuple(mid-side*width),tuple(base+d*length+Vector((0,0,-.035))),
                      tuple(mid+side*width),tuple(mid+up*length*.07)])
        for j in range(4): face((start+j,start+(j+1)%4,start+4),colour)

    def pendant(root, heading, length, colour, fullness):
        along=Vector((math.cos(heading),math.sin(heading),0))
        sway=Vector((-along.y,along.x,0))*rng.uniform(-.22,.22)
        points=[]
        for j in range(9):
            t=j/8
            points.append(root+along*(length*(.36*t+.08*math.sin(math.pi*t)))+
                          sway*math.sin(t*math.pi)+Vector((0,0,length*(.14*math.sin(t*math.pi)-.9*t*t))))
        tube(points,[.008,.0008],3)
        for j in range(1,9):
            for side in (-1,1):
                if rng.random()>fullness: continue
                t=(j-rng.uniform(0,.5))/8
                idx=min(7,int(t*8)); anchor=points[idx].lerp(points[idx+1],t*8-idx)
                a=heading+side*rng.uniform(.5,1.8)
                direction=Vector((math.cos(a)*.65,math.sin(a)*.65,-rng.uniform(.35,.9)))
                size=rng.uniform(.18,.29)*(1-.25*t)
                leaf(anchor,direction,size,colour if rng.random()<.8 else rng.choice([1,2,3,4,6]))

    for root,elbow,tip,heading,li in secondary:
        # Leaf masses overlap along a branch, while gaps between major limbs remain.
        mass_colour=[1,2,3,3,1,4,2,3][li]
        for k in range(rng.randint(4,6)):
            t=.24+k*.145
            anchor=elbow.lerp(tip,min(t,1))
            a=heading+(-1 if k%2 else 1)*rng.uniform(.4,1.5)
            length=rng.uniform(.42,.85)
            end=anchor+Vector((math.cos(a)*length,math.sin(a)*length,rng.uniform(.08,.35)))
            twig=curve([anchor,anchor.lerp(end,.5)+Vector((0,0,.08)),end],2)
            tube(twig,[.017,.0015],4)
            for n in range(rng.randint(4,6)):
                u=rng.uniform(.12,1)
                idx=min(len(twig)-2,int(u*(len(twig)-1)))
                pos=twig[idx].lerp(twig[idx+1],u*(len(twig)-1)-idx)
                pendant(pos,a+rng.uniform(-1.2,1.2),rng.uniform(.45,1.65),mass_colour,rng.uniform(.78,1))
            # Upward leaves tie the crown surface together above its pendant edges.
            for n in range(4):
                leaf(end,Vector((math.cos(a+n*1.6),math.sin(a+n*1.6),rng.uniform(-.1,.6))),rng.uniform(.16,.25),rng.choice([2,3,6]))

    ob=mesh_factory('SM_RF_Willow_Mature',verts,faces,bark,smooth=False)
    for m in mats[1:]: ob.data.materials.append(m)
    ca=ob.data.color_attributes['Color']
    for p,mi in zip(ob.data.polygons,indices):
        p.material_index=mi
        for loop in p.loop_indices:
            v=ob.data.vertices[ob.data.loops[loop].vertex_index].co
            if mi==0:
                # Long irregular grain following the wood, not a triangle checkerboard.
                grain=math.sin(v.x*17+v.y*12+.8*math.sin(v.z*1.1))
                broad=math.sin(v.x*5-v.y*4+v.z*.55+.6*math.sin(v.z))
                k=.77+.28*grain+.16*broad
                if broad<-.25:
                    colour=(k*.62,k*.83,k*1.28,1)
                else:
                    colour=(k*1.35,k*1.13,k*.91,1)
            else: colour=(1,1,1,1)
            ca.data[loop].color=colour
    bm=bmesh.new(); bm.from_mesh(ob.data)
    degenerate=[f for f in bm.faces if f.calc_area()<1e-10]
    bmesh.ops.delete(bm,geom=degenerate,context='FACES')
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    apply_bark(ob,wood_axes)
    assets[0]=ob
    return assets,collisions
