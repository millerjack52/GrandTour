#include "Dressing/GTRouteClearanceTestRunner.h"

#include "Dressing/GTVegetationSubsystem.h"
#include "Interaction/GTInteractable.h"
#include "Interaction/GTInteractionComponent.h"
#include "Run/GTLegActors.h"
#include "Terrain/GTProvingGround.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"

#include "CollisionQueryParams.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "WorldCollision.h"

namespace GTRouteClear
{
	constexpr float StartAfterSeconds = 2.f;
	constexpr int32 StartAfterTicks = 10;
	constexpr float StationStepM = 2.f;
	constexpr float BoxHalfLengthCm = 200.f;   // 4 m along the route
	constexpr float BoxHalfWidthCm = 150.f;    // 3 m across
	constexpr float BoxHalfHeightCm = 100.f;   // 2 m tall
	constexpr float BoxLiftCm = 10.f;          // its bottom over the spec's ground
	constexpr float GameplayMarginCm = 500.f;
	constexpr float EdgeBandCm = 200.f;        // "within 2 m of the corridor's edge" (and of the road's)
	constexpr float SegCellCm = 2000.f;
	constexpr float PlantCellCm = 400.f;

	const FName SolidTag(TEXT("GTVeg.Solid"));

	enum class EKind : uint8 { Solid, Soft, None };
	const TCHAR* KindName(EKind Kind)
	{
		return Kind == EKind::Solid ? TEXT("Solid") : Kind == EKind::Soft ? TEXT("Soft") : TEXT("None");
	}

	/** A dressing instance: soft ones from the vegetation subsystem's hash (the pivot and the index radius). */
	struct FPlant
	{
		FVector Location = FVector::ZeroVector;
		float RadiusCm = 0.f;
		float HeightCm = 0.f;
		EKind Kind = EKind::None;
	};

	/** A centreline piece between two stations (world cm). */
	struct FSeg
	{
		FVector2D A = FVector2D::ZeroVector;
		FVector2D B = FVector2D::ZeroVector;
		float GroundA = 0.f;
		float GroundB = 0.f;
		int32 Line = 0;             // 0 the main route, 1.. the alt routes
		float ArcM = 0.f;           // at A
		float RoadHalfWidthCm = 0.f;
	};

	bool IsDressing(const AActor* Actor)
	{
		for (const FName& Tag : Actor->Tags)
		{
			if (Tag.ToString().StartsWith(TEXT("GTBiome.")))
			{
				return true;
			}
		}
		return false;
	}

	FIntPoint CellOf(const FVector2D& P, float CellCm)
	{
		return FIntPoint(FMath::FloorToInt32(P.X / CellCm), FMath::FloorToInt32(P.Y / CellCm));
	}

	float DistToSeg(const FVector2D& P, const FVector2D& A, const FVector2D& B)
	{
		const FVector2D AB = B - A;
		const double Len2 = AB.SizeSquared();
		const double T = Len2 > 1.0 ? FMath::Clamp(FVector2D::DotProduct(P - A, AB) / Len2, 0.0, 1.0) : 0.0;
		return static_cast<float>(FVector2D::Distance(P, A + AB * T));
	}
}

FGTRouteClearanceTestRunner::FGTRouteClearanceTestRunner(UWorld* InWorld)
	: World(InWorld)
{
}

void FGTRouteClearanceTestRunner::Line(const FString& Text) const
{
	UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST routeclear %s"), *Text);
}

bool FGTRouteClearanceTestRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
{
	Elapsed += DeltaSeconds;
	++Ticks;
	if (Elapsed < GTRouteClear::StartAfterSeconds || Ticks < GTRouteClear::StartAfterTicks)
	{
		return false;
	}
	Judge();
	bOutPass = Failures.Num() == 0;
	OutSummary = bOutPass ? FString::Join(Notes, TEXT("; ")) : FString::Join(Failures, TEXT("; "));
	return true;
}

void FGTRouteClearanceTestRunner::Judge()
{
	using namespace GTRouteClear;
	UWorld* W = World.Get();
	if (!W)
	{
		Failures.Add(TEXT("no world"));
		return;
	}
	const double Start = FPlatformTime::Seconds();
	const UGTTerrainSpecAsset* Asset = GTProving::FindSpecAsset(W);
	if (!Asset)
	{
		Asset = LoadObject<UGTTerrainSpecAsset>(nullptr, TEXT("/Game/GrandTour/Terrain/DA_Terrain_Hide.DA_Terrain_Hide"));
	}
	if (!Asset)
	{
		Failures.Add(TEXT("no terrain spec asset (the level's builder names none and DA_Terrain_Hide did not load)"));
		return;
	}
	const FGTTerrainSpec& Spec = Asset->Spec;
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	auto GroundCm = [&](const FVector2D& Cm) { return GTTerrain::HeightM(Spec, Profiles, static_cast<float>(Cm.X / 100.0), static_cast<float>(Cm.Y / 100.0)) * 100.f; };
	UGTVegetationSubsystem* Veg = W->GetSubsystem<UGTVegetationSubsystem>();

	// 1. The dressing: every ISM on a GTBiome.* actor; Solid by its tag, soft from the hash, the rest unclassed.
	TArray<FPlant> Plants;
	TArray<AActor*> Ignored;
	int32 DressingActors = 0;
	int32 SoftIsmInstances = 0;
	int32 Counts[3] = { 0, 0, 0 };
	for (TActorIterator<AActor> It(W); It; ++It)
	{
		AActor* Actor = *It;
		if (!IsDressing(Actor))
		{
			Ignored.Add(Actor);
			continue;
		}
		++DressingActors;
		TArray<UInstancedStaticMeshComponent*> Isms;
		Actor->GetComponents<UInstancedStaticMeshComponent>(Isms);
		for (const UInstancedStaticMeshComponent* Ism : Isms)
		{
			bool bSoft = false;
			for (const FName& Tag : Ism->ComponentTags)
			{
				bSoft |= Tag.ToString().StartsWith(TEXT("GTVeg.Soft."));
			}
			if (bSoft)
			{
				SoftIsmInstances += Ism->GetInstanceCount();
				continue;   // from the hash below
			}
			const EKind Kind = Ism->ComponentTags.Contains(SolidTag) ? EKind::Solid : EKind::None;
			const float MeshTopCm = Ism->GetStaticMesh() ? static_cast<float>(Ism->GetStaticMesh()->GetBoundingBox().Max.Z) : 0.f;
			for (int32 Index = 0; Index < Ism->GetInstanceCount(); ++Index)
			{
				FTransform T;
				if (Ism->GetInstanceTransform(Index, T, /*bWorldSpace*/ true))
				{
					FPlant P;
					P.Location = T.GetLocation();
					P.HeightCm = MeshTopCm * static_cast<float>(T.GetScale3D().Z);
					P.Kind = Kind;
					Plants.Add(P);
					++Counts[static_cast<int32>(Kind)];
				}
			}
		}
	}
	if (Veg)
	{
		Veg->ForEachInstance([&Plants, &Counts](const FVector& Pivot, EGTVegClass, float RadiusCm, float HeightCm, bool)
		{
			FPlant P;
			P.Location = Pivot;
			P.RadiusCm = RadiusCm;
			P.HeightCm = HeightCm;
			P.Kind = EKind::Soft;
			Plants.Add(P);
			++Counts[static_cast<int32>(EKind::Soft)];
		});
	}
	Line(FString::Printf(TEXT("dressing: %d GTBiome.* actors; %d Solid, %d Soft (the vegetation hash; %d instances on the GTVeg.Soft.* ISMs), %d unclassed instances; spec %s"),
		DressingActors, Counts[0], Counts[1], SoftIsmInstances, Counts[2], *Asset->GetName()));
	if (Plants.Num() == 0)
	{
		Failures.Add(TEXT("no dressing instances on the map (run Art/dressing/setup_dress_hide.bat and the tick harness)"));
		return;
	}
	if (Counts[1] == 0 && SoftIsmInstances > 0)
	{
		Failures.Add(FString::Printf(TEXT("the vegetation hash is empty but %d soft instances exist"), SoftIsmInstances));
	}
	float MaxRadiusCm = 0.f;
	TMap<FIntPoint, TArray<int32>> PlantGrid;
	for (int32 Index = 0; Index < Plants.Num(); ++Index)
	{
		PlantGrid.FindOrAdd(CellOf(FVector2D(Plants[Index].Location), PlantCellCm)).Add(Index);
		MaxRadiusCm = FMath::Max(MaxRadiusCm, Plants[Index].RadiusCm);
	}

	// 2. The centrelines: the main route and every alt route, a station every 2 m.
	TArray<FSeg> Segs;
	auto AddLine = [&](const TArray<FVector2D>& PointsM, int32 LineIndex, TFunctionRef<float(float)> HalfWidthM)
	{
		const float LengthM = GTTerrain::PolylineLengthM(PointsM);
		if (PointsM.Num() < 2 || LengthM <= 0.f)
		{
			return;
		}
		const int32 Count = FMath::CeilToInt(LengthM / StationStepM);
		float Yaw;
		FVector2D Prev = GTTerrain::PointOnPolyline(PointsM, 0.f, Yaw) * 100.0;
		float PrevGround = GroundCm(Prev);
		for (int32 Index = 1; Index <= Count; ++Index)
		{
			const float Arc = FMath::Min(LengthM, Index * StationStepM);
			const FVector2D Next = GTTerrain::PointOnPolyline(PointsM, Arc, Yaw) * 100.0;
			const float NextGround = GroundCm(Next);
			FSeg S;
			S.A = Prev;
			S.B = Next;
			S.GroundA = PrevGround;
			S.GroundB = NextGround;
			S.Line = LineIndex;
			S.ArcM = FMath::Max(0.f, Arc - StationStepM);
			S.RoadHalfWidthCm = HalfWidthM(S.ArcM) * 100.f;
			Segs.Add(S);
			Prev = Next;
			PrevGround = NextGround;
		}
	};
	AddLine(Spec.RouteM, 0, [&Spec](float ArcM) { return GTTerrain::HalfWidthAt(Spec, ArcM); });
	for (int32 Alt = 0; Alt < Spec.AltRoutes.Num(); ++Alt)
	{
		const float Half = Spec.AltRoutes[Alt].HalfWidthM;
		AddLine(Spec.AltRoutes[Alt].PointsM, Alt + 1, [Half](float) { return Half; });
	}
	TMap<FIntPoint, TArray<int32>> SegGrid;
	for (int32 Index = 0; Index < Segs.Num(); ++Index)
	{
		const FVector2D Mid = (Segs[Index].A + Segs[Index].B) * 0.5;
		SegGrid.FindOrAdd(CellOf(Mid, SegCellCm)).Add(Index);
	}

	// 3. The swept boxes: the physics sweep for the solid ones, positions for every class.
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTRouteClear), /*bTraceComplex*/ false);
	Params.AddIgnoredActors(Ignored);
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	const FCollisionShape Shape = FCollisionShape::MakeBox(FVector(BoxHalfLengthCm, BoxHalfWidthCm, BoxHalfHeightCm));
	TSet<TPair<const UPrimitiveComponent*, int32>> SweepSolid;
	int32 SweepOther = 0;
	TSet<int32> Inside[3];
	FString FirstInside[3];
	FString FirstSweep;
	int32 Sweeps = 0;
	for (const FSeg& S : Segs)
	{
		const FVector2D AB = S.B - S.A;
		const double Len = AB.Size();
		if (Len < 1.0)
		{
			continue;
		}
		const FVector2D Dir = AB / Len;
		const FQuat Rot(FRotator(0.f, static_cast<float>(FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X))), 0.f));
		const FVector From(S.A, S.GroundA + BoxLiftCm + BoxHalfHeightCm);
		const FVector To(S.B, S.GroundB + BoxLiftCm + BoxHalfHeightCm);
		TArray<FHitResult> Hits;
		W->SweepMultiByObjectType(Hits, From, To, Rot, Objects, Shape, Params);
		++Sweeps;
		for (const FHitResult& Hit : Hits)
		{
			const UPrimitiveComponent* Comp = Hit.GetComponent();
			if (Comp && Comp->ComponentTags.Contains(SolidTag))
			{
				bool bAlready = false;
				SweepSolid.Add(TPair<const UPrimitiveComponent*, int32>(Comp, Hit.Item), &bAlready);
				if (!bAlready && FirstSweep.IsEmpty())
				{
					FirstSweep = FString::Printf(TEXT("%s.%s instance %d at (%.0f, %.0f) m, route line %d arc %.0f m"), Comp->GetOwner() ? *Comp->GetOwner()->GetName() : TEXT("?"), *Comp->GetName(), Hit.Item,
						Hit.ImpactPoint.X / 100.f, Hit.ImpactPoint.Y / 100.f, S.Line, S.ArcM);
				}
			}
			else if (Comp)
			{
				++SweepOther;
			}
		}
		// The swept box's footprint: the segment's length plus the box's, as wide as the box.
		const FVector2D Centre = (S.A + S.B) * 0.5;
		const double HalfLength = 0.5 * Len + BoxHalfLengthCm;
		const double Reach = FMath::Sqrt(HalfLength * HalfLength + BoxHalfWidthCm * BoxHalfWidthCm) + MaxRadiusCm;
		const FIntPoint Lo = CellOf(Centre - FVector2D(Reach, Reach), PlantCellCm);
		const FIntPoint Hi = CellOf(Centre + FVector2D(Reach, Reach), PlantCellCm);
		for (int32 CY = Lo.Y; CY <= Hi.Y; ++CY)
		{
			for (int32 CX = Lo.X; CX <= Hi.X; ++CX)
			{
				const TArray<int32>* Cell = PlantGrid.Find(FIntPoint(CX, CY));
				if (!Cell)
				{
					continue;
				}
				for (const int32 Index : *Cell)
				{
					const FPlant& P = Plants[Index];
					const FVector2D Local = FVector2D(P.Location) - Centre;
					const double Along = FVector2D::DotProduct(Local, Dir);
					const double Across = FVector2D::CrossProduct(Dir, Local);
					const double DX = FMath::Max(0.0, FMath::Abs(Along) - HalfLength);
					const double DY = FMath::Max(0.0, FMath::Abs(Across) - BoxHalfWidthCm);
					if (DX * DX + DY * DY > static_cast<double>(P.RadiusCm) * P.RadiusCm)
					{
						continue;
					}
					const float T = static_cast<float>(FMath::Clamp(0.5 + Along / FMath::Max(1.0, Len), 0.0, 1.0));
					const float Bottom = FMath::Lerp(S.GroundA, S.GroundB, T) + BoxLiftCm;
					const float Top = Bottom + 2.f * BoxHalfHeightCm;
					if (P.Location.Z > Top || P.Location.Z + FMath::Max(P.HeightCm, 1.f) < Bottom)
					{
						continue;
					}
					const int32 K = static_cast<int32>(P.Kind);
					bool bAlready = false;
					Inside[K].Add(Index, &bAlready);
					if (!bAlready && FirstInside[K].IsEmpty())
					{
						FirstInside[K] = FString::Printf(TEXT("at (%.0f, %.0f, %.0f) m, radius %.2f m, route line %d arc %.0f m, %.2f m across"),
							P.Location.X / 100.f, P.Location.Y / 100.f, P.Location.Z / 100.f, P.RadiusCm / 100.f, S.Line, S.ArcM, Across / 100.0);
					}
				}
			}
		}
	}
	Line(FString::Printf(TEXT("corridor: %d swept boxes (3 x 4 x 2 m, every 2 m) along the main route and %d alt route(s): the sweep hit %d Solid instance(s)%s (%d other hit(s) on the dressing); inside by position: Solid %d%s, Soft (the hash's contact circles) %d%s, unclassed %d%s"),
		Sweeps, Spec.AltRoutes.Num(), SweepSolid.Num(), FirstSweep.IsEmpty() ? TEXT("") : *FString::Printf(TEXT(", the first %s"), *FirstSweep), SweepOther,
		Inside[0].Num(), FirstInside[0].IsEmpty() ? TEXT("") : *FString::Printf(TEXT(" (the first %s)"), *FirstInside[0]),
		Inside[1].Num(), FirstInside[1].IsEmpty() ? TEXT("") : *FString::Printf(TEXT(" (the first %s)"), *FirstInside[1]),
		Inside[2].Num(), FirstInside[2].IsEmpty() ? TEXT("") : *FString::Printf(TEXT(" (the first %s)"), *FirstInside[2])));
	if (SweepSolid.Num() > 0 || Inside[0].Num() > 0 || Inside[1].Num() > 0 || Inside[2].Num() > 0)
	{
		Failures.Add(FString::Printf(TEXT("corridor: sweep %d Solid; inside Solid %d, Soft %d, unclassed %d (want 0)"), SweepSolid.Num(), Inside[0].Num(), Inside[1].Num(), Inside[2].Num()));
	}
	else
	{
		Notes.Add(FString::Printf(TEXT("corridor clear: %d boxes, 0 Solid swept, 0 Soft in the hash"), Sweeps));
	}

	// 4. Information: the nearest instance of each class to a centreline, and the edge bands.
	float Nearest[3] = { 1.e9f, 1.e9f, 1.e9f };
	FString NearestWhere[3];
	int32 NearCorridor[3] = { 0, 0, 0 };
	int32 NearRoad[3] = { 0, 0, 0 };
	int32 Measured = 0;
	for (const FPlant& P : Plants)
	{
		const FVector2D XY(P.Location);
		const FIntPoint C = CellOf(XY, SegCellCm);
		float Best = 1.e9f;
		const FSeg* BestSeg = nullptr;
		for (int32 DY = -1; DY <= 1; ++DY)
		{
			for (int32 DX = -1; DX <= 1; ++DX)
			{
				if (const TArray<int32>* Cell = SegGrid.Find(C + FIntPoint(DX, DY)))
				{
					for (const int32 Index : *Cell)
					{
						const float D = DistToSeg(XY, Segs[Index].A, Segs[Index].B);
						if (D < Best)
						{
							Best = D;
							BestSeg = &Segs[Index];
						}
					}
				}
			}
		}
		if (!BestSeg)
		{
			continue;   // over 20 m from every centreline
		}
		++Measured;
		const int32 K = static_cast<int32>(P.Kind);
		const float Edge = Best - P.RadiusCm;
		if (Edge < Nearest[K])
		{
			Nearest[K] = Edge;
			NearestWhere[K] = FString::Printf(TEXT("%.2f m (pivot %.2f m, radius %.2f m) at (%.0f, %.0f) m, route line %d arc %.0f m, road half width %.1f m"),
				Edge / 100.f, Best / 100.f, P.RadiusCm / 100.f, XY.X / 100.f, XY.Y / 100.f, BestSeg->Line, BestSeg->ArcM, BestSeg->RoadHalfWidthCm / 100.f);
		}
		NearCorridor[K] += Edge < BoxHalfWidthCm + EdgeBandCm ? 1 : 0;
		NearRoad[K] += Edge < BestSeg->RoadHalfWidthCm + EdgeBandCm ? 1 : 0;
	}
	for (int32 K = 0; K < 3; ++K)
	{
		Line(FString::Printf(TEXT("nearest %s instance to a centreline: %s; within 2 m of the corridor's edge (%.1f m from the centreline): %d; within 2 m of the road's edge: %d"),
			KindName(static_cast<EKind>(K)), Nearest[K] < 1.e8f ? *NearestWhere[K] : TEXT("none within 20 m"), BoxHalfWidthCm / 100.f, NearCorridor[K], NearRoad[K]));
	}
	Line(FString::Printf(TEXT("%d of %d instances stand within 20 m of a centreline"), Measured, Plants.Num()));
	Notes.Add(FString::Printf(TEXT("nearest Solid %.2f m, Soft %.2f m (edge of its circle), unclassed %.2f m from a centreline; within 2 m of the corridor's edge %d/%d/%d"),
		Nearest[0] < 1.e8f ? Nearest[0] / 100.f : -1.f, Nearest[1] < 1.e8f ? Nearest[1] / 100.f : -1.f, Nearest[2] < 1.e8f ? Nearest[2] / 100.f : -1.f,
		NearCorridor[0], NearCorridor[1], NearCorridor[2]));

	// 5. The gameplay points: no dressing within 5 m of their bounds (2D, the positions; soft ones their pivots).
	int32 Points = 0;
	int32 Violations = 0;
	FString Worst;
	for (TActorIterator<AActor> It(W); It; ++It)
	{
		AActor* Actor = *It;
		if (!Actor || Actor->IsA<APawn>() || !Actor->HasAnyFlags(RF_WasLoaded))
		{
			continue;
		}
		const bool bGameplay = Actor->IsA<AGTLegStart>() || Actor->IsA<AGTCheckpoint>() || Actor->IsA<AGTExtractionZone>()
			|| Actor->GetClass()->ImplementsInterface(UGTInteractable::StaticClass()) || Actor->FindComponentByClass<UGTInteractionComponent>() != nullptr;
		if (!bGameplay)
		{
			continue;
		}
		// The exclusion's own bounds (AGTDressingExclusion): colliding components, else all; empty bounds left out.
		auto BoundsOf = [Actor](bool bNonColliding)
		{
			FBox Box(ForceInit);
			TInlineComponentArray<UPrimitiveComponent*> Prims;
			Actor->GetComponents(Prims, /*bIncludeFromChildActors*/ true);
			for (const UPrimitiveComponent* Prim : Prims)
			{
				if (Prim && Prim->IsRegistered() && (bNonColliding || Prim->IsCollisionEnabled()) && Prim->Bounds.BoxExtent.GetMax() > 1.0)
				{
					Box += Prim->Bounds.GetBox();
				}
			}
			return Box;
		};
		FBox Bounds = BoundsOf(/*bNonColliding*/ false);
		if (!Bounds.IsValid)
		{
			Bounds = BoundsOf(/*bNonColliding*/ true);
		}
		if (!Bounds.IsValid)
		{
			Bounds = FBox(Actor->GetActorLocation(), Actor->GetActorLocation());
		}
		++Points;
		const FBox2D Box(FVector2D(Bounds.Min), FVector2D(Bounds.Max));
		const FBox2D Zone = Box.ExpandBy(GameplayMarginCm);
		int32 Within = 0;
		float NearestCm = 1.e9f;
		FString Examples;
		const FIntPoint Lo = CellOf(Zone.Min - FVector2D(2000.0, 2000.0), PlantCellCm);
		const FIntPoint Hi = CellOf(Zone.Max + FVector2D(2000.0, 2000.0), PlantCellCm);
		for (int32 CY = Lo.Y; CY <= Hi.Y; ++CY)
		{
			for (int32 CX = Lo.X; CX <= Hi.X; ++CX)
			{
				if (const TArray<int32>* Cell = PlantGrid.Find(FIntPoint(CX, CY)))
				{
					for (const int32 Index : *Cell)
					{
						const FVector2D XY(Plants[Index].Location);
						const float D = static_cast<float>(FMath::Sqrt(Box.ComputeSquaredDistanceToPoint(XY)));
						NearestCm = FMath::Min(NearestCm, D);
						if (D <= GameplayMarginCm)
						{
							++Within;
							if (Within <= 3)
							{
								Examples += FString::Printf(TEXT(" %s at (%.1f, %.1f) m %.1f m from the bounds;"), KindName(Plants[Index].Kind), XY.X / 100.f, XY.Y / 100.f, D / 100.f);
							}
						}
					}
				}
			}
		}
		Line(FString::Printf(TEXT("gameplay %s (%s at (%.1f, %.1f) m, bounds %.1f x %.1f m centred (%.1f, %.1f)): %d instance(s) within 5 m of its bounds; the nearest %s%s"),
			*Actor->GetName(), *Actor->GetClass()->GetName(), Actor->GetActorLocation().X / 100.f, Actor->GetActorLocation().Y / 100.f,
			Box.GetSize().X / 100.f, Box.GetSize().Y / 100.f, Box.GetCenter().X / 100.f, Box.GetCenter().Y / 100.f, Within,
			NearestCm < 1.e8f ? *FString::Printf(TEXT("%.1f m from them"), NearestCm / 100.f) : TEXT("over 20 m away"), *Examples));
		if (Within > 0)
		{
			++Violations;
			if (Worst.IsEmpty())
			{
				Worst = FString::Printf(TEXT("%s (%d)"), *Actor->GetName(), Within);
			}
		}
	}
	if (Points == 0)
	{
		Failures.Add(TEXT("gameplay: no start, checkpoint, extraction zone or interactable on the map"));
	}
	else if (Violations > 0)
	{
		Failures.Add(FString::Printf(TEXT("gameplay: %d of %d points have dressing within 5 m (the first %s)"), Violations, Points, *Worst));
	}
	else
	{
		Notes.Add(FString::Printf(TEXT("%d gameplay points clear by 5 m"), Points));
	}
	Line(FString::Printf(TEXT("judged in %.2f s"), FPlatformTime::Seconds() - Start));
}
