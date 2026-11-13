#include "Terrain/GTReliefLibrary.h"

namespace
{
	float ReliefStatsPercentile(TArray<float> Values, float P)
	{
		if (Values.Num() == 0)
		{
			return 0.f;
		}
		Values.Sort();
		const float At = FMath::Clamp(P, 0.f, 1.f) * (Values.Num() - 1);
		const int32 Lo = FMath::FloorToInt32(At);
		const int32 Hi = FMath::Min(Lo + 1, Values.Num() - 1);
		return FMath::Lerp(Values[Lo], Values[Hi], At - Lo);
	}

	/** Each point's nearest other point, m (a 4 m bucket grid; a point with none within 12 m gets 12). */
	TArray<float> NearestDistances(const TArray<FVector2D>& Points)
	{
		TArray<float> Out;
		Out.SetNumUninitialized(Points.Num());
		TMap<FIntPoint, TArray<int32>> Buckets;
		const float Bucket = 4.f;
		for (int32 I = 0; I < Points.Num(); ++I)
		{
			Buckets.FindOrAdd(FIntPoint(FMath::FloorToInt32(Points[I].X / Bucket), FMath::FloorToInt32(Points[I].Y / Bucket))).Add(I);
		}
		for (int32 I = 0; I < Points.Num(); ++I)
		{
			const FIntPoint B(FMath::FloorToInt32(Points[I].X / Bucket), FMath::FloorToInt32(Points[I].Y / Bucket));
			double Best = 12.0;
			for (int32 DY = -3; DY <= 3; ++DY)
			{
				for (int32 DX = -3; DX <= 3; ++DX)
				{
					if (const TArray<int32>* List = Buckets.Find(B + FIntPoint(DX, DY)))
					{
						for (const int32 J : *List)
						{
							if (J != I)
							{
								Best = FMath::Min(Best, FVector2D::Distance(Points[I], Points[J]));
							}
						}
					}
				}
			}
			Out[I] = static_cast<float>(Best);
		}
		return Out;
	}

	void MeanCV(const TArray<float>& Values, float& OutMean, float& OutCV)
	{
		OutMean = 0.f;
		OutCV = 0.f;
		if (Values.Num() < 2)
		{
			return;
		}
		double Sum = 0.0;
		for (const float V : Values)
		{
			Sum += V;
		}
		const double Mean = Sum / Values.Num();
		double Var = 0.0;
		for (const float V : Values)
		{
			Var += (V - Mean) * (V - Mean);
		}
		OutMean = static_cast<float>(Mean);
		OutCV = Mean > 0.0 ? static_cast<float>(FMath::Sqrt(Var / Values.Num()) / Mean) : 0.f;
	}
}

FGTReliefStats GTRelief::Measure(const FGTTerrainSpec& Spec)
{
	FGTReliefStats Stats;
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	auto H = [&](const FVector2D& P) { return GTTerrain::HeightM(Spec, Profiles, static_cast<float>(P.X), static_cast<float>(P.Y)); };
	// The route: grade over 3 m (about the wheelbase) and cross-slope over 1.6 m (the track), every 0.5 m.
	TArray<float> Grades;
	TArray<float> Cross;
	TArray<float> GradesOffFord;
	TArray<float> CrossOffFord;
	auto NearFord = [&Spec](float Arc)
	{
		for (const FGTRouteSection& Section : Spec.Sections)
		{
			if (Section.Kind == EGTRouteSectionKind::Ford && Arc >= Section.StartM - 3.f && Arc <= Section.EndM + 3.f)
			{
				return true;
			}
		}
		return false;
	};
	const float Length = GTTerrain::PolylineLengthM(Spec.RouteM);
	for (float Arc = 2.f; Arc <= Length - 2.f; Arc += 0.5f)
	{
		float Yaw = 0.f;
		const FVector2D P = GTTerrain::PointOnPolyline(Spec.RouteM, Arc, Yaw);
		const FVector2D Dir(FMath::Cos(FMath::DegreesToRadians(Yaw)), FMath::Sin(FMath::DegreesToRadians(Yaw)));
		const FVector2D Left(-Dir.Y, Dir.X);
		Grades.Add(100.f * FMath::Abs(H(P + Dir * 1.5) - H(P - Dir * 1.5)) / 3.f);
		Cross.Add(100.f * FMath::Abs(H(P + Left * 0.8) - H(P - Left * 0.8)) / 1.6f);
		if (!NearFord(Arc))
		{
			GradesOffFord.Add(Grades.Last());
			CrossOffFord.Add(Cross.Last());
		}
	}
	Stats.GradeP95OffFord = ReliefStatsPercentile(GradesOffFord, 0.95f);
	Stats.CrossP95OffFord = ReliefStatsPercentile(CrossOffFord, 0.95f);
	Stats.RouteSamples = Grades.Num();
	Stats.GradeP50 = ReliefStatsPercentile(Grades, 0.5f);
	Stats.GradeP95 = ReliefStatsPercentile(Grades, 0.95f);
	Stats.GradeMax = ReliefStatsPercentile(Grades, 1.f);
	Stats.CrossP50 = ReliefStatsPercentile(Cross, 0.5f);
	Stats.CrossP95 = ReliefStatsPercentile(Cross, 0.95f);
	Stats.CrossMax = ReliefStatsPercentile(Cross, 1.f);
	if (Spec.Hummocks.Density <= 0.f)
	{
		return Stats;
	}
	// The hummock field over the landscape's grid.
	const float SideM = (GTTerrain::VertsPerSide(Spec) - 1) * Spec.QuadSizeCm / 100.f;
	const FVector2D Origin(Spec.OriginXCm / 100.f, Spec.OriginYCm / 100.f);
	const FBox2D Area(Origin, Origin + FVector2D(SideM, SideM));
	TArray<FVector4f> Mounds;
	GTTerrain::HummockCentres(Spec, Area, Mounds);
	TArray<FVector2D> Raw;
	TArray<FVector2D> Stamped;
	for (const FVector4f& M : Mounds)
	{
		Raw.Add(FVector2D(M.X, M.Y));
		if (GTTerrain::HummockMask(Spec, Profiles, M.X, M.Y) > 0.5f)
		{
			Stamped.Add(FVector2D(M.X, M.Y));
		}
	}
	Stats.HummocksRaw = Raw.Num();
	Stats.HummocksStamped = Stamped.Num();
	Stats.Density = Raw.Num() / FMath::Max(1.f, SideM * SideM) * 100.f;
	// Nearest neighbours (the references at least 12 m in from the grid's edge, so their nearest is not cut off).
	const FBox2D Inner = Area.ExpandBy(-12.0);
	TArray<float> RawNearest = NearestDistances(Raw);
	TArray<float> InnerNearest;
	for (int32 I = 0; I < Raw.Num(); ++I)
	{
		if (Inner.IsInside(Raw[I]))
		{
			InnerNearest.Add(RawNearest[I]);
		}
	}
	MeanCV(InnerNearest, Stats.NearestMeanM, Stats.NearestCV);
	float StampedMean = 0.f;
	MeanCV(NearestDistances(Stamped), StampedMean, Stats.StampedNearestCV);
	// The radial pair correlation g(r), 0.5 m bins to 15 m, the references at least 15 m in (border method).
	const float Bin = 0.5f;
	const int32 Bins = 30;
	TArray<double> Counts;
	Counts.Init(0.0, Bins);
	int32 Refs = 0;
	const FBox2D RefBox = Area.ExpandBy(-15.0);
	TMap<FIntPoint, TArray<int32>> Buckets;
	for (int32 I = 0; I < Raw.Num(); ++I)
	{
		Buckets.FindOrAdd(FIntPoint(FMath::FloorToInt32(Raw[I].X / 15.0), FMath::FloorToInt32(Raw[I].Y / 15.0))).Add(I);
	}
	for (int32 I = 0; I < Raw.Num(); ++I)
	{
		if (!RefBox.IsInside(Raw[I]))
		{
			continue;
		}
		++Refs;
		const FIntPoint B(FMath::FloorToInt32(Raw[I].X / 15.0), FMath::FloorToInt32(Raw[I].Y / 15.0));
		for (int32 DY = -1; DY <= 1; ++DY)
		{
			for (int32 DX = -1; DX <= 1; ++DX)
			{
				if (const TArray<int32>* List = Buckets.Find(B + FIntPoint(DX, DY)))
				{
					for (const int32 J : *List)
					{
						const double D = FVector2D::Distance(Raw[I], Raw[J]);
						if (J != I && D < Bins * Bin)
						{
							Counts[FMath::Min(Bins - 1, FMath::FloorToInt32(D / Bin))] += 1.0;
						}
					}
				}
			}
		}
	}
	const double Lambda = Raw.Num() / FMath::Max(1.0, static_cast<double>(SideM) * SideM);
	for (int32 K = 0; K < Bins; ++K)
	{
		const double R0 = K * Bin;
		const double R1 = R0 + Bin;
		const double Expected = Refs * Lambda * PI * (R1 * R1 - R0 * R0);
		const float G = Expected > 0.0 ? static_cast<float>(Counts[K] / Expected) : 0.f;
		Stats.PairBins.Add(G);
		if (R0 >= Stats.NearestMeanM && G > Stats.PairPeak)
		{
			Stats.PairPeak = G;
			Stats.PairPeakAtM = static_cast<float>(R0 + 0.5 * Bin);
		}
	}
	// The field alone: its steepest slope at 0.25 m over a 64 m window in the grid's middle, and its tallest.
	const FVector2D Mid = Area.GetCenter();
	for (float Y = -32.f; Y < 32.f; Y += 0.25f)
	{
		for (float X = -32.f; X < 32.f; X += 0.25f)
		{
			const float PX = static_cast<float>(Mid.X) + X;
			const float PY = static_cast<float>(Mid.Y) + Y;
			const float GX = (GTTerrain::HummockHeightM(Spec, PX + 0.125f, PY) - GTTerrain::HummockHeightM(Spec, PX - 0.125f, PY)) / 0.25f;
			const float GY = (GTTerrain::HummockHeightM(Spec, PX, PY + 0.125f) - GTTerrain::HummockHeightM(Spec, PX, PY - 0.125f)) / 0.25f;
			Stats.FieldSlopeMaxDeg = FMath::Max(Stats.FieldSlopeMaxDeg, FMath::RadiansToDegrees(FMath::Atan(FMath::Sqrt(GX * GX + GY * GY))));
			Stats.HummockMaxM = FMath::Max(Stats.HummockMaxM, GTTerrain::HummockHeightM(Spec, PX, PY));
		}
	}
	// The finished ground at the landscape's own vertices, where the mask is over 0.5 (the slope by central differences over 2 m).
	const int32 Verts = GTTerrain::VertsPerSide(Spec);
	const float Quad = Spec.QuadSizeCm / 100.f;
	TArray<float> Heights;
	Heights.SetNumUninitialized(Verts * Verts);
	for (int32 Y = 0; Y < Verts; ++Y)
	{
		for (int32 X = 0; X < Verts; ++X)
		{
			Heights[Y * Verts + X] = GTTerrain::HeightM(Spec, Profiles, static_cast<float>(Origin.X) + X * Quad, static_cast<float>(Origin.Y) + Y * Quad);
		}
	}
	TArray<float> Slopes;
	for (int32 Y = 1; Y + 1 < Verts; ++Y)
	{
		for (int32 X = 1; X + 1 < Verts; ++X)
		{
			const float PX = static_cast<float>(Origin.X) + X * Quad;
			const float PY = static_cast<float>(Origin.Y) + Y * Quad;
			if (GTTerrain::HummockMask(Spec, Profiles, PX, PY) <= 0.5f)
			{
				continue;
			}
			const float GX = (Heights[Y * Verts + X + 1] - Heights[Y * Verts + X - 1]) / (2.f * Quad);
			const float GY = (Heights[(Y + 1) * Verts + X] - Heights[(Y - 1) * Verts + X]) / (2.f * Quad);
			Slopes.Add(FMath::RadiansToDegrees(FMath::Atan(FMath::Sqrt(GX * GX + GY * GY))));
		}
	}
	Stats.GroundSlopeMaxDeg = ReliefStatsPercentile(Slopes, 1.f);
	Stats.GroundSlopeP99Deg = ReliefStatsPercentile(Slopes, 0.99f);
	return Stats;
}

FString GTRelief::ToJson(const FGTReliefStats& S)
{
	FString Bins;
	for (int32 K = 0; K < S.PairBins.Num(); ++K)
	{
		Bins += FString::Printf(TEXT("%s%.3f"), K ? TEXT(",") : TEXT(""), S.PairBins[K]);
	}
	return FString::Printf(TEXT("{\"route\":{\"samples\":%d,\"grade_pct\":{\"p50\":%.2f,\"p95\":%.2f,\"max\":%.2f},\"cross_pct\":{\"p50\":%.2f,\"p95\":%.2f,\"max\":%.2f},\"off_ford_p95_pct\":{\"grade\":%.2f,\"cross\":%.2f}},")
		TEXT("\"hummocks\":{\"raw\":%d,\"stamped\":%d,\"density_per_100m2\":%.2f,\"nearest_mean_m\":%.3f,\"nearest_cv\":%.3f,\"stamped_nearest_cv\":%.3f,")
		TEXT("\"pair_peak\":%.3f,\"pair_peak_at_m\":%.2f,\"pair_bins_0_5m\":[%s],\"field_slope_max_deg\":%.2f,\"ground_slope_max_deg\":%.2f,\"ground_slope_p99_deg\":%.2f,\"hummock_max_m\":%.3f}}"),
		S.RouteSamples, S.GradeP50, S.GradeP95, S.GradeMax, S.CrossP50, S.CrossP95, S.CrossMax, S.GradeP95OffFord, S.CrossP95OffFord,
		S.HummocksRaw, S.HummocksStamped, S.Density, S.NearestMeanM, S.NearestCV, S.StampedNearestCV, S.PairPeak, S.PairPeakAtM, *Bins,
		S.FieldSlopeMaxDeg, S.GroundSlopeMaxDeg, S.GroundSlopeP99Deg, S.HummockMaxM);
}

TArray<FTransform> UGTReliefLibrary::VaryGrassTransforms(const FGTTerrainSpec& Spec, const TArray<FTransform>& Transforms, bool bTussock, FString& OutStatsJson)
{
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	TArray<FTransform> Out;
	FGTGrassStats Stats;
	GTTerrain::VaryGrass(Spec, Profiles, Transforms, bTussock, Out, &Stats);
	OutStatsJson = FString::Printf(TEXT("{\"in\":%d,\"bare\":%d,\"out\":%d,\"crest_extra\":%d,\"bare_share\":%.4f,\"scale_min\":%.3f,\"scale_max\":%.3f,\"tilt_max_deg\":%.2f}"),
		Stats.In, Stats.Bare, Stats.Out, Stats.CrestExtra, Stats.In > 0 ? static_cast<float>(Stats.Bare) / Stats.In : 0.f, Stats.ScaleMin, Stats.ScaleMax, Stats.TiltMaxDeg);
	return Out;
}

float UGTReliefLibrary::HummockHeightCm(const FGTTerrainSpec& Spec, float XCm, float YCm)
{
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	return GTTerrain::HummockAtM(Spec, Profiles, XCm / 100.f, YCm / 100.f) * 100.f;
}

FString UGTReliefLibrary::ReliefReportJson(const FGTTerrainSpec& Spec)
{
	return GTRelief::ToJson(GTRelief::Measure(Spec));
}
