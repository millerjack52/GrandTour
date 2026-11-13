#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Weather/GTWeatherStateDefinition.h"
#include "GTWeatherSubsystem.generated.h"

class AGTRainEmitter;
class UDirectionalLightComponent;
class UExponentialHeightFogComponent;
class UMaterialParameterCollection;
class USkyLightComponent;

/**
 * The weather (ARCHITECTURE 6d). A state machine over UGTWeatherStateDefinition assets: SetState
 * blends from the current values to the new state's over its transition time; a weather front
 * layers its storm on top by pressure (0 far away .. 1 inside), reported every tick by the
 * fronts and gone when they stop reporting. From the blended values it simulates the two slow
 * quantities, ground wetness (rises with rain, dries with time and warmth) and snow cover (falls
 * below freezing, melts above), writes the lot into MPC_Weather every frame, scales the map's
 * sun, sky light and height fog, and drives the rain emitter (drops, ambience and the occlusion
 * capture). Wet traction, body wetness and exposure read GetWetness / GetRainIntensity /
 * GetTemperature; nothing else in the game touches the collection.
 *
 * Assets: DA_Weather_* under /Game/GrandTour/Weather (Art/setup_m3_weather.bat); FindState falls
 * back to the C++ defaults so a leg without assets still has weather. Starts Clear.
 */
UCLASS()
class GRANDTOUR_API UGTWeatherSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UGTWeatherSubsystem, STATGROUP_Tickables); }

	/** Blend to a state over its transition time (bInstant: snap). */
	UFUNCTION(BlueprintCallable, Category = "GT|Weather")
	void SetState(UGTWeatherStateDefinition* State, bool bInstant = false);

	/** The state asset by id (Clear, Overcast, Rain, Storm, Snow), loaded from the weather folder or built from the defaults. */
	UFUNCTION(BlueprintCallable, Category = "GT|Weather")
	UGTWeatherStateDefinition* FindState(FName StateId);

	/** A front reports how close its storm is every tick; the highest report wins this frame. */
	void ReportStormPressure(float Pressure, UGTWeatherStateDefinition* StormState);

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	const FGTWeatherValues& GetCurrent() const { return Current; }

	/**
	 * The rain everything that reads a number reads: the test hook first, then the cvar gt.Weather.Rain (water stage
	 * W5: 0..1 forces it, -1 hands it back to the simulation), then the state blend's own. It drives the NUMBERS only -
	 * the wetness the ground gains, the material collection, the rain emitter's drops and its ambience all go on
	 * reading Current, as they have since WS2's SetRainForTest - so the cvar raises a river without wetting the world.
	 */
	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	float GetRainIntensity() const { return RainForTest >= 0.f ? RainForTest : (CvarRainOverride >= 0.f ? CvarRainOverride : Current.RainIntensity); }

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	float GetTemperature() const { return Current.TemperatureC; }

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	float GetWetness() const { return Wetness; }

	/**
	 * Tests only (the mud plan's stage G picture, hide_21_rut_wet): put the ground wetness where the picture needs it.
	 * The simulation carries on from there - in dry weather it falls at DryRate, 1 % a second - and WriteCollection
	 * pushes it into MPC_Weather on the next tick, so everything that reads the collection or GetWetness follows.
	 * Setting the collection directly instead would be overwritten by that same write.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Testing", meta = (DevelopmentOnly))
	void SetWetnessForTest(float InWetness) { Wetness = FMath::Clamp(InWetness, 0.f, 1.f); }

	/**
	 * Tests only (water stage WS2: the rain that stirs a ford's surface, Art/water_test.bat step 9 and the picture
	 * hide_28_ford_rain). A negative number hands the reading back to the simulation. It overrides what
	 * GetRainIntensity and GetRainAt answer, and nothing else: the state blend, the wetness the ground gains, the
	 * material collection and the rain emitter all go on reading Current, so a test can rain on the water without
	 * soaking the world or putting drops in a picture.
	 */
	void SetRainForTest(float InIntensity) { RainForTest = InIntensity < 0.f ? -1.f : FMath::Clamp(InIntensity, 0.f, 1.f); }
	float GetRainForTest() const { return RainForTest; }

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	float GetSnowAmount() const { return SnowAmount; }

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	float GetStormPressure() const { return StormPressure; }

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	UGTWeatherStateDefinition* GetTargetState() const { return TargetState; }

	/** How far the blend to the target state has run, 0..1 before the smoothstep (look stage L2 follows it). */
	float GetBlendAlpha() const { return BlendAlpha; }

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	FString GetStateName() const;

	/** Wind as a drift velocity, cm/s. */
	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	FVector GetWindVector() const;

	/** Upward trace from a point: true when something blocks the sky within CoverTraceLength. */
	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	bool IsUnderCover(const FVector& WorldLocation) const;

	/** A character standing here in the rain (the on-foot exposure drain uses it). */
	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	float GetRainAt(const FVector& WorldLocation) const { return IsUnderCover(WorldLocation) ? 0.f : GetRainIntensity(); }

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	AGTRainEmitter* GetRainEmitter() const { return Emitter; }

	/** Reads a collection scalar back (tests). False when the collection or the name is missing. */
	bool ReadCollectionScalar(FName Name, float& OutValue) const;

	/** The Geiger click rate the ambience plays (the radiation zone sets it while the player is inside). */
	void SetClickRate(float ClicksPerSecond) { PendingClickRate = FMath::Max(PendingClickRate, ClicksPerSecond); }

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	FString Describe() const;

	// ---- simulation rates ----------------------------------------------------------------------
	/** Wetness gained per second at full rain (soaked in 5 s). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	float WetRate = 0.2f;

	/** Wetness lost per second in dry weather at 15 C; warmer dries faster. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	float DryRate = 0.01f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	float SnowRate = 0.05f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	float MeltRate = 0.02f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	float CoverTraceLength = 5000.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	FString CollectionPath = TEXT("/Game/GrandTour/Materials/MPC_Weather.MPC_Weather");

	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	FString StateFolder = TEXT("/Game/GrandTour/Weather");

	// ---- leg dressing LD3 (docs/LEG_DRESSING_PLAN.md): the OW foliage's wind ------------------------------------------
	/** The OW toolkit's wind collection (M_OWFoliageMaster, M_OWTrunkMaster), written every tick when it loads. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	FString GlobalWindPath = TEXT("/Game/Materials/MaterialParameterCollection/MPC_GlobalWind.MPC_GlobalWind");

	/**
	 * MPC_GlobalWind's WindIntensity per unit of WindStrength. Calibrated 2026-09-27 so Clear gives the collection's own
	 * default: Clear's WindStrength 0.1 -> WindIntensity 0.5 (the default, read headless), so 5.0; Overcast 0.3 -> 1.5,
	 * Rain 0.5 -> 2.5, Snow 0.4 -> 2.0, Storm 1.0 -> 5.0 (ten times the default). A dial: the owner judges the storm's sway.
	 */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	float GlobalWindIntensityPerStrength = 5.f;

	static const FName GlobalWindParamIntensity;
	static const FName GlobalWindParamDirection;

	/** LD3 (tests): MPC_GlobalWind's value of a scalar in this world, and its default when OutDefault is given. False when the collection is missing. */
	bool ReadGlobalWindScalar(FName Name, float& OutValue, float* OutDefault = nullptr) const;

	bool HasGlobalWind() const { return GlobalWind != nullptr; }

	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	int32 StatesFromAssets = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	int32 Transitions = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Weather")
	bool bCollectionFound = false;

private:
	void FindSceneActors();
	void WriteCollection();
	/** LD3: MPC_GlobalWind from the current wind (nothing when the collection did not load). */
	void WriteGlobalWind();
	void ApplyToScene();
	void EnsureEmitter();

	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> Collection;

	/** LD3: MPC_GlobalWind, or null when it did not load. */
	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> GlobalWind;

	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UGTWeatherStateDefinition>> States;

	UPROPERTY(Transient)
	TObjectPtr<UGTWeatherStateDefinition> TargetState;

	UPROPERTY(Transient)
	TObjectPtr<UGTWeatherStateDefinition> StormState;

	UPROPERTY(Transient)
	TObjectPtr<AGTRainEmitter> Emitter;

	TWeakObjectPtr<UDirectionalLightComponent> Sun;
	TWeakObjectPtr<USkyLightComponent> Sky;
	TWeakObjectPtr<UExponentialHeightFogComponent> Fog;
	float SunBaseIntensity = 0.f;
	float SkyBaseIntensity = 0.f;
	bool bSceneSearched = false;

	FGTWeatherValues BlendFrom;
	FGTWeatherValues BlendTo;
	FGTWeatherValues Base;       // the state blend alone
	FGTWeatherValues Current;    // with the storm pressure on top
	float BlendAlpha = 1.f;
	float BlendSeconds = 1.f;
	float StormPressure = 0.f;
	float PendingStormPressure = 0.f;
	float PendingClickRate = 0.f;
	float ClickRate = 0.f;
	float Wetness = 0.f;
	float SnowAmount = 0.f;
	/** WS2's test hook: -1 when the simulation's own rain is what everything reads. */
	float RainForTest = -1.f;
	/** W5: gt.Weather.Rain as read on the game thread once a tick (-1 = no override), so GetRainIntensity stays cheap. */
	float CvarRainOverride = -1.f;
	TSet<FName> ScalarNames;
	TSet<FName> VectorNames;
};
