"""Unretouched Unreal shadow comparison: fixed camera, full view and detail crops."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw,ImageFont,ImageOps
O=Path('C:/GrandTour/Art/Export/FloraDrive')
sys.path.insert(0,'C:/GrandTour/Art/Unreal')
from flora_trial_evidence import audited_fingerprint
after=json.loads((O/'capture-report.json').read_text());before=json.loads((O/'BeforeGroundShadows/capture-report.json').read_text())
functional=json.loads((O/'functional-report.json').read_text());settings=json.loads((O/'shadows-report.json').read_text())
assert after['ok'] and before['ok'] and functional['ok'] and settings['ok']
assert after['trial_packages_sha256']==functional['trial_packages_sha256']==audited_fingerprint()
board=Image.new('RGB',(1800,1120),'#152322');d=ImageDraw.Draw(board)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
d.text((24,18),'GROUND FOLIAGE / actual Unreal shadow comparison',font=font(31),fill='#f0ead6')
d.text((24,65),'Fixed camera; unchanged planting, palette, sun intensity and exposure. Images are not retouched.',font=font(21),fill='#c2cfc4')
for x,label,file in [(24,'BEFORE / broadleaf casting disabled',O/'BeforeGroundShadows/09_ground_detail.png'),(912,'AFTER / cast shadows + short contact shadows',O/'09_ground_detail.png')]:
    d.text((x,108),label,font=font(23),fill='#e7d7a6');im=Image.open(file).convert('RGB')
    board.paste(ImageOps.contain(im,(864,463)),(x,147))
    d.text((x,635),'MATCHED DETAIL / plant bases and overlapping leaves',font=font(20),fill='#c2cfc4')
    crop=im.crop((250,365,1040,682));board.paste(ImageOps.contain(crop,(864,390)),(x,677))
board.save(O/'ground-shadows-comparison.jpg',quality=95)
timings=[]
for row in after['render_spot_checks']:
    prev=next(p for p in before['render_spot_checks'] if p['view']==row['view'])
    assert row['resolution']==prev['resolution']
    b=prev['metrics']['GPUTime']['median'];a=row['metrics']['GPUTime']['median']
    timings.append(dict(view=row['view'],resolution=row['resolution'],before_gpu_median_ms=b,after_gpu_median_ms=a,delta_ms=a-b,after_gpu_p95_ms=row['metrics']['GPUTime']['p95']))
report=dict(ok=True,trial_packages_sha256=after['trial_packages_sha256'],broadleaf_shadow_instances=settings['broadleaf_shadow_instances'],contact_length_cm=settings['settings']['contact_length_cm'],performance=timings,performance_scope='Paired stationary editor spot checks, 300 frames/view; run-to-run variation remains. Not packaged FPS or a whole-map budget.',driving_passed=True,limitations='Contact shadows are screen-space and cannot shadow off-screen blockers. Broadleaf plants have actual shadow-map casting; fine grasses use contact shadows. No baked black patches added to the ground.')
(O/'ground-shadows-review.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
