"""Verify the installed Plants/GRASS programs and record new shader evidence."""
from pathlib import Path
import json,zlib,struct,hashlib,math,random,zipfile,shutil
R=Path(__file__).resolve().parents[2];O=R/'Art/Export/BenmoreWoodland/GrassResearch';O.mkdir(parents=True,exist_ok=True)
G=Path('C:/Program Files (x86)/Steam/steamapps/common/MudRunner');RE=Path('C:/Agents/MudRunnerResearch')
cache=(G/'ShaderCache.sdc').read_bytes();b=zlib.decompress(cache[12:]);assert len(b)==struct.unpack_from('<I',cache,8)[0]
j=json.loads((RE/'stage4_plants_inventory.json').read_text())[0];rows=[]
for s in j['unique_shaders']:
 if s['file'].endswith(('_007.asm.txt','_008.asm.txt','_009.asm.txt')):
  off=int(s['offset'],16);code=b[off:off+s['bytes']];assert code[:4] in [bytes.fromhex('0003feff'),bytes.fromhex('0003ffff')]
  fx=b.rfind(bytes.fromhex('0109fffe'),int(j['start'],16),off)
  assert b'GRASS\0' in b[fx-100:fx]
  rows.append(dict(file=s['file'],offset=s['offset'],shader_sha256=hashlib.sha256(code).hexdigest(),fx_offset=hex(fx)))
  shutil.copy2(RE/'shaders'/s['file'],O/s['file'])
shutil.copy2(RE/'shaders/SpinTires_PlantsGrass_effect.fx.txt',O/'PlantsGrass_effect.fx.txt')
with zipfile.ZipFile(G/'MeshCache.zip') as z:
 raw=z.read('grass_grass_short');p=4+struct.unpack_from('<I',raw)[0];start=p+241;vertices=[]
 for i in range(16):
  angle,height,radius=struct.unpack_from('<3f',raw,start+i*32)
  wind=raw[start+i*32+28]/255
  assert wind==(1 if height>.05 else 0)
  vertices.append(dict(index=i,height_m=height,wind_weight=wind,packed_vertex=raw[start+i*32+20:start+i*32+32].hex()))
# Independent register-sequence reference versus the reduced oscillation.
rng=random.Random(810);max_error=0
for _ in range(1000):
 t=rng.uniform(-10000,10000)
 phases=[((t*f+.5)%1)*6.28318548-3.14159274 for f in [.0636619776,.216450721,.598422587]]
 ref=math.cos(phases[0])*math.cos(phases[1])+.25*math.sin(phases[2])
 simplified=math.cos(t*.4)*math.cos(t*1.36)+.25*math.sin(t*3.76)
 max_error=max(max_error,abs(ref-simplified))
assert max_error<.01
(O/'evidence.json').write_text(json.dumps(dict(shader_cache_sha256=hashlib.sha256(cache).hexdigest(),shaders=rows,mesh_sha256=hashlib.sha256(raw).hexdigest(),vertices=vertices,wind_formula_max_error=max_error,source_read_only=True),indent=2))
(O/'PLAN_AND_FINDINGS.txt').write_text('''Verified installed MudRunner Plants/GRASS shader, 2026-10-15

Evidence: Plants_009 vertex program and Plants_008 pixel program share the
GRASS + NIGHTLIGHTING + SHADOWMAP + VERTEXLIGHTING FX block at 0x11fda5c.
The separate FAR variant is Plants_007. The source grass mesh is 16 vertices,
8 triangles. Declaration offset 28 is UBYTE4N TEXCOORD3: x is exactly 1 at
every blade top and 0 at every root. The previous OBJ export discarded it.
On this verified mesh, local height >5 cm reproduces all 16 values exactly.

Recovered equations:
phase = Time + 43.3709984*packedRoot.x + 17.9130001*packedRoot.y.
wave = cos(.4*phase)*cos(1.36*phase) + .25*sin(3.76*phase).
The implementation retains the original frac/radian constants rather than
rounded frequencies. Wave amplitude is .04 metres times vertex wind weight.
Direction components are (type/4,1-type/4), with type=floor(packedByte*16).
The displaced vertex direction is normalized back to the original blade
length. Type 15 removes the plant by -1000 metres. Source deflection then uses
saturate((height-.1)*2.5), deflector alpha, a 4*deflector.z height gate,
2*(deflector.xy-.5) horizontal displacement and -.8 vertical displacement.
Pixel discard is diffuseAlpha*baseAlpha*distanceFade < g_fAlphaRef. This is
alpha testing, not a translucent grass surface. Source tint is decoded from
the packed state's low nibble. Terrain lightmaps, headlights and fog are also
present; those belong to the source renderer and cannot be copied as UE light.

Implementation plan:
1. Preserve the native mesh, source diffuse/alpha, physical root tracking,
   64 cm contacts and persistent damage already present in the host.
2. Add the verified root-pinned wind and length preservation to a new owned
   grass material. Use instance pivot coordinates so phase stays fixed as
   the streamed grass window moves. Keep centimetre conversions explicit.
3. Use the source alpha-times-fade rule and expose alpha threshold. Keep UE
   foliage lighting, shadows and fog as an explicit renderer adapter.
4. Bind the new material only in Benmore Woodland. Check source arithmetic,
   shader compilation, captures, bent/removed state and repeat rendering cost.

Host differences: source block coordinates are packed bytes; the host derives
stable normalized phase seeds from each instance's world pivot. Host state
type is 2 (0x20) until removed. Deflector direction and compression removal
gate remain the previously documented UE adapters. Exact source lightmap
bindings, runtime alpha threshold and fade distances are not claimed recovered.
No water, mud physics, source game files or original Benmore assets are edited.
''')
print('Verified grass wind weights, shader variant and 1000 phase comparisons',max_error)
