#pragma once

#include "CoreMinimal.h"
#include "Engine/StaticMeshActor.h"
#include "Terrain/GTWaterField.h"
#include "Terrain/GTMudContactFoam.h"
#include "GTWaterSheet.generated.h"

class ALandscapeProxy;
class UMaterialInstanceDynamic;
class UProceduralMeshComponent;
class UTexture2D;
class UGTRiverReference;
class UGTWaterDomain;
class UTextureRenderTarget2D;
class UMaterialInterface;
class AGTLandscapeSurface;
class UMeshComponent;

/**
 * Water stage R1 (docs/WATER_PLAN.md section 6, the standing finding): what a run costs the water, kept in EVERY run,
 * rendered ones included. A look change on the sheet once changed what the user felt with no physics code touched,
 * because the solver takes at most MaxSubSteps of 1/60 s a frame and under 15 fps the water runs in slow motion. One
 * window is logged once a second near the player, another is taken by each shots and test step; a picture taken in a
 * window whose Clamps is not 0 is void, and Art/tools/sample_ford.ps1 says so.
 */
struct FGTWaterRunStats
{
	/** Every frame the sheet ticked, and the game's own frame time over them, ms. */
	int32 Frames = 0;
	double FrameMsSum = 0.0;
	float FrameMsWorst = 0.f;
	/** The frames the solver actually stepped on, and what FGTWaterField::Step cost, ms. */
	int32 StepFrames = 0;
	double StepMsSum = 0.0;
	float StepMsWorst = 0.f;
	/** Sub-steps the accumulator asked for, sub-steps run, frames the cap cut and the simulated time it dropped. */
	int32 SubStepsAsked = 0;
	int32 SubStepsRun = 0;
	int32 Clamps = 0;
	float DeficitSeconds = 0.f;

	float FrameMsMean() const { return Frames > 0 ? static_cast<float>(FrameMsSum / Frames) : 0.f; }
	float StepMsMean() const { return StepFrames > 0 ? static_cast<float>(StepMsSum / StepFrames) : 0.f; }
	void Reset() { *this = FGTWaterRunStats(); }
};

/**
 * Water over a ford (driving feel stage 3): a translucent sheet with no collision whose surface the car reads. The
 * still level is the placed height plus water stage W5's river stage (UGTWaterSubsystem: the rain in the catchment,
 * lagged), plus RiseWithWetnessCm x the weather's ground wetness, which is 0 since W5 replaced it, and
 * ExtraRiseCm (plus the cvar gt.Water.ExtraRiseCm) is for events and tests. The car reads it through
 * UGTWaterSubsystem::Sample at each wheel's contact point and at five points on the hull: depth drags the wheel,
 * lightens the tyre, floats the body (W2) and, past the intake, floods the engine (UGTConditionComponent).
 *
 * Water stage W1 (docs/WATER_PLAN.md): the sheet carries a current - FlowDirection at FlowSpeedCmPerS.
 *
 * Water stage WS1: the surface is simulated. The sheet owns an FGTWaterField, a shallow-water height field over its
 * footprint at FieldCellCm, whose two flow-wise ends are held half of HeadDropCm over the level (upstream) and half
 * under it (downstream) so the current is a real flow across the bed rather than a constant vector; a disturbance spreads as
 * a ring and reflects off the banks. The engine cube is hidden and the surface is a UProceduralMeshComponent grid at
 * the field's cells wearing M_GT_Water, displaced in the vertex shader by an R/G float texture the sheet uploads
 * every frame (R the surface over the level in cm, G the depth in cm). gt.Water.FlowScale scales HeadDropCm, so 0 is
 * still water; gt.Water.ExtraRiseCm still raises the river, and the field fills from its two ends.
 *
 * Art/setup_m6_hide.py lays one over each ford section, scaled to the crossing, and sets the flow from the section's
 * FlowSpeedMps and FlowYawOffsetDeg; the builder's prefix list removes it on a rebuild like the other props.
 */
UCLASS()
class GRANDTOUR_API AGTWaterSheet : public AStaticMeshActor
{
	GENERATED_BODY()

public:
	AGTWaterSheet();
	/** Opt-in closed pond over deformable mud, using the shared field, queries and hull/wheel sources. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="GT|Water|Mud")
	TObjectPtr<AGTLandscapeSurface> MudSurface;
	/** Optional baked pool seed. Used once; subsequent wet coverage follows live bed/flow. */
	UPROPERTY(EditAnywhere, Category="GT|Water|Mud") TObjectPtr<UGTWaterDomain> MudInitialDomain;
	UPROPERTY(EditAnywhere, Category="GT|Water|Mud") TObjectPtr<UMaterialInterface> MudStateMaterial;
	UPROPERTY(EditAnywhere, Category="GT|Water|Mud") TObjectPtr<UMaterialInterface> MudSedimentMaterial;
	UPROPERTY(EditAnywhere, Category="GT|Water|Mud") TObjectPtr<UMaterialInterface> MudWaveMaterial;
	/** Fixed connected-basin extent. Resolution is budgeted to at most 128 x 128 cells. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="GT|Water|Mud", meta=(ClampMin="100",ClampMax="3200"))
	float MudHalfSizeCm=1575.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="GT|Water|Mud", meta=(ClampMin="10",ClampMax="100"))
	float MudCellCm=25.f;
	/** Optional scenic basin: initialize its still surface before entering the simulation budget. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="GT|Water|Mud")
	bool bBuildSleepingMudBasin=false;
	UFUNCTION(BlueprintPure, Category="GT|Water|Mud")
	FString MudWaterDiagnostics() const;
    // Research-only rendering bridge; never used by physical water queries.
    bool BindResearchSimulation(UMaterialInstanceDynamic* Material);
    void SetResearchWaterTextures(UTextureRenderTarget2D* State,UTextureRenderTarget2D* Sediment,UTextureRenderTarget2D* Waves);
	/** Whole-level mean water; a single interaction window follows the local player. */
	UPROPERTY(EditAnywhere, Category="GT|Water|Domain")
	TObjectPtr<UGTWaterDomain> WaterDomain;
	/** Opt in to live river shores. Closed mud ponds continue to use MudSurface. */
	UPROPERTY(EditAnywhere, Category="GT|Water|Domain")
	TObjectPtr<AGTLandscapeSurface> DomainGroundSurface;
	UPROPERTY(EditAnywhere, Category="GT|Water|Domain",meta=(ClampMin="0",ClampMax="400"))
	float DomainShoreMarginCm=250.f;
	UPROPERTY(EditAnywhere, Category="GT|Water|Domain")
	TArray<TObjectPtr<AStaticMeshActor>> DomainSurfaces;
    UPROPERTY() TArray<TObjectPtr<UMeshComponent>> RoadPoolSurfaces;
	/** Optional numerical wave precombine, shared by this domain's near/far surfaces.
	 * Cosmetic only: never sampled by buoyancy, the bed, or the disturbance solver. */
	UPROPERTY(EditAnywhere, Category="GT|Water|Domain")
	TObjectPtr<UMaterialInterface> AmbientWaveMaterial;
	/** Zero retains the legacy domain/fixture size; native Waves uses 512. */
	UPROPERTY(EditAnywhere, Category="GT|Water|Domain", meta=(ClampMin="0", ClampMax="1024"))
	int32 AmbientWaveResolution=0;
	/** Absolute wave clock for fixed-camera editor motion reviews; no physics time advance. */
	UFUNCTION(BlueprintCallable, Category="GT|Water|Domain")
	void PreviewAmbientWaves(float Seconds);
	/** Explicit fixed-time preview at any river/lake point (also useful for editor validation). */
	UFUNCTION(BlueprintCallable, Category="GT|Water|Domain")
	void PreviewWaterAt(FVector2D WorldXY, float Seconds, bool Reset);
	/** Editor-only moving immersed footprint, for repeatable wake pictures without vehicle tuning. */
	UFUNCTION(BlueprintCallable, Category="GT|Water|Domain")
	void PreviewWaterWake(FVector2D Start,FVector2D End,float Seconds);
	/** Cosmetic hull pressure ridge/wake, rasterized into the existing detail texture only. */
	void SetVisualVehicleWake(AActor* Source,FVector2D Centre,FVector2D Travel,
		float HalfLengthCm,float HalfWidthCm,float SpeedMps,float ImmersionM);
	UFUNCTION(BlueprintCallable, Category="GT|Water|Domain")
	FString WaterDiagnostics(bool Reset=false) { return Reset ? TakeStepStatsLine(TEXT("Domain")) : StatsLine(StepStats,TEXT("Domain")); }

	/** Optional fixed-bank river pilot. Null preserves the existing ford path. */
	UPROPERTY(EditAnywhere, Category="GT|Water|River")
	TObjectPtr<UGTRiverReference> RiverReference;
	/** Existing river geometry to displace. Uses SurfaceMaterialPath and never draws a second sheet. */
	UPROPERTY(EditAnywhere, Category="GT|Water|River")
	TObjectPtr<AStaticMeshActor> RiverSurface;
	UPROPERTY(EditAnywhere, Category="GT|Water|River", meta=(ClampMin="25"))
	float RiverActiveDistanceM = 100.f;
	/** Stationary editor preview, fixed simulation time. Does nothing in a game world. */
	UFUNCTION(BlueprintCallable, Category="GT|Water|River")
	void PreviewRiver(float Seconds, bool Reset);

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

	/** The still water level, world cm. 0 means "where the actor was placed", set in BeginPlay. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Water")
	float BaseLevelCm = 0.f;

	/**
	 * How much the weather's ground wetness (0..1) lifts the water, cm at wetness 1. **0 since water stage W5**:
	 * a river does not follow the puddles, it follows the rain in its catchment with a lag, and that is
	 * UGTWaterSubsystem's river stage. The field is kept (and still in the sum) for a pond or a sheet that should
	 * follow the ground.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Water")
	float RiseWithWetnessCm = 0.f;

	/** An extra rise for events and tests, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Water")
	float ExtraRiseCm = 0.f;

	/** W1: which way the current runs, unit, world XY. Zero is still water. WS1 makes it the field's +X. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Water")
	FVector2D FlowDirection = FVector2D::ZeroVector;

	/** W1: how fast it runs, cm/s (the section's FlowSpeedMps x 100). WS1 reads it only for the log and the pictures: the speed is the field's now. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Water")
	float FlowSpeedCmPerS = 0.f;

	/** W1: the flow faded to zero over the last this many metres at the sheet's ends. WS1: the length of the solver's friction ramp there. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Water")
	float FlowFadeM = 5.f;

	// ---- WS1 ---------------------------------------------------------------------------------------------
	/** The field's cell, cm. The Hide's 74 x 30 m sheet is 120 x 296 = 35,520 cells at 25. */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	float FieldCellCm = 25.f;

	/** The head across the field, cm, held centred on the level (half over it upstream, half under downstream): what the current's speed is set by. */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	float HeadDropCm = 30.f;

	/** The solver's numerical damping per sub-step, and the bed's Chezy drag (the steady speed is sqrt(g h S / BedFriction)). */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	float PipeDamping = 1.e-3f;

	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	float BedFriction = 0.005f;

	/** How much the bed friction is multiplied by at the very flow-wise ends (1 + this), ramped in over FlowFadeM. */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	float EndFriction = 1.f;

	/** The gain on the finite-difference slope the material turns into a normal. */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	float NormalGainCm = 1.f;

	/** Water shallower than this draws nothing (the material's opacity mask), cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	float DryCutCm = 1.f;

	/**
	 * A level change bigger than this in one tick is carried into the field at once instead of filling from the ends,
	 * cm. **0 since WS2's follow-up: every change is carried.** At 5 the weather's own rise crept in through the two
	 * heads, which is the one thing that excites the basin's mode - a 70 cm step at the ends alone rang the middle
	 * 103.6 cm peak to peak. Carried, the whole surface lifts in the same tick and there is no wave at all.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	float LevelJumpCm = 0.f;

	// ---- WS2: the sources ----------------------------------------------------------------------------------
	/** How fast a lid (the car's hull or a wheel occupying the water column) may grow or shrink, m/s. */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Sources")
	float LidRateMps = 1.5f;

	/** The wind's kick on a patch of faces, cm/s, and how long its amplitude takes to wander. */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Sources")
	float WindRippleCm = 45.f;

	UPROPERTY(EditAnywhere, Category = "GT|Water|Sources")
	float WindGustS = 4.f;

	/** Drops per square metre of water per second at rain 1, and how high one lifts its cell (its eight neighbours pay for it). */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Sources")
	float RainDropsPerM2S = 20.f;

	UPROPERTY(EditAnywhere, Category = "GT|Water|Sources")
	float RainDropCm = 0.8f;

	/**
	 * How fast the sponge over the last FlowFadeM at each end pulls the depth back to the boundary's head, seconds
	 * (0 is off), and how hard it damps the flux through the end. Built, measured and left off: five metres of
	 * relaxation cannot absorb a wave the length of the basin, and what stops the reflection is the open ends
	 * (FGTWaterField::bOpenEnds).
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Sources")
	float SpongeTauS = 0.f;

	UPROPERTY(EditAnywhere, Category = "GT|Water|Sources")
	float SpongeFluxDamp = 0.f;

	/** How far over and under the level the surface mesh's render bounds reach, cm (the vertex shader moves it). */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	float SurfaceRangeCm = 250.f;

	UPROPERTY(EditAnywhere, Category = "GT|Water|Surface")
	FString SurfaceMaterialPath = TEXT("/Game/GrandTour/Materials/M_GT_Water.M_GT_Water");

	// ---- RIVERBED S3: the water fills its basin (VEHICLE_BUILD_SYSTEM 53) -----------------------------------
	/**
	 * The margin round the basin's wet region (GTFORDFILL at the level) that the field is laid over, m. Proposed
	 * 2026-09-23, unmeasured: the owner names it.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Basin")
	float BasinMarginM = 2.f;
	/** Explicit connected channel seed; avoids selecting an unrelated deeper hollow. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="GT|Water|Basin")
	bool bUseAuthoredBasinSeed = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="GT|Water|Basin")
	FVector2D AuthoredBasinSeedCm = FVector2D::ZeroVector;
	/** Extend wet surface height across dry bank cells; G carries signed shore depth. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="GT|Water|Surface")
	bool bContinuousShoreRendering = false;

	/**
	 * The most cells one field simulates; a still basin past it is clipped along the flow about the crossing and goes
	 * on as the static part. Proposed 2026-09-23 from the step cost measured before S3 on a quiet machine (NullRHI):
	 * forda 0.501 ms / 25,920 cells = 19.3 ns, fordb 0.517 / 28,800 = 18.0 ns (ford_diag.log 11:42), the Hide 0.707 /
	 * 35,520 = 19.9 ns (water_test.log steps 0-7, the car in the water in some): 57,000 cells is 1.14 ms a step at
	 * 19.9 ns, twice WS1's 0.57. Extrapolated, unmeasured past 35,520 cells. 0 is no cap.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Water|Basin")
	int32 MaxSimCells = 57000;

	/** True when the field is laid over the basin (S3), false on the placed box (before S3, or -GTWaterPlacedBox). */
	bool IsBasinBox() const { return bBasinBox; }
	/** Whether the basin was clipped by MaxSimCells, and the basin's own cells (the fill at the heads' level) in the field. */
	bool IsBasinCapped() const { return bBasinCapped; }

	/**
	 * RIVERBED S3: the step the field's edges stand at against a flat sheet at the level, cm - the mean and the
	 * largest over the wet cells of the two flow-wise end columns (and of the two side rows), which is what a static
	 * sheet at the level meets there. Logged as GTFORDSEAM 5 s and 30 s after the field is built.
	 */
	FString SeamLine() const;

	UFUNCTION(BlueprintPure, Category = "GT|Water")
	float GetLevelCm() const { return (RiverReference || WaterDomain || MudSurface) ? BaseLevelCm : BaseLevelCm + WetnessRiseCm + RiverRiseCm + ExtraRiseCm + CvarExtraRiseCm; }

	/** W5: how much of this level is the river stage, cm (the test's "base + stage" is GetLevelCm with no extra on). */
	float GetRiverRiseCm() const { return RiverRiseCm; }

	/** True when the world point (X, Y) lies inside the sheet's footprint. */
	UFUNCTION(BlueprintPure, Category = "GT|Water")
	bool Covers(FVector2D WorldXY) const;

	/** WS1: the simulated surface's world Z at a world XY, cm - the level where the field is not built yet. */
	UFUNCTION(BlueprintPure, Category="GT|Water")
	float SurfaceCmAt(FVector2D WorldXY) const;

	/** Water above the fine mud surface, bounded by the conserved coarse water column. */
	float MudWaterDepthCmAt(FVector2D WorldXY) const;

	/** WS1: the current there, cm/s in world XY (the field's velocity; W1's faded constant as the fallback). */
	UFUNCTION(BlueprintPure, Category="GT|Water")
	FVector2D FlowCmPerSAt(FVector2D WorldXY) const;

	/** The flow's nominal speed after gt.Water.FlowScale, cm/s (the section's own, not the field's; the pictures log it). */
	float ScaledFlowSpeedCmPerS() const { return FlowSpeedCmPerS * AppliedFlowScale; }

	/** How far the footprint reaches along the flow from the sheet's centre, cm. */
	float FlowHalfSpanCm() const;
	/** And across it. */
	float CrossHalfSpanCm() const;

	const FGTWaterField& GetField() const { return Field; }
	FGTWaterField& GetMutableField() { return Field; }
	/** WS1: the surface mesh's vertex count and the field texture's size, for the test. */
	int32 GetSurfaceVertexCount() const { return SurfaceVertexCount; }
	UTexture2D* GetFieldTexture() const { return FieldTexture; }
	/** Controlled probes: R physical surface, G depth, B rendered surface, A speed (cm units). */
	UFUNCTION(BlueprintPure, Category="GT|Water|Review")
	FLinearColor ReviewWaterColumn(FVector2D WorldXY) const;
	/** One stationary body-occupancy stamp; never moves or controls a vehicle. */
	UFUNCTION(BlueprintCallable, Category="GT|Water|Review")
	void ReviewWaterContact(FVector2D WorldXY, float ImmersionCm);

	/**
	 * W4: the texel the field texture carries for a cell, which is what M_GT_Water reads.
	 *   R  the surface's height over the water level, cm (WS1's: a dry cell carries its bed, so the shoreline
	 *      vertices walk down to the bank instead of falling off a cliff)
	 *   G  the water column, cm - the depth plus WS2's lid, so the mesh is not cut away under a car that has pushed
	 *      its own cells dry; 0 on a dry cell with nothing standing in it. The depth the colour and the opacity ride
	 *      on, and the mask.
	 *   B, A  the cell's depth-averaged flow in the FIELD's own axes, cm/s (X along the flow), which is the frame the
	 *      material already maps world XY into, so the ripple pans with the current without a second rotation. Zero
	 *      on a dry cell: the solver leaves the last velocity in a cell that has just dried, and a ripple panned by
	 *      it would ride over dry ground.
	 * The texture is written on the game thread and handed to the render thread, so this is also exactly what the
	 * water test reads - a NullRHI run cannot sample a texture, but it can read the texel that went into it.
	 */
	static FLinearColor FieldTexel(const FGTWaterField& InField, float LevelCm, int32 Index);
	static FLinearColor ShoreTexel(const FGTWaterField& InField, float LevelCm, int32 Index);
	FLinearColor FieldTexelAt(int32 Index) const { return FieldTexel(Field, GetLevelCm(), Index); }

	/** Puts the field back to flat still water at the current level (the tests' "still water"). */
	void CalmField();

	// ---- R1: instrumentation ------------------------------------------------------------------------------
	/** What the sheet has cost since the last step line was taken (the window a shots or test step reads). */
	const FGTWaterRunStats& GetStepStats() const { return StepStats; }

	/** The GTWATERSTATS line for a window: frame ms, step ms, sub-steps asked against run, the clamps and the deficit. */
	FString StatsLine(const FGTWaterRunStats& Stats, const TCHAR* Why) const;

	/** The step window's line, the window then started again: the runner logs it at the end of every shots and test step. */
	FString TakeStepStatsLine(const TCHAR* Why);

	/** R1: how many of the field's cells took their bed from the trace (a stone standing in the channel) and how many were traced at all. */
	int32 GetBedFromTraceCells() const { return BedFromTraceCells; }
	int32 GetBedTracedCells() const { return BedTracedCells; }

	/**
	 * WS2: a solid occupying the water column here (the car's hull box, a wheel). The stamps of a tick are gathered
	 * and taken into the field at its next step, rate-limited by LidRateMps; UGTHullComponent writes them.
	 */
	void StampLid(const FVector2D& CentreCm, const FVector2D& ForwardXY, float HalfLenCm, float HalfWidCm,
		float BottomZCm, const FVector2D& BottomSlope, float MaxHeightCm, float Fill);

	/** WS2: the rain the sheet read at its own centre this tick, 0..1 (the field's drops are that times RainDropsPerM2S). */
	float GetRainAtSheet() const { return AppliedRain; }
	/** A ring: RiseCm of water over a disc of RadiusCm. Returns the volume added, m3. */
	UFUNCTION(BlueprintCallable, Category="GT|Water")
	double AddImpulse(FVector2D WorldXY, float RadiusCm, float RiseCm);

	/** Water depth (cm) over a ground point inside a sheet, 0 outside every sheet or where the ground is above the water. A thin wrapper over UGTWaterSubsystem::Sample since W1. */
	static float DepthCmAt(const UWorld* World, const FVector& GroundPoint);

	/**
	 * Raises or lowers every sheet in the world by ExtraRiseCm (tests, events). The whole surface is carried to the
	 * new level in one step (FGTWaterField::ShiftLevel) unless bShiftField is false, in which case the level moves
	 * only at the two fixed heads and the field fills from its ends - which is what the water test measures, and what
	 * a 70 cm step does to the basin's seiche.
	 */
	static void SetExtraRiseAll(UWorld* World, float ExtraCm, bool bShiftField = true);

	/** Calms every sheet's field (the still-water control, which the friction alone would take about 40 s to reach). */
	static void CalmAll(UWorld* World);

	/** Diagnostic: actual filtered water-relative motion driving the visual bow. */
	UFUNCTION(BlueprintPure, Category="GT|Water|Diagnostics")
	FVector2D GetVisualWakeMotion(AActor* Source) const;

private:
	void TickMudWater(float Dt);
	void UploadMudFoam();
	void StepNativeMudVisual(float Dt);
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MudStateDynamic;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MudSedimentDynamic;
	UPROPERTY(Transient) TArray<TObjectPtr<UTextureRenderTarget2D>> MudStateTargets;
	UPROPERTY(Transient) TArray<TObjectPtr<UTextureRenderTarget2D>> MudSedimentTargets;
	UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> MudWaves;
	int32 MudPrevious=0, MudNativeSteps=0;
	float MudNativeCarry=0;
	FGTMudContactFoam MudFoam;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> MudFoamTexture;
	TArray<float> MudBaseCm, MudBedCm;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> MudBaseTexture;
	uint64 MudBedRevision=MAX_uint64;
	float MudBedTime=0.f, MudUploadTime=0.f;
	double MudInitialVolume=0., MudBedPeakMs=0.;
	int32 MudBedUpdates=0;
	bool bMudAwake=false;
	struct FVisualVehicleWake
	{
		TWeakObjectPtr<AActor> Source;
		FVector2D Centre,Travel,MotionMps;
		float HalfLength=220,HalfWidth=95,Speed=0,Immersion=0,Updated=0,LastRipple=0;
	};
	TArray<FVisualVehicleWake> VisualVehicleWakes;
	struct FVisualTrailWave
	{
		FVector2D Centre,FlowCmPerS,Outward;
		float Born=0,Energy=0;
	};
	TArray<FVisualTrailWave> VisualTrailWaves;
	void RasterVisualVehicleWakes(TArray<FColor>& Data);
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> DomainMaterials;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> RiverDetailTexture;
	UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> AmbientWaveTarget;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> AmbientWavePrecombine;
	float AmbientWaveLastTime=-1.f;
	bool bAmbientWaveWasEnabled=false;
	void UpdateAmbientWaves(float Seconds,bool Force=false);
	float DomainUploadCarry=0;
	int32 DomainDetailEnabled=-1;
	void UploadRiverDetail();
	FVector2D DomainFocus=FVector2D::ZeroVector;
	TArray<float> DomainGroundCm,DomainMeanCm;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> DomainGroundTexture;
	TArray<FVector2D> DomainCurrent;
	TArray<uint8> DomainSupported;
	uint64 DomainBedRevision=0;
	float DomainBedCarry=0;
	bool SampleDomainWater(FVector2D XY,float& S,float& D,FVector2D& V) const;
	void RefreshDomainBed();
	bool MoveWaterWindow(FVector2D Focus, bool Force=false);
	void BindWaterWindow();
	void TickWaterDomain(float DeltaSeconds);
	float WetnessRiseCm = 0.f;
	/** W5: the river stage read off UGTWaterSubsystem once a tick, cm (cached like the cvars, so every query is cheap). */
	float RiverRiseCm = 0.f;
	float AppliedLevelCm = -1.e9f;
	/** gt.Water.ExtraRiseCm and gt.Water.FlowScale, read once a tick on the game thread so every query is cheap and thread-safe. */
	float CvarExtraRiseCm = 0.f;
	float AppliedFlowScale = 1.f;
	/** WS2: gt.Water.Wind and gt.Water.Lids as read this tick, and the weather's rain at the sheet's centre. */
	float AppliedWind = 1.f;
	bool bLidsOn = true;
	float AppliedRain = 0.f;

	// ---- WS1 ---------------------------------------------------------------------------------------------
	FGTWaterField Field;
	bool bFieldBuilt = false;
	bool bRiverAwake = false;
	float RiverFarSeconds = 0.f;

	UPROPERTY(Transient)
	TObjectPtr<UProceduralMeshComponent> SurfaceMesh;

	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> FieldTexture;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> SurfaceMaterial;

	int32 SurfaceVertexCount = 0;
	/** The level the field was last carried to, cm, and a one-shot that lets a test move the level without carrying it. */
	float FieldLevelCm = -1.e9f;
	bool bSuppressNextShift = false;
	FVector2D MeshCentreCm = FVector2D::ZeroVector;
	int32 UploadCount = 0;

	// ---- R1 ------------------------------------------------------------------------------------------------
	/** The window logged once a second while a camera or a pawn is within StatsNearM, and the one a step takes. */
	FGTWaterRunStats SecondStats;
	FGTWaterRunStats StepStats;
	/** The field's cumulative counters as they stood last tick, so a tick's own share can be taken out of them. */
	int32 LastSubStepsAsked = 0;
	int32 LastSubStepsRun = 0;
	int32 LastClamps = 0;
	float LastDeficitSeconds = 0.f;
	float SinceStatsLog = 0.f;
	/** The on-screen key gt.Water.Stats draws this sheet's line on (one line per sheet, never scrolling). */
	int32 StatsKey = 0;
	/** How near a camera or pawn has to be for the once-a-second line, m. */
	static constexpr float StatsNearM = 100.f;

	/** R1: the landscapes the bed sampler reads, gathered once per BuildField (and ignored by its trace). */
	TArray<TWeakObjectPtr<ALandscapeProxy>> BedLandscapes;
	mutable int32 BedFromTraceCells = 0;
	mutable int32 BedTracedCells = 0;

	/** RIVERBED S3: the basin the water fills at its level (GTFORDFILL), filled at BuildField. */
	FGTWaterBasin Basin;
	void LogBasin() const;
	bool bBasinBox = false;
	bool bBasinCapped = false;
	float SinceFieldBuilt = 0.f;
	int32 SeamLogs = 0;

	/**
	 * RIVERBED S3: the static part of a capped still basin - the basin + margin past the simulated field, drawn as a
	 * second section of the surface mesh on the same lattice, in the same material with its own flat field texture
	 * (R the surface over the level: 0 on water, the bed on a dry cell; G the depth at the level; no flow), no solver.
	 * The car reads the level there. Re-uploaded when the level moves (W5's rise), the basin grown to it.
	 */
	bool bStaticPart = false;
	FVector2D StaticOriginCm = FVector2D::ZeroVector;
	int32 StaticNX = 0;
	int32 StaticNY = 0;
	TArray<float> StaticBedCm;
	TArray<uint8> StaticBasin;
	float StaticLevelCm = -1.e9f;
	int32 StaticQuads = 0;

	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> StaticTexture;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> StaticMaterial;

	/** Lays the static part over the lattice cells [LoX..HiX] x [LoY..HiY], leaving out the quads the field [SimLoX..SimHiX] x [SimLoY..SimHiY] draws. */
	void BuildStaticPart(int32 LoX, int32 HiX, int32 LoY, int32 HiY, int32 SimLoX, int32 SimHiX, int32 SimLoY, int32 SimHiY);
	void UploadStatic();
	/** True when a world XY lies in the static part's rectangle and outside the simulated field's. */
	bool InStaticPart(const FVector2D& WorldXY) const;
	bool InFieldRect(const FVector2D& WorldXY) const;
	/** The placed actor's (section + 24) x 30 m box (the footprint before S3). */
	bool InPlacedBox(const FVector2D& WorldXY) const;
	/** True when the cell or one of its eight neighbours is in the basin or holds water. */
	bool NearFieldWater(int32 Index) const;
	bool NearStaticBasin(const FVector2D& WorldXY) const;

	/** Samples the landscape, and R1's trace against static world geometry (a stone in the channel is bed), for the field's bed. */
	float BedZAt(const FVector2D& WorldXY) const;
	void BuildField();
	void BuildSurfaceMesh();
	void UploadField();
	/** R1: takes this tick's share out of the field's counters into both windows. */
	void AccumulateStats(float DeltaSeconds);
};
