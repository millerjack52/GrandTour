#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTGroundedDressing.generated.h"
class AGTLandscapeSurface;
/** Batched cosmetic dressing follows the same GPU bed field as the ground. No actor tick. */
UCLASS()
class GRANDTOUR_API AGTGroundedDressing : public AActor
{
 GENERATED_BODY()
public:
 UPROPERTY(EditAnywhere, Category="GT|Dressing") TObjectPtr<AGTLandscapeSurface> GroundSurface;
protected:
 virtual void BeginPlay() override;
};
