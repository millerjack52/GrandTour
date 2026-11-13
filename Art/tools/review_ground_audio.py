"""Measure native ground exports and make a gently faded listening copy of the mixed audition."""
from pathlib import Path
import json
import numpy as np
from scipy import signal
from scipy.io import wavfile

root=Path(__file__).resolve().parents[2]
folder=root/'Saved/GroundAudioQA'
metadata=json.loads((folder/'materials.json').read_text())
sr,ground=wavfile.read(folder/'01_ground_materials.wav')
rate,mixed=wavfile.read(folder/'02_engine_and_ground.wav')
assert sr==rate==48000 and ground.dtype==mixed.dtype==np.int16
assert ground.shape==mixed.shape==(48000*28,2)
g=ground.astype(float)/32768;m=mixed.astype(float)/32768
assert np.isfinite(g).all() and np.isfinite(m).all() and np.max(abs(m))<.98
rows=[]
for i,item in enumerate(metadata['materials']):
    start=round(i*3.5*sr);x=g[start+sr//2:start+sr*3]
    f,p=signal.welch(x.mean(axis=1),sr,nperseg=8192)
    centroid=float(np.sum(f*p)/np.sum(p));rms=float(np.sqrt(np.mean(x*x)))
    rows.append(dict(material=item['material'],start_seconds=i*3.5,rms_dbfs=20*np.log10(rms),
        centroid_hz=centroid,peak_dbfs=float(20*np.log10(np.max(abs(x)))),
        dc_offset=np.mean(x,axis=0).tolist()))
    assert -.002<np.mean(x)<.002 and .003<rms<.06
    # Fade only the audition boundaries; the native test wave remains untouched.
    n=round(.10*sr);fade=np.sin(np.linspace(0,np.pi/2,n))**2
    m[start:start+n]*=fade[:,None];m[start+3*sr-n:start+3*sr]*=fade[::-1,None]
assert rows[6]['centroid_hz']>rows[4]['centroid_hz']*2
assert rows[3]['centroid_hz']>rows[2]['centroid_hz']*1.4
wavfile.write(folder/'03_listening_preview.wav',sr,(m*32767).astype(np.int16))
report=dict(native_materials_valid=True,engine_mix_unclipped=True,
    mix_peak_dbfs=float(20*np.log10(np.max(abs(mixed.astype(float)/32768)))),
    materials=rows,source='Procedural material textures; approved recorded V8 remains unchanged.')
(folder/'verification.json').write_text(json.dumps(report,indent=2))
(folder/'LISTENING_GUIDE.txt').write_text('Ground S1: 3 seconds each, with 0.5 second gaps.\n'+
    '\n'.join(f"{r['start_seconds']:4.1f}s {r['material']}" for r in rows)+
    '\n01: ground only. 02: raw native engine + ground. 03: audition with faded section edges.\n'+
    'Native sources use independent stereo noise beds and irregular grains, not recordings.\n'+
    'Driving: Art/play_range_rover_audio.bat; gravel road and grass verge on the existing circuit.\n'+
    'Console gt.Audio.GroundVolume 0 auditions engine alone; 1 restores ground audio.\n')
print(json.dumps(report,indent=2))
