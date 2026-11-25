// SouthAmericaFightersCore.Build.cs - Unreal Engine 5.4+ (SouthAmericaFightersCore)
using UnrealBuildTool;

public class SouthAmericaFightersCore : ModuleRules
{
    public SouthAmericaFightersCore(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        CppStandard = CppStandardVersion.Cpp20;

        PublicDependencyModuleNames.AddRange(new string[] {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            "EnhancedInput",
            "UMG",
            "Slate",
            "SlateCore",
            "CommonUI",
            "CommonInput",
            "Niagara",
            "AIModule"
        });

        // Validación estricta de identificadores indefinidos en UE 5.8+
        CppCompileWarningSettings.UndefinedIdentifierWarningLevel = WarningLevel.Error;
    }
}
