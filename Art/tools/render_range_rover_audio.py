"""Offline, recording-free V8 listening prototype. Does not load or modify Unreal.

Sample-rate combustion events -> two exhaust banks -> damped pipe reflections,
load-dependent filtering/saturation, plus generated intake/mechanical layers.
All clips share one output gain; traces are authored auditions, not live telemetry.
Run with Saved/Tools/TerrainPython/Scripts/python.exe Art/tools/render_range_rover_audio.py
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import time
import zipfile

import numpy as np
from numba import njit
from scipy import signal
from scipy.interpolate import PchipInterpolator
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / 'Art/Audio/range_rover_v8_prototype.json'


def curve(t, anchors):
    return PchipInterpolator(*np.array(anchors, dtype=float).T)(t)


def scenarios():
    return [
        dict(id='01_idle_and_blips', title='Idle and three throttle blips', seconds=18,
             notes='0-3 s idle; blips around 4, 8 and 12 s; returns to idle. Exterior close listening perspective.',
             rpm=[(0,800),(3,800),(3.7,2200),(4.0,2300),(5.8,800),(7,800),(7.7,3400),(8,3500),(10.3,800),(11.3,800),(12.0,4100),(12.3,4200),(15.1,800),(18,800)],
             load=[(0,.10),(3,.10),(3.2,.65),(3.7,.32),(4,.07),(6,.10),(7,.10),(7.2,.80),(7.7,.38),(8,.06),(10.5,.10),(11.3,.10),(11.5,.85),(12,.40),(12.3,.04),(15.2,.10),(18,.10)]),
        dict(id='02_acceleration_shifts_lift', title='Loaded acceleration, two shifts, lift-off', seconds=24,
             notes='0-2 s idle; loaded pull; shifts at about 7 and 12 s; lift-off at 17.5 s, then coast back to idle. Engine only.',
             rpm=[(0,800),(2,800),(2.7,1500),(4.5,2800),(6.9,4200),(7.23,2750),(9,3400),(11.9,4200),(12.24,2820),(14.5,3500),(17.4,4100),(18.3,3700),(20,2450),(22.5,1150),(24,800)],
             load=[(0,.10),(1.9,.10),(2.3,.86),(6.75,.90),(6.96,.04),(7.20,.08),(7.42,.91),(11.75,.92),(11.97,.03),(12.21,.07),(12.43,.92),(17.35,.92),(17.60,-.35),(21.5,-.20),(23,.07),(24,.10)]),
        dict(id='03_same_rpm_load', title='Same RPM, different engine load', seconds=14,
             notes='2500 rpm throughout. 0-4 s light load, 4.3-9 s heavy load, 9.3-14 s closed-throttle overrun. Shared gain, no per-section normalisation.',
             rpm=[(0,2500),(14,2500)],
             load=[(0,.10),(4,.10),(4.3,.90),(9,.90),(9.3,-.30),(14,-.30)]),
        dict(id='04_low_range_effort', title='Low-range climb and recovery', seconds=16,
             notes='Slow loaded climb archetype: rising effort, RPM sags at 7-9 s, then recovers; unload at 13 s. No gravel or tyre sound yet.',
             rpm=[(0,1050),(2,1400),(4.5,1800),(6,1700),(8,1150),(9,1200),(11,1850),(12.5,2000),(13.2,1800),(15,850),(16,800)],
             load=[(0,.30),(2,.65),(4.5,.78),(6,.92),(8,.98),(9,.96),(11,.88),(12.5,.75),(13,.30),(13.4,.06),(15,.10),(16,.10)])
    ]


@njit(cache=True)
def combust(rpm, load, variability, sr, banks, gains):
    """Continuous 720-degree phase; fractional event timing, no phase reset at shifts."""
    n = len(rpm)
    out = np.zeros((2, n), dtype=np.float64)
    phase = 0.0
    event = 0
    fire_times = np.zeros(int(n / sr * 400 + 64), dtype=np.float64)
    count = 0
    kernel_n = int(.016 * sr)
    for i in range(n):
        step = rpm[i] / 120.0 * 8.0 / sr
        phase += step
        if phase >= 1.0:
            phase -= 1.0
            frac = phase / max(step, 1.e-12)
            cylinder = event % 8
            bank = banks[cylinder]
            positive = max(0.0, load[i])
            # Closed throttle retains a quiet mechanical/exhaust presence. This
            # is an old petrol V8 archetype, not an assumed modern DFCO simulation.
            amplitude = (.13 + .83 * positive ** .70) * gains[cylinder]
            amplitude *= 1.0 + variability[i] * (.045 if rpm[i] < 1100 else .018)
            if load[i] < 0:
                amplitude *= .55
            # Loaded combustion has a steeper pressure rise and broader spectrum.
            # Lengthening the pulse with load cancelled the opening exhaust filter
            # in the first audition; load then mostly changed loudness.
            attack = .00023 - .00014 * positive
            decay = .00125 - .00045 * positive
            tail = .0032
            for j in range(min(kernel_n, n-i)):
                age = (j + frac) / sr
                # Asymmetric bipolar pressure wave. The slow negative tail
                # and output DC blocker avoid the old positive-half-sine fault.
                pulse = (1.0-math.exp(-age/attack)) * (
                    math.exp(-age/decay) - (decay/tail)*math.exp(-age/tail))
                out[bank, i+j] += amplitude * pulse
            fire_times[count] = (i-frac)/sr
            count += 1
            event += 1
    return out, fire_times[:count]


@njit(cache=True)
def pipe(x, cutoff, delay, feedback, sr):
    """Damped reflection delay and continuously varying low-pass; bounded feedback."""
    y = np.empty(len(x))
    ring = np.zeros(delay)
    pos = 0
    echo_lp = 0.0
    low1 = 0.0
    low2 = 0.0
    echo_a = 1.0-math.exp(-2.0*math.pi*2600.0/sr)
    for i in range(len(x)):
        reflected = ring[pos]
        echo_lp += echo_a*(reflected-echo_lp)
        pressure = x[i] + feedback*echo_lp
        ring[pos] = pressure
        pos = (pos+1) % delay
        a = 1.0-math.exp(-2.0*math.pi*cutoff[i]/sr)
        low1 += a*(pressure-low1)
        low2 += a*(low1-low2)
        y[i] = low2
    return y


def filtered(x, sr, hz, kind, order=2):
    return signal.sosfilt(signal.butter(order, hz, btype=kind, fs=sr, output='sos'), x, axis=0)


def resonant(x, sr, hz, q):
    return signal.lfilter(*signal.iirpeak(hz, q, fs=sr), x)


def delay_signal(x, samples):
    return np.concatenate((np.zeros(samples), x))[:len(x)] if samples else x.copy()


def render(spec, p):
    sr = p['sample_rate'] * p['oversampling']
    t = np.arange(round(spec['seconds']*sr))/sr
    rng = np.random.default_rng(p['seed'])
    rpm = curve(t, spec['rpm'])
    load = curve(t, spec['load'])
    slow = filtered(rng.standard_normal(len(t)), sr, 5, 'lowpass')
    slow /= max(np.std(slow), 1.e-9)
    idle = np.clip((1300-rpm)/500, 0, 1)
    actual_rpm = np.clip(rpm + slow*(2.5+idle*7), 0, p['maximum_rpm'])
    positive = np.maximum(load, 0)
    pressure, firing_times = combust(actual_rpm, load, slow, sr,
                                   np.array(p['firing_banks']), np.array(p['cylinder_gains']))
    cutoff = p['exhaust_lowpass_idle_hz'] + p['exhaust_lowpass_loaded_hz']*positive + .12*rpm
    exhaust = []
    for bank in range(2):
        x = delay_signal(pressure[bank], round(p['bank_delay_ms'][bank]*sr/1000))
        x = pipe(x, cutoff, round(p['exhaust_echo_ms'][bank]*sr/1000), p['exhaust_feedback'], sr)
        # Broad acoustic colour rather than a single whistling resonance.
        x += .30*resonant(x, sr, 115+bank*12, .85) + .17*resonant(x, sr, 330+bank*35, 1.1)
        drive = 1.3+positive*1.7
        exhaust.append(np.tanh(x*drive)/1.7)
    exhaust = np.array(exhaust)
    crank = np.cumsum(actual_rpm/60/sr)*2*np.pi
    noise = rng.standard_normal(len(t))
    intake_noise = filtered(noise, sr, [180,3200], 'bandpass')
    intake_envelope = (.45+.55*(.5+.5*np.sin(4*crank+.7)))
    intake = intake_noise*intake_envelope*(.015+.16*positive**1.5)
    intake += .13*filtered(pressure[0]+pressure[1], sr, [300,1600], 'bandpass')
    mechanical = filtered(rng.standard_normal(len(t)), sr, [750,4600], 'bandpass')
    mechanical *= (.018+.025*np.sqrt(rpm/5000))*(.5+.5*(.5+.5*np.sin(2*crank)))
    mechanical += .008*np.sin(2*crank) + .004*np.sin(8*crank)
    body = (.012+.020*positive)*np.sin(2*crank+.25) + (.008+.010*positive)*np.sin(crank)
    # Very narrow stereo: bank positions, not a chorus/artificial stereo widener.
    mid = p['intake_gain']*intake + p['mechanical_gain']*mechanical + p['body_gain']*body
    stereo = np.column_stack((p['exhaust_gain']*(.58*exhaust[0]+.42*exhaust[1])+mid,
                              p['exhaust_gain']*(.42*exhaust[0]+.58*exhaust[1])+mid))
    stereo = filtered(stereo, sr, 28, 'highpass')
    stereo = filtered(stereo, sr, 7000, 'lowpass')
    stereo = signal.resample_poly(stereo, 1, p['oversampling'], axis=0)
    # File-boundary fades, not a simulated starter or engine stall.
    fade = round(.10*p['sample_rate'])
    ramp = np.sin(np.linspace(0,np.pi/2,fade))**2
    stereo[:fade] *= ramp[:,None]
    stereo[-fade:] *= ramp[::-1,None]
    controls = dict(time_s=t[::int(sr/100)].tolist(),rpm=actual_rpm[::int(sr/100)].tolist(),
                    load=load[::int(sr/100)].tolist(),firing_count=len(firing_times),
                    expected_firing_count=float(np.sum(actual_rpm)/sr/120*8))
    return stereo, controls


def db(x):
    return float(20*np.log10(max(float(x),1.e-12)))


def metrics(x, sr):
    true_peak = np.max(np.abs(signal.resample_poly(x,4,1,axis=0)))
    f, power = signal.welch(np.mean(x,axis=1),sr,nperseg=8192)
    return dict(seconds=len(x)/sr,peak_dbfs=db(np.max(np.abs(x))),true_peak_dbfs=db(true_peak),
                rms_dbfs=db(np.sqrt(np.mean(x*x))),dc_offset=np.mean(x,axis=0).tolist(),
                max_adjacent_step=float(np.max(np.abs(np.diff(x,axis=0)))),
                energy_above_16khz_db=db(np.sqrt(np.sum(power[f>16000])/max(1.e-20,np.sum(power)))),
                finite=bool(np.isfinite(x).all()),clipped_samples=int(np.sum(np.abs(x)>=1)))


def write_wav(path,x,sr):
    wavfile.write(path,sr,np.round(np.clip(x,-1,1)*32767).astype(np.int16))


def checks():
    sr=48000
    rpm=np.full(sr*2,2400.)
    load=np.full(sr*2,.5)
    banks=np.array([0,1,1,0,1,0,0,1])
    _,fires=combust(rpm,load,np.zeros(len(rpm)),sr,banks,np.ones(8))
    assert abs(len(fires)-320)<=1
    assert np.max(np.abs(np.diff(fires)-1/160))<1/sr
    silence=pipe(np.zeros(sr),np.full(sr,1000.),200,.28,sr)
    assert not np.any(silence)
    # Ring out a high-amplitude impulse: feedback must decay, not self-oscillate.
    impulse=np.zeros(sr);impulse[0]=1
    tail=pipe(impulse,np.full(sr,1000.),200,.28,sr)
    assert np.max(np.abs(tail[-sr//4:]))<1.e-9
    return dict(firing_timing=True,zero_input_silent=True,pipe_stable=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,default=DEFAULT_PROFILE)
    parser.add_argument('--out',type=Path,default=ROOT/'Art/Export/VehicleAudio/RangeRover_Procedural_v1_review')
    args=parser.parse_args()
    if args.out.exists():
        raise SystemExit('Output already exists. Use a fresh --out directory to preserve earlier auditions.')
    p=json.loads(args.profile.read_text())
    assert p['cylinder_count']==8 and len(p['firing_banks'])==8
    assert 0<=p['exhaust_feedback']<.8
    args.out.mkdir(parents=True)
    start=time.perf_counter()
    test_results=checks()
    raw=[]
    for spec in scenarios():
        sound,controls=render(spec,p)
        raw.append((spec,sound,controls))
        print('Rendered',spec['id'],flush=True)
    peak=max(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))) for _,x,_ in raw)
    gain=10**(p['maximum_pack_peak_dbfs']/20)/peak
    report=dict(profile=p,profile_sha256=hashlib.sha256(args.profile.read_bytes()).hexdigest(),
                renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                procedural_only=True,recordings_used=False,in_game_integrated=False,
                control_source='Authored audition traces, not captured vehicle telemetry',
                output_format='48 kHz / stereo / 16-bit PCM WAV',shared_gain=float(gain),
                checks=test_results,clips=[])
    for spec,x,controls in raw:
        x*=gain
        m=metrics(x,p['sample_rate'])
        assert m['finite'] and m['clipped_samples']==0 and m['true_peak_dbfs']<=-5.95
        assert max(abs(v) for v in m['dc_offset'])<.0002
        assert abs(controls['firing_count']-controls['expected_firing_count'])<=1
        path=args.out/(spec['id']+'.wav')
        write_wav(path,x,p['sample_rate'])
        rate,decoded=wavfile.read(path)
        assert rate==48000 and decoded.shape==x.shape and decoded.dtype==np.int16
        (args.out/(spec['id']+'.controls.json')).write_text(json.dumps(controls))
        report['clips'].append(dict(id=spec['id'],title=spec['title'],notes=spec['notes'],file=path.name,**m))
    # Concise overview with explicit source ranges, silence between excerpts.
    excerpts=[(0,0,6),(1,2,14),(2,1,11),(3,4,11)]
    overview=[];chapters=[];cursor=0
    for index,a,b in excerpts:
        spec,x,_=raw[index];excerpt=x[round(a*48000):round(b*48000)].copy()
        ramp=np.sin(np.linspace(0,np.pi/2,2400))**2
        excerpt[:2400]*=ramp[:,None];excerpt[-2400:]*=ramp[::-1,None]
        chapters.append(dict(start_s=cursor,end_s=cursor+b-a,source=spec['id'],source_start_s=a,source_end_s=b))
        overview.extend([excerpt,np.zeros((24000,2))]);cursor+=b-a+.5
    preview=np.concatenate(overview)
    write_wav(args.out/'00_listening_overview.wav',preview,48000)
    report['overview']=dict(file='00_listening_overview.wav',chapters=chapters,**metrics(preview,48000))
    # Controlled timbre comparison: same RPM and equal RMS, unlike the natural
    # driving clips. Keep an explicit record of these diagnostic-only gains.
    comparison=[];states=[]
    source=raw[2][1]
    for name,a,b in [('light',1,3.5),('loaded',5,7.5),('overrun',10,12.5)]:
        segment=source[int(a*48000):int(b*48000)].copy()
        rms=float(np.sqrt(np.mean(segment*segment)))
        f,power=signal.welch(np.mean(segment,axis=1),48000,nperseg=16384)
        states.append(dict(state=name,source_start_s=a,source_end_s=b,natural_rms_dbfs=db(rms),
                           diagnostic_gain=.055/rms,centroid_hz=float(np.sum(f*power)/np.sum(power)),
                           upper_to_bass_db=float(10*np.log10(power[(f>500)&(f<4000)].sum()/power[(f>40)&(f<300)].sum()))))
        segment*=.055/rms
        segment[:2400]*=ramp[:,None];segment[-2400:]*=ramp[::-1,None]
        comparison.extend([segment,np.zeros((24000,2))])
    comparison=np.concatenate(comparison)
    write_wav(args.out/'05_load_tone_volume_matched.wav',comparison,48000)
    report['load_tone_comparison']=dict(file='05_load_tone_volume_matched.wav',
        note='Light / loaded / overrun, each 2.5 s with 0.5 s gaps; equal RMS before fades, not perceptual LUFS matching.',
        states=states,**metrics(comparison,48000))
    assert report['load_tone_comparison']['true_peak_dbfs']<-5.95
    assert states[1]['centroid_hz']>states[0]['centroid_hz']*1.1,'Load colour still too similar to light throttle'
    report['render_wall_seconds']=time.perf_counter()-start
    report['performance_note']='Offline NumPy/SciPy renderer with JIT, not Unreal real-time performance evidence.'
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2))
    (args.out/'profile.json').write_text(json.dumps(p,indent=2))
    guide='''RANGE ROVER PROCEDURAL V8 - FIRST LISTENING PROTOTYPE

All sound is generated mathematically. No engine recordings, sample libraries,
AI audio model or third-party sound assets are used. This is a V8 archetype for
the game car, not an exact historical-engine recreation. No in-game integration.

Start with 00_listening_overview.wav (37 seconds):
0-6 s: idle/blip; 6.5-18.5 s: acceleration/shifts;
19-29 s: fixed RPM/load changes; 29.5-36.5 s: low-range effort.

Full clips:
01_idle_and_blips.wav: 18 s. Idle, then blips at about 4, 8 and 12 seconds.
02_acceleration_shifts_lift.wav: 24 s. Shifts near 7/12 s, lift at 17.5 s.
03_same_rpm_load.wav: 14 s. 2500 RPM: light 0-4 s, loaded 4.3-9 s,
  overrun 9.3-14 s. These natural changes retain their volume differences.
04_low_range_effort.wav: 16 s. Loaded engine sags, recovers, then unloads.
05_load_tone_volume_matched.wav: 9 s. Light / loaded / overrun at 2500 RPM,
  2.5 s each with gaps. Each segment is equal-RMS for tone comparison only.

The overview and clips 01-04 share one gain; peak is capped at -6 dBFS.
48 kHz stereo 16-bit PCM WAV. The very narrow stereo comes from the two banks.
Traces are authored listening scenarios, not captured driving telemetry.
No tyres, wind, gear clunks, starter, explosions or gravel mask the engine here.

Listen for: believable idle; enough V8 weight; natural rev changes; smooth
shifts/lift-off; load changing tone as well as volume; any synthetic buzzing,
whistling, clicks or tiring drone. Choose the desired character before rollout.

Reproduce using Saved/Tools/TerrainPython/Scripts/python.exe
Art/tools/render_range_rover_audio.py --out <a new output directory>.
Profile: Art/Audio/range_rover_v8_prototype.json.
manifest.json contains metrics, source hashes and chapter timings.
'''
    (args.out/'LISTENING_GUIDE.txt').write_text(guide)
    with zipfile.ZipFile(args.out/'RangeRover_procedural_v1_samples.zip','w',zipfile.ZIP_DEFLATED) as z:
        for file in sorted(args.out.iterdir()):
            if file.suffix in ('.wav','.json','.txt'):z.write(file,file.name)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
