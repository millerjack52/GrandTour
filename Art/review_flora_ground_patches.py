"""Compare actual fixed-camera ground captures, without altering their appearance."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw,ImageOps
import review_flora_woodland as review
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/GroundPatches')
VIEWS=('drive','bank','floor','canopy','valley');CASES=('baseline','patches','strong')
def main(partial=False):
    report=json.loads((O/'candidate-report.json').read_text())
    if partial:assert (O/'candidate-stopped.json').exists() and not report['ok']
    else:assert report['ok']
    review.O=O
    review.panel([(label+' / '+view,O/f'candidate_{case}_{view}.png') for view in ('bank','floor','drive') for case,label in [('baseline','Current ground'),('patches','Larger moss and litter patches')]],'before-after.jpg')
    review.panel([(label+' / '+view,O/f'candidate_{case}_{view}.png') for view in ('bank','floor') for case,label in [('baseline','Before'),('patches','Ground candidate')]],'ground-review.jpg')
    if partial:
        refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
        review.panel([('Woodland reference',Path(refs['woodland'])),('Actual Unreal / verification pending',O/'candidate_patches_bank.png')],'reference-comparison.jpg')
        return
    review.panel([(case+' / '+view,O/f'candidate_{case}_{view}.png') for view in ('bank','floor') for case in CASES],'all-profiles.jpg')
    for grey in (False,True):
        sheet=Image.new('RGB',(960,204*len(VIEWS)),(27,29,31));draw=ImageDraw.Draw(sheet)
        for row,view in enumerate(VIEWS):
            for col,case in enumerate(CASES):
                with Image.open(O/f'candidate_{case}_{view}.png') as src:im=src.convert('RGB')
                im.thumbnail((320,172));draw.text((col*320+8,row*204+8),case+' / '+view,fill='white')
                sheet.paste(ImageOps.grayscale(im) if grey else im,(col*320,row*204+30))
        sheet.save(O/('greyscale-thumbnails.jpg' if grey else 'colour-thumbnails.jpg'))
    refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
    review.panel([('Woodland reference',Path(refs['woodland'])),('Actual Unreal ground candidate',O/'candidate_patches_bank.png')],'reference-comparison.jpg')
    for case in CASES:
        frames=[]
        for p in sorted(O.glob(f'candidate_{case}_motion_*.png')):
            with Image.open(p) as src:im=src.convert('RGB')
            im.thumbnail((960,540));frames.append(im)
        assert len(frames)==8
        frames[0].save(O/f'motion-{case}.gif',save_all=True,append_images=frames[1:],duration=180,loop=0)
    review.panel([(case+' / '+str(frame),O/f'candidate_{case}_motion_{frame:02d}.png') for frame in (0,18,42) for case in ('baseline','patches')],'motion-comparison.jpg')
if __name__=='__main__':main('--partial' in sys.argv)
