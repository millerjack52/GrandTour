"""2D Saint-Venant finite-volume solver for the offline river bake.

Rusanov flux with hydrostatic reconstruction (Audusse et al., 2004), explicit
CFL time steps and semi-implicit Manning friction. Units: metres and seconds.
"""
import numpy as np
from numba import njit

@njit(cache=True)
def step_for(z,h,hu,hv,a,b,axis,dx,source,weights,inflow,reservoir,level,duration,mannings=.05):
    n=len(h);dh=np.empty(n);du=np.empty(n);dv=np.empty(n);u=np.empty(n);v=np.empty(n)
    wallx=np.zeros(n);wally=np.zeros(n)
    for e in range(len(a)):
        if axis[e]==0:wallx[a[e]]+=1;wallx[b[e]]-=1
        else:wally[a[e]]+=1;wally[b[e]]-=1
    t=0.;added=0.;boundary=0.;steps=0;min_dt=1.;negative_volume=0.
    while t<duration-1e-9:
        maxsignal=.1
        for i in range(n):
            if h[i]>.00001:u[i]=hu[i]/h[i];v[i]=hv[i]/h[i]
            else:u[i]=0.;v[i]=0.
            maxsignal=max(maxsignal,abs(u[i])+abs(v[i])+2*np.sqrt(9.81*h[i]))
            dh[i]=0.;du[i]=wallx[i]*4.905*h[i]*h[i]/dx;dv[i]=wally[i]*4.905*h[i]*h[i]/dx
        dt=min(.12,.36*dx/maxsignal,duration-t);min_dt=min(dt,min_dt)
        for e in range(len(a)):
            i,j=a[e],b[e];hi,hj=h[i],h[j]
            if hi+hj<1e-12:continue
            crest=max(z[i],z[j]);hl=max(0.,z[i]+hi-crest);hr=max(0.,z[j]+hj-crest)
            if axis[e]==0:ul,ur,vl,vr=u[i],u[j],v[i],v[j]
            else:ul,ur,vl,vr=v[i],v[j],u[i],u[j]
            wave=max(abs(ul)+np.sqrt(9.81*hl),abs(ur)+np.sqrt(9.81*hr))
            f0=.5*(hl*ul+hr*ur-wave*(hr-hl))
            f1=.5*(hl*ul*ul+hr*ur*ur+4.905*(hl*hl+hr*hr)-wave*(hr*ur-hl*ul))
            f2=.5*(hl*ul*vl+hr*ur*vr-wave*(hr*vr-hl*vl))
            cl=4.905*(hi*hi-hl*hl);cr=4.905*(hj*hj-hr*hr)
            dh[i]-=f0/dx;dh[j]+=f0/dx
            if axis[e]==0:
                du[i]-=(f1+cl)/dx;du[j]+=(f1+cr)/dx;dv[i]-=f2/dx;dv[j]+=f2/dx
            else:
                dv[i]-=(f1+cl)/dx;dv[j]+=(f1+cr)/dx;du[i]-=f2/dx;du[j]+=f2/dx
        for i in range(n):
            newh=h[i]+dt*dh[i]
            if newh<0:negative_volume-=newh*dx*dx
            h[i]=max(0.,newh);hu[i]+=dt*du[i];hv[i]+=dt*dv[i]
            if h[i]<.00001:hu[i]=0.;hv[i]=0.
            else:
                speed=np.sqrt(hu[i]*hu[i]+hv[i]*hv[i])/h[i]
                resistance=1.+dt*9.81*mannings*mannings*speed/max(.00001,h[i]**(4./3.))
                hu[i]/=resistance;hv[i]/=resistance
        for k in range(len(source)):
            volume=inflow*weights[k]*dt;h[source[k]]+=volume/(dx*dx);added+=volume
        for i in reservoir:
            target=max(0.,level-z[i]);boundary+=(target-h[i])*dx*dx
            if target<h[i]:hu[i]*=target/max(h[i],1e-12);hv[i]*=target/max(h[i],1e-12)
            h[i]=target
        t+=dt;steps+=1
    return added,boundary,steps,min_dt,negative_volume

def check_solver():
    j,i=np.mgrid[:18,:32];z=(.09*np.sin(i*.4)+.15*np.cos(j*.4)).ravel();ids=np.arange(z.size).reshape(i.shape)
    a=np.r_[ids[:,:-1].ravel(),ids[:-1,:].ravel()];b=np.r_[ids[:,1:].ravel(),ids[1:,:].ravel()]
    axis=np.r_[np.zeros(ids[:,:-1].size,int),np.ones(ids[:-1,:].size,int)];empty=np.empty(0,np.int64);weights=np.empty(0)
    h=.8-z;hu=h*0;hv=h*0;before=h.copy()
    step_for(z,h,hu,hv,a,b,axis,1.,empty,weights,0.,empty,0.,10.)
    rest=float(abs(h-before).max());assert rest<1e-10 and np.max(abs(hu))<1e-10
    h=np.where(i.ravel()<11,1.,0.);hu=h*0;hv=h*0;mass=h.sum()
    r=step_for(z,h,hu,hv,a,b,axis,1.,empty,weights,0.,empty,0.,15.)
    error=abs(h.sum()-mass);assert error<1e-9 and h.min()>=0 and h[i.ravel()>12].max()>.01 and r[-1]<1e-9
    return dict(level_surface_max_change_m=rest,closed_dam_mass_error_m3=float(error),closed_dam_min_depth_m=float(h.min()),positivity_correction_m3=float(r[-1]))
