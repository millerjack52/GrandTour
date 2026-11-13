from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
out=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-bonnet-wheels-v05')
src=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-exterior-v04')
canvas=Image.new('RGB',(1400,1070),(237,235,231));d=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26)
for j,(p,title) in enumerate([(src,'BEFORE — exterior v04'),(out,'REVISED BONNET + WHEELS')]):
    img=Image.open(p/'front-module.png').convert('RGB');img.thumbnail((700,1000));canvas.paste(img,(700*j,55));d.text((700*j+24,18),title,fill=(35,35,35),font=font)
# Equal-size native renders; no deformation or generated geometry.
canvas=canvas.crop((0,0,1400,560));canvas.save(out/'bonnet-before-after.jpg',quality=94)
