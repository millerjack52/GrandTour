#include "Core/GTPlayerController.h"
#include "UI/GTWorkshopComponent.h"

#include "Character/GTPlayerCharacter.h"
#include "Run/GTRunGameMode.h"
#include "Terrain/GTProvingGround.h"
#include "Vehicle/GTBodyComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTWinchComponent.h"
#include "Vehicle/GTVehicleAudioComponent.h"
#include "Inventory/GTInventoryComponent.h"

#include "Camera/CameraComponent.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EnhancedInputSubsystems.h"
#include "InputMappingContext.h"
#include "Components/InputComponent.h"

AGTPlayerController::AGTPlayerController()
{
	CharacterClass = AGTPlayerCharacter::StaticClass();
	Workshop = CreateDefaultSubobject<UGTWorkshopComponent>(TEXT("Workshop"));
}

void AGTPlayerController::GTWorkshop()
{
	if (Workshop->IsOpen()) Workshop->Close();
	else Workshop->Open();
}

void AGTPlayerController::EndPlay(const EEndPlayReason::Type Reason)
{
	Workshop->Close();
	Super::EndPlay(Reason);
}

bool AGTPlayerController::ReplaceGarageVehicle(TSubclassOf<AGTCarPawn> VehicleClass, const FTransform& SpawnTransform, FString& Result)
{
	AGTCarPawn* Old = Car.Get();
	if (!VehicleClass || !Character.IsValid() || GetPawn() != Character.Get() || !Old || Old->GetController())
	{ Result = TEXT("Get out of your car first."); return false; }
	if (Old->GetVelocity().Size() > 30.f || Character->IsCarryingHook() ||
		(Old->GetWinch()->GetState() != EGTWinchState::Stowed && Old->GetWinch()->GetState() != EGTWinchState::Snapped))
	{ Result = TEXT("Stop the car and stow its winch first."); return false; }
	FCollisionQueryParams Query(SCENE_QUERY_STAT(GarageClearance), false);
	Query.AddIgnoredActor(Old);
	// All fleet cars fit this envelope. Ignore the outgoing car, but never the player or other cars.
	if (GetWorld()->OverlapBlockingTestByProfile(SpawnTransform.GetLocation()+FVector(0,0,90), SpawnTransform.GetRotation(),
		TEXT("BlockAll"), FCollisionShape::MakeBox(FVector(360,180,170)), Query))
	{ Result = TEXT("Clear the parking bay outside the garage."); return false; }
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Params.Owner = this;
	AGTCarPawn* NewCar = GetWorld()->SpawnActor<AGTCarPawn>(VehicleClass, SpawnTransform, Params);
	if (!NewCar) { Result = TEXT("Could not prepare this vehicle. Your car is unchanged."); return false; }
	UGTInventoryComponent* OldBoot = Old->GetBoot();
	UGTInventoryComponent* NewBoot = NewCar->GetBoot();
	if (OldBoot->GetTotalWeightKg() > NewBoot->MaxWeightKg)
	{ NewCar->Destroy(); Result = TEXT("Unload the boot: it exceeds this car's capacity."); return false; }
	// Replace any starter stock, preserving exact stacks without a partial transfer.
	NewBoot->Items = OldBoot->Items;
	++NewBoot->Version;
	NewCar->ResetDrivingInputs();
	NewCar->GetChaosMovement()->SetHandbrakeInput(true);
	NewCar->GetAudio()->SetMuted(Old->GetAudio()->bMuted);
	Character->CloseBoot();
	Car = NewCar;
	Old->Destroy();
	Result = TEXT("Ready outside. Your boot contents have been transferred.");
	return true;
}

void AGTPlayerController::OnPossess(APawn* InPawn)
{
	Workshop->Close();
	Super::OnPossess(InPawn);
	if (AGTCarPawn* NewCar = Cast<AGTCarPawn>(InPawn))
	{
		Car = NewCar;
		EnsureCharacter(NewCar);
		NewCar->ResetDrivingInputs();
	}
	else if (AGTPlayerCharacter* NewCharacter = Cast<AGTPlayerCharacter>(InPawn))
	{
		Character = NewCharacter;
	}
	// The possessed pawn added its own context in SetupPlayerInputComponent; drop the other pawn's.
	if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		if (Car.IsValid() && InPawn != Car.Get() && Car->DefaultMappingContext)
		{
			Subsystem->RemoveMappingContext(Car->DefaultMappingContext);
		}
		if (Character.IsValid() && InPawn != Character.Get() && Character->OnFootMappingContext)
		{
			Subsystem->RemoveMappingContext(Character->OnFootMappingContext);
		}
	}
}

void AGTPlayerController::GTGoto(const FString& Station)
{
	FString Message;
	GTProving::Goto(this, Station.TrimStartAndEnd(), Message);
	UE_LOG(LogTemp, Display, TEXT("%s"), *Message);
	ClientMessage(Message);
	if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 6.f, FColor(255, 220, 120), Message);
	}
}

void AGTPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	if (InputComponent)
	{
		InputComponent->BindKey(EKeys::U, IE_Pressed, this, &AGTPlayerController::GTWorkshop);
		// The results screen's one key; plain key bindings live beside the pawns' enhanced input contexts.
		InputComponent->BindKey(EKeys::Enter, IE_Pressed, this, &AGTPlayerController::OnContinuePressed);
		InputComponent->BindKey(EKeys::Gamepad_Special_Right, IE_Pressed, this, &AGTPlayerController::OnContinuePressed);
	}
}

void AGTPlayerController::OnContinuePressed()
{
	if (AGTRunGameMode* GameMode = GetWorld()->GetAuthGameMode<AGTRunGameMode>())
	{
		GameMode->ContinueAfterLeg();
	}
}

void AGTPlayerController::EnsureCharacter(AGTCarPawn* ForCar)
{
	if (Character.IsValid() || !ForCar || !CharacterClass)
	{
		return;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Params.Owner = this;
	AGTPlayerCharacter* NewCharacter = GetWorld()->SpawnActor<AGTPlayerCharacter>(CharacterClass, ForCar->GetActorLocation() + FVector(0.f, 0.f, 100.f), ForCar->GetActorRotation(), Params);
	if (!NewCharacter)
	{
		UE_LOG(LogTemp, Error, TEXT("AGTPlayerController: could not spawn the player character"));
		return;
	}
	NewCharacter->SetInCar(true, ForCar);
	Character = NewCharacter;
	UE_LOG(LogTemp, Display, TEXT("AGTPlayerController: spawned %s inside %s"), *NewCharacter->GetName(), *ForCar->GetName());
}

bool AGTPlayerController::IsDriving() const
{
	return Car.IsValid() && GetPawn() == Car.Get();
}

bool AGTPlayerController::ExitCar()
{
	AGTCarPawn* TheCar = Car.Get();
	AGTPlayerCharacter* TheCharacter = Character.Get();
	if (!TheCar || !TheCharacter || GetPawn() != TheCar)
	{
		return false;
	}
	UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement();
	if (Move && FMath::Abs(Move->GetForwardSpeed()) > MaxExitSpeed)
	{
		UE_LOG(LogTemp, Display, TEXT("AGTPlayerController: too fast to get out (%.0f cm/s)"), Move->GetForwardSpeed());
		return false;
	}
	TheCar->ResetDrivingInputs();
	if (Move)
	{
		Move->SetHandbrakeInput(true);   // the car keeps simulating with the handbrake on
	}
	// The driver's door swings open as you step out, and stays open.
	if (UGTBodyComponent* Body = TheCar->GetBody())
	{
		Body->SetDoorOpen(Body->GetDriverDoor(), true);
	}
	const FRotator SeatView = TheCar->GetDriverCamera() ? TheCar->GetDriverCamera()->GetComponentRotation() : TheCar->GetActorRotation();
	const UCapsuleComponent* Capsule = TheCharacter->GetCapsuleComponent();
	const FVector ExitLocation = TheCar->FindExitLocation(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight());

	TheCharacter->SetInCar(false, nullptr);
	TheCharacter->SetActorLocationAndRotation(ExitLocation, FRotator(0.f, SeatView.Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	if (CameraBlendTime > 0.f)
	{
		SetViewTargetWithBlend(TheCharacter, CameraBlendTime, VTBlend_EaseInOut, 2.f);
	}
	Possess(TheCharacter);
	SetControlRotation(FRotator(SeatView.Pitch, SeatView.Yaw, 0.f));
	++SwapCount;
	UE_LOG(LogTemp, Display, TEXT("AGTPlayerController: out of the car at %s"), *ExitLocation.ToCompactString());
	return true;
}

bool AGTPlayerController::EnterCar()
{
	return EnterVehicle(Car.Get());
}

bool AGTPlayerController::EnterVehicle(AGTCarPawn* TheCar)
{
	AGTPlayerCharacter* TheCharacter = Character.Get();
	if (!IsValid(TheCar) || TheCar->GetWorld() != GetWorld() || !TheCharacter || GetPawn() != TheCharacter)
	{
		return false;
	}
	if (TheCar->GetController() && TheCar->GetController() != this)
	{
		return false;
	}
	if (TheCar->GetVelocity().Size() > MaxExitSpeed)
	{
		return false;
	}
	TheCharacter->DropHook();
	TheCharacter->SetInCar(true, TheCar);
	if (CameraBlendTime > 0.f)
	{
		SetViewTargetWithBlend(TheCar, CameraBlendTime, VTBlend_EaseInOut, 2.f);
	}
	Possess(TheCar);
	TheCar->ResetDrivingInputs();
	// The door you came in through swings shut behind you (the driver's door when none was named).
	if (UGTBodyComponent* Body = TheCar->GetBody())
	{
		const int32 Door = TheCar->PendingEnterDoor != INDEX_NONE ? TheCar->PendingEnterDoor : Body->GetDriverDoor();
		if (Door != INDEX_NONE && Body->IsDoorOpen(Door) && !Body->IsDoorDetached(Door))
		{
			const float Delay = Body->IsDoorwayClear(Door) ? TheCar->EnterCloseDelay : Body->DoorSwingSeconds + TheCar->EnterCloseDelay;
			Body->SetDoorOpen(Door, false, Delay);
		}
	}
	TheCar->PendingEnterDoor = INDEX_NONE;
	++SwapCount;
	UE_LOG(LogTemp, Display, TEXT("AGTPlayerController: back in the car"));
	return true;
}

bool AGTPlayerController::HasDrivingContext() const
{
	const UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer());
	return Subsystem && Car.IsValid() && Car->DefaultMappingContext && Subsystem->HasMappingContext(Car->DefaultMappingContext);
}

bool AGTPlayerController::HasOnFootContext() const
{
	const UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer());
	return Subsystem && Character.IsValid() && Character->OnFootMappingContext && Subsystem->HasMappingContext(Character->OnFootMappingContext);
}
