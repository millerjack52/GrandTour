"""Read-only reference contact sheet and sampled display-colour evidence.

This is an analysis figure, not a paint-over or a material-colour prescription.
"""
from pathlib import Path
import json,textwrap
from PIL import Image,ImageDraw,ImageFont,ImageStat
R=Path('C:/GrandTour');O=R/'Art/Export/FloraPaletteStudy';O.mkdir(parents=True,exist_ok=True)
A=Path('C:/Users/mille/.codex/codex-remote-attachments/01a1ad67-e69b-7563-84c8-f0c7f1c15827/0366285E-CE89-4C0E-BADB-6DF93AB1F2DC')
refs={'woodland':A/'3-Photo-3.jpg','path':Path('C:/Users/mille/AppData/Local/Temp/codex-clipboard-87d6a348-848f-4c11-b06e-4b10d67ba70c.png'),'sunlit':Path('C:/Users/mille/AppData/Local/Temp/codex-clipboard-92317881-d93e-40b5-901e-6836452ec84c.png'),'fantasy':A/'1-Photo-1.jpg','blue_fog':A/'2-Photo-2.jpg','current':R/'Art/Export/FloraTrail/Sunlight/game_saved_road.png'}
ims={k:Image.open(p).convert('RGB') for k,p in refs.items()}
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
bg='#101E22';ink='#E7ECE8';muted='#B9C8C6';accent='#E4BE7D'
canvas=Image.new('RGB',(1800,1250),bg);d=ImageDraw.Draw(canvas)
def text(x,y,s,size=24,fill=ink,width=None):
 lines=textwrap.wrap(s,width) if width else [s]
 for line in lines:d.text((x,y),line,font=font(size),fill=fill);y+=int(size*1.35)
 return y
def fit(im,x,y,w,h):
 ratio=min(w/im.width,h/im.height);im=im.resize((round(im.width*ratio),round(im.height*ratio)),Image.Resampling.LANCZOS);canvas.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2))
text(24,16,'FLORA PAINT / what the references actually ask of the palette',34)
text(24,65,'User-supplied references. Analysis of the finished images; no assumptions about their original rendering setup.',22,muted)
cards=[('woodland','1  PRIMARY PALETTE / green woodland','Olive and moss greens; warm cream tips; dark green shadows; coral litter and plants.'),('path','2  LIGHT STRUCTURE / forest path','Small, strong pools of gold light. Cool shade keeps colour and readable plant silhouettes.'),('sunlit','3  SUNLIGHT BALANCE / open forest','Gold-facing branches against blue-green interiors. Brightness is selective, not uniform.')]
for i,(key,title,caption) in enumerate(cards):
 x=24+i*592;text(x,110,title,23,accent);fit(ims[key],x,151,568,284);text(x,450,caption,22,ink,43)
text(24,565,'CURRENT UNREAL / why stronger sunlight alone is insufficient',28)
fit(ims['current'],24,613,1000,535)
text(1050,615,'Observed gaps',27,accent)
for y,s in [(660,'Crowns share a broad yellow-olive fill; individual lit and shaded masses are weak.'),(775,'Ground foliage stays largely dark green. The reference repeats warm and cool colour families at several heights.'),(890,'Brown bark and grey rocks read as separate materials, rather than sharing the surrounding light colours.')]:text(1050,y,s,24,ink,49)
text(1050,1030,'Target: selective warmth, coloured shade, and related materials.',25,accent,44)
text(24,1180,'Different scenes and cameras: compare colour relationships and light structure, not overall histograms or pixel equality.',22,muted)
canvas.save(O/'reference-reading.jpg',quality=95)

# Small patches deliberately selected by material/light role, not a whole-image palette histogram.
samples=[('Sunlit foliage',(340,405,360,425)),('Shaded foliage',(132,430,150,450)),('Warm bark',(920,195,936,217)),('Coral accent',(1025,396,1045,416)),('Cool distance',(250,200,270,216)),('Deep foreground',(738,451,758,471))]
data=[]
canvas=Image.new('RGB',(1500,1040),bg);d=ImageDraw.Draw(canvas)
text(24,16,'COLOUR ROLES / sampled from the green woodland reference',30)
text(24,62,'JPEG display colours, not Unreal Base Color values or universal lighting targets.',22,muted)
fit(ims['woodland'],24,110,1452,612)
# Mark the source rectangles in the displayed image (image is 1200x506; fit width 1452).
scale=1452/1200;offset_y=110+(612-int(506*scale))//2
for i,(label,box) in enumerate(samples):
 rgb=tuple(int(v) for v in ImageStat.Stat(ims['woodland'].crop(box)).median)
 data.append({'role':label,'source':'woodland','pixel_box':box,'display_rgb_median':rgb,'hex':'#'+''.join(f'{v:02X}' for v in rgb)})
 x1,y1,x2,y2=box;cx=24+(x1+x2)/2*scale;cy=offset_y+(y1+y2)/2*scale
 d.ellipse((cx-15,cy-15,cx+15,cy+15),fill=bg,outline=ink,width=2);d.text((cx-7,cy-14),str(i+1),font=font(20),fill=ink)
 x=24+i*246;d.rectangle((x,750,x+220,822),fill=rgb)
 text(x,835,f'{i+1}  {label}',20);text(x,866,data[-1]['hex'],20,muted)
text(24,930,'These samples describe relationships: bright foliage remains yellow-green; accents are earthy coral; distance cools.',21,muted)
text(24,966,'Each patch contains local shading and texture. Use the reference crops as the acceptance target, not the hex codes.',21,muted)
canvas.save(O/'colour-roles.jpg',quality=95)
(O/'reference-evidence.json').write_text(json.dumps({'sources':{k:str(p) for k,p in refs.items()},'samples':data,'limits':['Finished compressed images only; original exposure, light energy, grading and renderer cannot be recovered uniquely.','Different framing and content prevent useful whole-image histogram equality.','Colours above are display RGB and must not be pasted into linear material inputs.']},indent=2)+'\n')
print(json.dumps(data,indent=2))
