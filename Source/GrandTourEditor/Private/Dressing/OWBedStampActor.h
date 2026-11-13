// Thin actor wrapper around UOWBedStampComponent so setup scripts can spawn a
// bed stamp in one call. Editor-only; it does nothing but hold the component.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "OWBedStampActor.generated.h"

class UOWBedStampComponent;

UCLASS(meta = (DisplayName = "OW Bed Stamp"))
class AOWBedStampActor : public AActor
{
	GENERATED_BODY()

public:
	AOWBedStampActor();

	UOWBedStampComponent* GetBedStamp() const { return BedStamp; }

private:
	UPROPERTY(VisibleAnywhere, Category = "OW Bed Stamp")
	TObjectPtr<UOWBedStampComponent> BedStamp;
};
