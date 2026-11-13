#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "Vehicle/GTConditionComponent.h"
#include "GTItemDefinition.generated.h"

UENUM(BlueprintType)
enum class EGTItemKind : uint8
{
	Resource,
	Part,
	Tool,
	Consumable
};

/**
 * Anything that sits in an inventory (ARCHITECTURE 4): id, name, weight, base price. Resources
 * are plain definitions; parts and consumables derive. Assets live under /Game/GrandTour/Items
 * (Art/setup_m4_base.bat writes DA_Item_*); UGTItemRegistry builds the same set from the C++
 * defaults when an asset is missing, so the greybox item table of M2 is now the fallback only.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTItemDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Item")
	FName ItemId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Item")
	FText DisplayName;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Item")
	EGTItemKind Kind = EGTItemKind::Resource;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Item", meta = (ClampMin = 0))
	float WeightKg = 1.f;

	/** What the trader pays before its cut and charges before its margin. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Item", meta = (ClampMin = 0))
	int32 BasePrice = 1;

	/** Sold by the trader when true. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Item")
	bool bTraderStocks = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Item|Greybox")
	FLinearColor GreyboxColour = FLinearColor(0.5f, 0.5f, 0.5f);

	virtual FString Describe() const;
};

/** A resistance a part grants: Env.* (conditions) or Hazard.* tags, 0..1. */
USTRUCT(BlueprintType)
struct FGTResistance
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part")
	FGameplayTag Tag;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part", meta = (ClampMin = 0, ClampMax = 1))
	float Strength = 0.5f;
};

/**
 * An installable part (ARCHITECTURE 4, VEHICLE_BUILD_SYSTEM 3 and 7): the slot it needs, its
 * tuning contributions, the resistances it grants by tag, the condition entries it owns (their
 * health resets when it is installed), a tag dependency, and a greybox box in car space so the
 * part is a real mesh on a socket from the start (the hands-on install of a later tier only
 * adds an interaction layer). Tier 1 ships one car with kits: no socket graph yet, one part per
 * slot, and the fit rules that exist are the slot, the occupancy and the tag dependency.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTPartDefinition : public UGTItemDefinition
{
	GENERATED_BODY()

public:
	UGTPartDefinition();

	/** Slot.Engine, Slot.Radiator, Slot.AirFilter, Slot.Heater, Slot.Suspension, Slot.Tyres, Slot.FuelTank, Slot.Gadget, Slot.Shielding. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part")
	FGameplayTag Slot;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part", meta = (ClampMin = 1, ClampMax = 3))
	int32 Tier = 1;

	// ---- tuning contributions (the parts stage of the pipeline) ---------------------------------
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part|Tuning")
	float TorqueScale = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part|Tuning")
	float DragDelta = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part|Tuning")
	float GripScale = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part|Tuning")
	float RollingResistanceScale = 1.f;

	/** Litres for a tank part, 0 otherwise. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part|Tuning")
	float TankCapacityLitres = 0.f;

	/** Rated pull for a winch part, 0 otherwise. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part|Tuning")
	float WinchPullN = 0.f;

	// ---- what it answers -------------------------------------------------------------------------
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part")
	TArray<FGTResistance> Resistances;

	/** Condition entries this part is; installing it sets them to full health. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part")
	TArray<EGTCarPart> OwnedParts;

	/** Multiplies impact damage to the owned parts (heavy-duty parts take less). Read by the condition in a later slice. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part", meta = (ClampMin = 0.1, ClampMax = 2))
	float DamageScale = 1.f;

	/** A tag another installed part must provide (a turbo needs an engine that provides Turbo). None = no dependency. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part")
	FGameplayTag RequiresTag;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part")
	FGameplayTagContainer ProvidesTags;

	// ---- greybox -----------------------------------------------------------------------------------
	/** Centre in car space, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part|Greybox")
	FVector GreyboxLocation = FVector::ZeroVector;

	/** Box size in cm; zero = no visual (tyres are the wheels, suspension is inside the arches). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Part|Greybox")
	FVector GreyboxSize = FVector::ZeroVector;

	virtual FString Describe() const override;
};

/**
 * A consumable (ARCHITECTURE 4: an item that grants a temporary resistance, or resets a state).
 * Used from the inventory screen on foot or in the seat.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTConsumableDefinition : public UGTItemDefinition
{
	GENERATED_BODY()

public:
	UGTConsumableDefinition();

	/** Temporary resistance granted to the car and the player, none = no resistance. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Consumable")
	FGameplayTag ResistanceTag;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Consumable", meta = (ClampMin = 0, ClampMax = 1))
	float ResistanceStrength = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Consumable", meta = (ClampMin = 0))
	float DurationSeconds = 0.f;

	/** Clears the environment's coolant heat. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Consumable")
	bool bResetHeat = false;

	/** Clears the air filter clog. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Consumable")
	bool bResetClog = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Consumable", meta = (ClampMin = 0))
	float ExposureRestore = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Consumable", meta = (ClampMin = 0))
	float FuelLitres = 0.f;

	virtual FString Describe() const override;
};

/** The C++ defaults every item comes from until the assets exist; also what the setup writes. */
namespace GTItemDefaults
{
	struct FResource { const TCHAR* Id; const TCHAR* Name; float WeightKg; int32 Price; bool bStocked; FLinearColor Colour; };
	struct FPart
	{
		const TCHAR* Id; const TCHAR* Name; const TCHAR* Slot; int32 Tier; float WeightKg; int32 Price; bool bStocked;
		float Torque; float Drag; float Grip; float Rolling; float Tank; float Winch;
		const TCHAR* ResistTag; float Resist; float DamageScale;
		TArray<EGTCarPart> Owned; FVector Location; FVector Size; FLinearColor Colour;
	};
	struct FConsumable
	{
		const TCHAR* Id; const TCHAR* Name; float WeightKg; int32 Price; bool bStocked;
		const TCHAR* ResistTag; float Resist; float Duration; bool bHeat; bool bClog; float Exposure; float Fuel;
	};
	GRANDTOUR_API TArrayView<const FResource> Resources();
	GRANDTOUR_API TArrayView<const FPart> Parts();
	GRANDTOUR_API TArrayView<const FConsumable> Consumables();

	GRANDTOUR_API void Apply(UGTItemDefinition* Item, const FResource& Row);
	GRANDTOUR_API void Apply(UGTPartDefinition* Part, const FPart& Row);
	GRANDTOUR_API void Apply(UGTConsumableDefinition* Item, const FConsumable& Row);

	/** Asset name for an item id: Part.Radiator -> DA_Item_Part_Radiator. */
	GRANDTOUR_API FString AssetName(const TCHAR* Id);
}
