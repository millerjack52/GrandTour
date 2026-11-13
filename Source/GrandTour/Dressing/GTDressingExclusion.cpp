#include "Dressing/GTDressingExclusion.h"

#include "Harvest/GTHarvestNode.h"

#include "Interaction/GTInteractable.h"
#include "Interaction/GTInteractionComponent.h"
#include "Run/GTLegActors.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"

#include "Components/BoxComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "LandscapeProxy.h"

const FName AGTDressingExclusion::ExcludeTag(TEXT("OWDressing.Exclude"));

namespace
{
	/** The lowest and highest ground, m, over an oriented rectangle (a 3 x 3 grid of it) or an axis-aligned box (5 x 5). */
	void GroundSpan(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, const FVector2D& CentreM, const FVector2D& AxisM, const FVector2D& SideM, int32 Grid, float& InOutMin, float& InOutMax)
	{
		for (int32 I = 0; I < Grid; ++I)
		{
			for (int32 J = 0; J < Grid; ++J)
			{
				const float U = Grid > 1 ? 2.f * I / (Grid - 1) - 1.f : 0.f;
				const float V = Grid > 1 ? 2.f * J / (Grid - 1) - 1.f : 0.f;
				const FVector2D P = CentreM + AxisM * U + SideM * V;
				const float H = GTTerrain::HeightM(Spec, Profiles, static_cast<float>(P.X), static_cast<float>(P.Y));
				InOutMin = FMath::Min(InOutMin, H);
				InOutMax = FMath::Max(InOutMax, H);
			}
		}
	}
}

AGTDressingExclusion::AGTDressingExclusion()
{
	PrimaryActorTick.bCanEverTick = false;
	bIsEditorOnlyActor = true;
	SetCanBeDamaged(false);
	Tags.Add(ExcludeTag);
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Static);
	SetRootComponent(Root);
	GameplayLabelPrefixes = { TEXT("Hide_"), TEXT("Roof_"), TEXT("Marker_"), TEXT("Water_") };
}

void AGTDressingExclusion::BeginPlay()
{
	Super::BeginPlay();
	int32 Disabled = 0;
	for (UBoxComponent* Box : Boxes)
	{
		if (Box)
		{
			Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			++Disabled;
		}
	}
	if (Disabled > 0)
	{
		UE_LOG(LogTemp, Display, TEXT("AGTDressingExclusion: %d boxes set to NoCollision for play (the actor is editor-only; uncooked play loads it)"), Disabled);
	}
}

void AGTDressingExclusion::Rebuild()
{
	RebuildFromSpec(SpecAsset);
}

void AGTDressingExclusion::ClearBoxes()
{
	for (UBoxComponent* Box : Boxes)
	{
		if (Box)
		{
			RemoveInstanceComponent(Box);
			Box->DestroyComponent();
		}
	}
	Boxes.Reset();
}

UBoxComponent* AGTDressingExclusion::AddBox(const FVector& CentreCm, const FRotator& Rotation, const FVector& HalfExtentCm)
{
	UBoxComponent* Box = NewObject<UBoxComponent>(this, NAME_None, RF_Transactional);
	Box->SetMobility(EComponentMobility::Static);
	Box->SetupAttachment(GetRootComponent());
	// QueryOnly so the box has a body (PCG's UPCGPrimitiveData tests points with OverlapComponent), every channel
	// ignored so no trace, sweep or overlap in a game ever meets it.
	Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Box->SetCollisionObjectType(ECC_WorldStatic);
	Box->SetCollisionResponseToAllChannels(ECR_Ignore);
	Box->SetGenerateOverlapEvents(false);
	Box->SetCanEverAffectNavigation(false);
	Box->SetHiddenInGame(true);
	Box->ShapeColor = FColor(255, 140, 0);
	Box->SetBoxExtent(HalfExtentCm, /*bUpdateOverlaps*/ false);
	Box->SetRelativeTransform(FTransform(Rotation, CentreCm).GetRelativeTransform(GetActorTransform()));
	AddInstanceComponent(Box);
	Box->RegisterComponent();
	Boxes.Add(Box);
	return Box;
}

int32 AGTDressingExclusion::RebuildFromSpec(UGTTerrainSpecAsset* InSpecAsset)
{
	if (InSpecAsset)
	{
		SpecAsset = InSpecAsset;
	}
	Modify();
	ClearBoxes();
	RouteBoxCount = AltBoxCount = SectionBoxCount = PatchBoxCount = GameplayBoxCount = 0;
	CoveredRouteM = CoveredAltM = 0.f;
	if (!SpecAsset)
	{
		LastMessage = TEXT("no spec asset: no boxes");
		UE_LOG(LogTemp, Warning, TEXT("AGTDressingExclusion: %s"), *LastMessage);
		return 0;
	}
	const FGTTerrainSpec& Spec = SpecAsset->Spec;
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	const float Step = FMath::Max(1.f, RouteBoxLengthM);
	const float MinHeightM = FMath::Max(1.f, RouteBoxHeightM);

	// A line's boxes: one per Step of arc, on the chord from its start to its end, as wide as the line there plus the
	// clear ground plus the arc's sag off the chord, and longer at both ends by a metre plus what the line's turn over the
	// box opens on the outside of a bend, so neighbours overlap round bends.
	auto LineBoxes = [&](const TArray<FVector2D>& PointsM, TFunctionRef<float(float)> HalfWidthAtM, float& OutCoveredM) -> int32
	{
		const float LengthM = GTTerrain::PolylineLengthM(PointsM);
		if (PointsM.Num() < 2 || LengthM <= 0.f)
		{
			return 0;
		}
		int32 Made = 0;
		const int32 Count = FMath::CeilToInt(LengthM / Step);
		for (int32 Index = 0; Index < Count; ++Index)
		{
			const float A = Index * Step;
			const float B = FMath::Min(LengthM, A + Step);
			if (B - A < 0.01f)
			{
				continue;
			}
			float YawA = 0.f, YawB = 0.f, YawMid = 0.f;
			const FVector2D PA = GTTerrain::PointOnPolyline(PointsM, A, YawA);
			const FVector2D PB = GTTerrain::PointOnPolyline(PointsM, B, YawB);
			const FVector2D PM = GTTerrain::PointOnPolyline(PointsM, 0.5f * (A + B), YawMid);
			const FVector2D Chord = PB - PA;
			const float ChordM = static_cast<float>(Chord.Size());
			const FVector2D Dir = ChordM > 0.01f ? Chord / ChordM : FVector2D(FMath::Cos(FMath::DegreesToRadians(YawMid)), FMath::Sin(FMath::DegreesToRadians(YawMid)));
			const FVector2D Left(-Dir.Y, Dir.X);
			const FVector2D Centre = 0.5f * (PA + PB);
			const float Sag = static_cast<float>(FVector2D::Distance(PM, Centre));
			const float HalfWidth = FMath::Max3(HalfWidthAtM(A), HalfWidthAtM(0.5f * (A + B)), HalfWidthAtM(B)) + RouteClearM + Sag;
			const float Turn = FMath::DegreesToRadians(FMath::Min(90.f, FMath::Abs(FMath::FindDeltaAngleDegrees(YawA, YawB))));
			const float HalfLength = 0.5f * ChordM + 1.f + HalfWidth * FMath::Sin(Turn);
			float Low = 1.e9f, High = -1.e9f;
			GroundSpan(Spec, Profiles, Centre, Dir * HalfLength, Left * HalfWidth, 3, Low, High);
			const float Bottom = Low - 2.f;
			const float Top = FMath::Max(High + 2.f, Bottom + MinHeightM);
			AddBox(FVector(Centre.X * 100.f, Centre.Y * 100.f, 50.f * (Bottom + Top)), FRotator(0.f, FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X)), 0.f),
				FVector(HalfLength * 100.f, HalfWidth * 100.f, 50.f * (Top - Bottom)));
			OutCoveredM += B - A;
			++Made;
		}
		return Made;
	};

	// An axis-aligned box (world metres) over the ground inside it.
	auto GroundBox = [&](const FBox2D& BoxM)
	{
		float Low = 1.e9f, High = -1.e9f;
		const FVector2D Centre = BoxM.GetCenter();
		const FVector2D Half = BoxM.GetExtent();
		GroundSpan(Spec, Profiles, Centre, FVector2D(Half.X, 0.f), FVector2D(0.f, Half.Y), 5, Low, High);
		const float Bottom = Low - 2.f;
		const float Top = FMath::Max(High + 2.f, Bottom + MinHeightM);
		AddBox(FVector(Centre.X * 100.f, Centre.Y * 100.f, 50.f * (Bottom + Top)), FRotator::ZeroRotator, FVector(Half.X * 100.f, Half.Y * 100.f, 50.f * (Top - Bottom)));
	};

	// 1. The main route and the alt routes.
	RouteBoxCount = LineBoxes(Spec.RouteM, [&Spec](float ArcM) { return GTTerrain::HalfWidthAt(Spec, ArcM); }, CoveredRouteM);
	for (const FGTAltRoute& Alt : Spec.AltRoutes)
	{
		const float AltHalf = Alt.HalfWidthM;
		AltBoxCount += LineBoxes(Alt.PointsM, [AltHalf](float) { return AltHalf; }, CoveredAltM);
	}

	// 2. Mud and Ford sections, their extent plus SectionMarginM; then every mud patch and deform patch box plus PatchMarginM.
	for (const FGTRouteSection& Section : Spec.Sections)
	{
		if (Section.Kind != EGTRouteSectionKind::Mud && Section.Kind != EGTRouteSectionKind::Ford)
		{
			continue;
		}
		FBox2D Extent(ForceInit);
		for (float Arc = Section.StartM; Arc <= Section.EndM + 0.01f; Arc += 2.f)
		{
			float Yaw = 0.f;
			const FVector2D P = GTTerrain::PointOnPolyline(Spec.RouteM, FMath::Min(Arc, Section.EndM), Yaw);
			const float Reach = GTTerrain::HalfWidthAt(Spec, FMath::Min(Arc, Section.EndM)) + SectionMarginM;
			Extent += FBox2D(P - FVector2D(Reach, Reach), P + FVector2D(Reach, Reach));
		}
		if (Extent.bIsValid)
		{
			GroundBox(Extent);
			++SectionBoxCount;
		}
	}
	for (int32 Index = 0; Index < Spec.Sections.Num(); ++Index)
	{
		FBox2D BoxCm(ForceInit);
		if (GTTerrain::MudPatchBoxCm(Spec, Index, BoxCm))
		{
			GroundBox(FBox2D(BoxCm.Min / 100.f, BoxCm.Max / 100.f).ExpandBy(PatchMarginM));
			++PatchBoxCount;
		}
		if (GTTerrain::DeformPatchBoxCm(Spec, Index, BoxCm))
		{
			GroundBox(FBox2D(BoxCm.Min / 100.f, BoxCm.Max / 100.f).ExpandBy(PatchMarginM));
			++PatchBoxCount;
		}
	}

	// 3. The gameplay actors in this world now, their bounds plus GameplayMarginM.
	FString Largest;
	float LargestM = 0.f;
	if (UWorld* World = GetWorld())
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			AActor* Actor = *It;
			if (!Actor || Actor == this || Actor->IsA<AGTDressingExclusion>() || Actor->IsA<ALandscapeProxy>())
			{
				continue;
			}
			bool bGameplay = Actor->IsA<AGTLegStart>() || Actor->IsA<AGTCheckpoint>() || Actor->IsA<AGTExtractionZone>()
				|| Actor->GetClass()->ImplementsInterface(UGTInteractable::StaticClass()) || Actor->FindComponentByClass<UGTInteractionComponent>() != nullptr;
			if (!bGameplay)
			{
#if WITH_EDITOR
				const FString Label = Actor->GetActorLabel();
#else
				const FString Label = Actor->GetName();
#endif
				for (const FString& Prefix : GameplayLabelPrefixes)
				{
					if (!Prefix.IsEmpty() && Label.StartsWith(Prefix))
					{
						bGameplay = true;
						break;
					}
				}
			}
			if (!bGameplay)
			{
				continue;
			}
			// The colliding components' bounds (a node's mesh, a zone's trigger), else every component's (a marker without
			// collision), else the actor's location: a helper with huge bounds (a spray system, a cable) never widens it.
			// LD6 (2026-09-27): a component with empty bounds is left out - AGTWaterSheet's SurfaceMesh uses absolute
			// location and has no sections in the editor, so its zero box sat at the world origin and the ford sheet's box
			// grew to 1055 x 82 m (the origin to the ford), clearing the dressing off the first kilometre of The Hide.
			auto BoundsOf = [Actor](bool bNonColliding)
			{
				FBox Box(ForceInit);
				TInlineComponentArray<UPrimitiveComponent*> Prims;
				Actor->GetComponents(Prims, /*bIncludeFromChildActors*/ true);
				for (const UPrimitiveComponent* Prim : Prims)
				{
					if (Prim && Prim->IsRegistered() && (bNonColliding || Prim->IsCollisionEnabled()) && Prim->Bounds.BoxExtent.GetMax() > 1.0)
					{
						Box += Prim->Bounds.GetBox();
					}
				}
				return Box;
			};
			// LD7 (2026-09-27, the route clearance test): the leg volumes and the harvest nodes are sized at BeginPlay - a
			// checkpoint's box from Extent (3 x 24 m, the editor holds the 64 cm default), a node's cube from GreyboxSize
			// (a wreck 3.2 x 1.6 m, the editor holds the 1 m cube) - so their game size is used, not the editor's.
			FBox Bounds(ForceInit);
			const FTransform Placement(Actor->GetActorRotation(), Actor->GetActorLocation());
			if (const AGTLegVolume* LegVolume = Cast<AGTLegVolume>(Actor))
			{
				Bounds = FBox(-LegVolume->Extent, LegVolume->Extent).TransformBy(Placement);
			}
			else if (const AGTHarvestNode* Node = Cast<AGTHarvestNode>(Actor))
			{
				const FVector Half = Node->GreyboxSize * 0.5f;
				Bounds = FBox(-Half, Half).TransformBy(Placement);
			}
			if (!Bounds.IsValid)
			{
				Bounds = BoundsOf(/*bNonColliding*/ false);
			}
			if (!Bounds.IsValid)
			{
				Bounds = BoundsOf(/*bNonColliding*/ true);
			}
			if (!Bounds.IsValid)
			{
				Bounds = FBox(Actor->GetActorLocation(), Actor->GetActorLocation());
			}
			Bounds = Bounds.ExpandBy(GameplayMarginM * 100.f);
			AddBox(Bounds.GetCenter(), FRotator::ZeroRotator, Bounds.GetExtent());
			++GameplayBoxCount;
			const float SizeM = static_cast<float>(Bounds.GetSize().GetMax()) / 100.f;
			if (SizeM > LargestM)
			{
				LargestM = SizeM;
				Largest = Actor->GetName();
			}
		}
	}

	LastMessage = FString::Printf(TEXT("%d boxes from %s: main route %d (%.0f m of %.0f), alt routes %d (%.0f m), Mud/Ford sections %d, patches %d, gameplay %d (largest %s, %.0f m on its longest side)"),
		Boxes.Num(), *SpecAsset->GetName(), RouteBoxCount, CoveredRouteM, GTTerrain::PolylineLengthM(Spec.RouteM), AltBoxCount, CoveredAltM, SectionBoxCount, PatchBoxCount,
		GameplayBoxCount, Largest.IsEmpty() ? TEXT("none") : *Largest, LargestM);
	UE_LOG(LogTemp, Display, TEXT("AGTDressingExclusion: %s"), *LastMessage);
	return Boxes.Num();
}
