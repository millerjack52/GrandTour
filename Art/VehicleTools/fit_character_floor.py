"""Fit the cabin floor in a new revision, preserving the rest of the assembly."""
import bpy,sys,json,shutil,hashlib,argparse,bmesh
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
import assembly_contracts as ac
import floor_contracts as fc
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);src=Path(a.source);out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Use a fresh empty output folder.')
out.mkdir(parents=True,exist_ok=True)
source=src/'Crafted_Utility_Detailed.blend';sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene
S=json.loads((src/'shape-spec.json').read_text());R=S['registration'];P=R['pixels_per_metre']
Y=lambda u:R['axle_front_world']+(u-R['front_hub_px'][0])/P
U=lambda y:R['front_hub_px'][0]+(y-R['axle_front_world'])*P
V=lambda z:R['front_hub_px'][1]-(z-R['axle_z'])*P
def width(y,z):return ac.interp(V(z),S['side_section_v_width'])*ac.interp(U(y),S['longitudinal_width'])
def rear_y(z):return Y(ac.interp(V(z),[(v,u) for u,v in S['rear_profile_uv']]))
before=fc.inspect(S);(out/'floor-before.json').write_text(json.dumps(before,indent=2))
removed=['Cabin | central floor','Cabin | cargo floor']
baseline={o.name:([tuple(v.co) for v in o.data.vertices],[list(r) for r in o.matrix_world]) for o in sc.objects if o.type=='MESH' and o.name not in removed}
for n in removed:bpy.data.objects.remove(bpy.data.objects[n],do_unlink=True)
c=bpy.data.collections.new('Cabin | fitted floor pan');sc.collection.children.link(c)
mat=bpy.data.materials['Dressed | interior shadows'];zt=.568;thickness=.018
# Intersect the wheelhouse profile with the floor plane. The narrow centre
# continues into each inner tub; full-width sections occupy only solid body.
rear=S['rear_arch_uv'];v=V(zt)
cross=[]
for (ua,va),(ub,vb) in zip(rear,rear[1:]):
    if min(va,vb)<=v<=max(va,vb):cross.append(Y(ua+(ub-ua)*(v-va)/(vb-va)))
ya,yb=min(cross),max(cross)
end=rear_y(zt)-.001
rows=[]
for lo,hi,narrow in [(-.900,ya,False),(ya,yb,True),(yb,end,False)]:
    n=max(2,int((hi-lo)/.015)+1)
    for j in range(n+1):
        y=lo+(hi-lo)*j/n;rows.append((y,.599 if narrow else width(y,zt)-.003))
outline=[(w,y,zt) for y,w in rows]+[(-w,y,zt) for y,w in reversed(rows)]
# Remove only duplicate adjacent points; preserve the inward notch at each tub.
clean=[]
for q in outline:
    if not clean or (Vector(q)-Vector(clean[-1])).length>1e-7:clean.append(q)
def mesh(n,verts,faces):
    me=bpy.data.meshes.new(n);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(n,me);c.objects.link(ob);me.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();return ob
N=len(clean);bottom=[((1 if x>0 else -1)*(width(y,zt-thickness)-.003) if abs(x)>.61 else x,min(y,rear_y(zt-thickness)-.001),z-thickness) for x,y,z in clean]
pan=mesh('Floor pan | continuous cabin and cargo',clean+bottom,[tuple(range(N)),tuple(range(2*N-1,N-1,-1))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)])
pan['interface']='Full width to body; inset to +/-0.599 at rear wheelhouses; floor top 0.568 m.'
# Rolled-down sill returns close oblique lines of sight below the horizontal
# floor. They meet the real side section, with their upper edge inside the pan.
for side in [-1,1]:
    for index,(lo,hi) in enumerate([(-.90,ya-.001),(yb+.001,rear_y(.478)-.001)]):
        verts=[];faces=[];n=max(2,int((hi-lo)/.015)+1)
        for j in range(n+1):
            y=lo+(hi-lo)*j/n
            verts.extend([(side*(width(y,zt)-.006),y,zt-.002),(side*(width(y,.478)-.006),y,.478)])
        for j in range(n):faces.append((2*j,2*j+1,2*j+3,2*j+2))
        ob=mesh('Floor pan | sill return '+str(side)+' '+str(index),verts,faces)
        mod=ob.modifiers.new('Sheet thickness','SOLIDIFY');mod.thickness=.004;mod.offset=0
# Front upstand closes the footwell beneath the dash; the engine bay stays open.
w=width(-.90,zt)-.005
ob=mesh('Floor pan | front footwell upstand',[(-w,-.900,.554),(w,-.900,.554),(w,-.900,.90),(-w,-.900,.90)],[(0,1,2,3)])
mod=ob.modifiers.new('Sheet thickness','SOLIDIFY');mod.thickness=.012
bpy.context.view_layer.update()
after=fc.inspect(S);(out/'floor-contracts.json').write_text(json.dumps(after,indent=2));assert after['passed'],after
unchanged=0
for name,(points,matrix) in baseline.items():
    o=bpy.data.objects[name];assert len(points)==len(o.data.vertices),name
    assert max((Vector(p)-v.co).length for p,v in zip(points,o.data.vertices))<1e-7,name
    assert max(abs(o.matrix_world[i][j]-matrix[i][j]) for i in range(4) for j in range(4))<1e-7,name
    unchanged+=1
for name in ['shape-spec.json','shape-map.json','preservation-checks.json','repair-manifest.json','side-reference.png','original-a-reference.png']:
    if (src/name).exists():shutil.copy2(src/name,out/name)
manifest={'source':str(source),'source_sha256':sha,'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==sha,'removed_objects':removed,'added_objects':[o.name for o in c.objects],'unaffected_meshes_unchanged':unchanged,'scope':'Floor only; seat, body, wheel, arch and earlier repair geometry unchanged.'}
(out/'floor-repair-manifest.json').write_text(json.dumps(manifest,indent=2))
for name in ['fit_character_floor.py','floor_contracts.py','assembly_contracts.py','check_assembly_contracts.py','verify_dressed_character.py']:shutil.copy2(ROOT/name,out/name)
def camera(name,loc,target,scale,res):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;o['resolution']=res;return o
views={'underside':camera('QA | floor straight underside',(0,.05,-6),(0,.05,.6),4.5,(850,1250)),
       'underside-quarter':camera('QA | floor oblique',(3.8,4,-2.4),(0,.2,.7),4.8,(1200,900)),
       'quarter':bpy.data.objects['Front quarter | volume review'],'side':bpy.data.objects['Side | fixed reference registration']}
sc.cycles.samples=24
sc['status']='Floor pan fitted to sills and rear tubs; see floor-contracts.json for scoped review.'
sc.camera=views['quarter'];bpy.ops.wm.save_as_mainfile(filepath=str(out/'Crafted_Utility_Detailed.blend'))
for key,view in views.items():
    sc.camera=view;sc.render.resolution_x,sc.render.resolution_y=view['resolution']
    ground=bpy.data.objects.get('Ground');was=ground.hide_render;ground.hide_render=key.startswith('underside')
    sc.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True);ground.hide_render=was
sc.camera=views['quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];bpy.ops.wm.save_as_mainfile(filepath=str(out/'Crafted_Utility_Detailed.blend'))
print('FLOOR_READY',json.dumps(manifest))
