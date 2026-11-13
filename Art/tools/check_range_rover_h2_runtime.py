"""Prepare an independent Python H2 oracle, or verify the native render exported by UE automation."""
from pathlib import Path
import argparse, json, struct, time
import numpy as np
from scipy import signal
from scipy.io import wavfile
from numba import njit
import render_range_rover_audio_hybrid_h2 as h2

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/AudioH2QA'

@njit(cache=True)
def follow(x, start, rise, fall):
    y=np.empty(len(x)); value=start
    for i in range(len(x)):
        alpha=1-np.exp(-1/(48000*(rise if x[i]>value else fall)))
        value+=alpha*(x[i]-value); y[i]=value
    return y

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    # Targets change at game/control block boundaries; render state persists throughout.
    block=256; count=2250; duration=count*block/48000
    t=np.arange(count)*block/48000
    rpm=np.interp(t,[0,1,4,4.25,6,7,8,10,11,12],[800,800,4200,2400,4200,3200,2500,2500,800,800])
    throttle=np.interp(t,[0,.9,1.1,3.9,4,4.25,4.5,6,6.15,8,8.15,9,9.15,10,10.2,12],[0,0,.9,.9,0,0,.9,.9,0,0,1,1,.1,.1,0,0])
    gain=np.where(t<11,1.,0.)
    controls=np.column_stack((rpm,throttle,gain)).astype('<f4')
    (OUT/'controls.bin').write_bytes(struct.pack('<II',block,count)+controls.tobytes())
    p=json.loads((ROOT/'Art/Audio/range_rover_v8_hybrid_h2.json').read_text())
    folder=ROOT/'Art/Export/VehicleAudio/RangeRover_Hybrid_H2_final'
    loops=[wavfile.read(folder/'PreparedLoops'/(s['name']+'.wav'))[1].astype(float) for s in p['banks']]
    lengths=np.array([len(a) for a in loops]); packed=np.zeros((4,max(lengths),2))
    for i,a in enumerate(loops):packed[i,:len(a)]=a
    targets=np.repeat(controls.astype(float),block,axis=0)
    r=follow(targets[:,0],800,.015,.015); th=follow(targets[:,1],0,.045,.14); g=follow(targets[:,2],0,.025,.025)
    rec,_=h2.playback(packed,lengths,np.array([s['root_rpm'] for s in p['banks']],float),r,np.zeros(4))
    rec=h2.throttle_response(rec,th,r,48000,600,6200,1.7)
    rec=h2.v1.filtered(rec,48000,29,'highpass')
    pressure,_=h2.v1.combust(r,th,np.zeros(len(r)),48000,np.array([0,1,1,0,1,0,0,1]),np.array([1.05,.91,1.04,.98,.94,1.06,.92,1]))
    support=h2.v1.filtered(pressure.sum(axis=0),48000,[32,125],'bandpass',order=4)
    m=json.loads((folder/'manifest.json').read_text())
    x=(rec+m['shared_support_gain']*support[:,None])*m['shared_gain']*g[:,None]
    pcm=(np.clip(x,-1,1)*32767).astype('<i2')
    (OUT/'expected.pcm').write_bytes(pcm.tobytes())
    wavfile.write(OUT/'python_reference.wav',48000,pcm)
    print(json.dumps(dict(seconds=duration,blocks=count,reference_peak=float(np.max(abs(x))))))

def verify():
    sr,x=wavfile.read(OUT/'native_render.wav'); x=x.astype(float)/32767
    expected=np.frombuffer((OUT/'expected.pcm').read_bytes(),dtype='<i2').reshape(-1,2).astype(float)/32767
    assert sr==48000 and x.shape==expected.shape and np.isfinite(x).all()
    max_error=float(np.max(abs(x-expected)))
    assert max_error<4/32767,(max_error, 'native renderer differs from independent H2 oracle')
    assert np.max(abs(x))<.9 and np.max(abs(x[-24000:]))<2/32767
    report=dict(native_matches_python_h2=True,max_error_pcm_counts=max_error*32767,
                peak_dbfs=float(20*np.log10(np.max(abs(x)))),end_gate_silent=True,
                covers='idle, RPM sweeps, shifts, closed throttle, fixed RPM throttle change, engine gate')
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    verify() if args.verify else prepare()
