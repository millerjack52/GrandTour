"""Shared deterministic RS7 surface in centimetres; no Unreal dependency."""
import math
CX,CY=-45800.,-31600.
HALF_U,HALF_V=1100.,780.
def xy(a,b):return CX+.6*a-.8*b,CY-.8*a-.6*b
def uv(x,y):
 x-=CX;y-=CY
 return .6*x-.8*y,-.8*x-.6*y
def inside(x,y,margin=0):
 a,b=uv(x,y);return abs(a)<HALF_U-margin and abs(b)<HALF_V-margin
def rock(a,b):
 return max(math.exp(-((a-au)/wu)**4-((b-bv)/wv)**4) for au,bv,wu,wv in [(-650,180,240,165),(120,-160,340,180),(770,270,180,220)])
def base_relief(x,y):
 a,b=uv(x,y)
 if abs(a)>=HALF_U or abs(b)>=HALF_V:return -6.
 edge=min(1.,max(0.,(HALF_U-abs(a))/120),max(0.,(HALF_V-abs(b))/120))
 r=rock(a,b);r=max(0.,min(1.,(r-.38)/.35));r=r*r*(3-2*r)
 return -9+edge*(12+9*(.5+.5*math.sin(a*.013+math.sin(b*.015)))*(.6+.4*math.cos(b*.018))+r*(52+13*math.sin(a*.025+b*.009)))

def relief(x,y):
 from lidar_bank_relief_detail import additional
 return base_relief(x,y)+additional(x,y)
