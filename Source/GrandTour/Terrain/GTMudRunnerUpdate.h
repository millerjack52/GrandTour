#pragma once
#include "CoreMinimal.h"

/** Arithmetic recovered from SpinTires/MudCompute, build 9640861.
 * Inputs/outputs use the original normalized RGBA encoding. No integration dt
 * occurs inside these passes. Scheduling and contact rasterization are adapters. */
namespace GTMudRunnerUpdate
{
    inline float EncodeHeight(float Cm) { return (Cm+124.f)/204.f; }
    inline float DecodeHeight(float R) { return R*204.f-124.f; }
    inline float UNorm8(float X) { return FMath::RoundToFloat(FMath::Clamp(X,0.f,1.f)*255.f)/255.f; }
    // MudCompute_005, all 11 pixel instructions. The caller controls write masks.
    inline float Push(float PointR,float FilteredR,float TargetR,float ReferenceR,float Strength)
    {
        const float Limit=1.f+Strength*(FMath::Clamp(FilteredR-ReferenceR-1.f/255.f,0.f,1.f)-1.f);
        return PointR+FMath::Min(FMath::Min(Limit,TargetR-PointR),2.f/255.f);
    }
    inline float RelaxChannel(float V)
    {
        return V>128.5f/255.f ? V-1.f/255.f : (V<.5f ? V+1.f/255.f : V);
    }
    // MudCompute_002 neighbor term; native offsets are 25 cm, despite the 12.5 cm map.
    inline float Incoming(float CentreR,float NeighborR,float Aux,float X,float Y)
    {
        const float Weight=FMath::Max(0.f,1.f-.5f*FMath::Sqrt(X*X+Y*Y));
        const float HeightGate=FMath::Clamp(((NeighborR-CentreR)*2.04f-.05f)*2.85714293f,0.f,1.f);
        return Aux*Weight*.15f*HeightGate;
    }
    inline FLinearColor Update(FLinearColor C,float Aux,float Received,float BaseAlpha)
    {
        const float Gate=FMath::Clamp((BaseAlpha-.75f)*4.f,0.f,1.f);
        return FLinearColor(C.R-FMath::Clamp(Aux-Received,-2.f/255.f,2.f/255.f)*Gate,
            RelaxChannel(C.G),RelaxChannel(C.B),C.A+.5f*(Aux+Received)*Gate);
    }
}
