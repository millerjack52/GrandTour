"""Check the cm/Y-up bridge against the original Mud_001 VS instruction slice."""
from pathlib import Path
import hashlib
import json
import random
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = Path('C:/Agents/MudRunnerResearch')
sys.path.insert(0, str(RESEARCH))
from validate_shader_arithmetic import parse, execute

program = parse('SpinTires_Mud_001.asm.txt', 'vs_3_0')
start = next(i for i, (op, a) in enumerate(program)
             if op == 'mul' and a == ['r1.xy', 'r0.xzzw', 'c35.z'])
end = next(i for i, (op, a) in enumerate(program[start:], start)
           if op == 'mad' and a == ['r2.xyz', 'r1', 'c35.w', 'r0'])
program = [(op, a) for op, a in program if op == 'def'] + program[start:end+1]
rng = random.Random(15)
error = uv_error = 0.
for _ in range(1000):
    xyz = np.array([rng.uniform(-1200, 1200), rng.uniform(-10, 100), rng.uniform(-1200, 1200)])
    tex = np.array([rng.random() for _ in range(4)])
    presence = rng.random()
    seen = []
    def sample(uv):
        seen.append(uv.copy())
        return tex
    result = execute(program, {'r0': [*xyz, 1], 'r6': [presence, 0, 0, 0]}, {'s2': sample})['r2'][:3]
    host = xyz[[0, 2, 1]] * 100 + (tex[[0, 2, 1]] - .5) * 22 * presence
    error = max(error, float(np.max(np.abs(host - result[[0, 2, 1]] * 100))))
    uv_error = max(uv_error, float(np.max(np.abs(seen[0] - xyz[[0, 2]] * .24))))
assert error < 1.e-5 and uv_error < 1.e-5, (error, uv_error)
shader = RESEARCH / 'shaders/SpinTires_Mud_001.asm.txt'
noise = ROOT / 'Art/Export/MudLab/NativeReference/env_mud_noise__uncmp.png'
report = dict(shader=str(shader), shader_sha256=hashlib.sha256(shader.read_bytes()).hexdigest(),
              noise_png=str(noise), noise_sha256=hashlib.sha256(noise.read_bytes()).hexdigest(),
              cases=1000, max_position_error_cm=error, max_uv_error=uv_error,
              source_formula='(sample(noise, worldXZ_metres*.24).xyz-.5)*.22*presence',
              unreal_formula='(sample(noise, worldXY_cm*.0024).rbg-.5)*22*presence',
              source_normal_excludes_noise=True)
# Exercise the separate host-grid adapter using the extracted source texture.
# This checks folded triangles directly, rather than only repeating its formula.
pixels = np.asarray(Image.open(noise), dtype=float)[:, :, [0, 2, 1]] / 255.
def sample_noise(xy):
    uv = xy * .0024 * 128 - .5
    ij = np.floor(uv).astype(int)
    f = uv - ij
    x, y = ij[..., 0] % 128, ij[..., 1] % 128
    a = pixels[y, x] * (1-f[..., 0, None]) + pixels[y, (x+1) % 128] * f[..., 0, None]
    b = pixels[(y+1) % 128, x] * (1-f[..., 0, None]) + pixels[(y+1) % 128, (x+1) % 128] * f[..., 0, None]
    return a * (1-f[..., 1, None]) + b * f[..., 1, None]
y, x = np.mgrid[:641, :641]
xy = np.stack([x*12.5-60000, y*12.5-60000], axis=-1)
raw = (sample_noise(xy)-.5)*22
filtered = (sum(sample_noise(xy+[dx,dy]) for dx in [-6.25,6.25] for dy in [-6.25,6.25])*.25-.5)*22
filtered[..., :2] = np.clip(filtered[..., :2], -2.5, 2.5)
def areas(displacement):
    p = xy + displacement[..., :2]
    a, b, c, d = p[:-1,:-1], p[:-1,1:], p[1:,:-1], p[1:,1:]
    cross = lambda v,w:v[...,0]*w[...,1]-v[...,1]*w[...,0]
    return np.r_[cross(b-a,c-a).ravel(),cross(d-b,c-b).ravel()]
before, after = areas(raw), areas(filtered)
assert np.min(after) > 0, 'Host-grid adapter folded a triangle'
report['host_grid'] = dict(triangles=len(after), raw_folded=int(np.sum(before<=0)),
                          filtered_folded=int(np.sum(after<=0)),
                          min_filtered_doubled_area_cm2=float(np.min(after)),
                          filtered_height_range_cm=[float(np.min(filtered[...,2])),float(np.max(filtered[...,2]))],
                          filtered_height_rms_cm=float(np.std(filtered[...,2])))
(ROOT / 'Art/Export/BenmoreWoodland/native-clods-evidence.json').write_text(json.dumps(report, indent=2))
print('1000 native displacement cases passed:', error, 'cm maximum difference')
