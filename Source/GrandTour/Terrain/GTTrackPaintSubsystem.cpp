#include "Terrain/GTTrackPaintSubsystem.h"

#include "Engine/Canvas.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Materials/MaterialParameterCollection.h"
#include "Math/RandomStream.h"
#include "Misc/App.h"
#include "Terrain/GTMudBlots.inl"
#include "Terrain/GTGroundScatter.h"
#include "LandscapeGrassType.h"
#include "Engine/Engine.h"

/** MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md): the three switches, each on by default, for the owner's A/B. */
static TAutoConsoleVariable<int32> CVarMudCarry(
	TEXT("gt.Mud.Carry"), 1,
	TEXT("MR1: 1 wheels carrying mud out of a patch lay broken muddy tracks into the track paint (G coverage, B wetness) and the ground materials draw them; 0 no carried tracks (the material skips its cover block when gt.Mud.Splats is 0 too)."));
static TAutoConsoleVariable<int32> CVarMudSplats(
	TEXT("gt.Mud.Splats"), 1,
	TEXT("MR1: 1 thrown mud that leaves every patch is traced (at most 64 traces a frame) and splats the landscape (track paint) or a static mesh (a pooled decal, at most 96); 0 it is lost as before MR1."));
static TAutoConsoleVariable<int32> CVarMudGrassMud(
	TEXT("gt.Mud.GrassMud"), 1,
	TEXT("MR1: 1 grass over carried mud darkens toward dried mud at its base (M_TS_Grass, M_GT_FoliageCard); 0 off (the material's GrassMud static switch removes it entirely)."));
/** MudRunner MRP (docs/MUDRUNNER_LESSONS_PLAN.md MRP): the physically based values and the mud ground's parallax, for the owner's A/B. */
static TAutoConsoleVariable<int32> CVarMudPBR(
	TEXT("gt.Mud.PBR"), 1,
	TEXT("MRP: 1 every mud surface draws physically based values (wet mud roughness 0.45-0.65, never under 0.4 outside water; rut water F0 0.02, settled 0.15 with a ripple, churned 0.5; the baked AO and a cavity tint); 0 the look before MRP (the glossy bake roughness, the far gloss fade, the water's grazing gloss and Fresnel opacity, the froth's glint)."));
static TAutoConsoleVariable<int32> CVarMudPOM(
	TEXT("gt.Mud.POM"), 2,
	TEXT("MRP: the mud ground's parallax occlusion (M_GT_Mud, 3 cm over the ORH height, faded out 6-14 m, none under rut water): 0 off, 1 8 steps, 2 adaptive 8-16 steps by the view angle (the default)."));
static TAutoConsoleVariable<int32> CVarMudPOMShadow(
	TEXT("gt.Mud.POMShadow"), 1,
	TEXT("MRP: 1 the parallax casts a 4-step self-shadow toward the sun within 4 m (needs gt.Mud.POM 1 or 2); 0 off."));
/** Deformable gravel DG1 (docs/DEFORMABLE_GRAVEL_PLAN.md DG1 item 2): the gravel ground's parallax, for the owner's A/B. */
static TAutoConsoleVariable<int32> CVarGravelPOM(
	TEXT("gt.Gravel.POM"), 2,
	TEXT("Deformable gravel DG1: the gravel ground's parallax occlusion (M_GT_Gravel over the Loose slice's height, 0.8 cm, the Packed 0.5 cm in the ruts, faded out 6-14 m, a 4-step sun self-shadow within 4 m): 0 off, 1 8 steps, 2 adaptive 8-16 steps by the view angle (the default)."));
static TAutoConsoleVariable<int32> CVarGravelDebug(
	TEXT("gt.Gravel.Debug"), 0,
	TEXT("Deformable gravel DG1, a diagnosis (the pale rut-edge line): M_GT_Gravel draws 1 the flat vertex normal instead of the field's, 2 no texture slide with the field, 3 no baked detail normal, 4 the lighting's normal flat (the parallax keeps the field's frame), 5 no specular, 6 fully rough; 0 normal."));
/** Ground relief GR2 (docs/GROUND_RELIEF_PLAN.md GR2 phase B item 2): the strips' soil detail, for the owner's A/B. */
static TAutoConsoleVariable<int32> CVarGroundDetail(
	TEXT("gt.Ground.Detail"), 1,
	TEXT("Ground relief GR2: 1 the test strips' landscape (MI_GT_Landscape_Strips, its GroundDetail switch on) draws the soil detail - the ScrubSoil and SoilUnderGrass bakes, two samples blended by a 7 m noise and a 13 m tint against the tiling, parallax within 15-25 m, faded into the old look over 25-40 m; Benmore B1: the review landscape's non-road ground through MF_GT_GroundDetail (MPC_GT_GroundDetail GroundDetail); 0 the look before GR2."));

namespace
{
	const TCHAR* RenderTargetPath = TEXT("/Game/GrandTour/Terrain/RT_TrackPaint.RT_TrackPaint");
	const TCHAR* CollectionPath = TEXT("/Game/GrandTour/Terrain/MPC_TrackPaint.MPC_TrackPaint");
	const TCHAR* GroundDetailCollectionPath = TEXT("/Game/GrandTour/Terrain/MPC_GT_GroundDetail.MPC_GT_GroundDetail");   // Benmore integration B1
	const TCHAR* ScatterGrassTypePaths[] = { TEXT("/Game/GrandTour/Terrain/GroundDetail/LGT_GT_SoilScatter.LGT_GT_SoilScatter"),
		TEXT("/Game/GrandTour/Terrain/GroundDetail/LGT_GT_GrassLitter.LGT_GT_GrassLitter") };   // Benmore integration B1
	const FName ParamOrigin(TEXT("TrackOrigin"));
	const FName ParamDepth(TEXT("TrackDepthCm"));
	const FName ParamMudCover(TEXT("MudCover"));
	const FName ParamGrassMud(TEXT("GrassMud"));
	const FName ParamMudPBR(TEXT("MudPBR"));
	const FName ParamMudPOM(TEXT("MudPOM"));
	const FName ParamMudPOMShadow(TEXT("MudPOMShadow"));
	const FName ParamGravelPOM(TEXT("GravelPOM"));   // Deformable gravel DG1
	const FName ParamGravelDebug(TEXT("GravelDebug"));
	const FName ParamGroundDetail(TEXT("GroundDetail"));   // Ground relief GR2
	constexpr float MaxCellDepth = 4.f;
	constexpr int32 AtlasTiles = 4;   // the splat atlas is 4 x 4 tiles
}

bool UGTTrackPaintSubsystem::IsCarryEnabled()
{
	return CVarMudCarry.GetValueOnGameThread() != 0;
}

bool UGTTrackPaintSubsystem::IsSplatsEnabled()
{
	return CVarMudSplats.GetValueOnGameThread() != 0;
}

bool UGTTrackPaintSubsystem::IsGrassMudEnabled()
{
	return CVarMudGrassMud.GetValueOnGameThread() != 0;
}

int32 UGTTrackPaintSubsystem::GetMudPBR()
{
	return CVarMudPBR.GetValueOnGameThread() != 0 ? 1 : 0;
}

int32 UGTTrackPaintSubsystem::GetMudPOM()
{
	return FMath::Clamp(CVarMudPOM.GetValueOnGameThread(), 0, 2);
}

int32 UGTTrackPaintSubsystem::GetMudPOMShadow()
{
	return CVarMudPOMShadow.GetValueOnGameThread() != 0 ? 1 : 0;
}

int32 UGTTrackPaintSubsystem::GetGravelPOM()
{
	return FMath::Clamp(CVarGravelPOM.GetValueOnGameThread(), 0, 2);
}

bool UGTTrackPaintSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGTTrackPaintSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	bGpuEnabled = FApp::CanEverRender();
	GridSize = FMath::Max(8, GridSize);
	MudGridSize = FMath::Max(GridSize, MudGridSize);

	RenderTarget = LoadObject<UTextureRenderTarget2D>(nullptr, RenderTargetPath);
	ParameterCollection = LoadObject<UMaterialParameterCollection>(nullptr, CollectionPath);
	// Benmore integration B1 (Art/Unreal/benmore_gt_ground.py makes them): absent before B1, so quiet finds.
	GroundDetailCollection = LoadObject<UMaterialParameterCollection>(nullptr, GroundDetailCollectionPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	for (const TCHAR* Path : ScatterGrassTypePaths)
	{
		if (ULandscapeGrassType* Type = LoadObject<ULandscapeGrassType>(nullptr, Path, nullptr, LOAD_NoWarn | LOAD_Quiet))
		{
			ScatterGrassTypes.Add(Type);
			for (const FGrassVariety& Variety : Type->GrassVarieties)
			{
				ScatterAuthoredDensity.Add(Variety.GrassDensity.Default);
			}
		}
	}
	if (RenderTarget)
	{
		Resolution = RenderTarget->SizeX;
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTTrackPaintSubsystem: %s missing (run Art/setup_m1_trackpaint.bat); tracks will not render"), RenderTargetPath);
		if (bGpuEnabled)
		{
			RenderTarget = UKismetRenderingLibrary::CreateRenderTarget2D(GetWorld(), Resolution, Resolution, RTF_RGBA16f, FLinearColor::Black);
		}
	}
	if (!ParameterCollection)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTTrackPaintSubsystem: %s missing; the material will not know where the window is"), CollectionPath);
	}
	if (Resolution % GridSize != 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTTrackPaintSubsystem: resolution %d is not a multiple of the grid %d; texels and cells can drift by a texel on recentre"), Resolution, GridSize);
	}
	Cells.Init(0.f, GridSize * GridSize);
	CoverCells.Init(0.f, MudGridSize * MudGridSize);
	WetCells.Init(0.f, MudGridSize * MudGridSize);
	if (bGpuEnabled && RenderTarget)
	{
		UKismetRenderingLibrary::ClearRenderTarget2D(GetWorld(), RenderTarget, FLinearColor::Black);
		BrushTexture = MakeBrush(true);
		WhiteTexture = MakeBrush(false);
		BlotMulTexture = MakeBlotBrush(true);
		BlotAddTexture = MakeBlotBrush(false);
	}
	WriteCollection();
	WriteSwitches();
	UE_LOG(LogTemp, Display, TEXT("UGTTrackPaintSubsystem: window %.0f m, %d px, %d cells, gpu=%d; MR1 mud grid %d cells (%.1f cm), G fade %.0f s, B dry %.0f s, %d atlas blots, gt.Mud.Carry %d gt.Mud.Splats %d gt.Mud.GrassMud %d; MRP gt.Mud.PBR %d gt.Mud.POM %d gt.Mud.POMShadow %d"),
		WindowSizeCm / 100.f, Resolution, GridSize, bGpuEnabled ? 1 : 0, MudGridSize, WindowSizeCm / MudGridSize, MudFadeSeconds, MudDrySeconds, GTMudBlots::Count,
		IsCarryEnabled() ? 1 : 0, IsSplatsEnabled() ? 1 : 0, IsGrassMudEnabled() ? 1 : 0, GetMudPBR(), GetMudPOM(), GetMudPOMShadow());
}

void UGTTrackPaintSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (bHaveFocus && FVector2D::Distance(Focus, Origin) > RecentreDistance)
	{
		Recentre(SnapToCell(Focus));
	}
	FlushStamps();
	FlushBlots();
	WriteSwitches();
	// R exactly as before MR1: every DecayInterval, once any rut was stamped. G and B on their own clocks (MR1).
	float FactorR = 1.f;
	DecayTimer += DeltaTime;
	if (DecayTimer >= DecayInterval)
	{
		if (StampCount > 0)
		{
			FactorR = FMath::Exp(-DecayTimer / FMath::Max(1.f, FadeSeconds));
		}
		DecayTimer = 0.f;
	}
	float FactorG = 1.f;
	float FactorB = 1.f;
	if (MudStampCount > 0)
	{
		CoverTimer += DeltaTime;
		WetTimer += DeltaTime;
		if (CoverTimer >= CoverDecayInterval)
		{
			FactorG = FMath::Exp(-CoverTimer / FMath::Max(1.f, MudFadeSeconds));
			CoverTimer = 0.f;
		}
		if (WetTimer >= WetDecayInterval)
		{
			FactorB = FMath::Exp(-WetTimer / FMath::Max(1.f, MudDrySeconds));
			WetTimer = 0.f;
		}
	}
	if (FactorR != 1.f || FactorG != 1.f || FactorB != 1.f)
	{
		Decay(FactorR, FactorG, FactorB);
	}
}

void UGTTrackPaintSubsystem::SetFocus(const FVector& WorldLocation)
{
	Focus = FVector2D(WorldLocation);
	if (!bHaveFocus)
	{
		bHaveFocus = true;
		Origin = SnapToCell(Focus);
		WriteCollection();
	}
}

void UGTTrackPaintSubsystem::AddWheelStamp(const FVector& Start, const FVector& End, float WidthCm, float Strength, float DeltaSeconds)
{
	if (Strength <= 0.f || WidthCm <= 0.f)
	{
		return;
	}
	const FVector2D A(Start);
	const FVector2D B(End);
	// Once per width of travel while moving, plus a slow dig while standing on the throttle.
	const float Amount = Strength * (FMath::Min(1.f, FVector2D::Distance(A, B) / WidthCm) + StationaryDigRate * DeltaSeconds);
	Pending.Add({A, B, WidthCm, Amount});
}

void UGTTrackPaintSubsystem::AddCarriedMud(FGTMudCarryState& State, const FVector& Start, const FVector& End, float WidthCm, float MudLoad)
{
	if (!IsCarryEnabled() || MudLoad <= MinCarryLoad || WidthCm <= 0.f)
	{
		return;
	}
	const FVector2D A(Start);
	const FVector2D Delta = FVector2D(End) - A;
	const float Length = static_cast<float>(Delta.Size());
	if (Length <= KINDA_SMALL_NUMBER)
	{
		return;
	}
	const FVector2D Dir = Delta / Length;
	const FVector2D Side(-Dir.Y, Dir.X);
	const float Load = FMath::Clamp(MudLoad, 0.f, 1.f);
	// MR2 housekeeping 1: stamped by distance with overlapping blots (the spacing a share of the smallest blot's reach at this
	// load), and the strength along the track from the stroke's own noise, so the trail breaks into smears and gaps, not beads.
	const float SizeScale = 0.55f + 0.45f * Load;
	const float SmallestReach = 0.5f * WidthCm * CarrySizeMin * SizeScale * GTMudBlots::Window;
	if (State.NoiseKey == 0)
	{
		State.NoiseKey = static_cast<uint32>(State.Seed) * 2654435761u | 1u;
	}
	FRandomStream Random(State.Seed);
	float Walked = 0.f;
	int32 Guard = 0;
	while (FMath::Max(0.f, State.ToNextCm) <= Length - Walked && Guard++ < 1024)
	{
		Walked += FMath::Max(0.f, State.ToNextCm);
		// Every random draw is made whether or not the place is a gap, so a gap never shifts the blots after it.
		const float Half = 0.5f * WidthCm * Random.FRandRange(CarrySizeMin, CarrySizeMax) * SizeScale;
		const float Across = WidthCm * Random.FRandRange(-CarryJitter, CarryJitter);
		const float Angle = Random.FRandRange(0.f, 360.f);
		const int32 Tile = Random.RandRange(0, GTMudBlots::Count - 1);
		const float Strength = CarryStrengthAt(State.DistanceCm + Walked, State.NoiseKey, Load);
		State.ToNextCm = SmallestReach * Random.FRandRange(CarrySpacingMin, CarrySpacingMax);
		if (Strength <= 0.05f)
		{
			++CarriedGapCount;
			continue;
		}
		FBlot Blot;
		Blot.HalfCm = Half;
		Blot.Centre = A + Dir * Walked + Side * Across;
		Blot.AngleDeg = Angle;
		Blot.Tile = Tile;
		Blot.Coverage = CarryCoverage * Load * Strength;
		Blot.Wet = 1.f;
		PendingBlots.Add(Blot);
		++CarriedBlotCount;
	}
	State.ToNextCm -= Length - Walked;
	State.DistanceCm += Length;
	State.Seed = Random.GetCurrentSeed();
}

namespace
{
	// MR2 housekeeping 1: a hashed value noise along a stroke (one value per lattice point, smoothstep between), no state but the key.
	float CarryHash01(int32 Index, uint32 Key)
	{
		uint32 H = static_cast<uint32>(Index) * 0x9E3779B1u ^ Key;
		H ^= H >> 16;
		H *= 0x7feb352du;
		H ^= H >> 15;
		H *= 0x846ca68bu;
		H ^= H >> 16;
		return static_cast<float>(H & 0xffffffu) / 16777216.f;
	}

	float CarryValueNoise(float X, uint32 Key)
	{
		const float Floor = FMath::FloorToFloat(X);
		const int32 Index = static_cast<int32>(Floor);
		const float T = X - Floor;
		return FMath::Lerp(CarryHash01(Index, Key), CarryHash01(Index + 1, Key), T * T * (3.f - 2.f * T));
	}
}

float UGTTrackPaintSubsystem::CarryStrengthAt(float DistanceCm, uint32 NoiseKey, float MudLoad) const
{
	const float Noise = 0.65f * CarryValueNoise(DistanceCm / FMath::Max(1.f, CarryNoiseLongCm), NoiseKey)
		+ 0.35f * CarryValueNoise(DistanceCm / FMath::Max(1.f, CarryNoiseShortCm) + 17.3f, NoiseKey ^ 0x5bd1e995u);
	const float Threshold = FMath::Lerp(CarryGapAtEmpty, CarryGapAtFull, FMath::Clamp(MudLoad, 0.f, 1.f));
	const float T = FMath::Clamp((Noise - Threshold) / FMath::Max(0.01f, CarryGapSoft), 0.f, 1.f);
	return T * T * (3.f - 2.f * T);
}

void UGTTrackPaintSubsystem::AddSplat(const FVector& Point, float RadiusCm, int32 Seed)
{
	if (RadiusCm <= 0.f)
	{
		return;
	}
	FRandomStream Random(Seed);
	FBlot Blot;
	Blot.Centre = FVector2D(Point);
	Blot.HalfCm = RadiusCm / GTMudBlots::Window;   // the blot reaches Window of the half side: RadiusCm
	Blot.AngleDeg = Random.FRandRange(0.f, 360.f);
	Blot.Tile = Random.RandRange(0, GTMudBlots::Count - 1);
	Blot.Coverage = SplatCoverage;
	Blot.Wet = 1.f;
	PendingBlots.Add(Blot);
	++SplatCount;
}

float UGTTrackPaintSubsystem::SampleBlotMask(int32 Tile, float U, float V)
{
	if (Tile < 0 || Tile >= GTMudBlots::Count || U < 0.f || U > 1.f || V < 0.f || V > 1.f)
	{
		return 0.f;
	}
	// Texel centres at (i + 0.5) / Size, as the GPU's bilinear sample of the brush tile; clamped at the tile's edge texels
	// (which the bake leaves empty).
	const int32 N = GTMudBlots::Size;
	const float X = FMath::Clamp(U * N - 0.5f, 0.f, N - 1.f);
	const float Y = FMath::Clamp(V * N - 0.5f, 0.f, N - 1.f);
	const int32 X0 = FMath::FloorToInt(X);
	const int32 Y0 = FMath::FloorToInt(Y);
	const int32 X1 = FMath::Min(X0 + 1, N - 1);
	const int32 Y1 = FMath::Min(Y0 + 1, N - 1);
	const float FX = X - X0;
	const float FY = Y - Y0;
	const uint8* M = GTMudBlots::Masks + Tile * N * N;
	const float A = FMath::Lerp(static_cast<float>(M[Y0 * N + X0]), static_cast<float>(M[Y0 * N + X1]), FX);
	const float B = FMath::Lerp(static_cast<float>(M[Y1 * N + X0]), static_cast<float>(M[Y1 * N + X1]), FX);
	return FMath::Lerp(A, B, FY) / 255.f;
}

FVector2D UGTTrackPaintSubsystem::SnapToCell(const FVector2D& World) const
{
	const float CellCm = WindowSizeCm / GridSize;
	return FVector2D(FMath::RoundToFloat(World.X / CellCm) * CellCm, FMath::RoundToFloat(World.Y / CellCm) * CellCm);
}

FVector2D UGTTrackPaintSubsystem::WorldToPixel(const FVector2D& World) const
{
	// Pixel (0, 0) is the window's min corner; MF_TrackPaint uses the same mapping.
	return ((World - Origin) / WindowSizeCm + FVector2D(0.5f, 0.5f)) * Resolution;
}

float UGTTrackPaintSubsystem::SampleDepth(const FVector& WorldLocation) const
{
	const float CellCm = WindowSizeCm / GridSize;
	const FVector2D Local = FVector2D(WorldLocation) - Origin + FVector2D(WindowSizeCm * 0.5f);
	const int32 X = FMath::FloorToInt(Local.X / CellCm);
	const int32 Y = FMath::FloorToInt(Local.Y / CellCm);
	if (X < 0 || Y < 0 || X >= GridSize || Y >= GridSize)
	{
		return 0.f;
	}
	return Cells[Y * GridSize + X];
}

int32 UGTTrackPaintSubsystem::MudCellAt(const FVector& WorldLocation) const
{
	const float CellCm = WindowSizeCm / MudGridSize;
	const FVector2D Local = FVector2D(WorldLocation) - Origin + FVector2D(WindowSizeCm * 0.5f);
	const int32 X = FMath::FloorToInt(Local.X / CellCm);
	const int32 Y = FMath::FloorToInt(Local.Y / CellCm);
	if (X < 0 || Y < 0 || X >= MudGridSize || Y >= MudGridSize)
	{
		return INDEX_NONE;
	}
	return Y * MudGridSize + X;
}

float UGTTrackPaintSubsystem::SampleCoverage(const FVector& WorldLocation) const
{
	const int32 Index = MudCellAt(WorldLocation);
	return CoverCells.IsValidIndex(Index) ? CoverCells[Index] : 0.f;
}

float UGTTrackPaintSubsystem::SampleWetness(const FVector& WorldLocation) const
{
	const int32 Index = MudCellAt(WorldLocation);
	return WetCells.IsValidIndex(Index) ? WetCells[Index] : 0.f;
}

float UGTTrackPaintSubsystem::GetMaxDepth() const
{
	float Result = 0.f;
	for (const float Cell : Cells)
	{
		Result = FMath::Max(Result, Cell);
	}
	return Result;
}

bool UGTTrackPaintSubsystem::ReadRenderTargetDepth(const FVector& WorldLocation, float& OutDepth) const
{
	if (!bGpuEnabled || !RenderTarget)
	{
		return false;
	}
	const FVector2D Pixel = WorldToPixel(FVector2D(WorldLocation));
	const int32 X = FMath::FloorToInt(Pixel.X);
	const int32 Y = FMath::FloorToInt(Pixel.Y);
	if (X < 0 || Y < 0 || X >= Resolution || Y >= Resolution)
	{
		OutDepth = 0.f;
		return true;
	}
	OutDepth = UKismetRenderingLibrary::ReadRenderTargetRawPixel(GetWorld(), RenderTarget, X, Y, false).R;
	return true;
}

FVector2D UGTTrackPaintSubsystem::ReadRenderTargetMud(const FVector& WorldLocation) const
{
	if (!bGpuEnabled || !RenderTarget)
	{
		return FVector2D(-1.f, -1.f);
	}
	const FVector2D Pixel = WorldToPixel(FVector2D(WorldLocation));
	const int32 X = FMath::FloorToInt(Pixel.X);
	const int32 Y = FMath::FloorToInt(Pixel.Y);
	if (X < 0 || Y < 0 || X >= Resolution || Y >= Resolution)
	{
		return FVector2D::ZeroVector;
	}
	const FLinearColor Texel = UKismetRenderingLibrary::ReadRenderTargetRawPixel(GetWorld(), RenderTarget, X, Y, false);
	return FVector2D(Texel.G, Texel.B);
}

void UGTTrackPaintSubsystem::WriteCollection() const
{
	if (!ParameterCollection)
	{
		return;
	}
	UKismetMaterialLibrary::SetVectorParameterValue(GetWorld(), ParameterCollection, ParamOrigin,
		FLinearColor(Origin.X, Origin.Y, WindowSizeCm, static_cast<float>(Resolution)));
	UKismetMaterialLibrary::SetScalarParameterValue(GetWorld(), ParameterCollection, ParamDepth, TrackDepthCm);
}

void UGTTrackPaintSubsystem::WriteSwitches()
{
	WriteGroundDetail();
	// MR1: the material's cover block runs while either source of G is on; the grass's while gt.Mud.GrassMud is. Written only
	// where the collection has them (Art/Unreal/mud_cover.py adds them) and only when they change.
	const int32 Cover = (IsCarryEnabled() || IsSplatsEnabled()) ? 1 : 0;
	const int32 Grass = IsGrassMudEnabled() ? 1 : 0;
	// MRP: gt.Mud.PBR, gt.Mud.POM and gt.Mud.POMShadow the same way (MudPBR, MudPOM, MudPOMShadow; Art/Unreal/live_mud_style.py adds them).
	const int32 Pbr = GetMudPBR();
	const int32 Pom = GetMudPOM();
	const int32 PomShadow = GetMudPOMShadow();
	// Deformable gravel DG1: gt.Gravel.POM the same way (GravelPOM; Art/Unreal/gravel_dg1_material.py adds it).
	const int32 GravelPom = GetGravelPOM();
	const int32 GravelDebug = FMath::Clamp(CVarGravelDebug.GetValueOnGameThread(), 0, 6);
	// Ground relief GR2: gt.Ground.Detail the same way (GroundDetail; Art/Unreal/ground_detail.py adds it).
	const int32 GroundDetail = CVarGroundDetail.GetValueOnGameThread() != 0 ? 1 : 0;
	if (!ParameterCollection || (Cover == WrittenCover && Grass == WrittenGrass && Pbr == WrittenPBR && Pom == WrittenPOM && PomShadow == WrittenPOMShadow
		&& GravelPom == WrittenGravelPOM && GravelDebug == WrittenGravelDebug && GroundDetail == WrittenGroundDetail))
	{
		return;
	}
	for (const TPair<FName, int32>& Switch : { TPair<FName, int32>(ParamMudPBR, Pbr), TPair<FName, int32>(ParamMudPOM, Pom), TPair<FName, int32>(ParamMudPOMShadow, PomShadow),
		TPair<FName, int32>(ParamGravelPOM, GravelPom), TPair<FName, int32>(ParamGravelDebug, GravelDebug), TPair<FName, int32>(ParamGroundDetail, GroundDetail) })
	{
		if (ParameterCollection->GetScalarParameterByName(Switch.Key))
		{
			UKismetMaterialLibrary::SetScalarParameterValue(GetWorld(), ParameterCollection, Switch.Key, static_cast<float>(Switch.Value));
		}
	}
	WrittenPBR = Pbr;
	WrittenPOM = Pom;
	WrittenPOMShadow = PomShadow;
	WrittenGravelPOM = GravelPom;
	WrittenGravelDebug = GravelDebug;
	WrittenGroundDetail = GroundDetail;
	if (ParameterCollection->GetScalarParameterByName(ParamMudCover))
	{
		UKismetMaterialLibrary::SetScalarParameterValue(GetWorld(), ParameterCollection, ParamMudCover, static_cast<float>(Cover));
	}
	if (ParameterCollection->GetScalarParameterByName(ParamGrassMud))
	{
		UKismetMaterialLibrary::SetScalarParameterValue(GetWorld(), ParameterCollection, ParamGrassMud, static_cast<float>(Grass));
	}
	WrittenCover = Cover;
	WrittenGrass = Grass;
}

void UGTTrackPaintSubsystem::WriteGroundDetail()
{
	const int32 Detail = CVarGroundDetail.GetValueOnGameThread() != 0 ? 1 : 0;
	if (GroundDetailCollection && Detail != WrittenGroundDetailB1 && GroundDetailCollection->GetScalarParameterByName(ParamGroundDetail))
	{
		UKismetMaterialLibrary::SetScalarParameterValue(GetWorld(), GroundDetailCollection, ParamGroundDetail, static_cast<float>(Detail));
	}
	WrittenGroundDetailB1 = Detail;
	// The scatter: on the grass types' densities, not the material's weight. A collection value does not reach the landscape's grass
	// weight render (B1's check: ScatterScale 0 left every scatter build the same), so the density is the switch; the grass maps stay.
	const float Scatter = AGTGroundScatter::IsEnabled() ? AGTGroundScatter::DensityScale() : 0.f;
	if (Scatter == WrittenScatterScale || ScatterGrassTypes.Num() == 0)
	{
		return;
	}
	const float Was = WrittenScatterScale < 0.f ? 1.f : WrittenScatterScale;
	ApplyScatterDensity(Scatter);
	WrittenScatterScale = Scatter;
	if (Was != Scatter && GEngine)
	{
		GEngine->Exec(GetWorld(), TEXT("grass.FlushCachePIE"));
		UE_LOG(LogTemp, Display, TEXT("UGTTrackPaintSubsystem: gt.Ground scatter density %.2f -> %.2f, landscape grass instances flushed"), Was, Scatter);
	}
}

void UGTTrackPaintSubsystem::ApplyScatterDensity(float Scale)
{
	int32 Index = 0;
	for (ULandscapeGrassType* Type : ScatterGrassTypes)
	{
		if (!Type)
		{
			continue;
		}
		for (FGrassVariety& Variety : Type->GrassVarieties)
		{
			if (ScatterAuthoredDensity.IsValidIndex(Index))
			{
				Variety.GrassDensity.Default = ScatterAuthoredDensity[Index] * Scale;
			}
			++Index;
		}
	}
}

void UGTTrackPaintSubsystem::Deinitialize()
{
	// The grass types are assets: leave them as authored (an editor session's PIE must not keep a scaled density).
	if (WrittenScatterScale >= 0.f && WrittenScatterScale != 1.f)
	{
		ApplyScatterDensity(1.f);
	}
	Super::Deinitialize();
}

void UGTTrackPaintSubsystem::Recentre(const FVector2D& NewOrigin)
{
	const float CellCm = WindowSizeCm / GridSize;
	const float TexelCm = WindowSizeCm / Resolution;
	const FVector2D Shift = NewOrigin - Origin;
	const FIntPoint CellShift(FMath::RoundToInt(Shift.X / CellCm), FMath::RoundToInt(Shift.Y / CellCm));
	const FIntPoint TexelShift(FMath::RoundToInt(Shift.X / TexelCm), FMath::RoundToInt(Shift.Y / TexelCm));

	// Content that was at cell (x + shift, y + shift) is now at (x, y); the rest is fresh ground.
	auto ShiftGrid = [](TArray<float>& Grid, int32 Size, const FIntPoint& By)
	{
		TArray<float> Moved;
		Moved.Init(0.f, Grid.Num());
		for (int32 Y = 0; Y < Size; ++Y)
		{
			const int32 SourceY = Y + By.Y;
			if (SourceY < 0 || SourceY >= Size)
			{
				continue;
			}
			for (int32 X = 0; X < Size; ++X)
			{
				const int32 SourceX = X + By.X;
				if (SourceX >= 0 && SourceX < Size)
				{
					Moved[Y * Size + X] = Grid[SourceY * Size + SourceX];
				}
			}
		}
		Grid = MoveTemp(Moved);
	};
	ShiftGrid(Cells, GridSize, CellShift);
	// MR1: G and B's mirror, on its finer cells (the origin moves by whole R cells, so by whole mud cells too).
	if (MudStampCount > 0)
	{
		const float MudCellCm = WindowSizeCm / MudGridSize;
		const FIntPoint MudShift(FMath::RoundToInt(Shift.X / MudCellCm), FMath::RoundToInt(Shift.Y / MudCellCm));
		ShiftGrid(CoverCells, MudGridSize, MudShift);
		ShiftGrid(WetCells, MudGridSize, MudShift);
	}

	if (bGpuEnabled && RenderTarget)
	{
		UWorld* World = GetWorld();
		if (!ScratchTarget)
		{
			ScratchTarget = UKismetRenderingLibrary::CreateRenderTarget2D(World, Resolution, Resolution, RTF_RGBA16f, FLinearColor::Black);
		}
		UCanvas* Canvas = nullptr;
		FVector2D Size;
		FDrawToRenderTargetContext Context;
		// Old pixel p lands at p - shift: draw the old target into the scratch offset by -shift, then copy back.
		UKismetRenderingLibrary::ClearRenderTarget2D(World, ScratchTarget, FLinearColor::Black);
		UKismetRenderingLibrary::BeginDrawCanvasToRenderTarget(World, ScratchTarget, Canvas, Size, Context);
		if (Canvas)
		{
			Canvas->K2_DrawTexture(RenderTarget, FVector2D(-TexelShift.X, -TexelShift.Y), Size, FVector2D::ZeroVector, FVector2D::UnitVector,
				FLinearColor::White, BLEND_Opaque);
		}
		UKismetRenderingLibrary::EndDrawCanvasToRenderTarget(World, Context);
		UKismetRenderingLibrary::ClearRenderTarget2D(World, RenderTarget, FLinearColor::Black);
		UKismetRenderingLibrary::BeginDrawCanvasToRenderTarget(World, RenderTarget, Canvas, Size, Context);
		if (Canvas)
		{
			Canvas->K2_DrawTexture(ScratchTarget, FVector2D::ZeroVector, Size, FVector2D::ZeroVector, FVector2D::UnitVector,
				FLinearColor::White, BLEND_Opaque);
		}
		UKismetRenderingLibrary::EndDrawCanvasToRenderTarget(World, Context);
	}
	Origin = NewOrigin;
	++RecentreCount;
	WriteCollection();
}

void UGTTrackPaintSubsystem::StampGrid(const FStamp& Stamp)
{
	const float CellCm = WindowSizeCm / GridSize;
	const FVector2D Lo = Origin - FVector2D(WindowSizeCm * 0.5f);
	// The drawn quad is at least one width long; mirror that so a stationary wheel marks a square.
	FVector2D Start = Stamp.Start;
	FVector2D End = Stamp.End;
	const FVector2D Delta = End - Start;
	const float Length = Delta.Size();
	if (Length < Stamp.Width)
	{
		const FVector2D Axis = Length > KINDA_SMALL_NUMBER ? Delta / Length : FVector2D(1.f, 0.f);
		const FVector2D Mid = (Start + End) * 0.5f;
		Start = Mid - Axis * (Stamp.Width * 0.5f);
		End = Mid + Axis * (Stamp.Width * 0.5f);
	}
	// Any cell the streak touches: cell centre within half a width plus half a cell of the segment.
	// That reach means consecutive streaks hit the same cell (Length + 2 Reach) / Length times, so
	// scale the deposit to leave the streak's peak depth in the cell once per pass, like the texels.
	const float Reach = Stamp.Width * 0.5f + CellCm * 0.5f;
	const float QuadLength = FMath::Max(Length, Stamp.Width);
	const float Amount = Stamp.Amount * QuadLength / (QuadLength + 2.f * Reach);
	const FVector2D Min = FVector2D::Min(Start, End) - FVector2D(Reach) - Lo;
	const FVector2D Max = FVector2D::Max(Start, End) + FVector2D(Reach) - Lo;
	if (Max.X < 0.f || Max.Y < 0.f || Min.X >= WindowSizeCm || Min.Y >= WindowSizeCm)
	{
		return;
	}
	const int32 X0 = FMath::Clamp(FMath::FloorToInt(Min.X / CellCm), 0, GridSize - 1);
	const int32 X1 = FMath::Clamp(FMath::FloorToInt(Max.X / CellCm), 0, GridSize - 1);
	const int32 Y0 = FMath::Clamp(FMath::FloorToInt(Min.Y / CellCm), 0, GridSize - 1);
	const int32 Y1 = FMath::Clamp(FMath::FloorToInt(Max.Y / CellCm), 0, GridSize - 1);
	for (int32 Y = Y0; Y <= Y1; ++Y)
	{
		for (int32 X = X0; X <= X1; ++X)
		{
			const FVector2D Centre = Lo + FVector2D((X + 0.5f) * CellCm, (Y + 0.5f) * CellCm);
			if (FVector2D::Distance(Centre, FMath::ClosestPointOnSegment2D(Centre, Start, End)) <= Reach)
			{
				float& Cell = Cells[Y * GridSize + X];
				Cell = FMath::Min(MaxCellDepth, Cell + Amount);
			}
		}
	}
}

void UGTTrackPaintSubsystem::StampBlotGrid(const FBlot& Blot)
{
	// The GPU's value at each cell's centre: the cell's offset from the blot turned into the drawn square's frame (the canvas
	// turns the square's +U axis to (cos a, sin a) in pixels, which are world X, Y), then the tile's mask there.
	const float CellCm = WindowSizeCm / MudGridSize;
	const FVector2D Lo = Origin - FVector2D(WindowSizeCm * 0.5f);
	const float Reach = Blot.HalfCm * UE_SQRT_2;
	const int32 X0 = FMath::Clamp(FMath::FloorToInt((Blot.Centre.X - Reach - Lo.X) / CellCm), 0, MudGridSize - 1);
	const int32 X1 = FMath::Clamp(FMath::FloorToInt((Blot.Centre.X + Reach - Lo.X) / CellCm), 0, MudGridSize - 1);
	const int32 Y0 = FMath::Clamp(FMath::FloorToInt((Blot.Centre.Y - Reach - Lo.Y) / CellCm), 0, MudGridSize - 1);
	const int32 Y1 = FMath::Clamp(FMath::FloorToInt((Blot.Centre.Y + Reach - Lo.Y) / CellCm), 0, MudGridSize - 1);
	if (Blot.Centre.X + Reach < Lo.X || Blot.Centre.Y + Reach < Lo.Y || Blot.Centre.X - Reach > Lo.X + WindowSizeCm || Blot.Centre.Y - Reach > Lo.Y + WindowSizeCm)
	{
		return;
	}
	float S = 0.f;
	float C = 1.f;
	FMath::SinCos(&S, &C, FMath::DegreesToRadians(Blot.AngleDeg));
	const float InvSide = 1.f / FMath::Max(2.f * Blot.HalfCm, KINDA_SMALL_NUMBER);
	for (int32 Y = Y0; Y <= Y1; ++Y)
	{
		for (int32 X = X0; X <= X1; ++X)
		{
			const FVector2D D = Lo + FVector2D((X + 0.5f) * CellCm, (Y + 0.5f) * CellCm) - Blot.Centre;
			const float U = (D.X * C + D.Y * S) * InvSide + 0.5f;
			const float V = (-D.X * S + D.Y * C) * InvSide + 0.5f;
			const float M = SampleBlotMask(Blot.Tile, U, V);
			if (M <= 0.f)
			{
				continue;
			}
			float& Cover = CoverCells[Y * MudGridSize + X];
			float& Wet = WetCells[Y * MudGridSize + X];
			Cover += (Blot.Coverage - Cover) * M;
			Wet += (Blot.Wet - Wet) * M;
		}
	}
}

void UGTTrackPaintSubsystem::FlushStamps()
{
	if (Pending.Num() == 0)
	{
		return;
	}
	for (const FStamp& Stamp : Pending)
	{
		StampGrid(Stamp);
	}
	if (bGpuEnabled && RenderTarget && BrushTexture)
	{
		UWorld* World = GetWorld();
		UCanvas* Canvas = nullptr;
		FVector2D Size;
		FDrawToRenderTargetContext Context;
		UKismetRenderingLibrary::BeginDrawCanvasToRenderTarget(World, RenderTarget, Canvas, Size, Context);
		if (Canvas)
		{
			const float PixelsPerCm = Resolution / WindowSizeCm;
			for (const FStamp& Stamp : Pending)
			{
				// A quad along the travel direction, soft across its width, added into the red channel (MR1: the red channel
				// alone; G and B are the mud's).
				const FVector2D A = WorldToPixel(Stamp.Start);
				const FVector2D B = WorldToPixel(Stamp.End);
				const FVector2D Delta = B - A;
				const float Width = Stamp.Width * PixelsPerCm;
				const FVector2D Extent(FMath::Max(Delta.Size(), Width), Width);
				const float Angle = FMath::RadiansToDegrees(FMath::Atan2(Delta.Y, Delta.X));
				Canvas->K2_DrawTexture(BrushTexture, (A + B) * 0.5f - Extent * 0.5f, Extent, FVector2D::ZeroVector, FVector2D::UnitVector,
					FLinearColor(Stamp.Amount, 0.f, 0.f, 1.f), BLEND_Additive, Angle, FVector2D(0.5f, 0.5f));
			}
		}
		UKismetRenderingLibrary::EndDrawCanvasToRenderTarget(World, Context);
	}
	StampCount += Pending.Num();
	Pending.Reset();
}

void UGTTrackPaintSubsystem::FlushBlots()
{
	if (PendingBlots.Num() == 0)
	{
		return;
	}
	for (const FBlot& Blot : PendingBlots)
	{
		StampBlotGrid(Blot);
	}
	if (bGpuEnabled && RenderTarget && BlotMulTexture && BlotAddTexture)
	{
		UWorld* World = GetWorld();
		UCanvas* Canvas = nullptr;
		FVector2D Size;
		FDrawToRenderTargetContext Context;
		UKismetRenderingLibrary::BeginDrawCanvasToRenderTarget(World, RenderTarget, Canvas, Size, Context);
		if (Canvas)
		{
			const float PixelsPerCm = Resolution / WindowSizeCm;
			const FVector2D TileSize(1.f / AtlasTiles, 1.f / AtlasTiles);
			for (const FBlot& Blot : PendingBlots)
			{
				// G = lerp(G, coverage, mask), B = lerp(B, wet, mask): multiply G and B by 1 - mask (R by 1), then add mask x
				// (0, coverage, wet). Each blot's pair in order (a change of blend mode starts a new batch, so the canvas keeps it).
				const FVector2D Centre = WorldToPixel(Blot.Centre);
				const FVector2D Side(2.f * Blot.HalfCm * PixelsPerCm);
				const FVector2D TilePos((Blot.Tile % AtlasTiles) * TileSize.X, (Blot.Tile / AtlasTiles) * TileSize.Y);
				Canvas->K2_DrawTexture(BlotMulTexture, Centre - Side * 0.5f, Side, TilePos, TileSize, FLinearColor::White, BLEND_Modulate,
					Blot.AngleDeg, FVector2D(0.5f, 0.5f));
				Canvas->K2_DrawTexture(BlotAddTexture, Centre - Side * 0.5f, Side, TilePos, TileSize, FLinearColor(0.f, Blot.Coverage, Blot.Wet, 1.f),
					BLEND_Additive, Blot.AngleDeg, FVector2D(0.5f, 0.5f));
			}
		}
		UKismetRenderingLibrary::EndDrawCanvasToRenderTarget(World, Context);
	}
	MudStampCount += PendingBlots.Num();
	PendingBlots.Reset();
}

void UGTTrackPaintSubsystem::Decay(float FactorR, float FactorG, float FactorB)
{
	if (FactorR != 1.f)
	{
		for (float& Cell : Cells)
		{
			Cell *= FactorR;
		}
	}
	if (FactorG != 1.f || FactorB != 1.f)
	{
		float Most = 0.f;
		for (int32 Index = 0; Index < CoverCells.Num(); ++Index)
		{
			CoverCells[Index] *= FactorG;
			WetCells[Index] *= FactorB;
			Most = FMath::Max(Most, CoverCells[Index]);
		}
		if (Most < 1.e-4f)
		{
			// Nothing left to see: stop the mud's clocks until the next blot (the GPU's last traces are under 1e-4 too).
			FMemory::Memzero(CoverCells.GetData(), CoverCells.Num() * sizeof(float));
			FMemory::Memzero(WetCells.GetData(), WetCells.Num() * sizeof(float));
			MudStampCount = 0;
			CoverTimer = 0.f;
			WetTimer = 0.f;
		}
	}
	if (bGpuEnabled && RenderTarget && WhiteTexture)
	{
		UWorld* World = GetWorld();
		UCanvas* Canvas = nullptr;
		FVector2D Size;
		FDrawToRenderTargetContext Context;
		UKismetRenderingLibrary::BeginDrawCanvasToRenderTarget(World, RenderTarget, Canvas, Size, Context);
		if (Canvas)
		{
			Canvas->K2_DrawTexture(WhiteTexture, FVector2D::ZeroVector, Size, FVector2D::ZeroVector, FVector2D::UnitVector,
				FLinearColor(FactorR, FactorG, FactorB, 1.f), BLEND_Modulate);
		}
		UKismetRenderingLibrary::EndDrawCanvasToRenderTarget(World, Context);
	}
}

UTexture2D* UGTTrackPaintSubsystem::MakeBrush(bool bSoft) const
{
	// Soft brush: constant along U (the streak), fading to the edges along V (across it). White: all ones.
	const int32 Width = 4;
	const int32 Height = bSoft ? 32 : 4;
	UTexture2D* Texture = UTexture2D::CreateTransient(Width, Height, PF_B8G8R8A8);
	Texture->SRGB = false;
	Texture->Filter = TF_Bilinear;
	Texture->AddressX = TA_Clamp;
	Texture->AddressY = TA_Clamp;
	Texture->NeverStream = true;
	FTexture2DMipMap& Mip = Texture->GetPlatformData()->Mips[0];
	uint8* Data = static_cast<uint8*>(Mip.BulkData.Lock(LOCK_READ_WRITE));
	for (int32 Y = 0; Y < Height; ++Y)
	{
		const float Edge = FMath::Abs((Y + 0.5f) / Height - 0.5f) * 2.f;   // 0 centre .. 1 edge
		const float Value = bSoft ? 1.f - FMath::SmoothStep(0.45f, 1.f, Edge) : 1.f;
		const uint8 Byte = static_cast<uint8>(FMath::RoundToInt(Value * 255.f));
		for (int32 X = 0; X < Width; ++X)
		{
			uint8* Pixel = Data + (Y * Width + X) * 4;
			Pixel[0] = Pixel[1] = Pixel[2] = Byte;
			Pixel[3] = 255;
		}
	}
	Mip.BulkData.Unlock();
	Texture->UpdateResource();
	return Texture;
}

UTexture2D* UGTTrackPaintSubsystem::MakeBlotBrush(bool bMultiply) const
{
	// MR1: the atlas mask laid out as the atlas (4 x 4 tiles of GTMudBlots::Size), every byte written (CreateTransient does
	// not zero). B8G8R8A8: [B, G, R, A]. Multiply: R 1, G and B 1 - mask. Add: R 0, G and B the mask.
	const int32 N = GTMudBlots::Size;
	const int32 Side = N * AtlasTiles;
	UTexture2D* Texture = UTexture2D::CreateTransient(Side, Side, PF_B8G8R8A8);
	Texture->SRGB = false;
	Texture->Filter = TF_Bilinear;
	Texture->AddressX = TA_Clamp;
	Texture->AddressY = TA_Clamp;
	Texture->NeverStream = true;
	FTexture2DMipMap& Mip = Texture->GetPlatformData()->Mips[0];
	uint8* Data = static_cast<uint8*>(Mip.BulkData.Lock(LOCK_READ_WRITE));
	for (int32 Tile = 0; Tile < AtlasTiles * AtlasTiles; ++Tile)
	{
		const uint8* M = Tile < GTMudBlots::Count ? GTMudBlots::Masks + Tile * N * N : nullptr;
		const int32 TX = (Tile % AtlasTiles) * N;
		const int32 TY = (Tile / AtlasTiles) * N;
		for (int32 Y = 0; Y < N; ++Y)
		{
			for (int32 X = 0; X < N; ++X)
			{
				const uint8 Mask = M ? M[Y * N + X] : 0;
				uint8* Pixel = Data + ((TY + Y) * Side + TX + X) * 4;
				Pixel[0] = Pixel[1] = bMultiply ? static_cast<uint8>(255 - Mask) : Mask;
				Pixel[2] = bMultiply ? 255 : 0;
				Pixel[3] = 255;
			}
		}
	}
	Mip.BulkData.Unlock();
	Texture->UpdateResource();
	return Texture;
}
