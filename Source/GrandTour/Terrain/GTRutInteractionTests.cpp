#include "Terrain/GTLandscapeSurfaceField.h"
#include "Terrain/GTMudContactModel.h"
#include "Vehicle/GTSoilVehicleMovement.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "HAL/PlatformTime.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTRutWallTest,"GrandTour.LandscapeMud.RutWallWork",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTRutWallTest::RunTest(const FString& Parameters)
{
    FGTSoilContact C;C.bActive=true;
    for(int32 Y=0;Y<C.Side;++Y) for(int32 X=0;X<C.Side;++X)
        C.Height[Y*C.Side+X]=FMath::Clamp(float(FMath::Abs(Y-4)*12.5-10),0.f,20.f)-20.f;
    const FVector2D Centre(0,0);
    const float Along=C.EntryRise(Centre,FVector2D(1,0),28);
    const float Across=C.EntryRise(Centre,FVector2D(0,1),28);
    const float Reverse=C.EntryRise(Centre,FVector2D(0,-1),28);
    const float Diagonal=C.EntryRise(Centre,FVector2D(1,1).GetSafeNormal(),28);
    TestTrue(TEXT("Along a rut costs less than climbing its bank"),Along<.01f && Across>12.f);
    TestTrue(TEXT("Mirrored rut walls respond equally"),FMath::Abs(Across-Reverse)<.001f);
    TestTrue(TEXT("Diagonal crossing has intermediate resistance"),Diagonal>Along && Diagonal<Across);
    const GTMudContact::FState Firm={true,.1f,.8f,0,10},Wet={true,.95f,.8f,1,10};
    TestTrue(TEXT("Wet remoulded bank yields more easily"),GTMudContact::BankResistance(Across,28,.9f,Wet)<GTMudContact::BankResistance(Across,28,.4f,Firm));
    TestEqual(TEXT("Small surface noise does not become a wall"),GTMudContact::BankResistance(1.5f,28,.8f,Wet),0.f);
    TestEqual(TEXT("Invalid negative resistance cannot propel the car"),GTMudContact::BankForce(400000,-1,100,.02f),0.f);
    for(float Speed : {-1200.f,-40.f,0.f,40.f,1200.f}) for(float Dt : {1.f/120,1.f/60,1.f/20})
    {
        const float Load=400000.f;
        const float Force=GTMudContact::BankForce(Load,GTMudContact::BankResistance(Across,28,.8f,Wet),Speed,Dt);
        const float After=Speed-FMath::Sign(Speed)*Force/(Load/980.f)*Dt;
        TestTrue(TEXT("Wall work cannot add kinetic energy or reverse velocity"),FMath::Abs(After)<=FMath::Abs(Speed)+.001f && After*Speed>=0);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTWorkedSoilTest,"GrandTour.LandscapeMud.DirectionalSoilFlow",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTWorkedSoilTest::RunTest(const FString& Parameters)
{
    auto Paint=[](FVector2D P) { return FLinearColor(P.Y>100 ? 0.f : 35.f,-4,0,.9f); };
    auto Make=[&](FGTLandscapeSurfaceField& F) {
        F.AuthoredHeightAt=[](FVector2D,float){return 0.f;};
        F.ShapeAt=[](FVector2D){return FLinearColor(.9f,.7f,1,1);};
        F.Focus(FVector2D::ZeroVector,Paint);
    };
    FGTLandscapeSurfaceField Roll,Spin;Make(Roll);Make(Spin);
    const double Start=FPlatformTime::Seconds();
    for(int32 I=0;I<90;++I)
    {
        Roll.StampWorked(FVector2D::ZeroVector,FVector2D::ZeroVector,FVector2D(1,0),28,14,Paint,-10,.6f,{true,0,1});
        Spin.StampWorked(FVector2D::ZeroVector,FVector2D::ZeroVector,FVector2D(1,0),28,14,Paint,-12,.6f,{true,1,0});
    }
    const double MeanMs=(FPlatformTime::Seconds()-Start)*1000/180;
    auto Centroid=[](const FGTLandscapeSurfaceField& F) {
        double Mass=0,Moment=0;
        for(const auto& T:F.Tiles) for(int32 I=0;I<T.Value.Cells.Num();++I)
        {
            const float H=T.Value.Cells[I].DeltaCm;
            if(H<=0) continue;
            const auto P=F.Centre(T.Key*F.TileCells+FIntPoint(I%F.TileCells,I/F.TileCells));
            Mass+=H;Moment+=H*P.X;
        }
        return Mass ? Moment/Mass : 0.;
    };
    TestTrue(TEXT("Rolling bow lies ahead of wheelspin deposits"),Centroid(Roll)>Centroid(Spin)+2);
    TestTrue(TEXT("Driven tread shears deposits toward the heel"),Centroid(Spin)<0);
    for(auto* F : {&Roll,&Spin})
    {
        double Net=0;
        for(const auto& T:F->Tiles) for(const auto& Cell:T.Value.Cells)
        {
            Net+=Cell.DeltaCm;
            if(!FMath::IsFinite(Cell.DeltaCm) || Cell.DeltaCm< -35.001f || Cell.DeltaCm>15.001f) {AddError(TEXT("Invalid soil height"));return false;}
        }
        TestTrue(TEXT("Actual cell-volume balance, including bank relaxation"),FMath::Abs(Net*F->CellCm*F->CellCm)<.5);
        TestTrue(TEXT("Bookkeeping conserves moved soil"),FMath::Abs(F->ExcavatedCm3-F->DepositedCm3)<.001);
        TestTrue(TEXT("Tyre still sinks to its loaded plane"),F->Sample(FVector2D::ZeroVector).DeltaCm< -8.f);
        TestEqual(TEXT("No deposits on adjacent firm ground"),F->Sample(FVector2D(0,130)).DeltaCm,0.f);
    }
    // Reverse travel must move the bow with the car; it cannot retain a forward-only toe.
    FGTLandscapeSurfaceField Back;Make(Back);
    for(int32 I=0;I<90;++I) Back.StampWorked(FVector2D::ZeroVector,FVector2D::ZeroVector,FVector2D(-1,0),28,14,Paint,-10,.6f,{true,0,1});
    TestTrue(TEXT("Reverse bow follows reverse travel"),Centroid(Back)<0 && Centroid(Roll)>0);
    AddInfo(FString::Printf(TEXT("Directional flow mean %.3f ms/stamp; rolling centroid %.2f cm, spin %.2f cm, reverse %.2f cm"),MeanMs,Centroid(Roll),Centroid(Spin),Centroid(Back)));
    return true;
}
#endif
