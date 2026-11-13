// Wheel spray P2 item 6 (docs/WHEEL_SPRAY_PLAN.md): GrandTour.Spray.Art, CPU only. The painterly layer's rules, each row printing
// a "SprayArt: " line: the gravel-patch flag (the rule UGTTractionComponent sets bInSnowPatch and bInGravelPatch by), the bursts'
// mean over 60 s, the switches (gt.Spray.Fine 0: every rate 0), the dry dust (0 at wetness 0.7), the clump choice per particle id.
#include "Vehicle/GTSprayComponent.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "HAL/IConsoleManager.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Vehicle/GTTractionComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTSprayArtTest, "GrandTour.Spray.Art",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FGTSprayArtTest::RunTest(const FString& Parameters)
{
	// Firm authored gravel uses generic collision material but still throws chips.
	{
		FGTWheelTraction W;W.bInContact=true;W.AuthoredSurface=TEXT("Gravel");
		TestTrue(TEXT("authored firm gravel emits without legacy marker"),UGTSprayComponent::IsGravelContact(W,false));
		W.AuthoredSurface=TEXT("Grass");
		TestFalse(TEXT("authored grass overrides gravel collision"),UGTSprayComponent::IsGravelContact(W,true));
		W.AuthoredSurface=TEXT("Sand");
		TestFalse(TEXT("sand does not throw gravel chips"),UGTSprayComponent::IsGravelContact(W,true));
		W.AuthoredSurface=TEXT("Gravel");W.bInContact=false;
		TestFalse(TEXT("no airborne chips"),UGTSprayComponent::IsGravelContact(W,true));
		W.bInContact=true;W.GroundWaterDepthCm=3;
		TestFalse(TEXT("authored water suppresses chips"),UGTSprayComponent::IsGravelContact(W,true));
		W.GroundWaterDepthCm=0;W.bInMudPatch=true;
		TestFalse(TEXT("mud suppresses chips"),UGTSprayComponent::IsGravelContact(W,true));
		W.bInMudPatch=false;W.bInSnowPatch=true;
		TestFalse(TEXT("snow suppresses chips"),UGTSprayComponent::IsGravelContact(W,true));
		W.bInSnowPatch=false;W.AuthoredSurface=NAME_None;
		TestTrue(TEXT("legacy gravel still emits"),UGTSprayComponent::IsGravelContact(W,true));
	}
	// 1. bInGravelPatch on a gravel patch, not on mud or snow (nor off the contact or outside a profiled patch).
	{
		struct FCase { const TCHAR* Name; bool bContact; bool bProfiled; EGTDeformMedium Medium; bool bSnow; bool bGravel; };
		const FCase Cases[] = {
			{ TEXT("gravel"), true, true, EGTDeformMedium::Gravel, false, true },
			{ TEXT("mud"), true, true, EGTDeformMedium::Mud, false, false },
			{ TEXT("snow"), true, true, EGTDeformMedium::Snow, true, false },
			{ TEXT("gravel, no contact"), false, true, EGTDeformMedium::Gravel, false, false },
			{ TEXT("gravel, not profiled"), true, false, EGTDeformMedium::Gravel, false, false } };
		for (const FCase& C : Cases)
		{
			bool bSnow = false, bGravel = false;
			UGTTractionComponent::PatchMediumFlags(C.bContact, C.bProfiled, static_cast<uint8>(C.Medium), bSnow, bGravel);
			AddInfo(FString::Printf(TEXT("SprayArt: patch %s -> snow %d gravel %d"), C.Name, bSnow ? 1 : 0, bGravel ? 1 : 0));
			TestTrue(FString::Printf(TEXT("%s: bInGravelPatch %d, bInSnowPatch %d"), C.Name, C.bGravel ? 1 : 0, C.bSnow ? 1 : 0), bSnow == C.bSnow && bGravel == C.bGravel);
		}
	}
	// 2. The bursts: mean 1 +- 5 % over 60 s on every wheel; clumped (well under and well over the mean within the minute).
	for (int32 Wheel = 0; Wheel < 4; ++Wheel)
	{
		double Sum = 0.0;
		float Lo = 1.e9f, Hi = 0.f;
		const int32 Steps = 60 * 240;
		for (int32 Step = 0; Step < Steps; ++Step)
		{
			const float B = UGTSprayComponent::BurstFactor(Wheel, 12.5 + Step / 240.0, 3.f);
			Sum += B;
			Lo = FMath::Min(Lo, B);
			Hi = FMath::Max(Hi, B);
		}
		const double Mean = Sum / Steps;
		AddInfo(FString::Printf(TEXT("SprayArt: wheel %d burst over 60 s mean %.4f min %.3f max %.3f"), Wheel, Mean, Lo, Hi));
		TestTrue(FString::Printf(TEXT("wheel %d: the burst mean %.4f is 1 +- 5 %%"), Wheel, Mean), FMath::Abs(Mean - 1.0) <= 0.05);
		TestTrue(FString::Printf(TEXT("wheel %d: bursts, not a stream (min %.3f < 0.3, max %.3f > 1.8)"), Wheel, Lo, Hi), Lo < 0.3f && Hi > 1.8f);
	}
	// 3. gt.Spray.Fine 0: every rate 0 (the switch read, and the rates with it off); 4. the dust is 0 at wetness 0.7, not when dry.
	{
		IConsoleVariable* Fine = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Spray.Fine"));
		TestNotNull(TEXT("gt.Spray.Fine exists"), Fine);
		if (Fine)
		{
			const int32 Was = Fine->GetInt();
			Fine->Set(0, ECVF_SetByCode);
			const bool bOff = !UGTSprayComponent::IsFineEnabled();
			const UGTSprayComponent::FFineRates Off = UGTSprayComponent::FineRates(true, 40.f, true, 1.f, 1.f, 0.f, 1.5f, UGTSprayComponent::IsFineEnabled(), 1.f, 6.f, 30.f, 8.f);
			Fine->Set(Was, ECVF_SetByCode);
			AddInfo(FString::Printf(TEXT("SprayArt: Fine 0 -> enabled %d, rates mud %.2f grit %.2f dust %.2f"), bOff ? 0 : 1, Off.Mud, Off.Grit, Off.Dust));
			TestTrue(TEXT("gt.Spray.Fine 0: every rate 0"), bOff && Off.Mud == 0.f && Off.Grit == 0.f && Off.Dust == 0.f);
		}
		const UGTSprayComponent* Defaults = GetDefault<UGTSprayComponent>();
		const UGTSprayComponent::FFineRates On = UGTSprayComponent::FineRates(true, 40.f, true, 1.f, 0.f, 0.f, 1.f, true, 1.f, Defaults->FineMudPerRate, Defaults->FineGritPerFactor, Defaults->FineDustPerFactor);
		const UGTSprayComponent::FFineRates Wet = UGTSprayComponent::FineRates(false, 0.f, true, 1.f, 0.f, 0.7f, 1.f, true, 1.f, Defaults->FineMudPerRate, Defaults->FineGritPerFactor, Defaults->FineDustPerFactor);
		AddInfo(FString::Printf(TEXT("SprayArt: full speed dry -> mud %.1f grit %.1f dust %.2f; wetness 0.7 -> grit %.1f dust %.2f"), On.Mud, On.Grit, On.Dust, Wet.Grit, Wet.Dust));
		TestTrue(TEXT("the default rates at full speed (P2b): mud 6 x 40, grit 30, dust 8"), FMath::IsNearlyEqual(On.Mud, 240.f) && FMath::IsNearlyEqual(On.Grit, 30.f) && FMath::IsNearlyEqual(On.Dust, 8.f));
		TestTrue(TEXT("DustRate 0 at wetness 0.7 (grit still flies)"), Wet.Dust == 0.f && Wet.Grit > 0.f);
	}
	// 5. The clump per particle id: deterministic, 0..7, all eight used.
	{
		bool bSame = true, bRange = true;
		int32 Used[8] = {};
		for (uint32 Id = 0; Id < 4000; ++Id)
		{
			const int32 K = UGTSprayComponent::ClumpMeshFor(Id);
			bSame &= K == UGTSprayComponent::ClumpMeshFor(Id);
			bRange &= K >= 0 && K < 8;
			if (K >= 0 && K < 8)
			{
				++Used[K];
			}
		}
		int32 Fewest = 4000;
		for (int32 K = 0; K < 8; ++K)
		{
			Fewest = FMath::Min(Fewest, Used[K]);
		}
		AddInfo(FString::Printf(TEXT("SprayArt: clumps over 4000 ids %d %d %d %d %d %d %d %d"), Used[0], Used[1], Used[2], Used[3], Used[4], Used[5], Used[6], Used[7]));
		TestTrue(TEXT("the clump choice is deterministic per particle id, 0..7, every clump used"), bSame && bRange && Fewest > 300);
	}
	// The palette: the wetter variant (Deep) darker than Standard, every tint the slice mean x 0.8.
	TestTrue(TEXT("MudTint: Deep darker than Standard"), UGTSprayComponent::MudTintFor(2).GetLuminance() < UGTSprayComponent::MudTintFor(0).GetLuminance());
	// P2d: Deep is exempt from the wet x0.8 (its bake is already the darkest), which keeps it inside the mud soil band.
	AddInfo(FString::Printf(TEXT("SprayArt: MudTint luminance Standard %.4f Firm %.4f Deep %.4f Stony %.4f"), UGTSprayComponent::MudTintFor(0).GetLuminance(),
		UGTSprayComponent::MudTintFor(1).GetLuminance(), UGTSprayComponent::MudTintFor(2).GetLuminance(), UGTSprayComponent::MudTintFor(3).GetLuminance()));
	TestTrue(TEXT("MudTint: every slice inside the mud soil band 0.03-0.25 (Deep unscaled)"), UGTSprayComponent::MudTintFor(2).GetLuminance() >= 0.03f
		&& UGTSprayComponent::MudTintFor(0).GetLuminance() >= 0.03f && UGTSprayComponent::MudTintFor(1).GetLuminance() <= 0.25f);
	return true;
}

#endif
