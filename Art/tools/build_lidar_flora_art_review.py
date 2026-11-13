"""Same-camera game images only; no grading or synthetic scene imagery."""
from pathlib import Path
import json,html
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraWorld'
B=Path('D:/GrandTourBackups/FloraWorld_ArtDirection_2026-11-13/BeforeReview')
report=json.loads((O/'review-report.json').read_text());assert report['ok']
old=json.loads((B/'review-report.json').read_text())
assert report['views']==old['views'],'Comparison cameras must match'
assert report['runtime_settings']==old['runtime_settings'],'Comparison render settings must match'
assert report['runtime_lights']==old['runtime_lights'],'Comparison light settings must match'
assert report['runtime_fog']==old['runtime_fog'],'Comparison fog must match'
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',27)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',21)
def board(name,entries,note='Actual Unreal captures, resized only. Same camera, lighting, fog and render settings.'):
 im=Image.new('RGB',(2200,760),'#111e20');d=ImageDraw.Draw(im)
 for i,(label,p) in enumerate(entries):
  x=20+1100*i;d.text((x,15),label,font=font,fill='#e4eee9')
  a=ImageOps.contain(Image.open(p).convert('RGB'),(1060,640),Image.Resampling.LANCZOS)
  im.paste(a,(x+(1060-a.width)//2,65+(640-a.height)//2))
 d.text((20,718),note,font=small,fill='#bccac8')
 im.save(O/name,quality=95)
for key,label in [('approach','Forest approach'),('upper_road','Woodland road'),('bank','River bank'),('woodland','Forest interior'),('river_valley','River valley')]:
 board('art-'+key+'-comparison.jpg',[('BEFORE / '+label,B/('review_'+key+'.png')),('AFTER / Instance-volume painting',O/('review_'+key+'.png'))])
F=R/'Art/References/FloraPaint/OwnerStyle_2026-11-13'
board('art-reference-comparison.jpg',[('OWNER REFERENCE / Sunlit woodland',F/'03_sunlit_woodland.jpg'),('ACTUAL UNREAL / LiDARStudy',O/'review_upper_road.png')],'Supplied reference at left; actual saved LiDARStudy at right. Images resized only; no post-capture grading.')
page='''<!doctype html><meta charset="utf-8"><title>LiDARStudy reference art pass</title><style>body{background:#111e20;color:#e4eee9;max-width:1800px;margin:30px auto;padding:0 24px;font:18px/1.6 system-ui}img{width:100%;height:auto}a{color:#b6dfcc}section{margin:45px 0}h1,h2{font-weight:500}</style><h1>LiDARStudy / instance-volume art pass</h1><p>Painted clump depth, warm growth tips, broken bark moss and shared canopy colour families. Actual normal-viewport game captures. No post-capture grading or generated scenery.</p>'''
for name in ['art-reference-comparison','art-approach-comparison','art-upper_road-comparison','art-bank-comparison','art-woodland-comparison','art-river_valley-comparison']:
 page+='<section><img src="'+(O/(name+'.jpg')).as_uri()+'"></section>'
page+='<p>Map checks and native grass-contact API probe passed. No new full driving test. Performance timings are hidden-editor intervals, not proof of 60 fps. Extra shader arithmetic still needs GPU profiling despite no extra meshes or texture samples.</p>'
page+='<p><a href="'+(O/'review.html').as_uri()+'">Full eight-view review</a> | <a href="'+(R/'docs/LIDAR_FLORA_ART_DIRECTION.txt').as_uri()+'">Implementation notes</a></p>'
(O/'art-review.html').write_text(page,encoding='utf-8')
print(O/'art-review.html')
