// Ground relief GR2 phase B item 3 (docs/GROUND_RELIEF_PLAN.md GR2): the ground scatter. See GTGroundScatter.h.
#include "Terrain/GTGroundScatter.h"

#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "LandscapeProxy.h"

static TAutoConsoleVariable<int32> CVarGroundScatter(
	TEXT("gt.Ground.Scatter"), 1,
	TEXT("Ground relief GR2: 1 the test strips draw the ground scatter (soil clods, pebbles, twigs, litter mats by the tussocks, a root mound under each tussock), and Benmore B1: the review landscape's scatter grass types (LGT_GT_SoilScatter, LGT_GT_GrassLitter: their densities, the landscape grass instances flushed on a change); 0 none."));
static TAutoConsoleVariable<float> CVarGroundScatterDensity(
	TEXT("gt.Ground.ScatterDensity"), 1.f,
	TEXT("Ground relief GR2: the ground scatter's density scale, 0-1 (1 = the placement's own: clods 0.6, pebbles 1.5, twigs 0.05 per m^2, litter 0.25 per m^2 within 1.5 m of a tussock, a mound under every tussock), a stable hashed subset, for the owner's cost tests; Benmore B1: scales the scatter grass types' densities, the grass instances flushed on a change."));

namespace
{
	const FName FamilyClods(TEXT("Clods"));
	const FName FamilyPebbles(TEXT("Pebbles"));
	const FName FamilyTwigs(TEXT("Twigs"));
	const FName FamilyLitter(TEXT("Litter"));
	const FName FamilyBases(TEXT("TussockBases"));

	float ScatterHash(int32 X, int32 Y, int32 Salt, int32 Seed)
	{
		uint32 H = static_cast<uint32>(X) * 73856093u ^ static_cast<uint32>(Y) * 19349663u ^ static_cast<uint32>(Salt) * 83492791u
			^ static_cast<uint32>(Seed) * 2654435761u;
		H ^= H >> 13;
		H *= 0x5bd1e995u;
		H ^= H >> 15;
		H *= 0x27d4eb2du;
		H ^= H >> 16;
		return static_cast<float>(H & 0xFFFFFF) / static_cast<float>(0x1000000);
	}

	/** Value noise in 0..1 over unit cells, smoothstepped. */
	float ScatterNoise(const FVector2D& C, int32 Seed)
	{
		const int32 X = FMath::FloorToInt(C.X);
		const int32 Y = FMath::FloorToInt(C.Y);
		float FX = static_cast<float>(C.X - X);
		float FY = static_cast<float>(C.Y - Y);
		FX = FX * FX * (3.f - 2.f * FX);
		FY = FY * FY * (3.f - 2.f * FY);
		return FMath::Lerp(FMath::Lerp(ScatterHash(X, Y, 991, Seed), ScatterHash(X + 1, Y, 991, Seed), FX),
			FMath::Lerp(ScatterHash(X, Y + 1, 991, Seed), ScatterHash(X + 1, Y + 1, 991, Seed), FX), FY);
	}

	/** A truncated power law (Pareto, Alpha) between Lo and Hi from a uniform U: most small. */
	float ScatterPareto(float U, float Lo, float Hi, float Alpha)
	{
		const float Tail = 1.f - FMath::Pow(Lo / Hi, Alpha);
		return Lo / FMath::Pow(1.f - U * Tail, 1.f / Alpha);
	}
}

AGTGroundScatter::AGTGroundScatter()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;
	PrimaryActorTick.TickInterval = 0.25f;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent->SetMobility(EComponentMobility::Static);
}

bool AGTGroundScatter::IsEnabled()
{
	return CVarGroundScatter.GetValueOnGameThread() != 0;
}

float AGTGroundScatter::DensityScale()
{
	return FMath::Clamp(CVarGroundScatterDensity.GetValueOnGameThread(), 0.f, 1.f);
}

float AGTGroundScatter::ClusterMultiplier(const FVector2D& XYCm) const
{
	const float N = ScatterNoise(XYCm / FMath::Max(50.0, static_cast<double>(ClusterCm)) + FVector2D(17.3, 41.9), Seed);
	const float S = FMath::Clamp(ClusterSharpen, 0.f, 0.5f);
	return FMath::Lerp(ClusterMin, ClusterMax, S > 0.f ? FMath::SmoothStep(0.5f - S, 0.5f + S, N) : N);
}

bool AGTGroundScatter::IsOpenGround(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, const TArray<FBox2D>& Boxes, const FVector2D& XYCm) const
{
	for (const FBox2D& Box : Boxes)
	{
		if (Box.IsInside(XYCm))
		{
			return false;
		}
	}
	const float XM = static_cast<float>(XYCm.X) * 0.01f;
	const float YM = static_cast<float>(XYCm.Y) * 0.01f;
	if (GTTerrain::ChannelDigM(Spec, XM, YM) > 0.02f)
	{
		return false;
	}
	return GTTerrain::OffRoadWeight(Spec, Profiles, XM, YM) >= OffRoadMin;
}

void AGTGroundScatter::Plan(const FGTTerrainSpec& Spec, const TArray<FGTGroundScatterMesh>& InMeshes, const TArray<FTransform>& Tussocks,
	const TArray<float>& TussockFootprintsCm, TArray<FPoint>& Out, FPlanStats& OutStats) const
{
	Out.Reset();
	OutStats = FPlanStats();
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	TArray<FBox2D> Boxes;
	for (int32 Index = 0; Index < Spec.Sections.Num(); ++Index)
	{
		FBox2D Box(ForceInit);
		if (GTTerrain::DeformPatchBoxCm(Spec, Index, Box))
		{
			Boxes.Add(Box.ExpandBy(static_cast<double>(PatchMarginCm)));
		}
	}
	TMap<FName, TArray<int32>> ByFamily;
	for (int32 M = 0; M < InMeshes.Num(); ++M)
	{
		ByFamily.FindOrAdd(InMeshes[M].Family).Add(M);   // the tests plan without meshes; Build skips a missing one's instances
	}
	// The mesh nearest a wanted size (log scale), and the scale that takes it there (within x0.8-1.25).
	auto Nearest = [&InMeshes](const TArray<int32>& List, float SizeCm, float& OutScale) -> int32
	{
		int32 Best = List[0];
		float BestD = TNumericLimits<float>::Max();
		for (int32 M : List)
		{
			const float D = FMath::Abs(FMath::Loge(FMath::Max(0.1f, SizeCm) / FMath::Max(0.1f, InMeshes[M].SizeCm)));
			if (D < BestD)
			{
				BestD = D;
				Best = M;
			}
		}
		OutScale = SizeCm / FMath::Max(0.1f, InMeshes[Best].SizeCm);
		return Best;
	};
	const float SideCm = (GTTerrain::VertsPerSide(Spec) - 1) * Spec.QuadSizeCm;
	const FVector2D Lo(Spec.OriginXCm + 100.f, Spec.OriginYCm + 100.f);
	const int32 Cells = FMath::Max(1, FMath::FloorToInt32((SideCm - 200.f) / 100.f));
	auto ClusterAt = [this](const FVector2D& P) { return ClusterMultiplier(P); };
	double Sum = 0.0;
	for (int32 CY = 0; CY < Cells; ++CY)
	{
		for (int32 CX = 0; CX < Cells; ++CX)
		{
			Sum += ClusterAt(Lo + FVector2D(CX * 100.f + 50.f, CY * 100.f + 50.f));
		}
	}
	const float Mean = static_cast<float>(FMath::Max(1e-3, Sum / (static_cast<double>(Cells) * Cells)));
	// The tussocks on a 1 m grid (litter's reach), and their bases.
	TMap<FIntPoint, TArray<int32>> TussockGrid;
	for (int32 T = 0; T < Tussocks.Num(); ++T)
	{
		const FVector L = Tussocks[T].GetLocation();
		TussockGrid.FindOrAdd(FIntPoint(FMath::FloorToInt32(L.X / 100.0), FMath::FloorToInt32(L.Y / 100.0))).Add(T);
	}
	OutStats.Tussocks = Tussocks.Num();
	auto NearTussock = [&](const FVector2D& P, float Reach) -> bool
	{
		const int32 GX = FMath::FloorToInt32(P.X / 100.0);
		const int32 GY = FMath::FloorToInt32(P.Y / 100.0);
		const int32 R = FMath::CeilToInt32(Reach / 100.f);
		for (int32 Y = GY - R; Y <= GY + R; ++Y)
		{
			for (int32 X = GX - R; X <= GX + R; ++X)
			{
				if (const TArray<int32>* List = TussockGrid.Find(FIntPoint(X, Y)))
				{
					for (int32 T : *List)
					{
						if (FVector2D::DistSquared(P, FVector2D(Tussocks[T].GetLocation())) <= Reach * Reach)
						{
							return true;
						}
					}
				}
			}
		}
		return false;
	};
	struct FFamily
	{
		FName Name;
		float PerM2;
		bool bNearTussocks;
		int32 Salt;
	};
	const FFamily Families[4] = { { FamilyClods, ClodsPerM2, false, 1 }, { FamilyPebbles, PebblesPerM2, false, 2 }, { FamilyTwigs, TwigsPerM2, false, 3 },
		{ FamilyLitter, LitterPerM2, true, 4 } };
	for (int32 CY = 0; CY < Cells; ++CY)
	{
		for (int32 CX = 0; CX < Cells; ++CX)
		{
			const FVector2D C0 = Lo + FVector2D(CX * 100.f, CY * 100.f);
			const FVector2D Centre = C0 + FVector2D(50.f, 50.f);
			const float Mult = ClusterAt(Centre) / Mean;
			bool bLitterCell = false;
			bool bLitterCellChecked = false;
			for (const FFamily& F : Families)
			{
				const TArray<int32>* List = ByFamily.Find(F.Name);
				if (!List || F.PerM2 <= 0.f)
				{
					continue;
				}
				if (F.bNearTussocks)
				{
					if (!bLitterCellChecked)
					{
						bLitterCell = NearTussock(Centre, LitterReachCm + 71.f);
						bLitterCellChecked = true;
						if (bLitterCell)
						{
							// The litter area (for the report): the cell's quarter points within reach.
							for (int32 Q = 0; Q < 4; ++Q)
							{
								const FVector2D QP = C0 + FVector2D(25.f + 50.f * (Q % 2), 25.f + 50.f * (Q / 2));
								if (NearTussock(QP, LitterReachCm) && IsOpenGround(Spec, Profiles, Boxes, QP))
								{
									OutStats.LitterAreaM2 += 0.25;
								}
							}
						}
					}
					if (!bLitterCell)
					{
						continue;
					}
				}
				const float Lambda = F.PerM2 * Mult;
				const int32 N = FMath::FloorToInt32(Lambda) + (ScatterHash(CX, CY, F.Salt * 64 + 63, Seed) < FMath::Frac(Lambda) ? 1 : 0);
				for (int32 K = 0; K < N; ++K)
				{
					const int32 S = F.Salt * 64 + K * 6;
					const FVector2D P = C0 + FVector2D(100.f * ScatterHash(CX, CY, S, Seed), 100.f * ScatterHash(CX, CY, S + 1, Seed));
					if ((F.bNearTussocks && !NearTussock(P, LitterReachCm)) || !IsOpenGround(Spec, Profiles, Boxes, P))
					{
						++OutStats.Rejected;
						continue;
					}
					FPoint Point;
					Point.XYCm = P;
					Point.YawDeg = 360.f * ScatterHash(CX, CY, S + 2, Seed);
					const float U = ScatterHash(CX, CY, S + 3, Seed);
					if (F.Name == FamilyClods || F.Name == FamilyPebbles)
					{
						const bool bClod = F.Name == FamilyClods;
						const float Size = ScatterPareto(U, bClod ? 3.f : 1.f, bClod ? 12.f : 5.f, 1.5f);
						Point.Mesh = Nearest(*List, Size, Point.Scale);
						Point.Scale = FMath::Clamp(Point.Scale, 0.8f, 1.25f);
					}
					else
					{
						Point.Mesh = (*List)[FMath::Min(List->Num() - 1, FMath::FloorToInt32(U * List->Num()))];
						Point.Scale = FMath::Lerp(0.85f, 1.15f, ScatterHash(CX, CY, S + 4, Seed));
					}
					Out.Add(Point);
					OutStats.PerFamily.FindOrAdd(F.Name)++;
				}
			}
		}
	}
	// One root mound under each tussock whose footprint is at least BaseMinFootprintCm, scaled to it.
	if (const TArray<int32>* List = ByFamily.Find(FamilyBases))
	{
		for (int32 T = 0; T < Tussocks.Num(); ++T)
		{
			const float Foot = TussockFootprintsCm.IsValidIndex(T) ? TussockFootprintsCm[T] : 0.f;
			if (Foot < BaseMinFootprintCm)
			{
				++OutStats.TussocksUnderFootprint;
				continue;
			}
			const FVector2D P(Tussocks[T].GetLocation());
			if (!IsOpenGround(Spec, Profiles, Boxes, P))
			{
				++OutStats.Rejected;
				continue;
			}
			FPoint Point;
			Point.XYCm = P;
			Point.Mesh = Nearest(*List, Foot, Point.Scale);
			Point.YawDeg = 360.f * ScatterHash(T, 7, 5, Seed);
			Out.Add(Point);
			OutStats.PerFamily.FindOrAdd(FamilyBases)++;
		}
	}
	// The open area (a 1 m grid).
	int32 Open = 0;
	for (int32 CY = 0; CY < Cells; ++CY)
	{
		for (int32 CX = 0; CX < Cells; ++CX)
		{
			Open += IsOpenGround(Spec, Profiles, Boxes, Lo + FVector2D(CX * 100.f + 50.f, CY * 100.f + 50.f)) ? 1 : 0;
		}
	}
	OutStats.OpenAreaM2 = Open;
}

FString AGTGroundScatter::Build(UGTTerrainSpecAsset* SpecAsset, const TArray<FGTGroundScatterMesh>& InMeshes, const TArray<FTransform>& Tussocks,
	const TArray<float>& TussockFootprintsCm)
{
	UWorld* World = GetWorld();
	if (!SpecAsset || !World)
	{
		return TEXT("{\"ok\":false,\"error\":\"no spec asset or world\"}");
	}
	const FGTTerrainSpec& Spec = SpecAsset->Spec;
	TArray<FPoint> Points;
	FPlanStats Stats;
	Plan(Spec, InMeshes, Tussocks, TussockFootprintsCm, Points, Stats);
	for (UHierarchicalInstancedStaticMeshComponent* Old : Components)
	{
		if (Old)
		{
			RemoveInstanceComponent(Old);
			Old->DestroyComponent();
		}
	}
	Components.Reset();
	TArray<float> MinZ;
	TArray<float> Height;
	for (int32 M = 0; M < InMeshes.Num(); ++M)
	{
		const FGTGroundScatterMesh& Row = InMeshes[M];
		const FString Name = Row.Mesh ? Row.Mesh->GetName() : FString::Printf(TEXT("Missing_%d"), M);
		UHierarchicalInstancedStaticMeshComponent* Hism = NewObject<UHierarchicalInstancedStaticMeshComponent>(this, *Name);
		Hism->SetMobility(EComponentMobility::Movable);
		Hism->SetStaticMesh(Row.Mesh);
		Hism->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Hism->SetCollisionProfileName(TEXT("NoCollision"));
		Hism->SetCanEverAffectNavigation(false);
		Hism->SetCastShadow(true);
		Hism->bAffectDistanceFieldLighting = false;
		Hism->bVisibleInRayTracing = false;
		const bool bSmall = Row.Family == FamilyTwigs || Row.Family == FamilyLitter;
		Hism->SetCullDistances(FMath::RoundToInt32(bSmall ? SmallCullStartCm : CullStartCm), FMath::RoundToInt32(bSmall ? SmallCullEndCm : CullEndCm));
		Hism->SetupAttachment(RootComponent);
		AddInstanceComponent(Hism);
		Hism->RegisterComponent();
		Components.Add(Hism);
		const FBox Box = Row.Mesh ? Row.Mesh->GetBoundingBox() : FBox(ForceInit);
		MinZ.Add(Box.IsValid ? static_cast<float>(Box.Min.Z) : 0.f);
		Height.Add(Box.IsValid ? static_cast<float>(Box.Max.Z - Box.Min.Z) : 0.f);
	}
	TArray<TArray<FTransform>> Per;
	Per.SetNum(InMeshes.Num());
	int32 Missed = 0;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTGroundScatter), true);
	for (const FPoint& P : Points)
	{
		const float Z = GTTerrain::SampleHeightCm(Spec, static_cast<float>(P.XYCm.X), static_cast<float>(P.XYCm.Y));
		TArray<FHitResult> Hits;
		World->LineTraceMultiByChannel(Hits, FVector(P.XYCm, Z + 500.f), FVector(P.XYCm, Z - 500.f), ECC_Visibility, Params);
		const FHitResult* Ground = Hits.FindByPredicate([](const FHitResult& H) { return H.GetActor() && H.GetActor()->IsA<ALandscapeProxy>(); });
		if (!Ground)
		{
			++Missed;
			continue;
		}
		const FVector N = Ground->ImpactNormal.GetSafeNormal();
		const FQuat Rot = FQuat::FindBetweenNormals(FVector::UpVector, N) * FQuat(FVector::UpVector, FMath::DegreesToRadians(P.YawDeg));
		const float Sink = InMeshes[P.Mesh].SinkShare > 0.f ? (-MinZ[P.Mesh] - InMeshes[P.Mesh].SinkShare * Height[P.Mesh]) * P.Scale : 0.f;
		if (InMeshes[P.Mesh].Mesh)
		{
			Per[P.Mesh].Add(FTransform(Rot, Ground->ImpactPoint + N * Sink, FVector(P.Scale)));
		}
	}
	TMap<FName, int32> PerFamily;
	FString Meshes;
	for (int32 M = 0; M < Components.Num(); ++M)
	{
		Components[M]->AddInstances(Per[M], false, true);
		PerFamily.FindOrAdd(InMeshes[M].Family) += Per[M].Num();
		Meshes += FString::Printf(TEXT("%s\"%s\":%d"), Meshes.IsEmpty() ? TEXT("") : TEXT(","), InMeshes[M].Mesh ? *InMeshes[M].Mesh->GetName() : TEXT("missing"), Per[M].Num());
	}
	FString Families;
	int32 Total = 0;
	for (const TPair<FName, int32>& F : PerFamily)
	{
		const bool bLitter = F.Key == FamilyLitter;
		const bool bBase = F.Key == FamilyBases;
		const double Area = bLitter ? Stats.LitterAreaM2 : Stats.OpenAreaM2;
		Families += FString::Printf(TEXT("%s\"%s\":{\"instances\":%d,\"per_m2\":%.4f}"), Families.IsEmpty() ? TEXT("") : TEXT(","), *F.Key.ToString(), F.Value,
			bBase ? 0.0 : (Area > 0.0 ? F.Value / Area : 0.0));
		Total += F.Value;
	}
	return FString::Printf(TEXT("{\"ok\":true,\"instances\":%d,\"meshes\":{%s},\"families\":{%s},\"open_area_m2\":%.0f,\"litter_area_m2\":%.1f,\"tussocks\":%d,\"tussocks_under_footprint\":%d,\"rejected\":%d,\"missed_traces\":%d,\"cluster\":[%.1f,%.2f,%.2f,%.2f],\"cull_cm\":[%.0f,%.0f,%.0f,%.0f]}"),
		Total, *Meshes, *Families, Stats.OpenAreaM2, Stats.LitterAreaM2, Stats.Tussocks, Stats.TussocksUnderFootprint, Stats.Rejected, Missed,
		ClusterCm, ClusterMin, ClusterMax, ClusterSharpen, CullStartCm, CullEndCm, SmallCullStartCm, SmallCullEndCm);
}

TArray<int32> AGTGroundScatter::InstanceCounts() const
{
	TArray<int32> Counts;
	for (const UHierarchicalInstancedStaticMeshComponent* C : Components)
	{
		Counts.Add(C ? C->GetInstanceCount() : 0);
	}
	return Counts;
}

void AGTGroundScatter::BeginPlay()
{
	Super::BeginPlay();
	Full.SetNum(Components.Num());
	for (int32 I = 0; I < Components.Num(); ++I)
	{
		Full[I].Reset();
		if (UHierarchicalInstancedStaticMeshComponent* C = Components[I])
		{
			Full[I].Reserve(C->GetInstanceCount());
			for (int32 J = 0; J < C->GetInstanceCount(); ++J)
			{
				FTransform T;
				C->GetInstanceTransform(J, T, false);
				Full[I].Add(T);
			}
		}
	}
	AppliedEnabled = 1;
	AppliedDensity = 1.f;
	ApplySwitches(false);
}

void AGTGroundScatter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	ApplySwitches(false);
}

void AGTGroundScatter::ApplySwitches(bool bForce)
{
	const int32 Enabled = IsEnabled() ? 1 : 0;
	const float Density = DensityScale();
	if (bForce || Enabled != AppliedEnabled)
	{
		for (UHierarchicalInstancedStaticMeshComponent* C : Components)
		{
			if (C)
			{
				C->SetVisibility(Enabled != 0);
			}
		}
		AppliedEnabled = Enabled;
	}
	if (bForce || !FMath::IsNearlyEqual(Density, AppliedDensity, 1e-3f))
	{
		for (int32 I = 0; I < Components.Num() && I < Full.Num(); ++I)
		{
			UHierarchicalInstancedStaticMeshComponent* C = Components[I];
			if (!C)
			{
				continue;
			}
			TArray<FTransform> Keep;
			Keep.Reserve(Full[I].Num());
			for (int32 J = 0; J < Full[I].Num(); ++J)
			{
				if (ScatterHash(J, I, 77, 13) < Density)
				{
					Keep.Add(Full[I][J]);
				}
			}
			C->ClearInstances();
			C->AddInstances(Keep, false, false);
		}
		AppliedDensity = Density;
	}
}
