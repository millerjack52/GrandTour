"""Rebuild native byte lookup tables and independent SM3 pixel-normal fixtures."""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np
from PIL import Image
sys.path.insert(0,'C:/Agents/MudRunnerResearch')
import re_tools as native
from validate_shader_arithmetic import parse,execute
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/SiberianShowcase/WaveResearch';OUT.mkdir(exist_ok=True)
(OUT/'native-wave-tables.asm.txt').write_text('\n'.join(native.dump(0x1408e5ad4,0x1408e5ee9,show=False)))
f=np.float32;pi=f(math.pi);step=f(.19634954631328583)
y,x=np.mgrid[:256,:256]
angle=np.arctan2((y.astype('float32')/f(255)-f(.5))*2,(x.astype('float32')/f(255)-f(.5))*2).astype('float32')
k=np.trunc((angle+pi)/step);lo=k*step-pi;hi=(k+1)*step-pi
enc=lambda v:np.floor(np.minimum((v+1)*f(.5)*f(256),255)+f(.5)).astype('uint8')
dirs=np.stack([enc(np.cos(lo)),enc(np.sin(lo)),enc(np.cos(hi)),enc(np.sin(hi))],-1)
blend=np.zeros_like(dirs);blend[:,:,3]=np.floor(np.clip((angle-lo)/step,0,1)*255+.5).astype('uint8')
s=np.arange(256,dtype='float32')/256;k=np.trunc(s/f(.1));a=k*f(.1);b=(k+1)*f(.1)
speed=np.stack([np.floor(a*255+.5),np.floor(b*255+.5),np.floor(np.clip((s-a)/f(.1),0,1)*255+.5),np.zeros(256)],-1).astype('uint8')[None]
# Dispatch copies speed data across the bottom half of the atlas with point sampling.
Image.fromarray(np.concatenate([dirs,blend])).save(OUT/'direction.png')
Image.fromarray(speed).save(OUT/'speed.png')
files=['water_constructor.asm.txt','shaders/SpinTires_Water_000.asm.txt','shaders/SpinTires_Water_001.asm.txt','shaders/SpinTires_WaterCompute_007.asm.txt']
(OUT/'provenance.json').write_text(json.dumps({'exe_sha256':hashlib.sha256(native.P.__data__).hexdigest(),'sources':{n:hashlib.sha256((native.OUT/n).read_bytes()).hexdigest() for n in files},'direction_sectors':32,'direction_size':[256,512],'speed_size':[256,1],'imports':{'0x140994e08':'atan2f','0x140994c48':'sinf','0x140994ca0':'cosf'}},indent=2))
# The original shader is interpreted independently, using a known source texture
# as the wave sampler. This checks table addressing, swizzles, blend order and normals.
wave=np.array(Image.open(ROOT/'Art/Export/MudLab/NativeReference/env_water_waves__d_a_uncmp.png'),dtype=float)/255
def sample(uv):
 p=np.asarray(uv)*512-.5;ij=np.floor(p).astype(int);fx,fy=p-ij;x,y=ij
 return (wave[y%512,x%512]*(1-fx)+wave[y%512,(x+1)%512]*fx)*(1-fy)+(wave[(y+1)%512,x%512]*(1-fx)+wave[(y+1)%512,(x+1)%512]*fx)*fy
atlas=np.zeros((512,768,4));atlas[:,512:]=np.concatenate([dirs,blend])/255
# Native dispatch writes the one-row speed texture from y=255.5 through 768.5:
# it tiles/clamps down the lower region. Only row 256 is sampled for speed.
atlas[256,512:]=speed[0]/255
def lookup(uv):
 x,y=np.clip(np.floor(np.asarray(uv)*[768,512]).astype(int),[0,0],[767,511]);return atlas[y,x]
program=parse('SpinTires_Water_000.asm.txt')
end=next(i for i,(op,a) in enumerate(program) if op=='nrm' and a==['r2.xyz','r1'])
program=[(op,a) for op,a in program[:end+1] if op!='texkill']
pixels=[];inputs=[];max_error=0
for y in range(8):
 for x in range(8):
  uv=np.array([(x+.5)/8,(y+.5)/8]);theta=(uv[0]*2-1)*math.pi;d=np.array([math.cos(theta),math.sin(theta)])
  speed_value=y*.12;world=uv*[13.7,15]-[6,3];dist=.2+uv[1]*50;clock=1.25
  reg=execute(program,{'v0':[world[0],0,world[1],1],'v2':[0,0,0,0],'v4':[*d,speed_value,.4],'v5':[0,1,0,0],'c1':[-5.12*clock,19.723,0,0],'c24':[world[0],dist,world[1],0]}, {'s2':sample,'s4':lookup})
  expected=reg['r2'][[0,2,1]]
  ij=np.clip(np.floor((d+1)*128+[1/6,.5]).astype(int),0,255);xx,yy=ij
  axes=dirs[yy,xx]/255*2-1;blend_value=blend[yy,xx,3]/255
  si=int(np.clip(math.floor(speed_value**2*256+1/6),0,255));bands=speed[0,si,:3]/255
  p0=[np.dot(axes[:2],world),np.dot([-axes[1],axes[0]],world)];p1=[np.dot(axes[2:],world),np.dot([-axes[3],axes[2]],world)]
  phase=np.array([-5.12*clock,19.723]);vals=[sample((p+phase*b)*.14) for b in bands[:2] for p in [p0,p1]]
  v=(vals[0]*(1-blend_value)+vals[1]*blend_value)*(1-bands[2])+(vals[2]*(1-blend_value)+vals[3]*blend_value)*bands[2]
  n=(v[:2]-.50195998)*2*speed_value*(.2+.8*(1-np.clip((dist-16)/24,0,1)))
  actual=np.r_[d*n[0]+np.array([-d[1],d[0]])*n[1],math.sqrt(max(0,1-np.dot(n,n)))*.5];actual/=np.linalg.norm(actual)
  error=float(np.max(abs(actual-expected)));max_error=max(max_error,error)
  assert error<1e-4,(x,y,error)
  pixels.append((expected*.5+.5).tolist())
(OUT/'sampling-oracle.json').write_text(json.dumps(dict(ok=True,size=8,time=1.25,pixels=pixels,cpu_max_error=max_error),indent=2))
print('Native lookup and 64 assembly fixtures generated; CPU maximum error',max_error)
