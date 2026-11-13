// FightingMatchGameMode.cpp - SouthAmericaFightersCore
#include "FightingMatchGameMode.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "FightingInputParser.h"

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

    CameraDirector = NewObject<UFightingCameraDirector>(this, TEXT("FightingCameraDirector"));
    CameraDirector->InitializeStageBounds(
        ActiveStageData.ZoneABounds.GetLeftWallFixed(),
        ActiveStageData.ZoneABounds.GetRightWallFixed());

    NetworkBridge = NewObject<UEOSGGPONetworkBridge>(this, TEXT("EOSGGPONetworkBridge"));
    ReplayDirector = NewObject<UReplayPlaybackSubsystem>(this, TEXT("ReplayPlaybackSubsystem"));

    // Instanciar luchadores P1 y P2 si no están ya en el nivel
    FActorSpawnParameters SpawnParams;
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    if (!Player1Pawn)
    {
        Player1Pawn = World->SpawnActor<AFighterCharacterPawn>(AFighterCharacterPawn::StaticClass(), FVector(-250.0f, 0.0f, 0.0f), FRotator::ZeroRotator, SpawnParams);
        if (Player1Pawn)
        {
            Player1Pawn->InitializeFighterForRound(0, TEXT("FENOMENO_BR"), FFixedPoint::FromMillimeters(-2500), true, 10000);
        }
    }

    if (!Player2Pawn)
    {
        Player2Pawn = World->SpawnActor<AFighterCharacterPawn>(AFighterCharacterPawn::StaticClass(), FVector(250.0f, 0.0f, 0.0f), FRotator(0.0f, 180.0f, 0.0f), SpawnParams);
        if (Player2Pawn)
        {
            Player2Pawn->InitializeFighterForRound(1, TEXT("CANON_AR"), FFixedPoint::FromMillimeters(2500), false, 10500);
        }
    }

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

    // Inicializar Audio Reactivo Wwise del estadio
    if (UWwiseCombatAudioDirector* AudioDirector = World->GetSubsystem<UWwiseCombatAudioDirector>())
    {
        AudioDirector->InitializeMatchAudioEnvironment(ActiveStageData.StageID, TEXT("FENOMENO_BR"), 0.0f);
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

    // Resolver fuente de entrada de P2 (Modo Entrenamiento o Jefe V.A.R. - ZERO)
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
    else if (ActiveBossAIController)
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

    // 1. Capturar posiciones previas antes del paso para evaluación simétrica
    const FFixedVector2D PrevP1Pos = P1SM->GetState().Position;
    const FFixedVector2D PrevP2Pos = P2SM->GetState().Position;

    // 2. Avanzar 1 frame ambas máquinas de estados deterministas
    P1SM->StepSimulationFrame(P1InputMask, PrevP2Pos);
    P2SM->StepSimulationFrame(P2InputMask, PrevP1Pos);

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
