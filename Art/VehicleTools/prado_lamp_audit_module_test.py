exec(compile(open('C:/GrandTour/Art/VehicleTools/prado_lamp_audit_inspect.py').read().split("render('rear-v08'")[0],'<audit_setup>','exec'))
import sys
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from prado_lamp_repair_module import repair_rear_lamps
r=repair_rear_lamps();(OUT/'module-manifest.json').write_text(json.dumps(r,indent=2))
sh.color_type='MATERIAL'
render('module-rear',(0,.43,.29),(0,3,.1),.70)
render('module-quarter',(.08,.38,.29),(2,3,.4),.69)
for o in sc.objects:
 if o.type=='MESH' and any(c.name in ['04 Spare wheel','06 Roof rack and cargo','07 Side equipment','09 Small fittings'] for c in o.users_collection):o.hide_render=True
render('module-corner',(.17,.43,.255),(1.7,3,.4),.20)
render('module-body-only',(0,.43,.27),(0,3,0),.49)
print(json.dumps(r))
