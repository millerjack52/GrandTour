// Benmore integration B2 (docs/BENMORE_INTEGRATION_PLAN.md B2): UGTMudSubsystem's deform zones - the units, their streaming, the
// LRU cache of released fields and the coverage texture the landscape cuts its hole by. The strips have no AGTDeformZone: nothing
// here runs there.

#include "Terrain/GTMudSubsystem.h"

#include "Terrain/GTDeformZone.h"
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTSurfacePhysMaterial.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Vehicle/GTCarPawn.h"
#include "Async/ParallelFor.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "LandscapeProxy.h"
#include "Misc/Compression.h"
#include "TimerManager.h"

namespace
{
	const FName CoverageParam(TEXT("GTDeformCoverage"));
	const FName CoverageWindowParam(TEXT("GTDeformWindow"));

	float BoxDistance(const FBox2D& Box, const FVector2D& P)
	{
		const double DX = FMath::Max3(Box.Min.X - P.X, 0.0, P.X - Box.Max.X);
		const double DY = FMath::Max3(Box.Min.Y - P.Y, 0.0, P.Y - Box.Max.Y);
		return static_cast<float>(FMath::Sqrt(DX * DX + DY * DY));
	}

	bool Overlaps(const FBox2D& A, const FBox2D& B)
	{
		return A.Min.X < B.Max.X && B.Min.X < A.Max.X && A.Min.Y < B.Max.Y && B.Min.Y < A.Max.Y;
	}

	/** Benmore B2c: the live mud-zone patches of every game world, for UGTMudSubsystem::IsInLiveMudZone (the spray's gravel test). */
	TArray<TWeakObjectPtr<AGTMudPatch>> GLiveMudZonePatches;

	/** One changed cell in the cache's raw form. */
#pragma pack(push, 1)
	struct FZoneCellRecord
	{
		int32 Index;
		float Height;
		float Lump;
		float OffsetX;
		float OffsetY;
		float Heading;
		float Phase;
		uint8 Tracks;
	};
#pragma pack(pop)
}

void UGTMudSubsystem::GatherZones(UWorld& InWorld)
{
	Zones.Reset();
	ZoneUnits.Reset();
	for (TActorIterator<AGTDeformZone> It(&InWorld); It; ++It)
	{
		It->Prepare();
		Zones.Add(*It);
	}
	if (Zones.Num() == 0)
	{
		return;
	}
	Zones.Sort([](const AGTDeformZone& A, const AGTDeformZone& B) { return A.ZoneId != B.ZoneId ? A.ZoneId < B.ZoneId : A.GetName() < B.GetName(); });
	const float Tile = ZoneTileCm;
	const float Cell = ZoneCellCm;
	int32 TileUnits = 0;
	int32 WholeUnits = 0;
	for (int32 ZoneIndex = 0; ZoneIndex < Zones.Num(); ++ZoneIndex)
	{
		AGTDeformZone* Zone = Zones[ZoneIndex];
		const FBox2D Bounds = Zone->GetBoundsCm();
		if (!Bounds.bIsValid)
		{
			continue;
		}
		if (!Zone->bTiled)
		{
			// A mud zone: one patch over its box, snapped out to whole cells.
			FZoneUnit Unit;
			Unit.ZoneIndex = ZoneIndex;
			Unit.bWhole = true;
			const FVector2D Min(FMath::FloorToDouble(Bounds.Min.X / Cell) * Cell - Cell, FMath::FloorToDouble(Bounds.Min.Y / Cell) * Cell - Cell);
			const FVector2D Max(FMath::CeilToDouble(Bounds.Max.X / Cell) * Cell + Cell, FMath::CeilToDouble(Bounds.Max.Y / Cell) * Cell + Cell);
			Unit.OwnBox = FBox2D(Min, Max);
			Unit.FieldBox = Unit.OwnBox;
			Unit.Cells = FMath::RoundToInt((Max.X - Min.X) / Cell) * FMath::RoundToInt((Max.Y - Min.Y) / Cell);
			ZoneUnits.Add(MoveTemp(Unit));
			++WholeUnits;
			continue;
		}
		// A tiled zone: every world tile its outline reaches (a 1 m probe grid over the tile finds a member).
		const int32 I0 = FMath::FloorToInt(Bounds.Min.X / Tile);
		const int32 I1 = FMath::FloorToInt(Bounds.Max.X / Tile);
		const int32 J0 = FMath::FloorToInt(Bounds.Min.Y / Tile);
		const int32 J1 = FMath::FloorToInt(Bounds.Max.Y / Tile);
		int32 Slot = 0;
		for (int32 J = J0; J <= J1; ++J)
		{
			for (int32 I = I0; I <= I1; ++I)
			{
				const FBox2D Own(FVector2D(I * Tile, J * Tile), FVector2D((I + 1) * Tile, (J + 1) * Tile));
				bool bAny = false;
				for (double Y = Own.Min.Y + 50.0; Y < Own.Max.Y && !bAny; Y += 100.0)
				{
					for (double X = Own.Min.X + 50.0; X < Own.Max.X; X += 100.0)
					{
						if (Zone->IsMember(FVector2D(X, Y)))
						{
							bAny = true;
							break;
						}
					}
				}
				if (!bAny)
				{
					continue;
				}
				FZoneUnit Unit;
				Unit.ZoneIndex = ZoneIndex;
				Unit.Slot = Slot++;
				Unit.Tile = FIntPoint(I, J);
				Unit.OwnBox = Own;
				Unit.FieldBox = Own.ExpandBy(Cell);
				const int32 Side = FMath::RoundToInt(Tile / Cell) + 2;
				Unit.Cells = Side * Side;
				ZoneUnits.Add(MoveTemp(Unit));
				++TileUnits;
			}
		}
	}
	UE_LOG(LogTemp, Display, TEXT("UGTMudSubsystem: Benmore B2 - %d deform zone(s), %d unit(s): %d tile(s) of %.0f m, %d whole mud zone(s); at most %d tile-equivalents live, on within %.0f m, off past %.0f m, cache %lld MB"),
		Zones.Num(), ZoneUnits.Num(), TileUnits, Tile * 0.01f, WholeUnits, MaxActiveZoneTiles, ZoneActivateCm * 0.01f, ZoneReleaseCm * 0.01f, ZoneCacheCapBytes >> 20);
	Coverage.Init(FColor(0, 0, 0, 0), CoverageSize * CoverageSize);
	CoverageTexture = UTexture2D::CreateTransient(CoverageSize, CoverageSize, PF_B8G8R8A8);
	if (CoverageTexture)
	{
		CoverageTexture->SRGB = false;
		CoverageTexture->Filter = TF_Bilinear;
		CoverageTexture->AddressX = TA_Clamp;
		CoverageTexture->AddressY = TA_Clamp;
		CoverageTexture->CompressionSettings = TC_VectorDisplacementmap;
		if (FTexturePlatformData* PlatformData = CoverageTexture->GetPlatformData())
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
		CoverageTexture->UpdateResource();
		for (TActorIterator<ALandscapeProxy> It(&InWorld); It; ++It)
		{
			It->SetLandscapeMaterialTextureParameterValue(CoverageParam, CoverageTexture);
			It->SetLandscapeMaterialVectorParameterValue(CoverageWindowParam, FLinearColor(0.f, 0.f, 1.f, 0.f));
		}
	}
	InWorld.GetTimerManager().SetTimer(ZoneTimer, FTimerDelegate::CreateUObject(this, &UGTMudSubsystem::OnZoneTimer), 0.1f, true, 0.f);
}

void UGTMudSubsystem::OnZoneTimer()
{
	StreamZones(false);
}

int32 UGTMudSubsystem::StreamZonesNow()
{
	StreamZones(true);
	return GetActiveZoneUnits();
}

void UGTMudSubsystem::SetZoneFocusForTest(FVector LocationCm, bool bOn)
{
	TestFocus = LocationCm;
	bTestFocus = bOn;
}

int32 UGTMudSubsystem::GetActiveZoneUnits() const
{
	int32 Count = 0;
	for (const FZoneUnit& Unit : ZoneUnits)
	{
		Count += Unit.Patch.IsValid() ? 1 : 0;
	}
	return Count;
}

int32 UGTMudSubsystem::GetActiveZoneCells() const
{
	int32 Count = 0;
	for (const FZoneUnit& Unit : ZoneUnits)
	{
		Count += Unit.Patch.IsValid() ? Unit.Cells : 0;
	}
	return Count;
}

AGTDeformZone* UGTMudSubsystem::ZoneAt(const FVector2D& XYCm, const AGTDeformZone* Except) const
{
	for (AGTDeformZone* Zone : Zones)
	{
		if (Zone && Zone != Except && Zone->IsMember(XYCm))
		{
			return Zone;
		}
	}
	return nullptr;
}

void UGTMudSubsystem::GetZoneFoci(TArray<FVector2D>& Out) const
{
	Out.Reset();
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	// A test focus first: the coverage window follows the first focus (a capture's camera, wherever the car is parked).
	if (bTestFocus)
	{
		Out.Add(FVector2D(TestFocus));
	}
	for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
	{
		const APlayerController* PC = It->Get();
		if (!PC)
		{
			continue;
		}
		if (const APawn* Pawn = PC->GetPawn())
		{
			Out.Add(FVector2D(Pawn->GetActorLocation()));
		}
		if (PC->PlayerCameraManager)
		{
			Out.Add(FVector2D(PC->PlayerCameraManager->GetCameraLocation()));
		}
	}
	// The active vehicles: possessed, or driving (over 3 m/s; a parked fleet car settling on its springs is not).
	for (TActorIterator<AGTCarPawn> It(World); It; ++It)
	{
		if (It->IsPlayerControlled() || It->GetVelocity().SizeSquared2D() > 300.f * 300.f)
		{
			Out.Add(FVector2D(It->GetActorLocation()));
		}
	}
}

int32 UGTMudSubsystem::StreamZones(bool bAll)
{
	if (ZoneUnits.Num() == 0)
	{
		return 0;
	}
	TArray<FVector2D> Foci;
	GetZoneFoci(Foci);
	if (Foci.Num() == 0)
	{
		return GetActiveZoneUnits();
	}
	TArray<int32> Wanted;
	for (int32 Index = 0; Index < ZoneUnits.Num(); ++Index)
	{
		FZoneUnit& Unit = ZoneUnits[Index];
		float Best = TNumericLimits<float>::Max();
		for (const FVector2D& F : Foci)
		{
			Best = FMath::Min(Best, BoxDistance(Unit.OwnBox, F));
		}
		Unit.Distance = Best;
		const bool bLive = Unit.Patch.IsValid();
		if (Best <= (bLive ? ZoneReleaseCm : ZoneActivateCm))
		{
			Wanted.Add(Index);
		}
	}
	Wanted.Sort([this](int32 A, int32 B) { return ZoneUnits[A].Distance < ZoneUnits[B].Distance; });
	const int32 TileCells = FMath::Square(FMath::RoundToInt(ZoneTileCm / ZoneCellCm));
	const int64 CapCells = static_cast<int64>(MaxActiveZoneTiles) * TileCells;
	TSet<int32> Keep;
	int64 Sum = 0;
	for (const int32 Index : Wanted)
	{
		// The cap counts a tile as one (its overlap ring aside) and a whole mud zone by its cells.
		const int64 Cost = ZoneUnits[Index].bWhole ? ZoneUnits[Index].Cells : TileCells;
		if (Sum + Cost > CapCells && Keep.Num() > 0)
		{
			continue;
		}
		Sum += Cost;
		Keep.Add(Index);
	}
	bool bChanged = false;
	for (int32 Index = 0; Index < ZoneUnits.Num(); ++Index)
	{
		if (ZoneUnits[Index].Patch.IsValid() && !Keep.Contains(Index))
		{
			ReleaseZoneUnit(Index);
			bChanged = true;
		}
	}
	int32 Activated = 0;
	for (const int32 Index : Wanted)
	{
		if (!Keep.Contains(Index) || ZoneUnits[Index].Patch.IsValid())
		{
			continue;
		}
		if (!bAll && Activated > 0)
		{
			break;   // one a pass: the next pass (0.1 s on) takes the next nearest
		}
		if (ActivateZoneUnit(Index))
		{
			++Activated;
			bChanged = true;
		}
	}
	// The coverage window follows the first focus (the player's pawn), recentred in whole 2 m steps.
	const FVector2D Focus = Foci[0];
	const bool bMove = !bCoverageValid || FMath::Max(FMath::Abs(Focus.X - CoverageOrigin.X), FMath::Abs(Focus.Y - CoverageOrigin.Y)) > CoverageRecentreCm;
	if (bMove)
	{
		CoverageOrigin = FVector2D(FMath::RoundToDouble(Focus.X / 200.0) * 200.0, FMath::RoundToDouble(Focus.Y / 200.0) * 200.0);
	}
	if (bChanged || bMove)
	{
		RebuildCoverage(bMove);
	}
	return GetActiveZoneUnits();
}

bool UGTMudSubsystem::ActivateZoneUnit(int32 Index)
{
	UWorld* World = GetWorld();
	FZoneUnit& Unit = ZoneUnits[Index];
	AGTDeformZone* Zone = Zones.IsValidIndex(Unit.ZoneIndex) ? Zones[Unit.ZoneIndex].Get() : nullptr;
	if (!World || !Zone)
	{
		return false;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AGTMudPatch* Patch = World->SpawnActor<AGTMudPatch>(AGTMudPatch::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, Params);
	if (!Patch)
	{
		return false;
	}
	// The zone's section as the strips' BuildPatches gives one (the water table, the variant, the profile; a spec only for snow's).
	static const FGTTerrainSpec NoSpec;
	Patch->ApplySection(NoSpec, Zone->Section);
	TArray<FVector2D> Route;
	Zone->GetRouteLine(Route);
	Patch->SetZoneRoute(Route, Zone->GetTrackHalfWidthCm());
	if (!Zone->PatchMaterialPath.IsEmpty())
	{
		Patch->MaterialPath = Zone->PatchMaterialPath;   // B2c: a mud zone's M_GT_Mud_Zone (a profile's own path still wins in Init)
	}
	Patch->bZonePatch = true;
	Patch->Zone = Zone;
	Patch->ZoneOwnBoxCm = Unit.OwnBox;
	Patch->ZoneSurfaceTint = Zone->SurfaceTint;
	Patch->ZoneMudRow = Zone->MudRow.LoadSynchronous();
	Patch->ZoneBogRow = Zone->BogRow.LoadSynchronous();
	// The noise runs on across the zone's tiles: the lattice offset is the field's world cell, the seed the zone's.
	Patch->GetField().NoiseCellX = FMath::RoundToInt(Unit.FieldBox.Min.X / ZoneCellCm);
	Patch->GetField().NoiseCellY = FMath::RoundToInt(Unit.FieldBox.Min.Y / ZoneCellCm);
	Patch->GetField().NoiseSeed = 1 + Zone->ZoneId;
	TArray<uint8> Cached;
	const uint64 Key = ZoneUnitKey(Zone->ZoneId, Unit.Slot);
	if (FZoneCacheEntry* Entry = ZoneCache.Find(Key))
	{
		Cached.SetNumUninitialized(Entry->RawBytes);
		if (!FCompression::UncompressMemory(NAME_Zlib, Cached.GetData(), Entry->RawBytes, Entry->Bytes.GetData(), Entry->Bytes.Num()))
		{
			Cached.Reset();
		}
		ZoneCacheBytes -= Entry->Bytes.Num();
		ZoneCache.Remove(Key);
	}
	Patch->ZoneAfterField = [this, Index, Cached](AGTMudPatch& P) { ZoneAfterField(P, Index, Cached); };
	const int32 SectionIndex = 10000 + 1000 * Zone->ZoneId + Unit.Slot;
	Patch->Init(SectionIndex, Unit.FieldBox, ZoneCellCm);
	Patch->ZoneAfterField = nullptr;
	if (Zone->IsMud())
	{
		Patch->BakeZoneLayers([Zone](const FVector2D& XY) { return Zone->BogWeightAt(XY); });
	}
	Patch->HoleSlot = -1;
	Patches.Add(Patch);
	if (UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>())
	{
		Water->RegisterPatch(Patch);
	}
	Unit.Patch = Patch;
	++LiveZoneUnits;
	++ZoneActivations;
	if (bCoverageValid && CoverageTexture)
	{
		Patch->SetZoneCoverage(CoverageTexture, FLinearColor(CoverageOrigin.X, CoverageOrigin.Y, CoverageSize * CoverageTexelCm, 1.f));
	}
	if (Zone->IsMud())
	{
		GLiveMudZonePatches.Add(Patch);
	}
	UE_LOG(LogTemp, Display, TEXT("UGTMudSubsystem: zone %d (%s) unit %d live%s - %s, field %d x %d cells, %d quads drawn, %.1f m off%s"),
		Zone->ZoneId, *Zone->Label, Unit.Slot, Unit.bWhole ? TEXT(" (whole)") : *FString::Printf(TEXT(" (tile %d,%d)"), Unit.Tile.X, Unit.Tile.Y),
		Zone->IsMud() ? *StaticEnum<EGTMudVariant>()->GetNameStringByValue(static_cast<int64>(Patch->MudVariant)) : TEXT("profiled"),
		Patch->CellsX, Patch->CellsY, Patch->ZoneDrawnQuads, Unit.Distance * 0.01f, Cached.Num() > 0 ? TEXT(", cached cells restored") : TEXT(""));
	return true;
}

void UGTMudSubsystem::ZoneAfterField(AGTMudPatch& Patch, int32 Index, const TArray<uint8>& Cached)
{
	FZoneUnit& Unit = ZoneUnits[Index];
	AGTDeformZone* Zone = Zones[Unit.ZoneIndex];
	FGTMudField& F = Patch.GetField();
	const int32 SX = F.SizeX;
	const int32 SY = F.SizeY;
	const int32 Cells = SX * SY;
	Patch.ZoneCells.Init(0, Cells);
	TArray<float> Inside;
	Inside.Init(-1000.f, Cells);
	// 1. The zone's cells.
	ParallelFor(SY, [&](int32 Y)
	{
		for (int32 X = 0; X < SX; ++X)
		{
			const FVector2D C = F.OriginCm + FVector2D(X + 0.5, Y + 0.5) * F.CellCm;
			float In = 0.f;
			if (Zone->IsMember(C, &In))
			{
				Patch.ZoneCells[Y * SX + X] = 2;
				Inside[Y * SX + X] = In;
			}
		}
	});
	// 2. The ring: a cell beside a zone cell that no other zone holds (the joint between two stretches draws no overlap).
	TArray<AGTDeformZone*> Others;
	for (AGTDeformZone* Other : Zones)
	{
		if (Other && Other != Zone && Overlaps(Other->GetBoundsCm(), Unit.FieldBox))
		{
			Others.Add(Other);
		}
	}
	TArray<uint8> Ring;
	Ring.Init(0, Cells);
	ParallelFor(SY, [&](int32 Y)
	{
		for (int32 X = 0; X < SX; ++X)
		{
			if (Patch.ZoneCells[Y * SX + X] != 0)
			{
				continue;
			}
			bool bBeside = false;
			for (int32 DY = -1; DY <= 1 && !bBeside; ++DY)
			{
				for (int32 DX = -1; DX <= 1; ++DX)
				{
					const int32 NX = X + DX;
					const int32 NY = Y + DY;
					if (NX >= 0 && NY >= 0 && NX < SX && NY < SY && Patch.ZoneCells[NY * SX + NX] == 2)
					{
						bBeside = true;
						break;
					}
				}
			}
			if (!bBeside)
			{
				continue;
			}
			const FVector2D C = F.OriginCm + FVector2D(X + 0.5, Y + 0.5) * F.CellCm;
			bool bOther = false;
			for (const AGTDeformZone* Other : Others)
			{
				if (Other->IsMember(C))
				{
					bOther = true;
					break;
				}
			}
			Ring[Y * SX + X] = bOther ? 0 : 1;
		}
	});
	for (int32 I = 0; I < Cells; ++I)
	{
		Patch.ZoneCells[I] = FMath::Max(Patch.ZoneCells[I], Ring[I]);
	}
	// B2c: how much of the patch draws per cell (a mud zone's feather in from its outline; a gravel zone whole), for the coverage.
	Patch.ZoneOpacity.Init(0, Cells);
	ParallelFor(SY, [&](int32 Y)
	{
		for (int32 X = 0; X < SX; ++X)
		{
			if (Patch.ZoneCells[Y * SX + X] == 2)
			{
				const FVector2D C = F.OriginCm + FVector2D(X + 0.5, Y + 0.5) * F.CellCm;
				Patch.ZoneOpacity[Y * SX + X] = static_cast<uint8>(FMath::RoundToInt(255.f * Zone->OpacityFromInside(C, Inside[Y * SX + X])));
			}
		}
	});
	// 3. A mud zone's pre-churn fades to the flat ground at its outline (its box's rim is the strips'; here the outline is the edge).
	// A road's outline is the road's own edge (the strips' box reaches 2 m past it), so across a road the fade is held to a fifth of the
	// half width (64 cm on the 6.4 m loop): the old tracks run across the running surface.
	if (Zone->IsMud())
	{
		const float Fade = Zone->Shape == EGTDeformZoneShape::Road ? FMath::Min(Zone->EdgeFadeCm, 0.2f * Zone->GetHalfWidthCm()) : Zone->EdgeFadeCm;
		Patch.FadeZonePreChurn(Inside, Fade);
	}
	// 4. The baseline the release diffs against, then the cached cells back.
	Unit.BaseHeight = F.HeightCm;
	Unit.BaseLump = F.LumpCm;
	Unit.BaseOffset = F.OffsetCm;
	Unit.BaseTracks = F.Tracks;
	Unit.BaseHeading = F.HeadingTurns;
	Unit.BasePhase = F.PhaseTurns;
	if (Cached.Num() >= static_cast<int32>(sizeof(int32)))
	{
		int32 Count = 0;
		FMemory::Memcpy(&Count, Cached.GetData(), sizeof(int32));
		const FZoneCellRecord* Records = reinterpret_cast<const FZoneCellRecord*>(Cached.GetData() + sizeof(int32));
		const int32 Max = (Cached.Num() - static_cast<int32>(sizeof(int32))) / static_cast<int32>(sizeof(FZoneCellRecord));
		for (int32 K = 0; K < FMath::Min(Count, Max); ++K)
		{
			const FZoneCellRecord& R = Records[K];
			if (R.Index < 0 || R.Index >= Cells)
			{
				continue;
			}
			F.HeightCm[R.Index] = R.Height;
			if (F.LumpCm.IsValidIndex(R.Index))
			{
				F.LumpCm[R.Index] = R.Lump;
			}
			F.OffsetCm[R.Index] = FVector2f(R.OffsetX, R.OffsetY);
			F.HeadingTurns[R.Index] = R.Heading;
			F.PhaseTurns[R.Index] = R.Phase;
			F.Tracks[R.Index] = R.Tracks;
		}
		++ZoneRestores;
	}
}

void UGTMudSubsystem::ReleaseZoneUnit(int32 Index)
{
	FZoneUnit& Unit = ZoneUnits[Index];
	AGTMudPatch* Patch = Unit.Patch.Get();
	AGTDeformZone* Zone = Zones.IsValidIndex(Unit.ZoneIndex) ? Zones[Unit.ZoneIndex].Get() : nullptr;
	if (Patch && Zone)
	{
		// The changed cells (any zone or ring cell that differs from its value at activation), packed and compressed into the cache.
		const FGTMudField& F = Patch->GetField();
		const int32 Cells = F.SizeX * F.SizeY;
		TArray<uint8> Raw;
		Raw.AddZeroed(sizeof(int32));
		int32 Count = 0;
		if (Unit.BaseHeight.Num() == Cells && Patch->ZoneCells.Num() == Cells)
		{
			for (int32 I = 0; I < Cells; ++I)
			{
				if (Patch->ZoneCells[I] == 0)
				{
					continue;
				}
				const float Lump = F.LumpCm.IsValidIndex(I) ? F.LumpCm[I] : 0.f;
				const float BaseLump = Unit.BaseLump.IsValidIndex(I) ? Unit.BaseLump[I] : 0.f;
				if (F.HeightCm[I] == Unit.BaseHeight[I] && Lump == BaseLump && F.OffsetCm[I] == Unit.BaseOffset[I] && F.Tracks[I] == Unit.BaseTracks[I]
					&& F.HeadingTurns[I] == Unit.BaseHeading[I] && F.PhaseTurns[I] == Unit.BasePhase[I])
				{
					continue;
				}
				FZoneCellRecord R;
				R.Index = I;
				R.Height = F.HeightCm[I];
				R.Lump = Lump;
				R.OffsetX = F.OffsetCm[I].X;
				R.OffsetY = F.OffsetCm[I].Y;
				R.Heading = F.HeadingTurns[I];
				R.Phase = F.PhaseTurns[I];
				R.Tracks = F.Tracks[I];
				Raw.Append(reinterpret_cast<const uint8*>(&R), sizeof(R));
				++Count;
			}
		}
		FMemory::Memcpy(Raw.GetData(), &Count, sizeof(int32));
		if (Count > 0)
		{
			FZoneCacheEntry Entry;
			int32 Bound = FCompression::CompressMemoryBound(NAME_Zlib, Raw.Num());
			Entry.Bytes.SetNumUninitialized(Bound);
			int32 Size = Bound;
			if (FCompression::CompressMemory(NAME_Zlib, Entry.Bytes.GetData(), Size, Raw.GetData(), Raw.Num()))
			{
				Entry.Bytes.SetNum(Size);
				Entry.RawBytes = Raw.Num();
				Entry.Cells = Count;
				Entry.Stamp = ++ZoneCacheClock;
				ZoneCacheBytes += Entry.Bytes.Num();
				ZoneCache.Add(ZoneUnitKey(Zone->ZoneId, Unit.Slot), MoveTemp(Entry));
			}
			// The LRU cap: the least recently released go first.
			while (ZoneCacheBytes > ZoneCacheCapBytes && ZoneCache.Num() > 0)
			{
				uint64 OldestKey = 0;
				uint64 OldestStamp = TNumericLimits<uint64>::Max();
				for (const TPair<uint64, FZoneCacheEntry>& Pair : ZoneCache)
				{
					if (Pair.Value.Stamp < OldestStamp)
					{
						OldestStamp = Pair.Value.Stamp;
						OldestKey = Pair.Key;
					}
				}
				ZoneCacheBytes -= ZoneCache[OldestKey].Bytes.Num();
				ZoneCache.Remove(OldestKey);
				++ZoneCacheEvicted;
			}
		}
		if (UWorld* World = GetWorld())
		{
			if (UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>())
			{
				Water->UnregisterPatch(Patch);
			}
		}
		Patches.Remove(Patch);
		GLiveMudZonePatches.RemoveAll([Patch](const TWeakObjectPtr<AGTMudPatch>& E) { return !E.IsValid() || E.Get() == Patch; });
		Patch->Destroy();
		UE_LOG(LogTemp, Display, TEXT("UGTMudSubsystem: zone %d unit %d released, %d changed cell(s) cached (cache %d entries, %.2f MB)"),
			Zone->ZoneId, Unit.Slot, Count, ZoneCache.Num(), ZoneCacheBytes / (1024.0 * 1024.0));
		--LiveZoneUnits;
		++ZoneReleases;
	}
	Unit.Patch = nullptr;
	Unit.BaseHeight.Empty();
	Unit.BaseLump.Empty();
	Unit.BaseOffset.Empty();
	Unit.BaseTracks.Empty();
	Unit.BaseHeading.Empty();
	Unit.BasePhase.Empty();
}

void UGTMudSubsystem::RebuildCoverage(bool bForce)
{
	if (!CoverageTexture || Coverage.Num() != CoverageSize * CoverageSize)
	{
		return;
	}
	// Benmore B2c: A (and R) how much of a live patch draws in a texel - the mean of its four cells' ZoneOpacity, blurred two texels
	// (a 5-tap tent each way) and held to the texels the patch's own drawn cells (zone or ring) reach, so a neighbouring patch's edge
	// never bleeds into it; B a mud zone's variant code (50 x (variant + 1)). The landscape draws a pixel where its dither is at or over
	// A (faded out over 40-60 m from the camera), the patch where it is under: one or the other, never both.
	FMemory::Memzero(Coverage.GetData(), Coverage.Num() * sizeof(FColor));
	const float Texel = CoverageTexelCm;
	const FVector2D Min = CoverageOrigin - FVector2D(0.5 * CoverageSize * Texel, 0.5 * CoverageSize * Texel);
	const int32 Sub = FMath::Max(1, FMath::RoundToInt(Texel / ZoneCellCm));   // cells per texel side (2 at 25 cm)
	const int32 Blur = 2;
	for (const FZoneUnit& Unit : ZoneUnits)
	{
		const AGTMudPatch* Patch = Unit.Patch.Get();
		if (!Patch || Patch->ZoneOpacity.Num() == 0)
		{
			continue;
		}
		const AGTDeformZone* Zone = Zones[Unit.ZoneIndex];
		const FGTMudField& F = Patch->GetField();
		const int32 TX0 = FMath::Max(0, FMath::FloorToInt((Unit.OwnBox.Min.X - Min.X) / Texel) - Blur);
		const int32 TY0 = FMath::Max(0, FMath::FloorToInt((Unit.OwnBox.Min.Y - Min.Y) / Texel) - Blur);
		const int32 TX1 = FMath::Min(CoverageSize - 1, FMath::CeilToInt((Unit.OwnBox.Max.X - Min.X) / Texel) - 1 + Blur);
		const int32 TY1 = FMath::Min(CoverageSize - 1, FMath::CeilToInt((Unit.OwnBox.Max.Y - Min.Y) / Texel) - 1 + Blur);
		if (TX0 > TX1 || TY0 > TY1)
		{
			continue;   // a live unit outside the window (a second focus far from the first)
		}
		const int32 W = TX1 - TX0 + 1;
		const int32 H = TY1 - TY0 + 1;
		TArray<float> A;
		A.Init(0.f, W * H);
		TArray<uint8> Drawn;
		Drawn.Init(0, W * H);
		for (int32 Y = 0; Y < H; ++Y)
		{
			for (int32 X = 0; X < W; ++X)
			{
				float Sum = 0.f;
				uint8 Any = 0;
				for (int32 SYI = 0; SYI < Sub; ++SYI)
				{
					for (int32 SXI = 0; SXI < Sub; ++SXI)
					{
						const FVector2D C = Min + FVector2D((TX0 + X) * Texel + (SXI + 0.5) * ZoneCellCm, (TY0 + Y) * Texel + (SYI + 0.5) * ZoneCellCm);
						if (C.X < Unit.OwnBox.Min.X || C.Y < Unit.OwnBox.Min.Y || C.X >= Unit.OwnBox.Max.X || C.Y >= Unit.OwnBox.Max.Y)
						{
							continue;
						}
						const int32 I = F.CellIndexAt(C);
						if (I == INDEX_NONE || !Patch->ZoneCells.IsValidIndex(I) || Patch->ZoneCells[I] == 0)
						{
							continue;
						}
						Any = 1;
						Sum += Patch->ZoneOpacity[I] / 255.f;
					}
				}
				A[Y * W + X] = Sum / (Sub * Sub);
				Drawn[Y * W + X] = Any;
			}
		}
		// The two-texel blur (tent 1 2 3 2 1 / 9), x then y.
		const float K[5] = { 1.f / 9.f, 2.f / 9.f, 3.f / 9.f, 2.f / 9.f, 1.f / 9.f };
		TArray<float> T;
		T.Init(0.f, W * H);
		for (int32 Y = 0; Y < H; ++Y)
		{
			for (int32 X = 0; X < W; ++X)
			{
				float V = 0.f;
				for (int32 D = -Blur; D <= Blur; ++D)
				{
					V += K[D + Blur] * A[Y * W + FMath::Clamp(X + D, 0, W - 1)];
				}
				T[Y * W + X] = V;
			}
		}
		for (int32 Y = 0; Y < H; ++Y)
		{
			for (int32 X = 0; X < W; ++X)
			{
				float V = 0.f;
				for (int32 D = -Blur; D <= Blur; ++D)
				{
					V += K[D + Blur] * T[FMath::Clamp(Y + D, 0, H - 1) * W + X];
				}
				A[Y * W + X] = Drawn[Y * W + X] ? V : 0.f;
			}
		}
		const uint8 Code = Zone->IsMud() ? static_cast<uint8>(50 * (1 + static_cast<int32>(Patch->MudVariant))) : 0;
		for (int32 Y = 0; Y < H; ++Y)
		{
			for (int32 X = 0; X < W; ++X)
			{
				if (A[Y * W + X] <= 0.f)
				{
					continue;
				}
				FColor& C = Coverage[(TY0 + Y) * CoverageSize + TX0 + X];
				const uint8 V = static_cast<uint8>(FMath::Min(255, C.A + FMath::RoundToInt(255.f * A[Y * W + X])));
				C.A = V;
				C.R = V;
				if (Code)
				{
					C.B = Code;
				}
			}
		}
	}
	// Up to the GPU (the whole texture: rebuilt only when a unit goes live or is released, or the window moves).
	TArray<FColor>* Data = new TArray<FColor>(Coverage);
	FUpdateTextureRegion2D* Region = new FUpdateTextureRegion2D(0, 0, 0, 0, CoverageSize, CoverageSize);
	CoverageTexture->UpdateTextureRegions(0, 1, Region, CoverageSize * sizeof(FColor), sizeof(FColor), reinterpret_cast<uint8*>(Data->GetData()),
		[Data](uint8*, const FUpdateTextureRegion2D* Regions)
		{
			delete Data;
			delete Regions;
		});
	++CoverageWrites;
	const FLinearColor Window(CoverageOrigin.X, CoverageOrigin.Y, CoverageSize * Texel, 1.f);
	if (bForce || !bCoverageValid)
	{
		if (UWorld* World = GetWorld())
		{
			for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
			{
				It->SetLandscapeMaterialVectorParameterValue(CoverageWindowParam, Window);
			}
		}
		bCoverageValid = true;
		for (const FZoneUnit& Unit : ZoneUnits)
		{
			if (AGTMudPatch* Patch = Unit.Patch.Get())
			{
				Patch->SetZoneCoverage(CoverageTexture, Window);
			}
		}
	}
}

bool UGTMudSubsystem::IsInLiveMudZone(const FVector& PointCm)
{
	const FVector2D XY(PointCm.X, PointCm.Y);
	for (const TWeakObjectPtr<AGTMudPatch>& Entry : GLiveMudZonePatches)
	{
		const AGTMudPatch* Patch = Entry.Get();
		if (Patch && Patch->Contains(XY))
		{
			return true;
		}
	}
	return false;
}

void UGTMudSubsystem::StampZoneNeighbours(const AGTMudPatch& Primary, const FVector2D& FromCm, const FVector2D& ToCm, float WidthCm, float DepthCm, const FVector2D& Heading, float RolledCm)
{
	if (!Primary.bZonePatch || !Primary.Zone || LiveZoneUnits < 2)
	{
		return;
	}
	FBox2D Reach(ForceInit);
	Reach += FromCm;
	Reach += ToCm;
	Reach = Reach.ExpandBy(WidthCm + 150.f);   // the tyre and its ridge band
	for (const FZoneUnit& Unit : ZoneUnits)
	{
		AGTMudPatch* Other = Unit.Patch.Get();
		if (!Other || Other == &Primary || Other->Zone != Primary.Zone || !Overlaps(Unit.FieldBox, Reach))
		{
			continue;
		}
		Other->GetField().StampWheel(FromCm, ToCm, WidthCm, DepthCm, Heading, RolledCm);
	}
}

FString UGTMudSubsystem::DescribeZones() const
{
	int32 Live = 0;
	int32 LiveCells = 0;
	FString Units;
	for (const FZoneUnit& Unit : ZoneUnits)
	{
		if (const AGTMudPatch* Patch = Unit.Patch.Get())
		{
			++Live;
			LiveCells += Unit.Cells;
			const AGTDeformZone* Zone = Zones[Unit.ZoneIndex];
			Units += FString::Printf(TEXT("%s{\"zone\":%d,\"label\":\"%s\",\"slot\":%d,\"whole\":%s,\"tile\":[%d,%d],\"cells\":%d,\"quads\":%d,\"distance_m\":%.1f}"),
				Units.IsEmpty() ? TEXT("") : TEXT(","), Zone->ZoneId, *Zone->Label, Unit.Slot, Unit.bWhole ? TEXT("true") : TEXT("false"), Unit.Tile.X, Unit.Tile.Y,
				Unit.Cells, Patch->ZoneDrawnQuads, Unit.Distance * 0.01f);
		}
	}
	int32 Covered = 0;
	for (const FColor& T : Coverage)
	{
		Covered += T.R >= 128 ? 1 : 0;
	}
	return FString::Printf(TEXT("{\"zones\":%d,\"units\":%d,\"live\":%d,\"live_cells\":%d,\"cap_tiles\":%d,\"activations\":%d,\"releases\":%d,\"restores\":%d,")
		TEXT("\"cache_entries\":%d,\"cache_bytes\":%lld,\"cache_cap_bytes\":%lld,\"cache_evicted\":%d,\"coverage_size\":%d,\"coverage_texel_cm\":%.1f,")
		TEXT("\"coverage_origin\":[%.0f,%.0f],\"coverage_texels_hole\":%d,\"coverage_writes\":%d,\"live_units\":[%s]}"),
		Zones.Num(), ZoneUnits.Num(), Live, LiveCells, MaxActiveZoneTiles, ZoneActivations, ZoneReleases, ZoneRestores, ZoneCache.Num(), ZoneCacheBytes,
		ZoneCacheCapBytes, ZoneCacheEvicted, CoverageSize, CoverageTexelCm, CoverageOrigin.X, CoverageOrigin.Y, Covered, CoverageWrites, *Units);
}
