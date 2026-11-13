#pragma once
#include "CoreMinimal.h"
#include "Vehicle/GTIndependentDrivetrain.h"

// Gameplay packages, expressed relative to the authored engine. Standard never overrides it.
namespace GTRangeRoverDrivetrain
{
    struct FSetup
    {
        const TCHAR* Id;
        const TCHAR* Name;
        float FinalRatio, LowRatio, Gears[4], UpRPM, DownRPM, ShiftSeconds, PedalExponent;
        float CentreLSD, FrontLSD, RearLSD;
        float TorqueAtIdle, TorqueAt2500, TorqueAt4500;
    };
    inline const FSetup& Setup(int32 Index)
    {
        static const FSetup Values[] = {
            {TEXT("Part.Engine"), TEXT("Standard"), 3.54f,2.5f,{3.32f,2.13f,1.4f,1.f},4200,1800,.4f,1.f,0,0,0,1,1,1},
            {TEXT("Part.RREngineRally"), TEXT("Rally"), 3.9f,2.5f,{3.05f,2.15f,1.58f,1.18f},4500,2300,.22f,.8f,.3f,.1f,.35f,.94f,1.15f,1.32f},
            {TEXT("Part.RREngineExpedition"), TEXT("Expedition"), 4.11f,3.3f,{3.32f,2.13f,1.4f,1.f},3400,1500,.45f,1.55f,0,0,0,1.20f,1.12f,.8f}
        };
        return Values[FMath::Clamp(Index,0,2)];
    }
    inline int32 Index(FName Id)
    {
        for(int32 I=1;I<3;++I) if(Id==FName(Setup(I).Id)) return I;
        return 0;
    }
    inline float TorqueScale(int32 Index,float RPM)
    {
        const auto& S=Setup(Index);
        return RPM<2500.f ? FMath::Lerp(S.TorqueAtIdle,S.TorqueAt2500,FMath::Clamp((RPM-800.f)/1700.f,0.f,1.f))
            : FMath::Lerp(S.TorqueAt2500,S.TorqueAt4500,FMath::Clamp((RPM-2500.f)/2000.f,0.f,1.f));
    }
    inline float Pedal(int32 Index,float Input) { return FMath::Pow(FMath::Clamp(Input,0.f,1.f),Setup(Index).PedalExponent); }
    using GTIndependentDrivetrain::IsWheelspin;
    using GTIndependentDrivetrain::CanShiftUp;
    using GTIndependentDrivetrain::CanShiftDown;
    using GTIndependentDrivetrain::StepClutch;
}
