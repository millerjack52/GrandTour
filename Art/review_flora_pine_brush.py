"""Contact sheets of actual Unreal probes, with no painted-over output."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageOps
import review_flora_woodland as review
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/PineBrush')
CASES=('baseline','threshold45','threshold55','fixed45')
VIEWS=('drive','bank','canopy','crowns','valley','pine_close','pine_middle','pine_far')
def main():
    assert json.loads((O/'candidate-report.json').read_text())['ok']
    review.O=O
    for view in VIEWS:
        review.panel([(case+' / '+view,O/f'candidate_{case}_{view}.png') for case in CASES],f'comparison-{view}.jpg')
    labels={'baseline':'Current approved pine','threshold45':'Moderately opened brush gaps','threshold55':'Strongly opened brush gaps','fixed45':'Without view-angle fading'}
    review.panel([(labels[case],O/f'candidate_{case}_pine_close.png') for case in CASES],'pine-review.jpg')
    review.panel([(labels[case]+' / motion sample '+str(frame),O/f'candidate_{case}_motion_{frame:02d}.png') for frame in (0,18,42) for case in ('baseline','threshold45')],'motion-comparison.jpg')
    for grey in (False,True):
        sheet=Image.new('RGB',(1280,204*len(VIEWS)),(27,29,31));draw=ImageDraw.Draw(sheet)
        for row,view in enumerate(VIEWS):
            for col,case in enumerate(CASES):
                with Image.open(O/f'candidate_{case}_{view}.png') as source:im=source.convert('RGB')
                im.thumbnail((320,172));draw.text((col*320+8,row*204+8),case+' / '+view,fill='white')
                sheet.paste(ImageOps.grayscale(im) if grey else im,(col*320,row*204+30))
        sheet.save(O/('greyscale-thumbnails.jpg' if grey else 'colour-thumbnails.jpg'))
    refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
    for case in CASES:
        review.panel([('Woodland reference',Path(refs['woodland'])),('Unreal / '+case,O/f'candidate_{case}_canopy.png'),('Sunlit conifer reference',Path(refs['sunlit'])),('Unreal / '+case,O/f'candidate_{case}_pine_middle.png'),('Forest-path reference',Path(refs['path'])),('Unreal / '+case,O/f'candidate_{case}_drive.png')],f'references-{case}.jpg')
        frames=[]
        for p in sorted(O.glob(f'candidate_{case}_motion_*.png')):
            with Image.open(p) as source:im=source.convert('RGB')
            im.thumbnail((960,540));frames.append(im)
        assert len(frames)==8
        frames[0].save(O/f'motion-samples-{case}.gif',save_all=True,append_images=frames[1:],duration=180,loop=0)
if __name__=='__main__':main()
