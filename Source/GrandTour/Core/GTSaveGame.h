#pragma once

#include "CoreMinimal.h"
#include "Core/GTRunSubsystem.h"
#include "GameFramework/SaveGame.h"
#include "GTSaveGame.generated.h"

/** The one save (ARCHITECTURE 9): the campaign state and the carry snapshot, with a version (2 since M5: the tour, its seed and the scored results). Slot "GrandTour0". */
UCLASS()
class GRANDTOUR_API UGTSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	UPROPERTY()
	int32 Version = 2;

	UPROPERTY()
	FGTCampaignState Campaign;

	UPROPERTY()
	FGTCarrySnapshot Snapshot;
};
