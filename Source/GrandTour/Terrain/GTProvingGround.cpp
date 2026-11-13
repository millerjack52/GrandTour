#include "Terrain/GTProvingGround.h"

#include "Character/GTPlayerCharacter.h"
#include "Core/GTGameplayTags.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTSurfacePhysMaterial.h"
#include "LandscapeProxy.h"
#include "HAL/PlatformTime.h"
#include "Core/GTPlayerController.h"
#include "Terrain/GTTerrainBuilder.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Vehicle/GTCarPawn.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"

const UGTTerrainSpecAsset* GTProving::FindSpecAsset(UWorld* World)
{
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AGTTerrainBuilder> It(World); It; ++It)
	{
		if (It->SpecAsset)
		{
			return It->SpecAsset;
		}
	}
	return nullptr;
}

FString GTProving::StationNames(const FGTTerrainSpec& Spec)
{
	TArray<FString> Names;
	for (const FGTTerrainStation& Station : Spec.Stations)
	{
		Names.Add(Station.Name.ToString());
	}
	return FString::Join(Names, TEXT(" "));
}

bool GTProving::GroundZ(UWorld* World, float XCm, float YCm, float& OutZ, const AActor* Ignore)
{
	if (!World)
	{
		return false;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTProvingGround), true);
	if (Ignore)
	{
		Params.AddIgnoredActor(Ignore);
	}
	FHitResult Hit;
	if (!World->LineTraceSingleByObjectType(Hit, FVector(XCm, YCm, 50000.f), FVector(XCm, YCm, -50000.f), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
	{
		return false;
	}
	OutZ = Hit.ImpactPoint.Z;
	return true;
}

GTProving::FGTMudSurvey GTProving::SurveyMud(UWorld* World, const FGTTerrainSpec& Spec, float StepCm, const AActor* Ignore)
{
	FGTMudSurvey Survey;
	Survey.StepCm = FMath::Max(1.f, StepCm);
	if (!World)
	{
		return Survey;
	}
	const UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	Survey.Patches = Mud ? Mud->GetPatches().Num() : 0;
	const double Start = FPlatformTime::Seconds();
	const float SizeCm = (GTTerrain::VertsPerSide(Spec) - 1) * Spec.QuadSizeCm;
	const int32 Count = FMath::FloorToInt(SizeCm / Survey.StepCm) + 1;
	// The regions the soft samples outside the boxes are put down to (the first that holds one): the channels, whose
	// bottoms the generator painted Mud (section 49's rule), and a 10 m fringe round each box.
	struct FRegion
	{
		FVector2D A;
		FVector2D B;
		float RadiusCm;
	};
	TArray<FRegion> Regions;
	for (const FGTTerrainFeature& Feature : Spec.Features)
	{
		if (Feature.Kind == EGTTerrainFeatureKind::Channel)
		{
			Regions.Add({ Feature.StartM * 100.f, Feature.EndM * 100.f, (Feature.RadiusM + 5.f) * 100.f });
			Survey.RegionNames.Add(FString::Printf(TEXT("channel (%.0f, %.0f)-(%.0f, %.0f) m"), Feature.StartM.X, Feature.StartM.Y, Feature.EndM.X, Feature.EndM.Y));
		}
	}
	TArray<FBox2D> Boxes;
	GTTerrain::MudPatchBoxesCm(Spec, Boxes);
	for (const FBox2D& Box : Boxes)
	{
		Regions.Add({ Box.GetCenter(), Box.GetCenter(), static_cast<float>(Box.GetExtent().Size()) + 1000.f });
		Survey.RegionNames.Add(FString::Printf(TEXT("a Mud section's box + 10 m (%.0f, %.0f) m"), Box.GetCenter().X / 100.0, Box.GetCenter().Y / 100.0));
	}
	Survey.RegionCounts.SetNumZeroed(Regions.Num());
	auto RegionOf = [&Regions](const FVector2D& P) -> int32
	{
		for (int32 Index = 0; Index < Regions.Num(); ++Index)
		{
			const FVector2D AB = Regions[Index].B - Regions[Index].A;
			const double Length2 = AB.SizeSquared();
			const double T = Length2 > 1.0 ? FMath::Clamp(FVector2D::DotProduct(P - Regions[Index].A, AB) / Length2, 0.0, 1.0) : 0.0;
			if (FVector2D::Distance(P, Regions[Index].A + AB * T) <= Regions[Index].RadiusCm)
			{
				return Index;
			}
		}
		return INDEX_NONE;
	};
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTMudSurvey), false);
	Params.bReturnPhysicalMaterial = true;
	if (Ignore)
	{
		Params.AddIgnoredActor(Ignore);
	}
	for (int32 J = 0; J < Count; ++J)
	{
		for (int32 I = 0; I < Count; ++I)
		{
			const float X = Spec.OriginXCm + I * Survey.StepCm;
			const float Y = Spec.OriginYCm + J * Survey.StepCm;
			++Survey.Samples;
			FHitResult Hit;
			bool bLandscape = false;
			for (int32 Try = 0; Try < 4; ++Try)
			{
				if (!World->LineTraceSingleByObjectType(Hit, FVector(X, Y, 50000.f), FVector(X, Y, -50000.f), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
				{
					break;
				}
				AActor* Actor = Hit.GetActor();
				if (!Actor)
				{
					break;
				}
				if (Actor->IsA<ALandscapeProxy>())
				{
					bLandscape = true;
					break;
				}
				Params.AddIgnoredActor(Actor);   // the ground under it is what is counted
			}
			if (!bLandscape)
			{
				continue;
			}
			++Survey.Landscape;
			const UGTSurfacePhysMaterial* Surface = Cast<UGTSurfacePhysMaterial>(Hit.PhysMaterial.Get());
			const bool bMud = Surface && Surface->SurfaceTag == GTTags::Surface_Mud.GetTag();
			const bool bBog = Surface && Surface->SurfaceTag == GTTags::Surface_Bog.GetTag();
			const bool bInBox = Mud && Mud->PatchAt(FVector2D(X, Y)) != nullptr;
			if (bInBox)
			{
				++Survey.InBoxes;
				Survey.MudInside += bMud ? 1 : 0;
				Survey.BogInside += bBog ? 1 : 0;
			}
			else if (bMud || bBog)
			{
				Survey.MudOutside += bMud ? 1 : 0;
				Survey.BogOutside += bBog ? 1 : 0;
				Survey.OutsideCm += FVector2D(X, Y);
				const int32 Region = RegionOf(FVector2D(X, Y));
				if (Region == INDEX_NONE)
				{
					++Survey.Elsewhere;
				}
				else
				{
					++Survey.RegionCounts[Region];
				}
			}
		}
	}
	Survey.Seconds = static_cast<float>(FPlatformTime::Seconds() - Start);
	return Survey;
}

FString GTProving::DescribeMudSurvey(const FGTMudSurvey& Survey)
{
	const FString Extent = Survey.OutsideCm.bIsValid
		? FString::Printf(TEXT(" over x %.0f..%.0f y %.0f..%.0f cm"), Survey.OutsideCm.Min.X, Survey.OutsideCm.Max.X, Survey.OutsideCm.Min.Y, Survey.OutsideCm.Max.Y)
		: FString();
	FString Where;
	for (int32 Index = 0; Index < Survey.RegionNames.Num() && Index < Survey.RegionCounts.Num(); ++Index)
	{
		Where += FString::Printf(TEXT("%s%s %d"), Where.IsEmpty() ? TEXT("") : TEXT(", "), *Survey.RegionNames[Index], Survey.RegionCounts[Index]);
	}
	Where += FString::Printf(TEXT("%selsewhere %d"), Where.IsEmpty() ? TEXT("") : TEXT(", "), Survey.Elsewhere);
	return FString::Printf(TEXT("mud survey every %.0f cm: %d samples, %d on the landscape, %d inside %d patch box(es) (Mud %d, Bog %d there); outside every box Mud %d, Bog %d%s (by where: %s); %.1f s"),
		Survey.StepCm, Survey.Samples, Survey.Landscape, Survey.InBoxes, Survey.Patches, Survey.MudInside, Survey.BogInside, Survey.MudOutside, Survey.BogOutside, *Extent, *Where, Survey.Seconds);
}

bool GTProving::Goto(AGTPlayerController* PC, const FString& Name, FString& OutMessage)
{
	UWorld* World = PC ? PC->GetWorld() : nullptr;
	const UGTTerrainSpecAsset* Asset = FindSpecAsset(World);
	if (!Asset || Asset->Spec.Stations.Num() == 0)
	{
		OutMessage = TEXT("GTGoto: this map has no stations (L_Proving has them)");
		return false;
	}
	const FGTTerrainSpec& Spec = Asset->Spec;
	if (Name.IsEmpty() || Name.Equals(TEXT("list"), ESearchCase::IgnoreCase))
	{
		OutMessage = FString::Printf(TEXT("GTGoto stations: %s"), *StationNames(Spec));
		return true;
	}
	const FGTTerrainStation* Station = GTTerrain::FindStation(Spec, Name);
	if (!Station)
	{
		OutMessage = FString::Printf(TEXT("GTGoto: no station '%s' (stations: %s)"), *Name, *StationNames(Spec));
		return false;
	}
	AGTCarPawn* Car = PC->GetCar() ? PC->GetCar() : Cast<AGTCarPawn>(PC->GetPawn());
	if (!Car)
	{
		OutMessage = TEXT("GTGoto: no car");
		return false;
	}
	const float XCm = Station->PointM.X * 100.f;
	const float YCm = Station->PointM.Y * 100.f;
	float GroundCm = 0.f;
	if (!GroundZ(World, XCm, YCm, GroundCm, Car))
	{
		GroundCm = GTTerrain::SampleHeightCm(Spec, XCm, YCm);
	}
	// 120 cm over the ground, as the terrain test drops the car: it falls onto its wheels and settles.
	const FVector Location(XCm, YCm, GroundCm + 120.f);
	const bool bDriving = PC->IsDriving();
	Car->SetActorLocationAndRotation(Location, FRotator(0.f, Station->YawDegrees, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	Car->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
	Car->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
	Car->ResetDrivingInputs();
	if (UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement())
	{
		Move->SetThrottleInput(0.f);
		Move->SetBrakeInput(0.f);
		Move->SetHandbrakeInput(true);
	}
	if (!bDriving)
	{
		if (AGTPlayerCharacter* Character = PC->GetPlayerCharacter())
		{
			const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
			const FVector Beside = Car->FindExitLocation(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight());
			Character->SetActorLocationAndRotation(Beside + FVector(0.f, 0.f, 30.f), FRotator(0.f, Station->YawDegrees, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
	OutMessage = FString::Printf(TEXT("GTGoto %s: %s; the car at (%.0f, %.0f, %.0f) yaw %.0f, %.0f m before the station%s"),
		*Station->Name.ToString(), *Station->Note, Location.X, Location.Y, Location.Z, Station->YawDegrees, Station->StartAheadM,
		bDriving ? TEXT("") : TEXT(", you beside it"));
	return true;
}

void GTProving::ShowHelp(UWorld* World, float Seconds)
{
	const UGTTerrainSpecAsset* Asset = FindSpecAsset(World);
	if (!Asset || Asset->Spec.Stations.Num() == 0)
	{
		return;
	}
	const TArray<FString> Lines = {
		FString::Printf(TEXT("%s: GTGoto <station> in the console (~). GTGoto list"), *Asset->DisplayName),
		FString::Printf(TEXT("Stations: %s"), *StationNames(Asset->Spec)),
		TEXT("Water: gt.Water.ExtraRiseCm <cm>  gt.Water.FlowScale <x>  gt.Water.Wind <x>  gt.Water.RutWater 0/1"),
		TEXT("       gt.Water.RiverLagScale <x>  gt.Water.Stats 0/1   Weather: gt.Weather.Rain <0..1, -1 off>"),
	};
	for (const FString& Line : Lines)
	{
		UE_LOG(LogTemp, Display, TEXT("GTProving %s"), *Line);
	}
	if (GEngine)
	{
		// On-screen messages stack newest on top, so the first line goes in last.
		for (int32 Index = Lines.Num() - 1; Index >= 0; --Index)
		{
			GEngine->AddOnScreenDebugMessage(-1, Seconds, FColor(255, 220, 120), Lines[Index]);
		}
	}
}
