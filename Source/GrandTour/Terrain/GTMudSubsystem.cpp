#include "Terrain/GTMudSubsystem.h"

#include "Terrain/GTMudPatch.h"
#include "Terrain/GTTerrainBuilder.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Vehicle/GTVehicleSetupLibrary.h"
#include "CoreGlobals.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "TimerManager.h"
#include "HAL/IConsoleManager.h"

// LM4 item 1 (docs/LIVING_MUD_PLAN.md LM4): the snow patches' grid, read when the patches are built (restart Play).
static TAutoConsoleVariable<int32> CVarSnowFineGrid(
	TEXT("gt.Snow.FineGrid"), 1,
	TEXT("LM4: 1 a snow patch's field and mesh take its profile's CellCm (6.25 cm), 0 they take 12.5 cm with every cell-unit number rescaled to keep its size in cm. Read when the patches are built (restart Play)."),
	ECVF_Default);

bool UGTMudSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	if (!Super::ShouldCreateSubsystem(Outer))
	{
		return false;
	}
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE);
}

void UGTMudSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	// Benmore B2 (GTMudSubsystemZones.cpp): the level's deform zones, streamed on a 0.1 s timer (none on the strips).
	GatherZones(InWorld);
	for (TActorIterator<AGTTerrainBuilder> It(&InWorld); It; ++It)
	{
		if (It->SpecAsset)
		{
			const int32 Count = BuildPatches(It->SpecAsset->Spec);
			UE_LOG(LogTemp, Display, TEXT("GTMud: %d mud patch(es) from %s"), Count, *It->SpecAsset->GetName());
			return;
		}
	}
}

void UGTMudSubsystem::Deinitialize()
{
	if (UWorld* ZoneWorld = GetWorld())
	{
		ZoneWorld->GetTimerManager().ClearTimer(ZoneTimer);   // Benmore B2
	}
	// Water stage W3: the patches are in the one water query, so they come out of it with the world.
	if (UWorld* World = GetWorld())
	{
		if (UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>())
		{
			for (AGTMudPatch* Patch : Patches)
			{
				Water->UnregisterPatch(Patch);
			}
		}
	}
	Super::Deinitialize();
}

float UGTMudSubsystem::MudHeightCmAt(FVector2D XYCm) const
{
	const AGTMudPatch* Patch = PatchAt(XYCm);
	return Patch ? Patch->GetField().HeightAt(XYCm) : 0.f;
}

float UGTMudSubsystem::MudLumpCmAt(FVector2D XYCm) const
{
	const AGTMudPatch* Patch = PatchAt(XYCm);
	return Patch ? Patch->GetField().LumpAt(XYCm) : 0.f;
}

float UGTMudSubsystem::MudBogAt(FVector2D XYCm) const
{
	const AGTMudPatch* Patch = PatchAt(XYCm);
	return Patch ? Patch->BogAt(XYCm) : 0.f;
}

int32 UGTMudSubsystem::FillClodsForTest(int32 PerPatch)
{
	int32 Added = 0;
	for (AGTMudPatch* Patch : Patches)
	{
		if (Patch)
		{
			Added += Patch->FillClodsForTest(PerPatch);
		}
	}
	return Added;
}

TArray<FVector4> UGTMudSubsystem::CutSnowTrenchForTest(FVector2D FromCm, FVector2D ToCm, float TyreWidthCm, float SinkCm)
{
	AGTMudPatch* Patch = PatchAt(FromCm);
	return Patch ? Patch->CutTrenchForTest(FromCm, ToCm, TyreWidthCm, SinkCm) : TArray<FVector4>();
}

// ---- LM4e (docs/LIVING_MUD_PLAN.md LM4e): the snow's cost, the record and the replay -----------------------------------

void UGTMudSubsystem::FoldCostFrame()
{
	if (CostFrame == MAX_uint64)
	{
		return;
	}
	++CostFrames;
	StampSamples.Add(FrameStampMs);
	SweptSum += FrameSwept;
	UploadCellsSum += FrameUploadCells;
	FrameStampMs = 0.f;
	FrameSwept = 0;
	FrameUploadCells = 0;
}

void UGTMudSubsystem::AddCostSample(float StampMs, int32 SweptTiles, int32 UploadCells)
{
	if (GFrameCounter != CostFrame)
	{
		FoldCostFrame();
		CostFrame = GFrameCounter;
	}
	FrameStampMs += StampMs;
	FrameSwept += SweptTiles;
	FrameUploadCells += UploadCells;
}

float UGTMudSubsystem::GetStampMeanMs() const
{
	double Sum = 0.0;
	for (const float Ms : StampSamples)
	{
		Sum += Ms;
	}
	return StampSamples.Num() > 0 ? static_cast<float>(Sum / StampSamples.Num()) : 0.f;
}

float UGTMudSubsystem::GetStampMaxMs() const
{
	float Max = 0.f;
	for (const float Ms : StampSamples)
	{
		Max = FMath::Max(Max, Ms);
	}
	return Max;
}

int32 UGTMudSubsystem::SetRecordingForTest(bool bOn)
{
	int32 Count = 0;
	for (AGTMudPatch* Patch : Patches)
	{
		if (Patch)
		{
			Patch->SetRecording(bOn);
			++Count;
		}
	}
	return Count;
}

int32 UGTMudSubsystem::StartReplayForTest(bool bAllAtOnce)
{
	int32 Events = 0;
	for (AGTMudPatch* Patch : Patches)
	{
		if (Patch)
		{
			Events += Patch->StartReplay(bAllAtOnce);
		}
	}
	return Events;
}

bool UGTMudSubsystem::IsReplayingForTest() const
{
	for (const AGTMudPatch* Patch : Patches)
	{
		if (Patch && Patch->IsReplaying())
		{
			return true;
		}
	}
	return false;
}

int32 UGTMudSubsystem::SaveRecordForTest(const FString& Path)
{
	int32 Events = 0;
	for (int32 Index = 0; Index < Patches.Num(); ++Index)
	{
		if (AGTMudPatch* Patch = Patches[Index])
		{
			const TArray<FGTMudField::FEvent>& Log = Patch->GetRecord();
			TArray<uint8> Bytes;
			const uint32 Header[4] = { 0x4C4D3465u, 1u, static_cast<uint32>(sizeof(FGTMudField::FEvent)), Patch->RecordEndCrc };   // 'LM4e', version, event size, the record's end CRC
			Bytes.Append(reinterpret_cast<const uint8*>(Header), sizeof(Header));
			Bytes.Append(reinterpret_cast<const uint8*>(Log.GetData()), Log.Num() * sizeof(FGTMudField::FEvent));
			if (FFileHelper::SaveArrayToFile(Bytes, *FString::Printf(TEXT("%s_%d.bin"), *Path, Index)))
			{
				Events += Log.Num();
			}
		}
	}
	return Events;
}

int32 UGTMudSubsystem::LoadRecordForTest(const FString& Path)
{
	int32 Events = 0;
	for (int32 Index = 0; Index < Patches.Num(); ++Index)
	{
		AGTMudPatch* Patch = Patches[Index];
		TArray<uint8> Bytes;
		if (!Patch || !FFileHelper::LoadFileToArray(Bytes, *FString::Printf(TEXT("%s_%d.bin"), *Path, Index)) || Bytes.Num() < 16)
		{
			continue;
		}
		const uint32* Header = reinterpret_cast<const uint32*>(Bytes.GetData());
		if (Header[0] != 0x4C4D3465u || Header[2] != sizeof(FGTMudField::FEvent))
		{
			continue;
		}
		const int32 Count = (Bytes.Num() - 16) / static_cast<int32>(sizeof(FGTMudField::FEvent));
		TArray<FGTMudField::FEvent>& Log = Patch->GetRecord();
		Log.SetNumUninitialized(Count);
		FMemory::Memcpy(Log.GetData(), Bytes.GetData() + 16, Count * sizeof(FGTMudField::FEvent));
		Patch->RecordEndCrc = Header[3];
		Events += Count;
	}
	return Events;
}

int64 UGTMudSubsystem::FieldCrcForTest() const
{
	return Patches.Num() > 0 && Patches[0] ? static_cast<int64>(Patches[0]->FieldCrc()) : -1;
}

int64 UGTMudSubsystem::RecordEndCrcForTest() const
{
	return Patches.Num() > 0 && Patches[0] ? static_cast<int64>(Patches[0]->RecordEndCrc) : -1;
}

float UGTMudSubsystem::Percentile(const TArray<float>& Samples, float P)
{
	if (Samples.Num() == 0)
	{
		return 0.f;
	}
	TArray<float> Sorted = Samples;
	Sorted.Sort();
	// Nearest rank: the smallest value with at least P of the samples at or under it.
	const int32 Rank = FMath::Clamp(FMath::CeilToInt(P * Sorted.Num()) - 1, 0, Sorted.Num() - 1);
	return Sorted[Rank];
}

int32 UGTMudSubsystem::RebuildPatchesForTest()
{
	// LM4: the patches again from the level's terrain builder (as OnWorldBeginPlay), so gt.Snow.FineGrid is read again.
	UWorld* World = GetWorld();
	if (!World)
	{
		return 0;
	}
	for (TActorIterator<AGTTerrainBuilder> It(World); It; ++It)
	{
		if (It->SpecAsset)
		{
			const int32 Count = BuildPatches(It->SpecAsset->Spec);
			UE_LOG(LogTemp, Display, TEXT("GTMud: rebuilt %d patch(es) from %s (gt.Snow.FineGrid %d)"), Count, *It->SpecAsset->GetName(), CVarSnowFineGrid.GetValueOnGameThread());
			return Count;
		}
	}
	return 0;
}

float UGTMudSubsystem::SnowTopCmAt(FVector2D XYCm) const
{
	const AGTMudPatch* Patch = PatchAt(XYCm);
	return Patch ? Patch->SnowTopCmAt(XYCm) : 0.f;
}

double UGTMudSubsystem::SnowPloughedCm3() const
{
	double Total = 0.0;
	for (const AGTMudPatch* Patch : Patches)
	{
		Total += Patch ? Patch->GetField().PloughedCm3 : 0.0;
	}
	return Total;
}

double UGTMudSubsystem::SnowPloughBermCm3() const
{
	double Total = 0.0;
	for (const AGTMudPatch* Patch : Patches)
	{
		Total += Patch ? Patch->GetField().PloughBermCm3 : 0.0;
	}
	return Total;
}

float UGTMudSubsystem::MudFreshAt(FVector2D XYCm) const
{
	const AGTMudPatch* Patch = PatchAt(XYCm);
	return Patch ? Patch->GetField().FreshAt(XYCm) : 0.f;
}

namespace
{
	/** LM1b: the cells whose centres lie in a box (Min inclusive, Max exclusive), clamped to the field. */
	FIntRect CellRectIn(const FGTMudField& Field, const FVector2D& MinCm, const FVector2D& MaxCm)
	{
		const FVector2D Lo = (MinCm - Field.OriginCm) / Field.CellCm - FVector2D(0.5, 0.5);
		const FVector2D Hi = (MaxCm - Field.OriginCm) / Field.CellCm - FVector2D(0.5, 0.5);
		return FIntRect(
			FMath::Clamp(FMath::CeilToInt(Lo.X), 0, Field.SizeX), FMath::Clamp(FMath::CeilToInt(Lo.Y), 0, Field.SizeY),
			FMath::Clamp(FMath::FloorToInt(Hi.X) + 1, 0, Field.SizeX), FMath::Clamp(FMath::FloorToInt(Hi.Y) + 1, 0, Field.SizeY));
	}
}

TArray<float> UGTMudSubsystem::MudCellHeightsCm(FVector2D MinCm, FVector2D MaxCm) const
{
	TArray<float> Heights;
	const AGTMudPatch* Patch = PatchAt(0.5 * (MinCm + MaxCm));
	if (!Patch || !Patch->GetField().IsValid())
	{
		return Heights;
	}
	const FGTMudField& Field = Patch->GetField();
	const FIntRect Rect = CellRectIn(Field, MinCm, MaxCm);
	for (int32 Y = Rect.Min.Y; Y < Rect.Max.Y; ++Y)
	{
		for (int32 X = Rect.Min.X; X < Rect.Max.X; ++X)
		{
			Heights.Add(Field.SurfaceCm(Y * Field.SizeX + X));   // LM2a: the surface, lumps included
		}
	}
	return Heights;
}

float UGTMudSubsystem::MudSetSecondsAt(FVector2D XYCm) const
{
	const AGTMudPatch* Patch = PatchAt(XYCm);
	if (!Patch || !Patch->GetField().IsValid())
	{
		return 0.f;
	}
	const FGTMudField& Field = Patch->GetField();
	const int32 Index = Field.CellIndexAt(XYCm);
	return Field.SetS.IsValidIndex(Index) ? Field.SetS[Index] : 0.f;
}

int32 UGTMudSubsystem::MudCellsAcross(FVector2D MinCm, FVector2D MaxCm) const
{
	const AGTMudPatch* Patch = PatchAt(0.5 * (MinCm + MaxCm));
	if (!Patch || !Patch->GetField().IsValid())
	{
		return 0;
	}
	const FIntRect Rect = CellRectIn(Patch->GetField(), MinCm, MaxCm);
	return FMath::Max(0, Rect.Max.X - Rect.Min.X);
}

void UGTMudSubsystem::ResetFieldsForTest()
{
	for (AGTMudPatch* Patch : Patches)
	{
		if (Patch)
		{
			Patch->ResetFieldForTest();
		}
	}
}

void UGTMudSubsystem::ResetSettleStats()
{
	SampleFrame = MAX_uint64;
	bFrameSettleOn = false;
	FrameSettleMs = 0.f;
	FrameUploadMs = 0.f;
	FrameAwake = 0;
	SettleFrames = 0;
	SettleSumMs = 0.0;
	SettleMaxMs = 0.f;
	SettleAwakePeak = 0;
	UploadFrames = 0;
	UploadSumMs = 0.0;
	UploadMaxMs = 0.f;
	SettleSamples.Reset();
	UploadSamples.Reset();
	ClodSamples.Reset();
	bFrameClodsOn = false;
	FrameClodMs = 0.f;
	ClodSumMs = 0.0;
	ClodMaxMs = 0.f;
	// LM4e
	CostFrame = MAX_uint64;
	FrameStampMs = 0.f;
	FrameSwept = 0;
	FrameUploadCells = 0;
	CostFrames = 0;
	SweptSum = 0.0;
	UploadCellsSum = 0.0;
	StampSamples.Reset();
}

void UGTMudSubsystem::FoldSettleFrame()
{
	if (SampleFrame == MAX_uint64)
	{
		return;
	}
	if (bFrameSettleOn)
	{
		++SettleFrames;
		SettleSumMs += FrameSettleMs;
		SettleMaxMs = FMath::Max(SettleMaxMs, FrameSettleMs);
		SettleAwakePeak = FMath::Max(SettleAwakePeak, FrameAwake);
		SettleSamples.Add(FrameSettleMs);
	}
	++UploadFrames;
	UploadSumMs += FrameUploadMs;
	UploadMaxMs = FMath::Max(UploadMaxMs, FrameUploadMs);
	UploadSamples.Add(FrameUploadMs);
	if (bFrameClodsOn)
	{
		ClodSamples.Add(FrameClodMs);
		ClodSumMs += FrameClodMs;
		ClodMaxMs = FMath::Max(ClodMaxMs, FrameClodMs);
	}
	bFrameSettleOn = false;
	FrameSettleMs = 0.f;
	FrameUploadMs = 0.f;
	FrameAwake = 0;
	bFrameClodsOn = false;
	FrameClodMs = 0.f;
}

void UGTMudSubsystem::AddSettleSample(bool bSettleOn, float SettleMs, int32 AwakeTiles, float UploadMs, bool bClodsOn, float ClodMs)
{
	// The patches tick one after another in the same frame: their times add up to the frame's, which is what the cost
	// gate is about. A new frame number folds the last one in.
	if (GFrameCounter != SampleFrame)
	{
		FoldSettleFrame();
		SampleFrame = GFrameCounter;
	}
	bFrameSettleOn |= bSettleOn;
	FrameSettleMs += SettleMs;
	FrameUploadMs += UploadMs;
	FrameAwake += AwakeTiles;
	bFrameClodsOn |= bClodsOn;
	FrameClodMs += ClodMs;
}

int32 UGTMudSubsystem::EnforceMudChunkAwakeCap(bool bForce)
{
	if (!bForce && GFrameCounter == ChunkCapFrame)
	{
		return 0;
	}
	ChunkCapFrame = GFrameCounter;
	// Every awake chunk with the time it woke (one woken since its patch last ticked counts as woken now).
	struct FAwake
	{
		double SinceS;
		AGTMudPatch* Patch;
		int32 Index;
	};
	const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	TArray<FAwake> Awake;
	for (AGTMudPatch* Patch : Patches)
	{
		if (!Patch || Patch->MudChunksLive <= 0)
		{
			continue;
		}
		for (int32 Index = 0; Index < Patch->NumMudChunkSlots(); ++Index)
		{
			if (Patch->IsMudChunkAwake(Index))
			{
				const double Since = Patch->MudChunkAwakeSince(Index);
				Awake.Add({ Since < 0.0 ? Now : Since, Patch, Index });
			}
		}
	}
	ChunkAwakePeak = FMath::Max(ChunkAwakePeak, Awake.Num());
	int32 Slept = 0;
	if (Awake.Num() > FMath::Max(0, MaxAwakeMudChunks))
	{
		// The longest-awake first (ties by section, then slot, so the cap is deterministic).
		Awake.Sort([](const FAwake& A, const FAwake& B)
		{
			if (A.SinceS != B.SinceS)
			{
				return A.SinceS < B.SinceS;
			}
			if (A.Patch->SectionIndex != B.Patch->SectionIndex)
			{
				return A.Patch->SectionIndex < B.Patch->SectionIndex;
			}
			return A.Index < B.Index;
		});
		Slept = Awake.Num() - FMath::Max(0, MaxAwakeMudChunks);
		for (int32 K = 0; K < Slept; ++K)
		{
			Awake[K].Patch->SleepMudChunk(Awake[K].Index);
		}
		ChunksCapped += Slept;
	}
	ChunkAwakeNow = Awake.Num() - Slept;
	return Slept;
}

AGTMudPatch* UGTMudSubsystem::PatchAt(const FVector2D& XYCm) const
{
	for (AGTMudPatch* Patch : Patches)
	{
		if (Patch && Patch->Contains(XYCm))
		{
			return Patch;
		}
	}
	return nullptr;
}

double UGTMudSubsystem::TotalLoweredCm3() const
{
	double Total = 0.0;
	for (const AGTMudPatch* Patch : Patches)
	{
		if (Patch)
		{
			Total += Patch->GetField().LoweredCm3;
		}
	}
	return Total;
}

int32 UGTMudSubsystem::BuildPatches(const FGTTerrainSpec& Spec)
{
	UWorld* World = GetWorld();
	UGTWaterSubsystem* Water = World ? World->GetSubsystem<UGTWaterSubsystem>() : nullptr;
	for (AGTMudPatch* Patch : Patches)
	{
		if (Patch)
		{
			if (Water)
			{
				Water->UnregisterPatch(Patch);
			}
			Patch->Destroy();
		}
	}
	Patches.Reset();
	if (!World)
	{
		return 0;
	}
	// RIVERBED S4 (2026-09-23, VEHICLE_BUILD_SYSTEM 54): two passes. The Mud sections first, in section order, exactly as
	// before (so a bog keeps its place in the list, its hole slot, its rows and its patch's own ridge numbers); then every
	// other section with a deformation profile (FGTRouteSection::Deform; a Ford's bed by default) on the same box rule. A
	// later box is cut back off any earlier patch's box on its side of least loss, a quarter metre short of it (two field
	// cells: the field rounds its size up), so no two patches overlap - two meshes on one ground would z-fight, and the
	// Hide's ford starts 5 m after its bog ends, well inside the bog's 11.6 m margin.
	constexpr float PatchGapCm = 25.f;
	// -GTNoBedPatch: the profiled patches are not built (the pre-S4 answer, for a control run; as -GTWaterPlacedBox is S3's).
	const bool bNoBedPatch = FParse::Param(FCommandLine::Get(), TEXT("GTNoBedPatch"));
	if (bNoBedPatch)
	{
		UE_LOG(LogTemp, Display, TEXT("UGTMudSubsystem: -GTNoBedPatch: no patch over a profiled section (the pre-RIVERBED S4 answer)"));
	}
	for (int32 Pass = 0; Pass < (bNoBedPatch ? 1 : 2); ++Pass)
	{
		for (int32 Index = 0; Index < Spec.Sections.Num(); ++Index)
		{
			const FGTRouteSection& Section = Spec.Sections[Index];
			if ((Section.Kind == EGTRouteSectionKind::Mud) != (Pass == 0))
			{
				continue;
			}
			// RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): the box is GTTerrain's, the one the generator paints Mud and
			// Bog inside and nowhere else (the same points +- the half width + 200 cm this loop used to add up itself). S4:
			// DeformPatchBoxCm is that box for a Mud section and the same rule for a profiled one.
			FBox2D Bounds(ForceInit);
			if (!GTTerrain::DeformPatchBoxCm(Spec, Index, Bounds))
			{
				continue;
			}
			// LM3a: with the spec, so a Snow section on ByKind takes the spec's SnowProfile.
			const FGTDeformProfile* Profile = GTTerrain::DeformProfileFor(Spec, Section);
			FString Trimmed;
			if (Pass == 1)
			{
				for (const AGTMudPatch* Earlier : Patches)
				{
					if (!Earlier)
					{
						continue;
					}
					const FBox2D Other(Earlier->BoundsMin, Earlier->BoundsMax);
					if (Bounds.Min.X >= Other.Max.X + PatchGapCm || Other.Min.X >= Bounds.Max.X + PatchGapCm
						|| Bounds.Min.Y >= Other.Max.Y + PatchGapCm || Other.Min.Y >= Bounds.Max.Y + PatchGapCm)
					{
						continue;
					}
					// The four ways out: the side that keeps the most of the box.
					FBox2D Cuts[4] = { Bounds, Bounds, Bounds, Bounds };
					Cuts[0].Min.X = Other.Max.X + PatchGapCm;
					Cuts[1].Max.X = Other.Min.X - PatchGapCm;
					Cuts[2].Min.Y = Other.Max.Y + PatchGapCm;
					Cuts[3].Max.Y = Other.Min.Y - PatchGapCm;
					int32 Best = INDEX_NONE;
					double BestArea = 0.0;
					for (int32 Cut = 0; Cut < 4; ++Cut)
					{
						const FVector2D Size = Cuts[Cut].Max - Cuts[Cut].Min;
						const double Area = (Size.X > 0.0 && Size.Y > 0.0) ? Size.X * Size.Y : 0.0;
						if (Area > BestArea)
						{
							BestArea = Area;
							Best = Cut;
						}
					}
					if (Best == INDEX_NONE)
					{
						Bounds = FBox2D(ForceInit);
						break;
					}
					const FVector2D OldSize = Bounds.GetSize();
					Bounds = Cuts[Best];
					Trimmed += FString::Printf(TEXT(" cut off section %d's patch at %s (%.1f x %.1f -> %.1f x %.1f m)"), Earlier->SectionIndex,
						Best == 0 ? TEXT("its +X side") : Best == 1 ? TEXT("its -X side") : Best == 2 ? TEXT("its +Y side") : TEXT("its -Y side"),
						OldSize.X * 0.01, OldSize.Y * 0.01, Bounds.GetSize().X * 0.01, Bounds.GetSize().Y * 0.01);
				}
				if (!Bounds.bIsValid)
				{
					UE_LOG(LogTemp, Warning, TEXT("UGTMudSubsystem: section %d's profiled patch lies inside an earlier patch; not built"), Index);
					continue;
				}
			}
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			AGTMudPatch* Patch = World->SpawnActor<AGTMudPatch>(AGTMudPatch::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, Params);
			if (!Patch)
			{
				continue;
			}
			// Stage G: the section owns its water table, so it is set before Init (which builds both grids). RIVERBED S4: the
			// profile's sinkage and ridge numbers, also before Init (which pushes the ridge numbers into the field and builds the
			// water grid, which leaves out what a sheet covers on a profiled patch). LM5b: and the section's mud variant (its
			// texture slice; a variant's profile scales the rows and keeps the patch a bog's). AGTMudPatch::ApplySection does
			// all three, in that order, with the same DeformProfileFor as above.
			Patch->ApplySection(Spec, Section);
			// MR5: the section's route line, where the chunks may lie (within 6 m of it).
			Patch->SetRouteLine(Spec, Section);
			// LM3a: a snow patch bakes its depth per cell from the section's drifts (the profile's SnowDepthCm elsewhere).
			TFunction<float(const FVector2D&)> SnowDepthAt;
			if (Profile && Profile->Medium == EGTDeformMedium::Snow && Section.SnowDrifts.Num() > 0)
			{
				const FGTDeformProfile ProfileCopy = *Profile;
				SnowDepthAt = [&Spec, &Section, ProfileCopy](const FVector2D& XYCm)
				{
					return GTTerrain::SnowDepthCmAt(Spec, Section, ProfileCopy, static_cast<float>(XYCm.X), static_cast<float>(XYCm.Y));
				};
			}
			// LM4 item 1: the profile's own cell (mud's 12.5; snow's 6.25), or with gt.Snow.FineGrid 0 a snow patch at 12.5 with
			// its cell-unit numbers rescaled so each keeps its size in cm (the measurement's comparison).
			float PatchCellCm = (Profile && !Profile->bScalesRows) ? FMath::Max(1.f, Profile->CellCm) : CellCm;   // LM5b: a mud variant is a bog's grid
			if (Profile && Profile->Medium == EGTDeformMedium::Snow && CVarSnowFineGrid.GetValueOnGameThread() == 0 && PatchCellCm < CellCm)
			{
				Patch->ScaleCellUnits(PatchCellCm / CellCm);
				UE_LOG(LogTemp, Display, TEXT("UGTMudSubsystem: gt.Snow.FineGrid 0 - section %d's snow patch at %.2f cm (its profile's %.2f; cell-unit numbers x%.3f)"), Index, CellCm, PatchCellCm, PatchCellCm / CellCm);
				PatchCellCm = CellCm;
			}
			Patch->Init(Index, Bounds, PatchCellCm, SnowDepthAt);
			Patch->BakeLayers(Spec);
			Patch->HoleSlot = Patches.Num() < 4 ? Patches.Num() : -1;
			Patches.Add(Patch);
			// Water stage W3: into the one water query. Nothing else in the game asks the patch for its water any more.
			if (Water)
			{
				Water->RegisterPatch(Patch);
			}
			UE_LOG(LogTemp, Display, TEXT("UGTMudSubsystem: patch %d over section %d (%s %.0f-%.0f m): box x %.0f..%.0f y %.0f..%.0f cm (%.1f x %.1f m, %d x %d cells), hole slot %d%s; %s; mesh %d vertices, water grid %d vertices (%d quads under a sheet)%s"),
				Patches.Num() - 1, Index, Section.Kind == EGTRouteSectionKind::Mud ? TEXT("Mud") : Section.Kind == EGTRouteSectionKind::Ford ? TEXT("Ford")
					: Section.Kind == EGTRouteSectionKind::Snow ? TEXT("Snow") : TEXT("other"),
				Section.StartM, Section.EndM, Patch->BoundsMin.X, Patch->BoundsMax.X, Patch->BoundsMin.Y, Patch->BoundsMax.Y,
				(Patch->BoundsMax.X - Patch->BoundsMin.X) * 0.01f, (Patch->BoundsMax.Y - Patch->BoundsMin.Y) * 0.01f, Patch->CellsX, Patch->CellsY,
				Patch->HoleSlot, Patch->HoleSlot < 0 ? TEXT(" (NO HOLE: the four MPC_TrackPaint slots are taken)") : TEXT(""),
				(Profile && Profile->bScalesRows) ? *FString::Printf(TEXT("mud variant %s (LM5b): the surface rows x sinkage %.2f / rate %.2f / friction %.2f and the Mud/Bog tag gate, RecoverShare %.2f, LumpShare %.2f, ThrowMax %.2f, water table %.1f cm"),
						*StaticEnum<EGTMudVariant>()->GetNameStringByValue(static_cast<int64>(Patch->MudVariant)), Patch->MaxSinkageScale, Patch->SinkageRateScale, Patch->FrictionScale, Patch->RecoverShare, Patch->LumpShare, Patch->ThrowMax, Patch->WaterTableCm)
				: Profile ? *FString::Printf(TEXT("profile MaxSinkage %.3f m SinkageRate %.3f m/s, ridge width %.0f cm max %.0f cm"), Patch->ProfileMaxSinkageM, Patch->ProfileSinkageRate, Patch->RidgeWidthCm, Patch->MaxRidgeCm)
					: TEXT("no profile: the surface rows' numbers and the Mud/Bog tag gate"),
				Patch->MeshVertexCount, Patch->WaterVertexCount, Patch->WaterQuadsUnderSheet, *Trimmed);
		}
	}
	// The landscape's hole under the mud (section 30, made one surface in section 31): M_GT_Landscape masks itself out
	// over the whole of each patch's box shrunk by HoleInsetCm, so the mud mesh is the ground there and there is no
	// boundary between touched and untouched mud. The box alone says where, so nothing has to reach the landscape per
	// patch any more: the MudField0..3 texture parameters and the binding loop that filled them through the landscape's
	// dynamic material instances are gone (stage C's hole followed the mesh's own mask and its edge was a visible
	// seam). bUseDynamicMaterialInstance stays on in BuildLegLandscape: one line, and stage E may want per-patch
	// parameters back. Counted here only for the log.
	int32 Landscapes = 0;
	for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
	{
		++Landscapes;
	}
	// The patches' boxes into MPC_TrackPaint: the landscape material cuts its hole inside Patch<slot>.
	bCollectionWritten = false;
	if (UMaterialParameterCollection* Collection = LoadObject<UMaterialParameterCollection>(nullptr, *CollectionPath))
	{
		if (UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(Collection))
		{
			for (int32 Slot = 0; Slot < 4; ++Slot)
			{
				const AGTMudPatch* Patch = Patches.IsValidIndex(Slot) ? Patches[Slot].Get() : nullptr;
				Instance->SetVectorParameterValue(*FString::Printf(TEXT("Patch%d"), Slot),
					Patch ? FLinearColor(Patch->BoundsMin.X, Patch->BoundsMin.Y, Patch->BoundsMax.X, Patch->BoundsMax.Y) : FLinearColor(0.f, 0.f, 0.f, 0.f));
				// LM5b: the patch's mud variant, so the landscape's apron round its box wears the same slice (Art/Unreal/
				// live_mud_style.py adds PatchVariant0..3; a collection without them is left alone).
				const FName VariantName(*FString::Printf(TEXT("PatchVariant%d"), Slot));
				if (Collection->GetScalarParameterByName(VariantName))
				{
					Instance->SetScalarParameterValue(VariantName, Patch ? static_cast<float>(static_cast<uint8>(Patch->MudVariant)) : 0.f);
				}
			}
			Instance->SetScalarParameterValue(TEXT("PatchCount"), Patches.Num());
			bCollectionWritten = true;
		}
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTMudSubsystem: %s missing (run Art/setup_m6_mud.bat); the landscape material has no patch boxes, no holes under the mud patches"), *CollectionPath);
	}
	const AGTMudPatch* First = Patches.Num() > 0 ? Patches[0].Get() : nullptr;
	UE_LOG(LogTemp, Log, TEXT("UGTMudSubsystem: %d patch(es); %d landscape(s); boxes %s (the landscape's hole is the box shrunk by HoleInsetCm); stage G water: table %.1f cm, %d vertices; W3: %d patch(es) in the one water query (kind Rut), the rut water counts"),
		Patches.Num(), Landscapes, bCollectionWritten ? TEXT("written") : TEXT("not written"),
		First ? First->WaterTableCm : 0.f, First ? First->WaterVertexCount : 0, Water ? Patches.Num() : 0);
	UE_LOG(LogTemp, Display, TEXT("UGTMudSubsystem: RIVERBED S4 patch count %d (%d with a deformation profile), %d with a landscape hole, %d without"),
		Patches.Num(), Patches.FilterByPredicate([](const TObjectPtr<AGTMudPatch>& P) { return P && P->bHasProfile; }).Num(), FMath::Min(Patches.Num(), 4), FMath::Max(0, Patches.Num() - 4));
	return Patches.Num();
}
