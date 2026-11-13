"""Centimetre-space art study geometry, shared by mesh export and dressing.

One continuous firm bed; water level is z=0. No deformation/vehicle interfaces.
"""
import math

def terrain_noise(x,y):
    """Smooth nonperiodic relief; integer hashing avoids repeated wave bands."""
    ix,iy=math.floor(x),math.floor(y);fx=x-ix;fy=y-iy
    fx=fx*fx*fx*(fx*(fx*6-15)+10);fy=fy*fy*fy*(fy*(fy*6-15)+10)
    def h(a,b):
        n=(a*374761393+b*668265263)&0xffffffff
        n=((n^(n>>13))*1274126177)&0xffffffff
        return ((n^(n>>16))/4294967295.)*2-1
    a=h(ix,iy)*(1-fx)+h(ix+1,iy)*fx
    b=h(ix,iy+1)*(1-fx)+h(ix+1,iy+1)*fx
    return a*(1-fy)+b*fy

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)

def centre(x):return 90+115*math.sin(x/930)+42*math.sin(x/370)

def silt(x,y):
    return math.exp(-((x-640)/340)**2-((y+425)/150)**2)

def height(x,y,spacing=0):
    d=abs(y-centre(x));w=400+50*math.sin(x/610)+24*math.sin(x/183)
    shore=55*(smooth(w-90,w+400,d))
    channel=-48*(1-smooth(w-300,w+40,d))
    island=75*math.exp(-((x-620)/750)**4-((y-centre(x)-85)/175)**2)
    terrace=42*smooth(1000,1800,d)
    # Retain the original ford. Outside it, filter relief that the export grid
    # cannot resolve instead of aliasing short ripples into large mesh facets.
    irregular=sum(amp*math.sin(x/fx+y/fy)*(1-smooth(20,max(21,math.pi/math.hypot(1/fx,1/fy)),spacing))
                  for amp,fx,fy in [(3.8,111,149),(2.1,41,-63),(1.4,19,23)])
    outside=smooth(0,1500,max(abs(x)-1800,abs(y)-1000))
    if outside:
        relief=sum(amp*terrain_noise((x*.91-y*.41)/scale,(x*.41+y*.91)/scale)*
                   (1-smooth(20,scale*.8,spacing)) for amp,scale in [(4.4,350),(2.5,125),(1.,45)])
        irregular=irregular*(1-outside)+relief*outside
    return shore+channel+island+terrace+irregular*(1-.8*silt(x,y))

VIEWS=[('shore_transition',(-850,-670,210),(20,-145,-4)),
       ('shallow_bed',(-520,-350,170),(-150,-40,-35)),
       ('dry_bar',(-300,-870,218),(340,-580,25)),
       ('silt_margin',(350,-800,210),(730,-375,0)),
       ('upstream',(1200,-560,205),(150,-50,0)),
       ('reach_overview',(-2100,-2100,1650),(200,0,0)),
       ('distant_reach',(-7200,-4800,2700),(-3900,0,0))]
VIEWS=[(key,(p[0],p[1],height(p[0],p[1])+160) if key not in ('reach_overview','distant_reach') else p,target) for key,p,target in VIEWS]
