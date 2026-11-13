"""Second offline V8 audition. Preserves v1 source/audio; never starts Unreal.

Uses v1's authored driving traces and analysis/file utilities, with a new
combustion and acoustic renderer. No recordings or learned audio model.
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
from scipy.io import wavfile
import render_range_rover_audio as v1

ROOT = v1.ROOT


@njit(cache=True)
def combustion(rpm, load, slow, sr, banks, gains, attack_ms, decay_ms,
               attack_reduction, decay_reduction, width_variation, texture):
    out = np.zeros((2,len(rpm)))
    phase = 0.0
    count = 0
    random_state = np.uint32(42184)
    kernel_n = int(.030*sr)
    grain_a = 1-math.exp(-2*math.pi*1500/sr)
    for i in range(len(rpm)):
        step = rpm[i]/120*8/sr
        phase += step
        if phase < 1:
            continue
        phase -= 1
        fraction = phase/step
        cylinder = count % 8
        bank = banks[cylinder]
        effort = max(0.0,load[i])
        random_state = np.uint32(1664525*random_state+1013904223)
        variation = float(random_state)/4294967296.0*2-1
        random_state = np.uint32(1664525*random_state+1013904223)
        width_random = float(random_state)/4294967296.0*2-1
        amplitude = (.18+.78*effort**.70)*gains[cylinder]
        # Healthy cylinder variation, not random misfires or exaggerated cam lope.
        amplitude *= 1+variation*(.095 if rpm[i]<1300 else .050)+.022*slow[i]
        if load[i]<0:
            amplitude *= .60
        width = 1+width_variation*width_random
        attack = (attack_ms-attack_reduction*effort)*.001*width
        decay = (decay_ms-decay_reduction*effort)*.001*width
        tail = .0062*(1+.035*variation)
        grain = 0.0
        for j in range(min(kernel_n,len(rpm)-i)):
            age = (j+fraction)/sr
            pulse = (1-math.exp(-age/attack))*(math.exp(-age/decay)-(decay/tail)*math.exp(-age/tail))
            random_state = np.uint32(1664525*random_state+1013904223)
            noise = float(random_state)/4294967296.0*2-1
            grain += grain_a*(noise-grain)
            # Turbulence belongs to each pressure event, not a constant hiss bed.
            out[bank,i+j] += amplitude*pulse*(1+texture*grain*3.0)
        count += 1
    return out,count


def render(spec,p):
    sr=p['sample_rate']*p['oversampling']
    t=np.arange(round(spec['seconds']*sr))/sr
    rng=np.random.default_rng(p['seed'])
    rpm=v1.curve(t,spec['rpm']);load=v1.curve(t,spec['load'])
    slow=v1.filtered(rng.standard_normal(len(t)),sr,5,'lowpass')
    slow/=max(np.std(slow),1.e-9)
    idle=np.clip((1300-rpm)/500,0,1)
    actual_rpm=np.clip(rpm+slow*(2.5+idle*7),0,p['maximum_rpm'])
    effort=np.maximum(load,0)
    pressure,count=combustion(actual_rpm,load,slow,sr,np.array(p['firing_banks']),
        np.array(p['cylinder_gains']),p['pulse_attack_ms'],p['pulse_decay_ms'],
        p['loaded_attack_reduction_ms'],p['loaded_decay_reduction_ms'],
        p['pulse_width_variation'],p['combustion_texture'])
    cutoff=p['exhaust_lowpass_idle_hz']+p['exhaust_lowpass_loaded_hz']*effort+.08*rpm
    exhaust=[]
    for bank in range(2):
        x=v1.delay_signal(pressure[bank],round(p['bank_delay_ms'][bank]*sr/1000))
        x=v1.pipe(x,cutoff,round(p['exhaust_echo_ms'][bank]*sr/1000),p['exhaust_feedback'],sr)
        # Lower, broader body modes and weaker pipe feedback reduce the old
        # ringing/organ quality. Do not pitch-shift the engine below its RPM.
        x+=.46*v1.resonant(x,sr,78+bank*13,.65)+.12*v1.resonant(x,sr,185+bank*25,.7)
        exhaust.append(np.tanh(x*(1.2+.75*effort))/1.65)
    exhaust=np.array(exhaust)
    crank=np.cumsum(actual_rpm/60/sr)*2*np.pi
    intake=v1.filtered(rng.standard_normal(len(t)),sr,[110,1900],'bandpass')
    intake*= (.020+.11*effort**1.25)*(.6+.4*(.5+.5*np.sin(4*crank+.7)))
    intake+=.09*v1.filtered(pressure[0]+pressure[1],sr,[160,1000],'bandpass')
    mechanical=v1.filtered(rng.standard_normal(len(t)),sr,[350,2800],'bandpass')
    mechanical*= (.017+.023*np.sqrt(rpm/5000))*(.65+.35*(.5+.5*np.sin(2*crank)))
    # Low engine orders are derived mainly from unequal exhaust-bank response.
    # A very small crank-order vibration supplies structure-borne engine weight.
    body=v1.filtered(.68*pressure[0]+.32*pressure[1],sr,[32,200],'bandpass')
    body+= (.006+.008*effort)*np.sin(2*crank+.25)*(1+.08*slow)
    mid=p['intake_gain']*intake+p['mechanical_gain']*mechanical+p['body_gain']*body
    stereo=np.column_stack((p['exhaust_gain']*(.65*exhaust[0]+.35*exhaust[1])+mid,
                            p['exhaust_gain']*(.52*exhaust[0]+.48*exhaust[1])+mid))
    stereo=v1.filtered(stereo,sr,27,'highpass')
    stereo=v1.filtered(stereo,sr,5000,'lowpass')
    stereo=signal.resample_poly(stereo,1,p['oversampling'],axis=0)
    fade=round(.10*p['sample_rate']);ramp=np.sin(np.linspace(0,np.pi/2,fade))**2
    stereo[:fade]*=ramp[:,None];stereo[-fade:]*=ramp[::-1,None]
    controls=dict(time_s=t[::int(sr/100)].tolist(),rpm=actual_rpm[::int(sr/100)].tolist(),
        load=load[::int(sr/100)].tolist(),firing_count=count,
        expected_firing_count=float(np.sum(actual_rpm)/sr/120*8))
    assert abs(count-controls['expected_firing_count'])<=1
    return stereo,controls


def colour(x,sr):
    f,p=signal.welch(np.mean(x,axis=1),sr,nperseg=16384)
    return dict(centroid_hz=float(np.sum(f*p)/np.sum(p)),
        bass_to_mid_db=float(10*np.log10(p[(f>=35)&(f<180)].sum()/p[(f>=400)&(f<2500)].sum())))


def join(parts):
    output=[]
    for x in parts:
        x=x.copy();ramp=np.sin(np.linspace(0,np.pi/2,2400))**2
        x[:2400]*=ramp[:,None];x[-2400:]*=ramp[::-1,None]
        output.extend([x,np.zeros((24000,2))])
    return np.concatenate(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,default=ROOT/'Art/Audio/range_rover_v8_prototype_v2.json')
    parser.add_argument('--out',type=Path,default=ROOT/'Art/Export/VehicleAudio/RangeRover_Procedural_v2_review')
    args=parser.parse_args()
    if args.out.exists():raise SystemExit('Preserving existing output. Choose a fresh --out directory.')
    p=json.loads(args.profile.read_text());assert p['sample_rate']==48000 and p['oversampling']==2
    assert 0<=p['exhaust_feedback']<.8
    assert p['pulse_attack_ms']>p['loaded_attack_reduction_ms']>0
    assert p['pulse_decay_ms']>p['loaded_decay_reduction_ms']>0
    args.out.mkdir(parents=True)
    started=time.perf_counter();raw=[]
    validation=v1.checks()
    for spec in v1.scenarios():
        x,controls=render(spec,p);raw.append((spec,x,controls))
        print('Rendered',spec['id'],flush=True)
    peak=max(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))) for _,x,_ in raw)
    gain=10**(p['maximum_pack_peak_dbfs']/20)/peak
    report=dict(version=2,profile=p,procedural_only=True,in_game_integrated=False,
        source='Authored traces identical to v1; no recordings, no learned audio model',
        checks=validation,shared_gain=float(gain),clips=[],
        source_hashes={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in [Path(__file__),Path(v1.__file__),args.profile]})
    for spec,x,controls in raw:
        x*=gain;m=v1.metrics(x,48000)
        assert m['finite'] and m['clipped_samples']==0 and m['true_peak_dbfs']<=-5.95
        assert max(abs(v) for v in m['dc_offset'])<.0002
        f=args.out/(spec['id']+'.wav');v1.write_wav(f,x,48000)
        sr,decoded=wavfile.read(f);assert sr==48000 and decoded.shape==x.shape
        (args.out/(spec['id']+'.controls.json')).write_text(json.dumps(controls))
        report['clips'].append(dict(id=spec['id'],notes=spec['notes'],**m))
    preview=join([raw[i][1][a*48000:b*48000] for i,a,b in [(0,0,6),(1,2,14),(2,1,11),(3,4,11)]])
    v1.write_wav(args.out/'00_deeper_v8_overview.wav',preview,48000)
    report['overview']=v1.metrics(preview,48000)
    # Same input scenarios and equal segment RMS for before/after tone judgement.
    reference=ROOT/'Art/Export/VehicleAudio/RangeRover_Procedural_v1_review'
    ab=[];comparisons=[]
    for i,a,b,label in [(0,0,6,'idle and blip'),(1,3,9,'loaded pull')]:
        sr,old=wavfile.read(reference/(raw[i][0]['id']+'.wav'));assert sr==48000
        old=old.astype(float)/32768
        pair=[]
        for version,x in [('v1',old[a*48000:b*48000]),('v2',raw[i][1][a*48000:b*48000])]:
            level=float(np.sqrt(np.mean(x*x)))
            comparisons.append(dict(scene=label,version=version,**colour(x,48000),rms_matching_gain=.055/level))
            pair.append(x*(.055/level))
        ab.extend(pair)
    comparison=join(ab)
    comparison_peak=float(np.max(np.abs(signal.resample_poly(comparison,4,1,axis=0))))
    comparison_gain=min(1.,10**(-6.05/20)/comparison_peak)
    comparison*=comparison_gain
    for row in comparisons:row['rms_matching_gain']*=comparison_gain
    v1.write_wav(args.out/'05_v1_then_v2_comparison.wav',comparison,48000)
    report['before_after']=dict(order='v1 idle/blip, v2 idle/blip, v1 loaded pull, v2 loaded pull; 6 s each, 0.5 s gaps',
        matching='Equal segment RMS before fades, not perceptual LUFS matching',measurements=comparisons,**v1.metrics(comparison,48000))
    assert report['before_after']['true_peak_dbfs']<-5.95
    assert comparisons[1]['bass_to_mid_db']>comparisons[0]['bass_to_mid_db']+2
    assert comparisons[3]['bass_to_mid_db']>comparisons[2]['bass_to_mid_db']+2
    report['offline_render_seconds']=time.perf_counter()-started
    report['limitations']='Not audition-approved; offline signal metrics do not prove naturalness or Unreal runtime cost.'
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2))
    (args.out/'profile.json').write_text(json.dumps(p,indent=2))
    (args.out/'LISTENING_GUIDE.txt').write_text('''RANGE ROVER V8 - PROCEDURAL V2

Requested changes: deeper V8 rumble and less synthetic engine texture.
Changes: softer, longer pressure pulses; variable event strength/width; generated
combustion turbulence; lower broad exhaust resonances with less ringing feedback;
stronger bank-derived low-frequency body; less pure mechanical sine tone.
No recorded engine sounds, external audio assets or machine-learning audio model.

00_deeper_v8_overview.wav (37 seconds):
0-6 idle/blip; 6.5-18.5 acceleration/shifts; 19-29 load; 29.5-36.5 low-range effort.
The four full scenario clips are the same authored driving traces as v1.
The natural scenario clips share one gain and a -6 dBFS true-peak ceiling.

05_v1_then_v2_comparison.wav (26 seconds):
0-6 old idle/blip; 6.5-12.5 new idle/blip;
13-19 old loaded pull; 19.5-25.5 new loaded pull.
Segments use equal RMS for comparison, not full perceptual loudness matching.

Still an offline listening prototype: no game code, mute setting or physics was
changed. Evaluate V8 weight, combustion texture, synthetic buzzing and drone.
Signal checks cannot judge realism; owner listening is the acceptance gate.

Reproduce: Saved/Tools/TerrainPython/Scripts/python.exe
Art/tools/render_range_rover_audio_v2.py --out <fresh output directory>.
''')
    with zipfile.ZipFile(args.out/'RangeRover_procedural_v2_samples.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for f in sorted(args.out.iterdir()):
            if f.suffix in ('.wav','.json','.txt'):archive.write(f,f.name)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
