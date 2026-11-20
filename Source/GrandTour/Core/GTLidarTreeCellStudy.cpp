#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"

#if !UE_BUILD_SHIPPING
namespace
{
	// Standalone diagnostic. The original components and the authored map stay intact.
	void TrialTreeCells(const TArray<FString>& Args, UWorld* World)
	{
		if (!World || !World->IsGameWorld() || UGameplayStatics::GetCurrentLevelName(World, true) != TEXT("L_LidarStudy") || Args.Num() != 1)
		{
			return;
		}
		const int32 CellMetres = FCString::Atoi(*Args[0]);
		if (CellMetres < 32 || CellMetres > 1024)
		{
			return;
		}
		TArray<UInstancedStaticMeshComponent*> Sources;
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			TInlineComponentArray<UInstancedStaticMeshComponent*> Meshes(*It);
			for (auto* Mesh : Meshes)
			{
				if (!Mesh->ComponentHasTag(TEXT("FloraWorldCanopy")) && !Mesh->ComponentHasTag(TEXT("FloraWorldSaplings")))
				{
					continue;
				}
				if (!Mesh->IsVisible() || Mesh->GetCollisionEnabled() != ECollisionEnabled::NoCollision ||
					Mesh->NumCustomDataFloats != 0 || Mesh->GetClass() != UInstancedStaticMeshComponent::StaticClass())
				{
					UE_LOG(LogTemp, Error, TEXT("GT_TREE_CELLS unexpected source %s"), *Mesh->GetPathName());
					return;
				}
				Sources.Add(Mesh);
			}
		}
		if (Sources.Num() != 6)
		{
			UE_LOG(LogTemp, Error, TEXT("GT_TREE_CELLS expected six original groups, found %d"), Sources.Num());
			return;
		}
		int32 TotalCells = 0;
		int32 TotalTrees = 0;
		const double CellCm = CellMetres * 100.;
		for (auto* Source : Sources)
		{
			AActor* Owner = Source->GetOwner();
			// Use a single empty template per family to retain all authored component settings.
			auto* Template = NewObject<UInstancedStaticMeshComponent>(Owner, NAME_None, RF_Transient, Source);
			Template->ClearInstances();
			Template->AdditionalRandomSeeds.Reset();
			Template->ComponentTags = {TEXT("LidarTreeCellTrial")};
			TMap<FIntPoint, TArray<int32>> Cells;
			TArray<int32> Seeds;
			Seeds.Reserve(Source->GetInstanceCount());
			FRandomStream Stream(Source->InstancingRandomSeed);
			int32 Reset = 0;
			for (int32 I = 0; I < Source->GetInstanceCount(); ++I)
			{
				if (Source->AdditionalRandomSeeds.IsValidIndex(Reset) && Source->AdditionalRandomSeeds[Reset].StartInstanceIndex == I)
				{
					Stream.Initialize(Source->AdditionalRandomSeeds[Reset++].RandomSeed);
				}
				Seeds.Add(Stream.GetCurrentSeed());
				Stream.GetFraction();
				const FVector P = Source->GetComponentTransform().TransformPosition(Source->PerInstanceSMData[I].Transform.GetOrigin());
				Cells.FindOrAdd(FIntPoint(FMath::FloorToInt(P.X / CellCm), FMath::FloorToInt(P.Y / CellCm))).Add(I);
			}
			for (const auto& Cell : Cells)
			{
				auto* Mesh = NewObject<UInstancedStaticMeshComponent>(Owner, NAME_None, RF_Transient, Template);
				Mesh->SetupAttachment(Source->GetAttachParent(), Source->GetAttachSocketName());
				Mesh->SetRelativeTransform(Source->GetRelativeTransform());
				Mesh->InstancingRandomSeed = Seeds[Cell.Value[0]];
				// A zero initial seed is regenerated on registration. An explicit index-zero reset preserves it.
				if (Mesh->InstancingRandomSeed == 0)
				{
					Mesh->InstancingRandomSeed = 1;
					Mesh->AdditionalRandomSeeds.AddDefaulted();
				}
				for (int32 Index : Cell.Value)
				{
					const int32 Local = Mesh->PerInstanceSMData.Num();
					if (Local > 0 && (Index != Cell.Value[Local - 1] + 1 || !Source->AdditionalRandomSeeds.IsEmpty()))
					{
						auto& Seed = Mesh->AdditionalRandomSeeds.AddDefaulted_GetRef();
						Seed.StartInstanceIndex = Local;
						Seed.RandomSeed = Seeds[Index];
					}
					// Preserve the raw instance matrix, including its full affine basis.
					Mesh->PerInstanceSMData.Add(Source->PerInstanceSMData[Index]);
				}
				Owner->AddInstanceComponent(Mesh);
				Mesh->RegisterComponent();
				++TotalCells;
				TotalTrees += Mesh->GetInstanceCount();
			}
			Source->SetVisibility(false);
		}
		UE_LOG(LogTemp, Display, TEXT("GT_TREE_CELLS groups=%d cells=%d trees=%d metres=%d"), Sources.Num(), TotalCells, TotalTrees, CellMetres);
	}

	FAutoConsoleCommandWithWorldAndArgs TreeCellStudy(
		TEXT("gt.Lidar.TrialTreeCells"), TEXT("Rebatch all six visible LiDAR tree groups in this game into cells of the given size in metres."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(TrialTreeCells));
}
#endif
