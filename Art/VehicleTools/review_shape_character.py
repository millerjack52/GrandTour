"""Evidence diagrams and comparisons from source pixels and native Blender renders."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops

OUT=Path(sys.argv[1]);S=json.loads((OUT/'shape-spec.json').read_text())
PAPER=(242,243,239);INK=(32,45,45);MUTED=(78,91,91);CYAN=(0,147,170);GOLD=(222,126,15)
def font(n):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
def text(d,xy,s,n=25,c=INK):d.text(xy,s,font=font(n),fill=c)
def marker(d,xy,n):
    x,y=xy;d.ellipse((x-16,y-16,x+16,y+16),fill=CYAN,outline='white',width=2);d.text((x,y-1),str(n),font=font(21),fill='white',anchor='mm')

# Annotated observations use original source pixels, never a generated retelling.
sheet=Image.new('RGB',(1080,1210),PAPER);d=ImageDraw.Draw(sheet)
text(d,(32,24),'CRAFTED UTILITY / SHAPE MAP',34)
text(d,(32,75),'Original A: the main artistic target',24,MUTED)
im=Image.open(OUT/'original-a-reference.png').convert('RGB').resize((1026,700),Image.Resampling.LANCZOS);sheet.paste(im,(27,112));d=ImageDraw.Draw(sheet)
marks=[(1,(89,145)),(2,(225,143)),(3,(325,27)),(4,(353,78)),(5,(399,164)),(6,(382,235))]
for n,(u,v) in marks:marker(d,(27+u*2,112+v*2),n)
labels=[('1  Short nose turns downward','2  Folded bonnet shoulders'),('3  Shallow roof crown + thin gutter','4  Cabin narrows toward the roof'),('5  Shoulder turns out below glass','6  Lower side tucks underneath')]
for i,(a,b) in enumerate(labels):text(d,(32,850+i*65),a,25);text(d,(552,850+i*65),b,25)
text(d,(32,1080),'These are shape observations. Widths and hidden surfaces remain provisional.',23,MUTED)
text(d,(32,1124),'Each item has a geometry control and a named review view in shape-map.json.',23,MUTED)
sheet.save(OUT/'shape-map-front.png')

sheet=Image.new('RGB',(1080,1180),PAPER);d=ImageDraw.Draw(sheet)
text(d,(32,24),'REAR CHARACTER / THE CHANGE OF ANGLE',32)
text(d,(32,73),'User correction + secondary side evidence; exact amounts are provisional.',23,MUTED)
im=Image.open(OUT/'side-reference.png').convert('RGB').resize((1008,480),Image.Resampling.LANCZOS);sheet.paste(im,(36,126));d=ImageDraw.Draw(sheet)
for key,color in [('rear_profile_uv',GOLD),('rear_bumper_uv',CYAN)]:
    points=[(36+u*1.2,126+v*1.2) for u,v in S[key]]
    if key=='rear_profile_uv':
        d.line(points[:4],fill=color,width=4)
        for a,b in zip(points[3:],points[4:]):
            length=((b[0]-a[0])**2+(b[1]-a[1])**2)**.5
            for distance in range(0,int(length),12):
                t=distance/length;q=min(1,(distance+6)/length)
                d.line([(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t),(a[0]+(b[0]-a[0])*q,a[1]+(b[1]-a[1])*q)],fill=color,width=4)
    else:d.line(points,fill=color,width=4)
marker(d,(36+785*1.2,126+87*1.2),1);marker(d,(36+790*1.2,126+214*1.2),2);marker(d,(36+818*1.2,126+248*1.2),3)
text(d,(32,641),'1  Upper rear slopes outward toward the belt.',26)
text(d,(32,688),'2  Below the widest point, the body turns inward toward the underside.',26)
text(d,(32,735),'3  Bumper projects outward, then its lower edge returns inward.',26)
text(d,(32,804),'Gold: rear body profile; dashed = inferred behind bumper. Cyan: bumper.',23,MUTED)
text(d,(32,852),'This reversal of slope is a form feature, not an accessory detail.',26)
text(d,(32,922),'Also tracked: window-bay rhythm, narrow arch lips and opening shapes.',23,MUTED)
text(d,(32,980),'The side reference is generated and may disagree with Original A.',23,MUTED)
text(d,(32,1020),'Keep those disagreements visible; do not claim a measured blueprint.',23,MUTED)
sheet.save(OUT/'shape-map-rear.png')

ref=Image.open(OUT/'side-reference.png').convert('RGBA')
mask=Image.open(OUT/'side-mask.png').convert('RGBA').resize(ref.size,Image.Resampling.LANCZOS)
alpha=mask.getchannel('A');edge=ImageChops.subtract(alpha.filter(ImageFilter.MaxFilter(3)),alpha.filter(ImageFilter.MinFilter(3)))
layer=Image.new('RGBA',ref.size,(*CYAN,255));layer.putalpha(edge);overlay=Image.alpha_composite(ref,layer);d=ImageDraw.Draw(overlay)
for key in ['rear_profile_uv','bonnet_crown_uv','roof_crown_uv']:
    d.line([tuple(p) for p in S[key]],fill=(*GOLD,255),width=2)
overlay.save(OUT/'side-overlay.png')
sheet=Image.new('RGB',(1080,1210),PAPER);d=ImageDraw.Draw(sheet)
text(d,(32,22),'BODY STUDY / REGISTERED SIDE COMPARISON',31)
text(d,(32,72),'Cyan: actual 3D outline. Gold: selected observed profiles.',24,MUTED)
sheet.paste(overlay.convert('RGB').resize((1008,480),Image.Resampling.LANCZOS),(36,123))
text(d,(32,639),'Bare body, same camera and wheel anchors',28)
im=Image.open(OUT/'side.png').convert('RGB').resize((1008,480),Image.Resampling.LANCZOS);sheet.paste(im,(36,688))
sheet.save(OUT/'side-comparison.png')

sheet=Image.new('RGB',(1080,1760),PAPER);d=ImageDraw.Draw(sheet)
text(d,(32,22),'CRAFTED UTILITY / PRIMARY-FORM STUDY',32)
text(d,(32,74),'Actual Blender renders. Provisional shape; detail deliberately deferred.',23,MUTED)
for key,y in [('quarter',125),('rear-quarter',925)]:
    im=Image.open(OUT/(key+'.png')).convert('RGB').resize((1024,768),Image.Resampling.LANCZOS);sheet.paste(im,(28,y))
text(d,(32,1715),'Rear return, bonnet relief, roof crown and body sections are editable.',23,MUTED)
sheet.save(OUT/'volume-review.png')
print(OUT/'side-comparison.png')
