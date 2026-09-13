using UnrealBuildTool;

public class OpenStanceTarget : TargetRules
{
	public OpenStanceTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("OpenStance");
	}
}
