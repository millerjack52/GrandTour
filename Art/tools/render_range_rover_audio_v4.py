"""Focused offline mid/high-RPM correction, retaining the v3 sound at low RPM.

Keeps all prior prototypes intact. The new voice is an audition, not an assertion
of naturalness. Uses the existing passive network with a less resonant geometry.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import zipfile
import numpy as np
from numba import njit
from scipy import signal
from scipy.io import wavfile
import render_range_rover_audio_v3 as v3

v1 = v3.v1
ROOT = v3.ROOT


@njit(cache=True)
def source(rpm, charge, noise, sr, gains, texture, seed):
    n=len(rpm)
    coherent=np.zeros((8,n));turbulent=np.zeros((8,n));intake=np.zeros(n)
    phase=0.;count=0;memory=np.zeros(8)
    times=np.empty(int(n/sr*400)+16)
    random_state=np.uint32(seed)
    for i in range(n):
        step=rpm[i]/120*8/sr;phase+=step
        if phase<1:continue
        phase-=1;fraction=phase/step;c=count%8
        times[count]=(i-fraction)/sr;count+=1
        random_state=np.uint32(1664525*random_state+1013904223)
        random=float(random_state)/4294967296.*2-1
        memory[c]=.58*memory[c]+.42*random
        effort=max(charge[i],0.);overrun=max(-charge[i],0.)
        amplitude=(.17+.83*effort**.7)*gains[c]*(1+.16*memory[c]+.035*random)
        if overrun>0:amplitude*=.32
        width=1+.18*memory[c]
        attack=(.00038-.00015*effort)*width
        decay=(.0018-.0004*effort)*width
        angular=rpm[i]*6
        duration=min(.075,255/angular)
        for j in range(min(int(duration*sr),n-i)):
            age=(j+fraction)/sr;angle=age*angular
            valve=math.sin(math.pi*min(angle/255,1.))**2
            blow=math.exp(-age/decay)-math.exp(-age/attack)
            recovery=.22*(1-math.exp(-age/.0007))*math.exp(-age/.0052)
            # No repeated sinusoidal chirp in the pressure pulse.
            coherent[c,i+j]+=amplitude*(blow-recovery+.19*valve*math.exp(-angle/150))
            k=(i+j+c*7919)%n
            flow=.46*noise[0,k]+.45*noise[1,k]+.09*noise[2,k]
            burst=.30*noise[0,k]+.49*noise[1,k]+.21*noise[2,k]
            turbulent[c,i+j]+=amplitude*texture*(.65*math.sqrt(max(blow,0))*burst+.62*valve*flow)
            turbulent[c,i+j]+=(.009+.028*overrun)*valve*flow
        delay=int(210/angular*sr);duration=int(175/angular*sr)
        for j in range(min(duration,max(0,n-i-delay))):
            w=math.sin(math.pi*j/max(1,duration))**2;k=i+delay+j
            intake[k]+=(.025+.23*effort)*w*(.78*noise[1,(k+c*3253)%n]+.22*noise[2,(k+c*3253)%n])
    return coherent,turbulent,intake,times[:count]


def new_voice(spec,p,revision):
    sr=p['sample_rate']*p['oversampling'];t=np.arange(round(spec['seconds']*sr))/sr
    rng=np.random.default_rng(p['seed']);rpm=v1.curve(t,spec['rpm']);load=v1.curve(t,spec['load'])
    charge=v3.follow(load,sr,.065,.12)
    slow=v1.filtered(rng.standard_normal(len(t)),sr,4,'lowpass')
    slow/=max(np.std(slow),1.e-9)
    actual=np.clip(rpm+slow*(2+6*np.clip((1300-rpm)/500,0,1)),1,p['maximum_rpm'])
    bands=[]
    for band in ([65,360],[360,1700],[1700,5500]):
        x=v1.filtered(rng.standard_normal(len(t)),sr,band,'bandpass')
        bands.append(x/max(np.std(x),1.e-9))
    noise=np.array(bands)
    coherent,turbulent,intake,times=source(actual,charge,noise,sr,np.array(p['cylinder_gains']),revision['texture_amount'],p['seed'])
    # Reduce narrow harmonics before adding independently shaped flow texture.
    low=v1.filtered(coherent.T,sr,revision['coherent_lowpass_hz'],'lowpass').T
    ports=low+revision['coherent_high_gain']*(coherent-low)+turbulent
    tubes=v3.network(ports,p,sr)
    # Avoid the additional upper harmonics from the old outlet saturation stage.
    outlet=.95*tubes[0]
    body=v1.filtered(coherent.sum(axis=0),sr,[38,195],'bandpass')
    intake=v1.filtered(intake,sr,[120,2100],'bandpass')
    common=p['body_gain']*body+p['intake_gain']*intake
    a,b=revision['manifold_mix']
    x=np.column_stack((outlet+a*tubes[1]+b*tubes[2]+common,
                       outlet+b*tubes[1]+a*tubes[2]+common))
    result=v3.finish(x,sr)
    assert abs(len(times)-float(np.sum(actual)/sr/120*8))<=1
    return result,dict(firing_count=len(times),expected_firing_count=float(np.sum(actual)/sr/120*8))


def blend(old,new,rpm,revision):
    amount=np.clip((rpm-revision['blend_start_rpm'])/(revision['blend_end_rpm']-revision['blend_start_rpm']),0,1)
    amount=amount*amount*(3-2*amount)
    return old*(1-amount[:,None])+new*amount[:,None],amount


def tone_measure(x,sr,rpm):
    f,power=signal.welch(np.mean(x,axis=1),sr,nperseg=32768)
    band=(f>=250)&(f<2500)
    # Broad +/-3 Hz masks around 720-degree-cycle orders, not a realism score.
    cycle=rpm/120
    distance=np.abs(f-cycle*np.round(f/cycle))
    tonal=band&(distance<3)
    return dict(order_band_energy_fraction=float(power[tonal].sum()/max(power[band].sum(),1.e-20)),
        mid_to_bass_db=float(10*np.log10(power[band].sum()/max(power[(f>=35)&(f<200)].sum(),1.e-20))))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'Art/Export/VehicleAudio/RangeRover_Procedural_v4_review')
    args=parser.parse_args()
    if args.out.exists():raise SystemExit('Preserving existing output; choose a fresh --out folder.')
    preset=ROOT/'Art/Audio/range_rover_v8_prototype_v4.json';revision=json.loads(preset.read_text())
    basepath=ROOT/revision['base_profile'];base=json.loads(basepath.read_text());p=base.copy()
    p.update({k:v for k,v in revision.items() if k in p})
    checks={k:v for k,v in v3.checks(p).items() if k.startswith('network_')}
    sr=48000
    spec=dict(id='mid_high',seconds=20,
        rpm=[(0,1800),(1,2400),(5,2400),(6,3200),(10,3200),(11,4200),(15,4200),(15.2,4100),(18,2000),(20,1000)],
        load=[(0,.35),(1,.8),(5,.8),(6,.86),(10,.86),(11,.88),(15,.88),(15.3,-.3),(18,-.15),(20,.1)])
    old,controls,_=v3.render(spec,base)
    print('Rendered v3 baseline on new control trace',flush=True)
    new,new_controls=new_voice(spec,p,revision)
    rpm=v1.curve(np.arange(len(old))/sr,spec['rpm'])
    revised,amount=blend(old,new,rpm,revision)
    # Values at/below the boundary are exactly the old voice before shared gain.
    assert np.array_equal(revised[rpm<=1700],old[rpm<=1700])
    assert np.isfinite(revised).all()
    checks['low_rpm_mix_preserved']=True
    n=sr
    _,_,_,fires=source(np.full(n,4200.),np.full(n,.8),np.zeros((3,n)),sr,np.ones(8),0,1084)
    assert abs(len(fires)-280)<=1 and np.max(np.abs(np.diff(fires)-1/280))<1.e-8
    checks['v4_high_rpm_firing_timing']=True
    args.out.mkdir(parents=True)
    sources=[Path(__file__),Path(v3.__file__),Path(v1.__file__),Path(v3.v2.__file__),preset,basepath]
    report=dict(version=4,procedural_only=True,recordings_used=False,in_game_integrated=False,
        description='Focused 2400/3200/4200 RPM audition; v3 voice retained below blend threshold.',
        limitations='No measured reference fit, perceptual approval or runtime performance claim.',
        checks=checks,files=[],base_profile=base,revision=revision,scenario=spec,
        source_hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources})
    def save(name,x,**details):
        assert np.isfinite(x).all() and np.max(np.abs(x))<1
        path=args.out/(name+'.wav');v1.write_wav(path,x,sr)
        rate,decoded=wavfile.read(path);assert rate==sr and decoded.dtype==np.int16
        metrics=v1.metrics(decoded.astype(float)/32768,sr)
        assert metrics['true_peak_dbfs']<=-5.94 and metrics['clipped_samples']==0
        assert max(abs(v) for v in metrics['dc_offset'])<.0002
        report['files'].append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**metrics,**details))
    gain=10**(-6/20)/max(float(np.max(np.abs(signal.resample_poly(x,4,1,axis=0)))) for x in [old,revised])
    save('00_mid_high_revision',revised*gain)
    save('01_v3_same_drive_reference',old*gain)
    parts=[];measurements=[]
    for start,end,r in [(1,5,2400),(6,10,3200),(11,15,4200)]:
        for label,x in [('v3',old),('v4',revised)]:
            segment=x[start*sr:end*sr];parts.append(segment)
            measurements.append(dict(version=label,rpm=r,**tone_measure(segment,sr,r)))
    ab,matching=v3.comparison(parts)
    save('02_v3_then_v4_mid_high_comparison',ab,matching=matching,
        order=['v3 2400','v4 2400','v3 3200','v4 3200','v3 4200','v4 4200'])
    report['spectral_diagnostics']=measurements
    report['shared_gain']=gain
    controls['v4_firing']=new_controls
    controls['v4_blend']=amount[::sr//100].tolist()
    (args.out/'controls.json').write_text(json.dumps(controls))
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2))
    (args.out/'profile.json').write_text(json.dumps(dict(base=base,revision=revision),indent=2))
    (args.out/'LISTENING_GUIDE.txt').write_text('''RANGE ROVER V4 - FOCUSED MID/HIGH REV AUDITION

00_mid_high_revision.wav (20 s): 2400 RPM at 1-5 s, 3200 at 6-10 s,
4200 at 11-15 s, then lift-off. 01 is V3 on the exact same authored drive.
These full takes share one output gain.

02 comparison (27 s): V3 then V4 at each speed, four-second segments.
0-4 / 4.5-8.5: 2400 RPM; 9-13 / 13.5-17.5: 3200 RPM;
18-22 / 22.5-26.5: 4200 RPM. Gaps are half a second.
Comparison uses matched K-weighted segment energy, not a full gated LUFS meter.

V4 removes the repeated blowdown chirp, softens coherent upper harmonics before
adding flow texture, reduces chamber impedance jumps/reflections and reduces
the direct manifold contribution. No outlet saturation stage. The revised
voice blends in from 1700 to 3200 RPM; below 1700 it is exactly the V3 signal
before shared output gain. This focuses the change on the reported problem.

Entirely procedural. No recordings or measured acoustic reference fitted.
Network/source diagnostics cannot prove naturalness. Listen for synthetic
buzz, overly smooth tones, excessive hiss or a loss of V8 identity.
No game edits or Unreal launch; prior sources and samples preserved.

Reproduce: Saved/Tools/TerrainPython/Scripts/python.exe
Art/tools/render_range_rover_audio_v4.py --out <fresh folder>.
''')
    with zipfile.ZipFile(args.out/'RangeRover_procedural_v4_samples.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(args.out.iterdir()):
            if path.suffix in ('.wav','.json','.txt'):z.write(path,path.name)
    print(json.dumps(dict(checks=checks,spectral_diagnostics=measurements,files=[f['file'] for f in report['files']]),indent=2))


if __name__=='__main__':main()
