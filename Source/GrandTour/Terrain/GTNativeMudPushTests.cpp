#include "Terrain/GTLandscapeSurfaceField.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTNativeMudPushTest,"GrandTour.MudRunner.LivePush",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTNativeMudPushTest::RunTest(const FString& Parameters)
{
    auto Paint=[](FVector2D P){return FLinearColor(P.Y>95 ? 0.f:45.f,-5,0,.95f);};
    FGTLandscapeSurfaceField F;
    F.AuthoredHeightAt=[](FVector2D,float){return 0.f;};
    F.NativeBaseAlpha=[](FVector2D){return 1.f;};
    F.NativeUpdateAt=[](FVector2D P){return P.Y<=95;};
    F.bNativeShaderUpdates=true;F.Focus(FVector2D::ZeroVector,Paint);
    // Use the shipping native branch, with overlapping contacts in one batch.
    for(int32 I=0;I<65;++I)
    {
        for(int32 Duplicate=0;Duplicate<2;++Duplicate)
            F.StampWorked(FVector2D(-60,0),FVector2D(60,0),FVector2D(1,0),35,22,Paint,-22,.8,{true,.7,1});
        F.StepNative();
    }
    float Raised=0,Slide=0;double Net=0;
    for(const auto& T:F.Tiles)for(const auto& C:T.Value.Cells)
    {
        Raised=FMath::Max(Raised,C.DeltaCm);Slide=FMath::Max(Slide,C.SlideCm.Size());Net+=C.DeltaCm;
        if(!FMath::IsFinite(C.DeltaCm)||C.DeltaCm< -45.001f||C.DeltaCm>15.001f)
        {AddError(TEXT("Non-finite or unbounded live soil"));return false;}
    }
    TestTrue(TEXT("Native contact sinks into its bed"),F.Sample(FVector2D::ZeroVector).DeltaCm< -18);
    TestTrue(TEXT("Displaced soil actually rises above the original ground"),Raised>3);
    TestTrue(TEXT("Separate lateral displacement is active"),Slide>.3);
    TestTrue(TEXT("Push pass ran on the live branch"),F.NativePushCells>0);
    TestTrue(TEXT("Overlap cannot mint soil"),F.DepositedCm3<=F.ExcavatedCm3+2 && Net*F.CellCm*F.CellCm<=2);
    TestEqual(TEXT("Unpainted ground remains rigid"),F.Sample(FVector2D(0,130)).DeltaCm,0.f);
    const float LoadedBank=F.Sample(FVector2D(0,38)).DeltaCm;
    for(int32 I=0;I<8;++I)
    {
        // This contact has no cut request; it must still prevent incoming deposits.
        F.StampWorked(FVector2D(-60,38),FVector2D(60,38),FVector2D(1,0),35,1,Paint,20,.8f,{});
        F.StampWorked(FVector2D(-60,0),FVector2D(60,0),FVector2D(1,0),35,30,Paint,-30,.8f,{true,.7f,1});
        F.StepNative();
    }
    TestTrue(TEXT("A settled neighbouring tyre cannot be refilled"),F.Sample(FVector2D(0,38)).DeltaCm<=LoadedBank+.02f);
    const float OldRut=F.Sample(FVector2D::ZeroVector).DeltaCm;
    const uint64 Before=F.GeometryRevision;
    // A crossing tyre must cut through an existing bank and retain the old rut.
    for(int32 I=0;I<30;++I)
    {
        F.StampWorked(FVector2D(0,-60),FVector2D(0,60),FVector2D(0,1),35,22,Paint,-22,.8,{true,0,1});F.StepNative();
    }
    TestTrue(TEXT("Crossing tyre remoulds the bank"),F.Sample(FVector2D(0,38)).DeltaCm< -8);
    // Native Update deliberately transports material into lower neighbours.
    // Crossing a deeper old rut can partially refill it; it must remain a rut,
    // rather than being reset to the untouched surface or the new stamp's rest.
    const float CrossedRut=F.Sample(FVector2D::ZeroVector).DeltaCm;
    TestTrue(TEXT("Crossing preserves the deep rut while allowing native backfill"),CrossedRut< -18.f && CrossedRut<OldRut+10.f);
    TArray<FBox2D> Changes;F.BedChangesSince(Before,Changes);
    TestTrue(TEXT("Raised and cut soil notify water/geometry consumers"),Changes.Num()>0 && F.GeometryRevision>Before);
    const uint64 Settled=F.GeometryRevision;const double Deposited=F.DepositedCm3;
    for(int32 I=0;I<120;++I)F.StepNative();
    TestTrue(TEXT("No contact means no accumulating mound or bed churn"),F.GeometryRevision==Settled && F.DepositedCm3==Deposited);
    TestTrue(TEXT("Transient contacts are drained"),F.NativePushContacts.IsEmpty() && F.NativeContactCells.IsEmpty());
    AddInfo(FString::Printf(TEXT("Live mud: raised %.2f cm, lateral %.2f cm; crossed rut %.2f -> %.2f cm; cut %.1f, deposited %.1f cm3"),Raised,Slide,OldRut,CrossedRut,F.ExcavatedCm3,F.DepositedCm3));
    return true;
}
#endif
