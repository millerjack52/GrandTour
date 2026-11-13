"""Pixel evidence and a clock-sampled preview from the saved Unreal water captures."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'
report=json.loads((OUT/'appearance-report.json').read_text())
assert report['ok'] and report['reloaded']
before=np.asarray(Image.open(OUT/'Appearance_Ford_Before.png').convert('RGB'),dtype=float)
after=np.asarray(Image.open(OUT/'Appearance_Ford_After.png').convert('RGB'),dtype=float)
box=(1020,520,1380,780)
x0,y0,x1,y1=box
def roi(a):return a[y0:y1,x0:x1]
b=roi(before);a=roi(after)
frames=[Image.open(OUT/'Appearance_Ford_After.png').convert('RGB')]
frames += [Image.open(OUT/('Appearance_Ford_Motion%02d.png'%i)).convert('RGB') for i in range(1,16)]
motion=[]
for i in range(1,len(frames)):
    delta=np.abs(roi(np.asarray(frames[i],dtype=float))-roi(np.asarray(frames[i-1],dtype=float)))
    motion.append({'from_seconds':12+(i-1)/8,'to_seconds':12+i/8,
                   'mean_abs_rgb':float(delta.mean()),'changed_over_10_pct':float((delta.max(axis=2)>10).mean()*100)})
# A single shared palette reduces false colour flicker caused by per-frame quantization.
thumbs=[im.resize((960,600),Image.Resampling.LANCZOS) for im in frames]
strip=Image.new('RGB',(960,600*len(thumbs)))
for i,im in enumerate(thumbs):strip.paste(im,(0,600*i))
palette=strip.quantize(colors=256)
gif=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in thumbs]
gif[0].save(OUT/'Appearance_Flow_Preview.gif',save_all=True,append_images=gif[1:],duration=125,loop=0,optimize=False)
result={'roi':box,'before_mean_rgb':b.mean(axis=(0,1)).tolist(),'after_mean_rgb':a.mean(axis=(0,1)).tolist(),
        'mean_abs_rgb_change':float(np.abs(a-b).mean()),'changed_over_20_pct':float((np.abs(a-b).max(axis=2)>20).mean()*100),
        'motion_adjacent_frames':motion,'preview_seconds':2,'preview_fps':8,
        'limitations':'Material clock sampled in the editor; not a frame-rate or vehicle-physics test. Reflections can vary between captures; pixel change is not an opacity or quality measurement. Loop resets at the end.'}
(OUT/'appearance-pixel-review.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='motion_adjacent_frames'},indent=2))
print('Motion mean adjacent RGB difference:',float(np.mean([r['mean_abs_rgb'] for r in motion])))
