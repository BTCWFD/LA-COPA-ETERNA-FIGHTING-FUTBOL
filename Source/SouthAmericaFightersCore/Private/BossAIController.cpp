// BossAIController.cpp - SouthAmericaFightersCore
#include "BossAIController.h"
#include "FightingInputParser.h"

uint32 FCombatFrameSnapshot::ComputeFletcher32Checksum() const
{
    // Calcula Fletcher-32 determinista excluyendo el propio campo Checksum al final del struct
    const uint16* Data = reinterpret_cast<const uint16*>(this);
    const size_t ByteLength = offsetof(FCombatFrameSnapshot, Checksum);
    size_t WordLen = ByteLength / sizeof(uint16);

    uint32 Sum1 = 0xFFFF;
    uint32 Sum2 = 0xFFFF;

    while (WordLen > 0)
    {
        size_t ChunkLen = (WordLen > 360) ? 360 : WordLen;
        WordLen -= ChunkLen;
        do
        {
            Sum1 += *Data++;
            Sum2 += Sum1;
        } while (--ChunkLen);

        Sum1 = (Sum1 & 0xFFFF) + (Sum1 >> 16);
        Sum2 = (Sum2 & 0xFFFF) + (Sum2 >> 16);
    }

    Sum1 = (Sum1 & 0xFFFF) + (Sum1 >> 16);
    Sum2 = (Sum2 & 0xFFFF) + (Sum2 >> 16);
    return (Sum2 << 16) | Sum1;
}

ABossAIController::ABossAIController()
{
    PrimaryActorTick.bCanEverTick = false; // El paso de IA se ejecuta de forma determinista a 60 Hz mediante DeterministicStep
}

void ABossAIController::BindFighterStateMachines(
    UDeterministicFighterStateMachine* InPlayerFighter,
    UDeterministicFighterStateMachine* InBossFighter)
{
    PlayerFighterSM = InPlayerFighter;
    BossFighterSM = InBossFighter;
    HistoryWriteIndex = 0;
    ValidHistoryFrames = 0;
    StreetFootballOutplayCount = 0;
    RewindCooldownRemaining = 0;
    OverloadFramesRemaining = 0;
    bIsSystemOverloaded = false;
    bCooperativeUltimateReady = false;
    CurrentPhase = EBossPhase::Phase1_IronRule;
}

void ABossAIController::DeterministicStep(uint32 CurrentFrame)
{
    // 1. Grabar snapshot determinista del frame actual en el Ring Buffer de 120 frames
    RecordCurrentFrameSnapshot(CurrentFrame);

    // 2. Actualizar contadores de enfriamiento y sobrecarga
    if (RewindCooldownRemaining > 0)
    {
        --RewindCooldownRemaining;
    }

    if (bIsSystemOverloaded)
    {
        if (OverloadFramesRemaining > 0)
        {
            --OverloadFramesRemaining;
            CurrentBossInputBitmask = 0; // El jefe queda en cortocircuito sin poder defenderse ni hacer Rewind
            return;
        }
        bIsSystemOverloaded = false;
    }

    // 3. Evaluar transición a Fase 2 ("Tiempo de Descuento Infinito")
    CheckAndTriggerPhaseTwoTransition();

    // 4. Si está en Fase 2 y está recibiendo un combo prolongado en Hitstun, activar V.A.R. Rewind
    if (CurrentPhase == EBossPhase::Phase2_InfiniteStoppage && BossFighterSM != nullptr)
    {
        const FFighterDeterministicStatePOD& BossState = BossFighterSM->GetState();
        if (BossState.CurrentState == EFighterActionState::Hitstun &&
            BossState.CurrentStateFrame >= 24 &&
            RewindCooldownRemaining == 0)
        {
            if (TriggerVARRewind(DefaultRewindFrames))
            {
                return;
            }
        }
    }

    // 5. Leer estado percibido con retardo humano (ReactionDelayFrames) para evitar input-reading de frame 0
    FCombatFrameSnapshot PerceivedSnapshot;
    if (!GetDelayedPerceivedSnapshot(PerceivedSnapshot))
    {
        CurrentBossInputBitmask = 0;
        return;
    }

    // 6. Decidir acción táctica determinista en función de la distancia en punto fijo y el estado percibido
    CurrentBossInputBitmask = DecideTacticalAction(CurrentFrame, PerceivedSnapshot);
}

void ABossAIController::RegisterStreetFootballOutplay()
{
    ++StreetFootballOutplayCount;

    if (StreetFootballOutplayCount >= OutplaysRequiredForOverload && !bIsSystemOverloaded)
    {
        bIsSystemOverloaded = true;
        bCooperativeUltimateReady = true;
        OverloadFramesRemaining = SystemOverloadDurationFrames;
        CurrentBossInputBitmask = 0;

        OnBossSystemOverload.Broadcast();
    }
}

bool ABossAIController::TriggerVARRewind(int32 FramesToRewind)
{
    if (bIsSystemOverloaded || RewindCooldownRemaining > 0)
    {
        return false;
    }

    const int32 ClampedRewind = FMath::Clamp(FramesToRewind, 1, HistoryCapacityFrames - 1);
    if (ValidHistoryFrames <= ClampedRewind)
    {
        return false;
    }

    const int32 TargetIndex = (HistoryWriteIndex - 1 - ClampedRewind + HistoryCapacityFrames * 2) % HistoryCapacityFrames;
    const FCombatFrameSnapshot& TargetSnapshot = FrameHistoryBuffer[TargetIndex];

    // Verificar integridad del checksum Fletcher-32 antes de restaurar
    if (TargetSnapshot.Checksum != TargetSnapshot.ComputeFletcher32Checksum())
    {
        return false;
    }

    ApplySnapshotToFighters(TargetSnapshot);
    RewindCooldownRemaining = VARRewindCooldownFrames;

    // Reiniciar ventana del historial al punto rebobinado para mantener coherencia temporal
    HistoryWriteIndex = (TargetIndex + 1) % HistoryCapacityFrames;
    ValidHistoryFrames = 1;

    OnVARRewindExecuted.Broadcast(TargetSnapshot);
    return true;
}

bool ABossAIController::CheckAndTriggerPhaseTwoTransition()
{
    if (CurrentPhase == EBossPhase::Phase2_InfiniteStoppage || BossFighterSM == nullptr)
    {
        return false;
    }

    const FFighterDeterministicStatePOD& BossState = BossFighterSM->GetState();
    if (BossState.CurrentHealth > 0 && BossState.CurrentHealth <= PhaseTwoHealthThreshold)
    {
        CurrentPhase = EBossPhase::Phase2_InfiniteStoppage;
        RewindCooldownRemaining = 0; // Habilita el primer V.A.R. Rewind inmediatamente en Fase 2
        OnBossPhaseChanged.Broadcast(CurrentPhase);
        return true;
    }

    return false;
}

bool ABossAIController::GetDelayedPerceivedSnapshot(FCombatFrameSnapshot& OutPerceivedSnapshot) const
{
    if (ValidHistoryFrames <= 0)
    {
        return false;
    }

    const int32 DelayToUse = FMath::Clamp(ReactionDelayFrames, 0, ValidHistoryFrames - 1);
    const int32 PerceivedIndex = (HistoryWriteIndex - 1 - DelayToUse + HistoryCapacityFrames * 2) % HistoryCapacityFrames;
    OutPerceivedSnapshot = FrameHistoryBuffer[PerceivedIndex];
    return true;
}

void ABossAIController::RecordCurrentFrameSnapshot(uint32 CurrentFrame)
{
    FCombatFrameSnapshot Snap;
    Snap.FrameNumber = CurrentFrame;

    if (PlayerFighterSM != nullptr)
    {
        const FFighterDeterministicStatePOD& P1 = PlayerFighterSM->GetState();
        Snap.P1PosX = P1.Position.X;
        Snap.P1PosY = P1.Position.Y;
        Snap.P1Health = P1.CurrentHealth;
        Snap.P1SuperMeter = P1.SuperMeter;
        Snap.P1StateID = static_cast<uint8>(P1.CurrentState);
        Snap.P1StateFrame = P1.CurrentStateFrame;
    }

    if (BossFighterSM != nullptr)
    {
        const FFighterDeterministicStatePOD& P2 = BossFighterSM->GetState();
        Snap.P2PosX = P2.Position.X;
        Snap.P2PosY = P2.Position.Y;
        Snap.P2Health = P2.CurrentHealth;
        Snap.P2SuperMeter = P2.SuperMeter;
        Snap.P2StateID = static_cast<uint8>(P2.CurrentState);
        Snap.P2StateFrame = P2.CurrentStateFrame;
    }

    Snap.Checksum = Snap.ComputeFletcher32Checksum();

    FrameHistoryBuffer[HistoryWriteIndex] = Snap;
    HistoryWriteIndex = (HistoryWriteIndex + 1) % HistoryCapacityFrames;
    ValidHistoryFrames = FMath::Min(ValidHistoryFrames + 1, HistoryCapacityFrames);
}

void ABossAIController::ApplySnapshotToFighters(const FCombatFrameSnapshot& Snapshot)
{
    if (PlayerFighterSM != nullptr)
    {
        FFighterDeterministicStatePOD P1State;
        PlayerFighterSM->SaveDeterministicState(P1State);
        P1State.Position.X = Snapshot.P1PosX;
        P1State.Position.Y = Snapshot.P1PosY;
        P1State.Velocity = FFixedVector2D(FFixedPoint(0), FFixedPoint(0));
        P1State.CurrentHealth = Snapshot.P1Health;
        P1State.SuperMeter = Snapshot.P1SuperMeter;
        P1State.CurrentState = EFighterActionState::Idle;
        P1State.ActiveMoveID = NAME_None;
        P1State.CurrentStateFrame = 0;
        P1State.StunFramesRemaining = 0;
        PlayerFighterSM->LoadDeterministicState(P1State);
    }

    if (BossFighterSM != nullptr)
    {
        FFighterDeterministicStatePOD P2State;
        BossFighterSM->SaveDeterministicState(P2State);
        P2State.Position.X = Snapshot.P2PosX;
        P2State.Position.Y = Snapshot.P2PosY;
        P2State.Velocity = FFixedVector2D(FFixedPoint(0), FFixedPoint(0));
        P2State.CurrentHealth = Snapshot.P2Health;
        // El jefe conserva su barra de Super o gasta 1000 por la intervención del V.A.R.
        P2State.SuperMeter = FMath::Max(0, Snapshot.P2SuperMeter - 1000);
        P2State.CurrentState = EFighterActionState::Idle;
        P2State.ActiveMoveID = NAME_None;
        P2State.CurrentStateFrame = 0;
        P2State.StunFramesRemaining = 0;
        BossFighterSM->LoadDeterministicState(P2State);
    }
}

uint16 ABossAIController::DecideTacticalAction(uint32 CurrentFrame, const FCombatFrameSnapshot& PerceivedState)
{
    const FFixedPoint DeltaX = PerceivedState.P1PosX - PerceivedState.P2PosX;
    const FFixedPoint AbsDistance = FFixedPoint::Abs(DeltaX);
    const bool bPlayerIsToRight = (DeltaX >= FFixedPoint(0));

    const uint16 ForwardBit = bPlayerIsToRight ? ECombatInputBits::Right : ECombatInputBits::Left;
    const uint16 BackBit    = bPlayerIsToRight ? ECombatInputBits::Left : ECombatInputBits::Right;

    const EFighterActionState PerceivedPlayerAction = static_cast<EFighterActionState>(PerceivedState.P1StateID);

    // 1. Defensa reactiva (con ReactionDelayFrames): si el jugador percibido está en frames activos de ataque a corta distancia, bloquear atrás/abajo
    if (PerceivedPlayerAction == EFighterActionState::AttackStartup ||
        PerceivedPlayerAction == EFighterActionState::AttackActive)
    {
        if (AbsDistance < FFixedPoint::FromMillimeters(1400))
        {
            return BackBit | ECombatInputBits::Down;
        }
    }

    // 2. Antiaéreo si el jugador percibido está en el aire acercándose
    if (PerceivedPlayerAction == EFighterActionState::Airborne &&
        AbsDistance < FFixedPoint::FromMillimeters(1600))
    {
        return ECombatInputBits::Down | ECombatInputBits::HP;
    }

    // 3. Fase 1 ("La Ley de Hierro"): Zoning con láser de Línea de Offside a larga distancia
    if (CurrentPhase == EBossPhase::Phase1_IronRule)
    {
        if (AbsDistance > FFixedPoint::FromMillimeters(2200))
        {
            // Dispara proyectil / Línea de Offside cada 45 frames
            if ((CurrentFrame % 45) == 0)
            {
                return ForwardBit | ECombatInputBits::SK;
            }
            return BackBit;
        }
    }
    else
    {
        // 4. Fase 2 ("Tiempo de Descuento Infinito"): Presión agresiva e intentos de agarre / tarjeta roja
        if (AbsDistance > FFixedPoint::FromMillimeters(1100))
        {
            return ForwardBit;
        }
        if ((CurrentFrame % 30) == 0)
        {
            return ECombatInputBits::HP | ECombatInputBits::SK;
        }
    }

    // Combate cercano estándar
    if (AbsDistance <= FFixedPoint::FromMillimeters(950))
    {
        return ((CurrentFrame % 12) == 0) ? ECombatInputBits::MP : ECombatInputBits::LP;
    }

    return ForwardBit;
}
