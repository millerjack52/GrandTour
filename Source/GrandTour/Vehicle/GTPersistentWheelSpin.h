#pragma once
#include "CoreMinimal.h"

// SI units. Impulse-limited rolling contact: retained wheel angular momentum,
// drive/brake torque and an equal tyre reaction, bounded by combined grip.
namespace GTPersistentWheelSpin
{
    struct FResult { float Omega=0, Fx=0, Fy=0, Brake=0; };
    inline FResult Step(float Dt,float Omega,float Speed,float Radius,float Inertia,
        float Mass,float Drive,float Brake,float Grip,float Lateral,float SlidingScale,bool Contact)
    {
        FResult Out;Out.Omega=Omega;
        if(Dt<=0 || Radius<=0 || Inertia<=0 || Mass<=0)return Out;
        const float Free=Omega+Drive*Dt/Inertia;
        Out.Brake=FMath::Sign(Free)*FMath::Min(FMath::Max(0.f,Brake),FMath::Abs(Free)*Inertia/Dt);
        const float Predicted=Free-Out.Brake*Dt/Inertia;
        if(Contact && Grip>0)
        {
            // Include the supported body's translation in the rolling impulse.
            // Clamp each axis before combining: accumulated spin must not erase
            // the entire lateral response with an unbounded force demand.
            // When the brake can hold against the entire tyre torque, rotation
            // is constrained. React the supported body mass directly; retaining
            // the free-wheel inverse mass here makes parked cars creep on slopes.
            const bool Locked=FMath::Abs(Predicted)<.0001f && Brake>=FMath::Abs(Drive)+Grip*Radius;
            const float Demand=Locked ? -Speed*Mass/Dt
                : (Predicted*Radius-Speed)/(Dt*(Radius*Radius/Inertia+1.f/Mass));
            Out.Fx=FMath::Clamp(Demand,-Grip,Grip);
            Out.Fy=FMath::Clamp(Lateral,-Grip,Grip);
            const float Length=FMath::Sqrt(Out.Fx*Out.Fx+Out.Fy*Out.Fy);
            const bool Sliding=FMath::Abs(Demand)>Grip || Length>Grip;
            const float Scale=(Length>Grip ? Grip/Length : 1.f)*(Sliding ? SlidingScale : 1.f);
            Out.Fx*=Scale;Out.Fy*=Scale;
        }
        // A locked brake also reacts the tyre torque; do not let the contact
        // impulse immediately spin a wheel the handbrake has enough torque to hold.
        const float Unbraked=Free-Out.Fx*Radius*Dt/Inertia;
        Out.Brake=FMath::Sign(Unbraked)*FMath::Min(FMath::Max(0.f,Brake),FMath::Abs(Unbraked)*Inertia/Dt);
        Out.Omega=Unbraked-Out.Brake*Dt/Inertia;
        return Out;
    }
}
