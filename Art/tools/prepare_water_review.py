"""Capture the installed water without modifying map assets or materials."""
from pathlib import Path
import json, math, sys

ROOT = Path('C:/GrandTour')
stage = 'Before' if '--before' in sys.argv else 'After' if '--after' in sys.argv else None
quick = '--quick' in sys.argv
woodland = '--woodland' in sys.argv
QA = ROOT / ('Saved/LidarAuthoringQA/WoodlandView/Capture' if woodland else 'Saved/LidarAuthoringQA/WaterRefinement/'+stage if stage else 'Saved/LidarAuthoringQA/WaterReview/Capture')
QA.mkdir(parents=True, exist_ok=True)
source = ROOT / 'Art/Export/LidarStudy/Place'
poses = json.loads((source / 'waterdiag.json').read_text())['poses']
views = []
for name, pose in [('river-bank', 'river_A'), ('river-above', 'river_check'),
                   ('access-pond-bank', 'pond_A'), ('access-pond-above', 'pond_check')]:
    v = poses[pose]
    views.append(dict(id=name, position=v['camera'], target=v['target'], fov=68))
# The current river pass raised the water above the old diagnostic eye position.
# Keep both low views above the surface and clear of the intervening bank.
views[0].update(position=[-47770.38,-31326.61,5212.78], target=[-48870.38,-32926.61,4932.78])
views[2].update(position=[-45450,11750,8458.66], target=[-43950,10750,7878.66])
data = json.loads((source / 'prepare.json').read_text())
x,y,z = next(w['probe'] for w in data['water'] if w['name']=='MappedPond')
views.extend([
    dict(id='mapped-pond-above', position=[x-2400,y-2500,z+2300], target=[x,y,z], fov=68),
    dict(id='mapped-pond-low', position=[x-900,y-700,z+250], target=[x+700,y+700,z], fov=68),
])
if woodland:
    views=[
        dict(id='woodland-overview',position=[-54000,22000,17500],target=[-45000,12000,9000],fov=70),
        dict(id='woodland-pond',position=[-47850,13950,9798.6588],target=[-44550,11150,7798.6588],fov=80),
    ]
commands = ['2:EnableCheats', '3:ke GTDistanceStyleController_0 FinishReviewShaders']
if woodland:commands.append('4:r.SetRes 1600x900w')
images = []
frame = 5
for v in views:
    p=v['position']; d=[v['target'][i]-p[i] for i in range(3)]
    pitch=math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])))
    yaw=math.degrees(math.atan2(d[1],d[0]))
    commands.append(f'{frame}:ke GTDistanceStyleController_0 SetReviewView '+ ' '.join(str(n) for n in [*p,pitch,yaw,v['fov']]))
    name=v['id']+'.png'; images.append(name)
    commands.append(f'{frame+(30 if quick else 150)}:Shot filename="{(QA/name).as_posix()}" -nosuffix')
    frame+=45 if quick else 180
old=json.loads((ROOT/'Saved/LidarAuthoringQA/RS7/runtime-evergreen.json').read_text(encoding='utf-8-sig'))
quality=[c for c in old['commands'] if not c.startswith('r.ScreenPercentage')]+['r.ScreenPercentage 100']
(QA/'plan.json').write_text(json.dumps(dict(commands=commands, images=images, views=views, frames=frame+7, quality=quality),indent=2))
