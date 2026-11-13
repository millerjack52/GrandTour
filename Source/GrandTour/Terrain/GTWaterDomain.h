#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GTWaterDomain.generated.h"

/** Authored mean surface/current for the whole river and lake. Runtime waves use a moving, bounded grid.
 * The lake mask is coverage, not surveyed underwater bathymetry. */
UCLASS()
class GRANDTOUR_API UGTWaterDomain : public UDataAsset
{
	GENERATED_BODY()
public:
    /** Owned high-resolution authored pools; empty retains original behavior. */
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TArray<TObjectPtr<UGTWaterDomain>> RoadPatches;
    /** Replace authored child domains, rejecting nulls and recursive cycles. */
    UFUNCTION(BlueprintCallable, CallInEditor, Category="GT|Water")
    bool SetChildDomains(const TArray<UGTWaterDomain*>& Domains);
	UPROPERTY(VisibleAnywhere,BlueprintReadOnly) FVector2D OriginCm;
	UPROPERTY(VisibleAnywhere,BlueprintReadOnly) int32 SizeX=0;
	UPROPERTY(VisibleAnywhere,BlueprintReadOnly) int32 SizeY=0;
	UPROPERTY(VisibleAnywhere,BlueprintReadOnly) float CellCm=125;
	/** Interleaved surface cm, depth m, world velocity X/Y m/s. Negative depth means dry. */
	UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TArray<float> Samples;
	UPROPERTY() int32 LakeSizeX=0;
	UPROPERTY() int32 LakeSizeY=0;
	UPROPERTY() TArray<uint8> LakeMask;
	UPROPERTY() FVector2D LakeMinCm=FVector2D(-1146300,-849200);
	UPROPERTY() FVector2D LakeSpanCm=FVector2D(1368000,1277000);
	UPROPERTY() float LakeLevelCm=60;
	/** Samples wet-weighted mean height; never interpolates dry-bank elevations into the water. */
	bool Sample(const FVector2D& XY, float& SurfaceCm, float& DepthM, FVector2D& Velocity) const;
	/** Bounded shoreline support, not water occupancy. Caller must compare against the live bed. */
	bool SampleEnvelope(const FVector2D& XY, float MarginCm, float& SurfaceCm, float& DepthM, FVector2D& Velocity) const;
	/** Import checked binary data into the asset; runtime/cooked games use serialized arrays, no file IO. */
	UFUNCTION(BlueprintCallable, CallInEditor, Category="GT|Water")
	bool ImportBake(const FString& Filename);
};
