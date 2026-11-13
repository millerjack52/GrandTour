from pathlib import Path
import json,math,sys
warmth='--warmth' in sys.argv
canopy='--canopy' in sys.argv
ROOT=Path('C:/GrandTour');QA=ROOT/('Saved/LidarAuthoringQA/CanopyInterior/Capture' if canopy else 'Saved/LidarAuthoringQA/PaletteWarmth/Capture' if warmth else 'Saved/LidarAuthoringQA/PaletteRefinement/Capture');QA.mkdir(parents=True,exist_ok=True)
old=json.loads((ROOT/'Saved/LidarAuthoringQA/RS7/runtime-evergreen.json').read_text(encoding='utf-8-sig'));v=next(x for x in old['views'] if x['view']=='V02');v.update(id='valley',title='River valley')
road=json.loads((ROOT/'Saved/LidarAuthoringQA/CohesiveRoads/check.json').read_text())['views'];r=next(x for x in road if x['view']=='R03')
views=[v,dict(id='road',title='Road, shoulder and near foliage',position=r['position'],target=r['target_position'],fov=68),dict(id='leaves',title='Sunlit broad leaves',position=[-55262.67,7200,10800],target=[-55262.67,5999.33,10800],fov=50)]
if canopy:views.append(dict(v,id='interior-only',title='Isolated understory validation'))
commands=['2:EnableCheats','3:ke GTDistanceStyleController_0 FinishReviewShaders'];images=[];frame=5
if canopy:commands.append('8:getall GTDistanceStyleController bHidden')
for v in views:
 p=v['position'];d=[v['target'][i]-p[i] for i in range(3)];pitch=math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])));yaw=math.degrees(math.atan2(d[1],d[0]))
 commands.append(f'{frame}:ke GTDistanceStyleController_0 SetReviewView '+' '.join(str(x) for x in [*p,pitch,yaw,v['fov']]))
 for preset,suffix in [('MutedPalette' if warmth else 'BeforePalette','before'),('Cohesive','after')]:
  if canopy:commands.append(f'{frame+1}:ke GTDistanceStyleController_0 SetCanopyDepthReview '+('0' if suffix=='before' else '2' if v['id']=='interior-only' else '1'))
  else:commands.append(f'{frame+1}:ke GTDistanceStyleController_0 SetStylePreset {preset}')
  name=v['id']+'-'+suffix+'.png';images.append(name);commands.append(f'{frame+120}:Shot filename="{(QA/name).as_posix()}" -nosuffix');frame+=140
quality=[x for x in old['commands'] if not x.startswith('r.ScreenPercentage')]+['r.ScreenPercentage 100']
(QA/'plan.json').write_text(json.dumps(dict(commands=commands,images=images,views=views,frames=frame+7,quality=quality),indent=2))
