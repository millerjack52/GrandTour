#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Sound/SoundWaveProcedural.h"
#include "Vehicle/GTRangeRoverHybridSynth.h"
#include "Vehicle/GTGroundAudioSynth.h"
#include "GTRangeRoverAudioComponent.generated.h"

class UAudioComponent;
class AGTLandscapeSurface;

UCLASS()
class GRANDTOUR_API UGTRangeRoverSoundWave : public USoundWaveProcedural
{
    GENERATED_BODY()
public:
    UGTRangeRoverSoundWave(const FObjectInitializer& Initializer);
    virtual int32 OnGeneratePCMAudio(TArray<uint8>& OutAudio, int32 NumSamples) override;
    // Assigned before Play; never modified while an audio callback can be running.
    TSharedPtr<FGTRangeRoverHybridSynth, ESPMode::ThreadSafe> Synth;
    TSharedPtr<FGTGroundAudioSynth, ESPMode::ThreadSafe> Ground;
};

/** H2 interior/driver audition. Only the Range Rover mesh opts in; parked cars are silent. */
UCLASS(ClassGroup=(GT))
class GRANDTOUR_API UGTRangeRoverAudioComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UGTRangeRoverAudioComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Dt, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
    static bool IsRangeRover(const AActor* Owner);
    static bool IsRangeRoverMeshPath(const FString& Path);
    static bool ShouldBeAudible(bool bCorrectCar, bool bLocalDriver, float Rpm, bool bOutOfFuel, bool bFlooded);
    UPROPERTY(EditAnywhere, Category="GT|Audio", meta=(ClampMin="0",ClampMax="1"))
    float Volume = 1.f;
    UPROPERTY(EditAnywhere, Category="GT|Audio", meta=(ClampMin="0",ClampMax="1"))
    float GroundVolume = 1.f;
    UFUNCTION(BlueprintPure, Category="GT|Audio")
    FString GroundAudioReport() const;
private:
    TSharedPtr<FGTRangeRoverHybridSynth, ESPMode::ThreadSafe> Synth;
    TSharedPtr<FGTGroundAudioSynth, ESPMode::ThreadSafe> Ground;
    FGTGroundAudioMix LastGroundMix;
    TArray<TWeakObjectPtr<AGTLandscapeSurface>> GroundSurfaces;
    TArray<float> FirmGrass;
    TArray<float> PreviousSuspension;
    float GrassQueryTime = 1;
    UPROPERTY(Transient) TObjectPtr<UGTRangeRoverSoundWave> Wave;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> Audio;
    float DiagnosticTime = 0;
    float SilentTime = 1;
};
