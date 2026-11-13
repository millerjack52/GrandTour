#include "Core/GTMudLab.h"
#include "Character/GTPlayerCharacter.h"
#include "Interaction/GTInteractionComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTVehicleTuningComponent.h"
#include "Vehicle/GTVehicleAudioComponent.h"
#include "Vehicle/GTRangeRoverAudioComponent.h"
#include "Vehicle/GTRangeRoverDrivetrain.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/InputComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerInput.h"
#include "Kismet/GameplayStatics.h"

namespace
{
void ApplyRouteDrivetrain(UWorld* World, AGTCarPawn* Car)
{
    bool Low=true, Locked=true;
    for (TActorIterator<AGTMudRoute> It(World); It; ++It)
    {
        Low=It->bStartLowRange;
        Locked=It->bStartDiffLocked;
        break;
    }
    Car->GetDrivetrain()->SetLowRange(Low);
    Car->GetDrivetrain()->SetDiffLock(Locked);
}
}

AGTMudLabGameMode::AGTMudLabGameMode()
{
    DefaultPawnClass=AGTCarPawn::StaticClass();
    if(FParse::Param(FCommandLine::Get(),TEXT("GTFerrariTest")))
        if(auto* FerrariClass=LoadClass<AGTCarPawn>(nullptr,TEXT("/Game/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288.BP_Ferrari288_C"))) DefaultPawnClass=FerrariClass;
    PlayerControllerClass=AGTMudLabController::StaticClass();
    HUDClass=AGTMudLabHUD::StaticClass();
}

void AGTMudLabController::OnPossess(APawn* InPawn)
{
    Super::OnPossess(InPawn);
    if (auto* LabCar=Cast<AGTCarPawn>(InPawn))
    {
        LabCar->SetChaseCamera(true);
        // The approved Range Rover H2 is the only audible vehicle in the rally/lab fleet.
        LabCar->GetAudio()->SetMuted(!GEngine || !GEngine->UseSound() || !UGTRangeRoverAudioComponent::IsRangeRover(LabCar));
        ApplyRouteDrivetrain(GetWorld(),LabCar);
    }
}

void AGTMudLabController::SetupInputComponent()
{
    Super::SetupInputComponent();
    // BaseInput.ini reserves F1 for wireframe in Development builds. Remove
    // only this player's conflicting debug key; F1 belongs to the driving HUD.
    if (PlayerInput)
    {
        const int32 Removed=PlayerInput->DebugExecBindings.RemoveAll([](const FKeyBind& Binding){return Binding.Key==EKeys::F1;});
        UE_LOG(LogTemp,Display,TEXT("Mud driving HUD: F1 reserved, removed %d debug binding(s)"),Removed);
    }
    InputComponent->BindKey(EKeys::One,IE_Pressed,this,&AGTMudLabController::FirmLane);
    InputComponent->BindKey(EKeys::Two,IE_Pressed,this,&AGTMudLabController::SoftLane);
    InputComponent->BindKey(EKeys::Three,IE_Pressed,this,&AGTMudLabController::WaterLane);
    InputComponent->BindKey(EKeys::Four,IE_Pressed,this,&AGTMudLabController::SandLane);
    InputComponent->BindKey(EKeys::Five,IE_Pressed,this,&AGTMudLabController::GrassLane);
    InputComponent->BindKey(EKeys::Six,IE_Pressed,this,&AGTMudLabController::RiverLane);
    InputComponent->BindKey(EKeys::Seven,IE_Pressed,this,&AGTMudLabController::RecoverySeven);
    InputComponent->BindKey(EKeys::Eight,IE_Pressed,this,&AGTMudLabController::RecoveryEight);
    InputComponent->BindKey(EKeys::Nine,IE_Pressed,this,&AGTMudLabController::RecoveryNine);
    InputComponent->BindKey(EKeys::BackSpace,IE_Pressed,this,&AGTMudLabController::ResetLab);
    InputComponent->BindKey(EKeys::F1,IE_Pressed,this,&AGTMudLabController::ToggleDriveInfo);
}

void AGTMudLabController::SelectLane(int32 Lane)
{
    auto* LabCar=GetCar();
    if (!LabCar) return;
    int32 LaneCount=3;
    for(TActorIterator<AGTMudRoute> It(GetWorld());It;++It){LaneCount=FMath::Max(3,It->RecoveryPoints.Num());break;}
    SelectedLane=FMath::Clamp(Lane,1,LaneCount);
    LabCar->ResetDrivingInputs();
    LabCar->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
    LabCar->GetMesh()->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
    if (GetPawn()!=LabCar) EnterVehicle(LabCar);
    LabCar->GetChaosMovement()->ResetVehicle();
    FTransform Recovery(FRotator::ZeroRotator,FVector(-1200,(SelectedLane-2)*850,100));
    for (TActorIterator<AGTMudRoute> It(GetWorld());It;++It)
    {
        if (It->RecoveryPoints.IsValidIndex(SelectedLane-1)) Recovery=It->RecoveryPoints[SelectedLane-1];
        break;
    }
    LabCar->SetActorLocationAndRotation(Recovery.GetLocation(),Recovery.Rotator(),false,nullptr,ETeleportType::TeleportPhysics);
    LabCar->GetMesh()->WakeAllRigidBodies();
    LabCar->GetCondition()->RepairAll();
    ApplyRouteDrivetrain(GetWorld(),LabCar);
    LabCar->SetChaseCamera(true);
    SetControlRotation(Recovery.Rotator());
}

void AGTMudLabController::ResetLab()
{
    // Reloading creates fresh terrain/water state and a fresh vehicle, including damage.
    UGameplayStatics::OpenLevel(this,FName(*UGameplayStatics::GetCurrentLevelName(this,true)));
}

void AGTMudLabHUD::DrawHUD()
{
    AHUD::DrawHUD();
    const auto* PC=Cast<AGTMudLabController>(PlayerOwner);
    const auto* LabCar=PC ? PC->GetCar() : nullptr;
    if (Canvas && PC && bShowHUD && !PC->IsDriving())
    {
        if (const auto* Character=PC->GetPlayerCharacter())
        {
            if (Character->IsStationOpen()) DrawStation(Character,Canvas->ClipX,Canvas->ClipY);
            DrawRect(FLinearColor::White,Canvas->ClipX*.5f-2,Canvas->ClipY*.5f-2,4,4);
            const auto* Interaction=Character->GetInteraction();
            if (Interaction && !Interaction->GetPrompt().IsEmpty())
                DrawText(TEXT("E  ")+Interaction->GetPrompt(),FLinearColor::White,Canvas->ClipX*.5f-160,Canvas->ClipY-100,GEngine->GetMediumFont());
        }
        return;
    }
    if (Canvas && LabCar && bShowHUD && PC->IsDriving() && LabCar->GetVelocity().Size()<30.f && UGTRangeRoverAudioComponent::IsRangeRover(LabCar))
    {
        DrawRect(FLinearColor(.015f,.015f,.015f,.82f),22,Canvas->ClipY-55,225,32);
        DrawRect(FLinearColor(.9f,.3f,.05f),22,Canvas->ClipY-55,4,32);
        DrawText(TEXT("U   Open workshop"),FLinearColor::White,36,Canvas->ClipY-49,GEngine->GetMediumFont(),.85f);
    }
    if (!Canvas || !LabCar || !bShowHUD || !PC->bShowDriveInfo) return;
    const float Scale=FMath::Clamp(Canvas->SizeX/1440.f,.7f,1.25f);
    auto Label=[&](const FString& Text,float Y,FLinearColor Colour=FLinearColor::White)
    { DrawText(Text,Colour,22*Scale,Y*Scale,GEngine->GetMediumFont(),.85f*Scale); };
    const bool RangeRover=UGTRangeRoverAudioComponent::IsRangeRover(LabCar);
    const bool Ferrari=LabCar->GetDrivetrain()->IsFerrari();
    DrawRect(FLinearColor(.025f,.035f,.04f,.68f),12*Scale,12*Scale,338*Scale,((RangeRover || Ferrari) ? 94 : 72)*Scale);
    float Sink=0,Water=0;
    if (const auto* Tuning=LabCar->FindComponentByClass<UGTVehicleTuningComponent>())
        for (const auto& Wheel:Tuning->GetCurrent().Wheels) Sink=FMath::Max(Sink,Wheel.SinkageCm);
    for (const auto& Wheel:LabCar->GetTraction()->Wheels) Water=FMath::Max(Water,Wheel.WaterDepthM*100.f);
    const auto* Drive=LabCar->GetDrivetrain();
    Label(FString::Printf(TEXT("%.0f km/h   |   %s range   |   Diffs %s"),LabCar->GetVelocity().Size()*.036f,Drive->IsLowRange()?TEXT("LOW"):TEXT("HIGH"),Drive->IsDiffLocked()?TEXT("LOCKED"):(Ferrari || Drive->GetRangeRoverSetup()==1) ? TEXT("LSD") : TEXT("OPEN")),20);
    Label(FString::Printf(TEXT("Sink %.1f cm   |   Water %.1f cm"),Sink,Water),41);
    Label(TEXT("F1 hide info   |   1-9 checkpoints   |   C camera"),62,FLinearColor(.7f,.77f,.8f));
    if(RangeRover) Label(FString::Printf(TEXT("%s   |   Gear %d   |   %.0f rpm"),GTRangeRoverDrivetrain::Setup(Drive->GetRangeRoverSetup()).Name,Drive->GetGear(),Drive->GetEngineRpm()),83,FLinearColor(.95f,.55f,.22f));
    else if(Ferrari) Label(FString::Printf(TEXT("Ferrari   |   Gear %d   |   %.0f rpm"),Drive->GetGear(),Drive->GetEngineRpm()),83,FLinearColor(.95f,.55f,.22f));
}
