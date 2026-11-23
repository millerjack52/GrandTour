"""Station and offset in metres. Points exposed by Unreal are in centimetres."""
import bisect
import math
import random

START, END = 27, 69
CLEAR = 3.20
HERO = (57, -7.1)
PATCHES = (  # station, outside/inside offset, along/across half-extents (metres)
    (31.0,-6.8,2.7,1.25), (36.0,-7.4,3.3,1.5), (43.0,6.3,3.0,1.6),
    (48.7,-7.1,3.25,1.55), (56.8,-6.6,2.7,1.40), (60.7,6.6,3.0,1.45),
    (64.9,-6.6,2.9,1.35),
)
COLONIES = ((32,-5.6), (40,-8.0), (54,-6.7), (63,-8.1), (32,6.9), (63,7.3))

class Road:
    def __init__(self, points, stations=None):
        self.points = list(points)
        if stations is None:
            self.stations = [0.]
            for a,b in zip(points,points[1:]):
                self.stations.append(self.stations[-1]+math.dist(a,b)/100.)
        else:
            self.stations = stations
    def at(self, station, across=0):
        i=max(0,min(len(self.points)-2,bisect.bisect_right(self.stations,station)-1))
        a,b=self.points[i:i+2]
        f=(station-self.stations[i])/(self.stations[i+1]-self.stations[i])
        dx,dy=b[0]-a[0],b[1]-a[1]
        n=math.hypot(dx,dy)
        return (a[0]+dx*f-100*across*dy/n,a[1]+dy*f+100*across*dx/n,math.degrees(math.atan2(dy,dx)))
    def nearest(self,x,y):
        best=(float('inf'),0.,0.)
        for i,(a,b) in enumerate(zip(self.points,self.points[1:])):
            dx,dy=b[0]-a[0],b[1]-a[1]
            n2=dx*dx+dy*dy
            if n2==0:continue
            u=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/n2))
            ex,ey=x-a[0]-u*dx,y-a[1]-u*dy
            dist=math.hypot(ex,ey)/100.
            if dist<best[0]:
                best=(dist,self.stations[i]+u*(self.stations[i+1]-self.stations[i]),math.copysign(dist,dx*ey-dy*ex))
        return best

def plant_target(station, across, seed, kind):
    rng=random.Random(seed)
    # Keep a gap on the inside between the two colonies; fan the rest across the bank.
    outside=across<0 or (37<station<57 and rng.random()<.68)
    choices=COLONIES[:4] if outside else COLONIES[4:]
    centre=min(choices,key=lambda p:abs(station-p[0])+rng.uniform(0,4))
    ds=max(-3.3,min(3.3,rng.gauss(0,1.65)))
    da=max(-1.1,min(1.1,rng.gauss(0,.65)))
    # Ferns sit a little deeper, leaving grass to break the leading edge.
    offset=centre[1]+da+math.copysign(.65 if kind=='fern' else 0,centre[1])
    return centre[0]+ds,offset
