// Generates derived tree static meshes from the vendor Kasyanik trees
// (Content/3DAssets) without touching the originals: splits a tree into its
// connected islands (trunk + individual leaf blobs), keeps the trunk and a
// seeded random subset of blobs (always keeping the crown blob for
// silhouette), rescales, and saves as a new /Game/OWGame mesh wearing the
// OW-owned MI_OW* materials. Normal recompute stays OFF (painterly normals).
// Run: UnrealEditor-Cmd.exe <uproject> -run=OWCreateTreeVariants -Unattended
//      -NullRHI -NoSplash -NoSound   (editor CLOSED)
// Leg dressing LD4 (docs/LEG_DRESSING_PLAN.md): every variant gets simple collision
// only - one trunk capsule on each tree, dead tree and stump, none on a bush - and
// CollisionTraceFlag UseSimpleAsComplex; the check is logged ("LD4 capsule") and
// written to docs/landscape_migration/ld4_variant_capsules.json.

#pragma once

#include "Commandlets/Commandlet.h"
#include "OWCreateTreeVariantsCommandlet.generated.h"

UCLASS()
class UOWCreateTreeVariantsCommandlet : public UCommandlet
{
	GENERATED_BODY()

public:
	virtual int32 Main(const FString& Params) override;
};
