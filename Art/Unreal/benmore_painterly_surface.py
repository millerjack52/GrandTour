"""World-space pigment shapes for the approved grounded painterly direction.

These are lit albedo/normal treatments, never a screen filter or baked sunlight.
Centimetres are converted to metres before the geographic pattern functions.
"""
NOISE = '''struct PigmentField {
float n(float2 p) { float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1,float2(127.1,311.7))))*43758.5453);
return lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y); }
}; PigmentField f;
float2 q=P.xy*.01;
float2 warp=float2(f.n(q/73),f.n(q.yx/91+21))*19;
float field=.65*f.n((q+warp)/115)+.35*f.n((q-warp*.4)/42);
float cover=smoothstep(.34,.65,field);
'''

COLOR = NOISE + '''
float distanceM=length(Camera-P)*.01;
float2 uv=float2((q.x+11463)/13680,(4278-q.y)/12770);
float3 land=Texture2DSample(Landform,LandformSampler,uv).rgb;
float4 ecology=Texture2DSample(CoverDetail,CoverDetailSampler,uv);
float slope=1-saturate(N.z);
// Coherent coverage follows drainage and exposure, with quieter mineral gaps.
float meadow=saturate(.20+cover*.65+ecology.r*.23-smoothstep(.20,.43,slope)*.30);
// Broad irregular pigment islands: elevation bands read as contour stripes
// across the distant mountains, so the large colour shapes use warped XY.
float patch=smoothstep(.25,.76,.65*f.n((q+warp*1.8)/63)+.35*field);
float3 ochre=lerp(float3(.31,.215,.095),float3(.47,.345,.155),patch);
float3 soil=lerp(float3(.21,.191,.155),float3(.335,.285,.205),smoothstep(.24,.78,field));
float3 col=lerp(soil,ochre,meadow);
float exposed=smoothstep(.36,.76,ecology.g+slope*.17+(ecology.b-.5)*.12);
float3 schist=lerp(float3(.165,.191,.226),float3(.335,.328,.294),patch);
// Selective elongated pigment marks follow the tilted geology rather than
// isotropic brown noise. Fine marks fade with pixel footprint and distance.
float footprint=max(length(ddx(q)),length(ddy(q)));
float brush=f.n(float2((q.x*.62+q.y*.38)/8.5,(P.z*.01+q.x*.15+q.y*.10)/1.7));
float marks=smoothstep(.35,.66,brush)-.5;
float markAmount=(1-smoothstep(2,8,footprint))*(1-smoothstep(350,1800,distanceM));
schist*=1+marks*.13*markAmount;
col=lerp(col,schist,exposed*.94);
// Sparse sage patches, tied to sheltered drainage, break the gold/grey masses.
float sheltered=smoothstep(.26,.74,ecology.a)*smoothstep(.47,.65,field)*(1-exposed);
col=lerp(col,float3(.115,.151,.111)*lerp(.92,1.08,patch),sheltered*.78);
col*=lerp(.95,1.05,ecology.b);
float closeDetail=1-smoothstep(18,80,distanceM);
float detail=clamp(dot(Base,float3(.2126,.7152,.0722))/.20,.82,1.15);
col*=lerp(1,detail,closeDetail*.32);
// Pigment compression complements atmosphere; it does not flatten the actual
// directional lighting or replace the true DEM's ridge/gully shading.
float far=smoothstep(1100,6800,distanceM);
float luma=dot(col,float3(.2126,.7152,.0722));
col=lerp(col,lerp(col,float3(luma*.89,luma*.99,luma*1.18),.48),far);
// Existing graded gravel, shoulders, POM and road-relative tracks stay intact.
return P.z<48 ? float3(.035,.15,.19) : lerp(col,Base,saturate(Mask.r+Mask.g*.18));
'''

DENSITY = NOISE + '''return clamp(lerp(.38,1.28,cover),.38,1.28);'''

HILL_NORMAL = '''
float2 q=P.xy*.01;
float2 uv=float2((q.x+11463)/13680,(4278-q.y)/12770);
// The normal field has 5 m texels. Select a stable footprint at distance,
// retaining landform shading while softening the finest survey artefacts.
float footprint=max(length(ddx(q)),length(ddy(q)));
float mip=max(1.0,log2(max(footprint/5.0,1.0)));
float3 a=Texture2DSampleLevel(HillNormal,HillNormalSampler,uv,mip).rgb*2-1;
float3 b=Texture2DSampleLevel(HillNormal,HillNormalSampler,uv,mip+1).rgb*2-1;
return normalize(lerp(a,b,.45));
'''

FOLIAGE = NOISE + '''
float v=saturate(dot(Base,float3(.2126,.7152,.0722))*2.0);
float t=smoothstep(.13,.58,v);
float3 root=float3(.115,.142,.097);
float3 tip=lerp(float3(.47,.335,.135),float3(.64,.47,.235),cover);
float3 paint=lerp(root,tip,t);
// Retain a little of the source vertex palette and all root-to-tip variation.
return lerp(paint,Base*1.28,.16);
'''

ROCK = NOISE + '''
float shape=f.n(float2(q.x*.65+q.y*.38,P.z*.01+q.x*.18+q.y*.11)/1.7);
float area=smoothstep(.30,.72,shape);
float3 col=lerp(float3(.16,.185,.22),float3(.32,.305,.26),area);
float layer=f.n(float2((q.x*.62+q.y*.39)/2.4,(P.z*.01+q.x*.17+q.y*.09)/.24));
float detail=1-smoothstep(80,280,length(Camera-P)*.01);
return col*(1+(smoothstep(.38,.68,layer)-.5)*.12*detail);
'''
