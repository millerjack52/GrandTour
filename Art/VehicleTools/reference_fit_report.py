"""Diagnostic layouts using reference pixels and native Blender projections."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
import json
out=Path('C:/GrandTour/Art/Export/VehicleTools/reference-fit-v01')
obs=json.loads((out/'reference-observations.json').read_text());errors=json.loads((out/'baseline-contour-errors.json').read_text())
cyan=(0,170,200,255);gold=(235,141,0,255)
def overlay(key):
    ref=Image.open(out/({'side':'side-reference.png','front':'front-reference.png','hero':'original-a-reference.png'}[key])).convert('RGBA')
    mask=Image.open(out/(key+'-baseline-mask.png')).convert('RGBA');alpha=mask.getchannel('A')
    edge=ImageChops.subtract(alpha.filter(ImageFilter.MaxFilter(3)),alpha.filter(ImageFilter.MinFilter(3)))
    layer=Image.new('RGBA',ref.size,cyan);layer.putalpha(edge);ref=Image.alpha_composite(ref,layer)
    if key=='side':
        d=ImageDraw.Draw(ref)
        for name in ['roof_crown','bonnet_silhouette','bonnet_shoulder','front_arch','rear_arch']:
            d.line([tuple(x) for x in obs['side']['traces'][name]],fill=gold,width=2)
        # The exact measured roof/bonnet section, also in cyan, makes errors visible
        # even where the whole-car silhouette crosses other geometry.
        for group in ['roof_crown','bonnet_silhouette']:
            pts=[(r['u'],r['model_v']) for r in errors[group]['samples'] if r['model_v'] is not None]
            d.line(pts,fill=cyan,width=2)
    ref.save(out/(key+'-overlay.png'));return ref
side=overlay('side');hero=overlay('hero');front=overlay('front')
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',30);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
board=Image.new('RGB',(1600,1480),(243,240,232));d=ImageDraw.Draw(board)
d.text((40,23),'WHERE THE SHAPE DEPARTS FROM THE REFERENCE',font=font,fill=(27,37,38))
d.text((40,73),'Cyan: actual Blender geometry     Gold: traced target     Wheel hubs registered at one uniform scale',font=small,fill=(47,62,65))
im=side.resize((1512,720),Image.Resampling.LANCZOS);board.paste(im.convert('RGB'),(44,118))
for x,rect,title,detail in [
    (44,(25,115,290,185),'BONNET: too high at the leading edge','Largest sampled error: 21.5 px; rear profile is slightly low.'),
    (830,(330,3,775,48),'ROOF: flat centre and abrupt ends','Centre about 5.7 px low; front corner about 9 px high.')]:
    d.text((x,875),title,font=small,fill=(27,37,38));im=side.crop(rect);ratio=min(710/im.width,210/im.height);im=im.resize((round(im.width*ratio),round(im.height*ratio)),Image.Resampling.LANCZOS)
    board.paste(im.convert('RGB'),(x,920));d.text((x,1155),detail,font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19),fill=(47,62,65))
d.text((44,1230),'These are local contour measurements, not a score for the whole car.',font=small,fill=(27,37,38))
d.text((44,1270),'Manual tracing uncertainty is about 3 px. Generated views can disagree.',font=small,fill=(47,62,65))
d.text((44,1310),'The original A three-quarter image remains the main visual target.',font=small,fill=(47,62,65))
d.text((44,1360),'Next: author the bonnet, roof and body sections; keep cameras fixed while comparing edits.',font=small,fill=(27,37,38))
board.save(out/'shape-diagnosis.png')
print(out/'shape-diagnosis.png')
