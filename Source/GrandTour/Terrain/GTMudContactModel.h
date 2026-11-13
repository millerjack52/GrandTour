#pragma once
#include "CoreMinimal.h"

/** Small soil law shared by diagnostics and the physics-thread vehicle simulation.
 * Speeds cm/s, lengths cm; force result is a fraction of supported wheel load. */
namespace GTMudContact
{
struct FResponse { float Grip=1, Resistance=0, Slip=0, LateralGrip=1; };
struct FState { bool Enabled=false;float Wetness=0,Cohesion=0,Disturbance=0,CompressionCm=0;bool Granular=false; };
// Additional work needed to displace a bank above the loaded footprint. A yielding
// bank is weaker when wet/remoulded. This is dissipative resistance, never a steering spring.
inline float BankResistance(float RiseCm,float ReachCm,float Softness,FState State)
{
    const float Grade=FMath::Clamp((RiseCm-2.f)/FMath::Max(10.f,ReachCm),0.f,1.f);
    if(State.Granular) return Grade*FMath::Lerp(.22f,.13f,FMath::Clamp(Softness,0.f,1.f));
    const float Wet=FMath::Clamp(State.Wetness,0.f,1.f);
    const float Worked=FMath::Clamp(State.Disturbance,0.f,1.f);
    const float Strength=FMath::Lerp(.65f,.28f,FMath::Clamp(Softness,0.f,1.f))
        * (1.f-.4f*Wet*Worked) + .14f*FMath::Clamp(State.Cohesion,0.f,1.f)*(1.f-Wet);
    return FMath::Min(.25f,Grade*Strength*.5f);
}
inline float BankForce(float Load,float Resistance,float SpeedCmS,float Dt)
{
    return FMath::Min(FMath::Max(0.f,Load)*FMath::Max(0.f,Resistance),
        FMath::Max(0.f,Load)/980.f*FMath::Abs(SpeedCmS)/FMath::Max(Dt,.001f)*.25f);
}
inline FResponse Evaluate(float Softness,float Grass,float SinkCm,float RadiusCm,float SpeedCmS,float TreadCmS,FState State={})
{
    const float Soft=FMath::Clamp(Softness,0.f,1.f)*FMath::Lerp(1.f,.3f,Grass);
    const float V=FMath::Abs(SpeedCmS)*.01f;
    const float Immersion=FMath::Clamp(SinkCm/FMath::Max(10.f,RadiusCm),0.f,.85f);
    FResponse R;
    R.Slip=FMath::Clamp(FMath::Abs(TreadCmS-SpeedCmS)/FMath::Max3(50.f,FMath::Abs(TreadCmS),FMath::Abs(SpeedCmS)),0.f,1.f);
    R.Grip=FMath::Lerp(.68f,.26f,Soft)*(1.f-.32f*R.Slip*Soft);
    // Compaction/ploughing, velocity-dependent soil displacement and axle drag.
    // No velocity cap; equilibrium emerges from traction against these losses.
    R.Resistance=(.02f+Soft*(.055f+.20f*Immersion)
        +Soft*(.04f*V+.022f*V*V)*(.3f+1.7f*Immersion)
        +Soft*.25f*FMath::Clamp((SinkCm-18.f)/12.f,0.f,1.f))
        *FMath::Clamp(FMath::Abs(SpeedCmS)/25.f,0.f,1.f);
    R.LateralGrip=R.Grip;
    if(State.Enabled)
    {
        const float Wet=FMath::Clamp(State.Wetness,0.f,1.f);
        const float Cohesion=FMath::Clamp(State.Cohesion,0.f,1.f);
        const float Worked=FMath::Clamp(State.Disturbance,0.f,1.f);
        // Dry soil firms under compression; saturated worked clay loses shear strength.
        const float Compacted=FMath::Clamp(State.CompressionCm/12.f,0.f,1.f)*(1.f-Wet);
        const float Remoulded=Worked*Wet*Soft;
        const float Peak=FMath::Lerp(.92f,.54f,Soft)+.10f*Cohesion*(1.f-Wet)+.10f*Compacted;
        const float PostPeak=FMath::SmoothStep(.16f,.8f,R.Slip);
        R.Grip=FMath::Clamp(Peak*(1.f-.24f*Remoulded)*(1.f-PostPeak*(.15f+.18f*Wet)),.12f,1.f);
        R.LateralGrip=R.Grip*FMath::Lerp(.95f,.63f,Wet*Soft);
        // Resistance is displacement of soil under the wheel, not an imposed speed limit.
        // Firm tracks have less compaction work; deep entry adds a speed-dependent ploughing term.
        R.Resistance=(.025f+Soft*(.035f+.15f*Immersion)*(1.f-.4f*Compacted)
            +Soft*(.014f*V+.016f*V*V)*(.25f+1.4f*Immersion)
            +Soft*.16f*FMath::Clamp((SinkCm-20.f)/12.f,0.f,1.f))
            *FMath::Clamp(FMath::Abs(SpeedCmS)/20.f,0.f,1.f);
    }
    if(State.Enabled && State.Granular)
    {
        // Frictional grains compact under load; wheelspin loosens their contact.
        // No saturated-clay remoulding or viscous drag term on this path.
        const float Packed=FMath::Clamp(State.CompressionCm/10.f,0.f,1.f);
        const float SlipLoss=FMath::SmoothStep(.18f,.85f,R.Slip);
        R.Grip=FMath::Clamp(.88f-.34f*Soft+.13f*Packed-.15f*SlipLoss*Soft,.25f,.95f);
        R.LateralGrip=R.Grip*FMath::Lerp(.96f,.77f,Soft);
        R.Resistance=(.018f+Soft*(.055f+.27f*Immersion)*(1.f-.45f*Packed)
            +Soft*(.010f*V+.008f*V*V)*Immersion)*FMath::Clamp(FMath::Abs(SpeedCmS)/20.f,0.f,1.f);
    }
    return R;
}
}
