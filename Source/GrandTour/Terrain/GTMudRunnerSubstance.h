#pragma once
#include "CoreMinimal.h"

/** Build 9640861, MudRunner.exe 0x140930110. All values here are m/kg/s, native Y-up.
 * Returns impulses per native action invocation, not forces. Scheduling and rigid-body
 * representation belong to the host adapter. See findings_stage2.txt for field provenance. */
namespace GTMudRunnerSubstance
{
struct FInput
{
    double Radius=.33,Width=.25,Depth=0,Q=0,Omega=0,RollingSpeed=0;
    FVector Velocity=FVector::ZeroVector,PredictedDisplacement=FVector::ZeroVector;
    FVector Forward=FVector(1,0,0),Axle=FVector(0,0,1),Flow=FVector::ZeroVector;
    FVector InertiaRows[3]={FVector(1,0,0),FVector(0,1,0),FVector(0,0,1)};
    double WheelMass=20,MassPerWheel=500,DriveState=0,TireFriction=1.2;
    double Friction=2.2,LinearResistance=10,FullPushDepth=1.2,PushResistance=36,FlowImpulse=0;
    bool bWater=false;
};
struct FOutput { FVector LinearImpulse=FVector::ZeroVector,AngularImpulse=FVector::ZeroVector; double Drive=0,Support=0; };
inline double Sat(double V) { return FMath::Clamp(V,0.,1.); }
inline double Slip(double V) { return Sat(2*(V-.5))*(1-.8*Sat((V-1)/9)); }
inline double Depth(double D,double R) { return D<.5*R ? D/(.5*R) : 1-FMath::Min((D-.5*R)/(1.5*R),1.); }
inline double Excitation(double R,double W,double Omega,double Speed,double Mass,double SoftForce)
{
    const double Tread=Omega*R;
    const double Width=.5+.5*FMath::Clamp(W/.52,.25,4.);
    return (1.2*FMath::Max(FMath::Abs(Tread-Speed)-.5,0.)*Sat((FMath::Max(FMath::Abs(Tread),FMath::Abs(Speed))-1.2)/2.4)+.2/Width)
        *1.2*FMath::Min(Mass/4000,1.)*(.5+.5*SoftForce/.28);
}
inline uint8 Extrude(uint8 Old,uint8 Base,bool Overlay,double P,bool Central)
{
    const int32 B=Overlay ? FMath::Min(int32(Base),64) : FMath::Max(int32(Base),32);
    const int32 Increment=FMath::Max(Central?1:0,int32(FMath::Square(1-Old/255.)*(1+4*B/255.)*P));
    const int32 Ceiling=FMath::Max(B,FMath::Min(16-int32(-32*P),255));
    return uint8(Old+FMath::Max(0,FMath::Min(Increment,Ceiling-Old)));
}
// 0x1408aaca0 acceptance branch for extrudable mud, no overlay and base A=255.
// Other material/overlay flags deliberately do not enter this mud-only branch.
inline bool AcceptMud(uint8 Old,uint8 Base,double P)
{
    const double Soft=FMath::Max(Sat((Base/255.-.2)/.6),.9);
    return int32(Sat(P)*255+.5)>int32((Old/255.+(1-Soft)*.4)*255+.5);
}
inline double CollisionFloor(double H,double Q) { return H-.05-Q; }
inline FOutput Evaluate(const FInput& I)
{
    FOutput O;
    const double R=I.Radius,W=FMath::Max(I.Width,.2),D=FMath::Max(I.Depth,0.);
    if(R<=0 || I.FullPushDepth<=0 || D<(I.bWater?.05:.025))return O;
    FVector V=I.Velocity;
    for(int32 Axis : {0,2}) V[Axis]=FMath::Lerp(I.PredictedDisplacement[Axis]*60,I.Velocity[Axis],Sat(I.Velocity[Axis]/.2-.5));
    const double Speed=V.Size();const FVector DragV=Speed>1?V*FMath::Pow(Speed,-.25):V;
    const FVector F(I.Forward.X,0,I.Forward.Z),A(I.Axle.X,0,I.Axle.Z);
    FVector Drag=(-F*(FVector::DotProduct(F,DragV)*FMath::Min(D,2*R)*W)
        -A*(FVector::DotProduct(A,DragV)*PI*R*FMath::Min(D,2*R))).GetClampedToMaxSize(8)*I.LinearResistance;
    O.Support=FMath::Min(Sat((D-.5*I.Q)/I.FullPushDepth)*2*R*W*I.PushResistance,128.);
    O.Support=FMath::Max(O.Support-128*FMath::Max(I.PredictedDisplacement.Y,0.),0.);
    FVector Linear(Drag.X,FMath::Max(Drag.Y+O.Support,0.),Drag.Z);
    FVector Current=I.Flow*I.FlowImpulse;const double N=Current.Size();
    if(N>1.e-4)Current*=1-Sat(FVector::DotProduct(Current,V)/(N*N));
    Linear+=Current*(R*W*FMath::Min(D/(2*R),1.));
    const double U=FMath::Abs(I.Omega)*R,Aligned=I.Omega<0?-I.RollingSpeed:I.RollingSpeed;
    FVector Angular=FVector::ZeroVector;
    if(U>Aligned)
    {
        const double S=U-Aligned;
        Angular=(I.Axle*(I.Omega>0?-S:S)).GetClampedToMaxSize(8)
            *(FMath::Min(D/.4,1.)*.1*I.Friction*FMath::Clamp(I.WheelMass/200,.25,4.));
        if(I.DriveState>1.e-4)
        {
            O.Drive=Slip(S)*Depth(D,R)*I.TireFriction*I.Friction/(1+.05*U)
                *(.5+.5*FMath::Min(W/.52,4.))*(.5+.5*FMath::Min(I.MassPerWheel/4000,1.));
            if(I.Omega<0)O.Drive=-O.Drive;
            Linear+=I.Forward*O.Drive;
        }
    }
    else if(I.DriveState<=1.e-4)
    {
        const double Difference=(Aligned-U)*(I.RollingSpeed<0?-1:1);
        const double Alignment=FMath::Abs(FVector::DotProduct(I.Velocity.GetSafeNormal(),I.Forward));
        const double K=Sat(2-D/R)*.0004*Difference*I.Friction*Sat(2*(Alignment*FMath::Min(FMath::Abs(I.RollingSpeed)/.1,1.)-.5));
        if(FMath::Abs(K)>1.e-4)
        {
            const FVector X=I.Axle*K;
            Angular=FVector(FVector::DotProduct(I.InertiaRows[0],X),FVector::DotProduct(I.InertiaRows[1],X),FVector::DotProduct(I.InertiaRows[2],X));
        }
    }
    O.LinearImpulse=Linear*60;O.AngularImpulse=Angular*60;return O;
}
// Q swaps native Y/Z (det Q=-1). Axial vectors need the additional minus sign.
inline FVector PolarToUnreal(FVector V) { return FVector(V.X,V.Z,V.Y); }
inline FVector AxialToUnreal(FVector V) { return -PolarToUnreal(V); }
}
