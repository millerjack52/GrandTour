#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameFramework/Actor.h"
#include "GTDistanceStyle.generated.h"

class UMaterialParameterCollection;
class ADirectionalLight;
class ACameraActor;
class UStaticMesh;
class UHierarchicalInstancedStaticMeshComponent;

/** Sparse, grounded stand-in vegetation for the gap between ground detail and canopy. */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTForestInteriorData : public UDataAsset
{
 GENERATED_BODY()
public:
 UPROPERTY(EditAnywhere) TObjectPtr<UStaticMesh> Mesh;
 UPROPERTY(EditAnywhere) TArray<FTransform> Placements;
};

/** Map-owned art direction. Values are applied to a world instance, never shared material defaults. */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTDistanceStyleProfile : public UDataAsset
{
 GENERATED_BODY()
public:
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Style", meta=(ClampMin="0",ClampMax="1")) float Strength=.7f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Style", meta=(ClampMin="0",Units="m")) float StartMetres=180.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Style", meta=(ClampMin="1",Units="m")) float FullMetres=850.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Style", meta=(ClampMin="0",ClampMax="1")) float NormalSimplification=.95f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette") FLinearColor ForestColour=FLinearColor(.11f,.23f,.155f);
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette") FLinearColor ShadowColour=FLinearColor(.055f,.11f,.095f);
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette") FLinearColor GroundTint=FLinearColor(.88f,1.03f,.94f);
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette", meta=(ClampMin="0",ClampMax=".5")) float PatchVariation=.10f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette", meta=(ClampMin="5",Units="m")) float PatchSizeMetres=90.f;
 /** Zero preserves the original distance-only presets. */
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Art Direction", meta=(ClampMin="0",ClampMax="1")) float PaletteStrength=0.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Art Direction", meta=(ClampMin="0",Units="m")) float PaletteStartMetres=40.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Art Direction", meta=(ClampMin="1",Units="m")) float PaletteFullMetres=220.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Art Direction", meta=(ClampMin="0",ClampMax="1")) float CrownDefinition=.7f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Art Direction") FLinearColor SunlitColour=FLinearColor(.085f,.13f,.045f);
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Art Direction") FLinearColor ClearingColour=FLinearColor(.12f,.145f,.055f);
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Art Direction") FLinearColor ClearingShadowColour=FLinearColor(.055f,.08f,.045f);
 /** Sky colours use the same SDR presentation space as the distant haze. */
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sky", meta=(ClampMin="0",ClampMax="1")) float SkyPaletteStrength=0.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sky") FLinearColor SkyHorizonColour=FLinearColor(.82f,.79f,.61f);
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sky") FLinearColor SkyZenithColour=FLinearColor(.36f,.57f,.63f);
 /** A light display-space finish shared by nearby plants, ground, sky and distance. */
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette Finish", meta=(ClampMin="0",ClampMax="1")) float FinishStrength=0.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette Finish", meta=(ClampMin="0",ClampMax="1.5")) float FinishSaturation=.8f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette Finish", meta=(ClampMin="0",ClampMax="1")) float GreenRestraint=.8f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette Finish", meta=(ClampMin="0",ClampMax=".5")) float HighlightCompression=.18f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette Finish", meta=(ClampMin=".5",ClampMax="1.5")) float MidtoneGain=.92f;
 /** Selective upper-tone treatment; zero preserves the muted palette. */
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette Finish", meta=(ClampMin="0",ClampMax="1")) float SunlightWarmth=0.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Palette Finish", meta=(ClampMin="0",ClampMax=".5")) float SunlightLift=0.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Forest Depth", meta=(ClampMin="0",ClampMax="1")) float CanopyDepthStrength=0.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Forest Depth") TObjectPtr<UGTForestInteriorData> ForestInterior;
 /** Close surface relief is independent of the long-view palette and haze. */
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Surface Detail", meta=(ClampMin="0",ClampMax="1")) float SurfaceDetailStrength=0.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Surface Detail", meta=(ClampMin="0",ClampMax="1")) float SurfaceParallaxStrength=1.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Surface Detail", meta=(ClampMin="0",ClampMax="5",Units="cm")) float GravelDepthCm=1.6f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Surface Detail", meta=(ClampMin="0",ClampMax="5",Units="cm")) float GroundDepthCm=2.2f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Surface Detail", meta=(ClampMin="25",Units="cm")) float GravelTileCm=140.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Surface Detail", meta=(ClampMin="25",Units="cm")) float GroundTileCm=150.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Surface Detail", meta=(ClampMin="0",Units="m")) float SurfaceNearMetres=6.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Surface Detail", meta=(ClampMin="1",Units="m")) float SurfaceFarMetres=18.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Surface Detail", meta=(ClampMin="8",ClampMax="32")) int32 SurfaceMaxSteps=24;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Haze", meta=(ClampMin="0",ClampMax="1")) float HazeIntensity=.55f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Haze", meta=(ClampMin="0",Units="m")) float HazeStartMetres=900.f;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Haze", meta=(ClampMin="1",Units="m")) float HazeFullMetres=2400.f;
 /** Display-referred colour for the current SDR presentation. */
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Haze") FLinearColor HazeColour=FLinearColor(.48f,.61f,.59f);
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Map") FVector2D FieldOriginCm=FVector2D(-185000,-185000);
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Map") FVector2D FieldSpanCm=FVector2D(370000,370000);
};

/** One per persistent map. Editor preview and gameplay share the same profile application. */
UCLASS()
class GRANDTOUR_API AGTDistanceStyleController : public AActor
{
 GENERATED_BODY()
public:
 AGTDistanceStyleController();
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distance Style") TObjectPtr<UGTDistanceStyleProfile> Profile;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distance Style|Presets") TObjectPtr<UGTDistanceStyleProfile> Subtle;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distance Style|Presets") TObjectPtr<UGTDistanceStyleProfile> Medium;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distance Style|Presets") TObjectPtr<UGTDistanceStyleProfile> Strong;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distance Style|Presets") TObjectPtr<UGTDistanceStyleProfile> Cohesive;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distance Style|Bindings") TObjectPtr<UMaterialParameterCollection> Parameters;
 UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distance Style|Bindings") TObjectPtr<ADirectionalLight> Sun;
 UFUNCTION(BlueprintCallable, CallInEditor, Category="Distance Style") void ApplyProfile();
 UFUNCTION(BlueprintCallable, Category="Distance Style") void SetStylePreset(FName Preset);
 /** Development capture helpers; do not mutate the profile asset or saved map. */
 UFUNCTION(BlueprintCallable, Category="Distance Style|Review") void SetSurfaceReviewMode(int32 Mode);
 UFUNCTION(BlueprintCallable, Category="Distance Style|Review") void SetLeafReviewStrength(float Strength);
 UFUNCTION(BlueprintCallable, Category="Distance Style|Review") void FinishReviewShaders();
 UFUNCTION(BlueprintCallable, Category="Distance Style|Review") void SetCanopyDepthReview(float Strength);
 UFUNCTION(BlueprintCallable, Category="Distance Style|Review") void SetReviewView(float X,float Y,float Z,float Pitch,float Yaw,float FOV);
 virtual void Tick(float DeltaSeconds) override;
 virtual void OnConstruction(const FTransform& Transform) override;
 virtual void BeginPlay() override;
 virtual bool ShouldTickIfViewportsOnly() const override { return true; }
private:
 UPROPERTY(Transient) TObjectPtr<ACameraActor> ReviewCamera;
 UPROPERTY(Transient) TObjectPtr<UMaterialParameterCollection> FinishParameters;
 UPROPERTY(Transient) TObjectPtr<UMaterialParameterCollection> DepthParameters;
 UPROPERTY(Transient) TObjectPtr<UGTForestInteriorData> LoadedInterior;
 UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> InteriorInstances;
 void ApplyInterior();
 float CanopyDepthReview=-1.f;
 int32 SurfaceReviewMode=-1;
};
