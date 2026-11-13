#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GTMudSplatSubsystem.generated.h"

class AActor;
class ALandscapeProxy;
class UDecalComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
struct FHitResult;

/**
 * MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1 item 3): thrown mud that leaves every patch splats where it comes down
 * instead of vanishing. UGTSprayComponent traces each volume-carrying blob's path once a frame outside every patch, at most
 * MaxTracesPerFrame traces a frame across every car (ReserveTrace); a hit comes here:
 * - on a landscape: a splat into the track paint's G and B (UGTTrackPaintSubsystem::AddSplat), radius SplatRadiusMin..Max x
 *   the blob's, a random atlas blot;
 * Inside a patch's box the blob's path is traced too (the same cap), and only a static mesh takes it there: a patch's box
 * reaches 2 m past its mud, so every post or rock beside a section (the winch posts included) stands inside one.
 * - on a static mesh (a rock, a post, dressing, a road mesh; not a pawn, not a simulating body, not a water sheet, not a
 *   patch's own mesh or clods): a pooled
 *   deferred decal, M_GT_MudSplatDecal (Art/Unreal/mud_cover.py) with its own instance (Tile, SpawnTime, SizeCm), at most
 *   MaxDecals alive, the oldest out first; the material goes wet to dry over 90 s and fades out over DecalLifeSeconds, and a
 *   decal past it is hidden and free again.
 * gt.Mud.Splats 0 turns both off (the blob is lost as before MR1). Blobs hitting the car are MR2's.
 *
 * MR2 housekeeping (docs/MUDRUNNER_LESSONS_PLAN.md MR2): a blob is traced only while it is descending and within TraceBandCm of
 * the surface under it (a patch's field surface inside a box; outside, the landscape's height from LandscapeHeightAt, a heightfield
 * lookup with no trace); a blob outside every patch that goes under the landscape's height splats there without a trace
 * (SplatGround). A decal is shown only once M_GT_MudSplatDecal's shaders are compiled: until then the renderer draws a decal with
 * the engine's fallback (DefaultDeferredDecalMaterial, an unlit opaque box: the black square of MR1's GoWR rerun), so a splat
 * that arrives earlier waits hidden and shows when they are ready, with its own spawn time.
 */
UCLASS()
class GRANDTOUR_API UGTMudSplatSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UGTMudSplatSubsystem, STATGROUP_Tickables); }

	/** One blob trace this frame, if the frame's MaxTracesPerFrame are not spent (then the blob traces next frame from where it was). */
	bool ReserveTrace();

	/** A thrown blob of BlobRadiusCm hit something: a landscape splat or a static mesh decal. False when nothing was made. With
	 * bMeshesOnly (a blob inside a patch's box, whose field takes it on the ground) only a static mesh takes it. */
	bool Splat(const FHitResult& Hit, float BlobRadiusCm, int32 Seed, bool bMeshesOnly = false);

	/** The check's own blob path (a synthetic throw, counted apart): traced Start to End as a thrown blob's is (world static and
	 * dynamic objects, pawns ignored), and splatted where it hits. True when it made a splat. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|Splats")
	bool TraceSplat(FVector Start, FVector End, float BlobRadiusCm, int32 Seed);

	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetSyntheticSplats() const { return SyntheticSplats; }

	/** MR2 housekeeping 4: the landscape's height under a point (a heightfield lookup, no trace); false where no landscape is. */
	bool LandscapeHeightAt(const FVector& Point, float& OutZ);

	/** MR2 housekeeping 4: a blob went under the landscape's height at Point outside every patch: a track paint splat there, no trace. */
	bool SplatGround(const FVector& Point, float BlobRadiusCm, int32 Seed);

	/** MR2 housekeeping 4: a blob out of the trace band this frame (rising, or more than TraceBandCm over the surface under it). */
	void NoteSkippedTrace() { ++SkippedTraces; }

	/** MR2 housekeeping 3: M_GT_MudSplatDecal's shaders are compiled for this world's platform (a decal is shown only then). */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|Splats")
	bool IsDecalMaterialReady();

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Splats")
	int32 MaxTracesPerFrame = 64;

	/** MR2 housekeeping 4: a blob is traced only while descending and within this of the surface under it, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Splats")
	float TraceBandCm = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Splats")
	int32 MaxDecals = 96;

	/** A splat's reach, x the blob's radius. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Splats")
	float SplatRadiusMin = 2.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Splats")
	float SplatRadiusMax = 3.f;

	/** A decal's whole life (the material fades it out over the same time), s. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Splats")
	float DecalLifeSeconds = 600.f;

	/** The decal's projection depth either side of the surface, x its reach. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Splats")
	float DecalDepthScale = 0.6f;

	UPROPERTY(EditAnywhere, Category = "GT|Mud|Splats")
	FString DecalMaterialPath = TEXT("/Game/GrandTour/Mud/Splats/M_GT_MudSplatDecal.M_GT_MudSplatDecal");

	/** The check's readouts. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetLiveDecalCount() const;

	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetDecalSplats() const { return DecalSplats; }

	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetLandscapeSplats() const { return LandscapeSplats; }

	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetTraceCount() const { return TraceCount; }

	/** Traces refused because a frame's MaxTracesPerFrame were spent. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetCappedTraces() const { return CappedTraces; }

	/** Hits on something that takes no splat (a pawn, a water sheet, a simulating body, a non-mesh surface). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetIgnoredHits() const { return IgnoredHits; }

	/** MR2 housekeeping 4: blob-frames out of the trace band (no trace asked), and landscape splats made by the height test alone. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetSkippedTraces() const { return SkippedTraces; }

	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetHeightSplats() const { return HeightSplats; }

	/** MR2 housekeeping 3: decals that waited hidden for the material's shaders, and those still waiting. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetHeldDecals() const { return HeldDecals; }

	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	int32 GetPendingDecalCount() const;

	/** The decals' names of what they landed on, one per live decal (the check's report). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Splats")
	TArray<FString> DescribeDecals() const;

private:
	UDecalComponent* TakeDecal(int32& OutIndex);

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> DecalMaterial = nullptr;

	UPROPERTY(Transient)
	TObjectPtr<AActor> PoolActor = nullptr;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UDecalComponent>> Decals;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> DecalMaterials;

	TArray<double> DecalBorn;
	TArray<FString> DecalOn;
	/** MR2 housekeeping 3: per decal, 0 free, 1 placed and waiting for the material's shaders, 2 shown. */
	TArray<uint8> DecalState;
	TArray<TWeakObjectPtr<ALandscapeProxy>> Landscapes;
	bool bLandscapesLooked = false;
	double LandscapesLookedAt = 0.0;
	bool bDecalReady = false;
	int32 SkippedTraces = 0;
	int32 HeightSplats = 0;
	int32 HeldDecals = 0;
	bool bMaterialLooked = false;
	uint64 TraceFrame = 0;
	int32 TracesThisFrame = 0;
	int32 TraceCount = 0;
	int32 CappedTraces = 0;
	int32 LandscapeSplats = 0;
	int32 DecalSplats = 0;
	int32 IgnoredHits = 0;
	int32 SyntheticSplats = 0;
	float ExpireTimer = 0.f;
};
