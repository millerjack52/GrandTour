"""Compare actual Unreal screenshots; separate pixels from geometry evidence."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parents[2]/'Art/Export/BenmoreGaea/ChannelShape'
VIEWS=['Plan','Plan_Bare','Reach','Bed_Bare','Ford']
ROIS={'Plan':(200,40,1240,850),'Plan_Bare':(200,40,1240,850),'Reach':(380,350,1000,700),'Bed_Bare':(0,420,1000,850),'Ford':(0,500,900,900)}

def main():
    report={};canvas=Image.new('RGB',(1440,468*len(VIEWS)),'#171b1e');draw=ImageDraw.Draw(canvas)
    for row,view in enumerate(VIEWS):
        pair=[];report[view]={}
        for col,phase in enumerate(['Before','After']):
            im=Image.open(OUT/(view+'_'+phase+'.png')).convert('RGB');assert im.size==(1440,900)
            values=np.asarray(im.crop(ROIS[view]),dtype=float)/255;luma=values @ np.array([.2126,.7152,.0722]);pair.append(values)
            report[view][phase]=dict(roi_xyxy=ROIS[view],mean_rgb=values.mean((0,1)).tolist(),luma_std=float(luma.std()),horizontal_pixel_difference_mean=float(abs(np.diff(luma,axis=1)).mean()))
            canvas.paste(im.resize((720,450)),(col*720,row*468+18));draw.text((col*720+10,row*468+3),view+' — '+phase,fill='white')
        delta=abs(pair[1]-pair[0]);report[view]['mean_absolute_rgb_change']=float(delta.mean());report[view]['pixels_over_20_of_255_fraction']=float(np.mean(delta.max(-1)>20/255))
    report['limits']='Same cameras and water clock. Pixel differences are still-image evidence; no animation, driving or FPS claim. Scalloping is separately measured from the native heightfield.'
    (OUT/'pixel-report.json').write_text(json.dumps(report,indent=2));canvas.save(OUT/'Channel_Shape_Comparison.png')
    top=Image.new('RGB',(1440,468),'#171b1e');draw=ImageDraw.Draw(top)
    for col,phase in enumerate(['Before','After']):
        im=Image.open(OUT/('Plan_'+phase+'.png'));top.paste(im.resize((720,450)),(col*720,18));draw.text((col*720+10,3),phase,fill='white')
    top.save(OUT/'Bank_Shape_Comparison.png');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
