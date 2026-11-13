"""Assemble unretouched actual Unreal captures; no generated imagery."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib,html
O=Path('C:/GrandTour/Art/Export/LidarStudy/FloraIntegration')
before=json.loads((O/'before-report.json').read_text());drive_report=json.loads((O/'check-report.json').read_text())
coverage=O/'coverageview-report.json'
after=json.loads(coverage.read_text()) if coverage.exists() and json.loads(coverage.read_text()).get('ok') else drive_report
assert before['views']==after['views'],'Camera comparison is not matched'
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
for group,names in [('road',['approach','mud']),('banks',['bank','context'])]:
 board=Image.new('RGB',(1660,1180),(16,27,27));d=ImageDraw.Draw(board)
 d.text((20,12),'LiDARStudy / Flora Paint + Rock Master — actual Unreal views',font=font,fill=(233,237,226))
 d.text((20,50),'BEFORE',font=small,fill='white');d.text((840,50),'INTEGRATED SECTION',font=small,fill='white')
 for row,name in enumerate(names):
  y=80+row*540
  for col,phase in enumerate(['before',after['phase']]):
   src=Image.open(O/(phase+'_'+name+'.png')).convert('RGB');src.thumbnail((800,500),Image.Resampling.LANCZOS);board.paste(src,(20+col*820,y))
  d.text((20,y+503),name.capitalize()+' / identical camera, exposure and sun',font=small,fill=(195,209,202))
 board.save(O/(group+'-comparison.jpg'),quality=94)
images=['road-comparison.jpg','banks-comparison.jpg','drive_fresh.png','drive_ruts.png']
if after['phase']=='coverageview':
 board=Image.new('RGB',(1660,610),(16,27,27));d=ImageDraw.Draw(board)
 d.text((20,12),'LiDARStudy / restored fern and grass coverage',font=font,fill='white')
 for col,(phase,label) in enumerate([('check','PREVIOUS PASS'),('coverageview','FERNS + GRASS RETAINED')]):
  x=20+col*820;d.text((x,50),label,font=small,fill='white')
  src=Image.open(O/(phase+'_mud.png')).convert('RGB');src.thumbnail((800,500),Image.Resampling.LANCZOS);board.paste(src,(x,80))
 board.save(O/'coverage-comparison.jpg',quality=94);images.insert(0,'coverage-comparison.jpg')
content='''<!doctype html><meta charset="utf-8"><title>LiDAR Flora integration</title><style>body{background:#101b1b;color:#e8eee6;font:17px system-ui;max-width:1640px;margin:30px auto}img{width:100%;height:auto}p{max-width:1000px}a{color:#a6dac9}</style><h1>LiDARStudy — integrated logging-road section</h1><p>Actual Unreal captures. Existing palette, lighting, native mud, water and terrain retained. This is the bounded 170–260m logging-road section, not a whole-map asset conversion.</p>'''
drive=drive_report.get('drive',{})
content+='<p><b>Last driving gate: '+('passed' if drive.get('ok') else 'NOT PASSED')+'</b>. The 0.8-throttle attempt bogged in the hollow before the ground-coverage restoration. Native soil settings were retained; this foliage change does not claim a new driving pass.</p>'
if after['phase']=='coverageview':content+='<p>Current views retain native grass and established low ferns alongside the new Flora Paint planting. Solid outcrop cores remain excluded.</p>'
content+='<table><tr><th>Matched view</th><th>Before median ms</th><th>After median ms</th></tr>'
for name in before['timings']:
 content+='<tr><td>'+name+'</td><td>'+str(round(before['timings'][name]['ms_p50'],1))+'</td><td>'+str(round(after['timings'][name]['ms_p50'],1))+'</td></tr>'
content+='</table><p>Hidden-editor tick intervals only; these are not standalone GPU benchmark results.</p>'
for name in images:
 if (O/name).exists():content+='<p>'+html.escape(name)+(' — earlier driving test, before ground-cover restoration' if name.startswith('drive_') else '')+'</p><img src="'+name+'">'
content+='<p><a href="profile.json">Editable profile</a> · <a href="install-report.json">Installation checks</a> · <a href="check-report.json">Runtime / driving checks</a> · <a href="verify-report.json">Saved-map reload verification</a></p>'
content+='<p>Before and after images completed. The baseline and latest driving-check editor processes subsequently returned access violations during shutdown; the earlier half-throttle run exited cleanly but also failed traversal. These are not clean end-to-end runtime passes.</p>'
(O/'review.html').write_text(content,encoding='utf-8')
print(str(O/'review.html'))
