#include "Look/GTLookSubsystem.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/MeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/CollisionProfile.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "ProceduralMeshComponent.h"
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTTerrainDressing.h"
#include "Terrain/GTWaterSheet.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTDashboardComponent.h"
#include "Weather/GTWeatherStateDefinition.h"
#include "Weather/GTWeatherSubsystem.h"

static TAutoConsoleVariable<int32> CVarLookPost(
	TEXT("gt.Look.Post"), 2,
	TEXT("Look stage L2: 0 the layer off (no volume, every sun's own light source angle); 1 on (the band pass, the fixed ")
	TEXT("exposure, no bloom/flare/grain/vignette/local exposure, the hard sun); 2 fixed exposure without screen filters (default)."));

static TAutoConsoleVariable<int32> CVarLookKuwahara(
	TEXT("gt.Look.Kuwahara"), 0,
	TEXT("Look stage L2: 1 runs the anisotropic Kuwahara filter after the band pass (off by default until its cost is known)."));

static TAutoConsoleVariable<float> CVarLookWarpScale(
	TEXT("gt.Look.WarpScale"), 0.f,
	TEXT("Look stage L2: multiplies the weather set's stroke-warp amplitude (0 takes the warp off; the follow-up's probe)."));

static TAutoConsoleVariable<int32> CVarLookSurface(
	TEXT("gt.Look.Surface"), 1,
	TEXT("Look stage L6: 1 the runtime painterly surface on every mesh slot wearing M_GT_Painterly (the terrain dressing); ")
	TEXT("0 the plain graph it copies (M_GT_Environment's), pixel for pixel. Set on a dynamic instance of each slot."));

static TAutoConsoleVariable<int32> CVarLookSky(
	TEXT("gt.Look.Sky"), 1,
	TEXT("Look stage L3: 1 the painted sky dome (M_GT_Sky: translucent, drawn over the atmosphere, kept out of every lighting ")
	TEXT("path); 0 hidden, the engine's sky as before."));

static TAutoConsoleVariable<int32> CVarLookHaze(
	TEXT("gt.Look.Haze"), 1,
	TEXT("Look stage L3: 1 the distance haze in M_GT_PostLook (saturation down and a cool lit tint mixed in from 60 m to 600 m); ")
	TEXT("0 off, the L2 output pixel for pixel."));

static TAutoConsoleVariable<int32> CVarLookFoliage(
	TEXT("gt.Look.Foliage"), 1,
	TEXT("Look stage L3: 1 the terrain dressing's foliage cards (PLACEHOLDER planes) shown; 0 hidden: no draw, no shadow."));

static TAutoConsoleVariable<int32> CVarLookDressing(
	TEXT("gt.Look.Dressing"), 1,
	TEXT("Leg dressing LD3: 1 the biome dressing shown (actors tagged OWBiome.* or GTBiome.*, the PCG volumes that own the ")
	TEXT("instances) and grass.Enable 1; 0 those actors hidden with their collision off, and grass.Enable 0. The vegetation ")
	TEXT("subsystem (LD5) reads it too and stops pushing the soft vegetation while it is 0."));

static TAutoConsoleVariable<FString> CVarLookWeather(
	TEXT("gt.Look.Weather"), TEXT(""),
	TEXT("Look stage L3: a weather state id (Clear, Overcast, Rain, Storm, Snow) held, set instantly, while this names it - for ")
	TEXT("pictures and the owner's gate; empty leaves the weather its own. The states' numbers are not touched."));

static TAutoConsoleVariable<int32> CVarLookDebug(
	TEXT("gt.Look.Debug"), 0,
	TEXT("Look stage L2 debug views: 1 BaseColor, 2 the light amount in eight colour classes, 3 the exclusions, 4 the plain ")
	TEXT("picture with the exposure left automatic (the band pass needs a fixed one: the histogram sees its output), 5 as 2 in linear bins of 0.1, 6 flags at the warped lookup (red no BaseColor, green sky, blue lit scene); 2-6 draw the exposure bars and the calibration patches."));

namespace
{
	const TCHAR* LookInstancePath = TEXT("/Game/GrandTour/Materials/Look/MI_GT_PostLook.MI_GT_PostLook");
	const TCHAR* KuwaharaInstancePath = TEXT("/Game/GrandTour/Materials/Look/MI_GT_PostKuwahara.MI_GT_PostKuwahara");
	const TCHAR* PainterlyPath = TEXT("/Game/GrandTour/Materials/M_GT_Painterly.M_GT_Painterly");
	const FName SurfaceParam(TEXT("Surface"));
	const TCHAR* SkyInstancePath = TEXT("/Game/GrandTour/Materials/Look/MI_GT_Sky.MI_GT_Sky");
	const TCHAR* SkySpherePath = TEXT("/Engine/BasicShapes/Sphere.Sphere");

	FGTLookSet MakeSet(float Bands, float T1, float T2, float Soft, float MidMix, float InBand, const FLinearColor& Lit, const FLinearColor& Shadow,
	                   const FLinearColor& Lift, float WarpPx, float EV100)
	{
		FGTLookSet S;
		S.Bands = Bands;
		S.T1 = T1;
		S.T2 = T2;
		S.Soft = Soft;
		S.MidMix = MidMix;
		S.InBand = InBand;
		S.LitTint = Lit;
		S.ShadowTint = Shadow;
		S.Lift = Lift;
		S.WarpPx = WarpPx;
		S.EV100 = EV100;
		return S;
	}

	bool TagStencil(UPrimitiveComponent* Prim, int32 Value)
	{
		if (!Prim)
		{
			return false;
		}
		if (!Prim->bRenderCustomDepth || Prim->CustomDepthStencilValue != Value)
		{
			Prim->SetRenderCustomDepth(true);
			Prim->SetCustomDepthStencilValue(Value);
		}
		return true;
	}
}

FGTLookSet FGTLookSet::Lerp(const FGTLookSet& A, const FGTLookSet& B, float Alpha)
{
	FGTLookSet S;
	S.Bands = FMath::Lerp(A.Bands, B.Bands, Alpha);
	S.T1 = FMath::Lerp(A.T1, B.T1, Alpha);
	S.T2 = FMath::Lerp(A.T2, B.T2, Alpha);
	S.Soft = FMath::Lerp(A.Soft, B.Soft, Alpha);
	S.MidMix = FMath::Lerp(A.MidMix, B.MidMix, Alpha);
	S.InBand = FMath::Lerp(A.InBand, B.InBand, Alpha);
	S.LitTint = FMath::Lerp(A.LitTint, B.LitTint, Alpha);
	S.ShadowTint = FMath::Lerp(A.ShadowTint, B.ShadowTint, Alpha);
	S.Lift = FMath::Lerp(A.Lift, B.Lift, Alpha);
	S.WarpPx = FMath::Lerp(A.WarpPx, B.WarpPx, Alpha);
	S.EV100 = FMath::Lerp(A.EV100, B.EV100, Alpha);
	return S;
}

FString FGTLookSet::Describe() const
{
	return FString::Printf(TEXT("bands %.2f T1 %.2f T2 %.2f soft %.2f mid %.2f inband %.2f lit (%.2f %.2f %.2f) shadow (%.2f %.2f %.2f) lift (%.3f %.3f %.3f) warp %.2f px EV100 %.2f"),
		Bands, T1, T2, Soft, MidMix, InBand, LitTint.R, LitTint.G, LitTint.B, ShadowTint.R, ShadowTint.G, ShadowTint.B, Lift.R, Lift.G, Lift.B, WarpPx, EV100);
}

FGTLookSet UGTLookSubsystem::DefaultSet(FName StateId)
{
	// Every number PROPOSED, UNMEASURED against the owner's look (VEHICLE_BUILD_SYSTEM 56). Clear: three tones, a short
	// terminator, the cool shadow tint of LOOK_PLAN 1 and a warm lit tint. Overcast, Rain and Storm: two tones with a
	// wide, shallow terminator and tints close together (low contrast), darker with the weather. Snow: three tones, a
	// bluer shadow, unchecked. EV100: Clear 0.25 keeps the sunlit orange of the painted car copy under clipping; the
	// others move with log2 of the weather's SunScale (0.6, 0.4, 0.2, 0.5) so the lit band keeps its brightness.
	static const FGTLookSet Clear = MakeSet(3.f, 0.20f, 0.45f, 0.08f, 0.60f, 0.25f, FLinearColor(1.00f, 0.96f, 0.88f), FLinearColor(0.55f, 0.62f, 0.80f), FLinearColor(0.012f, 0.014f, 0.020f), 1.5f, 0.25f);
	static const FGTLookSet Overcast = MakeSet(2.f, 0.30f, 0.90f, 0.35f, 0.50f, 0.25f, FLinearColor(0.92f, 0.93f, 0.95f), FLinearColor(0.72f, 0.76f, 0.84f), FLinearColor(0.020f, 0.021f, 0.024f), 1.5f, -0.45f);
	static const FGTLookSet Rain = MakeSet(2.f, 0.30f, 0.90f, 0.35f, 0.50f, 0.25f, FLinearColor(0.84f, 0.86f, 0.90f), FLinearColor(0.66f, 0.70f, 0.79f), FLinearColor(0.018f, 0.020f, 0.024f), 1.5f, -1.05f);
	static const FGTLookSet Storm = MakeSet(2.f, 0.30f, 0.90f, 0.40f, 0.50f, 0.25f, FLinearColor(0.74f, 0.77f, 0.82f), FLinearColor(0.58f, 0.62f, 0.72f), FLinearColor(0.016f, 0.018f, 0.022f), 1.5f, -2.0f);
	static const FGTLookSet Snow = MakeSet(3.f, 0.20f, 0.45f, 0.15f, 0.60f, 0.25f, FLinearColor(1.00f, 1.00f, 1.02f), FLinearColor(0.62f, 0.70f, 0.92f), FLinearColor(0.014f, 0.016f, 0.024f), 1.5f, -0.25f);
	if (StateId == TEXT("Overcast")) { return Overcast; }
	if (StateId == TEXT("Rain")) { return Rain; }
	if (StateId == TEXT("Storm")) { return Storm; }
	if (StateId == TEXT("Snow")) { return Snow; }
	return Clear;
}

bool UGTLookSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGTLookSubsystem::Initialize(FSubsystemCollectionBase& InCollection)
{
	Super::Initialize(InCollection);
	int32 Value = 0;
	if (FParse::Value(FCommandLine::Get(), TEXT("GTLook="), Value))
	{
		CVarLookPost->Set(Value, ECVF_SetByCommandline);
	}
	if (FParse::Value(FCommandLine::Get(), TEXT("GTLookKuwahara="), Value))
	{
		CVarLookKuwahara->Set(Value, ECVF_SetByCommandline);
	}
	float WarpScale = 1.f;
	if (FParse::Value(FCommandLine::Get(), TEXT("GTLookWarp="), WarpScale))
	{
		CVarLookWarpScale->Set(WarpScale, ECVF_SetByCommandline);
	}
	if (FParse::Value(FCommandLine::Get(), TEXT("GTLookDebug="), Value))
	{
		CVarLookDebug->Set(Value, ECVF_SetByCommandline);
	}
	if (FParse::Value(FCommandLine::Get(), TEXT("GTLookSurface="), Value))
	{
		CVarLookSurface->Set(Value, ECVF_SetByCommandline);
	}
	if (FParse::Value(FCommandLine::Get(), TEXT("GTLookSky="), Value))
	{
		CVarLookSky->Set(Value, ECVF_SetByCommandline);
	}
	if (FParse::Value(FCommandLine::Get(), TEXT("GTLookHaze="), Value))
	{
		CVarLookHaze->Set(Value, ECVF_SetByCommandline);
	}
	if (FParse::Value(FCommandLine::Get(), TEXT("GTLookFoliage="), Value))
	{
		CVarLookFoliage->Set(Value, ECVF_SetByCommandline);
	}
	if (FParse::Value(FCommandLine::Get(), TEXT("GTLookDressing="), Value))
	{
		CVarLookDressing->Set(Value, ECVF_SetByCommandline);
	}
	FString WeatherId;
	if (FParse::Value(FCommandLine::Get(), TEXT("GTWeather="), WeatherId))
	{
		CVarLookWeather->Set(*WeatherId, ECVF_SetByCommandline);
	}
	Current = DefaultSet(TEXT("Clear"));
	BlendFrom = Current;
	BlendTo = Current;
}

void UGTLookSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	bBegun = true;
	EnsureVolume();
	TagExclusions();
	WrapSurfaces();
	EnsureSky();
	ApplyFoliage(CVarLookFoliage.GetValueOnGameThread() != 0 ? 1 : 0);
	ApplyDressing(CVarLookDressing.GetValueOnGameThread() != 0 ? 1 : 0);
	TagTimer = 1.f;
}

void UGTLookSubsystem::WrapSurfaces()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	if (!PainterlyBase && !bPainterlyTried)
	{
		// Loaded here, never in a constructor (a rooted material breaks the setup scripts that rebuild it).
		bPainterlyTried = true;
		PainterlyBase = LoadObject<UMaterial>(nullptr, PainterlyPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
		UE_LOG(LogTemp, Display, TEXT("GTLOOK surface: %s %s"), PainterlyPath, PainterlyBase ? TEXT("loaded") : TEXT("missing (Art/setup_look_l6.bat): gt.Look.Surface has nothing to switch"));
	}
	if (!PainterlyBase)
	{
		return;
	}
	const float Value = CVarLookSurface.GetValueOnGameThread() != 0 ? 1.f : 0.f;
	int32 Wrapped = 0;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		TInlineComponentArray<UMeshComponent*> Meshes(*It);
		for (UMeshComponent* Mesh : Meshes)
		{
			const int32 Slots = Mesh ? Mesh->GetNumMaterials() : 0;
			for (int32 Slot = 0; Slot < Slots; ++Slot)
			{
				UMaterialInterface* Material = Mesh->GetMaterial(Slot);
				if (!Material || Material->IsA<UMaterialInstanceDynamic>() || Material->GetBaseMaterial() != PainterlyBase)
				{
					continue;
				}
				UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(Material, Mesh);
				MID->SetScalarParameterValue(SurfaceParam, Value);
				Mesh->SetMaterial(Slot, MID);
				SurfaceMIDs.Add(MID);
				++Wrapped;
			}
		}
	}
	if (Wrapped > 0)
	{
		SurfaceMIDs.RemoveAll([](const TWeakObjectPtr<UMaterialInstanceDynamic>& Entry) { return !Entry.IsValid(); });
		UE_LOG(LogTemp, Display, TEXT("GTLOOK surface: %d mesh slot(s) on M_GT_Painterly given a dynamic instance (%d in all), Surface %.0f"), Wrapped, SurfaceMIDs.Num(), Value);
	}
}

void UGTLookSubsystem::ApplySurface(int32 Surface)
{
	int32 Set = 0;
	for (const TWeakObjectPtr<UMaterialInstanceDynamic>& Entry : SurfaceMIDs)
	{
		if (UMaterialInstanceDynamic* MID = Entry.Get())
		{
			MID->SetScalarParameterValue(SurfaceParam, Surface != 0 ? 1.f : 0.f);
			++Set;
		}
	}
	AppliedSurface = Surface;
	UE_LOG(LogTemp, Display, TEXT("GTLOOK gt.Look.Surface %d on %d painterly slot(s)"), Surface, Set);
}

void UGTLookSubsystem::EnsureVolume()
{
	UWorld* World = GetWorld();
	if (Volume || !World)
	{
		return;
	}
	FActorSpawnParameters Params;
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Volume = World->SpawnActor<APostProcessVolume>(APostProcessVolume::StaticClass(), FTransform::Identity, Params);
	if (Volume)
	{
		Volume->bUnbound = true;
		Volume->Priority = 100.f;
		Volume->BlendWeight = 1.f;
		FPostProcessSettings& S = Volume->Settings;
		S.bOverride_BloomIntensity = true;
		S.BloomIntensity = 0.f;
		S.bOverride_LensFlareIntensity = true;
		S.LensFlareIntensity = 0.f;
		S.bOverride_FilmGrainIntensity = true;
		S.FilmGrainIntensity = 0.f;
		S.bOverride_VignetteIntensity = true;
		S.VignetteIntensity = 0.f;
		// Local exposure off (1 = no local contrast change): it would re-shade the flat bands after the pass.
		S.bOverride_LocalExposureHighlightContrastScale = true;
		S.LocalExposureHighlightContrastScale = 1.f;
		S.bOverride_LocalExposureShadowContrastScale = true;
		S.LocalExposureShadowContrastScale = 1.f;
	}
	UMaterialInterface* LookMaterial = LoadObject<UMaterialInterface>(nullptr, LookInstancePath);
	UMaterialInterface* KuwaharaMaterial = LoadObject<UMaterialInterface>(nullptr, KuwaharaInstancePath);
	LookMID = LookMaterial ? UMaterialInstanceDynamic::Create(LookMaterial, this) : nullptr;
	KuwaharaMID = KuwaharaMaterial ? UMaterialInstanceDynamic::Create(KuwaharaMaterial, this) : nullptr;
	if (KuwaharaMID)
	{
		KuwaharaMID->SetScalarParameterValue(TEXT("RadiusPx"), KuwaharaRadiusPx);
		KuwaharaMID->SetScalarParameterValue(TEXT("Q"), KuwaharaQ);
		KuwaharaMID->SetScalarParameterValue(TEXT("Alpha"), KuwaharaAlpha);
		KuwaharaMID->SetScalarParameterValue(TEXT("Zeta"), KuwaharaZeta);
	}
	UE_LOG(LogTemp, Display, TEXT("GTLOOK volume %s (unbound, priority 100); %s %s; %s %s"),
		Volume ? TEXT("spawned") : TEXT("FAILED"), LookInstancePath, LookMID ? TEXT("loaded") : TEXT("MISSING (run Art/setup_look_l2.bat)"),
		KuwaharaInstancePath, KuwaharaMID ? TEXT("loaded") : TEXT("MISSING"));
}

void UGTLookSubsystem::SetSunAngles(bool bHard)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	if (bHard && SunAngles.Num() == 0)
	{
		for (TActorIterator<ADirectionalLight> It(World); It; ++It)
		{
			if (UDirectionalLightComponent* Light = Cast<UDirectionalLightComponent>(It->GetLightComponent()))
			{
				SunAngles.Emplace(Light, Light->LightSourceAngle);
			}
		}
	}
	for (const TPair<TWeakObjectPtr<UDirectionalLightComponent>, float>& Entry : SunAngles)
	{
		if (UDirectionalLightComponent* Light = Entry.Key.Get())
		{
			Light->SetLightSourceAngle(bHard ? SunAngleDeg : Entry.Value);
		}
	}
	bSunHard = bHard;
}

void UGTLookSubsystem::ApplyMode(int32 Mode, int32 Kuwahara, int32 Debug)
{
	EnsureVolume();
	if (Volume)
	{
		Volume->bEnabled = Mode != 0;
		TArray<FWeightedBlendable>& Blendables = Volume->Settings.WeightedBlendables.Array;
		Blendables.Reset();
		if (Mode == 1 && LookMID)
		{
			Blendables.Add(FWeightedBlendable(1.f, LookMID));
		}
		if (Mode == 1 && Kuwahara != 0 && KuwaharaMID)
		{
			Blendables.Add(FWeightedBlendable(1.f, KuwaharaMID));
		}
	}
	// Only the optional banded look requires a hard sun. Clean mode preserves authored softness.
	SetSunAngles(Mode == 1);
	AppliedMode = Mode;
	AppliedKuwahara = Kuwahara;
	AppliedDebug = Debug;
	UE_LOG(LogTemp, Display, TEXT("GTLOOK applied: %s"), *Describe());
}

void UGTLookSubsystem::ApplyExposure(const FGTLookSet& Set, int32 Mode, int32 Debug)
{
	if (!Volume)
	{
		return;
	}
	FPostProcessSettings& S = Volume->Settings;
	const bool bFixed = Mode != 0 && Debug != 4;
	S.bOverride_AutoExposureMethod = bFixed;
	S.AutoExposureMethod = EAutoExposureMethod::AEM_Histogram;
	S.bOverride_AutoExposureMinBrightness = bFixed;
	S.AutoExposureMinBrightness = Set.EV100;
	S.bOverride_AutoExposureMaxBrightness = bFixed;
	S.AutoExposureMaxBrightness = Set.EV100;
	S.bOverride_AutoExposureBias = bFixed;
	S.AutoExposureBias = 0.f;
}

void UGTLookSubsystem::PushSet(const FGTLookSet& Set, int32 Debug)
{
	if (!LookMID)
	{
		return;
	}
	float SunLux = 0.f;
	for (const TPair<TWeakObjectPtr<UDirectionalLightComponent>, float>& Entry : SunAngles)
	{
		if (const UDirectionalLightComponent* Light = Entry.Key.Get())
		{
			SunLux = FMath::Max(SunLux, Light->Intensity);
		}
	}
	LastSunLux = SunLux;
	LookMID->SetScalarParameterValue(TEXT("Bands"), Set.Bands);
	LookMID->SetScalarParameterValue(TEXT("T1"), Set.T1);
	LookMID->SetScalarParameterValue(TEXT("T2"), Set.T2);
	LookMID->SetScalarParameterValue(TEXT("Soft"), Set.Soft);
	LookMID->SetScalarParameterValue(TEXT("MidMix"), Set.MidMix);
	LookMID->SetScalarParameterValue(TEXT("InBand"), Set.InBand);
	LookMID->SetVectorParameterValue(TEXT("LitTint"), Set.LitTint);
	LookMID->SetVectorParameterValue(TEXT("ShadowTint"), Set.ShadowTint);
	LookMID->SetVectorParameterValue(TEXT("Lift"), Set.Lift);
	LookMID->SetScalarParameterValue(TEXT("WarpPx"), Set.WarpPx * FMath::Max(0.f, CVarLookWarpScale.GetValueOnGameThread()));
	LookMID->SetScalarParameterValue(TEXT("StrokeLenPx"), StrokeLenPx);
	LookMID->SetScalarParameterValue(TEXT("StrokeWidthPx"), StrokeWidthPx);
	LookMID->SetScalarParameterValue(TEXT("SunRef"), SunLux > 0.f ? SunLux / UE_PI : 1.f);
	LookMID->SetScalarParameterValue(TEXT("BaseGuard"), BaseGuard);
	LookMID->SetScalarParameterValue(TEXT("LitX"), LitX);
	LookMID->SetScalarParameterValue(TEXT("SkyDepthCm"), SkyDepthCm);
	LookMID->SetScalarParameterValue(TEXT("DebugMode"), static_cast<float>(Debug));
	// Look stage L3: the haze (M_GT_PostLook skips it on 0, the L2 output pixel for pixel).
	LookMID->SetScalarParameterValue(TEXT("Haze"), CVarLookHaze.GetValueOnGameThread() != 0 ? 1.f : 0.f);
	LookMID->SetScalarParameterValue(TEXT("HazeStartCm"), HazeStartCm);
	LookMID->SetScalarParameterValue(TEXT("HazeEndCm"), HazeEndCm);
	LookMID->SetScalarParameterValue(TEXT("HazeSat"), HazeSat);
	LookMID->SetScalarParameterValue(TEXT("HazeMix"), HazeMix);
	LookMID->SetVectorParameterValue(TEXT("HazeTint"), HazeTint);
}

void UGTLookSubsystem::TagExclusions()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	int32 Water = 0;
	int32 Dash = 0;
	for (TActorIterator<AGTWaterSheet> It(World); It; ++It)
	{
		TInlineComponentArray<UPrimitiveComponent*> Prims(*It);
		for (UPrimitiveComponent* Prim : Prims)
		{
			Water += TagStencil(Prim, 1) ? 1 : 0;
		}
	}
	for (TActorIterator<AGTMudPatch> It(World); It; ++It)
	{
		TInlineComponentArray<UProceduralMeshComponent*> Meshes(*It);
		for (UProceduralMeshComponent* Mesh : Meshes)
		{
			if (Mesh && Mesh->GetFName() == TEXT("WaterMesh"))
			{
				Water += TagStencil(Mesh, 1) ? 1 : 0;
			}
		}
	}
	for (TActorIterator<AGTCarPawn> It(World); It; ++It)
	{
		if (UGTDashboardComponent* Dashboard = It->GetDashboard())
		{
			TArray<USceneComponent*> Children;
			Dashboard->GetChildrenComponents(/*bIncludeAllDescendants*/ true, Children);
			for (USceneComponent* Child : Children)
			{
				Dash += TagStencil(Cast<UPrimitiveComponent>(Child), 2) ? 1 : 0;
			}
		}
	}
	if (Water != StencilWater || Dash != StencilDash)
	{
		StencilWater = Water;
		StencilDash = Dash;
		UE_LOG(LogTemp, Display, TEXT("GTLOOK stencil: %d water primitive(s) at 1 (water sheets and rut water), %d dashboard primitive(s) at 2"), Water, Dash);
	}
}

void UGTLookSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	UWorld* World = GetWorld();
	if (!bBegun || !World)
	{
		return;
	}
	const int32 Mode = FMath::Clamp(CVarLookPost.GetValueOnGameThread(), 0, 2);
	const int32 Kuwahara = CVarLookKuwahara.GetValueOnGameThread() != 0 ? 1 : 0;
	const int32 Debug = FMath::Clamp(CVarLookDebug.GetValueOnGameThread(), 0, 6);
	if (Mode != AppliedMode || Kuwahara != AppliedKuwahara || Debug != AppliedDebug)
	{
		ApplyMode(Mode, Kuwahara, Debug);
	}

	// The weather sets blend the way the weather's own states do: the target state, its blend alpha through the same
	// smoothstep, then the fronts' storm pressure towards Storm on top.
	FName Id = TEXT("Clear");
	float Alpha = 1.f;
	float Pressure = 0.f;
	if (UGTWeatherSubsystem* Weather = World->GetSubsystem<UGTWeatherSubsystem>())
	{
		if (const UGTWeatherStateDefinition* Target = Weather->GetTargetState())
		{
			Id = Target->StateId;
		}
		Alpha = Weather->GetBlendAlpha();
		Pressure = Weather->GetStormPressure();
	}
	if (Id != TargetId)
	{
		BlendFrom = Current;
		BlendTo = DefaultSet(Id);
		TargetId = Id;
		UE_LOG(LogTemp, Display, TEXT("GTLOOK weather target %s (blend alpha %.2f): %s"), *Id.ToString(), Alpha, *BlendTo.Describe());
	}
	FGTLookSet Set = FGTLookSet::Lerp(BlendFrom, BlendTo, FMath::SmoothStep(0.f, 1.f, Alpha));
	if (Pressure > 0.f)
	{
		Set = FGTLookSet::Lerp(Set, DefaultSet(TEXT("Storm")), FMath::Clamp(Pressure, 0.f, 1.f));
	}
	Current = Set;
	if (Mode != 0)
	{
		ApplyExposure(Set, Mode, Debug);
		PushSet(Set, Debug);
	}

	TagTimer -= DeltaTime;
	if (TagTimer <= 0.f)
	{
		TagTimer = 1.f;
		TagExclusions();
		WrapSurfaces();
	}
	const int32 Surface = CVarLookSurface.GetValueOnGameThread() != 0 ? 1 : 0;
	if (Surface != AppliedSurface)
	{
		ApplySurface(Surface);
	}

	// Look stage L3: the weather held, the sky dome, the foliage switch.
	HoldWeather();
	UpdateSky(DeltaTime, CVarLookSky.GetValueOnGameThread() != 0 ? 1 : 0);
	const int32 Foliage = CVarLookFoliage.GetValueOnGameThread() != 0 ? 1 : 0;
	if (Foliage != AppliedFoliage)
	{
		ApplyFoliage(Foliage);
	}
	// Leg dressing LD3: the biome dressing switch.
	const int32 Dressing = CVarLookDressing.GetValueOnGameThread() != 0 ? 1 : 0;
	if (Dressing != AppliedDressing)
	{
		ApplyDressing(Dressing);
	}
}

FString UGTLookSubsystem::Describe() const
{
	int32 Lights = 0;
	for (const TPair<TWeakObjectPtr<UDirectionalLightComponent>, float>& Entry : SunAngles)
	{
		Lights += Entry.Key.IsValid() ? 1 : 0;
	}
	const FString L3 = FString::Printf(TEXT("gt.Look.Sky %d gt.Look.Haze %d gt.Look.Foliage %d gt.Look.Dressing %d (cloud cover %.2f, sky scale %.2f, weather held: %s); "),
		AppliedSky, CVarLookHaze.GetValueOnGameThread(), AppliedFoliage, AppliedDressing, SkyCloudCover, SkySkyScale, HeldWeather.IsEmpty() ? TEXT("no") : *HeldWeather);
	return L3 + FString::Printf(TEXT("gt.Look.Post %d gt.Look.Kuwahara %d gt.Look.Debug %d gt.Look.Surface %d (%d painterly slot(s)); weather %s; %s; sun %.2f lux, %d light(s) at %s deg; stencil water %d dashboard %d; volume %s, blendables %d"),
		AppliedMode, AppliedKuwahara, AppliedDebug, AppliedSurface, SurfaceMIDs.Num(), *TargetId.ToString(), *Current.Describe(), LastSunLux, Lights,
		bSunHard ? *FString::Printf(TEXT("%.2f"), SunAngleDeg) : TEXT("their own"), StencilWater, StencilDash,
		Volume ? (Volume->bEnabled ? TEXT("on") : TEXT("off")) : TEXT("none"), Volume ? Volume->Settings.WeightedBlendables.Array.Num() : 0);
}

// ---- look stage L3 (VEHICLE_BUILD_SYSTEM 58): the sky dome, the foliage switch, the weather hold -------------------------

void UGTLookSubsystem::EnsureSky()
{
	UWorld* World = GetWorld();
	if (SkyDome || bSkyTried || !World)
	{
		return;
	}
	bSkyTried = true;
	// A level can supply its own backdrop while retaining the shared weather controls.
	// Reuse it instead of drawing the prototype dome over distant terrain.
	for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
	{
		if (!It->ActorHasTag(TEXT("GTLook.LocalSky")))
		{
			continue;
		}
		UStaticMeshComponent* LocalMesh = It->GetStaticMeshComponent();
		UMaterialInterface* LocalMaterial = LocalMesh ? LocalMesh->GetMaterial(0) : nullptr;
		if (!LocalMaterial)
		{
			continue;
		}
		SkyMID = UMaterialInstanceDynamic::Create(LocalMaterial, this);
		LocalMesh->SetMaterial(0, SkyMID);
		SkyDome = *It;
		UE_LOG(LogTemp, Display, TEXT("GTLOOK sky: using level-owned backdrop %s"), *It->GetName());
		return;
	}
	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, SkySpherePath);
	UMaterialInterface* SkyMaterial = LoadObject<UMaterialInterface>(nullptr, SkyInstancePath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!Sphere || !SkyMaterial)
	{
		UE_LOG(LogTemp, Display, TEXT("GTLOOK sky: %s %s, %s %s: gt.Look.Sky has nothing to show (Art/setup_look_l3.bat)"),
			SkySpherePath, Sphere ? TEXT("loaded") : TEXT("MISSING"), SkyInstancePath, SkyMaterial ? TEXT("loaded") : TEXT("MISSING"));
		return;
	}
	FActorSpawnParameters Params;
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AStaticMeshActor* Dome = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform::Identity, Params);
	if (!Dome)
	{
		UE_LOG(LogTemp, Warning, TEXT("GTLOOK sky: the dome did not spawn"));
		return;
	}
	UStaticMeshComponent* Mesh = Dome->GetStaticMeshComponent();
	Mesh->SetMobility(EComponentMobility::Movable);
	// No collision of any kind (measured 2026-09-26: set before SetStaticMesh alone, the 10 km sphere still collided and
	// launched a car spawned near the origin 185 m up; the profile is set before the mesh and everything again after it).
	Mesh->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->SetCanEverAffectNavigation(false);
	// A backdrop, not a light: out of the shadows, the real-time sky capture (it would light the world), the reflection
	// captures, ray tracing, Lumen and the distance fields, and every scene capture (the rain's top-down occlusion
	// capture must not see a lid over the world). Translucent, it writes no depth and no GBuffer either.
	Mesh->CastShadow = false;
	Mesh->bCastDynamicShadow = false;
	Mesh->bCastStaticShadow = false;
	Mesh->bAffectDynamicIndirectLighting = false;
	Mesh->bAffectDistanceFieldLighting = false;
	Mesh->bVisibleInRayTracing = false;
	Mesh->bVisibleInReflectionCaptures = false;
	Mesh->bVisibleInRealTimeSkyCaptures = false;
	Mesh->bHiddenInSceneCapture = true;
	Mesh->bReceivesDecals = false;
	Mesh->bNeverDistanceCull = true;
	// Drawn before every other Before-DOF translucency (the rain, the spray), which the dome must never cover.
	Mesh->TranslucencySortPriority = -1000;
	Mesh->SetStaticMesh(Sphere);
	SkyMID = UMaterialInstanceDynamic::Create(SkyMaterial, this);
	Mesh->SetMaterial(0, SkyMID);
	Dome->SetActorScale3D(FVector(SkyRadiusCm / 50.f));
	Mesh->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
	Dome->SetActorEnableCollision(false);
	Mesh->MarkRenderStateDirty();
	SkyDome = Dome;
	for (TActorIterator<ADirectionalLight> It(World); It; ++It)
	{
		SkySun = Cast<UDirectionalLightComponent>(It->GetLightComponent());
		break;
	}
	UE_LOG(LogTemp, Display, TEXT("GTLOOK sky: the dome spawned at the world origin (%s, radius %.0f m, %s, sort priority %d; collision %d, a physics body %d, actor collision %d; no shadow, sky capture, reflection capture, ray tracing, Lumen, distance field or scene capture); sun %s"),
		*Sphere->GetName(), SkyRadiusCm / 100.f, *SkyMID->GetName(), Mesh->TranslucencySortPriority, static_cast<int32>(Mesh->GetCollisionEnabled()),
		Mesh->GetBodyInstance() && Mesh->GetBodyInstance()->IsValidBodyInstance() ? 1 : 0, Dome->GetActorEnableCollision() ? 1 : 0, SkySun.IsValid() ? *SkySun->GetOwner()->GetName() : TEXT("none"));
}

void UGTLookSubsystem::UpdateSky(float DeltaTime, int32 Sky)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	if (!SkyDome)
	{
		EnsureSky();
	}
	if (!SkyDome || !SkyMID)
	{
		AppliedSky = Sky;
		return;
	}
	if (Sky != AppliedSky)
	{
		SkyDome->SetActorHiddenInGame(Sky == 0);
		AppliedSky = Sky;
		UE_LOG(LogTemp, Display, TEXT("GTLOOK gt.Look.Sky %d: the dome %s"), Sky, Sky != 0 ? TEXT("shown") : TEXT("hidden"));
	}
	if (Sky == 0)
	{
		return;
	}
	float Cover = 0.1f;
	float Scale = 1.f;
	float WindYaw = 0.f;
	if (const UGTWeatherSubsystem* Weather = World->GetSubsystem<UGTWeatherSubsystem>())
	{
		const FGTWeatherValues& Values = Weather->GetCurrent();
		Cover = Values.CloudCover;
		Scale = Values.SkyScale;
		WindYaw = Values.WindYaw;
	}
	// The drift accumulates, so a turning wind turns it without a jump.
	const float Yaw = FMath::DegreesToRadians(WindYaw);
	CloudOffset += FVector(FMath::Cos(Yaw), FMath::Sin(Yaw), 0.f) * CloudDrift * DeltaTime;
	if (!SkySun.IsValid())
	{
		for (TActorIterator<ADirectionalLight> It(World); It; ++It)
		{
			SkySun = Cast<UDirectionalLightComponent>(It->GetLightComponent());
			break;
		}
	}
	const float SunLux = SkySun.IsValid() ? SkySun->Intensity : 0.f;
	SkyMID->SetScalarParameterValue(TEXT("CloudCover"), Cover);
	SkyMID->SetScalarParameterValue(TEXT("SkyScale"), Scale);
	SkyMID->SetScalarParameterValue(TEXT("SunRef"), SunLux > 0.f ? SunLux / UE_PI : 1.f);
	SkyMID->SetScalarParameterValue(TEXT("LitX"), LitX);
	SkyMID->SetVectorParameterValue(TEXT("CloudOffset"), FLinearColor(CloudOffset.X, CloudOffset.Y, CloudOffset.Z, 0.f));
	SkyCloudCover = Cover;
	SkySkyScale = Scale;
}

void UGTLookSubsystem::ApplyFoliage(int32 Foliage)
{
	int32 Dressings = 0;
	int32 Cards = 0;
	if (UWorld* World = GetWorld())
	{
		for (TActorIterator<AGTTerrainDressing> It(World); It; ++It)
		{
			if (UHierarchicalInstancedStaticMeshComponent* Component = It->Foliage.Get())
			{
				Component->SetVisibility(Foliage != 0);
				++Dressings;
				Cards += Component->GetInstanceCount();
			}
		}
	}
	AppliedFoliage = Foliage;
	UE_LOG(LogTemp, Display, TEXT("GTLOOK gt.Look.Foliage %d on %d dressing(s), %d card(s)"), Foliage, Dressings, Cards);
}

bool UGTLookSubsystem::IsBiomeDressing(const AActor* Actor)
{
	if (!Actor)
	{
		return false;
	}
	for (const FName& Tag : Actor->Tags)
	{
		const FString Text = Tag.ToString();
		if (Text.StartsWith(TEXT("OWBiome.")) || Text.StartsWith(TEXT("GTBiome.")))
		{
			return true;
		}
	}
	return false;
}

void UGTLookSubsystem::ApplyDressing(int32 Dressing)
{
	// Leg dressing LD3: 0 hides every actor tagged OWBiome.* / GTBiome.* (the PCG volumes; their instance components go
	// with them) and turns its collision off, remembering each one's own state; 1 puts back what was remembered, so an
	// actor that was hidden or without collision by design stays so. Nothing is touched at 1 when nothing was hidden.
	int32 Actors = 0;
	if (UWorld* World = GetWorld())
	{
		if (Dressing == 0)
		{
			for (TActorIterator<AActor> It(World); It; ++It)
			{
				if (!IsBiomeDressing(*It))
				{
					continue;
				}
				const TWeakObjectPtr<AActor> Key(*It);
				if (!DressingSaved.Contains(Key))
				{
					DressingSaved.Add(Key, TPair<bool, bool>(It->IsHidden(), It->GetActorEnableCollision()));
				}
				It->SetActorHiddenInGame(true);
				It->SetActorEnableCollision(false);
				++Actors;
			}
		}
		else
		{
			for (const TPair<TWeakObjectPtr<AActor>, TPair<bool, bool>>& Entry : DressingSaved)
			{
				if (AActor* Actor = Entry.Key.Get())
				{
					Actor->SetActorHiddenInGame(Entry.Value.Key);
					Actor->SetActorEnableCollision(Entry.Value.Value);
					++Actors;
				}
			}
			DressingSaved.Reset();
		}
	}
	if (IConsoleVariable* Grass = IConsoleManager::Get().FindConsoleVariable(TEXT("grass.Enable")))
	{
		Grass->Set(Dressing, ECVF_SetByCode);
	}
	// LD5 hook: UGTVegetationSubsystem reads gt.Look.Dressing itself each tick and neither bends, resists nor snaps
	// anything while it is 0 (its instances are hidden with their volumes above); nothing to call from here.
	AppliedDressing = Dressing;
	UE_LOG(LogTemp, Display, TEXT("GTLOOK gt.Look.Dressing %d on %d biome actor(s), grass.Enable %d"), Dressing, Actors, Dressing);
}

void UGTLookSubsystem::HoldWeather()
{
	UWorld* World = GetWorld();
	const FString Want = CVarLookWeather.GetValueOnGameThread();
	if (Want.IsEmpty() || !World)
	{
		HeldWeather.Reset();
		return;
	}
	UGTWeatherSubsystem* Weather = World->GetSubsystem<UGTWeatherSubsystem>();
	if (!Weather)
	{
		return;
	}
	const UGTWeatherStateDefinition* Target = Weather->GetTargetState();
	if (Target && Target->StateId == FName(*Want))
	{
		HeldWeather = Want;
		return;
	}
	if (UGTWeatherStateDefinition* State = Weather->FindState(FName(*Want)))
	{
		Weather->SetState(State, /*bInstant*/ true);
		UE_LOG(LogTemp, Display, TEXT("GTLOOK gt.Look.Weather %s: the weather set to it, instantly (it was %s)"), *Want, Target ? *Target->StateId.ToString() : TEXT("none"));
	}
	else if (HeldWeather != Want)
	{
		UE_LOG(LogTemp, Warning, TEXT("GTLOOK gt.Look.Weather %s: no such weather state"), *Want);
	}
	HeldWeather = Want;
}
