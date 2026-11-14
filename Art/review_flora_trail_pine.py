"""Build ungraded pine trial evidence from actual rendered files."""
import json
from pathlib import Path
from PIL import Image
import review_flora_trail_palette as review
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/PineTrial';B=R/'Art/Export/FloraTrail/PaletteCandidate'
def main():
 report=json.loads((O/'verify-report.json').read_text());assert report['ok']
 for stage in ('export','install','verify'):
  assert json.loads((O/(stage+'-process.json')).read_text(encoding='utf-8-sig'))['exit_code']==0
 review.O=O
 refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
 for view in ('road','canopy','bank','valley'):
  review.board([('Before / saved FloraTrail daylight',B/('baseline_'+view+'.png')),('After / F002 pine trial, same camera and light',O/('pine_'+view+'.png'))],O/('compare_'+view+'.jpg'),'FLORA TRAIL / fuller pine trial','Original map preserved. New tree family only; no lighting, fog or grade change.',columns=2)
 review.board([('Reference / green woodland',refs['woodland']),('Reference / forest path',refs['path']),('Reference / open conifers',refs['sunlit']),('Unreal / pine road',O/'pine_road.png'),('Unreal / pine under-canopy',O/'pine_canopy.png'),('Unreal / mixed bank',O/'pine_bank.png')],O/'pine-reference-review.jpg','FLORA TRAIL / pine trial vs palette references','Actual Unreal backbuffer captures. A species trial, not a reference-match claim.')
 review.board([('Source F002 / Blender 3.4.1, AO off',O/'source_ao_off.png'),('Source F002 / Blender 3.4.1, AO on',O/'source_ao_on.png'),('Actual Unreal / isolated F002, LOD0',O/'pine_isolated.png')],O/'source-unreal-review.jpg','F002 / source and engine appearance','Same position/target and sun/sky; slight projection mismatch remains. NOT pixel-parity proof.')
 frames=[]
 for path in sorted(O.glob('motion_*.png')):
  im=Image.open(path).convert('RGB');im.thumbnail((960,540));frames.append(im)
 if frames:frames[0].save(O/'pine-motion.webp',save_all=True,append_images=frames[1:],duration=160,loop=0,quality=90)
 print(O/'pine-reference-review.jpg')
if __name__=='__main__':main()
