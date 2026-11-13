#include "Core/GTM2TestRunner.h"

#include "Character/GTExposureComponent.h"
#include "Character/GTPlayerCharacter.h"
#include "Core/GTGameplayTags.h"
#include "Core/GTPlayerController.h"
#include "Harvest/GTHarvestNode.h"
#include "Hazards/GTHazardVolume.h"
#include "Interaction/GTInteractionComponent.h"
#include "Inventory/GTInventoryComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTWinchAnchor.h"
#include "Vehicle/GTWinchComponent.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "InputAction.h"
#include "InputMappingContext.h"

#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

FGTM2TestRunner::FGTM2TestRunner(UWorld* InWorld, bool bInWinchTest)
	: World(InWorld), bWinchTest(bInWinchTest)
{
}

void FGTM2TestRunner::Log(const FString& Line) const
{
	UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST m2 t=%.1f step %d: %s"), Elapsed, Step, *Line);
}

void FGTM2TestRunner::Finish(bool bInPass, const FString& InSummary)
{
	bDone = true;
	bPass = bInPass;
	Summary = InSummary;
}

void FGTM2TestRunner::Next()
{
	++Step;
	StepTime = 0.f;
	bStepStarted = false;
}

bool FGTM2TestRunner::StepTimedOut(float Seconds, const TCHAR* What)
{
	if (StepTime > Seconds)
	{
		Fail(FString::Printf(TEXT("timed out waiting for %s (%s)"), What, Character.IsValid() ? *Character->GetInteraction()->Describe() : TEXT("no character")));
		return true;
	}
	return false;
}

FVector FGTM2TestRunner::CarLocal(const FVector& Local) const
{
	return Car.IsValid() ? Car->GetMesh()->GetComponentTransform().TransformPosition(Local) : Local;
}

void FGTM2TestRunner::TeleportCharacter(const FVector& GroundLocation, const FVector& LookAt)
{
	if (!Character.IsValid())
	{
		return;
	}
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	Character->SetActorLocation(GroundLocation + FVector(0.f, 0.f, HalfHeight + 2.f), false, nullptr, ETeleportType::TeleportPhysics);
	AimAt(LookAt);
}

void FGTM2TestRunner::AimAt(const FVector& Target)
{
	if (PC.IsValid() && Character.IsValid())
	{
		PC->SetControlRotation((Target - Character->GetPawnViewLocation()).Rotation());
	}
}

bool FGTM2TestRunner::TargetIs(const AActor* Actor) const
{
	return Character.IsValid() && Actor && Character->GetInteraction()->GetCurrentTarget() == Actor;
}

bool FGTM2TestRunner::PromptContains(const TCHAR* Text) const
{
	return Character.IsValid() && Character->GetInteraction()->GetPrompt().Contains(Text);
}

bool FGTM2TestRunner::Setup()
{
	PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(World.Get(), 0));
	Car = PC.IsValid() ? Cast<AGTCarPawn>(PC->GetPawn()) : nullptr;
	if (!PC.IsValid() || !Car.IsValid())
	{
		Fail(TEXT("player 0 is not an AGTPlayerController driving an AGTCarPawn"));
		return false;
	}
	Car->DisableInput(PC.Get());
	Car->ResetDrivingInputs();
	Log(FString::Printf(TEXT("car at %s, controller %s"), *Car->GetActorLocation().ToCompactString(), *PC->GetName()));

	const bool bExited = PC->ExitCar();
	Character = PC->GetPlayerCharacter();
	if (!bExited || !Character.IsValid())
	{
		Fail(TEXT("ExitCar failed or no character was spawned"));
		return false;
	}
	Character->DisableInput(PC.Get());
	bExitOk = PC->GetPawn() == Character.Get() && !Character->IsHidden() && !Character->IsInCar() && Car.IsValid();
	bContextsAfterExit = PC->HasOnFootContext() && !PC->HasDrivingContext();
	ExitDistance = FVector::Dist2D(Character->GetActorLocation(), Car->GetActorLocation());
	Log(FString::Printf(TEXT("exit ok=%d contexts=%d distance=%.0f %s"), bExitOk ? 1 : 0, bContextsAfterExit ? 1 : 0, ExitDistance, *Character->Describe()));
	return true;
}

bool FGTM2TestRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
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
		if (Elapsed < 0.3f)
		{
			return false;   // let the car settle on its wheels first
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
	if (!Car.IsValid() || !Character.IsValid() || !PC.IsValid())
	{
		Fail(TEXT("car, character or controller vanished"));
	}
	else if (bWinchTest)
	{
		TickWinch(DeltaSeconds);
	}
	else
	{
		TickOnFoot(DeltaSeconds);
	}
	if (Elapsed > 60.f && !bDone)
	{
		Fail(FString::Printf(TEXT("overall timeout at step %d"), Step));
	}
	bOutPass = bPass;
	OutSummary = Summary;
	return bDone;
}

// ---- on foot -----------------------------------------------------------------------------------

void FGTM2TestRunner::TickOnFoot(float DeltaSeconds)
{
	UGTInteractionComponent* Interaction = Character->GetInteraction();
	UGTInventoryComponent* Inventory = Character->GetInventory();
	UGTConditionComponent* Condition = Car->GetCondition();
	switch (Step)
	{
	case 0:   // props, then walk forward with head bob
		if (!bStepStarted)
		{
			bStepStarted = true;
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Node = World->SpawnActor<AGTHarvestNode>(AGTHarvestNode::StaticClass(), CarLocal(FVector(700.f, 250.f, 30.f)), FRotator::ZeroRotator, Params);
			Wreck = World->SpawnActor<AGTWreck>(AGTWreck::StaticClass(), CarLocal(FVector(700.f, -450.f, 55.f)), FRotator::ZeroRotator, Params);
			WalkStart = Character->GetActorLocation();
			AimAt(Character->GetActorLocation() + Car->GetActorForwardVector() * 1000.f);
			Log(FString::Printf(TEXT("node=%s wreck=%s, walking"), *GetNameSafe(Node.Get()), *GetNameSafe(Wreck.Get())));
		}
		Character->AddMovementInput(Character->GetActorForwardVector(), 1.f);
		BobMax = FMath::Max(BobMax, FMath::Abs(Character->GetBobOffset().Z));
		if (StepTime >= 1.5f)
		{
			WalkDistance = FVector::Dist2D(Character->GetActorLocation(), WalkStart);
			Character->bHeadBobEnabled = false;
			Log(FString::Printf(TEXT("walked %.0f cm, bobMax=%.2f cm, bob now off"), WalkDistance, BobMax));
			Next();
		}
		break;
	case 1:   // keep walking with the bob off
		Character->AddMovementInput(Character->GetActorForwardVector(), 1.f);
		if (StepTime >= 0.6f)
		{
			BobAfterOff = FMath::Abs(Character->GetBobOffset().Z);
			Character->bHeadBobEnabled = true;
			Log(FString::Printf(TEXT("bob after off=%.2f cm speed=%.0f"), BobAfterOff, Character->GetVelocity().Size2D()));
			Next();
		}
		break;
	case 2:   // look at the node bare-handed
		if (!bStepStarted)
		{
			bStepStarted = true;
			Character->SelectTool(-1);
			TeleportCharacter(Node->GetActorLocation() + FVector(-200.f, 0.f, -30.f), Node->GetActorLocation());
		}
		if (StepTime >= 0.4f)
		{
			bBareHandsRefused = TargetIs(Node.Get()) && !Interaction->IsOfferAvailable() && PromptContains(TEXT("cutter"));
			Log(FString::Printf(TEXT("bare hands: %s -> refused=%d"), *Interaction->Describe(), bBareHandsRefused ? 1 : 0));
			Character->SelectToolByTag(GTTags::Tool_Cut);
			Next();
		}
		break;
	case 3:   // harvest with the cutter
		if (StepTime >= 0.3f && !bStepStarted)
		{
			bStepStarted = true;
			bCutterOffered = TargetIs(Node.Get()) && Interaction->IsOfferAvailable();
			Log(FString::Printf(TEXT("cutter: %s -> offered=%d"), *Interaction->Describe(), bCutterOffered ? 1 : 0));
			Interaction->SetHoldInput(true);
		}
		if (Node->HarvestCount >= 1)
		{
			Interaction->SetHoldInput(false);
			WireAfterHarvest = Inventory->CountOf(GTItems::Wire);
			Log(FString::Printf(TEXT("harvested: %s | %s"), *Node->Describe(), *Inventory->Describe()));
			Next();
		}
		else if (StepTimedOut(6.f, TEXT("the harvest")))
		{
			return;
		}
		break;
	case 4:   // field repair of the radiator with the kit
		if (!bStepStarted)
		{
			bStepStarted = true;
			Condition->DamagePart(EGTCarPart::Radiator, 0.6f);
			Inventory->Add(GTItems::Scrap, 4);
			Character->SelectToolByTag(GTTags::Tool_Repair);
			TeleportCharacter(CarLocal(FVector(450.f, 0.f, 0.f)), CarLocal(FVector(230.f, 0.f, 70.f)));
		}
		if (StepTime >= 0.4f && !bRepairOffered)
		{
			bRepairOffered = TargetIs(Car.Get()) && Interaction->IsOfferAvailable() && PromptContains(TEXT("Repair"));
			Log(FString::Printf(TEXT("repair kit: %s -> offered=%d radiator=%.2f"), *Interaction->Describe(), bRepairOffered ? 1 : 0, Condition->GetPartHealth(EGTCarPart::Radiator)));
			if (!bRepairOffered)
			{
				Fail(TEXT("repair not offered on the damaged front"));
				return;
			}
			Interaction->SetHoldInput(true);
		}
		if (Car->FieldRepairs >= 1)
		{
			Interaction->SetHoldInput(false);
			RadiatorAfterRepair = Condition->GetPartHealth(EGTCarPart::Radiator);
			ScrapAfterRepair = Inventory->CountOf(GTItems::Scrap);
			Log(FString::Printf(TEXT("repaired: radiator=%.2f scrap=%d"), RadiatorAfterRepair, ScrapAfterRepair));
			Next();
		}
		else if (StepTimedOut(8.f, TEXT("the repair")))
		{
			return;
		}
		break;
	case 5:   // boot transfer and the weight limit, then a jump
		if (!bStepStarted)
		{
			bStepStarted = true;
			Inventory->TransferTo(Car->GetBoot(), GTItems::Wire, 99);
			BootWire = Car->GetBoot()->CountOf(GTItems::Wire);
			OverfillAccepted = Inventory->Add(GTItems::Scrap, 100);
			bWeightRespected = Inventory->GetTotalWeightKg() <= Inventory->MaxWeightKg + 0.01f && OverfillAccepted < 100;
			Log(FString::Printf(TEXT("boot wire=%d overfill accepted=%d weightOk=%d | me %s | boot %s"), BootWire, OverfillAccepted, bWeightRespected ? 1 : 0, *Inventory->Describe(), *Car->GetBoot()->Describe()));
			JumpStartZ = Character->GetActorLocation().Z;
			Character->Jump();
		}
		JumpPeak = FMath::Max(JumpPeak, Character->GetActorLocation().Z - JumpStartZ);
		bJumpLeftGround |= Character->GetCharacterMovement()->IsFalling();
		if (StepTime >= 1.5f)
		{
			Character->StopJumping();
			bJumpLanded = Character->GetCharacterMovement()->IsMovingOnGround();
			Log(FString::Printf(TEXT("jump: peak %.0f cm leftGround=%d landed=%d"), JumpPeak, bJumpLeftGround ? 1 : 0, bJumpLanded ? 1 : 0));
			Next();
		}
		break;
	case 6:   // hazard drains exposure
		if (!bStepStarted)
		{
			bStepStarted = true;
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Hazard = World->SpawnActor<AGTHazardVolume>(AGTHazardVolume::StaticClass(), Character->GetActorLocation(), FRotator::ZeroRotator, Params);
			if (Hazard.IsValid())
			{
				Hazard->ExposureDrainPerSecond = 20.f;
			}
		}
		if (StepTime >= 2.f)
		{
			ExposureAfterHazard = Character->GetExposure()->Exposure;
			Log(FString::Printf(TEXT("after 2 s in the hazard: %s inside=%d"), *Character->GetExposure()->Describe(), Hazard.IsValid() ? Hazard->CharactersInside : -1));
			Next();
		}
		break;
	case 7:   // back in the car, exposure recovers
		if (!bStepStarted)
		{
			bStepStarted = true;
			AGTCarPawn* TheCar = Car.Get();
			const bool bEntered = PC->EnterCar();
			bEnterOk = bEntered && PC->GetPawn() == Car.Get() && Character->IsHidden() && Character->IsInCar();
			bContextsAfterEnter = PC->HasDrivingContext() && !PC->HasOnFootContext();
			bSameCar = PC->GetCar() == TheCar;
			ExposureAtEntry = Character->GetExposure()->Exposure;
			Car->DisableInput(PC.Get());
			Car->ResetDrivingInputs();
			Log(FString::Printf(TEXT("enter ok=%d contexts=%d sameCar=%d exposure=%.0f"), bEnterOk ? 1 : 0, bContextsAfterEnter ? 1 : 0, bSameCar ? 1 : 0, ExposureAtEntry));
		}
		if (StepTime >= 2.f)
		{
			ExposureAfterCar = Character->GetExposure()->Exposure;
			const bool bAll = bExitOk && bContextsAfterExit && ExitDistance > 120.f && ExitDistance < 300.f && WalkDistance > 200.f && BobMax > 0.5f
				&& BobAfterOff < 0.3f && bBareHandsRefused && bCutterOffered && WireAfterHarvest >= 2 && bRepairOffered && RadiatorAfterRepair > 0.85f
				&& ScrapAfterRepair == 2 && BootWire >= 2 && bWeightRespected && ExposureAfterHazard < 75.f && bEnterOk && bContextsAfterEnter && bSameCar
				&& ExposureAfterCar > ExposureAtEntry + 10.f && bJumpLeftGround && bJumpLanded && JumpPeak > 60.f && JumpPeak < 120.f;
			Finish(bAll, FString::Printf(TEXT("on foot: exit=%d contexts=%d exitDist=%.0f walked=%.0f bobMax=%.2f bobOff=%.2f bareRefused=%d cutterOffered=%d wire=%d repairOffered=%d radiator=%.2f scrap=%d bootWire=%d overfill=%d weightOk=%d exposureHazard=%.0f enter=%d contextsBack=%d sameCar=%d exposureCar=%.0f->%.0f arms=%d tools=%s input=%s jump=%.0fcm leftGround=%d landed=%d"),
				bExitOk ? 1 : 0, bContextsAfterExit ? 1 : 0, ExitDistance, WalkDistance, BobMax, BobAfterOff, bBareHandsRefused ? 1 : 0, bCutterOffered ? 1 : 0, WireAfterHarvest,
				bRepairOffered ? 1 : 0, RadiatorAfterRepair, ScrapAfterRepair, BootWire, OverfillAccepted, bWeightRespected ? 1 : 0, ExposureAfterHazard, bEnterOk ? 1 : 0,
				bContextsAfterEnter ? 1 : 0, bSameCar ? 1 : 0, ExposureAtEntry, ExposureAfterCar, Character->bHasArms ? 1 : 0,
				Character->bToolsFromAssets ? TEXT("assets") : TEXT("runtime"), Character->bInputFromAssets ? TEXT("assets") : TEXT("runtime"), JumpPeak, bJumpLeftGround ? 1 : 0, bJumpLanded ? 1 : 0));
		}
		break;
	default:
		Fail(TEXT("unknown step"));
		break;
	}
}

// ---- winch -------------------------------------------------------------------------------------

void FGTM2TestRunner::TickWinch(float DeltaSeconds)
{
	UGTInteractionComponent* Interaction = Character->GetInteraction();
	UGTWinchComponent* Winch = Car->GetWinch();
	if (!Winch)
	{
		Fail(TEXT("the car has no winch component"));
		return;
	}
	switch (Step)
	{
	case 0:   // take the hook at the nose
		if (!bStepStarted)
		{
			bStepStarted = true;
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			StrongAnchor = World->SpawnActor<AGTWinchAnchor>(AGTWinchAnchor::StaticClass(), CarLocal(FVector(2400.f, 0.f, 0.f)), FRotator::ZeroRotator, Params);
			if (StrongAnchor.IsValid())
			{
				StrongAnchor->GetAnchor()->StrengthN = 200000.f;
				StrongAnchor->GetAnchor()->DisplayName = TEXT("strong post");
			}
			Character->SelectTool(-1);
			TeleportCharacter(CarLocal(FVector(450.f, 0.f, 0.f)), CarLocal(FVector(230.f, 0.f, 70.f)));
		}
		if (StepTime >= 0.4f && !bHookOffered)
		{
			bHookOffered = TargetIs(Car.Get()) && Interaction->IsOfferAvailable() && PromptContains(TEXT("hook"));
			Log(FString::Printf(TEXT("at the nose: %s -> hookOffered=%d"), *Interaction->Describe(), bHookOffered ? 1 : 0));
			if (!bHookOffered)
			{
				Fail(TEXT("the hook was not offered at the nose"));
				return;
			}
			Interaction->SetHoldInput(true);
		}
		if (Winch->GetState() == EGTWinchState::HookCarried)
		{
			Interaction->SetHoldInput(false);
			bHookTaken = Character->IsCarryingHook();
			Log(FString::Printf(TEXT("hook taken=%d %s"), bHookTaken ? 1 : 0, *Winch->Describe()));
			Next();
		}
		else if (StepTimedOut(4.f, TEXT("the hook")))
		{
			return;
		}
		break;
	case 1:   // walk past the cable length: the tether must stop the character
		if (!bStepStarted)
		{
			bStepStarted = true;
			TeleportCharacter(CarLocal(FVector(2000.f, 400.f, 0.f)), CarLocal(FVector(6000.f, 400.f, 160.f)));
			Character->SetSprintHeld(true);
		}
		Character->AddMovementInput(Character->GetActorForwardVector(), 1.f);
		MaxHookDistance = FMath::Max(MaxHookDistance, FVector::Dist(Character->GetActorLocation(), Winch->GetMountLocation()));
		if (StepTime >= 3.f)
		{
			Character->SetSprintHeld(false);
			bTetherOk = MaxHookDistance <= Winch->CableLength + 80.f && Winch->TetherClamps > 0;
			Log(FString::Printf(TEXT("tether: maxDistance=%.0f (cable %.0f) clamps=%d ok=%d"), MaxHookDistance, Winch->CableLength, Winch->TetherClamps, bTetherOk ? 1 : 0));
			Next();
		}
		break;
	case 2:   // hook the post
		if (!bStepStarted)
		{
			bStepStarted = true;
			TeleportCharacter(StrongAnchor->GetActorLocation() + FVector(-180.f, 0.f, 0.f), StrongAnchor->GetActorLocation() + FVector(0.f, 0.f, 60.f));
		}
		if (StepTime >= 0.4f && !bAttachOffered)
		{
			bAttachOffered = TargetIs(StrongAnchor.Get()) && Interaction->IsOfferAvailable();
			Log(FString::Printf(TEXT("at the post: %s -> attachOffered=%d"), *Interaction->Describe(), bAttachOffered ? 1 : 0));
			if (!bAttachOffered)
			{
				Fail(TEXT("attach was not offered at the post"));
				return;
			}
			Interaction->SetHoldInput(true);
		}
		if (Winch->GetState() == EGTWinchState::Attached)
		{
			if (AttachedAt < 0.f)
			{
				Interaction->SetHoldInput(false);
				AttachedAt = StepTime;
				bAttached = !Character->IsCarryingHook();
				Log(FString::Printf(TEXT("attached=%d %s"), bAttached ? 1 : 0, *Winch->Describe()));
			}
			else if (StepTime - AttachedAt >= 0.3f)
			{
				// Section 51: empty-handed at the post the winch holds, E now offers to take the hook off (read, not pressed).
				bDetachOffered = TargetIs(StrongAnchor.Get()) && Interaction->IsOfferAvailable() && PromptContains(TEXT("Detach"));
				Log(FString::Printf(TEXT("at the post, hooked: %s -> detachOffered=%d"), *Interaction->Describe(), bDetachOffered ? 1 : 0));
				Next();
			}
		}
		else if (StepTimedOut(4.f, TEXT("the attach")))
		{
			return;
		}
		break;
	case 3:   // section 51: at the nose with the hook out on the post, E offers "Release winch" (read, not pressed)
		if (!bStepStarted)
		{
			bStepStarted = true;
			TeleportCharacter(CarLocal(FVector(450.f, 0.f, 0.f)), CarLocal(FVector(230.f, 0.f, 70.f)));
		}
		if (StepTime >= 0.4f)
		{
			bFrontReleaseOffered = TargetIs(Car.Get()) && Interaction->IsOfferAvailable() && PromptContains(TEXT("Release winch"));
			Log(FString::Printf(TEXT("at the nose, hooked: %s -> releaseOffered=%d"), *Interaction->Describe(), bFrontReleaseOffered ? 1 : 0));
			Next();
		}
		break;
	case 4:   // back in the seat
		if (!bStepStarted)
		{
			bStepStarted = true;
			const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
			Character->SetActorLocation(Car->FindExitLocation(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight()), false, nullptr, ETeleportType::TeleportPhysics);
			PC->EnterCar();
			Car->DisableInput(PC.Get());
			Car->ResetDrivingInputs();
			Log(FString::Printf(TEXT("entered: driving=%d %s"), PC->IsDriving() ? 1 : 0, *Winch->Describe()));
		}
		if (StepTime >= 0.3f)
		{
			Next();
		}
		break;
	case 5:   // reel: the car must come toward the post
		if (!bStepStarted)
		{
			bStepStarted = true;
			ReelStart = Car->GetActorLocation();
			Winch->SetReeling(true);
		}
		ReelMaxTension = FMath::Max(ReelMaxTension, Winch->GetTensionN());
		if (FMath::IsNearlyEqual(FMath::Fmod(StepTime, 1.f), 0.f, DeltaSeconds * 0.6f))
		{
			Log(FString::Printf(TEXT("reeling: carX=%.0f speed=%.0f %s"), Car->GetActorLocation().X, Car->GetVelocity().Size2D(), *Winch->Describe()));
		}
		if (StepTime >= 6.f)
		{
			Winch->SetReeling(false);
			const FVector ToAnchor = (StrongAnchor->GetActorLocation() - ReelStart).GetSafeNormal2D();
			PullDistance = FVector::DotProduct(Car->GetActorLocation() - ReelStart, ToAnchor);
			bReelOk = PullDistance > 300.f && Winch->GetState() == EGTWinchState::Attached;
			Log(FString::Printf(TEXT("reel: pulled %.0f cm maxTension=%.0f N ok=%d %s"), PullDistance, ReelMaxTension, bReelOk ? 1 : 0, *Winch->Describe()));
			Next();
		}
		break;
	case 6:   // section 51: G / DPad Up in the seat lets go; the drawn cable rewinds to the drum; then the post is hooked again
		if (!bStepStarted)
		{
			bStepStarted = true;
			bAttachedBeforeRelease = Winch->GetState() == EGTWinchState::Attached;
			// The keys: IA_ReleaseWinch must sit on G and DPad Up in the driving context this car runs on.
			if (Car->DefaultMappingContext && Car->ReleaseWinchAction)
			{
				for (const FEnhancedActionKeyMapping& Mapping : Car->DefaultMappingContext->GetMappings())
				{
					if (Mapping.Action == Car->ReleaseWinchAction)
					{
						bReleaseOnG |= Mapping.Key == EKeys::G;
						bReleaseOnDPadUp |= Mapping.Key == EKeys::Gamepad_DPad_Up;
					}
				}
			}
			// Under load first: the handbrake on and the drum reeling, so the release has a pull to take away (at the end
			// of the reel the car coasts toward the post on a slack cable, and a release there proves nothing).
			if (UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement())
			{
				Move->SetHandbrakeInput(true);
			}
			Winch->SetReeling(true);
			Log(FString::Printf(TEXT("release: loading the cable (handbrake on, reeling) %s"), *Winch->Describe()));
			break;
		}
		if (PressedAt < 0.f)
		{
			if (Winch->GetTensionN() < 2000.f && StepTime < 2.f)
			{
				break;
			}
			PressedAt = StepTime;
			TensionBeforeRelease = Winch->GetTensionN();
			bAttachedBeforeRelease = Winch->GetState() == EGTWinchState::Attached;
			// The key path: the action goes into the player's Enhanced Input the way a key press reaches it, through the
			// car's binding, with the car's input on for this step (the test keeps it off everywhere else).
			ULocalPlayer* LocalPlayer = PC->GetLocalPlayer();
			UEnhancedInputLocalPlayerSubsystem* Subsystem = LocalPlayer ? ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(LocalPlayer) : nullptr;
			if (!Subsystem || !Car->ReleaseWinchAction)
			{
				Fail(TEXT("no Enhanced Input subsystem or no IA_ReleaseWinch to press"));
				return;
			}
			Car->EnableInput(PC.Get());
			Subsystem->InjectInputForAction(Car->ReleaseWinchAction, FInputActionValue(true), TArray<UInputModifier*>(), TArray<UInputTrigger*>());
			Log(FString::Printf(TEXT("release: IA_ReleaseWinch pressed at %.2f s under %.0f N (mapped on G=%d DPadUp=%d) %s"), StepTime, TensionBeforeRelease,
				bReleaseOnG ? 1 : 0, bReleaseOnDPadUp ? 1 : 0, *Winch->Describe()));
			break;
		}
		if (ReleasedAt < 0.f)
		{
			if (Winch->GetState() == EGTWinchState::Stowed)
			{
				ReleasedAt = StepTime;
				Car->DisableInput(PC.Get());
				Car->ResetDrivingInputs();
				bReleasedByAction = bAttachedBeforeRelease;
				TensionAtRelease = Winch->GetTensionN();
				RewindStartCm = Winch->GetDrawnCableCm();
				LastDrawnCm = RewindStartCm;
				Log(FString::Printf(TEXT("released %.3f s after the press: tension %.0f -> %.0f N, reeling %d, drawn %.0f cm, rewinding at %.0f cm/s %s"),
					StepTime - PressedAt, TensionBeforeRelease, TensionAtRelease, Winch->IsReeling() ? 1 : 0, RewindStartCm, Winch->RewindSpeed, *Winch->Describe()));
			}
			else if (StepTime - PressedAt >= 1.f)
			{
				Fail(FString::Printf(TEXT("IA_ReleaseWinch did not reach the winch in 1 s: %s"), *Winch->Describe()));
				return;
			}
			break;
		}
		{
			// The drawn length every tick until the cable is in and hidden; the pull must stay off the whole time.
			const float Drawn = Winch->GetDrawnCableCm();
			++RewindTicks;
			bRewindMonotone &= Drawn <= LastDrawnCm + 0.01f;
			LastDrawnCm = Drawn;
			MaxTensionAfterRelease = FMath::Max(MaxTensionAfterRelease, Winch->GetTensionN());
			if (FMath::IsNearlyEqual(FMath::Fmod(StepTime - ReleasedAt, 0.5f), 0.f, DeltaSeconds * 0.6f))
			{
				Log(FString::Printf(TEXT("rewinding: %.2f s after the release, drawn %.0f cm"), StepTime - ReleasedAt, Drawn));
			}
			if (Drawn <= 0.f)
			{
				RewindSeconds = StepTime - ReleasedAt;
				bRewindHidden = !Winch->IsRewinding() && Winch->GetState() == EGTWinchState::Stowed;
				Log(FString::Printf(TEXT("rewound: %.0f cm in %.2f s over %d ticks (monotone=%d, hidden=%d, max tension after the release %.0f N) %s"),
					RewindStartCm, RewindSeconds, RewindTicks, bRewindMonotone ? 1 : 0, bRewindHidden ? 1 : 0, MaxTensionAfterRelease, *Winch->Describe()));
				Winch->AttachTo(StrongAnchor->GetAnchor());
				bReattached = Winch->GetState() == EGTWinchState::Attached;
				WinchAttachesAfter = Winch->AttachCount;
				AnchorAttachesAfter = StrongAnchor->GetAnchor()->AttachCount;
				Log(FString::Printf(TEXT("hooked again=%d: winch attaches %d, post attaches %d %s"), bReattached ? 1 : 0, WinchAttachesAfter, AnchorAttachesAfter, *Winch->Describe()));
				Next();
			}
			else if (StepTime - ReleasedAt > 15.f)
			{
				Fail(FString::Printf(TEXT("the cable did not rewind in 15 s: drawn %.0f cm %s"), Drawn, *Winch->Describe()));
				return;
			}
		}
		break;
	case 7:   // a wall between car and post: the cable must snap
		if (!bStepStarted)
		{
			bStepStarted = true;
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Wall = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), CarLocal(FVector(240.f + 25.f + 150.f, 0.f, 150.f)), Car->GetActorRotation(), Params);
			UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
			if (Wall.IsValid() && Cube)
			{
				Wall->SetMobility(EComponentMobility::Movable);
				Wall->GetStaticMeshComponent()->SetStaticMesh(Cube);
				Wall->SetActorScale3D(FVector(0.5f, 6.f, 3.f));
				Wall->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
			}
			Winch->SetReeling(true);
		}
		if (FMath::IsNearlyEqual(FMath::Fmod(StepTime, 1.f), 0.f, DeltaSeconds * 0.6f))
		{
			Log(FString::Printf(TEXT("against the wall: speed=%.0f %s"), Car->GetVelocity().Size2D(), *Winch->Describe()));
		}
		if (Winch->GetState() == EGTWinchState::Snapped)
		{
			Winch->SetReeling(false);
			bSnapped = Winch->CableSnaps == 1;
			WinchHealthAfterSnap = Car->GetCondition()->GetPartHealth(EGTCarPart::Winch);
			Log(FString::Printf(TEXT("snapped: winchHealth=%.2f %s"), WinchHealthAfterSnap, *Winch->Describe()));
			Next();
		}
		else if (StepTimedOut(10.f, TEXT("the snap")))
		{
			return;
		}
		break;
	case 8:   // a weak anchor ahead tears out: the handbrake holds the car against the pull
		if (!bStepStarted)
		{
			bStepStarted = true;
			if (Wall.IsValid())
			{
				Wall->Destroy();
			}
			Winch->Release();
			// The anchor sat 15 m to the side until driving feel stage 1: with tyres that let go, a car pulled sideways
			// from its bumper pivots and rolls toward the anchor, so the tension never holds above the post's strength.
			// Ahead, with the rear wheels locked, the pull is straight and the post is the weakest link.
			if (UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement())
			{
				Move->SetHandbrakeInput(true);
			}
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			WeakAnchor = World->SpawnActor<AGTWinchAnchor>(AGTWinchAnchor::StaticClass(), CarLocal(FVector(1500.f, 0.f, 0.f)), FRotator::ZeroRotator, Params);
			if (!WeakAnchor.IsValid())
			{
				Fail(TEXT("could not spawn the weak anchor"));
				return;
			}
			WeakAnchor->GetAnchor()->StrengthN = 3000.f;
			WeakAnchor->GetAnchor()->DisplayName = TEXT("rotten post");
			Winch->AttachTo(WeakAnchor->GetAnchor());
			Winch->SetReeling(true);
		}
		if (FMath::IsNearlyEqual(FMath::Fmod(StepTime, 1.f), 0.f, DeltaSeconds * 0.6f))
		{
			Log(FString::Printf(TEXT("pulling the weak anchor: carSpeed=%.0f sideways=%.0f %s"), Car->GetVelocity().Size2D(),
				FVector::DotProduct(Car->GetVelocity(), Car->GetActorRightVector()), *Winch->Describe()));
		}
		if (WeakAnchor->GetAnchor()->bFailed)
		{
			bWeakFailed = Winch->AnchorFailures == 1 && Winch->GetState() == EGTWinchState::Stowed;
			Log(FString::Printf(TEXT("weak anchor failed=%d %s"), bWeakFailed ? 1 : 0, *Winch->Describe()));
			// Section 51's release: offered at the post and the nose, the action on G and DPad Up, attached -> stowed ->
			// attached, no pull from the release on, the drawn cable in over more than 0.2 s and hidden, two attaches each.
			const bool bReleaseOk = bDetachOffered && bFrontReleaseOffered && bReleaseOnG && bReleaseOnDPadUp && bReleasedByAction
				&& TensionBeforeRelease > 0.f && TensionAtRelease == 0.f && MaxTensionAfterRelease == 0.f && RewindSeconds > 0.2f && bRewindHidden && bRewindMonotone
				&& bReattached && WinchAttachesAfter == 2 && AnchorAttachesAfter == 2;
			const bool bAll = bHookOffered && bHookTaken && bTetherOk && bAttachOffered && bAttached && bReelOk && bSnapped && WinchHealthAfterSnap < 1.f && bWeakFailed
				&& bReleaseOk;
			Finish(bAll, FString::Printf(TEXT("winch: release ok=%d (offered post=%d nose=%d, keys G=%d DPadUp=%d, by the action=%d, tension %.0f -> %.0f/%.0f N, rewind %.0f cm in %.2f s at %.0f cm/s, %d ticks, monotone=%d hidden=%d, attaches winch %d post %d) hookOffered=%d taken=%d tether maxDist=%.0f clamps=%d ok=%d attachOffered=%d attached=%d pulled=%.0f cm maxTension=%.0f N reelOk=%d snapped=%d winchHealth=%.2f weakFailed=%d"),
				bReleaseOk ? 1 : 0, bDetachOffered ? 1 : 0, bFrontReleaseOffered ? 1 : 0, bReleaseOnG ? 1 : 0, bReleaseOnDPadUp ? 1 : 0, bReleasedByAction ? 1 : 0,
				TensionBeforeRelease, TensionAtRelease, MaxTensionAfterRelease, RewindStartCm, RewindSeconds, Winch->RewindSpeed, RewindTicks, bRewindMonotone ? 1 : 0, bRewindHidden ? 1 : 0,
				WinchAttachesAfter, AnchorAttachesAfter,
				bHookOffered ? 1 : 0, bHookTaken ? 1 : 0, MaxHookDistance, Winch->TetherClamps, bTetherOk ? 1 : 0, bAttachOffered ? 1 : 0, bAttached ? 1 : 0,
				PullDistance, ReelMaxTension, bReelOk ? 1 : 0, bSnapped ? 1 : 0, WinchHealthAfterSnap, bWeakFailed ? 1 : 0));
		}
		else if (StepTimedOut(6.f, TEXT("the anchor failure")))
		{
			return;
		}
		break;
	default:
		Fail(TEXT("unknown step"));
		break;
	}
}
