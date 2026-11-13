#include "Vehicle/GTSprayComponent.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "HAL/IConsoleManager.h"
#include "Misc/AutomationTest.h"
#include "UObject/StrongObjectPtr.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTSprayUploadTest, "GrandTour.Spray.RenderUploads",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FGTSprayUploadTest::RunTest(const FString& Parameters)
{
	IConsoleVariable* Sparse = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Spray.SparseUpdates"));
	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (!TestNotNull(TEXT("Sparse upload rollback switch"), Sparse) || !TestNotNull(TEXT("ISM fixture mesh"), Sphere))
	{
		return false;
	}
	constexpr int32 Water = static_cast<int32>(EGTSprayKind::Water);
	constexpr int32 Capacity = 16;
	auto MakeSpray = [&]()
	{
		TStrongObjectPtr<UGTSprayComponent> Spray(NewObject<UGTSprayComponent>());
		Spray->PoolPerKind = Capacity;
		Spray->Meshes.SetNum(static_cast<int32>(EGTSprayKind::Count));
		UInstancedStaticMeshComponent* Mesh = NewObject<UInstancedStaticMeshComponent>(Spray.Get());
		Mesh->SetStaticMesh(Sphere);
		Mesh->SetCanEverAffectNavigation(false);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetNumCustomDataFloats(7);
		TArray<FTransform> Instances;
		Instances.Init(FTransform::Identity, Capacity);
		Mesh->AddInstances(Instances, false, false);
		for (int32 I = 0; I < Capacity; ++I)
		{
			Mesh->SetCustomDataValue(I, 0, .25f, false);
			Mesh->SetCustomDataValue(I, 1, .75f, false);
		}
		Spray->Meshes[Water] = Mesh;
		return Spray;
	};
	auto Reference = MakeSpray();
	auto Candidate = MakeSpray();
	const int32 WasSparse = Sparse->GetInt();
	// Reuse, compaction, shrinkage and complete retirement exercise real ISM
	// storage against the retained full upload, not a copy of the range formula.
	const int32 Counts[] = {0, 8, 2, 12, 0, 0, 1, Capacity, 3, 0};
	int32 Frame = 0;
	for (int32 Count : Counts)
	{
		auto& Pool = Candidate->Particles[Water];
		Pool.Reset();
		for (int32 I = 0; I < Count; ++I)
		{
			UGTSprayComponent::FParticle P;
			P.MudShare = (I + Frame) % 3 == 0 ? 0.f : .5f;
			P.MudTint = FLinearColor(.03f * (I + 1), .12f, .08f);
			P.MudTurbidity = .04f * I;
			Pool.Add(P);
		}
		if (Frame == 2 && Pool.Num() > 1)
		{
			Pool.RemoveAtSwap(0);
		}
		Reference->Particles[Water] = Pool;
		Sparse->Set(0, ECVF_SetByCode);
		Reference->PushWaterMud();
		Sparse->Set(1, ECVF_SetByCode);
		Candidate->PushWaterMud();
		const auto& Actual = Candidate->Meshes[Water]->PerInstanceSMCustomData;
		TestTrue(FString::Printf(TEXT("Frame %d: live and retired custom data match full upload"), Frame),
			Actual == Reference->Meshes[Water]->PerInstanceSMCustomData);
		TestEqual(TEXT("Muddy splash telemetry unchanged"), Candidate->MuddySplashCount, Reference->MuddySplashCount);
		for (int32 I = 0; I < Capacity; ++I)
		{
			TestEqual(TEXT("Water opacity channel retained"), Actual[I * 7], .25f);
			TestEqual(TEXT("Water family channel retained"), Actual[I * 7 + 1], .75f);
		}
		++Frame;
	}
	Sparse->Set(WasSparse, ECVF_SetByCode);
	return true;
}
#endif
