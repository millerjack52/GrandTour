#pragma once
#include "CoreMinimal.h"

// Media.zip scripts/{common,mud,water}.lua, build 9640861. Metres, native Y-up.
// This is the source's emission calculation; the renderer/Chaos inputs are adapters.
namespace GTMudRunnerWheelFX
{
enum EKind { MudSmall, MudLarge, WaterSmall, WaterMedium, WaterLarge, WaterFluid, MudBits, WaterDrops, WaterBits, Count };
struct FWheel
{
    FVector Org=FVector::ZeroVector,Velocity=FVector::ZeroVector;
    FVector Forward=FVector(1,0,0),Up=FVector(0,1,0),Axle=FVector(0,0,1);
    double Radius=.33,Width=.25,Omega=0,Speed=0,MudDepth=0,WaterDepth=0;
    bool Inside=false,Right=true;
    int32 WheelCount=4;
};
struct FSpawn { EKind Kind; FVector Org,Velocity; double Scale=1,Opacity=1; };
inline double Sat(double V){return FMath::Clamp(V,0.,1.);}
// Lua numeric for-loop truncates counts >=1; below 1 it uses a Bernoulli draw.
template<class TRandom> int32 Number(double Interval,double Amount,double Dt,TRandom&& Random)
{
    if(Interval<1.e-5 || Amount<1.e-5)return 0;
    const double N=Dt*Amount/Interval;
    return N<1 ? (Random()<N?1:0) : FMath::FloorToInt(N);
}
template<class TRandom,class TEmit> void Emit(const FWheel& W,double Dt,TRandom&& R,TEmit&& Add)
{
    if(W.Radius<=0 || Dt<=0)return;
    const auto RS=[&](){return R()-.5;};
    const FVector Cos=W.Omega>0?-W.Forward:W.Forward;
    FVector Out=W.Axle*(W.Right?1:-1);Out.Y=0;
    if(W.WaterDepth<.1)
    {
        const double V=W.Omega>0?FMath::Max(W.Omega-W.Speed/W.Radius*.5,0.):FMath::Max(W.Speed/W.Radius*.5-W.Omega,0.);
        double A=Sat((V-1.5)/2.5)*Sat((W.MudDepth-.05)/(W.Radius*.25));
        if(W.Inside)A*=.35;
        const int32 N=Number(.032,A,Dt,R);
        const double Scale=1+FMath::Clamp(V-6,0.,16.)*.02,Opacity=FMath::Min(A*2,1.);
        const double Depth=FMath::Clamp(W.MudDepth/W.Radius-.2,0.,.5);
        double Angular=FMath::Min(V,22.)*W.Radius;
        Angular=FMath::Lerp(Angular*.5,FMath::Sqrt(Angular/6)*2,Sat((FMath::Abs(W.Speed)-.25)/.5));
        for(int32 I=0;I<N;++I)
        {
            const double Angle=PI*(R()*.5+Depth*.7-.4),X=FMath::Cos(Angle),Y=FMath::Sin(Angle);
            FVector P=W.Org+W.Axle*(RS()*W.Width*.5)+(Cos*X+W.Up*Y)*(W.Radius-.05);
            P.Y-=FMath::Max(W.Radius-W.MudDepth,0.);
            FVector V0=(-Cos*Y+W.Up*X+W.Velocity*.25)*Angular;
            if(W.Inside){V0.X*=.2;V0.Z*=.2;}
            P.X+=W.Velocity.X*.15;P.Y-=V0.Y*.1;P.Z+=W.Velocity.Z*.15;
            Add(FSpawn{MudSmall,P,V0,Scale,Opacity});
        }
        const double Impact=Sat((FMath::Abs(W.Speed)-4)/2.5)*Sat((W.MudDepth-.2)/.1);
        const int32 NI=Number(FMath::Max(.2+FMath::Min(W.Velocity.Y,0.),.05),Impact,Dt,R);
        for(int32 I=0;I<NI;++I)
        {
            FVector P=W.Org+W.Axle*(W.Right?1:-1)*(W.Width*.5);P.Y-=.25;
            const double L=FMath::Min(W.Velocity.Size()*.5,4.);
            FVector V0(W.Velocity.X*.5+RS(),.5+L*.5,W.Velocity.Z*.5+RS());
            V0+=W.Axle*(W.Right?1:-1)*(L*.1);
            Add(FSpawn{MudLarge,P,V0,.6+R()*.5,1});
        }
    }
    const double Depth=W.WaterDepth>W.Radius?Sat((W.Radius*2-W.WaterDepth)/.4):Sat(W.WaterDepth/.4);
    const double Soft=FMath::Min(Depth/.33,1.);
    const double V=W.Omega>0?FMath::Max(W.Omega*W.Radius-W.Speed*.8,0.):FMath::Max(W.Speed*.8-W.Omega*W.Radius,0.);
    double Splash=Sat((V-.5)*.5);if(W.Inside)Splash*=.35;
    const int32 NS=Number(.008,Splash*Soft,Dt,R);
    const FVector Clamped=W.Velocity.GetClampedToMaxSize(6);
    const double Scale=1+FMath::Min(FMath::Abs(W.Velocity.Y)*.25,1.)+FMath::Max(V-2,0.)*.05;
    const double Angle0=FMath::Clamp(W.WaterDepth/W.Radius-.5,0.,.5)*.8-.4;
    for(int32 I=0;I<NS;++I)
    {
        const double Angle=PI*(R()*.5+Angle0),X=FMath::Cos(Angle),Y=FMath::Sin(Angle);
        FVector P=W.Org+(W.Axle*(RS()*W.Width*.5)+(Cos*X+W.Up*Y)*W.Radius)*.8;
        FVector V0=(-Cos*Y+W.Up*X)*FMath::Min(V,8.)+Clamped;V0.Y*=.6;
        if(W.Inside){V0.X*=.5;V0.Z*=.5;}
        Add(FSpawn{WaterSmall,P,V0,Scale,(.1+Splash*.9)*Soft});
    }
    const double Wheels=W.WheelCount>6?FMath::Max(1-(W.WheelCount-6)/8.,.5):1;
    const double LS=FMath::Max(Sat((FMath::Abs(W.Speed)-3.5)/.5),Sat((-FMath::Min(W.Velocity.Y,0.)-1))*1.2);
    if(LS>.01 && Soft>.01)
    {
        const double LP=Sat((FMath::Abs(W.Speed)-5.5)/3.5);
        const int32 NB=Number(FMath::Max(.15+FMath::Min(W.Velocity.Y,0.)-LP*.1,.05),Wheels,Dt,R);
        if(NB>0)
        {
            const double L=Sat((FMath::Abs(W.Speed)-2)/4.5);
            FVector P=W.Org-Out*.25;P.Y-=W.Radius-W.WaterDepth+FMath::Min(W.WaterDepth,.25)+.25;
            P.X+=W.Velocity.X*.2;P.Y+=FMath::Min(W.Velocity.Y,0.)*.06;P.Z+=W.Velocity.Z*.2;
            FVector V0=Out*(.4+Depth*L*2);const double M=.4+R()*.2;
            V0.X+=W.Velocity.X*Soft*M;V0.Z+=W.Velocity.Z*Soft*M;V0.Y=FMath::Min(1.3+.5*Soft+L*.8,5.);
            V0=FMath::Lerp(V0,FVector(0,5,0),Sat(-W.Velocity.Y)*.4);
            for(int32 I=0;I<NB;++I)
            {
                FVector VV=V0;VV.X+=RS();VV.Z+=RS();const EKind K=R()<.5?WaterLarge:WaterMedium;
                Add(FSpawn{K,P,VV,.85-FMath::Min(W.Velocity.Y,0.)*.04,FMath::Min(LS*Soft,.7)});
            }
        }
    }
    const double Fluid=Sat((FMath::Abs(W.Speed)-1.5)/2)*Soft;
    const int32 NF=Number(.18,Fluid*Wheels,Dt,R);
    if(NF>0)
    {
        const double L=Sat((FMath::Abs(W.Speed)-1.2)/2.8);
        FVector V0=W.Velocity*.8;V0.Y=L*1.2+.6;V0+=Out*.2;
        FVector P=W.Org;P.Y+=-W.Radius+W.WaterDepth+.15;P.X+=W.Velocity.X*.1;P.Z+=W.Velocity.Z*.1;
        for(int32 I=0;I<NF;++I)Add(FSpawn{WaterFluid,P,V0,.5+L*.5,.4+Fluid*.4});
    }
}
// Particles VS_001: piecewise linear size, independent of sprite alpha spline.
inline double Curve(FVector Values,double Median,double Age)
{
    return Age<Median?FMath::Lerp(Values.X,Values.Y,Age/FMath::Max(Median,1.e-6)):
        FMath::Lerp(Values.Y,Values.Z,Sat((Age-Median)/FMath::Max(1-Median,1.e-6)));
}
// Particles VS_001: initial velocity decelerates linearly to zero in |v|/AirResistance seconds;
// gravity has its own ballistic term (it is NOT exponential drag on total velocity).
inline FVector Position(FVector P,FVector V,double Age,double AirResistance,double Gravity)
{
    const double Stop=V.Size()/FMath::Max(AirResistance,1.e-6),T=FMath::Min(Age,Stop);
    return P+(Stop>1.e-8?V*(T-.5*T*T/Stop):FVector::ZeroVector)+FVector(0,.5*Gravity*Age*Age,0);
}
// 0x14088ba6b..0x14088bae6: source emits batches of 16. For N<1 the
// acceptance probability is 1-(1-N)^2, NOT the Lua parent's Bernoulli rate.
inline int32 ChildCount(double MeanSize,double Density,double HeightFraction,double Random)
{
    const double N=MeanSize*Density*Sat(HeightFraction)/16;
    if(N<1 && Random>1-FMath::Square(1-N))return 0;
    return 16*FMath::Clamp(FMath::TruncToInt(N),1,64);
}
}
