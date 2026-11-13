#pragma once
#include "CoreMinimal.h"

/** Post-peak lateral tyre response only. No added peak grip, yaw torque or power. */
namespace GTSlideRecovery
{
inline float Weight(float SpeedKmh, bool bLowRange, float Softness, float SoilDepthCm,
    float WaterDepthCm, float Strength, float StartKmh=30.f, float FullKmh=65.f)
{
    if(bLowRange || Softness>=.45f || SoilDepthCm>=12.f || WaterDepthCm>=5.f) return 0.f;
    const float Speed=FMath::SmoothStep(StartKmh,FMath::Max(StartKmh+1.f,FullKmh),FMath::Abs(SpeedKmh));
    // Ease out at the edge of deep/soft ground instead of switching force on a boundary.
    const float Ground=(1.f-FMath::SmoothStep(.25f,.45f,Softness))
        *(1.f-FMath::SmoothStep(6.f,12.f,SoilDepthCm))
        *(1.f-FMath::SmoothStep(1.f,5.f,WaterDepthCm));
    return FMath::Clamp(Strength,0.f,1.f)*Speed*Ground;
}

inline float GraphScale(float Value, float Peak, float AngleDeg, float PeakAngleDeg, float Weight)
{
    if(Weight<=0.f || AngleDeg<=PeakAngleDeg || Value<=UE_SMALL_NUMBER || Peak<=Value) return 1.f;
    return FMath::Lerp(Value,Peak,FMath::Clamp(Weight,0.f,1.f))/Value;
}
}
