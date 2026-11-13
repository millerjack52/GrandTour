#include "Core/GTLidarPerformanceSubsystem.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    TAutoConsoleVariable<int32> AutoProfile(TEXT("gt.Lidar.PerformanceAuto"),1,
        TEXT("Apply Art/lidar_performance.json when LiDAR play begins. Set 0 before play to use original quality; -GTLidarPerformance=0 bypasses for a launch."));
    struct FSavedSetting {FString Name,Before,Applied;EConsoleVariableFlags Priority;};
    TArray<FSavedSetting> Saved;
    int32 Users=0;
}

bool UGTLidarPerformanceSubsystem::DoesSupportWorldType(const EWorldType::Type Type) const
{
    return Type==EWorldType::Game || Type==EWorldType::PIE;
}

void UGTLidarPerformanceSubsystem::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    int32 Enabled=AutoProfile.GetValueOnGameThread();
    FParse::Value(FCommandLine::Get(),TEXT("GTLidarPerformance="),Enabled);
    if(!Enabled || UGameplayStatics::GetCurrentLevelName(&World,true)!=TEXT("L_LidarStudy"))return;
    if(Users>0){++Users;bOwnsProfile=true;return;}
    FString Text;
    TSharedPtr<FJsonObject> Root;
    const FString Path=FPaths::ProjectDir()/TEXT("Art/lidar_performance.json");
    if(!FFileHelper::LoadFileToString(Text,*Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root) || !Root.IsValid())
    {
        UE_LOG(LogTemp,Warning,TEXT("LiDAR play preset unavailable: %s"),*Path);return;
    }
    const TArray<TSharedPtr<FJsonValue>>* Commands=nullptr;
    if(!Root->TryGetArrayField(TEXT("commands"),Commands))return;
    for(const auto& Entry:*Commands)
    {
        FString Command,Name,Value;
        if(!Entry->TryGetString(Command) || !Command.Split(TEXT(" "),&Name,&Value))continue;
        if(IConsoleVariable* Variable=IConsoleManager::Get().FindConsoleVariable(*Name))
        {
            const auto Priority=EConsoleVariableFlags(Variable->GetFlags() & ECVF_SetByMask);
            // Explicit console/launch overrides remain authoritative.
            if(Priority>ECVF_SetByCode)continue;
            const FString Before=Variable->GetString();
            Variable->Set(*Value,ECVF_SetByCode);
            Saved.Add({Name,Before,Variable->GetString(),Priority});
        }
    }
    ++Users;bOwnsProfile=true;
    UE_LOG(LogTemp,Display,TEXT("LiDAR play preset applied (%d settings); restored when the last LiDAR play world closes."),Saved.Num());
}

void UGTLidarPerformanceSubsystem::Deinitialize()
{
    if(bOwnsProfile && --Users==0)
    {
        for(const auto& Setting:Saved)
        {
            if(auto* Variable=IConsoleManager::Get().FindConsoleVariable(*Setting.Name))
            {
                if(Variable->GetString()!=Setting.Applied || (Variable->GetFlags()&ECVF_SetByMask)!=ECVF_SetByCode)continue;
                Variable->ClearFlags(ECVF_SetByMask);
                Variable->Set(*Setting.Before,Setting.Priority);
            }
        }
        UE_LOG(LogTemp,Display,TEXT("LiDAR play preset released; prior settings restored unless changed during play."));
        Saved.Reset();
    }
    bOwnsProfile=false;
    Super::Deinitialize();
}
