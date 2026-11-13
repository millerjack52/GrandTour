"""Freeze contact constraints against the approved pre-relief bank surface."""
import json,math,random,sys
from pathlib import Path
ROOT=Path('C:/GrandTour');sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_section_surface as S
QA=ROOT/'Saved/LidarAuthoringQA/RS7Relief';OUT=ROOT/'Art/Export/LidarStudy/FirstSection'
survey=json.loads((QA/'survey.json').read_text())
grid={(int(x),int(y)):z for x,y,z in json.loads((ROOT/'Saved/LidarAuthoringQA/RS7/dense-ground.json').read_text())['grid']}
def height(x,y):
 ix=math.floor(x/50)*50;iy=math.floor(y/50)*50;fx=(x-ix)/50;fy=(y-iy)/50
 return (grid[ix,iy]*(1-fx)+grid[ix+50,iy]*fx)*(1-fy)+(grid[ix,iy+50]*(1-fx)+grid[ix+50,iy+50]*fx)*fy
caps=[[a['x'],a['y'],0,a['radius']] for a in survey['anchors']]
plants=json.loads((ROOT/'Saved/LidarAuthoringQA/RS7/placement.json').read_text())['placement']
meshes={m['asset']:m for m in json.loads((OUT/'plants.json').read_text())}
old_relief=getattr(S,'base_relief',S.relief)
for p in plants:
 ca,sa=math.cos(math.radians(p['yaw'])),math.sin(math.radians(p['yaw']))
 for px,py,pz in meshes[p['mesh']]['probes']:
  px*=100*p['scale'];py*=-100*p['scale'];pz*=100*p['scale']
  x=p['x']+px*ca-py*sa;y=p['y']+px*sa+py*ca;z=p['z']+pz
  if not S.inside(x,y,20):continue
  clearance=z-height(x,y)-max(0,old_relief(x,y))
  if clearance<48:caps.append([x,y,max(0.,clearance-7),12])
rng=random.Random(71913);ledges=[];stones=[]
for a,b,wu,wv in [(-650,180,240,165),(120,-160,340,180),(770,270,180,220)]:
 for k in range(8):ledges.append([a+rng.uniform(-wu*.8,wu*.8),b+rng.uniform(-wv*.7,wv*.7),rng.uniform(48,110),rng.uniform(35,76),rng.uniform(-.55,.55),rng.uniform(18,38)])
 # Front-facing stepped lips must read from the river, not hide behind the crowns.
 for offset in [-.55,.05,.62]:ledges.append([a+wu*offset,b+wv*rng.uniform(.72,.98),rng.uniform(65,110),rng.uniform(38,62),rng.uniform(-.35,.35),rng.uniform(30,48)])
for k in range(48):stones.append([rng.uniform(-980,980),rng.uniform(-620,620),rng.uniform(15,35),rng.uniform(12,26),rng.uniform(-math.pi,math.pi),rng.uniform(9,20)])
data={'version':'RS7 physical relief 1','units':'cm','protected_instance_count':len(survey['anchors']),'caps':caps,'rock_ledges':ledges,'embedded_stones':stones}
(OUT/'physical-relief.json').write_text(json.dumps(data,separators=(',',':')))
print(json.dumps({'contact_constraints':len(caps),'ledges':len(ledges),'embedded_stones':len(stones)}))
