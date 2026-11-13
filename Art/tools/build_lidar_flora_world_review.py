"""Present unaltered game captures and owner references; resize only, no grading."""
from pathlib import Path
import json,html
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraWorld';F=R/'Art/References/FloraPaint/OwnerStyle_2026-11-13'
report=json.loads((O/'review-report.json').read_text());assert report['ok']
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',27)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',21)
def board(name,entries,note):
 w,h=2200,770;im=Image.new('RGB',(w,h),'#111e20');d=ImageDraw.Draw(im)
 for col,(label,p) in enumerate(entries):
  x=20+1100*col;d.text((x,14),label,font=font,fill='#e4eee9')
  a=Image.open(p).convert('RGB');a=ImageOps.contain(a,(1060,650),Image.Resampling.LANCZOS)
  im.paste(a,(x+(1060-a.width)//2,58+(650-a.height)//2))
 d.text((20,728),note,font=small,fill='#bccac8');im.save(O/name,quality=94)
board('reference-comparison.jpg',[('OWNER REFERENCE / Sunlit woodland',F/'03_sunlit_woodland.jpg'),('ACTUAL UNREAL / Whole-map woodland',O/'review_upper_road.png')],'Source reference at left; actual saved LiDARStudy at right. Images resized only; no post-capture colour changes.')
board('valley-comparison.jpg',[('HISTORICAL / Highest-LOD screenshot',R/'Art/Export/LidarStudy/FloraIntegration/longrange_river_valley.png'),('CURRENT / Actual gameplay LODs',O/'review_river_valley.png')],'Same camera; different capture paths. Historical HighResShot forced LOD0. Current viewport capture retains gameplay LODs.')
board('distance-comparison.jpg',[('HISTORICAL / Highest-LOD screenshot',R/'Art/Export/LidarStudy/FloraIntegration/longrange_long_valley.png'),('CURRENT / Actual gameplay LODs',O/'review_long_valley.png')],'Same camera; different capture paths. Historical HighResShot forced LOD0. Current viewport capture retains gameplay LODs.')
before=Path('D:/GrandTourBackups/FloraWorld_Polish_2026-11-13/BeforeAtmosphere')
if before.exists():
 for key,label in [('upper_road','woodland'),('river_valley','valley')]:
  board('polish-'+label+'-comparison.jpg',[('EARLIER / Actual game viewport',before/('review_'+key+'.png')),('CURRENT / Actual game viewport',O/('review_'+key+'.png'))],'Matched camera and normal viewport capture. Earlier shader pass versus current fog, canopy coverage and material refinement.')
titles={'approach':'Logging-road approach','mud':'Native mud corridor','bank':'Rock Master bank','woodland':'Forest interior beyond the original pilot','upper_road':'Upper woodland road','integrated_hillside':'Hillside canopy','river_valley':'Across the river valley','long_valley':'Long valley'}
sections=[]
for key,label in titles.items():
 p=O/('review_'+key+'.png');t=report['timings'][key]
 sections.append(f'<section><h2>{label}</h2><a href="{p.as_uri()}"><img src="{p.as_uri()}" alt="Actual Unreal: {label}"></a><p>Editor tick interval: {t["ms_p50"]:.1f} ms median; {t["ms_p95"]:.1f} ms p95. Not a standalone GPU benchmark.</p></section>')
refs=''.join(f'<img src="{(F/n).as_uri()}" alt="Owner reference">' for n in ['03_sunlit_woodland.jpg','01_colourful_woodland.jpg','02_cool_mist.jpg'])
text='''<!doctype html><meta charset="utf-8"><title>LiDARStudy — Flora Paint whole-map review</title><style>body{margin:32px auto;max-width:1600px;padding:0 24px;background:#101c20;color:#e7eeeb;font:17px/1.5 system-ui}h1,h2{font-weight:500}img{max-width:100%;height:auto}section{margin:40px 0;border-top:1px solid #365052;padding-top:20px}.refs{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}p{color:#b6c9c6}a{color:#a5d6d1}</style><h1>LiDARStudy / whole-map Flora Paint review</h1><p>Actual Unreal runtime captures of the saved map. No generated game images or post-capture colour grading. The sunlit woodland is the daytime anchor; the other two references guide compatible atmosphere and colour variants.</p><div class="refs">'''+refs+'</div><p>146,197 living trees; 135,201 new ground plants; 139,753 retained low native ferns; 11,792 Rock Master rocks. Native mud, terrain and water preserved.</p>'
text=text.replace('139,753 retained low native ferns','139,753 retained fern positions using painted pack fronds')
text=text.replace('146,197 living trees;', '146,197 living canopy trees; 13,030 saplings;')
audit=json.loads((O/'visual-audit.json').read_text()) if (O/'visual-audit.json').exists() else {'status':'Visual review pending'}
text+='<p>Visual review: '+html.escape(audit.get('summary',audit.get('status','Pending')))+'</p>'
text+='<p>Runtime rendering settings: '+html.escape(json.dumps(report.get('runtime_settings',{})))+'</p>'
text+='<p>Timing scope: hidden editor, not a clean standalone or target-device benchmark. The earlier deep-mud traversal failure is separate and remains unresolved.</p>'
text+='<p>Capture method: '+html.escape(report.get('capture_method','HighResShot diagnostic capture'))+'</p>'
if before.exists():
 text+='<section><h2>Matched gameplay captures / final polish</h2>'+''.join('<img src="'+(O/('polish-'+name+'-comparison.jpg')).as_uri()+'">' for name in ['woodland','valley'])+'</section>'
text+='<p>Fresh saved-map integrity checks are included before PIE. Review outcome and native grass-contact evidence are in review-report.json. These visuals are not a 60 fps certification.</p>'
text+=''.join(sections)
board('contact-comparison.jpg',[('NATIVE GRASS / Before contact',O/'contact_before.png'),('NATIVE GRASS / After contact',O/'contact_after.png')],'Contact probe: bent/removed instances 3 to 5. Foreground ferns are static; this is not a full driving test.')
text+='<section><h2>Native grass contact probe</h2><img src="'+(O/'contact-comparison.jpg').as_uri()+'"><p>'+html.escape(json.dumps(report['grass_contact_probe']))+'</p></section>'
(O/'review.html').write_text(text,encoding='utf-8')
print(str(O/'review.html'))
