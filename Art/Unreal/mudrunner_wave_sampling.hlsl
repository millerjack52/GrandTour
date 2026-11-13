// Water_000 pixel pass, with constructor lookup tables split out of the simulation atlas.
// Native XZ metres are host XY metres. See WaveResearch/provenance.json.
struct MRWaveSampling
{
 float4 optical(Texture2D Waves,SamplerState WS,Texture2D Direction,SamplerState DS,
                Texture2D Speed,SamplerState SS,float2 worldM,float2 flow,float clock,float lod)
 {
  float speed=length(flow);
  float2 dir=speed>1.e-6?flow/speed:float2(1,0);
  // Match source point addresses, including its unusual one-sixth-texel X bias.
  float2 ij=clamp(floor((dir+1)*128+float2(1./6,.5)),0,255);
  float4 axes=Texture2DSampleLevel(Direction,DS,(ij+.5)/float2(256,512),0)*2-1;
  float blend=Texture2DSampleLevel(Direction,DS,(ij+float2(.5,256.5))/float2(256,512),0).a;
  float si=clamp(floor(speed*speed*256+1./6),0,255);
  float3 bands=Texture2DSampleLevel(Speed,SS,float2((si+.5)/256,.5),0).rgb;
  float2 p0=float2(dot(axes.xy,worldM),dot(float2(-axes.y,axes.x),worldM));
  float2 p1=float2(dot(axes.zw,worldM),dot(float2(-axes.w,axes.z),worldM));
  float2 phase=float2(-5.12*clock,19.723);
  float4 a=Texture2DSampleLevel(Waves,WS,(p0+phase*bands.x)*.14,lod);
  float4 b=Texture2DSampleLevel(Waves,WS,(p1+phase*bands.x)*.14,lod);
  float4 c=Texture2DSampleLevel(Waves,WS,(p0+phase*bands.y)*.14,lod);
  float4 d=Texture2DSampleLevel(Waves,WS,(p1+phase*bands.y)*.14,lod);
  return lerp(lerp(a,b,blend),lerp(c,d,blend),bands.z);
 }
 float3 normal(float2 encoded,float2 flow,float distanceM)
 {
  float speed=length(flow);
  float2 dir=speed>1.e-6?flow/speed:float2(1,0);
  float fade=1-saturate((distanceM-16)/24);
  // Pixel strength is speed*(.2+.8*fade), NOT the vertex sqrt speed envelope.
  float2 n=(encoded-.50195998)*2*speed*(.2+.8*fade);
  float up=sqrt(max(0,1-dot(n,n)));
  return normalize(float3(dir*n.x+float2(-dir.y,dir.x)*n.y,up*.5));
 }
};
