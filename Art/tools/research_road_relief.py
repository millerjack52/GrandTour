"""Read-only native instruction/asset investigation; no compiled map import."""
from pathlib import Path
import hashlib,json,struct,sys
import numpy as np
from PIL import Image
from verify_mudrunner_editor_kernels import Harness
from verify_mudrunner_editor_splines import SplineHarness
from unicorn.x86_const import *
ROOT=Path(__file__).resolve().parents[2]
SRC=Path('C:/Program Files (x86)/Steam/steamapps/common/MudRunner - Editor')
OUT=ROOT/'Art/Export/MudRunnerEditorResearch/RoadRelief';OUT.mkdir(exist_ok=True)
h=Harness();cases=[]
for width in [3.,7.,11.]:
 for aspect in [1.,2.,4.]:
  for distance in [0.,2.,17.3,101.]:
   for half in [1.,3.5,6.]:
    h.reset_stack();p=h.heap+0x400;h.uc.reg_write(UC_X86_REG_RDI,p)
    h.f(p,width);h.f(p+12,aspect)
    h.xmm(UC_X86_REG_XMM8,distance);h.xmm(UC_X86_REG_XMM12,half);h.xmm(UC_X86_REG_XMM10,.5)
    h.uc.emu_start(0x140249e56,0x140249e75,count=30)
    get=lambda r:struct.unpack('<f',struct.pack('<I',h.uc.reg_read(r)&0xffffffff))[0]
    u,v=get(UC_X86_REG_XMM8),get(UC_X86_REG_XMM2)
    assert abs(u-distance/(width*aspect))<.000002 and abs(v-(.5-half/width))<.000002
    cases.append([distance,width,aspect,half,u,v])
assets={}
for name in ['dirt_road','grass_road','dirt_path']:
 p=SRC/f'Media/prebuild/common/hmoffset_{name}__s.tga'
 im=Image.open(p).convert('RGB');red=np.asarray(im)[:,:,0];im.save(OUT/f'{name}.png')
 diffuse=SRC/f'Media/_t/overlays_{name}__d_a.dds';dim=Image.open(diffuse).size
 assets[name]=dict(source=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=im.size,diffuse_size=dim,aspect=dim[0]/dim[1],red_min=int(red.min()),red_max=int(red.max()),relief_cm=[(float(red.min())/255-.5)*384,(float(red.max())/255-.5)*384])
(OUT/'verification.json').write_text(json.dumps(dict(ok=True,native_uv_cases=len(cases),uv_cases=cases,assets=assets,shader='Editor.fxs overlayHMOffsetPS: (r-.5)*alpha*.06; MAX_HEIGHTMAP_VALUE=64m',limitations=['Native GPU rasterization and full rebuild not emulated.','Bilinear level-zero wrap is an explicit host sampling adapter; complete inherited D3D filter state remains unverified.']),indent=2))
lines=['// Generated from executed native UV arithmetic, not from our C++ implementation.','namespace GTRoadReliefOracle {','static const float UV[][6]={']
for c in cases:lines.append('{'+','.join(f'{v:.9e}f' for v in c)+'},')
lines+=['};','static const float Derivative[][2]={']
sh=SplineHarness();knots=[0,3,9,17,25];values=[1,-2,4,2,8];sh.construct(knots,values)
for t in [-1,0,1,3,5,9,12,17,20,25,26]:
 sh.reset_stack();sh.uc.reg_write(UC_X86_REG_RCX,sh.obj);sh.xmm(UC_X86_REG_XMM1,t)
 sh.uc.emu_start(0x140184b90,sh.stop,count=10000)
 value=struct.unpack('<f',struct.pack('<I',sh.uc.reg_read(UC_X86_REG_XMM0)&0xffffffff))[0]
 lines.append('{'+f'{t:.9e}f,{value:.9e}f'+'},')
lines+=['};','}']
(ROOT/'Source/GrandTour/Terrain/GTRoadReliefOracle.inl').write_text('\n'.join(lines))
print(json.dumps(dict(native_uv_cases=len(cases),assets=assets),indent=2))
