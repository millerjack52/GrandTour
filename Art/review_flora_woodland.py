"""Arrange ungraded Unreal captures beside source references; no visual pass inference."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageOps
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Woodland')

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
    views=('drive','bank','canopy','crowns','valley')
    panel([(label,O/f'candidate_{case}_{view}.png') for view in views for case,label in [('baseline','Before / '+view),('final','Woodland candidate / '+view)]],'before-after.jpg')
    panel([(case,O/f'candidate_{case}_bank.png') for case in ('baseline','materials','coverage','lighting','final','reverse_light')],'stages-bank.jpg')
    panel([(case,O/f'candidate_{case}_drive.png') for case in ('baseline','materials','coverage','lighting','final','reverse_light')],'stages-road.jpg')
    small=Image.new('RGB',(640,len(views)*204),(27,29,31));draw=ImageDraw.Draw(small)
    colour=small.copy();colour_draw=ImageDraw.Draw(colour)
    for row,view in enumerate(views):
        for col,case in enumerate(('baseline','final')):
            im=Image.open(O/f'candidate_{case}_{view}.png').convert('RGB');im.thumbnail((320,172))
            draw.text((col*320+8,row*204+8),case+' / '+view,fill='white')
            colour_draw.text((col*320+8,row*204+8),case+' / '+view,fill='white')
            colour.paste(im,(col*320,row*204+30))
            small.paste(ImageOps.grayscale(im),(col*320,row*204+30))
    small.save(O/'greyscale-thumbnails.jpg')
    colour.save(O/'colour-thumbnails.jpg')
    crops=[('Near crown','valley',(690,170,1090,570)),
           ('Middle crown','valley',(10,85,410,485)),
           ('Open-road crown','drive',(340,20,580,260)),
           ('Lit fern and shrub','bank',(35,305,435,555)),
           ('Shaded fern and shrub','canopy',(40,420,440,670)),
           ('Lit bark and rock','bank',(275,75,575,375)),
           ('Shaded bark and rock','reverse_light_bank',(275,75,575,375))]
    crop_items=[]
    for index,(label,view,box) in enumerate(crops):
        src='candidate_'+view+'.png' if view.startswith('reverse_light') else 'candidate_final_'+view+'.png'
        im=Image.open(O/src).convert('RGB').crop(box)
        for grey in (False,True):
            name=f'crop_{index}_{"grey" if grey else "colour"}.png'
            (ImageOps.grayscale(im) if grey else im).save(O/name)
            crop_items.append((label+(' / grey' if grey else ''),O/name))
    panel(crop_items,'semantic-crops.jpg',width=400)
    refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
    panel([('Daylight palette reference',Path(refs['woodland'])),('Actual Unreal / bank',O/'candidate_final_bank.png'),('Selective lighting reference',Path(refs['path'])),('Actual Unreal / canopy',O/'candidate_final_canopy.png'),('Warm/cool reference',Path(refs['sunlit'])),('Actual Unreal / road',O/'candidate_final_drive.png')],'reference-comparison.jpg')
    frames=[]
    for p in sorted(O.glob('candidate_final_motion_*.png')):
        im=Image.open(p).convert('RGB');im.thumbnail((960,540));frames.append(im)
    assert len(frames)==8
    panel([(p.stem,O/p.name) for p in sorted(O.glob('candidate_final_motion_*.png'))],'motion-contact-sheet.jpg',width=480)
    frames[0].save(O/'motion-samples.gif',save_all=True,append_images=frames[1:],duration=180,loop=0)
    print('Created ungraded colour/reference comparisons, grey thumbnails and sampled motion.')

if __name__=='__main__':main()
