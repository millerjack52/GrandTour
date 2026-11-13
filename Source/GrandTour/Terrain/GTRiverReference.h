#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GTRiverReference.generated.h"

/** A bounded, offline river mean. Fluxes are projected to zero interior divergence before import.
 * Positions are world centimetres; depths metres; face discharges m3/s. No external runtime files. */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTRiverReference : public UDataAsset
{
	GENERATED_BODY()
public:
	UPROPERTY(EditAnywhere, Category="River") FVector2D OriginCm;
	UPROPERTY(EditAnywhere, Category="River") FVector2D AxisX = FVector2D(1, 0);
	UPROPERTY(EditAnywhere, Category="River") int32 SizeX = 0;
	UPROPERTY(EditAnywhere, Category="River") int32 SizeY = 0;
	UPROPERTY(EditAnywhere, Category="River") float CellCm = 37.5f;
	UPROPERTY(EditAnywhere, Category="River") TArray<float> BedCm;
	UPROPERTY(EditAnywhere, Category="River") TArray<float> DepthM;
	UPROPERTY(EditAnywhere, Category="River") TArray<float> FluxX;
	UPROPERTY(EditAnywhere, Category="River") TArray<float> FluxY;
};
