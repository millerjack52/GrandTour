#include "Terrain/GTTerrainSpecAsset.h"

FString UGTTerrainSpecAsset::Describe() const
{
	float LengthM = 0.f;
	for (int32 Index = 0; Index + 1 < Spec.RouteM.Num(); ++Index)
	{
		LengthM += FVector2D::Distance(Spec.RouteM[Index], Spec.RouteM[Index + 1]);
	}
	return FString::Printf(TEXT("%s: %d x %d verts at %.0f cm, route %d points / %.0f m, %d spans, %d landforms, noise %.0f m / %.0f m, slope %.0f m/km, grade %.0f%%"),
		*DisplayName, GTTerrain::VertsPerSide(Spec), GTTerrain::VertsPerSide(Spec), Spec.QuadSizeCm, Spec.RouteM.Num(), LengthM, Spec.Spans.Num(), Spec.Features.Num(),
		Spec.BaseAmplitudeM, Spec.BaseWavelengthM, Spec.SlopeMPerKm, Spec.MaxGradePercent);
}
