// DeterministicFighterStateMachine.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include "FixedPointTypes.h"
#include "FightingInputParser.h"
#include "FrameDataTypes.h"
#include "DeterministicFighterStateMachine.generated.h"

UENUM(BlueprintType)
enum class EFighterActionState : uint8
{
    Idle,
    WalkForward,
    WalkBackward,
    Crouch,
    DashForward,
    DashBackward,
    JumpStartup,
    Airborne,
    AttackStartup,
    AttackActive,
    AttackRecovery,
    Blockstun,
    Hitstun,
    HardKnockdown
};

// POD Serializable con memcpy < 0.02ms para GGPO
struct FFighterDeterministicStatePOD
{
    FFixedVector2D Position;
    FFixedVector2D Velocity;
    int32 CurrentHealth = 10000;
    int32 SuperMeter = 0;      // 0 a 3000
    int32 GambetaMeter = 1000; // 0 a 1000
    int32 YellowCardRisk = 0;
    EFighterActionState CurrentState = EFighterActionState::Idle;
    FName ActiveMoveID = NAME_None;
    uint16 CurrentStateFrame = 0;
    uint16 StunFramesRemaining = 0;
    bool bIsFacingRight = true;
    bool bMoveHasConnectedThisExecution = false;
    bool bHitboxAlreadyRegistered = false;
};

UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UDeterministicFighterStateMachine : public UObject
{
    GENERATED_BODY()

public:
    void InitializeFighter(FFixedPoint SpawnX, bool bStartFacingRight, int32 MaxHP);
    void StepSimulationFrame(uint16 RawInputBitmask, const FFixedVector2D& OpponentPosition);

    FFixedAABB GetCurrentPushbox() const;
    FFixedAABB GetCurrentHurtbox() const;
    bool GetCurrentActiveHitbox(FFixedAABB& OutHitbox, FMoveFrameDataRow& OutMoveData) const;

    void NotifyAttackConnected(bool bWasBlocked);
    void ApplyIncomingHitOrBlock(const FMoveFrameDataRow& IncomingMove, bool bBlockedSuccessfully);

    void SaveDeterministicState(FFighterDeterministicStatePOD& OutState) const { OutState = State; }
    void LoadDeterministicState(const FFighterDeterministicStatePOD& InState) { State = InState; }
    uint32 ComputeStateChecksum() const;

    const FFighterDeterministicStatePOD& GetState() const { return State; }

private:
    FFighterDeterministicStatePOD State;
    FFightingInputRingBuffer InputBuffer;
    TMap<FName, FMoveFrameDataRow> MoveCatalog;

    void EvaluateInputTransitions();
    bool TryTriggerSpecialOrSuperMove(bool bIsCancelAttempt);
    bool CanCancelCurrentMove(ECancelWindowFlags RequiredFlag) const;
    void EnterMoveState(FName MoveID);
    void IntegrateFixedPointPhysics();
};
