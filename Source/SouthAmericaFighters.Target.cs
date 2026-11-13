// SouthAmericaFighters.Target.cs - Unreal Engine 5.4+
using UnrealBuildTool;
using System.Collections.Generic;

public class SouthAmericaFightersTarget : TargetRules
{
    public SouthAmericaFightersTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V5;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_4;
        CppStandard = CppStandardVersion.Cpp20;

        ExtraModuleNames.AddRange(new string[] { "SouthAmericaFightersCore" });
    }
}
