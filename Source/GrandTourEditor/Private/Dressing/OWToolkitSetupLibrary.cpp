#include "OWToolkitSetupLibrary.h"

#include "Editor.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Landscape.h"
#include "LandscapeComponent.h"
#include "LandscapeEdit.h"
#include "LandscapeInfo.h"
#include "LandscapeLayerInfoObject.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInterface.h"
#include "VT/RuntimeVirtualTexture.h"

DEFINE_LOG_CATEGORY_STATIC(LogOWToolkitSetup, Log, All);

// Named namespace (not anonymous): identical anonymous-namespace helpers in two .cpp files of one module collide
// under unity builds.
namespace OWToolkitTest
{
	// 9.C.1 grid: 8 x 8 components of 63 quads, 1 section, scale 100, origin (0,0,0) -> 505 x 505 vertices, 0..50400 cm.
	constexpr int32 ComponentsPerSide = 8;
	constexpr int32 QuadsPerComponent = 63;
	constexpr int32 VertsPerSide = ComponentsPerSide * QuadsPerComponent + 1;
	constexpr float QuadSizeCm = 100.f;
	constexpr float ZScaleCm = 100.f;   // actor Z scale; one heightmap unit = ZScaleCm / 128 cm
	constexpr float CellCm = 16800.f;   // 3 x 3 layout cells
	constexpr int32 BlurRadius = 4;     // separable box blur, vertices

	const FVector2D ScreeHill(25200.f, 42000.f);
	const FVector2D AlpineHill(42000.f, 42000.f);

	// The 13 non-water layers. The 4 water layers are never registered.
	const TCHAR* const LayerNames[] = {
		TEXT("OW_Meadow"), TEXT("OW_MeadowLush"), TEXT("OW_MeadowDry"), TEXT("OW_Bare"), TEXT("OW_Alpine"),
		TEXT("OW_Snow"), TEXT("OW_Forest"), TEXT("OW_ForestBeech"), TEXT("OW_ForestBirch"), TEXT("OW_ForestFir"),
		TEXT("OW_ForestOak"), TEXT("OW_Scree"), TEXT("OW_RoadVerge"),
	};
	constexpr int32 LayerCount = UE_ARRAY_COUNT(LayerNames);

	float HeightCm(float X, float Y)
	{
		float H = 100.f * FMath::Sin(X / 7000.f) * FMath::Cos(Y / 9000.f) + 50.f * FMath::Sin((X + Y) / 3100.f);
		const float RScree = FVector2D::Distance(FVector2D(X, Y), ScreeHill);
		H += 7000.f * FMath::Pow(FMath::Clamp(1.f - RScree / 6000.f, 0.f, 1.f), 1.6f);
		const float RAlpine = FVector2D::Distance(FVector2D(X, Y), AlpineHill);
		const float T = FMath::Clamp(1.f - RAlpine / 7500.f, 0.f, 1.f);
		H += 4000.f * (T * T * (3.f - 2.f * T));
		return H;
	}

	// Dominant layer name per 9.C.1. Rows run with Y, columns with X; "lower half" of a cell is its smaller-Y half.
	const TCHAR* LayerAt(float X, float Y)
	{
		const int32 Col = FMath::Clamp(FMath::FloorToInt(X / CellCm), 0, 2);
		const int32 Row = FMath::Clamp(FMath::FloorToInt(Y / CellCm), 0, 2);
		const bool bLowerHalf = (Y - Row * CellCm) < CellCm * 0.5f;
		if (Row == 0)
		{
			return Col == 0 ? TEXT("OW_Meadow") : Col == 1 ? TEXT("OW_MeadowLush") : TEXT("OW_MeadowDry");
		}
		if (Row == 1)
		{
			if (Col == 0)
			{
				return TEXT("OW_Forest");
			}
			if (Col == 1)
			{
				return bLowerHalf ? TEXT("OW_ForestBeech") : TEXT("OW_ForestBirch");
			}
			return bLowerHalf ? TEXT("OW_ForestFir") : TEXT("OW_ForestOak");
		}
		if (Col == 0)
		{
			return TEXT("OW_Bare");
		}
		if (Col == 1)
		{
			return FVector2D::Distance(FVector2D(X, Y), ScreeHill) < 6200.f ? TEXT("OW_Scree") : TEXT("OW_Bare");
		}
		const float RAlpine = FVector2D::Distance(FVector2D(X, Y), AlpineHill);
		return RAlpine < 3000.f ? TEXT("OW_Snow") : RAlpine < 7800.f ? TEXT("OW_Alpine") : TEXT("OW_Bare");
	}

	int32 LayerIndex(const TCHAR* Name)
	{
		for (int32 Index = 0; Index < LayerCount; ++Index)
		{
			if (FCString::Strcmp(LayerNames[Index], Name) == 0)
			{
				return Index;
			}
		}
		return INDEX_NONE;
	}

	// One pass of a box blur along one axis; the window is clamped to the grid and averaged over the samples it holds.
	void BoxBlurAxis(const TArray<float>& In, TArray<float>& Out, bool bAlongX)
	{
		Out.SetNumUninitialized(In.Num());
		for (int32 Y = 0; Y < VertsPerSide; ++Y)
		{
			for (int32 X = 0; X < VertsPerSide; ++X)
			{
				const int32 Centre = bAlongX ? X : Y;
				const int32 Lo = FMath::Max(0, Centre - BlurRadius);
				const int32 Hi = FMath::Min(VertsPerSide - 1, Centre + BlurRadius);
				float Sum = 0.f;
				for (int32 K = Lo; K <= Hi; ++K)
				{
					Sum += bAlongX ? In[Y * VertsPerSide + K] : In[K * VertsPerSide + X];
				}
				Out[Y * VertsPerSide + X] = Sum / float(Hi - Lo + 1);
			}
		}
	}

	void Fail(const FString& Error, FString& OutReport)
	{
		OutReport = FString::Printf(TEXT("{\"ok\":false,\"error\":\"%s\"}"), *Error.Replace(TEXT("\""), TEXT("'")));
		UE_LOG(LogOWToolkitSetup, Error, TEXT("OWToolkitSetup report: %s"), *OutReport);
	}
}

float UOWToolkitSetupLibrary::SampleToolkitTestHeightCm(float X, float Y)
{
	return OWToolkitTest::HeightCm(X, Y);
}

FString UOWToolkitSetupLibrary::ToolkitTestLayerAt(float X, float Y)
{
	return OWToolkitTest::LayerAt(X, Y);
}

bool UOWToolkitSetupLibrary::BuildToolkitTestLandscape(UMaterialInterface* Material, const TArray<ULandscapeLayerInfoObject*>& LayerInfos,
	URuntimeVirtualTexture* RVT, FString& OutReport)
{
	using namespace OWToolkitTest;

	if (!Material)
	{
		Fail(TEXT("no material"), OutReport);
		return false;
	}
	if (!RVT)
	{
		Fail(TEXT("no runtime virtual texture"), OutReport);
		return false;
	}
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World)
	{
		Fail(TEXT("no editor world"), OutReport);
		return false;
	}
	if (TActorIterator<ALandscapeProxy> Existing(World); Existing)
	{
		Fail(FString::Printf(TEXT("the world already has a landscape (%s)"), *Existing->GetName()), OutReport);
		return false;
	}

	// The layer infos passed in, one per layout layer, matched by layer name. Exactly the 13 non-water layers.
	if (LayerInfos.Num() != LayerCount)
	{
		Fail(FString::Printf(TEXT("expected %d layer infos, got %d"), LayerCount, LayerInfos.Num()), OutReport);
		return false;
	}
	TArray<ULandscapeLayerInfoObject*> ByIndex;
	ByIndex.Init(nullptr, LayerCount);
	for (ULandscapeLayerInfoObject* Info : LayerInfos)
	{
		const int32 Index = Info ? LayerIndex(*Info->GetLayerName().ToString()) : INDEX_NONE;
		if (Index == INDEX_NONE || ByIndex[Index])
		{
			Fail(FString::Printf(TEXT("layer info %s is not one of the 13 layout layers, or is passed twice"), *GetNameSafe(Info)), OutReport);
			return false;
		}
		ByIndex[Index] = Info;
	}

	// Heights: uint16 = 32768 + h_cm * 128 / ZScaleCm.
	const int32 NumVerts = VertsPerSide * VertsPerSide;
	TArray<uint16> Heights;
	Heights.SetNumUninitialized(NumVerts);
	float MinHeightCm = TNumericLimits<float>::Max();
	float MaxHeightCm = TNumericLimits<float>::Lowest();
	// One-hot dominant layer per vertex.
	TArray<TArray<float>> Blend;
	Blend.SetNum(LayerCount);
	for (TArray<float>& Layer : Blend)
	{
		Layer.SetNumZeroed(NumVerts);
	}
	for (int32 Y = 0; Y < VertsPerSide; ++Y)
	{
		for (int32 X = 0; X < VertsPerSide; ++X)
		{
			const float WorldX = X * QuadSizeCm;
			const float WorldY = Y * QuadSizeCm;
			const float H = HeightCm(WorldX, WorldY);
			MinHeightCm = FMath::Min(MinHeightCm, H);
			MaxHeightCm = FMath::Max(MaxHeightCm, H);
			Heights[Y * VertsPerSide + X] = (uint16)FMath::Clamp(FMath::RoundToInt(32768.f + H * 128.f / ZScaleCm), 0, 65535);
			Blend[LayerIndex(LayerAt(WorldX, WorldY))][Y * VertsPerSide + X] = 1.f;
		}
	}
	// Separable box blur per layer, radius BlurRadius vertices.
	{
		TArray<float> Temp;
		for (TArray<float>& Layer : Blend)
		{
			BoxBlurAxis(Layer, Temp, /*bAlongX*/ true);
			BoxBlurAxis(Temp, Layer, /*bAlongX*/ false);
		}
	}
	// Normalise to 255 per vertex: round each layer, then give the rounding remainder to the heaviest layer.
	TArray<TArray<uint8>> Weights;
	Weights.SetNum(LayerCount);
	for (TArray<uint8>& Layer : Weights)
	{
		Layer.SetNumZeroed(NumVerts);
	}
	for (int32 V = 0; V < NumVerts; ++V)
	{
		float Total = 0.f;
		int32 Heaviest = 0;
		for (int32 L = 0; L < LayerCount; ++L)
		{
			Total += Blend[L][V];
			Heaviest = Blend[L][V] > Blend[Heaviest][V] ? L : Heaviest;
		}
		int32 Sum = 0;
		for (int32 L = 0; L < LayerCount; ++L)
		{
			const int32 Q = Total > 0.f ? FMath::Clamp(FMath::RoundToInt(Blend[L][V] / Total * 255.f), 0, 255) : 0;
			Weights[L][V] = (uint8)Q;
			Sum += Q;
		}
		Weights[Heaviest][V] = (uint8)FMath::Clamp(int32(Weights[Heaviest][V]) + (255 - Sum), 0, 255);
	}
	TArray<int32> Painted;
	Painted.Init(0, LayerCount);
	for (int32 L = 0; L < LayerCount; ++L)
	{
		for (const uint8 W : Weights[L])
		{
			Painted[L] += W > 0 ? 1 : 0;
		}
	}

	// The import, the same sequence as UGTVehicleSetupLibrary::BuildLegLandscape (the editor's New Landscape button).
	TArray<FLandscapeImportLayerInfo> ImportLayers;
	for (int32 L = 0; L < LayerCount; ++L)
	{
		FLandscapeImportLayerInfo Import(ByIndex[L]->GetLayerName());
		Import.LayerInfo = ByIndex[L];
		Import.LayerData = Weights[L];
		ImportLayers.Add(MoveTemp(Import));
	}
	TMap<FGuid, TArray<uint16>> HeightDataPerLayers;
	TMap<FGuid, TArray<FLandscapeImportLayerInfo>> MaterialLayerDataPerLayers;
	HeightDataPerLayers.Add(FGuid(), Heights);
	MaterialLayerDataPerLayers.Add(FGuid(), MoveTemp(ImportLayers));

	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ALandscape* Landscape = World->SpawnActor<ALandscape>(ALandscape::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, Params);
	if (!Landscape)
	{
		Fail(TEXT("the landscape did not spawn"), OutReport);
		return false;
	}
	Landscape->LandscapeMaterial = Material;
	Landscape->RuntimeVirtualTextures.Reset();
	Landscape->RuntimeVirtualTextures.Add(RVT);   // before the import, so the new components register with it
	Landscape->SetActorRelativeScale3D(FVector(QuadSizeCm, QuadSizeCm, ZScaleCm));
	Landscape->StaticLightingLOD = FMath::DivideAndRoundUp(FMath::CeilLogTwo((NumVerts) / (2048 * 2048) + 1), (uint32)2);
	Landscape->Import(FGuid::NewGuid(), 0, 0, VertsPerSide - 1, VertsPerSide - 1, /*NumSubsections*/ 1, QuadsPerComponent,
		HeightDataPerLayers, TEXT(""), MaterialLayerDataPerLayers, ELandscapeImportAlphamapType::Additive, TArrayView<const FLandscapeLayer>());
	ULandscapeInfo* LandscapeInfo = Landscape->GetLandscapeInfo();
	if (!LandscapeInfo)
	{
		Fail(TEXT("no landscape info after the import"), OutReport);
		return false;
	}
	Landscape->SetActorLabel(TEXT("Landscape_OWToolkitTest"));
	LandscapeInfo->UpdateLayerInfoMap(Landscape);
	for (ULandscapeLayerInfoObject* Info : ByIndex)
	{
		Landscape->AddTargetLayer(Info->GetLayerName(), FLandscapeTargetLayerSettings(Info));
		const int32 LayerInfoIndex = LandscapeInfo->GetLayerInfoIndex(Info->GetLayerName());
		if (LayerInfoIndex != INDEX_NONE)
		{
			LandscapeInfo->Layers[LayerInfoIndex].LayerInfoObj = Info;
		}
	}
	// 5.8 always has edit layers and their GPU merge never runs under -NullRHI: write the FINAL weightmaps on the CPU
	// (an invalid guid = the final data), without re-normalising (every vertex already sums to 255). All-zero layers
	// (OW_RoadVerge until the road tools paint it) are skipped so no component allocates an empty channel.
	{
		FLandscapeEditDataInterface FinalEdit(LandscapeInfo, FGuid(), /*bInUploadTextureChangesToGPU*/ false);
		for (int32 L = 0; L < LayerCount; ++L)
		{
			if (Painted[L] == 0)
			{
				continue;
			}
			FinalEdit.SetAlphaData(ByIndex[L], 0, 0, VertsPerSide - 1, VertsPerSide - 1, Weights[L].GetData(), /*Stride*/ 0,
				ELandscapeLayerPaintingRestriction::None);   // 5.7+: no weight adjust (the removed flags were false anyway)
		}
		FinalEdit.Flush();
	}
	// The edit interface only patches texture regions; the weightmap textures still need PostEditChange to build their
	// platform data, or the game loads them with no mips.
	int32 WeightmapTextureCount = 0;
	{
		TSet<UTexture2D*> WeightmapTextures;
		for (ULandscapeComponent* Component : Landscape->LandscapeComponents)
		{
			for (UTexture2D* Texture : Component->GetWeightmapTextures())
			{
				if (Texture)
				{
					WeightmapTextures.Add(Texture);
				}
			}
		}
		for (UTexture2D* Texture : WeightmapTextures)
		{
			Texture->PostEditChange();
		}
		WeightmapTextureCount = WeightmapTextures.Num();
	}
	// A headless commandlet never ticks, so the per-component material instances must be built here.
	Landscape->UpdateAllComponentMaterialInstances(/*bInInvalidateCombinationMaterials*/ true);
	if (ULevel* Level = Landscape->GetLevel())
	{
		Level->MarkPackageDirty();
	}

	FString PaintedJson;
	for (int32 L = 0; L < LayerCount; ++L)
	{
		PaintedJson += FString::Printf(TEXT("%s\"%s\":%d"), L ? TEXT(",") : TEXT(""), LayerNames[L], Painted[L]);
	}
	OutReport = FString::Printf(TEXT("{\"ok\":true,\"verts\":%d,\"vertsPerSide\":%d,\"components\":%d,\"weightmapTextures\":%d,\"heightMinCm\":%.1f,\"heightMaxCm\":%.1f,\"painted\":{%s}}"),
		NumVerts, VertsPerSide, Landscape->LandscapeComponents.Num(), WeightmapTextureCount, MinHeightCm, MaxHeightCm, *PaintedJson);
	UE_LOG(LogOWToolkitSetup, Display, TEXT("OWToolkitSetup report: %s"), *OutReport);
	return true;
}
