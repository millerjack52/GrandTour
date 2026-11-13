"""Authored willow scaffolds, connected pendant foliage and lower-trunk UCX."""
import bpy, math, random
from mathutils import Vector

def build(mesh_factory, material_factory):
    bark=material_factory('M_RF_WillowBark',(.21,.135,.068),vertex=True)
    barklight=material_factory('M_RF_WillowBarkLight',(.34,.245,.135),vertex=True)
    barkdark=material_factory('M_RF_WillowBarkDark',(.085,.105,.12),vertex=True)
    leaves=[material_factory('M_RF_WillowLeaf'+str(i),c) for i,c in enumerate([
        (.29,.225,.09),(.38,.30,.14),(.235,.175,.07),(.23,.15,.065)])]
    mats=[bark,barklight,barkdark]+leaves
    assets=[]; collisions={}

    class Shape:
        def __init__(self,seed): self.v=[]; self.f=[]; self.mi=[]; self.r=random.Random(seed)
        def face(self,f,mat): self.f.append(f); self.mi.append(mat)
        def tube(self,points,radii,sides=7):
            start=len(self.v); points=[Vector(p) for p in points]
            for i,p in enumerate(points):
                tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
                u=tangent.cross(Vector((0,1,0))).normalized(); v=tangent.cross(u).normalized()
                for j in range(sides):
                    a=math.tau*j/sides
                    uneven=1+.045*math.sin(j*2.3+i*.8)
                    self.v.append(tuple(p+radii[i]*uneven*(u*math.cos(a)+v*math.sin(a))))
            self.face(tuple(start+j for j in reversed(range(sides))),0)
            for i in range(len(points)-1):
                for j in range(sides):
                    a=start+i*sides+j; b=start+i*sides+(j+1)%sides
                    self.face((a,b,b+sides,a+sides),0 if j%4 else 1)
            self.face(tuple(start+(len(points)-1)*sides+j for j in range(sides)),0)
        def unite_scaffold(self):
            ob=mesh_factory('TemporaryScaffold',self.v,self.f,bark,smooth=False)
            bpy.context.view_layer.objects.active=ob; ob.select_set(True)
            mod=ob.modifiers.new('Continuous forks','REMESH'); mod.mode='VOXEL'; mod.voxel_size=.065; mod.use_smooth_shade=False
            bpy.ops.object.modifier_apply(modifier=mod.name)
            mod=ob.modifiers.new('Soften fork joints','SMOOTH'); mod.factor=.65; mod.iterations=3
            bpy.ops.object.modifier_apply(modifier=mod.name)
            mod=ob.modifiers.new('Broad bark planes','DECIMATE'); mod.ratio=.22
            bpy.ops.object.modifier_apply(modifier=mod.name)
            self.v=[tuple(v.co) for v in ob.data.vertices]; self.f=[tuple(p.vertices) for p in ob.data.polygons]
            self.mi=[0]*len(self.f)
            old=ob.data; bpy.data.objects.remove(ob,do_unlink=True); bpy.data.meshes.remove(old)
        def leaf(self,base,direction,length,width,colour):
            base=Vector(base); d=Vector(direction).normalized()
            side=d.cross(Vector((.2,.4,1))).normalized()
            ridge=side.cross(d)*(.03*length)
            middle=base+d*length*.42; upper=base+d*length*.72+Vector((0,0,-length*.05)); end=base+d*length+Vector((0,0,-length*.15))
            start=len(self.v)
            self.v.extend([tuple(base),tuple(middle-side*width),tuple(upper-side*width*.55),tuple(end),tuple(upper+side*width*.55),tuple(middle+side*width),tuple(middle+ridge)])
            for j in range(6): self.face((start+j,start+(j+1)%6,start+6),colour)
        def shoot(self,root,heading,length,colour,leafy=True,leaf_scale=1):
            root=Vector(root); along=Vector((math.cos(heading),math.sin(heading),0))
            points=[]
            for j in range(7):
                t=j/6
                points.append(root+along*(.5*length*t)+Vector((0,0,.15*math.sin(t*math.pi)-length*t*t*.9)))
            self.tube(points,[.012*(1-j/7)+.001 for j in range(7)],3)
            if not leafy: return
            for j in range(1,7):
                for sign in [-1,1]:
                    a=heading+sign*self.r.uniform(.55,1.05)
                    direction=(math.cos(a)*.7,math.sin(a)*.7,-self.r.uniform(.5,.9))
                    self.leaf(points[j],direction,self.r.uniform(.21,.34)*leaf_scale,self.r.uniform(.033,.054)*leaf_scale,colour if self.r.random()<.82 else 4)
        def finish(self,name):
            ob=mesh_factory(name,self.v,self.f,mats[0],smooth=False)
            for m in mats[1:]: ob.data.materials.append(m)
            ca=ob.data.color_attributes['Color']
            for p,mat in zip(ob.data.polygons,self.mi):
                p.material_index=mat
                q=sum((ob.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
                patch=(math.sin(q.x*19+q.y*13+math.sin(q.z*1.1)*.8)+math.sin(q.x*7-q.y*15+q.z*.35))*.5
                if patch<-.57: tint=(.48,.68,1.06)
                elif patch<-.20: tint=(.77,.87,1.08)
                elif patch>.40: tint=(1.6,1.42,1.18)
                elif patch>.19: tint=(1.2,1.16,1.08)
                else: tint=(.94,.96,.96)
                for li in p.loop_indices:
                    v=ob.data.vertices[ob.data.loops[li].vertex_index].co
                    grain=(math.sin(v.x*11+v.y*7+math.sin(v.z*1.1)*.8)+math.sin(v.x*4-v.y*9+v.z*.35))*.5
                    k=.83+.30*grain+.10*math.sin(v.z*1.6+v.x*2)
                    cool=max(0,-grain-.20)*.6
                    ca.data[li].color=(k*tint[0],k*tint[1],k*tint[2],1) if mat<3 else (1,1,1,1)
            assets.append(ob); return ob

    trunk=[(0,0,-.13),(.12,.03,.45),(.02,0,1.05),(-.30,.02,1.75),(-.67,.05,2.45),(-.79,.10,3.15)]
    leaders=[
        ([(-.45,.03,2.05),(-1.20,.02,3.10),(-2.40,-.12,3.85),(-3.25,-.1,4.95),(-3.55,.1,6.10)],[.32,.26,.18,.09,.022]),
        ([(-.76,.09,2.95),(.02,-.1,3.68),(1.38,.05,4.05),(2.55,.33,4.73),(3.22,.45,5.60)],[.29,.24,.16,.09,.018]),
        ([(-.78,.10,2.90),(-.50,.30,4.05),(-.99,.20,5.13),(-.60,.48,6.27),(-.18,.67,7.12)],[.29,.23,.155,.08,.014]),
        ([(-.60,.1,2.65),(-.15,1.10,3.75),(.72,1.72,4.64),(1.36,2.10,5.63)],[.24,.18,.105,.02]),
        ([(-.27,-.08,1.9),(.55,-.72,2.83),(1.75,-1.25,3.27),(2.85,-1.48,3.58)],[.25,.19,.105,.018]),
    ]
    for variant in range(2):
        sh=Shape(1400+variant); r=sh.r
        size=1 if variant==0 else .76
        def scaled(p): return tuple(Vector(p)*size)
        spine=[scaled(p) for p in trunk]
        sh.tube(spine,[v*size for v in [.63,.48,.39,.34,.29,.18]],10)
        for j in range(6):
            a=j*math.tau/6+.25; reach=[1.25,.75,1,.95,.70,1.1][j]*size
            sh.tube([scaled((.06,0,.57)),(.40*math.cos(a)*size,.40*math.sin(a)*size,.14*size),(reach*math.cos(a),reach*math.sin(a),-.06)], [.27*size,.19*size,.035*size],7)
        chosen=leaders if variant==0 else [leaders[i] for i in [0,1,2,4]]
        for points,radii in chosen: sh.tube([scaled(p) for p in points],[v*size for v in radii],8)
        sh.unite_scaffold()
        for leader_index,(raw,radii) in enumerate(chosen):
            points=[Vector(scaled(p)) for p in raw]
            for k in range(2,len(points)):
                root=points[k-1].lerp(points[k],.52)
                forward=(points[k]-points[k-1]).normalized()
                for side in [-1,1]:
                    spread=Vector((-forward.y,forward.x,0)).normalized()*side
                    end=root+forward*r.uniform(.65,1.15)*size+spread*r.uniform(.65,1.3)*size+Vector((0,0,r.uniform(.45,.95)*size))
                    elbow=root.lerp(end,.58)+Vector((0,0,.20*size))
                    sh.tube([root,elbow,end],[.060*size,.033*size,.007*size],6)
                    heading=math.atan2(end.y-root.y,end.x-root.x)
                    leafy=variant==0 or (leader_index+k+(side==1))%3==0
                    for fan in range(3 if variant==0 else 2):
                        start=elbow.lerp(end,.2+fan*.30)
                        turn=heading+(fan-1)*.7+r.uniform(-.2,.2)
                        fan_tip=start+Vector((math.cos(turn)*r.uniform(.45,.85)*size,math.sin(turn)*r.uniform(.45,.85)*size,r.uniform(.0,.35)*size))
                        sh.tube([start,start.lerp(fan_tip,.6)+Vector((0,0,.10*size)),fan_tip],[.022*size,.012*size,.003*size],5)
                        for j in range(5 if variant==0 else 3):
                            anchor=start.lerp(fan_tip,r.uniform(.1,1))
                            if leafy:
                                sh.shoot(anchor,turn+r.uniform(-.65,.65),r.uniform(.55,1.45)*size,r.choice([3,3,4,5]))
                            elif j==0:
                                twig=anchor+Vector((math.cos(turn)*.28*size,math.sin(turn)*.28*size,.24*size))
                                sh.tube([anchor,twig,twig+Vector((-.08*size,.04*size,.16*size))],[.011*size,.006*size,.0015*size],4)
        name='SM_RF_Willow_Mature' if variant==0 else 'SM_RF_Willow_Young'
        sh.finish(name)
        hulls=[]
        for j in range(4):
            a=Vector(spine[j]); b=Vector(spine[j+1]); axis=(b-a).normalized()
            u=axis.cross(Vector((0,1,0))).normalized(); v=axis.cross(u).normalized(); radius=[.55,.46,.39,.34][j]*size
            vertices=[]
            for point in [a-axis*.04,b+axis*.04]:
                for k in range(8): vertices.append(tuple(point+radius*(u*math.cos(math.tau*k/8)+v*math.sin(math.tau*k/8))))
            faces=[tuple(reversed(range(8))),tuple(range(8,16))]+[(k,(k+1)%8,(k+1)%8+8,k+8) for k in range(8)]
            me=bpy.data.meshes.new('TrunkCollision'); me.from_pydata(vertices,[],faces); me.update()
            hull=bpy.data.objects.new('UCX_'+name+'_'+str(j).zfill(2),me); bpy.context.scene.collection.objects.link(hull)
            hull.hide_render=True; hull.hide_set(True); hulls.append(hull)
        collisions[name]=hulls

    for variant in range(2):
        sh=Shape(1510+variant); r=sh.r
        for j in range(8 if variant==0 else 12):
            a=j*2.399; base=Vector((r.uniform(-.12,.12),r.uniform(-.12,.12),-.03))
            end=Vector((math.cos(a)*r.uniform(.4,.8),math.sin(a)*r.uniform(.4,.8),r.uniform(.75,1.35)*(1 if variant==0 else .7)))
            elbow=base.lerp(end,.58)+Vector((0,0,.12))
            sh.tube([base,elbow,end],[.04,.023,.006],6)
            for k in [-1,1]:
                tip=end+Vector((math.cos(a+k*.65)*.25,math.sin(a+k*.65)*.25,.12))
                sh.tube([elbow,tip],[.015,.003],5)
                if variant==1 or j%2==0:
                    for twig in range(2 if variant==0 else 3):
                        root=elbow.lerp(tip,.45+twig*.20)
                        sh.shoot(root,a+k*.6+(twig-1)*.5,r.uniform(.28,.48),r.choice([3,4,5]),leaf_scale=.55)
        sh.finish('SM_RF_Scrub_Open' if variant==0 else 'SM_RF_Scrub_Dense')
    return assets,collisions
