"""Bake approved S2/S3 recording textures into an immutable runtime PCM bank."""
import json
import struct
import hashlib
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
import render_ground_audio_s2 as s2
import render_ground_audio_s3 as s3

OUT=s2.ROOT/'Content/Audio/RangeRoverGroundS3'
OUT.mkdir(parents=True,exist_ok=True)
raw={name:s3.load(s2.REF/(name+'_hq_preview.mp3')) for name in ['gravel1','gravel2','grass_foley','skid']}
loops=[s2.loop(raw['gravel1'],.5,10.5,115,5800,.030),
       s2.loop(raw['gravel2'],1,15,115,5800,.030),
       s2.loop(raw['grass_foley'],.05,4.25,100,3800,.012)]
texture=s2.loop(raw['gravel2'],1,15,120,1600,.1)
excitation=s2.play(texture,np.full(round(len(texture)/.52),.52),2*s2.SR)
body=s2.level(s2.filtered(excitation,38,225),.037)
body=.85*body.mean(axis=1,keepdims=True)+.15*body
# Bake one full source cycle, then make the filtered boundary continuous.
overlap=int(.16*s2.SR);n=len(body)-overlap
w=(.5-.5*np.cos(np.linspace(0,np.pi,overlap)))[:,None]
body[:overlap]=body[n:]*(1-w)+body[:overlap]*w
loops.append(body[:n])
loops.append(s2.fade(s2.level(s2.filtered(raw['skid'],100,6500),.055)))
for i in range(8):
    length=round((.30+.025*(i%3))*s2.SR);offset=round((1.2+i*.9)*s2.SR)
    clip=s2.play(raw['gravel2'][offset:offset+length*2],np.full(length,.53))
    clip=s2.level(s2.filtered(clip,48,520),.065)
    env=np.minimum(np.arange(length)/(.018*s2.SR),1)*np.exp(-np.arange(length)/(.085*s2.SR))
    loops.append(s2.fade(clip*env[:,None],.012))
bank=bytearray(struct.pack('<4I',0x33535447,1,48000,len(loops)))
for x in loops:
    assert np.isfinite(x).all() and np.max(np.abs(x))<.85
    bank+=struct.pack('<I',len(x))+x.astype('<f4').tobytes()
path=OUT/'recordings.gts3';path.write_bytes(bank)
source=s2.ROOT/'Art/Export/VehicleAudio/Ground_Recorded_S3_BodyRumble'
for name in ['sources.json','ATTRIBUTION.txt']:
    (OUT/name).write_bytes((source/name).read_bytes())
manifest=dict(version=1,sample_rate=48000,sha256=hashlib.sha256(bank).hexdigest(),
    frames=[len(x) for x in loops],order=['gravel_slow','gravel_fast','grass_foley','body','gravel_stop']+['bump_'+str(i) for i in range(8)],
    note='Approved recording-derived S3 textures. Grass is provisional cloth Foley. Body is designed rumble, not measured suspension audio.')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
