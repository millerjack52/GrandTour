"""Compare fixed-step evidence and assemble the actual engine capture sequence."""
from pathlib import Path
import json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/BenmoreGaea/FlowWaves'
before=json.loads((OUT/'motion-before.json').read_text())
after=json.loads((OUT/'motion-after.json').read_text())
assert before['ok'] and after['ok']
installed_at=(OUT/'install-report.json').stat().st_mtime
assert (OUT/'motion-after.json').stat().st_mtime>installed_at, 'Motion report predates the current installation'
assert all(Path(p).stat().st_mtime>installed_at for p in after['images']), 'A capture predates the current installation'
a=[s for s in before['samples'] if s['mode']=='Impulse']
b=[s for s in after['samples'] if s['mode']=='Impulse']
assert len(a)==len(b)==24
physical_error=max(abs(x[k]-y[k]) for x,y in zip(a,b) for k in ['time','min_cm','max_cm','rms_cm'])
assert physical_error<1e-6,physical_error
frames=[Image.open(OUT/f'Ambient{i:02d}_After.png').convert('RGB').crop((0,275,1280,445)) for i in range(60)]
palette=frames[0].quantize(colors=256)
quantized=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
quantized[0].save(OUT/'Ambient_After.gif',save_all=True,append_images=quantized[1:],duration=[80,80,90]*20,loop=0)
water=[np.asarray(im).astype(float) for im in frames]
delta=[float(np.mean(np.abs(y-x))) for x,y in zip(water,water[1:])]
report=dict(ok=True,physical_impulse_sample_max_error_cm=physical_error,ambient_frames=60,
    sequence_fps=12,render_fps_measured=False,driving_tested=False,
    water_strip_adjacent_pixel_difference_mean=float(np.mean(delta)),
    water_strip_adjacent_pixel_difference_max=max(delta),
    note='Pixels quantify motion only, not realism. Clouds/reflections also evolve. GIF wraps after 5 seconds; wrap is not a runtime reset.')
(OUT/'motion-comparison.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
