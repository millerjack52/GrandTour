"""Lay out untouched native Blender renders at equal image scale for review."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',28);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
board=Image.new('RGB',(1800,1500),(238,237,232));d=ImageDraw.Draw(board)
for col,(key,title,note) in enumerate([('OLD','CURRENT PROTOTYPE','Existing body and detailed components'),('A','A  /  COMPACT FOUR-DOOR','Taller body, larger tyres, tighter overhangs'),('B','B  /  SHORT EXPEDITION','Shorter wheelbase and more upright stance')]):
    x=col*600;d.text((x+20,18),title,font=font,fill=(30,38,37));d.text((x+20,54),note,font=small,fill=(70,76,74))
    for row,view in enumerate(['quarter','side','front']):
        im=Image.open(out/(key+'-'+view+'-clay.png')).convert('RGB');im.thumbnail((600,450),Image.Resampling.LANCZOS);board.paste(im,(x,90+row*460))
d.text((20,1470),'Same cameras, scale and clay material within each row. A and B are unapproved shape studies, not refitted final vehicles.',font=small,fill=(40,48,46))
board.save(out/'shape-comparison.png')
