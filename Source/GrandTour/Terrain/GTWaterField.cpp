#include "Terrain/GTWaterField.h"

namespace
{
	constexpr float GTWaterGravity = 9.81f;

	/** Bilinear over cell centres, the edge value outside (FGTMudField's sampler, kept in step with it). */
	template <typename F>
	float BilinearCells(const FVector2D& FieldCm, float CellCm, int32 SizeX, int32 SizeY, F&& Get)
	{
		const float GX = static_cast<float>(FieldCm.X) / CellCm - 0.5f;
		const float GY = static_cast<float>(FieldCm.Y) / CellCm - 0.5f;
		const int32 X0 = FMath::Clamp(FMath::FloorToInt(GX), 0, SizeX - 1);
		const int32 Y0 = FMath::Clamp(FMath::FloorToInt(GY), 0, SizeY - 1);
		const int32 X1 = FMath::Min(X0 + 1, SizeX - 1);
		const int32 Y1 = FMath::Min(Y0 + 1, SizeY - 1);
		const float FX = FMath::Clamp(GX - X0, 0.f, 1.f);
		const float FY = FMath::Clamp(GY - Y0, 0.f, 1.f);
		return FMath::Lerp(FMath::Lerp(Get(Y0 * SizeX + X0), Get(Y0 * SizeX + X1), FX),
			FMath::Lerp(Get(Y1 * SizeX + X0), Get(Y1 * SizeX + X1), FX), FY);
	}
}

void FGTWaterField::Init(const FVector2D& CentreCm, const FVector2D& FlowDirWorld, float HalfSpanAlongCm, float HalfSpanAcrossCm,
	float InCellCm, float InLevelCm, const TFunction<float(const FVector2D&)>& BedSamplerCm)
{
	CellCm = FMath::Max(1.f, InCellCm);
	RiverDepthM.Reset();
	RiverFluxX.Reset(); RiverFluxY.Reset();
	AxisX = FlowDirWorld.IsNearlyZero() ? FVector2D(1.0, 0.0) : FlowDirWorld.GetSafeNormal();
	AxisY = FVector2D(-AxisX.Y, AxisX.X);
	SizeX = FMath::Clamp(FMath::CeilToInt(FMath::Max(1.f, 2.f * HalfSpanAlongCm) / CellCm), 2, 2048);
	SizeY = FMath::Clamp(FMath::CeilToInt(FMath::Max(1.f, 2.f * HalfSpanAcrossCm) / CellCm), 2, 2048);
	OriginCm = CentreCm - AxisX * (SizeX * CellCm * 0.5) - AxisY * (SizeY * CellCm * 0.5);
	LevelCm = InLevelCm;
	AppliedHeadDropCm = HeadDropCm;
	// RIVERBED S3: no basin until the sheet sets one (SetBasinFrom): every cell under the level fills, as before.
	Basin.Reset();
	BasinCells = 0;

	const int32 Count = SizeX * SizeY;
	BedCm.SetNumUninitialized(Count);
	DepthM.SetNumUninitialized(Count);
	FluxX.Init(0.f, Count);
	FluxY.Init(0.f, Count);
	SurfaceCm.SetNumUninitialized(Count);
	VelXMps.Init(0.f, Count);
	VelYMps.Init(0.f, Count);
	// WS2: the lids start empty (nothing is in the water until a car stamps one).
	LidM.Init(0.f, Count);
	LidNextM.Init(0.f, Count);
	LidDirty.Init(0, Count);
	LidFilled.Init(0, Count);
	LidDirtyCells.Reset();
	LidCells.Reset();
	WindPhase = 0.f;
	WindCarry = 0.f;
	RainCarry = 0.f;
	SpongeLevelCm = LevelCm;
	EdgeUpMeanU.Init(0.f, SizeY);
	EdgeDownMeanU.Init(0.f, SizeY);
	EdgeUpLastU.Init(0.f, SizeY);
	EdgeDownLastU.Init(0.f, SizeY);
	EdgeUpFlux.Init(0.f, SizeY);
	EdgeDownFlux.Init(0.f, SizeY);
	EdgeUpEtaM.Init(0.f, SizeY);
	EdgeDownEtaM.Init(0.f, SizeY);
	Rng.Initialize(20260917);
	const float LevelM = LevelCm * 0.01f;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const float Bed = BedSamplerCm ? BedSamplerCm(CellCentreCm(Index)) : 0.f;
		BedCm[Index] = Bed;
		// Still water at the level is the exact hydrostatic solution, so the field starts at rest and the solver has
		// nothing to settle before the first query.
		DepthM[Index] = FMath::Max(0.f, LevelM - Bed * 0.01f);
		SurfaceCm[Index] = Bed + DepthM[Index] * 100.f;
	}

	// The open ends are seeded with the discharge the section asks for, by continuity from the crossing's own depth:
	// a boundary that starts at zero has to learn it, and learning took over a minute (the crossing read 0.87 m/s of
	// its 1.26 at sixty seconds). Seeded, the ford runs at its speed from the first seconds.
	// Continuity over the whole cross-section, not per row: the crossing carries the section's current through 22 m of
	// 0.6 m water and an end has 74 m of it, most of it deeper, so the end's own velocity is a fifth of the crossing's.
	// (Seeded per row by the depth ratio alone it came out four times too fast and the field had to drain it back.)
	{
		double MidArea = 0.0;
		double UpArea = 0.0;
		double DownArea = 0.0;
		for (int32 Y = 0; Y < SizeY; ++Y)
		{
			const int32 Up = Y * SizeX;
			MidArea += DepthM[Up + SizeX / 2];
			UpArea += DepthM[Up];
			DownArea += DepthM[Up + SizeX - 1];
		}
		const float UpSeed = UpArea > 1.e-3 ? FMath::Clamp(NominalFlowMps * static_cast<float>(MidArea / UpArea), 0.f, EdgeMaxUMps) : 0.f;
		const float DownSeed = DownArea > 1.e-3 ? FMath::Clamp(NominalFlowMps * static_cast<float>(MidArea / DownArea), 0.f, EdgeMaxUMps) : 0.f;
		for (int32 Y = 0; Y < SizeY; ++Y)
		{
			const int32 Up = Y * SizeX;
			EdgeUpMeanU[Y] = DepthM[Up] > 0.05f ? UpSeed : 0.f;
			EdgeDownMeanU[Y] = DepthM[Up + SizeX - 1] > 0.05f ? DownSeed : 0.f;
		}
	}

	// The friction ramp at the two flow-wise ends (W1's FlowFadeM), and WS2's sponge over the same last metres.
	const float FadeCells = FMath::Max(1.f, FlowFadeM * 100.f / CellCm);
	FrictionScaleX.SetNumUninitialized(SizeX);
	SpongeRampX.SetNumUninitialized(SizeX);
	for (int32 X = 0; X < SizeX; ++X)
	{
		const float ToEnd = static_cast<float>(FMath::Min(X, SizeX - 1 - X));
		const float Ramp = FMath::Clamp((FadeCells - ToEnd) / FadeCells, 0.f, 1.f);
		FrictionScaleX[X] = 1.f + FMath::Max(0.f, EndFriction) * Ramp;
		SpongeRampX[X] = Ramp;
	}
	Accumulator = 0.f;
	ResetStats();
}

void FGTWaterField::ResetStats()
{
	StepMs = 0.f;
	StepMsSum = 0.0;
	StepMsCount = 0;
	StepMsMax = 0.f;
	SubStepsRun = 0;
	SubStepClamps = 0;
	SubStepsAsked = 0;
	DeficitSeconds = 0.f;
	CoarseFrames = 0;
	LastCoarseCfl = 0.f;
	AccumulatorDrops = 0;
	RainDropsRun = 0;
	WindPatchesRun = 0;
	FluxClamps = 0;
	MaxOverLevelCm = 0.f;
	DepthClamps = 0;
}

FVector2D FGTWaterField::ToFieldCm(const FVector2D& XYCm) const
{
	const FVector2D Local = XYCm - OriginCm;
	return FVector2D(FVector2D::DotProduct(Local, AxisX), FVector2D::DotProduct(Local, AxisY));
}

FVector2D FGTWaterField::ToWorldCm(const FVector2D& FieldCm) const
{
	return OriginCm + AxisX * FieldCm.X + AxisY * FieldCm.Y;
}

FVector2D FGTWaterField::CellCentreCm(int32 Index) const
{
	if (SizeX <= 0)
	{
		return OriginCm;
	}
	const int32 X = Index % SizeX;
	const int32 Y = Index / SizeX;
	return ToWorldCm(FVector2D((X + 0.5) * CellCm, (Y + 0.5) * CellCm));
}

int32 FGTWaterField::CellIndexAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return INDEX_NONE;
	}
	const FVector2D Field = ToFieldCm(XYCm);
	const int32 X = FMath::Clamp(FMath::FloorToInt(static_cast<float>(Field.X) / CellCm), 0, SizeX - 1);
	const int32 Y = FMath::Clamp(FMath::FloorToInt(static_cast<float>(Field.Y) / CellCm), 0, SizeY - 1);
	return Y * SizeX + X;
}

float FGTWaterField::SurfaceCmAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return LevelCm;
	}
	if(bClosedBasin)
	{
		// A dry cell stores its ground height, not a free surface. Do not pull
		// the pond up a clod when interpolating across a wet/dry boundary.
		const auto Wet=[this](int32 I){return DepthM[I]+LidM[I]>DryDepthM ? 1.f : 0.f;};
		const FVector2D P=ToFieldCm(XYCm);
		const float Weight=BilinearCells(P,CellCm,SizeX,SizeY,Wet);
		return Weight>1.e-6f ? BilinearCells(P,CellCm,SizeX,SizeY,[&](int32 I){return SurfaceCm[I]*Wet(I);})/Weight : LevelCm;
	}
	return BilinearCells(ToFieldCm(XYCm), CellCm, SizeX, SizeY, [this](int32 Index) { return SurfaceCm[Index]; });
}

float FGTWaterField::DepthMAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return 0.f;
	}
	return BilinearCells(ToFieldCm(XYCm), CellCm, SizeX, SizeY, [this](int32 Index) { return DepthM[Index]; });
}

FVector2D FGTWaterField::VelocityAt(const FVector2D& XYCm) const
{
	if (!IsValid())
	{
		return FVector2D::ZeroVector;
	}
	const FVector2D Field = ToFieldCm(XYCm);
	const float VX = BilinearCells(Field, CellCm, SizeX, SizeY, [this](int32 Index) { return VelXMps[Index]; });
	const float VY = BilinearCells(Field, CellCm, SizeX, SizeY, [this](int32 Index) { return VelYMps[Index]; });
	return AxisX * VX + AxisY * VY;
}

FVector2D FGTWaterField::CellVelocity(int32 Index) const
{
	if (!VelXMps.IsValidIndex(Index))
	{
		return FVector2D::ZeroVector;
	}
	return AxisX * VelXMps[Index] + AxisY * VelYMps[Index];
}

double FGTWaterField::VolumeM3() const
{
	const double AreaM2 = static_cast<double>(CellCm) * CellCm * 1.e-4;
	double Sum = 0.0;
	for (float H : DepthM)
	{
		Sum += H;
	}
	return Sum * AreaM2;
}

void FGTWaterField::Calm(float InLevelCm)
{
	if (HasRiverReference()) { ResetRiverReference(); return; }
	if (!IsValid())
	{
		return;
	}
	LevelCm = InLevelCm;
	SpongeLevelCm = LevelCm;
	const float LevelM = LevelCm * 0.01f;
	// RIVERBED S3: flat still water fills the basin (grown to this level first), not every hollow under the level.
	GrowBasin(LevelCm);
	for (int32 Index = 0; Index < DepthM.Num(); ++Index)
	{
		DepthM[Index] = InBasin(Index) ? FMath::Max(0.f, LevelM - BedCm[Index] * 0.01f) : 0.f;
	}
	FMemory::Memzero(FluxX.GetData(), FluxX.Num() * sizeof(float));
	FMemory::Memzero(FluxY.GetData(), FluxY.Num() * sizeof(float));
	// "Flat still water" means no lid either: the tests that calm the field have no car in it, and a lid left over a
	// flat field would stand as a step the first sub-step has to swallow. The open ends forget the discharge they had
	// learned as well, or they would keep pushing the current they were carrying into water that is meant to be still.
	ClearLids();
	FMemory::Memzero(EdgeUpMeanU.GetData(), EdgeUpMeanU.Num() * sizeof(float));
	FMemory::Memzero(EdgeDownMeanU.GetData(), EdgeDownMeanU.Num() * sizeof(float));
	FMemory::Memzero(EdgeUpLastU.GetData(), EdgeUpLastU.Num() * sizeof(float));
	FMemory::Memzero(EdgeDownLastU.GetData(), EdgeDownLastU.Num() * sizeof(float));
	FMemory::Memzero(EdgeUpFlux.GetData(), EdgeUpFlux.Num() * sizeof(float));
	FMemory::Memzero(EdgeDownFlux.GetData(), EdgeDownFlux.Num() * sizeof(float));
	Accumulator = 0.f;
	UpdateDerived();
}

void FGTWaterField::ClearLids()
{
	for (int32 Index : LidCells)
	{
		LidM[Index] = 0.f;
	}
	for (int32 Index : LidDirtyCells)
	{
		LidNextM[Index] = 0.f;
		LidDirty[Index] = 0;
	}
	LidCells.Reset();
	LidDirtyCells.Reset();
	LidCellCount = 0;
	LidVolumeM3 = 0.f;
}

void FGTWaterField::StampLid(const FVector2D& CentreCm, const FVector2D& ForwardXY, float HalfLenCm, float HalfWidCm,
	float BottomZCm, const FVector2D& BottomSlope, float MaxHeightCm, float Fill)
{
	if (!IsValid() || Fill <= 0.f || MaxHeightCm <= 0.f)
	{
		return;
	}
	const FVector2D Forward = ForwardXY.IsNearlyZero() ? FVector2D(1.0, 0.0) : ForwardXY.GetSafeNormal();
	const FVector2D Right(-Forward.Y, Forward.X);
	const float HalfLen = FMath::Max(CellCm * 0.5f, HalfLenCm);
	const float HalfWid = FMath::Max(CellCm * 0.5f, HalfWidCm);
	// The box's bounding circle in field space, walked cell by cell; a cell is in when its centre is inside the box.
	const FVector2D Field = ToFieldCm(CentreCm);
	const float Reach = FMath::Sqrt(HalfLen * HalfLen + HalfWid * HalfWid);
	const int32 Span = FMath::CeilToInt(Reach / CellCm) + 1;
	const int32 CX = FMath::Clamp(FMath::FloorToInt(static_cast<float>(Field.X) / CellCm), -Span, SizeX + Span);
	const int32 CY = FMath::Clamp(FMath::FloorToInt(static_cast<float>(Field.Y) / CellCm), -Span, SizeY + Span);
	const float MaxLidM = MaxHeightCm * 0.01f;
	for (int32 Y = FMath::Max(0, CY - Span); Y <= FMath::Min(SizeY - 1, CY + Span); ++Y)
	{
		for (int32 X = FMath::Max(0, CX - Span); X <= FMath::Min(SizeX - 1, CX + Span); ++X)
		{
			const int32 Index = Y * SizeX + X;
			const FVector2D World = CellCentreCm(Index);
			const FVector2D Local = World - CentreCm;
			const float Along = static_cast<float>(FVector2D::DotProduct(Local, Forward));
			const float Across = static_cast<float>(FVector2D::DotProduct(Local, Right));
			if (FMath::Abs(Along) > HalfLen || FMath::Abs(Across) > HalfWid)
			{
				continue;
			}
			// The solid's bottom over this cell, following the car's pitch and roll - and never below the bed, because a
			// column of water starts at the bed and a wheel sunk into the mud under it displaces nothing that is there.
			// (Unclamped, a wheel whose contact point sat 20 cm into the mud held a lid 20 cm taller than the water it
			// stood in, and the terrain test read 0.85 m of water over a ford it had always read 0.62 m of.)
			const float BottomHere = FMath::Max(BottomZCm + static_cast<float>(BottomSlope.X * Local.X + BottomSlope.Y * Local.Y), BedCm[Index]);
			// How much of the column it holds: the cell's own effective surface (what the water stands at with the
			// lid already in it) down to the solid's bottom, never more than the solid is tall. The fill is the share
			// of the box that is actually solid.
			const float Lid = Fill * FMath::Clamp((SurfaceCm[Index] - BottomHere) * 0.01f, 0.f, MaxLidM);
			if (!LidDirty[Index])
			{
				LidDirty[Index] = 1;
				LidNextM[Index] = 0.f;
				LidDirtyCells.Add(Index);
			}
			LidNextM[Index] = FMath::Max(LidNextM[Index], Lid);
		}
	}
}

void FGTWaterField::PromoteLids(float Dt)
{
	// Every cell that had a lid is listed too, so one that the car has left relaxes back to zero at the same rate.
	for (int32 Index : LidCells)
	{
		if (!LidDirty[Index])
		{
			LidDirty[Index] = 1;
			LidNextM[Index] = 0.f;
			LidDirtyCells.Add(Index);
		}
	}
	const float MaxDelta = FMath::Max(0.001f, LidRateMps) * FMath::Max(1.e-4f, Dt);
	LidCells.Reset();
	LidVolumeM3 = 0.f;
	const double AreaM2 = static_cast<double>(CellCm) * CellCm * 1.e-4;
	for (int32 Index : LidDirtyCells)
	{
		const float Was = LidM[Index];
		float Now = FMath::Clamp(LidNextM[Index], Was - MaxDelta, Was + MaxDelta);
		if (Now < 1.e-4f)
		{
			Now = 0.f;
		}
		LidM[Index] = Now;
		LidNextM[Index] = 0.f;
		LidDirty[Index] = 0;
		if (Now > 0.f)
		{
			LidCells.Add(Index);
			LidVolumeM3 += static_cast<float>(Now * AreaM2);
		}
	}
	LidDirtyCells.Reset();
	BlurLids();
	LidCellCount = LidCells.Num();
}

void FGTWaterField::BlurLids()
{
	if (LidBlend <= 0.f || LidCells.Num() == 0)
	{
		return;
	}
	// A hull's side is vertical; a 25 cm cell cannot carry that. Unsmoothed, the lid puts the whole of the water's
	// depth across one face, g x 0.58 / 0.25 = 23 m/s2 of acceleration, and the cell empties itself into its
	// neighbour faster than the model can follow. Spread over its neighbours the same displacement becomes a slope
	// the grid can hold, which is a hull with a chine on it rather than a brick.
	LidScratch.Reset();
	auto Mark = [this](int32 Index)
	{
		if (!LidFilled[Index])
		{
			LidFilled[Index] = 1;
			LidScratch.Add(Index);
		}
	};
	for (int32 Index : LidCells)
	{
		const int32 X = Index % SizeX;
		const int32 Y = Index / SizeX;
		Mark(Index);
		if (X > 0) { Mark(Index - 1); }
		if (X + 1 < SizeX) { Mark(Index + 1); }
		if (Y > 0) { Mark(Index - SizeX); }
		if (Y + 1 < SizeY) { Mark(Index + SizeX); }
	}
	const float Keep = 1.f - FMath::Clamp(LidBlend, 0.f, 1.f);
	const float Share = FMath::Clamp(LidBlend, 0.f, 1.f) * 0.25f;
	for (int32 Index : LidScratch)
	{
		const int32 X = Index % SizeX;
		const int32 Y = Index / SizeX;
		float Sum = 0.f;
		Sum += (X > 0) ? LidM[Index - 1] : LidM[Index];
		Sum += (X + 1 < SizeX) ? LidM[Index + 1] : LidM[Index];
		Sum += (Y > 0) ? LidM[Index - SizeX] : LidM[Index];
		Sum += (Y + 1 < SizeY) ? LidM[Index + SizeX] : LidM[Index];
		LidNextM[Index] = Keep * LidM[Index] + Share * Sum;   // LidNextM is free here: the stamps have just been taken
	}
	LidCells.Reset();
	LidVolumeM3 = 0.f;
	const double AreaM2 = static_cast<double>(CellCm) * CellCm * 1.e-4;
	for (int32 Index : LidScratch)
	{
		const float Now = LidNextM[Index] < 1.e-4f ? 0.f : LidNextM[Index];
		LidM[Index] = Now;
		LidNextM[Index] = 0.f;
		LidFilled[Index] = 0;
		if (Now > 0.f)
		{
			LidCells.Add(Index);
			LidVolumeM3 += static_cast<float>(Now * AreaM2);
		}
	}
	LidScratch.Reset();
}

void FGTWaterField::FillLidVelocities()
{
	if (LidCells.Num() == 0)
	{
		return;
	}
	// Every cell under a solid, not only the ones squeezed dry. The water under a lid is being pushed out from under
	// it, and that escape jet is the lid's own doing: a hull that read it would read its own displacement as a
	// current and be shoved by it (measured before this: 21,274 N on a parked car against W2's 3,009, and the car
	// taken 0.83 m against its 0.5 m gate). What a body in the water feels is the stream around it, so every lidded
	// cell takes the velocity of the unlidded water at the edge of the lid, filled inward.
	LidScratch.Reset();
	for (int32 Index : LidCells)
	{
		LidScratch.Add(Index);
		LidFilled[Index] = 0;
	}
	for (int32 Pass = 0; Pass < 12 && LidScratch.Num() > 0; ++Pass)
	{
		int32 Filled = 0;
		for (int32 Entry = 0; Entry < LidScratch.Num(); ++Entry)
		{
			const int32 Index = LidScratch[Entry];
			if (LidFilled[Index])
			{
				continue;
			}
			const int32 X = Index % SizeX;
			const int32 Y = Index / SizeX;
			// The stream is COPIED inward, not averaged. Averaging the four neighbours diffuses it: the flow divides
			// around a car, so the vectors on opposite sides partly cancel and what the hull reads comes out smaller
			// than the river it is floating in - measured, the carried car of terrain step 16 drifted 2.25 m in ten
			// seconds against W2's 5.73 with the hull's force down from 2,398 N to 1,779. A copy keeps the speed.
			int32 Source = INDEX_NONE;
			auto Take = [&](int32 NX, int32 NY)
			{
				if (Source != INDEX_NONE || NX < 0 || NY < 0 || NX >= SizeX || NY >= SizeY)
				{
					return;
				}
				const int32 N = NY * SizeX + NX;
				// A neighbour is a source when it carries no lid of its own, or has already been filled this pass.
				if (LidM[N] > 0.f && !LidFilled[N])
				{
					return;
				}
				Source = N;
			};
			Take(X - 1, Y);
			Take(X + 1, Y);
			Take(X, Y - 1);
			Take(X, Y + 1);
			if (Source == INDEX_NONE)
			{
				continue;
			}
			VelXMps[Index] = VelXMps[Source];
			VelYMps[Index] = VelYMps[Source];
			LidFilled[Index] = 1;
			++Filled;
		}
		if (Filled == 0)
		{
			break;
		}
	}
	for (int32 Index : LidScratch)
	{
		LidFilled[Index] = 0;
	}
}

void FGTWaterField::ShiftLevel(float NewLevelCm, float FromLevelCm)
{
	// The fixed-bank reference pilot has no flood-stage bake. Do not flatten its sloping surface.
	if (HasRiverReference()) { return; }
	if (!IsValid())
	{
		LevelCm = NewLevelCm;
		SpongeLevelCm = NewLevelCm;
		return;
	}
	// R1: from the level the field was last carried to, not from the one Step was last handed (see the header).
	const float BaseCm = FromLevelCm > -1.e8f ? FromLevelCm : LevelCm;
	const float DeltaM = (NewLevelCm - BaseCm) * 0.01f;
	const float NewLevelM = NewLevelCm * 0.01f;
	// RIVERBED S3: a rise reaches the banks that touch the water through the bed, not a hollow behind a rim.
	if (DeltaM > 0.f)
	{
		GrowBasin(NewLevelCm);
	}
	TArray<float> WasM = DepthM;
	for (int32 Index = 0; Index < DepthM.Num(); ++Index)
	{
		// The water that is there rises with the river, and a bank the new level covers is filled to it in the same
		// tick. Both ways were measured on a carried 70 cm raise: filled here, the middle swings 13.7 cm peak to peak
		// over the ten seconds after it lands; left for the solver to wet from its neighbours - which is the more
		// physical of the two - the banks draw their water out of the channel instead and it swings 47.6 cm. So the
		// banks are filled here.
		DepthM[Index] = DepthM[Index] > 0.f
			? FMath::Max(0.f, DepthM[Index] + DeltaM)
			: (InBasin(Index) ? FMath::Max(0.f, NewLevelM - BedCm[Index] * 0.01f) : 0.f);
	}
	// The flux is a volume per second, v x width x depth, so carrying the depth without it would change the speed:
	// measured, a 70 cm drop left the fluxes of a 1.27 m channel in a 0.57 m one and the current read 5.4 m/s where
	// the field's own mean is 1.6. Each face's flux is scaled by how its depth changed, and the speed stands.
	auto FaceDepth = [this](const TArray<float>& Depths, int32 I, int32 J)
	{
		return FMath::Max(0.5f * (Depths[I] + Depths[J]), MinDepthM);
	};
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			const int32 I = Y * SizeX + X;
			if (X + 1 < SizeX)
			{
				FluxX[I] *= FMath::Clamp(FaceDepth(DepthM, I, I + 1) / FaceDepth(WasM, I, I + 1), 0.f, 10.f);
			}
			if (Y + 1 < SizeY)
			{
				FluxY[I] *= FMath::Clamp(FaceDepth(DepthM, I, I + SizeX) / FaceDepth(WasM, I, I + SizeX), 0.f, 10.f);
			}
		}
	}
	LevelCm = NewLevelCm;
	// The whole surface has been carried, so the sponge's own level goes with it: it must not pull the ends back.
	SpongeLevelCm = NewLevelCm;
	UpdateDerived();
}

double FGTWaterField::AddImpulse(const FVector2D& WorldXY, float RadiusCm, float RiseCm)
{
	if (!IsValid())
	{
		return 0.0;
	}
	const FVector2D Field = ToFieldCm(WorldXY);
	const float Radius = FMath::Max(CellCm * 0.5f, RadiusCm);
	const int32 Span = FMath::CeilToInt(Radius / CellCm) + 1;
	const int32 CX = FMath::Clamp(FMath::FloorToInt(static_cast<float>(Field.X) / CellCm), 0, SizeX - 1);
	const int32 CY = FMath::Clamp(FMath::FloorToInt(static_cast<float>(Field.Y) / CellCm), 0, SizeY - 1);
	const float RiseM = RiseCm * 0.01f;
	const double AreaM2 = static_cast<double>(CellCm) * CellCm * 1.e-4;
	double Added = 0.0;
	for (int32 Y = FMath::Max(0, CY - Span); Y <= FMath::Min(SizeY - 1, CY + Span); ++Y)
	{
		for (int32 X = FMath::Max(0, CX - Span); X <= FMath::Min(SizeX - 1, CX + Span); ++X)
		{
			const int32 Index = Y * SizeX + X;
			const FVector2D Centre((X + 0.5) * CellCm, (Y + 0.5) * CellCm);
			if (HasRiverReference() && RiverDepthM[Index] <= 0.f) { continue; }
			if (FVector2D::DistSquared(Centre, Field) > Radius * Radius)
			{
				continue;
			}
			DepthM[Index] += RiseM;
			Added += RiseM * AreaM2;
		}
	}
	UpdateDerived();
	return Added;
}

void FGTWaterField::ApplyBoundary()
{
	if (bClosedBasin) return;
	// The two flow-wise ends are fixed heads, centred on the level: upstream (X = 0) half the head over it,
	// downstream half under, so the middle of the sheet - where the route crosses - stands at the level itself and
	// the ford is as deep as W1 and W2 tuned it. They are the source and the sink, so mass is deliberately not
	// conserved in those two columns.
	const float UpM = (LevelCm + 0.5f * AppliedHeadDropCm) * 0.01f;
	const float DownM = (LevelCm - 0.5f * AppliedHeadDropCm) * 0.01f;
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		const int32 Row = Y * SizeX;
		// RIVERBED S3: only a basin cell is held at a head; an end that lies on a basin's dry rim passes nothing.
		if (InBasin(Row))
		{
			DepthM[Row] = FMath::Max(0.f, UpM - BedCm[Row] * 0.01f);
		}
		const int32 Last = Row + SizeX - 1;
		if (InBasin(Last))
		{
			DepthM[Last] = FMath::Max(0.f, DownM - BedCm[Last] * 0.01f);
		}
	}
}

int32 FGTWaterField::SetBasinFrom(int32 SeedIndex, float FillLevelCm)
{
	if (!IsValid() || !BedCm.IsValidIndex(SeedIndex))
	{
		Basin.Reset();
		BasinCells = 0;
		return 0;
	}
	const int32 Count = NumCells();
	Basin.Init(0, Count);
	BasinCells = 0;
	TArray<int32> Queue;
	Queue.Reserve(Count / 2);
	Basin[SeedIndex] = 1;
	Queue.Add(SeedIndex);
	for (int32 Head = 0; Head < Queue.Num(); ++Head)
	{
		const int32 I = Queue[Head];
		const int32 X = I % SizeX;
		const int32 Y = I / SizeX;
		++BasinCells;
		const int32 NX[4] = { X - 1, X + 1, X, X };
		const int32 NY[4] = { Y, Y, Y - 1, Y + 1 };
		for (int32 K = 0; K < 4; ++K)
		{
			if (NX[K] < 0 || NY[K] < 0 || NX[K] >= SizeX || NY[K] >= SizeY)
			{
				continue;
			}
			const int32 J = NY[K] * SizeX + NX[K];
			if (!Basin[J] && BedCm[J] < FillLevelCm)
			{
				Basin[J] = 1;
				Queue.Add(J);
			}
		}
	}
	// Still water only inside it: Init filled every cell under the level.
	const float LevelM = LevelCm * 0.01f;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		DepthM[Index] = Basin[Index] ? FMath::Max(0.f, LevelM - BedCm[Index] * 0.01f) : 0.f;
	}
	UpdateDerived();
	return BasinCells;
}

int32 FGTWaterField::GrowBasin(float InLevelCm)
{
	if (Basin.Num() != NumCells() || Basin.Num() == 0)
	{
		return 0;
	}
	TArray<int32> Queue;
	// The seeds: every basin cell with a neighbour outside the basin whose bed is under the level.
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			const int32 I = Y * SizeX + X;
			if (!Basin[I])
			{
				continue;
			}
			if ((X > 0 && !Basin[I - 1] && BedCm[I - 1] < InLevelCm) || (X + 1 < SizeX && !Basin[I + 1] && BedCm[I + 1] < InLevelCm)
				|| (Y > 0 && !Basin[I - SizeX] && BedCm[I - SizeX] < InLevelCm) || (Y + 1 < SizeY && !Basin[I + SizeX] && BedCm[I + SizeX] < InLevelCm))
			{
				Queue.Add(I);
			}
		}
	}
	int32 Joined = 0;
	for (int32 Head = 0; Head < Queue.Num(); ++Head)
	{
		const int32 I = Queue[Head];
		const int32 X = I % SizeX;
		const int32 Y = I / SizeX;
		const int32 NX[4] = { X - 1, X + 1, X, X };
		const int32 NY[4] = { Y, Y, Y - 1, Y + 1 };
		for (int32 K = 0; K < 4; ++K)
		{
			if (NX[K] < 0 || NY[K] < 0 || NX[K] >= SizeX || NY[K] >= SizeY)
			{
				continue;
			}
			const int32 J = NY[K] * SizeX + NX[K];
			if (!Basin[J] && BedCm[J] < InLevelCm)
			{
				Basin[J] = 1;
				++Joined;
				Queue.Add(J);
			}
		}
	}
	BasinCells += Joined;
	return Joined;
}

void FGTWaterField::ApplyWind(float Dt)
{
	if (WindScale <= 0.f || WindRippleCm <= 0.f || Dt <= 0.f)
	{
		return;
	}
	WindPhase += Dt;
	// The gust: the amplitude wanders between about a third and one over WindGustS, with a second, shorter beat on it
	// so it does not read as a metronome. It is never negative - a gust that reversed would only cancel itself.
	const float T = 2.f * PI * WindPhase / FMath::Max(0.5f, WindGustS);
	const float Gust = FMath::Clamp((0.55f + 0.45f * FMath::Sin(T)) * (0.7f + 0.3f * FMath::Sin(T * 2.7f)), 0.f, 1.5f);
	WindCarry += WindPatchesPerS * Gust * Dt;
	const int32 Patches = FMath::Min(FMath::FloorToInt(WindCarry), 64);
	WindCarry -= Patches;
	if (Patches <= 0)
	{
		return;
	}
	const float CellM = CellCm * 0.01f;
	const float RadiusCm = FMath::Max(CellCm, WindPatchM * 100.f);
	const int32 Span = FMath::CeilToInt(RadiusCm / CellCm);
	for (int32 Patch = 0; Patch < Patches; ++Patch)
	{
		// Only six cells in ten hold water here, so a patch dropped blind is wasted more often than not: try a few.
		int32 CX = 0;
		int32 CY = 0;
		bool bWet = false;
		for (int32 Try = 0; Try < 8 && !bWet; ++Try)
		{
			CX = Rng.RandRange(0, SizeX - 1);
			CY = Rng.RandRange(0, SizeY - 1);
			bWet = DepthM[CY * SizeX + CX] > DryDepthM;
		}
		if (!bWet)
		{
			continue;
		}
		const float Angle = Rng.FRandRange(0.f, 2.f * PI);
		// A velocity put on a patch is a dipole - water leaves one side and gathers on the other - so it radiates as a
		// ring and adds no volume at all: only fluxes are touched, and a flux moves water between two cells.
		const float Speed = WindRippleCm * 0.01f * WindScale * Gust * Rng.FRandRange(0.5f, 1.5f);
		const float DirX = FMath::Cos(Angle) * Speed;
		const float DirY = FMath::Sin(Angle) * Speed;
		++WindPatchesRun;
		for (int32 Y = FMath::Max(0, CY - Span); Y <= FMath::Min(SizeY - 1, CY + Span); ++Y)
		{
			for (int32 X = FMath::Max(0, CX - Span); X <= FMath::Min(SizeX - 1, CX + Span); ++X)
			{
				const float DX = (X - CX) * CellCm;
				const float DY = (Y - CY) * CellCm;
				const float DistCm = FMath::Sqrt(DX * DX + DY * DY);
				if (DistCm > RadiusCm)
				{
					continue;
				}
				const float Weight = 0.5f + 0.5f * FMath::Cos(PI * DistCm / RadiusCm);   // a soft disc, so the edges do not ring
				const int32 Index = Y * SizeX + X;
				const float H = DepthM[Index];
				if (H <= DryDepthM)
				{
					continue;
				}
				const float Conveyance = CellM * H;
				if (X + 1 < SizeX && DepthM[Index + 1] > DryDepthM)
				{
					FluxX[Index] += DirX * Weight * Conveyance;
				}
				if (Y + 1 < SizeY && DepthM[Index + SizeX] > DryDepthM)
				{
					FluxY[Index] += DirY * Weight * Conveyance;
				}
			}
		}
	}
}

void FGTWaterField::ApplyRain(float Dt)
{
	if (RainIntensity <= 0.f || RainDropsPerM2S <= 0.f || RainDropCm <= 0.f || Dt <= 0.f)
	{
		return;
	}
	const double AreaM2 = static_cast<double>(CellCm) * CellCm * 1.e-4;
	const double WetAreaM2 = WetCellCount * AreaM2;
	RainCarry += static_cast<float>(RainDropsPerM2S * FMath::Clamp(RainIntensity, 0.f, 1.f) * WetAreaM2 * Dt);
	const int32 Drops = FMath::Min(FMath::FloorToInt(RainCarry), MaxDropsPerStep);
	RainCarry -= Drops;
	if (Drops <= 0)
	{
		return;
	}
	const float RiseM = RainDropCm * 0.01f;
	const float TakeM = RiseM / 8.f;
	for (int32 Drop = 0; Drop < Drops; ++Drop)
	{
		const int32 X = Rng.RandRange(1, SizeX - 2);
		const int32 Y = Rng.RandRange(1, SizeY - 2);
		const int32 Index = Y * SizeX + X;
		if (DepthM[Index] <= DryDepthM)
		{
			continue;
		}
		// A drop is an impulse, not water: the cell rises and its eight neighbours give up the same volume between
		// them, so the level stays the boundary's and the field's volume is what it was. A drop at the waterline,
		// where a neighbour has not the depth to give, is skipped rather than clamped (a clamp would add water).
		bool bCanTake = true;
		for (int32 DY = -1; DY <= 1 && bCanTake; ++DY)
		{
			for (int32 DX = -1; DX <= 1; ++DX)
			{
				if (DX == 0 && DY == 0)
				{
					continue;
				}
				if (DepthM[Index + DY * SizeX + DX] < TakeM + DryDepthM)
				{
					bCanTake = false;
					break;
				}
			}
		}
		if (!bCanTake)
		{
			continue;
		}
		DepthM[Index] += RiseM;
		for (int32 DY = -1; DY <= 1; ++DY)
		{
			for (int32 DX = -1; DX <= 1; ++DX)
			{
				if (DX == 0 && DY == 0)
				{
					continue;
				}
				DepthM[Index + DY * SizeX + DX] -= TakeM;
			}
		}
		++RainDropsRun;
	}
}

void FGTWaterField::ApplySponge(float Dt)
{
	if (SpongeTauS <= 0.f && SpongeFluxDamp <= 0.f)
	{
		return;
	}
	// WS1's flag: both ends are fixed heads, so every wave that reaches one comes back, and a 70 cm raise left the
	// middle swinging 38 to 58 cm on the basin's seiche for a minute. Over the last FlowFadeM the depth is pulled
	// back toward the head the boundary would hold at that column - the linear drop between the two ends, so the
	// mean gradient that drives the current is what the sponge asks for and only the wave on top of it is eaten.
	// Not LevelCm but the sponge's own, filtered: a level that jumps at the two boundaries (SetExtraRiseAll with no
	// carry, the weather's step) would otherwise be pumped into the whole five metres of each end at once - measured,
	// 518 m3 into a 332 m3 field in a second, which rang the basin 114 cm peak to peak instead of absorbing it.
	// ShiftLevel and Calm snap it, so a level the game carries into the field is not fought by the sponge.
	const float LevelM = SpongeLevelCm * 0.01f;
	const float HeadM = AppliedHeadDropCm * 0.01f;
	const float InvSpan = SizeX > 1 ? 1.f / (SizeX - 1) : 0.f;
	for (int32 X = 0; X < SizeX; ++X)
	{
		const float Ramp = SpongeRampX[X];
		if (Ramp <= 0.f)
		{
			continue;
		}
		const float Relax = SpongeTauS > 0.f ? FMath::Clamp(Ramp * Dt / SpongeTauS, 0.f, 1.f) : 0.f;
		const float FluxKeep = SpongeFluxDamp > 0.f ? FMath::Clamp(1.f - Ramp * SpongeFluxDamp * Dt, 0.f, 1.f) : 1.f;
		const float TargetM = LevelM + HeadM * (0.5f - X * InvSpan);
		for (int32 Y = 0; Y < SizeY; ++Y)
		{
			const int32 Index = Y * SizeX + X;
			if (Relax > 0.f)
			{
				const float WantM = FMath::Max(0.f, TargetM - BedCm[Index] * 0.01f);
				DepthM[Index] += (WantM - DepthM[Index]) * Relax;
			}
			if (FluxKeep < 1.f)
			{
				FluxX[Index] *= FluxKeep;
			}
		}
	}
}

void FGTWaterField::ComputeEdgeFluxes()
{
	// The radiating (Flather) ends. Each row's ghost face outside the field carries
	//     u = the learned mean + sqrt(g / h) x (the head this end asks for - the surface it has),
	// where sqrt(g / h) is the water's own wave impedance: a wave arriving at the end raises its surface, the term
	// turns that into an outgoing flux of exactly the size the wave carries, and nothing is reflected. A pinned
	// column - WS1's fixed head - reflects all of it, which is why a 70 cm raise rang the basin for a minute.
	const float CellM = CellCm * 0.01f;
	const float UpM = (LevelCm + 0.5f * AppliedHeadDropCm) * 0.01f;
	const float DownM = (LevelCm - 0.5f * AppliedHeadDropCm) * 0.01f;
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		const int32 Up = Y * SizeX;
		const int32 Down = Up + SizeX - 1;

		const float UpBedM = BedCm[Up] * 0.01f;
		const float UpH = FMath::Max(DepthM[Up], 0.f);
		const float UpEta = UpBedM + UpH + LidM[Up];
		EdgeUpEtaM[Y] = UpEta;
		float UpU = EdgeUpMeanU[Y] + (UpM - UpEta) * FMath::Sqrt(GTWaterGravity / FMath::Max(UpH, MinDepthM));
		UpU = FMath::Clamp(UpU, -EdgeMaxUMps, EdgeMaxUMps);
		// Upwind: water coming in carries the depth the outside stands at, water leaving carries the cell's own.
		const float UpFaceH = UpU > 0.f ? FMath::Max(0.f, UpM - UpBedM) : UpH;
		EdgeUpLastU[Y] = UpU;
		EdgeUpFlux[Y] = UpU * CellM * UpFaceH;

		const float DownBedM = BedCm[Down] * 0.01f;
		const float DownH = FMath::Max(DepthM[Down], 0.f);
		const float DownEta = DownBedM + DownH + LidM[Down];
		EdgeDownEtaM[Y] = DownEta;
		float DownU = EdgeDownMeanU[Y] + (DownEta - DownM) * FMath::Sqrt(GTWaterGravity / FMath::Max(DownH, MinDepthM));
		DownU = FMath::Clamp(DownU, -EdgeMaxUMps, EdgeMaxUMps);
		const float DownFaceH = DownU > 0.f ? DownH : FMath::Max(0.f, DownM - DownBedM);
		EdgeDownLastU[Y] = DownU;
		EdgeDownFlux[Y] = DownU * CellM * DownFaceH;
	}
}

float FGTWaterField::EdgeMeanUMps(bool bUpstream) const
{
	double Sum = 0.0;
	int32 Count = 0;
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		const int32 Index = bUpstream ? Y * SizeX : Y * SizeX + SizeX - 1;
		if (!DepthM.IsValidIndex(Index) || DepthM[Index] <= DryDepthM)
		{
			continue;
		}
		Sum += bUpstream ? EdgeUpMeanU[Y] : EdgeDownMeanU[Y];
		++Count;
	}
	return Count > 0 ? static_cast<float>(Sum / Count) : 0.f;
}

void FGTWaterField::LearnEdgeMeans(float Dt)
{
	// An open end only knows how much water the channel wants through it by watching what goes through while the
	// boundary is quiet. Driving 1.3 m/s through a matched boundary would otherwise cost 32 cm of head, and the ford
	// has 8.5; learned, the end settles at its own head with the discharge running through it. While a wave or a
	// raise is passing - the surface moving faster than EdgeQuietMps - nothing is learned, so the transient is
	// radiated away instead of being taken for the new normal.
	if (Dt <= 0.f)
	{
		return;
	}
	const float Blend = FMath::Clamp(Dt / FMath::Max(1.f, EdgeMeanTauS), 0.f, 1.f);
	// The surfaces below were read at the start of the last sub-step, so the threshold is a sub-step's worth of motion.
	const float QuietM = EdgeQuietMps * FMath::Max(1.e-4f, SubStepSeconds);
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		const int32 Up = Y * SizeX;
		const int32 Down = Up + SizeX - 1;
		const float UpEta = BedCm[Up] * 0.01f + FMath::Max(DepthM[Up], 0.f) + LidM[Up];
		if (FMath::Abs(UpEta - EdgeUpEtaM[Y]) < QuietM)
		{
			EdgeUpMeanU[Y] = FMath::Clamp(EdgeUpMeanU[Y] + (EdgeUpLastU[Y] - EdgeUpMeanU[Y]) * Blend, -EdgeMaxUMps, EdgeMaxUMps);
		}
		const float DownEta = BedCm[Down] * 0.01f + FMath::Max(DepthM[Down], 0.f) + LidM[Down];
		if (FMath::Abs(DownEta - EdgeDownEtaM[Y]) < QuietM)
		{
			EdgeDownMeanU[Y] = FMath::Clamp(EdgeDownMeanU[Y] + (EdgeDownLastU[Y] - EdgeDownMeanU[Y]) * Blend, -EdgeMaxUMps, EdgeMaxUMps);
		}
	}
}

void FGTWaterField::SubStep(float Dt)
{
	if (HasRiverReference()) { RiverSubStep(Dt); return; }
	const float CellM = CellCm * 0.01f;
	const float AreaM2 = CellM * CellM;
	const float InvArea = 1.f / AreaM2;

	if (bOpenEnds)
	{
		ComputeEdgeFluxes();
	}
	else
	{
		ApplyBoundary();
	}

	// ---- 1. the fluxes ------------------------------------------------------------------------------------
	// Each face accelerates by g x (the water's own cross-section / the cell length) x the surface difference. The
	// cross-section is CellM x h_face and the length CellM, so the cell size cancels and only the depth is left.
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			const int32 I = Y * SizeX + X;
			const float HI = DepthM[I];
			// WS2: the surface the pressure follows is bed + water + the solid holding the column down (the lid), so
			// water is pushed out from under a hull or a wheel until what is left plus the solid stands at the level
			// the water outside stands at - which is Archimedes, with no volume to keep track of - and runs back in
			// when the solid leaves. The conveyance below stays the water's own depth: a wheel is a wall, not a pipe.
			const float SI = BedCm[I] * 0.01f + HI + LidM[I];
			const float Scale = FrictionScaleX[X];
			if (X + 1 < SizeX)
			{
				const int32 J = I + 1;
				const float HJ = DepthM[J];
				if (HI <= 0.f && HJ <= 0.f)
				{
					FluxX[I] = 0.f;   // two dry cells: a wall
				}
				else
				{
					const float HFace = FMath::Max(0.5f * (HI + HJ), MinDepthM);
					const float SJ = BedCm[J] * 0.01f + HJ + LidM[J];
					float F = FluxX[I] + Dt * GTWaterGravity * HFace * (SI - SJ);
					const float V = FMath::Abs(F) / FMath::Max(CellM * HFace, 1.e-4f);
					const float Rate = BedFriction * Scale * V / FMath::Max(HFace, MinDepthM);
					F *= FMath::Clamp(1.f - PipeDamping - Rate * Dt, 0.f, 1.f);
					// WS2's sim guard: a lid's step across one cell asks for more than the model can carry.
					const float CapX = MaxFlowSpeedMps * CellM * HFace;
					if (FMath::Abs(F) > CapX)
					{
						F = F > 0.f ? CapX : -CapX;
						++FluxClamps;
					}
					FluxX[I] = F;
				}
			}
			else
			{
				FluxX[I] = 0.f;
			}
			if (Y + 1 < SizeY)
			{
				const int32 J = I + SizeX;
				const float HJ = DepthM[J];
				if (HI <= 0.f && HJ <= 0.f)
				{
					FluxY[I] = 0.f;
				}
				else
				{
					const float HFace = FMath::Max(0.5f * (HI + HJ), MinDepthM);
					const float SJ = BedCm[J] * 0.01f + HJ + LidM[J];
					float F = FluxY[I] + Dt * GTWaterGravity * HFace * (SI - SJ);
					const float V = FMath::Abs(F) / FMath::Max(CellM * HFace, 1.e-4f);
					const float Rate = BedFriction * Scale * V / FMath::Max(HFace, MinDepthM);
					F *= FMath::Clamp(1.f - PipeDamping - Rate * Dt, 0.f, 1.f);
					const float CapY = MaxFlowSpeedMps * CellM * HFace;
					if (FMath::Abs(F) > CapY)
					{
						F = F > 0.f ? CapY : -CapY;
						++FluxClamps;
					}
					FluxY[I] = F;
				}
			}
			else
			{
				FluxY[I] = 0.f;
			}
		}
	}

	// ---- 2. no cell may empty ------------------------------------------------------------------------------
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			const int32 I = Y * SizeX + X;
			const float Have = DepthM[I] * AreaM2;
			const float OutXPlus = (X + 1 < SizeX) ? FMath::Max(0.f, FluxX[I]) : 0.f;
			const float OutXMinus = (X > 0) ? FMath::Max(0.f, -FluxX[I - 1]) : 0.f;
			const float OutYPlus = (Y + 1 < SizeY) ? FMath::Max(0.f, FluxY[I]) : 0.f;
			const float OutYMinus = (Y > 0) ? FMath::Max(0.f, -FluxY[I - SizeX]) : 0.f;
			// An open end's ghost face is an outflow too when it is carrying water out of the field.
			const float OutEdge = bOpenEnds
				? ((X == 0 ? FMath::Max(0.f, -EdgeUpFlux[Y]) : 0.f) + (X == SizeX - 1 ? FMath::Max(0.f, EdgeDownFlux[Y]) : 0.f))
				: 0.f;
			const float Out = (OutXPlus + OutXMinus + OutYPlus + OutYMinus + OutEdge) * Dt;
			if (Out <= Have || Out <= 0.f)
			{
				continue;
			}
			const float K = Have / Out;
			if (OutXPlus > 0.f) { FluxX[I] *= K; }
			if (OutXMinus > 0.f) { FluxX[I - 1] *= K; }
			if (OutYPlus > 0.f) { FluxY[I] *= K; }
			if (OutYMinus > 0.f) { FluxY[I - SizeX] *= K; }
			if (bOpenEnds && X == 0 && EdgeUpFlux[Y] < 0.f) { EdgeUpFlux[Y] *= K; }
			if (bOpenEnds && X == SizeX - 1 && EdgeDownFlux[Y] > 0.f) { EdgeDownFlux[Y] *= K; }
		}
	}

	// ---- 3. the depths ------------------------------------------------------------------------------------
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			const int32 I = Y * SizeX + X;
			float Net = 0.f;
			if (X + 1 < SizeX) { Net -= FluxX[I]; }
			if (X > 0) { Net += FluxX[I - 1]; }
			if (Y + 1 < SizeY) { Net -= FluxY[I]; }
			if (Y > 0) { Net += FluxY[I - SizeX]; }
			if (bOpenEnds)
			{
				if (X == 0) { Net += EdgeUpFlux[Y]; }
				if (X == SizeX - 1) { Net -= EdgeDownFlux[Y]; }
			}
			DepthM[I] = FMath::Max(0.f, DepthM[I] + Net * Dt * InvArea);
		}
	}

	// ---- 4. WS2: the ends absorb what reaches them ---------------------------------------------------------
	if (!bClosedBasin) ApplySponge(Dt);
}

bool FGTWaterField::UpdateClosedBed(TConstArrayView<float> HeightsCm)
{
	if (!bClosedBasin || bOpenEnds || HasRiverReference() || HeightsCm.Num()!=NumCells()) return false;
	for (float H : HeightsCm) if (!FMath::IsFinite(H)) return false;
	for (int32 I=0;I<NumCells();++I) BedCm[I]=HeightsCm[I];
	// The existing water column rides the moving bed. Its pressure difference
	// subsequently pushes/pulls water through connected cells, conserving volume.
	UpdateDerived();
	return true;
}

void FGTWaterField::UpdateDerived()
{
	const float CellM = CellCm * 0.01f;
	WetCellCount = 0;
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			const int32 I = Y * SizeX + X;
			float H = DepthM[I];
			// WS2's last guard: no cell may stand more than GuardOverLevelM over the level. It should never fire - the
			// flux cap and the lid's own smoothing are what keep the solver in hand - and when it does it is logged,
			// because water is being thrown away here and the volume gates would see it as a leak.
			// Three metres over the level, or three metres of water, whichever is more: a cell whose bed stands over the
			// level (the banks, five metres of them here) would otherwise be "clamped" to a negative depth every frame.
			const float GuardM = FMath::Max(3.f, (LevelCm - BedCm[I]) * 0.01f + 3.f);
			if (H > GuardM)
			{
				H = FMath::Max(0.f, GuardM);
				DepthM[I] = H;
				++DepthClamps;
			}
			if (H > DryDepthM)
			{
				MaxOverLevelCm = FMath::Max(MaxOverLevelCm, BedCm[I] + (H + LidM[I]) * 100.f - LevelCm);
			}
			// WS2: the surface everything reads is the effective one, the water plus whatever solid stands in its
			// column, so a wheel that has squeezed its own cell dry still reads the level it is standing in and W1's
			// drag, W2's lift and the engine's flood are what they were before the lids existed.
			SurfaceCm[I] = BedCm[I] + (H + LidM[I]) * 100.f;
			if (H > DryDepthM)
			{
				++WetCellCount;
			}
			if (H <= DryDepthM)
			{
				VelXMps[I] = 0.f;
				VelYMps[I] = 0.f;
				continue;
			}
			const float Denominator = CellM * FMath::Max(H, MinDepthM);
			const float FX = 0.5f * (((X + 1 < SizeX) ? FluxX[I] : 0.f) + ((X > 0) ? FluxX[I - 1] : 0.f));
			const float FY = 0.5f * (((Y + 1 < SizeY) ? FluxY[I] : 0.f) + ((Y > 0) ? FluxY[I - SizeX] : 0.f));
			VelXMps[I] = FX / Denominator;
			VelYMps[I] = FY / Denominator;
		}
	}
	FillLidVelocities();
}

void FGTWaterField::Step(float DeltaSeconds, float InLevelCm, float HeadScale)
{
	if (!IsValid())
	{
		return;
	}
	LevelCm = InLevelCm;
	AppliedHeadDropCm = HeadDropCm * FMath::Max(0.f, HeadScale);
	float Dt = FMath::Max(1.e-4f, SubStepSeconds);
	// R1: the time this frame brought is added to whatever the last one could not simulate, bounded at
	// MaxAccumulatorSeconds. Over that bound the water really does lose time (a level load, a hitch of half a second),
	// and that is counted as a clamp of its own rather than quietly thrown away as it was before.
	const float Wanted = Accumulator + FMath::Clamp(DeltaSeconds, 0.f, 1.f);
	if (Wanted > MaxAccumulatorSeconds)
	{
		DeficitSeconds += Wanted - MaxAccumulatorSeconds;
		++AccumulatorDrops;
		++SubStepClamps;
	}
	Accumulator = FMath::Min(Wanted, MaxAccumulatorSeconds);
	int32 Steps = FMath::FloorToInt(Accumulator / Dt);
	// R1: what the frame asked for, before the cap.
	SubStepsAsked += FMath::Max(0, Steps);
	if (Steps <= 0)
	{
		StepMs = 0.f;
		// The lids still have to be taken in, or a frame the solver sits out would drop what the car stamped on it.
		PromoteLids(FMath::Max(0.f, DeltaSeconds));
		return;
	}
	// R1: a frame may burst past the cap while its sub-steps are cheap enough to fit the budget (the last stepping
	// frame's own cost per sub-step is the estimate), and past that it takes coarse steps rather than losing time.
	int32 Cap = MaxSubSteps;
	// What a sub-step costs, averaged over every one this field has run: the last stepping frame's own StepMs divided
	// by its sub-steps counts the per-frame work (the sources, the boundary, the derived fields) as though it were
	// per sub-step, and on a frame that ran one sub-step that reads three times the truth and closes the burst off.
	const float MeanSubMs = SubStepsRun > 0 ? static_cast<float>(StepMsSum / SubStepsRun) : 0.f;
	if (Steps > MaxSubSteps && MeanSubMs * FMath::Min(Steps, MaxSubStepsBurst) <= BurstBudgetMs)
	{
		Cap = FMath::Max(MaxSubSteps, FMath::Min(Steps, MaxSubStepsBurst));
	}
	if (Steps > Cap)
	{
		float DeepestM = 0.f;
		for (int32 Index = 0; Index < DepthM.Num(); ++Index)
		{
			DeepestM = FMath::Max(DeepestM, DepthM[Index]);
		}
		const float Coarse = FMath::Max(Dt, CoarseSubStepSeconds);
		const float Cfl = FMath::Sqrt(9.81f * FMath::Max(0.01f, DeepestM)) * Coarse / FMath::Max(0.01f, CellCm * 0.01f);
		if (Cfl <= CflLimit)
		{
			Dt = Coarse;
			Steps = FMath::FloorToInt(Accumulator / Dt);
			// A frame that has fallen back to coarse steps may take up to MaxSubStepsBurst of them: that is 0.27 s of
			// water, which covers anything the 0.25 s accumulator can hold, and it is the only way the fallback
			// actually catches a 160 ms frame up. Four of them cover 0.133 s and left 0.033 s on the floor every time
			// a screenshot hitched (measured over two picture runs).
			Cap = FMath::Max(Cap, FMath::Min(Steps, MaxSubStepsBurst));
			LastCoarseCfl = Cfl;
			++CoarseFrames;
			if (CoarseFrames <= 5)
			{
				UE_LOG(LogTemp, Display, TEXT("FGTWaterField: R1 coarse step %.4f s for one frame (%d sub-steps of it against the cap of %d fine ones); the deepest cell is %.2f m, so the Courant number at %.1f cm cells is %.2f against the %.2f allowed"),
					Dt, Steps, Cap, DeepestM, CellCm, Cfl, CflLimit);
			}
		}
	}
	if (Steps > Cap)
	{
		// The field runs slow rather than blowing up; the dropped time is logged by the count and, since R1, in seconds.
		++SubStepClamps;
		DeficitSeconds += (Steps - Cap) * Dt;
		Steps = Cap;
		Accumulator = 0.f;
	}
	else
	{
		Accumulator -= Steps * Dt;
	}
	const double Started = FPlatformTime::Seconds();
	// WS2's sources go in once a frame, not once a sub-step: the lids are what the car stamped since the last one,
	// and the wind and the rain are forcings whose rate is per second either way. Both only move fluxes or trade
	// depth between neighbours, so neither changes the field's volume.
	const float SourceDt = Steps * Dt;
	// The sponge follows a level that jumps only as fast as SpongeLevelTauS lets it (see ApplySponge).
	SpongeLevelCm += (LevelCm - SpongeLevelCm) * FMath::Clamp(SourceDt / FMath::Max(0.1f, SpongeLevelTauS), 0.f, 1.f);
	PromoteLids(SourceDt);
	if (HasRiverReference())
	{
		// Preserve the existing volume-neutral gust forcing in the river's disturbance momentum.
		RiverNextX=FluxX; RiverNextY=FluxY;
		ApplyWind(SourceDt);
		for(int32 I=0; I<NumCells(); ++I)
		{
			RiverWaveX[I]+=FluxX[I]-RiverNextX[I];
			RiverWaveY[I]+=FluxY[I]-RiverNextY[I];
		}
	}
	else ApplyWind(SourceDt);
	ApplyRain(SourceDt);
	for (int32 Index = 0; Index < Steps; ++Index)
	{
		SubStep(Dt);
	}
	if (HasRiverReference())
	{
		// RiverSubStep owns its spatial reference boundaries, not the ford's two flat heads.
	}
	else if (bOpenEnds)
	{
		LearnEdgeMeans(SourceDt);
	}
	else
	{
		ApplyBoundary();
	}
	UpdateDerived();
	StepMs = static_cast<float>((FPlatformTime::Seconds() - Started) * 1000.0);
	StepMsSum += StepMs;
	++StepMsCount;
	StepMsMax = FMath::Max(StepMsMax, StepMs);
	SubStepsRun += Steps;
	LastSubStepMs = StepMs / FMath::Max(1, Steps);
}

// ---- RIVERBED S3: the basin (docs/RIVERBED_PLAN.md, VEHICLE_BUILD_SYSTEM 53) ----------------------------------------

int32 FGTWaterBasin::CellAt(const FVector2D& XYCm) const
{
	if (Size <= 0)
	{
		return INDEX_NONE;
	}
	const FVector2D D = XYCm - OriginCm;
	const int32 X = FMath::FloorToInt(static_cast<float>(FVector2D::DotProduct(D, AxisX)) / CellCm);
	const int32 Y = FMath::FloorToInt(static_cast<float>(FVector2D::DotProduct(D, AxisY)) / CellCm);
	return (X >= 0 && Y >= 0 && X < Size && Y < Size) ? Index(X, Y) : INDEX_NONE;
}

void FGTWaterBasin::Fill(const FVector2D& CentreCm, const FVector2D& FlowDir, float InCellCm, float SearchCm, float InLevelCm,
	float BoxHalfAlongCm, float BoxHalfAcrossCm, const TFunction<float(const FVector2D&)>& BedSamplerCm, TOptional<FVector2D> AuthoredSeed)
{
	const double Started = FPlatformTime::Seconds();
	CellCm = FMath::Max(1.f, InCellCm);
	LevelCm = InLevelCm;
	AxisX = FlowDir.IsNearlyZero() ? FVector2D(1.0, 0.0) : FlowDir.GetSafeNormal();
	AxisY = FVector2D(-AxisX.Y, AxisX.X);
	const int32 HalfCells = FMath::Clamp(FMath::CeilToInt(0.5f * SearchCm / CellCm - 0.001f), 2, 4096);
	Size = 2 * HalfCells;
	OriginCm = CentreCm - AxisX * (HalfCells * CellCm) - AxisY * (HalfCells * CellCm);
	const int32 Count = Size * Size;
	BedCm.SetNumUninitialized(Count);
	Sampled.Init(0, Count);
	Wet.Init(0, Count);
	SeedIndex = INDEX_NONE;
	SeedBedCm = 0.f;
	MinX = MinY = Size;
	MaxX = MaxY = -1;
	Cells = 0;
	bHitSearchEdge = false;
	BoxUnderLevel = RegionInBox = HollowCells = Hollows = 0;
	HollowDeepestCm = 0.f;
	SampledCells = 0;
	auto Bed = [this, &BedSamplerCm](int32 X, int32 Y) -> float
	{
		const int32 I = Index(X, Y);
		if (!Sampled[I])
		{
			BedCm[I] = BedSamplerCm ? BedSamplerCm(CellCentreCm(X, Y)) : 0.f;
			Sampled[I] = 1;
			++SampledCells;
		}
		return BedCm[I];
	};
	// The placed box on the same lattice: the sheet's field (120 x 216 cells on forda) is exactly these cells.
	const int32 HalfAlong = FMath::Clamp(FMath::CeilToInt(BoxHalfAlongCm / CellCm - 0.001f), 1, HalfCells);
	const int32 HalfAcross = FMath::Clamp(FMath::CeilToInt(BoxHalfAcrossCm / CellCm - 0.001f), 1, HalfCells);
	BoxMinX = HalfCells - HalfAlong;
	BoxMaxX = HalfCells + HalfAlong - 1;
	BoxMinY = HalfCells - HalfAcross;
	BoxMaxY = HalfCells + HalfAcross - 1;
	float Lowest = TNumericLimits<float>::Max();
	for (int32 Y = BoxMinY; Y <= BoxMaxY; ++Y)
	{
		for (int32 X = BoxMinX; X <= BoxMaxX; ++X)
		{
			const float B = Bed(X, Y);
			if (B < Lowest)
			{
				Lowest = B;
				SeedIndex = Index(X, Y);
			}
		}
	}
	if(AuthoredSeed.IsSet())
	{
		SeedIndex=CellAt(AuthoredSeed.GetValue());
		if(SeedIndex!=INDEX_NONE)Lowest=Bed(SeedIndex%Size,SeedIndex/Size);
	}
	if (SeedIndex == INDEX_NONE || Lowest >= LevelCm)
	{
		SeedIndex = INDEX_NONE;
		FillMs = (FPlatformTime::Seconds() - Started) * 1000.0;
		return;
	}
	SeedBedCm = Lowest;
	TArray<int32> Queue;
	Queue.Reserve(65536);
	Wet[SeedIndex] = 1;
	Queue.Add(SeedIndex);
	for (int32 Head = 0; Head < Queue.Num(); ++Head)
	{
		const int32 I = Queue[Head];
		const int32 X = I % Size;
		const int32 Y = I / Size;
		++Cells;
		MinX = FMath::Min(MinX, X);
		MaxX = FMath::Max(MaxX, X);
		MinY = FMath::Min(MinY, Y);
		MaxY = FMath::Max(MaxY, Y);
		if (X == 0 || Y == 0 || X == Size - 1 || Y == Size - 1)
		{
			bHitSearchEdge = true;
		}
		const int32 NX[4] = { X - 1, X + 1, X, X };
		const int32 NY[4] = { Y, Y, Y - 1, Y + 1 };
		for (int32 K = 0; K < 4; ++K)
		{
			if (NX[K] < 0 || NY[K] < 0 || NX[K] >= Size || NY[K] >= Size)
			{
				continue;
			}
			const int32 J = Index(NX[K], NY[K]);
			if (!Wet[J] && Bed(NX[K], NY[K]) < LevelCm)
			{
				Wet[J] = 1;
				Queue.Add(J);
			}
		}
	}
	// Inside the placed box: what stands under the level, how much of it the fill reached, and the rest in hollows.
	TArray<uint8> Seen;
	Seen.Init(0, Count);
	TArray<int32> Hollow;
	for (int32 Y = BoxMinY; Y <= BoxMaxY; ++Y)
	{
		for (int32 X = BoxMinX; X <= BoxMaxX; ++X)
		{
			const int32 I = Index(X, Y);
			if (BedCm[I] >= LevelCm)
			{
				continue;
			}
			++BoxUnderLevel;
			if (Wet[I])
			{
				++RegionInBox;
				continue;
			}
			++HollowCells;
			HollowDeepestCm = FMath::Max(HollowDeepestCm, LevelCm - BedCm[I]);
			if (Seen[I])
			{
				continue;
			}
			++Hollows;
			Hollow.Reset();
			Seen[I] = 1;
			Hollow.Add(I);
			for (int32 Head = 0; Head < Hollow.Num(); ++Head)
			{
				const int32 HX = Hollow[Head] % Size;
				const int32 HY = Hollow[Head] / Size;
				const int32 NX[4] = { HX - 1, HX + 1, HX, HX };
				const int32 NY[4] = { HY, HY, HY - 1, HY + 1 };
				for (int32 K = 0; K < 4; ++K)
				{
					if (NX[K] < BoxMinX || NY[K] < BoxMinY || NX[K] > BoxMaxX || NY[K] > BoxMaxY)
					{
						continue;
					}
					const int32 J = Index(NX[K], NY[K]);
					if (!Seen[J] && !Wet[J] && BedCm[J] < LevelCm)
					{
						Seen[J] = 1;
						Hollow.Add(J);
					}
				}
			}
		}
	}
	FillMs = (FPlatformTime::Seconds() - Started) * 1000.0;
}

void FGTWaterBasin::ReleaseLattice()
{
	BedCm.Empty();
	Sampled.Empty();
	Wet.Empty();
}
