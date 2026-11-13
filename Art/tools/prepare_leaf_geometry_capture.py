from pathlib import Path
import json,math,shutil
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/LeafGeometry/Capture';QA.mkdir(parents=True,exist_ok=True)
previous=ROOT/'Saved/LidarAuthoringQA/LeafSurface/Capture'
old=json.loads((previous/'plan.json').read_text());views=old['views']
for v in views:
 src=previous/(v['id']+'-after.png');dst=QA/(v['id']+'-before.png')
 if not dst.exists():shutil.copy2(src,dst)
# Additional natural-LOD views, receding from the same upper crown.
views+= [dict(id='range20',title='Crown at longer range / natural LOD',position=[-55262.67,8000,10800],target=[-55262.67,5999.33,10800],fov=50),dict(id='range35',title='Crown at longer range / natural LOD',position=[-55262.67,9500,10800],target=[-55262.67,5999.33,10800],fov=50)]
commands=['2:EnableCheats'];images=[];frame=5
for v in views:
 p=v['position'];d=[v['target'][i]-p[i] for i in range(3)];pitch=math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])));yaw=math.degrees(math.atan2(d[1],d[0]))
 commands.append(f'{frame}:ke GTDistanceStyleController_0 SetReviewView '+' '.join(str(x) for x in [*p,pitch,yaw,v['fov']]))
 commands.append(f'{frame+1}:ke GTDistanceStyleController_0 SetLeafReviewStrength 1')
 name=v['id']+'-after.png';images.append(name)
 commands.append(f'{frame+17}:Shot filename="{(QA/name).as_posix()}" -nosuffix');frame+=23
(QA/'plan.json').write_text(json.dumps(dict(commands=commands,frames=frame+7,images=images,views=views,quality=old['quality']),indent=2))
