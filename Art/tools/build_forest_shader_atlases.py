"""Repack existing tree bakes for mipmaps and add projected canopy occlusion.

No generated imagery: all colour, silhouette and normals come from the saved
mesh captures. Occlusion is a conservative silhouette-based approximation.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt,gaussian_filter
ROOT=Path('C:/GrandTour');SOURCE=ROOT/'Art/Export/LidarStudy/Place';OUT=SOURCE/'ForestShaders';OUT.mkdir(exist_ok=True)
rows=[]
for kind in range(4):
    src=SOURCE/f'FirAtlas_{kind}.tga';npath=SOURCE/f'FirNormal_{kind}.tga'
    colour=np.asarray(Image.open(src).convert('RGBA')).copy();normal=np.asarray(Image.open(npath).convert('RGBA')).copy()
    assert colour.shape==normal.shape==(512,1536,4)
    c=np.zeros((512,2048,4),np.uint8);n=np.full_like(c,255);n[:,:,:2]=128
    ranges=[]
    for view in range(3):
        lo=view*512;hi=lo+512;cc=colour[:,lo:hi].copy();nn=normal[:,lo:hi].copy();alpha=cc[:,:,3]/255.;mask=alpha>.35
        assert mask.sum()>100
        _,indices=distance_transform_edt(~mask,return_indices=True)
        # Transparent texels retain nearby leaf colour/normal so mip filters do
        # not blend silhouettes with black backgrounds or invalid normals.
        for rgb in [cc,nn]:rgb[:,:,:3]=rgb[indices[0],indices[1],:3]
        mass=.65*gaussian_filter(alpha,9)+.35*gaussian_filter(alpha,25)
        cavity=np.clip(1-.36*mass,.64,1) if kind<3 else np.ones_like(mass)
        nn[:,:,3]=np.uint8(cavity*255+.5)
        c[:,lo:hi]=cc;n[:,lo:hi]=nn
        ranges.append(dict(view=view,coverage=float(mask.mean()),mean_occlusion=float(cavity[mask].mean())))
    # Fourth tile is padding; its edge data is continuous with the third tile.
    c[:,1536:,:3]=c[:,1535:1536,:3];n[:,1536:,:3]=n[:,1535:1536,:3]
    Image.fromarray(c).save(OUT/f'T_FS_Colour_{kind}.png');Image.fromarray(n).save(OUT/f'T_FS_NormalAO_{kind}.png')
    rows.append(dict(kind=kind,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),normal_sha256=hashlib.sha256(npath.read_bytes()).hexdigest(),size=[2048,512],uv_scale=[.75,1],views=ranges))
(OUT/'atlas-build.json').write_text(json.dumps(dict(method='Power-of-two padding, edge dilation, alpha-coverage mipmaps; projected occlusion packed into normal alpha',trees=rows),indent=2))
print(json.dumps(rows,indent=2))
