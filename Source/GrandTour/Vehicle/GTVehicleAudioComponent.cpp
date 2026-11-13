#include "Vehicle/GTVehicleAudioComponent.h"
#include "Vehicle/GTRangeRoverAudioComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

#include "Core/GTGameplayTags.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTTractionComponent.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/Engine.h"
#include "GameFramework/Actor.h"

namespace
{
	constexpr float SynthSampleRate = 22050.f;

	struct FSurfaceSound
	{
		float Cutoff;     // Hz, one-pole low-pass on the tyre noise
		float Loudness;   // relative level at full speed
	};

	FSurfaceSound SoundFor(const FGameplayTag& Tag)
	{
		if (Tag == GTTags::Surface_Mud.GetTag() || Tag == GTTags::Surface_Bog.GetTag())  { return {600.f, 1.0f}; }
		if (Tag == GTTags::Surface_Snow.GetTag()) { return {900.f, 0.7f}; }
		if (Tag == GTTags::Surface_Dirt.GetTag()) { return {1500.f, 0.8f}; }
		if (Tag == GTTags::Surface_Sand.GetTag()) { return {1200.f, 0.8f}; }
		return {4000.f, 0.5f};   // tarmac and anything untagged
	}
}

// ---- synth ----------------------------------------------------------------------------------------

void FGTVehicleSynth::CopyParamsFrom(const FGTVehicleSynth& Other)
{
	EngineHz.store(Other.EngineHz.load());
	EngineGain.store(Other.EngineGain.load());
	TyreCutoff.store(Other.TyreCutoff.load());
	TyreGain.store(Other.TyreGain.load());
	SkidGain.store(Other.SkidGain.load());
	ThudGain.store(Other.ThudGain.load());
	SampleRate = Other.SampleRate;
}

void FGTVehicleSynth::Generate(int16* Out, int32 NumSamples)
{
	const float Hz = EngineHz.load(std::memory_order_relaxed);
	const float EG = EngineGain.load(std::memory_order_relaxed);
	const float Cutoff = FMath::Clamp(TyreCutoff.load(std::memory_order_relaxed), 50.f, SampleRate * 0.45f);
	const float TG = TyreGain.load(std::memory_order_relaxed);
	const float SG = SkidGain.load(std::memory_order_relaxed);
	const float Alpha = 1.f - FMath::Exp(-2.f * PI * Cutoff / SampleRate);
	const float ThudDecay = FMath::Exp(-1.f / (0.15f * SampleRate));
	float Thud = FMath::Max(ThudLevel, ThudGain.exchange(0.f));   // take a new thud, then decay it here
	const float Step = Hz / SampleRate;

	for (int32 Index = 0; Index < NumSamples; ++Index)
	{
		Phase += Step;
		if (Phase >= 1.f)
		{
			Phase -= 1.f;
		}
		float Engine = 0.f;
		for (int32 Harmonic = 1; Harmonic <= 4; ++Harmonic)
		{
			Engine += FMath::Sin(2.f * PI * Harmonic * Phase) / Harmonic;
		}
		Engine = Engine * 0.5f + 0.4f * FMath::Sin(PI * Phase);   // the half-rate sub gives the lumpy V8 feel

		Rng ^= Rng << 13;
		Rng ^= Rng >> 17;
		Rng ^= Rng << 5;
		const float Noise = (Rng / 4294967296.f) * 2.f - 1.f;
		LowPass += Alpha * (Noise - LowPass);

		const float Sample = EG * Engine + TG * LowPass + SG * Noise + Thud * Noise;
		Thud *= ThudDecay;
		Out[Index] = static_cast<int16>(FMath::Clamp(Sample, -1.f, 1.f) * 32000.f);
	}
	ThudLevel = Thud;
}

// ---- sound wave -----------------------------------------------------------------------------------

UGTVehicleSoundWave::UGTVehicleSoundWave(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	SetSampleRate(static_cast<uint32>(SynthSampleRate));
	NumChannels = 1;
	Duration = INDEFINITELY_LOOPING_DURATION;
	SoundGroup = SOUNDGROUP_Default;
	bLooping = false;
	NumSamplesToGeneratePerCallback = 1024;
}

int32 UGTVehicleSoundWave::OnGeneratePCMAudio(TArray<uint8>& OutAudio, int32 NumSamples)
{
	OutAudio.SetNumUninitialized(NumSamples * sizeof(int16));
	if (Synth.IsValid())
	{
		Synth->Generate(reinterpret_cast<int16*>(OutAudio.GetData()), NumSamples);
	}
	else
	{
		FMemory::Memzero(OutAudio.GetData(), OutAudio.Num());
	}
	return NumSamples;
}

// ---- component ------------------------------------------------------------------------------------

UGTVehicleAudioComponent::UGTVehicleAudioComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick after condition
}

void UGTVehicleAudioComponent::BeginPlay()
{
	Super::BeginPlay();
	// The RR uses its approved H2 renderer. The rally audio audition retains silence for other cars.
	bReplacedForH2 = UGTRangeRoverAudioComponent::IsRangeRover(GetOwner());
	bMuted = bMuted || (!bReplacedForH2 && FParse::Param(FCommandLine::Get(), TEXT("GTRangeRoverAudioTest")));
	Synth = MakeShared<FGTVehicleSynth, ESPMode::ThreadSafe>();
	Synth->SampleRate = SynthSampleRate;
	Wave = NewObject<UGTVehicleSoundWave>(this, TEXT("VehicleSynthWave"), RF_Transient);
	Wave->Synth = Synth;

	AActor* Owner = GetOwner();
	if (Owner && GEngine && GEngine->UseSound())
	{
		Audio = NewObject<UAudioComponent>(Owner, TEXT("VehicleAudio"), RF_Transient);
		Audio->bAutoActivate = false;
		Audio->bAllowSpatialization = false;   // the driver sits in the car
		Audio->SetupAttachment(Owner->GetRootComponent());
		Audio->RegisterComponent();
		Audio->SetSound(Wave);
		if (!bMuted && !bReplacedForH2) Audio->Play();
		bPlaying = Audio->IsPlaying();
	}
	UE_LOG(LogTemp, Display, TEXT("UGTVehicleAudioComponent: synth %s (%.0f Hz mono)"), bPlaying ? TEXT("playing") : TEXT("silent: no audio device"), SynthSampleRate);
}

void UGTVehicleAudioComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (Audio)
	{
		Audio->Stop();
	}
	if (Wave)
	{
		Wave->Synth.Reset();
	}
	Super::EndPlay(EndPlayReason);
}

void UGTVehicleAudioComponent::SetMuted(bool bInMuted)
{
	bMuted=bInMuted;
	if (Audio)
	{
		if (bMuted || bReplacedForH2) Audio->Stop();
		else if (!Audio->IsPlaying()) Audio->Play();
	}
	bPlaying=Audio && Audio->IsPlaying();
}

void UGTVehicleAudioComponent::Update(float DeltaSeconds, UChaosWheeledVehicleMovementComponent& Move, const UGTTractionComponent& Traction,
                                      const UGTConditionComponent& Condition, float EngineRpm, float DriveInput)
{
	if (!Synth.IsValid())
	{
		return;
	}
	if (bMuted || bReplacedForH2)
	{
		EngineGain=TyreGain=SkidGain=0.f;
		Synth->EngineGain.store(0.f);Synth->TyreGain.store(0.f);
		Synth->SkidGain.store(0.f);Synth->ThudGain.store(0.f);
		LastImpacts=Condition.TotalImpacts;
		bPlaying=false;
		return;
	}
	// Engine: firing frequency from rpm, gain from throttle, gated by misfires and an empty tank.
	const float Rpm = FMath::Max(0.f, EngineRpm);   // the drivetrain's engine (Chaos's mechanical sim is off)
	EngineHz = Rpm / 60.f * FiringPulsesPerRev;
	const float Throttle = FMath::Clamp(DriveInput, 0.f, 1.f);
	EngineGain = (IdleGain + ThrottleGain * Throttle) * (Condition.bMisfiring ? 0.3f : 1.f) * (Condition.bOutOfFuel || Condition.bFlooded ? 0.f : 1.f) * MasterVolume;

	// Tyres: the surfaces under the wheels in contact set the colour, speed the level; slip adds skid.
	const float Speed = FMath::Abs(Move.GetForwardSpeed());
	float CutoffSum = 0.f;
	float Loudness = 0.f;
	float Slip = 0.f;
	int32 Contacts = 0;
	for (const FGTWheelTraction& Wheel : Traction.Wheels)
	{
		if (!Wheel.bInContact)
		{
			continue;
		}
		const FSurfaceSound Sound = SoundFor(Wheel.SurfaceTag);
		CutoffSum += Sound.Cutoff;
		Loudness = FMath::Max(Loudness, Sound.Loudness);
		if (Wheel.bSlipping)
		{
			Slip = FMath::Max(Slip, FMath::Clamp(Wheel.SlipMagnitude / 300.f, 0.f, 1.f));
		}
		++Contacts;
	}
	TyreCutoff = Contacts > 0 ? CutoffSum / Contacts : 4000.f;
	TyreGain = Contacts > 0 ? FMath::Clamp(Speed / FMath::Max(1.f, TyreFullSpeed), 0.f, 1.f) * Loudness * 0.35f * MasterVolume : 0.f;
	SkidGain = Slip * 0.3f * MasterVolume;

	Synth->EngineHz.store(EngineHz);
	Synth->EngineGain.store(EngineGain);
	Synth->TyreCutoff.store(TyreCutoff);
	Synth->TyreGain.store(TyreGain);
	Synth->SkidGain.store(SkidGain);

	// Impacts: a thud scaled by the hit's severity.
	if (Condition.TotalImpacts != LastImpacts)
	{
		LastImpacts = Condition.TotalImpacts;
		const float Severity = FMath::Clamp(Condition.LastImpactDeltaV / 1500.f, 0.f, 1.f);
		if (Severity > 0.f)
		{
			Synth->ThudGain.store(FMath::Max(Synth->ThudGain.load(), Severity * MasterVolume));
			++ThudCount;
		}
	}
	bPlaying = Audio && Audio->IsPlaying();
}

float UGTVehicleAudioComponent::RenderTestBlock(int32 NumSamples) const
{
	if (!Synth.IsValid() || NumSamples <= 0)
	{
		return 0.f;
	}
	FGTVehicleSynth Local;
	Local.CopyParamsFrom(*Synth);
	TArray<int16> Buffer;
	Buffer.SetNumUninitialized(NumSamples);
	Local.Generate(Buffer.GetData(), NumSamples);
	double Sum = 0.0;
	for (const int16 Sample : Buffer)
	{
		const double Value = Sample / 32767.0;
		Sum += Value * Value;
	}
	return static_cast<float>(FMath::Sqrt(Sum / NumSamples));
}

FString UGTVehicleAudioComponent::Describe() const
{
	return FString::Printf(TEXT("audio engine=%.0fHz/%.2f tyre=%.0fHz/%.2f skid=%.2f thuds=%d playing=%d"),
		EngineHz, EngineGain, TyreCutoff, TyreGain, SkidGain, ThudCount, bPlaying ? 1 : 0);
}
