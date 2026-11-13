#include "Weather/GTWeatherStateDefinition.h"

#include "GameplayTagsManager.h"

FGTWeatherValues FGTWeatherValues::Lerp(const FGTWeatherValues& A, const FGTWeatherValues& B, float Alpha)
{
	const float T = FMath::Clamp(Alpha, 0.f, 1.f);
	FGTWeatherValues R;
	R.RainIntensity = FMath::Lerp(A.RainIntensity, B.RainIntensity, T);
	R.CloudCover = FMath::Lerp(A.CloudCover, B.CloudCover, T);
	R.FogDensity = FMath::Lerp(A.FogDensity, B.FogDensity, T);
	R.SunScale = FMath::Lerp(A.SunScale, B.SunScale, T);
	R.SkyScale = FMath::Lerp(A.SkyScale, B.SkyScale, T);
	R.WindStrength = FMath::Lerp(A.WindStrength, B.WindStrength, T);
	R.WindYaw = A.WindYaw + FMath::FindDeltaAngleDegrees(A.WindYaw, B.WindYaw) * T;
	R.TemperatureC = FMath::Lerp(A.TemperatureC, B.TemperatureC, T);
	R.RainGain = FMath::Lerp(A.RainGain, B.RainGain, T);
	R.WindGain = FMath::Lerp(A.WindGain, B.WindGain, T);
	return R;
}

FString FGTWeatherValues::Describe() const
{
	return FString::Printf(TEXT("rain=%.2f cloud=%.2f fog=%.3f sun=%.2f sky=%.2f wind=%.2f@%.0f temp=%.1f audio=%.2f/%.2f"),
		RainIntensity, CloudCover, FogDensity, SunScale, SkyScale, WindStrength, WindYaw, TemperatureC, RainGain, WindGain);
}

namespace
{
	FGTWeatherValues MakeValues(float Rain, float Cloud, float Fog, float Sun, float Sky, float Wind, float Yaw, float Temp, float RainGain, float WindGain)
	{
		FGTWeatherValues V;
		V.RainIntensity = Rain;
		V.CloudCover = Cloud;
		V.FogDensity = Fog;
		V.SunScale = Sun;
		V.SkyScale = Sky;
		V.WindStrength = Wind;
		V.WindYaw = Yaw;
		V.TemperatureC = Temp;
		V.RainGain = RainGain;
		V.WindGain = WindGain;
		return V;
	}

	const UGTWeatherStateDefinition::FDefault WeatherDefaults[] = {
		//  asset                id           name          tag                rain cloud fog    sun  sky  wind yaw  temp  audio
		{TEXT("DA_Weather_Clear"),    TEXT("Clear"),    TEXT("Clear"),    TEXT("Weather.Clear"),    MakeValues(0.0f, 0.1f, 0.010f, 1.0f, 1.0f, 0.1f, 20.f, 18.f, 0.00f, 0.05f), 20.f},
		{TEXT("DA_Weather_Overcast"), TEXT("Overcast"), TEXT("Overcast"), TEXT("Weather.Overcast"), MakeValues(0.0f, 0.9f, 0.020f, 0.6f, 0.9f, 0.3f, 30.f, 14.f, 0.00f, 0.15f), 20.f},
		{TEXT("DA_Weather_Rain"),     TEXT("Rain"),     TEXT("Rain"),     TEXT("Weather.Rain"),     MakeValues(0.7f, 1.0f, 0.040f, 0.4f, 0.7f, 0.5f, 40.f, 10.f, 0.50f, 0.30f), 15.f},
		{TEXT("DA_Weather_Storm"),    TEXT("Storm"),    TEXT("Storm"),    TEXT("Weather.Storm"),    MakeValues(1.0f, 1.0f, 0.120f, 0.2f, 0.5f, 1.0f, 60.f, 8.f,  0.90f, 0.80f), 10.f},
		{TEXT("DA_Weather_Snow"),     TEXT("Snow"),     TEXT("Snow"),     TEXT("Weather.Snow"),     MakeValues(0.6f, 1.0f, 0.060f, 0.5f, 0.9f, 0.4f, 10.f, -5.f, 0.05f, 0.30f), 20.f},
	};
}

TArrayView<const UGTWeatherStateDefinition::FDefault> UGTWeatherStateDefinition::DefaultStates()
{
	return MakeArrayView(WeatherDefaults, UE_ARRAY_COUNT(WeatherDefaults));
}

const UGTWeatherStateDefinition::FDefault* UGTWeatherStateDefinition::FindDefault(FName Id)
{
	for (const FDefault& Row : WeatherDefaults)
	{
		if (Id == FName(Row.Id))
		{
			return &Row;
		}
	}
	return nullptr;
}

void UGTWeatherStateDefinition::ApplyDefault(const FDefault& Row)
{
	StateId = Row.Id;
	DisplayName = FText::FromString(Row.Name);
	Tag = UGameplayTagsManager::Get().RequestGameplayTag(FName(Row.Tag), /*ErrorIfNotFound*/ false);
	Values = Row.Values;
	TransitionSeconds = Row.TransitionSeconds;
}
