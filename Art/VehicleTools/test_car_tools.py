"""Behavioural regression tests, run in background Blender with --python-exit-code 1."""
import bpy,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import car_tools as ct
checks=[]
def check(label,condition):
 if not condition:raise AssertionError(label)
 checks.append(label)
def hashes(part=None):return {o['gt_role']:ct.fingerprint(o) for o in ct.owned() if not part or o['gt_part']==part}
def refuses(fn):
 try:fn()
 except (ValueError,RuntimeError):return True
 return False
bpy.ops.wm.read_factory_settings(use_empty=True)
s=json.loads((Path(__file__).parent/'specs/estate_front_v1.json').read_text())
ct.rebuild(s);ct.setup_references(s,Path(__file__).resolve().parents[2])
check('Baseline panel topology and static tyre clearance',ct.fit_report()['ok'])
body=bpy.data.objects['FixedBody']
for sign in [-1,1]:
 point=ct.P(s['scuttle_u'],sign*(s['width']/2-.065),s['scuttle_z'])
 check('Window/body shared corner '+str(sign),min((v.co-point).length for v in body.data.vertices)<1e-6)
sentinel=bpy.data.objects.new('ArtistNotes',None);bpy.context.scene.collection.objects.link(sentinel);sentinel['keep']='yes'
baseline=hashes();cabin=hashes('cabin');fittings=hashes('fittings')
t=dict(s,wheel_radius=s['wheel_radius']+.02)
check('Radius change rebuilds body and wheels only',ct.rebuild(t)==['body','wheels'])
check('Radius change preserves cabin and fittings',hashes('cabin')==cabin and hashes('fittings')==fittings)
check('Radius change raises arch with tyre',abs(bpy.data.objects['FixedBody']['gt_arch_peak_m']-(2*t['wheel_radius']+t['arch_clearance']))<1e-7)
check('Radius change refreshes guides',abs(bpy.data.objects['Guide_FrontAxle_L'].location.z-t['wheel_radius'])<1e-6)
check('Larger wheel remains clear',ct.fit_report()['ok'])
wheel=hashes('wheels');t=dict(t,width=t['width']+.06)
check('Width change rebuilds body cabin fittings',ct.rebuild(t)==['body','cabin','fittings'])
check('Width change preserves wheel geometry',hashes('wheels')==wheel)
check('Unrelated artist object preserved',bpy.data.objects['ArtistNotes']['keep']=='yes')
ob=bpy.data.objects['Wheel_L'];ob.data.vertices[0].co.z+=.008;ob.data.update();bpy.context.view_layer.update();edited=hashes('wheels')
ct.rebuild(t,['body'])
check('Unrelated component rebuild preserves manual wheel edit',hashes('wheels')==edited)
before=hashes()
check('Destructive rebuild refuses manual edit',refuses(lambda:ct.rebuild(t,['wheels'])))
check('Refused rebuild leaves scene unchanged',hashes()==before)
check('Invalid specification rejected',refuses(lambda:ct.rebuild(dict(t,gap=-1))))
check('Invalid specification leaves scene unchanged',hashes()==before)
real=ct.build_body
def broken(s,c,m):
 ct.box('PartialBuild',(0,0,0),(1,1,1),c,m[0],'body')
 raise RuntimeError('Injected builder failure')
ct.build_body=broken
check('Failed staged build reports error',refuses(lambda:ct.rebuild(t,['body'])))
ct.build_body=real
check('Failed staged build preserves original geometry',hashes()==before)
check('Failed staging object removed',not bpy.data.objects.get('PartialBuild'))
temp=Path(tempfile.gettempdir())/'GTCT-regression-roundtrip.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(temp));bpy.ops.wm.open_mainfile(filepath=str(temp))
check('Save/reopen preserves fingerprints',hashes()==before)
bpy.data.objects['Wheel_R'].location.z=.25;bpy.context.view_layer.update()
check('Deliberate wheel/body collision detected',not ct.fit_report()['ok'])
bpy.ops.wm.read_factory_settings(use_empty=True)
shape=json.loads((Path(__file__).parent/'specs/estate_shape_v1.json').read_text())
ct.rebuild(shape)
check('Whole estate body and four-wheel static fit',ct.fit_report()['ok'])
check('Whole estate has four wheels',len([o for o in ct.owned() if o['gt_part']=='wheels'])==4)
panels=[o for o in ct.owned() if 'DoorSkin' in o['gt_role']]
check('Four separately extracted door skins',len(panels)==4)
eo=bpy.data.objects['FixedBody'].evaluated_get(bpy.context.evaluated_depsgraph_get())
for sign in [-1,1]:
 origin=ct.P(shape['front_u']+.2,sign*shape['width']*.325,shape['nose_z']-.134)
 check('Lamp opening is unobstructed '+str(sign),not eo.ray_cast(origin,ct.Vector((0,1,0)),distance=.21)[0])
shape2=dict(shape,rear_axle_u=shape['rear_axle_u']-.03)
ct.rebuild(shape2)
check('Rear axle edit retains static clearance',ct.fit_report()['ok'])
bpy.ops.wm.read_factory_settings(use_empty=True)
taper=json.loads((Path(__file__).parent/'specs/estate_shape_v2.json').read_text());ct.rebuild(taper)
check('Tapered body and all reported fit details pass',ct.fit_report()['ok'])
body=bpy.data.objects['FixedBody']
front_points=[v.co for v in body.data.vertices if abs(v.co.y+taper['front_u'])<1e-5]
check('Nose is measurably narrower than cabin',max(abs(v.x) for v in front_points)<taper['width']/2*.90)
check('Bumper is one connected part',not any(o['gt_role'].startswith('BumperReturn') for o in ct.owned()))
wheel_before=hashes('wheels')
check('Taper edit rebuilds surfaces and fittings only',ct.rebuild(dict(taper,nose_width_ratio=.90))==['body','cabin','fittings'])
check('Taper edit preserves wheel dimensions and positions',hashes('wheels')==wheel_before)
bpy.data.objects['Indicator_L'].location.x+=.15;bpy.context.view_layer.update()
check('Deliberate indicator overhang is detected',not ct.detail_checks(dict(taper,nose_width_ratio=.90))['indicator_inside_recess_L'])
bpy.data.objects['SillTrim_R'].location.y+=.12;bpy.context.view_layer.update()
check('Deliberate trim intrusion into arch is detected',not ct.detail_checks(dict(taper,nose_width_ratio=.90))['trim_clear_of_arch_feet_R'])
bpy.ops.wm.read_factory_settings(use_empty=True)
coach=json.loads((Path(__file__).parent/'specs/estate_coachwork_v1.json').read_text());ct.rebuild(coach)
check('Coachwork retains static assembly and fitting clearance',ct.fit_report()['ok'])
roof=bpy.data.objects['RoofSection'].data
near_front=[abs(v.co.x) for v in roof.vertices if abs(-v.co.y-coach['roof_front_u'])<.07]
near_middle=[abs(v.co.x) for v in roof.vertices if abs(-v.co.y-coach['b_pillar_u'])<.07]
check('Roof outline has different front and middle widths',max(near_middle)-max(near_front)>.025)
check('Roof has an actual crown',max(v.co.z for v in roof.vertices)-min(v.co.z for v in roof.vertices)>.035)
verts=[v.co for o in ct.owned() if o['gt_part']=='body' for v in o.data.vertices if abs(-v.co.y-coach['b_pillar_u'])<.05]
low=max(abs(v.x) for v in verts if v.z<.45)
high=max(abs(v.x) for v in verts if .8<v.z<.94)
check('Door section tucks inward at the rocker',high-low>.06)
output=Path(__file__).resolve().parent/'test-results.json'
output.write_text(json.dumps({'passed':len(checks),'checks':checks},indent=2))
print('GTCT_TESTS '+str(len(checks))+' passed')
