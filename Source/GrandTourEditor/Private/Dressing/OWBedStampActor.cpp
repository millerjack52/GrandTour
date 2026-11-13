#include "OWBedStampActor.h"

#include "OWBedStampComponent.h"

AOWBedStampActor::AOWBedStampActor()
{
	// C3: no tick anywhere in the stamp kit.
	PrimaryActorTick.bCanEverTick = false;
	PrimaryActorTick.bStartWithTickEnabled = false;

	// The patch component is editor-only and cook-stripped; so is the actor.
	bIsEditorOnlyActor = true;

	BedStamp = CreateDefaultSubobject<UOWBedStampComponent>(TEXT("BedStamp"));
	SetRootComponent(BedStamp);
}
