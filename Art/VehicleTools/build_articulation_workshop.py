import bpy,sys,json,argparse,shutil,zipfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent));import articulation_workshop as ar;import wheel_fender_workshop as wf;import fit_articulation_interfaces as fit
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output).resolve()
if out.exists() and any(out.iterdir()):raise RuntimeError('Use an empty revision folder')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/cockpit-workshop-v04/RangeRover_Cockpit_Workshop.blend')
comps=[c for c in bpy.data.collections if c.get('gt_owner')];source_hashes={c.name:wf.fingerprint(c) for c in comps}
assert all(source_hashes[c.name]==c.get('fingerprint') for c in comps),'Edited source components: preserve before rigging'
fit_changes=fit.migrate();original={c.name:wf.fingerprint(c) for c in comps}
changed_collections=[n for n in original if original[n]!=source_hashes[n]]
world={o.name:[list(row) for row in o.matrix_world] for c in comps for o in c.objects}
groups=ar.build()
guarded=json.loads(ar.root()['guarded_collections'])
for n in changed_collections:
    if n not in guarded:
        g=ar.empty('RIG GUARD | '+n,bpy.data.collections[n]);g.hide_viewport=True;g.hide_render=True;g['gt_rig_guard']=True;guarded.append(n);bpy.data.collections[n]['gt_articulated']=True
ar.root()['guarded_collections']=json.dumps(sorted(guarded))
unchanged={c.name:wf.fingerprint(SimpleNamespace(objects=[o for o in c.objects if not o.get('gt_rig_guard')]))==original[c.name] for c in comps}
error=max(abs(bpy.data.objects[n].matrix_world[i][j]-m[i][j]) for n,m in world.items() for i in range(4) for j in range(4))
assert all(unchanged.values()) and error<1e-6,(unchanged,error)
sc=bpy.context.scene;sc['articulation_source_hashes']=json.dumps(original);sc['articulation_rest_matrices']=json.dumps(world);sc['articulation_original_source_hashes']=json.dumps(source_hashes);sc['articulation_fit_changes']=json.dumps(fit_changes)
sc['articulation_groups']=json.dumps(groups);sc['shape_status']='Learning prototype: user finds shape off; details improved. Not an approved shape template.'
for t in list(bpy.data.texts):
    if t.name.startswith('START HERE'):bpy.data.texts.remove(t)
t=bpy.data.texts.new('START HERE - movement controls.py');t.write("import sys\nsys.path.insert(0, 'C:/GrandTour/Art/VehicleTools')\nimport articulation_workshop\narticulation_workshop.register()\n")
t=bpy.data.texts.new('MOVEMENT - read first');t.write('Select GT | inspection controls and edit Custom Properties, or run START HERE for GT Parts controls.\nDoors, steer and roll are degrees. Positive steer turns toward vehicle left.\nStandard Blender drivers work without installing the panel.\nAuthor shape/components in the static cockpit source; old rebuilds are blocked in this rigged derivative.\nThis is a learning prototype with unapproved overall shape. See sweep-report.json for measured contacts.\nNo suspension, physics, game rig or export validation yet.\n')
for f in [__file__,ar.__file__,wf.__file__,fit.__file__]:shutil.copy2(f,out/Path(f).name)
with zipfile.ZipFile(out/'GrandTour_Articulation_Addon.zip','w',zipfile.ZIP_DEFLATED) as z:z.write(ar.__file__,'grandtour_articulation/__init__.py')
sc.camera.data.type='ORTHO';sc.camera.data.ortho_scale=5.65
(out/'build-report.json').write_text(json.dumps(dict(post_fit_components_preserved_by_rig=unchanged,unchanged_original_collections=[n for n in original if n not in changed_collections],changed_collections=changed_collections,fit_changes=fit_changes,neutral_world_transform_max_error=error,groups=groups),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RangeRover_Articulation_Workshop.blend'));print('ARTICULATION_SAVED',flush=True)
