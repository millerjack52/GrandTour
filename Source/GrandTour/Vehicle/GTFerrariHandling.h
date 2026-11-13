#pragma once
#include "CoreMinimal.h"
namespace GTFerrariHandling
{
    // Unlock the driver's available steering travel only into an existing slide.
    // No steering sign is chosen here; release, normal turn-in, reverse and crawl
    // retain the authored speed curve. Used by the physics-thread steering path.
    inline float CountersteerWeight(float Input,float ForwardCmS,float LateralCmS,bool LowRange)
    {
        if(LowRange || ForwardCmS<=0.f || Input*LateralCmS<=0.f) return 0.f;
        const float Slip=FMath::Abs(FMath::RadiansToDegrees(FMath::Atan2(LateralCmS,ForwardCmS)));
        return FMath::SmoothStep(20.f,45.f,ForwardCmS*.036f)*FMath::SmoothStep(3.f,10.f,Slip);
    }
}
