#include "Vehicle/GTResponsiveSteering.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTResponsiveSteeringTest,"GrandTour.Vehicle.ResponsiveSteering",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTResponsiveSteeringTest::RunTest(const FString& Parameters)
{
    using S=FGTResponsiveSteering;
    TestEqual(TEXT("low range bypass"),S::Weight(true,false,0,0,1),0.f);
    TestEqual(TEXT("firm high range consistent at every speed"),S::Weight(false,false,0,0,1),1.f);
    TestEqual(TEXT("mud bypass"),S::Weight(false,true,0,0,1),0.f);
    TestEqual(TEXT("deep yielding gravel bypass"),S::Weight(false,false,12,0,1),0.f);
    TestEqual(TEXT("water bypass"),S::Weight(false,false,0,5,1),0.f);
    TestEqual(TEXT("A/B off"),S::Weight(false,false,0,0,0),0.f);
    TestTrue(TEXT("gradual water blend"),S::Weight(false,false,0,3,1)>0 && S::Weight(false,false,0,3,1)<1);
    FVehicleInputRateConfig Base;
    Base.RiseRate=2.5f;Base.FallRate=5.f;Base.InputCurveFunction=EInputFunctionType::SquaredFunction;
    auto Config=Base;S State;
    // Use Chaos's real filter to check taps, reversal, centring and signed input.
    auto Tap=[](FVehicleInputRateConfig C,float Dt)
    {
        float V=0;
        for(int32 I=0;I<FMath::RoundToInt(.18f/Dt);++I)V=C.InterpInputValue(Dt,V,1.f);
        return C.CalcControlFunction(V);
    };
    State.Update(Config,1);
    TestTrue(TEXT("180ms tap reaches useful steering"),Tap(Config,.01f)>.95f && Tap(Base,.01f)<.21f);
    TestTrue(TEXT("tap consistent at 30 and 120 Hz"),FMath::Abs(Tap(Config,1.f/30)-Tap(Config,1.f/120))<.03f);
    TestEqual(TEXT("half stick keeps half available lock"),Config.CalcControlFunction(.5f),.5f);
    TestEqual(TEXT("signed input"),Config.CalcControlFunction(-.5f),-.5f);
    float V=.5f;
    for(int32 I=0;I<15;++I)V=Config.InterpInputValue(.01f,V,-.5f);
    TestTrue(TEXT("countersteer reaches opposite half within 150ms"),V<-.49f);
    for(int32 I=0;I<10;++I)V=Config.InterpInputValue(.01f,V,0);
    TestEqual(TEXT("release recentres"),V,0.f);
    for(float Weight:{.01f,.25f,.5f,.75f,.99f})
    {
        State.Update(Config,Weight);
        float Last=0;
        for(int32 I=0;I<=100;++I)
        {
            const float X=I*.01f,Y=Config.CalcControlFunction(X);
            TestTrue(TEXT("blend bounded and monotonic"),Y>=Last-.0001f && Y<=1.f && Y>=0.f);
            TestTrue(TEXT("blend agrees with original/linear mix"),FMath::Abs(Y-FMath::Lerp(X*X,X,Weight))<.0011f);
            Last=Y;
        }
    }
    State.Update(Config,0);
    TestEqual(TEXT("restore authored rise"),Config.RiseRate,Base.RiseRate);
    TestEqual(TEXT("restore authored fall"),Config.FallRate,Base.FallRate);
    TestEqual(TEXT("restore exact crawl input curve"),Tap(Config,.01f),Tap(Base,.01f));
    // Different car defaults survive enabling/disabling; no shared class mutation.
    Base.RiseRate=10;Base.FallRate=12;Base.InputCurveFunction=EInputFunctionType::LinearFunction;
    Config=Base;S Other;Other.Update(Config,1);Other.Update(Config,0);
    TestEqual(TEXT("per-car fast filter preserved"),Config.RiseRate,10.f);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTCountersteerResponseTest,"GrandTour.Vehicle.CountersteerResponse",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTCountersteerResponseTest::RunTest(const FString& Parameters)
{
    auto Reversal=[](float Dt,float Sign,float Weight,float Strength)
    {
        FVehicleInputRateConfig Config;Config.RiseRate=2.5f;Config.FallRate=5.f;
        FGTResponsiveSteering State;State.Update(Config,Weight);
        float V=Sign,T=0.f;
        while(V*Sign>-.99f && T<2.f)
        {
            State.Update(Config,Weight);State.UpdateReversal(Config,-Sign,V,Strength);
            V=Config.InterpInputValue(Dt,V,-Sign);T+=Dt;
        }
        return T;
    };
    for(float Dt:{1.f/30,1.f/60,1.f/120})for(float Sign:{-1.f,1.f})
    {
        const float Before=Reversal(Dt,Sign,1,0),After=Reversal(Dt,Sign,1,1);
        TestTrue(TEXT("full reversal within 180ms at 30/60/120Hz"),After<=.18f);
        TestTrue(TEXT("explicit reversal saves at least 90ms"),Before-After>.09f);
        TestEqual(TEXT("low-range/soft-ground gate preserves original filter exactly"),Reversal(Dt,Sign,0,1),Reversal(Dt,Sign,0,0));
    }
    FVehicleInputRateConfig Config;Config.RiseRate=2.5f;Config.FallRate=5.f;
    FGTResponsiveSteering State;State.Update(Config,1);
    State.UpdateReversal(Config,1,0,1);
    TestEqual(TEXT("initial turn-in remains 6/s"),Config.RiseRate,6.f);
    State.UpdateReversal(Config,-1,.8f,1);
    TestEqual(TEXT("intentional opposite key starts reversal"),Config.RiseRate,12.f);
    State.UpdateReversal(Config,0,.2f,1);
    TestEqual(TEXT("release cancels reversal"),State.ReversalDirection,0.f);
    TestEqual(TEXT("normal release remains 8/s"),Config.FallRate,8.f);
    State.UpdateReversal(Config,-.5f,.8f,1);
    TestEqual(TEXT("partial analogue input retains normal rate"),Config.RiseRate,6.f);
    State.UpdateReversal(Config,-1,.8f,1);State.Update(Config,0);State.UpdateReversal(Config,-1,.5f,1);
    TestEqual(TEXT("entering low range cancels reversal"),State.ReversalDirection,0.f);
    TestEqual(TEXT("low range authored rise restored"),Config.RiseRate,2.5f);
    State.Update(Config,1);State.UpdateReversal(Config,-1,.8f,.5f);
    TestEqual(TEXT("speed/surface transition blends smoothly"),Config.RiseRate,9.f);
    State.UpdateReversal(Config,-1,.8f,1,.3f);State.UpdateReversal(Config,-1,-.7f,1,.3f);
    TestEqual(TEXT("damage-biased target cancels reversal when reached"),State.ReversalDirection,0.f);
    TestEqual(TEXT("damage-biased settled rate restored"),Config.RiseRate,6.f);
    FVehicleInputRateConfig Fast;Fast.RiseRate=20;Fast.FallRate=25;
    FGTResponsiveSteering FastState;FastState.Update(Fast,1);FastState.UpdateReversal(Fast,-1,1,1);
    TestEqual(TEXT("faster authored rise preserved"),Fast.RiseRate,20.f);
    TestEqual(TEXT("faster authored fall preserved"),Fast.FallRate,25.f);
    return true;
}
#endif
