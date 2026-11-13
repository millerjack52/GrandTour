#include "Dressing/GTDressingTestRunner.h"

#include "Dressing/OWRoadBedComponent.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "LandscapeComponent.h"
#include "LandscapeLayerInfoObject.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInterface.h"

namespace GTDressingTest
{
	constexpr float JudgeAfterSeconds = 3.f;
	constexpr int32 JudgeAfterTicks = 10;
	constexpr int32 ExpectedRoads = 3;

	const TCHAR* const LayerInfoNames[] = {
		TEXT("OW_Meadow_LayerInfo"), TEXT("OW_MeadowLush_LayerInfo"), TEXT("OW_MeadowDry_LayerInfo"), TEXT("OW_Bare_LayerInfo"),
		TEXT("OW_Alpine_LayerInfo"), TEXT("OW_Snow_LayerInfo"), TEXT("OW_Forest_LayerInfo"), TEXT("OW_ForestBeech_LayerInfo"),
		TEXT("OW_ForestBirch_LayerInfo"), TEXT("OW_ForestFir_LayerInfo"), TEXT("OW_ForestOak_LayerInfo"), TEXT("OW_Scree_LayerInfo"),
		TEXT("OW_RoadVerge_LayerInfo"),
	};
	const TCHAR* const BiomeTags[] = {
		TEXT("OWBiome.Forest"), TEXT("OWBiome.Meadow"), TEXT("OWBiome.Scree"),
		TEXT("OWBiome.Alpine"), TEXT("OWBiome.Cliff"), TEXT("OWBiome.Road"),
	};

	void Line(const FString& Text)
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST dressing %s"), *Text);
	}
}

FGTDressingTestRunner::FGTDressingTestRunner(UWorld* InWorld)
	: World(InWorld)
{
}

bool FGTDressingTestRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
{
	Elapsed += DeltaSeconds;
	++Ticks;
	if (Elapsed < GTDressingTest::JudgeAfterSeconds || Ticks < GTDressingTest::JudgeAfterTicks)
	{
		return false;
	}
	Judge(bOutPass, OutSummary);
	return true;
}

void FGTDressingTestRunner::Judge(bool& bOutPass, FString& OutSummary) const
{
	using namespace GTDressingTest;

	UWorld* W = World.Get();
	if (!W)
	{
		bOutPass = false;
		OutSummary = TEXT("no world");
		return;
	}
	TArray<FString> Failures;

	// 1. Roads: 3 actors whose class name starts with BP_OWRoad, each with a UOWRoadBedComponent.
	{
		int32 Roads = 0;
		int32 WithBed = 0;
		FString Names;
		for (TActorIterator<AActor> It(W); It; ++It)
		{
			const FString ClassName = It->GetClass()->GetName();
			if (!ClassName.StartsWith(TEXT("BP_OWRoad")))
			{
				continue;
			}
			++Roads;
			const bool bBed = It->FindComponentByClass<UOWRoadBedComponent>() != nullptr;
			WithBed += bBed ? 1 : 0;
			Names += FString::Printf(TEXT(" %s(bed=%d)"), *ClassName, bBed ? 1 : 0);
		}
		Line(FString::Printf(TEXT("roads %d, with road bed %d:%s"), Roads, WithBed, *Names));
		if (Roads != ExpectedRoads || WithBed != ExpectedRoads)
		{
			Failures.Add(FString::Printf(TEXT("roads %d with bed %d (want %d)"), Roads, WithBed, ExpectedRoads));
		}
	}

	// 2 and 3. The landscape material, and the layer infos in the weightmap allocations.
	{
		int32 Proxies = 0;
		int32 WrongMaterial = 0;
		TSet<FString> Found;
		for (TActorIterator<ALandscapeProxy> It(W); It; ++It)
		{
			++Proxies;
			const UMaterialInterface* Material = It->GetLandscapeMaterial();
			const FString Path = Material ? Material->GetPathName() : FString(TEXT("none"));
			Line(FString::Printf(TEXT("landscape %s material %s"), *It->GetName(), *Path));
			if (!Path.EndsWith(TEXT("MI_OWDressingLab_Style")))
			{
				++WrongMaterial;
			}
			for (const ULandscapeComponent* Component : It->LandscapeComponents)
			{
				if (!Component)
				{
					continue;
				}
				for (const FWeightmapLayerAllocationInfo& Allocation : Component->GetWeightmapLayerAllocations())
				{
					Found.Add(Allocation.LayerInfo ? Allocation.LayerInfo->GetName() : FString(TEXT("null")));
				}
			}
		}
		if (Proxies == 0)
		{
			Failures.Add(TEXT("no landscape"));
		}
		else if (WrongMaterial > 0)
		{
			Failures.Add(FString::Printf(TEXT("landscape material is not MI_OWDressingLab_Style on %d of %d"), WrongMaterial, Proxies));
		}

		TSet<FString> Expected;
		for (const TCHAR* Name : LayerInfoNames)
		{
			Expected.Add(Name);
		}
		TArray<FString> Sorted = Found.Array();
		Sorted.Sort();
		Line(FString::Printf(TEXT("layer infos %d: %s"), Sorted.Num(), *FString::Join(Sorted, TEXT(" "))));
		TArray<FString> Missing;
		for (const FString& Name : Expected)
		{
			if (!Found.Contains(Name))
			{
				Missing.Add(Name);
			}
		}
		TArray<FString> Extra;
		for (const FString& Name : Sorted)
		{
			if (!Expected.Contains(Name) || Name.Contains(TEXT("Bed")) || Name.Contains(TEXT("RiverWet")))
			{
				Extra.Add(Name);
			}
		}
		Missing.Sort();
		if (Missing.Num() > 0 || Extra.Num() > 0)
		{
			Failures.Add(FString::Printf(TEXT("layer infos: missing [%s] unexpected [%s]"), *FString::Join(Missing, TEXT(" ")), *FString::Join(Extra, TEXT(" "))));
		}
	}

	// 4. Each OWBiome.* actor owns ISM instances.
	{
		for (const TCHAR* Tag : BiomeTags)
		{
			const FName TagName(Tag);
			int32 Actors = 0;
			int32 Components = 0;
			int32 Instances = 0;
			for (TActorIterator<AActor> It(W); It; ++It)
			{
				if (!It->Tags.Contains(TagName))
				{
					continue;
				}
				++Actors;
				TArray<UInstancedStaticMeshComponent*> Ism;
				It->GetComponents<UInstancedStaticMeshComponent>(Ism);
				for (const UInstancedStaticMeshComponent* Component : Ism)
				{
					++Components;
					Instances += Component ? Component->GetInstanceCount() : 0;
				}
			}
			Line(FString::Printf(TEXT("biome %s actors %d ism components %d instances %d"), Tag, Actors, Components, Instances));
			if (Actors == 0)
			{
				Failures.Add(FString::Printf(TEXT("no actor tagged %s"), Tag));
			}
			else if (Instances <= 0)
			{
				Failures.Add(FString::Printf(TEXT("%s has no ISM instances"), Tag));
			}
		}
	}

	bOutPass = Failures.Num() == 0;
	OutSummary = bOutPass ? TEXT("toolkit test map: roads, material, 13 layers and 6 biomes all present") : FString::Join(Failures, TEXT("; "));
}
