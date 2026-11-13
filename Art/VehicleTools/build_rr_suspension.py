"""Editable coil-sprung RR kit studies. New output only; never edits the source car.

These are component assemblies, not a claim that the blockout's floor has suitable mounts.
"""
import bpy,bmesh,math,json,sys,hashlib,shutil
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
import wheel_fender_workshop as wf
OUT=Path(sys.argv[sys.argv.index('--')+1]).resolve();OUT.mkdir(parents=True,exist_ok=False)
SOURCE=Path('C:/GrandTour/Art/rangerover.blend');sourcehash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
REF=Path('C:/GrandTour/Art/References/Vehicles/RangeRoverCustomization_2026-10-25_v01/02-suspension-stance.png')
bpy.ops.wm.read_factory_settings(use_empty=True)
black=wf.material('Suspension | powder coat',(.009,.013,.016),.5,.25)
rubber=wf.material('Suspension | rubber bushes',(.012,.016,.019),.84,0)
silver=wf.material('Suspension | plated hardware',(.46,.49,.51),.27,.8)
chrome=wf.material('Suspension | piston chrome',(.65,.68,.70),.16,.95)
gold=wf.material('Suspension | touring damper',(.43,.27,.075),.37,.65)
grey=wf.material('Suspension | trail damper',(.29,.32,.34),.37,.75)
checks=[];parts=[];rows=[]
def lathe(name,profile,mat,c,root,position=(0,0,0),axis='Z',segments=64):
 o=wf.revolve(name,profile,mat,c,root,segments,True)
 if axis=='Z':o.data.transform(Matrix.Rotation(-math.pi/2,4,'Y'))
 o.location=position
 return o
def cylinder(name,z0,z1,r,mat,c,root,position=(0,0,0),axis='Z'):
 o=wf.cylinder(name,(z0+z1)/2,0,0,r,z1-z0,mat,c,root,64)
 if axis=='Z':o.data.transform(Matrix.Rotation(-math.pi/2,4,'Y'))
 o.location=position
 for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
 return o
def ring(name,z,r,t,mat,c,root,position=(0,0,0),axis='Z'):
 return lathe(name,[(z+t*math.cos(i*math.tau/12),r+t*math.sin(i*math.tau/12)) for i in range(12)],mat,c,root,position,axis)
def eye(name,z,mat,c,root,x=.19):
 # Actual open steel eye, elastomer annulus and sleeve share a single bore.
 for suffix,outer,inner,half,m in [('steel',.026,.018,.016,mat),('bush',.0185,.008,.018,rubber),('sleeve',.0085,.005,.021,silver)]:
  lathe(name+' '+suffix,[(-half,inner),(-half,outer),(half,outer),(half,inner)],m,c,root,(x,0,z),'X')
def coil(name,height,c,root):
 # Ground, closed ends; smoothly variable pitch over the first and last turn.
 n=336;k=12;turns=6;wire=.007;rad=.069
 centers=[]
 for i in range(n+1):
  t=i/n; a=t*turns*math.tau
  # Monotone pitch with closed ends, .014 m centre pitch at each end.
  end=.12
  def f(u):
   if u<end:return u*u/(2*end)
   if u>1-end:return 1-end-(1-u)*(1-u)/(2*end)
   return u-end/2
  z=wire+(height-2*wire)*(.24*t+.76*f(t)/(1-end))
  centers.append(Vector((rad*math.cos(a),rad*math.sin(a),z)))
 verts=[];faces=[]
 for i,p in enumerate(centers):
  tang=(centers[min(i+1,n)]-centers[max(0,i-1)]).normalized()
  radial=Vector((p.x,p.y,0)).normalized(); across=tang.cross(radial).normalized()
  for j in range(k):verts.append(p+wire*(radial*math.cos(j*math.tau/k)+across*math.sin(j*math.tau/k)))
 for i in range(n):
  for j in range(k):faces.append((i*k+j,i*k+(j+1)%k,(i+1)*k+(j+1)%k,(i+1)*k+j))
 faces += [tuple(range(k-1,-1,-1)),tuple(n*k+j for j in range(k))]
 o=wf.mesh(name,verts,faces,black,c,root)
 for p in o.data.polygons:p.use_smooth=True
 o['wire_diameter_m']=2*wire;o['turns']=turns;o['installed_length_m']=height
 return o
for index,(name,height,dampermat) in enumerate([('Standard',.28,black),('Touring',.31,gold),('Trail',.34,grey)]):
 c=bpy.data.collections.new('SUSPENSION | '+name);bpy.context.scene.collection.children.link(c)
 root=bpy.data.objects.new(name+' | lower spring seat origin',None);c.objects.link(root);root.empty_display_type='ARROWS';root.empty_display_size=.07
 c['kind']='suspension';c['units']='metres';c['axis']='Z compression; X across damper eyes';c['status']='Editable component assembly; vehicle mounting pending';c['kit_index']=index
 coil(name+' | continuous spring',height,c,root)
 for label,z in [('lower',0),('upper',height)]:
  lathe(name+' | '+label+' pressed seat',[(z-.006,.010),(z-.006,.085),(z+.004,.085),(z+.004,.078),(z+.001,.078),(z+.001,.010)],black,c,root)
  lathe(name+' | '+label+' rubber isolator',[(z-.001,.055),(z-.001,.077),(z+.005,.077),(z+.005,.055)],rubber,c,root)
  cylinder(name+' | '+label+' mounting stud',z-.021,z+.012,.010,silver,c,root)
  for dz in [-.008,.001]:
   lathe(name+' | '+label+' retaining washer',[(z+dz,.010),(z+dz,.020),(z+dz+.002,.020),(z+dz+.002,.010)],silver,c,root)
  lathe(name+' | '+label+' retaining nut',[(z+.003,.010),(z+.003,.017),(z+.010,.017),(z+.010,.010)],silver,c,root,segments=6)
 bottom=-.045;top=height+.055
 eye(name+' | lower damper eye',bottom,dampermat,c,root)
 eye(name+' | upper damper eye',top,dampermat,c,root)
 cylinder(name+' | damper tube',bottom+.02,.205,.027,dampermat,c,root,(.19,0,0))
 ring(name+' | tube base weld',bottom+.024,.026,.0025,dampermat,c,root,(.19,0,0))
 cylinder(name+' | polished piston',.16,top-.018,.010,chrome,c,root,(.19,0,0))
 lathe(name+' | rod seal',[(.199,.010),(.199,.028),(.213,.028),(.213,.010)],rubber,c,root,(.19,0,0))
 # Upper dust gaiter with genuine corrugation, clear of the plated shaft.
 profile=[(top-.025-j*.006,.016+(.004 if j%2 else 0)) for j in range(10)]
 profile += [(profile[-1][0],.013),(profile[0][0],.013)]
 lathe(name+' | dust boot',profile,rubber,c,root,(.19,0,0))
 for z in [bottom,top]:
  cylinder(name+' | eye through bolt',-.034,.034,.0048,silver,c,root,(.19,0,z),'X')
  lathe(name+' | eye hex head',[(-.035,.0049),(-.035,.009),(-.026,.009),(-.026,.0049)],silver,c,root,(.19,0,z),'X',6)
 c.asset_mark();c.asset_data.description=name+' separate coil, seats, two-piece telescopic damper and open eye bushes. Component prototype.'
 parts.append(c);rows.append(dict(name=name,spring_height_m=height,damper_eye_spacing_m=top-bottom,kit_index=index))
 for o in c.objects:
  if o.type!='MESH':continue
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
  bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data)
  bad=sum(not e.is_manifold for e in bm.edges);zero=sum(f.calc_area()<1e-12 for f in bm.faces);bm.free()
  checks.append(dict(name=o.name,closed=bad==0,nonzero_faces=zero==0))
  bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
 wf.seal(c)
for c in parts:bpy.context.scene.collection.children.unlink(c);c.use_fake_user=True
bpy.data.libraries.write(str(OUT/'GT_RangeRover_Suspension_Components.blend'),set(parts),fake_user=True)
sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.resolution_x=1600;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.threads_mode='FIXED';sc.render.threads=10;sc.view_settings.view_transform='AgX'
sc.world=bpy.data.worlds.new('Workshop paper studio');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.68,.68,.65,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.7
for name,loc,power,size in [('Key',(1,-2,3),500,2),('Fill',(-2,-1,2),280,2),('Edge',(0,2,2),500,2)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
paper=wf.material('Workshop | warm paper',(.64,.62,.57),.9)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.073));bpy.context.object.data.materials.append(paper)
for i,c in enumerate(parts):
 o=bpy.data.objects.new(c.name,None);sc.collection.objects.link(o);o.instance_type='COLLECTION';o.instance_collection=c;o.location=(i*.51-.60,0,0)
 cu=bpy.data.curves.new(rows[i]['name'],'FONT');cu.body=rows[i]['name'].upper();cu.size=.030;cu.align_x='CENTER';cu.materials.append(black)
 ob=bpy.data.objects.new(cu.body,cu);sc.collection.objects.link(ob);ob.location=(i*.51-.50,-.12,-.071)
cu=bpy.data.curves.new('Title','FONT');cu.body='RANGE ROVER / SUSPENSION';cu.size=.045;cu.align_x='CENTER';cu.materials.append(black)
ob=bpy.data.objects.new('Title',cu);sc.collection.objects.link(ob);ob.location=(0,.57,-.071)
camdata=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',camdata);sc.collection.objects.link(cam);sc.camera=cam;camdata.type='ORTHO'
def render(name,loc,target,scale):
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=scale;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('01-component-board',(1,-2.8,1.6),(0,0,.16),1.85)
render('02-touring-detail',(.43,-1.4,.7),(.01,0,.18),.68)
render('03-front',(0,-3,.18),(0,0,.18),1.75)
render('04-top',(0,0,3),(0,0,0),1.75)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RangeRover_Suspension_Review.blend'))
shutil.copy2(REF,OUT/'approved-reference.png');shutil.copy2(__file__,OUT/'build_source.py')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sourcehash
report=dict(ok=all(r['closed'] and r['nonzero_faces'] for r in checks),checks=checks,source_sha256=sourcehash,kits=rows,
 scope='Standalone component topology, UVs, nested eye/bush/sleeve construction. Not fitted vehicle hardware or exported engine assets.')
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
(OUT/'README.txt').write_text('Editable suspension component prototypes. Source car unchanged. Separate six-turn coils, seats, studs, isolators, damper bodies, piston rods, gaiters, steel eyes, rubber bushes and sleeves. UVs present.\nThe original blockout needs a deliberate underfloor/mounting pass before these meshes can be fitted. Gameplay kits are independently implemented in the workshop; these component studies are not installed in Unreal.\n')
assert report['ok'],report
print('SUSPENSION_COMPONENTS_OK',len(checks),flush=True)
