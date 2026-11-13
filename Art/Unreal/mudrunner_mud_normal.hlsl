// Mud_001 VS scales the difference in metres by 128, with vertical component
// 32 (-c29.x). Preserve both constants: their ratio matches the 25 cm span.
struct NativeMudNormal {
 float3 eval(float dxCm,float dyCm) {
  return normalize(float3(-dxCm*1.28,-dyCm*1.28,32));
 }
};
