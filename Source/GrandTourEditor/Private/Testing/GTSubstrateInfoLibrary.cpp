#include "GTSubstrateInfoLibrary.h"

#include "MaterialShared.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "RenderUtils.h"
#include "RHIShaderPlatform.h"
#include "Rendering/SubstrateMaterialShared.h"

FString UGTSubstrateInfoLibrary::GetSubstrateMaterialInfo(UMaterialInterface* Material)
{
	UMaterial* Base = Material ? Material->GetMaterial() : nullptr;
	if (!Base)
	{
		return TEXT("no material");
	}
	if (!Substrate::IsSubstrateEnabled())
	{
		return FString::Printf(TEXT("%s: Substrate off"), *Base->GetName());
	}
	const FMaterialResource* Resource = Base->GetMaterialResource(GMaxRHIShaderPlatform);
	const FMaterialShaderMap* Map = Resource ? Resource->GetGameThreadShaderMap() : nullptr;
	if (!Map)
	{
		return FString::Printf(TEXT("%s: not compiled for the editor's shader platform"), *Base->GetName());
	}
	const FSubstrateMaterialCompilationOutput& Out = Map->GetSubstrateMaterialCompilationOutput();
	const ESubstrateBsdfFeature Features = ESubstrateBsdfFeature(Out.SubstrateMaterialBsdfFeatures);
	FString FeatureText;
	const TPair<ESubstrateBsdfFeature, const TCHAR*> Names[] = {
		{ ESubstrateBsdfFeature::SSS, TEXT("SSS") }, { ESubstrateBsdfFeature::MFPPluggedIn, TEXT("MFPPluggedIn") },
		{ ESubstrateBsdfFeature::EdgeColor, TEXT("EdgeColor") }, { ESubstrateBsdfFeature::Fuzz, TEXT("Fuzz") },
		{ ESubstrateBsdfFeature::SecondRoughnessOrSimpleClearCoat, TEXT("SecondRoughnessOrSimpleClearCoat") },
		{ ESubstrateBsdfFeature::Anisotropy, TEXT("Anisotropy") }, { ESubstrateBsdfFeature::Glint, TEXT("Glint") },
		{ ESubstrateBsdfFeature::SpecularProfile, TEXT("SpecularProfile") }, { ESubstrateBsdfFeature::Eye, TEXT("Eye") },
		{ ESubstrateBsdfFeature::Hair, TEXT("Hair") }, { ESubstrateBsdfFeature::Toon, TEXT("Toon") } };
	for (const TPair<ESubstrateBsdfFeature, const TCHAR*>& Name : Names)
	{
		if (EnumHasAnyFlags(Features, Name.Key))
		{
			if (!FeatureText.IsEmpty())
			{
				FeatureText += TEXT("|");
			}
			FeatureText += Name.Value;
		}
	}
	const uint16 ShadingModels = Resource->GetShadingModels().GetShadingModelField();
	FString Text = FString::Printf(TEXT("%s: material type %u, tile %s, closures %u, uints per pixel %u, BSDF features 0x%04x [%s], shading models 0x%04x"),
		*Base->GetName(), Out.SubstrateMaterialType, ToString(GetSubstrateTileTypeFromMaterialType(Out.SubstrateMaterialType)), Out.SubstrateClosureCount,
		Out.SubstrateUintPerPixel, static_cast<uint32>(Features), FeatureText.IsEmpty() ? TEXT("none") : *FeatureText, ShadingModels);
#if WITH_EDITORONLY_DATA
	Text += FString::Printf(TEXT(", legacy GBuffer pass-through %u, final type %u, thin %u, bytes per pixel %u asked / %u allowed, closures per pixel %u asked / %u allowed, simplified %u; %s"),
		Out.bMaterialUsesLegacyGBufferDataPassThrough, Out.MaterialType, Out.bIsThin, Out.RequestedBytePerPixel, Out.PlatformBytePerPixel,
		Out.RequestedClosurePerPixel, Out.PlatformClosurePixel, Out.bMaterialOutOfBudgetHasBeenSimplified,
		*FString(Out.SubstrateMaterialDescription).Replace(TEXT("\n"), TEXT(" / ")).Replace(TEXT("\r"), TEXT("")));
#endif
	return Text;
}
