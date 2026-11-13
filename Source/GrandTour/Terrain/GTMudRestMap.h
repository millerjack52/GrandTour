#pragma once
#include "CoreMinimal.h"

/** Cell-centred world map sampling shared with the shader's clamped bilinear lookup. */
namespace GTMudRestMap
{
inline float SamplePeriodic(const TArray<float>& Data,int32 N,float Size,FVector2D World)
{
    if(N<2 || N>1024 || Data.Num()!=N*N || !FMath::IsFinite(Size) || Size<=0 || World.ContainsNaN())return 0;
    const FVector2D UV=World/Size;
    const FVector2D P((UV.X-FMath::FloorToDouble(UV.X))*N-.5,(UV.Y-FMath::FloorToDouble(UV.Y))*N-.5);
    const int32 X=FMath::FloorToInt(P.X),Y=FMath::FloorToInt(P.Y);
    auto Read=[&](int32 A,int32 B){return Data[((B+N)%N)*N+(A+N)%N];};
    return FMath::Lerp(FMath::Lerp(Read(X,Y),Read(X+1,Y),float(P.X-X)),FMath::Lerp(Read(X,Y+1),Read(X+1,Y+1),float(P.X-X)),float(P.Y-Y));
}
inline float ReliefWeight(FLinearColor Material,float Thickness,bool GrassIsVisualCover=false)
{
    return FMath::Clamp((1-Material.R)*(GrassIsVisualCover ? 1.f : 1-Material.G)*(1-Material.A),0.f,1.f)*FMath::SmoothStep(4.f,30.f,Thickness);
}
inline float Sample(const TArray<float>& Data,int32 N,FVector2D Origin,float Size,FVector2D World)
{
    if(N<2 || N>1024 || Data.Num()!=N*N || !FMath::IsFinite(Size) || Size<=0 || World.ContainsNaN()) return 0;
    const FVector2D UV=(World-Origin)/Size;
    if(UV.X<0 || UV.Y<0 || UV.X>1 || UV.Y>1) return 0;
    const FVector2D P=UV*N-FVector2D(.5,.5);
    const int32 X=FMath::FloorToInt(P.X),Y=FMath::FloorToInt(P.Y);
    auto Read=[&](int32 A,int32 B) { return Data[FMath::Clamp(B,0,N-1)*N+FMath::Clamp(A,0,N-1)]; };
    return FMath::Lerp(FMath::Lerp(Read(X,Y),Read(X+1,Y),float(P.X-X)),
        FMath::Lerp(Read(X,Y+1),Read(X+1,Y+1),float(P.X-X)),float(P.Y-Y));
}
}
