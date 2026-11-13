#include "Terrain/GTLandscapeSurfaceField.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTMudContactModel.h"
#include "Terrain/GTMudRestMap.h"
#include "Terrain/GTWaterField.h"
#include "Vehicle/GTSoilVehicleMovement.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "HAL/PlatformTime.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudWaterBedTest,"GrandTour.LandscapeMud.MovingWaterBed",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTMudWaterBedTest::RunTest(const FString& Parameters)
{
    FGTWaterField Water;Water.bClosedBasin=true;Water.NominalFlowMps=0;Water.HeadDropCm=0;
    Water.WindScale=0;Water.RainIntensity=0;Water.SpongeTauS=0;Water.SpongeFluxDamp=0;
    Water.Init(FVector2D::ZeroVector,FVector2D(1,0),600,600,12.5f,0,
        [](FVector2D P){return FMath::Abs(P.X)<30 ? 20.f : -15.f;});
    const double Initial=Water.VolumeM3();
    TestTrue(TEXT("Dry bank height cannot tilt the sampled water surface"),FMath::Abs(Water.SurfaceCmAt(FVector2D(-27,0)))<.001f);
    float Peak=0;
    for(int32 I=0;I<180;++I)
    {
        if(I<45) Water.StampLid(FVector2D(-250,0),FVector2D(1,0),32,15,-6,FVector2D::ZeroVector,6,.7f);
        Water.Step(1.f/60.f,0,0);
        Peak=FMath::Max(Peak,FMath::Abs(Water.SurfaceCmAt(FVector2D(-180,0))));
    }
    TestTrue(TEXT("Shared wheel occupancy produces propagating waves"),Peak>.05f);
    TestTrue(TEXT("Dry bank blocks the disturbance"),FMath::Abs(Water.SurfaceCmAt(FVector2D(180,0)))<.01f);
    TestTrue(TEXT("Closed pond preserves volume during vehicle displacement"),FMath::Abs(Water.VolumeM3()-Initial)<.0001);
    TArray<float> Bed=Water.BedCm;
    for(int32 I=0;I<Water.NumCells();++I)
    {
        const auto P=Water.CellCentreCm(I);
        if(FMath::Abs(P.X)<40 && FMath::Abs(P.Y)<25) Bed[I]=-12;
    }
    TestTrue(TEXT("Accept a cut through the bank"),Water.UpdateClosedBed(Bed));
    TestTrue(TEXT("Excavation does not create water"),FMath::Abs(Water.VolumeM3()-Initial)<.0001);
    TestTrue(TEXT("Newly excavated dry rut is initially dry"),Water.DepthMAt(FVector2D::ZeroVector)<.001f);
    const double Start=FPlatformTime::Seconds();
    for(int32 I=0;I<300;++I) Water.Step(1.f/60.f,0,0);
    TestTrue(TEXT("Connected water flows into the opened rut"),Water.DepthMAt(FVector2D::ZeroVector)>.03f);
    TestTrue(TEXT("Bed movement and wetting conserve pond water"),FMath::Abs(Water.VolumeM3()-Initial)<.0001);
    TestEqual(TEXT("No depth safety clamp"),Water.DepthClamps,0);
    TestTrue(TEXT("Finite nonnegative depth"),!Water.DepthM.ContainsByPredicate([](float H){return !FMath::IsFinite(H)||H<0;}));
    AddInfo(FString::Printf(TEXT("Closed mud water: cells=%d peak_wave_cm=%.4f volume_error_m3=%.8f mean_step_wall_ms=%.3f"),
        Water.NumCells(),Peak,Water.VolumeM3()-Initial,(FPlatformTime::Seconds()-Start)*1000./300));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudPropertiesTest,"GrandTour.LandscapeMud.SoilProperties",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTMudPropertiesTest::RunTest(const FString& Parameters)
{
    FGTLandscapeSurfaceSample S;
    S.bSoilShearResponse=true;S.Softness=.9f;S.SinkageCapCm=36.f;S.RestWheelSupportCm=-5.f;
    const float Baseline=S.LoadedSettlementCm(1.f);
    S.BearingStrength=.6f;S.SinkageCapCm=48.f;
    const float Deep=S.LoadedSettlementCm(1.f);
    TestTrue(TEXT("Deep weak soil has meaningfully greater equilibrium settlement"),Deep>Baseline+10.f);
    TestTrue(TEXT("Additional load sinks farther"),S.LoadedSettlementCm(.5f)<Deep);
    S.SinkageCapCm=12.f;
    TestEqual(TEXT("Even weak soil stops at the finite base beneath the existing hollow"),S.LoadedSettlementCm(1.f),7.f);
    S.RestWheelSupportCm=-20.f;
    TestEqual(TEXT("No yielding below the mineral base"),S.LoadedSettlementCm(1.f),0.f);
    S.RestWheelSupportCm=-5.f;S.SinkageCapCm=48.f;S.BearingStrength=1.6f;
    TestTrue(TEXT("Greater bearing strength reduces settlement independently of layer thickness"),S.LoadedSettlementCm(1.f)<Baseline);
    S.BearingStrength=.6f;S.GrassCover=1.f;
    TestTrue(TEXT("Intact sod holds the load above otherwise identical weak mud"),S.LoadedSettlementCm(1.f)<Deep*.5f);
    S.GrassCover=0.f;S.bSoilShearResponse=false;
    TestTrue(TEXT("Legacy response ignores the new bearing strength control"),FMath::IsNearlyEqual(S.LoadedSettlementCm(1.f),20.25f));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudWorldMapTest,"GrandTour.LandscapeMud.WorldRestMap",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTMudWorldMapTest::RunTest(const FString& Parameters)
{
    // An asymmetric map makes wrapping, transposition and half-texel shifts observable.
    TArray<float> Data={-9.f,3.f,7.f,11.f};
    const FVector2D Origin(-100,-200);
    auto Read=[&](FVector2D P) { return GTMudRestMap::Sample(Data,2,Origin,200,P); };
    TestEqual(TEXT("Northwest texel centre"),Read(FVector2D(-50,-150)),-9.f);
    TestEqual(TEXT("Opposite texel centre"),Read(FVector2D(50,-50)),11.f);
    TestEqual(TEXT("Bilinear centre matches shader"),Read(FVector2D(0,-100)),3.f);
    TestEqual(TEXT("Outside the map is not tiled"),Read(FVector2D(250,-50)),0.f);
    TestEqual(TEXT("Edge clamps to edge texels"),Read(Origin),-9.f);
    TestEqual(TEXT("Malformed map rejected"),GTMudRestMap::Sample(Data,3,Origin,200,Origin),0.f);
    FGTLandscapeSurfaceField Field;
    auto Paint=[](FVector2D) { return FLinearColor(35,-4,0,.9f); };
    Field.AuthoredHeightAt=[&](FVector2D P,float) { return Read(P); };
    Field.Focus(FVector2D::ZeroVector,Paint);
    const FVector2D Point(-50,-150);
    const float Before=Field.Sample(Point).DeltaCm;
    Field.Stamp(Point,Point,FVector2D(1,0),28,4,Paint);
    TestTrue(TEXT("Imported ground yields beneath the tyre"),Field.Sample(Point).DeltaCm<Before);
    const float After=Field.Sample(Point).DeltaCm;
    Field.Focus(FVector2D(4800,0),Paint);Field.Focus(FVector2D::ZeroVector,Paint);
    TestEqual(TEXT("Unique map deformation survives window movement"),Field.Sample(Point).DeltaCm,After);
    TestTrue(TEXT("Water fills depressions below its plane"),FGTLandscapeSurfaceField::WaterDepth(Before,Paint(Point))>0);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudShearStateTest,"GrandTour.LandscapeMud.SoilShearState",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTMudShearStateTest::RunTest(const FString& Parameters)
{
    auto Response=[](float Wet,float Worked,float Compression,float Speed,float Tread) {
        return GTMudContact::Evaluate(.85f,0,15,32,Speed,Tread,{true,Wet,.8f,Worked,Compression});
    };
    const auto Fresh=Response(.95f,0,0,100,120),Churned=Response(.95f,1,10,100,120);
    const auto Dry=Response(.1f,0,0,100,120),Packed=Response(.1f,1,10,100,120);
    TestTrue(TEXT("Churned saturated soil loses shear strength"),Churned.Grip<Fresh.Grip);
    TestTrue(TEXT("Dry soil gains support through compaction"),Packed.Grip>Dry.Grip);
    TestTrue(TEXT("Wet clay lateral response differs from forward grip"),Fresh.LateralGrip<Fresh.Grip*.8f);
    TestTrue(TEXT("Excessive spin goes beyond peak traction"),Response(.95f,0,0,100,900).Grip<Fresh.Grip);
    TestTrue(TEXT("Fast entry increases displacement resistance"),Response(.95f,0,0,800,850).Resistance>Fresh.Resistance);
    TestEqual(TEXT("Standing soil applies no artificial drag impulse"),Response(.95f,1,10,0,0).Resistance,0.f);
    for(float Speed : {-1500.f,-100.f,0.f,100.f,1500.f})
        for(float Tread : {-2500.f,0.f,2500.f})
        {
            const auto R=Response(.95f,1,10,Speed,Tread);
            TestTrue(TEXT("Forward/reverse/spin response remains finite and dissipative"),FMath::IsFinite(R.Resistance) && R.Resistance>=0 && R.Grip>=.12f && R.Grip<=1);
        }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTLandscapeMudCompressionTest,"GrandTour.LandscapeMud.LocalCompression",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTLandscapeMudCompressionTest::RunTest(const FString& Parameters)
{
    FGTLandscapeSurfaceField Field;
    Field.AuthoredHeightAt=[](FVector2D P,float) { return float(4.*FMath::Sin(P.X/65.)); };
    auto Paint=[](FVector2D) { return FLinearColor(12,-5,0,.7f); };
    Field.Focus(FVector2D::ZeroVector,Paint);
    auto Pass=[&](float Depth,bool Cross=false) {
        for (int32 X=-250;X<250;X+=8)
            Field.Stamp(Cross?FVector2D(0,X):FVector2D(X,0),Cross?FVector2D(0,X+8):FVector2D(X+8,0),
                Cross?FVector2D(0,1):FVector2D(1,0),28,Depth,Paint);
    };
    Pass(3);
    float Lowest=100,Highest=-100;
    for (int32 X=-200;X<200;X+=10)
    {
        const FVector2D P(X,0);const float H=Field.Sample(P).DeltaCm;
        const float Rest=Field.RestHeight(P,12);
        TestTrue(TEXT("Rolling cuts at most its local 3 cm target"),Rest-H<=3.1f);
        Lowest=FMath::Min(Lowest,H);Highest=FMath::Max(Highest,H);
    }
    TestTrue(TEXT("Bog relief survives the tyre pass"),Highest-Lowest>6.f);
    for (int32 Repeat=0;Repeat<12;++Repeat) Pass(3);
    const float Before=Field.Sample(FVector2D(0,0)).DeltaCm;
    for (int32 Repeat=0;Repeat<120;++Repeat) Field.Stamp(FVector2D(0,0),FVector2D(0,0),FVector2D(1,0),28,3,Paint);
    TestTrue(TEXT("Stationary equilibrium does not keep excavating"),FMath::Abs(Before-Field.Sample(FVector2D(0,0)).DeltaCm)<.05f);
    Pass(7,true);
    TestTrue(TEXT("Crossing and spin preserve cut/deposit volume"),FMath::Abs(Field.ExcavatedCm3-Field.DepositedCm3)<.001);
    for (const auto& Tile : Field.Tiles)
        for (const auto& Cell : Tile.Value.Cells)
            if (!FMath::IsFinite(Cell.DeltaCm) || Cell.DeltaCm < -12.001f || Cell.DeltaCm>15.001f)
                { AddError(TEXT("Crossing cuts exceeded the finite ground bounds"));return false; }
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTLandscapeMudSparseTest,"GrandTour.LandscapeMud.SparseUpdates",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTLandscapeMudSparseTest::RunTest(const FString& Parameters)
{
    FGTLandscapeSurfaceField Field;
    Field.AuthoredHeightAt=[](FVector2D P,float) { return float(4.*FMath::Sin(P.X/65.)); };
    auto Paint=[](FVector2D) { return FLinearColor(12,-5,0,.7f); };
    auto Appearance=[](FVector2D) { return FVector2f(.8f,0); };
    Field.Focus(FVector2D::ZeroVector,Paint);
    for (auto& T:Field.Tiles) T.Value.DirtyBlocks=0;
    Field.Step(1.f);
    TestEqual(TEXT("Untouched soil has no decay scan"),Field.LastDecayCells,0);
    Field.Stamp(FVector2D(-20,-5),FVector2D(20,5),FVector2D(1,0),28,3,Paint);
    TArray<FBox2D> BedRegions;Field.BedChangesSince(0,BedRegions);
    TestTrue(TEXT("Water sees a bounded set of changed bed blocks"),BedRegions.Num()>0 && BedRegions.Num()<=4);
    // Upload consumers may clear their bits; a later water consumer still sees the cut.
    for(auto& T:Field.Tiles) T.Value.ContactDirtyBlocks=0;
    Field.BedChangesSince(0,BedRegions);
    TestTrue(TEXT("Water revision survives terrain upload"),BedRegions.Num()>0);
    Field.BedChangesSince(Field.GeometryRevision,BedRegions);
    TestTrue(TEXT("Already observed bed has no pending regions"),BedRegions.IsEmpty());
    const float Before=Field.Sample(FVector2D(0,0)).DeltaCm;
    Field.Step(.1f);
    TestTrue(TEXT("Only disturbed cells decay"),Field.LastDecayCells>0 && Field.LastDecayCells<4096);
    TestEqual(TEXT("Cosmetic decay cannot change support height"),Field.Sample(FVector2D(0,0)).DeltaCm,Before);
    const FIntPoint First=Field.WindowTile*Field.TileCells;
    TArray<FFloat16Color> Full,FullWater,Block,BlockWater;
    const double Start=FPlatformTime::Seconds();
    Field.Pack(FIntRect(First,First+FIntPoint(Field.WindowCells,Field.WindowCells)),Paint,Appearance,Full,FullWater);
    const double FullMs=(FPlatformTime::Seconds()-Start)*1000.;
    int32 Cells=0;double SparseMs=0;
    for (const auto& T:Field.Tiles)
        for (int32 B=0;B<64;++B)
            if (T.Value.DirtyBlocks&(uint64(1)<<B))
            {
                const FIntPoint Origin=T.Key*Field.TileCells+FIntPoint(B%8,B/8)*Field.UploadBlockCells;
                const double BlockStart=FPlatformTime::Seconds();
                Field.Pack(FIntRect(Origin,Origin+FIntPoint(32,32)),Paint,Appearance,Block,BlockWater);
                SparseMs+=(FPlatformTime::Seconds()-BlockStart)*1000.;Cells+=1024;
                for (int32 Y=0;Y<32;++Y)
                    for (int32 X=0;X<32;++X)
                    {
                        const int32 Index=(Origin.Y-First.Y+Y)*Field.WindowCells+Origin.X-First.X+X;
                        if (FMemory::Memcmp(&Full[Index],&Block[Y*32+X],sizeof(FFloat16Color)) ||
                            FMemory::Memcmp(&FullWater[Index],&BlockWater[Y*32+X],sizeof(FFloat16Color)))
                        { AddError(TEXT("Partial upload differs from full-window reference"));return false; }
                    }
            }
    TestTrue(TEXT("One contact uploads less than 5 percent of the window"),Cells>0 && Cells<Field.WindowCells*Field.WindowCells/20);
    AddInfo(FString::Printf(TEXT("Mud packing CPU: full_window_ms=%.3f dirty_blocks_ms=%.3f full_cells=%d dirty_cells=%d decay_cells=%d (not GPU/frame timing)"),FullMs,SparseMs,Full.Num(),Cells,Field.LastDecayCells));
    Field.Step(1000.f);Field.Step(.1f);
    TestEqual(TEXT("Settled cosmetics retire from the decay set"),Field.LastDecayCells,0);
    // Recaching a negative-coordinate tile must still retain its deformation.
    Field.Focus(FVector2D(1700,0),Paint);Field.Focus(FVector2D::ZeroVector,Paint);
    TestEqual(TEXT("Window movement preserves cached rut height"),Field.Sample(FVector2D(0,0)).DeltaCm,Before);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTLandscapeMudPressureTest,"GrandTour.LandscapeMud.LoadedClumps",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTLandscapeMudPressureTest::RunTest(const FString& Parameters)
{
    FGTLandscapeSurfaceField Field;
    Field.AuthoredHeightAt=[](FVector2D P,float) { return float(5.*FMath::Cos(P.X*PI/25.)); };
    auto Paint=[](FVector2D) { return FLinearColor(12,-5,0,.8f); };
    Field.Focus(FVector2D::ZeroVector,Paint);
    const FIntPoint Crown(0,0),Hollow(2,0),Untouched(0,24);
    const float Before=Field.Read(Crown).DeltaCm,LowBefore=Field.Read(Hollow).DeltaCm,Outside=Field.Read(Untouched).DeltaCm;
    auto Press=[&]() { Field.Stamp(FVector2D::ZeroVector,FVector2D::ZeroVector,FVector2D(1,0),28,9,Paint,0,.2f); };
    Press();
    TestTrue(TEXT("Pressure yields gradually within its cell-rate limit"),Before-Field.Read(Crown).DeltaCm>0 && Before-Field.Read(Crown).DeltaCm<=.201f);
    for (int32 I=0;I<60;++I) Press();
    TestTrue(TEXT("Loaded crown visibly crushes"),Before-Field.Read(Crown).DeltaCm>3.f);
    TestTrue(TEXT("Displaced crowns smear into low bed pockets without excavating them"),Field.Read(Hollow).DeltaCm>=LowBefore && Field.Read(Hollow).DeltaCm<=-1.49f);
    TestEqual(TEXT("Ground outside the footprint and banks keeps its shape"),Field.Read(Untouched).DeltaCm,Outside);
    const float Settled=Field.Read(Crown).DeltaCm;
    for (int32 I=0;I<120;++I) Press();
    TestTrue(TEXT("Sustained pressure reaches equilibrium without endless digging"),FMath::Abs(Field.Read(Crown).DeltaCm-Settled)<.01f);
    TestTrue(TEXT("Crushed material is deposited in the banks"),Field.ExcavatedCm3>0 && FMath::Abs(Field.ExcavatedCm3-Field.DepositedCm3)<.001);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTLandscapeMudSettlementTest,"GrandTour.LandscapeMud.LoadEquilibrium",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTLandscapeMudSettlementTest::RunTest(const FString& Parameters)
{
    FGTLandscapeSurfaceSample Bog;
    Bog.Softness=.85f;Bog.SinkageCapCm=28;Bog.RestWheelSupportCm=-5;
    const float Settlement=Bog.LoadedSettlementCm(.65f);
    TestTrue(TEXT("Ordinary wheel load settles visibly into the bog"),Settlement>10 && Settlement<16);
    TestTrue(TEXT("Unloaded soil does not settle"),Bog.LoadedSettlementCm(0)==0);
    FGTLandscapeSurfaceField Field;
    Field.AuthoredHeightAt=[](FVector2D P,float) { return float(-5+5*FMath::Cos(P.X*PI/25.)); };
    auto Paint=[](FVector2D) { return FLinearColor(28,-5,0,.85f); };
    Field.Focus(FVector2D::ZeroVector,Paint);
    const float Plane=Bog.RestWheelSupportCm-Settlement*.7f;
    auto Press=[&]() { Field.Stamp(FVector2D::ZeroVector,FVector2D::ZeroVector,FVector2D(1,0),28,Settlement*.7f+12,Paint,Plane,.4f); };
    for(int32 I=0;I<180;++I) Press();
    const float Settled=Field.Read(FIntPoint(0,0)).DeltaCm;
    AddInfo(FString::Printf(TEXT("Loaded bog equilibrium: target=%.3f actual=%.3f"),Plane,Settled));
    TestTrue(TEXT("Soil flows to the rounded tyre bottom near the loaded plane"),Settled>=Plane && Settled<Plane+1.f);
    for(int32 I=0;I<600;++I) Press();
    TestTrue(TEXT("Sustained load cannot ratchet the plane deeper"),FMath::Abs(Field.Read(FIntPoint(0,0)).DeltaCm-Settled)<.01f);
    Bog.GrassCover=1;Bog.SinkageCapCm=5;Bog.RestWheelSupportCm=0;
    TestTrue(TEXT("Shallow sod gives much less than bare bog"),Bog.LoadedSettlementCm(.65f)<4);
    Bog.GrassCover=0;Bog.SinkageCapCm=2;Bog.RestWheelSupportCm=-1;
    TestTrue(TEXT("Thin soil still stops at its mineral base"),Bog.LoadedSettlementCm(1.6f)<=1);
    Bog.SinkageCapCm=48;Bog.RestWheelSupportCm=-5;Bog.Softness=1;
    TestTrue(TEXT("Deep saturated reservoir yields more than the approved standard bog"),Bog.LoadedSettlementCm(.65f)>Settlement+4.f);
    const FLinearColor PuddlePaint(48,-2,0,1);
    TestEqual(TEXT("Deep rut water reaches its water table instead of following a six cm cap"),
        -22.f+FGTLandscapeSurfaceField::WaterDepth(-22.f,PuddlePaint),-2.f);
    TestEqual(TEXT("Raised clumps above the water table remain exposed"),FGTLandscapeSurfaceField::WaterDepth(1.f,PuddlePaint),0.f);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudContactLawTest,"GrandTour.LandscapeMud.SoilContactLaw",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTMudContactLawTest::RunTest(const FString& Parameters)
{
    const auto Crawl=GTMudContact::Evaluate(.9f,0,16,38,100,100);
    const auto Spin=GTMudContact::Evaluate(.9f,0,16,38,100,900);
    const auto Fast=GTMudContact::Evaluate(.9f,0,16,38,1100,1100);
    const auto Sod=GTMudContact::Evaluate(.9f,1,4,38,100,100);
    const auto Reverse=GTMudContact::Evaluate(.9f,0,16,38,-100,-100);
    TestTrue(TEXT("Wheelspin reduces soil purchase"),Spin.Slip>.8f && Spin.Grip<Crawl.Grip);
    TestTrue(TEXT("Deep mud dissipates fast entry more strongly than crawl"),Fast.Resistance>Crawl.Resistance*4);
    TestTrue(TEXT("Shallow sod offers more purchase and less resistance"),Sod.Grip>Crawl.Grip && Sod.Resistance<Crawl.Resistance);
    TestEqual(TEXT("Resistance is symmetric in reverse"),Reverse.Resistance,Crawl.Resistance);
    TestEqual(TEXT("Stationary soil drag cannot self-propel the car"),GTMudContact::Evaluate(1,0,20,38,0,100).Resistance,0.f);
    FGTSoilContact Patch;Patch.bActive=true;
    for(int32 Y=0;Y<9;++Y)for(int32 X=0;X<9;++X)Patch.Height[Y*9+X]=float(X-4)*1.25f-8;
    float H=0;FVector2D N;
    TestTrue(TEXT("Physics contact samples a local snapshot"),Patch.Sample(FVector2D(5,3),H,N));
    TestTrue(TEXT("Snapshot retains height and slope"),FMath::IsNearlyEqual(H,-7.5f,.001f) && FMath::IsNearlyEqual(float(N.X),.1f,.001f));
    TestFalse(TEXT("A stale patch cannot override distant terrain"),Patch.Sample(FVector2D(100,0),H,N));
    return true;
}
#endif
