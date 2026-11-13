#include "Character/GTPlayerCharacter.h"

#include "Character/GTExposureComponent.h"
#include "Core/GTGameplayTags.h"
#include "Core/GTPlayerController.h"
#include "Crafting/GTCraftingStation.h"
#include "Environment/GTEnvironmentComponent.h"
#include "Parts/GTItemDefinition.h"
#include "Parts/GTItemRegistry.h"
#include "Parts/GTPartSlotsComponent.h"
#include "Vehicle/GTConditionComponent.h"
#include "Interaction/GTInteractionComponent.h"
#include "Run/GTLegDefinition.h"
#include "Run/GTRunGameState.h"
#include "Weather/GTWeatherSubsystem.h"
#include "Inventory/GTInventoryComponent.h"
#include "Tools/GTToolDefinition.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTWinchComponent.h"

#include "Animation/AnimSequence.h"
#include "AnimationRuntime.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	/** Legacy input scales are on (DefaultInput.ini): yaw x2.5, pitch x-2.5. 0.4 makes one unit one degree. */
	constexpr float LegacyLookScaleCompensation = 0.4f;

	UInputAction* MakeAction(UObject* Outer, const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* Action = NewObject<UInputAction>(Outer, Name);
		Action->ValueType = Type;
		return Action;
	}

	enum class EMod : uint8 { None, Negate, SwizzleY, SwizzleYNegate, DeadZone };

	void MapKey(UInputMappingContext* Context, UInputAction* Action, const FKey& Key, EMod Mod = EMod::None)
	{
		FEnhancedActionKeyMapping& Mapping = Context->MapKey(Action, Key);
		switch (Mod)
		{
		case EMod::Negate:
			Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(Context));
			break;
		case EMod::SwizzleY:
		case EMod::SwizzleYNegate:
		{
			UInputModifierSwizzleAxis* Swizzle = NewObject<UInputModifierSwizzleAxis>(Context);
			Swizzle->Order = EInputAxisSwizzle::YXZ;
			Mapping.Modifiers.Add(Swizzle);
			if (Mod == EMod::SwizzleYNegate)
			{
				Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(Context));
			}
			break;
		}
		case EMod::DeadZone:
		{
			UInputModifierDeadZone* DeadZone = NewObject<UInputModifierDeadZone>(Context);
			DeadZone->LowerThreshold = 0.2f;
			DeadZone->UpperThreshold = 0.98f;
			Mapping.Modifiers.Add(DeadZone);
			break;
		}
		default:
			break;
		}
	}
}

AGTPlayerCharacter::AGTPlayerCharacter()
{
	PrimaryActorTick.bCanEverTick = true;

	GetCapsuleComponent()->InitCapsuleSize(34.f, 96.f);
	bUseControllerRotationYaw = true;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->MaxWalkSpeed = WalkSpeed;
	Move->BrakingDecelerationWalking = 2000.f;
	Move->GroundFriction = 8.f;
	Move->JumpZVelocity = JumpVelocity;   // a plain jump; still no platforming content (PROJECT_PLAN)
	Move->AirControl = 0.2f;
	Move->bOrientRotationToMovement = false;

	// No full body: the inherited mesh stays empty (no shadow body, ARCHITECTURE 9a).
	GetMesh()->SetOwnerNoSee(true);
	GetMesh()->SetCollisionProfileName(TEXT("NoCollision"));

	CameraRoot = CreateDefaultSubobject<USceneComponent>(TEXT("CameraRoot"));
	CameraRoot->SetupAttachment(GetCapsuleComponent());
	CameraRoot->SetRelativeLocation(FVector(0.f, 0.f, EyeHeight));

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(CameraRoot);
	Camera->bUsePawnControlRotation = true;
	Camera->SetFieldOfView(90.f);
	Camera->bEnableFirstPersonFieldOfView = true;
	Camera->FirstPersonFieldOfView = 70.f;
	Camera->bEnableFirstPersonScale = true;
	Camera->FirstPersonScale = 0.6f;

	Arms = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Arms"));
	Arms->SetupAttachment(Camera);
	Arms->SetOnlyOwnerSee(true);
	Arms->FirstPersonPrimitiveType = EFirstPersonPrimitiveType::FirstPerson;
	Arms->SetCollisionProfileName(TEXT("NoCollision"));
	Arms->CastShadow = false;
	Arms->bCastDynamicShadow = false;

	ToolMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ToolMesh"));
	ToolMesh->SetupAttachment(Camera);
	ToolMesh->SetOnlyOwnerSee(true);
	ToolMesh->FirstPersonPrimitiveType = EFirstPersonPrimitiveType::FirstPerson;
	ToolMesh->SetCollisionProfileName(TEXT("NoCollision"));
	ToolMesh->CastShadow = false;
	ToolMesh->SetVisibility(false);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		ToolMesh->SetStaticMesh(CubeMesh.Object);
	}

	Interaction = CreateDefaultSubobject<UGTInteractionComponent>(TEXT("Interaction"));
	Inventory = CreateDefaultSubobject<UGTInventoryComponent>(TEXT("Inventory"));
	Inventory->MaxWeightKg = 40.f;
	Exposure = CreateDefaultSubobject<UGTExposureComponent>(TEXT("Exposure"));
}

void AGTPlayerCharacter::BeginPlay()
{
	Super::BeginPlay();
	BaseFov = Camera->FieldOfView;
	CurrentFov = BaseFov;
	LoadArms();
	LoadTools();
	SelectTool(-1);
}

void AGTPlayerCharacter::LoadArms()
{
	USkeletalMesh* ArmsMesh = LoadObject<USkeletalMesh>(nullptr, *ArmsMeshPath);
	if (!ArmsMesh)
	{
		UE_LOG(LogTemp, Warning, TEXT("AGTPlayerCharacter: no arms mesh at %s (run Art/setup_m2_character.bat); playing without arms"), *ArmsMeshPath);
		bHasArms = false;
		return;
	}
	Arms->SetSkeletalMeshAsset(ArmsMesh);
	bHasArms = true;
	if (UAnimSequence* Pose = LoadObject<UAnimSequence>(nullptr, *ArmsPosePath))
	{
		Arms->PlayAnimation(Pose, true);
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("AGTPlayerCharacter: no arms pose at %s; reference pose"), *ArmsPosePath);
	}
	for (const FName& Bone : HiddenBones)
	{
		if (Arms->GetBoneIndex(Bone) != INDEX_NONE)
		{
			Arms->HideBoneByName(Bone, PBO_None);
		}
	}
	// Mannequins face +Y; turn them to the camera's +X and put the head bone at ArmsHeadOffset from the eye.
	Arms->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));
	const int32 HeadIndex = ArmsMesh->GetRefSkeleton().FindBoneIndex(TEXT("head"));
	if (HeadIndex != INDEX_NONE)
	{
		const FVector HeadCS = FAnimationRuntime::GetComponentSpaceTransformRefPose(ArmsMesh->GetRefSkeleton(), HeadIndex).GetLocation();
		const FVector HeadInCamera = Arms->GetRelativeRotation().RotateVector(HeadCS);
		Arms->SetRelativeLocation(ArmsHeadOffset - HeadInCamera);
	}
	UE_LOG(LogTemp, Display, TEXT("AGTPlayerCharacter: arms %s, head bone %d, offset %s"), *ArmsMesh->GetName(), HeadIndex, *Arms->GetRelativeLocation().ToCompactString());
}

void AGTPlayerCharacter::LoadTools()
{
	if (Tools.Num() > 0)
	{
		bToolsFromAssets = true;
		return;
	}
	bool bAllFound = true;
	for (const UGTToolDefinition::FDefault& Row : UGTToolDefinition::DefaultTools())
	{
		UGTToolDefinition* Tool = LoadObject<UGTToolDefinition>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), *ToolAssetFolder, Row.AssetName, Row.AssetName));
		if (!Tool)
		{
			bAllFound = false;
			Tool = NewObject<UGTToolDefinition>(this, Row.AssetName);
			Tool->ApplyDefault(Row);
		}
		Tools.Add(Tool);
	}
	bToolsFromAssets = bAllFound;
	UE_LOG(LogTemp, Display, TEXT("AGTPlayerCharacter: %d tools from %s"), Tools.Num(), bAllFound ? TEXT("assets") : TEXT("runtime defaults"));
}

FVector AGTPlayerCharacter::GetPawnViewLocation() const
{
	return Camera ? Camera->GetComponentLocation() : Super::GetPawnViewLocation();
}

void AGTPlayerCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Exposure->Update(DeltaSeconds, bInCar);
	UpdateEnvironmentExposure(DeltaSeconds);
	Interaction->bSuppressed = bInCar;

	const bool bCollapsed = Exposure->IsCollapsed();
	GetCharacterMovement()->MaxWalkSpeed = bCollapsed ? WalkSpeed * CollapsedSpeedScale : (bSprintHeld ? SprintSpeed : WalkSpeed);
	GetCharacterMovement()->JumpZVelocity = bCollapsed ? 0.f : JumpVelocity;

	if (bBootOpen && (!BootCar.IsValid() || FVector::Dist(GetActorLocation(), BootCar->GetActorLocation()) > 600.f))
	{
		CloseBoot();
	}
	if (CurrentStation.IsValid() && FVector::Dist(GetActorLocation(), CurrentStation->GetActorLocation()) > 600.f)
	{
		CloseStation();
	}
	for (int32 Index = TemporaryResistances.Num() - 1; Index >= 0; --Index)
	{
		TemporaryResistances[Index].TimeLeft -= DeltaSeconds;
		if (TemporaryResistances[Index].TimeLeft <= 0.f)
		{
			TemporaryResistances.RemoveAt(Index);
		}
	}
	if (!bInCar)
	{
		UpdateCamera(DeltaSeconds);
	}
}

void AGTPlayerCharacter::UpdateEnvironmentExposure(float DeltaSeconds)
{
	EnvironmentDrainRate = 0.f;
	if (bInCar || DeltaSeconds <= 0.f)
	{
		return;
	}
	UWorld* World = GetWorld();
	const UGTWeatherSubsystem* Weather = World->GetSubsystem<UGTWeatherSubsystem>();
	CoverCheckTimer -= DeltaSeconds;
	if (CoverCheckTimer <= 0.f)
	{
		CoverCheckTimer = CoverCheckInterval;
		bUnderCover = Weather && Weather->IsUnderCover(GetActorLocation());
	}
	float Rate = 0.f;
	if (Weather)
	{
		Rate += (bUnderCover ? 0.f : Weather->GetRainIntensity()) * RainExposurePerSecond * (1.f - GetResistance(GTTags::Hazard_Weather));
		Rate += FMath::Max(0.f, -Weather->GetTemperature()) * ColdExposurePerDegree * (1.f - GetResistance(GTTags::Env_Cold));
	}
	if (const AGTRunGameState* RunState = World->GetGameState<AGTRunGameState>())
	{
		if (const UGTLegDefinition* Leg = RunState->GetLeg())
		{
			const float Progress = RunState->ProgressAt(GetActorLocation());
			Rate += Leg->SampleCondition(GTTags::Env_Cold, Progress) * EnvColdExposurePerSecond * (1.f - GetResistance(GTTags::Env_Cold));
			Rate += Leg->SampleCondition(GTTags::Env_Heat, Progress) * EnvHeatExposurePerSecond * (1.f - GetResistance(GTTags::Env_Heat));
			Rate += Leg->SampleCondition(GTTags::Env_Dust, Progress) * EnvDustExposurePerSecond * (1.f - GetResistance(GTTags::Env_Dust));
		}
	}
	EnvironmentDrainRate = Rate;
	if (Rate > 0.f)
	{
		Exposure->Drain(Rate * DeltaSeconds, GTTags::Hazard_Weather);
	}
}

void AGTPlayerCharacter::UpdateCamera(float DeltaSeconds)
{
	const float Speed2D = GetVelocity().Size2D();
	const bool bMoving = Speed2D > 20.f && GetCharacterMovement()->IsMovingOnGround();
	FVector TargetBob = FVector::ZeroVector;
	if (bHeadBobEnabled && bMoving)
	{
		const float SpeedRatio = Speed2D / FMath::Max(1.f, WalkSpeed);   // 1 walking, ~1.8 sprinting
		BobPhase = FMath::Fmod(BobPhase + DeltaSeconds * HeadBobFrequency * SpeedRatio * 2.f * PI, 2.f * PI);
		const float Amplitude = FMath::Clamp(SpeedRatio, 0.5f, 1.6f);
		TargetBob.Y = FMath::Sin(BobPhase) * HeadBobLateral * Amplitude;              // one sway per stride
		TargetBob.Z = -FMath::Abs(FMath::Sin(BobPhase)) * HeadBobVertical * Amplitude;  // one dip per footfall
	}
	else
	{
		BobPhase = 0.f;
	}
	BobOffset = FMath::VInterpTo(BobOffset, TargetBob, DeltaSeconds, bMoving ? 30.f : 8.f);
	CurrentEyeDrop = FMath::FInterpTo(CurrentEyeDrop, Exposure->IsCollapsed() ? CollapsedEyeDrop : 0.f, DeltaSeconds, 4.f);
	CameraRoot->SetRelativeLocation(FVector(0.f, 0.f, EyeHeight - CurrentEyeDrop) + BobOffset);

	const float TargetFov = BaseFov + ((bSprintFovKickEnabled && IsSprinting() && bMoving) ? SprintFovKick : 0.f);
	CurrentFov = FMath::FInterpTo(CurrentFov, TargetFov, DeltaSeconds, 6.f);
	Camera->SetFieldOfView(CurrentFov);
}

bool AGTPlayerCharacter::IsSprinting() const
{
	return bSprintHeld && !bInCar && !Exposure->IsCollapsed();
}

// ---- car -----------------------------------------------------------------------------------------

void AGTPlayerCharacter::SetInCar(bool bIn, AGTCarPawn* Car)
{
	bInCar = bIn;
	UCharacterMovementComponent* Move = GetCharacterMovement();
	if (bIn)
	{
		CloseBoot();
		CloseStation();   // no screen survives getting in
		bInventoryOpen = false;
		Interaction->SetHoldInput(false);
		Interaction->bSuppressed = true;
		Move->StopMovementImmediately();
		Move->DisableMovement();
		SetActorEnableCollision(false);
		SetActorHiddenInGame(true);
		if (Car)
		{
			AttachToActor(Car, FAttachmentTransformRules::KeepWorldTransform);
		}
	}
	else
	{
		DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
		SetActorHiddenInGame(false);
		SetActorEnableCollision(true);
		Move->SetMovementMode(MOVE_Walking);
		Interaction->bSuppressed = false;
		BobOffset = FVector::ZeroVector;
	}
}

// ---- tools ---------------------------------------------------------------------------------------

UGTToolDefinition* AGTPlayerCharacter::GetCurrentTool() const
{
	return Tools.IsValidIndex(CurrentToolIndex) ? Tools[CurrentToolIndex].Get() : nullptr;
}

bool AGTPlayerCharacter::HasToolTag(FGameplayTag Tag) const
{
	const UGTToolDefinition* Tool = GetCurrentTool();
	return Tool && !Exposure->IsCollapsed() && Tool->GrantsTag(Tag);
}

void AGTPlayerCharacter::SelectTool(int32 Index)
{
	CurrentToolIndex = FMath::Clamp(Index, -1, Tools.Num() - 1);
	UpdateToolMesh();
}

bool AGTPlayerCharacter::SelectToolByTag(FGameplayTag Tag)
{
	for (int32 Index = 0; Index < Tools.Num(); ++Index)
	{
		if (Tools[Index] && Tools[Index]->GrantsTag(Tag))
		{
			SelectTool(Index);
			return true;
		}
	}
	return false;
}

void AGTPlayerCharacter::NextTool()
{
	// Cycle hands -> tool 0 -> ... -> last -> hands.
	SelectTool(CurrentToolIndex + 1 >= Tools.Num() ? -1 : CurrentToolIndex + 1);
}

void AGTPlayerCharacter::PrevTool()
{
	SelectTool(CurrentToolIndex - 1 < -1 ? Tools.Num() - 1 : CurrentToolIndex - 1);
}

void AGTPlayerCharacter::UpdateToolMesh()
{
	const UGTToolDefinition* Tool = GetCurrentTool();
	if (!Tool)
	{
		ToolMesh->SetVisibility(false);
		return;
	}
	if (!ToolMaterial)
	{
		if (UMaterialInterface* Prop = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/GrandTour/Materials/M_GT_Prop.M_GT_Prop")))
		{
			ToolMaterial = UMaterialInstanceDynamic::Create(Prop, this);
			ToolMesh->SetMaterial(0, ToolMaterial);
		}
	}
	if (ToolMaterial)
	{
		ToolMaterial->SetVectorParameterValue(TEXT("BaseColor"), Tool->GreyboxColour);
		ToolMaterial->SetScalarParameterValue(TEXT("Roughness"), 0.6f);
	}
	ToolMesh->SetRelativeScale3D(Tool->GreyboxSize / 100.f);
	if (bHasArms && Arms->DoesSocketExist(ToolSocketName))
	{
		ToolMesh->AttachToComponent(Arms, FAttachmentTransformRules::SnapToTargetNotIncludingScale, ToolSocketName);
		ToolMesh->SetRelativeLocationAndRotation(ToolOffsetInHand, ToolRotationInHand);
	}
	else
	{
		ToolMesh->AttachToComponent(Camera, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
		ToolMesh->SetRelativeLocationAndRotation(ToolOffsetInCamera, FRotator::ZeroRotator);
	}
	ToolMesh->SetVisibility(true);
}

// ---- hook ----------------------------------------------------------------------------------------

void AGTPlayerCharacter::SetCarriedHook(AGTCarPawn* Car)
{
	HookCar = Car;
}

void AGTPlayerCharacter::DropHook()
{
	if (AGTCarPawn* Car = HookCar.Get())
	{
		if (UGTWinchComponent* Winch = Car->GetWinch())
		{
			Winch->DropHook();
		}
	}
	HookCar = nullptr;
}

// ---- boot ----------------------------------------------------------------------------------------

void AGTPlayerCharacter::OpenBoot(AGTCarPawn* Car)
{
	if (Car)
	{
		CloseStation();   // one screen at a time: scroll and T would still go to the station
	}
	BootCar = Car;
	bBootOpen = Car != nullptr;
	bInventoryOpen = bBootOpen;
	BootSelection = 0;
}

void AGTPlayerCharacter::CloseBoot()
{
	bBootOpen = false;
	BootCar = nullptr;
}

void AGTPlayerCharacter::MoveBootSelection(int32 Delta)
{
	AGTCarPawn* Car = BootCar.Get();
	const int32 Total = Inventory->Items.Num() + (Car && Car->GetBoot() ? Car->GetBoot()->Items.Num() : 0);
	if (Total <= 0)
	{
		BootSelection = 0;
		return;
	}
	BootSelection = (BootSelection + Delta + Total) % Total;
}

int32 AGTPlayerCharacter::TransferSelected()
{
	AGTCarPawn* Car = BootCar.Get();
	UGTInventoryComponent* Boot = Car ? Car->GetBoot() : nullptr;
	if (!Boot)
	{
		return 0;
	}
	const int32 Mine = Inventory->Items.Num();
	int32 Moved = 0;
	if (BootSelection < Mine)
	{
		const FGTItemStack Stack = Inventory->Items[BootSelection];
		Moved = Inventory->TransferTo(Boot, Stack.ItemId, Stack.Count);
	}
	else if (Boot->Items.IsValidIndex(BootSelection - Mine))
	{
		const FGTItemStack Stack = Boot->Items[BootSelection - Mine];
		Moved = Boot->TransferTo(Inventory, Stack.ItemId, Stack.Count);
	}
	MoveBootSelection(0);
	return Moved;
}

// ---- input ---------------------------------------------------------------------------------------

void AGTPlayerCharacter::BuildOnFootMappings(UInputMappingContext* Context, UInputAction* Move, UInputAction* LookMouse, UInputAction* LookStick,
                                             UInputAction* Sprint, UInputAction* Interact, UInputAction* ToolNext, UInputAction* ToolPrev,
                                             UInputAction* Inventory, UInputAction* DropHook, UInputAction* ToggleHeadBob, UInputAction* Transfer, UInputAction* Jump)
{
	MapKey(Context, Move, EKeys::W, EMod::SwizzleY);
	MapKey(Context, Move, EKeys::S, EMod::SwizzleYNegate);
	MapKey(Context, Move, EKeys::D);
	MapKey(Context, Move, EKeys::A, EMod::Negate);
	MapKey(Context, Move, EKeys::Gamepad_Left2D, EMod::DeadZone);
	MapKey(Context, LookMouse, EKeys::Mouse2D);
	MapKey(Context, LookStick, EKeys::Gamepad_Right2D, EMod::DeadZone);
	MapKey(Context, Sprint, EKeys::LeftShift);
	MapKey(Context, Sprint, EKeys::Gamepad_LeftThumbstick);
	MapKey(Context, Interact, EKeys::E);
	MapKey(Context, Interact, EKeys::Gamepad_FaceButton_Bottom);
	MapKey(Context, ToolNext, EKeys::MouseScrollUp);
	MapKey(Context, ToolNext, EKeys::Gamepad_DPad_Right);
	MapKey(Context, ToolPrev, EKeys::MouseScrollDown);
	MapKey(Context, ToolPrev, EKeys::Gamepad_DPad_Left);
	MapKey(Context, Inventory, EKeys::Tab);
	MapKey(Context, Inventory, EKeys::Gamepad_Special_Left);
	MapKey(Context, DropHook, EKeys::G);
	MapKey(Context, DropHook, EKeys::Gamepad_FaceButton_Left);
	MapKey(Context, ToggleHeadBob, EKeys::H);
	MapKey(Context, Transfer, EKeys::T);
	MapKey(Context, Transfer, EKeys::Gamepad_FaceButton_Top);
	if (Jump)
	{
		// Space, and B on the pad: A is interact and X drops the hook.
		MapKey(Context, Jump, EKeys::SpaceBar);
		MapKey(Context, Jump, EKeys::Gamepad_FaceButton_Right);
	}
}

void AGTPlayerCharacter::EnsureDefaultInputAssets()
{
	auto LoadAction = [](const TCHAR* Name)
	{
		return LoadObject<UInputAction>(nullptr, *FString::Printf(TEXT("/Game/GrandTour/Input/%s.%s"), Name, Name));
	};
	if (!MoveAction)          { MoveAction          = LoadAction(TEXT("IA_Move")); }
	if (!LookMouseAction)     { LookMouseAction     = LoadAction(TEXT("IA_LookMouse")); }
	if (!LookStickAction)     { LookStickAction     = LoadAction(TEXT("IA_LookStick")); }
	if (!SprintAction)        { SprintAction        = LoadAction(TEXT("IA_Sprint")); }
	if (!InteractAction)      { InteractAction      = LoadAction(TEXT("IA_Interact")); }
	if (!ToolNextAction)      { ToolNextAction      = LoadAction(TEXT("IA_ToolNext")); }
	if (!ToolPrevAction)      { ToolPrevAction      = LoadAction(TEXT("IA_ToolPrev")); }
	if (!InventoryAction)     { InventoryAction     = LoadAction(TEXT("IA_Inventory")); }
	if (!DropHookAction)      { DropHookAction      = LoadAction(TEXT("IA_DropHook")); }
	if (!ToggleHeadBobAction) { ToggleHeadBobAction = LoadAction(TEXT("IA_ToggleHeadBob")); }
	if (!TransferAction)      { TransferAction      = LoadAction(TEXT("IA_Transfer")); }
	if (!JumpAction)          { JumpAction          = LoadAction(TEXT("IA_Jump")); }
	const bool bAllActions = MoveAction && LookMouseAction && LookStickAction && SprintAction && InteractAction && ToolNextAction
		&& ToolPrevAction && InventoryAction && DropHookAction && ToggleHeadBobAction && TransferAction && JumpAction;
	if (!OnFootMappingContext && bAllActions)
	{
		OnFootMappingContext = LoadObject<UInputMappingContext>(nullptr, TEXT("/Game/GrandTour/Input/IMC_OnFoot.IMC_OnFoot"));
	}
	bInputFromAssets = OnFootMappingContext != nullptr;

	if (!MoveAction)          { MoveAction          = MakeAction(this, TEXT("IA_Move"), EInputActionValueType::Axis2D); }
	if (!LookMouseAction)     { LookMouseAction     = MakeAction(this, TEXT("IA_LookMouse"), EInputActionValueType::Axis2D); }
	if (!LookStickAction)     { LookStickAction     = MakeAction(this, TEXT("IA_LookStick"), EInputActionValueType::Axis2D); }
	if (!SprintAction)        { SprintAction        = MakeAction(this, TEXT("IA_Sprint"), EInputActionValueType::Boolean); }
	if (!InteractAction)      { InteractAction      = MakeAction(this, TEXT("IA_Interact"), EInputActionValueType::Boolean); }
	if (!ToolNextAction)      { ToolNextAction      = MakeAction(this, TEXT("IA_ToolNext"), EInputActionValueType::Boolean); }
	if (!ToolPrevAction)      { ToolPrevAction      = MakeAction(this, TEXT("IA_ToolPrev"), EInputActionValueType::Boolean); }
	if (!InventoryAction)     { InventoryAction     = MakeAction(this, TEXT("IA_Inventory"), EInputActionValueType::Boolean); }
	if (!DropHookAction)      { DropHookAction      = MakeAction(this, TEXT("IA_DropHook"), EInputActionValueType::Boolean); }
	if (!ToggleHeadBobAction) { ToggleHeadBobAction = MakeAction(this, TEXT("IA_ToggleHeadBob"), EInputActionValueType::Boolean); }
	if (!TransferAction)      { TransferAction      = MakeAction(this, TEXT("IA_Transfer"), EInputActionValueType::Boolean); }
	if (!JumpAction)          { JumpAction          = MakeAction(this, TEXT("IA_Jump"), EInputActionValueType::Boolean); }
	if (!OnFootMappingContext)
	{
		OnFootMappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_OnFootRuntime"));
		BuildOnFootMappings(OnFootMappingContext, MoveAction, LookMouseAction, LookStickAction, SprintAction, InteractAction,
			ToolNextAction, ToolPrevAction, InventoryAction, DropHookAction, ToggleHeadBobAction, TransferAction, JumpAction);
	}
	UE_LOG(LogTemp, Display, TEXT("AGTPlayerCharacter: on-foot input from %s, %d mappings"),
		bInputFromAssets ? TEXT("assets") : TEXT("runtime defaults"), OnFootMappingContext->GetMappings().Num());
}

void AGTPlayerCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	EnsureDefaultInputAssets();

	if (const APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			if (!Subsystem->HasMappingContext(OnFootMappingContext))
			{
				Subsystem->AddMappingContext(OnFootMappingContext, 0);
			}
		}
	}
	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		UE_LOG(LogTemp, Error, TEXT("AGTPlayerCharacter: input component is not an EnhancedInputComponent"));
		return;
	}
	Input->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AGTPlayerCharacter::OnMove);
	Input->BindAction(LookMouseAction, ETriggerEvent::Triggered, this, &AGTPlayerCharacter::OnLookMouse);
	Input->BindAction(LookStickAction, ETriggerEvent::Triggered, this, &AGTPlayerCharacter::OnLookStick);
	Input->BindAction(SprintAction, ETriggerEvent::Started, this, &AGTPlayerCharacter::OnSprintPressed);
	Input->BindAction(SprintAction, ETriggerEvent::Completed, this, &AGTPlayerCharacter::OnSprintReleased);
	Input->BindAction(InteractAction, ETriggerEvent::Started, this, &AGTPlayerCharacter::OnInteractPressed);
	Input->BindAction(InteractAction, ETriggerEvent::Completed, this, &AGTPlayerCharacter::OnInteractReleased);
	Input->BindAction(ToolNextAction, ETriggerEvent::Started, this, &AGTPlayerCharacter::OnToolNext);
	Input->BindAction(ToolPrevAction, ETriggerEvent::Started, this, &AGTPlayerCharacter::OnToolPrev);
	Input->BindAction(InventoryAction, ETriggerEvent::Started, this, &AGTPlayerCharacter::OnInventory);
	Input->BindAction(DropHookAction, ETriggerEvent::Started, this, &AGTPlayerCharacter::OnDropHook);
	Input->BindAction(ToggleHeadBobAction, ETriggerEvent::Started, this, &AGTPlayerCharacter::OnToggleHeadBob);
	Input->BindAction(TransferAction, ETriggerEvent::Started, this, &AGTPlayerCharacter::OnTransfer);
	Input->BindAction(JumpAction, ETriggerEvent::Started, this, &AGTPlayerCharacter::OnJumpPressed);
	Input->BindAction(JumpAction, ETriggerEvent::Completed, this, &AGTPlayerCharacter::OnJumpReleased);
}

void AGTPlayerCharacter::OnMove(const FInputActionValue& Value)
{
	if (bInCar)
	{
		return;
	}
	const FVector2D Axis = Value.Get<FVector2D>();
	AddMovementInput(GetActorForwardVector(), Axis.Y);
	AddMovementInput(GetActorRightVector(), Axis.X);
}

void AGTPlayerCharacter::OnLookMouse(const FInputActionValue& Value)
{
	const FVector2D Look = Value.Get<FVector2D>();
	AddControllerYawInput(Look.X * MouseSensitivity * LegacyLookScaleCompensation);
	AddControllerPitchInput(-Look.Y * MouseSensitivity * LegacyLookScaleCompensation * (bInvertLookY ? -1.f : 1.f));
}

void AGTPlayerCharacter::OnLookStick(const FInputActionValue& Value)
{
	const FVector2D Look = Value.Get<FVector2D>();
	const float Step = StickLookRate * GetWorld()->GetDeltaSeconds() * LegacyLookScaleCompensation;
	AddControllerYawInput(Look.X * Step);
	AddControllerPitchInput(-Look.Y * Step * (bInvertLookY ? -1.f : 1.f));
}

void AGTPlayerCharacter::OnSprintPressed(const FInputActionValue& Value)  { bSprintHeld = true; }
void AGTPlayerCharacter::OnSprintReleased(const FInputActionValue& Value) { bSprintHeld = false; }

void AGTPlayerCharacter::OnInteractPressed(const FInputActionValue& Value)
{
	// E is never captured by the boot screen: looking at the boot and pressing E closes it like any prompt.
	Interaction->SetHoldInput(true);
}

void AGTPlayerCharacter::OnTransfer(const FInputActionValue& Value)
{
	if (CurrentStation.IsValid())
	{
		ActOnStation();
	}
	else if (bBootOpen)
	{
		TransferSelected();
	}
	else if (bInventoryOpen && Inventory->Items.IsValidIndex(InventorySelection))
	{
		UseConsumable(Inventory->Items[InventorySelection].ItemId);
	}
}

void AGTPlayerCharacter::OnInteractReleased(const FInputActionValue& Value)
{
	Interaction->SetHoldInput(false);
}

void AGTPlayerCharacter::OnToolNext(const FInputActionValue& Value)
{
	if (CurrentStation.IsValid()) { MoveStationSelection(1); }
	else if (bBootOpen) { MoveBootSelection(1); }
	else if (bInventoryOpen) { InventorySelection = FMath::Clamp(InventorySelection + 1, 0, FMath::Max(0, Inventory->Items.Num() - 1)); }
	else { NextTool(); }
}

void AGTPlayerCharacter::OnToolPrev(const FInputActionValue& Value)
{
	if (CurrentStation.IsValid()) { MoveStationSelection(-1); }
	else if (bBootOpen) { MoveBootSelection(-1); }
	else if (bInventoryOpen) { InventorySelection = FMath::Clamp(InventorySelection - 1, 0, FMath::Max(0, Inventory->Items.Num() - 1)); }
	else { PrevTool(); }
}

void AGTPlayerCharacter::OnInventory(const FInputActionValue& Value)
{
	if (CurrentStation.IsValid())
	{
		CloseStation();
		return;
	}
	if (bBootOpen)
	{
		CloseBoot();
		bInventoryOpen = false;
		return;
	}
	bInventoryOpen = !bInventoryOpen;
	InventorySelection = 0;
}
// ---- stations and consumables (M4) -------------------------------------------------------------------

namespace
{
	/** The selectable row one step from Current in Delta's direction (0: Current itself, else the nearest selectable row, looking back first); stays put at either end. */
	int32 StepToSelectableRow(const TArray<FGTScreenRow>& Rows, int32 Current, int32 Delta)
	{
		if (Rows.Num() == 0)
		{
			return 0;
		}
		const int32 Start = FMath::Clamp(Current, 0, Rows.Num() - 1);
		if (Delta != 0)
		{
			const int32 Step = Delta < 0 ? -1 : 1;
			for (int32 Index = Start + Step; Rows.IsValidIndex(Index); Index += Step)
			{
				if (!Rows[Index].bHeader)
				{
					return Index;
				}
			}
		}
		if (!Rows[Start].bHeader)
		{
			return Start;
		}
		for (int32 Offset = 1; Offset < Rows.Num(); ++Offset)
		{
			if (Rows.IsValidIndex(Start - Offset) && !Rows[Start - Offset].bHeader)
			{
				return Start - Offset;
			}
			if (Rows.IsValidIndex(Start + Offset) && !Rows[Start + Offset].bHeader)
			{
				return Start + Offset;
			}
		}
		return Start;
	}
}

void AGTPlayerCharacter::OpenStation(AGTCraftingStation* Station)
{
	CloseBoot();
	bInventoryOpen = false;
	CurrentStation = Station;
	StationSelection = 0;
	bStationSelectionArmed = true;
	MoveStationSelection(0);   // land on the first selectable row
}

void AGTPlayerCharacter::CloseStation()
{
	CurrentStation = nullptr;
	StationSelection = 0;
	bStationSelectionArmed = true;
}

void AGTPlayerCharacter::MoveStationSelection(int32 Delta)
{
	if (!CurrentStation.IsValid())
	{
		return;
	}
	TArray<FGTScreenRow> Rows;
	CurrentStation->BuildRows(this, Rows);
	StationSelection = StepToSelectableRow(Rows, StationSelection, Delta);
	if (Delta != 0)
	{
		bStationSelectionArmed = true;
	}
}

bool AGTPlayerCharacter::ActOnStation()
{
	if (!CurrentStation.IsValid())
	{
		return false;
	}
	TArray<FGTScreenRow> Rows;
	CurrentStation->BuildRows(this, Rows);
	if (!bStationSelectionArmed || !Rows.IsValidIndex(StationSelection))
	{
		return false;
	}
	const FGTScreenRow Acted = Rows[StationSelection];
	const bool bDone = CurrentStation->ActOnRow(this, StationSelection);
	// The rows can change under the cursor (a stack sold out, a new sell row above it): stay on the row acted on,
	// not its index. When that row is gone, land nearby but let the next T wait for a scroll.
	Rows.Reset();
	CurrentStation->BuildRows(this, Rows);
	int32 Same = INDEX_NONE;
	for (int32 Index = 0; Index < Rows.Num(); ++Index)
	{
		const FGTScreenRow& Row = Rows[Index];
		if (!Row.bHeader && Row.Action == Acted.Action && Row.Tag == Acted.Tag && (Acted.Tag.IsValid() || Row.Payload == Acted.Payload))
		{
			Same = Index;
			break;
		}
	}
	if (Same != INDEX_NONE)
	{
		StationSelection = Same;
	}
	else
	{
		StationSelection = StepToSelectableRow(Rows, StationSelection, 0);
		bStationSelectionArmed = false;
	}
	return bDone;
}

bool AGTPlayerCharacter::UseConsumable(FName ItemId)
{
	const UGTItemRegistry* Registry = UGTItemRegistry::Get(this);
	const UGTConsumableDefinition* Use = Registry ? Registry->FindConsumable(ItemId) : nullptr;
	if (!Use || !Inventory->Has(ItemId, 1))
	{
		return false;
	}
	const AGTPlayerController* PC = Cast<AGTPlayerController>(GetController());
	AGTCarPawn* Car = PC ? PC->GetCar() : nullptr;
	// Used up only when it changes something now: a flush on a cool engine or a can on a full tank stays in the bag.
	bool bDidSomething = false;
	if (Use->ResistanceTag.IsValid() && Use->ResistanceStrength > 0.f)
	{
		AddTemporaryResistance(Use->ResistanceTag, Use->ResistanceStrength, Use->DurationSeconds);
		if (Car && Car->GetParts())
		{
			Car->GetParts()->AddTemporaryResistance(Use->ResistanceTag, Use->ResistanceStrength, Use->DurationSeconds);
		}
		bDidSomething = true;
	}
	if (Car && Car->GetEnvironment())
	{
		if (Use->bResetHeat && Car->GetEnvironment()->Heat > 0.f)
		{
			Car->GetEnvironment()->Heat = 0.f;
			bDidSomething = true;
		}
		if (Use->bResetClog && Car->GetEnvironment()->Clog > 0.f)
		{
			Car->GetEnvironment()->Clog = 0.f;
			bDidSomething = true;
		}
	}
	if (Car && Car->GetCondition() && Car->GetParts() && Use->FuelLitres > 0.f && !Car->GetParts()->GetInstalled(GTTags::Slot_FuelTank).IsNone())
	{
		UGTConditionComponent* CarCondition = Car->GetCondition();
		const float FuelBefore = CarCondition->FuelLitres;
		CarCondition->FuelLitres = FMath::Min(CarCondition->TankCapacityLitres, CarCondition->FuelLitres + Use->FuelLitres);
		bDidSomething |= CarCondition->FuelLitres > FuelBefore + KINDA_SMALL_NUMBER;
	}
	if (Use->ExposureRestore > 0.f && Exposure->Exposure < Exposure->MaxExposure)
	{
		Exposure->Exposure = FMath::Min(Exposure->MaxExposure, Exposure->Exposure + Use->ExposureRestore);
		bDidSomething = true;
	}
	if (!bDidSomething)
	{
		LastUseMessage = FString::Printf(TEXT("%s would do nothing right now"), *Use->DisplayName.ToString());
		return false;
	}
	Inventory->Remove(ItemId, 1);
	InventorySelection = FMath::Clamp(InventorySelection, 0, FMath::Max(0, Inventory->Items.Num() - 1));
	++ConsumablesUsed;
	LastUseMessage = FString::Printf(TEXT("used %s"), *Use->DisplayName.ToString());
	UE_LOG(LogTemp, Display, TEXT("AGTPlayerCharacter: used %s"), *Use->Describe());
	return true;
}

TArray<FGTTimedResistance> AGTPlayerCharacter::GetTemporaryResistances() const
{
	TArray<FGTTimedResistance> Result;
	for (const FTemporaryResistance& T : TemporaryResistances)
	{
		FGTTimedResistance R;
		R.Tag = T.Tag;
		R.Strength = T.Strength;
		R.SecondsLeft = T.TimeLeft;
		Result.Add(R);
	}
	return Result;
}

float AGTPlayerCharacter::GetResistance(FGameplayTag Tag) const
{
	float Total = 0.f;
	for (const FTemporaryResistance& R : TemporaryResistances)
	{
		if (R.Tag == Tag)
		{
			Total += R.Strength;
		}
	}
	return FMath::Clamp(Total, 0.f, 1.f);
}

void AGTPlayerCharacter::AddTemporaryResistance(FGameplayTag Tag, float Strength, float Seconds)
{
	if (!Tag.IsValid() || Strength <= 0.f || Seconds <= 0.f)
	{
		return;
	}
	FTemporaryResistance R;
	R.Tag = Tag;
	R.Strength = Strength;
	R.TimeLeft = Seconds;
	TemporaryResistances.Add(R);
}


void AGTPlayerCharacter::OnDropHook(const FInputActionValue& Value)
{
	DropHook();
}

void AGTPlayerCharacter::OnToggleHeadBob(const FInputActionValue& Value)
{
	bHeadBobEnabled = !bHeadBobEnabled;
	UE_LOG(LogTemp, Display, TEXT("AGTPlayerCharacter: head bob %s"), bHeadBobEnabled ? TEXT("on") : TEXT("off"));
}

FString AGTPlayerCharacter::Describe() const
{
	const UGTToolDefinition* Tool = GetCurrentTool();
	return FString::Printf(TEXT("pos=%s speed=%.0f tool=%s bob=(%.2f, %.2f) fov=%.1f inCar=%d hook=%d arms=%d %s | %s"),
		*GetActorLocation().ToCompactString(), GetVelocity().Size2D(), Tool ? *Tool->ToolId.ToString() : TEXT("hands"),
		BobOffset.Y, BobOffset.Z, CurrentFov, bInCar ? 1 : 0, IsCarryingHook() ? 1 : 0, bHasArms ? 1 : 0,
		*Exposure->Describe(), *Inventory->Describe());
}

void AGTPlayerCharacter::OnJumpPressed(const FInputActionValue& Value)
{
	if (!bInCar && !Exposure->IsCollapsed())
	{
		Jump();
	}
}

void AGTPlayerCharacter::OnJumpReleased(const FInputActionValue& Value)
{
	StopJumping();
}
