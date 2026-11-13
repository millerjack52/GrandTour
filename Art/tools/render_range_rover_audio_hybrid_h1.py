"""Recording-led V8 voice audition with a restrained procedural bass layer.

Real V8 recordings retain their original timing and pitch. This deliberately
tests the voice before building game-driven granular playback. No Unreal use.
Source files, acquisition metadata and credits are retained outside game Content.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import zipfile
import numpy as np
import soundfile as sf
from scipy import signal
from scipy.io import wavfile
import render_range_rover_audio_v3 as v3

v1=v3.v1
ROOT=v3.ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rms(x):
    return float(np.sqrt(np.mean(x*x)))


def crossfade(a,b,n):
    if a is None:return b.copy()
    # Smooth complementary windows avoid a coherent +3 dB gain hump.
    w=.5-.5*np.cos(np.linspace(0,np.pi,n))
    if a.ndim==2:w=w[:,None]
    return np.concatenate((a[:-n],a[-n:]*(1-w)+b[:n]*w,b[n:]))


def fade(x,sr):
    x=x.copy();n=round(.12*sr);w=np.sin(np.linspace(0,np.pi/2,n))**2
    x[:n]*=w[:,None];x[-n:]*=w[::-1,None]
    return x


def load_sources(p):
    sr=p['sample_rate'];data={};provenance=[]
    for key,spec in p['sources'].items():
        path=ROOT/spec['file']
        entry=next(x for x in json.loads((ROOT/spec['metadata']).read_text()) if x['id']==spec['id'])
        assert sha(path)==entry['sha256'],path
        assert spec['page']==entry['source_page'] and spec['license_url']==entry['license_url']
        x,rate=sf.read(path,always_2d=True)
        if rate!=sr:
            divisor=math.gcd(sr,rate)
            x=signal.resample_poly(x,sr//divisor,rate//divisor,axis=0)
        assert x.shape[1]==2 and np.isfinite(x).all()
        # Gentle preparation, no phase vocoder, synthetic top end or pitch shift.
        x=v1.filtered(x,sr,p['source_highpass_hz'],'highpass')
        x=v1.filtered(x,sr,p['source_lowpass_hz'],'lowpass')
        mid=x.mean(axis=1,keepdims=True)
        x=mid+p['stereo_width']*(x-mid)
        a,b=spec['gain_reference_seconds']
        level=rms(x[round(a*sr):round(b*sr)])
        gain=.045/max(level,1.e-10)
        data[key]=x*gain
        provenance.append(dict(**spec,download_url=entry['download_url'],source_sha256=entry['sha256'],
            retrieved=entry['retrieved'],source_format=entry['format'],preparation_gain=gain))
    return data,provenance


def assemble(p,data):
    sr=p['sample_rate'];n=round(sr*p['crossfade_seconds'])
    recording=None;rpm=None;chapters=[]
    for item in p['segments']:
        a=round(item['start']*sr);b=round(item['end']*sr)
        clip=data[item['source']][a:b]
        assert len(clip)==b-a and len(clip)>n
        hints=v1.curve(np.arange(a,b)/sr,item['rpm_hints'])
        start=0 if recording is None else (len(recording)-n)/sr
        recording=crossfade(recording,clip,n);rpm=crossfade(rpm,hints,n)
        chapters.append(dict(start_seconds=start,end_seconds=len(recording)/sr,**item))
    # Use the natural recording envelope to make support follow the rev effort.
    power=v3.follow(np.mean(recording*recording,axis=1),sr,.04,.18)
    env=np.sqrt(np.maximum(power,0))
    lo,hi=np.percentile(env,[15,95])
    load=.10+.72*np.clip((env-lo)/max(hi-lo,1.e-9),0,1)
    return recording,rpm,load,chapters


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'Art/Export/VehicleAudio/RangeRover_Hybrid_H1_review')
    args=parser.parse_args()
    if args.out.exists():raise SystemExit('Preserving existing output; choose a fresh --out directory.')
    preset=ROOT/'Art/Audio/range_rover_v8_hybrid_h1.json';p=json.loads(preset.read_text());sr=p['sample_rate']
    assert sr==48000
    data,provenance=load_sources(p)
    recording,rpm,load,chapters=assemble(p,data)
    # Four-stroke V8 phase remains continuous through every excerpt boundary.
    banks=np.array([0,1,1,0,1,0,0,1]);gains=np.array([1.05,.91,1.04,.98,.94,1.06,.92,1.])
    pressure,fires=v1.combust(rpm,load,np.zeros(len(rpm)),sr,banks,gains)
    low=v1.filtered(pressure[0]+pressure[1],sr,p['procedural_support_band_hz'],'bandpass',order=4)
    support=np.column_stack((low,low))
    bass=v1.filtered(recording,sr,p['procedural_support_band_hz'],'bandpass',order=4)
    support_gain=rms(bass)/max(rms(support),1.e-10)*10**(p['procedural_to_recorded_bass_db']/20)
    support*=support_gain
    recording=fade(recording,sr);support=fade(support,sr)
    hybrid=recording+support
    assert np.max(np.abs(hybrid-recording))>0
    assert abs(len(fires)-np.sum(rpm)/sr/120*8)<=1
    gain=10**(p['maximum_true_peak_dbfs']/20)/max(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))) for x in [recording,hybrid])
    recording*=gain;support*=gain;hybrid*=gain
    args.out.mkdir(parents=True)
    report=dict(version='H1',recordings_used=True,procedural_only=False,in_game_integrated=False,
        source_led_audition=True,arbitrary_rpm_playback_implemented=False,profile=p,source_provenance=provenance,
        source_hashes={str(f.relative_to(ROOT)):sha(f) for f in [Path(__file__),Path(v3.__file__),Path(v1.__file__),Path(v3.v2.__file__),preset]},
        shared_gain=float(gain),support_gain=support_gain,chapters=chapters,
        procedural_rms_relative_to_recording_db=20*np.log10(rms(support)/rms(recording)),files=[])

    def save(name,x,**extra):
        assert np.isfinite(x).all() and np.max(np.abs(x))<1
        path=args.out/(name+'.wav');v1.write_wav(path,x,sr)
        rate,decoded=wavfile.read(path)
        assert rate==sr and decoded.dtype==np.int16 and decoded.shape==x.shape
        m=v1.metrics(decoded.astype(float)/32768,sr)
        assert m['finite'] and m['clipped_samples']==0 and m['true_peak_dbfs']<=-5.94
        assert max(abs(v) for v in m['dc_offset'])<.0002
        report['files'].append(dict(file=path.name,sha256=sha(path),**m,**extra))

    save('00_recording_led_hybrid',hybrid)
    save('01_recordings_without_procedural_support',recording)
    reference=ROOT/'Art/Export/VehicleAudio/RangeRover_Procedural_v4_review/00_mid_high_revision.wav'
    rate,old=wavfile.read(reference);assert rate==sr
    report['comparison_reference_sha256']=sha(reference)
    comp,matching=v3.comparison([old[4*sr:12*sr].astype(float)/32768,hybrid[4*sr:12*sr]])
    save('02_procedural_then_hybrid',comp,matching=matching,
        note='V4 4-12 s then H1 4-12 s. Tone-direction comparison: different rev contours, not an identical-RPM benchmark.')
    (args.out/'controls.json').write_text(json.dumps(dict(time_s=(np.arange(len(rpm))[::480]/sr).tolist(),
        rpm_hints=rpm[::480].tolist(),support_load=load[::480].tolist(),firing_count=len(fires),
        warning='Authored hints for procedural support; NOT measured source RPM or live gameplay telemetry.')))
    credits='THIRD-PARTY AUDIO ATTRIBUTION - GRAND TOUR HYBRID H1\n\n'
    for item in provenance:
        credits+=f"{item['title']}\nBy {item['creator']}\n{item['page']}\n{item['license']}: {item['license_url']}\n\n"
    credits+='''Changes: selected excerpts, high/low-pass filtering, stereo-width and gain
adjustments, crossfades, and mixing with original procedural low-frequency support.
Recordings play at their original speed/pitch. Public HQ MP3 previews were used;
these are not the original lossless WAVs. No recorder endorsement is implied.
Keep these credits and license links with redistributed/derived audio. The sound
recordings retain their stated Creative Commons licenses. Game code is separate.
'''
    (args.out/'ATTRIBUTION.txt').write_text(credits)
    (args.out/'profile.json').write_text(json.dumps(p,indent=2))
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2))
    (args.out/'LISTENING_GUIDE.txt').write_text('''GRAND TOUR - RECORDING-LED V8 HYBRID H1

00 (22.6 s): recorded idle, two revs, sustained note and return to idle;
quiet procedural bass support follows authored RPM hints and the sound envelope.
01 (22.6 s): identical prepared recordings without the procedural support layer.
02 (17 s): 0-8 previous procedural V4, 8.5-16.5 recording-led hybrid.
Comparison matches K-weighted segment energy, not gated LUFS; the rev contours
are different, so judge natural engine texture rather than exact RPM matching.

Sources: Dodge RAM V8 idle by sketchy.dog and a classic Dodge 318 V8 revving
by BoilingSand. See ATTRIBUTION.txt for source links, licenses and changes.
No claim of an exact Rover V8 recreation. No racing-engine synthesis is used to
replace the recorded mid/high detail. Source revs retain their natural timing.

This first hybrid test establishes a voice. Arbitrary gameplay-controlled RPM,
loaded/off-load loop or grain selection, shifts and runtime CPU/latency still
need development after listening acceptance. RPM hints are not tachometer data.
The available HQ MP3 previews are sufficient for an audition; evaluate original
lossless recordings and fuller RPM/load coverage before production integration.

Engine only; no extra road/gravel ambience added. Field recordings may retain
their original background sound. No subjective listening approval is claimed.
Game files/mute settings untouched; Unreal was not launched.

Reproduce: Saved/Tools/TerrainPython/Scripts/python.exe
Art/tools/render_range_rover_audio_hybrid_h1.py --out <fresh directory>.
Requires numpy, scipy, numba and soundfile (tested with soundfile 0.14.0).
''')
    with zipfile.ZipFile(args.out/'RangeRover_hybrid_H1_samples.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(args.out.iterdir()):
            if path.suffix in ('.wav','.json','.txt'):z.write(path,path.name)
    print(json.dumps(dict(seconds=len(hybrid)/sr,procedural_db=report['procedural_rms_relative_to_recording_db'],
        files=[(f['file'],f['true_peak_dbfs']) for f in report['files']]),indent=2))


if __name__=='__main__':main()
