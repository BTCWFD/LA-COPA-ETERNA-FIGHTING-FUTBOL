// SouthAmericaFightersCoreModule.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

DECLARE_LOG_CATEGORY_EXTERN(LogSouthAmericaFighters, Log, All);

class FSouthAmericaFightersCoreModule : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
};
