#include "UI/GTWorkshopComponent.h"
#include "UI/SGTWorkshop.h"
#include "Core/GTPlayerController.h"
#include "Core/GTMudLab.h"
#include "Character/GTPlayerCharacter.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTBodyComponent.h"
#include "Vehicle/GTRangeRoverAudioComponent.h"
#include "Vehicle/GTRangeRoverSuspension.h"
#include "Vehicle/GTRangeRoverDrivetrain.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTDriveLayout.h"
#include "Parts/GTPartSlotsComponent.h"
#include "Parts/GTItemRegistry.h"
#include "Parts/GTItemDefinition.h"
#include "Inventory/GTInventoryComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "Kismet/GameplayStatics.h"
#include "Framework/Application/SlateApplication.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace
{
    const FName TyreIds[] = { TEXT("Part.Tyre"), TEXT("Part.TyreAllTerrain"), TEXT("Part.TyreKnobbly") };
    FGameplayTag TyreSlot() { return FGameplayTag::RequestGameplayTag(TEXT("Slot.Tyres")); }
    FGameplayTag SuspensionSlot() { return FGameplayTag::RequestGameplayTag(TEXT("Slot.Suspension")); }
    FName MechanicalId(int32 Part,int32 Option) { return Part==6 ? FName(GTDriveLayout::Id(Option)) : Part==5 ? FName(GTRangeRoverDrivetrain::Setup(Option).Id) : Part==3 ? FName(GTRangeRoverSuspension::Kit(Option).Id) : TyreIds[Option]; }
    FGameplayTag MechanicalSlot(int32 Part) { return Part==6 ? FGameplayTag::RequestGameplayTag(TEXT("Slot.DriveLayout")) : Part==5 ? FGameplayTag::RequestGameplayTag(TEXT("Slot.Engine")) : Part==3 ? SuspensionSlot() : TyreSlot(); }
}

UGTWorkshopComponent::UGTWorkshopComponent() { PrimaryComponentTick.bCanEverTick = false; }
AGTPlayerController* UGTWorkshopComponent::Controller() const { return Cast<AGTPlayerController>(GetOwner()); }
FString UGTWorkshopComponent::SaveSlot()
{
    return FParse::Param(FCommandLine::Get(), TEXT("GTWorkshopQA")) ? TEXT("GT_Workshop_RangeRover_QA") : TEXT("GT_Workshop_RangeRover");
}
FLinearColor UGTWorkshopComponent::PaintColour(int32 Choice)
{
    static const FColor Colours[] = { FColor(183,113,52), FColor(94,105,72), FColor(201,183,145), FColor(119,42,35), FColor(48,58,62), FColor(213,211,193) };
    return FLinearColor(Colours[FMath::Clamp(Choice,0,5)]);
}
FLinearColor UGTWorkshopComponent::RimColour(int32 Choice)
{
    static const FLinearColor Colours[] = { FLinearColor(.40f,.38f,.30f), FLinearColor(.42f,.45f,.47f), FLinearColor(.055f,.062f,.066f) };
    return Colours[FMath::Clamp(Choice,0,2)];
}

bool UGTWorkshopComponent::Open()
{
    if (bOpen) return true;
    auto* PC = Controller();
    auto* Target = PC ? PC->GetCar() : nullptr;
    auto Reject = [&](const TCHAR* Why) { Message=Why; if(PC) PC->ClientMessage(Message); return false; };
    if (!PC || !PC->IsLocalController() || !PC->GetLocalPlayer() || !PC->GetLocalPlayer()->ViewportClient || !Target)
        return Reject(TEXT("Workshop needs a local vehicle."));
    const bool FullWorkshop=UGTRangeRoverAudioComponent::IsRangeRover(Target);
    if (Target->GetVelocity().Size() > 30.f) return Reject(TEXT("Stop the car before opening the workshop."));
    if (FullWorkshop && !Target->GetBody()->WorkshopReady()) return Reject(TEXT("Workshop materials are missing. Run Art/workshop.ps1 -Mode Setup."));
    if (FullWorkshop && !Target->GetBody()->WorkshopWheelsReady()) return Reject(TEXT("Workshop wheel models are missing. Run Art/workshop.ps1 -Mode WheelSetup."));
    Camera = GetWorld()->SpawnActor<ACameraActor>();
    if (!Camera) return false;
    Car=Target;
    FittedPaint=Target->GetBody()->WorkshopPaint;
    FittedRims=Target->GetBody()->WorkshopRims;
    FittedEquipment=Target->GetBody()->WorkshopEquipment;
    FittedTyres=Target->GetParts()->GetInstalled(TyreSlot());
    FittedSuspension=Target->GetParts()->GetInstalled(SuspensionSlot());
    FittedDrivetrain=Target->GetParts()->GetInstalled(MechanicalSlot(5));
    FittedDriveLayout=Target->GetParts()->GetInstalled(MechanicalSlot(6));
    FittedFrontPercent=FMath::RoundToInt(Target->GetDrivetrain()->GetAWDFrontShare()*100.f);
    SelectedFrontPercent=FittedFrontPercent;
    bTestFitting=GetWorld()->GetAuthGameMode<AGTMudLabGameMode>() != nullptr;
    bWasPaused=UGameplayStatics::IsGamePaused(this);
    bWasCursor=PC->bShowMouseCursor;
    bWasFullTick=PC->ShouldPerformFullTickWhenPaused();
    PreviousView=PC->GetViewTarget();
    if(auto* HUD=PC->GetHUD()) { bWasHUD=HUD->bShowHUD; HUD->bShowHUD=false; }
    if(auto* Character=PC->GetPlayerCharacter()) { Character->CloseStation(); Character->CloseBoot(); }
    Target->ResetDrivingInputs();
    PC->FlushPressedKeys();
    SelectedPart=INDEX_NONE; SelectedOption=0; bComparing=false; Message.Empty();
    Yaw=CameraYaw=-42.f; Pitch=CameraPitch=15.f; Distance=CameraDistance=780.f;
    CameraFraming=0.f;
    // Prefer a clear three-quarter view when the car is parked beside the service awning or trees.
    const FVector Centre=Target->GetActorTransform().TransformPosition(FVector(10,0,80));
    FCollisionQueryParams ViewQuery(SCENE_QUERY_STAT(WorkshopOpeningView),true,Target);
    if(PC->GetPlayerCharacter()) ViewQuery.AddIgnoredActor(PC->GetPlayerCharacter());
    int32 BestOcclusion=MAX_int32;
    for(float Candidate : {-42.f,42.f,138.f,-138.f})
    {
        const FVector Eye=Centre+FRotator(Pitch,Candidate+Target->GetActorRotation().Yaw,0).Vector()*Distance;
        int32 Occluded=0;
        for(const FVector& Local : {FVector(0,0,80),FVector(150,0,80),FVector(-150,0,80),FVector(0,0,155)})
        {
            FHitResult Hit;
            if(GetWorld()->LineTraceSingleByChannel(Hit,Eye,Target->GetActorTransform().TransformPosition(Local),ECC_Visibility,ViewQuery)) ++Occluded;
        }
        if(Occluded<BestOcclusion) { BestOcclusion=Occluded; Yaw=CameraYaw=Candidate; }
        if(Occluded==0) break;
    }
    Camera->GetCameraComponent()->SetFieldOfView(45.f);
    Camera->GetCameraComponent()->bConstrainAspectRatio=false;
    // Paused-world temporal velocity otherwise smears the inspection orbit indefinitely.
    Camera->GetCameraComponent()->PostProcessSettings.bOverride_MotionBlurAmount=true;
    Camera->GetCameraComponent()->PostProcessSettings.MotionBlurAmount=0.f;
    PC->SetWorkshopFullTick(true);
    bOpen=true;
    UpdateCamera(1.f);
    PC->SetViewTarget(Camera);
    PC->SetIgnoreMoveInput(true); PC->SetIgnoreLookInput(true);
    if(!bWasPaused && !PC->SetPause(true)) { Close(); return Reject(TEXT("Workshop requires a paused local game.")); }
    PC->bShowMouseCursor=true;
    SAssignNew(Widget, SGTWorkshop, this);
    PC->GetLocalPlayer()->ViewportClient->AddViewportWidgetContent(Widget.ToSharedRef(), 100);
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(Widget);
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    PC->SetInputMode(Mode);
    FSlateApplication::Get().SetKeyboardFocus(Widget, EFocusCause::SetDirectly);
    UE_LOG(LogTemp, Display, TEXT("Workshop opened: %s"), *Describe());
    return true;
}

void UGTWorkshopComponent::Close()
{
    if(!bOpen) return;
    ApplyPreview(true);
    bOpen=false; bComparing=false; SelectedPart=INDEX_NONE;
    auto* PC=Controller();
    if(PC)
    {
        if(Widget.IsValid() && PC->GetLocalPlayer() && PC->GetLocalPlayer()->ViewportClient)
            PC->GetLocalPlayer()->ViewportClient->RemoveViewportWidgetContent(Widget.ToSharedRef());
        PC->SetViewTarget(PreviousView.IsValid() ? PreviousView.Get() : PC->GetPawn());
        PC->bShowMouseCursor=bWasCursor;
        PC->SetWorkshopFullTick(bWasFullTick);
        PC->SetIgnoreMoveInput(false); PC->SetIgnoreLookInput(false);
        PC->FlushPressedKeys();
        PC->SetInputMode(FInputModeGameOnly());
        if(auto* HUD=PC->GetHUD()) HUD->bShowHUD=bWasHUD;
        if(!bWasPaused) PC->SetPause(false);
    }
    Widget.Reset();
    if(Camera) Camera->Destroy();
    Camera=nullptr; Car.Reset(); PreviousView.Reset();
}
void UGTWorkshopComponent::EndPlay(const EEndPlayReason::Type Reason) { Close(); Super::EndPlay(Reason); }

int32 UGTWorkshopComponent::FittedOption(int32 Part) const
{
    if(Part==6) return GTDriveLayout::Index(FittedDriveLayout);
    if(Part==5)
    {
        for(int32 I=0;I<3;++I) if(FittedDrivetrain==FName(GTRangeRoverDrivetrain::Setup(I).Id)) return I;
        return INDEX_NONE; // a removed engine or legacy Engine L is not the Standard replacement
    }
    if(Part==3) return GTRangeRoverSuspension::Index(FittedSuspension);
    return Part==0 ? FittedPaint : Part==1 ? FittedRims : FittedTyres==TyreIds[2] ? 2 : FittedTyres==TyreIds[1] ? 1 : 0;
}
bool UGTWorkshopComponent::PartAvailable(int32 Part) const
{
    return Part>=0 && Part<=6 && Car.IsValid() && (Part==6 || UGTRangeRoverAudioComponent::IsRangeRover(Car.Get()));
}
int32 UGTWorkshopComponent::NextPart() const
{
    for(int32 Step=1;Step<=7;++Step) { const int32 P=(SelectedPart+Step)%7; if(PartAvailable(P)) return P; }
    return INDEX_NONE;
}
FString UGTWorkshopComponent::VehicleName() const
{
    return Car.IsValid() && UGTRangeRoverAudioComponent::IsRangeRover(Car.Get()) ? TEXT("RANGE ROVER") : Car.IsValid() && Car->GetDrivetrain()->IsFerrari() ? TEXT("FERRARI 288 GTO") : TEXT("DRIVE CONVERSION");
}
int32 UGTWorkshopComponent::OptionCount() const { return SelectedPart==6 ? 4 : SelectedPart==0 ? 6 : SelectedPart>=1 && SelectedPart<=5 ? 3 : 0; }
FString UGTWorkshopComponent::OptionName(int32 Choice) const
{
    if(Choice<0 || Choice>=OptionCount()) return FString();
    static const TCHAR* Paints[]={TEXT("Original paint"),TEXT("Highland green"),TEXT("Sandstone"),TEXT("Oxblood"),TEXT("Charcoal"),TEXT("Limestone")};
    static const TCHAR* Rims[]={TEXT("Pressed steel"),TEXT("Classic alloy"),TEXT("Heavy-duty steel")};
    if(SelectedPart==6) return GTDriveLayout::Name(Choice);
    if(SelectedPart==0) return Paints[Choice];
    if(SelectedPart==1) return Rims[Choice];
    if(SelectedPart==3) return GTRangeRoverSuspension::Kit(Choice).Name;
    if(SelectedPart==5) return GTRangeRoverDrivetrain::Setup(Choice).Name;
    if(SelectedPart==4)
    {
        static const TCHAR* Names[]={TEXT("Roof rack"),TEXT("Bull bar"),TEXT("Snorkel")};
        return FString(Names[Choice])+((FittedEquipment&(1<<Choice)) ? TEXT(" / remove") : TEXT(" / add"));
    }
    static const TCHAR* Tyres[]={TEXT("Road"),TEXT("All-terrain"),TEXT("Mud")};
    return Tyres[Choice];
}
void UGTWorkshopComponent::SelectPart(int32 Part)
{
    if(!bOpen || !PartAvailable(Part)) return;
    ApplyPreview(true); bComparing=false; SelectedPart=Part; SelectedOption=FMath::Max(0,FittedOption(Part)); Message.Empty();
    bEquipmentPreview=false;
    SelectedFrontPercent=FittedFrontPercent;
    if(Part==4)SelectedOption=0;
    // Retain the user's orbit. A modest dolly brings the selected part closer without hiding the car.
    Distance=Part==0 ? 780.f : Part==4 ? 850.f : 720.f;
}
void UGTWorkshopComponent::Preview(int32 Option)
{
    if(!bOpen || Option<0 || Option>=OptionCount()) return;
    SelectedOption=Option; bComparing=false; Message.Empty(); bEquipmentPreview=SelectedPart==4; ApplyPreview(false);
}
void UGTWorkshopComponent::ApplyPreview(bool bFitted)
{
    auto* Body=Car.IsValid() ? Car->GetBody() : nullptr;
    if(!Body || !UGTRangeRoverAudioComponent::IsRangeRover(Car.Get())) return;
    const int32 Paint=!bFitted && SelectedPart==0 ? SelectedOption : FittedPaint;
    const int32 Rims=!bFitted && SelectedPart==1 ? SelectedOption : FittedRims;
    const int32 Tyres=!bFitted && SelectedPart==2 ? SelectedOption : FittedOption(2);
    Body->SetWorkshopAppearance(Paint,Rims,Tyres);
    Body->SetWorkshopEquipment(!bFitted && SelectedPart==4 && bEquipmentPreview ? FittedEquipment^(1<<SelectedOption) : FittedEquipment);
}
void UGTWorkshopComponent::AdjustAWDSplit(int32 Steps)
{
    if(!bOpen || !ShowAWDSplit()) return;
    SelectedFrontPercent=FMath::Clamp(SelectedFrontPercent+FMath::Clamp(Steps,-16,16)*5,10,90);
    bComparing=false; Message.Empty();
}
void UGTWorkshopComponent::Compare(bool bFitted)
{
    if(!bOpen || SelectedPart==INDEX_NONE) return;
    bComparing=bFitted; ApplyPreview(bFitted);
}
void UGTWorkshopComponent::Cancel()
{
    if(!bOpen) return;
    ApplyPreview(true); bComparing=false; SelectedPart=INDEX_NONE; Message.Empty(); Distance=780.f;
}
FString UGTWorkshopComponent::FitReason() const
{
    if(!bOpen || !Car.IsValid() || SelectedPart==INDEX_NONE) return TEXT("Select a part");
    if(SelectedPart==4)
    {
        if(!Car->GetBody()->WorkshopEquipmentReady())return TEXT("Run equipment setup to load the models");
        return bEquipmentPreview ? FString() : TEXT("Choose an accessory to add or remove");
    }
    if(!HasPendingChange()) return TEXT("Already fitted");
    if(SelectedPart<2) return FString();
    if(SelectedPart==6 && Car->GetVelocity().Size()>30.f) return TEXT("Stop the car before swapping drive layout");
    // Tuning an installed AWD kit consumes no new kit and cannot repair the car.
    if(ShowAWDSplit() && FittedOption(6)==3) return FString();
    const FName NewId=MechanicalId(SelectedPart,SelectedOption);
    const FName OldId=SelectedPart==6 ? FittedDriveLayout : SelectedPart==5 ? FittedDrivetrain : SelectedPart==3 ? FittedSuspension : FittedTyres;
    const auto Fit=Car->GetParts()->CanInstall(NewId);
    if(!Fit.bFits) return Fit.Hint;
    if(bTestFitting) return FString();
    const auto* Boot=Car->GetBoot();
    if(!Boot->Has(NewId,1)) return TEXT("Put the replacement kit in the boot");
    if(Boot->GetFreeWeightKg()+GTItems::WeightKg(NewId) < GTItems::WeightKg(OldId)) return TEXT("Make room in the boot for the old kit");
    return FString();
}
bool UGTWorkshopComponent::CanFit() const { return FitReason().IsEmpty(); }
bool UGTWorkshopComponent::Fit()
{
    if(!CanFit()) { Message=FitReason(); return false; }
    const bool bSplitOnly=ShowAWDSplit() && FittedOption(6)==3;
    if(bSplitOnly)
    {
        if(!Car->GetDrivetrain()->SetAWDFrontShare(SelectedFrontPercent*.01f)) return false;
        FittedFrontPercent=SelectedFrontPercent;
    }
    else if(SelectedPart==2 || SelectedPart==3 || SelectedPart==5 || SelectedPart==6)
    {
        const FName NewTyres=MechanicalId(SelectedPart,SelectedOption);
        const FGameplayTag Slot=MechanicalSlot(SelectedPart);
        if(bTestFitting)
        {
            // A lab comparison must not repair the car or grant inventory.
            auto Loadout=Car->GetParts()->GetLoadout();
            bool bFound=false;
            for(auto& Entry:Loadout) if(Entry.Slot==Slot) { Entry.PartId=NewTyres; bFound=true; }
            if(!bFound) { FGTSlotEntry Entry; Entry.Slot=Slot; Entry.PartId=NewTyres; Loadout.Add(Entry); }
            Car->GetParts()->ApplyLoadout(Loadout,false);
        }
        else
        {
            auto* Boot=Car->GetBoot();
            if(Boot->Remove(NewTyres,1)!=1) return false;
            FName Replaced;
            if(!Car->GetParts()->Install(NewTyres,Replaced)) { Boot->Add(NewTyres,1); return false; }
            if(!Replaced.IsNone()) Boot->Add(Replaced,1); // capacity checked before mutation
        }
        if(SelectedPart==6) FittedDriveLayout=NewTyres;
        else if(SelectedPart==5) FittedDrivetrain=NewTyres;
        else if(SelectedPart==3) FittedSuspension=NewTyres; else FittedTyres=NewTyres;
        if(ShowAWDSplit())
        {
            Car->GetDrivetrain()->SetAWDFrontShare(SelectedFrontPercent*.01f);
            FittedFrontPercent=SelectedFrontPercent;
        }
    }
    else
    {
        auto* Save=Cast<UGTWorkshopSave>(UGameplayStatics::CreateSaveGameObject(UGTWorkshopSave::StaticClass()));
        Save->Paint=SelectedPart==0 ? SelectedOption : FittedPaint;
        Save->Rims=SelectedPart==1 ? SelectedOption : FittedRims;
        Save->RimModel=Save->Rims;
        Save->Equipment=SelectedPart==4 ? FittedEquipment^(1<<SelectedOption) : FittedEquipment;
        if(!UGameplayStatics::SaveGameToSlot(Save,SaveSlot(),0)) { Message=TEXT("Could not save. Preview is still open."); return false; }
        FittedPaint=Save->Paint; FittedRims=Save->Rims;
        FittedEquipment=Save->Equipment;
    }
    Message=SelectedPart==4 ? TEXT("Equipment updated") : OptionName(SelectedOption)+TEXT(" fitted");
    if(ShowAWDSplit()) Message=FString::Printf(TEXT("AWD fitted / %d%% front, %d%% rear"),FittedFrontPercent,100-FittedFrontPercent);
    ApplyPreview(true); bComparing=false; SelectedPart=INDEX_NONE; Distance=780.f;
    UE_LOG(LogTemp, Display, TEXT("Workshop fitted: %s"), *Describe());
    return true;
}
FString UGTWorkshopComponent::Detail() const
{
    if(SelectedPart==6)
    {
        const int32 Choice=bComparing ? FittedOption(6) : SelectedOption;
        if(Choice==3) return FString::Printf(TEXT("%d%% front / %d%% rear nominal torque\nDiff locks can redistribute torque\n%s"),DisplayFrontPercent(),100-DisplayFrontPercent(),FittedOption(6)==3 ? TEXT("Adjusting the split needs no new kit") : bTestFitting ? TEXT("Test fit / applies when driving resumes") : TEXT("AWD conversion kit must be in the boot"));
        static const TCHAR* Details[]={TEXT("Restore this car's original driven wheels"),TEXT("Front wheels pull / rear wheels coast"),TEXT("Rear wheels push / front wheels steer")};
        return FString(Details[Choice])+TEXT("\nKeeps engine, gearing and suspension\n")+(bTestFitting ? TEXT("Test fit / applies when driving resumes") : TEXT("Conversion kit must be in the boot"));
    }
    if(SelectedPart==0) return TEXT("Body and roof colour / original trim");
    if(SelectedPart==1) return TEXT("Rim design / complete set of four");
    if(SelectedPart==4) return TEXT("Visual accessories / combine freely\nNo cargo, protection or wading bonus");
    if(SelectedPart==5)
    {
        const int32 Choice=bComparing ? FittedOption(5) : SelectedOption;
        if(Choice<0) return TEXT("Existing engine / authored gearing");
        static const TCHAR* Descriptions[]={
            TEXT("Original V8 / 4-speed automatic\nOpen diffs / 2.50:1 low range"),
            TEXT("High-rev pull / close-ratio gears\nLimited-slip diffs / faster shifts"),
            TEXT("Low-speed torque / gentle throttle\n3.30:1 low range / earlier shifts")};
        return FString(Descriptions[Choice])+TEXT("\nV  High / low (stop first)   X  Diff locks\n")+
            (bTestFitting ? TEXT("Test fit / applies when driving resumes") : TEXT("Replacement drivetrain must be in boot"));
    }
    if(SelectedPart==3)
    {
        const int32 Choice=bComparing ? FittedOption(3) : SelectedOption;
        static const TCHAR* Descriptions[]={TEXT("Original ride / revised bump stops"),TEXT("Modest lift / firmer damping"),TEXT("Raised stance / longer droop")};
        return FString(Descriptions[Choice])+TEXT("\nRide height settles after fitting");
    }
    if(SelectedPart!=2) return FString();
    const auto* Registry=UGTItemRegistry::Get(this);
    const auto* Part=Registry ? Registry->FindPart(TyreIds[SelectedOption]) : nullptr;
    return Part ? FString::Printf(TEXT("Grip %.2fx / rolling resistance %.2fx\n%s"),Part->GripScale,Part->RollingResistanceScale,
        bTestFitting ? TEXT("Test fitting / no inventory cost") : TEXT("Replacement set must be in the boot")) : TEXT("Part unavailable");
}
void UGTWorkshopComponent::Orbit(float X, float Y) { if(bOpen) { Yaw+=X*.32f; Pitch=FMath::Clamp(Pitch+Y*.22f,4.f,48.f); } }
void UGTWorkshopComponent::Zoom(float Amount) { if(bOpen) Distance=FMath::Clamp(Distance-Amount*55.f,510.f,1150.f); }
void UGTWorkshopComponent::UpdateCamera(float Delta)
{
    if(!bOpen) return;
    if(!Car.IsValid()) { Close(); return; }
    if(!Camera) return;
    const float Alpha=1.f-FMath::Exp(-12.f*FMath::Clamp(Delta,0.f,.1f));
    CameraYaw=FMath::Lerp(CameraYaw,Yaw,Alpha); CameraPitch=FMath::Lerp(CameraPitch,Pitch,Alpha); CameraDistance=FMath::Lerp(CameraDistance,Distance,Alpha);
    const FVector Centre=Car->GetActorTransform().TransformPosition(FVector(10,0,80));
    const FRotator OrbitRotation(CameraPitch,CameraYaw+Car->GetActorRotation().Yaw,0);
    const FVector Desired=Centre+OrbitRotation.Vector()*CameraDistance;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WorkshopCamera),false,Car.Get());
    Query.AddIgnoredActor(Camera);
    if(Controller() && Controller()->GetPlayerCharacter()) Query.AddIgnoredActor(Controller()->GetPlayerCharacter());
    FHitResult Hit;
    const bool bBlocked=GetWorld()->SweepSingleByChannel(Hit,Centre,Desired,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(12.f),Query);
    const FVector Location=bBlocked ? Hit.Location : Desired;
    CameraFraming=FMath::Lerp(CameraFraming,SelectedPart>=0 ? 55.f : 0.f,Alpha);
    const FVector Right=FRotationMatrix((Centre-Location).Rotation()).GetUnitAxis(EAxis::Y);
    Camera->SetActorLocationAndRotation(Location,(Centre+Right*CameraFraming-Location).Rotation());
}
FVector UGTWorkshopComponent::Hotspot(int32 Part) const
{
    if(!Car.IsValid()) return FVector::ZeroVector;
    const FVector4 Wheels=Car->GetBody()->GetWheelGeom();
    // Choose the side facing the orbit camera; a wheel marker never points through the far side.
    const float Side=FMath::Sin(FMath::DegreesToRadians(CameraYaw))<0.f ? -1.f : 1.f;
    const FVector Local=Part==6 ? FVector(-65,Side*60,65) : Part==0 ? FVector(75,Side*68,118) : Part==1 ? FVector(Wheels.X,Side*95,Wheels.Z) : Part==2 ? FVector(Wheels.Y,Side*95,Wheels.Z+Wheels.W*.7f) : Part==3 ? FVector(0,Side*88,48) : Part==5 ? FVector(150,Side*35,105) : FVector(-45,Side*45,195);
    return Car->GetActorTransform().TransformPosition(Local);
}
FString UGTWorkshopComponent::Describe() const
{
    return FString::Printf(TEXT("open=%d selected=%d option=%d comparing=%d paint=%d rims=%d tyres=%s test=%d"), bOpen,SelectedPart,SelectedOption,bComparing,FittedPaint,FittedRims,*FittedTyres.ToString(),bTestFitting);
}
