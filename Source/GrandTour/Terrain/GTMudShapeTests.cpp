#include "Terrain/GTMudField.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/Crc.h"
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Terrain/GTMudSubsystem.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudSoftShapeTest, "GrandTour.Mud.SoftShoulders",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTMudSoftShapeTest::RunTest(const FString& Parameters)
{
	FGTMudField A, B;
	const FBox2D Bounds(FVector2D(-200, -350), FVector2D(1200, 350));
	A.Init(Bounds, 12.5f);
	B.Init(Bounds, 12.5f);
	auto Pass = [](FGTMudField& Field, bool Reverse)
	{
		for (int32 I = 0; I < 200; ++I)
		{
			const float X = Reverse ? 1000.f - I * 5.f : I * 5.f;
			const float Next = X + (Reverse ? -5.f : 5.f);
			Field.StampWheel(FVector2D(X, 0), FVector2D(Next, 0), 28.f, 40.f,
				FVector2D(Reverse ? -1 : 1, 0), I * 5.f);
		}
	};
	Pass(A, false);
	Pass(B, false);
	TestTrue(TEXT("World-seeded shape is deterministic"), A.HeightCm == B.HeightCm);
	float WorstStep = 0.f, MinWidth = 1000.f, MaxWidth = 0.f, MinCore = 0.f, MaxCore = -100.f;
	for (float X = 100; X <= 900; X += 25)
	{
		float Width = 0.f;
		int32 SlopeSamples = 0;
		for (float Y = -100; Y <= 100; Y += 6.25f)
		{
			const float H = A.HeightAt(FVector2D(X, Y));
			if (H < -5.f) Width += 6.25f;
			if (H > -35.f && H < -5.f) ++SlopeSamples;
			WorstStep = FMath::Max(WorstStep, FMath::Abs(H - A.HeightAt(FVector2D(X, Y + 12.5f))));
		}
		TestTrue(TEXT("Each section has sloped walls on both sides"), SlopeSamples >= 6);
		const float Core = A.HeightAt(FVector2D(X, 0));
		TestTrue(TEXT("Firmer pockets retain a substantial rut within the sinkage bound"), Core < -23.f && Core > -43.f);
		MinCore = FMath::Min(MinCore, Core); MaxCore = FMath::Max(MaxCore, Core);
		MinWidth = FMath::Min(MinWidth, Width); MaxWidth = FMath::Max(MaxWidth, Width);
	}
	TestTrue(TEXT("No vertical one-cell 40 cm trench wall"), WorstStep < 24.f);
	TestTrue(TEXT("Shoulder width varies along the rut"), MaxWidth - MinWidth >= 6.25f);
	TestTrue(TEXT("Coherent firmer pockets break up the constant-depth trench"), MaxCore - MinCore > 5.f);
	AddInfo(FString::Printf(TEXT("max 12.5cm cross-step %.2fcm; width at -5cm %.2f..%.2fcm; core %.2f..%.2fcm"), WorstStep, MinWidth, MaxWidth, MinCore, MaxCore));
	for (int32 I = 0; I < 5; ++I) Pass(A, I % 2 == 0);
	A.StampWheel(FVector2D(500, -200), FVector2D(500, 200), 28, 40, FVector2D(0, 1), 400);
	A.StampBelly(FVector2D(500, 0), FVector2D(1, 0), 260, 110, 12);
	bool Bounded = true;
	for (float H : A.HeightCm) Bounded &= FMath::IsFinite(H) && H >= -43.f && H <= A.MaxRidgeCm + 0.01f;
	TestTrue(TEXT("Repeated and crossing passes remain finite and bounded"), Bounded);
	TestTrue(TEXT("Ground outside stamp reach is untouched"), FMath::IsNearlyZero(A.HeightAt(FVector2D(-150, 300))));
	FGTMudField Belly;
	Belly.Init(Bounds, 12.5f);
	Belly.StampBelly(FVector2D(500, 0), FVector2D(1, 0), 200, 100, 12);
	const float Feather = Belly.HeightAt(FVector2D(500, 68.75));
	TestTrue(TEXT("Belly edge has an intermediate depth"), Feather < -1.f && Feather > -11.f);
	return true;
}

// LM1, the living field (docs/LIVING_MUD_PLAN.md, the LM1 table): the section L test stroke (40 cm asked, 28 cm tyre),
// then FGTMudField::Settle. The bog's numbers are AGTMudPatch's defaults and the ford's are FGTDeformProfile's, so the
// test reads what ships. LM1b (the LM1b table): the recovery is the shape-keeping relax, measured on that narrow stroke
// and on a broad one like the strip's (asked 15 cm, the same tyre), and the detail kept is D = RMS(S - the 3x3 mean of
// S) / RMS(S) over the stroke's touched cells, against LM1's diffusion (OozeRate 1.2, RecoverShare 0) on the same strokes.
namespace GTMudSettleTest
{
	const FBox2D Bounds(FVector2D(-200, -350), FVector2D(1200, 350));

	/** The narrow stroke is asked 40 cm; LM1b's broad one, like the strip's rut, 15 cm. */
	constexpr float NarrowCm = 40.f;
	constexpr float BroadCm = 15.f;

	/**
	 * LM2a (docs/LIVING_MUD_PLAN.md, "Decisions after phase A"): the Settle rows are asserted twice. With the lumps off
	 * (LumpShare 0) LM1b's rows stand exactly as they are, as LM1b's regression; with the shipped bog numbers (LumpShare
	 * 0.35) the recovery is asked at least 9 % on both strokes (the relax moves HeightCm only and the balance caps the
	 * rut's rise at what the banks give up; the lumps hold about 35 % of the bank outside it), every tile asleep by
	 * 12.5 s (the lumps' talus runs to about 5.7 s, then the sheen fades for 6 s), the detail kept 0.9-1.1, and the
	 * steepest step and the volume as before. LumpsOff is the regression pass's LumpShare (RunStroke's default too).
	 */
	constexpr float LumpsOff = 0.f;
	constexpr float LumpsOnRecoveryMin = 0.09f;
	constexpr float LumpsOnSleepByS = 12.5f;

	void Stroke(FGTMudField& Field, float DepthCm = NarrowCm)
	{
		for (int32 I = 0; I < 200; ++I)
		{
			Field.StampWheel(FVector2D(I * 5.f, 0), FVector2D(I * 5.f + 5.f, 0), 28.f, DepthCm, FVector2D(1, 0), I * 5.f);
		}
	}

	/** The cells the stroke wrote (its set timers are running just after it): the detail measure's cells. */
	TArray<int32> TouchedCells(const FGTMudField& Field)
	{
		TArray<int32> Cells;
		for (int32 Index = 0; Index < Field.SetS.Num(); ++Index)
		{
			if (Field.SetS[Index] > 0.f)
			{
				Cells.Add(Index);
			}
		}
		return Cells;
	}

	void Bog(FGTMudField& Field)
	{
		const AGTMudPatch* Patch = GetDefault<AGTMudPatch>();
		Field.ReposeDeg = Patch->ReposeDeg;
		Field.SlumpRate = Patch->SlumpRate;
		Field.OozeRate = Patch->OozeRate;
		Field.RecoverShare = Patch->RecoverShare;
		Field.CreepCmPerCm = Patch->CreepCmPerCm;
		Field.SetSeconds = Patch->SetSeconds;
		Field.SmearCmPerCm = Patch->SmearCmPerCm;
		Field.FreshFadeS = Patch->FreshFadeS;
		Field.SleepCmPerS = Patch->SleepCmPerS;
		// LM2a: the fresh threshold, the lumps and stage I's clods (0 with the lumps on), the patch's.
		Field.FreshMinCm = Patch->FreshMinCm;
		Field.LumpShare = Patch->LumpShare;
		Field.LumpSpacingCells = Patch->LumpSpacingCells;
		Field.LumpRadiusCells = Patch->LumpRadiusCells;
		Field.LumpMaxCm = Patch->LumpMaxCm;
		Field.ClodChance = Patch->ClodChance;
		// LM2c: the variety and the lip's bank clods, the patch's.
		Field.bLumpVariety = Patch->bLumpVariety;
		Field.ClodBankPerCm = Patch->ClodBankPerCm;
		Field.ClodBankInner = Patch->ClodBankInner;
		Field.ClodBankSizeMinCm = Patch->ClodBankSizeMinCm;
		Field.ClodBankSizeMaxCm = Patch->ClodBankSizeMaxCm;
		Field.ClodSizePower = Patch->ClodSizePower;
	}

	void Ford(FGTMudField& Field)
	{
		const FGTDeformProfile Profile;
		Field.ReposeDeg = Profile.ReposeDeg;
		Field.SlumpRate = Profile.SlumpRate;
		Field.OozeRate = Profile.OozeRate;
		Field.RecoverShare = Profile.RecoverShare;
		Field.CreepCmPerCm = Profile.CreepCmPerCm;
		Field.SetSeconds = Profile.SetSeconds;
		Field.SmearCmPerCm = Profile.SmearCmPerCm;
		Field.FreshFadeS = Profile.FreshFadeS;
		Field.SleepCmPerS = Profile.SleepCmPerS;
		Field.FreshMinCm = Profile.FreshMinCm;
		Field.LumpShare = Profile.LumpShare;
		Field.LumpSpacingCells = Profile.LumpSpacingCells;
		Field.LumpRadiusCells = Profile.LumpRadiusCells;
		Field.LumpMaxCm = Profile.LumpMaxCm;
		Field.ClodChance = Profile.ClodChance;
	}

	/** LM2a: the surface's volume, HeightCm + LumpCm (the talus moves lumps into the bank). */
	double Volume(const FGTMudField& Field)
	{
		double Sum = 0.0;
		for (int32 Index = 0; Index < Field.HeightCm.Num(); ++Index)
		{
			Sum += Field.SurfaceCm(Index);
		}
		return Sum * Field.CellCm * Field.CellCm;
	}

	/** LM2a: the lumps' volume alone. */
	double LumpVolume(const FGTMudField& Field)
	{
		double Sum = 0.0;
		for (const float Lump : Field.LumpCm)
		{
			Sum += Lump;
		}
		return Sum * Field.CellCm * Field.CellCm;
	}

	/** The rut's centre line, as the SoftShoulders test reads its core: the mean over the stroke's middle 8 m. */
	float CoreMean(const FGTMudField& Field)
	{
		float Sum = 0.f;
		int32 Count = 0;
		for (float X = 100; X <= 900; X += 25)
		{
			Sum += Field.HeightAt(FVector2D(X, 0));
			++Count;
		}
		return Sum / Count;
	}

	/** The +Y bank, station by station over the middle 8 m: the highest cell out from the rut and the width at half its height (the terrain test's way). */
	void Crest(const FGTMudField& Field, float& OutHeight, float& OutWidth)
	{
		float HeightSum = 0.f;
		float WidthSum = 0.f;
		int32 Stations = 0;
		for (float X = 100; X <= 900; X += 25)
		{
			TArray<float> Cross;
			TArray<float> Out;
			int32 Last = INDEX_NONE;
			for (float Y = 6.25f; Y <= 340.f; Y += 3.125f)
			{
				const int32 Cell = Field.CellIndexAt(FVector2D(X, Y));
				if (Cell == Last)
				{
					continue;
				}
				Last = Cell;
				Cross.Add(Field.CellHeightCm(Cell));
				Out.Add(Y);
			}
			int32 Peak = 0;
			for (int32 Index = 1; Index < Cross.Num(); ++Index)
			{
				if (Cross[Index] > Cross[Peak])
				{
					Peak = Index;
				}
			}
			if (Cross.Num() < 3 || Cross[Peak] <= 0.2f)
			{
				continue;
			}
			const float Half = 0.5f * Cross[Peak];
			int32 Lo = Peak;
			while (Lo > 0 && Cross[Lo] >= Half)
			{
				--Lo;
			}
			const float LoEdge = Cross[Lo] >= Half ? Out[0] : FMath::Lerp(Out[Lo], Out[Lo + 1], (Half - Cross[Lo]) / FMath::Max(0.01f, Cross[Lo + 1] - Cross[Lo]));
			int32 Hi = Peak;
			while (Hi < Cross.Num() - 1 && Cross[Hi] >= Half)
			{
				++Hi;
			}
			const float HiEdge = Cross[Hi] >= Half ? Out.Last() : FMath::Lerp(Out[Hi - 1], Out[Hi], (Cross[Hi - 1] - Half) / FMath::Max(0.01f, Cross[Hi - 1] - Cross[Hi]));
			HeightSum += Cross[Peak];
			WidthSum += FMath::Max(0.f, HiEdge - LoEdge);
			++Stations;
		}
		OutHeight = Stations > 0 ? HeightSum / Stations : 0.f;
		OutWidth = Stations > 0 ? WidthSum / Stations : 0.f;
	}

	float SteepestStep(const FGTMudField& Field)
	{
		float Worst = 0.f;
		for (int32 Y = 0; Y < Field.SizeY; ++Y)
		{
			for (int32 X = 0; X < Field.SizeX; ++X)
			{
				const float Here = Field.SurfaceCm(Y * Field.SizeX + X);   // LM2a: the talus works on the surface
				if (X + 1 < Field.SizeX)
				{
					Worst = FMath::Max(Worst, FMath::Abs(Here - Field.SurfaceCm(Y * Field.SizeX + X + 1)));
				}
				if (Y + 1 < Field.SizeY)
				{
					Worst = FMath::Max(Worst, FMath::Abs(Here - Field.SurfaceCm((Y + 1) * Field.SizeX + X)));
				}
			}
		}
		return Worst;
	}

	void SettleFor(FGTMudField& Field, float Seconds, float Dt)
	{
		const int32 Calls = FMath::RoundToInt(Seconds / Dt);
		for (int32 Call = 0; Call < Calls; ++Call)
		{
			Field.Settle(Dt);
		}
	}

	float MaxDifference(const FGTMudField& A, const FGTMudField& B)
	{
		float Worst = 0.f;
		for (int32 Index = 0; Index < A.HeightCm.Num(); ++Index)
		{
			Worst = FMath::Max(Worst, FMath::Abs(A.SurfaceCm(Index) - B.SurfaceCm(Index)));
		}
		return Worst;
	}

	/** One stroke settled for 10 s at 1/30 s frames: the core, the bank and the detail just stamped, at 5 s and at 10 s, and the relax's volumes. */
	struct FStrokeRun
	{
		float Core0 = 0.f, Core5 = 0.f;
		float Crest0 = 0.f, Width0 = 0.f, Crest5 = 0.f, Width5 = 0.f, Crest10 = 0.f, Width10 = 0.f;
		float D0 = 0.f, D10 = 0.f;
		double LoweredCm3 = 0.0, AskedUpCm3 = 0.0, AskedDownCm3 = 0.0, MovedCm3 = 0.0;
		float LumpShare = 0.f;
		double Lumps0Cm3 = 0.0, Lumps10Cm3 = 0.0;
		float Step0 = 0.f, Step10 = 0.f, SleptAt = -1.f;
		double VolumeError = 0.0;
		/** The core depth back at 5 s, share of the just-stamped core (0.2 = a fifth of the rut filled back in). */
		float Recovery() const { return (Core5 - Core0) / FMath::Max(0.01f, -Core0); }
		/** D at 10 s over D just stamped (1 = the detail kept). */
		float DetailKept() const { return D0 > 0.f ? D10 / D0 : 0.f; }
	};

	FStrokeRun RunStroke(void (*Numbers)(FGTMudField&), float DepthCm, float OozeOverride = -1.f, float ShareOverride = -1.f, float LumpOverride = LumpsOff)
	{
		FGTMudField Field;
		Field.Init(Bounds, 12.5f);
		Numbers(Field);
		if (LumpOverride >= 0.f)
		{
			Field.LumpShare = LumpOverride;
		}
		if (OozeOverride >= 0.f)
		{
			Field.OozeRate = OozeOverride;
		}
		if (ShareOverride >= 0.f)
		{
			Field.RecoverShare = ShareOverride;
		}
		Stroke(Field, DepthCm);
		FStrokeRun Run;
		Run.LumpShare = Field.LumpShare;
		Run.Lumps0Cm3 = LumpVolume(Field);
		const TArray<int32> Touched = TouchedCells(Field);
		Run.LoweredCm3 = Field.LoweredCm3;
		Run.Core0 = CoreMean(Field);
		Crest(Field, Run.Crest0, Run.Width0);
		Run.D0 = Field.DetailRatio(Touched);
		Run.Step0 = SteepestStep(Field);
		const double Volume0 = Volume(Field);
		for (int32 Call = 1; Call <= 300; ++Call)   // 10 s at 1/30 s
		{
			Field.Settle(1.f / 30.f);
			if (Call == 150)
			{
				Run.Core5 = CoreMean(Field);
				Crest(Field, Run.Crest5, Run.Width5);
			}
			if (Run.SleptAt < 0.f && Field.AwakeTileCount() == 0)
			{
				Run.SleptAt = Call / 30.f;
			}
		}
		Crest(Field, Run.Crest10, Run.Width10);
		Run.Step10 = SteepestStep(Field);
		Run.VolumeError = FMath::Abs(Volume(Field) - Volume0);
		Run.D10 = Field.DetailRatio(Touched);
		Run.AskedUpCm3 = Field.RelaxAskedUpCm3;
		Run.AskedDownCm3 = Field.RelaxAskedDownCm3;
		Run.MovedCm3 = Field.RelaxMovedCm3;
		Run.Lumps10Cm3 = LumpVolume(Field);
		for (int32 Call = 301; Call <= 600 && Run.SleptAt < 0.f; ++Call)   // on to 20 s, for the sleep time
		{
			Field.Settle(1.f / 30.f);
			if (Field.AwakeTileCount() == 0)
			{
				Run.SleptAt = Call / 30.f;
			}
		}
		return Run;
	}

	FString Describe(const TCHAR* Name, const FStrokeRun& Run)
	{
		return FString::Printf(TEXT("%s (LumpShare %.2f): core %.2f -> %.2f cm at 5 s = %.1f %% back; crest %.2f cm (%.1f cm wide) -> %.2f (%.1f) at 5 s -> %.2f (%.1f) at 10 s; D %.4f -> %.4f at 10 s = %.3f; relax asked V_up %.0f / V_down %.0f cm^3, moved %.0f each way (lowered %.0f); lumps %.0f -> %.0f cm^3; steepest step %.2f -> %.2f cm; volume error %.1f cm^3; asleep at %.2f s"),
			Name, Run.LumpShare, Run.Core0, Run.Core5, 100.f * Run.Recovery(), Run.Crest0, Run.Width0, Run.Crest5, Run.Width5, Run.Crest10, Run.Width10,
			Run.D0, Run.D10, Run.DetailKept(), Run.AskedUpCm3, Run.AskedDownCm3, Run.MovedCm3, Run.LoweredCm3, Run.Lumps0Cm3, Run.Lumps10Cm3, Run.Step0, Run.Step10, Run.VolumeError, Run.SleptAt);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudSettleTest, "GrandTour.Mud.Settle",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTMudSettleTest::RunTest(const FString& Parameters)
{
	using namespace GTMudSettleTest;
	// gt.Mud.Settle 0: the stroke, never settled, is today's field. The numbers are the SoftShoulders test's as LM0
	// measured them before LM1 (docs/LIVING_MUD_PLAN.md LM0), printed to 0.01; the CRC is for the next stage to hold.
	{
		FGTMudField Field;
		Field.Init(Bounds, 12.5f);
		// LM2a: LM0's stroke had no lumps and stage I's clods (0.15); with those two numbers the stamp must be LM0's
		// field to the bit, so the lumps and the throw are a pure addition to it.
		Field.LumpShare = 0.f;
		Field.ClodChance = 0.15f;
		Stroke(Field);
		float WorstStep = 0.f, MinWidth = 1000.f, MaxWidth = 0.f, MinCore = 0.f, MaxCore = -100.f;
		for (float X = 100; X <= 900; X += 25)
		{
			float Width = 0.f;
			for (float Y = -100; Y <= 100; Y += 6.25f)
			{
				const float H = Field.HeightAt(FVector2D(X, Y));
				if (H < -5.f) Width += 6.25f;
				WorstStep = FMath::Max(WorstStep, FMath::Abs(H - Field.HeightAt(FVector2D(X, Y + 12.5f))));
			}
			const float Core = Field.HeightAt(FVector2D(X, 0));
			MinCore = FMath::Min(MinCore, Core); MaxCore = FMath::Max(MaxCore, Core);
			MinWidth = FMath::Min(MinWidth, Width); MaxWidth = FMath::Max(MaxWidth, Width);
		}
		uint32 Crc = FCrc::MemCrc32(Field.HeightCm.GetData(), Field.HeightCm.Num() * sizeof(float));
		Crc = FCrc::MemCrc32(Field.OffsetCm.GetData(), Field.OffsetCm.Num() * sizeof(FVector2f), Crc);
		Crc = FCrc::MemCrc32(Field.Tracks.GetData(), Field.Tracks.Num(), Crc);
		Crc = FCrc::MemCrc32(Field.HeadingTurns.GetData(), Field.HeadingTurns.Num() * sizeof(float), Crc);
		Crc = FCrc::MemCrc32(Field.PhaseTurns.GetData(), Field.PhaseTurns.Num() * sizeof(float), Crc);
		TestTrue(TEXT("gt.Mud.Settle 0 with LumpShare 0 and ClodChance 0.15: the field CRC is LM0's 8e0aad06"), Crc == 0x8e0aad06u);
		const bool bToday = FMath::Abs(WorstStep - 14.94f) <= 0.0051f && FMath::Abs(MinWidth - 93.75f) <= 0.0051f && FMath::Abs(MaxWidth - 143.75f) <= 0.0051f
			&& FMath::Abs(MinCore + 40.78f) <= 0.0051f && FMath::Abs(MaxCore + 25.94f) <= 0.0051f;
		TestTrue(TEXT("gt.Mud.Settle 0: the stroke is today's field (LM0's 14.94 / 93.75..143.75 / -40.78..-25.94)"), bToday);
		AddInfo(FString::Printf(TEXT("Settle: gt.Mud.Settle 0 identity - cross-step %.2fcm, width %.2f..%.2fcm, core %.2f..%.2fcm (LM0 14.94, 93.75..143.75, -40.78..-25.94) -> %d; field CRC %08x"),
			WorstStep, MinWidth, MaxWidth, MinCore, MaxCore, bToday ? 1 : 0, Crc));
	}

	// The bog, the narrow stroke: volume, the steepest step, the core's recovery, the bank, the detail, sleep.
	FGTMudField Field;
	Field.Init(Bounds, 12.5f);
	Bog(Field);
	Field.LumpShare = LumpsOff;   // the regression pass: LM1b's rows as they stand
	Stroke(Field);
	const TArray<int32> Touched = TouchedCells(Field);
	const float D0 = Field.DetailRatio(Touched);
	const double Lowered = Field.LoweredCm3;
	const double Volume0 = Volume(Field);
	const float Core0 = CoreMean(Field);
	const float Step0 = SteepestStep(Field);
	float Crest0 = 0.f, Width0 = 0.f;
	Crest(Field, Crest0, Width0);
	const int32 Awake0 = Field.AwakeTileCount();
	float SleptAt = -1.f;
	float Core5 = 0.f, Crest5 = 0.f, Width5 = 0.f;
	const float Dt = 1.f / 30.f;
	for (int32 Call = 1; Call <= 300; ++Call)   // 10 s
	{
		Field.Settle(Dt);
		if (Call == 150)
		{
			Core5 = CoreMean(Field);
			Crest(Field, Crest5, Width5);
		}
		if (SleptAt < 0.f && Field.AwakeTileCount() == 0)
		{
			SleptAt = Call * Dt;
		}
	}
	const double Volume10 = Volume(Field);
	const float Step10 = SteepestStep(Field);
	float Crest10 = 0.f, Width10 = 0.f;
	Crest(Field, Crest10, Width10);
	const float D10 = Field.DetailRatio(Touched);
	const double AskedUp = Field.RelaxAskedUpCm3;
	const double AskedDown = Field.RelaxAskedDownCm3;
	const double Moved = Field.RelaxMovedCm3;
	for (int32 Call = 301; Call <= 600 && SleptAt < 0.f; ++Call)   // on to 20 s, for the sleep time
	{
		Field.Settle(Dt);
		if (Field.AwakeTileCount() == 0)
		{
			SleptAt = Call * Dt;
		}
	}
	const double VolumeError = FMath::Abs(Volume10 - Volume0);
	const float Talus = FMath::Tan(FMath::DegreesToRadians(Field.ReposeDeg)) * Field.CellCm;
	const float Recovery = (Core5 - Core0) / FMath::Max(0.01f, -Core0);
	const float SleepBy = Field.SetSeconds + Field.FreshFadeS + 1.f;
	const float Kept = D0 > 0.f ? D10 / D0 : 0.f;
	TestTrue(TEXT("Volume: 10 s settled equals just stamped within 0.1 % of the stroke's lowered volume"), VolumeError <= 0.001 * Lowered);
	TestTrue(TEXT("Steepest neighbour step after 10 s within tan(ReposeDeg) x CellCm + 0.5 cm"), Step10 <= Talus + 0.5f);
	TestTrue(TEXT("Core depth back at 5 s, the 40 cm narrow stroke, bog numbers: at least 14 %"), Recovery >= 0.14f);
	TestTrue(TEXT("Detail kept, the narrow stroke: D at 10 s within 10 % of just stamped"), Kept >= 0.9f && Kept <= 1.1f);
	TestTrue(TEXT("Bank crest lower than just stamped"), Crest10 < Crest0);
	TestTrue(TEXT("Sleep: every tile asleep by SetSeconds + FreshFadeS + 1 s"), SleptAt >= 0.f && SleptAt <= SleepBy + 1.e-3f);
	AddInfo(FString::Printf(TEXT("Settle: bog numbers ReposeDeg %.1f SlumpRate %.2f OozeRate %.2f RecoverShare %.3f CreepCmPerCm %.2f SetSeconds %.2f SmearCmPerCm %.2f FreshFadeS %.1f SleepCmPerS %.3f FreshMinCm %.3f; the regression rows below with LumpShare %.2f, ClodChance %.2f"),
		Field.ReposeDeg, Field.SlumpRate, Field.OozeRate, Field.RecoverShare, Field.CreepCmPerCm, Field.SetSeconds, Field.SmearCmPerCm, Field.FreshFadeS, Field.SleepCmPerS, Field.FreshMinCm,
		Field.LumpShare, Field.ClodChance));
	AddInfo(FString::Printf(TEXT("Settle: volume %.0f -> %.0f cm^3, error %.1f cm^3 = %.5f %% of the lowered %.0f cm^3 (asked <= 0.1 %%)"),
		Volume0, Volume10, VolumeError, 100.0 * VolumeError / FMath::Max(1.0, Lowered), Lowered));
	AddInfo(FString::Printf(TEXT("Settle: steepest step %.2f cm just stamped -> %.2f cm at 10 s (asked <= %.2f)"), Step0, Step10, Talus + 0.5f));
	AddInfo(FString::Printf(TEXT("Settle: narrow stroke (40 cm) core %.2f cm just stamped -> %.2f cm at 5 s: %.1f %% back (asked at least 14 %%); relax asked V_up %.0f cm^3, V_down %.0f cm^3, moved %.0f each way"),
		Core0, Core5, 100.f * Recovery, AskedUp, AskedDown, Moved));
	AddInfo(FString::Printf(TEXT("Settle: narrow stroke detail D %.4f just stamped -> %.4f at 10 s = %.3f (asked 0.9-1.1) over %d touched cells"), D0, D10, Kept, Touched.Num()));
	AddInfo(FString::Printf(TEXT("Settle: bank crest %.2f cm wide %.1f cm at half height just stamped -> %.2f cm / %.1f cm at 5 s -> %.2f cm / %.1f cm at 10 s: %.1f %% lower (asked lower)"),
		Crest0, Width0, Crest5, Width5, Crest10, Width10, 100.f * (Crest0 - Crest10) / FMath::Max(0.01f, Crest0)));
	AddInfo(FString::Printf(TEXT("Settle: %d tiles awake after the stroke, all asleep at %.2f s (asked by %.1f s)"), Awake0, SleptAt, SleepBy));

	// The broad stroke, like the strip's rut (asked 15 cm, the same tyre).
	const FStrokeRun Broad = RunStroke(&Bog, BroadCm);
	TestTrue(TEXT("Core depth back at 5 s, the broad stroke (asked 15 cm), bog numbers: at least 14 %"), Broad.Recovery() >= 0.14f);
	TestTrue(TEXT("Detail kept, the broad stroke: D at 10 s within 10 % of just stamped"), Broad.DetailKept() >= 0.9f && Broad.DetailKept() <= 1.1f);
	TestTrue(TEXT("Bank crest lower than just stamped, the broad stroke"), Broad.Crest10 < Broad.Crest0);
	AddInfo(TEXT("Settle: ") + Describe(TEXT("broad stroke (15 cm), bog"), Broad));
	AddInfo(FString::Printf(TEXT("Settle: crest fall at RecoverShare %.2f - narrow %.2f -> %.2f cm at 5 s (%.1f %% lower), broad %.2f -> %.2f cm (%.1f %% lower)"),
		Field.RecoverShare, Crest0, Crest5, 100.f * (Crest0 - Crest5) / FMath::Max(0.01f, Crest0),
		Broad.Crest0, Broad.Crest5, 100.f * (Broad.Crest0 - Broad.Crest5) / FMath::Max(0.01f, Broad.Crest0)));

	// The ford's numbers: stiffer, so the rut stays, on either stroke.
	const FStrokeRun FordNarrow = RunStroke(&Ford, NarrowCm);
	const FStrokeRun FordBroad = RunStroke(&Ford, BroadCm);
	TestTrue(TEXT("Core depth back at 5 s, ford numbers, the narrow stroke: under 3 %"), FordNarrow.Recovery() < 0.03f);
	TestTrue(TEXT("Core depth back at 5 s, ford numbers, the broad stroke: under 3 %"), FordBroad.Recovery() < 0.03f);
	AddInfo(TEXT("Settle: ") + Describe(TEXT("ford numbers, narrow stroke"), FordNarrow));
	AddInfo(TEXT("Settle: ") + Describe(TEXT("ford numbers, broad stroke"), FordBroad));

	// LM1's diffusion on the same strokes, for comparison (OozeRate 1.2, RecoverShare 0): the blur the owner called too smooth.
	const FStrokeRun Lm1Narrow = RunStroke(&Bog, NarrowCm, 1.2f, 0.f);
	const FStrokeRun Lm1Broad = RunStroke(&Bog, BroadCm, 1.2f, 0.f);
	AddInfo(FString::Printf(TEXT("Settle: detail kept D10/D0 - LM1b relax narrow %.3f, broad %.3f; LM1 diffusion (OozeRate 1.2, RecoverShare 0) narrow %.3f, broad %.3f"),
		Kept, Broad.DetailKept(), Lm1Narrow.DetailKept(), Lm1Broad.DetailKept()));
	AddInfo(TEXT("Settle: ") + Describe(TEXT("LM1 diffusion, narrow stroke"), Lm1Narrow));
	AddInfo(TEXT("Settle: ") + Describe(TEXT("LM1 diffusion, broad stroke"), Lm1Broad));

	// The recovery against RecoverShare (information: the balance caps the rut's rise at what the banks give up).
	FString Curve;
	for (const float Share : { 0.1f, 0.2f, 0.3f, 0.4f, 0.5f, 0.6f })
	{
		const FStrokeRun Narrow = RunStroke(&Bog, NarrowCm, -1.f, Share);
		const FStrokeRun Wide = RunStroke(&Bog, BroadCm, -1.f, Share);
		Curve += FString::Printf(TEXT("%s%.1f: narrow %.1f %% (crest %.2f -> %.2f), broad %.1f %% (crest %.2f -> %.2f)"), Curve.IsEmpty() ? TEXT("") : TEXT(", "), Share,
			100.f * Narrow.Recovery(), Narrow.Crest0, Narrow.Crest10, 100.f * Wide.Recovery(), Wide.Crest0, Wide.Crest10);
	}
	AddInfo(TEXT("Settle: core back at 5 s by RecoverShare - ") + Curve);

	// Frame rate: the same stamps settled at 1/30, 1/60 and 1/144 s frames.
	{
		FGTMudField A, B, C;
		for (FGTMudField* Each : { &A, &B, &C })
		{
			Each->Init(Bounds, 12.5f);
			Bog(*Each);
			Stroke(*Each);
		}
		SettleFor(A, 5.f, 1.f / 30.f);
		SettleFor(B, 5.f, 1.f / 60.f);
		SettleFor(C, 5.f, 1.f / 144.f);
		const float At5 = FMath::Max(MaxDifference(A, B), MaxDifference(A, C));
		SettleFor(A, 5.f, 1.f / 30.f);
		SettleFor(B, 5.f, 1.f / 60.f);
		SettleFor(C, 5.f, 1.f / 144.f);
		const float At10 = FMath::Max(MaxDifference(A, B), MaxDifference(A, C));
		TestTrue(TEXT("Frame rate: 1/30, 1/60, 1/144 every cell within 0.1 cm"), At5 <= 0.1f && At10 <= 0.1f);
		AddInfo(FString::Printf(TEXT("Settle: frame rate 1/30 vs 1/60 vs 1/144 - worst cell %.4f cm at 5 s, %.4f cm at 10 s (asked <= 0.1)"), At5, At10));
	}

	// Determinism: twice from the same input.
	{
		FGTMudField A, B;
		for (FGTMudField* Each : { &A, &B })
		{
			Each->Init(Bounds, 12.5f);
			Bog(*Each);
			Stroke(*Each);
			SettleFor(*Each, 10.f, 1.f / 60.f);
		}
		const bool bSame = A.HeightCm == B.HeightCm && A.LumpCm == B.LumpCm && A.OffsetCm == B.OffsetCm && A.Fresh == B.Fresh && A.SetS == B.SetS;
		TestTrue(TEXT("Determinism: the same input twice gives the same field"), bSame);
		AddInfo(FString::Printf(TEXT("Settle: determinism (heights, lumps, offsets, fresh, set timers identical) -> %d"), bSame ? 1 : 0));
	}

	// LM2a, the second pass: the shipped bog numbers, lumps on (the lumps-off rows above are LM1b's regression). The
	// surface now includes LumpCm, and the relax (HeightCm only) leaves the lumps alone.
	{
		const float Shipped = GetDefault<AGTMudPatch>()->LumpShare;
		const FStrokeRun NarrowOn = RunStroke(&Bog, NarrowCm, -1.f, -1.f, -1.f);   // -1: the bog's own LumpShare
		const FStrokeRun NarrowOff = RunStroke(&Bog, NarrowCm, -1.f, -1.f, LumpsOff);
		const FStrokeRun BroadOn = RunStroke(&Bog, BroadCm, -1.f, -1.f, -1.f);
		const FStrokeRun BroadOff = RunStroke(&Bog, BroadCm, -1.f, -1.f, LumpsOff);
		TestTrue(TEXT("Lumps on (the shipped bog numbers): LumpShare is the patch's 0.35"), FMath::IsNearlyEqual(NarrowOn.LumpShare, 0.35f) && FMath::IsNearlyEqual(BroadOn.LumpShare, 0.35f));
		for (const TPair<const TCHAR*, const FStrokeRun*>& Each : { TPair<const TCHAR*, const FStrokeRun*>(TEXT("narrow"), &NarrowOn), TPair<const TCHAR*, const FStrokeRun*>(TEXT("broad"), &BroadOn) })
		{
			const FStrokeRun& Run = *Each.Value;
			TestTrue(FString::Printf(TEXT("Lumps on, the %s stroke: core depth back at 5 s at least 9 %%"), Each.Key), Run.Recovery() >= LumpsOnRecoveryMin);
			TestTrue(FString::Printf(TEXT("Lumps on, the %s stroke: every tile asleep by 12.5 s"), Each.Key), Run.SleptAt >= 0.f && Run.SleptAt <= LumpsOnSleepByS + 1.e-3f);
			TestTrue(FString::Printf(TEXT("Lumps on, the %s stroke: detail kept, D at 10 s within 10 %% of just stamped"), Each.Key), Run.DetailKept() >= 0.9f && Run.DetailKept() <= 1.1f);
			TestTrue(FString::Printf(TEXT("Lumps on, the %s stroke: steepest neighbour step after 10 s within tan(ReposeDeg) x CellCm + 0.5 cm"), Each.Key), Run.Step10 <= Talus + 0.5f);
			TestTrue(FString::Printf(TEXT("Lumps on, the %s stroke: volume at 10 s equals just stamped within 0.1 %% of the lowered volume"), Each.Key), Run.VolumeError <= 0.001 * Run.LoweredCm3);
		}
		AddInfo(FString::Printf(TEXT("Settle: lumps on (asserted, LumpShare %.2f) - narrow core back %.1f %%, broad %.1f %% (asked at least %.0f); asleep at %.2f / %.2f s (asked by %.1f); D10/D0 %.3f / %.3f (asked 0.9-1.1); steepest step at 10 s %.2f / %.2f cm (asked <= %.2f); volume error %.1f / %.1f cm^3 of %.0f / %.0f lowered"),
			Shipped, 100.f * NarrowOn.Recovery(), 100.f * BroadOn.Recovery(), 100.f * LumpsOnRecoveryMin, NarrowOn.SleptAt, BroadOn.SleptAt, LumpsOnSleepByS,
			NarrowOn.DetailKept(), BroadOn.DetailKept(), NarrowOn.Step10, BroadOn.Step10, Talus + 0.5f, NarrowOn.VolumeError, BroadOn.VolumeError, NarrowOn.LoweredCm3, BroadOn.LoweredCm3));
		AddInfo(TEXT("Settle: LM2a lumps on - ") + Describe(TEXT("narrow stroke, bog"), NarrowOn));
		AddInfo(TEXT("Settle: LM2a lumps off - ") + Describe(TEXT("narrow stroke, bog"), NarrowOff));
		AddInfo(TEXT("Settle: LM2a lumps on - ") + Describe(TEXT("broad stroke, bog"), BroadOn));
		AddInfo(TEXT("Settle: LM2a lumps off - ") + Describe(TEXT("broad stroke, bog"), BroadOff));
		AddInfo(FString::Printf(TEXT("Settle: LM2a moved rows (LumpShare %.2f vs 0) - narrow core back %.1f vs %.1f %% (asked at least 9 on, 14 off), D10/D0 %.3f vs %.3f (asked 0.9-1.1), crest %.2f -> %.2f vs %.2f -> %.2f cm; broad core back %.1f vs %.1f %%, D10/D0 %.3f vs %.3f, crest %.2f -> %.2f vs %.2f -> %.2f cm"),
			Shipped, 100.f * NarrowOn.Recovery(), 100.f * NarrowOff.Recovery(), NarrowOn.DetailKept(), NarrowOff.DetailKept(), NarrowOn.Crest0, NarrowOn.Crest10, NarrowOff.Crest0, NarrowOff.Crest10,
			100.f * BroadOn.Recovery(), 100.f * BroadOff.Recovery(), BroadOn.DetailKept(), BroadOff.DetailKept(), BroadOn.Crest0, BroadOn.Crest10, BroadOff.Crest0, BroadOff.Crest10));
		// For the gate: the recovery against RecoverShare with the lumps on (not shipped: RecoverShare is LM1b's, 0.4).
		FString OnCurve;
		for (const float Share : { 0.4f, 0.5f, 0.6f, 0.7f })
		{
			const FStrokeRun Narrow = RunStroke(&Bog, NarrowCm, -1.f, Share, -1.f);
			const FStrokeRun Wide = RunStroke(&Bog, BroadCm, -1.f, Share, -1.f);
			OnCurve += FString::Printf(TEXT("%s%.1f: narrow %.1f %%, broad %.1f %%"), OnCurve.IsEmpty() ? TEXT("") : TEXT(", "), Share, 100.f * Narrow.Recovery(), 100.f * Wide.Recovery());
		}
		AddInfo(TEXT("Settle: LM2a lumps on, core back at 5 s by RecoverShare - ") + OnCurve);
	}
	return true;
}

// LM2a, lumps in the field and the wheel's throw (docs/LIVING_MUD_PLAN.md, the LM2a table). The bog's numbers are
// AGTMudPatch's defaults (LumpShare 0.35, LumpMaxCm 10, ClodChance 0), the stroke is the Settle test's narrow one.
namespace GTMudLumpTest
{
	using namespace GTMudSettleTest;

	/**
	 * The +Y bank's crest along the stroke, cell column by cell column over its middle 8 m: the highest surface cell out
	 * from the rut in each column (the terrain test's "highest cell across the hump"), their mean and their coefficient
	 * of variation (sd / mean).
	 */
	float CrestCv(const FGTMudField& Field, float& OutMean)
	{
		TArray<float> Peaks;
		const int32 Y0 = Field.CellIndexAt(FVector2D(0.0, 6.25)) / Field.SizeX;
		const int32 Y1 = Field.CellIndexAt(FVector2D(0.0, 340.0)) / Field.SizeX;
		for (float X = 100.f; X <= 900.f + 0.1f; X += Field.CellCm)
		{
			const int32 Column = Field.CellIndexAt(FVector2D(X, 0.0)) % Field.SizeX;
			float Peak = -1000.f;
			for (int32 Y = Y0; Y <= Y1; ++Y)
			{
				Peak = FMath::Max(Peak, Field.SurfaceCm(Y * Field.SizeX + Column));
			}
			Peaks.Add(Peak);
		}
		double Sum = 0.0;
		for (const float Peak : Peaks)
		{
			Sum += Peak;
		}
		const double Mean = Sum / FMath::Max(1, Peaks.Num());
		double Var = 0.0;
		for (const float Peak : Peaks)
		{
			Var += (Peak - Mean) * (Peak - Mean);
		}
		OutMean = static_cast<float>(Mean);
		return Mean > 0.0 ? static_cast<float>(FMath::Sqrt(Var / FMath::Max(1, Peaks.Num())) / Mean) : 0.f;
	}

	/** The same along the bank's own crest line: in each column the cell where HeightCm (the bank, no lumps) is highest, and the surface there (lumps included). */
	float CrestLineCv(const FGTMudField& Field, float& OutMean)
	{
		TArray<float> Values;
		const int32 Y0 = Field.CellIndexAt(FVector2D(0.0, 6.25)) / Field.SizeX;
		const int32 Y1 = Field.CellIndexAt(FVector2D(0.0, 340.0)) / Field.SizeX;
		for (float X = 100.f; X <= 900.f + 0.1f; X += Field.CellCm)
		{
			const int32 Column = Field.CellIndexAt(FVector2D(X, 0.0)) % Field.SizeX;
			int32 Best = Y0 * Field.SizeX + Column;
			for (int32 Y = Y0; Y <= Y1; ++Y)
			{
				if (Field.HeightCm[Y * Field.SizeX + Column] > Field.HeightCm[Best])
				{
					Best = Y * Field.SizeX + Column;
				}
			}
			Values.Add(Field.SurfaceCm(Best));
		}
		double Sum = 0.0;
		for (const float Value : Values)
		{
			Sum += Value;
		}
		const double Mean = Sum / FMath::Max(1, Values.Num());
		double Var = 0.0;
		for (const float Value : Values)
		{
			Var += (Value - Mean) * (Value - Mean);
		}
		OutMean = static_cast<float>(Mean);
		return Mean > 0.0 ? static_cast<float>(FMath::Sqrt(Var / FMath::Max(1, Values.Num())) / Mean) : 0.f;
	}

	/** What stands above the ground: the bank (HeightCm over 0) and the lumps, cm^3. */
	double Standing(const FGTMudField& Field)
	{
		double Sum = 0.0;
		for (int32 Index = 0; Index < Field.HeightCm.Num(); ++Index)
		{
			Sum += FMath::Max(0.f, Field.HeightCm[Index]) + Field.LumpCm[Index];
		}
		return Sum * Field.CellCm * Field.CellCm;
	}

	/** The cells whose centres lie within Radius of the segment A-B (the tyre itself, inside any capsule's bowl). */
	TArray<int32> CellsUnder(const FGTMudField& Field, const FVector2D& A, const FVector2D& B, float Radius)
	{
		TArray<int32> Cells;
		const FVector2D AB = B - A;
		const double LenSq = FMath::Max(1.e-6, AB.SizeSquared());
		for (int32 Index = 0; Index < Field.HeightCm.Num(); ++Index)
		{
			const FVector2D P = Field.CellCentreCm(Index);
			const double T = FMath::Clamp(FVector2D::DotProduct(P - A, AB) / LenSq, 0.0, 1.0);
			if (FVector2D::Distance(P, A + AB * T) <= Radius)
			{
				Cells.Add(Index);
			}
		}
		return Cells;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudLumpsTest, "GrandTour.Mud.Lumps",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTMudLumpsTest::RunTest(const FString& Parameters)
{
	using namespace GTMudSettleTest;
	using namespace GTMudLumpTest;

	// The narrow stroke with the lumps on, and the same stroke with LumpShare 0 (stage I's clods 0 in both, the bog's).
	FGTMudField On;
	On.Init(Bounds, 12.5f);
	Bog(On);
	On.bQueueClods = true;   // LM2b's bank sites, counted below (the field's clock stands at 0 here)
	Stroke(On);
	FGTMudField Off;
	Off.Init(Bounds, 12.5f);
	Bog(Off);
	Off.LumpShare = 0.f;
	Stroke(Off);
	TestTrue(TEXT("Bog numbers: LumpShare 0.35, ClodChance 0"), FMath::IsNearlyEqual(On.LumpShare, 0.35f) && On.ClodChance == 0.f);

	// 1. The volume: of what the stamps handed the bank's cells, the bank's ask and the lumps' hold add up to it, and every
	// cm^3 held landed (in the field now, flattened since by a later stamp of the stroke into its displaced volume, or over
	// LumpMaxCm into HeightCm).
	const FGTMudField::FLumpBook& Book = On.Book;
	const double Lowered = On.LoweredCm3;
	const double InField = LumpVolume(On);
	const double SplitError = FMath::Abs(Book.HandedCm3 - (Book.BankAskedCm3 + Book.LumpHeldCm3));
	const double LandError = FMath::Abs(Book.LumpHeldCm3 - (InField + Book.FlattenedCm3 + Book.LumpOverflowCm3));
	TestTrue(TEXT("A stroke's volume with lumps on: handed to the bank = banked + lumps within 0.1 % of the lowered volume"), SplitError <= 0.001 * Lowered);
	TestTrue(TEXT("A stroke's volume with lumps on: the lumps held = landed (in the field + flattened since + over the cap) within 0.1 % of the lowered volume"), LandError <= 0.001 * Lowered);
	TestTrue(TEXT("The lumps are there"), InField > 0.01 * Lowered);
	AddInfo(FString::Printf(TEXT("Lumps: narrow stroke, lowered %.0f cm^3 (the flattened lumps in it), deposit (RidgeReturn x lowered) %.0f; handed to the bank's cells %.0f = bank asked %.0f + lumps held %.0f (error %.1f cm^3 = %.4f %% of lowered); bank took %.0f (stage H's blend and the cap keep the rest, as before LM2a)"),
		Lowered, Book.DepositCm3, Book.HandedCm3, Book.BankAskedCm3, Book.LumpHeldCm3, SplitError, 100.0 * SplitError / FMath::Max(1.0, Lowered), Book.BankAddedCm3));
	AddInfo(FString::Printf(TEXT("Lumps: held %.0f cm^3 = in the field %.0f + flattened by later stamps %.0f + over LumpMaxCm into HeightCm %.0f (error %.1f cm^3 = %.4f %% of lowered); the deepest lump %.2f cm"),
		Book.LumpHeldCm3, InField, Book.FlattenedCm3, Book.LumpOverflowCm3, LandError, 100.0 * LandError / FMath::Max(1.0, Lowered), FMath::Max(On.LumpCm)));
	AddInfo(FString::Printf(TEXT("Lumps: the same stroke with LumpShare 0 - lowered %.0f vs %.0f cm^3 with lumps; standing above the ground (bank + lumps) %.0f vs %.0f; the field's volume %.0f vs %.0f cm^3"),
		Off.LoweredCm3, Lowered, Standing(Off), Standing(On), Volume(Off), Volume(On)));
	// LM3c follow-up, reported: the lumps' overflow over LumpMaxCm spreads over the stroke's band (bLumpOverflowToBand, on)
	// instead of piling into HeightCm in its own cell (LM2a, off). The narrow stroke's field CRC (HeightCm and LumpCm) both
	// ways, and how much overflowed: a mud field changes only where a lump overflows.
	{
		FGTMudField Same;
		Same.Init(Bounds, 12.5f);
		Bog(Same);
		Same.bQueueClods = true;
		Same.bLumpOverflowToBand = false;
		Stroke(Same);
		auto FieldCrc = [](const FGTMudField& Field)
		{
			const uint32 Crc = FCrc::MemCrc32(Field.HeightCm.GetData(), Field.HeightCm.Num() * sizeof(float));
			return FCrc::MemCrc32(Field.LumpCm.GetData(), Field.LumpCm.Num() * sizeof(float), Crc);
		};
		AddInfo(FString::Printf(TEXT("Lumps: overflow (LM3c follow-up) - the narrow stroke overflowed %.0f cm^3 over LumpMaxCm %.0f (LM2a's same-cell rule: %.0f); field CRC spread %08x, same-cell %08x; the highest bank cell %.2f vs %.2f cm, the field's volume %.0f vs %.0f cm^3"),
			On.Book.LumpOverflowCm3, On.LumpMaxCm, Same.Book.LumpOverflowCm3, FieldCrc(On), FieldCrc(Same), FMath::Max(On.HeightCm), FMath::Max(Same.HeightCm), Volume(On), Volume(Same)));
	}

	// 2. The bank's coefficient of variation along the crest: lumps 0.35 against 0, and stage I's clods 0.15 against 0.
	float MeanOn = 0.f, MeanOff = 0.f, MeanClods = 0.f;
	const float CvOn = CrestCv(On, MeanOn);
	const float CvOff = CrestCv(Off, MeanOff);
	FGTMudField Clods;
	Clods.Init(Bounds, 12.5f);
	Bog(Clods);
	Clods.LumpShare = 0.f;
	Clods.ClodChance = 0.15f;
	Stroke(Clods);
	const float CvClods = CrestCv(Clods, MeanClods);
	TestTrue(TEXT("The bank's coefficient of variation along the crest: LumpShare 0.35 at least 1.5x LumpShare 0"), CvOff > 0.f && CvOn >= 1.5f * CvOff);
	AddInfo(FString::Printf(TEXT("Lumps: crest along the +Y bank, cell by cell over 8 m - LumpShare 0.35: mean %.2f cm, cv %.3f; LumpShare 0: mean %.2f cm, cv %.3f; ratio %.2f (asked at least 1.5). Stage I's clods (LumpShare 0): ClodChance 0.15 mean %.2f cm, cv %.3f against ClodChance 0 cv %.3f, ratio %.2f"),
		MeanOn, CvOn, MeanOff, CvOff, CvOff > 0.f ? CvOn / CvOff : 0.f, MeanClods, CvClods, CvOff, CvOff > 0.f ? CvClods / CvOff : 0.f));
	{
		// For the main session: the same cv read on the bank's own crest line (the surface where the bank, without its
		// lumps, is highest), and the crest-max cv against the lumps' numbers.
		float LineOnMean = 0.f, LineOffMean = 0.f;
		const float LineOn = CrestLineCv(On, LineOnMean);
		const float LineOff = CrestLineCv(Off, LineOffMean);
		FString Sweep;
		for (const float Share : { 0.35f, 0.5f })
		{
			for (const float Spacing : { 3.f, 4.f, 5.f })
			{
				for (const float Radius : { 1.2f, 1.6f, 2.0f })
				{
					FGTMudField Try;
					Try.Init(Bounds, 12.5f);
					Bog(Try);
					Try.LumpShare = Share;
					Try.LumpSpacingCells = Spacing;
					Try.LumpRadiusCells = Radius;
					Stroke(Try);
					float TryMean = 0.f, TryLineMean = 0.f;
					const float TryCv = CrestCv(Try, TryMean);
					const float TryLine = CrestLineCv(Try, TryLineMean);
					Sweep += FString::Printf(TEXT("%sshare %.2f spacing %.0f radius %.1f: cv %.3f (x%.2f), line cv %.3f (x%.2f), crest %.2f cm"), Sweep.IsEmpty() ? TEXT("") : TEXT("; "),
						Share, Spacing, Radius, TryCv, CvOff > 0.f ? TryCv / CvOff : 0.f, TryLine, LineOff > 0.f ? TryLine / LineOff : 0.f, TryMean);
				}
			}
		}
		AddInfo(FString::Printf(TEXT("Lumps: on the bank's crest line - LumpShare %.2f cv %.3f (mean %.2f cm), LumpShare 0 cv %.3f (mean %.2f cm), ratio %.2f"),
			On.LumpShare, LineOn, LineOnMean, LineOff, LineOffMean, LineOff > 0.f ? LineOn / LineOff : 0.f));
		AddInfo(TEXT("Lumps: sweep - ") + Sweep);
	}

	// 3. The lumps after 10 s settled, bog numbers: their height on the cells that carried a lump of 1 cm or more.
	{
		FGTMudField Settled = On;
		TArray<int32> Lumped;
		double Before = 0.0;
		float PeakBefore = 0.f;
		for (int32 Index = 0; Index < Settled.LumpCm.Num(); ++Index)
		{
			if (Settled.LumpCm[Index] >= 1.f)
			{
				Lumped.Add(Index);
				Before += Settled.LumpCm[Index];
				PeakBefore = FMath::Max(PeakBefore, Settled.LumpCm[Index]);
			}
		}
		const double VolumeBefore = Volume(Settled);
		const double LumpsBefore = LumpVolume(Settled);
		SettleFor(Settled, 10.f, 1.f / 30.f);
		double After = 0.0;
		float PeakAfter = 0.f;
		for (const int32 Index : Lumped)
		{
			After += Settled.LumpCm[Index];
			PeakAfter = FMath::Max(PeakAfter, Settled.LumpCm[Index]);
		}
		const float Kept = Before > 0.0 ? static_cast<float>(After / Before) : 0.f;
		const double VolumeError = FMath::Abs(Volume(Settled) - VolumeBefore);
		TestTrue(TEXT("Lumps after 10 s settled keep at least 60 % of their height (bog numbers)"), Lumped.Num() > 0 && Kept >= 0.6f);
		TestTrue(TEXT("Settling with lumps keeps the volume within 0.1 % of the stroke's lowered volume"), VolumeError <= 0.001 * Lowered);
		AddInfo(FString::Printf(TEXT("Lumps: %d cells with a lump of 1 cm or more, mean %.2f cm just stamped -> %.2f cm after 10 s settled = %.1f %% kept (asked at least 60); the highest %.2f -> %.2f cm; all lumps %.0f -> %.0f cm^3; the surface's volume error %.1f cm^3"),
			Lumped.Num(), Before / FMath::Max(1, Lumped.Num()), After / FMath::Max(1, Lumped.Num()), 100.f * Kept, PeakBefore, PeakAfter, LumpsBefore, LumpVolume(Settled), VolumeError));
	}

	// 4. A second capsule over the lumps: one stamp along the +Y bank where its lumps are thickest, on the field as stamped
	// (A) and on a copy whose lumps were taken out (B: the same heights). Under it LumpCm is 0, and what it displaced (so
	// what it handed the bank) is B's plus exactly the lumps it flattened.
	{
		const float TyreCm = 28.f;
		const float Radius = 0.5f * TyreCm;
		float BestY = 0.f;
		double BestLumps = -1.0;
		for (float Y = 62.5f; Y <= 200.f; Y += 6.25f)
		{
			double Sum = 0.0;
			for (const int32 Index : CellsUnder(On, FVector2D(400.0, Y), FVector2D(470.0, Y), Radius))
			{
				Sum += On.LumpCm[Index];
			}
			if (Sum > BestLumps)
			{
				BestLumps = Sum;
				BestY = Y;
			}
		}
		const FVector2D From(400.0, BestY);
		const FVector2D To(470.0, BestY);
		FGTMudField A = On;
		FGTMudField B = On;
		for (float& Lump : B.LumpCm)
		{
			Lump = 0.f;
		}
		const TArray<int32> Under = CellsUnder(A, From, To, Radius);
		int32 LumpedBefore = 0;
		double UnderBefore = 0.0;
		for (const int32 Index : Under)
		{
			LumpedBefore += A.LumpCm[Index] > 0.f ? 1 : 0;
			UnderBefore += A.LumpCm[Index];
		}
		const double FlatBefore = A.Book.FlattenedCm3;
		const double DepABefore = A.Book.DepositCm3;
		const double DepBBefore = B.Book.DepositCm3;
		const double RemovedA = A.StampWheel(From, To, TyreCm, 20.f, FVector2D(1.0, 0.0), 0.f);
		const double RemovedB = B.StampWheel(From, To, TyreCm, 20.f, FVector2D(1.0, 0.0), 0.f);
		const double FlatA = A.Book.FlattenedCm3 - FlatBefore;
		const double DepA = A.Book.DepositCm3 - DepABefore;
		const double DepB = B.Book.DepositCm3 - DepBBefore;
		float UnderAfter = 0.f;
		for (const int32 Index : Under)
		{
			UnderAfter = FMath::Max(UnderAfter, A.LumpCm[Index]);
		}
		const double DisplacedError = FMath::Abs((RemovedA - RemovedB) - FlatA);
		const double BankError = FMath::Abs((DepA - DepB) - A.RidgeReturn * FlatA);
		TestTrue(TEXT("A second capsule over lumps: LumpCm 0 under it"), LumpedBefore > 0 && UnderAfter == 0.f);
		TestTrue(TEXT("A second capsule over lumps: their volume in the new bank (displaced = B's + the flattened lumps, and RidgeReturn of it handed to the bank, within 0.1 %)"),
			FlatA > 0.0 && DisplacedError <= 0.001 * RemovedA && BankError <= 0.001 * FMath::Max(1.0, DepA));
		AddInfo(FString::Printf(TEXT("Lumps: a second 70 cm capsule at y %.2f cm over the +Y bank - %d of %d cells under the tyre carried lumps (%.0f cm^3 under the tyre alone), the highest after it %.3f cm; it flattened %.0f cm^3 of lumps (its bowl and shoulders); displaced %.0f vs %.0f with the lumps taken out, difference %.0f (error %.2f cm^3); handed the bank %.0f vs %.0f, difference %.0f = RidgeReturn %.2f x %.0f (error %.2f cm^3)"),
			BestY, LumpedBefore, Under.Num(), UnderBefore * On.CellCm * On.CellCm, UnderAfter, FlatA, RemovedA, RemovedB, RemovedA - RemovedB, DisplacedError,
			DepA, DepB, DepA - DepB, A.RidgeReturn, FlatA, BankError));
	}

	// LM2b's bank sites, as the stroke queued them (the field's clock at 0, so each site at most once).
	{
		float MinSize = 1000.f, MaxSize = 0.f;
		for (const FGTMudField::FClodSpawn& Spawn : On.PendingClods)
		{
			MinSize = FMath::Min(MinSize, Spawn.SizeCm);
			MaxSize = FMath::Max(MaxSize, Spawn.SizeCm);
		}
		AddInfo(FString::Printf(TEXT("Lumps: bank clods the narrow stroke queued: %d (sizes %.1f-%.1f cm; LM2c %d: lip cells at ClodBankPerCm %.4f per cm of deposit, else LM2b's ClodBankChance %.2f per %.1f cm of lump at a site's top)"),
			On.PendingClods.Num(), On.PendingClods.Num() ? MinSize : 0.f, MaxSize, On.bLumpVariety ? 1 : 0, On.ClodBankPerCm, On.ClodBankChance, On.ClodBankMinCm));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudThrowTest, "GrandTour.Mud.Throw",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTMudThrowTest::RunTest(const FString& Parameters)
{
	using namespace GTMudSettleTest;
	using namespace GTMudLumpTest;

	// 5. ThrowShare 0.5 against 0: one 100 cm stroke in one call (one capsule, so the second half of a stroke does not
	// re-cut what the first half deposited), 15 cm deep, on fresh fields, bog numbers.
	struct FOne
	{
		double Lowered = 0.0, Thrown = 0.0, Deposit = 0.0, Standing = 0.0;
		TArray<float> Heights;
	};
	auto One = [](float Share, bool bOldCall)
	{
		FOne Out;
		FGTMudField Field;
		Field.Init(Bounds, 12.5f);
		Bog(Field);
		Out.Lowered = bOldCall ? Field.StampWheel(FVector2D(300.0, 0.0), FVector2D(400.0, 0.0), 28.f, 15.f, FVector2D(1.0, 0.0), 0.f)
			: Field.StampWheel(FVector2D(300.0, 0.0), FVector2D(400.0, 0.0), 28.f, 15.f, FVector2D(1.0, 0.0), 0.f, Share, Out.Thrown);
		Out.Deposit = Field.Book.DepositCm3;
		Out.Standing = Standing(Field);
		Out.Heights = Field.HeightCm;
		for (int32 Index = 0; Index < Field.LumpCm.Num(); ++Index)
		{
			Out.Heights[Index] += Field.LumpCm[Index];
		}
		return Out;
	};
	const FOne Old = One(0.f, true);
	const FOne Zero = One(0.f, false);
	const FOne Half = One(0.5f, false);
	TestTrue(TEXT("ThrowShare 0 is the stroke without it, to the bit, and returns nothing"), Zero.Heights == Old.Heights && Zero.Thrown == 0.0);
	TestTrue(TEXT("The same lowered volume either way"), FMath::IsNearlyEqual(Half.Lowered, Zero.Lowered, 1.e-6 * Zero.Lowered));
	const double Difference = Zero.Deposit - Half.Deposit;
	TestTrue(TEXT("ThrowShare 0.5: bank deposit halved vs 0 (what the stamp hands the bank, and what stands above the ground, within 0.1 %)"),
		FMath::Abs(Half.Deposit - 0.5 * Zero.Deposit) <= 0.001 * Zero.Deposit && FMath::Abs(Half.Standing - 0.5 * Zero.Standing) <= 0.001 * Zero.Standing);
	TestTrue(TEXT("ThrowShare 0.5: OutThrown equals the difference within 0.1 %"), Difference > 0.0 && FMath::Abs(Half.Thrown - Difference) <= 0.001 * Difference);
	AddInfo(FString::Printf(TEXT("Throw: one 100 cm capsule 15 cm deep - lowered %.0f / %.0f cm^3; handed to the bank %.0f at ThrowShare 0, %.0f at 0.5 (ratio %.5f); standing above the ground %.0f / %.0f (ratio %.5f); OutThrown %.0f against the difference %.0f (error %.3f %%)"),
		Zero.Lowered, Half.Lowered, Zero.Deposit, Half.Deposit, Half.Deposit / FMath::Max(1.0, Zero.Deposit), Zero.Standing, Half.Standing,
		Half.Standing / FMath::Max(1.0, Zero.Standing), Half.Thrown, Difference, 100.0 * FMath::Abs(Half.Thrown - Difference) / FMath::Max(1.0, Difference)));
	{
		// The whole narrow stroke at 0.5, for scale (a spinning wheel's every stamp throws half its bank).
		FGTMudField Field;
		Field.Init(Bounds, 12.5f);
		Bog(Field);
		double Thrown = 0.0;
		for (int32 I = 0; I < 200; ++I)
		{
			double Out = 0.0;
			Field.StampWheel(FVector2D(I * 5.f, 0.0), FVector2D(I * 5.f + 5.f, 0.0), 28.f, NarrowCm, FVector2D(1.0, 0.0), I * 5.f, 0.5f, Out);
			Thrown += Out;
		}
		AddInfo(FString::Printf(TEXT("Throw: the narrow stroke (200 stamps) at ThrowShare 0.5 - lowered %.0f cm^3, thrown %.0f (the field's book %.0f), handed the bank %.0f"),
			Field.LoweredCm3, Thrown, Field.Book.ThrownCm3, Field.Book.DepositCm3));
	}

	// 6. DepositThrown (AGTMudPatch::DepositThrown is this call with 1.5 x the blob's radius, plus the clod roll): a 10 cm
	// blob, a 6 cm one smaller than a cell, and a 3,000 cm^3 lump into one cell (over LumpMaxCm), each exactly its volume.
	{
		FGTMudField Field;
		Field.Init(Bounds, 12.5f);
		Bog(Field);
		struct FDrop
		{
			FVector2D XY;
			double Volume;
			float DomeCm;
		};
		const double Blob10 = 4.0 / 3.0 * PI * 5.0 * 5.0 * 5.0 * 0.6;
		const double Blob6 = 4.0 / 3.0 * PI * 3.0 * 3.0 * 3.0 * 0.6;
		const FDrop Drops[3] = { { FVector2D(500.3, 20.7), Blob10, 1.5f * 5.f }, { FVector2D(700.0, 100.0), Blob6, 1.5f * 3.f }, { FVector2D(300.0, -100.0), 3000.0, 0.f } };
		double WorstError = 0.0;
		bool bFresh = true;
		FString Text;
		for (const FDrop& Drop : Drops)
		{
			const double Before = Volume(Field);
			const double Put = Field.DepositLump(Drop.XY, Drop.Volume, Drop.DomeCm);
			const double Added = Volume(Field) - Before;
			const double Error = FMath::Abs(Added - Drop.Volume);
			WorstError = FMath::Max(WorstError, Error / Drop.Volume);
			const int32 Cell = Field.CellIndexAt(Drop.XY);
			bFresh &= Field.Fresh[Cell] == 1.f;
			Text += FString::Printf(TEXT("%s%.1f cm^3 (dome %.1f cm) put %.1f, the surface rose %.3f cm^3 (error %.5f %%), lump at the cell %.2f cm"), Text.IsEmpty() ? TEXT("") : TEXT("; "),
				Drop.Volume, Drop.DomeCm, Put, Added, 100.0 * Error / Drop.Volume, Field.LumpCm[Cell]);
		}
		TestTrue(TEXT("DepositThrown adds exactly its volume (within 0.1 %)"), WorstError <= 0.001);
		TestTrue(TEXT("DepositThrown marks its cells fresh (1) and wakes their tiles"), bFresh && Field.AwakeTileCount() > 0);
		TestTrue(TEXT("DepositThrown outside the field puts nothing down"), Field.DepositLump(FVector2D(5000.0, 5000.0), Blob10, 7.5f) == 0.0);
		AddInfo(TEXT("Throw: DepositThrown - ") + Text + FString::Printf(TEXT("; over LumpMaxCm into HeightCm %.1f cm^3; %d tiles awake"), Field.Book.LumpOverflowCm3, Field.AwakeTileCount()));
		// Settled, the drops keep their volume (the talus takes the 3,000 cm^3 lump down first).
		const double Before = Volume(Field);
		SettleFor(Field, 10.f, 1.f / 30.f);
		const double SettledError = FMath::Abs(Volume(Field) - Before);
		TestTrue(TEXT("Settling the drops keeps their volume within 0.1 %"), SettledError <= 0.001 * (Blob10 + Blob6 + 3000.0));
		AddInfo(FString::Printf(TEXT("Throw: the drops settled 10 s - volume error %.3f cm^3, the 3,000 cm^3 cell's lump %.2f cm, all lumps %.1f cm^3"),
			SettledError, Field.LumpCm[Field.CellIndexAt(FVector2D(300.0, -100.0))], LumpVolume(Field)));
	}
	return true;
}

// LM2c, break the uniformity (docs/LIVING_MUD_PLAN.md, the LM2c table). Every row is read on the strip-like broad stroke
// (15 cm) over four NoiseSeeds pooled, with the LM2c features on (the shipped bog numbers) and off (LM2a/LM2b's exact
// path, the comparison); the narrow stroke (40 cm, lumps at the 10 cm cap) is printed beside it.
namespace GTMudVarietyTest
{
	using namespace GTMudSettleTest;

	struct FStats
	{
		int32 N = 0;
		double Mean = 0.0;
		double Sd = 0.0;
		double Cv() const { return Mean > 0.0 ? Sd / Mean : 0.0; }
	};

	FStats Stats(const TArray<double>& Values)
	{
		FStats Out;
		Out.N = Values.Num();
		if (Out.N == 0)
		{
			return Out;
		}
		double Sum = 0.0;
		for (const double V : Values)
		{
			Sum += V;
		}
		Out.Mean = Sum / Out.N;
		double Var = 0.0;
		for (const double V : Values)
		{
			Var += (V - Out.Mean) * (V - Out.Mean);
		}
		Out.Sd = FMath::Sqrt(Var / Out.N);
		return Out;
	}

	struct FRun
	{
		TArray<double> PeakSpacing, PeakHeight, ClodSize, ClodGap;
		TArray<double> PeakSpacing5, PeakHeight5, PeakAlong;   // the peaks read over 5x5 (a satellite merges into its parent) and the gaps along the crest
		int32 Peaks = 0, Peaks5 = 0, Queued = 0, Kept = 0, Seeds = 0;
		int32 SitesBuilt = 0, SitesAbsent = 0, Satellites = 0;
		double ExpectPerRate = 0.0, SplitError = 0.0, LandError = 0.0, Lowered = 0.0;
		bool bSame = true;
	};

	/**
	 * The LM2c follow-up's tuning table (info): the absent share swept over 0.35-0.55 (GAbsent; -1 is the shipped value) and
	 * LM2c off (GVarietyOff), each read for the spacing, SoftShoulders' cross-step, the narrow stroke's detail kept and the
	 * stage I crest cv proxy below. The shipped rows above are read with neither.
	 */
	float GAbsent = -1.f;
	bool GVarietyOff = false;
	void Ablate(FGTMudField& Field)
	{
		if (GVarietyOff)
		{
			Field.bLumpVariety = false;
		}
		if (GAbsent >= 0.f)
		{
			Field.LumpAbsentShare = GAbsent;
		}
	}
	/**
	 * The terrain test's stage I crest cv (GTM6TestRunner, the shipped spot A), as a proxy: a 660 cm line in 33 uneven
	 * strokes (its weights), a 25 cm tyre 30 cm deep, then per along-cell step over the middle 6 m the highest cell from
	 * 15 cm out to the band's reach on one side; sd / mean. On a straight line along X here (the terrain's is diagonal).
	 */
	float CrestCvStageI(int32 Seed)
	{
		FGTMudField Field;
		Field.Init(Bounds, 12.5f);
		Bog(Field);
		Field.NoiseSeed = Seed;
		Ablate(Field);
		static const float StrokeWeights[18] = { 0.35f, 1.70f, 0.60f, 1.40f, 0.45f, 1.85f, 0.70f, 1.25f, 0.40f,
			1.60f, 0.90f, 1.10f, 0.50f, 1.75f, 0.65f, 1.30f, 0.55f, 1.45f };
		const float LineCm = 660.f;
		const float SpanCm = 600.f;
		const FVector2D Spot(500.0, 0.0);
		const FVector2D Along(1.0, 0.0);
		const FVector2D Left(0.0, 1.0);
		float WeightTotal = 0.f;
		for (int32 Stroke = 0; Stroke < 33; ++Stroke)
		{
			WeightTotal += StrokeWeights[Stroke % 18];
		}
		float Rolled = 0.f;
		for (int32 Stroke = 0; Stroke < 33; ++Stroke)
		{
			const float StrokeCm = LineCm * StrokeWeights[Stroke % 18] / WeightTotal;
			const FVector2D P0 = Spot + Along * (-0.5f * LineCm + Rolled);
			Field.StampWheel(P0, P0 + Along * StrokeCm, 25.f, 30.f, Along, Rolled);
			Rolled += StrokeCm;
		}
		TArray<float> Heights;
		int32 LastIndex = INDEX_NONE;
		const float BandCm = 12.5f + Field.RidgeBandCm();
		for (float T = -0.5f * SpanCm; T <= 0.5f * SpanCm + 0.1f; T += 0.25f * Field.CellCm)
		{
			const int32 AxisIndex = Field.CellIndexAt(Spot + Along * T);
			if (AxisIndex == LastIndex || AxisIndex == INDEX_NONE)
			{
				continue;
			}
			LastIndex = AxisIndex;
			float Best = -1000.f;
			for (float Out = 15.f; Out <= BandCm + 0.1f; Out += 0.25f * Field.CellCm)
			{
				Best = FMath::Max(Best, Field.CellHeightCm(Field.CellIndexAt(Spot + Along * T + Left * Out)));
			}
			Heights.Add(Best);
		}
		double Mean = 0.0;
		for (const float H : Heights)
		{
			Mean += H;
		}
		Mean /= FMath::Max(1, Heights.Num());
		double Sq = 0.0;
		for (const float H : Heights)
		{
			Sq += FMath::Square(H - Mean);
		}
		return Mean > 0.1 ? static_cast<float>(FMath::Sqrt(Sq / FMath::Max(1, Heights.Num())) / Mean) : 0.f;
	}
	void BogAblated(FGTMudField& Field)
	{
		Bog(Field);
		Ablate(Field);
	}
	/** SoftShoulders' stroke and measure (the field's own numbers, 40 cm asked), the worst 12.5 cm cross-step and where. */
	float CrossStep(float& OutY, float& OutLump)
	{
		FGTMudField A;
		A.Init(Bounds, 12.5f);
		Ablate(A);
		for (int32 I = 0; I < 200; ++I)
		{
			A.StampWheel(FVector2D(I * 5.f, 0), FVector2D(I * 5.f + 5.f, 0), 28.f, 40.f, FVector2D(1, 0), I * 5.f);
		}
		float Worst = 0.f;
		for (float X = 100; X <= 900; X += 25)
		{
			for (float Y = -100; Y <= 100; Y += 6.25f)
			{
				const float Step = FMath::Abs(A.HeightAt(FVector2D(X, Y)) - A.HeightAt(FVector2D(X, Y + 12.5f)));
				if (Step > Worst)
				{
					Worst = Step;
					OutY = Y;
					OutLump = FMath::Max(A.LumpAt(FVector2D(X, Y)), A.LumpAt(FVector2D(X, Y + 12.5f)));
				}
			}
		}
		return Worst;
	}

	/** One stroke on a fresh bog field, its lump peaks and its bank clods added to Run. */
	void One(FRun& Run, bool bVariety, float DepthCm, int32 Seed)
	{
		auto Make = [&](FGTMudField& Field)
		{
			Field.Init(Bounds, 12.5f);
			Bog(Field);
			Field.NoiseSeed = Seed;
			Field.bLumpVariety = bVariety;
			Ablate(Field);
			Field.bQueueClods = true;
			Field.MaxPendingClods = 100000;
			Stroke(Field, DepthCm);
		};
		FGTMudField Field;
		Make(Field);
		++Run.Seeds;
		// Determinism: the same stroke again, to the bit (the lumps, the bank, the queued clods).
		{
			FGTMudField Again;
			Make(Again);
			bool bSame = Again.HeightCm == Field.HeightCm && Again.LumpCm == Field.LumpCm && Again.PendingClods.Num() == Field.PendingClods.Num();
			for (int32 K = 0; bSame && K < Field.PendingClods.Num(); ++K)
			{
				const FGTMudField::FClodSpawn& A = Field.PendingClods[K];
				const FGTMudField::FClodSpawn& B = Again.PendingClods[K];
				bSame = A.XYCm == B.XYCm && A.SizeCm == B.SizeCm && A.Seed == B.Seed && A.Source == B.Source;
			}
			Run.bSame &= bSame;
		}
		// Volume as LM2a: the bank's cells' share = bank asked + lumps held, and the held = in the field + flattened + over the cap.
		const FGTMudField::FLumpBook& Book = Field.Book;
		Run.Lowered += Field.LoweredCm3;
		Run.SplitError = FMath::Max(Run.SplitError, FMath::Abs(Book.HandedCm3 - (Book.BankAskedCm3 + Book.LumpHeldCm3)) / FMath::Max(1.0, Field.LoweredCm3));
		Run.LandError = FMath::Max(Run.LandError, FMath::Abs(Book.LumpHeldCm3 - (LumpVolume(Field) + Book.FlattenedCm3 + Book.LumpOverflowCm3)) / FMath::Max(1.0, Field.LoweredCm3));
		Run.SitesBuilt += Field.LumpSitesBuilt;
		Run.SitesAbsent += Field.LumpSitesAbsent;
		Run.Satellites += Field.LumpSatellites;
		Run.ExpectPerRate += Field.ClodBankExpectPerRate;
		// The lump peaks on the two banks over the stroke's middle 8 m: cells with at least 0.25 cm of lump that top every
		// cell round them (a tie goes to the lower index, so a plateau at the cap is one peak). Asserted over 3x3 (the plain
		// local maximum: a satellite's top is its own peak); 5x5 printed beside it. Per bank, each peak's nearest neighbour.
		const int32 SX = Field.SizeX;
		const int32 SY = Field.SizeY;
		for (const int32 Reach : { 1, 2 })
		{
			TArray<FVector2D> PeaksPos[2];
			TArray<double>& Heights = Reach == 1 ? Run.PeakHeight : Run.PeakHeight5;
			TArray<double>& Spacing = Reach == 1 ? Run.PeakSpacing : Run.PeakSpacing5;
			for (int32 Y = 2; Y < SY - 2; ++Y)
			{
				for (int32 X = 2; X < SX - 2; ++X)
				{
					const int32 Index = Y * SX + X;
					const float L = Field.LumpCm[Index];
					if (L < 0.25f)
					{
						continue;
					}
					const FVector2D P = Field.CellCentreCm(Index);
					const double Off = FMath::Abs(P.Y);
					if (P.X < 100.0 || P.X > 900.0 || Off < 6.25 || Off > 340.0)
					{
						continue;
					}
					bool bPeak = true;
					for (int32 DY = -Reach; bPeak && DY <= Reach; ++DY)
					{
						for (int32 DX = -Reach; DX <= Reach; ++DX)
						{
							const int32 N = (Y + DY) * SX + X + DX;
							if (N == Index)
							{
								continue;
							}
							const float LN = Field.LumpCm[N];
							if (LN > L || (LN == L && N < Index))
							{
								bPeak = false;
								break;
							}
						}
					}
					if (bPeak)
					{
						PeaksPos[P.Y > 0.0 ? 0 : 1].Add(P);
						Heights.Add(L);
					}
				}
			}
			for (int32 Side = 0; Side < 2; ++Side)
			{
				const TArray<FVector2D>& Ps = PeaksPos[Side];
				(Reach == 1 ? Run.Peaks : Run.Peaks5) += Ps.Num();
				for (int32 I = 0; I < Ps.Num(); ++I)
				{
					double Best = TNumericLimits<double>::Max();
					for (int32 J = 0; J < Ps.Num(); ++J)
					{
						if (J != I)
						{
							Best = FMath::Min(Best, FVector2D::Distance(Ps[I], Ps[J]));
						}
					}
					if (Ps.Num() > 1)
					{
						Spacing.Add(Best);
					}
				}
				if (Reach == 1)
				{
					TArray<double> Xs;
					for (const FVector2D& P : Ps)
					{
						Xs.Add(P.X);
					}
					Xs.Sort();
					for (int32 K = 1; K < Xs.Num(); ++K)
					{
						Run.PeakAlong.Add(Xs[K] - Xs[K - 1]);
					}
				}
			}
		}
		// The bank clods the stroke queued, kept where the bank still stands at the end (not on its own rut: a later capsule
		// squashes those in the patch); their sizes, and the gaps between them along the stroke on each bank.
		TArray<double> Along[2];
		for (const FGTMudField::FClodSpawn& Spawn : Field.PendingClods)
		{
			if (Spawn.Source != 0)
			{
				continue;
			}
			++Run.Queued;
			const int32 Cell = Field.CellIndexAt(Spawn.XYCm);
			if (Field.HeightCm[Cell] < -1.f)
			{
				continue;
			}
			++Run.Kept;
			Run.ClodSize.Add(Spawn.SizeCm);
			Along[Spawn.XYCm.Y > 0.0 ? 0 : 1].Add(Spawn.XYCm.X);
		}
		for (int32 Side = 0; Side < 2; ++Side)
		{
			Along[Side].Sort();
			for (int32 K = 1; K < Along[Side].Num(); ++K)
			{
				Run.ClodGap.Add(Along[Side][K] - Along[Side][K - 1]);
			}
		}
	}

	FRun Runs(bool bVariety, float DepthCm)
	{
		FRun Run;
		for (int32 Seed = 1; Seed <= 4; ++Seed)
		{
			One(Run, bVariety, DepthCm, Seed);
		}
		return Run;
	}

	FString Describe(const TCHAR* Name, const FRun& Run)
	{
		const FStats Spacing = Stats(Run.PeakSpacing);
		const FStats Height = Stats(Run.PeakHeight);
		const FStats Size = Stats(Run.ClodSize);
		const FStats Gap = Stats(Run.ClodGap);
		const FStats Spacing5 = Stats(Run.PeakSpacing5);
		const FStats Height5 = Stats(Run.PeakHeight5);
		const FStats Along = Stats(Run.PeakAlong);
		return FString::Printf(TEXT("%s: %d lump peaks (3x3), nearest-neighbour spacing mean %.1f cm cv %.3f, heights mean %.2f cm cv %.3f, gaps along the crest cv %.3f; over 5x5 %d peaks, spacing cv %.3f, heights cv %.3f; sites %d built / %d absent (%.1f %%), %d satellites; bank clods %d queued, %d kept = %.2f per m of stroke, sizes mean %.2f cm cv %.3f (%.1f-%.1f), gaps along the stroke mean %.1f cm cv %.3f"),
			Name, Run.Peaks, Spacing.Mean, Spacing.Cv(), Height.Mean, Height.Cv(), Along.Cv(), Run.Peaks5, Spacing5.Cv(), Height5.Cv(), Run.SitesBuilt, Run.SitesAbsent,
			100.0 * Run.SitesAbsent / FMath::Max(1, Run.SitesBuilt + Run.SitesAbsent), Run.Satellites, Run.Queued, Run.Kept, Run.Kept / (10.0 * FMath::Max(1, Run.Seeds)),
			Size.Mean, Size.Cv(), Run.ClodSize.Num() ? FMath::Min(Run.ClodSize) : 0.0, Run.ClodSize.Num() ? FMath::Max(Run.ClodSize) : 0.0, Gap.Mean, Gap.Cv());
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudVarietyTest, "GrandTour.Mud.Variety",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTMudVarietyTest::RunTest(const FString& Parameters)
{
	using namespace GTMudSettleTest;
	using namespace GTMudVarietyTest;

	const AGTMudPatch* Patch = GetDefault<AGTMudPatch>();
	TestTrue(TEXT("The bog ships LM2c on (bLumpVariety)"), Patch->bLumpVariety);
	const FRun On = Runs(true, BroadCm);
	const FRun Off = Runs(false, BroadCm);
	const FRun NarrowOn = Runs(true, NarrowCm);
	const FRun NarrowOff = Runs(false, NarrowCm);
	AddInfo(TEXT("Variety: broad stroke (15 cm), seeds 1-4 pooled - ") + Describe(TEXT("LM2c"), On));
	AddInfo(TEXT("Variety: broad stroke (15 cm), seeds 1-4 pooled - ") + Describe(TEXT("LM2 (LM2c off)"), Off));
	AddInfo(TEXT("Variety: narrow stroke (40 cm), seeds 1-4 pooled - ") + Describe(TEXT("LM2c"), NarrowOn));
	AddInfo(TEXT("Variety: narrow stroke (40 cm), seeds 1-4 pooled - ") + Describe(TEXT("LM2 (LM2c off)"), NarrowOff));

	const double SpacingOn = Stats(On.PeakSpacing).Cv(), SpacingOff = Stats(Off.PeakSpacing).Cv();
	const double HeightOn = Stats(On.PeakHeight).Cv(), HeightOff = Stats(Off.PeakHeight).Cv();
	const double SizeOn = Stats(On.ClodSize).Cv(), SizeOff = Stats(Off.ClodSize).Cv();
	const double GapOn = Stats(On.ClodGap).Cv(), GapOff = Stats(Off.ClodGap).Cv();
	const double PerMOn = On.Kept / (10.0 * On.Seeds), PerMOff = Off.Kept / (10.0 * Off.Seeds);
	const double Ratio = PerMOff > 0.0 ? PerMOn / PerMOff : 0.0;
	TestTrue(TEXT("Lump peaks along a crest: CV of the nearest-neighbour spacing at least 0.45"), On.PeakSpacing.Num() > 10 && SpacingOn >= 0.45);
	TestTrue(TEXT("Lump peak heights: CV at least 0.5"), On.PeakHeight.Num() > 10 && HeightOn >= 0.5);
	TestTrue(TEXT("Bank clod sizes: CV at least 0.5"), On.ClodSize.Num() > 10 && SizeOn >= 0.5);
	TestTrue(TEXT("Bank clod spacing along the stroke: CV at least 0.6 (clustered)"), On.ClodGap.Num() > 10 && GapOn >= 0.6);
	TestTrue(TEXT("Bank clods per metre of stroke: about a third of LM2's (0.25-0.42x)"), Ratio >= 0.25 && Ratio <= 0.42);
	TestTrue(TEXT("Volume as LM2a: handed = bank asked + lumps held, held = in the field + flattened + over the cap, within 0.1 % of lowered (both strokes)"),
		On.SplitError <= 0.001 && On.LandError <= 0.001 && NarrowOn.SplitError <= 0.001 && NarrowOn.LandError <= 0.001);
	TestTrue(TEXT("Determinism: the same stroke twice is the same field and the same clods, to the bit (both strokes, LM2c on and off)"), On.bSame && Off.bSame && NarrowOn.bSame && NarrowOff.bSame);
	// The rate that would land a third exactly, for the main session (the chance is in proportion to the rate below 1).
	const double Rate = Patch->ClodBankPerCm;
	const double Third = PerMOn > 0.0 ? Rate * (PerMOff / 3.0) / PerMOn : 0.0;
	AddInfo(FString::Printf(TEXT("Variety: LM2 vs LM2c (broad, asserted) - peak spacing cv %.3f vs %.3f (asked at least 0.45); peak heights cv %.3f vs %.3f (asked at least 0.5); bank clod sizes cv %.3f vs %.3f (asked at least 0.5); bank clod gaps cv %.3f vs %.3f (asked at least 0.6); bank clods per m %.2f vs %.2f = %.2fx (asked about a third); volume split error %.6f %% / landed %.6f %% of lowered; deterministic %d"),
		SpacingOff, SpacingOn, HeightOff, HeightOn, SizeOff, SizeOn, GapOff, GapOn, PerMOff, PerMOn, Ratio, 100.0 * On.SplitError, 100.0 * On.LandError, On.bSame && Off.bSame ? 1 : 0));
	AddInfo(FString::Printf(TEXT("Variety: LM2 vs LM2c (narrow, reported) - peak spacing cv %.3f vs %.3f; peak heights cv %.3f vs %.3f; clod sizes cv %.3f vs %.3f; clod gaps cv %.3f vs %.3f; per m %.2f vs %.2f = %.2fx; ClodBankPerCm %.4f (expected per unit rate %.1f broad / %.1f narrow over 4 strokes); a third exactly on the broad stroke at %.4f"),
		Stats(NarrowOff.PeakSpacing).Cv(), Stats(NarrowOn.PeakSpacing).Cv(), Stats(NarrowOff.PeakHeight).Cv(), Stats(NarrowOn.PeakHeight).Cv(),
		Stats(NarrowOff.ClodSize).Cv(), Stats(NarrowOn.ClodSize).Cv(), Stats(NarrowOff.ClodGap).Cv(), Stats(NarrowOn.ClodGap).Cv(),
		NarrowOff.Kept / 40.0, NarrowOn.Kept / 40.0, NarrowOff.Kept > 0 ? static_cast<double>(NarrowOn.Kept) / NarrowOff.Kept : 0.0, Rate, On.ExpectPerRate, NarrowOn.ExpectPerRate, Third));
	// The LM2c follow-up's tuning table (info): LM2 and the absent share over 0.35-0.55, each with the spacing cv, the
	// SoftShoulders cross-step (asked < 24 cm), the narrow stroke's detail kept with lumps on (asked 0.9-1.1), the stage I
	// crest cv proxy over seeds 1-4 (asked 0.22-0.60; the terrain test's own read is the gate) and the bank clods per metre.
	{
		FString Text;
		for (int32 Row = -1; Row < 5; ++Row)
		{
			GVarietyOff = Row < 0;
			GAbsent = Row < 0 ? -1.f : 0.35f + 0.05f * Row;
			const FRun Broad = Runs(true, BroadCm);
			float StepY = 0.f, StepLump = 0.f;
			const float Step = CrossStep(StepY, StepLump);
			const FStrokeRun Narrow = RunStroke(&BogAblated, NarrowCm, -1.f, -1.f, -1.f);
			float CrestMin = 1000.f, CrestMax = 0.f, CrestSum = 0.f;
			for (int32 Seed = 1; Seed <= 4; ++Seed)
			{
				const float Cv = CrestCvStageI(Seed);
				CrestMin = FMath::Min(CrestMin, Cv);
				CrestMax = FMath::Max(CrestMax, Cv);
				CrestSum += Cv;
			}
			Text += FString::Printf(TEXT("%s%s: spacing cv %.3f, heights cv %.3f, cross-step %.2f cm (lump %.2f), narrow D kept %.3f, stage I crest cv %.3f (%.3f-%.3f), bank clods %.2f per m"),
				Text.IsEmpty() ? TEXT("") : TEXT("; "), Row < 0 ? TEXT("LM2") : *FString::Printf(TEXT("absent %.2f"), GAbsent), Stats(Broad.PeakSpacing).Cv(), Stats(Broad.PeakHeight).Cv(),
				Step, StepLump, Narrow.DetailKept(), CrestSum / 4.f, CrestMin, CrestMax, Broad.Kept / (10.0 * FMath::Max(1, Broad.Seeds)));
		}
		GVarietyOff = false;
		GAbsent = -1.f;
		AddInfo(TEXT("Variety: tuning - ") + Text);
	}
	// The throw's volume with the variety on (LM2a's row on this path): a narrow stroke at ThrowShare 0.5 hands the bank and
	// the throw together exactly RidgeReturn x what it lowered.
	{
		FGTMudField Field;
		Field.Init(Bounds, 12.5f);
		Bog(Field);
		double Thrown = 0.0;
		for (int32 I = 0; I < 200; ++I)
		{
			double Out = 0.0;
			Field.StampWheel(FVector2D(I * 5.f, 0.0), FVector2D(I * 5.f + 5.f, 0.0), 28.f, NarrowCm, FVector2D(1.0, 0.0), I * 5.f, 0.5f, Out);
			Thrown += Out;
		}
		const double Expected = Field.RidgeReturn * Field.LoweredCm3;
		const double Error = FMath::Abs(Field.Book.DepositCm3 + Thrown - Expected);
		TestTrue(TEXT("Volume (throw) as LM2a: at ThrowShare 0.5 the deposit and the throw are RidgeReturn x lowered within 0.1 %"), Field.bLumpVariety && Error <= 0.001 * Expected);
		AddInfo(FString::Printf(TEXT("Variety: the narrow stroke at ThrowShare 0.5 with LM2c on - lowered %.0f cm^3, deposit %.0f + thrown %.0f = %.0f against RidgeReturn x lowered %.0f (error %.4f %%)"),
			Field.LoweredCm3, Field.Book.DepositCm3, Thrown, Field.Book.DepositCm3 + Thrown, Expected, 100.0 * Error / FMath::Max(1.0, Expected)));
	}
	return true;
}
/**
 * Living mud LM5b (docs/LIVING_MUD_PLAN.md LM5b "Tests", docs/MUD_VARIANTS.md): a row per variant - the table's profile
 * reaches the patch. First the profiles as GTTerrain gives them (Standard none; Firm, Deep and Stony a rows-scaling
 * profile; Mode Off none, Mode On the section's own). Then a Game world with four Mud sections of 25 m along +X (Firm,
 * Standard, Deep, Stony at L_MudVariants' stations; the spec's default road width, so these boxes are wider than the strip's
 * and overlap: nothing here draws), UGTMudSubsystem::BuildPatches as play builds them, and per patch: the variant,
 * the sinkage cap and rate scales and the friction scale, RecoverShare, LumpShare and ThrowMax (and the field's two), the
 * water table, and that it stays a bog's patch (no profile: the rows and their Mud/Bog tag gate, the bog's cell). Every
 * number the table leaves out is the bog's (AGTMudPatch's defaults). Printed with "Variants: ".
 */
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudVariantsTest, "GrandTour.Mud.Variants",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTMudVariantsTest::RunTest(const FString& Parameters)
{
	struct FRow
	{
		EGTMudVariant Variant;
		const TCHAR* Name;
		float Sink;
		float Recover;
		float Lump;
		float Throw;
		float WaterOffsetCm;
		float Friction;
	};
	const AGTMudPatch* Bog = GetDefault<AGTMudPatch>();
	// The table (docs/LIVING_MUD_PLAN.md LM5b), in the strip's order; a number the table leaves out is the bog's.
	const FRow Rows[4] = {
		{ EGTMudVariant::Firm, TEXT("Firm"), 0.6f, 0.25f, 0.25f, 0.3f, 0.f, 1.1f },
		{ EGTMudVariant::Standard, TEXT("Standard"), 1.f, Bog->RecoverShare, Bog->LumpShare, Bog->ThrowMax, 0.f, 1.f },
		{ EGTMudVariant::Deep, TEXT("Deep"), 1.5f, 0.55f, 0.35f, 0.6f, 10.f, 0.9f },
		{ EGTMudVariant::Stony, TEXT("Stony"), 0.8f, 0.3f, 0.2f, Bog->ThrowMax, 0.f, 1.15f } };
	auto Same = [](float A, float B) { return FMath::Abs(A - B) <= 1.e-6f; };

	FGTTerrainSpec Spec;
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

	// ---- 1. the profiles ---------------------------------------------------------------------------------------------
	for (int32 Index = 0; Index < 4; ++Index)
	{
		const FRow& Row = Rows[Index];
		const FGTRouteSection& Section = Spec.Sections[Index];
		const FGTDeformProfile* P = GTTerrain::DeformProfileFor(Spec, Section);
		const FGTDeformProfile D = FGTDeformProfile::MudVariantDefaults(Row.Variant);
		const bool bDefaults = D.bScalesRows && Same(D.MaxSinkageScale, Row.Sink) && Same(D.SinkageRateScale, Row.Sink) && Same(D.FrictionScale, Row.Friction)
			&& Same(D.RecoverShare, Row.Recover) && Same(D.LumpShare, Row.Lump) && Same(D.ThrowMax, Row.Throw) && Same(D.WaterTableOffsetCm, Row.WaterOffsetCm);
		TestTrue(FString::Printf(TEXT("Variants: %s - MudVariantDefaults is the table's"), Row.Name), bDefaults);
		if (Row.Variant == EGTMudVariant::Standard)
		{
			TestTrue(TEXT("Variants: Standard - no profile (today's path)"), P == nullptr);
		}
		else
		{
			TestTrue(FString::Printf(TEXT("Variants: %s - DeformProfileFor gives the variant's rows-scaling profile"), Row.Name), P != nullptr && P == GTTerrain::MudVariantProfile(Row.Variant) && P->bScalesRows);
		}
	}
	{
		FGTRouteSection Off = Spec.Sections[0];
		Off.Deform.Mode = EGTDeformProfileMode::Off;
		FGTRouteSection On = Spec.Sections[0];
		On.Deform.Mode = EGTDeformProfileMode::On;
		TestTrue(TEXT("Variants: Firm with Deform Mode Off - no profile"), GTTerrain::DeformProfileFor(Spec, Off) == nullptr);
		const FGTDeformProfile* OnProfile = GTTerrain::DeformProfileFor(Spec, On);
		TestTrue(TEXT("Variants: Firm with Deform Mode On - the section's own full profile"), OnProfile == &On.Deform && !OnProfile->bScalesRows);
	}

	// ---- 2. the patches, built as play builds them -------------------------------------------------------------------
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("GTMudVariantsTest"));
	if (!TestNotNull(TEXT("Variants: a Game world"), World))
	{
		return false;
	}
	FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
	Context.SetCurrentWorld(World);
	UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	TestNotNull(TEXT("Variants: the mud subsystem in the Game world"), Mud);
	const int32 Count = Mud ? Mud->BuildPatches(Spec) : 0;
	TestTrue(TEXT("Variants: four patches, one per section"), Count == 4);
	UMaterialParameterCollection* Collection = Mud ? LoadObject<UMaterialParameterCollection>(nullptr, *Mud->CollectionPath) : nullptr;
	UMaterialParameterCollectionInstance* Instance = Collection ? World->GetParameterCollectionInstance(Collection) : nullptr;
	int32 Rowed = 0;
	for (TActorIterator<AGTMudPatch> It(World); It; ++It)
	{
		const AGTMudPatch* Patch = *It;
		if (!Mud || !Spec.Sections.IsValidIndex(Patch->SectionIndex))
		{
			continue;
		}
		++Rowed;
		const FRow& Row = Rows[Patch->SectionIndex];
		const FGTMudField& Field = Patch->GetField();
		const float WaterAsked = Spec.Sections[Patch->SectionIndex].WaterTableCm + Row.WaterOffsetCm;
		const bool bVariant = Patch->MudVariant == Row.Variant;
		const bool bSink = Same(Patch->MaxSinkageScale, Row.Sink) && Same(Patch->SinkageRateScale, Row.Sink);
		const bool bFriction = Same(Patch->FrictionScale, Row.Friction);
		const bool bShares = Same(Patch->RecoverShare, Row.Recover) && Same(Patch->LumpShare, Row.Lump)
			&& Same(Field.RecoverShare, FMath::Clamp(Row.Recover, 0.f, 0.99f)) && Same(Field.LumpShare, FMath::Clamp(Row.Lump, 0.f, 1.f));
		const bool bThrow = Same(Patch->ThrowMax, Row.Throw);
		const bool bWater = Same(Patch->WaterTableCm, WaterAsked);
		// Still a bog's patch: no profile (the rows and the Mud/Bog tag gate), the bog's cell and the bog's other numbers.
		const bool bBog = !Patch->bHasProfile && Same(Patch->ProfileMaxSinkageM, 0.f) && Same(Field.CellCm, Mud->CellCm) && Same(Patch->ReposeDeg, Bog->ReposeDeg)
			&& Same(Patch->SetSeconds, Bog->SetSeconds) && Same(Patch->RidgeWidthCm, Bog->RidgeWidthCm) && Same(Patch->ClodBankPerCm, Bog->ClodBankPerCm);
		float SlotVariant = -1.f;
		const FName SlotName(*FString::Printf(TEXT("PatchVariant%d"), Patch->HoleSlot));
		if (Instance && Collection->GetScalarParameterByName(SlotName))
		{
			Instance->GetScalarParameterValue(SlotName, SlotVariant);
		}
		TestTrue(FString::Printf(TEXT("Variants: %s - the patch carries its variant"), Row.Name), bVariant);
		TestTrue(FString::Printf(TEXT("Variants: %s - sinkage cap and rate x%.2f"), Row.Name, Row.Sink), bSink);
		TestTrue(FString::Printf(TEXT("Variants: %s - friction x%.2f"), Row.Name, Row.Friction), bFriction);
		TestTrue(FString::Printf(TEXT("Variants: %s - RecoverShare %.2f and LumpShare %.2f, in the patch and its field"), Row.Name, Row.Recover, Row.Lump), bShares);
		TestTrue(FString::Printf(TEXT("Variants: %s - ThrowMax %.2f"), Row.Name, Row.Throw), bThrow);
		TestTrue(FString::Printf(TEXT("Variants: %s - water table %.1f cm"), Row.Name, WaterAsked), bWater);
		TestTrue(FString::Printf(TEXT("Variants: %s - still a bog's patch (no profile, the bog's cell and other numbers)"), Row.Name), bBog);
		const FString SlotText = SlotVariant >= 0.f ? FString::Printf(TEXT("%.0f"), SlotVariant) : FString(TEXT("(not in the collection yet)"));
		AddInfo(FString::Printf(TEXT("Variants: %s (section %d, slot %d, box x %.0f..%.0f cm) - variant %d; sinkage cap x%.2f rate x%.2f, friction x%.2f; RecoverShare %.2f (field %.2f), LumpShare %.2f (field %.2f), ThrowMax %.2f; water table %.1f cm; profile %d, cell %.2f cm; MPC PatchVariant%d %s -> %d"),
			Row.Name, Patch->SectionIndex, Patch->HoleSlot, Patch->BoundsMin.X, Patch->BoundsMax.X, static_cast<int32>(Patch->MudVariant), Patch->MaxSinkageScale, Patch->SinkageRateScale, Patch->FrictionScale,
			Patch->RecoverShare, Field.RecoverShare, Patch->LumpShare, Field.LumpShare, Patch->ThrowMax, Patch->WaterTableCm, Patch->bHasProfile ? 1 : 0, Field.CellCm,
			Patch->HoleSlot, *SlotText, bVariant && bSink && bFriction && bShares && bThrow && bWater && bBog ? 1 : 0));
	}
	TestTrue(TEXT("Variants: a row for each of the four patches"), Rowed == 4);
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}
#endif
