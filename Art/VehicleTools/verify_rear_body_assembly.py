"""Inspect persisted rear components against the saved front/side/roof neighbours."""
import bpy,sys,json,argparse,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import rear_body_workshop as rb
wf=rb.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Rear_Body_Workshop.blend'))
new=[c for c in bpy.data.collections if c.get('gt_owner')==rb.OWNER]
prior=[c for c in bpy.data.collections if c.get('gt_owner') in [wf.OWNER,'GT_LIGHTS_01','GT_BONNET_BUMPER_01','GT_DOORS_01']]
preserved={c.name:wf.fingerprint(c)==c.get('fingerprint') for c in new+prior};assert len(new)==7 and len(prior)==27 and all(preserved.values()),preserved
fit=rb.fit_report(new);assert max(fit['boundary_error_m'].values())<1e-5 and all(fit['closed_selected_meshes'].values()) and not fit['lamp_column_intersections'],fit
fixed=[o for c in prior for o in c.objects if o.type=='MESH']
fixed += [o for o in bpy.data.collections['Range Rover Classic — stylized study'].objects if any(s in o.name for s in ['connected body and flares','Roof with narrow edge folds','roof gutter','Roof end fold'])]
bpy.context.view_layer.update();trees={o:wf.tree(o) for o in fixed};contacts=[];mounts=[]
for c in new:
    for o in c.objects:
        if o.type!='MESH':continue
        tree=wf.tree(o)
        for other,ot in trees.items():
            if tree.overlap(ot):
                item=[c.name,o.name,other.name]
                if o.get('intentional_roof_mount') and other.name.startswith('Roof'):mounts.append(item)
                else:contacts.append(item)
sys.path.insert(0,str(out/'GrandTour_Rear_Body_Addon.zip'));import grandtour_rear
grandtour_rear.register();registered=hasattr(bpy.types.Scene,'gtrb');grandtour_rear.unregister();assert registered
report=dict(saved_fingerprints=preserved,unintended_fixed_neighbour_intersections=contacts,intentional_roof_mount_and_seal_contacts=mounts,fit=fit,packaged_addon_registers=registered,
    scope='Seven rear components against the previous 27 workshop collections, retained body and roof. Roof hinge and header-seal contacts are listed separately. No moving sweeps, collision structure or game-export validation.')
(out/'assembly-reopen-check.json').write_text(json.dumps(report,indent=2));shutil.copy2(__file__,out/Path(__file__).name)
print('REAR_ASSEMBLY '+json.dumps(report),flush=True);assert not contacts,contacts
