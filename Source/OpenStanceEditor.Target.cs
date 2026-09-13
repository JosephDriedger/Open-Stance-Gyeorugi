using UnrealBuildTool;

public class OpenStanceEditorTarget : TargetRules
{
	public OpenStanceEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.AddRange(new string[] { "OpenStance", "OpenStanceEditorTools" });
	}
}
