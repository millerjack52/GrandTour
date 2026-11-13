"""Reopen fit checks and FBX roundtrips for the finished interior package."""
import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from graphic_adventure_coverage_v04 import tree
BASE=Path('C:/GrandTour/Art/Export/VehicleTools');OUT=BASE/'graphic-adventure-unreal-v02'
report={'ok':False,'roundtrips':[]}
bpy.ops.wm.open_mainfile(filepath=str(BASE/'graphic-adventure-interior-v01/GraphicAdventure_Interior.blend'))
mesh=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('RET |')]
new=[o for o in mesh if o.get('ga_interior')]
seats=[o for o in new if 'Seat |' in o.name or 'Bench |' in o.name]
fixed=[o for o in new if any(k in o.name for k in ['Console |','shaped door card','armrest','cloth insert','map pocket'])]
ft=tree(fixed);conflicts=[]
for o in seats:
 if tree([o]).overlap(ft):conflicts.append(o.name)
report['seat_console_door_intersections']=conflicts
tyres=[o for o in mesh if 'tyre' in o.name or 'tread' in o.name];tt=tree(tyres)
conflicts=[]
for o in new:
 if tree([o]).overlap(tt):conflicts.append(o.name)
report['interior_tyre_intersections']=conflicts
spec=json.loads((OUT/'export-report.json').read_text())
for item in spec['lods']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=item['file'])
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==1
 ob=meshes[0];count=sum(len(p.vertices)-2 for p in ob.data.polygons);assert count==item['triangles'],(item['level'],count,item['triangles'])
 assert len(ob.data.materials)==2
 assert ob.data.uv_layers and all(math.isfinite(x) for v in ob.data.uv_layers.active.data for x in v.uv)
 assert all(v.groups and abs(sum(g.weight for g in v.groups)-1)<.002 for v in ob.data.vertices)
 arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(arms)==1
 for bone in spec['bones']:assert bone in arms[0].data.bones
 report['roundtrips'].append({'lod':item['level'],'triangles':count,'materials':len(ob.data.materials),'bones':len(arms[0].data.bones),'weighted_vertices':len(ob.data.vertices),'uv_loops':len(ob.data.uv_layers.active.data)})
report['ok']=not report['seat_console_door_intersections'] and not report['interior_tyre_intersections']
(OUT/'fit-and-roundtrip.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
assert report['ok']
