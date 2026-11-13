#include "Vehicle/GTWinchComponent.h"

#include "Character/GTPlayerCharacter.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTWinchAnchor.h"

#include "CableComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Actor.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
	const TCHAR* StateName(EGTWinchState State)
	{
		switch (State)
		{
		case EGTWinchState::Stowed:      return TEXT("stowed");
		case EGTWinchState::HookCarried: return TEXT("hookCarried");
		case EGTWinchState::Attached:    return TEXT("attached");
		case EGTWinchState::Snapped:     return TEXT("snapped");
		default:                         return TEXT("?");
		}
	}
}

UGTWinchComponent::UGTWinchComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick
}

void UGTWinchComponent::BeginPlay()
{
	Super::BeginPlay();
	USkeletalMeshComponent* Body = GetOwner() ? GetOwner()->FindComponentByClass<USkeletalMeshComponent>() : nullptr;
	if (!Body)
	{
		return;
	}
	Cable = NewObject<UCableComponent>(GetOwner(), TEXT("WinchCable"));
	Cable->bAttachStart = true;
	Cable->bAttachEnd = true;
	Cable->CableLength = 100.f;
	Cable->NumSegments = 12;
	Cable->CableWidth = 2.5f;
	Cable->SolverIterations = 4;
	Cable->bEnableStiffness = false;
	Cable->bEnableCollision = true;      // particles sweep against the world so the rope lies on the ground instead of through it
	Cable->CollisionFriction = 0.2f;
	Cable->CableGravityScale = 0.5f;
	Cable->bResetAfterTeleport = true;
	Cable->EndLocation = FVector::ZeroVector;
	Cable->SetVisibility(false);
	Cable->RegisterComponent();
	Cable->AttachToComponent(Body, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
	Cable->SetRelativeLocation(MountOffset);
}

FVector UGTWinchComponent::GetMountLocation() const
{
	const USkeletalMeshComponent* Body = GetOwner() ? GetOwner()->FindComponentByClass<USkeletalMeshComponent>() : nullptr;
	return Body ? Body->GetComponentTransform().TransformPosition(MountOffset) : FVector::ZeroVector;
}

float UGTWinchComponent::GetCableDistance() const
{
	if (State == EGTWinchState::Attached && Anchor.IsValid())
	{
		return FVector::Dist(GetMountLocation(), Anchor->GetComponentLocation());
	}
	if (State == EGTWinchState::HookCarried && HookCarrier.IsValid())
	{
		return FVector::Dist(GetMountLocation(), HookCarrier->GetActorLocation());
	}
	return 0.f;
}

bool UGTWinchComponent::TakeHook(AGTPlayerCharacter* Character)
{
	if (!Character || !CanTakeHook())
	{
		return false;
	}
	State = EGTWinchState::HookCarried;
	HookCarrier = Character;
	ForgetAnchor();
	Anchor = nullptr;
	TensionN = 0.f;
	RewindRemainingCm = 0.f;   // taken off a rewinding cable: the hook goes to the hand
	Character->SetCarriedHook(Cast<AGTCarPawn>(GetOwner()));
	if (Cable)
	{
		Cable->SetAttachEndToComponent(Character->GetCapsuleComponent());
		Cable->EndLocation = FVector(0.f, 0.f, -70.f);
		Cable->SetVisibility(true);
	}
	UE_LOG(LogTemp, Display, TEXT("UGTWinchComponent: hook taken by %s"), *Character->GetName());
	return true;
}

void UGTWinchComponent::DropHook()
{
	if (State == EGTWinchState::HookCarried)
	{
		Release();
	}
}

bool UGTWinchComponent::AttachTo(UGTWinchAnchorComponent* NewAnchor)
{
	if (!NewAnchor || !NewAnchor->CanAttach())
	{
		return false;
	}
	if (AGTPlayerCharacter* Carrier = HookCarrier.Get())
	{
		Carrier->SetCarriedHook(nullptr);
	}
	HookCarrier = nullptr;
	ForgetAnchor();
	Anchor = NewAnchor;
	NewAnchor->HeldBy = this;
	State = EGTWinchState::Attached;
	RestLength = FMath::Max(MinRestLength, FVector::Dist(GetMountLocation(), NewAnchor->GetComponentLocation()));
	TensionN = 0.f;
	SnapTimer = 0.f;
	AnchorOverloadTimer = 0.f;
	RewindRemainingCm = 0.f;
	++AttachCount;
	++NewAnchor->AttachCount;
	if (Cable)
	{
		Cable->SetAttachEndToComponent(NewAnchor);
		Cable->EndLocation = FVector::ZeroVector;
		Cable->SetVisibility(true);
	}
	UE_LOG(LogTemp, Display, TEXT("UGTWinchComponent: attached to %s at %.0f cm"), *NewAnchor->DisplayName, RestLength);
	return true;
}

void UGTWinchComponent::Release()
{
	// Where the hook is before the anchor or the carrier is forgotten: the drawn cable runs back from there.
	bool bHookOut = false;
	FVector HookWorld = FVector::ZeroVector;
	if (Cable && Cable->IsVisible())
	{
		if (State == EGTWinchState::Attached && Anchor.IsValid())
		{
			HookWorld = Anchor->GetComponentLocation();
			bHookOut = true;
		}
		else if (State == EGTWinchState::HookCarried && HookCarrier.IsValid())
		{
			HookWorld = HookCarrier->GetActorLocation() + FVector(0.f, 0.f, -70.f);   // the hand, as TakeHook draws it
			bHookOut = true;
		}
	}
	if (AGTPlayerCharacter* Carrier = HookCarrier.Get())
	{
		Carrier->SetCarriedHook(nullptr);
	}
	HookCarrier = nullptr;
	ForgetAnchor();
	Anchor = nullptr;
	State = EGTWinchState::Stowed;
	TensionN = 0.f;   // the pull is gone now: Update applies no force while stowed, whatever the cable still draws
	SnapTimer = 0.f;
	AnchorOverloadTimer = 0.f;
	bReeling = false;
	if (!Cable)
	{
		return;
	}
	if (bHookOut && RewindSpeed > 0.f)
	{
		StartRewind(HookWorld);
	}
	else if (RewindRemainingCm <= 0.f)
	{
		Cable->SetAttachEndToComponent(nullptr);
		Cable->SetVisibility(false);
	}
}

float UGTWinchComponent::GetDrawnCableCm() const
{
	return (Cable && Cable->IsVisible()) ? Cable->CableLength : 0.f;
}

void UGTWinchComponent::ForgetAnchor()
{
	if (UGTWinchAnchorComponent* Held = Anchor.Get())
	{
		if (Held->HeldBy.Get() == this)
		{
			Held->HeldBy = nullptr;
		}
	}
}

void UGTWinchComponent::StartRewind(const FVector& HookWorld)
{
	// The end is held in the body's space (a null end component would mean the owner's root), so the hook rides with
	// the car while the drum takes the cable in: first whatever slack was paid out, then the straight run to the hook.
	USceneComponent* BodyComponent = Cable->GetAttachParent();
	const FTransform BodyTransform = BodyComponent ? BodyComponent->GetComponentTransform() : FTransform::Identity;
	const FVector HookLocal = BodyTransform.InverseTransformPosition(HookWorld);
	const FVector ToHook = HookLocal - MountOffset;
	RewindChordCm = ToHook.Size();
	RewindDirLocal = RewindChordCm > KINDA_SMALL_NUMBER ? ToHook / RewindChordCm : FVector::ForwardVector;
	RewindRemainingCm = FMath::Max(Cable->CableLength, RewindChordCm);
	Cable->SetAttachEndToComponent(BodyComponent);
	Cable->EndLocation = HookLocal;
	Cable->CableLength = RewindRemainingCm;
	Cable->SetVisibility(true);
	UE_LOG(LogTemp, Display, TEXT("UGTWinchComponent: released; the cable rewinds %.0f cm at %.0f cm/s"), RewindRemainingCm, RewindSpeed);
}

void UGTWinchComponent::UpdateRewind(float DeltaSeconds)
{
	if (!Cable)
	{
		RewindRemainingCm = 0.f;
		return;
	}
	RewindRemainingCm = FMath::Max(0.f, RewindRemainingCm - RewindSpeed * DeltaSeconds);
	if (RewindRemainingCm <= 0.f)
	{
		Cable->SetAttachEndToComponent(nullptr);
		Cable->EndLocation = FVector::ZeroVector;
		Cable->CableLength = 100.f;
		Cable->SetVisibility(false);
		return;
	}
	Cable->EndLocation = MountOffset + RewindDirLocal * FMath::Min(RewindRemainingCm, RewindChordCm);
	Cable->CableLength = RewindRemainingCm;
}

void UGTWinchComponent::Update(float DeltaSeconds, USkeletalMeshComponent& Body, UGTConditionComponent& Condition)
{
	switch (State)
	{
	case EGTWinchState::HookCarried:
		UpdateTether();
		break;
	case EGTWinchState::Attached:
		UpdatePull(DeltaSeconds, Body, Condition);
		break;
	default:
		TensionN = 0.f;
		if (RewindRemainingCm > 0.f)
		{
			UpdateRewind(DeltaSeconds);
		}
		break;
	}
	UpdateCableVisual();
}

void UGTWinchComponent::UpdateTether()
{
	AGTPlayerCharacter* Carrier = HookCarrier.Get();
	if (!Carrier || Carrier->IsInCar())
	{
		Release();
		return;
	}
	const FVector Mount = GetMountLocation();
	const FVector Delta = Carrier->GetActorLocation() - Mount;
	const float Distance = Delta.Size();
	if (Distance <= CableLength || Distance <= KINDA_SMALL_NUMBER)
	{
		return;
	}
	// Walking past the cable length stops you: pull the capsule back onto the circle and kill the outward velocity.
	const FVector Direction = Delta / Distance;
	const FVector Clamped = Mount + Direction * CableLength;
	Carrier->SetActorLocation(FVector(Clamped.X, Clamped.Y, Carrier->GetActorLocation().Z), true);
	if (UCharacterMovementComponent* Move = Carrier->GetCharacterMovement())
	{
		const float Outward = FVector::DotProduct(Move->Velocity, Direction);
		if (Outward > 0.f)
		{
			Move->Velocity -= Direction * Outward;
		}
	}
	++TetherClamps;
}

void UGTWinchComponent::UpdatePull(float DeltaSeconds, USkeletalMeshComponent& Body, UGTConditionComponent& Condition)
{
	UGTWinchAnchorComponent* Target = Anchor.Get();
	if (!Target || Target->bFailed)
	{
		Release();
		return;
	}
	const float Health = Condition.GetPartHealth(EGTCarPart::Winch);
	const float MaxPull = PullForceN * Health;
	const FVector Mount = GetMountLocation();
	const FVector Delta = Target->GetComponentLocation() - Mount;
	const float Distance = Delta.Size();
	const FVector Direction = Distance > KINDA_SMALL_NUMBER ? Delta / Distance : FVector::ForwardVector;

	// The motor shortens the rest length, slowing to a stall as the tension nears the rated pull.
	if (bReeling && MaxPull > 0.f)
	{
		const float Stall = FMath::Clamp(1.f - TensionN / MaxPull, 0.f, 1.f);
		RestLength = FMath::Max(MinRestLength, RestLength - ReelSpeed * Stall * DeltaSeconds);
	}

	const float Stretch = Distance - RestLength;
	const float StretchRate = DeltaSeconds > KINDA_SMALL_NUMBER ? (Stretch - LastStretch) / DeltaSeconds : 0.f;
	LastStretch = Stretch;
	const FVector MountVelocity = Body.GetPhysicsLinearVelocityAtPoint(Mount);
	const float Closing = FVector::DotProduct(MountVelocity, Direction);   // cm/s toward the anchor

	float Demand = 0.f;
	if (Stretch > 0.f)
	{
		Demand = FMath::Max(0.f, SpringNPerCm * Stretch + DampingNsPerCm * StretchRate);
	}
	TensionN = FMath::Min(Demand, MaxPull);
	MaxTensionN = FMath::Max(MaxTensionN, TensionN);
	if (TensionN > 0.f)
	{
		Body.AddForceAtLocation(Direction * TensionN * 100.f, Mount);   // N -> kg cm/s^2
	}

	// Anchor failure: more tension than the anchor holds, for long enough to rule out a spike.
	if (TensionN > Target->StrengthN)
	{
		AnchorOverloadTimer += DeltaSeconds;
		if (AnchorOverloadTimer >= AnchorFailDelay)
		{
			++AnchorFailures;
			UE_LOG(LogTemp, Display, TEXT("UGTWinchComponent: anchor %s failed at %.0f N (strength %.0f)"), *Target->DisplayName, TensionN, Target->StrengthN);
			Target->Fail(-Direction);
			Release();
			return;
		}
	}
	else
	{
		AnchorOverloadTimer = 0.f;
	}

	// Cable snap: pulling at the limit against something that will not come.
	if (TensionN >= BreakForceN && Closing < StallSpeed)
	{
		SnapTimer += DeltaSeconds;
		if (SnapTimer >= SnapDelay)
		{
			Snap(Body, Condition, Direction);
		}
	}
	else
	{
		SnapTimer = 0.f;
	}
}

void UGTWinchComponent::Snap(USkeletalMeshComponent& Body, UGTConditionComponent& Condition, const FVector& Direction)
{
	++CableSnaps;
	UE_LOG(LogTemp, Display, TEXT("UGTWinchComponent: cable snapped at %.0f N"), TensionN);
	Condition.DamagePart(EGTCarPart::Winch, SnapDamage);
	// The whip: the car lurches back as the tension vanishes.
	Body.AddImpulse(-Direction * SnapRecoilSpeed * Body.GetMass(), NAME_None, /*bVelChange*/ false);
	ForgetAnchor();
	Anchor = nullptr;
	State = EGTWinchState::Snapped;
	TensionN = 0.f;
	SnapTimer = 0.f;
	bReeling = false;
	RewindRemainingCm = 0.f;
	if (Cable)
	{
		Cable->SetAttachEndToComponent(nullptr);
		Cable->SetVisibility(false);
	}
}

void UGTWinchComponent::UpdateCableVisual()
{
	if (!Cable)
	{
		return;
	}
	switch (State)
	{
	case EGTWinchState::Attached:
		// Taut when the winch is holding the car, slack only when the car has come closer than the drum paid out.
		Cable->CableLength = FMath::Max(50.f, TensionN > 0.f ? GetCableDistance() : FMath::Min(RestLength, GetCableDistance() * 1.2f));
		break;
	case EGTWinchState::HookCarried:
		Cable->CableLength = FMath::Max(50.f, GetCableDistance() * 1.02f);
		break;
	default:
		break;
	}
}

FString UGTWinchComponent::Describe() const
{
	return FString::Printf(TEXT("winch %s dist=%.0f rest=%.0f tension=%.0fN max=%.0fN reel=%d snaps=%d anchorFails=%d clamps=%d attaches=%d drawn=%.0f"),
		StateName(State), GetCableDistance(), RestLength, TensionN, MaxTensionN, bReeling ? 1 : 0, CableSnaps, AnchorFailures, TetherClamps, AttachCount,
		GetDrawnCableCm());
}
