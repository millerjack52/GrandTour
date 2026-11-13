#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "GTUpgradeDefinition.generated.h"

/**
 * A crew upgrade (ARCHITECTURE 4, PROJECT_PLAN: crew upgrades as a menu at the base). Tracks
 * are gameplay tags (Crew.Mechanic, Crew.Trader, Crew.Scout, Crew.Workbench); tiers must be
 * bought in order; the effect of a tier is read by the station that cares (the lift's repair
 * price, the trader's cut, the briefing's precision, the workbench's recipe tier). Assets under
 * /Game/GrandTour/Economy (Art/setup_m4_base.bat writes DA_Upgrade_*).
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTUpgradeDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Upgrade")
	FName UpgradeId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Upgrade")
	FText DisplayName;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Upgrade")
	FGameplayTag Track;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Upgrade", meta = (ClampMin = 1, ClampMax = 3))
	int32 Tier = 1;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Upgrade", meta = (ClampMin = 0))
	int32 Cost = 200;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Upgrade")
	FText Effect;

	UFUNCTION(BlueprintPure, Category = "GT|Upgrade")
	FString Describe() const;

	struct FDefault
	{
		const TCHAR* AssetName;
		const TCHAR* Id;
		const TCHAR* Name;
		const TCHAR* Track;
		int32 Tier;
		int32 Cost;
		const TCHAR* Effect;
	};
	static TArrayView<const FDefault> DefaultUpgrades();
	void ApplyDefault(const FDefault& Row);

	/** The trader's payout fraction at a Crew.Trader tier: 0.6, 0.7, 0.8. */
	static float SellFraction(int32 TraderTier);
	/** The lift's repair price factor at a Crew.Mechanic tier: 1, 0.5, 0. */
	static float RepairPriceFactor(int32 MechanicTier);
};
