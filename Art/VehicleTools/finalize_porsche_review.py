"""Record the reviewed Blender handoff; deliberately performs no export."""
import json,hashlib
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04')
v=json.loads((O/'verification.json').read_text());p=O/'Porsche_Safari_Review.blend';sha=hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((O/'build-report.json').read_text())
assert sha==m['blend_sha256']
assert not any(v['static_failures'].values())
assert not v['interior_body_contacts'] and not v['seat_glass_contacts']
assert not v['dashboard_source_intrusions']['exposed']
assert not any(w['body_intersections'] for w in v['wheel_motion'])
assert not any(f['misses'] for f in v['floor_coverage'].values())
assert hashlib.sha256(Path(m['source']).read_bytes()).hexdigest()==m['source_sha256']
status={'status':'Blender review build prepared; user visual judgement pending','blend':str(p),'sha256':sha,'export_performed':False,'engine_validated':False,'scope_completed':['Local source-body cleanup and backed interfaces','Fitted transparent glazing with corrected rear pane notch','Front protection bar, lamp details, plate and underbody shields','Closed wheelwell liners with sampled clearance','Complete 2+2 cabin, dashboard, gauges, steering wheel, pedals, shifter, belts, door cards, floor and headliner','Named collections, inspection controls, UV layers, two preview LODs and convex collision proxies'],'verification':{'motion_poses':len(v['wheel_motion']),'motion_intersections':0,'seat_body_or_glass_intersections':0,'seat_floor_coverage_rays':sum(x['samples'] for x in v['floor_coverage'].values()),'seat_floor_misses':0,'body_support_change_max_m':v['body_support_change_max_m'],'static_mesh_failures':v['static_failures'],'triangles':v['total_lod0_triangles'],'lod_triangles':v['lod_triangles']},'export_stage_remaining':['Choose final runtime mesh budget and combine static render parts','Convert Blender inspection controls to engine bone rig and physics setup','Bake/translate procedural materials and confirm UV packing as needed','Set final LOD thresholds and collision fit in Unreal','Export, roundtrip shading/axis/scale checks and drive-test in engine'],'limitations':['Body retains mixed triangulated source topology and some surface irregularity','Wheel clearance is sampled at steering +/-22 degrees, suspension -25 mm to +15 mm; it is not a full dynamic simulation','Hidden LOD collections and collision proxies are preparation assets; they have not been engine-tested','Source files and previous accepted revision remain untouched']}
(O/'delivery-status.json').write_text(json.dumps(status,indent=2))
m['status']=status['status'];m['verification_file']='verification.json';m['delivery_status_file']='delivery-status.json';(O/'build-report.json').write_text(json.dumps(m,indent=2))
notes=f'''PORSCHE SAFARI - BLENDER REVIEW BUILD

Open Porsche_Safari_Review.blend. The original shape-preserving v03 source is untouched.
This handoff is for visual judgement before export. No FBX/GLB export or Unreal import was performed.

Included
Fitted 2+2 cockpit: front bucket seats, rear seats, belts, five gauges, steering wheel and stalks,
radio, vents, glovebox, pedals, shifter, handbrake, door cards, floor mats, continuous floor,
headliner, visors and mirror. Transparent panes and fitted window returns.
Rebuilt protection bar, mounted bumper insert, lamp details, rear plate, skid and floor shields,
and front/rear wheelwell barrels and inner closures.

Review controls
Select "Porsche | ROOT" in collection "06 Controls" and edit its Custom Properties.
steering_degrees: -22 to +22; wheel_roll_degrees: -360 to +360;
suspension_m: -0.025 to +0.015; headlamps: 0 to 1.
These are Blender inspection controls. Engine skeletal rig and vehicle physics are the export-stage task.
The main body and doors are a fixed shell in this revision; door-opening animation is not provided.

Review images
beauty.png / rear-beauty.png: actual saved-model Cycles renders.
driver-view.png: actual cockpit render through the clear windshield.
interior-cutaway.png / seats.png / dashboard.png: interior assembly inspection.
side.png / front.png / top.png: orthographic proportions.
front-detail.png / rear-detail.png / wheelhouses.png / underside.png: interfaces and enclosure.
Wheelhouse and underside diagnostics deliberately hide the wheels; the saved model restores them.

Recorded checks
{len(v['wheel_motion'])} steering/suspension poses: zero sampled tyre intersections with body or wheelwell liners.
All four seats: zero tested body/glass intersections and 900 floor-coverage rays with zero misses.
No overconnected edges, degenerate faces or missing UV layers in the checked visible meshes.
Maximum change in 216 directional body support measurements: {v['body_support_change_max_m']*1000:.2f} mm.
This measures the outer envelope; it does not certify every local surface or seam.
Detailed results are in verification.json.

Asset preparation
LOD0: {v['total_lod0_triangles']:,} triangles across {v['mesh_count']} editable mesh objects.
Two hidden preview LOD collections and four convex collision proxies are included.
They need runtime budget/material batching, final LOD tuning and Unreal validation after visual review.
UV layers are present; procedural Blender materials have not been baked into engine texture sets.
Retained body topology is mixed triangulated geometry, with some original surface irregularity.

Files
Porsche_Safari_Review.blend is the current review asset. The .blend1 is an automatic prior-save backup.
build-report.json records the source and protected SHA fingerprint. The builder refuses to overwrite
the review blend if its fingerprint changes, preserving later manual edits.
delivery-status.json records delivered scope and the remaining export-stage work.
'''
(O/'Review-Notes.txt').write_text(notes)
print(json.dumps({'blend':str(p),'sha256':sha,'triangles':v['total_lod0_triangles'],'status':status['status']},indent=2))
