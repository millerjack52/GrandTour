from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,shutil
out=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-exterior-v04')
bg=(244,243,238);ink=(34,43,49)
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/arial'+('bd' if b else '')+'.ttf',n)
def text(im,p,s,n=22,b=False):ImageDraw.Draw(im).text(p,s,font=font(n,b),fill=ink)
ppm=1400/5.05;front_x=700+(-1.35-.04)*ppm;rear_x=700+(1.35-.04)*ppm;hub_y=325+(.94-.369)*ppm
scale=(rear_x-front_x)/561
ref=Image.open('C:/GrandTour/Art/References/Vehicles/Pathfinder2002/01-crafted-utility-overall.png').convert('RGB').crop((0,595,1024,966))
ref=ref.resize((round(ref.width*scale),round(ref.height*scale)),Image.Resampling.LANCZOS)
upper=Image.new('RGB',(1400,650),bg);upper.paste(ref,(round(front_x-208*scale),round(hub_y-(891-595)*scale)))
lower=Image.open(out/'side.png').convert('RGB')
board=Image.new('RGB',(1480,1550),bg)
text(board,(40,24),'PATHFINDER / EXTERIOR PASS',32,True)
text(board,(40,73),'Fixed wheelbase alignment. Reference perspective is retained.',21)
text(board,(40,119),'APPROVED ARTISTIC TARGET',23,True);board.paste(upper,(40,158))
text(board,(40,817),'CURRENT BLENDER MODEL',23,True);board.paste(lower,(40,856))
text(board,(40,1514),'Wheels and cabin are still proxies. Static exterior review only.',20)
board.save(out/'style-check.jpg',quality=96)
for name in ['pathfinder-exterior-v01','pathfinder-exterior-v02']:
    src=out.parent/name/'saved-assembly-checks.json'
    shutil.copy2(src,out/(name+'-regression.json'))
checks=json.loads((out/'saved-assembly-checks.json').read_text())
assert checks['passed']
print(json.dumps({'passed':checks['passed'],'floor':checks['floor_coverage'],'sill_closure':checks['floor_sill_closure'],'optics':checks['optical_openings'],'style_comparison':str(out/'style-check.jpg')},indent=2))
