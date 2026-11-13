#include "Character/GTExposureComponent.h"

UGTExposureComponent::UGTExposureComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTPlayerCharacter::Tick
}

void UGTExposureComponent::Update(float DeltaSeconds, bool bSheltered)
{
	TimeSinceDrain += DeltaSeconds;
	float Recovery = 0.f;
	if (bSheltered)
	{
		Recovery = ShelteredRecoveryPerSecond;
	}
	else if (TimeSinceDrain >= RecoveryDelay)
	{
		Recovery = OpenAirRecoveryPerSecond;
	}
	Exposure = FMath::Clamp(Exposure + Recovery * DeltaSeconds, 0.f, MaxExposure);
	if (bCollapsed && Exposure >= RecoverThreshold)
	{
		bCollapsed = false;
		UE_LOG(LogTemp, Display, TEXT("UGTExposureComponent: recovered (%.0f)"), Exposure);
	}
}

void UGTExposureComponent::Drain(float Amount, FGameplayTag HazardTag)
{
	if (Amount <= 0.f)
	{
		return;
	}
	Exposure = FMath::Clamp(Exposure - Amount, 0.f, MaxExposure);
	TotalDrained += Amount;
	LastHazardTag = HazardTag;
	TimeSinceDrain = 0.f;
	if (Exposure <= 0.f && !bCollapsed)
	{
		bCollapsed = true;
		++CollapseCount;
		UE_LOG(LogTemp, Display, TEXT("UGTExposureComponent: collapsed by %s"), *HazardTag.ToString());
	}
}

FString UGTExposureComponent::Describe() const
{
	return FString::Printf(TEXT("exposure=%.0f/%.0f collapsed=%d drained=%.0f last=%s"),
		Exposure, MaxExposure, bCollapsed ? 1 : 0, TotalDrained, *LastHazardTag.ToString());
}
