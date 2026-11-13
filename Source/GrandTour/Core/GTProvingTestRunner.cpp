#include "Core/GTProvingTestRunner.h"

#include "Core/GTPlayerController.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTProvingGround.h"
#include "Terrain/GTSurfacePhysMaterial.h"
#include "Terrain/GTTerrainDressing.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTVehicleSetupLibrary.h"
#include "Vehicle/GTWinchAnchor.h"

#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "LandscapeProxy.h"
#include "PhysicalMaterials/PhysicalMaterial.h"

namespace
{
	constexpr float RestCmS = 50.f;        // "at rest": under 0.5 m/s
	constexpr float SettleS = 2.f;         // after a GTGoto
	constexpr float SpawnSettleS = 3.f;    // after the car is found
	constexpr float GradeToleranceP = 3.f;
	constexpr float SlopeToleranceDeg = 2.f;
	constexpr float DeepFordM = 1.f;       // a ford this deep gets its four winch posts (setup_m6_proving.py)
	constexpr float StillWaterCmPerS = 20.f;   // RIVERBED S3: a still pond's mean current along the flow axis, cm/s (proposed; the Hide's current reads 144 at its crossing in the water test)

	FVector2D Heading(float YawDegrees)
	{
		const float Yaw = FMath::DegreesToRadians(YawDegrees);
		return FVector2D(FMath::Cos(Yaw), FMath::Sin(Yaw));
	}
}

FGTProvingTestRunner::FGTProvingTestRunner(UWorld* InWorld)
	: World(InWorld)
{
}

void FGTProvingTestRunner::Log(const FString& Line) const
{
	UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST proving t=%.1f step %d: %s"), Elapsed, Step, *Line);
}

bool FGTProvingTestRunner::CarAtRest(float& OutSpeedCmS, float& OutUpZ, float& OutAboveGroundCm) const
{
	const AGTCarPawn* TheCar = Car.Get();
	OutSpeedCmS = TheCar->GetMesh()->GetPhysicsLinearVelocity().Size();
	OutUpZ = TheCar->GetActorUpVector().Z;
	const FVector Where = TheCar->GetActorLocation();
	float GroundCm = 0.f;
	OutAboveGroundCm = GTProving::GroundZ(World.Get(), Where.X, Where.Y, GroundCm, TheCar) ? Where.Z - GroundCm : 1e6f;
	return OutSpeedCmS < RestCmS && OutUpZ > 0.9f && OutAboveGroundCm > -50.f && OutAboveGroundCm < 150.f;
}

bool FGTProvingTestRunner::CheckMap()
{
	UWorld* W = World.Get();
	const UGTTerrainSpecAsset* Asset = GTProving::FindSpecAsset(W);
	if (!Asset)
	{
		Failures.Add(TEXT("no terrain builder with a spec asset (run Art/setup_m6_proving.bat)"));
		return false;
	}
	const FGTTerrainSpec& Spec = Asset->Spec;
	int32 Landscapes = 0;
	for (TActorIterator<ALandscapeProxy> It(W); It; ++It)
	{
		++Landscapes;
	}
	int32 Fords = 0, DeepFords = 0, Muds = 0;
	for (const FGTRouteSection& Section : Spec.Sections)
	{
		Fords += Section.Kind == EGTRouteSectionKind::Ford ? 1 : 0;
		DeepFords += (Section.Kind == EGTRouteSectionKind::Ford && Section.DepthM >= DeepFordM) ? 1 : 0;
		Muds += Section.Kind == EGTRouteSectionKind::Mud ? 1 : 0;
	}
	int32 Sheets = 0;
	for (TActorIterator<AGTWaterSheet> It(W); It; ++It)
	{
		++Sheets;
	}
	const UGTMudSubsystem* Mud = W->GetSubsystem<UGTMudSubsystem>();
	const int32 Patches = Mud ? Mud->GetPatches().Num() : -1;
	int32 Anchors = 0;
	for (TActorIterator<AGTWinchAnchor> It(W); It; ++It)
	{
		++Anchors;
	}
	TArray<FGTTerrainStone> Rocks, Stones;
	TArray<FGTTerrainPost> Posts;
	GTTerrain::FordRocks(Spec, Rocks);
	GTTerrain::TrackStones(Spec, Stones);
	GTTerrain::RallyPosts(Spec, Posts);
	const AGTTerrainDressing* Dressing = AGTTerrainDressing::Find(W);
	int32 Bars = 0;
	for (const FGTRouteSection& Section : Spec.Sections)
	{
		TArray<float> Arcs;
		GTTerrain::WaterBarArcs(Spec, Section, Arcs);
		Bars += Arcs.Num();
	}
	const int32 ExpectedAnchors = 4 * Muds + 4 * DeepFords;
	// RIVERBED S4 (VEHICLE_BUILD_SYSTEM 54): a patch per bog and per section with a deformation profile (every ford's bed by default).
	const int32 ExpectedPatches = GTTerrain::DeformPatchCount(Spec);
	Log(FString::Printf(TEXT("map: spec %s | landscape %d, %dx%d components of %.0f m = %.0f m square, route %.0f m, %d stations | water sheets %d/%d fords | mud patches %d/%d bogs | "
		"ford rocks %d/%d | track stones %d/%d | rally posts %d/%d | water bars %d | winch posts %d/%d (4 per bog, 4 per ford of %.1f m or more) | mud patches with the fords' beds %d/%d"),
		*Asset->Describe(), Landscapes, Spec.ComponentsPerSide, Spec.ComponentsPerSide, Spec.SubsectionsPerComponent * Spec.QuadsPerSubsection * Spec.QuadSizeCm / 100.f,
		Spec.ComponentsPerSide * Spec.SubsectionsPerComponent * Spec.QuadsPerSubsection * Spec.QuadSizeCm / 100.f, GTTerrain::PolylineLengthM(Spec.RouteM), Spec.Stations.Num(),
		Sheets, Fords, Patches, Muds, Dressing ? Dressing->FordRockCount : -1, Rocks.Num(), Dressing ? Dressing->StoneCount : -1, Stones.Num(),
		Dressing ? Dressing->PostCount : -1, Posts.Num(), Bars, Anchors, ExpectedAnchors, DeepFordM, Patches, ExpectedPatches));
	const int32 Before = Failures.Num();
	if (Landscapes < 1) { Failures.Add(TEXT("no landscape")); }
	if (Spec.Stations.Num() == 0) { Failures.Add(TEXT("the spec has no stations")); }
	if (Sheets != Fords) { Failures.Add(FString::Printf(TEXT("water sheets %d of %d"), Sheets, Fords)); }
	if (Patches != ExpectedPatches) { Failures.Add(FString::Printf(TEXT("mud patches %d of %d (%d bogs + the profiled beds)"), Patches, ExpectedPatches, Muds)); }
	if (!Dressing) { Failures.Add(TEXT("no dressing")); }
	else
	{
		if (Dressing->FordRockCount != Rocks.Num()) { Failures.Add(FString::Printf(TEXT("ford rocks %d of %d"), Dressing->FordRockCount, Rocks.Num())); }
		if (Dressing->StoneCount != Stones.Num()) { Failures.Add(FString::Printf(TEXT("track stones %d of %d"), Dressing->StoneCount, Stones.Num())); }
		if (Dressing->PostCount != Posts.Num()) { Failures.Add(FString::Printf(TEXT("rally posts %d of %d"), Dressing->PostCount, Posts.Num())); }
	}
	if (Anchors != ExpectedAnchors) { Failures.Add(FString::Printf(TEXT("winch posts %d of %d"), Anchors, ExpectedAnchors)); }
	Readings.Add(FString::Printf(TEXT("sheets %d patches %d rocks %d stones %d rallyposts %d winchposts %d"), Sheets, Patches, Dressing ? Dressing->FordRockCount : -1,
		Dressing ? Dressing->StoneCount : -1, Dressing ? Dressing->PostCount : -1, Anchors));
	return Failures.Num() == Before;
}

bool FGTProvingTestRunner::CheckStation(int32 Index)
{
	UWorld* W = World.Get();
	const UGTTerrainSpecAsset* Asset = GTProving::FindSpecAsset(W);
	const FGTTerrainSpec& Spec = Asset->Spec;
	const FGTTerrainStation& S = Spec.Stations[Index];
	const FString Name = S.Name.ToString();
	float Speed = 0.f, UpZ = 0.f, Above = 0.f;
	const bool bRest = CarAtRest(Speed, UpZ, Above);
	const FVector CarAt = Car->GetActorLocation();
	const FVector2D Land(S.PointM.X * 100.f, S.PointM.Y * 100.f);
	const float Drift = FVector2D::Distance(FVector2D(CarAt.X, CarAt.Y), Land);
	const FVector2D Fwd = Heading(S.YawDegrees);
	auto GroundAt = [W, this](const FVector2D& XY, float& OutZ) { return GTProving::GroundZ(W, XY.X, XY.Y, OutZ, Car.Get()); };
	FString Feature;
	bool bFeature = true;
	if (S.GradePercent > 0.f)
	{
		// A ramp: its grade from 3 m past the foot to 22 m up it (clear of the top's rounding).
		float ZA = 0.f, ZB = 0.f;
		const bool bHit = GroundAt(Land + Fwd * (S.StartAheadM + 3.f) * 100.f, ZA) && GroundAt(Land + Fwd * (S.StartAheadM + 22.f) * 100.f, ZB);
		const float Grade = (ZB - ZA) / 1900.f * 100.f;
		bFeature = bHit && FMath::Abs(Grade - S.GradePercent) <= GradeToleranceP;
		Feature = FString::Printf(TEXT("grade ahead %.1f %% asked %.0f %% (+-%.0f)"), Grade, S.GradePercent, GradeToleranceP);
	}
	else if (S.CrossSlopeDegrees > 0.f)
	{
		// The slope: across it 3 m either side of its line, halfway along.
		const FVector2D Mid = Land + Fwd * (S.StartAheadM + 20.f) * 100.f;
		const FVector2D Left(-Fwd.Y, Fwd.X);
		float ZL = 0.f, ZR = 0.f;
		const bool bHit = GroundAt(Mid + Left * 300.f, ZL) && GroundAt(Mid - Left * 300.f, ZR);
		const float Deg = FMath::RadiansToDegrees(FMath::Atan(FMath::Abs(ZL - ZR) / 600.f));
		bFeature = bHit && FMath::Abs(Deg - S.CrossSlopeDegrees) <= SlopeToleranceDeg;
		Feature = FString::Printf(TEXT("cross slope %.1f deg asked %.0f (+-%.0f)"), Deg, S.CrossSlopeDegrees, SlopeToleranceDeg);
	}
	else if (S.StartAheadM <= 0.f)
	{
		// The pad: the car stands on it, on tarmac.
		FCollisionQueryParams Params(SCENE_QUERY_STAT(GTProvingPad), true);
		Params.AddIgnoredActor(Car.Get());
		Params.bReturnPhysicalMaterial = true;
		FHitResult Hit;
		FString Surface = TEXT("none");
		if (W->LineTraceSingleByObjectType(Hit, CarAt + FVector(0.f, 0.f, 200.f), CarAt - FVector(0.f, 0.f, 500.f), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
		{
			if (const UGTSurfacePhysMaterial* Phys = Cast<UGTSurfacePhysMaterial>(Hit.PhysMaterial.Get()))
			{
				Surface = Phys->SurfaceTag.GetTagName().ToString();
			}
			else if (Hit.PhysMaterial.IsValid())
			{
				Surface = Hit.PhysMaterial->GetName();
			}
		}
		float Inside = 0.f;
		for (const FGTTerrainPlane& Plane : Spec.Planes)
		{
			float H = 0.f;
			if (Plane.Layer == 0)
			{
				Inside = FMath::Max(Inside, GTTerrain::PlanePresence(Plane, CarAt.X / 100.f, CarAt.Y / 100.f, H));
			}
		}
		bFeature = Inside >= 1.f && Surface.Contains(TEXT("Tarmac"));
		Feature = FString::Printf(TEXT("on the pad %s, surface %s"), Inside >= 1.f ? TEXT("yes") : TEXT("no"), *Surface);
	}
	else if (S.ArcM >= 0.f)
	{
		const float StartArc = S.ArcM + S.StartAheadM;
		const FGTRouteSection* Section = GTTerrain::SectionAt(Spec, StartArc + 1.f);
		const EGTRouteSectionKind Kind = Section ? Section->Kind : EGTRouteSectionKind::Road;
		auto RouteXY = [&Spec](float Arc)
		{
			float Yaw = 0.f;
			const FVector2D P = GTTerrain::PointOnPolyline(Spec.RouteM, Arc, Yaw);
			return FVector2D(P.X * 100.f, P.Y * 100.f);
		};
		if (Kind == EGTRouteSectionKind::Ford)
		{
			// The water along the route ahead: the depth 5 m ahead and the first wet metre within 30 m.
			const UGTWaterSubsystem* Water = W->GetSubsystem<UGTWaterSubsystem>();
			float At5 = -1.f, FirstWet = -1.f, Deepest = 0.f;
			// RIVERBED S3 (VEHICLE_BUILD_SYSTEM 53), the owner's decision 2026-09-22: the Proving Ground's ponds stand
			// still. The current along the sheet's flow axis, averaged over the wet metres ahead (the wind's ripple has
			// no mean), and the fastest point; before S3 the crossing ran at about 1.4 m/s.
			double AlongSum = 0.0;
			float Fastest = 0.f;
			int32 WetPoints = 0;
			const AGTWaterSheet* FordSheet = nullptr;
			for (int32 Ahead = 1; Ahead <= 30 && Water; ++Ahead)
			{
				const FVector2D XY = RouteXY(S.ArcM + Ahead);
				float Z = 0.f;
				if (!GroundAt(XY, Z))
				{
					continue;
				}
				const FGTWaterSample Here = Water->Sample(FVector(XY.X, XY.Y, Z));
				const float Depth = Here.DepthCm;
				At5 = Ahead == 5 ? Depth : At5;
				Deepest = FMath::Max(Deepest, Depth);
				if (FirstWet < 0.f && Depth > 0.f)
				{
					FirstWet = Ahead;
				}
				if (Depth > 5.f)
				{
					FordSheet = FordSheet ? FordSheet : Water->SheetAt(XY);
					const FVector2D Axis = FordSheet && !FordSheet->FlowDirection.IsNearlyZero() ? FordSheet->FlowDirection.GetSafeNormal() : FVector2D(1.0, 0.0);
					AlongSum += FVector2D::DotProduct(Here.FlowCmPerS, Axis);
					Fastest = FMath::Max(Fastest, static_cast<float>(Here.FlowCmPerS.Size()));
					++WetPoints;
				}
			}
			const float MeanAlong = WetPoints > 0 ? static_cast<float>(AlongSum / WetPoints) : 0.f;
			const bool bStill = WetPoints > 0 && FMath::Abs(MeanAlong) < StillWaterCmPerS;
			bFeature = FirstWet > 0.f && bStill;
			Feature = FString::Printf(TEXT("water depth 5 m ahead %.1f cm, first wet %.0f m ahead, deepest %.1f cm within 30 m (asked %.1f m); still water: the current along the flow axis %.1f cm/s mean over %d wet points (asked under %.0f), the fastest point %.1f cm/s, the sheet's head drop %.1f cm -> %s"),
				At5, FirstWet, Deepest, Section->DepthM, MeanAlong, WetPoints, StillWaterCmPerS, Fastest, FordSheet ? FordSheet->HeadDropCm : -1.f, bStill ? TEXT("still") : TEXT("NOT still"));
		}
		else if (Kind == EGTRouteSectionKind::Mud)
		{
			const UGTMudSubsystem* Mud = W->GetSubsystem<UGTMudSubsystem>();
			const FVector2D XY = RouteXY(StartArc + 2.f);
			bFeature = Mud && Mud->PatchAt(XY) != nullptr;
			Feature = FString::Printf(TEXT("mud patch 2 m past the start: %s"), bFeature ? TEXT("yes") : TEXT("no"));
		}
		else
		{
			const FGTRouteHit Hit = GTTerrain::RouteAtCm(Spec, CarAt.X, CarAt.Y);
			const float Half = GTTerrain::HalfWidthAt(Spec, Hit.ArcM);
			bFeature = Section != nullptr && Hit.DistanceM <= Half;
			Feature = FString::Printf(TEXT("section ahead %d, the car %.1f m off the route (road half width %.1f m)"), Section ? static_cast<int32>(Kind) : -1, Hit.DistanceM, Half);
		}
	}
	const bool bOk = bRest && bFeature;
	Log(FString::Printf(TEXT("station %s (%s): landed %.1f m from its point, speed %.0f cm/s, up %.3f, %.0f cm over the ground -> %s | %s -> %s"),
		*Name, *S.Note, Drift / 100.f, Speed, UpZ, Above, bRest ? TEXT("at rest") : TEXT("NOT at rest"), *Feature, bFeature ? TEXT("ok") : TEXT("FAIL")));
	Readings.Add(FString::Printf(TEXT("%s: %s%s"), *Name, *Feature, bRest ? TEXT("") : TEXT(" (not at rest)")));
	if (!bOk)
	{
		Failures.Add(FString::Printf(TEXT("%s: %s%s"), *Name, bRest ? TEXT("") : TEXT("not at rest; "), bFeature ? TEXT("") : *Feature));
	}
	return bOk;
}

bool FGTProvingTestRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
{
	Elapsed += DeltaSeconds;
	StepTime += DeltaSeconds;
	if (!World.IsValid())
	{
		bOutPass = false;
		OutSummary = TEXT("proving: no world");
		return true;
	}
	auto Finish = [&]()
	{
		bOutPass = Failures.Num() == 0;
		OutSummary = FString::Printf(TEXT("proving: %s | %s"), bOutPass ? TEXT("all stations") : *FString::Join(Failures, TEXT("; ")), *FString::Join(Readings, TEXT(" | ")));
		return true;
	};
	if (Elapsed > 150.f)
	{
		Failures.Add(FString::Printf(TEXT("timed out at step %d"), Step));
		return Finish();
	}
	switch (Step)
	{
	case 0:
	{
		PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(World.Get(), 0));
		Car = PC.IsValid() ? (PC->GetCar() ? PC->GetCar() : Cast<AGTCarPawn>(PC->GetPawn())) : nullptr;
		if (!Car.IsValid())
		{
			if (StepTime > 10.f)
			{
				Failures.Add(TEXT("no car"));
				return Finish();
			}
			return false;
		}
		if (!CheckMap() && !GTProving::FindSpecAsset(World.Get()))
		{
			return Finish();
		}
		++Step;
		StepTime = 0.f;
		return false;
	}
	case 1:
	{
		if (StepTime < SpawnSettleS)
		{
			return false;
		}
		// The spawn: the pad station's own checks, where the car was put by the PlayerStart.
		const UGTTerrainSpecAsset* Asset = GTProving::FindSpecAsset(World.Get());
		int32 PadIndex = INDEX_NONE;
		for (int32 Index = 0; Index < Asset->Spec.Stations.Num(); ++Index)
		{
			if (Asset->Spec.Stations[Index].StartAheadM <= 0.f)
			{
				PadIndex = Index;
				break;
			}
		}
		Log(TEXT("the spawn, 3 s after the car was found:"));
		if (PadIndex == INDEX_NONE)
		{
			Failures.Add(TEXT("no pad station"));
		}
		else
		{
			CheckStation(PadIndex);
		}
		++Step;
		StepTime = 0.f;
		Station = 0;
		bGone = false;
		return false;
	}
	default:
	{
		const UGTTerrainSpecAsset* Asset = GTProving::FindSpecAsset(World.Get());
		if (Station >= Asset->Spec.Stations.Num())
		{
			return Finish();
		}
		if (!bGone)
		{
			FString Message;
			GTProving::Goto(PC.Get(), Asset->Spec.Stations[Station].Name.ToString(), Message);
			Log(Message);
			bGone = true;
			StepTime = 0.f;
			return false;
		}
		if (StepTime < SettleS)
		{
			return false;
		}
		CheckStation(Station);
		++Station;
		++Step;
		bGone = false;
		return false;
	}
	}
}
