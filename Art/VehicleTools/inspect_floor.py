import bpy,sys,json
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
import assembly_contracts as ac
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/crafted-character-detailed-v05/Crafted_Utility_Detailed.blend')
rows=[]
for o in bpy.context.scene.objects:
    if o.type=='MESH' and any(s in o.name.lower() for s in ['floor','seat','rail','sill','backing','derived skin','bulkhead']):
        rows.append([o.name,ac.bounds(o),[c.name for c in o.users_collection]])
open('C:/GrandTour/Art/VehicleTools/floor-inspection.json','w').write(json.dumps(rows,indent=2))
