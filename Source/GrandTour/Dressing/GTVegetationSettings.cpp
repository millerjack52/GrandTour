#include "Dressing/GTVegetationSettings.h"

UGTVegetationSettings::UGTVegetationSettings()
{
	// docs/LEG_DRESSING_PLAN.md LD5 table as revised by LD5 v2: class, theta max, theta break, v break, t hold, K, cap, m_debris.
	Brush.MaxTiltDeg = 75.f;
	Brush.BreakTiltDeg = 0.f;      // never
	Brush.BreakSpeedMs = 0.f;
	Brush.SustainHoldS = 0.f;
	Brush.StiffnessN = 1500.f;
	Brush.CapG = 0.15f;
	Brush.DebrisMassKg = 0.f;      // none

	Sapling.MaxTiltDeg = 70.f;
	Sapling.BreakTiltDeg = 40.f;
	Sapling.BreakSpeedMs = 2.5f;
	Sapling.SustainHoldS = 0.5f;
	Sapling.StiffnessN = 2500.f;   // v2 (v1 5000)
	Sapling.CapG = 0.20f;
	Sapling.DebrisMassKg = 30.f;

	Young.MaxTiltDeg = 45.f;
	Young.BreakTiltDeg = 35.f;
	Young.BreakSpeedMs = 7.f;      // 25 km/h
	Young.SustainHoldS = 2.f;
	Young.StiffnessN = 16000.f;
	Young.CapG = 0.35f;
	Young.DebrisMassKg = 150.f;
}

const FGTVegClassDials& UGTVegetationSettings::ForClass(EGTVegClass Class) const
{
	switch (Class)
	{
	case EGTVegClass::Sapling: return Sapling;
	case EGTVegClass::Young: return Young;
	default: return Brush;
	}
}
