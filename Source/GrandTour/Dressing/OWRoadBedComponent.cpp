#include "Dressing/OWRoadBedComponent.h"

#if WITH_EDITOR
#include "Components/SplineComponent.h"
#include "EngineUtils.h"
#include "Framework/Notifications/NotificationManager.h"
#include "Landscape.h"
#include "LandscapeEditLayer.h"
#include "LandscapeLayerInfoObject.h"
#include "LandscapeProxy.h"
#include "Widgets/Notifications/SNotificationList.h"
#endif

#if WITH_EDITOR

// Declared inside the guard so shipping builds carry no unused static.
// NAMED namespace (not anonymous) on purpose: identical anonymous-
// namespace helpers in two .cpp files of one module collide under unity
// builds - the documented ODR trap.
DEFINE_LOG_CATEGORY_STATIC(LogOWRoadBed, Log, All);

namespace OWRoadBedLocal
{
	// The whole point of this button is that failures are VISIBLE: the
	// script it replaces returned "ok" while painting nothing.
	void Report(const FString& Message, bool bSuccess)
	{
		if (bSuccess)
		{
			UE_LOG(LogOWRoadBed, Display, TEXT("%s"), *Message);
		}
		else
		{
			UE_LOG(LogOWRoadBed, Error, TEXT("%s"), *Message);
		}

		FNotificationInfo Info(FText::FromString(Message));
		Info.ExpireDuration = bSuccess ? 5.0f : 12.0f;
		Info.bFireAndForget = true;
		const TSharedPtr<SNotificationItem> Item =
			FSlateNotificationManager::Get().AddNotification(Info);
		if (Item.IsValid())
		{
			Item->SetCompletionState(bSuccess ? SNotificationItem::CS_Success
			                                  : SNotificationItem::CS_Fail);
		}
	}
}

void UOWRoadBedComponent::ApplyBedAndVerge()
{
	AActor* Owner = GetOwner();
	if (!Owner || !Owner->GetWorld())
	{
		return;
	}
	const FString RoadName = Owner->GetActorNameOrLabel();

	USplineComponent* Spline = Owner->FindComponentByClass<USplineComponent>();
	if (!Spline)
	{
		OWRoadBedLocal::Report(FString::Printf(
			TEXT("OW Road Bed: '%s' has no SplineComponent - nothing to apply."),
			*RoadName), false);
		return;
	}

	ALandscape* Landscape = nullptr;
	for (TActorIterator<ALandscape> It(Owner->GetWorld()); It; ++It)
	{
		Landscape = *It;
		break;
	}
	if (!Landscape)
	{
		OWRoadBedLocal::Report(TEXT("OW Road Bed: no Landscape actor in this "
			"level (on World Partition maps, load the region first)."), false);
		return;
	}

	// Edit layer: a name this landscape does not have aborts the ENTIRE
	// apply, heights included (LandscapeBlueprintSupport.cpp:28-31).
	const TArray<ULandscapeEditLayerBase*> EditLayers = Landscape->GetEditLayers();
	TArray<FString> EditLayerNames;
	for (const ULandscapeEditLayerBase* Layer : EditLayers)
	{
		if (Layer)
		{
			EditLayerNames.Add(Layer->GetName().ToString());
		}
	}
	FName ResolvedEditLayer = EditLayerName;
	if (ResolvedEditLayer.IsNone())
	{
		if (EditLayers.Num() > 0 && EditLayers[0])
		{
			ResolvedEditLayer = EditLayers[0]->GetName();
		}
		else
		{
			OWRoadBedLocal::Report(FString::Printf(
				TEXT("OW Road Bed: landscape '%s' reports NO edit layers, so the "
				     "engine cannot apply a spline to it. Enable Edit Layers on "
				     "the landscape, then retry."),
				*Landscape->GetActorNameOrLabel()), false);
			return;
		}
	}
	else if (!EditLayerNames.Contains(ResolvedEditLayer.ToString()))
	{
		OWRoadBedLocal::Report(FString::Printf(
			TEXT("OW Road Bed: edit layer '%s' does not exist on this landscape. "
			     "Available: [%s]. Clear Edit Layer Name to auto-pick the first."),
			*ResolvedEditLayer.ToString(), *FString::Join(EditLayerNames, TEXT(", "))),
			false);
		return;
	}

	// Verge layer info: MUST be the object this landscape is configured
	// with - every map owns its own copy (LandscapeProxy.h ~L1036).
	ULandscapeLayerInfoObject* VergeInfo = nullptr;
	TArray<FString> TargetLayerNames;
	for (const TPair<FName, FLandscapeTargetLayerSettings>& Pair : Landscape->GetTargetLayers())
	{
		TargetLayerNames.Add(Pair.Key.ToString());
		if (Pair.Key == VergeLayerName)
		{
			VergeInfo = Pair.Value.LayerInfoObj;
		}
	}
	if (!VergeInfo)
	{
		OWRoadBedLocal::Report(FString::Printf(
			TEXT("OW Road Bed: layer '%s' has no Layer Info on THIS map's "
			     "landscape - create it in the Paint panel (Weight-Blended). "
			     "Target layers present: [%s]."),
			*VergeLayerName.ToString(), *FString::Join(TargetLayerNames, TEXT(", "))),
			false);
		return;
	}

	// Pass 1: carve the bed to the spline (wide blended shoulder).
	if (bDeformBed)
	{
		Landscape->EditorApplySpline(Spline, HalfWidth, HalfWidth,
			DeformSideFalloff, DeformSideFalloff, /*StartRoll=*/0.0f, /*EndRoll=*/0.0f,
			NumSubdivisions, /*bRaiseHeights=*/true, /*bLowerHeights=*/true,
			/*PaintLayer=*/nullptr, ResolvedEditLayer);
	}

	// Pass 2: paint the verge kill-switch at exactly road width.
	Landscape->EditorApplySpline(Spline, HalfWidth, HalfWidth,
		PaintSideFalloff, PaintSideFalloff, /*StartRoll=*/0.0f, /*EndRoll=*/0.0f,
		NumSubdivisions, /*bRaiseHeights=*/false, /*bLowerHeights=*/false,
		VergeInfo, ResolvedEditLayer);

	OWRoadBedLocal::Report(FString::Printf(
		TEXT("OW Road Bed: applied to '%s' (%s, verge '%s' -> %s, edit layer '%s'). "
		     "Re-Generate the PCG volumes - the ground moved."),
		*RoadName,
		bDeformBed ? TEXT("bed carved + verge painted") : TEXT("verge painted only"),
		*VergeLayerName.ToString(), *VergeInfo->GetName(),
		*ResolvedEditLayer.ToString()), true);
}

#endif // WITH_EDITOR
