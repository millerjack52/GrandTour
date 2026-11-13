#include "Vehicle/GTRangeRoverAudioComponent.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/MemoryReader.h"
#include "Audio.h"
#include "HAL/PlatformTime.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTRangeRoverAudioTest,"GrandTour.Vehicle.RangeRoverHybridH2",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTRangeRoverAudioTest::RunTest(const FString& Parameters)
{
    using C=UGTRangeRoverAudioComponent;
    TestTrue(TEXT("only approved RR mesh opts in"),C::IsRangeRoverMeshPath(TEXT("/Game/GrandTour/Vehicles/Bodies/RangeRover/SK_RangeRover.SK_RangeRover")));
    TestFalse(TEXT("other car excluded"),C::IsRangeRoverMeshPath(TEXT("/Game/GrandTour/Vehicles/Bodies/Defender/SK_Defender.SK_Defender")));
    TestFalse(TEXT("similar names excluded"),C::IsRangeRoverMeshPath(TEXT("/Game/GrandTour/Vehicles/Bodies/RangeRoverSport/SK_RangeRoverSport.SK_RangeRoverSport")));
    TestTrue(TEXT("local driver audible"),C::ShouldBeAudible(true,true,800,false,false));
    TestFalse(TEXT("parked car silent"),C::ShouldBeAudible(true,false,800,false,false));
    TestFalse(TEXT("other car silent"),C::ShouldBeAudible(false,true,800,false,false));
    TestFalse(TEXT("engine stopped silent"),C::ShouldBeAudible(true,true,0,false,false));
    TestFalse(TEXT("empty tank silent"),C::ShouldBeAudible(true,true,800,true,false));
    TestFalse(TEXT("flooded engine silent"),C::ShouldBeAudible(true,true,800,false,true));
    const auto Bank=FGTHybridBank::Load(); if (!TestTrue(TEXT("staged H2 bank loads"),Bank.IsValid())) return false;
    FGTRangeRoverHybridSynth Whole(Bank), Split(Bank);
    Whole.TargetGain=Split.TargetGain=1; Whole.TargetRpm=Split.TargetRpm=4200; Whole.TargetThrottle=Split.TargetThrottle=.85f;
    TArray<int16> A,B; A.SetNumUninitialized(24000); B.SetNumUninitialized(24000);
    Whole.Render(A.GetData(),12000); Split.Render(B.GetData(),4567); Split.Render(B.GetData()+9134,7433);
    TestTrue(TEXT("all cursors, combustion and filter state continuous across callbacks"),A==B);
    TestTrue(TEXT("RPM tracks drivetrain target"),FMath::Abs(Whole.GetSmoothedRpmForTest()-4200)<.01);
    auto* Wave=NewObject<UGTRangeRoverSoundWave>(); Wave->Synth=MakeShared<FGTRangeRoverHybridSynth,ESPMode::ThreadSafe>(Bank);
    TArray<uint8> Callback;
    TestEqual(TEXT("UE callback returns sample count"),Wave->OnGeneratePCMAudio(Callback,2048),2048);
    TestEqual(TEXT("stereo int16 callback byte count"),Callback.Num(),4096);
    TestEqual(TEXT("stereo frame count"),Wave->Synth->RenderedFrames.load(),uint64(1024));
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("AudioH2QA");
    TArray<uint8> Controls, Expected;
    if (!TestTrue(TEXT("independent oracle controls prepared"),FFileHelper::LoadFileToArray(Controls,*(Dir/TEXT("controls.bin"))))) return false;
    if (!TestTrue(TEXT("independent oracle prepared"),FFileHelper::LoadFileToArray(Expected,*(Dir/TEXT("expected.pcm"))))) return false;
    FMemoryReader Reader(Controls); uint32 Block,Count; Reader<<Block<<Count;
    if (!TestTrue(TEXT("bounded control data"),Block==256 && Count==2250 && Controls.Num()==8+Count*12 && Expected.Num()==Block*Count*4)) return false;
    FGTRangeRoverHybridSynth Native(Bank);
    TArray<int16> Render; Render.SetNumUninitialized(Block*Count*2);
    const double Started=FPlatformTime::Seconds();
    for (uint32 I=0;I<Count;++I)
    {
        float R,T,G; Reader<<R<<T<<G;
        Native.TargetRpm=R; Native.TargetThrottle=T; Native.TargetGain=G;
        Native.Render(Render.GetData()+I*Block*2,Block);
    }
    const double Elapsed=FPlatformTime::Seconds()-Started;
    int32 MaxError=0, Peak=0; const int16* Oracle=reinterpret_cast<const int16*>(Expected.GetData());
    for (int32 I=0;I<Render.Num();++I) { MaxError=FMath::Max(MaxError,FMath::Abs(int32(Render[I])-Oracle[I])); Peak=FMath::Max(Peak,FMath::Abs(int32(Render[I]))); }
    TestTrue(TEXT("native matches approved Python H2 signal path within four PCM counts"),MaxError<=4);
    TestTrue(TEXT("output has headroom"),Peak<29490);
    AddInfo(FString::Printf(TEXT("H2: 12 seconds rendered in %.3f s (%.2f%% of realtime), max PCM error=%d peak=%d"),Elapsed,Elapsed/12*100,MaxError,Peak));
    TArray<uint8> Wav; SerializeWaveFile(Wav,reinterpret_cast<const uint8*>(Render.GetData()),Render.Num()*sizeof(int16),2,48000);
    TestTrue(TEXT("native validation WAV saved"),FFileHelper::SaveArrayToFile(Wav,*(Dir/TEXT("native_render.wav"))));
    return true;
}
#endif
