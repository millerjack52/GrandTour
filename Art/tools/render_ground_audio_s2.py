"""Offline recorded ground audition; no Unreal assets or runtime changes.

Public Freesound previews retain their source licences. Grass is cloth Foley,
explicitly provisional. Controls are authored examples, not driving telemetry.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import hashlib
import json
import re
import numpy as np
import soundfile as sf
from scipy import signal

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / 'Art/Audio/References/Ground_Recorded_S2'
OUT = ROOT / 'Art/Export/VehicleAudio/Ground_Recorded_S2'
SR = 48000
SOURCES = [
    dict(id='gravel1', author='OBXJohn', title='Tires on Gravel Road 1',
         page='https://freesound.org/people/OBXJohn/sounds/251661/',
         license='CC0', license_url='https://creativecommons.org/publicdomain/zero/1.0/',
         warning='Trailer tyre beside recorder on hayride; background tractor/people may remain.'),
    dict(id='gravel2', author='OBXJohn', title='Tires on Gravel Road 2',
         page='https://freesound.org/people/OBXJohn/sounds/251662/',
         license='CC0', license_url='https://creativecommons.org/publicdomain/zero/1.0/',
         warning='Trailer tyre beneath trailer; background tractor/people may remain.'),
    dict(id='skid', author='kyles', title='auto car or van stop brake skid gravel short.flac',
         page='https://freesound.org/people/kyles/sounds/637161/',
         license='CC0', license_url='https://creativecommons.org/publicdomain/zero/1.0/',
         warning='Short car/van gravel stop; not a sustained sliding loop.'),
    dict(id='grass_foley', author='BBoz87', title='Rolling In Grass Loop',
         page='https://freesound.org/people/BBoz87/sounds/816446/',
         license='CC BY 4.0', license_url='https://creativecommons.org/licenses/by/4.0/',
         warning='Recorded towel rubbed against shirt, NOT real tyres on grass.'),
]


def get(url):
    with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as response:
        return response.read()


def sources():
    REF.mkdir(parents=True, exist_ok=True)
    result = {}
    provenance = []
    for spec in SOURCES:
        page_path = REF / (spec['id'] + '.html')
        if not page_path.exists():
            page_path.write_bytes(get(spec['page']))
        html = page_path.read_text(encoding='utf-8')
        urls = re.findall(r'https://[^\s"<>]+hq\.mp3', html)
        assert urls, spec['page']
        preview = urls[0]
        path = REF / (spec['id'] + '_hq_preview.mp3')
        if not path.exists():
            path.write_bytes(get(preview))
        x, rate = sf.read(path, always_2d=True)
        if x.shape[1] == 1:
            x = np.repeat(x, 2, axis=1)
        meta = dict(**spec, preview_url=preview, file=str(path.relative_to(ROOT)),
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    decoded_rate=rate, decoded_seconds=len(x)/rate,
                    accessed_utc=datetime.now(timezone.utc).isoformat())
        provenance.append(meta)
        g = np.gcd(rate, SR)
        result[spec['id']] = signal.resample_poly(x, SR//g, rate//g)
        print(spec['id'], round(len(x)/rate, 3), spec['license'], flush=True)
    (REF/'provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    return result, provenance


def filtered(x, low, high):
    return signal.sosfiltfilt(signal.butter(2, [low, high], btype='bandpass', fs=SR, output='sos'), x, axis=0)


def rms(x):
    return float(np.sqrt(np.mean(x*x)))


def level(x, target):
    return x * min(target/max(rms(x), 1e-9), .8/max(np.max(np.abs(x)), 1e-9))


def loop(x, start, end, low, high, target):
    x = filtered(x[round(start*SR):round(end*SR)], low, high)
    x -= x.mean(axis=0)
    overlap = int(.16*SR)
    period = len(x)-overlap
    w = (.5-.5*np.cos(np.linspace(0, np.pi, overlap)))[:, None]
    y = x[:period].copy()
    y[:overlap] = x[period:]*(1-w)+x[:overlap]*w
    return level(y, target)


def play(x, rate, offset=0):
    pos = (np.cumsum(rate)-rate[0]+offset) % len(x)
    a = pos.astype(np.int64)
    f = (pos-a)[:, None]
    return x[a]*(1-f)+x[(a+1)%len(x)]*f


def fade(x, seconds=.04):
    x = x.copy()
    n = min(round(seconds*SR), len(x)//2)
    w = .5-.5*np.cos(np.linspace(0, np.pi, n))
    x[:n] *= w[:, None]
    x[-n:] *= w[::-1, None]
    return x


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, provenance = sources()
    # Long source excerpts retain recorded irregularity; only mild playback-rate
    # changes. Wider speed coverage requires actual recordings at those speeds.
    gravel1 = loop(data['gravel1'], .5, 10.5, 115, 5800, .030)
    gravel2 = loop(data['gravel2'], 1, 15, 115, 5800, .030)
    grass = loop(data['grass_foley'], .05, 4.25, 100, 3800, .012)
    skid = fade(level(filtered(data['skid'], 100, 6500), .055))
    t = np.arange(24*SR)/SR
    speed_points = [(0,0),(3,0),(3.8,6),(6.5,6),(9,35),(12,60),
                    (12.8,60),(14,34),(15,34),(18,24),(21,13),(23,0),(24,0)]
    speed = np.interp(t, *np.array(speed_points).T)
    grass_weight = np.interp(t, [0,18,18.8,24], [0,0,1,1])
    grass_weight = grass_weight**2*(3-2*grass_weight)
    moving = np.clip(speed/3, 0, 1)
    moving = moving**2*(3-2*moving)
    roll_gain = moving*(.24+.76*np.sqrt(speed/60))
    rate = .72+.48*np.sqrt(speed/60)
    fast = np.clip((speed-12)/40, 0, 1)
    gravel = (play(gravel1, rate)*(np.cos(fast*np.pi/2))[:,None]
              +play(gravel2, rate, 3*SR)*(np.sin(fast*np.pi/2))[:,None])
    bed = (gravel*np.sqrt(1-grass_weight)[:,None]
           +play(grass, rate)*np.sqrt(grass_weight)[:,None])*roll_gain[:,None]
    event = np.zeros_like(bed)
    # One braking event; ordinary rolling/coasting never triggers this layer.
    start = round(12.9*SR)
    event[start:start+len(skid)] += skid
    dry = bed+event
    engine_path = ROOT/'Art/Export/VehicleAudio/RangeRover_Hybrid_H2_final/01_acceleration_shifts_lift.wav'
    engine, engine_sr = sf.read(engine_path, always_2d=True)
    assert engine_sr == SR and engine.shape == dry.shape
    mix = engine+dry
    comparison = np.concatenate([
        fade(gravel1[:4*SR]), np.zeros((SR//2,2)),
        fade(skid), np.zeros((SR//2,2)),
        fade(grass[:3*SR])])
    outputs = {'01_recorded_material_candidates':comparison,
               '02_ground_response_only':dry, '03_ground_with_approved_v8':mix}
    report = dict(sample_rate=SR, integration=False,
                  controls='Authored offline controls; not gameplay telemetry or handling verification.',
                  limitations=[s['warning'] for s in SOURCES], files={})
    for name, audio in outputs.items():
        assert np.isfinite(audio).all() and np.max(np.abs(audio)) < .95
        sf.write(OUT/(name+'.wav'), audio, SR, subtype='PCM_16')
        report['files'][name] = dict(seconds=len(audio)/SR, peak_dbfs=float(20*np.log10(np.max(np.abs(audio)))), rms_dbfs=float(20*np.log10(rms(audio))))
    assert np.max(np.abs(dry[:3*SR])) == 0
    assert np.max(np.abs(dry[23*SR:])) == 0
    assert np.max(np.abs(event[:start])) == 0
    report['checks'] = dict(finite_and_unclipped=True, parked_silent=True,
                            braking_layer_only_during_authored_event=True,
                            approved_engine_pcm_used_without_gain_change=True)
    controls = dict(time_s=t[::480].tolist(), speed_kmh=speed[::480].tolist(),
                    grass_weight=grass_weight[::480].tolist(),
                    rolling_gain=roll_gain[::480].tolist(), playback_rate=rate[::480].tolist(),
                    braking_event_s=12.9, throttle_note='Ground independent of throttle; original H2 engine demo reused unchanged.')
    (OUT/'controls.json').write_text(json.dumps(controls), encoding='utf-8')
    (OUT/'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (OUT/'sources.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    credit = '\n\n'.join(f"{s['title']} by {s['author']}\n{s['page']}\n{s['license']}: {s['license_url']}\n{s['warning']}\nAdapted: excerpted, filtered, crossfaded, resampled and gain adjusted." for s in SOURCES)
    credit += '\n\nApproved engine credits:\n'+(engine_path.parent/'ATTRIBUTION.txt').read_text(encoding='utf-8')
    (OUT/'ATTRIBUTION.txt').write_text(credit, encoding='utf-8')
    (OUT/'LISTENING_GUIDE.txt').write_text(
        'Ground recorded S2 - OFFLINE CANDIDATE, not integrated or accepted.\n'
        '01: gravel rolling 0-4 s; gap; car/van gravel stop; gap; provisional cloth grass Foley.\n'
        '02 and 03 share authored controls: 0-3 parked; 3-6.5 crawl; 6.5-12 accelerate;\n'
        '12.9 short gravel braking event; 15-18 coast with throttle released;\n'
        '18-18.8 transition into provisional grass Foley; 23-24 stopped.\n'
        '03 adds the approved H2 engine clip unchanged; ground and engine use a demonstration timeline,\n'
        'not actual telemetry. Grass is towel-on-shirt Foley, NOT real tyres.\n'
        'Hayride recordings may retain people/tractor background. These are public MP3 previews.\n'
        'Numerical checks establish headroom/silence only, not convincing sound or driving response.\n'
        'Next integration needs genuine grass/speed-range sources and live contact/slip control tuning.\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
