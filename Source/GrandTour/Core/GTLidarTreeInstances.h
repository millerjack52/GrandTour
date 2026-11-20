#pragma once

#include "Components/InstancedStaticMeshComponent.h"

namespace GTLidarTreeInstances
{
	inline TArray<int32> RandomSeeds(const UInstancedStaticMeshComponent& Source)
	{
		TArray<int32> Seeds;
		Seeds.Reserve(Source.GetInstanceCount());
		FRandomStream Stream(Source.InstancingRandomSeed);
		int32 Reset = 0;
		for (int32 Index = 0; Index < Source.GetInstanceCount(); ++Index)
		{
			if (Source.AdditionalRandomSeeds.IsValidIndex(Reset) && Source.AdditionalRandomSeeds[Reset].StartInstanceIndex == Index)
				Stream.Initialize(Source.AdditionalRandomSeeds[Reset++].RandomSeed);
			Seeds.Add(Stream.GetCurrentSeed());
			Stream.GetFraction();
		}
		return Seeds;
	}

	inline void CopySubset(UInstancedStaticMeshComponent& To, const UInstancedStaticMeshComponent& From,
		const TArray<int32>& Indices, const TArray<int32>& Seeds)
	{
		To.PerInstanceSMData.Reset(Indices.Num());
		To.AdditionalRandomSeeds.Reset();
		To.InstancingRandomSeed = Seeds[Indices[0]];
		// Registration generates a new seed if it sees zero. Restore zero on the first instance.
		if (To.InstancingRandomSeed == 0)
		{
			To.InstancingRandomSeed = 1;
			To.AdditionalRandomSeeds.AddDefaulted();
		}
		for (int32 Local = 0; Local < Indices.Num(); ++Local)
		{
			const int32 Index = Indices[Local];
			if (Local > 0 && (Index != Indices[Local - 1] + 1 || !From.AdditionalRandomSeeds.IsEmpty()))
			{
				auto& Reset = To.AdditionalRandomSeeds.AddDefaulted_GetRef();
				Reset.StartInstanceIndex = Local;
				Reset.RandomSeed = Seeds[Index];
			}
			To.PerInstanceSMData.Add(From.PerInstanceSMData[Index]);
		}
	}
}
