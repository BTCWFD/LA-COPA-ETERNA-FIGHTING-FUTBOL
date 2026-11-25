// DeterministicFighterStateMachine.cpp - SouthAmericaFightersCore
#include "DeterministicFighterStateMachine.h"

namespace DeterministicArenaConstants
{
    // Límites de cancha Zona A (-12.5m a +12.5m) y Zona B (-18.5m a +18.5m) expresados en milímetros,
    // alineados con FightingMatchGameMode.cpp y StageDefinition.h.
    static constexpr int64 LeftWallFixedMm = -12500;
    static constexpr int64 RightWallFixedMm = 12500;
    static constexpr int64 ZoneBLeftWallFixedMm = -18500;
    static constexpr int64 ZoneBRightWallFixedMm = 18500;

    // Velocidades por frame a 60 Hz en milímetros (75 mm/f = 4.50 m/s, 57 mm/f = 3.42 m/s, gravedad 14 mm/f^2 = 50.4 m/s^2)
    static constexpr int64 WalkForwardMmPerFrame = 75;
    static constexpr int64 WalkBackwardMmPerFrame = 57;
    static constexpr int64 GravityMmPerFrameSq = 14;
}

void UDeterministicFighterStateMachine::InitializeFighter(FFixedPoint SpawnX, bool bStartFacingRight, int32 MaxHP)
{
    State = FFighterDeterministicStatePOD{};
    State.Position = FFixedVector2D(SpawnX, FFixedPoint(0));
    State.bIsFacingRight = bStartFacingRight;
    State.CurrentHealth = MaxHP;
}

void UDeterministicFighterStateMachine::StepSimulationFrame(
    uint16 RawInputBitmask, const FFixedVector2D& OpponentPosition)
{
    // 1. Auto-orientación solo en neutro de pie o agachado
    if (State.CurrentState == EFighterActionState::Idle ||
        State.CurrentState == EFighterActionState::Crouch)
    {
        State.bIsFacingRight = (OpponentPosition.X >= State.Position.X);
    }

    // 2. Alimentar el Ring Buffer
    InputBuffer.PushFrameInput(RawInputBitmask, State.bIsFacingRight);

    // 3. Incrementar reloj de frame del estado actual
    ++State.CurrentStateFrame;

    // 4. Hitstun / Blockstun
    if (State.CurrentState == EFighterActionState::Hitstun ||
        State.CurrentState == EFighterActionState::Blockstun)
    {
        if (State.StunFramesRemaining > 0)
        {
            --State.StunFramesRemaining;
        }
        if (State.StunFramesRemaining == 0)
        {
            State.CurrentState = EFighterActionState::Idle;
            State.CurrentStateFrame = 0;
        }
        IntegrateFixedPointPhysics();
        return;
    }

    // 5. Progresión Startup -> Active -> Recovery -> Idle
    if (State.CurrentState == EFighterActionState::AttackStartup ||
        State.CurrentState == EFighterActionState::AttackActive ||
        State.CurrentState == EFighterActionState::AttackRecovery)
    {
        if (const FMoveFrameDataRow* Move = MoveCatalog.Find(State.ActiveMoveID))
        {
            const int32 StartupEnd = Move->StartupFrames;
            const int32 ActiveEnd = StartupEnd + Move->ActiveFrames;
            const int32 TotalEnd = ActiveEnd + Move->RecoveryFrames;

            if (State.CurrentStateFrame < StartupEnd)
            {
                State.CurrentState = EFighterActionState::AttackStartup;
            }
            else if (State.CurrentStateFrame < ActiveEnd)
            {
                State.CurrentState = EFighterActionState::AttackActive;
            }
            else if (State.CurrentStateFrame < TotalEnd)
            {
                State.CurrentState = EFighterActionState::AttackRecovery;
            }
            else
            {
                State.CurrentState = EFighterActionState::Idle;
                State.ActiveMoveID = NAME_None;
                State.CurrentStateFrame = 0;
            }
        }
    }

    // 6. Evaluar transiciones por comandos
    EvaluateInputTransitions();

    // 7. Integrar físicas
    IntegrateFixedPointPhysics();
}

void UDeterministicFighterStateMachine::EvaluateInputTransitions()
{
    const bool bIsNeutral = (State.CurrentState == EFighterActionState::Idle ||
                             State.CurrentState == EFighterActionState::WalkForward ||
                             State.CurrentState == EFighterActionState::WalkBackward ||
                             State.CurrentState == EFighterActionState::Crouch);

    if (!bIsNeutral)
    {
        if (State.bMoveHasConnectedThisExecution)
        {
            TryTriggerSpecialOrSuperMove(true);
        }
        return;
    }

    if (TryTriggerSpecialOrSuperMove(false))
    {
        return;
    }

    // Golpes normales (HP > MP > LP)
    const FInputFrameEntry& Latest = InputBuffer.GetFrameFromBack(0);
    if (Latest.PressedThisFrame & ECombatInputBits::HP)
    {
        EnterMoveState(TEXT("Normal_5HP"));
        return;
    }
    if (Latest.PressedThisFrame & ECombatInputBits::MP)
    {
        EnterMoveState(TEXT("Normal_5MP"));
        return;
    }
    if (Latest.PressedThisFrame & ECombatInputBits::LP)
    {
        EnterMoveState(TEXT("Normal_5LP"));
        return;
    }

    // Movimiento básico
    if (Latest.RelativeNumpadDir == 6)
    {
        State.CurrentState = EFighterActionState::WalkForward;
        const FFixedPoint WalkSpeed = FFixedPoint::FromMillimeters(DeterministicArenaConstants::WalkForwardMmPerFrame);
        State.Velocity.X = State.bIsFacingRight ? WalkSpeed : -WalkSpeed;
    }
    else if (Latest.RelativeNumpadDir == 4)
    {
        State.CurrentState = EFighterActionState::WalkBackward;
        const FFixedPoint BackSpeed = FFixedPoint::FromMillimeters(DeterministicArenaConstants::WalkBackwardMmPerFrame);
        State.Velocity.X = State.bIsFacingRight ? -BackSpeed : BackSpeed;
    }
    else if (Latest.RelativeNumpadDir <= 3)
    {
        State.CurrentState = EFighterActionState::Crouch;
        State.Velocity.X = FFixedPoint(0);
    }
    else
    {
        State.CurrentState = EFighterActionState::Idle;
        State.Velocity.X = FFixedPoint(0);
    }
}

bool UDeterministicFighterStateMachine::TryTriggerSpecialOrSuperMove(bool bIsCancelAttempt)
{
    // Nivel 3 Ultimate (214214 + HP + SK)
    if (State.SuperMeter >= 3000 && (!bIsCancelAttempt || CanCancelCurrentMove(ECancelWindowFlags::SuperCancel)))
    {
        if (InputBuffer.CheckCommand(ECommandMotionType::Ultimate_214214, ECombatInputBits::HP | ECombatInputBits::SK))
        {
            State.SuperMeter -= 3000;
            EnterMoveState(TEXT("Ultimate_GritoSagrado"));
            return true;
        }
    }

    // Nivel 1 Super (236236 + SK)
    if (State.SuperMeter >= 1000 && (!bIsCancelAttempt || CanCancelCurrentMove(ECancelWindowFlags::SuperCancel)))
    {
        if (InputBuffer.CheckCommand(ECommandMotionType::Super_236236, ECombatInputBits::SK))
        {
            State.SuperMeter -= 1000;
            EnterMoveState(TEXT("Super_Level1"));
            return true;
        }
    }

    // Movimientos Especiales: 41236 > 623 > 236 > 214
    if (!bIsCancelAttempt || CanCancelCurrentMove(ECancelWindowFlags::SpecialCancel))
    {
        if (InputBuffer.CheckCommand(ECommandMotionType::HCF_41236, ECombatInputBits::LP))
        {
            EnterMoveState(TEXT("Special_41236_CommandGrab"));
            return true;
        }
        if (InputBuffer.CheckCommand(ECommandMotionType::DP_623, ECombatInputBits::HP))
        {
            EnterMoveState(TEXT("Special_623_AntiAir"));
            return true;
        }
        if (InputBuffer.CheckCommand(ECommandMotionType::QCF_236, ECombatInputBits::SK))
        {
            EnterMoveState(TEXT("Special_236_Projectile"));
            return true;
        }
        if (InputBuffer.CheckCommand(ECommandMotionType::QCB_214, ECombatInputBits::SK))
        {
            EnterMoveState(TEXT("Special_214_Technique"));
            return true;
        }
    }
    return false;
}

bool UDeterministicFighterStateMachine::CanCancelCurrentMove(ECancelWindowFlags RequiredFlag) const
{
    const FMoveFrameDataRow* Move = MoveCatalog.Find(State.ActiveMoveID);
    if (!Move) return false;
    const bool bHasFlag = (Move->CancelFlags & static_cast<uint8>(RequiredFlag)) != 0;
    if (!bHasFlag) return false;

    const int32 WindowStart = Move->StartupFrames;
    const int32 WindowEnd = WindowStart + Move->CancelWindowDurationFrames;
    return (State.CurrentStateFrame >= WindowStart && State.CurrentStateFrame <= WindowEnd);
}

void UDeterministicFighterStateMachine::EnterMoveState(FName MoveID)
{
    State.ActiveMoveID = MoveID;
    State.CurrentState = EFighterActionState::AttackStartup;
    State.CurrentStateFrame = 1;
    State.bMoveHasConnectedThisExecution = false;
    State.bHitboxAlreadyRegistered = false;
    State.Velocity.X = FFixedPoint(0);
}

void UDeterministicFighterStateMachine::IntegrateFixedPointPhysics()
{
    const FFixedPoint PrevX = State.Position.X;

    State.Position.X += State.Velocity.X;
    State.Position.Y += State.Velocity.Y;

    if (State.Position.Y > FFixedPoint(0))
    {
        State.Velocity.Y -= FFixedPoint::FromMillimeters(DeterministicArenaConstants::GravityMmPerFrameSq);
    }
    else if (State.Position.Y < FFixedPoint(0))
    {
        State.Position.Y = FFixedPoint(0);
        State.Velocity.Y = FFixedPoint(0);
    }

    if (State.CurrentState == EFighterActionState::Hitstun ||
        State.CurrentState == EFighterActionState::Blockstun)
    {
        State.Velocity.X = State.Velocity.X * FFixedPoint::FromMillimeters(820);
    }

    // Sujeción determinista a los límites de escenario (-12.5m / +12.5m en Zona A, -18.5m / +18.5m en Zona B).
    // Durante Hitstun permitimos cruzar la línea de Zona A en este paso para que FightingMatchGameMode
    // detecte el impacto contra el alambrado y evalúe CheckAndTriggerStageWallBreak().
    const FFixedPoint LeftWallZoneA = FFixedPoint::FromMillimeters(DeterministicArenaConstants::LeftWallFixedMm);
    const FFixedPoint RightWallZoneA = FFixedPoint::FromMillimeters(DeterministicArenaConstants::RightWallFixedMm);
    const FFixedPoint LeftWallZoneB = FFixedPoint::FromMillimeters(DeterministicArenaConstants::ZoneBLeftWallFixedMm);
    const FFixedPoint RightWallZoneB = FFixedPoint::FromMillimeters(DeterministicArenaConstants::ZoneBRightWallFixedMm);

    const bool bAlreadyInZoneB = (PrevX < LeftWallZoneA) || (PrevX > RightWallZoneA);
    if (State.CurrentState != EFighterActionState::Hitstun)
    {
        const FFixedPoint MinBound = bAlreadyInZoneB ? LeftWallZoneB : LeftWallZoneA;
        const FFixedPoint MaxBound = bAlreadyInZoneB ? RightWallZoneB : RightWallZoneA;
        State.Position.X = FFixedPoint::Clamp(State.Position.X, MinBound, MaxBound);
    }
    else
    {
        State.Position.X = FFixedPoint::Clamp(State.Position.X, LeftWallZoneB, RightWallZoneB);
    }
}

FFixedAABB UDeterministicFighterStateMachine::GetCurrentPushbox() const
{
    FFixedAABB Box;
    const FFixedPoint HalfW = FFixedPoint::FromMillimeters(300);
    Box.MinX = State.Position.X - HalfW;
    Box.MaxX = State.Position.X + HalfW;
    Box.MinY = State.Position.Y;
    Box.MaxY = State.Position.Y + FFixedPoint::FromMillimeters(1800);
    return Box;
}

FFixedAABB UDeterministicFighterStateMachine::GetCurrentHurtbox() const
{
    FFixedAABB Box;
    const FFixedPoint HalfW = FFixedPoint::FromMillimeters(350);
    Box.MinX = State.Position.X - HalfW;
    Box.MaxX = State.Position.X + HalfW;
    Box.MinY = State.Position.Y;
    Box.MaxY = State.Position.Y + FFixedPoint::FromMillimeters(1850);
    return Box;
}

bool UDeterministicFighterStateMachine::GetCurrentActiveHitbox(
    FFixedAABB& OutHitbox, FMoveFrameDataRow& OutMoveData) const
{
    if (State.CurrentState != EFighterActionState::AttackActive || State.bHitboxAlreadyRegistered)
    {
        return false;
    }
    if (const FMoveFrameDataRow* Move = MoveCatalog.Find(State.ActiveMoveID))
    {
        OutMoveData = *Move;
        const FFixedPoint ForwardOffset = State.bIsFacingRight ? FFixedPoint::FromMillimeters(400) : FFixedPoint::FromMillimeters(-400);
        const FFixedPoint BoxWidth = FFixedPoint::FromMillimeters(350);

        OutHitbox.MinX = State.Position.X + (State.bIsFacingRight ? ForwardOffset : ForwardOffset - BoxWidth);
        OutHitbox.MaxX = OutHitbox.MinX + BoxWidth;
        OutHitbox.MinY = State.Position.Y + FFixedPoint::FromMillimeters(400);
        OutHitbox.MaxY = OutHitbox.MinY + FFixedPoint::FromMillimeters(600);
        return true;
    }
    return false;
}

void UDeterministicFighterStateMachine::NotifyAttackConnected(bool bWasBlocked)
{
    State.bMoveHasConnectedThisExecution = true;
    State.bHitboxAlreadyRegistered = true;
    State.SuperMeter = FMath::Min(3000, State.SuperMeter + (bWasBlocked ? 60 : 120));
}

void UDeterministicFighterStateMachine::ApplyIncomingHitOrBlock(
    const FMoveFrameDataRow& IncomingMove, bool bBlockedSuccessfully)
{
    const int32 RemainingAttackerFrames = (IncomingMove.ActiveFrames - 1) + IncomingMove.RecoveryFrames;
    if (bBlockedSuccessfully)
    {
        State.CurrentState = EFighterActionState::Blockstun;
        State.StunFramesRemaining = FMath::Max(1, RemainingAttackerFrames + IncomingMove.AdvantageOnBlock);
        State.CurrentHealth = FMath::Max(1, State.CurrentHealth - (IncomingMove.BaseDamage / 8));
    }
    else
    {
        State.CurrentState = EFighterActionState::Hitstun;
        State.StunFramesRemaining = FMath::Max(1, RemainingAttackerFrames + IncomingMove.AdvantageOnHit);
        State.CurrentHealth = FMath::Max(0, State.CurrentHealth - IncomingMove.BaseDamage);
    }
    State.CurrentStateFrame = 0;
}

uint32 UDeterministicFighterStateMachine::ComputeStateChecksum() const
{
    const uint16* Data = reinterpret_cast<const uint16*>(&State);
    size_t Len = sizeof(FFighterDeterministicStatePOD) / 2;
    uint32 Sum1 = 0xFFFF, Sum2 = 0xFFFF;
    while (Len > 0)
    {
        size_t TLen = Len > 360 ? 360 : Len;
        Len -= TLen;
        do
        {
            Sum1 += *Data++;
            Sum2 += Sum1;
        } while (--TLen);
        Sum1 = (Sum1 & 0xFFFF) + (Sum1 >> 16);
        Sum2 = (Sum2 & 0xFFFF) + (Sum2 >> 16);
    }
    Sum1 = (Sum1 & 0xFFFF) + (Sum1 >> 16);
    Sum2 = (Sum2 & 0xFFFF) + (Sum2 >> 16);
    return (Sum2 << 16) | Sum1;
}
