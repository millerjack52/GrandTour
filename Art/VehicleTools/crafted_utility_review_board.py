"""Lay out unretouched native Blender renders beside the supplied concept reference."""
from pathlib import Path
import argparse
from PIL import Image,ImageDraw,ImageFont
p=argparse.ArgumentParser();p.add_argument('--folder',required=True);a=p.parse_args();out=Path(a.folder)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',28)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',21)
bg=(235,232,224)
board=Image.new('RGB',(1600,1710),bg);d=ImageDraw.Draw(board)
d.text((36,20),'CRAFTED UTILITY  |  Concept and native Blender comparison',font=font,fill=(33,39,32))
src=Image.open('C:/GrandTour/Art/References/Vehicles/BoardDerived_2026-09-30/01-crafted-utility-views.png').convert('RGB')
# Normalize wheelbase, preserving aspect ratio; source anchors are read from the
# supplied image. Blender anchor spacing follows its recorded orthographic camera.
items=[(src.crop((22,108,856,480)),880/506,138,115,'Selected reference - side profile'),
       (Image.open(out/'side.png').crop((45,290,1440,883)),880/(2.64/4.9*1500),(750+(-1.39-.12)/4.9*1500)-45,845,'Blender model - orthographic side')]
for im,scale,frontx,y,label in items:
    d.text((35,y-34),label,font=small,fill=(56,60,51));im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
    board.paste(im,(round(310-frontx*scale),y))
d.text((38,1530),'Views normalized to the same wheelbase; image proportions are preserved.',font=small,fill=(56,60,51))
d.text((38,1570),'Compare bonnet and roof profile, tyre scale, glazing rake and door divisions.',font=small,fill=(56,60,51))
d.text((38,1610),'Visual reference only. The static Blender interpretation awaits shape review.',font=small,fill=(56,60,51))
board.save(out/'reference-comparison.png')
board=Image.new('RGB',(1800,1510),bg);d=ImageDraw.Draw(board)
d.text((30,16),'CRAFTED UTILITY  |  Native Blender review',font=font,fill=(33,39,32))
for i,(name,label) in enumerate([('quarter','Front three-quarter'),('rear-quarter','Rear three-quarter'),('side','Side profile'),('front','Front'),('top','Top'),('quarter-clay','Clay - primary surfaces')]):
    x=20+(i%2)*900;y=85+(i//2)*470;im=Image.open(out/(name+'.png')).convert('RGB');im.thumbnail((870,430),Image.Resampling.LANCZOS)
    d.text((x,y-26),label,font=small,fill=(56,60,51));board.paste(im,(x+(870-im.width)//2,y))
board.save(out/'review-board.png')
print(out/'review-board.png')
