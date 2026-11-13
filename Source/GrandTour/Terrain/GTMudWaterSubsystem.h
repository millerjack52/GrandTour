// Mud and water MW1 (docs/MUD_WATER_SURFACE_PLAN.md): the switches for the crisp deformed mud and the moving rut water
// (MPC_TrackPaint MudDeformDetail / MudWaterMotion, Art/Unreal/live_mud_style.py reads them), and the water rings
// (NS_GT_WaterRings, Art/Unreal/setup_mud_water.py): flat painted rings on the rut water where a wheel moves through it and at
// each on-foot footstep in it.
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GTMudWaterSubsystem.generated.h"

class UMaterialParameterCollection;
class UNiagaraComponent;
class UNiagaraSystem;

UCLASS()
class GRANDTOUR_API UGTMudWaterSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UGTMudWaterSubsystem, STATGROUP_Tickables); }

	/** gt.Mud.DeformDetail, gt.Mud.WaterMotion and gt.Mud.WaterRings (each 0/1, default 1). */
	static bool IsDeformDetailEnabled();
	static bool IsWaterMotionEnabled();
	static bool IsWaterRingsEnabled();

	/** Rings a second for one wheel in rut water at this ground speed (cm/s): none under RingMinSpeedCm, 1 there rising
	 *  linearly to 6 at RingFullSpeedCm and held. */
	static float WheelRingRate(float SpeedCmS);
	/** Whole rings this frame for a rate (rings/s), the fraction carried in Carry. */
	static int32 RingsThisFrame(float& Carry, float RatePerS, float DeltaSeconds);
	/** Footstep rings this frame: one every StepS while moving in water, the first as the foot meets the water (Clock primed),
	 *  Clock reset when out of it. */
	static int32 StepsThisFrame(float& Clock, bool bMovingInWater, float DeltaSeconds, float StepS);

	/** Rings emitted since the world began: by the wheels (bFeet false) or the footsteps. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Water")
	int32 GetRingsEmitted(bool bFeet) const { return bFeet ? FeetRings : WheelRings; }
	/** The rings alive now over every source's Niagara component (0 with no system). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Water")
	int32 GetRingLiveParticles() const;
	/** The rut water's surface at a world XY: Z (cm) and the depth there (cm, 0 where there is none; Z is then the mud's rest). */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Water")
	float WaterSurfaceZAt(FVector2D XYCm, float& OutDepthCm) const;
	/** The checks' readout: what the last ticks saw (cars, wheels in contact / in rut water / deep enough, the fastest car, the
	 *  walker's water and motion) and whether the ring system loaded. */
	UFUNCTION(BlueprintPure, Category = "GT|Mud|Water")
	FString DescribeRings() const;
	/** Tests and checks: Count rings at a world location now (through a test source). */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|Water")
	void EmitRingsForTest(FVector WorldLocation, int32 Count);

	/** The tunables (proposed; the owner names them). */
	static constexpr float RingMinSpeedCm = 30.f;      // a wheel creeping slower than this leaves no rings
	static constexpr float RingFullSpeedCm = 700.f;    // about 25 km/h: 6 rings a second
	static constexpr float RingMinDepthCm = 1.f;       // the water at the contact over this
	static constexpr float StepSeconds = 0.45f;        // the on-foot cadence (the character has no step event)
	static constexpr float StepMinSpeedCm = 20.f;      // the head bob's own "moving" threshold
	static constexpr float RingLiftCm = 0.6f;          // the sprites just over the water surface

private:
	struct FSource
	{
		TWeakObjectPtr<UNiagaraComponent> Component;
		float Carry = 0.f;
		float Clock = StepSeconds;   // primed: a walker's first step in the water rings at once
		float Side = 1.f;
		double LastEmit = -1e9;
		double LastTouch = 0.0;      // the last tick this source was fed or in the water (it is forgotten ForgetSeconds after)
		float WrittenRate = 0.f;
	};

	void WriteSwitches();
	void UpdateRings(float DeltaSeconds);
	FSource& Source(uint64 Key);
	void Emit(FSource& S, const FVector& Location, int32 Count, float DeltaSeconds);
	void Quiet(FSource& S, float DeltaSeconds);

	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> ParameterCollection;
	UPROPERTY(Transient)
	TObjectPtr<UNiagaraSystem> RingSystem;
	/** Every source's component (kept alive here; the map below points into it). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UNiagaraComponent>> Components;

	TMap<uint64, FSource> Sources;
	int32 WrittenDeformDetail = -1;
	int32 WrittenWaterMotion = -1;
	int32 WrittenOldTread = -1;   // MRD1: gt.Mud.OldTread as last written (MPC_TrackPaint MudOldTread)
	int32 WheelRings = 0;
	int32 FeetRings = 0;
	bool bRingSystemLooked = false;
	/** DescribeRings' counts (ticks since the world began; wheel-ticks seen in contact, in rut water, over the depth; the fastest car). */
	int32 DiagTicks = 0;
	int32 DiagWheelTicks = 0;
	int32 DiagContact = 0;
	int32 DiagRut = 0;
	int32 DiagDeep = 0;
	int32 DiagMoving = 0;
	float DiagMaxSpeed = 0.f;
	int32 DiagWalkerTicks = 0;
	int32 DiagWalkerWet = 0;
	int32 DiagWalkerMoving = 0;
	float DiagWalkerMaxDepth = 0.f;
};
