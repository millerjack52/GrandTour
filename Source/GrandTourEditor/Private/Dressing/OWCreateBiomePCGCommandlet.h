// D2 of Docs/WorldDressingPlan.md: authors the three biome PCG graphs
// (PCG_OWForest / PCG_OWMeadow / PCG_OWScree) that read painted landscape
// layer weights. Lives in C++ because FPCGAttributePropertySelector is not
// reachable from python (protected UPROPERTYs; ScriptMethod setter ensures on
// the derived InputSelector - paid 2026-07-27, four failed python routes).
// Rerunnable: existing graphs are cleared and rebuilt in place so level
// actors keep their references.
// Run: UnrealEditor-Cmd.exe <uproject> -run=OWCreateBiomePCG -Unattended
//      -NullRHI -NoSplash -NoSound   (editor CLOSED)
// Leg dressing LD4 (docs/LEG_DRESSING_PLAN.md): -Variant=GT builds the GrandTour
// variants PCG_GT_Forest/Meadow/Scree/Alpine/Brush into /Game/GrandTour/Dressing/PCG
// instead (physical classes, tree size classes, understorey, Thicket brush) and
// writes docs/landscape_migration/ld4_gt_graphs.json. Without it the OW graphs
// build exactly as before.

#pragma once

#include "Commandlets/Commandlet.h"
#include "OWCreateBiomePCGCommandlet.generated.h"

UCLASS()
class UOWCreateBiomePCGCommandlet : public UCommandlet
{
	GENERATED_BODY()

public:
	virtual int32 Main(const FString& Params) override;
};
