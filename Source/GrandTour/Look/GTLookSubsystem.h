#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GTLookSubsystem.generated.h"

class AActor;
class APostProcessVolume;
class AStaticMeshActor;
class UDirectionalLightComponent;
class UMaterial;
class UMaterialInstanceDynamic;
class UMaterialInterface;

/**
 * One weather state's post-layer numbers (look stage L2, VEHICLE_BUILD_SYSTEM 56). Every number is PROPOSED and
 * UNMEASURED against the owner's look; the owner names them. X, the light amount the bands cut, is
 * luma(SceneColor) / PreExposure / luma(BaseColor) / (the sun's lux / pi): 1 is a surface square to the sun.
 */
USTRUCT(BlueprintType)
struct FGTLookSet
{
	GENERATED_BODY()

	/** 2 or 3 tones per surface: shadow + lit, or shadow + mid + lit. Lerped between sets, cut at 2.5. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	float Bands = 3.f;

	/** The shadow/lit (2 bands) or shadow/mid (3 bands) terminator, in X. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	float T1 = 0.2f;

	/** The mid/lit terminator (3 bands), in X. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	float T2 = 0.45f;

	/** The terminator's width in X (a smoothstep this wide across each cut). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	float Soft = 0.08f;

	/** The mid band's tint: lerp(ShadowTint, LitTint, MidMix). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	float MidMix = 0.6f;

	/** The power of the light variation kept inside a band: 0 flat bands; (X / the band's typical X) ^ InBand, 0.7-1.3. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	float InBand = 0.25f;

	/** Linear; the lit band is BaseColor x LitTint (its level too: the displayed lit side does not follow the exposure). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	FLinearColor LitTint = FLinearColor(1.f, 0.96f, 0.88f);

	/** Linear; the shadow band is BaseColor x ShadowTint. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	FLinearColor ShadowTint = FLinearColor(0.55f, 0.62f, 0.80f);

	/** Linear lifted blacks: Lift + (1 - Lift) x colour. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	FLinearColor Lift = FLinearColor(0.012f, 0.014f, 0.020f);

	/** The stroke-noise warp's amplitude, pixels at 1080p. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	float WarpPx = 1.5f;

	/** The fixed exposure (auto exposure clamped: min = max brightness, EV100). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Look")
	float EV100 = 0.25f;

	static FGTLookSet Lerp(const FGTLookSet& A, const FGTLookSet& B, float Alpha);
	FString Describe() const;
};

/**
 * Look stage L2 (docs/LOOK_PLAN.md, VEHICLE_BUILD_SYSTEM 56): the post-process lighting layer, put on every game
 * world at BeginPlay so no level is missed and no level asset changes. It spawns one transient unbound
 * APostProcessVolume carrying a dynamic instance of M_GT_PostLook (the band pass, Before DOF) and, while
 * gt.Look.Kuwahara is 1, one of M_GT_PostKuwahara after it; it clamps the exposure to the weather set's EV100,
 * turns bloom, lens flare, film grain, vignette and local exposure off, and sets every directional light's light
 * source angle to SunAngleDeg only in band-pass mode, restoring authored softness otherwise. Every tick
 * it blends the weather sets the way UGTWeatherSubsystem blends its states (the target state, its blend alpha with
 * the same smoothstep, then the storm pressure towards Storm) and pushes the numbers into the instance, with SunRef
 * from the sun's current intensity. Once a second it stencils the water sheets (1: AGTWaterSheet's primitives, the
 * mud patches' rut WaterMesh) and the dashboard (2: every primitive under UGTDashboardComponent) with custom
 * depth-stencil (r.CustomDepth=3); the band pass and the Kuwahara filter leave stencilled pixels alone.
 *
 * Console: gt.Look.Post 0 off / 1 band pass and hard sun / 2 fixed exposure without filters (default, authored sun softness);
 * gt.Look.Kuwahara 0/1; gt.Look.WarpScale (0 by default; 1 enables the authored stroke warp); gt.Look.Debug 0-6 (the material's debug
 * views; 4 leaves the exposure automatic, 6 the follow-up's flags).
 * Command line: -GTLook=N, -GTLookKuwahara=N, -GTLookWarp=F, -GTLookDebug=N set the same at start (the picture .bat files pass them).
 *
 * Look stage L6 (VEHICLE_BUILD_SYSTEM 57): gt.Look.Surface 1/0 (-GTLookSurface=N) switches the runtime painterly surface.
 * At BeginPlay and once a second every mesh slot whose base material is M_GT_Painterly gets a dynamic instance, and
 * its Surface scalar follows the cvar (M_GT_Painterly already holds two parameter collections, so not a collection).
 *
 * Look stage L3 (VEHICLE_BUILD_SYSTEM 58): the backdrop and the distance. At BeginPlay a transient sky dome - the engine's
 * sphere at SkyRadiusCm wearing a dynamic instance of MI_GT_Sky (unlit, translucent Before DOF, no fog), kept out of the
 * real-time sky capture, reflection captures, ray tracing, shadows, Lumen, distance fields and scene captures - spawned
 * once at the world origin and never moved (every leg's grid is 2 km, so it surrounds every camera; the gradient and the
 * clouds are on the view direction), with the weather's CloudCover, SkyScale and wind (the cloud drift) and the sun's
 * lux pushed in every tick.
 * gt.Look.Sky 1/0 (-GTLookSky=N) shows or hides it; gt.Look.Haze 1/0 (-GTLookHaze=N) sets M_GT_PostLook's Haze;
 * gt.Look.Foliage 1/0 (-GTLookFoliage=N) shows or hides every terrain dressing's Foliage cards; gt.Look.Weather <Id>
 * (-GTWeather=Id) holds a weather state, set instantly, for pictures and the owner's gate (empty: the weather's own).
 *
 * Leg dressing LD3 (docs/LEG_DRESSING_PLAN.md): gt.Look.Dressing 1/0 (-GTLookDressing=N) shows or hides the biome
 * dressing - every actor tagged OWBiome.* or GTBiome.* hidden with its collision off (each one's own state put back at
 * 1) - and sets grass.Enable to match. UGTVegetationSubsystem (LD5) reads the cvar itself.
 */
UCLASS()
class GRANDTOUR_API UGTLookSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UGTLookSubsystem, STATGROUP_Tickables); }

	/** The proposed set for a weather state id (Clear, Overcast, Rain, Storm, Snow; anything else gets Clear's). */
	static FGTLookSet DefaultSet(FName StateId);

	/** LD3: an actor gt.Look.Dressing switches (a tag starting OWBiome. or GTBiome.). */
	static bool IsBiomeDressing(const AActor* Actor);

	/** One line: mode, Kuwahara, debug, the target state, the blended set, the sun, the stencilled counts. */
	FString Describe() const;

	const FGTLookSet& GetCurrentSet() const { return Current; }

	// ---- numbers outside the weather sets (PROPOSED, UNMEASURED) --------------------------------------------------
	/** The sun's light source angle while the layer is on, degrees (the engine default is 0.5357). */
	float SunAngleDeg = 0.05f;
	float StrokeLenPx = 24.f;
	float StrokeWidthPx = 5.f;
	/** The X the bands are shown at (the lit band as bright as a surface at X = LitX under this sun); measured lit X 0.5-1. */
	float LitX = 0.75f;
	float BaseGuard = 0.02f;
	float SkyDepthCm = 5.0e6f;
	float KuwaharaRadiusPx = 4.f;
	float KuwaharaQ = 8.f;
	float KuwaharaAlpha = 1.f;
	float KuwaharaZeta = 0.33f;

	// ---- look stage L3 (VEHICLE_BUILD_SYSTEM 58), PROPOSED, UNMEASURED ---------------------------------------------
	/** The sky dome's radius, cm: the engine sphere (100 cm across) scaled to it, at the world origin, never moved. */
	float SkyRadiusCm = 1.0e6f;
	/** The clouds' drift along the weather's wind, direction units a second (a blob, 0.333 across, crosses in ~170 s). */
	float CloudDrift = 0.002f;
	/** The haze: none nearer than HazeStartCm, full at HazeEndCm (linear in depth). HazeEndCm 120000 and HazeMix 0.15 are the
	 * owner's first named set (2026-09-26; the first build 60000 and 0.35), pushed every frame over M_GT_PostLook's defaults. */
	float HazeStartCm = 6000.f;
	float HazeEndCm = 120000.f;
	/** At full haze the saturation is HazeSat of itself and HazeTint (lit at LitX) is mixed in to HazeMix. */
	float HazeSat = 0.5f;
	float HazeMix = 0.15f;
	FLinearColor HazeTint = FLinearColor(0.70f, 0.78f, 0.90f);

private:
	void EnsureVolume();
	void ApplyMode(int32 Mode, int32 Kuwahara, int32 Debug);
	void ApplyExposure(const FGTLookSet& Set, int32 Mode, int32 Debug);
	void PushSet(const FGTLookSet& Set, int32 Debug);
	void SetSunAngles(bool bHard);
	void TagExclusions();
	/** L6: a dynamic instance on every mesh slot wearing M_GT_Painterly that has none yet. */
	void WrapSurfaces();
	/** L6: gt.Look.Surface onto every wrapped slot. */
	void ApplySurface(int32 Surface);
	/** L3: the transient sky dome, once (hidden while gt.Look.Sky is 0). */
	void EnsureSky();
	/** L3: the weather and the sun into the dome's instance, its visibility from gt.Look.Sky. */
	void UpdateSky(float DeltaTime, int32 Sky);
	/** L3: gt.Look.Foliage onto every terrain dressing's Foliage component. */
	void ApplyFoliage(int32 Foliage);
	/** L3: gt.Look.Weather held (SetState, instant) while it names a state. */
	void HoldWeather();
	/** LD3: gt.Look.Dressing onto every biome dressing actor and grass.Enable. */
	void ApplyDressing(int32 Dressing);

	UPROPERTY(Transient)
	TObjectPtr<APostProcessVolume> Volume;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> LookMID;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> KuwaharaMID;

	TArray<TPair<TWeakObjectPtr<UDirectionalLightComponent>, float>> SunAngles;
	bool bSunHard = false;

	FGTLookSet Current;
	FGTLookSet BlendFrom;
	FGTLookSet BlendTo;
	FName TargetId;
	bool bBegun = false;
	int32 AppliedMode = -1;
	int32 AppliedKuwahara = -1;
	int32 AppliedDebug = -1;
	float TagTimer = 0.f;
	int32 StencilWater = 0;
	int32 StencilDash = 0;
	float LastSunLux = 0.f;

	// ---- look stage L6: the runtime painterly surface ------------------------------------------------------------
	UPROPERTY(Transient)
	TObjectPtr<UMaterial> PainterlyBase;

	bool bPainterlyTried = false;
	TArray<TWeakObjectPtr<UMaterialInstanceDynamic>> SurfaceMIDs;
	int32 AppliedSurface = -1;

	// ---- look stage L3: the sky, the haze, the foliage ------------------------------------------------------------
	UPROPERTY(Transient)
	TObjectPtr<AStaticMeshActor> SkyDome;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> SkyMID;

	TWeakObjectPtr<UDirectionalLightComponent> SkySun;
	bool bSkyTried = false;
	FVector CloudOffset = FVector::ZeroVector;
	float SkyCloudCover = 0.f;
	float SkySkyScale = 1.f;
	int32 AppliedSky = -1;
	int32 AppliedFoliage = -1;
	FString HeldWeather;

	// ---- leg dressing LD3: the biome dressing switch --------------------------------------------------------------
	int32 AppliedDressing = -1;
	/** Each actor gt.Look.Dressing 0 hid: its own hidden-in-game and collision flags, put back at 1. */
	TMap<TWeakObjectPtr<AActor>, TPair<bool, bool>> DressingSaved;
};
