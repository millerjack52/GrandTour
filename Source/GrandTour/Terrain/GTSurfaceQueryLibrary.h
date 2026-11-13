// Benmore integration B1 (docs/BENMORE_INTEGRATION_PLAN.md B1 item 5): what surface a point of the ground is, for scripts and checks.
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GTSurfaceQueryLibrary.generated.h"

class UPhysicalMaterial;

UCLASS()
class GRANDTOUR_API UGTSurfaceQueryLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * The physical material the first landscape hit between Start and End carries (complex collision with physical materials returned:
	 * the landscape's per-sample surface from its physical material output, or its layers). Other actors are passed through. Null on a
	 * miss. (The Kismet line traces do not return physical materials.)
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Surface", meta = (WorldContext = "WorldContextObject"))
	static UPhysicalMaterial* TraceLandscapeSurface(UObject* WorldContextObject, FVector Start, FVector End, FVector& OutPoint, FVector& OutNormal);

	/** A diagnosis of the landscape surface at a world XY: the trace's physical material, the landscape's own lookup (complex and simple
	 *  heightfields) and the collision component's physical material lists (render objects, render samples, cooked, layer infos). */
	UFUNCTION(BlueprintCallable, Category = "GT|Surface", meta = (WorldContext = "WorldContextObject"))
	static FString DescribeLandscapeSurfaceAt(UObject* WorldContextObject, FVector Location);
};
