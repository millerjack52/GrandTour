#pragma once

#include "CoreMinimal.h"
#include "Run/GTLegActors.h"
#include "GTDepartGate.generated.h"

/** The base's exit: drive the car through it and the base game mode departs to the next leg. Greybox: a slab across the gateway. */
UCLASS()
class GRANDTOUR_API AGTDepartGate : public AGTLegVolume
{
	GENERATED_BODY()

public:
	AGTDepartGate();

	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Base")
	bool bTriggered = false;
};
