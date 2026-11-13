"""Offline body-rumble variation of S2; preserves S2 and the approved V8.

Body vibration is sound design derived from recorded gravel, not an actual
Range Rover suspension recording. No oscillator or generated noise bed.
"""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
import soundfile as sf
from scipy import signal
import render_ground_audio_s2 as s2

ROOT = s2.ROOT
SR = s2.SR
BASE = ROOT/'Art/Export/VehicleAudio/Ground_Recorded_S2'
OUT = ROOT/'Art/Export/VehicleAudio/Ground_Recorded_S3_BodyRumble'


def load(path):
    x, rate = sf.read(path, always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    divisor = np.gcd(rate, SR)
    return signal.resample_poly(x, SR//divisor, rate//divisor)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ground_path = BASE/'02_ground_response_only.wav'
    engine_path = ROOT/'Art/Export/VehicleAudio/RangeRover_Hybrid_H2_final/01_acceleration_shifts_lift.wav'
    protected = [ground_path, engine_path, BASE/'controls.json']
    hashes = {str(p):digest(p) for p in protected}
    ground = load(ground_path)
    engine = load(engine_path)
    raw = load(s2.REF/'gravel2_hq_preview.mp3')
    controls = json.loads((BASE/'controls.json').read_text())
    t = np.arange(len(ground))/SR
    speed = np.interp(t, controls['time_s'], controls['speed_kmh'])
    grass = np.interp(t, controls['time_s'], controls['grass_weight'])
    moving = np.clip(speed/3, 0, 1)
    moving = moving**2*(3-2*moving)

    # Slow recorded stone texture supplies irregular vibration; high-pass before
    # slowing reduces the original trailer/tractor low-frequency contribution.
    texture = s2.loop(raw, 1, 15, 120, 1600, .1)
    rate = .43+.18*np.sqrt(speed/60)
    excitation = s2.play(texture, rate, 2*SR)
    body = s2.level(s2.filtered(excitation, 38, 225), .037)
    # Mostly central body sound, retaining a little irregular stereo texture.
    body = .85*body.mean(axis=1, keepdims=True)+.15*body
    envelope = moving*(.28+.72*np.sqrt(speed/60))*(1-.48*grass)
    body *= envelope[:,None]

    # Broad, dull knocks use slices of the same recorded texture. These are
    # authored bump examples, not measurements of suspension force or travel.
    bumps = np.zeros_like(body)
    events = [(4.5,.40),(7.7,.55),(10.4,.75),(11.7,.50),
              (14.6,.65),(16.3,.50),(19.2,.35),(21.1,.25)]
    for index,(time, strength) in enumerate(events):
        length = round((.30+.025*(index%3))*SR)
        offset = round((1.2+index*.9)*SR)
        clip = raw[offset:offset+length*2]
        # Half-speed source transients provide short body thuds, with no tonal
        # resonator or repeated synthetic impact waveform.
        clip = s2.play(clip, np.full(length,.53))
        clip = s2.level(s2.filtered(clip, 48, 520), .065)
        attack = np.minimum(np.arange(length)/(.018*SR), 1)
        decay = np.exp(-np.arange(length)/(.085*SR))
        clip = s2.fade(clip*attack[:,None]*decay[:,None], .012)
        at = round(time*SR)
        bumps[at:at+length] += clip*strength
    added = body+bumps
    new_ground = ground+added
    old_mix = engine+ground
    new_mix = engine+new_ground
    # Same interval and same gain, so A/B evaluates the extra body sound only.
    a,b = 9*SR,17*SR
    comparison = np.concatenate([s2.fade(old_mix[a:b]), np.zeros((SR,2)),
                                 s2.fade(new_mix[a:b])])
    outputs = {'01_v8_with_body_rumble':new_mix,
               '02_ground_and_body_only':new_ground,
               '03_before_after_same_section':comparison}
    report = dict(integrated=False, source='S2 recorded gravel, lowered and filtered for designed body vibration.',
                  controls='Same authored speed/surface timeline as S2; bumps are authored, not live telemetry.',
                  files={}, protected_sha256=hashes)
    for name,x in outputs.items():
        assert np.isfinite(x).all() and np.max(np.abs(x)) < .95
        sf.write(OUT/(name+'.wav'), x, SR, subtype='PCM_16')
        report['files'][name] = dict(seconds=len(x)/SR,
            peak_dbfs=float(20*np.log10(np.max(np.abs(x)))),
            rms_dbfs=float(20*np.log10(s2.rms(x))))
    assert np.max(np.abs(new_ground[:3*SR])) == 0
    assert np.max(np.abs(new_ground[23*SR:])) == 0
    assert all(digest(p) == hashes[str(p)] for p in protected)
    old_low = s2.filtered(ground, 35, 220)[7*SR:18*SR]
    new_low = s2.filtered(new_ground, 35, 220)[7*SR:18*SR]
    report['ground_35_220hz_gain_db'] = float(20*np.log10(s2.rms(new_low)/s2.rms(old_low)))
    report['checks'] = dict(parked_ground_silent=True, finite_unclipped=True,
                            original_samples_unchanged=True, engine_gain_unchanged=True)
    (OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (OUT/'bumps.json').write_text(json.dumps(events),encoding='utf-8')
    shutil.copyfile(BASE/'controls.json',OUT/'controls.json')
    shutil.copyfile(BASE/'sources.json',OUT/'sources.json')
    credit = (BASE/'ATTRIBUTION.txt').read_text(encoding='utf-8')
    credit += '\n\nS3 additional adaptation: gravel2 lowered in pitch, filtered into body rumble and short bump textures.\nDesigned vibration; not a recording of Range Rover suspension.\n'
    (OUT/'ATTRIBUTION.txt').write_text(credit,encoding='utf-8')
    (OUT/'LISTENING_GUIDE.txt').write_text(
        'S3 BODY RUMBLE - offline audition only\n'
        '01: approved V8 + S2 ground + low body vibration and subdued bumps.\n'
        '02: ground/body alone. 03: same 9-17s interval before, 1s silence, then after.\n'
        'Full samples: 0-3 parked; 3-6.5 crawl; 6.5-12 acceleration; 12.9 gravel brake;\n'
        '15-18 coast; 18-18.8 transition to provisional grass Foley; 23-24 stopped.\n'
        'Body rumble derives from recorded gravel; this is sound design, not measured suspension audio.\n'
        'Grass remains cloth Foley. Engine and S2 texture gains remain unchanged.\n'
        'Checks establish headroom and silence, not perceptual quality or in-game response.\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
