#pragma once

#include "CoreMinimal.h"
#include "Math/Float16Color.h"

/** CPU authority for the landscape prototype. Cells are centres on a world grid, never patch vertices.
 * Paint: R = mud thickness cm, G = water table cm below the undisturbed surface (negative),
 * B = gravel coverage, A = softness. Zero thickness is firm and cannot be excavated.
 * Landscape collision excludes the relief; the firm base is ThicknessCm below that original surface. */
struct GRANDTOUR_API FGTLandscapeSurfaceCell
{
    float DeltaCm = 0.f; // Total mud surface relative to the original landscape, including authored relief.
    FVector2f SlideCm = FVector2f::ZeroVector;
    float Track = 0.f;
    float Fresh = 0.f;
    float Turbidity = 0.f;
};

struct GRANDTOUR_API FGTLandscapeSurfaceField
{
    static constexpr int32 TileCells = 256;
    static constexpr float CellCm = 6.25f;
    static constexpr float TileCm = TileCells * CellCm;
    static constexpr int32 WindowCells = TileCells * 3;
    static constexpr int32 UploadBlockCells = 32;
    static constexpr int32 BlocksPerSide = TileCells / UploadBlockCells;
    static constexpr int64 CacheBudgetBytes = 128ll * 1024 * 1024;
    static constexpr float LipCapCm = 15.f;
    static constexpr float WaterFillLimitCm = 32.f;

    struct FTile
    {
        TArray<FGTLandscapeSurfaceCell> Cells;
        uint64 LastUse = 0;
        uint64 DirtyBlocks = MAX_uint64;
        uint64 ContactDirtyBlocks = 0;
        uint64 BedBlockRevision[BlocksPerSide*BlocksPerSide] = {};
        TSet<int32> DecayingCells;
        /** PF1: time since this tile's decay was last applied (the sliced decay applies it every third frame with the whole elapsed time). */
        float DecayAccum = 0.f;
    };
    TMap<FIntPoint, FTile> Tiles;
    FIntPoint WindowTile = FIntPoint::ZeroValue;
    uint64 Clock = 0;
    double ExcavatedCm3 = 0.;
    double DepositedCm3 = 0.;
    int32 Evictions = 0;
    uint64 GeometryRevision = 0;
    // Lab-only native shader update path. Existing scenes retain the original solver.
    bool bNativeShaderUpdates = false;
    uint64 NativeUpdateCells = 0;
    uint64 NativePushCells = 0;
    TMap<FIntPoint,float> NativeAux;
    TSet<FIntPoint> NativeContactCells;
    // Host contact raster for the separately recovered RED/MAX PushMud and GB
    // displacement passes. Transient work, never a second persistent soil field.
    struct FPushReceiver { FIntPoint Key; float Capacity; float Ceiling; FVector2f Direction; };
    struct FPushContact { TArray<FIntPoint> Sources; TArray<FPushReceiver> Receivers; };
    TArray<FPushContact> NativePushContacts;
    TFunction<float(FVector2D)> NativeBaseAlpha;
    /** Null preserves old all-native fixtures; atlas maps route sod/sand to their host laws. */
    TFunction<bool(FVector2D)> NativeUpdateAt;
    /** CL2: clay weight 0-1 at a world point. Unset (the default) keeps Step exactly as it was. Called from Step on the game thread only. */
    TFunction<float(FVector2D)> ClayAt;
    int32 LastDecayCells = 0;
    /** PF1: runtime only (AGTLandscapeSurface sets it). Step then decays each window tile every third frame with the time elapsed since its last decay, instead of all nine tiles every frame. Tests leave it off. */
    bool bSliceDecay = false;
    uint32 DecayFrame = 0;
    /** PF1: tiles the focus can reach by crossing one tile boundary (a 5 x 5 block) are initialised ahead of the crossing, a few rows per call under Deadline (FPlatformTime::Seconds), so Focus never builds three tiles in one frame. */
    void Prefetch(FVector2D World, TFunctionRef<FLinearColor(FVector2D)> Paint, double Deadline);
    // R wetness, G cohesion, B relief strength, A fragment scale. Separate from depth/softness paint.
    TFunction<FLinearColor(FVector2D)> ShapeAt;
    // Optional imported rest relief. The same heights seed cells and bound deposit capacity.
    TFunction<float(FVector2D, float)> AuthoredHeightAt;
    struct FWheelWork
    {
        bool Enabled = false;
        float Slip = 0.f;
        float Motion = 0.f;
        bool Granular = false;
    };

    void Focus(FVector2D World, TFunctionRef<FLinearColor(FVector2D)> Paint);
    bool IsActive(FIntPoint Cell) const;
    FGTLandscapeSurfaceCell* Edit(FIntPoint Cell);
    FGTLandscapeSurfaceCell Read(FIntPoint Cell) const;
    FGTLandscapeSurfaceCell Sample(FVector2D World) const;
    void Step(float Dt);
    void StepNative();
    void StampNative(FVector2D Start,FVector2D End,FVector2D Heading,float Width,float Depth,
        TFunctionRef<FLinearColor(FVector2D)> Paint,float Plane,float MaxCut,FWheelWork Work);
    void MarkChanged(FIntPoint Cell, bool bDecay = false);
    /** Persistent revisions let independent consumers update only changed geometry, without stealing upload bits. */
    void BedChangesSince(uint64 Revision,TArray<FBox2D>& Regions) const;
    /** Pack only a bounded rectangle; the CPU authority retains full resolution at every quality. */
    void Pack(FIntRect Cells, TFunctionRef<FLinearColor(FVector2D)> Paint,
        TFunctionRef<FVector2f(FVector2D)> Appearance, TArray<FFloat16Color>& Ground, TArray<FFloat16Color>& Water) const;
    /** Compression target below local authored relief, not cumulative per frame. Digging is limited by available lip capacity;
     * every removed cm^3 is deposited in painted mud beside this tyre, even at a tile or paint boundary. */
    void Stamp(FVector2D Start, FVector2D End, FVector2D Heading, float WidthCm,
        float TargetDepthCm, TFunctionRef<FLinearColor(FVector2D)> Paint,
        float ContactPlaneCm = MAX_flt, float MaxCutCm = MAX_flt);
    void StampWorked(FVector2D Start, FVector2D End, FVector2D Heading, float WidthCm,
        float TargetDepthCm, TFunctionRef<FLinearColor(FVector2D)> Paint,
        float ContactPlaneCm, float MaxCutCm, FWheelWork Work);
    static FVector2D Centre(FIntPoint Cell);
    static float WaterDepth(float DeltaCm, const FLinearColor& Paint);
    /** Deterministic authored clumps, shared by tile initialization and lip capacity. */
    float RestHeight(FVector2D World, float ThicknessCm) const;
    /** Fills rows [From, To) of a tile's rest heights (the per-cell part of tile initialization). */
    void InitTileRows(FIntPoint Key, TArray<FGTLandscapeSurfaceCell>& Cells, int32 From, int32 To, TFunctionRef<FLinearColor(FVector2D)> Paint) const;
    FIntPoint PrefetchKey = FIntPoint::ZeroValue;
    TArray<FGTLandscapeSurfaceCell> PrefetchCells;
    int32 PrefetchRow = -1;
};
