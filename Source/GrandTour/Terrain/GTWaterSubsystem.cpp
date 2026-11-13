#include "Terrain/GTWaterSubsystem.h"

#include "Terrain/GTMudPatch.h"
#include "Terrain/GTWaterSheet.h"
#include "Weather/GTWeatherSubsystem.h"

#include "CoreGlobals.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

/**
 * Water stage W3's follow-up: 0 makes Sample skip the mud patches, so the wheels read no rut water and the driving is
 * what it was before W3. It is the comparison the bog's moved numbers need (the middle crawl's sink and the rut mean
 * went with W3, and a crawl is chaotic), and the user gets it while driving. -GTRutWater=0 on the command line sets it
 * for a headless run (read once at Initialize).
 */
static TAutoConsoleVariable<int32> CVarRutWater(
	TEXT("gt.Water.RutWater"), 1,
	TEXT("1 the mud patches' rut water is in the one water query (kind Rut), 0 the query skips them (pre-W3 physics)."));

void UGTWaterSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	int32 FromCommandLine = 1;
	if (FParse::Value(FCommandLine::Get(), TEXT("GTRutWater="), FromCommandLine))
	{
		CVarRutWater->Set(FromCommandLine != 0 ? 1 : 0, ECVF_SetByCommandline);
		UE_LOG(LogTemp, Display, TEXT("UGTWaterSubsystem: -GTRutWater=%d -> gt.Water.RutWater %d (0 = the query skips the mud patches, the pre-W3 physics)"),
			FromCommandLine, CVarRutWater.GetValueOnGameThread());
	}
}

bool UGTWaterSubsystem::IsRutWaterOn()
{
	return CVarRutWater.GetValueOnGameThread() != 0;
}

/**
 * Water stage W5: the driver's own scale on the river's two lags. At 1 a ford takes RiseLagS 180 s to reach 63 % of
 * what the rain asks of it and FallLagS 600 s to give it back, which is the point of the stage and far too slow to
 * watch; 0.2 puts a three-minute rise inside a minute. It multiplies with SetLagScaleForTest, which is the water
 * test's own hook, so the two never have to know about each other.
 */
static TAutoConsoleVariable<float> CVarRiverLagScale(
	TEXT("gt.Water.RiverLagScale"), 1.f,
	TEXT("Scales the river stage's rise and fall lags (1 the game's 180 / 600 s, 0.2 five times faster)."));

void UGTWaterSubsystem::AdvanceRiverStage(float DeltaSeconds)
{
	// One advance a frame however many sheets ask: they all stand in the same river.
	if (RiverStageFrame == GFrameCounter || DeltaSeconds <= 0.f || bRiverFrozenForTest)
	{
		return;
	}
	RiverStageFrame = GFrameCounter;
	const UWorld* OwningWorld = GetWorld();
	const UGTWeatherSubsystem* Weather = OwningWorld ? OwningWorld->GetSubsystem<UGTWeatherSubsystem>() : nullptr;
	const float Rain = Weather ? FMath::Clamp(Weather->GetRainIntensity(), 0.f, 1.f) : 0.f;
	const float TargetCm = RiverRiseCmAtFullRain * Rain;
	const float Scale = FMath::Max(0.001f, LagScaleForTest * CVarRiverLagScale.GetValueOnGameThread());
	const float LagS = FMath::Max(0.001f, (TargetCm > RiverStageCm ? RiseLagS : FallLagS) * Scale);
	// Exact for a target held constant over the frame, so the reading does not depend on the frame rate: the stage
	// covers 1 - e^-(dt/lag) of what is left between it and the target.
	RiverStageCm += (TargetCm - RiverStageCm) * (1.f - FMath::Exp(-DeltaSeconds / LagS));
}

void UGTWaterSubsystem::RegisterSheet(AGTWaterSheet* Sheet)
{
	if (Sheet)
	{
		Sheets.AddUnique(Sheet);
		MudSelectionFrame=MAX_uint64;
	}
}

void UGTWaterSubsystem::UnregisterSheet(AGTWaterSheet* Sheet)
{
	MudSelectionFrame=MAX_uint64;
	Sheets.RemoveAll([Sheet](const TWeakObjectPtr<AGTWaterSheet>& Entry) { return !Entry.IsValid() || Entry.Get() == Sheet; });
}

bool UGTWaterSubsystem::ShouldSimulateMudSheet(const AGTWaterSheet* Sheet,int32 Budget)
{
	if(MudSelectionFrame!=GFrameCounter)
	{
		MudSelectionFrame=GFrameCounter;ActiveMudSheets.Reset();
		const auto* PC=GetWorld()->GetFirstPlayerController();
		const APawn* Pawn=PC ? PC->GetPawn().Get() : nullptr;
		const int32 Limit=FMath::Clamp(Budget,0,4);
		if(Pawn && Limit>0)
		{
			const FVector Focus=Pawn->GetActorLocation();
			// Keep only the best four as we walk; O(pond count), no whole-list sort or per-pond allocation.
			for(const auto& Entry:Sheets)
			{
				auto* Candidate=Entry.Get();
				if(!Candidate || !Candidate->MudSurface) continue;
				const double Distance=FVector::DistSquared2D(Focus,Candidate->GetActorLocation());
				if(Distance>=FMath::Square(8000.+FMath::Clamp(Candidate->MudHalfSizeCm,100.f,3200.f))) continue;
				int32 Index=0;
				while(Index<ActiveMudSheets.Num())
				{
					const auto* Other=ActiveMudSheets[Index].Get();
					const double D=FVector::DistSquared2D(Focus,Other->GetActorLocation());
					if(Distance<D || (Distance==D && Candidate->GetUniqueID()<Other->GetUniqueID())) break;
					++Index;
				}
				if(Index<Limit)
				{
					ActiveMudSheets.Insert(Candidate,Index);
					if(ActiveMudSheets.Num()>Limit) ActiveMudSheets.SetNum(Limit,EAllowShrinking::No);
				}
			}
		}
	}
	return ActiveMudSheets.ContainsByPredicate([Sheet](const auto& Entry){return Entry.Get()==Sheet;});
}

void UGTWaterSubsystem::RegisterPatch(AGTMudPatch* Patch)
{
	if (Patch)
	{
		Patches.AddUnique(Patch);
	}
}

void UGTWaterSubsystem::UnregisterPatch(AGTMudPatch* Patch)
{
	Patches.RemoveAll([Patch](const TWeakObjectPtr<AGTMudPatch>& Entry) { return !Entry.IsValid() || Entry.Get() == Patch; });
}

FGTWaterSample UGTWaterSubsystem::Sample(const FVector& GroundPoint) const
{
	FGTWaterSample Result;
	Result.SurfaceZCm = static_cast<float>(GroundPoint.Z);
	const FVector2D XY(GroundPoint.X, GroundPoint.Y);
	bool bFound = false;
	for (const TWeakObjectPtr<AGTWaterSheet>& Entry : Sheets)
	{
		const AGTWaterSheet* Sheet = Entry.Get();
		if (!Sheet || !Sheet->Covers(XY))
		{
			continue;
		}
		// Water stage WS1: the surface is the sheet's simulated field at this XY (the level only where the field is
		// not built yet), so a wave lifts and drops what reads it and the current varies with the bed.
		const float SurfaceZ = Sheet->SurfaceCmAt(XY);
		const float AbovePoint = FMath::Max(0.f, SurfaceZ - static_cast<float>(GroundPoint.Z));
		// A tyre buried beneath the mud bed does not gain a second fluid column
		// inside the soil. Existing wheel drag/lift reads only water above that bed.
		const float Depth = Sheet->MudSurface ? FMath::Min(AbovePoint,Sheet->MudWaterDepthCmAt(XY)) : AbovePoint;
		// The deepest covering sheet wins; the first one covering a point above every surface still answers Ford.
		if (!bFound || Depth > Result.DepthCm)
		{
			bFound = true;
			Result.DepthCm = Depth;
			Result.SurfaceZCm = SurfaceZ;
			Result.FlowCmPerS = Sheet->FlowCmPerSAt(XY);
			Result.Kind = Sheet->MudSurface ? EGTWaterKind::Rut : EGTWaterKind::Ford;
			Result.bSimulatedMudWater = Sheet->MudSurface!=nullptr;
		}
	}
	// Water stage W3: the mud patches answer the same call. A rut cut below its bog's water table holds water - the
	// table over the mud field's own height there, lifted by the weather through WetTableLiftCm - and it stands: no
	// flow, no waves, nothing to simulate (the field solver is the fords' alone). The deeper of the two wins.
	// gt.Water.RutWater 0 skips them entirely: the pre-W3 answer, for the comparison and for driving both ways.
	if (!IsRutWaterOn())
	{
		return Result;
	}
	for (const TWeakObjectPtr<AGTMudPatch>& Entry : Patches)
	{
		const AGTMudPatch* Patch = Entry.Get();
		if (!Patch || !Patch->Contains(XY))
		{
			continue;
		}
		const float Depth = FMath::Max(0.f, Patch->WaterDepthCmAt(XY));
		if (!bFound || Depth > Result.DepthCm)
		{
			bFound = true;
			Result.DepthCm = Depth;
			Result.SurfaceZCm = static_cast<float>(GroundPoint.Z) + Depth;
			Result.FlowCmPerS = FVector2D::ZeroVector;
			Result.Kind = EGTWaterKind::Rut;
			Result.bSimulatedMudWater = false;
		}
	}
	return Result;
}

AGTWaterSheet* UGTWaterSubsystem::SheetAt(const FVector2D& WorldXY) const
{
	for (const TWeakObjectPtr<AGTWaterSheet>& Entry : Sheets)
	{
		AGTWaterSheet* Sheet = Entry.Get();
		if (Sheet && Sheet->Covers(WorldXY))
		{
			return Sheet;
		}
	}
	return nullptr;
}
