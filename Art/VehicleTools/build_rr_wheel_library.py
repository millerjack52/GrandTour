"""Approved Oct 25 wheel family. New empty output only; never saves the source car."""
import bpy, bmesh, math, json, sys, argparse, hashlib, shutil
from pathlib import Path
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).parent))
import wheel_fender_workshop as wf

P=argparse.ArgumentParser();P.add_argument('--output',required=True);P.add_argument('--samples',type=int,default=32)
A=P.parse_args(sys.argv[sys.argv.index('--')+1:]);OUT=Path(A.output)
if OUT.exists() and any(OUT.iterdir()):raise RuntimeError('Refusing overwrite: use a new empty revision')
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=Path('C:/GrandTour/Art/rangerover.blend')
REF=Path('C:/GrandTour/Art/References/Vehicles/RangeRoverCustomization_2026-10-25_v01/01-wheels-tyres.png')
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True)
R=.3795418; H=.12387025; SEG=128
spec={'outer_radius_m':R,'width_m':2*H,'rim_flange_radius_m':.222,'rim_flange_axial_m':[-.103,.103],
      'bead_seat_radius_m':.211,'axis':'X outward, front -Y, up Z; metres',
      'source_sha256':source_hash,'source':str(SOURCE),'reference':str(REF),
      'status':'Blender authoring components; no engine export or gameplay integration',
      'intentional_contacts':['tread bases embedded 1.5 mm in carcass','rim flange seats against tyre bead','hub/fasteners seat in rim web']}

def mat(name,c,metal=0,rough=.5):
    m=wf.material(name,c,rough,metal)
    n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=150;noise.inputs['Detail'].default_value=2
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.00035
    l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m
rubber=mat('GT | tyre charcoal',(.022,.026,.029),0,.78)
treadmat=mat('GT | tread rubber',(.029,.033,.036),0,.82)
steel=mat('GT | limestone steel',(.43,.42,.355),.62,.35)
alloy=mat('GT | satin silver alloy',(.53,.55,.55),.74,.28)
heavy=mat('GT | graphite steel',(.065,.074,.077),.65,.4)
edge=mat('GT | machined fasteners',(.40,.43,.44),.8,.25)
hubmat=mat('GT | dark hub',(.055,.063,.066),.3,.43)
def coll(name,kind):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);c['kind']=kind;c['interface']='GT_RR_16_V1';c['spec']=json.dumps(spec)
    root=bpy.data.objects.new(name+' | axle pivot',None);c.objects.link(root);root.empty_display_type='ARROWS';root.empty_display_size=.07
    root['mount']=True;root['axis']='+X outward';return c,root
def bevel(o,width=.0015):
    m=o.modifiers.new('Manufactured edge','BEVEL');m.width=width;m.segments=3
    m=o.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');m.keep_sharp=True
def rev(name,p,m,c,root,smooth=True):return wf.revolve(name,p,m,c,root,SEG,smooth)
def ring(name,x,r,thick,m,c,root):
    return rev(name,[(x+thick*math.cos(i*math.tau/8),r+thick*math.sin(i*math.tau/8)) for i in range(8)],m,c,root)
def cut_window(web,coords,c,root):
    vs=[(x,y,z) for x in [-.12,.17] for y,z in coords];n=len(coords)
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    cutter=wf.mesh('TEMP window',vs,fs,None,c,root)
    bpy.context.view_layer.objects.active=web
    md=web.modifiers.new('True ventilation opening','BOOLEAN');md.operation='DIFFERENCE';md.solver='EXACT';md.object=cutter
    bpy.ops.object.modifier_apply(modifier=md.name);bpy.data.objects.remove(cutter,do_unlink=True)

def rim(style):
    name=['Pressed Steel','Classic Alloy','Heavy Duty Steel'][style];c,root=coll('RIM | '+name,'rim');m=[steel,alloy,heavy][style]
    # One continuous double-sided barrel section, rolled flanges and bead seats.
    barrel=[(-.103,.219),(-.100,.222),(-.094,.222),(-.089,.215),(-.084,.211),(-.058,.210),(-.046,.201),
            (.046,.201),(.058,.210),(.084,.211),(.089,.215),(.094,.222),(.100,.222),(.103,.219),(.101,.212),
            (.090,.204),(.058,.200),(.046,.191),(-.046,.191),(-.058,.200),(-.090,.204),(-.101,.212)]
    rev(name+' | open barrel',barrel,m,c,root)
    ring(name+' | outer rolled lip',.099,.217,.003,alloy if style==1 else m,c,root)
    # A continuous shaped web is punched through; never hide holes behind a black disc.
    depth=[.048,.058,.030][style]
    web=rev(name+' | perforated dish',[(depth,.052),(depth,.089),(depth+.011,.108),(.078,.176),(.088,.202),(.078,.205),(.064,.177),(depth-.003,.108),(depth-.014,.089),(depth-.014,.052)],m,c,root)
    count=5 if style==1 else 8
    for i in range(count):
        a=i*math.tau/count
        if style==1:
            # Broad flared spokes with clipped trapezoidal windows in between.
            coords=[]
            for radius,angle in [(.113,-.17),(.119,-.25),(.176,-.32),(.189,-.25),(.189,.25),(.176,.32),(.119,.25),(.113,.17)]:
                coords.append((radius*math.sin(a+angle),radius*math.cos(a+angle)))
        else:
            cr=.150 if style==0 else .158;ry=.024 if style==0 else .021;rz=.029 if style==0 else .023
            coords=[]
            for j in range(32):
                t=j*math.tau/32;y=ry*math.sin(t);z=cr+rz*math.cos(t)
                coords.append((y*math.cos(a)+z*math.sin(a),-y*math.sin(a)+z*math.cos(a)))
        cut_window(web,coords,c,root)
    bm=bmesh.new();bm.from_mesh(web.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(web.data);bm.free()
    # Flat analytic strips avoid pinched interpolated normals around punched windows.
    # At 128 angular stations the circular dish remains visually smooth.
    for polygon in web.data.polygons:polygon.use_smooth=False
    bevel(web,.0025 if style==1 else .0018)
    rev(name+' | closed hub cap',[(depth-.010,.052),(depth+.014,.052),(depth+.029,.044),(depth+.031,.001),(depth-.010,.001)],hubmat,c,root)
    # Close tiny central bore with a physical end cap.
    wf.cylinder(name+' | cap centre',depth+.027,0,0,.008,.008,hubmat,c,root,32)
    for i in range(5):
        a=i*math.tau/5+.15;y=.074*math.sin(a);z=.074*math.cos(a)
        seat=wf.cylinder(name+' | lug seat',depth+.003,y,z,.014,.009,m,c,root,24);bevel(seat,.001)
        bolt=wf.cylinder(name+' | hex nut',depth+.016,y,z,.010,.018,edge,c,root,6);bevel(bolt,.001)
    a=.42;v=wf.cylinder(name+' | valve rubber',.091,.195*math.sin(a),.195*math.cos(a),.004,.022,hubmat,c,root,12);bevel(v,.0006)
    wf.cylinder(name+' | valve cap',.105,.195*math.sin(a),.195*math.cos(a),.0045,.008,hubmat,c,root,12)
    c['vent_count']=count;c['lug_count']=5;c.asset_mark();c.asset_data.description='Independent rim, metre scale, X axle, shared RR bead interface. '+name
    return c

def tyre(kind):
    name=['Road','All Terrain','Mud'][kind];c,root=coll('TYRE | '+name,'tyre');height=[.006,.012,.020][kind];cr=R-height
    # Authored carcass cross-section includes inner liner and both bead returns.
    p=[(-.090,.210),(-.104,.218),(-.116,.253),(-H,.289),(-.121,.320),(-.109,cr-.012),(-.090,cr-.003),(-.05,cr),
       (0,cr),(.05,cr),(.090,cr-.003),(.109,cr-.012),(.121,.320),(H,.289),(.116,.253),(.104,.218),(.090,.210),
       (.083,.215),(.094,.245),(.103,.285),(.101,.316),(.086,cr-.019),(.04,cr-.018),(-.04,cr-.018),(-.086,cr-.019),(-.101,.316),(-.103,.285),(-.094,.245),(-.083,.215)]
    rev(name+' | closed carcass with inner liner',p,rubber,c,root)
    def crown(x):
        ax=abs(x)
        if ax<=.05:return cr
        if ax<=.090:return cr-.003*(ax-.05)/.04
        return cr-.003-.009*(ax-.090)/.019
    vs=[];fs=[];blocks=[];count=[76,42,28][kind];step=math.tau/count
    bands=[(-.105,-.068),(-.063,-.025),(-.020,.020),(.025,.063),(.068,.105)] if kind==0 else [(-.110,-.057),(-.051,-.004),(.004,.051),(.057,.110)]
    if kind==2:bands=[(-.110,-.040),(-.034,.034),(.040,.110)]
    for row,(xa,xb) in enumerate(bands):
        for i in range(count):
            phase=(i+.46*(row%2))*step;half=[.45,.42,.39][kind]
            # Chamfered asymmetrical blocks, close pitch on road, open mud evacuation channels.
            clip=.003 if kind==0 else .007
            outline=[(xa+clip,-half),(xb-clip,-half),(xb,-half+.10),(xb,half-.10),(xb-clip,half),(xa+clip,half),(xa,half-.10),(xa,-half+.10)]
            # Divide road blocks with real transverse sipes, not painted grooves.
            outlines=[outline]
            if kind==1:
                # Offset tongue-and-recess planform makes connected-looking interlocking rows.
                mid=(xa+xb)/2
                outlines=[[(xa+clip,-half),(mid,-half),(mid+.004,-half+.11),(xb-clip,-half+.11),
                           (xb,-half+.18),(xb,half-.08),(xb-clip,half),(mid,half),(mid-.004,half-.12),
                           (xa+clip,half-.12),(xa,half-.20),(xa,-half+.08)]]
            elif kind==2:
                mid=(xa+xb)/2
                outlines=[[(xa+.005,-half+.11),(mid,-half),(xb-.006,-half+.10),(xb,half-.11),
                           (mid+.006,half+.10),(xa,half-.04)]]
            if kind==0:
                outlines=[]
                for low,high in [(-half,-.035),(.035,half)]:
                    outlines.append([(xa+clip,low),(xb-clip,low),(xb,low+.06),(xb,high-.06),(xb-clip,high),(xa+clip,high),(xa,high-.06),(xa,low+.06)])
            for points in outlines:
                base=len(vs);n=len(points)
                for layer in [0,1]:
                    for x,aa in points:
                        angle=phase+(aa+(x/(.11))*(.44 if kind==2 else .24 if kind else .14)*(1 if row<len(bands)/2 else -1))*step
                        radius=crown(x)-.0015+(height+.0015)*layer
                        vs.append((x,radius*math.sin(angle),radius*math.cos(angle)))
                fs += [tuple(base+j for j in range(n-1,-1,-1)),tuple(base+n+j for j in range(n))]
                fs += [(base+j,base+(j+1)%n,base+(j+1)%n+n,base+j+n) for j in range(n)]
                blocks.append(list(range(base,base+2*n)))
    ob=wf.mesh(name+' | individually shaped tread blocks',vs,fs,treadmat,c,root);bevel(ob,.0007 if kind==0 else .0015)
    ob['block_count']=len(blocks);ob['block_vertex_groups']=json.dumps(blocks)
    # Shoulder bars extend the outer blocks down onto the sidewall (same radial envelope).
    if kind>0:
        sv=[];sf=[]
        for side in [-1,1]:
            for j in range(count):
                angle=(j+(.46 if side>0 else 0))*step
                base=len(sv)
                for outer in [False,True]:
                    for x,rad,da in [(.100,cr-.008,-.25),(.118,.327,-.18),(.118,.327,.18),(.100,cr-.008,.25)]:
                        # Raised strip stays inside the measured maximum section width.
                        xx=side*(x+(0.002 if outer else -.002))
                        rr=rad+(.006 if outer else -.002)
                        sv.append((xx,rr*math.sin(angle+da*step),rr*math.cos(angle+da*step)))
                sf += [tuple(base+k for k in [0,3,2,1]),tuple(base+k for k in [4,5,6,7])]
                sf += [(base+k,base+(k+1)%4,base+(k+1)%4+4,base+k+4) for k in range(4)]
        sh=wf.mesh(name+' | wraparound shoulder lugs',sv,sf,treadmat,c,root);bevel(sh,.001)
    for side in [-1,1]:
        for r,x in [(.234,.110),(.249,.115),(.304,.123)]:ring(name+' | moulded sidewall ring',side*x,r,.0012,rubber,c,root)
        # Raised radial shoulder ribs follow the sidewall, well below the tread envelope.
        for j in range(32):
            a=j*math.tau/32
            pts=[]
            for rr in [.315,.326]:
                xx=.121 if rr==.315 else .117
                for da in [-.008,.008]:pts.append((side*(xx+.0005),rr*math.sin(a+da),rr*math.cos(a+da)))
            # Thin moulded rib with its back embedded in carcass.
            pts += [(x-side*.002,y,z) for x,y,z in pts]
            wf.mesh(name+' | shoulder rib',pts,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],rubber,c,root)
    c['outer_radius']=R;c['axial_half_width']=H;c['tread_depth']=height;c.asset_mark();c.asset_data.description='Independent '+name+' tyre, shared RR bead and outer envelope; actual tread geometry.'
    return c

rims=[rim(i) for i in range(3)];tyres=[tyre(i) for i in range(3)];parts=rims+tyres
for c in parts:
    for ob in c.objects:
        if ob.type!='MESH':continue
        bm=bmesh.new();bm.from_mesh(ob.data)
        for e in bm.edges:
            if len(e.link_faces)==2 and e.calc_face_angle()>math.radians(35):e.smooth=False
        bm.to_mesh(ob.data);bm.free();ob.data.update()
for c in parts:wf.seal(c)
shutil.copy2(REF,OUT/'approved-reference.png');bpy.data.images.load(str(REF)).pack()
for c in parts:bpy.context.scene.collection.children.unlink(c);c.use_fake_user=True
bpy.data.libraries.write(str(OUT/'GT_RangeRover_Wheel_Components.blend'),set(parts),fake_user=True)

def instance(c,name,location,rotation=None):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.instance_type='COLLECTION';o.instance_collection=c;o.location=location
    if rotation:o.rotation_euler=rotation
    return o
def setup():
    sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.render.engine='CYCLES';sc.cycles.samples=A.samples
    sc.cycles.use_denoising=True;sc.render.resolution_x=1600;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
    sc.render.threads_mode='FIXED';sc.render.threads=12
    sc.world=bpy.data.worlds.new('Soft grey studio');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.75,.69,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.7
    sc.view_settings.view_transform='AgX'
    for name,loc,power,size in [('Key',(4,-3,6),1300,5),('Fill',(-3,-1,3),900,4),('Rim',(1,4,5),1600,3)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        ob=bpy.data.objects.new(name,data);sc.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',data);sc.collection.objects.link(cam);sc.camera=cam;data.type='ORTHO';data.lens=55
    return sc
sc=setup()
def view(loc,target,scale):
    sc.camera.location=loc;sc.camera.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();sc.camera.data.ortho_scale=scale
def render(name,loc,target,scale):
    view(loc,target,scale);sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
def text_obj(body,loc,size=.075):
    cu=bpy.data.curves.new(body,'FONT');cu.body=body;cu.size=size;cu.align_x='CENTER';cu.extrude=.0001
    ob=bpy.data.objects.new(body,cu);sc.collection.objects.link(ob);ob.location=loc
    # Text lies in YZ plane, facing +X.
    ob.rotation_euler=(math.pi/2,0,math.pi/2);cu.materials.append(hubmat);return ob
stage=[]
for i in range(3):
    y=(i-1)*1.04
    stage += [instance(rims[i],'Rim display '+str(i),(0,y,1.28)),instance(rims[i],'Mounted rim '+str(i),(0,y,.38)),instance(tyres[i],'Mounted tyre '+str(i),(0,y,.38))]
    stage.append(text_obj(['PRESSED STEEL','CLASSIC ALLOY','HEAVY DUTY'][i],(.10,y,.89),.060))
    stage.append(text_obj(['ROAD','ALL TERRAIN','MUD'][i],(.10,y,-.07),.066))
readme=bpy.data.texts.new('START HERE - wheel library')
readme.write('Approved wheel family / October 25 2026\n\nSix asset collections: three rims and three tyres. Each has X-axis hub pivot at local origin, in metres. All nine combinations share a bead interface and the existing 759 mm outer tyre envelope.\nAppend collections from GT_RangeRover_Wheel_Components.blend and instance them at a hub. Rotate 180 degrees around Z for right side (no negative scale).\nThis presentation uses collection instances. Make Instance Real to author a local variant, or edit the original asset collection. Save a new revision. The builder refuses non-empty output folders; it does not overwrite manual work.\nRim/tyre meshes and materials are separate, tread is actual geometry, holes pass through the web. Raw authoring mesh with editable bevels: LOD/UV/Unreal integration not delivered here.\nSee verification.json, fit-review.json and spec.json for checked scope.\n')
sc['spec']=json.dumps(spec)
render('01-wheel-family',(5,-2.9,2.25),(0,0,.74),3.65)
render('02-front-orthographic',(6,0,.74),(0,0,.74),3.5)
render('03-top-orthographic',(0,0,7),(0,0,.74),3.5)
view((5,-2.9,2.25),(0,0,.74),3.65)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RangeRover_Wheels_Tyres.blend'))
for o in stage:bpy.data.objects.remove(o,do_unlink=True)
grid=[]
for i in range(3):
    for j in range(3):
        pos=(0,(i-1)*.95,(2-j)*.88+.38)
        grid += [instance(rims[i],'Combination rim',pos),instance(tyres[j],'Combination tyre',pos)]
render('04-all-nine-combinations',(6,-2.5,3.4),(0,0,1.26),3.45)
for o in grid:bpy.data.objects.remove(o,do_unlink=True)
close=[instance(rims[1],'Detail alloy',(0,0,0)),instance(tyres[1],'Detail tyre',(0,0,0))]
render('05-bead-and-rim-detail',(2,-1.2,.7),(0,0,0),.94)
for o in close:bpy.data.objects.remove(o,do_unlink=True)
rear=[instance(rims[0],'Rear detail',(0,0,0)),instance(tyres[0],'Rear tyre',(0,0,0))]
render('06-rear-bead-detail',(-2,-1,.6),(0,0,0),.94)
for o in rear:bpy.data.objects.remove(o,do_unlink=True)

# Context scene loads evaluated source meshes; original file remains completely untouched.
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):dst.objects=[n for n in src.objects if not n.startswith('Ref_')]
body=[];centres=[]
for o in dst.objects:
    if o:sc.collection.objects.link(o)
bpy.context.view_layer.update()
for o in dst.objects:
    if not o:continue
    if o.type!='MESH':o.hide_render=True;continue
    if o.name.lower().startswith('wheel'):
        vv=[o.matrix_world@v.co for v in o.data.vertices];centre=[(min(v[k] for v in vv)+max(v[k] for v in vv))/2 for k in range(3)]
        centres.append(centre);o.hide_render=True;o.hide_set(True)
    else:
        body.append(o)
        # Only display materials in this derivative: geometry and world transforms are unchanged.
        o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(wf.material('Context | green',(.10,.19,.12),.55) if not any(n in o.name.lower() for n in ['bumper','interior','pillar']) else hubmat)
wheel_instances=[]
for k,centre in enumerate(centres):
    rot=(0,0,math.pi) if centre[0]<0 else None
    wheel_instances += [instance(rims[0],'Fitted steel '+str(k),centre,rot),instance(tyres[1],'Fitted all terrain '+str(k),centre,rot)]
spec['measured_hub_centres_m']=centres
render('07-range-rover-fit',(6,-8,4),(0,0,.85),5.8)
render('08-range-rover-side',(7,0,1),(0,0,1),5.3)
render('09-range-rover-front',(0,-8,1),(0,0,1),2.7)
render('10-range-rover-top',(0,0,8),(0,0,0),5.3)
leftfront=min((v for v in centres if v[0]>0),key=lambda v:v[1])
render('11-fitted-front-detail',(3.1,-3.7,1.2),leftfront,1.28)
view((6,-8,4),(0,0,.85),5.8)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RangeRover_Wheel_Fit.blend'))
(OUT/'spec.json').write_text(json.dumps(spec,indent=2))
for f in [Path(__file__),Path(wf.__file__)]:shutil.copy2(f,OUT/f.name)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
print('WHEEL_BUILD_COMPLETE '+str(OUT),flush=True)
