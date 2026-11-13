#include "Parts/GTPartSlotsComponent.h"

#include "Core/GTGameplayTags.h"
#include "Environment/GTEnvironmentComponent.h"
#include "Parts/GTItemDefinition.h"
#include "Parts/GTItemRegistry.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTRangeRoverAudioComponent.h"
#include "Vehicle/GTRangeRoverDrivetrain.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTVehicleTuning.h"
#include "Vehicle/GTWinchAnchor.h"
#include "Vehicle/GTWinchComponent.h"

#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

UGTPartSlotsComponent::UGTPartSlotsComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick
	Slots = {
		GTTags::Slot_DriveLayout, GTTags::Slot_Engine, GTTags::Slot_Radiator, GTTags::Slot_AirFilter, GTTags::Slot_Heater, GTTags::Slot_Suspension,
	          GTTags::Slot_Tyres, GTTags::Slot_FuelTank, GTTags::Slot_Gadget, GTTags::Slot_Shielding };
	auto Entry = [](FGameplayTag Slot, const TCHAR* PartId)
	{
		FGTSlotEntry E;
		E.Slot = Slot;
		E.PartId = PartId;
		return E;
	};
	DefaultLoadout = {
		Entry(GTTags::Slot_Engine, TEXT("Part.Engine")),
		Entry(GTTags::Slot_Radiator, TEXT("Part.Radiator")),
		Entry(GTTags::Slot_Suspension, TEXT("Part.Suspension")),
		Entry(GTTags::Slot_Tyres, TEXT("Part.Tyre")),
		Entry(GTTags::Slot_FuelTank, TEXT("Part.FuelTank")),
		Entry(GTTags::Slot_Gadget, TEXT("Part.Winch")),
	};
	RequiredSlots = { GTTags::Slot_Engine, GTTags::Slot_Radiator, GTTags::Slot_Suspension, GTTags::Slot_Tyres, GTTags::Slot_FuelTank };
}

UGTItemRegistry* UGTPartSlotsComponent::Registry() const
{
	return UGTItemRegistry::Get(this);
}

void UGTPartSlotsComponent::BeginPlay()
{
	Super::BeginPlay();
	bBegun = true;
	// Existing blueprints serialize the previous slot list. Migrate instances without touching assets.
	Slots.AddUnique(GTTags::Slot_DriveLayout);
	if (Installed.Num() == 0)
	{
		for (const FGTSlotEntry& E : DefaultLoadout)
		{
			if (E.Slot.IsValid() && !E.PartId.IsNone())
			{
				Installed.Add(E.Slot, E.PartId);
			}
		}
	}
	ApplyEffects();
}

FName UGTPartSlotsComponent::GetInstalled(FGameplayTag Slot) const
{
	const FName* Found = Installed.Find(Slot);
	return Found ? *Found : NAME_None;
}

UGTPartDefinition* UGTPartSlotsComponent::GetInstalledPart(FGameplayTag Slot) const
{
	const FName Id = GetInstalled(Slot);
	return (Id.IsNone() || !Registry()) ? nullptr : Registry()->FindPart(Id);
}

bool UGTPartSlotsComponent::ProvidesTag(FGameplayTag Tag, FGameplayTag ExceptSlot) const
{
	for (const TPair<FGameplayTag, FName>& Pair : Installed)
	{
		if (Pair.Key == ExceptSlot)
		{
			continue;
		}
		const UGTPartDefinition* Part = Registry() ? Registry()->FindPart(Pair.Value) : nullptr;
		if (Part && Part->ProvidesTags.HasTag(Tag))
		{
			return true;
		}
	}
	return false;
}

FGTFitResult UGTPartSlotsComponent::CanInstall(FName PartId) const
{
	FGTFitResult Result;
	if(GTRangeRoverDrivetrain::Index(PartId)>0 && !UGTRangeRoverAudioComponent::IsRangeRover(GetOwner()))
	{
		Result.Reason=EGTFitReason::NeedsProvider;
		Result.Hint=TEXT("This drivetrain fits the Range Rover only");
		return Result;
	}
	const UGTItemDefinition* Item = Registry() ? Registry()->Find(PartId) : nullptr;
	if (!Item)
	{
		Result.Reason = EGTFitReason::UnknownItem;
		Result.Hint = TEXT("unknown item");
		return Result;
	}
	const UGTPartDefinition* Part = Cast<UGTPartDefinition>(Item);
	if (!Part)
	{
		Result.Reason = EGTFitReason::NotAPart;
		Result.Hint = TEXT("not a part");
		return Result;
	}
	if (Part->Slot==GTTags::Slot_DriveLayout && GetOwner()->GetVelocity().Size()>30.f)
	{
		Result.Reason=EGTFitReason::NeedsProvider;
		Result.Hint=TEXT("Stop the car before swapping drive layout");
		return Result;
	}
	if (!Slots.Contains(Part->Slot))
	{
		Result.Reason = EGTFitReason::NoSuchSlot;
		Result.Hint = FString::Printf(TEXT("this car has no %s slot"), *SlotName(Part->Slot));
		return Result;
	}
	if (Part->RequiresTag.IsValid() && !ProvidesTag(Part->RequiresTag, Part->Slot))
	{
		Result.Reason = EGTFitReason::NeedsProvider;
		Result.Hint = FString::Printf(TEXT("needs a part that provides %s"), *Part->RequiresTag.ToString());
		return Result;
	}
	Result.bFits = true;
	Result.Replaces = GetInstalled(Part->Slot);
	return Result;
}

bool UGTPartSlotsComponent::Install(FName PartId, FName& OutReplaced)
{
	OutReplaced = NAME_None;
	const FGTFitResult Fit = CanInstall(PartId);
	if (!Fit.bFits)
	{
		UE_LOG(LogTemp, Display, TEXT("UGTPartSlotsComponent: %s does not fit: %s"), *PartId.ToString(), *Fit.Hint);
		return false;
	}
	const UGTPartDefinition* Part = Registry()->FindPart(PartId);
	OutReplaced = Fit.Replaces;
	Installed.Add(Part->Slot, PartId);
	if (const AGTCarPawn* Car = Cast<AGTCarPawn>(GetOwner()))
	{
		if (UGTConditionComponent* Condition = Car->GetCondition())
		{
			for (const EGTCarPart Owned : Part->OwnedParts)
			{
				Condition->SetPartHealth(Owned, 1.f);   // a new part is a whole part
			}
		}
	}
	++Installs;
	++Version;
	ApplyEffects();
	UE_LOG(LogTemp, Display, TEXT("UGTPartSlotsComponent: installed %s in %s%s"), *PartId.ToString(), *SlotName(Part->Slot),
		OutReplaced.IsNone() ? TEXT("") : *FString::Printf(TEXT(" (replacing %s)"), *OutReplaced.ToString()));
	return true;
}

bool UGTPartSlotsComponent::Remove(FGameplayTag Slot, FName& OutRemoved)
{
	OutRemoved = GetInstalled(Slot);
	if (OutRemoved.IsNone())
	{
		return false;
	}
	Installed.Remove(Slot);
	++Removals;
	++Version;
	ApplyEffects();
	UE_LOG(LogTemp, Display, TEXT("UGTPartSlotsComponent: removed %s from %s"), *OutRemoved.ToString(), *SlotName(Slot));
	return true;
}

float UGTPartSlotsComponent::GetResistance(FGameplayTag Tag) const
{
	float Total = 0.f;
	for (const TPair<FGameplayTag, FName>& Pair : Installed)
	{
		const UGTPartDefinition* Part = Registry() ? Registry()->FindPart(Pair.Value) : nullptr;
		if (!Part)
		{
			continue;
		}
		for (const FGTResistance& R : Part->Resistances)
		{
			if (R.Tag == Tag)
			{
				Total += R.Strength;
			}
		}
	}
	for (const FTemporary& T : Temporaries)
	{
		if (T.Tag == Tag)
		{
			Total += T.Strength;
		}
	}
	return FMath::Clamp(Total, 0.f, 1.f);
}

void UGTPartSlotsComponent::AddTemporaryResistance(FGameplayTag Tag, float Strength, float Seconds)
{
	if (!Tag.IsValid() || Strength <= 0.f || Seconds <= 0.f)
	{
		return;
	}
	FTemporary T;
	T.Tag = Tag;
	T.Strength = Strength;
	T.TimeLeft = Seconds;
	Temporaries.Add(T);
	ApplyEffects();
}

void UGTPartSlotsComponent::Update(float DeltaSeconds)
{
	bool bChanged = false;
	for (int32 Index = Temporaries.Num() - 1; Index >= 0; --Index)
	{
		Temporaries[Index].TimeLeft -= DeltaSeconds;
		if (Temporaries[Index].TimeLeft <= 0.f)
		{
			Temporaries.RemoveAt(Index);
			bChanged = true;
		}
	}
	if (bChanged)
	{
		ApplyEffects();
	}
}

void UGTPartSlotsComponent::ApplyEffects()
{
	AGTCarPawn* Car = Cast<AGTCarPawn>(GetOwner());
	if (!Car || !bBegun)
	{
		return;
	}
	// Resistances: Hazard.* into the condition, Env.* into the environment.
	if (UGTConditionComponent* Condition = Car->GetCondition())
	{
		Condition->HazardResistance.Reset();
		for (const FGameplayTag& Tag : { GTTags::Hazard_Weather.GetTag(), GTTags::Hazard_Radiation.GetTag() })
		{
			const float R = GetResistance(Tag);
			if (R > 0.f)
			{
				Condition->HazardResistance.Add(Tag, R);
			}
		}
		// Tank capacity from the tank part. With no tank the fuel stays where it is, so refitting a tank does not
		// empty it; ModifyTuning takes the drive away instead.
		if (const UGTPartDefinition* Tank = GetInstalledPart(GTTags::Slot_FuelTank))
		{
			Condition->TankCapacityLitres = Tank->TankCapacityLitres;
			Condition->FuelLitres = FMath::Min(Condition->FuelLitres, Condition->TankCapacityLitres);
		}
	}
	if (UGTEnvironmentComponent* Environment = Car->GetEnvironment())
	{
		Environment->Resistance.Reset();
		for (const FGameplayTag& Tag : { GTTags::Env_Cold.GetTag(), GTTags::Env_Heat.GetTag(), GTTags::Env_Dust.GetTag() })
		{
			const float R = GetResistance(Tag);
			if (R > 0.f)
			{
				Environment->Resistance.Add(Tag, R);
			}
		}
	}
	if (UGTWinchComponent* Winch = Car->GetWinch())
	{
		const UGTPartDefinition* Gadget = GetInstalledPart(GTTags::Slot_Gadget);
		const bool bWinch = Gadget && Gadget->WinchPullN > 0.f;
		Winch->bEnabled = bWinch;
		if (bWinch)
		{
			Winch->PullForceN = Gadget->WinchPullN;
		}
	}
	RebuildVisuals();
}

void UGTPartSlotsComponent::ModifyTuning(FGTVehicleTuning& Tuning) const
{
	for (const TPair<FGameplayTag, FName>& Pair : Installed)
	{
		const UGTPartDefinition* Part = Registry() ? Registry()->FindPart(Pair.Value) : nullptr;
		if (!Part)
		{
			continue;
		}
		Tuning.TorqueScale *= Part->TorqueScale;
		Tuning.DragCoefficient += Part->DragDelta;
		Tuning.RollingScale *= Part->RollingResistanceScale;
		for (FGTWheelTuning& Wheel : Tuning.Wheels)
		{
			Wheel.FrictionScale *= Part->GripScale;
		}
	}
	// No engine, or no tank to feed it: no drive.
	if (GetInstalled(GTTags::Slot_Engine).IsNone() || GetInstalled(GTTags::Slot_FuelTank).IsNone())
	{
		Tuning.TorqueScale = 0.f;
	}
}

TArray<FGTTimedResistance> UGTPartSlotsComponent::GetTemporaryResistances() const
{
	TArray<FGTTimedResistance> Result;
	for (const FTemporary& T : Temporaries)
	{
		FGTTimedResistance R;
		R.Tag = T.Tag;
		R.Strength = T.Strength;
		R.SecondsLeft = T.TimeLeft;
		Result.Add(R);
	}
	return Result;
}

void UGTPartSlotsComponent::RebuildVisuals()
{
	for (UStaticMeshComponent* Visual : Visuals)
	{
		if (Visual)
		{
			Visual->DestroyComponent();
		}
	}
	Visuals.Reset();
	if (!bShowGreyboxVisuals)
	{
		return;
	}
	AGTCarPawn* Car = Cast<AGTCarPawn>(GetOwner());
	USkeletalMeshComponent* Mesh = Car ? Car->GetMesh() : nullptr;
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (!Mesh || !Cube)
	{
		return;
	}
	for (const TPair<FGameplayTag, FName>& Pair : Installed)
	{
		const UGTPartDefinition* Part = Registry() ? Registry()->FindPart(Pair.Value) : nullptr;
		if (!Part || Part->GreyboxSize.IsNearlyZero())
		{
			continue;
		}
		UStaticMeshComponent* Visual = NewObject<UStaticMeshComponent>(Car, NAME_None, RF_Transient);
		Visual->SetStaticMesh(Cube);
		Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Visual->SetCastShadow(false);
		Visual->SetupAttachment(Mesh);
		Visual->SetRelativeLocation(Part->GreyboxLocation);
		Visual->SetRelativeScale3D(Part->GreyboxSize / 100.f);
		Visual->RegisterComponent();
		GTGreybox::ApplyPropColour(Visual, Car, Part->GreyboxColour);
		Visuals.Add(Visual);
	}
}

TArray<FGTSlotEntry> UGTPartSlotsComponent::GetLoadout() const
{
	TArray<FGTSlotEntry> Loadout;
	for (const FGameplayTag& Slot : Slots)
	{
		const FName Id = GetInstalled(Slot);
		if (!Id.IsNone())
		{
			FGTSlotEntry E;
			E.Slot = Slot;
			E.PartId = Id;
			Loadout.Add(E);
		}
	}
	return Loadout;
}

void UGTPartSlotsComponent::ApplyLoadout(const TArray<FGTSlotEntry>& Loadout, bool bResetHealth)
{
	Installed.Reset();
	for (const FGTSlotEntry& E : Loadout)
	{
		if (E.Slot.IsValid() && !E.PartId.IsNone())
		{
			Installed.Add(E.Slot, E.PartId);
		}
	}
	if (bResetHealth)
	{
		if (const AGTCarPawn* Car = Cast<AGTCarPawn>(GetOwner()))
		{
			if (UGTConditionComponent* Condition = Car->GetCondition())
			{
				Condition->RepairAll();
			}
		}
	}
	++Version;
	ApplyEffects();
}

const TCHAR* UGTPartSlotsComponent::ReasonName(EGTFitReason Reason)
{
	switch (Reason)
	{
	case EGTFitReason::Fits:          return TEXT("fits");
	case EGTFitReason::UnknownItem:   return TEXT("unknown item");
	case EGTFitReason::NotAPart:      return TEXT("not a part");
	case EGTFitReason::NoSuchSlot:    return TEXT("no such slot");
	case EGTFitReason::NeedsProvider: return TEXT("needs a provider");
	default:                          return TEXT("?");
	}
}

FString UGTPartSlotsComponent::SlotName(FGameplayTag Slot)
{
	FString Name = Slot.ToString();
	Name.RemoveFromStart(TEXT("Slot."));
	return Name;
}

FString UGTPartSlotsComponent::Describe() const
{
	FString Result;
	for (const FGameplayTag& Slot : Slots)
	{
		const FName Id = GetInstalled(Slot);
		Result += FString::Printf(TEXT(" %s=%s"), *SlotName(Slot), Id.IsNone() ? TEXT("-") : *Id.ToString());
	}
	return FString::Printf(TEXT("parts:%s temporaries=%d resist cold=%.1f heat=%.1f dust=%.1f weather=%.1f radiation=%.1f"), *Result, Temporaries.Num(),
		GetResistance(GTTags::Env_Cold), GetResistance(GTTags::Env_Heat), GetResistance(GTTags::Env_Dust), GetResistance(GTTags::Hazard_Weather), GetResistance(GTTags::Hazard_Radiation));
}
