#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameplayTagContainer.h"
#include "Interaction/GTInteractable.h"
#include "GTCraftingStation.generated.h"

class AGTCarPawn;
class AGTPlayerCharacter;
class UGTInventoryComponent;
class UGTItemRegistry;
class UGTRunSubsystem;
class UStaticMeshComponent;

/** One line of a station screen: what it says, whether it can be acted on, and what acting means. */
USTRUCT(BlueprintType)
struct FGTScreenRow
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	FString Text;

	/** Why the row is disabled, or what acting does. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	FString Hint;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	bool bEnabled = true;

	/** A caption; never selected. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	bool bHeader = false;

	/** Station-specific action code (see each station). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	int32 Action = -1;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	FName Payload;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	FGameplayTag Tag;

	static FGTScreenRow Header(const FString& Text);
	static FGTScreenRow Line(const FString& Text, int32 Action, bool bEnabled, const FString& Hint = TEXT(""));
};

/**
 * Base for the stations of the convoy base (ARCHITECTURE 5: AGTCraftingStation; PROJECT_PLAN:
 * workbench, car lift, trader, crew as a menu, plus the briefing board). Each station is an
 * interactable greybox box; using it opens a screen on the character that lists the station's
 * rows (BuildRows) and acts on the selected one (Act). The rows are rebuilt after every act and
 * can change (a stack sold out, a new sell row), so the character keeps its cursor on the row it
 * acted on, not the index. E on the station or Tab closes it; walking away closes it too. An act
 * never uses up or takes off anything it has nowhere to put: it checks the bag and the boot first.
 * UMG replaces the canvas screens in M7; the rows and acts are what carry over.
 */
UCLASS(Abstract)
class GRANDTOUR_API AGTCraftingStation : public AActor, public IGTInteractable
{
	GENERATED_BODY()

public:
	AGTCraftingStation();

	virtual void BeginPlay() override;
	virtual FGTInteractionOffer GetInteractionOffer(const FGTInteractionQuery& Query) const override;
	virtual void Interact(const FGTInteractionQuery& Query) override;

	/** The screen's rows for this user right now. */
	virtual void BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const {}

	/** Acts on a row built by BuildRows; true when something changed. */
	virtual bool Act(AGTPlayerCharacter* User, const FGTScreenRow& Row) { return false; }

	/** The rows and a row index in one call (what the character's act key does). */
	bool ActOnRow(AGTPlayerCharacter* User, int32 RowIndex);

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Station")
	FGameplayTag StationTag;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Station")
	FString DisplayName = TEXT("station");

	UPROPERTY(EditAnywhere, Category = "GT|Station|Greybox")
	FVector GreyboxSize = FVector(120.f, 60.f, 90.f);

	UPROPERTY(EditAnywhere, Category = "GT|Station|Greybox")
	FLinearColor Colour = FLinearColor(0.4f, 0.4f, 0.45f);

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	int32 ActsCompleted = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	FString LastMessage;

protected:
	UGTRunSubsystem* Run() const;
	UGTItemRegistry* Registry() const;
	AGTCarPawn* FindPlayerCar() const;
	static UGTInventoryComponent* Bag(const AGTPlayerCharacter* User);
	static UGTInventoryComponent* Boot(const AGTCarPawn* Car);
	/** Count across the bag and the boot. */
	static int32 CountBoth(const AGTPlayerCharacter* User, const AGTCarPawn* Car, FName ItemId);
	/** Removes from the bag first, then the boot; returns what was removed. */
	static int32 RemoveBoth(AGTPlayerCharacter* User, AGTCarPawn* Car, FName ItemId, int32 Count);
	/** Adds to the bag, the rest to the boot; returns what fitted. */
	static int32 GiveBoth(AGTPlayerCharacter* User, AGTCarPawn* Car, FName ItemId, int32 Count);
	/** Adds to the boot, the rest to the bag; returns what fitted. Parts taken off the car go here. */
	static int32 GiveBootFirst(AGTPlayerCharacter* User, AGTCarPawn* Car, FName ItemId, int32 Count);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Station")
	TObjectPtr<UStaticMeshComponent> Mesh;
};

/** Crafts recipes tagged Station.Workbench from the bag and the boot into the bag (then the boot); refused when the result would not fit. */
UCLASS()
class GRANDTOUR_API AGTWorkbench : public AGTCraftingStation
{
	GENERATED_BODY()

public:
	AGTWorkbench();
	virtual void BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const override;
	virtual bool Act(AGTPlayerCharacter* User, const FGTScreenRow& Row) override;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	int32 Crafted = 0;
};

/**
 * Install, remove, repair and wash the car parked on the lift. Rows: the slots (act = remove to
 * the boot; the car's required slots only swap, and a part with no room in the boot or the bag
 * stays on), the parts in the bag and boot that fit (act = install, the old part goes to the
 * boot; refused when it has nowhere to go), repair all (scrap, priced by the mechanic tier and
 * offered whenever anything is damaged, free at Mechanic II; puts every panel back, clears
 * dents), wash (dirt, wetness and snow gone). Tuning waits for runtime suspension setters.
 */
UCLASS()
class GRANDTOUR_API AGTCarLift : public AGTCraftingStation
{
	GENERATED_BODY()

public:
	AGTCarLift();
	virtual void BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const override;
	virtual bool Act(AGTPlayerCharacter* User, const FGTScreenRow& Row) override;

	/** The car must be this close (cm) to the lift. */
	UPROPERTY(EditAnywhere, Category = "GT|Lift")
	float LiftRadius = 1200.f;

	/** Scrap per whole point of missing part health, before the mechanic discount. */
	UPROPERTY(EditAnywhere, Category = "GT|Lift")
	float RepairScrapPerHealth = 4.f;

	UFUNCTION(BlueprintPure, Category = "GT|Lift")
	int32 RepairCost(const AGTCarPawn* Car) const;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	int32 Repairs = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	int32 Washes = 0;

	enum EAction { Remove = 1, Install = 2, Repair = 3, Wash = 4 };
};

/** Sells the bag's and boot's items at a fraction of base price (by the trader tier) and buys stock at base price. */
UCLASS()
class GRANDTOUR_API AGTTrader : public AGTCraftingStation
{
	GENERATED_BODY()

public:
	AGTTrader();
	virtual void BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const override;
	virtual bool Act(AGTPlayerCharacter* User, const FGTScreenRow& Row) override;

	UFUNCTION(BlueprintPure, Category = "GT|Trader")
	int32 SellPrice(FName ItemId) const;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	int32 Sold = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	int32 Bought = 0;

	enum EAction { Sell = 1, Buy = 2 };
};

/** Buys crew tiers in order per track. */
UCLASS()
class GRANDTOUR_API AGTCrewTent : public AGTCraftingStation
{
	GENERATED_BODY()

public:
	AGTCrewTent();
	virtual void BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const override;
	virtual bool Act(AGTPlayerCharacter* User, const FGTScreenRow& Row) override;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	int32 UpgradesBought = 0;
};

/**
 * The next leg's briefing: the tour and leg, the mission and its brief, par and limit, weather,
 * the conditions profile at the scout tier's precision, the rivals' usual pace and the table so
 * far. Once the tour is over it shows the final table and the ending, and offers a new tour.
 */
UCLASS()
class GRANDTOUR_API AGTBriefingBoard : public AGTCraftingStation
{
	GENERATED_BODY()

public:
	AGTBriefingBoard();
	virtual void BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const override;
	virtual bool Act(AGTPlayerCharacter* User, const FGTScreenRow& Row) override;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Station")
	int32 ToursStarted = 0;

	enum EAction { NewTour = 1 };
};
