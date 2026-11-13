"""Seat widened glass to the complete 3D pillar/header boundary."""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from prado_glazing_repair import make,ring_strip,glass_grid,edge_y
from shapely.geometry import Polygon,LineString
import prado_wiper_repair as wr
from prado_boundary_surface import build_surface

BASE=Path('C:/GrandTour/Art/Export/VehicleTools');SRC=BASE/'prado-glazing-v12/Prado_Corrected.blend';OUT=BASE/'prado-glazing-v13';OUT.mkdir(exist_ok=True)
assert not (OUT/'Prado_Corrected.blend').exists(),'Protect existing saved revision'
bpy.ops.wm.open_mainfile(filepath=str(SRC));sc=bpy.context.scene
report=json.loads((SRC.parent/'repair-report.json').read_text())
contract=json.loads((BASE/'prado-glazing-audit/windscreen-corner-repair-contract.json').read_text())
ring=[p['co'] for p in contract['outer_ring']]
outer=Polygon([(p[0],p[2]) for p in ring]);seal_outer=Polygon(report['windscreen']['smooth_seal_outline_raw']);pane=Polygon(report['windscreen']['pane_outline_raw'])
shape,diagnostics=build_surface(ring,pane)
changed={'Glass | Windscreen','Windscreen | fitted painted surround','Windscreen | continuous rubber seal','CAB | aperture-fitted dashboard cowl'}
changed.update(o.name for o in bpy.data.collections['18 Windscreen wipers'].objects)
def fingerprint(o):
 return hashlib.sha256(repr(([(tuple(v.co)) for v in o.data.vertices],[(tuple(p.vertices),p.material_index,p.use_smooth) for p in o.data.polygons],list(map(tuple,o.matrix_world)))).encode()).hexdigest()
before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH' and o.name not in changed}
for n in changed:bpy.data.objects.remove(bpy.data.objects[n],do_unlink=True)
seal_y=lambda x,z:edge_y(ring,x,z)+.00025
ring_strip('Windscreen | fitted painted surround',outer,seal_outer,lambda x,z:edge_y(ring,x,z),seal_y,'Paint',-1,.0008)
ring_strip('Windscreen | continuous rubber seal',seal_outer,pane,seal_y,shape,'Rubber',-1,.0006)
glass_grid('Glass | Windscreen',pane,shape,-1)
vs=[];fs=[]
for i in range(49):
 x=-.153+.306*i/48;cross=pane.intersection(LineString([(x,.29),(x,.34)]));assert cross.geom_type=='LineString' and not cross.is_empty
 z=min(p[1] for p in cross.coords);vs.extend([(x,shape(x,z)+.0015,z-.0010),(x,-.153,.3058)])
for i in range(48):a=2*i;fs.append((a,a+2,a+3,a+1))
make('CAB | aperture-fitted dashboard cowl',vs,fs,'Cabin',col='14 Dashboard',thick=.0006,outnormal=(0,0,1))
wr.fit_surface=lambda *a,**kw:shape
report['wipers']=wr.repair_wipers(contract)
report['windscreen']['depth_fit']=diagnostics
report['input_file']=str(SRC);report['input_sha256']=hashlib.sha256(SRC.read_bytes()).hexdigest()
report['preservation']={'changed_objects':sorted(changed),'unchanged_meshes':len(before),'verified':all(fingerprint(bpy.data.objects[n])==v for n,v in before.items())}
assert report['preservation']['verified']
(OUT/'repair-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'preservation':report['preservation'],'depth_fit':diagnostics},indent=2))
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.render.resolution_x=1500;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
cam=sc.camera
def render(n,c,d,size):
 target=Vector(c)*5;cam.data.type='ORTHO';cam.location=target+Vector(d)*5;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=size*5;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
for args in [('front-close',(0,-.13,.36),(0,-3,.1),.44),('front-left',(0,-.13,.36),(-2,-3,.5),.48),('front-right',(0,-.13,.36),(2,-3,.5),.48),('pillar-right',(.142,-.13,.357),(2,-3,.6),.20),('pillar-left',(-.142,-.13,.357),(-2,-3,.6),.20)]:render(*args)
render('quarter',(0,0,.27),(2,-3,1.1),1.2)
sc['asset_status']='V13 pane fills actual pillar opening and follows 3D rim with shallow seal. V11 width rejected; v12 depth needed correction. Other cleanup/engine preparation outstanding.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Corrected.blend'))
