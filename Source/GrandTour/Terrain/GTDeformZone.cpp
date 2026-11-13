#include "Terrain/GTDeformZone.h"

#include "Components/SplineComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Terrain/GTSurfacePhysMaterial.h"

namespace
{
	uint32 ZoneHash(uint32 X)
	{
		X ^= X >> 16;
		X *= 0x7FEB352Du;
		X ^= X >> 15;
		X *= 0x846CA68Bu;
		X ^= X >> 16;
		return X;
	}
}

AGTDeformZone::AGTDeformZone()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Spline = CreateDefaultSubobject<USplineComponent>(TEXT("Spline"));
	Spline->SetupAttachment(RootComponent);
	Spline->SetMobility(EComponentMobility::Static);
	Spline->bDrawDebug = true;
	MudRow = TSoftObjectPtr<UGTSurfacePhysMaterial>(FSoftObjectPath(TEXT("/Game/GrandTour/Terrain/Surfaces/PM_Mud.PM_Mud")));
	BogRow = TSoftObjectPtr<UGTSurfacePhysMaterial>(FSoftObjectPath(TEXT("/Game/GrandTour/Terrain/Surfaces/PM_Bog.PM_Bog")));
}

void AGTDeformZone::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	bPrepared = false;
	Prepare();
	// The spline is a view of the road line (linear points, world space), so the zone shows in the editor.
	if (Spline && Shape == EGTDeformZoneShape::Road && LineCm.Num() >= 2)
	{
		Spline->ClearSplinePoints(false);
		const float Z = GetActorLocation().Z;
		for (const FVector2D& P : LineCm)
		{
			Spline->AddSplinePoint(FVector(P.X, P.Y, Z), ESplineCoordinateSpace::World, false);
		}
		for (int32 I = 0; I < Spline->GetNumberOfSplinePoints(); ++I)
		{
			Spline->SetSplinePointType(I, ESplinePointType::Linear, false);
		}
		Spline->UpdateSpline();
	}
}

void AGTDeformZone::Prepare()
{
	ArcCm.Reset();
	BoundsCm = FBox2D(ForceInit);
	if (Shape == EGTDeformZoneShape::Road)
	{
		if (LineCm.Num() < 2)
		{
			bPrepared = true;
			return;
		}
		ArcCm.Add(0.f);
		for (int32 K = 1; K < LineCm.Num(); ++K)
		{
			ArcCm.Add(ArcCm.Last() + static_cast<float>(FVector2D::Distance(LineCm[K - 1], LineCm[K])));
		}
		EndArcCm = EndCm > StartCm ? EndCm : ArcCm.Last();
		// The bounds: the stretch's points (and the cut's reach) +- the half width.
		const float Reach = 0.5f * WidthCm + 10.f;
		const float S0 = StartCm - FMath::Abs(CutWaveCm) - Reach;
		const float S1 = EndArcCm + FMath::Abs(CutWaveCm) + Reach;
		for (int32 K = 0; K < LineCm.Num(); ++K)
		{
			const bool bIn = ArcCm[K] >= S0 && ArcCm[K] <= S1;
			const bool bNext = K + 1 < LineCm.Num() && ArcCm[K + 1] >= S0 && ArcCm[K] <= S1;
			if (bIn || bNext)
			{
				BoundsCm += LineCm[K];
				if (K + 1 < LineCm.Num())
				{
					BoundsCm += LineCm[K + 1];
				}
			}
		}
		BoundsCm = BoundsCm.ExpandBy(Reach + OutlineWarpMaxCm);
	}
	else
	{
		const FVector C = GetActorLocation();
		const float R = FMath::Max(BlobHalfCm.X, BlobHalfCm.Y) * (1.f + FMath::Abs(BlobEdgeNoise)) + 10.f + OutlineWarpMaxCm;
		BoundsCm = FBox2D(FVector2D(C.X - R, C.Y - R), FVector2D(C.X + R, C.Y + R));
	}
	bPrepared = true;
}

float AGTDeformZone::CutOffsetCm(int32 Key, float LateralCm, float AmpCm)
{
	if (Key == 0 || AmpCm == 0.f)
	{
		return 0.f;
	}
	const uint32 H = ZoneHash(static_cast<uint32>(Key) * 2654435761u + 977u);
	const float P1 = (H & 0xFFFF) / 65535.f * 2.f * PI;
	const float P2 = (H >> 16) / 65535.f * 2.f * PI;
	return AmpCm * (0.6f * FMath::Sin(2.f * PI * LateralCm / 260.f + P1) + 0.4f * FMath::Sin(2.f * PI * LateralCm / 110.f + P2));
}

void AGTDeformZone::Project(const FVector2D& XY, float& OutS, float& OutT, float& OutDist) const
{
	double Best = TNumericLimits<double>::Max();
	OutS = 0.f;
	OutT = 0.f;
	for (int32 K = 0; K + 1 < LineCm.Num(); ++K)
	{
		const FVector2D A = LineCm[K];
		const FVector2D AB = LineCm[K + 1] - A;
		const double Len2 = AB.SizeSquared();
		const double U = Len2 > 0.0 ? FMath::Clamp(FVector2D::DotProduct(XY - A, AB) / Len2, 0.0, 1.0) : 0.0;
		const FVector2D P = A + AB * U;
		const double D2 = FVector2D::DistSquared(XY, P);
		if (D2 < Best)
		{
			Best = D2;
			OutS = ArcCm[K] + static_cast<float>(U * FMath::Sqrt(Len2));
			const double Cross = AB.X * (XY.Y - A.Y) - AB.Y * (XY.X - A.X);
			OutT = static_cast<float>(FMath::Sqrt(D2)) * (Cross >= 0.0 ? 1.f : -1.f);
		}
	}
	OutDist = static_cast<float>(FMath::Sqrt(Best));
}

float AGTDeformZone::BlobEdge(float Angle) const
{
	const uint32 H = ZoneHash(static_cast<uint32>(ZoneId) * 7919u + 13u);
	const float P1 = (H & 0x3FF) / 1023.f * 2.f * PI;
	const float P2 = ((H >> 10) & 0x3FF) / 1023.f * 2.f * PI;
	const float P3 = ((H >> 20) & 0x3FF) / 1023.f * 2.f * PI;
	return 1.f + BlobEdgeNoise * (0.55f * FMath::Sin(2.f * Angle + P1) + 0.3f * FMath::Sin(3.f * Angle + P2) + 0.15f * FMath::Sin(5.f * Angle + P3));
}

bool AGTDeformZone::IsMember(const FVector2D& InXYCm, float* OutInsideCm) const
{
	if (!bPrepared)
	{
		const_cast<AGTDeformZone*>(this)->Prepare();
	}
	if (!BoundsCm.bIsValid || InXYCm.X < BoundsCm.Min.X || InXYCm.Y < BoundsCm.Min.Y || InXYCm.X > BoundsCm.Max.X || InXYCm.Y > BoundsCm.Max.Y)
	{
		if (OutInsideCm)
		{
			*OutInsideCm = -1000.f;
		}
		return false;
	}
	// Benmore B2c: the outline is the test at the warped point.
	const FVector2D XYCm = InXYCm + OutlineWarpCm(InXYCm);
	if (Shape == EGTDeformZoneShape::Road)
	{
		if (LineCm.Num() < 2)
		{
			return false;
		}
		float S = 0.f;
		float T = 0.f;
		float Dist = 0.f;
		Project(XYCm, S, T, Dist);
		const float Half = 0.5f * WidthCm;
		const float CutA = StartCm + CutOffsetCm(StartCutKey, T, CutWaveCm);
		const float CutB = EndArcCm + CutOffsetCm(EndCutKey, T, CutWaveCm);
		const float Inside = FMath::Min3(Half - Dist, S - CutA, CutB - S);
		if (OutInsideCm)
		{
			*OutInsideCm = Inside;
		}
		return Dist <= Half && S >= CutA && S < CutB;
	}
	const FVector C = GetActorLocation();
	const float Yaw = FMath::DegreesToRadians(GetActorRotation().Yaw);
	const FVector2D D = XYCm - FVector2D(C.X, C.Y);
	const float LX = static_cast<float>(D.X * FMath::Cos(Yaw) + D.Y * FMath::Sin(Yaw));
	const float LY = static_cast<float>(-D.X * FMath::Sin(Yaw) + D.Y * FMath::Cos(Yaw));
	const float U = LX / FMath::Max(1.f, BlobHalfCm.X);
	const float V = LY / FMath::Max(1.f, BlobHalfCm.Y);
	const float R = FMath::Sqrt(U * U + V * V);
	const float Edge = BlobEdge(FMath::Atan2(V, U));
	if (OutInsideCm)
	{
		*OutInsideCm = (Edge - R) * FMath::Min(BlobHalfCm.X, BlobHalfCm.Y);
	}
	return R < Edge;
}

float AGTDeformZone::BogWeightAt(const FVector2D& XYCm) const
{
	if (!IsMud())
	{
		return 0.f;
	}
	// GTTerrainGenerator's bog rule (the deep core down the middle, a 25 m noise widening it), softened over half a metre.
	const float Noise = 0.5f + 0.5f * FMath::PerlinNoise2D(XYCm / 2500.0 + FVector2D(31.7, 11.3));
	const float Core = 0.45f + 0.3f * Noise;
	if (Shape == EGTDeformZoneShape::Road)
	{
		float S = 0.f;
		float T = 0.f;
		float Dist = 0.f;
		Project(XYCm, S, T, Dist);
		const float Half = GetTrackHalfWidthCm();
		return 1.f - FMath::SmoothStep(Half * Core - 50.f, Half * Core + 50.f, Dist);
	}
	float Inside = 0.f;
	IsMember(XYCm, &Inside);
	const float Radius = FMath::Min(BlobHalfCm.X, BlobHalfCm.Y);
	const float Frac = 1.f - FMath::Clamp(Inside / FMath::Max(1.f, Radius), 0.f, 1.f);   // 0 at the centre, 1 at the edge
	return 1.f - FMath::SmoothStep(Core - 0.1f, Core + 0.1f, Frac);
}

void AGTDeformZone::GetRouteLine(TArray<FVector2D>& Out) const
{
	Out.Reset();
	if (Shape == EGTDeformZoneShape::Road)
	{
		Out = LineCm;
		return;
	}
	const FVector C = GetActorLocation();
	const float Yaw = FMath::DegreesToRadians(GetActorRotation().Yaw);
	const FVector2D Dir(FMath::Cos(Yaw), FMath::Sin(Yaw));
	const float Half = BlobHalfCm.X * (1.f + FMath::Abs(BlobEdgeNoise));
	for (int32 K = -10; K <= 10; ++K)
	{
		Out.Add(FVector2D(C.X, C.Y) + Dir * (Half * K / 10.f));
	}
}

float AGTDeformZone::GetHalfWidthCm() const
{
	return Shape == EGTDeformZoneShape::Road ? 0.5f * WidthCm : BlobHalfCm.Y;
}

float AGTDeformZone::GetTrackHalfWidthCm() const
{
	return Shape == EGTDeformZoneShape::Road ? 0.5f * (TrackWidthCm > 0.f ? TrackWidthCm : WidthCm) : BlobHalfCm.Y;
}

FVector2D AGTDeformZone::OutlineWarpCm(const FVector2D& XYCm)
{
	// Two octaves (15 m and 8 m) of a 2D Perlin displacement, the amplitude itself a 40 m noise between 100 and 250 cm.
	const FVector2D Q = XYCm / 100.0;   // metres
	const float Amp = 100.f + 150.f * FMath::Clamp(0.5f + 0.5f * FMath::PerlinNoise2D(Q / 40.0 + FVector2D(13.1, 71.7)), 0.f, 1.f);
	const FVector2D A(FMath::PerlinNoise2D(Q / 15.0 + FVector2D(3.7, 9.2)), FMath::PerlinNoise2D(Q / 15.0 + FVector2D(41.3, 17.9)));
	const FVector2D B(FMath::PerlinNoise2D(Q / 8.0 + FVector2D(27.5, 63.1)), FMath::PerlinNoise2D(Q / 8.0 + FVector2D(88.4, 5.3)));
	FVector2D W = (A * 0.65 + B * 0.35) * Amp;
	const double Len = W.Size();
	if (Len > OutlineWarpMaxCm - 10.0)
	{
		W *= (OutlineWarpMaxCm - 10.0) / Len;
	}
	return W;
}

float AGTDeformZone::OpacityFromInside(const FVector2D& XYCm, float InsideCm) const
{
	if (InsideCm <= 0.f)
	{
		return 0.f;
	}
	if (!IsMud())
	{
		return 1.f;
	}
	const float N = FMath::Clamp(0.5f + 0.5f * FMath::PerlinNoise2D(XYCm / 900.0 + FVector2D(57.2, 23.8)), 0.f, 1.f);
	const float Feather = FMath::Lerp(FeatherCm.X, FMath::Max(FeatherCm.X, FeatherCm.Y), N);
	return FMath::SmoothStep(0.f, FMath::Max(1.f, Feather), InsideCm);
}

float AGTDeformZone::OpacityAt(const FVector2D& XYCm) const
{
	float Inside = 0.f;
	return IsMember(XYCm, &Inside) ? OpacityFromInside(XYCm, Inside) : 0.f;
}

FString AGTDeformZone::BakeMudMaps(UObject* WorldContext, FVector2D OriginCm, float SizeCm, int32 MaskSize, int32 ColourSize, float ApronCm, const FString& MaskPng, const FString& ColourPng)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World || MaskSize < 2 || ColourSize < 2 || SizeCm <= 0.f)
	{
		return TEXT("{\"ok\":false}");
	}
	TArray<AGTDeformZone*> Muds;
	for (TActorIterator<AGTDeformZone> It(World); It; ++It)
	{
		It->Prepare();
		if (It->IsMud())
		{
			Muds.Add(*It);
		}
	}
	TArray<FColor> Mask;
	Mask.Init(FColor(0, 0, 0, 255), MaskSize * MaskSize);
	TArray<float> Best;   // the colour map: the nearest (most inside) mud zone per texel
	TArray<FColor> Colour;
	Colour.Init(FColor(128, 128, 128, 255), ColourSize * ColourSize);
	Best.Init(-1.e9f, ColourSize * ColourSize);
	const float MaskTexel = SizeCm / MaskSize;
	const float ColourTexel = SizeCm / ColourSize;
	int64 MudTexels = 0;
	int64 ApronTexels = 0;
	for (AGTDeformZone* Zone : Muds)
	{
		const FBox2D B = Zone->GetBoundsCm().ExpandBy(ApronCm + 450.f);
		const int32 X0 = FMath::Clamp(FMath::FloorToInt((B.Min.X - OriginCm.X) / MaskTexel), 0, MaskSize - 1);
		const int32 X1 = FMath::Clamp(FMath::CeilToInt((B.Max.X - OriginCm.X) / MaskTexel), 0, MaskSize - 1);
		const int32 Y0 = FMath::Clamp(FMath::FloorToInt((B.Min.Y - OriginCm.Y) / MaskTexel), 0, MaskSize - 1);
		const int32 Y1 = FMath::Clamp(FMath::CeilToInt((B.Max.Y - OriginCm.Y) / MaskTexel), 0, MaskSize - 1);
		for (int32 Y = Y0; Y <= Y1; ++Y)
		{
			for (int32 X = X0; X <= X1; ++X)
			{
				const FVector2D P = OriginCm + FVector2D(X + 0.5, Y + 0.5) * MaskTexel;
				float Inside = -1.e6f;
				const bool bIn = Zone->IsMember(P, &Inside);
				FColor& T = Mask[Y * MaskSize + X];
				if (bIn)
				{
					const uint8 R = static_cast<uint8>(FMath::RoundToInt(255.f * Zone->OpacityFromInside(P, Inside)));
					MudTexels += (T.R == 0 && R > 0) ? 1 : 0;
					T.R = FMath::Max(T.R, R);
				}
				else if (Inside > -ApronCm)
				{
					const uint8 G = static_cast<uint8>(FMath::RoundToInt(255.f * (1.f - FMath::SmoothStep(0.f, ApronCm, -Inside))));
					ApronTexels += (T.G == 0 && G > 0) ? 1 : 0;
					T.G = FMath::Max(T.G, G);
				}
			}
		}
		const int32 CX0 = FMath::Clamp(FMath::FloorToInt((B.Min.X - OriginCm.X) / ColourTexel), 0, ColourSize - 1);
		const int32 CX1 = FMath::Clamp(FMath::CeilToInt((B.Max.X - OriginCm.X) / ColourTexel), 0, ColourSize - 1);
		const int32 CY0 = FMath::Clamp(FMath::FloorToInt((B.Min.Y - OriginCm.Y) / ColourTexel), 0, ColourSize - 1);
		const int32 CY1 = FMath::Clamp(FMath::CeilToInt((B.Max.Y - OriginCm.Y) / ColourTexel), 0, ColourSize - 1);
		const FColor C = Zone->MudColour.ToFColor(true);
		for (int32 Y = CY0; Y <= CY1; ++Y)
		{
			for (int32 X = CX0; X <= CX1; ++X)
			{
				const FVector2D P = OriginCm + FVector2D(X + 0.5, Y + 0.5) * ColourTexel;
				float Inside = -1.e6f;
				Zone->IsMember(P, &Inside);
				if (Inside > -(ApronCm + 400.f) && Inside > Best[Y * ColourSize + X])
				{
					Best[Y * ColourSize + X] = Inside;
					Colour[Y * ColourSize + X] = FColor(C.R, C.G, C.B, 255);
				}
			}
		}
	}
	// The colour map spread outward a few texels (the bilinear read at the far mask's edge never meets the grey).
	for (int32 Pass = 0; Pass < 3; ++Pass)
	{
		TArray<FColor> Next = Colour;
		TArray<float> NextBest = Best;
		for (int32 Y = 0; Y < ColourSize; ++Y)
		{
			for (int32 X = 0; X < ColourSize; ++X)
			{
				if (Best[Y * ColourSize + X] > -1.e8f)
				{
					continue;
				}
				for (int32 D = 0; D < 4; ++D)
				{
					const int32 NX = X + (D == 0 ? 1 : D == 1 ? -1 : 0);
					const int32 NY = Y + (D == 2 ? 1 : D == 3 ? -1 : 0);
					if (NX >= 0 && NY >= 0 && NX < ColourSize && NY < ColourSize && Best[NY * ColourSize + NX] > -1.e8f)
					{
						Next[Y * ColourSize + X] = Colour[NY * ColourSize + NX];
						NextBest[Y * ColourSize + X] = -1.e7f;
						break;
					}
				}
			}
		}
		Colour = MoveTemp(Next);
		Best = MoveTemp(NextBest);
	}
	auto Save = [](const TArray<FColor>& Pixels, int32 Size, const FString& Path)
	{
		TArray64<uint8> Png;
		FImageUtils::PNGCompressImageArray(Size, Size, TArrayView64<const FColor>(Pixels.GetData(), Pixels.Num()), Png);
		return FFileHelper::SaveArrayToFile(TArrayView64<const uint8>(Png.GetData(), Png.Num()), *Path);
	};
	const bool bMask = Save(Mask, MaskSize, MaskPng);
	const bool bColour = Save(Colour, ColourSize, ColourPng);
	return FString::Printf(TEXT("{\"ok\":%s,\"mud_zones\":%d,\"mask_size\":%d,\"mask_texel_cm\":%.2f,\"colour_size\":%d,\"colour_texel_cm\":%.2f,\"origin_cm\":[%.0f,%.0f],\"size_cm\":%.0f,\"mud_texels\":%lld,\"apron_texels\":%lld,\"apron_cm\":%.0f}"),
		(bMask && bColour) ? TEXT("true") : TEXT("false"), Muds.Num(), MaskSize, MaskTexel, ColourSize, ColourTexel, OriginCm.X, OriginCm.Y, SizeCm, MudTexels, ApronTexels, ApronCm);
}

float AGTDeformZone::StretchLengthM() const
{
	if (Shape != EGTDeformZoneShape::Road)
	{
		return 2.f * BlobHalfCm.X * 0.01f;
	}
	const float End = EndCm > StartCm ? EndCm : (ArcCm.Num() > 0 ? ArcCm.Last() : 0.f);
	return (End - StartCm) * 0.01f;
}

float AGTDeformZone::AreaM2() const
{
	if (Shape == EGTDeformZoneShape::Road)
	{
		return StretchLengthM() * WidthCm * 0.01f;
	}
	return PI * BlobHalfCm.X * BlobHalfCm.Y * 1.e-4f;
}
