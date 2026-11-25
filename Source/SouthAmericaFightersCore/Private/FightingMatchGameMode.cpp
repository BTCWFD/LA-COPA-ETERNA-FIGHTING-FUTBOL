// FightingMatchGameMode.cpp - SouthAmericaFightersCore
#include "FightingMatchGameMode.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/DataTable.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FightingInputParser.h"
#include "FrameDataTypes.h"
#include "GameFramework/PlayerController.h"
#include "Misc/PackageName.h"

namespace FightingMatchAssetPaths
{
    static constexpr const TCHAR* RosterTablePkg    = TEXT("/Game/DataTables/DT_SouthAmericaRoster");
    static constexpr const TCHAR* StagesTablePkg    = TEXT("/Game/DataTables/DT_StagesCONMEBOL");
    static constexpr const TCHAR* FrameDataTablePkg = TEXT("/Game/DataTables/DT_FrameDataUniversal");

    static UDataTable* TryLoadDataTable(const TCHAR* PackagePath, const TCHAR* Label)
    {
        if (!FPackageName::DoesPackageExist(PackagePath))
        {
            UE_LOG(LogTemp, Log, TEXT("FightingMatchGameMode: DataTable %s not packaged at %s (using built-in defaults)."), Label, PackagePath);
            return nullptr;
        }
        if (UDataTable* Table = LoadObject<UDataTable>(nullptr, PackagePath))
        {
            UE_LOG(LogTemp, Log, TEXT("FightingMatchGameMode: Loaded %s (%d rows)."), Label, Table->GetRowNames().Num());
            return Table;
        }
        return nullptr;
    }
}

AFightingMatchGameMode::AFightingMatchGameMode()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PrePhysics;

    DefaultPawnClass = AFighterCharacterPawn::StaticClass();
    GameStateClass = AFightingMatchGameState::StaticClass();

    // Configuración por defecto: Templo do Maracanã (Zona A: -12.5m a +12.5m, Zona B: -18.5m a +18.5m)
    ActiveStageData.StageID = TEXT("STAGE_MARACANA");
    ActiveStageData.DisplayName = FText::FromString(TEXT("Templo do Maracanã (Río de Janeiro)"));
    ActiveStageData.ZoneABounds.LeftWallFixedMm = -12500;
    ActiveStageData.ZoneABounds.RightWallFixedMm = 12500;
    ActiveStageData.ZoneABounds.MaxWallHealth = 3;
    ActiveStageData.ZoneBBounds.LeftWallFixedMm = -18500;
    ActiveStageData.ZoneBBounds.RightWallFixedMm = 18500;
    ActiveStageData.ZoneBBounds.MaxWallHealth = 99;
    ActiveStageData.BaseTempoBPM = 115.0f;
}

void AFightingMatchGameMode::BeginPlay()
{
    Super::BeginPlay();

    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }

    // 1. Cargar DataTables oficiales desde /Game/DataTables/ (si existen) y configurar estadio según el mapa
    LoadCoreCombatDataTables();
    ConfigureStageDataFromCurrentWorld(World);

    CameraDirector = NewObject<UFightingCameraDirector>(this, TEXT("FightingCameraDirector"));
    CameraDirector->InitializeStageBounds(
        ActiveStageData.ZoneABounds.GetLeftWallFixed(),
        ActiveStageData.ZoneABounds.GetRightWallFixed());

    NetworkBridge = NewObject<UEOSGGPONetworkBridge>(this, TEXT("EOSGGPONetworkBridge"));
    ReplayDirector = NewObject<UReplayPlaybackSubsystem>(this, TEXT("ReplayPlaybackSubsystem"));

    // Resolver HP inicial desde DT_SouthAmericaRoster si está cargado
    const FName DefaultP1ID = TEXT("FENOMENO_BR");
    const FName DefaultP2ID = TEXT("CANON_AR");
    int32 P1MaxHP = 10000;
    int32 P2MaxHP = 10500;

    if (LoadedRosterTable)
    {
        static const FString RosterCtx(TEXT("MatchBeginPlay_Roster"));
        TArray<FFighterRosterRow*> RosterRows;
        LoadedRosterTable->GetAllRows<FFighterRosterRow>(RosterCtx, RosterRows);
        for (const FFighterRosterRow* Row : RosterRows)
        {
            if (!Row)
            {
                continue;
            }
            if (Row->Name == DefaultP1ID && Row->MaxHealth > 0)
            {
                P1MaxHP = Row->MaxHealth;
            }
            else if (Row->Name == DefaultP2ID && Row->MaxHealth > 0)
            {
                P2MaxHP = Row->MaxHealth;
            }
        }
    }

    // 2. Instanciar luchadores P1 y P2 si no están ya en el nivel
    FActorSpawnParameters SpawnParams;
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    if (!Player1Pawn)
    {
        Player1Pawn = World->SpawnActor<AFighterCharacterPawn>(AFighterCharacterPawn::StaticClass(), FVector(-250.0f, 0.0f, 0.0f), FRotator::ZeroRotator, SpawnParams);
        if (Player1Pawn)
        {
            Player1Pawn->InitializeFighterForRound(0, DefaultP1ID, FFixedPoint::FromMillimeters(-2500), true, P1MaxHP);
        }
    }

    if (!Player2Pawn)
    {
        Player2Pawn = World->SpawnActor<AFighterCharacterPawn>(AFighterCharacterPawn::StaticClass(), FVector(250.0f, 0.0f, 0.0f), FRotator(0.0f, 180.0f, 0.0f), SpawnParams);
        if (Player2Pawn)
        {
            Player2Pawn->InitializeFighterForRound(1, DefaultP2ID, FFixedPoint::FromMillimeters(2500), false, P2MaxHP);
        }
    }

    if (LoadedFrameDataTable)
    {
        if (Player1Pawn && Player1Pawn->GetFighterStateMachine())
        {
            Player1Pawn->GetFighterStateMachine()->LoadMoveCatalogFromDataTable(LoadedFrameDataTable);
        }
        if (Player2Pawn && Player2Pawn->GetFighterStateMachine())
        {
            Player2Pawn->GetFighterStateMachine()->LoadMoveCatalogFromDataTable(LoadedFrameDataTable);
        }
    }

    // 3. Configurar BroadcastCameraActor 2.5D, posesión de PlayerController e IA de P2 / 2do jugador local
    SetupLiveCameraAndControllers(World);

    // Pool de proyectiles de balón deterministas (1 activo por jugador en pantalla)
    Player1BallProjectile = World->SpawnActor<ADeterministicBallProjectile>(ADeterministicBallProjectile::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    Player2BallProjectile = World->SpawnActor<ADeterministicBallProjectile>(ADeterministicBallProjectile::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);

    if (AFightingMatchGameState* MatchGS = GetGameState<AFightingMatchGameState>())
    {
        MatchGS->MatchState.LeftWallRemainingHealth = ActiveStageData.ZoneABounds.MaxWallHealth;
        MatchGS->MatchState.RightWallRemainingHealth = ActiveStageData.ZoneABounds.MaxWallHealth;
    }

    // Vincular con el Modo Entrenamiento si está activo
    if (UGameInstance* GI = GetGameInstance())
    {
        if (UTrainingModeSubsystem* TrainingSub = GI->GetSubsystem<UTrainingModeSubsystem>())
        {
            if (Player1Pawn && Player2Pawn)
            {
                TrainingSub->BindTrainingFighters(Player1Pawn->GetFighterStateMachine(), Player2Pawn->GetFighterStateMachine());
            }
        }
    }

    // Inicializar Audio Reactivo Wwise del estadio (incluyendo altitud 3600m en La Paz)
    if (UWwiseCombatAudioDirector* AudioDirector = World->GetSubsystem<UWwiseCombatAudioDirector>())
    {
        const FName HomeFighter = Player1Pawn ? Player1Pawn->GetFighterRosterID() : DefaultP1ID;
        AudioDirector->InitializeMatchAudioEnvironment(
            ActiveStageData.StageID,
            HomeFighter,
            ActiveStageData.GetEffectiveAltitudeMeters());
    }
}

void AFightingMatchGameMode::LoadCoreCombatDataTables()
{
    LoadedRosterTable    = FightingMatchAssetPaths::TryLoadDataTable(FightingMatchAssetPaths::RosterTablePkg, TEXT("DT_SouthAmericaRoster"));
    LoadedStagesTable    = FightingMatchAssetPaths::TryLoadDataTable(FightingMatchAssetPaths::StagesTablePkg, TEXT("DT_StagesCONMEBOL"));
    LoadedFrameDataTable = FightingMatchAssetPaths::TryLoadDataTable(FightingMatchAssetPaths::FrameDataTablePkg, TEXT("DT_FrameDataUniversal"));
}

FName AFightingMatchGameMode::ResolveStageIDFromMapName(const FString& CleanMapName)
{
    if (CleanMapName.Contains(TEXT("Bombonera"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("02_"), ESearchCase::IgnoreCase))
    {
        return TEXT("STAGE_BOMBONERA");
    }
    if (CleanMapName.Contains(TEXT("Centenario"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("03_"), ESearchCase::IgnoreCase))
    {
        return TEXT("STAGE_CENTENARIO");
    }
    if (CleanMapName.Contains(TEXT("Metropolitano"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("Barranquilla"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("04_"), ESearchCase::IgnoreCase))
    {
        return TEXT("STAGE_METROPOLITANO");
    }
    if (CleanMapName.Contains(TEXT("Nunoa"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("05_"), ESearchCase::IgnoreCase))
    {
        return TEXT("STAGE_NUNOA");
    }
    if (CleanMapName.Contains(TEXT("Defensores"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("Asuncion"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("06_"), ESearchCase::IgnoreCase))
    {
        return TEXT("STAGE_DEFENSORES");
    }
    if (CleanMapName.Contains(TEXT("NacionalLima"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("Lima"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("07_"), ESearchCase::IgnoreCase))
    {
        return TEXT("STAGE_NACIONAL_LIMA");
    }
    if (CleanMapName.Contains(TEXT("Atahualpa"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("Quito"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("08_"), ESearchCase::IgnoreCase))
    {
        return TEXT("STAGE_ATAHUALPA");
    }
    if (CleanMapName.Contains(TEXT("Avila"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("Caracas"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("09_"), ESearchCase::IgnoreCase))
    {
        return TEXT("STAGE_AVILA");
    }
    if (CleanMapName.Contains(TEXT("HernandoSiles"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("LaPaz"), ESearchCase::IgnoreCase) || CleanMapName.Contains(TEXT("10_"), ESearchCase::IgnoreCase))
    {
        return TEXT("STAGE_HERNANDO_SILES");
    }
    return TEXT("STAGE_MARACANA");
}

FStageDataRow AFightingMatchGameMode::BuildCanonicalStageData(FName StageID)
{
    FStageCONMEBOLTableRow FlatRow;
    FlatRow.StageID = StageID;

    if (StageID == TEXT("STAGE_BOMBONERA"))
    {
        FlatRow.DisplayName = FText::FromString(TEXT("La Caldera de La Boca (Buenos Aires)"));
        FlatRow.ZoneAWidth = 2200; FlatRow.WallHealth = 4; FlatRow.BPM = 128.0f;
    }
    else if (StageID == TEXT("STAGE_CENTENARIO"))
    {
        FlatRow.DisplayName = FText::FromString(TEXT("Monumento Centenario (Montevideo)"));
        FlatRow.ZoneAWidth = 2400; FlatRow.WallHealth = 3; FlatRow.BPM = 120.0f;
    }
    else if (StageID == TEXT("STAGE_METROPOLITANO"))
    {
        FlatRow.DisplayName = FText::FromString(TEXT("Coloso de Barranquilla (Metropolitano)"));
        FlatRow.ZoneAWidth = 2500; FlatRow.WallHealth = 3; FlatRow.BPM = 130.0f;
    }
    else if (StageID == TEXT("STAGE_NUNOA"))
    {
        FlatRow.DisplayName = FText::FromString(TEXT("Coliseo de Ñuñoa (Santiago)"));
        FlatRow.ZoneAWidth = 2400; FlatRow.WallHealth = 3; FlatRow.BPM = 125.0f;
    }
    else if (StageID == TEXT("STAGE_DEFENSORES"))
    {
        FlatRow.DisplayName = FText::FromString(TEXT("El Fortín de Sajonia (Defensores del Chaco - Asunción)"));
        FlatRow.ZoneAWidth = 2300; FlatRow.WallHealth = 4; FlatRow.BPM = 120.0f;
    }
    else if (StageID == TEXT("STAGE_NACIONAL_LIMA"))
    {
        FlatRow.DisplayName = FText::FromString(TEXT("Templo José Díaz (Estadio Nacional de Lima)"));
        FlatRow.ZoneAWidth = 2400; FlatRow.WallHealth = 3; FlatRow.BPM = 118.0f;
    }
    else if (StageID == TEXT("STAGE_ATAHUALPA"))
    {
        FlatRow.DisplayName = FText::FromString(TEXT("El Volcán de Quito (Atahualpa / Casa Blanca)"));
        FlatRow.ZoneAWidth = 2450; FlatRow.WallHealth = 3; FlatRow.BPM = 135.0f;
    }
    else if (StageID == TEXT("STAGE_AVILA"))
    {
        FlatRow.DisplayName = FText::FromString(TEXT("El Monumental del Ávila (Caracas)"));
        FlatRow.ZoneAWidth = 2400; FlatRow.WallHealth = 3; FlatRow.BPM = 170.0f;
    }
    else if (StageID == TEXT("STAGE_HERNANDO_SILES"))
    {
        FlatRow.DisplayName = FText::FromString(TEXT("El Nido del Cóndor - 3600m (Hernando Siles - La Paz)"));
        FlatRow.ZoneAWidth = 2600; FlatRow.WallHealth = 2; FlatRow.BPM = 110.0f;
        FlatRow.AltitudeMeters = FStageDataRow::LaPazAltitudeMeters;
    }
    else
    {
        FlatRow.StageID = TEXT("STAGE_MARACANA");
        FlatRow.DisplayName = FText::FromString(TEXT("Templo do Maracanã (Río de Janeiro)"));
        FlatRow.ZoneAWidth = 2500; FlatRow.WallHealth = 3; FlatRow.BPM = 115.0f;
    }

    return FlatRow.ToStageDataRow();
}

void AFightingMatchGameMode::ConfigureStageDataFromCurrentWorld(const UWorld* World)
{
    if (!World)
    {
        return;
    }

    const FString RawMapName = World->GetMapName();
    const FString CleanMapName = UWorld::RemovePIEPrefix(RawMapName);
    const FName TargetStageID = ResolveStageIDFromMapName(CleanMapName);

    ActiveStageData = BuildCanonicalStageData(TargetStageID);

    if (LoadedStagesTable)
    {
        static const FString StagesCtx(TEXT("MatchBeginPlay_Stages"));
        TArray<FStageCONMEBOLTableRow*> StageRows;
        LoadedStagesTable->GetAllRows<FStageCONMEBOLTableRow>(StagesCtx, StageRows);
        for (const FStageCONMEBOLTableRow* Row : StageRows)
        {
            if (Row && Row->StageID == TargetStageID)
            {
                ActiveStageData = Row->ToStageDataRow();
                break;
            }
        }
    }

    UE_LOG(LogTemp, Log, TEXT("FightingMatchGameMode: Map='%s' -> Stage='%s' (ZoneA=[%lld..%lld mm], WallHP=%d, BPM=%.1f, Alt=%.0fm)."),
        *CleanMapName,
        *ActiveStageData.StageID.ToString(),
        ActiveStageData.ZoneABounds.LeftWallFixedMm,
        ActiveStageData.ZoneABounds.RightWallFixedMm,
        ActiveStageData.ZoneABounds.MaxWallHealth,
        ActiveStageData.BaseTempoBPM,
        ActiveStageData.GetEffectiveAltitudeMeters());
}

void AFightingMatchGameMode::SetupLiveCameraAndControllers(UWorld* World)
{
    if (!World)
    {
        return;
    }

    // 1. Buscar o crear BroadcastCameraActor para el plano competitivo 2.5D
    if (!BroadcastCameraActor)
    {
        for (TActorIterator<ACameraActor> It(World); It; ++It)
        {
            ACameraActor* Candidate = *It;
            if (Candidate && (Candidate->ActorHasTag(TEXT("BroadcastCamera")) || Candidate->GetName().Contains(TEXT("BroadcastCamera"))))
            {
                BroadcastCameraActor = Candidate;
                break;
            }
        }

        if (!BroadcastCameraActor)
        {
            const FTransform InitialCamTransform = CameraDirector
                ? CameraDirector->GetWorldCameraTransformUE()
                : FTransform(FRotator(0.0f, 90.0f, 0.0f), FVector(0.0f, -480.0f, 115.0f));

            FActorSpawnParameters CamParams;
            CamParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            BroadcastCameraActor = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), InitialCamTransform, CamParams);
            if (BroadcastCameraActor)
            {
                BroadcastCameraActor->Tags.AddUnique(TEXT("BroadcastCamera"));
            }
        }
    }

    if (BroadcastCameraActor && CameraDirector)
    {
        float HorizontalFOV = 54.0f;
        const FTransform CamTransform = CameraDirector->GetVisualCameraTransformCm(HorizontalFOV);
        BroadcastCameraActor->SetActorTransform(CamTransform);
        if (UCameraComponent* CamComp = BroadcastCameraActor->GetCameraComponent())
        {
            CamComp->SetFieldOfView(HorizontalFOV);
        }
    }

    // 2. Vincular PlayerControllers locales (P1 y opcionalmente P2 local) y fijar la vista en BroadcastCameraActor
    TArray<APlayerController*> LocalControllers;
    for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
    {
        if (APlayerController* PC = It->Get())
        {
            LocalControllers.Add(PC);
        }
    }

    if (LocalControllers.Num() >= 1 && Player1Pawn)
    {
        APlayerController* P1Controller = LocalControllers[0];
        P1Controller->bAutoManageActiveCameraTarget = false;
        Player1Pawn->BindFighterPlayerControllerInput(P1Controller);
        if (BroadcastCameraActor)
        {
            P1Controller->SetViewTargetWithBlend(BroadcastCameraActor, 0.0f);
        }
    }

    if (LocalControllers.Num() >= 2 && Player2Pawn)
    {
        APlayerController* P2Controller = LocalControllers[1];
        P2Controller->bAutoManageActiveCameraTarget = false;
        Player2Pawn->BindFighterPlayerControllerInput(P2Controller);
        if (BroadcastCameraActor)
        {
            P2Controller->SetViewTargetWithBlend(BroadcastCameraActor, 0.0f);
        }
    }
    else if (!bIsTrainingModeMatch && !ActiveBossAIController && bSpawnDefaultSparringAI && Player1Pawn && Player2Pawn)
    {
        // 3. Si P2 no tiene controlador ni Training Dummy, instanciar IA de combate por defecto
        FActorSpawnParameters AIParams;
        AIParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        ActiveBossAIController = World->SpawnActor<ABossAIController>(ABossAIController::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, AIParams);
        if (ActiveBossAIController)
        {
            ActiveBossAIController->bAllowVARRewindMechanic = ABossAIController::IsBossFighterID(Player2Pawn->GetFighterRosterID());
            ActiveBossAIController->BindFighterStateMachines(Player1Pawn->GetFighterStateMachine(), Player2Pawn->GetFighterStateMachine());
        }
    }
}

void AFightingMatchGameMode::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    if (!Player1Pawn || !Player2Pawn)
    {
        return;
    }

    // Si hay ventaja de reloj en red GGPO P2P (>0.75 frames), hacer Rift Sync esperando 1 tick
    if (NetworkBridge && NetworkBridge->IsSessionActive())
    {
        NetworkBridge->PollIncomingPackets();
        if (NetworkBridge->ShouldStallSimulationForRiftSync())
        {
            return;
        }
    }

    const uint16 P1Mask = Player1Pawn->PollLocalRawInputBitmask();
    uint16 P2Mask = Player2Pawn->PollLocalRawInputBitmask();

    // Resolver fuente de entrada de P2 (Modo Entrenamiento, 2do Jugador Local o IA Sparring / Jefe V.A.R. - ZERO)
    if (bIsTrainingModeMatch)
    {
        if (UGameInstance* GI = GetGameInstance())
        {
            if (UTrainingModeSubsystem* TrainingSub = GI->GetSubsystem<UTrainingModeSubsystem>())
            {
                P2Mask = TrainingSub->EvaluateDummyFrameInput(P1Mask);
            }
        }
    }
    else if (!Player2Pawn->bIsPlayerControlled && ActiveBossAIController)
    {
        if (AFightingMatchGameState* MatchGS = GetGameState<AFightingMatchGameState>())
        {
            ActiveBossAIController->DeterministicStep(MatchGS->MatchState.CurrentSimulationFrame);
            P2Mask = ActiveBossAIController->GetCurrentBossInputBitmask();
        }
    }

    StepDeterministicMatchTick(P1Mask, P2Mask, false);
}

void AFightingMatchGameMode::StepDeterministicMatchTick(uint16 P1InputMask, uint16 P2InputMask, bool bIsRollbackReSimulation)
{
    if (!Player1Pawn || !Player2Pawn)
    {
        return;
    }

    UDeterministicFighterStateMachine* P1SM = Player1Pawn->GetFighterStateMachine();
    UDeterministicFighterStateMachine* P2SM = Player2Pawn->GetFighterStateMachine();
    if (!P1SM || !P2SM)
    {
        return;
    }

    CachedP1InputMask = P1InputMask;
    CachedP2InputMask = P2InputMask;

    AFightingMatchGameState* MatchGS = GetGameState<AFightingMatchGameState>();
    uint32 CurrentFrame = 0;
    if (MatchGS)
    {
        ++MatchGS->MatchState.CurrentSimulationFrame;
        CurrentFrame = MatchGS->MatchState.CurrentSimulationFrame;
        if (MatchGS->MatchState.RemainingTimerFrames > 0)
        {
            --MatchGS->MatchState.RemainingTimerFrames;
        }
    }

    // 1. Capturar posiciones y estados previos antes del paso para evaluación simétrica
    const FFixedVector2D PrevP1Pos = P1SM->GetState().Position;
    const FFixedVector2D PrevP2Pos = P2SM->GetState().Position;
    const EFighterActionState PrevP1ActionState = P1SM->GetState().CurrentState;
    const EFighterActionState PrevP2ActionState = P2SM->GetState().CurrentState;

    // 2. Avanzar 1 frame ambas máquinas de estados deterministas
    P1SM->StepSimulationFrame(P1InputMask, PrevP2Pos);
    P2SM->StepSimulationFrame(P2InputMask, PrevP1Pos);

    // Disparar proyectil de balón determinista en el primer frame activo de 236+SK
    if (PrevP1ActionState != EFighterActionState::AttackActive &&
        P1SM->GetState().CurrentState == EFighterActionState::AttackActive &&
        P1SM->GetState().ActiveMoveID == TEXT("Special_236_Projectile"))
    {
        SpawnBallProjectileForFighter(0, Player1Pawn->GetFighterRosterID() == TEXT("CANON_AR"));
    }
    if (PrevP2ActionState != EFighterActionState::AttackActive &&
        P2SM->GetState().CurrentState == EFighterActionState::AttackActive &&
        P2SM->GetState().ActiveMoveID == TEXT("Special_236_Projectile"))
    {
        SpawnBallProjectileForFighter(1, Player2Pawn->GetFighterRosterID() == TEXT("CANON_AR"));
    }

    // Reiniciar contadores de combo cuando el defensor vuelve a estado neutro
    if (MatchGS)
    {
        if (P2SM->GetState().CurrentState != EFighterActionState::Hitstun)
        {
            MatchGS->MatchState.P1ActiveComboHits = 0;
            MatchGS->MatchState.P1ActiveComboDamage = 0;
        }
        if (P1SM->GetState().CurrentState != EFighterActionState::Hitstun)
        {
            MatchGS->MatchState.P2ActiveComboHits = 0;
            MatchGS->MatchState.P2ActiveComboDamage = 0;
        }
    }

    // 3. Resolver Pushbox-vs-Pushbox y sujeción a muros de estadio
    ResolvePushboxAndStageWallCollision();

    // 4. Avanzar y resolver proyectiles de balón (choque entre proyectiles, reflejo de El Escorpión e impacto)
    StepAndResolveBallProjectiles(bIsRollbackReSimulation);

    // 5. Resolver Hitbox-vs-Hurtbox cuerpo a cuerpo (soporta Trade simultáneo)
    ResolveMeleeHitboxes(bIsRollbackReSimulation);

    // 6. Avanzar cámara determinista 2.5D en punto fijo Q32.32
    if (CameraDirector)
    {
        CameraDirector->StepDeterministicCamera(P1SM->GetState(), P2SM->GetState());
    }

    // 7. Registrar checksum en el puente de red GGPO y grabar frame en el Teatro de Repeticiones
    if (NetworkBridge && !bIsRollbackReSimulation)
    {
        const uint16 CombinedChecksum16 = static_cast<uint16>((P1SM->ComputeStateChecksum() ^ P2SM->ComputeStateChecksum()) & 0xFFFF);
        NetworkBridge->RecordLocalFrameChecksum(CurrentFrame, CombinedChecksum16);
        if (NetworkBridge->IsSessionActive())
        {
            NetworkBridge->SendFrameInputToOpponent(CurrentFrame, P1InputMask, CombinedChecksum16);
        }
    }

    if (ReplayDirector && !bIsRollbackReSimulation)
    {
        FMatchDeterministicSnapshotPOD ReplaySnap;
        ReplaySnap.FrameNumber = CurrentFrame;
        P1SM->SaveDeterministicState(ReplaySnap.Player1State);
        P2SM->SaveDeterministicState(ReplaySnap.Player2State);
        if (CameraDirector)
        {
            CameraDirector->SaveCameraState(ReplaySnap.CameraState);
        }
        ReplayDirector->RecordLiveMatchFrame(CurrentFrame, P1InputMask, P2InputMask, ReplaySnap);
    }

    // 8. Sincronizar Transforms visuales 3D, cajas Greyboxing, Audio Wwise y HUD Zero-Binding
    BroadcastVisualAndHUDState(bIsRollbackReSimulation);
}

ADeterministicBallProjectile* AFightingMatchGameMode::SpawnBallProjectileForFighter(
    int32 OwnerPlayerIndex,
    bool bIsHeavyChargedCanonShot)
{
    AFighterCharacterPawn* OwnerPawn = (OwnerPlayerIndex == 0) ? Player1Pawn : Player2Pawn;
    ADeterministicBallProjectile* TargetProjectile = (OwnerPlayerIndex == 0) ? Player1BallProjectile : Player2BallProjectile;

    if (!OwnerPawn || !TargetProjectile || !OwnerPawn->GetFighterStateMachine())
    {
        return nullptr;
    }

    const FFighterDeterministicStatePOD& FighterState = OwnerPawn->GetFighterStateMachine()->GetState();
    const FFixedPoint ForwardOffset = FighterState.bIsFacingRight
        ? FFixedPoint::FromMillimeters(550)
        : FFixedPoint::FromMillimeters(-550);

    const FFixedVector2D SpawnPos(
        FighterState.Position.X + ForwardOffset,
        FighterState.Position.Y + FFixedPoint::FromMillimeters(450));

    // Velocidad horizontal: 18.0 m/s (300 mm/frame a 60 Hz) o 24.0 m/s (400 mm/frame) para Bati-Cañonazo cargado
    const FFixedPoint SpeedPerFrame = bIsHeavyChargedCanonShot
        ? FFixedPoint::FromMillimeters(400)
        : FFixedPoint::FromMillimeters(300);

    const FFixedVector2D Velocity(
        FighterState.bIsFacingRight ? SpeedPerFrame : -SpeedPerFrame,
        FFixedPoint(0));

    // Pasiva de El Cañón: el proyectil cargado tiene 2 puntos de impacto en choques de proyectiles
    const int32 ClashHP = bIsHeavyChargedCanonShot ? 2 : 1;
    const int32 Damage = bIsHeavyChargedCanonShot ? 1650 : 1100;

    TargetProjectile->SpawnDeterministicBall(OwnerPlayerIndex, SpawnPos, Velocity, ClashHP, Damage);
    return TargetProjectile;
}

void AFightingMatchGameMode::ResolvePushboxAndStageWallCollision()
{
    UDeterministicFighterStateMachine* P1SM = Player1Pawn->GetFighterStateMachine();
    UDeterministicFighterStateMachine* P2SM = Player2Pawn->GetFighterStateMachine();

    const FFixedAABB Box1 = P1SM->GetCurrentPushbox();
    const FFixedAABB Box2 = P2SM->GetCurrentPushbox();

    FFighterDeterministicStatePOD State1;
    FFighterDeterministicStatePOD State2;
    P1SM->SaveDeterministicState(State1);
    P2SM->SaveDeterministicState(State2);

    // 1. Separación simétrica Pushbox-vs-Pushbox (50% cada jugador en Q32.32)
    if (Box1.Intersects(Box2))
    {
        const FFixedPoint OverlapLeft  = Box1.MaxX - Box2.MinX;
        const FFixedPoint OverlapRight = Box2.MaxX - Box1.MinX;
        const FFixedPoint Penetration = (OverlapLeft < OverlapRight) ? OverlapLeft : OverlapRight;
        const FFixedPoint HalfPush = Penetration * FFixedPoint::FromMillimeters(500);

        if (State1.Position.X <= State2.Position.X)
        {
            State1.Position.X -= HalfPush;
            State2.Position.X += HalfPush;
        }
        else
        {
            State1.Position.X += HalfPush;
            State2.Position.X -= HalfPush;
        }
    }

    // 2. Sujeción a los muros de la zona actual del estadio (Zona A o Zona B)
    const AFightingMatchGameState* MatchGS = GetGameState<AFightingMatchGameState>();
    const bool bInZoneB = MatchGS ? MatchGS->MatchState.bIsInStageZoneB : false;
    const FStageZoneBounds& CurrentBounds = bInZoneB ? ActiveStageData.ZoneBBounds : ActiveStageData.ZoneABounds;

    const FFixedPoint LeftWall  = CurrentBounds.GetLeftWallFixed();
    const FFixedPoint RightWall = CurrentBounds.GetRightWallFixed();

    if (State1.Position.X < LeftWall)
    {
        State1.Position.X = LeftWall;
        if (State1.CurrentState == EFighterActionState::Hitstun)
        {
            CheckAndTriggerStageWallBreak(0, -1);
        }
    }
    else if (State1.Position.X > RightWall)
    {
        State1.Position.X = RightWall;
        if (State1.CurrentState == EFighterActionState::Hitstun)
        {
            CheckAndTriggerStageWallBreak(0, 1);
        }
    }

    if (State2.Position.X < LeftWall)
    {
        State2.Position.X = LeftWall;
        if (State2.CurrentState == EFighterActionState::Hitstun)
        {
            CheckAndTriggerStageWallBreak(1, -1);
        }
    }
    else if (State2.Position.X > RightWall)
    {
        State2.Position.X = RightWall;
        if (State2.CurrentState == EFighterActionState::Hitstun)
        {
            CheckAndTriggerStageWallBreak(1, 1);
        }
    }

    P1SM->LoadDeterministicState(State1);
    P2SM->LoadDeterministicState(State2);
}

void AFightingMatchGameMode::StepAndResolveBallProjectiles(bool bIsRollbackReSimulation)
{
    if (Player1BallProjectile)
    {
        Player1BallProjectile->StepDeterministicBallFrame();
    }
    if (Player2BallProjectile)
    {
        Player2BallProjectile->StepDeterministicBallFrame();
    }

    // 1. Choque de proyectil contra proyectil (incluye prioridad de 2 puntos de impacto de El Cañón)
    if (Player1BallProjectile && Player2BallProjectile &&
        Player1BallProjectile->GetBallState().bIsActive &&
        Player2BallProjectile->GetBallState().bIsActive)
    {
        const FFixedAABB BallBox1 = Player1BallProjectile->GetBallHitboxAABB();
        const FFixedAABB BallBox2 = Player2BallProjectile->GetBallHitboxAABB();
        if (BallBox1.Intersects(BallBox2))
        {
            const int32 HP1 = Player1BallProjectile->GetBallState().RemainingClashHitPoints;
            const int32 HP2 = Player2BallProjectile->GetBallState().RemainingClashHitPoints;
            Player1BallProjectile->ConsumeClashHitPoints(HP2);
            Player2BallProjectile->ConsumeClashHitPoints(HP1);
        }
    }

    // 2. Impacto o reflejo ("El Escorpión" 214+SK) de proyectiles contra los luchadores
    ADeterministicBallProjectile* Balls[2] = { Player1BallProjectile, Player2BallProjectile };
    for (ADeterministicBallProjectile* Ball : Balls)
    {
        if (!Ball || !Ball->GetBallState().bIsActive)
        {
            continue;
        }

        const int32 BallOwner = Ball->GetBallState().OwnerPlayerIndex;
        const int32 DefenderIndex = (BallOwner == 0) ? 1 : 0;
        AFighterCharacterPawn* DefenderPawn = (DefenderIndex == 0) ? Player1Pawn : Player2Pawn;
        if (!DefenderPawn || !DefenderPawn->GetFighterStateMachine())
        {
            continue;
        }

        UDeterministicFighterStateMachine* DefenderSM = DefenderPawn->GetFighterStateMachine();
        const FFixedAABB BallBox = Ball->GetBallHitboxAABB();
        const FFixedAABB DefenderHurtbox = DefenderSM->GetCurrentHurtbox();

        if (BallBox.Intersects(DefenderHurtbox))
        {
            const FFighterDeterministicStatePOD& DefState = DefenderSM->GetState();

            // Si el defensor está ejecutando la técnica 214+SK ("El Escorpión"), refleja el balón con +35% de velocidad
            if (DefState.ActiveMoveID == TEXT("Special_214_Technique") || DefState.ActiveMoveID == TEXT("LOCO_ESCORPION"))
            {
                Ball->ReflectByScorpionKick(DefenderIndex);
                continue;
            }

            const uint16 DefenderInput = (DefenderIndex == 0) ? CachedP1InputMask : CachedP2InputMask;
            FFighterDeterministicStatePOD FakeProjectileAttacker = DefState;
            FakeProjectileAttacker.Position = Ball->GetBallState().Position;

            const bool bBlocked = IsDefenderBlockingAttack(FakeProjectileAttacker, DefState, DefenderInput);

            FMoveFrameDataRow ProjectileMoveData;
            ProjectileMoveData.MoveID = TEXT("BALL_PROJECTILE");
            ProjectileMoveData.ActiveFrames = 2;
            ProjectileMoveData.RecoveryFrames = 12;
            ProjectileMoveData.AdvantageOnBlock = Ball->GetBallState().AdvantageOnBlock;
            ProjectileMoveData.AdvantageOnHit = Ball->GetBallState().AdvantageOnHit;
            ProjectileMoveData.BaseDamage = Ball->GetBallState().BaseDamage;

            DefenderSM->ApplyIncomingHitOrBlock(ProjectileMoveData, bBlocked);
            if (DefenderPawn->GetVisualFeedbackComponent() && !bIsRollbackReSimulation)
            {
                DefenderPawn->GetVisualFeedbackComponent()->TriggerHitstopAndShake(bBlocked ? 7 : 11, true, bBlocked ? 2.5f : 5.5f);
            }

            Ball->DeactivateBall();
        }
    }
}

void AFightingMatchGameMode::ResolveMeleeHitboxes(bool bIsRollbackReSimulation)
{
    UDeterministicFighterStateMachine* P1SM = Player1Pawn->GetFighterStateMachine();
    UDeterministicFighterStateMachine* P2SM = Player2Pawn->GetFighterStateMachine();

    FFixedAABB P1Hitbox, P2Hitbox;
    FMoveFrameDataRow P1Move, P2Move;
    const bool bP1HasActiveHitbox = P1SM->GetCurrentActiveHitbox(P1Hitbox, P1Move);
    const bool bP2HasActiveHitbox = P2SM->GetCurrentActiveHitbox(P2Hitbox, P2Move);

    const FFixedAABB P1Hurtbox = P1SM->GetCurrentHurtbox();
    const FFixedAABB P2Hurtbox = P2SM->GetCurrentHurtbox();

    const bool bP1HitsP2 = bP1HasActiveHitbox && P1Hitbox.Intersects(P2Hurtbox);
    const bool bP2HitsP1 = bP2HasActiveHitbox && P2Hitbox.Intersects(P1Hurtbox);

    AFightingMatchGameState* MatchGS = GetGameState<AFightingMatchGameState>();

    // Resolución simétrica (permite Trade si ambos conectan en el mismo frame exacto)
    if (bP1HitsP2)
    {
        const bool bP2Blocked = !bP2HitsP1 && IsDefenderBlockingAttack(P1SM->GetState(), P2SM->GetState(), CachedP2InputMask);
        P1SM->NotifyAttackConnected(bP2Blocked);
        P2SM->ApplyIncomingHitOrBlock(P1Move, bP2Blocked);

        if (MatchGS && !bP2Blocked)
        {
            ++MatchGS->MatchState.P1ActiveComboHits;
            MatchGS->MatchState.P1ActiveComboDamage += P1Move.BaseDamage;
        }

        if (!bIsRollbackReSimulation)
        {
            const int32 HitstopFrames = bP2Blocked ? 6 : 10;
            if (Player1Pawn->GetVisualFeedbackComponent())
            {
                Player1Pawn->GetVisualFeedbackComponent()->TriggerHitstopAndShake(HitstopFrames, false, 0.0f);
            }
            if (Player2Pawn->GetVisualFeedbackComponent())
            {
                Player2Pawn->GetVisualFeedbackComponent()->TriggerHitstopAndShake(HitstopFrames, true, bP2Blocked ? 2.2f : 4.8f);
            }
        }
    }

    if (bP2HitsP1)
    {
        const bool bP1Blocked = !bP1HitsP2 && IsDefenderBlockingAttack(P2SM->GetState(), P1SM->GetState(), CachedP1InputMask);
        P2SM->NotifyAttackConnected(bP1Blocked);
        P1SM->ApplyIncomingHitOrBlock(P2Move, bP1Blocked);

        if (MatchGS && !bP1Blocked)
        {
            ++MatchGS->MatchState.P2ActiveComboHits;
            MatchGS->MatchState.P2ActiveComboDamage += P2Move.BaseDamage;
        }

        if (!bIsRollbackReSimulation)
        {
            const int32 HitstopFrames = bP1Blocked ? 6 : 10;
            if (Player2Pawn->GetVisualFeedbackComponent())
            {
                Player2Pawn->GetVisualFeedbackComponent()->TriggerHitstopAndShake(HitstopFrames, false, 0.0f);
            }
            if (Player1Pawn->GetVisualFeedbackComponent())
            {
                Player1Pawn->GetVisualFeedbackComponent()->TriggerHitstopAndShake(HitstopFrames, true, bP1Blocked ? 2.2f : 4.8f);
            }
        }
    }
}

void AFightingMatchGameMode::CheckAndTriggerStageWallBreak(int32 KnockedPlayerIndex, int32 WallDirectionSign)
{
    AFightingMatchGameState* MatchGS = GetGameState<AFightingMatchGameState>();
    if (!MatchGS || MatchGS->MatchState.bIsInStageZoneB)
    {
        return;
    }

    int32& TargetWallHealth = (WallDirectionSign < 0)
        ? MatchGS->MatchState.LeftWallRemainingHealth
        : MatchGS->MatchState.RightWallRemainingHealth;

    --TargetWallHealth;
    if (TargetWallHealth <= 0)
    {
        MatchGS->MatchState.bIsInStageZoneB = true;

        if (CameraDirector)
        {
            CameraDirector->TriggerWallBreakCameraSequence(
                WallDirectionSign,
                ActiveStageData.ZoneBBounds.GetLeftWallFixed(),
                ActiveStageData.ZoneBBounds.GetRightWallFixed());
        }

        if (UWorld* World = GetWorld())
        {
            if (UWwiseCombatAudioDirector* AudioDirector = World->GetSubsystem<UWwiseCombatAudioDirector>())
            {
                AudioDirector->NotifyStageWallBreakTransition(
                    ActiveStageData.WwiseZoneSwitchStateB,
                    MatchGS->MatchState.CurrentSimulationFrame);
            }
        }
    }
}

bool AFightingMatchGameMode::IsDefenderBlockingAttack(
    const FFighterDeterministicStatePOD& Attacker,
    const FFighterDeterministicStatePOD& Defender,
    uint16 DefenderInputMask) const
{
    // No se puede bloquear durante Startup/Active/Recovery de un ataque ni en Hitstun
    if (Defender.CurrentState == EFighterActionState::AttackStartup ||
        Defender.CurrentState == EFighterActionState::AttackActive ||
        Defender.CurrentState == EFighterActionState::AttackRecovery ||
        Defender.CurrentState == EFighterActionState::Hitstun ||
        Defender.CurrentState == EFighterActionState::HardKnockdown)
    {
        return false;
    }

    const bool bAttackerIsToRight = (Attacker.Position.X >= Defender.Position.X);
    const uint16 RequiredBackBit = bAttackerIsToRight ? ECombatInputBits::Left : ECombatInputBits::Right;

    return (DefenderInputMask & RequiredBackBit) != 0;
}

void AFightingMatchGameMode::BroadcastVisualAndHUDState(bool bIsRollbackReSimulation)
{
    if (bIsRollbackReSimulation)
    {
        return;
    }

    AFightingMatchGameState* MatchGS = GetGameState<AFightingMatchGameState>();
    const uint32 CurrentFrame = MatchGS ? MatchGS->MatchState.CurrentSimulationFrame : 0;

    if (BroadcastCameraActor && CameraDirector)
    {
        float HorizontalFOV = 54.0f;
        const FTransform CamTransform = CameraDirector->GetVisualCameraTransformCm(HorizontalFOV);
        BroadcastCameraActor->SetActorTransform(CamTransform);
        if (UCameraComponent* CamComp = BroadcastCameraActor->GetCameraComponent())
        {
            CamComp->SetFieldOfView(HorizontalFOV);
        }
    }

    if (Player1Pawn)
    {
        Player1Pawn->SyncVisualTransformFromFixedPoint(CurrentFrame, true);
    }
    if (Player2Pawn)
    {
        Player2Pawn->SyncVisualTransformFromFixedPoint(CurrentFrame, true);
    }
    if (Player1BallProjectile)
    {
        Player1BallProjectile->SyncBallVisualTransform(true);
    }
    if (Player2BallProjectile)
    {
        Player2BallProjectile->SyncBallVisualTransform(true);
    }

    UDeterministicFighterStateMachine* P1SM = Player1Pawn ? Player1Pawn->GetFighterStateMachine() : nullptr;
    UDeterministicFighterStateMachine* P2SM = Player2Pawn ? Player2Pawn->GetFighterStateMachine() : nullptr;
    if (!P1SM || !P2SM)
    {
        return;
    }

    const FFighterDeterministicStatePOD& P1State = P1SM->GetState();
    const FFighterDeterministicStatePOD& P2State = P2SM->GetState();

    if (P2State.CurrentHealth <= 0 && P1State.CurrentHealth > 0 && Player1Pawn)
    {
        Player1Pawn->PlayVictoryPoseAnimation();
    }
    else if (P1State.CurrentHealth <= 0 && P2State.CurrentHealth > 0 && Player2Pawn)
    {
        Player2Pawn->PlayVictoryPoseAnimation();
    }

    // Actualizar Audio Reactivo Wwise
    if (UWorld* World = GetWorld())
    {
        if (UWwiseCombatAudioDirector* AudioDirector = World->GetSubsystem<UWwiseCombatAudioDirector>())
        {
            const float P1Ratio = static_cast<float>(P1State.CurrentHealth) / static_cast<float>(FMath::Max(1, Player1Pawn->GetMaxHealth()));
            const float P2Ratio = static_cast<float>(P2State.CurrentHealth) / static_cast<float>(FMath::Max(1, Player2Pawn->GetMaxHealth()));
            const int32 RemSeconds = MatchGS ? MatchGS->GetRemainingMatchSeconds() : 99;
            const int32 MaxCombo = MatchGS ? FMath::Max(MatchGS->MatchState.P1ActiveComboHits, MatchGS->MatchState.P2ActiveComboHits) : 0;

            AudioDirector->UpdateDeterministicAudioFrame(CurrentFrame, false, P1Ratio, P2Ratio, RemSeconds, MaxCombo, 0);
        }
    }

    // Inyectar telemetría al HUD CommonUI Zero-Binding
    if (ActiveCombatHUDWidget && MatchGS)
    {
        FDeterministicHUDFramePacket Packet;
        Packet.SimulationFrame = CurrentFrame;
        Packet.RemainingMatchSeconds = MatchGS->GetRemainingMatchSeconds();
        Packet.CurrentRoundIndex = MatchGS->MatchState.CurrentRoundNumber;

        Packet.Player1.CurrentHealth = P1State.CurrentHealth;
        Packet.Player1.MaxHealth = Player1Pawn->GetMaxHealth();
        Packet.Player1.RecoverableRedHealth = P1State.CurrentHealth;
        Packet.Player1.SuperMeter = P1State.SuperMeter;
        Packet.Player1.GambetaStamina = P1State.GambetaMeter;
        Packet.Player1.YellowCardRisk = P1State.YellowCardRisk;
        Packet.Player1.ActiveComboHits = MatchGS->MatchState.P1ActiveComboHits;
        Packet.Player1.ActiveComboDamage = MatchGS->MatchState.P1ActiveComboDamage;

        Packet.Player2.CurrentHealth = P2State.CurrentHealth;
        Packet.Player2.MaxHealth = Player2Pawn->GetMaxHealth();
        Packet.Player2.RecoverableRedHealth = P2State.CurrentHealth;
        Packet.Player2.SuperMeter = P2State.SuperMeter;
        Packet.Player2.GambetaStamina = P2State.GambetaMeter;
        Packet.Player2.YellowCardRisk = P2State.YellowCardRisk;
        Packet.Player2.ActiveComboHits = MatchGS->MatchState.P2ActiveComboHits;
        Packet.Player2.ActiveComboDamage = MatchGS->MatchState.P2ActiveComboDamage;

        ActiveCombatHUDWidget->PushDeterministicHUDUpdate(Packet);
    }
}
