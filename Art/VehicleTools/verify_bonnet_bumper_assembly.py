"""Validate saved component preservation, neighbouring surfaces and packaged panel."""
import bpy,sys,json,argparse,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bonnet_bumper_workshop as bb
wf=bb.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Bonnet_Bumper_Workshop.blend'))
new=[c for c in bpy.data.collections if c.get('gt_owner')==bb.OWNER]
prior=[c for c in bpy.data.collections if c.get('gt_owner') in [wf.OWNER,'GT_LIGHTS_01']]
preserved={c.name:wf.fingerprint(c)==c.get('fingerprint') for c in new+prior};assert all(preserved.values())
fixed=[o for c in prior for o in c.objects if o.type=='MESH']
fixed += [bpy.data.objects['Nose fascia | fitted apertures']]
bpy.context.view_layer.update();trees={o:wf.tree(o) for o in fixed};contacts=[]
for c in new:
    for o in c.objects:
        if o.type!='MESH' or 'chassis mounting arm' in o.name:continue
        tr=wf.tree(o)
        for other,tree in trees.items():
            if tr.overlap(tree):contacts.append([c.name,o.name,other.name])
assert not contacts,contacts
sys.path.insert(0,str(out/'GrandTour_Bonnet_Bumper_Addon.zip'))
import grandtour_panels
grandtour_panels.register();registered=hasattr(bpy.types.Scene,'gtbb');grandtour_panels.unregister();assert registered
report=dict(saved_component_fingerprints=preserved,unintended_fixed_neighbour_intersections=contacts,
            packaged_addon_registers=registered,
            scope='Static new component surfaces against the eleven existing wheel/fender/light collections and nose cap. Chassis mounting arms excluded as intentional interfaces. No wiper sweep, bonnet articulation, crash or game-readiness validation.')
(out/'assembly-reopen-check.json').write_text(json.dumps(report,indent=2));shutil.copy2(__file__,out/Path(__file__).name)
print('BONNET_BUMPER_ASSEMBLY_VERIFIED '+json.dumps(report),flush=True)
