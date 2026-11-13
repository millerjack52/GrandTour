// Deformable gravel DG1 item 3 (docs/DEFORMABLE_GRAVEL_PLAN.md DG1): the loose stones. See GTGravelStones.h.
#include "Terrain/GTGravelStones.h"

#include "Terrain/GTMudPatch.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/PackageName.h"

static TAutoConsoleVariable<int32> CVarGravelStones(
	TEXT("gt.Gravel.Stones"), 1,
	TEXT("Deformable gravel DG1: 1 the gravel patches draw the study's loose stones (pushed aside, pressed in or flicked by the wheels); 0 none (no instances)."));
static TAutoConsoleVariable<float> CVarGravelStoneDensity(
	TEXT("gt.Gravel.StoneDensity"), 1.f,
	TEXT("Deformable gravel DG1: the loose stones' density scale, 0-1 (1 = the profile's own: about 30 per m^2 Loose, 12 Firm), for the owner's cost tests."));

const TCHAR* const UGTGravelStones::MeshPaths[4] = {
	TEXT("/Game/GrandTour/ArtTests/GravelRoad/SM_GR_Stone1.SM_GR_Stone1"), TEXT("/Game/GrandTour/ArtTests/GravelRoad/SM_GR_Stone2.SM_GR_Stone2"),
	TEXT("/Game/GrandTour/ArtTests/GravelRoad/SM_GR_Stone3.SM_GR_Stone3"), TEXT("/Game/GrandTour/ArtTests/GravelRoad/SM_GR_Stone4.SM_GR_Stone4") };
const TCHAR* const UGTGravelStones::MaterialPath = TEXT("/Game/GrandTour/ArtTests/DeformableGravel/M_GT_GravelStone.M_GT_GravelStone");

namespace
{
	double StoneSegmentDistance(const FVector2D& P, const FVector2D& A, const FVector2D& B)
	{
		const FVector2D AB = B - A;
		const double L2 = AB.SizeSquared();
		const double T = L2 > 1e-6 ? FMath::Clamp(FVector2D::DotProduct(P - A, AB) / L2, 0.0, 1.0) : 0.0;
		return FVector2D::Distance(P, A + AB * T);
	}

	float StoneHash(int32 X, int32 Y, int32 Seed)
	{
		uint32 H = static_cast<uint32>(X) * 73856093u ^ static_cast<uint32>(Y) * 19349663u ^ static_cast<uint32>(Seed) * 83492791u;
		H ^= H >> 13;
		H *= 0x5bd1e995u;
		H ^= H >> 15;
		return static_cast<float>(H & 0xFFFFFF) / static_cast<float>(0x1000000);
	}

	/** Value noise in 0..1 over unit cells, smoothstepped. */
	float StoneNoise(const FVector2D& C, int32 Seed)
	{
		const int32 X = FMath::FloorToInt(C.X);
		const int32 Y = FMath::FloorToInt(C.Y);
		float FX = static_cast<float>(C.X - X);
		float FY = static_cast<float>(C.Y - Y);
		FX = FX * FX * (3.f - 2.f * FX);
		FY = FY * FY * (3.f - 2.f * FY);
		return FMath::Lerp(FMath::Lerp(StoneHash(X, Y, Seed), StoneHash(X + 1, Y, Seed), FX),
			FMath::Lerp(StoneHash(X, Y + 1, Seed), StoneHash(X + 1, Y + 1, Seed), FX), FY);
	}
}

UGTGravelStones::UGTGravelStones()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = true;
}

bool UGTGravelStones::IsEnabled()
{
	return CVarGravelStones.GetValueOnGameThread() != 0;
}

float UGTGravelStones::DensityScale()
{
	return FMath::Clamp(CVarGravelStoneDensity.GetValueOnGameThread(), 0.f, 1.f);
}

bool UGTGravelStones::EnsureMeshes()
{
	if (Meshes.Num() > 0)
	{
		return true;
	}
	AActor* Owner = GetOwner();
	if (!Owner)
	{
		return false;
	}
	UMaterialInterface* Material = FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(FString(MaterialPath)))
		? LoadObject<UMaterialInterface>(nullptr, MaterialPath, nullptr, LOAD_NoWarn | LOAD_Quiet) : nullptr;
	for (int32 Index = 0; Index < 4; ++Index)
	{
		const FString Path(MeshPaths[Index]);
		UStaticMesh* Mesh = FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(Path))
			? LoadObject<UStaticMesh>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet) : nullptr;
		if (!Mesh)
		{
			continue;
		}
		UHierarchicalInstancedStaticMeshComponent* Hism = NewObject<UHierarchicalInstancedStaticMeshComponent>(Owner, *FString::Printf(TEXT("GravelStones_%d"), Index + 1), RF_Transient);
		Hism->SetStaticMesh(Mesh);
		Hism->SetMobility(EComponentMobility::Movable);
		Hism->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Hism->SetCanEverAffectNavigation(false);
		Hism->SetCastShadow(true);
		Hism->SetCullDistances(FMath::RoundToInt(CullStartCm), FMath::RoundToInt(FMath::Max(CullStartCm, CullEndCm)));
		if (Material)
		{
			Hism->SetMaterial(0, Material);
		}
		Hism->SetupAttachment(this);
		Hism->RegisterComponent();
		Meshes.Add(Hism);
		const FBox Box = Mesh->GetBoundingBox();
		MeshAcrossCm.Add(Box.IsValid ? FMath::Max(1.f, static_cast<float>(FMath::Max(Box.Max.X - Box.Min.X, Box.Max.Y - Box.Min.Y))) : 100.f);
		MeshMinZ.Add(Box.IsValid ? static_cast<float>(Box.Min.Z) : 0.f);
		MeshHeight.Add(Box.IsValid ? FMath::Max(0.1f, static_cast<float>(Box.Max.Z - Box.Min.Z)) : 60.f);
	}
	if (Meshes.Num() == 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTGravelStones: no SM_GR_Stone mesh under /Game/GrandTour/ArtTests/GravelRoad (Art/import_gravel_road.ps1): no stones"));
	}
	return Meshes.Num() > 0;
}

float UGTGravelStones::SurfaceZ(const FVector2D& XY) const
{
	const AGTMudPatch* P = Patch.Get();
	return P ? P->MeshRestZAt(XY) + P->GetField().HeightAt(XY) : 0.f;
}

FVector UGTGravelStones::SurfaceNormal(const FVector2D& XY) const
{
	const float D = 8.f;
	const float DX = SurfaceZ(XY + FVector2D(D, 0.0)) - SurfaceZ(XY - FVector2D(D, 0.0));
	const float DY = SurfaceZ(XY + FVector2D(0.0, D)) - SurfaceZ(XY - FVector2D(0.0, D));
	return FVector(-DX, -DY, 2.f * D).GetSafeNormal();
}

float UGTGravelStones::LateralCm(const FVector2D& XY) const
{
	if (RouteCm.Num() < 2)
	{
		return 0.f;
	}
	// The route line with its two end segments extended 20 m, so the patch's margins beyond the section measure across the road.
	double Best = 1.0e9;
	for (int32 K = 0; K + 1 < RouteCm.Num(); ++K)
	{
		FVector2D A = RouteCm[K];
		FVector2D B = RouteCm[K + 1];
		const FVector2D Dir = (B - A).GetSafeNormal();
		if (K == 0)
		{
			A -= Dir * 2000.0;
		}
		if (K + 2 == RouteCm.Num())
		{
			B += Dir * 2000.0;
		}
		Best = FMath::Min(Best, StoneSegmentDistance(XY, A, B));
	}
	return static_cast<float>(Best);
}

float UGTGravelStones::Weight(const FVector2D& XY, int32 Seed) const
{
	// Benmore B2: a zone patch's stones only on its own zone cells.
	if (const AGTMudPatch* Owner = Patch.Get(); Owner && !Owner->KeepsDecorAt(XY))
	{
		return 0.f;
	}
	const float Lateral = LateralCm(XY);
	if (Lateral > RoadHalfCm)
	{
		return 0.f;
	}
	const double Along = FVector2D::DotProduct(XY, RouteDir);
	const float Taper = FMath::SmoothStep(static_cast<float>(AlongMin), static_cast<float>(AlongMin + EndTaperCm), static_cast<float>(Along))
		* (1.f - FMath::SmoothStep(static_cast<float>(AlongMax - EndTaperCm), static_cast<float>(AlongMax), static_cast<float>(Along)));
	float N = StoneNoise(XY / FMath::Max(1.f, ClusterCm), Seed);
	if (ClusterOctave2 > 0.f)
	{
		N = FMath::Lerp(N, StoneNoise(XY / FMath::Max(1.f, ClusterCm2) + FVector2D(37.1, -11.3), Seed + 7), ClusterOctave2);
	}
	if (ClusterSharpen > 0.f)
	{
		N = FMath::SmoothStep(0.5f - ClusterSharpen, 0.5f + ClusterSharpen, N);
	}
	const float Cluster = FMath::Lerp(ClusterMin, ClusterMax, N);
	const bool bBoost = Lateral < CrownHalfCm || Lateral > RoadHalfCm - EdgeBandCm;
	return Taper * Cluster * (bBoost ? EdgeCrownBoost : 1.f);
}

int32 UGTGravelStones::GridCellAt(const FVector2D& XY) const
{
	const int32 X = FMath::Clamp(FMath::FloorToInt((XY.X - GridOrigin.X) / GridCm), 0, FMath::Max(0, GridX - 1));
	const int32 Y = FMath::Clamp(FMath::FloorToInt((XY.Y - GridOrigin.Y) / GridCm), 0, FMath::Max(0, GridY - 1));
	return Y * GridX + X;
}

void UGTGravelStones::GridAdd(int32 Index)
{
	if (Grid.Num() > 0)
	{
		Grid[GridCellAt(Stones[Index].XY)].Add(Index);
	}
}

void UGTGravelStones::GridRemove(int32 Index)
{
	if (Grid.Num() > 0)
	{
		Grid[GridCellAt(Stones[Index].XY)].RemoveSingleSwap(Index);
	}
}

FTransform UGTGravelStones::StoneTransform(const FStone& Stone) const
{
	const int32 M = FMath::Clamp(Stone.Mesh, 0, MeshAcrossCm.Num() - 1);
	const float Scale = Stone.SizeCm / MeshAcrossCm[M];
	const FVector Scale3 = Stone.Stretch * Scale;
	const FVector Up(0.0, 0.0, 1.0);
	const FQuat Align = FQuat::FindBetweenNormals(Up, SurfaceNormal(Stone.XY));
	const FQuat Tilt(FVector(Stone.TiltAxis.X, Stone.TiltAxis.Y, 0.0).GetSafeNormal(), FMath::DegreesToRadians(Stone.TiltDeg));
	const FQuat Yaw(Up, FMath::DegreesToRadians(Stone.YawDeg));
	const float Z = SurfaceZ(Stone.XY) - (MeshMinZ[M] + Stone.Sink * MeshHeight[M]) * static_cast<float>(Scale3.Z);
	return FTransform(Align * Tilt * Yaw, FVector(Stone.XY.X, Stone.XY.Y, Z), Scale3);
}

void UGTGravelStones::Apply(int32 Index, bool bMarkDirty)
{
	const FStone& Stone = Stones[Index];
	if (Meshes.IsValidIndex(Stone.Mesh) && Meshes[Stone.Mesh] && Stone.Instance != INDEX_NONE)
	{
		Meshes[Stone.Mesh]->UpdateInstanceTransform(Stone.Instance, StoneTransform(Stone), true, bMarkDirty, true);
	}
}

int32 UGTGravelStones::NumInstances() const
{
	int32 N = 0;
	for (const UHierarchicalInstancedStaticMeshComponent* Hism : Meshes)
	{
		N += Hism ? Hism->GetInstanceCount() : 0;
	}
	return N;
}

void UGTGravelStones::Clear()
{
	for (UHierarchicalInstancedStaticMeshComponent* Hism : Meshes)
	{
		if (Hism)
		{
			Hism->ClearInstances();
		}
	}
	Stones.Reset();
	Flights.Reset();
	FlickStarts.Reset();
	Grid.Reset();
	PlacedAreaM2 = 0.f;
	TargetCount = 0;
}

int32 UGTGravelStones::Build(AGTMudPatch& InPatch, int32 Seed, float InDensityPerM2, float InRoadHalfCm)
{
	Patch = &InPatch;
	BuiltSeed = Seed;
	BuiltProfileDensity = InDensityPerM2;
	BuiltEnabled = IsEnabled() ? 1 : 0;
	BuiltScale = DensityScale();
	RoadHalfCm = FMath::Max(50.f, InRoadHalfCm);
	DensityPerM2 = FMath::Max(0.f, InDensityPerM2) * BuiltScale;
	PressDebt = 0.f;
	FlickDebt = 0.f;
	PushCount = 0;
	Clear();
	const FGTMudField& Field = InPatch.GetField();
	if (!BuiltEnabled || DensityPerM2 <= 0.f || !Field.IsValid() || !EnsureMeshes())
	{
		return 0;
	}
	const FBox2D Box = Field.Bounds();
	RouteCm = InPatch.GetRouteLine();
	if (RouteCm.Num() < 2)
	{
		RouteCm = { FVector2D(Box.Min.X, Box.GetCenter().Y), FVector2D(Box.Max.X, Box.GetCenter().Y) };
	}
	RouteDir = (RouteCm.Last() - RouteCm[0]).GetSafeNormal();
	AlongMin = 1.0e9f;
	AlongMax = -1.0e9f;
	for (const FVector2D& Corner : { Box.Min, Box.Max, FVector2D(Box.Min.X, Box.Max.Y), FVector2D(Box.Max.X, Box.Min.Y) })
	{
		const float A = static_cast<float>(FVector2D::DotProduct(Corner, RouteDir));
		AlongMin = FMath::Min(AlongMin, A);
		AlongMax = FMath::Max(AlongMax, A);
	}
	// The area the target spreads over: the road inside the patch, its two ends' taper weighted in (25 cm samples).
	const float Sample = 25.f;
	double Area = 0.0;
	// DG1b: the target is renormalised over the section's own span and over the patch's margins separately, so the section's density
	// is its profile's number whatever the cluster noise does near the ends.
	const float SecA = static_cast<float>(FVector2D::DotProduct(RouteCm[0], RouteDir));
	const float SecB = static_cast<float>(FVector2D::DotProduct(RouteCm.Last(), RouteDir));
	const float SecLo = FMath::Min(SecA, SecB);
	const float SecHi = FMath::Max(SecA, SecB);
	double AreaSection = 0.0;
	double WeightMax = 0.0;
	for (float Y = Box.Min.Y + 0.5f * Sample; Y < Box.Max.Y; Y += Sample)
	{
		for (float X = Box.Min.X + 0.5f * Sample; X < Box.Max.X; X += Sample)
		{
			const FVector2D P(X, Y);
			if (LateralCm(P) <= RoadHalfCm)
			{
				const double Along = FVector2D::DotProduct(P, RouteDir);
				const double Cell = FMath::SmoothStep(AlongMin, AlongMin + EndTaperCm, static_cast<float>(Along)) * (1.f - FMath::SmoothStep(AlongMax - EndTaperCm, AlongMax, static_cast<float>(Along)));
				Area += Cell;
				AreaSection += (Along >= SecLo && Along <= SecHi) ? Cell : 0.0;
			}
		}
	}
	PlacedAreaM2 = static_cast<float>(Area * Sample * Sample / 10000.0);
	const int32 TargetSection = FMath::RoundToInt(DensityPerM2 * static_cast<float>(AreaSection * Sample * Sample / 10000.0));
	TargetCount = TargetSection + FMath::RoundToInt(DensityPerM2 * static_cast<float>((Area - AreaSection) * Sample * Sample / 10000.0));
	WeightMax = ClusterMax * EdgeCrownBoost;
	FRandomStream Random(0x6A7E1 + Seed * 7919);
	GridOrigin = Box.Min;
	GridX = FMath::Max(1, FMath::CeilToInt(Box.GetSize().X / GridCm));
	GridY = FMath::Max(1, FMath::CeilToInt(Box.GetSize().Y / GridCm));
	Grid.SetNum(GridX * GridY);
	TArray<TArray<FTransform>> PerMesh;
	PerMesh.SetNum(Meshes.Num());
	Stones.Reserve(TargetCount);
	const int64 MaxTries = static_cast<int64>(TargetCount) * 400 + 1000;
	const float Lo = FMath::Pow(SizeMinCm / SizeMaxCm, SizeAlpha);
	for (int64 Try = 0; Try < MaxTries && Stones.Num() < TargetCount; ++Try)
	{
		const FVector2D P(Random.FRandRange(Box.Min.X, Box.Max.X), Random.FRandRange(Box.Min.Y, Box.Max.Y));
		// The section's stones first, then the margins'.
		const float PAlong = static_cast<float>(FVector2D::DotProduct(P, RouteDir));
		const bool bInSection = PAlong >= SecLo && PAlong <= SecHi;
		if (bInSection != (Stones.Num() < TargetSection))
		{
			continue;
		}
		const float W = Weight(P, Seed);
		const float Gate = Random.FRand();
		if (W <= 0.f || Gate * WeightMax > W)
		{
			continue;
		}
		FStone Stone;
		Stone.XY = P;
		// The truncated power law: most small, a few at SizeMaxCm.
		Stone.SizeCm = SizeMinCm / FMath::Pow(1.f - Random.FRand() * (1.f - Lo), 1.f / SizeAlpha);
		Stone.SizeCm = FMath::Clamp(Stone.SizeCm, SizeMinCm, SizeMaxCm);
		Stone.YawDeg = Random.FRandRange(-180.f, 180.f);
		const float AxisAngle = Random.FRandRange(0.f, 2.f * PI);
		Stone.TiltAxis = FVector2D(FMath::Cos(AxisAngle), FMath::Sin(AxisAngle));
		Stone.TiltDeg = Random.FRandRange(0.f, TiltDeg);
		Stone.Stretch = FVector(Random.FRandRange(0.9f, 1.35f), 1.f, Random.FRandRange(0.7f, 1.1f));
		Stone.Sink = Random.FRandRange(SinkMin, SinkMax);
		Stone.Mesh = Random.RandHelper(Meshes.Num());
		Stone.Instance = PerMesh[Stone.Mesh].Num();
		const int32 Index = Stones.Add(Stone);
		PerMesh[Stone.Mesh].Add(StoneTransform(Stones[Index]));
		GridAdd(Index);
	}
	for (int32 M = 0; M < Meshes.Num(); ++M)
	{
		if (PerMesh[M].Num() > 0)
		{
			Meshes[M]->AddInstances(PerMesh[M], false, true);
		}
	}
	UE_LOG(LogTemp, Display, TEXT("UGTGravelStones: patch %d, %d stones (target %d = %.1f per m^2 over %.1f m^2 of road), %d meshes (DG1)"),
		Seed, Stones.Num(), TargetCount, DensityPerM2, PlacedAreaM2, Meshes.Num());
	return Stones.Num();
}

UGTGravelStones::FPushResult UGTGravelStones::PushUnderWheel(const FVector2D& FromCm, const FVector2D& ToCm, float HalfWidthCm, const FVector2D& Travel, float Slip)
{
	FPushResult Result;
	if (Stones.Num() == 0 || Grid.Num() == 0 || HalfWidthCm <= 0.f)
	{
		return Result;
	}
	const FVector2D AB = ToCm - FromCm;
	const float Length = static_cast<float>(AB.Size());
	const FVector2D Dir = Length > 0.5f ? AB / Length : (Travel.IsNearlyZero() ? FVector2D(1.0, 0.0) : Travel.GetSafeNormal());
	const FVector2D Perp(-Dir.Y, Dir.X);
	const FVector2D Back = -(Travel.IsNearlyZero() ? Dir : Travel.GetSafeNormal());
	const float Reach = HalfWidthCm * (1.f + PushMax) + 5.f;
	const int32 C0 = GridCellAt(FVector2D(FMath::Min(FromCm.X, ToCm.X) - Reach, FMath::Min(FromCm.Y, ToCm.Y) - Reach));
	const int32 C1 = GridCellAt(FVector2D(FMath::Max(FromCm.X, ToCm.X) + Reach, FMath::Max(FromCm.Y, ToCm.Y) + Reach));
	TArray<int32, TInlineAllocator<32>> Inside;
	TArray<int32, TInlineAllocator<64>> Near;
	for (int32 GY = C0 / GridX; GY <= C1 / GridX; ++GY)
	{
		for (int32 GX = C0 % GridX; GX <= C1 % GridX; ++GX)
		{
			for (const int32 Index : Grid[GY * GridX + GX])
			{
				const double D = StoneSegmentDistance(Stones[Index].XY, FromCm, ToCm);
				// A pressed stone stays pressed: the next tick's capsule, the rear wheel and a repeat pass roll over it (it only settles).
				if (D < HalfWidthCm && Stones[Index].State != 2)
				{
					Inside.Add(Index);
				}
				else if (D < Reach)
				{
					Near.Add(Index);
				}
			}
		}
	}
	// Along the stroke, so the order (and the shares' dither) never depends on the grid.
	Inside.Sort([this, &FromCm, &Dir](int32 A, int32 B) { return FVector2D::DotProduct(Stones[A].XY - FromCm, Dir) < FVector2D::DotProduct(Stones[B].XY - FromCm, Dir); });
	Result.Inside = Inside.Num();
	const float FlickShare = Slip > FlickSlipMin ? FMath::Min(Slip, FlickShareMax) : 0.f;
	FRandomStream Random(static_cast<int32>(0x51A7E + BuiltSeed * 131 + static_cast<int32>(PushCount++) * 7));
	const FBox2D Box = Patch.IsValid() ? Patch->GetField().Bounds() : FBox2D(FVector2D(-1.0e9, -1.0e9), FVector2D(1.0e9, 1.0e9));
	const FBox2D Keep(Box.Min + FVector2D(10.0, 10.0), Box.Max - FVector2D(10.0, 10.0));
	TSet<int32> Dirty;
	for (const int32 Index : Inside)
	{
		FStone& Stone = Stones[Index];
		// The shares by a dithered running total: exact over many stones, never a fixed rhythm.
		FlickDebt += FlickShare * (1.f + 0.8f * (Random.FRand() - 0.5f));
		const bool bFlick = FlickShare > 0.f && FlickDebt >= 1.f;
		bool bPress = false;
		if (bFlick)
		{
			FlickDebt -= 1.f;
		}
		else
		{
			PressDebt += PressedShare * (1.f + 0.8f * (Random.FRand() - 0.5f));
			bPress = PressDebt >= 1.f;
			if (bPress)
			{
				PressDebt -= 1.f;
			}
		}
		GridRemove(Index);
		if (bFlick)
		{
			const FVector2D Start = Stone.XY;
			const float Angle = FMath::DegreesToRadians(Random.FRandRange(-FlickSpreadDeg, FlickSpreadDeg));
			const FVector2D Way(Back.X * FMath::Cos(Angle) - Back.Y * FMath::Sin(Angle), Back.X * FMath::Sin(Angle) + Back.Y * FMath::Cos(Angle));
			const float Distance = Random.FRandRange(FlickMinCm, FlickMaxCm);
			FFlight Flight;
			Flight.Stone = Index;
			Flight.From = StoneTransform(Stone).GetLocation();
			Flight.Duration = 0.3f + 0.12f * Distance / 100.f;
			Flight.ArcCm = FMath::Min(40.f, 0.18f * Distance);
			Stone.XY = FVector2D(FMath::Clamp(Start.X + Way.X * Distance, Keep.Min.X, Keep.Max.X), FMath::Clamp(Start.Y + Way.Y * Distance, Keep.Min.Y, Keep.Max.Y));
			Stone.YawDeg = Random.FRandRange(-180.f, 180.f);
			Stone.Sink = Random.FRandRange(SinkMin, SinkMax);
			Stone.State = 3;
			FlickStarts.Add(Index, Start);
			Flights.Add(Flight);
			Result.Thrown.Add(Index);
			++Result.Flicked;
		}
		else if (bPress)
		{
			Stone.Sink = PressedSink;
			Stone.State = 2;
			Dirty.Add(Index);
			++Result.Pressed;
		}
		else
		{
			// Out sideways to the nearer edge, PushMin..PushMax half-widths past it, jittered along the stroke (kept within it).
			const float T = FMath::Clamp(static_cast<float>(FVector2D::DotProduct(Stone.XY - FromCm, Dir)), 0.f, Length);
			const FVector2D OnAxis = FromCm + Dir * T;
			const float Side = FVector2D::DotProduct(Stone.XY - OnAxis, Perp) >= 0.0 ? 1.f : -1.f;
			const float Lateral = HalfWidthCm * (1.f + Random.FRandRange(PushMin, PushMax));
			const float T2 = FMath::Clamp(T + Random.FRandRange(-PushJitter, PushJitter) * HalfWidthCm, 0.f, Length);
			const FVector2D To = FromCm + Dir * T2 + Perp * (Side * Lateral);
			Stone.XY = FVector2D(FMath::Clamp(To.X, Keep.Min.X, Keep.Max.X), FMath::Clamp(To.Y, Keep.Min.Y, Keep.Max.Y));
			Stone.YawDeg = Random.FRandRange(-180.f, 180.f);
			Stone.Sink = Random.FRandRange(SinkMin, SinkMax);
			Stone.State = 1;
			Dirty.Add(Index);
			Result.Moved.Add(Index);
			++Result.Pushed;
		}
		GridAdd(Index);
	}
	// The stones round the stroke settle on the field as it is now (the rut cut, the windrow raised).
	for (const int32 Index : Near)
	{
		Dirty.Add(Index);
	}
	TSet<int32> Touched;
	for (const int32 Index : Dirty)
	{
		bool bFlying = false;
		for (const FFlight& Flight : Flights)
		{
			bFlying |= Flight.Stone == Index;
		}
		if (!bFlying)
		{
			Apply(Index, false);
			Touched.Add(Stones[Index].Mesh);
		}
	}
	for (const int32 M : Touched)
	{
		if (Meshes.IsValidIndex(M) && Meshes[M])
		{
			Meshes[M]->MarkRenderStateDirty();
		}
	}
	return Result;
}

void UGTGravelStones::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	// The switches: gt.Gravel.Stones and gt.Gravel.StoneDensity rebuild (deterministic, so the same stones come back).
	if (AGTMudPatch* P = Patch.Get())
	{
		if ((IsEnabled() ? 1 : 0) != BuiltEnabled || !FMath::IsNearlyEqual(DensityScale(), BuiltScale))
		{
			Build(*P, BuiltSeed, BuiltProfileDensity, RoadHalfCm);
		}
	}
	if (Flights.Num() == 0)
	{
		return;
	}
	TSet<int32> Touched;
	for (int32 F = Flights.Num() - 1; F >= 0; --F)
	{
		FFlight& Flight = Flights[F];
		Flight.Age += DeltaTime;
		const FStone& Stone = Stones[Flight.Stone];
		if (Flight.Age >= Flight.Duration)
		{
			Apply(Flight.Stone, false);
			Touched.Add(Stone.Mesh);
			Flights.RemoveAtSwap(F);
			continue;
		}
		const float A = Flight.Age / FMath::Max(0.01f, Flight.Duration);
		FTransform T = StoneTransform(Stone);
		const FVector Land = T.GetLocation();
		T.SetLocation(FMath::Lerp(Flight.From, Land, A) + FVector(0.0, 0.0, Flight.ArcCm * 4.f * A * (1.f - A)));
		T.SetRotation(FQuat(FVector(0.0, 0.0, 1.0), A * 6.f) * T.GetRotation());
		if (Meshes.IsValidIndex(Stone.Mesh) && Meshes[Stone.Mesh])
		{
			Meshes[Stone.Mesh]->UpdateInstanceTransform(Stone.Instance, T, true, false, true);
			Touched.Add(Stone.Mesh);
		}
	}
	for (const int32 M : Touched)
	{
		if (Meshes.IsValidIndex(M) && Meshes[M])
		{
			Meshes[M]->MarkRenderStateDirty();
		}
	}
}

// ---- AGTMudPatch's side (declared in GTMudPatch.h): kept here so the patch's own file carries only the hooks ----
void AGTMudPatch::InitGravelStones()
{
	if (Medium != EGTDeformMedium::Gravel || GravelStonesPerM2 <= 0.f || !Field.IsValid())
	{
		return;
	}
	if (!GravelStones)
	{
		GravelStones = NewObject<UGTGravelStones>(this, TEXT("GravelStones"), RF_Transient);
		GravelStones->SetupAttachment(RootComponent);
		GravelStones->RegisterComponent();
	}
	GravelStones->Build(*this, SectionIndex, GravelStonesPerM2, RoadHalfWidthCm);
}

FString AGTMudPatch::DescribeGravelStones() const
{
	if (!GravelStones)
	{
		return FString::Printf(TEXT("section %d: no stones (medium %d, %.1f per m^2)"), SectionIndex, static_cast<int32>(Medium), GravelStonesPerM2);
	}
	int32 States[4] = { 0, 0, 0, 0 };
	for (const UGTGravelStones::FStone& Stone : GravelStones->GetStones())
	{
		++States[FMath::Clamp<int32>(Stone.State, 0, 3)];
	}
	return FString::Printf(TEXT("section %d: %d stones, %d instances, target %d over %.1f m^2 of road (%.1f per m^2 x gt.Gravel.StoneDensity %.2f, gt.Gravel.Stones %d); rest %d pushed %d pressed %d flicked %d"),
		SectionIndex, GravelStones->NumStones(), GravelStones->NumInstances(), GravelStones->GetTargetCount(), GravelStones->GetPlacedAreaM2(),
		GravelStonesPerM2, UGTGravelStones::DensityScale(), UGTGravelStones::IsEnabled() ? 1 : 0, States[0], States[1], States[2], States[3]);
}
