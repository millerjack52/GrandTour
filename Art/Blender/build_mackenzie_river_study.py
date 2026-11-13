"""Export a continuous study bed, clipped water and reusable worn cobbles."""
from pathlib import Path
import sys,math,json,random,bisect
import bpy,numpy as np
from mathutils import noise,Vector
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/MackenzieRiverStudy';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from mackenzie_river_study_shape import height,silt
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
parts=[]
def export(name,vertices,faces,smooth=True):
    # Input is UE cm. FBX exports Blender metres with reflected Y.
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in vertices],[],[list(reversed(f)) for f in faces]);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:p.use_smooth=smooth
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    if name=='SM_MRS_Water':
        # Keep the regular wave grid; only weld shared clipping vertices.
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.00001);bpy.ops.object.mode_set(mode='OBJECT')
        mesh=obj.data
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False)
    obj.select_set(False);parts.append(dict(name=name,vertices=len(mesh.vertices),triangles=sum(len(p.vertices)-2 for p in mesh.polygons)))

def graded_axis(extent,bands):
    positive=[0]
    for limit,step in bands:
        positive.extend(range(positive[-1]+step,min(limit,extent)+1,step))
    return [-v for v in reversed(positive[1:])]+positive

xs=graded_axis(60000,[(1800,5),(4500,20),(10000,50),(60000,100)])
ys=[v for v in graded_axis(26000,[(1000,5),(2600,20),(6000,100),(26000,200)]) if v<=2600]
def spacing(axis,i):
    return max(axis[min(i+1,len(axis)-1)]-axis[i],axis[i]-axis[max(0,i-1)])
nx=len(xs)
verts=[(x,y,height(x,y,max(spacing(xs,i),spacing(ys,j)))) for j,y in enumerate(ys) for i,x in enumerate(xs)]
# Coherent sub-centimetre relief from the same scan as colour/normal/POM.
# Fine topology is local to the 36 m review area, outer bed stays inexpensive.
im=bpy.data.images.load(str(ROOT/'Art/Textures/MackenzieRiver/ganges_river_pebbles_disp_2k.png'))
im.colorspace_settings.name='Non-Color'
pix=np.array(im.pixels[:],dtype=np.float32).reshape(im.size[1],im.size[0],4)[::-1,:,0]
for k,(x,y,z) in enumerate(verts):
    if abs(x)<=1800 and -1000<=y<=1000:
        h=float(pix[int((y/135%1)*im.size[1])%im.size[1],int((x/135%1)*im.size[0])%im.size[0]])
        fade=min(1,max(0,(1800-abs(x))/100),max(0,(1000-abs(y))/100))
        verts[k]=(x,y,z+(h-.5)*1.8*(1-silt(x,y))*fade)
faces=[];water_v=[];water_f=[]
for j in range(len(ys)-1):
    for i in range(nx-1):
        a=j*nx+i
        for tri in [(a,a+1,a+nx+1),(a,a+nx+1,a+nx)]:
            faces.append(tri)
export('SM_MRS_Bed',verts,faces)
# Retain wave-supporting geometry beyond the close-up reach. The old abrupt
# 25 cm -> 5 m boundary made both displacement and the clipped bank angular.
wx=graded_axis(60000,[(4500,25),(18000,50),(60000,100)])
wy=list(range(-2000,2001,25));wn=len(wx)
def bed_height(x,y):
    i=max(0,min(nx-2,bisect.bisect_right(xs,x)-1))
    j=max(0,min(len(ys)-2,bisect.bisect_right(ys,y)-1))
    u=(x-xs[i])/(xs[i+1]-xs[i]);v=(y-ys[j])/(ys[j+1]-ys[j]);a=j*nx+i
    z00,z10,z01,z11=(verts[k][2] for k in (a,a+1,a+nx,a+nx+1))
    return z00+(z10-z00)*u+(z11-z10)*v if v<=u else z00+(z11-z01)*u+(z01-z00)*v
wv=[(x,y,bed_height(x,y)) for y in wy for x in wx]
for j in range(len(wy)-1):
    for i in range(wn-1):
        a=j*wn+i
        for tri in [(a,a+1,a+wn+1),(a,a+wn+1,a+wn)]:
            poly=[wv[k] for k in tri];out=[]
            for k,p in enumerate(poly):
                q=poly[(k+1)%3];h=-p[2]-.12;hq=-q[2]-.12
                if h>=0:out.append((p[0],p[1],0))
                if (h>=0)!=(hq>=0):
                    t=h/(h-hq);out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1]),0))
            if len(out)>2:
                k=len(water_v);water_v.extend(out)
                for t in range(1,len(out)-1):water_f.append((k,k+t,k+t+1))
export('SM_MRS_Water',water_v,water_f)

# Context landforms outside the detailed reach; no claim of a surveyed location.
verts=[];faces=[];n=100
for j in range(n+1):
    for i in range(n+1):
        x=-60000+i*1200;y=2600+j*900
        ramp=1-math.exp(-max(0,y-4000)/14000)
        z=80+ramp*(2600+1800*math.sin(x/8500+y/13000)+1700*noise.fractal(Vector((x/16000,y/14000,.7)),1.,2.,4))
        verts.append((x,y,z))
for j in range(n):
    for i in range(n):
        a=j*(n+1)+i;faces.extend([(a,a+1,a+n+2),(a,a+n+2,a+n+1)])
export('SM_MRS_Hills',verts,faces)

for kind in range(8):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1)
    obj=bpy.context.object;verts=[]
    for v in obj.data.vertices:
        p=v.co;ns=noise.noise_vector(p*2.1+Vector((kind*7.1,kind*.31,2)))
        r=1+.14*ns.x+.055*noise.noise(p*5+Vector((kind,0,0)))
        verts.append((p.x*r*10,p.y*r*(6.4+kind*.22),p.z*r*(4.2+(kind%3)*.65)))
    faces=[tuple(p.vertices) for p in obj.data.polygons];bpy.data.objects.remove(obj,do_unlink=True)
    export('SM_MRS_Cobble'+str(kind),verts,faces)
(OUT/'geometry.json').write_text(json.dumps(dict(parts=parts,water_level_cm=0,bed_extent_cm=[min(xs),max(xs),min(ys),max(ys)],detail_extent_cm=[-1800,1800,-1000,1000]),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MackenzieRiverStudy.blend'))
print('MACKENZIE_RIVER_GEOMETRY_OK')
