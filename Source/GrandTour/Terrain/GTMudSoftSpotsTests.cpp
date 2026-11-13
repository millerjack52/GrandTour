// MudRunner MR4 (docs/MUDRUNNER_LESSONS_PLAN.md MR4 execution block item 5): GrandTour.Mud.SoftSpots, CPU only (-NullRHI). The
// four L_MudVariants patches built as play builds them (UGTMudSubsystem::BuildPatches); each row prints a "SoftSpots: " line for
// Art/mud_shape_test.ps1.
#include "Terrain/GTMudPatch.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTSurfacePhysMaterial.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Vehicle/GTTractionComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudSoftSpotsTest, "GrandTour.Mud.SoftSpots",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace
{
	/** One grid's soft-spot numbers: the share over 0.6, the blobs (8-connected over 0.6, at least 1 m2) and the outer 0.5 m's most. */
	struct FSoftStats
	{
		double Share = 0.0;
		int32 SoftCells = 0;
		// The interior (cells whose centre is at least 2 m from the edge: the percentile remap's own cells) and its share over 0.6.
		double InteriorShare = 0.0;
		int32 InteriorSoft = 0;
		int32 InteriorCells = 0;
		int32 Cells = 0;
		TArray<float> DiameterM;   // per blob, sqrt(4 A / pi)
		TArray<float> Shape;       // per blob, P^2 / (4 pi A), cell edges
		TArray<FVector2D> CentroidM;
		float RimMax = 0.f;        // the most S of a cell whose centre is within 50 cm of the grid's edge
	};

	float Median(TArray<float> Values)
	{
		if (Values.Num() == 0)
		{
			return 0.f;
		}
		Values.Sort();
		const int32 Mid = Values.Num() / 2;
		return (Values.Num() % 2) ? Values[Mid] : 0.5f * (Values[Mid - 1] + Values[Mid]);
	}

	/** The CV of the blob centroids' nearest-neighbour distances (population std / mean); 0 with fewer than two. */
	float NearestCV(const TArray<FVector2D>& Points)
	{
		if (Points.Num() < 2)
		{
			return 0.f;
		}
		TArray<double> Nearest;
		for (int32 I = 0; I < Points.Num(); ++I)
		{
			double Best = TNumericLimits<double>::Max();
			for (int32 J = 0; J < Points.Num(); ++J)
			{
				if (I != J)
				{
					Best = FMath::Min(Best, FVector2D::Distance(Points[I], Points[J]));
				}
			}
			Nearest.Add(Best);
		}
		double Mean = 0.0;
		for (const double D : Nearest)
		{
			Mean += D;
		}
		Mean /= Nearest.Num();
		double Var = 0.0;
		for (const double D : Nearest)
		{
			Var += (D - Mean) * (D - Mean);
		}
		Var /= Nearest.Num();
		return Mean > 0.0 ? static_cast<float>(FMath::Sqrt(Var) / Mean) : 0.f;
	}

	FSoftStats SoftStats(const TArray<float>& S, int32 SX, int32 SY, float CellCm)
	{
		FSoftStats Out;
		Out.Cells = SX * SY;
		TArray<int32> Label;
		Label.Init(-1, Out.Cells);
		const int32 MinCells = FMath::CeilToInt(10000.f / (CellCm * CellCm));   // 1 m2
		TArray<int32> Stack;
		int32 Next = 0;
		for (int32 Start = 0; Start < Out.Cells; ++Start)
		{
			const int32 X = Start % SX;
			const int32 Y = Start / SX;
			const float CX = (X + 0.5f) * CellCm;
			const float CY = (Y + 0.5f) * CellCm;
			const float EdgeCm = FMath::Min(FMath::Min(CX, SX * CellCm - CX), FMath::Min(CY, SY * CellCm - CY));
			if (EdgeCm < 50.f)
			{
				Out.RimMax = FMath::Max(Out.RimMax, S[Start]);
			}
			if (EdgeCm >= 200.f)
			{
				++Out.InteriorCells;
				Out.InteriorSoft += S[Start] > 0.6f ? 1 : 0;
			}
			if (S[Start] <= 0.6f)
			{
				continue;
			}
			++Out.SoftCells;
			if (Label[Start] >= 0)
			{
				continue;
			}
			// A new blob: 8-connected flood, its cells, its cell-edge perimeter and its centroid.
			const int32 Id = Next++;
			Label[Start] = Id;
			Stack.Reset();
			Stack.Add(Start);
			int64 Area = 0;
			int64 Perimeter = 0;
			double SumX = 0.0;
			double SumY = 0.0;
			while (Stack.Num() > 0)
			{
				const int32 Index = Stack.Pop(EAllowShrinking::No);
				const int32 IX = Index % SX;
				const int32 IY = Index / SX;
				++Area;
				SumX += IX + 0.5;
				SumY += IY + 0.5;
				const int32 Side[4][2] = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } };
				for (const auto& D : Side)
				{
					const int32 NX = IX + D[0];
					const int32 NY = IY + D[1];
					Perimeter += (NX < 0 || NY < 0 || NX >= SX || NY >= SY || S[NY * SX + NX] <= 0.6f) ? 1 : 0;
				}
				for (int32 DY = -1; DY <= 1; ++DY)
				{
					for (int32 DX = -1; DX <= 1; ++DX)
					{
						const int32 NX = IX + DX;
						const int32 NY = IY + DY;
						if ((DX || DY) && NX >= 0 && NY >= 0 && NX < SX && NY < SY && S[NY * SX + NX] > 0.6f && Label[NY * SX + NX] < 0)
						{
							Label[NY * SX + NX] = Id;
							Stack.Add(NY * SX + NX);
						}
					}
				}
			}
			if (Area >= MinCells)
			{
				const double AreaM2 = Area * CellCm * CellCm * 1.e-4;
				Out.DiameterM.Add(static_cast<float>(FMath::Sqrt(4.0 * AreaM2 / UE_PI)));
				Out.Shape.Add(static_cast<float>(double(Perimeter) * double(Perimeter) / (4.0 * UE_PI * double(Area))));
				Out.CentroidM.Add(FVector2D(SumX / Area, SumY / Area) * CellCm * 0.01);
			}
		}
		Out.Share = Out.Cells > 0 ? double(Out.SoftCells) / Out.Cells : 0.0;
		Out.InteriorShare = Out.InteriorCells > 0 ? double(Out.InteriorSoft) / Out.InteriorCells : 0.0;
		return Out;
	}
}

bool FGTMudSoftSpotsTest::RunTest(const FString& Parameters)
{
	IConsoleVariable* Switch = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Mud.SoftSpots"));
	if (!TestNotNull(TEXT("SoftSpots: the gt.Mud.SoftSpots switch"), Switch))
	{
		return false;
	}
	// Set by console so a run started with the switch at 0 (-ExecCmds) is overridden here and restored after.
	const int32 SwitchWas = Switch->GetInt();
	Switch->Set(1, ECVF_SetByConsole);

	struct FRow
	{
		EGTMudVariant Variant;
		const TCHAR* Name;
		float Amplitude;
	};
	// The execution block's proposals (Standard 1 with no profile), in the strip's order.
	const FRow Rows[4] = { { EGTMudVariant::Firm, TEXT("Firm"), 0.5f }, { EGTMudVariant::Standard, TEXT("Standard"), 1.f },
		{ EGTMudVariant::Deep, TEXT("Deep"), 0.6f }, { EGTMudVariant::Stony, TEXT("Stony"), 0.6f } };
	// The strip's own spec (DA_MudVariants, Art/Unreal/setup_mud_variants.py), so the patches are L_MudVariants' (their size, their
	// section indices and so their seeds); the Variants test's hand-built spec when the asset is missing.
	FGTTerrainSpec Spec;
	const UGTTerrainSpecAsset* StripSpec = LoadObject<UGTTerrainSpecAsset>(nullptr, TEXT("/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants.DA_MudVariants"));
	bool bStrip = StripSpec && StripSpec->Spec.Sections.Num() == 4;
	for (int32 Index = 0; bStrip && Index < 4; ++Index)
	{
		bStrip = StripSpec->Spec.Sections[Index].Kind == EGTRouteSectionKind::Mud && StripSpec->Spec.Sections[Index].MudVariant == Rows[Index].Variant;
	}
	if (bStrip)
	{
		Spec = StripSpec->Spec;
		// Ground relief GR1: the fixture keeps the flat field (the strip's bogs are pre-churned since GR1).
		for (FGTRouteSection& Section : Spec.Sections)
		{
			Section.Deform.PreChurnScale = 0.f;
		}
	}
	else
	{
		AddWarning(TEXT("SoftSpots: DA_MudVariants missing or changed - the hand-built spec of GrandTour.Mud.Variants (its patches are not the strip's size)"));
		Spec.RouteM = { FVector2D(0.0, 0.0), FVector2D(215.0, 0.0) };
		Spec.Sections.Reset();
		for (int32 Index = 0; Index < 4; ++Index)
		{
			FGTRouteSection Section;
			Section.StartM = 30.f + 45.f * Index;
			Section.EndM = Section.StartM + 25.f;
			Section.Kind = EGTRouteSectionKind::Mud;
			Section.MudVariant = Rows[Index].Variant;
			Spec.Sections.Add(Section);
		}
	}
	AddInfo(FString::Printf(TEXT("SoftSpots: the spec - %s"), bStrip ? TEXT("DA_MudVariants (L_MudVariants' own)") : TEXT("the hand-built one")));
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("GTMudSoftSpotsTest"));
	if (!TestNotNull(TEXT("SoftSpots: a Game world"), World))
	{
		Switch->Set(SwitchWas, ECVF_SetByConsole);
		return false;
	}
	FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
	Context.SetCurrentWorld(World);
	UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	const int32 Count = Mud ? Mud->BuildPatches(Spec) : 0;
	TestTrue(TEXT("SoftSpots: four patches, one per section"), Count == 4);
	AGTMudPatch* Patches[4] = { nullptr, nullptr, nullptr, nullptr };
	for (TActorIterator<AGTMudPatch> It(World); It; ++It)
	{
		if (It->SectionIndex >= 0 && It->SectionIndex < 4)
		{
			Patches[It->SectionIndex] = *It;
		}
	}

	// ---- 1. the field per patch: scope, amplitude, determinism, the statistics at its amplitude and at amplitude 1 -----------
	TArray<float> PoolDiameter;
	TArray<float> PoolShape;
	int64 PoolSoft = 0;    // the interior's (main session, 2026-10-09: the gate is on the interior cells)
	int64 PoolCells = 0;
	int64 PoolWholeSoft = 0;
	int64 PoolWholeCells = 0;
	TArray<TArray<uint8>> LayerAtOne;
	LayerAtOne.SetNum(4);
	for (int32 Index = 0; Index < 4; ++Index)
	{
		const FRow& Row = Rows[Index];
		AGTMudPatch* Patch = Patches[Index];
		if (!TestNotNull(FString::Printf(TEXT("SoftSpots: %s - a patch"), Row.Name), Patch))
		{
			continue;
		}
		const FGTMudField& Field = Patch->GetField();
		const int32 SX = Field.SizeX;
		const int32 SY = Field.SizeY;
		const int32 Seed = AGTMudPatch::SoftSpotSeed(Patch->SectionIndex);
		TestTrue(FString::Printf(TEXT("SoftSpots: %s - in scope (no profile, the Mud medium, S built)"), Row.Name), Patch->HasSoftSpots());
		TestTrue(FString::Printf(TEXT("SoftSpots: %s - amplitude %.2f"), Row.Name, Row.Amplitude), FMath::Abs(Patch->SoftSpotAmplitude - Row.Amplitude) <= 1.e-6f);
		// The same seed, the same S, byte for byte; and the patch's own S is the generator's (read back at the cell centres, exact).
		TArray<float> Own;
		TArray<float> Again;
		AGTMudPatch::BuildSoftness(Own, SX, SY, Field.CellCm, Field.OriginCm, Seed, Patch->SoftSpotAmplitude);
		AGTMudPatch::BuildSoftness(Again, SX, SY, Field.CellCm, Field.OriginCm, Seed, Patch->SoftSpotAmplitude);
		const bool bSame = Own.Num() == SX * SY && Own.Num() == Again.Num() && FMemory::Memcmp(Own.GetData(), Again.GetData(), Own.Num() * sizeof(float)) == 0;
		float ReadBack = 0.f;
		double SumSink = 0.0;
		double SumFriction = 0.0;
		for (int32 Cell = 0; Cell < Own.Num(); ++Cell)
		{
			const FVector2D Centre = Field.CellCentreCm(Cell);
			ReadBack = FMath::Max(ReadBack, FMath::Abs(Patch->SoftnessAt(Centre) - Own[Cell]));
			const FVector2D Scales = Patch->SoftScalesAt(Centre);
			SumSink += Scales.X;
			SumFriction += Scales.Y;
		}
		TestTrue(FString::Printf(TEXT("SoftSpots: %s - the same seed gives the same S byte for byte, and the patch holds it"), Row.Name), bSame && ReadBack == 0.f);
		const double MeanSink = Own.Num() ? SumSink / Own.Num() : 0.0;
		const double MeanFriction = Own.Num() ? SumFriction / Own.Num() : 0.0;
		TestTrue(FString::Printf(TEXT("SoftSpots: %s - mean SinkScale %.4f and FrictionScale %.4f each 1 within 2 %%"), Row.Name, MeanSink, MeanFriction),
			FMath::Abs(MeanSink - 1.0) <= 0.02 && FMath::Abs(MeanFriction - 1.0) <= 0.02);
		const FSoftStats At = SoftStats(Own, SX, SY, Field.CellCm);
		TestTrue(FString::Printf(TEXT("SoftSpots: %s - S at most 0.45 in the outer 0.5 m (most %.3f)"), Row.Name, At.RimMax), At.RimMax <= 0.45f);
		// At amplitude 1 (the generator's own spread, this patch's seed), pooled over the four for the gates.
		TArray<float> One;
		AGTMudPatch::BuildSoftness(One, SX, SY, Field.CellCm, Field.OriginCm, Seed, 1.f);
		const FSoftStats AtOne = SoftStats(One, SX, SY, Field.CellCm);
		PoolDiameter.Append(AtOne.DiameterM);
		PoolShape.Append(AtOne.Shape);
		PoolSoft += AtOne.InteriorSoft;
		PoolCells += AtOne.InteriorCells;
		PoolWholeSoft += AtOne.SoftCells;
		PoolWholeCells += AtOne.Cells;
		LayerAtOne[Index] = Patch->GetLayerBytes();
		// The layer's G is S x 255 with the switch on.
		const TArray<uint8> Bytes = Patch->GetSoftnessBytes();
		bool bLayerG = Bytes.Num() == SX * SY && LayerAtOne[Index].Num() == 2 * SX * SY;
		for (int32 Cell = 0; bLayerG && Cell < Bytes.Num(); ++Cell)
		{
			bLayerG = LayerAtOne[Index][2 * Cell + 1] == Bytes[Cell];
		}
		TestTrue(FString::Printf(TEXT("SoftSpots: %s - the layer's G is S x 255 with the switch on"), Row.Name), bLayerG);
		AddInfo(FString::Printf(TEXT("SoftSpots: %s (section %d, seed %d, %d x %d cells, amplitude %.2f) - soft share %.1f %% (interior, 2 m in: %.1f %%), blobs %d, median equivalent diameter %.2f m, median shape factor %.2f, nearest-neighbour CV %.2f, outer 0.5 m max S %.3f; mean SinkScale %.4f FrictionScale %.4f (patch means of the lerps %.4f / %.4f); at amplitude 1: share %.1f %% (interior %.1f %%), blobs %d, median diameter %.2f m, median shape %.2f, NN CV %.2f, outer 0.5 m max %.3f"),
			Row.Name, Patch->SectionIndex, Seed, SX, SY, Patch->SoftSpotAmplitude, 100.0 * At.Share, 100.0 * At.InteriorShare, At.DiameterM.Num(), Median(At.DiameterM), Median(At.Shape), NearestCV(At.CentroidM), At.RimMax,
			MeanSink, MeanFriction, Patch->SoftMeanSink, Patch->SoftMeanFriction,
			100.0 * AtOne.Share, 100.0 * AtOne.InteriorShare, AtOne.DiameterM.Num(), Median(AtOne.DiameterM), Median(AtOne.Shape), NearestCV(AtOne.CentroidM), AtOne.RimMax));
	}
	const double PoolShare = PoolCells > 0 ? double(PoolSoft) / PoolCells : 0.0;
	const double PoolWholeShare = PoolWholeCells > 0 ? double(PoolWholeSoft) / PoolWholeCells : 0.0;
	const float PoolDiameterMedian = Median(PoolDiameter);
	const float PoolShapeMedian = Median(PoolShape);
	AddInfo(FString::Printf(TEXT("SoftSpots: amplitude 1, the four seeds pooled - soft share of the interior (2 m in) %.1f %%, of the whole patches %.1f %%, %d blobs, median equivalent diameter %.2f m, median shape factor %.2f"),
		100.0 * PoolShare, 100.0 * PoolWholeShare, PoolDiameter.Num(), PoolDiameterMedian, PoolShapeMedian));
	TestTrue(FString::Printf(TEXT("SoftSpots: the interior's soft share at amplitude 1 is 20-30 %% (%.1f %%)"), 100.0 * PoolShare), PoolShare >= 0.20 && PoolShare <= 0.30);
	TestTrue(FString::Printf(TEXT("SoftSpots: median blob equivalent diameter 2-6 m at amplitude 1 (%.2f m)"), PoolDiameterMedian), PoolDiameterMedian >= 2.f && PoolDiameterMedian <= 6.f);
	TestTrue(FString::Printf(TEXT("SoftSpots: median blob shape factor at least 1.6 at amplitude 1 (%.2f)"), PoolShapeMedian), PoolShapeMedian >= 1.6f);

	// ---- 2. the stroke: two CPU strokes with the traction's own sinkage numbers, over S 0.8 and over S 0.2 ------------------
	if (AGTMudPatch* Patch = Patches[1])   // Standard
	{
		FGTMudField& Field = Patch->GetField();
		const UGTSurfacePhysMaterial* MudRow = LoadObject<UGTSurfacePhysMaterial>(nullptr, TEXT("/Game/GrandTour/Terrain/Surfaces/PM_Mud.PM_Mud"));
		const float BaseRate = MudRow ? MudRow->SinkageRate : 0.05f;
		const float BaseCap = MudRow ? MudRow->MaxSinkage : 0.40f;
		// The cell nearest each S, at least 1.5 m inside the box (the stroke and its shoulders stay in the patch).
		auto Nearest = [&](float Want)
		{
			int32 Best = INDEX_NONE;
			float BestError = TNumericLimits<float>::Max();
			for (int32 Cell = 0; Cell < Field.SizeX * Field.SizeY; ++Cell)
			{
				const int32 X = Cell % Field.SizeX;
				const int32 Y = Cell / Field.SizeX;
				const float Edge = FMath::Min(FMath::Min(X + 0.5f, Field.SizeX - X - 0.5f), FMath::Min(Y + 0.5f, Field.SizeY - Y - 0.5f)) * Field.CellCm;
				const float Error = FMath::Abs(Patch->SoftnessAt(Field.CellCentreCm(Cell)) - Want);
				if (Edge >= 150.f && Error < BestError)
				{
					BestError = Error;
					Best = Cell;
				}
			}
			return Best;
		};
		const int32 SoftCell = Nearest(0.8f);
		const int32 FirmCell = Nearest(0.2f);
		struct FStroke
		{
			float S = 0.f;
			float SinkScale = 1.f;
			float DepthCm = 0.f;
			float RutCm = 0.f;
		};
		auto Stroke = [&](int32 Cell)
		{
			FStroke Out;
			const FVector2D Centre = Field.CellCentreCm(Cell);
			Out.S = Patch->SoftnessAt(Centre);
			Out.SinkScale = static_cast<float>(Patch->SoftScalesAt(Centre).X);
			float Rate = 0.f;
			float Cap = 0.f;
			UGTTractionComponent::PatchSinkage(BaseRate, BaseCap, 1.f, Patch->SinkageRateScale, Patch->MaxSinkageScale, Out.SinkScale, Rate, Cap);
			Out.DepthCm = Cap * 100.f;   // a wheel at its cap stamps Sinkage x 100 (UGTTractionComponent::StampMud)
			Field.StampWheel(Centre - FVector2D(25.0, 0.0), Centre + FVector2D(25.0, 0.0), 28.f, Out.DepthCm, FVector2D(1.0, 0.0), 0.f);
			Out.RutCm = -Field.HeightAt(Centre);
			return Out;
		};
		if (TestTrue(TEXT("SoftSpots: stroke cells found"), SoftCell != INDEX_NONE && FirmCell != INDEX_NONE))
		{
			// The field's own floor noise and pockets left on (reported), then off (the gate: the soft spot's part alone).
			const FStroke SoftNoisy = Stroke(SoftCell);
			const FStroke FirmNoisy = Stroke(FirmCell);
			const float RutVariation = Field.RutDepthVariation;
			const float FloorNoise = Field.FloorNoiseCm;
			Patch->ResetFieldForTest();
			Field.RutDepthVariation = 0.f;
			Field.FloorNoiseCm = 0.f;
			const FStroke Soft = Stroke(SoftCell);
			const FStroke Firm = Stroke(FirmCell);
			Field.RutDepthVariation = RutVariation;
			Field.FloorNoiseCm = FloorNoise;
			Patch->ResetFieldForTest();
			const float RutRatio = Firm.RutCm > 0.f ? Soft.RutCm / Firm.RutCm : 0.f;
			const float SinkRatio = Firm.SinkScale > 0.f ? Soft.SinkScale / Firm.SinkScale : 0.f;
			const float NoisyRatio = FirmNoisy.RutCm > 0.f ? SoftNoisy.RutCm / FirmNoisy.RutCm : 0.f;
			AddInfo(FString::Printf(TEXT("SoftSpots: stroke (Standard, the Mud row's MaxSinkage %.3f m%s) - soft cell S %.3f SinkScale %.4f depth %.2f cm rut %.2f cm; firm cell S %.3f SinkScale %.4f depth %.2f cm rut %.2f cm; rut ratio %.4f against SinkScale ratio %.4f (%.2f %% apart); with the field's floor noise and pockets on: ruts %.2f / %.2f cm, ratio %.4f"),
				BaseCap, MudRow ? TEXT("") : TEXT(" - PM_Mud not loaded, 0.40 assumed"), Soft.S, Soft.SinkScale, Soft.DepthCm, Soft.RutCm, Firm.S, Firm.SinkScale, Firm.DepthCm, Firm.RutCm,
				RutRatio, SinkRatio, SinkRatio > 0.f ? 100.f * FMath::Abs(RutRatio / SinkRatio - 1.f) : 0.f, SoftNoisy.RutCm, FirmNoisy.RutCm, NoisyRatio));
			TestTrue(FString::Printf(TEXT("SoftSpots: the rut ratio %.4f equals the SinkScale ratio %.4f within 5 %%"), RutRatio, SinkRatio),
				SinkRatio > 0.f && FMath::Abs(RutRatio / SinkRatio - 1.f) <= 0.05f);
		}
	}

	// ---- 3. the switch: 0 - both scales exactly 1 and G all 0 (R untouched); back to 1 - G is S again ---------------------
	Switch->Set(0, ECVF_SetByConsole);
	for (int32 Index = 0; Index < 4; ++Index)
	{
		AGTMudPatch* Patch = Patches[Index];
		if (!Patch)
		{
			continue;
		}
		Patch->ApplySoftSwitch(Switch->GetInt() != 0);   // what the patch's tick does when the switch flips
		const FGTMudField& Field = Patch->GetField();
		bool bOnes = true;
		for (int32 Cell = 0; bOnes && Cell < Field.SizeX * Field.SizeY; ++Cell)
		{
			bOnes = Patch->SoftScalesAt(Field.CellCentreCm(Cell)) == FVector2D(1.0, 1.0);
		}
		const TArray<uint8>& Layer = Patch->GetLayerBytes();
		bool bZeroG = Layer.Num() == LayerAtOne[Index].Num() && Layer.Num() > 0;
		for (int32 Byte = 0; bZeroG && Byte < Layer.Num(); Byte += 2)
		{
			bZeroG = Layer[Byte + 1] == 0 && Layer[Byte] == LayerAtOne[Index][Byte];
		}
		TestTrue(FString::Printf(TEXT("SoftSpots: %s with the switch 0 - both scales exactly 1 at every cell"), Rows[Index].Name), bOnes);
		TestTrue(FString::Printf(TEXT("SoftSpots: %s with the switch 0 - the layer's G all 0, R unchanged"), Rows[Index].Name), bZeroG);
	}
	Switch->Set(1, ECVF_SetByConsole);
	for (int32 Index = 0; Index < 4; ++Index)
	{
		if (AGTMudPatch* Patch = Patches[Index])
		{
			Patch->ApplySoftSwitch(true);
			TestTrue(FString::Printf(TEXT("SoftSpots: %s back at 1 - the layer as before"), Rows[Index].Name), Patch->GetLayerBytes() == LayerAtOne[Index]);
		}
	}
	AddInfo(TEXT("SoftSpots: the scope predicate - !bHasProfile && Medium == EGTDeformMedium::Mud (an unprofiled bog's or an LM5b variant's patch)"));
	Switch->Set(SwitchWas, ECVF_SetByConsole);
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}
#endif
