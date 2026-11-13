#include "OWBedStampComponent.h"

#include "Engine/Texture2D.h"
#include "Math/Float16.h"
#include "UObject/ObjectMacros.h"

#if WITH_EDITOR
#include "TextureResource.h"
#endif

namespace OWBedStampLocals
{
	/** Texel of the generated stamp texture. RGBA16F: R = encoded height, A = patch alpha. */
	struct FStampTexel
	{
		FFloat16 R;
		FFloat16 G;
		FFloat16 B;
		FFloat16 A;
	};

	/** Height encoding: value 0.5 == stamp Z, full [0,1] range == +/-1000 cm relative to stamp Z. */
	static constexpr double HeightZeroInEncoding = 0.5;
	static constexpr double HeightWorldSpaceEncodingScale = 2000.0;
	static constexpr float HeightHalfRangeCm = 1000.f;

	/** World cm per stamp texel, and the resolution clamp per axis. */
	static constexpr float CmPerTexel = 50.f;
	static constexpr int32 MinResolution = 16;
	static constexpr int32 MaxResolution = 512;

	/** Extra margin so alpha is guaranteed to reach 0 before the texture border. */
	static constexpr float BorderPadCm = 100.f;

	static float SmoothStep01(float T)
	{
		T = FMath::Clamp(T, 0.f, 1.f);
		return T * T * (3.f - 2.f * T);
	}

	static FFloat16 EncodeHeight(float HeightCm)
	{
		const float Clamped = FMath::Clamp(HeightCm, -HeightHalfRangeCm, HeightHalfRangeCm);
		return FFloat16(static_cast<float>((Clamped / HeightWorldSpaceEncodingScale) + HeightZeroInEncoding));
	}
}

UOWBedStampComponent::UOWBedStampComponent(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	// C3: stamps never tick.
	PrimaryComponentTick.bCanEverTick = false;
	PrimaryComponentTick.bStartWithTickEnabled = false;

	// Set the inherited (protected) patch settings directly rather than through the
	// setters: the setters call Modify(), which is not something we want to do while
	// constructing the CDO.

	// C7: cut-only by default. The user can flip this in Details (Settings > Blend Mode).
	BlendMode = ELandscapeTexturePatchBlendMode::Min;

	// All falloff is baked into the alpha channel of the generated texture, so the
	// patch's own falloff must be off or it would double-feather the edges.
	Falloff = 0.f;
	FalloffMode = ELandscapeTexturePatchFalloffMode::RoundedRectangle;

	// Height comes from the generated texture asset, red channel, [0,1] encoded.
	HeightSourceMode = ELandscapeTexturePatchSourceMode::TextureAsset;
	DetailPanelHeightSourceMode = ELandscapeTexturePatchSourceMode::TextureAsset;
	HeightTextureChannel = ELandscapeTexturePatchTextureChannel::Red;
	HeightEncoding = ELandscapeTextureHeightPatchEncoding::ZeroToOne;
	HeightEncodingSettings.ZeroInEncoding = OWBedStampLocals::HeightZeroInEncoding;
	HeightEncodingSettings.WorldSpaceEncodingScale = OWBedStampLocals::HeightWorldSpaceEncodingScale;

	// Heights move with the stamp actor - dragging the stamp up/down moves the cut.
	ZeroHeightMeaning = ELandscapeTextureHeightPatchZeroHeightMeaning::PatchZ;

	// Alpha mask comes from the alpha channel of the same generated texture.
	// FLandscapeTexturePatchAlphaSettings::SetAlphaSourceMode is not DLL-exported, so
	// go through the patch's exported wrapper. In a CDO it takes the IsTemplate() path
	// (no allocation); on an instance the Modify() inside is a no-op while the object
	// still has RF_NeedInitialization.
	HeightAlphaSettings.AlphaTextureChannel = ELandscapeTexturePatchTextureChannel::Alpha;
	SetHeightAlphaSourceMode(ELandscapeTexturePatchAlphaSourceMode::SourceTextureChannel, /*bAlwaysMarkDirty=*/false);
}

#if WITH_EDITOR

void UOWBedStampComponent::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);

	// Cheap enough to always rebuild: the stamp textures are at most 512x512.
	RebuildStamp();
}

void UOWBedStampComponent::PostLoad()
{
	Super::PostLoad();

	if (!StampTexture)
	{
		RebuildStamp();
	}
}

void UOWBedStampComponent::OnRegister()
{
	Super::OnRegister();

	if (!StampTexture)
	{
		RebuildStamp();
	}
}

void UOWBedStampComponent::RebuildStamp()
{
	using namespace OWBedStampLocals;

	// Never allocate textures on the CDO / blueprint archetypes.
	if (IsTemplate())
	{
		return;
	}

	const float Shoulder = FMath::Max(ShoulderFalloffCm, 1.f);

	// 1. Coverage (world cm at scale 1.0, measured between outermost texel centers).
	FVector2D Coverage(FVector2D::ZeroVector);
	switch (Shape)
	{
	case EOWBedStampShape::Pool:
	{
		const float Extent = 2.f * (RadiusCm + Shoulder);
		Coverage = FVector2D(Extent, Extent);
		break;
	}
	case EOWBedStampShape::Step:
		Coverage = FVector2D(LengthCm, 2.f * (StepWidthCm * 0.5f + Shoulder + BorderPadCm));
		break;
	case EOWBedStampShape::Bench:
		Coverage = FVector2D(LengthCm, 2.f * (BenchHalfWidthCm + Shoulder + BorderPadCm));
		break;
	case EOWBedStampShape::Channel:
	default:
		Coverage = FVector2D(LengthCm, 2.f * (BedHalfWidthCm + Shoulder + BorderPadCm));
		break;
	}

	// 2. Resolution: roughly one texel per 50 cm of coverage.
	const int32 ResX = FMath::Clamp(FMath::CeilToInt(Coverage.X / CmPerTexel) + 1, MinResolution, MaxResolution);
	const int32 ResY = FMath::Clamp(FMath::CeilToInt(Coverage.Y / CmPerTexel) + 1, MinResolution, MaxResolution);

	// 3. Evaluate the profile into an RGBA16F texel array.
	TArray<FStampTexel> Texels;
	Texels.SetNumUninitialized(ResX * ResY);

	const float HalfCoverageX = static_cast<float>(Coverage.X) * 0.5f;
	const float HalfCoverageY = static_cast<float>(Coverage.Y) * 0.5f;
	const float StepX = (ResX > 1) ? (static_cast<float>(Coverage.X) / static_cast<float>(ResX - 1)) : 0.f;
	const float StepY = (ResY > 1) ? (static_cast<float>(Coverage.Y) / static_cast<float>(ResY - 1)) : 0.f;

	const bool bUseEndFeather = (EndFeatherCm > 1.f);

	for (int32 IndexY = 0; IndexY < ResY; ++IndexY)
	{
		const float LocalY = -HalfCoverageY + StepY * static_cast<float>(IndexY);

		for (int32 IndexX = 0; IndexX < ResX; ++IndexX)
		{
			const float LocalX = -HalfCoverageX + StepX * static_cast<float>(IndexX);

			float HeightCm = 0.f;
			float Alpha = 0.f;
			bool bApplyEndFeather = true;

			switch (Shape)
			{
			case EOWBedStampShape::Pool:
			{
				bApplyEndFeather = false;
				const float Radius = FMath::Sqrt(LocalX * LocalX + LocalY * LocalY);
				const float FloorRadius = FMath::Max(RadiusCm - Shoulder, 0.f);
				if (Radius <= FloorRadius)
				{
					HeightCm = -DepthCm;
					Alpha = 1.f;
				}
				else if (Radius <= RadiusCm)
				{
					const float Band = FMath::Max(RadiusCm - FloorRadius, 1.f);
					const float T = SmoothStep01((Radius - FloorRadius) / Band);
					HeightCm = FMath::Lerp(-DepthCm, HeadroomCm, T);
					Alpha = 1.f - T;
				}
				else
				{
					HeightCm = HeadroomCm;
					Alpha = 0.f;
				}
				break;
			}
			case EOWBedStampShape::Step:
			{
				const float HalfLip = FMath::Max(LipSharpnessCm, 1.f) * 0.5f;
				if (LocalX < -HalfLip)
				{
					HeightCm = 0.f;
				}
				else if (LocalX > HalfLip)
				{
					HeightCm = -DropCm;
				}
				else
				{
					const float T = SmoothStep01((LocalX + HalfLip) / (2.f * HalfLip));
					HeightCm = FMath::Lerp(0.f, -DropCm, T);
				}

				const float DistY = FMath::Abs(LocalY);
				const float HalfWidth = StepWidthCm * 0.5f;
				if (DistY <= HalfWidth)
				{
					Alpha = 1.f;
				}
				else if (DistY <= HalfWidth + Shoulder)
				{
					Alpha = 1.f - SmoothStep01((DistY - HalfWidth) / Shoulder);
				}
				else
				{
					Alpha = 0.f;
				}
				break;
			}
			case EOWBedStampShape::Bench:
			{
				if (LocalY <= 0.f)
				{
					// The shelf itself, flat at stamp Z.
					HeightCm = 0.f;
					if (LocalY >= -BenchHalfWidthCm)
					{
						Alpha = 1.f;
					}
					else
					{
						Alpha = 1.f - SmoothStep01(((-LocalY) - BenchHalfWidthCm) / Shoulder);
					}
				}
				else if (LocalY <= Shoulder)
				{
					// Back wall: daylight up into the hillside at full strength.
					const float T = SmoothStep01(LocalY / Shoulder);
					HeightCm = FMath::Lerp(0.f, HeadroomCm, T);
					Alpha = 1.f;
				}
				else
				{
					HeightCm = HeadroomCm;
					Alpha = 0.f;
				}
				break;
			}
			case EOWBedStampShape::Channel:
			default:
			{
				const float DistY = FMath::Abs(LocalY);
				if (DistY <= BedHalfWidthCm)
				{
					HeightCm = -DepthCm;
					Alpha = 1.f;
				}
				else if (DistY <= BedHalfWidthCm + Shoulder)
				{
					const float T = SmoothStep01((DistY - BedHalfWidthCm) / Shoulder);
					HeightCm = FMath::Lerp(-DepthCm, HeadroomCm, T);
					Alpha = 1.f - T;
				}
				else
				{
					HeightCm = HeadroomCm;
					Alpha = 0.f;
				}
				break;
			}
			}

			if (bApplyEndFeather && bUseEndFeather)
			{
				Alpha *= SmoothStep01((HalfCoverageX - FMath::Abs(LocalX)) / EndFeatherCm);
			}

			FStampTexel& Texel = Texels[IndexY * ResX + IndexX];
			Texel.R = EncodeHeight(HeightCm);
			Texel.G = Texel.R;
			Texel.B = Texel.R;
			Texel.A = FFloat16(FMath::Clamp(Alpha, 0.f, 1.f));
		}
	}

	// 4. Create / refill the stamp texture.
	if (!StampTexture)
	{
		StampTexture = NewObject<UTexture2D>(this, NAME_None, RF_Transactional);
		StampTexture->SRGB = false;
		StampTexture->MipGenSettings = TMGS_NoMipmaps;
		StampTexture->AddressX = TA_Clamp;
		StampTexture->AddressY = TA_Clamp;
		// Uncompressed 16-bit float RGBA: DXT would destroy both the height ramp
		// and the alpha feather.
		StampTexture->CompressionNone = true;
		StampTexture->CompressionSettings = TC_HDR;
		// Avoid a DDC rebuild request per regeneration of an identical texture.
		StampTexture->Source.UseHashAsGuid();
	}

	StampTexture->Modify();
	StampTexture->Source.Init(ResX, ResY, 1, 1, ETextureSourceFormat::TSF_RGBA16F, reinterpret_cast<const uint8*>(Texels.GetData()));
	StampTexture->UpdateResource();

	// 5. Push coverage / resolution / texture onto the patch and ask for a re-render.
	SetUnscaledCoverage(Coverage);
	SetResolution(FVector2D(ResX, ResY));
	SetHeightTextureAsset(StampTexture);

	RequestLandscapeUpdate();
}

#endif // WITH_EDITOR
