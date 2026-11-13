#include "Core/GTM4TestRunner.h"

#include "Base/GTBaseGameMode.h"
#include "Base/GTDepartGate.h"
#include "Character/GTExposureComponent.h"
#include "Character/GTPlayerCharacter.h"
#include "Core/GTGameplayTags.h"
#include "Core/GTPlayerController.h"
#include "Core/GTRunSubsystem.h"
#include "Crafting/GTCraftingStation.h"
#include "Environment/GTEnvironmentComponent.h"
#include "Interaction/GTInteractionComponent.h"
#include "Inventory/GTInventoryComponent.h"
#include "Parts/GTItemRegistry.h"
#include "Parts/GTPartSlotsComponent.h"
#include "Run/GTLegActors.h"
#include "Run/GTRunGameMode.h"
#include "Run/GTRunGameState.h"
#include "Vehicle/GTBodyComponent.h"
#include "Vehicle/GTBodyStateComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"

#include "Camera/CameraActor.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "GameFramework/HUD.h"
#include "HAL/FileManager.h"
#include "Misc/App.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#endif
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"

namespace
{
	const FName PartRadiator(TEXT("Part.Radiator"));
	const FName PartHeater(TEXT("Part.Heater"));
	const FName UseFlush(TEXT("Use.CoolantFlush"));
	const FName UseBlanket(TEXT("Use.ThermalBlanket"));
	const FName RecipeRadiator(TEXT("Radiator"));
	const FName UpgradeScout1(TEXT("Scout1"));
}

namespace
{
	/** A point just inside a door's shut outer skin at its middle, in world space: the doorway once the door is open. */
	FVector DoorwayPoint(const AGTCarPawn* Car, const UGTBodyComponent* Body, int32 Door)
	{
		const FBox B = Body->GetDoorClosedBounds(Door);
		const bool bLeft = Body->IsDoorLeft(Door);
		return Car->GetMesh()->GetComponentTransform().TransformPosition(FVector(B.GetCenter().X, (bLeft ? B.Min.Y : B.Max.Y) + (bLeft ? 6.f : -6.f), B.GetCenter().Z));
	}
}

FGTM4TestRunner::FGTM4TestRunner(UWorld* InWorld, EGTM4Test InKind)
	: World(InWorld), Kind(InKind)
{
}

void FGTM4TestRunner::Log(const FString& Line) const
{
	UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST m4 t=%.1f step %d: %s"), Elapsed, Step, *Line);
}

void FGTM4TestRunner::Finish(bool bInPass, const FString& InSummary)
{
	bDone = true;
	bPass = bInPass;
	Summary = InSummary;
}

void FGTM4TestRunner::Next()
{
	++Step;
	StepTime = 0.f;
	bStepStarted = false;
}

bool FGTM4TestRunner::StepTimedOut(float Seconds, const TCHAR* What)
{
	if (StepTime > Seconds)
	{
		Fail(FString::Printf(TEXT("timed out waiting for %s"), What));
		return true;
	}
	return false;
}

FVector FGTM4TestRunner::CarLocal(const FVector& Local) const
{
	return Car.IsValid() ? Car->GetMesh()->GetComponentTransform().TransformPosition(Local) : Local;
}

void FGTM4TestRunner::TeleportCar(const FVector& Location)
{
	if (!Car.IsValid())
	{
		return;
	}
	Car->SetActorLocation(Location, false, nullptr, ETeleportType::TeleportPhysics);
	Car->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
	Car->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
	if (UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement())
	{
		Move->SetThrottleInput(0.f);
		Move->SetHandbrakeInput(true);
	}
}

bool FGTM4TestRunner::ExitCar()
{
	if (!PC.IsValid())
	{
		return false;
	}
	if (!PC->IsDriving())
	{
		Character = PC->GetPlayerCharacter();
		return Character.IsValid();
	}
	if (!PC->ExitCar())
	{
		return false;
	}
	Character = PC->GetPlayerCharacter();
	if (Character.IsValid())
	{
		Character->DisableInput(PC.Get());
	}
	return Character.IsValid();
}

bool FGTM4TestRunner::EnterCar()
{
	if (!PC.IsValid() || !Car.IsValid() || !Character.IsValid())
	{
		return false;
	}
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	Character->SetActorLocation(Car->FindExitLocation(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight()), false, nullptr, ETeleportType::TeleportPhysics);
	const bool bEntered = PC->EnterCar();
	Car->DisableInput(PC.Get());
	Car->ResetDrivingInputs();
	return bEntered;
}

template <typename T>
T* FGTM4TestRunner::FindActor() const
{
	for (TActorIterator<T> It(World.Get()); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

bool FGTM4TestRunner::HasRow(AGTCraftingStation* Station, int32 Action, FName Payload, bool& bOutEnabled, FString& OutText) const
{
	if (!Station || !Character.IsValid())
	{
		return false;
	}
	TArray<FGTScreenRow> Rows;
	Station->BuildRows(Character.Get(), Rows);
	for (const FGTScreenRow& Row : Rows)
	{
		if (Row.bHeader || Row.Action != Action || (!Payload.IsNone() && Row.Payload != Payload))
		{
			continue;
		}
		bOutEnabled = Row.bEnabled;
		OutText = Row.Text + (Row.Hint.IsEmpty() ? TEXT("") : TEXT(" | ") + Row.Hint);
		return true;
	}
	return false;
}

bool FGTM4TestRunner::ActRow(AGTCraftingStation* Station, int32 Action, FName Payload, FString& OutText)
{
	if (!Station || !Character.IsValid())
	{
		return false;
	}
	TArray<FGTScreenRow> Rows;
	Station->BuildRows(Character.Get(), Rows);
	for (int32 Index = 0; Index < Rows.Num(); ++Index)
	{
		const FGTScreenRow& Row = Rows[Index];
		if (Row.bHeader || Row.Action != Action || (!Payload.IsNone() && Row.Payload != Payload))
		{
			continue;
		}
		OutText = Row.Text + (Row.Hint.IsEmpty() ? TEXT("") : TEXT(" | ") + Row.Hint);
		return Row.bEnabled && Station->ActOnRow(Character.Get(), Index);
	}
	OutText = TEXT("(no such row)");
	return false;
}

bool FGTM4TestRunner::Setup()
{
	PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(World.Get(), 0));
	Car = PC.IsValid() ? (PC->GetCar() ? PC->GetCar() : Cast<AGTCarPawn>(PC->GetPawn())) : nullptr;
	if (!PC.IsValid() || !Car.IsValid())
	{
		Fail(TEXT("player 0 is not an AGTPlayerController with an AGTCarPawn"));
		return false;
	}
	Car->DisableInput(PC.Get());
	Car->ResetDrivingInputs();
	Character = PC->GetPlayerCharacter();
	if (Character.IsValid())
	{
		Character->DisableInput(PC.Get());
	}
	Run = World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UGTRunSubsystem>() : nullptr;
	if (!Run.IsValid())
	{
		Fail(TEXT("no UGTRunSubsystem"));
		return false;
	}
	const UGTItemRegistry* Registry = UGTItemRegistry::Get(World.Get());
	bAssets = Registry && Registry->ItemsFromAssets > 0;
	Log(FString::Printf(TEXT("car at %s driving=%d registry=%s | %s"), *Car->GetActorLocation().ToCompactString(), PC->IsDriving() ? 1 : 0,
		Registry ? *Registry->Describe() : TEXT("none"), *Run->Describe()));
	return true;
}

bool FGTM4TestRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
{
	if (bDone)
	{
		bOutPass = bPass;
		OutSummary = Summary;
		return true;
	}
	Elapsed += DeltaSeconds;
	if (Step < 0)
	{
		if (Elapsed < 0.5f)
		{
			return false;
		}
		if (!Setup())
		{
			bOutPass = bPass;
			OutSummary = Summary;
			return true;
		}
		Next();
	}
	StepTime += DeltaSeconds;
	if (!Car.IsValid() || !PC.IsValid())
	{
		Fail(TEXT("car or controller vanished"));
	}
	else if (Kind == EGTM4Test::Base)
	{
		TickBase(DeltaSeconds);
	}
	else if (Kind == EGTM4Test::Loop)
	{
		TickLoop(DeltaSeconds);
	}
	else if (Kind == EGTM4Test::Screenshots)
	{
		TickScreenshots(DeltaSeconds);
	}
	else
	{
		TickDoors(DeltaSeconds);
	}
	if (Elapsed > ((Kind == EGTM4Test::Screenshots || Kind == EGTM4Test::Doors) ? 300.f : 90.f) && !bDone)
	{
		Fail(FString::Printf(TEXT("overall timeout at step %d"), Step));
	}
	bOutPass = bPass;
	OutSummary = Summary;
	return bDone;
}

// ---- base --------------------------------------------------------------------------------------------

void FGTM4TestRunner::TickBase(float DeltaSeconds)
{
	UGTConditionComponent* Condition = Car->GetCondition();
	UGTPartSlotsComponent* Parts = Car->GetParts();
	FString Text;
	switch (Step)
	{
	case 0:   // a clean campaign, the stations beside the car, some stock, some damage, on foot
	{
		// The car spawns above the floor: wait for it to land and stop, since the exit spot and the doorway check read its pose.
		if (StepTime < 1.5f || Car->GetVelocity().Size() > 10.f)
		{
			StepTimedOut(8.f, TEXT("the car to settle"));
			break;
		}
		Run->ResetCampaign();
		Run->DeleteSave();
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		const FRotator Facing = Car->GetActorRotation();
		Workbench = World->SpawnActor<AGTWorkbench>(AGTWorkbench::StaticClass(), CarLocal(FVector(600.f, 400.f, 45.f)), Facing, Params);
		Lift = World->SpawnActor<AGTCarLift>(AGTCarLift::StaticClass(), CarLocal(FVector(0.f, 800.f, 10.f)), Facing, Params);
		Trader = World->SpawnActor<AGTTrader>(AGTTrader::StaticClass(), CarLocal(FVector(600.f, -400.f, 50.f)), Facing, Params);
		Crew = World->SpawnActor<AGTCrewTent>(AGTCrewTent::StaticClass(), CarLocal(FVector(-800.f, 600.f, 110.f)), Facing, Params);
		Briefing = World->SpawnActor<AGTBriefingBoard>(AGTBriefingBoard::StaticClass(), CarLocal(FVector(800.f, 0.f, 55.f)), Facing, Params);
		if (!Workbench.IsValid() || !Lift.IsValid() || !Trader.IsValid() || !Crew.IsValid() || !Briefing.IsValid())
		{
			Fail(TEXT("could not spawn the stations"));
			return;
		}
		// A 20 cm slab on the driver's side with its edge 25 cm short of the exit spot behind the door, like the lift's
		// edge when the car is parked off-centre: getting out must stand you on it, not send you to the passenger side.
		float SlabGroundZ = 0.f;
		{
			// 30 cm wide, Y -150..-120: the outer edge blocks the exit spot, the inner edge stays clear of the rear-left wheel's
			// 38 cm ground sweep at Y -78 so the slab never lifts the car.
			FVector SlabAt = CarLocal(FVector(-34.5f, -135.f, 0.f));
			FHitResult Ground;
			FCollisionQueryParams GroundParams(SCENE_QUERY_STAT(GTStepSlab), false, Car.Get());
			if (World->LineTraceSingleByChannel(Ground, SlabAt + FVector(0.f, 0.f, 300.f), SlabAt - FVector(0.f, 0.f, 500.f), ECC_Visibility, GroundParams))
			{
				SlabAt.Z = Ground.ImpactPoint.Z;
			}
			SlabGroundZ = SlabAt.Z;
			// The scale rides in the spawn transform so the slab never registers as a 1 m cube against the car.
			const FTransform SlabXf(Facing, SlabAt + FVector(0.f, 0.f, 10.f), FVector(3.f, 0.3f, 0.2f));
			if (AGTCarLift* Slab = World->SpawnActorDeferred<AGTCarLift>(AGTCarLift::StaticClass(), SlabXf, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn))
			{
				Slab->GreyboxSize = FVector(300.f, 30.f, 20.f);
				Slab->FinishSpawning(SlabXf);
			}
		}
		if (!ExitCar())
		{
			Fail(TEXT("could not get out of the car"));
			return;
		}
		// On the driver's side and lifted by the step: a spot placed at ground level puts the capsule centre half height + 2 cm
		// above the floor (98); resting its rounded foot on the slab's edge, 25 cm in from the axis, lifts it about 8 cm more.
		ExitLocal = Car->GetMesh()->GetComponentTransform().InverseTransformPosition(Character->GetActorLocation());
		const float StandHeight = Character->GetActorLocation().Z - SlabGroundZ;
		const float GroundLevel = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.f;
		bExitBesideStep = ExitLocal.Y < -150.f && ExitLocal.X < 0.f && StandHeight > GroundLevel + 3.f;
		Log(FString::Printf(TEXT("out beside a 20 cm step at car-space %s, capsule centre %.1f cm above the floor (ground level %.1f) -> driver's side on the step=%d"),
			*ExitLocal.ToCompactString(), StandHeight, GroundLevel, bExitBesideStep ? 1 : 0));
		UGTInventoryComponent* Bag = Character->GetInventory();
		Bag->Items.Reset();
		Bag->Add(GTItems::Scrap, 12);
		Bag->Add(GTItems::Bolts, 4);
		Bag->Add(GTItems::Wire, 5);
		Car->GetBoot()->Items.Reset();
		Condition->SetPartHealth(EGTCarPart::Engine, 0.5f);
		Condition->SetPartHealth(EGTCarPart::Radiator, 0.4f);
		if (Car->GetBodyState())
		{
			Car->GetBodyState()->Wetness = 0.7f;
		}
		Log(FString::Printf(TEXT("stations up; bag %s; engine 0.5 radiator 0.4 wet 0.7; %s"), *Bag->Describe(), *Parts->Describe()));
		Next();
		break;
	}
	case 1:   // workbench: a radiator from scrap and bolts
	{
		bCrafted = ActRow(Workbench.Get(), 1, RecipeRadiator, Text);
		ScrapAfterCraft = Character->GetInventory()->CountOf(GTItems::Scrap);
		Log(FString::Printf(TEXT("craft radiator: %s -> ok=%d bag %s"), *Text, bCrafted ? 1 : 0, *Character->GetInventory()->Describe()));
		Next();
		break;
	}
	case 2:   // lift: install the new radiator, repair everything, wash
	{
		bInstalledRadiator = ActRow(Lift.Get(), AGTCarLift::Install, PartRadiator, Text);
		RadiatorAfterInstall = Condition->GetPartHealth(EGTCarPart::Radiator);
		BootRadiators = Car->GetBoot()->CountOf(PartRadiator);
		Log(FString::Printf(TEXT("install: %s -> ok=%d radiator=%.2f bootRadiators=%d"), *Text, bInstalledRadiator ? 1 : 0, RadiatorAfterInstall, BootRadiators));
		RepairCostSeen = Lift->RepairCost(Car.Get());
		const bool bRepaired = ActRow(Lift.Get(), AGTCarLift::Repair, NAME_None, Text);
		EngineAfterRepair = Condition->GetPartHealth(EGTCarPart::Engine);
		Log(FString::Printf(TEXT("repair (cost %d): %s -> ok=%d engine=%.2f scrap=%d"), RepairCostSeen, *Text, bRepaired ? 1 : 0, EngineAfterRepair, Character->GetInventory()->CountOf(GTItems::Scrap)));
		const bool bWashed = ActRow(Lift.Get(), AGTCarLift::Wash, NAME_None, Text);
		WetAfterWash = Car->GetBodyState() ? Car->GetBodyState()->Wetness : -1.f;
		Log(FString::Printf(TEXT("wash: ok=%d wet=%.2f"), bWashed ? 1 : 0, WetAfterWash));
		Next();
		break;
	}
	case 3:   // trader: sell the wire, buy a heater, install it
	{
		for (int32 Index = 0; Index < 5; ++Index)
		{
			ActRow(Trader.Get(), AGTTrader::Sell, GTItems::Wire, Text);
		}
		CurrencyAfterSell = Run->GetCurrency();
		Log(FString::Printf(TEXT("sold 5 wire: credits=%d wire=%d"), CurrencyAfterSell, Character->GetInventory()->CountOf(GTItems::Wire)));
		const bool bBought = ActRow(Trader.Get(), AGTTrader::Buy, PartHeater, Text);
		CurrencyAfterBuy = Run->GetCurrency();
		Log(FString::Printf(TEXT("buy heater: %s -> ok=%d credits=%d"), *Text, bBought ? 1 : 0, CurrencyAfterBuy));
		bHeaterInstalled = ActRow(Lift.Get(), AGTCarLift::Install, PartHeater, Text);
		ColdResistance = Parts->GetResistance(GTTags::Env_Cold);
		const float* EnvCold = Car->GetEnvironment()->Resistance.Find(GTTags::Env_Cold);
		Log(FString::Printf(TEXT("install heater: %s -> ok=%d coldResistance=%.2f env=%.2f %s"), *Text, bHeaterInstalled ? 1 : 0, ColdResistance, EnvCold ? *EnvCold : -1.f, *Parts->Describe()));
		Next();
		break;
	}
	case 4:   // crew: refused without credits, bought with them; the briefing shows peaks
	{
		bool bEnabled = true;
		HasRow(Crew.Get(), 1, UpgradeScout1, bEnabled, Text);
		bScoutRefused = !bEnabled && !ActRow(Crew.Get(), 1, UpgradeScout1, Text);
		Log(FString::Printf(TEXT("scout with %d credits: %s -> refused=%d"), Run->GetCurrency(), *Text, bScoutRefused ? 1 : 0));
		Run->AddCurrency(100);
		const bool bBought = ActRow(Crew.Get(), 1, UpgradeScout1, Text);
		ScoutTier = Run->GetCrewTier(GTTags::Crew_Scout);
		TArray<FGTScreenRow> Rows;
		Briefing->BuildRows(Character.Get(), Rows);
		FString Board;
		for (const FGTScreenRow& Row : Rows)
		{
			Board += Row.Text + TEXT(" / ");
			bBriefingPeak |= Row.Text.Contains(TEXT("peak"));
		}
		Log(FString::Printf(TEXT("scout bought=%d tier=%d credits=%d; briefing: %s"), bBought ? 1 : 0, ScoutTier, Run->GetCurrency(), *Board));
		Next();
		break;
	}
	case 5:   // consumables: a flush clears the heat, a blanket adds cold resistance to car and player
	{
		Character->GetInventory()->Add(UseFlush, 1);
		Character->GetInventory()->Add(UseBlanket, 1);
		Car->GetEnvironment()->Heat = 0.8f;
		const bool bFlushed = Character->UseConsumable(UseFlush);
		HeatAfterFlush = Car->GetEnvironment()->Heat;
		const bool bBlanket = Character->UseConsumable(UseBlanket);
		ColdResistanceWithBlanket = Parts->GetResistance(GTTags::Env_Cold);
		OwnColdResistance = Character->GetResistance(GTTags::Env_Cold);
		Log(FString::Printf(TEXT("flush=%d heat=%.2f blanket=%d carCold=%.2f ownCold=%.2f used=%d bag %s"), bFlushed ? 1 : 0, HeatAfterFlush, bBlanket ? 1 : 0,
			ColdResistanceWithBlanket, OwnColdResistance, Character->ConsumablesUsed, *Character->GetInventory()->Describe()));
		Next();
		break;
	}
	case 6:   // the review fixes: required slots, free repairs, room, the cursor, a no-op consumable, the doorway above the door skin
	{
		UGTInventoryComponent* BagInventory = Character->GetInventory();
		UGTInventoryComponent* BootInventory = Car->GetBoot();
		if (SubStep == 0)
		{
			bool bEnabled = true;
			// Required slots only swap.
			const FName EngineId(TEXT("Part.Engine"));
			HasRow(Lift.Get(), AGTCarLift::Remove, EngineId, bEnabled, Text);
			const bool bEngineRowDisabled = !bEnabled && Text.Contains(TEXT("replacement"));
			bRequiredSlotRefused = bEngineRowDisabled && !ActRow(Lift.Get(), AGTCarLift::Remove, EngineId, Text) && Parts->GetInstalled(GTTags::Slot_Engine) == EngineId;
			Log(FString::Printf(TEXT("engine remove: %s -> refused=%d"), *Text, bRequiredSlotRefused ? 1 : 0));

			// Mechanic II: repairs are free and still offered.
			Run->SetCrewTier(GTTags::Crew_Mechanic, 2);
			Condition->SetPartHealth(EGTCarPart::Engine, 0.5f);
			const int32 ScrapBeforeRepair = BagInventory->CountOf(GTItems::Scrap) + BootInventory->CountOf(GTItems::Scrap);
			const bool bRepairOffered = HasRow(Lift.Get(), AGTCarLift::Repair, NAME_None, bEnabled, Text) && bEnabled && Text.Contains(TEXT("free"));
			const FString RepairText = Text;
			const bool bRepaired = ActRow(Lift.Get(), AGTCarLift::Repair, NAME_None, Text);
			bFreeRepair = bRepairOffered && bRepaired && Condition->GetPartHealth(EGTCarPart::Engine) > 0.99f
				&& BagInventory->CountOf(GTItems::Scrap) + BootInventory->CountOf(GTItems::Scrap) == ScrapBeforeRepair;
			Run->SetCrewTier(GTTags::Crew_Mechanic, 0);
			Log(FString::Printf(TEXT("mechanic II: %s -> repaired=%d engine=%.2f free=%d"), *RepairText, bRepaired ? 1 : 0, Condition->GetPartHealth(EGTCarPart::Engine), bFreeRepair ? 1 : 0));

			// No room: the inputs of a lead lining (60 kg) are in the bag, and the bag and the boot are packed with bolts.
			Run->SetCrewTier(GTTags::Crew_Workbench, 1);
			BagInventory->Add(GTItems::Scrap, 8);
			BagInventory->Add(GTItems::RareAlloy, 2);
			const int32 FilledBagBolts = BagInventory->Add(GTItems::Bolts, 100000);
			const int32 FilledBootBolts = BootInventory->Add(GTItems::Bolts, 100000);
			const FName LiningId(TEXT("LeadLining"));
			const int32 ScrapBeforeLining = BagInventory->CountOf(GTItems::Scrap);
			const bool bLiningRow = HasRow(Workbench.Get(), 1, LiningId, bEnabled, Text);
			bWorkbenchNoRoom = bLiningRow && !bEnabled && Text.Contains(TEXT("no room")) && !ActRow(Workbench.Get(), 1, LiningId, Text)
				&& BagInventory->CountOf(GTItems::Scrap) == ScrapBeforeLining;
			Log(FString::Printf(TEXT("lead lining, packed: %s -> refused=%d"), *Text, bWorkbenchNoRoom ? 1 : 0));
			const FName WinchId(TEXT("Part.Winch"));
			const bool bWinchRow = HasRow(Lift.Get(), AGTCarLift::Remove, WinchId, bEnabled, Text);
			bLiftNoRoom = bWinchRow && !bEnabled && Text.Contains(TEXT("no room")) && !ActRow(Lift.Get(), AGTCarLift::Remove, WinchId, Text)
				&& Parts->GetInstalled(GTTags::Slot_Gadget) == WinchId;
			Log(FString::Printf(TEXT("winch off, packed (%d + %d bolts): %s -> refused=%d"), FilledBagBolts, FilledBootBolts, *Text, bLiftNoRoom ? 1 : 0));
			BagInventory->Remove(GTItems::Bolts, FilledBagBolts);
			BootInventory->Remove(GTItems::Bolts, FilledBootBolts);
			BagInventory->Remove(GTItems::Scrap, 8);
			BagInventory->Remove(GTItems::RareAlloy, 2);
			Run->SetCrewTier(GTTags::Crew_Workbench, 0);

			// The cursor, through the character as the keys drive it.
			Character->OpenStation(Trader.Get());
			TArray<FGTScreenRow> TraderRows;
			auto SelectRow = [&](int32 Action, FName Payload) -> bool
			{
				for (int32 Tries = 0; Tries < 80; ++Tries)
				{
					TraderRows.Reset();
					Trader->BuildRows(Character.Get(), TraderRows);
					const int32 Current = Character->GetStationSelection();
					int32 Target = INDEX_NONE;
					for (int32 RowIndex = 0; RowIndex < TraderRows.Num(); ++RowIndex)
					{
						if (!TraderRows[RowIndex].bHeader && TraderRows[RowIndex].Action == Action && TraderRows[RowIndex].Payload == Payload)
						{
							Target = RowIndex;
							break;
						}
					}
					if (Target == INDEX_NONE)
					{
						return false;
					}
					if (Target == Current)
					{
						return true;
					}
					Character->MoveStationSelection(Target > Current ? 1 : -1);
				}
				return false;
			};
			// T twice on "Buy Wire" with none carried: the first buy adds a sell row above it, and the second T still buys wire.
			const int32 WireBefore = BagInventory->CountOf(GTItems::Wire) + BootInventory->CountOf(GTItems::Wire);
			const int32 CreditsBeforeWire = Run->GetCurrency();
			const bool bOnWire = SelectRow(AGTTrader::Buy, GTItems::Wire);
			Character->ActOnStation();
			Character->ActOnStation();
			TraderRows.Reset();
			Trader->BuildRows(Character.Get(), TraderRows);
			const int32 WireSelection = Character->GetStationSelection();
			bCursorStays = bOnWire && WireBefore == 0 && BagInventory->CountOf(GTItems::Wire) + BootInventory->CountOf(GTItems::Wire) == 2 && Run->GetCurrency() == CreditsBeforeWire - 8
				&& TraderRows.IsValidIndex(WireSelection) && TraderRows[WireSelection].Action == AGTTrader::Buy && TraderRows[WireSelection].Payload == GTItems::Wire;
			// Selling the only radiator removes its row: the next T does nothing until the cursor moves.
			const bool bOnRadiator = SelectRow(AGTTrader::Sell, PartRadiator);
			const bool bSoldRadiator = Character->ActOnStation();
			const int32 CreditsAfterSale = Run->GetCurrency();
			const bool bSecondPress = Character->ActOnStation();
			bCursorDisarmed = bOnRadiator && bSoldRadiator && !bSecondPress && !Character->IsStationSelectionArmed() && Run->GetCurrency() == CreditsAfterSale;
			// Scrolling up past the top stays on a row.
			for (int32 Notch = 0; Notch < 60; ++Notch)
			{
				Character->MoveStationSelection(-1);
			}
			TraderRows.Reset();
			Trader->BuildRows(Character.Get(), TraderRows);
			const int32 TopSelection = Character->GetStationSelection();
			bCursorOffHeaders = TraderRows.IsValidIndex(TopSelection) && !TraderRows[TopSelection].bHeader && Character->IsStationSelectionArmed();
			Character->CloseStation();
			Log(FString::Printf(TEXT("cursor: wire twice=%d (credits %d -> %d after the radiator sale), radiator sold=%d, second T acted=%d, top row %d off headers=%d"),
				bCursorStays ? 1 : 0, CreditsBeforeWire, CreditsAfterSale, bSoldRadiator ? 1 : 0, bSecondPress ? 1 : 0, TopSelection, bCursorOffHeaders ? 1 : 0));

			// A coolant flush on a cool engine stays in the bag.
			Car->GetEnvironment()->Heat = 0.f;
			BagInventory->Add(UseFlush, 1);
			const bool bUsedFlush = Character->UseConsumable(UseFlush);
			bNoOpConsumableRefused = !bUsedFlush && BagInventory->CountOf(UseFlush) == 1 && Character->LastUseMessage.Contains(TEXT("nothing"));
			Log(FString::Printf(TEXT("flush on a cool engine: used=%d kept=%d '%s'"), bUsedFlush ? 1 : 0, BagInventory->CountOf(UseFlush), *Character->LastUseMessage));
			BagInventory->Remove(UseFlush, 1);

			// Look into the open driver's doorway above the door skin (the door opened when getting out in step 0).
			if (const UGTBodyComponent* Body = Car->GetBody())
			{
				const FBox Bounds = Body->GetDoorClosedBounds(Body->GetDriverDoor());
				const FVector High = Car->GetMesh()->GetComponentTransform().TransformPosition(FVector(Bounds.GetCenter().X, Bounds.Min.Y + 6.f, Bounds.Max.Z + 30.f));
				PC->SetControlRotation((High - Character->GetPawnViewLocation()).Rotation());
			}
			SubStep = 1;
			StepTime = 0.f;
		}
		else if (StepTime >= 0.8f)
		{
			const UGTInteractionComponent* Interaction = Character->GetInteraction();
			bGetInAboveSkin = Interaction && Interaction->IsOfferAvailable() && Interaction->GetPrompt().Contains(TEXT("Get in"));
			Log(FString::Printf(TEXT("doorway above the door skin: '%s' -> getIn=%d | %s"), Interaction ? *Interaction->GetPrompt() : TEXT(""), bGetInAboveSkin ? 1 : 0,
				Car->GetBody() ? *Car->GetBody()->DescribeDoors() : TEXT("no body")));
			SubStep = 0;
			Next();
		}
		break;
	}
	case 7:   // save, change, load: the campaign and the loadout come back
	{
		Run->CaptureFromPawns(Car.Get(), Character.Get());
		CurrencyBeforeSave = Run->GetCurrency();
		const bool bSaved = Run->SaveToSlot();
		Run->AddCurrency(1000);
		const bool bLoaded = Run->LoadFromSlot();
		CurrencyAfterLoad = Run->GetCurrency();
		for (const FGTSlotEntry& E : Run->GetSnapshot().Loadout)
		{
			bLoadedLoadoutHasHeater |= E.Slot == GTTags::Slot_Heater && E.PartId == PartHeater;
		}
		// The blanket of step 5 is still running: its resistance rides in the save for both the car and the character.
		bSnapshotResistances = Run->GetSnapshot().CarResistances.Num() > 0 && Run->GetSnapshot().CharacterResistances.Num() > 0;
		Log(FString::Printf(TEXT("save=%d load=%d credits %d -> %d loadoutHeater=%d resistances car %d character %d | %s"), bSaved ? 1 : 0, bLoaded ? 1 : 0, CurrencyBeforeSave, CurrencyAfterLoad,
			bLoadedLoadoutHasHeater ? 1 : 0, Run->GetSnapshot().CarResistances.Num(), Run->GetSnapshot().CharacterResistances.Num(), *Run->Describe()));
		const bool bAll = bCrafted && ScrapAfterCraft == 6 && bInstalledRadiator && RadiatorAfterInstall > 0.99f && BootRadiators == 1
			&& RepairCostSeen == 2 && EngineAfterRepair > 0.99f && WetAfterWash == 0.f
			&& CurrencyAfterSell == 310 && CurrencyAfterBuy == 190 && bHeaterInstalled && FMath::IsNearlyEqual(ColdResistance, 0.7f, 0.01f)
			&& bScoutRefused && ScoutTier == 1 && bBriefingPeak
			&& HeatAfterFlush == 0.f && FMath::IsNearlyEqual(ColdResistanceWithBlanket, 1.f, 0.01f) && FMath::IsNearlyEqual(OwnColdResistance, 0.6f, 0.01f)
			&& bSaved && bLoaded && CurrencyAfterLoad == CurrencyBeforeSave && bLoadedLoadoutHasHeater
			&& bExitBesideStep && bRequiredSlotRefused && bFreeRepair && bWorkbenchNoRoom && bLiftNoRoom && bCursorStays && bCursorDisarmed && bCursorOffHeaders
			&& bNoOpConsumableRefused && bGetInAboveSkin && bSnapshotResistances;
		Run->DeleteSave();   // the test slot starts empty next run
		Finish(bAll, FString::Printf(TEXT("base: crafted=%d scrap=%d installed=%d radiator=%.2f bootRadiators=%d repairCost=%d engine=%.2f wet=%.2f credits %d/%d heater=%d cold=%.2f scoutRefused=%d scoutTier=%d peak=%d flushHeat=%.2f blanket %.2f/%.2f save/load %d->%d loadoutHeater=%d assets=%d | fixes: exitOnStep=%d requiredSlot=%d freeRepair=%d benchNoRoom=%d liftNoRoom=%d cursorStays=%d cursorDisarmed=%d offHeaders=%d noOpRefused=%d getInAboveSkin=%d savedResistances=%d"),
			bCrafted ? 1 : 0, ScrapAfterCraft, bInstalledRadiator ? 1 : 0, RadiatorAfterInstall, BootRadiators, RepairCostSeen, EngineAfterRepair, WetAfterWash, CurrencyAfterSell, CurrencyAfterBuy,
			bHeaterInstalled ? 1 : 0, ColdResistance, bScoutRefused ? 1 : 0, ScoutTier, bBriefingPeak ? 1 : 0, HeatAfterFlush, ColdResistanceWithBlanket, OwnColdResistance,
			CurrencyBeforeSave, CurrencyAfterLoad, bLoadedLoadoutHasHeater ? 1 : 0, bAssets ? 1 : 0,
			bExitBesideStep ? 1 : 0, bRequiredSlotRefused ? 1 : 0, bFreeRepair ? 1 : 0, bWorkbenchNoRoom ? 1 : 0, bLiftNoRoom ? 1 : 0, bCursorStays ? 1 : 0, bCursorDisarmed ? 1 : 0,
			bCursorOffHeaders ? 1 : 0, bNoOpConsumableRefused ? 1 : 0, bGetInAboveSkin ? 1 : 0, bSnapshotResistances ? 1 : 0));
		break;
	}
	default:
		Fail(TEXT("unknown step"));
		break;
	}
}

// ---- loop --------------------------------------------------------------------------------------------

void FGTM4TestRunner::TickLoop(float DeltaSeconds)
{
	AGTRunGameMode* RunMode = Cast<AGTRunGameMode>(World->GetAuthGameMode());
	AGTBaseGameMode* BaseMode = Cast<AGTBaseGameMode>(World->GetAuthGameMode());
	AGTRunGameState* State = World->GetGameState<AGTRunGameState>();
	FString Text;

	if (BaseMode)
	{
		// ---- the base: the haul arrived, buy and fit a heater, drive out through the gate ----
		switch (Step)
		{
		case 0:
		{
			if (Run->TestStage != TEXT("base"))
			{
				Fail(FString::Printf(TEXT("base reached with stage '%s'"), *Run->TestStage));
				return;
			}
			if (!ExitCar())
			{
				Fail(TEXT("not on foot at the base"));
				return;
			}
			const int32 BootScrap = Car->GetBoot()->CountOf(GTItems::Scrap);
			const int32 BootWire = Car->GetBoot()->CountOf(GTItems::Wire);
			const bool bSaved = Run->HasSaveInSlot();
			Trader = FindActor<AGTTrader>();
			Lift = FindActor<AGTCarLift>();
			Log(FString::Printf(TEXT("base: onFoot=%d bootScrap=%d bootWire=%d credits=%d results=%d saved=%d trader=%d lift=%d gate=%d | %s"),
				PC->IsDriving() ? 0 : 1, BootScrap, BootWire, Run->GetCurrency(), Run->GetCampaign().Results.Num(), bSaved ? 1 : 0, Trader.IsValid() ? 1 : 0, Lift.IsValid() ? 1 : 0,
				FindActor<AGTDepartGate>() ? 1 : 0, *Run->Describe()));
			if (BootScrap != 3 || BootWire != 1 || Run->GetCampaign().Results.Num() != 1 || !bSaved || !Trader.IsValid() || !Lift.IsValid() || !FindActor<AGTDepartGate>())
			{
				Fail(TEXT("the haul, the result, the save or the stations are missing at the base"));
				return;
			}
			const bool bBought = ActRow(Trader.Get(), AGTTrader::Buy, PartHeater, Text);
			const bool bInstalled = ActRow(Lift.Get(), AGTCarLift::Install, PartHeater, Text);
			// A blanket used here must still be working on the leg: the snapshot carries timed resistances.
			Character->GetInventory()->Add(UseBlanket, 1);
			const bool bBlanket = Character->UseConsumable(UseBlanket);
			Log(FString::Printf(TEXT("heater bought=%d installed=%d credits=%d blanket=%d carCold=%.2f ownCold=%.2f %s"), bBought ? 1 : 0, bInstalled ? 1 : 0, Run->GetCurrency(),
				bBlanket ? 1 : 0, Car->GetParts()->GetResistance(GTTags::Env_Cold), Character->GetResistance(GTTags::Env_Cold), *Car->GetParts()->Describe()));
			if (!bBought || !bInstalled || !bBlanket)
			{
				Fail(TEXT("could not buy and install the heater, or use the blanket"));
				return;
			}
			Next();
			break;
		}
		case 1:   // out through the gate
			if (!bStepStarted)
			{
				bStepStarted = true;
				if (!EnterCar())
				{
					Fail(TEXT("could not get back in the car"));
					return;
				}
				Run->TestStage = TEXT("leg2");
				const AGTDepartGate* Gate = FindActor<AGTDepartGate>();
				TeleportCar(FVector(Gate->GetActorLocation().X, Gate->GetActorLocation().Y, Car->GetActorLocation().Z));
				Log(TEXT("in the car, inside the gate: departing"));
			}
			if (StepTimedOut(5.f, TEXT("the departure")))
			{
				return;
			}
			break;   // the level changes under us
		default:
			break;
		}
		return;
	}

	if (!RunMode || !State)
	{
		Fail(TEXT("neither the run nor the base game mode"));
		return;
	}
	if (Run->TestStage == TEXT("leg2"))
	{
		// ---- back on the leg: the loadout, the boot and the campaign carried ----
		const FName Heater = Car->GetParts()->GetInstalled(GTTags::Slot_Heater);
		const float* Cold = Car->GetEnvironment()->Resistance.Find(GTTags::Env_Cold);
		const float OwnCold = Character.IsValid() ? Character->GetResistance(GTTags::Env_Cold) : -1.f;
		const int32 BootScrap = Car->GetBoot()->CountOf(GTItems::Scrap);
		const bool bSaved = Run->HasSaveInSlot();
		// The heater's 0.7 plus the blanket used at the base (0.6), clamped to 1; the character keeps its own 0.6.
		// Credits: the tour's 300 at the start, plus the first leg's prize money (M5), less the heater's 120.
		const int32 Prize = Run->GetCampaign().Results.Num() > 0 ? Run->GetCampaign().Results[0].PrizeCredits : 0;
		const int32 ExpectedCredits = 300 + Prize - 120;
		const bool bAll = Heater == PartHeater && Cold && FMath::IsNearlyEqual(*Cold, 1.f, 0.01f) && FMath::IsNearlyEqual(OwnCold, 0.6f, 0.01f) && BootScrap == 3
			&& Prize > 0 && Run->GetCurrency() == ExpectedCredits && Run->GetCampaign().CurrentLegIndex == 1 && bSaved && State->GetPhase() == EGTLegPhase::Staging;
		Run->TestStage.Reset();
		Run->DeleteSave();   // the test slot starts empty next run
		Finish(bAll, FString::Printf(TEXT("loop: leg -> base -> leg: heater=%s cold=%.2f ownCold=%.2f bootScrap=%d credits=%d legIndex=%d saved=%d phase=%d | %s"),
			*Heater.ToString(), Cold ? *Cold : -1.f, OwnCold, BootScrap, Run->GetCurrency(), Run->GetCampaign().CurrentLegIndex, bSaved ? 1 : 0, static_cast<int32>(State->GetPhase()), *Run->Describe()));
		return;
	}

	// ---- the first leg: extract with a haul, continue to the base ----
	switch (Step)
	{
	case 0:
		Run->ResetCampaign();
		Run->DeleteSave();
		Run->TestStage = TEXT("leg1");
		if (!State->GetLeg() || State->GetCheckpointCount() < 2 || !State->GetExtraction())
		{
			Fail(FString::Printf(TEXT("the leg map did not resolve a leg with checkpoints and an extraction (%s)"), *State->Describe()));
			return;
		}
		Car->GetBoot()->Add(GTItems::Scrap, 3);
		Car->GetBoot()->Add(GTItems::Wire, 1);
		Log(FString::Printf(TEXT("leg1: %s | boot %s"), *State->Describe(), *Car->GetBoot()->Describe()));
		Next();
		break;
	case 1:   // through the checkpoints by teleport (the timer needs a move first)
		if (!bStepStarted)
		{
			bStepStarted = true;
			if (UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement())
			{
				Move->SetThrottleInput(1.f);
				Move->SetHandbrakeInput(false);
			}
		}
		if (State->GetPhase() == EGTLegPhase::Running)
		{
			for (int32 Pass = 0; Pass < 2; ++Pass)
			{
				if (const AGTCheckpoint* Next = State->GetNextCheckpoint())
				{
					TeleportCar(FVector(Next->GetActorLocation().X, Next->GetActorLocation().Y, Car->GetActorLocation().Z));
					State->Tick(0.f);
				}
			}
			const FVector Zone = State->GetExtraction()->GetActorLocation();
			TeleportCar(FVector(Zone.X, Zone.Y, Car->GetActorLocation().Z));
			Log(FString::Printf(TEXT("checkpoints: %s"), *State->Describe()));
			Next();
		}
		else if (StepTimedOut(6.f, TEXT("the timer to start")))
		{
			return;
		}
		break;
	case 2:   // hold in the zone, then continue to the base
		if (State->GetPhase() == EGTLegPhase::Finished)
		{
			Log(FString::Printf(TEXT("finished: %s"), *State->GetResult().Describe()));
			Run->TestStage = TEXT("base");
			RunMode->ContinueAfterLeg();
			Next();
		}
		else if (StepTimedOut(8.f, TEXT("the extraction")))
		{
			return;
		}
		break;
	default:
		if (StepTimedOut(10.f, TEXT("the base to load")))
		{
			return;
		}
		break;
	}
}

// ---- screenshots -------------------------------------------------------------------------------------

void FGTM4TestRunner::TeleportCharacter(const FVector& GroundLocation, const FVector& LookAt)
{
	if (!Character.IsValid() || !PC.IsValid())
	{
		return;
	}
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	Character->SetActorLocation(GroundLocation + FVector(0.f, 0.f, HalfHeight + 2.f), false, nullptr, ETeleportType::TeleportPhysics);
	PC->SetControlRotation((LookAt - Character->GetPawnViewLocation()).Rotation());
}

void FGTM4TestRunner::ShowFromCamera(const FVector& Location, const FRotator& Rotation)
{
	if (!ShotCamera.IsValid())
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ShotCamera = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), Location, Rotation, Params);
	}
	if (ShotCamera.IsValid())
	{
		ShotCamera->SetActorLocationAndRotation(Location, Rotation);
		PC->SetViewTarget(ShotCamera.Get());
	}
	if (PC->GetHUD())
	{
		PC->GetHUD()->bShowHUD = false;
	}
}

void FGTM4TestRunner::RequestShot(const TCHAR* Name)
{
	const FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("Screenshots") / ShotFolder / FString(Name) + TEXT(".png"));
	IFileManager::Get().Delete(*Path, false, true, true);
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path), true);
	FScreenshotRequest::RequestScreenshot(Path, /*bInShowUI*/ false, /*bAddFilenameSuffix*/ false);
	ShotFiles.Add(Path);
	Log(FString::Printf(TEXT("screenshot requested: %s"), *Path));
}

int32 FGTM4TestRunner::PendingCompileJobs() const
{
#if WITH_EDITOR
	int32 Jobs = GShaderCompilingManager ? GShaderCompilingManager->GetNumRemainingJobs() : 0;
	Jobs += FAssetCompilingManager::Get().GetNumRemainingAssets();
	return Jobs;
#else
	return 0;
#endif
}

void FGTM4TestRunner::TickScreenshots(float DeltaSeconds)
{
	switch (Step)
	{
	case 0:   // shaders and meshes compiled, the scene settled, on foot
	{
		const int32 Jobs = PendingCompileJobs();
		SettleLogTimer -= DeltaSeconds;
		if (SettleLogTimer <= 0.f)
		{
			SettleLogTimer = 5.f;
			Log(FString::Printf(TEXT("waiting for %d compile jobs (%.0f s)"), Jobs, StepTime));
		}
		if ((Jobs == 0 && StepTime >= 5.f) || StepTime >= 240.f)
		{
			if (!ExitCar())
			{
				Fail(TEXT("not on foot at the base"));
				return;
			}
			Lift = FindActor<AGTCarLift>();
			Log(FString::Printf(TEXT("settled after %.0f s with %d jobs left; lift=%d gate=%d"), StepTime, Jobs, Lift.IsValid() ? 1 : 0, FindActor<AGTDepartGate>() ? 1 : 0));
			Next();
		}
		break;
	}
	case 1:   // three-quarter overview from above the crew tent corner
		if (!bStepStarted)
		{
			bStepStarted = true;
			const FVector Location(-2600.f, 2600.f, 2000.f);
			const FVector Target(800.f, -300.f, 0.f);
			ShowFromCamera(Location, (Target - Location).Rotation());
		}
		if (StepTime >= 5.f)
		{
			RequestShot(TEXT("base_1_overview"));
			Next();
		}
		break;
	case 2:   // straight down over the whole yard
		if (!bStepStarted && StepTime >= 1.f)
		{
			bStepStarted = true;
			ShowFromCamera(FVector(1000.f, 0.f, 5500.f), FRotator(-89.f, 0.f, 0.f));
		}
		if (bStepStarted && StepTime >= 5.f)
		{
			RequestShot(TEXT("base_2_topdown"));
			Next();
		}
		break;
	case 3:   // eye level from the gate road, looking back at the car on the lift and the stations
		if (!bStepStarted && StepTime >= 1.f)
		{
			bStepStarted = true;
			PC->SetViewTarget(Character.Get());
			if (PC->GetHUD())
			{
				PC->GetHUD()->bShowHUD = true;
			}
			TeleportCharacter(FVector(1700.f, 250.f, 0.f), FVector(0.f, -500.f, 80.f));
		}
		if (bStepStarted && StepTime >= 5.f)
		{
			RequestShot(TEXT("base_3_yard"));
			Next();
		}
		break;
	case 4:   // beside the car with the lift screen open (bag stocked and the engine damaged for the picture)
		if (!bStepStarted && StepTime >= 1.f)
		{
			bStepStarted = true;
			UGTInventoryComponent* Bag = Character->GetInventory();
			Bag->Add(GTItems::Scrap, 10);
			Bag->Add(PartHeater, 1);
			Bag->Add(FName(TEXT("Part.AirFilter")), 1);
			Car->GetCondition()->SetPartHealth(EGTCarPart::Engine, 0.6f);
			TeleportCharacter(FVector(60.f, -330.f, 0.f), FVector(0.f, 0.f, 90.f));
			if (Lift.IsValid())
			{
				Character->OpenStation(Lift.Get());
			}
		}
		if (bStepStarted && StepTime >= 3.f)
		{
			RequestShot(TEXT("base_4_lift_screen"));
			Next();
		}
		break;
	case 5:   // all four doors open, seen from outside at the front-left corner
		if (!bStepStarted && StepTime >= 1.f)
		{
			bStepStarted = true;
			Character->CloseStation();
			if (UGTBodyComponent* Body = Car->GetBody())
			{
				for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
				{
					Body->SetDoorOpen(Door, true);
				}
			}
			const FTransform CarXf = Car->GetMesh()->GetComponentTransform();
			const FVector Eye = CarXf.TransformPosition(FVector(330.f, -430.f, 190.f));
			ShowFromCamera(Eye, (CarXf.TransformPosition(FVector(0.f, 0.f, 85.f)) - Eye).Rotation());
		}
		if (bStepStarted && StepTime >= 5.f)
		{
			RequestShot(TEXT("base_5_doors_open"));
			Next();
		}
		break;
	case 6:   // on foot behind the open driver's door, looking into the doorway
		if (!bStepStarted && StepTime >= 1.f)
		{
			bStepStarted = true;
			if (UGTBodyComponent* Body = Car->GetBody())
			{
				for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
				{
					Body->SetDoorOpen(Door, Door == Body->GetDriverDoor());
				}
			}
			PC->SetViewTarget(Character.Get());
			if (PC->GetHUD())
			{
				PC->GetHUD()->bShowHUD = true;
			}
			const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
			Character->SetActorLocation(Car->FindExitLocation(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight()), false, nullptr, ETeleportType::TeleportPhysics);
		}
		if (bStepStarted)
		{
			if (const UGTBodyComponent* Body = Car->GetBody())
			{
				PC->SetControlRotation((DoorwayPoint(Car.Get(), Body, Body->GetDriverDoor()) - Character->GetPawnViewLocation()).Rotation());
			}
		}
		if (bStepStarted && StepTime >= 4.f)
		{
			RequestShot(TEXT("base_6_get_in"));
			Next();
		}
		break;
	default:
		if (StepTime >= 3.f)
		{
			int32 Found = 0;
			FString Sizes;
			for (const FString& Path : ShotFiles)
			{
				const int64 Size = IFileManager::Get().FileSize(*Path);
				Found += Size > 0 ? 1 : 0;
				Sizes += FString::Printf(TEXT(" %s=%lld"), *FPaths::GetBaseFilename(Path), Size);
			}
			Run->DeleteSave();   // the arrival save of a picture run is not the user's
			Finish(Found == 6 && ShotFiles.Num() == 6, FString::Printf(TEXT("screenshots: %d/%d written:%s"), Found, ShotFiles.Num(), *Sizes));
		}
		break;
	}
}

// ---- doors -------------------------------------------------------------------------------------------

void FGTM4TestRunner::TickDoors(float DeltaSeconds)
{
	UGTBodyComponent* Body = Car->GetBody();
	if (!Body)
	{
		Fail(TEXT("the car has no body component"));
		return;
	}
	const int32 Driver = Body->GetDriverDoor();
	const FTransform CarXf = Car->GetMesh()->GetComponentTransform();
	// The shut door's trailing outer edge, wherever the panel is now, in car space.
	auto TrailingLocal = [&](int32 Door) -> FVector
	{
		const FBox B = Body->GetDoorClosedBounds(Door);
		const FVector MeshPoint(B.Min.X, Body->IsDoorLeft(Door) ? B.Min.Y : B.Max.Y, B.GetCenter().Z);
		const UStaticMeshComponent* Panel = Body->GetDoorPanel(Door);
		return Panel ? CarXf.InverseTransformPosition(Panel->GetComponentTransform().TransformPosition(MeshPoint)) : FVector::ZeroVector;
	};
	// Where that edge should be at an angle about the hinge.
	auto ExpectedTrailing = [&](int32 Door, float Angle) -> FVector
	{
		const FBox B = Body->GetDoorClosedBounds(Door);
		const FVector H = Body->GetDoorHingeLocal(Door);
		const FVector Rel(B.Min.X - H.X, 0.f, B.GetCenter().Z - H.Z);
		return H + FRotator(0.f, (Body->IsDoorLeft(Door) ? 1.f : -1.f) * Angle, 0.f).RotateVector(Rel);
	};
	auto DoorwayWorld = [&]() -> FVector
	{
		const FBox B = Body->GetDoorClosedBounds(Driver);
		const bool bLeft = Body->IsDoorLeft(Driver);
		return CarXf.TransformPosition(FVector(B.GetCenter().X, (bLeft ? B.Min.Y : B.Max.Y) + (bLeft ? 6.f : -6.f), B.GetCenter().Z));
	};
	auto Aim = [&](const FVector& World)
	{
		if (Character.IsValid())
		{
			PC->SetControlRotation((World - Character->GetPawnViewLocation()).Rotation());
		}
	};
	UGTInteractionComponent* Interaction = Character.IsValid() ? Character->GetInteraction() : nullptr;
	auto Prompt = [&]() -> FString
	{
		return Interaction ? FString::Printf(TEXT("'%s'%s"), *Interaction->GetPrompt(), Interaction->IsOfferAvailable() ? TEXT("") : TEXT(" (unavailable)")) : TEXT("no interaction");
	};

	switch (Step)
	{
	case 0:   // four doors, hinges at the front edges on the outer skin, the driver's door front-left; swing all open
	{
		bFourDoors = Body->GetDoorCount() == 4;
		bHingesOk = bFourDoors;
		for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
		{
			const FBox B = Body->GetDoorClosedBounds(Door);
			const FVector H = Body->GetDoorHingeLocal(Door);
			const float OuterY = Body->IsDoorLeft(Door) ? B.Min.Y : B.Max.Y;
			bHingesOk &= FMath::IsNearlyEqual(H.X, B.Max.X, 0.1f) && FMath::IsNearlyEqual(H.Y, OuterY, 0.1f) && Body->GetDoorHinge(Door) && Body->GetDoorPanel(Door)
				&& Body->GetDoorPanel(Door)->GetAttachParent() == Body->GetDoorHinge(Door);
			const int32 Partner = Body->FindDoor(Body->IsDoorLeft(Door), !Body->IsDoorFront(Door));
			if (Body->IsDoorFront(Door) && Partner != INDEX_NONE)
			{
				bHingesOk &= H.X > Body->GetDoorHingeLocal(Partner).X;
			}
			Log(FString::Printf(TEXT("%s: bounds min=%s max=%s hinge=%s trailing now=%s"), *Body->DoorName(Door), *B.Min.ToCompactString(), *B.Max.ToCompactString(),
				*H.ToCompactString(), *TrailingLocal(Door).ToCompactString()));
		}
		bDriverOk = Driver != INDEX_NONE && Body->IsDoorFront(Driver) && Body->IsDoorLeft(Driver);
		if (Character.IsValid())
		{
			Character->SelectTool(-1);
		}
		for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
		{
			Body->SetDoorOpen(Door, true);
		}
		Log(FString::Printf(TEXT("doors=%d hingesOk=%d driverOk=%d; all opening"), Body->GetDoorCount(), bHingesOk ? 1 : 0, bDriverOk ? 1 : 0));
		if (!bFourDoors || Driver == INDEX_NONE)
		{
			Fail(FString::Printf(TEXT("expected four doors with a driver's door: %s"), *Body->DescribeDoors()));
			return;
		}
		Next();
		break;
	}
	case 1:   // fully open, and every trailing edge sits where the hinge math says
		if (StepTime >= 0.8f)
		{
			bAllOpen = true;
			SwingError = 0.f;
			for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
			{
				bAllOpen &= FMath::IsNearlyEqual(Body->GetDoorAngle(Door), Body->DoorOpenAngle, 0.5f);
				SwingError = FMath::Max(SwingError, FVector::Dist(TrailingLocal(Door), ExpectedTrailing(Door, Body->GetDoorAngle(Door))));
			}
			const FVector DriverEdge = TrailingLocal(Driver);
			bSwingOk = SwingError < 1.f && DriverEdge.Y < -170.f;
			Log(FString::Printf(TEXT("open: %s | driver trailing edge %s swingError=%.2f cm"), *Body->DescribeDoors(), *DriverEdge.ToCompactString(), SwingError));
			for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
			{
				Body->SetDoorOpen(Door, false);
			}
			Next();
		}
		break;
	case 2:   // shut again exactly; then get out: the driver's door opens and the exit spot is behind it
		if (StepTime >= 0.8f)
		{
			const FBox B = Body->GetDoorClosedBounds(Driver);
			const FVector Shut(B.Min.X, B.Min.Y, B.GetCenter().Z);
			bClosedBack = FVector::Dist(TrailingLocal(Driver), Shut) < 0.5f && Body->GetDoorAngle(Driver) == 0.f;
			Log(FString::Printf(TEXT("shut: %s | driver trailing %s closedBack=%d"), *Body->DescribeDoors(), *TrailingLocal(Driver).ToCompactString(), bClosedBack ? 1 : 0));
			if (!ExitCar())
			{
				Fail(TEXT("could not get out"));
				return;
			}
			Interaction = Character->GetInteraction();
			const FVector Local = CarXf.InverseTransformPosition(Character->GetActorLocation());
			bDriverDoorOpenedOnExit = Body->IsDoorOpen(Driver);
			bExitBehindDoor = Local.X < B.Min.X && Local.Y < -150.f;
			DoorExitDistance = FVector::Dist2D(Character->GetActorLocation(), Car->GetActorLocation());
			Log(FString::Printf(TEXT("out at car-space %s (%.0f cm from the car) doorOpening=%d behindDoor=%d"), *Local.ToCompactString(), DoorExitDistance, bDriverDoorOpenedOnExit ? 1 : 0, bExitBehindDoor ? 1 : 0));
			Next();
		}
		break;
	case 3:   // the door has swung; look into the doorway
		if (StepTime >= 0.8f)
		{
			Aim(DoorwayWorld());
			Next();
		}
		break;
	case 4:
		if (StepTime >= 0.35f)
		{
			bGetInOffered = Interaction->IsOfferAvailable() && Interaction->GetPrompt().Contains(TEXT("Get in"));
			DoorPrompts += TEXT(" doorway:") + Prompt();
			Aim(Body->GetDoorPanel(Driver)->Bounds.Origin);
			Next();
		}
		break;
	case 5:   // look at the open door: close it by hand
		if (StepTime >= 0.35f)
		{
			bCloseOffered = Interaction->IsOfferAvailable() && Interaction->GetPrompt().Contains(TEXT("Close front-left door"));
			DoorPrompts += TEXT(" openDoor:") + Prompt();
			Interaction->SetHoldInput(true);
			Next();
		}
		break;
	case 6:
		if (!Body->IsDoorOpen(Driver))
		{
			Interaction->SetHoldInput(false);
			Next();
		}
		else if (StepTimedOut(3.f, TEXT("the door to close")))
		{
			return;
		}
		break;
	case 7:   // shut: the doorway now shows the door
		if (StepTime >= 0.8f)
		{
			bClosedByHand = Body->GetDoorAngle(Driver) == 0.f;
			Aim(DoorwayWorld());
			Next();
		}
		break;
	case 8:
		if (StepTime >= 0.35f)
		{
			bOpenOffered = Interaction->IsOfferAvailable() && Interaction->GetPrompt().Contains(TEXT("Open front-left door"));
			DoorPrompts += TEXT(" shutDoor:") + Prompt();
			Aim(CarXf.TransformPosition(FVector(-140.f, -93.f, 70.f)));   // the rear arch: not a door
			Next();
		}
		break;
	case 9:
		if (StepTime >= 0.35f)
		{
			bNeedsDoorHint = !Interaction->IsOfferAvailable() && Interaction->GetPrompt().Contains(TEXT("door"));
			DoorPrompts += TEXT(" arch:") + Prompt();
			Aim(DoorwayWorld());
			Next();
		}
		break;
	case 10:   // open it by hand
		if (StepTime >= 0.35f)
		{
			Interaction->SetHoldInput(true);
			Next();
		}
		break;
	case 11:
		if (Body->IsDoorOpen(Driver))
		{
			Interaction->SetHoldInput(false);
			Next();
		}
		else if (StepTimedOut(3.f, TEXT("the door to open")))
		{
			return;
		}
		break;
	case 12:   // swung open: get in through the doorway
		if (StepTime >= 0.8f)
		{
			bOpenedByHand = Body->GetDoorAngle(Driver) > Body->DoorwayClearAngle;
			Interaction->SetHoldInput(true);
			Next();
		}
		break;
	case 13:
		if (PC->IsDriving())
		{
			Interaction->SetHoldInput(false);
			Car->DisableInput(PC.Get());
			Car->ResetDrivingInputs();
			bEnteredThroughDoor = true;
			Next();
		}
		else if (StepTimedOut(3.f, TEXT("getting in")))
		{
			return;
		}
		break;
	case 14:   // the door shut behind; then out again and knock both left doors off
		if (StepTime >= 1.2f)
		{
			bShutBehind = !Body->IsDoorOpen(Driver) && Body->GetDoorAngle(Driver) == 0.f;
			Log(FString::Printf(TEXT("in the seat: %s shutBehind=%d"), *Body->DescribeDoors(), bShutBehind ? 1 : 0));
			if (!ExitCar())
			{
				Fail(TEXT("could not get out the second time"));
				return;
			}
			Interaction = Character->GetInteraction();
			UGTConditionComponent* Condition = Car->GetCondition();
			for (int32 Hit = 0; Hit < 6 && Condition->GetRegionHealth(EGTDamageRegion::SideL) > 0.f; ++Hit)
			{
				Condition->ApplyImpact(FVector(40.f, -93.f, 80.f), FVector(0.f, -1.f, 0.f), 3000.f);
			}
			Log(FString::Printf(TEXT("left side health %.2f"), Condition->GetRegionHealth(EGTDamageRegion::SideL)));
			Next();
		}
		break;
	case 15:   // knocked off: park the dropped doors out of the line of sight, then look into the doorway
		if (StepTime >= 0.5f)
		{
			bDoorDetached = Body->IsDoorDetached(Driver);
			for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
			{
				if (Body->IsDoorDetached(Door) && Body->GetDoorPanel(Door))
				{
					Body->GetDoorPanel(Door)->SetSimulatePhysics(false);
					Body->GetDoorPanel(Door)->SetWorldLocation(CarXf.TransformPosition(FVector(0.f, -3000.f, 0.f)));
				}
			}
			Log(FString::Printf(TEXT("detached: %s"), *Body->DescribeDoors()));
			Aim(DoorwayWorld());
			Next();
		}
		break;
	case 16:
		if (StepTime >= 0.35f)
		{
			bGetInWithoutDoor = Interaction->IsOfferAvailable() && Interaction->GetPrompt().Contains(TEXT("Get in"));
			DoorPrompts += TEXT(" noDoor:") + Prompt();
			Car->GetCondition()->RepairAll();
			Body->ReattachAll();
			Next();
		}
		break;
	case 17:   // back on the hinge, shut, targetable
		if (StepTime >= 0.3f)
		{
			const UStaticMeshComponent* Panel = Body->GetDoorPanel(Driver);
			const FBox B = Body->GetDoorClosedBounds(Driver);
			const FVector Shut(B.Min.X, B.Min.Y, B.GetCenter().Z);
			bReattached = Panel && !Body->IsDoorDetached(Driver) && Panel->GetAttachParent() == Body->GetDoorHinge(Driver)
				&& Panel->GetRelativeLocation().Equals(-Body->GetDoorHingeLocal(Driver), 0.1f) && FVector::Dist(TrailingLocal(Driver), Shut) < 0.5f
				&& Body->GetDoorAngle(Driver) == 0.f && Panel->GetCollisionEnabled() == ECollisionEnabled::QueryOnly
				&& Panel->GetCollisionResponseToChannel(ECC_Visibility) == ECR_Block;
			Log(FString::Printf(TEXT("reattached=%d %s"), bReattached ? 1 : 0, *Body->DescribeDoors()));
			const bool bAll = bFourDoors && bHingesOk && bDriverOk && bAllOpen && bSwingOk && bClosedBack && bDriverDoorOpenedOnExit && bExitBehindDoor
				&& DoorExitDistance > 120.f && DoorExitDistance < 300.f && bGetInOffered && bCloseOffered && bClosedByHand && bOpenOffered && bNeedsDoorHint
				&& bOpenedByHand && bEnteredThroughDoor && bShutBehind && bDoorDetached && bGetInWithoutDoor && bReattached;
			Summary = FString::Printf(TEXT("doors: four=%d hinges=%d driver=%d allOpen=%d swing=%d (err %.2f cm) closedBack=%d exitOpens=%d behindDoor=%d exitDist=%.0f getIn=%d closeOffered=%d closedByHand=%d openOffered=%d needsDoorHint=%d openedByHand=%d entered=%d shutBehind=%d detached=%d getInNoDoor=%d reattached=%d |%s"),
				bFourDoors ? 1 : 0, bHingesOk ? 1 : 0, bDriverOk ? 1 : 0, bAllOpen ? 1 : 0, bSwingOk ? 1 : 0, SwingError, bClosedBack ? 1 : 0, bDriverDoorOpenedOnExit ? 1 : 0,
				bExitBehindDoor ? 1 : 0, DoorExitDistance, bGetInOffered ? 1 : 0, bCloseOffered ? 1 : 0, bClosedByHand ? 1 : 0, bOpenOffered ? 1 : 0, bNeedsDoorHint ? 1 : 0,
				bOpenedByHand ? 1 : 0, bEnteredThroughDoor ? 1 : 0, bShutBehind ? 1 : 0, bDoorDetached ? 1 : 0, bGetInWithoutDoor ? 1 : 0, bReattached ? 1 : 0, *DoorPrompts);
			bPass = bAll;
			if (!FApp::CanEverRender())
			{
				Finish(bAll, Summary);
				return;
			}
			ShotFolder = TEXT("Doors");
			Next();
		}
		break;
	case 18:   // pictures (gpu runs): wait for compiles, then all four doors open from outside
	{
		const int32 Jobs = PendingCompileJobs();
		SettleLogTimer -= DeltaSeconds;
		if (SettleLogTimer <= 0.f)
		{
			SettleLogTimer = 5.f;
			Log(FString::Printf(TEXT("pictures: waiting for %d compile jobs (%.0f s)"), Jobs, StepTime));
		}
		if ((Jobs == 0 && StepTime >= 2.f) || StepTime >= 200.f)
		{
			for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
			{
				Body->SetDoorOpen(Door, true);
			}
			const FVector Eye = CarXf.TransformPosition(FVector(330.f, -430.f, 190.f));
			ShowFromCamera(Eye, (CarXf.TransformPosition(FVector(0.f, 0.f, 85.f)) - Eye).Rotation());
			Next();
		}
		break;
	}
	case 19:
		if (StepTime >= 4.f)
		{
			RequestShot(TEXT("doors_1_open"));
			Next();   // the request is served on the next frame drawn: change the view a step later
		}
		break;
	case 20:   // on foot behind the open driver's door, looking into the doorway
		if (!bStepStarted && StepTime >= 1.f)
		{
			bStepStarted = true;
			for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
			{
				Body->SetDoorOpen(Door, Door == Driver);
			}
			PC->SetViewTarget(Character.Get());
			if (PC->GetHUD())
			{
				PC->GetHUD()->bShowHUD = true;
			}
			const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
			Character->SetActorLocation(Car->FindExitLocation(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight()), false, nullptr, ETeleportType::TeleportPhysics);
		}
		if (bStepStarted)
		{
			Aim(DoorwayWorld());
		}
		if (bStepStarted && StepTime >= 4.f)
		{
			DoorPrompts += TEXT(" picture:") + Prompt();
			RequestShot(TEXT("doors_2_get_in"));
			Next();
		}
		break;
	default:
		if (StepTime >= 3.f)
		{
			int32 Found = 0;
			for (const FString& Path : ShotFiles)
			{
				Found += IFileManager::Get().FileSize(*Path) > 0 ? 1 : 0;
			}
			Finish(bPass && Found == 2, FString::Printf(TEXT("%s | pictures %d/2 in Saved/Screenshots/Doors"), *Summary, Found));
		}
		break;
	}
}
