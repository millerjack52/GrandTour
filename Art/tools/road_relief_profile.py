"""Road-frame relief authoring in centimetres: station along the road, lateral across it.

Map adapters supply these coordinates and blend the returned delta into their
own base terrain. This is authored terrain, not a runtime deformation substitute.
"""
import math
from make_mud_proving_ground import noise,smooth

def profile(station,lateral):
    envelope=smooth(-2450,-2150,station)*(1-smooth(2350,2780,station))
    cover=(1-smooth(240,330,abs(lateral)))*envelope
    rut=0.
    for side in (-1,1):
        wander=8*math.sin(station/280+side)+4*math.sin(station/95+side*2)
        rut=max(rut,math.exp(-((lateral-side*83-wander)/39)**4))
    broken=.4+.6*noise(station/120,lateral/80,711)
    crown=(1-smooth(24,65,abs(lateral)))*broken
    shoulder=math.exp(-((abs(lateral)-163)/42)**2)*(.35+.65*noise(station/160,lateral/100,712))
    # Several 25-80 cm lumps rather than texture-sized noise below the mesh spacing.
    aggregate=smooth(.46,.75,noise(station/100,lateral/80,719))*(1-rut)
    lumps=(noise(station/52,lateral/47,713)-.45)*8*(1-rut*.75)
    delta=(8*crown+8*shoulder-(5+4*noise(station/230,3,714))*rut+lumps+5*aggregate)*cover
    return delta,rut*cover,max(crown,shoulder)*cover,aggregate*cover,cover
