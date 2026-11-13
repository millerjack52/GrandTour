// MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5 execution block item 6): GrandTour.Mud.Chunks, -NullRHI (Chaos runs headless).
// The four L_MudVariants patches built as play builds them (UGTMudSubsystem::BuildPatches) over a flat static ground box with its
// top at Z 0 (the test world has no landscape; the chunks' spawn trace lands on the box). Each row prints a "Chunks: " line for
// Art/mud_shape_test.ps1.
#include "Terrain/GTMudPatch.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Terrain/GTMudChunkData.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudChunksTest, "GrandTour.Mud.Chunks",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace
{
	/** The population coefficient of variation (sd / mean); 0 under two values. */
	float ChunkCV(const TArray<float>& Values)
	{
		if (Values.Num() < 2)
		{
			return 0.f;
		}
		double Sum = 0.0;
		for (const float V : Values)
		{
			Sum += V;
		}
		const double Mean = Sum / Values.Num();
		double Sq = 0.0;
		for (const float V : Values)
		{
			Sq += (V - Mean) * (V - Mean);
		}
		return Mean > 0.0 ? static_cast<float>(FMath::Sqrt(Sq / Values.Num()) / Mean) : 0.f;
	}

	/** Each point's distance to its nearest other, cm. */
	TArray<float> ChunkNearest(const TArray<FVector2D>& Points)
	{
		TArray<float> Out;
		for (int32 I = 0; I < Points.Num(); ++I)
		{
			double Best = TNumericLimits<double>::Max();
			for (int32 J = 0; J < Points.Num(); ++J)
			{
				if (I != J)
				{
					Best = FMath::Min(Best, FVector2D::Distance(Points[I], Points[J]));
				}
			}
			if (Points.Num() > 1)
			{
				Out.Add(static_cast<float>(Best));
			}
		}
		return Out;
	}

	/** The field's lump and height volumes, cm^3 (sums over the cells x the cell's area). */
	void ChunkFieldVolumes(const FGTMudField& Field, double& OutLump, double& OutHeight)
	{
		OutLump = 0.0;
		OutHeight = 0.0;
		const double Area = static_cast<double>(Field.CellCm) * Field.CellCm;
		for (const float V : Field.LumpCm)
		{
			OutLump += V * Area;
		}
		for (const float V : Field.HeightCm)
		{
			OutHeight += V * Area;
		}
	}

	/** Art/Export/MudChunks/manifest.json's closed-mesh volumes (cm^3 at its across) and across, by mesh number; empty without it. Each
	 *  "volume_cm3" key in file order (one a chunk; "hull_volume_cm3" is another key), the first "across_cm" the manifest's own. */
	bool ReadChunkManifest(TArray<float>& OutVolume, float& OutAcross)
	{
		OutVolume.Reset();
		OutAcross = 0.f;
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectDir() / TEXT("Art/Export/MudChunks/manifest.json"))))
		{
			return false;
		}
		auto NumberAfter = [&Text](int32 At)
		{
			const int32 Colon = Text.Find(TEXT(":"), ESearchCase::CaseSensitive, ESearchDir::FromStart, At);
			return Colon == INDEX_NONE ? 0.f : FCString::Atof(*Text.Mid(Colon + 1, 32).TrimStart());
		};
		const int32 Across = Text.Find(TEXT("\"across_cm\""));
		OutAcross = Across == INDEX_NONE ? 0.f : NumberAfter(Across);
		for (int32 At = Text.Find(TEXT("\"volume_cm3\"")); At != INDEX_NONE; At = Text.Find(TEXT("\"volume_cm3\""), ESearchCase::CaseSensitive, ESearchDir::FromStart, At + 1))
		{
			OutVolume.Add(NumberAfter(At));
		}
		return OutVolume.Num() > 0;
	}
}

bool FGTMudChunksTest::RunTest(const FString& Parameters)
{
	IConsoleVariable* ChunkSwitch = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Mud.Chunks"));
	IConsoleVariable* ClodSwitch = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Mud.Clods"));
	if (!TestNotNull(TEXT("Chunks: gt.Mud.Chunks exists"), ChunkSwitch))
	{
		return false;
	}
	const int32 ChunksWas = ChunkSwitch->GetInt();
	const int32 ClodsWas = ClodSwitch ? ClodSwitch->GetInt() : 1;
	ChunkSwitch->Set(1, ECVF_SetByConsole);
	if (ClodSwitch)
	{
		ClodSwitch->Set(1, ECVF_SetByConsole);
	}

	struct FRow
	{
		EGTMudVariant Variant;
		const TCHAR* Name;
		float DensityScale;
	};
	// The execution block's multipliers (Standard 1 with no profile), in the strip's order.
	const FRow Rows[4] = { { EGTMudVariant::Firm, TEXT("Firm"), 0.5f }, { EGTMudVariant::Standard, TEXT("Standard"), 1.f },
		{ EGTMudVariant::Deep, TEXT("Deep"), 1.5f }, { EGTMudVariant::Stony, TEXT("Stony"), 1.f } };
	// The strip's own spec (DA_MudVariants), so the patches are L_MudVariants' (their size, their section indices and so their
	// seeds); the Variants test's hand-built spec when the asset is missing.
	FGTTerrainSpec Spec;
	const UGTTerrainSpecAsset* StripSpec = LoadObject<UGTTerrainSpecAsset>(nullptr, TEXT("/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants.DA_MudVariants"));
	bool bStrip = StripSpec && StripSpec->Spec.Sections.Num() == 4;
	for (int32 Index = 0; bStrip && Index < 4; ++Index)
	{
		bStrip = StripSpec->Spec.Sections[Index].Kind == EGTRouteSectionKind::Mud && StripSpec->Spec.Sections[Index].MudVariant == Rows[Index].Variant;
	}
	if (bStrip)
	{
		Spec = StripSpec->Spec;
		// Ground relief GR1: the fixture keeps the flat field (the strip's bogs are pre-churned since GR1).
		for (FGTRouteSection& Section : Spec.Sections)
		{
			Section.Deform.PreChurnScale = 0.f;
		}
	}
	else
	{
		AddWarning(TEXT("Chunks: DA_MudVariants missing or changed - the hand-built spec of GrandTour.Mud.Variants (its patches are not the strip's size)"));
		Spec.RouteM = { FVector2D(0.0, 0.0), FVector2D(215.0, 0.0) };
		Spec.Sections.Reset();
		for (int32 Index = 0; Index < 4; ++Index)
		{
			FGTRouteSection Section;
			Section.StartM = 30.f + 45.f * Index;
			Section.EndM = Section.StartM + 25.f;
			Section.Kind = EGTRouteSectionKind::Mud;
			Section.MudVariant = Rows[Index].Variant;
			Spec.Sections.Add(Section);
		}
	}
	AddInfo(FString::Printf(TEXT("Chunks: the spec - %s"), bStrip ? TEXT("DA_MudVariants (L_MudVariants' own)") : TEXT("the hand-built one")));

	// A Game world that simulates physics, with a static ground box (top at Z 0) under the whole strip.
	UWorld::InitializationValues Values;
	Values.CreatePhysicsScene(true).ShouldSimulatePhysics(true).EnableTraceCollision(true).CreateNavigation(false).CreateAISystem(false).AllowAudioPlayback(false);
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("GTMudChunksTest"), nullptr, true, ERHIFeatureLevel::Num, &Values);
	if (!TestNotNull(TEXT("Chunks: a Game world"), World))
	{
		ChunkSwitch->Set(ChunksWas, ECVF_SetByConsole);
		return false;
	}
	FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
	Context.SetCurrentWorld(World);
	auto Restore = [&]()
	{
		ChunkSwitch->Set(ChunksWas, ECVF_SetByConsole);
		if (ClodSwitch)
		{
			ClodSwitch->Set(ClodsWas, ECVF_SetByConsole);
		}
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
	};
	AActor* Ground = World->SpawnActor<AActor>();
	UBoxComponent* GroundBox = NewObject<UBoxComponent>(Ground, TEXT("Ground"));
	GroundBox->SetMobility(EComponentMobility::Static);
	GroundBox->SetBoxExtent(FVector(15000.0, 4000.0, 500.0), false);
	GroundBox->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	GroundBox->SetWorldLocation(FVector(10750.0, 0.0, -500.0));
	Ground->SetRootComponent(GroundBox);
	GroundBox->RegisterComponent();
	UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	const int32 Count = Mud ? Mud->BuildPatches(Spec) : 0;
	TestTrue(TEXT("Chunks: four patches, one per section"), Count == 4);
	AGTMudPatch* Patches[4] = { nullptr, nullptr, nullptr, nullptr };
	for (TActorIterator<AGTMudPatch> It(World); It; ++It)
	{
		if (It->SectionIndex >= 0 && It->SectionIndex < 4)
		{
			Patches[It->SectionIndex] = *It;
		}
	}
	for (int32 Index = 0; Index < 4; ++Index)
	{
		if (!TestNotNull(FString::Printf(TEXT("Chunks: %s - a patch"), Rows[Index].Name), Patches[Index]))
		{
			Restore();
			return false;
		}
	}

	// ---- 0. the meshes: all six imported, their numbers (UGTMudChunkData) the manifest's ----------------------------------
	AGTMudPatch* Standard = Patches[1];
	TArray<float> ManifestVolume;
	float ManifestAcross = 0.f;
	const bool bManifest = ReadChunkManifest(ManifestVolume, ManifestAcross);
	TestTrue(TEXT("Chunks: Art/Export/MudChunks/manifest.json read"), bManifest);
	if (!TestEqual(TEXT("Chunks: the six chunk meshes imported (Art/import_mud_chunks.ps1)"), Standard->MudChunkMeshCount, AGTMudPatch::MudChunkMeshVariants))
	{
		Restore();
		return false;
	}
	FString MeshLine;
	for (int32 Mesh = 0; Mesh < AGTMudPatch::MudChunkMeshVariants; ++Mesh)
	{
		const float Volume = Standard->MudChunkMeshVolumeCm3(Mesh);
		const float Want = ManifestVolume.IsValidIndex(Mesh) ? ManifestVolume[Mesh] : -1.f;
		TestTrue(FString::Printf(TEXT("Chunks: mesh %d's volume %.1f cm3 is the manifest's %.1f (UGTMudChunkData)"), Mesh, Volume, Want), Want > 0.f && FMath::Abs(Volume - Want) <= 0.001f * Want);
		TestTrue(FString::Printf(TEXT("Chunks: mesh %d is %.1f cm across"), Mesh, Standard->MudChunkMeshAcrossCm(Mesh)), FMath::Abs(Standard->MudChunkMeshAcrossCm(Mesh) - (ManifestAcross > 0.f ? ManifestAcross : 30.f)) < 0.01f);
		MeshLine += FString::Printf(TEXT("%s%d %.0f cm3"), MeshLine.IsEmpty() ? TEXT("") : TEXT(", "), Mesh, Volume);
	}
	AddInfo(FString::Printf(TEXT("Chunks: meshes - %s at %.0f cm across"), *MeshLine, Standard->MudChunkMeshAcrossCm(0)));

	// ---- 1. the spawn per variant: deterministic, the count, the rules, the spread, resting asleep on the ground ------------
	for (int32 RowIndex = 0; RowIndex < 4; ++RowIndex)
	{
		const FRow& Row = Rows[RowIndex];
		AGTMudPatch* Patch = Patches[RowIndex];
		const FGTMudField& Field = Patch->GetField();
		TestTrue(FString::Printf(TEXT("Chunks: %s - in scope (a bog's patch, S built)"), Row.Name), Patch->HasSoftSpots());
		TestTrue(FString::Printf(TEXT("Chunks: %s - density x%.2f"), Row.Name, Row.DensityScale), FMath::IsNearlyEqual(Patch->MudChunkDensityScale, Row.DensityScale, 1.e-6f));
		TArray<AGTMudPatch::FMudChunkPlan> PlanA;
		TArray<AGTMudPatch::FMudChunkPlan> PlanB;
		float AreaM2 = 0.f;
		int32 Target = 0;
		Patch->PlanMudChunks(PlanA, false, &AreaM2, &Target);
		Patch->PlanMudChunks(PlanB, false);
		bool bSame = PlanA.Num() == PlanB.Num();
		for (int32 K = 0; bSame && K < PlanA.Num(); ++K)
		{
			bSame = PlanA[K].XYCm == PlanB[K].XYCm && PlanA[K].SizeCm == PlanB[K].SizeCm && PlanA[K].Mesh == PlanB[K].Mesh && PlanA[K].YawDeg == PlanB[K].YawDeg
				&& PlanA[K].TiltDeg == PlanB[K].TiltDeg;
		}
		TestTrue(FString::Printf(TEXT("Chunks: %s - the plan is deterministic"), Row.Name), bSame);
		// The live chunks are the plan's, each where it was planned.
		TArray<FVector2D> Points;
		TArray<float> Sizes;
		TArray<int32> Live;
		for (int32 Slot = 0; Slot < Patch->NumMudChunkSlots(); ++Slot)
		{
			if (Patch->IsMudChunkAlive(Slot))
			{
				Live.Add(Slot);
				Points.Add(Patch->MudChunkXY(Slot));
				Sizes.Add(Patch->MudChunkSize(Slot));
			}
		}
		bool bLiveIsPlan = Live.Num() == PlanA.Num();
		for (int32 K = 0; bLiveIsPlan && K < Live.Num(); ++K)
		{
			bLiveIsPlan = FVector2D::Distance(Points[K], PlanA[K].XYCm) < 0.01 && FMath::IsNearlyEqual(Sizes[K], PlanA[K].SizeCm, 1.e-3f);
		}
		TestTrue(FString::Printf(TEXT("Chunks: %s - the %d live chunks are the plan's %d, where it put them"), Row.Name, Live.Num(), PlanA.Num()), bLiveIsPlan);
		TestTrue(FString::Printf(TEXT("Chunks: %s - %d chunks within 25 %% of the target %d (%.1f m2 x %.3f x %.2f)"), Row.Name, Live.Num(), Target, AreaM2, Patch->MudChunkDensityPerM2, Patch->MudChunkDensityScale),
			Target > 0 && FMath::Abs(Live.Num() - Target) <= 0.25f * Target);
		// The rules: S (the generator's own array), the rim, the route line, the edge gap.
		TArray<float> Softness;
		AGTMudPatch::BuildSoftness(Softness, Field.SizeX, Field.SizeY, Field.CellCm, Field.OriginCm, AGTMudPatch::SoftSpotSeed(Patch->SectionIndex), Patch->SoftSpotAmplitude);
		const FBox2D Box = Field.Bounds();
		int32 SoftHits = 0;
		int32 RimHits = 0;
		int32 RouteHits = 0;
		int32 Overlaps = 0;
		float MinGap = TNumericLimits<float>::Max();
		float MaxS = 0.f;
		float MinRim = TNumericLimits<float>::Max();
		int32 Asleep = 0;
		float WorstRest = 0.f;
		float MinMass = TNumericLimits<float>::Max();
		float MaxMass = 0.f;
		double VolumeSum = 0.0;
		int32 InCluster = 0;
		for (const AGTMudPatch::FMudChunkPlan& Plan : PlanA)
		{
			InCluster += Plan.bCluster ? 1 : 0;
		}
		for (int32 K = 0; K < Live.Num(); ++K)
		{
			const FVector2D P = Points[K];
			const float S = Softness[Field.CellIndexAt(P)];
			MaxS = FMath::Max(MaxS, S);
			SoftHits += S > Patch->MudChunkMaxSoftness ? 1 : 0;
			const float Rim = static_cast<float>(FMath::Min(FMath::Min(P.X - Box.Min.X, Box.Max.X - P.X), FMath::Min(P.Y - Box.Min.Y, Box.Max.Y - P.Y)));
			MinRim = FMath::Min(MinRim, Rim);
			RimHits += Rim < Patch->MudChunkRimCm ? 1 : 0;
			RouteHits += Patch->DistanceToRouteCm(P) > Patch->MudChunkRouteCm ? 1 : 0;
			for (int32 J = K + 1; J < Live.Num(); ++J)
			{
				const float Gap = static_cast<float>(FVector2D::Distance(P, Points[J])) - 0.5f * (Sizes[K] + Sizes[J]);
				MinGap = FMath::Min(MinGap, Gap);
				Overlaps += Gap < Patch->MudChunkGapCm - 1.e-3f ? 1 : 0;
			}
			Asleep += Patch->IsMudChunkAwake(Live[K]) ? 0 : 1;
			WorstRest = FMath::Max(WorstRest, FMath::Abs(Patch->MudChunkLowestHullZ(Live[K])));   // the ground's top is Z 0
			MinMass = FMath::Min(MinMass, Patch->MudChunkMassKg(Live[K]));
			MaxMass = FMath::Max(MaxMass, Patch->MudChunkMassKg(Live[K]));
			VolumeSum += Patch->MudChunkVolumeCm3(Live[K]);
		}
		TestEqual(FString::Printf(TEXT("Chunks: %s - none on a cell with S over %.2f"), Row.Name, Patch->MudChunkMaxSoftness), SoftHits, 0);
		TestEqual(FString::Printf(TEXT("Chunks: %s - none within %.0f cm of the rim"), Row.Name, Patch->MudChunkRimCm), RimHits, 0);
		TestEqual(FString::Printf(TEXT("Chunks: %s - none beyond %.0f cm of the route line"), Row.Name, Patch->MudChunkRouteCm), RouteHits, 0);
		TestEqual(FString::Printf(TEXT("Chunks: %s - no overlaps (edge gap at least %.0f cm)"), Row.Name, Patch->MudChunkGapCm), Overlaps, 0);
		float SizeMin = TNumericLimits<float>::Max();
		float SizeMax = 0.f;
		for (const float Size : Sizes)
		{
			SizeMin = FMath::Min(SizeMin, Size);
			SizeMax = FMath::Max(SizeMax, Size);
		}
		const float SizeCV = ChunkCV(Sizes);
		const TArray<float> Nearest = ChunkNearest(Points);
		const float NearestCV = ChunkCV(Nearest);
		TestTrue(FString::Printf(TEXT("Chunks: %s - size CV %.3f at least 0.25"), Row.Name, SizeCV), SizeCV >= 0.25f);
		TestTrue(FString::Printf(TEXT("Chunks: %s - the largest %.1f cm at least twice the smallest %.1f cm"), Row.Name, SizeMax, SizeMin), Sizes.Num() > 0 && SizeMax >= 2.f * SizeMin);
		TestTrue(FString::Printf(TEXT("Chunks: %s - nearest-neighbour CV %.3f at least 0.4"), Row.Name, NearestCV), NearestCV >= 0.4f);
		TestEqual(FString::Printf(TEXT("Chunks: %s - every chunk asleep after its spawn"), Row.Name), Asleep, Live.Num());
		TestTrue(FString::Printf(TEXT("Chunks: %s - every hull's lowest point on the ground (worst %.3f cm)"), Row.Name, WorstRest), WorstRest <= 0.5f);
		TestTrue(FString::Printf(TEXT("Chunks: %s - masses %.1f-%.1f kg within %.0f-%.0f"), Row.Name, MinMass, MaxMass, Patch->MudChunkMassMinKg, Patch->MudChunkMassMaxKg),
			Live.Num() == 0 || (MinMass >= Patch->MudChunkMassMinKg - 1.e-3f && MaxMass <= Patch->MudChunkMassMaxKg + 1.e-3f));
		float NearestMean = 0.f;
		for (const float D : Nearest)
		{
			NearestMean += D / FMath::Max(1, Nearest.Num());
		}
		AddInfo(FString::Printf(TEXT("Chunks: %s (section %d, seed %d) - %d live of target %d (%.1f m2 candidate x %.3f a m2 x %.2f; %d in cluster ground), sizes %.1f-%.1f cm CV %.3f, nearest-neighbour mean %.0f cm CV %.3f, max S %.3f (violations %d), min rim %.0f cm (violations %d), route violations %d, min edge gap %.1f cm (overlaps %d), %d asleep, worst rest %.3f cm, masses %.1f-%.1f kg, volume %.0f cm3"),
			Row.Name, Patch->SectionIndex, AGTMudPatch::MudChunkSeed(Patch->SectionIndex), Live.Num(), Target, AreaM2, Patch->MudChunkDensityPerM2, Patch->MudChunkDensityScale, InCluster,
			SizeMin, SizeMax, SizeCV, NearestMean, NearestCV, MaxS, SoftHits, MinRim, RimHits, RouteHits, MinGap, Overlaps, Asleep, WorstRest, MinMass, MaxMass, VolumeSum));
	}

	// ---- 2. the wheel: a footprint just clear of a chunk leaves it, one that reaches it breaks it (volume exact, 3-5 clods) ----
	{
		AGTMudPatch* Patch = Standard;
		int32 Index = INDEX_NONE;
		for (int32 Slot = 0; Slot < Patch->NumMudChunkSlots() && Index == INDEX_NONE; ++Slot)
		{
			Index = Patch->IsMudChunkAlive(Slot) ? Slot : INDEX_NONE;
		}
		if (TestTrue(TEXT("Chunks: wheel - a live chunk in Standard"), Index != INDEX_NONE))
		{
			const FVector2D XY = Patch->MudChunkXY(Index);
			const float Size = Patch->MudChunkSize(Index);
			const float Reach = 12.5f + Patch->MudChunkFootprint * Size;   // a 25 cm tyre's half width + the footprint circle
			// A stroke along X, 2 cm clear of the footprint to the -Y side: nothing breaks.
			const int32 Clear = Patch->BreakMudChunksUnderWheel(XY + FVector2D(-60.0, -(Reach + 2.0)), XY + FVector2D(60.0, -(Reach + 2.0)), 12.5f);
			TestTrue(TEXT("Chunks: wheel - a stroke 2 cm clear of the footprint breaks nothing there"), Patch->IsMudChunkAlive(Index) && Clear == 0);
			double Lump0 = 0.0;
			double Height0 = 0.0;
			ChunkFieldVolumes(Patch->GetField(), Lump0, Height0);
			const float Volume = Patch->MudChunkVolumeCm3(Index);
			const int32 Mesh = Patch->MudChunkMesh(Index);
			const float FromManifest = ManifestVolume.IsValidIndex(Mesh) ? ManifestVolume[Mesh] * FMath::Pow(Size / FMath::Max(1.f, ManifestAcross), 3.f) : -1.f;
			const int32 ClodsBefore = Patch->ClodsFromChunk;
			const int32 WheelBefore = Patch->MudChunkBreaksWheel;
			// The same stroke 2 cm into it.
			const int32 Breaks = Patch->BreakMudChunksUnderWheel(XY + FVector2D(-60.0, -(Reach - 2.0)), XY + FVector2D(60.0, -(Reach - 2.0)), 12.5f);
			double Lump1 = 0.0;
			double Height1 = 0.0;
			ChunkFieldVolumes(Patch->GetField(), Lump1, Height1);
			const double Added = (Lump1 - Lump0) + (Height1 - Height0);
			const double Error = FMath::Abs(Added - Volume) / FMath::Max(1.f, Volume);
			const int32 Clods = Patch->ClodsFromChunk - ClodsBefore;
			TestTrue(TEXT("Chunks: wheel - a stroke 2 cm into the footprint removes the chunk"), !Patch->IsMudChunkAlive(Index) && Breaks >= 1 && Patch->MudChunkBreaksWheel == WheelBefore + Breaks);
			TestTrue(FString::Printf(TEXT("Chunks: wheel - its volume %.1f cm3 is the manifest's x scale^3 (%.1f)"), Volume, FromManifest), FromManifest > 0.f && FMath::Abs(Volume - FromManifest) <= 0.005f * FromManifest);
			TestTrue(FString::Printf(TEXT("Chunks: wheel - the field took %.1f cm3 for %.1f (%.3f %%)"), Added, Volume, 100.0 * Error), Breaks == 1 && Error <= 0.005);
			TestTrue(FString::Printf(TEXT("Chunks: wheel - %d clods (3-5)"), Clods), Clods >= 3 && Clods <= 5);
			AddInfo(FString::Printf(TEXT("Chunks: wheel break - a %.1f cm chunk (mesh %d) of %.1f cm3 (the manifest's x scale^3 %.1f): the field +%.1f cm3 (LumpCm +%.1f, over LumpMaxCm into HeightCm +%.1f; error %.4f %%), %d clod(s), %d break(s); 2 cm clear: %d"),
				Size, Mesh, Volume, FromManifest, Added, Lump1 - Lump0, Height1 - Height0, 100.0 * Error, Clods, Breaks, Clear));
		}
	}

	// ---- 3. the chassis' impulse (0.9x and 1.1x ChunkBreakImpulse) and a landing (0.9x and 1.1x ChunkBreakLandCmPerS) ----------
	{
		AGTMudPatch* Patch = Patches[2];   // Deep: the most chunks
		TArray<int32> Live;
		for (int32 Slot = 0; Slot < Patch->NumMudChunkSlots(); ++Slot)
		{
			if (Patch->IsMudChunkAlive(Slot))
			{
				Live.Add(Slot);
			}
		}
		AActor* Car = World->SpawnActor<AActor>();
		UBoxComponent* Body = NewObject<UBoxComponent>(Car, TEXT("Body"));
		Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Body->SetCollisionObjectType(ECC_Vehicle);
		Body->SetWorldLocation(FVector(0.0, 50000.0, 1000.0));
		Car->SetRootComponent(Body);
		Body->RegisterComponent();
		if (TestTrue(TEXT("Chunks: impulse - two live chunks in Deep"), Live.Num() >= 2))
		{
			UStaticMeshComponent* Hit = Patch->GetMudChunkComponent(Live[0]);
			const float J = Patch->ChunkBreakImpulse;
			const int32 Before = Patch->MudChunkBreaksImpulse;
			Patch->OnMudChunkHit(Hit, Car, Body, FVector(0.0, 0.0, 0.9 * J), FHitResult());
			const bool bAfterLow = Patch->IsMudChunkAlive(Live[0]);
			Patch->OnMudChunkHit(Hit, Car, Body, FVector(0.6 * 1.1 * J, 0.8 * 1.1 * J, 0.0), FHitResult());
			const bool bAfterHigh = Patch->IsMudChunkAlive(Live[0]);
			TestTrue(FString::Printf(TEXT("Chunks: impulse - 0.9x %.0f kg cm/s from the chassis: pushed, not broken"), J), bAfterLow);
			TestTrue(FString::Printf(TEXT("Chunks: impulse - 1.1x %.0f kg cm/s from the chassis: broken"), J), !bAfterHigh && Patch->MudChunkBreaksImpulse == Before + 1);
			// A landing: the ground's hit impulse over the chunk's mass against ChunkBreakLandCmPerS.
			UStaticMeshComponent* Lands = Patch->GetMudChunkComponent(Live[1]);
			const float Mass = Patch->MudChunkMassKg(Live[1]);
			const float V = Patch->ChunkBreakLandCmPerS;
			const int32 LandBefore = Patch->MudChunkBreaksLanding;
			Patch->OnMudChunkHit(Lands, Ground, GroundBox, FVector(0.0, 0.0, 0.9 * V * Mass), FHitResult());
			const bool bLandLow = Patch->IsMudChunkAlive(Live[1]);
			Patch->OnMudChunkHit(Lands, Ground, GroundBox, FVector(0.0, 0.0, 1.1 * V * Mass), FHitResult());
			TestTrue(TEXT("Chunks: landing - at 0.9x not broken, at 1.1x broken"), bLandLow && !Patch->IsMudChunkAlive(Live[1]) && Patch->MudChunkBreaksLanding == LandBefore + 1);
			AddInfo(FString::Printf(TEXT("Chunks: impulse break - at 0.9x %.0f kg cm/s %s, at 1.1x %s; landing (%.1f kg) at 0.9x %.0f cm/s %s, at 1.1x %s"),
				J, bAfterLow ? TEXT("pushed") : TEXT("BROKEN"), bAfterHigh ? TEXT("NOT BROKEN") : TEXT("broken"), Mass, V, bLandLow ? TEXT("held") : TEXT("BROKEN"),
				Patch->IsMudChunkAlive(Live[1]) ? TEXT("NOT BROKEN") : TEXT("broken")));
		}
	}

	// ---- 4. the awake cap: 100 more chunks on Firm's rim band, every chunk woken, at most MaxAwakeMudChunks stay awake ----------
	{
		AGTMudPatch* Patch = Patches[0];
		const FBox2D Box = Patch->GetField().Bounds();
		int32 Added = 0;
		for (int32 K = 0; K < 100; ++K)
		{
			const FVector At(Box.Min.X + 40.0 + 32.0 * (K % 50), Box.Min.Y + 30.0 + 40.0 * (K / 50), 0.0);   // the rim band: no planned chunk there
			Added += Patch->SpawnMudChunkForTest(At, 20.f, K % AGTMudPatch::MudChunkMeshVariants, true) != INDEX_NONE ? 1 : 0;
		}
		TestEqual(TEXT("Chunks: awake cap - 100 test chunks"), Added, 100);
		int32 Woken = 0;
		for (AGTMudPatch* Each : Patches)
		{
			for (int32 Slot = 0; Slot < Each->NumMudChunkSlots(); ++Slot)
			{
				if (Each->IsMudChunkAlive(Slot))
				{
					Each->GetMudChunkComponent(Slot)->WakeRigidBody();
					Woken += Each->IsMudChunkAwake(Slot) ? 1 : 0;
				}
			}
		}
		const int32 Slept = Mud->EnforceMudChunkAwakeCap(true);
		int32 Awake = 0;
		for (AGTMudPatch* Each : Patches)
		{
			for (int32 Slot = 0; Slot < Each->NumMudChunkSlots(); ++Slot)
			{
				Awake += Each->IsMudChunkAwake(Slot) ? 1 : 0;
			}
		}
		TestTrue(FString::Printf(TEXT("Chunks: awake cap - %d woken (at least 100)"), Woken), Woken >= 100);
		TestTrue(FString::Printf(TEXT("Chunks: awake cap - %d stay awake (at most %d)"), Awake, Mud->MaxAwakeMudChunks), Awake <= Mud->MaxAwakeMudChunks && Awake == FMath::Min(Woken, Mud->MaxAwakeMudChunks));
		AddInfo(FString::Printf(TEXT("Chunks: awake cap - %d woken, %d put to sleep, %d awake (cap %d; subsystem peak %d)"), Woken, Slept, Awake, Mud->MaxAwakeMudChunks, Mud->GetMudChunkAwakePeak()));
		// Everything back to sleep for the drop.
		for (AGTMudPatch* Each : Patches)
		{
			for (int32 Slot = 0; Slot < Each->NumMudChunkSlots(); ++Slot)
			{
				Each->SleepMudChunk(Slot);
			}
		}
	}

	// ---- 5. the physics: each mesh dropped 5 cm onto the flat ground rests and sleeps within 3 s, its hull's bottom on the ground ----
	{
		AGTMudPatch* Patch = Patches[3];   // Stony's rim band: no planned chunk there
		const FBox2D Box = Patch->GetField().Bounds();
		TArray<int32> Dropped;
		for (int32 Mesh = 0; Mesh < AGTMudPatch::MudChunkMeshVariants; ++Mesh)
		{
			const FVector At(Box.Min.X + 100.0 + 100.0 * Mesh, Box.Min.Y + 70.0, 5.0);
			Dropped.Add(Patch->SpawnMudChunkForTest(At, 30.f, Mesh, false));
		}
		TArray<float> SleptAt;
		SleptAt.Init(-1.f, Dropped.Num());
		const float Step = 1.f / 60.f;
		float Time = 0.f;
		while (Time < 3.f + 0.5f * Step)
		{
			// A tick function runs once per engine frame (GFrameCounter), and this loop sits inside one: the counter moves with each tick.
			++GFrameCounter;
			World->Tick(LEVELTICK_All, Step);
			Time += Step;
			bool bAll = true;
			for (int32 K = 0; K < Dropped.Num(); ++K)
			{
				if (SleptAt[K] < 0.f && Dropped[K] != INDEX_NONE && !Patch->IsMudChunkAwake(Dropped[K]))
				{
					SleptAt[K] = Time;
				}
				bAll &= SleptAt[K] >= 0.f;
			}
			if (bAll)
			{
				break;
			}
		}
		if (const UStaticMeshComponent* First = Dropped[0] != INDEX_NONE ? Patch->GetMudChunkComponent(Dropped[0]) : nullptr)
		{
			const FBodyInstance* BodyInstance = First->GetBodyInstance();
			AddInfo(FString::Printf(TEXT("Chunks: drop diag - world time %.3f s after %.2f s of ticks, physics scene %d, simulating %d, dynamic %d, valid body %d, z %.3f, velocity %s, should simulate %d, collision %d"),
				World->GetTimeSeconds(), Time, World->GetPhysicsScene() != nullptr ? 1 : 0, First->IsSimulatingPhysics() ? 1 : 0, BodyInstance && BodyInstance->IsDynamic() ? 1 : 0,
				BodyInstance && BodyInstance->IsValidBodyInstance() ? 1 : 0, First->GetComponentLocation().Z, *First->GetPhysicsLinearVelocity().ToString(), World->bShouldSimulatePhysics ? 1 : 0,
				static_cast<int32>(First->GetCollisionEnabled())));
		}
		FString DropLine;
		for (int32 K = 0; K < Dropped.Num(); ++K)
		{
			const bool bThere = Dropped[K] != INDEX_NONE && Patch->IsMudChunkAlive(Dropped[K]);
			const float Bottom = bThere ? Patch->MudChunkLowestHullZ(Dropped[K]) : 1.e6f;
			TestTrue(FString::Printf(TEXT("Chunks: drop - mesh %d asleep within 3 s (at %.2f s)"), K, SleptAt[K]), bThere && SleptAt[K] >= 0.f && SleptAt[K] <= 3.f + 0.5f * Step);
			TestTrue(FString::Printf(TEXT("Chunks: drop - mesh %d's hull bottom %.2f cm within 1 cm of the ground"), K, Bottom), FMath::Abs(Bottom) <= 1.f);
			DropLine += FString::Printf(TEXT("%smesh %d asleep at %.2f s, hull bottom %.2f cm"), DropLine.IsEmpty() ? TEXT("") : TEXT("; "), K, SleptAt[K], Bottom);
		}
		AddInfo(FString::Printf(TEXT("Chunks: drop 5 cm (30 cm, %.0f ticks of 1/60 s at most) - %s"), 3.f / Step, *DropLine));
	}

	// ---- 6. the switch: 0 removes every chunk and leaves the fields as they were; 1 places them anew on untouched ground ---------
	{
		uint32 Crc[4];
		for (int32 K = 0; K < 4; ++K)
		{
			Crc[K] = Patches[K]->FieldCrc();
		}
		ChunkSwitch->Set(0, ECVF_SetByConsole);
		int32 Live = 0;
		bool bSameField = true;
		for (int32 K = 0; K < 4; ++K)
		{
			Patches[K]->ApplyMudChunkSwitch(false);   // what the patch's tick does when the switch flips
			Live += Patches[K]->MudChunksLive;
			bSameField &= Patches[K]->FieldCrc() == Crc[K];
		}
		TestEqual(TEXT("Chunks: switch 0 - no chunks"), Live, 0);
		TestTrue(TEXT("Chunks: switch 0 - the fields as they were (no deposit)"), bSameField);
		ChunkSwitch->Set(1, ECVF_SetByConsole);
		int32 Back = 0;
		FString BackLine;
		for (int32 K = 0; K < 4; ++K)
		{
			Patches[K]->ApplyMudChunkSwitch(true);
			Back += Patches[K]->MudChunksLive;
			BackLine += FString::Printf(TEXT("%s%s %d"), BackLine.IsEmpty() ? TEXT("") : TEXT(", "), Rows[K].Name, Patches[K]->MudChunksLive);
		}
		TestTrue(TEXT("Chunks: switch 1 again - chunks placed anew"), Back > 0);
		AddInfo(FString::Printf(TEXT("Chunks: switch - 0: %d live, fields unchanged %d; 1 again: %d live on untouched ground (%s)"), Live, bSameField ? 1 : 0, Back, *BackLine));
	}

	Restore();
	return true;
}

#endif
