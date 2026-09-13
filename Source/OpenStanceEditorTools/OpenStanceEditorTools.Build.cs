using UnrealBuildTool;

public class OpenStanceEditorTools : ModuleRules
{
	public OpenStanceEditorTools(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"UnrealEd",
			"PhysicsCore",
			"ClothingSystemRuntimeCommon",
			"ClothingSystemRuntimeInterface",
			"ClothingSystemEditorInterface",
			"SkeletalMeshEditor",
		});
	}
}
