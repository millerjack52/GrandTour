#include "Parts/GTItemDefinition.h"

#include "GameplayTagsManager.h"

FString UGTItemDefinition::Describe() const
{
	return FString::Printf(TEXT("%s '%s' kind=%d %.1f kg price=%d%s"), *ItemId.ToString(), *DisplayName.ToString(), static_cast<int32>(Kind), WeightKg, BasePrice, bTraderStocks ? TEXT(" stocked") : TEXT(""));
}

UGTPartDefinition::UGTPartDefinition()
{
	Kind = EGTItemKind::Part;
}

FString UGTPartDefinition::Describe() const
{
	FString Resist;
	for (const FGTResistance& R : Resistances)
	{
		Resist += FString::Printf(TEXT(" %s=%.1f"), *R.Tag.ToString(), R.Strength);
	}
	return FString::Printf(TEXT("%s slot=%s tier=%d torque=%.2f grip=%.2f tank=%.0f winch=%.0f resist=[%s] owns=%d"),
		*UGTItemDefinition::Describe(), *Slot.ToString(), Tier, TorqueScale, GripScale, TankCapacityLitres, WinchPullN, *Resist.TrimStart(), OwnedParts.Num());
}

UGTConsumableDefinition::UGTConsumableDefinition()
{
	Kind = EGTItemKind::Consumable;
}

FString UGTConsumableDefinition::Describe() const
{
	return FString::Printf(TEXT("%s resist=%s %.1f for %.0f s heat=%d clog=%d exposure=%.0f fuel=%.0f"),
		*UGTItemDefinition::Describe(), *ResistanceTag.ToString(), ResistanceStrength, DurationSeconds, bResetHeat ? 1 : 0, bResetClog ? 1 : 0, ExposureRestore, FuelLitres);
}

namespace GTItemDefaults
{
	namespace
	{
		const FLinearColor Steel(0.55f, 0.55f, 0.58f);
		const FLinearColor Rubber(0.12f, 0.12f, 0.12f);
		const FLinearColor Copper(0.7f, 0.4f, 0.2f);
		const FLinearColor Paper(0.8f, 0.78f, 0.7f);
		const FLinearColor Alloy(0.3f, 0.9f, 0.35f);
		const FLinearColor Blue(0.2f, 0.4f, 0.9f);

		const FResource ResourceRows[] = {
			{TEXT("Scrap"),     TEXT("Scrap metal"), 2.0f, 5,   true,  Steel},
			{TEXT("Wire"),      TEXT("Wire"),        0.5f, 4,   true,  Copper},
			{TEXT("Bolts"),     TEXT("Bolts"),       0.2f, 2,   true,  Steel},
			{TEXT("RareAlloy"), TEXT("Rare alloy"),  4.0f, 150, false, Alloy},
		};

		const TArray<EGTCarPart> NoParts;
		const TArray<EGTCarPart> EngineParts = { EGTCarPart::Engine };
		const TArray<EGTCarPart> RadiatorParts = { EGTCarPart::Radiator };
		const TArray<EGTCarPart> SuspensionParts = { EGTCarPart::SuspensionFL, EGTCarPart::SuspensionFR, EGTCarPart::SuspensionRL, EGTCarPart::SuspensionRR };
		const TArray<EGTCarPart> TyreParts = { EGTCarPart::TyreFL, EGTCarPart::TyreFR, EGTCarPart::TyreRL, EGTCarPart::TyreRR };
		const TArray<EGTCarPart> TankParts = { EGTCarPart::FuelTank };
		const TArray<EGTCarPart> WinchParts = { EGTCarPart::Winch };

		// id, name, slot, tier, kg, price, stocked, torque, drag, grip, rolling, tank, winch, resist tag, resist, damage scale, owned, location, size, colour
		const FPart PartRows[] = {
			{TEXT("Part.DriveFactory"), TEXT("Factory drive layout"), TEXT("Slot.DriveLayout"), 1, 0.f, 0, true, 1.f, 0.f, 1.f, 1.f, 0.f, 0.f, nullptr, 0.f, 1.f, NoParts, FVector::ZeroVector, FVector::ZeroVector, Steel},
			{TEXT("Part.DriveFWD"), TEXT("FWD conversion"), TEXT("Slot.DriveLayout"), 1, 0.f, 600, true, 1.f, 0.f, 1.f, 1.f, 0.f, 0.f, nullptr, 0.f, 1.f, NoParts, FVector::ZeroVector, FVector::ZeroVector, Steel},
			{TEXT("Part.DriveRWD"), TEXT("RWD conversion"), TEXT("Slot.DriveLayout"), 1, 0.f, 600, true, 1.f, 0.f, 1.f, 1.f, 0.f, 0.f, nullptr, 0.f, 1.f, NoParts, FVector::ZeroVector, FVector::ZeroVector, Steel},
			{TEXT("Part.DriveAWD"), TEXT("AWD conversion"), TEXT("Slot.DriveLayout"), 1, 0.f, 1000, true, 1.f, 0.f, 1.f, 1.f, 0.f, 0.f, nullptr, 0.f, 1.f, NoParts, FVector::ZeroVector, FVector::ZeroVector, Steel},

			{TEXT("Part.RREngineRally"), TEXT("Range Rover Rally drivetrain"), TEXT("Slot.Engine"), 2, 150.f, 950, true, 1.f, 0.f, 1.f, 1.f, 0.f, 0.f, nullptr, 0.f, 1.f, EngineParts, FVector(120.f,0.f,85.f), FVector(60.f,50.f,45.f), Steel},
			{TEXT("Part.RREngineExpedition"), TEXT("Range Rover Expedition drivetrain"), TEXT("Slot.Engine"), 2, 150.f, 900, true, 1.f, 0.f, 1.f, 1.f, 0.f, 0.f, nullptr, 0.f, 1.f, EngineParts, FVector(120.f,0.f,85.f), FVector(60.f,50.f,45.f), Steel},
			{TEXT("Part.Engine"),        TEXT("Engine (M)"),        TEXT("Slot.Engine"),     1, 150.f, 300, true,  1.00f, 0.f,   1.f,   1.f,  0.f,   0.f,     nullptr,             0.f,  1.f,  EngineParts,     FVector(120.f, 0.f, 85.f),    FVector(60.f, 50.f, 45.f), Steel},
			{TEXT("Part.EngineL"),       TEXT("Engine (L)"),        TEXT("Slot.Engine"),     2, 190.f, 650, true,  1.25f, 0.f,   1.f,   1.f,  0.f,   0.f,     nullptr,             0.f,  1.f,  EngineParts,     FVector(120.f, 0.f, 88.f),    FVector(70.f, 56.f, 52.f), Steel},
			{TEXT("Part.Radiator"),      TEXT("Radiator"),          TEXT("Slot.Radiator"),   1, 8.f,   80,  true,  1.f,   0.f,   1.f,   1.f,  0.f,   0.f,     nullptr,             0.f,  1.f,  RadiatorParts,   FVector(195.f, 0.f, 80.f),    FVector(8.f, 60.f, 40.f),  Copper},
			{TEXT("Part.RadiatorBig"),   TEXT("Big radiator"),      TEXT("Slot.Radiator"),   2, 12.f,  180, true,  1.f,   0.f,   1.f,   1.f,  0.f,   0.f,     TEXT("Env.Heat"),    0.5f, 1.f,  RadiatorParts,   FVector(195.f, 0.f, 80.f),    FVector(10.f, 70.f, 48.f), Copper},
			{TEXT("Part.AirFilter"),     TEXT("Air filter"),        TEXT("Slot.AirFilter"),  1, 2.f,   60,  true,  1.f,   0.f,   1.f,   1.f,  0.f,   0.f,     TEXT("Env.Dust"),    0.6f, 1.f,  NoParts,         FVector(150.f, 35.f, 108.f),  FVector(22.f, 22.f, 14.f), Paper},
			{TEXT("Part.Heater"),        TEXT("Cabin heater"),      TEXT("Slot.Heater"),     1, 5.f,   120, true,  1.f,   0.f,   1.f,   1.f,  0.f,   0.f,     TEXT("Env.Cold"),    0.7f, 1.f,  NoParts,         FVector(70.f, 0.f, 95.f),     FVector(20.f, 30.f, 14.f), Steel},
			{TEXT("Part.Suspension"),    TEXT("Suspension (stock)"),TEXT("Slot.Suspension"), 1, 60.f,  200, true,  1.f,   0.f,   1.f,   1.f,  0.f,   0.f,     nullptr,             0.f,  1.f,  SuspensionParts, FVector::ZeroVector,          FVector::ZeroVector,       Steel},
			{TEXT("Part.SuspensionHD"),  TEXT("Suspension (heavy duty)"), TEXT("Slot.Suspension"), 2, 75.f, 450, true, 1.f, 0.f, 1.f, 1.f, 0.f, 0.f,    nullptr,             0.f,  0.6f, SuspensionParts, FVector::ZeroVector,          FVector::ZeroVector,       Steel},
			{TEXT("Part.SuspensionTrail"),TEXT("Suspension (trail)"),TEXT("Slot.Suspension"), 2, 78.f, 520, true, 1.f, 0.f, 1.f, 1.f, 0.f, 0.f,    nullptr,             0.f,  0.7f, SuspensionParts, FVector::ZeroVector,          FVector::ZeroVector,       Steel},
			{TEXT("Part.Tyre"),          TEXT("Road tyres (set)"),  TEXT("Slot.Tyres"),      1, 48.f,  240, true,  1.f,   0.f,   1.f,   1.f,  0.f,   0.f,     nullptr,             0.f,  1.f,  TyreParts,       FVector::ZeroVector,          FVector::ZeroVector,       Rubber},
			{TEXT("Part.TyreKnobbly"),   TEXT("Knobbly tyres (set)"), TEXT("Slot.Tyres"),    2, 56.f,  400, true,  1.f,   0.f,   1.10f, 1.2f, 0.f,   0.f,     nullptr,             0.f,  1.f,  TyreParts,       FVector::ZeroVector,          FVector::ZeroVector,       Rubber},
			{TEXT("Part.TyreAllTerrain"),TEXT("All-terrain tyres (set)"),TEXT("Slot.Tyres"), 2, 52.f, 320, true, 1.f, 0.f, 1.05f, 1.1f, 0.f, 0.f, nullptr, 0.f, 1.f, TyreParts, FVector::ZeroVector, FVector::ZeroVector, Rubber},
			{TEXT("Part.FuelTank"),      TEXT("Fuel tank"),         TEXT("Slot.FuelTank"),   1, 20.f,  150, true,  1.f,   0.f,   1.f,   1.f,  81.f,  0.f,     nullptr,             0.f,  1.f,  TankParts,       FVector(-150.f, 0.f, 35.f),   FVector(50.f, 60.f, 20.f), Steel},
			{TEXT("Part.FuelTankLong"),  TEXT("Long-range tank"),   TEXT("Slot.FuelTank"),   2, 28.f,  350, true,  1.f,   0.f,   1.f,   1.f,  120.f, 0.f,     nullptr,             0.f,  1.f,  TankParts,       FVector(-150.f, 0.f, 35.f),   FVector(70.f, 70.f, 24.f), Steel},
			{TEXT("Part.Winch"),         TEXT("Winch"),             TEXT("Slot.Gadget"),     1, 30.f,  350, true,  1.f,   0.f,   1.f,   1.f,  0.f,   40000.f, nullptr,             0.f,  1.f,  WinchParts,      FVector(238.f, 0.f, 55.f),    FVector(18.f, 40.f, 20.f), Steel},
			{TEXT("Part.CabinSeal"),     TEXT("Sealed cabin"),      TEXT("Slot.Shielding"),  1, 15.f,  250, true,  1.f,   0.f,   1.f,   1.f,  0.f,   0.f,     TEXT("Hazard.Weather"), 0.5f, 1.f, NoParts,       FVector(0.f, 0.f, 150.f),     FVector(40.f, 40.f, 6.f),  Blue},
			{TEXT("Part.LeadLining"),    TEXT("Lead lining"),       TEXT("Slot.Shielding"),  2, 60.f,  400, true,  1.f,   0.f,   1.f,   1.f,  0.f,   0.f,     TEXT("Hazard.Radiation"), 0.6f, 1.f, NoParts,     FVector(0.f, 0.f, 150.f),     FVector(60.f, 60.f, 6.f),  Steel},
		};

		// id, name, kg, price, stocked, resist tag, resist, duration, heat, clog, exposure, fuel
		const FConsumable ConsumableRows[] = {
			{TEXT("FuelCan"),            TEXT("Fuel can"),        10.f, 30, true, nullptr,                  0.f,  0.f,   false, false, 0.f,  20.f},
			{TEXT("Use.CoolantFlush"),   TEXT("Coolant flush"),   1.f,  25, true, nullptr,                  0.f,  0.f,   true,  false, 0.f,  0.f},
			{TEXT("Use.FilterCleaner"),  TEXT("Filter cleaner"),  0.5f, 20, true, nullptr,                  0.f,  0.f,   false, true,  0.f,  0.f},
			{TEXT("Use.RadPills"),       TEXT("Rad pills"),       0.2f, 40, true, TEXT("Hazard.Radiation"), 0.5f, 120.f, false, false, 40.f, 0.f},
			{TEXT("Use.ThermalBlanket"), TEXT("Thermal blanket"), 1.5f, 35, true, TEXT("Env.Cold"),         0.6f, 300.f, false, false, 0.f,  0.f},
		};
	}

	TArrayView<const FResource> Resources() { return MakeArrayView(ResourceRows, UE_ARRAY_COUNT(ResourceRows)); }
	TArrayView<const FPart> Parts() { return MakeArrayView(PartRows, UE_ARRAY_COUNT(PartRows)); }
	TArrayView<const FConsumable> Consumables() { return MakeArrayView(ConsumableRows, UE_ARRAY_COUNT(ConsumableRows)); }

	static FGameplayTag Tag(const TCHAR* Name)
	{
		return Name ? UGameplayTagsManager::Get().RequestGameplayTag(FName(Name), /*ErrorIfNotFound*/ false) : FGameplayTag();
	}

	void Apply(UGTItemDefinition* Item, const FResource& Row)
	{
		Item->ItemId = Row.Id;
		Item->DisplayName = FText::FromString(Row.Name);
		Item->Kind = EGTItemKind::Resource;
		Item->WeightKg = Row.WeightKg;
		Item->BasePrice = Row.Price;
		Item->bTraderStocks = Row.bStocked;
		Item->GreyboxColour = Row.Colour;
	}

	void Apply(UGTPartDefinition* Part, const FPart& Row)
	{
		Part->ItemId = Row.Id;
		Part->DisplayName = FText::FromString(Row.Name);
		Part->Kind = EGTItemKind::Part;
		Part->WeightKg = Row.WeightKg;
		Part->BasePrice = Row.Price;
		Part->bTraderStocks = Row.bStocked;
		Part->GreyboxColour = Row.Colour;
		Part->Slot = Tag(Row.Slot);
		Part->Tier = Row.Tier;
		Part->TorqueScale = Row.Torque;
		Part->DragDelta = Row.Drag;
		Part->GripScale = Row.Grip;
		Part->RollingResistanceScale = Row.Rolling;
		Part->TankCapacityLitres = Row.Tank;
		Part->WinchPullN = Row.Winch;
		Part->Resistances.Reset();
		if (Row.ResistTag)
		{
			FGTResistance R;
			R.Tag = Tag(Row.ResistTag);
			R.Strength = Row.Resist;
			Part->Resistances.Add(R);
		}
		Part->DamageScale = Row.DamageScale;
		Part->OwnedParts = Row.Owned;
		Part->GreyboxLocation = Row.Location;
		Part->GreyboxSize = Row.Size;
	}

	void Apply(UGTConsumableDefinition* Item, const FConsumable& Row)
	{
		Item->ItemId = Row.Id;
		Item->DisplayName = FText::FromString(Row.Name);
		Item->Kind = EGTItemKind::Consumable;
		Item->WeightKg = Row.WeightKg;
		Item->BasePrice = Row.Price;
		Item->bTraderStocks = Row.bStocked;
		Item->ResistanceTag = Tag(Row.ResistTag);
		Item->ResistanceStrength = Row.Resist;
		Item->DurationSeconds = Row.Duration;
		Item->bResetHeat = Row.bHeat;
		Item->bResetClog = Row.bClog;
		Item->ExposureRestore = Row.Exposure;
		Item->FuelLitres = Row.Fuel;
	}

	FString AssetName(const TCHAR* Id)
	{
		return TEXT("DA_Item_") + FString(Id).Replace(TEXT("."), TEXT("_"));
	}
}
