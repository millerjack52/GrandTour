// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class GrandTour : ModuleRules
{
	public GrandTour(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// Source is organised in subfolders (Vehicle/, Core/, ...); include them relative to the module root.
		PublicIncludePaths.Add(ModuleDirectory);
	
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "ChaosVehicles", "GameplayTags", "PhysicsCore", "AssetRegistry", "AudioExtensions", "CableComponent", "Landscape", "Foliage", "RHI", "RenderCore", "ProceduralMeshComponent", "DeveloperSettings", "Niagara" });

		PrivateDependencyModuleNames.AddRange(new string[] { "MeshDescription", "StaticMeshDescription", "ChaosVehiclesCore", "Chaos", "Json", "Slate", "SlateCore" });
		RuntimeDependencies.Add("$(ProjectDir)/Art/lidar_performance.json", StagedFileType.NonUFS);
		RuntimeDependencies.Add("$(ProjectDir)/Content/Audio/RangeRoverHybridH2/loops.gth2", StagedFileType.UFS);
		RuntimeDependencies.Add("$(ProjectDir)/Content/Audio/RangeRoverHybridH2/ATTRIBUTION.txt", StagedFileType.NonUFS);
		RuntimeDependencies.Add("$(ProjectDir)/Content/Audio/RangeRoverHybridH2/provenance.json", StagedFileType.NonUFS);
		RuntimeDependencies.Add("$(ProjectDir)/Content/Audio/RangeRoverGroundS3/recordings.gts3", StagedFileType.UFS);
		RuntimeDependencies.Add("$(ProjectDir)/Content/Audio/RangeRoverGroundS3/ATTRIBUTION.txt", StagedFileType.NonUFS);
		RuntimeDependencies.Add("$(ProjectDir)/Content/Audio/RangeRoverGroundS3/sources.json", StagedFileType.NonUFS);

		// Setup helpers that only editor scripts call (input asset writing, material pins).
		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.AddRange(new string[] { "MaterialEditor" });
			// OWRoadBedComponent (Dressing/): editor toasts (FNotificationInfo) on Apply Bed & Verge.
			PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
		}

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
		
		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
