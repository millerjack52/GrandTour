#pragma once
#include "CoreMinimal.h"
namespace GTIndependentDrivetrain
{
    inline float DrivenOmega(float Front,float Rear,float FrontShare)
    { return FMath::Lerp(Rear,Front,FMath::Clamp(FrontShare,0.f,1.f)); }
    inline bool IsWheelspin(float ShaftRPM,float RoadRPM,float IdleRPM,int32 Contacts)
    {
        return Contacts==0 || ShaftRPM>FMath::Max(IdleRPM,RoadRPM)+FMath::Max(500.f,RoadRPM*.2f);
    }
    inline bool CanShiftUp(bool Wheelspin) { return !Wheelspin; }
    inline bool CanShiftDown(bool Wheelspin,float EngineRPM,float DownRPM) { return !Wheelspin || EngineRPM<DownRPM; }

    // Simplified automatic clutch, with real engine inertia and equal/opposite
    // clutch reaction. Call in small time steps; ShaftRPM is the gearbox input speed.
    // Handbrake opens the clutch so locked wheels cannot pin the engine to idle.
    inline float StepClutch(float Dt,float ShaftRPM,float CombustionNm,float RatedTorque,
        float IdleRPM,float MaxRPM,bool Open,float& RPM,float& Engagement,float TotalRatio=12.f,float Inertia=.65f,float EngagementRate=2.5f)
    {
        // Inertia is engine plus flywheel in kg m^2.
        Engagement=Open ? 0.f : FMath::Min(1.f,Engagement+Dt*EngagementRate);
        // Once engaged, the gearbox can back-drive the engine. Use the existing
        // wheel solver's kinematic speed for this direction of coupling rather
        // than letting a softened slip correction leave the engine below shaft
        // RPM in low range. Blend the speed floor during clutch take-up.
        const float BackdriveRPM=FMath::Clamp(ShaftRPM,IdleRPM,MaxRPM*1.02f);
        RPM=FMath::Max(RPM,FMath::Lerp(IdleRPM,BackdriveRPM,Engagement));
        const float AntiStall=FMath::Clamp((RPM-IdleRPM)/350.f,0.f,1.f);
        const float Capacity=RatedTorque*1.6f*Engagement*(RPM>ShaftRPM ? AntiStall : 1.f);
        // Transfer the engine's output plus a bounded flywheel synchronisation
        // torque. Reflected wheel inertia falls with ratio squared: a fixed stiff
        // speed coupling would alternate huge drive/braking impulses in low range
        // because Chaos wheel speed is sampled once per game frame.
        const float RatioScale=12.f/FMath::Max(12.f,FMath::Abs(TotalRatio));
        const float Sync=FMath::Clamp((RPM-ShaftRPM)*.06f*RatioScale*RatioScale,-RatedTorque*.3f,RatedTorque*.3f);
        // The authored positive torque curve is net crankshaft output, already
        // including engine losses. Apply rundown drag only when it supplies no
        // torque (lift-off, limiter, shifting or fuel cutoff), not a second loss.
        const float Drag=CombustionNm>0.f ? 0.f : 35.f+50.f*FMath::Clamp((RPM-IdleRPM)/FMath::Max(1.f,MaxRPM-IdleRPM),0.f,1.f);
        const float Overrun= ShaftRPM>=RPM ? Drag : 0.f;
        const float Transmitted=FMath::Clamp((CombustionNm+Sync-Overrun)*Engagement,-Capacity,Capacity);
        RPM=FMath::Clamp(RPM+(CombustionNm-Drag-Transmitted)/Inertia*60.f/(2.f*PI)*Dt,IdleRPM,MaxRPM*1.02f);
        return Transmitted;
    }
}
