#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTMudDetailStudy.generated.h"

class AGTLandscapeSurface;
class UInstancedStaticMeshComponent;

/** Opt-in art-study dressing. Seeds a worn lane and keeps small decorative debris on its mud surface. */
UCLASS()
class GRANDTOUR_API AGTMudDetailStudy : public AActor
{
    GENERATED_BODY()
public:
    AGTMudDetailStudy();
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Study") TObjectPtr<AGTLandscapeSurface> Surface;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Study") TArray<TObjectPtr<AActor>> DebrisGroups;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Study") bool bSeedTracksOnPlay = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Study", meta=(ClampMin="0",ClampMax="1")) float SeedDepthScale = 1.f;
    UFUNCTION(BlueprintCallable, Category="Mud Study") void SeedTracks();
private:
    struct FAnchors
    {
        TWeakObjectPtr<UInstancedStaticMeshComponent> Component;
        TArray<FTransform> Rest;
        bool bFloat = false;
        bool bGrass = false;
    };
    TArray<FAnchors> Anchors;
    bool bReady = false;
    bool bSeeded = false;
};
