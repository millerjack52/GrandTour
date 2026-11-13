"""Package unretouched contact-foam captures and validation evidence."""
from pathlib import Path
import json,sys,re
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[2]
out=root/'Art/Export/BenmoreGaea'/(sys.argv[1] if len(sys.argv)>1 else 'WaterSurface_Foam_20261011')
r=json.loads((out/'install-report.json').read_text());assert r['ok']
v=json.loads((out/'vehicle-review.json').read_text());assert v['ok'] and v['fixed_dt']['ok']
assert v['paired_foam_same_physics_state']
fresh=json.loads((out/'verify-report.json').read_text());assert fresh['ok']
crop=(0,260,960,600)
frames=[Image.open(out/('Verified_%02d.png'%i)).convert('RGB').crop(crop) for i in range(8)]
frames[0].save(out/'EdgeFoamMotion.gif',save_all=True,append_images=frames[1:],duration=[120,130]*4,loop=0)
before=Image.open(out/'Before_00.png').convert('RGB').crop(crop)
before.save(out/'EdgeFoamComparison.gif',save_all=True,append_images=[frames[0]],duration=1500,loop=0)
pair=[]
for name,label in [('Driver_FoamOff.png','Foam off'),('Driver_FoamOn.png','Contact foam on')]:
    frame=Image.open(out/name).convert('RGB')
    draw=ImageDraw.Draw(frame);draw.rectangle((8,8,175,36),fill=(20,24,26));draw.text((16,16),label,fill='white')
    pair.append(frame)
pair[0].save(out/'CarFoamComparison.gif',save_all=True,append_images=pair[1:],duration=1500,loop=0)
rows=[x for x in v['samples'] if x['case']=='AlongRiver']
drive=[Image.open(out/('AlongRiver_%02d.png'%(i+1))).convert('RGB') for i in range(len(rows))]
duration=[round((b['t']-a['t'])*100)*10 for a,b in zip(rows,rows[1:])];duration.append(duration[-1])
drive[0].save(out/'CarFoamMotion.gif',save_all=True,append_images=drive[1:],duration=duration,loop=0)
summary={'ok':True,'material_only':'Focused_' not in out.name,'protected_files_unchanged':r['protected_files_unchanged'],
    'wave_displacement_unchanged':r['wave_displacement_unchanged'],'fixed_dt':v['fixed_dt'],
    'cases':sorted(set(x['case'] for x in v['samples'])),'foam_comparison_same_physics_state':True,
    'vehicle':v['car_actor'],'performance_measured':False,'new_meshes':0,'new_textures':0}
if 'Focused_' in out.name:
    values=[tuple(map(int,m)) for m in re.findall(r'contactPeak=(\d+) contactCells=(\d+)',(out/'Review.log').read_text())]
    assert values and max(x[0] for x in values)>0
    assert 0<max(x[1] for x in values)<500
    summary['contact_peak_byte']=max(x[0] for x in values)
    summary['max_contact_cells_of_9216']=max(x[1] for x in values)
if 'Motion_' in out.name:
    assert v['steering_isolation_passed']
    rows=v['steering_isolation']
    summary['steering_isolation']={'samples':len(rows),
        'max_direction_error_deg':max(x['direction_error_deg'] for x in rows),
        'min_body_heading_difference_deg':min(x['body_heading_difference_deg'] for x in rows),
        'steer_range':[min(x['steer'] for x in rows),max(x['steer'] for x in rows)]}
status_path=out/'validation-status.json'
if status_path.exists():
    status=json.loads(status_path.read_text(encoding='utf-8-sig'))
    summary['editor_processes_exited_cleanly']=status['editor_processes_exited_cleanly']
    summary['process_status_report']=status_path.name
(out/'preview-report.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
