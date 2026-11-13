#include "Weather/GTRainEmitter.h"

#include "Vehicle/GTWinchAnchor.h"

#include "Components/AudioComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Misc/App.h"

namespace
{
	constexpr float RainSynthSampleRate = 22050.f;
}

// ---- synth ------------------------------------------------------------------------------------------

void FGTWeatherSynth::CopyParamsFrom(const FGTWeatherSynth& Other)
{
	RainGain.store(Other.RainGain.load());
	WindGain.store(Other.WindGain.load());
	ClickRate.store(Other.ClickRate.load());
	SampleRate = Other.SampleRate;
}

void FGTWeatherSynth::Generate(int16* Out, int32 NumSamples)
{
	const float Rain = FMath::Clamp(RainGain.load(), 0.f, 1.f);
	const float WindLevel = FMath::Clamp(WindGain.load(), 0.f, 1.f);
	const float Clicks = FMath::Max(0.f, ClickRate.load());
	const float WindAlpha = 120.f / SampleRate;      // ~120 Hz low-pass: a rumble
	for (int32 Index = 0; Index < NumSamples; ++Index)
	{
		Rng = Rng * 1664525u + 1013904223u;
		const float Noise = (static_cast<int32>(Rng >> 9) & 0x7FFF) / 16384.f - 1.f;
		WindLow += (Noise - WindLow) * WindAlpha;
		// Gusts: a slow wandering envelope on the wind.
		GustPhase += 0.6f / SampleRate;
		Gust = 0.6f + 0.4f * FMath::Sin(GustPhase * 2.f * PI) * FMath::Sin(GustPhase * 2.f * PI * 0.37f + 1.f);
		RainHigh = Noise - RainLast + 0.95f * RainHigh;   // one-pole high-pass: rain hiss keeps the top end
		RainLast = Noise;
		const float RainSample = RainHigh;
		// Geiger clicks: Poisson-ish, each a short decaying pulse.
		ClickAccumulator += Clicks / SampleRate;
		if (ClickAccumulator >= 1.f)
		{
			ClickAccumulator -= 1.f;
			ClickLevel = 1.f;
		}
		ClickLevel *= 0.985f;
		const float Sample = WindLow * 6.f * WindLevel * Gust + RainSample * 0.25f * Rain + ClickLevel * 0.5f * (Noise > 0.f ? 1.f : -1.f);
		Out[Index] = static_cast<int16>(FMath::Clamp(Sample, -1.f, 1.f) * 32767.f);
	}
}

UGTWeatherSoundWave::UGTWeatherSoundWave(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	SetSampleRate(static_cast<uint32>(RainSynthSampleRate));
	NumChannels = 1;
	Duration = INDEFINITELY_LOOPING_DURATION;
	SoundGroup = SOUNDGROUP_Default;
	bLooping = false;
	NumSamplesToGeneratePerCallback = 1024;
}

int32 UGTWeatherSoundWave::OnGeneratePCMAudio(TArray<uint8>& OutAudio, int32 NumSamples)
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

// ---- emitter ----------------------------------------------------------------------------------------

AGTRainEmitter::AGTRainEmitter()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;   // after the pawns moved this frame
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Random.Initialize(0x5EED5);
}

void AGTRainEmitter::BeginPlay()
{
	Super::BeginPlay();
	bGpuEnabled = FApp::CanEverRender();
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMesh* Cylinder = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));

	auto MakePool = [this](const TCHAR* Name, UStaticMesh* Mesh, int32 Count, const FLinearColor& Colour) -> UInstancedStaticMeshComponent*
	{
		UInstancedStaticMeshComponent* Component = NewObject<UInstancedStaticMeshComponent>(this, Name, RF_Transient);
		Component->SetupAttachment(Root);
		Component->SetAbsolute(true, true, true);   // instances are placed in world space
		Component->SetStaticMesh(Mesh);
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Component->SetCastShadow(false);
		Component->SetMobility(EComponentMobility::Movable);
		Component->bAffectDynamicIndirectLighting = false;   // BO2: out of the Lumen scene
		Component->bVisibleInRayTracing = false;             // BO2: out of the ray-tracing scene
		Component->bAffectDistanceFieldLighting = false;
		Component->bReceivesDecals = false;
		Component->RegisterComponent();
		GTGreybox::ApplyPropColour(Component, this, Colour);
		for (int32 Index = 0; Index < Count; ++Index)
		{
			Component->AddInstance(FTransform(FRotator::ZeroRotator, FVector::ZeroVector, FVector::ZeroVector), /*bWorldSpace*/ true);
		}
		return Component;
	};
	if (Cube && Cylinder)
	{
		Drops = MakePool(TEXT("RainDrops"), Cube, MaxDrops, FLinearColor(0.7f, 0.78f, 0.9f));
		Splashes = MakePool(TEXT("RainSplashes"), Cylinder, MaxSplashes, FLinearColor(0.75f, 0.8f, 0.9f));
	}
	DropPool.Reserve(MaxDrops);
	SplashPool.Reserve(MaxSplashes);
	DropTransforms.SetNum(MaxDrops);
	SplashTransforms.SetNum(MaxSplashes);

	// Occlusion capture: straight down from CaptureHeight above the player.
	RenderTarget = LoadObject<UTextureRenderTarget2D>(nullptr, *RenderTargetPath);
	bRenderTargetFromAsset = RenderTarget != nullptr;
	if (!RenderTarget)
	{
		RenderTarget = NewObject<UTextureRenderTarget2D>(this, TEXT("RT_RainOcclusion_Transient"), RF_Transient);
		RenderTarget->RenderTargetFormat = RTF_RGBA16f;
		RenderTarget->ClearColor = FLinearColor(1e6f, 0.f, 0.f, 1.f);
		RenderTarget->InitAutoFormat(512, 512);
		RenderTarget->UpdateResourceImmediate(true);
		UE_LOG(LogTemp, Warning, TEXT("AGTRainEmitter: %s missing (run Art/setup_m3_weather.bat); materials will not see the occlusion"), *RenderTargetPath);
	}
	Resolution = RenderTarget->SizeX;
	Capture = NewObject<USceneCaptureComponent2D>(this, TEXT("OcclusionCapture"), RF_Transient);
	Capture->SetupAttachment(Root);
	Capture->SetRelativeLocationAndRotation(FVector(0.f, 0.f, CaptureHeight), FRotator(-90.f, 0.f, 0.f));
	Capture->ProjectionType = ECameraProjectionMode::Orthographic;
	Capture->OrthoWidth = HalfExtentCm * 2.f;
	Capture->CaptureSource = ESceneCaptureSource::SCS_SceneDepth;
	Capture->bCaptureEveryFrame = false;
	Capture->bCaptureOnMovement = false;
	Capture->bAlwaysPersistRenderingState = true;
	Capture->TextureTarget = RenderTarget;
	Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_RenderScenePrimitives;
	Capture->ShowFlags.SetAtmosphere(false);
	Capture->ShowFlags.SetFog(false);
	Capture->ShowFlags.SetVolumetricFog(false);
	Capture->ShowFlags.SetParticles(false);
	if (Drops)
	{
		Capture->HideComponent(Drops);
	}
	if (Splashes)
	{
		Capture->HideComponent(Splashes);
	}
	Capture->RegisterComponent();

	// Ambience.
	Synth = MakeShared<FGTWeatherSynth, ESPMode::ThreadSafe>();
	Synth->SampleRate = RainSynthSampleRate;
	Wave = NewObject<UGTWeatherSoundWave>(this, TEXT("WeatherSynthWave"), RF_Transient);
	Wave->Synth = Synth;
	if (GEngine && GEngine->UseSound())
	{
		Audio = NewObject<UAudioComponent>(this, TEXT("WeatherAudio"), RF_Transient);
		Audio->bAutoActivate = false;
		Audio->bAllowSpatialization = false;
		Audio->SetupAttachment(Root);
		Audio->RegisterComponent();
		Audio->SetSound(Wave);
		Audio->Play();
		bAudioPlaying = Audio->IsPlaying();
	}
	UE_LOG(LogTemp, Display, TEXT("AGTRainEmitter: pool %d drops, capture %d px over %.0f m, rt=%s, gpu=%d, audio=%s"),
		MaxDrops, Resolution, HalfExtentCm * 2.f / 100.f, bRenderTargetFromAsset ? TEXT("asset") : TEXT("transient"), bGpuEnabled ? 1 : 0,
		bAudioPlaying ? TEXT("playing") : TEXT("silent"));
}

void AGTRainEmitter::EndPlay(const EEndPlayReason::Type EndPlayReason)
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

void AGTRainEmitter::SetWeather(float InRainIntensity, float InTemperatureC, const FVector& InWindCmPerSec)
{
	RainIntensity = FMath::Clamp(InRainIntensity, 0.f, 1.f);
	TemperatureC = InTemperatureC;
	Wind = InWindCmPerSec;
}

void AGTRainEmitter::SetAmbience(float RainGain, float WindGain, float ClickRate)
{
	if (Synth.IsValid())
	{
		Synth->RainGain.store(RainGain);
		Synth->WindGain.store(WindGain);
		Synth->ClickRate.store(ClickRate);
	}
}

void AGTRainEmitter::Follow(const FVector& InCameraLocation)
{
	CameraLocation = InCameraLocation;
	bHaveCamera = true;
}

void AGTRainEmitter::SpawnDrop()
{
	const float Angle = Random.FRand() * 2.f * PI;
	const float Radius = FMath::Sqrt(Random.FRand()) * SpawnRadius;
	const FVector Start = CameraLocation + FVector(FMath::Cos(Angle) * Radius, FMath::Sin(Angle) * Radius, SpawnHeight + Random.FRand() * SpawnHeightSpread);
	UWorld* World = GetWorld();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(RainCover), false);
	Params.AddIgnoredActor(this);
	FHitResult Hit;
	// Open sky above the spawn point, or no drop: nothing rains under cover.
	if (World->LineTraceSingleByChannel(Hit, Start, Start + FVector(0.f, 0.f, CoverTraceLength), ECC_Visibility, Params))
	{
		++RejectedUnderCover;
		return;
	}
	FDrop Drop;
	Drop.Position = Start;
	Drop.GroundZ = World->LineTraceSingleByChannel(Hit, Start, Start - FVector(0.f, 0.f, SpawnHeight + SpawnHeightSpread + 3000.f), ECC_Visibility, Params)
		? Hit.ImpactPoint.Z : Start.Z - (SpawnHeight + SpawnHeightSpread + 3000.f);
	DropPool.Add(Drop);
	++TotalSpawned;
}

void AGTRainEmitter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bHaveCamera || DeltaSeconds <= 0.f)
	{
		return;
	}
	const bool bSnow = TemperatureC < 0.f;
	const float FallSpeed = bSnow ? SnowFallSpeed : RainFallSpeed;
	const float FallDistance = SpawnHeight + SpawnHeightSpread * 0.5f + 160.f;   // to about the ground
	const float Life = FallDistance / FMath::Max(50.f, FallSpeed);
	const float Rate = RainIntensity * MaxDrops / Life;   // keeps the pool full at full intensity
	SpawnAccumulator += Rate * DeltaSeconds;
	int32 Budget = 64;   // traces per tick cap: a long frame does not spawn a wall of drops
	while (SpawnAccumulator >= 1.f && DropPool.Num() < MaxDrops && Budget-- > 0)
	{
		SpawnAccumulator -= 1.f;
		SpawnDrop();
	}
	if (DropPool.Num() >= MaxDrops)
	{
		SpawnAccumulator = 0.f;
	}

	const FVector Velocity = Wind + FVector(0.f, 0.f, -FallSpeed);
	for (int32 Index = DropPool.Num() - 1; Index >= 0; --Index)
	{
		FDrop& Drop = DropPool[Index];
		Drop.Position += Velocity * DeltaSeconds;
		Drop.Life += DeltaSeconds;
		if (Drop.Position.Z <= Drop.GroundZ || Drop.Life > Life * 2.f)
		{
			if (!bSnow && SplashPool.Num() < MaxSplashes && Drop.Position.Z <= Drop.GroundZ)
			{
				FSplash Splash;
				Splash.Position = FVector(Drop.Position.X, Drop.Position.Y, Drop.GroundZ + 1.f);
				SplashPool.Add(Splash);
				++SplashCount;
			}
			DropPool.RemoveAtSwap(Index);
		}
	}
	for (int32 Index = SplashPool.Num() - 1; Index >= 0; --Index)
	{
		SplashPool[Index].Life += DeltaSeconds;
		if (SplashPool[Index].Life >= SplashSeconds)
		{
			SplashPool.RemoveAtSwap(Index);
		}
	}
	LiveDrops = DropPool.Num();
	PushInstances();
	UpdateCapture(DeltaSeconds);
}

void AGTRainEmitter::PushInstances()
{
	const bool bSnow = TemperatureC < 0.f;
	const FVector StreakScale = bSnow ? FVector(0.03f, 0.03f, 0.03f) : FVector(0.006f, 0.006f, 0.3f);   // 3 cm flake or a 0.6 x 30 cm streak
	const FRotator Lean = (Wind.IsNearlyZero() || bSnow) ? FRotator::ZeroRotator : FRotator(FMath::RadiansToDegrees(FMath::Atan2(Wind.Size2D(), RainFallSpeed)), Wind.Rotation().Yaw, 0.f);
	for (int32 Index = 0; Index < MaxDrops; ++Index)
	{
		if (Index < DropPool.Num())
		{
			DropTransforms[Index] = FTransform(Lean, DropPool[Index].Position, StreakScale);
		}
		else
		{
			DropTransforms[Index] = FTransform(FRotator::ZeroRotator, FVector::ZeroVector, FVector::ZeroVector);
		}
	}
	for (int32 Index = 0; Index < MaxSplashes; ++Index)
	{
		if (Index < SplashPool.Num())
		{
			const float Grow = 0.04f + 0.1f * SplashPool[Index].Life / FMath::Max(SplashSeconds, 0.01f);
			SplashTransforms[Index] = FTransform(FRotator::ZeroRotator, SplashPool[Index].Position, FVector(Grow, Grow, 0.004f));
		}
		else
		{
			SplashTransforms[Index] = FTransform(FRotator::ZeroRotator, FVector::ZeroVector, FVector::ZeroVector);
		}
	}
	if (Drops)
	{
		Drops->BatchUpdateInstancesTransforms(0, DropTransforms, /*bWorldSpace*/ true, /*bMarkRenderStateDirty*/ false, /*bTeleport*/ true);
	}
	if (Splashes)
	{
		Splashes->BatchUpdateInstancesTransforms(0, SplashTransforms, true, false, true);
	}
}

void AGTRainEmitter::UpdateCapture(float DeltaSeconds)
{
	// Snap the window to whole texels so the captured depth does not swim as the player walks.
	const float Texel = HalfExtentCm * 2.f / FMath::Max(1, Resolution);
	const FVector Snapped(FMath::GridSnap(CameraLocation.X, Texel), FMath::GridSnap(CameraLocation.Y, Texel), CameraLocation.Z);
	const bool bMoved = !Snapped.Equals(CaptureCentre, 0.5f);
	CaptureCentre = Snapped;
	SetActorLocation(Snapped);
	CaptureTimer += DeltaSeconds;
	if (!bGpuEnabled || !Capture)
	{
		return;
	}
	if (bMoved || CaptureTimer >= CaptureInterval || CaptureCount == 0)
	{
		CaptureTimer = 0.f;
		Capture->CaptureScene();
		++CaptureCount;
	}
}

FVector2D AGTRainEmitter::WorldToPixel(const FVector& World) const
{
	// Looking down with pitch -90 and yaw 0: image up is world +X, image right is world +Y.
	const float U = 0.5f + (World.Y - CaptureCentre.Y) / (2.f * HalfExtentCm);
	const float V = 0.5f - (World.X - CaptureCentre.X) / (2.f * HalfExtentCm);
	return FVector2D(U * Resolution, V * Resolution);
}

bool AGTRainEmitter::ReadOcclusionDepth(const FVector& WorldLocation, float& OutDepth) const
{
	if (!bGpuEnabled || !RenderTarget || CaptureCount == 0)
	{
		return false;
	}
	const FVector2D Pixel = WorldToPixel(WorldLocation);
	const int32 X = FMath::FloorToInt(Pixel.X);
	const int32 Y = FMath::FloorToInt(Pixel.Y);
	if (X < 0 || Y < 0 || X >= Resolution || Y >= Resolution)
	{
		return false;
	}
	OutDepth = UKismetRenderingLibrary::ReadRenderTargetRawPixel(GetWorld(), RenderTarget, X, Y, false).R;
	return true;
}

int32 AGTRainEmitter::CountDropsInBox(const FVector& Centre, const FVector& Extent) const
{
	int32 Count = 0;
	for (const FDrop& Drop : DropPool)
	{
		const FVector D = Drop.Position - Centre;
		if (FMath::Abs(D.X) <= Extent.X && FMath::Abs(D.Y) <= Extent.Y && FMath::Abs(D.Z) <= Extent.Z)
		{
			++Count;
		}
	}
	return Count;
}

float AGTRainEmitter::RenderTestBlock(int32 NumSamples) const
{
	if (!Synth.IsValid() || NumSamples <= 0)
	{
		return 0.f;
	}
	FGTWeatherSynth Local;
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

FString AGTRainEmitter::Describe() const
{
	return FString::Printf(TEXT("rain=%.2f temp=%.1f live=%d spawned=%d rejectedUnderCover=%d splashes=%d captures=%d centre=(%.0f, %.0f) top=%.0f gpu=%d rt=%s"),
		RainIntensity, TemperatureC, LiveDrops, TotalSpawned, RejectedUnderCover, SplashCount, CaptureCount, CaptureCentre.X, CaptureCentre.Y, GetCaptureTopZ(),
		bGpuEnabled ? 1 : 0, bRenderTargetFromAsset ? TEXT("asset") : TEXT("transient"));
}
