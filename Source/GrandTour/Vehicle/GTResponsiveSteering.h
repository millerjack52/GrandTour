#pragma once
#include "CoreMinimal.h"
#include "ChaosVehicleMovementComponent.h"
#include "Vehicle/GTSlideRecovery.h"
#include "Curves/CurveFloat.h"
#include "UObject/StrongObjectPtr.h"

/** Input response only: retain each vehicle's steering lock and tyre forces. */
struct FGTResponsiveSteering
{
    FVehicleInputRateConfig Original;
    TStrongObjectPtr<UCurveFloat> OriginalExternalCurve;
    float LastWeight=-1.f;
    bool bCaptured=false;
    float ReversalDirection=0.f;

    // The player must explicitly reverse steering. Nothing here reads yaw/slip
    // or chooses a steering direction. Ordinary turn-in and release keep 6/8.
    void UpdateReversal(FVehicleInputRateConfig& Config,float Raw,float Filtered,float Strength,float SteeringBias=0.f)
    {
        if(!bCaptured)return;
        const float Weight=FMath::Max(0.f,LastWeight);
        const float ReversalWeight=Weight*FMath::Clamp(Strength,0.f,1.f);
        const float Target=FMath::Clamp(Raw+SteeringBias,-1.f,1.f);
        if(ReversalWeight<=0.f || FMath::Abs(Raw)<.99f || Target*Raw<=0.f)ReversalDirection=0.f;
        else
        {
            const float Direction=FMath::Sign(Raw);
            if(ReversalDirection!=Direction)ReversalDirection=0.f;
            if(Raw*Filtered<-.05f)ReversalDirection=Direction;
            if(Filtered*Direction>=FMath::Abs(Target)-.01f)ReversalDirection=0.f;
        }
        const bool Reversing=ReversalDirection!=0.f;
        Config.RiseRate=FMath::Lerp(Original.RiseRate,FMath::Max(Original.RiseRate,6.f),Weight);
        Config.FallRate=FMath::Lerp(Original.FallRate,FMath::Max(Original.FallRate,8.f),Weight);
        if(Reversing)
        {
            Config.RiseRate=FMath::Lerp(Config.RiseRate,FMath::Max(Config.RiseRate,12.f),ReversalWeight);
            Config.FallRate=FMath::Lerp(Config.FallRate,FMath::Max(Config.FallRate,12.f),ReversalWeight);
        }
    }

    static float Weight(bool bLowRange,bool bSoftSurface,float SinkCm,float WaterCm,float Strength)
    {
        // Ordinary turn-in uses the same filter at every speed. The separate
        // deliberate-reversal transition must not change these tap rates.
        return GTSlideRecovery::Weight(60.f,bLowRange,bSoftSurface?1.f:0.f,SinkCm,WaterCm,Strength,30.f,60.f);
    }

    void Update(FVehicleInputRateConfig& Config,float Weight)
    {
        if(!bCaptured){Original=Config;OriginalExternalCurve.Reset(Original.UserCurve.ExternalCurve);bCaptured=true;}
        Weight=FMath::Clamp(Weight,0.f,1.f);
        if(Weight==LastWeight)return;
        const float PreviousWeight=LastWeight;
        LastWeight=Weight;
        if(Weight==0.f){Config=Original;return;}
        // Never slow down an already responsive per-car setup.
        Config.RiseRate=FMath::Lerp(Original.RiseRate,FMath::Max(Original.RiseRate,6.f),Weight);
        Config.FallRate=FMath::Lerp(Original.FallRate,FMath::Max(Original.FallRate,8.f),Weight);
        if(Weight==1.f){Config.InputCurveFunction=EInputFunctionType::LinearFunction;return;}
        Config.InputCurveFunction=EInputFunctionType::CustomCurve;
        // Only the transition band needs a curve; UpdateOrAddKey reuses its keys.
        // Preserve signed input and centre zero; the engine applies the sign.
        Config.UserCurve.ExternalCurve=nullptr;
        auto* Curve=Config.UserCurve.GetRichCurve();
        if(PreviousWeight<=0 || PreviousWeight>=1 || Curve->GetNumKeys()!=17)Curve->Reset();
        for(int32 I=0;I<=16;++I)
        {
            const float X=float(I)/16.f;
            const auto Key=Curve->UpdateOrAddKey(X,FMath::Lerp(Original.CalcControlFunction(X),X,Weight));
            Curve->SetKeyInterpMode(Key,RCIM_Linear);
        }
    }
};
