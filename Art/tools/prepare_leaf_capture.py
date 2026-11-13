from pathlib import Path
import json,math
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/LeafSurface/Capture';QA.mkdir(parents=True,exist_ok=True)
views=[dict(id='road',title='Roadside crown',position=[-55302.02429,3983.22879,10047.04590],target=[-55262.67,5999.33,10550],fov=65),dict(id='close',title='Overhanging leaf sprays',position=[-55262.67,4900,10200],target=[-55262.67,5999.33,10400],fov=45),dict(id='sunlit',title='Upper crown / sunward inspection',position=[-55262.67,7200,10800],target=[-55262.67,5999.33,10800],fov=50)]
cmds=['2:EnableCheats'];images=[];frame=5
for v in views:
 p=v['position'];d=[v['target'][i]-p[i] for i in range(3)];pitch=math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])));yaw=math.degrees(math.atan2(d[1],d[0]))
 cmds.append(f'{frame}:ke GTDistanceStyleController_0 SetReviewView '+ ' '.join(str(x) for x in [*p,pitch,yaw,v['fov']]))
 for strength,suffix in [(0,'before'),(1,'after')]:
  cmds.append(f'{frame+1}:ke GTDistanceStyleController_0 SetLeafReviewStrength {strength}')
  name=v['id']+'-'+suffix+'.png';images.append(name)
  cmds.append(f'{frame+16}:Shot filename="{(QA/name).as_posix()}" -nosuffix');frame+=21
quality=json.loads((ROOT/'Art/lidar_performance.json').read_text())['commands']
# Equal settings in both arms; camera zoom supplies close inspection at native size.
quality=[x for x in quality if not x.startswith('r.ScreenPercentage')]+['r.ScreenPercentage 100']
(QA/'plan.json').write_text(json.dumps(dict(commands=cmds,frames=frame+7,images=images,views=views,quality=quality),indent=2))
