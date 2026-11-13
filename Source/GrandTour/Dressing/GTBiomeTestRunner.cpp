#include "Dressing/GTBiomeTestRunner.h"

#include "Dressing/GTDressingExclusion.h"
#include "Look/GTLookSubsystem.h"
#include "Terrain/GTTerrainDressing.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Weather/GTWeatherStateDefinition.h"
#include "Weather/GTWeatherSubsystem.h"

#include "Components/BoxComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

namespace GTBiomeTest
{
	constexpr float StartAfterSeconds = 1.f;
	constexpr int32 StartAfterTicks = 5;

	/**
	 * GTTerrain::GenerateHash of HideSpec() and ProvingSpec(), recorded 2026-09-27 before the biome rules went in (LD1
	 * stage 1: the hash function and this test built and run on the generator as it was). A spec with no biomes must keep
	 * generating exactly these bytes.
	 */
	constexpr uint64 ExpectedHideHash = 0x977AF3A498E07815ull;
	constexpr uint64 ExpectedProvingHash = 0x7DBDFB11F2FD2CE1ull;

	/** LayerAt / BiomeAt sample points on the Hide grid. */
	constexpr int32 SamplePoints = 4000;
	/** BiomeAt must name the grid's dominant biome at this share of the mostly off-road sample vertices at least. */
	constexpr float MinBiomeAgreement = 0.98f;

	/**
	 * LD1b (the D2 palette revised 2026-09-27): the dominant shares of the off-road land (vertices that had Scrub) the Hide
	 * grid must land in - Forest + ForestFir about 30 % (the 300 m noise within 0.70-1), Thicket at most about 8 %.
	 */
	constexpr float ForestShareMin = 0.22f;
	constexpr float ForestShareMax = 0.38f;
	constexpr float ThicketShareMin = 0.01f;
	constexpr float ThicketShareMax = 0.09f;
	/** The rule order revised after LD1b: the riparian Thicket (before the forest rules) dominant on at least this many Hide vertices. */
	constexpr int32 MinRiparianDominantVerts = 1000;

	const TCHAR* const SpecAssetPath = TEXT("/Game/GrandTour/Terrain/DA_Terrain_Hide.DA_Terrain_Hide");

	void Line(const FString& Text)
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST biome %s"), *Text);
	}

	void SetCvar(const TCHAR* Name, int32 Value)
	{
		if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name))
		{
			Var->Set(Value, ECVF_SetByCode);
		}
	}

	int32 GetCvar(const TCHAR* Name)
	{
		const IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name);
		return Var ? Var->GetInt() : -1;
	}
}

void FGTBiomeTestRunner::AddD2Palette(FGTTerrainSpec& Spec)
{
	// LEG_DRESSING_PLAN section 5, D2 (revised after LD1b). Since LD6 the palette's one source is GTTerrain::HideSpec()
	// (Terrain/GTTerrainGenerator.cpp AddHideBiomes, pushed to DA_Terrain_Hide); this copies its rules onto any spec.
	const FGTTerrainSpec Hide = GTTerrain::HideSpec();
	Spec.Biomes = Hide.Biomes;
	Spec.FallbackBiome = Hide.FallbackBiome;
}

FGTTerrainSpec FGTBiomeTestRunner::HideSpecNoBiomes()
{
	// The Hide as it was before the biome rules: the pre-biome hash and the "plain" side of every comparison.
	FGTTerrainSpec Spec = GTTerrain::HideSpec();
	Spec.Biomes.Reset();
	Spec.FallbackBiome = NAME_None;
	return Spec;
}

FGTBiomeTestRunner::FGTBiomeTestRunner(UWorld* InWorld)
	: World(InWorld)
{
}

bool FGTBiomeTestRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
{
	Elapsed += DeltaSeconds;
	++Ticks;
	if (Elapsed < GTBiomeTest::StartAfterSeconds || Ticks < GTBiomeTest::StartAfterTicks)
	{
		return false;
	}
	if (WaitTicks > 0)
	{
		--WaitTicks;
		return false;
	}
	switch (Phase++)
	{
	case 0: PhaseHashes(); return false;
	case 1: PhaseBiomes(); return false;
	case 2: PhaseLayerAt(); return false;
	case 3: PhaseCards(); return false;
	case 4: PhaseExclusion(); return false;
	case 5: PhaseWind(); return false;
	case 6: PhaseDressingOff(); WaitTicks = 3; return false;
	case 7: PhaseDressingOn(); WaitTicks = 3; return false;
	case 8: PhaseDressingRestored(); return false;
	default: break;
	}
	bOutPass = Failures.Num() == 0;
	OutSummary = bOutPass ? FString::Join(Notes, TEXT("; ")) : FString::Join(Failures, TEXT("; "));
	return true;
}

void FGTBiomeTestRunner::PhaseHashes()
{
	using namespace GTBiomeTest;
	struct FCase
	{
		const TCHAR* Name;
		FGTTerrainSpec Spec;
		uint64 Expected;
	};
	const FCase Cases[] = {
		{ TEXT("Hide"), HideSpecNoBiomes(), ExpectedHideHash },   // LD6: HideSpec() carries the palette; cleared here
		{ TEXT("Proving"), GTTerrain::ProvingSpec(), ExpectedProvingHash },
	};
	for (const FCase& Case : Cases)
	{
		const double Start = FPlatformTime::Seconds();
		TArray<uint16> Heights;
		TArray<TArray<uint8>> Weights;
		GTTerrain::Generate(Case.Spec, Heights, Weights);
		const uint64 Hash = GTTerrain::HashGrid(Heights, Weights);
		const int32 Verts = GTTerrain::VertsPerSide(Case.Spec);
		Line(FString::Printf(TEXT("no-biome hash %s: 0x%016llX (expected 0x%016llX) %dx%d verts, %d layers, generated in %.1f s; GenerateHash agrees: %s"),
			Case.Name, Hash, Case.Expected, Verts, Verts, Weights.Num(), FPlatformTime::Seconds() - Start, GTTerrain::GenerateHash(Case.Spec) == Hash ? TEXT("yes") : TEXT("NO")));
		if (Hash != Case.Expected || Weights.Num() != GTTerrain::LayerCount)
		{
			Failures.Add(FString::Printf(TEXT("%s no-biome hash 0x%016llX != 0x%016llX (%d layers)"), Case.Name, Hash, Case.Expected, Weights.Num()));
		}
		else
		{
			Notes.Add(FString::Printf(TEXT("%s hash 0x%016llX unchanged"), Case.Name, Hash));
		}
		if (FCString::Strcmp(Case.Name, TEXT("Hide")) == 0)
		{
			PlainHeights = MoveTemp(Heights);
			PlainWeights = MoveTemp(Weights);
		}
	}
	// The asset the legs actually build from: the same spec as HideSpec()? (The exclusion phase reads it.)
	if (const UGTTerrainSpecAsset* Asset = LoadObject<UGTTerrainSpecAsset>(nullptr, SpecAssetPath))
	{
		const FGTTerrainSpec Code = GTTerrain::HideSpec();
		const bool bSame = FGTTerrainSpec::StaticStruct()->CompareScriptStruct(&Asset->Spec, &Code, PPF_None);
		Line(FString::Printf(TEXT("DA_Terrain_Hide: the same spec as GTTerrain::HideSpec(): %s; %d biome rule(s), fallback %s"),
			bSame ? TEXT("yes") : TEXT("no"), Asset->Spec.Biomes.Num(), *Asset->Spec.FallbackBiome.ToString()));
	}
}

void FGTBiomeTestRunner::PhaseBiomes()
{
	using namespace GTBiomeTest;
	FGTTerrainSpec Spec = HideSpecNoBiomes();
	AddD2Palette(Spec);
	GTTerrain::BiomeLayers(Spec, BiomeNames);
	const double Start = FPlatformTime::Seconds();
	TArray<uint16> Heights;
	GTTerrain::Generate(Spec, Heights, BiomeWeights);
	const double Seconds = FPlatformTime::Seconds() - Start;
	const int32 Verts = GTTerrain::VertsPerSide(Spec);
	const int32 N = Verts * Verts;
	const int32 Ground = FMath::Clamp(Spec.OffRoadLayer, 0, GTTerrain::LayerCount - 1);
	TArray<FName> Names;
	GTTerrain::WeightLayerNames(Spec, Names);
	Line(FString::Printf(TEXT("with the D2 palette: %d rules, %d biome layers (%s), %d weight layers in all, generated in %.1f s"),
		Spec.Biomes.Num(), BiomeNames.Num(), *FString::JoinBy(BiomeNames, TEXT(" "), [](const FName& Name) { return Name.ToString(); }), BiomeWeights.Num(), Seconds));
	if (BiomeWeights.Num() != GTTerrain::LayerCount + BiomeNames.Num() || Names.Num() != BiomeWeights.Num() || PlainWeights.Num() != GTTerrain::LayerCount)
	{
		Failures.Add(FString::Printf(TEXT("with biomes: %d weight layers, %d names, %d biome layers"), BiomeWeights.Num(), Names.Num(), BiomeNames.Num()));
		return;
	}

	// Heights and layers 0-3 and 5 byte-identical.
	const bool bHeights = Heights.Num() == PlainHeights.Num() && FMemory::Memcmp(Heights.GetData(), PlainHeights.GetData(), Heights.Num() * sizeof(uint16)) == 0;
	FString Identical;
	int32 Differing = 0;
	for (int32 Layer = 0; Layer < GTTerrain::LayerCount; ++Layer)
	{
		if (Layer == Ground)
		{
			continue;
		}
		const bool bSame = BiomeWeights[Layer].Num() == N && FMemory::Memcmp(BiomeWeights[Layer].GetData(), PlainWeights[Layer].GetData(), N) == 0;
		Identical += FString::Printf(TEXT(" %s=%s"), GTTerrain::LayerName(Layer), bSame ? TEXT("same") : TEXT("DIFFERENT"));
		Differing += bSame ? 0 : 1;
	}
	Line(FString::Printf(TEXT("heights byte-identical: %s; layers:%s"), bHeights ? TEXT("yes") : TEXT("NO"), *Identical));
	if (!bHeights)
	{
		Failures.Add(TEXT("heights differ with biomes"));
	}
	if (Differing > 0)
	{
		Failures.Add(FString::Printf(TEXT("%d of layers 0-3,5 differ with biomes"), Differing));
	}

	// The biome bytes add up to the old Scrub byte at every vertex; every vertex sums to 255.
	int32 SumViolations = 0;
	int32 WorstDiff = 0;
	int32 Not255 = 0;
	int32 ScrubLeft = 0;
	int32 OffRoadVerts = 0;
	TArray<int32> Painted;
	TArray<int32> Dominant;
	Painted.SetNumZeroed(BiomeNames.Num());
	Dominant.SetNumZeroed(BiomeNames.Num());
	for (int32 Index = 0; Index < N; ++Index)
	{
		int32 Biome = 0;
		int32 Best = INDEX_NONE;
		int32 BestByte = 0;
		for (int32 B = 0; B < BiomeNames.Num(); ++B)
		{
			const int32 Byte = BiomeWeights[GTTerrain::LayerCount + B][Index];
			Biome += Byte;
			if (Byte > 0)
			{
				++Painted[B];
			}
			if (Byte > BestByte)
			{
				BestByte = Byte;
				Best = B;
			}
		}
		if (Best != INDEX_NONE)
		{
			++Dominant[Best];
		}
		const int32 NewScrub = BiomeWeights[Ground][Index];
		const int32 OldScrub = PlainWeights[Ground][Index];
		ScrubLeft += NewScrub > 0 ? 1 : 0;
		OffRoadVerts += OldScrub > 0 ? 1 : 0;
		const int32 Diff = FMath::Abs(Biome + NewScrub - OldScrub);
		WorstDiff = FMath::Max(WorstDiff, Diff);
		SumViolations += Diff > 1 ? 1 : 0;
		int32 Total = 0;
		for (int32 Layer = 0; Layer < BiomeWeights.Num(); ++Layer)
		{
			Total += BiomeWeights[Layer][Index];
		}
		Not255 += Total != 255 ? 1 : 0;
	}
	Line(FString::Printf(TEXT("sum check: %d of %d vertices off by more than 1 (worst %d); %d vertices not summing to 255; %d vertices keep a Scrub byte (fallback %s); %d vertices had Scrub"),
		SumViolations, N, WorstDiff, Not255, ScrubLeft, *Spec.FallbackBiome.ToString(), OffRoadVerts));
	if (SumViolations > 0 || Not255 > 0)
	{
		Failures.Add(FString::Printf(TEXT("biome sum: %d vertices off by > 1 (worst %d), %d not 255"), SumViolations, WorstDiff, Not255));
	}
	int32 Empty = 0;
	FString Counts;
	int32 ForestDominant = 0;
	int32 ThicketDominant = 0;
	int32 ThicketLayer = INDEX_NONE;
	for (int32 B = 0; B < BiomeNames.Num(); ++B)
	{
		Line(FString::Printf(TEXT("layer %d %s: painted on %d vertices (%.1f %% of the Scrub ones), dominant on %d (%.1f %% of the off-road land)"),
			GTTerrain::LayerCount + B, *BiomeNames[B].ToString(), Painted[B], 100.f * Painted[B] / FMath::Max(1, OffRoadVerts), Dominant[B], 100.f * Dominant[B] / FMath::Max(1, OffRoadVerts)));
		Counts += FString::Printf(TEXT(" %s %d"), *BiomeNames[B].ToString(), Painted[B]);
		Empty += Painted[B] > 0 ? 0 : 1;
		if (BiomeNames[B] == FName(TEXT("OW_Forest")) || BiomeNames[B] == FName(TEXT("OW_ForestFir")))
		{
			ForestDominant += Dominant[B];
		}
		if (BiomeNames[B] == FName(TEXT("Thicket")))
		{
			ThicketDominant = Dominant[B];
			ThicketLayer = B;
		}
	}
	if (Empty > 0)
	{
		Failures.Add(FString::Printf(TEXT("%d biome layer(s) on no vertex:%s"), Empty, *Counts));
	}
	else
	{
		Notes.Add(FString::Printf(TEXT("biomes: heights and layers 0-3,5 identical, sums exact (worst %d), painted:%s"), WorstDiff, *Counts));
	}

	// LD1b: the revised D2 coverage, as dominant shares of the off-road land.
	const float ForestShare = static_cast<float>(ForestDominant) / FMath::Max(1, OffRoadVerts);
	const float ThicketShare = static_cast<float>(ThicketDominant) / FMath::Max(1, OffRoadVerts);
	Line(FString::Printf(TEXT("coverage: Forest + ForestFir dominant on %.1f %% of the off-road land (want %.0f-%.0f %%), Thicket on %.1f %% (want %.0f-%.0f %%)"),
		100.f * ForestShare, 100.f * ForestShareMin, 100.f * ForestShareMax, 100.f * ThicketShare, 100.f * ThicketShareMin, 100.f * ThicketShareMax));
	if (ForestShare < ForestShareMin || ForestShare > ForestShareMax)
	{
		Failures.Add(FString::Printf(TEXT("Forest + ForestFir dominant on %.1f %% of the off-road land (want %.0f-%.0f %%)"), 100.f * ForestShare, 100.f * ForestShareMin, 100.f * ForestShareMax));
	}
	if (ThicketShare < ThicketShareMin || ThicketShare > ThicketShareMax)
	{
		Failures.Add(FString::Printf(TEXT("Thicket dominant on %.1f %% of the off-road land (want %.0f-%.0f %%)"), 100.f * ThicketShare, 100.f * ThicketShareMin, 100.f * ThicketShareMax));
	}
	else
	{
		Notes.Add(FString::Printf(TEXT("coverage: forest %.1f %%, thicket %.1f %%"), 100.f * ForestShare, 100.f * ThicketShare));
	}

	// LD1b: Thicket's split, ring against riparian - the grid again with the section rule's layer renamed, so each rule's
	// bytes land on a layer of their own (the compositing is by rule, so every other byte is the same).
	if (ThicketLayer != INDEX_NONE)
	{
		const FName ThicketName(TEXT("Thicket"));
		const FName RiparianName(TEXT("Thicket_Riparian"));
		FGTTerrainSpec Split = Spec;
		for (FGTBiomeRule& R : Split.Biomes)
		{
			if (R.Layer == ThicketName && R.MaxSectionDistM > 0.f)
			{
				R.Layer = RiparianName;
			}
		}
		TArray<FName> SplitNames;
		GTTerrain::BiomeLayers(Split, SplitNames);
		const int32 Ring = SplitNames.IndexOfByKey(ThicketName);
		const int32 Riparian = SplitNames.IndexOfByKey(RiparianName);
		TArray<uint16> SplitHeights;
		TArray<TArray<uint8>> SplitWeights;
		GTTerrain::Generate(Split, SplitHeights, SplitWeights);
		if (Ring != INDEX_NONE && Riparian != INDEX_NONE && SplitWeights.Num() == GTTerrain::LayerCount + SplitNames.Num())
		{
			int64 RingBytes = 0;
			int64 RiparianBytes = 0;
			int32 RingDominant = 0;
			int32 RiparianDominant = 0;
			int32 ThicketVertsRing = 0;
			int32 ThicketVertsRiparian = 0;
			for (int32 Index = 0; Index < N; ++Index)
			{
				const int32 RingByte = SplitWeights[GTTerrain::LayerCount + Ring][Index];
				const int32 RiparianByte = SplitWeights[GTTerrain::LayerCount + Riparian][Index];
				RingBytes += RingByte;
				RiparianBytes += RiparianByte;
				int32 Best = INDEX_NONE;
				int32 BestByte = 0;
				for (int32 B = 0; B < SplitNames.Num(); ++B)
				{
					const int32 Byte = SplitWeights[GTTerrain::LayerCount + B][Index];
					if (Byte > BestByte)
					{
						BestByte = Byte;
						Best = B;
					}
				}
				RingDominant += Best == Ring ? 1 : 0;
				RiparianDominant += Best == Riparian ? 1 : 0;
				// Of the vertices where the merged Thicket dominates, which rule gave it more.
				int32 MergedBest = INDEX_NONE;
				int32 MergedByte = 0;
				for (int32 B = 0; B < BiomeNames.Num(); ++B)
				{
					const int32 Byte = BiomeWeights[GTTerrain::LayerCount + B][Index];
					if (Byte > MergedByte)
					{
						MergedByte = Byte;
						MergedBest = B;
					}
				}
				if (MergedBest == ThicketLayer && (RingByte > 0 || RiparianByte > 0))
				{
					(RingByte >= RiparianByte ? ThicketVertsRing : ThicketVertsRiparian) += 1;
				}
			}
			const int64 ThicketBytes = FMath::Max<int64>(1, RingBytes + RiparianBytes);
			Line(FString::Printf(TEXT("Thicket split: ring %.1f %% / riparian %.1f %% of its weight; of its %d dominant vertices %d ring, %d riparian; alone, ring dominant on %.2f %% of the off-road land, riparian on %.2f %%"),
				100.0 * RingBytes / ThicketBytes, 100.0 * RiparianBytes / ThicketBytes, ThicketDominant, ThicketVertsRing, ThicketVertsRiparian,
				100.f * RingDominant / FMath::Max(1, OffRoadVerts), 100.f * RiparianDominant / FMath::Max(1, OffRoadVerts)));
			// The rule order revised after LD1b: the riparian rule evaluated before the forest must now hold ground of its own.
			if (ThicketVertsRiparian < MinRiparianDominantVerts)
			{
				Failures.Add(FString::Printf(TEXT("riparian Thicket dominant on %d vertices (want >= %d)"), ThicketVertsRiparian, MinRiparianDominantVerts));
			}
			else
			{
				Notes.Add(FString::Printf(TEXT("riparian thicket %d dominant vertices"), ThicketVertsRiparian));
			}

			// What holds the riparian band: the off-road vertices within the section rule's distance of one of its sections
			// (by the nearest point of the route), and which biome dominates each there.
			const FGTBiomeRule* Section = Spec.Biomes.FindByPredicate([](const FGTBiomeRule& R) { return R.MaxSectionDistM > 0.f; });
			if (Section)
			{
				FBox2D Box(ForceInit);
				for (const FGTRouteSection& S : Spec.Sections)
				{
					if ((Section->SectionKinds & (1 << static_cast<int32>(S.Kind))) != 0)
					{
						for (float Arc = S.StartM; Arc <= S.EndM + 0.1f; Arc += 5.f)
						{
							float Yaw;
							Box += GTTerrain::PointOnPolyline(Spec.RouteM, FMath::Min(Arc, S.EndM), Yaw);
						}
					}
				}
				TArray<int32> BandDominant;
				BandDominant.SetNumZeroed(BiomeNames.Num());
				int32 BandVerts = 0;
				int64 BandRiparianBytes = 0;
				int64 BandOffRoadBytes = 0;
				if (Box.bIsValid)
				{
					Box = Box.ExpandBy(Section->MaxSectionDistM);
					const float MetresPerQuad = Spec.QuadSizeCm / 100.f;
					const float OriginXM = Spec.OriginXCm / 100.f;
					const float OriginYM = Spec.OriginYCm / 100.f;
					const int32 X0 = FMath::Clamp(FMath::FloorToInt((Box.Min.X - OriginXM) / MetresPerQuad), 0, Verts - 1);
					const int32 X1 = FMath::Clamp(FMath::CeilToInt((Box.Max.X - OriginXM) / MetresPerQuad), 0, Verts - 1);
					const int32 Y0 = FMath::Clamp(FMath::FloorToInt((Box.Min.Y - OriginYM) / MetresPerQuad), 0, Verts - 1);
					const int32 Y1 = FMath::Clamp(FMath::CeilToInt((Box.Max.Y - OriginYM) / MetresPerQuad), 0, Verts - 1);
					for (int32 Y = Y0; Y <= Y1; ++Y)
					{
						for (int32 X = X0; X <= X1; ++X)
						{
							const int32 Index = Y * Verts + X;
							if (PlainWeights[Ground][Index] == 0)
							{
								continue;
							}
							const FGTRouteHit Hit = GTTerrain::NearestRoute(Spec, OriginXM + X * MetresPerQuad, OriginYM + Y * MetresPerQuad);
							const FGTRouteSection* At = GTTerrain::SectionAt(Spec, Hit.ArcM);
							if (Hit.DistanceM > Section->MaxSectionDistM || !At || (Section->SectionKinds & (1 << static_cast<int32>(At->Kind))) == 0)
							{
								continue;
							}
							++BandVerts;
							BandRiparianBytes += SplitWeights[GTTerrain::LayerCount + Riparian][Index];
							BandOffRoadBytes += PlainWeights[Ground][Index];
							int32 Best = INDEX_NONE;
							int32 BestByte = 0;
							for (int32 B = 0; B < BiomeNames.Num(); ++B)
							{
								const int32 Byte = BiomeWeights[GTTerrain::LayerCount + B][Index];
								if (Byte > BestByte)
								{
									BestByte = Byte;
									Best = B;
								}
							}
							if (Best != INDEX_NONE)
							{
								++BandDominant[Best];
							}
						}
					}
				}
				FString Held;
				for (int32 B = 0; B < BiomeNames.Num(); ++B)
				{
					if (BandDominant[B] > 0)
					{
						Held += FString::Printf(TEXT(" %s %.1f %%"), *BiomeNames[B].ToString(), 100.f * BandDominant[B] / FMath::Max(1, BandVerts));
					}
				}
				Line(FString::Printf(TEXT("riparian band: %d off-road vertices within %.0f m of a section of its kinds (by the nearest route point), the riparian rule holding %.1f %% of their off-road weight; dominant there:%s"),
					BandVerts, Section->MaxSectionDistM, 100.0 * BandRiparianBytes / FMath::Max<int64>(1, BandOffRoadBytes), *Held));
			}
		}
		else
		{
			Failures.Add(TEXT("Thicket split: the split grid lacks the ring or the riparian layer"));
		}
	}
}

void FGTBiomeTestRunner::PhaseLayerAt()
{
	using namespace GTBiomeTest;
	const FGTTerrainSpec Plain = HideSpecNoBiomes();
	FGTTerrainSpec Spec = Plain;
	AddD2Palette(Spec);
	const FGTTerrainProfiles PlainProfiles = GTTerrain::BuildProfiles(Plain);
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	const int32 Verts = GTTerrain::VertsPerSide(Spec);
	const int32 Ground = FMath::Clamp(Spec.OffRoadLayer, 0, GTTerrain::LayerCount - 1);
	const float MetresPerQuad = Spec.QuadSizeCm / 100.f;
	FRandomStream Rng(20260927);
	int32 OutOfRange = 0;
	int32 Changed = 0;
	int32 Compared = 0;
	int32 Agreed = 0;
	int32 NoneOnPlain = 0;
	for (int32 Sample = 0; Sample < SamplePoints; ++Sample)
	{
		const int32 X = Rng.RandRange(0, Verts - 1);
		const int32 Y = Rng.RandRange(0, Verts - 1);
		const float XM = Spec.OriginXCm / 100.f + X * MetresPerQuad;
		const float YM = Spec.OriginYCm / 100.f + Y * MetresPerQuad;
		const int32 With = GTTerrain::LayerAt(Spec, Profiles, XM, YM);
		const int32 Without = GTTerrain::LayerAt(Plain, PlainProfiles, XM, YM);
		OutOfRange += (With < 0 || With >= GTTerrain::LayerCount) ? 1 : 0;
		Changed += With != Without ? 1 : 0;
		NoneOnPlain += GTTerrain::BiomeAt(Plain, PlainProfiles, XM, YM).IsNone() ? 0 : 1;
		const int32 Index = Y * Verts + X;
		if (BiomeWeights.Num() > GTTerrain::LayerCount && PlainWeights.Num() > Ground && PlainWeights[Ground][Index] >= 128)
		{
			int32 Best = INDEX_NONE;
			int32 BestByte = 0;
			for (int32 B = 0; B < BiomeNames.Num(); ++B)
			{
				const int32 Byte = BiomeWeights[GTTerrain::LayerCount + B][Index];
				if (Byte > BestByte)
				{
					BestByte = Byte;
					Best = B;
				}
			}
			++Compared;
			Agreed += (Best != INDEX_NONE && GTTerrain::BiomeAt(Spec, Profiles, XM, YM) == BiomeNames[Best]) ? 1 : 0;
		}
	}
	const float Agreement = Compared > 0 ? static_cast<float>(Agreed) / Compared : 0.f;
	Line(FString::Printf(TEXT("LayerAt at %d points: %d outside 0-5, %d changed by the biomes; BiomeAt on the plain spec named something at %d; BiomeAt agrees with the grid's dominant biome at %d of %d mostly off-road points (%.1f %%)"),
		SamplePoints, OutOfRange, Changed, NoneOnPlain, Agreed, Compared, 100.f * Agreement));
	if (OutOfRange > 0 || Changed > 0 || NoneOnPlain > 0)
	{
		Failures.Add(FString::Printf(TEXT("LayerAt: %d out of range, %d changed; BiomeAt named %d on the plain spec"), OutOfRange, Changed, NoneOnPlain));
	}
	if (Compared == 0 || Agreement < MinBiomeAgreement)
	{
		Failures.Add(FString::Printf(TEXT("BiomeAt agrees at %.1f %% of %d points (want %.0f %%)"), 100.f * Agreement, Compared, 100.f * MinBiomeAgreement));
	}
	// The grids are done with.
	PlainHeights.Empty();
	PlainWeights.Empty();
	BiomeWeights.Empty();
}

void FGTBiomeTestRunner::PhaseCards()
{
	using namespace GTBiomeTest;
	UWorld* W = World.Get();
	if (!W)
	{
		Failures.Add(TEXT("cards: no world"));
		return;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AGTTerrainDressing* Dressing = W->SpawnActor<AGTTerrainDressing>(AGTTerrainDressing::StaticClass(), FTransform::Identity, Params);
	if (!Dressing)
	{
		Failures.Add(TEXT("cards: could not spawn a terrain dressing"));
		return;
	}
	FGTTerrainSpec Spec = GTTerrain::ProvingSpec();
	Dressing->Rebuild(Spec);
	const int32 Plain = Dressing->FoliageCount;
	AddD2Palette(Spec);
	Dressing->Rebuild(Spec);
	const int32 WithBiomes = Dressing->FoliageCount;
	const int32 CardsWithBiomes = Dressing->Foliage ? Dressing->Foliage->GetInstanceCount() : -1;
	Dressing->Destroy();
	Line(FString::Printf(TEXT("L3 cards on the Proving spec: %d clumps without biomes, %d with the palette (%d card instances)"), Plain, WithBiomes, CardsWithBiomes));
	if (Plain <= 0 || WithBiomes != 0 || CardsWithBiomes != 0)
	{
		Failures.Add(FString::Printf(TEXT("L3 cards: %d clumps without biomes (want > 0), %d with (want 0)"), Plain, WithBiomes));
	}
	else
	{
		Notes.Add(FString::Printf(TEXT("L3 cards %d -> 0 with biomes"), Plain));
	}
}

void FGTBiomeTestRunner::PhaseExclusion()
{
	using namespace GTBiomeTest;
	UWorld* W = World.Get();
	if (!W)
	{
		Failures.Add(TEXT("exclusion: no world"));
		return;
	}
	UGTTerrainSpecAsset* Asset = LoadObject<UGTTerrainSpecAsset>(nullptr, SpecAssetPath);
	if (!Asset)
	{
		Line(TEXT("exclusion: DA_Terrain_Hide did not load; a transient asset with GTTerrain::HideSpec() stands in"));
		Asset = NewObject<UGTTerrainSpecAsset>(GetTransientPackage());
		Asset->Spec = GTTerrain::HideSpec();
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AGTDressingExclusion* Exclusion = W->SpawnActor<AGTDressingExclusion>(AGTDressingExclusion::StaticClass(), FTransform::Identity, Params);
	if (!Exclusion)
	{
		Failures.Add(TEXT("exclusion: could not spawn"));
		return;
	}
	const double Start = FPlatformTime::Seconds();
	const int32 Count = Exclusion->RebuildFromSpec(Asset);
	const double Seconds = FPlatformTime::Seconds() - Start;
	const FGTTerrainSpec& Spec = Asset->Spec;
	const float RouteM = GTTerrain::PolylineLengthM(Spec.RouteM);
	float AltM = 0.f;
	for (const FGTAltRoute& Alt : Spec.AltRoutes)
	{
		AltM += GTTerrain::PolylineLengthM(Alt.PointsM);
	}
	int32 NotQueryOnly = 0;
	int32 NotIgnoring = 0;
	int32 Shown = 0;
	float MaxHeightM = 0.f;
	float MaxGameplayM = 0.f;
	const int32 SpecBoxes = Exclusion->Boxes.Num() - Exclusion->GameplayBoxCount;
	for (int32 Index = 0; Index < Exclusion->Boxes.Num(); ++Index)
	{
		const UBoxComponent* Box = Exclusion->Boxes[Index];
		if (!Box)
		{
			continue;
		}
		NotQueryOnly += Box->GetCollisionEnabled() == ECollisionEnabled::QueryOnly ? 0 : 1;
		bool bIgnoresAll = true;
		for (int32 Channel = 0; Channel < ECC_MAX; ++Channel)
		{
			if (Box->GetCollisionResponseToChannel(static_cast<ECollisionChannel>(Channel)) != ECR_Ignore)
			{
				bIgnoresAll = false;
				break;
			}
		}
		NotIgnoring += bIgnoresAll ? 0 : 1;
		Shown += Box->bHiddenInGame ? 0 : 1;
		const float SideM = static_cast<float>(Box->GetUnscaledBoxExtent().Z) * 2.f / 100.f;
		if (Index < SpecBoxes)
		{
			MaxHeightM = FMath::Max(MaxHeightM, SideM);
		}
		else
		{
			MaxGameplayM = FMath::Max(MaxGameplayM, static_cast<float>(Box->GetUnscaledBoxExtent().GetMax()) * 2.f / 100.f);
		}
	}
	const bool bTagged = Exclusion->Tags.Contains(AGTDressingExclusion::ExcludeTag);
	const bool bEditorOnly = Exclusion->IsEditorOnly();
	Line(FString::Printf(TEXT("exclusion: %s (%.2f s)"), *Exclusion->LastMessage, Seconds));
	Line(FString::Printf(TEXT("exclusion: %d boxes; covered main %.1f of %.1f m, alt %.1f of %.1f m (%d alt route(s)); not QueryOnly %d, not ignoring every channel %d, shown in game %d; tallest spec box %.1f m, largest gameplay box side %.1f m; tagged %s, editor-only %s"),
		Count, Exclusion->CoveredRouteM, RouteM, Exclusion->CoveredAltM, AltM, Spec.AltRoutes.Num(), NotQueryOnly, NotIgnoring, Shown, MaxHeightM, MaxGameplayM,
		bTagged ? TEXT("yes") : TEXT("NO"), bEditorOnly ? TEXT("yes") : TEXT("NO")));
	const int32 ExpectedRouteBoxes = FMath::CeilToInt(RouteM / FMath::Max(1.f, Exclusion->RouteBoxLengthM));
	if (Count <= 0 || Exclusion->RouteBoxCount != ExpectedRouteBoxes || FMath::Abs(Exclusion->CoveredRouteM - RouteM) > 0.5f || FMath::Abs(Exclusion->CoveredAltM - AltM) > 0.5f
		|| NotQueryOnly > 0 || NotIgnoring > 0 || Shown > 0 || !bTagged || !bEditorOnly)
	{
		Failures.Add(FString::Printf(TEXT("exclusion: %d boxes (route %d, want %d), covered %.1f/%.1f m main %.1f/%.1f m alt, bad collision %d/%d, shown %d, tagged %d, editor-only %d"),
			Count, Exclusion->RouteBoxCount, ExpectedRouteBoxes, Exclusion->CoveredRouteM, RouteM, Exclusion->CoveredAltM, AltM, NotQueryOnly, NotIgnoring, Shown, bTagged ? 1 : 0, bEditorOnly ? 1 : 0));
	}
	else
	{
		Notes.Add(FString::Printf(TEXT("exclusion %d boxes over %.0f m of route + %.0f m alt"), Count, Exclusion->CoveredRouteM, Exclusion->CoveredAltM));
	}
	Exclusion->Destroy();
}

void FGTBiomeTestRunner::PhaseWind()
{
	using namespace GTBiomeTest;
	UWorld* W = World.Get();
	UGTWeatherSubsystem* Weather = W ? W->GetSubsystem<UGTWeatherSubsystem>() : nullptr;
	if (!Weather || !Weather->HasGlobalWind())
	{
		Failures.Add(FString::Printf(TEXT("wind: %s"), Weather ? TEXT("MPC_GlobalWind did not load") : TEXT("no weather subsystem")));
		return;
	}
	float Live = -1.f;
	float Default = -1.f;
	const bool bRead = Weather->ReadGlobalWindScalar(UGTWeatherSubsystem::GlobalWindParamIntensity, Live, &Default);
	const UGTWeatherStateDefinition* Clear = Weather->FindState(TEXT("Clear"));
	const float ClearWind = Clear ? Clear->Values.WindStrength : -1.f;
	const float Scale = Weather->GlobalWindIntensityPerStrength;
	const float Now = Weather->GetCurrent().WindStrength;
	Line(FString::Printf(TEXT("wind: MPC_GlobalWind WindIntensity default %.3f; Clear WindStrength %.3f x %.2f = %.3f; now %s WindStrength %.3f -> the collection reads %.3f (want %.3f)"),
		Default, ClearWind, Scale, ClearWind * Scale, *Weather->GetStateName(), Now, Live, Now * Scale));
	if (!bRead || !Clear || FMath::Abs(ClearWind * Scale - Default) > 1.e-3f || FMath::Abs(Live - Now * Scale) > 1.e-3f)
	{
		Failures.Add(FString::Printf(TEXT("wind: Clear %.3f x %.2f = %.3f vs default %.3f; live %.3f vs %.3f"), ClearWind, Scale, ClearWind * Scale, Default, Live, Now * Scale));
	}
	else
	{
		Notes.Add(FString::Printf(TEXT("wind Clear %.2f -> %.2f (x %.1f)"), ClearWind, Default, Scale));
	}
}

void FGTBiomeTestRunner::PhaseDressingOff()
{
	using namespace GTBiomeTest;
	UWorld* W = World.Get();
	if (!W)
	{
		Failures.Add(TEXT("dressing: no world"));
		return;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	auto Spawn = [&](const FVector& At, const TCHAR* Tag) -> AActor*
	{
		AStaticMeshActor* Probe = W->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform(At), Params);
		if (Probe)
		{
			Probe->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
			Probe->GetStaticMeshComponent()->SetStaticMesh(Cube);
			Probe->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
			Probe->Tags.Add(FName(Tag));
		}
		return Probe;
	};
	AActor* Shown = Spawn(FVector(0.f, 0.f, -100000.f), TEXT("GTBiome.TestProbe"));
	AActor* Hidden = Spawn(FVector(500.f, 0.f, -100000.f), TEXT("OWBiome.TestProbe"));
	if (!Shown || !Hidden)
	{
		Failures.Add(TEXT("dressing: could not spawn the probes"));
		return;
	}
	Hidden->SetActorHiddenInGame(true);
	Hidden->SetActorEnableCollision(false);
	ProbeShown = Shown;
	ProbeHidden = Hidden;
	SetCvar(TEXT("gt.Look.Dressing"), 0);
	Line(FString::Printf(TEXT("dressing: two probes (GTBiome.TestProbe shown and solid, OWBiome.TestProbe hidden without collision); gt.Look.Dressing 0; grass.Enable %d before"), GetCvar(TEXT("grass.Enable"))));
}

void FGTBiomeTestRunner::PhaseDressingOn()
{
	using namespace GTBiomeTest;
	const AActor* Shown = ProbeShown.Get();
	const AActor* Hidden = ProbeHidden.Get();
	const int32 Grass = GetCvar(TEXT("grass.Enable"));
	const bool bOff = Shown && Shown->IsHidden() && !Shown->GetActorEnableCollision() && Hidden && Hidden->IsHidden() && !Hidden->GetActorEnableCollision() && Grass == 0;
	Line(FString::Printf(TEXT("dressing 0: probe hidden %d collision %d, hidden probe hidden %d collision %d, grass.Enable %d, UGTLookSubsystem::IsBiomeDressing %d"),
		Shown ? (Shown->IsHidden() ? 1 : 0) : -1, Shown ? (Shown->GetActorEnableCollision() ? 1 : 0) : -1,
		Hidden ? (Hidden->IsHidden() ? 1 : 0) : -1, Hidden ? (Hidden->GetActorEnableCollision() ? 1 : 0) : -1, Grass, UGTLookSubsystem::IsBiomeDressing(Shown) ? 1 : 0));
	if (!bOff)
	{
		Failures.Add(FString::Printf(TEXT("gt.Look.Dressing 0 did not hide the probes / take their collision / set grass.Enable 0 (grass %d)"), Grass));
	}
	SetCvar(TEXT("gt.Look.Dressing"), 1);
}

void FGTBiomeTestRunner::PhaseDressingRestored()
{
	using namespace GTBiomeTest;
	AActor* Shown = ProbeShown.Get();
	AActor* Hidden = ProbeHidden.Get();
	const int32 Grass = GetCvar(TEXT("grass.Enable"));
	const bool bOn = Shown && !Shown->IsHidden() && Shown->GetActorEnableCollision() && Hidden && Hidden->IsHidden() && !Hidden->GetActorEnableCollision() && Grass == 1;
	Line(FString::Printf(TEXT("dressing 1: probe hidden %d collision %d, hidden probe hidden %d collision %d (its own state), grass.Enable %d"),
		Shown ? (Shown->IsHidden() ? 1 : 0) : -1, Shown ? (Shown->GetActorEnableCollision() ? 1 : 0) : -1,
		Hidden ? (Hidden->IsHidden() ? 1 : 0) : -1, Hidden ? (Hidden->GetActorEnableCollision() ? 1 : 0) : -1, Grass));
	if (!bOn)
	{
		Failures.Add(FString::Printf(TEXT("gt.Look.Dressing 1 did not put the probes' own states back / set grass.Enable 1 (grass %d)"), Grass));
	}
	else
	{
		Notes.Add(TEXT("gt.Look.Dressing 0/1 ok"));
	}
	if (Shown)
	{
		Shown->Destroy();
	}
	if (Hidden)
	{
		Hidden->Destroy();
	}
}
