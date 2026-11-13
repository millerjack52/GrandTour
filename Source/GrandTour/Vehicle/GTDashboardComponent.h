#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "GTDashboardComponent.generated.h"

class UChaosWheeledVehicleMovementComponent;
class UGTConditionComponent;
class UGTEnvironmentComponent;
class UGTTractionComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * The instrument cluster (ARCHITECTURE 6, 6c): needles for speed, rpm, fuel and coolant
 * temperature, warning lights for engine, coolant, fuel, bogged, suspension, filter (dust), cold
 * and radiation, driven every tick from the vehicle, condition, traction and environment
 * components. No screen-space HUD: everything is a mesh in the cabin.
 *
 * Until the real interior exists it also builds a greybox dash from engine primitives: a dash
 * slab, three dials with needles, a row of warning lights and a steering wheel that turns with
 * the input. All of it is transient (never saved into a level) and collision-free. Place this
 * component where the cluster should sit; its local Z points at the driver and local X is "up"
 * on the dial faces.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTDashboardComponent : public USceneComponent
{
	GENERATED_BODY()

public:
	UGTDashboardComponent();

	virtual void OnRegister() override;

	void UpdateFromVehicle(float DeltaSeconds, const UChaosWheeledVehicleMovementComponent& Movement,
	                       const UGTConditionComponent& Condition, const UGTTractionComponent& Traction,
	                       const UGTEnvironmentComponent* Environment = nullptr, bool bRadiation = false,
	                       float EngineRpm = 0.f, bool bDiffLock = false, bool bLowRange = false);

	/** One line: needle angles and lit lights, for logs and tests. */
	UFUNCTION(BlueprintPure, Category = "GT|Dashboard")
	FString Describe() const;

	/** Which greybox parts sit between EyeLocation and each dial, by bounding box. Empty means all three dials are clear. */
	UFUNCTION(BlueprintPure, Category = "GT|Dashboard")
	FString CheckDialVisibility(const FVector& EyeLocation) const;

	// ---- gauge ranges ------------------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "GT|Dashboard")
	float SpeedoMaxKph = 160.f;

	UPROPERTY(EditAnywhere, Category = "GT|Dashboard")
	float TachoMaxRpm = 6000.f;

	/** Total sweep of the two big dials, centred on "up". */
	UPROPERTY(EditAnywhere, Category = "GT|Dashboard")
	float NeedleSweepDegrees = 240.f;

	UPROPERTY(EditAnywhere, Category = "GT|Dashboard")
	float FuelSweepDegrees = 90.f;

	/** Needle inertia: higher snaps faster. */
	UPROPERTY(EditAnywhere, Category = "GT|Dashboard")
	float NeedleLagSpeed = 8.f;

	UPROPERTY(EditAnywhere, Category = "GT|Dashboard", meta = (ClampMin = 0, ClampMax = 1))
	float LowFuelFraction = 0.15f;

	/** A part below this health lights its warning. */
	UPROPERTY(EditAnywhere, Category = "GT|Dashboard", meta = (ClampMin = 0, ClampMax = 1))
	float WarningHealth = 0.5f;

	/** Steering wheel rotation at full lock, degrees. */
	UPROPERTY(EditAnywhere, Category = "GT|Dashboard")
	float SteeringWheelDegrees = 150.f;

	// ---- greybox build -------------------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "GT|Dashboard|Greybox")
	bool bBuildGreybox = true;

	/** Dash slab centre and size in the parent (car mesh) frame, cm; hugs the blockout's dash wall at X = 80. */
	UPROPERTY(EditAnywhere, Category = "GT|Dashboard|Greybox")
	FVector DashSlabCentre = FVector(75.f, 0.f, 103.f);

	UPROPERTY(EditAnywhere, Category = "GT|Dashboard|Greybox")
	FVector DashSlabSize = FVector(10.f, 170.f, 24.f);

	/** Binnacle hood behind the cluster, parent frame, cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Dashboard|Greybox")
	FVector BinnacleCentre = FVector(70.f, -40.f, 119.f);

	UPROPERTY(EditAnywhere, Category = "GT|Dashboard|Greybox")
	FVector BinnacleSize = FVector(16.f, 32.f, 18.f);

	/** Steering wheel hub in the parent frame, cm; the wheel faces the driver and the dials sit above its rim. */
	UPROPERTY(EditAnywhere, Category = "GT|Dashboard|Greybox")
	FVector SteeringWheelCentre = FVector(46.f, -40.f, 96.f);

	UPROPERTY(EditAnywhere, Category = "GT|Dashboard|Greybox")
	float SteeringWheelPitch = 70.f;

	UPROPERTY(EditAnywhere, Category = "GT|Dashboard|Greybox")
	float SteeringWheelDiameter = 38.f;

	// ---- state ---------------------------------------------------------------------------------
	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	float SpeedNeedleDegrees = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	float RpmNeedleDegrees = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	float FuelNeedleDegrees = 0.f;

	/** Coolant temperature from the environment's heat model, same sweep as the fuel dial. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	float TempNeedleDegrees = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	float SteeringWheelAngle = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bEngineLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bCoolantLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bFuelLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bBoggedLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bSuspensionLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bFilterLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bColdLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bRadiationLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bLockLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	bool bLowLight = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Dashboard")
	int32 GreyboxPartCount = 0;

private:
	enum class ELight : uint8 { Engine, Coolant, Fuel, Bogged, Suspension, Filter, Cold, Radiation, Lock, Low, Count };

	void BuildGreybox();
	UStaticMeshComponent* MakeMesh(const FString& Name, UStaticMesh* Mesh, USceneComponent* Parent, const FVector& Location,
	                               const FRotator& Rotation, const FVector& Scale, UMaterialInterface* Material);
	UMaterialInstanceDynamic* MakeMaterial(const FLinearColor& BaseColor, float Roughness, const FLinearColor& Emissive, float Strength);
	USceneComponent* MakeDial(const FString& Name, const FVector& LocalPosition, float Diameter);
	void SetLight(ELight Light, bool bOn);

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CylinderMesh;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CubeMesh;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> PropMaterial;

	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> SpeedNeedle;

	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> RpmNeedle;

	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> FuelNeedle;

	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> TempNeedle;

	/** Tilted wheel axis; its child SteeringWheelSpinner yaws about that axis. */
	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> SteeringWheel;

	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> SteeringWheelSpinner;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> LightMaterials;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> OwnedMaterials;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> GreyboxMeshes;

	TArray<bool> LightStates;
	float TargetSpeedDegrees = 0.f;
	float TargetRpmDegrees = 0.f;
	float TargetFuelDegrees = 0.f;
	float TargetTempDegrees = 0.f;
	bool bBuilt = false;
	int32 NameCounter = 0;
};
