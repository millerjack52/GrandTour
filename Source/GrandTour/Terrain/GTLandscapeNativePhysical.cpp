#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTMudRunnerSubstance.h"

namespace { constexpr double NativeSpacingCm=200./3.; }
void AGTLandscapeSurface::ApplyBodySoilContact(FVector Point,FVector Velocity,float MassKg,float WidthCm,float Dt)
{
    if(!HasActorBegunPlay()||!bUseNativeSubstanceResponse||Dt<=0)return;
    const FVector2D XY(Point);const auto S=SampleSurface(XY);const auto H=GroundHeightAt(Point);
    if(!H.IsSet()||!S.bNativeSubstanceResponse||Point.Z>=H.GetValue()+S.SurfaceDeltaCm)return;
    const float Motion=Velocity.Size()*.01f;
    // Native 0x1401b2d90: sqrt(mass/1000), clamped .25..4, times contact motion.
    // Chaos adapter: point speed and a 60-Hz invocation rate, divided across 9 samples.
    const float Excitation=FMath::Clamp(FMath::Sqrt(MassKg/1000.f),.25f,4.f)*Motion;
    if(Excitation>1.e-4f)StampNativePhysical(XY,Excitation*FMath::Min(Dt,.05f)*60.f/9.f);
    // A stationary belly can compress to its actual plane; it cannot excavate
    // below itself or generate an ever-growing mound from zero motion.
    const float Plane=FMath::Max(float(Point.Z-H.GetValue()),-S.SinkageCapCm);
    FVector2D Direction(Velocity);Direction=Direction.IsNearlyZero()?FVector2D(1,0):Direction.GetSafeNormal();
    Field.StampWorked(XY,XY,Direction,WidthCm,S.SinkageCapCm,[this](FVector2D P){return PaintAt(P);},Plane,20.f*FMath::Min(Dt,.05f),
        {bUseRutInteraction,0.f,FMath::Clamp(Motion,0.f,1.f),S.bGranularResponse});
}
void AGTLandscapeSurface::ApplyReviewNativeContact(FVector2D Point,float Excitation)
{
    if(bUseNativeSubstanceResponse)StampNativePhysical(Point,Excitation);
}
uint8 AGTLandscapeSurface::NativeByte(FIntPoint K) const
{
    if(const auto* V=NativeExtrudes.Find(K))return *V;
    // Authored initial state, not decoded STG data. Preserve the old one-byte
    // road seed through 50 cm. Deep bog layers start with a yielding column so
    // they yield on entry. Initial extrusion stays within the estate's ground
    // clearance; the full authored layer remains available for further working.
    const float Depth=PaintAt(FVector2D(K.X,K.Y)*NativeSpacingCm).R;
    return Depth>.01f ? uint8(FMath::Clamp(FMath::RoundToInt(FMath::Max(0.f,Depth-50.f)*.3f*255.f/124.f),1,255)) : 0;
}
float AGTLandscapeSurface::NativeQ(FVector2D XY) const
{
    // Native padded-block texel centres simplify to a 2/3-m world lattice.
    const FVector2D G=XY/NativeSpacingCm;
    const FIntPoint K(FMath::FloorToInt(G.X),FMath::FloorToInt(G.Y));
    return FMath::Lerp(FMath::Lerp(double(NativeByte(K)),double(NativeByte(K+FIntPoint(1,0))),G.X-K.X),
        FMath::Lerp(double(NativeByte(K+FIntPoint(0,1))),double(NativeByte(K+FIntPoint(1,1))),G.X-K.X),G.Y-K.Y)*(124./255.);
}
float AGTLandscapeSurface::NativeUpper(FVector2D XY) const
{
    // H is authored separately from E and never follows the changing visual texture.
    const FVector2D G=XY/NativeSpacingCm;const FIntPoint K(FMath::FloorToInt(G.X),FMath::FloorToInt(G.Y));
    auto H=[&](FIntPoint C){const FVector2D P=FVector2D(C.X,C.Y)*NativeSpacingCm;return Field.RestHeight(P,PaintAt(P).R);};
    return FMath::Lerp(FMath::Lerp(H(K),H(K+FIntPoint(1,0)),G.X-K.X),FMath::Lerp(H(K+FIntPoint(0,1)),H(K+FIntPoint(1,1)),G.X-K.X),G.Y-K.Y);
}
void AGTLandscapeSurface::StampNativePhysical(FVector2D XY,float P)
{
    using namespace GTMudRunnerSubstance;
    if(PaintAt(XY).R<=.01f || !FMath::IsFinite(P) || P<=0)return;
    const FVector2D G=XY/NativeSpacingCm;
    const FIntPoint K(FMath::FloorToInt(G.X+.5),FMath::FloorToInt(G.Y+.5));
    const auto Base=PaintAt(FVector2D(K.X,K.Y)*NativeSpacingCm);
    const uint8 B=uint8(FMath::RoundToInt(FMath::Clamp(Base.A,0.f,1.f)*255));
    if(Base.R<=.01f || !AcceptMud(NativeByte(K),B,P))return;
    const double DX=G.X-K.X,DY=G.Y-K.Y,X=1-FMath::Abs(DX),Y=1-FMath::Abs(DY);
    auto Write=[&](FIntPoint C,double Weight,bool Central)
    {
        const auto Paint=PaintAt(FVector2D(C.X,C.Y)*NativeSpacingCm);if(Paint.R<=.01f)return;
        const uint8 Old=NativeByte(C);
        // Host finite mud layer bounds the native encoding range on this authored road.
        const int32 Limit=FMath::Clamp(FMath::FloorToInt(Paint.R*255.f/124.f),1,255);
        NativeExtrudes.Add(C,uint8(FMath::Min(int32(Extrude(Old,uint8(FMath::RoundToInt(Paint.A*255)),false,P*Weight,Central)),Limit)));
    };
    const int32 SX=DX>.01?1:DX<-.01?-1:0,SY=DY>.01?1:DY<-.01?-1:0;
    Write(K,X*Y,true);
    if(SX)Write(K+FIntPoint(SX,0),(1-X)*Y,false);
    if(SY)Write(K+FIntPoint(0,SY),X*(1-Y),false);
    if(SX&&SY)Write(K+FIntPoint(SX,SY),(1-X)*(1-Y),false);
}
