"""Terrain-shaped surface layers that survive the mesh-grass transition."""
from benmore_painterly_surface import NOISE, HILL_NORMAL

COLOR=NOISE+'''
float distanceM=length(Camera-P)*.01;
float2 uv=float2((q.x+11463)/13680,(4278-q.y)/12770);
float4 geo=Texture2DSample(CoverDetail,CoverDetailSampler,uv);
float slope=1-saturate(N.z);
float footprint=max(length(ddx(q)),length(ddy(q)));
float patch=smoothstep(.26,.75,.65*f.n((q+warp*1.8)/63)+.35*field);
// Three surface scales: fine clumps, connected 8-25 m cover, broad landforms.
// Detail tracks screen footprint so neither distance bands nor subpixel noise
// replace the grass when its geometry becomes too small to draw.
float fine=lerp(.5,f.n((q+warp*.08)/1.7),1-smoothstep(.6,2.3,footprint));
float clump=lerp(.5,f.n((q+warp*.22)/4.8),1-smoothstep(2.2,7,footprint));
float mass=lerp(.5,f.n((q+warp*.65)/17),1-smoothstep(8,26,footprint));
float tufts=smoothstep(.25,.73,fine*.20+clump*.50+mass*.30);
float vegetation=saturate(.62+cover*.32-geo.b*.22-geo.g*.35);
float3 straw=lerp(float3(.255,.194,.097),float3(.37,.284,.139),tufts);
straw*=lerp(.96,1.05,patch);
float3 soil=lerp(float3(.215,.193,.157),float3(.29,.254,.200),mass*.45+patch*.55);
float3 col=lerp(soil,straw,vegetation);
// Exposed rock and light soil tongues follow actual slopes and hollows.
float exposed=smoothstep(.16,.64,geo.g+slope*.10);
// Keep the broad rock planes readable. Local noise is subordinate to actual
// relief instead of creating a mottled camouflage pattern across the range.
float rockPigment=saturate(.45+(patch-.5)*.35+(geo.a-.5)*.40);
float3 schist=lerp(float3(.185,.202,.212),float3(.33,.314,.280),rockPigment);
float fracture=lerp(.5,geo.a,1-smoothstep(12,35,footprint));
schist*=lerp(.94,1.06,fracture);
col=lerp(col,schist,exposed*.90);
float settled=geo.b*smoothstep(.42,.70,mass)*(.55+.45*geo.r);
col=lerp(col,float3(.33,.289,.226)*lerp(.9,1.10,patch),settled*.38);
// Broad sage-brown drainage vegetation supplies connected darker shapes.
float shelter=smoothstep(.15,.64,geo.r)*(1-exposed*.70);
float3 sheltered=lerp(float3(.115,.135,.080),float3(.215,.208,.119),tufts);
col=lerp(col,sheltered,shelter*.68);
// Surface details are pigment/coverage, never baked directional shadows.
float closeDetail=1-smoothstep(25,120,distanceM);
float detail=clamp(dot(Base,float3(.2126,.7152,.0722))/.20,.80,1.16);
col*=lerp(1,detail,closeDetail*.30);
float far=smoothstep(1800,7500,distanceM);
float luma=dot(col,float3(.2126,.7152,.0722));
col=lerp(col,float3(luma*.91,luma*.99,luma*1.12),far*.28);
return P.z<48 ? float3(.035,.15,.19) : lerp(col,Base,saturate(Mask.r+Mask.g*.18));
'''
