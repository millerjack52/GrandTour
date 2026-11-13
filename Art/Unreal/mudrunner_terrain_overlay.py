"""Terrain_003 PS arithmetic, with explicit host world/lightmap bindings."""
from pathlib import Path

def code():
 body=(Path(__file__).resolve().parents[1]/'Export/MudRoad/NativeInteractions/terrain-overlay-native.hlsl').read_text()
 return '''
float3 sandy;
{
// Native texture/overlay arithmetic is complete. These bindings describe the
// host daytime fixture: neutral shadow/projector maps, existing source ambient
// colours, and no vegetation tint on the sand. They are not native STG decoding.
float4 c0=0,c1=0,c2=float4(InterestForward.z*.5,0,0,0),c3=float4(1/max(InterestForward.z,.01),0,0,0);
float4 c4=0,c5=float4(InterestRight.z*.5,0,0,0),c6=float4(1/max(InterestRight.z,.01),0,0,0);
float4 c7=float4(1,0,0,0),c8=float4(0,1,0,0),c9=float4(0,0,1,0),c10=float4(0,0,0,1),c11=c7,c12=c8,c13=c9,c14=c10;
float4 c15=float4(AmbientPos,0),c16=float4(AmbientMid,0),c17=float4(AmbientNeg,0);
float4 c18=float4(InterestForward.xyz,0),c19=float4(InterestRight.xyz,0),c20=float4(Camera.xzy*.01,0),c21=0;
// Static reflection colour supplied by the study sky; native cached lightmaps
// and headlights remain unbound, as on the existing native mud material.
float4 c22=float4(AmbientPos,0),c23=float4(0,0,1./1024,1./1024),c24=float4(10000,10000,.01,0),c25=0;
float4 c26=float4(InterestCenter.xy,0,0),c27=InterestHeight.xxxx,c28=float4(0,2,0,0),c29=0,c30=float4(3,.03,0,0);
float4 c31=float4(0,0,1,1),c32=float4(-100000,100000,0,0);
float coverage=saturate(.8+field.a*.2);
float4 v0=float4(puv,materialXY*.0018),v1=float4(puv,1,0),v2=0,v3=float4(materialXY/600.,coverage,0);
float4 v4=float4(P.xzy*.01+float3(0,height*.01,0),1),v5=float4(mrNormal.xzy,0);
#define SAMPLE0(p) float4(1,1,1,1)
#define SAMPLE1(p) float4(0,0,0,0)
#define SAMPLE2(p) float4(.5,.5,0,1)
#define SAMPLE3(p) float4(0,1,0,1)
#define SAMPLE4(p) Texture2DSample(WetSand,WetSandSampler,p)
#define SAMPLE5(p) Texture2DSample(SandSpec,SandSpecSampler,p)
#define SAMPLE6(p) Texture2DSample(Grass,GrassSampler,p)
#define SAMPLE7(p) Texture2DSample(Sand,SandSampler,p)
'''+body+'''
sandy=oC0.rgb;
}
'''+''.join('#undef SAMPLE'+str(i)+'\n' for i in range(8))+'''
// Authored worn shore blends into the unchanged native mud colour result.
sandy=lerp(sandy,oC0.rgb,saturate(field.a*.5+max(0,-height)*.025));
'''
