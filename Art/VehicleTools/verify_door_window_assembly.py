"""Reopen the delivered assembly, compare previous components and fixed neighbours."""
import bpy,sys,json,argparse,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import door_window_workshop as dw
wf=dw.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--render-orthos',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Doors_Windows_Workshop.blend'))
new=[c for c in bpy.data.collections if c.get('gt_owner')==dw.OWNER]
prior=[c for c in bpy.data.collections if c.get('gt_owner') in [wf.OWNER,'GT_LIGHTS_01','GT_BONNET_BUMPER_01']]
preserved={c.name:wf.fingerprint(c)==c.get('fingerprint') for c in new+prior}
assert len(new)==12 and len(prior)==15 and all(preserved.values()),preserved
fit=dw.fit_report(new)
assert max(fit['boundary_error_m'].values())<1e-5 and all(fit['closed_meshes'].values()) and all(fit['pane_seats'].values()),fit
fixed=[o for c in prior for o in c.objects if o.type=='MESH']
fixed += [o for o in bpy.data.collections['Range Rover Classic — stylized study'].objects if any(s in o.name for s in ['connected body and flares','Roof with narrow edge folds','roof gutter'])]
bpy.context.view_layer.update();trees={o:wf.tree(o) for o in fixed};contacts=[]
for c in new:
    for o in c.objects:
        if o.type!='MESH':continue
        tr=wf.tree(o)
        for other,tree in trees.items():
            if tr.overlap(tree):contacts.append([c.name,o.name,other.name])
sys.path.insert(0,str(out/'GrandTour_Doors_Windows_Addon.zip'))
import grandtour_doors
grandtour_doors.register();registered=hasattr(bpy.types.Scene,'gtdw');grandtour_doors.unregister();assert registered
report=dict(saved_component_fingerprints=preserved,fixed_neighbour_surface_contacts=contacts,fit=fit,
            packaged_addon_registers=registered,
            scope='Static side components against the fifteen previous workshop collections, retained rear body/arches and roof/gutters. Internal mount/seal overlaps are designed contact; no door motion or game-readiness validation.')
(out/'assembly-reopen-check.json').write_text(json.dumps(report,indent=2));shutil.copy2(__file__,out/Path(__file__).name)
print('DOOR_WINDOW_ASSEMBLY '+json.dumps(report),flush=True)
assert not contacts,contacts
if a.render_orthos:
    from mathutils import Vector
    sc=bpy.context.scene;cam=sc.camera
    for name,loc,target,scale in [('11-front-fit',(0,-7,1.04),(0,0,1.04),2.95),('12-top-fit',(0,.12,7),(0,.12,0),6.50)]:
        cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
        sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
