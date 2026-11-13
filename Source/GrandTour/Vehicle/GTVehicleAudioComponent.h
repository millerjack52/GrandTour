#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Sound/SoundWaveProcedural.h"
#include <atomic>
#include "GTVehicleAudioComponent.generated.h"

class UAudioComponent;
class UChaosWheeledVehicleMovementComponent;
class UGTConditionComponent;
class UGTTractionComponent;

/**
 * Greybox vehicle synth. The game thread writes parameters, the audio thread renders: an engine
 * tone (four harmonics plus a half-rate sub at the firing frequency, gain by throttle, gated by
 * misfires), tyre noise low-passed by surface (tarmac hiss, dirt, mud rumble, snow) and scaled
 * by speed, skid noise from wheel slip, and a decaying noise thud on impacts. Mono int16.
 */
struct FGTVehicleSynth
{
	std::atomic<float> EngineHz{53.f};
	std::atomic<float> EngineGain{0.1f};
	std::atomic<float> TyreCutoff{4000.f};
	std::atomic<float> TyreGain{0.f};
	std::atomic<float> SkidGain{0.f};
	std::atomic<float> ThudGain{0.f};   // set by the game thread on an impact; the renderer takes and decays it
	float SampleRate = 22050.f;

	void Generate(int16* Out, int32 NumSamples);
	void CopyParamsFrom(const FGTVehicleSynth& Other);

private:
	float Phase = 0.f;
	float LowPass = 0.f;
	float ThudLevel = 0.f;
	uint32 Rng = 0x1234567u;
};

UCLASS()
class GRANDTOUR_API UGTVehicleSoundWave : public USoundWaveProcedural
{
	GENERATED_BODY()

public:
	UGTVehicleSoundWave(const FObjectInitializer& ObjectInitializer);

	virtual int32 OnGeneratePCMAudio(TArray<uint8>& OutAudio, int32 NumSamples) override;

	TSharedPtr<FGTVehicleSynth, ESPMode::ThreadSafe> Synth;
};

/**
 * Drives FGTVehicleSynth from the vehicle every tick and plays it through an audio component
 * (ARCHITECTURE 6a "tyre audio by surface tag"). Non-spatial: the driver is in the car. With
 * -nosound (the headless tests) nothing plays, but RenderTestBlock still renders the mix on the
 * calling thread so a test can check the synth produces signal. Real engine and tyre recordings
 * replace the synth in the audio pass; the parameter mapping is what carries over.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTVehicleAudioComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTVehicleAudioComponent();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	/** Movement is non-const only because Chaos' input getters are not const. */
	void Update(float DeltaSeconds, UChaosWheeledVehicleMovementComponent& Move, const UGTTractionComponent& Traction,
	            const UGTConditionComponent& Condition, float EngineRpm, float DriveInput);

	UFUNCTION(BlueprintPure, Category = "GT|Audio")
	FString Describe() const;

	/** Mute this vehicle without muting environmental sound. */
	UFUNCTION(BlueprintCallable, Category = "GT|Audio")
	void SetMuted(bool bInMuted);

	UPROPERTY(BlueprintReadOnly, Category = "GT|Audio")
	bool bMuted = false;

	/** Renders NumSamples of the current mix into a scratch buffer here and returns the RMS level (0..1). For tests. */
	UFUNCTION(BlueprintCallable, Category = "GT|Audio")
	float RenderTestBlock(int32 NumSamples) const;

	UPROPERTY(EditAnywhere, Category = "GT|Audio", meta = (ClampMin = 0, ClampMax = 1))
	float MasterVolume = 0.6f;

	/** Firing pulses per crank revolution: a four-stroke V8 fires four times a turn. */
	UPROPERTY(EditAnywhere, Category = "GT|Audio")
	float FiringPulsesPerRev = 4.f;

	UPROPERTY(EditAnywhere, Category = "GT|Audio")
	float IdleGain = 0.12f;

	UPROPERTY(EditAnywhere, Category = "GT|Audio")
	float ThrottleGain = 0.3f;

	/** Speed (cm/s) at which the tyre noise is at full level. */
	UPROPERTY(EditAnywhere, Category = "GT|Audio")
	float TyreFullSpeed = 2000.f;

	// ---- state, mirrored from the synth for logs and tests ------------------------------------
	UPROPERTY(BlueprintReadOnly, Category = "GT|Audio")
	float EngineHz = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Audio")
	float EngineGain = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Audio")
	float TyreCutoff = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Audio")
	float TyreGain = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Audio")
	float SkidGain = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Audio")
	int32 ThudCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Audio")
	bool bPlaying = false;

private:
	TSharedPtr<FGTVehicleSynth, ESPMode::ThreadSafe> Synth;
	bool bReplacedForH2 = false;

	UPROPERTY(Transient)
	TObjectPtr<UGTVehicleSoundWave> Wave;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> Audio;

	int32 LastImpacts = 0;
};
