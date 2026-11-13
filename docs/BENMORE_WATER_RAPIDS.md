# Benmore shallow rapids, 2026-10-11

The owner requested visible turbulence and little rapids in shallow sections,
building on the stronger-motion pass. `Gaea/WaterRapids` is a material variant
over the same accepted river geometry, hydraulic bake and car simulation.

Rapids intensity follows the baked depth and speed. It ramps in from 2.5–10 cm
depth, stays strongest through 28 cm, fades out by 72 cm, and ramps with currents
from 0.35–1.05 m/s. Broad spatial variation keeps it patchy. Bank and distance
fades are retained. The ford's baked depths are mostly 10–25 cm and speed is
approximately 1 m/s.

Two uneven standing-crest bands (3 m and 5.2 m wavelengths) fit the existing
render mesh. Their crests wrinkle over time while a separate swirling froth
pattern travels downstream at the local current velocity. Fine ripples become
stronger within the rapids. The foam is broken and bright enough to cover the
water at breaking crests, with darker gaps and quieter stretches between them.
The deep pool/lake and slow-flow gates prevent whitewater there.

Standing crests share the existing cosmetic height budget: 40% of the previous
22%-of-depth bound is reserved in proportion to rapids intensity, and the new
crest contribution is bounded by that same 8.8% of depth. The overall bound is
unchanged. This is an authored visual riffle model, not a new turbulent-fluid
solver or a claim of physically resolved whitewater.

The material parameter `RapidsIntensity` defaults to 1 and can fade the additional
effect to 0. Source: `Art/Unreal/benmore_water_rapids.py`. Install with
`Art/benmore_water_motion.ps1 -Variant Rapids`; fresh-process validation uses
`-Variant Rapids -Mode Verify`. The shared capture/preview scripts support both
the Motion and Rapids variants.

Evidence is in `Art/Export/BenmoreGaea/WaterRapids_20261011/`. The comparison uses
the accepted motion-pass engine frames as its baseline, with verified identical
placement/depth snapshots, camera and water-clock samples. The first candidate
was too subdued; its representative frame and report remain as `Initial_10.png`
and `install-initial-report.json`. That first capture also exposed a list/tuple
comparison issue in the baseline-camera assertion; numeric camera values were
identical and the serializer now uses lists consistently.

The revised install completed successfully and exited cleanly. Materials compiled,
the map saved and reloaded with all preservation snapshots matching, and all four
surfaces had `RapidsIntensity=1`. In normal PIE, their clocks advanced together
from 6.3024 to 7.3025 seconds. The revised capture has visibly broken white crests;
the 24-frame, three-second comparison shows the froth changing and travelling
through the standing-wave zones. This is a controlled animation capture, not a
game-performance benchmark. Deeper/slow-water exclusion is authored into the
depth/speed gates; this capture shows the shallow ford.

Rollback is `Gaea/L_Benmore_BeforeWaterRapids` or the previous `Gaea/WaterMotion`
material bindings. No channel or shared spray reset is required.
