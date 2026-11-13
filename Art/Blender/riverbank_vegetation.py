"""Reusable low-poly riverbank meshes, local metre coordinates and trunk-only UCX."""
import bpy, math, random
from mathutils import Vector

def build(mesh_factory, material_factory):
    bark=material_factory('M_RF_WillowBark',(.20,.125,.063))
    barklight=material_factory('M_RF_WillowBarkLight',(.34,.245,.13))
    barkdark=material_factory('M_RF_WillowBarkDark',(.095,.08,.055))
    leaves=[material_factory('M_RF_WillowLeaf'+str(i),color) for i,color in enumerate([
        (.47,.31,.045),(.67,.46,.08),(.235,.30,.027),(.32,.19,.035)])]
    mats=[bark,barklight,barkdark]+leaves
    assets=[]; collisions={}

    class Shape:
        def __init__(self,seed): self.v=[]; self.f=[]; self.mi=[]; self.r=random.Random(seed)
        def face(self,indices,mat): self.f.append(indices); self.mi.append(mat)
        def tube(self,points,radii,sides=6):
            start=len(self.v)
            for i,point in enumerate(points):
                p=Vector(point)
                tangent=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized()
                u=tangent.cross(Vector((0,1,0))).normalized(); v=tangent.cross(u).normalized()
                for j in range(sides):
                    a=math.tau*j/sides
                    self.v.append(tuple(p+radii[i]*(u*math.cos(a)+v*math.sin(a))))
            self.face(tuple(start+j for j in reversed(range(sides))),2)
            for i in range(len(points)-1):
                for j in range(sides):
                    a=start+i*sides+j; b=start+i*sides+(j+1)%sides
                    self.face((a,b,b+sides,a+sides),[0,0,1,0,2,0][j%6])
            self.face(tuple(start+(len(points)-1)*sides+j for j in range(sides)),0)
        def foliage(self,point,size):
            # Bent lance-shaped leaves preserve open crowns and a readable silhouette.
            p=Vector(point)
            count=48 if size[2]>.5 else 24
            for _ in range(count):
                a=self.r.uniform(0,math.tau); radius=math.sqrt(self.r.random())
                q=p+Vector((math.cos(a)*size[0]*radius,math.sin(a)*size[1]*radius,self.r.uniform(-.55,.55)*size[2]))
                heading=self.r.uniform(0,math.tau)
                side=Vector((math.cos(heading),math.sin(heading),0))
                direction=Vector((-math.sin(heading)*.4,math.cos(heading)*.4,-1)).normalized()
                length=self.r.uniform(.20,.40); width=self.r.uniform(.045,.085)
                ridge=side.cross(direction)*.035
                start=len(self.v)
                self.v.extend([tuple(q-direction*length*.5),tuple(q-side*width),tuple(q+ridge),tuple(q+side*width),tuple(q+direction*length*.7)])
                colour=self.r.choice([3,3,4,5,6])
                for f in [(0,1,2),(0,2,3),(1,4,2),(2,4,3)]: self.face(tuple(start+k for k in f),colour)
        def finish(self,name):
            ob=mesh_factory(name,self.v,self.f,mats[0],smooth=False)
            for mat in mats[1:]: ob.data.materials.append(mat)
            for polygon,index in zip(ob.data.polygons,self.mi): polygon.material_index=index
            assets.append(ob); return ob

    for variant in range(2):
        sh=Shape(810+variant); r=sh.r
        tall=1 if variant==0 else .72
        name='SM_RF_Willow_Mature' if variant==0 else 'SM_RF_Willow_Young'
        spine=[(0,0,-.10),(.13,-.06,1.1),(.30,.04,2.35),(.13,.13,3.45),(.33,.10,4.6),(.65,.08,5.65),(.91,.18,6.6)]
        spine=[tuple(Vector(p)*tall) for p in spine]
        sh.tube(spine,[x*tall for x in [.32,.26,.205,.16,.10,.045,.009]],8)
        # Visible buttress roots join the trunk at the bank, without a flat cylinder base.
        for j in range(5):
            a=math.tau*j/5+.25
            sh.tube([(math.cos(a)*.66*tall,math.sin(a)*.66*tall,-.03),(.06,.02,.36*tall),spine[1]],[.08*tall,.16*tall,.16*tall],5)
        for j in range(10 if variant==0 else 8):
            a=j*2.399+.25; z=(1.7+j*.29)*tall
            root=Vector((.19,.06,z)); radius=r.uniform(1.7,2.7)*tall
            direction=Vector((math.cos(a),math.sin(a),0))
            elbow=root+direction*radius*.43+Vector((0,0,.95*tall))
            fork=root+direction*radius*.8+Vector((0,0,1.8*tall))
            tip=root+direction*radius+Vector((0,0,2.45*tall))
            sh.tube([root,elbow,fork,tip],[.14*tall,.10*tall,.048*tall,.006*tall],6)
            for k in range(3):
                anchor=elbow.lerp(fork,.25+k*.28)
                heading=a+(k-1)*.68
                twig=Vector((math.cos(heading),math.sin(heading),0))
                end=anchor+twig*r.uniform(.8,1.55)*tall+Vector((0,0,r.uniform(.9,1.7)*tall))
                mid=anchor.lerp(end,.6)+Vector((0,0,.18*tall))
                sh.tube([anchor,mid,end],[.039*tall,.022*tall,.003*tall],5)
                # Sparse crowns leave the branching structure visible like the supplied ford photos.
                if r.random() < (.68 if variant==0 else .48):
                    for offset in [0,.4]:
                        point=end-twig*offset*tall+Vector((0,0,-.10-offset*.6))
                        sh.foliage(point,(r.uniform(.42,.68)*tall,r.uniform(.28,.49)*tall,r.uniform(.72,1.25)*tall))
                branch=mid+Vector((-twig.y,twig.x,.55))*.45*tall
                sh.tube([mid,branch],[.014*tall,.002*tall],4)
        tree=sh.finish(name)
        # Capsule-like convex prisms cover the lower trunk only: canopy never blocks the car.
        hulls=[]
        for j in range(3):
            a=Vector(spine[j]); b=Vector(spine[j+1]); axis=(b-a).normalized()
            u=axis.cross(Vector((0,1,0))).normalized(); v=axis.cross(u).normalized()
            radius=[.33,.27,.21][j]*tall; verts=[]
            for point in [a-axis*.05,b+axis*.05]:
                for k in range(8): verts.append(tuple(point+radius*(u*math.cos(math.tau*k/8)+v*math.sin(math.tau*k/8))))
            faces=[tuple(reversed(range(8))),tuple(range(8,16))]+[(k,(k+1)%8,(k+1)%8+8,k+8) for k in range(8)]
            me=bpy.data.meshes.new('TrunkCollision'); me.from_pydata(verts,[],faces); me.update()
            hull=bpy.data.objects.new('UCX_'+name+'_'+str(j).zfill(2),me); bpy.context.scene.collection.objects.link(hull)
            hull.hide_render=True; hull.hide_set(True); hulls.append(hull)
        collisions[name]=hulls

    for variant in range(2):
        sh=Shape(910+variant); r=sh.r; height=1.25 if variant==0 else .8
        for j in range(11):
            a=j*2.399; root=Vector((r.uniform(-.10,.10),r.uniform(-.10,.10),-.02))
            end=Vector((math.cos(a)*r.uniform(.3,.8),math.sin(a)*r.uniform(.3,.8),r.uniform(.65,1.05)*height))
            mid=root.lerp(end,.6)+Vector((0,0,.15))
            sh.tube([root,mid,end],[.034,.018,.0025],5)
            for k in [-1,1]:
                twig=mid.lerp(end,.3)+Vector((math.cos(a+k*.7)*.28,math.sin(a+k*.7)*.28,.23))
                sh.tube([mid,twig],[.012,.002],4)
            if variant==1 or j%3==0: sh.foliage(end,(.30,.24,.43))
        sh.finish('SM_RF_Scrub_Open' if variant==0 else 'SM_RF_Scrub_Dense')
    return assets,collisions
