"""Reconstruct tileable relief from the purchased OpenGL normals, not colour brightness.

These are approximate derived height maps, not creator-supplied displacement maps.
Store moss / litter / soil in RGB so each POM step needs one texture read.
"""
from pathlib import Path
import numpy as np,json
from PIL import Image
SRC=Path('D:/GrandTourAssets/FlippedNormals/Lazy_Forest_Gen_Addon/Assets/Textures/Ground')
OUT=Path('C:/GrandTour/Art/Export/FloraDrive')
channels=[];metrics=[];size=2048
for i in (1,2,3):
    normal=np.asarray(Image.open(SRC/('Ground_%02dN.png'%i)).convert('RGB').resize((size,size),Image.Resampling.LANCZOS),dtype=np.float64)/127.5-1
    nz=np.maximum(normal[:,:,2],.18)
    dx=np.clip(-normal[:,:,0]/nz,-4,4);dy=np.clip(normal[:,:,1]/nz,-4,4)
    wx=2*np.pi*np.fft.fftfreq(size)[None,:];wy=2*np.pi*np.fft.fftfreq(size)[:,None]
    denom=wx*wx+wy*wy;denom[0,0]=1
    spectrum=(-1j*wx*np.fft.fft2(dx)-1j*wy*np.fft.fft2(dy))/denom
    spectrum[0,0]=0
    # Remove metre-scale integration drift; retain leaf, clod and stone relief.
    spectrum*=1-np.exp(-(wx*wx+wy*wy)*(size/60)**2)
    height=np.fft.ifft2(spectrum).real
    lo,hi=np.percentile(height,[1,99]);height=np.clip((height-lo)/(hi-lo),0,1)
    channels.append(np.uint8(np.round(height*255)))
    metrics.append({'source':str(SRC/('Ground_%02dN.png'%i)),'raw_height_range':[float(lo),float(hi)]})
Image.fromarray(np.stack(channels,axis=2)).save(OUT/'T_ForestHeightRGB.png')
(OUT/'ground-height-report.json').write_text(json.dumps({'method':'periodic Fourier integration of purchased OpenGL normals; approximate reconstruction','channels':['moss','leaf litter','soil'],'size':size,'sources':metrics},indent=2))
