#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "GTPartSlotsComponent.generated.h"

class UGTItemRegistry;
class UGTPartDefinition;
class UStaticMeshComponent;
struct FGTVehicleTuning;

/** One installed part, saved as (slot, part id) pairs (VEHICLE_BUILD_SYSTEM 7). */
USTRUCT(BlueprintType)
struct FGTSlotEntry
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Parts")
	FGameplayTag Slot;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Parts")
	FName PartId;
};

/** A timed resistance from a consumable (tag, strength, time left); the run subsystem carries these between levels. */
USTRUCT(BlueprintType)
struct FGTTimedResistance
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Parts")
	FGameplayTag Tag;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Parts")
	float Strength = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Parts")
	float SecondsLeft = 0.f;
};

UENUM(BlueprintType)
enum class EGTFitReason : uint8
{
	Fits,
	UnknownItem,
	NotAPart,
	NoSuchSlot,
	NeedsProvider
};

/** Why a part fits or not, and what would make it fit (the lift UI always says why). */
USTRUCT(BlueprintType)
struct FGTFitResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GT|Parts")
	bool bFits = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Parts")
	EGTFitReason Reason = EGTFitReason::Fits;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Parts")
	FString Hint;

	/** The part the install would replace, none when the slot is empty. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Parts")
	FName Replaces;
};

/**
 * The car's installed parts (ARCHITECTURE 5 UGTPartSlotsComponent, VEHICLE_BUILD_SYSTEM 3 and 7,
 * Tier 1 shape): one part per named slot, a default loadout, and the effects of what is
 * installed: the parts stage of the tuning pipeline (torque, drag, grip, rolling), resistances
 * by tag written into the condition (Hazard.*) and the environment (Env.*), the tank capacity,
 * the winch's presence and pull, and a greybox box per part at its car-space socket so the
 * hands-on install of a later tier only adds an interaction layer. Consumables add temporary
 * resistances here. The fit rules are the slot, the occupancy (an install swaps the old part
 * out to the inventory) and a tag dependency; the socket graph and envelopes of the full design
 * come with the modular content. An empty engine or tank slot means no drive, and the lift keeps
 * the RequiredSlots filled (swap only).
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTPartSlotsComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTPartSlotsComponent();

	virtual void BeginPlay() override;

	/** Driven by the car every tick: temporary resistances tick down here. */
	void Update(float DeltaSeconds);
	void ModifyTuning(FGTVehicleTuning& Tuning) const;

	UFUNCTION(BlueprintPure, Category = "GT|Parts")
	FName GetInstalled(FGameplayTag Slot) const;

	UFUNCTION(BlueprintPure, Category = "GT|Parts")
	UGTPartDefinition* GetInstalledPart(FGameplayTag Slot) const;

	UFUNCTION(BlueprintPure, Category = "GT|Parts")
	FGTFitResult CanInstall(FName PartId) const;

	/** Installs PartId in its slot (the old part id, if any, comes back in OutReplaced); resets the health of the parts it owns. */
	UFUNCTION(BlueprintCallable, Category = "GT|Parts")
	bool Install(FName PartId, FName& OutReplaced);

	UFUNCTION(BlueprintCallable, Category = "GT|Parts")
	bool Remove(FGameplayTag Slot, FName& OutRemoved);

	/** Permanent (installed parts) plus temporary (consumables) resistance for a tag, 0..1. */
	UFUNCTION(BlueprintPure, Category = "GT|Parts")
	float GetResistance(FGameplayTag Tag) const;

	UFUNCTION(BlueprintCallable, Category = "GT|Parts")
	void AddTemporaryResistance(FGameplayTag Tag, float Strength, float Seconds);

	/** The consumables' resistances still running, with their time left. */
	TArray<FGTTimedResistance> GetTemporaryResistances() const;

	UFUNCTION(BlueprintPure, Category = "GT|Parts")
	TArray<FGTSlotEntry> GetLoadout() const;

	/** Replaces every slot from a saved loadout (empty slots stay empty); health untouched unless bResetHealth. */
	UFUNCTION(BlueprintCallable, Category = "GT|Parts")
	void ApplyLoadout(const TArray<FGTSlotEntry>& Loadout, bool bResetHealth);

	/** Pushes the installed set into the condition, environment, winch and visuals. */
	UFUNCTION(BlueprintCallable, Category = "GT|Parts")
	void ApplyEffects();

	static const TCHAR* ReasonName(EGTFitReason Reason);
	static FString SlotName(FGameplayTag Slot);

	UFUNCTION(BlueprintPure, Category = "GT|Parts")
	FString Describe() const;

	/** Slots in display order. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Parts")
	TArray<FGameplayTag> Slots;

	/** What a new car carries. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Parts")
	TArray<FGTSlotEntry> DefaultLoadout;

	/** Prototype part boxes are optional when the vehicle already has an authored body/interior. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Parts")
	bool bShowGreyboxVisuals = true;

	/** Slots the car cannot run without (engine, radiator, suspension, tyres, tank): the lift swaps their parts but never leaves them empty. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Parts")
	TArray<FGameplayTag> RequiredSlots;

	UFUNCTION(BlueprintPure, Category = "GT|Parts")
	bool IsRequiredSlot(FGameplayTag Slot) const { return RequiredSlots.Contains(Slot); }

	UPROPERTY(BlueprintReadOnly, Category = "GT|Parts")
	int32 Installs = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Parts")
	int32 Removals = 0;

	/** Bumps on every change (HUD refresh, tests). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Parts")
	int32 Version = 0;

private:
	struct FTemporary
	{
		FGameplayTag Tag;
		float Strength = 0.f;
		float TimeLeft = 0.f;
	};

	UGTItemRegistry* Registry() const;
	void RebuildVisuals();
	bool ProvidesTag(FGameplayTag Tag, FGameplayTag ExceptSlot) const;

	UPROPERTY(VisibleAnywhere, Category = "GT|Parts")
	TMap<FGameplayTag, FName> Installed;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Visuals;

	TArray<FTemporary> Temporaries;
	bool bBegun = false;
};
