"""World-centimetre layout and soil characters for L_MudVariants."""
PROFILES=[
 dict(key='DryClay',title='01  DRY CLAY',start=3000,end=5500,depth=30,soft=.25,wet=.10,cohesion=.94,relief=.45,scale=1.25,table=50,seed=.16),
 dict(key='WetMud',title='02  WET MUD',start=7500,end=10000,depth=28,soft=.84,wet=.84,cohesion=.86,relief=.68,scale=1.3,table=5,seed=.28),
 dict(key='DeepBog',title='03  DEEP SOFT BOG',start=12000,end=14500,depth=46,soft=.98,wet=.96,cohesion=.65,relief=.60,scale=1.5,table=3,seed=.35),
 dict(key='PuddledBog',title='04  PUDDLED BOG',start=16500,end=19000,depth=48,soft=1.,wet=1.,cohesion=.55,relief=.40,scale=1.65,table=8,seed=.30),
 # CL2 (docs/LIDAR_PLACE_PLAN.md): the clay feel lane. One lane, three thirds that differ only in wetness (dry .3, damp .5, wet .8), each a mud region with
 # ClayWeight 1 (the weight the LiDAR map's clay atlas carries) so the soil response is the clay one. Paint depth/softness/table are the same all along it, so wetness is the
 # only variable; seed 0 leaves it un-rutted (the passes of the check cut the ruts).
 dict(key='ClayLane',title='05  CLAY  DRY / DAMP / WET',start=20300,end=22800,depth=30,soft=.35,wet=.30,cohesion=.92,relief=.45,scale=1.25,table=50,seed=0.,
      clay=1.,thirds=[('Dry',.30),('Damp',.50),('Wet',.80)]),
]
PUDDLES=[(17050,-40,340,260),(17800,100,380,300),(18500,-100,300,260)]
LEVEL='/Game/GrandTour/ArtTests/MudVariants/L_MudVariants'
