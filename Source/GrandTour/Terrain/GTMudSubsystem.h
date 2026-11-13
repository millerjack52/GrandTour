#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GTMudSubsystem.generated.h"

class AGTMudPatch;
class AGTDeformZone;
class UTexture2D;
struct FGTTerrainSpec;

/**
 * Owns the mud patches of a level (docs/MUD_DEFORMATION_PLAN.md): at BeginPlay it reads the terrain builder's spec
 * and spawns one AGTMudPatch per Mud route section over the section's footprint (the section's half width plus
 * MarginCm along its route) at CellCm. The traction stamps the patch under each wheel on mud; the test and stage B
 * read the patches. RIVERBED S4 (VEHICLE_BUILD_SYSTEM 54): also one per section with a deformation profile
 * (FGTRouteSection::Deform; every Ford's bed by default), built after the bogs so a bog keeps its hole slot.
 */
UCLASS()
class GRANDTOUR_API UGTMudSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;

	/** The patch covering a world XY, or null. */
	AGTMudPatch* PatchAt(const FVector2D& XYCm) const;
	const TArray<TObjectPtr<AGTMudPatch>>& GetPatches() const { return Patches; }
	/** Volume the wheels have lowered across every patch, cm^3. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	double TotalLoweredCm3() const;

	// ---- LM1, the living field: the check script's readouts (docs/LIVING_MUD_PLAN.md LM1, "Check script") --------
	/** The mud field's height at a world XY, cm relative to the undisturbed ground (0 outside every patch): the settle profile's sampler. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float MudHeightCmAt(FVector2D XYCm) const;
	/** LM3a: the snow top over the ground at a world XY, cm (0 on mud or outside every patch); the snow surface there is this plus MudHeightCmAt. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float SnowTopCmAt(FVector2D XYCm) const;
	/** LM3a: what the belly ploughed out of every snow patch, and what of it went into the berms, cm^3. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	double SnowPloughedCm3() const;
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	double SnowPloughBermCm3() const;
	/** The fresh sheen there, 0..1 (0 outside every patch). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float MudFreshAt(FVector2D XYCm) const;
	/** LM1b, the check script's detail measure: the heights of the cells whose centres lie in the box, row by row (MudCellsAcross of them to a row), from the patch under the box's centre; empty outside every patch. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	TArray<float> MudCellHeightsCm(FVector2D MinCm, FVector2D MaxCm) const;
	/** LM1b, the check script's trace: the set timer left on the cell under a world XY, s (0 outside every patch). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float MudSetSecondsAt(FVector2D XYCm) const;
	/** How many cells each row of MudCellHeightsCm holds. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	int32 MudCellsAcross(FVector2D MinCm, FVector2D MaxCm) const;
	/** Every patch's field back to untouched ground, for a second measured crossing in the same session (the drive check's gt.Mud.Settle 0 / 1 pair). */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	void ResetFieldsForTest();
	/** LM4: the patches built again from the level's terrain builder (gt.Snow.FineGrid is read when they are built): the drive check's FineGrid 1 / 0 pair in one session. Returns the count. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	int32 RebuildPatchesForTest();
	/** Starts the settle cost readout afresh. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	void ResetSettleStats();
	/** Frames measured since the reset (frames with gt.Mud.Settle on; the patches' times are summed per frame). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	int32 GetSettleFrames() const { return SettleFrames; }
	/** Settle's mean and worst frame, ms, over those frames. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetSettleMeanMs() const { return SettleFrames > 0 ? static_cast<float>(SettleSumMs / SettleFrames) : 0.f; }
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetSettleMaxMs() const { return SettleMaxMs; }
	/** The most tiles awake at once over all patches. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	int32 GetSettleAwakePeak() const { return SettleAwakePeak; }
	/** LM2a housekeeping 2: the cost gate is mean <= 0.3 ms and p99 <= 0.7 ms per feature, the max reported. Settle's p99, ms (nearest rank over the frames since the reset). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetSettleP99Ms() const { return Percentile(SettleSamples, 0.99f); }
	/** The upload's p99, ms. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetUploadP99Ms() const { return Percentile(UploadSamples, 0.99f); }
	/** LM2b: the clods' update (spawns, re-snap, squash, sinking, the push), frames with gt.Mud.Clods on and a clod mesh, summed over the patches. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	int32 GetClodFrames() const { return ClodSamples.Num(); }
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetClodMeanMs() const { return ClodSamples.Num() > 0 ? static_cast<float>(ClodSumMs / ClodSamples.Num()) : 0.f; }
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetClodP99Ms() const { return Percentile(ClodSamples, 0.99f); }
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetClodMaxMs() const { return ClodMaxMs; }
	/** LM2a: the lumps alone at a world XY, cm (0 outside every patch). MudHeightCmAt is the surface, lumps included. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float MudLumpCmAt(FVector2D XYCm) const;
	/** LM2b: the Bog layer under a world XY, 0..1 (0 outside every patch): where the spin test finds the deepest mud. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float MudBogAt(FVector2D XYCm) const;
	/** LM2b, the GPU cost at the cap: every patch filled with PerPatch clods at seeded spots (none without a clod mesh). Returns how many were added. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	int32 FillClodsForTest(int32 PerPatch);
	/** LM4c, the drive check's collapse pair: a tyre's cut from FromCm to ToCm (world XY) stamped now on the snow patch under FromCm; per collapse segment it armed, the pile's spot (X, Y), its side (Z) and its delay (W, s). Empty off a snow patch. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	TArray<FVector4> CutSnowTrenchForTest(FVector2D FromCm, FVector2D ToCm, float TyreWidthCm, float SinkCm);
	/** The texture upload's mean and worst frame, ms, over every frame since the reset (on or off). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetUploadMeanMs() const { return UploadFrames > 0 ? static_cast<float>(UploadSumMs / UploadFrames) : 0.f; }
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetUploadMaxMs() const { return UploadMaxMs; }
	/** Each patch's tick reports its settle, upload and (LM2b) clod update; the subsystem sums the patches of one frame. */
	void AddSettleSample(bool bSettleOn, float SettleMs, int32 AwakeTiles, float UploadMs, bool bClodsOn = false, float ClodMs = 0.f);

	// ---- LM4e (docs/LIVING_MUD_PLAN.md LM4e): the snow's cost, the record and the replay -------------------------------
	/** LM4e: each patch's tick also reports its stamp time (the traction's stamps and the throw's landings), the tiles its settle swept and the cells its upload wrote; summed per frame. */
	void AddCostSample(float StampMs, int32 SweptTiles, int32 UploadCells);
	/** The stamps' mean, p99 and worst frame, ms, since the settle readout's reset (every frame). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetStampMeanMs() const;
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetStampP99Ms() const { return Percentile(StampSamples, 0.99f); }
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetStampMaxMs() const;
	/** The mean tiles swept a frame and cells uploaded a frame since the reset. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetSweptTilesMean() const { return CostFrames > 0 ? static_cast<float>(SweptSum / CostFrames) : 0.f; }
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	float GetUploadCellsMean() const { return CostFrames > 0 ? static_cast<float>(UploadCellsSum / CostFrames) : 0.f; }
	/** Every patch starts a record on its reset field (true), or stops it (false). Returns the patches. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	int32 SetRecordingForTest(bool bOn);
	/** Every patch replays its record onto its reset field: all at once now, or one recorded frame per tick. Returns the events. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	int32 StartReplayForTest(bool bAllAtOnce);
	/** A frame-by-frame replay still running on any patch. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	bool IsReplayingForTest() const;
	/** The records to a file per patch (Path + "_<n>.bin") / back from them. Returns the events written / read. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	int32 SaveRecordForTest(const FString& Path);
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	int32 LoadRecordForTest(const FString& Path);
	/** The first patch's field CRC (HeightCm, LumpCm) now and when its record stopped (the replay's check). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	int64 FieldCrcForTest() const;
	UFUNCTION(BlueprintPure, Category = "GT|Mud")
	int64 RecordEndCrcForTest() const;

	// ---- MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5): the mud chunks' awake cap, over every patch -------------------
	/** The most chunks awake at once in the world; beyond it the longest-awake are put to sleep. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MaxAwakeMudChunks = 64;
	/** The cap, once a frame (the patches' ticks call it; bForce: now, whatever the frame). Returns the chunks put to sleep. */
	int32 EnforceMudChunkAwakeCap(bool bForce = false);
	/** Awake after the last cap, the most awake seen before a cap acted (the peak), and the chunks the cap has put to sleep. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Chunks")
	int32 GetMudChunkAwakeNow() const { return ChunkAwakeNow; }
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Chunks")
	int32 GetMudChunkAwakePeak() const { return ChunkAwakePeak; }
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Chunks")
	int32 GetMudChunksCapped() const { return ChunksCapped; }
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|Chunks")
	void ResetMudChunkAwakePeak() { ChunkAwakePeak = ChunkAwakeNow; ChunksCapped = 0; }

	/**
	 * One patch per Mud section of the spec; the patches of a previous build are destroyed. Returns the count.
	 * Water stage W3: each patch registers with UGTWaterSubsystem here, so its ruts' water is part of the one water
	 * query and the traction and the hull read it through the same call a ford's sheet answers.
	 */
	int32 BuildPatches(const FGTTerrainSpec& Spec);

	/** The box's margin round the road is GTTerrain::MudPatchMarginCm (200 cm), shared with the generator since RIVERBED S2 (2026-09-23): no Mud or Bog is painted outside a patch's box. */
	float CellCm = 12.5f;

	// ---- Benmore integration B2 (docs/BENMORE_INTEGRATION_PLAN.md B2): deform zones, streamed patches, the coverage texture ----------
	/**
	 * The level's AGTDeformZone actors become units: a tiled zone's 24 m world tiles (ZoneTileCm, 192 x 192 cells at ZoneCellCm, the
	 * field one cell wider each side: the overlap its neighbours own), a mud zone's whole box. Every 0.1 s the units within
	 * ZoneActivateCm of a focus (the player's pawn and camera, every possessed or moving GTCarPawn, SetZoneFocusForTest) are wanted, a
	 * live one until it is beyond ZoneReleaseCm; nearest first, at most MaxActiveZoneTiles x 192^2 cells; one activation a pass. A
	 * released unit's changed cells (against its field at activation) go into an LRU cache of ZoneCacheCapBytes, zlib-compressed, and
	 * come back when it is wanted again. The live units write the coverage texture (CoverageSize texels of CoverageTexelCm round the
	 * focus; R the zone share of each texel, G the apron over ApronCm round a mud zone, B its variant) into every landscape's material
	 * (GTDeformCoverage, GTDeformWindow): the landscape cuts its hole where R passes 0.5. The strips have no zones: nothing here runs.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|Zones")
	int32 MaxActiveZoneTiles = 9;
	float ZoneTileCm = 2400.f;
	float ZoneCellCm = 12.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|Zones")
	float ZoneActivateCm = 4000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|Zones")
	float ZoneReleaseCm = 6000.f;
	int64 ZoneCacheCapBytes = 128ll * 1024 * 1024;
	int32 CoverageSize = 1024;
	float CoverageTexelCm = 25.f;
	float CoverageRecentreCm = 3200.f;
	float ApronCm = 200.f;
	/** One streaming pass now with no one-a-pass limit (the captures; the 0.1 s timer runs it with the limit). Returns the live units. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|Zones")
	int32 StreamZonesNow();
	/** An extra focus (a capture's camera); bOn false drops it. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|Zones")
	void SetZoneFocusForTest(FVector LocationCm, bool bOn);
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Zones")
	FString DescribeZones() const;
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Zones")
	int32 GetZoneCount() const { return Zones.Num(); }
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Zones")
	int32 GetZoneUnitCount() const { return ZoneUnits.Num(); }
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Zones")
	int32 GetActiveZoneUnits() const;
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Zones")
	int32 GetActiveZoneCells() const;
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Zones")
	int64 GetZoneCacheBytes() const { return ZoneCacheBytes; }
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Zones")
	int32 GetZoneCacheEntries() const { return ZoneCache.Num(); }
	/** The zone whose outline holds a world XY (any zone, live or not), or null. */
	AGTDeformZone* ZoneAt(const FVector2D& XYCm, const AGTDeformZone* Except = nullptr) const;
	bool HasZonePatches() const { return LiveZoneUnits > 0; }
	/** Benmore B2c: a world point inside a live mud zone's patch (any game world): the spray's gravel grit stays off there. */
	static bool IsInLiveMudZone(const FVector& PointCm);
	/** A wheel's stroke on a zone patch also goes into the same zone's other live patches its reach touches (a tile's overlap cells),
	 *  so a rut runs on across a tile border. The primary's stamp is the traction's; these return nothing to it. */
	void StampZoneNeighbours(const AGTMudPatch& Primary, const FVector2D& FromCm, const FVector2D& ToCm, float WidthCm, float DepthCm, const FVector2D& Heading, float RolledCm);

	/** MPC_TrackPaint's Patch0..Patch3 (Art/setup_m6_mud.bat adds them: a material may reference two collections and the landscape already has weather and track paint) get the patches' boxes (x0 y0 x1 y1 cm) so M_GT_Landscape pushes its Mud and Bog layers back in depth under them. */
	FString CollectionPath = TEXT("/Game/GrandTour/Terrain/MPC_TrackPaint.MPC_TrackPaint");
	bool bCollectionWritten = false;

private:
	UPROPERTY()
	TArray<TObjectPtr<AGTMudPatch>> Patches;

	// Benmore B2: the zones, their units, the cache and the coverage.
	UPROPERTY()
	TArray<TObjectPtr<AGTDeformZone>> Zones;
	struct FZoneUnit
	{
		int32 ZoneIndex = INDEX_NONE;
		int32 Slot = 0;
		FIntPoint Tile = FIntPoint::ZeroValue;
		bool bWhole = false;
		FBox2D OwnBox = FBox2D(ForceInit);
		FBox2D FieldBox = FBox2D(ForceInit);
		int32 Cells = 0;
		float Distance = 0.f;
		TWeakObjectPtr<AGTMudPatch> Patch;
		TArray<float> BaseHeight;
		TArray<float> BaseLump;
		TArray<FVector2f> BaseOffset;
		TArray<uint8> BaseTracks;
		TArray<float> BaseHeading;
		TArray<float> BasePhase;
	};
	TArray<FZoneUnit> ZoneUnits;
	struct FZoneCacheEntry
	{
		TArray<uint8> Bytes;
		int32 RawBytes = 0;
		int32 Cells = 0;
		uint64 Stamp = 0;
	};
	TMap<uint64, FZoneCacheEntry> ZoneCache;
	int64 ZoneCacheBytes = 0;
	uint64 ZoneCacheClock = 0;
	int32 ZoneCacheEvicted = 0;
	int32 LiveZoneUnits = 0;
	int32 ZoneActivations = 0;
	int32 ZoneReleases = 0;
	int32 ZoneRestores = 0;
	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> CoverageTexture;
	TArray<FColor> Coverage;
	FVector2D CoverageOrigin = FVector2D::ZeroVector;
	bool bCoverageValid = false;
	int32 CoverageWrites = 0;
	FTimerHandle ZoneTimer;
	FVector TestFocus = FVector::ZeroVector;
	bool bTestFocus = false;
	void GatherZones(UWorld& InWorld);
	void OnZoneTimer();
	int32 StreamZones(bool bAll);
	bool ActivateZoneUnit(int32 Index);
	void ReleaseZoneUnit(int32 Index);
	void ZoneAfterField(AGTMudPatch& Patch, int32 Index, const TArray<uint8>& Cached);
	void GetZoneFoci(TArray<FVector2D>& Out) const;
	void RebuildCoverage(bool bForce);
	static uint64 ZoneUnitKey(int32 ZoneId, int32 Slot) { return (static_cast<uint64>(static_cast<uint32>(ZoneId)) << 32) | static_cast<uint32>(Slot); }

	// LM1: the settle readout, one frame accumulated at a time.
	void FoldSettleFrame();
	uint64 SampleFrame = MAX_uint64;
	bool bFrameSettleOn = false;
	float FrameSettleMs = 0.f;
	float FrameUploadMs = 0.f;
	int32 FrameAwake = 0;
	int32 SettleFrames = 0;
	double SettleSumMs = 0.0;
	float SettleMaxMs = 0.f;
	int32 SettleAwakePeak = 0;
	int32 UploadFrames = 0;
	double UploadSumMs = 0.0;
	float UploadMaxMs = 0.f;
	// LM2a/LM2b: every frame's time per feature, for the p99; and the clods' frame.
	TArray<float> SettleSamples;
	TArray<float> UploadSamples;
	TArray<float> ClodSamples;
	bool bFrameClodsOn = false;
	float FrameClodMs = 0.f;
	double ClodSumMs = 0.0;
	float ClodMaxMs = 0.f;
	// LM4e: the stamps, the swept tiles and the uploaded cells per frame.
	uint64 CostFrame = MAX_uint64;
	float FrameStampMs = 0.f;
	int32 FrameSwept = 0;
	int32 FrameUploadCells = 0;
	int32 CostFrames = 0;
	double SweptSum = 0.0;
	double UploadCellsSum = 0.0;
	TArray<float> StampSamples;
	void FoldCostFrame();
	// MR5: the awake cap's frame and its counts.
	uint64 ChunkCapFrame = MAX_uint64;
	int32 ChunkAwakeNow = 0;
	int32 ChunkAwakePeak = 0;
	int32 ChunksCapped = 0;
	static float Percentile(const TArray<float>& Samples, float P);
};
