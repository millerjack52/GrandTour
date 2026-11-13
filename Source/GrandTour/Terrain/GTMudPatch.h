#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Terrain/GTMudField.h"
#include "Terrain/GTTerrainGenerator.h"   // LM3a: EGTDeformMedium
#include "GTMudPatch.generated.h"

class UGTGravelStones;   // Deformable gravel DG1
class AGTDeformZone;      // Benmore B2
class UGTSurfacePhysMaterial;
class UHierarchicalInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UPrimitiveComponent;   // MR5
class UStaticMesh;
class UStaticMeshComponent;
class UProceduralMeshComponent;
class UTexture2D;
struct FGTTerrainSpec;
struct FGTDeformProfile;

/**
 * One bog's deformable mud (docs/MUD_DEFORMATION_PLAN.md): the mud field over a Mud route section's footprint, spawned
 * by UGTMudSubsystem at BeginPlay, the texture built from it each tick the field changes (R height in metres, GB the
 * slide-away offset in metres, A the tracks factor), and (stage B) a flat grid mesh at MeshCellCm over the footprint
 * with its vertices on the landscape MeshLiftCm up, wearing M_GT_Mud with this patch's texture and bounds: the vertex
 * shader displaces by the texture and the pixel shader draws mud over the whole box (stage D, one surface: the
 * landscape has a hole the size of the box shrunk by one cell, so this mesh is the ground there and there is no
 * boundary between touched and untouched mud). No collision: the wheels sweep the landscape and the sinkage model
 * drops the car.
 * Stage G adds a second grid, WaterMesh: the same vertices WaterTableCm over the mud mesh's rest surface, translucent,
 * wearing M_GT_MudWater, which draws nothing where the field stands at or above the table - so the water is in the
 * ruts and only in the ruts, and its surface follows the ground cell by cell instead of being one plane per bog. The
 * weather lifts the table by WetTableLiftCm x wetness, as AGTWaterSheet lifts a ford.
 */
UCLASS(NotPlaceable)
class GRANDTOUR_API AGTMudPatch : public AActor
{
	GENERATED_BODY()

public:
	AGTMudPatch();

	virtual void Tick(float DeltaSeconds) override;

	/** LM3a: SnowDepthAt (world cm -> cm, the section's drifts) bakes a snow patch's depth per cell before the mesh is built; unset, the snow is SnowDepthCm all over. */
	void Init(int32 InSectionIndex, const FBox2D& BoundsCm, float CellCm, const TFunction<float(const FVector2D&)>& SnowDepthAt = TFunction<float(const FVector2D&)>());

	/** The grid mesh over the field's footprint from the ground under each vertex; Init calls it. Returns the vertex count. */
	int32 BuildMesh();
	/** Stage G: the water grid, the same vertices WaterTableCm over the mud mesh's rest surface, wearing M_GT_MudWater; BuildMesh calls it. Returns the vertex count (0 when the material is missing). */
	int32 BuildWaterMesh();
	/** Which landscape layer lies under each cell, from the generator (1 where the Bog layer is, 0 where Mud, blended across the landscape's quads as its weightmap is), as a texture the mud material takes its ground colour and roughness from. Returns the bog cells. */
	int32 BakeLayers(const FGTTerrainSpec& Spec);
	/** The material's diagnostic ramp (the hide shots): R the mud height, G the ground's Z from WindowZ0 over WindowRangeCm (the mesh's own range when 0), B the tracks; everything drawn. */
	void SetDiagnostic(bool bOn, float WindowZ0 = 0.f, float WindowRangeCm = 0.f);
	/** The mesh's rest height (the ground MeshLiftCm up) at a world XY, bilinear over the vertices, the edge outside. */
	float MeshRestZAt(const FVector2D& XYCm) const;

	const FGTMudField& GetField() const { return Field; }
	FGTMudField& GetField() { return Field; }
	/** Benmore B2: a zone patch contains only its own region's cells inside the zone (the rest of its field is inert overlap). */
	bool Contains(const FVector2D& XYCm) const { return Field.Contains(XYCm) && (!bZonePatch || ZoneOwns(XYCm)); }

	/** Stage G: where the water stands now, cm over the undisturbed ground (negative: under it) - the section's table plus the weather's lift. */
	float CurrentWaterTableCm() const { return WaterTableCm + WaterLiftCm; }
	/** The water over the mud at a world XY inside this patch, cm; 0 where the mud stands at or above the table. What the WaterMesh draws, and what UGTWaterSubsystem::Sample answers as kind Rut since water stage W3 (the traction reads it through that one call; the hull ignores it). */
	float WaterDepthCmAt(const FVector2D& XYCm) const;
	/** The water grid is there, has its material and is visible (the test's draw state). */
	bool IsWaterDrawn() const;

	/** The Mud section of the spec this patch covers (since RIVERBED S4 also a section with a deformation profile: a ford's bed). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 SectionIndex = -1;

	// ---- RIVERBED S4 (2026-09-23, VEHICLE_BUILD_SYSTEM 54): a section's deformation profile ------------------------
	/**
	 * The section has a deformation profile (FGTRouteSection::Deform; a Ford's bed by default): for a wheel inside this
	 * box on ground that sinks at all, the traction takes ProfileSinkageRate and ProfileMaxSinkageM in place of the
	 * surface row's two numbers, and reads and stamps this field whatever the ground's tag. False on a bog: its rows and
	 * its Mud/Bog tag gate, as before.
	 */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	bool bHasProfile = false;
	/** m/s and m, the profile's (0 without one). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float ProfileSinkageRate = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float ProfileMaxSinkageM = 0.f;
	/** The MPC_TrackPaint slot (Patch0..3) this patch's box went into, so the landscape has its hole there; -1 when the four were taken. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 HoleSlot = -1;
	/** The rut-water grid's quads left out because a water sheet covers them (under a ford's sheet the water is the sheet's). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 WaterQuadsUnderSheet = 0;
	/** RIVERBED S4: the profile's sinkage numbers and its ridge numbers into this patch. Before Init, which pushes the ridge numbers into the field. LM5b: a mud variant's profile (bScalesRows) sets only its scales, RecoverShare, LumpShare, ThrowMax and the water table's offset; the patch stays a bog's. */
	void ApplyProfile(const FGTDeformProfile& Profile);
	/**
	 * LM5b: everything a section gives its patch before Init, in UGTMudSubsystem::BuildPatches' order: the water table, the
	 * variant (a Mud section's MudVariant; Standard for any other kind) and the profile (GTTerrain::DeformProfileFor).
	 * Returns the profile applied, or null.
	 */
	const FGTDeformProfile* ApplySection(const FGTTerrainSpec& Spec, const FGTRouteSection& Section);

	// ---- LM5b, the four churned-bog variants (docs/LIVING_MUD_PLAN.md LM5b, docs/MUD_VARIANTS.md) --------------------
	/** The section's variant: the slice of the bog texture arrays the mesh (M_GT_Mud's MudVariant) and the clods (M_GT_Clod's) wear, and MPC_TrackPaint's PatchVariant<slot> for the landscape's apron. Standard on every non-Mud patch. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Variant")
	EGTMudVariant MudVariant = EGTMudVariant::Standard;
	/** The variant's scales on the sinkage (cap, rate) and friction a wheel inside the box takes (UGTTractionComponent): 1 on Standard and on every patch before LM5b. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Variant")
	float MaxSinkageScale = 1.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Variant")
	float SinkageRateScale = 1.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Variant")
	float FrictionScale = 1.f;
	/** The clods' M_GT_Clod instance with this patch's MudVariant (null on Standard and snow: the clods wear the material itself). */
	UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Variant")
	TObjectPtr<UMaterialInstanceDynamic> ClodMaterialInstance;

	// ---- Ground relief GR1 item 4, the bog's pre-churn (docs/GROUND_RELIEF_PLAN.md GR1) ---------------------------------
	// At Init, after the soft spots and before the mesh and the chunks: hummocks in HeightCm, old rut pairs along the route line
	// (GR1b: cosine troughs with banks, partly filled, LM2's lumps re-seeded over them; GR1c: 1-2 pairs fading in and out, wide and
	// shallow, puddles under the water table; then PreChurnSettleS of the field's own Settle), the rim faded, the tread and the fresh sheen cleared (old ruts). gt.Mud.PreChurn 0 or PreChurnScale 0: the flat
	// field as before. gt.Mud.PreChurnDebug: the GR1b crease diagnosis.
	/** The section's Deform.PreChurnScale (ApplySection); 0 none, 1 the plan's numbers (depths and hummocks scale with it). Before Init. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnScale = 0.f;
	/** GR1c: old rut pairs per patch; PreChurnPairsLong where the route runs more than PreChurnLongPatchCm through the patch's box. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	int32 PreChurnPairs = 1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	int32 PreChurnPairsLong = 2;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnLongPatchCm = 4000.f;
	/** A pair's lateral wander off the route line, cm (+-), over a wavelength drawn per pair between these (two sines, not one). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnWanderCm = 150.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnWanderWaveMinCm = 2000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnWanderWaveMaxCm = 4000.f;
	/** A pair's centre sits within this of the route line before its wander, cm (+-). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnSpreadCm = 100.f;
	/** The old ruts' depth, cm, varying along the length between these (x PreChurnScale; GR1b: on knots PreChurnDepthKnot* apart; GR1c 5-14). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnDepthMinCm = 5.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnDepthMaxCm = 14.f;
	/** GR1b: a trough's half width is at least this many times its depth (cosine section: the steepest flank about atan(pi / (2 x this))). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnWallPerDepth = 2.6f;
	/** GR1c: a wheel line's width at half depth, x its tyre's width, between these along the track (knots 2-4 m apart): old tracks spread. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnWidthMin = 1.4f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnWidthMax = 1.9f;
	/** GR1c: each pair fades in and out over these, cm, at random points (the holds between drawn from a cycle of PreChurnFadeCycle*),
	 * so PreChurnPresentMin-Max of its length in the box is present (drawn per pair) and no pair runs the whole box. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnFadeMinCm = 300.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnFadeMaxCm = 800.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnFadeCycleMinCm = 1600.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnFadeCycleMaxCm = 2800.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPresentMin = 0.35f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPresentMax = 0.6f;
	/** GR1c: where the patch has a water table (at or above -PreChurnPuddleTableMaxCm), the lowest-lying PreChurnPuddleShareMin-Max of
	 * each line's present length makes the puddle runs, each with a floor PreChurnPuddleBelowMin-MaxCm under the table, after the
	 * settle. GR2 phase B item 7: each run is a cosine basin inside the track's footprint (along the run + half PreChurnPuddleRampCm
	 * each end, across the track's half width), its walls at most PreChurnPuddleWallMaxDeg; the field is taken down to it where higher.
	 * (GR1c: a trough along the run, PreChurnPuddleWallPerDepth x the extra cut wide; no longer read.) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleShareMin = 0.2f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleShareMax = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleBelowMinCm = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleBelowMaxCm = 5.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleRampCm = 150.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleTableMaxCm = 40.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleWallPerDepth = 4.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleWallMaxDeg = 30.f;
	/** GR2 phase B item 7: past the track's half width the basin's wall goes on at the limit over this share of it more, so a floor
	 *  under a deep table (Standard's -25 cm) is reachable without a step; then the floor rises (a dry dip) if still short. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleSkirt = 0.5f;
	/** GR1b: the depth's knots along the track lie this far apart, cm, drawn between these. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnDepthKnotMinCm = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnDepthKnotMaxCm = 300.f;
	/** GR1b: each line's share of its length filled back (drawn per line between these) and how far back (per segment), share of the depth. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnFillShareMin = 0.2f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnFillShareMax = 0.4f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnFillDepthMin = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnFillDepthMax = 0.6f;
	/** GR1b: the share of a trough's section the banks beside it carry (cosine humps 1.2 x its half width). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnBankReturn = 0.5f;
	/** MR4: inside S over 0.6 the old ruts are this much deeper (GR1c: within PreChurnDepthMaxCm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnSoftDeepen = 1.4f;
	/** Seconds of the field's own settle after the tracks, so they read old and slumped. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnSettleS = 10.f;
	/** The hummocks: +- amplitude between these, cm (a cluster noise of PreChurnClusterCm picks it), two octaves at these wavelengths, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnHummockMinCm = 5.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnHummockMaxCm = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnHummockWaveCm = 250.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnHummockFineWaveCm = 120.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnClusterCm = 500.f;
	/** The pre-churn fades to nothing over the patch's outer this-many cm, so the apron matches. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnRimCm = 150.f;
	/** MR5: a chunk sits only where the pre-churned surface is within this of the hummocked ground before the tracks, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|PreChurn")
	float PreChurnChunkBandCm = 3.f;
	/** Readouts (Init): the pairs stamped, the depths asked (cm, after the soft deepening), the hummocks' most |cm|, the cells under the
	 * water table, the most |surface| in the outermost cells, and of the plan without the pre-churn's chunks how many places the
	 * pre-churn kept (within PreChurnChunkBandCm of the hummocked ground) or moved (an old rut or its bank). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	int32 PreChurnTracks = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnDepthLoCm = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnDepthHiCm = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnHummockCm = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	int32 PreChurnWaterCells = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnRimMaxCm = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	int32 PreChurnChunksKept = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	int32 PreChurnChunksMoved = 0;
	/** The plan without the pre-churn's count (whose places Kept / Moved sort). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	int32 PreChurnChunksFlat = 0;
	/** GR1b readouts: the shallowest filled depth, cm; the filled share of the tracks' length inside the box; the trough cells (cut over
	 * 0.5 cm); the steepest a trough cell stands after the settle, degrees. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnFilledLoCm = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnFilledShare = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	int32 PreChurnTrackCells = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnSlopeMaxDeg = 0.f;
	/** GR1c readouts: each pair's present share of the route's stretch in the box; the puddle runs' share of the lines' present length;
	 * the most a puddle was cut into the settled floor, cm; the route's stretch in the box, cm (it picks the pair count). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	TArray<float> PreChurnPresentShares;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleShare = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleDepthHiCm = 0.f;
	/** GR2 phase B item 7: the basins cut, and the steepest cell on their own surface, degrees. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	int32 PreChurnPuddleBasins = 0;
	/** GR2 phase B item 7: the basins whose floor lies under the water table (the others are dips the table cannot reach). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	int32 PreChurnPuddleWet = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnPuddleWallDeg = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|PreChurn")
	float PreChurnBoxLineCm = 0.f;
	/** GR1: the readouts above as JSON (the check scripts' rows). */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|PreChurn")
	FString DescribePreChurn() const;
	/** GR1: whether Init pre-churned this patch. */
	bool IsPreChurned() const { return PreChurnSurfaceCm.Num() > 0 && PreChurnSurfaceCm.Num() == Field.SizeX * Field.SizeY; }
	/** GR1: the hummocked ground before the tracks, per cell, cm (empty without a pre-churn). */
	const TArray<float>& GetPreChurnBase() const { return PreChurnBaseCm; }
	/** GR1: the pre-churn's per-sample asked depths (cm) along every old rut, for the test. */
	const TArray<float>& GetPreChurnDepths() const { return PreChurnDepthsCm; }

	// ---- Mud roads MRD1 (docs/MUD_ROADS_PLAN.md MRD1 items 1, 3, 4): the braided pre-churn, its debris, its spray number ---------
	// PreChurnStyle Braided (the section's Deform.PreChurnStyle): in place of GR1c's pairs, RoadTracks old tracks across the road
	// (2 x RoadHalfWidthCm / RoadTrackSpacingCm, RoadTracksMin-Max), each a cosine trough on its own path (two sines, the first
	// RoadWave1Min-MaxCm, the second RoadWave2Min-MaxCm, swinging RoadSwingMin-MaxCm), present over RoadPresentMin-Max of the road
	// (one stretch, starting and ending at random), RoadDepthMin-MaxCm deep by a truncated power law (RoadDepthAlpha) on knots
	// RoadDepthKnotMin-MaxCm apart, RoadWidthMin-Max x its tyre wide at half depth; the layout redrawn (at most RoadLayoutTries)
	// until every 20 m window has RoadCrossingsMin crossings and a heading sd of RoadHeadingSdMinDeg. Banks of RoadBankReturn of the
	// cut make the ridges, lumps re-seeded at RoadLumpShare (heavier on the ridges); the field's settle; then the deep tracks'
	// walls stepped and their lips broken into blocks (some leaning in), the puddles cut in the lowest runs until the water covers
	// RoadPuddleShareMin-Max of the road, the churn zones, the partial old tread on the freshest tracks.
	/** The section's Deform.PreChurnStyle (ApplySection). Before Init. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	EGTPreChurnStyle PreChurnStyle = EGTPreChurnStyle::Pairs;
	/** The section's Deform.MudRoadSprayScale (ApplySection): the mud road's spray multiplier for the spray code to read (B1b's). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	float MudRoadSprayScale = 1.f;
	/** The section's Deform.RoadDebrisPerM2 (ApplySection): sticks and branches per m^2 of the road band on a braided patch. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	float RoadDebrisPerM2 = 0.f;
	/** MRD1b item 3: the section's Deform.RoadSiltTileMul / RoadSiltStrength, M_GT_Mud's SiltTileMul / SiltStrength on this patch. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	float RoadSiltTileMul = 1.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	float RoadSiltStrength = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadTrackSpacingCm = 90.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	int32 RoadTracksMin = 6;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	int32 RoadTracksMax = 14;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadWave1MinCm = 1500.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadWave1MaxCm = 3500.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadWave2MinCm = 3000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadWave2MaxCm = 6000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadSwingMinCm = 40.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadSwingMaxCm = 150.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPresentMin = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPresentMax = 0.9f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadDepthMinCm = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadDepthMaxCm = 25.f;
	/** The power law's exponent: a knot's depth Min / (1 - u (1 - (Min/Max)^a))^(1/a); 0.4 gives a median near 5.8 cm and 10 % at 15 cm or more along the tracks. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadDepthAlpha = 0.4f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadDepthKnotMinCm = 200.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadDepthKnotMaxCm = 600.f;
	/** MRD1b item 4: 1.2-2.0 x the tyre (MRD1's 0.8-1.6 drew narrow dark crevices from above). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadWidthMin = 1.2f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadWidthMax = 2.0f;
	/** The trough's width at half depth is at least this x its depth (GR1c's 2.6 made deep tracks broad and soft). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadWallPerDepth = 1.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadBankReturn = 0.7f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadLumpShare = 0.5f;
	/** The hummocks' amplitude on a road, x the bog's (a road is flatter than a bog; the ridges come from the tracks' banks). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadHummockScale = 0.4f;
	/** MRD1b item 4: relaxed from 3. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadCrossingsMin = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadHeadingSdMinDeg = 4.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	int32 RoadLayoutTries = 48;
	/** Walls of tracks deeper than this get the stepped, crumbly profile (shallower keep the cosine). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadWallDeepCm = 10.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadStepMinCm = 4.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadStepMaxCm = 7.f;
	/** The lip's clump blocks: one a cell (12.5 cm, the plan's 6-15 cm), RoadBlockMin-MaxCm high, some cells left out. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadBlockMinCm = 1.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadBlockMaxCm = 4.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadOverhangShare = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadOverhangMinCm = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadOverhangMaxCm = 4.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPuddleShareMin = 0.08f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPuddleShareMax = 0.15f;
	/** MRD1b item 2: a pool's floor 1-4 cm under the table. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPuddleBelowMinCm = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPuddleBelowMaxCm = 4.f;
	/** MRD1b item 2 / MRD1c item 2: the pools - low runs of RoadPoolMin-MaxCm along a track (Min + (Max - Min) u^RoadPoolLenPower:
	 *  mostly short, a long tail, CV about 0.45), keeping RoadPoolGapMin-MaxCm clear on each side (the same law), their ends tapering
	 *  over RoadPoolTaperMin-MaxCm, the flat's width wobbled by RoadPoolWobble, RoadPoolJoinShare of those meeting another track's
	 *  trough carrying on across it; the floor flat over RoadPoolFlat of the track's half-depth width, up to the ground by 1.05 of it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolMinCm = 200.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolMaxCm = 800.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolLenPower = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolGapMinCm = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolGapMaxCm = 600.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolTaperMinCm = 50.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolTaperMaxCm = 150.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolWobble = 0.35f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolJoinShare = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadPoolFlat = 0.55f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadChurnPer40mMin = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadChurnPer40mMax = 3.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadChurnRadiusMinCm = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadChurnRadiusMaxCm = 180.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadClodsPerM2Min = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadClodsPerM2Max = 6.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadClodFalloffMinCm = 200.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadClodFalloffMaxCm = 400.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	int32 RoadChunksPerZoneMin = 2;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	int32 RoadChunksPerZoneMax = 4;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	int32 RoadTreadTracksMin = 2;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	int32 RoadTreadTracksMax = 3;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadTreadShare = 0.4f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadTreadDepthMinCm = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadTreadDepthMaxCm = 0.8f;
	/** The debris: GR2's twigs and MRD1's branches, the cluster noise's cell, the branches' share of the pieces, sunk this share of their thickness. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadDebrisClusterCm = 400.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadDebrisBranchShare = 0.35f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadDebrisSinkMin = 0.25f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|MudRoad")
	float RoadDebrisSinkMax = 0.6f;
	// The readouts (DescribeMudRoad): the gates of item 1, measured over the road band inside the rim.
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	int32 RoadTracks = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	int32 RoadLayoutTry = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	float RoadCrossingsPer20m = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	float RoadCrossingsMinWindow = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	float RoadHeadingSdMinWindowDeg = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	float RoadPuddleShare = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	float RoadPuddleTarget = 0.f;
	/** MRD1b: the pool runs cut (MRD1: the basins). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	int32 RoadPuddleBasins = 0;
	/** MRD1b item 2's gate, MRD1c item 3: the most of a track's OWN pools reaching into any 5 m of it (<= 2). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	int32 RoadPoolsPer5mMax = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	int32 RoadClodsPlaced = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	int32 RoadChunksPlaced = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|MudRoad")
	int32 RoadDebrisPlaced = 0;
	/** The braided patch's gates and counts as JSON (the capture's rows); "{}" on any other patch. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|MudRoad")
	FString DescribeMudRoad() const;
	bool IsMudRoad() const { return PreChurnStyle == EGTPreChurnStyle::Braided && IsPreChurned(); }

	// ---- MudRunner MR4, readable soft spots (docs/MUDRUNNER_LESSONS_PLAN.md MR4 execution block) ----------------------
	// What you see is what you feel: a static softness S (0..1) per cell, built at Init, read by the traction (SoftScalesAt)
	// and by M_GT_Mud (LayerTexture G). It changes no field height (outside the field and its CRC).
	/** MR4: the soft spots' amplitude, S = 0.5 + (S0 - 0.5) x this: the variant profile's SoftSpotAmplitude (ApplyProfile), 1 on Standard (no profile). Before Init. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|SoftSpots")
	float SoftSpotAmplitude = 1.f;
	/** MR4: the patch means of lerp(0.75, 1.5, S) and lerp(1.05, 0.9, S) over all its cells (Init); SoftScalesAt divides by them, so the patch's mean scale is 1. 1 off scope. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|SoftSpots")
	float SoftMeanSink = 1.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|SoftSpots")
	float SoftMeanFriction = 1.f;
	/** MR4's scope: a Mud-medium bog patch without a profile (an unprofiled bog, or an LM5b variant's: bScalesRows keeps bHasProfile false). Not a ford's or riverbed's profiled patch, not snow, not any other medium. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|SoftSpots")
	bool HasSoftSpots() const { return !bHasProfile && Medium == EGTDeformMedium::Mud && Softness.Num() > 0 && Softness.Num() == Field.SizeX * Field.SizeY; }
	/** MR4: S at a world XY, bilinear over the cells (0.5 off scope); the static field, whatever gt.Mud.SoftSpots says. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|SoftSpots")
	float SoftnessAt(FVector2D XYCm) const;
	/**
	 * MR4: the scales a wheel on this patch's Mud or Bog row takes at a world XY (UGTTractionComponent, on top of the variant's):
	 * X the SinkScale, lerp(0.75, 1.5, S) / SoftMeanSink, on the sinkage's cap and rate; Y the FrictionScale, lerp(1.05, 0.9, S) /
	 * SoftMeanFriction. Exactly (1, 1) off scope and with gt.Mud.SoftSpots 0.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|SoftSpots")
	FVector2D SoftScalesAt(FVector2D XYCm) const;
	/** MR4: S x 255 per cell, row-major (Y then X), CellsX x CellsY; empty off scope (the check's CPU maps). */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|SoftSpots")
	TArray<uint8> GetSoftnessBytes() const;
	/** MR4: the layer texture's texels as last written (two bytes a cell: R the bog layer, G S x 255 or 0). */
	const TArray<uint8>& GetLayerBytes() const { return LayerBytes; }
	/** MR4: gt.Mud.SoftSpots applied - the scales on (or exactly 1) and the layer's G re-uploaded (S, or 0 when off). The tick calls it when the switch flips. */
	void ApplySoftSwitch(bool bOn);
	bool IsSoftOn() const { return bSoftOn; }
	/**
	 * MR4, the generator: S per cell of a SizeX x SizeY grid of CellCm cells from OriginCm (world cm), deterministic from Seed.
	 * Two octaves of hashed smooth noise at 7 m and 3 m (0.65 / 0.35), domain-warped by a 9 m noise of 1.5 m; remapped by the
	 * percentiles of its interior (the cells at least 2 m from the edge), piecewise-linear (min 0, p5 0.15, p75 0.6, p95 0.9,
	 * max 1); the amplitude about 0.5; the rim S = lerp(0.4, S, smoothstep(0.5 m, 2.0 m, d)), d the distance to the nearest edge.
	 */
	static void BuildSoftness(TArray<float>& Out, int32 SizeX, int32 SizeY, float CellCm, const FVector2D& OriginCm, int32 Seed, float Amplitude);
	/** MR4: the generator's seed for a section (deterministic: the same section, the same S). */
	static int32 SoftSpotSeed(int32 InSectionIndex) { return 104729 * (InSectionIndex + 1) + 17; }
	static float SoftSinkLerp(float S) { return FMath::Lerp(0.75f, 1.5f, S); }
	static float SoftFrictionLerp(float S) { return FMath::Lerp(1.05f, 0.9f, S); }

	// ---- MudRunner MR5, breakable mud chunks (docs/MUDRUNNER_LESSONS_PLAN.md MR5 execution block) -----------------------
	// Chunks are the firm crust and soft spots the soup: placed at Init where MR4's S is low near the route line, one simulated
	// rigid body each, asleep until touched. The wheels' suspension traces ignore them (AGTCarPawn), so a wheel never rides up
	// on one: a wheel whose stamp footprint reaches a chunk breaks it. The chassis bumps and pushes them, and breaks one over
	// ChunkBreakImpulse; one that lands at over ChunkBreakLandCmPerS breaks. A break leaves 3-5 LM2c clods (Source 5) and a
	// lump dome of the chunk's exact volume (DepositLumpDome, DepositThrown's dome). Scope as MR4 (HasSoftSpots: a Mud-medium
	// bog without a profile). gt.Mud.Chunks 0 removes them and deposits nothing (the field's CRC is untouched).
	/** The chunks' collision object type, unused elsewhere in the project; the car's wheel traces ignore it (AGTCarPawn). */
	static constexpr ECollisionChannel MudChunkChannel = ECC_Destructible;
	/** Why a chunk broke: a wheel's footprint, the chassis' impulse, a hard landing, or a test. */
	enum class EMudChunkBreak : uint8 { Wheel, Impulse, Landing, Test };
	/** A planned chunk (PlanMudChunks): its centre, its size (across), its yaw, its tilt about a horizontal axis, its mesh number. */
	struct FMudChunkPlan
	{
		FVector2D XYCm = FVector2D::ZeroVector;
		float SizeCm = 20.f;
		float YawDeg = 0.f;
		float TiltDeg = 0.f;
		float TiltAxisDeg = 0.f;
		int32 Mesh = 0;      // 0-1 rounded, 2-3 slab, 4 broken, 5 smear (MudChunkFamilyOf)
		int32 Cell = INDEX_NONE;
		bool bCluster = false;
	};
	/** The candidate cells' density, chunks per m^2 (1 per 25 m^2), times MudChunkDensityScale. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkDensityPerM2 = 0.04f;
	/** The variant's multiplier on the density (FGTDeformProfile::ChunkDensityScale, ApplyProfile: Firm 0.5, Deep 1.5, Stony 1; Standard 1). Before Init. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkDensityScale = 1.f;
	/** Candidate cells: within this of the section's route line, at least MudChunkRimCm from the patch's rim, S at most MudChunkMaxSoftness. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkRouteCm = 600.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkRimCm = 150.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkMaxSoftness = 0.55f;
	/** Clustering: a hashed MudChunkClusterCm noise marks MudChunkClusterShare of the candidate area as cluster ground, MudChunkClusterDensity x there and MudChunkSparseDensity x elsewhere (renormalised: the count is the target). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkClusterCm = 400.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkClusterShare = 0.35f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkClusterDensity = 2.5f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkSparseDensity = 0.2f;
	/** Sizes (across, cm): min + (max - min) u^power, so most are small (u stratified over the patch's chunks, in a hashed order). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkSizeMinCm = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkSizeMaxCm = 50.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkSizePower = 2.2f;
	/** Random yaw; tilted up to this either way off the ground's normal. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkTiltDeg = 12.f;
	/** Spacing: centres at least r1 + r2 + this apart (r half the size). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkGapCm = 5.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MaxMudChunks = 48;
	/** The families' weights: rounded, slab, broken, smear. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	FVector4 MudChunkFamilyWeights = FVector4(0.3, 0.35, 0.2, 0.15);
	/** Mass = clamp(this x the volume in litres, min, max) kg. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkKgPerL = 1.6f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkMassMinKg = 10.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkMassMaxKg = 40.f;
	/** The chassis breaks a chunk with a normal impulse over this, kg cm/s (500 N s); below it the chunk is pushed. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float ChunkBreakImpulse = 50000.f;
	/** A chunk that hits the ground (WorldStatic) at over this, cm/s (the hit's impulse over its mass), breaks. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float ChunkBreakLandCmPerS = 400.f;
	/** A wheel breaks a chunk whose footprint circle (this x its size, radius) its stamp capsule overlaps. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkFootprint = 0.4f;
	/** A break: the dome's radius (x the size), MudChunkClodsMin..Max clods of MudChunkClodSizeMin..Max x the size, within MudChunkClodScatter x the size. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkDomeRadius = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkClodsMin = 3;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkClodsMax = 5;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkClodSizeMin = 0.25f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkClodSizeMax = 0.45f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkClodScatter = 0.6f;
	/** A chunk more than this under the landscape at its XY is removed, its volume logged as lost. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkLostCm = 100.f;
	/** The wheels' coarse grid over the patch, cm a cell. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkGridCm = 200.f;
	/** The chunk meshes (Art/Unreal/import_mud_chunks.py), this prefix with 0..5, and their material (M_GT_Clod's path, Art/Unreal/live_mud_style.py). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	FString MudChunkMeshPrefix = TEXT("/Game/GrandTour/Mud/Chunks/SM_GT_MudChunk_");
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	FString MudChunkMaterialPath = TEXT("/Game/GrandTour/Materials/M_GT_MudChunk.M_GT_MudChunk");
	/** The chunks' M_GT_MudChunk instance with this patch's MudVariant (null on Standard: the material itself). */
	UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	TObjectPtr<UMaterialInstanceDynamic> MudChunkMaterialInstance;
	/** MR5 readouts: meshes found, the plan (candidate area m^2, the target, planned), live and spawned (no ground under: skipped), breaks by trigger, lost, switched off, the volume deposited and lost (cm^3), awake now and the peak, the clods from breaks, the largest chassis impulse and landing speed seen. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkMeshCount = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkCandidateM2 = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkTarget = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunksPlanned = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunksLive = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunksSpawned = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunksNoGround = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkBreaksWheel = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkBreaksImpulse = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkBreaksLanding = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkBreaksTest = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunksLost = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunksSwitchedOff = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	double MudChunkDepositedCm3 = 0.0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	double MudChunkLostCm3 = 0.0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkAwakeNow = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 MudChunkAwakePeak = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	int32 ClodsFromChunk = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkMaxChassisImpulse = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Chunks")
	float MudChunkMaxLandCmPerS = 0.f;
	/** MR5: the section's route line (world cm, every 2 m from its start to its end: the line MR4's wheel-path share used); UGTMudSubsystem::BuildPatches sets it before Init. */
	void SetRouteLine(const FGTTerrainSpec& Spec, const FGTRouteSection& Section);
	const TArray<FVector2D>& GetRouteLine() const { return RouteLineCm; }
	/** MR5: the distance from a world XY to the route line, cm (a big number without one). */
	float DistanceToRouteCm(const FVector2D& XYCm) const;
	/** MR5: the chunks' seed for a section (deterministic: the same section, the same chunks). */
	static int32 MudChunkSeed(int32 InSectionIndex) { return 7919 * (InSectionIndex + 1) + 3301; }
	static int32 MudChunkFamilyOf(int32 MeshNo) { return MeshNo <= 1 ? 0 : (MeshNo <= 3 ? 1 : (MeshNo == 4 ? 2 : 3)); }
	static constexpr int32 MudChunkMeshVariants = 6;
	/**
	 * MR5, the placement (deterministic from MudChunkSeed): the candidate cells (route line, rim, S; bUntouchedOnly also the field
	 * still 0 there, for gt.Mud.Chunks back at 1), the target count (their area x the density x MudChunkDensityScale, at most
	 * MaxMudChunks), each chunk on a candidate cell drawn by the cluster weights with the spacing kept, largest first. Returns the
	 * planned count; OutCandidateM2 and OutTarget take the area and the target. GR1: on a pre-churned patch only the cells within
	 * PreChurnChunkBandCm of the hummocked ground before the tracks (never an old rut or its bank), and "untouched" is against the
	 * pre-churned surface; bIgnorePreChurn plans as without it (the kept/moved count).
	 */
	int32 PlanMudChunks(TArray<FMudChunkPlan>& Out, bool bUntouchedOnly, float* OutCandidateM2 = nullptr, int32* OutTarget = nullptr, bool bIgnorePreChurn = false) const;
	/** MR5 (a): every chunk whose footprint circle the capsule FromCm-ToCm of HalfWidthCm overlaps breaks (UGTTractionComponent::StampMud, per wheel in contact). Returns the breaks. */
	int32 BreakMudChunksUnderWheel(const FVector2D& FromCm, const FVector2D& ToCm, float HalfWidthCm);
	/** MR5: one chunk broken where it lies: its volume into the field as a dome, 3-5 clods. Returns the clods spawned (-1: not alive). */
	int32 BreakMudChunk(int32 Index, EMudChunkBreak Why);
	/** MR5 (b, c): a chunk's physics hit - the chassis (ECC_Vehicle) over ChunkBreakImpulse, or the ground (ECC_WorldStatic) at over ChunkBreakLandCmPerS. */
	UFUNCTION()
	void OnMudChunkHit(UPrimitiveComponent* HitComponent, AActor* OtherActor, UPrimitiveComponent* OtherComponent, FVector NormalImpulse, const FHitResult& Hit);
	/** MR5: gt.Mud.Chunks applied - 0 every chunk removed (nothing deposited), 1 placed anew on untouched ground. The tick calls it when the switch flips. */
	void ApplyMudChunkSwitch(bool bOn);
	bool IsMudChunksOn() const { return bMudChunksOn; }
	/** MR5, for the tests: a chunk at a world location (its pivot, the hull's bottom), upright, of a size and mesh; asleep or awake. Returns its slot (INDEX_NONE without the mesh). */
	int32 SpawnMudChunkForTest(const FVector& LocationCm, float SizeCm, int32 MeshNo, bool bAsleep);
	/** MR5 slots (live or pooled) and a slot's state, for the tests, the subsystem's awake cap and the checks. */
	int32 NumMudChunkSlots() const { return MudChunks.Num(); }
	bool IsMudChunkAlive(int32 Index) const { return MudChunks.IsValidIndex(Index) && MudChunks[Index].bAlive; }
	UStaticMeshComponent* GetMudChunkComponent(int32 Index) const { return MudChunkComponents.IsValidIndex(Index) ? MudChunkComponents[Index].Get() : nullptr; }
	FVector2D MudChunkXY(int32 Index) const { return MudChunks.IsValidIndex(Index) ? MudChunks[Index].XYCm : FVector2D::ZeroVector; }
	float MudChunkSize(int32 Index) const { return MudChunks.IsValidIndex(Index) ? MudChunks[Index].SizeCm : 0.f; }
	float MudChunkVolumeCm3(int32 Index) const { return MudChunks.IsValidIndex(Index) ? MudChunks[Index].VolumeCm3 : 0.f; }
	float MudChunkMassKg(int32 Index) const { return MudChunks.IsValidIndex(Index) ? MudChunks[Index].MassKg : 0.f; }
	int32 MudChunkMesh(int32 Index) const { return MudChunks.IsValidIndex(Index) ? MudChunks[Index].Mesh : INDEX_NONE; }
	/** The lowest point of a chunk's hull in the world now, Z cm (its pivot's Z without a hull). */
	float MudChunkLowestHullZ(int32 Index) const;
	bool IsMudChunkAwake(int32 Index) const;
	double MudChunkAwakeSince(int32 Index) const { return MudChunks.IsValidIndex(Index) ? MudChunks[Index].AwakeSinceS : -1.0; }
	/** Puts one chunk to sleep (the subsystem's awake cap). */
	void SleepMudChunk(int32 Index);
	/** A chunk mesh's volume at its across (cm^3, UGTMudChunkData's; the hull's without it) and its across (cm); 0 without the mesh. */
	float MudChunkMeshVolumeCm3(int32 MeshNo) const { return MudChunkMeshVolume.IsValidIndex(MeshNo) ? MudChunkMeshVolume[MeshNo] : 0.f; }
	float MudChunkMeshAcrossCm(int32 MeshNo) const { return MudChunkMeshAcross.IsValidIndex(MeshNo) ? MudChunkMeshAcross[MeshNo] : 0.f; }
	/** MR5, for the check: per live chunk (X, Y world cm, size cm, 1 awake / 0 asleep). */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|Chunks")
	TArray<FVector4> GetMudChunksForCheck() const;
	/** MR5, for the check: the readouts as one JSON object. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud|Chunks")
	FString DescribeMudChunks() const;
	/** MR5: the dome DepositThrown and a chunk's break share - DomeRadiusCm, exactly VolumeCm3 into LumpCm (over LumpMaxCm into HeightCm in the same cell), timed with the stamps and recorded as EventKind with RecordRadiusCm. Returns the volume put down (0 outside the field). */
	double DepositLumpDome(uint8 EventKind, const FVector2D& XYCm, double VolumeCm3, float RecordRadiusCm, float DomeRadiusCm);
	/** LM1, for the drive check: the field back to untouched ground (its numbers kept) and the whole of it uploaded, so two crossings can be measured on fresh mud in one session. */
	void ResetFieldForTest();

	// ---- LM4e (docs/LIVING_MUD_PLAN.md LM4e): the record and the replay ----------------------------------------------
	/** Starts a record on a reset field (the reset and the first event in the same call, so a replay from a reset is exact), or stops it. */
	void SetRecording(bool bOn);
	bool IsRecording() const { return Field.EventLog != nullptr; }
	TArray<FGTMudField::FEvent>& GetRecord() { return RecordLog; }
	/**
	 * Replays the record onto a reset field: bAllAtOnce, every frame of it now (each frame's upload and clod batch as the drive
	 * had them), else one recorded frame per tick from the next one on (its clock and settle in place of the tick's own), so
	 * Settle and the upload measure the drive's own work. Returns the events.
	 */
	int32 StartReplay(bool bAllAtOnce);
	bool IsReplaying() const { return ReplayCursor < ReplayLog.Num(); }
	/** HeightCm and LumpCm's CRC (the replay's check against the record's end). */
	uint32 FieldCrc() const;
	/** The record's end: the field's CRC when the record stopped. */
	uint32 RecordEndCrc = 0;
	/** LM4e readouts: the last frame's stamp time (the field's outside calls), the tiles swept and listed by its settle, the cells its upload wrote. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float LastStampMs = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	int32 LastSweptTiles = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	int32 LastListedTiles = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	int32 LastUploadCells = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	FVector2D BoundsMin = FVector2D::ZeroVector;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	FVector2D BoundsMax = FVector2D::ZeroVector;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 CellsX = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 CellsY = 0;

	/** Texture uploads so far (one per tick the field changed). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 UploadCount = 0;

	/** The field as a texture: R height (m), GB offset (m), A tracks. The mud material reads it. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	TObjectPtr<UTexture2D> Texture;

	/** Stage F: the tread as a texture (R the stamping wheel's heading in turns, G the lug phase in turns of LugPeriodCm), uploaded with the field's own dirty rects. M_GT_Mud reads it as MudTread. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	TObjectPtr<UTexture2D> TreadTexture;

	/** The landscape layer under each cell (R: 1 Bog, 0 Mud), baked once by BakeLayers; the mud material matches the ground with it. MR4: PF_R8G8, G the softness S (0 off scope or with gt.Mud.SoftSpots 0). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	TObjectPtr<UTexture2D> LayerTexture;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 BogCells = 0;

	/** Stage B: the grid mesh (no collision, no shadow) and its M_GT_Mud instance carrying this patch's texture and bounds. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	TObjectPtr<UProceduralMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	TObjectPtr<UMaterialInstanceDynamic> MeshMaterial;

	/** Stage G: the water grid over the same vertices, translucent, sorted above the mud mesh; M_GT_MudWater draws only the cells the field has cut below the table. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	TObjectPtr<UProceduralMeshComponent> WaterMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	TObjectPtr<UMaterialInstanceDynamic> WaterMaterial;

	/** The mesh's vertex spacing (the field's cell, so a 25 cm tyre's rut gets its own vertices; 25 until 2026-09-15, which drew the ridges as lumps) and how far above the ground its vertices rest. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float MeshCellCm = 12.5f;

	/** How far over the ground the mesh rests. 0 since the hole is the whole box (stage D): the mesh is the ground, so it sits on it. 2 until 2026-09-15, and from eye height a ray under the mesh's edge landed inside the hole on nothing (a thin dark line along the deformed region's edge). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float MeshLiftCm = 0.f;

	/** The outermost vertex ring's lift over the ground, fading to 0 at the second ring: the overlap ring between the hole's inset edge and the box edge sits this far over the landscape, so it cannot z-fight and any crack the landscape's LOD opens at the border shows mud, not sky. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float EdgeLipCm = 0.1f;

	/** Stage F: the tyre's lug spacing, cm of rolled distance per lug (about 11 lugs a metre under a 25 cm tyre with no slip). The field carries the phase, M_GT_Mud draws the bump; both take this number from here. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float LugPeriodCm = 9.f;

	// ---- stage G, water in the ruts (docs/MUD_ONE_SURFACE_PLAN.md section 3) -----------------------------------

	/** Where this bog's water table stands, cm relative to the undisturbed ground under each point (negative: below it). UGTMudSubsystem takes it from the Mud section's own WaterTableCm before Init; -25 since stage J3 (the user asked for the waterline lowered by about half) puts about 5 cm of water in a 30 cm rut and leaves untouched mud dry. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float WaterTableCm = -25.f;

	/** How far the weather's ground wetness lifts that table, cm at wetness 1 - the ford sheet's own RiseWithWetnessCm is 80, and a bog's table is a hand's width, not a river's. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float WetTableLiftCm = 15.f;

	/** The lift the weather is applying now, cm (the mesh is moved by it and the material told; CurrentWaterTableCm is the sum). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float WaterLiftCm = 0.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 WaterVertexCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 WaterTriangleCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	bool bWaterMaterialLoaded = false;

	/** The water master, by path at runtime (Art/setup_m6_water.bat builds it; without it there is no water grid at all). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	FString WaterMaterialPath = TEXT("/Game/GrandTour/Materials/M_GT_MudWater.M_GT_MudWater");

	/** Stage H, less spiky ruts: a new hump is blended into a ridge cell by max plus this fraction of the lesser, not summed (1.0 is the sum of stage F; 0.8 cost the crest a fifth of its height). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeBlend = 0.9f;

	/** Stage H: how far a stamp's own cells are pulled toward a 3-tap mean along its direction, in proportion to how far the stroke rolled over the tyre's width (the crest stops being a row of humps, the floor loses its steps). 0.7: 0.5 left the crest's difference sd at 0.54 cm where half of 0.94 was asked. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeSmooth = 0.7f;

	/** Stage H, randomness: the ridge's return and the tracks' edge vary by this much either way across the cells, in clumps of 4 cells (a hash of the cell, no state). 0.7: 0.35 left the crest's coefficient of variation at 0.12, the same as with stage H off. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeNoise = 0.7f;

	/** Stage H: the rut floor's target varies by this many cm at a 4-6 cell wavelength. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float FloorNoiseCm = 1.5f;

	// ---- stage I, a mud-like shape (docs/MUD_ONE_SURFACE_PLAN.md section 3; the user on foot after F and H: "still
	// very sharp and uniform. It needs to be more mudlike"). All of them are pushed into the field in Init and logged.

	/** Stage I1: the band the returned volume spreads over, 40 until stage I. Wide and low instead of a knife edge. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeWidthCm = 90.f;

	/** Stage I1: the ceiling on a bank's height, 25 until stage I. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float MaxRidgeCm = 12.f;

	/** Stage I1: the plateau's flanks - the weight rises over this many cm, holds flat, and its outer foot fades over the last this many. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeFootCm = 30.f;

	/** Stage I2: the two wavelengths along the rut, the height's swing over them (measured: 250 / 600 / 1.0, not the plan's 120 / 300 / 0.5 - the smoothing is a 27 cm low-pass, see FGTMudField) and the width's own swing. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeWaveCm = 250.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeWaveLongCm = 600.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeWave = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeWidthWave = 0.5f;

	/** Stage I2: one side of each tyre throws this much more than the other; which side is chosen by a 1 m noise. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeSideBias = 0.3f;

	/** Stage I2: the share of the rut's length whose bank slumps back in by half, in stretches of 40-80 cm, and how much of what falls settles on the floor. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeSlump = 0.25f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeSlumpFloor = 0.333f;

	/** How much of the rut under it a slump may fill: uncapped it took the escape's rut mean -32.1 -> -28.5 cm, and at 3 the bog's middle run sank the body 8 cm where 8 is asked (the rears drive on the filled floor). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeSlumpRiseMaxCm = 1.f;

	/** Stage I1: how much of a bank's deposit a cell that is already a rut takes (the 90 cm band reaches over the next pass's rut; at 1.0 the escape's rut mean read -27.3 cm against -32.1 before stage I). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeFillShare = 0.35f;

	/** Stage I2: the share of the band's cells carrying a clod (half the local bank again) and how big a clod is across. LM2a: 0 with the lumps on (stage I's 0.15 clods were under two cells and smoothed away); the code path stays. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float ClodChance = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float ClodMinCm = 8.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float ClodMaxCm = 15.f;

	// ---- LM1, the living field (docs/LIVING_MUD_PLAN.md): the settle numbers, pushed into the field in Init. A ford's
	// profile is stiffer (FGTDeformProfile). gt.Mud.Settle 0 stops the settling (the field is then exactly as stamped).

	/** The angle a wall slumps to, degrees: steeper than the traction's RutHoldMaxSlope (tan 38 = 0.78 > 0.5), so a slumped wall still holds a tyre. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float ReposeDeg = 38.f;

	/** How fast a step over the repose slumps, 1/s (of the excess). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float SlumpRate = 2.f;

	/** LM1's ooze, a diffusion of the whole step while fresh mud sets, 1/s. 0 since LM1b (the relax below gives the recovery): it is a blur, and at LM1's 1.2 the owner found the mud "too smooth". Kept so the two can be compared. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float OozeRate = 0.f;

	/** LM1b: the share of every set cell's height a whole set gives back (a rut cell rises, a bank cell sinks, each by its own height: the shape scales, it does not blur). The rut rises only by what the banks give up (the field balances the two over the patch), and the banks hold about 35-38 % of a rut's volume, so the rut comes back about 0.38 x this. Bog 0.4 (the main session's revision of the plan's 0.2, which gave 7.6 %), a ford's bed 0.02. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float RecoverShare = 0.4f;

	/** LM1b: the clay's texture creeps down the surface's slope by this many cm per cm a cell's height moved in the relax (capped at MaxSlideCm), shown through the material's SlideUV. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float CreepCmPerCm = 3.f;

	/** How long a stamped cell keeps oozing, s; then the mud has set. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float SetSeconds = 4.f;

	/** The texture's drag where mud moved, cm of offset per cm of height moved (capped at the field's MaxSlideCm). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float SmearCmPerCm = 0.5f;

	/** How long the fresh sheen takes to fade, s. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float FreshFadeS = 6.f;

	/** A tile is still when no cell in it moves faster than this, cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float SleepCmPerS = 0.05f;

	/** LM1 readouts: the last frame's Settle (ms, sub-steps, awake tiles) and Upload (ms), for the check script through UGTMudSubsystem. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float LastSettleMs = 0.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	int32 LastSettleSteps = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	int32 LastAwakeTiles = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float LastUploadMs = 0.f;

	/** LM2a housekeeping 1: a cell is fresh when its surface moves more than this in one stamp or sub-step (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Settle")
	float FreshMinCm = 0.002f;

	// ---- LM2a, lumps in the field and the wheel's throw (docs/LIVING_MUD_PLAN.md LM2a): pushed into the field in Init,
	// copied from FGTDeformProfile by ApplyProfile. Proposed starting points, the bog's (snow comes later).

	/** The share of a stamp's bank deposit held back from the bank and spread over the band's lump domes (0: no lumps; stage I's ClodChance then stays the clumps). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpShare = 0.35f;

	/** The lump sites' grid, cells, and a dome's radius in cells (jittered +-40 % by site). 4 (50 cm), not the proposed 3 (37.5 cm): GrandTour.Mud.Lumps read the crest's coefficient of variation 1.15x LumpShare 0's at 3 and 1.59x at 4 (asked at least 1.5x). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpSpacingCells = 4.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpRadiusCells = 1.6f;

	/** The most lump a cell holds, cm; the excess goes to HeightCm in the same cell. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpMaxCm = 10.f;

	/** The share of the bank's deposit a wheel at full spin throws instead (the traction maps its slip to 0..this). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float ThrowMax = 0.5f;

	/**
	 * LM2a: a thrown blob came down at XY inside this patch: a dome of 1.5 x RadiusCm into the field's lumps with exactly
	 * VolumeCm3, its tile woken and its cells fresh; LM2b: with ClodThrowChance a clod of the blob's size (2 x RadiusCm)
	 * is queued there. Returns the volume put down (0 outside the field).
	 */
	double DepositThrown(const FVector2D& XYCm, double VolumeCm3, float RadiusCm);

	/** LM2a readouts (the check script): what the throw returned from this field's stamps, what came back down on it, and the lumps the capsules flattened, cm^3. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	double ThrowReturnedCm3 = 0.0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	double ThrowDepositedCm3 = 0.0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	int32 ThrowDeposits = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	double LumpFlattenedCm3 = 0.0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	double LumpLandedCm3 = 0.0;

	// ---- LM2b, clods on the banks and from the throw (docs/LIVING_MUD_PLAN.md LM2b). gt.Mud.Clods 0 hides them and
	// stops spawning. Without a clod mesh (SM_GT_Clod_0..4 not imported) nothing is drawn and the queue is dropped.

	/** The most clods this patch keeps; a new one replaces the oldest. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 MaxClods = 1200;

	/** A bank lump site rolls this when its dome has taken ClodBankMinCm since its last roll, at most once per ClodRespawnS. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodBankChance = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodRespawnS = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodBankMinCm = 2.f;

	/** A bank clod is ClodBankMinSizeCm..ClodBankMaxSizeCm across, larger with the stamp's depth. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodBankMinSizeCm = 6.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodBankMaxSizeCm = 16.f;

	/** A thrown blob's landing spawns a clod of its size with this chance (LM2b 0.5; LM2c 0.2, which left 768 clods live after the dry crossing; the follow-up's 0.065 is tuned for 300-350). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodThrowChance = 0.065f;

	/** A new clod sits ClodSinkIn..ClodSinkInMax of its own height in the surface, by a hash (LM2c; LM2b's 0.35 alone), the flat face down. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodSinkIn = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodSinkInMax = 0.75f;

	/** Its tilt off the local surface normal, degrees either way (LM2c: 35 from the normal; LM2b's 25 from straight up). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodTiltDeg = 35.f;

	// ---- LM2c, break the uniformity (docs/LIVING_MUD_PLAN.md LM2c). bLumpVariety 0 is LM2a/LM2b's lumps and bank clods.

	/** LM2c: the lump sites jittered over their whole cell, a 150 cm cluster noise leaving 35 % of them out in patches, skewed amplitudes, elliptical domes and satellites; the bank clods from random lip cells. Off: LM2a/LM2b exactly. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	bool bLumpVariety = true;

	/** LM2c bank clods: the chance per cm a lip cell takes in one stamp at the cluster's full weight (landed for about a third of LM2b's count per metre of stroke), on the band's inner ClodBankInner beside the rut, ClodBankSizeMinCm..ClodBankSizeMaxCm across by a power law (min + (max - min) u^ClodSizePower). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodBankPerCm = 0.017f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodBankInner = 0.4f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodBankSizeMinCm = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodBankSizeMaxCm = 18.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodSizePower = 2.5f;

	/** LM2c placement: the scale on top of the size, X and Y each ClodScaleXYMin..Max, Z ClodScaleZMin..Max. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodScaleXYMin = 0.7f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodScaleXYMax = 1.4f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodScaleZMin = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodScaleZMax = 1.2f;

	/** LM2c: M_GT_Clod's freshness (PerInstanceCustomData 0), static: a throw's clod and a bank clod. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodFreshThrow = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodFreshBank = 0.3f;

	/** LM2c cost: the wet sinking re-pushes a clod only when it has moved this far since its last push, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodRepushCm = 0.2f;

	/** On Bog cells, or anywhere at wetness over 0.5, a clod sinks this x wetness cm/s and goes at 90 % of its height under. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodSinkCmPerS = 0.3f;

	/** A clod whose surface fell this far under a just-stamped cell (a new capsule) is squashed: removed, its volume already in the field. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodSquashCm = 3.f;

	/** The re-snap, squash and sinking run in batches this many times a second, one render-state dirty per batch. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodBatchHz = 5.f;

	/** The clods' draw distance, cm: they fade from the first to the second. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodCullStartCm = 4000.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float ClodCullEndCm = 6000.f;

	/** The clod meshes, by path at runtime: this prefix with 0..9 (LM2c's ten in four families, Art/Unreal/import_mud_clods.py), and their material (Art/Unreal/live_mud_style.py). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	FString ClodMeshPrefix = TEXT("/Game/GrandTour/Mud/Clods/SM_GT_Clod_");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	FString ClodMaterialPath = TEXT("/Game/GrandTour/Materials/M_GT_Clod.M_GT_Clod");

	/** LM2b readouts: clod meshes found, live clods, spawned by source, removed by fate, dropped (no mesh / switched off), the last frame's clod update ms. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 ClodMeshCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 ClodsLive = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 ClodsFromBank = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 ClodsFromThrow = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 ClodsFromTest = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 ClodsSquashed = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 ClodsSunk = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 ClodsRecycled = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	int32 ClodsDropped = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Clods")
	float LastClodMs = 0.f;

	/** LM2b, for the GPU cost at the cap: Count clods at seeded random spots over the box (source "test"). Returns how many were added (0 without a mesh). */
	int32 FillClodsForTest(int32 Count);
	/** LM2b: the Bog layer under a world XY, 0..1 (BakeLayers' CPU copy; 0 outside). */
	float BogAt(const FVector2D& XYCm) const;

	// ---- LM3a housekeeping 3: the field's own numbers before LM3a, now the patch's (and a profile's), pushed in Init ----
	/** The share of a stamp's cut that comes back up beside it (snow 0.2: it compacts). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RidgeReturn = 0.6f;
	/** The rut wall's width and the fewest cells it spans (mud 45 / 2; snow 10 / 1, a near-vertical wall). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RutShoulderCm = 45.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RutShoulderMinCells = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float RutDepthVariation = 0.35f;
	/** LM2c's lump variety numbers (bLumpVariety stays the master switch), the field's as LM2c shipped them. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpAbsentShare = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpClusterCm = 150.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpAmpMin = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpAmpMax = 1.6f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpAspectMax = 2.2f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpVarietyRadiusJitter = 0.6f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpSatelliteChance = 0.2f;

	// ---- LM3a, snow (docs/LIVING_MUD_PLAN.md LM3a): a Snow section's patch (FGTTerrainSpec::SnowProfile) ------------
	/** Mud, or Snow: the mesh rests SnowTopCm over the ground, the field is relative to the snow top, the tyres cut to their own bottom, the belly ploughs, it refills while it snows, no rut water, M_GT_Snow and M_GT_Clod_Snow. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	EGTDeformMedium Medium = EGTDeformMedium::Mud;
	bool IsSnow() const { return Medium == EGTDeformMedium::Snow; }
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SnowDepthCm = 35.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SnowEdgeCm = 300.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float PloughReturn = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float PloughBandCm = 40.f;
	/** LM3c follow-up: the plough berm's lump share (the profile's PloughLumpShare). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float PloughLumpShare = 0.25f;
	/** LM3c follow-up: the berm's share of the bank's height swings (the profile's PloughBankVariation). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float PloughBankVariation = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float RefillCmPerMin = 2.f;
	/** The traction's plough drag coefficient for the uncut snow ahead of a tyre (UGTTractionComponent reads it here). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SnowPlough = 0.35f;
	/** LM3b: the scale on the belly's drag in snow (UGTTractionComponent reads it here; 1 is LM3a's). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SnowBellyDrag = 1.f;
	/** The refill's pass rate, Hz (the plan's 1 Hz: one whole-field pass and one full upload). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float RefillHz = 1.f;

	// ---- LM4, God of War snow deformation (docs/LIVING_MUD_PLAN.md LM4): the profile's numbers, pushed in Init. Every
	// default is the value in force before LM4 (mud's), so a bog and a ford's bed are unchanged. ---------------------------
	/** Item 1: the cell-unit numbers the field had of its own (the profile states them at its CellCm): stage H's clumps, the settle tile, the floor noise's, the pockets' and the tracks' edge's wavelengths, in cells. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Grid")
	float RidgeNoiseCells = 4.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Grid")
	int32 SettleTileCells = 16;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Grid")
	float FloorNoiseCells = 5.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Grid")
	float PocketNoiseCells = 12.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Grid")
	float TracksEdgeCells = 3.f;
	/** Item 1 readout: the field's cell, cm, as built (the profile's CellCm, or 12.5 with gt.Snow.FineGrid 0 on snow). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Grid")
	float FieldCellCm = 12.5f;
	/** Item 2 (snow): crust plates (FGTMudField::bLumpPlates) tilted PlateTiltMinDeg..PlateTiltMaxDeg. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	bool bLumpPlates = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float PlateTiltMinDeg = 5.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float PlateTiltMaxDeg = 25.f;
	/** Item 3 (snow): the stepped wall line and the lip plates that fall in (FGTMudField's numbers; WallStepMaxCm 0 is off). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallStepMinCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallStepMaxCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallSegMinCm = 15.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallSegMaxCm = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallDropShare = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float FloorChunkChance = 0.f;
	/** Item 6 (snow): the uneven snow top's sd (cm) and wavelengths (FGTMudField::SnowTopNoiseCm; 0 is flat). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SnowTopUndulationCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SnowTopWaveMinCm = 60.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SnowTopWaveMaxCm = 300.f;
	/**
	 * Item 4 (snow): the snow shards (Art/Blender/build_snow_chunks.py, Art/Unreal/import_snow_chunks.py), this prefix with
	 * 0..7; a snow patch draws them in place of the clods when they exist (the clods otherwise), M_GT_Clod_Snow on them.
	 * Placement: the yaw along the lip (the spawn's heading) +- ShardYawSpreadDeg (random where a spawn has none), tilted
	 * ShardTiltMinDeg..ShardTiltMaxDeg off the local surface normal, sunk ShardSinkMin..ShardSinkMax of its height, scaled to
	 * the spawn's size over the mesh's own across (+-ShardScaleJitter each way).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	FString SnowChunkPrefix = TEXT("/Game/GrandTour/Mud/SnowChunks/SM_GT_SnowChunk_");
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float ShardYawSpreadDeg = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float ShardTiltMinDeg = 10.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float ShardTiltMaxDeg = 40.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float ShardSinkMin = 0.2f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float ShardSinkMax = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float ShardScaleJitter = 0.15f;
	/** Item 4 readouts: whether this patch draws shards, and the floor chunks spawned (a lip plate fallen in; Source 3). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	bool bShards = false;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 ClodsFromFloor = 0;
	/** Item 3 readouts from the field: the lip-plate drops, the volume they moved to the floor (cm^3), and the chunks the field queued (lip and floor). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 WallDrops = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	double WallDropCm3 = 0.0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 LipChunksQueued = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 FloorChunksQueued = 0;
	/** Item 1, gt.Snow.FineGrid 0: every cell-unit number scaled by Factor (the profile's CellCm / 12.5), so each keeps its size in cm on the coarser grid. */
	void ScaleCellUnits(float Factor);
	// ---- LM4b, soft shape and crumbly detail (docs/LIVING_MUD_PLAN.md LM4b): the profile's numbers, pushed in Init. The
	// defaults are off (mud's), so a bog and a ford's bed are unchanged. ---------------------------------------------------
	/** Item 1 (snow): the wall line's continuous waves (FGTMudField::WallWave*; both amplitudes 0: none). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallWaveCm = 25.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallWaveLongCm = 70.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallWaveAmpCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallWaveLongAmpCm = 0.f;
	/** Item 2 (snow): the notch's feather (cells), and the soft domes (FGTMudField::bLumpSoftDomes, their skew and height per radius). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallDropFeatherCells = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	bool bLumpSoftDomes = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpSkewMinDeg = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpSkewMaxDeg = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpHeightPerRadius = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpCapAmpPower = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lumps")
	float LumpCapRadiusPower = 0.f;
	// ---- LM4c, piles not walls (docs/LIVING_MUD_PLAN.md LM4c): the profile's numbers, pushed in Init (off by default: mud's) --
	/** Item 1 (snow): the talus per cell (FGTMudField::bCellRepose: loose above the top and on a pile, the wall's 40-80 deg below). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	bool bCellRepose = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float LooseReposeDeg = 35.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallReposeDeg = 60.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallReposeRangeDeg = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallReposeWaveMinCm = 40.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float WallReposeWaveMaxCm = 80.f;
	/** Item 2 (snow): the delayed wall collapses (FGTMudField::Collapse*; CollapseChance 0: off). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float CollapseChance = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float CollapseSegMinCm = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float CollapseSegMaxCm = 80.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float CollapseDelayMinS = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float CollapseDelayMaxS = 3.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float CollapseTopMin = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float CollapseTopMax = 0.6f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float CollapseFeatherCells = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 CollapseClumpsMin = 1;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 CollapseClumpsMax = 2;
	/** Item 3 (snow): the plough's falling profile and the piles' cluster factor (1 / 1: off). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	bool bPloughFallingProfile = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float PileClusterMin = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float PileClusterMax = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float PileWaveMinCm = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float PileWaveMaxCm = 250.f;
	// ---- LM4d, the belly's channel (docs/LIVING_MUD_PLAN.md LM4d): the profile's numbers, pushed in Init (off by default) ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float BellyUndulationCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float BellyWaveMinCm = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float BellyWaveMaxCm = 60.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float BellyStretch = 2.5f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SmearChance = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SmearLaneCm = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SmearLengthMinCm = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SmearLengthMaxCm = 80.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SmearWidthMinCm = 8.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SmearWidthMaxCm = 15.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SmearHeightMinCm = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SmearHeightMaxCm = 3.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SmearClusterCm = 120.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float PloughSpillShare = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float SpillClumpChance = 0.f;
	/** LM4d readouts from the field: the smear ridges' and the spill's volume (cm^3), the spill's clumps queued; the clumps spawned from the channel (Source 4). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	double SmearCm3 = 0.0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	double SpillCm3 = 0.0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 SpillClumpsQueued = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 ClodsFromChannel = 0;
	/** Item 2 readouts from the field: collapses fired, the volume they moved (cm^3), the segments armed, the clumps queued on the piles. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 CollapsesFired = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	double CollapseCm3 = 0.0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 CollapseSegsArmed = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 CollapseClumpsQueued = 0;
	/**
	 * LM4c, the drive check's collapse pair: a tyre's cut (TyreWidthCm wide, SinkCm deep, 5 cm strokes) from FromCm to ToCm
	 * stamped now on this patch, and the collapse segments it armed: per segment the pile's spot on the floor (X, Y, world cm),
	 * its side (Z, +-1) and its delay (W, s). Empty on mud or with no collapse armed.
	 */
	TArray<FVector4> CutTrenchForTest(const FVector2D& FromCm, const FVector2D& ToCm, float TyreWidthCm, float SinkCm);
	/** Item 6, gt.Snow.Parallax: the value last pushed to the mesh material's SnowParallax, and the material's own default (read once; -2 not yet). */
	float PushedParallax = -2.f;
	float DefaultParallax = -2.f;
	float PushedFastPath = -2.f;    // LM4e cut 6: gt.Snow.FastMaterial onto SnowFastPath
	float DefaultFastPath = -2.f;
	/** The snow patch's materials, by path at runtime (Art/Unreal/live_snow_style.py); without them the mud ones, with a warning. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	FString SnowMaterialPath = TEXT("/Game/GrandTour/Materials/M_GT_Snow.M_GT_Snow");
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	FString SnowClodMaterialPath = TEXT("/Game/GrandTour/Materials/M_GT_Clod_Snow.M_GT_Clod_Snow");
	/** The snow top over the ground at a world XY, cm (0 on mud or outside). */
	float SnowTopCmAt(const FVector2D& XYCm) const { return Field.SnowTopAt(XYCm); }
	/** LM3a readouts: the refill's passes, whether it snowed at the last pass, the volume it put back (cm^3) and the last pass's ms. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	int32 RefillPasses = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	bool bRefilling = false;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	double RefilledCm3 = 0.0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	float LastRefillMs = 0.f;
	/** The belly's plough, cm^3: cut, put into the berms. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	double PloughedCm3 = 0.0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Snow")
	double PloughBermCm3 = 0.0;

	/** How far the material's displacement can take a vertex below and above its rest height: the render bounds carry it, or the mesh is culled when the camera looks along it. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float DisplaceDownCm = 40.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	float DisplaceUpCm = 25.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 MeshVerticesX = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 MeshVerticesY = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 MeshVertexCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 MeshTriangleCount = 0;

	/** Vertices with no landscape under them (put at the lowest ground found). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 MeshGroundMisses = 0;

	/** World bounds of the rest mesh (before the material's displacement). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	FBox MeshBounds = FBox(ForceInit);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	bool bMaterialLoaded = false;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	bool bDiagnostic = false;

	/** The mud master, by path at runtime (Art/setup_m6_mud.bat builds it). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	FString MaterialPath = TEXT("/Game/GrandTour/Materials/M_GT_Mud.M_GT_Mud");

	// ---- LM4e cut 4 (docs/LIVING_MUD_PLAN.md LM4e): the snow mesh in chunks with distance LODs (gt.Snow.MeshLod, read when the
	// mesh is built) -----------------------------------------------------------------------------------------------------
	/**
	 * A snow patch's surface as chunks of ChunkCells x ChunkCells field cells, each its own component (culled on its own) with
	 * three sections: every vertex of the patch's grid (LOD 0), every 2nd (LOD 1) and every 4th (LOD 2), a chunk's last row and
	 * column always kept so neighbours share their corners. Within LodNearCm of the camera a chunk draws LOD 0, within LodFarCm
	 * LOD 1, else LOD 2 (LodHysteresisCm either side of each). Where a coarser chunk meets a finer one the finer edge's middle
	 * vertices are not on the coarser edge, so every inner chunk edge hangs a skirt SkirtCm down (both chunks' skirts face out).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	int32 ChunkCells = 128;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	float LodNearCm = 2000.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	float LodFarCm = 4000.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	float LodHysteresisCm = 150.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	float SkirtCm = 40.f;
	/** The chunks (0: the one grid mesh), and per LOD how many chunks draw it now and the triangles drawn now. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	int32 ChunkCount = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	FIntVector ChunksAtLod = FIntVector::ZeroValue;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	int32 DrawnTriangles = 0;
	/** LM4e: the surface's material, shadow casting and visibility on the grid mesh and every chunk (the profiles' and the checks' switches). */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	void SetSurfaceMaterialForTest(UMaterialInterface* Material);
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	void SetSurfaceCastShadowForTest(bool bCast);
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	void SetSurfaceVisibleForTest(bool bVisible);
	/** LM4e: every chunk at one LOD (-1: by the distance again), for the seam check. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	void ForceChunkLodForTest(int32 Lod) { ForcedLod = Lod; }
	/**
	 * LM4f item 1 (gt.Snow.ShadowProxy, docs/LIVING_MUD_PLAN.md LM4f): per chunk a shadow-only mesh, the patch's grid every
	 * ShadowProxyCm (25 cm), hidden in every view (bCastHiddenShadow) with the surface's material (so the same displacement from
	 * the field, every frame); with the switch on the chunks cast no shadow and these cast it. Built with the chunks.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	float ShadowProxyCm = 25.f;
	/** The shadow meshes' triangles (all chunks). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Lod")
	int32 ShadowProxyTriangles = 0;

	// ---- MudRunner MR3, muddy rut water (docs/MUDRUNNER_LESSONS_PLAN.md MR3 item 1) ------------------------------------
	/** The turbidity's sub-steps last tick (FGTMudField::SettleTurbidity). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud")
	int32 LastTurbidSteps = 0;
	/** The cell's turbidity at a world XY (bilinear), for the checks. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	float TurbidityAt(FVector2D XYCm) const { return Field.TurbidityAt(XYCm); }
	/** Tiles awake for the turbidity now. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	int32 TurbidTileCount() const { return Field.TurbidTileCount(); }
	/** The rut water within RadiusCm of a world XY, for the checks: wet cells, turbid ones (over 0.5), the max and the wet mean turbidity, froth cells (fresh over 0.3 and turbid over 0.5), the turbid tiles. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	FString DescribeMuddyWater(FVector2D CentreCm, float RadiusCm) const;
	/** GR2 phase B item 7, for the spray check: the centre of the cell nearest FromCm whose surface lies at least MinDepthCm under the
	 *  patch's water table (a puddle), with that depth in Z; Z below 0 when no cell holds that much. */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	FVector NearestPuddleCm(FVector2D FromCm, float MinDepthCm) const;

	// ---- Deformable gravel DG1 item 3 (docs/DEFORMABLE_GRAVEL_PLAN.md): the loose stones (GTGravelStones.h/.cpp) ----
	/** The profile's stones per m^2 of road (FGTDeformProfile::GravelStonesPerM2, ApplyProfile): 0, none. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Gravel")
	float GravelStonesPerM2 = 0.f;
	/** The spec's road half width (SetRouteLine), cm: the stones lie within it either side of the route line. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Gravel")
	float RoadHalfWidthCm = 600.f;
	/** DG1b: the profile's texture slide with the field (FGTDeformProfile::TextureSlideScale), M_GT_Gravel's GravelSlideUV; 1 elsewhere. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Gravel")
	float TextureSlideScale = 1.f;
	/** A Gravel patch with GravelStonesPerM2 over 0: its stones (Init builds them after the mesh); null otherwise. */
	UGTGravelStones* GetGravelStones() const { return GravelStones; }
	/** The stones for the check (GTGravelStones.cpp): count, instances, states, target, density. */
	UFUNCTION(BlueprintCallable, Category = "GT|Gravel")
	FString DescribeGravelStones() const;

	// ---- Benmore integration B2 (docs/BENMORE_INTEGRATION_PLAN.md B2): a deform zone's patch ----------------------------
	/** A patch UGTMudSubsystem streams for an AGTDeformZone (a 24 m tile of a tiled zone, or a mud zone's whole box). Off it, every
	 *  hook below is inert: the strips' patches are built exactly as before. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Zone")
	bool bZonePatch = false;
	UPROPERTY(Transient)
	TObjectPtr<AGTDeformZone> Zone;
	/** The patch's own region: a tile's 24 m box (its field reaches one cell further, the overlap its neighbours own) or the zone's box. */
	FBox2D ZoneOwnBoxCm = FBox2D(ForceInit);
	/** Per field cell: 2 inside the zone, 1 the drawn ring just outside it (no other zone's cell), 0 inert. Set by ZoneAfterField. */
	TArray<uint8> ZoneCells;
	/** Benmore B2c: per field cell, how much of the patch draws there (0-255; AGTDeformZone::OpacityAt: a mud zone's feather), for the
	 *  coverage texture. */
	TArray<uint8> ZoneOpacity;
	/** Benmore B2c: the coverage texture and its window into this patch's material (the patch draws where the coverage's dither says
	 *  the landscape does not). */
	void SetZoneCoverage(class UTexture* Coverage, const FLinearColor& Window);
	/** The subsystem's hook, called in Init after the field and its pre-churn and before the textures and the mesh: it sets ZoneCells,
	 *  fades a mud zone's pre-churn at the outline (FadeZonePreChurn), keeps the baseline and restores the cached cells. */
	TFunction<void(AGTMudPatch&)> ZoneAfterField;
	/** The zone's route line and half width in place of a spec's (SetRouteLine's), before Init. */
	void SetZoneRoute(const TArray<FVector2D>& LineCm, float HalfWidthCm);
	/** Inside the own region on a zone cell (always true off a zone patch). */
	bool ZoneOwns(const FVector2D& XYCm) const;
	/** Where stones, chunks, clods and debris may lie: ZoneOwns (always true off a zone patch). */
	bool KeepsDecorAt(const FVector2D& XYCm) const { return !bZonePatch || ZoneOwns(XYCm); }
	/** A zone patch's grid quad (= field cell) X, Y is drawn: a zone or ring cell inside the own region. */
	bool ZoneQuadDrawn(int32 X, int32 Y) const;
	/** A mud zone's pre-churn x smoothstep(0, FadeCm, InsideCm) per cell (InsideCm per cell, the field's size); off-zone cells flat. */
	void FadeZonePreChurn(const TArray<float>& InsideCm, float FadeCm);
	/** The layer texture from the zone (BakeLayers without a spec): BogWeightAt per cell centre, 0..1. Returns the bog cells. */
	int32 BakeZoneLayers(const TFunctionRef<float(const FVector2D&)>& BogWeightAt);
	/** A mud zone's rows for the traction (the landscape under it has none): the Bog row on the deep core, the Mud row elsewhere; null off a mud zone. */
	const UGTSurfacePhysMaterial* ZoneSurfaceAt(const FVector2D& XYCm) const;
	UPROPERTY(Transient)
	TObjectPtr<UGTSurfacePhysMaterial> ZoneMudRow;
	UPROPERTY(Transient)
	TObjectPtr<UGTSurfacePhysMaterial> ZoneBogRow;
	/** The zone's field material tint (M_GT_Gravel_Zone's GravelTint). */
	FLinearColor ZoneSurfaceTint = FLinearColor::White;
	/** The zone patch's drawn quads and the edge sink: vertices on the zone's edge sit ZoneEdgeSinkCm under the ground (the landscape
	 *  draws over them outside the coverage hole), the ring's outer ones ZoneRingSinkCm; skirts ZoneSkirtCm deep on the own region's border. */
	float ZoneEdgeSinkCm = 0.f;   // Benmore B2c: 0 - the patch and the landscape share each pixel by a complementary dither now
	float ZoneRingSinkCm = 0.f;
	float ZoneSkirtCm = 40.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Mud|Zone")
	int32 ZoneDrawnQuads = 0;

private:
	FGTMudField Field;
	FString ProfileSurfaceMaterialPath;
	UPROPERTY(Transient)
	TObjectPtr<UGTGravelStones> GravelStones;
	/** DG1: makes and builds GravelStones on a Gravel patch (GTGravelStones.cpp); Init calls it after BuildMesh. */
	void InitGravelStones();
	/** LM1: gt.Mud.Settle as this tick read it (the upload writes the fresh sheen only while it is on). */
	bool bSettleOn = true;
	/** LM3a: the time since the last refill pass, s. */
	float RefillAccumS = 0.f;
	/** Per vertex, row-major (Y then X): the ground MeshLiftCm up. */
	TArray<float> MeshRestZ;
	void Upload(const FIntRect& Rect);
	bool TraceGround(float XCm, float YCm, float& OutZ) const;
	/** LM2b: BakeLayers' layer per cell (255 Bog, 0 Mud), kept for the clods' wet sinking. */
	TArray<uint8> BogMask;

	// ---- LM2b, the clods ---------------------------------------------------------------------------------------
	struct FClod
	{
		FVector2D XYCm = FVector2D::ZeroVector;
		float SizeCm = 10.f;
		float HeightCm = 6.f;     // LM2c: its own height (the mesh's at scale 1 x size / 10 x the Z scale)
		float SunkCm = 0.f;       // how far the flat face is under the surface
		float SurfaceCm = 0.f;    // the field's surface under it when last snapped
		float PushedZ = 0.f;      // LM2c: the world Z last pushed to its instance
		FQuat Rotation = FQuat::Identity;
		FVector Scale = FVector::OneVector;   // LM2c: the non-uniform scale on top of the size
		int32 MeshIndex = INDEX_NONE;  // LM2c: which HISM and which instance in it (the family's mesh, not the slot's)
		int32 Instance = INDEX_NONE;
		int32 Tile = INDEX_NONE;
		uint8 Source = 0;
		bool bAlive = false;
	};
	/** One HISM per clod mesh found; LM2c: each keeps a pool of instances (the dead at zero scale) and a clod takes one from its family's mesh. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> ClodMeshes;
	TArray<FClod> Clods;                      // the ring, MaxClods slots
	int32 ClodNext = 0;
	TArray<TArray<int32>> TileClods;          // per settle tile (16 cells), the ring slots in it
	int32 ClodTilesX = 0;
	int32 ClodTilesY = 0;
	TArray<TArray<FTransform>> ClodTransforms;   // per mesh, the instances' transforms (world)
	TArray<TArray<int32>> ClodFree;           // LM2c: per mesh, the dead instances
	TArray<TArray<int32>> ClodDirtyList;      // LM2c: per mesh, the instances to push this batch (only those)
	TArray<TArray<uint8>> ClodDirtyFlag;      // per mesh and instance, already in the list
	TArray<float> ClodMeshHeightCm;           // LM2c: per mesh, its height at scale 1 (10 cm across), from its bounds
	TArray<float> ClodMeshAcrossCm;           // LM4: per mesh, its across at scale 1 (the clods' 10; a shard's own 6-25 from its bounds)
	TArray<int32> ClodMeshFamily;             // LM2c: per mesh, 0 blob, 1 pancake, 2 chunk, 3 smear (by its number)
	FIntRect ClodDirtyCells;                  // the field cells changed since the last batch
	bool bClodDirtyCells = false;
	float ClodBatchAccumS = 0.f;
	bool bClodsVisible = true;
	FRandomStream ClodRandom;
	FVector ClodParkLocation = FVector::ZeroVector;   // where a dead instance sits, at zero scale (inside the box, at ground level)
	void InitClods();
	void UpdateClods(float DeltaSeconds, bool bClodsOn);
	void SpawnClod(const FGTMudField::FClodSpawn& Spawn);
	void RemoveClod(int32 Slot);
	FTransform ClodTransform(const FClod& Clod) const;
	void SetClodInstance(int32 Slot, const FTransform& Transform);
	/** LM2c: a free instance on the mesh (the pool grows when it has none). */
	int32 TakeClodInstance(int32 MeshIndex);
	int32 PickClodMesh(uint8 Source, FRandomStream& Random) const;
	FTransform DeadClodTransform() const { return FTransform(FQuat::Identity, ClodParkLocation, FVector::ZeroVector); }
	// LM4e: the record and the replay.
	TArray<FGTMudField::FEvent> RecordLog;
	TArray<FGTMudField::FEvent> ReplayLog;
	int32 ReplayCursor = 0;
	void Record(uint8 Kind, std::initializer_list<double> Values, uint8 Flag = 0);
	/** LM4e cut 2: one cell's two texels (the field's and the tread's), as Upload writes them. */
	void EncodeCell(int32 Index, FFloat16Color& OutField, FFloat16Color* OutTread) const;
	/** LM4e cut 2: the boxes uploaded in one update per texture; returns the cells. */
	int32 UploadRects(const TArray<FIntRect>& Rects);
	TArray<FIntRect> UploadRectList;
	// LM4e cut 4: the chunks.
	UPROPERTY(Transient)
	TArray<TObjectPtr<UProceduralMeshComponent>> ChunkMeshes;
	TArray<FBox> ChunkBoxes;        // world, the rest surface's
	TArray<int32> ChunkLod;         // the section drawn now
	TArray<int32> ChunkLodTris;     // per chunk and LOD (3 a chunk), the section's triangles
	int32 ForcedLod = -1;
	bool bSurfaceCastShadow = true;
	// LM4f item 1: the chunks' shadow meshes, gt.Snow.ShadowProxy as last applied, and whether the surface is shown (its test switch).
	UPROPERTY(Transient)
	TArray<TObjectPtr<UProceduralMeshComponent>> ShadowMeshes;
	bool bShadowProxyOn = true;
	bool bSurfaceVisible = true;
	void DestroyShadowMeshes();
	/** Who casts the surface's shadow: the chunks (gt.Snow.ShadowProxy 0, or no shadow meshes) or their shadow meshes. */
	void ApplySurfaceShadows();
	/** Builds the chunks from MeshRestZ (BuildMesh, snow with gt.Snow.MeshLod 1); returns the vertices over every LOD. */
	int32 BuildChunks();
	void UpdateChunkLods();
	/** One event of the replay; for a frame's end, its dt and clods switch. */
	void ReplayEvent(const FGTMudField::FEvent& Event);
	/** MR3: gt.Mud.MuddyWater as last pushed onto the water material (-1 before the first push). */
	float PushedMuddyWater = -1.f;
	/** MRP: the rut water's table (cm, the field's frame) as last pushed onto the mud's own material (MudWaterTableCm). */
	float PushedMeshTableCm = -1.0e9f;
	// MR4: S per cell (empty off scope), outside the field and its CRC; gt.Mud.SoftSpots as last applied; the layer's texels.
	TArray<float> Softness;
	bool bSoftOn = true;
	TArray<uint8> LayerBytes;
	/** MR4: S, its means and the switch at Init (nothing off scope). */
	void BuildSoftSpots();
	/** GR1: the pre-churn at Init (after BuildSoftSpots, before the mesh); the hummocked ground, the surface it left, the depths asked. */
	void PreChurn();
	/** MRD1: the braided pre-churn (PreChurn's steps 2-4 on a mud road), after the hummocks. */
	void PreChurnBraided(FRandomStream& Random, float Scale);
	/** MRD1: the churn zones (x, y, radius, the clod field's falloff), cm; the readouts' JSON body (PreChurnBraided writes it). */
	TArray<FVector4f> RoadChurnZones;
	FString RoadDescribe;
	FString RoadLayoutDescribe;   // MRD1b: the widths, the stretches, the pools' gate (a JSON fragment)
	/** MRD1: the churn zones' clod fields (after InitClods) and their chunks (InitMudChunks appends them to its plan). */
	void SpawnRoadClodFields();
	void PlanRoadChunks(TArray<FMudChunkPlan>& Plan);
	/** MRD1 item 3: the sticks and branches - one HISM per mesh, placed at Init on the pre-churned surface; where a wheel presses the
	 *  ground under one by over 2 cm in a track it goes down with the ground (UpdateRoadDebris, on the uploaded rect). */
	struct FRoadDebris { FVector2D XYCm = FVector2D::ZeroVector; FQuat Rotation = FQuat::Identity; float Scale = 1.f; float SurfaceCm = 0.f; float SunkCm = 0.f; int32 Mesh = 0; int32 Instance = INDEX_NONE; };
	UPROPERTY(Transient)
	TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> RoadDebrisMeshes;
	TArray<FRoadDebris> RoadDebris;
	void InitRoadDebris();
	void UpdateRoadDebris(const FIntRect& Rect);
	FTransform RoadDebrisTransform(const FRoadDebris& Piece) const;
	TArray<float> PreChurnBaseCm;
	TArray<float> PreChurnSurfaceCm;
	TArray<float> PreChurnDepthsCm;
	/** MR4: LayerBytes from BogMask (R) and S (G, 0 off scope or with the switch off). */
	void FillLayerBytes();
	/** MR4: LayerBytes up to LayerTexture (the whole texture, one region). */
	void UploadLayer();
	// MR5: the chunks - per slot its record, its pooled component (index-aligned), the meshes by number and their numbers, the
	// route line, the wheels' coarse grid, the switch as last applied, the break clods' stream.
	struct FMudChunk
	{
		FVector2D XYCm = FVector2D::ZeroVector;
		float SizeCm = 20.f;
		float Scale = 1.f;
		float VolumeCm3 = 0.f;
		float MassKg = 10.f;
		int32 Mesh = INDEX_NONE;
		int32 GridCell = INDEX_NONE;
		double AwakeSinceS = -1.0;   // the world time it woke (-1 asleep)
		bool bAlive = false;
	};
	TArray<FMudChunk> MudChunks;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> MudChunkComponents;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> MudChunkMeshes;   // by number, null where missing
	TArray<float> MudChunkMeshVolume;
	TArray<float> MudChunkMeshAcross;
	TArray<TArray<FVector>> MudChunkHullVerts;        // per mesh, the hull's vertices (the mesh's space; the pivot the hull's bottom)
	TArray<FVector2D> RouteLineCm;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> MudChunkMaterial;   // M_GT_MudChunk (the instance above wears it on a variant)
	float MudChunkLargestCm = 0.f;                     // the largest chunk spawned (the wheels' grid reach)
	TArray<TArray<int32>> MudChunkGrid;
	int32 MudChunkGridX = 0;
	int32 MudChunkGridY = 0;
	bool bMudChunksOn = true;
	FRandomStream MudChunkRandom;
	/** MR5: the meshes, the material, the plan and the chunks at Init (nothing off scope). */
	void InitMudChunks();
	/** MR5: a plan spawned, each chunk asleep on the ground. Returns the chunks spawned. */
	int32 SpawnPlannedMudChunks(const TArray<FMudChunkPlan>& Plan);
	/** MR5: one chunk into a free slot (a pooled component when there is one). At: the pivot's world location (a test's), else on the ground under the plan's XY. */
	int32 SpawnMudChunk(const FMudChunkPlan& Plan, bool bAsleep, const FVector* At);
	/** MR5: a chunk out of the world (its component kept, hidden, without collision or simulation, for the next one). */
	void RemoveMudChunk(int32 Index);
	/** MR5, each tick: the switch, the awake chunks' places, the lost ones, the awake count and the subsystem's cap. */
	void UpdateMudChunks(float DeltaSeconds);
	int32 MudChunkGridCellAt(const FVector2D& XYCm) const;
	void SetMudChunkGridCell(int32 Index, int32 Cell);
	int32 FindMudChunk(const UPrimitiveComponent* Component) const;
};
