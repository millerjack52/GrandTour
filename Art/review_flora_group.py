"""Compose untouched Unreal captures beside the supplied artist reference."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraGroup'
REF=Path('C:/Users/mille/AppData/Local/Temp/codex-clipboard-87d6a348-848f-4c11-b06e-4b10d67ba70c.png')
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',21);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
def board(items,title,out,cols=2):
 w=660;h=330;pad=18;header=66;rowh=h+54
 canvas=Image.new('RGB',(cols*w+(cols+1)*pad,header+((len(items)+cols-1)//cols)*rowh+28),(18,29,30));d=ImageDraw.Draw(canvas)
 d.text((pad,17),title,font=font,fill=(229,235,231))
 for i,(path,label) in enumerate(items):
  x=pad+(i%cols)*(w+pad);y=header+(i//cols)*rowh
  d.text((x,y),label,font=small,fill=(200,214,211));image=Image.open(path).convert('RGB');image.thumbnail((w,h),Image.Resampling.LANCZOS);canvas.paste(image,(x+(w-image.width)//2,y+29+(h-image.height)//2))
 canvas.save(O/out,quality=94)
board([(REF,'REFERENCE / Casey Sheep — Flora Paint'),(O/'viewport-reference.png','UNREAL EDITOR / saved group test map')],'FOREST PATH / grouped material study','reference-comparison.jpg')
board([(O/'00_reference_sun.png','Warm sun / cool forest fill'),(O/'01_open_shade.png','Same scene / sky fill only'),(O/'02_sun_and_local_lights.png','Sun + warm spotlight + cool point light'),(O/'04_local_lights.png','Local lights / low sky fill')],'UNREAL / same camera and geometry; different lighting','lighting-comparison.jpg')
board([(O/'03_local_baseline.png','Local lights OFF / low sky'),(O/'04_local_lights.png','Local lights ON / source-transfer candidate'),(O/'04_local_lights.png','Source-transfer candidate / same light rig'),(O/'05_local_native_diagnostic.png','Native UE foliage lighting / same pigment and masks')],'LOCAL-LIGHT DIAGNOSTIC / response, not an exact-match claim','local-light-diagnostic.jpg')
names=['00_reference_sun','01_open_shade','02_sun_and_local_lights','03_local_baseline','04_local_lights','05_local_native_diagnostic']
pixels={n:np.asarray(Image.open(O/(n+'.png')).convert('RGB'),dtype=np.float32)/255 for n in names}
stats={n:{'mean_display_rgb':im.mean((0,1)).tolist(),'fraction_near_white':float((im.min(2)>.98).mean()),'fraction_near_black':float((im.max(2)<.02).mean())} for n,im in pixels.items()}
baseline=json.loads((R/'Art/Export/LidarStudy/FloraParity/protected-baseline.json').read_text())
protected={p:hashlib.sha256((R/p).read_bytes()).hexdigest()==sha for p,sha in baseline.items()};assert all(protected.values()),protected
report={'screenshots':stats,'local_light_mean_absolute_display_change':float(abs(pixels['04_local_lights']-pixels['03_local_baseline']).mean()),'protected_unchanged':protected,'performance_verified':False,'notes':['Pixel change verifies a visible effect, not physically correct leaf lighting','No image recolouring, grading or generative edits; board thumbnails resized only','Artist reference and Unreal have a matched source camera but a reduced plant palette']}
viewport=np.asarray(Image.open(O/'viewport-reference.png').convert('RGB'),dtype=np.float32)/255
report['editor_vs_scene_capture_mean_display_difference']=float(abs(viewport-pixels['00_reference_sun']).mean())
report['notes'].append('Editor high-resolution screenshot still shows noisier foliage edges than settled SceneCapture; do not conceal this difference')
(O/'review-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
