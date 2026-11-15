"""Arrange ungraded Unreal captures beside source references; no visual pass inference."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageOps
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/LazyFern')

def panel(items, file, width=640):
    rows=[]
    for label,p in items:
        im=Image.open(p).convert('RGB');im.thumbnail((width,420))
        row=Image.new('RGB',(width,im.height+32),(27,29,31));row.paste(im,((width-im.width)//2,32))
        ImageDraw.Draw(row).text((10,10),label,fill='white');rows.append(row)
    result=Image.new('RGB',(width*2,sum(max(r.height,rows[i+1].height if i+1<len(rows) else 0) for i,r in enumerate(rows) if i%2==0)),(27,29,31))
    y=0
    for i in range(0,len(rows),2):
        result.paste(rows[i],(0,y))
        if i+1<len(rows):result.paste(rows[i+1],(width,y))
        y+=max(r.height for r in rows[i:i+2])
    result.save(O/file)

def main():
    data=json.loads((O/'candidate-report.json').read_text());assert data['ok']
    panel([(label,O/f'candidate_{case}_{view}.png') for view in ('fern','verge','drive') for case,label in [('baseline','Previous fern / '+view),('lazy_fern','Lazy Forest Fern_02 / '+view)]],'before-after.jpg')
    small=Image.new('RGB',(640,3*204),(27,29,31));draw=ImageDraw.Draw(small)
    for row,view in enumerate(('fern','verge','drive')):
        for col,case in enumerate(('baseline','lazy_fern')):
            im=Image.open(O/f'candidate_{case}_{view}.png').convert('RGB');im.thumbnail((320,172))
            draw.text((col*320+8,row*204+8),case+' / '+view,fill='white')
            small.paste(ImageOps.grayscale(im),(col*320,row*204+30))
    small.save(O/'greyscale-thumbnails.jpg')
    refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
    preview=Path('D:/GrandTourAssets/FlippedNormals/Lazy_Forest_Gen_Addon/Assets/Assets_img/Fern_02.png')
    panel([('Owned model: supplied source preview',preview),('Actual Unreal: Lazy Forest Fern_02',O/'candidate_lazy_fern_fern.png'),('Daylight palette reference',Path(refs['woodland'])),('Actual Unreal: mixed bank',O/'candidate_lazy_fern_verge.png'),('Selective lighting reference',Path(refs['path'])),('Actual Unreal: road',O/'candidate_lazy_fern_drive.png')],'reference-comparison.jpg')
    frames=[]
    for p in sorted(O.glob('candidate_lazy_fern_motion_*.png')):
        im=Image.open(p).convert('RGB');im.thumbnail((960,540));frames.append(im)
    assert len(frames)==8
    frames[0].save(O/'motion-samples.gif',save_all=True,append_images=frames[1:],duration=180,loop=0)
    print('Created comparison panels and eight-frame motion sample sequence.')

if __name__=='__main__':main()
