#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GTTrackPaintSubsystem.generated.h"

class UMaterialParameterCollection;
class UTexture2D;
class UTextureRenderTarget2D;

/**
 * Tyre tracks (ARCHITECTURE 6a). One world-aligned render target follows the player's car; every
 * sinking wheel stamps a soft streak into it each tick, and the environment master samples it
 * through MF_TrackPaint for a rut normal and displacement. The contents scroll by whole texels
 * when the focus moves more than RecentreDistance from the centre, so tracks behind you survive
 * until they leave the window, and fade with a multiplicative decay pass every DecayInterval.
 *
 * A coarse CPU grid (GridSize cells over the same window) mirrors every stamp and decay, so
 * gameplay and the headless tests can ask how deep the ruts are at a point without the GPU.
 * Under -NullRHI only the grid runs; the render target is untouched.
 *
 * Assets from Art/setup_m1_trackpaint.bat: RT_TrackPaint (what the material samples, R = depth)
 * and MPC_TrackPaint (TrackOrigin = centre x, y, window size cm, resolution; TrackDepthCm). If
 * they are missing the subsystem draws into a transient target and the material shows nothing.
 *
 * MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md, "mud leaves the bog"): the target stays RGBA16f with R the ruts exactly as
 * before (a rut stamp now adds to R alone: until MR1 G and B carried copies of it that nothing read). G is mud coverage and
 * B its wetness. Wheels carrying mud out of a patch (FGTWheelTraction::MudLoad) lay clumpy blots from the splat atlas
 * (Art/Blender/build_mud_splats.py; GTMudBlots.inl is its mask at 32 x 32 a tile) through AddCarriedMud, and thrown mud
 * landing on the landscape lays one through AddSplat. A blot sets G toward its coverage and B toward 1 under its mask (a
 * modulate pass by 1 - mask, then an additive pass), so neither passes 1. Each channel scrolls with the window and fades on
 * its own clock: R over FadeSeconds as before, G over MudFadeSeconds, B over MudDrySeconds. A second CPU grid (MudGridSize
 * cells, 25 cm) mirrors G and B for the tests. MF_MudCover (Art/Unreal/mud_cover.py) reads them in the ground materials;
 * MPC_TrackPaint's MudCover and GrassMud scalars carry the switches gt.Mud.Carry, gt.Mud.Splats and gt.Mud.GrassMud.
 */

/**
 * MR1: one wheel's carried-mud stroke (the car keeps one per wheel): the ground left to its next blot and its own random stream.
 * MR2 housekeeping 1: the ground the stroke has covered (DistanceCm) and its noise key (0: taken from Seed at the first blot),
 * so the strength along the track follows one 1-3 m noise per wheel.
 */
struct FGTMudCarryState
{
	float ToNextCm = 0.f;
	int32 Seed = 0;
	float DistanceCm = 0.f;
	uint32 NoiseKey = 0;
};

UCLASS()
class GRANDTOUR_API UGTTrackPaintSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UGTTrackPaintSubsystem, STATGROUP_Tickables); }

	/** Where the window should be centred; the player's car calls this every tick. */
	void SetFocus(const FVector& WorldLocation);

	/**
	 * A wheel WidthCm wide moved from Start to End this tick while sinking. Strength (0..1) is its
	 * sinkage fraction times the surface's track depth. A moving wheel deposits Strength once on
	 * every point it passes; a stationary one keeps digging at StationaryDigRate x Strength per second.
	 */
	void AddWheelStamp(const FVector& Start, const FVector& End, float WidthCm, float Strength, float DeltaSeconds);

	/** Rut depth at a world point from the CPU grid, 0 outside the window. The material saturates it at 1. */
	UFUNCTION(BlueprintPure, Category = "GT|TrackPaint")
	float SampleDepth(const FVector& WorldLocation) const;

	UFUNCTION(BlueprintPure, Category = "GT|TrackPaint")
	float GetMaxDepth() const;

	/** Reads the render target's red channel at a world point. False when there is no GPU to read (NullRHI). */
	bool ReadRenderTargetDepth(const FVector& WorldLocation, float& OutDepth) const;

	// ---- MudRunner MR1: carried mud and splats (G coverage, B wetness) ------------------------------------------------
	/**
	 * A wheel carrying MudLoad (0..1) rolled from Start to End outside every patch. Stamps by distance (MR2 housekeeping 1, so the
	 * frame rate never shows): a blot every CarrySpacingMin..Max x the smallest blot's reach at this load (so neighbours always
	 * overlap: spacing at most 0.6 of any blot's radius), each CarrySizeMin..Max widths across scaled by 0.55 + 0.45 load, turned
	 * at random, a random tile, jittered CarryJitter widths across the tyre. The strength along the track follows the stroke's own
	 * noise (two hashed octaves at CarryNoiseLongCm and CarryNoiseShortCm, about 1-3 m features): a soft threshold that rises from
	 * CarryGapAtFull at a full load to CarryGapAtEmpty as the load runs out, so the trail breaks into smears and gaps, more gaps as
	 * it thins; under the threshold no blot is laid. G toward CarryCoverage x MudLoad x that strength, B toward 1. Nothing at or
	 * under MinCarryLoad, nothing while gt.Mud.Carry is 0; a standing wheel lays nothing.
	 */
	void AddCarriedMud(FGTMudCarryState& State, const FVector& Start, const FVector& End, float WidthCm, float MudLoad);

	/** Thrown mud came down on the ground at Point: a random atlas blot reaching RadiusCm from it, G toward SplatCoverage, B toward 1. */
	void AddSplat(const FVector& Point, float RadiusCm, int32 Seed);

	/** Mud coverage (G) at a world point from the mud grid, 0 outside the window. */
	UFUNCTION(BlueprintPure, Category = "GT|TrackPaint|Mud")
	float SampleCoverage(const FVector& WorldLocation) const;

	/** Its wetness (B): 1 fresh, falling over MudDrySeconds. */
	UFUNCTION(BlueprintPure, Category = "GT|TrackPaint|Mud")
	float SampleWetness(const FVector& WorldLocation) const;

	/** MR1, the check's mirror test: the render target's G (coverage) and B (wetness) at a world point; (-1, -1) with no GPU (NullRHI). */
	UFUNCTION(BlueprintCallable, Category = "GT|TrackPaint|Mud")
	FVector2D ReadRenderTargetMud(const FVector& WorldLocation) const;

	UFUNCTION(BlueprintPure, Category = "GT|TrackPaint|Mud")
	int32 GetCarriedBlotCount() const { return CarriedBlotCount; }

	/** MR2 housekeeping 1: the blot places the noise left empty (a gap in the track), and the ground the carried strokes covered, cm. */
	UFUNCTION(BlueprintPure, Category = "GT|TrackPaint|Mud")
	int32 GetCarriedGapCount() const { return CarriedGapCount; }

	/** MR2 housekeeping 1: the carried strength (0..1) at DistanceCm along a stroke with NoiseKey, at MudLoad (the tests' and the check's readout). */
	float CarryStrengthAt(float DistanceCm, uint32 NoiseKey, float MudLoad) const;

	UFUNCTION(BlueprintPure, Category = "GT|TrackPaint|Mud")
	int32 GetSplatCount() const { return SplatCount; }

	/** gt.Mud.Carry, gt.Mud.Splats, gt.Mud.GrassMud (each 1 by default). */
	static bool IsCarryEnabled();
	static bool IsSplatsEnabled();
	static bool IsGrassMudEnabled();
	/** MRP: gt.Mud.PBR (0/1), gt.Mud.POM (0/1/2) and gt.Mud.POMShadow (0/1) as WriteSwitches puts them into MPC_TrackPaint. */
	static int32 GetMudPBR();
	static int32 GetMudPOM();
	static int32 GetMudPOMShadow();
	/** Deformable gravel DG1: gt.Gravel.POM (0/1/2) as WriteSwitches puts it into MPC_TrackPaint (GravelPOM). */
	static int32 GetGravelPOM();

	/** The atlas tile's mask (GTMudBlots.inl) at U, V (0..1 across the tile, V down the PNG), bilinear, 0..1. */
	static float SampleBlotMask(int32 Tile, float U, float V);

	UFUNCTION(BlueprintPure, Category = "GT|TrackPaint")
	FVector2D GetOrigin() const { return Origin; }

	/** Side of the square window in cm. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	float WindowSizeCm = 12800.f;

	/** Render target size; taken from the RT_TrackPaint asset when it exists. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	int32 Resolution = 2048;

	/** CPU grid cells per side; the window is snapped to whole cells so texels and cells move together. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	int32 GridSize = 256;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	float RecentreDistance = 2000.f;

	/** Time constant of the fade: a rut is at 37 % after this many seconds. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	float FadeSeconds = 120.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	float DecayInterval = 0.5f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	float StationaryDigRate = 0.5f;

	/** Full rut depth in cm, sent to the material through MPC_TrackPaint. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	float TrackDepthCm = 12.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	int32 StampCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	int32 RecentreCount = 0;

	/** False under -NullRHI: the grid runs, the render target does not. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint")
	bool bGpuEnabled = false;

	/** MR1: the G/B mirror's cells per side (25 cm at 512); a multiple of GridSize, so both shift by whole cells. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	int32 MudGridSize = 512;

	/** MR1: G's fade time constant (37 % left after it), s. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float MudFadeSeconds = 600.f;

	/** MR1: B's drying time constant, s. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float MudDrySeconds = 90.f;

	/** MR1: how often G, then B, are multiplied down, s (long enough that each step is several half-float steps on the GPU). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CoverDecayInterval = 4.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float WetDecayInterval = 1.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float MinCarryLoad = 0.02f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarryCoverage = 0.8f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float SplatCoverage = 0.9f;

	/** MR2 housekeeping 1: the spacing between carried blots, x the smallest blot's reach at the load (was 0.45-1.0 tyre widths x 1/sqrt(load)). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarrySpacingMin = 0.3f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarrySpacingMax = 0.6f;

	/** MR2 housekeeping 1: the strength noise's two octaves along the track, cm (features of about 1-3 m). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarryNoiseLongCm = 230.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarryNoiseShortCm = 110.f;

	/** MR2 housekeeping 1: the noise's gap threshold at a full load and as the load runs out, and its soft width (proposed). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarryGapAtFull = 0.15f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarryGapAtEmpty = 0.5f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarryGapSoft = 0.15f;

	/** The drawn square, x the tyre's width (the atlas blots fill about half their square: at 1.1-1.9 the tracks read as thin dotted lines, 2026-10-08). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarrySizeMin = 1.8f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarrySizeMax = 2.8f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|TrackPaint|Mud")
	float CarryJitter = 0.3f;

private:
	/** MR1: one atlas blot into G and B. */
	struct FBlot
	{
		FVector2D Centre;
		float HalfCm;      // the drawn square's half side (the blot reaches GTMudBlots::Window of it)
		float AngleDeg;
		int32 Tile;
		float Coverage;
		float Wet;
	};

	struct FStamp
	{
		FVector2D Start;
		FVector2D End;
		float Width;
		float Amount;
	};

	void Recentre(const FVector2D& NewOrigin);
	void FlushStamps();
	void FlushBlots();
	void Decay(float FactorR, float FactorG, float FactorB);
	void WriteCollection() const;
	void WriteSwitches();
	/** Benmore integration B1: gt.Ground.Detail into MPC_GT_GroundDetail (MF_GT_GroundDetail); gt.Ground.Scatter x gt.Ground.ScatterDensity
	 *  onto the scatter grass types' densities, the landscape grass instances flushed on a change (the grass maps stay). */
	void WriteGroundDetail();
	void ApplyScatterDensity(float Scale);
	FVector2D SnapToCell(const FVector2D& World) const;
	FVector2D WorldToPixel(const FVector2D& World) const;
	void StampGrid(const FStamp& Stamp);
	void StampBlotGrid(const FBlot& Blot);
	int32 MudCellAt(const FVector& WorldLocation) const;
	UTexture2D* MakeBrush(bool bSoft) const;
	UTexture2D* MakeBlotBrush(bool bMultiply) const;

	UPROPERTY(Transient)
	TObjectPtr<UTextureRenderTarget2D> RenderTarget;

	UPROPERTY(Transient)
	TObjectPtr<UTextureRenderTarget2D> ScratchTarget;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> ParameterCollection;

	/** Benmore integration B1: MPC_GT_GroundDetail (MF_GT_GroundDetail's parameters and GroundDetail); null where absent. */
	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> GroundDetailCollection;

	/** Benmore integration B1: the scatter grass types (LGT_GT_SoilScatter, LGT_GT_GrassLitter) and their varieties' authored densities,
	 *  scaled by gt.Ground.Scatter x gt.Ground.ScatterDensity and restored on Deinitialize. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<class ULandscapeGrassType>> ScatterGrassTypes;
	TArray<float> ScatterAuthoredDensity;

	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> BrushTexture;

	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> WhiteTexture;

	/** MR1: the blot brushes, the atlas mask at 32 px a tile: G, B = 1 - mask (R, A = 1) for the modulate pass; G, B = mask (R = 0) for the additive one. */
	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> BlotMulTexture;

	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> BlotAddTexture;

	TArray<FStamp> Pending;
	TArray<float> Cells;
	FVector2D Origin = FVector2D::ZeroVector;
	FVector2D Focus = FVector2D::ZeroVector;
	bool bHaveFocus = false;
	float DecayTimer = 0.f;

	// MR1
	TArray<FBlot> PendingBlots;
	TArray<float> CoverCells;
	TArray<float> WetCells;
	float CoverTimer = 0.f;
	float WetTimer = 0.f;
	int32 MudStampCount = 0;
	int32 CarriedBlotCount = 0;
	int32 CarriedGapCount = 0;
	int32 SplatCount = 0;
	int32 WrittenCover = -1;
	int32 WrittenGrass = -1;
	int32 WrittenPBR = -1;
	int32 WrittenPOM = -1;
	int32 WrittenPOMShadow = -1;
	int32 WrittenGravelPOM = -1;   // Deformable gravel DG1
	int32 WrittenGravelDebug = -1;
	int32 WrittenGroundDetail = -1;   // Ground relief GR2
	int32 WrittenGroundDetailB1 = -1;   // Benmore integration B1: MPC_GT_GroundDetail's GroundDetail
	float WrittenScatterScale = -1.f;   // and the scatter grass types' density scale (gt.Ground.Scatter x gt.Ground.ScatterDensity)
};
