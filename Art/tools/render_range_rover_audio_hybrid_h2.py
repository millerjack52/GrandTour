"""Offline recorded-loop V8 renderer driven by independent RPM and throttle.

Continuous cursors, seam-matched recorded loops, smooth bank selection, throttle
filter/level response, and quiet procedural bass. Does not launch or edit Unreal.
"""
from pathlib import Path
import argparse
import json
import math
import zipfile
import numpy as np
from numba import njit
from scipy import signal
from scipy.io import wavfile
import render_range_rover_audio_hybrid_h1 as h1

v3=h1.v3
v1=h1.v1
ROOT=h1.ROOT


def scenarios():
    return [
        dict(id='01_acceleration_shifts_lift',seconds=24,
             notes='Idle 0-3 s; pull to 4200 RPM, shift at 9 s; second pull, then lift at 15 s and coast to idle.',
             rpm=[(0,800),(3,800),(4,1500),(6,2500),(8.8,4200),(9.2,2600),(12,3450),(14.8,4200),(15.4,3950),(18,2800),(21,1500),(23,800),(24,800)],
             throttle=[(0,.08),(2.8,.08),(3.3,.85),(8.75,.9),(8.98,.02),(9.2,.05),(9.45,.9),(14.8,.9),(15.05,0),(22,0),(23,.08),(24,.08)]),
        dict(id='02_fixed_rpm_throttle',seconds=12,
             notes='2500 RPM held throughout: light throttle 0-3 s, full 3.2-6 s, medium 6.2-9 s, closed 9.2-12 s.',
             rpm=[(0,2500),(12,2500)],
             throttle=[(0,.10),(3,.10),(3.2,.95),(6,.95),(6.2,.35),(9,.35),(9.2,0),(12,0)]),
        dict(id='03_mid_high_holds',seconds=15,
             notes='Constant 80% throttle: 2400 RPM 0-4 s, 3200 RPM 5-9 s, 4200 RPM 10-15 s.',
             rpm=[(0,2400),(4,2400),(5,3200),(9,3200),(10,4200),(15,4200)],
             throttle=[(0,.8),(15,.8)])
    ]


def prepare_loop(x,sr,p):
    """Choose a correlated end region, then overlap the tail into the loop head.

    At the actual circular boundary the samples remain consecutive source samples.
    The waveform transition occurs over the overlap rather than at a hard splice.
    """
    overlap=round(p['loop_crossfade_seconds']*sr)
    match=round(p['loop_match_seconds']*sr)
    search=round(p['loop_end_search_seconds']*sr)
    mono=x.mean(axis=1)
    template=mono[:match]-np.mean(mono[:match])
    low=len(x)-overlap-search;high=len(x)-overlap
    assert low>overlap
    region=mono[low:high+match]
    cross=signal.correlate(region,template,mode='valid',method='fft')
    energy=signal.convolve(region*region,np.ones(match),mode='valid',method='fft')
    score=cross/np.sqrt(np.maximum(energy*np.sum(template*template),1.e-20))
    period=low+int(np.argmax(score))
    w=.5-.5*np.cos(np.linspace(0,np.pi,overlap))
    loop=x[:period].copy()
    loop[:overlap]=x[period:period+overlap]*(1-w[:,None])+x[:overlap]*w[:,None]
    # Remove the small per-loop DC component before variable-rate playback.
    loop-=np.mean(loop,axis=0)
    gain=p['prepared_loop_rms']/max(h1.rms(loop),1.e-12)
    loop*=gain
    return loop,dict(period_samples=period,period_seconds=period/sr,
        seam_correlation=float(np.max(score)),normalisation_gain=gain,
        wrap_step=float(np.max(np.abs(loop[0]-loop[-1]))))


def build_banks(p,source_data):
    loops=[];details=[];sr=p['sample_rate']
    for spec in p['banks']:
        x=source_data[spec['source']][round(spec['start']*sr):round(spec['end']*sr)]
        loop,detail=prepare_loop(x,sr,p)
        loops.append(loop);details.append(dict(**spec,**detail))
    lengths=np.array([len(x) for x in loops],dtype=np.int64)
    packed=np.zeros((len(loops),int(max(lengths)),2))
    for i,x in enumerate(loops):packed[i,:len(x)]=x
    return packed,lengths,np.array([s['root_rpm'] for s in p['banks']],dtype=float),details


@njit(cache=True)
def playback(packed,lengths,roots,rpm,initial_positions):
    """Pitch follows RPM; cursors never reset when throttle or active bank changes.

    Root-to-root blending is smooth in log RPM, using constant-power weights.
    Sources were low-passed at 6.5 kHz; the highest *audible* rate in the supported
    range is 5000/2180, keeping that band below the 24 kHz output Nyquist limit.
    """
    n=len(rpm);count=len(roots);out=np.zeros((n,2))
    positions=initial_positions.copy()
    for i in range(n):
        lower=0
        while lower<count-1 and rpm[i]>=roots[lower+1]:lower+=1
        upper=min(lower+1,count-1)
        if rpm[i]<=roots[0]:upper=lower=0
        if lower==upper:
            w0=1.;w1=0.
        else:
            mix=(math.log(rpm[i])-math.log(roots[lower]))/(math.log(roots[upper])-math.log(roots[lower]))
            mix=max(0.,min(1.,mix));mix=mix*mix*(3-2*mix)
            w0=math.cos(mix*math.pi/2);w1=math.sin(mix*math.pi/2)
        for bank in range(count):
            pos=positions[bank];a=int(pos);f=pos-a;b=(a+1)%lengths[bank]
            weight=w0 if bank==lower else (w1 if bank==upper else 0.)
            if weight>0:
                for c in range(2):out[i,c]+=weight*(packed[bank,a,c]*(1-f)+packed[bank,b,c]*f)
            positions[bank]=(pos+rpm[i]/roots[bank])%lengths[bank]
    return out,positions


@njit(cache=True)
def throttle_response(x,throttle,rpm,sr,closed_hz,open_hz,presence_gain):
    out=np.zeros_like(x);low1=np.zeros(2);low2=np.zeros(2)
    presence_top=np.zeros(2);presence_bottom=np.zeros(2)
    top_a=1-math.exp(-2*math.pi*2500/sr)
    bottom_a=1-math.exp(-2*math.pi*220/sr)
    for i in range(len(x)):
        cutoff=closed_hz+(open_hz-closed_hz)*throttle[i]**.7
        a=1-math.exp(-2*math.pi*cutoff/sr)
        gain=(.27+.73*math.sqrt(throttle[i]))*(.70+.30*math.sqrt(rpm[i]/5000))
        for c in range(2):
            low1[c]+=a*(x[i,c]-low1[c]);low2[c]+=a*(low1[c]-low2[c])
            presence_top[c]+=top_a*(low2[c]-presence_top[c])
            presence_bottom[c]+=bottom_a*(low2[c]-presence_bottom[c])
            # Authored load colour from recorded material, no added oscillator/noise.
            presence=presence_top[c]-presence_bottom[c]
            out[i,c]=gain*(low2[c]+presence_gain*throttle[i]**.8*presence)
    return out


def render(spec,p,bank_data):
    sr=p['sample_rate'];t=np.arange(round(spec['seconds']*sr))/sr
    requested_rpm=v1.curve(t,spec['rpm']);requested_throttle=v1.curve(t,spec['throttle'])
    rpm=v3.follow(np.clip(requested_rpm,p['minimum_rpm'],p['maximum_rpm']),sr,p['rpm_smoothing_seconds'],p['rpm_smoothing_seconds'])
    throttle=v3.follow(np.clip(requested_throttle,0,1),sr,p['throttle_attack_seconds'],p['throttle_release_seconds'])
    packed,lengths,roots,_=bank_data
    recorded,positions=playback(packed,lengths,roots,rpm,np.zeros(len(roots)))
    recorded=throttle_response(recorded,throttle,rpm,sr,p['closed_throttle_cutoff_hz'],p['open_throttle_cutoff_hz'],p['loaded_presence_gain'])
    recorded=v1.filtered(recorded,sr,29,'highpass')
    # Same quiet procedural support principle as approved H1; no synthetic top end.
    pressure,fires=v1.combust(rpm,throttle,np.zeros(len(rpm)),sr,np.array([0,1,1,0,1,0,0,1]),np.array([1.05,.91,1.04,.98,.94,1.06,.92,1.]))
    low=v1.filtered(pressure.sum(axis=0),sr,p['support_band_hz'],'bandpass',order=4)
    support=np.column_stack((low,low))
    assert abs(len(fires)-np.sum(rpm)/sr/120*8)<=1
    recorded=h1.fade(recorded,sr);support=h1.fade(support,sr)
    controls=dict(time_s=t[::480].tolist(),requested_rpm=requested_rpm[::480].tolist(),rpm=rpm[::480].tolist(),
        requested_throttle=requested_throttle[::480].tolist(),throttle=throttle[::480].tolist(),
        final_loop_positions=positions.tolist(),firing_count=len(fires),
        note='Independent authored RPM/throttle inputs; source root RPMs are provisional acoustic estimates.')
    return recorded,support,controls


def checks(p,bank_data):
    sr=p['sample_rate']
    # Playback-rate check with a known carrier, unrelated to the engine recording.
    t=np.arange(sr)/sr;tone=np.sin(2*np.pi*200*t)
    packed=np.column_stack((tone,tone))[None,:,:]
    lengths=np.array([sr],dtype=np.int64);roots=np.array([1000.])
    rpm=np.full(sr*2,2000.)
    y,_=playback(packed,lengths,roots,rpm,np.zeros(1))
    f,power=signal.welch(y[:,0],sr,nperseg=sr)
    assert abs(f[np.argmax(power)]-400)<1
    # Splitting a varying control trace must not restart cursors at buffer boundaries.
    actual,lengths,roots,_=bank_data
    rpm=np.linspace(800,4200,12000)
    whole,end=playback(actual,lengths,roots,rpm,np.zeros(len(roots)))
    a,pos=playback(actual,lengths,roots,rpm[:4567],np.zeros(len(roots)))
    b,end2=playback(actual,lengths,roots,rpm[4567:],pos)
    assert np.array_equal(whole,np.concatenate((a,b))) and np.array_equal(end,end2)
    silent,_=playback(np.zeros_like(actual),lengths,roots,rpm,np.zeros(len(roots)))
    assert not np.any(silent)
    return dict(playback_pitch_ratio=True,playback_cursors_continuous_across_blocks=True,zero_input_silent=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'Art/Export/VehicleAudio/RangeRover_Hybrid_H2_final')
    args=parser.parse_args()
    if args.out.exists():raise SystemExit('Preserving existing output; choose a fresh --out folder.')
    preset=ROOT/'Art/Audio/range_rover_v8_hybrid_h2.json';p=json.loads(preset.read_text());sr=p['sample_rate']
    source_preset=ROOT/p['source_profile'];source_p=json.loads(source_preset.read_text())
    source_data,provenance=h1.load_sources(source_p)
    bank_data=build_banks(p,source_data)
    validation=checks(p,bank_data)
    raw=[]
    for spec in scenarios():
        recorded,support,controls=render(spec,p,bank_data)
        raw.append((spec,recorded,support,controls))
        print('Rendered',spec['id'],flush=True)
    # One support calibration and one output gain across the entire scenario pack.
    support_gain=min(h1.rms(v1.filtered(x,sr,p['support_band_hz'],'bandpass',order=4))/max(h1.rms(s),1.e-10)
        for _,x,s,_ in raw)*10**(p['support_to_recorded_bass_db']/20)
    combined=[x+support_gain*s for _,x,s,_ in raw]
    gain=10**(p['maximum_true_peak_dbfs']/20)/max(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))) for x in combined)
    args.out.mkdir(parents=True)
    sources=[Path(__file__),Path(h1.__file__),Path(v3.__file__),Path(v1.__file__),Path(v3.v2.__file__),preset,source_preset]
    report=dict(version='H2',recordings_used=True,in_game_integrated=False,offline_rpm_throttle_playback=True,
        runtime_port_completed=False,profile=p,loop_bank=bank_data[3],source_provenance=provenance,
        source_hashes={str(f.relative_to(ROOT)):h1.sha(f) for f in sources},checks=validation,
        shared_gain=float(gain),shared_support_gain=float(support_gain),files=[])

    def save(name,x,**details):
        assert np.isfinite(x).all() and np.max(np.abs(x))<1
        path=args.out/(name+'.wav');v1.write_wav(path,x,sr)
        rate,decoded=wavfile.read(path)
        assert rate==sr and decoded.dtype==np.int16 and decoded.shape==x.shape
        m=v1.metrics(decoded.astype(float)/32768,sr)
        assert m['finite'] and m['clipped_samples']==0 and m['true_peak_dbfs']<=-5.94
        assert max(abs(v) for v in m['dc_offset'])<.0002
        report['files'].append(dict(file=path.name,sha256=h1.sha(path),**m,**details))

    rendered=[]
    for (spec,recorded,support,controls),x in zip(raw,combined):
        x*=gain;rendered.append(x)
        save(spec['id'],x,notes=spec['notes'])
        (args.out/(spec['id']+'.controls.json')).write_text(json.dumps(controls))
    overview=v3.v2.join([rendered[0][:15*sr],rendered[1],rendered[0][15*sr:21*sr]])
    save('00_rpm_throttle_overview',overview,chapters=[dict(start=0,end=15,scene='Idle, acceleration and shift'),
        dict(start=15.5,end=27.5,scene='2500 RPM, light/full/medium/closed throttle'),
        dict(start=28,end=34,scene='Lift-off and coasting')])
    # A matched-level comparison shows timbre changes independent of loudness.
    parts=[rendered[1][round(a*sr):round(b*sr)] for a,b in [(0.5,2.5),(3.8,5.8),(9.8,11.8)]]
    matching,mdata=v3.comparison(parts)
    save('04_throttle_tone_matched',matching,order=['light','full','closed'],matching=mdata)
    diagnostics=[]
    for label,x in zip(['light','full','closed'],parts):
        diagnostics.append(dict(state=label,**v3.v2.colour(x,sr),rms_dbfs=20*np.log10(h1.rms(x))))
    assert diagnostics[1]['rms_dbfs']>diagnostics[0]['rms_dbfs']+3
    assert diagnostics[1]['centroid_hz']>diagnostics[0]['centroid_hz']*1.05
    validation['throttle_changes_level_and_spectrum_at_fixed_rpm']=True
    report['fixed_rpm_diagnostics']=diagnostics
    # Export actual prepared loops, separately levelled for use in subsequent work.
    loop_dir=args.out/'PreparedLoops';loop_dir.mkdir()
    packed,lengths,roots,_=bank_data
    for i,spec in enumerate(p['banks']):
        # Float WAV retains the prepared loop's calibration without PCM clipping.
        wavfile.write(loop_dir/(spec['name']+'.wav'),sr,packed[i,:lengths[i]].astype(np.float32))
    credits='THIRD-PARTY AUDIO ATTRIBUTION - GRAND TOUR HYBRID H2\n\n'
    for item in provenance:
        credits+=f"{item['title']}\nBy {item['creator']}\n{item['page']}\n{item['license']}: {item['license_url']}\n\n"
    credits+='''Changes: excerpt selection, filtering, stereo-width and gain changes,
seam-matched looping, variable-rate RPM playback, crossfades, throttle-dependent
filtering/amplitude, and quiet procedural bass support. Public HQ MP3 previews
were used; original lossless WAVs have not been acquired. No recorder endorsement
is implied. Keep these credits and license links with redistributed audio and
prepared loops. Source recordings retain their stated Creative Commons licenses.
'''
    (args.out/'ATTRIBUTION.txt').write_text(credits)
    (args.out/'profile.json').write_text(json.dumps(p,indent=2))
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2))
    (args.out/'LISTENING_GUIDE.txt').write_text('''GRAND TOUR HYBRID H2 - INDEPENDENT RPM / THROTTLE CONTROL

00 overview (34.5 s): 0-15 idle/pull/shift; 15.5-27.5 fixed 2500 RPM with
light/full/medium/closed throttle; 28-34 lift-off and coasting. Half-second gaps.
01 full driving trace (24 s): idle, two pulls to 4200 RPM, shift, lift and coast.
02 fixed RPM (12 s): throttle changes at 3, 6 and 9 s while RPM stays at 2500.
03 upper-range holds (15 s): 2400, 3200, 4200 RPM at fixed 80% throttle.
04 matched-level throttle tone (7.5 s): light/full/closed, two seconds each.
Main scenes share one gain; 04 matches K-weighted segment energy (not gated LUFS).

Real V8 excerpts play continuously with variable-rate cursors and smooth blending
between four prepared loop banks. RPM and throttle are independent inputs;
throttle controls brightness and gain without changing playback pitch. Source
timelines no longer determine the output rev sequence. Cursor state is retained
across playback blocks. The Python audition's filters are offline implementations;
runtime buffering/filter state, device latency and CPU cost still require a port.

Root RPMs are provisional acoustic estimates, NOT measured tachometer readings.
Highest source root is 2180 RPM; 4200 RPM pitches it upward about 1.93x. Listen
especially for excessive brightness or obvious repetition there. Throttle tone
is authored from these recordings; no separate measured on/off-load bank exists.
The sources are Dodge V8s, not an exact Rover recreation. Credits are included.

PreparedLoops contains float WAVs for later work. Previous H1 and procedural
samples remain intact. No game source, assets or mute settings changed; no Unreal
launch. Listening approval and runtime integration are still pending.

Reproduce: Saved/Tools/TerrainPython/Scripts/python.exe
Art/tools/render_range_rover_audio_hybrid_h2.py --out <fresh directory>.
''')
    with zipfile.ZipFile(args.out/'RangeRover_hybrid_H2_samples.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(args.out.rglob('*')):
            if path.is_file() and path.suffix in ('.wav','.json','.txt'):z.write(path,str(path.relative_to(args.out)))
    print(json.dumps(dict(checks=validation,loop_bank=bank_data[3],throttle=diagnostics),indent=2))


if __name__=='__main__':main()
