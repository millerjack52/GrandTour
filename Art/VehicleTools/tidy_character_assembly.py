"""Repair the five user-identified assembly faults without rebuilding the car."""
import bpy,bmesh,json,sys,math,shutil,hashlib,argparse
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
import wheel_fender_workshop as wf
import door_window_workshop as dw
import cockpit_workshop as ck
import assembly_contracts as ac
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);src=Path(a.source);out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Use a new empty output revision; manual edits are preserved.')
out.mkdir(parents=True);source=src/'Crafted_Utility_Detailed.blend';sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene;S=json.loads((src/'shape-spec.json').read_text());R=S['registration'];P=R['pixels_per_metre']
before=ac.inspect(S);(out/'assembly-before.json').write_text(json.dumps(before,indent=2))
Y=lambda u:R['axle_front_world']+(u-R['front_hub_px'][0])/P
Z=lambda v:R['axle_z']+(R['front_hub_px'][1]-v)/P
U=lambda y:R['front_hub_px'][0]+(y-R['axle_front_world'])*P
V=lambda z:R['front_hub_px'][1]-(z-R['axle_z'])*P
def width(u,v):return ac.interp(v,S['side_section_v_width'])*ac.interp(u,S['longitudinal_width'])
def collection(n):
    c=bpy.data.collections.new(n);sc.collection.children.link(c);return c
repair=collection('Assembly repairs | mounts and junctions')
paint=bpy.data.materials['Dressed | olive enamel'];rubber=bpy.data.materials['Dressed | black rubber'];dark=bpy.data.materials['Dressed | interior shadows'];metal=bpy.data.materials['Dressed | warm metal']
trim=bpy.data.materials['Dressed | satin graphite']
def box(n,loc,dim,m,c=repair,b=.002):return dw.box(n,loc,dim,m,c,None,b)
changed={};removed=[]
def mark(ob,reason):changed[ob.name]=reason

# Local lower-cabin transition: the upper cabin is unchanged. At the belt, the
# cargo frame follows the rear body's plan taper instead of projecting past it.
def transition(co):
    u=U(co.y);v=V(co.z)
    if u<=634 or v<=100:return co.copy()
    fade=max(0,min(1,(v-100)/36));factor=1+(ac.interp(u,S['longitudinal_width'])-1)*fade
    return Vector((co.x*factor,co.y,co.z))
for cname in ['02 | Cabin and openings','Glazing | seals, wipers and mirrors']:
    for ob in bpy.data.collections[cname].objects:
        if ob.type!='MESH':continue
        if cname.startswith('Glazing') and not ('perimeter' in ob.name or 'demister' in ob.name or 'Rear pillar' in ob.name):continue
        maximum=0
        for vert in ob.data.vertices:
            new=transition(vert.co);maximum=max(maximum,(new-vert.co).length);vert.co=new
        if maximum>1e-7:mark(ob,'Lower rear cabin follows the actual body taper; upper frame and roof remain fixed.')
for ob in bpy.data.collections['01 | Primary surfaces'].objects:
    if not ob.name.startswith('Belt ledge'):continue
    for vert in ob.data.vertices:
        if abs(abs(vert.co.x)-S['cabin_half_width_bottom'])<.0001:vert.co=transition(vert.co)
    mark(ob,'Belt ledge upper boundary refitted to corrected lower cargo frame.')
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-6);bm.to_mesh(ob.data);bm.free()
bpy.context.view_layer.update()

panels=[o for o in sc.objects if o.type=='MESH' and 'derived skin' in o.name]
trees={o.name:ac.bvh(o) for o in panels}
def side_hit(side,y,z):
    hits=[]
    for ob in panels:
        if not ob.name.startswith('L' if side>0 else 'R'):continue
        hit=trees[ob.name].ray_cast(Vector((side*1.4,y,z)),Vector((-side,0,0)),.9)
        if hit[0] is not None:hits.append((hit[3],hit[0],ob))
    if not hits:
        estimate=Vector((side*width(U(y),V(z)),y,z));near=[]
        for ob in panels:
            if not ob.name.startswith('L' if side>0 else 'R'):continue
            hit=trees[ob.name].find_nearest(estimate)
            if hit[0] is not None:near.append((hit[3],hit[0],ob))
        nearest=min(near,key=lambda h:h[0])
        if nearest[0]>.003:raise RuntimeError('No nearby body surface at interface '+str((side,y,z,nearest[0])))
        return nearest[1:]
    return min(hits,key=lambda h:h[0])[1:]

# Build a single continuous arch lip/return from body contact through the whole
# wheelhouse depth. The aperture path is unchanged; the old liner gap is removed.
arch_collection=bpy.data.collections['01 | Primary surfaces']
for side in [-1,1]:
    for key in ['front_arch_uv','rear_arch_uv']:
        for ob in list(arch_collection.objects):
            if ob.name.startswith(str(side)+' | '+key):
                removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
        path=S[key];verts=[];faces=[];seating=[];outer=[]
        for i,(u,v) in enumerate(path):
            prev=Vector(path[max(0,i-1)]);nxt=Vector(path[min(len(path)-1,i+1)]);t=(nxt-prev).normalized();normal=Vector((t.y,-t.x))
            uv=Vector((u,v))+normal*(S['arch_lip_width']*P)
            outer.append(uv)
        samples=[]
        for i,(aa,bb) in enumerate(zip(path,path[1:])):
            count=max(1,math.ceil(math.dist(aa,bb)))
            for j in range(count):
                t=j/count;inner=Vector(aa).lerp(Vector(bb),t);uv=outer[i].lerp(outer[i+1],t);samples.append((inner,uv))
        samples.append((Vector(path[-1]),outer[-1]))
        for inner,uv in samples:
            u,v=inner
            # The top of the lip seats on the actual panel, not an approximate
            # width formula. Endpoints near the sill may lie beyond the skin;
            # clamp just above the sill to provide a formed return there.
            uv.y=min(uv.y,277.7)
            hit,panel=side_hit(side,Y(uv.x),Z(uv.y));seat=(hit.x+side*.0005,hit.y,hit.z)
            seating.append(len(verts));verts.append(seat)
            verts.append((side*(width(u,v)+.009),Y(u),Z(v)))
            verts.append((side*.600,Y(u),Z(v)))
        for j in range(len(samples)-1):
            i=j*3;faces.extend([(i,i+3,i+4,i+1),(i+1,i+4,i+5,i+2)])
        ob=wf.mesh(str(side)+' | '+key+' narrow lip',verts,faces,paint,arch_collection)
        ob.data.materials.append(dark)
        for face in ob.data.polygons:face.material_index=face.index%2
        mod=ob.modifiers.new('Formed lip and continuous inward return','SOLIDIFY');mod.thickness=.006;mod.offset=-1
        ob['contact_edge_indices']=json.dumps(seating);ob['interface']='body seating edge -> aperture edge -> inboard wheelhouse at x=0.600'
        mark(ob,'Rebuilt continuous lip/liner with measured body seating edge; aperture coordinates retained.')
        back=[(side*.600,Y(u),Z(v)) for u,v in path]
        cap=wf.mesh(str(side)+' | '+key+' recessed backing',back,[tuple(range(len(back)))],dark,arch_collection)
        mod=cap.modifiers.new('Inboard tub wall','SOLIDIFY');mod.thickness=.006;mod.offset=1 if side>0 else -1
        mark(cap,'Inboard tub wall meets the continuous arch return.')

# Bench width is limited by the wheelhouse, not the outer body width. Its height,
# fore/aft position and original upholstery remain unchanged.
c=bpy.data.collections['Cabin | Rear bench'];root=next(o for o in c.objects if o.get('mount'))
maxhalf=max(abs(v.co.x) for o in c.objects if o.type=='MESH' for v in o.data.vertices)
root.scale.x=.565/maxhalf;root['fit_note']='Outer bench half-width 0.565; wheelhouse boundary 0.600, nominal 35 mm lateral space.'
for ob in c.objects:
    if ob.type=='MESH':mark(ob,'Whole bench narrowed to fit between the measured wheelhouse volumes.')

# Harmonize wheel section. Radial dimensions, centres and tread diameter stay
# fixed. Rubber gains sidewall bulge; rim/barrel/hub axial depth is refitted.
tyre_profile=[(-.114,.216),(-.114,.233),(-.135,.290),(-.132,.334),(-.110,.364),(-.065,.3726),(0,.376),(.065,.3726),(.110,.364),(.132,.334),(.135,.290),(.114,.233),(.114,.216),(.100,.216),(.087,.235),(-.087,.235),(-.100,.216)]
outward=[(.216,.114),(.233,.114),(.290,.135),(.334,.132),(.364,.110),(.3726,.065),(.376,0)]
for c in [c for c in bpy.data.collections if c.name.endswith('| Detailed wheel')]:
    root=next(o for o in c.objects if o.get('mount'));old=next(o for o in c.objects if o.name.startswith('Tyre | shaped carcass'));name=old.name;mat=old.data.materials[0]
    bpy.data.objects.remove(old,do_unlink=True);ob=wf.revolve(name,tyre_profile,mat,c,root,64,True);mark(ob,'New shared bead/sidewall section, unchanged radial envelope.')
    for ob in list(c.objects):
        if ob.type!='MESH' or ob.name==name:continue
        if ob.name.startswith('Tyre | staggered tread'):
            for v in ob.data.vertices:v.co.x*=1.125
            mark(ob,'Tread width refitted to 270 mm carcass; radial coordinates unchanged.')
        elif ob.name.startswith('Tyre | moulded sidewall rib'):
            for v in ob.data.vertices:v.co.x=ac.interp(math.hypot(v.co.y,v.co.z),outward)+.0007
            mark(ob,'Moulded rib now follows the actual tyre sidewall.')
        elif ob.name.startswith(('Rim |','Wheel |','Brake |')):
            for v in ob.data.vertices:v.co.x*=.8
            mark(ob,'Rim/barrel/hardware axial width reduced to fit tyre beads and sidewalls.')
    for ob in c.objects:
        if ob.type=='CURVE' and ob.get('profile_guide'):ob['status']='Historical guide; tyre section now recorded in repair-manifest.json.'

# Visible mounted mudflaps: direct chain through a clamp and hanger into the
# actual side skin. Keep the current fore/aft positions and enlarge flap width
# to cover the corrected tyres.
bpy.context.view_layer.update()
for flap in [o for o in sc.objects if o.type=='MESH' and o.name.startswith('Mudflap | flexible rubber')]:
    lo,hi=ac.bounds(flap);side=1 if (lo[0]+hi[0])>0 else -1;cx=(lo[0]+hi[0])/2;cy=(lo[1]+hi[1])/2;top=hi[2]
    for v in flap.data.vertices:v.co.x=cx+(v.co.x-cx)*(.270/.230)
    contact,panel=side_hit(side,cy,.565)
    clamp=box('Mudflap mount | clamp '+flap.name,(cx,cy,top-.006),(.278,.027,.025),trim)
    hangx=contact.x-side*.014
    hanger=box('Mudflap mount | body hanger '+flap.name,(hangx,cy,(top-.018+.578)/2),(.021,.039,.578-(top-.018)),trim)
    for dx in [-.085,.085]:ck.rod('Mudflap mount | bolt',(cx+dx,cy-.020,top-.006),(cx+dx,cy+.020,top-.006),.006,metal,repair,None)
    flap['mount_clamp']=clamp.name;flap['mount_hanger']=hanger.name;flap['mount_panel']=panel.name
    mark(flap,'Flap widened to tyre and attached through clamp/hanger to the measured body surface.')

bpy.context.view_layer.update();after=ac.inspect(S)
(out/'assembly-contracts.json').write_text(json.dumps(after,indent=2))
manifest={'source':str(source),'source_sha256':sha,'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==sha,
 'changed_objects':changed,'removed_objects':removed,'tyre_profile_local_x_radius':tyre_profile,
 'protected_shape_exceptions':[n for n in changed if n in [o.name for c in ['01 | Primary surfaces','02 | Cabin and openings'] for o in bpy.data.collections[c].objects]],
 'scope':'Localized assembly repairs requested by user. Approved main panels, bonnet, roof, wheel centres and tread diameter retained.'}
(out/'repair-manifest.json').write_text(json.dumps(manifest,indent=2))
for name in ['shape-spec.json','shape-map.json','preservation-checks.json','side-reference.png','original-a-reference.png']:
    if (src/name).exists():shutil.copy2(src/name,out/name)
for name in ['tidy_character_assembly.py','assembly_contracts.py','floor_contracts.py','check_assembly_contracts.py','wheel_fender_workshop.py','door_window_workshop.py','cockpit_workshop.py']:shutil.copy2(ROOT/name,out/name)
sc['status']='Assembly tidy pass: rear pillar, arch joints, wheelhouse seating, mudflap mounting, tyre/rim section. Review pending.'
text=bpy.data.texts.new('ASSEMBLY REPAIRS | user feedback');text.write(json.dumps(manifest,indent=2))

def cam(name,loc,target,scale,w=1100,h=850):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;o['resolution']=[w,h];return o
reviews={'rear-low':cam('QA | rear low',(3.7,6.0,.32),(0,1.3,.95),3.2),
 'arch-close':cam('QA | rear arch low',(4.7,3.5,.69),(.72,1.25,.74),1.65),
 'pillar-close':cam('QA | rear pillar low',(4.2,5.0,.73),(.69,1.93,1.29),1.10),
 'wheel-section':cam('QA | wheel axial section',(3.7,-2.4,.71),(.8,-1.39,.45),1.10),
 'wheel-off':cam('QA | rear wheel removed',(4.2,2.8,.68),(.60,1.25,.76),1.55)}
views={'quarter':bpy.data.objects['Front quarter | volume review'],'side':bpy.data.objects['Side | fixed reference registration'],
 'rear-quarter':bpy.data.objects['Rear quarter | return review'],'front':bpy.data.objects['Front | section review'],'top':bpy.data.objects['Top | width review'],**reviews}
sc.cycles.samples=24
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Crafted_Utility_Detailed.blend'))
for key,view in views.items():
    hidden=[]
    if key=='rear-low':
        ground=bpy.data.objects.get('Ground')
        if ground and not ground.hide_render:ground.hide_render=True;hidden.append(ground)
    if key=='wheel-off':
        for c in bpy.data.collections:
            if c.name.endswith('| Detailed wheel') and c.name.startswith('Rear'):
                for ob in c.objects:
                    if not ob.hide_render:ob.hide_render=True;hidden.append(ob)
    sc.camera=view;sc.render.resolution_x,sc.render.resolution_y=view['resolution'];sc.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True)
    for ob in hidden:ob.hide_render=False
sc.camera=views['quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];bpy.ops.wm.save_as_mainfile(filepath=str(out/'Crafted_Utility_Detailed.blend'))
print('TIDY_READY '+str(out));print(json.dumps({k:v.get('passed') for k,v in after.items() if isinstance(v,dict)},indent=2))
