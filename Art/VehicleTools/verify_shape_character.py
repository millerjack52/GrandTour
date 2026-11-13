"""Reopen the delivered study and exercise the actual coordinated controls."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

out=Path(sys.argv[sys.argv.index('--')+1]);bpy.ops.wm.open_mainfile(filepath=str(out/'Crafted_Utility_Character_Study.blend'))
sc=bpy.context.scene;control=bpy.data.objects['FORM CONTROLS | 1 proposed - 0 flattened']
def update():
    control.update_tag();sc.frame_set(sc.frame_current);bpy.context.view_layer.update()
def snapshot():
    dg=bpy.context.evaluated_depsgraph_get();result={}
    for ob in sc.objects:
        if ob.type!='MESH' or not ob.get('study_part'):continue
        eo=ob.evaluated_get(dg);me=eo.to_mesh();result[ob.name]=[v.co.copy() for v in me.vertices];eo.to_mesh_clear()
    return result
update();base=snapshot();checks={}
for prop in ['rear_tuck','side_tuck','bumper_return','bonnet_shoulders','roof_crown','cabin_taper']:
    control[prop]=0.;update();new=snapshot();affected={}
    for name,pts in base.items():
        delta=max((a-b).length for a,b in zip(pts,new[name]))
        if delta>.00001:affected[name]=delta
    assert affected,prop+' driver does not move geometry'
    control[prop]=1.;update();restored=snapshot()
    error=max((a-b).length for name,pts in base.items() for a,b in zip(pts,restored[name]))
    assert error<.00001,(prop,error)
    checks[prop]={'affected_objects':affected,'restoration_error_m':error}
S=json.loads((out/'shape-spec.json').read_text());R=S['registration'];cam=bpy.data.objects['Side | fixed reference registration'];sc.camera=cam
sc.render.resolution_x=1260;sc.render.resolution_y=600;bpy.context.view_layer.update()
errors=[]
for y,expected in [(R['axle_front_world'],R['front_hub_px']),(R['axle_rear_world'],R['rear_hub_px'])]:
    p=world_to_camera_view(sc,cam,Vector((S['wheel_half_track'],y,R['axle_z'])));actual=(p.x*840,(1-p.y)*400);errors.append(math.dist(actual,expected))
assert max(errors)<.01
checks['side_hub_registration_max_error_px']=max(errors)
checks['packed_references']=[im.name for im in bpy.data.images if im.packed_file]
assert len(checks['packed_references'])>=4
checks['limitations']='Tests establish saved control behaviour and unchanged side registration, not artistic approval. Global probes can expose dependent joints; widths and original-A camera fit remain provisional.'
(out/'saved-control-checks.json').write_text(json.dumps(checks,indent=2))
print('SAVED_CONTROL_CHECKS_PASSED',flush=True)
