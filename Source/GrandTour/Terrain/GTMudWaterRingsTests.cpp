// Mud and water MW1 item 3d (docs/MUD_WATER_SURFACE_PLAN.md): the water rings' timing, CPU only - the wheels' rate by speed,
// the accumulator, the footstep cadence and the switches' defaults.
#include "Terrain/GTMudWaterSubsystem.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudWaterRingsTest, "GrandTour.Mud.WaterRings",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTMudWaterRingsTest::RunTest(const FString& Parameters)
{
	using S = UGTMudWaterSubsystem;
	const float Dt = 1.f / 60.f;
	// The wheels' rate: none creeping, 1 at RingMinSpeedCm, 6 from RingFullSpeedCm; about 10 km/h between.
	const float Slow = S::WheelRingRate(20.f), AtMin = S::WheelRingRate(S::RingMinSpeedCm), Ten = S::WheelRingRate(277.8f),
		Full = S::WheelRingRate(S::RingFullSpeedCm), Fast = S::WheelRingRate(2000.f);
	TestEqual(TEXT("WaterRings: no rings under the minimum speed"), Slow, 0.f);
	TestTrue(TEXT("WaterRings: 1 a second at the minimum speed"), FMath::IsNearlyEqual(AtMin, 1.f, 1e-4f));
	TestTrue(TEXT("WaterRings: 6 a second at full speed and over"), FMath::IsNearlyEqual(Full, 6.f, 1e-4f) && FMath::IsNearlyEqual(Fast, 6.f, 1e-4f));
	TestTrue(TEXT("WaterRings: between at 10 km/h"), Ten > 1.f && Ten < 6.f);
	// The accumulator: 1 s of fixed steps at each rate gives that many whole rings (the fraction carried).
	int32 Counts[3] = { 0, 0, 0 };
	const float Rates[3] = { AtMin, Ten, Full };
	for (int32 K = 0; K < 3; ++K)
	{
		float Carry = 0.f;
		int32 MaxPerFrame = 0;
		for (int32 F = 0; F < 600; ++F)
		{
			const int32 N = S::RingsThisFrame(Carry, Rates[K], Dt);
			Counts[K] += N;
			MaxPerFrame = FMath::Max(MaxPerFrame, N);
		}
		TestTrue(FString::Printf(TEXT("WaterRings: 10 s at %.2f/s gives %d rings"), Rates[K], Counts[K]), FMath::Abs(Counts[K] - FMath::RoundToInt(Rates[K] * 10.f)) <= 1);
		TestTrue(TEXT("WaterRings: at most one ring a frame at 60 fps"), MaxPerFrame <= 1);
	}
	// The footsteps: 2 s walking in water - one as the foot meets it, then one every 0.45 s; none out of it; primed again after.
	float Clock = S::StepSeconds;
	int32 Steps = 0, FirstAt = -1;
	for (int32 F = 0; F < 120; ++F)
	{
		const int32 N = S::StepsThisFrame(Clock, true, Dt, S::StepSeconds);
		if (N > 0 && FirstAt < 0)
		{
			FirstAt = F;
		}
		Steps += N;
	}
	int32 Dry = 0;
	for (int32 F = 0; F < 60; ++F)
	{
		Dry += S::StepsThisFrame(Clock, false, Dt, S::StepSeconds);
	}
	const int32 Again = S::StepsThisFrame(Clock, true, Dt, S::StepSeconds);
	const int32 Expected = 1 + FMath::FloorToInt((120.f * Dt - Dt) / S::StepSeconds);
	TestTrue(FString::Printf(TEXT("WaterRings: footsteps over 2 s in water %d (expected %d), the first on frame %d"), Steps, Expected, FirstAt), FMath::Abs(Steps - Expected) <= 1 && FirstAt == 0);
	TestEqual(TEXT("WaterRings: no footstep rings out of the water"), Dry, 0);
	TestEqual(TEXT("WaterRings: the first step back in the water rings at once"), Again, 1);
	TestTrue(TEXT("WaterRings: the switches default on"), S::IsDeformDetailEnabled() && S::IsWaterMotionEnabled() && S::IsWaterRingsEnabled());
	AddInfo(FString::Printf(TEXT("WaterRings: wheel rates %.2f / %.2f / %.2f / %.2f rings/s at 0.2 / 0.3 / 2.8 / 7 m/s; 10 s gives %d / %d / %d; footsteps over 2 s %d (first on frame %d), out of the water %d, back in %d"),
		Slow, AtMin, Ten, Full, Counts[0], Counts[1], Counts[2], Steps, FirstAt, Dry, Again));
	return true;
}
#endif
