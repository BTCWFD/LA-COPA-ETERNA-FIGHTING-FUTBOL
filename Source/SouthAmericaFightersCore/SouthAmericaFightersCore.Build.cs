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

        // Desactiva optimizaciones de punto flotante que rompan determinismo entre x86_64 y Consolas
        bEnableUndefinedIdentifierWarnings = true;
    }
}
