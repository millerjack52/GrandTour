import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
R=Path('C:/GrandTour/Art/Export/VehicleTools');P=R/'graphic-adventure-assembly-v02'
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));dg=bpy.context.evaluated_depsgraph_get();out={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or not o.name.startswith('RET |'):continue
  ev=o.evaluated_get(dg);m=ev.to_mesh();out[o.name]={'vertices':[list(o.matrix_world@v.co) for v in m.vertices],'faces':[list(p.vertices) for p in m.polygons],'groups':[c.name for c in o.users_collection]};ev.to_mesh_clear()
 return out
old=snapshot(R/'graphic-adventure-assembly-v01/GraphicAdventure_Assembly.blend');new=snapshot(P/'GraphicAdventure_Assembly.blend')
unchanged=[];changed=[];protected=[]
for name,a in old.items():
 if name not in new:continue
 b=new[name];same=a['faces']==b['faces'] and len(a['vertices'])==len(b['vertices'])
 error=max((Vector(x)-Vector(y)).length for x,y in zip(a['vertices'],b['vertices'])) if same else None
 if same and error<.00001:unchanged.append(name)
 else:changed.append(name)
 if any(c in ['Wheels','Roof equipment'] for c in a['groups']):
  assert same and error<.00001,(name,error)
  protected.append(name)
# The hidden firewall must stay inside the body, including between shared stations.
spec=json.loads((P/'vehicle-spec.json').read_text());stations=spec['side_stations']
def sx(z):
 for (za,xa),(zb,xb) in zip(stations,stations[1:]):
  if za<=z<=zb:return xa+(xb-xa)*(z-za)/(zb-za)
 return stations[0][1] if z<stations[0][0] else stations[-1][1]
excess=max(abs(p[0]/4.6)-sx(p[2]/4.6) for p in new['RET | Firewall']['vertices']);assert excess<0,excess
report={'protected_wheel_and_roof_equipment_meshes':len(protected),'unchanged_meshes':len(unchanged),'unchanged':unchanged,'changed':changed,'added':sorted(set(new)-set(old)),'replaced_or_removed':sorted(set(old)-set(new)),'firewall_max_relative_to_outer_body_mm':excess*4600,'status':'Protected wheels/equipment preserved within 0.01 mm; firewall contained'}
(P/'preservation.json').write_text(json.dumps(report,indent=2));print('PRESERVATION',len(unchanged),'protected',len(protected),'firewall',excess*4600)
