#include "GTLidarTreeInstances.h"
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
			const auto Seeds = GTLidarTreeInstances::RandomSeeds(*Source);
			for (int32 I = 0; I < Source->GetInstanceCount(); ++I)
			{
				const FVector P = Source->GetComponentTransform().TransformPosition(Source->PerInstanceSMData[I].Transform.GetOrigin());
				Cells.FindOrAdd(FIntPoint(FMath::FloorToInt(P.X / CellCm), FMath::FloorToInt(P.Y / CellCm))).Add(I);
			}
			for (const auto& Cell : Cells)
			{
				auto* Mesh = NewObject<UInstancedStaticMeshComponent>(Owner, NAME_None, RF_Transient, Template);
				Mesh->SetupAttachment(Source->GetAttachParent(), Source->GetAttachSocketName());
				Mesh->SetRelativeTransform(Source->GetRelativeTransform());
				GTLidarTreeInstances::CopySubset(*Mesh, *Source, Cell.Value, Seeds);
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
