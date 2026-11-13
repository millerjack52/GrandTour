"""Reopen and inspect cockpit interfaces against protected exterior components."""
import bpy,sys,json,argparse,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import cockpit_workshop as ci
wf=ci.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Cockpit_Workshop.blend'))
new=[c for c in bpy.data.collections if c.get('gt_owner')==ci.OWNER]
prior=[c for c in bpy.data.collections if c.get('gt_owner') in [wf.OWNER,'GT_LIGHTS_01','GT_BONNET_BUMPER_01','GT_DOORS_01','GT_REAR_BODY_01']]
preserved={c.name:wf.fingerprint(c)==c.get('fingerprint') for c in new+prior}
assert len(new)==12 and len(prior)==34 and all(preserved.values()),preserved
fixed=[o for c in prior for o in c.objects if o.type=='MESH']
fixed += [o for o in bpy.data.collections['Range Rover Classic — stylized study'].objects if o.type=='MESH' and any(s in o.name for s in ['connected body and flares','Roof with narrow edge folds','roof gutter','Roof end fold','Windscreen'])]
bpy.context.view_layer.update();trees={o:wf.tree(o) for o in fixed};contacts=[]
for c in new:
    for o in c.objects:
        if o.type!='MESH':continue
        tree=wf.tree(o)
        for other,ot in trees.items():
            if tree.overlap(ot):contacts.append([c.name,o.name,other.name])
fit=ci.report(new)
sys.path.insert(0,str(out/'GrandTour_Cockpit_Addon.zip'));import grandtour_cockpit
grandtour_cockpit.register();registered=hasattr(bpy.types.Scene,'gtci');grandtour_cockpit.unregister();assert registered
report=dict(saved_fingerprints=preserved,fixed_neighbour_intersections=contacts,fit=fit,packaged_addon_registers=registered,scope='Static mesh surface intersections against 34 exterior components and retained body, roof and windscreen. Not motion or human ergonomics validation.')
(out/'assembly-reopen-check.json').write_text(json.dumps(report,indent=2));shutil.copy2(__file__,out/Path(__file__).name)
print('COCKPIT_ASSEMBLY '+json.dumps(dict(collections=len(preserved),contacts=contacts,packaged_addon_registers=registered)),flush=True)
assert not contacts,contacts
