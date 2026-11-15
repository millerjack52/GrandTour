"""Unmodified Unreal crown comparisons, thumbnail values and sampled motion."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageOps
import review_flora_woodland as review
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/CrownForm')
def main():
    assert json.loads((O/'candidate-report.json').read_text())['ok']
    review.O=O
    views=('drive','bank','canopy','crowns','valley')
    review.panel([(label+' / '+view,O/f'candidate_{case}_{view}.png') for view in views for case,label in [('baseline','Before'),('final','Crown candidate')]],'before-after.jpg')
    review.panel([(label+' / '+view,O/f'candidate_{case}_{view}.png') for view in ('drive','valley') for case,label in [('baseline','Before'),('final','Updated crown shading')]],'crown-comparison.jpg')
    for view in ('drive','crowns','valley'):
        review.panel([(case,O/f'candidate_{case}_{view}.png') for case in ('baseline','mesh','volume','card','coverage','occlusion','normals','final','reverse')],f'diagnosis-{view}.jpg')
    for grey in (False,True):
        out=Image.new('RGB',(640,204*len(views)),(27,29,31));draw=ImageDraw.Draw(out)
        for row,view in enumerate(views):
            for col,case in enumerate(('baseline','final')):
                im=Image.open(O/f'candidate_{case}_{view}.png').convert('RGB');im.thumbnail((320,172))
                draw.text((col*320+8,row*204+8),case+' / '+view,fill='white')
                out.paste(ImageOps.grayscale(im) if grey else im,(col*320,row*204+30))
        out.save(O/('greyscale-thumbnails.jpg' if grey else 'colour-thumbnails.jpg'))
    refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
    crops=[('Near crown','valley',(690,170,1090,570)),('Middle conifer','valley',(10,85,410,485)),('Road-edge crown','drive',(340,20,580,260))]
    items=[]
    for i,(label,view,box) in enumerate(crops):
        for grey in (False,True):
            for case in ('baseline','final'):
                im=Image.open(O/f'candidate_{case}_{view}.png').convert('RGB').crop(box)
                path=O/f'crop_{i}_{case}_{"grey" if grey else "colour"}.png'
                (ImageOps.grayscale(im) if grey else im).save(path)
                items.append((label+' / '+case+(' / grey' if grey else ''),path))
    review.panel(items,'crown-crops.jpg',400)
    review.panel([('Daylight reference',Path(refs['woodland'])),('Actual Unreal / canopy',O/'candidate_final_canopy.png'),('Directional-light reference',Path(refs['sunlit'])),('Actual Unreal / overview',O/'candidate_final_valley.png')],'reference-comparison.jpg')
    frames=[]
    for p in sorted(O.glob('candidate_final_motion_*.png')):
        im=Image.open(p).convert('RGB');im.thumbnail((960,540));frames.append(im)
    assert len(frames)==8
    frames[0].save(O/'motion-samples.gif',save_all=True,append_images=frames[1:],duration=180,loop=0)
    review.panel([(p.stem,p) for p in sorted(O.glob('candidate_final_motion_*.png'))],'motion-contact-sheet.jpg',480)
if __name__=='__main__':main()
