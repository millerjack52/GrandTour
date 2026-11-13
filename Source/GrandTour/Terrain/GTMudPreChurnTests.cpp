// Ground relief GR1 item 4 (docs/GROUND_RELIEF_PLAN.md): GrandTour.Mud.PreChurn, CPU only (-NullRHI). The four L_MudVariants
// patches built as play builds them (UGTMudSubsystem::BuildPatches) with the strip's PreChurnScale (1 on each bog since GR1; GR1b's
// cosine old tracks: the filled share and no wall too; GR1c: 1 pair (2 over 40 m), 35-60 % of each present, 5-14 cm, puddles in
// Standard and Deep), then
// again, then at PreChurnScale 0 and with gt.Mud.PreChurn 0. Each row prints a "PreChurn: " line for Art/mud_shape_test.ps1.
#include "Terrain/GTMudPatch.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudPreChurnTest, "GrandTour.Mud.PreChurn",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace
{
	struct FPreChurnRow
	{
		uint32 Crc = 0;
		int32 Tracks = 0;
		float DepthLo = 0.f;
		float DepthHi = 0.f;
		float Hummock = 0.f;
		int32 WaterCells = 0;
		int32 Cells = 0;
		float RimMax = 0.f;
		float OuterMean = 0.f;    // mean |surface| of the cells within 25 cm of the rim
		float InnerMean = 0.f;    // mean |surface| of the cells at least 1.5 m in
		float SurfaceLo = 0.f;
		float SurfaceHi = 0.f;
		bool bFlat = false;       // every cell's height and lump exactly 0
		bool bPreChurned = false;
		int32 Kept = 0;
		int32 Moved = 0;
		int32 Planned = 0;
		int32 Flat = 0;
		float FilledLo = 0.f;
		float FilledShare = 0.f;
		int32 TroughCells = 0;
		float SlopeMax = 0.f;
		TArray<float> Present;    // GR1c: each pair's present share
		float PuddleShare = 0.f;
		float PuddleDepth = 0.f;
		int32 PuddleBasins = 0;   // GR2 phase B item 7
		int32 PuddleWet = 0;
		float PuddleWall = 0.f;
		float BoxLine = 0.f;
		FString Variant;
	};

	/** The four patches over Spec in a fresh Game world, their rows by section, the world torn down. */
	bool BuildRows(FAutomationTestBase& Test, const FGTTerrainSpec& Spec, const TCHAR* Tag, TArray<FPreChurnRow>& Out)
	{
		Out.Reset();
		Out.SetNum(4);
		UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, *FString::Printf(TEXT("GTMudPreChurnTest_%s"), Tag));
		if (!World)
		{
			return false;
		}
		FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
		Context.SetCurrentWorld(World);
		UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
		const int32 Count = Mud ? Mud->BuildPatches(Spec) : 0;
		Test.TestTrue(FString::Printf(TEXT("PreChurn: %s - four patches, one per section"), Tag), Count == 4);
		for (TActorIterator<AGTMudPatch> It(World); It; ++It)
		{
			const AGTMudPatch* Patch = *It;
			if (Patch->SectionIndex < 0 || Patch->SectionIndex >= 4)
			{
				continue;
			}
			FPreChurnRow& Row = Out[Patch->SectionIndex];
			const FGTMudField& Field = Patch->GetField();
			Row.Crc = Patch->FieldCrc();
			Row.Tracks = Patch->PreChurnTracks;
			Row.DepthLo = Patch->PreChurnDepthLoCm;
			Row.DepthHi = Patch->PreChurnDepthHiCm;
			Row.Hummock = Patch->PreChurnHummockCm;
			Row.WaterCells = Patch->PreChurnWaterCells;
			Row.Cells = Field.SizeX * Field.SizeY;
			Row.RimMax = Patch->PreChurnRimMaxCm;
			Row.bPreChurned = Patch->IsPreChurned();
			Row.Kept = Patch->PreChurnChunksKept;
			Row.Moved = Patch->PreChurnChunksMoved;
			Row.Planned = Patch->MudChunksPlanned;
			Row.Flat = Patch->PreChurnChunksFlat;
			Row.FilledLo = Patch->PreChurnFilledLoCm;
			Row.FilledShare = Patch->PreChurnFilledShare;
			Row.TroughCells = Patch->PreChurnTrackCells;
			Row.SlopeMax = Patch->PreChurnSlopeMaxDeg;
			Row.Present = Patch->PreChurnPresentShares;
			Row.PuddleShare = Patch->PreChurnPuddleShare;
			Row.PuddleDepth = Patch->PreChurnPuddleDepthHiCm;
			Row.PuddleBasins = Patch->PreChurnPuddleBasins;
			Row.PuddleWet = Patch->PreChurnPuddleWet;
			Row.PuddleWall = Patch->PreChurnPuddleWallDeg;
			Row.BoxLine = Patch->PreChurnBoxLineCm;
			Row.Variant = StaticEnum<EGTMudVariant>()->GetNameStringByValue(static_cast<int64>(Patch->MudVariant));
			const FBox2D Box = Field.Bounds();
			double Outer = 0.0;
			double Inner = 0.0;
			int32 NOuter = 0;
			int32 NInner = 0;
			Row.bFlat = true;
			for (int32 Index = 0; Index < Row.Cells; ++Index)
			{
				const float Surface = Field.SurfaceCm(Index);
				Row.bFlat &= Field.HeightCm[Index] == 0.f && Field.LumpCm[Index] == 0.f;
				Row.SurfaceLo = FMath::Min(Row.SurfaceLo, Surface);
				Row.SurfaceHi = FMath::Max(Row.SurfaceHi, Surface);
				const FVector2D C = Field.CellCentreCm(Index);
				const double Rim = FMath::Min(FMath::Min(C.X - Box.Min.X, Box.Max.X - C.X), FMath::Min(C.Y - Box.Min.Y, Box.Max.Y - C.Y));
				if (Rim < 25.0)
				{
					Outer += FMath::Abs(Surface);
					++NOuter;
				}
				else if (Rim >= 150.0)
				{
					Inner += FMath::Abs(Surface);
					++NInner;
				}
			}
			Row.OuterMean = NOuter > 0 ? static_cast<float>(Outer / NOuter) : 0.f;
			Row.InnerMean = NInner > 0 ? static_cast<float>(Inner / NInner) : 0.f;
		}
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
		return Count == 4;
	}
}

bool FGTMudPreChurnTest::RunTest(const FString& Parameters)
{
	IConsoleVariable* Switch = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Mud.PreChurn"));
	if (!TestNotNull(TEXT("PreChurn: the gt.Mud.PreChurn switch"), Switch))
	{
		return false;
	}
	const int32 SwitchWas = Switch->GetInt();
	Switch->Set(1, ECVF_SetByConsole);
	// The strip's own spec (DA_MudVariants), its bogs at PreChurnScale 1 whatever the asset says (the asset's own numbers are
	// reported as the strip's baseline below); a hand-built one like it when the asset is missing.
	const EGTMudVariant Variants[4] = { EGTMudVariant::Firm, EGTMudVariant::Standard, EGTMudVariant::Deep, EGTMudVariant::Stony };
	FGTTerrainSpec Spec;
	const UGTTerrainSpecAsset* StripSpec = LoadObject<UGTTerrainSpecAsset>(nullptr, TEXT("/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants.DA_MudVariants"));
	bool bStrip = StripSpec && StripSpec->Spec.Sections.Num() == 4;
	for (int32 Index = 0; bStrip && Index < 4; ++Index)
	{
		bStrip = StripSpec->Spec.Sections[Index].Kind == EGTRouteSectionKind::Mud && StripSpec->Spec.Sections[Index].MudVariant == Variants[Index];
	}
	if (bStrip)
	{
		Spec = StripSpec->Spec;
	}
	else
	{
		AddWarning(TEXT("PreChurn: DA_MudVariants missing or changed - a hand-built spec like it"));
		Spec.RouteM = { FVector2D(0.0, 0.0), FVector2D(215.0, 0.0) };
		Spec.RoadHalfWidthM = 3.f;
		Spec.Sections.Reset();
		for (int32 Index = 0; Index < 4; ++Index)
		{
			FGTRouteSection Section;
			Section.StartM = 30.f + 45.f * Index;
			Section.EndM = Section.StartM + 25.f;
			Section.Kind = EGTRouteSectionKind::Mud;
			Section.MudVariant = Variants[Index];
			Spec.Sections.Add(Section);
		}
	}
	TArray<float> AssetScales;
	for (const FGTRouteSection& Section : Spec.Sections)
	{
		AssetScales.Add(Section.Deform.PreChurnScale);
	}
	TArray<FPreChurnRow> First;
	TArray<FPreChurnRow> Second;
	TArray<FPreChurnRow> Zero;
	TArray<FPreChurnRow> Off;
	TArray<FPreChurnRow> Strip;
	if (bStrip)
	{
		BuildRows(*this, Spec, TEXT("asset"), Strip);   // the strip as the asset has it: its CRCs are the new strip baseline
	}
	FGTTerrainSpec On = Spec;
	for (FGTRouteSection& Section : On.Sections)
	{
		Section.Deform.PreChurnScale = 1.f;
	}
	FGTTerrainSpec Flat = Spec;
	for (FGTRouteSection& Section : Flat.Sections)
	{
		Section.Deform.PreChurnScale = 0.f;
	}
	BuildRows(*this, On, TEXT("first"), First);
	BuildRows(*this, On, TEXT("second"), Second);
	BuildRows(*this, Flat, TEXT("scale0"), Zero);
	Switch->Set(0, ECVF_SetByConsole);
	BuildRows(*this, On, TEXT("switch0"), Off);
	Switch->Set(SwitchWas, ECVF_SetByConsole);
	const AGTMudPatch* Defaults = GetDefault<AGTMudPatch>();
	const float DepthLo = Defaults->PreChurnDepthMinCm;
	const float DepthHi = Defaults->PreChurnDepthMaxCm;   // GR1c: the soft deepening stays within the range
	for (int32 Index = 0; Index < 4; ++Index)
	{
		const FPreChurnRow& R = First[Index];
		const TCHAR* Name = *R.Variant;
		FString Shares;
		for (const float Share : R.Present)
		{
			Shares += FString::Printf(TEXT("%s%.1f %%"), Shares.IsEmpty() ? TEXT("") : TEXT(", "), 100.f * Share);
		}
		AddInfo(FString::Printf(TEXT("PreChurn: %s - CRC %08x, %d old rut pairs over %.1f m of route, present %s, depth asked %.1f-%.1f cm, filled to %.1f cm over %.1f %% of the length, puddles over %.1f %% of the present length (cut up to %.1f cm into the settled floor), %d trough cells, steepest %.1f deg, hummocks +-%.1f cm at most, surface %.1f..%.1f cm, ")
			TEXT("water %d of %d cells (%.2f %%), rim %.3f cm at most, mean |surface| %.2f cm within 25 cm of the rim vs %.2f cm 1.5 m in; chunks %d planned (%d without the pre-churn, of whose places %d kept, %d in an old rut or bank)"),
			Name, R.Crc, R.Tracks, R.BoxLine / 100.f, *Shares, R.DepthLo, R.DepthHi, R.FilledLo, 100.f * R.FilledShare, 100.f * R.PuddleShare, R.PuddleDepth, R.TroughCells, R.SlopeMax, R.Hummock, R.SurfaceLo, R.SurfaceHi,
			R.WaterCells, R.Cells, R.Cells > 0 ? 100.f * R.WaterCells / R.Cells : 0.f, R.RimMax, R.OuterMean, R.InnerMean, R.Planned, R.Flat, R.Kept, R.Moved));
		TestTrue(FString::Printf(TEXT("PreChurn: %s pre-churned at scale 1"), Name), R.bPreChurned);
		// GR1c: 1 pair, 2 where the route runs more than 40 m through the box.
		const int32 Want = R.BoxLine > Defaults->PreChurnLongPatchCm ? Defaults->PreChurnPairsLong : Defaults->PreChurnPairs;
		TestTrue(FString::Printf(TEXT("PreChurn: %s - %d old rut pair(s) over %.1f m (%d)"), Name, Want, R.BoxLine / 100.f, R.Tracks), R.Tracks == Want && R.Present.Num() == Want);
		for (int32 Pair = 0; Pair < R.Present.Num(); ++Pair)
		{
			TestTrue(FString::Printf(TEXT("PreChurn: %s - pair %d present over 35-60 %% of its length (%.1f)"), Name, Pair, 100.f * R.Present[Pair]),
				R.Present[Pair] >= Defaults->PreChurnPresentMin - 0.005f && R.Present[Pair] <= Defaults->PreChurnPresentMax + 0.005f);
		}
		TestTrue(FString::Printf(TEXT("PreChurn: %s - the depths asked within %.0f-%.1f cm (%.1f-%.1f)"), Name, DepthLo, DepthHi, R.DepthLo, R.DepthHi),
			R.DepthLo >= DepthLo - 0.01f && R.DepthHi <= DepthHi + 0.01f && R.DepthHi - R.DepthLo >= 4.f);
		TestTrue(FString::Printf(TEXT("PreChurn: %s - the ruts reach at least %.0f cm down (%.1f cm)"), Name, DepthLo, R.SurfaceLo), R.SurfaceLo <= -DepthLo);
		// GR1c: the puddles (every bog here has a water table): the deepest 20-30 % of each line's present length, so rut water stands in
		// Standard and Deep (GR1b had lost Deep's).
		TestTrue(FString::Printf(TEXT("PreChurn: %s - puddle runs over 15-35 %% of the present length (%.1f)"), Name, 100.f * R.PuddleShare), R.PuddleShare >= 0.15f && R.PuddleShare <= 0.35f);
		if (R.Variant == TEXT("Standard") || R.Variant == TEXT("Deep"))
		{
			TestTrue(FString::Printf(TEXT("PreChurn: %s - water-holding cells (%d)"), Name, R.WaterCells), R.WaterCells > 0);
		}
		// GR2 phase B item 7: the puddles are cosine basins inside the tracks, their own walls at most 30 deg (a cell's central difference).
		AddInfo(FString::Printf(TEXT("PreChurn: %s - %d puddle basins (%d with a floor under the table), cut up to %.1f cm, their steepest cell %.1f deg, %d water-holding cells"), Name, R.PuddleBasins, R.PuddleWet, R.PuddleDepth, R.PuddleWall, R.WaterCells));
		TestTrue(FString::Printf(TEXT("PreChurn: %s - puddle basins (%d)"), Name, R.PuddleBasins), R.PuddleBasins > 0);
		TestTrue(FString::Printf(TEXT("PreChurn: %s - the basins' walls at most 30 deg, their edges included (%.1f)"), Name, R.PuddleWall), R.PuddleWall <= 30.5f);
		// GR1b: 20-40 % of each line filled back to 30-60 % of its depth (the share measured over the box, so +-5 %), no vertical wall.
		TestTrue(FString::Printf(TEXT("PreChurn: %s - the filled share within 15-45 %% (%.1f)"), Name, 100.f * R.FilledShare), R.FilledShare >= 0.15f && R.FilledShare <= 0.45f);
		TestTrue(FString::Printf(TEXT("PreChurn: %s - filled no shallower than 40 %% of the shallowest depth (%.2f cm)"), Name, R.FilledLo),
			R.FilledLo >= 0.4f * DepthLo - 0.01f && R.FilledLo < R.DepthLo);
		TestTrue(FString::Printf(TEXT("PreChurn: %s - no wall: the steepest trough cell under 60 deg (%.1f)"), Name, R.SlopeMax), R.SlopeMax > 0.f && R.SlopeMax < 60.f);
		TestTrue(FString::Printf(TEXT("PreChurn: %s - the hummocks' most within 5-20 cm (%.1f)"), Name, R.Hummock), R.Hummock >= 5.f && R.Hummock <= 20.01f);
		TestTrue(FString::Printf(TEXT("PreChurn: %s - the rim faded (at most 0.5 cm in the outer cell, %.3f; within 25 cm a quarter of 1.5 m in at most, %.2f vs %.2f)"),
			Name, R.RimMax, R.OuterMean, R.InnerMean), R.RimMax <= 0.5f && R.OuterMean <= 0.25f * FMath::Max(0.01f, R.InnerMean));
		TestTrue(FString::Printf(TEXT("PreChurn: %s - deterministic (CRC %08x twice)"), Name, R.Crc), Second.IsValidIndex(Index) && Second[Index].Crc == R.Crc);
		TestTrue(FString::Printf(TEXT("PreChurn: %s - PreChurnScale 0 the flat field"), Name), Zero.IsValidIndex(Index) && Zero[Index].bFlat && !Zero[Index].bPreChurned);
		TestTrue(FString::Printf(TEXT("PreChurn: %s - gt.Mud.PreChurn 0 the flat field"), Name), Off.IsValidIndex(Index) && Off[Index].bFlat && !Off[Index].bPreChurned);
		if (Strip.IsValidIndex(Index))
		{
			AddInfo(FString::Printf(TEXT("PreChurn: the strip baseline - %s at the asset's PreChurnScale %.2f: CRC %08x"), Name, AssetScales[Index], Strip[Index].Crc));
		}
	}
	return true;
}
#endif
