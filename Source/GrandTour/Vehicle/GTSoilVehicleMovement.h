#pragma once
#include "CoreMinimal.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Terrain/GTMudContactModel.h"
#include "GTSoilVehicleMovement.generated.h"

/** Immutable game-thread snapshot around one tyre. No terrain UObject access on the physics thread. */
struct FGTSoilContact
{
    static constexpr int32 Side=9;
    static constexpr float Spacing=12.5f;
    bool bActive=false;
    FVector2D Centre=FVector2D::ZeroVector;
    TWeakObjectPtr<UPrimitiveComponent> Component;
    float Height[Side*Side]={};
    float Penetration=0, TotalSink=0, Softness=0, Grass=0, LoadCorrection=1;
    GTMudContact::FState SoilState;
    bool bRutInteraction=false;
    FVector2D Heading=FVector2D(1,0);
    float WidthCm=25;
    bool bNativeSubstance=false;
    bool bNativeWater=false;
    float NativeQ=0,NativeDepth=0,NativeWaterDepth=0,NativeMassPerWheel=500,NativeWheelMass=20;
    /** CL2: the native mud substance numbers for this ground (the substance struct's defaults unless clay) and the clay weight behind them. */
    float NativeFriction=2.2f,NativeLinearResistance=10.f,NativePushResistance=36.f,Clay=0.f;
    FVector NativeFlow=FVector::ZeroVector;
    bool Sample(FVector2D XY,float& OutHeight,FVector2D& OutSlope) const;
    /** Positive rise into the direction of motion, footprint-filtered; no force down a slope. */
    float EntryRise(FVector2D XY,FVector2D Direction,float ReachCm) const;
};

/** Sampled from the actual chassis box, not the cosmetic car bounds. */
struct FGTBodySoilContact
{
    FVector LocalPoint=FVector::ZeroVector;
    FVector2D SampleXY=FVector2D::ZeroVector;
    float Top=0,Support=0,Base=0,MassShare=0,YieldCm=10;
};

/** Landscape contact plus a bounded high-speed post-peak tyre response. */
UCLASS()
class GRANDTOUR_API UGTSoilVehicleMovement : public UChaosWheeledVehicleMovementComponent
{
    GENERATED_BODY()
public:
    /** Fraction of lost post-peak lateral force retained at speed. Low range is unchanged. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="GT|Handling", meta=(ClampMin="0",ClampMax="1"))
    float HighSpeedSlideRecovery=.75f;
    /** Softer high-speed firm-ground ride; original crawl suspension is restored by its gate. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="GT|Handling", meta=(ClampMin="0",ClampMax="0.35"))
    float RallySuspensionCompliance=.2f;
    void UpdateRallySuspension(float DeltaSeconds,float SurfaceWeight);
    UFUNCTION(BlueprintPure, Category="GT|Handling") float GetRallySuspensionWeight() const { return RallyRideWeight; }
    UFUNCTION(BlueprintPure, Category="GT|Workshop") int32 GetSuspensionKit() const { return AppliedSuspensionKit; }
    UFUNCTION(BlueprintPure, Category="GT|Workshop") FString SuspensionReport();
    virtual float GetSuspensionOffset(int WheelIndex) override;

    virtual TUniquePtr<Chaos::FSimpleWheeledVehicle> CreatePhysicsVehicle() override;
    void SetSoilContacts(const TArray<FGTSoilContact>& Contacts);
    /** Current suspension origin, independent of last frame's contact/animation. */
    FVector SoilQueryOrigin(int32 WheelIndex);
    /** UE 5.8 UChaosVehicleWheel::Location is not populated by the simulation. */
    UFUNCTION(BlueprintPure, Category="Soil") FVector SoilWheelCentre(int32 WheelIndex);
    /** Read-only fixture using the same collision channel/mask as suspension. */
    UFUNCTION(BlueprintPure, Category="Soil") bool ReviewSuspensionObstacle(AActor* Obstacle);
    UFUNCTION(BlueprintPure, Category="Soil")
    FString RutInteractionReport();
    UFUNCTION(BlueprintPure, Category="Soil") FString NativeSubstanceReport();
    UFUNCTION(BlueprintPure, Category="Soil") FString BodySoilReport();
    /** On-demand, physics-locked solver snapshot for handling QA; never changes forces. */
    UFUNCTION(BlueprintPure, Category="GT|Handling") FString RallyHandlingReport();
    /** Game-thread filter state, before the authored control curve. GetSteeringInput returns raw input. */
    float GetFilteredSteeringInput() const { return SteeringInput; }
private:
    TArray<FGTBodySoilContact> GatherBodySoil();
    float BodyContactCarry=0;
    float RallyRideWeight=0;
    float AppliedRideWeight=-1;
    int32 AppliedSuspensionKit=-1;
    TArray<float> KitWheelOffsets;
    TArray<uint64> KitWheelFrames;
};
