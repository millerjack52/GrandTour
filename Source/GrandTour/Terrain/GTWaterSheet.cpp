#include "Terrain/GTWaterSheet.h"
#include "Core/GTPerfProbe.h"

#include "Terrain/GTWaterSubsystem.h"
#include "Terrain/GTRiverReference.h"
#include "Terrain/GTWaterDomain.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Weather/GTWeatherSubsystem.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "CollisionQueryParams.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "LandscapeProxy.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "ProceduralMeshComponent.h"
#include "RHI.h"
#include "UObject/ConstructorHelpers.h"

/** Water stage W1: 0 makes every ford still water again, for the comparison the drive gate asks for. WS1: it scales the field's head drop. */
static TAutoConsoleVariable<float> CVarWaterFlowScale(
	TEXT("gt.Water.FlowScale"), 1.f,
	TEXT("Multiplies every water sheet's head drop (1 the section's own current, 0 still water)."));

/** Water stage W1: the driver raises the ford in play to reach the deep state the test uses. */
static TAutoConsoleVariable<float> CVarWaterExtraRiseCm(
	TEXT("gt.Water.ExtraRiseCm"), 0.f,
	TEXT("Extra rise on every water sheet, cm, on top of the actor's own ExtraRiseCm."));

/** Water stage WS2: the wind that stirs still water (0 takes it off, which is what the still picture pair needs). */
static TAutoConsoleVariable<float> CVarWaterWind(
	TEXT("gt.Water.Wind"), 1.f,
	TEXT("Scales the wind's ripple on every water field (1 the sheet's own WindRippleCm, 0 no wind at all)."));

/** Water stage WS2: the car as a lid on the water (0 leaves the surface to the current, the wind and the rain). */
static TAutoConsoleVariable<int32> CVarWaterLids(
	TEXT("gt.Water.Lids"), 1,
	TEXT("1 the car's hull and wheels displace the water field (bow wave, wake), 0 they do not."));

/** Water stage R1: the same GTWATERSTATS line the log carries, drawn on screen so the user can see the water's cost while driving. */
static TAutoConsoleVariable<int32> CVarWaterStats(
	TEXT("gt.Water.Stats"), 0,
	TEXT("1 draws each water sheet's frame ms, step ms, sub-steps and clamp count on screen, 0 does not."));

namespace
{
	/** R1: how high over the water level the bed trace starts, and how far under the level a cell is still worth tracing, cm. */
	constexpr float GTBedTraceOverLevelCm = 500.f;
	constexpr float GTBedTraceBandCm = 200.f;
	/** One on-screen line per sheet: a fixed key each, handed out at BeginPlay. */
	int32 GTNextWaterStatsKey = 7710;
	/** RIVERBED S3: the basin's search square, cm a side (the plan's 200 x 200 m cap). */
	constexpr float GTBasinSearchCm = 20000.f;
}

void AGTWaterSheet::LogBasin() const
{
	FString Label = GetName();
#if WITH_EDITOR
	Label = FString::Printf(TEXT("%s (%s)"), *GetName(), *GetActorLabel());
#endif
	const FGTWaterBasin& B = Basin;
	const float Cell = B.CellCm * 0.01f;
	const int32 H = B.Half();
	if (!B.IsValid())
	{
		UE_LOG(LogTemp, Display, TEXT("GTFORDFILL %s: level %.1f cm, no bed under it inside the placed box (%d beds sampled in %.0f ms)"),
			*Label, B.LevelCm, B.SampledCells, B.FillMs);
		return;
	}
	const FVector2D Seed = B.CellCentreCm(B.SeedIndex % B.Size, B.SeedIndex / B.Size);
	const float A0 = (B.MinX - H) * Cell, A1 = (B.MaxX + 1 - H) * Cell;
	const float C0 = (B.MinY - H) * Cell, C1 = (B.MaxY + 1 - H) * Cell;
	const float BA0 = (B.BoxMinX - H) * Cell, BA1 = (B.BoxMaxX + 1 - H) * Cell;
	const float BC0 = (B.BoxMinY - H) * Cell, BC1 = (B.BoxMaxY + 1 - H) * Cell;
	const int32 BoxCells = (B.BoxMaxX - B.BoxMinX + 1) * (B.BoxMaxY - B.BoxMinY + 1);
	const int32 BoundsCells = (B.MaxX - B.MinX + 1) * (B.MaxY - B.MinY + 1);
	UE_LOG(LogTemp, Display, TEXT("GTFORDFILL %s: level %.1f cm, %.0f cm cells in a %.0f m search square, X along the flow (%.2f, %.2f), Y its left; seed (%.0f, %.0f) bed %.1f cm (the lowest in the placed box); the wet region along the flow %.2f to %.2f m (%.2f m), across %.2f to %.2f m (%.2f m) from the sheet's centre, %d cells = %.1f m2 (its bounds %d cells), reached the search edge %s; the placed box along %.2f to %.2f m (%.1f m), across %.2f to %.2f m (%.1f m), %d cells; the region past the placed box: upstream %.2f m, downstream %.2f m, left %.2f m, right %.2f m; inside the placed box %d cells under the level, %d in the region, %d in %d disconnected hollows (the deepest %.1f cm); %d beds sampled in %.0f ms"),
		*Label, B.LevelCm, B.CellCm, B.Size * Cell, B.AxisX.X, B.AxisX.Y, Seed.X, Seed.Y, B.SeedBedCm,
		A0, A1, A1 - A0, C0, C1, C1 - C0, B.Cells, B.Cells * Cell * Cell, BoundsCells, B.bHitSearchEdge ? TEXT("YES") : TEXT("no"),
		BA0, BA1, BA1 - BA0, BC0, BC1, BC1 - BC0, BoxCells,
		FMath::Max(0.f, BA0 - A0), FMath::Max(0.f, A1 - BA1), FMath::Max(0.f, C1 - BC1), FMath::Max(0.f, BC0 - C0),
		B.BoxUnderLevel, B.RegionInBox, B.HollowCells, B.Hollows, B.HollowDeepestCm, B.SampledCells, B.FillMs);
}

AGTWaterSheet::AGTWaterSheet()
{
	PrimaryActorTick.bCanEverTick = true;
	// The engine's cube (not a project asset, so it may be found from a constructor) is still the actor's root and so
	// still what the footprint's scale lives on, but since WS1 it draws nothing: the surface is the field's own mesh.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMeshComponent* Sheet = GetStaticMeshComponent();
	Sheet->SetMobility(EComponentMobility::Movable);
	if (Cube.Succeeded())
	{
		Sheet->SetStaticMesh(Cube.Object);
	}
	Sheet->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Sheet->SetCollisionProfileName(TEXT("NoCollision"));
	Sheet->SetGenerateOverlapEvents(false);
	Sheet->CastShadow = false;
	Sheet->SetVisibility(false);
	Sheet->SetHiddenInGame(true);
	SetActorEnableCollision(false);

	// WS1's surface. The root carries the footprint's scale (74 x 30 x 0.1), which would stretch a procedural grid out
	// of all recognition, so this component keeps its own absolute transform: unrotated, unit scale, its world XY at
	// the field's centre and its world Z at the water level, with the vertices laid out around it in world cm.
	SurfaceMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("SurfaceMesh"));
	SurfaceMesh->SetupAttachment(Sheet);
	SurfaceMesh->SetUsingAbsoluteLocation(true);
	SurfaceMesh->SetUsingAbsoluteRotation(true);
	SurfaceMesh->SetUsingAbsoluteScale(true);
	SurfaceMesh->SetRelativeRotation(FRotator::ZeroRotator);
	SurfaceMesh->SetRelativeScale3D(FVector::OneVector);
	SurfaceMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SurfaceMesh->SetCastShadow(false);
	SurfaceMesh->bUseAsyncCooking = false;
	SurfaceMesh->BoundsScale = 1.f;
	// After the mud patches' rut water (priority 1): a ford's sheet is the outer surface where the two meet.
	SurfaceMesh->SetTranslucentSortPriority(2);
}

void AGTWaterSheet::BeginPlay()
{
	Super::BeginPlay();
	if(WaterDomain)
	{
		// Keep the saved authoring bake intact. Seeded live mud basins replace
		// only their child domain in this play session, including newly dry cells.
		TArray<UGTWaterDomain*> Seeds;
		for(TActorIterator<AGTWaterSheet> It(GetWorld());It;++It)
			if(It->MudSurface && It->MudInitialDomain)Seeds.Add(It->MudInitialDomain);
		bool Replaced=false;
		for(const auto& P:WaterDomain->RoadPatches)Replaced|=Seeds.Contains(P.Get());
		if(Replaced)
		{
			const auto OriginalChildren=WaterDomain->RoadPatches;
			WaterDomain=DuplicateObject<UGTWaterDomain>(WaterDomain,this);
			WaterDomain->RoadPatches=OriginalChildren;
			WaterDomain->RoadPatches.RemoveAll([&](const auto& P){return Seeds.Contains(P.Get());});
		}
	}
	if (MudSurface) { PrimaryActorTick.TickGroup=TG_PostPhysics; AddTickPrerequisiteActor(MudSurface); }
	if (FMath::IsNearlyZero(BaseLevelCm))
	{
		BaseLevelCm = GetActorLocation().Z;
	}
	if (UStaticMeshComponent* Sheet = GetStaticMeshComponent())
	{
		Sheet->SetVisibility(false);
		Sheet->SetHiddenInGame(true);
	}
	if (UGTWaterSubsystem* Water = GetWorld() ? GetWorld()->GetSubsystem<UGTWaterSubsystem>() : nullptr)
	{
		Water->RegisterSheet(this);
	}
	StatsKey = GTNextWaterStatsKey++;
	UE_LOG(LogTemp, Display, TEXT("AGTWaterSheet %s: level %.0f cm, flow %.2f m/s along (%.2f, %.2f), fade %.0f m; WS1 field at %.1f cm cells, head drop %.1f cm, pipe damping %.5f, bed friction %.4f (x%.2f at the ends); WS2 sources: lids at %.1f m/s, wind %.1f cm/s in %.0f s gusts, rain %.0f drops/m2/s of %.1f cm, sponge tau %.2f s (flux damp %.2f) over the last %.0f m"),
		*GetName(), GetLevelCm(), FlowSpeedCmPerS * 0.01f, FlowDirection.X, FlowDirection.Y, FlowFadeM,
		FieldCellCm, HeadDropCm, PipeDamping, BedFriction, 1.f + EndFriction,
		LidRateMps, WindRippleCm, WindGustS, RainDropsPerM2S, RainDropCm, SpongeTauS, SpongeFluxDamp, FlowFadeM);
}

void AGTWaterSheet::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UGTWaterSubsystem* Water = GetWorld() ? GetWorld()->GetSubsystem<UGTWaterSubsystem>() : nullptr)
	{
		Water->UnregisterSheet(this);
	}
	Super::EndPlay(EndPlayReason);
}

float AGTWaterSheet::BedZAt(const FVector2D& WorldXY) const
{
	UWorld* World = const_cast<UWorld*>(GetWorld());
	if (!World)
	{
		return BaseLevelCm - 200.f;
	}
	const float Level = GetLevelCm();
	float BedZ = 0.f;
	bool bHaveBed = false;
	for (const TWeakObjectPtr<ALandscapeProxy>& Proxy : BedLandscapes)
	{
		if (!Proxy.IsValid())
		{
			continue;
		}
		const TOptional<float> Height = Proxy->GetHeightAtLocation(FVector(WorldXY.X, WorldXY.Y, 0.f));
		if (Height.IsSet())
		{
			BedZ = Height.GetValue();
			bHaveBed = true;
			break;
		}
	}
	// Water stage R1 (docs/WATER_PLAN.md section 6): the bed is the HIGHER of the landscape and whatever static
	// geometry stands on it, so a stone in the channel is bed - a submerged one a bump the flow runs over, a proud one
	// dry cells the flow runs round, and a wave bounces off both with no other code. The landscapes themselves are
	// ignored by the trace: their collision mesh is not their heightmap, and taking it here would move a crossing that
	// is tuned to the centimetre. The car, pawns and anything movable are not WorldStatic, so they are not in the
	// query at all; neither is the sheet's own surface mesh, which has no collision.
	if (!bHaveBed || BedZ < Level + GTBedTraceBandCm)
	{
		FCollisionQueryParams Params(SCENE_QUERY_STAT(GTWaterBed), false, this);
		for (const TWeakObjectPtr<ALandscapeProxy>& Proxy : BedLandscapes)
		{
			if (Proxy.IsValid())
			{
				Params.AddIgnoredActor(Proxy.Get());
			}
		}
		const FVector From(WorldXY.X, WorldXY.Y, Level + GTBedTraceOverLevelCm);
		const FVector To(WorldXY.X, WorldXY.Y, bHaveBed ? BedZ - 50.f : Level - 20000.f);
		FHitResult Hit;
		++BedTracedCells;
		if (World->LineTraceSingleByObjectType(Hit, From, To, FCollisionObjectQueryParams(ECC_WorldStatic), Params))
		{
			const float HitZ = static_cast<float>(Hit.ImpactPoint.Z);
			if (!bHaveBed || HitZ > BedZ + 1.f)
			{
				++BedFromTraceCells;
				BedZ = HitZ;
				bHaveBed = true;
			}
		}
	}
	if (bHaveBed)
	{
		return BedZ;
	}
	// Nothing under the sheet: a bed two metres down, so the cell is water rather than a hole.
	return BaseLevelCm - 200.f;
}

FString AGTWaterSheet::StatsLine(const FGTWaterRunStats& Stats, const TCHAR* Why) const
{
	const float FrameMean = Stats.FrameMsMean();
	return FString::Printf(TEXT("GTWATERSTATS %s (%s): %d frames, frame %.2f ms mean / %.2f worst (%.0f fps mean), field step %.3f ms mean / %.3f worst over %d stepping frames, sub-steps %d asked / %d run (cap %d, burst %d of %.4f s), clamps %d, deficit %.3f s; since the field was built: %d coarse frames (the last at a Courant number of %.2f) and %d frames dropped by the %.2f s bound"),
		*GetName(), Why, Stats.Frames, FrameMean, Stats.FrameMsWorst, FrameMean > 0.f ? 1000.f / FrameMean : 0.f,
		Stats.StepMsMean(), Stats.StepMsWorst, Stats.StepFrames,
		Stats.SubStepsAsked, Stats.SubStepsRun, Field.MaxSubSteps, Field.MaxSubStepsBurst, Field.SubStepSeconds,
		Stats.Clamps, Stats.DeficitSeconds, Field.CoarseFrames, Field.LastCoarseCfl, Field.AccumulatorDrops, Field.MaxAccumulatorSeconds);
}

FString AGTWaterSheet::TakeStepStatsLine(const TCHAR* Why)
{
	const FString Line = StatsLine(StepStats, Why);
	StepStats.Reset();
	return Line;
}

void AGTWaterSheet::AccumulateStats(float DeltaSeconds)
{
	const float FrameMs = FMath::Max(0.f, DeltaSeconds) * 1000.f;
	// The field's counters are cumulative and are only reset when it is built, so a tick's own share is the difference
	// (clamped at 0, which is what a rebuild's reset reads as).
	const int32 AskedNow = FMath::Max(0, Field.SubStepsAsked - LastSubStepsAsked);
	const int32 RunNow = FMath::Max(0, Field.SubStepsRun - LastSubStepsRun);
	const int32 ClampsNow = FMath::Max(0, Field.SubStepClamps - LastClamps);
	const float DeficitNow = FMath::Max(0.f, Field.DeficitSeconds - LastDeficitSeconds);
	LastSubStepsAsked = Field.SubStepsAsked;
	LastSubStepsRun = Field.SubStepsRun;
	LastClamps = Field.SubStepClamps;
	LastDeficitSeconds = Field.DeficitSeconds;
	for (FGTWaterRunStats* Stats : { &SecondStats, &StepStats })
	{
		++Stats->Frames;
		Stats->FrameMsSum += FrameMs;
		Stats->FrameMsWorst = FMath::Max(Stats->FrameMsWorst, FrameMs);
		if (RunNow > 0)
		{
			++Stats->StepFrames;
			Stats->StepMsSum += Field.StepMs;
			Stats->StepMsWorst = FMath::Max(Stats->StepMsWorst, Field.StepMs);
		}
		Stats->SubStepsAsked += AskedNow;
		Stats->SubStepsRun += RunNow;
		Stats->Clamps += ClampsNow;
		Stats->DeficitSeconds += DeficitNow;
	}
}

void AGTWaterSheet::BuildField()
{
	bFieldBuilt = true;
	const FVector Centre = GetActorLocation();
	const FVector2D CentreXY(Centre.X, Centre.Y);
	const FVector2D Dir = FlowDirection.IsNearlyZero()
		? FVector2D(FMath::Cos(FMath::DegreesToRadians(GetActorRotation().Yaw)), FMath::Sin(FMath::DegreesToRadians(GetActorRotation().Yaw)))
		: FlowDirection.GetSafeNormal();
	const float HalfAlong = FMath::Max(100.f, FlowHalfSpanCm());
	const float HalfAcross = FMath::Max(100.f, CrossHalfSpanCm());
	Field.PipeDamping = FMath::Max(0.f, PipeDamping);
	Field.BedFriction = FMath::Max(1.e-4f, BedFriction);
	Field.EndFriction = FMath::Max(0.f, EndFriction);
	Field.FlowFadeM = FMath::Max(0.f, FlowFadeM);
	Field.HeadDropCm = FMath::Max(0.f, HeadDropCm);
	Field.DryDepthM = FMath::Max(0.001f, DryCutCm * 0.01f);
	// WS2's sources.
	Field.LidRateMps = FMath::Max(0.01f, LidRateMps);
	Field.WindRippleCm = FMath::Max(0.f, WindRippleCm);
	Field.WindGustS = FMath::Max(0.5f, WindGustS);
	Field.RainDropsPerM2S = FMath::Max(0.f, RainDropsPerM2S);
	Field.RainDropCm = FMath::Max(0.f, RainDropCm);
	Field.SpongeTauS = FMath::Max(0.f, SpongeTauS);
	Field.SpongeFluxDamp = FMath::Max(0.f, SpongeFluxDamp);
	// What the open ends are seeded with: the section's own current (W1's FlowSpeedMps, through the sheet).
	Field.NominalFlowMps = FMath::Max(0.f, FlowSpeedCmPerS * 0.01f);
	if(WaterDomain) { MoveWaterWindow(FVector2D(GetActorLocation()),true); return; }
	if (RiverReference)
	{
		const UGTRiverReference& R = *RiverReference;
		const int64 N = static_cast<int64>(R.SizeX)*R.SizeY;
		if (R.SizeX<2 || R.SizeY<2 || N>8192 || !FMath::IsFinite(R.CellCm) || R.CellCm<10 || R.BedCm.Num()!=N || R.AxisX.IsNearlyZero() || R.AxisX.ContainsNaN() || R.OriginCm.ContainsNaN())
		{
			UE_LOG(LogTemp, Error, TEXT("GTRIVER invalid/capped reference on %s"), *GetName()); return;
		}
		for(float Bed : R.BedCm) if(!FMath::IsFinite(Bed))
		{
			UE_LOG(LogTemp, Error, TEXT("GTRIVER invalid reference bed")); return;
		}
		const FVector2D AX=R.AxisX.GetSafeNormal(), AY(-AX.Y,AX.X);
		const FVector2D Mid=R.OriginCm+(AX*R.SizeX+AY*R.SizeY)*(R.CellCm*.5);
		Field.Init(Mid,AX,R.SizeX*R.CellCm*.5f,R.SizeY*R.CellCm*.5f,R.CellCm,GetLevelCm(),
			[&](const FVector2D& XY)
			{
				const FVector2D P=XY-R.OriginCm;
				const int32 X=FMath::Clamp(FMath::FloorToInt(FVector2D::DotProduct(P,AX)/R.CellCm),0,R.SizeX-1);
				const int32 Y=FMath::Clamp(FMath::FloorToInt(FVector2D::DotProduct(P,AY)/R.CellCm),0,R.SizeY-1);
				return R.BedCm[Y*R.SizeX+X];
			});
		if (!Field.SetRiverReference(R.DepthM,R.FluxX,R.FluxY))
		{
			Field=FGTWaterField(); UE_LOG(LogTemp, Error, TEXT("GTRIVER rejected unbalanced reference")); return;
		}
		BuildSurfaceMesh();
		UE_LOG(LogTemp, Display, TEXT("GTRIVER reference initialized: %d cells, %.3f m3, shared rendered/queried field"), Field.NumCells(),Field.VolumeM3());
		return;
	}
	// R1: the landscapes the bed reads, gathered once (the sampler ran a TActorIterator per cell before) and ignored
	// by the bed's own trace.
	BedLandscapes.Reset();
	if (UWorld* BedWorld = GetWorld())
	{
		for (TActorIterator<ALandscapeProxy> It(BedWorld); It; ++It)
		{
			BedLandscapes.Add(*It);
		}
	}
	BedFromTraceCells = 0;
	BedTracedCells = 0;
	// RIVERBED S3 (VEHICLE_BUILD_SYSTEM 53), measure first: the basin this ford's water fills at its level, against the
	// placed box. Logged as GTFORDFILL in every run (the first tick), so the ford diag's and the water test's logs carry it.
	Basin.Fill(CentreXY, Dir, FieldCellCm, GTBasinSearchCm, GetLevelCm(), HalfAlong, HalfAcross,
		[this](const FVector2D& XY) { return BedZAt(XY); },
		bUseAuthoredBasinSeed ? TOptional<FVector2D>(AuthoredBasinSeedCm) : TOptional<FVector2D>());
	LogBasin();
	BedFromTraceCells = 0;
	BedTracedCells = 0;
	// RIVERBED S3, the change: the field is laid over the basin's wet region plus BasinMarginM, on the survey's own
	// lattice, instead of the placed (section + 24) x 30 m box. -GTWaterPlacedBox keeps the placed box (the before
	// picture). A sheet with a current keeps the placed box's length along the flow: its two flow-wise ends are the
	// current's source and sink and HeadDropCm is set over that length (the slope sets the speed, v = sqrt(g h S / f)),
	// so the Hide's tuned current is not moved; across the flow it takes the basin too, symmetric about the crossing.
	FVector2D FieldCentre = CentreXY;
	float FieldHalfAlong = HalfAlong;
	float FieldHalfAcross = HalfAcross;
	bBasinBox = !FParse::Param(FCommandLine::Get(), TEXT("GTWaterPlacedBox")) && Basin.IsValid();
	bBasinCapped = false;
	const bool bFlowing = HeadDropCm > 0.f && FlowSpeedCmPerS > 0.f;
	int32 BoxCellsWanted = 0;
	// The basin + margin wanted, and the simulated window of it, in the survey lattice's cells.
	int32 WLoX = 0, WHiX = -1, WLoY = 0, WHiY = -1, SLoX = 0, SHiX = -1, SLoY = 0, SHiY = -1;
	// -GTWaterSimCellCap=N overrides MaxSimCells for a run (a check of the static part on a basin under the cap).
	int32 Cap = MaxSimCells;
	int32 CapOverride = 0;
	if (FParse::Value(FCommandLine::Get(), TEXT("GTWaterSimCellCap="), CapOverride) && CapOverride > 0)
	{
		Cap = CapOverride;
	}
	if (bBasinBox)
	{
		const int32 H = Basin.Half();
		const int32 Last = Basin.Size - 1;
		const int32 Margin = FMath::Max(0, FMath::CeilToInt(BasinMarginM * 100.f / Basin.CellCm - 0.001f));
		int32 LoX = FMath::Max(0, Basin.MinX - Margin), HiX = FMath::Min(Last, Basin.MaxX + Margin);
		int32 LoY = FMath::Max(0, Basin.MinY - Margin), HiY = FMath::Min(Last, Basin.MaxY + Margin);
		if (bFlowing)
		{
			LoX = Basin.BoxMinX;
			HiX = Basin.BoxMaxX;
			const int32 HalfY = FMath::Max(H - FMath::Min(LoY, Basin.BoxMinY), FMath::Max(HiY, Basin.BoxMaxY) + 1 - H);
			LoY = FMath::Max(0, H - HalfY);
			HiY = FMath::Min(Last, H + HalfY - 1);
		}
		BoxCellsWanted = (HiX - LoX + 1) * (HiY - LoY + 1);
		WLoX = LoX; WHiX = HiX; WLoY = LoY; WHiY = HiY;
		// The cap: a window of at most MaxSimCells, along the flow first (still water) or across it (a current's length
		// stays), kept about the crossing (the lattice's middle) as far as the basin's bounds allow.
		auto Window = [H](int32& Lo, int32& Hi, int32 MaxN)
		{
			if (Hi - Lo + 1 <= MaxN)
			{
				return;
			}
			const int32 Start = FMath::Clamp(H - MaxN / 2, Lo, Hi - MaxN + 1);
			Lo = Start;
			Hi = Start + MaxN - 1;
		};
		if (Cap > 0 && BoxCellsWanted > Cap)
		{
			bBasinCapped = true;
			if (!bFlowing)
			{
				Window(LoX, HiX, FMath::Max(2, Cap / (HiY - LoY + 1)));
			}
			Window(LoY, HiY, FMath::Max(2, Cap / (HiX - LoX + 1)));
		}
		SLoX = LoX; SHiX = HiX; SLoY = LoY; SHiY = HiY;
		const int32 NX = HiX - LoX + 1;
		const int32 NY = HiY - LoY + 1;
		FieldCentre = Basin.OriginCm + Basin.AxisX * ((LoX + HiX + 1) * 0.5 * Basin.CellCm) + Basin.AxisY * ((LoY + HiY + 1) * 0.5 * Basin.CellCm);
		FieldHalfAlong = NX * Basin.CellCm * 0.5f;
		FieldHalfAcross = NY * Basin.CellCm * 0.5f;
	}
	const double Started = FPlatformTime::Seconds();
	// The landscape list is walked per cell, so gather the bed through one lambda and let the field drive it.
	Field.Init(FieldCentre, Dir, FieldHalfAlong, FieldHalfAcross, FieldCellCm, GetLevelCm(),
		[this](const FVector2D& XY) { return BedZAt(XY); });
	const double BedMs = (FPlatformTime::Seconds() - Started) * 1000.0;
	if (bBasinBox)
	{
		// Still water only in the basin: the fill from the survey's seed at the level the heads hold (the level + half
		// the head drop), so a hollow the level does not reach through the bed stays dry (Init filled every cell).
		const FVector2D SeedXY = Basin.CellCentreCm(Basin.SeedIndex % Basin.Size, Basin.SeedIndex / Basin.Size);
		const float FillLevel = GetLevelCm() + 0.5f * FMath::Max(0.f, HeadDropCm);
		const int32 BasinCells = Field.SetBasinFrom(Field.CellIndexAt(SeedXY), FillLevel);
		const float Cell = Field.CellCm * 0.01f;
		const FVector2D FieldMid = Field.ToFieldCm(CentreXY);
		UE_LOG(LogTemp, Display, TEXT("GTFORDBOX %s: the field laid over the basin, %s: %d x %d = %d cells (%.1f x %.1f m; the placed box %d cells, the basin + %.1f m %d cells%s), the placed centre %.2f m along and %.2f m across from the field's corner; the basin filled from (%.0f, %.0f) at %.1f cm (the level + half the head drop): %d cells"),
			*GetName(), bFlowing ? TEXT("a current: the placed length along the flow, the basin across it") : TEXT("still water: the basin both ways"),
			Field.SizeX, Field.SizeY, Field.NumCells(), Field.SizeX * Cell, Field.SizeY * Cell,
			(Basin.BoxMaxX - Basin.BoxMinX + 1) * (Basin.BoxMaxY - Basin.BoxMinY + 1), BasinMarginM, BoxCellsWanted,
			bBasinCapped ? *FString::Printf(TEXT(", CAPPED at %d"), Cap) : TEXT(""),
			FieldMid.X * 0.01f, FieldMid.Y * 0.01f, SeedXY.X, SeedXY.Y, FillLevel, BasinCells);
	}
	float LowestBed = TNumericLimits<float>::Max();
	float HighestBed = -TNumericLimits<float>::Max();
	int32 Wet = 0;
	for (int32 Index = 0; Index < Field.NumCells(); ++Index)
	{
		LowestBed = FMath::Min(LowestBed, Field.BedCm[Index]);
		HighestBed = FMath::Max(HighestBed, Field.BedCm[Index]);
		if (Field.DepthM[Index] > Field.DryDepthM)
		{
			++Wet;
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AGTWaterSheet %s: WS1 field %d x %d = %d cells of %.1f cm over %.1f x %.1f m (X along the flow (%.2f, %.2f)); bed %.0f to %.0f cm under a level of %.0f, %d cells wet (%.1f %%), %.1f m3, bed sampled in %.0f ms"),
		*GetName(), Field.SizeX, Field.SizeY, Field.NumCells(), Field.CellCm,
		Field.SizeX * Field.CellCm / 100.f, Field.SizeY * Field.CellCm / 100.f, Field.AxisX.X, Field.AxisX.Y,
		LowestBed, HighestBed, GetLevelCm(), Wet, Field.NumCells() > 0 ? 100.f * Wet / Field.NumCells() : 0.f,
		Field.VolumeM3(), BedMs);
	UE_LOG(LogTemp, Display, TEXT("AGTWaterSheet %s: R1 bed from %d landscape(s); %d cells traced against static world geometry (the band %.0f cm under the level), %d of them took their bed from the trace rather than the landscape (a stone standing in the channel)"),
		*GetName(), BedLandscapes.Num(), BedTracedCells, GTBedTraceBandCm, BedFromTraceCells);
	BuildSurfaceMesh();
	// RIVERBED S3: past the cap a still basin goes on as a static flat sheet; a current stops at the cap (the Hide's
	// stream past its ends is R3a's river).
	bStaticPart = false;
	if (bBasinBox && bBasinCapped && !bFlowing)
	{
		BuildStaticPart(WLoX, WHiX, WLoY, WHiY, SLoX, SHiX, SLoY, SHiY);
	}
	Basin.ReleaseLattice();
}

void AGTWaterSheet::BuildSurfaceMesh()
{
	SurfaceVertexCount = 0;
	if (!SurfaceMesh || !Field.IsValid())
	{
		return;
	}
	if (!SurfaceMaterial)
	{
		if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, *SurfaceMaterialPath))
		{
			SurfaceMaterial = UMaterialInstanceDynamic::Create(Base, this);
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("AGTWaterSheet: %s missing (run Art/setup_m6_water.bat); the ford draws no surface"), *SurfaceMaterialPath);
		}
	}
	if (!SurfaceMaterial)
	{
		SurfaceMesh->SetVisibility(false);
		return;
	}
	// The field texture: R the surface over the level in cm, G the water column in cm, and since W4 B and A the
	// cell's flow in the field's axes in cm/s (AGTWaterSheet::FieldTexel writes the texel). Half-float RGBA and not the plan's
	// R32F because the dry cells need a value the hardware's bilinear filter may safely blend with a wet neighbour -
	// a sentinel in the same channel the vertex shader displaces by would throw the shoreline vertices to the moon -
	// so the dryness rides in its own channel and the height stays a height everywhere. A transient texture's first
	// mip is not cleared, so it is zeroed before the first upload.
	FieldTexture = UTexture2D::CreateTransient(Field.SizeX, Field.SizeY, PF_FloatRGBA);
	if (FieldTexture)
	{
		FieldTexture->SRGB = false;
		FieldTexture->Filter = TF_Bilinear;
		FieldTexture->AddressX = TA_Clamp;
		FieldTexture->AddressY = TA_Clamp;
		if (FTexturePlatformData* PlatformData = FieldTexture->GetPlatformData())
		{
			if (PlatformData->Mips.Num() > 0)
			{
				FTexture2DMipMap& Mip = PlatformData->Mips[0];
				if (void* Data = Mip.BulkData.Lock(LOCK_READ_WRITE))
				{
					FMemory::Memzero(Data, Mip.BulkData.GetBulkDataSize());
				}
				Mip.BulkData.Unlock();
			}
		}
		FieldTexture->UpdateResource();
	}

	const int32 Count = Field.NumCells();
	// The grid's own centre in world XY (the field's origin plus half its span along each axis).
	MeshCentreCm = Field.OriginCm + Field.AxisX * (Field.SizeX * Field.CellCm * 0.5) + Field.AxisY * (Field.SizeY * Field.CellCm * 0.5);
	TArray<FVector> Vertices;
	TArray<FVector> Normals;
	TArray<FVector2D> UV0;
	TArray<FLinearColor> Colours;
	TArray<FProcMeshTangent> Tangents;
	TArray<int32> Triangles;
	Vertices.Reserve(Count);
	Normals.Reserve(Count);
	UV0.Reserve(Count);
	Colours.Reserve(Count);
	Tangents.Reserve(Count);
	Triangles.Reserve((Field.SizeX - 1) * (Field.SizeY - 1) * 6);
	for (int32 Y = 0; Y < Field.SizeY; ++Y)
	{
		for (int32 X = 0; X < Field.SizeX; ++X)
		{
			const FVector2D World = Field.CellCentreCm(Y * Field.SizeX + X);
			Vertices.Add(FVector(World.X - MeshCentreCm.X, World.Y - MeshCentreCm.Y, 0.f));
			// Flat: the surface's own shape is the vertex shader's, and its normal the pixel shader's finite differences.
			Normals.Add(FVector::UpVector);
			UV0.Add(FVector2D((X + 0.5) / Field.SizeX, (Y + 0.5) / Field.SizeY));
			Colours.Add(FLinearColor::White);
			Tangents.Add(FProcMeshTangent(1.f, 0.f, 0.f));
		}
	}
	for (int32 Y = 0; Y < Field.SizeY - 1; ++Y)
	{
		for (int32 X = 0; X < Field.SizeX - 1; ++X)
		{
			const int32 V00 = Y * Field.SizeX + X;
			const int32 V10 = V00 + 1;
			const int32 V01 = V00 + Field.SizeX;
			const int32 V11 = V01 + 1;
			Triangles.Add(V00);
			Triangles.Add(V01);
			Triangles.Add(V10);
			Triangles.Add(V10);
			Triangles.Add(V01);
			Triangles.Add(V11);
		}
	}
	if (!RiverSurface)
		SurfaceMesh->CreateMeshSection_LinearColor(0, Vertices, Triangles, Normals, UV0, Colours, Tangents, /*bCreateCollision*/ false);
	SurfaceMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	// The vertex shader moves every vertex in Z, so the section's box has to carry that range or the sheet is culled
	// while the camera looks along it.
	if (const FProcMeshSection* Section = SurfaceMesh->GetProcMeshSection(0))
	{
		FProcMeshSection Expanded = *Section;
		if (Expanded.SectionLocalBox.IsValid)
		{
			Expanded.SectionLocalBox.Min.Z -= SurfaceRangeCm;
			Expanded.SectionLocalBox.Max.Z += SurfaceRangeCm;
			SurfaceMesh->SetProcMeshSection(0, Expanded);
		}
	}
	SurfaceVertexCount = Count;
	SurfaceMaterial->SetTextureParameterValue(TEXT("FieldTex"), FieldTexture);
	SurfaceMaterial->SetVectorParameterValue(TEXT("FieldMin"), FLinearColor(Field.OriginCm.X, Field.OriginCm.Y, 0.f, 0.f));
	SurfaceMaterial->SetVectorParameterValue(TEXT("FieldSize"), FLinearColor(Field.SizeX * Field.CellCm, Field.SizeY * Field.CellCm, 0.f, 0.f));
	SurfaceMaterial->SetVectorParameterValue(TEXT("FieldAxisX"), FLinearColor(Field.AxisX.X, Field.AxisX.Y, 0.f, 0.f));
	SurfaceMaterial->SetVectorParameterValue(TEXT("FieldAxisY"), FLinearColor(Field.AxisY.X, Field.AxisY.Y, 0.f, 0.f));
	SurfaceMaterial->SetVectorParameterValue(TEXT("FieldTexels"), FLinearColor(Field.SizeX, Field.SizeY, 0.f, 0.f));
	SurfaceMaterial->SetScalarParameterValue(TEXT("NormalGainCm"), NormalGainCm);
	SurfaceMaterial->SetScalarParameterValue(TEXT("DryCutCm"), FMath::Max(0.05f, DryCutCm));
	SurfaceMaterial->SetScalarParameterValue(TEXT("FieldLevelCm"), GetLevelCm());
	SurfaceMaterial->SetScalarParameterValue(TEXT("FieldActive"), 1.f);
	SurfaceMaterial->SetScalarParameterValue(TEXT("LocalSurface"), WaterDomain ? 1.f : 0.f);
	SurfaceMesh->SetMaterial(0, SurfaceMaterial);
	SurfaceMesh->SetVisibility(!RiverSurface);
	if (RiverSurface && RiverSurface->GetStaticMeshComponent())
	{
		RiverSurface->GetStaticMeshComponent()->SetMaterial(0, SurfaceMaterial);
		RiverSurface->GetStaticMeshComponent()->SetBoundsScale(1.05f);
	}
	SurfaceMesh->SetRelativeLocation(FVector(MeshCentreCm.X, MeshCentreCm.Y, GetLevelCm()));
	UploadField();
	UE_LOG(LogTemp, Display, TEXT("AGTWaterSheet %s: WS1 surface mesh %d vertices (%d x %d), %d triangles, no collision, no shadow, translucent sort 2; field texture %d x %d PF_FloatRGBA (R the surface over the level in cm, G the water column in cm, B and A the flow in the field's axes in cm/s), material %s"),
		*GetName(), SurfaceVertexCount, Field.SizeX, Field.SizeY, Triangles.Num() / 3,
		FieldTexture ? FieldTexture->GetSizeX() : 0, FieldTexture ? FieldTexture->GetSizeY() : 0, *SurfaceMaterialPath);
}

FLinearColor AGTWaterSheet::FieldTexel(const FGTWaterField& InField, float LevelCm, int32 Index)
{
	if (!InField.SurfaceCm.IsValidIndex(Index))
	{
		return FLinearColor(0.f, 0.f, 0.f, 0.f);
	}
	// R the surface over the level, G what stands in the column: WS2's lid counts toward G as water does, or the
	// mesh would be cut away under a car that has pushed its own cells dry and leave a hole where the car is.
	// W4: B and A carry the cell's flow in the field's own axes, cm/s, which is what pans the ripple normal; a cell
	// with no water in it carries no flow, because the solver leaves its last velocity behind when it dries.
	const bool bWet = InField.DepthM[Index] > InField.DryDepthM;
	return FLinearColor(InField.SurfaceCm[Index] - LevelCm,
		(InField.DepthM[Index] + InField.LidM[Index]) * 100.f,
		bWet ? InField.VelXMps[Index] * 100.f : 0.f,
		bWet ? InField.VelYMps[Index] * 100.f : 0.f);
}

FLinearColor AGTWaterSheet::ShoreTexel(const FGTWaterField& F, float Level, int32 I)
{
	FLinearColor C=FieldTexel(F,Level,I);
	if(!F.SurfaceCm.IsValidIndex(I) || F.DepthM[I]+F.LidM[I]>.00001f)return C;
	// Dry solver cells carry bed elevation, not a water surface. Extrapolate the
	// adjoining wet surface into them, keeping a signed depth for sub-cell clipping.
	// This is a rendering bridge only: no water mass, flux or physical height changes.
	const int32 X=I%F.SizeX,Y=I/F.SizeX;float Sum=0,Weight=0;
	for(int32 DY=-1;DY<=1;++DY)for(int32 DX=-1;DX<=1;++DX)
	{
		if(X+DX<0 || X+DX>=F.SizeX || Y+DY<0 || Y+DY>=F.SizeY)continue;
		const int32 J=(Y+DY)*F.SizeX+X+DX;
		if(F.DepthM[J]+F.LidM[J]>.00001f){Sum+=F.SurfaceCm[J];Weight+=1;}
	}
	const float Surface=Weight>0?Sum/Weight:Level;
	C.R=Surface-Level;C.G=FMath::Min(0.f,Surface-F.BedCm[I]);return C;
}

void AGTWaterSheet::UploadField()
{
	if (!FieldTexture || !FieldTexture->GetResource() || !Field.IsValid())
	{
		return;
	}
	GT_PERF_SCOPE(PerfWUploadField,"Water.UploadField");
	const int32 Width = Field.SizeX;
	const int32 Height = Field.SizeY;
	PerfWUploadField.Work = Width * Height;
	const float Level = GetLevelCm();
	TArray<FFloat16Color>* Data = new TArray<FFloat16Color>();
	Data->SetNumUninitialized(Width * Height);
	for (int32 Index = 0; Index < Width * Height; ++Index)
	{
		(*Data)[Index] = FFloat16Color(bContinuousShoreRendering ? ShoreTexel(Field, Level, Index) : FieldTexel(Field, Level, Index));
	}
	FUpdateTextureRegion2D* Region = new FUpdateTextureRegion2D(0, 0, 0, 0, Width, Height);
	FieldTexture->UpdateTextureRegions(0, 1, Region, Width * sizeof(FFloat16Color), sizeof(FFloat16Color), reinterpret_cast<uint8*>(Data->GetData()),
		[Data](uint8*, const FUpdateTextureRegion2D* Regions)
		{
			delete Data;
			delete Regions;
		});
	++UploadCount;
}

void AGTWaterSheet::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// Optical evolution also runs on sleeping ponds; this does not step their fluid field.
	if(!WaterDomain && AmbientWaveMaterial && GetWorld())UpdateAmbientWaves(GetWorld()->GetTimeSeconds());
	if(MudSurface) { TickMudWater(DeltaSeconds); return; }
	if(WaterDomain) { TickWaterDomain(DeltaSeconds); return; }
	// The two cvars are read once here, on the game thread, and cached: the surface and the flow are asked for
	// several times per wheel per tick from the traction and the hull.
	CvarExtraRiseCm = CVarWaterExtraRiseCm.GetValueOnGameThread();
	AppliedFlowScale = FMath::Max(0.f, CVarWaterFlowScale.GetValueOnGameThread());
	AppliedWind = FMath::Max(0.f, CVarWaterWind.GetValueOnGameThread());
	bLidsOn = CVarWaterLids.GetValueOnGameThread() != 0;
	const UGTWeatherSubsystem* Weather = GetWorld() ? GetWorld()->GetSubsystem<UGTWeatherSubsystem>() : nullptr;
	WetnessRiseCm = Weather ? FMath::Clamp(Weather->GetWetness(), 0.f, 1.f) * RiseWithWetnessCm : 0.f;
	// Water stage W5: the river stage. The subsystem holds one stage for every sheet in the world and advances it
	// once a frame, whichever sheet asks first; the sheet caches it beside the cvars so GetLevelCm stays a few adds.
	if (UGTWaterSubsystem* Water = GetWorld() ? GetWorld()->GetSubsystem<UGTWaterSubsystem>() : nullptr)
	{
		Water->AdvanceRiverStage(DeltaSeconds);
		RiverRiseCm = Water->GetRiverStageCm();
	}
	// WS2: the rain that falls on this ford - the weather's intensity at the sheet's own middle, so a sheet under
	// cover gets none. It is an impulse source: the drops add no water, the level is still the boundary's.
	const FVector CentreForRain = GetActorLocation();
	AppliedRain = Weather ? FMath::Clamp(Weather->GetRainAt(CentreForRain), 0.f, 1.f) : 0.f;
	Field.WindScale = AppliedWind;
	Field.RainIntensity = AppliedRain;
	if (!bLidsOn && Field.LidCellCount > 0)
	{
		Field.ClearLids();
	}
	const float Level = GetLevelCm();
	if (!FMath::IsNearlyEqual(Level, AppliedLevelCm, 0.5f))
	{
		const FVector Location = GetActorLocation();
		SetActorLocation(FVector(Location.X, Location.Y, Level));
		AppliedLevelCm = Level;
	}
	// The field is built on the first tick, not at BeginPlay: the landscape has to be registered before its heights
	// can be read, and nothing guarantees that order between placed actors.
	if (!bFieldBuilt)
	{
		BuildField();
		FieldLevelCm = Level;
		return;
	}
	if (RiverReference)
	{
		// The pilot owns a fixed mean stage, not a catchment flood simulation. Stay at its authored level.
		float NearCm=1.e9f;
		if (const APlayerController* PC=GetWorld()->GetFirstPlayerController())
		{
			if (PC->PlayerCameraManager) NearCm=FVector::Dist2D(PC->PlayerCameraManager->GetCameraLocation(),GetActorLocation());
			if (PC->GetPawn()) NearCm=FMath::Min(NearCm,static_cast<float>(FVector::Dist2D(PC->GetPawn()->GetActorLocation(),GetActorLocation())));
		}
		if (NearCm<RiverActiveDistanceM*100) { bRiverAwake=true; RiverFarSeconds=0; }
		else if (NearCm>(RiverActiveDistanceM+40)*100) RiverFarSeconds+=DeltaSeconds;
		if (bRiverAwake && RiverFarSeconds>8)
		{
			Field.ResetRiverReference(); UploadField(); bRiverAwake=false;
		}
		if (bRiverAwake && Field.HasRiverReference())
		{
			Field.Step(DeltaSeconds,BaseLevelCm,1); UploadField(); AccumulateStats(DeltaSeconds);
		}
		return;
	}
	// EVERY level change is carried into the field at once (LevelJumpCm 0 since WS2's follow-up): the whole surface
	// lifts in the same tick, wet cells by the delta and dry ones flooding from the new level, so a rise makes no wave
	// at all. Left to the two fixed heads - which is what a 5 cm threshold did to the weather's slow rise - a step
	// reaches the middle as a bore and rings the basin's mode for a minute.
	const bool bCarryLevel = FMath::Abs(Level - FieldLevelCm) > FMath::Max(0.01f, LevelJumpCm);
	if (bCarryLevel)
	{
		if (bSuppressNextShift)
		{
			UE_LOG(LogTemp, Display, TEXT("AGTWaterSheet %s: the level moved %.1f cm and was NOT carried into the field (the ends fill it)"), *GetName(), Level - FieldLevelCm);
		}
		else
		{
			// R1: measured from the level the field was last carried to (FieldLevelCm), so the frames whose change was
			// too small to cross the threshold are carried as well and not thrown away one at a time.
			Field.ShiftLevel(Level, FieldLevelCm);
		}
	}
	// W5: the level is remembered only when its change was taken - carried, or deliberately left to the ends. The
	// river's own rise is 0.007 cm a tick at RiseLagS 180 s, under the 0.01 cm floor, and remembering the level every
	// tick would throw those away one at a time and the field would never follow the river at all.
	if (bCarryLevel || bSuppressNextShift)
	{
		FieldLevelCm = Level;
	}
	bSuppressNextShift = false;
	Field.Step(DeltaSeconds, Level, AppliedFlowScale);
	if (SurfaceMesh && SurfaceVertexCount > 0)
	{
		SurfaceMesh->SetRelativeLocation(FVector(MeshCentreCm.X, MeshCentreCm.Y, Level));
		UploadField();
	}
	// RIVERBED S3: the static part follows the level (W5's rise) when it has moved a quarter of a centimetre.
	if (bStaticPart && FMath::Abs(Level - StaticLevelCm) > 0.25f)
	{
		UploadStatic();
	}
	// ---- R1: what this frame cost the water, in every run, rendered ones included ----
	AccumulateStats(DeltaSeconds);
	// ---- RIVERBED S3: the step the field's edges stand at against the level, twice a run ----
	SinceFieldBuilt += DeltaSeconds;
	if ((SeamLogs == 0 && SinceFieldBuilt >= 5.f) || (SeamLogs == 1 && SinceFieldBuilt >= 30.f))
	{
		++SeamLogs;
		UE_LOG(LogTemp, Display, TEXT("%s (%.0f s after the field was built)"), *SeamLine(), SinceFieldBuilt);
	}
	SinceStatsLog += DeltaSeconds;
	if (SinceStatsLog >= 1.f)
	{
		// Once a second while someone is near enough to see this ford: a camera's view point, or the pawn's, whichever
		// is nearer (a shots run drives the view from a camera actor with no pawn in the water at all).
		float NearestCm = 1.e9f;
		if (const APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr)
		{
			if (const APlayerCameraManager* Camera = PC->PlayerCameraManager)
			{
				NearestCm = FMath::Min(NearestCm, static_cast<float>(FVector::Dist2D(Camera->GetCameraLocation(), GetActorLocation())));
			}
			if (const APawn* Pawn = PC->GetPawn())
			{
				NearestCm = FMath::Min(NearestCm, static_cast<float>(FVector::Dist2D(Pawn->GetActorLocation(), GetActorLocation())));
			}
		}
		if (NearestCm <= StatsNearM * 100.f)
		{
			UE_LOG(LogTemp, Display, TEXT("%s, viewer %.0f m off"), *StatsLine(SecondStats, TEXT("the last second")), NearestCm * 0.01f);
		}
		SecondStats.Reset();
		SinceStatsLog = 0.f;
	}
	if (GEngine && CVarWaterStats.GetValueOnGameThread() != 0)
	{
		GEngine->AddOnScreenDebugMessage(StatsKey, 1.1f, FColor::Cyan, StatsLine(SecondStats, TEXT("this second")));
	}
}

bool AGTWaterSheet::Covers(FVector2D WorldXY) const
{
	if(MudSurface) return Field.IsValid() && InFieldRect(WorldXY) && Field.DepthMAt(WorldXY)>.002f;
	if(WaterDomain) { float S,H;FVector2D V;return SampleDomainWater(WorldXY,S,H,V); }
	if (RiverReference) return Field.HasRiverReference() && InFieldRect(WorldXY)
		&& (Field.DepthMAt(WorldXY)>Field.DryDepthM || Field.LidM[Field.CellIndexAt(WorldXY)]>0.f);
	// RIVERBED S3: once the field is laid over the basin, the footprint is the field's rectangle - all of it inside the
	// placed box, as before S3, and past the placed box only within a cell of the basin or of water the solver has
	// carried there. The field's dry rectangle is not water: a covered dry cell answers its bed as the surface, so a
	// hull sunk into ground under it read "ford water" (measured: the Hide's capped field reached its bog, and the terrain
	// test's parked car read 0.129 m of it). The static part likewise only near its basin.
	if (bBasinBox && Field.IsValid())
	{
		if (InFieldRect(WorldXY))
		{
			return InPlacedBox(WorldXY) || NearFieldWater(Field.CellIndexAt(WorldXY));
		}
		return InStaticPart(WorldXY) && NearStaticBasin(WorldXY);
	}
	return InPlacedBox(WorldXY);
}

bool AGTWaterSheet::InPlacedBox(const FVector2D& WorldXY) const
{
	// The cube is 100 cm before the actor's scale, so a point is inside when its actor-space X and Y are within 50.
	const FVector Local = GetActorTransform().InverseTransformPosition(FVector(WorldXY.X, WorldXY.Y, GetActorLocation().Z));
	return FMath::Abs(Local.X) <= 50.f && FMath::Abs(Local.Y) <= 50.f;
}

bool AGTWaterSheet::NearFieldWater(int32 Index) const
{
	if (!Field.IsValid() || Index == INDEX_NONE)
	{
		return false;
	}
	const int32 X = Index % Field.SizeX;
	const int32 Y = Index / Field.SizeX;
	for (int32 DY = -1; DY <= 1; ++DY)
	{
		for (int32 DX = -1; DX <= 1; ++DX)
		{
			const int32 NX = X + DX;
			const int32 NY = Y + DY;
			if (NX < 0 || NY < 0 || NX >= Field.SizeX || NY >= Field.SizeY)
			{
				continue;
			}
			const int32 J = NY * Field.SizeX + NX;
			if ((Field.Basin.IsValidIndex(J) && Field.Basin[J]) || Field.DepthM[J] > Field.DryDepthM)
			{
				return true;
			}
		}
	}
	return false;
}

bool AGTWaterSheet::NearStaticBasin(const FVector2D& WorldXY) const
{
	if (!bStaticPart || StaticNX <= 0)
	{
		return false;
	}
	const FVector2D D = WorldXY - StaticOriginCm;
	const int32 X = FMath::FloorToInt(static_cast<float>(FVector2D::DotProduct(D, Field.AxisX)) / Field.CellCm);
	const int32 Y = FMath::FloorToInt(static_cast<float>(FVector2D::DotProduct(D, Field.AxisY)) / Field.CellCm);
	for (int32 DY = -1; DY <= 1; ++DY)
	{
		for (int32 DX = -1; DX <= 1; ++DX)
		{
			const int32 NX = X + DX;
			const int32 NY = Y + DY;
			if (NX >= 0 && NY >= 0 && NX < StaticNX && NY < StaticNY && StaticBasin[NY * StaticNX + NX])
			{
				return true;
			}
		}
	}
	return false;
}

float AGTWaterSheet::FlowHalfSpanCm() const
{
	const FVector2D Dir = FlowDirection.IsNearlyZero()
		? FVector2D(FMath::Cos(FMath::DegreesToRadians(GetActorRotation().Yaw)), FMath::Sin(FMath::DegreesToRadians(GetActorRotation().Yaw)))
		: FlowDirection.GetSafeNormal();
	const FTransform Transform = GetActorTransform();
	const FVector Centre = GetActorLocation();
	float Half = 0.f;
	for (int32 SignX = -1; SignX <= 1; SignX += 2)
	{
		for (int32 SignY = -1; SignY <= 1; SignY += 2)
		{
			const FVector Corner = Transform.TransformPosition(FVector(SignX * 50.f, SignY * 50.f, 0.f));
			Half = FMath::Max(Half, FMath::Abs(static_cast<float>(Dir.X * (Corner.X - Centre.X) + Dir.Y * (Corner.Y - Centre.Y))));
		}
	}
	return Half;
}

float AGTWaterSheet::CrossHalfSpanCm() const
{
	const FVector2D Dir = FlowDirection.IsNearlyZero()
		? FVector2D(FMath::Cos(FMath::DegreesToRadians(GetActorRotation().Yaw)), FMath::Sin(FMath::DegreesToRadians(GetActorRotation().Yaw)))
		: FlowDirection.GetSafeNormal();
	const FVector2D Across(-Dir.Y, Dir.X);
	const FTransform Transform = GetActorTransform();
	const FVector Centre = GetActorLocation();
	float Half = 0.f;
	for (int32 SignX = -1; SignX <= 1; SignX += 2)
	{
		for (int32 SignY = -1; SignY <= 1; SignY += 2)
		{
			const FVector Corner = Transform.TransformPosition(FVector(SignX * 50.f, SignY * 50.f, 0.f));
			Half = FMath::Max(Half, FMath::Abs(static_cast<float>(Across.X * (Corner.X - Centre.X) + Across.Y * (Corner.Y - Centre.Y))));
		}
	}
	return Half;
}

FString AGTWaterSheet::SeamLine() const
{
	if (!Field.IsValid())
	{
		return FString::Printf(TEXT("GTFORDSEAM %s: no field"), *GetName());
	}
	const float Level = GetLevelCm();
	// The four edges: X = 0 (upstream end), X = SizeX - 1 (downstream end), Y = 0 and Y = SizeY - 1 (the sides).
	FString Parts;
	for (int32 Edge = 0; Edge < 4; ++Edge)
	{
		const bool bColumn = Edge < 2;
		const int32 N = bColumn ? Field.SizeY : Field.SizeX;
		int32 Wet = 0;
		double Sum = 0.0;
		float Worst = 0.f;
		for (int32 K = 0; K < N; ++K)
		{
			const int32 X = bColumn ? (Edge == 0 ? 0 : Field.SizeX - 1) : K;
			const int32 Y = bColumn ? K : (Edge == 2 ? 0 : Field.SizeY - 1);
			const int32 I = Y * Field.SizeX + X;
			if (Field.DepthM[I] <= Field.DryDepthM)
			{
				continue;
			}
			const float Step = Field.SurfaceCm[I] - Level;
			++Wet;
			Sum += Step;
			Worst = FMath::Abs(Step) > FMath::Abs(Worst) ? Step : Worst;
		}
		static const TCHAR* Names[4] = { TEXT("upstream end"), TEXT("downstream end"), TEXT("right side"), TEXT("left side") };
		Parts += FString::Printf(TEXT("%s%s %d wet cells, mean %+.2f cm, largest %+.2f cm"), Parts.IsEmpty() ? TEXT("") : TEXT("; "), Names[Edge], Wet,
			Wet > 0 ? static_cast<float>(Sum / Wet) : 0.f, Worst);
	}
	return FString::Printf(TEXT("GTFORDSEAM %s: the field's edges against a flat sheet at the level %.1f cm (%s, head drop %.1f cm x flow scale %.2f): %s"),
		*GetName(), Level, bBasinBox ? (bBasinCapped ? TEXT("the basin box, capped") : TEXT("the basin box")) : TEXT("the placed box"),
		HeadDropCm, AppliedFlowScale, *Parts);
}

float AGTWaterSheet::SurfaceCmAt(FVector2D WorldXY) const
{
	if(WaterDomain)
	{
		float S,H;FVector2D V;SampleDomainWater(WorldXY,S,H,V);
		return Field.HasRiverReference() && InFieldRect(WorldXY) && Field.DepthMAt(WorldXY)>.005f ? Field.SurfaceCmAt(WorldXY) : S;
	}
	// RIVERBED S3: the static part stands at the level.
	if (InStaticPart(WorldXY))
	{
		return GetLevelCm();
	}
	return Field.IsValid() ? Field.SurfaceCmAt(WorldXY) : GetLevelCm();
}

FVector2D AGTWaterSheet::FlowCmPerSAt(FVector2D WorldXY) const
{
	if(WaterDomain)
	{
		float S,H;FVector2D V;if(!SampleDomainWater(WorldXY,S,H,V)) return FVector2D::ZeroVector;
		return Field.HasRiverReference() && InFieldRect(WorldXY) ? Field.VelocityAt(WorldXY)*100 : V*100;
	}
	if (!Covers(WorldXY) || InStaticPart(WorldXY))
	{
		return FVector2D::ZeroVector;
	}
	if (Field.IsValid())
	{
		// The field's own velocity: it varies with the bed (fast over the road's hump, slow in the deep), which is
		// what WS1 is for, and it is already zero where gt.Water.FlowScale has taken the head drop away.
		return Field.VelocityAt(WorldXY) * 100.f;
	}
	// Before the first tick: W1's constant, faded at the ends.
	if (FlowSpeedCmPerS <= 0.f || FlowDirection.IsNearlyZero() || AppliedFlowScale <= 0.f)
	{
		return FVector2D::ZeroVector;
	}
	const FVector2D Dir = FlowDirection.GetSafeNormal();
	const FVector Centre = GetActorLocation();
	const float Along = static_cast<float>(Dir.X * (WorldXY.X - Centre.X) + Dir.Y * (WorldXY.Y - Centre.Y));
	const float Half = FlowHalfSpanCm();
	const float FadeCm = FMath::Max(1.f, FlowFadeM * 100.f);
	const float Fade = FMath::Clamp((Half - FMath::Abs(Along)) / FadeCm, 0.f, 1.f);
	return Dir * (FlowSpeedCmPerS * AppliedFlowScale * Fade);
}

void AGTWaterSheet::CalmField()
{
	if (Field.IsValid())
	{
		Field.Calm(GetLevelCm());
	}
}

void AGTWaterSheet::PreviewRiver(float Seconds, bool Reset)
{
	if (!RiverReference || !GetWorld() || GetWorld()->IsGameWorld()) return;
	if (!bFieldBuilt) BuildField();
	if (!Field.HasRiverReference()) return;
	if (Reset) Field.ResetRiverReference();
	// Bounded deterministic editor preview; no frame-time/performance claims from this path.
	const int32 Steps=FMath::Clamp(FMath::RoundToInt(Seconds*60),0,600);
	Field.WindScale=0; Field.RainIntensity=0;
	for(int32 I=0; I<Steps; ++I) Field.Step(1.f/60.f,BaseLevelCm,1);
	UploadField();
}

void AGTWaterSheet::StampLid(const FVector2D& CentreCm, const FVector2D& ForwardXY, float HalfLenCm, float HalfWidCm,
	float BottomZCm, const FVector2D& BottomSlope, float MaxHeightCm, float Fill)
{
	if(MudSurface && !bMudAwake) return;
	// TickWaterDomain owns the player-centred window. A distant parked vehicle
	// must not move it away and force a second rebuild on the following tick.
	// Field stamping already clips contacts to the current simulated area.
	if (bLidsOn && Field.IsValid())
	{
		Field.StampLid(CentreCm, ForwardXY, HalfLenCm, HalfWidCm, BottomZCm, BottomSlope, MaxHeightCm, Fill);
	}
}

FLinearColor AGTWaterSheet::ReviewWaterColumn(FVector2D XY) const
{
	const int32 I=Field.CellIndexAt(XY);if(!Field.SurfaceCm.IsValidIndex(I))return FLinearColor::Transparent;
	const auto C=bContinuousShoreRendering?ShoreTexel(Field,GetLevelCm(),I):FieldTexel(Field,GetLevelCm(),I);
	return FLinearColor(Field.SurfaceCm[I],(Field.DepthM[I]+Field.LidM[I])*100,C.R+GetLevelCm(),Field.VelocityAt(XY).Size()*100);
}
void AGTWaterSheet::ReviewWaterContact(FVector2D XY,float Immersion)
{
	if(!FMath::IsFinite(Immersion) || Immersion<0 || Immersion>100)return;
	StampLid(XY,FVector2D(1,0),140,75,SurfaceCmAt(XY)-Immersion,FVector2D::ZeroVector,Immersion,.65f);
}

double AGTWaterSheet::AddImpulse(FVector2D WorldXY, float RadiusCm, float RiseCm)
{
	// Remote impulses are clipped by the field, never used as streaming focus.
	if(WaterDomain) Field.AddRiverDetail(WorldXY,RadiusCm,FMath::Abs(RiseCm)*.025f,FMath::Abs(RiseCm)*.018f);
	return Field.IsValid() ? Field.AddImpulse(WorldXY, RadiusCm, RiseCm) : 0.0;
}

float AGTWaterSheet::DepthCmAt(const UWorld* World, const FVector& GroundPoint)
{
	if (!World)
	{
		return 0.f;
	}
	if (const UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>())
	{
		return Water->Sample(GroundPoint).DepthCm;
	}
	float Depth = 0.f;
	for (TActorIterator<AGTWaterSheet> It(const_cast<UWorld*>(World)); It; ++It)
	{
		if (It->Covers(FVector2D(GroundPoint)))
		{
			Depth = FMath::Max(Depth, It->SurfaceCmAt(FVector2D(GroundPoint)) - static_cast<float>(GroundPoint.Z));
		}
	}
	return Depth;
}

void AGTWaterSheet::SetExtraRiseAll(UWorld* World, float ExtraCm, bool bShiftField)
{
	if (!World)
	{
		return;
	}
	for (TActorIterator<AGTWaterSheet> It(World); It; ++It)
	{
		It->ExtraRiseCm = ExtraCm;
		It->bSuppressNextShift = !bShiftField;
	}
}

void AGTWaterSheet::CalmAll(UWorld* World)
{
	if (!World)
	{
		return;
	}
	for (TActorIterator<AGTWaterSheet> It(World); It; ++It)
	{
		It->CalmField();
	}
}

// ---- RIVERBED S3: the static part past the cap (VEHICLE_BUILD_SYSTEM 53) ------------------------------------------

bool AGTWaterSheet::InFieldRect(const FVector2D& WorldXY) const
{
	if (!Field.IsValid())
	{
		return false;
	}
	const FVector2D F = Field.ToFieldCm(WorldXY);
	return F.X >= 0.0 && F.Y >= 0.0 && F.X <= Field.SizeX * Field.CellCm && F.Y <= Field.SizeY * Field.CellCm;
}

bool AGTWaterSheet::InStaticPart(const FVector2D& WorldXY) const
{
	if (!bStaticPart || InFieldRect(WorldXY))
	{
		return false;
	}
	const FVector2D D = WorldXY - StaticOriginCm;
	const double X = FVector2D::DotProduct(D, Field.AxisX);
	const double Y = FVector2D::DotProduct(D, Field.AxisY);
	return X >= 0.0 && Y >= 0.0 && X <= StaticNX * Field.CellCm && Y <= StaticNY * Field.CellCm;
}

void AGTWaterSheet::BuildStaticPart(int32 LoX, int32 HiX, int32 LoY, int32 HiY, int32 SimLoX, int32 SimHiX, int32 SimLoY, int32 SimHiY)
{
	UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, *SurfaceMaterialPath);
	if (!SurfaceMesh || !Base || Basin.Size <= 0 || Basin.Sampled.Num() != Basin.Size * Basin.Size || HiX < LoX || HiY < LoY)
	{
		return;
	}
	const double Started = FPlatformTime::Seconds();
	StaticNX = HiX - LoX + 1;
	StaticNY = HiY - LoY + 1;
	StaticOriginCm = Basin.OriginCm + Basin.AxisX * (LoX * Basin.CellCm) + Basin.AxisY * (LoY * Basin.CellCm);
	const int32 Count = StaticNX * StaticNY;
	StaticBedCm.SetNumUninitialized(Count);
	StaticBasin.Init(0, Count);
	int32 Sampled = 0;
	int32 BasinCellsHere = 0;
	for (int32 Y = 0; Y < StaticNY; ++Y)
	{
		for (int32 X = 0; X < StaticNX; ++X)
		{
			const int32 L = Basin.Index(LoX + X, LoY + Y);
			const int32 I = Y * StaticNX + X;
			if (Basin.Sampled[L])
			{
				StaticBedCm[I] = Basin.BedCm[L];
			}
			else
			{
				StaticBedCm[I] = BedZAt(Basin.CellCentreCm(LoX + X, LoY + Y));
				++Sampled;
			}
			StaticBasin[I] = Basin.Wet[L];
			BasinCellsHere += Basin.Wet[L] ? 1 : 0;
		}
	}
	// The grid: a vertex at every lattice cell's centre, laid out about the surface mesh's own centre (the component
	// stands there at the level), and a quad wherever the simulated field does not draw one - so the two sections share
	// the field's edge vertices and neither overlaps nor leaves a gap.
	auto IsSim = [LoX, LoY, SimLoX, SimHiX, SimLoY, SimHiY](int32 X, int32 Y)
	{
		const int32 LX = LoX + X;
		const int32 LY = LoY + Y;
		return LX >= SimLoX && LX <= SimHiX && LY >= SimLoY && LY <= SimHiY;
	};
	TArray<FVector> Vertices;
	TArray<FVector> Normals;
	TArray<FVector2D> UV0;
	TArray<FLinearColor> Colours;
	TArray<FProcMeshTangent> Tangents;
	TArray<int32> Triangles;
	Vertices.Reserve(Count);
	Normals.Reserve(Count);
	UV0.Reserve(Count);
	Colours.Reserve(Count);
	Tangents.Reserve(Count);
	for (int32 Y = 0; Y < StaticNY; ++Y)
	{
		for (int32 X = 0; X < StaticNX; ++X)
		{
			const FVector2D W = Basin.CellCentreCm(LoX + X, LoY + Y);
			Vertices.Add(FVector(W.X - MeshCentreCm.X, W.Y - MeshCentreCm.Y, 0.f));
			Normals.Add(FVector::UpVector);
			UV0.Add(FVector2D((X + 0.5) / StaticNX, (Y + 0.5) / StaticNY));
			Colours.Add(FLinearColor::White);
			Tangents.Add(FProcMeshTangent(1.f, 0.f, 0.f));
		}
	}
	for (int32 Y = 0; Y < StaticNY - 1; ++Y)
	{
		for (int32 X = 0; X < StaticNX - 1; ++X)
		{
			if (IsSim(X, Y) && IsSim(X + 1, Y) && IsSim(X, Y + 1) && IsSim(X + 1, Y + 1))
			{
				continue;
			}
			const int32 V00 = Y * StaticNX + X;
			const int32 V10 = V00 + 1;
			const int32 V01 = V00 + StaticNX;
			const int32 V11 = V01 + 1;
			Triangles.Add(V00);
			Triangles.Add(V01);
			Triangles.Add(V10);
			Triangles.Add(V10);
			Triangles.Add(V01);
			Triangles.Add(V11);
		}
	}
	StaticQuads = Triangles.Num() / 6;
	SurfaceMesh->CreateMeshSection_LinearColor(1, Vertices, Triangles, Normals, UV0, Colours, Tangents, /*bCreateCollision*/ false);
	if (const FProcMeshSection* Section = SurfaceMesh->GetProcMeshSection(1))
	{
		FProcMeshSection Expanded = *Section;
		if (Expanded.SectionLocalBox.IsValid)
		{
			Expanded.SectionLocalBox.Min.Z -= SurfaceRangeCm;
			Expanded.SectionLocalBox.Max.Z += SurfaceRangeCm;
			SurfaceMesh->SetProcMeshSection(1, Expanded);
		}
	}
	// Its own flat field texture (FieldTexel's layout, no flow) and its own instance of the same material.
	StaticTexture = UTexture2D::CreateTransient(StaticNX, StaticNY, PF_FloatRGBA);
	if (StaticTexture)
	{
		StaticTexture->SRGB = false;
		StaticTexture->Filter = TF_Bilinear;
		StaticTexture->AddressX = TA_Clamp;
		StaticTexture->AddressY = TA_Clamp;
		if (FTexturePlatformData* PlatformData = StaticTexture->GetPlatformData())
		{
			if (PlatformData->Mips.Num() > 0)
			{
				FTexture2DMipMap& Mip = PlatformData->Mips[0];
				if (void* Data = Mip.BulkData.Lock(LOCK_READ_WRITE))
				{
					FMemory::Memzero(Data, Mip.BulkData.GetBulkDataSize());
				}
				Mip.BulkData.Unlock();
			}
		}
		StaticTexture->UpdateResource();
	}
	StaticMaterial = UMaterialInstanceDynamic::Create(Base, this);
	StaticMaterial->SetTextureParameterValue(TEXT("FieldTex"), StaticTexture);
	StaticMaterial->SetVectorParameterValue(TEXT("FieldMin"), FLinearColor(StaticOriginCm.X, StaticOriginCm.Y, 0.f, 0.f));
	StaticMaterial->SetVectorParameterValue(TEXT("FieldSize"), FLinearColor(StaticNX * Basin.CellCm, StaticNY * Basin.CellCm, 0.f, 0.f));
	StaticMaterial->SetVectorParameterValue(TEXT("FieldAxisX"), FLinearColor(Basin.AxisX.X, Basin.AxisX.Y, 0.f, 0.f));
	StaticMaterial->SetVectorParameterValue(TEXT("FieldAxisY"), FLinearColor(Basin.AxisY.X, Basin.AxisY.Y, 0.f, 0.f));
	StaticMaterial->SetVectorParameterValue(TEXT("FieldTexels"), FLinearColor(StaticNX, StaticNY, 0.f, 0.f));
	StaticMaterial->SetScalarParameterValue(TEXT("NormalGainCm"), NormalGainCm);
	StaticMaterial->SetScalarParameterValue(TEXT("DryCutCm"), FMath::Max(0.05f, DryCutCm));
	SurfaceMesh->SetMaterial(1, StaticMaterial);
	bStaticPart = true;
	StaticLevelCm = -1.e9f;
	UploadStatic();
	UE_LOG(LogTemp, Display, TEXT("GTFORDSTATIC %s: the basin past the cap as a static flat sheet at the level, %d x %d lattice cells (%.1f x %.1f m) about the field, %d quads outside the field's %d x %d, %d basin cells in it, %d beds sampled past the survey's, built in %.0f ms; its own texture %d x %d, no solver, no flow"),
		*GetName(), StaticNX, StaticNY, StaticNX * Basin.CellCm * 0.01f, StaticNY * Basin.CellCm * 0.01f, StaticQuads, Field.SizeX, Field.SizeY,
		BasinCellsHere, Sampled, (FPlatformTime::Seconds() - Started) * 1000.0, StaticNX, StaticNY);
}

void AGTWaterSheet::UploadStatic()
{
	if (!bStaticPart || !StaticTexture || !StaticTexture->GetResource())
	{
		return;
	}
	const float Level = GetLevelCm();
	// W5: a rise reaches the banks that touch the basin through the bed (4-connected), as the field's ShiftLevel does.
	if (Level > StaticLevelCm)
	{
		TArray<int32> Queue;
		for (int32 I = 0; I < StaticBasin.Num(); ++I)
		{
			if (StaticBasin[I])
			{
				Queue.Add(I);
			}
		}
		for (int32 Head = 0; Head < Queue.Num(); ++Head)
		{
			const int32 X = Queue[Head] % StaticNX;
			const int32 Y = Queue[Head] / StaticNX;
			const int32 NX[4] = { X - 1, X + 1, X, X };
			const int32 NY[4] = { Y, Y, Y - 1, Y + 1 };
			for (int32 K = 0; K < 4; ++K)
			{
				if (NX[K] < 0 || NY[K] < 0 || NX[K] >= StaticNX || NY[K] >= StaticNY)
				{
					continue;
				}
				const int32 J = NY[K] * StaticNX + NX[K];
				if (!StaticBasin[J] && StaticBedCm[J] < Level)
				{
					StaticBasin[J] = 1;
					Queue.Add(J);
				}
			}
		}
	}
	StaticLevelCm = Level;
	TArray<FFloat16Color>* Data = new TArray<FFloat16Color>();
	Data->SetNumUninitialized(StaticNX * StaticNY);
	for (int32 I = 0; I < StaticNX * StaticNY; ++I)
	{
		const bool bWet = StaticBasin[I] && StaticBedCm[I] < Level;
		(*Data)[I] = FFloat16Color(FLinearColor(bWet ? 0.f : StaticBedCm[I] - Level, bWet ? Level - StaticBedCm[I] : 0.f, 0.f, 0.f));
	}
	FUpdateTextureRegion2D* Region = new FUpdateTextureRegion2D(0, 0, 0, 0, StaticNX, StaticNY);
	StaticTexture->UpdateTextureRegions(0, 1, Region, StaticNX * sizeof(FFloat16Color), sizeof(FFloat16Color), reinterpret_cast<uint8*>(Data->GetData()),
		[Data](uint8*, const FUpdateTextureRegion2D* Regions)
		{
			delete Data;
			delete Regions;
		});
}
