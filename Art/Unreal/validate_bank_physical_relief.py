import unreal as u,json,math,sys
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(root/'Art/Unreal'))
import lidar_first_section as section
qa=root/'Saved/LidarAuthoringQA/RS7Relief'
report=section.validate();plants=json.loads((section.QA/'placement.json').read_text())['placement']
meshes={r['asset']:r for r in json.loads((section.OUT/'plants.json').read_text())}
author=next(a for a in section.actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));g=section.GroundSampler(author)
checks=[];total=0
for p in plants:
 ca,sa=math.cos(math.radians(p['yaw'])),math.sin(math.radians(p['yaw']));clear=[]
 for px,py,pz in meshes[p['mesh']]['probes']:
  px*=100*p['scale'];py*=-100*p['scale'];pz*=100*p['scale']
  x=p['x']+px*ca-py*sa;y=p['y']+px*sa+py*ca;z=p['z']+pz
  clear.append(z-(g.height(x,y)+max(0,section.S.relief(x,y))))
 clipped=sum(v<-12 for v in clear)/len(clear);total+=len(clear)
 assert clipped<=p['clipping_fraction']+1e-6,(p['mesh'],clipped,p['clipping_fraction'])
 checks.append({'mesh':p['mesh'],'clipping_fraction':clipped,'previous_clipping_fraction':p['clipping_fraction']})
report.update(frond_probe_count=total,plants_checked=len(checks),frond_penetration_not_increased=True,planting_unchanged=report['snapshot']==json.loads((qa/'survey.json').read_text())['snapshot'])
(qa/'validation.json').write_text(json.dumps(report,indent=2));(qa/'frond-checks.json').write_text(json.dumps(checks,indent=2));print('BANK_PHYSICAL_RELIEF_VALIDATED',report)
