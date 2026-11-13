"""Offline V8 audition: crank-phase gas events and a passive exhaust tube network.

Research-informed sound design, not a calibrated thermodynamic simulation.
Preserves v1/v2 and refuses to replace an existing output folder. No Unreal use.
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
import render_range_rover_audio as v1
import render_range_rover_audio_v2 as v2

ROOT = v1.ROOT


@njit(cache=True)
def follow(x, sr, rise, fall):
    out = np.empty(len(x))
    state = x[0]
    for i in range(len(x)):
        tau = rise if x[i] > state else fall
        state += (1-math.exp(-1/(sr*tau)))*(x[i]-state)
        out[i] = state
    return out


@njit(cache=True)
def events(rpm, charge, fuel_cut, noise, sr, gains, texture, seed):
    """Continuous 720-degree cycle; cylinder slots are in firing sequence order.

    Exhaust opening is the event origin. Blowdown has a rapid pressure transient;
    piston discharge and intake windows use crank angle. Noise follows flow.
    fuel_cut is explicit; negative load alone never declares fuel cutoff.
    """
    n = len(rpm)
    ports = np.zeros((8, n))
    intake = np.zeros(n)
    mechanical = np.zeros(n)
    phase = 0.0
    count = 0
    times = np.empty(int(n/sr*400)+16)
    strength_memory = np.zeros(8)
    random_state = np.uint32(seed)
    for i in range(n):
        step = rpm[i]/120*8/sr
        phase += step
        if phase < 1:
            continue
        phase -= 1
        fraction = phase/step
        c = count % 8
        times[count] = (i-fraction)/sr
        count += 1
        random_state = np.uint32(1664525*random_state+1013904223)
        variation = float(random_state)/4294967296.0*2-1
        strength_memory[c] = .68*strength_memory[c]+.32*variation
        effort = max(charge[i], 0.)
        overrun = max(-charge[i], 0.)
        combustion = 1-fuel_cut[i]
        amplitude = (.17+.83*effort**.7)*gains[c]
        amplitude *= 1+.12*strength_memory[c]+.025*variation
        if overrun > 0:
            amplitude *= .32
        amplitude *= combustion
        width = 1+.13*strength_memory[c]+.03*variation
        attack = (.00030-.00014*effort)*width
        decay = (.00165-.00065*effort)*width
        # Degrees per second, not one fixed-length noise burst across all RPM.
        angular_speed = rpm[i]*6
        duration = min(.075, 255/angular_speed)
        for j in range(min(int(duration*sr), n-i)):
            age = (j+fraction)/sr
            angle = age*angular_speed
            valve = math.sin(math.pi*min(angle/255, 1.0))**2
            blowdown = math.exp(-age/decay)-math.exp(-age/attack)
            recovery = .22*(1-math.exp(-age/.0007))*math.exp(-age/.0052)
            # A short dispersive transient, deliberately damped within milliseconds.
            bent_phase = 2*math.pi*(190*age+420*.0017*(1-math.exp(-age/.0017)))
            transient = .12*math.sin(bent_phase)*math.exp(-age/.0033)
            discharge = .19*valve*math.exp(-angle/150)
            k = (i+j+c*7919) % n
            flow_noise = .57*noise[0,k]+.33*noise[1,k]+.10*noise[2,k]
            burst_noise = .25*noise[0,k]+.45*noise[1,k]+.30*noise[2,k]
            textured = texture*(.60*math.sqrt(max(blowdown,0))*burst_noise + .55*valve*flow_noise)
            ports[c,i+j] += amplitude*(blowdown-recovery+transient+discharge+textured)
            # Pumping persists during fuel cut, but combustion does not.
            ports[c,i+j] += (.009+.028*overrun+.035*fuel_cut[i])*valve*flow_noise
        # Valve-seat/mechanical tick, separate radiation path from exhaust gas.
        for j in range(min(int(.004*sr),n-i)):
            age = (j+fraction)/sr
            mechanical[i+j] += (.014+.018*rpm[i]/5000)*noise[2,(i+j+c*3571)%n]*math.exp(-age/.0008)
        intake_delay = int(210/angular_speed*sr)
        intake_duration = int(175/angular_speed*sr)
        for j in range(min(intake_duration,max(0,n-i-intake_delay))):
            w = math.sin(math.pi*j/max(1,intake_duration))**2
            k = i+intake_delay+j
            intake[k] += (.025+.23*effort)*w*(.65*noise[1,(k+c*3253)%n]+.35*noise[2,(k+c*3253)%n])
    return ports, intake, mechanical, times[:count]


def geometry(p, sr):
    lengths = p['runner_length_m']+p['collector_length_m']+[p['silencer_length_m'],p['tailpipe_length_m']]
    types = np.array([0]*8+[1]*2+[2,3])
    speed = np.array(p['sound_speed_m_s'])[types]
    delays = np.maximum(2,np.rint(np.array(lengths)/speed*sr)).astype(np.int64)
    # Area proportional admittances; the common pi/4 factor cancels at junctions.
    admittance = np.array(p['diameters_m'])[types]**2
    loss = np.array(p['propagation_gain'])[types]
    cutoff = np.array(p['propagation_lowpass_hz'])[types]
    left = np.array([-1]*8+[0,1,2,3],dtype=np.int64)
    right = np.array(p['firing_banks']+[2,2,3,-1],dtype=np.int64)
    return delays,admittance,loss,cutoff,left,right


@njit(cache=True)
def exhaust_network(ports, sr, delays, admittance, loss, cutoff, left, right, source_r, outlet_r):
    """12 bidirectional waveguides, four pressure-continuous scattering junctions.

    Positive admittances make junction scattering passive. Each propagation path
    has attenuation and a one-pole lowpass. All terminations have |reflection|<1.
    No feedback waves are invented after the fact or added to the firing clock.
    """
    count = len(delays)
    forward = np.zeros((count,np.max(delays)))
    backward = np.zeros_like(forward)
    pos = np.zeros(count,dtype=np.int64)
    lp_f = np.zeros(count)
    lp_b = np.zeros(count)
    alpha = 1-np.exp(-2*np.pi*cutoff/sr)
    junction_y = np.zeros(4)
    for e in range(count):
        if left[e]>=0: junction_y[left[e]] += admittance[e]
        if right[e]>=0: junction_y[right[e]] += admittance[e]
    out = np.zeros((3,ports.shape[1]))
    incident_f = np.zeros(count)
    incident_b = np.zeros(count)
    for i in range(ports.shape[1]):
        junction = np.zeros(4)
        for e in range(count):
            incident_f[e] = forward[e,pos[e]]
            incident_b[e] = backward[e,pos[e]]
            if left[e]>=0: junction[left[e]] += admittance[e]*incident_b[e]
            if right[e]>=0: junction[right[e]] += admittance[e]*incident_f[e]
        junction *= 2/junction_y
        for e in range(count):
            send_f = ports[e,i]+source_r*incident_b[e] if left[e]<0 else junction[left[e]]-incident_b[e]
            send_b = outlet_r*incident_f[e] if right[e]<0 else junction[right[e]]-incident_f[e]
            lp_f[e] += alpha[e]*(send_f-lp_f[e])
            lp_b[e] += alpha[e]*(send_b-lp_b[e])
            forward[e,pos[e]] = loss[e]*lp_f[e]
            backward[e,pos[e]] = loss[e]*lp_b[e]
            pos[e] = (pos[e]+1) % delays[e]
        # Outlet volume-velocity proxy and the two manifold radiation proxies.
        out[0,i] = (1-outlet_r)*incident_f[11]
        out[1,i] = junction[0]
        out[2,i] = junction[1]
    return out


def network(ports,p,sr):
    return exhaust_network(ports,sr,*geometry(p,sr),p['source_reflection'],p['outlet_reflection'])


def finish(x,sr):
    x = v1.filtered(x,sr,29,'highpass')
    x = v1.filtered(x,sr,6500,'lowpass')
    x = signal.resample_poly(x,1,sr//48000,axis=0)
    ramp = np.sin(np.linspace(0,np.pi/2,4800))**2
    x[:4800] *= ramp[:,None]
    x[-4800:] *= ramp[::-1,None]
    return x


def render(spec,p,ablation=False):
    sr = p['sample_rate']*p['oversampling']
    t = np.arange(round(spec['seconds']*sr))/sr
    rng = np.random.default_rng(p['seed'])
    rpm = v1.curve(t,spec['rpm'])
    load = v1.curve(t,spec['load'])
    # Explicit authored state only; all standard review traces retain combustion.
    fuel_cut = v1.curve(t,spec['fuel_cut']) if 'fuel_cut' in spec else np.zeros(len(t))
    charge = follow(load,sr,.065,.12)
    slow = v1.filtered(rng.standard_normal(len(t)),sr,4,'lowpass')
    slow /= max(np.std(slow),1.e-9)
    actual_rpm = np.clip(rpm+slow*(2+6*np.clip((1300-rpm)/500,0,1)),1,p['maximum_rpm'])
    noise = []
    for band in ([65,360],[360,1700],[1700,5500]):
        x = v1.filtered(rng.standard_normal(len(t)),sr,band,'bandpass')
        noise.append(x/max(np.std(x),1.e-9))
    noise = np.array(noise)
    ports,intake,mechanical,times = events(actual_rpm,charge,fuel_cut,noise,sr,
        np.array(p['cylinder_gains']),p['texture_amount'],p['seed'])
    tubes = network(ports,p,sr)
    effort = np.maximum(charge,0)
    outlet = np.tanh(tubes[0]*(1.15+.5*effort))/1.3
    # No sub oscillator: body vibration comes from the combustion pressure itself.
    body = v1.filtered(ports.sum(axis=0),sr,[38,195],'bandpass')
    intake = v1.filtered(intake,sr,[120,2300],'bandpass')
    mechanical = v1.filtered(mechanical,sr,[550,4500],'bandpass')
    common = p['body_gain']*body+p['intake_gain']*intake+p['mechanical_gain']*mechanical
    stereo = np.column_stack((p['exhaust_gain']*(outlet+.13*tubes[1]+.06*tubes[2])+common,
                              p['exhaust_gain']*(outlet+.08*tubes[1]+.11*tubes[2])+common))
    result = finish(stereo,sr)
    controls = dict(time_s=t[::sr//100].tolist(),rpm=actual_rpm[::sr//100].tolist(),
        load=load[::sr//100].tolist(),charge=charge[::sr//100].tolist(),
        fuel_cut=fuel_cut[::sr//100].tolist(),firing_count=len(times),
        expected_firing_count=float(np.sum(actual_rpm)/sr/120*8))
    assert abs(controls['firing_count']-controls['expected_firing_count'])<=1
    variants = {}
    if ablation:
        # Same new source, old bank-filter path: isolates the exhaust replacement.
        banks = np.zeros((2,len(t)))
        for c,b in enumerate(p['firing_banks']): banks[b] += ports[c]
        old = []
        for b in range(2):
            x = v1.pipe(banks[b],430+1450*effort+.08*actual_rpm,round([.0091,.0113][b]*sr),.13,sr)
            x += .46*v1.resonant(x,sr,78+b*13,.65)+.12*v1.resonant(x,sr,185+b*25,.7)
            old.append(np.tanh(x*(1.2+.75*effort))/1.65)
        old = np.array(old)
        variants['new_source_old_exhaust'] = finish(np.column_stack((.65*old[0]+.35*old[1],.52*old[0]+.48*old[1])),sr)
        variants['new_source_new_exhaust'] = finish(np.column_stack((outlet+.13*tubes[1]+.06*tubes[2],outlet+.08*tubes[1]+.11*tubes[2])),sr)
    return result,controls,variants


def weighted_level(x):
    """48 kHz K-weighted segment energy; no gating or claimed LUFS compliance."""
    shelf = signal.lfilter([1.53512485958697,-2.69169618940638,1.19839281085285],
                          [1,-1.69065929318241,.73248077421585],x,axis=0)
    weighted = signal.lfilter([1,-2,1],[1,-1.99004745483398,.99007225036621],shelf,axis=0)
    return float(np.sqrt(np.mean(np.sum(weighted*weighted,axis=1))))


def comparison(parts):
    levels = [weighted_level(x) for x in parts]
    gains = [.055/max(v,1.e-10) for v in levels]
    x = v2.join([part*g for part,g in zip(parts,gains)])
    peak = float(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))))
    common = min(1,10**(-6.05/20)/peak)
    return x*common,dict(method='K-weighted whole-segment energy, before boundary fades; no loudness gating',
                         gains=[g*common for g in gains])


def checks(p):
    sr = 48000
    for value in p['propagation_gain']: assert 0 < value < 1
    assert abs(p['source_reflection']) < 1 and abs(p['outlet_reflection']) < 1
    assert min(p['diameters_m'])>0
    silence = network(np.zeros((8,sr)),p,sr)
    assert np.max(np.abs(silence))==0
    impulse = np.zeros((8,sr*2)); impulse[0,0]=1
    response = network(impulse,p,sr)
    assert np.isfinite(response).all()
    assert np.max(np.abs(response[:,-sr//2:]))<1.e-9
    assert np.max(np.abs(response))>0
    n=sr*2;rpm=np.full(n,2400.);load=np.full(n,.6)
    ports,_,_,times=events(rpm,load,np.zeros(n),np.zeros((3,n)),sr,np.ones(8),0,1084)
    assert abs(len(times)-320)<=1 and np.max(np.abs(np.diff(times)-1/160))<1.e-8
    off,_,_,_=events(rpm,load,np.ones(n),np.zeros((3,n)),sr,np.ones(8),0,1084)
    assert np.max(np.abs(off))==0 and np.max(np.abs(ports))>0
    return dict(network_zero_input_silent=True,network_impulse_decays=True,
                firing_timing=True,explicit_fuel_cut_removes_combustion=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,default=ROOT/'Art/Audio/range_rover_v8_prototype_v3.json')
    parser.add_argument('--out',type=Path,default=ROOT/'Art/Export/VehicleAudio/RangeRover_Procedural_v3_review')
    args=parser.parse_args()
    if args.out.exists(): raise SystemExit('Preserving existing output; choose a fresh --out folder.')
    p=json.loads(args.profile.read_text())
    assert p['sample_rate']==48000 and p['oversampling']==2
    assert len(p['runner_length_m'])==len(p['cylinder_gains'])==len(p['firing_banks'])==8
    validation=checks(p)
    args.out.mkdir(parents=True)
    raw=[];variants={}
    for i,spec in enumerate(v1.scenarios()):
        x,controls,stems=render(spec,p,ablation=(i==2))
        raw.append((spec,x,controls));variants.update(stems)
        print('Rendered',spec['id'],flush=True)
    gain=10**(-6/20)/max(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))) for _,x,_ in raw)
    report=dict(version=3,procedural_only=True,recordings_used=False,in_game_integrated=False,
        limitations='Uncalibrated physical approximations; no listening approval or runtime-performance claim.',
        checks=validation,profile=p,shared_gain=float(gain),files=[],
        source_hashes={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in [Path(__file__),Path(v1.__file__),Path(v2.__file__),args.profile]})

    def save(name,x,**details):
        assert np.isfinite(x).all() and np.max(np.abs(x))<1
        path=args.out/(name+'.wav');v1.write_wav(path,x,48000)
        sr,decoded=wavfile.read(path)
        assert sr==48000 and decoded.dtype==np.int16 and decoded.shape==x.shape
        m=v1.metrics(decoded.astype(float)/32768,sr)
        assert m['finite'] and m['clipped_samples']==0 and m['true_peak_dbfs']<=-5.94
        assert max(abs(v) for v in m['dc_offset'])<.0002
        report['files'].append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**m,**details))

    for spec,x,controls in raw:
        x*=gain
        save(spec['id'],x,notes=spec['notes'])
        (args.out/(spec['id']+'.controls.json')).write_text(json.dumps(controls))
    overview=v2.join([raw[i][1][a*48000:b*48000] for i,a,b in [(0,0,6),(1,2,14),(2,1,11),(3,4,11)]])
    save('00_v8_combustion_exhaust_overview',overview)
    parts=[];order=[]
    for i,a,b,label in [(0,0,6,'idle/blip'),(1,3,9,'loaded acceleration'),(1,17,23,'lift-off')]:
        oldpath=ROOT/'Art/Export/VehicleAudio/RangeRover_Procedural_v2_review'/(raw[i][0]['id']+'.wav')
        sr,old=wavfile.read(oldpath);assert sr==48000
        parts.extend([old[a*sr:b*sr].astype(float)/32768,raw[i][1][a*sr:b*sr]])
        order.extend(['v2 '+label,'v3 '+label])
    comp,matching=comparison(parts)
    save('05_v2_then_v3_comparison',comp,order=order,matching=matching)
    # Hold 2500 RPM and high load constant, isolate only the acoustic path change.
    comp,matching=comparison([variants[k][5*48000:9*48000] for k in ['new_source_old_exhaust','new_source_new_exhaust']])
    save('06_exhaust_model_comparison',comp,order=['v3 source with v2-style exhaust','same v3 source with waveguide exhaust'],matching=matching)
    (args.out/'profile.json').write_text(json.dumps(p,indent=2))
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2))
    (args.out/'LISTENING_GUIDE.txt').write_text('''RANGE ROVER PROCEDURAL V3 - OFFLINE AUDITION

00 overview (37 s): 0-6 idle/blip; 6.5-18.5 acceleration/shifts;
19-29 fixed-RPM load changes; 29.5-36.5 low-range effort.
01-04: full scenarios, the same authored RPM/load traces as prior versions.
05 comparison (39 s): v2 then v3 for each scene.
0-6 / 6.5-12.5 idle/blip; 13-19 / 19.5-25.5 acceleration;
26-32 / 32.5-38.5 lift-off. Half-second gaps between segments.
06 exhaust comparison (9 s): same v3 pressure source at 2500 RPM under load,
0-4 old-style bank filtering; 4.5-8.5 new tube network. Exhaust only.

Comparison clips match K-weighted whole-segment energy before fades. This is
closer to perceived level than unweighted RMS, but is not a gated LUFS meter
or a guarantee of equal subjective loudness. Main clips share one gain.

New source: crank-angle discharge/intake windows, correlated cylinder variation,
load response memory, dispersive blowdown transient and multiband flow texture.
New exhaust: eight separate runners, two collectors, an expansion chamber and
tailpipe; bidirectional damped wave propagation and area-dependent scattering.
Separate intake/valve-seat/body layers; body has no added bass oscillator.

All sound generated locally; no engine recordings or measured impulse responses.
Geometry and combustion parameters are sound-design approximations, not a
recording-calibrated or exact historical Rover engine/exhaust recreation.
Fuel cutoff is supported only as an explicit input; standard audition traces
retain reduced combustion on overrun, with pumping noise continuing separately.

Listen for believable texture, V8 identity, rasp, drone and throttle response.
No road ambience masks the engine. Signal checks do not prove realism.
Game files and mute settings untouched; no Unreal launch or runtime integration.

Reproduce with Saved/Tools/TerrainPython/Scripts/python.exe
Art/tools/render_range_rover_audio_v3.py --out <fresh directory>.
''')
    with zipfile.ZipFile(args.out/'RangeRover_procedural_v3_samples.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(args.out.iterdir()):
            if path.suffix in ('.wav','.json','.txt'):z.write(path,path.name)
    print(json.dumps({'checks':validation,'files':[(f['file'],f['seconds'],f['true_peak_dbfs']) for f in report['files']]},indent=2))


if __name__=='__main__':main()
