#include "Terrain/GTLandscapeSurface.h"

FLinearColor AGTLandscapeSurface::MaterialAt(FVector2D World) const
{
    const int32 N=MaterialResolution;
    if(N<2 || N>2048 || MaterialCells.Num()!=N*N)return FLinearColor(0,0,.35f,0);
    const FVector2D UV=(World-PaintOriginCm)/FMath::Max(1.f,PaintSizeCm);
    if(UV.X<0 || UV.Y<0 || UV.X>=1 || UV.Y>=1)return FLinearColor(0,0,.35f,1);
    const FVector2D P=UV*N-FVector2D(.5,.5);
    const int32 X=FMath::FloorToInt(P.X),Y=FMath::FloorToInt(P.Y);
    auto Read=[&](int32 A,int32 B){return MaterialCells[FMath::Clamp(B,0,N-1)*N+FMath::Clamp(A,0,N-1)];};
    return FMath::Lerp(FMath::Lerp(Read(X,Y),Read(X+1,Y),float(P.X-X)),
        FMath::Lerp(Read(X,Y+1),Read(X+1,Y+1),float(P.X-X)),float(P.Y-Y));
}

bool AGTLandscapeSurface::NativeMudAt(FVector2D World) const
{
    if(!bUseNativeSubstanceResponse)return false;
    if(MaterialResolution<2)return true;
    const auto M=MaterialAt(World);
    return M.R<.5f && (bGrassIsVisualCover || M.G<.5f) && M.A<.5f;
}

FLinearColor AGTLandscapeSurface::ClayAt(FVector2D World) const
{
    const int32 N=ClayResolution;
    // Outside the atlas, or without one: no clay, no orange face, no slurry.
    if(N<2 || N>2048 || ClayCells.Num()!=N*N)return FLinearColor(0,0,0,0);
    const FVector2D UV=(World-PaintOriginCm)/FMath::Max(1.f,PaintSizeCm);
    if(UV.X<0 || UV.Y<0 || UV.X>=1 || UV.Y>=1)return FLinearColor(0,0,0,0);
    const FVector2D P=UV*N-FVector2D(.5,.5);
    const int32 X=FMath::FloorToInt(P.X),Y=FMath::FloorToInt(P.Y);
    auto Read=[&](int32 A,int32 B){const FColor& C=ClayCells[FMath::Clamp(B,0,N-1)*N+FMath::Clamp(A,0,N-1)];return FLinearColor(C.R,C.G,C.B,C.A)*(1.f/255.f);};
    return FMath::Lerp(FMath::Lerp(Read(X,Y),Read(X+1,Y),float(P.X-X)),
        FMath::Lerp(Read(X,Y+1),Read(X+1,Y+1),float(P.X-X)),float(P.Y-Y));
}

bool AGTLandscapeSurface::HasClay() const
{
    if(ClayResolution>1 && ClayCells.Num()==ClayResolution*ClayResolution)return true;
    for(const auto& Region:MudRegions)if(Region.ClayWeight>0.f)return true;
    return false;
}

float AGTLandscapeSurface::ClayWeightAt(FVector2D World) const
{
    float Clay=ClayResolution>1 ? ClayAt(World).R : 0.f;
    // Only regions that carry clay are tested for containment, so maps without clay pay a float compare per region.
    for(const auto& Region:MudRegions)
        if(Region.ClayWeight>0.f && Region.Contains(World))Clay=FMath::Max(Clay,Region.ClayWeight);
    return FMath::Clamp(Clay,0.f,1.f);
}
