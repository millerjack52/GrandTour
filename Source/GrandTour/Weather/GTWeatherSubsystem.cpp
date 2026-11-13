#include "Weather/GTWeatherSubsystem.h"

#include "Weather/GTRainEmitter.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"

/**
 * Water stage W5: the driver's rain switch. 0..1 forces what GetRainIntensity and GetRainAt answer - the river stage
 * reads it, so `gt.Weather.Rain 1` with `gt.Water.RiverLagScale 0.2` puts a three-minute rise into a minute - and -1
 * gives the reading back to the weather simulation. It moves the numbers and nothing else: the drops in the air, the
 * ambience, the wetness the ground gains and MPC_Weather all go on reading the state blend's own intensity.
 */
static TAutoConsoleVariable<float> CVarWeatherRain(
	TEXT("gt.Weather.Rain"), -1.f,
	TEXT("Forces the rain intensity everything that reads a number reads, 0..1 (-1 = the simulation's own). Numbers only: no drops, no wetness."));

namespace
{
	const FName WeatherParamWetness(TEXT("Wetness"));
	const FName ParamRain(TEXT("RainIntensity"));
	const FName WeatherParamSnow(TEXT("SnowAmount"));
	const FName ParamWindStrength(TEXT("WindStrength"));
	const FName ParamTemperature(TEXT("Temperature"));
	const FName ParamOcclusionEnabled(TEXT("OcclusionEnabled"));
	const FName ParamWindDirection(TEXT("WindDirection"));
	const FName ParamOcclusionBounds(TEXT("OcclusionBounds"));
}

const FName UGTWeatherSubsystem::GlobalWindParamIntensity(TEXT("WindIntensity"));
const FName UGTWeatherSubsystem::GlobalWindParamDirection(TEXT("WindDirection"));

bool UGTWeatherSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGTWeatherSubsystem::Initialize(FSubsystemCollectionBase& InCollection)
{
	Super::Initialize(InCollection);
	Collection = LoadObject<UMaterialParameterCollection>(nullptr, *CollectionPath);
	bCollectionFound = Collection != nullptr;
	if (Collection)
	{
		for (const FCollectionScalarParameter& Parameter : Collection->ScalarParameters)
		{
			ScalarNames.Add(Parameter.ParameterName);
		}
		for (const FCollectionVectorParameter& Parameter : Collection->VectorParameters)
		{
			VectorNames.Add(Parameter.ParameterName);
		}
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTWeatherSubsystem: %s missing (run Art/setup_m1_weather.bat); materials will not see the weather"), *CollectionPath);
	}
	UGTWeatherStateDefinition* Clear = FindState(TEXT("Clear"));
	BlendFrom = BlendTo = Base = Current = Clear ? Clear->Values : FGTWeatherValues();
	TargetState = Clear;
	BlendAlpha = 1.f;
	// LD3: the OW foliage's wind, by a soft path - loaded when there, never required.
	GlobalWind = LoadObject<UMaterialParameterCollection>(nullptr, *GlobalWindPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (GlobalWind)
	{
		const FCollectionScalarParameter* Intensity = GlobalWind->GetScalarParameterByName(GlobalWindParamIntensity);
		const float ClearWind = Clear ? Clear->Values.WindStrength : 0.f;
		UE_LOG(LogTemp, Display, TEXT("UGTWeatherSubsystem: MPC_GlobalWind WindIntensity = WindStrength x %.2f (Clear %.2f -> %.3f; the collection's default %.3f)"),
			GlobalWindIntensityPerStrength, ClearWind, ClearWind * GlobalWindIntensityPerStrength, Intensity ? Intensity->DefaultValue : -1.f);
	}
	UE_LOG(LogTemp, Display, TEXT("UGTWeatherSubsystem: ready, collection=%d, start %s"), bCollectionFound ? 1 : 0, *Current.Describe());
}

UGTWeatherStateDefinition* UGTWeatherSubsystem::FindState(FName StateId)
{
	if (TObjectPtr<UGTWeatherStateDefinition>* Found = States.Find(StateId))
	{
		return Found->Get();
	}
	const UGTWeatherStateDefinition::FDefault* Row = UGTWeatherStateDefinition::FindDefault(StateId);
	if (!Row)
	{
		return nullptr;
	}
	UGTWeatherStateDefinition* State = LoadObject<UGTWeatherStateDefinition>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), *StateFolder, Row->AssetName, Row->AssetName));
	if (State)
	{
		++StatesFromAssets;
	}
	else
	{
		State = NewObject<UGTWeatherStateDefinition>(this, Row->AssetName, RF_Transient);
		State->ApplyDefault(*Row);
	}
	States.Add(StateId, State);
	return State;
}

void UGTWeatherSubsystem::SetState(UGTWeatherStateDefinition* State, bool bInstant)
{
	if (!State)
	{
		return;
	}
	BlendFrom = Base;
	BlendTo = State->Values;
	BlendSeconds = bInstant ? 0.f : FMath::Max(0.1f, State->TransitionSeconds);
	BlendAlpha = bInstant ? 1.f : 0.f;
	TargetState = State;
	++Transitions;
	if (bInstant)
	{
		Base = BlendTo;
	}
	UE_LOG(LogTemp, Display, TEXT("UGTWeatherSubsystem: -> %s over %.0f s"), *State->StateId.ToString(), BlendSeconds);
}

void UGTWeatherSubsystem::ReportStormPressure(float Pressure, UGTWeatherStateDefinition* InStormState)
{
	if (Pressure > PendingStormPressure)
	{
		PendingStormPressure = FMath::Clamp(Pressure, 0.f, 1.f);
		if (InStormState)
		{
			StormState = InStormState;
		}
	}
}

FString UGTWeatherSubsystem::GetStateName() const
{
	return TargetState ? TargetState->StateId.ToString() : TEXT("none");
}

FVector UGTWeatherSubsystem::GetWindVector() const
{
	const float Yaw = FMath::DegreesToRadians(Current.WindYaw);
	return FVector(FMath::Cos(Yaw), FMath::Sin(Yaw), 0.f) * Current.WindStrength * 600.f;
}

bool UGTWeatherSubsystem::IsUnderCover(const FVector& WorldLocation) const
{
	const UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(WeatherCover), false);
	if (Emitter)
	{
		Params.AddIgnoredActor(Emitter);
	}
	if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0))
	{
		Params.AddIgnoredActor(Pawn);
	}
	FHitResult Hit;
	return World->LineTraceSingleByChannel(Hit, WorldLocation, WorldLocation + FVector(0.f, 0.f, CoverTraceLength), ECC_Visibility, Params);
}

bool UGTWeatherSubsystem::ReadCollectionScalar(FName Name, float& OutValue) const
{
	if (!Collection || !GetWorld())
	{
		return false;
	}
	UMaterialParameterCollectionInstance* Instance = GetWorld()->GetParameterCollectionInstance(Collection);
	return Instance && Instance->GetScalarParameterValue(Name, OutValue);
}

void UGTWeatherSubsystem::FindSceneActors()
{
	bSceneSearched = true;
	UWorld* World = GetWorld();
	for (TActorIterator<ADirectionalLight> It(World); It; ++It)
	{
		if (It->ActorHasTag(TEXT("GTWeatherUnmanaged"))) { continue; }
		if (UDirectionalLightComponent* Light = Cast<UDirectionalLightComponent>(It->GetLightComponent()))
		{
			Sun = Light;
			SunBaseIntensity = Light->Intensity;
			break;
		}
	}
	for (TActorIterator<ASkyLight> It(World); It; ++It)
	{
		if (It->ActorHasTag(TEXT("GTWeatherUnmanaged"))) { continue; }
		if (USkyLightComponent* Light = It->GetLightComponent())
		{
			Sky = Light;
			SkyBaseIntensity = Light->Intensity;
			break;
		}
	}
	for (TActorIterator<AExponentialHeightFog> It(World); It; ++It)
	{
		// Authored study/map atmospheres can own their density instead of being
		// overwritten by the global weather state's absolute fog value.
		if (It->ActorHasTag(TEXT("GTWeatherUnmanaged"))) { continue; }
		Fog = It->GetComponent();
		break;
	}
	UE_LOG(LogTemp, Display, TEXT("UGTWeatherSubsystem: scene sun=%d (%.1f) sky=%d (%.1f) fog=%d"), Sun.IsValid() ? 1 : 0, SunBaseIntensity, Sky.IsValid() ? 1 : 0, SkyBaseIntensity, Fog.IsValid() ? 1 : 0);
}

void UGTWeatherSubsystem::EnsureEmitter()
{
	if (Emitter || !GetWorld())
	{
		return;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Params.ObjectFlags |= RF_Transient;
	Emitter = GetWorld()->SpawnActor<AGTRainEmitter>(AGTRainEmitter::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, Params);
}

void UGTWeatherSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	UWorld* World = GetWorld();
	if (!World || DeltaTime <= 0.f)
	{
		return;
	}
	// W5: read once a tick on the game thread, like the water's own cvars, so GetRainIntensity is a compare and a
	// return wherever it is called from.
	const float RainCvar = CVarWeatherRain.GetValueOnGameThread();
	CvarRainOverride = RainCvar < 0.f ? -1.f : FMath::Clamp(RainCvar, 0.f, 1.f);
	if (!bSceneSearched)
	{
		FindSceneActors();
	}
	EnsureEmitter();

	// State blend, then the storm pressure the fronts reported this frame on top.
	if (BlendAlpha < 1.f)
	{
		BlendAlpha = FMath::Min(1.f, BlendAlpha + DeltaTime / FMath::Max(0.1f, BlendSeconds));
	}
	Base = FGTWeatherValues::Lerp(BlendFrom, BlendTo, FMath::SmoothStep(0.f, 1.f, BlendAlpha));
	StormPressure = PendingStormPressure;
	PendingStormPressure = 0.f;
	ClickRate = PendingClickRate;
	PendingClickRate = 0.f;
	Current = (StormPressure > 0.f && StormState) ? FGTWeatherValues::Lerp(Base, StormState->Values, StormPressure) : Base;

	// Wetness and snow: the two slow quantities.
	const bool bFreezing = Current.TemperatureC < 0.f;
	const float Rain = bFreezing ? 0.f : Current.RainIntensity;
	const float Snowfall = bFreezing ? Current.RainIntensity : 0.f;
	if (Rain > 0.f)
	{
		Wetness += Rain * WetRate * DeltaTime;
	}
	else
	{
		Wetness -= DryRate * (1.f + FMath::Max(0.f, Current.TemperatureC - 15.f) / 10.f) * DeltaTime;
	}
	Wetness = FMath::Clamp(Wetness, 0.f, 1.f);
	if (Snowfall > 0.f)
	{
		SnowAmount += Snowfall * SnowRate * DeltaTime;
	}
	else if (Current.TemperatureC > 0.f)
	{
		SnowAmount -= MeltRate * (Current.TemperatureC / 10.f) * DeltaTime;
		Wetness = FMath::Max(Wetness, FMath::Min(1.f, SnowAmount));   // melting snow is wet
	}
	SnowAmount = FMath::Clamp(SnowAmount, 0.f, 1.f);

	// The emitter follows the player's camera.
	if (Emitter)
	{
		FVector Camera = FVector::ZeroVector;
		if (const APlayerController* PC = UGameplayStatics::GetPlayerController(World, 0))
		{
			Camera = PC->PlayerCameraManager ? PC->PlayerCameraManager->GetCameraLocation() : (PC->GetPawn() ? PC->GetPawn()->GetActorLocation() : FVector::ZeroVector);
		}
		Emitter->Follow(Camera);
		Emitter->SetWeather(Current.RainIntensity, Current.TemperatureC, GetWindVector());
		Emitter->SetAmbience(Current.RainGain, Current.WindGain, ClickRate);
	}
	WriteCollection();
	WriteGlobalWind();
	ApplyToScene();
}

void UGTWeatherSubsystem::WriteGlobalWind()
{
	// Leg dressing LD3 (docs/LEG_DRESSING_PLAN.md): the OW foliage and trunk masters sway by MPC_GlobalWind, so GrandTour's
	// wind drives it - WindIntensity = WindStrength x GlobalWindIntensityPerStrength, WindDirection the wind's heading as
	// a unit XY vector (MPC_Weather's convention; the collection's own default is +Y). Nothing when the asset is missing.
	if (!GlobalWind || !GetWorld())
	{
		return;
	}
	UMaterialParameterCollectionInstance* Instance = GetWorld()->GetParameterCollectionInstance(GlobalWind);
	if (!Instance)
	{
		return;
	}
	if (GlobalWind->GetScalarParameterByName(GlobalWindParamIntensity))
	{
		Instance->SetScalarParameterValue(GlobalWindParamIntensity, Current.WindStrength * GlobalWindIntensityPerStrength);
	}
	if (GlobalWind->GetVectorParameterByName(GlobalWindParamDirection))
	{
		const float Yaw = FMath::DegreesToRadians(Current.WindYaw);
		Instance->SetVectorParameterValue(GlobalWindParamDirection, FLinearColor(FMath::Cos(Yaw), FMath::Sin(Yaw), 0.f, 0.f));
	}
}

bool UGTWeatherSubsystem::ReadGlobalWindScalar(FName Name, float& OutValue, float* OutDefault) const
{
	if (!GlobalWind || !GetWorld())
	{
		return false;
	}
	if (OutDefault)
	{
		const FCollectionScalarParameter* Parameter = GlobalWind->GetScalarParameterByName(Name);
		*OutDefault = Parameter ? Parameter->DefaultValue : 0.f;
	}
	UMaterialParameterCollectionInstance* Instance = GetWorld()->GetParameterCollectionInstance(GlobalWind);
	return Instance && Instance->GetScalarParameterValue(Name, OutValue);
}

void UGTWeatherSubsystem::WriteCollection()
{
	if (!Collection || !GetWorld())
	{
		return;
	}
	UMaterialParameterCollectionInstance* Instance = GetWorld()->GetParameterCollectionInstance(Collection);
	if (!Instance)
	{
		return;
	}
	auto Scalar = [this, Instance](const FName& Name, float Value)
	{
		if (ScalarNames.Contains(Name))
		{
			Instance->SetScalarParameterValue(Name, Value);
		}
	};
	auto Vector = [this, Instance](const FName& Name, const FLinearColor& Value)
	{
		if (VectorNames.Contains(Name))
		{
			Instance->SetVectorParameterValue(Name, Value);
		}
	};
	Scalar(WeatherParamWetness, Wetness);
	Scalar(ParamRain, Current.RainIntensity);
	Scalar(WeatherParamSnow, SnowAmount);
	Scalar(ParamWindStrength, Current.WindStrength);
	Scalar(ParamTemperature, Current.TemperatureC);
	const float Yaw = FMath::DegreesToRadians(Current.WindYaw);
	Vector(ParamWindDirection, FLinearColor(FMath::Cos(Yaw), FMath::Sin(Yaw), 0.f, 0.f));
	if (Emitter)
	{
		Scalar(ParamOcclusionEnabled, (Emitter->bGpuEnabled && Emitter->bRenderTargetFromAsset && Emitter->CaptureCount > 0) ? 1.f : 0.f);
		const FVector Centre = Emitter->GetCaptureCentre();
		Vector(ParamOcclusionBounds, FLinearColor(Centre.X, Centre.Y, Emitter->GetCaptureTopZ(), Emitter->HalfExtentCm));
	}
}

void UGTWeatherSubsystem::ApplyToScene()
{
	if (Sun.IsValid())
	{
		Sun->SetIntensity(SunBaseIntensity * FMath::Clamp(Current.SunScale, 0.f, 1.f));
	}
	if (Sky.IsValid())
	{
		Sky->SetIntensity(SkyBaseIntensity * FMath::Clamp(Current.SkyScale, 0.f, 1.f));
	}
	if (Fog.IsValid())
	{
		Fog->SetFogDensity(FMath::Max(0.f, Current.FogDensity));
	}
}

FString UGTWeatherSubsystem::Describe() const
{
	return FString::Printf(TEXT("state=%s blend=%.2f storm=%.2f wet=%.2f snow=%.2f %s | %s"),
		*GetStateName(), BlendAlpha, StormPressure, Wetness, SnowAmount, *Current.Describe(), Emitter ? *Emitter->Describe() : TEXT("no emitter"));
}
