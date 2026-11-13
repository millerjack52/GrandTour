#pragma once
#include "CoreMinimal.h"

// Host-authored spatial composition informed by Island's independent mud relief.
// This is deliberately not labelled a recovered MudRunner procedural generator.
namespace GTRoadConditionShape
{
struct FResult {float Relief=0,Soft=0,Worked=0;};
inline FResult Evaluate(float S,float Across,float HalfWidth,int32 Seed,float Depth,float Spread,float Churn,float Crossing,float Breakup)
{
    auto N=[&](float X,float Y,float Scale,int32 Offset)
    {return .5f+.5f*FMath::PerlinNoise2D(FVector2D(X/Scale+(Seed+Offset)%193,Y/Scale+(Seed+Offset)%97));};
    auto Gate=[](float A,float B,float X){return FMath::SmoothStep(A,B,X);};
    const float Along=S*100;
    float Cuts=0,Banks=0,Worked=0,Soft=0;
    // Three traffic lines, independently interrupted. The side lines fan out and
    // merge with the central one; do not stack full-depth trenches at a merge.
    for(int32 Pass=-1;Pass<=1;++Pass)
    {
        if(Pass && Spread<=0)continue;
        const float Fan=Gate(.24f,.72f,N(Along,617,1900,13));
        const float Centre=Pass*Spread*Fan+(N(Along,Pass*953,1100,19)-.5f)*85;
        const float Presence=Pass ? Gate(.32f,.65f,N(Along,Pass*1979,1400,31)) : 1.f;
        for(float Side:{-1.f,1.f})
        {
            const float RutCentre=Centre+Side*(85+30*N(Along,Side*1291,1600,23));
            const float Width=FMath::Lerp(27.f,78.f,N(Along,Side*739+Pass*331,650,47))*(1+.55f*Churn);
            const float D=FMath::Abs(Across-RutCentre)/Width;
            const float Broken=Gate(.22f,.69f,N(Along,Side*1543+Pass*421,430,29));
            const float Load=Presence*(.12f+.88f*Broken);
            const float Cut=FMath::Exp(-D*D*1.5f)*Load;
            Cuts=FMath::Max(Cuts,Cut);Soft=FMath::Max(Soft,Cut);
            Banks=FMath::Max(Banks,FMath::Exp(-FMath::Square(D-1.8f)*3)*Load*.13f);
            Worked=FMath::Max(Worked,FMath::Exp(-D*D*.35f)*Load);
        }
    }
    // Diagonal abandoned wheel channels cross the current path in short patches.
    const float CrossMask=Crossing*Gate(.38f,.72f,N(Along,371,1400,71));
    const float CrossCentre=(N(Along,971,1200,73)-.5f)*HalfWidth*2.8f;
    const float CrossD=FMath::Min(FMath::Abs(Across-CrossCentre-85),FMath::Abs(Across-CrossCentre+85))/45.f;
    const float CrossCut=FMath::Exp(-CrossD*CrossD)*CrossMask;
    Cuts=FMath::Max(Cuts,CrossCut*.75f);Worked=FMath::Max(Worked,CrossCut);
    const float Area=1-Gate(HalfWidth*.55f,HalfWidth, FMath::Abs(Across));
    const float Pocket=Gate(.28f,.7f,N(Along+80*N(Along,Across,250,87),Across,310,89));
    const float Broad=Churn*Area*Pocket;
    const float Clumps=(N(Along,Across,72,101)-.5f)*1.2f+(N(Along,Across,190,109)-.5f);
    FResult R;
    R.Relief=Depth*(-Cuts*(1-.35f*Churn)+Banks-Broad*.52f)+Breakup*Clumps*Area;
    R.Soft=FMath::Max(Soft,Broad);R.Worked=FMath::Max(Worked,Broad);
    return R;
}
}
