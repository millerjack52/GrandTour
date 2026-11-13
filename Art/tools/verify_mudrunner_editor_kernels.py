"""Differential checks against captured x64 instructions in an isolated emulator.

No code injection, game/editor memory writes, native map builds or vehicle input.
The candidate generator uses preallocated C++ vector storage; only CRT rand is
stubbed with a sequence checked against the installed MSVCR110 runtime.
"""
import ctypes, hashlib, json, struct
import numpy as np
from mudrunner_editor_re import EditorCode, OUT
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *

F=np.float32
class Random:
    def __init__(self,seed): self.state=seed;self.calls=0
    def rand(self):
        self.state=(self.state*214013+2531011)&0xffffffff;self.calls+=1
        return (self.state>>16)&32767

def model_patterns(budget,seed):
    rng=Random(seed);patterns=[]
    for _ in range(16):
        points=[]
        for _ in range(budget//4):
            best=None;best_score=F(np.finfo('f4').max)
            for _ in range(min(2*len(points),3)+1):
                z=F(F(F(rng.rand())/F(32767)-F(.5))*F(8))
                x=F(F(F(rng.rand())/F(32767)-F(.5))*F(8))
                radial=F(F(F(x*x)*F(.005))+F(F(z*z)*F(.005)))
                score=F(0)
                with np.errstate(divide='ignore'):
                    for px,pz in points:
                        dx=F(x-px);dz=F(z-pz)
                        d2=F(F(dz*dz)+F(dx*dx))
                        score=F(F(F(F(8)/d2)+score)+radial)
                if best_score>score:best=(x,z);best_score=score
            if best is not None:points.append(best)
        patterns.append(np.asarray(points,dtype='<f4').reshape(-1,2))
    return patterns,rng.calls

class Harness:
    def __init__(self):
        self.editor=EditorCode();self.uc=Uc(UC_ARCH_X86,UC_MODE_64)
        c=self.editor;u=self.uc
        u.mem_map(c.base,(c.pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
        u.mem_write(c.base,bytes(c.image))
        self.heap=0x20000000;self.stack=0x30000000;self.stub=0x40000000;self.stop=self.stub+0x100
        u.mem_map(self.heap,0x200000);u.mem_map(self.stack,0x20000);u.mem_map(self.stub,0x1000)
        u.mem_write(self.stub,b'\xc3');u.mem_write(self.stop,b'\x90')
        rand_iat=next(a for a,n in c.imports.items() if n=='MSVCR110.dll:rand')
        u.mem_write(rand_iat,struct.pack('<Q',self.stub))
        def random_hook(u,address,size,data):u.reg_write(UC_X86_REG_EAX,self.rng.rand())
        u.hook_add(UC_HOOK_CODE,random_hook,begin=self.stub,end=self.stub)
        # Keep the CRT normal SSE rounding mode; no flush-to-zero shortcuts.
        u.reg_write(UC_X86_REG_MXCSR,0x1f80)
    def f(self,address,value):self.uc.mem_write(address,struct.pack('<f',value))
    def xmm(self,reg,value):self.uc.reg_write(reg,struct.unpack('<I',struct.pack('<f',value))[0])
    def reset_stack(self):
        sp=self.stack+0x10008;self.uc.mem_write(sp,struct.pack('<Q',self.stop));self.uc.reg_write(UC_X86_REG_RSP,sp);return sp
    def patterns(self,budget,seed):
        u=self.uc;self.rng=Random(seed);self.reset_stack()
        outer=self.heap;bank=outer+0x100;brush=outer+0x400
        u.mem_write(outer,struct.pack('<QQQ',bank,bank+16*24,bank+16*24))
        u.mem_write(brush+0x60,struct.pack('<I',budget))
        for i in range(16):
            p=self.heap+0x1000+i*0x4000
            u.mem_write(bank+i*24,struct.pack('<QQQ',p,p,p+0x4000))
        u.reg_write(UC_X86_REG_RCX,outer);u.reg_write(UC_X86_REG_RDX,brush)
        u.emu_start(0x140252ad0,self.stop,timeout=30000000,count=500000000)
        assert u.reg_read(UC_X86_REG_RIP)==self.stop,'Emulator did not finish'
        result=[]
        for i in range(16):
            a,b,_=struct.unpack('<QQQ',u.mem_read(bank+i*24,24))
            result.append(np.frombuffer(u.mem_read(a,b-a),'<f4').reshape(-1,2).copy())
        return result,self.rng.calls
    def density(self,density,threshold,multiplier,attenuation,seed):
        # Execute the actual final density gate, given already computed inputs.
        # This tests arithmetic/branch boundaries, not upstream mask sampling.
        u=self.uc;self.rng=Random(seed);self.reset_stack();rbp=self.heap+0x900;brush=self.heap+0x400
        u.reg_write(UC_X86_REG_RBP,rbp);u.reg_write(UC_X86_REG_RDI,brush)
        self.f(brush+0x5c,threshold);self.f(rbp-0x44,multiplier)
        self.xmm(UC_X86_REG_XMM10,density);self.xmm(UC_X86_REG_XMM13,attenuation)
        stops={0x140253fd0:True,0x140255945:False};out=[]
        def stop(u,address,size,data):out.append(stops[address]);u.emu_stop()
        hooks=[u.hook_add(UC_HOOK_CODE,stop,begin=a,end=a) for a in stops]
        try:u.emu_start(0x140253f73,self.stop,timeout=1000000,count=1000)
        finally:
            for h in hooks:u.hook_del(h)
        assert len(out)==1
        return out[0],self.rng.calls
    def road_alpha(self,distance,length):
        u=self.uc;self.reset_stack();curve=self.heap+0x500
        u.reg_write(UC_X86_REG_R15,curve);u.reg_write(UC_X86_REG_RDX,0);self.f(curve+0x38,length)
        for reg,value in [(UC_X86_REG_XMM8,distance),(UC_X86_REG_XMM9,1),(UC_X86_REG_XMM10,.5),(UC_X86_REG_XMM11,0)]:self.xmm(reg,value)
        u.emu_start(0x140249dca,0x140249e56,timeout=1000000,count=100)
        assert u.reg_read(UC_X86_REG_RIP)==0x140249e56
        return u.reg_read(UC_X86_REG_RDX)&255
    def mud_gate(self,red,alpha,wide=False,dirty_corner=False):
        u=self.uc;sp=self.reset_stack();pixel=self.heap+0x1000
        values=np.zeros((3,3,4),dtype='u1');values[:,:,2]=155
        y,x=(0,0) if dirty_corner else (1,1)
        values[y,x,2]=red;values[y,x,3]=alpha
        u.mem_write(pixel,values.tobytes())
        u.mem_write(sp+0x38,struct.pack('<I',12));u.mem_write(sp+0x40,struct.pack('<Q',pixel if wide else pixel+16))
        u.reg_write(UC_X86_REG_R14,0xffffffffffffffff if wide else 0)
        u.reg_write(UC_X86_REG_RBX,2 if wide else 1);u.reg_write(UC_X86_REG_RDI,0)
        u.emu_start(0x1402531aa,0x140253211,timeout=1000000,count=1000)
        assert u.reg_read(UC_X86_REG_RIP)==0x140253211
        return bool(u.reg_read(UC_X86_REG_RDI)&255)
    def plant_scale(self,g,minmap,maxmap,minsize,maxsize,jitter,seed):
        u=self.uc;self.rng=Random(seed);self.reset_stack();plant=self.heap+0x600
        u.reg_write(UC_X86_REG_R13,plant)
        for offset,value in [(0x20,minmap),(0x24,maxmap),(0x28,minsize),(0x2c,maxsize),(0x38,jitter)]:self.f(plant+offset,value)
        for reg,value in [(UC_X86_REG_XMM9,0),(UC_X86_REG_XMM13,32767),(UC_X86_REG_XMM14,g)]:self.xmm(reg,value)
        u.emu_start(0x140254aff,0x140254ba7,timeout=1000000,count=1000)
        assert u.reg_read(UC_X86_REG_RIP)==0x140254ba7
        bits=u.reg_read(UC_X86_REG_XMM10)&0xffffffff
        return struct.unpack('<f',struct.pack('<I',bits))[0]

def main():
    runtime=ctypes.CDLL('C:/Windows/System32/msvcr110.dll')
    runtime.srand.argtypes=[ctypes.c_uint];runtime.rand.restype=ctypes.c_int
    crt=[]
    for seed in [0,1,962,0xffffffff]:
        runtime.srand(seed);rng=Random(seed)
        native=[runtime.rand() for _ in range(256)];model=[rng.rand() for _ in range(256)]
        assert native==model;crt.append(dict(seed=seed,matched_calls=256))
    h=Harness();patterns=[]
    for budget,seed in [(0,0),(3,1),(4,962),(7,962),(26,0),(26,962),(64,962),(140,472),(800,958)]:
        actual,calls=h.patterns(budget,seed);expected,ecalls=model_patterns(budget,seed)
        match=all(a.tobytes()==b.tobytes() for a,b in zip(actual,expected)) and calls==ecalls
        assert match,(budget,seed)
        data=b''.join(a.tobytes() for a in actual)
        patterns.append(dict(budget=budget,seed=seed,patterns=len(actual),points_per_pattern=len(actual[0]),
                             random_calls=calls,bit_exact=match,output_sha256=hashlib.sha256(data).hexdigest()))
        if budget in [26,800]:np.save(OUT/'Deep'/f'pattern-bank-{budget}.npy',np.stack(actual))
    density_cases=[]
    for density in [0,.0099,.01,.01001,.0101,.02,.25,.5,.99,1]:
        for multiplier,attenuation in [(1,1),(.5,1),(1,.25)]:
            for seed in [1,962,472]:
                threshold=F(.01);numerator=F(F(F(F(density)-threshold)*F(multiplier))*F(attenuation))
                rng=Random(seed)
                expected=False if F(.0001)>numerator else F(rng.rand())/F(32767)<=F(numerator/F(F(1)-threshold))
                result,calls=h.density(density,threshold,multiplier,attenuation,seed)
                assert result==bool(expected) and calls==rng.calls
                density_cases.append(dict(density=density,multiplier=multiplier,attenuation=attenuation,seed=seed,accepted=result,random_calls=calls))
    road_cases=[]
    for length in [2,3.5,4,8,100,137.3]:
        for distance in [0,1,2,2.5,3,3.99,4,length-2.1,length-2,length-1,length,length+1]:
            s=F(distance);length32=F(length)
            sat=lambda v:F(max(0,min(1,v)))
            if s<F(4):alpha=sat(F(F(s-F(2))*F(.5)))
            elif s>F(length32-F(2)):alpha=F(F(1)-sat(F(F(s-F(length32-F(2)))*F(.5))))
            else:alpha=F(1)
            expected=int(F(alpha*F(255)));actual=h.road_alpha(distance,length)
            assert actual==expected,(distance,length,actual,expected)
            road_cases.append(dict(length=length,distance=distance,alpha_byte=actual))
    mud_cases=[]
    for red,alpha in [(155,0),(123,0),(122,0),(187,0),(188,0),(155,64),(155,65),(0,255)]:
        for wide in [False,True]:
            for corner in [False,True]:
                dirty=abs(red-155)>32 or alpha>64
                expected=dirty and (wide or not corner)
                actual=h.mud_gate(red,alpha,wide,corner);assert actual==expected
                mud_cases.append(dict(red=red,alpha=alpha,wide=wide,corner=corner,rejected=actual))
    scale_cases=[]
    for minmap,maxmap in [(0,1),(.2,.8),(.5,.5)]:
        for g in [minmap,(minmap+maxmap)/2,maxmap]:
            for minsize,maxsize,jitter in [(.6,1.4,0),(.6,1.4,.4),(.25,4,2)]:
                for seed in [962,472]:
                    delta=F(F(maxmap)-F(minmap))
                    t=F(F(F(g)-F(minmap))/delta) if delta>F(.0001) else F(minmap)
                    t=F(max(0,min(1,t)))
                    size=F(F(F(F(1)-t)*F(minsize))+F(t*F(maxsize)))
                    noise=F(F(F(F(Random(seed).rand())/F(32767))-F(.5))*F(jitter))
                    expected=F(max(.25,min(4,F(noise+size))))
                    actual=h.plant_scale(g,minmap,maxmap,minsize,maxsize,jitter,seed)
                    assert struct.pack('<f',actual)==struct.pack('<f',expected)
                    scale_cases.append(dict(green=g,min_map=minmap,max_map=maxmap,min_size=minsize,max_size=maxsize,jitter=jitter,seed=seed,scale=actual))
    result=dict(ok=True,scope='Captured x64 instructions under Unicorn; preallocated vector storage and validated CRT rand stub. Not an end-to-end editor rebuild.',
                runtime_rand=crt,pattern_cases=patterns,density_cases=density_cases,
                road_alpha_cases=road_cases,mud_filter_cases=mud_cases,plant_scale_cases=scale_cases,
                code_sha256=hashlib.sha256(h.editor.code).hexdigest())
    (OUT/'Deep/kernel-verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(ok=True,crt_calls_checked=1024,pattern_cases=len(patterns),density_cases=len(density_cases),bit_exact_pattern_cases=len(patterns),road_alpha_cases=len(road_cases),mud_filter_cases=len(mud_cases),plant_scale_cases=len(scale_cases))))

if __name__=='__main__':main()
