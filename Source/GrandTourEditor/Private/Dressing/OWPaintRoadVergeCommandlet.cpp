#include "OWPaintRoadVergeCommandlet.h"

#include "Components/SplineComponent.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "Landscape.h"
#include "LandscapeEdit.h"
#include "LandscapeEditLayer.h"
#include "LandscapeInfo.h"
#include "LandscapeLayerInfoObject.h"
#include "LandscapeSubsystem.h"
#include "LandscapeEditTypes.h"
#include "RenderingThread.h"
#include "Editor.h"
#include "Misc/Parse.h"

DEFINE_LOG_CATEGORY_STATIC(LogOWPaintRoadVerge, Log, All);

namespace
{
	const FName VergeLayerName(TEXT("OW_RoadVerge"));
	// Road width 400 -> half 200; stamp full weight to 240cm, fall off to
	// zero at 320cm so the painted strip hugs the road without a hard
	// stair-step in the grass line.
	constexpr float VergeFullCm = 240.0f;
	constexpr float VergeZeroCm = 320.0f;
	constexpr float SplineStepCm = 50.0f;

	bool IsOWRoadActor(const AActor* Actor)
	{
		const FString ClassName = Actor->GetClass()->GetName();
		return ClassName == TEXT("BP_OWRoad_C")
			|| ClassName == TEXT("BP_OWRoad_Dusty_C")
			|| ClassName == TEXT("BP_OWRoad_Gravel_C");
	}
}

int32 UOWPaintRoadVergeCommandlet::Main(const FString& Params)
{
	// -Map= is required, with no default: the verge is painted into whichever
	// map the caller names, never a hardcoded one.
	FString MapArg;
	if (!FParse::Value(*Params, TEXT("Map="), MapArg) || MapArg.IsEmpty())
	{
		UE_LOG(LogOWPaintRoadVerge, Error,
			TEXT("missing required -Map=<long package name>, e.g. -Map=/Game/GrandTour/Test/L_OWToolkitTest"));
		return 1;
	}
	const TCHAR* VergeMapPath = *MapArg;

	UWorld* World = UEditorLoadingAndSavingUtils::LoadMap(VergeMapPath);
	if (!World)
	{
		UE_LOG(LogOWPaintRoadVerge, Error, TEXT("map load failed: %s"), VergeMapPath);
		return 1;
	}

	ALandscape* Landscape = nullptr;
	for (TActorIterator<ALandscape> It(World); It; ++It) { Landscape = *It; break; }
	if (!Landscape)
	{
		UE_LOG(LogOWPaintRoadVerge, Error, TEXT("no ALandscape in %s"), VergeMapPath);
		return 1;
	}
	ULandscapeInfo* Info = Landscape->GetLandscapeInfo();
	ULandscapeLayerInfoObject* LayerInfo = Info ? Info->GetLayerInfoByName(VergeLayerName) : nullptr;
	if (!LayerInfo)
	{
		UE_LOG(LogOWPaintRoadVerge, Error,
			TEXT("layer info '%s' not assigned on the landscape - create it once "
			     "in the Paint panel (it exists if the verge was ever hand-painted)."),
			*VergeLayerName.ToString());
		return 1;
	}

	// Gather road splines.
	TArray<USplineComponent*> Splines;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (!IsOWRoadActor(*It)) { continue; }
		if (USplineComponent* Spline = It->FindComponentByClass<USplineComponent>())
		{
			Splines.Add(Spline);
		}
	}
	if (Splines.IsEmpty())
	{
		UE_LOG(LogOWPaintRoadVerge, Display, TEXT("no BP_OWRoad* actors found - nothing to paint."));
		return 0;
	}

	// Rasterize the verge stamp in landscape-vertex space. Landscape
	// vertex (x, y) sits at local (x, y) * DrawScale; with the lab's
	// 100-scale landscape one vertex = 100cm.
	const FTransform LandXform = Landscape->GetActorTransform();
	TMap<FIntPoint, uint8> Stamp;
	int32 SampleCount = 0;
	for (USplineComponent* Spline : Splines)
	{
		const float Len = Spline->GetSplineLength();
		for (float D = 0.0f; D <= Len; D += SplineStepCm)
		{
			const FVector WorldP = Spline->GetLocationAtDistanceAlongSpline(
				D, ESplineCoordinateSpace::World);
			const FVector LocalP = LandXform.InverseTransformPosition(WorldP);
			++SampleCount;
			const int32 VertRadius = FMath::CeilToInt32(VergeZeroCm / 100.0f);
			const FIntPoint Center(FMath::RoundToInt32(LocalP.X), FMath::RoundToInt32(LocalP.Y));
			for (int32 DY = -VertRadius; DY <= VertRadius; ++DY)
			{
				for (int32 DX = -VertRadius; DX <= VertRadius; ++DX)
				{
					const FIntPoint V(Center.X + DX, Center.Y + DY);
					const float DistCm = FVector2D::Distance(
						FVector2D(V.X * 100.0f, V.Y * 100.0f),
						FVector2D(LocalP.X * 100.0f, LocalP.Y * 100.0f));
					if (DistCm >= VergeZeroCm) { continue; }
					const float Alpha = DistCm <= VergeFullCm ? 1.0f
						: 1.0f - (DistCm - VergeFullCm) / (VergeZeroCm - VergeFullCm);
					const uint8 W = static_cast<uint8>(FMath::RoundToInt32(Alpha * 255.0f));
					if (uint8* Existing = Stamp.Find(V))
					{
						*Existing = FMath::Max(*Existing, W);
					}
					else
					{
						Stamp.Add(V, W);
					}
				}
			}
		}
	}

	FIntPoint Min(MAX_int32, MAX_int32), Max(MIN_int32, MIN_int32);
	for (const auto& Pair : Stamp)
	{
		Min.X = FMath::Min(Min.X, Pair.Key.X); Min.Y = FMath::Min(Min.Y, Pair.Key.Y);
		Max.X = FMath::Max(Max.X, Pair.Key.X); Max.Y = FMath::Max(Max.Y, Pair.Key.Y);
	}
	const int32 SizeX = Max.X - Min.X + 1;
	const int32 SizeY = Max.Y - Min.Y + 1;
	UE_LOG(LogOWPaintRoadVerge, Display,
		TEXT("stamping %d verts over rect %dx%d from %d spline samples (%d roads)."),
		Stamp.Num(), SizeX, SizeY, SampleCount, Splines.Num());

	// PAID 2026-07-30, twice on this commandlet:
	// (1) The 5.8 single-layer SetAlphaData does NOT adjust sibling
	//     layers (bWeightAdjust REMOVED; the editor paint brush
	//     normalizes siblings itself before calling in) - so every
	//     other target layer must be scaled down explicitly via the
	//     multi-layer SetAlphaData.
	// (2) The composite SUMS all EDIT LAYERS: zeroing siblings on edit
	//     layer 0 alone left OW_ForestOak=255 contributed by another
	//     edit layer (read-back gate caught it, run 3). Therefore the
	//     scale-down must run on EVERY edit layer; the verge boost is
	//     applied once, on the first non-splines layer.
	const TArrayView<const FLandscapeLayer> EditLayers = Landscape->GetLayersConst();
	if (EditLayers.IsEmpty())
	{
		UE_LOG(LogOWPaintRoadVerge, Error, TEXT("landscape has no edit layers"));
		return 1;
	}
	const int32 NumLayers = Info->Layers.Num();
	const int32 VergeLayerIdx = Info->GetLayerInfoIndex(LayerInfo);
	check(VergeLayerIdx != INDEX_NONE);
	bool bVergeBoostDone = false;
	for (const FLandscapeLayer& EditLayer : EditLayers)
	{
		if (!EditLayer.EditLayer) { continue; }
		const bool bSplinesLayer = EditLayer.EditLayer->IsA<ULandscapeEditLayerSplines>();
		const bool bBoostHere = !bSplinesLayer && !bVergeBoostDone;
		UE_LOG(LogOWPaintRoadVerge, Display,
			TEXT("edit layer '%s'%s: scaling down non-verge weights%s."),
			*EditLayer.EditLayer->GetName().ToString(),
			bSplinesLayer ? TEXT(" (splines)") : TEXT(""),
			bBoostHere ? TEXT(" + writing the verge stamp") : TEXT(""));

		FScopedSetLandscapeEditingLayer Scope(Landscape, EditLayer.EditLayer->GetGuid());
		FLandscapeEditDataInterface EditInterface(Info);

		TArray<TArray<uint8>> LayerData;
		LayerData.SetNum(NumLayers);
		TSet<ULandscapeLayerInfoObject*> DirtyLayerInfos;
		for (int32 LayerIdx = 0; LayerIdx < NumLayers; ++LayerIdx)
		{
			LayerData[LayerIdx].AddZeroed(SizeX * SizeY);
			if (ULandscapeLayerInfoObject* Obj = Info->Layers[LayerIdx].LayerInfoObj)
			{
				DirtyLayerInfos.Add(Obj);
				EditInterface.GetWeightDataFast(Obj, Min.X, Min.Y, Max.X, Max.Y,
					LayerData[LayerIdx].GetData(), SizeX);
			}
		}

		TArray<uint8> Packed;
		Packed.AddZeroed(SizeX * SizeY * NumLayers);
		for (int32 Row = 0; Row < SizeY; ++Row)
		{
			for (int32 Col = 0; Col < SizeX; ++Col)
			{
				const int32 VertIdx = Row * SizeX + Col;
				const uint8* StampW = Stamp.Find(FIntPoint(Min.X + Col, Min.Y + Row));
				const uint8 S = StampW ? *StampW : 0;
				uint8* Vert = &Packed[VertIdx * NumLayers];
				for (int32 LayerIdx = 0; LayerIdx < NumLayers; ++LayerIdx)
				{
					const uint8 Old = LayerData[LayerIdx][VertIdx];
					Vert[LayerIdx] = (LayerIdx == VergeLayerIdx)
						? (bBoostHere ? FMath::Max(Old, S)
						              : static_cast<uint8>((Old * (255 - S)) / 255))
						: static_cast<uint8>((Old * (255 - S)) / 255);
				}
			}
		}
		EditInterface.SetAlphaData(DirtyLayerInfos, Min.X, Min.Y, Max.X, Max.Y,
			Packed.GetData(), SizeX * NumLayers);
		EditInterface.Flush();
		if (bBoostHere) { bVergeBoostDone = true; }
	}
	if (!bVergeBoostDone)
	{
		UE_LOG(LogOWPaintRoadVerge, Error, TEXT("no non-splines edit layer found for the verge stamp"));
		return 1;
	}
	Landscape->RequestLayersContentUpdateForceAll();

	// PAID 2026-07-30 (runs 1-4 of this commandlet): the edit-layer
	// merge is dispatched from the landscape TICK - a commandlet never
	// ticks, so BOTH "save right after the write" (run 1: zero visible
	// effect) and "call BuildAll once" (runs 2-4: returned in ~0ms, gate
	// read a STALE composite) silently skip the merge. Pump it manually:
	// ForceUpdateLayersContent + TickLayers + render-thread flush until
	// the landscape reports IsUpToDate, THEN build grass maps, THEN
	// verify the composite by read-back before claiming anything.
	int32 PumpIterations = 0;
	for (; PumpIterations < 300 && !Landscape->IsUpToDate(); ++PumpIterations)
	{
		Landscape->ForceUpdateLayersContent();
		Landscape->TickLayers(0.033f);
		FlushRenderingCommands();
	}
	UE_LOG(LogOWPaintRoadVerge, Display,
		TEXT("layer merge pump: %d iterations, IsUpToDate=%s."),
		PumpIterations, Landscape->IsUpToDate() ? TEXT("true") : TEXT("false"));
	if (!Landscape->IsUpToDate())
	{
		UE_LOG(LogOWPaintRoadVerge, Error,
			TEXT("layer merge never converged after %d pump iterations."), PumpIterations);
		return 1;
	}
	ULandscapeSubsystem* LandscapeSubsystem = World->GetSubsystem<ULandscapeSubsystem>();
	if (!LandscapeSubsystem)
	{
		UE_LOG(LogOWPaintRoadVerge, Error, TEXT("no ULandscapeSubsystem"));
		return 1;
	}
	LandscapeSubsystem->BuildAll(
		UE::Landscape::EBuildFlags::ForceRebuild | UE::Landscape::EBuildFlags::WriteFinalLog);

	// Read-back: unscoped edit-interface reads hit the final composited
	// weightmaps. Verify BOTH invariants at each spline's center line -
	// verge >= 200 AND the sum of every OTHER layer <= 30. The first
	// ship verified only the verge side and passed while OW_Meadow was
	// still 255 underneath (grass kept spawning) - never again.
	{
		FLandscapeEditDataInterface VerifyInterface(Info);
		uint8 MinVerge = 255;
		int32 MaxOtherSum = 0;
		FName WorstOther;
		int32 Checked = 0;
		for (USplineComponent* Spline : Splines)
		{
			const float Len = Spline->GetSplineLength();
			for (float D = 0.0f; D <= Len; D += FMath::Max(Len / 10.0f, SplineStepCm))
			{
				const FVector LocalP = LandXform.InverseTransformPosition(
					Spline->GetLocationAtDistanceAlongSpline(D, ESplineCoordinateSpace::World));
				const int32 VX = FMath::RoundToInt32(LocalP.X);
				const int32 VY = FMath::RoundToInt32(LocalP.Y);
				int32 OtherSum = 0;
				for (const FLandscapeInfoLayerSettings& LayerSettings : Info->Layers)
				{
					if (!LayerSettings.LayerInfoObj) { continue; }
					uint8 Weight = 0;
					VerifyInterface.GetWeightDataFast(LayerSettings.LayerInfoObj,
						VX, VY, VX, VY, &Weight, 1);
					if (LayerSettings.LayerInfoObj == LayerInfo)
					{
						MinVerge = FMath::Min(MinVerge, Weight);
					}
					else if (Weight > 0)
					{
						OtherSum += Weight;
						if (OtherSum > MaxOtherSum) { WorstOther = LayerSettings.LayerName; }
					}
				}
				MaxOtherSum = FMath::Max(MaxOtherSum, OtherSum);
				++Checked;
			}
		}
		UE_LOG(LogOWPaintRoadVerge, Display,
			TEXT("read-back: %d center samples, min verge %d, max other-layer sum %d."),
			Checked, MinVerge, MaxOtherSum);
		if (MinVerge < 200 || MaxOtherSum > 30)
		{
			UE_LOG(LogOWPaintRoadVerge, Error,
				TEXT("COMPOSITE READ-BACK FAILED (min verge %d, other-layer sum %d, "
				     "worst offender '%s') - do NOT trust this run."),
				MinVerge, MaxOtherSum, *WorstOther.ToString());
			return 1;
		}
	}

	if (!UEditorLoadingAndSavingUtils::SaveDirtyPackages(
			/*bSaveMapPackages=*/true, /*bSaveContentPackages=*/true))
	{
		UE_LOG(LogOWPaintRoadVerge, Error, TEXT("save failed"));
		return 1;
	}
	UE_LOG(LogOWPaintRoadVerge, Display,
		TEXT("OWPaintRoadVerge done: %d roads painted into '%s', map saved."),
		Splines.Num(), *VergeLayerName.ToString());
	return 0;
}
