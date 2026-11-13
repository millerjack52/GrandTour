#pragma once
#include "CoreMinimal.h"

/** Shared RR workshop specification. Distances are cm; rates use Chaos wheel authoring units. */
namespace GTRangeRoverSuspension
{
    struct FKit { const TCHAR* Id; const TCHAR* Name; float Rate, Damping, Drop, Rollbar; };
    inline const FKit& Kit(int32 Index)
    {
        static const FKit Kits[] = {
            {TEXT("Part.Suspension"),TEXT("Standard"),340.f,.62f,16.f,1.f},
            {TEXT("Part.SuspensionHD"),TEXT("Touring"),410.f,.72f,18.f,1.1f},
            {TEXT("Part.SuspensionTrail"),TEXT("Trail"),360.f,.68f,21.f,.85f}};
        return Kits[FMath::Clamp(Index,0,2)];
    }
    inline int32 Index(FName Id) { return Id==Kit(2).Id ? 2 : Id==Kit(1).Id ? 1 : 0; }
    // Conservative hull of all three authored tyres clears the unchanged arches at full lock.
    inline float Raise(int32 Wheel) { return Wheel<2 ? 0.f : 2.5f; }
}
