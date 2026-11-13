"""Sample same-camera engine renders; pixel changes are not quality acceptance."""
import json
from pathlib import Path
import sample_benmore_gaea_creek as sample
ROOT=Path(__file__).resolve().parents[2]
sample.OUT=ROOT/'Art/Export/BenmoreGaea/ShoreRefinement'
sample.COURSE_REVISION=True
sample.VIEWS=['Bars','Bars_Bare','BarGround','BarGround_Bare','Lower','Lower_Bare','FullCourse','Reach','Ford']
sample.ROIS.update({name:(0,0,1440,900) for name in sample.VIEWS})
sample.ROIS.update(BarGround=(0,360,1440,900),BarGround_Bare=(0,360,1440,900),Ford=(0,400,1440,900))
if __name__=='__main__':
    sample.main()
    from PIL import Image,ImageDraw
    for name in ['Bars','BarGround','Ford']:
        canvas=Image.new('RGB',(1440,468),'#171b1e');draw=ImageDraw.Draw(canvas)
        for col,phase in enumerate(['Before','After']):
            canvas.paste(Image.open(sample.OUT/(name+'_'+phase+'.png')).resize((720,450)),(col*720,18))
            draw.text((col*720+10,3),phase,fill='white')
        canvas.save(sample.OUT/(name+'_Comparison.png'))
