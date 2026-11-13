from pathlib import Path
import json,math
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RoadParallax/Native';QA.mkdir(exist_ok=True)
old=json.loads((ROOT/'Saved/LidarAuthoringQA/CohesiveRoads/check.json').read_text())
views={r['view']:r for r in old['views']}
r=views['R03'];p=r['position'];t=r['target_position'];dx=t[0]-p[0];dy=t[1]-p[1];length=math.hypot(dx,dy);side=[-dy/length,dx/length]
views['R07']=dict(view='R07',title='Exposed shoulder / low oblique view',position=[p[0]+side[0]*250,p[1]+side[1]*250,p[2]+40],target_position=[t[0]+side[0]*250,t[1]+side[1]*250,t[2]+30],fov=68)
commands=['2:EnableCheats']
preset=json.loads((ROOT/'Art/lidar_performance.json').read_text())['commands']
def pose(frame,p,t,fov=68):
 d=[t[i]-p[i] for i in range(3)];pitch=math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])));yaw=math.degrees(math.atan2(d[1],d[0]))
 commands.append(str(frame)+':ke GTDistanceStyleController_0 SetReviewView '+' '.join(f'{x:.5f}' for x in [*p,pitch,yaw,fov]))
def shot(frame,name,res='1600x900'):
 commands.append(f'{frame}:Shot filename="{(QA/(name+".png")).as_posix()}" -nosuffix')
frame=5;images=[]
for ident,mode,suffix in [('R03',2,''),('R03',0,'-before'),('R03',1,'-normal-only'),('R07',2,''),('R07',0,'-before'),('R07',1,'-normal-only')]:
 v=views[ident];commands.append(f'{frame}:ke GTDistanceStyleController_0 SetSurfaceReviewMode {mode}');pose(frame+1,v['position'],v['target_position']);shot(frame+12,ident+suffix);images.append(ident+suffix+'.png');frame+=16
commands.append(f'{frame}:ke GTDistanceStyleController_0 SetSurfaceReviewMode 2')
frames=[]
for i in range(8):
 off=math.sin(i/7*math.pi*2)*40;p2=[p[0]+side[0]*off,p[1]+side[1]*off,p[2]]
 pose(frame+1,p2,t);shot(frame+6,f'motion-{i:03d}','960x540');frames.append(str(QA/f'motion-{i:03d}.png'));frame+=8
(QA/'plan.json').write_text(json.dumps(dict(commands=commands,frames=frame+8,images=images,motion=frames,views=[views[x] for x in ['R03','R07']],quality=preset),indent=2))
print('Prepared focused standalone stills and eight camera samples')
