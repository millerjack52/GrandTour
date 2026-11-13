using UnrealBuildTool;

// Editor-only module: the OW landscape toolkit (biome PCG graphs, tree variants,
// road verge paint, bed stamps, test-map setup). See docs/LandscapeMigrationManifest.md.
public class GrandTourEditor : ModuleRules
{
	public GrandTourEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicIncludePaths.Add(ModuleDirectory);

		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "GrandTour" });

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"AssetRegistry",
			"UnrealEd",
			"Landscape",
            "ProceduralMeshComponent",
			// UOWBedStampComponent: ULandscapeTexturePatch sculpt stamps.
			"LandscapePatch",
			// Biome PCG graph authoring (OWCreateBiomePCGCommandlet).
			"PCG",
			// OWCreateTreeVariantsCommandlet: Geometry Script mesh edits.
			"GeometryCore",
			"GeometryFramework",
			"GeometryScriptingCore",
			"GeometryScriptingEditor",
			// OWPaintRoadVergeCommandlet: FlushRenderingCommands for the edit-layer merge pump.
			"RenderCore",
			// GTSubstrateInfoLibrary (LM3c): GMaxRHIShaderPlatform for the material resource it reads.
			"RHI",
			// LandscapeEdit.h pulls Foliage headers.
			"Foliage",
			"Slate",
			"SlateCore",
			// Wheel spray P2 (UGTNiagaraSetupLibrary): Niagara systems authored through UNiagaraExternalEditUtilities.
			"Niagara",
			"NiagaraCore",
			"NiagaraEditor",
		});
	}
}
