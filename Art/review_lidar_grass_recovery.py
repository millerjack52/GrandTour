"""Arrange native gameplay captures without changing their colour or detail."""
from pathlib import Path
import json,re
from PIL import Image,ImageDraw,ImageFont
O=Path('C:/GrandTour/Art/Export/LidarGrassRecovery')
r=json.loads((O/'compare-report.json').read_text());p=json.loads((O/'compare-process.json').read_text(encoding='utf-8-sig'))
assert r['ok'] and p['exit_code']==0
assert not re.search(r'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error',(O/'compare.log').read_text(errors='replace'))
installed=json.loads((O/'install-report.json').read_text());process=json.loads((O/'install-process.json').read_text(encoding='utf-8-sig'))
assert installed['ok'] and process['exit_code']==0
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
stages=[('current','Before / 1274 x 682'),('fine_original','Original fine grass palette / 1600 x 868'),('verify','Saved fine grass + v2 palette / 1274 x 682')]
for view in ('paddock_low','paddock_wide','bank'):
 board=Image.new('RGB',(1920,368),(23,25,27));draw=ImageDraw.Draw(board)
 for col,(stage,label) in enumerate(stages):
  with Image.open(O/(stage+'_'+view+'.png')) as im:
   im=im.convert('RGB');assert im.size==((1600,868) if stage=='fine_original' else (1274,682));im.thumbnail((640,343));board.paste(im,(640*col,25))
  draw.text((640*col+8,3),label,font=font,fill='white')
 board.save(O/(view+'-three-way.jpg'),quality=96)
 pair=Image.new('RGB',(1280,368),(23,25,27));pair.paste(board.crop((0,0,640,368)),(0,0));pair.paste(board.crop((1280,0,1920,368)),(640,0));pair.save(O/(view+'-comparison.jpg'),quality=96)
 board.convert('L').resize((960,184),Image.Resampling.LANCZOS).save(O/(view+'-greyscale.jpg'),quality=95)
print('Matched before/saved pairs written at native 1274x682; three-way diagnosis labels the intermediate resolution difference. Source PNGs unchanged.')
