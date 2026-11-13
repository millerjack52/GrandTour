#pragma once
#include "CoreMinimal.h"

namespace GTWaterDrag
{
// Dimensionless load fraction, in world XY. A current can accelerate a stopped
// wheel or a slower downstream car; dissipate velocity relative to the WATER.
inline FVector2D FlowingWheelFraction(FVector2D RelativeCmPerS, float DepthM, float DragPerMetre, float Cap)
{
	const double Speed=RelativeCmPerS.Size();
	if(Speed<1.e-6 || DepthM<=0 || DragPerMetre<=0 || Cap<=0) return FVector2D::ZeroVector;
	const double Magnitude=FMath::Min(double(Cap),DragPerMetre*DepthM*FMath::Square(Speed/1000.));
	return RelativeCmPerS*(-Magnitude/Speed);
}
}
