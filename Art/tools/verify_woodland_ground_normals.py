"""Image regression for the distant-ground normal failure at the fixed road camera."""
from pathlib import Path
from PIL import Image
import numpy as np
import json
import argparse

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreWoodland'
# Ground between trunks, beyond the moving 48m deformation mesh. The sky,
# black letterbox, car and HUD are outside this fixed-camera sample.
ROI=(600,355,770,385)
def black_fraction(path):
    image=Image.open(path).convert('RGB')
    assert image.size==(1440,900),image.size
    pixels=np.asarray(image.crop(ROI))
    return float(np.mean(np.max(pixels,axis=2)<8))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--after',default='Forest_WorldNormal.png');args=parser.parse_args()
    before=OUT/'ShadowDiagnostic_WorldNormal.png'
    after=OUT/args.after
    assert after.stat().st_mtime>(ROOT/'Content/GrandTour/ArtTests/BenmoreWoodland/M_Terrain.uasset').stat().st_mtime,'Capture predates saved material'
    report={'before':str(before),'after':str(after),'roi_xyxy':ROI,
            'before_black_fraction':black_fraction(before),'after_black_fraction':black_fraction(after)}
    report['ok']=report['before_black_fraction']>.8 and report['after_black_fraction']<.01
    (OUT/'terrain-normal-regression.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2));assert report['ok'],report
