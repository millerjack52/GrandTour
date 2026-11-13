from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
O=Path('C:/GrandTour/Art/Export/FloraDrive/RockMaster');O.mkdir(parents=True,exist_ok=True)
P=Path('D:/GrandTourAssets/FlippedNormals/Rock Master Tools/IMG/All/Model_Rock')
files=[]
for category in ['003_Asset_Large_Rock','002_Asset_Medium_Rock']:
    rows=sorted((P/category).glob('*.png'));files+=rows[::max(1,len(rows)//24)][:24]
canvas=Image.new('RGB',(1440,8*210),'#202524');d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
for i,f in enumerate(files):
    x=i%6*240;y=i//6*210;im=ImageOps.contain(Image.open(f).convert('RGB'),(230,180));canvas.paste(im,(x,y));d.text((x+4,y+184),f.stem,font=font,fill='white')
canvas.save(O/'source-contact-sheet.jpg',quality=92)
