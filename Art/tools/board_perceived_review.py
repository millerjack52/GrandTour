"""Lay out unretouched game captures and clearly labelled references."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review/PerceivedDetail'
def make():
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
 titlefont=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',30)
 board=Image.new('RGB',(1800,878),'#12221b');draw=ImageDraw.Draw(board)
 draw.text((22,14),'ACTUAL GAME COMPARISON  |  Bounded detail test',font=titlefont,fill='#f2f5eb')
 rows=[('before-T01.png','Forest - before'),('after-T01.png','Forest - after'),('original-landscape-crop.png','Original style reference'),('before-B01.png','Bank - before'),('after-B01.png','Bank - after'),('site-bank.jpg','User site photograph')]
 for i,(filename,label) in enumerate(rows):
  x=(i%3)*600;y=68+(i//3)*388
  draw.text((x+14,y),label,font=font,fill='#e9f0e4')
  im=ImageOps.contain(Image.open(OUT/filename).convert('RGB'),(592,333),Image.Resampling.LANCZOS)
  board.paste(im,(x+(600-im.width)//2,y+34+(333-im.height)//2))
 draw.text((22,846),'Same cameras and lighting. Reference images are not game renders. Full-size comparisons and motion are in the review.',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18),fill='#b8c8bb')
 board.save(OUT/'comparison-board.jpg',quality=95)
 print(OUT/'comparison-board.jpg')
if __name__=='__main__':make()
