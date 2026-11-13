// Road-verge auto-paint (user directive 2026-07-29 "get rid of grass on
// the road"): stamps OW_RoadVerge layer weight into the -Map=
// landscape under every BP_OWRoad* spline, so the carpet/tuft/flower
// grass pins (which OW_RoadVerge deliberately lacks) stop spawning on
// roads without a hand stroke per road. Lives in C++ because landscape
// weightmap writes (FLandscapeEditDataInterface) are not python-exposed.
// Read-modify-write with max(): existing hand-painted verge strokes are
// preserved; rerun after drawing new roads. Limitation (recorded): the
// stamp is additive - moving/deleting a road leaves its strip painted
// (repaint by hand or extend with a clear mode if it ever matters).
// Run: UnrealEditor-Cmd.exe <uproject> -run=OWPaintRoadVerge -Map=<map>
//      -Unattended -NoSplash -NoSound   (-Map= required, e.g.
//      /Game/GrandTour/Test/L_OWToolkitTest; editor CLOSED; run WITH RHI - edit-layer
//      weight compositing is GPU work, NullRHI would defer it to the
//      next editor load)

#pragma once

#include "Commandlets/Commandlet.h"
#include "OWPaintRoadVergeCommandlet.generated.h"

UCLASS()
class UOWPaintRoadVergeCommandlet : public UCommandlet
{
	GENERATED_BODY()

public:
	virtual int32 Main(const FString& Params) override;
};
