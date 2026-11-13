"""Measure matched Unreal stills; report pixels, never infer physical behaviour."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw

OUT=Path(__file__).resolve().parents[2]/'Art/Export/BenmoreGaea/ChannelPilot'
ROIS={'Ford':(0,500,900,900),'Bed':(0,420,1000,850),'Bed_Bare':(0,420,1000,850),'Reach':(380,350,1000,700)}
def main():
    report={};canvas=Image.new('RGB',(1440,len(ROIS)*468),'#171b1e');draw=ImageDraw.Draw(canvas)
    for row,(view,box) in enumerate(ROIS.items()):
        report[view]={}
        for col,phase in enumerate(['Before','After']):
            im=Image.open(OUT/(view+'_'+phase+'.png')).convert('RGB')
            assert im.size==(1440,900)
            values=np.asarray(im.crop(box),dtype=float)/255
            luma=values @ np.array([.2126,.7152,.0722])
            report[view][phase]={'roi_xyxy':box,'mean_rgb':values.mean((0,1)).tolist(),'mean_luma':float(luma.mean()),'luma_std':float(luma.std()),'horizontal_pixel_difference_mean':float(np.abs(np.diff(luma,axis=1)).mean())}
            canvas.paste(im.resize((720,450)),(col*720,row*468+18))
            draw.text((col*720+10,row*468+3),view+' — '+phase,fill='white')
    report['limits']='Same cameras and water time; pixel statistics describe these stills only. No motion, driving or frame-rate inference.'
    (OUT/'pixel-report.json').write_text(json.dumps(report,indent=2));canvas.save(OUT/'Channel_Comparison.png')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
