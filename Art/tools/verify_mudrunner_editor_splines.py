"""Natural cubic construction reconstructed from editor instructions, with native checks.

Runs captured code in Unicorn, never changes the running editor. Allocator calls
are replaced by a bounded scratch heap; spline arithmetic executes unchanged.
"""
import json, struct
import numpy as np
from verify_mudrunner_editor_kernels import Harness, F
from mudrunner_editor_re import OUT
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *

def coefficients(x,y):
    x=np.asarray(x,dtype='f4');y=np.asarray(y,dtype='f4');n=len(x)-1
    assert n>=2 and np.all(np.diff(x)>0)
    h=np.diff(x);q=np.diff(y)/h
    a=np.zeros(n,dtype='f4');v=a.copy();c=a.copy();b=a.copy();d=a.copy()
    a[0]=F(-F(h[1]/F(F(h[1]+h[0])*F(2))))
    v[0]=F(F(F(q[1]-q[0])*F(1.5))/F(h[0]+h[1]))
    for i in range(1,n-1):
        den=F(F(F(h[i]+h[i+1])*F(2))+F(h[i]*a[i-1]))
        a[i]=F(-F(h[i+1]/den))
        v[i]=F(F(F(F(q[i+1]*F(3))-F(q[i]*F(3)))-F(h[i]*v[i-1]))/den)
    for i in range(n-2,-1,-1):c[i]=F(F(a[i]*c[i+1])+v[i])
    d[0]=F(c[0]/F(h[0]*F(3)))
    b[0]=F(F(F(F(c[0]*F(2))*h[0])/F(3))+q[0])
    for i in range(1,n):
        d[i]=F(F(c[i]-c[i-1])/F(h[i]*F(3)))
        b[i]=F(F(F(F(F(c[i]*F(2))*h[i])+F(h[i]*c[i-1]))/F(3))+q[i])
    return b,c,d

def evaluate(x,y,coef,t):
    t=F(t);k=max(0,min(len(x)-2,int(np.searchsorted(x,t,side='left'))-1));dt=F(t-F(x[k+1]))
    b,c,d=coef;tt=F(dt*dt)
    return F(F(F(F(dt*b[k])+F(y[k+1]))+F(tt*c[k]))+F(F(tt*dt)*d[k]))

class SplineHarness(Harness):
    def __init__(self):
        super().__init__();self.next_alloc=self.heap+0x4000
        for name,offset in [('mfc110u.dll:265',0x200),('mfc110u.dll:266',0x300)]:
            stub=self.stub+offset;self.uc.mem_write(stub,b'\xc3')
            iat=next(a for a,n in self.editor.imports.items() if n==name)
            self.uc.mem_write(iat,struct.pack('<Q',stub))
        def alloc(u,address,size,data):
            n=u.reg_read(UC_X86_REG_RCX);assert 0<n<65536
            p=self.next_alloc;self.next_alloc+=(n+15)&~15
            assert self.next_alloc<self.heap+0x200000
            u.reg_write(UC_X86_REG_RAX,p)
        self.uc.hook_add(UC_HOOK_CODE,alloc,begin=self.stub+0x200,end=self.stub+0x200)
    def construct(self,x,y):
        u=self.uc;sp=self.reset_stack();self.next_alloc=self.heap+0x4000
        self.obj=self.heap;xp=self.heap+0x100;yp=self.heap+0x1000
        u.mem_write(xp,np.array(x,dtype='<f4').tobytes());u.mem_write(yp,np.array(y,dtype='<f4').tobytes())
        u.reg_write(UC_X86_REG_RCX,self.obj);u.reg_write(UC_X86_REG_RDX,xp)
        u.reg_write(UC_X86_REG_R8,4);u.reg_write(UC_X86_REG_R9,yp)
        u.mem_write(sp+0x28,struct.pack('<Q',4));u.mem_write(sp+0x30,struct.pack('<Q',len(x)))
        u.emu_start(0x140183bd0,self.stop,timeout=1000000,count=1000000)
        assert u.reg_read(UC_X86_REG_RIP)==self.stop
        pointers=struct.unpack('<5Q',u.mem_read(self.obj,40))
        return tuple(np.frombuffer(u.mem_read(p,4*(len(x)-1)),'<f4').copy() for p in pointers[2:])
    def evaluate(self,t):
        u=self.uc;self.reset_stack();u.reg_write(UC_X86_REG_RCX,self.obj);self.xmm(UC_X86_REG_XMM1,t)
        u.emu_start(0x140184ae0,self.stop,timeout=1000000,count=10000)
        assert u.reg_read(UC_X86_REG_RIP)==self.stop
        return struct.unpack('<f',struct.pack('<I',u.reg_read(UC_X86_REG_XMM0)&0xffffffff))[0]

def main():
    rng=np.random.default_rng(20261015);h=SplineHarness();cases=[]
    for n in [3,4,5,8,16,33]:
        x=np.r_[F(0),np.cumsum(rng.uniform(.1,20,n-1).astype('f4'),dtype='f4')]
        for label,y in [('line',x*F(.5)),('variable',rng.uniform(-20,20,n).astype('f4'))]:
            native=h.construct(x,y);model=coefficients(x,y)
            assert all(np.array_equal(a.view('u4'),b.view('u4')) for a,b in zip(native,model)),(n,label,native,model)
            samples=np.r_[x,np.linspace(x[0]-2,x[-1]+2,101,dtype='f4')]
            for t in samples:
                actual=F(h.evaluate(t));expected=evaluate(x,y,model,t)
                assert actual.view('u4')==expected.view('u4'),(n,label,t,actual,expected)
            cases.append(dict(points=n,kind=label,coefficients_bit_exact=True,evaluations_bit_exact=len(samples)))
    report=dict(ok=True,constructor='0x140183bd0',evaluate='0x140184ae0',boundary='natural (zero endpoint second derivative)',parameter='cumulative straight-line node distance, not integrated cubic arc length',cases=cases)
    (OUT/'Deep/spline-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':main()
