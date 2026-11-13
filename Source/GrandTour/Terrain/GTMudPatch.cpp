#include "Terrain/GTMudPatch.h"

#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTSurfacePhysMaterial.h"   // Benmore B2: a mud zone's rows
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "ProceduralMeshComponent.h"
#include "RHI.h"
#include "HAL/IConsoleManager.h"
#include "ProfilingDebugging/CsvProfiler.h"
#include "Terrain/GTMudSubsystem.h"
#include "Weather/GTWeatherSubsystem.h"
#include "Misc/Crc.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"   // MR5: the mud chunks
#include "PhysicsEngine/BodySetup.h"
#include "Terrain/GTMudChunkData.h"

// LM1, the living field (docs/LIVING_MUD_PLAN.md): the switch, the cycle stat and the CSV timer for Settle.
static TAutoConsoleVariable<int32> CVarMudSettle(
	TEXT("gt.Mud.Settle"), 1,
	TEXT("LM1: 1 the mud fields settle (slump, ooze, smear, the fresh sheen), 0 they stay exactly as the wheels stamped them."),
	ECVF_Default);
// LM2b: the clods' switch, their cycle stat and CSV timer.
static TAutoConsoleVariable<int32> CVarMudClods(
	TEXT("gt.Mud.Clods"), 1,
	TEXT("LM2b: 1 the mud patches spawn and draw clods (bank sites and throw landings), 0 they are hidden and none spawn."),
	ECVF_Default);
// MudRunner MR3 (docs/MUDRUNNER_LESSONS_PLAN.md MR3 item 1): churned rut water.
static TAutoConsoleVariable<int32> CVarMudMuddyWater(
	TEXT("gt.Mud.MuddyWater"), 1,
	TEXT("MR3: 1 a stamp or a throw's landing in a rut pool churns its water brown (the field's Turbidity, TreadTexture A), light-brown froth where it is fresh, settling clear (half-life RutSettleS 45 s); 0 the rut water exactly as before."),
	ECVF_Default);
// MudRunner MR4 (docs/MUDRUNNER_LESSONS_PLAN.md MR4): readable soft spots.
static TAutoConsoleVariable<int32> CVarMudSoftSpots(
	TEXT("gt.Mud.SoftSpots"), 1,
	TEXT("MR4: 1 a bog's patch has soft spots - a static softness S per cell the traction reads (sinkage cap and rate x lerp(0.75, 1.5, S), friction x lerp(1.05, 0.9, S), each normalised to a patch mean of 1) and M_GT_Mud draws (toward the Deep slice, wetter); 0 S is treated as 0.5: today's numbers exactly, the layer's G 0. At once (the patch re-uploads its layer on its tick)."),
	ECVF_Default);
// MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5): breakable mud chunks.
static TAutoConsoleVariable<int32> CVarMudChunks(
	TEXT("gt.Mud.Chunks"), 1,
	TEXT("MR5: 1 a bog's patch has breakable mud chunks - the firm crust where the soft spots' S is low, near the route line: rigid bodies asleep until touched, which a wheel breaks (3-5 clods and a lump dome of the chunk's volume) and the chassis pushes (or breaks over ChunkBreakImpulse); 0 none (the chunks removed, nothing deposited: the field as before). At once (the patch notices on its tick; 1 again places them anew on untouched ground)."),
	ECVF_Default);
// Ground relief GR1 (docs/GROUND_RELIEF_PLAN.md GR1 item 4): a bog's pre-churn at Init.
static TAutoConsoleVariable<int32> CVarMudPreChurn(
	TEXT("gt.Mud.PreChurn"), 1,
	TEXT("GR1: 1 a bog patch whose section has a Deform.PreChurnScale over 0 starts pre-churned - old rut pairs along the route line (the field's own wheel stamp and settle), hummocks, the rim faded; 0 every patch starts flat as before. Read at Init (a patch built after the change)."),
	ECVF_Default);
// GR1b (docs/GROUND_RELIEF_PLAN.md GR1b item 1): what draws the dark lines along the old ruts, a bitmask read at Init on a pre-churned
// patch: 1 the tracks factor cleared, 2 the field smoothed (four 3x3 passes), 4 the lumps cleared. 0 (the default): nothing changed.
static TAutoConsoleVariable<int32> CVarMudPreChurnDebug(
	TEXT("gt.Mud.PreChurnDebug"), 0,
	TEXT("GR1b debug, read at Init on a pre-churned patch (a bitmask): 1 clear the tracks factor (the material's worked/darkened ruts), 2 smooth the field (four 3x3 passes: no crease at a wall foot), 4 clear the lumps. 0 nothing."),
	ECVF_Default);
// LM3a: the snow patches' refill, -1 while the weather snows (the default), 0 never, 1 always (a test hook).
static TAutoConsoleVariable<int32> CVarSnowRefill(
	TEXT("gt.Snow.Refill"), -1,
	TEXT("LM3a: -1 the snow patches refill while the weather snows, 0 never, 1 always (a test hook)."),
	ECVF_Default);
// LM4b item 6: the parallax experiment on M_GT_Snow's detail height (its SnowParallax parameter), -1 the material's own default.
static TAutoConsoleVariable<int32> CVarSnowParallax(
	TEXT("gt.Snow.Parallax"), -1,
	TEXT("LM4b: 1 M_GT_Snow draws the snow detail with parallax occlusion where the edge mask is over 0.2, 0 without, -1 the material's default."),
	ECVF_Default);
// LM4e (docs/LIVING_MUD_PLAN.md LM4e): the snow's cost cuts, each a switch so its saving shows on and off.
static TAutoConsoleVariable<int32> CVarSnowQuietSleep(
	TEXT("gt.Snow.QuietSleep"), 1,
	TEXT("LM4e cut 1: 1 a snow patch's settle keeps no fresh sheen (M_GT_Snow draws none), so its tiles sleep as soon as they are still; 0 as before (the sheen's 6 s fade keeps them awake)."),
	ECVF_Default);
static TAutoConsoleVariable<int32> CVarSnowFastMaterial(
	TEXT("gt.Snow.FastMaterial"), -1,
	TEXT("LM4e cut 6 / LM4f item 2: M_GT_Snow's SnowFastPath. 2 (LM4f) as 1, and the detail map top-down only under 30 deg, only where the edge mask E is over 0.05, one tiling under E 0.2, the glint fading out over 12-20 m and the subsurface over 20-35 m; 1 (LM4e) the scrape streaks' noise only where they show; 0 the full material; -1 the material's own default (2)."),
	ECVF_Default);
// LM4f item 1 (docs/LIVING_MUD_PLAN.md LM4f): the snow chunks' shadows from a 25 cm shadow-only mesh per chunk.
static TAutoConsoleVariable<int32> CVarSnowShadowProxy(
	TEXT("gt.Snow.ShadowProxy"), 1,
	TEXT("LM4f item 1: 1 a snow patch's chunks cast no shadow and a hidden 25 cm mesh per chunk (the same material, so the same displacement) casts it instead; 0 the chunks cast their own (LM4e). Needs gt.Snow.MeshLod 1; at once."),
	ECVF_Default);
static TAutoConsoleVariable<int32> CVarSnowFastSweep(
	TEXT("gt.Snow.FastSweep"), 1,
	TEXT("LM4e cut 3: 1 a snow patch's settle passes over the pairs under the smallest talus before their talus is looked up (exact) and keeps no smear (not drawn on snow); 0 as before."),
	ECVF_Default);
static TAutoConsoleVariable<int32> CVarSnowMeshLod(
	TEXT("gt.Snow.MeshLod"), 1,
	TEXT("LM4e cut 4: 1 a snow patch's mesh is built in chunks with distance LODs (6.25 cm near, 12.5 and 25 cm further out, skirts at the chunks' edges), 0 as one grid at the field's cell. Read when the mesh is built (restart Play)."),
	ECVF_Default);
static TAutoConsoleVariable<int32> CVarSnowUploadTiles(
	TEXT("gt.Snow.UploadTiles"), 1,
	TEXT("LM4e cut 2: 1 a snow patch uploads its changed cells as one box per settle tile, 0 as one box round all of them (as before)."),
	ECVF_Default);
DECLARE_CYCLE_STAT(TEXT("GT Mud Settle"), STAT_GTMudSettle, STATGROUP_Game);
DECLARE_CYCLE_STAT(TEXT("GT Mud Clods"), STAT_GTMudClods, STATGROUP_Game);
DECLARE_CYCLE_STAT(TEXT("GT Mud Upload"), STAT_GTMudUpload, STATGROUP_Game);
// LM4e: the stamps' time (the traction's stamps and plough, the throw's landings: timed in the field, outermost calls) and the
// work counts, in stat game beside the cycle stats.
DECLARE_FLOAT_COUNTER_STAT(TEXT("GT Mud Stamp ms"), STAT_GTMudStampMs, STATGROUP_Game);
DECLARE_DWORD_COUNTER_STAT(TEXT("GT Mud Swept Tiles"), STAT_GTMudSweptTiles, STATGROUP_Game);
DECLARE_DWORD_COUNTER_STAT(TEXT("GT Mud Upload Cells"), STAT_GTMudUploadCells, STATGROUP_Game);
DECLARE_DWORD_COUNTER_STAT(TEXT("GT Snow Drawn Triangles"), STAT_GTSnowDrawnTriangles, STATGROUP_Game);
CSV_DEFINE_CATEGORY(GTMud, true);

AGTMudPatch::AGTMudPatch()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Mesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(RootComponent);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	// Stage D: this mesh is the ground over the patch (the landscape has a hole under it and casts nothing there), so it
	// has to cast the ground's shadow.
	Mesh->SetCastShadow(true);
	Mesh->bUseAsyncCooking = false;
	// The displacement's range goes into the section's own box in BuildMesh (-DisplaceDownCm to +DisplaceUpCm), which is
	// exact; a bounds scale would inflate the 69 x 36 m footprint sideways for the same Z.
	Mesh->BoundsScale = 1.f;
	// Stage G: the water sheet over the same grid. Translucent, so it is sorted after the mud mesh (which is masked, and
	// so opaque: this only orders it against other translucency) and casts nothing - water in a rut does not shadow the
	// rut. No collision either: the wheels sweep the landscape and the depth is read from the field.
	WaterMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("WaterMesh"));
	WaterMesh->SetupAttachment(RootComponent);
	WaterMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	WaterMesh->SetCastShadow(false);
	WaterMesh->bUseAsyncCooking = false;
	WaterMesh->BoundsScale = 1.f;
	WaterMesh->SetTranslucentSortPriority(1);
}

const FGTDeformProfile* AGTMudPatch::ApplySection(const FGTTerrainSpec& Spec, const FGTRouteSection& Section)
{
	// Stage G: the section owns its water table, so it is set before Init (which builds both grids); then the variant (LM5b)
	// and the profile (RIVERBED S4), whose water-table offset (LM5b) lands on the section's table.
	WaterTableCm = Section.WaterTableCm;
	MudVariant = Section.Kind == EGTRouteSectionKind::Mud ? Section.MudVariant : EGTMudVariant::Standard;
	const FGTDeformProfile* Profile = GTTerrain::DeformProfileFor(Spec, Section);
	if (Profile)
	{
		ApplyProfile(*Profile);
	}
	// GR1: the section's own pre-churn number whatever its Deform's Mode (a ByKind bog has no profile of its own, or a variant's
	// static one); PreChurn reads it only on a Mud-medium bog patch.
	PreChurnScale = FMath::Max(0.f, Section.Deform.PreChurnScale);
	// MRD1: the mud road's layout, spray and debris numbers, likewise whatever the Mode.
	PreChurnStyle = Section.Deform.PreChurnStyle;
	MudRoadSprayScale = FMath::Max(0.f, Section.Deform.MudRoadSprayScale);
	RoadDebrisPerM2 = FMath::Max(0.f, Section.Deform.RoadDebrisPerM2);
	RoadSiltTileMul = FMath::Max(0.25f, Section.Deform.RoadSiltTileMul);   // MRD1b item 3
	RoadSiltStrength = FMath::Clamp(Section.Deform.RoadSiltStrength, 0.f, 1.f);
	return Profile;
}

void AGTMudPatch::ApplyProfile(const FGTDeformProfile& Profile)
{
	ProfileSurfaceMaterialPath = Profile.SurfaceMaterialPath;
	// Deformable gravel DG1: the loose stones' density (0 on every profile but gravel's).
	GravelStonesPerM2 = FMath::Max(0.f, Profile.GravelStonesPerM2);
	TextureSlideScale = FMath::Max(0.f, Profile.TextureSlideScale);   // DG1b
	// LM5b: the variant's scales, and the water table moved by its offset (the identity on every other profile).
	MaxSinkageScale = FMath::Max(0.f, Profile.MaxSinkageScale);
	SinkageRateScale = FMath::Max(0.f, Profile.SinkageRateScale);
	FrictionScale = FMath::Max(0.f, Profile.FrictionScale);
	WaterTableCm += Profile.WaterTableOffsetCm;
	if (Profile.bScalesRows)
	{
		// LM5b: a mud variant stays a bog - its rows and their Mud/Bog tag gate (bHasProfile false), every number the bog's
		// but these three (MudVariantDefaults starts them from the bog's own, so a number the variant leaves out is unchanged).
		RecoverShare = Profile.RecoverShare;
		LumpShare = Profile.LumpShare;
		ThrowMax = Profile.ThrowMax;
		// MR4: and the soft spots' amplitude (a profiled patch has none, so only here).
		SoftSpotAmplitude = FMath::Max(0.f, Profile.SoftSpotAmplitude);
		// MR5: and the chunks' density multiplier (a profiled patch has no chunks either).
		MudChunkDensityScale = FMath::Max(0.f, Profile.ChunkDensityScale);
		return;
	}
	// RIVERBED S4: the sinkage numbers the traction reads for a wheel inside the box, and the ridge numbers Init pushes
	// into the field (the WaterTableCm pattern: set on the patch, then Init).
	bHasProfile = true;
	ProfileSinkageRate = FMath::Max(0.f, Profile.SinkageRate);
	ProfileMaxSinkageM = FMath::Max(0.f, Profile.MaxSinkageM);
	RidgeBlend = Profile.RidgeBlend;
	RidgeSmooth = Profile.RidgeSmooth;
	RidgeNoise = Profile.RidgeNoise;
	FloorNoiseCm = Profile.FloorNoiseCm;
	RidgeWidthCm = Profile.RidgeWidthCm;
	MaxRidgeCm = Profile.MaxRidgeCm;
	RidgeFootCm = Profile.RidgeFootCm;
	RidgeWaveCm = Profile.RidgeWaveCm;
	RidgeWaveLongCm = Profile.RidgeWaveLongCm;
	RidgeWave = Profile.RidgeWave;
	RidgeWidthWave = Profile.RidgeWidthWave;
	RidgeSideBias = Profile.RidgeSideBias;
	RidgeSlump = Profile.RidgeSlump;
	RidgeSlumpFloor = Profile.RidgeSlumpFloor;
	RidgeSlumpRiseMaxCm = Profile.RidgeSlumpRiseMaxCm;
	RidgeFillShare = Profile.RidgeFillShare;
	ClodChance = Profile.ClodChance;
	ClodMinCm = Profile.ClodMinCm;
	ClodMaxCm = Profile.ClodMaxCm;
	// LM1: the settle numbers (a ford's bed is stiffer than the bog by default).
	ReposeDeg = Profile.ReposeDeg;
	SlumpRate = Profile.SlumpRate;
	OozeRate = Profile.OozeRate;
	RecoverShare = Profile.RecoverShare;
	CreepCmPerCm = Profile.CreepCmPerCm;
	SetSeconds = Profile.SetSeconds;
	SmearCmPerCm = Profile.SmearCmPerCm;
	FreshFadeS = Profile.FreshFadeS;
	SleepCmPerS = Profile.SleepCmPerS;
	// LM2a: the fresh threshold, the lumps and the throw.
	FreshMinCm = Profile.FreshMinCm;
	LumpShare = Profile.LumpShare;
	LumpSpacingCells = Profile.LumpSpacingCells;
	LumpRadiusCells = Profile.LumpRadiusCells;
	LumpMaxCm = Profile.LumpMaxCm;
	ThrowMax = Profile.ThrowMax;
	// LM3a housekeeping 3: the variety, profile-owned (the defaults are LM2c's, so a ford's bed is unchanged).
	LumpAbsentShare = Profile.LumpAbsentShare;
	LumpClusterCm = Profile.LumpClusterCm;
	LumpAmpMin = Profile.LumpAmpMin;
	LumpAmpMax = Profile.LumpAmpMax;
	LumpAspectMax = Profile.LumpAspectMax;
	LumpVarietyRadiusJitter = Profile.LumpVarietyRadiusJitter;
	LumpSatelliteChance = Profile.LumpSatelliteChance;
	ClodBankPerCm = Profile.ClodBankPerCm;
	ClodThrowChance = Profile.ClodThrowChance;
	// LM3a: the field's own numbers before LM3a (the defaults are the field's, so a ford's bed is unchanged), and snow.
	RidgeReturn = Profile.RidgeReturn;
	RutShoulderCm = Profile.RutShoulderCm;
	RutShoulderMinCells = Profile.RutShoulderMinCells;
	RutDepthVariation = Profile.RutDepthVariation;
	Medium = Profile.Medium;
	SnowDepthCm = Profile.SnowDepthCm;
	SnowEdgeCm = Profile.SnowEdgeCm;
	PloughReturn = Profile.PloughReturn;
	PloughBandCm = Profile.PloughBandCm;
	PloughLumpShare = Profile.PloughLumpShare;
	PloughBankVariation = Profile.PloughBankVariation;
	RefillCmPerMin = Profile.RefillCmPerMin;
	SnowPlough = Profile.SnowPlough;
	SnowBellyDrag = Profile.SnowBellyDrag;
	// LM4: the cell-unit numbers (item 1), the plates (2), the stepped wall and its drops (3), the bank clods' sizes (4) and
	// the uneven snow top (6). The defaults are mud's, so a ford's bed is unchanged. The cell itself is the subsystem's to
	// pass to Init (the profile's CellCm, or 12.5 with gt.Snow.FineGrid 0).
	RidgeNoiseCells = Profile.RidgeNoiseCells;
	SettleTileCells = Profile.SettleTileCells;
	FloorNoiseCells = Profile.FloorNoiseCells;
	PocketNoiseCells = Profile.PocketNoiseCells;
	TracksEdgeCells = Profile.TracksEdgeCells;
	bLumpPlates = Profile.bLumpPlates;
	PlateTiltMinDeg = Profile.PlateTiltMinDeg;
	PlateTiltMaxDeg = Profile.PlateTiltMaxDeg;
	WallStepMinCm = Profile.WallStepMinCm;
	WallStepMaxCm = Profile.WallStepMaxCm;
	WallSegMinCm = Profile.WallSegMinCm;
	WallSegMaxCm = Profile.WallSegMaxCm;
	WallDropShare = Profile.WallDropShare;
	FloorChunkChance = Profile.FloorChunkChance;
	SnowTopUndulationCm = Profile.SnowTopUndulationCm;
	SnowTopWaveMinCm = Profile.SnowTopWaveMinCm;
	SnowTopWaveMaxCm = Profile.SnowTopWaveMaxCm;
	ClodBankSizeMinCm = Profile.ClodBankSizeMinCm;
	ClodBankSizeMaxCm = Profile.ClodBankSizeMaxCm;
	ClodSizePower = Profile.ClodSizePower;
	// LM4b: the continuous wall line, the notch's feather and the soft domes (off by default: mud's).
	WallWaveCm = Profile.WallWaveCm;
	WallWaveLongCm = Profile.WallWaveLongCm;
	WallWaveAmpCm = Profile.WallWaveAmpCm;
	WallWaveLongAmpCm = Profile.WallWaveLongAmpCm;
	WallDropFeatherCells = Profile.WallDropFeatherCells;
	bLumpSoftDomes = Profile.bLumpSoftDomes;
	LumpSkewMinDeg = Profile.LumpSkewMinDeg;
	LumpSkewMaxDeg = Profile.LumpSkewMaxDeg;
	LumpHeightPerRadius = Profile.LumpHeightPerRadius;
	LumpCapAmpPower = Profile.LumpCapAmpPower;
	LumpCapRadiusPower = Profile.LumpCapRadiusPower;
	// LM4c: the talus per cell, the delayed wall collapses, the berm in piles (off by default: mud's).
	bCellRepose = Profile.bCellRepose;
	LooseReposeDeg = Profile.LooseReposeDeg;
	WallReposeDeg = Profile.WallReposeDeg;
	WallReposeRangeDeg = Profile.WallReposeRangeDeg;
	WallReposeWaveMinCm = Profile.WallReposeWaveMinCm;
	WallReposeWaveMaxCm = Profile.WallReposeWaveMaxCm;
	CollapseChance = Profile.CollapseChance;
	CollapseSegMinCm = Profile.CollapseSegMinCm;
	CollapseSegMaxCm = Profile.CollapseSegMaxCm;
	CollapseDelayMinS = Profile.CollapseDelayMinS;
	CollapseDelayMaxS = Profile.CollapseDelayMaxS;
	CollapseTopMin = Profile.CollapseTopMin;
	CollapseTopMax = Profile.CollapseTopMax;
	CollapseFeatherCells = Profile.CollapseFeatherCells;
	CollapseClumpsMin = Profile.CollapseClumpsMin;
	CollapseClumpsMax = Profile.CollapseClumpsMax;
	bPloughFallingProfile = Profile.bPloughFallingProfile;
	PileClusterMin = Profile.PileClusterMin;
	PileClusterMax = Profile.PileClusterMax;
	PileWaveMinCm = Profile.PileWaveMinCm;
	PileWaveMaxCm = Profile.PileWaveMaxCm;
	// LM4d: the belly's channel (off by default).
	BellyUndulationCm = Profile.BellyUndulationCm;
	BellyWaveMinCm = Profile.BellyWaveMinCm;
	BellyWaveMaxCm = Profile.BellyWaveMaxCm;
	BellyStretch = Profile.BellyStretch;
	SmearChance = Profile.SmearChance;
	SmearLaneCm = Profile.SmearLaneCm;
	SmearLengthMinCm = Profile.SmearLengthMinCm;
	SmearLengthMaxCm = Profile.SmearLengthMaxCm;
	SmearWidthMinCm = Profile.SmearWidthMinCm;
	SmearWidthMaxCm = Profile.SmearWidthMaxCm;
	SmearHeightMinCm = Profile.SmearHeightMinCm;
	SmearHeightMaxCm = Profile.SmearHeightMaxCm;
	SmearClusterCm = Profile.SmearClusterCm;
	PloughSpillShare = Profile.PloughSpillShare;
	SpillClumpChance = Profile.SpillClumpChance;
}

void AGTMudPatch::ScaleCellUnits(float Factor)
{
	// LM4 item 1 (gt.Snow.FineGrid 0): FGTDeformProfile::ScaleCellUnits' list, on the patch's copies.
	WallDropFeatherCells *= Factor;   // LM4b
	CollapseFeatherCells *= Factor;   // LM4c
	RidgeNoiseCells *= Factor;
	LumpSpacingCells *= Factor;
	LumpRadiusCells *= Factor;
	RutShoulderMinCells *= Factor;
	SettleTileCells = FMath::Max(1, FMath::RoundToInt(SettleTileCells * Factor));
	FloorNoiseCells *= Factor;
	PocketNoiseCells *= Factor;
	TracksEdgeCells *= Factor;
}

void AGTMudPatch::ResetFieldForTest()
{
	if (!Field.IsValid())
	{
		return;
	}
	// FGTMudField::Init clears the arrays and keeps every number the patch pushed in.
	Field.Init(Field.Bounds(), Field.CellCm);
	Upload(FIntRect(0, 0, Field.SizeX, Field.SizeY));
	// LM2a/LM2b: the throw's and the clods' readouts start afresh with the field, and every clod goes.
	for (int32 Slot = 0; Slot < Clods.Num(); ++Slot)
	{
		if (Clods[Slot].bAlive)
		{
			RemoveClod(Slot);
		}
	}
	ClodNext = 0;
	bClodDirtyCells = false;
	ThrowDepositedCm3 = 0.0;
	ThrowDeposits = 0;
	ClodsFromBank = ClodsFromThrow = ClodsFromTest = ClodsSquashed = ClodsSunk = ClodsRecycled = ClodsDropped = 0;
	ClodsFromFloor = 0;   // LM4
	ClodsFromChannel = 0;   // LM4d
	ClodBatchAccumS = 1.f;   // the dead transforms go up on the next tick
}

// ---- LM4e, the record and the replay --------------------------------------------------------------------------------

void AGTMudPatch::Record(uint8 Kind, std::initializer_list<double> Values, uint8 Flag)
{
	if (!Field.EventLog)
	{
		return;
	}
	FGTMudField::FEvent Event;
	Event.Kind = Kind;
	Event.Flag = Flag;
	int32 K = 0;
	for (const double Value : Values)
	{
		if (K < 10)
		{
			Event.V[K++] = Value;
		}
	}
	Field.EventLog->Add(Event);
}

void AGTMudPatch::SetRecording(bool bOn)
{
	if (bOn)
	{
		// A reset field and the clod roll's stream from its start, then every outside call from the next one on.
		ReplayLog.Reset();
		ReplayCursor = 0;
		ResetFieldForTest();
		ClodRandom.Initialize(0xC10D + SectionIndex);
		RecordLog.Reset();
		Field.EventLog = &RecordLog;
	}
	else if (Field.EventLog)
	{
		Field.EventLog = nullptr;
		RecordEndCrc = FieldCrc();
	}
}

uint32 AGTMudPatch::FieldCrc() const
{
	const uint32 Crc = FCrc::MemCrc32(Field.HeightCm.GetData(), Field.HeightCm.Num() * sizeof(float));
	return FCrc::MemCrc32(Field.LumpCm.GetData(), Field.LumpCm.Num() * sizeof(float), Crc);
}

void AGTMudPatch::ReplayEvent(const FGTMudField::FEvent& Event)
{
	const double* V = Event.V;
	switch (Event.Kind)
	{
	case FGTMudField::EventStampWheel:
	{
		double Thrown = 0.0;
		Field.StampWheel(FVector2D(V[0], V[1]), FVector2D(V[2], V[3]), static_cast<float>(V[4]), static_cast<float>(V[5]), FVector2D(V[6], V[7]),
			static_cast<float>(V[8]), static_cast<float>(V[9]), Thrown);
		break;
	}
	case FGTMudField::EventPloughBelly:
		Field.PloughBelly(FVector2D(V[0], V[1]), FVector2D(V[2], V[3]), static_cast<float>(V[4]), static_cast<float>(V[5]), static_cast<float>(V[6]));
		break;
	case FGTMudField::EventStampBelly:
		Field.StampBelly(FVector2D(V[0], V[1]), FVector2D(V[2], V[3]), static_cast<float>(V[4]), static_cast<float>(V[5]), static_cast<float>(V[6]));
		break;
	case FGTMudField::EventThrow:
		DepositThrown(FVector2D(V[0], V[1]), V[2], static_cast<float>(V[3]));
		break;
	case FGTMudField::EventClock:
		Field.AdvanceClock(static_cast<float>(V[0]));
		Field.bQueueClods = Event.Flag != 0;
		break;
	case FGTMudField::EventSettle:
		LastSettleSteps = Field.Settle(static_cast<float>(V[0]));
		break;
	case FGTMudField::EventRefill:
		Field.Refill(static_cast<float>(V[0]));
		break;
	case FGTMudField::EventChunk:   // MR5: a chunk's break, its dome alone (its clods are not the field's)
		Field.DepositLump(FVector2D(V[0], V[1]), V[2], static_cast<float>(V[4]));
		break;
	default:
		break;
	}
}

int32 AGTMudPatch::StartReplay(bool bAllAtOnce)
{
	if (Field.EventLog)
	{
		SetRecording(false);
	}
	ResetFieldForTest();
	ClodRandom.Initialize(0xC10D + SectionIndex);
	ReplayLog = RecordLog;
	ReplayCursor = 0;
	if (!bAllAtOnce)
	{
		return ReplayLog.Num();
	}
	// Every frame now: its events, then its dirty cells to the clods' re-snap and its clod batch, as the tick has them.
	FIntRect Union;
	bool bAny = false;
	while (ReplayCursor < ReplayLog.Num())
	{
		const FGTMudField::FEvent Event = ReplayLog[ReplayCursor++];
		ReplayEvent(Event);
		if (Event.Kind != FGTMudField::EventFrame)
		{
			continue;
		}
		FIntRect Rect;
		if (Field.TakeDirty(Rect))
		{
			if (bAny)
			{
				Union.Union(Rect);
			}
			else
			{
				Union = Rect;
				bAny = true;
			}
			if (bClodDirtyCells)
			{
				ClodDirtyCells.Union(Rect);
			}
			else
			{
				ClodDirtyCells = Rect;
				bClodDirtyCells = true;
			}
		}
		UpdateClods(static_cast<float>(Event.V[0]), Event.V[1] > 0.5);
	}
	Field.StampMs = 0.0;
	if (bAny)
	{
		Upload(Union);
	}
	return ReplayLog.Num();
}

void AGTMudPatch::Init(int32 InSectionIndex, const FBox2D& BoundsCm, float CellCm, const TFunction<float(const FVector2D&)>& SnowDepthAt)
{
	SectionIndex = InSectionIndex;
	// LM3a: the medium and the snow's numbers go in before the field is built (Init lays the snow top for them).
	Field.bSnow = IsSnow();
	Field.SnowDepthCm = FMath::Max(0.f, SnowDepthCm);
	Field.SnowEdgeCm = FMath::Max(1.f, SnowEdgeCm);
	Field.SnowDepthCell.Reset();
	// LM4: the settle tile and the snow top's undulation also go in before the field is built (Init lays the tiles and the top).
	Field.SettleTileCells = FMath::Max(1, SettleTileCells);
	Field.SnowTopUndulationCm = FMath::Max(0.f, SnowTopUndulationCm);
	Field.SnowTopWaveMinCm = FMath::Max(5.f, SnowTopWaveMinCm);
	Field.SnowTopWaveMaxCm = FMath::Max(Field.SnowTopWaveMinCm, SnowTopWaveMaxCm);
	Field.Init(BoundsCm, CellCm);
	// LM4 item 1: the mesh follows the field's cell (mud's 12.5 as before; snow's 6.25).
	FieldCellCm = Field.CellCm;
	MeshCellCm = Field.CellCm;
	if (IsSnow() && SnowDepthAt)
	{
		Field.BuildSnow(SnowDepthAt);   // the section's drifts, per cell
	}
	BoundsMin = Field.Bounds().Min;
	BoundsMax = Field.Bounds().Max;
	CellsX = Field.SizeX;
	CellsY = Field.SizeY;
	SetActorLocation(FVector(BoundsMin.X, BoundsMin.Y, 0.f));
	Field.LugPeriodCm = FMath::Max(1.f, LugPeriodCm);
	// Stage H's shape numbers live here as properties and are pushed in, as LugPeriodCm is.
	Field.RidgeBlend = FMath::Clamp(RidgeBlend, 0.f, 1.f);
	Field.RidgeSmooth = FMath::Clamp(RidgeSmooth, 0.f, 1.f);
	Field.RidgeNoise = FMath::Max(0.f, RidgeNoise);
	Field.RidgeNoiseCells = FMath::Max(1.f, RidgeNoiseCells);   // LM4 item 1: the profile's (mud's 4, snow's 8 at 6.25 cm)
	Field.FloorNoiseCm = FMath::Max(0.f, FloorNoiseCm);
	// Stage I's shape numbers, the same way.
	Field.RidgeWidthCm = FMath::Max(1.f, RidgeWidthCm);
	Field.MaxRidgeCm = FMath::Max(1.f, MaxRidgeCm);
	Field.RidgeFootCm = FMath::Max(1.f, RidgeFootCm);
	Field.RidgeFillShare = FMath::Clamp(RidgeFillShare, 0.f, 1.f);
	Field.RidgeWaveCm = FMath::Max(1.f, RidgeWaveCm);
	Field.RidgeWaveLongCm = FMath::Max(1.f, RidgeWaveLongCm);
	Field.RidgeWave = FMath::Max(0.f, RidgeWave);
	Field.RidgeWidthWave = FMath::Clamp(RidgeWidthWave, 0.f, 1.f);
	Field.RidgeSideBias = FMath::Clamp(RidgeSideBias, 0.f, 0.9f);
	Field.RidgeSlump = FMath::Clamp(RidgeSlump, 0.f, 1.f);
	Field.RidgeSlumpFloor = FMath::Clamp(RidgeSlumpFloor, 0.f, 1.f);
	Field.RidgeSlumpRiseMaxCm = FMath::Max(0.f, RidgeSlumpRiseMaxCm);
	Field.ClodChance = FMath::Clamp(ClodChance, 0.f, 1.f);
	Field.ClodMinCm = FMath::Max(0.f, ClodMinCm);
	Field.ClodMaxCm = FMath::Max(Field.ClodMinCm, ClodMaxCm);
	// LM3a housekeeping 3: the field's own numbers before LM3a, the patch's (and a profile's) now, pushed the same way.
	Field.RidgeReturn = FMath::Clamp(RidgeReturn, 0.f, 1.f);
	Field.RutShoulderCm = FMath::Max(1.f, RutShoulderCm);
	Field.RutShoulderMinCells = FMath::Max(0.5f, RutShoulderMinCells);
	Field.RutDepthVariation = FMath::Clamp(RutDepthVariation, 0.f, 0.5f);
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: mud shape - RidgeReturn %.2f over RidgeWidthCm %.0f (band to %.0f with the wave) capped at %.0f, ")
		TEXT("plateau foot %.0f cm (a cell that is already a rut takes RidgeFillShare %.2f of a bank), RidgeBlend %.2f, RidgeSmooth %.2f, RidgeNoise %.2f over %.0f cells, FloorNoiseCm %.2f; ")
		TEXT("stage I: RidgeWave %.2f at %.0f and %.0f cm (width swing %.2f), RidgeSideBias %.2f, RidgeSlump %.2f (floor share %.2f, at most %.1f cm), ClodChance %.2f at %.0f-%.0f cm"),
		InSectionIndex, Field.RidgeReturn, Field.RidgeWidthCm, Field.RidgeBandCm(), Field.MaxRidgeCm, Field.RidgeFootCm, Field.RidgeFillShare,
		Field.RidgeBlend, Field.RidgeSmooth, Field.RidgeNoise, Field.RidgeNoiseCells, Field.FloorNoiseCm,
		Field.RidgeWave, Field.RidgeWaveCm, Field.RidgeWaveLongCm, Field.RidgeWidthWave, Field.RidgeSideBias, Field.RidgeSlump,
		Field.RidgeSlumpFloor, Field.RidgeSlumpRiseMaxCm, Field.ClodChance, Field.ClodMinCm, Field.ClodMaxCm);
	// LM1: the living field's numbers, the same way.
	Field.ReposeDeg = FMath::Clamp(ReposeDeg, 1.f, 89.f);
	Field.SlumpRate = FMath::Max(0.f, SlumpRate);
	Field.OozeRate = FMath::Max(0.f, OozeRate);
	Field.RecoverShare = FMath::Clamp(RecoverShare, 0.f, 0.99f);
	Field.CreepCmPerCm = FMath::Max(0.f, CreepCmPerCm);
	Field.SetSeconds = FMath::Max(0.f, SetSeconds);
	Field.SmearCmPerCm = FMath::Max(0.f, SmearCmPerCm);
	Field.FreshFadeS = FMath::Max(0.01f, FreshFadeS);
	Field.SleepCmPerS = FMath::Max(0.f, SleepCmPerS);
	// LM2a: the fresh threshold and the lumps, the same way; LM2b's bank-clod numbers ride in the field (it rolls them).
	Field.FreshMinCm = FMath::Max(0.f, FreshMinCm);
	Field.LumpShare = FMath::Clamp(LumpShare, 0.f, 1.f);
	Field.LumpSpacingCells = FMath::Max(1.f, LumpSpacingCells);
	Field.LumpRadiusCells = FMath::Max(0.5f, LumpRadiusCells);
	Field.LumpMaxCm = FMath::Max(0.f, LumpMaxCm);
	Field.ClodBankChance = FMath::Clamp(ClodBankChance, 0.f, 1.f);
	Field.ClodRespawnS = FMath::Max(0.f, ClodRespawnS);
	Field.ClodBankMinCm = FMath::Max(0.01f, ClodBankMinCm);
	Field.ClodBankMinSizeCm = FMath::Max(1.f, ClodBankMinSizeCm);
	Field.ClodBankMaxSizeCm = FMath::Max(Field.ClodBankMinSizeCm, ClodBankMaxSizeCm);
	// LM2c: the variety (lump sites, domes, satellites, the lip's bank clods), the field's own LM2c numbers otherwise.
	Field.bLumpVariety = bLumpVariety;
	Field.ClodBankPerCm = FMath::Max(0.f, ClodBankPerCm);
	Field.ClodBankInner = FMath::Clamp(ClodBankInner, 0.f, 1.f);
	Field.ClodBankSizeMinCm = FMath::Max(1.f, ClodBankSizeMinCm);
	Field.ClodBankSizeMaxCm = FMath::Max(Field.ClodBankSizeMinCm, ClodBankSizeMaxCm);
	Field.ClodSizePower = FMath::Max(0.1f, ClodSizePower);
	// LM3a housekeeping 3: LM2c's lump numbers, profile-owned (the field's LM2c values by default).
	Field.LumpAbsentShare = FMath::Clamp(LumpAbsentShare, 0.f, 0.95f);
	Field.LumpClusterCm = FMath::Max(1.f, LumpClusterCm);
	Field.LumpAmpMin = FMath::Max(0.f, LumpAmpMin);
	Field.LumpAmpMax = FMath::Max(Field.LumpAmpMin, LumpAmpMax);
	Field.LumpAspectMax = FMath::Max(1.f, LumpAspectMax);
	Field.LumpVarietyRadiusJitter = FMath::Clamp(LumpVarietyRadiusJitter, 0.f, 0.95f);
	Field.LumpSatelliteChance = FMath::Clamp(LumpSatelliteChance, 0.f, 1.f);
	// LM3a, snow: the belly's plough and the refill; the materials and the render bounds for the deeper cut.
	Field.PloughReturn = FMath::Clamp(PloughReturn, 0.f, 1.f);
	Field.PloughBandCm = FMath::Max(1.f, PloughBandCm);
	Field.PloughLumpShare = FMath::Clamp(PloughLumpShare, 0.f, 1.f);
	Field.PloughBankVariation = FMath::Max(0.f, PloughBankVariation);
	Field.RefillCmPerMin = FMath::Max(0.f, RefillCmPerMin);
	// LM4: the cell-unit numbers (item 1), the plates (2), the stepped wall (3), the shards' sizes ride in ClodBankSize* above.
	Field.FloorNoiseCells = FMath::Max(1.f, FloorNoiseCells);
	Field.PocketNoiseCells = FMath::Max(1.f, PocketNoiseCells);
	Field.TracksEdgeCells = FMath::Max(1.f, TracksEdgeCells);
	Field.bLumpPlates = IsSnow() && bLumpPlates;
	Field.PlateTiltMinDeg = FMath::Clamp(PlateTiltMinDeg, 0.f, 80.f);
	Field.PlateTiltMaxDeg = FMath::Clamp(PlateTiltMaxDeg, Field.PlateTiltMinDeg, 80.f);
	Field.WallStepMinCm = FMath::Max(0.f, WallStepMinCm);
	Field.WallStepMaxCm = FMath::Max(Field.WallStepMinCm, WallStepMaxCm);
	Field.WallSegMinCm = FMath::Max(1.f, WallSegMinCm);
	Field.WallSegMaxCm = FMath::Max(Field.WallSegMinCm, WallSegMaxCm);
	Field.WallDropShare = FMath::Clamp(WallDropShare, 0.f, 1.f);
	Field.FloorChunkChance = FMath::Clamp(FloorChunkChance, 0.f, 1.f);
	// LM4b: the continuous wall line, the notch's feather and the soft domes (snow only).
	Field.WallWaveCm = FMath::Max(1.f, WallWaveCm);
	Field.WallWaveLongCm = FMath::Max(1.f, WallWaveLongCm);
	Field.WallWaveAmpCm = FMath::Max(0.f, WallWaveAmpCm);
	Field.WallWaveLongAmpCm = FMath::Max(0.f, WallWaveLongAmpCm);
	Field.WallDropFeatherCells = FMath::Max(0.f, WallDropFeatherCells);
	Field.bLumpSoftDomes = IsSnow() && bLumpSoftDomes && !bLumpPlates;
	Field.LumpSkewMinDeg = FMath::Clamp(LumpSkewMinDeg, 0.f, 45.f);
	Field.LumpSkewMaxDeg = FMath::Clamp(LumpSkewMaxDeg, Field.LumpSkewMinDeg, 45.f);
	Field.LumpHeightPerRadius = FMath::Max(0.f, LumpHeightPerRadius);
	Field.LumpCapAmpPower = FMath::Max(0.f, LumpCapAmpPower);
	Field.LumpCapRadiusPower = FMath::Max(0.f, LumpCapRadiusPower);
	// LM4c: the talus per cell, the delayed wall collapses and the berm in piles (snow only; mud keeps them off).
	Field.bCellRepose = IsSnow() && bCellRepose;
	Field.LooseReposeDeg = FMath::Clamp(LooseReposeDeg, 1.f, 89.f);
	Field.WallReposeDeg = FMath::Clamp(WallReposeDeg, 1.f, 89.f);
	Field.WallReposeRangeDeg = FMath::Clamp(WallReposeRangeDeg, 0.f, 45.f);
	Field.WallReposeWaveMinCm = FMath::Max(1.f, WallReposeWaveMinCm);
	Field.WallReposeWaveMaxCm = FMath::Max(Field.WallReposeWaveMinCm, WallReposeWaveMaxCm);
	Field.CollapseChance = IsSnow() ? FMath::Clamp(CollapseChance, 0.f, 1.f) : 0.f;
	Field.CollapseSegMinCm = FMath::Max(1.f, CollapseSegMinCm);
	Field.CollapseSegMaxCm = FMath::Max(Field.CollapseSegMinCm, CollapseSegMaxCm);
	Field.CollapseDelayMinS = FMath::Max(0.f, CollapseDelayMinS);
	Field.CollapseDelayMaxS = FMath::Max(Field.CollapseDelayMinS, CollapseDelayMaxS);
	Field.CollapseTopMin = FMath::Clamp(CollapseTopMin, 0.f, 1.f);
	Field.CollapseTopMax = FMath::Clamp(CollapseTopMax, Field.CollapseTopMin, 1.f);
	Field.CollapseFeatherCells = FMath::Max(0.f, CollapseFeatherCells);
	Field.CollapseClumpsMin = FMath::Max(0, CollapseClumpsMin);
	Field.CollapseClumpsMax = FMath::Max(Field.CollapseClumpsMin, CollapseClumpsMax);
	Field.bPloughFallingProfile = IsSnow() && bPloughFallingProfile;
	Field.PileClusterMin = IsSnow() ? FMath::Max(0.f, PileClusterMin) : 1.f;
	Field.PileClusterMax = IsSnow() ? FMath::Max(Field.PileClusterMin, PileClusterMax) : 1.f;
	Field.PileWaveMinCm = FMath::Max(1.f, PileWaveMinCm);
	Field.PileWaveMaxCm = FMath::Max(Field.PileWaveMinCm, PileWaveMaxCm);
	// LM4d: the belly's channel (snow only).
	Field.BellyUndulationCm = IsSnow() ? FMath::Max(0.f, BellyUndulationCm) : 0.f;
	Field.BellyWaveMinCm = FMath::Max(1.f, BellyWaveMinCm);
	Field.BellyWaveMaxCm = FMath::Max(1.f, BellyWaveMaxCm);
	Field.BellyStretch = FMath::Max(1.f, BellyStretch);
	Field.SmearChance = IsSnow() ? FMath::Clamp(SmearChance, 0.f, 1.f) : 0.f;
	Field.SmearLaneCm = FMath::Max(4.f, SmearLaneCm);
	Field.SmearLengthMinCm = FMath::Max(1.f, SmearLengthMinCm);
	Field.SmearLengthMaxCm = FMath::Max(Field.SmearLengthMinCm, SmearLengthMaxCm);
	Field.SmearWidthMinCm = FMath::Max(1.f, SmearWidthMinCm);
	Field.SmearWidthMaxCm = FMath::Max(Field.SmearWidthMinCm, SmearWidthMaxCm);
	Field.SmearHeightMinCm = FMath::Max(0.f, SmearHeightMinCm);
	Field.SmearHeightMaxCm = FMath::Max(Field.SmearHeightMinCm, SmearHeightMaxCm);
	Field.SmearClusterCm = FMath::Max(1.f, SmearClusterCm);
	Field.PloughSpillShare = IsSnow() ? FMath::Clamp(PloughSpillShare, 0.f, 1.f) : 0.f;
	Field.SpillClumpChance = FMath::Clamp(SpillClumpChance, 0.f, 1.f);
	if (IsSnow())
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: snow (LM4d) - the channel undulates +-%.1f cm at %.0f / %.0f cm (x%.1f along); smear ridges %.2f of %.0f cm lanes, %.0f-%.0f cm long, %.0f-%.0f wide, %.1f-%.1f high; spill %.2f of the side deposit, clumps %.2f"),
			InSectionIndex, Field.BellyUndulationCm, Field.BellyWaveMinCm, Field.BellyWaveMaxCm, Field.BellyStretch, Field.SmearChance, Field.SmearLaneCm, Field.SmearLengthMinCm, Field.SmearLengthMaxCm,
			Field.SmearWidthMinCm, Field.SmearWidthMaxCm, Field.SmearHeightMinCm, Field.SmearHeightMaxCm, Field.PloughSpillShare, Field.SpillClumpChance);
	}
	if (IsSnow())
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: snow (LM4c) - talus per cell %d (loose %.0f deg, wall %.0f +-%.0f deg at %.0f-%.0f cm); collapses %.2f of %.0f-%.0f cm segments after %.1f-%.1f s, top %.0f-%.0f %%, feather %.1f cells, %d-%d clumps; plough band %.0f cm falling %d; piles %.2f-%.2f at %.0f-%.0f cm"),
			InSectionIndex, Field.bCellRepose ? 1 : 0, Field.LooseReposeDeg, Field.WallReposeDeg, Field.WallReposeRangeDeg, Field.WallReposeWaveMinCm, Field.WallReposeWaveMaxCm,
			Field.CollapseChance, Field.CollapseSegMinCm, Field.CollapseSegMaxCm, Field.CollapseDelayMinS, Field.CollapseDelayMaxS, 100.f * Field.CollapseTopMin, 100.f * Field.CollapseTopMax,
			Field.CollapseFeatherCells, Field.CollapseClumpsMin, Field.CollapseClumpsMax, Field.PloughBandCm, Field.bPloughFallingProfile ? 1 : 0, Field.PileClusterMin, Field.PileClusterMax,
			Field.PileWaveMinCm, Field.PileWaveMaxCm);
	}
	if (IsSnow())
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: snow (LM4b) - wall waves %.2f cm at %.0f cm + %.2f cm at %.0f cm; notch feather %.1f cells; soft domes %d (skew %.0f-%.0f deg, height at most %.2f x radius, radius %.2f cells +-%.0f %%)"),
			InSectionIndex, Field.WallWaveAmpCm, Field.WallWaveCm, Field.WallWaveLongAmpCm, Field.WallWaveLongCm, Field.WallDropFeatherCells, Field.bLumpSoftDomes ? 1 : 0,
			Field.LumpSkewMinDeg, Field.LumpSkewMaxDeg, Field.LumpHeightPerRadius, Field.LumpRadiusCells, 100.f * Field.LumpVarietyRadiusJitter);
	}
	if (IsSnow())
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: snow (LM4) - cell %.2f cm (mesh %.2f, %d x %d cells), clumps %.1f cells, settle tile %d cells, floor noise %.1f / pockets %.1f / tracks' edge %.1f cells, wall at least %.2f cells; plates %d (%.0f-%.0f deg, sites %.2f cells apart); wall steps %.1f-%.1f cm over %.0f-%.0f cm, %.0f %% drop (floor chunk %.0f %%); snow top +-%.1f cm sd at %.0f-%.0f cm; shard sizes %.0f-%.0f cm (u^%.1f), ClodBankPerCm %.4f per 12.5 cm cell"),
			InSectionIndex, Field.CellCm, MeshCellCm, Field.SizeX, Field.SizeY, Field.RidgeNoiseCells, Field.SettleTileCells, Field.FloorNoiseCells, Field.PocketNoiseCells, Field.TracksEdgeCells,
			Field.RutShoulderMinCells, Field.bLumpPlates ? 1 : 0, Field.PlateTiltMinDeg, Field.PlateTiltMaxDeg, Field.LumpSpacingCells, Field.WallStepMinCm, Field.WallStepMaxCm, Field.WallSegMinCm, Field.WallSegMaxCm,
			100.f * Field.WallDropShare, 100.f * Field.FloorChunkChance, Field.SnowTopUndulationCm, Field.SnowTopWaveMinCm, Field.SnowTopWaveMaxCm, Field.ClodBankSizeMinCm, Field.ClodBankSizeMaxCm, Field.ClodSizePower, Field.ClodBankPerCm);
	}
	if (IsSnow())
	{
		float DeepestCm = 0.f;
		for (const float Depth : Field.SnowDepthCell)
		{
			DeepestCm = FMath::Max(DeepestCm, Depth);
		}
		// The tyre cuts to its bottom: the deepest snow plus the deepest sinkage (the profile's), and a margin; LM4: and the
		// undulation's reach above the depth (three sd).
		DisplaceDownCm = FMath::Max(DisplaceDownCm, DeepestCm + 3.f * Field.SnowTopUndulationCm + ProfileMaxSinkageM * 100.f + 15.f);
		if (FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(SnowMaterialPath)))
		{
			MaterialPath = SnowMaterialPath;
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("AGTMudPatch %d: %s missing (run Art/setup_live_snow_drive.ps1); the snow wears %s"), InSectionIndex, *SnowMaterialPath, *MaterialPath);
		}
		if (FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(SnowClodMaterialPath)))
		{
			ClodMaterialPath = SnowClodMaterialPath;
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("AGTMudPatch %d: %s missing; the snow clods wear %s"), InSectionIndex, *SnowClodMaterialPath, *ClodMaterialPath);
		}
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: snow (LM3a) - depth %.0f cm (deepest %.0f with the drifts), taper over %.0f cm in from the box, RidgeReturn %.2f, wall %.0f cm (at least %.1f cells), RutDepthVariation %.2f, plough return %.2f into %.0f cm, refill %.1f cm/min, SnowPlough %.2f, SnowBellyDrag %.2f, sinkage %.3f m at %.3f m/s, material %s, clods %s"),
			InSectionIndex, Field.SnowDepthCm, DeepestCm, Field.SnowEdgeCm, Field.RidgeReturn, Field.RutShoulderCm, Field.RutShoulderMinCells, Field.RutDepthVariation,
			Field.PloughReturn, Field.PloughBandCm, Field.RefillCmPerMin, SnowPlough, SnowBellyDrag, ProfileMaxSinkageM, ProfileSinkageRate, *MaterialPath, *ClodMaterialPath);
	}
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: variety (LM2c) %d - sites jittered +-0.5, cluster %.0f cm with %.0f %% absent, amplitude %.2f-%.2f (u^2), aspect 1-%.1f, radius +-%.0f %%, satellites %.0f %%; bank clods %.3f per cm of deposit on the band's inner %.0f %%, %.0f-%.0f cm (u^%.1f); throw clods %.2f; tilt +-%.0f deg off the normal, sunk %.2f-%.2f, scale XY %.1f-%.1f Z %.1f-%.1f, fresh throw %.1f bank %.1f, re-push at %.1f cm"),
		InSectionIndex, Field.bLumpVariety ? 1 : 0, Field.LumpClusterCm, 100.f * Field.LumpAbsentShare, Field.LumpAmpMin, Field.LumpAmpMax, Field.LumpAspectMax, 100.f * Field.LumpVarietyRadiusJitter,
		100.f * Field.LumpSatelliteChance, Field.ClodBankPerCm, 100.f * Field.ClodBankInner, Field.ClodBankSizeMinCm, Field.ClodBankSizeMaxCm, Field.ClodSizePower, ClodThrowChance,
		ClodTiltDeg, ClodSinkIn, ClodSinkInMax, ClodScaleXYMin, ClodScaleXYMax, ClodScaleZMin, ClodScaleZMax, ClodFreshThrow, ClodFreshBank, ClodRepushCm);
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: lumps and throw (LM2a) - LumpShare %.2f on sites %.1f cells apart, radius %.1f cells (+-%.0f %%), LumpMaxCm %.1f, ThrowMax %.2f, FreshMinCm %.3f; clods (LM2b) bank %.2f per %.1f cm (respawn %.1f s, %.0f-%.0f cm), throw %.2f, max %d, sink-in %.2f, wet sink %.2f cm/s, gt.Mud.Clods %d"),
		InSectionIndex, Field.LumpShare, Field.LumpSpacingCells, Field.LumpRadiusCells, 100.f * Field.LumpRadiusJitter, Field.LumpMaxCm, ThrowMax, Field.FreshMinCm,
		Field.ClodBankChance, Field.ClodBankMinCm, Field.ClodRespawnS, Field.ClodBankMinSizeCm, Field.ClodBankMaxSizeCm, ClodThrowChance, MaxClods, ClodSinkIn, ClodSinkCmPerS,
		CVarMudClods.GetValueOnGameThread());
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: settle (LM1/LM1b) - ReposeDeg %.1f, SlumpRate %.2f/s, OozeRate %.2f/s, RecoverShare %.3f, CreepCmPerCm %.2f, SetSeconds %.2f s, SmearCmPerCm %.2f, FreshFadeS %.1f s, SleepCmPerS %.3f; tiles of %d cells, sub-step %.4f s; gt.Mud.Settle %d"),
		InSectionIndex, Field.ReposeDeg, Field.SlumpRate, Field.OozeRate, Field.RecoverShare, Field.CreepCmPerCm, Field.SetSeconds, Field.SmearCmPerCm, Field.FreshFadeS, Field.SleepCmPerS,
		Field.SettleTileCells, Field.SettleStepS, CVarMudSettle.GetValueOnGameThread());
	// LM4 item 2: a snow patch's plates (the Voronoi cells over the field) are built now, not on the first stamp.
	if (Field.LumpsShaped() && Field.LumpShare > 0.f)   // LM4b: the soft domes too
	{
		Field.PrepareLumps();
	}
	// LM4c: the wall repose's and the piles' static per-cell arrays, now rather than on the first stamp or sub-step.
	Field.PrepareSnowPiles();
	// LM4f item 4: the stamps' static per-cell noises, now rather than on the first stamp.
	Field.PrepareStampNoise();
	// MR4: the soft spots (a bog's patch only), before BakeLayers writes them into the layer's G.
	BuildSoftSpots();
	// GR1: the pre-churn (a bog's patch with PreChurnScale over 0), after S (its soft ruts) and before the mesh and the chunks.
	PreChurn();
	// Benmore B2: a zone patch's cells, its pre-churn faded at the outline, the baseline kept and the cached cells restored (the
	// subsystem's hook; unset on every other patch).
	if (ZoneAfterField)
	{
		ZoneAfterField(*this);
	}
	// A transient texture's first mip is not cleared: zero it, or the mesh displaces by garbage wherever no stamp
	// has uploaded yet (the whole bog until the first wheel: giant triangles over the camera).
	auto MakeField = [this](UTexture2D*& Out)
	{
		Out = UTexture2D::CreateTransient(Field.SizeX, Field.SizeY, PF_FloatRGBA);
		if (!Out)
		{
			return;
		}
		Out->SRGB = false;
		Out->Filter = TF_Bilinear;
		Out->AddressX = TA_Clamp;
		Out->AddressY = TA_Clamp;
		if (FTexturePlatformData* PlatformData = Out->GetPlatformData())
		{
			if (PlatformData->Mips.Num() > 0)
			{
				FTexture2DMipMap& Mip = PlatformData->Mips[0];
				if (void* Data = Mip.BulkData.Lock(LOCK_READ_WRITE))
				{
					FMemory::Memzero(Data, Mip.BulkData.GetBulkDataSize());
				}
				Mip.BulkData.Unlock();
			}
		}
		Out->UpdateResource();
	};
	UTexture2D* NewField = nullptr;
	MakeField(NewField);
	Texture = NewField;
	// Stage F: the tread rides in its own texture, the same size and the same dirty rects (R heading turns, G lug phase).
	UTexture2D* NewTread = nullptr;
	MakeField(NewTread);
	TreadTexture = NewTread;
	// Apply after the medium's default, before the mesh binds its field textures.
	if (!ProfileSurfaceMaterialPath.IsEmpty())
	{
		MaterialPath = ProfileSurfaceMaterialPath;
	}
	BuildMesh();
	// Deformable gravel DG1: a gravel patch's loose stones, on the mesh just built.
	InitGravelStones();
	// And the whole field once, so the GPU copy starts equal to the CPU one whatever the mip held.
	Upload(FIntRect(0, 0, Field.SizeX, Field.SizeY));
	// LM2b: the clods' instances (none without a mesh).
	InitClods();
	// MR5: the chunks (a bog's patch only; after S, which places them, and the clods, which their breaks spawn).
	InitMudChunks();
	// MRD1: a mud road's clod fields round its churn zones, and its sticks and branches.
	SpawnRoadClodFields();
	InitRoadDebris();
}

int32 AGTMudPatch::BakeLayers(const FGTTerrainSpec& Spec)
{
	BogCells = 0;
	if (!Field.IsValid())
	{
		return 0;
	}
	// The generator's layer at the landscape's own vertices (its quads), then bilinear into the cells: the landscape blends
	// its weightmap the same way, so the mesh's ground colour meets the ground's without a seam.
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	const float Quad = FMath::Max(1.f, Spec.QuadSizeCm);
	const FBox2D Bounds = Field.Bounds();
	const int32 VX0 = FMath::FloorToInt((Bounds.Min.X - Spec.OriginXCm) / Quad);
	const int32 VY0 = FMath::FloorToInt((Bounds.Min.Y - Spec.OriginYCm) / Quad);
	const int32 VX1 = FMath::CeilToInt((Bounds.Max.X - Spec.OriginXCm) / Quad) + 1;
	const int32 VY1 = FMath::CeilToInt((Bounds.Max.Y - Spec.OriginYCm) / Quad) + 1;
	const int32 VW = VX1 - VX0 + 1;
	const int32 VH = VY1 - VY0 + 1;
	TArray<float> Vertex;
	Vertex.SetNumZeroed(VW * VH);
	for (int32 J = 0; J < VH; ++J)
	{
		for (int32 I = 0; I < VW; ++I)
		{
			const float XCm = Spec.OriginXCm + (VX0 + I) * Quad;
			const float YCm = Spec.OriginYCm + (VY0 + J) * Quad;
			Vertex[J * VW + I] = GTTerrain::LayerAt(Spec, Profiles, XCm / 100.f, YCm / 100.f) == 5 ? 1.f : 0.f;   // layer 5: the Bog
		}
	}
	TArray<uint8> Data;
	Data.SetNumUninitialized(Field.SizeX * Field.SizeY);
	for (int32 Y = 0; Y < Field.SizeY; ++Y)
	{
		for (int32 X = 0; X < Field.SizeX; ++X)
		{
			const float XCm = Bounds.Min.X + (X + 0.5f) * Field.CellCm;
			const float YCm = Bounds.Min.Y + (Y + 0.5f) * Field.CellCm;
			const float FX = FMath::Clamp((XCm - Spec.OriginXCm) / Quad - VX0, 0.f, VW - 1.001f);
			const float FY = FMath::Clamp((YCm - Spec.OriginYCm) / Quad - VY0, 0.f, VH - 1.001f);
			const int32 IX = FMath::FloorToInt(FX);
			const int32 IY = FMath::FloorToInt(FY);
			const float TX = FX - IX;
			const float TY = FY - IY;
			const float Bog = FMath::Lerp(FMath::Lerp(Vertex[IY * VW + IX], Vertex[IY * VW + IX + 1], TX), FMath::Lerp(Vertex[(IY + 1) * VW + IX], Vertex[(IY + 1) * VW + IX + 1], TX), TY);
			Data[Y * Field.SizeX + X] = static_cast<uint8>(FMath::RoundToInt(255.f * FMath::Clamp(Bog, 0.f, 1.f)));
			BogCells += Bog >= 0.5f ? 1 : 0;
		}
	}
	BogMask = Data;   // LM2b: the clods' wet sinking reads it
	// MR4: two channels - R the layer as before, G the softness S x 255 (0 off scope or with gt.Mud.SoftSpots 0).
	FillLayerBytes();
	LayerTexture = UTexture2D::CreateTransient(Field.SizeX, Field.SizeY, PF_R8G8);
	if (LayerTexture)
	{
		LayerTexture->SRGB = false;
		LayerTexture->Filter = TF_Bilinear;
		LayerTexture->AddressX = TA_Clamp;
		LayerTexture->AddressY = TA_Clamp;
		if (FTexturePlatformData* PlatformData = LayerTexture->GetPlatformData())
		{
			if (PlatformData->Mips.Num() > 0)
			{
				FTexture2DMipMap& Mip = PlatformData->Mips[0];
				if (void* Dest = Mip.BulkData.Lock(LOCK_READ_WRITE))
				{
					FMemory::Memcpy(Dest, LayerBytes.GetData(), FMath::Min<int64>(LayerBytes.Num(), Mip.BulkData.GetBulkDataSize()));
				}
				Mip.BulkData.Unlock();
			}
		}
		LayerTexture->UpdateResource();
		if (MeshMaterial)
		{
			MeshMaterial->SetTextureParameterValue(TEXT("MudLayer"), LayerTexture);
		}
	}
	return BogCells;
}

// ---- MudRunner MR4, readable soft spots (docs/MUDRUNNER_LESSONS_PLAN.md MR4 execution block) ----------------------------
namespace
{
	/** MR4: a lattice point's value, -1..1, from an integer hash of its coordinates and the seed. */
	float SoftHash(int32 X, int32 Y, uint32 Seed)
	{
		uint32 H = (static_cast<uint32>(X) * 0x8da6b343u) ^ (static_cast<uint32>(Y) * 0xd8163841u) ^ (Seed * 0xcb1ab31fu);
		H ^= H >> 16;
		H *= 0x7feb352du;
		H ^= H >> 15;
		H *= 0x846ca68bu;
		H ^= H >> 16;
		return static_cast<float>(H & 0xFFFFFFu) / static_cast<float>(0xFFFFFF) * 2.f - 1.f;
	}

	/** MR4: smooth value noise at a world point in metres, -1..1: the lattice turned by AngleRad (no octave lines up with the route or the box), smoothstep between its points. */
	float SoftNoise(double XM, double YM, double WavelengthM, double AngleRad, uint32 Seed)
	{
		const double C = FMath::Cos(AngleRad);
		const double S = FMath::Sin(AngleRad);
		const double U = (C * XM - S * YM) / WavelengthM;
		const double V = (S * XM + C * YM) / WavelengthM;
		const double U0 = FMath::FloorToDouble(U);
		const double V0 = FMath::FloorToDouble(V);
		const float TX = static_cast<float>(U - U0);
		const float TY = static_cast<float>(V - V0);
		const float FX = TX * TX * (3.f - 2.f * TX);
		const float FY = TY * TY * (3.f - 2.f * TY);
		const int32 IX = static_cast<int32>(U0);
		const int32 IY = static_cast<int32>(V0);
		return FMath::Lerp(FMath::Lerp(SoftHash(IX, IY, Seed), SoftHash(IX + 1, IY, Seed), FX),
			FMath::Lerp(SoftHash(IX, IY + 1, Seed), SoftHash(IX + 1, IY + 1, Seed), FX), FY);
	}

	/** MR4: a sorted array's value at quantile Q (0..1), linear between ranks. */
	float SoftQuantile(const TArray<float>& Sorted, double Q)
	{
		const double Pos = FMath::Clamp(Q, 0.0, 1.0) * (Sorted.Num() - 1);
		const int32 I = FMath::Clamp(static_cast<int32>(FMath::FloorToDouble(Pos)), 0, Sorted.Num() - 1);
		const int32 J = FMath::Min(I + 1, Sorted.Num() - 1);
		return FMath::Lerp(Sorted[I], Sorted[J], static_cast<float>(Pos - I));
	}
}

void AGTMudPatch::BuildSoftness(TArray<float>& Out, int32 SizeX, int32 SizeY, float CellCm, const FVector2D& OriginCm, int32 Seed, float Amplitude)
{
	Out.Reset();
	if (SizeX <= 0 || SizeY <= 0 || CellCm <= 0.f)
	{
		return;
	}
	const int32 Count = SizeX * SizeY;
	Out.SetNumUninitialized(Count);
	const uint32 Base = static_cast<uint32>(Seed);
	// The raw n: two octaves (7 m and 3 m, 0.65 / 0.35) at a point domain-warped by a 9 m noise of 1.5 m - the warp makes the
	// blobs ragged rather than round.
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			const double XM = (OriginCm.X + (X + 0.5) * CellCm) * 0.01;
			const double YM = (OriginCm.Y + (Y + 0.5) * CellCm) * 0.01;
			const double WX = 1.5 * SoftNoise(XM, YM, 9.0, 0.3, Base + 1u);
			const double WY = 1.5 * SoftNoise(XM, YM, 9.0, 1.1, Base + 2u);
			Out[Y * SizeX + X] = 0.65f * SoftNoise(XM + WX, YM + WY, 7.0, 0.6, Base + 3u) + 0.35f * SoftNoise(XM + WX, YM + WY, 3.0, 1.9, Base + 4u);
		}
	}
	// S0: n by the percentiles of the patch's interior (the cells at least RimInnerCm from its edge; all of them on a patch too small
	// to have one), piecewise-linear (min 0, p5 0.15, p75 0.6, p95 0.9, max 1), so exactly the interior cells over p75 are over 0.6
	// before the amplitude; then the amplitude about 0.5 and the rim (main session, 2026-10-09): S = lerp(0.4, S, smoothstep(0.5 m,
	// 2.0 m, d)), d the distance to the nearest edge - the outer 0.5 m exactly 0.4, under the look's threshold even in the hollows.
	const float RimOuterCm = 50.f;
	const float RimInnerCm = 200.f;
	const float WidthCm = SizeX * CellCm;
	const float HeightCm = SizeY * CellCm;
	auto EdgeOf = [CellCm, WidthCm, HeightCm](int32 X, int32 Y)
	{
		const float CX = (X + 0.5f) * CellCm;
		const float CY = (Y + 0.5f) * CellCm;
		return FMath::Min(FMath::Min(CX, WidthCm - CX), FMath::Min(CY, HeightCm - CY));
	};
	TArray<float> Sorted;
	Sorted.Reserve(Count);
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			if (EdgeOf(X, Y) >= RimInnerCm)
			{
				Sorted.Add(Out[Y * SizeX + X]);
			}
		}
	}
	if (Sorted.Num() == 0)
	{
		Sorted = Out;
	}
	Sorted.Sort();
	const float Knot[5] = { Sorted[0], SoftQuantile(Sorted, 0.05), SoftQuantile(Sorted, 0.75), SoftQuantile(Sorted, 0.95), Sorted.Last() };
	const float Value[5] = { 0.f, 0.15f, 0.6f, 0.9f, 1.f };
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			const float N = Out[Y * SizeX + X];
			float S0 = Value[4];
			if (N <= Knot[0])
			{
				S0 = Value[0];
			}
			else
			{
				for (int32 K = 1; K < 5; ++K)
				{
					if (N <= Knot[K])
					{
						const float Span = Knot[K] - Knot[K - 1];
						S0 = Span > 1.e-9f ? FMath::Lerp(Value[K - 1], Value[K], (N - Knot[K - 1]) / Span) : Value[K];
						break;
					}
				}
			}
			float S = 0.5f + (S0 - 0.5f) * Amplitude;
			const float T = FMath::Clamp((EdgeOf(X, Y) - RimOuterCm) / (RimInnerCm - RimOuterCm), 0.f, 1.f);
			S = FMath::Lerp(0.4f, S, T * T * (3.f - 2.f * T));
			Out[Y * SizeX + X] = FMath::Clamp(S, 0.f, 1.f);
		}
	}
}

void AGTMudPatch::BuildSoftSpots()
{
	Softness.Reset();
	SoftMeanSink = 1.f;
	SoftMeanFriction = 1.f;
	bSoftOn = CVarMudSoftSpots.GetValueOnGameThread() != 0;
	// The scope: a Mud-medium bog patch without a profile (an unprofiled bog or an LM5b variant's). Not a profiled patch (a ford's
	// or riverbed's bed, any other medium's profile), not snow.
	if (!Field.IsValid() || bHasProfile || Medium != EGTDeformMedium::Mud)
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: soft spots (MR4) - none (%s)"), SectionIndex, bHasProfile ? TEXT("a profiled patch") : TEXT("not a mud field"));
		return;
	}
	BuildSoftness(Softness, Field.SizeX, Field.SizeY, Field.CellCm, Field.OriginCm, SoftSpotSeed(SectionIndex), SoftSpotAmplitude);
	double SumSink = 0.0;
	double SumFriction = 0.0;
	int32 Soft = 0;
	for (const float S : Softness)
	{
		SumSink += SoftSinkLerp(S);
		SumFriction += SoftFrictionLerp(S);
		Soft += S > 0.6f ? 1 : 0;
	}
	const double Count = FMath::Max(1, Softness.Num());
	SoftMeanSink = static_cast<float>(SumSink / Count);
	SoftMeanFriction = static_cast<float>(SumFriction / Count);
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: soft spots (MR4) - amplitude %.2f, seed %d, %d x %d cells, soft (S over 0.6) %.1f %%, mean lerps sink %.4f friction %.4f; gt.Mud.SoftSpots %d"),
		SectionIndex, SoftSpotAmplitude, SoftSpotSeed(SectionIndex), Field.SizeX, Field.SizeY, 100.0 * Soft / Count, SoftMeanSink, SoftMeanFriction, bSoftOn ? 1 : 0);
}

float AGTMudPatch::SoftnessAt(FVector2D XYCm) const
{
	if (!HasSoftSpots())
	{
		return 0.5f;
	}
	const float GX = static_cast<float>((XYCm.X - Field.OriginCm.X) / Field.CellCm) - 0.5f;   // cell centres carry the values
	const float GY = static_cast<float>((XYCm.Y - Field.OriginCm.Y) / Field.CellCm) - 0.5f;
	const int32 X0 = FMath::Clamp(FMath::FloorToInt(GX), 0, Field.SizeX - 1);
	const int32 Y0 = FMath::Clamp(FMath::FloorToInt(GY), 0, Field.SizeY - 1);
	const int32 X1 = FMath::Min(X0 + 1, Field.SizeX - 1);
	const int32 Y1 = FMath::Min(Y0 + 1, Field.SizeY - 1);
	const float FX = FMath::Clamp(GX - X0, 0.f, 1.f);
	const float FY = FMath::Clamp(GY - Y0, 0.f, 1.f);
	return FMath::Lerp(FMath::Lerp(Softness[Y0 * Field.SizeX + X0], Softness[Y0 * Field.SizeX + X1], FX),
		FMath::Lerp(Softness[Y1 * Field.SizeX + X0], Softness[Y1 * Field.SizeX + X1], FX), FY);
}

FVector2D AGTMudPatch::SoftScalesAt(FVector2D XYCm) const
{
	if (!bSoftOn || !HasSoftSpots())
	{
		return FVector2D(1.0, 1.0);
	}
	const float S = SoftnessAt(XYCm);
	return FVector2D(SoftSinkLerp(S) / FMath::Max(SoftMeanSink, 1.e-3f), SoftFrictionLerp(S) / FMath::Max(SoftMeanFriction, 1.e-3f));
}

TArray<uint8> AGTMudPatch::GetSoftnessBytes() const
{
	TArray<uint8> Bytes;
	if (HasSoftSpots())
	{
		Bytes.SetNumUninitialized(Softness.Num());
		for (int32 Index = 0; Index < Softness.Num(); ++Index)
		{
			Bytes[Index] = static_cast<uint8>(FMath::RoundToInt(255.f * FMath::Clamp(Softness[Index], 0.f, 1.f)));
		}
	}
	return Bytes;
}

void AGTMudPatch::FillLayerBytes()
{
	const int32 Count = Field.SizeX * Field.SizeY;
	LayerBytes.SetNumUninitialized(Count * 2);
	const bool bLayer = BogMask.Num() == Count;
	const bool bSoft = bSoftOn && HasSoftSpots();
	for (int32 Index = 0; Index < Count; ++Index)
	{
		LayerBytes[2 * Index] = bLayer ? BogMask[Index] : static_cast<uint8>(0);
		LayerBytes[2 * Index + 1] = bSoft ? static_cast<uint8>(FMath::RoundToInt(255.f * FMath::Clamp(Softness[Index], 0.f, 1.f))) : static_cast<uint8>(0);
	}
}

void AGTMudPatch::UploadLayer()
{
	if (!LayerTexture || !LayerTexture->GetResource() || LayerBytes.Num() != Field.SizeX * Field.SizeY * 2)
	{
		return;
	}
	TArray<uint8>* Data = new TArray<uint8>(LayerBytes);
	FUpdateTextureRegion2D* Region = new FUpdateTextureRegion2D(0, 0, 0, 0, Field.SizeX, Field.SizeY);
	LayerTexture->UpdateTextureRegions(0, 1, Region, Field.SizeX * 2, 2, Data->GetData(),
		[Data](uint8*, const FUpdateTextureRegion2D* Regions)
		{
			delete Data;
			delete Regions;
		});
}

void AGTMudPatch::ApplySoftSwitch(bool bOn)
{
	bSoftOn = bOn;
	if (HasSoftSpots() && LayerBytes.Num() > 0)
	{
		FillLayerBytes();
		UploadLayer();
	}
}

void AGTMudPatch::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// LM1: the field settles before what changed goes up. The traction stamps in AGTCarPawn::Tick (pre-physics) and this
	// patch ticks post-physics, both on the game thread, so the stamps and the settling share the field without locks.
	bSettleOn = CVarMudSettle.GetValueOnGameThread() != 0;
	// MR4: gt.Mud.SoftSpots flipped since the last tick - the scales switch and the layer's G goes up again (S, or 0).
	const bool bSoftNow = CVarMudSoftSpots.GetValueOnGameThread() != 0;
	if (bSoftNow != bSoftOn)
	{
		ApplySoftSwitch(bSoftNow);
	}
	// MR5: gt.Mud.Chunks, the awake chunks' places, the lost ones and the world-wide awake cap.
	UpdateMudChunks(DeltaSeconds);
	// MR3: where the rut water stands and whether it churns (gt.Mud.MuddyWater, only where this patch's rut water is drawn),
	// before this tick's stamps replay; the material told when the switch moves (0: today's water exactly).
	if (!IsSnow())
	{
		const bool bMuddy = CVarMudMuddyWater.GetValueOnGameThread() != 0;
		Field.RutWaterTableCm = CurrentWaterTableCm();
		Field.SetMuddyWater(bMuddy && IsWaterDrawn());
		if (WaterMaterial && PushedMuddyWater != (bMuddy ? 1.f : 0.f))
		{
			PushedMuddyWater = bMuddy ? 1.f : 0.f;
			WaterMaterial->SetScalarParameterValue(TEXT("MuddyWater"), PushedMuddyWater);
		}
		// MRP: the rut water's table onto the mud's own material, so its parallax skips the pixels under the water (-10000: none
		// drawn, the material's default).
		const float MeshTable = IsWaterDrawn() ? CurrentWaterTableCm() : -10000.f;
		if (MeshMaterial && MeshTable != PushedMeshTableCm)
		{
			PushedMeshTableCm = MeshTable;
			MeshMaterial->SetScalarParameterValue(TEXT("MudWaterTableCm"), MeshTable);
		}
	}
	// LM4b item 6: gt.Snow.Parallax onto the snow material when it changes (-1: the material's own default, read once).
	if (IsSnow() && MeshMaterial)
	{
		if (DefaultParallax < -1.5f)
		{
			DefaultParallax = MeshMaterial->K2_GetScalarParameterValue(TEXT("SnowParallax"));
		}
		const int32 Parallax = CVarSnowParallax.GetValueOnGameThread();
		const float Want = Parallax < 0 ? DefaultParallax : (Parallax > 0 ? 1.f : 0.f);
		if (Want != PushedParallax)
		{
			MeshMaterial->SetScalarParameterValue(TEXT("SnowParallax"), Want);
			PushedParallax = Want;
		}
		// LM4e cut 6: gt.Snow.FastMaterial onto SnowFastPath the same way.
		if (DefaultFastPath < -1.5f)
		{
			DefaultFastPath = MeshMaterial->K2_GetScalarParameterValue(TEXT("SnowFastPath"));
		}
		const int32 Fast = CVarSnowFastMaterial.GetValueOnGameThread();
		const float WantFast = Fast < 0 ? DefaultFastPath : static_cast<float>(FMath::Clamp(Fast, 0, 2));   // LM4f: level 2
		if (WantFast != PushedFastPath)
		{
			MeshMaterial->SetScalarParameterValue(TEXT("SnowFastPath"), WantFast);
			PushedFastPath = WantFast;
		}
	}
	// LM2b: the field's clock (the bank clods' respawn timer) and whether it queues clods at all this tick.
	bool bClodsOn = CVarMudClods.GetValueOnGameThread() != 0;
	float FrameDt = DeltaSeconds;
	Field.bSnowQuietSleep = CVarSnowQuietSleep.GetValueOnGameThread() != 0;   // LM4e cut 1 (read on snow only)
	Field.bSnowFastSweep = CVarSnowFastSweep.GetValueOnGameThread() != 0;     // LM4e cut 3 (read on snow only)
	Field.SnowFastSettle = FGTMudField::DefaultSnowFastSettle();             // LM4f item 3: gt.Snow.FastSettle (read on snow only)
	// LM4f item 1: gt.Snow.ShadowProxy onto the chunks and their shadow meshes when it changes.
	const bool bWantProxy = CVarSnowShadowProxy.GetValueOnGameThread() != 0;
	if (bWantProxy != bShadowProxyOn)
	{
		bShadowProxyOn = bWantProxy;
		ApplySurfaceShadows();
	}
	LastSettleMs = 0.f;
	LastSettleSteps = 0;
	LastAwakeTiles = 0;
	Field.SweptTilesSinceTake = 0;
	Field.ListedTilesSinceTake = 0;
	if (IsReplaying())
	{
		// LM4e: one recorded frame in place of this one's clock and settle - its stamps, its clock, its settle (timed as Settle)
		// and its end (the frame's dt and clods switch for the upload and the clod batch below).
		bool bFrameEnd = false;
		while (IsReplaying() && !bFrameEnd)
		{
			const FGTMudField::FEvent Event = ReplayLog[ReplayCursor++];
			if (Event.Kind == FGTMudField::EventSettle)
			{
				SCOPE_CYCLE_COUNTER(STAT_GTMudSettle);
				CSV_SCOPED_TIMING_STAT(GTMud, Settle);
				const double Start = FPlatformTime::Seconds();
				ReplayEvent(Event);
				LastSettleMs = static_cast<float>((FPlatformTime::Seconds() - Start) * 1000.0);
				LastAwakeTiles = Field.AwakeTileCount();
				bSettleOn = true;
			}
			else
			{
				ReplayEvent(Event);
			}
			if (Event.Kind == FGTMudField::EventFrame)
			{
				bFrameEnd = true;
				FrameDt = static_cast<float>(Event.V[0]);
				bClodsOn = Event.V[1] > 0.5;
			}
		}
	}
	else
	{
		Field.AdvanceClock(DeltaSeconds);
		Field.bQueueClods = bClodsOn && ClodMeshes.Num() > 0;
		Record(FGTMudField::EventClock, { DeltaSeconds }, Field.bQueueClods ? 1 : 0);
		if (bSettleOn)
		{
			Record(FGTMudField::EventSettle, { DeltaSeconds });
			SCOPE_CYCLE_COUNTER(STAT_GTMudSettle);
			CSV_SCOPED_TIMING_STAT(GTMud, Settle);
			const double Start = FPlatformTime::Seconds();
			LastSettleSteps = Field.Settle(DeltaSeconds);
			LastSettleMs = static_cast<float>((FPlatformTime::Seconds() - Start) * 1000.0);
			LastAwakeTiles = Field.AwakeTileCount();
		}
	}
	// MR3: the churned water mixes and settles on its own clock (whatever gt.Mud.Settle says), before what changed goes up.
	LastTurbidSteps = Field.SettleTurbidity(FrameDt);
	if (ChunkMeshes.Num() > 0)
	{
		UpdateChunkLods();   // LM4e cut 4
	}
	LastSweptTiles = Field.SweptTilesSinceTake;
	LastListedTiles = Field.ListedTilesSinceTake;
	// LM4e: the outside stamp calls since the last tick (the traction's this frame, the throw's landings), as a CSV stat.
	LastStampMs = static_cast<float>(Field.StampMs);
	Field.StampMs = 0.0;
	CSV_CUSTOM_STAT(GTMud, Stamp, LastStampMs, ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(GTMud, SweptTiles, LastSweptTiles, ECsvCustomStatOp::Set);
	FIntRect Rect;
	LastUploadMs = 0.f;
	LastUploadCells = 0;
	// LM4e cut 2 (snow, gt.Snow.UploadTiles): the changed cells as one box per settle tile, not one box round them all.
	const bool bTileUpload = IsSnow() && CVarSnowUploadTiles.GetValueOnGameThread() != 0;
	if (bTileUpload ? Field.TakeDirtyRects(UploadRectList, Rect) : Field.TakeDirty(Rect))
	{
		SCOPE_CYCLE_COUNTER(STAT_GTMudUpload);
		CSV_SCOPED_TIMING_STAT(GTMud, Upload);
		const double Start = FPlatformTime::Seconds();
		if (bTileUpload)
		{
			LastUploadCells = UploadRects(UploadRectList);
		}
		else
		{
			Upload(Rect);
			LastUploadCells = Rect.Width() * Rect.Height();
		}
		LastUploadMs = static_cast<float>((FPlatformTime::Seconds() - Start) * 1000.0);
		// LM2b: the cells that changed, for the clods' re-snap at the next batch.
		if (bClodDirtyCells)
		{
			ClodDirtyCells.Union(Rect);
		}
		else
		{
			ClodDirtyCells = Rect;
			bClodDirtyCells = true;
		}
		// MRD1: a mud road's sticks pressed down with the ground under them.
		if (RoadDebris.Num() > 0)
		{
			UpdateRoadDebris(Rect);
		}
	}
	{
		SCOPE_CYCLE_COUNTER(STAT_GTMudClods);
		CSV_SCOPED_TIMING_STAT(GTMud, Clods);
		const double Start = FPlatformTime::Seconds();
		UpdateClods(FrameDt, bClodsOn);
		LastClodMs = static_cast<float>((FPlatformTime::Seconds() - Start) * 1000.0);
	}
	CSV_CUSTOM_STAT(GTMud, UploadCells, LastUploadCells, ECsvCustomStatOp::Set);
	INC_FLOAT_STAT_BY(STAT_GTMudStampMs, LastStampMs);
	INC_DWORD_STAT_BY(STAT_GTMudSweptTiles, LastSweptTiles);
	INC_DWORD_STAT_BY(STAT_GTMudUploadCells, LastUploadCells);
	if (IsSnow())
	{
		INC_DWORD_STAT_BY(STAT_GTSnowDrawnTriangles, DrawnTriangles);
	}
	// LM4e: the frame's end in the record (its dt and clods switch: the replay's upload and clod batch).
	Record(FGTMudField::EventFrame, { DeltaSeconds, bClodsOn ? 1.0 : 0.0 });
	// LM3a: the snow's refill while the weather snows, a whole-field pass at RefillHz (one full upload next tick).
	if (IsSnow())
	{
		RefillAccumS += DeltaSeconds;
		const float Period = 1.f / FMath::Max(0.01f, RefillHz);
		if (RefillAccumS >= Period && !IsReplaying())
		{
			const int32 Mode = CVarSnowRefill.GetValueOnGameThread();
			bool bSnowing = Mode > 0;
			if (Mode < 0)
			{
				// Snowing is precipitation below freezing: UGTWeatherSubsystem's own rule for SnowAmount's growth.
				const UGTWeatherSubsystem* SnowWeather = GetWorld() ? GetWorld()->GetSubsystem<UGTWeatherSubsystem>() : nullptr;
				bSnowing = SnowWeather && SnowWeather->GetCurrent().TemperatureC < 0.f && SnowWeather->GetCurrent().RainIntensity > 0.f;
			}
			bRefilling = bSnowing;
			if (bSnowing)
			{
				Record(FGTMudField::EventRefill, { RefillAccumS });
				const double Start = FPlatformTime::Seconds();
				Field.Refill(RefillAccumS);
				LastRefillMs = static_cast<float>((FPlatformTime::Seconds() - Start) * 1000.0);
				++RefillPasses;
			}
			RefillAccumS = 0.f;
		}
		RefilledCm3 = Field.RefilledCm3;
		PloughedCm3 = Field.PloughedCm3;
		PloughBermCm3 = Field.PloughBermCm3;
		// LM4 item 3 readouts.
		WallDrops = Field.WallDrops;
		WallDropCm3 = Field.WallDropCm3;
		LipChunksQueued = Field.LipChunksQueued;
		FloorChunksQueued = Field.FloorChunksQueued;
		// LM4c item 2 readouts.
		CollapsesFired = Field.CollapsesFired;
		CollapseCm3 = Field.CollapseCm3;
		CollapseSegsArmed = Field.CollapseSegsArmed;
		CollapseClumpsQueued = Field.CollapseClumpsQueued;
		// LM4d readouts.
		SmearCm3 = Field.SmearCm3;
		SpillCm3 = Field.SpillCm3;
		SpillClumpsQueued = Field.SpillClumpsQueued;
	}
	// LM2a readouts from the field's book.
	ThrowReturnedCm3 = Field.Book.ThrownCm3;
	LumpFlattenedCm3 = Field.Book.FlattenedCm3;
	LumpLandedCm3 = Field.Book.LumpLandedCm3;
	if (UGTMudSubsystem* Mud = GetWorld() ? GetWorld()->GetSubsystem<UGTMudSubsystem>() : nullptr)
	{
		Mud->AddSettleSample(bSettleOn, LastSettleMs, LastAwakeTiles, LastUploadMs, bClodsOn && ClodMeshes.Num() > 0, LastClodMs);
		Mud->AddCostSample(LastStampMs, LastSweptTiles, LastUploadCells);   // LM4e
	}
	// Stage G: the weather lifts the water table, as it lifts a ford's sheet (AGTWaterSheet::Tick). The grid was built
	// at the still table, so the lift moves the whole component and the material is told where the table is now - the
	// mask that keeps the water in the ruts is a comparison against it.
	const UGTWeatherSubsystem* Weather = GetWorld() ? GetWorld()->GetSubsystem<UGTWeatherSubsystem>() : nullptr;
	const float Lift = Weather ? FMath::Clamp(Weather->GetWetness(), 0.f, 1.f) * WetTableLiftCm : 0.f;
	if (!FMath::IsNearlyEqual(Lift, WaterLiftCm, 0.05f))
	{
		WaterLiftCm = Lift;
		if (WaterMesh)
		{
			WaterMesh->SetRelativeLocation(FVector(0.f, 0.f, WaterLiftCm));
		}
		if (WaterMaterial)
		{
			WaterMaterial->SetScalarParameterValue(TEXT("WaterTableCm"), CurrentWaterTableCm());
		}
	}
}

float AGTMudPatch::WaterDepthCmAt(const FVector2D& XYCm) const
{
	// LM3a: no water in snow (the field there is relative to the snow top, not the ground the table is measured from).
	return IsSnow() ? 0.f : FMath::Max(0.f, CurrentWaterTableCm() - Field.HeightAt(XYCm));
}

FVector AGTMudPatch::NearestPuddleCm(FVector2D FromCm, float MinDepthCm) const
{
	FVector Best(0.0, 0.0, -1.0);
	double BestD2 = TNumericLimits<double>::Max();
	if (!Field.IsValid())
	{
		return Best;
	}
	const int32 Cells = Field.SizeX * Field.SizeY;
	for (int32 Index = 0; Index < Cells; ++Index)
	{
		const float Depth = WaterTableCm - Field.SurfaceCm(Index);
		if (Depth < MinDepthCm)
		{
			continue;
		}
		const FVector2D C = Field.CellCentreCm(Index);
		const double D2 = FVector2D::DistSquared(C, FromCm);
		if (D2 < BestD2)
		{
			BestD2 = D2;
			Best = FVector(C.X, C.Y, Depth);
		}
	}
	return Best;
}

FString AGTMudPatch::DescribeMuddyWater(FVector2D CentreCm, float RadiusCm) const
{
	// MR3: the rut water round a point, cell by cell (the checks' readout).
	const FGTMudField& F = Field;
	if (!F.IsValid() || F.Turbidity.Num() != F.SizeX * F.SizeY)
	{
		return TEXT("no turbidity (snow or no field)");
	}
	int32 Wet = 0, Turbid = 0, Froth = 0;
	float Max = 0.f;
	double Sum = 0.0;
	const float R = FMath::Max(0.f, RadiusCm);
	const int32 X0 = FMath::Max(0, FMath::FloorToInt((CentreCm.X - R - F.OriginCm.X) / F.CellCm));
	const int32 X1 = FMath::Min(F.SizeX - 1, FMath::FloorToInt((CentreCm.X + R - F.OriginCm.X) / F.CellCm));
	const int32 Y0 = FMath::Max(0, FMath::FloorToInt((CentreCm.Y - R - F.OriginCm.Y) / F.CellCm));
	const int32 Y1 = FMath::Min(F.SizeY - 1, FMath::FloorToInt((CentreCm.Y + R - F.OriginCm.Y) / F.CellCm));
	for (int32 Y = Y0; Y <= Y1; ++Y)
	{
		for (int32 X = X0; X <= X1; ++X)
		{
			const FVector2D At = F.OriginCm + FVector2D(X + 0.5, Y + 0.5) * F.CellCm;
			const int32 I = Y * F.SizeX + X;
			if (FVector2D::Distance(At, CentreCm) > R || F.WaterOverCm(I) <= 0.f)
			{
				continue;
			}
			++Wet;
			const float T = F.Turbidity[I];
			Sum += T;
			Max = FMath::Max(Max, T);
			Turbid += T > 0.5f ? 1 : 0;
			Froth += (T > 0.5f && F.Fresh.IsValidIndex(I) && F.Fresh[I] > 0.3f) ? 1 : 0;
		}
	}
	return FString::Printf(TEXT("wet %d, turbid %d, max %.3f, wet mean %.3f, froth %d, turbid tiles %d, table %.1f cm, switch %d"),
		Wet, Turbid, Max, Wet > 0 ? Sum / Wet : 0.0, Froth, F.TurbidTileCount(), F.RutWaterTableCm, F.bMuddyWater ? 1 : 0);
}

bool AGTMudPatch::IsWaterDrawn() const
{
	return WaterMesh != nullptr && bWaterMaterialLoaded && WaterVertexCount > 0 && WaterMesh->IsVisible();
}

bool AGTMudPatch::TraceGround(float XCm, float YCm, float& OutZ) const
{
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTMudPatchGround), false, this);
	if (GetWorld()->LineTraceSingleByObjectType(Hit, FVector(XCm, YCm, 50000.f), FVector(XCm, YCm, -50000.f), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
	{
		OutZ = Hit.ImpactPoint.Z;
		return true;
	}
	return false;
}

int32 AGTMudPatch::BuildMesh()
{
	MeshVertexCount = 0;
	MeshTriangleCount = 0;
	MeshGroundMisses = 0;
	MeshBounds = FBox(ForceInit);
	MeshRestZ.Reset();
	if (!Mesh || !Field.IsValid() || !GetWorld())
	{
		return 0;
	}
	const FBox2D Footprint = Field.Bounds();
	const FVector2D Size = Footprint.GetSize();
	MeshCellCm = FMath::Max(5.f, MeshCellCm);
	MeshVerticesX = FMath::Clamp(FMath::CeilToInt(Size.X / MeshCellCm), 1, 2048) + 1;
	MeshVerticesY = FMath::Clamp(FMath::CeilToInt(Size.Y / MeshCellCm), 1, 2048) + 1;
	const float StepX = Size.X / (MeshVerticesX - 1);
	const float StepY = Size.Y / (MeshVerticesY - 1);
	const int32 Count = MeshVerticesX * MeshVerticesY;

	// The ground under each vertex: the landscape's collision heightfield (what the wheels see), a trace where none answers.
	TArray<ALandscapeProxy*> Landscapes;
	for (TActorIterator<ALandscapeProxy> It(GetWorld()); It; ++It)
	{
		Landscapes.Add(*It);
	}
	MeshRestZ.SetNumUninitialized(Count);
	TBitArray<> Found(false, Count);
	float Lowest = TNumericLimits<float>::Max();
	// Stage D: the outermost vertex ring sits EdgeLipCm over the ground, fading to 0 at the second ring (a one-cell
	// ramp). The landscape's hole is the box shrunk by one cell, so that ring is the only place the two surfaces
	// overlap: the lip keeps it off the landscape's depth (no z-fight) and puts mud, not sky, behind any crack the
	// landscape's LOD morphing opens at the border. Everything inside rests on the ground (MeshLiftCm 0).
	auto LiftAt = [this](int32 I, int32 J)
	{
		const int32 Ring = FMath::Min(FMath::Min(I, MeshVerticesX - 1 - I), FMath::Min(J, MeshVerticesY - 1 - J));
		return MeshLiftCm + (Ring == 0 ? EdgeLipCm : 0.f);
	};
	for (int32 J = 0; J < MeshVerticesY; ++J)
	{
		for (int32 I = 0; I < MeshVerticesX; ++I)
		{
			const float X = Footprint.Min.X + I * StepX;
			const float Y = Footprint.Min.Y + J * StepY;
			float Z = 0.f;
			bool bFound = false;
			for (ALandscapeProxy* Landscape : Landscapes)
			{
				const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(X, Y, 0.f));
				if (Height.IsSet())
				{
					Z = Height.GetValue();
					bFound = true;
					break;
				}
			}
			if (!bFound)
			{
				bFound = TraceGround(X, Y, Z);
			}
			const int32 Index = J * MeshVerticesX + I;
			// LM3a: a snow patch rests on the snow's top, SnowDepthCm x the taper over the ground (0 at the box's border).
			const float Lift = LiftAt(I, J) + Field.SnowTopAt(FVector2D(X, Y));
			Found[Index] = bFound;
			MeshRestZ[Index] = bFound ? Z + Lift : 0.f;
			if (bFound)
			{
				Lowest = FMath::Min(Lowest, Z + Lift);
			}
			else
			{
				++MeshGroundMisses;
			}
		}
	}
	if (MeshGroundMisses > 0)
	{
		const float Fill = Lowest < TNumericLimits<float>::Max() ? Lowest : 0.f;
		for (int32 Index = 0; Index < Count; ++Index)
		{
			if (!Found[Index])
			{
				MeshRestZ[Index] = Fill;
			}
		}
	}
	// Benmore B2: a zone patch's vertices on the zone's edge go a little under the ground, the ring's outer ones further, so the
	// landscape (which draws everywhere outside the coverage hole) covers them and only the hole shows the mesh (ZoneEdgeSinkCm).
	const bool bZoneGrid = bZonePatch && ZoneCells.Num() == Field.SizeX * Field.SizeY && MeshVerticesX == Field.SizeX + 1 && MeshVerticesY == Field.SizeY + 1;
	if (bZoneGrid)
	{
		auto CellAt = [this](int32 X, int32 Y) -> uint8 { return (X >= 0 && Y >= 0 && X < Field.SizeX && Y < Field.SizeY) ? ZoneCells[Y * Field.SizeX + X] : 0; };
		for (int32 J = 0; J < MeshVerticesY; ++J)
		{
			for (int32 I = 0; I < MeshVerticesX; ++I)
			{
				int32 Members = 0;
				for (int32 DY = -1; DY <= 0; ++DY)
				{
					for (int32 DX = -1; DX <= 0; ++DX)
					{
						Members += CellAt(I + DX, J + DY) == 2 ? 1 : 0;
					}
				}
				float Sink = 0.f;
				if (Members == 0)
				{
					Sink = ZoneRingSinkCm;
				}
				else if (Members < 4)
				{
					Sink = ZoneEdgeSinkCm;
				}
				else
				{
					bool bNearEdge = false;
					for (int32 DY = -2; DY <= 1 && !bNearEdge; ++DY)
					{
						for (int32 DX = -2; DX <= 1; ++DX)
						{
							if (CellAt(I + DX, J + DY) != 2)
							{
								bNearEdge = true;
								break;
							}
						}
					}
					Sink = bNearEdge ? 0.5f * ZoneEdgeSinkCm : 0.f;
				}
				MeshRestZ[J * MeshVerticesX + I] -= Sink;
			}
		}
	}

	// Benmore B2c: a zone patch takes the landscape's own vertex normals (central differences on its 124 cm grid, bilinear between its
	// vertices) and the landscape vertex factory's tangent (N.z, 0, -N.x), so a patch wearing the landscape's material shades as it does.
	TArray<FVector> ZoneNormals;
	if (bZonePatch && Landscapes.Num() > 0)
	{
		const FTransform LT = Landscapes[0]->GetActorTransform();
		const FVector LS = LT.GetScale3D();
		const FVector LO = LT.GetLocation();
		if (LS.X > 1.0 && LS.Y > 1.0)
		{
			const int32 LX0 = FMath::FloorToInt((Footprint.Min.X - LO.X) / LS.X) - 2;
			const int32 LY0 = FMath::FloorToInt((Footprint.Min.Y - LO.Y) / LS.Y) - 2;
			const int32 LW = FMath::CeilToInt((Footprint.Max.X - LO.X) / LS.X) + 2 - LX0 + 1;
			const int32 LH = FMath::CeilToInt((Footprint.Max.Y - LO.Y) / LS.Y) + 2 - LY0 + 1;
			TArray<float> LHeights;
			LHeights.SetNumUninitialized(LW * LH);
			for (int32 J = 0; J < LH; ++J)
			{
				for (int32 I = 0; I < LW; ++I)
				{
					const FVector P(LO.X + (LX0 + I) * LS.X, LO.Y + (LY0 + J) * LS.Y, 0.0);
					float Z = 0.f;
					for (ALandscapeProxy* Landscape : Landscapes)
					{
						const TOptional<float> Height = Landscape->GetHeightAtLocation(P);
						if (Height.IsSet())
						{
							Z = Height.GetValue();
							break;
						}
					}
					LHeights[J * LW + I] = Z;
				}
			}
			auto LNormal = [&](int32 I, int32 J)
			{
				I = FMath::Clamp(I, 1, LW - 2);
				J = FMath::Clamp(J, 1, LH - 2);
				const float DX = (LHeights[J * LW + I + 1] - LHeights[J * LW + I - 1]) / (2.f * LS.X);
				const float DY = (LHeights[(J + 1) * LW + I] - LHeights[(J - 1) * LW + I]) / (2.f * LS.Y);
				return FVector(-DX, -DY, 1.f).GetSafeNormal();
			};
			ZoneNormals.SetNumUninitialized(Count);
			for (int32 J = 0; J < MeshVerticesY; ++J)
			{
				for (int32 I = 0; I < MeshVerticesX; ++I)
				{
					const double FX = (Footprint.Min.X + I * StepX - LO.X) / LS.X - LX0;
					const double FY = (Footprint.Min.Y + J * StepY - LO.Y) / LS.Y - LY0;
					const int32 IX = FMath::FloorToInt(FX);
					const int32 IY = FMath::FloorToInt(FY);
					const float TX = static_cast<float>(FX - IX);
					const float TY = static_cast<float>(FY - IY);
					const FVector N = FMath::Lerp(FMath::Lerp(LNormal(IX, IY), LNormal(IX + 1, IY), TX), FMath::Lerp(LNormal(IX, IY + 1), LNormal(IX + 1, IY + 1), TX), TY);
					ZoneNormals[J * MeshVerticesX + I] = N.GetSafeNormal();
				}
			}
		}
	}
	const FVector ActorLocation = GetActorLocation();
	TArray<FVector> Vertices;
	TArray<FVector> Normals;
	TArray<FVector2D> UV0;
	TArray<FLinearColor> Colours;
	TArray<FProcMeshTangent> Tangents;
	TArray<int32> Triangles;
	Vertices.Reserve(Count);
	Normals.Reserve(Count);
	UV0.Reserve(Count);
	Colours.Reserve(Count);
	Tangents.Reserve(Count);
	Triangles.Reserve((MeshVerticesX - 1) * (MeshVerticesY - 1) * 6);
	auto RestZ = [this](int32 I, int32 J)
	{
		return MeshRestZ[FMath::Clamp(J, 0, MeshVerticesY - 1) * MeshVerticesX + FMath::Clamp(I, 0, MeshVerticesX - 1)];
	};
	for (int32 J = 0; J < MeshVerticesY; ++J)
	{
		for (int32 I = 0; I < MeshVerticesX; ++I)
		{
			const float X = Footprint.Min.X + I * StepX;
			const float Y = Footprint.Min.Y + J * StepY;
			const float Z = RestZ(I, J);
			Vertices.Add(FVector(X - ActorLocation.X, Y - ActorLocation.Y, Z - ActorLocation.Z));
			MeshBounds += FVector(X, Y, Z);
			// The ground's slope from the neighbours (one-sided at the edge): the mud material adds the field's slope to it.
			const float DZDX = (RestZ(I + 1, J) - RestZ(I - 1, J)) / ((FMath::Min(I + 1, MeshVerticesX - 1) - FMath::Max(I - 1, 0)) * StepX);
			const float DZDY = (RestZ(I, J + 1) - RestZ(I, J - 1)) / ((FMath::Min(J + 1, MeshVerticesY - 1) - FMath::Max(J - 1, 0)) * StepY);
			if (ZoneNormals.Num() == Count)
			{
				const FVector N = ZoneNormals[J * MeshVerticesX + I];
				Normals.Add(N);
				Tangents.Add(FProcMeshTangent(FVector(N.Z, 0.0, -N.X).GetSafeNormal(), false));   // the landscape vertex factory's tangent
			}
			else
			{
				Normals.Add(FVector(-DZDX, -DZDY, 1.f).GetSafeNormal());
				Tangents.Add(FProcMeshTangent(1.f, 0.f, 0.f));
			}
			UV0.Add(FVector2D((X - Footprint.Min.X) / Size.X, (Y - Footprint.Min.Y) / Size.Y));
			Colours.Add(FLinearColor::White);
		}
	}
	ZoneDrawnQuads = 0;
	for (int32 J = 0; J < MeshVerticesY - 1; ++J)
	{
		for (int32 I = 0; I < MeshVerticesX - 1; ++I)
		{
			const int32 V00 = J * MeshVerticesX + I;
			const int32 V10 = V00 + 1;
			const int32 V01 = V00 + MeshVerticesX;
			const int32 V11 = V01 + 1;
			// Benmore B2: a zone patch draws its own region's zone cells and the ring round them, nothing else.
			if (bZoneGrid)
			{
				if (!ZoneQuadDrawn(I, J))
				{
					continue;
				}
				++ZoneDrawnQuads;
			}
			// Wound so the computed face normal points up (the material is one-sided since section 30).
			Triangles.Add(V00);
			Triangles.Add(V01);
			Triangles.Add(V10);
			Triangles.Add(V10);
			Triangles.Add(V01);
			Triangles.Add(V11);
		}
	}
	// Benmore B2: skirts ZoneSkirtCm deep under every drawn quad's edge on the own region's border (a tile whose neighbour is not
	// active, or a rut that runs into the border): the gap between the field's surface and the landscape beyond shows mud, not sky.
	if (bZoneGrid && ZoneSkirtCm > 0.f)
	{
		auto AddSkirt = [&](int32 VA, int32 VB, const FVector2D& Out)
		{
			const FVector PA = Vertices[VA];
			const FVector PB = Vertices[VB];
			const int32 SA = Vertices.Num();
			for (const int32 V : { VA, VB })
			{
				// Copies first: an element of the array being added to may move when it grows.
				const FVector Down = Vertices[V] - FVector(0.0, 0.0, ZoneSkirtCm);
				const FVector N = Normals[V];
				const FVector2D UV = UV0[V];
				const FLinearColor Colour = Colours[V];
				const FProcMeshTangent Tangent = Tangents[V];
				Vertices.Add(Down);
				Normals.Add(N);
				UV0.Add(UV);
				Colours.Add(Colour);
				Tangents.Add(Tangent);
			}
			// Facing the patch's inside (the grid's winding: the visible side is opposite the right-handed cross).
			const FVector Edge = PB - PA;
			const bool bAB = (-Edge.Y * Out.X + Edge.X * Out.Y) > 0.0;
			const int32 P = bAB ? VA : VB;
			const int32 Q = bAB ? VB : VA;
			const int32 PD = bAB ? SA : SA + 1;
			const int32 QD = bAB ? SA + 1 : SA;
			Triangles.Append({ P, Q, PD, Q, QD, PD });
		};
		auto InOwn = [this](int32 X, int32 Y)
		{
			const FVector2D C = Field.OriginCm + FVector2D(X + 0.5, Y + 0.5) * Field.CellCm;
			return C.X >= ZoneOwnBoxCm.Min.X && C.Y >= ZoneOwnBoxCm.Min.Y && C.X < ZoneOwnBoxCm.Max.X && C.Y < ZoneOwnBoxCm.Max.Y;
		};
		for (int32 J = 0; J < MeshVerticesY - 1; ++J)
		{
			for (int32 I = 0; I < MeshVerticesX - 1; ++I)
			{
				if (!ZoneQuadDrawn(I, J))
				{
					continue;
				}
				const int32 V00 = J * MeshVerticesX + I;
				if (!InOwn(I - 1, J)) { AddSkirt(V00, V00 + MeshVerticesX, FVector2D(-1.0, 0.0)); }
				if (!InOwn(I + 1, J)) { AddSkirt(V00 + 1, V00 + MeshVerticesX + 1, FVector2D(1.0, 0.0)); }
				if (!InOwn(I, J - 1)) { AddSkirt(V00, V00 + 1, FVector2D(0.0, -1.0)); }
				if (!InOwn(I, J + 1)) { AddSkirt(V00 + MeshVerticesX, V00 + MeshVerticesX + 1, FVector2D(0.0, 1.0)); }
			}
		}
	}
	// LM4e cut 4: a snow patch's surface in chunks with distance LODs (gt.Snow.MeshLod); the grid component keeps no section then.
	const bool bChunks = IsSnow() && CVarSnowMeshLod.GetValueOnGameThread() != 0;
	if (bChunks)
	{
		Mesh->ClearAllMeshSections();
		BuildChunks();
	}
	else
	{
		for (UProceduralMeshComponent* Chunk : ChunkMeshes)
		{
			if (Chunk)
			{
				Chunk->DestroyComponent();
			}
		}
		ChunkMeshes.Reset();
		ChunkBoxes.Reset();
		ChunkLod.Reset();
		ChunkLodTris.Reset();
		ChunkCount = 0;
		DestroyShadowMeshes();   // LM4f item 1: only the chunks have shadow meshes
		Mesh->CreateMeshSection_LinearColor(0, Vertices, Triangles, Normals, UV0, Colours, Tangents, /*bCreateCollision*/ false);
	}
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	// The section's box is the rest surface's; the material moves a vertex down into a rut and up onto a ridge, so the
	// render bounds have to carry that range or the mesh is culled while the camera looks along it (and, since stage D,
	// its shadow with it). MeshBounds stays the rest box: the test and the diagnostic's Z window read it.
	if (const FProcMeshSection* Section = Mesh->GetProcMeshSection(0))
	{
		FProcMeshSection Expanded = *Section;
		if (Expanded.SectionLocalBox.IsValid)
		{
			Expanded.SectionLocalBox.Min.Z -= DisplaceDownCm;
			Expanded.SectionLocalBox.Max.Z += DisplaceUpCm;
			Mesh->SetProcMeshSection(0, Expanded);
		}
	}
	MeshVertexCount = Count;
	MeshTriangleCount = Triangles.Num() / 3;
	DrawnTriangles = MeshTriangleCount;
	if (bChunks)
	{
		// LM4e cut 4: the chunks' LOD 0 sections (the grid and the skirts) are the mesh's triangles; the drawn ones follow the LODs.
		MeshTriangleCount = 0;
		for (int32 Index = 0; Index < ChunkMeshes.Num(); ++Index)
		{
			MeshTriangleCount += ChunkLodTris[Index * 3];
		}
		UpdateChunkLods();
	}

	if (!MeshMaterial)
	{
		if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, *MaterialPath))
		{
			MeshMaterial = UMaterialInstanceDynamic::Create(Base, this);
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("AGTMudPatch: %s missing (run Art/setup_m6_mud.bat); the mud mesh wears the default material"), *MaterialPath);
		}
	}
	bMaterialLoaded = MeshMaterial != nullptr;
	if (MeshMaterial)
	{
		MeshMaterial->SetTextureParameterValue(TEXT("MudField"), Texture);
		MeshMaterial->SetTextureParameterValue(TEXT("MudTread"), TreadTexture);
		MeshMaterial->SetScalarParameterValue(TEXT("LugPeriodCm"), FMath::Max(1.f, LugPeriodCm));   // the field writes the phase in turns of this, so the two must agree
		MeshMaterial->SetVectorParameterValue(TEXT("PatchMin"), FLinearColor(Footprint.Min.X, Footprint.Min.Y, 0.f, 0.f));
		MeshMaterial->SetVectorParameterValue(TEXT("PatchSize"), FLinearColor(Size.X, Size.Y, 0.f, 0.f));
		MeshMaterial->SetVectorParameterValue(TEXT("PatchTexels"), FLinearColor(Field.SizeX, Field.SizeY, 0.f, 0.f));   // a vector parameter's main pin is RGB: no .w
		MeshMaterial->SetScalarParameterValue(TEXT("DiagZ0"), MeshBounds.Min.Z);
		MeshMaterial->SetScalarParameterValue(TEXT("DiagZRange"), FMath::Max(100.f, MeshBounds.Max.Z - MeshBounds.Min.Z));
		MeshMaterial->SetScalarParameterValue(TEXT("MudDiagnostic"), bDiagnostic ? 1.f : 0.f);
		// LM5b: the variant's slice of the bog texture arrays (M_GT_Mud's MudVariant; 0 is Standard, the material's default).
		MeshMaterial->SetScalarParameterValue(TEXT("MudVariant"), static_cast<float>(static_cast<uint8>(MudVariant)));
		// MRD1b item 3: the silt surface's numbers (1 and 1 on every patch but a mud road's: the bog as before).
		MeshMaterial->SetScalarParameterValue(TEXT("SiltTileMul"), RoadSiltTileMul);
		MeshMaterial->SetScalarParameterValue(TEXT("SiltStrength"), RoadSiltStrength);
		// Deformable gravel DG1b: the gravel field's texture slide (M_GT_Gravel's GravelSlideUV; the mud materials have no such parameter).
		MeshMaterial->SetScalarParameterValue(TEXT("GravelSlideUV"), TextureSlideScale);
		// Benmore B2: a zone's tint (M_GT_Gravel_Zone's GravelTint; the strips' materials have no such parameter).
		if (bZonePatch)
		{
			MeshMaterial->SetVectorParameterValue(TEXT("GravelTint"), ZoneSurfaceTint);
			MeshMaterial->SetVectorParameterValue(TEXT("MudTint"), ZoneSurfaceTint);   // B2c: M_GT_Mud_Zone's Benmore palette
		}
		Mesh->SetMaterial(0, MeshMaterial);
		for (UProceduralMeshComponent* Chunk : ChunkMeshes)
		{
			for (int32 Lod = 0; Chunk && Lod < 3; ++Lod)
			{
				Chunk->SetMaterial(Lod, MeshMaterial);
			}
		}
		for (UProceduralMeshComponent* Shadow : ShadowMeshes)   // LM4f item 1: the same displacement
		{
			if (Shadow)
			{
				Shadow->SetMaterial(0, MeshMaterial);
			}
		}
	}
	BuildWaterMesh();
	return Count;
}

// ---- LM4e cut 4, the snow mesh in chunks with distance LODs ------------------------------------------------------------

int32 AGTMudPatch::BuildChunks()
{
	for (UProceduralMeshComponent* Chunk : ChunkMeshes)
	{
		if (Chunk)
		{
			Chunk->DestroyComponent();
		}
	}
	DestroyShadowMeshes();   // LM4f item 1
	ChunkMeshes.Reset();
	ChunkBoxes.Reset();
	ChunkLod.Reset();
	ChunkLodTris.Reset();
	ChunkCount = 0;
	if (MeshVerticesX < 2 || MeshVerticesY < 2 || MeshRestZ.Num() != MeshVerticesX * MeshVerticesY)
	{
		return 0;
	}
	const FBox2D Footprint = Field.Bounds();
	const FVector2D Size = Footprint.GetSize();
	const float StepX = Size.X / (MeshVerticesX - 1);
	const float StepY = Size.Y / (MeshVerticesY - 1);
	const FVector ActorLocation = GetActorLocation();
	const int32 Cells = FMath::Max(8, ChunkCells);
	const int32 LastI = MeshVerticesX - 1;
	const int32 LastJ = MeshVerticesY - 1;
	auto RestZ = [this](int32 I, int32 J)
	{
		return MeshRestZ[FMath::Clamp(J, 0, MeshVerticesY - 1) * MeshVerticesX + FMath::Clamp(I, 0, MeshVerticesX - 1)];
	};
	int32 Total = 0;
	TArray<FVector> Vertices;
	TArray<FVector> Normals;
	TArray<FVector2D> UV0;
	TArray<FLinearColor> Colours;
	TArray<FProcMeshTangent> Tangents;
	TArray<int32> Triangles;
	TArray<int32> Cols;
	TArray<int32> Rows;
	TArray<int32> Edge;
	for (int32 J0 = 0; J0 < LastJ; J0 += Cells)
	{
		for (int32 I0 = 0; I0 < LastI; I0 += Cells)
		{
			const int32 I1 = FMath::Min(I0 + Cells, LastI);
			const int32 J1 = FMath::Min(J0 + Cells, LastJ);
			UProceduralMeshComponent* Chunk = NewObject<UProceduralMeshComponent>(this, *FString::Printf(TEXT("SnowChunk_%d_%d"), I0 / Cells, J0 / Cells));
			Chunk->SetupAttachment(RootComponent);
			Chunk->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Chunk->SetCastShadow(bSurfaceCastShadow);
			Chunk->bUseAsyncCooking = false;
			Chunk->BoundsScale = 1.f;
			Chunk->RegisterComponent();
			FBox Box(ForceInit);
			// LM4f item 1: a fourth pass builds the chunk's shadow mesh, the same grid every ShadowProxyCm (25 cm), no skirts (every
			// shadow mesh has the one spacing, so neighbours share their edges' vertices), hidden in every view and casting the
			// shadow the chunk no longer casts (gt.Snow.ShadowProxy). The same material, so the same displacement from the field.
			UProceduralMeshComponent* Shadow = NewObject<UProceduralMeshComponent>(this, *FString::Printf(TEXT("SnowShadow_%d_%d"), I0 / Cells, J0 / Cells));
			Shadow->SetupAttachment(RootComponent);
			Shadow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Shadow->bUseAsyncCooking = false;
			Shadow->BoundsScale = 1.f;
			Shadow->SetVisibility(false, false);
			Shadow->bCastHiddenShadow = true;
			Shadow->SetCastShadow(false);   // ApplySurfaceShadows turns it on
			Shadow->bVisibleInRayTracing = false;
			Shadow->bAffectDistanceFieldLighting = false;
			Shadow->bAffectDynamicIndirectLighting = false;
			Shadow->SetCanEverAffectNavigation(false);
			Shadow->RegisterComponent();
			const int32 ProxyStep = FMath::Max(1, FMath::RoundToInt(FMath::Max(1.f, ShadowProxyCm) / FMath::Max(1.f, StepX)));
			for (int32 Lod = 0; Lod < 4; ++Lod)
			{
				// The grid's columns and rows every 2^Lod vertices from the chunk's first, its last always kept (so a chunk's corners
				// and its patch-border vertices are the full grid's, whatever the LOD).
				const bool bShadowPass = Lod == 3;
				const int32 Step = bShadowPass ? ProxyStep : 1 << Lod;
				Cols.Reset();
				Rows.Reset();
				for (int32 I = I0; I < I1; I += Step)
				{
					Cols.Add(I);
				}
				Cols.Add(I1);
				for (int32 J = J0; J < J1; J += Step)
				{
					Rows.Add(J);
				}
				Rows.Add(J1);
				Vertices.Reset();
				Normals.Reset();
				UV0.Reset();
				Colours.Reset();
				Tangents.Reset();
				Triangles.Reset();
				// One vertex of the full grid's (I, J), DownCm under its rest (a skirt's foot), with the full grid's normal there.
				auto AddVertex = [&](int32 I, int32 J, float DownCm)
				{
					const float X = Footprint.Min.X + I * StepX;
					const float Y = Footprint.Min.Y + J * StepY;
					const float Z = RestZ(I, J) - DownCm;
					Vertices.Add(FVector(X - ActorLocation.X, Y - ActorLocation.Y, Z - ActorLocation.Z));
					if (DownCm == 0.f)
					{
						Box += FVector(X, Y, Z);
					}
					const float DZDX = (RestZ(I + 1, J) - RestZ(I - 1, J)) / ((FMath::Min(I + 1, MeshVerticesX - 1) - FMath::Max(I - 1, 0)) * StepX);
					const float DZDY = (RestZ(I, J + 1) - RestZ(I, J - 1)) / ((FMath::Min(J + 1, MeshVerticesY - 1) - FMath::Max(J - 1, 0)) * StepY);
					Normals.Add(FVector(-DZDX, -DZDY, 1.f).GetSafeNormal());
					UV0.Add(FVector2D((X - Footprint.Min.X) / Size.X, (Y - Footprint.Min.Y) / Size.Y));
					Colours.Add(FLinearColor::White);
					Tangents.Add(FProcMeshTangent(1.f, 0.f, 0.f));
					return Vertices.Num() - 1;
				};
				for (const int32 J : Rows)
				{
					for (const int32 I : Cols)
					{
						AddVertex(I, J, 0.f);
					}
				}
				const int32 NC = Cols.Num();
				for (int32 R = 0; R + 1 < Rows.Num(); ++R)
				{
					for (int32 C = 0; C + 1 < NC; ++C)
					{
						const int32 V00 = R * NC + C;
						const int32 V10 = V00 + 1;
						const int32 V01 = V00 + NC;
						const int32 V11 = V01 + 1;
						// BuildMesh's winding (the face normal up).
						Triangles.Append({ V00, V01, V10, V10, V01, V11 });
					}
				}
				// The skirts on the inner edges (not the patch's border), each facing out of the chunk: the edge walked so that its
				// direction crossed with +Z is the way out (BuildMesh's winding rule), a quad per step down SkirtCm.
				auto Skirt = [&](bool bAlongX, int32 Fixed, bool bReverse)
				{
					Edge.Reset();
					const TArray<int32>& Along = bAlongX ? Cols : Rows;
					for (int32 K = 0; K < Along.Num(); ++K)
					{
						Edge.Add(Along[bReverse ? Along.Num() - 1 - K : K]);
					}
					int32 PrevTop = INDEX_NONE;
					int32 PrevFoot = INDEX_NONE;
					for (const int32 A : Edge)
					{
						const int32 I = bAlongX ? A : Fixed;
						const int32 J = bAlongX ? Fixed : A;
						const int32 Top = AddVertex(I, J, 0.f);
						const int32 Foot = AddVertex(I, J, FMath::Max(1.f, SkirtCm));
						if (PrevTop != INDEX_NONE)
						{
							Triangles.Append({ PrevTop, Top, PrevFoot, Top, Foot, PrevFoot });
						}
						PrevTop = Top;
						PrevFoot = Foot;
					}
				};
				if (I1 < LastI && !bShadowPass)
				{
					Skirt(false, I1, false);   // +X: walked along +Y
				}
				if (I0 > 0 && !bShadowPass)
				{
					Skirt(false, I0, true);    // -X: along -Y
				}
				if (J1 < LastJ && !bShadowPass)
				{
					Skirt(true, J1, true);     // +Y: along -X
				}
				if (J0 > 0 && !bShadowPass)
				{
					Skirt(true, J0, false);    // -Y: along +X
				}
				UProceduralMeshComponent* Target = bShadowPass ? Shadow : Chunk;
				const int32 ChunkSection = bShadowPass ? 0 : Lod;
				Target->CreateMeshSection_LinearColor(ChunkSection, Vertices, Triangles, Normals, UV0, Colours, Tangents, /*bCreateCollision*/ false);
				// The material's displacement and the skirt in the section's box (as BuildMesh's), or the chunk is culled early.
				if (const FProcMeshSection* Section = Target->GetProcMeshSection(ChunkSection))
				{
					FProcMeshSection Expanded = *Section;
					if (Expanded.SectionLocalBox.IsValid)
					{
						Expanded.SectionLocalBox.Min.Z -= DisplaceDownCm;
						Expanded.SectionLocalBox.Max.Z += DisplaceUpCm;
						Target->SetProcMeshSection(ChunkSection, Expanded);
					}
				}
				if (bShadowPass)
				{
					ShadowProxyTriangles += Triangles.Num() / 3;
					continue;
				}
				Chunk->SetMeshSectionVisible(Lod, Lod == 0);
				ChunkLodTris.Add(Triangles.Num() / 3);
				Total += Vertices.Num();
			}
			ShadowMeshes.Add(Shadow);
			ChunkMeshes.Add(Chunk);
			ChunkBoxes.Add(Box);
			ChunkLod.Add(0);
		}
	}
	ChunkCount = ChunkMeshes.Num();
	// LM4f item 1: who casts the surface's shadow (the chunks, or their shadow meshes), from gt.Snow.ShadowProxy as it is now.
	bShadowProxyOn = CVarSnowShadowProxy.GetValueOnGameThread() != 0;
	ApplySurfaceShadows();
	return Total;
}

void AGTMudPatch::DestroyShadowMeshes()
{
	for (UProceduralMeshComponent* Shadow : ShadowMeshes)
	{
		if (Shadow)
		{
			Shadow->DestroyComponent();
		}
	}
	ShadowMeshes.Reset();
	ShadowProxyTriangles = 0;
}

void AGTMudPatch::ApplySurfaceShadows()
{
	// LM4f item 1: with gt.Snow.ShadowProxy on (and shadow meshes built) the chunks cast nothing and the shadow meshes cast the
	// surface's shadow while the surface is shown; off, the chunks cast as LM4e's did. The test switches (cast, visible) hold for both.
	const bool bProxy = bShadowProxyOn && ShadowMeshes.Num() > 0;
	for (UProceduralMeshComponent* Chunk : ChunkMeshes)
	{
		if (Chunk)
		{
			Chunk->SetCastShadow(bSurfaceCastShadow && !bProxy);
		}
	}
	for (UProceduralMeshComponent* Shadow : ShadowMeshes)
	{
		if (Shadow)
		{
			Shadow->SetCastShadow(bSurfaceCastShadow && bSurfaceVisible && bProxy);
		}
	}
}

void AGTMudPatch::UpdateChunkLods()
{
	// The camera's place (the player's view: the cockpit, or the camera actor a check aims), and per chunk its distance to the
	// chunk's rest box: LOD 0 within LodNearCm, 1 within LodFarCm, else 2, LodHysteresisCm either side before a chunk changes.
	FVector Eye = FVector::ZeroVector;
	bool bEye = false;
	if (const UWorld* World = GetWorld())
	{
		if (const APlayerController* PC = World->GetFirstPlayerController())
		{
			if (PC->PlayerCameraManager)
			{
				Eye = PC->PlayerCameraManager->GetCameraLocation();
				bEye = true;
			}
		}
	}
	ChunksAtLod = FIntVector::ZeroValue;
	DrawnTriangles = 0;
	for (int32 Index = 0; Index < ChunkMeshes.Num(); ++Index)
	{
		UProceduralMeshComponent* Chunk = ChunkMeshes[Index];
		if (!Chunk)
		{
			continue;
		}
		int32 Want = ChunkLod[Index];
		if (ForcedLod >= 0)
		{
			Want = FMath::Clamp(ForcedLod, 0, 2);
		}
		else if (bEye)
		{
			const float D = FMath::Sqrt(ChunkBoxes[Index].ComputeSquaredDistanceToPoint(Eye));
			const int32 Current = ChunkLod[Index];
			auto LodAt = [this](float Distance) { return Distance < LodNearCm ? 0 : (Distance < LodFarCm ? 1 : 2); };
			Want = LodAt(D);
			// Hysteresis: move only once past the boundary by LodHysteresisCm.
			if (Want > Current && LodAt(D - LodHysteresisCm) <= Current)
			{
				Want = Current;
			}
			else if (Want < Current && LodAt(D + LodHysteresisCm) >= Current)
			{
				Want = Current;
			}
		}
		if (Want != ChunkLod[Index])
		{
			Chunk->SetMeshSectionVisible(ChunkLod[Index], false);
			Chunk->SetMeshSectionVisible(Want, true);
			ChunkLod[Index] = Want;
		}
		ChunksAtLod[ChunkLod[Index]] += 1;
		DrawnTriangles += ChunkLodTris[Index * 3 + ChunkLod[Index]];
	}
}

void AGTMudPatch::SetSurfaceMaterialForTest(UMaterialInterface* Material)
{
	Mesh->SetMaterial(0, Material);
	for (UProceduralMeshComponent* Chunk : ChunkMeshes)
	{
		for (int32 Lod = 0; Chunk && Lod < 3; ++Lod)
		{
			Chunk->SetMaterial(Lod, Material);
		}
	}
	for (UProceduralMeshComponent* Shadow : ShadowMeshes)   // LM4f item 1
	{
		if (Shadow)
		{
			Shadow->SetMaterial(0, Material);
		}
	}
}

void AGTMudPatch::SetSurfaceCastShadowForTest(bool bCast)
{
	bSurfaceCastShadow = bCast;
	Mesh->SetCastShadow(bCast);
	ApplySurfaceShadows();   // LM4f item 1: the chunks, or their shadow meshes
}

void AGTMudPatch::SetSurfaceVisibleForTest(bool bVisible)
{
	bSurfaceVisible = bVisible;
	Mesh->SetVisibility(bVisible, false);
	for (UProceduralMeshComponent* Chunk : ChunkMeshes)
	{
		if (Chunk)
		{
			Chunk->SetVisibility(bVisible, false);
		}
	}
	ApplySurfaceShadows();   // LM4f item 1: a hidden surface's shadow meshes cast nothing either
}

int32 AGTMudPatch::BuildWaterMesh()
{
	// LM3a: snow holds no water in its cuts.
	if (IsSnow())
	{
		WaterVertexCount = 0;
		WaterTriangleCount = 0;
		bWaterMaterialLoaded = false;
		if (WaterMesh)
		{
			WaterMesh->ClearAllMeshSections();
			WaterMesh->SetVisibility(false);
		}
		return 0;
	}
	// Stage G (docs/MUD_ONE_SURFACE_PLAN.md section 3): the water in the ruts. The same grid as the mud mesh, every
	// vertex WaterTableCm over that mesh's rest height - so the water surface is the local ground plus the table and
	// not one plane per bog - wearing M_GT_MudWater, which reads this patch's field texture and draws nothing at a
	// pixel whose mud stands at or above the table. Only the cells a wheel has cut below it hold water.
	WaterVertexCount = 0;
	WaterTriangleCount = 0;
	bWaterMaterialLoaded = false;
	if (!WaterMesh || MeshVerticesX < 2 || MeshVerticesY < 2 || MeshRestZ.Num() != MeshVerticesX * MeshVerticesY)
	{
		return 0;
	}
	if (!WaterMaterial)
	{
		if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, *WaterMaterialPath))
		{
			WaterMaterial = UMaterialInstanceDynamic::Create(Base, this);
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("AGTMudPatch: %s missing (run Art/setup_m6_water.bat); the ruts hold no water"), *WaterMaterialPath);
		}
	}
	bWaterMaterialLoaded = WaterMaterial != nullptr;
	if (!bWaterMaterialLoaded)
	{
		WaterMesh->SetVisibility(false);   // a white default sheet over the bog would be worse than no water
		return 0;
	}
	const FBox2D Footprint = Field.Bounds();
	const FVector2D Size = Footprint.GetSize();
	const float StepX = Size.X / (MeshVerticesX - 1);
	const float StepY = Size.Y / (MeshVerticesY - 1);
	const FVector ActorLocation = GetActorLocation();
	const int32 Count = MeshVerticesX * MeshVerticesY;
	TArray<FVector> Vertices;
	TArray<FVector> Normals;
	TArray<FVector2D> UV0;
	TArray<FLinearColor> Colours;
	TArray<FProcMeshTangent> Tangents;
	TArray<int32> Triangles;
	Vertices.Reserve(Count);
	Normals.Reserve(Count);
	UV0.Reserve(Count);
	Colours.Reserve(Count);
	Tangents.Reserve(Count);
	Triangles.Reserve((MeshVerticesX - 1) * (MeshVerticesY - 1) * 6);
	for (int32 J = 0; J < MeshVerticesY; ++J)
	{
		for (int32 I = 0; I < MeshVerticesX; ++I)
		{
			const float X = Footprint.Min.X + I * StepX;
			const float Y = Footprint.Min.Y + J * StepY;
			const float Z = MeshRestZ[J * MeshVerticesX + I] + WaterTableCm;
			Vertices.Add(FVector(X - ActorLocation.X, Y - ActorLocation.Y, Z - ActorLocation.Z));
			// Flat: a water surface is level whatever the ground under it does, and the fresnel in the material reads
			// this normal. The sheet still follows the ground from vertex to vertex; only its facets are level.
			Normals.Add(FVector::UpVector);
			UV0.Add(FVector2D((X - Footprint.Min.X) / Size.X, (Y - Footprint.Min.Y) / Size.Y));
			Colours.Add(FLinearColor::White);
			Tangents.Add(FProcMeshTangent(1.f, 0.f, 0.f));
		}
	}
	// RIVERBED S4 (VEHICLE_BUILD_SYSTEM 54): a patch with a deformation profile (a ford's bed) draws no rut water where a
	// water sheet covers the ground: the ford's water is the sheet's. The sheets have not begun play when the patches are
	// built, so Covers answers the placed box (what it answered before RIVERBED S3); a quad with any corner covered is left
	// out. A bog keeps its whole grid (the Hide's placed sheet box reaches over the bog's far end; that stays as it was).
	TArray<const AGTWaterSheet*> CoveringSheets;
	if (bHasProfile)
	{
		for (TActorIterator<AGTWaterSheet> It(GetWorld()); It; ++It)
		{
			CoveringSheets.Add(*It);
		}
	}
	TBitArray<> Covered(false, Count);
	if (CoveringSheets.Num() > 0)
	{
		for (int32 J = 0; J < MeshVerticesY; ++J)
		{
			for (int32 I = 0; I < MeshVerticesX; ++I)
			{
				const FVector2D XY(Footprint.Min.X + I * StepX, Footprint.Min.Y + J * StepY);
				for (const AGTWaterSheet* Sheet : CoveringSheets)
				{
					if (Sheet->Covers(XY))
					{
						Covered[J * MeshVerticesX + I] = true;
						break;
					}
				}
			}
		}
	}
	WaterQuadsUnderSheet = 0;
	for (int32 J = 0; J < MeshVerticesY - 1; ++J)
	{
		for (int32 I = 0; I < MeshVerticesX - 1; ++I)
		{
			const int32 V00 = J * MeshVerticesX + I;
			const int32 V10 = V00 + 1;
			const int32 V01 = V00 + MeshVerticesX;
			const int32 V11 = V01 + 1;
			if (Covered[V00] || Covered[V10] || Covered[V01] || Covered[V11])
			{
				++WaterQuadsUnderSheet;
				continue;
			}
			if (bZonePatch && !ZoneQuadDrawn(I, J))   // Benmore B2: the water only over the drawn quads
			{
				continue;
			}
			Triangles.Add(V00);
			Triangles.Add(V01);
			Triangles.Add(V10);
			Triangles.Add(V10);
			Triangles.Add(V01);
			Triangles.Add(V11);
		}
	}
	if (Triangles.Num() == 0)
	{
		// Every quad under a sheet: no rut-water grid at all.
		WaterMesh->ClearAllMeshSections();
		WaterMesh->SetVisibility(false);
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: water grid off, all %d quads under a water sheet (RIVERBED S4: the ford's water is the sheet's)"), SectionIndex, WaterQuadsUnderSheet);
		return 0;
	}
	WaterMesh->CreateMeshSection_LinearColor(0, Vertices, Triangles, Normals, UV0, Colours, Tangents, /*bCreateCollision*/ false);
	WaterMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	WaterMesh->SetRelativeLocation(FVector(0.f, 0.f, WaterLiftCm));
	WaterVertexCount = Count;
	WaterTriangleCount = Triangles.Num() / 3;
	WaterMaterial->SetTextureParameterValue(TEXT("MudField"), Texture);
	// MRD1b item 1: the variant, for the opaque body's mud tint (its bog slice's mean).
	WaterMaterial->SetScalarParameterValue(TEXT("MudVariant"), static_cast<float>(static_cast<uint8>(MudVariant)));
	WaterMaterial->SetVectorParameterValue(TEXT("PatchMin"), FLinearColor(Footprint.Min.X, Footprint.Min.Y, 0.f, 0.f));
	WaterMaterial->SetVectorParameterValue(TEXT("PatchSize"), FLinearColor(Size.X, Size.Y, 0.f, 0.f));
	WaterMaterial->SetScalarParameterValue(TEXT("WaterTableCm"), CurrentWaterTableCm());
	// MR3: the churned water's turbidity rides in the tread texture's A (the fresh sheen in B: the froth), and the switch.
	WaterMaterial->SetTextureParameterValue(TEXT("MudTread"), TreadTexture);
	PushedMuddyWater = CVarMudMuddyWater.GetValueOnGameThread() != 0 ? 1.f : 0.f;
	WaterMaterial->SetScalarParameterValue(TEXT("MuddyWater"), PushedMuddyWater);
	Field.RutWaterTableCm = CurrentWaterTableCm();
	WaterMesh->SetMaterial(0, WaterMaterial);
	WaterMesh->SetVisibility(true);
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: water grid %d vertices (%d x %d), %d triangles, table %.1f cm over the ground (lift %.1f, at wetness 1 %.1f), material M_GT_MudWater; %d quads left out under a water sheet"),
		SectionIndex, WaterVertexCount, MeshVerticesX, MeshVerticesY, WaterTriangleCount, WaterTableCm, WaterLiftCm, WetTableLiftCm, WaterQuadsUnderSheet);
	return WaterVertexCount;
}

void AGTMudPatch::SetDiagnostic(bool bOn, float WindowZ0, float WindowRangeCm)
{
	bDiagnostic = bOn;
	if (MeshMaterial)
	{
		MeshMaterial->SetScalarParameterValue(TEXT("MudDiagnostic"), bOn ? 1.f : 0.f);
		const bool bWindow = WindowRangeCm > 0.f;
		MeshMaterial->SetScalarParameterValue(TEXT("DiagZ0"), bWindow ? WindowZ0 : MeshBounds.Min.Z);
		MeshMaterial->SetScalarParameterValue(TEXT("DiagZRange"), bWindow ? WindowRangeCm : FMath::Max(100.f, MeshBounds.Max.Z - MeshBounds.Min.Z));
	}
}

float AGTMudPatch::MeshRestZAt(const FVector2D& XYCm) const
{
	if (MeshVerticesX < 2 || MeshVerticesY < 2 || MeshRestZ.Num() != MeshVerticesX * MeshVerticesY)
	{
		return 0.f;
	}
	const FBox2D Footprint = Field.Bounds();
	const FVector2D Size = Footprint.GetSize();
	const float GX = (XYCm.X - Footprint.Min.X) / Size.X * (MeshVerticesX - 1);
	const float GY = (XYCm.Y - Footprint.Min.Y) / Size.Y * (MeshVerticesY - 1);
	const int32 X0 = FMath::Clamp(FMath::FloorToInt(GX), 0, MeshVerticesX - 2);
	const int32 Y0 = FMath::Clamp(FMath::FloorToInt(GY), 0, MeshVerticesY - 2);
	const float FX = FMath::Clamp(GX - X0, 0.f, 1.f);
	const float FY = FMath::Clamp(GY - Y0, 0.f, 1.f);
	auto At = [this](int32 I, int32 J) { return MeshRestZ[J * MeshVerticesX + I]; };
	return FMath::Lerp(FMath::Lerp(At(X0, Y0), At(X0 + 1, Y0), FX), FMath::Lerp(At(X0, Y0 + 1), At(X0 + 1, Y0 + 1), FX), FY);
}

void AGTMudPatch::Upload(const FIntRect& Rect)
{
	if (!Texture || !Texture->GetResource())
	{
		return;
	}
	const int32 Width = Rect.Width();
	const int32 Height = Rect.Height();
	if (Width <= 0 || Height <= 0)
	{
		return;
	}
	TArray<FFloat16Color>* Data = new TArray<FFloat16Color>();
	Data->SetNumUninitialized(Width * Height);
	// Stage F: the tread goes up with the same rect (R the stamping heading in turns, G the lug phase; both 0 where no
	// wheel has been, where the material's depth and tracks gates keep the lugs off anyway). LM1: B the fresh sheen,
	// 0 with gt.Mud.Settle off (nothing fades it then, so it is not drawn).
	TArray<FFloat16Color>* Tread = TreadTexture && TreadTexture->GetResource() ? new TArray<FFloat16Color>() : nullptr;
	if (Tread)
	{
		Tread->SetNumUninitialized(Width * Height);
	}
	for (int32 Y = 0; Y < Height; ++Y)
	{
		for (int32 X = 0; X < Width; ++X)
		{
			const int32 Index = (Rect.Min.Y + Y) * Field.SizeX + Rect.Min.X + X;
			EncodeCell(Index, (*Data)[Y * Width + X], Tread ? &(*Tread)[Y * Width + X] : nullptr);
		}
	}
	FUpdateTextureRegion2D* Region = new FUpdateTextureRegion2D(Rect.Min.X, Rect.Min.Y, 0, 0, Width, Height);
	Texture->UpdateTextureRegions(0, 1, Region, Width * sizeof(FFloat16Color), sizeof(FFloat16Color), reinterpret_cast<uint8*>(Data->GetData()),
		[Data](uint8*, const FUpdateTextureRegion2D* Regions)
		{
			delete Data;
			delete Regions;
		});
	if (Tread)
	{
		FUpdateTextureRegion2D* TreadRegion = new FUpdateTextureRegion2D(Rect.Min.X, Rect.Min.Y, 0, 0, Width, Height);
		TreadTexture->UpdateTextureRegions(0, 1, TreadRegion, Width * sizeof(FFloat16Color), sizeof(FFloat16Color), reinterpret_cast<uint8*>(Tread->GetData()),
			[Tread](uint8*, const FUpdateTextureRegion2D* Regions)
			{
				delete Tread;
				delete Regions;
			});
	}
	++UploadCount;
}

void AGTMudPatch::EncodeCell(int32 Index, FFloat16Color& OutField, FFloat16Color* OutTread) const
{
	OutField = FFloat16Color(FLinearColor(Field.SurfaceCm(Index) * 0.01f, Field.OffsetCm[Index].X * 0.01f, Field.OffsetCm[Index].Y * 0.01f, Field.Tracks[Index] / 255.f));
	if (OutTread)
	{
		// LM3c: A, snow only (0 on mud as before): the lug strength where a tyre's tread is set, -1 where the belly scraped.
		// LM4 item 5: B on snow is the crust plates' mask (M_GT_Snow does not draw mud's fresh sheen; 0 with the plates off).
		const float B = Field.bSnow ? Field.PlateAlpha(Index) : (bSettleOn ? Field.Fresh[Index] : 0.f);
		*OutTread = FFloat16Color(FLinearColor(Field.HeadingTurns[Index], FMath::Max(0.f, Field.PhaseTurns[Index]), B, Field.TreadAlpha(Index)));
	}
}

int32 AGTMudPatch::UploadRects(const TArray<FIntRect>& Rects)
{
	// LM4e cut 2: every box stacked in one buffer (as wide as the widest, a box's rows one under the other) and one region per
	// box, so the two textures take one update each and only the cells that changed are encoded.
	if (!Texture || !Texture->GetResource() || Rects.Num() == 0)
	{
		return 0;
	}
	int32 Pitch = 0;
	int32 Rows = 0;
	int32 Cells = 0;
	for (const FIntRect& R : Rects)
	{
		Pitch = FMath::Max(Pitch, R.Width());
		Rows += FMath::Max(0, R.Height());
		Cells += FMath::Max(0, R.Width()) * FMath::Max(0, R.Height());
	}
	if (Pitch <= 0 || Rows <= 0)
	{
		return 0;
	}
	const bool bTread = TreadTexture && TreadTexture->GetResource();
	TArray<FFloat16Color>* Data = new TArray<FFloat16Color>();
	Data->SetNumUninitialized(Pitch * Rows);
	TArray<FFloat16Color>* Tread = bTread ? new TArray<FFloat16Color>() : nullptr;
	if (Tread)
	{
		Tread->SetNumUninitialized(Pitch * Rows);
	}
	FUpdateTextureRegion2D* Regions = new FUpdateTextureRegion2D[Rects.Num()];
	FUpdateTextureRegion2D* TreadRegions = bTread ? new FUpdateTextureRegion2D[Rects.Num()] : nullptr;
	int32 Row0 = 0;
	for (int32 K = 0; K < Rects.Num(); ++K)
	{
		const FIntRect& R = Rects[K];
		const int32 W = FMath::Max(0, R.Width());
		const int32 H = FMath::Max(0, R.Height());
		Regions[K] = FUpdateTextureRegion2D(R.Min.X, R.Min.Y, 0, Row0, W, H);
		if (TreadRegions)
		{
			TreadRegions[K] = Regions[K];
		}
		for (int32 Y = 0; Y < H; ++Y)
		{
			FFloat16Color* DataRow = Data->GetData() + (Row0 + Y) * Pitch;
			FFloat16Color* TreadRow = Tread ? Tread->GetData() + (Row0 + Y) * Pitch : nullptr;
			Field.EncodeTexels((R.Min.Y + Y) * Field.SizeX + R.Min.X, W, DataRow, TreadRow, bSettleOn);
		}
		Row0 += H;
	}
	Texture->UpdateTextureRegions(0, Rects.Num(), Regions, Pitch * sizeof(FFloat16Color), sizeof(FFloat16Color), reinterpret_cast<uint8*>(Data->GetData()),
		[Data](uint8*, const FUpdateTextureRegion2D* InRegions)
		{
			delete Data;
			delete[] InRegions;
		});
	if (Tread)
	{
		TreadTexture->UpdateTextureRegions(0, Rects.Num(), TreadRegions, Pitch * sizeof(FFloat16Color), sizeof(FFloat16Color), reinterpret_cast<uint8*>(Tread->GetData()),
			[Tread](uint8*, const FUpdateTextureRegion2D* InRegions)
			{
				delete Tread;
				delete[] InRegions;
			});
	}
	++UploadCount;
	return Cells;
}

// ---- LM2a, the throw's landing ---------------------------------------------------------------------------------

double AGTMudPatch::DepositThrown(const FVector2D& XYCm, double VolumeCm3, float RadiusCm)
{
	// LM4e: timed with the stamps and recorded (the replay calls this, so the clod roll below draws the same numbers).
	// A dome of 1.5 x the blob's radius into the lumps, at least one cell, volume exact; the field wakes the tile and
	// marks the cells fresh. MR5: the dome is DepositLumpDome, which a chunk's break shares.
	const double Put = DepositLumpDome(FGTMudField::EventThrow, XYCm, VolumeCm3, RadiusCm, 1.5f * FMath::Max(0.f, RadiusCm));
	if (Put > 0.0)
	{
		ThrowDepositedCm3 += Put;
		++ThrowDeposits;
		// LM2b: and with ClodThrowChance a clod of the blob's size where it came down (its volume is already in the field).
		if (Field.bQueueClods && ClodRandom.FRand() < ClodThrowChance)
		{
			FGTMudField::FClodSpawn Spawn;
			Spawn.XYCm = XYCm;
			Spawn.SizeCm = FMath::Clamp(2.f * RadiusCm, 1.f, 40.f);
			Spawn.Seed = ClodRandom.RandHelper(MAX_int32);
			Spawn.Source = 1;
			Field.QueueClod(Spawn);
		}
	}
	return Put;
}

float AGTMudPatch::BogAt(const FVector2D& XYCm) const
{
	if (!Field.Contains(XYCm))
	{
		return 0.f;
	}
	const int32 Index = Field.CellIndexAt(XYCm);
	return BogMask.IsValidIndex(Index) ? BogMask[Index] / 255.f : 0.f;
}

// ---- LM2b, the clods ---------------------------------------------------------------------------------------------

namespace
{
	/** The clod meshes are 10 cm across at scale 1 (their longest side), their flat face down at the pivot (Art/Blender/build_mud_clods.py); their heights come from their bounds. */
	constexpr float ClodMeshCm = 10.f;
	constexpr float ClodHeightRatio = 0.6f;   // LM2b's one recipe: the fallback height when a mesh has no bounds
	/** LM2c: ten meshes in four families by number: 0-1 rounded blobs, 2-4 pancakes and slabs, 5-7 broken chunks, 8-9 smears. */
	constexpr int32 ClodMeshVariants = 10;
	int32 ClodFamilyOf(int32 Variant)
	{
		return Variant <= 1 ? 0 : (Variant <= 4 ? 1 : (Variant <= 7 ? 2 : 3));
	}
	/** LM2c: the families' odds, banks favouring pancakes and chunks, throws blobs and smears (blob, pancake, chunk, smear). */
	constexpr float ClodBankFamilies[4] = { 0.15f, 0.40f, 0.35f, 0.10f };
	constexpr float ClodThrowFamilies[4] = { 0.40f, 0.10f, 0.15f, 0.35f };
	/** LM4 item 4: the snow shards, SM_GT_SnowChunk_0..7 (Art/Blender/build_snow_chunks.py), one family. */
	constexpr int32 SnowChunkVariants = 8;
}

void AGTMudPatch::InitClods()
{
	for (UHierarchicalInstancedStaticMeshComponent* Old : ClodMeshes)
	{
		if (Old)
		{
			Old->DestroyComponent();
		}
	}
	ClodMeshes.Reset();
	ClodTransforms.Reset();
	ClodFree.Reset();
	ClodDirtyList.Reset();
	ClodDirtyFlag.Reset();
	ClodMeshHeightCm.Reset();
	ClodMeshAcrossCm.Reset();
	ClodMeshFamily.Reset();
	Clods.Reset();
	ClodNext = 0;
	ClodsLive = 0;
	ClodMeshCount = 0;
	bClodDirtyCells = false;
	ClodBatchAccumS = 0.f;
	ClodRandom.Initialize(0xC10D + SectionIndex);
	const int32 TileCells = FMath::Max(1, Field.SettleTileCells);
	ClodTilesX = (Field.SizeX + TileCells - 1) / TileCells;
	ClodTilesY = (Field.SizeY + TileCells - 1) / TileCells;
	TileClods.Reset();
	TileClods.SetNum(ClodTilesX * ClodTilesY);
	if (!Field.IsValid() || MaxClods <= 0)
	{
		return;
	}
	// The meshes by path; a missing one is skipped quietly (no meshes: no instances, no clods).
	TArray<UStaticMesh*> Found;
	TArray<int32> FoundVariant;
	auto FindMeshes = [&Found, &FoundVariant](const FString& Prefix, int32 Variants)
	{
		const FString AssetBase = FPaths::GetCleanFilename(Prefix);
		for (int32 Variant = 0; Variant < Variants; ++Variant)
		{
			const FString Package = FString::Printf(TEXT("%s%d"), *Prefix, Variant);
			if (!FPackageName::DoesPackageExist(Package))
			{
				continue;
			}
			if (UStaticMesh* ClodMesh = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("%s.%s%d"), *Package, *AssetBase, Variant), nullptr, LOAD_NoWarn | LOAD_Quiet))
			{
				Found.Add(ClodMesh);
				FoundVariant.Add(Variant);
			}
		}
	};
	// LM4 item 4: a snow patch draws the snow shards where they are imported (the clods otherwise, as LM3c).
	bShards = false;
	if (IsSnow())
	{
		FindMeshes(SnowChunkPrefix, SnowChunkVariants);
		bShards = Found.Num() > 0;
		if (!bShards)
		{
			UE_LOG(LogTemp, Warning, TEXT("AGTMudPatch %d: no snow shard at %s0..%d (run Art/import_snow_chunks.ps1); the snow draws the clods (LM3c)"), SectionIndex, *SnowChunkPrefix, SnowChunkVariants - 1);
		}
	}
	if (!bShards)
	{
		FindMeshes(ClodMeshPrefix, ClodMeshVariants);
	}
	ClodMeshCount = Found.Num();
	if (Found.Num() == 0)
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: no clod mesh at %s0..%d: no clods (LM2b)"), SectionIndex, *ClodMeshPrefix, ClodMeshVariants - 1);
		return;
	}
	UMaterialInterface* ClodMaterial = FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(ClodMaterialPath))
		? LoadObject<UMaterialInterface>(nullptr, *ClodMaterialPath, nullptr, LOAD_NoWarn | LOAD_Quiet) : nullptr;
	// LM5b: the clods wear their patch's variant slice (M_GT_Clod's MudVariant), bank and thrown alike: one instance per
	// patch. Standard and snow keep the material itself.
	ClodMaterialInstance = nullptr;
	if (ClodMaterial && !IsSnow() && MudVariant != EGTMudVariant::Standard)
	{
		ClodMaterialInstance = UMaterialInstanceDynamic::Create(ClodMaterial, this);
		ClodMaterialInstance->SetScalarParameterValue(TEXT("MudVariant"), static_cast<float>(static_cast<uint8>(MudVariant)));
		ClodMaterial = ClodMaterialInstance;
	}
	const FVector2D Centre = Field.Bounds().GetCenter();
	ClodParkLocation = FVector(Centre.X, Centre.Y, MeshRestZAt(Centre));
	Clods.SetNum(MaxClods);
	// LM2c: a pool per mesh, MaxClods over the meshes to start with; a family's mesh that runs out grows its pool.
	const int32 PerMesh = (MaxClods + Found.Num() - 1) / Found.Num();
	FString Heights;
	for (int32 MeshIndex = 0; MeshIndex < Found.Num(); ++MeshIndex)
	{
		UHierarchicalInstancedStaticMeshComponent* Hism = NewObject<UHierarchicalInstancedStaticMeshComponent>(this, *FString::Printf(TEXT("Clods_%d"), FoundVariant[MeshIndex]), RF_Transient);
		Hism->SetStaticMesh(Found[MeshIndex]);
		Hism->SetMobility(EComponentMobility::Movable);
		Hism->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Hism->SetCanEverAffectNavigation(false);
		Hism->SetCastShadow(true);
		Hism->SetCullDistances(FMath::RoundToInt(ClodCullStartCm), FMath::RoundToInt(FMath::Max(ClodCullStartCm, ClodCullEndCm)));
		Hism->SetNumCustomDataFloats(1);   // LM2c: M_GT_Clod's freshness
		if (ClodMaterial)
		{
			Hism->SetMaterial(0, ClodMaterial);
		}
		Hism->SetupAttachment(RootComponent);
		Hism->RegisterComponent();
		TArray<FTransform>& Transforms = ClodTransforms.AddDefaulted_GetRef();
		Transforms.Init(DeadClodTransform(), PerMesh);
		Hism->AddInstances(Transforms, false, true);
		ClodMeshes.Add(Hism);
		TArray<int32>& Free = ClodFree.AddDefaulted_GetRef();
		Free.Reserve(PerMesh);
		for (int32 Instance = PerMesh - 1; Instance >= 0; --Instance)
		{
			Free.Add(Instance);
		}
		ClodDirtyList.AddDefaulted();
		ClodDirtyFlag.AddDefaulted_GetRef().Init(0, PerMesh);
		const FBox Box = Found[MeshIndex]->GetBoundingBox();
		// LM4: a shard's own across (6-25 cm at scale 1) from its bounds; the clods are 10 across by construction.
		const float Across = (bShards && Box.IsValid) ? static_cast<float>(FMath::Max(Box.Max.X - Box.Min.X, Box.Max.Y - Box.Min.Y)) : ClodMeshCm;
		ClodMeshAcrossCm.Add(FMath::Max(1.f, Across));
		const float Height = Box.IsValid ? static_cast<float>(Box.Max.Z - FMath::Min(0.0, Box.Min.Z)) : ClodHeightRatio * ClodMeshCm;
		ClodMeshHeightCm.Add(FMath::Clamp(Height, 0.5f, 2.f * ClodMeshAcrossCm.Last()));
		ClodMeshFamily.Add(bShards ? 0 : ClodFamilyOf(FoundVariant[MeshIndex]));
		Heights += FString::Printf(TEXT("%s%d:%.1f"), Heights.IsEmpty() ? TEXT("") : TEXT(" "), FoundVariant[MeshIndex], ClodMeshHeightCm.Last());
		if (bShards)
		{
			Heights += FString::Printf(TEXT("/%.1f across"), ClodMeshAcrossCm.Last());
		}
	}
	bClodsVisible = true;
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: %d clod mesh(es), %d instances each to start, heights (cm at 10 across) %s, material %s (LM2c)"), SectionIndex, Found.Num(), PerMesh,
		*Heights, ClodMaterial ? *ClodMaterial->GetName() : TEXT("the meshes' own"));
}

FTransform AGTMudPatch::ClodTransform(const FClod& Clod) const
{
	const float Z = MeshRestZAt(Clod.XYCm) + Clod.SurfaceCm - Clod.SunkCm;
	const float Across = ClodMeshAcrossCm.IsValidIndex(Clod.MeshIndex) ? ClodMeshAcrossCm[Clod.MeshIndex] : ClodMeshCm;   // LM4: a shard's own
	return FTransform(Clod.Rotation, FVector(Clod.XYCm.X, Clod.XYCm.Y, Z), Clod.Scale * (Clod.SizeCm / Across));
}

int32 AGTMudPatch::TakeClodInstance(int32 MeshIndex)
{
	if (!ClodMeshes.IsValidIndex(MeshIndex) || !ClodMeshes[MeshIndex])
	{
		return INDEX_NONE;
	}
	TArray<int32>& Free = ClodFree[MeshIndex];
	if (Free.Num() == 0)
	{
		// The family's mesh ran out: half as many again (at least 32), dead, in one AddInstances.
		TArray<FTransform>& Transforms = ClodTransforms[MeshIndex];
		const int32 Old = Transforms.Num();
		const int32 Grow = FMath::Max(32, Old / 2);
		TArray<FTransform> Added;
		Added.Init(DeadClodTransform(), Grow);
		ClodMeshes[MeshIndex]->AddInstances(Added, false, true);
		Transforms.Append(Added);
		ClodDirtyFlag[MeshIndex].AddZeroed(Grow);
		for (int32 Instance = Old + Grow - 1; Instance >= Old; --Instance)
		{
			Free.Add(Instance);
		}
	}
	return Free.Pop(EAllowShrinking::No);
}

int32 AGTMudPatch::PickClodMesh(uint8 Source, FRandomStream& Random) const
{
	const int32 Meshes = ClodMeshes.Num();
	if (Meshes <= 1)
	{
		return 0;
	}
	if (bShards)
	{
		return Random.RandHelper(Meshes);   // LM4: the shards are one family, any of the eight
	}
	if (Source <= 1 || Source == 6)   // MRD1: a churn zone's field takes the throw's families
	{
		// The family by its odds, then one of its meshes; a family with no mesh falls back to any.
		const float* Odds = Source == 0 ? ClodBankFamilies : ClodThrowFamilies;
		const float Roll = Random.FRand();
		int32 Family = 3;
		float Sum = 0.f;
		for (int32 F = 0; F < 4; ++F)
		{
			Sum += Odds[F];
			if (Roll < Sum)
			{
				Family = F;
				break;
			}
		}
		TArray<int32, TInlineAllocator<4>> InFamily;
		for (int32 MeshIndex = 0; MeshIndex < Meshes; ++MeshIndex)
		{
			if (ClodMeshFamily[MeshIndex] == Family)
			{
				InFamily.Add(MeshIndex);
			}
		}
		if (InFamily.Num() > 0)
		{
			return InFamily[Random.RandHelper(InFamily.Num())];
		}
	}
	return Random.RandHelper(Meshes);
}

void AGTMudPatch::SetClodInstance(int32 Slot, const FTransform& Transform)
{
	if (!Clods.IsValidIndex(Slot))
	{
		return;
	}
	FClod& Clod = Clods[Slot];
	const int32 MeshIndex = Clod.MeshIndex;
	const int32 Instance = Clod.Instance;
	if (!ClodTransforms.IsValidIndex(MeshIndex) || !ClodTransforms[MeshIndex].IsValidIndex(Instance))
	{
		return;
	}
	ClodTransforms[MeshIndex][Instance] = Transform;
	Clod.PushedZ = static_cast<float>(Transform.GetLocation().Z);
	if (!ClodDirtyFlag[MeshIndex][Instance])
	{
		ClodDirtyFlag[MeshIndex][Instance] = 1;
		ClodDirtyList[MeshIndex].Add(Instance);
	}
}

void AGTMudPatch::RemoveClod(int32 Slot)
{
	FClod& Clod = Clods[Slot];
	if (!Clod.bAlive)
	{
		return;
	}
	Clod.bAlive = false;
	if (TileClods.IsValidIndex(Clod.Tile))
	{
		TileClods[Clod.Tile].RemoveSingleSwap(Slot);
	}
	ClodsLive = FMath::Max(0, ClodsLive - 1);
	SetClodInstance(Slot, DeadClodTransform());
	// LM2c: its instance back to its mesh's pool (the dead transform is pushed with the batch unless a new clod takes it first).
	if (ClodFree.IsValidIndex(Clod.MeshIndex) && Clod.Instance != INDEX_NONE)
	{
		ClodFree[Clod.MeshIndex].Add(Clod.Instance);
	}
	Clod.MeshIndex = INDEX_NONE;
	Clod.Instance = INDEX_NONE;
}

void AGTMudPatch::SpawnClod(const FGTMudField::FClodSpawn& Spawn)
{
	if (ClodMeshes.Num() == 0 || Clods.Num() == 0 || !Field.Contains(Spawn.XYCm))
	{
		return;
	}
	// The ring: the next slot, the oldest clod in it replaced.
	const int32 Slot = ClodNext;
	ClodNext = (ClodNext + 1) % Clods.Num();
	if (Clods[Slot].bAlive)
	{
		++ClodsRecycled;
		RemoveClod(Slot);
	}
	FRandomStream Random(Spawn.Seed);
	// LM2c: the mesh by the source's family odds, an instance from its pool.
	const int32 MeshIndex = PickClodMesh(Spawn.Source, Random);
	const int32 Instance = TakeClodInstance(MeshIndex);
	if (Instance == INDEX_NONE)
	{
		return;
	}
	FClod& Clod = Clods[Slot];
	Clod.MeshIndex = MeshIndex;
	Clod.Instance = Instance;
	Clod.XYCm = Spawn.XYCm;
	Clod.SizeCm = FMath::Max(1.f, Spawn.SizeCm);
	// LM2c placement: a non-uniform scale, a random yaw, tilted off the local surface normal (the field's and the ground's)
	// by up to ClodTiltDeg about a random horizontal axis, and sunk ClodSinkIn..ClodSinkInMax of its own height.
	const FVector2D Gradient = Field.GradientAt(Spawn.XYCm);
	const double StepCm = Field.CellCm;
	const double RestX = (MeshRestZAt(Spawn.XYCm + FVector2D(StepCm, 0.0)) - MeshRestZAt(Spawn.XYCm - FVector2D(StepCm, 0.0))) / (2.0 * StepCm);
	const double RestY = (MeshRestZAt(Spawn.XYCm + FVector2D(0.0, StepCm)) - MeshRestZAt(Spawn.XYCm - FVector2D(0.0, StepCm))) / (2.0 * StepCm);
	const FVector Normal = FVector(-(Gradient.X + RestX), -(Gradient.Y + RestY), 1.0).GetSafeNormal();
	const float Across = ClodMeshAcrossCm.IsValidIndex(MeshIndex) ? ClodMeshAcrossCm[MeshIndex] : ClodMeshCm;
	float SinkMin = FMath::Clamp(ClodSinkIn, 0.f, 1.f);
	float SinkMax = FMath::Clamp(ClodSinkInMax, SinkMin, 1.f);
	if (bShards)
	{
		// LM4 item 4, a shard's placement: its own proportions kept (the spawn's size over the mesh's across, +-ShardScaleJitter
		// each way), the yaw along the lip (the stroke's heading) +-ShardYawSpreadDeg (any yaw for a throw's), tilted
		// ShardTiltMinDeg..ShardTiltMaxDeg off the local surface normal about a random horizontal axis, sunk ShardSinkMin..Max.
		const float J = FMath::Clamp(ShardScaleJitter, 0.f, 0.9f);
		Clod.Scale = FVector(Random.FRandRange(1.f - J, 1.f + J), Random.FRandRange(1.f - J, 1.f + J), Random.FRandRange(1.f - J, 1.f + J));
		const float TiltMin = FMath::DegreesToRadians(FMath::Clamp(ShardTiltMinDeg, 0.f, 89.f));
		const float TiltMax = FMath::DegreesToRadians(FMath::Clamp(ShardTiltMaxDeg, FMath::Clamp(ShardTiltMinDeg, 0.f, 89.f), 89.f));
		const float AxisAngle = Random.FRandRange(0.f, 2.f * PI);
		const FQuat TiltQuat(FVector(FMath::Cos(AxisAngle), FMath::Sin(AxisAngle), 0.f), Random.FRandRange(TiltMin, TiltMax));
		const float YawRad = Spawn.bHeading
			? FMath::DegreesToRadians(Spawn.HeadingDeg + Random.FRandRange(-ShardYawSpreadDeg, ShardYawSpreadDeg))
			: Random.FRandRange(0.f, 2.f * PI);
		const FQuat YawQuat(FVector::UpVector, YawRad);
		Clod.Rotation = FQuat::FindBetweenNormals(FVector::UpVector, Normal.IsNearlyZero() ? FVector::UpVector : Normal) * TiltQuat * YawQuat;
		SinkMin = FMath::Clamp(ShardSinkMin, 0.f, 1.f);
		SinkMax = FMath::Clamp(ShardSinkMax, SinkMin, 1.f);
	}
	else
	{
		Clod.Scale = FVector(Random.FRandRange(ClodScaleXYMin, ClodScaleXYMax), Random.FRandRange(ClodScaleXYMin, ClodScaleXYMax), Random.FRandRange(ClodScaleZMin, ClodScaleZMax));
		const float Tilt = FMath::DegreesToRadians(FMath::Clamp(ClodTiltDeg, 0.f, 89.f));
		const float AxisAngle = Random.FRandRange(0.f, 2.f * PI);
		const FQuat TiltQuat(FVector(FMath::Cos(AxisAngle), FMath::Sin(AxisAngle), 0.f), Random.FRandRange(-Tilt, Tilt));
		const FQuat YawQuat(FVector::UpVector, Random.FRandRange(0.f, 2.f * PI));
		Clod.Rotation = FQuat::FindBetweenNormals(FVector::UpVector, Normal.IsNearlyZero() ? FVector::UpVector : Normal) * TiltQuat * YawQuat;
	}
	Clod.HeightCm = ClodMeshHeightCm.IsValidIndex(MeshIndex) ? ClodMeshHeightCm[MeshIndex] * (Clod.SizeCm / Across) * static_cast<float>(Clod.Scale.Z) : ClodHeightRatio * Clod.SizeCm;
	Clod.SunkCm = FMath::Lerp(SinkMin, SinkMax, Random.FRand()) * Clod.HeightCm;
	Clod.SurfaceCm = Field.HeightAt(Spawn.XYCm);
	const FVector2D Local = (Spawn.XYCm - Field.OriginCm) / (Field.CellCm * FMath::Max(1, Field.SettleTileCells));
	Clod.Tile = FMath::Clamp(FMath::FloorToInt(Local.Y), 0, ClodTilesY - 1) * ClodTilesX + FMath::Clamp(FMath::FloorToInt(Local.X), 0, ClodTilesX - 1);
	Clod.Source = Spawn.Source;
	Clod.bAlive = true;
	TileClods[Clod.Tile].Add(Slot);
	++ClodsLive;
	ClodsFromBank += Spawn.Source == 0 ? 1 : 0;
	ClodsFromThrow += Spawn.Source == 1 ? 1 : 0;
	ClodsFromTest += Spawn.Source == 2 ? 1 : 0;
	ClodsFromFloor += Spawn.Source == 3 ? 1 : 0;   // LM4: a lip plate fallen onto the trench floor
	ClodsFromChannel += Spawn.Source == 4 ? 1 : 0;   // LM4d: spilled from the belly's berm into its channel
	ClodsFromChunk += Spawn.Source == 5 ? 1 : 0;     // MR5: a chunk's break
	SetClodInstance(Slot, ClodTransform(Clod));
	// LM2c: the freshness M_GT_Clod reads (PerInstanceCustomData 0), static: a throw's 1 (darker, glossier), a bank clod's 0.3.
	if (UHierarchicalInstancedStaticMeshComponent* Hism = ClodMeshes[MeshIndex])
	{
		// MR5: a broken chunk's clods are its dry crust (freshness 0, as the chunk's own material).
		// MRD1: a churn zone's field is old and dry too (Source 6).
		Hism->SetCustomDataValue(Instance, 0, Spawn.Source == 1 ? ClodFreshThrow : ((Spawn.Source == 5 || Spawn.Source == 6) ? 0.f : ClodFreshBank), false);
	}
}

void AGTMudPatch::UpdateClods(float DeltaSeconds, bool bClodsOn)
{
	if (ClodMeshes.Num() == 0)
	{
		ClodsDropped += Field.PendingClods.Num();
		Field.PendingClods.Reset();
		return;
	}
	if (bClodsOn != bClodsVisible)
	{
		for (UHierarchicalInstancedStaticMeshComponent* Hism : ClodMeshes)
		{
			if (Hism)
			{
				Hism->SetVisibility(bClodsOn);
			}
		}
		bClodsVisible = bClodsOn;
	}
	if (!bClodsOn)
	{
		ClodsDropped += Field.PendingClods.Num();
		Field.PendingClods.Reset();
		return;
	}
	// Everything below runs in batches at ClodBatchHz: the spawns queued since the last batch, the re-snap and the
	// squash in the tiles whose cells changed, the wet sinking, then one push per mesh and one render-state dirty.
	ClodBatchAccumS += DeltaSeconds;
	const float Period = 1.f / FMath::Max(0.1f, ClodBatchHz);
	if (ClodBatchAccumS < Period)
	{
		return;
	}
	const float BatchS = FMath::Min(ClodBatchAccumS, 1.f);
	ClodBatchAccumS = 0.f;
	for (const FGTMudField::FClodSpawn& Spawn : Field.PendingClods)
	{
		SpawnClod(Spawn);
	}
	Field.PendingClods.Reset();
	if (bClodDirtyCells)
	{
		bClodDirtyCells = false;
		const int32 TileCells = FMath::Max(1, Field.SettleTileCells);
		const int32 TX0 = FMath::Clamp(ClodDirtyCells.Min.X / TileCells, 0, ClodTilesX - 1);
		const int32 TY0 = FMath::Clamp(ClodDirtyCells.Min.Y / TileCells, 0, ClodTilesY - 1);
		const int32 TX1 = FMath::Clamp((ClodDirtyCells.Max.X - 1) / TileCells, 0, ClodTilesX - 1);
		const int32 TY1 = FMath::Clamp((ClodDirtyCells.Max.Y - 1) / TileCells, 0, ClodTilesY - 1);
		TArray<int32> Slots;
		for (int32 TY = TY0; TY <= TY1; ++TY)
		{
			for (int32 TX = TX0; TX <= TX1; ++TX)
			{
				Slots = TileClods[TY * ClodTilesX + TX];   // a copy: a squash takes the slot out of the tile's list
				for (const int32 Slot : Slots)
				{
					FClod& Clod = Clods[Slot];
					const float Now = Field.HeightAt(Clod.XYCm);
					// Squashed: a new capsule went over it (the tracks set there and the surface down by over ClodSquashCm
					// since the last snap). Its volume is in the field already, so it just goes.
					if (Clod.SurfaceCm - Now > ClodSquashCm && Field.TracksAt(Clod.XYCm) >= 0.5f)
					{
						++ClodsSquashed;
						RemoveClod(Slot);
						continue;
					}
					if (!FMath::IsNearlyEqual(Now, Clod.SurfaceCm, 0.05f))
					{
						Clod.SurfaceCm = Now;
						SetClodInstance(Slot, ClodTransform(Clod));
					}
				}
			}
		}
	}
	// Wet sinking: on Bog cells, or anywhere at wetness over 0.5, ClodSinkCmPerS x wetness; gone at 90 % of its height under.
	const UGTWeatherSubsystem* Weather = GetWorld() ? GetWorld()->GetSubsystem<UGTWeatherSubsystem>() : nullptr;
	const float Wet = Weather ? FMath::Clamp(Weather->GetWetness(), 0.f, 1.f) : 0.f;
	if (Wet > 0.f && ClodSinkCmPerS > 0.f)
	{
		for (int32 Slot = 0; Slot < Clods.Num(); ++Slot)
		{
			FClod& Clod = Clods[Slot];
			if (!Clod.bAlive || Clod.Source == 6)   // MRD1: a churn zone's old clods stay on the road
			{
				continue;
			}
			const int32 Index = Field.CellIndexAt(Clod.XYCm);
			const bool bBog = BogMask.IsValidIndex(Index) && BogMask[Index] >= 128;
			if (!bBog && Wet <= 0.5f)
			{
				continue;
			}
			Clod.SunkCm += ClodSinkCmPerS * Wet * BatchS;
			if (Clod.SunkCm >= 0.9f * Clod.HeightCm)
			{
				++ClodsSunk;
				RemoveClod(Slot);
				continue;
			}
			// LM2c: re-pushed only once it has gone ClodRepushCm down since its last push (LM2b pushed every sinking clod every batch).
			const float Z = MeshRestZAt(Clod.XYCm) + Clod.SurfaceCm - Clod.SunkCm;
			if (FMath::Abs(Z - Clod.PushedZ) > ClodRepushCm)
			{
				SetClodInstance(Slot, ClodTransform(Clod));
			}
		}
	}
	// LM2c: one push per dirty instance (a contiguous range re-pushed every clean instance between the dirty ones), then
	// one render-state dirty per batch on the last mesh pushed, as LM2b.
	int32 LastDirty = INDEX_NONE;
	for (int32 MeshIndex = 0; MeshIndex < ClodDirtyList.Num(); ++MeshIndex)
	{
		if (ClodDirtyList[MeshIndex].Num() > 0 && ClodMeshes[MeshIndex])
		{
			LastDirty = MeshIndex;
		}
	}
	for (int32 MeshIndex = 0; MeshIndex <= LastDirty; ++MeshIndex)
	{
		TArray<int32>& List = ClodDirtyList[MeshIndex];
		UHierarchicalInstancedStaticMeshComponent* Hism = ClodMeshes[MeshIndex];
		if (List.Num() == 0 || !Hism)
		{
			continue;
		}
		List.Sort();
		for (int32 K = 0; K < List.Num(); ++K)
		{
			const int32 Instance = List[K];
			Hism->UpdateInstanceTransform(Instance, ClodTransforms[MeshIndex][Instance], true, MeshIndex == LastDirty && K == List.Num() - 1, true);
			ClodDirtyFlag[MeshIndex][Instance] = 0;
		}
		List.Reset();
	}
}

TArray<FVector4> AGTMudPatch::CutTrenchForTest(const FVector2D& FromCm, const FVector2D& ToCm, float TyreWidthCm, float SinkCm)
{
	TArray<FVector4> Out;
	if (!Field.IsValid() || !IsSnow())
	{
		return Out;
	}
	// LM4c: one tyre's cut in 5 cm strokes (the traction's stride at about 3 m/s and 60 Hz), all now: the collapse segments it
	// arms fall CollapseDelayMinS..MaxS of settle time from now (gt.Mud.Settle on), behind no car.
	const FVector2D Line = ToCm - FromCm;
	const double Length = Line.Size();
	if (Length < 5.0)
	{
		return Out;
	}
	const FVector2D Dir = Line / Length;
	const int32 Before = Field.CollapseSegs.Num();
	TSet<uint64> Seen;
	for (const FGTMudField::FCollapseSeg& Seg : Field.CollapseSegs)
	{
		if (Seg.bPending)
		{
			Seen.Add(Seg.Key);   // pending before this cut: not this cut's
		}
	}
	const int32 Strokes = FMath::FloorToInt(static_cast<float>(Length / 5.0));
	for (int32 Stroke = 0; Stroke < Strokes; ++Stroke)
	{
		Field.StampWheel(FromCm + Dir * (5.0 * Stroke), FromCm + Dir * (5.0 * (Stroke + 1)), TyreWidthCm, SinkCm, Dir, 5.f * (Stroke + 1));
	}
	for (int32 Index = 0; Index < Field.CollapseSegs.Num(); ++Index)
	{
		const FGTMudField::FCollapseSeg& Seg = Field.CollapseSegs[Index];
		if (!Seg.bPending || (Index < Before && Seen.Contains(Seg.Key)))
		{
			continue;
		}
		// The pile's spot: mid-segment on the line, a cell in from the wall's foot (FGTMudField::Collapse's cone centre).
		FVector2D N(-Dir.Y, Dir.X);
		if ((Seg.bAlongX ? N.Y : N.X) * Seg.Side < 0.0)
		{
			N = -N;
		}
		const double Mid = 0.5 * (Seg.Along0 + Seg.Along1);
		const double DirAxis = Seg.bAlongX ? Dir.X : Dir.Y;
		const double T = FMath::Abs(DirAxis) > 1.e-3 ? (Mid - (Seg.bAlongX ? Seg.LinePoint.X : Seg.LinePoint.Y)) / DirAxis : 0.0;
		const FVector2D Pile = Seg.LinePoint + Dir * T + N * (Seg.FaceCm - Field.CellCm);
		Out.Add(FVector4(Pile.X, Pile.Y, Seg.Side, Seg.DelayS));
	}
	return Out;
}

int32 AGTMudPatch::FillClodsForTest(int32 Count)
{
	if (ClodMeshes.Num() == 0 || Count <= 0)
	{
		return 0;
	}
	const FBox2D Box = Field.Bounds();
	FRandomStream Random(0xF111 + SectionIndex);
	int32 Added = 0;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		FGTMudField::FClodSpawn Spawn;
		Spawn.XYCm = FVector2D(Random.FRandRange(Box.Min.X + 50.0, Box.Max.X - 50.0), Random.FRandRange(Box.Min.Y + 50.0, Box.Max.Y - 50.0));
		Spawn.SizeCm = Random.FRandRange(ClodBankMinSizeCm, ClodBankMaxSizeCm);
		Spawn.Seed = Random.RandHelper(MAX_int32);
		Spawn.Source = 2;
		SpawnClod(Spawn);
		++Added;
	}
	ClodBatchAccumS = 1.f;   // pushed on the next tick
	return Added;
}

// ---- MudRunner MR5, breakable mud chunks (docs/MUDRUNNER_LESSONS_PLAN.md MR5 execution block) ---------------------------

namespace
{
	/** MR5: a repeatable 0..1 from a seed and an index (the sizes' strata). */
	float ChunkHash01(uint32 Seed, uint32 K)
	{
		uint32 H = (Seed * 0x9E3779B1u) ^ ((K + 0x7F4A7C15u) * 0x85EBCA77u);
		H ^= H >> 15;
		H *= 0x2C1B3C6Du;
		H ^= H >> 12;
		H *= 0x297A2D39u;
		H ^= H >> 15;
		return static_cast<float>(H & 0xFFFFFFu) / static_cast<float>(0x1000000);
	}

	/** MR5: the distance from P to the segment A-B. */
	double SegmentDistance(const FVector2D& P, const FVector2D& A, const FVector2D& B)
	{
		const FVector2D AB = B - A;
		const double Len2 = AB.SizeSquared();
		const double T = Len2 > 0.0 ? FMath::Clamp(FVector2D::DotProduct(P - A, AB) / Len2, 0.0, 1.0) : 0.0;
		return FVector2D::Distance(P, A + AB * T);
	}

	/** MR5: a chunk's collision - its own object type, blocking the ground, the world's movers, the car's body, pawns and the other chunks; nothing else (no trace channel, no camera, no loose body panel). */
	void SetMudChunkCollision(UStaticMeshComponent& Component)
	{
		Component.SetCollisionObjectType(AGTMudPatch::MudChunkChannel);
		Component.SetCollisionResponseToAllChannels(ECR_Ignore);
		for (const ECollisionChannel Channel : { ECC_WorldStatic, ECC_WorldDynamic, ECC_Vehicle, ECC_Pawn, AGTMudPatch::MudChunkChannel })
		{
			Component.SetCollisionResponseToChannel(Channel, ECR_Block);
		}
	}

	/** MR5: the families' meshes by number (0-1 rounded, 2-3 slab, 4 broken, 5 smear). */
	constexpr int32 MudChunkFamilyFirst[4] = { 0, 2, 4, 5 };
	constexpr int32 MudChunkFamilyCount[4] = { 2, 2, 1, 1 };
}

void AGTMudPatch::SetRouteLine(const FGTTerrainSpec& Spec, const FGTRouteSection& Section)
{
	RouteLineCm.Reset();
	RoadHalfWidthCm = Spec.RoadHalfWidthM * 100.f;   // Deformable gravel DG1: the stones' road
	if (Section.EndM <= Section.StartM || Spec.RouteM.Num() < 2)
	{
		return;
	}
	// SectionBoxCm's points (GTTerrainGenerator.cpp): the main route every 2 m from the section's start to its end.
	const int32 Steps = FMath::Max(1, FMath::CeilToInt((Section.EndM - Section.StartM) / 2.f));
	for (int32 Step = 0; Step <= Steps; ++Step)
	{
		float Yaw = 0.f;
		const float ArcM = FMath::Lerp(Section.StartM, Section.EndM, static_cast<float>(Step) / Steps);
		RouteLineCm.Add(GTTerrain::PointOnPolyline(Spec.RouteM, ArcM, Yaw) * 100.0);
	}
}

float AGTMudPatch::DistanceToRouteCm(const FVector2D& XYCm) const
{
	if (RouteLineCm.Num() == 1)
	{
		return static_cast<float>(FVector2D::Distance(XYCm, RouteLineCm[0]));
	}
	double Best = 1.0e9;
	for (int32 K = 0; K + 1 < RouteLineCm.Num(); ++K)
	{
		Best = FMath::Min(Best, SegmentDistance(XYCm, RouteLineCm[K], RouteLineCm[K + 1]));
	}
	return static_cast<float>(Best);
}

int32 AGTMudPatch::PlanMudChunks(TArray<FMudChunkPlan>& Out, bool bUntouchedOnly, float* OutCandidateM2, int32* OutTarget, bool bIgnorePreChurn) const
{
	Out.Reset();
	if (OutCandidateM2)
	{
		*OutCandidateM2 = 0.f;
	}
	if (OutTarget)
	{
		*OutTarget = 0;
	}
	if (!HasSoftSpots() || RouteLineCm.Num() < 2)
	{
		return 0;
	}
	const int32 SX = Field.SizeX;
	const int32 SY = Field.SizeY;
	const float Cell = Field.CellCm;
	const uint32 Seed = static_cast<uint32>(MudChunkSeed(SectionIndex));
	// The candidate cells: S at most MudChunkMaxSoftness (the firm crust), MudChunkRimCm from the rim, within MudChunkRouteCm of
	// the route line (back at gt.Mud.Chunks 1: the field still 0 there too). The route test takes the segments' boxes first.
	TArray<FBox2D> SegmentBoxes;
	for (int32 K = 0; K + 1 < RouteLineCm.Num(); ++K)
	{
		FBox2D Box(ForceInit);
		Box += RouteLineCm[K];
		Box += RouteLineCm[K + 1];
		SegmentBoxes.Add(Box.ExpandBy(MudChunkRouteCm));
	}
	auto NearRoute = [this, &SegmentBoxes](const FVector2D& P)
	{
		for (int32 K = 0; K < SegmentBoxes.Num(); ++K)
		{
			if (SegmentBoxes[K].IsInside(P) && SegmentDistance(P, RouteLineCm[K], RouteLineCm[K + 1]) <= MudChunkRouteCm)
			{
				return true;
			}
		}
		return false;
	};
	const FVector2D BoxLo = Field.Bounds().Min;
	const FVector2D BoxHi = Field.Bounds().Max;
	auto RimDistance = [&BoxLo, &BoxHi](const FVector2D& P)
	{
		return FMath::Min(FMath::Min(P.X - BoxLo.X, BoxHi.X - P.X), FMath::Min(P.Y - BoxLo.Y, BoxHi.Y - P.Y));
	};
	TArray<int32> Candidates;
	TArray<float> Noise;
	const double ClusterM = FMath::Max(0.1f, MudChunkClusterCm) * 0.01;
	for (int32 Y = 0; Y < SY; ++Y)
	{
		for (int32 X = 0; X < SX; ++X)
		{
			const int32 Index = Y * SX + X;
			const FVector2D Centre = Field.CellCentreCm(Index);
			if (RimDistance(Centre) < MudChunkRimCm || Softness[Index] > MudChunkMaxSoftness)
			{
				continue;
			}
			// GR1: on a pre-churned patch "untouched" is against the surface the pre-churn left, and a chunk sits only where that
			// surface is within PreChurnChunkBandCm of the hummocked ground before the tracks (the hummock tops and the flats between
			// the old ruts, never a rut or its bank).
			const bool bPreChurned = !bIgnorePreChurn && IsPreChurned();
			if (bUntouchedOnly && (bPreChurned ? FMath::Abs(Field.SurfaceCm(Index) - PreChurnSurfaceCm[Index]) > 0.5f
				: (FMath::Abs(Field.HeightCm[Index]) > 0.5f || FMath::Abs(Field.LumpCm[Index]) > 0.5f)))
			{
				continue;
			}
			if (bPreChurned && FMath::Abs(PreChurnSurfaceCm[Index] - PreChurnBaseCm[Index]) > PreChurnChunkBandCm)
			{
				continue;
			}
			if (!NearRoute(Centre))
			{
				continue;
			}
			Candidates.Add(Index);
			Noise.Add(SoftNoise(Centre.X * 0.01, Centre.Y * 0.01, ClusterM, 0.61, Seed ^ 0x5bd1e995u));
		}
	}
	const float AreaM2 = Candidates.Num() * Cell * Cell * 1.e-4f;
	const int32 Target = FMath::Clamp(FMath::RoundToInt(AreaM2 * MudChunkDensityPerM2 * MudChunkDensityScale), 0, FMath::Max(0, MaxMudChunks));
	if (OutCandidateM2)
	{
		*OutCandidateM2 = AreaM2;
	}
	if (OutTarget)
	{
		*OutTarget = Target;
	}
	if (Target <= 0 || Candidates.Num() == 0)
	{
		return 0;
	}
	// Clustering: the noise's top MudChunkClusterShare of the candidate area is cluster ground (x MudChunkClusterDensity), the rest
	// x MudChunkSparseDensity. Drawing exactly the target by these weights renormalises them: the mean density is the target's.
	TArray<float> Sorted = Noise;
	Sorted.Sort();
	const float Threshold = SoftQuantile(Sorted, 1.0 - FMath::Clamp(MudChunkClusterShare, 0.f, 1.f));
	TArray<double> Cumulative;
	Cumulative.SetNumUninitialized(Candidates.Num());
	double Total = 0.0;
	for (int32 K = 0; K < Candidates.Num(); ++K)
	{
		Total += Noise[K] > Threshold ? FMath::Max(0.f, MudChunkClusterDensity) : FMath::Max(0.f, MudChunkSparseDensity);
		Cumulative[K] = Total;
	}
	if (Total <= 0.0)
	{
		return 0;
	}
	// Sizes: min + (max - min) u^power (most are small), u stratified - one in each 1/Target of 0..1, jittered by a hash - so even
	// a few chunks span the range; placed largest first, so the spacing finds room for the big ones.
	TArray<float> Sizes;
	for (int32 K = 0; K < Target; ++K)
	{
		const float U = (K + ChunkHash01(Seed, static_cast<uint32>(K))) / Target;
		Sizes.Add(MudChunkSizeMinCm + (MudChunkSizeMaxCm - MudChunkSizeMinCm) * FMath::Pow(U, FMath::Max(0.1f, MudChunkSizePower)));
	}
	Sizes.Sort(TGreater<float>());
	const float Weights[4] = { FMath::Max(0.f, static_cast<float>(MudChunkFamilyWeights.X)), FMath::Max(0.f, static_cast<float>(MudChunkFamilyWeights.Y)),
		FMath::Max(0.f, static_cast<float>(MudChunkFamilyWeights.Z)), FMath::Max(0.f, static_cast<float>(MudChunkFamilyWeights.W)) };
	const float WeightSum = FMath::Max(1.e-6f, Weights[0] + Weights[1] + Weights[2] + Weights[3]);
	FRandomStream Random(static_cast<int32>(Seed));
	for (const float Size : Sizes)
	{
		for (int32 Attempt = 0; Attempt < 60; ++Attempt)
		{
			// A candidate cell by the cluster weights (a binary search of the running sum), a point inside it.
			const double Roll = Random.FRand() * Total;
			int32 Lo = 0;
			int32 Hi = Cumulative.Num() - 1;
			while (Lo < Hi)
			{
				const int32 Mid = (Lo + Hi) / 2;
				if (Cumulative[Mid] < Roll)
				{
					Lo = Mid + 1;
				}
				else
				{
					Hi = Mid;
				}
			}
			const int32 CellIndex = Candidates[Lo];
			const FVector2D Corner = Field.OriginCm + FVector2D(static_cast<double>(CellIndex % SX), static_cast<double>(CellIndex / SX)) * Cell;
			const FVector2D XY = Corner + FVector2D(Random.FRandRange(0.02f, 0.98f), Random.FRandRange(0.02f, 0.98f)) * Cell;
			// The centre itself within the rim and the route's reach (a cell's corner may not be), and the edge gap to every other.
			if (RimDistance(XY) < MudChunkRimCm || DistanceToRouteCm(XY) > MudChunkRouteCm)
			{
				continue;
			}
			bool bFree = true;
			for (const FMudChunkPlan& Other : Out)
			{
				if (FVector2D::Distance(XY, Other.XYCm) < 0.5f * (Size + Other.SizeCm) + MudChunkGapCm)
				{
					bFree = false;
					break;
				}
			}
			if (!bFree)
			{
				continue;
			}
			FMudChunkPlan Plan;
			Plan.XYCm = XY;
			Plan.SizeCm = Size;
			Plan.YawDeg = Random.FRandRange(0.f, 360.f);
			Plan.TiltDeg = Random.FRandRange(-MudChunkTiltDeg, MudChunkTiltDeg);
			Plan.TiltAxisDeg = Random.FRandRange(0.f, 360.f);
			const float FamilyRoll = Random.FRand() * WeightSum;
			int32 Family = 3;
			float Sum = 0.f;
			for (int32 F = 0; F < 4; ++F)
			{
				Sum += Weights[F];
				if (FamilyRoll < Sum)
				{
					Family = F;
					break;
				}
			}
			Plan.Mesh = MudChunkFamilyFirst[Family] + Random.RandHelper(MudChunkFamilyCount[Family]);
			Plan.Cell = CellIndex;
			Plan.bCluster = Noise[Lo] > Threshold;
			Out.Add(Plan);
			break;
		}
	}
	return Out.Num();
}

void AGTMudPatch::InitMudChunks()
{
	for (UStaticMeshComponent* Old : MudChunkComponents)
	{
		if (Old)
		{
			Old->DestroyComponent();
		}
	}
	MudChunkComponents.Reset();
	MudChunks.Reset();
	MudChunkMeshes.Reset();
	MudChunkMeshVolume.Reset();
	MudChunkMeshAcross.Reset();
	MudChunkHullVerts.Reset();
	MudChunkGrid.Reset();
	MudChunkGridX = 0;
	MudChunkGridY = 0;
	MudChunkMaterial = nullptr;
	MudChunkMaterialInstance = nullptr;
	MudChunkMeshCount = 0;
	MudChunksLive = 0;
	MudChunkLargestCm = 0.f;
	bMudChunksOn = CVarMudChunks.GetValueOnGameThread() != 0;
	MudChunkRandom.Initialize(MudChunkSeed(SectionIndex) ^ 0x2C1B3C6D);
	// The scope: MR4's (a Mud-medium bog without a profile, S built). Not a ford's or riverbed's bed, not snow, not gravel.
	if (!Field.IsValid() || !HasSoftSpots())
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: chunks (MR5) - none (%s)"), SectionIndex, bHasProfile ? TEXT("a profiled patch") : TEXT("not a bog's mud field"));
		return;
	}
	// The wheels' coarse grid over the box.
	const float GridCm = FMath::Max(25.f, MudChunkGridCm);
	const FVector2D BoxSize = Field.Bounds().GetSize();
	MudChunkGridX = FMath::Max(1, FMath::CeilToInt(BoxSize.X / GridCm));
	MudChunkGridY = FMath::Max(1, FMath::CeilToInt(BoxSize.Y / GridCm));
	MudChunkGrid.SetNum(MudChunkGridX * MudChunkGridY);
	// The meshes by path (a missing one skipped quietly), their volume and across from UGTMudChunkData, their hull's vertices.
	MudChunkMeshes.SetNum(MudChunkMeshVariants);
	MudChunkMeshVolume.Init(0.f, MudChunkMeshVariants);
	MudChunkMeshAcross.Init(0.f, MudChunkMeshVariants);
	MudChunkHullVerts.SetNum(MudChunkMeshVariants);
	const FString AssetBase = FPaths::GetCleanFilename(MudChunkMeshPrefix);
	FString Facts;
	for (int32 MeshNo = 0; MeshNo < MudChunkMeshVariants; ++MeshNo)
	{
		const FString Package = FString::Printf(TEXT("%s%d"), *MudChunkMeshPrefix, MeshNo);
		if (!FPackageName::DoesPackageExist(Package))
		{
			continue;
		}
		UStaticMesh* Found = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("%s.%s%d"), *Package, *AssetBase, MeshNo), nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!Found)
		{
			continue;
		}
		MudChunkMeshes[MeshNo] = Found;
		++MudChunkMeshCount;
		const UGTMudChunkData* Data = Found->GetAssetUserData<UGTMudChunkData>();
		const UBodySetup* Body = Found->GetBodySetup();
		if (Body)
		{
			for (const FKConvexElem& Elem : Body->AggGeom.ConvexElems)
			{
				MudChunkHullVerts[MeshNo].Append(Elem.VertexData);
			}
		}
		const FBox Box = Found->GetBoundingBox();
		MudChunkMeshAcross[MeshNo] = (Data && Data->AcrossCm > 0.f) ? Data->AcrossCm
			: (Box.IsValid ? static_cast<float>(FMath::Max(Box.Max.X - Box.Min.X, Box.Max.Y - Box.Min.Y)) : 30.f);
		if (Data && Data->VolumeCm3 > 0.f)
		{
			MudChunkMeshVolume[MeshNo] = Data->VolumeCm3;
		}
		else
		{
			MudChunkMeshVolume[MeshNo] = Body ? static_cast<float>(Body->AggGeom.GetScaledVolume(FVector::OneVector)) : 0.f;
			UE_LOG(LogTemp, Warning, TEXT("AGTMudPatch %d: %s has no UGTMudChunkData (run Art/import_mud_chunks.ps1); its hull's volume %.0f cm^3 stands in"), SectionIndex, *Found->GetName(), MudChunkMeshVolume[MeshNo]);
		}
		Facts += FString::Printf(TEXT("%s%d:%.0f cm3/%d hull verts"), Facts.IsEmpty() ? TEXT("") : TEXT(" "), MeshNo, MudChunkMeshVolume[MeshNo], MudChunkHullVerts[MeshNo].Num());
	}
	// M_GT_MudChunk (M_GT_Clod's path, Art/Unreal/live_mud_style.py): the variant slice through an instance, Standard the material itself.
	if (FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(MudChunkMaterialPath)))
	{
		MudChunkMaterial = LoadObject<UMaterialInterface>(nullptr, *MudChunkMaterialPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	}
	if (MudChunkMaterial && MudVariant != EGTMudVariant::Standard)
	{
		MudChunkMaterialInstance = UMaterialInstanceDynamic::Create(MudChunkMaterial, this);
		MudChunkMaterialInstance->SetScalarParameterValue(TEXT("MudVariant"), static_cast<float>(static_cast<uint8>(MudVariant)));
	}
	// The plan (its numbers whatever the meshes), then the chunks, each asleep on the ground.
	TArray<FMudChunkPlan> Plan;
	MudChunksPlanned = PlanMudChunks(Plan, false, &MudChunkCandidateM2, &MudChunkTarget);
	// GR1: on a pre-churned patch, the plan without the pre-churn's chunks: how many of their places the pre-churn left as they were
	// (within PreChurnChunkBandCm of the hummocked ground: kept) or put in an old rut or on its bank (moved, the plan drawing anew).
	PreChurnChunksKept = 0;
	PreChurnChunksMoved = 0;
	PreChurnChunksFlat = 0;
	if (IsPreChurned())
	{
		TArray<FMudChunkPlan> Flat;
		PlanMudChunks(Flat, false, nullptr, nullptr, true);
		PreChurnChunksFlat = Flat.Num();
		for (const FMudChunkPlan& Chunk : Flat)
		{
			const int32 Cell = Field.CellIndexAt(Chunk.XYCm);
			const bool bKept = Cell != INDEX_NONE && FMath::Abs(PreChurnSurfaceCm[Cell] - PreChurnBaseCm[Cell]) <= PreChurnChunkBandCm;
			(bKept ? PreChurnChunksKept : PreChurnChunksMoved) += 1;
		}
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: chunks (MR5) on the pre-churn (GR1) - %d planned (%d without it, of whose places %d kept and %d in an old rut or its bank)"),
			SectionIndex, Plan.Num(), Flat.Num(), PreChurnChunksKept, PreChurnChunksMoved);
	}
	// MRD1: a few chunks round a mud road's churn zones.
	PlanRoadChunks(Plan);
	const int32 Spawned = (bMudChunksOn && MudChunkMeshCount > 0) ? SpawnPlannedMudChunks(Plan) : 0;
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: chunks (MR5) - %d mesh(es) [%s], material %s; candidate %.1f m2 (route line +-%.0f cm, rim %.0f cm, S <= %.2f), %.3f a m2 x %.2f -> target %d, planned %d, spawned %d (no ground %d); gt.Mud.Chunks %d"),
		SectionIndex, MudChunkMeshCount, *Facts, MudChunkMaterialInstance ? *MudChunkMaterialInstance->GetName() : (MudChunkMaterial ? *MudChunkMaterial->GetName() : TEXT("the meshes' own")),
		MudChunkCandidateM2, MudChunkRouteCm, MudChunkRimCm, MudChunkMaxSoftness, MudChunkDensityPerM2, MudChunkDensityScale, MudChunkTarget, MudChunksPlanned, Spawned, MudChunksNoGround,
		bMudChunksOn ? 1 : 0);
}

int32 AGTMudPatch::SpawnPlannedMudChunks(const TArray<FMudChunkPlan>& Plan)
{
	int32 Spawned = 0;
	for (const FMudChunkPlan& Chunk : Plan)
	{
		if (!KeepsDecorAt(Chunk.XYCm))   // Benmore B2: a zone patch's chunks only on its own zone cells
		{
			continue;
		}
		Spawned += SpawnMudChunk(Chunk, true, nullptr) != INDEX_NONE ? 1 : 0;
	}
	MudChunksSpawned += Spawned;
	return Spawned;
}

int32 AGTMudPatch::SpawnMudChunk(const FMudChunkPlan& Plan, bool bAsleep, const FVector* At)
{
	// The plan's mesh, or the first found (a family without its mesh falls back).
	int32 MeshNo = Plan.Mesh;
	if (!MudChunkMeshes.IsValidIndex(MeshNo) || !MudChunkMeshes[MeshNo])
	{
		MeshNo = MudChunkMeshes.IndexOfByPredicate([](const TObjectPtr<UStaticMesh>& Candidate) { return Candidate != nullptr; });
		if (MeshNo == INDEX_NONE)
		{
			return INDEX_NONE;
		}
	}
	const float Scale = FMath::Max(0.01f, Plan.SizeCm / FMath::Max(1.f, MudChunkMeshAcross[MeshNo]));
	const FQuat Yaw(FVector::UpVector, FMath::DegreesToRadians(Plan.YawDeg));
	const float AxisRad = FMath::DegreesToRadians(Plan.TiltAxisDeg);
	const FQuat Tilt(FVector(FMath::Cos(AxisRad), FMath::Sin(AxisRad), 0.f), FMath::DegreesToRadians(Plan.TiltDeg));
	FVector Location;
	FQuat Rotation;
	if (At)
	{
		Location = *At;
		Rotation = Tilt * Yaw;
	}
	else
	{
		// On the landscape under its centre (a trace at spawn), turned to the ground's slope (the rest mesh's, as a clod's), tilted
		// and yawed, then lifted along the normal until the hull's lowest point is on the ground: nothing drops, nothing starts inside.
		float GroundZ = 0.f;
		if (!TraceGround(static_cast<float>(Plan.XYCm.X), static_cast<float>(Plan.XYCm.Y), GroundZ))
		{
			++MudChunksNoGround;
			return INDEX_NONE;
		}
		const double StepCm = Field.CellCm;
		const double RestX = (MeshRestZAt(Plan.XYCm + FVector2D(StepCm, 0.0)) - MeshRestZAt(Plan.XYCm - FVector2D(StepCm, 0.0))) / (2.0 * StepCm);
		const double RestY = (MeshRestZAt(Plan.XYCm + FVector2D(0.0, StepCm)) - MeshRestZAt(Plan.XYCm - FVector2D(0.0, StepCm))) / (2.0 * StepCm);
		const FVector Normal = FVector(-RestX, -RestY, 1.0).GetSafeNormal();
		Rotation = FQuat::FindBetweenNormals(FVector::UpVector, Normal.IsNearlyZero() ? FVector::UpVector : Normal) * Tilt * Yaw;
		double Lowest = 0.0;
		for (const FVector& Vertex : MudChunkHullVerts[MeshNo])
		{
			Lowest = FMath::Min(Lowest, FVector::DotProduct(Rotation.RotateVector(Vertex * Scale), Normal));
		}
		Location = FVector(Plan.XYCm.X, Plan.XYCm.Y, GroundZ) - Normal * Lowest;
	}
	// A free slot (its pooled component), or a new one.
	int32 Slot = MudChunks.IndexOfByPredicate([](const FMudChunk& Chunk) { return !Chunk.bAlive; });
	if (Slot == INDEX_NONE)
	{
		Slot = MudChunks.AddDefaulted();
		MudChunkComponents.AddDefaulted();
	}
	const float VolumeCm3 = MudChunkMeshVolume[MeshNo] * Scale * Scale * Scale;
	const float MassKg = FMath::Clamp(MudChunkKgPerL * VolumeCm3 * 1.e-3f, MudChunkMassMinKg, FMath::Max(MudChunkMassMinKg, MudChunkMassMaxKg));
	UMaterialInterface* Material = MudChunkMaterialInstance ? static_cast<UMaterialInterface*>(MudChunkMaterialInstance.Get()) : MudChunkMaterial.Get();
	UStaticMeshComponent* Component = MudChunkComponents[Slot];
	const bool bNew = Component == nullptr;
	if (bNew)
	{
		Component = NewObject<UStaticMeshComponent>(this, *FString::Printf(TEXT("MudChunk_%d"), Slot), RF_Transient);
		Component->SetMobility(EComponentMobility::Movable);
		Component->SetCanEverAffectNavigation(false);
		Component->SetGenerateOverlapEvents(false);
		Component->SetCastShadow(true);
		Component->SetCullDistance(FMath::Max(ClodCullStartCm, ClodCullEndCm));
		Component->SetNotifyRigidBodyCollision(true);
		SetMudChunkCollision(*Component);
		Component->OnComponentHit.AddDynamic(this, &AGTMudPatch::OnMudChunkHit);
		MudChunkComponents[Slot] = Component;
	}
	else
	{
		Component->SetSimulatePhysics(false);
	}
	Component->SetStaticMesh(MudChunkMeshes[MeshNo]);
	if (Material)
	{
		Component->SetMaterial(0, Material);
	}
	Component->SetWorldLocationAndRotation(Location, Rotation, false, nullptr, ETeleportType::TeleportPhysics);
	Component->SetWorldScale3D(FVector(Scale));
	Component->SetCustomPrimitiveDataFloat(0, MudChunkRandom.FRand());   // M_GT_MudChunk's ChunkRand: the tint per chunk
	Component->SetMassOverrideInKg(NAME_None, MassKg, true);
	Component->SetVisibility(true);
	Component->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Component->SetSimulatePhysics(true);
	if (bNew)
	{
		Component->RegisterComponent();
	}
	Component->SetPhysicsLinearVelocity(FVector::ZeroVector);
	Component->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
	if (bAsleep)
	{
		Component->PutRigidBodyToSleep();
	}
	FMudChunk& Chunk = MudChunks[Slot];
	Chunk.XYCm = FVector2D(Location.X, Location.Y);
	Chunk.SizeCm = Plan.SizeCm;
	Chunk.Scale = Scale;
	Chunk.VolumeCm3 = VolumeCm3;
	Chunk.MassKg = MassKg;
	Chunk.Mesh = MeshNo;
	Chunk.GridCell = INDEX_NONE;
	Chunk.AwakeSinceS = (bAsleep || !GetWorld()) ? -1.0 : GetWorld()->GetTimeSeconds();
	Chunk.bAlive = true;
	SetMudChunkGridCell(Slot, MudChunkGridCellAt(Chunk.XYCm));
	MudChunkLargestCm = FMath::Max(MudChunkLargestCm, Plan.SizeCm);
	++MudChunksLive;
	return Slot;
}

int32 AGTMudPatch::SpawnMudChunkForTest(const FVector& LocationCm, float SizeCm, int32 MeshNo, bool bAsleep)
{
	FMudChunkPlan Plan;
	Plan.XYCm = FVector2D(LocationCm.X, LocationCm.Y);
	Plan.SizeCm = FMath::Max(1.f, SizeCm);
	Plan.Mesh = MeshNo;
	return SpawnMudChunk(Plan, bAsleep, &LocationCm);
}

void AGTMudPatch::RemoveMudChunk(int32 Index)
{
	if (!IsMudChunkAlive(Index))
	{
		return;
	}
	FMudChunk& Chunk = MudChunks[Index];
	Chunk.bAlive = false;
	Chunk.AwakeSinceS = -1.0;
	SetMudChunkGridCell(Index, INDEX_NONE);
	MudChunksLive = FMath::Max(0, MudChunksLive - 1);
	if (UStaticMeshComponent* Component = GetMudChunkComponent(Index))
	{
		Component->SetSimulatePhysics(false);
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Component->SetVisibility(false);
	}
}

int32 AGTMudPatch::MudChunkGridCellAt(const FVector2D& XYCm) const
{
	if (MudChunkGridX <= 0 || MudChunkGridY <= 0)
	{
		return INDEX_NONE;
	}
	// Clamped: a chunk pushed out of the box sits in the border cells, where a wheel at the patch's edge still finds it.
	const FVector2D Local = (XYCm - Field.OriginCm) / FMath::Max(25.f, MudChunkGridCm);
	return FMath::Clamp(FMath::FloorToInt(Local.Y), 0, MudChunkGridY - 1) * MudChunkGridX + FMath::Clamp(FMath::FloorToInt(Local.X), 0, MudChunkGridX - 1);
}

void AGTMudPatch::SetMudChunkGridCell(int32 Index, int32 Cell)
{
	FMudChunk& Chunk = MudChunks[Index];
	if (Chunk.GridCell == Cell)
	{
		return;
	}
	if (MudChunkGrid.IsValidIndex(Chunk.GridCell))
	{
		MudChunkGrid[Chunk.GridCell].RemoveSingleSwap(Index);
	}
	Chunk.GridCell = Cell;
	if (MudChunkGrid.IsValidIndex(Cell))
	{
		MudChunkGrid[Cell].Add(Index);
	}
}

int32 AGTMudPatch::FindMudChunk(const UPrimitiveComponent* Component) const
{
	if (!Component)
	{
		return INDEX_NONE;
	}
	for (int32 Index = 0; Index < MudChunkComponents.Num(); ++Index)
	{
		if (MudChunkComponents[Index] == Component)
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

double AGTMudPatch::DepositLumpDome(uint8 EventKind, const FVector2D& XYCm, double VolumeCm3, float RecordRadiusCm, float DomeRadiusCm)
{
	// LM4e: timed with the stamps and recorded (the replay deposits the same dome: EventThrow through DepositThrown, EventChunk
	// on its own); a dome of DomeRadiusCm into the lumps, at least one cell, volume exact, its tile woken and its cells fresh.
	const FGTMudField::FOuterCall Call(Field);
	Call.Record(EventKind, { XYCm.X, XYCm.Y, VolumeCm3, RecordRadiusCm, DomeRadiusCm });
	return Field.DepositLump(XYCm, VolumeCm3, FMath::Max(0.f, DomeRadiusCm));
}

int32 AGTMudPatch::BreakMudChunk(int32 Index, EMudChunkBreak Why)
{
	if (!IsMudChunkAlive(Index))
	{
		return -1;
	}
	const FMudChunk Chunk = MudChunks[Index];   // a copy: the removal clears the slot
	const UStaticMeshComponent* Component = GetMudChunkComponent(Index);
	const FVector2D XY = Component ? FVector2D(Component->GetComponentLocation().X, Component->GetComponentLocation().Y) : Chunk.XYCm;
	RemoveMudChunk(Index);
	MudChunkBreaksWheel += Why == EMudChunkBreak::Wheel ? 1 : 0;
	MudChunkBreaksImpulse += Why == EMudChunkBreak::Impulse ? 1 : 0;
	MudChunkBreaksLanding += Why == EMudChunkBreak::Landing ? 1 : 0;
	MudChunkBreaksTest += Why == EMudChunkBreak::Test ? 1 : 0;
	// Its exact volume into the field where it lies, as DepositThrown's dome of MudChunkDomeRadius x its size (off the field: lost).
	const float Dome = MudChunkDomeRadius * Chunk.SizeCm;
	const double Put = DepositLumpDome(FGTMudField::EventChunk, XY, Chunk.VolumeCm3, Dome, Dome);
	if (Put > 0.0)
	{
		MudChunkDepositedCm3 += Put;
	}
	else
	{
		MudChunkLostCm3 += Chunk.VolumeCm3;
	}
	// MudChunkClodsMin..Max LM2c clods of MudChunkClodSizeMin..Max x its size within MudChunkClodScatter x its size (Source 5),
	// from the chunks' own stream (the throw's clod roll keeps its numbers). gt.Mud.Clods 0, or no clod mesh: dropped.
	const int32 Count = MudChunkRandom.RandRange(FMath::Max(0, MudChunkClodsMin), FMath::Max(MudChunkClodsMin, MudChunkClodsMax));
	if (!bClodsVisible || ClodMeshes.Num() == 0)
	{
		ClodsDropped += Count;
		return 0;
	}
	const int32 Before = ClodsFromChunk;
	for (int32 K = 0; K < Count; ++K)
	{
		const float Angle = MudChunkRandom.FRandRange(0.f, 2.f * PI);
		const float Radius = MudChunkClodScatter * Chunk.SizeCm * FMath::Sqrt(MudChunkRandom.FRand());
		FGTMudField::FClodSpawn Spawn;
		Spawn.XYCm = XY + FVector2D(FMath::Cos(Angle), FMath::Sin(Angle)) * Radius;
		Spawn.SizeCm = MudChunkRandom.FRandRange(MudChunkClodSizeMin, FMath::Max(MudChunkClodSizeMin, MudChunkClodSizeMax)) * Chunk.SizeCm;
		Spawn.Seed = MudChunkRandom.RandHelper(MAX_int32);
		Spawn.Source = 5;
		SpawnClod(Spawn);
	}
	return ClodsFromChunk - Before;
}

int32 AGTMudPatch::BreakMudChunksUnderWheel(const FVector2D& FromCm, const FVector2D& ToCm, float HalfWidthCm)
{
	if (MudChunksLive <= 0 || MudChunkGrid.Num() == 0)
	{
		return 0;
	}
	// The grid cells the capsule's box reaches (out to the largest chunk's footprint), then each chunk's footprint circle exactly.
	const float Half = FMath::Max(0.f, HalfWidthCm);
	const float Reach = Half + MudChunkFootprint * MudChunkLargestCm;
	const int32 C0 = MudChunkGridCellAt(FVector2D(FMath::Min(FromCm.X, ToCm.X) - Reach, FMath::Min(FromCm.Y, ToCm.Y) - Reach));
	const int32 C1 = MudChunkGridCellAt(FVector2D(FMath::Max(FromCm.X, ToCm.X) + Reach, FMath::Max(FromCm.Y, ToCm.Y) + Reach));
	TArray<int32, TInlineAllocator<16>> Hits;
	for (int32 GY = C0 / MudChunkGridX; GY <= C1 / MudChunkGridX; ++GY)
	{
		for (int32 GX = C0 % MudChunkGridX; GX <= C1 % MudChunkGridX; ++GX)
		{
			for (const int32 Index : MudChunkGrid[GY * MudChunkGridX + GX])
			{
				const FMudChunk& Chunk = MudChunks[Index];
				if (Chunk.bAlive && SegmentDistance(Chunk.XYCm, FromCm, ToCm) < Half + MudChunkFootprint * Chunk.SizeCm)
				{
					Hits.Add(Index);
				}
			}
		}
	}
	for (const int32 Index : Hits)
	{
		BreakMudChunk(Index, EMudChunkBreak::Wheel);
	}
	return Hits.Num();
}

void AGTMudPatch::OnMudChunkHit(UPrimitiveComponent* HitComponent, AActor* OtherActor, UPrimitiveComponent* OtherComponent, FVector NormalImpulse, const FHitResult& Hit)
{
	const int32 Index = FindMudChunk(HitComponent);
	if (!IsMudChunkAlive(Index))
	{
		return;
	}
	const float Impulse = static_cast<float>(NormalImpulse.Size());   // kg cm/s
	const ECollisionChannel Other = OtherComponent ? OtherComponent->GetCollisionObjectType() : ECC_WorldStatic;
	if (Other == ECC_Vehicle)
	{
		// (b) the chassis: over ChunkBreakImpulse it breaks, under it the chunk is pushed (the physics does that).
		MudChunkMaxChassisImpulse = FMath::Max(MudChunkMaxChassisImpulse, Impulse);
		if (Impulse > ChunkBreakImpulse)
		{
			BreakMudChunk(Index, EMudChunkBreak::Impulse);
		}
	}
	else if (Other == ECC_WorldStatic)
	{
		// (c) the ground: the speed the hit took out of it, its impulse over its mass (cm/s; a sleeping chunk makes no hit).
		const float Speed = Impulse / FMath::Max(1.f, MudChunks[Index].MassKg);
		MudChunkMaxLandCmPerS = FMath::Max(MudChunkMaxLandCmPerS, Speed);
		if (Speed > ChunkBreakLandCmPerS)
		{
			BreakMudChunk(Index, EMudChunkBreak::Landing);
		}
	}
}

void AGTMudPatch::ApplyMudChunkSwitch(bool bOn)
{
	bMudChunksOn = bOn;
	if (!bOn)
	{
		// Removed, nothing deposited: the field (and its CRC) as if there had been none.
		int32 Removed = 0;
		for (int32 Index = 0; Index < MudChunks.Num(); ++Index)
		{
			if (MudChunks[Index].bAlive)
			{
				RemoveMudChunk(Index);
				++Removed;
			}
		}
		MudChunksSwitchedOff += Removed;
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: gt.Mud.Chunks 0 - %d chunk(s) removed (MR5)"), SectionIndex, Removed);
		return;
	}
	if (MudChunkMeshCount > 0 && HasSoftSpots())
	{
		// Back at 1: placed anew on the cells the wheels have not touched (the plan's seed, so an untouched field gets the same chunks).
		TArray<FMudChunkPlan> Plan;
		PlanMudChunks(Plan, true);
		const int32 Spawned = SpawnPlannedMudChunks(Plan);
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: gt.Mud.Chunks 1 - %d of %d planned chunk(s) placed on untouched ground (MR5)"), SectionIndex, Spawned, Plan.Num());
	}
}

void AGTMudPatch::UpdateMudChunks(float DeltaSeconds)
{
	const bool bOn = CVarMudChunks.GetValueOnGameThread() != 0;
	if (bOn != bMudChunksOn)
	{
		ApplyMudChunkSwitch(bOn);
	}
	int32 Awake = 0;
	if (MudChunksLive > 0)
	{
		const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
		for (int32 Index = 0; Index < MudChunks.Num(); ++Index)
		{
			FMudChunk& Chunk = MudChunks[Index];
			UStaticMeshComponent* Component = GetMudChunkComponent(Index);
			if (!Chunk.bAlive || !Component)
			{
				continue;
			}
			if (!Component->RigidBodyIsAwake())
			{
				Chunk.AwakeSinceS = -1.0;
				continue;
			}
			if (Chunk.AwakeSinceS < 0.0)
			{
				Chunk.AwakeSinceS = Now;
			}
			// An awake chunk moves: its place for the wheels' grid, and lost when more than MudChunkLostCm under the landscape
			// (the rest mesh inside the box, a trace outside it).
			const FVector Location = Component->GetComponentLocation();
			Chunk.XYCm = FVector2D(Location.X, Location.Y);
			SetMudChunkGridCell(Index, MudChunkGridCellAt(Chunk.XYCm));
			float GroundZ = 0.f;
			bool bGround = Field.Contains(Chunk.XYCm);
			if (bGround)
			{
				GroundZ = MeshRestZAt(Chunk.XYCm) - MeshLiftCm;
			}
			else
			{
				bGround = TraceGround(static_cast<float>(Location.X), static_cast<float>(Location.Y), GroundZ);
			}
			if (bGround && Location.Z < GroundZ - MudChunkLostCm)
			{
				++MudChunksLost;
				MudChunkLostCm3 += Chunk.VolumeCm3;
				RemoveMudChunk(Index);
				continue;
			}
			++Awake;
		}
	}
	MudChunkAwakeNow = Awake;
	MudChunkAwakePeak = FMath::Max(MudChunkAwakePeak, Awake);
	// The world-wide awake cap, once a frame (the first patch to tick runs it).
	if (UGTMudSubsystem* Mud = GetWorld() ? GetWorld()->GetSubsystem<UGTMudSubsystem>() : nullptr)
	{
		Mud->EnforceMudChunkAwakeCap();
	}
}

bool AGTMudPatch::IsMudChunkAwake(int32 Index) const
{
	const UStaticMeshComponent* Component = GetMudChunkComponent(Index);
	return IsMudChunkAlive(Index) && Component && Component->RigidBodyIsAwake();
}

void AGTMudPatch::SleepMudChunk(int32 Index)
{
	if (UStaticMeshComponent* Component = IsMudChunkAlive(Index) ? GetMudChunkComponent(Index) : nullptr)
	{
		Component->PutRigidBodyToSleep();
		MudChunks[Index].AwakeSinceS = -1.0;
	}
}

float AGTMudPatch::MudChunkLowestHullZ(int32 Index) const
{
	const UStaticMeshComponent* Component = GetMudChunkComponent(Index);
	if (!Component)
	{
		return 0.f;
	}
	const FTransform Transform = Component->GetComponentTransform();
	const int32 MeshNo = MudChunkMesh(Index);
	if (!MudChunkHullVerts.IsValidIndex(MeshNo) || MudChunkHullVerts[MeshNo].Num() == 0)
	{
		return static_cast<float>(Transform.GetLocation().Z);
	}
	double Lowest = 1.0e12;
	for (const FVector& Vertex : MudChunkHullVerts[MeshNo])
	{
		Lowest = FMath::Min(Lowest, Transform.TransformPosition(Vertex).Z);
	}
	return static_cast<float>(Lowest);
}

TArray<FVector4> AGTMudPatch::GetMudChunksForCheck() const
{
	TArray<FVector4> Out;
	for (int32 Index = 0; Index < MudChunks.Num(); ++Index)
	{
		if (MudChunks[Index].bAlive)
		{
			const UStaticMeshComponent* Component = GetMudChunkComponent(Index);
			const FVector Location = Component ? Component->GetComponentLocation() : FVector(MudChunks[Index].XYCm.X, MudChunks[Index].XYCm.Y, 0.0);
			Out.Add(FVector4(Location.X, Location.Y, MudChunks[Index].SizeCm, IsMudChunkAwake(Index) ? 1.0 : 0.0));
		}
	}
	return Out;
}

FString AGTMudPatch::DescribeMudChunks() const
{
	return FString::Printf(TEXT("{\"section\":%d,\"on\":%d,\"meshes\":%d,\"candidate_m2\":%.2f,\"density_scale\":%.3f,\"target\":%d,\"planned\":%d,\"live\":%d,\"spawned\":%d,\"no_ground\":%d,")
		TEXT("\"breaks\":{\"wheel\":%d,\"impulse\":%d,\"landing\":%d,\"test\":%d},\"lost\":%d,\"switched_off\":%d,\"deposited_cm3\":%.1f,\"lost_cm3\":%.1f,")
		TEXT("\"awake_now\":%d,\"awake_peak\":%d,\"clods\":%d,\"max_chassis_impulse\":%.1f,\"max_land_cm_s\":%.1f}"),
		SectionIndex, bMudChunksOn ? 1 : 0, MudChunkMeshCount, MudChunkCandidateM2, MudChunkDensityScale, MudChunkTarget, MudChunksPlanned, MudChunksLive, MudChunksSpawned, MudChunksNoGround,
		MudChunkBreaksWheel, MudChunkBreaksImpulse, MudChunkBreaksLanding, MudChunkBreaksTest, MudChunksLost, MudChunksSwitchedOff, MudChunkDepositedCm3, MudChunkLostCm3,
		MudChunkAwakeNow, MudChunkAwakePeak, ClodsFromChunk, MudChunkMaxChassisImpulse, MudChunkMaxLandCmPerS);
}

// ---- Ground relief GR1 item 4 (docs/GROUND_RELIEF_PLAN.md): the bog's pre-churn ------------------------------------------
void AGTMudPatch::PreChurn()
{
	PreChurnBaseCm.Reset();
	PreChurnSurfaceCm.Reset();
	PreChurnDepthsCm.Reset();
	PreChurnTracks = 0;
	PreChurnDepthLoCm = 0.f;
	PreChurnDepthHiCm = 0.f;
	PreChurnHummockCm = 0.f;
	PreChurnWaterCells = 0;
	PreChurnRimMaxCm = 0.f;
	PreChurnFilledLoCm = 0.f;
	PreChurnFilledShare = 0.f;
	PreChurnTrackCells = 0;
	PreChurnSlopeMaxDeg = 0.f;
	PreChurnPresentShares.Reset();
	PreChurnPuddleShare = 0.f;
	PreChurnPuddleDepthHiCm = 0.f;
	PreChurnPuddleBasins = 0;
	PreChurnPuddleWet = 0;
	PreChurnPuddleWallDeg = 0.f;
	PreChurnBoxLineCm = 0.f;
	const float Scale = FMath::Max(0.f, PreChurnScale);
	// The scope: MR4's (a Mud-medium bog patch without a profile), with a scale, the switch on and a route line to follow.
	if (!Field.IsValid() || IsSnow() || bHasProfile || Medium != EGTDeformMedium::Mud || Scale <= 0.f || RouteLineCm.Num() < 2)
	{
		if (Scale > 0.f)
		{
			UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: pre-churn (GR1) - none (%s)"), SectionIndex,
				bHasProfile ? TEXT("a profiled patch") : RouteLineCm.Num() < 2 ? TEXT("no route line") : TEXT("not a bog's mud field"));
		}
		return;
	}
	if (CVarMudPreChurn.GetValueOnGameThread() == 0)
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: pre-churn (GR1) - off (gt.Mud.PreChurn 0), the flat field"), SectionIndex);
		return;
	}
	const int32 SX = Field.SizeX;
	const int32 SY = Field.SizeY;
	const int32 Cells = SX * SY;
	const float Cell = Field.CellCm;
	FRandomStream Random(104723 * (SectionIndex + 1) + 7);
	// 1. The hummocks into HeightCm: two octaves of the field's own value noise (PreChurnHummockWaveCm and the fine one), their
	// amplitude between Min and Max by a cluster noise (clustered: mostly low, some stretches strong), the sum's peak at it.
	const int32 Salt = 7001 + 97 * SectionIndex;
	const float WaveCells = FMath::Max(1.f, PreChurnHummockWaveCm / Cell);
	const float FineCells = FMath::Max(1.f, PreChurnHummockFineWaveCm / Cell);
	const float ClusterCells = FMath::Max(1.f, PreChurnClusterCm / Cell);
	// MRD1: a mud road's hummocks x RoadHummockScale (its ridges come from the tracks' banks).
	const float HummockK = PreChurnStyle == EGTPreChurnStyle::Braided ? FMath::Max(0.f, RoadHummockScale) : 1.f;
	const float AmpLo = FMath::Max(0.f, PreChurnHummockMinCm) * Scale * HummockK;
	const float AmpHi = FMath::Max(PreChurnHummockMinCm, PreChurnHummockMaxCm) * Scale * HummockK;
	PreChurnBaseCm.Init(0.f, Cells);
	for (int32 Y = 0; Y < SY; ++Y)
	{
		for (int32 X = 0; X < SX; ++X)
		{
			// The value noise sits mostly within +-0.5 of 0: x1.6 and a clamp take the sum's peaks to +-1, and the cluster's square
			// keeps most of the patch at the low amplitude.
			const float Cluster = FMath::Clamp(0.5f + 0.8f * Field.CellNoise(X, Y, ClusterCells, Salt + 3), 0.f, 1.f);
			const float Amp = FMath::Lerp(AmpLo, AmpHi, Cluster * Cluster);
			const float N = FMath::Clamp(1.6f * (0.65f * Field.CellNoise(X, Y, WaveCells, Salt + 1) + 0.35f * Field.CellNoise(X, Y, FineCells, Salt + 2)), -1.f, 1.f);
			PreChurnBaseCm[Y * SX + X] = Amp * N;
		}
	}
	for (int32 Index = 0; Index < Cells; ++Index)
	{
		Field.HeightCm[Index] += PreChurnBaseCm[Index];
	}
	// MRD1 (docs/MUD_ROADS_PLAN.md): a mud road lays braided tracks in place of the pairs (steps 2-4 its own).
	if (PreChurnStyle == EGTPreChurnStyle::Braided)
	{
		PreChurnBraided(Random, Scale);
		return;
	}
	// 2. The old rut pairs along the route line, run through the whole box (the line carried straight on past its ends).
	// GR1c (docs/GROUND_RELIEF_PLAN.md, decisions after phase A): a layout, not a bundle of grooves - PreChurnPairs pair per patch,
	// PreChurnPairsLong where the route runs more than PreChurnLongPatchCm through the box, each with its own centre and wander
	// (two sines of different wavelengths, at most PreChurnWanderCm), so two cross, merge and split; each wheel line
	// PreChurnWidthMin-Max x its tyre wide at half depth (knots 2-4 m apart), PreChurnDepthMin-MaxCm deep (knots 1-3 m apart,
	// x PreChurnSoftDeepen where S is over 0.6, within the range); each pair fading in and out over PreChurnFadeMin-MaxCm at
	// random points, PreChurnPresentMin-Max of its length in the box present (no pair runs the whole box); and where the section
	// has a water table, the lowest-lying PreChurnPuddleShareMin-Max of each line's present length cut to PreChurnPuddleBelowMin-MaxCm
	// under it (step 3b, after the settle, whose relax gives a set cell RecoverShare of its depth back: cut before it, a 30 cm puddle
	// came out 10-15 cm shallower, above the table), so rut water stands there.
	TArray<float> ArcCm;
	ArcCm.Add(0.f);
	for (int32 K = 1; K < RouteLineCm.Num(); ++K)
	{
		ArcCm.Add(ArcCm.Last() + static_cast<float>(FVector2D::Distance(RouteLineCm[K - 1], RouteLineCm[K])));
	}
	const float LineCm = ArcCm.Last();
	const float ExtendCm = static_cast<float>(Field.Bounds().GetSize().GetMax());
	auto OnLine = [&](float S, FVector2D& OutDir)
	{
		const int32 Last = RouteLineCm.Num() - 1;
		if (S <= 0.f)
		{
			OutDir = (RouteLineCm[1] - RouteLineCm[0]).GetSafeNormal();
			return RouteLineCm[0] + OutDir * S;
		}
		if (S >= LineCm)
		{
			OutDir = (RouteLineCm[Last] - RouteLineCm[Last - 1]).GetSafeNormal();
			return RouteLineCm[Last] + OutDir * (S - LineCm);
		}
		int32 K = 1;
		while (K < Last && ArcCm[K] < S)
		{
			++K;
		}
		const float Span = FMath::Max(1.e-3f, ArcCm[K] - ArcCm[K - 1]);
		OutDir = (RouteLineCm[K] - RouteLineCm[K - 1]).GetSafeNormal();
		return FMath::Lerp(RouteLineCm[K - 1], RouteLineCm[K], (S - ArcCm[K - 1]) / Span);
	};
	const FBox2D Box = Field.Bounds();
	const float StepCm = 25.f;
	const float S0 = -ExtendCm;
	const float S1 = LineCm + ExtendCm;
	// The route's stretch inside the box: its length picks the pair count, the presence and the puddles are measured over it.
	float SA = TNumericLimits<float>::Max();
	float SB = -TNumericLimits<float>::Max();
	for (float S = S0; S <= S1; S += StepCm)
	{
		FVector2D Dir;
		if (Box.IsInside(OnLine(S, Dir)))
		{
			SA = FMath::Min(SA, S);
			SB = FMath::Max(SB, S);
		}
	}
	if (SB < SA)
	{
		SA = 0.f;
		SB = LineCm;
	}
	PreChurnBoxLineCm = SB - SA;
	const int32 Pairs = FMath::Max(0, PreChurnBoxLineCm > PreChurnLongPatchCm ? PreChurnPairsLong : PreChurnPairs);
	float DepthLo = TNumericLimits<float>::Max();
	float DepthHi = 0.f;
	float FilledLo = TNumericLimits<float>::Max();
	double FilledLength = 0.0;
	double TrackLength = 0.0;
	double PresentLength = 0.0;
	double PuddleLength = 0.0;
	// GR1b (docs/GROUND_RELIEF_PLAN.md GR1b item 1): the old tracks are drawn here, not by the field's wheel stamp, whose capsule cut a
	// tyre-wide flat floor between near-vertical two-cell walls (the dark lines: the mesh's own shadow along that floor and its dark
	// wall, gt.Mud.PreChurnDebug 2's smoothing took them away). Each wheel line is a cosine trough, D (0.5 + 0.5 cos(pi d / w)) across,
	// w its width at half depth and at least PreChurnWallPerDepth x D (so the steepest flank is about atan(pi / (2 x 2.6)) = 31 deg
	// before the wander); a cosine bank beside it carries PreChurnBankReturn of what it took; 20-40 % of each line's length in
	// segments filled back to 30-60 % of its depth (0.4 m ramps, irregular gaps). The cuts take the deepest line at a cell, the
	// banks the highest; the tracks factor and the lumps follow the presence, and a puddle's floor carries no lumps.
	const int32 Cells2 = SX * SY;
	TArray<float> Cut;
	TArray<float> Bank;
	TArray<float> CutShape;
	Cut.Init(0.f, Cells2);
	Bank.Init(0.f, Cells2);
	CutShape.Init(0.f, Cells2);
	const float BankReturn = FMath::Clamp(PreChurnBankReturn, 0.f, 1.f);
	auto Knots = [&Random](float K0, float K1, float MinGap, float MaxGap, float Lo, float Hi, TArray<FVector2f>& Out)
	{
		Out.Reset();
		for (float S = K0 - MaxGap; S <= K1 + MaxGap; S += Random.FRandRange(MinGap, MaxGap))
		{
			Out.Add(FVector2f(S, static_cast<float>(Random.FRandRange(Lo, Hi))));
		}
		Out.Add(FVector2f(K1 + 2.f * MaxGap, static_cast<float>(Random.FRandRange(Lo, Hi))));
	};
	auto KnotAt = [](const TArray<FVector2f>& K, float S)
	{
		int32 I = 1;
		while (I < K.Num() - 1 && K[I].X < S)
		{
			++I;
		}
		const float T = FMath::Clamp((S - K[I - 1].X) / FMath::Max(1.f, K[I].X - K[I - 1].X), 0.f, 1.f);
		return FMath::Lerp(K[I - 1].Y, K[I].Y, T * T * (3.f - 2.f * T));
	};
	// A per-cell value under a point, bilinear (step 3b reads the settled surface under each puddle step).
	auto SampleAt = [&](const TArray<float>& Grid, const FVector2D& P)
	{
		const float FX = FMath::Clamp(static_cast<float>((P.X - Field.OriginCm.X) / Cell) - 0.5f, 0.f, static_cast<float>(SX - 1));
		const float FY = FMath::Clamp(static_cast<float>((P.Y - Field.OriginCm.Y) / Cell) - 0.5f, 0.f, static_cast<float>(SY - 1));
		const int32 X0 = FMath::Min(FMath::FloorToInt32(FX), SX - 1);
		const int32 Y0 = FMath::Min(FMath::FloorToInt32(FY), SY - 1);
		const int32 X1 = FMath::Min(X0 + 1, SX - 1);
		const int32 Y1 = FMath::Min(Y0 + 1, SY - 1);
		const float TX = FX - X0;
		const float TY = FY - Y0;
		return FMath::Lerp(FMath::Lerp(Grid[Y0 * SX + X0], Grid[Y0 * SX + X1], TX), FMath::Lerp(Grid[Y1 * SX + X0], Grid[Y1 * SX + X1], TX), TY);
	};
	const float RimCm0 = FMath::Max(1.f, PreChurnRimCm);
	const float FadeLo = FMath::Max(50.f, FMath::Min(PreChurnFadeMinCm, PreChurnFadeMaxCm));
	const float FadeHi = FMath::Max(FadeLo, PreChurnFadeMaxCm);
	const float PresentLo = FMath::Clamp(FMath::Min(PreChurnPresentMin, PreChurnPresentMax), 0.05f, 1.f);
	const float PresentHi = FMath::Clamp(FMath::Max(PreChurnPresentMin, PreChurnPresentMax), PresentLo, 1.f);
	// The presence along a pair: hold, fade over 3-8 m, hold the other way, ... from a random phase; drawn until the share over the
	// box is within PresentLo-Hi and the visible stretch (inside the rim) has both an absent and a present place (at most 32 draws,
	// else the closest). Returns the share.
	auto Presence = [&](TArray<FVector2f>& Out)
	{
		const float Want = static_cast<float>(Random.FRandRange(PresentLo, PresentHi));
		const float FadeMean = 0.5f * (FadeLo + FadeHi);
		float BestErr = TNumericLimits<float>::Max();
		float BestShare = 0.f;
		for (int32 Try = 0; Try < 32; ++Try)
		{
			TArray<FVector2f> K;
			const float Cycle = FMath::Max(2.f * FadeHi, static_cast<float>(Random.FRandRange(FMath::Min(PreChurnFadeCycleMinCm, PreChurnFadeCycleMaxCm), FMath::Max(PreChurnFadeCycleMinCm, PreChurnFadeCycleMaxCm))));
			const float HoldOn = FMath::Max(0.f, Want * Cycle - FadeMean);
			const float HoldOff = FMath::Max(0.f, (1.f - Want) * Cycle - FadeMean);
			float S = SA - FadeHi - static_cast<float>(Random.FRandRange(0.f, Cycle));
			float V = Random.FRand() < Want ? 1.f : 0.f;
			K.Add(FVector2f(FMath::Min(S, S0) - 1.f, V));
			K.Add(FVector2f(S, V));
			while (S < SB + FadeHi)
			{
				S += (V > 0.5f ? HoldOn : HoldOff) * static_cast<float>(Random.FRandRange(0.6f, 1.4f));
				K.Add(FVector2f(S, V));
				S += static_cast<float>(Random.FRandRange(FadeLo, FadeHi));
				V = 1.f - V;
				K.Add(FVector2f(S, V));
			}
			K.Add(FVector2f(FMath::Max(S, S1) + 1.f, V));
			double Sum = 0.0;
			int32 N = 0;
			float VisLo = 1.f;
			float VisHi = 0.f;
			for (float T = SA; T <= SB; T += StepCm)
			{
				const float P = KnotAt(K, T);
				Sum += P;
				++N;
				if (T >= SA + RimCm0 && T <= SB - RimCm0)
				{
					VisLo = FMath::Min(VisLo, P);
					VisHi = FMath::Max(VisHi, P);
				}
			}
			const float Share = N > 0 ? static_cast<float>(Sum / N) : 0.f;
			const float Err = FMath::Abs(Share - FMath::Clamp(Share, PresentLo, PresentHi)) + (VisLo > 0.05f ? 1.f : 0.f) + (VisHi < 0.95f ? 1.f : 0.f);
			if (Err < BestErr)
			{
				BestErr = Err;
				BestShare = Share;
				Out = K;
			}
			if (Err <= 0.f)
			{
				break;
			}
		}
		return BestShare;
	};
	const float Table = WaterTableCm;
	const bool bPuddles = Table <= 0.f && Table >= -FMath::Max(0.f, PreChurnPuddleTableMaxCm);
	struct FLineStep { FVector2D P; float Filled = 0.f; float Depth = 0.f; float Present = 0.f; float WidthK = 0.f; bool bInBox = false; bool bInFill = false; };
	// Step 3b's input: every wheel line's steps - place, presence, the track's width at half depth, inside the box or not.
	struct FTrackStep { FVector2D P; float Present = 0.f; float HalfW = 0.f; bool bInBox = false; };
	TArray<TArray<FTrackStep>> TrackLines;
	for (int32 Pair = 0; Pair < Pairs; ++Pair)
	{
		const float Centre = Random.FRandRange(-1.f, 1.f) * PreChurnSpreadCm;
		const float Wave1 = FMath::Max(100.f, Random.FRandRange(FMath::Min(PreChurnWanderWaveMinCm, PreChurnWanderWaveMaxCm), FMath::Max(PreChurnWanderWaveMinCm, PreChurnWanderWaveMaxCm)));
		const float Wave2 = Wave1 * Random.FRandRange(1.6f, 2.1f);
		const float Phase1 = Random.FRandRange(0.f, 2.f * PI);
		const float Phase2 = Random.FRandRange(0.f, 2.f * PI);
		const float Gauge = Random.FRandRange(150.f, 180.f);
		const float Tyre = Random.FRandRange(25.f, 32.f);
		auto LateralAt = [&](float S)
		{
			return Centre + PreChurnWanderCm * (0.7f * FMath::Sin(2.f * PI * S / Wave1 + Phase1) + 0.3f * FMath::Sin(2.f * PI * S / Wave2 + Phase2));
		};
		TArray<FVector2f> PresentKnots;
		PreChurnPresentShares.Add(Presence(PresentKnots));
		bool bInside = false;
		for (int32 Side = -1; Side <= 1; Side += 2)
		{
			// This line's depth, width and fill along its length; its presence the pair's, shifted a little (the two wheels' tracks do
			// not end abreast).
			TArray<FVector2f> DepthKnots;
			TArray<FVector2f> WidthKnots;
			Knots(S0, S1, FMath::Max(10.f, PreChurnDepthKnotMinCm), FMath::Max(PreChurnDepthKnotMinCm, PreChurnDepthKnotMaxCm), 0.f, 1.f, DepthKnots);
			Knots(S0, S1, 200.f, 400.f, 0.f, 1.f, WidthKnots);
			const float Shift = static_cast<float>(Random.FRandRange(-75.f, 75.f));
			struct FFill { float A; float B; float Share; };
			TArray<FFill> Fills;
			const float FillShare = Random.FRandRange(FMath::Min(PreChurnFillShareMin, PreChurnFillShareMax), FMath::Max(PreChurnFillShareMin, PreChurnFillShareMax));
			for (float S = S0 + Random.FRandRange(0.f, 300.f); S < S1;)
			{
				const float Len = Random.FRandRange(80.f, 300.f);
				Fills.Add({ S, S + Len, static_cast<float>(Random.FRandRange(FMath::Min(PreChurnFillDepthMin, PreChurnFillDepthMax), FMath::Max(PreChurnFillDepthMin, PreChurnFillDepthMax))) });
				// The gap to the next: its mean keeps the filled share, x0.3-1.7 so the gaps are irregular.
				S += Len + 190.f * (1.f - FillShare) / FMath::Max(0.05f, FillShare) * Random.FRandRange(0.3f, 1.7f);
			}
			// The fill inside each segment, ramped over its first and last 40 cm (so the segments' own lengths are the filled share).
			auto FillAt = [&Fills](float S, bool& bInFill)
			{
				float F = 0.f;
				bInFill = false;
				for (const FFill& Seg : Fills)
				{
					if (S >= Seg.A && S <= Seg.B)
					{
						bInFill = true;
						const float Ramp = FMath::Min(40.f, 0.5f * (Seg.B - Seg.A));
						F = FMath::Max(F, Seg.Share * FMath::SmoothStep(Seg.A, Seg.A + Ramp, S) * (1.f - FMath::SmoothStep(Seg.B - Ramp, Seg.B, S)));
					}
				}
				return F;
			};
			// The line, step by step: where it is, its depth asked and filled, its presence.
			const int32 Steps = FMath::CeilToInt((S1 - S0) / StepCm);
			TArray<FLineStep> Line;
			Line.SetNum(Steps + 1);
			const float DepthMin = FMath::Max(0.f, PreChurnDepthMinCm) * Scale;
			const float DepthMax = FMath::Max(PreChurnDepthMinCm, PreChurnDepthMaxCm) * Scale;
			for (int32 Step = 0; Step <= Steps; ++Step)
			{
				FLineStep& L = Line[Step];
				const float S = S0 + Step * StepCm;
				FVector2D Dir;
				const FVector2D OnRoute = OnLine(S, Dir);
				const FVector2D Left(-Dir.Y, Dir.X);
				L.P = OnRoute + Left * (LateralAt(S) + Side * 0.5f * Gauge);
				L.Depth = FMath::Lerp(DepthMin, DepthMax, KnotAt(DepthKnots, S));
				if (HasSoftSpots() && SoftnessAt(L.P) > 0.6f)
				{
					L.Depth = FMath::Min(DepthMax, L.Depth * FMath::Max(1.f, PreChurnSoftDeepen));
				}
				L.Filled = L.Depth * (1.f - FillAt(S, L.bInFill));
				L.Present = FMath::Clamp(KnotAt(PresentKnots, S + Shift), 0.f, 1.f);
				L.WidthK = KnotAt(WidthKnots, S);
				L.bInBox = Box.IsInside(L.P);
			}
			// Into the cut and bank grids.
			FVector2D Prev = FVector2D::ZeroVector;
			float PrevD = 0.f;
			float PrevW = 0.f;
			float PrevP = 0.f;
			for (int32 Step = 0; Step < Line.Num(); ++Step)
			{
				const FLineStep& L = Line[Step];
				const FVector2D P = L.P;
				const float D = L.Filled * L.Present;
				const float HalfW = FMath::Max(Tyre * FMath::Lerp(PreChurnWidthMin, FMath::Max(PreChurnWidthMin, PreChurnWidthMax), L.WidthK), FMath::Max(1.f, PreChurnWallPerDepth) * D);
				if (L.bInBox)
				{
					PreChurnDepthsCm.Add(L.Depth);
					DepthLo = FMath::Min(DepthLo, L.Depth);
					DepthHi = FMath::Max(DepthHi, L.Depth);
					FilledLo = FMath::Min(FilledLo, L.Filled);
					TrackLength += StepCm;
					FilledLength += L.bInFill ? StepCm : 0.0;
					PresentLength += L.Present >= 0.5f ? StepCm : 0.0;
					bInside = true;
				}
				if (Step > 0 && (D > 0.01f || PrevD > 0.01f) && (Box.ExpandBy(200.f).IsInside(P) || Box.ExpandBy(200.f).IsInside(Prev)))
				{
					// The segment Prev-P into the cells within the reach of its trough and bank.
					const float Reach = 2.2f * FMath::Max(HalfW, PrevW) + Cell;
					const FVector2D Lo = FVector2D::Min(Prev, P) - FVector2D(Reach, Reach) - Field.OriginCm;
					const FVector2D Hi = FVector2D::Max(Prev, P) + FVector2D(Reach, Reach) - Field.OriginCm;
					const int32 X0 = FMath::Clamp(FMath::FloorToInt32(Lo.X / Cell), 0, SX - 1);
					const int32 Y0 = FMath::Clamp(FMath::FloorToInt32(Lo.Y / Cell), 0, SY - 1);
					const int32 X1 = FMath::Clamp(FMath::CeilToInt32(Hi.X / Cell), 0, SX - 1);
					const int32 Y1 = FMath::Clamp(FMath::CeilToInt32(Hi.Y / Cell), 0, SY - 1);
					const FVector2D AB = P - Prev;
					const double Len2 = FMath::Max(1.e-6, AB.SizeSquared());
					for (int32 Y = Y0; Y <= Y1; ++Y)
					{
						for (int32 X = X0; X <= X1; ++X)
						{
							const int32 Index = Y * SX + X;
							const FVector2D C = Field.CellCentreCm(Index);
							const float T = static_cast<float>(FMath::Clamp(FVector2D::DotProduct(C - Prev, AB) / Len2, 0.0, 1.0));
							const float Dist = static_cast<float>(FVector2D::Distance(C, Prev + AB * T));
							const float DT = FMath::Lerp(PrevD, D, T);
							const float W = FMath::Lerp(PrevW, HalfW, T);
							if (Dist < W)
							{
								const float Shape = 0.5f + 0.5f * FMath::Cos(PI * Dist / W);
								Cut[Index] = FMath::Max(Cut[Index], DT * Shape);
								CutShape[Index] = FMath::Max(CutShape[Index], Shape * FMath::Lerp(PrevP, L.Present, T));
							}
							else if (Dist < 2.2f * W)
							{
								// The bank: a cosine hump 1.2 w wide outside the trough, BankReturn of the trough's section (D w) over both banks.
								const float U = (Dist - W) / (1.2f * W);
								Bank[Index] = FMath::Max(Bank[Index], BankReturn * DT / 1.2f * 0.5f * (1.f - FMath::Cos(2.f * PI * U)));
							}
						}
					}
				}
				Prev = P;
				PrevD = D;
				PrevW = HalfW;
				PrevP = L.Present;
			}
			// The line for step 3b's puddles.
			TArray<FTrackStep>& Out = TrackLines.AddDefaulted_GetRef();
			for (const FLineStep& L : Line)
			{
				Out.Add({ L.P, L.Present, Tyre * FMath::Lerp(PreChurnWidthMin, FMath::Max(PreChurnWidthMin, PreChurnWidthMax), L.WidthK), L.bInBox });
			}
		}
		PreChurnTracks += bInside ? 1 : 0;
	}
	PreChurnDepthLoCm = PreChurnDepthsCm.Num() > 0 ? DepthLo : 0.f;
	PreChurnDepthHiCm = DepthHi;
	PreChurnFilledLoCm = PreChurnDepthsCm.Num() > 0 ? FilledLo : 0.f;
	PreChurnFilledShare = TrackLength > 0.0 ? static_cast<float>(FilledLength / TrackLength) : 0.f;
	// Into the field: the cut below the hummocked ground, the bank where no trough is; the tracks factor at half the trough's shape (old
	// worked mud, MR4's material term) x the presence, and LM2's lumps re-seeded over the troughs and banks from the field's own lump
	// domes (LumpShare of the cell's disturbance x its dome weight, at most LumpMaxCm), so the 10 s settle
	// slumps them lumpy.
	PreChurnTrackCells = 0;
	TArray<uint8> Edited;
	Edited.Init(0, Cells2);
	for (int32 Index = 0; Index < Cells2; ++Index)
	{
		const float Delta = Bank[Index] * (1.f - FMath::SmoothStep(0.f, 2.f, Cut[Index])) - Cut[Index];
		if (Delta == 0.f)
		{
			continue;
		}
		Edited[Index] = 1;
		Field.HeightCm[Index] += Delta;
		Field.Tracks[Index] = FMath::Max(Field.Tracks[Index], static_cast<uint8>(FMath::Clamp(FMath::RoundToInt(127.f * CutShape[Index]), 0, 255)));
		const float Lump = FMath::Min(FMath::Max(0.f, Field.LumpMaxCm), Field.LumpShare * (Cut[Index] + Bank[Index]) * Field.LumpWeightAt(Index));
		Field.LumpCm[Index] = FMath::Max(Field.LumpCm[Index], Lump);
		PreChurnTrackCells += Cut[Index] > 0.5f ? 1 : 0;
	}
	// A stamp's bookkeeping for these cells (their set timers, their tiles awake), so the settle below works them.
	Field.WakeEdited(Edited);
	// 3. The field's own settle, PreChurnSettleS of it at its own sub-step, so the ruts read old and slumped.
	const float Dt = 1.f / 30.f;
	for (float T = 0.f; T < PreChurnSettleS - 1.e-4f; T += Dt)
	{
		Field.AdvanceClock(Dt);
		Field.Settle(Dt);
	}
	// 3b. GR1c's puddles, cut into the settled field; GR2 phase B item 7: as cosine basins. Along each wheel line the lowest-lying
	// PreChurnPuddleShareMin-Max of its present length in the box (the settled floor under its centre: water collects where the track
	// already lies lowest) makes the puddle runs, each with a floor PreChurnPuddleBelowMin-MaxCm under the table. Each run is one basin
	// inside the track's footprint: an ellipse centred on the run's lowest step, along the line over the run (+ half the ramp each
	// end), across the track's half width there; its surface rises from the flat floor by a quarter cosine to the wall limit
	// PreChurnPuddleWallMaxDeg at the ellipse's edge and on at that slope over a skirt (PreChurnPuddleSkirt of the ellipse more:
	// a 30 deg wall inside the track's half width alone reaches 0.37 of it, too little to get under Standard's -25 cm table), and the
	// field is taken down to it where it lies higher (min, so the basin's walls never add to the track's). The floor is the run's
	// depth under the table, raised until the skirt's top reaches the ground round its edge (no step where the basin ends): where
	// it still falls short the basin is shallower and may hold no water. Under it the lumps are cleared; not woken, so no relax takes it back before a wheel works it. (GR1c cut a
	// cosine trough along the run, PreChurnPuddleWallPerDepth x its depth wide, into the settled walls: 41.6-43.5 deg, and from
	// above short dark slashes.)
	PreChurnPuddleBasins = 0;
	PreChurnPuddleWet = 0;
	PreChurnPuddleWallDeg = 0.f;
	if (bPuddles && TrackLines.Num() > 0)
	{
		TArray<float> Surface;
		auto ReadSurface = [&]()
		{
			Surface.SetNumUninitialized(Cells2);
			for (int32 Index = 0; Index < Cells2; ++Index)
			{
				Surface[Index] = Field.SurfaceCm(Index);
			}
		};
		struct FBasin { FVector2D C; FVector2D Along; float A = 0.f; float B = 0.f; float FloorCm = 0.f; float RimCm = 0.f; float SkirtCm = 0.f; };
		TArray<FBasin> Basins;
		ReadSurface();
		const float WallTan = FMath::Tan(FMath::DegreesToRadians(FMath::Clamp(PreChurnPuddleWallMaxDeg, 5.f, 60.f)));
		for (const TArray<FTrackStep>& Steps : TrackLines)
		{
			TArray<float> Floor;
			Floor.Init(0.f, Steps.Num());
			TArray<float> Floors;
			for (int32 Step = 0; Step < Steps.Num(); ++Step)
			{
				if (Steps[Step].bInBox && Steps[Step].Present >= 0.5f)
				{
					Floor[Step] = SampleAt(Surface, Steps[Step].P);
					Floors.Add(Floor[Step]);
				}
			}
			if (Floors.Num() == 0)
			{
				continue;
			}
			Floors.Sort();
			const float Share = static_cast<float>(Random.FRandRange(FMath::Min(PreChurnPuddleShareMin, PreChurnPuddleShareMax), FMath::Max(PreChurnPuddleShareMin, PreChurnPuddleShareMax)));
			const float Threshold = Floors[FMath::Clamp(FMath::CeilToInt32(Share * Floors.Num()) - 1, 0, Floors.Num() - 1)];
			// The runs (each its own floor under the table), each made a basin.
			int32 RunStart = INDEX_NONE;
			float Run = 0.f;
			for (int32 Step = 0; Step <= Steps.Num(); ++Step)
			{
				const bool bRun = Step < Steps.Num() && Steps[Step].bInBox && Steps[Step].Present >= 0.5f && Floor[Step] <= Threshold;
				if (bRun && RunStart == INDEX_NONE)
				{
					RunStart = Step;
					Run = static_cast<float>(Random.FRandRange(FMath::Min(PreChurnPuddleBelowMinCm, PreChurnPuddleBelowMaxCm), FMath::Max(PreChurnPuddleBelowMinCm, PreChurnPuddleBelowMaxCm)));
				}
				if (bRun)
				{
					PuddleLength += StepCm;
					continue;
				}
				if (RunStart == INDEX_NONE)
				{
					continue;
				}
				const int32 RunEnd = Step - 1;
				int32 Low = RunStart;
				for (int32 J = RunStart; J <= RunEnd; ++J)
				{
					Low = Floor[J] < Floor[Low] ? J : Low;
				}
				const FVector2D From = Steps[FMath::Max(0, RunStart - 1)].P;
				const FVector2D To = Steps[FMath::Min(Steps.Num() - 1, RunEnd + 1)].P;
				FBasin Basin;
				Basin.C = Steps[Low].P;
				Basin.Along = (To - From).GetSafeNormal();
				if (Basin.Along.IsNearlyZero())
				{
					Basin.Along = FVector2D(1.0, 0.0);
				}
				Basin.A = FMath::Max(60.f, 0.5f * StepCm * (RunEnd - RunStart + 1) + 0.5f * PreChurnPuddleRampCm);
				Basin.B = FMath::Max(Cell * 2.f, Steps[Low].HalfW);
				// The profile over the ellipse's radius r: a quarter cosine from the flat floor to its steepest, the wall limit, at r = 1
				// (rise RimCm), then on at that slope over the skirt to r = 1 + PreChurnPuddleSkirt (rise SkirtCm more).
				Basin.RimCm = WallTan * (2.f / PI) * FMath::Min(Basin.A, Basin.B);
				Basin.SkirtCm = WallTan * FMath::Min(Basin.A, Basin.B) * FMath::Max(0.f, PreChurnPuddleSkirt);
				// The floor: the run's depth under the table, raised until the skirt's top reaches the ground round its edge (24 points).
				const FVector2D Side(-Basin.Along.Y, Basin.Along.X);
				const float Out = 1.f + FMath::Max(0.f, PreChurnPuddleSkirt);
				float Edge = -1.e9f;
				for (int32 K = 0; K < 24; ++K)
				{
					const float Ang = 2.f * PI * K / 24.f;
					Edge = FMath::Max(Edge, SampleAt(Surface, Basin.C + Basin.Along * (Out * Basin.A * FMath::Cos(Ang)) + Side * (Out * Basin.B * FMath::Sin(Ang))));
				}
				Basin.FloorCm = FMath::Max(Table - Run, Edge - Basin.RimCm - Basin.SkirtCm);
				if (Basin.FloorCm < SampleAt(Surface, Basin.C) - 0.1f)
				{
					Basins.Add(Basin);
					PreChurnPuddleWet += Basin.FloorCm < Table ? 1 : 0;
				}
				RunStart = INDEX_NONE;
			}
		}
		// The basins' surface at a cell (the lowest of any that reach it; a large number where none does).
		TArray<float> Bowl;
		Bowl.Init(1.e9f, Cells2);
		for (const FBasin& Basin : Basins)
		{
			const float Out = 1.f + FMath::Max(0.f, PreChurnPuddleSkirt);
			const float Reach = Out * FMath::Max(Basin.A, Basin.B) + Cell;
			const FVector2D Lo = Basin.C - FVector2D(Reach, Reach) - Field.OriginCm;
			const FVector2D Hi = Basin.C + FVector2D(Reach, Reach) - Field.OriginCm;
			const int32 X0 = FMath::Clamp(FMath::FloorToInt32(Lo.X / Cell), 0, SX - 1);
			const int32 Y0 = FMath::Clamp(FMath::FloorToInt32(Lo.Y / Cell), 0, SY - 1);
			const int32 X1 = FMath::Clamp(FMath::CeilToInt32(Hi.X / Cell), 0, SX - 1);
			const int32 Y1 = FMath::Clamp(FMath::CeilToInt32(Hi.Y / Cell), 0, SY - 1);
			const FVector2D Across(-Basin.Along.Y, Basin.Along.X);
			for (int32 Y = Y0; Y <= Y1; ++Y)
			{
				for (int32 X = X0; X <= X1; ++X)
				{
					const int32 Index = Y * SX + X;
					const FVector2D D = Field.CellCentreCm(Index) - Basin.C;
					const float U = static_cast<float>(FVector2D::DotProduct(D, Basin.Along)) / Basin.A;
					const float V = static_cast<float>(FVector2D::DotProduct(D, Across)) / Basin.B;
					const float R = FMath::Sqrt(U * U + V * V);
					if (R < Out)
					{
						const float Z = R < 1.f ? Basin.RimCm * (1.f - FMath::Cos(0.5f * PI * R)) : Basin.RimCm + Basin.SkirtCm * (R - 1.f) / FMath::Max(Out - 1.f, 1e-3f);
						Bowl[Index] = FMath::Min(Bowl[Index], Basin.FloorCm + Z);
					}
				}
			}
		}
		// The lumps cleared where a basin cuts, then the floor read again and taken down to the basins.
		for (int32 Index = 0; Index < Cells2; ++Index)
		{
			if (Bowl[Index] < Surface[Index])
			{
				Field.LumpCm[Index] *= 1.f - FMath::SmoothStep(0.f, 1.f, Surface[Index] - Bowl[Index]);
			}
		}
		ReadSurface();
		TArray<uint8> InBasin;
		InBasin.Init(0, Cells2);
		for (int32 Index = 0; Index < Cells2; ++Index)
		{
			const float E = Surface[Index] - Bowl[Index];
			if (E > 0.f)
			{
				Field.HeightCm[Index] -= E;
				PreChurnPuddleDepthHiCm = FMath::Max(PreChurnPuddleDepthHiCm, E);
				InBasin[Index] = E > 0.1f ? 1 : 0;
			}
		}
		// The steepest cell a basin cut (central differences: its edge cells straddle the ground they meet), degrees.
		for (int32 Y = 1; Y + 1 < SY; ++Y)
		{
			for (int32 X = 1; X + 1 < SX; ++X)
			{
				const int32 Index = Y * SX + X;
				if (!InBasin[Index])
				{
					continue;
				}
				const float GX = (Field.SurfaceCm(Index + 1) - Field.SurfaceCm(Index - 1)) / (2.f * Cell);
				const float GY = (Field.SurfaceCm(Index + SX) - Field.SurfaceCm(Index - SX)) / (2.f * Cell);
				PreChurnPuddleWallDeg = FMath::Max(PreChurnPuddleWallDeg, FMath::RadiansToDegrees(FMath::Atan(FMath::Sqrt(GX * GX + GY * GY))));
			}
		}
		PreChurnPuddleBasins = Basins.Num();
	}
	PreChurnPuddleShare = PresentLength > 0.0 ? static_cast<float>(PuddleLength / PresentLength) : 0.f;
	// 4. The rim: everything faded to nothing over the outer PreChurnRimCm (the hummocked base the chunks read too), so the apron
	// matches; and the tread and the fresh sheen cleared (old ruts carry neither).
	const float RimCm = FMath::Max(1.f, PreChurnRimCm);
	float SurfaceHi = 0.f;
	float SurfaceLo = 0.f;
	for (int32 Y = 0; Y < SY; ++Y)
	{
		for (int32 X = 0; X < SX; ++X)
		{
			const int32 Index = Y * SX + X;
			const FVector2D C = Field.CellCentreCm(Index);
			const float Rim = static_cast<float>(FMath::Min(FMath::Min(C.X - Box.Min.X, Box.Max.X - C.X), FMath::Min(C.Y - Box.Min.Y, Box.Max.Y - C.Y)));
			const float Fade = FMath::SmoothStep(0.f, RimCm, Rim);
			Field.HeightCm[Index] *= Fade;
			Field.LumpCm[Index] *= Fade;
			PreChurnBaseCm[Index] *= Fade;
			Field.PhaseTurns[Index] = -1.f;
			Field.HeadingTurns[Index] = 0.f;
			Field.Fresh[Index] = 0.f;
			PreChurnHummockCm = FMath::Max(PreChurnHummockCm, FMath::Abs(PreChurnBaseCm[Index]));
			const float Surface = Field.SurfaceCm(Index);
			SurfaceHi = FMath::Max(SurfaceHi, Surface);
			SurfaceLo = FMath::Min(SurfaceLo, Surface);
			if (Rim < Cell)
			{
				PreChurnRimMaxCm = FMath::Max(PreChurnRimMaxCm, FMath::Abs(Surface));
			}
			PreChurnWaterCells += Surface < WaterTableCm ? 1 : 0;
		}
	}
	// GR1b: the steepest the old tracks' cells stand after the settle (central differences over a cell), degrees.
	PreChurnSlopeMaxDeg = 0.f;
	for (int32 Y = 1; Y + 1 < SY; ++Y)
	{
		for (int32 X = 1; X + 1 < SX; ++X)
		{
			const int32 Index = Y * SX + X;
			if (Cut[Index] <= 0.5f)
			{
				continue;
			}
			const float GX = (Field.SurfaceCm(Index + 1) - Field.SurfaceCm(Index - 1)) / (2.f * Cell);
			const float GY = (Field.SurfaceCm(Index + SX) - Field.SurfaceCm(Index - SX)) / (2.f * Cell);
			PreChurnSlopeMaxDeg = FMath::Max(PreChurnSlopeMaxDeg, FMath::RadiansToDegrees(FMath::Atan(FMath::Sqrt(GX * GX + GY * GY))));
		}
	}
	// GR1b's crease diagnosis (gt.Mud.PreChurnDebug), after the fade.
	const int32 Debug = CVarMudPreChurnDebug.GetValueOnGameThread();
	if (Debug & 1)
	{
		FMemory::Memzero(Field.Tracks.GetData(), Field.Tracks.Num());
	}
	if (Debug & 2)
	{
		TArray<float> Blur;
		for (int32 Pass = 0; Pass < 4; ++Pass)
		{
			Blur = Field.HeightCm;
			for (int32 Y = 1; Y + 1 < SY; ++Y)
			{
				for (int32 X = 1; X + 1 < SX; ++X)
				{
					float Sum = 0.f;
					for (int32 DY = -1; DY <= 1; ++DY)
					{
						for (int32 DX = -1; DX <= 1; ++DX)
						{
							Sum += Blur[(Y + DY) * SX + X + DX];
						}
					}
					Field.HeightCm[Y * SX + X] = Sum / 9.f;
				}
			}
		}
	}
	if (Debug & 4)
	{
		FMemory::Memzero(Field.LumpCm.GetData(), Field.LumpCm.Num() * sizeof(float));
	}
	if (Debug != 0)
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: pre-churn (GR1b) debug %d - tracks cleared %d, smoothed %d, lumps cleared %d"),
			SectionIndex, Debug, (Debug & 1) ? 1 : 0, (Debug & 2) ? 1 : 0, (Debug & 4) ? 1 : 0);
	}
	PreChurnSurfaceCm.SetNumUninitialized(Cells);
	for (int32 Index = 0; Index < Cells; ++Index)
	{
		PreChurnSurfaceCm[Index] = Field.SurfaceCm(Index);
	}
	// The render bounds carry the new reach (the mesh is built after this).
	DisplaceUpCm = FMath::Max(DisplaceUpCm, SurfaceHi + 15.f);
	DisplaceDownCm = FMath::Max(DisplaceDownCm, -SurfaceLo + 15.f);
	FString Shares;
	for (const float Share : PreChurnPresentShares)
	{
		Shares += FString::Printf(TEXT("%s%.0f %%"), Shares.IsEmpty() ? TEXT("") : TEXT(", "), 100.f * Share);
	}
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: pre-churn (GR1c) - scale %.2f: %d old rut pairs over %.1f m of route (present %s), depth asked %.1f-%.1f cm (x%.2f over S 0.6), filled to %.1f cm over %.0f %% of their length, puddles %.0f %% of the present length (cut up to %.1f cm into the settled floor), %d trough cells, steepest %.1f deg; %.0f s settled; hummocks +-%.1f-%.1f cm at %.0f / %.0f cm (most %.1f cm); surface %.1f..%.1f cm, rim %.2f cm at most, %d of %d cells under the %.1f cm water table; gt.Mud.PreChurn 1"),
		SectionIndex, Scale, PreChurnTracks, PreChurnBoxLineCm / 100.f, *Shares, PreChurnDepthLoCm, PreChurnDepthHiCm, PreChurnSoftDeepen, PreChurnFilledLoCm, 100.f * PreChurnFilledShare, 100.f * PreChurnPuddleShare, PreChurnPuddleDepthHiCm,
		PreChurnTrackCells, PreChurnSlopeMaxDeg, PreChurnSettleS, AmpLo, AmpHi, PreChurnHummockWaveCm, PreChurnHummockFineWaveCm, PreChurnHummockCm, SurfaceLo, SurfaceHi, PreChurnRimMaxCm, PreChurnWaterCells, Cells, WaterTableCm);
}

// ---- Mud roads MRD1 (docs/MUD_ROADS_PLAN.md MRD1 items 1 and 3): the braided pre-churn, its churn zones and debris -------------

namespace
{
	/** MRD1: a truncated power law on Lo..Hi with exponent A, from u in 0..1 (most samples near Lo, a long tail to Hi). */
	float RoadPowerLaw(float U, float Lo, float Hi, float A)
	{
		const float Ratio = FMath::Pow(Lo / FMath::Max(Hi, Lo + 0.01f), FMath::Max(A, 0.05f));
		return Lo / FMath::Pow(FMath::Max(1.e-4f, 1.f - U * (1.f - Ratio)), 1.f / FMath::Max(A, 0.05f));
	}

	/** MRD1: a repeatable 0..1 from a cell and a salt (the lip blocks, the wall steps). */
	float RoadHash01(int32 X, int32 Y, int32 Salt)
	{
		uint32 H = static_cast<uint32>(X) * 0x8DA6B343u ^ static_cast<uint32>(Y) * 0xD8163841u ^ static_cast<uint32>(Salt) * 0xCB1AB31Fu;
		H ^= H >> 13;
		H *= 0x5BD1E995u;
		H ^= H >> 15;
		return static_cast<float>(H & 0xFFFFFFu) / static_cast<float>(0x1000000);
	}

	/** MRD1: a sorted copy's percentile (0..1). */
	float RoadPercentile(TArray<float> Values, float P)
	{
		if (Values.Num() == 0)
		{
			return 0.f;
		}
		Values.Sort();
		return Values[FMath::Clamp(FMath::FloorToInt32(P * (Values.Num() - 1) + 0.5f), 0, Values.Num() - 1)];
	}

	/** MRD1: the depth histogram's bins (cm) as JSON counts, with the median, the 90th percentile and the share at 15 cm or more. */
	FString RoadHistogram(const TArray<float>& Values)
	{
		static const float Edges[] = { 0.f, 2.f, 3.f, 4.f, 5.f, 6.f, 8.f, 10.f, 12.f, 15.f, 20.f, 25.f, 1000.f };
		constexpr int32 Bins = UE_ARRAY_COUNT(Edges) - 1;
		int32 Counts[Bins] = {};
		int32 Deep = 0;
		for (const float V : Values)
		{
			for (int32 B = 0; B < Bins; ++B)
			{
				if (V >= Edges[B] && V < Edges[B + 1])
				{
					++Counts[B];
					break;
				}
			}
			Deep += V >= 15.f ? 1 : 0;
		}
		FString Out = TEXT("{\"bins_cm\":[0,2,3,4,5,6,8,10,12,15,20,25],\"counts\":[");
		for (int32 B = 0; B < Bins; ++B)
		{
			Out += FString::Printf(TEXT("%s%d"), B ? TEXT(",") : TEXT(""), Counts[B]);
		}
		Out += FString::Printf(TEXT("],\"samples\":%d,\"median_cm\":%.2f,\"p90_cm\":%.2f,\"share_15cm_plus\":%.3f}"), Values.Num(), RoadPercentile(Values, 0.5f),
			RoadPercentile(Values, 0.9f), Values.Num() ? static_cast<float>(Deep) / Values.Num() : 0.f);
		return Out;
	}
}

void AGTMudPatch::PreChurnBraided(FRandomStream& Random, float Scale)
{
	const int32 SX = Field.SizeX;
	const int32 SY = Field.SizeY;
	const int32 Cells = SX * SY;
	const float Cell = Field.CellCm;
	const FBox2D Box = Field.Bounds();
	const float RimCm = FMath::Max(1.f, PreChurnRimCm);
	RoadChurnZones.Reset();
	RoadDescribe.Reset();
	// The route line through the box, carried straight on past its ends (GR1c's).
	TArray<float> ArcCm;
	ArcCm.Add(0.f);
	for (int32 K = 1; K < RouteLineCm.Num(); ++K)
	{
		ArcCm.Add(ArcCm.Last() + static_cast<float>(FVector2D::Distance(RouteLineCm[K - 1], RouteLineCm[K])));
	}
	const float LineCm = ArcCm.Last();
	auto OnLine = [&](float S, FVector2D& OutDir)
	{
		const int32 Last = RouteLineCm.Num() - 1;
		if (S <= 0.f)
		{
			OutDir = (RouteLineCm[1] - RouteLineCm[0]).GetSafeNormal();
			return RouteLineCm[0] + OutDir * S;
		}
		if (S >= LineCm)
		{
			OutDir = (RouteLineCm[Last] - RouteLineCm[Last - 1]).GetSafeNormal();
			return RouteLineCm[Last] + OutDir * (S - LineCm);
		}
		int32 K = 1;
		while (K < Last && ArcCm[K] < S)
		{
			++K;
		}
		const float Span = FMath::Max(1.e-3f, ArcCm[K] - ArcCm[K - 1]);
		OutDir = (RouteLineCm[K] - RouteLineCm[K - 1]).GetSafeNormal();
		return FMath::Lerp(RouteLineCm[K - 1], RouteLineCm[K], (S - ArcCm[K - 1]) / Span);
	};
	const float StepCm = 25.f;
	const float ExtendCm = static_cast<float>(Box.GetSize().GetMax());
	float SA = TNumericLimits<float>::Max();
	float SB = -TNumericLimits<float>::Max();
	for (float S = -ExtendCm; S <= LineCm + ExtendCm; S += StepCm)
	{
		FVector2D Dir;
		if (Box.IsInside(OnLine(S, Dir)))
		{
			SA = FMath::Min(SA, S);
			SB = FMath::Max(SB, S);
		}
	}
	if (SB < SA)
	{
		SA = 0.f;
		SB = LineCm;
	}
	PreChurnBoxLineCm = SB - SA;
	// The visible stretch (inside the rim) carries the gates; the road band is the route line +- the road's half width (within the
	// box's cross half less the rim).
	const float VA = (SB - SA > 2.f * RimCm + 400.f) ? SA + RimCm : SA;
	const float VB = (SB - SA > 2.f * RimCm + 400.f) ? SB - RimCm : SB;
	const float CrossHalf = 0.5f * static_cast<float>(FMath::Min(Box.GetSize().X, Box.GetSize().Y));
	const float HalfRoad = FMath::Clamp(RoadHalfWidthCm > 0.f ? RoadHalfWidthCm : CrossHalf - RimCm, 100.f, FMath::Max(100.f, CrossHalf - 0.5f * RimCm));
	RoadTracks = FMath::Clamp(FMath::RoundToInt(2.f * HalfRoad / FMath::Max(10.f, RoadTrackSpacingCm)), FMath::Max(1, RoadTracksMin), FMath::Max(RoadTracksMin, RoadTracksMax));
	const int32 N = RoadTracks;
	const float FadeCm = 300.f;

	// 2. The layout: each track a path of two sines about its own lane, present over one stretch; redrawn until every 20 m window
	// (5 m apart) of the visible stretch has RoadCrossingsMin crossings (two present tracks' sides swapping) and a heading sd of
	// RoadHeadingSdMinDeg over its present samples, at most RoadLayoutTries times (else the best).
	struct FTrack { float Centre = 0.f; float Swing = 0.f; float Wave1 = 2000.f; float Wave2 = 4000.f; float Phase1 = 0.f; float Phase2 = 0.f; float A = 0.f; float B = 0.f; float Tyre = 28.f; };
	auto Lateral = [](const FTrack& T, float S) { return T.Centre + T.Swing * (0.65f * FMath::Sin(2.f * PI * S / T.Wave1 + T.Phase1) + 0.35f * FMath::Sin(2.f * PI * S / T.Wave2 + T.Phase2)); };
	auto Presence = [FadeCm](const FTrack& T, float S) { return FMath::Clamp(FMath::Min((S - T.A) / FadeCm + 0.5f, (T.B - S) / FadeCm + 0.5f), 0.f, 1.f); };
	const int32 Samples = FMath::Max(2, FMath::FloorToInt32((VB - VA) / StepCm) + 1);
	TArray<FTrack> Tracks;
	TArray<FVector2f> Crossings;   // (S, lateral) of every crossing in the chosen layout
	float BestScore = -1.f;
	RoadLayoutTry = 0;
	for (int32 Try = 0; Try < FMath::Max(1, RoadLayoutTries); ++Try)
	{
		TArray<FTrack> Layout;
		const float Lane = 2.f * HalfRoad / N;
		// MRD1b item 4: the stretches' places spread evenly along the road - track K's (shuffled) slot of N, jittered in it, places
		// the stretch's middle, so its start or its end (or both) lies inside the visible road at evenly spread points; never all at
		// the patch ends.
		TArray<int32> Slot;
		for (int32 K = 0; K < N; ++K)
		{
			Slot.Add(K);
		}
		for (int32 K = N - 1; K > 0; --K)
		{
			Slot.Swap(K, Random.RandHelper(K + 1));
		}
		for (int32 K = 0; K < N; ++K)
		{
			FTrack T;
			T.Centre = -HalfRoad + (K + 0.5f) * Lane + Random.FRandRange(-0.3f, 0.3f) * Lane;
			T.Swing = FMath::Clamp(static_cast<float>(Random.FRandRange(RoadSwingMinCm, RoadSwingMaxCm)), RoadSwingMinCm, FMath::Max(RoadSwingMinCm, HalfRoad + 60.f - FMath::Abs(T.Centre)));
			T.Wave1 = FMath::Max(100.f, static_cast<float>(Random.FRandRange(RoadWave1MinCm, RoadWave1MaxCm)));
			T.Wave2 = FMath::Max(100.f, static_cast<float>(Random.FRandRange(RoadWave2MinCm, RoadWave2MaxCm)));
			T.Phase1 = Random.FRandRange(0.f, 2.f * PI);
			T.Phase2 = Random.FRandRange(0.f, 2.f * PI);
			const float Share = FMath::Clamp(static_cast<float>(Random.FRandRange(RoadPresentMin, RoadPresentMax)), 0.05f, 1.f);
			const float Middle = VA + (Slot[K] + Random.FRandRange(0.15f, 0.85f)) / N * (VB - VA);
			T.A = Middle - 0.5f * Share * (VB - VA);
			T.B = T.A + Share * (VB - VA);
			T.Tyre = Random.FRandRange(25.f, 32.f);
			Layout.Add(T);
		}
		TArray<float> Lat;
		TArray<uint8> On;
		Lat.SetNumUninitialized(N * Samples);
		On.SetNumUninitialized(N * Samples);
		for (int32 K = 0; K < N; ++K)
		{
			for (int32 I = 0; I < Samples; ++I)
			{
				const float S = VA + I * StepCm;
				Lat[K * Samples + I] = Lateral(Layout[K], S);
				On[K * Samples + I] = Presence(Layout[K], S) >= 0.5f ? 1 : 0;
			}
		}
		TArray<float> CrossAt;
		CrossAt.Init(0.f, Samples);
		TArray<FVector2f> Found;
		for (int32 K = 0; K < N; ++K)
		{
			for (int32 J = K + 1; J < N; ++J)
			{
				for (int32 I = 1; I < Samples; ++I)
				{
					if (!(On[K * Samples + I] && On[J * Samples + I] && On[K * Samples + I - 1] && On[J * Samples + I - 1]))
					{
						continue;
					}
					const float D0 = Lat[K * Samples + I - 1] - Lat[J * Samples + I - 1];
					const float D1 = Lat[K * Samples + I] - Lat[J * Samples + I];
					if ((D0 < 0.f) != (D1 < 0.f))
					{
						CrossAt[I] += 1.f;
						Found.Add(FVector2f(VA + I * StepCm, 0.5f * (Lat[K * Samples + I] + Lat[J * Samples + I])));
					}
				}
			}
		}
		float MinCross = TNumericLimits<float>::Max();
		float MinSd = TNumericLimits<float>::Max();
		for (float W0 = VA; ; W0 += 500.f)
		{
			float W1 = W0 + 2000.f;
			if (W1 > VB)
			{
				if (W0 > VA)
				{
					break;
				}
				W1 = VB;
			}
			double Cross = 0.0;
			double Sum = 0.0;
			double Sum2 = 0.0;
			int32 Count = 0;
			for (int32 I = 1; I + 1 < Samples; ++I)
			{
				const float S = VA + I * StepCm;
				if (S < W0 || S >= W1)
				{
					continue;
				}
				Cross += CrossAt[I];
				for (int32 K = 0; K < N; ++K)
				{
					if (On[K * Samples + I])
					{
						const float Deg = FMath::RadiansToDegrees(FMath::Atan((Lat[K * Samples + I + 1] - Lat[K * Samples + I - 1]) / (2.f * StepCm)));
						Sum += Deg;
						Sum2 += Deg * Deg;
						++Count;
					}
				}
			}
			MinCross = FMath::Min(MinCross, static_cast<float>(Cross * 2000.0 / FMath::Max(1.f, W1 - W0)));
			const double Mean = Count ? Sum / Count : 0.0;
			MinSd = FMath::Min(MinSd, Count > 1 ? static_cast<float>(FMath::Sqrt(FMath::Max(0.0, Sum2 / Count - Mean * Mean))) : 0.f);
			if (W1 >= VB)
			{
				break;
			}
		}
		const float Score = FMath::Min(MinCross / FMath::Max(0.01f, RoadCrossingsMin), 1.f) + FMath::Min(MinSd / FMath::Max(0.01f, RoadHeadingSdMinDeg), 1.f);
		if (Score > BestScore)
		{
			BestScore = Score;
			Tracks = Layout;
			Crossings = Found;
			RoadLayoutTry = Try + 1;
			RoadCrossingsMinWindow = MinCross;
			RoadHeadingSdMinWindowDeg = MinSd;
			float Total = 0.f;
			for (const float C : CrossAt)
			{
				Total += C;
			}
			RoadCrossingsPer20m = Total * 2000.f / FMath::Max(1.f, VB - VA);
		}
		if (Score >= 2.f)
		{
			break;
		}
	}

	// The tracks into the cut, bank and per-cell bookkeeping grids: each a cosine trough D (0.5 + 0.5 cos(pi d / w)) across, w its width
	// at half depth (RoadWidthMin-Max x its tyre on knots 2-4 m apart, at least RoadWallPerDepth x D), D the power law's on knots
	// RoadDepthKnotMin-MaxCm apart x the presence (x PreChurnSoftDeepen where S is over 0.6, within RoadDepthMaxCm); a cosine bank
	// beside it of RoadBankReturn of what it took. Per cell: the deepest trough's track, its asked depth and shape; the lip ring of a
	// deep track (its depth, the way in, a segment number); the floor of a tread track (its along and heading).
	TArray<float> Cut;
	TArray<float> Bank;
	TArray<float> CutShape;
	TArray<float> CellDepth;     // the asked depth of the trough whose cut is deepest here
	TArray<float> CellShape;     // that trough's shape here (1 the floor, 0 the lip)
	TArray<float> LipDepth;      // the deepest deep track whose lip ring holds the cell (0 none)
	TArray<FVector2f> LipIn;     // the way in to that track's line
	TArray<int32> LipSeg;        // that lip's segment (about 3 cells along)
	TArray<float> TreadAlong;    // a tread track's along at the cell (-1 none)
	TArray<float> TreadHeading;  // turns
	TArray<float> TreadStrength;
	Cut.Init(0.f, Cells);
	Bank.Init(0.f, Cells);
	CutShape.Init(0.f, Cells);
	CellDepth.Init(0.f, Cells);
	CellShape.Init(0.f, Cells);
	LipDepth.Init(0.f, Cells);
	LipIn.Init(FVector2f::ZeroVector, Cells);
	LipSeg.Init(0, Cells);
	TreadAlong.Init(-1.f, Cells);
	TreadHeading.Init(0.f, Cells);
	TreadStrength.Init(0.f, Cells);
	const float BankReturn = FMath::Clamp(RoadBankReturn, 0.f, 1.f);
	const float DepthLo = FMath::Max(0.1f, RoadDepthMinCm);
	const float DepthHi = FMath::Max(DepthLo + 0.1f, RoadDepthMaxCm);
	auto Knots = [&Random](float K0, float K1, float MinGap, float MaxGap, TFunction<float()> Draw, TArray<FVector2f>& Out)
	{
		Out.Reset();
		for (float S = K0 - MaxGap; S <= K1 + MaxGap; S += Random.FRandRange(MinGap, MaxGap))
		{
			Out.Add(FVector2f(S, Draw()));
		}
		Out.Add(FVector2f(K1 + 2.f * MaxGap, Draw()));
	};
	auto KnotAt = [](const TArray<FVector2f>& K, float S)
	{
		int32 I = 1;
		while (I < K.Num() - 1 && K[I].X < S)
		{
			++I;
		}
		const float T = FMath::Clamp((S - K[I - 1].X) / FMath::Max(1.f, K[I].X - K[I - 1].X), 0.f, 1.f);
		return FMath::Lerp(K[I - 1].Y, K[I].Y, T * T * (3.f - 2.f * T));
	};
	// The freshest 2-3 tracks (the last drawn) carry the partial old tread: segments of 1.5-4 m over RoadTreadShare of their present
	// stretch, each faded in and out over 50 cm, its strength 0.4-1 (RoadTreadDepthMin-Max of RoadTreadDepthMaxCm).
	const int32 TreadTracks = FMath::Clamp(Random.RandRange(FMath::Min(RoadTreadTracksMin, RoadTreadTracksMax), FMath::Max(RoadTreadTracksMin, RoadTreadTracksMax)), 0, N);
	TArray<TArray<FVector4f>> TreadSegs;   // per track: (start, end, strength, 0)
	TreadSegs.SetNum(N);
	float TreadLength = 0.f;
	float TreadPresent = 0.f;
	for (int32 K = N - TreadTracks; K < N; ++K)
	{
		const FTrack& T = Tracks[K];
		const float Lo = FMath::Max(T.A, VA);
		const float Hi = FMath::Min(T.B, VB);
		if (Hi - Lo < 200.f)
		{
			continue;
		}
		TreadPresent += Hi - Lo;
		const float Want = FMath::Clamp(RoadTreadShare, 0.f, 1.f) * (Hi - Lo);
		float Have = 0.f;
		for (int32 Guard = 0; Guard < 12 && Have < Want - 50.f; ++Guard)
		{
			const float Len = FMath::Min(Want - Have, static_cast<float>(Random.FRandRange(150.f, 400.f)));
			const float Start = Random.FRandRange(Lo, FMath::Max(Lo, Hi - Len));
			bool bOverlap = false;
			for (const FVector4f& Seg : TreadSegs[K])
			{
				bOverlap |= Start < Seg.Y + 60.f && Start + Len > Seg.X - 60.f;
			}
			if (bOverlap)
			{
				continue;
			}
			const float Depth = Random.FRandRange(FMath::Min(RoadTreadDepthMinCm, RoadTreadDepthMaxCm), FMath::Max(RoadTreadDepthMinCm, RoadTreadDepthMaxCm));
			TreadSegs[K].Add(FVector4f(Start, Start + Len, Depth / FMath::Max(0.01f, FMath::Max(RoadTreadDepthMinCm, RoadTreadDepthMaxCm)), 0.f));
			Have += Len;
		}
		TreadLength += Have;
	}
	TArray<float> AskedDepths;
	TArray<FVector2f> DeepSpots;   // (S, lateral) where a knot asked 12 cm or more (the churn zones' other candidates)
	PreChurnDepthsCm.Reset();
	const float S0 = SA - 400.f;
	const float S1 = SB + 400.f;
	struct FStep { FVector2D P; FVector2D Dir; float S = 0.f; float D = 0.f; float Asked = 0.f; float W = 0.f; float Present = 0.f; bool bVisible = false; };
	TArray<TArray<FStep>> Lines;
	for (int32 K = 0; K < N; ++K)
	{
		const FTrack& T = Tracks[K];
		TArray<FVector2f> DepthKnots;
		TArray<FVector2f> WidthKnots;
		Knots(S0, S1, FMath::Max(10.f, RoadDepthKnotMinCm), FMath::Max(RoadDepthKnotMinCm, RoadDepthKnotMaxCm),
			[&]() { return RoadPowerLaw(Random.FRand(), DepthLo, DepthHi, RoadDepthAlpha); }, DepthKnots);
		Knots(S0, S1, 200.f, 400.f, [&]() { return Random.FRand(); }, WidthKnots);
		for (const FVector2f& Knot : DepthKnots)
		{
			if (Knot.Y >= 12.f && Knot.X >= VA && Knot.X <= VB && Presence(T, Knot.X) >= 0.5f)
			{
				DeepSpots.Add(FVector2f(Knot.X, Lateral(T, Knot.X)));
			}
		}
		TArray<FStep>& Line = Lines.AddDefaulted_GetRef();
		for (float S = S0; S <= S1; S += StepCm)
		{
			FStep& L = Line.AddDefaulted_GetRef();
			FVector2D Dir;
			const FVector2D OnRoute = OnLine(S, Dir);
			const FVector2D Left(-Dir.Y, Dir.X);
			// The track's own direction: the route's turned by the lateral's slope.
			const float Slope = (Lateral(T, S + 0.5f * StepCm) - Lateral(T, S - 0.5f * StepCm)) / StepCm;
			L.Dir = (Dir + Left * Slope).GetSafeNormal();
			L.P = OnRoute + Left * Lateral(T, S);
			L.S = S;
			L.Present = Presence(T, S);
			L.Asked = KnotAt(DepthKnots, S) * Scale;
			if (HasSoftSpots() && SoftnessAt(L.P) > 0.6f)
			{
				L.Asked = FMath::Min(DepthHi * Scale, L.Asked * FMath::Max(1.f, PreChurnSoftDeepen));
			}
			L.D = L.Asked * L.Present;
			L.W = FMath::Max(T.Tyre * FMath::Lerp(RoadWidthMin, FMath::Max(RoadWidthMin, RoadWidthMax), KnotAt(WidthKnots, S)), FMath::Max(0.5f, RoadWallPerDepth) * L.D);
			L.bVisible = S >= VA && S <= VB && Box.IsInside(L.P);
			if (L.bVisible && L.Present >= 0.5f)
			{
				AskedDepths.Add(L.Asked);
				PreChurnDepthsCm.Add(L.Asked);
			}
		}
		// Into the grids, segment by segment.
		for (int32 I = 1; I < Line.Num(); ++I)
		{
			const FStep& A0 = Line[I - 1];
			const FStep& A1 = Line[I];
			if (A0.D <= 0.01f && A1.D <= 0.01f)
			{
				continue;
			}
			if (!Box.ExpandBy(200.f).IsInside(A0.P) && !Box.ExpandBy(200.f).IsInside(A1.P))
			{
				continue;
			}
			const float Reach = 2.2f * FMath::Max(A0.W, A1.W) + Cell;
			const FVector2D Lo = FVector2D::Min(A0.P, A1.P) - FVector2D(Reach, Reach) - Field.OriginCm;
			const FVector2D Hi = FVector2D::Max(A0.P, A1.P) + FVector2D(Reach, Reach) - Field.OriginCm;
			const int32 X0 = FMath::Clamp(FMath::FloorToInt32(Lo.X / Cell), 0, SX - 1);
			const int32 Y0 = FMath::Clamp(FMath::FloorToInt32(Lo.Y / Cell), 0, SY - 1);
			const int32 X1 = FMath::Clamp(FMath::CeilToInt32(Hi.X / Cell), 0, SX - 1);
			const int32 Y1 = FMath::Clamp(FMath::CeilToInt32(Hi.Y / Cell), 0, SY - 1);
			const FVector2D AB = A1.P - A0.P;
			const double Len2 = FMath::Max(1.e-6, AB.SizeSquared());
			const bool bTread = TreadSegs[K].Num() > 0;
			for (int32 Y = Y0; Y <= Y1; ++Y)
			{
				for (int32 X = X0; X <= X1; ++X)
				{
					const int32 Index = Y * SX + X;
					const FVector2D C = Field.CellCentreCm(Index);
					const float Tt = static_cast<float>(FMath::Clamp(FVector2D::DotProduct(C - A0.P, AB) / Len2, 0.0, 1.0));
					const FVector2D Near = A0.P + AB * Tt;
					const float Dist = static_cast<float>(FVector2D::Distance(C, Near));
					const float DT = FMath::Lerp(A0.D, A1.D, Tt);
					const float W = FMath::Lerp(A0.W, A1.W, Tt);
					const float AskedT = FMath::Lerp(A0.Asked, A1.Asked, Tt) * FMath::Lerp(A0.Present, A1.Present, Tt);
					const float Along = FMath::Lerp(A0.S, A1.S, Tt);
					if (Dist < W)
					{
						const float Shape = 0.5f + 0.5f * FMath::Cos(PI * Dist / W);
						if (DT * Shape > Cut[Index])
						{
							Cut[Index] = DT * Shape;
							CellDepth[Index] = AskedT;
							CellShape[Index] = Shape;
						}
						CutShape[Index] = FMath::Max(CutShape[Index], Shape * FMath::Lerp(A0.Present, A1.Present, Tt));
						// The tread on the floor of a tread track (inside 0.55 of its half-depth width), in a segment.
						if (bTread && Dist < 0.55f * W && DT * Shape >= Cut[Index] - 0.01f)
						{
							float Strength = 0.f;
							for (const FVector4f& Seg : TreadSegs[K])
							{
								Strength = FMath::Max(Strength, Seg.Z * FMath::SmoothStep(Seg.X, Seg.X + 50.f, Along) * (1.f - FMath::SmoothStep(Seg.Y - 50.f, Seg.Y, Along)));
							}
							if (Strength > 0.02f)
							{
								const FVector2D Dir = FMath::Lerp(A0.Dir, A1.Dir, static_cast<double>(Tt)).GetSafeNormal();
								TreadAlong[Index] = Along + static_cast<float>(FVector2D::DotProduct(C - Near, Dir));
								float Turns = FMath::Atan2(static_cast<float>(Dir.Y), static_cast<float>(Dir.X)) / (2.f * PI);
								TreadHeading[Index] = Turns - FMath::FloorToFloat(Turns);
								TreadStrength[Index] = Strength;
							}
						}
					}
					else if (Dist < 2.2f * W)
					{
						const float U = (Dist - W) / (1.2f * W);
						Bank[Index] = FMath::Max(Bank[Index], BankReturn * DT / 1.2f * 0.5f * (1.f - FMath::Cos(2.f * PI * U)));
					}
					// The lip ring of a deep track (0.7-1.35 w out): its depth, the way in, a segment of about 3 cells along.
					if (AskedT >= RoadWallDeepCm && Dist > 0.7f * W && Dist < 1.35f * W && AskedT > LipDepth[Index] && Dist > 1.f)
					{
						LipDepth[Index] = AskedT;
						LipIn[Index] = FVector2f((Near - C) / Dist);
						LipSeg[Index] = K * 100003 + FMath::FloorToInt32(Along / (3.f * Cell));
					}
				}
			}
		}
	}
	// Into the field: the cut below the hummocked ground, the bank where no trough is; the tracks factor at half the trough's shape x
	// the presence; LM2's lumps re-seeded at RoadLumpShare, heavier on the ridges (the bank x 1.5, the cut x 0.5).
	PreChurnTrackCells = 0;
	TArray<uint8> Edited;
	Edited.Init(0, Cells);
	for (int32 Index = 0; Index < Cells; ++Index)
	{
		const float Delta = Bank[Index] * (1.f - FMath::SmoothStep(0.f, 2.f, Cut[Index])) - Cut[Index];
		if (Delta == 0.f)
		{
			continue;
		}
		Edited[Index] = 1;
		Field.HeightCm[Index] += Delta;
		Field.Tracks[Index] = FMath::Max(Field.Tracks[Index], static_cast<uint8>(FMath::Clamp(FMath::RoundToInt(127.f * CutShape[Index]), 0, 255)));
		const float Lump = FMath::Min(FMath::Max(0.f, Field.LumpMaxCm), FMath::Max(0.f, RoadLumpShare) * (1.5f * Bank[Index] + 0.5f * Cut[Index]) * Field.LumpWeightAt(Index));
		Field.LumpCm[Index] = FMath::Max(Field.LumpCm[Index], Lump);
		PreChurnTrackCells += Cut[Index] > 0.5f ? 1 : 0;
	}
	Field.WakeEdited(Edited);
	// 3. The field's own settle (PreChurnSettleS), so the tracks read old and slumped.
	const float Dt = 1.f / 30.f;
	for (float T = 0.f; T < PreChurnSettleS - 1.e-4f; T += Dt)
	{
		Field.AdvanceClock(Dt);
		Field.Settle(Dt);
	}
	// The settled depth along the tracks (the hummocked ground less the surface under each present visible step).
	TArray<float> SettledDepths;
	auto SurfaceAt = [&](const FVector2D& P)
	{
		const int32 Index = Field.CellIndexAt(P);
		return Index == INDEX_NONE ? 0.f : Field.SurfaceCm(Index);
	};
	for (const TArray<FStep>& Line : Lines)
	{
		for (const FStep& L : Line)
		{
			const int32 Index = Field.CellIndexAt(L.P);
			if (L.bVisible && L.Present >= 0.5f && Index != INDEX_NONE)
			{
				SettledDepths.Add(PreChurnBaseCm[Index] - Field.SurfaceCm(Index));
			}
		}
	}
	// 3a. The deep tracks' walls (asked over RoadWallDeepCm): the trough's cut depth terraced in steps of RoadStepMin-MaxCm (a step
	// height per block of 2 x 2 cells) with a short riser; then the lip ring's clump blocks - one a cell, RoadBlockMin-MaxCm high, a
	// quarter of the cells left out - into the lumps, and RoadOverhangShare of the lip segments leaning in (RoadOverhangMin-MaxCm of
	// the block carried onto the next cell in). Not woken: no relax takes them back before a wheel works them.
	int32 WallCells = 0;
	int32 BlockCells = 0;
	int32 LeanCells = 0;
	for (int32 Y = 1; Y + 1 < SY; ++Y)
	{
		for (int32 X = 1; X + 1 < SX; ++X)
		{
			const int32 Index = Y * SX + X;
			const float Deep = FMath::SmoothStep(RoadWallDeepCm, RoadWallDeepCm + 3.f, CellDepth[Index]);
			if (Deep > 0.f && CellShape[Index] > 0.06f && CellShape[Index] < 0.9f)
			{
				const float C = CellShape[Index] * CellDepth[Index];   // the trough's cut below its lip here, as asked
				const float Step = FMath::Lerp(RoadStepMinCm, FMath::Max(RoadStepMinCm, RoadStepMaxCm), RoadHash01(X / 2, Y / 2, 811 + SectionIndex));
				const float Tq = C / FMath::Max(0.5f, Step);
				const float Terraced = Step * (FMath::FloorToFloat(Tq) + FMath::SmoothStep(0.55f, 1.f, Tq - FMath::FloorToFloat(Tq)));
				Field.HeightCm[Index] += Deep * (C - Terraced);
				++WallCells;
			}
			if (LipDepth[Index] > 0.f)
			{
				const float H = RoadHash01(X, Y, 977 + SectionIndex);
				if (H < 0.75f)
				{
					const float Block = FMath::Lerp(RoadBlockMinCm, FMath::Max(RoadBlockMinCm, RoadBlockMaxCm), RoadHash01(X, Y, 1291 + SectionIndex)) * FMath::SmoothStep(RoadWallDeepCm, RoadWallDeepCm + 3.f, LipDepth[Index]);
					Field.LumpCm[Index] += Block;
					++BlockCells;
					const int32 Seg = LipSeg[Index];
					if (RoadHash01(Seg, Seg >> 7, 1543 + SectionIndex) < RoadOverhangShare)
					{
						const FVector2f In = LipIn[Index];
						const int32 IX = X + FMath::RoundToInt32(In.X);
						const int32 IY = Y + FMath::RoundToInt32(In.Y);
						if (IX >= 0 && IX < SX && IY >= 0 && IY < SY && (IX != X || IY != Y))
						{
							const float Lean = FMath::Lerp(RoadOverhangMinCm, FMath::Max(RoadOverhangMinCm, RoadOverhangMaxCm), RoadHash01(X, Y, 1777 + SectionIndex));
							// The block's top carried in: the inner cell raised toward the block's top by the lean's share of a cell.
							const int32 Inner = IY * SX + IX;
							const float Top = Field.SurfaceCm(Index);
							const float Rise = FMath::Max(0.f, Top - Field.SurfaceCm(Inner)) * FMath::Clamp(Lean / Cell, 0.f, 1.f);
							Field.LumpCm[Inner] += Rise;
							++LeanCells;
						}
					}
				}
			}
		}
	}
	// The road band: the cells within HalfRoad of the route line, inside the rim (the gates' area).
	TArray<uint8> Band;
	Band.Init(0, Cells);
	int32 BandCells = 0;
	for (int32 Index = 0; Index < Cells; ++Index)
	{
		const FVector2D C = Field.CellCentreCm(Index);
		const float Rim = static_cast<float>(FMath::Min(FMath::Min(C.X - Box.Min.X, Box.Max.X - C.X), FMath::Min(C.Y - Box.Min.Y, Box.Max.Y - C.Y)));
		if (Rim >= RimCm && DistanceToRouteCm(C) <= HalfRoad)
		{
			Band[Index] = 1;
			++BandCells;
		}
	}
	// 3b. The churn zones: RoadChurnPer40mMin-Max per 40 m of the visible stretch (at least one), at crossings or deep spots inside the
	// road, at least 8 m apart; each RoadChurnRadiusMin-MaxCm, its clod field falling off over RoadClodFalloffMin-MaxCm. The ground
	// there churned: +-5 cm of a 35 cm value noise and lumps up to 5 cm by the field's dome weights, the tracks factor worked.
	{
		const float Visible = VB - VA;
		const int32 Zones = FMath::Max(Visible >= 1500.f ? 1 : 0, FMath::RoundToInt(Visible / 4000.f * Random.FRandRange(RoadChurnPer40mMin, FMath::Max(RoadChurnPer40mMin, RoadChurnPer40mMax))));
		TArray<FVector2f> Candidates = Crossings;
		Candidates.Append(DeepSpots);
		for (int32 Guard = 0; Guard < 200 && RoadChurnZones.Num() < Zones && Candidates.Num() > 0; ++Guard)
		{
			const int32 Pick = Random.RandHelper(Candidates.Num());
			const FVector2f Cand = Candidates[Pick];
			Candidates.RemoveAtSwap(Pick);
			if (FMath::Abs(Cand.Y) > HalfRoad - 50.f || Cand.X < VA + 300.f || Cand.X > VB - 300.f)
			{
				continue;
			}
			FVector2D Dir;
			const FVector2D P = OnLine(Cand.X, Dir) + FVector2D(-Dir.Y, Dir.X) * Cand.Y;
			bool bNear = false;
			for (const FVector4f& Z : RoadChurnZones)
			{
				bNear |= FVector2D::Distance(P, FVector2D(Z.X, Z.Y)) < 800.f;
			}
			if (!bNear && Box.IsInside(P))
			{
				RoadChurnZones.Add(FVector4f(static_cast<float>(P.X), static_cast<float>(P.Y), Random.FRandRange(RoadChurnRadiusMinCm, FMath::Max(RoadChurnRadiusMinCm, RoadChurnRadiusMaxCm)),
					Random.FRandRange(RoadClodFalloffMinCm, FMath::Max(RoadClodFalloffMinCm, RoadClodFalloffMaxCm))));
			}
		}
		const float NoiseCells = FMath::Max(1.f, 35.f / Cell);
		for (const FVector4f& Z : RoadChurnZones)
		{
			const float Reach = 1.3f * Z.Z;
			const int32 X0 = FMath::Clamp(FMath::FloorToInt32((Z.X - Reach - Field.OriginCm.X) / Cell), 0, SX - 1);
			const int32 X1 = FMath::Clamp(FMath::CeilToInt32((Z.X + Reach - Field.OriginCm.X) / Cell), 0, SX - 1);
			const int32 Y0 = FMath::Clamp(FMath::FloorToInt32((Z.Y - Reach - Field.OriginCm.Y) / Cell), 0, SY - 1);
			const int32 Y1 = FMath::Clamp(FMath::CeilToInt32((Z.Y + Reach - Field.OriginCm.Y) / Cell), 0, SY - 1);
			for (int32 Y = Y0; Y <= Y1; ++Y)
			{
				for (int32 X = X0; X <= X1; ++X)
				{
					const int32 Index = Y * SX + X;
					const float D = static_cast<float>(FVector2D::Distance(Field.CellCentreCm(Index), FVector2D(Z.X, Z.Y)));
					const float K = 1.f - FMath::SmoothStep(0.7f * Z.Z, Reach, D);
					if (K <= 0.f)
					{
						continue;
					}
					Field.HeightCm[Index] += K * 5.f * FMath::Clamp(2.f * Field.CellNoise(X, Y, NoiseCells, 3301 + SectionIndex), -1.f, 1.f);
					Field.LumpCm[Index] = FMath::Max(Field.LumpCm[Index], K * FMath::Min(Field.LumpMaxCm, 5.f * Field.LumpWeightAt(Index)));
					Field.Tracks[Index] = FMath::Max(Field.Tracks[Index], static_cast<uint8>(FMath::RoundToInt(160.f * K)));
				}
			}
		}
	}
	// 3c. MRD1b item 2 / MRD1c item 2, the pools: where the patch has a water table (at or above -PreChurnPuddleTableMaxCm), a present
	// track's floor goes down along low runs to RoadPuddleBelowMin-MaxCm under the table. MRD1c: a run is RoadPoolMin-MaxCm long by a
	// power law (RoadPoolLenPower: mostly short, a long tail), its ends tapering over RoadPoolTaperMin-MaxCm each (the floor rising
	// back and the flat narrowing to nothing), its outline wobbled (the flat's width by +-RoadPoolWobble of a 0.6-1.2 m value noise
	// along it, its centre +-0.15 of the half width across, every cell's distance by +-0.18 of a 40 cm cell noise); the gap it keeps
	// clear on each side RoadPoolGapMin-MaxCm by the same power law; RoadPoolJoinShare of the runs that meet another track's trough
	// (within 1 m of their ends) carry on across it for 1-2.5 m on that track, so the pools join. Runs go down lowest first across
	// all the tracks until the water covers the drawn RoadPuddleShareMin-Max of the road band; lumps go first, then the height. Then
	// every cell under the table outside a pool is lifted to it (+0.3 cm), so no track holds stray small pools.
	const float Table = WaterTableCm;
	RoadPuddleBasins = 0;
	RoadPuddleTarget = FMath::Clamp(static_cast<float>(Random.FRandRange(RoadPuddleShareMin, FMath::Max(RoadPuddleShareMin, RoadPuddleShareMax))), 0.f, 1.f);
	int32 WetBand = 0;
	int32 Lifted = 0;
	TArray<uint8> Pool;
	Pool.Init(0, Cells);
	TArray<FVector2f> PoolRuns;              // per run: (its length, cm; its floor under the table, cm)
	TArray<TArray<FVector2f>> OwnRuns;       // per track: its own runs' extents along the line (S from, S to), cm
	OwnRuns.SetNum(Lines.Num());
	int32 RunsMeeting = 0;
	int32 RunsJoined = 0;
	const float PowerK = FMath::Max(0.1f, RoadPoolLenPower);
	auto PowerDraw = [&](float Lo, float Hi) { return Lo + (FMath::Max(Lo, Hi) - Lo) * FMath::Pow(Random.FRand(), PowerK); };
	// One run onto a line's steps [First, First + Len): the level and the flat's width tapered at both ends, the outline wobbled.
	auto ApplyRun = [&](int32 K, int32 First, int32 Len, int32 TaperA, int32 TaperB, float Target, int32 Seed)
	{
		const TArray<FStep>& Line = Lines[K];
		const float Flat0 = FMath::Clamp(RoadPoolFlat, 0.1f, 0.95f);
		const float WaveSteps = Random.FRandRange(60.f, 120.f) / StepCm;
		const float Wobble = FMath::Clamp(RoadPoolWobble, 0.f, 0.9f);
		auto Noise1 = [Seed](float T, int32 Salt)
		{
			const int32 I = FMath::FloorToInt32(T);
			const float F = T - I;
			return FMath::Lerp(RoadHash01(I, Seed, Salt), RoadHash01(I + 1, Seed, Salt), F * F * (3.f - 2.f * F)) * 2.f - 1.f;
		};
		for (int32 I = FMath::Max(0, First); I < FMath::Min(Line.Num(), First + Len); ++I)
		{
			const FStep& L = Line[I];
			const int32 J = I - First;
			const float Ta = TaperA > 0 ? FMath::SmoothStep(0.f, 1.f, (J + 0.5f) / TaperA) : 1.f;
			const float Tb = TaperB > 0 ? FMath::SmoothStep(0.f, 1.f, (Len - J - 0.5f) / TaperB) : 1.f;
			const float Taper = FMath::Min(Ta, Tb);
			const float Floor = SurfaceAt(L.P);
			const float Level = FMath::Min(Floor, FMath::Lerp(Floor, Target, Taper));
			const float FlatHere = Flat0 * Taper * (1.f + Wobble * Noise1(I / WaveSteps, 211));
			if (Level >= Floor - 0.01f || FlatHere <= 0.02f)
			{
				continue;
			}
			const FVector2D Left(-L.Dir.Y, L.Dir.X);
			const FVector2D Centre = L.P + Left * (0.15f * L.W * Noise1(I / WaveSteps + 17.f, 347));
			const float Reach = 1.3f * L.W + Cell;
			const int32 X0 = FMath::Clamp(FMath::FloorToInt32((Centre.X - Reach - Field.OriginCm.X) / Cell), 0, SX - 1);
			const int32 X1 = FMath::Clamp(FMath::CeilToInt32((Centre.X + Reach - Field.OriginCm.X) / Cell), 0, SX - 1);
			const int32 Y0 = FMath::Clamp(FMath::FloorToInt32((Centre.Y - Reach - Field.OriginCm.Y) / Cell), 0, SY - 1);
			const int32 Y1 = FMath::Clamp(FMath::CeilToInt32((Centre.Y + Reach - Field.OriginCm.Y) / Cell), 0, SY - 1);
			for (int32 Y = Y0; Y <= Y1; ++Y)
			{
				for (int32 X = X0; X <= X1; ++X)
				{
					const int32 Index = Y * SX + X;
					const float U = static_cast<float>(FVector2D::Distance(Field.CellCentreCm(Index), Centre)) / FMath::Max(1.f, L.W)
						* (1.f + 0.18f * FMath::Clamp(2.f * Field.CellNoise(X, Y, FMath::Max(1.f, 40.f / Cell), 2903 + SectionIndex), -1.f, 1.f));
					if (U >= 1.05f)
					{
						continue;
					}
					const float Bowl = Level + 40.f * FMath::SmoothStep(FMath::Min(FlatHere, 1.f), 1.05f, U);
					const float E = Field.SurfaceCm(Index) - Bowl;
					if (E <= 0.f)
					{
						continue;
					}
					const float FromLump = FMath::Min(Field.LumpCm[Index], E);
					Field.LumpCm[Index] -= FromLump;
					Field.HeightCm[Index] -= E - FromLump;
					Pool[Index] = Field.SurfaceCm(Index) < Table ? 1 : Pool[Index];
				}
			}
		}
	};
	if (Table <= 0.f && Table >= -FMath::Max(0.f, PreChurnPuddleTableMaxCm) && BandCells > 0)
	{
		auto CountWet = [&]()
		{
			int32 Wet = 0;
			for (int32 Index = 0; Index < Cells; ++Index)
			{
				Wet += (Band[Index] && Field.SurfaceCm(Index) < Table) ? 1 : 0;
			}
			return Wet;
		};
		// Per track, the steps a run may use (visible, present, in the band) and the ones its runs (with their gaps) have taken.
		TArray<TArray<uint8>> Usable;
		TArray<TArray<uint8>> Taken;
		for (const TArray<FStep>& Line : Lines)
		{
			TArray<uint8>& U = Usable.AddDefaulted_GetRef();
			U.Init(0, Line.Num());
			Taken.AddDefaulted_GetRef().Init(0, Line.Num());
			for (int32 I = 0; I < Line.Num(); ++I)
			{
				const int32 Index = Field.CellIndexAt(Line[I].P);
				U[I] = (Line[I].bVisible && Line[I].Present >= 0.5f && Index != INDEX_NONE && Band[Index]) ? 1 : 0;
			}
		}
		WetBand = CountWet();
		for (int32 Guard = 0; Guard < 400 && static_cast<float>(WetBand) / BandCells < RoadPuddleTarget; ++Guard)
		{
			// Each track's lowest free window of a length drawn for it this round; the lowest of those goes down.
			int32 BestLine = INDEX_NONE;
			int32 BestStart = 0;
			int32 BestLen = 0;
			float BestMean = TNumericLimits<float>::Max();
			TArray<int32> Lens;
			for (int32 K = 0; K < Lines.Num(); ++K)
			{
				Lens.Add(FMath::Max(4, FMath::RoundToInt(PowerDraw(RoadPoolMinCm, RoadPoolMaxCm) / StepCm)));
			}
			for (int32 K = 0; K < Lines.Num(); ++K)
			{
				const TArray<FStep>& Line = Lines[K];
				const int32 Len = Lens[K];
				for (int32 Start = 0; Start + Len <= Line.Num(); ++Start)
				{
					double Sum = 0.0;
					bool bOk = true;
					for (int32 I = Start; I < Start + Len && bOk; ++I)
					{
						bOk = Usable[K][I] && !Taken[K][I];
						Sum += bOk ? SurfaceAt(Line[I].P) : 0.f;
					}
					if (bOk && Sum / Len < BestMean)
					{
						BestMean = static_cast<float>(Sum / Len);
						BestLine = K;
						BestStart = Start;
						BestLen = Len;
					}
				}
			}
			if (BestLine == INDEX_NONE)
			{
				break;
			}
			const TArray<FStep>& Line = Lines[BestLine];
			const int32 GapA = FMath::Max(1, FMath::RoundToInt(PowerDraw(RoadPoolGapMinCm, RoadPoolGapMaxCm) / StepCm));
			const int32 GapB = FMath::Max(1, FMath::RoundToInt(PowerDraw(RoadPoolGapMinCm, RoadPoolGapMaxCm) / StepCm));
			for (int32 I = FMath::Max(0, BestStart - GapA); I < FMath::Min(Line.Num(), BestStart + BestLen + GapB); ++I)
			{
				Taken[BestLine][I] = 1;
			}
			const int32 TaperCap = FMath::Max(1, FMath::RoundToInt(0.4f * BestLen));
			const int32 TaperA = FMath::Min(TaperCap, FMath::RoundToInt(Random.FRandRange(RoadPoolTaperMinCm, FMath::Max(RoadPoolTaperMinCm, RoadPoolTaperMaxCm)) / StepCm));
			const int32 TaperB = FMath::Min(TaperCap, FMath::RoundToInt(Random.FRandRange(RoadPoolTaperMinCm, FMath::Max(RoadPoolTaperMinCm, RoadPoolTaperMaxCm)) / StepCm));
			const float Below = Random.FRandRange(FMath::Min(RoadPuddleBelowMinCm, RoadPuddleBelowMaxCm), FMath::Max(RoadPuddleBelowMinCm, RoadPuddleBelowMaxCm));
			const float Target = Table - Below;
			const int32 RunSeed = 7919 * (RoadPuddleBasins + 1) + 31 * BestLine + SectionIndex;
			ApplyRun(BestLine, BestStart, BestLen, TaperA, TaperB, Target, RunSeed);
			OwnRuns[BestLine].Add(FVector2f(Line[BestStart].S, Line[BestStart + BestLen - 1].S + StepCm));
			PoolRuns.Add(FVector2f(BestLen * StepCm, Below));
			++RoadPuddleBasins;
			// MRD1c: a run meeting another track's trough within 1 m of its ends carries on across it (RoadPoolJoinShare of them).
			const int32 Near = FMath::RoundToInt(100.f / StepCm);
			int32 MeetLine = INDEX_NONE;
			int32 MeetStep = INDEX_NONE;
			for (int32 I = FMath::Max(0, BestStart - Near); I < FMath::Min(Line.Num(), BestStart + BestLen + Near) && MeetLine == INDEX_NONE; ++I)
			{
				for (int32 J = 0; J < Lines.Num(); ++J)
				{
					if (J != BestLine && Lines[J].IsValidIndex(I) && Usable[J][I]
						&& FVector2D::Distance(Lines[J][I].P, Line[I].P) < 0.6f * (Lines[J][I].W + Line[I].W))
					{
						MeetLine = J;
						MeetStep = I;
						break;
					}
				}
			}
			if (MeetLine != INDEX_NONE)
			{
				++RunsMeeting;
				if (Random.FRand() < RoadPoolJoinShare)
				{
					const int32 JoinLen = FMath::Max(4, FMath::RoundToInt(Random.FRandRange(100.f, 250.f) / StepCm));
					const int32 JoinTaper = FMath::Max(1, FMath::RoundToInt(Random.FRandRange(50.f, 100.f) / StepCm));
					ApplyRun(MeetLine, MeetStep - JoinLen / 2, JoinLen, JoinTaper, JoinTaper, Target, RunSeed + 101);
					++RunsJoined;
				}
			}
			WetBand = CountWet();
		}
		// No stray pools: under the table outside a run's pool, lifted to it.
		for (int32 Index = 0; Index < Cells; ++Index)
		{
			const float Surface = Field.SurfaceCm(Index);
			if (!Pool[Index] && Surface < Table)
			{
				Field.HeightCm[Index] += Table + 0.3f - Surface;
				++Lifted;
			}
		}
	}
	// MRD1c item 3: the pools per 5 m of each track counted from its OWN runs (their extents along its line): the most that reach
	// into any 5 m window, sliding 25 cm. And, for the record, MRD1b's count (every wet stretch along the line, the other tracks'
	// pools it crosses included). The runs' lengths and the gaps between a track's runs, with their CVs.
	RoadPoolsPer5mMax = 0;
	int32 LinePools5m = 0;
	TArray<float> RunLengths;
	TArray<float> Gaps;
	for (int32 K = 0; K < Lines.Num(); ++K)
	{
		TArray<FVector2f>& Runs = OwnRuns[K];
		Runs.Sort([](const FVector2f& A, const FVector2f& B) { return A.X < B.X; });
		for (int32 R = 0; R < Runs.Num(); ++R)
		{
			RunLengths.Add(Runs[R].Y - Runs[R].X);
			if (R > 0)
			{
				Gaps.Add(Runs[R].X - Runs[R - 1].Y);
			}
		}
		if (Lines[K].Num() > 0)
		{
			for (float W0 = Lines[K][0].S; W0 <= Lines[K].Last().S; W0 += StepCm)
			{
				int32 N5 = 0;
				for (const FVector2f& Run : Runs)
				{
					N5 += (Run.Y > W0 && Run.X < W0 + 500.f) ? 1 : 0;
				}
				RoadPoolsPer5mMax = FMath::Max(RoadPoolsPer5mMax, N5);
			}
		}
		const TArray<FStep>& Line = Lines[K];
		const int32 Window = FMath::Max(1, FMath::RoundToInt(500.f / StepCm));
		TArray<int8> Wet;
		Wet.Init(-1, Line.Num());
		for (int32 I = 0; I < Line.Num(); ++I)
		{
			const int32 Index = Field.CellIndexAt(Line[I].P);
			if (Line[I].bVisible && Line[I].Present >= 0.5f && Index != INDEX_NONE)
			{
				Wet[I] = Field.SurfaceCm(Index) < Table ? 1 : 0;
			}
		}
		for (int32 W0 = 0; W0 + Window <= Line.Num(); ++W0)
		{
			int32 N5 = 0;
			for (int32 I = W0; I < W0 + Window; ++I)
			{
				N5 += (Wet[I] == 1 && (I == W0 || Wet[I - 1] != 1)) ? 1 : 0;
			}
			LinePools5m = FMath::Max(LinePools5m, N5);
		}
	}
	auto Cv = [](const TArray<float>& V)
	{
		if (V.Num() < 2)
		{
			return 0.f;
		}
		double S = 0.0;
		double S2 = 0.0;
		for (const float X : V)
		{
			S += X;
			S2 += X * X;
		}
		const double M = S / V.Num();
		return M > 0.0 ? static_cast<float>(FMath::Sqrt(FMath::Max(0.0, S2 / V.Num() - M * M)) / M) : 0.f;
	};
	const FString PoolsDescribe = FString::Printf(TEXT("\"pool_run_m\":[%.2f,%.2f,%.2f],\"pool_run_cv\":%.3f,\"pool_gap_m\":[%.2f,%.2f,%.2f],\"pool_gap_cv\":%.3f,\"pool_gaps\":%d,")
		TEXT("\"pools_per_5m_line_max\":%d,\"runs_meeting_a_track\":%d,\"runs_joined_across\":%d,"),
		RoadPercentile(RunLengths, 0.f) / 100.f, RoadPercentile(RunLengths, 0.5f) / 100.f, RoadPercentile(RunLengths, 1.f) / 100.f, Cv(RunLengths),
		RoadPercentile(Gaps, 0.f) / 100.f, RoadPercentile(Gaps, 0.5f) / 100.f, RoadPercentile(Gaps, 1.f) / 100.f, Cv(Gaps), Gaps.Num(), LinePools5m, RunsMeeting, RunsJoined);
	// MRD1b item 4's readouts: the tracks' width at half depth over their tyre (the visible present steps), and where their stretches
	// start and end inside the visible road (fractions of it; the largest gap between those events).
	{
		TArray<float> Ratios;
		TArray<float> Widths;
		for (int32 K = 0; K < Lines.Num(); ++K)
		{
			for (const FStep& L : Lines[K])
			{
				if (L.bVisible && L.Present >= 0.5f)
				{
					Ratios.Add(L.W / FMath::Max(1.f, Tracks[K].Tyre));
					Widths.Add(L.W);
				}
			}
		}
		TArray<float> Events;
		FString Stretches;
		for (const FTrack& T : Tracks)
		{
			const float A = (T.A - VA) / FMath::Max(1.f, VB - VA);
			const float B = (T.B - VA) / FMath::Max(1.f, VB - VA);
			Stretches += FString::Printf(TEXT("%s[%.2f,%.2f]"), Stretches.IsEmpty() ? TEXT("") : TEXT(","), A, B);
			if (A > 0.f && A < 1.f)
			{
				Events.Add(A);
			}
			if (B > 0.f && B < 1.f)
			{
				Events.Add(B);
			}
		}
		Events.Sort();
		float Gap = 0.f;
		for (int32 I = 0; I <= Events.Num(); ++I)
		{
			Gap = FMath::Max(Gap, (I < Events.Num() ? Events[I] : 1.f) - (I > 0 ? Events[I - 1] : 0.f));
		}
		RoadLayoutDescribe = FString::Printf(TEXT("\"width_over_tyre\":[%.2f,%.2f,%.2f],\"width_cm\":[%.1f,%.1f,%.1f],\"stretches\":[%s],\"stretch_ends_in_view\":%d,\"stretch_ends_largest_gap\":%.3f,")
			TEXT("\"pools_per_5m_max\":%d,\"pool_runs\":%d,\"pool_run_mean_m\":%.2f,\"cells_lifted_to_table\":%d,"),
			RoadPercentile(Ratios, 0.f), RoadPercentile(Ratios, 0.5f), RoadPercentile(Ratios, 1.f), RoadPercentile(Widths, 0.f), RoadPercentile(Widths, 0.5f), RoadPercentile(Widths, 1.f),
			*Stretches, Events.Num(), Gap, RoadPoolsPer5mMax, PoolRuns.Num(), PoolRuns.Num() ? [&]() { float S = 0.f; for (const FVector2f& R : PoolRuns) { S += R.X; } return S / PoolRuns.Num() / 100.f; }() : 0.f, Lifted);
		RoadLayoutDescribe += PoolsDescribe;   // MRD1c
	}
	// 4. The rim: everything faded to nothing over the outer PreChurnRimCm (GR1c's), the fresh sheen cleared, and the tread cleared
	// but on the tread tracks' floors: there the old tread (heading + 1..8 for its strength in eighths, phase + 2: M_GT_Mud's old-tread
	// flag, x MPC_TrackPaint MudOldTread, gt.Mud.OldTread).
	float SurfaceHi = 0.f;
	float SurfaceLo = 0.f;
	int32 TreadCells = 0;
	PreChurnHummockCm = 0.f;
	PreChurnRimMaxCm = 0.f;
	PreChurnWaterCells = 0;
	for (int32 Y = 0; Y < SY; ++Y)
	{
		for (int32 X = 0; X < SX; ++X)
		{
			const int32 Index = Y * SX + X;
			const FVector2D C = Field.CellCentreCm(Index);
			const float Rim = static_cast<float>(FMath::Min(FMath::Min(C.X - Box.Min.X, Box.Max.X - C.X), FMath::Min(C.Y - Box.Min.Y, Box.Max.Y - C.Y)));
			const float Fade = FMath::SmoothStep(0.f, RimCm, Rim);
			Field.HeightCm[Index] *= Fade;
			Field.LumpCm[Index] *= Fade;
			PreChurnBaseCm[Index] *= Fade;
			Field.PhaseTurns[Index] = -1.f;
			Field.HeadingTurns[Index] = 0.f;
			Field.Fresh[Index] = 0.f;
			const float Tread = TreadStrength[Index] * Fade;
			if (TreadAlong[Index] >= 0.f && Tread > 0.06f)
			{
				const float Phase = TreadAlong[Index] / FMath::Max(1.f, Field.LugPeriodCm);
				Field.PhaseTurns[Index] = 2.f + (Phase - FMath::FloorToFloat(Phase));
				Field.HeadingTurns[Index] = TreadHeading[Index] + static_cast<float>(FMath::Clamp(FMath::RoundToInt(8.f * Tread), 1, 8));
				++TreadCells;
			}
			PreChurnHummockCm = FMath::Max(PreChurnHummockCm, FMath::Abs(PreChurnBaseCm[Index]));
			const float Surface = Field.SurfaceCm(Index);
			SurfaceHi = FMath::Max(SurfaceHi, Surface);
			SurfaceLo = FMath::Min(SurfaceLo, Surface);
			if (Rim < Cell)
			{
				PreChurnRimMaxCm = FMath::Max(PreChurnRimMaxCm, FMath::Abs(Surface));
			}
			PreChurnWaterCells += Surface < WaterTableCm ? 1 : 0;
		}
	}
	// The gate's water share after the fade (the band lies inside the rim, so the fade leaves it).
	WetBand = 0;
	for (int32 Index = 0; Index < Cells; ++Index)
	{
		WetBand += (Band[Index] && Field.SurfaceCm(Index) < Table) ? 1 : 0;
	}
	RoadPuddleShare = BandCells > 0 ? static_cast<float>(WetBand) / BandCells : 0.f;
	PreChurnSlopeMaxDeg = 0.f;
	for (int32 Y = 1; Y + 1 < SY; ++Y)
	{
		for (int32 X = 1; X + 1 < SX; ++X)
		{
			const int32 Index = Y * SX + X;
			if (Cut[Index] <= 0.5f)
			{
				continue;
			}
			const float GX = (Field.SurfaceCm(Index + 1) - Field.SurfaceCm(Index - 1)) / (2.f * Cell);
			const float GY = (Field.SurfaceCm(Index + SX) - Field.SurfaceCm(Index - SX)) / (2.f * Cell);
			PreChurnSlopeMaxDeg = FMath::Max(PreChurnSlopeMaxDeg, FMath::RadiansToDegrees(FMath::Atan(FMath::Sqrt(GX * GX + GY * GY))));
		}
	}
	PreChurnSurfaceCm.SetNumUninitialized(Cells);
	for (int32 Index = 0; Index < Cells; ++Index)
	{
		PreChurnSurfaceCm[Index] = Field.SurfaceCm(Index);
	}
	DisplaceUpCm = FMath::Max(DisplaceUpCm, SurfaceHi + 15.f);
	DisplaceDownCm = FMath::Max(DisplaceDownCm, -SurfaceLo + 15.f);
	PreChurnTracks = N;
	PreChurnDepthLoCm = AskedDepths.Num() ? RoadPercentile(AskedDepths, 0.f) : 0.f;
	PreChurnDepthHiCm = AskedDepths.Num() ? RoadPercentile(AskedDepths, 1.f) : 0.f;
	PreChurnPuddleShare = RoadPuddleShare;
	PreChurnPuddleBasins = RoadPuddleBasins;
	FString Zones;
	for (const FVector4f& Z : RoadChurnZones)
	{
		Zones += FString::Printf(TEXT("%s[%.0f,%.0f,%.0f,%.0f]"), Zones.IsEmpty() ? TEXT("") : TEXT(","), Z.X, Z.Y, Z.Z, Z.W);
	}
	RoadDescribe = RoadLayoutDescribe + FString::Printf(TEXT("\"tracks\":%d,\"road_half_width_cm\":%.0f,\"visible_m\":%.2f,\"layout_try\":%d,\"crossings_per_20m\":%.2f,\"crossings_min_window_per_20m\":%.2f,")
		TEXT("\"heading_sd_min_window_deg\":%.2f,\"depth_asked\":%s,\"depth_settled\":%s,\"puddle_share\":%.4f,\"puddle_target\":%.4f,\"puddle_basins\":%d,\"band_cells\":%d,")
		TEXT("\"water_table_cm\":%.1f,\"churn_zones\":[%s],\"wall_cells\":%d,\"lip_block_cells\":%d,\"lip_lean_cells\":%d,\"tread_tracks\":%d,\"tread_share_of_present\":%.3f,\"tread_cells\":%d,")
		TEXT("\"hummock_scale\":%.2f,\"slope_max_deg\":%.1f"),
		N, HalfRoad, (VB - VA) / 100.f, RoadLayoutTry, RoadCrossingsPer20m, RoadCrossingsMinWindow, RoadHeadingSdMinWindowDeg, *RoadHistogram(AskedDepths), *RoadHistogram(SettledDepths),
		RoadPuddleShare, RoadPuddleTarget, RoadPuddleBasins, BandCells, Table, *Zones, WallCells, BlockCells, LeanCells, TreadTracks, TreadPresent > 0.f ? TreadLength / TreadPresent : 0.f, TreadCells,
		RoadHummockScale, PreChurnSlopeMaxDeg);
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: mud road (MRD1) - %d braided tracks over %.1f m (layout try %d): crossings %.2f per 20 m (fewest in a window %.2f), heading sd at least %.2f deg; depth asked median %.1f / p90 %.1f cm, settled median %.1f / p90 %.1f cm; puddles %.1f %% of the road (target %.1f %%, %d pool runs, at most %d pools in 5 m of a track); %d churn zone(s); walls %d cells, lip blocks %d (leaning %d); tread on %d track(s), %d cells; surface %.1f..%.1f cm"),
		SectionIndex, N, (VB - VA) / 100.f, RoadLayoutTry, RoadCrossingsPer20m, RoadCrossingsMinWindow, RoadHeadingSdMinWindowDeg, RoadPercentile(AskedDepths, 0.5f), RoadPercentile(AskedDepths, 0.9f),
		RoadPercentile(SettledDepths, 0.5f), RoadPercentile(SettledDepths, 0.9f), 100.f * RoadPuddleShare, 100.f * RoadPuddleTarget, RoadPuddleBasins, RoadPoolsPer5mMax, RoadChurnZones.Num(), WallCells, BlockCells, LeanCells,
		TreadTracks, TreadCells, SurfaceLo, SurfaceHi);
}

void AGTMudPatch::SpawnRoadClodFields()
{
	RoadClodsPlaced = 0;
	if (!IsMudRoad() || ClodMeshes.Num() == 0 || RoadChurnZones.Num() == 0 || CVarMudClods.GetValueOnGameThread() == 0)
	{
		return;
	}
	// Each zone's field: RoadClodsPerM2Min-Max inside its radius, falling off to none over its falloff (a smoothstep), the throw's
	// clod families (PickClodMesh), 4-14 cm (mostly small), old and dry (Source 6: no wet sinking, freshness 0).
	FRandomStream Random(0xC10D6 + 7919 * SectionIndex);
	for (const FVector4f& Z : RoadChurnZones)
	{
		const float Density = Random.FRandRange(RoadClodsPerM2Min, FMath::Max(RoadClodsPerM2Min, RoadClodsPerM2Max));
		const float Outer = Z.Z + Z.W;
		const int32 Draws = FMath::RoundToInt(Density * PI * Outer * Outer / 10000.f);
		for (int32 K = 0; K < Draws; ++K)
		{
			const float R = Outer * FMath::Sqrt(Random.FRand());
			const float Ang = Random.FRandRange(0.f, 2.f * PI);
			const float Keep = R <= Z.Z ? 1.f : 1.f - FMath::SmoothStep(Z.Z, Outer, R);
			if (Random.FRand() > Keep)
			{
				continue;
			}
			FGTMudField::FClodSpawn Spawn;
			Spawn.XYCm = FVector2D(Z.X + R * FMath::Cos(Ang), Z.Y + R * FMath::Sin(Ang));
			const float U = Random.FRand();
			Spawn.SizeCm = FMath::Lerp(4.f, 14.f, U * U);
			Spawn.Seed = Random.RandHelper(MAX_int32);
			Spawn.Source = 6;
			if (Field.Contains(Spawn.XYCm) && KeepsDecorAt(Spawn.XYCm))
			{
				SpawnClod(Spawn);
				++RoadClodsPlaced;
			}
		}
	}
	ClodBatchAccumS = 1.f;   // pushed on the next tick
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: mud road (MRD1) - %d clods in %d churn zone field(s)"), SectionIndex, RoadClodsPlaced, RoadChurnZones.Num());
}

void AGTMudPatch::PlanRoadChunks(TArray<FMudChunkPlan>& Plan)
{
	RoadChunksPlaced = 0;
	if (!IsMudRoad())
	{
		return;
	}
	// A few MR5 chunks round each zone: RoadChunksPerZoneMin-Max, 20-35 cm, between its edge and 60 % of its falloff out.
	FRandomStream Random(0xC4C4 + 104729 * SectionIndex);
	for (const FVector4f& Z : RoadChurnZones)
	{
		const int32 Count = Random.RandRange(FMath::Min(RoadChunksPerZoneMin, RoadChunksPerZoneMax), FMath::Max(RoadChunksPerZoneMin, RoadChunksPerZoneMax));
		for (int32 K = 0; K < Count; ++K)
		{
			const float R = Random.FRandRange(0.6f * Z.Z, Z.Z + 0.6f * Z.W);
			const float Ang = Random.FRandRange(0.f, 2.f * PI);
			FMudChunkPlan Chunk;
			Chunk.XYCm = FVector2D(Z.X + R * FMath::Cos(Ang), Z.Y + R * FMath::Sin(Ang));
			if (!Field.Contains(Chunk.XYCm) || !KeepsDecorAt(Chunk.XYCm))
			{
				continue;
			}
			Chunk.SizeCm = Random.FRandRange(20.f, 35.f);
			Chunk.YawDeg = Random.FRandRange(0.f, 360.f);
			Chunk.TiltDeg = Random.FRandRange(-MudChunkTiltDeg, MudChunkTiltDeg);
			Chunk.TiltAxisDeg = Random.FRandRange(0.f, 360.f);
			Chunk.Mesh = Random.RandHelper(6);
			Chunk.Cell = Field.CellIndexAt(Chunk.XYCm);
			Plan.Add(Chunk);
			++RoadChunksPlaced;
		}
	}
}

FTransform AGTMudPatch::RoadDebrisTransform(const FRoadDebris& Piece) const
{
	return FTransform(Piece.Rotation, FVector(Piece.XYCm.X, Piece.XYCm.Y, MeshRestZAt(Piece.XYCm) + Piece.SurfaceCm - Piece.SunkCm), FVector(Piece.Scale));
}

void AGTMudPatch::InitRoadDebris()
{
	for (UHierarchicalInstancedStaticMeshComponent* Old : RoadDebrisMeshes)
	{
		if (Old)
		{
			Old->DestroyComponent();
		}
	}
	RoadDebrisMeshes.Reset();
	RoadDebris.Reset();
	RoadDebrisPlaced = 0;
	if (!IsMudRoad() || RoadDebrisPerM2 <= 0.f)
	{
		return;
	}
	// The meshes: GR2's three twigs (15, 26, 40 cm) and MRD1's two branches (Art/Blender/build_road_branches.py); a missing one is skipped.
	struct FDebrisMesh { const TCHAR* Path; bool bBranch; };
	static const FDebrisMesh Paths[] = {
		{ TEXT("/Game/GrandTour/ArtTests/GroundDetail/SM_GD_Twig0.SM_GD_Twig0"), false },
		{ TEXT("/Game/GrandTour/ArtTests/GroundDetail/SM_GD_Twig1.SM_GD_Twig1"), false },
		{ TEXT("/Game/GrandTour/ArtTests/GroundDetail/SM_GD_Twig2.SM_GD_Twig2"), false },
		{ TEXT("/Game/GrandTour/ArtTests/MudRoads/SM_MRD_Branch0.SM_MRD_Branch0"), true },
		{ TEXT("/Game/GrandTour/ArtTests/MudRoads/SM_MRD_Branch1.SM_MRD_Branch1"), true } };
	TArray<int32> Twigs;
	TArray<int32> Branches;
	TArray<float> Length;
	TArray<float> Thick;
	for (const FDebrisMesh& Entry : Paths)
	{
		UStaticMesh* DebrisMesh = LoadObject<UStaticMesh>(nullptr, Entry.Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!DebrisMesh)
		{
			continue;
		}
		UHierarchicalInstancedStaticMeshComponent* Hism = NewObject<UHierarchicalInstancedStaticMeshComponent>(this, *FString::Printf(TEXT("RoadDebris_%d"), RoadDebrisMeshes.Num()), RF_Transient);
		Hism->SetStaticMesh(DebrisMesh);
		Hism->SetMobility(EComponentMobility::Movable);
		Hism->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Hism->SetCanEverAffectNavigation(false);
		Hism->SetCastShadow(true);
		Hism->SetCullDistances(4000, 6000);
		Hism->SetupAttachment(RootComponent);
		Hism->RegisterComponent();
		(Entry.bBranch ? Branches : Twigs).Add(RoadDebrisMeshes.Num());
		RoadDebrisMeshes.Add(Hism);
		const FBox Bounds = DebrisMesh->GetBoundingBox();
		Length.Add(FMath::Max(1.f, static_cast<float>(FMath::Max(Bounds.Max.X - Bounds.Min.X, Bounds.Max.Y - Bounds.Min.Y))));
		Thick.Add(FMath::Max(0.3f, static_cast<float>(Bounds.Max.Z - Bounds.Min.Z)));
	}
	if (RoadDebrisMeshes.Num() == 0)
	{
		UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: mud road debris (MRD1) - no meshes found"), SectionIndex);
		return;
	}
	// The road band's area (inside the rim), the count, and the places: uniform over the band, kept by a cluster noise (smoothstepped
	// value noise at RoadDebrisClusterCm, 0.08..1), off the water; a piece lies flat, pitched along the ground under its two ends,
	// sunk RoadDebrisSinkMin-Max of its thickness.
	const FBox2D Box = Field.Bounds();
	const float RimCm = FMath::Max(1.f, PreChurnRimCm);
	const float Cell = Field.CellCm;
	const float HalfRoad = RoadHalfWidthCm > 0.f ? RoadHalfWidthCm : 300.f;
	int32 BandCells = 0;
	for (int32 Index = 0; Index < Field.SizeX * Field.SizeY; ++Index)
	{
		const FVector2D C = Field.CellCentreCm(Index);
		const float Rim = static_cast<float>(FMath::Min(FMath::Min(C.X - Box.Min.X, Box.Max.X - C.X), FMath::Min(C.Y - Box.Min.Y, Box.Max.Y - C.Y)));
		BandCells += (Rim >= RimCm && DistanceToRouteCm(C) <= HalfRoad) ? 1 : 0;
	}
	const float AreaM2 = BandCells * Cell * Cell / 10000.f;
	const int32 Want = FMath::RoundToInt(AreaM2 * RoadDebrisPerM2);
	FRandomStream Random(0xDEB215 + 7 * SectionIndex);
	const float ClusterCells = FMath::Max(1.f, RoadDebrisClusterCm / Cell);
	TArray<int32> PerMesh;
	PerMesh.Init(0, RoadDebrisMeshes.Num());
	for (int32 Guard = 0; Guard < 400 * FMath::Max(1, Want) && RoadDebris.Num() < Want; ++Guard)
	{
		const FVector2D XY(Random.FRandRange(Box.Min.X + RimCm, Box.Max.X - RimCm), Random.FRandRange(Box.Min.Y + RimCm, Box.Max.Y - RimCm));
		if (DistanceToRouteCm(XY) > HalfRoad || !KeepsDecorAt(XY))   // Benmore B2: a zone's debris on its own cells
		{
			continue;
		}
		const int32 Index = Field.CellIndexAt(XY);
		if (Index == INDEX_NONE || Field.SurfaceCm(Index) < WaterTableCm + 0.5f)
		{
			continue;
		}
		const int32 CX = Index % Field.SizeX;
		const int32 CY = Index / Field.SizeX;
		const float Keep = FMath::Max(0.08f, FMath::SmoothStep(0.35f, 0.65f, 0.5f + Field.CellNoise(CX, CY, ClusterCells, 4409 + SectionIndex)));
		if (Random.FRand() > Keep)
		{
			continue;
		}
		const bool bBranch = Branches.Num() > 0 && (Twigs.Num() == 0 || Random.FRand() < RoadDebrisBranchShare);
		const TArray<int32>& Pool = bBranch ? Branches : Twigs;
		FRoadDebris Piece;
		Piece.Mesh = Pool[Random.RandHelper(Pool.Num())];
		Piece.XYCm = XY;
		// Branches 40-120 cm: their own length scaled into that range; twigs +-20 %.
		const float Len0 = Length[Piece.Mesh];
		Piece.Scale = bBranch ? FMath::Clamp(Random.FRandRange(40.f, 120.f) / Len0, 0.4f, 2.f) : Random.FRandRange(0.8f, 1.2f);
		const float Yaw = Random.FRandRange(0.f, 360.f);
		const FVector2D Dir(FMath::Cos(FMath::DegreesToRadians(Yaw)), FMath::Sin(FMath::DegreesToRadians(Yaw)));
		const float Half = 0.5f * Len0 * Piece.Scale;
		auto Ground = [&](const FVector2D& P) { return MeshRestZAt(P) + Field.HeightAt(P); };
		const float ZA = Ground(XY - Dir * Half);
		const float ZB = Ground(XY + Dir * Half);
		const float Pitch = FMath::RadiansToDegrees(FMath::Atan2(ZB - ZA, 2.f * Half));
		Piece.Rotation = FRotator(Pitch, Yaw, Random.FRandRange(-6.f, 6.f)).Quaternion();
		// The centre on the higher of the ground under it and the ends' mean (a branch over a rut lies on its ridges), then sunk.
		const float Mean = 0.5f * (ZA + ZB) - MeshRestZAt(XY);
		Piece.SurfaceCm = FMath::Max(Field.HeightAt(XY), Mean);
		Piece.SunkCm = Random.FRandRange(RoadDebrisSinkMin, FMath::Max(RoadDebrisSinkMin, RoadDebrisSinkMax)) * Thick[Piece.Mesh] * Piece.Scale;
		Piece.Instance = RoadDebrisMeshes[Piece.Mesh]->AddInstance(RoadDebrisTransform(Piece), true);
		++PerMesh[Piece.Mesh];
		RoadDebris.Add(Piece);
	}
	RoadDebrisPlaced = RoadDebris.Num();
	FString Counts;
	for (int32 K = 0; K < PerMesh.Num(); ++K)
	{
		Counts += FString::Printf(TEXT("%s%s %d"), K ? TEXT(", ") : TEXT(""), *RoadDebrisMeshes[K]->GetStaticMesh()->GetName(), PerMesh[K]);
	}
	UE_LOG(LogTemp, Display, TEXT("AGTMudPatch %d: mud road debris (MRD1) - %d of %d pieces over %.1f m2 of road (%.3f a m2): %s"), SectionIndex, RoadDebris.Num(), Want, AreaM2, RoadDebrisPerM2, *Counts);
}

void AGTMudPatch::UpdateRoadDebris(const FIntRect& Rect)
{
	// A piece whose ground a wheel pressed by over 2 cm in a track goes down with it, a further 1.5 cm in.
	const FVector2D Lo = Field.OriginCm + FVector2D(Rect.Min.X, Rect.Min.Y) * Field.CellCm;
	const FVector2D Hi = Field.OriginCm + FVector2D(Rect.Max.X, Rect.Max.Y) * Field.CellCm;
	for (FRoadDebris& Piece : RoadDebris)
	{
		if (Piece.XYCm.X < Lo.X || Piece.XYCm.Y < Lo.Y || Piece.XYCm.X > Hi.X || Piece.XYCm.Y > Hi.Y)
		{
			continue;
		}
		const float Now = Field.HeightAt(Piece.XYCm);
		if (Piece.SurfaceCm - Now > 2.f && Field.TracksAt(Piece.XYCm) >= 0.5f && RoadDebrisMeshes.IsValidIndex(Piece.Mesh) && RoadDebrisMeshes[Piece.Mesh])
		{
			Piece.SurfaceCm = Now;
			Piece.SunkCm += 1.5f;
			RoadDebrisMeshes[Piece.Mesh]->UpdateInstanceTransform(Piece.Instance, RoadDebrisTransform(Piece), true, true, true);
		}
	}
}

FString AGTMudPatch::DescribeMudRoad() const
{
	if (!IsMudRoad())
	{
		return TEXT("{}");
	}
	return FString::Printf(TEXT("{\"section\":%d,\"mud_road_spray_scale\":%.2f,\"debris_per_m2\":%.3f,\"debris\":%d,\"clods\":%d,\"chunks\":%d,%s}"),
		SectionIndex, MudRoadSprayScale, RoadDebrisPerM2, RoadDebrisPlaced, RoadClodsPlaced, RoadChunksPlaced, *RoadDescribe);
}

FString AGTMudPatch::DescribePreChurn() const
{
	return FString::Printf(TEXT("{\"section\":%d,\"scale\":%.3f,\"pre_churned\":%s,\"tracks\":%d,\"depth_cm\":[%.2f,%.2f],\"hummock_cm\":%.2f,\"water_cells\":%d,\"cells\":%d,\"water_table_cm\":%.1f,\"rim_max_cm\":%.3f,\"chunks_kept\":%d,\"chunks_moved\":%d,\"chunks_planned\":%d,\"chunks_planned_flat\":%d,\"filled_depth_cm\":%.2f,\"filled_share\":%.3f,\"trough_cells\":%d,\"slope_max_deg\":%.2f,\"box_line_m\":%.2f,\"present_shares\":[%s],\"puddle_share\":%.3f,\"puddle_depth_cm\":%.2f,\"puddle_basins\":%d,\"puddle_basins_wet\":%d,\"puddle_wall_max_deg\":%.2f}"),
		SectionIndex, PreChurnScale, IsPreChurned() ? TEXT("true") : TEXT("false"), PreChurnTracks, PreChurnDepthLoCm, PreChurnDepthHiCm, PreChurnHummockCm, PreChurnWaterCells,
		Field.SizeX * Field.SizeY, WaterTableCm, PreChurnRimMaxCm, PreChurnChunksKept, PreChurnChunksMoved, MudChunksPlanned, PreChurnChunksFlat, PreChurnFilledLoCm, PreChurnFilledShare, PreChurnTrackCells, PreChurnSlopeMaxDeg,
		PreChurnBoxLineCm / 100.f, *FString::JoinBy(PreChurnPresentShares, TEXT(","), [](float Share) { return FString::Printf(TEXT("%.3f"), Share); }),
		PreChurnPuddleShare, PreChurnPuddleDepthHiCm, PreChurnPuddleBasins, PreChurnPuddleWet, PreChurnPuddleWallDeg);
}

// ---- Benmore integration B2 (docs/BENMORE_INTEGRATION_PLAN.md B2): a deform zone's patch ------------------------------------

void AGTMudPatch::SetZoneCoverage(UTexture* Coverage, const FLinearColor& Window)
{
	if (MeshMaterial && Coverage)
	{
		MeshMaterial->SetTextureParameterValue(TEXT("GTDeformCoverage"), Coverage);
		MeshMaterial->SetVectorParameterValue(TEXT("GTDeformWindow"), Window);
	}
}

void AGTMudPatch::SetZoneRoute(const TArray<FVector2D>& LineCm, float HalfWidthCm)
{
	RouteLineCm = LineCm;
	RoadHalfWidthCm = FMath::Max(1.f, HalfWidthCm);
}

bool AGTMudPatch::ZoneOwns(const FVector2D& XYCm) const
{
	if (XYCm.X < ZoneOwnBoxCm.Min.X || XYCm.Y < ZoneOwnBoxCm.Min.Y || XYCm.X >= ZoneOwnBoxCm.Max.X || XYCm.Y >= ZoneOwnBoxCm.Max.Y)
	{
		return false;
	}
	const int32 Index = Field.CellIndexAt(XYCm);
	return ZoneCells.IsValidIndex(Index) && ZoneCells[Index] == 2;
}

bool AGTMudPatch::ZoneQuadDrawn(int32 X, int32 Y) const
{
	if (X < 0 || Y < 0 || X >= Field.SizeX || Y >= Field.SizeY || !ZoneCells.IsValidIndex(Y * Field.SizeX + X) || ZoneCells[Y * Field.SizeX + X] == 0)
	{
		return false;
	}
	const FVector2D C = Field.OriginCm + FVector2D(X + 0.5, Y + 0.5) * Field.CellCm;
	return C.X >= ZoneOwnBoxCm.Min.X && C.Y >= ZoneOwnBoxCm.Min.Y && C.X < ZoneOwnBoxCm.Max.X && C.Y < ZoneOwnBoxCm.Max.Y;
}

void AGTMudPatch::FadeZonePreChurn(const TArray<float>& InsideCm, float FadeCm)
{
	const int32 Cells = Field.SizeX * Field.SizeY;
	if (InsideCm.Num() != Cells || ZoneCells.Num() != Cells)
	{
		return;
	}
	const float Fade = FMath::Max(1.f, FadeCm);
	for (int32 Index = 0; Index < Cells; ++Index)
	{
		const float K = ZoneCells[Index] == 2 ? FMath::SmoothStep(0.f, Fade, InsideCm[Index]) : 0.f;
		if (K >= 1.f)
		{
			continue;
		}
		Field.HeightCm[Index] *= K;
		if (Field.LumpCm.IsValidIndex(Index))
		{
			Field.LumpCm[Index] *= K;
		}
		if (PreChurnBaseCm.IsValidIndex(Index))
		{
			PreChurnBaseCm[Index] *= K;
		}
		if (PreChurnSurfaceCm.IsValidIndex(Index))
		{
			PreChurnSurfaceCm[Index] *= K;
		}
		if (K <= 0.f)
		{
			Field.OffsetCm[Index] = FVector2f::ZeroVector;
			Field.Tracks[Index] = 0;
		}
	}
}

int32 AGTMudPatch::BakeZoneLayers(const TFunctionRef<float(const FVector2D&)>& BogWeightAt)
{
	BogCells = 0;
	if (!Field.IsValid())
	{
		return 0;
	}
	BogMask.SetNumUninitialized(Field.SizeX * Field.SizeY);
	for (int32 Y = 0; Y < Field.SizeY; ++Y)
	{
		for (int32 X = 0; X < Field.SizeX; ++X)
		{
			const FVector2D C = Field.OriginCm + FVector2D(X + 0.5, Y + 0.5) * Field.CellCm;
			const float Bog = FMath::Clamp(BogWeightAt(C), 0.f, 1.f);
			BogMask[Y * Field.SizeX + X] = static_cast<uint8>(FMath::RoundToInt(255.f * Bog));
			BogCells += Bog >= 0.5f ? 1 : 0;
		}
	}
	// BakeLayers' texture, the same two channels (R the layer, G the softness).
	FillLayerBytes();
	LayerTexture = UTexture2D::CreateTransient(Field.SizeX, Field.SizeY, PF_R8G8);
	if (LayerTexture)
	{
		LayerTexture->SRGB = false;
		LayerTexture->Filter = TF_Bilinear;
		LayerTexture->AddressX = TA_Clamp;
		LayerTexture->AddressY = TA_Clamp;
		if (FTexturePlatformData* PlatformData = LayerTexture->GetPlatformData())
		{
			if (PlatformData->Mips.Num() > 0)
			{
				FTexture2DMipMap& Mip = PlatformData->Mips[0];
				if (void* Dest = Mip.BulkData.Lock(LOCK_READ_WRITE))
				{
					FMemory::Memcpy(Dest, LayerBytes.GetData(), FMath::Min<int64>(LayerBytes.Num(), Mip.BulkData.GetBulkDataSize()));
				}
				Mip.BulkData.Unlock();
			}
		}
		LayerTexture->UpdateResource();
		if (MeshMaterial)
		{
			MeshMaterial->SetTextureParameterValue(TEXT("MudLayer"), LayerTexture);
		}
	}
	return BogCells;
}

const UGTSurfacePhysMaterial* AGTMudPatch::ZoneSurfaceAt(const FVector2D& XYCm) const
{
	if (!bZonePatch || bHasProfile || Medium != EGTDeformMedium::Mud)
	{
		return nullptr;
	}
	const int32 Index = Field.CellIndexAt(XYCm);
	const bool bBog = BogMask.IsValidIndex(Index) && BogMask[Index] >= 128;
	return bBog && ZoneBogRow ? ZoneBogRow.Get() : ZoneMudRow.Get();
}
