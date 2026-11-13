// MudRunner MR3 (docs/MUDRUNNER_LESSONS_PLAN.md MR3 item 1): GrandTour.Mud.MuddyWater, CPU only, on the mud field's turbidity.
// Each row prints a "MuddyWater: " line for Art/mud_shape_test.ps1.
#include "Terrain/GTMudField.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/Crc.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudMuddyWaterTest, "GrandTour.Mud.MuddyWater",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace GTMudMuddyWaterTest
{
	// The Settle test's box and narrow stroke (40 cm asked: a floor about 26-41 cm down), under the bog's -25 cm table: a rut pool
	// along y = 0 holding up to about 15 cm of water, the untouched mud dry.
	const FBox2D Bounds(FVector2D(-200, -350), FVector2D(1200, 350));
	constexpr float TableCm = -25.f;

	void Stroke(FGTMudField& Field, float DepthCm = 40.f)
	{
		for (int32 I = 0; I < 200; ++I)
		{
			Field.StampWheel(FVector2D(I * 5.f, 0), FVector2D(I * 5.f + 5.f, 0), 28.f, DepthCm, FVector2D(1, 0), I * 5.f);
		}
	}

	void Make(FGTMudField& Field, float Table, bool bMuddy = true)
	{
		Field.Init(Bounds, 12.5f);
		Field.LumpShare = 0.f;       // the Settle test's LM0 stroke (its CRC 8e0aad06)
		Field.ClodChance = 0.15f;
		Field.RutWaterTableCm = Table;
		Field.SetMuddyWater(bMuddy);
	}

	/** The field's own state (everything but the turbidity): heights, lumps, slide, tracks, tread, fresh, set timers. */
	uint32 StateCrc(const FGTMudField& Field)
	{
		uint32 Crc = FCrc::MemCrc32(Field.HeightCm.GetData(), Field.HeightCm.Num() * sizeof(float));
		Crc = FCrc::MemCrc32(Field.LumpCm.GetData(), Field.LumpCm.Num() * sizeof(float), Crc);
		Crc = FCrc::MemCrc32(Field.OffsetCm.GetData(), Field.OffsetCm.Num() * sizeof(FVector2f), Crc);
		Crc = FCrc::MemCrc32(Field.Tracks.GetData(), Field.Tracks.Num(), Crc);
		Crc = FCrc::MemCrc32(Field.HeadingTurns.GetData(), Field.HeadingTurns.Num() * sizeof(float), Crc);
		Crc = FCrc::MemCrc32(Field.PhaseTurns.GetData(), Field.PhaseTurns.Num() * sizeof(float), Crc);
		Crc = FCrc::MemCrc32(Field.Fresh.GetData(), Field.Fresh.Num() * sizeof(float), Crc);
		return FCrc::MemCrc32(Field.SetS.GetData(), Field.SetS.Num() * sizeof(float), Crc);
	}

	/** The Settle test's LM0 CRC: heights, slide, tracks, heading, phase. */
	uint32 Lm0Crc(const FGTMudField& Field)
	{
		uint32 Crc = FCrc::MemCrc32(Field.HeightCm.GetData(), Field.HeightCm.Num() * sizeof(float));
		Crc = FCrc::MemCrc32(Field.OffsetCm.GetData(), Field.OffsetCm.Num() * sizeof(FVector2f), Crc);
		Crc = FCrc::MemCrc32(Field.Tracks.GetData(), Field.Tracks.Num(), Crc);
		Crc = FCrc::MemCrc32(Field.HeadingTurns.GetData(), Field.HeadingTurns.Num() * sizeof(float), Crc);
		return FCrc::MemCrc32(Field.PhaseTurns.GetData(), Field.PhaseTurns.Num() * sizeof(float), Crc);
	}

	struct FTally
	{
		int32 Wet = 0;          // water over the cell
		int32 Deep = 0;         // water over TurbidMinWaterCm
		int32 Turbid = 0;       // turbidity over 0
		int32 TurbidDry = 0;    // turbidity over 0 in a dry cell
		float Max = 0.f;
		float Min = 0.f;
		double Sum = 0.0;
	};

	FTally Tally(const FGTMudField& Field)
	{
		FTally Out;
		for (int32 I = 0; I < Field.Turbidity.Num(); ++I)
		{
			const float W = Field.WaterOverCm(I);
			const float T = Field.Turbidity[I];
			Out.Wet += W > 0.f ? 1 : 0;
			Out.Deep += W > Field.TurbidMinWaterCm ? 1 : 0;
			Out.Turbid += T > 0.f ? 1 : 0;
			Out.TurbidDry += (T > 0.f && W <= 0.f) ? 1 : 0;
			Out.Max = FMath::Max(Out.Max, T);
			Out.Min = FMath::Min(Out.Min, T);
			Out.Sum += T;
		}
		return Out;
	}

	int32 CellAt(const FGTMudField& Field, float X, float Y)
	{
		return Field.CellIndexAt(FVector2D(X, Y));
	}
}

bool FGTMudMuddyWaterTest::RunTest(const FString& Parameters)
{
	using namespace GTMudMuddyWaterTest;
	const float Dt = 1.f / 60.f;

	// ---- 1. set only where water stands: a stamp in the rut pool, none on dry mud, none without a table, a throw's landing ----
	{
		FGTMudField Pool;
		Make(Pool, TableCm);
		Stroke(Pool);
		const FTally Stamped = Tally(Pool);
		Pool.SettleTurbidity(Pool.TurbidStepS);   // one sub-step: a cell a later stamp of the stroke lifted out of the water lets go
		const FTally Stepped = Tally(Pool);
		FGTMudField NoTable;
		Make(NoTable, -1.e9f);
		Stroke(NoTable);
		const FTally Dry = Tally(NoTable);
		FGTMudField Shallow;
		Make(Shallow, TableCm);
		Stroke(Shallow, 15.f);   // a 15 cm rut under a -25 cm table: no water
		const FTally ShallowT = Tally(Shallow);
		// A throw's landing: cleared first (the switch off and on), then a blob in the pool and one on the dry mud beside it.
		Pool.SetMuddyWater(false);
		const FTally Cleared = Tally(Pool);
		Pool.SetMuddyWater(true);
		const int32 InPool = CellAt(Pool, 500.f, 0.f);
		const int32 OnMud = CellAt(Pool, 500.f, 250.f);
		const float PoolWater = Pool.WaterOverCm(InPool);
		Pool.DepositLump(FVector2D(500.f, 0.f), 300.0, 6.f);
		Pool.DepositLump(FVector2D(500.f, 250.f), 300.0, 6.f);
		const FTally Thrown = Tally(Pool);
		const bool bSetWet = Stamped.Turbid > 0 && Stamped.Turbid >= Stamped.Deep * 9 / 10 && Stepped.TurbidDry == 0 && Stepped.Turbid <= Stepped.Wet;
		const bool bNoneDry = Dry.Turbid == 0 && NoTable.TurbidTileCount() == 0 && ShallowT.Turbid == 0;
		const bool bThrow = Cleared.Turbid == 0 && Pool.Turbidity[InPool] == 1.f && Pool.Turbidity[OnMud] == 0.f && Thrown.TurbidDry == 0 && Thrown.Turbid > 0;
		TestTrue(TEXT("MuddyWater: a stamp sets turbidity 1 in the rut pool's cells only (none in a dry cell after a sub-step)"), bSetWet);
		TestTrue(TEXT("MuddyWater: no turbidity without water (no table, or a rut above the table)"), bNoneDry);
		TestTrue(TEXT("MuddyWater: a throw's landing sets it in the pool and not on the dry mud beside it"), bThrow);
		AddInfo(FString::Printf(TEXT("MuddyWater: set - the 40 cm stroke under a -25 cm table: %d cells over 1 cm of water, %d turbid at the stamps (%d of them dry once a later stamp lifted them), after one sub-step %d turbid, %d dry -> %d; no table %d turbid, a 15 cm rut %d turbid -> %d; a throw: cleared %d, pool cell (%.1f cm of water) %.2f, dry mud %.2f, %d turbid, %d dry -> %d"),
			Stamped.Deep, Stamped.Turbid, Stamped.TurbidDry, Stepped.Turbid, Stepped.TurbidDry, bSetWet ? 1 : 0, Dry.Turbid, ShallowT.Turbid, bNoneDry ? 1 : 0,
			Cleared.Turbid, PoolWater, Pool.Turbidity[InPool], Pool.Turbidity[OnMud], Thrown.Turbid, Thrown.TurbidDry, bThrow ? 1 : 0));
	}

	// ---- 2. the settle's half-life (RutSettleS 45 s within 10 %), over the whole pool and at its middle cell ----------------
	{
		FGTMudField Pool;
		Make(Pool, TableCm);
		Stroke(Pool);
		Pool.SettleTurbidity(Pool.TurbidStepS);
		const double Sum0 = Tally(Pool).Sum;
		const int32 Mid = CellAt(Pool, 500.f, 0.f);
		const float Mid0 = Pool.Turbidity[Mid];
		float HalfS = -1.f, MidHalfS = -1.f, At90 = 0.f;
		double Sum90 = 0.0;
		for (int32 Frame = 1; Frame <= 90 * 60; ++Frame)
		{
			Pool.SettleTurbidity(Dt);
			const double Sum = Tally(Pool).Sum;
			if (HalfS < 0.f && Sum <= 0.5 * Sum0)
			{
				HalfS = Frame * Dt;
			}
			if (MidHalfS < 0.f && Pool.Turbidity[Mid] <= 0.5f * Mid0)
			{
				MidHalfS = Frame * Dt;
			}
			if (Frame == 90 * 60)
			{
				Sum90 = Sum;
				At90 = Pool.Turbidity[Mid];
			}
		}
		const bool bHalf = FMath::Abs(HalfS - Pool.RutSettleS) <= 0.1f * Pool.RutSettleS && FMath::Abs(MidHalfS - Pool.RutSettleS) <= 0.1f * Pool.RutSettleS;
		TestTrue(TEXT("MuddyWater: the churned pool settles at RutSettleS 45 s (within 10 %)"), bHalf);
		AddInfo(FString::Printf(TEXT("MuddyWater: settle - the pool's sum %.1f halves in %.2f s, its middle cell %.3f in %.2f s (asked %.0f s, 10 %%) -> %d; at 90 s the sum %.3f of the start (asked 0.25), the middle %.3f"),
			Sum0, HalfS, Mid0, MidHalfS, Pool.RutSettleS, bHalf ? 1 : 0, Sum0 > 0.0 ? Sum90 / Sum0 : 0.0, At90));
	}

	// ---- 3. the mixing: bounded (never above 1, never below 0, never into a dry cell, never more in all), across a tile edge ---
	{
		FGTMudField Pool;
		Make(Pool, TableCm);
		Stroke(Pool);
		Pool.SetMuddyWater(false);   // cleared
		Pool.SetMuddyWater(true);
		// One churned cell at the last column of a settle tile, in the rut's middle line, so the mix has to cross the tile's edge.
		// The row (within 3 of the rut's line) where the seed, the cell across the edge and the one two back all hold water, the seed most.
		const int32 Line = CellAt(Pool, 500.f, 0.f) / Pool.SizeX;
		const int32 SeedX = (CellAt(Pool, 500.f, 0.f) % Pool.SizeX) / Pool.SettleTileCells * Pool.SettleTileCells + Pool.SettleTileCells - 1;
		int32 Row = Line;
		float Best = -1.e9f;
		for (int32 R = Line - 3; R <= Line + 3; ++R)
		{
			const int32 I = R * Pool.SizeX + SeedX;
			if (Pool.WaterOverCm(I) > Best && Pool.WaterOverCm(I + 1) > 0.f && Pool.WaterOverCm(I - 1) > 0.f && Pool.WaterOverCm(I - 2) > 0.f)
			{
				Best = Pool.WaterOverCm(I);
				Row = R;
			}
		}
		const int32 Seed = Row * Pool.SizeX + SeedX;
		const float SeedWater = Pool.WaterOverCm(Seed);
		Pool.ChurnWater(Seed, Pool.SurfaceCm(Seed));
		const int32 Across = Seed + 1;   // the first cell of the next tile
		const int32 Two = Seed - 2;      // two cells back in its own tile
		bool bBounded = true;
		double PrevSum = 1.0;
		double WorstGain = 0.0;
		int32 MaxDry = 0;
		float MaxSeen = 0.f;
		for (int32 Frame = 1; Frame <= 20 * 60; ++Frame)
		{
			Pool.SettleTurbidity(Dt);
			const FTally Now = Tally(Pool);
			MaxSeen = FMath::Max(MaxSeen, Now.Max);
			MaxDry = FMath::Max(MaxDry, Now.TurbidDry);
			WorstGain = FMath::Max(WorstGain, Now.Sum - PrevSum);
			bBounded &= Now.Max <= 1.f && Now.Min >= 0.f && Now.TurbidDry == 0 && Now.Sum <= PrevSum + 1.e-5;
			PrevSum = Now.Sum;
		}
		const float Expect = FMath::Pow(0.5f, 20.f / Pool.RutSettleS);
		const bool bSpread = Pool.Turbidity[Across] > 0.f && Pool.Turbidity[Two] > 0.f && Pool.Turbidity[Seed] < 0.5f;
		const bool bConserved = FMath::Abs(PrevSum - Expect) <= 0.02 * Expect;
		TestTrue(TEXT("MuddyWater: the mix stays bounded (0..1, never into a dry cell, the sum never grows)"), bBounded);
		TestTrue(TEXT("MuddyWater: the mix spreads into wet neighbours, across a tile's edge, and the sum only settles"), bSpread && bConserved);
		AddInfo(FString::Printf(TEXT("MuddyWater: mix - one churned cell (%.1f cm of water) at a tile's edge, 20 s: max seen %.3f, the dry cells' most %d, the sum's worst rise %.2e -> %d; the seed %.3f, across the edge %.3f, two back %.3f, the sum %.4f (the settle alone %.4f) -> %d; %d turbid tiles"),
			SeedWater, MaxSeen, MaxDry, WorstGain, bBounded ? 1 : 0, Pool.Turbidity[Seed], Pool.Turbidity[Across], Pool.Turbidity[Two], PrevSum, Expect, (bSpread && bConserved) ? 1 : 0, Pool.TurbidTileCount()));
	}

	// ---- 4. the switch's 0 identity: the field's own state as with it on (the LM0 CRC under water), no turbidity, A all 0 --------
	{
		FGTMudField On, Off;
		Make(On, TableCm, true);
		Make(Off, TableCm, false);
		Stroke(On);
		Stroke(Off);
		const uint32 OnCrc0 = Lm0Crc(On);
		const uint32 OffCrc0 = Lm0Crc(Off);
		const FTally OnT = Tally(On);
		bool bSameAwake = true;
		for (int32 Frame = 0; Frame < 30 * 60; ++Frame)
		{
			On.Settle(Dt);
			On.SettleTurbidity(Dt);
			Off.Settle(Dt);
			Off.SettleTurbidity(Dt);
			bSameAwake &= On.AwakeTileCount() == Off.AwakeTileCount();
		}
		const uint32 OnCrc = StateCrc(On);
		const uint32 OffCrc = StateCrc(Off);
		const FTally OffT = Tally(Off);
		// The tread texels: Off's A is 0 everywhere and its R, G, B are On's.
		const int32 N = On.SizeX * On.SizeY;
		TArray<FFloat16Color> FieldOn, FieldOff, TreadOn, TreadOff;
		FieldOn.SetNumZeroed(N);
		FieldOff.SetNumZeroed(N);
		TreadOn.SetNumZeroed(N);
		TreadOff.SetNumZeroed(N);
		On.EncodeTexels(0, N, FieldOn.GetData(), TreadOn.GetData(), true);
		Off.EncodeTexels(0, N, FieldOff.GetData(), TreadOff.GetData(), true);
		int32 OffA = 0, RgbDiffer = 0, OnA = 0;
		for (int32 I = 0; I < N; ++I)
		{
			OffA += TreadOff[I].A.GetFloat() != 0.f ? 1 : 0;
			OnA += TreadOn[I].A.GetFloat() != 0.f ? 1 : 0;
			RgbDiffer += (TreadOn[I].R.GetFloat() != TreadOff[I].R.GetFloat() || TreadOn[I].G.GetFloat() != TreadOff[I].G.GetFloat() || TreadOn[I].B.GetFloat() != TreadOff[I].B.GetFloat()
				|| FMemory::Memcmp(&FieldOn[I], &FieldOff[I], sizeof(FFloat16Color)) != 0) ? 1 : 0;
		}
		const bool bCrc = OnCrc0 == 0x8e0aad06u && OffCrc0 == 0x8e0aad06u;
		const bool bIdentity = OnCrc == OffCrc && bSameAwake && OffT.Turbid == 0 && Off.TurbidTileCount() == 0 && OffA == 0 && RgbDiffer == 0 && OnT.Turbid > 0;
		TestTrue(TEXT("MuddyWater: under water, with the switch on, the stroke is still LM0's field (CRC 8e0aad06)"), bCrc);
		TestTrue(TEXT("MuddyWater: gt.Mud.MuddyWater 0 - the field settles exactly as with it on, no turbidity, the tread's A all 0"), bIdentity);
		AddInfo(FString::Printf(TEXT("MuddyWater: switch - the LM0 CRC under a -25 cm table, on %08x, off %08x -> %d; after 30 s of settle the state CRC on %08x, off %08x, awake tiles the same every frame %d, off turbid %d (on %d at the stroke), off's A non-zero %d (on %d), texels otherwise differing %d -> %d"),
			OnCrc0, OffCrc0, bCrc ? 1 : 0, OnCrc, OffCrc, bSameAwake ? 1 : 0, OffT.Turbid, OnT.Turbid, OffA, OnA, RgbDiffer, bIdentity ? 1 : 0));
	}

	// ---- 5. the tiles sleep once settled (under TurbidSleepBelow everywhere), the remainder to 0 --------------------------------
	{
		FGTMudField Pool;
		Make(Pool, TableCm);
		Stroke(Pool);
		const int32 Tiles0 = Pool.TurbidTileCount();
		float SleptS = -1.f;
		int32 Most = Tiles0;
		for (int32 Frame = 1; Frame <= 400 * 60 && SleptS < 0.f; ++Frame)
		{
			Pool.SettleTurbidity(Dt);
			Most = FMath::Max(Most, Pool.TurbidTileCount());
			if (Pool.TurbidTileCount() == 0)
			{
				SleptS = Frame * Dt;
			}
		}
		const FTally After = Tally(Pool);
		// Asked: 1 to TurbidSleepBelow at the half-life, log2(1 / 0.02) x 45 = 254 s, within 10 %.
		const float Asked = FMath::Log2(1.f / Pool.TurbidSleepBelow) * Pool.RutSettleS;
		const bool bSlept = SleptS > 0.f && FMath::Abs(SleptS - Asked) <= 0.1f * Asked && After.Turbid == 0;
		TestTrue(TEXT("MuddyWater: the turbid tiles sleep once settled under 0.02, and hold none after"), bSlept);
		AddInfo(FString::Printf(TEXT("MuddyWater: sleep - %d turbid tiles at the stroke (at most %d), all asleep at %.1f s (asked %.1f s, 10 %%), %d cells turbid after -> %d"),
			Tiles0, Most, SleptS, Asked, After.Turbid, bSlept ? 1 : 0));
	}
	return true;
}
#endif
