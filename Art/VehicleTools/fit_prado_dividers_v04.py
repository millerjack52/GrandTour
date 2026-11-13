import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/prado-prepared-v03')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/prado-exterior-v04');OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'Prado_Exterior.blend').exists(),'Preserve saved output'
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Prado_Exterior.blend'))
A=json.loads(Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01/islands.json').read_text())
reports=[]
for idx in [224,233,234,236,237,240]:
 old=next(o for o in bpy.context.scene.objects if o.get('source_component')==idx)
 a=A[idx];lo,hi=Vector(a['min']),Vector(a['max']);sgn=1 if lo.x>0 else -1
 pane=bpy.data.objects['Glass | '+('RearDoor' if idx in [224,240] else 'FrontDoor')+('_L' if sgn>0 else '_R')]
 tree=BVHTree.FromPolygons([v.co for v in pane.data.vertices],[list(p.vertices) for p in pane.data.polygons],all_triangles=False)
 # Keep source division position and endpoints; derive axial position from
 # the actual pane so that it does not emerge only at the top and bottom.
 yb=sum(v[1] for v in a['verts'] if abs(v[2]-lo.z)<.002)/sum(abs(v[2]-lo.z)<.002 for v in a['verts'])
 yt=sum(v[1] for v in a['verts'] if abs(v[2]-hi.z)<.002)/sum(abs(v[2]-hi.z)<.002 for v in a['verts'])
 width=.0033*5;verts=[]
 for k in range(13):
  t=k/12;z=(lo.z*(1-t)+hi.z*t)*5;y=(yb*(1-t)+yt*t)*5
  for yy in [y-width/2,y+width/2]:
   hit,n,face,dist=tree.ray_cast(Vector((sgn*3,yy,z)),Vector((-sgn,0,0)),6)
   if hit is None:hit,n,face,dist=tree.find_nearest(Vector((sgn*.16*5,yy,z)))
   x=hit.x
   verts.extend([(x+sgn*.003,yy,z),(x-sgn*.002,yy,z)])
 faces=[]
 for k in range(12):
  b=k*4;c=b+4;faces += [(b,c,c+2,b+2),(b+1,b+3,c+3,c+1),(b,b+1,c+1,c),(b+2,c+2,c+3,b+3)]
 faces += [(0,2,3,1),(48,49,51,50)]
 me=bpy.data.meshes.new('Fitted window division');me.from_pydata(verts,[],faces);bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for f in bm.faces:f.smooth=False
 bm.to_mesh(me);bm.free();me.materials.append(bpy.data.materials['Prado | Rubber']);old.data=me;old.name=f'Window divider | {idx} | fitted to pane';old.color=bpy.data.materials['Prado | Rubber'].diffuse_color
 for m in list(old.modifiers):old.modifiers.remove(m)
 reports.append({'source_component':idx,'pane':pane.name,'source_yz_position_preserved':True,'pane_overlap_m':.002,'outer_trim_depth_m':.003})

sc=bpy.context.scene;cam=sc.camera
def render(n,c,d,scale=1.2):
 center=Vector(c)*5;cam.location=center+Vector(d)*5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*5;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
for name,d in [('side',(3,0,0)),('opposite-side',(-3,0,0)),('front',(0,-3,0)),('rear',(0,3,0)),('top',(0,0,3)),('rear-quarter',(-2,3,1)),('underside',(1,-1,-2))]:render(name,(0,0,.27),d)
render('window-close',(0,-.1,.355),(2,-3,.7),.53)
render('wheel-close',(.16,-.28,.13),(3,-1,.2),.32)
render('quarter',(0,0,.27),(2,-3,1.1))
bpy.ops.object.select_all(action='DESELECT');body=bpy.data.objects['Prado | source-fitted body'];body.select_set(True);bpy.context.view_layer.objects.active=body
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   rv=area.spaces.active.region_3d;rv.view_distance=7;rv.view_location=Vector((0,0,1.35));rv.view_rotation=cam.rotation_euler.to_quaternion()
(OUT/'divider-fit.json').write_text(json.dumps(reports,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Exterior.blend'))
