#include "Terrain/GTMudField.h"
#include "Async/ParallelFor.h"
#include "HAL/IConsoleManager.h"

// LM4f item 3 (docs/LIVING_MUD_PLAN.md LM4f): the snow's fast settle. Here, not in the patch, so a field the CPU tests build takes
// it as its default too (AGTMudPatch pushes it every tick).
static TAutoConsoleVariable<int32> CVarSnowFastSettle(
	TEXT("gt.Snow.FastSettle"), 1,
	TEXT("LM4f: 1 a snow patch's settle runs the talus at 15 Hz, keeps awake only the tiles within 2 m of a write in the last 3 s (or by a pending collapse) and sweeps the tiles in parallel (summed in the serial order); 2 the parallel sweep alone (exact, a check); 3 parallel + 15 Hz (no band); 4 parallel + the band (30 Hz); 0 as LM4e."),
	ECVF_Default);

int32 FGTMudField::DefaultSnowFastSettle()
{
	return CVarSnowFastSettle.GetValueOnAnyThread();
}

namespace
{
	template <typename F>
	auto BilinearSample(const FVector2D& LocalCm, float CellCm, int32 SizeX, int32 SizeY, F&& Get) -> decltype(Get(0))
	{
		const float GX = LocalCm.X / CellCm - 0.5f;   // cell centres carry the values
		const float GY = LocalCm.Y / CellCm - 0.5f;
		const int32 X0 = FMath::Clamp(FMath::FloorToInt(GX), 0, SizeX - 1);
		const int32 Y0 = FMath::Clamp(FMath::FloorToInt(GY), 0, SizeY - 1);
		const int32 X1 = FMath::Min(X0 + 1, SizeX - 1);
		const int32 Y1 = FMath::Min(Y0 + 1, SizeY - 1);
		const float FX = FMath::Clamp(GX - X0, 0.f, 1.f);
		const float FY = FMath::Clamp(GY - Y0, 0.f, 1.f);
		return FMath::Lerp(FMath::Lerp(Get(Y0 * SizeX + X0), Get(Y0 * SizeX + X1), FX), FMath::Lerp(Get(Y1 * SizeX + X0), Get(Y1 * SizeX + X1), FX), FY);
	}

	/** 0..1, whatever the sign: FMath::Frac keeps a negative number negative. */
	float Wrap01(float Value)
	{
		return Value - FMath::FloorToFloat(Value);
	}

	/** Stage H: one lattice point's value, -1..1, from an integer hash of its coordinates and the field's seed. */
	float HashLattice(int32 X, int32 Y, int32 Seed)
	{
		uint32 H = static_cast<uint32>(X) * 374761393u + static_cast<uint32>(Y) * 668265263u + static_cast<uint32>(Seed) * 2246822519u;
		H = (H ^ (H >> 13)) * 1274126177u;
		H ^= H >> 16;
		return (H & 0xFFFFFFu) / static_cast<float>(0xFFFFFF) * 2.f - 1.f;
	}

	/** LM4 item 6: smoothed value noise at a continuous lattice coordinate, -1..1 (HashLattice at the corners, smoothstep between). */
	float LatticeValueNoise(double GX, double GY, int32 Seed)
	{
		const int32 X0 = FMath::FloorToInt(static_cast<float>(GX));
		const int32 Y0 = FMath::FloorToInt(static_cast<float>(GY));
		const float TX = static_cast<float>(GX - X0);
		const float TY = static_cast<float>(GY - Y0);
		const float FX = TX * TX * (3.f - 2.f * TX);
		const float FY = TY * TY * (3.f - 2.f * TY);
		return FMath::Lerp(FMath::Lerp(HashLattice(X0, Y0, Seed), HashLattice(X0 + 1, Y0, Seed), FX),
			FMath::Lerp(HashLattice(X0, Y0 + 1, Seed), HashLattice(X0 + 1, Y0 + 1, Seed), FX), FY);
	}
}

void FGTMudField::Init(const FBox2D& BoundsCm, float InCellCm)
{
	CellCm = FMath::Max(1.f, InCellCm);
	OriginCm = BoundsCm.Min;
	SizeX = FMath::Clamp(FMath::CeilToInt(BoundsCm.GetSize().X / CellCm), 1, 4096);
	SizeY = FMath::Clamp(FMath::CeilToInt(BoundsCm.GetSize().Y / CellCm), 1, 4096);
	HeightCm.Init(0.f, SizeX * SizeY);
	OffsetCm.Init(FVector2f::ZeroVector, SizeX * SizeY);
	Tracks.Init(0, SizeX * SizeY);
	HeadingTurns.Init(0.f, SizeX * SizeY);
	PhaseTurns.Init(-1.f, SizeX * SizeY);   // -1: no wheel has been here, so there is no tread to draw
	LoweredCm3 = 0.0;
	bDirty = false;
	// LM1: the living field's state. Nothing is fresh, nothing is setting and every tile sleeps until a stamp wakes it.
	Fresh.Init(0.f, SizeX * SizeY);
	SetS.Init(0.f, SizeX * SizeY);
	SettleDelta.Init(0.f, SizeX * SizeY);
	TileCells = FMath::Max(1, SettleTileCells);
	TilesX = (SizeX + TileCells - 1) / TileCells;
	TilesY = (SizeY + TileCells - 1) / TileCells;
	TileAwake.Init(0, TilesX * TilesY);
	TileQuietS.Init(0.f, TilesX * TilesY);
	TileStill.Init(0, TilesX * TilesY);
	SettleSweeps.Init(0, TilesX * TilesY);
	SettleInList.Init(0, TilesX * TilesY);
	SettleList.Reset();
	TileDirtyRect.Init(FIntRect(), TilesX * TilesY);   // LM4e cut 2
	DirtyTiles.Reset();
	// LM4f item 3: no tile has been written (the band-only wake); LM4f item 4's noise slots stay if the size is the same (their key).
	TileWriteS.Init(-1.e30, TilesX * TilesY);
	TilePending.Init(0, TilesX * TilesY);
	SettleAccumS = 0.0;
	// MudRunner MR3: no churned water yet (none on snow: its field is not measured from the ground the table is).
	Turbidity.Init(0.f, bSnow ? 0 : SizeX * SizeY);
	TileTurbid.Init(0, bSnow ? 0 : TilesX * TilesY);
	TurbidScratch.Reset();
	TurbidAccumS = 0.0;
	RelaxAskedUpCm3 = 0.0;
	RelaxAskedDownCm3 = 0.0;
	RelaxMovedCm3 = 0.0;
	// LM2a: no lumps yet; the static weights are rebuilt on first use (their numbers are pushed in after Init).
	LumpCm.Init(0.f, SizeX * SizeY);
	SettleOut.Init(0.f, SizeX * SizeY);
	Book = FLumpBook();
	LumpKeyCells = -1;
	PendingClods.Reset();
	ClockS = 0.0;
	ClodRolls = 0;
	// LM2c: the stamp counter the bank clods hash, and the readouts.
	StampSteps = 0;
	ClodBankExpectPerRate = 0.0;
	// LM3a: a snow field keeps the depths baked into it over a reset of the same size (AGTMudPatch::ResetFieldForTest), and
	// its top is rebuilt from them; a new one starts uniform at SnowDepthCm (the patch bakes the section's drifts after).
	PloughedCm3 = 0.0;
	PloughBermCm3 = 0.0;
	PloughLostCm3 = 0.0;
	SnowBankLostCm3 = 0.0;
	RefilledCm3 = 0.0;
	RefillTrackCarry = 0.f;
	PloughLumpCm3 = 0.0;
	// LM4: the wall drops' readouts and the floor chunks' segment keys start afresh with the field.
	WallDrops = 0;
	WallDropCm3 = 0.0;
	FloorChunksQueued = 0;
	LipChunksQueued = 0;
	FloorChunkKeys.Reset();
	// LM4c: the settle clock, the collapse segments and their readouts start afresh; the static per-cell arrays are rebuilt on
	// first use if the field's place, size or numbers changed (EnsureSnowPiles' key).
	SettleClockS = 0.0;
	CollapseSegs.Reset();
	CollapseIndex.Reset();
	CollapsesFired = 0;
	CollapseCm3 = 0.0;
	CollapseSegsArmed = 0;
	CollapseClumpsQueued = 0;
	CollapseLog.Reset();
	// LM4d: the channel's readouts and the spill's sites.
	SmearCm3 = 0.0;
	SmearCells = 0;
	SpillCm3 = 0.0;
	SpillLumpCm3 = 0.0;
	SpillClumpsQueued = 0;
	SpillSites.Reset();
	if (bSnow)
	{
		if (SnowDepthCell.Num() != SizeX * SizeY)
		{
			SnowDepthCell.Init(FMath::Max(0.f, SnowDepthCm), SizeX * SizeY);
		}
		SnowTopCm.SetNumUninitialized(SizeX * SizeY);
		for (int32 Index = 0; Index < SnowTopCm.Num(); ++Index)
		{
			// LM4 item 6: the undulation joins the depth before the taper (SnowTopAt's rule, at the cell's centre).
			const FVector2D Centre = CellCentreCm(Index);
			SnowTopCm[Index] = FMath::Max(0.f, SnowDepthCell[Index] + SnowTopNoiseCm(Centre)) * SnowTaperAt(Centre);
		}
		// LM3c: the tread's tick, the belly's marks and the broken lugs (snow only; mud keeps none of them).
		TreadTickOf.Init(0u, SizeX * SizeY);
		TreadTick = 1;
		SnowMark.Init(0, SizeX * SizeY);
		LipDropShare.Init(0, SizeX * SizeY);   // LM4b: the feathered notches
		BuildLugStrength();
	}
	else
	{
		SnowDepthCell.Reset();
		SnowTopCm.Reset();
		TreadTickOf.Reset();
		SnowMark.Reset();
		LipDropShare.Reset();
		LugStrength.Reset();
	}
}

float FGTMudField::SnowTaperAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return 0.f;
	}
	const FBox2D Box = Bounds();
	const float In = static_cast<float>(FMath::Min(FMath::Min(XYCm.X - Box.Min.X, Box.Max.X - XYCm.X), FMath::Min(XYCm.Y - Box.Min.Y, Box.Max.Y - XYCm.Y)));
	if (In <= 0.f)
	{
		return 0.f;
	}
	return FMath::SmoothStep(0.f, FMath::Max(1.f, SnowEdgeCm), In);
}

float FGTMudField::SnowTopAt(const FVector2D& XYCm) const
{
	if (!bSnow || !IsValid() || SnowDepthCell.Num() != SizeX * SizeY)
	{
		return 0.f;
	}
	const float Depth = BilinearSample(XYCm - OriginCm, CellCm, SizeX, SizeY, [this](int32 Index) { return SnowDepthCell[Index]; });
	// LM4 item 6: the one snow top - the depth with the static undulation, tapered (the mesh's rest, the stamps' cut through
	// SnowTopCm and the traction's GroundRelativeAt all read this).
	return FMath::Max(0.f, Depth + SnowTopNoiseCm(XYCm)) * SnowTaperAt(XYCm);
}

float FGTMudField::SnowTopNoiseCm(const FVector2D& XYCm) const
{
	if (!bSnow || SnowTopUndulationCm <= 0.f)
	{
		return 0.f;
	}
	// LM4 item 6: three octaves of value noise in world cm, the wavelengths geometric from SnowTopWaveMaxCm down to
	// SnowTopWaveMinCm, weights 1 / 0.6 / 0.35, each octave rotated (no axis-aligned rows) and seeded on its own. A single
	// smoothstep octave of a -1..1 lattice and the three weighted together measured an sd of 0.30 (the first LM4 test read
	// 1.75 cm over a 20 m line at 3 with 0.52 assumed), so the sum over 0.30 gives SnowTopUndulationCm of sd.
	const float WaveMax = FMath::Max(10.f, SnowTopWaveMaxCm);
	const float WaveMin = FMath::Clamp(SnowTopWaveMinCm, 5.f, WaveMax);
	static const float Weights[3] = { 1.f, 0.6f, 0.35f };
	static const float Angles[3] = { 0.31f, 1.43f, 2.57f };
	float Sum = 0.f;
	for (int32 Octave = 0; Octave < 3; ++Octave)
	{
		const float Wave = WaveMax * FMath::Pow(WaveMin / WaveMax, Octave / 2.f);
		const float C = FMath::Cos(Angles[Octave]);
		const float S = FMath::Sin(Angles[Octave]);
		const double U = (XYCm.X * C - XYCm.Y * S) / Wave;
		const double V = (XYCm.X * S + XYCm.Y * C) / Wave;
		Sum += Weights[Octave] * LatticeValueNoise(U, V, NoiseSeed + 301 + 7 * Octave);
	}
	return SnowTopUndulationCm * Sum / 0.30f;
}

void FGTMudField::EnsureSnowPiles()
{
	const bool bRepose = CellReposeOn();
	const bool bPiles = PilesOn();
	if (!IsValid() || (!bRepose && !bPiles))
	{
		if (WallTalusCm.Num() > 0 || PileFactor.Num() > 0)
		{
			WallTalusCm.Reset();
			PileFactor.Reset();
		}
		bPileKeySet = false;
		return;
	}
	// LM4c: the arrays are static (functions of the cell's world place, the numbers and the seed), built once for the
	// numbers in force; the key is every input, so a reset of the same field keeps them.
	const double Key[PileKeyCount] = { bRepose ? 1.0 : 0.0, bPiles ? 1.0 : 0.0, LooseReposeDeg, WallReposeDeg, WallReposeRangeDeg, WallReposeWaveMinCm,
		WallReposeWaveMaxCm, PileClusterMin, PileClusterMax, PileWaveMinCm, PileWaveMaxCm, CellCm, OriginCm.X, OriginCm.Y, static_cast<double>(SizeX),
		static_cast<double>(SizeY), static_cast<double>(NoiseSeed), PileContrast };
	if (bPileKeySet && FMemory::Memcmp(Key, PileKeyVals, sizeof(Key)) == 0)
	{
		return;
	}
	FMemory::Memcpy(PileKeyVals, Key, sizeof(Key));
	bPileKeySet = true;
	const int32 Count = SizeX * SizeY;
	// Two octaves of value noise in world cm, each rotated (no axis-aligned rows of lattice points along a trench) and seeded
	// on its own, then ranked over the field into 0..1 evenly (a 4096-bin histogram, linear within a bin: O(cells), no sort),
	// so the range named is the range used, evenly (a raw value noise bunches about its middle).
	auto Ranked = [this, Count](float WaveA, float WaveB, float AngleA, float AngleB, int32 Salt, TArray<float>& Out)
	{
		Out.SetNumUninitialized(Count);
		const float CA = FMath::Cos(AngleA), SA = FMath::Sin(AngleA), CB = FMath::Cos(AngleB), SB = FMath::Sin(AngleB);
		const double WA = FMath::Max(1.f, WaveA), WB = FMath::Max(1.f, WaveB);
		for (int32 Index = 0; Index < Count; ++Index)
		{
			const FVector2D P = CellCentreCm(Index);
			const float NA = LatticeValueNoise((P.X * CA - P.Y * SA) / WA, (P.X * SA + P.Y * CA) / WA, NoiseSeed + Salt);
			const float NB = LatticeValueNoise((P.X * CB - P.Y * SB) / WB + 0.37, (P.X * SB + P.Y * CB) / WB + 0.61, NoiseSeed + Salt + 1);
			Out[Index] = 0.5f * (NA + NB);
		}
		constexpr int32 Bins = 4096;
		TArray<int32> Histogram;
		Histogram.Init(0, Bins);
		auto BinOf = [Bins](float V) { return FMath::Clamp(static_cast<int32>((V * 0.5f + 0.5f) * Bins), 0, Bins - 1); };
		for (const float V : Out)
		{
			++Histogram[BinOf(V)];
		}
		TArray<double> Below;   // the share of cells under each bin's floor
		Below.SetNumUninitialized(Bins + 1);
		Below[0] = 0.0;
		for (int32 Bin = 0; Bin < Bins; ++Bin)
		{
			Below[Bin + 1] = Below[Bin] + static_cast<double>(Histogram[Bin]) / FMath::Max(1, Count);
		}
		for (float& V : Out)
		{
			const float Pos = (V * 0.5f + 0.5f) * Bins;
			const int32 Bin = BinOf(V);
			const float Within = FMath::Clamp(Pos - Bin, 0.f, 1.f);
			V = static_cast<float>(FMath::Lerp(Below[Bin], Below[Bin + 1], static_cast<double>(Within)));
		}
	};
	if (bRepose)
	{
		Ranked(WallReposeWaveMinCm, WallReposeWaveMaxCm, 0.79f, 2.21f, 421, WallTalusCm);
		WallTalusMinCm = TNumericLimits<float>::Max();
		for (float& Talus : WallTalusCm)
		{
			const float Deg = FMath::Clamp(WallReposeDeg + WallReposeRangeDeg * (2.f * Talus - 1.f), 1.f, 89.f);
			Talus = FMath::Tan(FMath::DegreesToRadians(Deg)) * CellCm;
			WallTalusMinCm = FMath::Min(WallTalusMinCm, Talus);   // LM4e cut 3: the sweep's early out
		}
	}
	else
	{
		WallTalusCm.Reset();
	}
	if (bPiles)
	{
		Ranked(PileWaveMinCm, PileWaveMaxCm, 0.53f, 1.97f, 431, PileFactor);
		const float Lo = FMath::Max(0.f, PileClusterMin);
		const float Hi = FMath::Max(Lo, PileClusterMax);
		const float Contrast = FMath::Clamp(PileContrast, 0.f, 1.f);
		for (float& Factor : PileFactor)
		{
			const float U = Factor;
			Factor = Lo + (Hi - Lo) * FMath::Lerp(U, U * U * (3.f - 2.f * U), Contrast);
		}
	}
	else
	{
		PileFactor.Reset();
	}
}

float FGTMudField::PileFactorAt(const FVector2D& XYCm)
{
	if (!PilesOn())
	{
		return 1.f;
	}
	EnsureSnowPiles();
	const int32 Index = CellIndexAt(XYCm);
	return PileFactor.IsValidIndex(Index) ? PileFactor[Index] : 1.f;
}

float FGTMudField::WallReposeAt(int32 Index)
{
	EnsureSnowPiles();
	if (!CellReposeOn() || !WallTalusCm.IsValidIndex(Index))
	{
		return ReposeDeg;
	}
	return FMath::RadiansToDegrees(FMath::Atan(WallTalusCm[Index] / CellCm));
}

bool FGTMudField::CollapseSegmentAt(const FVector2D& FootCm, const FVector2D& LineDir, float Side, uint64& OutKey, double& OutAlong0, double& OutAlong1) const
{
	// LM4c item 2: LM4's segment scheme (WallOffsetAt) at CollapseSegMinCm..CollapseSegMaxCm: boundaries every mean length along
	// the world axis nearer the stroke, each jittered by a quarter of the range (so a segment is min..max long), and a hash of
	// the segment, the wall's side and its 60 cm lane across decides whether it collapses.
	const bool bAlongX = FMath::Abs(LineDir.X) >= FMath::Abs(LineDir.Y);
	const double Along = bAlongX ? FootCm.X : FootCm.Y;
	const double Across = bAlongX ? FootCm.Y : FootCm.X;
	const float SegMin = FMath::Max(1.f, CollapseSegMinCm);
	const float SegMax = FMath::Max(SegMin, CollapseSegMaxCm);
	const float Mean = 0.5f * (SegMin + SegMax);
	const float Jitter = 0.25f * (SegMax - SegMin);
	const int32 Axis = bAlongX ? 0 : 1;
	auto Boundary = [&](int32 K) { return static_cast<double>(K) * Mean + Jitter * HashLattice(K, 2000 + Axis, NoiseSeed + 401); };
	int32 K = FMath::FloorToInt(static_cast<float>(Along / Mean));
	if (Along < Boundary(K))
	{
		--K;
	}
	else if (Along >= Boundary(K + 1))
	{
		++K;
	}
	const int32 Lane = FMath::FloorToInt(static_cast<float>(Across / 60.0));
	const int32 Salt = ((Lane * 2 + (Side > 0.f ? 1 : 0)) * 2) + Axis;
	OutKey = (static_cast<uint64>(static_cast<uint32>(K)) << 32) | static_cast<uint64>(static_cast<uint32>(Salt));
	OutAlong0 = Boundary(K);
	OutAlong1 = Boundary(K + 1);
	return 0.5f * (HashLattice(K, Salt, NoiseSeed + 409) + 1.f) < FMath::Clamp(CollapseChance, 0.f, 1.f);
}

void FGTMudField::ArmCollapse(const FVector2D& FootCm, const FVector2D& LineDir, float Side, float FaceCm, float FloorCm)
{
	uint64 Key = 0;
	double Along0 = 0.0, Along1 = 0.0;
	if (!CollapseSegmentAt(FootCm, LineDir, Side, Key, Along0, Along1))
	{
		return;
	}
	FCollapseSeg* Seg = nullptr;
	if (const int32* Found = CollapseIndex.Find(Key))
	{
		Seg = &CollapseSegs[*Found];
	}
	else
	{
		const int32 Added = CollapseSegs.AddDefaulted();
		CollapseIndex.Add(Key, Added);
		Seg = &CollapseSegs[Added];
		Seg->Key = Key;
		const int32 KA = static_cast<int32>(Key >> 32);
		const int32 KB = static_cast<int32>(Key & 0xFFFFFFFFu);
		Seg->DelayS = FMath::Lerp(CollapseDelayMinS, FMath::Max(CollapseDelayMinS, CollapseDelayMaxS), 0.5f * (HashLattice(KA, KB, NoiseSeed + 411) + 1.f));
		Seg->TopShare = FMath::Lerp(CollapseTopMin, FMath::Max(CollapseTopMin, CollapseTopMax), 0.5f * (HashLattice(KA, KB, NoiseSeed + 413) + 1.f));
		++CollapseSegsArmed;
	}
	// The last stamp that cut the wall sets the geometry and starts the timer again: the collapse comes after the last tyre.
	Seg->Side = static_cast<int8>(Side > 0.f ? 1 : -1);
	Seg->bAlongX = FMath::Abs(LineDir.X) >= FMath::Abs(LineDir.Y);
	Seg->Along0 = Along0;
	Seg->Along1 = Along1;
	Seg->LinePoint = FootCm;
	Seg->LineDir = LineDir;
	Seg->FaceCm = FaceCm;
	Seg->FloorCm = FloorCm;
	Seg->ArmS = SettleClockS;
	Seg->bPending = true;
}

int32 FGTMudField::FireCollapses()
{
	int32 Fell = 0;
	for (FCollapseSeg& Seg : CollapseSegs)
	{
		if (Seg.bPending && SettleClockS + 1.e-9 >= Seg.ArmS + Seg.DelayS)
		{
			Seg.bPending = false;
			if (Collapse(Seg))
			{
				++Seg.Fired;
				++Fell;
			}
		}
	}
	return Fell;
}

bool FGTMudField::Collapse(FCollapseSeg& Seg)
{
	if (!IsValid() || !bSnow)
	{
		return false;
	}
	const float C = CellCm;
	FVector2D Dir = Seg.LineDir.GetSafeNormal();
	if (Dir.IsNearlyZero())
	{
		Dir = Seg.bAlongX ? FVector2D(1.0, 0.0) : FVector2D(0.0, 1.0);
	}
	// Out of the trench on the segment's side: square to the line, toward Side on the axis across.
	FVector2D N(-Dir.Y, Dir.X);
	if ((Seg.bAlongX ? N.Y : N.X) * Seg.Side < 0.0)
	{
		N = -N;
	}
	const double DirAxis = Seg.bAlongX ? Dir.X : Dir.Y;
	if (FMath::Abs(DirAxis) < 1.e-3)
	{
		return false;
	}
	const float Face = FMath::Max(C, Seg.FaceCm);
	const float Feather = FMath::Max(0.f, CollapseFeatherCells) * C;
	const float HalfFeather = 0.5f * Feather;
	const float TopReach = RutShoulderCm + 30.f;    // the wall's top is looked for this far out from its foot (the lip and the berm's inner face)
	const float BackMax = RutShoulderCm + 60.f;     // and the plane can reach back this far
	const float TanLoose = FMath::Tan(FMath::DegreesToRadians(FMath::Clamp(LooseReposeDeg, 1.f, 89.f)));
	const double Mid = 0.5 * (Seg.Along0 + Seg.Along1);
	const float SegCm = static_cast<float>(Seg.Along1 - Seg.Along0);
	// The pile: a cone on the trench floor at the wall's foot - centred a cell in from the foot, mid-segment, over the segment's
	// length and the feather along the trench and the trench's whole width across (to the far wall's foot), only on the floor.
	const float PileA = 0.5f * SegCm + Feather;
	const float PileB = 2.f * Face;
	const float PileL = Face - C;
	const double R0 = FMath::Min(Seg.Along0 - HalfFeather, Mid - PileA);
	const double R1 = FMath::Max(Seg.Along1 + HalfFeather, Mid + PileA);
	// The cells' box from the region's corners (world): along the axis R0..R1, across from the far foot to Face + BackMax.
	FVector2D Lo(TNumericLimits<double>::Max(), TNumericLimits<double>::Max());
	FVector2D Hi(-TNumericLimits<double>::Max(), -TNumericLimits<double>::Max());
	const double LineAxis = Seg.bAlongX ? Seg.LinePoint.X : Seg.LinePoint.Y;
	for (const double AxisAt : { R0, R1 })
	{
		const double T = (AxisAt - LineAxis) / DirAxis;
		for (const float Lat : { -Face - C, Face + BackMax })
		{
			const FVector2D P = Seg.LinePoint + Dir * T + N * Lat;
			Lo = FVector2D::Min(Lo, P);
			Hi = FVector2D::Max(Hi, P);
		}
	}
	const int32 X0 = FMath::Clamp(FMath::FloorToInt(static_cast<float>((Lo.X - OriginCm.X) / C)) - 1, 0, SizeX - 1);
	const int32 Y0 = FMath::Clamp(FMath::FloorToInt(static_cast<float>((Lo.Y - OriginCm.Y) / C)) - 1, 0, SizeY - 1);
	const int32 X1 = FMath::Clamp(FMath::CeilToInt(static_cast<float>((Hi.X - OriginCm.X) / C)) + 1, 0, SizeX - 1);
	const int32 Y1 = FMath::Clamp(FMath::CeilToInt(static_cast<float>((Hi.Y - OriginCm.Y) / C)) + 1, 0, SizeY - 1);
	// Station by station (the cell rows square to the axis): the floor beside the foot, the wall's top, the cut level, and what
	// comes off above the plane; then the pile's kernel over the floor cells.
	const int32 S0 = Seg.bAlongX ? X0 : Y0;
	const int32 S1 = Seg.bAlongX ? X1 : Y1;
	const int32 Q0 = Seg.bAlongX ? Y0 : X0;
	const int32 Q1 = Seg.bAlongX ? Y1 : X1;
	auto Ramp = [](float T) { T = FMath::Clamp(T, 0.f, 1.f); return T * T * (3.f - 2.f * T); };
	TArray<TPair<int32, float>, TInlineAllocator<256>> Removes;
	TArray<TPair<int32, float>, TInlineAllocator<256>> Kernel;
	double Volume = 0.0;
	double KernelSum = 0.0;
	const double CellArea = static_cast<double>(C) * C;
	for (int32 S = S0; S <= S1; ++S)
	{
		const double Along = (Seg.bAlongX ? OriginCm.X : OriginCm.Y) + (S + 0.5) * C;
		const bool bNotch = Along >= Seg.Along0 - HalfFeather && Along <= Seg.Along1 + HalfFeather;
		const bool bPile = FMath::Abs(Along - Mid) <= PileA;
		if (!bNotch && !bPile)
		{
			continue;
		}
		float Floor = TNumericLimits<float>::Max();
		float Top = -TNumericLimits<float>::Max();
		for (int32 Q = Q0; Q <= Q1; ++Q)
		{
			const int32 Index = Seg.bAlongX ? (Q * SizeX + S) : (S * SizeX + Q);
			const float Lat = static_cast<float>(FVector2D::DotProduct(CellCentreCm(Index) - Seg.LinePoint, N));
			const float Surface = SurfaceCm(Index);
			if (Lat >= Face - 2.f * C && Lat <= Face + 0.5f * C)
			{
				Floor = FMath::Min(Floor, Surface);
			}
			if (Lat >= Face && Lat <= Face + TopReach)
			{
				Top = FMath::Max(Top, Surface);
			}
			if (bPile && Lat >= -Face && Lat <= Face + 0.5f * C)
			{
				const float DA = static_cast<float>(Along - Mid) / PileA;
				const float DL = (Lat - PileL) / PileB;
				const float K = 1.f - FMath::Sqrt(DA * DA + DL * DL);
				if (K > 0.f)
				{
					Kernel.Emplace(Index, K);
					KernelSum += K;
				}
			}
		}
		if (!bNotch || Floor > 1.e30f || Top < -1.e30f || Top - Floor < 4.f)
		{
			continue;   // no wall here to drop (re-cut, already fallen, or the floor is level with the top)
		}
		const float Cut = Top - FMath::Clamp(Seg.TopShare, 0.f, 1.f) * (Top - Floor);
		// The failure plane starts where the wall's face rises through the cut level (going out from the floor, interpolated
		// between the cells) and rises back into the snow at the loose repose: the wall's top above the cut comes off, however
		// steep the talus has left the face (anchored at the foot instead, the plane passed over an eased wall's top: the first
		// sweep read a median pile of 0.8 litres, 0.9 cm high).
		float FaceAtCut = Face;
		{
			const int32 QStep = (Seg.bAlongX ? N.Y : N.X) >= 0.0 ? 1 : -1;
			float PrevLat = 0.f;
			float PrevSurface = 0.f;
			bool bPrev = false;
			for (int32 Q = QStep > 0 ? Q0 : Q1; QStep > 0 ? Q <= Q1 : Q >= Q0; Q += QStep)
			{
				const int32 Index = Seg.bAlongX ? (Q * SizeX + S) : (S * SizeX + Q);
				const float Lat = static_cast<float>(FVector2D::DotProduct(CellCentreCm(Index) - Seg.LinePoint, N));
				if (Lat < Face - 2.f * C || Lat > Face + TopReach)
				{
					continue;
				}
				const float Surface = SurfaceCm(Index);
				if (Surface >= Cut)
				{
					FaceAtCut = (bPrev && Surface > PrevSurface) ? PrevLat + (Cut - PrevSurface) / (Surface - PrevSurface) * (Lat - PrevLat) : Lat;
					break;
				}
				PrevLat = Lat;
				PrevSurface = Surface;
				bPrev = true;
			}
		}
		const float W = Feather > 0.f
			? Ramp(0.5f + static_cast<float>(Along - Seg.Along0) / Feather) * Ramp(0.5f + static_cast<float>(Seg.Along1 - Along) / Feather)
			: ((Along >= Seg.Along0 && Along < Seg.Along1) ? 1.f : 0.f);
		if (W <= 0.f)
		{
			continue;
		}
		for (int32 Q = Q0; Q <= Q1; ++Q)
		{
			const int32 Index = Seg.bAlongX ? (Q * SizeX + S) : (S * SizeX + Q);
			const float Lat = static_cast<float>(FVector2D::DotProduct(CellCentreCm(Index) - Seg.LinePoint, N));
			if (Lat < Face - 0.5f * C || Lat > Face + BackMax)
			{
				continue;
			}
			const float Keep = Cut + FMath::Max(0.f, Lat - FaceAtCut) * TanLoose;
			const float Off = W * (SurfaceCm(Index) - Keep);
			if (Off > 0.f)
			{
				Removes.Emplace(Index, Off);
				Volume += static_cast<double>(Off) * CellArea;
			}
		}
	}
	if (Volume <= 0.0 || KernelSum <= 0.0)
	{
		return false;
	}
	// Apply: the lumps go first (they sit on top), then the height; the pile lands exactly the volume taken.
	for (const TPair<int32, float>& Remove : Removes)
	{
		const int32 Index = Remove.Key;
		const float FromLump = FMath::Min(LumpCm[Index], Remove.Value);
		LumpCm[Index] -= FromLump;
		HeightCm[Index] -= Remove.Value - FromLump;
		Fresh[Index] = 1.f;
	}
	const bool bMarks = SnowMark.Num() == SizeX * SizeY;
	float PileTop = 0.f;
	for (const TPair<int32, float>& Cell : Kernel)
	{
		const float Rise = static_cast<float>(Volume * Cell.Value / (KernelSum * CellArea));
		HeightCm[Cell.Key] += Rise;
		PileTop = FMath::Max(PileTop, Rise);
		Fresh[Cell.Key] = 1.f;
		if (bMarks)
		{
			SnowMark[Cell.Key] |= SnowMarkDebris;
		}
	}
	++CollapsesFired;
	CollapseCm3 += Volume;
	const double MidLineT = (Mid - LineAxis) / DirAxis;
	const FVector2D PileXY = Seg.LinePoint + Dir * MidLineT + N * PileL;
	// One or two clumps on the pile (a hash of the segment and how often it has fallen), its own size law, along the line.
	if (bQueueClods)
	{
		const int32 KA = static_cast<int32>(Seg.Key >> 32);
		const int32 KB = static_cast<int32>(Seg.Key & 0xFFFFFFFFu);
		const int32 Salt = NoiseSeed + 431 + 17 * Seg.Fired;
		const int32 Lo2 = FMath::Max(0, CollapseClumpsMin);
		const int32 Hi2 = FMath::Max(Lo2, CollapseClumpsMax);
		const int32 Clumps = FMath::Clamp(Lo2 + FMath::FloorToInt(0.5f * (HashLattice(KA, KB, Salt) + 1.f) * (Hi2 - Lo2 + 1)), Lo2, Hi2);
		const float SizeMin = FMath::Max(1.f, ClodBankSizeMinCm);
		const float SizeMax = FMath::Max(SizeMin, ClodBankSizeMaxCm);
		for (int32 Clump = 0; Clump < Clumps; ++Clump)
		{
			const float UA = HashLattice(KA, KB + 101 * (Clump + 1), Salt + 1);
			const float UL = HashLattice(KA, KB + 101 * (Clump + 1), Salt + 2);
			const float USize = 0.5f * (HashLattice(KA, KB + 101 * (Clump + 1), Salt + 3) + 1.f);
			FClodSpawn Spawn;
			Spawn.XYCm = PileXY + Dir * (0.4 * PileA * UA) + N * (0.3 * Face * UL);
			Spawn.SizeCm = SizeMin + (SizeMax - SizeMin) * FMath::Pow(USize, FMath::Max(0.1f, ClodSizePower));
			Spawn.Seed = static_cast<int32>(static_cast<uint32>(KA) * 7919u + static_cast<uint32>(KB) * 104729u + static_cast<uint32>(Clump + 1 + 3 * Seg.Fired) * 15485863u);
			Spawn.Source = 3;   // on the trench floor, as LM4's fallen lip plates
			Spawn.HeadingDeg = FMath::RadiansToDegrees(static_cast<float>(FMath::Atan2(Dir.Y, Dir.X)));
			Spawn.bHeading = true;
			QueueClod(Spawn);
			++CollapseClumpsQueued;
		}
	}
	if (CollapseLog.Num() < 1024)
	{
		FCollapseEvent Event;
		Event.XYCm = PileXY;
		Event.Side = Seg.Side;
		Event.DelayS = static_cast<float>(SettleClockS - Seg.ArmS);
		Event.VolumeCm3 = Volume;
		Event.TopShare = Seg.TopShare;
		Event.PileTopCm = PileTop;
		Event.SegCm = SegCm;
		Event.AtS = SettleClockS;
		CollapseLog.Add(Event);
	}
	WakeTiles(X0, Y0, X1, Y1);
	MarkDirty(X0, Y0, X1 + 1, Y1 + 1);
	return true;
}

float FGTMudField::BellyOffsetCm(const FVector2D& XYCm, const FVector2D& Forward) const
{
	if (!bSnow || BellyUndulationCm <= 0.f)
	{
		return 0.f;
	}
	// LM4d item 1: two octaves in the frame of the world axis nearer the heading, stretched along it; each octave's lattice turned
	// in its own (stretched) space, so the anisotropy stays along the trench and no row of lattice points runs down it.
	const bool bAlongX = FMath::Abs(Forward.X) >= FMath::Abs(Forward.Y);
	const double Along = bAlongX ? XYCm.X : XYCm.Y;
	const double Across = bAlongX ? XYCm.Y : XYCm.X;
	const double Stretch = FMath::Max(1.f, BellyStretch);
	auto Octave = [&](float WaveCm, float AngleRad, int32 Salt, double Shift)
	{
		const double U = Along / (FMath::Max(1.f, WaveCm) * Stretch);
		const double V = Across / FMath::Max(1.f, WaveCm);
		const double C = FMath::Cos(AngleRad), S = FMath::Sin(AngleRad);
		return LatticeValueNoise(U * C - V * S + Shift, U * S + V * C + 0.5 * Shift, NoiseSeed + Salt);
	};
	const float N = Octave(BellyWaveMinCm, 0.41f, 451, 0.0) + Octave(BellyWaveMaxCm, 1.13f, 453, 0.37);
	// Two value-noise octaves summed read an sd of about 0.47 of a unit: x BellyUndulationCm, clamped, +-2.5 cm at most, about 1.2 sd.
	return BellyUndulationCm * FMath::Clamp(N, -1.f, 1.f);
}

float FGTMudField::SmearRidgeCm(const FVector2D& XYCm, const FVector2D& Forward) const
{
	if (!bSnow || SmearChance <= 0.f)
	{
		return 0.f;
	}
	// LM4d item 2: world lanes across the axis nearer the heading, each cut into segments along it with its own phase (so the
	// segments of neighbouring lanes do not end in rows); the cell reads its own lane and the two beside it.
	const bool bAlongX = FMath::Abs(Forward.X) >= FMath::Abs(Forward.Y);
	const double Along = bAlongX ? XYCm.X : XYCm.Y;
	const double Across = bAlongX ? XYCm.Y : XYCm.X;
	const int32 Axis = bAlongX ? 0 : 1;
	const float Lane = FMath::Max(4.f, SmearLaneCm);
	const float LenMin = FMath::Max(1.f, SmearLengthMinCm);
	const float LenMax = FMath::Max(LenMin, SmearLengthMaxCm);
	const float Mean = 0.5f * (LenMin + LenMax);
	const float Jitter = 0.25f * (LenMax - LenMin);
	const float Cluster = FMath::Max(1.f, SmearClusterCm);
	auto Ramp = [](float T) { T = FMath::Clamp(T, 0.f, 1.f); return T * T * (3.f - 2.f * T); };
	const int32 J0 = FMath::FloorToInt(static_cast<float>(Across / Lane));
	float Best = 0.f;
	for (int32 J = J0 - 1; J <= J0 + 1; ++J)
	{
		const int32 Salt = J * 2 + Axis;
		const double Phase = 0.5 * (HashLattice(J, 3000 + Axis, NoiseSeed + 461) + 1.f) * Mean;
		auto Boundary = [&](int32 K) { return static_cast<double>(K) * Mean + Phase + Jitter * HashLattice(K, Salt, NoiseSeed + 463); };
		int32 K = FMath::FloorToInt(static_cast<float>((Along - Phase) / Mean));
		if (Along < Boundary(K))
		{
			--K;
		}
		else if (Along >= Boundary(K + 1))
		{
			++K;
		}
		const double A0 = Boundary(K);
		const double A1 = Boundary(K + 1);
		const float Width = FMath::Lerp(SmearWidthMinCm, FMath::Max(SmearWidthMinCm, SmearWidthMaxCm), 0.5f * (HashLattice(K, Salt, NoiseSeed + 467) + 1.f));
		const double Centre = (J + 0.5) * Lane + 0.5 * HashLattice(K, Salt, NoiseSeed + 469) * FMath::Max(0.f, Lane - Width);
		const float Bunch = FMath::Clamp(0.5f + LatticeValueNoise(0.5 * (A0 + A1) / Cluster, Centre / Cluster, NoiseSeed + 471), 0.f, 1.f);
		if (0.5f * (HashLattice(K, Salt, NoiseSeed + 473) + 1.f) >= FMath::Clamp(SmearChance, 0.f, 1.f) * 2.f * Bunch)
		{
			continue;
		}
		const float T = static_cast<float>(FMath::Abs(Across - Centre)) / FMath::Max(0.5f, 0.5f * Width);
		if (T >= 1.f)
		{
			continue;
		}
		const float U = static_cast<float>((Along - A0) / FMath::Max(1.0, A1 - A0));
		const float Height = FMath::Lerp(SmearHeightMinCm, FMath::Max(SmearHeightMinCm, SmearHeightMaxCm), 0.5f * (HashLattice(K, Salt, NoiseSeed + 475) + 1.f));
		Best = FMath::Max(Best, Height * (1.f - T * T) * Ramp(U / 0.3f) * Ramp((1.f - U) / 0.3f));
	}
	return Best;
}

double FGTMudField::DepositChannel(TArrayView<const FBehindCell> Cells, const FVector2D& CentreCm, const FVector2D& Forward, float HalfL, float InnerNeg, float InnerPos,
	double Return, double& OutRidgeCm3)
{
	OutRidgeCm3 = 0.0;
	if (!bSnow || Cells.Num() == 0 || Return <= 0.0 || SnowMark.Num() != SizeX * SizeY || TreadTickOf.Num() != SizeX * SizeY)
	{
		return 0.0;
	}
	const double CellArea = static_cast<double>(CellCm) * CellCm;
	const float Band = FMath::Max(CellCm, ChannelBandCm);
	// The channel: cells the belly scraped that no tyre has ever covered, between the tyres' trenches (the scrape mark alone takes
	// in the trenches' outer shoulders the belly's feather cuts after the tyres have gone by, and where a tyre's shoulder fell short
	// of them no tyre covered them either: the first tests laid spill and ridges on the walls' tops by the berm).
	const FVector2D Across(-Forward.Y, Forward.X);
	auto Channel = [&](int32 Index)
	{
		if ((SnowMark[Index] & SnowMarkScraped) == 0 || TreadTickOf[Index] != 0u)
		{
			return false;
		}
		const float Side = static_cast<float>(FVector2D::DotProduct(CellCentreCm(Index) - CentreCm, Across));
		return Side > InnerNeg && Side < InnerPos;
	};
	// Item 2: the ridges, on the channel's cells as they leave the box (each cell once), out of the return.
	double Budget = Return;
	if (SmearChance > 0.f)
	{
		for (const FBehindCell& Cell : Cells)
		{
			if (Cell.Along < -HalfL - Band || !Channel(Cell.Index) || (SnowMark[Cell.Index] & SnowMarkSmeared))
			{
				continue;
			}
			SnowMark[Cell.Index] |= SnowMarkSmeared;
			++SmearCells;
			const float Height = SmearRidgeCm(CellCentreCm(Cell.Index), Forward);
			if (Height <= 0.f || Budget <= 0.0)
			{
				continue;
			}
			const double Volume = FMath::Min(static_cast<double>(Height) * CellArea, Budget);
			const float Before = SurfaceCm(Cell.Index);
			HeightCm[Cell.Index] += static_cast<float>(Volume / CellArea);
			Budget -= Volume;
			OutRidgeCm3 += Volume;
			TouchCell(Cell.Index, Before);
		}
		SmearCm3 += OutRidgeCm3;
	}
	// Item 3: the spill, PloughSpillShare of the side deposit, onto the lump sites whose centre is SpillBackCm..+Band behind the box.
	double Landed = 0.0;
	const double Spill = FMath::Clamp(PloughSpillShare, 0.f, 1.f) * Budget;
	if (Spill > 0.0 && bLumpSoftDomes && LumpShare > 0.f)
	{
		EnsureLumpWeights();
		if (LumpW.Num() == SizeX * SizeY && LumpSiteOf.Num() == SizeX * SizeY && SiteCellStart.Num() == PlateSites.Num() + 1)
		{
			struct FSpillSite
			{
				int32 Site = INDEX_NONE;
				double Weight = 0.0;
			};
			TArray<FSpillSite, TInlineAllocator<32>> Sites;
			double WeightSum = 0.0;
			for (const FBehindCell& Cell : Cells)
			{
				const int32 Site = LumpSiteOf[Cell.Index];
				if (Site == INDEX_NONE || !PlateSites.IsValidIndex(Site) || !PlateSites[Site].bPresent
					|| Sites.ContainsByPredicate([Site](const FSpillSite& Each) { return Each.Site == Site; }))
				{
					continue;
				}
				const float SiteAlong = static_cast<float>(FVector2D::DotProduct(LumpSiteCentreCm(Site) - CentreCm, Forward));
				if (SiteAlong >= -HalfL - SpillBackCm || SiteAlong < -HalfL - SpillBackCm - Band)
				{
					continue;
				}
				double Kernel = 0.0;
				for (int32 K = SiteCellStart[Site]; K < SiteCellStart[Site + 1]; ++K)
				{
					const int32 Index = SiteCellList[K];
					Kernel += Channel(Index) ? LumpW[Index] : 0.f;
				}
				const int32 CentreIndex = CellIndexAt(LumpSiteCentreCm(Site));
				const float Bunch = CentreIndex != INDEX_NONE ? LumpClusterWeight(CentreIndex % SizeX, CentreIndex / SizeX) : 1.f;
				const double Weight = Kernel * Bunch;
				if (Weight <= 0.0)
				{
					continue;
				}
				Sites.Add({ Site, Weight });
				WeightSum += Weight;
			}
			for (const FSpillSite& Each : Sites)
			{
				// The site's share: a soft dome T x its kernel over its channel cells (its lump there and the new share), at most
				// its height cap; what is over the cap a soft mound in HeightCm by the same kernel (exact).
				const double Share = Spill * Each.Weight / WeightSum;
				double KernelSum = 0.0;
				float KernelMax = 0.f;
				double Lump = 0.0;
				for (int32 K = SiteCellStart[Each.Site]; K < SiteCellStart[Each.Site + 1]; ++K)
				{
					const int32 Index = SiteCellList[K];
					if (Channel(Index) && LumpW[Index] > 0.f)
					{
						KernelSum += LumpW[Index];
						KernelMax = FMath::Max(KernelMax, LumpW[Index]);
						Lump += LumpCm[Index];
					}
				}
				if (KernelSum <= 1.e-9)
				{
					continue;
				}
				const double Total = Lump + Share / CellArea;
				double T = Total / KernelSum;
				const double Cap = FMath::Max(0.f, PlateSites[Each.Site].CapCm);
				if (KernelMax > 0.f && T * KernelMax > Cap)
				{
					T = Cap / KernelMax;
				}
				const double Mound = (Total - T * KernelSum) / KernelSum;   // per unit of kernel, cm
				for (int32 K = SiteCellStart[Each.Site]; K < SiteCellStart[Each.Site + 1]; ++K)
				{
					const int32 Index = SiteCellList[K];
					if (!Channel(Index) || LumpW[Index] <= 0.f)
					{
						continue;
					}
					const float Before = SurfaceCm(Index);
					const float NewLump = static_cast<float>(T * LumpW[Index]);
					SpillLumpCm3 += (static_cast<double>(NewLump) - LumpCm[Index]) * CellArea;
					LumpCm[Index] = NewLump;
					HeightCm[Index] += static_cast<float>(Mound * LumpW[Index]);
					TouchCell(Index, Before);
				}
				Landed += Share;
				// A site's first spill rolls for a clump on it (more where the lumps bunch).
				bool bSeen = false;
				SpillSites.Add(Each.Site, &bSeen);
				if (!bSeen && bQueueClods && SpillClumpChance > 0.f)
				{
					const FVector2D SiteXY = LumpSiteCentreCm(Each.Site);
					const int32 CentreIndex = CellIndexAt(SiteXY);
					const float Bunch = CentreIndex != INDEX_NONE ? LumpClusterWeight(CentreIndex % SizeX, CentreIndex / SizeX) : 1.f;
					if (0.5f * (HashLattice(Each.Site, 4001, NoiseSeed + 481) + 1.f) < SpillClumpChance * Bunch)
					{
						const float USize = 0.5f * (HashLattice(Each.Site, 4003, NoiseSeed + 483) + 1.f);
						const float SizeMin = FMath::Max(1.f, ClodBankSizeMinCm);
						const float SizeMax = FMath::Max(SizeMin, ClodBankSizeMaxCm);
						FClodSpawn Spawn;
						Spawn.XYCm = SiteXY;
						Spawn.SizeCm = SizeMin + (SizeMax - SizeMin) * FMath::Pow(USize, FMath::Max(0.1f, ClodSizePower));
						Spawn.Seed = static_cast<int32>(static_cast<uint32>(Each.Site) * 7919u + static_cast<uint32>(NoiseSeed) * 15485863u + 4001u);
						Spawn.Source = 4;   // LM4d: spilled from the belly's berm into its channel
						Spawn.HeadingDeg = FMath::RadiansToDegrees(static_cast<float>(FMath::Atan2(Forward.Y, Forward.X)));
						Spawn.bHeading = true;
						QueueClod(Spawn);
						++SpillClumpsQueued;
					}
				}
			}
		}
	}
	SpillCm3 += Landed;
	return OutRidgeCm3 + Landed;
}

float FGTMudField::WallOffsetAt(const FVector2D& FootCm, const FVector2D& LineDir, float Side, bool& bOutDrop, uint64& OutKey, float* OutDropWeight) const
{
	bOutDrop = false;
	OutKey = 0;
	if (OutDropWeight)
	{
		*OutDropWeight = 0.f;
	}
	if (!WallLineOn())
	{
		return 0.f;
	}
	// LM4 item 3: segments along the world axis nearer the stroke's direction (so a track's front and rear tyres share
	// them whatever their small yaw), WallSegMinCm..WallSegMaxCm long: boundaries every mean length, each jittered by a
	// quarter of the range. The lane is the tyre line's 60 cm band across, so two tyres' walls step independently.
	// LM4b: the segments carry only the drops; the line itself is the continuous waves below (with LM4's steps off).
	const bool bAlongX = FMath::Abs(LineDir.X) >= FMath::Abs(LineDir.Y);
	const double Along = bAlongX ? FootCm.X : FootCm.Y;
	const double Across = bAlongX ? FootCm.Y : FootCm.X;
	const float SegMin = FMath::Max(1.f, WallSegMinCm);
	const float SegMax = FMath::Max(SegMin, WallSegMaxCm);
	const float Mean = 0.5f * (SegMin + SegMax);
	const float Jitter = 0.25f * (SegMax - SegMin);
	const int32 Axis = bAlongX ? 0 : 1;
	auto Boundary = [&](int32 K) { return static_cast<double>(K) * Mean + Jitter * HashLattice(K, 1000 + Axis, NoiseSeed + 211); };
	int32 K = FMath::FloorToInt(static_cast<float>(Along / Mean));
	if (Along < Boundary(K))
	{
		--K;
	}
	else if (Along >= Boundary(K + 1))
	{
		++K;
	}
	const int32 Lane = FMath::FloorToInt(static_cast<float>(Across / 60.0));
	const int32 Salt = ((Lane * 2 + (Side > 0.f ? 1 : 0)) * 2) + Axis;
	const float DropShare = FMath::Clamp(WallDropShare, 0.f, 1.f);
	auto Drops = [&](int32 KK) { return 0.5f * (HashLattice(KK, Salt, NoiseSeed + 229) + 1.f) < DropShare; };
	bOutDrop = Drops(K);
	OutKey = (static_cast<uint64>(static_cast<uint32>(K)) << 32) | static_cast<uint64>(static_cast<uint32>(Salt));
	if (OutDropWeight)
	{
		// LM4b item 2: the notch's ends feather - across each segment boundary the drop's share ramps (a smoothstep over
		// WallDropFeatherCells cells centred on the boundary) between the two segments' own 0 or 1. Off: LM4's hard 0 / 1.
		float W = bOutDrop ? 1.f : 0.f;
		const float Feather = FMath::Max(0.f, WallDropFeatherCells) * CellCm;
		if (Feather > 0.f)
		{
			const float Half = 0.5f * Feather;
			const float Lo = static_cast<float>(Along - Boundary(K));
			const float Hi = static_cast<float>(Boundary(K + 1) - Along);
			auto Ramp = [](float T) { T = FMath::Clamp(T, 0.f, 1.f); return T * T * (3.f - 2.f * T); };
			if (Lo < Half)
			{
				W = FMath::Lerp(Drops(K - 1) ? 1.f : 0.f, W, Ramp(0.5f + Lo / Feather));
			}
			else if (Hi < Half)
			{
				W = FMath::Lerp(Drops(K + 1) ? 1.f : 0.f, W, Ramp(0.5f + Hi / Feather));
			}
		}
		*OutDropWeight = W;
	}
	if (WallStepMaxCm > 0.f)
	{
		// LM4's stepped line. The magnitude is one of three levels across StepMin..WallStepMaxCm (3, 5.5, 8 cm), each jittered
		// by 5 % of the range, so two segments on one side step by at least 2 cm unless they drew the same sign and level (a
		// sixth of boundaries); a uniform magnitude left a third of the boundaries under 2 cm (the first test read 12-18 % of
		// stations stepping).
		const float USign = HashLattice(K, Salt, NoiseSeed + 223);
		const float UMag = 0.5f * (HashLattice(K, Salt, NoiseSeed + 227) + 1.f);
		const float UJitter = HashLattice(K, Salt, NoiseSeed + 231);
		const float StepMin = FMath::Clamp(WallStepMinCm, 0.f, WallStepMaxCm);
		const float Range = WallStepMaxCm - StepMin;
		const float Level = static_cast<float>(FMath::Min(2, FMath::FloorToInt(UMag * 3.f)));
		const float Magnitude = FMath::Clamp(StepMin + Range * (0.5f * Level + 0.05f * UJitter), StepMin, WallStepMaxCm);
		return (USign >= 0.f ? 1.f : -1.f) * Magnitude;
	}
	// LM4b item 1: two octaves of smoothed value noise along the line (a lattice row per wall side and lane, so the two walls
	// and two tyres wander independently), no step anywhere: the outline is continuous and its slope bounded.
	const float Short = FMath::Max(1.f, WallWaveCm);
	const float Long = FMath::Max(1.f, WallWaveLongCm);
	return WallWaveAmpCm * LatticeValueNoise(Along / Short, Salt, NoiseSeed + 251)
		+ WallWaveLongAmpCm * LatticeValueNoise(Along / Long + 0.37, Salt, NoiseSeed + 257);
}

void FGTMudField::BuildSnow(const TFunction<float(const FVector2D&)>& DepthAt)
{
	if (!IsValid())
	{
		return;
	}
	const int32 Count = SizeX * SizeY;
	SnowDepthCell.SetNumUninitialized(Count);
	SnowTopCm.SetNumUninitialized(Count);
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const FVector2D Centre = CellCentreCm(Index);
		SnowDepthCell[Index] = FMath::Max(0.f, DepthAt ? DepthAt(Centre) : SnowDepthCm);
		SnowTopCm[Index] = FMath::Max(0.f, SnowDepthCell[Index] + SnowTopNoiseCm(Centre)) * SnowTaperAt(Centre);   // LM4 item 6: SnowTopAt's rule
	}
}

void FGTMudField::BuildLugStrength()
{
	const int32 Count = SizeX * SizeY;
	if (!IsValid() || Count <= 0)
	{
		LugStrength.Reset();
		return;
	}
	// LM3c item 2: the strength is a value noise at LugWaveCm ranked over the field, so it spreads evenly over
	// LugStrengthMin..1 (a raw value noise bunches about its middle); the missing patches are the cells under the
	// LugMissingShare quantile of a second noise at LugMissingCm. Both are functions of the cell and NoiseSeed alone.
	TArray<float> Strength;
	TArray<float> Missing;
	Strength.SetNumUninitialized(Count);
	Missing.SetNumUninitialized(Count);
	const float WaveCells = FMath::Max(1.f, LugWaveCm / CellCm);
	const float MissingCells = FMath::Max(1.f, LugMissingCm / CellCm);
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const int32 X = Index % SizeX;
		const int32 Y = Index / SizeX;
		Strength[Index] = CellNoise(X, Y, WaveCells, 61);
		Missing[Index] = CellNoise(X, Y, MissingCells, 67);
	}
	TArray<int32> Order;
	Order.SetNumUninitialized(Count);
	for (int32 Index = 0; Index < Count; ++Index)
	{
		Order[Index] = Index;
	}
	Order.Sort([&Strength](int32 A, int32 B) { return Strength[A] < Strength[B]; });
	LugStrength.SetNumUninitialized(Count);
	const float Lo = FMath::Clamp(LugStrengthMin, 0.f, 1.f);
	for (int32 Rank = 0; Rank < Count; ++Rank)
	{
		LugStrength[Order[Rank]] = Lo + (1.f - Lo) * (Count > 1 ? static_cast<float>(Rank) / (Count - 1) : 1.f);
	}
	const float Share = FMath::Clamp(LugMissingShare, 0.f, 1.f);
	if (Share > 0.f)
	{
		TArray<float> Sorted = Missing;
		Sorted.Sort();
		const float Threshold = Sorted[FMath::Clamp(FMath::RoundToInt(Share * Count), 0, Count - 1)];
		for (int32 Index = 0; Index < Count; ++Index)
		{
			if (Missing[Index] < Threshold)
			{
				LugStrength[Index] = 0.f;
			}
		}
	}
}

double FGTMudField::PloughBelly(const FVector2D& CentreCm, const FVector2D& Forward, float LengthCm, float WidthCm, float UndersideCm)
{
	const FOuterCall Call(*this);   // LM4e
	Call.Record(EventPloughBelly, { CentreCm.X, CentreCm.Y, Forward.X, Forward.Y, LengthCm, WidthCm, UndersideCm });
	if (!IsValid() || !bSnow || LengthCm <= 0.f || WidthCm <= 0.f || SnowTopCm.Num() != SizeX * SizeY)
	{
		return 0.0;
	}
	const FVector2D F = Forward.GetSafeNormal();
	if (F.IsNearlyZero())
	{
		return 0.0;
	}
	const FVector2D R(-F.Y, F.X);
	// The box, its side walls feathered over one rut wall (snow stands: max(CellCm, RutShoulderCm)), and a berm band of
	// PloughBandCm beyond each wall along the box's length. The front is not feathered: the car rides on into it.
	const float HalfL = 0.5f * LengthCm;
	const float HalfW = 0.5f * WidthCm;
	const float Wall = FMath::Max(CellCm, RutShoulderCm);
	const float Band = FMath::Max(CellCm, PloughBandCm);
	// LM3c item 3: through the bank path the band's width swings by RidgeWidthWave (stage I), so the reach is its widest.
	const bool bBank = bPloughBankPath;
	const float WidthWave = FMath::Clamp(RidgeWidthWave, 0.f, 1.f);
	const float BandMax = bBank ? Band * (1.f + WidthWave) : Band;
	// LM4d items 2 and 3: the smear ridges and the spill land on the channel's cells behind the box (a band it has left), so the
	// reach runs that far behind it.
	const bool bChannelMarks = TreadTickOf.Num() == SizeX * SizeY && SnowMark.Num() == SizeX * SizeY;
	const bool bChannel = bChannelMarks && (SmearChance > 0.f || PloughSpillShare > 0.f);
	const float ChannelBand = FMath::Max(CellCm, ChannelBandCm);
	const float BehindCm = !bChannel ? 0.f : (PloughSpillShare > 0.f ? FMath::Max(ChannelBand, SpillBackCm + ChannelBand + 30.f) : ChannelBand);
	TArray<FBehindCell, TInlineAllocator<512>> BehindCells;
	float InnerNeg = -TNumericLimits<float>::Max();   // the innermost tyre-covered cells under the box, either side across it (cm)
	float InnerPos = TNumericLimits<float>::Max();
	const float Reach = FMath::Sqrt(FMath::Square(HalfL + BehindCm) + FMath::Square(HalfW + Wall + BandMax)) + CellCm;
	const FVector2D C = CentreCm - OriginCm;
	if (C.X + Reach < 0.f || C.Y + Reach < 0.f || C.X - Reach > SizeX * CellCm || C.Y - Reach > SizeY * CellCm)
	{
		return 0.0;
	}
	const int32 X0 = FMath::Clamp(FMath::FloorToInt((C.X - Reach) / CellCm), 0, SizeX - 1);
	const int32 Y0 = FMath::Clamp(FMath::FloorToInt((C.Y - Reach) / CellCm), 0, SizeY - 1);
	const int32 X1 = FMath::Clamp(FMath::CeilToInt((C.X + Reach) / CellCm), 0, SizeX - 1);
	const int32 Y1 = FMath::Clamp(FMath::CeilToInt((C.Y + Reach) / CellCm), 0, SizeY - 1);
	const float CellArea = CellCm * CellCm;
	double Removed = 0.0;
	struct FBerm
	{
		int32 Index = 0;
		float Weight = 0.f;
		float Before = 0.f;
	};
	TArray<FBerm, TInlineAllocator<256>> Berm;
	double BermWeight = 0.0;
	// LM3c item 1: the belly's heading (turns) for the cells it scrapes, and the marks (snow fields carry them).
	const float BellyTurns = Wrap01(static_cast<float>(FMath::Atan2(F.Y, F.X)) / (2.f * PI));
	const bool bMarks = TreadTickOf.Num() == SizeX * SizeY && SnowMark.Num() == SizeX * SizeY;
	// LM3c item 3: the bank path's numbers, as StampWheel reads them.
	// LM3c follow-up: scaled by the berm's PloughBankVariation.
	const float BermSwing = FMath::Max(0.f, PloughBankVariation);
	const float SideBias = FMath::Clamp(RidgeSideBias * BermSwing, 0.f, 0.9f);
	const float WaveAmount = FMath::Max(0.f, RidgeWave * BermSwing);
	const float NoiseRidge = FMath::Max(0.f, RidgeNoise * BermSwing);
	if (bBank && PloughLumpShare > 0.f)
	{
		EnsureLumpWeights();
	}
	// LM4c item 3: the berm's falling profile and its cluster factor (snow; off: LM4b's plateau, no factor).
	const bool bFalling = bBank && bPloughFallingProfile;
	const bool bPiles = bBank && PilesOn();
	const bool bDebrisMarks = SnowMark.Num() == SizeX * SizeY;
	// LM4f item 4: the bank weight's static noises from their slots (StampWheel's), and the piles' arrays ensured once here.
	const float WaveCells = FMath::Max(1.f, RidgeWaveCm / CellCm);
	const float WaveLongCells = FMath::Max(1.f, RidgeWaveLongCm / CellCm);
	const float MetreCells = FMath::Max(1.f, 100.f / CellCm);
	const float* NWave = bBank ? NoiseCells(NoiseWave, WaveCells, 11) : nullptr;
	const float* NWaveLong = bBank ? NoiseCells(NoiseWaveLong, WaveLongCells, 13) : nullptr;
	const float* NSide = bBank ? NoiseCells(NoiseSide, MetreCells, 17) : nullptr;
	const float* NClump = bBank ? NoiseCells(NoiseClump, RidgeNoiseCells, 0) : nullptr;
	if (bPiles)
	{
		EnsureSnowPiles();
	}
	for (int32 Y = Y0; Y <= Y1; ++Y)
	{
		for (int32 X = X0; X <= X1; ++X)
		{
			const FVector2D P = FVector2D((X + 0.5f) * CellCm, (Y + 0.5f) * CellCm) - C;
			const float AlongSigned = static_cast<float>(FVector2D::DotProduct(P, F));
			const float Along = FMath::Abs(AlongSigned);
			const float AcrossSigned = static_cast<float>(FVector2D::DotProduct(P, R));
			const float Across = FMath::Abs(AcrossSigned);
			const int32 Index = Y * SizeX + X;
			if (bChannel && TreadTickOf[Index] != 0u && Across <= HalfW + Wall)
			{
				// LM4d: the innermost tyre-covered cells anywhere in the reach, the front tyres' fresh trench ahead of the box included
				// (at the start of a drive none is under it yet, and the whole box read as channel: ridges and spill on the rear
				// tyres' lines, which they then cut).
				(AcrossSigned >= 0.f ? InnerPos : InnerNeg) = AcrossSigned >= 0.f ? FMath::Min(InnerPos, AcrossSigned) : FMath::Max(InnerNeg, AcrossSigned);
			}
			if (Along > HalfL)
			{
				// LM4d: a cell the box has left behind it, within the band the ridges and the spill land in.
				if (bChannel && AlongSigned < -HalfL && AlongSigned >= -HalfL - BehindCm && Across <= HalfW + Wall)
				{
					BehindCells.Add({ Index, AlongSigned });
				}
				continue;
			}
			if (Across <= HalfW + Wall)
			{
				// Down to the underside where the snow stands above it (relative to the snow top), only ever lowered. LM4d item 1:
				// the underside's height over the ground undulates by +-BellyUndulationCm under the belly's full width (0 on LM4c's
				// level floor); its feathered sides keep LM4c's target, so the trenches' outer walls and lips are as LM4c left them.
				const float Target = FMath::Min(0.f, UndersideCm + (Across <= HalfW ? BellyOffsetCm(OriginCm + C + P, F) : 0.f) - SnowTopCm[Index]);
				if (Target >= 0.f)
				{
					continue;
				}
				const float Cut = 1.f - FMath::Clamp((Across - HalfW) / Wall, 0.f, 1.f);
				const float Profile = Cut * Cut * (3.f - 2.f * Cut);
				const float SoftTarget = Target * Profile;
				const float Before = SurfaceCm(Index);
				if (Before <= SoftTarget)
				{
					continue;
				}
				if (LumpCm[Index] > 0.f)
				{
					const double Lump = static_cast<double>(LumpCm[Index]) * CellArea;
					Removed += Lump;
					Book.FlattenedCm3 += Lump;
					LumpCm[Index] = 0.f;
				}
				if (HeightCm[Index] > SoftTarget)
				{
					Removed += (HeightCm[Index] - SoftTarget) * CellArea;
					HeightCm[Index] = SoftTarget;
				}
				if (bDebrisMarks)
				{
					SnowMark[Index] &= ~(SnowMarkDebris | SnowMarkSmeared);   // LM4c: a collapse's pile the belly scraped is cut snow now; LM4d: its ridge too
				}
				Tracks[Index] = FMath::Max(Tracks[Index], static_cast<uint8>(FMath::RoundToInt(255.f * Profile)));
				// LM3c item 1: a cell the belly flattened that no tyre capsule covered this tick loses its tread (no lugs
				// across the belly's channel) and takes the belly's heading (the material's scrape streaks run along it).
				if (bMarks && TreadTickOf[Index] != TreadTick)
				{
					PhaseTurns[Index] = -1.f;
					HeadingTurns[Index] = BellyTurns;
					SnowMark[Index] |= SnowMarkScraped;
				}
				TouchCell(Index, Before);
			}
			else if (Across <= HalfW + Wall + BandMax && HeightCm[Index] >= -1.f)
			{
				// The berm, on cells that are not a rut (a tyre's trench keeps its floor).
				const float Out = Across - HalfW - Wall;
				float Weight = 0.f;
				if (!bBank)
				{
					// LM3b: a sine hump across the band.
					Weight = FMath::Sin(PI * FMath::Clamp(Out / Band, 0.f, 1.f));
				}
				else
				{
					// LM3c: a tyre's bank weight (StampWheel's), read at the cell's foot on the box's long side, so one station
					// along the trench has one height, one width and one heavier side: stage I1's plateau over a width swung by
					// RidgeWidthWave, stage I2's two waves along it (RidgeWave), RidgeSideBias, and stage H's clumps
					// (RidgeNoise). Everything lives in the weight; the volume is normalised below, so it is exact.
					const float Side = FVector2D::DotProduct(P, R) >= 0.0 ? 1.f : -1.f;
					const FVector2D Foot = C + F * FVector2D::DotProduct(P, F) + R * (Side * (HalfW + Wall));
					const int32 SX = FMath::FloorToInt(Foot.X / CellCm);
					const int32 SY = FMath::FloorToInt(Foot.Y / CellCm);
					const float HeightWave = NoiseAt(NWave, SX, SY, WaveCells, 11);
					const float LongWave = NoiseAt(NWaveLong, SX, SY, WaveLongCells, 13);
					const float SideNoise = FMath::Clamp(2.f * NoiseAt(NSide, SX, SY, MetreCells, 17), -1.f, 1.f);
					const float WidthHere = FMath::Clamp(Band * (1.f + WidthWave * LongWave), 0.25f * Band, BandMax);
					if (Out <= WidthHere)
					{
						if (bFalling)
						{
							// LM4c item 3: heaviest at the wall, falling outward over the band, (1 - u)^PloughFallPower (the talus spreads it after).
							const float U = FMath::Clamp(Out / FMath::Max(1.f, WidthHere), 0.f, 1.f);
							Weight = FMath::Pow(1.f - U, FMath::Max(0.1f, PloughFallPower));
						}
						else
						{
							const float FootCm = FMath::Clamp(RidgeFootCm, 1.f, 0.5f * WidthHere);
							const float In = FMath::Clamp(Out / FootCm, 0.f, 1.f);
							const float Down = FMath::Clamp((WidthHere - Out) / FootCm, 0.f, 1.f);
							Weight = (In * In * (3.f - 2.f * In)) * (Down * Down * (3.f - 2.f * Down));
						}
						Weight *= FMath::Max(0.05f, 1.f + WaveAmount * (0.7f * HeightWave + 0.5f * LongWave));
						Weight *= FMath::Max(0.05f, 1.f + SideBias * Side * SideNoise);
						Weight *= FMath::Max(0.05f, 1.f + NoiseRidge * NoiseAt(NClump, X, Y, RidgeNoiseCells, 0));
						if (bPiles)
						{
							// LM4c item 3: the cluster factor at the cell's foot on the box's side (the lips read theirs on the tyre's line).
							Weight *= PileFactorReady(OriginCm + Foot);   // LM4f: ensured above
						}
					}
				}
				if (Weight > 0.f)
				{
					Berm.Add({ Index, Weight, SurfaceCm(Index) });
					BermWeight += Weight;
				}
			}
		}
	}
	if (bMarks)
	{
		++TreadTick;   // the next tick's tyre stamps
	}
	if (Removed > 0.0)
	{
		const double Return = FMath::Clamp(PloughReturn, 0.f, 1.f) * Removed;
		// LM4d items 2 and 3: the smear ridges and the spill come out of the return (moved, not lost: the compaction is the same);
		// the side berms take the rest. PloughBermCm3 books the whole return.
		double RidgeCm3 = 0.0;
		const double ChannelCm3 = bChannel ? DepositChannel(BehindCells, CentreCm, F, HalfL, InnerNeg, InnerPos, Return, RidgeCm3) : 0.0;
		const double Volume = Return - ChannelCm3;
		if (BermWeight > 0.0 && !bBank)
		{
			for (const FBerm& Cell : Berm)
			{
				HeightCm[Cell.Index] += static_cast<float>(Volume * Cell.Weight / (BermWeight * CellArea));
				TouchCell(Cell.Index, Cell.Before);
			}
			PloughBermCm3 += Return;   // LM4d: the whole return (the channel's ridges and spill with the berms)
		}
		else if (BermWeight > 0.0)
		{
			// LM3c: LumpShare of the deposit into the lump domes over the berm's cells (LM2a's lumps, with LM2c's held share:
			// it scales with the lump weight that exists over these cells against the full site set's, so an absent site's
			// share stays in the bank), the rest into the bank by the weights; a lump over LumpMaxCm overflows into HeightCm
			// in its own cell. No MaxRidgeCm cap (LM3b's berm had none) and no smoothing (the cells are marked).
			double LumpWeightSum = 0.0;
			double LumpFullSum = 0.0;
			const bool bLumps = PloughLumpShare > 0.f && LumpW.Num() == SizeX * SizeY;   // LM3c follow-up: the berm's own share
			if (bLumps)
			{
				for (const FBerm& Cell : Berm)
				{
					LumpWeightSum += LumpW[Cell.Index];
					LumpFullSum += LumpWFull.IsValidIndex(Cell.Index) ? LumpWFull[Cell.Index] : LumpW[Cell.Index];
				}
			}
			const float LumpK = (bLumps && LumpWeightSum > 0.0) ? FMath::Clamp(PloughLumpShare, 0.f, 1.f) : 0.f;
			const float HeldShare = (bLumpVariety && LumpFullSum > 0.0) ? LumpK * static_cast<float>(FMath::Min(1.0, LumpWeightSum / LumpFullSum)) : LumpK;
			const double Held = static_cast<double>(HeldShare) * Volume;
			const double BankVolume = Volume - Held;
			double OverflowCm3 = 0.0;   // LM3c follow-up: what the lumps could not hold, back into the berm's shape below
			// LM4 item 2: with plates, the held share lands flat on the plates' cells (W, uncapped) and each plate touched is
			// re-levelled to its tilted plane; what the clamp cannot hold overflows into the berm like a capped lump.
			const bool bPlates = LumpsShaped() && Held > 0.0;   // LM4b: the soft domes the same way
			TArray<int32, TInlineAllocator<32>> Touched;
			int32 PX0 = X0, PY0 = Y0, PX1 = X1, PY1 = Y1;
			for (const FBerm& Cell : Berm)
			{
				HeightCm[Cell.Index] += static_cast<float>(BankVolume * Cell.Weight / (BermWeight * CellArea));
				if (Held > 0.0 && LumpW[Cell.Index] > 0.f)
				{
					const float Add = static_cast<float>(Held * LumpW[Cell.Index] / (LumpWeightSum * CellArea));
					if (bPlates && bMarks && (SnowMark[Cell.Index] & SnowMarkDropped))
					{
						// A lip cell whose plate fell in takes no plate (item 3): its share is bank here. LM4b: over the berm's whole
						// band (the overflow's spread), not in this one cell - a soft dome's centre takes a large share of W every
						// plough tick, and in the one cell it built a 41 cm tower (GrandTour.Snow.Compact's berm row, 2.18x).
						if (bLumpSoftDomes)
						{
							OverflowCm3 += static_cast<double>(Add) * CellArea;
						}
						else
						{
							HeightCm[Cell.Index] += Add;
						}
					}
					else if (bPlates)
					{
						LumpCm[Cell.Index] += Add;
						PloughLumpCm3 += static_cast<double>(Add) * CellArea;
						Touched.AddUnique(LumpSiteOf[Cell.Index]);
					}
					else
					{
						const float Over = bLumpOverflowToBand ? AddLumpCapped(Cell.Index, Add) : AddLump(Cell.Index, Add);
						OverflowCm3 += static_cast<double>(Over) * CellArea;
						PloughLumpCm3 += static_cast<double>(Add - Over) * CellArea;
					}
				}
				if (bMarks)
				{
					SnowMark[Cell.Index] |= SnowMarkBerm;
				}
			}
			if (bPlates && Touched.Num() > 0)
			{
				const double Over = ReshapeLumps(Touched, PX0, PY0, PX1, PY1);
				PloughLumpCm3 -= Over;
				if (bLumpOverflowToBand)
				{
					OverflowCm3 += Over;
				}
				else
				{
					// LM2a's rule has no band to go to: the plates' excess into the berm cells' banks evenly (exact).
					for (const FBerm& Cell : Berm)
					{
						HeightCm[Cell.Index] += static_cast<float>(Over * Cell.Weight / (BermWeight * CellArea));
					}
				}
				WakeTiles(PX0, PY0, PX1, PY1);
				MarkDirty(PX0, PY0, PX1 + 1, PY1 + 1);
			}
			if (bLumpOverflowToBand && OverflowCm3 > 0.0)
			{
				for (const FBerm& Cell : Berm)
				{
					HeightCm[Cell.Index] += static_cast<float>(OverflowCm3 * Cell.Weight / (BermWeight * CellArea));
				}
			}
			for (const FBerm& Cell : Berm)
			{
				TouchCell(Cell.Index, Cell.Before);
			}
			PloughBermCm3 += Return;   // LM4d: the whole return (the channel's ridges and spill with the berms)
		}
		else
		{
			PloughBermCm3 += ChannelCm3;
			PloughLostCm3 += Volume;
		}
		PloughedCm3 += Removed;
		LoweredCm3 += Removed;
	}
	WakeTiles(X0, Y0, X1, Y1);
	MarkDirty(X0, Y0, X1 + 1, Y1 + 1);
	return Removed;
}

double FGTMudField::Refill(float Seconds)
{
	if (!IsValid() || !bSnow || Seconds <= 0.f || RefillCmPerMin <= 0.f)
	{
		return 0.0;
	}
	const float Rise = RefillCmPerMin * Seconds / 60.f;
	// The tracks fade by the same share of the snow's depth as the cuts rise (a full-depth trench refills and loses its
	// packed look together). Tracks are bytes, so the fade carries its fraction over from pass to pass.
	RefillTrackCarry += 255.f * Rise / FMath::Max(1.f, SnowDepthCm);
	const int32 Fade = FMath::FloorToInt(RefillTrackCarry);
	RefillTrackCarry -= Fade;
	double Added = 0.0;
	const int32 Count = SizeX * SizeY;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		float& Height = HeightCm[Index];
		if (Height < 0.f)
		{
			const float Raised = FMath::Min(0.f, Height + Rise);
			Added += Raised - Height;
			Height = Raised;
		}
		if (LumpCm[Index] > 0.f)
		{
			LumpCm[Index] = FMath::Max(0.f, LumpCm[Index] - Rise);   // the lumps soften under the new snow
		}
		if (Fade > 0 && Tracks[Index] > 0)
		{
			Tracks[Index] = static_cast<uint8>(FMath::Max(0, static_cast<int32>(Tracks[Index]) - Fade));
		}
	}
	Added *= static_cast<double>(CellCm) * CellCm;
	RefilledCm3 += Added;
	MarkDirty(0, 0, SizeX, SizeY);
	return Added;
}

void FGTMudField::EnsureLumpWeights()
{
	const int32 Cells = SizeX * SizeY;
	const int32 Variety = bLumpVariety ? 1 : 0;
	const int32 PlatesKey = bLumpPlates ? 1 + 1000 * FMath::RoundToInt(PlateTiltMinDeg * 10.f) + FMath::RoundToInt(PlateTiltMaxDeg * 10.f) : 0;
	// LM4b: the soft domes' numbers (a sum that changes when any of them does; -1 with them off).
	const bool bSoft = bLumpSoftDomes && !bLumpPlates && bLumpVariety;
	const float SoftKey = bSoft ? 1.f + LumpSkewMinDeg * 1000.f + LumpSkewMaxDeg * 10.f + LumpHeightPerRadius * 0.1f + LumpMaxCm * 1.e-3f + CellCm * 1.e-5f + LumpCapAmpPower * 1.e-2f + LumpCapRadiusPower * 3.e-3f : -1.f;
	if (LumpKeyCells == Cells && LumpKeySpacing == LumpSpacingCells && LumpKeyRadius == LumpRadiusCells && LumpKeyJitter == LumpRadiusJitter
		&& LumpKeySeed == NoiseSeed && LumpKeyVariety == Variety && LumpKeyPlates == PlatesKey && LumpKeySoft == SoftKey && LumpW.Num() == Cells)
	{
		return;
	}
	LumpKeySoft = SoftKey;
	LumpKeyCells = Cells;
	LumpKeySpacing = LumpSpacingCells;
	LumpKeyRadius = LumpRadiusCells;
	LumpKeyJitter = LumpRadiusJitter;
	LumpKeySeed = NoiseSeed;
	LumpKeyVariety = Variety;
	LumpKeyPlates = PlatesKey;
	LumpW.Init(0.f, Cells);
	LumpSiteOf.Init(INDEX_NONE, Cells);
	PlateSites.Reset();
	SiteCellStart.Reset();
	SiteCellList.Reset();
	// LM2c follow-up: the weight the full site set would give (the absent sites' domes too); LM2c off leaves it empty.
	LumpWFull.Reset();
	if (bLumpVariety)
	{
		LumpWFull.Init(0.f, Cells);
	}
	const float Spacing = FMath::Max(1.f, LumpSpacingCells);
	LumpSitesX = FMath::CeilToInt(SizeX / Spacing) + 1;
	LumpSitesY = FMath::CeilToInt(SizeY / Spacing) + 1;
	SiteLumpCm.Init(0.f, LumpSitesX * LumpSitesY);
	SiteClodS.Init(-1.e9, LumpSitesX * LumpSitesY);
	SitePeak.Init(INDEX_NONE, LumpSitesX * LumpSitesY);
	LumpSitesBuilt = 0;
	LumpSitesAbsent = 0;
	LumpSatellites = 0;
	LumpClusterT = -2.f;
	if (bLumpPlates)
	{
		// LM4 item 2, crust plates. The sites as LM2c lays them (jittered over their whole grid cell with the variety on,
		// LM2c's cluster noise leaving LumpAbsentShare of them out in patches, LM2c's skewed amplitude), and each owns its
		// Voronoi cell: every field cell goes to its nearest site over the whole set, the absent ones included, so a plate is
		// clipped against its neighbours' and an absent site's cell is a gap. W is the site's amplitude, flat over its cell
		// (LumpWFull the same for every site): the deposit lands flat and ReshapePlates tilts each plate it touched.
		const int32 Sites = LumpSitesX * LumpSitesY;
		TArray<float> Noise;
		Noise.SetNumUninitialized(Sites);
		for (int32 Site = 0; Site < Sites; ++Site)
		{
			const FVector2D Centre = (LumpSiteCentreCm(Site) - OriginCm) / CellCm;
			Noise[Site] = LumpClusterNoise(FMath::FloorToInt(Centre.X), FMath::FloorToInt(Centre.Y));
		}
		if (bLumpVariety)
		{
			TArray<float> Sorted = Noise;
			Sorted.Sort();
			const float Share = FMath::Clamp(LumpAbsentShare, 0.f, 0.95f);
			LumpClusterT = Share > 0.f && Sorted.Num() > 0 ? Sorted[FMath::Clamp(FMath::FloorToInt(Share * Sorted.Num()), 0, Sorted.Num() - 1)] : -2.f;
		}
		const float AmpMin = FMath::Max(0.f, LumpAmpMin);
		const float AmpMax = FMath::Max(AmpMin, LumpAmpMax);
		const float TiltMin = FMath::Clamp(PlateTiltMinDeg, 0.f, 80.f);
		const float TiltMax = FMath::Clamp(PlateTiltMaxDeg, TiltMin, 80.f);
		const int32 Seed = NoiseSeed;
		auto U = [Seed](int32 SX, int32 SY, int32 Salt) { return 0.5f * (HashLattice(SX, SY, Seed + Salt) + 1.f); };
		TArray<float> Amp;
		Amp.SetNumUninitialized(Sites);
		PlateSites.SetNum(Sites);
		for (int32 Site = 0; Site < Sites; ++Site)
		{
			const int32 SX = Site % LumpSitesX;
			const int32 SY = Site / LumpSitesX;
			FPlateSite& Plate = PlateSites[Site];
			Plate.bPresent = !bLumpVariety || Noise[Site] >= LumpClusterT;
			++(Plate.bPresent ? LumpSitesBuilt : LumpSitesAbsent);
			const FVector2D Centre = (LumpSiteCentreCm(Site) - OriginCm) / CellCm;
			Plate.CentreCells = FVector2f(static_cast<float>(Centre.X), static_cast<float>(Centre.Y));
			Plate.TiltDeg = TiltMin + (TiltMax - TiltMin) * U(SX, SY, 131);
			Plate.AzimuthRad = 2.f * PI * U(SX, SY, 133);
			Amp[Site] = bLumpVariety ? AmpMin + (AmpMax - AmpMin) * FMath::Square(U(SX, SY, 81)) : 1.f;
		}
		// The nearest site: with the jitter over the whole grid cell a site two grid cells away can be nearer than the
		// cell's own, so the 5 x 5 block of site cells round the field cell is searched.
		TArray<int32> Owner;
		Owner.SetNumUninitialized(Cells);
		TArray<int32> Count;
		Count.Init(0, Sites);
		for (int32 Y = 0; Y < SizeY; ++Y)
		{
			for (int32 X = 0; X < SizeX; ++X)
			{
				const float PX = X + 0.5f;
				const float PY = Y + 0.5f;
				const int32 GX = FMath::FloorToInt(PX / Spacing);
				const int32 GY = FMath::FloorToInt(PY / Spacing);
				int32 Best = INDEX_NONE;
				float BestDSq = TNumericLimits<float>::Max();
				for (int32 SY = FMath::Max(0, GY - 2); SY <= FMath::Min(LumpSitesY - 1, GY + 2); ++SY)
				{
					for (int32 SX = FMath::Max(0, GX - 2); SX <= FMath::Min(LumpSitesX - 1, GX + 2); ++SX)
					{
						const FVector2f& C = PlateSites[SY * LumpSitesX + SX].CentreCells;
						const float DSq = FMath::Square(PX - C.X) + FMath::Square(PY - C.Y);
						if (DSq < BestDSq)
						{
							BestDSq = DSq;
							Best = SY * LumpSitesX + SX;
						}
					}
				}
				const int32 Index = Y * SizeX + X;
				Owner[Index] = Best;
				if (Best == INDEX_NONE)
				{
					continue;
				}
				++Count[Best];
				if (LumpWFull.IsValidIndex(Index))
				{
					LumpWFull[Index] = Amp[Best];
				}
				if (PlateSites[Best].bPresent)
				{
					LumpW[Index] = Amp[Best];
					LumpSiteOf[Index] = Best;
				}
			}
		}
		SiteCellStart.SetNumUninitialized(Sites + 1);
		SiteCellStart[0] = 0;
		for (int32 Site = 0; Site < Sites; ++Site)
		{
			SiteCellStart[Site + 1] = SiteCellStart[Site] + Count[Site];
		}
		SiteCellList.SetNumUninitialized(SiteCellStart[Sites]);
		TArray<int32> Fill = SiteCellStart;
		for (int32 Index = 0; Index < Cells; ++Index)
		{
			if (Owner[Index] != INDEX_NONE)
			{
				SiteCellList[Fill[Owner[Index]]++] = Index;
			}
		}
	}
	else if (bLumpVariety)
	{
		// LM2c: the cluster noise at every site's centre; the LumpAbsentShare quantile of it is the threshold below which
		// a site is left out (the noise is smooth, so the absent sites come in patches and the present ones bunch).
		TArray<float> Noise;
		Noise.Reserve(LumpSitesX * LumpSitesY);
		for (int32 Site = 0; Site < LumpSitesX * LumpSitesY; ++Site)
		{
			const FVector2D Centre = (LumpSiteCentreCm(Site) - OriginCm) / CellCm;
			Noise.Add(LumpClusterNoise(FMath::FloorToInt(Centre.X), FMath::FloorToInt(Centre.Y)));
		}
		TArray<float> Sorted = Noise;
		Sorted.Sort();
		const float Share = FMath::Clamp(LumpAbsentShare, 0.f, 0.95f);
		LumpClusterT = Share > 0.f && Sorted.Num() > 0 ? Sorted[FMath::Clamp(FMath::FloorToInt(Share * Sorted.Num()), 0, Sorted.Num() - 1)] : -2.f;
		const float AmpMin = FMath::Max(0.f, LumpAmpMin);
		const float AmpMax = FMath::Max(AmpMin, LumpAmpMax);
		const float Jitter = FMath::Clamp(LumpVarietyRadiusJitter, 0.f, 0.9f);
		const float AspectMax = FMath::Max(1.f, LumpAspectMax);
		const int32 Seed = NoiseSeed;
		auto U = [Seed](int32 SX, int32 SY, int32 Salt) { return 0.5f * (HashLattice(SX, SY, Seed + Salt) + 1.f); };
		// LM4b item 2: the soft domes' skew (a lean toward a hashed azimuth) and height cap per site, kept for the re-shape.
		const float SkewMin = FMath::Clamp(LumpSkewMinDeg, 0.f, 45.f);
		const float SkewMax = FMath::Clamp(LumpSkewMaxDeg, SkewMin, 45.f);
		if (bSoft)
		{
			PlateSites.SetNum(LumpSitesX * LumpSitesY);
		}
		for (int32 SY = 0; SY < LumpSitesY; ++SY)
		{
			for (int32 SX = 0; SX < LumpSitesX; ++SX)
			{
				const int32 Site = SY * LumpSitesX + SX;
				// LM2c follow-up: an absent site still draws its dome into the full weight (LumpWFull), only not into W.
				const bool bPresent = Noise[Site] >= LumpClusterT;
				++(bPresent ? LumpSitesBuilt : LumpSitesAbsent);
				const FVector2D Centre = (LumpSiteCentreCm(Site) - OriginCm) / CellCm;   // in cells
				const float Amp = AmpMin + (AmpMax - AmpMin) * FMath::Square(U(SX, SY, 81));   // u^2: mostly small, a few big
				const float Radius = LumpRadiusCells * (1.f + Jitter * HashLattice(SX, SY, NoiseSeed + 67));
				const float Aspect = 1.f + (AspectMax - 1.f) * U(SX, SY, 83);
				const float Angle = PI * U(SX, SY, 85);
				float SkewTan = 0.f, SkewAz = 0.f, CapCm = 1.f;
				if (bSoft)
				{
					FPlateSite& Dome = PlateSites[Site];
					Dome.CentreCells = FVector2f(static_cast<float>(Centre.X), static_cast<float>(Centre.Y));
					Dome.bPresent = bPresent;
					Dome.TiltDeg = SkewMin + (SkewMax - SkewMin) * U(SX, SY, 131);
					Dome.AzimuthRad = 2.f * PI * U(SX, SY, 133);
					Dome.RadiusCm = FMath::Max(1.f, Radius) * CellCm;   // the dome's semi-axes are at least a cell (AddLumpDome)
					// The cap: a height per radius (a small dome stays low), times the site's amplitude over LM2c's mean amplitude
					// (min + (max - min) / 3, the u^2 law's mean) to LumpCapAmpPower, so the amplitude spread survives the cap.
					const float AmpMean = AmpMin + (AmpMax - AmpMin) / 3.f;
					const float AmpScale = LumpCapAmpPower > 0.f && AmpMean > 0.f ? FMath::Pow(Amp / AmpMean, LumpCapAmpPower) : 1.f;
					// And by (its radius / the mean radius)^LumpCapRadiusPower: a wide dome may stand taller at the same slope.
					const float RadiusMean = FMath::Max(1.f, LumpRadiusCells) * CellCm;
					const float RadiusScale = LumpCapRadiusPower > 0.f ? FMath::Pow(Dome.RadiusCm / RadiusMean, LumpCapRadiusPower) : 1.f;
					Dome.CapCm = LumpHeightPerRadius > 0.f ? FMath::Min(LumpMaxCm, LumpHeightPerRadius * Dome.RadiusCm * AmpScale * RadiusScale) : LumpMaxCm;
					SkewTan = FMath::Tan(FMath::DegreesToRadians(Dome.TiltDeg));
					SkewAz = Dome.AzimuthRad;
					CapCm = FMath::Max(0.1f, Dome.CapCm);
				}
				AddLumpDome(Centre, Radius, Aspect, Angle, Amp, Site, bPresent, SkewTan, SkewAz, CapCm);
				if (U(SX, SY, 87) < LumpSatelliteChance)
				{
					// A satellite 0.6-0.9 of the radius away: a lumpy pair, not a single bead. Smaller and lower than its
					// parent, so its top stands clear of the parent's flank.
					LumpSatellites += bPresent ? 1 : 0;
					const float Away = (0.6f + 0.3f * U(SX, SY, 89)) * Radius;
					const float Heading = 2.f * PI * U(SX, SY, 91);
					const FVector2D SatCentre = Centre + Away * FVector2D(FMath::Cos(Heading), FMath::Sin(Heading));
					AddLumpDome(SatCentre, Radius * (0.5f + 0.3f * U(SX, SY, 93)), 1.f + 0.5f * U(SX, SY, 95), PI * U(SX, SY, 97),
						Amp * (0.55f + 0.35f * U(SX, SY, 99)), Site, bPresent, SkewTan, SkewAz, CapCm);
				}
			}
		}
	}
	if (bSoft)
	{
		// LM4b: each present site's cells (the ones its dome owns, LumpSiteOf), for the re-shape.
		const int32 Sites = LumpSitesX * LumpSitesY;
		TArray<int32> Count;
		Count.Init(0, Sites);
		for (int32 Index = 0; Index < Cells; ++Index)
		{
			if (LumpSiteOf[Index] != INDEX_NONE)
			{
				++Count[LumpSiteOf[Index]];
			}
		}
		SiteCellStart.SetNumUninitialized(Sites + 1);
		SiteCellStart[0] = 0;
		for (int32 Site = 0; Site < Sites; ++Site)
		{
			SiteCellStart[Site + 1] = SiteCellStart[Site] + Count[Site];
		}
		SiteCellList.SetNumUninitialized(SiteCellStart[Sites]);
		TArray<int32> Fill = SiteCellStart;
		for (int32 Index = 0; Index < Cells; ++Index)
		{
			if (LumpSiteOf[Index] != INDEX_NONE)
			{
				SiteCellList[Fill[LumpSiteOf[Index]]++] = Index;
			}
		}
	}
	else if (!bLumpPlates && !bLumpVariety)
	{
		// LM2a: one smooth dome per site, (1 - (d/r)^2)^2, the site jittered +-0.35 of the spacing and its radius
		// +-LumpRadiusJitter from hashes of the site and the seed; a cell under two domes takes the higher (domes do not add).
		for (int32 SY = 0; SY < LumpSitesY; ++SY)
		{
			for (int32 SX = 0; SX < LumpSitesX; ++SX)
			{
				const int32 Site = SY * LumpSitesX + SX;
				++LumpSitesBuilt;
				const FVector2D Centre = (LumpSiteCentreCm(Site) - OriginCm) / CellCm;   // in cells
				const float Radius = FMath::Max(0.5f, LumpRadiusCells * (1.f + FMath::Clamp(LumpRadiusJitter, 0.f, 0.9f) * HashLattice(SX, SY, NoiseSeed + 67)));
				const int32 X0 = FMath::Max(0, FMath::FloorToInt(Centre.X - Radius - 0.5f));
				const int32 X1 = FMath::Min(SizeX - 1, FMath::CeilToInt(Centre.X + Radius - 0.5f));
				const int32 Y0 = FMath::Max(0, FMath::FloorToInt(Centre.Y - Radius - 0.5f));
				const int32 Y1 = FMath::Min(SizeY - 1, FMath::CeilToInt(Centre.Y + Radius - 0.5f));
				for (int32 Y = Y0; Y <= Y1; ++Y)
				{
					for (int32 X = X0; X <= X1; ++X)
					{
						const float DSq = static_cast<float>(FVector2D::DistSquared(FVector2D(X + 0.5f, Y + 0.5f), FVector2D(Centre.X, Centre.Y))) / (Radius * Radius);
						if (DSq >= 1.f)
						{
							continue;
						}
						const float W = (1.f - DSq) * (1.f - DSq);
						const int32 Index = Y * SizeX + X;
						if (W > LumpW[Index])
						{
							LumpW[Index] = W;
							LumpSiteOf[Index] = Site;
						}
					}
				}
			}
		}
	}
	for (int32 Index = 0; Index < Cells; ++Index)
	{
		const int32 Site = LumpSiteOf[Index];
		if (Site != INDEX_NONE && (SitePeak[Site] == INDEX_NONE || LumpW[Index] > LumpW[SitePeak[Site]]))
		{
			SitePeak[Site] = Index;
		}
	}
}

void FGTMudField::AddLumpDome(const FVector2D& CentreCells, float RadiusCells, float Aspect, float AngleRad, float Amplitude, int32 Site, bool bPresent,
	float SkewTan, float SkewAzimuthRad, float SkewRefCm)
{
	// An ellipse of the same area as the circle of RadiusCells: semi-axes R sqrt(A) and R / sqrt(A), each at least one
	// cell: a thinner dome is a one-cell spike on the 12.5 cm grid (at 0.6 of a cell the narrow stroke's detail kept read
	// 0.881 and SoftShoulders' cross-step 25.5 cm, both out of their ranges). (1 - d^2)^2 in the ellipse's own metric.
	const float Root = FMath::Sqrt(FMath::Max(1.f, Aspect));
	const float Major = FMath::Max(1.f, RadiusCells * Root);
	const float Minor = FMath::Max(1.f, RadiusCells / Root);
	const float C = FMath::Cos(AngleRad);
	const float S = FMath::Sin(AngleRad);
	const int32 X0 = FMath::Max(0, FMath::FloorToInt(static_cast<float>(CentreCells.X) - Major - 0.5f));
	const int32 X1 = FMath::Min(SizeX - 1, FMath::CeilToInt(static_cast<float>(CentreCells.X) + Major - 0.5f));
	const int32 Y0 = FMath::Max(0, FMath::FloorToInt(static_cast<float>(CentreCells.Y) - Major - 0.5f));
	const int32 Y1 = FMath::Min(SizeY - 1, FMath::CeilToInt(static_cast<float>(CentreCells.Y) + Major - 0.5f));
	for (int32 Y = Y0; Y <= Y1; ++Y)
	{
		for (int32 X = X0; X <= X1; ++X)
		{
			const float DX = X + 0.5f - static_cast<float>(CentreCells.X);
			const float DY = Y + 0.5f - static_cast<float>(CentreCells.Y);
			const float A = (DX * C + DY * S) / Major;
			const float B = (-DX * S + DY * C) / Minor;
			const float DSq = A * A + B * B;
			if (DSq >= 1.f)
			{
				continue;
			}
			float W = Amplitude * (1.f - DSq) * (1.f - DSq);
			if (SkewTan > 0.f)
			{
				// LM4b item 2: the lean - 1 + tan(skew) x the offset along the azimuth (cm) / the dome's height, so at its full
				// height the dome's top tilts by the skew; never below 0 (the far rim of a long oval).
				const float Along = (DX * FMath::Cos(SkewAzimuthRad) + DY * FMath::Sin(SkewAzimuthRad)) * CellCm;
				W *= FMath::Max(0.f, 1.f + SkewTan * Along / FMath::Max(0.1f, SkewRefCm));
			}
			const int32 Index = Y * SizeX + X;
			if (LumpWFull.IsValidIndex(Index))
			{
				LumpWFull[Index] = FMath::Max(LumpWFull[Index], W);
			}
			if (bPresent && W > LumpW[Index])
			{
				LumpW[Index] = W;
				LumpSiteOf[Index] = Site;
			}
		}
	}
}

double FGTMudField::ReshapePlates(TArrayView<const int32> Sites, int32& InOutX0, int32& InOutY0, int32& InOutX1, int32& InOutY1)
{
	// LM4 item 2: each plate is a flat plane tilted TiltDeg toward its azimuth over its cell's standing cells (not cut into a
	// trench: HeightCm at least -1; not a lip cell whose plate fell in), clamped to 0..LumpMaxCm, its volume kept: the plane's
	// height T at the site is solved (bisection; the clamped sum is monotone in T) so the plate holds what it held. A plate
	// fuller than its cells at the cap keeps the cap and the excess is returned (cm^3) for the band.
	if (!bLumpPlates || PlateSites.Num() == 0 || SiteCellStart.Num() != PlateSites.Num() + 1)
	{
		return 0.0;
	}
	const float Cap = FMath::Max(0.f, LumpMaxCm);
	const double CellArea = static_cast<double>(CellCm) * CellCm;
	const bool bMarks = SnowMark.Num() == SizeX * SizeY;
	double Excess = 0.0;
	TArray<int32, TInlineAllocator<128>> Plate;
	TArray<float, TInlineAllocator<128>> Off;
	for (const int32 Site : Sites)
	{
		if (!PlateSites.IsValidIndex(Site) || !PlateSites[Site].bPresent)
		{
			continue;
		}
		const FPlateSite& P = PlateSites[Site];
		const float Slope = FMath::Tan(FMath::DegreesToRadians(P.TiltDeg)) * CellCm;   // cm of height per cell along the azimuth
		const float DX = FMath::Cos(P.AzimuthRad);
		const float DY = FMath::Sin(P.AzimuthRad);
		Plate.Reset();
		Off.Reset();
		double Volume = 0.0;
		float OffMin = TNumericLimits<float>::Max();
		float OffMax = -TNumericLimits<float>::Max();
		for (int32 K = SiteCellStart[Site]; K < SiteCellStart[Site + 1]; ++K)
		{
			const int32 Index = SiteCellList[K];
			if (HeightCm[Index] < -1.f || (bMarks && (SnowMark[Index] & SnowMarkDropped)))
			{
				continue;
			}
			const float RX = (Index % SizeX) + 0.5f - P.CentreCells.X;
			const float RY = (Index / SizeX) + 0.5f - P.CentreCells.Y;
			const float O = Slope * (RX * DX + RY * DY);
			Plate.Add(Index);
			Off.Add(O);
			Volume += LumpCm[Index];
			OffMin = FMath::Min(OffMin, O);
			OffMax = FMath::Max(OffMax, O);
		}
		if (Plate.Num() == 0 || Volume <= 0.0)
		{
			continue;
		}
		const int32 N = Plate.Num();
		auto Held = [&](double T)
		{
			double Sum = 0.0;
			for (int32 K = 0; K < N; ++K)
			{
				Sum += FMath::Clamp(T + Off[K], 0.0, static_cast<double>(Cap));
			}
			return Sum;
		};
		double T = 0.0;
		if (Volume >= N * static_cast<double>(Cap))
		{
			T = Cap - OffMin;   // every cell at the cap
			Excess += (Volume - N * static_cast<double>(Cap)) * CellArea;
		}
		else
		{
			double Lo = -OffMax;
			double Hi = Cap - OffMin;
			for (int32 Iter = 0; Iter < 40; ++Iter)
			{
				const double Mid = 0.5 * (Lo + Hi);
				(Held(Mid) < Volume ? Lo : Hi) = Mid;
			}
			T = 0.5 * (Lo + Hi);
		}
		// Write the plane, then put the bisection's last few millionths of a cm back on the cells strictly inside the clamp
		// (or into the excess), so the plate's volume is exact.
		double Written = 0.0;
		int32 Free = 0;
		for (int32 K = 0; K < N; ++K)
		{
			const int32 Index = Plate[K];
			const float Before = LumpCm[Index];
			const float Value = static_cast<float>(FMath::Clamp(T + Off[K], 0.0, static_cast<double>(Cap)));
			LumpCm[Index] = Value;
			Written += Value;
			Free += (Value > 0.f && Value < Cap) ? 1 : 0;
			if (FMath::Abs(Value - Before) > FreshMinCm && Fresh.IsValidIndex(Index))
			{
				Fresh[Index] = 1.f;
			}
			const int32 X = Index % SizeX;
			const int32 Y = Index / SizeX;
			InOutX0 = FMath::Min(InOutX0, X);
			InOutY0 = FMath::Min(InOutY0, Y);
			InOutX1 = FMath::Max(InOutX1, X);
			InOutY1 = FMath::Max(InOutY1, Y);
		}
		const double Target = FMath::Min(Volume, N * static_cast<double>(Cap));
		const double Residual = Target - Written;
		if (Free > 0)
		{
			const float Each = static_cast<float>(Residual / Free);
			for (int32 K = 0; K < N; ++K)
			{
				float& Value = LumpCm[Plate[K]];
				if (Value > 0.f && Value < Cap)
				{
					Value += Each;
				}
			}
		}
		else
		{
			Excess += Residual * CellArea;
		}
	}
	return Excess;
}

double FGTMudField::ReshapeDomes(TArrayView<const int32> Sites, int32& InOutX0, int32& InOutY0, int32& InOutX1, int32& InOutY1)
{
	// LM4b item 2: each dome is T x its own kernel (LumpW: the site's amplitude, the dome, the lean) over its standing cells
	// (HeightCm at least -1, not a lip cell whose lump fell in; a feathered cell keeps 1 - its share of the kernel), with T the
	// site's volume over the kernel's sum, so the volume is exact; but the peak stays at most the site's height cap (its
	// radius x LumpHeightPerRadius, LumpMaxCm at most): a fuller dome keeps the capped kernel and the excess is returned
	// (cm^3) for the band. So a dome stays a dome at any fill - never a capped column.
	if (!bLumpSoftDomes || PlateSites.Num() == 0 || SiteCellStart.Num() != PlateSites.Num() + 1)
	{
		return 0.0;
	}
	const double CellArea = static_cast<double>(CellCm) * CellCm;
	const bool bMarks = SnowMark.Num() == SizeX * SizeY;
	const bool bShares = LipDropShare.Num() == SizeX * SizeY;
	double Excess = 0.0;
	TArray<int32, TInlineAllocator<64>> Dome;
	TArray<float, TInlineAllocator<64>> Kernel;
	for (const int32 Site : Sites)
	{
		if (!PlateSites.IsValidIndex(Site) || !PlateSites[Site].bPresent)
		{
			continue;
		}
		Dome.Reset();
		Kernel.Reset();
		double Volume = 0.0;
		double KernelSum = 0.0;
		float KernelMax = 0.f;
		for (int32 K = SiteCellStart[Site]; K < SiteCellStart[Site + 1]; ++K)
		{
			const int32 Index = SiteCellList[K];
			if (HeightCm[Index] < -1.f || (bMarks && (SnowMark[Index] & SnowMarkDropped)))
			{
				continue;
			}
			const float Keep = bShares ? 1.f - LipDropShare[Index] / 255.f : 1.f;
			const float Weight = LumpW[Index] * Keep;
			Dome.Add(Index);
			Kernel.Add(Weight);
			Volume += LumpCm[Index];
			KernelSum += Weight;
			KernelMax = FMath::Max(KernelMax, Weight);
		}
		if (Dome.Num() == 0 || Volume <= 0.0)
		{
			continue;
		}
		if (KernelSum <= 1.e-9 || KernelMax <= 0.f)
		{
			// Nothing of the kernel stands (every cell feathered out): the lump goes to the band.
			for (const int32 Index : Dome)
			{
				LumpCm[Index] = 0.f;
			}
			Excess += Volume * CellArea;
			continue;
		}
		const double Cap = FMath::Max(0.f, PlateSites[Site].CapCm);
		double T = Volume / KernelSum;
		if (T * KernelMax > Cap)
		{
			T = Cap / KernelMax;
			Excess += (Volume - T * KernelSum) * CellArea;
		}
		for (int32 K = 0; K < Dome.Num(); ++K)
		{
			const int32 Index = Dome[K];
			const float Before = LumpCm[Index];
			const float Value = static_cast<float>(T * Kernel[K]);
			LumpCm[Index] = Value;
			if (FMath::Abs(Value - Before) > FreshMinCm && Fresh.IsValidIndex(Index))
			{
				Fresh[Index] = 1.f;
			}
			const int32 X = Index % SizeX;
			const int32 Y = Index / SizeX;
			InOutX0 = FMath::Min(InOutX0, X);
			InOutY0 = FMath::Min(InOutY0, Y);
			InOutX1 = FMath::Max(InOutX1, X);
			InOutY1 = FMath::Max(InOutY1, Y);
		}
	}
	return Excess;
}

float FGTMudField::LumpClusterNoise(int32 X, int32 Y) const
{
	return CellNoise(X, Y, FMath::Max(1.f, LumpClusterCm / CellCm), 79);
}

float FGTMudField::LumpClusterWeight(int32 X, int32 Y) const
{
	if (!bLumpVariety || LumpClusterT < -1.5f)
	{
		return 1.f;
	}
	return FMath::Clamp((LumpClusterNoise(X, Y) - LumpClusterT) / 0.5f, 0.f, 1.f);
}

float FGTMudField::LumpWeightAt(int32 Index)
{
	EnsureLumpWeights();
	return LumpW.IsValidIndex(Index) ? LumpW[Index] : 0.f;
}

int32 FGTMudField::LumpSiteAt(int32 Index)
{
	EnsureLumpWeights();
	return LumpSiteOf.IsValidIndex(Index) ? LumpSiteOf[Index] : INDEX_NONE;
}

FVector2D FGTMudField::LumpSiteCentreCm(int32 Site) const
{
	if (LumpSitesX <= 0 || Site < 0)
	{
		return OriginCm;
	}
	const int32 SX = Site % LumpSitesX;
	const int32 SY = Site / LumpSitesX;
	const float Spacing = FMath::Max(1.f, LumpSpacingCells);
	// LM2a: +-0.35 of the spacing; LM2c: over the whole grid cell (+-0.5).
	const float Reach = bLumpVariety ? 0.5f : 0.35f;
	const float JX = Reach * HashLattice(SX, SY, NoiseSeed + 61);
	const float JY = Reach * HashLattice(SX, SY, NoiseSeed + 63);
	return OriginCm + FVector2D((SX + 0.5f + JX) * Spacing, (SY + 0.5f + JY) * Spacing) * CellCm;
}

void FGTMudField::QueueClod(const FClodSpawn& Spawn)
{
	if (PendingClods.Num() >= FMath::Max(1, MaxPendingClods))
	{
		PendingClods.RemoveAt(0);
	}
	PendingClods.Add(Spawn);
}

double FGTMudField::DepositLump(const FVector2D& XYCm, double VolumeCm3, float DomeRadiusCm)
{
	if (!IsValid() || VolumeCm3 <= 0.0 || !Contains(XYCm))
	{
		return 0.0;
	}
	// A dome (1 - (d/R)^2)^2 over the cell centres within R; a blob smaller than a cell lands in the cell it hit.
	const FVector2D Local = (XYCm - OriginCm) / CellCm;
	const float R = FMath::Max(0.f, DomeRadiusCm) / CellCm;   // cells
	const int32 X0 = FMath::Max(0, FMath::FloorToInt(Local.X - R - 0.5f));
	const int32 X1 = FMath::Min(SizeX - 1, FMath::CeilToInt(Local.X + R - 0.5f));
	const int32 Y0 = FMath::Max(0, FMath::FloorToInt(Local.Y - R - 0.5f));
	const int32 Y1 = FMath::Min(SizeY - 1, FMath::CeilToInt(Local.Y + R - 0.5f));
	TArray<TPair<int32, double>, TInlineAllocator<64>> Cells;
	double WeightSum = 0.0;
	if (R > 0.f)
	{
		for (int32 Y = Y0; Y <= Y1; ++Y)
		{
			for (int32 X = X0; X <= X1; ++X)
			{
				const double DSq = FVector2D::DistSquared(FVector2D(X + 0.5, Y + 0.5), Local) / (static_cast<double>(R) * R);
				if (DSq < 1.0)
				{
					const double W = (1.0 - DSq) * (1.0 - DSq);
					Cells.Emplace(Y * SizeX + X, W);
					WeightSum += W;
				}
			}
		}
	}
	if (WeightSum <= 0.0)
	{
		Cells.Reset();
		Cells.Emplace(CellIndexAt(XYCm), 1.0);
		WeightSum = 1.0;
	}
	const double CellArea = static_cast<double>(CellCm) * CellCm;
	int32 CX0 = SizeX, CY0 = SizeY, CX1 = -1, CY1 = -1;
	for (const TPair<int32, double>& Cell : Cells)
	{
		const float Add = static_cast<float>(VolumeCm3 * Cell.Value / (WeightSum * CellArea));
		const float SurfaceBefore = SurfaceCm(Cell.Key);
		const float Over = AddLump(Cell.Key, Add);
		Book.LumpOverflowCm3 += Over * CellArea;
		Book.LumpLandedCm3 += (Add - Over) * CellArea;
		Fresh[Cell.Key] = 1.f;
		ChurnWater(Cell.Key, FMath::Min(SurfaceBefore, SurfaceCm(Cell.Key)));   // MR3: a blob landing in a rut pool churns it
		const int32 X = Cell.Key % SizeX;
		const int32 Y = Cell.Key / SizeX;
		CX0 = FMath::Min(CX0, X);
		CY0 = FMath::Min(CY0, Y);
		CX1 = FMath::Max(CX1, X);
		CY1 = FMath::Max(CY1, Y);
	}
	Book.ThrowLandedCm3 += VolumeCm3;
	++Book.ThrowDeposits;
	if (CX1 >= CX0)
	{
		WakeTiles(CX0, CY0, CX1, CY1);
		MarkDirty(CX0, CY0, CX1 + 1, CY1 + 1);
	}
	return VolumeCm3;
}

FBox2D FGTMudField::Bounds() const
{
	return FBox2D(OriginCm, OriginCm + FVector2D(static_cast<double>(SizeX), static_cast<double>(SizeY)) * CellCm);
}

bool FGTMudField::Contains(const FVector2D& XYCm) const
{
	return IsValid() && Bounds().IsInside(XYCm);
}

float FGTMudField::HeightAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return 0.f;
	}
	// LM2a: the surface, HeightCm + LumpCm, so the render, the water and the traction read the same thing.
	return BilinearSample(XYCm - OriginCm, CellCm, SizeX, SizeY, [this](int32 Index) { return HeightCm[Index] + LumpCm[Index]; });
}

float FGTMudField::LumpAt(const FVector2D& XYCm) const
{
	if (!IsValid() || LumpCm.Num() != HeightCm.Num())
	{
		return 0.f;
	}
	return BilinearSample(XYCm - OriginCm, CellCm, SizeX, SizeY, [this](int32 Index) { return LumpCm[Index]; });
}

FVector2f FGTMudField::OffsetAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return FVector2f::ZeroVector;
	}
	return BilinearSample(XYCm - OriginCm, CellCm, SizeX, SizeY, [this](int32 Index) { return OffsetCm[Index]; });
}

float FGTMudField::TracksAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return 0.f;
	}
	return BilinearSample(XYCm - OriginCm, CellCm, SizeX, SizeY, [this](int32 Index) { return Tracks[Index] / 255.f; });
}

FVector2D FGTMudField::GradientAt(const FVector2D& XYCm) const
{
	const FVector2D DX(CellCm, 0.f);
	const FVector2D DY(0.f, CellCm);
	return FVector2D((HeightAt(XYCm + DX) - HeightAt(XYCm - DX)) / (2.f * CellCm), (HeightAt(XYCm + DY) - HeightAt(XYCm - DY)) / (2.f * CellCm));
}

int32 FGTMudField::CellIndexAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return INDEX_NONE;
	}
	const FVector2D Local = XYCm - OriginCm;
	const int32 X = FMath::Clamp(FMath::FloorToInt(Local.X / CellCm), 0, SizeX - 1);
	const int32 Y = FMath::Clamp(FMath::FloorToInt(Local.Y / CellCm), 0, SizeY - 1);
	return Y * SizeX + X;
}

float FGTMudField::CellNoise(int32 X, int32 Y, float WavelengthCells, int32 Salt) const
{
	const float Wavelength = FMath::Max(1.f, WavelengthCells);
	const float GX = (X + NoiseCellX) / Wavelength;   // Benmore B2: NoiseCellX/Y 0 off a zone tile
	const float GY = (Y + NoiseCellY) / Wavelength;
	const int32 X0 = FMath::FloorToInt(GX);
	const int32 Y0 = FMath::FloorToInt(GY);
	const float TX = GX - X0;
	const float TY = GY - Y0;
	const float FX = TX * TX * (3.f - 2.f * TX);   // smoothstep, so the clumps have no lattice corners in them
	const float FY = TY * TY * (3.f - 2.f * TY);
	const int32 Seed = NoiseSeed + Salt;
	const float N00 = HashLattice(X0, Y0, Seed);
	const float N10 = HashLattice(X0 + 1, Y0, Seed);
	const float N01 = HashLattice(X0, Y0 + 1, Seed);
	const float N11 = HashLattice(X0 + 1, Y0 + 1, Seed);
	return FMath::Lerp(FMath::Lerp(N00, N10, FX), FMath::Lerp(N01, N11, FX), FY);
}

const float* FGTMudField::NoiseCells(int32 Slot, float WavelengthCells, int32 Salt)
{
	// LM4f item 4: CellNoise is a function of the cell, the wavelength, the salt and the seed alone, so a slot built once holds
	// exactly the values the stamps computed per cell before; the key is every input (and the size), compared exactly.
	if (!IsValid() || Slot < 0 || Slot >= NoiseSlotCount)
	{
		return nullptr;
	}
	FNoiseCells& Cache = NoiseCache[Slot];
	if (Cache.WavelengthCells != WavelengthCells || Cache.Salt != Salt || Cache.Seed != NoiseSeed || Cache.SX != SizeX || Cache.SY != SizeY
		|| Cache.Values.Num() != SizeX * SizeY)
	{
		Cache.WavelengthCells = WavelengthCells;
		Cache.Salt = Salt;
		Cache.Seed = NoiseSeed;
		Cache.SX = SizeX;
		Cache.SY = SizeY;
		Cache.Values.SetNumUninitialized(SizeX * SizeY);
		float* Out = Cache.Values.GetData();
		ParallelFor(TEXT("GTMudNoiseCells"), SizeY, 16, [this, Out, WavelengthCells, Salt](int32 Y)
		{
			for (int32 X = 0; X < SizeX; ++X)
			{
				Out[Y * SizeX + X] = CellNoise(X, Y, WavelengthCells, Salt);
			}
		});
	}
	return Cache.Values.GetData();
}

void FGTMudField::PrepareStampNoise()
{
	// LM4f item 4: every slot the numbers in force read, with the very arguments the stamps pass (so their keys match).
	if (!IsValid())
	{
		return;
	}
	NoiseCells(NoiseWave, FMath::Max(1.f, RidgeWaveCm / CellCm), 11);
	NoiseCells(NoiseWaveLong, FMath::Max(1.f, RidgeWaveLongCm / CellCm), 13);
	NoiseCells(NoiseSide, FMath::Max(1.f, 100.f / CellCm), 17);
	if (FMath::Clamp(RidgeSlump, 0.f, 1.f) > 0.f)
	{
		NoiseCells(NoiseSlump, FMath::Max(1.f, 100.f / CellCm), 23);
	}
	NoiseCells(NoisePocket, PocketNoiseCells, 53);
	NoiseCells(NoiseFloor, FloorNoiseCells, 31);
	NoiseCells(NoiseClump, RidgeNoiseCells, 0);
	if (ClodChance > 0.f)
	{
		NoiseCells(NoiseClod, 1.f, 41);
		NoiseCells(NoiseClodSize, 1.f, 43);
	}
	NoiseCells(NoiseTracksEdge, TracksEdgeCells, 7);
	if (bLumpVariety)
	{
		NoiseCells(NoiseCluster, FMath::Max(1.f, LumpClusterCm / CellCm), 79);
	}
}

float FGTMudField::TreadHeadingAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return -1.f;
	}
	const FVector2D Local = XYCm - OriginCm;
	const int32 X = FMath::Clamp(FMath::FloorToInt(Local.X / CellCm), 0, SizeX - 1);
	const int32 Y = FMath::Clamp(FMath::FloorToInt(Local.Y / CellCm), 0, SizeY - 1);
	const int32 Index = Y * SizeX + X;
	return PhaseTurns[Index] < 0.f ? -1.f : HeadingTurns[Index];
}

float FGTMudField::TreadPhaseAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return -1.f;
	}
	const FVector2D Local = XYCm - OriginCm;
	const int32 X = FMath::Clamp(FMath::FloorToInt(Local.X / CellCm), 0, SizeX - 1);
	const int32 Y = FMath::Clamp(FMath::FloorToInt(Local.Y / CellCm), 0, SizeY - 1);
	const int32 Index = Y * SizeX + X;
	if (PhaseTurns[Index] < 0.f)
	{
		return -1.f;
	}
	// The cell's phase is its centre's; carry it to the point along the heading the stamp was made with, as the material does.
	const float Angle = HeadingTurns[Index] * 2.f * PI;
	const FVector2D Dir(FMath::Cos(Angle), FMath::Sin(Angle));
	const FVector2D Centre((X + 0.5f) * CellCm, (Y + 0.5f) * CellCm);
	const float Along = static_cast<float>(FVector2D::DotProduct(Local - Centre, Dir));
	return Wrap01(PhaseTurns[Index] + Along / FMath::Max(1.f, LugPeriodCm));
}

void FGTMudField::MarkDirty(int32 X0, int32 Y0, int32 X1, int32 Y1)
{
	const FIntRect Rect(FIntPoint(X0, Y0), FIntPoint(X1, Y1));
	if (bDirty)
	{
		Dirty.Union(Rect);
	}
	else
	{
		Dirty = Rect;
		bDirty = true;
	}
	// LM4e cut 2: the same cells, one box per settle tile.
	const int32 CX0 = FMath::Max(0, X0);
	const int32 CY0 = FMath::Max(0, Y0);
	const int32 CX1 = FMath::Min(SizeX, X1);
	const int32 CY1 = FMath::Min(SizeY, Y1);
	if (CX1 <= CX0 || CY1 <= CY0)
	{
		return;
	}
	if (TileDirtyRect.Num() != TilesX * TilesY)
	{
		bDirtyUnsplit = true;   // no tiles yet: the take falls back to the union
		return;
	}
	for (int32 TY = CY0 / TileCells; TY <= (CY1 - 1) / TileCells; ++TY)
	{
		for (int32 TX = CX0 / TileCells; TX <= (CX1 - 1) / TileCells; ++TX)
		{
			const int32 Tile = TY * TilesX + TX;
			const FIntRect Part(FIntPoint(FMath::Max(CX0, TX * TileCells), FMath::Max(CY0, TY * TileCells)),
				FIntPoint(FMath::Min(CX1, (TX + 1) * TileCells), FMath::Min(CY1, (TY + 1) * TileCells)));
			FIntRect& Box = TileDirtyRect[Tile];
			if (Box.Max.X <= Box.Min.X)
			{
				Box = Part;
				DirtyTiles.Add(Tile);
			}
			else
			{
				Box.Union(Part);
			}
		}
	}
}

bool FGTMudField::TakeDirty(FIntRect& OutRect)
{
	for (const int32 Tile : DirtyTiles)
	{
		TileDirtyRect[Tile] = FIntRect();
	}
	DirtyTiles.Reset();
	bDirtyUnsplit = false;
	if (!bDirty)
	{
		return false;
	}
	OutRect = Dirty;
	bDirty = false;
	return OutRect.Width() > 0 && OutRect.Height() > 0;
}

void FGTMudField::EncodeTexels(int32 Index0, int32 Count, FFloat16Color* OutField, FFloat16Color* OutTread, bool bFreshSheen) const
{
	const int32 N = SizeX * SizeY;
	const bool bLumps = LumpCm.Num() == N;
	const bool bPlates = bSnow && LumpsShaped() && bLumps && LumpSiteOf.Num() == N;
	const bool bPhase = PhaseTurns.Num() == N;
	const bool bLug = LugStrength.Num() == N;
	const bool bMarks = SnowMark.Num() == N;
	const bool bFresh = !bSnow && bFreshSheen && Fresh.Num() == N;
	const bool bTurbid = !bSnow && Turbidity.Num() == N;
	for (int32 K = 0; K < Count; ++K)
	{
		const int32 I = Index0 + K;
		const float Surface = HeightCm[I] + (bLumps ? LumpCm[I] : 0.f);
		OutField[K] = FFloat16Color(FLinearColor(Surface * 0.01f, OffsetCm[I].X * 0.01f, OffsetCm[I].Y * 0.01f, Tracks[I] / 255.f));
		if (OutTread)
		{
			// PlateAlpha and TreadAlpha, as their inline definitions.
			const float B = bSnow ? ((bPlates && LumpSiteOf[I] != INDEX_NONE) ? FMath::Clamp(LumpCm[I] / 1.5f, 0.f, 1.f) : 0.f) : (bFresh ? Fresh[I] : 0.f);
			float A = bTurbid ? Turbidity[I] : 0.f;   // MR3: on mud, the churned water
			if (bSnow && bPhase)
			{
				A = PhaseTurns[I] >= 0.f ? (bLug ? LugStrength[I] : 1.f) : ((bMarks && (SnowMark[I] & SnowMarkScraped)) ? -1.f : 0.f);
			}
			OutTread[K] = FFloat16Color(FLinearColor(HeadingTurns[I], FMath::Max(0.f, PhaseTurns[I]), B, A));
		}
	}
}

bool FGTMudField::TakeDirtyRects(TArray<FIntRect>& OutRects, FIntRect& OutUnion)
{
	OutRects.Reset();
	for (const int32 Tile : DirtyTiles)
	{
		OutRects.Add(TileDirtyRect[Tile]);
		TileDirtyRect[Tile] = FIntRect();
	}
	DirtyTiles.Reset();
	if (!bDirty)
	{
		bDirtyUnsplit = false;
		return false;
	}
	OutUnion = Dirty;
	bDirty = false;
	if (bDirtyUnsplit || OutRects.Num() == 0)
	{
		OutRects.Reset();
		OutRects.Add(OutUnion);
	}
	bDirtyUnsplit = false;
	return OutRects.Num() > 0 && OutUnion.Width() > 0 && OutUnion.Height() > 0;
}

float FGTMudField::FreshAt(const FVector2D& XYCm) const
{
	if (!IsValid() || Fresh.Num() != HeightCm.Num())
	{
		return 0.f;
	}
	return BilinearSample(XYCm - OriginCm, CellCm, SizeX, SizeY, [this](int32 Index) { return Fresh[Index]; });
}

float FGTMudField::DetailRatio(TArrayView<const int32> Cells) const
{
	// LM1b: RMS(S - the 3x3 mean of S) / RMS(S) over these cells; the mean over the neighbours inside the grid.
	double Residual = 0.0;
	double Relief = 0.0;
	for (const int32 Index : Cells)
	{
		if (!HeightCm.IsValidIndex(Index))
		{
			continue;
		}
		const int32 X = Index % SizeX;
		const int32 Y = Index / SizeX;
		double Sum = 0.0;
		int32 Count = 0;
		for (int32 NY = FMath::Max(0, Y - 1); NY <= FMath::Min(SizeY - 1, Y + 1); ++NY)
		{
			for (int32 NX = FMath::Max(0, X - 1); NX <= FMath::Min(SizeX - 1, X + 1); ++NX)
			{
				Sum += SurfaceCm(NY * SizeX + NX);   // LM2a: the surface, lumps included
				++Count;
			}
		}
		const double S = SurfaceCm(Index);
		const double Off = S - Sum / FMath::Max(1, Count);
		Residual += Off * Off;
		Relief += S * S;
	}
	return Relief > 0.0 ? static_cast<float>(FMath::Sqrt(Residual / Relief)) : 0.f;
}

// ---- MudRunner MR3, muddy rut water ------------------------------------------------------------------------------------

float FGTMudField::TurbidityAt(const FVector2D& XYCm) const
{
	if (!IsValid() || Turbidity.Num() != HeightCm.Num())
	{
		return 0.f;
	}
	return BilinearSample(XYCm - OriginCm, CellCm, SizeX, SizeY, [this](int32 Index) { return Turbidity[Index]; });
}

int32 FGTMudField::TurbidTileCount() const
{
	int32 Count = 0;
	for (const uint8 Flag : TileTurbid)
	{
		Count += Flag ? 1 : 0;
	}
	return Count;
}

void FGTMudField::SetMuddyWater(bool bOn)
{
	if (bOn == bMuddyWater)
	{
		return;
	}
	bMuddyWater = bOn;
	if (bOn || Turbidity.Num() != SizeX * SizeY || TileTurbid.Num() != TilesX * TilesY)
	{
		return;
	}
	// Off: every turbid tile's cells to 0 (dirty, so the texture's A goes to 0 with them), and the tiles asleep.
	for (int32 Tile = 0; Tile < TileTurbid.Num(); ++Tile)
	{
		if (!TileTurbid[Tile])
		{
			continue;
		}
		TileTurbid[Tile] = 0;
		const int32 X0 = (Tile % TilesX) * TileCells;
		const int32 Y0 = (Tile / TilesX) * TileCells;
		const int32 X1 = FMath::Min(X0 + TileCells, SizeX);
		const int32 Y1 = FMath::Min(Y0 + TileCells, SizeY);
		for (int32 Y = Y0; Y < Y1; ++Y)
		{
			for (int32 X = X0; X < X1; ++X)
			{
				Turbidity[Y * SizeX + X] = 0.f;
			}
		}
		MarkDirty(X0, Y0, X1, Y1);
	}
	TurbidAccumS = 0.0;
}

bool FGTMudField::TurbidEdgeWakes(int32 FromTile, int32 ToTile) const
{
	const int32 FX = FromTile % TilesX, FY = FromTile / TilesX;
	const int32 TX = ToTile % TilesX, TY = ToTile / TilesX;
	const float Wake = FMath::Max(0.f, TurbidSleepBelow);
	// The edge of From that faces To, cell by cell, and the cell across it in To.
	int32 X0 = FX * TileCells, Y0 = FY * TileCells;
	int32 X1 = FMath::Min(X0 + TileCells, SizeX) - 1, Y1 = FMath::Min(Y0 + TileCells, SizeY) - 1;
	int32 DX = 0, DY = 0;
	if (TX < FX) { X1 = X0; DX = -1; }
	else if (TX > FX) { X0 = X1; DX = 1; }
	else if (TY < FY) { Y1 = Y0; DY = -1; }
	else { Y0 = Y1; DY = 1; }
	for (int32 Y = Y0; Y <= Y1; ++Y)
	{
		for (int32 X = X0; X <= X1; ++X)
		{
			const int32 I = Y * SizeX + X;
			const int32 NX = X + DX, NY = Y + DY;
			if (NX < 0 || NY < 0 || NX >= SizeX || NY >= SizeY)
			{
				continue;
			}
			if (Turbidity[I] >= Wake && WaterOverCm(I) > 0.f && WaterOverCm(NY * SizeX + NX) > 0.f)
			{
				return true;
			}
		}
	}
	return false;
}

int32 FGTMudField::SettleTurbidity(float DeltaSeconds)
{
	if (!IsValid() || bSnow || Turbidity.Num() != SizeX * SizeY || TileTurbid.Num() != TilesX * TilesY)
	{
		return 0;
	}
	if (TurbidTileCount() == 0)
	{
		TurbidAccumS = 0.0;   // nothing turbid: the next churn starts its own clock
		return 0;
	}
	// Fixed sub-steps from an accumulator (the half-life does not depend on the frame rate), at most TurbidMaxSteps a call.
	const double Step = FMath::Max(0.01, static_cast<double>(TurbidStepS));
	TurbidAccumS += FMath::Max(0.0, static_cast<double>(DeltaSeconds));
	int32 Steps = 0;
	const int32 MaxSteps = FMath::Max(1, TurbidMaxSteps);
	while (TurbidAccumS >= Step * (1.0 - 1.e-4) && Steps < MaxSteps)
	{
		TurbidAccumS -= Step;
		TurbidStep(static_cast<float>(Step));
		++Steps;
	}
	if (Steps >= MaxSteps)
	{
		TurbidAccumS = FMath::Min(TurbidAccumS, 0.0);
	}
	return Steps;
}

void FGTMudField::TurbidStep(float Dt)
{
	const int32 N = SizeX * SizeY;
	const int32 NumTiles = TilesX * TilesY;
	const float Decay = FMath::Pow(0.5f, Dt / FMath::Max(0.01f, RutSettleS));
	const float K = FMath::Clamp(TurbidMixRate * Dt, 0.f, 0.2f);   // 1 - 4K >= 0.2: each new value a weighted mean of the old
	const float Wake = FMath::Max(0.f, TurbidSleepBelow);
	if (TurbidScratch.Num() != N)
	{
		TurbidScratch.SetNumZeroed(N);
	}
	float* T = Turbidity.GetData();
	float* New = TurbidScratch.GetData();
	auto TileOfCell = [this](int32 X, int32 Y) { return (Y / TileCells) * TilesX + X / TileCells; };
	// 1. The work list: the turbid tiles, then any neighbour a turbid wet edge faces across a wet cell (it joins before the
	//    mix, so the exchange across that edge happens; an edge under Wake carries nothing to a sleeping tile).
	TurbidList.Reset();
	for (int32 Tile = 0; Tile < NumTiles; ++Tile)
	{
		if (TileTurbid[Tile])
		{
			TurbidList.Add(Tile);
		}
	}
	const int32 Listed0 = TurbidList.Num();
	for (int32 L = 0; L < Listed0; ++L)
	{
		const int32 Tile = TurbidList[L];
		const int32 TX = Tile % TilesX, TY = Tile / TilesX;
		const FIntPoint Near[4] = { FIntPoint(TX - 1, TY), FIntPoint(TX + 1, TY), FIntPoint(TX, TY - 1), FIntPoint(TX, TY + 1) };
		for (const FIntPoint& Nb : Near)
		{
			if (Nb.X < 0 || Nb.Y < 0 || Nb.X >= TilesX || Nb.Y >= TilesY)
			{
				continue;
			}
			const int32 Other = Nb.Y * TilesX + Nb.X;
			if (!TileTurbid[Other] && TurbidEdgeWakes(Tile, Other))
			{
				TileTurbid[Other] = 1;
				TurbidList.Add(Other);
			}
		}
	}
	// 2. The mix and the settle, from the old values into the scratch: a wet cell takes K x (a wet listed neighbour - itself)
	//    from each such neighbour (both sides of every pair, so the exchange conserves), then the decay; a dry cell holds none.
	for (const int32 Tile : TurbidList)
	{
		const int32 X0 = (Tile % TilesX) * TileCells;
		const int32 Y0 = (Tile / TilesX) * TileCells;
		const int32 X1 = FMath::Min(X0 + TileCells, SizeX);
		const int32 Y1 = FMath::Min(Y0 + TileCells, SizeY);
		for (int32 Y = Y0; Y < Y1; ++Y)
		{
			for (int32 X = X0; X < X1; ++X)
			{
				const int32 I = Y * SizeX + X;
				if (WaterOverCm(I) <= 0.f)
				{
					New[I] = 0.f;
					continue;
				}
				const float Own = T[I];
				float Sum = 0.f;
				auto Pair = [&](int32 JX, int32 JY)
				{
					const int32 J = JY * SizeX + JX;
					if (TileTurbid[TileOfCell(JX, JY)] && WaterOverCm(J) > 0.f)
					{
						Sum += T[J] - Own;
					}
				};
				if (X > 0) Pair(X - 1, Y);
				if (X < SizeX - 1) Pair(X + 1, Y);
				if (Y > 0) Pair(X, Y - 1);
				if (Y < SizeY - 1) Pair(X, Y + 1);
				New[I] = FMath::Clamp((Own + K * Sum) * Decay, 0.f, 1.f);
			}
		}
	}
	// 3. Written back; a cell whose value crossed a 32nd (or went to 0) is dirty.
	const int32 Listed = TurbidList.Num();
	TurbidListMax.SetNumUninitialized(Listed, EAllowShrinking::No);
	TurbidListBox.SetNumUninitialized(Listed, EAllowShrinking::No);
	for (int32 L = 0; L < Listed; ++L)
	{
		const int32 Tile = TurbidList[L];
		const int32 X0 = (Tile % TilesX) * TileCells;
		const int32 Y0 = (Tile / TilesX) * TileCells;
		const int32 X1 = FMath::Min(X0 + TileCells, SizeX);
		const int32 Y1 = FMath::Min(Y0 + TileCells, SizeY);
		float Max = 0.f;
		FIntRect Box(INT32_MAX, INT32_MAX, -1, -1);
		for (int32 Y = Y0; Y < Y1; ++Y)
		{
			for (int32 X = X0; X < X1; ++X)
			{
				const int32 I = Y * SizeX + X;
				const float Old = T[I];
				const float Value = New[I] < 1.e-5f ? 0.f : New[I];
				T[I] = Value;
				Max = FMath::Max(Max, Value);
				if (FMath::FloorToInt(Value * 32.f) != FMath::FloorToInt(Old * 32.f) || ((Value == 0.f) != (Old == 0.f)))
				{
					Box.Min.X = FMath::Min(Box.Min.X, X);
					Box.Min.Y = FMath::Min(Box.Min.Y, Y);
					Box.Max.X = FMath::Max(Box.Max.X, X);
					Box.Max.Y = FMath::Max(Box.Max.Y, Y);
				}
			}
		}
		TurbidListMax[L] = Max;
		TurbidListBox[L] = Box;
	}
	// 4. A tile under Wake everywhere sleeps, its remainder to 0 - unless a turbid neighbour's wet edge faces it (it would only
	//    join again next sub-step). Only tiles at Wake or more keep others awake, so the order does not matter.
	for (int32 L = 0; L < Listed; ++L)
	{
		const int32 Tile = TurbidList[L];
		FIntRect& Box = TurbidListBox[L];
		if (TurbidListMax[L] < Wake)
		{
			const int32 TX = Tile % TilesX, TY = Tile / TilesX;
			const FIntPoint Near[4] = { FIntPoint(TX - 1, TY), FIntPoint(TX + 1, TY), FIntPoint(TX, TY - 1), FIntPoint(TX, TY + 1) };
			bool bHeld = false;
			for (const FIntPoint& Nb : Near)
			{
				if (Nb.X >= 0 && Nb.Y >= 0 && Nb.X < TilesX && Nb.Y < TilesY)
				{
					const int32 Other = Nb.Y * TilesX + Nb.X;
					bHeld |= TileTurbid[Other] && TurbidEdgeWakes(Other, Tile);
				}
			}
			if (!bHeld)
			{
				TileTurbid[Tile] = 0;
				const int32 X0 = (Tile % TilesX) * TileCells;
				const int32 Y0 = (Tile / TilesX) * TileCells;
				const int32 X1 = FMath::Min(X0 + TileCells, SizeX);
				const int32 Y1 = FMath::Min(Y0 + TileCells, SizeY);
				for (int32 Y = Y0; Y < Y1; ++Y)
				{
					for (int32 X = X0; X < X1; ++X)
					{
						float& Value = T[Y * SizeX + X];
						if (Value > 0.f)
						{
							Value = 0.f;
							Box.Min.X = FMath::Min(Box.Min.X, X);
							Box.Min.Y = FMath::Min(Box.Min.Y, Y);
							Box.Max.X = FMath::Max(Box.Max.X, X);
							Box.Max.Y = FMath::Max(Box.Max.Y, Y);
						}
					}
				}
			}
		}
		if (Box.Max.X >= Box.Min.X)
		{
			MarkDirty(Box.Min.X, Box.Min.Y, Box.Max.X + 1, Box.Max.Y + 1);
		}
	}
}

int32 FGTMudField::AwakeTileCount() const
{
	int32 Count = 0;
	for (const uint8 Awake : TileAwake)
	{
		Count += Awake ? 1 : 0;
	}
	return Count;
}

int32 FGTMudField::WakeEdited(const TArray<uint8>& Edited)
{
	if (!IsValid() || Edited.Num() != SizeX * SizeY)
	{
		return 0;
	}
	int32 Count = 0;
	for (int32 Index = 0; Index < Edited.Num(); ++Index)
	{
		if (Edited[Index] == 0)
		{
			continue;
		}
		if (SetS.IsValidIndex(Index))
		{
			SetS[Index] = FMath::Max(SetS[Index], SetSeconds);
		}
		const int32 X = Index % SizeX;
		const int32 Y = Index / SizeX;
		WakeTiles(X, Y, X, Y);
		++Count;
	}
	return Count;
}

void FGTMudField::WakeTiles(int32 X0, int32 Y0, int32 X1, int32 Y1)
{
	if (TileAwake.Num() == 0)
	{
		return;
	}
	const int32 TX0 = FMath::Clamp(X0 / TileCells, 0, TilesX - 1);
	const int32 TY0 = FMath::Clamp(Y0 / TileCells, 0, TilesY - 1);
	const int32 TX1 = FMath::Clamp(X1 / TileCells, 0, TilesX - 1);
	const int32 TY1 = FMath::Clamp(Y1 / TileCells, 0, TilesY - 1);
	for (int32 TY = TY0; TY <= TY1; ++TY)
	{
		for (int32 TX = TX0; TX <= TX1; ++TX)
		{
			const int32 Tile = TY * TilesX + TX;
			TileAwake[Tile] = 1;
			TileQuietS[Tile] = 0.f;
			TileStill[Tile] = 0;
		}
	}
	// LM4f item 3 (read by gt.Snow.FastSettle 1 only): the tiles within FastSettleBandCm of these cells were written now.
	if (TileWriteS.Num() == TileAwake.Num())
	{
		const int32 Band = FMath::Max(0, FMath::CeilToInt(FMath::Max(0.f, FastSettleBandCm) / CellCm));
		const int32 BX0 = FMath::Clamp((X0 - Band) / TileCells, 0, TilesX - 1);
		const int32 BY0 = FMath::Clamp((Y0 - Band) / TileCells, 0, TilesY - 1);
		const int32 BX1 = FMath::Clamp((X1 + Band) / TileCells, 0, TilesX - 1);
		const int32 BY1 = FMath::Clamp((Y1 + Band) / TileCells, 0, TilesY - 1);
		for (int32 TY = BY0; TY <= BY1; ++TY)
		{
			for (int32 TX = BX0; TX <= BX1; ++TX)
			{
				TileWriteS[TY * TilesX + TX] = SettleClockS;
			}
		}
	}
}

int32 FGTMudField::Settle(float DeltaSeconds)
{
	if (!IsValid() || TileAwake.Num() == 0)
	{
		return 0;
	}
	// Fixed sub-steps from an accumulator, so the mud moves the same at 30, 60 or 144 frames a second. Float frame times
	// (1/60, 1/144) sum a hair under a whole number of steps, so a ten-thousandth of a step's slack, carried as a small
	// negative remainder rather than lost.
	double Step = FMath::Max(1.e-3, static_cast<double>(SettleStepS));
	if (bSnow && (SnowFastSettle == 1 || SnowFastSettle == 3))
	{
		// LM4f item 3 (gt.Snow.FastSettle 1, or 3): the snow's talus at FastSettleHz (15), each sub-step moving twice as far as at 30.
		Step = FMath::Max(Step, 1.0 / FMath::Max(1.0, static_cast<double>(FastSettleHz)));
	}
	SettleAccumS += FMath::Max(0.0, static_cast<double>(DeltaSeconds));
	int32 Steps = 0;
	const int32 MaxSteps = FMath::Max(1, SettleMaxSteps);
	while (SettleAccumS >= Step * (1.0 - 1.e-4) && Steps < MaxSteps)
	{
		SettleAccumS -= Step;
		SettleStep(static_cast<float>(Step));
		++Steps;
	}
	if (Steps >= MaxSteps)
	{
		SettleAccumS = FMath::Min(SettleAccumS, 0.0);   // a hitch: drop what is over the cap rather than run a burst next frame
	}
	return Steps;
}

void FGTMudField::SettleStep(float Dt)
{
	// LM4c item 2: the settle clock (the sub-steps run, so the collapses do not depend on the frame rate), and the wall
	// collapses that are due (snow), before the work list so the tiles they wrote sweep this sub-step.
	SettleClockS += Dt;
	if (bSnow && CollapseSegs.Num() > 0)
	{
		FireCollapses();
	}
	// LM4e cut 1 (snow, gt.Snow.QuietSleep): see the apply below.
	const bool bQuiet = bSnow && bSnowQuietSleep;
	float* F = Fresh.GetData();
	// LM4f item 3 (snow, gt.Snow.FastSettle 1, or 4): only the tiles within FastSettleBandCm of a write in the last FastSettleBandS, or by
	// a pending collapse, stay awake; any other awake tile sleeps now (as a quiet tile does: its sheen with it), though the
	// flux of a tile still awake reaches it and wakes it for that sub-step's apply.
	if (bSnow && (SnowFastSettle == 1 || SnowFastSettle == 4) && TileWriteS.Num() == TileAwake.Num() && TilePending.Num() == TileAwake.Num())
	{
		FMemory::Memzero(TilePending.GetData(), TilePending.Num());
		const int32 Band = FMath::Max(0, FMath::CeilToInt(FMath::Max(0.f, FastSettleBandCm) / CellCm));
		for (const FCollapseSeg& Seg : CollapseSegs)
		{
			if (!Seg.bPending)
			{
				continue;
			}
			// The wall lies FaceCm out from the line point, along Along0..Along1: a box round the point that holds all of it.
			const FVector2D Local = (Seg.LinePoint - OriginCm) / CellCm;
			const int32 Reach = Band + FMath::CeilToInt((FMath::Abs(Seg.FaceCm) + 0.5f * static_cast<float>(FMath::Abs(Seg.Along1 - Seg.Along0))) / CellCm);
			const int32 PX = FMath::FloorToInt(Local.X);
			const int32 PY = FMath::FloorToInt(Local.Y);
			if (PX + Reach < 0 || PY + Reach < 0 || PX - Reach >= SizeX || PY - Reach >= SizeY)
			{
				continue;
			}
			const int32 TX0 = FMath::Clamp((PX - Reach) / TileCells, 0, TilesX - 1);
			const int32 TY0 = FMath::Clamp((PY - Reach) / TileCells, 0, TilesY - 1);
			const int32 TX1 = FMath::Clamp((PX + Reach) / TileCells, 0, TilesX - 1);
			const int32 TY1 = FMath::Clamp((PY + Reach) / TileCells, 0, TilesY - 1);
			for (int32 TY = TY0; TY <= TY1; ++TY)
			{
				for (int32 TX = TX0; TX <= TX1; ++TX)
				{
					TilePending[TY * TilesX + TX] = 1;
				}
			}
		}
		const double BandS = FMath::Max(0.0, static_cast<double>(FastSettleBandS)) + 1.e-6;
		for (int32 Tile = 0; Tile < TileAwake.Num(); ++Tile)
		{
			if (!TileAwake[Tile] || TilePending[Tile] || SettleClockS - TileWriteS[Tile] <= BandS)
			{
				continue;
			}
			TileAwake[Tile] = 0;
			TileQuietS[Tile] = 0.f;
			TileStill[Tile] = 0;
			if (!bQuiet)
			{
				// As a tile that goes to sleep by itself: the last of its sheen goes with it.
				const int32 X0 = (Tile % TilesX) * TileCells;
				const int32 Y0 = (Tile / TilesX) * TileCells;
				const int32 X1 = FMath::Min(X0 + TileCells, SizeX);
				const int32 Y1 = FMath::Min(Y0 + TileCells, SizeY);
				int32 CX0 = INT32_MAX, CY0 = INT32_MAX, CX1 = -1, CY1 = -1;
				for (int32 Y = Y0; Y < Y1; ++Y)
				{
					for (int32 X = X0; X < X1; ++X)
					{
						float& Value = F[Y * SizeX + X];
						if (Value > 0.f)
						{
							Value = 0.f;
							CX0 = FMath::Min(CX0, X);
							CY0 = FMath::Min(CY0, Y);
							CX1 = FMath::Max(CX1, X);
							CY1 = FMath::Max(CY1, Y);
						}
					}
				}
				if (CX1 >= CX0)
				{
					MarkDirty(CX0, CY0, CX1 + 1, CY1 + 1);
				}
			}
		}
	}
	// The work list: the awake tiles that are moving or setting (swept), then the still ones (only their sheen fades),
	// then whatever this sub-step's flux wakes.
	SettleList.Reset();
	for (int32 Tile = 0; Tile < TileAwake.Num(); ++Tile)
	{
		if (TileAwake[Tile] && !TileStill[Tile])
		{
			SettleList.Add(Tile);
			SettleInList[Tile] = 1;
			SettleSweeps[Tile] = 1;
		}
	}
	const int32 NumAwake = SettleList.Num();
	SweptTilesSinceTake += NumAwake;   // LM4e readout
	for (int32 Tile = 0; Tile < TileAwake.Num(); ++Tile)
	{
		if (TileAwake[Tile] && TileStill[Tile])
		{
			SettleList.Add(Tile);
			SettleInList[Tile] = 1;
		}
	}
	ListedTilesSinceTake += SettleList.Num();   // LM4e readout
	if (SettleList.Num() == 0)
	{
		return;
	}
	// LM4f item 3 (snow, gt.Snow.FastSettle 1-4): the sweep and the apply over the tiles in parallel.
	const bool bParallel = bSnow && SnowFastSettle >= 1;
	// Slump to the angle of repose, ooze while the mud is still setting (LM1's diffusion, OozeRate 0 by default since
	// LM1b: the relax below gives the recovery without the blur). q is the height moved from the higher cell to
	// the lower one; the 0.2 caps keep a long sub-step stable (a cell can lose at most 0.2 of each step to each of its
	// four neighbours).
	const float Talus = FMath::Tan(FMath::DegreesToRadians(FMath::Clamp(ReposeDeg, 1.f, 89.f))) * CellCm;
	// LM4c item 1 (snow): the talus per cell - a pair takes the higher cell's: LooseReposeDeg where it stands above the snow
	// top or holds a collapse's pile, its static wall repose (40-80 deg by world noise) below the top. Mud: Talus as before.
	if (CellReposeOn())
	{
		EnsureSnowPiles();
	}
	const float* WallTalus = (CellReposeOn() && WallTalusCm.Num() == SizeX * SizeY) ? WallTalusCm.GetData() : nullptr;
	const uint8* Marks = (WallTalus && SnowMark.Num() == SizeX * SizeY) ? SnowMark.GetData() : nullptr;
	const float LooseTalus = FMath::Tan(FMath::DegreesToRadians(FMath::Clamp(LooseReposeDeg, 1.f, 89.f))) * CellCm;
	const float SlumpK = 0.5f * FMath::Min(FMath::Max(0.f, SlumpRate) * Dt, 0.2f);
	const float OozeK = 0.5f * FMath::Min(FMath::Max(0.f, OozeRate) * Dt, 0.2f);
	// LM4e cut 3 (snow, gt.Snow.FastSweep): a pair whose step is under the smallest talus any pair can take moves nothing
	// without the ooze, so it is passed over before its talus is looked up (exact); and no smear on snow (its OffsetCm is
	// neither drawn - M_GT_Snow reads no slide - nor read back by anything).
	const bool bFast = bSnow && bSnowFastSweep;
	const float Smear = (bFast ? 0.f : FMath::Max(0.f, SmearCmPerCm));
	const float MaxSlide = FMath::Max(0.f, MaxSlideCm);
	const float MinPairTalus = WallTalus ? FMath::Min(LooseTalus, WallTalusMinCm) : Talus;
	const bool bEarlyOut = bFast && OozeK <= 0.f;
	// LM4e cut 3: the flux's tiles, so the apply can pass over a listed tile nothing reached (snow: no set timers, no relax).
	const bool bFluxTiles = bFast && bSnowQuietSleep && SetSeconds <= 0.f;
	if (TileFlux.Num() != TilesX * TilesY)
	{
		TileFlux.Init(0, TilesX * TilesY);
	}
	uint8* TileFluxPtr = TileFlux.GetData();
	float* H = HeightCm.GetData();
	float* L = LumpCm.GetData();
	float* Delta = SettleDelta.GetData();
	float* Out = SettleOut.GetData();
	const float* Set = SetS.GetData();
	FVector2f* Off = OffsetCm.GetData();
	// One neighbour pair, I and J (J to the right of or below I, Dir the unit step from I to J). True when mud moved.
	// LM2a: the talus and the ooze run on the surface, HeightCm + LumpCm; what leaves a cell is also booked in Out, and
	// the apply takes it from the cell's lumps first.
	// LM4f item 3: in two halves - PairQ, the height a pair moves (0: none) and which way, from the heights the sub-step started
	// with and nothing else (it writes nothing, so the parallel sweep calls it from any thread), and AddFlux, its writes.
	auto PairQ = [&](int32 I, int32 J, bool& bOutIHigher) -> float
	{
		const float SurfI = H[I] + L[I];
		const float SurfJ = H[J] + L[J];
		const float Diff = SurfI - SurfJ;
		const float AbsDiff = FMath::Abs(Diff);
		if (bEarlyOut && AbsDiff <= MinPairTalus)
		{
			return 0.f;   // LM4e cut 3: under every talus, and no ooze: nothing moves (the full test below gives the same)
		}
		float PairTalus = Talus;
		if (WallTalus)
		{
			const int32 Higher = Diff >= 0.f ? I : J;
			const float HigherSurf = Diff >= 0.f ? SurfI : SurfJ;
			PairTalus = (HigherSurf > 0.f || (Marks && (Marks[Higher] & SnowMarkDebris))) ? LooseTalus : WallTalus[Higher];
		}
		float Q = 0.f;
		if (AbsDiff > PairTalus)
		{
			Q += SlumpK * (AbsDiff - PairTalus);
		}
		if (Set[I] > 0.f || Set[J] > 0.f)
		{
			Q += OozeK * AbsDiff;
		}
		bOutIHigher = Diff >= 0.f;
		return Q;
	};
	auto AddFlux = [&](int32 I, int32 J, const FVector2f& Dir, float Q, bool bIHigher)
	{
		const int32 From = bIHigher ? I : J;
		const int32 To = bIHigher ? J : I;
		Delta[From] -= Q;
		Delta[To] += Q;
		Out[From] -= Q;
		if (bFluxTiles)
		{
			// LM4e cut 3: the tiles this flux touched (the apply passes over a listed tile no flux reached).
			TileFluxPtr[((I / SizeX) / TileCells) * TilesX + (I % SizeX) / TileCells] = 1;
			TileFluxPtr[((J / SizeX) / TileCells) * TilesX + (J % SizeX) / TileCells] = 1;
		}
		if (Smear > 0.f)
		{
			// The receiving cell's texture drags the way the mud went, so the clay visibly smears where it moved.
			FVector2f& Offset = Off[To];
			Offset += (bIHigher ? Dir : -Dir) * (Q * Smear);
			const float Size = Offset.Size();
			if (Size > MaxSlide && Size > 0.f)
			{
				Offset *= MaxSlide / Size;
			}
		}
	};
	auto Pair = [&](int32 I, int32 J, const FVector2f& Dir) -> bool
	{
		bool bIHigher = false;
		const float Q = PairQ(I, J, bIHigher);
		if (Q <= 0.f)
		{
			return false;
		}
		AddFlux(I, J, Dir, Q, bIHigher);
		return true;
	};
	auto WakeTile = [&](int32 X, int32 Y)
	{
		const int32 Tile = (Y / TileCells) * TilesX + (X / TileCells);
		if (!SettleInList[Tile])
		{
			SettleInList[Tile] = 1;
			SettleList.Add(Tile);
		}
	};
	const FVector2f Right(1.f, 0.f);
	const FVector2f Down(0.f, 1.f);
	// The sweep. A pair is the tile's of its first cell when that tile is swept; the pairs reaching in from a tile that is
	// not (asleep, or still) to the left or above are this tile's too (its one-cell border), so every pair touching a swept
	// tile is taken exactly once. Flux into a sleeping tile wakes it; flux into a still one moves it, and it sweeps again.
	// LM4f item 3: one tile's sweep, its pairs through PairFn (true: it moved) and its wakes through WakeFn, in the serial order.
	auto SweepTile = [&](int32 Tile, auto&& PairFn, auto&& WakeFn)
	{
		const int32 X0 = (Tile % TilesX) * TileCells;
		const int32 Y0 = (Tile / TilesX) * TileCells;
		const int32 X1 = FMath::Min(X0 + TileCells, SizeX);
		const int32 Y1 = FMath::Min(Y0 + TileCells, SizeY);
		for (int32 Y = Y0; Y < Y1; ++Y)
		{
			const int32 Row = Y * SizeX;
			int32 X = X0;
			if (bEarlyOut)
			{
				// LM4e cut 3: four cells at a time, their right and down steps against a hair under MinPairTalus (SSE); only
				// a lane over it goes through Pair, in the scalar order (right, then down, cell by cell), which decides as
				// before - so the pairs that move and the order their flux is added are the same.
				const VectorRegister4Float Limit = VectorSetFloat1(MinPairTalus * 0.9999f - 1.e-5f);
				const bool bDownRow = Y + 1 < SizeY;
				for (; X + 4 < X1 || (X + 4 <= X1 && X + 4 < SizeX); X += 4)
				{
					const int32 I = Row + X;
					const VectorRegister4Float S = VectorAdd(VectorLoad(H + I), VectorLoad(L + I));
					const VectorRegister4Float SR = VectorAdd(VectorLoad(H + I + 1), VectorLoad(L + I + 1));
					int32 Bits = VectorMaskBits(VectorCompareGT(VectorAbs(VectorSubtract(S, SR)), Limit));
					if (bDownRow)
					{
						const VectorRegister4Float SD = VectorAdd(VectorLoad(H + I + SizeX), VectorLoad(L + I + SizeX));
						Bits |= VectorMaskBits(VectorCompareGT(VectorAbs(VectorSubtract(S, SD)), Limit)) << 4;
					}
					if (Bits == 0)
					{
						continue;
					}
					for (int32 K = 0; K < 4; ++K)
					{
						const int32 XK = X + K;
						if (((Bits >> K) & 1) && PairFn(I + K, I + K + 1, Right) && XK + 1 == X1)
						{
							WakeFn(XK + 1, Y);
						}
						if (((Bits >> (K + 4)) & 1) && PairFn(I + K, I + K + SizeX, Down) && Y + 1 == Y1)
						{
							WakeFn(XK, Y + 1);
						}
					}
				}
			}
			for (; X < X1; ++X)
			{
				const int32 I = Row + X;
				if (X + 1 < SizeX && PairFn(I, I + 1, Right) && X + 1 == X1)
				{
					WakeFn(X + 1, Y);
				}
				if (Y + 1 < SizeY && PairFn(I, I + SizeX, Down) && Y + 1 == Y1)
				{
					WakeFn(X, Y + 1);
				}
			}
		}
		if (X0 > 0)
		{
			for (int32 Y = Y0; Y < Y1; ++Y)
			{
				if (!SettleSweeps[(Y / TileCells) * TilesX + (X0 - 1) / TileCells] && PairFn(Y * SizeX + X0 - 1, Y * SizeX + X0, Right))
				{
					WakeFn(X0 - 1, Y);
				}
			}
		}
		if (Y0 > 0)
		{
			for (int32 X = X0; X < X1; ++X)
			{
				if (!SettleSweeps[((Y0 - 1) / TileCells) * TilesX + X / TileCells] && PairFn((Y0 - 1) * SizeX + X, Y0 * SizeX + X, Down))
				{
					WakeFn(X, Y0 - 1);
				}
			}
		}
	};
	if (!bParallel)
	{
		for (int32 ListIndex = 0; ListIndex < NumAwake; ++ListIndex)
		{
			SweepTile(SettleList[ListIndex], Pair, WakeTile);
		}
	}
	else
	{
		// LM4f item 3: every swept tile's pairs at once (PairQ reads only the heights, the lumps, the set timers and the static
		// talus, none of which the sweep writes), each tile's flux and wakes logged in its own serial order; then the logs are
		// added tile by tile in the work list's order - exactly the serial sweep's sequence of additions, so the same sums.
		if (SweepLogs.Num() < NumAwake)
		{
			SweepLogs.SetNum(NumAwake);
		}
		ParallelFor(TEXT("GTSnowSettleSweep"), NumAwake, 1, [&](int32 ListIndex)
		{
			TArray<FFluxLog>& Log = SweepLogs[ListIndex];
			Log.Reset();
			auto LogPair = [&](int32 I, int32 J, const FVector2f& Dir) -> bool
			{
				bool bIHigher = false;
				const float Q = PairQ(I, J, bIHigher);
				if (Q <= 0.f)
				{
					return false;
				}
				FFluxLog& Entry = Log.AddDefaulted_GetRef();
				Entry.From = I;
				Entry.To = J;
				Entry.Q = Q;
				Entry.Flags = static_cast<uint8>((Dir.Y > 0.5f ? 1 : 0) | (bIHigher ? 0 : 2));
				return true;
			};
			auto LogWake = [&](int32 X, int32 Y)
			{
				FFluxLog& Entry = Log.AddDefaulted_GetRef();
				Entry.From = X;
				Entry.To = Y;
				Entry.Q = -1.f;
			};
			SweepTile(SettleList[ListIndex], LogPair, LogWake);
		}, EParallelForFlags::Unbalanced);
		for (int32 ListIndex = 0; ListIndex < NumAwake; ++ListIndex)
		{
			for (const FFluxLog& Entry : SweepLogs[ListIndex])
			{
				if (Entry.Q < 0.f)
				{
					WakeTile(Entry.From, Entry.To);
				}
				else
				{
					AddFlux(Entry.From, Entry.To, (Entry.Flags & 1) ? Down : Right, Entry.Q, (Entry.Flags & 2) == 0);
				}
			}
		}
	}
	// LM1b, the shape-keeping relax (docs/LIVING_MUD_PLAN.md LM1b). Every set cell of the swept tiles (a still or sleeping
	// tile has none: it sleeps only once nothing in it is setting) asks to move toward the ground by K of its own height,
	// K = 1 - exp(-a dt), a = -ln(1 - RecoverShare) / SetSeconds, so a whole set gives back RecoverShare of it. First pass:
	// the rises asked below 0 (V_up) and the falls asked above 0 (V_down), over the whole patch. The larger side is scaled
	// down to the smaller, so the rut rises only by what the banks give up and the volume is kept exactly. Second pass:
	// the moves into the delta buffer (HeightCm only), and each moved cell's texture creeps down the surface's slope by
	// CreepCmPerCm per cm it moved. No neighbour's height enters a cell's move, so nothing is averaged: the relief scales.
	const float Share = FMath::Clamp(RecoverShare, 0.f, 0.99f);
	if (Share > 0.f && SetSeconds > 0.f)
	{
		const float Rate = -FMath::Loge(1.f - Share) / SetSeconds;
		const double K = 1.0 - FMath::Exp(-static_cast<double>(Rate) * Dt);
		RelaxCells.Reset();
		double AskUp = 0.0;
		double AskDown = 0.0;
		for (int32 ListIndex = 0; ListIndex < NumAwake; ++ListIndex)
		{
			const int32 Tile = SettleList[ListIndex];
			const int32 X0 = (Tile % TilesX) * TileCells;
			const int32 Y0 = (Tile / TilesX) * TileCells;
			const int32 X1 = FMath::Min(X0 + TileCells, SizeX);
			const int32 Y1 = FMath::Min(Y0 + TileCells, SizeY);
			for (int32 Y = Y0; Y < Y1; ++Y)
			{
				const int32 Row = Y * SizeX;
				for (int32 X = X0; X < X1; ++X)
				{
					const int32 I = Row + X;
					if (Set[I] > 0.f && H[I] != 0.f)
					{
						RelaxCells.Add(I);
						if (H[I] < 0.f)
						{
							AskUp -= H[I];
						}
						else
						{
							AskDown += H[I];
						}
					}
				}
			}
		}
		const double CellArea = static_cast<double>(CellCm) * CellCm;
		AskUp *= K;
		AskDown *= K;
		RelaxAskedUpCm3 += AskUp * CellArea;
		RelaxAskedDownCm3 += AskDown * CellArea;
		const double Moved = FMath::Min(AskUp, AskDown);
		if (Moved > 0.0)
		{
			RelaxMovedCm3 += Moved * CellArea;
			const float UpK = static_cast<float>(K * (Moved / AskUp));
			const float DownK = static_cast<float>(K * (Moved / AskDown));
			const float Creep = FMath::Max(0.f, CreepCmPerCm);
			for (const int32 I : RelaxCells)
			{
				const float Change = -H[I] * (H[I] < 0.f ? UpK : DownK);
				Delta[I] += Change;
				if (Creep > 0.f)
				{
					// The surface's slope here (central differences, one-sided at the grid's edge), from the heights this
					// sub-step started with; the texture creeps the downhill way.
					const int32 X = I % SizeX;
					const int32 Y = I / SizeX;
					const int32 XL = X > 0 ? I - 1 : I;
					const int32 XR = X + 1 < SizeX ? I + 1 : I;
					const int32 YU = Y > 0 ? I - SizeX : I;
					const int32 YD = Y + 1 < SizeY ? I + SizeX : I;
					const FVector2f Slope((H[XR] - H[XL]) / (static_cast<float>(FMath::Max(1, XR - XL)) * CellCm),
						(H[YD] - H[YU]) / (static_cast<float>(FMath::Max(1, (YD - YU) / SizeX)) * CellCm));
					const float SlopeSize = Slope.Size();
					if (SlopeSize > 1.e-4f)
					{
						FVector2f& Offset = Off[I];
						Offset -= Slope * (FMath::Abs(Change) * Creep / SlopeSize);
						const float Size = Offset.Size();
						if (Size > MaxSlide && Size > 0.f)
						{
							Offset *= MaxSlide / Size;
						}
					}
				}
			}
		}
	}
	// Apply the flux, then fresh, the set timer and sleep, tile by tile, and mark dirty only the cells that changed (a
	// height over a micrometre, or a fresh value across a sixteenth, which is all the texture would show).
	const float FreshFade = Dt / FMath::Max(0.01f, FreshFadeS);
	const float SleepCm = FMath::Max(0.f, SleepCmPerS) * Dt;
	float* SetW = SetS.GetData();
	// LM4e cut 1 (snow, gt.Snow.QuietSleep): no fresh sheen is kept - M_GT_Snow draws none (the tread texture's B is the lumps'
	// mask on snow) - so a still tile sleeps after its 0.5 s quiet instead of holding the sheen's 6 s fade awake, nothing is
	// marked dirty for a fading sheen, and a sleeping tile that flux reaches takes a still tile's test (it sweeps again only
	// once it moves over SleepCmPerS), as it would have while its sheen faded. The heights move exactly as before.
	// LM4f item 3: one tile's apply, its changed cells' box into Box (the caller marks it dirty). A tile's apply writes its own
	// cells and its own tile flags only, so the parallel apply runs the tiles at once and marks them dirty in the list's order.
	auto ApplyTile = [&](int32 Tile, FTileBox& Box)
	{
		const int32 X0 = (Tile % TilesX) * TileCells;
		const int32 Y0 = (Tile / TilesX) * TileCells;
		const int32 X1 = FMath::Min(X0 + TileCells, SizeX);
		const int32 Y1 = FMath::Min(Y0 + TileCells, SizeY);
		float MaxMove = 0.f;
		bool bSetting = false;
		bool bFresh = false;
		int32 CX0 = INT32_MAX, CY0 = INT32_MAX, CX1 = -1, CY1 = -1;
		// LM4e cut 3: a listed tile no flux reached this sub-step has no move, set timer or sheen to apply (its cells' Delta and
		// Out are 0): it only keeps its still and quiet time below.
		const bool bNoFlux = bFluxTiles && !TileFluxPtr[Tile];
		TileFluxPtr[Tile] = 0;
		for (int32 Y = Y0; Y < Y1 && !bNoFlux; ++Y)
		{
			const int32 Row = Y * SizeX;
			for (int32 X = X0; X < X1; ++X)
			{
				const int32 I = Row + X;
				const float Move = Delta[I];
				if (bQuiet)
				{
					if (Move == 0.f && SetW[I] == 0.f)
					{
						if (F[I] != 0.f)
						{
							F[I] = 0.f;   // a stamp's mark, unread on snow
						}
						if (Out[I] != 0.f)
						{
							Out[I] = 0.f;
						}
						continue;
					}
				}
				else if (Move == 0.f && F[I] == 0.f && SetW[I] == 0.f)
				{
					Out[I] = 0.f;
					continue;   // untouched ground in an awake tile: nothing moves, fades or sets
				}
				const float AbsMove = FMath::Abs(Move);
				if (Move != 0.f)
				{
					H[I] += Move;
					Delta[I] = 0.f;
					MaxMove = FMath::Max(MaxMove, AbsMove);
				}
				if (Out[I] != 0.f)
				{
					// LM2a: what left the cell by the talus or the ooze comes out of its lumps first (the surface's change is
					// Move either way): the lumps sag before the bank does. With no lump here this is nothing.
					const float Take = FMath::Min(L[I], -Out[I]);
					if (Take > 0.f)
					{
						L[I] -= Take;
						H[I] += Take;
					}
					Out[I] = 0.f;
				}
				const float OldFresh = F[I];
				const float NewFresh = bQuiet ? 0.f : (AbsMove > FreshMinCm ? 1.f : FMath::Max(0.f, OldFresh - FreshFade));
				F[I] = NewFresh;
				if (SetW[I] > 0.f)
				{
					SetW[I] = FMath::Max(0.f, SetW[I] - Dt);
					bSetting |= SetW[I] > 0.f;
				}
				bFresh |= NewFresh > 0.02f;
				if (AbsMove > 1.e-4f || (!bQuiet && FMath::FloorToInt(NewFresh * 16.f) != FMath::FloorToInt(OldFresh * 16.f)))
				{
					CX0 = FMath::Min(CX0, X);
					CY0 = FMath::Min(CY0, Y);
					CX1 = FMath::Max(CX1, X);
					CY1 = FMath::Max(CY1, Y);
				}
			}
		}
		const bool bStill = MaxMove <= SleepCm && !bSetting;
		if (!TileAwake[Tile])
		{
			TileAwake[Tile] = 1;   // woken by flux this sub-step: it sweeps the next one
			TileQuietS[Tile] = 0.f;
			TileStill[Tile] = (bQuiet && bStill) ? 1 : 0;   // LM4e cut 1: on snow, as a still tile would (it sweeps once it moves)
		}
		else
		{
			TileStill[Tile] = bStill ? 1 : 0;
			TileQuietS[Tile] = (bStill && !bFresh) ? TileQuietS[Tile] + Dt : 0.f;
			if (TileQuietS[Tile] >= 0.5f - 1.e-4f)
			{
				// Asleep: the last of the sheen goes to nothing with it, so a sleeping tile never holds a faint one.
				TileAwake[Tile] = 0;
				TileQuietS[Tile] = 0.f;
				for (int32 Y = Y0; Y < Y1 && !bQuiet; ++Y)
				{
					for (int32 X = X0; X < X1; ++X)
					{
						float& Value = F[Y * SizeX + X];
						if (Value > 0.f)
						{
							Value = 0.f;
							CX0 = FMath::Min(CX0, X);
							CY0 = FMath::Min(CY0, Y);
							CX1 = FMath::Max(CX1, X);
							CY1 = FMath::Max(CY1, Y);
						}
					}
				}
			}
		}
		SettleInList[Tile] = 0;
		SettleSweeps[Tile] = 0;
		Box.X0 = CX0;
		Box.Y0 = CY0;
		Box.X1 = CX1;
		Box.Y1 = CY1;
	};
	if (!bParallel)
	{
		for (const int32 Tile : SettleList)
		{
			FTileBox Box;
			ApplyTile(Tile, Box);
			if (Box.X1 >= Box.X0)
			{
				MarkDirty(Box.X0, Box.Y0, Box.X1 + 1, Box.Y1 + 1);
			}
		}
	}
	else
	{
		const int32 Listed = SettleList.Num();
		ApplyBoxes.SetNum(Listed, EAllowShrinking::No);
		ParallelFor(TEXT("GTSnowSettleApply"), Listed, 1, [&](int32 ListIndex)
		{
			ApplyTile(SettleList[ListIndex], ApplyBoxes[ListIndex]);
		}, EParallelForFlags::Unbalanced);
		for (int32 ListIndex = 0; ListIndex < Listed; ++ListIndex)
		{
			const FTileBox& Box = ApplyBoxes[ListIndex];
			if (Box.X1 >= Box.X0)
			{
				MarkDirty(Box.X0, Box.Y0, Box.X1 + 1, Box.Y1 + 1);
			}
		}
	}
}

double FGTMudField::StampWheel(const FVector2D& FromCm, const FVector2D& ToCm, float WidthCm, float DepthCm, const FVector2D& HeadingDir, float RolledCm,
	float ThrowShare, double& OutThrownCm3)
{
	// LM4e: timed and recorded when called from outside the field (the replay calls it the same way).
	const FOuterCall Call(*this);
	Call.Record(EventStampWheel, { FromCm.X, FromCm.Y, ToCm.X, ToCm.Y, WidthCm, DepthCm, HeadingDir.X, HeadingDir.Y, RolledCm, ThrowShare });
	OutThrownCm3 = 0.0;
	// LM3a: in snow a tyre with no sinkage still cuts the snow above its bottom, so only mud needs a depth.
	if (!IsValid() || (DepthCm <= 0.f && !(bSnow && DepthCm >= 0.f)))
	{
		return 0.0;
	}
	// LM2a: the lumps' static weights for the numbers in force (built once; a no-op after that).
	const bool bLumps = LumpShare > 0.f;
	if (bLumps)
	{
		EnsureLumpWeights();
	}
	// LM4f item 4: the static per-cell noises this stamp reads come from their slots (CellNoise's very values, built once when the
	// patch starts, not hashed per cell per stamp), and the piles' static arrays are ensured once here, not per lip cell.
	const float WaveCells = FMath::Max(1.f, RidgeWaveCm / CellCm);
	const float WaveLongCells = FMath::Max(1.f, RidgeWaveLongCm / CellCm);
	const float MetreCells = FMath::Max(1.f, 100.f / CellCm);
	const float* NWave = NoiseCells(NoiseWave, WaveCells, 11);
	const float* NWaveLong = NoiseCells(NoiseWaveLong, WaveLongCells, 13);
	const float* NSide = NoiseCells(NoiseSide, MetreCells, 17);
	const float* NSlump = FMath::Clamp(RidgeSlump, 0.f, 1.f) > 0.f ? NoiseCells(NoiseSlump, MetreCells, 23) : nullptr;
	const float* NPocket = NoiseCells(NoisePocket, PocketNoiseCells, 53);
	const float* NFloor = NoiseCells(NoiseFloor, FloorNoiseCells, 31);
	const float* NClump = NoiseCells(NoiseClump, RidgeNoiseCells, 0);
	const float* NClod = ClodChance > 0.f ? NoiseCells(NoiseClod, 1.f, 41) : nullptr;
	const float* NClodSize = ClodChance > 0.f ? NoiseCells(NoiseClodSize, 1.f, 43) : nullptr;
	const float* NTracksEdge = NoiseCells(NoiseTracksEdge, TracksEdgeCells, 7);
	if (PilesOn())
	{
		EnsureSnowPiles();
	}
	const float Radius = FMath::Max(2.f, WidthCm * 0.5f);
	// Stage I: the band's width varies along the stroke (RidgeWave), so the reach is the widest it can be.
	const float BandCm = FMath::Max(1.f, RidgeBandCm());
	// LM3a: the fewest cells a wall spans is RutShoulderMinCells (mud's 2 as before; snow's 1, so its 10 cm wall stands).
	const float ShoulderBase = FMath::Max(FMath::Max(0.5f, RutShoulderMinCells) * CellCm, FMath::Max(RutShoulderCm, DepthCm * RutShoulderDepthScale));
	const float ShoulderWave = FMath::Clamp(RutShoulderVariation, 0.f, 0.5f);
	// LM4 item 3 (snow): the wall line steps out by up to WallStepMaxCm, so the reach does too (0 on mud: as before).
	// LM4b: or wanders by the waves (their amplitudes' sum at most), or only drops plates (no offset).
	const bool bWallSteps = WallLineOn();
	const float WallReach = WallStepMaxCm > 0.f ? WallStepMaxCm : FMath::Abs(WallWaveAmpCm) + FMath::Abs(WallWaveLongAmpCm);
	const float Reach = Radius + ShoulderBase * (1.f + ShoulderWave + 0.15f) + FMath::Max(BandCm, SlideWidthCm) + (bWallSteps ? WallReach : 0.f);
	const FVector2D A = FromCm - OriginCm;
	const FVector2D B = ToCm - OriginCm;
	const FVector2D Lo = FVector2D::Min(A, B) - FVector2D(Reach, Reach);
	const FVector2D Hi = FVector2D::Max(A, B) + FVector2D(Reach, Reach);
	if (Hi.X < 0.f || Hi.Y < 0.f || Lo.X > SizeX * CellCm || Lo.Y > SizeY * CellCm)
	{
		return 0.0;
	}
	const int32 X0 = FMath::Clamp(FMath::FloorToInt(Lo.X / CellCm), 0, SizeX - 1);
	const int32 Y0 = FMath::Clamp(FMath::FloorToInt(Lo.Y / CellCm), 0, SizeY - 1);
	const int32 X1 = FMath::Clamp(FMath::CeilToInt(Hi.X / CellCm), 0, SizeX - 1);
	const int32 Y1 = FMath::Clamp(FMath::CeilToInt(Hi.Y / CellCm), 0, SizeY - 1);
	const FVector2D AB = B - A;
	const float LenSq = AB.SizeSquared();
	const float SegLenM = FMath::Sqrt(LenSq) / 100.f;
	const float CellArea = CellCm * CellCm;
	const float Target = -DepthCm;
	double Removed = 0.0;
	// Stage F, the tread: the heading the tyre is going (the caller's, the stroke's own direction when it has none) as
	// turns, and the lug phase at each cell of the capsule from how far the tyre has rolled. Written over the whole
	// capsule, so a second pass down a compacted rut (which lowers nothing) still lays its own tread.
	FVector2D Head = HeadingDir.GetSafeNormal();
	if (Head.IsNearlyZero())
	{
		Head = AB.GetSafeNormal();
	}
	if (Head.IsNearlyZero())
	{
		Head = FVector2D(1.f, 0.f);
	}
	const float HeadTurns = Wrap01(static_cast<float>(FMath::Atan2(Head.Y, Head.X)) / (2.f * PI));
	const float LugCm = FMath::Max(1.f, LugPeriodCm);
	// LM3c item 1: snow fields record the tick a tyre last wrote each cell's tread (PloughBelly reads it).
	const bool bTreadTicks = bSnow && TreadTickOf.Num() == SizeX * SizeY;
	// LM3c item 3: and the plough's berm cells take no ridge smoothing (stage H's below) when the berm is a bank's.
	const bool bKeepBerms = bSnow && bPloughBankPath && SnowMark.Num() == SizeX * SizeY;
	// LM4c (snow): the lips' cluster factor (item 3), and the wall segments a cut arms for a delayed collapse (item 2).
	const bool bPiles = PilesOn();
	const bool bCollapses = bSnow && CollapseChance > 0.f;
	const bool bDebrisMarks = bCollapses && SnowMark.Num() == SizeX * SizeY;
	// Stage H: the ridge's return, the rut floor's depth and the tracks' edge all vary cell by cell from a hashed
	// lattice (a function of the cell alone, so a second pass down a rut deepens the same clumps and nothing has to be
	// stored), and the cells a stamp touched are smoothed along its own direction once it has drawn them.
	const float NoiseRidge = FMath::Max(0.f, RidgeNoise);
	const float NoiseFloorCm = FMath::Max(0.f, FloorNoiseCm);
	// The smoothing is in proportion to how far this stroke rolled, over the tyre's own width: mud slumps by as much as
	// was just moved, and a stamp is one physics tick. A flat RidgeSmooth per stamp made the whole thing depend on the
	// tick rate - a crawling wheel stamps a 0.2 cm stroke a hundred times a second, which is a hundred smoothings of the
	// same cells a second, and that diffused away everything the stamps had just written (the crest's clumps with it).
	const float Smooth = FMath::Clamp(RidgeSmooth, 0.f, 1.f) * FMath::Clamp(FMath::Sqrt(LenSq) / (2.f * Radius), 0.f, 1.f);
	const float Blend = FMath::Clamp(RidgeBlend, 0.f, 1.f);
	// Stage I (docs/MUD_ONE_SURFACE_PLAN.md section 3): the bank varies along the stroke, not only from cell to cell.
	// Everything here is read at the cell's foot on the stroke - the point on the segment it hangs off - so one station
	// of the rut has one height, one width, one heavier side and one slump, whatever the cell's distance out. Four
	// lattice noises share a one-entry cache because a stamp's cells walk the same few stations.
	const float WaveAmount = FMath::Max(0.f, RidgeWave);
	const float WidthWave = FMath::Clamp(RidgeWidthWave, 0.f, 1.f);
	const float SideBias = FMath::Clamp(RidgeSideBias, 0.f, 0.9f);
	const float SlumpChance = FMath::Clamp(RidgeSlump, 0.f, 1.f);
	int32 CacheX = INT32_MIN;
	int32 CacheY = INT32_MIN;
	float CacheHeightWave = 0.f;
	float CacheWidthWave = 0.f;
	float CacheSide = 0.f;
	float CacheSlump = 0.f;
	auto Station = [&](const FVector2D& Foot)
	{
		const int32 SX = FMath::FloorToInt(Foot.X / CellCm);
		const int32 SY = FMath::FloorToInt(Foot.Y / CellCm);
		if (SX == CacheX && SY == CacheY)
		{
			return;
		}
		CacheX = SX;
		CacheY = SY;
		CacheHeightWave = NoiseAt(NWave, SX, SY, WaveCells, 11);
		CacheWidthWave = NoiseAt(NWaveLong, SX, SY, WaveLongCells, 13);
		CacheSide = FMath::Clamp(2.f * NoiseAt(NSide, SX, SY, MetreCells, 17), -1.f, 1.f);
		// The slump stretches: the top 2 x RidgeSlump of a 1 m noise's range, which comes out as 40-80 cm of bank at a time.
		CacheSlump = SlumpChance <= 0.f ? 0.f
			: FMath::Clamp((NoiseAt(NSlump, SX, SY, MetreCells, 23) - (1.f - 2.f * SlumpChance)) / 0.35f, 0.f, 1.f);
	};
	auto ShoulderAt = [&](const FVector2D& Foot, const FVector2D& Away)
	{
		Station(Foot);
		const float Side = FVector2D::CrossProduct(Head, Away) >= 0.f ? 1.f : -1.f;
		return ShoulderBase * (1.f + ShoulderWave * FMath::Clamp(2.f * CacheHeightWave, -1.f, 1.f) + 0.15f * Side * CacheSide);
	};
	// LM4 item 3 (snow): the wall's offset at a station, on the world side of the stroke's dominant axis the cell lies on
	// (FGTMudField::WallOffsetAt; a one-entry cache per side, as Station's), and whether that segment drops its lip plate.
	const FVector2D WallLine = AB.SizeSquared() > 1.e-6 ? AB.GetSafeNormal() : Head;
	const bool bWallAlongX = FMath::Abs(WallLine.X) >= FMath::Abs(WallLine.Y);
	struct FWallCache
	{
		int32 SX = INT32_MIN;
		int32 SY = INT32_MIN;
		float Offset = 0.f;
		bool bDrop = false;
		uint64 Key = 0;
	};
	FWallCache WallCache[2];
	auto WallSideOf = [&](const FVector2D& Away) { return (bWallAlongX ? Away.Y : Away.X) >= 0.0 ? 1.f : -1.f; };
	auto WallAt = [&](const FVector2D& Foot, float Side) -> const FWallCache&
	{
		FWallCache& Cache = WallCache[Side > 0.f ? 1 : 0];
		if (!bWallSteps)
		{
			return Cache;
		}
		const int32 SX = FMath::FloorToInt(Foot.X / CellCm);
		const int32 SY = FMath::FloorToInt(Foot.Y / CellCm);
		if (SX != Cache.SX || SY != Cache.SY)
		{
			Cache.SX = SX;
			Cache.SY = SY;
			Cache.Offset = WallOffsetAt(Foot + OriginCm, WallLine, Side, Cache.bDrop, Cache.Key);
		}
		return Cache;
	};
	struct FRidgeCell
	{
		int32 Index = 0;
		float Weight = 0.f;
		float Before = 0.f;     // LM1: the surface before this stamp, for the fresh mark
		float BandT = 1.f;      // LM2c: how far out across the band beside the stroke's line (0 at the shoulder, 1 at the band's width)
		bool bLip = false;      // LM2c: beside the rut (not ahead of or behind the tyre on its own line)
		bool bEligible = false; // LM2a: takes a deposit (not a rut, not at the cap), as it stood before this stamp
		bool bDrop = false;     // LM4 item 3: a lip cell beside a wall segment that drops its plate into the trench
		float DropW = 0.f;      // LM4b item 2: the share of its lump that falls (1 inside a dropping segment, feathered at its ends)
		int8 WallSide = 0;      // LM4: the world side of the stroke it lies on (+1 / -1)
		uint64 WallKey = 0;     // LM4: its wall segment
		FVector2D LineFoot = FVector2D::ZeroVector;   // LM4: its own foot on the stroke's line (unclamped), field-local cm
	};
	// LM2c: the stroke's line, for the bank clods' lip (the band's cells beside the rut, measured square to the line).
	const FVector2D LineDir = AB.SizeSquared() > 1.e-6 ? AB.GetSafeNormal() : Head;
	struct FFloorCell
	{
		int32 Index = 0;
		float TargetCm = 0.f;   // the depth this stamp cut the cell to (stage H's smoothing keeps to it)
		float Slump = 0.f;      // stage I: how much of the bank above it fell back in here
		float Before = 0.f;     // LM1: the surface before this stamp, for the fresh mark
		int8 WallSide = 0;      // LM4 item 3: the world side of the stroke it lies on, and how far out across the tyre (D / Radius)
		float Out = 0.f;
	};
	const float CellAreaLump = CellCm * CellCm;
	double Flattened = 0.0;     // LM2a: the lumps this capsule flattened (their volume joins what it displaced)
	TArray<FRidgeCell> Ridge;
	TArray<FFloorCell> FloorCells;
	float WeightSum = 0.f;         // after the slump took its share out
	float UnslumpedSum = 0.f;      // before it: the volume is normalised by this, so what slumps leaves the bank
	float SlumpFloorWeight = 0.f;  // the floor cells that share what came back
	for (int32 Y = Y0; Y <= Y1; ++Y)
	{
		for (int32 X = X0; X <= X1; ++X)
		{
			const FVector2D P((X + 0.5f) * CellCm, (Y + 0.5f) * CellCm);
			const float T = LenSq > 1.e-3f ? FMath::Clamp(static_cast<float>(FVector2D::DotProduct(P - A, AB) / LenSq), 0.f, 1.f) : 0.f;
			const FVector2D Away = P - (A + AB * T);
			const float D = Away.Size();
			const int32 Index = Y * SizeX + X;
			const float Shoulder = ShoulderAt(A + AB * T, Away);
			// LM4 item 3 (snow): the wall's foot steps in or out by the segment of the cell's own place along the line (0 on mud, so
			// Edge is Radius as before). Its own, not the stamp's clamped foot: a stroke's end caps reach some 24 cm along the line,
			// and the union of the cuts kept the widest of the segments within that reach (the first test read 13-17 % of the
			// outline's stations stepping), so every stamp now cuts a cell with the same offset.
			const float WallSide = WallSideOf(Away);
			const float WallOffset = bWallSteps ? WallAt(A + LineDir * FVector2D::DotProduct(P - A, LineDir), WallSide).Offset : 0.f;
			const float Edge = Radius + WallOffset;
			if (D <= Edge + Shoulder || (bWallSteps && D <= Radius))
			{
				// A continuous bowl: preserve contact depth, then ease back to ground over several cells.
				// Absolute world-seeded widths prevent repeated stamps from diffusively widening the rut.
				// LM4: inward the cut still takes the tyre's own width to the full depth (the wall's top moves in, its floor stays).
				const float Cut = (bWallSteps && D <= Radius) ? 1.f : FMath::Clamp((Edge + Shoulder - D) / Shoulder, 0.f, 1.f);
				const float Profile = Cut * Cut * (3.f - 2.f * Cut);
				// The floor is not flat: a 4-6 cell noise draws it up to FloorNoiseCm shallower here and there (never
				// deeper than the tyre, and never above the ground), and the cell is only ever lowered to it.
				// LM4 item 1: the two wavelengths are the profile's, in cells (mud's 12 and 5 as before).
				const float Softness = FMath::Clamp(0.5f + 1.4f * NoiseAt(NPocket, X, Y, PocketNoiseCells, 53), 0.f, 1.f);
				const float DepthScale = 1.f - FMath::Clamp(RutDepthVariation, 0.f, 0.5f) * (1.f - Softness);
				// LM3a: in snow the tyre sits on the ground, so the cut is to its own bottom: the sinkage plus the snow above
				// the ground here (the field is relative to the snow's top).
				const float CellCut = bSnow ? -(DepthCm + SnowTopCell(Index)) : Target;
				const float CellTarget = FMath::Min(0.f, CellCut * DepthScale + NoiseFloorCm * NoiseAt(NFloor, X, Y, FloorNoiseCells, 31)) * Profile;
				const float Before = SurfaceCm(Index);
				// LM4c item 2: what this stamp takes off the cell (its lumps, and its height down to the cut).
				const float LoweredHere = bCollapses ? LumpCm[Index] + FMath::Max(0.f, HeightCm[Index] - CellTarget) : 0.f;
				// LM2a: the capsule flattens the lumps under it. Their volume joins the stroke's displaced volume (it goes to
				// the bank like any displaced mud) and LumpCm goes to 0 here; the compaction below is HeightCm's as before.
				if (LumpCm[Index] > 0.f)
				{
					const double Lump = static_cast<double>(LumpCm[Index]) * CellAreaLump;
					Flattened += Lump;
					Removed += Lump;
					LumpCm[Index] = 0.f;
				}
				if (HeightCm[Index] > CellTarget)
				{
					Removed += (HeightCm[Index] - CellTarget) * CellArea;
					HeightCm[Index] = CellTarget;
				}
				if (bCollapses && LoweredHere >= CollapseArmMinCm)
				{
					// LM4c item 2: the cut is fresh here - a pile that lay on it is cut floor now, and a cell of the cut's outer part
					// beside the line (not ahead of the tyre) arms its wall segment's timer again (FGTMudField::ArmCollapse).
					if (bDebrisMarks)
					{
						SnowMark[Index] &= ~SnowMarkDebris;
					}
					const float LateralHere = FMath::Abs(static_cast<float>(FVector2D::CrossProduct(LineDir, P - A)));
					if (LateralHere >= FMath::Clamp(CollapseArmOut, 0.f, 1.f) * Radius)
					{
						ArmCollapse(OriginCm + A + LineDir * FVector2D::DotProduct(P - A, LineDir), LineDir, WallSide, Edge, CellTarget);
					}
				}
				Station(A + AB * T);
				const float FloorSlump = D <= Radius ? CacheSlump : 0.f;
				FloorCells.Add({ Index, CellTarget, FloorSlump, Before, static_cast<int8>(WallSide), D / Radius });
				SlumpFloorWeight += FloorSlump;
				Tracks[Index] = FMath::Max(Tracks[Index], static_cast<uint8>(FMath::RoundToInt(255.f * Profile)));
				HeadingTurns[Index] = HeadTurns;
				PhaseTurns[Index] = Wrap01((RolledCm + static_cast<float>(FVector2D::DotProduct(P - B, Head))) / LugCm);
				if (bTreadTicks)
				{
					TreadTickOf[Index] = TreadTick;   // LM3c item 1: a tyre covered it this tick, so the plough keeps its tread
				}
				continue;
			}
			const float Out = D - Edge - Shoulder;
			if (Out <= BandCm)
			{
				Station(A + AB * T);
				// Stage I1: how wide this station's bank is, and the plateau over it - smoothstep up over RidgeFootCm, a
				// flat middle, then the outer foot fading over the last RidgeFootCm. Until stage I this was a sine over
				// 40 cm, which put the whole return into a knife edge two cells wide.
				const float WidthHere = FMath::Clamp(RidgeWidthCm * (1.f + WidthWave * CacheWidthWave), 0.25f * RidgeWidthCm, BandCm);
				if (Out <= WidthHere)
				{
					const float FootCm = FMath::Clamp(RidgeFootCm, 1.f, 0.5f * WidthHere);
					const float In = FMath::Clamp(Out / FootCm, 0.f, 1.f);
					const float Down = FMath::Clamp((WidthHere - Out) / FootCm, 0.f, 1.f);
					float Weight = (In * In * (3.f - 2.f * In)) * (Down * Down * (3.f - 2.f * Down));
					// Everything that varies the bank lives in this weight and never in the height itself: the volume the
					// stamp moved is conserved and nothing can compound from stamp to stamp (stage H's crash).
					// Stage I2: the two waves along the rut, the short one weighted 0.7 and the long one 0.5. They are not a
					// partition: the long one comes through stage H's smoothing nearly whole and the short one about four
					// fifths, and the two together are the swing the crest's coefficient of variation is made of.
					Weight *= FMath::Max(0.05f, 1.f + WaveAmount * (0.7f * CacheHeightWave + 0.5f * CacheWidthWave));
					const float SideSign = FVector2D::CrossProduct(Head, Away) >= 0.f ? 1.f : -1.f;
					Weight *= FMath::Max(0.05f, 1.f + SideBias * SideSign * CacheSide);                    // one side of the tyre heavier
					Weight *= FMath::Max(0.05f, 1.f + NoiseRidge * NoiseAt(NClump, X, Y, RidgeNoiseCells, 0));   // stage H's clumps
					if (ClodChance > 0.f && 0.5f * (NoiseAt(NClod, X, Y, 1.f, 41) + 1.f) < ClodChance)
					{
						// A clod: half the local bank again, over as much of the cell as its 8-15 cm fills.
						const float ClodSizeCm = FMath::Lerp(ClodMinCm, ClodMaxCm, 0.5f * (NoiseAt(NClodSize, X, Y, 1.f, 43) + 1.f));
						Weight *= 1.f + 0.5f * FMath::Clamp(ClodSizeCm / CellCm, 0.f, 1.f);
					}
					if (bPiles)
					{
						// LM4c item 3: the cluster factor (0.2-1.8 by a 1-2.5 m world noise) at the cell's foot on the stroke's line, so
						// the lip's deposit comes in piles along the trench (the volume is normalised below: exact).
						Weight *= PileFactorReady(OriginCm + A + LineDir * FVector2D::DotProduct(P - A, LineDir));   // LM4f: ensured above
					}
					UnslumpedSum += Weight;
					Weight *= 1.f - 0.5f * CacheSlump;   // stage I2: half of a slumped stretch's bank never gets up there
					// LM2c: across the band square to the stroke's line, so the cells ahead of the tyre on its own line
					// (the rut to come) are not the lip.
					const float Lateral = FMath::Abs(static_cast<float>(FVector2D::CrossProduct(LineDir, P - A)));
					const float LipOut = Lateral - Edge - Shoulder;
					FRidgeCell& Cell = Ridge.Add_GetRef({ Index, Weight, SurfaceCm(Index), FMath::Clamp(LipOut / FMath::Max(1.f, WidthHere), 0.f, 1.f), LipOut >= 0.f, false });
					if (bWallSteps)
					{
						// LM4 item 3: a lip cell's drop is its own segment's (its foot on the line, unclamped, so a cell's
						// segment does not change from stamp to stamp as the stroke's end passes it).
						Cell.WallSide = static_cast<int8>(WallSide);
						Cell.LineFoot = A + LineDir * FVector2D::DotProduct(P - A, LineDir);
						bool bDrop = false;
						uint64 Key = 0;
						float DropW = 0.f;
						WallOffsetAt(Cell.LineFoot + OriginCm, WallLine, WallSide, bDrop, Key, &DropW);
						Cell.bDrop = bDrop && Cell.bLip;
						Cell.DropW = Cell.bLip ? DropW : 0.f;
						Cell.WallKey = Key;
					}
					WeightSum += Weight;
					// A ragged churn boundary across the tyre's edge, not a straight band (LM4 item 1: TracksEdgeCells, mud's 3).
					const float Ragged = FMath::Clamp((1.f - Out / WidthHere) * (1.f + NoiseRidge * NoiseAt(NTracksEdge, X, Y, TracksEdgeCells, 7)), 0.f, 1.f);
					Tracks[Index] = FMath::Max(Tracks[Index], static_cast<uint8>(FMath::RoundToInt(255.f * Ragged)));
				}
			}
			if (Out <= SlideWidthCm && D > KINDA_SMALL_NUMBER && SegLenM > 0.f)
			{
				const FVector2f Push = FVector2f(Away / D) * (SlideCmPerMetre * SegLenM * (1.f - Out / SlideWidthCm));
				FVector2f& Offset = OffsetCm[Index];
				const float Before = Offset.Size();
				Offset += Push;
				const float Size = Offset.Size();
				// The cap falls off with the distance like the push does, so the slide is at most a ramp from MaxSlideCm at the
				// tyre's edge to nothing at SlideWidthCm (a slope of 1/3): a flat cap let a long drive pile the outer cells on
				// top of each other (20 cm of push over the last 20 cm), which folded the mesh's triangles there and showed
				// their backs as black strips along the band. A stamp never undoes a nearer stamp's slide (Before).
				const float Cap = FMath::Max(Before, MaxSlideCm * (1.f - Out / SlideWidthCm));
				if (Size > Cap)
				{
					Offset *= Cap / Size;
				}
			}
		}
	}
	float SlumpVolume = 0.f;   // stage I2: what the slumped stretches kept out of the bank, to settle in the rut below
	// LM4 items 2 and 3: what fell from the lip into the trench on each world side (cm^3), the segments that dropped (their
	// key, their foot on the line, their side), the plates' rewritten cells' box and their excess (LM2a's same-cell rule).
	double DropCm3[2] = { 0.0, 0.0 };
	struct FDrop
	{
		uint64 Key = 0;
		FVector2D Foot = FVector2D::ZeroVector;
		int8 Side = 0;
	};
	TArray<FDrop, TInlineAllocator<4>> Drops;
	int32 PlateX0 = X0, PlateY0 = Y0, PlateX1 = X1, PlateY1 = Y1;
	double PlateExcessCm3 = 0.0;
	if (Removed > 0.0)
	{
		// LM2a, the throw: ThrowShare of the bank's deposit is returned instead of deposited (0: exactly as before).
		const float Throw = FMath::Clamp(ThrowShare, 0.f, 1.f);
		if (Throw > 0.f)
		{
			OutThrownCm3 = static_cast<double>(RidgeReturn) * Removed * Throw;
			Book.ThrownCm3 += OutThrownCm3;
		}
		const float Volume = Throw > 0.f ? RidgeReturn * static_cast<float>(Removed) * (1.f - Throw) : RidgeReturn * static_cast<float>(Removed);
		Book.DepositCm3 += Volume;
		Book.FlattenedCm3 += Flattened;
		if (UnslumpedSum > 0.f)
		{
			// Normalised by the weight before the slump took its share, so what slumps really leaves the bank instead
			// of being handed to the cells beside it.
			SlumpVolume = Volume * FMath::Max(0.f, UnslumpedSum - WeightSum) / UnslumpedSum;
			// LM2a, the lumps: the cells that take a deposit below (not a rut, not at the cap), as they stand before it,
			// their share of the band's weight, and the lump weight W over them. LumpShare of what those cells would
			// take is held back and spread over them by W, normalised so the held volume is exactly what lands.
			TArray<int32, TInlineAllocator<512>> Eligible;
			double EligibleWeight = 0.0;
			double LumpWeightSum = 0.0;
			double LumpFullSum = 0.0;      // LM2c follow-up: the full site set's weight over the same cells
			for (FRidgeCell& Cell : Ridge)
			{
				const float Height = HeightCm[Cell.Index];
				// LM3a: in snow only the lip takes the deposit (the band's cells beside the stroke's line, not the ones ahead
				// of the tyre on its own line, which it is about to cut again, nor its own trench behind it).
				if (Height >= -1.f && Height < MaxRidgeCm && (!bSnow || Cell.bLip))
				{
					Cell.bEligible = true;
					EligibleWeight += Cell.Weight;
					if (bLumps)
					{
						Eligible.Add(Cell.Index);
						LumpWeightSum += LumpW[Cell.Index];
						LumpFullSum += LumpWFull.IsValidIndex(Cell.Index) ? LumpWFull[Cell.Index] : LumpW[Cell.Index];
					}
				}
			}
			const float LumpK = (bLumps && LumpWeightSum > 0.0) ? FMath::Clamp(LumpShare, 0.f, 1.f) : 0.f;
			// LM2c follow-up (the main session): the held share scales with the lump weight that exists over these cells
			// against what the full site set would give, so an absent site's share stays in the bank (HeightCm) and the
			// domes that exist keep the heights a full set would give them (LumpShare x handed x W / sum of the full W)
			// instead of piling to the cap. LM2c off: LM2a's LumpK exactly.
			const float HeldShare = (bLumpVariety && LumpFullSum > 0.0) ? LumpK * static_cast<float>(FMath::Min(1.0, LumpWeightSum / LumpFullSum)) : LumpK;
			const float BankVolume = HeldShare > 0.f ? Volume * (1.f - HeldShare) : Volume;
			// LM3a: snow hands the whole return to the eligible lip cells (normalised over their weight, so RidgeReturn of the
			// cut lands exactly: the compaction row), where mud hands each band cell its share of the whole band as before
			// (a rut cell's or a capped cell's share is not deposited). With no eligible lip cell the return is lost (booked).
			const double Norm = bSnow ? EligibleWeight : static_cast<double>(UnslumpedSum);
			const double Handed = bSnow ? (EligibleWeight > 0.0 ? static_cast<double>(Volume) : 0.0) : static_cast<double>(Volume) * EligibleWeight / UnslumpedSum;
			if (bSnow && EligibleWeight <= 0.0)
			{
				SnowBankLostCm3 += Volume;
			}
			Book.HandedCm3 += Handed;
			for (const FRidgeCell& Cell : Ridge)
			{
				float& Height = HeightCm[Cell.Index];
				// A following stamp's broad bank must not rebuild an already compacted shoulder/floor.
				// Slump inside the current cut is handled separately with an absolute bounded target.
				if (Height < -1.f) continue;
				if (bSnow && !Cell.bEligible) continue;   // LM3a: the lip only, as weighed above
				if (Height < MaxRidgeCm)
				{
					const float Add = BankVolume * Cell.Weight / (static_cast<float>(Norm) * CellArea);
					// Stage I: a cell that is already somebody's rut takes only RidgeFillShare of it (the 90 cm band
					// reaches across the next pass's rut, and filling it in undid the ruts the traction reads).
					const float Fill = Height < -1.f ? FMath::Clamp(RidgeFillShare, 0.f, 1.f) : 1.f;
					const float Old = Height;
					// Stage H: max plus a fraction of the lesser where a hump already stands, instead of the sum that
					// piled two humps into a spike (Blend 1.0 is that sum exactly, which is how the test measures
					// "before"). A cell that is really a rut floor (a neighbouring pass cut it) keeps the sum: taking
					// the max there would raise the floor and undo the compaction.
					Height = (Height <= 0.f) ? FMath::Min(MaxRidgeCm, Height + Add * Fill)
											 : FMath::Min(MaxRidgeCm, FMath::Max(Height, Add) + Blend * FMath::Min(Height, Add));
					Book.BankAskedCm3 += static_cast<double>(Add) * CellArea;
					Book.BankAddedCm3 += static_cast<double>(Height - Old) * CellArea;
				}
			}
			double OverflowCm3 = 0.0;   // LM3c follow-up: what the lumps could not hold, back to the band below
			const bool bMarksHere = SnowMark.Num() == SizeX * SizeY;
			if (LumpK > 0.f && LumpsShaped())
			{
				// LM4 items 2 and 3 (snow), crust plates: the held share lands flat on the plates' cells by W (LM2a's
				// normalisation), then each plate it touched is re-levelled to its tilted plane (ReshapePlates); what the clamp
				// cannot hold is the band's, as LM3c's overflow. A lip cell beside a wall segment that drops its plate (or one
				// whose plate already fell) takes none: its share and what plate it held go into the trench, onto the floor
				// cells beside that wall, and the cell is marked so no plate forms there again.
				// LM4b items 2 and 3: the soft domes the same way (ReshapeDomes: each touched dome back to its own kernel), and
				// the notch's ends feathered - a lip cell within the feather drops only its share DropW of what lands on it, and
				// the dome re-shape keeps 1 - DropW of its kernel there (LipDropShare, the largest share it has seen).
				const double Held = static_cast<double>(HeldShare) * Handed;
				Book.LumpHeldCm3 += Held;
				TArray<int32, TInlineAllocator<32>> Touched;
				const bool bShares = LipDropShare.Num() == SizeX * SizeY;
				for (const FRidgeCell& Cell : Ridge)
				{
					if (!Cell.bEligible)
					{
						continue;
					}
					const float W = LumpW[Cell.Index];
					float Add = (W > 0.f && LumpWeightSum > 0.0) ? static_cast<float>(Held * W / (LumpWeightSum * CellArea)) : 0.f;
					const bool bMarked = bMarksHere && (SnowMark[Cell.Index] & SnowMarkDropped);
					const float DropW = bWallSteps ? (bMarked ? 1.f : FMath::Clamp(Cell.DropW, 0.f, 1.f)) : 0.f;
					const bool bDropped = DropW >= 0.999f;
					if (!bDropped && DropW > 0.f)
					{
						// LM4b: the feather - DropW of this stamp's share falls (onto the floor beside that wall), the rest lands.
						const double Fell = static_cast<double>(DropW) * Add * CellArea;
						DropCm3[Cell.WallSide > 0 ? 1 : 0] += Fell;
						Book.LumpLandedCm3 += Fell;
						Add *= 1.f - DropW;
						if (bShares)
						{
							LipDropShare[Cell.Index] = FMath::Max(LipDropShare[Cell.Index], static_cast<uint8>(FMath::RoundToInt(255.f * DropW)));
						}
						if (Cell.bDrop && !Drops.ContainsByPredicate([&Cell](const FDrop& Drop) { return Drop.Key == Cell.WallKey; }))
						{
							Drops.Add({ Cell.WallKey, Cell.LineFoot, Cell.WallSide });
						}
					}
					if (bDropped)
					{
						const double Fell = (static_cast<double>(Add) + LumpCm[Cell.Index]) * CellArea;
						if (Fell > 0.0)
						{
							DropCm3[Cell.WallSide > 0 ? 1 : 0] += Fell;
							Book.LumpLandedCm3 += static_cast<double>(Add) * CellArea;   // the held share lands, on the floor below
						}
						LumpCm[Cell.Index] = 0.f;
						if (bMarksHere)
						{
							SnowMark[Cell.Index] |= SnowMarkDropped;
						}
						if (Cell.bDrop && !Drops.ContainsByPredicate([&Cell](const FDrop& Drop) { return Drop.Key == Cell.WallKey; }))
						{
							Drops.Add({ Cell.WallKey, Cell.LineFoot, Cell.WallSide });
						}
						continue;
					}
					if (Add <= 0.f)
					{
						continue;
					}
					LumpCm[Cell.Index] += Add;
					Book.LumpLandedCm3 += static_cast<double>(Add) * CellArea;
					if (LumpSiteOf[Cell.Index] != INDEX_NONE)
					{
						Touched.AddUnique(LumpSiteOf[Cell.Index]);
					}
				}
				if (Touched.Num() > 0)
				{
					const double Over = ReshapeLumps(Touched, PlateX0, PlateY0, PlateX1, PlateY1);
					Book.LumpOverflowCm3 += Over;
					Book.LumpLandedCm3 -= Over;
					if (bLumpOverflowToBand)
					{
						OverflowCm3 += Over;
					}
					else
					{
						PlateExcessCm3 += Over;   // LM2a's rule: into the band's eligible cells' banks below, evenly
					}
				}
			}
			else if (LumpK > 0.f)
			{
				const double Held = static_cast<double>(HeldShare) * Handed;
				Book.LumpHeldCm3 += Held;
				// LM2b's bank clods at the lump sites' tops (LM2c off only; with it on they come from the lip's cells below).
				const bool bSites = !bLumpVariety && bQueueClods && SitePeak.Num() == LumpSitesX * LumpSitesY && LumpSitesX > 0;
				for (const int32 Index : Eligible)
				{
					const float W = LumpW[Index];
					if (W <= 0.f)
					{
						continue;
					}
					const float Add = static_cast<float>(Held * W / (LumpWeightSum * CellArea));
					const float Over = bLumpOverflowToBand ? AddLumpCapped(Index, Add) : AddLump(Index, Add);
					OverflowCm3 += static_cast<double>(Over) * CellArea;
					Book.LumpOverflowCm3 += static_cast<double>(Over) * CellArea;
					Book.LumpLandedCm3 += static_cast<double>(Add - Over) * CellArea;
					// LM2b: a lump site whose dome top took ClodBankMinCm since its last roll rolls for a bank clod, at
					// most once per ClodRespawnS; larger with the stamp's depth.
					const int32 Site = LumpSiteOf[Index];
					if (bSites && Site != INDEX_NONE && SitePeak[Site] == Index)
					{
						SiteLumpCm[Site] += Add;
						if (SiteLumpCm[Site] >= ClodBankMinCm)
						{
							SiteLumpCm[Site] = 0.f;
							if (ClockS - SiteClodS[Site] >= ClodRespawnS)
							{
								++ClodRolls;
								const float Roll = 0.5f * (HashLattice(Site, static_cast<int32>(ClodRolls), NoiseSeed + 71) + 1.f);
								if (Roll < ClodBankChance)
								{
									SiteClodS[Site] = ClockS;
									const float Deep = FMath::Clamp(DepthCm / FMath::Max(1.f, ClodBankFullDepthCm), 0.f, 1.f);
									const float Size = FMath::Clamp(FMath::Lerp(ClodBankMinSizeCm, ClodBankMaxSizeCm, Deep)
										* (1.f + 0.15f * HashLattice(Site, static_cast<int32>(ClodRolls), NoiseSeed + 73)), ClodBankMinSizeCm, ClodBankMaxSizeCm);
									FClodSpawn Spawn;
									Spawn.XYCm = LumpSiteCentreCm(Site);
									Spawn.SizeCm = Size;
									Spawn.Seed = static_cast<int32>(Site * 7919u + ClodRolls * 104729u);
									Spawn.Source = 0;
									QueueClod(Spawn);
								}
							}
						}
					}
				}
			}
			// LM3c follow-up: the lumps' overflow goes into the band's cells that took this stamp's deposit (the eligible
			// ones), by the weights the bank's plain deposit used, normalised over them so the volume is exact: the bank's
			// shape, not a spike in the lump's own cell. Added as it is (no blend, no cap), so nothing of it is lost.
			if (bLumpOverflowToBand && OverflowCm3 > 0.0 && EligibleWeight > 0.0)
			{
				for (const FRidgeCell& Cell : Ridge)
				{
					if (Cell.bEligible)
					{
						HeightCm[Cell.Index] += static_cast<float>(OverflowCm3 * Cell.Weight / (EligibleWeight * CellArea));
					}
				}
			}
			if (PlateExcessCm3 != 0.0 && EligibleWeight > 0.0)
			{
				for (const FRidgeCell& Cell : Ridge)
				{
					if (Cell.bEligible)
					{
						HeightCm[Cell.Index] += static_cast<float>(PlateExcessCm3 * Cell.Weight / (EligibleWeight * CellArea));
					}
				}
			}
			// LM4 item 3: what fell from a dropping segment's lip lands on the trench floor beside that wall - the floor cells
			// of this stamp on that side, the outer 60 % of the tyre's half width (lumps over LumpMaxCm into the same cell's
			// height, exact) - with a floor chunk once per segment (FloorChunkChance, a hash of the segment). With no floor cell
			// on that side the volume goes back to the lip's eligible cells' banks, so nothing is lost.
			for (int32 SideBin = 0; SideBin < 2; ++SideBin)
			{
				if (DropCm3[SideBin] <= 0.0)
				{
					continue;
				}
				const int8 Side = SideBin == 1 ? 1 : -1;
				int32 Under = 0;
				for (const FFloorCell& Floor : FloorCells)
				{
					Under += (Floor.WallSide == Side && Floor.Out >= 0.4f && Floor.Out <= 1.f) ? 1 : 0;
				}
				if (Under > 0)
				{
					const float Each = static_cast<float>(DropCm3[SideBin] / (Under * static_cast<double>(CellArea)));
					for (const FFloorCell& Floor : FloorCells)
					{
						if (Floor.WallSide == Side && Floor.Out >= 0.4f && Floor.Out <= 1.f)
						{
							AddLump(Floor.Index, Each);
						}
					}
					++WallDrops;
					WallDropCm3 += DropCm3[SideBin];
				}
				else if (EligibleWeight > 0.0)
				{
					for (const FRidgeCell& Cell : Ridge)
					{
						if (Cell.bEligible)
						{
							HeightCm[Cell.Index] += static_cast<float>(DropCm3[SideBin] * Cell.Weight / (EligibleWeight * CellArea));
						}
					}
				}
			}
			if (bQueueClods && FloorChunkChance > 0.f)
			{
				const float SizeMin = FMath::Max(1.f, ClodBankSizeMinCm);
				const float SizeMax = FMath::Max(SizeMin, ClodBankSizeMaxCm);
				for (const FDrop& Drop : Drops)
				{
					if (FloorChunkKeys.Contains(Drop.Key))
					{
						continue;
					}
					FloorChunkKeys.Add(Drop.Key);
					const int32 KA = static_cast<int32>(Drop.Key >> 32);
					const int32 KB = static_cast<int32>(Drop.Key & 0xFFFFFFFFu);
					if (0.5f * (HashLattice(KA, KB, NoiseSeed + 241) + 1.f) >= FloorChunkChance)
					{
						continue;
					}
					// On the floor beside the wall it fell from: the foot on the line out 0.6 of the tyre's half width to that side.
					const FVector2D SideDir = bWallAlongX ? FVector2D(0.0, Drop.Side) : FVector2D(Drop.Side, 0.0);
					const float USize = 0.5f * (HashLattice(KA, KB, NoiseSeed + 243) + 1.f);
					FClodSpawn Spawn;
					Spawn.XYCm = OriginCm + Drop.Foot + SideDir * (0.6f * Radius);
					Spawn.SizeCm = SizeMin + (SizeMax - SizeMin) * FMath::Pow(USize, FMath::Max(0.1f, ClodSizePower));
					Spawn.Seed = static_cast<int32>(static_cast<uint32>(KA) * 7919u + static_cast<uint32>(KB) * 104729u + static_cast<uint32>(NoiseSeed) * 15485863u);
					Spawn.Source = 3;
					Spawn.HeadingDeg = FMath::RadiansToDegrees(static_cast<float>(FMath::Atan2(Head.Y, Head.X)));
					Spawn.bHeading = true;
					QueueClod(Spawn);
					++FloorChunksQueued;
				}
			}
			// LM2c: the bank clods from random cells of the lip (the band's inner ClodBankInner beside the rut), each with
			// the chance ClodBankPerCm x what the cell took this stamp (the bank and its lumps, cm) x the cluster weight, so
			// they bunch where the lumps bunch and the chance does not depend on how finely the wheel's travel is stamped.
			// A hash of the cell and the stamp's step decides, the spot in the cell and the size (power law) the same.
			if (bLumpVariety && bLumps && bQueueClods && ClodBankPerCm > 0.f)
			{
				++StampSteps;
				const double HeldPerW = (HeldShare > 0.f && LumpWeightSum > 0.0) ? static_cast<double>(HeldShare) * Handed / (LumpWeightSum * CellArea) : 0.0;
				const float SizeMin = FMath::Max(1.f, ClodBankSizeMinCm);
				const float SizeMax = FMath::Max(SizeMin, ClodBankSizeMaxCm);
				const int32 Step = static_cast<int32>(StampSteps);
				// LM4 item 4: per 12.5 cm cell's area (1 on mud), so the count per metre does not depend on the grid.
				const float AreaScale = ClodAreaScale();
				const float HeadDeg = FMath::RadiansToDegrees(static_cast<float>(FMath::Atan2(Head.Y, Head.X)));
				// LM4f item 4: the cluster noise from its slot (LumpClusterWeight's values).
				const float* NCluster = (bLumpVariety && LumpClusterT >= -1.5f) ? NoiseCells(NoiseCluster, FMath::Max(1.f, LumpClusterCm / CellCm), 79) : nullptr;
				for (const FRidgeCell& Cell : Ridge)
				{
					if (!Cell.bEligible || !Cell.bLip || Cell.BandT > ClodBankInner)
					{
						continue;
					}
					const int32 X = Cell.Index % SizeX;
					const int32 Y = Cell.Index / SizeX;
					if (LumpsShaped())
					{
						// LM4 item 4: snow's chunks break off the plates' edges (LM4b: the soft domes' edges) (a plate cell with a 4-neighbour in another
						// plate or a gap), never where the lip's plate fell in.
						const int32 Site = LumpSiteOf[Cell.Index];
						if (Site == INDEX_NONE || (bMarksHere && (SnowMark[Cell.Index] & SnowMarkDropped)) || (bWallSteps && Cell.bDrop))
						{
							continue;
						}
						const bool bEdge = (X > 0 && LumpSiteOf[Cell.Index - 1] != Site) || (X < SizeX - 1 && LumpSiteOf[Cell.Index + 1] != Site)
							|| (Y > 0 && LumpSiteOf[Cell.Index - SizeX] != Site) || (Y < SizeY - 1 && LumpSiteOf[Cell.Index + SizeX] != Site);
						if (!bEdge)
						{
							continue;
						}
					}
					const float Cluster = LumpClusterWeightFrom(NCluster, X, Y);
					if (Cluster <= 0.f)
					{
						continue;
					}
					const float Deposit = BankVolume * Cell.Weight / (static_cast<float>(Norm) * CellArea) + static_cast<float>(HeldPerW * LumpW[Cell.Index]);
					ClodBankExpectPerRate += static_cast<double>(Deposit) * Cluster;
					const float Chance = ClodBankPerCm * Deposit * Cluster * AreaScale;
					if (0.5f * (HashLattice(Cell.Index, Step, NoiseSeed + 101) + 1.f) >= Chance)
					{
						continue;
					}
					++ClodRolls;
					const float USize = 0.5f * (HashLattice(Cell.Index, Step, NoiseSeed + 103) + 1.f);
					FClodSpawn Spawn;
					Spawn.XYCm = OriginCm + FVector2D(X + 0.5f + 0.5f * HashLattice(Cell.Index, Step, NoiseSeed + 105), Y + 0.5f + 0.5f * HashLattice(Cell.Index, Step, NoiseSeed + 107)) * CellCm;
					Spawn.SizeCm = SizeMin + (SizeMax - SizeMin) * FMath::Pow(USize, FMath::Max(0.1f, ClodSizePower));
					Spawn.Seed = static_cast<int32>(static_cast<uint32>(Cell.Index) * 7919u + static_cast<uint32>(Step) * 104729u + static_cast<uint32>(NoiseSeed) * 15485863u);
					Spawn.Source = 0;
					Spawn.HeadingDeg = HeadDeg;   // LM4: the shards' yaw runs along the lip
					Spawn.bHeading = true;
					QueueClod(Spawn);
					++LipChunksQueued;
				}
			}
		}
		LoweredCm3 += Removed;
	}
	// Stage H: a 3-tap mean along the stamp's own direction over the cells it touched, so successive stamps leave one
	// crest and one floor instead of a row of humps and a row of steps. The neighbours are read before anything is
	// written (a sequential pass would smear the stamp along itself), and a cell is only ever averaged with the cells
	// of the same kind in this same stamp: a crest cell with the crest cells beside it, a floor cell with the floor.
	// Both of those matter. The first cut let a crest cell take whatever lay beside it, so the cells the wheel was
	// about to drive into (they are crest cells of every tick until the tyre arrives) were dragged down toward the rut
	// behind them tick after tick. The second cut kept the old rule that a stamp may never raise what a wheel cut, as
	// a min() on the result, and a smoothing that may only lower is a ratchet: at a hundred stamps a second every cell
	// within reach fell to the deepest one around it, the rut came out 75 cm wide at -41 cm with its crest inside it
	// (the escape's ridge mean -12.4 cm, 2 of 92 over 3) and the floor's own noise was eaten. So the mean is a plain
	// mean here, and compaction is kept the other way about: a floor cell may not come out above the depth this stamp
	// cut it to, so the next pass down the same line still finds nothing to remove.
	// The crest's randomness (H2) stays in the volume of each hump. Pulling the cell toward a *noised* mean instead was
	// tried and is unstable: a clump of cells whose noise is positive pulls itself up by (1 + RidgeSmooth x RidgeNoise)
	// every stamp, which is geometric - the crest reached infinity inside ten seconds of crawling, the field's gradient
	// came out NaN, the traction pushed a NaN at the chassis and Chaos died indexing its slip table with it.
	if (Smooth > 0.f && (Ridge.Num() > 0 || FloorCells.Num() > 0))
	{
		const int32 DX = FMath::RoundToInt(Head.X);   // the lattice neighbour along the heading (|Head| = 1, so never 0,0)
		const int32 DY = FMath::RoundToInt(Head.Y);
		TArray<TPair<int32, float>> Writes;
		Writes.Reserve(Ridge.Num() + FloorCells.Num());
		auto SameKind = [&](int32 Index, bool bFloorKind) -> bool
		{
			const FVector2D P(((Index % SizeX) + 0.5f) * CellCm, ((Index / SizeX) + 0.5f) * CellCm);
			const float T = LenSq > 1.e-3f ? FMath::Clamp(static_cast<float>(FVector2D::DotProduct(P - A, AB) / LenSq), 0.f, 1.f) : 0.f;
			const FVector2D Away = P - (A + AB * T);
			const float D = Away.Size();
			// LM4 item 3: the wall's step at the cell's own place along the line (0 on mud).
			const float Step = bWallSteps ? WallAt(A + LineDir * FVector2D::DotProduct(P - A, LineDir), WallSideOf(Away)).Offset : 0.f;
			const float Edge = Radius + Step + ShoulderAt(A + AB * T, Away);
			return bFloorKind ? (D <= Edge) : (D > Edge && D <= Edge + BandCm);
		};
		auto Mean3 = [&](int32 Index, bool bFloorKind) -> float
		{
			float Sum = HeightCm[Index];
			int32 Count = 1;
			for (int32 Sign = -1; Sign <= 1; Sign += 2)
			{
				const int32 NX = (Index % SizeX) + Sign * DX;
				const int32 NY = (Index / SizeX) + Sign * DY;
				if (NX < 0 || NY < 0 || NX >= SizeX || NY >= SizeY)
				{
					continue;
				}
				const int32 NeighbourIndex = NY * SizeX + NX;
				if (SameKind(NeighbourIndex, bFloorKind))
				{
					Sum += HeightCm[NeighbourIndex];
					++Count;
				}
			}
			return Sum / Count;
		};
		for (const FRidgeCell& Cell : Ridge)
		{
			const float Current = HeightCm[Cell.Index];
			if (Current < -1.f) continue; // do not diffuse a previous rut upward into this stamp's bank
			if (bKeepBerms && (SnowMark[Cell.Index] & SnowMarkBerm)) continue;   // LM3c: the plough's berm keeps its crumbs
			// LM3a: in snow the cap does not clip a cell that already stands over it (the belly plough's berm, PloughReturn of
			// what it cut, would otherwise be cut back to MaxRidgeCm by the tyres' next stamps and its volume lost); mud as before.
			const float SmoothCap = bSnow ? FMath::Max(MaxRidgeCm, Current) : MaxRidgeCm;
			float Value = FMath::Min(FMath::Lerp(Current, Mean3(Cell.Index, false), Smooth), SmoothCap);
			if (Current < 0.f)
			{
				Value = FMath::Min(Value, 0.f);   // a crest cell that is really a rut may slump toward the ground, never above it
			}
			Writes.Emplace(Cell.Index, Value);
		}
		for (const FFloorCell& Cell : FloorCells)   // the cell and the depth this stamp cut it to
		{
			// LM3a: snow's floor is the tyre's packed bottom (its pockets the only variation): no smoothing there, which
			// would lower a cell toward a deeper neighbour without the volume being counted as cut.
			if (bSnow)
			{
				break;
			}
			// The capsule's trailing feather gets shallower as the wheel moves away. It cannot lift
			// a deeper cut left by its contact area; smoothing applies only to the current cut.
			if (HeightCm[Cell.Index] < Cell.TargetCm - 0.01f) continue;
			Writes.Emplace(Cell.Index, FMath::Min(FMath::Lerp(HeightCm[Cell.Index], Mean3(Cell.Index, true), Smooth), Cell.TargetCm));
		}
		for (const TPair<int32, float>& Write : Writes)
		{
			HeightCm[Write.Key] = Write.Value;
		}
	}
	// Stage I2, the slump's other half: RidgeSlumpFloor of the mud that did not make it up the bank settles on the rut
	// floor under that stretch, shared by how slumped each floor cell's station is. This is the only place a stamp
	// raises a floor, and it is written as an absolute (the depth this stamp cut plus the rise, never above the
	// ground), so a hundred stamps a second cannot walk it upward - stage H's lesson about anything that compounds.
	// It comes after the smoothing, whose floor cells are bounded by that same cut depth.
	if (SlumpVolume > 0.f && SlumpFloorWeight > 0.f)
	{
		const float RisePerWeight = FMath::Min(FMath::Max(0.f, RidgeSlumpRiseMaxCm),
			FMath::Clamp(RidgeSlumpFloor, 0.f, 1.f) * SlumpVolume / (SlumpFloorWeight * CellArea));
		for (const FFloorCell& Cell : FloorCells)
		{
			if (Cell.Slump > 0.f && HeightCm[Cell.Index] >= Cell.TargetCm - 0.01f)
			{
				HeightCm[Cell.Index] = FMath::Min(0.f, FMath::Max(HeightCm[Cell.Index], Cell.TargetCm + RisePerWeight * Cell.Slump));
			}
		}
	}
	// LM1: every cell this stamp wrote (the capsule, the shoulders and the band) starts setting, is fresh where it moved,
	// and its tiles wake. Only the new arrays are written here: the heights, offsets, tracks and tread are as before.
	for (const FFloorCell& Cell : FloorCells)
	{
		TouchCell(Cell.Index, Cell.Before);
	}
	for (const FRidgeCell& Cell : Ridge)
	{
		TouchCell(Cell.Index, Cell.Before);
	}
	// LM4 item 2: the plates it re-levelled can reach past the stamp's own box (PlateX0..PlateY1 start as that box).
	WakeTiles(PlateX0, PlateY0, PlateX1, PlateY1);
	MarkDirty(PlateX0, PlateY0, PlateX1 + 1, PlateY1 + 1);
	return Removed;
}

double FGTMudField::StampBelly(const FVector2D& CentreCm, const FVector2D& Forward, float LengthCm, float WidthCm, float DepthCm)
{
	const FOuterCall Call(*this);   // LM4e
	Call.Record(EventStampBelly, { CentreCm.X, CentreCm.Y, Forward.X, Forward.Y, LengthCm, WidthCm, DepthCm });
	if (!IsValid() || DepthCm <= 0.f || LengthCm <= 0.f || WidthCm <= 0.f)
	{
		return 0.0;
	}
	const FVector2D F = Forward.GetSafeNormal();
	if (F.IsNearlyZero())
	{
		return 0.0;
	}
	const FVector2D R(-F.Y, F.X);
	const float Feather = FMath::Max(CellCm * 2.f, BellyFeatherCm);
	const float Reach = 0.5f * FMath::Sqrt(LengthCm * LengthCm + WidthCm * WidthCm) + Feather;
	const FVector2D C = CentreCm - OriginCm;
	if (C.X + Reach < 0.f || C.Y + Reach < 0.f || C.X - Reach > SizeX * CellCm || C.Y - Reach > SizeY * CellCm)
	{
		return 0.0;
	}
	const int32 X0 = FMath::Clamp(FMath::FloorToInt((C.X - Reach) / CellCm), 0, SizeX - 1);
	const int32 Y0 = FMath::Clamp(FMath::FloorToInt((C.Y - Reach) / CellCm), 0, SizeY - 1);
	const int32 X1 = FMath::Clamp(FMath::CeilToInt((C.X + Reach) / CellCm), 0, SizeX - 1);
	const int32 Y1 = FMath::Clamp(FMath::CeilToInt((C.Y + Reach) / CellCm), 0, SizeY - 1);
	const float CellArea = CellCm * CellCm;
	const float Target = -DepthCm;
	double Removed = 0.0;
	for (int32 Y = Y0; Y <= Y1; ++Y)
	{
		for (int32 X = X0; X <= X1; ++X)
		{
			const FVector2D P = FVector2D((X + 0.5f) * CellCm, (Y + 0.5f) * CellCm) - C;
			const float Along = FMath::Max(0.f, static_cast<float>(FMath::Abs(FVector2D::DotProduct(P, F))) - LengthCm * 0.5f);
			const float Across = FMath::Max(0.f, static_cast<float>(FMath::Abs(FVector2D::DotProduct(P, R))) - WidthCm * 0.5f);
			const float Distance = FMath::Sqrt(Along * Along + Across * Across);
			if (Distance >= Feather)
			{
				continue;
			}
			const int32 Index = Y * SizeX + X;
			const float Cut = 1.f - Distance / Feather;
			const float Profile = Cut * Cut * (3.f - 2.f * Cut);
			const float SoftTarget = Target * Profile;
			const float Before = SurfaceCm(Index);
			// LM2a: the belly flattens the lumps under its box as a capsule does (their volume is what it displaced).
			if (LumpCm[Index] > 0.f)
			{
				const double Lump = static_cast<double>(LumpCm[Index]) * CellArea;
				Removed += Lump;
				Book.FlattenedCm3 += Lump;
				LumpCm[Index] = 0.f;
			}
			if (HeightCm[Index] > SoftTarget)
			{
				Removed += (HeightCm[Index] - SoftTarget) * CellArea;
				HeightCm[Index] = SoftTarget;
			}
			Tracks[Index] = FMath::Max(Tracks[Index], static_cast<uint8>(FMath::RoundToInt(255.f * Profile)));
			TouchCell(Index, Before);   // LM1: setting, fresh where it moved
		}
	}
	LoweredCm3 += Removed;
	WakeTiles(X0, Y0, X1, Y1);
	MarkDirty(X0, Y0, X1 + 1, Y1 + 1);
	return Removed;
}
