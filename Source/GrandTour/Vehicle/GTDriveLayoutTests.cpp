#include "Vehicle/GTDriveLayout.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Core/GTSaveGame.h"
#include "Core/GTGameplayTags.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTDriveLayoutTest,"GrandTour.Vehicle.DriveLayout",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTDriveLayoutTest::RunTest(const FString&)
{
    TestEqual(TEXT("old loadouts use Factory"),GTDriveLayout::Index(NAME_None),0);
    TestEqual(TEXT("old snapshots default to balanced AWD"),FGTCarrySnapshot().AWDFrontShare,.5f);
    auto* Drivetrain=NewObject<UGTDrivetrainComponent>();
    for(float Share : {.1f,.3f,.5f,.7f,.9f}) for(float Torque : {-1200.f,0.f,1200.f})
    {
        float Front=0,Rear=0;
        Drivetrain->Split(Torque,40,60,10,10,0,Front,Rear,true,Share);
        TestTrue(TEXT("nominal centre split reaches front axle"),FMath::IsNearlyEqual(Front,Torque*Share,.001f));
        TestTrue(TEXT("nominal centre split reaches rear axle"),FMath::IsNearlyEqual(Rear,Torque*(1-Share),.001f));
        Drivetrain->Split(Torque,40,60,30,10,1,Front,Rear,true,Share);
        TestTrue(TEXT("locked biased centre conserves shaft torque"),FMath::IsNearlyEqual(Front+Rear,Torque,.001f));
        TestTrue(TEXT("lock transfers torque away from faster front axle"),Front<Torque*Share);
    }
    Drivetrain->SetAWDFrontShare(-1); TestEqual(TEXT("AWD retains at least ten percent front drive"),Drivetrain->GetAWDFrontShare(),.1f);
    Drivetrain->SetAWDFrontShare(2); TestEqual(TEXT("AWD retains at least ten percent rear drive"),Drivetrain->GetAWDFrontShare(),.9f);
    for(int32 Layout=0;Layout<4;++Layout)
    {
        const FString Slot=TEXT("GT_Layout_NativeQA_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
        auto* Save=Cast<UGTSaveGame>(UGameplayStatics::CreateSaveGameObject(UGTSaveGame::StaticClass()));
        Save->Snapshot.bValid=true;
        Save->Snapshot.AWDFrontShare=.3f;
        FGTSlotEntry Engine; Engine.Slot=GTTags::Slot_Engine; Engine.PartId=TEXT("Part.RREngineRally");
        FGTSlotEntry Drive; Drive.Slot=GTTags::Slot_DriveLayout; Drive.PartId=GTDriveLayout::Id(Layout);
        Save->Snapshot.Loadout={Engine,Drive};
        Save->Snapshot.PartHealth.Add(EGTCarPart::Engine,.63f);
        TestTrue(TEXT("save conversion using production serializer"),UGameplayStatics::SaveGameToSlot(Save,Slot,0));
        const auto* Loaded=Cast<UGTSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot,0));
        if(TestNotNull(TEXT("load conversion from disk"),Loaded))
        {
            TestEqual(TEXT("both mechanical slots retained"),Loaded->Snapshot.Loadout.Num(),2);
            if(Loaded->Snapshot.Loadout.Num()==2)
            {
                TestEqual(TEXT("engine package coexists with conversion"),Loaded->Snapshot.Loadout[0].PartId,Engine.PartId);
                TestEqual(TEXT("layout slot retained"),Loaded->Snapshot.Loadout[1].Slot.GetTagName(),GTTags::Slot_DriveLayout.GetTag().GetTagName());
                TestEqual(TEXT("layout choice survives disk roundtrip"),GTDriveLayout::Index(Loaded->Snapshot.Loadout[1].PartId),Layout);
            }
            TestEqual(TEXT("conversion save preserves damage"),Loaded->Snapshot.PartHealth.FindRef(EGTCarPart::Engine),.63f);
            TestEqual(TEXT("rear bias survives disk roundtrip"),Loaded->Snapshot.AWDFrontShare,.3f);
        }
        UGameplayStatics::DeleteGameInSlot(Slot,0);
    }
    // Exercise the production capture/apply path independently of the player's run subsystem or save.
    UWorld* World=nullptr;
    for(const auto& Context:GEngine->GetWorldContexts()) if(Context.WorldType==EWorldType::Editor) { World=Context.World(); break; }
    if(TestNotNull(TEXT("editor test world available"),World))
    {
        FActorSpawnParameters Params; Params.ObjectFlags=RF_Transient;
        auto* Source=World->SpawnActor<AGTCarPawn>(Params);
        auto* Restored=World->SpawnActor<AGTCarPawn>(Params);
        if(TestNotNull(TEXT("source car for snapshot"),Source) && TestNotNull(TEXT("restored car for snapshot"),Restored))
        {
            FGTSlotEntry Entry;Entry.Slot=GTTags::Slot_DriveLayout;Entry.PartId=GTDriveLayout::Id(3);
            Source->GetParts()->ApplyLoadout({Entry},false);
            Source->GetDrivetrain()->SetAWDFrontShare(.3f);
            auto* Instance=NewObject<UGameInstance>();
            auto* Run=NewObject<UGTRunSubsystem>(Instance);
            Run->CaptureFromPawns(Source,nullptr);
            TestEqual(TEXT("production carry captures AWD bias"),Run->GetSnapshot().AWDFrontShare,.3f);
            Run->ApplyToPawns(Restored,nullptr);
            TestEqual(TEXT("production carry restores effective split"),Restored->GetDrivetrain()->GetEffectiveFrontShare(),.3f);
        }
        if(Source) Source->Destroy();
        if(Restored) Restored->Destroy();
    }
    return true;
}
#endif
