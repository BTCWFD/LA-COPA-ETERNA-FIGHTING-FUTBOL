// SouthAmericaFightersCoreModule.cpp - SouthAmericaFightersCore
#include "SouthAmericaFightersCoreModule.h"

DEFINE_LOG_CATEGORY(LogSouthAmericaFighters);

void FSouthAmericaFightersCoreModule::StartupModule()
{
    UE_LOG(LogSouthAmericaFighters, Log, TEXT("SouthAmericaFightersCore Initialized: 60Hz Q32.32 Deterministic Combat Engine Ready."));
}

void FSouthAmericaFightersCoreModule::ShutdownModule()
{
    UE_LOG(LogSouthAmericaFighters, Log, TEXT("SouthAmericaFightersCore Shutdown."));
}

IMPLEMENT_PRIMARY_GAME_MODULE(FSouthAmericaFightersCoreModule, SouthAmericaFightersCore, "SouthAmericaFightersCore");
