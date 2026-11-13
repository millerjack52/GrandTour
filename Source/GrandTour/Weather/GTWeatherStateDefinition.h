#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "GTWeatherStateDefinition.generated.h"

/** The values a weather state targets; the subsystem blends between them (ARCHITECTURE 6d). */
USTRUCT(BlueprintType)
struct FGTWeatherValues
{
	GENERATED_BODY()

	/** Precipitation 0..1: rain above freezing, snow below. Wetness and snow cover are simulated from it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather", meta = (ClampMin = 0, ClampMax = 1))
	float RainIntensity = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather", meta = (ClampMin = 0, ClampMax = 1))
	float CloudCover = 0.1f;

	/** Absolute exponential height fog density (0.01 clear .. 0.12 storm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather", meta = (ClampMin = 0, ClampMax = 1))
	float FogDensity = 0.01f;

	/** Multiplier on the map's directional light. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather", meta = (ClampMin = 0, ClampMax = 1))
	float SunScale = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather", meta = (ClampMin = 0, ClampMax = 1))
	float SkyScale = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather", meta = (ClampMin = 0, ClampMax = 1))
	float WindStrength = 0.1f;

	/** World yaw the wind blows toward, degrees. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather")
	float WindYaw = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather")
	float TemperatureC = 15.f;

	/** Greybox ambience levels 0..1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather", meta = (ClampMin = 0, ClampMax = 1))
	float RainGain = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Weather", meta = (ClampMin = 0, ClampMax = 1))
	float WindGain = 0.05f;

	static FGTWeatherValues Lerp(const FGTWeatherValues& A, const FGTWeatherValues& B, float Alpha);
	FString Describe() const;
};

/**
 * One weather state (ARCHITECTURE 6d): clear, overcast, rain, storm or snow. Target values for
 * the collection, the map's sun / sky / fog and the ambience, and how long the blend into it
 * takes. Assets live under /Game/GrandTour/Weather (Art/setup_m3_weather.bat writes
 * DA_Weather_*); the subsystem builds the same five from DefaultStates() when an asset is missing.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTWeatherStateDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Weather")
	FName StateId = TEXT("Clear");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Weather")
	FText DisplayName;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Weather")
	FGameplayTag Tag;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Weather")
	FGTWeatherValues Values;

	/** Seconds to blend into this state. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Weather", meta = (ClampMin = 0.1))
	float TransitionSeconds = 20.f;

	struct FDefault
	{
		const TCHAR* AssetName;
		const TCHAR* Id;
		const TCHAR* Name;
		const TCHAR* Tag;
		FGTWeatherValues Values;
		float TransitionSeconds;
	};
	/** Clear, Overcast, Rain, Storm, Snow. */
	static TArrayView<const FDefault> DefaultStates();
	static const FDefault* FindDefault(FName Id);

	void ApplyDefault(const FDefault& Row);
};
