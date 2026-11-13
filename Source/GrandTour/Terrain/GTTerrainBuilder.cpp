#include "Terrain/GTTerrainBuilder.h"

#include "Harvest/GTHarvestNode.h"
#include "Run/GTLegActors.h"
#include "Run/GTPhotoSubject.h"
#include "Terrain/GTTerrainDressing.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Vehicle/GTVehicleSetupLibrary.h"
#include "Vehicle/GTWinchAnchor.h"

#include "Components/SceneComponent.h"
#include "DrawDebugHelpers.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/Volume.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInterface.h"
#include "UObject/Package.h"

AGTTerrainBuilder::AGTTerrainBuilder()
{
	PrimaryActorTick.bCanEverTick = false;
	bIsEditorOnlyActor = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	RegroundLabelPrefixes = { TEXT("Rock_"), TEXT("Hide_"), TEXT("Roof_"), TEXT("Marker_"), TEXT("Post_"), TEXT("Water_") };
	KeepLabelPrefixes = { TEXT("Floor_Skirt") };
}

bool AGTTerrainBuilder::IsRegroundable(const AActor* Actor) const
{
	if (!Actor || Actor == this || Actor->IsA<ALandscapeProxy>())
	{
		return false;
	}
	if (Actor->IsA<AGTLegVolume>() || Actor->IsA<AGTHarvestNode>() || Actor->IsA<AGTPhotoSubject>() || Actor->IsA<AGTWinchAnchor>() || Actor->IsA<APlayerStart>() || Actor->IsA<AGTLegStart>())
	{
		return true;
	}
#if WITH_EDITOR
	if (Actor->IsA<AStaticMeshActor>())
	{
		const FString Label = Actor->GetActorLabel();
		for (const FString& Prefix : KeepLabelPrefixes)
		{
			if (Label.StartsWith(Prefix))
			{
				return false;
			}
		}
		for (const FString& Prefix : RegroundLabelPrefixes)
		{
			if (Label.StartsWith(Prefix))
			{
				return true;
			}
		}
	}
#endif
	return false;
}

float AGTTerrainBuilder::GroundUnder(const AActor* Actor, const TArray<AActor*>& NotGround, bool& bOutHit) const
{
	bOutHit = false;
	const FVector Location = Actor->GetActorLocation();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTTerrainBuilderGround), false, Actor);
	Params.AddIgnoredActors(NotGround);
	FHitResult Hit;
	// From above the actor down through everything static; the actor itself and what is not ground (NotGround) ignored.
	if (GetWorld()->LineTraceSingleByObjectType(Hit, Location + FVector(0.f, 0.f, 50000.f), Location - FVector(0.f, 0.f, 50000.f), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
	{
		bOutHit = true;
		return Hit.ImpactPoint.Z;
	}
	return 0.f;
}

void AGTTerrainBuilder::CollectRegroundable(TArray<FRegroundEntry>& OutEntries) const
{
	// Leg dressing LD6 (2026-09-27): what the ground trace must pass through. A dressed leg has PCG volumes over the whole
	// landscape (their brushes answer a WorldStatic object query: the first rebuild after dressing measured every actor
	// against a volume's top face, 140 m up, and sank them all 140 m) and solid trees with trunk capsules; the volumes,
	// the dressing exclusion and the GTBiome.* / OWBiome.* dressing are not ground.
	TArray<AActor*> NotGround;
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		bool bDressing = It->IsA<AVolume>();
		for (const FName& Tag : It->Tags)
		{
			const FString Name = Tag.ToString();
			bDressing |= Name.StartsWith(TEXT("GTBiome.")) || Name.StartsWith(TEXT("OWBiome.")) || Name == TEXT("OWDressing.Exclude");
		}
		if (bDressing)
		{
			NotGround.Add(*It);
		}
	}
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (!IsRegroundable(*It))
		{
			continue;
		}
		FRegroundEntry Entry;
		Entry.Actor = *It;
		bool bHit;
		const float Ground = GroundUnder(*It, NotGround, bHit);
		Entry.AboveGroundCm = bHit ? It->GetActorLocation().Z - Ground : 0.f;
		OutEntries.Add(Entry);
	}
}

AActor* AGTTerrainBuilder::RebuildLandscape()
{
#if WITH_EDITOR
	if (!SpecAsset)
	{
		LastMessage = TEXT("no spec asset");
		UE_LOG(LogTemp, Warning, TEXT("AGTTerrainBuilder: %s"), *LastMessage);
		return nullptr;
	}
	UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("%s.%s"), *LandscapeMaterialPath, *FPaths::GetBaseFilename(LandscapeMaterialPath)));
	if (!Material)
	{
		LastMessage = FString::Printf(TEXT("no landscape material at %s (run Art/setup_m6_hide.bat once)"), *LandscapeMaterialPath);
		UE_LOG(LogTemp, Warning, TEXT("AGTTerrainBuilder: %s"), *LastMessage);
		return nullptr;
	}
	// Remember where everything stands above the old ground before that ground goes.
	TArray<FRegroundEntry> Entries;
	if (bRegroundActors)
	{
		CollectRegroundable(Entries);
	}
	int32 Removed = 0;
	for (TActorIterator<ALandscapeProxy> It(GetWorld()); It; ++It)
	{
		It->Modify();
		GetWorld()->DestroyActor(*It);
		++Removed;
	}
	AActor* Landscape = UGTVehicleSetupLibrary::BuildLegLandscape(GetWorld(), SpecAsset->Spec, Material, LayerInfoFolder, SurfaceFolder, FString::Printf(TEXT("Landscape_%s"), *SpecAsset->DisplayName.Replace(TEXT(" "), TEXT(""))));
	if (!Landscape)
	{
		LastMessage = TEXT("the landscape did not build (see the log)");
		UE_LOG(LogTemp, Error, TEXT("AGTTerrainBuilder: %s"), *LastMessage);
		return nullptr;
	}
	++Rebuilds;
	LastRegrounded = 0;
	for (const FRegroundEntry& Entry : Entries)
	{
		if (!Entry.Actor.IsValid())
		{
			continue;
		}
		const FVector Location = Entry.Actor->GetActorLocation();
		const float NewGround = GTTerrain::SampleHeightCm(SpecAsset->Spec, Location.X, Location.Y);
		Entry.Actor->Modify();
		Entry.Actor->SetActorLocation(FVector(Location.X, Location.Y, NewGround + Entry.AboveGroundCm));
		++LastRegrounded;
	}
	const int32 Dressed = RebuildDressing();
	if (ULevel* Level = GetLevel())
	{
		Level->MarkPackageDirty();
	}
	LastMessage = FString::Printf(TEXT("rebuilt %s: %d old landscape%s removed, %d actors re-grounded, %d stones and posts placed"), *SpecAsset->DisplayName, Removed, Removed == 1 ? TEXT("") : TEXT("s"), LastRegrounded, Dressed);
	UE_LOG(LogTemp, Display, TEXT("AGTTerrainBuilder: %s"), *LastMessage);
	return Landscape;
#else
	return nullptr;
#endif
}

int32 AGTTerrainBuilder::RebuildDressing()
{
	if (!SpecAsset)
	{
		LastMessage = TEXT("no spec asset");
		return 0;
	}
	if (!Dressing)
	{
		Dressing = AGTTerrainDressing::Find(GetWorld());
	}
	if (!Dressing)
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Dressing = GetWorld()->SpawnActor<AGTTerrainDressing>(AGTTerrainDressing::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, Params);
#if WITH_EDITOR
		if (Dressing)
		{
			Dressing->SetActorLabel(TEXT("TerrainDressing"));
		}
#endif
	}
	if (!Dressing)
	{
		LastMessage = TEXT("could not spawn the dressing actor");
		UE_LOG(LogTemp, Warning, TEXT("AGTTerrainBuilder: %s"), *LastMessage);
		return 0;
	}
	const int32 Count = Dressing->Rebuild(SpecAsset->Spec);
	LastMessage = Dressing->LastMessage;
	return Count;
}

int32 AGTTerrainBuilder::RegroundActors()
{
#if WITH_EDITOR
	if (!SpecAsset)
	{
		LastMessage = TEXT("no spec asset");
		return 0;
	}
	TArray<FRegroundEntry> Entries;
	CollectRegroundable(Entries);
	int32 Moved = 0;
	for (const FRegroundEntry& Entry : Entries)
	{
		if (!Entry.Actor.IsValid())
		{
			continue;
		}
		const FVector Location = Entry.Actor->GetActorLocation();
		const float NewGround = GTTerrain::SampleHeightCm(SpecAsset->Spec, Location.X, Location.Y);
		const float NewZ = NewGround + Entry.AboveGroundCm;
		if (FMath::Abs(NewZ - Location.Z) > 0.5f)
		{
			Entry.Actor->Modify();
			Entry.Actor->SetActorLocation(FVector(Location.X, Location.Y, NewZ));
			++Moved;
		}
	}
	LastRegrounded = Moved;
	const int32 Dressed = RebuildDressing();
	if (ULevel* Level = GetLevel())
	{
		Level->MarkPackageDirty();
	}
	LastMessage = FString::Printf(TEXT("re-grounded %d of %d actors, %d stones and posts placed"), Moved, Entries.Num(), Dressed);
	UE_LOG(LogTemp, Display, TEXT("AGTTerrainBuilder: %s"), *LastMessage);
	return Moved;
#else
	return 0;
#endif
}

void AGTTerrainBuilder::ShowRoute()
{
	if (!SpecAsset)
	{
		return;
	}
	const FGTTerrainSpec& Spec = SpecAsset->Spec;
	const float Seconds = 60.f;
	const FGTRouteProfile Profile = GTTerrain::BuildRouteProfile(Spec);
	auto LayerColour = [](int32 Layer)
	{
		switch (Layer)
		{
		case 0: return FColor(90, 90, 95);
		case 2: return FColor(110, 70, 40);
		case 3: return FColor::White;
		case 4: return FColor(120, 120, 70);
		default: return FColor(210, 160, 90);
		}
	};
	// The route every 10 m, coloured by its span, 1 m above the generated ground.
	for (float Arc = 0.f; Arc < Profile.LengthM; Arc += 10.f)
	{
		float Yaw;
		const FVector A = UGTVehicleSetupLibrary::TerrainRoutePointCm(Spec, Arc, Yaw) + FVector(0.f, 0.f, 100.f);
		const FVector B = UGTVehicleSetupLibrary::TerrainRoutePointCm(Spec, Arc + 10.f, Yaw) + FVector(0.f, 0.f, 100.f);
		int32 Layer = 1;
		for (const FGTSurfaceSpan& Span : Spec.Spans)
		{
			if (Arc >= Span.StartM && Arc <= Span.EndM)
			{
				Layer = Span.Layer;
			}
		}
		DrawDebugLine(GetWorld(), A, B, LayerColour(Layer), false, Seconds, 0, 60.f);
	}
	for (const FVector2D& Point : Spec.RouteM)
	{
		const FVector P(Point.X * 100.f, Point.Y * 100.f, GTTerrain::SampleHeightCm(Spec, Point.X * 100.f, Point.Y * 100.f) + 100.f);
		DrawDebugSphere(GetWorld(), P, 300.f, 12, FColor::White, false, Seconds, 0, 20.f);
	}
	// Landforms: hills and ridges green, bowls and channels red, at their radius.
	for (const FGTTerrainFeature& Feature : Spec.Features)
	{
		const bool bUp = Feature.Kind == EGTTerrainFeatureKind::Hill || Feature.Kind == EGTTerrainFeatureKind::Ridge;
		const FColor Colour = bUp ? FColor::Green : FColor::Red;
		const float Radius = Feature.RadiusM * 100.f;
		if (Feature.Kind == EGTTerrainFeatureKind::Hill || Feature.Kind == EGTTerrainFeatureKind::Bowl)
		{
			const FVector C(Feature.StartM.X * 100.f, Feature.StartM.Y * 100.f, GTTerrain::SampleHeightCm(Spec, Feature.StartM.X * 100.f, Feature.StartM.Y * 100.f) + 200.f);
			DrawDebugCircle(GetWorld(), C, Radius, 32, Colour, false, Seconds, 0, 40.f, FVector(1.f, 0.f, 0.f), FVector(0.f, 1.f, 0.f), false);
		}
		else
		{
			const FVector A(Feature.StartM.X * 100.f, Feature.StartM.Y * 100.f, GTTerrain::SampleHeightCm(Spec, Feature.StartM.X * 100.f, Feature.StartM.Y * 100.f) + 200.f);
			const FVector B(Feature.EndM.X * 100.f, Feature.EndM.Y * 100.f, GTTerrain::SampleHeightCm(Spec, Feature.EndM.X * 100.f, Feature.EndM.Y * 100.f) + 200.f);
			DrawDebugLine(GetWorld(), A, B, Colour, false, Seconds, 0, 80.f);
			DrawDebugCircle(GetWorld(), A, Radius, 24, Colour, false, Seconds, 0, 20.f, FVector(1.f, 0.f, 0.f), FVector(0.f, 1.f, 0.f), false);
			DrawDebugCircle(GetWorld(), B, Radius, 24, Colour, false, Seconds, 0, 20.f, FVector(1.f, 0.f, 0.f), FVector(0.f, 1.f, 0.f), false);
		}
	}
	LastMessage = FString::Printf(TEXT("route %.0f m, %d points, %d spans, %d landforms drawn for %.0f s"), Profile.LengthM, Spec.RouteM.Num(), Spec.Spans.Num(), Spec.Features.Num(), Seconds);
	UE_LOG(LogTemp, Display, TEXT("AGTTerrainBuilder: %s"), *LastMessage);
}
