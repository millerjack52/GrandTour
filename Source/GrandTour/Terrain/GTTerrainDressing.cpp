#include "Terrain/GTTerrainDressing.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInterface.h"

namespace
{
	UHierarchicalInstancedStaticMeshComponent* MakeInstances(AActor* Owner, const TCHAR* Name)
	{
		UHierarchicalInstancedStaticMeshComponent* Component = Owner->CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(Name);
		Component->SetMobility(EComponentMobility::Static);
		// Solid to everything: the wheels sweep against the instances, the body dents on them.
		Component->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		Component->SetCollisionProfileName(TEXT("BlockAll"));
		Component->SetGenerateOverlapEvents(false);
		Component->bCastDynamicShadow = true;
		Component->NumCustomDataFloats = 0;
		return Component;
	}

	UMaterialInterface* LoadMaterial(const FString& MaterialPath)
	{
		if (MaterialPath.IsEmpty())
		{
			return nullptr;
		}
		const FString ObjectPath = MaterialPath.Contains(TEXT(".")) ? MaterialPath : FString::Printf(TEXT("%s.%s"), *MaterialPath, *FPaths::GetBaseFilename(MaterialPath));
		return LoadObject<UMaterialInterface>(nullptr, *ObjectPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	}

	// Look stage L6: the material path, or the plain one when it does not load (a level rebuilt before setup_look_l6).
	void Dress(UHierarchicalInstancedStaticMeshComponent* Component, const FString& MeshPath, const FString& MaterialPath, const FString& FallbackPath)
	{
		if (UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath))
		{
			if (Component->GetStaticMesh() != Mesh)
			{
				Component->SetStaticMesh(Mesh);
			}
		}
		UMaterialInterface* Material = LoadMaterial(MaterialPath);
		if (!Material && !FallbackPath.IsEmpty())
		{
			Material = LoadMaterial(FallbackPath);
			UE_LOG(LogTemp, Warning, TEXT("AGTTerrainDressing: %s did not load; %s wears %s"), *MaterialPath, *Component->GetName(), *FallbackPath);
		}
		if (Material)
		{
			Component->SetMaterial(0, Material);
		}
	}
}

AGTTerrainDressing::AGTTerrainDressing()
{
	PrimaryActorTick.bCanEverTick = false;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	GetRootComponent()->SetMobility(EComponentMobility::Static);
	Stones = MakeInstances(this, TEXT("Stones"));
	Stones->SetupAttachment(GetRootComponent());
	Posts = MakeInstances(this, TEXT("Posts"));
	Posts->SetupAttachment(GetRootComponent());
	Rocks = MakeInstances(this, TEXT("Rocks"));
	Rocks->SetupAttachment(GetRootComponent());
	// Look stage L3: the foliage cards - drawn and shadowing, never solid.
	Foliage = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(TEXT("Foliage"));
	Foliage->SetupAttachment(GetRootComponent());
	Foliage->SetMobility(EComponentMobility::Static);
	Foliage->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Foliage->SetCollisionProfileName(TEXT("NoCollision"));
	Foliage->SetGenerateOverlapEvents(false);
	Foliage->SetCanEverAffectNavigation(false);
	Foliage->bCastDynamicShadow = true;
	Foliage->NumCustomDataFloats = 0;
}

AGTTerrainDressing* AGTTerrainDressing::Find(UWorld* World)
{
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AGTTerrainDressing> It(World); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

int32 AGTTerrainDressing::Rebuild(const FGTTerrainSpec& Spec)
{
	Modify();
	Dress(Stones, StoneMeshPath, StoneMaterialPath, PlainStoneMaterialPath);
	Dress(Posts, PostMeshPath, PostMaterialPath, PlainPostMaterialPath);
	Dress(Rocks, StoneMeshPath, RockMaterialPath, PlainStoneMaterialPath);
	Dress(Foliage, FoliageMeshPath, FoliageMaterialPath, FString());
	Stones->ClearInstances();
	Posts->ClearInstances();
	Rocks->ClearInstances();
	Foliage->ClearInstances();
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);

	// The engine's cube and cylinder are 100 cm across before the scale; the transforms are world space.
	TArray<FGTTerrainStone> StoneList;
	GTTerrain::TrackStones(Spec, StoneList);
	TArray<FTransform> Transforms;
	Transforms.Reserve(StoneList.Num());
	for (const FGTTerrainStone& Stone : StoneList)
	{
		const float GroundCm = GTTerrain::HeightM(Spec, Profiles, Stone.PositionM.X, Stone.PositionM.Y) * 100.f;
		const FVector Scale(Stone.SizeM, Stone.SizeM * 0.75f, Stone.SizeM * 0.55f);
		const float HeightCm = Scale.Z * 100.f;
		const FVector Location(Stone.PositionM.X * 100.f, Stone.PositionM.Y * 100.f, GroundCm + HeightCm * (0.5f - FMath::Clamp(StoneSinkFraction, 0.f, 1.f)));
		Transforms.Add(FTransform(FRotator(Stone.PitchDegrees, Stone.YawDegrees, Stone.RollDegrees), Location, Scale));
	}
	if (Transforms.Num() > 0)
	{
		Stones->AddInstances(Transforms, /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true);
	}
	StoneCount = Transforms.Num();

	// Water stage R1 (docs/WATER_PLAN.md section 6): the rocks in a ford's wet channel, the same mesh and the same
	// collision as a track stone. A rock is placed so that the top of the cube over its own centre stands
	// GTTerrain::FordRockExposedCm over the bed whatever its tilt - that height is what the water test reads off the
	// field's bed against the ring of cells a metre out, so the placement has to mean it.
	TArray<FGTTerrainStone> RockList;
	GTTerrain::FordRocks(Spec, RockList);
	Transforms.Reset();
	for (const FGTTerrainStone& Rock : RockList)
	{
		const float GroundCm = GTTerrain::HeightM(Spec, Profiles, Rock.PositionM.X, Rock.PositionM.Y) * 100.f;
		const FVector Scale = GTTerrain::FordRockScaleM(Rock.SizeM);
		const float HalfZCm = Scale.Z * 100.f * 0.5f;
		const float Upright = FMath::Max(0.3f, FMath::Cos(FMath::DegreesToRadians(Rock.PitchDegrees)) * FMath::Cos(FMath::DegreesToRadians(Rock.RollDegrees)));
		const float CentreZ = GroundCm + GTTerrain::FordRockExposedCm(Rock.SizeM) - HalfZCm / Upright;
		Transforms.Add(FTransform(FRotator(Rock.PitchDegrees, Rock.YawDegrees, Rock.RollDegrees),
			FVector(Rock.PositionM.X * 100.f, Rock.PositionM.Y * 100.f, CentreZ), Scale));
	}
	if (Transforms.Num() > 0)
	{
		// Look stage L6: in their own component (the same mesh and collision), so they wear their own instance.
		Rocks->AddInstances(Transforms, /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true);
	}
	FordRockCount = Transforms.Num();

	TArray<FGTTerrainPost> PostList;
	GTTerrain::RallyPosts(Spec, PostList);
	Transforms.Reset();
	for (const FGTTerrainPost& Post : PostList)
	{
		const float GroundCm = GTTerrain::HeightM(Spec, Profiles, Post.PositionM.X, Post.PositionM.Y) * 100.f;
		const FVector Scale(Spec.RallyPostWidthM, Spec.RallyPostWidthM, Spec.RallyPostHeightM);
		// Sunk 10 cm so the foot is in the ground on a slope.
		const FVector Location(Post.PositionM.X * 100.f, Post.PositionM.Y * 100.f, GroundCm + Spec.RallyPostHeightM * 50.f - 10.f);
		Transforms.Add(FTransform(FRotator(0.f, Post.YawDegrees, 0.f), Location, Scale));
	}
	if (Transforms.Num() > 0)
	{
		Posts->AddInstances(Transforms, /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true);
	}
	PostCount = Transforms.Num();

	// Look stage L3 (VEHICLE_BUILD_SYSTEM 58): the foliage clumps, PLACEHOLDER cards.
	Transforms.Reset();
	const double FoliageStart = FPlatformTime::Seconds();
	PlaceFoliage(Spec, Profiles, Transforms);
	if (Transforms.Num() > 0)
	{
		Foliage->AddInstances(Transforms, /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true);
	}
	FoliageCardCount = Transforms.Num();
	Stones->MarkRenderStateDirty();
	Posts->MarkRenderStateDirty();
	Rocks->MarkRenderStateDirty();
	Foliage->MarkRenderStateDirty();
	LastMessage = FString::Printf(TEXT("%d stones in the tracks, %d posts along the rally edges, %d rocks in the fords, %d foliage clumps (%d cards, placed in %.2f s)"),
		StoneCount, PostCount, FordRockCount, FoliageCount, FoliageCardCount, FPlatformTime::Seconds() - FoliageStart);
	UE_LOG(LogTemp, Display, TEXT("AGTTerrainDressing: %s"), *LastMessage);
	return StoneCount + PostCount + FordRockCount + FoliageCardCount;
}

void AGTTerrainDressing::PlaceFoliage(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, TArray<FTransform>& OutCards)
{
	// Rows outward from the road's edge on both sides, one cell (sqrt(1 / density) m) apart along the route and across
	// it, each point jittered 40 % of a cell. A point is kept on the Scrub layer, inside the grid, off any dug channel,
	// at least FoliageRouteClearM outside the main road's edge and every alt route's, and nearest its own stretch of
	// the route (so the inside of a bend is not filled twice). Rows go on until FoliageMaxClumps are kept; the farthest
	// of the last row are then dropped, so the cap is spent where the road sees it. Deterministic from the spec's seed.
	FoliageCount = 0;
	OutCards.Reset();
	if (FoliageDensity <= 0.f || FoliageMaxClumps <= 0 || FoliageCardsPerClump <= 0 || Spec.RouteM.Num() < 2)
	{
		return;
	}
	// Leg dressing LD3 (docs/LEG_DRESSING_PLAN.md, decision D3): where the biomes grow the OW PCG graphs dress the ground,
	// so a spec with biome rules gets no placeholder cards; a spec without them (L_Proving) keeps its cards.
	if (GTTerrain::HasBiomes(Spec))
	{
		UE_LOG(LogTemp, Display, TEXT("AGTTerrainDressing: the spec has biomes, so no L3 placeholder foliage cards"));
		return;
	}
	const float CellM = 1.f / FMath::Sqrt(FoliageDensity);
	const float LengthM = GTTerrain::PolylineLengthM(Spec.RouteM);
	const float SizeM = (GTTerrain::VertsPerSide(Spec) - 1) * Spec.QuadSizeCm / 100.f;
	const FBox2D Grid(FVector2D(Spec.OriginXCm / 100.f + 2.f, Spec.OriginYCm / 100.f + 2.f),
		FVector2D(Spec.OriginXCm / 100.f + SizeM - 2.f, Spec.OriginYCm / 100.f + SizeM - 2.f));
	struct FClump
	{
		FVector2D XY;
		float EdgeM;
	};
	TArray<FClump> Kept;
	FRandomStream Rng(Spec.Seed * 7919 + 58);
	const int32 Along = FMath::Max(1, FMath::FloorToInt(LengthM / CellM));
	for (int32 Row = 0; Row < 200 && Kept.Num() < FoliageMaxClumps; ++Row)
	{
		for (int32 Index = 0; Index < Along; ++Index)
		{
			for (int32 Side = -1; Side <= 1; Side += 2)
			{
				const float Arc = (Index + 0.5f + Rng.FRandRange(-0.4f, 0.4f)) * CellM;
				const float Across = FoliageRouteClearM + (Row + 0.5f + Rng.FRandRange(-0.4f, 0.4f)) * CellM;
				float Yaw = 0.f;
				const FVector2D Point = GTTerrain::PointOnPolyline(Spec.RouteM, Arc, Yaw);
				const FVector2D Left(-FMath::Sin(FMath::DegreesToRadians(Yaw)), FMath::Cos(FMath::DegreesToRadians(Yaw)));
				const FVector2D XY = Point + Left * (Side * (GTTerrain::HalfWidthAt(Spec, Arc) + Across));
				if (!Grid.IsInside(XY))
				{
					continue;
				}
				const FGTRouteHit Hit = GTTerrain::NearestRoute(Spec, XY.X, XY.Y);
				const float Edge = Hit.DistanceM - GTTerrain::HalfWidthAt(Spec, Hit.ArcM);
				if (Edge < FoliageRouteClearM || FMath::Abs(Hit.ArcM - Arc) > CellM)
				{
					continue;
				}
				bool bClear = true;
				for (const FGTAltRoute& Alt : Spec.AltRoutes)
				{
					if (Alt.PointsM.Num() >= 2 && GTTerrain::NearestOnPolyline(Alt.PointsM, XY.X, XY.Y).DistanceM - Alt.HalfWidthM < FoliageRouteClearM)
					{
						bClear = false;
						break;
					}
				}
				if (!bClear || GTTerrain::ChannelDigM(Spec, XY.X, XY.Y) > 0.01f || GTTerrain::LayerAt(Spec, Profiles, XY.X, XY.Y) != 4)
				{
					continue;
				}
				Kept.Add({XY, Edge});
			}
		}
	}
	if (Kept.Num() > FoliageMaxClumps)
	{
		Kept.StableSort([](const FClump& A, const FClump& B) { return A.EdgeM < B.EdgeM; });
		Kept.SetNum(FoliageMaxClumps);
	}
	FoliageCount = Kept.Num();
	OutCards.Reserve(Kept.Num() * FoliageCardsPerClump);
	const float Lo = FMath::Min(FoliageScaleMin, FoliageScaleMax);
	const float Hi = FMath::Max(FoliageScaleMin, FoliageScaleMax);
	for (const FClump& Clump : Kept)
	{
		const float Scale = Rng.FRandRange(Lo, Hi);
		const float Yaw = Rng.FRandRange(0.f, 360.f);
		const float GroundCm = GTTerrain::HeightM(Spec, Profiles, Clump.XY.X, Clump.XY.Y) * 100.f;
		const float HeightCm = FoliageCardHeightM * 100.f * Scale;
		// The engine's plane lies in its local XY (100 cm, facing +Z); roll -90 stands it up with local +Y to world +Z.
		const FVector Location(Clump.XY.X * 100.f, Clump.XY.Y * 100.f, GroundCm + HeightCm * 0.5f - FoliageSinkCm);
		const FVector Size(FoliageCardWidthM * Scale, FoliageCardHeightM * Scale, 1.f);
		for (int32 Card = 0; Card < FoliageCardsPerClump; ++Card)
		{
			OutCards.Add(FTransform(FRotator(0.f, Yaw + Card * 180.f / FoliageCardsPerClump, -90.f), Location, Size));
		}
	}
}
