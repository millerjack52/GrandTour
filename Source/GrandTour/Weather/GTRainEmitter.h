#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Sound/SoundWaveProcedural.h"
#include <atomic>
#include "GTRainEmitter.generated.h"

class UAudioComponent;
class UInstancedStaticMeshComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;

/** Greybox ambience: rain hiss and wind rumble by level, plus a Geiger click rate near radiation. Mono int16. */
struct FGTWeatherSynth
{
	std::atomic<float> RainGain{0.f};
	std::atomic<float> WindGain{0.f};
	std::atomic<float> ClickRate{0.f};   // clicks per second
	float SampleRate = 22050.f;

	void Generate(int16* Out, int32 NumSamples);
	void CopyParamsFrom(const FGTWeatherSynth& Other);

private:
	float WindLow = 0.f;
	float RainHigh = 0.f;
	float RainLast = 0.f;
	float Gust = 0.f;
	float GustPhase = 0.f;
	float ClickLevel = 0.f;
	float ClickAccumulator = 0.f;
	uint32 Rng = 0x9E3779B9u;
};

UCLASS()
class GRANDTOUR_API UGTWeatherSoundWave : public USoundWaveProcedural
{
	GENERATED_BODY()

public:
	UGTWeatherSoundWave(const FObjectInitializer& ObjectInitializer);
	virtual int32 OnGeneratePCMAudio(TArray<uint8>& OutAudio, int32 NumSamples) override;

	TSharedPtr<FGTWeatherSynth, ESPMode::ThreadSafe> Synth;
};

/**
 * The rain around the player (ARCHITECTURE 6d), greybox until the Niagara pass of M6: a pool of
 * instanced streaks (flakes below freezing) spawned in a cylinder around the camera, falling
 * with the wind, dying with a short splash disc where a downward trace found the ground. A drop
 * is only spawned where an upward trace finds open sky, so nothing rains under cover.
 *
 * It also runs the rain occlusion capture: an orthographic scene capture looking straight down
 * from CaptureHeight above the player writes scene depth into RT_RainOcclusion (re-centred on
 * the player by whole texels, captured every CaptureInterval). MF_Weather compares a surface's
 * height with the captured depth to mask wetness and snow under roofs; the collection's
 * OcclusionBounds carries (centre x, centre y, top z, half extent). Under -NullRHI the capture
 * is skipped and the drops still simulate for the tests. The weather ambience plays from here.
 */
UCLASS()
class GRANDTOUR_API AGTRainEmitter : public AActor
{
	GENERATED_BODY()

public:
	AGTRainEmitter();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

	/** The subsystem sets these every tick. */
	void SetWeather(float InRainIntensity, float InTemperatureC, const FVector& InWindCmPerSec);
	void SetAmbience(float RainGain, float WindGain, float ClickRate);
	void Follow(const FVector& CameraLocation);

	/** Live drops whose position is inside a world box (tests: none under the roof). */
	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	int32 CountDropsInBox(const FVector& Centre, const FVector& Extent) const;

	/** Captured depth (cm below the capture plane) at a world XY; false with no GPU or outside the window. */
	bool ReadOcclusionDepth(const FVector& WorldLocation, float& OutDepth) const;

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	FVector GetCaptureCentre() const { return CaptureCentre; }

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	float GetCaptureTopZ() const { return CaptureCentre.Z + CaptureHeight; }

	/** Renders NumSamples of the ambience and returns the RMS level (tests). */
	float RenderTestBlock(int32 NumSamples) const;

	UFUNCTION(BlueprintPure, Category = "GT|Weather")
	FString Describe() const;

	UPROPERTY(EditAnywhere, Category = "GT|Rain")
	int32 MaxDrops = 600;

	UPROPERTY(EditAnywhere, Category = "GT|Rain")
	float SpawnRadius = 1200.f;

	/** Drops start this far above the camera (plus up to SpawnHeightSpread). */
	UPROPERTY(EditAnywhere, Category = "GT|Rain")
	float SpawnHeight = 800.f;

	UPROPERTY(EditAnywhere, Category = "GT|Rain")
	float SpawnHeightSpread = 400.f;

	UPROPERTY(EditAnywhere, Category = "GT|Rain")
	float RainFallSpeed = 900.f;

	UPROPERTY(EditAnywhere, Category = "GT|Rain")
	float SnowFallSpeed = 150.f;

	/** Upward trace length that decides "open sky". */
	UPROPERTY(EditAnywhere, Category = "GT|Rain")
	float CoverTraceLength = 5000.f;

	UPROPERTY(EditAnywhere, Category = "GT|Rain")
	float SplashSeconds = 0.2f;

	UPROPERTY(EditAnywhere, Category = "GT|Rain")
	int32 MaxSplashes = 200;

	// ---- occlusion capture -----------------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "GT|Occlusion")
	float CaptureHeight = 3000.f;

	/** Half the side of the captured square, cm (60 m window). */
	UPROPERTY(EditAnywhere, Category = "GT|Occlusion")
	float HalfExtentCm = 3000.f;

	UPROPERTY(EditAnywhere, Category = "GT|Occlusion")
	float CaptureInterval = 0.25f;

	UPROPERTY(EditAnywhere, Category = "GT|Occlusion")
	FString RenderTargetPath = TEXT("/Game/GrandTour/Materials/RT_RainOcclusion.RT_RainOcclusion");

	// ---- state ---------------------------------------------------------------------------------
	UPROPERTY(BlueprintReadOnly, Category = "GT|Rain")
	int32 LiveDrops = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Rain")
	int32 TotalSpawned = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Rain")
	int32 RejectedUnderCover = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Rain")
	int32 SplashCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Occlusion")
	int32 CaptureCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Occlusion")
	int32 Resolution = 512;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Occlusion")
	bool bGpuEnabled = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Occlusion")
	bool bRenderTargetFromAsset = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Audio")
	bool bAudioPlaying = false;

private:
	struct FDrop
	{
		FVector Position = FVector::ZeroVector;
		float GroundZ = 0.f;
		float Life = 0.f;
	};
	struct FSplash
	{
		FVector Position = FVector::ZeroVector;
		float Life = 0.f;
	};

	void SpawnDrop();
	void PushInstances();
	void UpdateCapture(float DeltaSeconds);
	FVector2D WorldToPixel(const FVector& World) const;

	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(Transient)
	TObjectPtr<UInstancedStaticMeshComponent> Drops;

	UPROPERTY(Transient)
	TObjectPtr<UInstancedStaticMeshComponent> Splashes;

	UPROPERTY(Transient)
	TObjectPtr<USceneCaptureComponent2D> Capture;

	UPROPERTY(Transient)
	TObjectPtr<UTextureRenderTarget2D> RenderTarget;

	UPROPERTY(Transient)
	TObjectPtr<UGTWeatherSoundWave> Wave;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> Audio;

	TSharedPtr<FGTWeatherSynth, ESPMode::ThreadSafe> Synth;
	TArray<FDrop> DropPool;
	TArray<FSplash> SplashPool;
	TArray<FTransform> DropTransforms;
	TArray<FTransform> SplashTransforms;
	FVector CameraLocation = FVector::ZeroVector;
	FVector CaptureCentre = FVector::ZeroVector;
	FVector Wind = FVector::ZeroVector;
	float RainIntensity = 0.f;
	float TemperatureC = 15.f;
	float SpawnAccumulator = 0.f;
	float CaptureTimer = 0.f;
	bool bHaveCamera = false;
	FRandomStream Random;
};
