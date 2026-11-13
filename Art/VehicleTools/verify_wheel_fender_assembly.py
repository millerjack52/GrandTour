"""Reopen a workshop revision, check the four tyres against fixed bodywork, frame side render."""
import bpy,sys,json,argparse,shutil
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import wheel_fender_workshop as wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Wheel_Fender_Workshop.blend'))
parts=[c for c in bpy.data.collections if c.get('gt_owner')==wf.OWNER]
preserved={c.name:c.get('fingerprint')==wf.fingerprint(c) for c in parts}
assert all(preserved.values()),preserved
car=bpy.data.collections['Range Rover Classic — stylized study']
fixed=[o for o in car.objects if o.type=='MESH' and any(t in o.name for t in ['connected body','sill trim','dark wheelhouse','Underbody mass'])]
fixed += [o for c in parts if c['kind']=='fender' for o in c.objects if o.type=='MESH']
bpy.context.view_layer.update();trees={o:wf.tree(o) for o in fixed};contacts=[]
for c in parts:
    if c['kind']!='wheel':continue
    for o in c.objects:
        if o.type=='MESH' and any(t in o.name for t in ['carcass','tread blocks']):
            tr=wf.tree(o)
            for b,bt in trees.items():
                if tr.overlap(bt):contacts.append([o.name,b.name])
assert not contacts,contacts
report={'saved_part_fingerprints_match':preserved,'four_tyre_fixed_body_intersections':contacts,
        'scope':'Static evaluated carcass/tread against retained side body, sill trim, wheelhouses, underbody mass and new fenders. Axle/hub contact, articulation, containment and other assemblies excluded.'}
(out/'assembly-reopen-check.json').write_text(json.dumps(report,indent=2))
sc=bpy.context.scene;cam=sc.camera;cam.location=(5,-1.36,.60)
cam.rotation_euler=(Vector((.85,-1.36,.60))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.90
sc.render.filepath=str(out/'07-after-side.png');bpy.ops.render.render(write_still=True)
shutil.copy2(Path(__file__),out/Path(__file__).name)
shutil.copy2(Path(__file__).with_name('build_wheel_fender_workshop.py'),out/'build_wheel_fender_workshop.py')
print('ASSEMBLY_REOPEN_VERIFIED '+json.dumps(report),flush=True)
