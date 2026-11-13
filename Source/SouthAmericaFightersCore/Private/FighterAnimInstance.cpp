// FighterAnimInstance.cpp - SouthAmericaFightersCore
// Unreal Engine 5.4+ - 60FPS Stepped Animation Bridge, Control Rig Smear Frames (1.25x),
// KawaiiPhysics/Spring Hair Solver (El Pibe / El Loco) & Chaos Cloth 5.4 AnimDrive Stiffness

#include "FighterAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"

UFighterAnimInstance::UFighterAnimInstance()
{
    bUseMultiThreadedAnimationUpdate = true;
    bForceSteppedPoseNoInterpolation = true;
    TeleportStiffnessHoldFrames = 0;
}

void UFighterAnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation();

    SetFighterHairArchetype(HairSpringParams.HairArchetype);
    ChaosClothRules = FChaosCloth54DynamicRules();
}

void UFighterAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);

    // Garantizar que cualquier tiempo acumulado se mantenga cuantizado a múltiplos exactos de 1/60s (16.666ms)
    QuantizedSequenceExplicitTime = QuantizeTimeToStepped60FPS( static_cast<float>(SteppedStateFrameIndex) / 60.0f );
}

float UFighterAnimInstance::QuantizeTimeToStepped60FPS(float RawTimeSeconds)
{
    constexpr float FramesPerSecond = 60.0f;
    constexpr float InvFramesPerSecond = 1.0f / 60.0f;
    const int32 DiscreteFrame = FMath::Max(0, FMath::FloorToInt((RawTimeSeconds * FramesPerSecond) + 0.0001f));
    return static_cast<float>(DiscreteFrame) * InvFramesPerSecond;
}

void UFighterAnimInstance::SetFighterHairArchetype(EFighterHairArchetype InArchetype)
{
    HairSpringParams.HairArchetype = InArchetype;

    switch (InArchetype)
    {
    case EFighterHairArchetype::ElPibe_Curly90sMane:
        // Melena rizada icónica de los años 90 ("El Pibe"): alta rigidez radial y rebote elástico corto
        HairSpringParams.Damping = 0.16f;
        HairSpringParams.Stiffness = 0.34f;
        HairSpringParams.CapsuleCollisionRadiusCm = 6.2f;
        break;

    case EFighterHairArchetype::ElLoco_LongFlowingLocks:
        // Melena larga suelta ("El Loco"): menor rigidez, gran estela aerodinámica en saltos y voleas
        HairSpringParams.Damping = 0.09f;
        HairSpringParams.Stiffness = 0.18f;
        HairSpringParams.CapsuleCollisionRadiusCm = 5.0f;
        break;

    case EFighterHairArchetype::Guerrera_BraidedTail:
        // Trenza larga balística con efecto látigo al girar
        HairSpringParams.Damping = 0.12f;
        HairSpringParams.Stiffness = 0.24f;
        HairSpringParams.CapsuleCollisionRadiusCm = 4.5f;
        break;

    case EFighterHairArchetype::StandardShort:
    default:
        HairSpringParams.Damping = 0.30f;
        HairSpringParams.Stiffness = 0.55f;
        HairSpringParams.CapsuleCollisionRadiusCm = 4.0f;
        break;
    }
}

void UFighterAnimInstance::SyncFromDeterministicFighterState(
    const FFighterDeterministicStatePOD& DeterministicState,
    bool bHadRollbackOrTeleportThisFrame,
    bool bIsInHitstop)
{
    CurrentActionState = DeterministicState.CurrentState;
    ActiveMoveID = DeterministicState.ActiveMoveID;
    SteppedStateFrameIndex = static_cast<int32>(DeterministicState.CurrentStateFrame);
    bIsFacingRight = DeterministicState.bIsFacingRight;

    PlanarVelocityMetersPerSec = FVector2D(
        DeterministicState.Velocity.X.ToFloatVisualOnly(),
        DeterministicState.Velocity.Y.ToFloatVisualOnly());

    // 1. Cuantización estricta a 60 FPS puros:
    // Durante ataques, bloqueos y hitstun se prohíbe la interpolación sub-frame para que Overheads y Lows
    // muestren sus keyframes clave en el frame exacto 1:1 con la tabla de Frame Data.
    QuantizedSequenceExplicitTime = static_cast<float>(SteppedStateFrameIndex) * (1.0f / 60.0f);
    bForceSteppedPoseNoInterpolation =
        (CurrentActionState == EFighterActionState::AttackStartup) ||
        (CurrentActionState == EFighterActionState::AttackActive) ||
        (CurrentActionState == EFighterActionState::AttackRecovery) ||
        (CurrentActionState == EFighterActionState::Blockstun) ||
        (CurrentActionState == EFighterActionState::Hitstun);

    // 2. Evaluación de Smear / Exaggeration Control Rig (1.25x en tibia/botín durante frames activos)
    EvaluateControlRigSmearWeights(DeterministicState);

    // 3. Evaluación de cadenas de resortes KawaiiPhysics para las melenas de El Pibe y El Loco
    EvaluateHairSpringChainSolver(DeterministicState, bHadRollbackOrTeleportThisFrame, bIsInHitstop);

    // 4. Reglas de mapas de peso y AnimDriveStiffness (0.95 en teleports/rollbacks) para Chaos Cloth 5.4
    EvaluateChaosCloth54Parameters(DeterministicState, bHadRollbackOrTeleportThisFrame);
    PushChaosClothParametersToSkeletalMesh();
}

void UFighterAnimInstance::EvaluateControlRigSmearWeights(const FFighterDeterministicStatePOD& State)
{
    SmearRigWeights = FControlRigSmearFrameWeights();

    if (State.CurrentState != EFighterActionState::AttackActive)
    {
        return;
    }

    SmearRigWeights.bEnableSmearDeformation = true;

    const FString MoveNameStr = State.ActiveMoveID.ToString();
    const float FacingSign = State.bIsFacingRight ? 1.0f : -1.0f;

    // Detectar si es Chilena, Volea, Barrida o Puntazo Pesado para aplicar deformación 1.25x en Tibia y Botín
    const bool bIsLeftLegStrike =
        MoveNameStr.Contains(TEXT("Chilena"), ESearchCase::IgnoreCase) ||
        MoveNameStr.Contains(TEXT("Sweep"), ESearchCase::IgnoreCase) ||
        MoveNameStr.Contains(TEXT("2HK"), ESearchCase::IgnoreCase);

    const bool bIsHeaderStrike =
        MoveNameStr.Contains(TEXT("Header"), ESearchCase::IgnoreCase) ||
        MoveNameStr.Contains(TEXT("Palomita"), ESearchCase::IgnoreCase) ||
        MoveNameStr.Contains(TEXT("Cabezazo"), ESearchCase::IgnoreCase);

    const bool bIsHandKeeperStrike =
        MoveNameStr.Contains(TEXT("Punch"), ESearchCase::IgnoreCase) ||
        MoveNameStr.Contains(TEXT("HP"), ESearchCase::IgnoreCase) ||
        MoveNameStr.Contains(TEXT("LP"), ESearchCase::IgnoreCase);

    if (bIsHeaderStrike)
    {
        SmearRigWeights.HeaderCrownScale = FVector(1.18f, 1.12f, 1.18f);
        SmearRigWeights.SwingArcTangentLocal = FVector(FacingSign, 0.0f, -0.25f).GetSafeNormal();
    }
    else if (bIsHandKeeperStrike)
    {
        SmearRigWeights.LeadHandScale = FVector(1.22f, 1.10f, 1.22f);
        SmearRigWeights.SwingArcTangentLocal = FVector(FacingSign, 0.0f, 0.15f).GetSafeNormal();
    }
    else if (bIsLeftLegStrike)
    {
        // Exageración 1.25x en tibia/botín izquierdo para Chilenas y Barridas
        SmearRigWeights.LeftTibiaAndBootScale = FVector(1.25f, 1.12f, 1.25f);
        SmearRigWeights.SwingArcTangentLocal = FVector(FacingSign * 0.7f, 0.0f, 0.7f).GetSafeNormal();
    }
    else
    {
        // Por defecto en ataques de pierna/voleas/cañonazos: 1.25x en tibia y botín derecho
        SmearRigWeights.RightTibiaAndBootScale = FVector(1.25f, 1.12f, 1.25f);
        SmearRigWeights.SwingArcTangentLocal = FVector(FacingSign * 0.85f, 0.0f, 0.52f).GetSafeNormal();
    }
}

void UFighterAnimInstance::EvaluateHairSpringChainSolver(
    const FFighterDeterministicStatePOD& State,
    bool bHadTeleport,
    bool bIsInHitstop)
{
    if (HairSpringParams.HairArchetype == EFighterHairArchetype::StandardShort)
    {
        HairSpringParams.SolverAlpha = 0.0f;
        HairSpringParams.WorldInertialWindForce = FVector::ZeroVector;
        return;
    }

    if (bIsInHitstop)
    {
        // Congelar las cadenas de pelo durante el Hitstop para reforzar el impacto visual
        HairSpringParams.SolverAlpha = 0.0f;
        return;
    }

    HairSpringParams.SolverAlpha = 1.0f;

    if (bHadTeleport)
    {
        // En frame de Rollback/Teleport anulamos la fuerza inercial para evitar latigazo capilar
        HairSpringParams.WorldInertialWindForce = FVector::ZeroVector;
        return;
    }

    // Fuerza de viento aparente opuesta a la velocidad del luchador + gravedad estilizada
    const float VelXCmPerSec = State.Velocity.X.ToFloatVisualOnly() * 100.0f;
    const float VelZCmPerSec = State.Velocity.Y.ToFloatVisualOnly() * 100.0f;

    const float ArchetypeWindMultiplier =
        (HairSpringParams.HairArchetype == EFighterHairArchetype::ElLoco_LongFlowingLocks) ? 1.45f : 1.0f;

    HairSpringParams.WorldInertialWindForce = FVector(
        -VelXCmPerSec * 0.65f * ArchetypeWindMultiplier,
        0.0f,
        (-VelZCmPerSec * 0.45f * ArchetypeWindMultiplier) - 280.0f);
}

void UFighterAnimInstance::EvaluateChaosCloth54Parameters(
    const FFighterDeterministicStatePOD& State,
    bool bHadTeleport)
{
    if (bHadTeleport)
    {
        TeleportStiffnessHoldFrames = 3;
    }

    if (TeleportStiffnessHoldFrames > 0)
    {
        --TeleportStiffnessHoldFrames;
        // Regla técnica Chaos Cloth 5.4: AnimDriveStiffness = 0.95 durante teleports/rollbacks
        // para ceñir la tela a la malla cinemática y evitar penetraciones o estiramientos infinitos.
        ChaosClothRules.AnimDriveStiffness = 0.95f;
        ChaosClothRules.AnimDriveDamping = 0.85f;
        ChaosClothRules.LinearVelocityScale = 0.0f;
        ChaosClothRules.MaxDistanceScaleCm = 6.0f;
        return;
    }

    const float SpeedMetersPerSec = FMath::Sqrt(
        FMath::Square(State.Velocity.X.ToFloatVisualOnly()) +
        FMath::Square(State.Velocity.Y.ToFloatVisualOnly()));

    if (State.CurrentState == EFighterActionState::DashForward ||
        State.CurrentState == EFighterActionState::DashBackward ||
        SpeedMetersPerSec > 7.5f)
    {
        // Durante Gambeta Dash de alta velocidad: elevar AnimDriveStiffness a 0.52 para mantener silueta limpia
        ChaosClothRules.AnimDriveStiffness = 0.52f;
        ChaosClothRules.AnimDriveDamping = 0.40f;
        ChaosClothRules.LinearVelocityScale = 0.35f;
        ChaosClothRules.MaxDistanceScaleCm = 14.0f;
    }
    else
    {
        // Estado nominal de combate/idle: camiseta holgada de los años 90 con pliegues libres (AnimDriveStiffness = 0.18)
        ChaosClothRules.AnimDriveStiffness = 0.18f;
        ChaosClothRules.AnimDriveDamping = 0.25f;
        ChaosClothRules.LinearVelocityScale = 0.75f;
        ChaosClothRules.MaxDistanceScaleCm = 18.0f;
    }
}

void UFighterAnimInstance::PushChaosClothParametersToSkeletalMesh()
{
    USkeletalMeshComponent* OwningMesh = GetSkelMeshComponent();
    if (!IsValid(OwningMesh))
    {
        return;
    }

    // Si estamos en el primer frame de estabilización de Teleport (AnimDriveStiffness >= 0.94f),
    // solicitar a Chaos Cloth el reset de velocidades inerciales de partículas
    if (ChaosClothRules.AnimDriveStiffness >= 0.94f && TeleportStiffnessHoldFrames == 2)
    {
        OwningMesh->ForceNextUpdateTeleportAndReset();
    }
}
