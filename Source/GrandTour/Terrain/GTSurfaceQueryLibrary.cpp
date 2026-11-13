#include "Terrain/GTSurfaceQueryLibrary.h"
#include "Terrain/GTRoadReliefTile.h"
#include "Terrain/GTLandscapeSurface.h"

#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "LandscapeProxy.h"
#include "LandscapeHeightfieldCollisionComponent.h"
#include "PhysicalMaterials/PhysicalMaterial.h"

UPhysicalMaterial* UGTSurfaceQueryLibrary::TraceLandscapeSurface(UObject* WorldContextObject, FVector Start, FVector End, FVector& OutPoint, FVector& OutNormal)
{
	OutPoint = FVector::ZeroVector;
	OutNormal = FVector::UpVector;
	UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World)
	{
		return nullptr;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTTraceLandscapeSurface), true);
	Params.bReturnPhysicalMaterial = true;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
        if (!Cast<ALandscapeProxy>(*It) && !Cast<AGTRoadReliefTile>(*It))
		{
			Params.AddIgnoredActor(*It);
		}
	}
	FHitResult Hit;
    if (!World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params) || (!Cast<ULandscapeHeightfieldCollisionComponent>(Hit.GetComponent()) && !Cast<AGTRoadReliefTile>(Hit.GetActor())))
	{
		return nullptr;
	}
	OutPoint = Hit.ImpactPoint;
	OutNormal = Hit.ImpactNormal;
	if (UPhysicalMaterial* Material = Hit.PhysMaterial.Get())
	{
		return Material;
	}
	// The editor world's queries can come back without one: the landscape's own lookup on the complex heightfield (the wheels' data).
	const ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(Hit.GetActor());
    if(const auto* Tile=Cast<AGTRoadReliefTile>(Hit.GetActor());Tile&&Tile->Surface)Proxy=Tile->Surface->Landscape;
	return Proxy ? Proxy->GetPhysicalMaterialAtLocation(Hit.ImpactPoint, EHeightfieldSource::Complex) : nullptr;
}

FString UGTSurfaceQueryLibrary::DescribeLandscapeSurfaceAt(UObject* WorldContextObject, FVector Location)
{
	FVector Point, Normal;
	const UPhysicalMaterial* Traced = TraceLandscapeSurface(WorldContextObject, FVector(Location.X, Location.Y, 1.0e6), FVector(Location.X, Location.Y, -1.0e6), Point, Normal);
	UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull) : nullptr;
	FString Out = FString::Printf(TEXT("traced=%s point=%s"), Traced ? *Traced->GetName() : TEXT("null"), *Point.ToString());
	if (!World)
	{
		return Out;
	}
	for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
	{
		const UPhysicalMaterial* Complex = It->GetPhysicalMaterialAtLocation(Point, EHeightfieldSource::Complex);
		const UPhysicalMaterial* Simple = It->GetPhysicalMaterialAtLocation(Point, EHeightfieldSource::Simple);
		Out += FString::Printf(TEXT(" complex=%s simple=%s"), Complex ? *Complex->GetName() : TEXT("null"), Simple ? *Simple->GetName() : TEXT("null"));
		for (ULandscapeHeightfieldCollisionComponent* C : It->CollisionComponents)
		{
			if (!C || !C->Bounds.GetBox().ExpandBy(FVector(0, 0, 1.0e6)).IsInsideXY(Point))
			{
				continue;
			}
			auto Names = [](const TArray<TObjectPtr<UPhysicalMaterial>>& A)
			{
				TArray<FString> N;
				for (const TObjectPtr<UPhysicalMaterial>& M : A)
				{
					N.Add(M ? M->GetName() : TEXT("null"));
				}
				return FString::Join(N, TEXT("|"));
			};
#if WITH_EDITORONLY_DATA
			Out += FString::Printf(TEXT(" comp=%s renderObjects=[%s] renderSamples=%lld"), *C->GetName(), *Names(C->PhysicalMaterialRenderObjects),
				static_cast<long long>(C->PhysicalMaterialRenderData.GetElementCount()));
#endif
			Out += FString::Printf(TEXT(" cooked=[%s] layers=%d"), *Names(C->CookedPhysicalMaterials), C->ComponentLayerInfos.Num());
			break;
		}
	}
	return Out;
}
