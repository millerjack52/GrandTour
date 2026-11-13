"""Repair the rejected v11 pane extent without rebuilding the car."""
import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from prado_glazing_repair import ring_strip,glass_grid,fit_surface,edge_y
from shapely.geometry import Polygon,LineString

BASE=Path('C:/GrandTour/Art/Export/VehicleTools')
SRC=BASE/'prado-glazing-v11/Prado_Corrected.blend'
OUT=BASE/'prado-glazing-v12';OUT.mkdir(exist_ok=True)
assert not (OUT/'Prado_Corrected.blend').exists(),'Protect existing saved revision'
bpy.ops.wm.open_mainfile(filepath=str(SRC));sc=bpy.context.scene
report=json.loads((BASE/'prado-glazing-v11/repair-report.json').read_text())
contract=json.loads((BASE/'prado-glazing-audit/windscreen-corner-repair-contract.json').read_text())
ring=[p['co'] for p in contract['outer_ring']]
outer=Polygon([(p[0],p[2]) for p in ring])
changed={'Glass | Windscreen','Windscreen | fitted painted surround','Windscreen | continuous rubber seal'}
def fingerprint(o):
 return hashlib.sha256(repr(([(tuple(v.co)) for v in o.data.vertices],[(tuple(p.vertices),p.material_index,p.use_smooth) for p in o.data.polygons],list(map(tuple,o.matrix_world)))).encode()).hexdigest()
before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH' and o.name not in changed}
for n in changed:bpy.data.objects.remove(bpy.data.objects[n],do_unlink=True)

# Keep the even cowl/bottom edge from the previous repair. Side and top extent
# now come from the actual pillar/header opening, not an arbitrary trapezoid.
bottom=[(-.3,.313)]
for i in range(81):
 x=-.148+.296*i/80;t=(x+.148)/.296
 bottom.append((x,.313+2*t*(1-t)*.001))
bottom.extend([(.3,.313),(.3,.6),(-.3,.6)])
desired=outer.intersection(Polygon(bottom)).buffer(-.0004,join_style=2)
radius=.0025
seal_outer=desired.buffer(-radius,quad_segs=12).buffer(radius,quad_segs=12)
assert seal_outer.geom_type=='Polygon' and outer.covers(seal_outer)
pane=seal_outer.buffer(-.0009,quad_segs=12)
shape=fit_surface(ring,bow=.0007,outsign=-1,offset=-.00065)
seal_y=lambda x,z:shape(x,z)-.00035
ring_strip('Windscreen | fitted painted surround',outer,seal_outer,lambda x,z:edge_y(ring,x,z),seal_y,'Paint',-1,.0008)
ring_strip('Windscreen | continuous rubber seal',seal_outer,pane,seal_y,shape,'Rubber',-1,.0006)
glass_grid('Glass | Windscreen',pane,shape,-1)
report['windscreen']['smooth_seal_outline_raw']=list(seal_outer.exterior.coords)[:-1]
report['windscreen']['pane_outline_raw']=list(pane.exterior.coords)[:-1]
report['windscreen']['extent_repair']='Pane follows retained inner pillar/header lip; 2 mm nominal paint lip + 4.5 mm rubber at scale 5. Smooth lower edge retained.'
report['input_file']=str(SRC);report['input_sha256']=hashlib.sha256(SRC.read_bytes()).hexdigest()
report['preservation']={'changed_objects':sorted(changed),'unchanged_meshes':len(before),'verified':all(fingerprint(bpy.data.objects[n])==v for n,v in before.items())}
assert report['preservation']['verified']
oldpoly=Polygon(json.loads((BASE/'prado-glazing-v11/repair-report.json').read_text())['windscreen']['smooth_seal_outline_raw']).buffer(-.001)
widths=[]
for z in [.325,.335,.345,.355,.365,.375,.385,.395,.400]:
 def cross(poly):
  line=poly.intersection(LineString([(-.25,z),(.25,z)]));return min(p[0] for p in line.coords),max(p[0] for p in line.coords)
 lo,hi=cross(outer);oa,ob=cross(oldpoly);na,nb=cross(pane)
 widths.append({'height_m':z*5,'old_left_setback_mm':(oa-lo)*5000,'old_right_setback_mm':(hi-ob)*5000,'new_left_setback_mm':(na-lo)*5000,'new_right_setback_mm':(hi-nb)*5000})
report['windscreen']['side_setback_comparison']=widths
(OUT/'repair-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'preservation':report['preservation'],'side_setback_comparison':widths},indent=2))
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL'
sc.render.resolution_x=1500;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
cam=sc.camera
def render(n,c,d,size):
 target=Vector(c)*5;cam.data.type='ORTHO';cam.location=target+Vector(d)*5;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=size*5;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
for args in [('front-close',(0,-.13,.36),(0,-3,.1),.44),('front-left',(0,-.13,.36),(-2,-3,.5),.48),('front-right',(0,-.13,.36),(2,-3,.5),.48),('pillar-right',(.142,-.13,.357),(2,-3,.6),.20),('pillar-left',(-.142,-.13,.357),(-2,-3,.6),.20)]:render(*args)
render('quarter',(0,0,.27),(2,-3,1.1),1.2)
sc['asset_status']='V12 windscreen extent corrected to pillar lip. V11 glass extent rejected by user. Other cleanup/engine preparation outstanding.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Corrected.blend'))
