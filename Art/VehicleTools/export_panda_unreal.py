"""Use the tested static FBX exporter with Panda's actual component hierarchy."""
from pathlib import Path
import bpy
base=Path('C:/GrandTour/Art/VehicleTools/export_new_cars_unreal.py').read_text()
start=base.index(' def group(o):');end=base.index(' groups={}; material_specs={}',start)
group=''' def group(o):
  if any(m and m.name.endswith('Panda_Glass') for m in o.data.materials):return 'Glass'
  parent=o.parent
  while parent:
   if parent.name!='PANDA | assembly':
    g=clean(parent.name);pivots[g]=parent.matrix_world.translation.copy();return g
   parent=parent.parent
  cs=' '.join(c.name for c in o.users_collection)
  if o.get('panda_cabin') or 'Interior' in cs:return 'Cabin'
  if 'Underbody' in cs:return 'Underbody'
  if 'Front equipment' in cs:return 'FrontEquipment'
  if 'Roof and snorkel' in cs:return 'RoofEquipment'
  return 'Body'
'''
base=base[:start]+group+base[end:]
ns={'__name__':'panda_export_helpers'};exec(compile(base,'export_new_cars_unreal.py','exec'),ns)
ns['OUT']=Path('C:/GrandTour/Art/Export/VehicleTools/panda-unreal-v01')
ns['OUT'].mkdir(exist_ok=True)
report=ns['export']('Panda1990',Path('C:/GrandTour/Art/Export/VehicleTools/panda-interior-v02/Panda_Assembly.blend'))
assert report['triangles']==199052,report['triangles']
assert sum(len(p['source_objects']) for p in report['parts'])==798
assert len(next(p for p in report['parts'] if p['group']=='Glass')['source_objects'])==6
print('PANDA_EXPORT_VERIFIED',flush=True)
