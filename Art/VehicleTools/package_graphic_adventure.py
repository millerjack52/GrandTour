"""Record the delivered mesh scope and freeze the authoring/verification sources."""
import json,hashlib,shutil,ast
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-assembly-v01')
T=Path('C:/GrandTour/Art/VehicleTools')
r=json.loads((P/'verification.json').read_text());spec=json.loads((P/'vehicle-spec.json').read_text())
assert r['coverage']['uncovered']==0 and r['export_coverage']['uncovered']==0
scripts=['build_graphic_adventure.py','graphic_adventure_coverage.py','verify_graphic_adventure.py','review_graphic_adventure.py','inspect_graphic_adventure.py','analyse_graphic_adventure.py','measure_graphic_adventure.py']
dest=P/'authoring-snapshot';dest.mkdir(exist_ok=True)
for n in scripts:shutil.copy2(T/n,dest/n)
helper=Path('C:/GrandTour/Art/Export/VehicleTools/defender-retopology-v01/retopologize_defender.py').read_text()
tree=ast.parse(helper)
(dest/'shared_geometry_helpers.py').write_text('\n\n'.join(ast.get_source_segment(helper,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['interp','make','grid','box','tube','chamfer','ring_lamp']))
manifest={'asset':'Graphic Adventure Range Rover','revision':'assembly-v01','source':spec['source'],'source_sha256':spec['source_sha256'],'source_preservation':'Original download untouched; normalized source also retained in hidden Blender collection. GLB export excludes reference geometry.','method':'Measured reconstruction of exterior and fitted assembly; this is not a preservation of every Tripo vertex.','shape_authority':spec['shape_authority'],'reconstructed':['Body skins and window frames','Single windscreen and other glazing','Broad bonnet, crowned roof, split tailgate','Flares, connected inner wheelhouses, cabin floor and body returns','Four circular wheels and fitted rims','Roof basket, three cases, straps, handles and mounts','Grille, lamps, bumpers, winch, shackles and wipers'],'separation':'344 editable meshes organised in nine component collections; named pivot parents for four wheels, four doors, bonnet, upper/lower tailgate, roof/rack and cargo. No animation rig.','blender_version':'5.1.2','units':'metres; source uniformly scaled by 4.6; X width, -Y forward, Z up','status':'Cleaned exterior assembly for visual review; scoped static QA passed','qa':{'meshes':r['meshes'],'triangles':r['evaluated_triangles'],'coverage_samples':r['coverage']['samples'],'uncovered':0,'negative_control_uncovered':r['negative_control']['uncovered'],'tyre_intersections':r['static_tyre_intersections'],'mesh_errors':r['mesh_errors'],'export_bounds_max_error_m':r['export_bounds_max_error_m']},'not_delivered':['Texture, UV and livery work (deferred)','Detailed cockpit','Steering/suspension or door-opening rig and clearance validation','LODs, collision meshes, draw-call consolidation and Unreal integration'],'files':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['GraphicAdventure_Assembly.blend','GraphicAdventure_Assembly.glb']}}
(P/'repair-manifest.json').write_text(json.dumps(manifest,indent=2))
(P/'READ_ME.txt').write_text('''GRAPHIC ADVENTURE RANGE ROVER — CLEANED EXTERIOR ASSEMBLY

Open GraphicAdventure_Assembly.blend for editable separated parts.
GraphicAdventure_Assembly.glb is the exported assembly with modifiers applied.
The hidden "99 SOURCE - hidden original" collection retains the Tripo reference.
The original Downloads file was not modified.

344 mesh objects, 50,328 evaluated triangles. Basic review colours only.
Four wheels, doors, bonnet, upper/lower tailgate and equipment have named
parent pivots. This is an authoring assembly, not a finished gameplay rig.

6,035 local coverage probes pass before and after GLB reimport. No tested
static tyre/liner/floor/flare intersections. No base-mesh degenerate faces,
loose vertices or overconnected edges. Reimported part bounds match exactly.
Removing wheelhouse shells, floor and windscreen exposes 3,192 probes,
demonstrating that the coverage test detects these missing surfaces.
These tests cover sampled areas, not every possible view or movement.

REPAIRS CAUGHT DURING THIS BUILD
The initial pass exposed rear-arch reveal and cargo floor-edge gaps. Fitted
backing flanges and returns repaired them. Bonnet skirt bottoms now meet
the wing cross-section; roof-side closures follow the changing roof crown.
Wheel bolt mounting discs, lamp housings, handle mounts and seated wipers
were added after close-up review. See verification-first-pass.json for the
initial failures and verification.json for the delivered revision.

REUSABLE PROCESS
1. Measure this source's wheel centres, hood, shoulder, cabin taper and rear tuck.
2. Preserve the source; derive mating panels from shared profile stations.
3. Give every intended reveal a physical return or support behind it.
4. Inspect both sides, rear corners, wheel-off and underside views.
5. Check coverage, static tyre fit, pivots and the reimported exported file.
6. Keep structural/assembly QA separate from final engine readiness.

Textures/livery and a detailed cockpit are not included. LODs, collision,
rigging, moving-part clearance and Unreal integration remain future work.
The roof equipment and separate trim can be consolidated after editing to
reduce object/draw-call overhead for the actual game asset.

Authoring scripts are frozen under authoring-snapshot. The active scripts
live in C:/GrandTour/Art/VehicleTools. Their measured coordinates apply only
to this vehicle: reuse the checks and shared-interface approach, not its shape.
''',encoding='utf-8')
print(json.dumps({'delivery':str(P),'meshes':r['meshes'],'triangles':r['evaluated_triangles'],'coverage':r['coverage']['samples']}))
