#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GTTourDefinition.generated.h"

/** A rival in the standings (PROJECT_PLAN 6: standings only, no car on the track). */
USTRUCT(BlueprintType)
struct FGTRivalDefinition
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	FString Name;

	/** Flavour for the standings ("a tired Hilux"). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	FString Car;

	/** Multiplies the leg's par: 0.9 is quick, 1.2 is slow. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour", meta = (ClampMin = 0.5, ClampMax = 2))
	float Skill = 1.f;

	/** Relative spread of the leg time (one sigma); 0.08 is eight per cent. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour", meta = (ClampMin = 0, ClampMax = 0.5))
	float Consistency = 0.08f;

	/** 0..1: how often the rival finishes a hard leg (endurance, photograph); time trials rarely drop anyone. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour", meta = (ClampMin = 0, ClampMax = 1))
	float Grit = 0.85f;
};

/**
 * A tour (the format proposed on 2026-09-09 and the M5 leg sequence): a run of legs in one
 * region with a camp, the rivals who share the standings, the points and the prize money by
 * placing, and the ending lines. The campaign holds the tour's path and its leg index; the run
 * subsystem resolves the next leg from here. DA_Tour_01 is written by Art/setup_m5_legs.bat
 * from ApplyDefaultTour01, and a runtime copy stands in when the asset is missing.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTTourDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	FName TourId = TEXT("Tour01");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	FText DisplayName;

	/** Where the tour is set; the camp map takes its style from it (M6). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	FText Region;

	/** The camp between legs, as a long package path. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	FString CampMapPath = TEXT("/Game/GrandTour/Base/L_Base");

	/** The legs in order, as long package paths (/Game/GrandTour/Legs/DA_Leg_01). A missing asset falls back to the default leg of the same index. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	TArray<FString> LegPaths;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	TArray<FGTRivalDefinition> Rivals;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour", meta = (ClampMin = 0))
	int32 StartingCredits = 300;

	/** Points for 1st, 2nd, ...; a placing past the end scores the last entry; a did-not-finish scores 0. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	TArray<int32> PointsByPlace;

	/** Prize credits by placing, the same way. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	TArray<int32> PrizeByPlace;

	/** The ending card's line when the player wins, stands on the podium, or neither. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	FText EndingWin;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	FText EndingPodium;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tour")
	FText EndingLose;

	UFUNCTION(BlueprintPure, Category = "GT|Tour")
	int32 LegCount() const { return LegPaths.Num(); }

	UFUNCTION(BlueprintPure, Category = "GT|Tour")
	int32 PointsForPlace(int32 Place) const;

	UFUNCTION(BlueprintPure, Category = "GT|Tour")
	int32 PrizeForPlace(int32 Place) const;

	UFUNCTION(BlueprintPure, Category = "GT|Tour")
	FString Describe() const;

	/** Tour 1: the Altiplano, five legs (DefaultLegs), four rivals, 10/8/6/5/4 points, 200/150/100/60/40 credits. */
	void ApplyDefaultTour01(const FString& LegFolder = TEXT("/Game/GrandTour/Legs"));
};
