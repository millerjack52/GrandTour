"""Save and audit the reviewed low-poly source, without Unreal or FBX changes."""
import bpy, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REVIEW=ROOT/'Art/Export/LandCruiser/05'
OUT=ROOT/'Art/Vehicles/LandCruiser80'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(REVIEW/'LandCruiser80.blend'))
scene=bpy.context.scene
dg=bpy.context.evaluated_depsgraph_get()
issues=[];degenerate=[];counts={};vertices=[];objects=0
for c in bpy.data.collections:
    if c.name in {'Studio','Reference','Pivots','Collection'}:continue
    triangles=0
    for ob in c.objects:
        if ob.type not in {'MESH','CURVE','FONT'}:continue
        objects+=1;ev=ob.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles()
        triangles+=len(me.loop_triangles)
        world=[ev.matrix_world@v.co for v in me.vertices];vertices.extend(world)
        if any(not math.isfinite(float(v)) for co in world for v in co):issues.append('Non-finite vertex: '+ob.name)
        bad=0
        for tri in me.loop_triangles:
            a,b,d=[world[i] for i in tri.vertices]
            if (b-a).cross(d-a).length<1e-10:bad+=1
        if bad:degenerate.append({'object':ob.name,'triangles':bad})
        ev.to_mesh_clear()
    counts[c.name]=triangles
hubs={}
for key,expected in {'FL':(.8,-1.425,.4),'FR':(-.8,-1.425,.4),'RL':(.8,1.425,.4),'RR':(-.8,1.425,.4)}.items():
    ob=bpy.data.objects['Wheel_'+key];pos=list(ob.matrix_world.translation);hubs[key]=pos
    if max(abs(a-b) for a,b in zip(pos,expected))>1e-5:issues.append('Wheel pivot: '+key)
bounds=[[min(v[i] for v in vertices),max(v[i] for v in vertices)] for i in range(3)]
if bounds[1][1]-bounds[1][0]>5.0 or bounds[2][1]>2.0:issues.append('Vehicle bounds exceed expected envelope')
if sum(counts.values())>30000:issues.append('Modelling budget exceeds 30k triangles')
report={'source':'Art/Vehicles/LandCruiser80/LandCruiser80.blend','review_iteration':'05','triangles':sum(counts.values()),
        'triangles_by_collection':counts,'modelling_objects':objects,'wheel_pivots_blender_metres':hubs,'bounds_metres':bounds,
        'degenerate_triangles':degenerate,'errors':issues,'checks_pass':not issues and not degenerate,
        'scope':'Geometry, dimensions and pivots only; no game, collision, UV or performance validation'}
(OUT/'model_check.json').write_text(json.dumps(report,indent=2))
print('LC_SOURCE_AUDIT '+json.dumps(report),flush=True)
if issues or degenerate:raise RuntimeError('Geometry audit failed; see model_check.json')
bpy.ops.object.select_all(action='DESELECT')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.shading.type='SOLID';area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.shading.show_cavity=True
scene['ModellingStage']='First low-poly exterior and cockpit; UV, textures, collision and game rig pending'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LandCruiser80.blend'))
print('LC_SOURCE_SAVED '+str(OUT/'LandCruiser80.blend'),flush=True)
