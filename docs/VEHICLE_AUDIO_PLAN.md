# Grand Tour vehicle audio research and plan

2026-10-24 UTC. Status: proposed plan, not implementation approval or listening acceptance.
Scope: audio first; prepare the data contract for later customisation and garage UI.
This research pass changes no gameplay code, assets, plugins or mute settings.

## Recommendation

Prototype physically informed procedural engine audio, with a hybrid comparison
using a small amount of recorded texture. Use Unreal's audio system and MetaSounds
for routing, layering and sound design, with a small C++ synthesis operator if
precise cylinder pulse timing needs it. Select the engine renderer after listening
and profiling, before expanding to the fleet. A fully procedural engine remains a
candidate; recordings are an option, not a prerequisite imposed by this plan.

The intended result is an expressive, convincing driving sound: engine load, shifts,
tyre grip and surface contact should be understandable by ear. Physical parameters
provide useful controls; they do not guarantee a convincing result without tuning.

## Current implementation audit

Inspected Source/GrandTour/Vehicle/GTVehicleAudioComponent.h/.cpp and the audio call
in GTCarPawn.cpp, drivetrain/traction interfaces, parts interfaces and local engine.

- Existing runtime synth: mono, 22.05 kHz, four engine harmonics, noise for tyres
  and skids, and a noise thud for impacts. Engine frequency follows the custom
  drivetrain RPM; amplitude follows pedal input and simple condition gates.
- It does not consume torque/load, gearshift phase or distinct intake/exhaust
  signals. Spatialisation is explicitly disabled. It is a greybox foundation.
- FiringPulsesPerRev defaults to four (four-stroke V8). No other assignment was
  found in searched C++/Python; Blueprint overrides still need an asset audit.
  Do not assume that the whole fleet has correctly configured engine identities.
- The claimed half-rate sub uses sin(PI * Phase) while Phase wraps every turn at
  one. This repeats a positive half-sine, rather than a continuous half-frequency
  oscillation. Replace it in the new renderer and check DC offset explicitly.
- Parameters are read once per 1024-sample generation callback, with no explicit
  sample ramping. The nominal generated block is about 46 ms at 22.05 kHz; that is
  not a measured end-to-end latency. Responsiveness and clicks need a real test.
- Tyre sound reads legacy SurfaceTag and falls back to tarmac. It ignores the
  authored Gravel identity used by the new visual effects. Share authoritative
  contact classification rather than creating another conflicting surface lookup.
- Available inputs already include RPM, drive/brake input, gear, engine torque,
  low range, contact load, tread speed, signed longitudinal slip, authored surface,
  moisture, water depth and condition. Shift phase, boost and calibrated engine
  load may require explicit interfaces; do not pretend they already exist.
- UGTPartSlotsComponent already supplies installed part IDs, fit checks and
  loadout application. UGTPartDefinition supplies tuning contributions and tag
  dependencies. Extend these rather than adding a second audio-only parts system.
- The older VEHICLE_BUILD_SYSTEM.md contains a single-car design assumption that
  conflicts with today's fleet. This plan preserves the fleet and does not adopt
  that older restriction.

## Research findings

| Approach | Benefit for Grand Tour | Main tradeoff | Proposed use |
| --- | --- | --- | --- |
| Combustion pulses and acoustic resonators | Cylinder, firing-order, exhaust and condition changes can affect the sound directly | Believable timbre needs substantial tuning | First procedural prototype |
| Recorded loops with procedural control | Strong source character with a relatively simple renderer | Pitch shifting and crossfades can reveal the loops; modifications need authored variation | Hybrid comparison/fallback |
| Granular/resynthesised recordings | Responsive RPM changes while retaining recorded detail | Needs suitable recordings and analysis; renderer dependency | Evaluate after first listening test |
| Detailed engine simulation | Rich engine-design experimentation | Separate simulation integration and unmeasured runtime cost | Reference or offline authoring candidate |
| Learned procedural model | Can fit interpretable synthesis parameters to reference audio | Training, deployment, rights and performance work | Research reference, outside first milestone |

MetaSounds provides a DSP graph, reusable sound designs and gameplay-driven
parameters. It is a construction tool, not a ready-made realistic vehicle engine.
[Epic MetaSounds overview](https://dev.epicgames.com/documentation/en-us/unreal-engine/metasounds-the-next-generation-sound-sources-in-unreal-engine).

Epic's City Sample uses MotoSynth to resynthesise acceleration/deceleration
recordings for drivable vehicles, with MetaSounds adding layers such as idle and
drift. This is a useful hybrid precedent, not proof of recording-free synthesis.
[City Sample vehicle audio](https://dev.epicgames.com/documentation/en-us/unreal-engine/city-sample-project-unreal-engine-demonstration#vehicleaudio).

MotoSynth's UE 5.8 API exists, and the installed descriptor at
C:/Program Files/Epic Games/UE_5.8/Engine/Plugins/Experimental/MotoSynth/MotoSynth.uplugin
marks it experimental, unsupported and disabled by default. Use behind an adapter
if trialled; evaluate packaging and maintenance before committing.
[Epic MotoSynth API](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/MotoSynth).

Baldan and colleagues present a physically informed procedural alternative to
sample-based and analysis/resynthesis methods. This supports testing a lightweight
acoustic model without implementing a full engineering simulator.
[2015 paper and repository record](https://air.iuav.it/handle/11578/264484).

The 2026 Pulse-Train-Resonator paper models firing pulses and exhaust resonances,
conditioned by RPM, torque and operating state. The architectural lesson here is
to distinguish load and overrun at the same RPM. Its reported reconstruction
results are not a Grand Tour performance benchmark or a listening acceptance test.
[PTR paper](https://arxiv.org/html/2603.09391v2).

The author's companion dataset page offers comparable gearshift, overrun and
neutral tip-in examples across engine/capture configurations. Use these for the
listening session; no listening judgement or production-use rights were established
in this research pass. Check code, weights, recordings and dataset terms separately
before importing any material.
[Examples and dataset description](https://rdoerfler.github.io/procedural-engine-sounds-page/).

Ange Yaghi's Engine Simulator generates audio using real-time engine simulation;
its repository explicitly says it is not a scientific engineering tool. Treat it
as a reference/offline authoring candidate, not a replacement for our drivetrain.
[Engine Simulator repository](https://github.com/ange-yaghi/engine-sim).

REV is a commercial comparison option: its vendor describes resynthesis of recorded
accelerations and an Unreal integration. UE 5.8 compatibility and commercial terms
would need checking with the vendor before selection; neither is assumed here.
[Crankcase Audio](https://www.crankcaseaudio.com/).

## Proposed audio design

One coherent vehicle-state snapshot feeds the renderer. Physics stays authoritative;
audio does not run a competing engine/gearbox simulation. Smooth continuous controls
on the audio side, preserve firing phase, and schedule discrete events without
retriggering them every frame. Use the device sample rate and floating-point DSP,
with bounded filters, DC removal, headroom and controlled limiting.

An EngineSoundProfile would specify the four-stroke firing schedule over 720
degrees, cylinder/bank routing, pulse character, idle variation, intake/exhaust
resonances and operating-state curves. Cylinder count alone cannot distinguish
all engines. Proposed first identities are the Range Rover V8, BMW inline-six and
Suzuki inline-four, subject to checking the actual selected engine variants.

| Layer | Controls | Driving information |
| --- | --- | --- |
| Combustion/exhaust | RPM, load, firing schedule, exhaust profile | Revs, effort, lift-off and engine identity |
| Intake/mechanical | Load, RPM, installed intake, condition | Induction growl, mechanical texture and strain |
| Drivetrain events | Gear/shift state, torque reversal, low range | Shift interruption, engagement and transmission load |
| Tyre/ground | Contact load, tread speed, slip, surface blend, wetness | Grip loss, gravel scrub, mud churn and water |
| Body/contact | Suspension travel/velocity, impact energy, loose-part state | Bumps, landing, clunks and stone strikes |
| Air/cabin | Speed, listener position, doors/windows where supported | Speed and interior/exterior perspective |

Gravel needs rolling crunch, slip-dependent scrub and intermittent stone hits on
the underbody. Do not play one sound for every rendered particle: derive a bounded
event stream from tyre contact. Mud, water and tarmac get different responses;
airborne wheels lose contact noise. Lateral scrub should eventually use lateral
contact motion too, not only the current longitudinal SlipMagnitude.

Misfires should alter pulse events, not merely turn the whole engine down. Backfire,
turbo and limiter effects must have supported engine/state conditions; no random
pops on every car. Off-road effort follows load and wheel motion, even at low
vehicle speed. Engine-off coasting retains tyre and wind sound.

Use engine-bay, exhaust and contact emitters with separate cabin/exterior mixes.
Distance and voice budgeting should reduce inactive/far-car cost. A parked service
fleet must not produce twelve full-detail non-spatial engines. Test Doppler during
pass-bys and moving-camera transitions rather than applying it blindly everywhere.

## Milestones and acceptance gates

1. **Audio bench and reference capture.** Reuse the rally level and a controlled
   RPM/load trace. Produce level-matched, labelled WAVs for idle, neutral blips,
   loaded acceleration, constant-RPM load changes, shift, lift-off and shutdown.
   Compare the placeholder, a pulse/resonator prototype and a hybrid if suitable
   recordings are available. First deliverable: one convincing Range Rover, not
   twelve approximate engine noises. Listening selects the renderer.
2. **Driving feedback.** Connect the selected engine to authoritative drivetrain
   state; add shifts and gravel rolling/scrub/stone hits. Audition tight corners,
   fast bends and low-range effort. Gate: the driver can hear load and grip change
   without watching telemetry; no exaggerated effects masking weak base audio.
3. **Fleet and perspectives.** Author the contrasting BMW and Suzuki profiles,
   then cabin, chase and walk-around mixes. Gate: distinct identities at matched
   loudness, coherent engine swaps, and smooth camera/vehicle transitions.
4. **Off-road and stability.** Add mud/water/suspension/condition response. Exercise
   idle, flood/stall, engine-off coasting, reverse, low range, reset and car swap.
   Test peak level, DC, discontinuities, aliasing and audio underruns. Capture audio
   thread/DSP cost plus game-frame p95/p99/hitches with audio on/off under the same
   graphics and driving workload. Target <25% of the audio callback deadline for
   the vehicle mix initially; measure before promising a budget or 120 fps.
5. **Customisation and UI.** Extend the existing part data with sound-profile
   references and bounded modifiers. Build the garage flow around inspecting a
   fitted part, comparing a compatible replacement, previewing its visual/stat/
   sound effects, applying or reverting, and saving/loading the same loadout.

Keep milestone 1 UI small: play/stop, idle/rev/drive scenario, profile A/B, layer
solo/mute and level matching. This is a development audition panel. The eventual
player UI uses parts and plain-language effects, not pulse/filter coefficient
sliders. An exhaust preview should compare the same RPM/load passage at matched
loudness, so louder is not automatically judged better. Preview must not silently
install parts, reset condition or spend resources.

Player-facing audio settings should include master, engine, tyres/contact and world
levels, plus a reduced-dynamic-range option. Save audio settings separately from
the vehicle loadout. Do not undertake the whole garage redesign until the audio
prototype establishes what players need to preview.

## First implementation slice

Proposed files: evolve GTVehicleAudioComponent.h/.cpp into the state adapter; add
a small engine-synth implementation and EngineSoundProfile asset class; add
MetaSound assets under Content/GrandTour/Audio; expose missing drivetrain events
without changing its physics; reuse the existing rally authoring/test workflow for
offline captures. Later extend Parts/GTItemDefinition and GTPartSlotsComponent,
and replace the relevant garage/HUD interactions after a separate UI audit.

Do not bulk-import City Sample, purchase middleware, adopt neural inference, or
change the fleet/handling as part of the first slice. Keep existing mute behaviour
until an explicit audition run. Retain the normal single-Unreal guard, authored
asset backups and unchanged graphics settings throughout implementation.


## Prototype A1 delivered: Range Rover procedural listening samples

2026-10-24 UTC. Milestone 1 offline synthesis prototype is implemented; owner
listening acceptance and Unreal integration are pending. No live audio was enabled.

Renderer: Art/tools/render_range_rover_audio.py.
Preset: Art/Audio/range_rover_v8_prototype.json.
Review pack: Art/Export/VehicleAudio/RangeRover_Procedural_v1_review/.
Run with Saved/Tools/TerrainPython/Scripts/python.exe
Art/tools/render_range_rover_audio.py --out <fresh output directory>.
Existing output directories are protected from replacement.

The synthesis uses a continuous four-stroke V8 firing cycle, uneven per-bank firing
sequence, fractional event timing, asymmetric bipolar pressure pulses, damped
exhaust reflections, load-dependent pulse/filter/saturation response, and generated
intake/mechanical/body layers. Internal synthesis is 96 kHz, downsampled to 48 kHz
stereo 16-bit PCM WAV. No recordings, AI audio model or third-party audio assets.
This is a warm cross-plane V8 archetype for the game car, not an exact model-year
or exhaust-system recreation. Idle/max RPM follow the current native car's 800/5000
settings. Authored scenarios are not captured vehicle telemetry.

Files: 00_listening_overview (37 s); 01_idle_and_blips (18 s);
02_acceleration_shifts_lift (24 s); 03_same_rpm_load (14 s);
04_low_range_effort (16 s); 05_load_tone_volume_matched (9 s).
The overview and four driving clips use one gain, with maximum 4x estimated true
peak -6 dBFS. The last comparison equalises segment RMS (not perceptual LUFS).
The ZIP includes WAVs, 100 Hz control traces, preset, manifest and listening guide.

Validation: firing count/timing at fixed RPM; silent pipe response for zero input;
stable decaying pipe feedback; expected event counts for every trace; finite DSP
output; no clipped samples; negligible DC; WAV decode and archive integrity.
The fixed-RPM comparison initially changed amplitude much more than spectrum.
That first diagnostic is preserved in RangeRover_Procedural_v1. The review version
changes the loaded pulse's rise/decay; at 2500 RPM spectral centroid rises from
243 to 290 Hz and upper/bass energy ratio from -10.59 to -7.75 dB. These are
signal diagnostics, not proof of perceptual realism. The volume-matched file is
provided so the owner can judge the change in character.

No listening-quality approval is claimed from automated analysis. Assess believable
idle, V8 weight, rev transition, load character, shift/lift-off continuity and any
synthetic buzz, whistle, drone or clicks. No tyres, wind, gravel or extra effects
mask the engine. Offline render timing is not a real-time Unreal CPU/latency result.
Next step after feedback: refine the approved voice, then port the DSP/state
interface into the existing vehicle audio system and test in the rally level.


## Prototype A2 delivered: deeper Range Rover V8 revision

2026-10-24 UTC. Owner feedback on A1: too synthetic; requested deeper V8
rumble and more natural texture before any game integration.

Renderer: Art/tools/render_range_rover_audio_v2.py.
Preset: Art/Audio/range_rover_v8_prototype_v2.json.
Review pack: Art/Export/VehicleAudio/RangeRover_Procedural_v2_review/.
V1 source, preset and audio remain intact. V2 reuses the V1 authored scenarios
and utilities; manifest source hashes include both renderers and the V2 preset.
Run using the TerrainPython interpreter and a fresh --out directory.

Changes: softer/longer pressure pulses, seeded event amplitude and width
variation, pulse-shaped generated combustion turbulence, lower broad exhaust
resonances, reduced feedback/ringing, stronger bank-derived bass/body and reduced
pure mechanical tones. Still entirely procedural; no engine recordings.

Listen to 00_deeper_v8_overview.wav (37 s), or the full four scenario clips.
05_v1_then_v2_comparison.wav (26 s) contains old/new idle and blip, followed by
old/new loaded pull. Six seconds each with half-second gaps, at equal segment
RMS before fades (not perceptual LUFS matching). Common comparison attenuation
preserves headroom. The initial diagnostic render is retained separately in
RangeRover_Procedural_v2; use the completed _review pack for listening.

Validation: all six final WAVs decode as 48 kHz stereo PCM16, with no clipping,
negligible DC and estimated 4x true peaks at or below -6 dBFS. Archive integrity,
source hashes, firing counts/timing, silent zero-input response and stable pipe
feedback passed. In compared segments the 35-180 Hz to 400-2500 Hz energy ratio
increases by 11.29 dB at idle/blip and 10.07 dB under load. Spectral centroids
fall from 249 to 131 Hz and 339 to 206 Hz respectively. These establish a deeper
spectral balance, not perceived naturalness. Owner audition remains pending.

No live game audio, car physics, mute settings or other vehicles were changed
for A2. Unreal was not launched. Approve/refine this voice before integration.


## A2 follow-up research: reducing the synthetic character

2026-10-24. Owner judgement: closer, but still too synthetic. This pass reviews
published methods and current renderer code; it does not claim an independent
audio audition. No renderer, sample or game integration changes were made.

### Diagnosis from our implementation

A2 improves bass balance but every cylinder still uses the same analytic pulse
family, with small gain/width changes. Intake and mechanical layers are mostly
filtered noise with simple periodic modulation. Both exhaust paths use a single
fixed echo and two broad resonances. Their parameters were hand-selected without
fitting a target engine. Negative load simply reduces combustion amplitude; there
is no explicit fuel-cut state, valve-event model or manifold response history.
These are plausible causes of the reported synthetic character, not established
perceptual diagnoses. Increasing bass or random noise alone is unlikely to resolve
all of them.

The GTCarPawn.cpp constructor describes the car as a Range Rover Classic 3.9 V8.
Use that as the provisional reference identity; the current sound preset is only
a generic V8 archetype. Verify engine-specific cylinder numbering, firing order,
bank routing and exhaust configuration before claiming an accurate recreation.
The game's tuned torque is not a reference acoustic measurement.

### Findings that change the next experiment

1. Shape the irregular component by engine state. The 2026 EONE study fits both
engine-order energy and broadband noise across RPM and torque, then exports
parameters to conventional DSP. Its 12-listener study rates the full reconstruction
above a simplified 36-harmonic/no-broadband baseline. This supports reference-guided
texture design; it does not isolate noise as the only cause or establish a result
for our Range Rover. [EONE paper](https://arxiv.org/html/2606.21521v1).

2. Improve event shape and operating-state transitions. PTR combines cylinder
pulses, exhaust resonators, pulse-synchronous turbulence, intake events and separate
fuel-cut airflow. It also conditions on RPM/torque changes. For A3, investigate
crank-phase valve envelopes and state-dependent pulse/noise shaping. Fuel cut must
be an explicit supported engine state, not inferred from every negative-torque
instant. [PTR paper](https://arxiv.org/html/2603.09391v2).

3. Treat exhaust transfer as a substantial part of the voice. Engine Simulator's
public synthesizer source applies timing jitter, a signal/derivative blend,
airflow modulation and per-channel convolution. That is evidence of a richer
rendering chain, not a guarantee from copying it. Trial a small damped network of
runners, collector, silencer and outlet, or a generated impulse response from that
network. An arbitrary reverb/IR cannot supply missing combustion behaviour.
[Engine Simulator source](https://github.com/ange-yaghi/engine-sim/blob/master/src/synthesizer.cpp).

4. Keep a recording-based fallback. Epic uses acceleration/deceleration recordings
with MotoSynth for City Sample drivable vehicles, plus MetaSound layers. This is a
practical alternative if the next procedural experiment still fails listening
acceptance. It requires suitable source recordings; adopting MetaSounds alone
will not repair a weak source voice.
[Epic vehicle audio](https://dev.epicgames.com/documentation/en-us/unreal-engine/city-sample-project-unreal-engine-demonstration#vehicleaudio).

### Recommended A3 experiment (proposed, not implemented)

- Select a consistent exterior Range Rover Classic V8 reference perspective.
  Obtain clean idle, steady RPM, loaded pull, lift-off and tip-in references.
  Free-rev recordings alone cannot establish loaded sound. References used for
  fitting and any incorporated recordings/IRs need suitable usage rights.
- Preserve the engine-cycle clock and plausible per-bank firing sequence. Develop
  per-cylinder event envelopes and subtle correlated cycle variation. Avoid
  exaggerated random timing, misfires or racing-cam lope as realism shortcuts.
- Replace the simple exhaust colouring with the small acoustic network. Keep its
  decay bounded; vary load response smoothly. Compare against the A2 path using
  identical controls so we can identify whether this change actually helps.
- Fit several noise-band levels and modulation envelopes across RPM/load. Give
  intake, exhaust and mechanical radiation different timing and filtering.
  A modest offline parameter search/manual fitting is the first step; a neural
  runtime is not required to test reference-informed procedural synthesis.
- Make short isolated comparisons: idle at 800 RPM, 2500 RPM light/heavy load,
  throttle tip-in/lift, then a pull. Include A2 baseline and separate source-only,
  exhaust-only and combined revisions. Match perceptual level as well as practical;
  equal RMS is insufficient when the bass balance changes substantially.
- Judge texture, V8 identity, drone and transitions by listening, including on
  ordinary speakers. Preserve clipping/DC/stability checks, but do not substitute
  spectral centroid or bass ratio for realism. Keep road/gravel ambience separate
  until the engine voice is acceptable.

Recommendation: one focused A3 procedural attempt using a reference-informed
source and exhaust model. If it still sounds synthetic, compare a hybrid voice
using a small licensed recording set, retaining procedural RPM/load control and
customisation parameters. Do not keep iterating bass EQ without a target.

Useful listening comparisons are provided by the authors:
[EONE reference/full/simplified examples](https://rdoerfler.github.io/eone-model-page/)
and [PTR reference/baseline/model examples](https://rdoerfler.github.io/ptr-model-page/).
EONE's game demonstration additionally uses sampled pops/burble, so that demo is
not evidence of wholly recording-free effects. No demo audio has been imported.


## Prototype A3 delivered: combustion events and exhaust propagation

2026-10-24. Owner authorised the next procedural prototype as an offline sample
before game integration. New renderer Art/tools/render_range_rover_audio_v3.py
and preset Art/Audio/range_rover_v8_prototype_v3.json. Completed review pack:
Art/Export/VehicleAudio/RangeRover_Procedural_v3_review/.

Combustion now includes crank-angle discharge/intake windows, a short dispersive
blowdown transient, correlated cylinder-strength/width variation, separately
filtered turbulence bands and load response memory. Valve-seat radiation and
intake flow use distinct timing. Fuel cutoff has an explicit control input;
standard audition traces retain reduced combustion on overrun because historical
engine-specific cutoff behaviour has not been verified. Pumping noise remains a
separate contribution. Body vibration derives from pressure, with no bass sine.

The exhaust uses 12 bidirectional damped waveguides: eight unequal runners,
two collectors, a silencer expansion chamber and a tailpipe. Four junctions
scatter pressure using area-proportional admittances. Propagation losses,
low-pass filtering and bounded source/outlet reflections control decay.
These are physically informed sound-design approximations, not a measured Rover
exhaust, complete thermodynamic model or reference-recording fit. No recordings,
measured impulse responses, pretrained models or external audio assets were used.

Files:
- 00_v8_combustion_exhaust_overview.wav: 37 seconds, same scenario excerpts as A2.
- 01-04: full idle/blips, acceleration/shifts/lift, 2500 RPM load and low-range traces.
- 05_v2_then_v3_comparison.wav: 39 seconds; old/new idle at 0/6.5 s, old/new
  acceleration at 13/19.5 s, old/new lift-off at 26/32.5 s. Each segment is 6 s.
- 06_exhaust_model_comparison.wav: 9 seconds; new source with old-style exhaust
  at 0 s, identical new source with waveguides at 4.5 s; 4 s each at loaded 2500 RPM.
- ZIP: WAVs, control traces, preset, source/WAV hashes, metrics and listening guide.

Main scenarios share one gain. Comparison segments match K-weighted energy,
without LUFS gating or a claim of identical perceived loudness. Decoded comparison
pairs differ by at most 0.07 dB in that measure after fades. This is an improvement
on the prior unweighted-RMS comparison methodology, not a listening test.

Validation: silent zero-input network, decaying impulse response, fixed-RPM firing
timing and explicit fuel-cut suppression passed. All seven delivered WAVs decode
as 48 kHz stereo PCM16, have finite output, no clipped samples, maximum estimated
4x true peak -6.000 dBFS and maximum absolute DC below 0.000001. ZIP integrity,
renderer/helper/preset/WAV hashes and preserved A2 source hashes verified.
Verification record: Saved/RallyHandlingQA/range-rover-audio-v3-verification.json.

No game source, mute setting, physics or other vehicle changed in A3; Unreal was
not launched. Listening approval and real-time profiling remain pending. Ask the
owner to judge texture, V8 identity, drone and throttle transitions before porting
this voice. Preserve A1/A2 and use a fresh --out directory for any further render.


## Prototype A4 delivered: focused medium/high-RPM revision

2026-10-24. Owner feedback: medium/high still sounds very synthetic. Offline
revision only. Renderer Art/tools/render_range_rover_audio_v4.py and preset
Art/Audio/range_rover_v8_prototype_v4.json. Review pack:
Art/Export/VehicleAudio/RangeRover_Procedural_v4_review/.

Analysis of A3's loaded 2500 RPM clip found a strong peak near 500 Hz, close to
one of the model's exhaust resonances. That is a plausible contributor, not a
confirmed perceptual diagnosis. A4 removes the repeated blowdown chirp, reduces
coherent upper harmonics before adding flow texture, damps the tube network,
reduces chamber impedance discontinuities and direct manifold radiation, and
omits outlet saturation. A smooth RPM blend applies this voice from 1700 to
3200 RPM. Below 1700 RPM the result equals A3 before common output gain.

The focused 20-second sample holds 2400, 3200 and 4200 RPM under load, then lifts.
00_mid_high_revision.wav is A4; 01_v3_same_drive_reference.wav renders A3 on the
same new authored RPM/load trace. Both share a gain. The 27-second comparison
02_v3_then_v4_mid_high_comparison.wav uses old/new pairs of four-second holds:
2400 RPM at 0/4.5 s, 3200 at 9/13.5 s and 4200 at 18/22.5 s. K-weighted energy
matching is not a gated LUFS measurement or identical perceived loudness claim.

Within 250-2500 Hz, the fraction of energy within +/-3 Hz of 720-degree-cycle
orders changes from 0.516 to 0.366, 0.431 to 0.231 and 0.667 to 0.194 for those
three holds. This establishes reduced narrow-order dominance, not realism;
too much hiss or lost V8 identity must also be judged by the owner.

Checks passed for network silence/decay, high-RPM event timing, low-RPM blend
preservation, final WAV decode/clipping/DC/true peaks, archive integrity and source
hashes. A3 sources remain unchanged. Detailed validation is saved in
Saved/RallyHandlingQA/range-rover-audio-v4-verification.json.

No game source or assets changed; Unreal was not launched. No recordings were
imported and this remains an uncalibrated procedural approximation. If the focused
revision still fails the owner's mid/high listening test, prioritise a properly
licensed reference/hybrid comparison over further unguided procedural tuning.


## Hybrid H1 delivered: real V8 recordings with restrained procedural support

2026-10-24. Owner requested a hybrid sample after rejecting procedural A4 as
still synthetic. Renderer Art/tools/render_range_rover_audio_hybrid_h1.py;
preset Art/Audio/range_rover_v8_hybrid_h1.json. Completed listening pack:
Art/Export/VehicleAudio/RangeRover_Hybrid_H1_review/.

Selected real recordings:
- sketchy.dog: V8 Dodge RAM 1500 Engine Starting & Idling, CC BY 4.0.
  https://freesound.org/people/sketchy.dog/sounds/760152/
  https://creativecommons.org/licenses/by/4.0/
- BoilingSand: 080316 Dodge truck revving in driveway.wav, CC BY 3.0.
  Described by the recorder as a mid-1970s 318 V8, recorded near the tailpipe.
  https://freesound.org/people/BoilingSand/sounds/49988/
  https://creativecommons.org/licenses/by/3.0/

Both creator pages and license deeds were checked. Public HQ MP3 previews were
obtained directly from the CDN URLs embedded in the source pages. These are
licensed real recordings, not purchased original lossless WAVs. Saved source
pages, acquisition URLs, retrieval date and hashes accompany the reference
files in Art/Audio/References. A RAM driving take and AMG rev take were evaluated
as candidates but are not used in H1. A Commons Rover recording was found but
not used because its metadata carried an unresolved migration-review notice.

H1 preserves original recording speed and rev timing. Gentle 35 Hz high-pass,
6.5 kHz low-pass, stereo-width adjustment, per-source gain and 250 ms crossfades
assemble idle, two revs, a sustained note and return to idle. Continuous V8 pulse
synthesis supplies only 32-125 Hz support, set 16 dB below recorded energy in
that band and measured 20.12 dB below the recordings overall. Authored RPM hints
and the recording envelope control that layer. They are NOT measured source RPM.
No granular resynthesis or variable-RPM playback is claimed in this prototype.

Files: 00_recording_led_hybrid.wav (22.6 s),
01_recordings_without_procedural_support.wav (same sequence, no support),
02_procedural_then_hybrid.wav (17 s: 8 s A4, half-second gap, 8 s H1, gap).
The comparison uses different rev contours, so it tests voice direction rather
than equal-RPM behaviour. K-weighted segment levels differ by 0.008 dB after
fades; this is not a gated LUFS measurement or proof of perceived equality.

All WAVs decode as stereo 48 kHz PCM16 with no clipped output, maximum estimated
4x true peak -6.000 dBFS and maximum absolute DC below 0.0000002. Source/code/audio
hashes and ZIP integrity passed. The ZIP includes credits, license links,
modification notices, source provenance, excerpt timing and controls. Checks are
saved in Saved/RallyHandlingQA/range-rover-hybrid-h1-verification.json.

No game files, vehicle physics or mute settings changed; Unreal was not launched.
This is a recording-led voice audition for the Range Rover using other Dodge V8s,
not an exact Rover reconstruction. Listening approval remains with the owner.
If accepted, the next task is controlled RPM/load playback using appropriate
loop/grain material and fuller loaded/off-load coverage, followed by runtime
profiling. Evaluate original lossless source availability before integration.
Soundfile 0.14.0 was added to the isolated TerrainPython environment to decode
MP3 sources; existing prototype sources and samples were preserved.


## Hybrid H2 delivered: independent RPM and throttle control

2026-10-24. Owner approved H1's voice direction and requested RPM/throttle
response as another offline audition before game integration. Renderer:
Art/tools/render_range_rover_audio_hybrid_h2.py. Preset:
Art/Audio/range_rover_v8_hybrid_h2.json. Final review pack:
Art/Export/VehicleAudio/RangeRover_Hybrid_H2_final/.

Four recorded loop banks use the same licensed H1 sources. Ends are selected by
waveform correlation and joined with 160 ms complementary crossfades. Each bank
has a continuous variable-rate cursor; RPM controls pitch and smooth log-RPM bank
blending. Throttle is independent of pitch and controls amplitude, low-pass cutoff
and an authored recorded-midrange presence boost. RPM response is smoothed over
15 ms; throttle attack/release over 45/140 ms. Quiet procedural bass uses one
shared calibration and the whole scenario pack uses one output gain.

Source root RPMs (790/960/1890/2180) are provisional acoustic estimates rather
than tachometer data. The upper bank is pitched about 1.93x at 4200 RPM. Separate
measured on/off-load recordings are not available; the throttle colour is authored
filtering of recorded material. These limitations remain important for production
material selection. H2 now rearranges and retunes source loops in response to
controls, rather than replaying H1's fixed recorded rev timeline.

Files:
- 00_rpm_throttle_overview.wav (34.5 s): 0-15 idle/pull/shift, 15.5-27.5 fixed
  2500 RPM with light/full/medium/closed throttle, 28-34 lift-off/coasting.
- 01_acceleration_shifts_lift.wav (24 s): full authored drive, pulls to 4200 RPM.
- 02_fixed_rpm_throttle.wav (12 s): fixed 2500 RPM; changes at 3, 6 and 9 seconds.
- 03_mid_high_holds.wav (15 s): 2400/3200/4200 RPM at fixed 80% throttle.
- 04_throttle_tone_matched.wav (7.5 s): light/full/closed at matched K-weighted
  segment energy, two seconds each plus half-second gaps; not a gated LUFS test.
- PreparedLoops/: float WAV loop bank, accompanied by attribution in the ZIP.

The first diagnostic render changed throttle volume more than timbre. It remains
in RangeRover_Hybrid_H2_review/ and is not the delivery pack. The final revision
adds recorded midrange presence under throttle and a softer closed-throttle
filter. At fixed RPM, light/full spectral centroids are 181/200 Hz and RMS levels
are approximately -32/-22 dBFS. These diagnose response, not perceived realism.

Validation: known-carrier playback pitch ratio, continuous cursors when rendering
a varying RPM trace in split blocks, zero-input silence, and constant 2500 RPM
during the throttle test passed. Recorded firing-band peaks in the upper holds
are 159.7/212.4/279.8 Hz against nominal V8 values 160/213.3/280 Hz. Delivered
WAVs decode as stereo 48 kHz PCM16 without clipping, at or below an estimated
4x true peak of -6 dBFS. Matched throttle levels differ by less than 0.035 dB.
Source/code/audio hashes, preserved H1 sources, prepared loop WAVs, credit/license
inclusion and ZIP integrity verified. Verification record:
Saved/RallyHandlingQA/range-rover-hybrid-h2-verification.json.

No game source/assets/physics/mute settings changed; Unreal was not launched.
This implements offline control response only. Runtime audio buffering, persistent
filter state, device latency and CPU cost still require a port and measurement.
Owner listening should assess pitch continuity, throttle growl, loop repetition
and high-RPM brightness before integration. All prior audition files are intact.


## Range Rover H2 runtime driving prototype - 2026-10-24

Owner approved H2 and requested live RPM/throttle driving, Range Rover only.
The approved four float recording loops are packaged losslessly in
Content/Audio/RangeRoverHybridH2/loops.gth2 with source attribution and provenance.
RuntimeDependencies stages the bank as UFS and credits/provenance as NonUFS.
The preparation tool retains prepared-loop hashes and generates the exact H2
filter coefficients and calibration gains; original auditions remain untouched.

GTRangeRoverHybridSynth ports continuous fractional stereo cursors, log-RPM bank
crossfades, independent throttle smoothing/filtering/presence/gain, 29 Hz highpass,
and quiet combustion support with the same 32-125 Hz bandpass and shared gains.
The combustion pulse uses an equivalent four-exponential recurrence with eight
persistent voices, avoiding audio-callback allocations. Native output is stereo
48 kHz PCM16; UE performs device-rate conversion. All render state persists across
callbacks; only atomic targets/diagnostics cross threads. The wave retains its
synth until collection so stopping does not invalidate pending callbacks.

GTRangeRoverAudioComponent reads GTDrivetrainComponent GetEngineRpm/GetDriveInput
(after the pawn tick), including reverse pedal mapping, shifts and low range.
Only the exact SK_RangeRover mesh opts in. It plays for the local driver, gates
empty fuel/flooding, reduces misfire gain, and fades on mute/exit with a 25 ms
smoother before stopping the source. Parked RR vehicles are silent. This is the
interior/driver prototype; exterior spatial audio and other cars are deferred.
The existing vehicle SetMuted API also gates H2. Greybox synthesis is suppressed
for RR, while other car defaults are unchanged. The rally controller enables
only RR when an audio device exists; -NoSound QA retains the old mute state.

Launch: Art/play_range_rover_audio.bat, or
powershell -File Art/rally_handling.ps1 -Mode Play -RangeRoverAudio -Label range-rover-h2
The new opt-in switch removes -NoSound and adds -GTRangeRoverAudioTest; the existing
launcher modes/performance profile stay unchanged. Use the existing circuit,
F1 driving information, 1 to reset, 7 for service, F to exit and E for interaction.
No maps, fleet assets, suspension, handling or graphics settings were authored.

Verification:
- Guarded GrandTourEditor Development builds succeeded. Existing engine/compiler
  deprecation warnings remain; no build errors.
- GrandTour.Vehicle.RangeRoverHybridH2 passed: exact split-buffer continuity,
  stereo UE callback contract, scope/driver/engine gates and lossless bank loading.
- Independent Python oracle vs 12 s native render (idle, pull, shifts, lift,
  fixed-RPM throttle and engine gate): maximum error one PCM count; peak -6.53 dBFS,
  final gate silent. Native DSP rendered 12 s in 0.051 s (~0.43% realtime) in the
  isolated CPU test, not an end-to-end frame-time/latency measurement.
- Real-device PIE smoke drive passed: 800-4151 RPM, 71.4 km/h acceleration, full
  throttle/lift/reverse; actual callback frames advanced at 48 kHz. Exit/re-entry,
  public mute/unmute, BMW/Suzuki silence and return to RR passed. All 12 fleet
  mesh identities inspected; only RR matches. Rally and Lidar map hashes unchanged.
- The first drive harness run stopped on a Python b_muted/muted naming error;
  corrected harness and successful rerun are in Saved/AudioH2QA/drive.json.

Reports: Saved/Automation/RangeRoverH2/index.json, Saved/AudioH2QA/comparison.json,
Saved/AudioH2QA/native_render.wav, Saved/AudioH2QA/drive.json, and
Saved/Logs/RangeRoverH2-Drive.log. Re-run Art/range_rover_audio_test.ps1 -Mode Tests
(prepares its independent oracle), then -Mode Drive for the real-device smoke test.
Always run Art/wait_unreal_free.ps1 as its own command before each build/editor
launch, retain the shared reservation, and never terminate an existing Unreal.

Existing source snapshots before edits:
Saved/AudioIntegrationBackups/H2-20261024-135514/.
Listening limitations from H2 remain: Dodge V8 sources, provisional acoustic root
RPMs, highest bank 2180 RPM, authored throttle color rather than measured load
banks. User driving/listening assessment is the next step; subjective realism
and device latency have not been certified by the automated tests.


## Ground audio S1 - 2026-10-24

Owner approved Range Rover H2 in game and requested ground-material sounds.
Scope remains Range Rover only for this first pass. New GTGroundAudioSynth and
GTGroundAudioMix provide procedural tarmac, gravel, dirt, grass, mud/bog, sand,
snow and water textures, without additional source recordings or audio assets.
Layered filtered stereo noise and irregular decaying grains distinguish rolling
beds, loose-stone crunch, vegetation rustle, fine grit and wet churn. These are
procedural approximations for listening review, not field-recorded tyre sounds.

The audio component reads existing wheel contacts, authored surface names,
physical gravel material, wheel tread speed, longitudinal slip, lateral slip
angle, road speed, wetness and water depth. It blends individual wheel materials
with modest left/right placement. Mud/snow patches override their underlying
surface. Water overlays and damps dry-ground layers. Reverse uses absolute
motion; locked/sliding wheels and stationary wheelspin remain audible. No contact
means no ground sound; parked jitter is below a dead zone. Ground gain and
surface targets smooth across callbacks. Fuel loss/flooding gates the engine
separately, allowing tyres to sound while coasting. Vehicle mute, exit and
re-entry continue to control the shared audio source.

Firm grass has no authored soil tag in the physics query. A cosmetic-only cache
reads the existing landscape grass mask at 12.5 Hz for untagged contacts. A short
contact trace confirms that the hit belongs to that landscape/road source, so
bridges or rocks do not inherit the grass mask beneath them. No terrain, traction,
handling, mesh, graphics or other-car source/assets were changed by this pass.

GTRangeRoverSoundWave adds the ground output to the unchanged H2 PCM buffer.
The new layer alone is smoothly bounded to 0.16 amplitude; there is no engine
normalization or ducking. The approved V8 renderer .cpp/.h remain byte-identical.
GroundVolume and console gt.Audio.GroundVolume (0..1, default 1) control the layer;
0 auditions the engine alone. Art/play_range_rover_audio.bat launches the existing
rally circuit with sound. The original default silent QA launch modes remain.

Automated verification passed:
- Ground mapping precedence, mixed-wheel surfaces, subtle stereo placement,
  parked/airborne silence, forward/reverse equality, stationary spin, locked-wheel
  and lateral scrub, water overlay, and callback continuity.
- Silent ground leaves engine PCM untouched; contact/mute fade reaches silence.
- Speed increases rolling energy; slip increases gravel disturbance.
- Eight 3-second native material exports plus engine mix retain headroom. The
  mixed audition peak is -9.52 dBFS. Rolling levels range from -36.34 dBFS RMS
  (tarmac) to -26.81 dBFS (water), with material-specific spectral differences.
- H2 independent Python reference still matches to within one PCM count. Engine
  reference peak remains -6.53 dBFS. Two UE automation tests passed.
- Initial grain calibration failed the rolling loudness check on four materials;
  grain gains were reduced before the successful repeat. Original metrics remain
  in Saved/GroundAudioQA/materials-first-loud-render.json.

Evidence: Saved/Automation/RangeRoverH2/index.json; Saved/GroundAudioQA/materials.json,
verification.json, 01_ground_materials.wav, 02_engine_and_ground.wav and the faded
03_listening_preview.wav. The sequence is Tarmac, Gravel, Dirt, Grass, Mud, Sand,
Snow, Water: three seconds each separated by half a second. Run
Art/range_rover_audio_test.ps1 -Mode Tests and Art/tools/review_ground_audio.py to
reproduce. Live test observations are recorded separately below.

Pre-edit snapshots: Saved/AudioIntegrationBackups/Ground-S1-20261024-141145/.


S1 live contact/device verification: passed on the existing rally map using
Art/range_rover_audio_test.ps1 -Mode Drive -CpuOnly (NullRHI; audio enabled).
The actual gravel contacts and firm grass verge selected the correct layers;
coasting retained ground activity and an airborne car reported zero contacts
and ground activity. Reverse, public mute/unmute, exit/re-entry, two other fleet
cars remaining silent, and return to RR passed. Actual audio callback frames
advanced. Rally and Lidar map hashes remained unchanged. Evidence is preserved
in Saved/GroundAudioQA/drive-nullrhi-passed.json and .log.

Two prior rendered-editor smoke runs were too slow (roughly a few frames/sec)
to pass the timed acceleration assertion; waiting for contact settling alone
did not resolve it. They also returned -1073741819 during failed-test shutdown.
Evidence: drive-startup-stall.json/.log and drive-settled-slow.json/.log in the
same folder. This is not a rendered performance pass or a diagnosis of that
editor problem. The successful NullRHI test establishes physics/contact routing,
source lifecycle and device callbacks, not graphics performance. The ordinary
interactive launcher retains the existing graphics preset unchanged.

2026-10-24 Ground S1 rejected; recorded S2 offline audition
-------------------------------------------------------
The user rejected BOTH the generated material sounds and their driving response.
S1 technical tests did not establish convincing audio or acceptable response.
No runtime, game asset, handling, graphics or engine changes in this S2 pass.

Art/tools/render_ground_audio_s2.py creates an offline recorded-source audition
in Art/Export/VehicleAudio/Ground_Recorded_S2. Original public previews and
source-page/license evidence are under Art/Audio/References/Ground_Recorded_S2.
OBXJohn gravel rolling and kyles gravel stop are CC0 recordings. Grass is a
clearly labelled CC BY 4.0 cloth Foley candidate by BBoz87, NOT tyre-on-grass.
Hayride rolling sources may retain background people/tractor; these are MP3
previews, not production-clean masters. Attribution and exact processing are
saved alongside the samples. No purchased or noncommercial sources are used.

The 24-second authored timeline separates rolling from a single braking event,
keeps rolling during lift/coast, crosses to quieter grass Foley and reaches
silence when stopped. Speed changes gain, mild playback rate and source blend.
The mixed version adds the approved H2 acceleration sample without changing its
gain. This is not live telemetry, an accepted tyre model, or a driving test.
Read LISTENING_GUIDE.txt and verification.json beside the WAVs for exact timing
and numeric checks. Source direction must be auditioned before integration;
genuine grass and broader real speed-range recordings remain unresolved.

2026-10-24 Ground S3: body rumble audition
----------------------------------------
User: recorded S2 is much better, but needs more rumble from the car.
New offline tool Art/tools/render_ground_audio_s3.py retains the S2 ground and
approved H2 engine at their existing gains, adding lowered/filtered recorded
gravel for central low body vibration and occasional dull bump textures.
This is designed body sound, not an actual Range Rover suspension recording.
Speed/surface and bump cues are authored, not runtime telemetry. Grass remains
the explicitly provisional cloth Foley from S2. No runtime or game changes.

Outputs: Art/Export/VehicleAudio/Ground_Recorded_S3_BodyRumble/.
01 is the 24s V8 mix; 02 ground/body alone; 03 repeats the same 8s segment before
and after with a 1s gap, preserving engine and existing texture gain.
Finite/headroom and parked-silence checks passed. Full mix peak -4.54 dBFS.
Hashes confirm original ground sample, controls and approved engine unchanged.
No perceptual acceptance or live driving verification is claimed.

2026-10-24 S3 recorded ground/body runtime integration (Range Rover only)
---------------------------------------------------------------------
User approved the S3 body-rumble sample and requested in-game driving tests.
Replaced the S1 generated ground-noise DSP with continuous recorded gravel and
provisional grass Foley loops, recorded gravel stop onset, and recorded-texture
body rumble/thumps. Art/tools/prepare_ground_audio_s3.py bakes the approved source
processing into Content/Audio/RangeRoverGroundS3/recordings.gts3 (48 kHz stereo).
The bank, credits and provenance are staged through GrandTour.Build.cs. Audio
callbacks interpolate resident immutable PCM and never perform file loading.

Road/tread speed controls texture rate and gain. Slip uses speed-normalized
thresholds with onset/re-arm hysteresis; sustained slip adds recorded crunch
without repeatedly restarting the short stop sample. Body rumble follows actual
travel speed, including coasting; stationary wheelspin can disturb gravel but
cannot make travelling body rumble. Suspension compression-rate impulses trigger
varied subdued body thumps, with a cooldown to avoid a constant rattle. Contact
loss, mute and exit fade out. Per-wheel surface weights retain gravel/grass
transitions and subtle stereo placement. Other materials currently receive only
quiet body-rumble fallback, not new dedicated recordings or the rejected S1 noise.
Grass remains the approved provisional cloth Foley; no authenticity claim added.

Range Rover mesh gating, other-car behavior, H2 renderer, maps, handling and
visual settings are unchanged. gt.Audio.GroundVolume 0 disables the entire ground
and body layer; 1 restores it. Art/play_range_rover_audio.bat remains the launcher.

Guarded editor build succeeded after fixing two local C++ compile errors.
Both GrandTour.Vehicle.GroundAudio and RangeRoverHybridH2 automation suites passed:
recording bank, sample continuity across callbacks, silent engine-buffer identity,
contact/mute silence, headroom, speed/slip response, onset-only skid, bump impulse,
parked jitter, surface mapping and mixed wheel contacts. Independent H2 reference
still matches within one PCM count. Ground material/native engine-mix exports
are in Saved/GroundAudioQA; test report in Saved/Automation/RangeRoverH2.
Original source/report snapshots: Saved/AudioIntegrationBackups/Ground-S3-runtime-20261024-163551/.
Live test result is recorded below after completion. These checks do not establish
subjective driving sound quality or rendered performance.

S3 live check passed using the existing rally map with NullRHI and audio enabled.
Recorded-bank readiness and audio callbacks were confirmed. Actual gravel driving
reached 87.7 km/h; grass reached 39.2 km/h. Body speed remained active during lift,
suspension thump counters advanced in motion and remained zero at idle, and
contact loss produced zero ground activity. Reverse, mute/unmute, exit/re-entry,
BMW/Suzuki silence and disabled RR component ticks, fleet identity, and return to
RR passed. Rally and Lidar map hashes were unchanged. Evidence is copied to
Saved/GroundAudioQA/drive-s3-recorded.json and .log. NullRHI verifies physics/audio
routing, not rendered frame rate or subjective sound. Normal play uses unchanged
graphics via Art/rally_handling.ps1 -Mode Play -RangeRoverAudio -Label ground-s3.

2026-10-24 S4 speed dynamics
---------------------------
User feedback: close, but little dynamism or change with speed. Audit found the
S3 rate, gain and bank blend saturated at 60 km/h, while a .24 plus square-root
level curve made low-speed rolling disproportionately loud.

GTGroundAudioSynth now normalizes travel/tread speed through 160 km/h. Rolling
uses a quieter crawl and a wider level curve, .45..1.8 recording playback rate,
speed-dependent 1.6..8.6 kHz tone filtering, and a broader source crossfade.
Body rumble has its own slower rate progression and increasing weight with speed.
Existing contact, slip, suspension impulse and mute behavior remain. No new noise
sources, engine edits, bank changes, other-car changes or graphics/handling edits.

Guarded editor build and both audio automation suites passed. Added native signal
checks at 5/20/40/60/80/100/120/160 km/h verify continued growth above the old cap,
changing normalized sample differences (not just gain), and headroom with the V8
at 4200 RPM and 85% throttle. Ground RMS grows monotonically: .00470, .01058,
.01855, .02564, .03344, .04121, .04923, .06457. 60 to 100 km/h increases about
4.1 dB; 20 to 100 about 11.8 dB. Loaded engine plus ground did not clip. H2 reference
still matches within one PCM count. This is numerical verification; user driving
remains the subjective sound gate. Contact routing was not changed and was verified
in the preceding S3 live smoke test; no new S4 live smoke-test claim is made.

Evidence: Saved/GroundAudioQA/s4_speed_response.json, s4_speed_ground.wav and
s4_speed_with_v8.wav (4 seconds per listed speed plus half-second gaps).
Backup: Saved/AudioIntegrationBackups/Ground-S4-speed-20261024-164802/.
Normal play launch label: ground-s4-speed.

2026-10-24 S5 rumble level
-------------------------
User requested more rumble after S4 driving. Doubled only the recorded continuous
body-rumble contribution (+6.02 dB before the existing safety knee). S4 speed gain,
rate and tone progression, gravel/grass detail, discrete bumps, approved engine
and all other-car behavior remain unchanged. No source-bank regeneration.
Guarded editor build and both audio automation suites passed. Native 5-160 km/h
exports retain progressive level/texture response and do not clip when combined
with the loaded 4200 RPM V8. H2 reference remains within one PCM count.
S5 speed metrics: Saved/GroundAudioQA/s5_rumble_speed_response.json. Backup:
Saved/AudioIntegrationBackups/Ground-S5-rumble-20261024-165430/.
Normal play launch label: ground-s5-rumble. Subjective balance awaits user driving.
