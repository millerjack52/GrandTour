#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTProceduralGround.h"
#include "GTLidarAuthoringPath.generated.h"

class USplineComponent;

UENUM(BlueprintType)
enum class EGTLidarPathKind : uint8 { MudTrack, RiverBed };

/** Saved design controls, never runtime geometry. Export through Tools > LiDAR Place. */
UCLASS()
class GRANDTOUREDITOR_API AGTLidarAuthoringPath : public AActor
{
    GENERATED_BODY()
public:
    AGTLidarAuthoringPath();
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="LiDAR") TObjectPtr<USplineComponent> ControlPoints;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR") EGTLidarPathKind Kind=EGTLidarPathKind::MudTrack;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR") FString DesignName="Logging site mud track";
    UPROPERTY(EditAnywhere,BlueprintReadWrite,AdvancedDisplay,Category="LiDAR") FString DesignId;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR") bool bEnabled=true;
    /** Full track or flat channel-bed width. Two metre shoulders on tracks. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR",meta=(ClampMin="2",ClampMax="20",Units="m")) float WidthMetres=3;
    /** River bed blends to the existing bed across this distance outside the flat bottom. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR|River bed",meta=(ClampMin="1",ClampMax="20",Units="m")) float BankBlendMetres=5;
    /** Used by 'Fit selected bed to depth'. Afterwards point Z is the actual bed elevation. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR|River bed",meta=(ClampMin="0.1",ClampMax="1.5",Units="m")) float TargetDepthMetres=.35f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR",meta=(ClampMin="0.1",ClampMax="3",Units="m")) float MaximumCutFillMetres=1;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR|Mud",meta=(ClampMin="1",ClampMax="40",Units="cm")) float MudDepthCm=18;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR|Mud",meta=(ClampMin="0",ClampMax="20",Units="cm")) float RutDepthCm=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR|Mud",meta=(ClampMin="0",ClampMax="1")) float Firmness=.45f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR|Mud",meta=(ClampMin="0",ClampMax="1")) float Wetness=.65f;
    /** Existing study conditions: local stretches, independent soil and authored relief. Empty means no extra old ruts. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR|Mud") TArray<FGTRoadCondition> Conditions;
    /** Recovered dirt-path solid relief. Independent of soil depth and live wheel deformation. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR|Mud",meta=(ClampMin="0",ClampMax="2")) float ReliefStrength=0;
};
