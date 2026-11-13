// SpinTires_Mud_000 PS, diffuse blend before scene lighting.
// LRP weights above one are extrapolations, not saturated lerps.
struct NativeMudBlend {
 float3 eval(float4 churn,float4 flatTex,float4 dirt,float4 grass,float3 decalRGB,
             float presence,float flatWeight,float decalWeight,float baseDirt,
             float3 dirtTint,float3 grassTint) {
  float cover=saturate(2*presence-churn.a);
  float decal=saturate(4*decalWeight-3*churn.a);
  float attenuation=max(1-abs(decalWeight-decal),0);
  float3 churned=lerp(churn.rgb,decalRGB*attenuation,decal);
  float3 flatRGB=flatTex.rgb*lerp(float3(1,1,1),dirtTint,flatTex.a);
  float3 muddy=lerp(churned,flatRGB,flatWeight);
  float dirtCoverage=saturate(3*baseDirt-2*grass.a);
  float3 base=lerp(grass.rgb*grassTint,dirt.rgb*lerp(float3(1,1,1),dirtTint,dirt.a),dirtCoverage);
  return lerp(base,muddy,cover)*(abs(cover-.5)+.5);
 }
};
