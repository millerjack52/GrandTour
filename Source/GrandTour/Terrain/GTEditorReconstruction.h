#pragma once
#include "CoreMinimal.h"

// Reconstructed arithmetic. Evidence: Art/Export/MudRunnerEditorResearch/Deep.
// This is not the native editor's complete build scheduler or placement pipeline.
namespace GTEditorReconstruction
{
struct FRandom
{
    uint32 State;
    explicit FRandom(uint32 Seed) : State(Seed) {}
    uint32 Next() { State=State*214013u+2531011u; return (State>>16)&32767u; }
    float Unit() { return float(Next())/32767.f; }
};
struct GRANDTOUR_API FCurve
{
    TArray<float> X,Y,B,C,D;
    bool Build(const TArray<float>& Knots,const TArray<float>& Values);
    float At(float T) const;
    float Derivative(float T) const;
};
using FPatternBank=TArray<TArray<FVector2f>>;
GRANDTOUR_API FPatternBank Patterns(int32 Budget,uint32 Seed);
GRANDTOUR_API bool Density(float Effective,float Minimum,float Multiplier,float Attenuation,FRandom& Random);
GRANDTOUR_API float Scale(float Green,float MinMap,float MaxMap,float MinSize,float MaxSize,float Jitter,FRandom& Random);
// Ordinary plants only: inclusive green-map ranges, then one random selection.
GRANDTOUR_API int32 SelectVariant(float Green,const TArray<FVector2f>& Ranges,FRandom& Random);
GRANDTOUR_API uint8 RoadAlpha(float DistanceM,float LengthM);
GRANDTOUR_API FVector2f RoadUV(float DistanceM,float SignedAcrossM,float DefaultWidthM,float DiffuseAspect);
GRANDTOUR_API float RoadOffsetCm(float Red,float Alpha);
GRANDTOUR_API float SampleRoadRed(const TArray<uint8>& BGRA,int32 Width,int32 Height,FVector2f UV);
// Host seed addressing: stable across tile order, not the native global scheduler.
GRANDTOUR_API uint32 CellSeed(int32 X,int32 Y,uint32 Seed,uint32 Channel);
}
