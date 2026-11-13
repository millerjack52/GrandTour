#include "Terrain/GTTerrainGenerator.h"

#include "Hash/CityHash.h"
#include "Terrain/GTMudPatch.h"   // LM5b: the bog's own numbers (AGTMudPatch's defaults) under a mud variant's

#include <cmath>

namespace
{
	/** A smooth bump: 1 at the centre, 0 at the radius, no kink either end. */
	float Falloff(float DistanceM, float RadiusM)
	{
		if (RadiusM <= 0.f || DistanceM >= RadiusM)
		{
			return 0.f;
		}
		const float U = DistanceM / RadiusM;
		const float V = 1.f - U * U;
		return V * V;
	}

	/** A stable pseudo-random number in [0, 1) from two integers and the spec's seed (the same spec places the same stones). */
	float Hash01(const FGTTerrainSpec& Spec, int32 A, int32 B)
	{
		uint32 H = static_cast<uint32>(A) * 2654435761u ^ (static_cast<uint32>(B) + 0x9E3779B9u) ^ (static_cast<uint32>(Spec.Seed) * 0x85EBCA6Bu);
		H ^= H >> 15;
		H *= 0x2C1B3C6Du;
		H ^= H >> 12;
		H *= 0x297A2D39u;
		H ^= H >> 15;
		return (H & 0xFFFFFFu) / 16777216.f;
	}

	/** A raised cosine: 1 at 0, 0 at +-HalfM, no kink either end. */
	float Hump(float OffsetM, float HalfM)
	{
		if (HalfM <= 0.f || FMath::Abs(OffsetM) >= HalfM)
		{
			return 0.f;
		}
		return 0.5f * (1.f + FMath::Cos(PI * OffsetM / HalfM));
	}

	/** The centre arc of a track's water bar number K: a bar every WaterBarSpacingM from the section's start, each moved up to 30 % of the spacing by the hash. */
	float WaterBarArc(const FGTTerrainSpec& Spec, const FGTRouteSection& Section, int32 K)
	{
		const float Spacing = FMath::Max(1.f, Spec.WaterBarSpacingM);
		return Section.StartM + (K + 0.5f) * Spacing + (Hash01(Spec, K, 11) - 0.5f) * 0.6f * Spacing;
	}

	/** The water bars' height at a point of a track section: a ridge across the track, skewed so it drains to one side, m. */
	float WaterBarHeight(const FGTTerrainSpec& Spec, const FGTRouteSection& Section, float ArcM, float SignedM)
	{
		if (Spec.WaterBarSpacingM <= 0.f || Spec.WaterBarHeightM <= 0.f)
		{
			return 0.f;
		}
		const float Spacing = FMath::Max(1.f, Spec.WaterBarSpacingM);
		const float Skew = FMath::Tan(FMath::DegreesToRadians(FMath::Clamp(Spec.WaterBarSkewDegrees, -60.f, 60.f)));
		const int32 Nearest = FMath::FloorToInt((ArcM - Section.StartM) / Spacing);
		float Height = 0.f;
		for (int32 K = Nearest - 1; K <= Nearest + 1; ++K)
		{
			const float Centre = WaterBarArc(Spec, Section, K);
			if (K < 0 || Centre < Section.StartM + 3.f || Centre > Section.EndM - 3.f)
			{
				continue;
			}
			Height += Spec.WaterBarHeightM * Hump(ArcM - Centre - Skew * SignedM, Spec.WaterBarLengthM * 0.5f);
		}
		return Height;
	}

	/** The rut pair's dig at a point, m (positive = down): two grooves either side of a centre that wanders along the route. */
	float RutDepth(const FGTTerrainSpec& Spec, float ArcM, float SignedM, float DepthM)
	{
		if (DepthM <= 0.f)
		{
			return 0.f;
		}
		const float Centre = GTTerrain::RutWanderAt(Spec, ArcM);
		return DepthM * (Hump(SignedM - Centre - Spec.RutOffsetM, Spec.RutHalfWidthM) + Hump(SignedM - Centre + Spec.RutOffsetM, Spec.RutHalfWidthM));
	}

	float DistanceToSegment(const FVector2D& P, const FVector2D& A, const FVector2D& B, float& OutT)
	{
		const FVector2D AB = B - A;
		const float Length2 = AB.SizeSquared();
		OutT = Length2 > KINDA_SMALL_NUMBER ? FMath::Clamp(FVector2D::DotProduct(P - A, AB) / Length2, 0.f, 1.f) : 0.f;
		return FVector2D::Distance(P, A + AB * OutT);
	}

	float Fbm(const FGTTerrainSpec& Spec, float XM, float YM)
	{
		float Sum = 0.f;
		float Amplitude = Spec.BaseAmplitudeM;
		float Wavelength = FMath::Max(1.f, Spec.BaseWavelengthM);
		const FVector2D Offset(Spec.Seed * 1000.37f, Spec.Seed * 733.91f);
		for (int32 Octave = 0; Octave < FMath::Max(1, Spec.Octaves); ++Octave)
		{
			Sum += Amplitude * FMath::PerlinNoise2D((FVector2D(XM, YM) + Offset) / Wavelength);
			Amplitude *= Spec.Persistence;
			Wavelength *= 0.5f;
		}
		return Sum;
	}

	float FeatureHeight(const FGTTerrainFeature& Feature, float XM, float YM)
	{
		const FVector2D P(XM, YM);
		float Distance;
		if (Feature.Kind == EGTTerrainFeatureKind::Hill || Feature.Kind == EGTTerrainFeatureKind::Bowl)
		{
			Distance = FVector2D::Distance(P, Feature.StartM);
		}
		else
		{
			float T;
			Distance = DistanceToSegment(P, Feature.StartM, Feature.EndM, T);
		}
		const float Sign = (Feature.Kind == EGTTerrainFeatureKind::Bowl || Feature.Kind == EGTTerrainFeatureKind::Channel) ? -1.f : 1.f;
		return Sign * FMath::Abs(Feature.HeightM) * Falloff(Distance, Feature.RadiusM);
	}

	/** One road's profile: the land along the polyline, smoothed and grade-limited, the limits varying by the main route's sections when bMain. */
	FGTRouteProfile ProfileFor(const FGTTerrainSpec& Spec, const TArray<FVector2D>& PointsM, bool bMain)
	{
		FGTRouteProfile Profile;
		Profile.StepM = 5.f;
		Profile.LengthM = GTTerrain::PolylineLengthM(PointsM);
		const int32 Samples = FMath::Max(2, FMath::CeilToInt(Profile.LengthM / Profile.StepM) + 1);
		TArray<float> Raw;
		Raw.Reserve(Samples);
		for (int32 Sample = 0; Sample < Samples; ++Sample)
		{
			float Yaw;
			const FVector2D Point = GTTerrain::PointOnPolyline(PointsM, FMath::Min(Sample * Profile.StepM, Profile.LengthM), Yaw);
			Raw.Add(GTTerrain::BaseHeightM(Spec, Point.X, Point.Y));
		}
		Profile.HeightsM.SetNum(Samples);
		for (int32 Sample = 0; Sample < Samples; ++Sample)
		{
			const float Arc = Sample * Profile.StepM;
			float SmoothM = Spec.RouteSmoothM;
			if (bMain)
			{
				switch (GTTerrain::SectionKindAt(Spec, Arc))
				{
				case EGTRouteSectionKind::Rally: SmoothM = Spec.RallySmoothM; break;
				case EGTRouteSectionKind::Ford: SmoothM = 10.f; break;
				default: break;
				}
			}
			const int32 Half = FMath::Max(1, FMath::RoundToInt(SmoothM / Profile.StepM / 2.f));
			float Sum = 0.f;
			int32 Count = 0;
			for (int32 Offset = -Half; Offset <= Half; ++Offset)
			{
				const int32 Index = Sample + Offset;
				if (Raw.IsValidIndex(Index))
				{
					Sum += Raw[Index];
					++Count;
				}
			}
			Profile.HeightsM[Sample] = Sum / FMath::Max(1, Count);
		}
		auto MaxStep = [&](int32 Sample) { return (bMain ? GTTerrain::GradeLimitAt(Spec, Sample * Profile.StepM) : Spec.MaxGradePercent) / 100.f * Profile.StepM; };
		for (int32 Sample = 1; Sample < Samples; ++Sample)
		{
			const float Step = MaxStep(Sample);
			Profile.HeightsM[Sample] = FMath::Clamp(Profile.HeightsM[Sample], Profile.HeightsM[Sample - 1] - Step, Profile.HeightsM[Sample - 1] + Step);
		}
		for (int32 Sample = Samples - 2; Sample >= 0; --Sample)
		{
			const float Step = MaxStep(Sample);
			Profile.HeightsM[Sample] = FMath::Clamp(Profile.HeightsM[Sample], Profile.HeightsM[Sample + 1] - Step, Profile.HeightsM[Sample + 1] + Step);
		}
		// A bog sinks below the profile, fading in and out over 10 m.
		if (bMain)
		{
			for (int32 Sample = 0; Sample < Samples; ++Sample)
			{
				const float Arc = Sample * Profile.StepM;
				if (const FGTRouteSection* Section = GTTerrain::SectionAt(Spec, Arc))
				{
					if (Section->Kind == EGTRouteSectionKind::Mud)
					{
						const float Edge = FMath::Min(Arc - Section->StartM, Section->EndM - Arc);
						Profile.HeightsM[Sample] -= Spec.MudSinkM * FMath::Clamp(Edge / 10.f, 0.f, 1.f);
					}
				}
			}
			// The sections' crests and compressions (stage 2) ride on top, evaluated in HeightAt so they are smooth at any step.
			for (const FGTRouteSection& Section : Spec.Sections)
			{
				for (const FGTProfileBump& Bump : Section.Bumps)
				{
					if (Bump.ArcM >= Section.StartM && Bump.ArcM <= Section.EndM && Bump.LengthM > 0.f)
					{
						Profile.Bumps.Add(Bump);
					}
				}
			}
		}
		return Profile;
	}

	/** What a road contributes at a point: how much of it is there (0..1 across the shoulder), its height, its layer. */
	struct FRoadSample
	{
		float Presence = 0.f;      // 1 on the road, fading to 0 across the shoulder
		float PaveWeight = 0.f;    // 1 on the road, fading over the first part of the shoulder
		float HeightM = 0.f;
		float RoughnessM = 0.02f;  // the bumps this stretch carries (stage 2)
		int32 Layer = 1;
		bool bValid = false;
		bool bFirmFordBed = false;   // a Ford section without bFordBedMud: the channel's mud stays off its paving (section 49)
	};

	/** Bumps in [-1, 1]: two octaves of Perlin noise at the relief wavelength and half of it. */
	float RoughnessNoise(const FGTTerrainSpec& Spec, float XM, float YM)
	{
		const float W = FMath::Max(1.f, Spec.RoughnessWavelengthM);
		const FVector2D P(XM, YM);
		if (Spec.RoughnessOctaves >= 3)
		{
			// Ground relief GR1 item 2: a third octave at a third of the wavelength, weights 1 / 0.55 / 0.3 over their sum (the
			// two octaves' 0.67 + 0.33 peak); the first two read the same noise as before.
			return (FMath::PerlinNoise2D(P / W + FVector2D(7.3f, 19.1f)) + 0.55f * FMath::PerlinNoise2D(P / (W * 0.5f) + FVector2D(41.9f, 3.7f))
				+ 0.3f * FMath::PerlinNoise2D(P / (W / 3.f) + FVector2D(23.3f, 57.1f))) / 1.85f;
		}
		return 0.67f * FMath::PerlinNoise2D(P / W + FVector2D(7.3f, 19.1f)) + 0.33f * FMath::PerlinNoise2D(P / (W * 0.5f) + FVector2D(41.9f, 3.7f));
	}

	FRoadSample SampleRoad(const FGTTerrainSpec& Spec, const TArray<FVector2D>& PointsM, const FGTRouteProfile& Profile, float HalfWidthM, int32 DefaultLayer, bool bMain, float XM, float YM)
	{
		FRoadSample Sample;
		if (PointsM.Num() < 2)
		{
			return Sample;
		}
		const FGTRouteHit Hit = GTTerrain::NearestOnPolyline(PointsM, XM, YM);
		float HalfWidth = HalfWidthM;
		int32 Layer = DefaultLayer;
		float Camber = 0.f;
		float Roughness = Spec.TrackRoughnessM;   // an alternative line is a track
		if (bMain)
		{
			HalfWidth = GTTerrain::HalfWidthAt(Spec, Hit.ArcM);
			switch (GTTerrain::SectionKindAt(Spec, Hit.ArcM))
			{
			case EGTRouteSectionKind::Track: Roughness = Spec.TrackRoughnessM; break;
			case EGTRouteSectionKind::Rally: Roughness = Spec.RallyRoughnessM; break;
			case EGTRouteSectionKind::Mud: Roughness = Spec.MudRoughnessM; break;
			case EGTRouteSectionKind::Ford: Roughness = Spec.FordRoughnessM; break;
			default: Roughness = Spec.RoadRoughnessM; break;
			}
			for (const FGTSurfaceSpan& Span : Spec.Spans)
			{
				if (Hit.ArcM >= Span.StartM && Hit.ArcM <= Span.EndM)
				{
					Layer = FMath::Clamp(Span.Layer, 0, GTTerrain::LayerCount - 1);
				}
			}
			const EGTRouteSectionKind Kind = GTTerrain::SectionKindAt(Spec, Hit.ArcM);
			if (Kind == EGTRouteSectionKind::Ford)
			{
				// 2026-09-22 (section 49): a firm bed, Dirt (1), unless the spec asks for M6 stage 3's Mud (2). The Mud row
				// sank the wheels 22 cm through the water and popped them out in one tick where it met the Dirt bank.
				Layer = Spec.bFordBedMud ? 2 : 1;
				Sample.bFirmFordBed = !Spec.bFordBedMud;
			}
			else if (Kind == EGTRouteSectionKind::Mud)
			{
				// The bog: deep mud (layer 5) down the middle in a band that widens and narrows along it, so there are
				// pockets to read; mud at the edges, the shallow line a careful driver takes.
				const float Noise = 0.5f + 0.5f * FMath::PerlinNoise2D(FVector2D(XM, YM) / FMath::Max(1.f, Spec.BogPocketWavelengthM) + FVector2D(31.7f, 11.3f));
				const float Core = Spec.BogCoreFraction + Spec.BogPocketFraction * Noise;
				Layer = FMath::Abs(Hit.SignedM) < HalfWidth * Core ? 5 : 2;
			}
			else if (Kind == EGTRouteSectionKind::Snow)
			{
				// LM3a: the Snow layer (3) across a Snow section's paving; its patch is the deep snow over it.
				Layer = 3;
			}
			Camber = GTTerrain::CamberDegreesAt(Spec, Hit.ArcM);
		}
		const float Outer = HalfWidth + Spec.ShoulderM;
		if (Hit.DistanceM >= Outer)
		{
			return Sample;
		}
		Sample.bValid = true;
		Sample.Presence = 1.f - FMath::SmoothStep(HalfWidth, Outer, Hit.DistanceM);
		// The paving stops soon after the road's edge, in proportion to its width, so a narrow track stays narrow.
		Sample.PaveWeight = 1.f - FMath::SmoothStep(HalfWidth, HalfWidth + FMath::Max(1.5f, HalfWidth * 0.5f), Hit.DistanceM);
		// Camber: the surface tilts across the road, the tilt carried out to the shoulder's edge where it fades.
		const float Lateral = FMath::Clamp(Hit.SignedM, -HalfWidth, HalfWidth);
		Sample.HeightM = Profile.HeightAt(Hit.ArcM) - FMath::Tan(FMath::DegreesToRadians(Camber)) * Lateral;
		if (bMain)
		{
			// Stage 2, the shape the wheels feel: water bars across a track and a rut pair down it (and down a bog), on the
			// paving only; beyond a rally road's edge a verge, a ditch where the road is on fill and a bank where it is in
			// cut, so a wheel off the road is pulled in, then the shoulder as before.
			if (const FGTRouteSection* Section = GTTerrain::SectionAt(Spec, Hit.ArcM))
			{
				if (Section->Kind == EGTRouteSectionKind::Track)
				{
					Sample.HeightM += (WaterBarHeight(Spec, *Section, Hit.ArcM, Hit.SignedM) - RutDepth(Spec, Hit.ArcM, Hit.SignedM, Spec.TrackRutDepthM)) * Sample.PaveWeight;
				}
				else if (Section->Kind == EGTRouteSectionKind::Mud)
				{
					Sample.HeightM -= RutDepth(Spec, Hit.ArcM, Hit.SignedM, Spec.MudRutDepthM) * Sample.PaveWeight;
				}
				else if (Section->Kind == EGTRouteSectionKind::Rally && Hit.DistanceM > HalfWidth && Spec.VergeWidthM > 0.f)
				{
					const float Beyond = Hit.DistanceM - HalfWidth;
					if (Beyond < Spec.VergeWidthM)
					{
						// Cut or fill is read once per side from the land 2 m beyond the verge against the road's height, so the
						// whole verge is one shape (read at the point itself it flipped along a shallow cut); level ground gets a ditch.
						float Yaw;
						const FVector2D OnRoute = GTTerrain::PointOnPolyline(PointsM, Hit.ArcM, Yaw);
						const FVector2D Left(-FMath::Sin(FMath::DegreesToRadians(Yaw)), FMath::Cos(FMath::DegreesToRadians(Yaw)));
						const FVector2D Probe = OnRoute + Left * (Hit.SignedM >= 0.f ? 1.f : -1.f) * (HalfWidth + Spec.VergeWidthM + 2.f);
						const bool bCut = GTTerrain::BaseHeightM(Spec, Probe.X, Probe.Y) > Profile.HeightAt(Hit.ArcM) + 0.3f;
						Sample.HeightM += (bCut ? Spec.VergeBankM : -Spec.VergeDitchM) * FMath::Sin(PI * Beyond / Spec.VergeWidthM);
					}
				}
			}
		}
		Sample.Layer = Layer;
		Sample.RoughnessM = Roughness;
		return Sample;
	}
}

float FGTRouteProfile::HeightAt(float ArcM) const
{
	if (HeightsM.Num() == 0)
	{
		return 0.f;
	}
	const float Index = FMath::Clamp(ArcM / StepM, 0.f, static_cast<float>(HeightsM.Num() - 1));
	const int32 I0 = FMath::FloorToInt(Index);
	const int32 I1 = FMath::Min(I0 + 1, HeightsM.Num() - 1);
	float Height = FMath::Lerp(HeightsM[I0], HeightsM[I1], Index - I0);
	for (const FGTProfileBump& Bump : Bumps)
	{
		Height += Bump.HeightM * Hump(ArcM - Bump.ArcM, Bump.LengthM * 0.5f);
	}
	return Height;
}

int32 GTTerrain::VertsPerSide(const FGTTerrainSpec& Spec)
{
	return Spec.ComponentsPerSide * Spec.SubsectionsPerComponent * Spec.QuadsPerSubsection + 1;
}

const TCHAR* GTTerrain::LayerName(int32 Layer)
{
	switch (Layer)
	{
	case 0: return TEXT("Tarmac");
	case 2: return TEXT("Mud");
	case 3: return TEXT("Snow");
	case 4: return TEXT("Scrub");
	case 5: return TEXT("Bog");
	default: return TEXT("Dirt");
	}
}

const TCHAR* GTTerrain::PhysName(int32 Layer)
{
	return Layer == 4 ? TEXT("Dirt") : LayerName(Layer);
}

float GTTerrain::BaseHeightM(const FGTTerrainSpec& Spec, float XM, float YM)
{
	float Height = Spec.SlopeMPerKm * XM / 1000.f + Fbm(Spec, XM, YM);
	for (const FGTTerrainFeature& Feature : Spec.Features)
	{
		Height += FeatureHeight(Feature, XM, YM);
	}
	return Height;
}

float GTTerrain::ChannelDigM(const FGTTerrainSpec& Spec, float XM, float YM)
{
	float Dig = 0.f;
	for (const FGTTerrainFeature& Feature : Spec.Features)
	{
		if (Feature.Kind == EGTTerrainFeatureKind::Channel)
		{
			Dig -= FeatureHeight(Feature, XM, YM);
		}
	}
	return FMath::Max(0.f, Dig);
}

float GTTerrain::PolylineLengthM(const TArray<FVector2D>& PointsM)
{
	float Length = 0.f;
	for (int32 Index = 0; Index + 1 < PointsM.Num(); ++Index)
	{
		Length += FVector2D::Distance(PointsM[Index], PointsM[Index + 1]);
	}
	return Length;
}

FVector2D GTTerrain::PointOnPolyline(const TArray<FVector2D>& PointsM, float ArcM, float& OutYawDegrees)
{
	OutYawDegrees = 0.f;
	if (PointsM.Num() == 0)
	{
		return FVector2D::ZeroVector;
	}
	float Remaining = FMath::Max(0.f, ArcM);
	FVector2D Point = PointsM[0];
	FVector2D Direction(1.f, 0.f);
	for (int32 Index = 0; Index + 1 < PointsM.Num(); ++Index)
	{
		const FVector2D AB = PointsM[Index + 1] - PointsM[Index];
		const float SegmentLength = AB.Size();
		Direction = SegmentLength > KINDA_SMALL_NUMBER ? AB / SegmentLength : Direction;
		if (Remaining <= SegmentLength || Index + 2 == PointsM.Num())
		{
			Point = PointsM[Index] + Direction * FMath::Min(Remaining, SegmentLength);
			break;
		}
		Remaining -= SegmentLength;
	}
	OutYawDegrees = FMath::RadiansToDegrees(FMath::Atan2(Direction.Y, Direction.X));
	return Point;
}

FGTRouteHit GTTerrain::NearestOnPolyline(const TArray<FVector2D>& PointsM, float XM, float YM)
{
	FGTRouteHit Hit;
	Hit.DistanceM = 1e9f;
	const FVector2D P(XM, YM);
	float Arc = 0.f;
	for (int32 Index = 0; Index + 1 < PointsM.Num(); ++Index)
	{
		const FVector2D& A = PointsM[Index];
		const FVector2D& B = PointsM[Index + 1];
		float T;
		const float Distance = DistanceToSegment(P, A, B, T);
		if (Distance < Hit.DistanceM)
		{
			Hit.DistanceM = Distance;
			Hit.ArcM = Arc + T * FVector2D::Distance(A, B);
			Hit.Segment = Index;
			const FVector2D AB = B - A;
			const FVector2D AP = P - A;
			Hit.SignedM = (AB.X * AP.Y - AB.Y * AP.X) >= 0.f ? Distance : -Distance;   // left of the direction is positive
		}
		Arc += FVector2D::Distance(A, B);
	}
	if (PointsM.Num() == 1)
	{
		Hit.DistanceM = FVector2D::Distance(P, PointsM[0]);
	}
	return Hit;
}

FGTRouteHit GTTerrain::NearestRoute(const FGTTerrainSpec& Spec, float XM, float YM)
{
	return NearestOnPolyline(Spec.RouteM, XM, YM);
}

const FGTRouteSection* GTTerrain::SectionAt(const FGTTerrainSpec& Spec, float ArcM)
{
	for (const FGTRouteSection& Section : Spec.Sections)
	{
		if (ArcM >= Section.StartM && ArcM <= Section.EndM)
		{
			return &Section;
		}
	}
	return nullptr;
}

EGTRouteSectionKind GTTerrain::SectionKindAt(const FGTTerrainSpec& Spec, float ArcM)
{
	const FGTRouteSection* Section = SectionAt(Spec, ArcM);
	return Section ? Section->Kind : EGTRouteSectionKind::Road;
}

float GTTerrain::HalfWidthAt(const FGTTerrainSpec& Spec, float ArcM)
{
	switch (SectionKindAt(Spec, ArcM))
	{
	case EGTRouteSectionKind::Track: return Spec.RoadHalfWidthM * Spec.TrackWidthScale;
	case EGTRouteSectionKind::Rally: return Spec.RoadHalfWidthM * Spec.RallyWidthScale;
	case EGTRouteSectionKind::Mud: return Spec.RoadHalfWidthM * Spec.MudWidthScale;
	case EGTRouteSectionKind::Ford: return Spec.RoadHalfWidthM * 1.2f;
	case EGTRouteSectionKind::Snow: return Spec.RoadHalfWidthM * Spec.SnowWidthScale;   // LM3a
	default: return Spec.RoadHalfWidthM;
	}
}

float GTTerrain::GradeLimitAt(const FGTTerrainSpec& Spec, float ArcM)
{
	switch (SectionKindAt(Spec, ArcM))
	{
	case EGTRouteSectionKind::Rally: return Spec.RallyGradePercent;
	case EGTRouteSectionKind::Ford: return Spec.FordGradePercent;
	default: return Spec.MaxGradePercent;
	}
}

float GTTerrain::HeadingAt(const FGTTerrainSpec& Spec, float ArcM)
{
	// The direction between the points 20 m behind and 20 m ahead: a bend's heading turns over its approach and exit.
	float Yaw;
	const FVector2D A = PointOnPolyline(Spec.RouteM, FMath::Max(0.f, ArcM - 20.f), Yaw);
	const FVector2D B = PointOnPolyline(Spec.RouteM, ArcM + 20.f, Yaw);
	const FVector2D D = B - A;
	return D.SizeSquared() > KINDA_SMALL_NUMBER ? FMath::Atan2(D.Y, D.X) : 0.f;
}

float GTTerrain::CurvatureAt(const FGTTerrainSpec& Spec, float ArcM)
{
	const float Behind = HeadingAt(Spec, ArcM - 15.f);
	const float Ahead = HeadingAt(Spec, ArcM + 15.f);
	return FMath::FindDeltaAngleRadians(Behind, Ahead) / 30.f;
}

float GTTerrain::CamberDegreesAt(const FGTTerrainSpec& Spec, float ArcM)
{
	if (SectionKindAt(Spec, ArcM) != EGTRouteSectionKind::Rally)
	{
		return 0.f;
	}
	// A left bend (positive curvature) banks so the left side is lower: positive camber means the right side is higher.
	return FMath::Clamp(CurvatureAt(Spec, ArcM) * Spec.CamberGainDegrees, -Spec.CamberMaxDegrees, Spec.CamberMaxDegrees);
}

FGTRouteProfile GTTerrain::BuildRouteProfile(const FGTTerrainSpec& Spec)
{
	return ProfileFor(Spec, Spec.RouteM, true);
}

FGTTerrainProfiles GTTerrain::BuildProfiles(const FGTTerrainSpec& Spec)
{
	FGTTerrainProfiles Profiles;
	Profiles.Main = ProfileFor(Spec, Spec.RouteM, true);
	for (const FGTAltRoute& Alt : Spec.AltRoutes)
	{
		Profiles.Alts.Add(ProfileFor(Spec, Alt.PointsM, false));
	}
	MudPatchBoxesCm(Spec, Profiles.MudBoxesCm);
	return Profiles;
}

namespace
{
	/** A section's box, world cm: its route points every 2 m +- the half width there + MarginCm (MudPatchBoxCm's rule since RIVERBED S2; DeformPatchBoxCm shares it since S4). */
	bool SectionBoxCm(const FGTTerrainSpec& Spec, const FGTRouteSection& Section, FBox2D& OutBox, float MarginCm)
	{
		OutBox = FBox2D(ForceInit);
		if (Section.EndM <= Section.StartM)
		{
			return false;
		}
		// Moved here from UGTMudSubsystem::BuildPatches unchanged (its points were UGTVehicleSetupLibrary::TerrainRoutePointCm,
		// whose XY is this PointOnPolyline x 100; the height it added was never used).
		const int32 Steps = FMath::Max(1, FMath::CeilToInt((Section.EndM - Section.StartM) / 2.f));
		for (int32 Step = 0; Step <= Steps; ++Step)
		{
			const float ArcM = FMath::Lerp(Section.StartM, Section.EndM, static_cast<float>(Step) / Steps);
			float Yaw;
			const FVector2D PointM = GTTerrain::PointOnPolyline(Spec.RouteM, ArcM, Yaw);
			const FVector2D Point = PointM * 100.f;
			const float Half = GTTerrain::HalfWidthAt(Spec, ArcM) * 100.f + MarginCm;
			OutBox += FVector2D(Point.X - Half, Point.Y - Half);
			OutBox += FVector2D(Point.X + Half, Point.Y + Half);
		}
		return OutBox.bIsValid;
	}
}

bool GTTerrain::MudPatchBoxCm(const FGTTerrainSpec& Spec, int32 SectionIndex, FBox2D& OutBox, float MarginCm)
{
	OutBox = FBox2D(ForceInit);
	if (!Spec.Sections.IsValidIndex(SectionIndex) || Spec.Sections[SectionIndex].Kind != EGTRouteSectionKind::Mud)
	{
		return false;
	}
	return SectionBoxCm(Spec, Spec.Sections[SectionIndex], OutBox, MarginCm);
}

const FGTDeformProfile* GTTerrain::DeformProfileFor(const FGTRouteSection& Section)
{
	switch (Section.Deform.Mode)
	{
	case EGTDeformProfileMode::On: return &Section.Deform;
	case EGTDeformProfileMode::ByKind:
		// LM5b: a Mud section on ByKind takes its MudVariant's profile (Standard: none, the bog as before).
		return Section.Kind == EGTRouteSectionKind::Ford ? &Section.Deform
			: Section.Kind == EGTRouteSectionKind::Mud ? MudVariantProfile(Section.MudVariant) : nullptr;
	default: return nullptr;
	}
}

const FGTDeformProfile* GTTerrain::MudVariantProfile(EGTMudVariant Variant)
{
	if (Variant == EGTMudVariant::Standard)
	{
		return nullptr;
	}
	// Built once, on the first call (the patch's class default object exists by then): the slice order of EGTMudVariant.
	static const FGTDeformProfile Profiles[4] = {
		FGTDeformProfile::MudVariantDefaults(EGTMudVariant::Standard),
		FGTDeformProfile::MudVariantDefaults(EGTMudVariant::Firm),
		FGTDeformProfile::MudVariantDefaults(EGTMudVariant::Deep),
		FGTDeformProfile::MudVariantDefaults(EGTMudVariant::Stony) };
	const int32 Index = static_cast<int32>(Variant);
	return Index >= 0 && Index < 4 ? &Profiles[Index] : nullptr;
}

const FGTDeformProfile* GTTerrain::DeformProfileFor(const FGTTerrainSpec& Spec, const FGTRouteSection& Section)
{
	// LM3a: a Snow section on ByKind takes the spec's SnowProfile; everything else exactly as the one-argument form.
	if (Section.Kind == EGTRouteSectionKind::Snow && Section.Deform.Mode == EGTDeformProfileMode::ByKind)
	{
		return &Spec.SnowProfile;
	}
	return DeformProfileFor(Section);
}

float GTTerrain::SnowDepthCmAt(const FGTTerrainSpec& Spec, const FGTRouteSection& Section, const FGTDeformProfile& Profile, float XCm, float YCm)
{
	float Depth = FMath::Max(0.f, Profile.SnowDepthCm);
	if (Section.SnowDrifts.Num() == 0)
	{
		return Depth;
	}
	// The drift's weight at the arc of the nearest point of the main route: 1 from StartM to EndM, a smoothstep down to 0
	// over RampM beyond each end. The deepest weighted drift wins, so two drifts that meet do not add up.
	const float ArcM = NearestRoute(Spec, XCm / 100.f, YCm / 100.f).ArcM;
	float Best = Depth;
	for (const FGTSnowDrift& Drift : Section.SnowDrifts)
	{
		if (Drift.EndM <= Drift.StartM)
		{
			continue;
		}
		const float Ramp = FMath::Max(0.01f, Drift.RampM);
		const float Outside = FMath::Max(Drift.StartM - ArcM, ArcM - Drift.EndM);
		const float Weight = Outside <= 0.f ? 1.f : 1.f - FMath::SmoothStep(0.f, Ramp, Outside);
		Best = FMath::Max(Best, FMath::Lerp(Depth, FMath::Max(0.f, Drift.DepthCm), Weight));
	}
	return Best;
}

FGTDeformProfile FGTDeformProfile::SnowDefaults()
{
	// docs/LIVING_MUD_PLAN.md LM3a, the block's snow numbers in the current names (housekeeping item 4 overrides the
	// body where they differ): everything not named keeps this struct's defaults.
	FGTDeformProfile P;
	P.Medium = EGTDeformMedium::Snow;
	P.SnowDepthCm = 35.f;
	P.SnowEdgeCm = 300.f;
	// The traction in a snow patch: packed snow.
	P.MaxSinkageM = 0.05f;
	P.SinkageRate = 0.05f;
	// The cut: snow compacts (80 % of what a tyre cuts is gone), a small lip, a near-vertical wall rounded over at the top.
	P.RidgeReturn = 0.2f;
	P.RidgeWidthCm = 35.f;
	P.MaxRidgeCm = 8.f;
	P.RidgeFootCm = 12.f;
	P.RutShoulderCm = 10.f;
	P.RutShoulderMinCells = 1.f;   // so RutShoulderCm 10 stands: at the field's 2 cells (25 cm) a 35 cm wall is 54-62 deg
	P.RutDepthVariation = 0.1f;
	P.FloorNoiseCm = 0.5f;
	// LM3c item 3 (the block's snow numbers): the lips' and the plough berm's clumps and along-stroke waves (LM3a: 0.3 and 0.3).
	P.RidgeNoise = 0.5f;
	P.RidgeWave = 0.6f;
	P.RidgeSlump = 0.f;
	// Not a plan number: stage H's blend (max plus 0.9 of the lesser where a hump already stands) loses a tenth of every
	// later stamp's deposit on a lip cell; on snow that put the compaction row's volume gone at 0.8175 of the cut (2.2 %
	// over the asked 0.8 within 1 %). At the sum (1.0) it reads 0.8045; the lip is capped at MaxRidgeCm 8 anyway.
	P.RidgeBlend = 1.f;
	// The relax: none, the walls stand; the talus at 70 deg.
	P.ReposeDeg = 70.f;
	P.OozeRate = 0.f;
	P.RecoverShare = 0.f;
	P.SetSeconds = 0.f;
	// A crumbly lip of small lumps, and the clods along it and from the throw.
	P.LumpShare = 0.5f;
	P.LumpMaxCm = 6.f;
	P.LumpRadiusCells = 1.2f;
	P.LumpAbsentShare = 0.5f;
	P.ClodBankPerCm = 0.03f;
	P.ClodThrowChance = 0.1f;
	P.ThrowMax = 0.15f;
	// The belly's plough, the refill, the plough drag (proposed).
	P.PloughReturn = 0.3f;
	P.PloughBandCm = 40.f;
	P.PloughLumpShare = 0.25f;   // LM3c follow-up (the main session's): the berm's lumps, half the lips' 0.5
	// LM3c follow-up, not a plan number: the berm's share of the bank's height swings. The no-spike rows (the crest's 90th
	// percentile at most 1.3x its median, its highest at most 1.6x) hold at no share: the lips' own lumps (LumpShare 0.5)
	// lie under the berm and alone read 1.32x. 0.4 is the largest share that keeps the highest under 1.6x (1.53x; the
	// 90th percentile 1.40x, cv 0.175); at 1.0 the crest reads 1.52x / 1.87x, cv 0.243. GrandTour.Snow.Compact's sweep.
	P.PloughBankVariation = 0.4f;
	P.RefillCmPerMin = 2.f;
	// LM3b (housekeeping 1): tuned on L_SnowDrive at full throttle once the tyre's own sinkage rolls at the Dirt row's
	// rate (LM3a: 0.35 and the belly's full BellyDragPerMetre). The values the check's trials landed on, for the owner to
	// name at the gate: the belly's drag in snow off (any of it tipped the drift into the 1.7-1.9 km/h crawl the trials
	// fell into), the uncut snow ahead of the tyres carrying the drag. The belly still ploughs the field (its berms).
	P.SnowPlough = 0.78f;
	P.SnowBellyDrag = 0.f;
	// LM4 (docs/LIVING_MUD_PLAN.md LM4, God of War snow deformation). Item 1: a 6.25 cm grid, and every cell-unit number
	// stated so its size in cm is the one intended (the stage note's table): the clumps 50 cm, the settle tile 2 m, the floor
	// noise 62.5 cm, the pockets 150 cm, the tracks' edge 37.5 cm as at 12.5; the wall's fewest cells 1 (6.25 cm), so
	// RutShoulderCm 10 is the wall, as LM3a meant; the lump sites 20 cm apart (item 2: plates 12-30 cm across); the domes'
	// radius 15 cm as LM3c's (unread by the plates).
	P.CellCm = 6.25f;
	P.RidgeNoiseCells = 8.f;
	P.SettleTileCells = 32;
	P.FloorNoiseCells = 10.f;
	P.PocketNoiseCells = 24.f;
	P.TracksEdgeCells = 6.f;
	// Stage H's ridge smoothing is a 3-cell mean along the stroke (37.5 cm at 12.5, 18.75 at 6.25): off in snow. On the stepped
	// lip (item 3) it is not volume-conserving - GrandTour.Snow.Compact's stroke read 0.8115 of the cut gone with it (asked 0.8
	// within 1 %), 0.8000 without - and the owner has rejected smoothing; LM3c's was 0.7 (the field's default).
	P.RidgeSmooth = 0.f;
	P.RutShoulderMinCells = 1.f;
	P.LumpSpacingCells = 3.2f;
	P.LumpRadiusCells = 2.4f;
	// Item 2: crust plates, 5-25 degrees.
	P.bLumpPlates = true;
	P.PlateTiltMinDeg = 5.f;
	P.PlateTiltMaxDeg = 25.f;
	// Item 3: the stepped wall line, 15 % of its segments dropping their lip plate into the trench.
	P.WallStepMinCm = 3.f;
	P.WallStepMaxCm = 8.f;
	P.WallSegMinCm = 15.f;
	P.WallSegMaxCm = 30.f;
	P.WallDropShare = 0.15f;
	P.FloorChunkChance = 0.18f;   // landed on GrandTour.Snow.GoW's 30 m car (2.67 floor chunks a metre per unit): about 30 % on the floor at LM3c's count
	// Item 4: the shards' sizes, power law (the meshes are 6-25 cm across at scale 1): 4-25 cm at u^3, a cv of 0.64 by the law
	// (5-25 read 0.498 on GrandTour.Snow.GoW's 48 chunks, asked at least 0.5).
	P.ClodBankSizeMinCm = 4.f;
	P.ClodBankSizeMaxCm = 25.f;
	P.ClodSizePower = 3.f;
	// Per 12.5 cm cell's area (FGTMudField::ClodAreaScale) and only at the plates' edges: landed on GrandTour.Snow.GoW's 30 m car
	// (65 lip chunks a metre per unit) for LM3c's count there, 1.60 a metre with the floor's (LM3c 0.03 on every lip cell at 12.5 cm).
	P.ClodBankPerCm = 0.017f;
	// Item 6: the uneven snow top (sd 2.5 cm at 0.6-3 m: +-3-5 cm), and the trench floor +-1.5 cm (LM3a's 0.5).
	P.SnowTopUndulationCm = 2.5f;
	P.SnowTopWaveMinCm = 60.f;
	P.SnowTopWaveMaxCm = 300.f;
	P.FloorNoiseCm = 1.5f;
	// LM4b (docs/LIVING_MUD_PLAN.md LM4b, the owner's "the snow is a bit blocky"): the shape soft and irregular, the crumbly
	// detail per pixel in M_GT_Snow. The 6.25 cm grid and every snow physics number stay.
	// Item 1: the wall line as continuous noise, two octaves at 25 and 70 cm, +-3 cm in all (LM4's 3-8 cm steps off; the
	// segments carry the drops only). Landed on GrandTour.Snow.GoW's sweep: 1.25 + 2.5 cm read a largest station step of
	// 1.69 cm (asked at most 1.5), 1.0 + 2.0 cm 1.29 / 1.01 with the sd 3.20 / 2.53 (asked 2-4).
	P.WallStepMinCm = 0.f;
	P.WallStepMaxCm = 0.f;
	P.WallWaveCm = 25.f;
	P.WallWaveLongCm = 70.f;
	P.WallWaveAmpCm = 1.f;
	P.WallWaveLongAmpCm = 2.f;
	// Item 2: soft lumps - LM2c's domes back on LM4's sites (20 cm apart, half absent in patches), radii 5-12 cm (8.5 cm
	// +- 41 %; a dome's semi-axes are at least a cell, 6.25 cm), leaning by a skew of 2-10 deg, each dome re-shaped to its
	// kernel with its peak at most 0.30 x its radius (LumpMaxCm 6 at most). Not a plan number: the softness - uncapped, a dome
	// fills to a 6 cm column 10-17 cm across; landed on GrandTour.Snow.GoW's sweep for the lip band's steps over 3 cm at most
	// half LM4's (0.30: 3.33 % against LM4's 7.81 %; 0.35 4.08 %, 0.45 6.03 %, uncapped 8.73 %; the amplitude- and
	// radius-scaled caps tried, LumpCapAmpPower / LumpCapRadiusPower, all over 3.91 %). The fallen-plate notches stay, their
	// ends feathered over 2 cells.
	P.bLumpPlates = false;
	P.bLumpSoftDomes = true;
	P.LumpRadiusCells = 8.5f / 6.25f;
	P.LumpVarietyRadiusJitter = 0.41f;
	P.LumpSkewMinDeg = 2.f;
	P.LumpSkewMaxDeg = 10.f;
	P.LumpHeightPerRadius = 0.3f;
	P.LumpCapAmpPower = 0.f;
	P.LumpCapRadiusPower = 0.f;
	P.WallDropFeatherCells = 2.f;
	// Item 3: the chunks' count as LM4's - the domes' edges are fewer cells than the plates' were (the first LM4b test read
	// 15 lip chunks on GrandTour.Snow.GoW's 30 m car at 0.017 against LM4's 32; 0.036 read 31, then 37 with the landed cap),
	// so the rate per 12.5 cm cell's area is 0.031.
	P.ClodBankPerCm = 0.031f;
	// LM4c (docs/LIVING_MUD_PLAN.md LM4c, the owner's "those tall edges need to fall down into piles"): piles, not walls. The
	// snow physics stay (SnowPlough 0.78, SnowBellyDrag 0, the sinkage), and SetSeconds 0 (no relax).
	// Item 1: the talus per cell - loose snow above the top (the berm, the lip) and a collapse's pile, the cut wall below it at
	// WallReposeDeg +- 20 deg by a 40-80 cm world noise (ranked: evenly over the range). Landed on GrandTour.Snow.Piles' sweeps:
	// the block's 35 and 60 +- 20 read the trench floor's debris row at 52 % (asked 8-30) - the loose berm pours into the 28 cm
	// trench at 35 deg, and a wall that eases under 55 deg spreads across the floor - and the berm crest's cv at 0.23 / 0.24
	// (asked at least 0.35: the slump smooths the piles). Loose 50 and the wall 64 +- 20 hold the floor under 30 % with the
	// outer walls' cells under 60 % steep; the two rows pull against each other through the wall's repose.
	P.bCellRepose = true;
	P.LooseReposeDeg = 50.f;
	P.WallReposeDeg = 64.f;
	P.WallReposeRangeDeg = 20.f;
	P.WallReposeWaveMinCm = 40.f;
	P.WallReposeWaveMaxCm = 80.f;
	// Item 2: a fifth of the wall's 30-80 cm segments collapse 0.5-3 s after the last cut: the top 30-60 % onto the floor (the
	// block's 0.25 landed at 0.2 for the floor's debris row: the collapses alone put 6-8 points of it there).
	P.CollapseChance = 0.2f;
	P.CollapseSegMinCm = 30.f;
	P.CollapseSegMaxCm = 80.f;
	P.CollapseDelayMinS = 0.5f;
	P.CollapseDelayMaxS = 3.f;
	P.CollapseTopMin = 0.3f;
	P.CollapseTopMax = 0.6f;
	P.CollapseFeatherCells = 2.f;
	P.CollapseClumpsMin = 1;
	P.CollapseClumpsMax = 2;
	// Item 3: the berm in piles - the plough's band, falling from the wall ((1 - u)^0.5, FGTMudField::PloughFallPower), and the
	// plough's and the lips' deposits scaled along the trench by a 1-2.5 m world noise (ranked, by smoothstep: piles and gaps,
	// FGTMudField::PileContrast). Landed on the sweeps: gaps down to 0.08 (the block's 0.2) lift the crest's cv to the 0.35
	// asked; lower (0.05) the lips' gaps move GrandTour.Snow.GoW's wall line row (its largest step 1.50 cm, asked at most 1.5);
	// the band at 85 cm (the block's 70) keeps the edge's median and 90th percentile near 0.56x LM4b's with the steeper loose
	// repose (70 read 0.59-0.62x, asked at most 0.6).
	P.PloughBandCm = 85.f;
	P.bPloughFallingProfile = true;
	P.PileClusterMin = 0.08f;
	P.PileClusterMax = 1.8f;
	P.PileWaveMinCm = 100.f;
	P.PileWaveMaxCm = 250.f;
	// LM4d (docs/LIVING_MUD_PLAN.md LM4d, the owner's "the middle is still very perfectly flat"): the belly's channel. Item 1: the
	// target over the ground +-2.5 cm by two octaves at 20 and 60 cm across, 2.5x longer along the heading's axis.
	P.BellyUndulationCm = 2.5f;
	P.BellyWaveMinCm = 20.f;
	P.BellyWaveMaxCm = 60.f;
	P.BellyStretch = 2.5f;
	// Item 2: smear ridges 30-80 cm long, 8-15 cm wide, 1-3 cm high, a quarter of the 20 cm lanes' segments (bunched at 120 cm).
	P.SmearChance = 0.25f;
	P.SmearLaneCm = 20.f;
	P.SmearLengthMinCm = 30.f;
	P.SmearLengthMaxCm = 80.f;
	P.SmearWidthMinCm = 8.f;
	P.SmearWidthMaxCm = 15.f;
	P.SmearHeightMinCm = 1.f;
	P.SmearHeightMaxCm = 3.f;
	P.SmearClusterCm = 120.f;
	// Item 3: 15 % of the side deposit spills back into the channel as soft lumps, a clump on 15 % of its sites (bunched).
	P.PloughSpillShare = 0.15f;
	P.SpillClumpChance = 0.15f;
	return P;
}

FGTDeformProfile FGTDeformProfile::MudVariantDefaults(EGTMudVariant Variant)
{
	// docs/LIVING_MUD_PLAN.md LM5b, the variant table (the feel numbers are proposals the owner names after driving).
	// "Sinkage" scales the surface row's MaxSinkage and SinkageRate inside the patch, "friction" the row's friction; the
	// three bog numbers start from the bog's own (the patch's defaults), so a number the table leaves out is the bog's.
	FGTDeformProfile P;
	P.bScalesRows = true;
	const AGTMudPatch* Bog = GetDefault<AGTMudPatch>();
	P.RecoverShare = Bog->RecoverShare;
	P.LumpShare = Bog->LumpShare;
	P.ThrowMax = Bog->ThrowMax;
	auto Sinkage = [&P](float Scale)
	{
		P.MaxSinkageScale = Scale;
		P.SinkageRateScale = Scale;
	};
	switch (Variant)
	{
	case EGTMudVariant::Firm:
		Sinkage(0.6f);
		P.RecoverShare = 0.25f;
		P.LumpShare = 0.25f;
		P.ThrowMax = 0.3f;
		P.FrictionScale = 1.1f;
		P.SoftSpotAmplitude = 0.5f;   // MR4
		P.ChunkDensityScale = 0.5f;   // MR5
		break;
	case EGTMudVariant::Deep:
		Sinkage(1.5f);
		P.RecoverShare = 0.55f;
		P.LumpShare = 0.35f;
		P.ThrowMax = 0.6f;
		P.WaterTableOffsetCm = 10.f;
		P.FrictionScale = 0.9f;
		// MR4: under the outline's 1 - Deep already crawls on sinkage x1.5; at 1 its soft spots would sink about 1.36x more again.
		P.SoftSpotAmplitude = 0.6f;
		P.ChunkDensityScale = 1.5f;   // MR5
		break;
	case EGTMudVariant::Stony:
		Sinkage(0.8f);
		P.RecoverShare = 0.3f;
		P.LumpShare = 0.2f;
		P.FrictionScale = 1.15f;
		P.SoftSpotAmplitude = 0.6f;   // MR4
		P.ChunkDensityScale = 1.f;    // MR5 (stony chunks: the Stony slice)
		break;
	default:   // Standard: the identity
		break;
	}
	return P;
}

bool GTTerrain::DeformPatchBoxCm(const FGTTerrainSpec& Spec, int32 SectionIndex, FBox2D& OutBox, float MarginCm)
{
	OutBox = FBox2D(ForceInit);
	if (!Spec.Sections.IsValidIndex(SectionIndex))
	{
		return false;
	}
	const FGTRouteSection& Section = Spec.Sections[SectionIndex];
	if (Section.Kind != EGTRouteSectionKind::Mud && !DeformProfileFor(Spec, Section))
	{
		return false;
	}
	return SectionBoxCm(Spec, Section, OutBox, MarginCm);
}

int32 GTTerrain::DeformPatchCount(const FGTTerrainSpec& Spec)
{
	int32 Count = 0;
	for (int32 Index = 0; Index < Spec.Sections.Num(); ++Index)
	{
		FBox2D Box;
		Count += DeformPatchBoxCm(Spec, Index, Box) ? 1 : 0;
	}
	return Count;
}

void GTTerrain::MudPatchBoxesCm(const FGTTerrainSpec& Spec, TArray<FBox2D>& OutBoxes, float MarginCm)
{
	OutBoxes.Reset();
	for (int32 Index = 0; Index < Spec.Sections.Num(); ++Index)
	{
		FBox2D Box;
		if (MudPatchBoxCm(Spec, Index, Box, MarginCm))
		{
			OutBoxes.Add(Box);
		}
	}
}

namespace
{
	/** The road that has the most claim on a point (the strongest presence), or none. */
	FRoadSample StrongestRoad(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM)
	{
		FRoadSample Best = SampleRoad(Spec, Spec.RouteM, Profiles.Main, Spec.RoadHalfWidthM, 1, true, XM, YM);
		for (int32 Index = 0; Index < Spec.AltRoutes.Num() && Index < Profiles.Alts.Num(); ++Index)
		{
			const FGTAltRoute& Alt = Spec.AltRoutes[Index];
			const FRoadSample Sample = SampleRoad(Spec, Alt.PointsM, Profiles.Alts[Index], Alt.HalfWidthM, FMath::Clamp(Alt.Layer, 0, GTTerrain::LayerCount - 1), false, XM, YM);
			if (Sample.bValid && (!Best.bValid || Sample.Presence > Best.Presence))
			{
				Best = Sample;
			}
		}
		return Best;
	}
}

float GTTerrain::HeightM(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM)
{
	// The land, the road carved into it, and on top the relief (stage 2): the surface's bumps, the scrub's away from
	// any road and the road's own on its paving, blended across the paving's fade. The route profile is built from the
	// land alone, so the bumps never fight the grade limits.
	const float Base = BaseHeightM(Spec, XM, YM);
	const FRoadSample Road = StrongestRoad(Spec, Profiles, XM, YM);
	float Amplitude = Road.bValid ? FMath::Lerp(Spec.ScrubRoughnessM, Road.RoughnessM, Road.PaveWeight) : Spec.ScrubRoughnessM;
	float Height = Road.bValid ? FMath::Lerp(Base, Road.HeightM, Road.Presence) : Base;
	// The Proving Ground's planes (a pad, ramps, a cross slope) lie over the land and the roads, in order; a spec with
	// none (every leg) takes neither branch and returns what it always did.
	for (const FGTTerrainPlane& Plane : Spec.Planes)
	{
		float PlaneHeight = 0.f;
		const float Presence = PlanePresence(Plane, XM, YM, PlaneHeight);
		if (Presence > 0.f)
		{
			Height = FMath::Lerp(Height, PlaneHeight, Presence);
			Amplitude = FMath::Lerp(Amplitude, Plane.RoughnessM, Presence);
		}
	}
	const float Relief = Amplitude * RoughnessNoise(Spec, XM, YM);
	if (Spec.Hummocks.Density <= 0.f)
	{
		return Height + Relief;   // every spec but GR1's strips: exactly as before
	}
	// Ground relief GR1 item 3: the hummocks, off the roads' bands and shoulders, the planes and the channels.
	float Mask = Road.bValid ? FMath::Cube(1.f - Road.Presence) : 1.f;
	for (const FGTTerrainPlane& Plane : Spec.Planes)
	{
		float PlaneHeight = 0.f;
		Mask *= 1.f - PlanePresence(Plane, XM, YM, PlaneHeight);
	}
	if (Mask > 0.f)
	{
		Mask *= 1.f - FMath::SmoothStep(0.f, 0.3f, ChannelDigM(Spec, XM, YM));
	}
	return Height + Relief + (Mask > 0.f ? Mask * HummockHeightM(Spec, XM, YM) : 0.f);
}

float GTTerrain::HummockMask(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM)
{
	const FRoadSample Road = StrongestRoad(Spec, Profiles, XM, YM);
	float Mask = Road.bValid ? FMath::Cube(1.f - Road.Presence) : 1.f;
	for (const FGTTerrainPlane& Plane : Spec.Planes)
	{
		float PlaneHeight = 0.f;
		Mask *= 1.f - PlanePresence(Plane, XM, YM, PlaneHeight);
	}
	return Mask > 0.f ? Mask * (1.f - FMath::SmoothStep(0.f, 0.3f, ChannelDigM(Spec, XM, YM))) : 0.f;
}

float GTTerrain::HummockAtM(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM, float* OutPeakM)
{
	if (OutPeakM)
	{
		*OutPeakM = 0.f;
	}
	if (Spec.Hummocks.Density <= 0.f)
	{
		return 0.f;
	}
	const float Mask = HummockMask(Spec, Profiles, XM, YM);
	if (Mask <= 0.f)
	{
		return 0.f;
	}
	float Peak = 0.f;
	const float H = HummockHeightM(Spec, XM, YM, &Peak);
	if (OutPeakM)
	{
		*OutPeakM = Peak * Mask;
	}
	return H * Mask;
}

float GTTerrain::PlanePresence(const FGTTerrainPlane& Plane, float XM, float YM, float& OutHeightM)
{
	const float Yaw = FMath::DegreesToRadians(Plane.YawDegrees);
	const FVector2D Along(FMath::Cos(Yaw), FMath::Sin(Yaw));
	const FVector2D Left(-Along.Y, Along.X);
	const FVector2D D = FVector2D(XM, YM) - Plane.StartM;
	const float A = FVector2D::DotProduct(D, Along);
	const float C = FVector2D::DotProduct(D, Left);
	const float Length = FMath::Max(0.f, Plane.LengthM);
	const float Half = FMath::Max(0.f, Plane.HalfWidthM);
	const float AC = FMath::Clamp(A, 0.f, Length);
	const float CC = FMath::Clamp(C, -Half, Half);
	OutHeightM = Plane.BaseZM + AC * Plane.GradePercent / 100.f + CC * FMath::Tan(FMath::DegreesToRadians(Plane.CrossSlopeDegrees));
	const float Outside = FVector2D(A - AC, C - CC).Size();
	if (Outside <= 0.f)
	{
		return 1.f;
	}
	return Plane.BlendM > 0.f ? 1.f - FMath::SmoothStep(0.f, Plane.BlendM, Outside) : 0.f;
}

const FGTTerrainStation* GTTerrain::FindStation(const FGTTerrainSpec& Spec, const FString& Name)
{
	for (const FGTTerrainStation& Station : Spec.Stations)
	{
		if (Station.Name.ToString().Equals(Name, ESearchCase::IgnoreCase))
		{
			return &Station;
		}
	}
	return nullptr;
}

namespace
{
	/** Weights per layer at a point, 0..1 each, before normalisation. */
	void LayerWeights(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM, float HeightAtPoint, float Weights[GTTerrain::LayerCount])
	{
		for (int32 Layer = 0; Layer < GTTerrain::LayerCount; ++Layer)
		{
			Weights[Layer] = 0.f;
		}
		const FRoadSample Road = StrongestRoad(Spec, Profiles, XM, YM);
		const float RoadWeight = Road.bValid ? Road.PaveWeight : 0.f;
		const int32 Ground = FMath::Clamp(Spec.OffRoadLayer, 0, GTTerrain::LayerCount - 1);
		Weights[Ground] += 1.f - RoadWeight;
		Weights[Road.bValid ? Road.Layer : Ground] += RoadWeight;
		// The Proving Ground's paved planes (the pad is tarmac), with a 2 m edge; none on a leg.
		for (const FGTTerrainPlane& Plane : Spec.Planes)
		{
			if (Plane.Layer < 0)
			{
				continue;
			}
			float PlaneHeight = 0.f;
			const float Blend = FMath::Min(2.f, Plane.BlendM);
			FGTTerrainPlane Edge = Plane;
			Edge.BlendM = Blend;
			const float Paint = GTTerrain::PlanePresence(Edge, XM, YM, PlaneHeight);
			if (Paint > 0.f)
			{
				for (int32 Layer = 0; Layer < GTTerrain::LayerCount; ++Layer)
				{
					Weights[Layer] *= 1.f - Paint;
				}
				Weights[FMath::Clamp(Plane.Layer, 0, GTTerrain::LayerCount - 1)] += Paint;
			}
		}
		// Mud in the bottoms of channels, on and off the road; 2026-09-22 (section 49) not on a ford's firm bed: without
		// this the stream's own mud still covered the bed under the road (forda 60.05-81.00 m) after the section went Dirt.
		float Mud = FMath::Clamp(GTTerrain::ChannelDigM(Spec, XM, YM) / FMath::Max(0.1f, Spec.MudChannelDepthM) - 0.5f, 0.f, 1.f);
		if (Road.bValid && Road.bFirmFordBed)
		{
			Mud *= 1.f - RoadWeight;
		}
		if (Mud > 0.f)
		{
			for (int32 Layer = 0; Layer < GTTerrain::LayerCount; ++Layer)
			{
				Weights[Layer] *= 1.f - Mud;
			}
			Weights[2] += Mud;
		}
		// RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): no Mud or Bog outside every mud patch box. The wheels sink by
		// the row under them and only a patch deforms, so Mud painted anywhere else (the channel bottoms above, the edge
		// of a bog's paving past its box, a Mud span, a Mud line or plane) sank them into ground that never moved (the
		// owner's picture 1, beside forda). It goes to Dirt; inside a box nothing changes.
		const float Soft = Weights[2] + Weights[5];
		if (Soft > 0.f)
		{
			const FVector2D PointCm(XM * 100.f, YM * 100.f);
			bool bInBox = false;
			for (const FBox2D& Box : Profiles.MudBoxesCm)
			{
				if (Box.IsInsideOrOn(PointCm))
				{
					bInBox = true;
					break;
				}
			}
			if (!bInBox)
			{
				Weights[1] += Soft;
				Weights[2] = 0.f;
				Weights[5] = 0.f;
			}
		}
		// Snow above the line, everything.
		if (HeightAtPoint > Spec.SnowLineM)
		{
			const float Snow = FMath::Clamp((HeightAtPoint - Spec.SnowLineM) / 5.f, 0.f, 1.f);
			for (int32 Layer = 0; Layer < GTTerrain::LayerCount; ++Layer)
			{
				Weights[Layer] *= 1.f - Snow;
			}
			Weights[3] += Snow;
		}
	}
}

namespace
{
	// ---- leg dressing LD1: the biome rules ----------------------------------------------------------------------------

	/**
	 * The standard deviation of FMath::PerlinNoise2D over the plane, measured 2026-09-27 on 400000 random points of a port
	 * of the engine's function (UnrealMath.cpp: the Grad2 corners and axes, the quintic curve): 0.2622, range -0.99..0.97.
	 * The raw noise piles up round 0 (0.5 + 0.5 n puts 28 % of the land in a 0.45-0.55 band); through the normal CDF with
	 * this sigma every tenth of 0..1 holds 9.6-10.6 % of it, so a rule's noise band reads as the share of land it names.
	 */
	constexpr float BiomePerlinSigma = 0.2622f;

	/** LD1b: one rule's route-section band - the main route's polyline cut to the sections of its kinds, and their box grown by the band. */
	struct FBiomeSectionLines
	{
		TArray<FVector2D> SegmentsM;   // pairs: A, B
		FBox2D ReachM = FBox2D(ForceInit);
	};

	/** What a spec's rules make: the biome layers in order, each rule's layer index, where each rule's noise comes from. */
	struct FBiomePlan
	{
		TArray<FName> Layers;
		TArray<int32> RuleLayer;
		TArray<int32> NoiseSource;
		/** LD1b: per rule, its section lines (empty for a rule with no MaxSectionDistM). */
		TArray<FBiomeSectionLines> SectionLines;
		int32 FallbackIndex = INDEX_NONE;
	};

	/**
	 * LD1b: the main route's polyline cut to every section whose kind is in Rule.SectionKinds (each section's StartM..EndM),
	 * as segments, and the box they reach with the band (MaxSectionDistM + FadeM) round them.
	 */
	FBiomeSectionLines MakeSectionLines(const FGTTerrainSpec& Spec, const FGTBiomeRule& Rule)
	{
		FBiomeSectionLines Lines;
		const TArray<FVector2D>& Route = Spec.RouteM;
		if (Rule.MaxSectionDistM <= 0.f || Route.Num() < 2)
		{
			return Lines;
		}
		for (const FGTRouteSection& Section : Spec.Sections)
		{
			const int32 Bit = 1 << static_cast<int32>(Section.Kind);
			if ((Rule.SectionKinds & Bit) == 0 || Section.EndM <= Section.StartM)
			{
				continue;
			}
			// The section's stretch of the polyline: its start, the route's vertices inside it, its end.
			TArray<FVector2D, TInlineAllocator<64>> Points;
			float Yaw;
			Points.Add(GTTerrain::PointOnPolyline(Route, Section.StartM, Yaw));
			float Arc = 0.f;
			for (int32 Index = 0; Index + 1 < Route.Num(); ++Index)
			{
				Arc += FVector2D::Distance(Route[Index], Route[Index + 1]);
				if (Arc > Section.StartM && Arc < Section.EndM)
				{
					Points.Add(Route[Index + 1]);
				}
			}
			Points.Add(GTTerrain::PointOnPolyline(Route, Section.EndM, Yaw));
			for (int32 Index = 0; Index + 1 < Points.Num(); ++Index)
			{
				Lines.SegmentsM.Add(Points[Index]);
				Lines.SegmentsM.Add(Points[Index + 1]);
				Lines.ReachM += Points[Index];
				Lines.ReachM += Points[Index + 1];
			}
		}
		if (Lines.SegmentsM.Num() > 0)
		{
			Lines.ReachM = Lines.ReachM.ExpandBy(Rule.MaxSectionDistM + FMath::Max(0.f, Rule.FadeM) + 1.f);
		}
		return Lines;
	}

	/** LD1b: a rule's route-section band at a point: 1 within MaxSectionDistM of its section lines, fading to 0 over FadeM beyond. */
	float SectionMask(const FGTBiomeRule& Rule, const FBiomeSectionLines& Lines, float XM, float YM)
	{
		const FVector2D P(XM, YM);
		if (Lines.SegmentsM.Num() == 0 || !Lines.ReachM.IsInside(P))
		{
			return 0.f;
		}
		float Nearest = TNumericLimits<float>::Max();
		for (int32 Index = 0; Index + 1 < Lines.SegmentsM.Num(); Index += 2)
		{
			float T;
			Nearest = FMath::Min(Nearest, DistanceToSegment(P, Lines.SegmentsM[Index], Lines.SegmentsM[Index + 1], T));
		}
		const float Fade = FMath::Max(0.f, Rule.FadeM);
		if (Fade <= 0.f)
		{
			return Nearest <= Rule.MaxSectionDistM ? 1.f : 0.f;
		}
		return 1.f - FMath::SmoothStep(Rule.MaxSectionDistM, Rule.MaxSectionDistM + Fade, Nearest);
	}

	FBiomePlan MakeBiomePlan(const FGTTerrainSpec& Spec)
	{
		FBiomePlan Plan;
		const int32 Rules = Spec.Biomes.Num();
		Plan.RuleLayer.Init(INDEX_NONE, Rules);
		Plan.NoiseSource.Init(INDEX_NONE, Rules);
		Plan.SectionLines.SetNum(Rules);
		for (int32 Rule = 0; Rule < Rules; ++Rule)
		{
			const FGTBiomeRule& R = Spec.Biomes[Rule];
			if (!R.Layer.IsNone())
			{
				Plan.RuleLayer[Rule] = Plan.Layers.AddUnique(R.Layer);
			}
			Plan.SectionLines[Rule] = MakeSectionLines(Spec, R);
			if (R.NoiseWavelengthM > 0.f)
			{
				Plan.NoiseSource[Rule] = Rule;
				for (int32 Earlier = 0; Earlier < Rule; ++Earlier)
				{
					const FGTBiomeRule& E = Spec.Biomes[Earlier];
					if (E.NoiseWavelengthM == R.NoiseWavelengthM && E.Seed == R.Seed)
					{
						Plan.NoiseSource[Rule] = Plan.NoiseSource[Earlier];
						break;
					}
				}
			}
		}
		if (!Spec.FallbackBiome.IsNone())
		{
			Plan.FallbackIndex = Plan.Layers.AddUnique(Spec.FallbackBiome);
		}
		return Plan;
	}

	/** A rule's noise at a point, about uniform over 0..1 (BiomePerlinSigma). */
	float BiomeNoise01(const FGTBiomeRule& Rule, float XM, float YM)
	{
		const FVector2D Offset(Rule.Seed * 1731.13f + 4096.5f, Rule.Seed * 1187.77f + 2048.25f);
		const float N = FMath::PerlinNoise2D((FVector2D(XM, YM) + Offset) / FMath::Max(1.f, Rule.NoiseWavelengthM));
		return FMath::Clamp(0.5f * (1.f + static_cast<float>(std::erf(N / (BiomePerlinSigma * 1.41421356f)))), 0.f, 1.f);
	}

	/** 1 inside [Min, Max], 0 outside, a smoothstep Fade wide centred on each limit; a zero limit is none. */
	float BandMask(float Value, float Min, float Max, float Fade)
	{
		const float Half = FMath::Max(0.f, Fade) * 0.5f;
		float Mask = 1.f;
		if (Min != 0.f)
		{
			Mask *= Half > 0.f ? FMath::SmoothStep(Min - Half, Min + Half, Value) : (Value >= Min ? 1.f : 0.f);
		}
		if (Max != 0.f)
		{
			Mask *= Half > 0.f ? 1.f - FMath::SmoothStep(Max - Half, Max + Half, Value) : (Value < Max ? 1.f : 0.f);
		}
		return Mask;
	}

	float RuleMask(const FGTBiomeRule& Rule, float HeightAtPoint, float SlopeDeg, float Noise)
	{
		float Mask = BandMask(HeightAtPoint, Rule.MinHeightM, Rule.MaxHeightM, Rule.FadeM);
		if (Mask > 0.f)
		{
			Mask *= BandMask(SlopeDeg, Rule.MinSlopeDeg, Rule.MaxSlopeDeg, Rule.FadeDeg);
		}
		if (Mask > 0.f && Rule.NoiseWavelengthM > 0.f)
		{
			// The noise is 0..1: a NoiseMin of 0 or less and a NoiseMax of 1 or more are no limit (a fade across 1 would
			// thin the band's top).
			Mask *= BandMask(Noise, Rule.NoiseMin > 0.f ? Rule.NoiseMin : 0.f, Rule.NoiseMax < 1.f ? Rule.NoiseMax : 0.f, Rule.NoiseFade);
		}
		return Mask;
	}

	/**
	 * The shares of the off-road weight at a point: OutShares[i] for biome layer i, and OutShares[Plan.Layers.Num()] what
	 * stays on the off-road layer (nothing when there is a fallback). Priority compositing: rule r takes its mask of what
	 * the rules before it left. The shares sum to 1.
	 */
	void BiomeShares(const FGTTerrainSpec& Spec, const FBiomePlan& Plan, float XM, float YM, float HeightAtPoint, float SlopeDeg, TArrayView<float> OutShares, TArrayView<float> NoiseScratch)
	{
		const int32 Layers = Plan.Layers.Num();
		for (float& Share : OutShares)
		{
			Share = 0.f;
		}
		const int32 Rules = Spec.Biomes.Num();
		for (int32 Rule = 0; Rule < Rules; ++Rule)
		{
			const int32 Source = Plan.NoiseSource[Rule];
			NoiseScratch[Rule] = Source == INDEX_NONE ? 0.f : (Source == Rule ? BiomeNoise01(Spec.Biomes[Rule], XM, YM) : NoiseScratch[Source]);
		}
		float Remaining = 1.f;
		for (int32 Rule = 0; Rule < Rules && Remaining > 0.f; ++Rule)
		{
			const int32 Layer = Plan.RuleLayer[Rule];
			if (Layer == INDEX_NONE)
			{
				continue;
			}
			const FGTBiomeRule& R = Spec.Biomes[Rule];
			float Mask = RuleMask(R, HeightAtPoint, SlopeDeg, NoiseScratch[Rule]);
			if (R.MaxSectionDistM > 0.f && Mask > 0.f)
			{
				Mask *= SectionMask(R, Plan.SectionLines[Rule], XM, YM);
			}
			const float Take = Mask * Remaining;
			OutShares[Layer] += Take;
			Remaining -= Take;
		}
		Remaining = FMath::Max(0.f, Remaining);
		OutShares[Plan.FallbackIndex != INDEX_NONE ? Plan.FallbackIndex : Layers] += Remaining;
	}

	/**
	 * LD1: shares every vertex's off-road byte out among the biome layers (weight layers LayerCount and up) by BiomeShares,
	 * to the byte: the largest remainders get the leftover units, so the biome bytes (plus what stays on the off-road layer
	 * without a fallback) add up to exactly the byte the off-road layer had. Layers 0-5 other than the off-road one are not
	 * touched. The slope is the grid's own over SlopeDegrees' step where that is whole quads and inside the grid (the same
	 * difference SlopeDegrees takes), else SlopeDegrees.
	 */
	void ShareOffRoad(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, const FBiomePlan& Plan, const TArray<float>& HeightsM, TArray<TArray<uint8>>& Weights)
	{
		const int32 Verts = GTTerrain::VertsPerSide(Spec);
		const int32 Layers = Plan.Layers.Num();
		const int32 Ground = FMath::Clamp(Spec.OffRoadLayer, 0, GTTerrain::LayerCount - 1);
		const float MetresPerQuad = Spec.QuadSizeCm / 100.f;
		const float OriginXM = Spec.OriginXCm / 100.f;
		const float OriginYM = Spec.OriginYCm / 100.f;
		const float StepM = FMath::Max(4.f, Spec.QuadSizeCm / 100.f);
		const float StepQuads = StepM / FMath::Max(MetresPerQuad, KINDA_SMALL_NUMBER);
		const int32 K = FMath::RoundToInt(StepQuads);
		const bool bGridStep = K >= 1 && FMath::IsNearlyEqual(StepQuads, static_cast<float>(K), 1.e-3f);
		TArray<float, TInlineAllocator<32>> Shares;
		Shares.SetNumZeroed(Layers + 1);
		TArray<float, TInlineAllocator<32>> Noise;
		Noise.SetNumZeroed(Spec.Biomes.Num());
		TArray<float, TInlineAllocator<32>> Exact;
		Exact.SetNumZeroed(Layers + 1);
		TArray<int32, TInlineAllocator<32>> Bytes;
		Bytes.SetNumZeroed(Layers + 1);
		for (int32 Y = 0; Y < Verts; ++Y)
		{
			for (int32 X = 0; X < Verts; ++X)
			{
				const int32 Index = Y * Verts + X;
				const int32 Off = Weights[Ground][Index];
				if (Off == 0)
				{
					continue;
				}
				const float XM = OriginXM + X * MetresPerQuad;
				const float YM = OriginYM + Y * MetresPerQuad;
				float Slope;
				if (bGridStep && X >= K && X + K < Verts && Y >= K && Y + K < Verts)
				{
					const float DX = (HeightsM[Index + K] - HeightsM[Index - K]) / (2.f * StepM);
					const float DY = (HeightsM[Index + K * Verts] - HeightsM[Index - K * Verts]) / (2.f * StepM);
					Slope = FMath::RadiansToDegrees(FMath::Atan(FMath::Sqrt(DX * DX + DY * DY)));
				}
				else
				{
					Slope = GTTerrain::SlopeDegrees(Spec, Profiles, XM, YM);
				}
				BiomeShares(Spec, Plan, XM, YM, HeightsM[Index], Slope, Shares, Noise);
				float Sum = 0.f;
				for (const float Share : Shares)
				{
					Sum += Share;
				}
				Sum = FMath::Max(Sum, KINDA_SMALL_NUMBER);
				int32 Given = 0;
				for (int32 Bucket = 0; Bucket <= Layers; ++Bucket)
				{
					Exact[Bucket] = Off * Shares[Bucket] / Sum;
					Bytes[Bucket] = FMath::Clamp(FMath::FloorToInt(Exact[Bucket]), 0, Off);
					Given += Bytes[Bucket];
				}
				// The leftover units to the largest remainders (the first on a tie); never more than one each.
				for (int32 Left = Off - Given; Left > 0; --Left)
				{
					int32 Best = INDEX_NONE;
					float BestRemainder = -1.f;
					for (int32 Bucket = 0; Bucket <= Layers; ++Bucket)
					{
						const float Remainder = Exact[Bucket] - Bytes[Bucket];
						if (Remainder > BestRemainder)
						{
							BestRemainder = Remainder;
							Best = Bucket;
						}
					}
					++Bytes[Best];
					Exact[Best] = static_cast<float>(Bytes[Best]);   // taken: its remainder is now <= 0
				}
				for (int32 Bucket = 0; Bucket < Layers; ++Bucket)
				{
					Weights[GTTerrain::LayerCount + Bucket][Index] = static_cast<uint8>(Bytes[Bucket]);
				}
				Weights[Ground][Index] = static_cast<uint8>(Bytes[Layers]);
			}
		}
	}
}

bool GTTerrain::HasBiomes(const FGTTerrainSpec& Spec)
{
	return MakeBiomePlan(Spec).Layers.Num() > 0;
}

void GTTerrain::BiomeLayers(const FGTTerrainSpec& Spec, TArray<FName>& OutLayers)
{
	OutLayers = MakeBiomePlan(Spec).Layers;
}

void GTTerrain::WeightLayerNames(const FGTTerrainSpec& Spec, TArray<FName>& OutNames)
{
	OutNames.Reset();
	for (int32 Layer = 0; Layer < GTTerrain::LayerCount; ++Layer)
	{
		OutNames.Add(FName(LayerName(Layer)));
	}
	OutNames.Append(MakeBiomePlan(Spec).Layers);
}

FName GTTerrain::BiomeAt(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM)
{
	const FBiomePlan Plan = MakeBiomePlan(Spec);
	const int32 Layers = Plan.Layers.Num();
	if (Layers == 0)
	{
		return NAME_None;
	}
	TArray<float, TInlineAllocator<32>> Shares;
	Shares.SetNumZeroed(Layers + 1);
	TArray<float, TInlineAllocator<32>> Noise;
	Noise.SetNumZeroed(Spec.Biomes.Num());
	BiomeShares(Spec, Plan, XM, YM, HeightM(Spec, Profiles, XM, YM), SlopeDegrees(Spec, Profiles, XM, YM), Shares, Noise);
	int32 Best = Layers;   // what stays on the off-road layer
	for (int32 Bucket = 0; Bucket < Layers; ++Bucket)
	{
		if (Shares[Bucket] > Shares[Best])
		{
			Best = Bucket;
		}
	}
	return Best < Layers ? Plan.Layers[Best] : NAME_None;
}

int32 GTTerrain::LayerAt(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM)
{
	float Weights[GTTerrain::LayerCount];
	LayerWeights(Spec, Profiles, XM, YM, HeightM(Spec, Profiles, XM, YM), Weights);
	int32 Best = 1;
	for (int32 Layer = 0; Layer < GTTerrain::LayerCount; ++Layer)
	{
		if (Weights[Layer] > Weights[Best])
		{
			Best = Layer;
		}
	}
	return Best;
}

float GTTerrain::OffRoadWeight(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM)
{
	float Weights[GTTerrain::LayerCount];
	LayerWeights(Spec, Profiles, XM, YM, HeightM(Spec, Profiles, XM, YM), Weights);
	return Weights[FMath::Clamp(Spec.OffRoadLayer, 0, GTTerrain::LayerCount - 1)];
}

float GTTerrain::SlopeDegrees(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM)
{
	// The landform's slope over 4 m, not the relief's bumps (rocks are placed by it).
	const float Step = FMath::Max(4.f, Spec.QuadSizeCm / 100.f);
	const float DX = (HeightM(Spec, Profiles, XM + Step, YM) - HeightM(Spec, Profiles, XM - Step, YM)) / (2.f * Step);
	const float DY = (HeightM(Spec, Profiles, XM, YM + Step) - HeightM(Spec, Profiles, XM, YM - Step)) / (2.f * Step);
	return FMath::RadiansToDegrees(FMath::Atan(FMath::Sqrt(DX * DX + DY * DY)));
}

float GTTerrain::FordWaterLevelM(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, const FGTRouteSection& Section)
{
	float Lowest = 1e9f;
	for (float Arc = Section.StartM; Arc <= Section.EndM; Arc += 1.f)
	{
		Lowest = FMath::Min(Lowest, Profiles.Main.HeightAt(Arc));
	}
	return (Lowest < 1e8f ? Lowest : 0.f) + Section.DepthM;
}

void GTTerrain::WaterBarArcs(const FGTTerrainSpec& Spec, const FGTRouteSection& Section, TArray<float>& OutArcsM)
{
	OutArcsM.Reset();
	if (Section.Kind != EGTRouteSectionKind::Track || Spec.WaterBarSpacingM <= 0.f || Spec.WaterBarHeightM <= 0.f)
	{
		return;
	}
	const int32 Count = FMath::CeilToInt((Section.EndM - Section.StartM) / FMath::Max(1.f, Spec.WaterBarSpacingM)) + 1;
	for (int32 K = 0; K < Count; ++K)
	{
		const float Centre = WaterBarArc(Spec, Section, K);
		if (Centre >= Section.StartM + 3.f && Centre <= Section.EndM - 3.f)
		{
			OutArcsM.Add(Centre);
		}
	}
}

float GTTerrain::RutWanderAt(const FGTTerrainSpec& Spec, float ArcM)
{
	return Spec.RutWanderM * FMath::PerlinNoise1D(ArcM / FMath::Max(1.f, Spec.RutWanderWavelengthM) + Spec.Seed * 0.37f);
}

void GTTerrain::TrackStones(const FGTTerrainSpec& Spec, TArray<FGTTerrainStone>& OutStones)
{
	OutStones.Reset();
	if (Spec.TrackStoneSpacingM <= 0.f)
	{
		return;
	}
	const float Spacing = FMath::Max(0.5f, Spec.TrackStoneSpacingM);
	int32 Serial = 0;
	for (int32 SectionIndex = 0; SectionIndex < Spec.Sections.Num(); ++SectionIndex)
	{
		const FGTRouteSection& Section = Spec.Sections[SectionIndex];
		if (Section.Kind != EGTRouteSectionKind::Track)
		{
			continue;
		}
		const float HalfWidth = HalfWidthAt(Spec, (Section.StartM + Section.EndM) * 0.5f);
		for (float Arc = Section.StartM + 2.f; Arc <= Section.EndM - 2.f; Arc += Spacing, ++Serial)
		{
			const float ArcJitter = (Hash01(Spec, Serial, 1) - 0.5f) * 0.8f * Spacing;
			const float Lateral = (Hash01(Spec, Serial, 2) * 2.f - 1.f) * FMath::Max(0.f, HalfWidth - 0.4f);
			float Yaw;
			const FVector2D Point = PointOnPolyline(Spec.RouteM, Arc + ArcJitter, Yaw);
			const FVector2D Left(-FMath::Sin(FMath::DegreesToRadians(Yaw)), FMath::Cos(FMath::DegreesToRadians(Yaw)));
			FGTTerrainStone Stone;
			Stone.PositionM = Point + Left * Lateral;
			Stone.SizeM = FMath::Lerp(Spec.TrackStoneMinM, Spec.TrackStoneMaxM, Hash01(Spec, Serial, 3));
			Stone.YawDegrees = Hash01(Spec, Serial, 4) * 360.f;
			Stone.PitchDegrees = (Hash01(Spec, Serial, 5) - 0.5f) * 30.f;
			Stone.RollDegrees = (Hash01(Spec, Serial, 6) - 0.5f) * 30.f;
			OutStones.Add(Stone);
		}
	}
}

void GTTerrain::RallyPosts(const FGTTerrainSpec& Spec, TArray<FGTTerrainPost>& OutPosts)
{
	OutPosts.Reset();
	if (Spec.RallyPostSpacingM <= 0.f)
	{
		return;
	}
	const float Spacing = FMath::Max(5.f, Spec.RallyPostSpacingM);
	int32 Serial = 0;
	for (const FGTRouteSection& Section : Spec.Sections)
	{
		if (Section.Kind != EGTRouteSectionKind::Rally)
		{
			continue;
		}
		// Clear of the stretch's ends by 20 m, where the road changes width and the neighbours' runs start.
		for (float Arc = Section.StartM + 20.f; Arc <= Section.EndM - 20.f; Arc += Spacing, ++Serial)
		{
			for (const float Side : { -1.f, 1.f })
			{
				const float At = Arc + (Hash01(Spec, Serial, Side > 0.f ? 7 : 8) - 0.5f) * 0.4f * Spacing;
				float Yaw;
				const FVector2D Point = PointOnPolyline(Spec.RouteM, At, Yaw);
				const FVector2D Left(-FMath::Sin(FMath::DegreesToRadians(Yaw)), FMath::Cos(FMath::DegreesToRadians(Yaw)));
				FGTTerrainPost Post;
				Post.PositionM = Point + Left * Side * (HalfWidthAt(Spec, At) + Spec.VergeWidthM + 0.5f);
				Post.YawDegrees = Yaw;
				OutPosts.Add(Post);
			}
		}
	}
}

void GTTerrain::FordRocks(const FGTTerrainSpec& Spec, TArray<FGTTerrainStone>& OutRocks)
{
	OutRocks.Reset();
	if (Spec.FordRockCount <= 0 || Spec.RouteM.Num() < 2)
	{
		return;
	}
	const FGTTerrainProfiles Profiles = BuildProfiles(Spec);
	const float MinSize = FMath::Max(0.2f, FMath::Min(Spec.FordRockMinM, Spec.FordRockMaxM));
	const float MaxSize = FMath::Max(MinSize, Spec.FordRockMaxM);
	const float HalfLane = FMath::Max(0.f, Spec.FordLaneM * 0.5f);
	const float ExposedPerMetreCm = FMath::Max(1.f, FordRockExposedCm(1.f));
	// The sheet Art/setup_m6_hide.py lays over a ford reaches 15 m either side of the route and half the section's
	// length plus 12 m along it: a rock outside that is not in the water the field simulates.
	constexpr float HalfAcrossM = 14.f;
	for (int32 SectionIndex = 0; SectionIndex < Spec.Sections.Num(); ++SectionIndex)
	{
		const FGTRouteSection& Section = Spec.Sections[SectionIndex];
		if (Section.Kind != EGTRouteSectionKind::Ford)
		{
			continue;
		}
		// The Proving Ground (2026-09-19): a section may ask for its own count; -1 takes the spec's, as before.
		const int32 RockCount = Section.FordRockCountOverride >= 0 ? Section.FordRockCountOverride : Spec.FordRockCount;
		if (RockCount <= 0)
		{
			continue;
		}
		const float LevelM = FordWaterLevelM(Spec, Profiles, Section);
		const float MidArc = (Section.StartM + Section.EndM) * 0.5f;
		const float HalfAlongM = FMath::Min(25.f, (Section.EndM - Section.StartM) * 0.5f + 12.f);
		// Which side of the route the current runs toward, and the middle of the crossing: a rock that stands over the
		// surface belongs in the current, not in the friction ramp at the sheet's flow-wise ends.
		float MidYaw = 0.f;
		const FVector2D MidPoint = PointOnPolyline(Spec.RouteM, MidArc, MidYaw);
		const FVector2D LeftAtMid(-FMath::Sin(FMath::DegreesToRadians(MidYaw)), FMath::Cos(FMath::DegreesToRadians(MidYaw)));
		const float FlowYaw = MidYaw + Section.FlowYawOffsetDeg;
		const FVector2D FlowDir(FMath::Cos(FMath::DegreesToRadians(FlowYaw)), FMath::Sin(FMath::DegreesToRadians(FlowYaw)));
		const float DownstreamSide = FVector2D::DotProduct(FlowDir, LeftAtMid) >= 0.f ? 1.f : -1.f;
		const int32 First = OutRocks.Num();
		int32 Serial = SectionIndex * 1000;
		int32 SinceLast = 0;
		int32 Proud = 0;
		for (int32 Attempt = 0; Attempt < RockCount * 120 && OutRocks.Num() - First < RockCount; ++Attempt, ++Serial)
		{
			const int32 Placed = OutRocks.Num() - First;
			++SinceLast;
			// A rock's ROLE - on the lane's edge, or tall enough to break the surface - asks for water of a particular
			// depth in a particular place, and a channel that has none of that anywhere would otherwise spend every
			// attempt on the same impossible rock. After 120 fruitless tries the role is given up and an ordinary rock
			// is placed instead.
			const bool bRelax = SinceLast > 120;
			// The first two stand on the lane's edges, one each side; every other rock is clear of the lane.
			const bool bOnLaneEdge = Placed < 2 && !bRelax;
			const float Side = bOnLaneEdge ? (Placed == 0 ? -1.f : 1.f) : (Hash01(Spec, Serial, 31) < 0.5f ? -1.f : 1.f);
			const float Lateral = bOnLaneEdge
				? Side * (HalfLane + 0.15f)
				: Side * FMath::Lerp(HalfLane + 0.6f, HalfAcrossM, Hash01(Spec, Serial, 32));
			// Clear of the crossing's middle along the route: the current runs across the route, so the strip of water
			// that feeds the spot the car parks and drives through has to have nothing standing in it.
			const float ClearM = FMath::Clamp(Spec.FordRockClearM, 0.f, HalfAlongM - 1.f);
			const float ArcSide = Hash01(Spec, Serial, 33) < 0.5f ? -1.f : 1.f;
			const float Arc = MidArc + ArcSide * FMath::Lerp(ClearM, HalfAlongM, Hash01(Spec, Serial, 38));
			// The recovery line is left clear: a car that loses the crossing is taken downstream and winched back out
			// past the ford's exit, which is a line from the crossing's middle running down the route and about 20
			// degrees into the current (Art/setup_m6_hide.py puts Post_Ford 35 m along the route and 12 m downstream of
			// it). With rocks in that lane the terrain test's cable snagged and snapped at 40 kN on the way out
			// (measured, 2026-09-18); either side of it they are only scenery to the winch.
			if (Side == DownstreamSide)
			{
				// The downstream half of the crossing is left clear altogether. It is where the current takes a car
				// that has lost the ford and the whole lane the winch then drags it back along to Post_Ford by the
				// exit. Measured 2026-09-18, three runs: with rocks anywhere in that half the terrain test's tow
				// stalled after 3.1 m and the cable snapped at 40 kN, where the same tow reaches the post in 24 s with
				// it clear - and the nearest rock was nine metres from the car, so what the tow catches on is not
				// simply the rock it touches. Upstream of the route they are the same scenery to the driver and the
				// water, and the recovery is the user's own drive gate.
				continue;
			}
			float Yaw = 0.f;
			const FVector2D Point = PointOnPolyline(Spec.RouteM, Arc, Yaw);
			const FVector2D Left(-FMath::Sin(FMath::DegreesToRadians(Yaw)), FMath::Cos(FMath::DegreesToRadians(Yaw)));
			const FVector2D At = Point + Left * Lateral;
			const float GroundM = HeightM(Spec, Profiles, At.X, At.Y);
			const float DepthCm = (LevelM - GroundM) * 100.f;
			if (DepthCm < 20.f)
			{
				continue;   // the bank, or a shallow the channel's water never reaches
			}
			bool bTooNear = false;
			for (int32 K = First; K < OutRocks.Num(); ++K)
			{
				if (FVector2D::Distance(OutRocks[K].PositionM, At) < 2.f)
				{
					bTooNear = true;
					break;
				}
			}
			if (bTooNear)
			{
				continue;
			}
			// About a third of them stand over the surface - sized so their top is 12 cm over the ford's level; the
			// rest are sized to stay 8 cm under it. A spot too deep for a proud rock, or too shallow to drown the
			// smallest one, is passed over and another is tried.
			// A rock is sized to stand 12 cm over the ford's level or to keep its top 5 cm under it, and the water
			// where it stands decides which of the two it can be at all: about every third one is asked to break the
			// surface, and a spot that cannot take the role it was asked for is given the other rather than passed
			// over - a channel whose shallows can only hold proud rocks and whose deeps can only drown them would
			// otherwise place a third of what it was asked for (measured: 5 of 14).
			const bool bCanProud = (DepthCm + 12.f) / ExposedPerMetreCm <= MaxSize;
			const bool bCanSink = (DepthCm - 5.f) / ExposedPerMetreCm >= MinSize;
			bool bProud = !bOnLaneEdge && !bRelax && (Placed % 3) == 2;
			if (bProud && !bCanProud)
			{
				bProud = false;
			}
			else if (!bProud && !bCanSink && bCanProud && !bOnLaneEdge && Proud * 2 < RockCount)
			{
				bProud = true;
			}
			if (bProud ? !bCanProud : !bCanSink)
			{
				continue;
			}
			float SizeM = MinSize;
			if (bProud)
			{
				SizeM = FMath::Max((DepthCm + 12.f) / ExposedPerMetreCm, MinSize);
			}
			else
			{
				SizeM = FMath::Min(FMath::Lerp(MinSize, MaxSize, Hash01(Spec, Serial, 34)), (DepthCm - 5.f) / ExposedPerMetreCm);
			}
			FGTTerrainStone Rock;
			Rock.PositionM = At;
			Rock.SizeM = FMath::Clamp(SizeM, MinSize, MaxSize);
			Rock.YawDegrees = Hash01(Spec, Serial, 35) * 360.f;
			// Turned freely but tilted little: the height of the top over the bed is what the water test reads against
			// the ring of cells a metre out, and a cube up on its corner puts that reading where nothing stands.
			Rock.PitchDegrees = (Hash01(Spec, Serial, 36) - 0.5f) * 12.f;
			Rock.RollDegrees = (Hash01(Spec, Serial, 37) - 0.5f) * 12.f;
			OutRocks.Add(Rock);
			Proud += bProud ? 1 : 0;
			SinceLast = 0;
		}
		UE_LOG(LogTemp, Display, TEXT("GTTerrain::FordRocks: %d of %d rock(s) placed in the ford at %.0f-%.0f m, %d of them over the water (at %.2f m); a lane of %.1f m, %.1f m of the crossing's middle and the whole downstream half left clear"),
			OutRocks.Num() - First, RockCount, Section.StartM, Section.EndM, Proud, LevelM, Spec.FordLaneM, Spec.FordRockClearM);
	}
}

void GTTerrain::Generate(const FGTTerrainSpec& Spec, TArray<uint16>& OutHeights, TArray<TArray<uint8>>& OutWeights)
{
	const int32 Verts = VertsPerSide(Spec);
	const FGTTerrainProfiles Profiles = BuildProfiles(Spec);
	// Leg dressing LD1: the biome layers after the six surface layers, none on a spec without biomes. The surface layers
	// are made exactly as they always were; ShareOffRoad then splits the off-road byte, reading the heights kept here.
	const FBiomePlan Plan = MakeBiomePlan(Spec);
	const bool bBiomes = Plan.Layers.Num() > 0;
	TArray<float> HeightsM;
	if (bBiomes)
	{
		HeightsM.SetNumUninitialized(Verts * Verts);
	}
	OutHeights.SetNumUninitialized(Verts * Verts);
	OutWeights.SetNum(GTTerrain::LayerCount + Plan.Layers.Num());
	for (TArray<uint8>& Layer : OutWeights)
	{
		Layer.SetNumZeroed(Verts * Verts);
	}
	for (int32 Layer = GTTerrain::LayerCount; Layer < OutWeights.Num(); ++Layer)
	{
		FMemory::Memzero(OutWeights[Layer].GetData(), OutWeights[Layer].Num());
	}
	const float MetresPerQuad = Spec.QuadSizeCm / 100.f;
	const float OriginXM = Spec.OriginXCm / 100.f;
	const float OriginYM = Spec.OriginYCm / 100.f;
	for (int32 Y = 0; Y < Verts; ++Y)
	{
		for (int32 X = 0; X < Verts; ++X)
		{
			const float XM = OriginXM + X * MetresPerQuad;
			const float YM = OriginYM + Y * MetresPerQuad;
			const float H = HeightM(Spec, Profiles, XM, YM);
			if (bBiomes)
			{
				HeightsM[Y * Verts + X] = H;
			}
			const float Value = 32768.f + H * 100.f * 128.f / FMath::Max(1.f, Spec.ZScale);
			OutHeights[Y * Verts + X] = static_cast<uint16>(FMath::Clamp(FMath::RoundToInt(Value), 0, 65535));
			float Weights[GTTerrain::LayerCount];
			LayerWeights(Spec, Profiles, XM, YM, H, Weights);
			float Sum = 0.f;
			for (int32 Layer = 0; Layer < GTTerrain::LayerCount; ++Layer)
			{
				Sum += Weights[Layer];
			}
			Sum = FMath::Max(Sum, KINDA_SMALL_NUMBER);
			int32 Given = 0;
			for (int32 Layer = 0; Layer < GTTerrain::LayerCount; ++Layer)
			{
				const int32 Byte = Layer == GTTerrain::LayerCount - 1 ? 255 - Given : FMath::Clamp(FMath::RoundToInt(255.f * Weights[Layer] / Sum), 0, 255 - Given);
				OutWeights[Layer][Y * Verts + X] = static_cast<uint8>(Byte);
				Given += Byte;
			}
		}
	}
	if (bBiomes)
	{
		ShareOffRoad(Spec, Profiles, Plan, HeightsM, OutWeights);
	}
}

uint64 GTTerrain::HashGrid(const TArray<uint16>& Heights, const TArray<TArray<uint8>>& Weights)
{
	// CityHash64 over each buffer, chained through the seed; the layer count and each length go in first, so a grid
	// that gains a layer or loses a vertex hashes differently even when the bytes it keeps are the same.
	uint64 Hash = CityHash64WithSeed(reinterpret_cast<const char*>(Heights.GetData()), Heights.Num() * sizeof(uint16), 0x4C44315F48415348ull ^ static_cast<uint64>(Weights.Num()));
	for (const TArray<uint8>& Layer : Weights)
	{
		Hash = CityHash64WithSeed(reinterpret_cast<const char*>(Layer.GetData()), Layer.Num(), Hash ^ static_cast<uint64>(Layer.Num()));
	}
	return Hash;
}

uint64 GTTerrain::GenerateHash(const FGTTerrainSpec& Spec)
{
	TArray<uint16> Heights;
	TArray<TArray<uint8>> Weights;
	Generate(Spec, Heights, Weights);
	return HashGrid(Heights, Weights);
}

float GTTerrain::SampleHeightCm(const FGTTerrainSpec& Spec, float XCm, float YCm)
{
	const FGTTerrainProfiles Profiles = BuildProfiles(Spec);
	return HeightM(Spec, Profiles, XCm / 100.f, YCm / 100.f) * 100.f;
}

FGTRouteHit GTTerrain::RouteAtCm(const FGTTerrainSpec& Spec, float XCm, float YCm)
{
	return NearestRoute(Spec, XCm / 100.f, YCm / 100.f);
}

namespace
{
	/**
	 * Leg dressing LD6 (docs/LEG_DRESSING_PLAN.md section 5, D2): The Hide's biome palette, rules in order with soft edges
	 * (every number a dial; DA_Terrain_Hide carries a copy the owner edits). The one source: HideSpec() ends with it, and
	 * the biome test (FGTBiomeTestRunner::AddD2Palette) reads it from there. The forest mask is one noise (300 m, seed 11)
	 * read by ForestFir, Forest and Thicket's ring, so the ring hugs the forest's edge. Revised 2026-09-27 (LD1b): the
	 * forest from 0.70 (0.55 gave 43 %), the ring 0.64-0.70, and the riparian Thicket by its distance to the Ford and Mud
	 * sections (the "height < 3 m" rule took the whole valley, 19 %); the riparian rule evaluated after Alpine and before
	 * the forest rules (the fords and the bog sit inside the forest noise, so under Forest's priority it painted 0 %).
	 */
	void AddHideBiomes(FGTTerrainSpec& Spec)
	{
		constexpr float ForestWavelengthM = 300.f;
		constexpr int32 ForestSeed = 11;
		// The forest from 0.70: Forest + ForestFir 27.1 % of the off-road land (0.76 gave 21.6 %, under the biome test's 22 %
		// floor); the ring keeps its 0.06 band just under it. LD7 cut step 6 moved it to 0.75 for no measured gain, and LD8a
		// (docs/LEG_DRESSING_PLAN.md) put it back.
		constexpr float ForestNoiseMin = 0.70f;
		constexpr float RingBand = 0.06f;
		auto Rule = [](const TCHAR* Layer)
		{
			FGTBiomeRule R;
			R.Layer = FName(Layer);
			return R;
		};
		Spec.Biomes.Reset();
		FGTBiomeRule R = Rule(TEXT("OW_Scree"));           // 1. slope >= 32 deg
		R.MinSlopeDeg = 32.f;
		R.FadeDeg = 4.f;
		Spec.Biomes.Add(R);
		R = Rule(TEXT("OW_Alpine"));                        // 2. height >= 75 m
		R.MinHeightM = 75.f;
		R.FadeM = 6.f;
		Spec.Biomes.Add(R);
		R = Rule(TEXT("Thicket"));                          // 5b. riparian brush: within 40 m of a Ford or Mud section (fading over 10 m), an 80 m noise within 0.4-1
		R.MaxSectionDistM = 40.f;
		R.SectionKinds = (1 << static_cast<int32>(EGTRouteSectionKind::Ford)) | (1 << static_cast<int32>(EGTRouteSectionKind::Mud));
		R.FadeM = 10.f;
		R.NoiseWavelengthM = 80.f;
		R.Seed = 12;
		R.NoiseMin = 0.4f;
		R.NoiseMax = 1.f;
		R.NoiseFade = 0.06f;
		Spec.Biomes.Add(R);
		R = Rule(TEXT("OW_ForestFir"));                     // 3. the forest mask and height >= 45 m
		R.NoiseWavelengthM = ForestWavelengthM;
		R.Seed = ForestSeed;
		R.NoiseMin = ForestNoiseMin;
		R.NoiseMax = 1.f;
		R.NoiseFade = 0.04f;
		R.MaxSlopeDeg = 25.f;
		R.FadeDeg = 4.f;
		R.MinHeightM = 45.f;
		R.FadeM = 6.f;
		Spec.Biomes.Add(R);
		R = Rule(TEXT("OW_Forest"));                        // 4. the forest mask: the 300 m noise within 0.70-1, slope < 25 deg
		R.NoiseWavelengthM = ForestWavelengthM;
		R.Seed = ForestSeed;
		R.NoiseMin = ForestNoiseMin;
		R.NoiseMax = 1.f;
		R.NoiseFade = 0.04f;
		R.MaxSlopeDeg = 25.f;
		R.FadeDeg = 4.f;
		Spec.Biomes.Add(R);
		R = Rule(TEXT("Thicket"));                          // 5a. the forest-edge ring: the same noise within 0.64-0.70
		R.NoiseWavelengthM = ForestWavelengthM;
		R.Seed = ForestSeed;
		R.NoiseMin = ForestNoiseMin - RingBand;
		R.NoiseMax = ForestNoiseMin;
		R.NoiseFade = 0.04f;
		Spec.Biomes.Add(R);
		R = Rule(TEXT("OW_MeadowLush"));                    // 6. height < 5 m
		R.MaxHeightM = 5.f;
		R.FadeM = 2.f;
		Spec.Biomes.Add(R);
		R = Rule(TEXT("OW_MeadowDry"));                     // 7. a 150 m noise within 0.65-1
		R.NoiseWavelengthM = 150.f;
		R.Seed = 13;
		R.NoiseMin = 0.65f;
		R.NoiseMax = 1.f;
		R.NoiseFade = 0.06f;
		Spec.Biomes.Add(R);
		Spec.FallbackBiome = FName(TEXT("OW_Meadow"));      // 8. the rest
	}
}

FGTTerrainSpec GTTerrain::HideSpec()
{
	FGTTerrainSpec Spec;
	Spec.Seed = 3;
	Spec.BaseAmplitudeM = 20.f;
	Spec.BaseWavelengthM = 320.f;
	Spec.Octaves = 4;
	Spec.SlopeMPerKm = 22.f;
	// The route: a valley floor, a swing left up onto the plateau (the rally stretch, the pocket and the hide off to the
	// right), a bog, the ford through the stream, then a narrow track under the hillside to the zone. Checkpoints at
	// (500, 0) and (1100, 40), the zone at (1400, 0), as DA_Leg_03 has them. Arc marks: 292 at (250, 30), 543 at
	// (500, 0), 710 at (640, -90), 877 at (800, -40), 1058 at (950, 60), 1209 at (1100, 40), 1367 at (1250, 90),
	// 1542 at (1400, 0), 1631 at the end.
	Spec.RouteM = { FVector2D(-40.f, 0.f), FVector2D(250.f, 30.f), FVector2D(500.f, 0.f), FVector2D(640.f, -90.f), FVector2D(800.f, -40.f),
		FVector2D(950.f, 60.f), FVector2D(1100.f, 40.f), FVector2D(1250.f, 90.f), FVector2D(1400.f, 0.f), FVector2D(1480.f, -40.f) };
	Spec.RoadHalfWidthM = 6.f;
	Spec.ShoulderM = 14.f;
	Spec.MaxGradePercent = 13.f;
	Spec.RouteSmoothM = 80.f;
	auto Span = [&Spec](float Start, float End, int32 Layer) { FGTSurfaceSpan S; S.StartM = Start; S.EndM = End; S.Layer = Layer; Spec.Spans.Add(S); };
	Span(0.f, 330.f, 0);   // tarmac out of the valley, dirt from there
	auto Section = [&Spec](float Start, float End, EGTRouteSectionKind Kind, float Depth = 0.6f) { FGTRouteSection S; S.StartM = Start; S.EndM = End; S.Kind = Kind; S.DepthM = Depth; Spec.Sections.Add(S); };
	Section(560.f, 1030.f, EGTRouteSectionKind::Rally);    // over the plateau, two bends, crests kept
	// Stage 2: a crest on the straight after the first bend (in the air at 90 km/h), a compression into the second bend, a crest before the bog.
	auto Bump = [&Spec](float Arc, float Height, float Length) { FGTProfileBump B; B.ArcM = Arc; B.HeightM = Height; B.LengthM = Length; Spec.Sections.Last().Bumps.Add(B); };
	Bump(810.f, 0.9f, 24.f);
	Bump(862.f, -0.5f, 18.f);
	Bump(960.f, 0.8f, 22.f);
	Section(1035.f, 1085.f, EGTRouteSectionKind::Mud);      // the bog before the stream
	Section(1090.f, 1140.f, EGTRouteSectionKind::Ford, 0.6f);   // through the stream
	Section(1145.f, 1500.f, EGTRouteSectionKind::Track);    // the narrow track under the hillside
	// The detour: south round the plateau from the first checkpoint, rejoining before the bog.
	FGTAltRoute Detour;
	Detour.PointsM = { FVector2D(500.f, 0.f), FVector2D(560.f, -130.f), FVector2D(700.f, -210.f), FVector2D(860.f, -180.f), FVector2D(950.f, 60.f) };
	Detour.HalfWidthM = 3.5f;
	Detour.Layer = 1;
	Spec.AltRoutes.Add(Detour);
	auto Feature = [&Spec](EGTTerrainFeatureKind Kind, FVector2D Start, FVector2D End, float Radius, float Height)
	{
		FGTTerrainFeature F;
		F.Kind = Kind;
		F.StartM = Start;
		F.EndM = End;
		F.RadiusM = Radius;
		F.HeightM = Height;
		Spec.Features.Add(F);
	};
	// Valley walls either side of the first 450 m, higher than before.
	Feature(EGTTerrainFeatureKind::Ridge, FVector2D(-200.f, 95.f), FVector2D(430.f, 120.f), 70.f, 40.f);
	Feature(EGTTerrainFeatureKind::Ridge, FVector2D(-200.f, -85.f), FVector2D(430.f, -110.f), 70.f, 34.f);
	// The plateau the road climbs onto, with the bear's dell in a rise beside the radiation pocket.
	Feature(EGTTerrainFeatureKind::Hill, FVector2D(720.f, 120.f), FVector2D::ZeroVector, 160.f, 20.f);
	Feature(EGTTerrainFeatureKind::Bowl, FVector2D(735.f, 150.f), FVector2D::ZeroVector, 26.f, 5.f);
	// The stream that crosses the road around 1115 m.
	Feature(EGTTerrainFeatureKind::Channel, FVector2D(950.f, -220.f), FVector2D(1050.f, 260.f), 20.f, 3.2f);
	// The hillside the last stretch skirts (rock-strewn), and a ridge beyond the zone so the valley closes.
	Feature(EGTTerrainFeatureKind::Hill, FVector2D(1250.f, -260.f), FVector2D::ZeroVector, 230.f, 50.f);
	Feature(EGTTerrainFeatureKind::Ridge, FVector2D(1300.f, 170.f), FVector2D(1520.f, 280.f), 90.f, 26.f);
	Spec.OffRoadLayer = 4;
	Spec.MudChannelDepthM = 1.5f;
	// Leg dressing LD6: the D2 biome palette (the grid without it hashes to the pre-biome bytes; the biome test clears it).
	AddHideBiomes(Spec);
	return Spec;
}

FGTTerrainSpec GTTerrain::ProvingSpec()
{
	FGTTerrainSpec Spec;
	// The grid: 3 x 3 components of 2 x 63 one-metre quads = 378 m square, centred on the pad at (0, 0). The import
	// takes any whole number of components; 3 is the fewest that hold the loop, its shoulders and the ramps.
	Spec.ComponentsPerSide = 3;
	Spec.SubsectionsPerComponent = 2;
	Spec.QuadsPerSubsection = 63;
	Spec.QuadSizeCm = 100.f;
	Spec.OriginXCm = -18900.f;
	Spec.OriginYCm = -18900.f;
	// Gentle relief: +-2.5 m over 150 m, no tilt, a quieter scrub.
	Spec.Seed = 5;
	Spec.BaseAmplitudeM = 2.5f;
	Spec.BaseWavelengthM = 150.f;
	Spec.Octaves = 3;
	Spec.SlopeMPerKm = 0.f;
	Spec.ScrubRoughnessM = 0.12f;
	Spec.WaterBarSpacingM = 30.f;   // an 80 m track carries two or three bars
	Spec.RoadHalfWidthM = 6.f;
	Spec.ShoulderM = 14.f;
	Spec.MaxGradePercent = 14.f;
	Spec.RouteSmoothM = 80.f;

	// The loop: a 250 x 120 m rectangle with 25 m corners, starting and ending at the pad's middle, run anticlockwise
	// (east, north, west, south). Arc marks: 100 the first corner, 139 the east side, 209 the second corner, 248 the
	// north side, 448 the third corner, 487 the west side, 557 the last corner, 597 the south side, 697 the end.
	const float R = 25.f;
	auto Corner = [&Spec, R](const FVector2D& Centre, float FromDeg)
	{
		for (int32 K = 1; K <= 6; ++K)
		{
			const float A = FMath::DegreesToRadians(FromDeg + 15.f * K);
			Spec.RouteM.Add(Centre + FVector2D(FMath::Cos(A), FMath::Sin(A)) * R);
		}
	};
	Spec.RouteM.Add(FVector2D(0.f, 0.f));
	Spec.RouteM.Add(FVector2D(100.f, 0.f));
	Corner(FVector2D(100.f, 25.f), -90.f);
	Spec.RouteM.Add(FVector2D(125.f, 95.f));
	Corner(FVector2D(100.f, 95.f), 0.f);
	Spec.RouteM.Add(FVector2D(-100.f, 120.f));
	Corner(FVector2D(-100.f, 95.f), 90.f);
	Spec.RouteM.Add(FVector2D(-125.f, 25.f));
	Corner(FVector2D(-100.f, 25.f), 180.f);
	Spec.RouteM.Add(FVector2D(0.f, 0.f));
	auto ArcOf = [&Spec](float X, float Y) { return NearestOnPolyline(Spec.RouteM, X, Y).ArcM; };

	auto Section = [&Spec](float Start, float End, EGTRouteSectionKind Kind, float Depth = 0.6f) -> FGTRouteSection&
	{
		FGTRouteSection S;
		S.StartM = Start;
		S.EndM = End;
		S.Kind = Kind;
		S.DepthM = Depth;
		return Spec.Sections.Add_GetRef(S);
	};
	// Ford A: 30 m across the stream at x = 70, 0.6 m deep, the R1 rocks in it.
	const float FordAMid = ArcOf(70.f, 0.f);
	Section(FordAMid - 15.f, FordAMid + 15.f, EGTRouteSectionKind::Ford, 0.6f);
	// Ford B: 36 m across the deeper stream at y = 45 on the east side, 1.4 m (the car floats and floods), no rocks.
	const float FordBMid = ArcOf(125.f, 45.f);
	Section(FordBMid - 18.f, FordBMid + 18.f, EGTRouteSectionKind::Ford, 1.4f).FordRockCountOverride = 0;
	// The bog: 60 m, most of it on the north side's first straight.
	const float BogMid = ArcOf(82.f, 120.f);
	Section(BogMid - 30.f, BogMid + 30.f, EGTRouteSectionKind::Mud);
	// No shallow-mud station: BogCoreFraction is the spec's, not a section's, so a second Mud section would have a bog
	// core too.
	// The rally stretch: 120 m, a crest and a compression on the straight, then the third corner banked.
	const float RallyStart = ArcOf(-8.f, 120.f);
	FGTRouteSection& Rally = Section(RallyStart, RallyStart + 120.f, EGTRouteSectionKind::Rally);
	FGTProfileBump Crest;
	Crest.ArcM = RallyStart + 24.f;
	Crest.HeightM = 0.9f;
	Crest.LengthM = 24.f;
	Rally.Bumps.Add(Crest);
	FGTProfileBump Compression;
	Compression.ArcM = RallyStart + 64.f;
	Compression.HeightM = -0.5f;
	Compression.LengthM = 18.f;
	Rally.Bumps.Add(Compression);
	// The track: 80 m down the west side, stones, water bars and the rut pair.
	const float TrackStart = RallyStart + 124.f;
	Section(TrackStart, TrackStart + 80.f, EGTRouteSectionKind::Track);

	auto Feature = [&Spec](EGTTerrainFeatureKind Kind, FVector2D Start, FVector2D End, float Radius, float Height)
	{
		FGTTerrainFeature F;
		F.Kind = Kind;
		F.StartM = Start;
		F.EndM = End;
		F.RadiusM = Radius;
		F.HeightM = Height;
		Spec.Features.Add(F);
	};
	Feature(EGTTerrainFeatureKind::Channel, FVector2D(70.f, -30.f), FVector2D(70.f, 20.f), 30.f, 2.0f);    // Ford A's stream: broad, so the 0.6 m of water reaches 12 m either side of the middle and the rocks have somewhere to stand
	Feature(EGTTerrainFeatureKind::Channel, FVector2D(100.f, 45.f), FVector2D(160.f, 45.f), 20.f, 3.4f);   // Ford B's
	Spec.OffRoadLayer = 4;
	Spec.MudChannelDepthM = 1.5f;

	// The planes, set on the road's own profile so each meets the road it leaves.
	const FGTRouteProfile Profile = BuildRouteProfile(Spec);
	auto Plane = [&Spec](FVector2D Start, float Yaw, float Length, float Half, float BaseZ, float Grade, float Cross, float Blend, int32 Layer)
	{
		FGTTerrainPlane P;
		P.StartM = Start;
		P.YawDegrees = Yaw;
		P.LengthM = Length;
		P.HalfWidthM = Half;
		P.BaseZM = BaseZ;
		P.GradePercent = Grade;
		P.CrossSlopeDegrees = Cross;
		P.BlendM = Blend;
		P.Layer = Layer;
		Spec.Planes.Add(P);
	};
	// The skid pan: 60 x 60 m of flat tarmac round the start.
	const float PadZ = Profile.HeightAt(0.f);
	Plane(FVector2D(-30.f, 0.f), 0.f, 60.f, 30.f, PadZ, 0.f, 0.f, 8.f, 0);
	// The climbs: three 30 m ramps south off the south side at 15, 25 and 35 %, 30 m apart, each with an 18 x 14 m flat top.
	const float RampX[3] = { -110.f, -80.f, -50.f };
	const float RampGrade[3] = { 15.f, 25.f, 35.f };
	for (int32 K = 0; K < 3; ++K)
	{
		const FVector2D Foot(RampX[K], -8.f);
		const float FootZ = Profile.HeightAt(NearestOnPolyline(Spec.RouteM, Foot.X, Foot.Y).ArcM);
		Plane(Foot, -90.f, 30.f, 4.f, FootZ, RampGrade[K], 0.f, 6.f, 1);
		Plane(FVector2D(RampX[K], -38.f), -90.f, 18.f, 7.f, FootZ + 30.f * RampGrade[K] / 100.f, 0.f, 0.f, 6.f, 1);
	}
	// The side slope: a 40 m traverse across 18 degrees south of the pad, the low side toward it.
	Plane(FVector2D(-20.f, -58.f), 0.f, 40.f, 8.f, BaseHeightM(Spec, 0.f, -58.f), 0.f, -18.f, 6.f, 1);

	// The stations GTGoto knows: 10 m before each.
	auto OnRoute = [&Spec](const TCHAR* Name, float StartArc, const TCHAR* Note)
	{
		FGTTerrainStation S;
		S.Name = FName(Name);
		S.ArcM = FMath::Max(0.f, StartArc - 10.f);
		const FVector2D P = PointOnPolyline(Spec.RouteM, S.ArcM, S.YawDegrees);
		S.PointM = P;
		S.StartAheadM = StartArc - S.ArcM;
		S.Note = Note;
		Spec.Stations.Add(S);
	};
	auto OffRoute = [&Spec](const TCHAR* Name, FVector2D Point, float Yaw, float Grade, float Cross, const TCHAR* Note)
	{
		FGTTerrainStation S;
		S.Name = FName(Name);
		S.PointM = Point;
		S.YawDegrees = Yaw;
		S.StartAheadM = 10.f;
		S.GradePercent = Grade;
		S.CrossSlopeDegrees = Cross;
		S.Note = Note;
		Spec.Stations.Add(S);
	};
	FGTTerrainStation Pad;
	Pad.Name = FName(TEXT("pad"));
	Pad.ArcM = 0.f;
	Pad.StartAheadM = 0.f;
	Pad.Note = TEXT("skid pan, 60 x 60 m tarmac");
	Spec.Stations.Add(Pad);
	OnRoute(TEXT("forda"), Spec.Sections[0].StartM, TEXT("ford A, 0.6 m, rocks"));
	OnRoute(TEXT("fordb"), Spec.Sections[1].StartM, TEXT("ford B, 1.4 m (floats), posts both banks"));
	OnRoute(TEXT("bog"), Spec.Sections[2].StartM, TEXT("bog, 60 m, posts both ends"));
	OnRoute(TEXT("rally"), Spec.Sections[3].StartM, TEXT("rally, 120 m, crest, compression, banked bend"));
	OnRoute(TEXT("track"), Spec.Sections[4].StartM, TEXT("track, 80 m, stones, water bars, ruts"));
	OffRoute(TEXT("climbs"), FVector2D(RampX[0], 2.f), -90.f, RampGrade[0], 0.f, TEXT("ramp 15 %, 30 m"));
	OffRoute(TEXT("climbs25"), FVector2D(RampX[1], 2.f), -90.f, RampGrade[1], 0.f, TEXT("ramp 25 %, 30 m"));
	OffRoute(TEXT("climbs35"), FVector2D(RampX[2], 2.f), -90.f, RampGrade[2], 0.f, TEXT("ramp 35 %, 30 m"));
	OffRoute(TEXT("slope"), FVector2D(-30.f, -58.f), 0.f, 0.f, 18.f, TEXT("side slope, 40 m across 18 degrees"));
	return Spec;
}

// ---- Ground relief GR1 (docs/GROUND_RELIEF_PLAN.md): the hummock field and the grass placement's variation ----------------
namespace
{
	/** A stable hash of a hummock cell, a mound in it and a salt, with the field's seed. */
	uint32 HummockHash(int32 X, int32 Y, int32 Salt, int32 Seed)
	{
		uint32 H = static_cast<uint32>(X) * 0x8DA6B343u ^ static_cast<uint32>(Y) * 0xD8163841u ^ static_cast<uint32>(Salt) * 0xCB1AB31Fu
			^ (static_cast<uint32>(Seed) + 0x632BE5ABu) * 0x9E3779B9u;
		H ^= H >> 15;
		H *= 0x2C1B3C6Du;
		H ^= H >> 12;
		H *= 0x297A2D39u;
		H ^= H >> 15;
		return H;
	}

	float HummockRand(int32 X, int32 Y, int32 Mound, int32 Salt, int32 Seed)
	{
		return static_cast<float>(HummockHash(X, Y, Mound * 37 + Salt, Seed) & 0xFFFFFFu) / 16777216.f;
	}

	/** The cell the mounds are drawn per, m: at least the widest mound's reach, so a point needs only its cell and the eight round it. */
	float HummockCellM(const FGTHummockField& F)
	{
		return FMath::Max(4.f, FMath::Max(F.RadiusMinM, F.RadiusMaxM) * (1.f + FMath::Clamp(F.RimWarp, 0.f, 0.9f)) + 0.05f);
	}

	/** The cluster noise, 0..1: hashed lattice values at ClusterWavelengthM, smoothstep-blended (mean 0.5). */
	float HummockCluster(const FGTHummockField& F, float XM, float YM)
	{
		const float W = FMath::Max(1.f, F.ClusterWavelengthM);
		const float GX = XM / W;
		const float GY = YM / W;
		const int32 X0 = FMath::FloorToInt(GX);
		const int32 Y0 = FMath::FloorToInt(GY);
		const float TX = FMath::SmoothStep(0.f, 1.f, GX - X0);
		const float TY = FMath::SmoothStep(0.f, 1.f, GY - Y0);
		auto V = [&F](int32 X, int32 Y) { return HummockRand(X, Y, 0, 29, F.Seed ^ 0x5BD1E995); };
		return FMath::Lerp(FMath::Lerp(V(X0, Y0), V(X0 + 1, Y0), TX), FMath::Lerp(V(X0, Y0 + 1), V(X0 + 1, Y0 + 1), TX), TY);
	}

	/** One mound, drawn from its cell's hashes. */
	struct FMound
	{
		FVector2D C = FVector2D::ZeroVector;
		FVector2D Crest = FVector2D::ZeroVector;   // the crest's offset from C
		float R = 1.f;
		float H = 0.f;
		int32 K[3] = { 2, 4, 8 };
		float Phase[3] = { 0.f, 0.f, 0.f };
	};

	/** The mounds of one cell (a Poisson count from the cluster noise at the cell's centre, renormalised by its mean 0.5). */
	int32 HummockCellMounds(const FGTHummockField& F, int32 CX, int32 CY, FMound* Out, int32 MaxOut)
	{
		const float Cell = HummockCellM(F);
		const FVector2D Centre((CX + 0.5f) * Cell, (CY + 0.5f) * Cell);
		const float Lo = FMath::Max(0.f, F.ClusterMin);
		const float Hi = FMath::Max(Lo, F.ClusterMax);
		const float Mean = FMath::Max(1.e-3f, FMath::Lerp(Lo, Hi, 0.5f));
		const float Multiplier = FMath::Lerp(Lo, Hi, HummockCluster(F, Centre.X, Centre.Y)) / Mean;
		const float Lambda = FMath::Max(0.f, F.Density) * 0.01f * Cell * Cell * Multiplier;
		// The count by inversion: the first k whose cumulative Poisson probability passes a hashed uniform.
		const float U = HummockRand(CX, CY, 0, 1, F.Seed);
		float P = FMath::Exp(-Lambda);
		float Cumulative = P;
		int32 Count = 0;
		while (U > Cumulative && Count < MaxOut)
		{
			++Count;
			P *= Lambda / Count;
			Cumulative += P;
		}
		const float RMin = FMath::Max(0.1f, FMath::Min(F.RadiusMinM, F.RadiusMaxM));
		const float RMax = FMath::Max(RMin, FMath::Max(F.RadiusMinM, F.RadiusMaxM));
		const float Alpha = FMath::Max(0.1f, F.RadiusPower);
		const float Tail = 1.f - FMath::Pow(RMin / RMax, Alpha);
		const float HLo = FMath::Max(0.f, FMath::Min(F.HeightMinM, F.HeightMaxM));
		const float HHi = FMath::Max(HLo, FMath::Max(F.HeightMinM, F.HeightMaxM));
		for (int32 M = 0; M < Count; ++M)
		{
			FMound& Mound = Out[M];
			const int32 Id = M + 1;
			Mound.C = FVector2D((CX + HummockRand(CX, CY, Id, 2, F.Seed)) * Cell, (CY + HummockRand(CX, CY, Id, 3, F.Seed)) * Cell);
			// A truncated power law between RMin and RMax: most small.
			Mound.R = RMin / FMath::Pow(1.f - HummockRand(CX, CY, Id, 4, F.Seed) * Tail, 1.f / Alpha);
			const float T = RMax > RMin ? (Mound.R - RMin) / (RMax - RMin) : 0.f;
			Mound.H = FMath::Clamp(FMath::Lerp(HLo, HHi, T) * (0.8f + 0.4f * HummockRand(CX, CY, Id, 5, F.Seed)), HLo, HHi);
			const float CrestAngle = 2.f * PI * HummockRand(CX, CY, Id, 6, F.Seed);
			const float CrestShare = FMath::Clamp(F.CrestOffset, 0.f, 0.8f) * HummockRand(CX, CY, Id, 7, F.Seed);
			Mound.Crest = FVector2D(FMath::Cos(CrestAngle), FMath::Sin(CrestAngle)) * CrestShare * Mound.R;
			// The steep side's cap (GR1's 35-degree gate): the dome's radial flank, 1.54 h over the crest's shortest reach to the rim
			// (the rim pulled in by the whole warp, less the crest's offset), kept at most tan 30 deg; it bites only where the height's
			// jitter and a big crest offset meet on one mound.
			const float Shortest = FMath::Max(0.05f, Mound.R * (1.f - FMath::Clamp(F.RimWarp, 0.f, 0.9f)) - CrestShare * Mound.R);
			Mound.H = FMath::Min(Mound.H, 0.5774f * Shortest / 1.5396f);
			Mound.K[0] = 2 + (HummockRand(CX, CY, Id, 8, F.Seed) < 0.5f ? 0 : 1);
			Mound.K[1] = 2 * Mound.K[0] + (HummockRand(CX, CY, Id, 9, F.Seed) < 0.5f ? 0 : 1);
			Mound.K[2] = 2 * Mound.K[1] + (HummockRand(CX, CY, Id, 10, F.Seed) < 0.5f ? 0 : 1);
			for (int32 Harmonic = 0; Harmonic < 3; ++Harmonic)
			{
				Mound.Phase[Harmonic] = 2.f * PI * HummockRand(CX, CY, Id, 11 + Harmonic, F.Seed);
			}
		}
		return Count;
	}

	/** One mound's height at a point: the soft dome (1 - u^2)^2, u the distance from the crest over the ray's reach to the warped rim. */
	float MoundHeightAt(const FGTHummockField& F, const FMound& Mound, const FVector2D& P)
	{
		const float Warp = FMath::Clamp(F.RimWarp, 0.f, 0.9f);
		const FVector2D D = P - Mound.C;
		const float Reach = Mound.R * (1.f + Warp);
		if (D.SizeSquared() >= Reach * Reach)
		{
			return 0.f;
		}
		const FVector2D Q = D - Mound.Crest;
		const float L = static_cast<float>(Q.Size());
		if (L < 1.e-4f)
		{
			return Mound.H;
		}
		const FVector2D E = Q / L;
		const float Theta = static_cast<float>(FMath::Atan2(E.Y, E.X));
		const float W = (FMath::Sin(Mound.K[0] * Theta + Mound.Phase[0]) + 0.5f * FMath::Sin(Mound.K[1] * Theta + Mound.Phase[1])
			+ 0.25f * FMath::Sin(Mound.K[2] * Theta + Mound.Phase[2])) / 1.75f;
		const float Rim = Mound.R * (1.f + Warp * W);
		// The ray from the crest along E meets the rim circle (radius Rim round C) at T: |Crest + T E| = Rim.
		const float OE = static_cast<float>(FVector2D::DotProduct(Mound.Crest, E));
		const float T = -OE + FMath::Sqrt(FMath::Max(0.f, OE * OE - static_cast<float>(Mound.Crest.SizeSquared()) + Rim * Rim));
		if (T <= 1.e-4f || L >= T)
		{
			return 0.f;
		}
		const float U = L / T;
		const float V = 1.f - U * U;
		return Mound.H * V * V;
	}

	constexpr int32 MaxMoundsPerCell = 16;
}

float GTTerrain::HummockHeightM(const FGTTerrainSpec& Spec, float XM, float YM, float* OutPeakM)
{
	if (OutPeakM)
	{
		*OutPeakM = 0.f;
	}
	const FGTHummockField& F = Spec.Hummocks;
	if (F.Density <= 0.f)
	{
		return 0.f;
	}
	const float Cell = HummockCellM(F);
	const int32 CX = FMath::FloorToInt(XM / Cell);
	const int32 CY = FMath::FloorToInt(YM / Cell);
	const FVector2D P(XM, YM);
	FMound Mounds[MaxMoundsPerCell];
	float SumSq = 0.f;
	float Peak = 0.f;
	for (int32 DY = -1; DY <= 1; ++DY)
	{
		for (int32 DX = -1; DX <= 1; ++DX)
		{
			const int32 Count = HummockCellMounds(F, CX + DX, CY + DY, Mounds, MaxMoundsPerCell);
			for (int32 M = 0; M < Count; ++M)
			{
				const float H = MoundHeightAt(F, Mounds[M], P);
				if (H > 0.f)
				{
					SumSq += H * H;
					Peak = FMath::Max(Peak, Mounds[M].H);
				}
			}
		}
	}
	if (OutPeakM)
	{
		*OutPeakM = Peak;
	}
	return FMath::Sqrt(SumSq);
}

void GTTerrain::HummockCentres(const FGTTerrainSpec& Spec, const FBox2D& AreaM, TArray<FVector4f>& OutMounds)
{
	OutMounds.Reset();
	const FGTHummockField& F = Spec.Hummocks;
	if (F.Density <= 0.f || !AreaM.bIsValid)
	{
		return;
	}
	const float Cell = HummockCellM(F);
	FMound Mounds[MaxMoundsPerCell];
	for (int32 CY = FMath::FloorToInt32(AreaM.Min.Y / Cell); CY <= FMath::FloorToInt32(AreaM.Max.Y / Cell); ++CY)
	{
		for (int32 CX = FMath::FloorToInt32(AreaM.Min.X / Cell); CX <= FMath::FloorToInt32(AreaM.Max.X / Cell); ++CX)
		{
			const int32 Count = HummockCellMounds(F, CX, CY, Mounds, MaxMoundsPerCell);
			for (int32 M = 0; M < Count; ++M)
			{
				if (AreaM.IsInside(Mounds[M].C))
				{
					OutMounds.Add(FVector4f(static_cast<float>(Mounds[M].C.X), static_cast<float>(Mounds[M].C.Y), Mounds[M].R, Mounds[M].H));
				}
			}
		}
	}
}

namespace
{
	/** A Perlin noise value, about uniform over 0..1 (Sigma its measured spread, BiomePerlinSigma for one octave). */
	float GrassUniform(float N, float Sigma)
	{
		return FMath::Clamp(0.5f * (1.f + static_cast<float>(std::erf(N / (Sigma * 1.41421356f)))), 0.f, 1.f);
	}

	float GrassNoise(const FGTGrassVariation& G, float XM, float YM, float WavelengthM, float OX, float OY)
	{
		const FVector2D Offset(OX + G.Seed * 113.17f, OY + G.Seed * 71.31f);
		return FMath::PerlinNoise2D(FVector2D(XM, YM) / FMath::Max(0.05f, WavelengthM) + Offset);
	}

	float GrassHash01(int32 A, int32 B, int32 Salt)
	{
		return static_cast<float>(HummockHash(A, B, Salt, 0x47524153) & 0xFFFFFFu) / 16777216.f;
	}
}

void GTTerrain::VaryGrass(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, const TArray<FTransform>& In, bool bTussock,
	TArray<FTransform>& Out, FGTGrassStats* OutStats)
{
	const FGTGrassVariation& G = Spec.Grass;
	FGTGrassStats Stats;
	Stats.In = In.Num();
	if (!G.IsActive())
	{
		Out = In;
		Stats.Out = Out.Num();
		if (OutStats)
		{
			*OutStats = Stats;
		}
		return;
	}
	Out.Reset();
	Out.Reserve(In.Num() + In.Num() / 4);
	bool bFirstScale = true;
	const float MaxTilt = FMath::Max(0.f, G.TiltDegrees);
	const float Jitter = FMath::Clamp(G.HeightJitter, 0.f, 0.95f);
	const float ComboSigma = BiomePerlinSigma * FMath::Sqrt(0.7f * 0.7f + 0.3f * 0.3f);
	const float Follow = FMath::Clamp(G.SlopeFollow, 0.f, 1.f);
	// One instance's height scale and lean at a point (its rotation and scale changed in place).
	auto Shape = [&](FTransform& T, float XM, float YM)
	{
		float Scale = 1.f;
		if (Jitter > 0.f)
		{
			const float N = 0.7f * GrassNoise(G, XM, YM, G.HeightWavelengthM, 3.1f, 17.9f) + 0.3f * GrassNoise(G, XM, YM, G.HeightFineWavelengthM, 29.3f, 5.3f);
			Scale = 1.f + Jitter * (2.f * GrassUniform(N, ComboSigma) - 1.f);
			const FVector S = T.GetScale3D();
			const float Wide = FMath::Sqrt(Scale);   // the height x Scale, the width x its root (a short tussock is not a flat one)
			T.SetScale3D(FVector(S.X * Wide, S.Y * Wide, S.Z * Scale));
		}
		if (bFirstScale)
		{
			Stats.ScaleMin = Stats.ScaleMax = Scale;
			bFirstScale = false;
		}
		Stats.ScaleMin = FMath::Min(Stats.ScaleMin, Scale);
		Stats.ScaleMax = FMath::Max(Stats.ScaleMax, Scale);
		if (MaxTilt > 0.f)
		{
			// The lean: SlopeFollow of the ground's own tilt (central differences over 0.5 m) plus a noise lean, clamped to TiltDegrees.
			const float GX = (HeightM(Spec, Profiles, XM + 0.25f, YM) - HeightM(Spec, Profiles, XM - 0.25f, YM)) / 0.5f;
			const float GY = (HeightM(Spec, Profiles, XM, YM + 0.25f) - HeightM(Spec, Profiles, XM, YM - 0.25f)) / 0.5f;
			const float NX = 2.f * GrassUniform(GrassNoise(G, XM, YM, 1.5f, 61.7f, 13.3f), BiomePerlinSigma) - 1.f;
			const float NY = 2.f * GrassUniform(GrassNoise(G, XM, YM, 1.5f, 7.9f, 83.1f), BiomePerlinSigma) - 1.f;
			const float NoiseTan = FMath::Tan(FMath::DegreesToRadians(0.6f * MaxTilt));
			FVector Up(-GX * Follow + NX * NoiseTan, -GY * Follow + NY * NoiseTan, 1.f);
			Up.Normalize();
			const float Angle = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(static_cast<float>(Up.Z), -1.f, 1.f)));
			if (Angle > MaxTilt)
			{
				const FVector2D Flat = FVector2D(Up.X, Up.Y).GetSafeNormal();
				const float Lean = FMath::DegreesToRadians(MaxTilt);
				Up = FVector(Flat.X * FMath::Sin(Lean), Flat.Y * FMath::Sin(Lean), FMath::Cos(Lean));
			}
			Stats.TiltMaxDeg = FMath::Max(Stats.TiltMaxDeg, FMath::Min(Angle, MaxTilt));
			T.SetRotation(FQuat::FindBetweenNormals(FVector::UpVector, Up) * T.GetRotation());
		}
	};
	for (int32 Index = 0; Index < In.Num(); ++Index)
	{
		FTransform T = In[Index];
		const float XM = static_cast<float>(T.GetLocation().X) / 100.f;
		const float YM = static_cast<float>(T.GetLocation().Y) / 100.f;
		if (G.BareShareMax > 0.f)
		{
			const float Share = FMath::Lerp(FMath::Max(0.f, G.BareShareMin), FMath::Max(G.BareShareMin, G.BareShareMax),
				GrassUniform(GrassNoise(G, XM, YM, G.BareShareWavelengthM, 41.3f, 97.1f), BiomePerlinSigma));
			if (GrassUniform(GrassNoise(G, XM, YM, G.BareWavelengthM, 11.9f, 37.7f), BiomePerlinSigma) < Share)
			{
				++Stats.Bare;
				continue;
			}
		}
		Shape(T, XM, YM);
		Out.Add(T);
		if (bTussock && G.CrestTussockWeight > 1.f)
		{
			float Peak = 0.f;
			const float H = HummockAtM(Spec, Profiles, XM, YM, &Peak);
			if (Peak > 0.f && H >= 0.6f * Peak)
			{
				// On a crest: (weight - 1) companions, the fraction by a hash, each 0.3-0.7 m off on its own yaw.
				const int32 QX = FMath::RoundToInt(XM * 20.f);
				const int32 QY = FMath::RoundToInt(YM * 20.f);
				const float Extra = G.CrestTussockWeight - 1.f;
				const int32 Count = FMath::FloorToInt(Extra) + (GrassHash01(QX, QY, 1) < FMath::Frac(Extra) ? 1 : 0);
				for (int32 C = 0; C < Count; ++C)
				{
					const float A = 2.f * PI * GrassHash01(QX, QY, 2 + 3 * C);
					const float Dist = FMath::Lerp(0.3f, 0.7f, GrassHash01(QX, QY, 3 + 3 * C));
					const float CX = XM + Dist * FMath::Cos(A);
					const float CY = YM + Dist * FMath::Sin(A);
					FTransform Companion = In[Index];
					Companion.SetLocation(FVector(CX * 100.f, CY * 100.f, HeightM(Spec, Profiles, CX, CY) * 100.f));
					Companion.SetRotation(FQuat(FVector::UpVector, 2.f * PI * GrassHash01(QX, QY, 4 + 3 * C)) * In[Index].GetRotation());
					Shape(Companion, CX, CY);
					Out.Add(Companion);
					++Stats.CrestExtra;
				}
			}
		}
	}
	Stats.Out = Out.Num();
	if (OutStats)
	{
		*OutStats = Stats;
	}
}
